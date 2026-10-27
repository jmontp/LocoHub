"""End-to-end release tests use only two synthetic 150-row observations."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from contributor_tools import build_dataset_release as release


SIGNAL = "knee_flexion_angle_ipsi_rad"


@pytest.fixture
def release_inputs(tmp_path):
    data = pd.DataFrame({
        "subject": "S01", "source_recording_id": "fixture.csv",
        "observation_id": np.repeat(["pass", "fail"], 150),
        "reference_side": "left", "observation_type": "individual_cycle",
        "task": "level_walking", "task_id": "level_1_m_s", "task_info": "{}",
        "phase_ipsi": np.tile(np.linspace(0, 100, 150), 2),
        SIGNAL: np.repeat([0.5, 2.0], 150),
    })
    raw = tmp_path / "fixture.csv"
    data.to_csv(raw, index=False)
    source = tmp_path / "input.parquet"
    data.sample(frac=1, random_state=7).to_parquet(source, index=False)
    profile = tmp_path / "ranges.yaml"
    profile.write_text(
        f"version: '2.0'\ntasks:\n  level_walking:\n    phases:\n"
        f"      0:\n        {SIGNAL}:\n          min: 0\n          max: 1\n"
        f"      100:\n        {SIGNAL}:\n          min: 0\n          max: 1\n"
    )
    provenance = tmp_path / "source.json"
    provenance.write_text(json.dumps({
        "dataset_id": "synthetic-fixture", "release_id": "test-v1",
        "sources": [{"uri": "fixture.csv", "path": "fixture.csv", "sha256": release.sha256_file(raw)}],
        "converter": {"name": "test-fixture", "revision": "fixture-v1"},
        "review": {"reviewer": "automated-test-fixture", "reviewed_at": "2026-01-01T00:00:00Z"},
    }))
    return source, profile, provenance


def test_release_preserves_full_export_and_filters_whole_identified_observations(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance, ranges_path=profile)
    assert release.sha256_file(source) == release.sha256_file(output / "full.parquet")
    filtered = pd.read_parquet(output / "filtered.parquet")
    assert len(filtered) == 150 and set(filtered.observation_id) == {"pass"}
    assert filtered.phase_ipsi.tolist() == np.linspace(0, 100, 150).tolist()
    ledger = pd.read_parquet(output / "exclusions.parquet")
    assert ledger.observation_id.tolist() == ["fail"]
    assert ledger.status.tolist() == ["failed"]
    assert manifest["counts"]["full_observations"] == 2
    assert manifest["counts"]["filtered_observations"] == 1
    assert manifest["sources"][0]["status"] == "verified_local"
    assert manifest["profile"]["sha256"] == release.sha256_file(profile)
    assert manifest["profile"]["review_status"] == "legacy_unspecified"
    card = (output / "README.md").read_text()
    assert "Participants: 1" in card
    assert "individual_cycle: 2" in card
    assert "Filtered export: 1 observations, 150 rows" in card
    assert "level_walking | 2 | 1" in card
    assert "README.md" in manifest["artifacts"]
    for name, artifact in manifest["artifacts"].items():
        assert artifact["sha256"] == release.sha256_file(output / name)
    assert (output / "manifest.sha256").read_text().startswith(release.sha256_file(output / "manifest.json"))
    assert not list(tmp_path.glob(".release.staging-*"))


def test_existing_release_is_immutable(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    output = tmp_path / "release"
    release.build_release(source, output, provenance, ranges_path=profile)
    manifest_hash = release.sha256_file(output / "manifest.json")
    with pytest.raises(release.ReleaseError, match="overwritten"):
        release.build_release(source, output, provenance, ranges_path=profile)
    assert release.sha256_file(output / "manifest.json") == manifest_hash


def test_no_profile_makes_empty_filtered_artifact_not_a_quality_pass(release_inputs, tmp_path):
    source, _, provenance = release_inputs
    output = tmp_path / "release"
    manifest = release.build_release(source, output, provenance)
    assert manifest["counts"]["filtered_rows"] == 0
    assert manifest["counts"]["observation_statuses"]["unchecked"] == 2
    filtered = pd.read_parquet(output / "filtered.parquet")
    assert len(filtered) == 0 and SIGNAL in filtered
    assert len(pd.read_parquet(output / "exclusions.parquet")) == 2


def test_failure_during_write_never_publishes_partial_release(release_inputs, tmp_path, monkeypatch):
    source, profile, provenance = release_inputs
    output = tmp_path / "release"

    def fail(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(release.pq, "write_table", fail)
    with pytest.raises(OSError, match="simulated"):
        release.build_release(source, output, provenance, ranges_path=profile)
    assert not output.exists()
    assert not list(tmp_path.glob(".release.*"))


def test_admission_rejects_input_before_eager_read(release_inputs, tmp_path, monkeypatch):
    source, profile, provenance = release_inputs

    def unexpected_read(*args, **kwargs):
        raise AssertionError("admission must run before reading")

    monkeypatch.setattr(release.pq, "read_table", unexpected_read)
    with pytest.raises(release.ReleaseError, match="before loading"):
        release.build_release(
            source, tmp_path / "release", provenance, ranges_path=profile, max_input_rows=100
        )
    assert not (tmp_path / "release").exists()


def test_unidentified_legacy_export_cannot_be_published(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    data = pd.read_parquet(source).drop(columns="source_recording_id")
    data.to_parquet(source, index=False)
    with pytest.raises(release.ReleaseError, match="unreviewed"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert not (tmp_path / "release").exists()


def test_source_hash_mismatch_fails_before_publication(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    raw = json.loads(provenance.read_text())
    raw["sources"][0]["sha256"] = "0" * 64
    provenance.write_text(json.dumps(raw))
    with pytest.raises(release.ReleaseError, match="checksum"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert not (tmp_path / "release").exists()


def test_remote_source_hash_is_explicitly_declared_not_verified(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    raw = json.loads(provenance.read_text())
    raw["sources"][0].pop("path")
    raw["sources"][0]["uri"] = "https://example.invalid/source.csv"
    provenance.write_text(json.dumps(raw))
    manifest = release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert manifest["sources"][0]["status"] == "contributor_declared"
    assert any("not downloaded" in limitation for limitation in manifest["limitations"])


def test_cli_builds_headless_release(release_inputs, tmp_path, capsys):
    source, profile, provenance = release_inputs
    code = release.main([
        str(source), "--output-dir", str(tmp_path / "release"),
        "--provenance", str(provenance), "--ranges", str(profile),
    ])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["counts"]["filtered_rows"] == 150


def test_draft_profile_cannot_publish(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    profile.write_text("review_status: draft\n" + profile.read_text())
    with pytest.raises(release.ReleaseError, match="review_status='draft'"):
        release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert not (tmp_path / "release").exists()


def test_reviewed_profile_status_is_preserved(release_inputs, tmp_path):
    source, profile, provenance = release_inputs
    profile.write_text("review_status: reviewed\n" + profile.read_text())
    result = release.build_release(source, tmp_path / "release", provenance, ranges_path=profile)
    assert result["profile"]["review_status"] == "reviewed"
    assert not any("legacy profile" in limitation for limitation in result["limitations"])
