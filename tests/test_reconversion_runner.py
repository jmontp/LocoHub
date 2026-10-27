"""Small orchestration checks without importing scientific libraries or sources."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contributor_tools.reconvert_recording import admit_sources, digest, resume_matches
from contributor_tools.run_reconversion_batch import inventory, summarize, worker_command
from contributor_tools import run_reconversion_batch as batch
from contributor_tools import reconvert_recording as worker


def test_inventory_preserves_source_spelling_and_excludes_reconstructions(tmp_path):
    subject = tmp_path / "TVC03"
    subject.mkdir()
    for name in ("BWA6_ik.mot", "BWA_7_ik.mot", "bwa-8_ik.mot", "BWA6_test_ik.mot"):
        (subject / name).write_text("fixture")
    (tmp_path / "TVC04").mkdir()
    plan = inventory("strokepig", tmp_path)
    assert plan["recording_count"] == 3
    assert plan["subjects_without_supported_recordings"] == ["TVC04"]
    assert plan["excluded_derived_recordings"] == ["TVC03/BWA6_test_ik.mot"]
    assert {item["recording"] for item in plan["recordings"]} == {
        "BWA6_ik.mot", "BWA_7_ik.mot", "bwa-8_ik.mot",
    }


def test_large_source_is_rejected_before_loading():
    source = SimpleNamespace(stat=lambda: SimpleNamespace(st_size=65 * 1024**2))
    with pytest.raises(MemoryError):
        admit_sources([source], memory_mib=1536, max_source_mib=64)


@pytest.mark.parametrize("changed", ["profile", "sources", "converter_code", "environment"])
def test_resume_requires_exact_scientific_inputs(tmp_path, changed):
    artifact = tmp_path / "phase.parquet"
    artifact.write_bytes(b"fixture artifact")
    existing = {
        "sources": [{"sha256": "source"}], "converter_code": [{"sha256": "code"}],
        "profile": None, "environment": {"numpy": "fixture"},
        "outputs": [{"name": artifact.name, "sha256": digest(artifact)}],
    }
    assert resume_matches(existing, existing["sources"], existing["converter_code"],
                          None, existing["environment"], tmp_path)
    current = copy.deepcopy(existing)
    current[changed] = {"changed": True}
    assert not resume_matches(existing, current["sources"], current["converter_code"],
                              current["profile"], current["environment"], tmp_path)


def test_resume_rejects_modified_output(tmp_path):
    artifact = tmp_path / "phase.parquet"
    artifact.write_bytes(b"before")
    existing = {
        "sources": [], "converter_code": [], "profile": None, "environment": {},
        "outputs": [{"name": artifact.name, "sha256": digest(artifact)}],
    }
    artifact.write_bytes(b"after")
    assert not resume_matches(existing, [], [], None, {}, tmp_path)


def test_worker_command_is_single_recording_and_resume_scoped(tmp_path):
    args = SimpleNamespace(
        dataset="gt24", source_root=tmp_path, output_root=tmp_path / "out",
        memory_mib=1536, max_source_mib=64, source="Phase3", ranges=tmp_path / "ranges.yaml",
    )
    command = worker_command(args, {"subject": "BT01", "recording": "walking"})
    assert command[command.index("--subject") + 1] == "BT01"
    assert command[command.index("--recording") + 1] == "walking"
    assert command[command.index("--ranges") + 1] == str(args.ranges)
    assert "--resume" in command


def test_schema_failures_are_quarantined_in_aggregate_counts():
    plan = {
        "recordings": [{}, {}], "source_subject_count": 1,
        "subjects_with_recordings": ["fixture"], "subjects_without_supported_recordings": [],
        "excluded_derived_recordings": [],
    }
    results = [
        {"status": "converted_unreviewed", "rows": 150, "schema_passed": True,
         "decision_counts": {"unchecked": 1}, "peak_rss_kib": 100},
        {"status": "quarantined_schema_failure", "rows": 150, "schema_passed": False,
         "decision_counts": {"invalid": 1}, "peak_rss_kib": 110},
    ]
    summary = summarize(results, plan)
    assert summary["rows"] == 300
    assert summary["schema_valid_rows"] == 150
    assert summary["status_counts"]["quarantined_schema_failure"] == 1
    assert summary["review_status"] == "unreviewed"


def test_batch_stops_after_three_consecutive_failures(tmp_path, monkeypatch):
    source = tmp_path / "raw"
    subject = source / "TVC03"
    subject.mkdir(parents=True)
    for index in range(4):
        (subject / f"BWA{index}_ik.mot").write_text("fixture")
    output = tmp_path / "converted_datasets" / "reconversion_v2" / "failure_fixture"
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    monkeypatch.setattr(batch, "available_memory_bytes", lambda: 4 * 1024**3)
    monkeypatch.setattr(batch, "ensure_storage_headroom", lambda path: 10 * 1024**3)
    monkeypatch.setattr(batch.os, "nice", lambda amount: 19)
    monkeypatch.setattr(batch.time, "sleep", lambda duration: None)
    launches = []
    def failed_worker(command, **kwargs):
        launches.append(command)
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(batch, "run_guarded_worker", failed_worker)
    monkeypatch.setattr(batch.sys, "argv", [
        "batch", "--dataset", "strokepig", "--source-root", str(source),
        "--output-root", str(output), "--run",
    ])
    assert batch.main() == 2
    assert len(launches) == 3
    summary = json.loads((output / "batch_summary.json").read_text())
    assert summary["batch_status"] == "stopped_incomplete"
    assert summary["remaining_recordings"] == 1


def test_storage_guard_rejects_small_real_volume_before_conversion(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker.platform, "release", lambda: "linux-fixture")
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)
    monkeypatch.setattr(worker.shutil, "disk_usage", lambda path: SimpleNamespace(free=3 * 1024**3))
    with pytest.raises(worker.StorageHeadroomError, match="at least 5 GiB"):
        worker.ensure_storage_headroom(tmp_path / "converted_datasets" / "reconversion_v2" / "fixture")


def test_storage_guard_does_not_trust_sparse_wsl_capacity(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker.platform, "release", lambda: "microsoft-standard-WSL2")
    monkeypatch.setattr(worker.shutil, "disk_usage", lambda path: SimpleNamespace(free=900 * 1024**3))
    with pytest.raises(worker.StorageHeadroomError, match="backing-volume"):
        worker.ensure_storage_headroom(tmp_path / "converted_datasets" / "reconversion_v2" / "fixture")


def test_storage_rejection_precedes_import_and_output_creation(tmp_path, monkeypatch):
    output = tmp_path / "must_not_exist"
    def reject(path):
        raise worker.StorageHeadroomError("fixture capacity exhausted")
    monkeypatch.setattr(worker, "ensure_storage_headroom", reject)
    monkeypatch.setattr(worker, "load_converter", lambda path: pytest.fail("Scientific imports must not start"))
    with pytest.raises(worker.StorageHeadroomError):
        worker.convert(SimpleNamespace(output_root=output))
    assert not output.exists()


def test_expanded_memory_budget_keeps_total_cap_and_reserve(monkeypatch):
    gib = 1024**3
    monkeypatch.setattr(worker, 'memory_snapshot', lambda: {'MemTotal':16*gib, 'MemAvailable':12*gib})
    worker.ensure_memory_headroom(9216)
    with pytest.raises(worker.MemoryHeadroomError):
        worker.ensure_memory_headroom(11264)
    monkeypatch.setattr(worker, 'memory_snapshot', lambda: {'MemTotal':16*gib, 'MemAvailable':10*gib})
    with pytest.raises(worker.MemoryHeadroomError, match='reserve'):
        worker.ensure_memory_headroom(9216)
    monkeypatch.setattr(worker, 'memory_snapshot', lambda: {'MemTotal':8*gib, 'MemAvailable':8*gib})
    with pytest.raises(worker.MemoryHeadroomError, match='80%'):
        worker.ensure_memory_headroom(7168)


def test_runtime_pressure_terminates_only_owned_worker_group(tmp_path, monkeypatch):
    import signal
    process = SimpleNamespace(pid=12345, returncode=None)
    process.poll = lambda: process.returncode
    def wait(**kwargs):
        process.returncode = -signal.SIGTERM
        return process.returncode
    process.wait = wait
    def launch(command, **kwargs):
        assert kwargs['start_new_session'] is True
        return process
    killed=[]
    monkeypatch.setattr(batch.subprocess, 'Popen', launch)
    monkeypatch.setattr(batch, 'available_memory_bytes', lambda:1024**3)
    monkeypatch.setattr(batch.os, 'killpg', lambda pid,sig:killed.append((pid,sig)))
    with pytest.raises(worker.MemoryHeadroomError):
        batch.run_guarded_worker(['fixture'],stdout=None,timeout=10,output_root=tmp_path)
    assert killed==[(12345,signal.SIGTERM)]
    assert process.returncode is not None
