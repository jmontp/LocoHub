"""Independent CORE-06 verifier checks of the release-builder gap fixes.

Synthetic only. Filesystem cases run on pytest's Linux tmp path and on a
temporary directory on the repository's drvfs mount (removed after each test),
using the CORE-05 verifier fixtures. Strict xfails pin verifier-found residuals.
"""

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from contributor_tools import build_dataset_release as release
from tests.test_release_publish_drvfs_verify import (  # noqa: F401  (fixture import)
    KNEE, MARKER, _bundle_verifies, _inputs, _sealed_stage, where,
)


def _swap_after_admission(monkeypatch, replacement):
    admit = release._admit_input

    def admit_then_replace(path, **kwargs):
        admitted = admit(path, **kwargs)
        replacement(path)
        return admitted

    monkeypatch.setattr(release, "_admit_input", admit_then_replace)


def _spy_reads(monkeypatch):
    calls = []
    read = release.pq.read_table

    def spy(source, *args, **kwargs):
        calls.append(str(source))
        return read(source, *args, **kwargs)

    monkeypatch.setattr(release.pq, "read_table", spy)
    return calls


# --- G4 -------------------------------------------------------------------------

def test_admitted_bytes_are_read_through_the_open_handle(where, monkeypatch):
    calls = _spy_reads(monkeypatch)
    source, provenance, profile = _inputs(where)
    release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert len(calls) == 1 and calls[0].startswith("/proc/self/fd/")


def test_larger_replacement_is_rejected_without_an_eager_read(where, monkeypatch):
    source, provenance, profile = _inputs(where)
    bigger = pd.concat([pd.read_parquet(source)] * 3, ignore_index=True)
    bigger["observation_id"] = [f"{o}-{i // 300}" for i, o in enumerate(bigger.observation_id)]
    _swap_after_admission(monkeypatch, lambda path: bigger.to_parquet(path, index=False))
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="not read"):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (where / "rel").exists()


def test_same_footer_replacement_is_read_within_admission_and_rejected(where, monkeypatch):
    source, provenance, profile = _inputs(where)
    edited = pd.read_parquet(source)
    edited[KNEE] = edited[KNEE] * 0.9  # same shape and encoding sizes, other values
    _swap_after_admission(monkeypatch, lambda path: edited.to_parquet(path, index=False))
    with pytest.raises(release.ReleaseError, match="changed"):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert not (where / "rel").exists()


def test_rename_over_during_the_read_is_caught_by_the_copy_check(where, monkeypatch):
    source, provenance, profile = _inputs(where)
    other = where / "other.parquet"
    edited = pd.read_parquet(source)
    edited[KNEE] = 0.25
    edited.to_parquet(other, index=False)
    read = release.pq.read_table

    def rename_then_read(path, *args, **kwargs):
        other.replace(source)  # new inode at the input path while the old one is open
        return read(path, *args, **kwargs)

    monkeypatch.setattr(release.pq, "read_table", rename_then_read)
    with pytest.raises(release.ReleaseError, match="changed during release creation"):
        release.build_release(source, where / "rel", provenance, ranges_path=profile)
    assert not (where / "rel").exists()


# --- V1 ---------------------------------------------------------------------------

def test_failed_staged_unlink_rolls_back_the_publication(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    original = Path.unlink

    def unlink(self, missing_ok=False):
        if self.parent == stage and self.name == "manifest.json":
            raise PermissionError(13, "simulated busy staged file", str(self))
        return original(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError):
        release._publish_files_exclusively(stage, destination)
    monkeypatch.undo()
    assert not destination.exists() or (destination / MARKER).exists()
    assert not _bundle_verifies(destination)


def test_staged_edit_after_its_hash_check_cannot_change_the_release(where, monkeypatch):
    stage = _sealed_stage(where)
    destination = where / "rel"
    hashed = release.sha256_file

    def hash_then_edit(path):
        digest = hashed(path)
        if Path(path) == destination / "notes.txt":  # last file verified; data.bin already checked
            try:
                with open(stage / "data.bin", "ab") as handle:
                    handle.write(b"edited after its check")
            except FileNotFoundError:
                pass
        return digest

    monkeypatch.setattr(release, "sha256_file", hash_then_edit)
    release._publish_files_exclusively(stage, destination)
    monkeypatch.undo()
    assert _bundle_verifies(destination)


# --- G3, G7, G8 -------------------------------------------------------------------

def test_review_labels_do_not_claim_verification(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    raw = json.loads(provenance.read_text())
    raw["review"]["scope"] = "synthetic scope statement"
    provenance.write_text(json.dumps(raw))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    card = (tmp_path / "rel" / "README.md").read_text()
    assert manifest["declared_by_contributor"] == ["converter", "review"]
    assert manifest["review"] == raw["review"]
    assert "declared by the contributor" in card and "did not verify this review" in card
    assert "synthetic scope statement" in card
    assert not any(word in card.lower() for word in ("verified review", "approved", "certified"))


@pytest.mark.parametrize("uri,limited", [
    ("https://example.invalid/raw.zip", True),
    ("s3://bucket/raw.zip", True),
    ("doi:10.0000/synthetic", True),
    ("file:///raw.bin", False),
    ("C:\\data\\raw.bin", False),
    ("raw.bin", False),
])
def test_local_copy_limitation_follows_the_uri_scheme(tmp_path, uri, limited):
    source, provenance, profile = _inputs(tmp_path)
    raw = json.loads(provenance.read_text())
    raw["sources"][0]["uri"] = uri
    provenance.write_text(json.dumps(raw))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["sources"][0]["status"] == "verified_local"
    assert any("not downloaded" in item for item in manifest["limitations"]) is limited


def test_single_category_identity_now_releases_through_the_cli(tmp_path):
    # CORE-08 fixed the G7 root cause; the CLI must release, not refuse.
    source, provenance, profile = _inputs(tmp_path)
    frame = pd.read_parquet(source)
    frame["reference_side"] = frame["reference_side"].astype("category")
    frame.to_parquet(source, index=False)
    code = release.main([str(source), "--output-dir", str(tmp_path / "rel"),
                         "--provenance", str(provenance), "--ranges", str(profile)])
    assert code == 0 and (tmp_path / "rel" / "manifest.json").exists()


def test_assessment_type_error_fails_closed_without_a_bundle(tmp_path, monkeypatch):
    """The G7 refusal branch was removed after CORE-08; an unexpected TypeError must still leave nothing."""
    source, provenance, profile = _inputs(tmp_path)

    def broken(*args, **kwargs):
        raise TypeError("synthetic assessment type failure")

    monkeypatch.setattr(release, "assess_observations", broken)
    with pytest.raises(TypeError):
        release.main([str(source), "--output-dir", str(tmp_path / "rel"),
                      "--provenance", str(provenance), "--ranges", str(profile)])
    assert not (tmp_path / "rel").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".rel")]


def test_filtered_rows_ignore_declared_category_order(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    plain = pd.read_parquet(source)
    plain = pd.concat([plain, plain.assign(subject="A0")], ignore_index=True)  # two subjects, both pass "in"
    plain.to_parquet(source, index=False)
    release.build_release(source, tmp_path / "plain", provenance, ranges_path=profile)
    reordered = plain.copy()
    for column in ("subject", "observation_id"):
        values = sorted(reordered[column].unique(), reverse=True)
        reordered[column] = pd.Categorical(reordered[column], categories=values)
    other = tmp_path / "cat"
    other.mkdir()
    reordered.to_parquet(other / "export.parquet", index=False)
    release.build_release(other / "export.parquet", tmp_path / "categorical", provenance, ranges_path=profile)
    a = pd.read_parquet(tmp_path / "plain" / "filtered.parquet")
    b = pd.read_parquet(tmp_path / "categorical" / "filtered.parquet")
    for column in ("subject", "observation_id"):
        b[column] = b[column].astype(str)
    assert list(a.subject.unique()) == ["A0", "V1"]
    pd.testing.assert_frame_equal(a, b)


# --- applicability enforcement (reviewed/approved profiles) -------------------------

SYNTHETIC_REVIEW = "review:\n  reviewer: synthetic-profile-reviewer\n  reviewed_at: '2026-01-02T00:00:00Z'"


def _profile_text(status, tasks, review=SYNTHETIC_REVIEW):
    lines = [f"review_status: {status}",  # with a synthetic profile review record
             review, "tasks:"]
    for task, applicability in tasks.items():
        lines.append(f"  {task}:")
        if applicability is not None:
            lines.append(f"    metadata:\n      applicability: {applicability}")
        lines.append(f"    phases:\n      0:\n        {KNEE}: {{min: 0, max: 1}}\n      100:\n        {KNEE}: {{min: 0, max: 1}}")
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("status", ["reviewed", "approved"])
@pytest.mark.parametrize("tasks", [
    {"level_walking": "{}"},
    {"level_walking": None},
    {"level_walking": "{population: [synthetic]}", "incline_walking": None},
])
def test_reviewed_profile_without_applicability_for_every_task_is_refused_unread(tmp_path, monkeypatch, status, tasks):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text(status, tasks))
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="applicability"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()


def test_malformed_applicability_fails_closed(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("reviewed", {"level_walking": "[synthetic]"}))
    code = release.main([str(source), "--output-dir", str(tmp_path / "rel"),
                         "--provenance", str(provenance), "--ranges", str(profile)])
    assert code == 2 and not (tmp_path / "rel").exists()


def test_unlabelled_legacy_profile_without_applicability_still_releases_with_limitation(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("reviewed", {"level_walking": None}).replace("review_status: reviewed\n", ""))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["profile"]["review_status"] == "legacy_unspecified"
    assert any("no explicit review status" in item for item in manifest["limitations"])


# --- CORE-09: profile review record, task-only applicability, card wording ----------

POP = {"level_walking": "{population: [synthetic]}"}


@pytest.mark.parametrize("review,message", [
    ("review:\n  reviewer: someone\n  reviewed_at: 2026-01-02T00:00:00Z", "quote"),      # YAML datetime
    ("review:\n  reviewer: someone\n  reviewed_at: '2026-01-02T00:00:00'", "timezone"),  # naive
    ("review:\n  reviewer: someone\n  reviewed_at: '2026-01-02'", "timezone"),           # date only
    ("review:\n  reviewer: '   '\n  reviewed_at: '2026-01-02T00:00:00Z'", "reviewer"),
    ("review:\n  reviewer: 123\n  reviewed_at: '2026-01-02T00:00:00Z'", "reviewer"),
    ("review:\n  reviewer: yes\n  reviewed_at: '2026-01-02T00:00:00Z'", "reviewer"),
    ("review: synthetic", "review record"),
    ("", "review record"),
    ("review:\n  reviewer: someone\n  reviewed_at: '2026-01-02T00:00:00Z'\n  scope: '  '", "scope"),
])
@pytest.mark.parametrize("status", ["reviewed", "approved"])
def test_incomplete_profile_review_record_is_refused_unread(tmp_path, monkeypatch, review, message, status):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text(status, POP, review=review))
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match=message):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()


@pytest.mark.parametrize("applicability", ["{task: [level_walking]}", "{task_id: [lw]}",
                                           "{task: [level_walking], task_id: [lw]}"])
def test_task_only_applicability_is_refused(tmp_path, applicability):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("reviewed", {"level_walking": applicability}))
    with pytest.raises(release.ReleaseError, match="more than the task"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)


@pytest.mark.parametrize("applicability", ["{observation_type: [individual_cycle]}", "{reference_side: [left]}"])
def test_structural_only_applicability_is_refused(tmp_path, applicability):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("reviewed", {"level_walking": applicability}))
    with pytest.raises(release.ReleaseError, match="more than"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)


def test_non_json_profile_review_values_fail_with_a_release_error(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    review = SYNTHETIC_REVIEW + "\n  checked_on: 2026-01-03"
    profile.write_text(_profile_text("reviewed", POP, review=review))
    with pytest.raises(release.ReleaseError):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)


def test_card_labels_profile_review_as_declared_and_unverified(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("approved", POP, review=SYNTHETIC_REVIEW + "\n  scope: synthetic profile scope"))
    release.build_release(source, tmp_path / "with_scope", provenance, ranges_path=profile)
    card = (tmp_path / "with_scope" / "README.md").read_text()
    line = next(l for l in card.splitlines() if l.startswith("- Profile review status"))
    assert "as declared by the profile: approved" in line and "did not verify" in line
    assert "synthetic-profile-reviewer" in line and "synthetic profile scope" in line
    profile.write_text(_profile_text("reviewed", POP))
    manifest = release.build_release(source, tmp_path / "no_scope", provenance, ranges_path=profile)
    assert "scope: not declared" in (tmp_path / "no_scope" / "README.md").read_text()
    assert any("does not state a scope" in item for item in manifest["limitations"])


# --- CORE-10: structure/identity-only applicability, JSON-only profile review --------

@pytest.mark.parametrize("applicability", [
    "{subject: [V1]}", "{source_recording_id: [r]}", "{observation_id: [in]}",
    "{task: [level_walking], observation_type: [individual_cycle], reference_side: [left]}",
    "{subject: [V1], task_id: [lw]}",
])
@pytest.mark.parametrize("status", ["reviewed", "approved"])
def test_identity_or_structure_only_applicability_is_refused_unread(tmp_path, monkeypatch, applicability, status):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text(status, {"level_walking": applicability}))
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="more than the task"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()


def test_population_with_structure_keys_still_releases_and_filters(tmp_path):
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text(_profile_text("reviewed", {
        "level_walking": "{population: [synthetic], reference_side: [left], observation_type: [individual_cycle]}"}))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["counts"]["filtered_observations"] == 1


@pytest.mark.parametrize("review", [
    "review: 2026-01-01",                                          # scalar YAML date
    "review:\n  reviewer: x\n  checked_on: 2026-01-03",          # nested date, legacy profile
    "review:\n  reviewer: x\n  weight: .nan",                    # NaN
    "review:\n  reviewer: x\n  weight: .inf",                    # infinity
    "review:\n  reviewer: x\n  tags: !!set {a: null}",           # YAML set
    "review:\n  reviewer: x\n  blob: !!binary aGk=",             # bytes
])
def test_legacy_profile_review_must_be_json_and_is_refused_unread(tmp_path, monkeypatch, review):
    source, provenance, profile = _inputs(tmp_path)
    text = _profile_text("reviewed", POP, review=review).replace("review_status: reviewed\n", "")
    profile.write_text(text)
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="JSON values"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()


def test_unquoted_dates_outside_the_review_do_not_block_or_leak(tmp_path):
    """Only the review is copied into JSON outputs; other profile metadata stays in profile.yaml."""
    source, provenance, profile = _inputs(tmp_path)
    profile.write_text("generated: 2026-01-12 21:29:13\n" + _profile_text("reviewed", POP))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert "generated" not in json.dumps(manifest["profile"])
