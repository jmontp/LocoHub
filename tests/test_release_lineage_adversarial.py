"""Adversarial release-lineage checks on small synthetic fixtures (CORE-02).

Every array here is synthetic: six 150-sample phase observations with constant
or deliberately missing/infinite values. No research dataset is read.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from contributor_tools import build_dataset_release as release
from contributor_tools.common.data_contract import IDENTITY_COLUMNS


REQUIRED = "knee_flexion_angle_ipsi_rad"
OPTIONAL = "hip_flexion_angle_ipsi_rad"
PHASE = np.linspace(0, 100, 150)

# (subject, recording, observation, side, task, required values, optional values)
# The same observation_id recurs across recordings and sides on purpose.
_OBSERVATIONS = [
    ("S01", "rec_A", "c1", "left", "level_walking", 0.5, np.nan),  # passes; optional absent
    ("S01", "rec_B", "c1", "left", "level_walking", 2.0, 0.1),  # fails range
    ("S01", "rec_A", "c1", "right", "level_walking", 0.5, "partial"),  # passes; optional partial
    ("S02", "rec_A", "c1", "left", "level_walking", np.nan, 0.1),  # required missing
    ("S02", "rec_C", "c2", "left", "incline_walking", 0.5, 0.1),  # no profile for task
    ("S02", "rec_C", "c3", "left", "level_walking", "inf", 0.1),  # invalid sample
]
EXPECTED_STATUS = {
    ("S01", "rec_A", "c1", "left"): "passed",
    ("S01", "rec_B", "c1", "left"): "failed",
    ("S01", "rec_A", "c1", "right"): "passed",
    ("S02", "rec_A", "c1", "left"): "missing",
    ("S02", "rec_C", "c2", "left"): "unchecked",
    ("S02", "rec_C", "c3", "left"): "invalid",
}


def _values(spec):
    if spec == "partial":
        values = np.full(150, 0.1)
        values[40:60] = np.nan
        return values
    if spec == "inf":
        values = np.full(150, 0.5)
        values[75] = np.inf
        return values
    return np.full(150, spec, dtype=float)


def synthetic_frame() -> pd.DataFrame:
    frames = []
    for subject, recording, observation, side, task, required, optional in _OBSERVATIONS:
        frames.append(pd.DataFrame({
            "subject": subject, "source_recording_id": recording,
            "observation_id": observation, "reference_side": side,
            "observation_type": "individual_cycle", "task": task,
            "task_id": f"{task}_synthetic", "task_info": '{"population": "synthetic"}',  # synthetic label
            "phase_ipsi": PHASE, REQUIRED: _values(required), OPTIONAL: _values(optional),
        }))
    return pd.concat(frames, ignore_index=True)


def _keys(frame: pd.DataFrame) -> set:
    return set(frame[list(IDENTITY_COLUMNS)].drop_duplicates().itertuples(index=False, name=None))


@pytest.fixture
def inputs(tmp_path):
    raw = tmp_path / "synthetic_source.csv"
    raw.write_text("synthetic fixture bytes, not research data\n")
    source = tmp_path / "input.parquet"
    synthetic_frame().sample(frac=1, random_state=11).to_parquet(source, index=False)
    profile = tmp_path / "ranges.yaml"
    profile.write_text(
        "review_status: reviewed\n"
        "review: {reviewer: synthetic-profile-reviewer, reviewed_at: '2026-01-02T00:00:00Z',"
        " scope: synthetic fixture only}\n"
        "tasks:\n  level_walking:\n"
        f"    metadata:\n      required_features: [{REQUIRED}]\n"
        # Synthetic applicability: matches the synthetic population label in task_info.
        "      applicability: {population: [synthetic]}\n"
        f"      optional_features: [{OPTIONAL}]\n"
        "    phases:\n"
        f"      0:\n        {REQUIRED}: {{min: 0, max: 1}}\n        {OPTIONAL}: {{min: 0, max: 1}}\n"
        f"      100:\n        {REQUIRED}: {{min: 0, max: 1}}\n        {OPTIONAL}: {{min: 0, max: 1}}\n"
    )
    provenance = tmp_path / "provenance.json"
    provenance.write_text(json.dumps({
        "dataset_id": "synthetic-core02", "release_id": "fixture-v1",
        "sources": [{"uri": "synthetic_source.csv", "path": "synthetic_source.csv",
                     "sha256": release.sha256_file(raw)}],
        "converter": {"name": "synthetic-converter", "revision": "fixture-rev"},
        "review": {"reviewer": "synthetic-fixture", "reviewed_at": "2026-01-01T00:00:00Z",
                   "scope": "synthetic identity handling only"},
    }))
    return source, profile, provenance


def _edit_provenance(provenance: Path, change) -> None:
    raw = json.loads(provenance.read_text())
    change(raw)
    provenance.write_text(json.dumps(raw))


def _assert_nothing_published(tmp_path: Path, name: str = "release") -> None:
    assert not (tmp_path / name).exists()
    assert not list(tmp_path.glob(f".{name}.staging-*"))
    assert not (tmp_path / f".{name}.release.lock").exists()


# --- identity recording -----------------------------------------------------

def test_manifest_binds_every_input_output_and_code_identity(inputs, tmp_path):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    quality = json.loads((output / "quality.json").read_text())
    assert manifest["input"]["sha256"] == release.sha256_file(source)
    assert manifest["input"]["filename"] == "input.parquet"
    assert manifest["input"]["rows"] == manifest["counts"]["full_rows"] == 900
    assert quality["source"] == {
        "input_sha256": release.sha256_file(source),
        "provenance_sha256": release.sha256_file(provenance),
    }
    assert manifest["profile"]["sha256"] == release.sha256_file(profile)
    assert (output / "profile.yaml").read_bytes() == profile.read_bytes()
    assert (output / "provenance.json").read_bytes() == provenance.read_bytes()
    assert manifest["converter"] == {"name": "synthetic-converter", "revision": "fixture-rev"}
    for relative, digest in manifest["processing_code"].items():
        assert digest == release.sha256_file(release.ROOT / relative)
    published = {path.name for path in output.iterdir()}
    assert published == set(manifest["artifacts"]) | {"manifest.json", "manifest.sha256"}
    for name, artifact in manifest["artifacts"].items():
        assert artifact["sha256"] == release.sha256_file(output / name)
        assert artifact["size_bytes"] == (output / name).stat().st_size
    # The on-disk manifest is the returned manifest, sealed by its checksum file.
    assert json.loads((output / "manifest.json").read_text()) == json.loads(json.dumps(manifest))
    assert (output / "manifest.sha256").read_text() == (
        f"{release.sha256_file(output / 'manifest.json')}  manifest.json\n"
    )


# --- whole-observation filtering, shared lineage, known-missing ---------------

def test_filter_keeps_whole_observations_by_full_identity_not_observation_id(inputs, tmp_path):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    release.build_release(source, output, provenance, ranges_path=profile)
    full = pd.read_parquet(output / "full.parquet")
    filtered = pd.read_parquet(output / "filtered.parquet")
    passed = {key for key, status in EXPECTED_STATUS.items() if status == "passed"}
    assert _keys(filtered) == passed
    # Shared observation_id "c1" in rec_B (failed) and S02 (missing) is excluded.
    assert filtered.groupby(list(IDENTITY_COLUMNS)).size().tolist() == [150, 150]
    # Filtered rows are the full-export rows for those identities, value for value.
    index = pd.MultiIndex.from_frame(full[list(IDENTITY_COLUMNS)])
    expected = full.loc[index.isin(passed)].sort_values(
        list(IDENTITY_COLUMNS) + ["phase_ipsi"], kind="stable"
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(filtered.reset_index(drop=True), expected)
    # Same column names and Arrow types for this fixture's columns (strings, float64).
    # Other types, schema metadata and NaN encoding: tests/test_release_lineage_verify.py (G6).
    full_schema = pq.read_schema(output / "full.parquet")
    filtered_schema = pq.read_schema(output / "filtered.parquet")
    assert [(f.name, f.type) for f in filtered_schema] == [(f.name, f.type) for f in full_schema]


def test_known_missing_optional_values_are_preserved_not_imputed(inputs, tmp_path):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    release.build_release(source, output, provenance, ranges_path=profile)
    filtered = pd.read_parquet(output / "filtered.parquet")
    absent = filtered[filtered.reference_side == "left"]
    partial = filtered[filtered.reference_side == "right"].sort_values("phase_ipsi")
    assert absent[OPTIONAL].isna().all()
    assert partial[OPTIONAL].isna().sum() == 20
    assert partial[OPTIONAL].isna().to_numpy()[40:60].all()
    quality = json.loads((output / "quality.json").read_text())
    states = {
        observation["identity"]["reference_side"]: {
            signal["feature"]: signal["status"] for signal in observation["signals"]
        }
        for observation in quality["observations"]
        if observation["eligible"]
    }
    # Missing is recorded as missing, never as passing.
    assert states["left"][OPTIONAL] == "missing"
    assert states["right"][OPTIONAL] == "missing"
    assert states["left"][REQUIRED] == "passed"


# --- exclusions from the same assessment --------------------------------------

def test_exclusion_ledger_accounts_for_every_observation_from_one_assessment(inputs, tmp_path):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    quality = json.loads((output / "quality.json").read_text())
    full = pd.read_parquet(output / "full.parquet")
    filtered = pd.read_parquet(output / "filtered.parquet")
    ledger = pd.read_parquet(output / "exclusions.parquet")
    statuses = {
        tuple(item["identity"][c] for c in IDENTITY_COLUMNS): item["status"]
        for item in quality["observations"]
    }
    assert statuses == EXPECTED_STATUS
    ledger_keys = _keys(ledger)
    assert len(ledger) == len(ledger_keys) == 4
    assert ledger_keys.isdisjoint(_keys(filtered))
    assert ledger_keys | _keys(filtered) == _keys(full)
    assert int(ledger.row_count.sum()) + len(filtered) == len(full)
    by_identity = {
        tuple(item["identity"][c] for c in IDENTITY_COLUMNS): item
        for item in quality["observations"]
    }
    for row in ledger.to_dict("records"):
        item = by_identity[tuple(row[c] for c in IDENTITY_COLUMNS)]
        assert not item["eligible"]
        assert row["status"] == item["status"]
        assert json.loads(row["reasons_json"]) == item["reasons"]
        assert row["row_count"] == item["row_count"] == 150
        # No exclusion lacks identity, task metadata, or a stated reason.
        assert all(isinstance(row[c], str) and row[c] for c in (
            *IDENTITY_COLUMNS, "task", "task_id", "observation_type", "status"
        ))
        assert json.loads(row["reasons_json"])
    counts = manifest["counts"]
    assert counts["full_observations"] == 6 and counts["filtered_observations"] == 2
    assert counts["observation_statuses"] == {
        "passed": 2, "failed": 1, "missing": 1, "unchecked": 1, "invalid": 1
    }


@pytest.mark.parametrize("damage", [
    lambda frame: frame.drop(columns="task_id"),
    lambda frame: frame.assign(task_id=np.where(frame.observation_id == "c3", " ", frame.task_id)),
    lambda frame: frame.assign(task_info=np.where(frame.index % 2 == 0, "{}", '{"speed_m_s": 1}')),
    lambda frame: frame.assign(reference_side=np.where(frame.observation_id == "c2", "ipsi", frame.reference_side)),
])
def test_missing_or_ambiguous_exclusion_metadata_blocks_the_whole_release(inputs, tmp_path, damage):
    source, profile, provenance = inputs
    damage(pd.read_parquet(source)).to_parquet(source, index=False)
    with pytest.raises(release.ReleaseError, match="not publishable"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


# --- immutability and overwrite refusal ---------------------------------------

@pytest.mark.parametrize("occupant", ["empty_directory", "file", "dangling_symlink"])
def test_any_existing_destination_is_refused_untouched(inputs, tmp_path, occupant):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    if occupant == "empty_directory":
        output.mkdir()
    elif occupant == "file":
        output.write_text("pre-existing")
    else:
        output.symlink_to(tmp_path / "nowhere")
    with pytest.raises(release.ReleaseError, match="overwritten"):
        release.build_release(source, output, provenance, ranges_path=profile)
    if occupant == "empty_directory":
        assert output.is_dir() and not list(output.iterdir())
    elif occupant == "file":
        assert output.read_text() == "pre-existing"
    else:
        assert output.is_symlink() and not output.exists()


def test_stale_lock_is_refused_and_left_for_its_owner(inputs, tmp_path):
    source, profile, provenance = inputs
    lock = tmp_path / ".release.release.lock"
    lock.write_text("held by another builder")
    with pytest.raises(release.ReleaseError, match="stale lock"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert lock.read_text() == "held by another builder"
    assert not (tmp_path / "release").exists()


def test_destination_created_mid_build_is_not_merged_or_replaced(inputs, tmp_path, monkeypatch):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    original = release._release_card

    def racing_card(*args, **kwargs):
        output.mkdir()
        (output / "other.txt").write_text("concurrent writer")
        return original(*args, **kwargs)

    monkeypatch.setattr(release, "_release_card", racing_card)
    with pytest.raises(release.ReleaseError, match="already exists"):
        release.build_release(source, output, provenance, ranges_path=profile)
    assert [path.name for path in output.iterdir()] == ["other.txt"]
    assert not list(tmp_path.glob(".release.staging-*"))
    assert not (tmp_path / ".release.release.lock").exists()


def test_no_replace_rename_refuses_existing_empty_directory(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "a.txt").write_text("staged")
    destination = tmp_path / "destination"
    destination.mkdir()
    with pytest.raises(OSError):
        release._publish_directory(stage, destination)
    assert not list(destination.iterdir())
    assert (stage / "a.txt").read_text() == "staged"


# --- changed inputs -----------------------------------------------------------

def test_input_replaced_after_admission_is_rejected(inputs, tmp_path, monkeypatch):
    """A larger export swapped in after admission must not be released under the old evidence."""
    source, profile, provenance = inputs
    original = release._admit_input

    def admit_then_swap(path, **kwargs):
        admitted = original(path, **kwargs)
        bigger = synthetic_frame()
        bigger = pd.concat([bigger, bigger.assign(source_recording_id=bigger.source_recording_id + "_copy")], ignore_index=True)
        bigger.to_parquet(path, index=False)
        return admitted

    monkeypatch.setattr(release, "_admit_input", admit_then_swap)
    with pytest.raises(release.ReleaseError, match="changed"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


def test_input_modified_during_read_is_rejected(inputs, tmp_path, monkeypatch):
    source, profile, provenance = inputs
    original = release.pq.read_table

    def read_then_modify(path, **kwargs):
        table = original(path, **kwargs)
        with open(path, "ab") as handle:
            handle.write(b"\0")
        return table

    monkeypatch.setattr(release.pq, "read_table", read_then_modify)
    with pytest.raises(release.ReleaseError, match="changed"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


def test_profile_changed_after_hashing_is_rejected(inputs, tmp_path, monkeypatch):
    source, profile, provenance = inputs
    original = release.ValidationConfigManager

    def load_then_modify(path):
        config = original(path)
        profile.write_text(profile.read_text().replace("max: 1", "max: 3"))
        return config

    monkeypatch.setattr(release, "ValidationConfigManager", load_then_modify)
    with pytest.raises(release.ReleaseError, match="profile changed"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


def test_provenance_changed_after_parsing_is_rejected(inputs, tmp_path, monkeypatch):
    source, profile, provenance = inputs
    original = release._read_provenance

    def parse_then_modify(path):
        parsed = original(path)
        _edit_provenance(provenance, lambda raw: raw["converter"].update(revision="other"))
        return parsed

    monkeypatch.setattr(release, "_read_provenance", parse_then_modify)
    with pytest.raises(release.ReleaseError, match="Provenance changed"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


def test_missing_local_source_file_is_not_downgraded_to_declared(inputs, tmp_path):
    source, profile, provenance = inputs
    (tmp_path / "synthetic_source.csv").unlink()
    with pytest.raises(release.ReleaseError, match="checksum does not match"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


# --- incomplete review evidence -----------------------------------------------

@pytest.mark.parametrize("change, message", [
    (lambda raw: raw.pop("review"), "review metadata"),
    (lambda raw: raw.update(review="approved"), "review metadata"),
    (lambda raw: raw["review"].pop("reviewer"), "review.reviewer"),
    (lambda raw: raw["review"].update(reviewer="  "), "review.reviewer"),
    (lambda raw: raw["review"].pop("reviewed_at"), "review.reviewed_at"),
    (lambda raw: raw["review"].update(reviewed_at="2026-01-01T00:00:00"), "timezone"),
    (lambda raw: raw["review"].update(reviewed_at="last week"), "timezone"),
    (lambda raw: raw["converter"].pop("revision"), "converter.revision"),
    (lambda raw: raw.update(sources=[]), "at least one declared source"),
    (lambda raw: raw["sources"][0].pop("sha256"), "SHA-256"),
    (lambda raw: raw["sources"][0].update(sha256="abc"), "SHA-256"),
    (lambda raw: raw["sources"][0].update(path=None), "nonempty string"),
    (lambda raw: raw.update(release_id=""), "release_id"),
])
def test_incomplete_review_or_lineage_evidence_is_refused(inputs, tmp_path, change, message):
    source, profile, provenance = inputs
    _edit_provenance(provenance, change)
    with pytest.raises(release.ReleaseError, match=message):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


def test_duplicate_provenance_keys_are_refused(inputs, tmp_path):
    source, profile, provenance = inputs
    text = provenance.read_text()
    provenance.write_text(text[:-1] + ', "release_id": "other"}')
    with pytest.raises(ValueError, match="Duplicate"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


@pytest.mark.parametrize("status", ["draft", "Approved", "true", "pending"])
def test_unrecognized_profile_review_status_is_refused(inputs, tmp_path, status):
    source, profile, provenance = inputs
    profile.write_text(profile.read_text().replace("review_status: reviewed", f"review_status: {status}"))
    with pytest.raises(release.ReleaseError, match="cannot be published"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    _assert_nothing_published(tmp_path)


# --- no manufactured approval -------------------------------------------------

def test_declared_review_is_recorded_verbatim_without_added_approval(inputs, tmp_path):
    source, profile, provenance = inputs
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    assert manifest["review"] == {
        "reviewer": "synthetic-fixture", "reviewed_at": "2026-01-01T00:00:00Z",
        "scope": "synthetic identity handling only",
    }
    assert manifest["profile"]["review_status"] == "reviewed"
    assert manifest["profile"]["review"] == {
        "reviewer": "synthetic-profile-reviewer", "reviewed_at": "2026-01-02T00:00:00Z",
        "scope": "synthetic fixture only",
    }
    assert manifest["filter_policy"]["universal_pass_rate_threshold"] is None
    assert any("not a universal quality certification" in item for item in manifest["limitations"])
    text = json.dumps(manifest).lower() + (output / "README.md").read_text().lower()
    for claim in ("scientifically approved", "scientific approval", "certified", "validated dataset"):
        assert claim not in text


def test_legacy_profile_and_no_profile_never_imply_approval(inputs, tmp_path):
    source, profile, provenance = inputs
    profile.write_text("\n".join(profile.read_text().splitlines()[2:]) + "\n")
    legacy = release.build_release(source, tmp_path / "legacy", provenance, ranges_path=profile)
    assert legacy["profile"]["review_status"] == "legacy_unspecified"
    assert legacy["profile"]["review"] is None
    assert any("no inferred profile approval" in item for item in legacy["limitations"])
    unprofiled = release.build_release(source, tmp_path / "unprofiled", provenance)
    assert unprofiled["profile"]["review_status"] == "not_applicable"
    assert unprofiled["counts"]["filtered_observations"] == 0
    assert unprofiled["counts"]["observation_statuses"]["passed"] == 0


# --- remote checksum declarations ---------------------------------------------

def test_remote_checksums_stay_declared_even_when_claimed_verified(inputs, tmp_path):
    source, profile, provenance = inputs
    remote_hash = "A" * 64

    def add_remote(raw):
        raw["sources"].append({
            "uri": "https://example.invalid/synthetic.zip", "sha256": remote_hash,
            "status": "verified_download", "verified": True,
        })

    _edit_provenance(provenance, add_remote)
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    assert [(item["uri"], item["status"]) for item in manifest["sources"]] == [
        ("synthetic_source.csv", "verified_local"),
        ("https://example.invalid/synthetic.zip", "contributor_declared"),
    ]
    assert manifest["sources"][1]["sha256"] == remote_hash.lower()
    assert set(manifest["sources"][1]) == {"uri", "sha256", "status"}
    note = "Remote source checksums were declared by the contributor and were not downloaded"
    assert any(note in item for item in manifest["limitations"])
    assert note in (output / "README.md").read_text()


def test_all_local_sources_add_no_remote_limitation(inputs, tmp_path):
    source, profile, provenance = inputs
    manifest = release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert {item["status"] for item in manifest["sources"]} == {"verified_local"}
    assert not any("not downloaded" in item for item in manifest["limitations"])
