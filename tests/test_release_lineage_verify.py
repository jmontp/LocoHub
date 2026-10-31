"""Independent CORE-02 verifier checks of the release bundle builder.

All data here are synthetic and labelled as such. Values are chosen so the
expected outcome is known without running the builder: a constant 0.5 rad knee
signal lies inside the synthetic [0, 1] profile range, and 2.0 rad lies outside.
Tests marked ``xfail(strict=True)`` pin verifier-found gaps; they start passing
(and so fail the suite) when a gap is closed, prompting removal of the marker.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from contributor_tools import build_dataset_release as release


KNEE = "knee_flexion_angle_ipsi_rad"
HIP = "hip_flexion_angle_ipsi_rad"
IDENTITY = ("subject", "source_recording_id", "observation_id", "reference_side")
GRID = np.linspace(0.0, 100.0, 150)
IN_RANGE, OUT_OF_RANGE = 0.5, 2.0


def _cycle(subject, recording, observation, knee, side="right", task="level_walking"):
    return pd.DataFrame({
        "subject": subject, "source_recording_id": recording,
        "observation_id": observation, "reference_side": side,
        "observation_type": "individual_cycle", "task": task, "task_id": "synthetic",
        "task_info": '{"population": "synthetic"}', "phase_ipsi": GRID, KNEE: np.full(150, knee),
    })


def _profile(path, status="reviewed"):
    # Synthetic profile review record (required for reviewed/approved since CORE-09).
    head = (f"review_status: {status}\n" + "review:\n  reviewer: synthetic-profile-reviewer\n  reviewed_at: '2026-01-02T00:00:00Z'\n") if status is not None else ""
    path.write_text(
        head + "version: '2.0'\ntasks:\n  level_walking:\n"
        "    metadata:\n      applicability:\n        population: [synthetic]\n    phases:\n"
        f"      0:\n        {KNEE}: {{min: 0, max: 1}}\n"
        f"      100:\n        {KNEE}: {{min: 0, max: 1}}\n"
    )
    return path


def _provenance(directory, uri="synthetic_raw.bin"):
    raw = directory / "synthetic_raw.bin"
    raw.write_bytes(b"synthetic verifier source bytes")
    path = directory / "provenance.json"
    path.write_text(json.dumps({
        "dataset_id": "verifier-synthetic", "release_id": "verify-1",
        "sources": [{"uri": uri, "path": raw.name, "sha256": release.sha256_file(raw)}],
        "converter": {"name": "verifier-fixture", "revision": "v1"},
        "review": {"reviewer": "verifier-fixture", "reviewed_at": "2026-10-30T00:00:00Z"},
    }))
    return path


def _write(directory, frame_or_table):
    path = directory / "export.parquet"
    if isinstance(frame_or_table, pa.Table):
        pq.write_table(frame_or_table, path)
    else:
        frame_or_table.to_parquet(path, index=False)
    return path


def _build(directory, data, *, status="reviewed", uri="synthetic_raw.bin", out="bundle"):
    source = _write(directory, data)
    return release.build_release(
        source, directory / out, _provenance(directory, uri), ranges_path=_profile(directory / "p.yaml", status)
    ), directory / out


def _no_residue(directory):
    names = [path.name for path in directory.iterdir()]
    assert not [name for name in names if ".staging-" in name or name.endswith(".release.lock")]


# --- fix under review: input replacement between admission and read ----------

def test_export_swapped_in_after_admission_is_not_released(tmp_path, monkeypatch):
    small = _cycle("P1", "t1", "c1", IN_RANGE)
    larger = pd.concat([_cycle("P1", "t1", f"c{i}", IN_RANGE) for i in range(1, 5)], ignore_index=True)
    source = _write(tmp_path, small)
    admit = release._admit_input

    def admit_then_replace(path, **kwargs):
        admitted = admit(path, **kwargs)
        assert admitted["rows"] == 150
        larger.to_parquet(path, index=False)
        return admitted

    monkeypatch.setattr(release, "_admit_input", admit_then_replace)
    with pytest.raises(release.ReleaseError, match="changed"):
        release.build_release(source, tmp_path / "bundle", _provenance(tmp_path), ranges_path=_profile(tmp_path / "p.yaml"))
    assert not (tmp_path / "bundle").exists()
    _no_residue(tmp_path)


def test_export_changed_after_read_is_caught_by_copy_check(tmp_path, monkeypatch):
    data = pd.concat([_cycle("P1", "t1", "c1", IN_RANGE), _cycle("P1", "t1", "c2", OUT_OF_RANGE)])
    source = _write(tmp_path, data)
    original = release._filtered_rows

    def filter_then_edit(df, quality):
        _cycle("P9", "t9", "c9", IN_RANGE).to_parquet(source, index=False)
        return original(df, quality)

    monkeypatch.setattr(release, "_filtered_rows", filter_then_edit)
    with pytest.raises(release.ReleaseError, match="changed during release creation"):
        release.build_release(source, tmp_path / "bundle", _provenance(tmp_path), ranges_path=_profile(tmp_path / "p.yaml"))
    assert not (tmp_path / "bundle").exists()
    _no_residue(tmp_path)


# --- membership and accounting ----------------------------------------------

def test_rows_partition_exactly_into_filtered_and_ledger(tmp_path):
    data = pd.concat([
        _cycle("P1", "t1", "c1", IN_RANGE),
        _cycle("P1", "t1", "c1", OUT_OF_RANGE, side="left"),     # same ids, other side
        _cycle("P1", "t2", "c1", np.nan),                        # required signal absent
        _cycle("P2", "t1", "c1", IN_RANGE, task="incline_walking"),  # no profile task
        _cycle("P2", "t1", "c2", IN_RANGE),
    ], ignore_index=True)
    manifest, bundle = _build(tmp_path, data)
    filtered = pd.read_parquet(bundle / "filtered.parquet")
    ledger = pd.read_parquet(bundle / "exclusions.parquet")
    kept = set(map(tuple, filtered[["subject", "source_recording_id", "observation_id", "reference_side"]].drop_duplicates().values))
    assert kept == {("P1", "t1", "c1", "right"), ("P2", "t1", "c2", "right")}
    assert sorted(zip(ledger.subject, ledger.source_recording_id, ledger.reference_side, ledger.status)) == [
        ("P1", "t1", "left", "failed"), ("P1", "t2", "right", "missing"), ("P2", "t1", "right", "unchecked"),
    ]
    assert len(filtered) + int(ledger.row_count.sum()) == len(data) == manifest["counts"]["full_rows"]
    quality = json.loads((bundle / "quality.json").read_text())
    columns = ("subject", "source_recording_id", "observation_id", "reference_side")
    eligible = {tuple(o["identity"][c] for c in columns) for o in quality["observations"] if o["eligible"]}
    assert eligible == kept


def test_identities_with_separator_characters_do_not_merge(tmp_path):
    data = pd.concat([
        _cycle("a|b", "c", "o", IN_RANGE),
        _cycle("a", "b|c", "o", OUT_OF_RANGE),
    ], ignore_index=True)
    manifest, bundle = _build(tmp_path, data)
    assert manifest["counts"]["full_observations"] == 2
    assert set(pd.read_parquet(bundle / "filtered.parquet").subject) == {"a|b"}


def test_input_row_order_changes_identity_but_not_filtered_bytes(tmp_path):
    base = pd.concat([_cycle("P1", "t1", f"c{i}", level) for i, level in enumerate([IN_RANGE, OUT_OF_RANGE, 0.25])])
    results = []
    for seed in (3, 11):
        directory = tmp_path / f"seed{seed}"
        directory.mkdir()
        manifest, bundle = _build(directory, base.sample(frac=1, random_state=seed))
        results.append((manifest["input"]["sha256"], release.sha256_file(bundle / "filtered.parquet"),
                        release.sha256_file(bundle / "full.parquet")))
    (in_a, filt_a, full_a), (in_b, filt_b, full_b) = results
    assert in_a != in_b and full_a == in_a and full_b == in_b
    assert filt_a == filt_b


def test_without_profile_nothing_is_filtered_in_and_everything_is_ledgered(tmp_path):
    data = pd.concat([_cycle("P1", "t1", "c1", IN_RANGE), _cycle("P1", "t1", "c2", IN_RANGE)])
    source = _write(tmp_path, data)
    manifest = release.build_release(source, tmp_path / "bundle", _provenance(tmp_path))
    assert manifest["counts"]["filtered_rows"] == 0
    ledger = pd.read_parquet(tmp_path / "bundle" / "exclusions.parquet")
    assert ledger.status.tolist() == ["unchecked", "unchecked"] and ledger.row_count.sum() == 300
    assert manifest["profile"]["review_status"] == "not_applicable"


# --- immutability -------------------------------------------------------------

@pytest.mark.parametrize("occupant", ["file", "dangling_link", "link_to_directory"])
def test_occupied_destinations_are_refused_without_writing_through(tmp_path, occupant):
    target = tmp_path / "bundle"
    elsewhere = tmp_path / "elsewhere"
    if occupant == "file":
        target.write_text("occupied")
    elif occupant == "dangling_link":
        target.symlink_to(tmp_path / "absent")
    else:
        elsewhere.mkdir()
        target.symlink_to(elsewhere)
    with pytest.raises(release.ReleaseError):
        _build(tmp_path, _cycle("P1", "t1", "c1", IN_RANGE))
    if occupant == "file":
        assert target.read_text() == "occupied"
    if occupant == "link_to_directory":
        assert not list(elsewhere.iterdir())
    _no_residue(tmp_path)


@pytest.mark.parametrize("status", ["draft", "Reviewed", "approved ", "pending"])
def test_profile_statuses_other_than_exact_reviewed_or_approved_are_refused(tmp_path, status):
    with pytest.raises(release.ReleaseError, match="cannot be published"):
        _build(tmp_path, _cycle("P1", "t1", "c1", IN_RANGE), status=f"'{status}'")
    assert not (tmp_path / "bundle").exists()


def test_card_and_manifest_add_no_approval_language(tmp_path):
    manifest, bundle = _build(tmp_path, _cycle("P1", "t1", "c1", IN_RANGE))
    card = (bundle / "README.md").read_text()
    assert "approv" not in card.lower() and "certified" not in card.lower()
    assert "not a universal quality certification" in card
    assert "approv" not in json.dumps({k: v for k, v in manifest.items() if k != "contract"}).lower()


def test_remote_only_checksum_is_declared_and_limited(tmp_path):
    data = _cycle("P1", "t1", "c1", IN_RANGE)
    source = _write(tmp_path, data)
    provenance = tmp_path / "remote.json"
    provenance.write_text(json.dumps({
        "dataset_id": "verifier-synthetic", "release_id": "verify-1",
        "sources": [{"uri": "https://example.invalid/raw.zip", "sha256": "F" * 64}],
        "converter": {"name": "verifier-fixture", "revision": "v1"},
        "review": {"reviewer": "verifier-fixture", "reviewed_at": "2026-10-30T00:00:00+00:00"},
    }))
    manifest = release.build_release(source, tmp_path / "bundle", provenance, ranges_path=_profile(tmp_path / "p.yaml"))
    assert manifest["sources"] == [{"uri": "https://example.invalid/raw.zip", "sha256": "f" * 64, "status": "contributor_declared"}]
    assert any("not downloaded" in item for item in manifest["limitations"])


# --- verifier-found gaps (strict xfail; remove the marker when fixed) -------

def test_filtered_export_keeps_the_full_export_arrow_schema(tmp_path):
    frame = pd.concat([_cycle("P1", "t1", "c1", IN_RANGE), _cycle("P1", "t1", "c2", OUT_OF_RANGE)], ignore_index=True)
    rows = len(frame)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    table = table.append_column("sample_count", pa.array([i if i < 150 else None for i in range(rows)], pa.int64()))
    table = table.append_column("note", pa.array([None if i < 150 else "excluded" for i in range(rows)], pa.string()))
    table = table.append_column("label", pa.array(["s"] * rows, pa.large_string()))
    table = table.replace_schema_metadata({**table.schema.metadata, b"synthetic_units": b"{}"})
    _, bundle = _build(tmp_path, table)
    full = pq.read_schema(bundle / "full.parquet")
    filtered = pq.read_schema(bundle / "filtered.parquet")
    assert [(f.name, f.type) for f in filtered] == [(f.name, f.type) for f in full]
    assert b"synthetic_units" in filtered.metadata


def test_filtered_export_keeps_source_nan_encoding(tmp_path):
    frame = _cycle("P1", "t1", "c1", IN_RANGE)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    hip = np.where(np.arange(150) % 10 == 0, np.nan, 0.3)
    table = table.append_column(HIP, pa.array(hip, pa.float64(), from_pandas=False))
    assert table[HIP].null_count == 0
    _, bundle = _build(tmp_path, table)
    column = pq.read_table(bundle / "filtered.parquet")[HIP]
    assert column.null_count == 0
    assert pc.sum(pc.is_nan(column)).as_py() == 15


def test_categorical_identities_release_like_plain_strings(tmp_path):
    # Was the CORE-02-G7 pin; CORE-08 fixed the root cause. Single-category columns
    # (subject, source_recording_id, reference_side here) were the crashing case.
    plain = pd.concat([
        _cycle("P1", "t1", "c2", OUT_OF_RANGE),
        _cycle("P1", "t1", "c1", IN_RANGE),
        _cycle("P1", "t1", "c3", 0.25),
    ], ignore_index=True)
    categorical = plain.copy()
    for column in IDENTITY:
        categorical[column] = categorical[column].astype("category")
    results = []
    for label, frame in (("plain", plain), ("categorical", categorical)):
        directory = tmp_path / label
        directory.mkdir()
        manifest, bundle = _build(directory, frame)
        quality = json.loads((bundle / "quality.json").read_text())
        filtered = pd.read_parquet(bundle / "filtered.parquet")
        ledger = pd.read_parquet(bundle / "exclusions.parquet")
        for table in (filtered, ledger):
            for column in IDENTITY:
                table[column] = table[column].astype(str)
        results.append((
            manifest["counts"],
            [(o["identity"], o["status"], o["row_count"]) for o in quality["observations"]],
            filtered.reset_index(drop=True),
            ledger.reset_index(drop=True),
        ))
    (counts_p, obs_p, filt_p, led_p), (counts_c, obs_c, filt_c, led_c) = results
    assert counts_c == counts_p and counts_p["filtered_observations"] == 2
    assert obs_c == obs_p
    pd.testing.assert_frame_equal(filt_c, filt_p)
    pd.testing.assert_frame_equal(led_c, led_p)


def test_remote_uri_verified_only_through_a_local_copy_is_labelled(tmp_path):
    manifest, _ = _build(tmp_path, _cycle("P1", "t1", "c1", IN_RANGE), uri="https://example.invalid/raw.zip")
    assert manifest["sources"][0]["status"] == "verified_local"
    assert any("not downloaded" in item for item in manifest["limitations"])
