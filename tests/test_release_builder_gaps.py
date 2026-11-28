"""Release-builder gap fixes (CORE-06, CORE-09) on small synthetic fixtures.

Every array is synthetic: 150-sample phase observations with constant knee
values, 0.5 rad inside and 2.0 rad outside a synthetic [0, 1] profile range.
No research dataset is read.
"""

import json
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from contributor_tools import build_dataset_release as release


KNEE = "knee_flexion_angle_ipsi_rad"


def _cycles(*observations) -> pd.DataFrame:
    return pd.concat([pd.DataFrame({
        "subject": "P1", "source_recording_id": "rec", "observation_id": name,
        "reference_side": "left", "observation_type": "individual_cycle",
        "task": "level_walking", "task_id": "synthetic", "task_info": '{"population": "synthetic"}',
        "phase_ipsi": np.linspace(0, 100, 150), KNEE: np.full(150, value),
    }) for name, value in observations], ignore_index=True)


# Synthetic applicability and profile review record; neither describes a real population or reviewer.
APPLICABILITY = "    metadata: {applicability: {population: [synthetic]}}\n"
PROFILE_REVIEW = "review: {reviewer: synthetic-profile-reviewer, reviewed_at: '2026-01-02T00:00:00Z'}\n"
_OBSERVATIONS = (("in", 0.5), ("out", 2.0))


def _inputs(directory, review):
    source = directory / "export.parquet"
    _cycles(*_OBSERVATIONS).to_parquet(source, index=False)
    raw = directory / "raw.bin"
    raw.write_bytes(b"synthetic source bytes")
    profile = directory / "p.yaml"
    profile.write_text(
        "review_status: reviewed\n" + PROFILE_REVIEW + "tasks:\n  level_walking:\n" + APPLICABILITY + "    phases:\n"
        f"      0:\n        {KNEE}: {{min: 0, max: 1}}\n      100:\n        {KNEE}: {{min: 0, max: 1}}\n"
    )
    provenance = directory / "provenance.json"
    provenance.write_text(json.dumps({
        "dataset_id": "synthetic-core06", "release_id": "v1",
        "sources": [{"uri": "raw.bin", "path": "raw.bin", "sha256": release.sha256_file(raw)}],
        "converter": {"name": "synthetic-converter", "revision": "r1"},
        "review": review,
    }))
    return source, provenance, profile


REVIEW = {"reviewer": "synthetic-reviewer", "reviewed_at": "2026-01-01T00:00:00Z"}


# --- G3: review scope and declarations ----------------------------------------

def test_missing_review_scope_is_labelled_not_silent(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert any("declares no scope" in item for item in manifest["limitations"])
    card = (tmp_path / "rel" / "README.md").read_text()
    assert "scope: not declared" in card
    assert "declares no scope" in card


def test_declared_review_scope_is_rendered_and_review_is_labelled_a_declaration(tmp_path):
    source, provenance, profile = _inputs(tmp_path, {**REVIEW, "scope": "synthetic identity checks"})
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["review"]["scope"] == "synthetic identity checks"
    assert manifest["declared_by_contributor"] == ["converter", "review"]
    assert not any("declares no scope" in item for item in manifest["limitations"])
    card = (tmp_path / "rel" / "README.md").read_text()
    assert "declared by the contributor" in card
    assert "scope: synthetic identity checks" in card


@pytest.mark.parametrize("scope", ["", "   ", ["list"], 3])
def test_malformed_review_scope_is_refused(tmp_path, scope):
    source, provenance, profile = _inputs(tmp_path, {**REVIEW, "scope": scope})
    with pytest.raises(release.ReleaseError, match="review.scope"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()


# --- G4: a replaced input is never read eagerly ---------------------------------

@pytest.mark.parametrize("replace", ["in_place", "renamed_over"])
def test_input_replaced_after_admission_is_refused_before_any_eager_read(tmp_path, monkeypatch, replace):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    larger = _cycles(*[(f"c{i}", 0.5) for i in range(8)])
    admit = release._admit_input
    reads = []

    def admit_then_replace(path, **kwargs):
        admitted = admit(path, **kwargs)
        assert admitted["rows"] == 300
        if replace == "in_place":
            larger.to_parquet(path, index=False)
        else:
            other = tmp_path / "other.parquet"
            larger.to_parquet(other, index=False)
            other.replace(path)
        return admitted

    def record(name):
        def read(*args, **kwargs):
            reads.append(name)
            raise AssertionError("an unadmitted input was read")
        return read

    monkeypatch.setattr(release, "_admit_input", admit_then_replace)
    monkeypatch.setattr(release.pq, "read_table", record("read_table"))
    monkeypatch.setattr(pq.ParquetFile, "read", record("ParquetFile.read"))
    with pytest.raises(release.ReleaseError, match="changed after admission"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert reads == []
    assert not (tmp_path / "rel").exists()


def test_input_edited_during_the_read_is_rejected(tmp_path, monkeypatch):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    original = release.pq.read_table

    def read_then_edit(where, **kwargs):
        table = original(where, **kwargs)
        with open(source, "r+b") as handle:  # same inode, same size, one byte changed
            handle.seek(8)
            byte = handle.read(1)
            handle.seek(8)
            handle.write(bytes([byte[0] ^ 0xFF]))
        return table

    monkeypatch.setattr(release.pq, "read_table", read_then_edit)
    with pytest.raises(release.ReleaseError, match="changed while it was being read"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()


# --- G7: categorical identities ---------------------------------------------------

def _plain_and_categorical(tmp_path, column, categories=None):
    """Build the same synthetic export twice: plain strings, then ``column`` categorical."""
    results = {}
    for encoding in ("plain", "categorical"):
        directory = tmp_path / encoding
        directory.mkdir()
        source, provenance, profile = _inputs(directory, dict(REVIEW))
        frame = pd.read_parquet(source)
        if encoding == "categorical":
            frame[column] = pd.Categorical(frame[column], categories=categories)
        frame.to_parquet(source, index=False)
        manifest = release.build_release(source, directory / "rel", provenance, ranges_path=profile)
        results[encoding] = (manifest, pd.read_parquet(directory / "rel" / "filtered.parquet"))
    return results


def test_single_category_identity_releases_like_plain_strings(tmp_path):
    results = _plain_and_categorical(tmp_path, "source_recording_id")
    (plain, plain_rows), (categorical, categorical_rows) = results["plain"], results["categorical"]
    assert isinstance(categorical_rows["source_recording_id"].dtype, pd.CategoricalDtype)
    assert categorical["counts"] == plain["counts"]
    assert categorical["counts"]["filtered_rows"] == 150
    assert categorical_rows.astype({"source_recording_id": object}).equals(plain_rows)


def test_multi_category_identity_still_releases(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    frame = pd.read_parquet(source)
    frame["observation_id"] = frame["observation_id"].astype("category")
    frame.to_parquet(source, index=False)
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["counts"]["filtered_rows"] == 150
    assert manifest["counts"]["filtered_observations"] == 1


def test_filtered_row_order_ignores_categorical_category_order(tmp_path, monkeypatch):
    # Two passing observations whose categories are declared in reverse
    # alphabetical order; plain strings sort "a_in" before "b_in".
    monkeypatch.setattr(sys.modules[__name__], "_OBSERVATIONS", (("b_in", 0.5), ("a_in", 0.5), ("c_out", 2.0)))
    results = _plain_and_categorical(tmp_path, "observation_id", categories=["c_out", "b_in", "a_in"])
    plain_order = results["plain"][1]["observation_id"].tolist()
    categorical_order = results["categorical"][1]["observation_id"].astype(object).tolist()
    assert plain_order == ["a_in"] * 150 + ["b_in"] * 150
    assert categorical_order == plain_order


# --- reviewed profiles must declare applicability ---------------------------------

@pytest.mark.parametrize("status", ["reviewed", "approved"])
def test_labelled_profile_without_applicability_is_refused(tmp_path, status):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(
        profile.read_text()
        .replace("review_status: reviewed", f"review_status: {status}")
        .replace(APPLICABILITY, "")
    )
    with pytest.raises(release.ReleaseError, match="applicability block.*level_walking"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()
    assert not list(tmp_path.glob(".rel.*"))


def test_unlabelled_legacy_profile_without_applicability_still_releases_with_limitation(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace("review_status: reviewed\n", "").replace(APPLICABILITY, ""))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["profile"]["review_status"] == "legacy_unspecified"
    assert any("no inferred profile" in item for item in manifest["limitations"])


# --- CORE-09 G2 default: reviewed/approved profiles record who and when ------------

def _spy_reads(monkeypatch):
    calls = []
    read = release.pq.read_table

    def spy(source, *args, **kwargs):
        calls.append(str(source))
        return read(source, *args, **kwargs)

    monkeypatch.setattr(release.pq, "read_table", spy)
    return calls


@pytest.mark.parametrize("status", ["reviewed", "approved"])
@pytest.mark.parametrize("record", [
    "",  # no review block
    "review: {reviewed_at: '2026-01-02T00:00:00Z'}\n",
    "review: {reviewer: '  ', reviewed_at: '2026-01-02T00:00:00Z'}\n",
    "review: {reviewer: synthetic-profile-reviewer}\n",
    "review: {reviewer: synthetic-profile-reviewer, reviewed_at: '2026-01-02T00:00:00'}\n",
    "review: {reviewer: synthetic-profile-reviewer, reviewed_at: 2026-01-02T00:00:00Z}\n",
    "review: {reviewer: synthetic-profile-reviewer, reviewed_at: 'yesterday'}\n",
    "review: {reviewer: synthetic-profile-reviewer, reviewed_at: '2026-01-02T00:00:00Z', scope: ''}\n",
    "review: synthetic-profile-reviewer\n",
], ids=["absent", "no_reviewer", "blank_reviewer", "no_date", "naive_date", "yaml_timestamp",
        "not_a_date", "blank_scope", "not_a_mapping"])
def test_labelled_profile_without_a_review_record_is_refused_unread(tmp_path, monkeypatch, status, record):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(
        profile.read_text().replace("review_status: reviewed", f"review_status: {status}").replace(PROFILE_REVIEW, record)
    )
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="profile review"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()


def test_profile_review_scope_is_optional_but_labelled(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["profile"]["review"] == {
        "reviewer": "synthetic-profile-reviewer", "reviewed_at": "2026-01-02T00:00:00Z"
    }
    assert any("profile's review does not state a scope" in item for item in manifest["limitations"])
    scoped = PROFILE_REVIEW.replace("}", ", scope: synthetic ranges only}")
    profile.write_text(profile.read_text().replace(PROFILE_REVIEW, scoped))
    manifest = release.build_release(source, tmp_path / "rel2", provenance, ranges_path=profile)
    assert manifest["profile"]["review"]["scope"] == "synthetic ranges only"
    assert not any("profile's review does not state a scope" in item for item in manifest["limitations"])


# --- CORE-09 R2: applicability must name more than the task -------------------------

@pytest.mark.parametrize("block", [
    "{task: [level_walking]}", "{task_id: [synthetic]}", "{task: [level_walking], task_id: [synthetic]}",
])
def test_applicability_naming_only_the_task_is_refused(tmp_path, block):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace(
        APPLICABILITY, f"    metadata: {{applicability: {block}}}\n"
    ))
    with pytest.raises(release.ReleaseError, match="more than the task"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()


def test_applicability_with_task_and_population_releases(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace(
        APPLICABILITY, "    metadata: {applicability: {task: [level_walking], population: [synthetic]}}\n"
    ))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["counts"]["filtered_observations"] == 1


# --- CORE-09 R3: the card labels the profile's review status as its own claim -------

def test_card_labels_profile_review_status_as_the_profiles_claim(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    card = (tmp_path / "rel" / "README.md").read_text()
    assert (
        "- Profile review status, as declared by the profile: reviewed "
        "(synthetic-profile-reviewer at 2026-01-02T00:00:00Z; scope: not declared). "
        "The builder did not verify this review." in card
    )
    assert "- Profile review status: " not in card


# --- CORE-10: structural-only applicability and non-JSON profile reviews ------------

@pytest.mark.parametrize("block", [
    "{observation_type: [individual_cycle], reference_side: [left]}",
    "{task: [level_walking], observation_type: [individual_cycle]}",
])
def test_structural_only_applicability_combinations_are_refused(tmp_path, block):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace(
        APPLICABILITY, f"    metadata: {{applicability: {block}}}\n"
    ))
    with pytest.raises(release.ReleaseError, match="more than the task or observation structure"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()


def test_population_with_structural_keys_releases(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace(
        APPLICABILITY,
        "    metadata: {applicability: {population: [synthetic], reference_side: [left]}}\n",
    ))
    manifest = release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert manifest["counts"]["filtered_observations"] == 1


@pytest.mark.parametrize("labelled", [True, False], ids=["reviewed", "legacy"])
def test_unquoted_date_in_profile_review_is_refused_cleanly(tmp_path, monkeypatch, labelled):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    text = profile.read_text().replace(PROFILE_REVIEW, PROFILE_REVIEW.replace("}", ", checked_on: 2026-01-03}"))
    if not labelled:
        text = text.replace("review_status: reviewed\n", "")
    profile.write_text(text)
    calls = _spy_reads(monkeypatch)
    with pytest.raises(release.ReleaseError, match="quote dates"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert calls == [] and not (tmp_path / "rel").exists()
    assert not list(tmp_path.glob(".rel.*"))


def test_unquoted_reviewed_at_still_needs_quotes(tmp_path):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace("reviewed_at: '2026-01-02T00:00:00Z'", "reviewed_at: 2026-01-02T00:00:00Z"))
    with pytest.raises(release.ReleaseError, match="quote timestamps"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)


@pytest.mark.parametrize("block", [
    "{subject: [P1]}", "{source_recording_id: [rec]}", "{observation_id: [in]}",
    "{subject: [P1], source_recording_id: [rec], observation_id: [in], reference_side: [left]}",
])
def test_identity_only_applicability_is_refused(tmp_path, block):
    source, provenance, profile = _inputs(tmp_path, dict(REVIEW))
    profile.write_text(profile.read_text().replace(
        APPLICABILITY, f"    metadata: {{applicability: {block}}}\n"
    ))
    with pytest.raises(release.ReleaseError, match="more than the task or observation structure"):
        release.build_release(source, tmp_path / "rel", provenance, ranges_path=profile)
    assert not (tmp_path / "rel").exists()
