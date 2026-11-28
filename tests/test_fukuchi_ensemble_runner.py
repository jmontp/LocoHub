"""Pure orchestration fixtures; no numerical imports or worker execution."""
import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).resolve().parents[1]/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py'
SPEC = importlib.util.spec_from_file_location('fukuchi_runner', PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_pinned_plan_mutation_rejected(tmp_path, monkeypatch):
    plan = tmp_path/'plan.json'
    plan.write_text('{}')
    monkeypatch.setattr(RUNNER, 'PLAN', plan)
    with pytest.raises(ValueError, match='hash mismatch'):
        RUNNER.verified_plan()


@pytest.mark.parametrize('windows,linux,c,s,prelaunch', [
    (2815, 4096, 2, 6, True), (2047, 4096, 2, 6, False),
    (4096, 2047, 2, 6, False), (4096, 4096, .99, 6, False),
    (4096, 4096, 2, 4.99, False)])
def test_resource_reserves_fail_closed(monkeypatch, windows, linux, c, s, prelaunch):
    from types import SimpleNamespace
    monkeypatch.setattr(RUNNER, 'windows_available_mib', lambda **kw: windows)
    monkeypatch.setattr(RUNNER, 'linux_available_mib', lambda: linux)
    monkeypatch.setattr(RUNNER.shutil, 'disk_usage', lambda path: SimpleNamespace(free=(c if path == '/mnt/c' else s)*1024**3))
    with pytest.raises((MemoryError, OSError)):
        RUNNER.check_resources(prelaunch=prelaunch)


def test_runtime_and_startup_thresholds_are_distinct(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(RUNNER, 'windows_available_mib', lambda **kw: 2300)
    monkeypatch.setattr(RUNNER, 'linux_available_mib', lambda: 2048)
    monkeypatch.setattr(RUNNER.shutil, 'disk_usage', lambda path: SimpleNamespace(free=5*1024**3))
    assert RUNNER.check_resources()['windows_available_mib'] == 2300
    with pytest.raises(MemoryError):
        RUNNER.check_resources(prelaunch=True)


def test_cleanup_targets_only_owned_group(monkeypatch):
    from types import SimpleNamespace
    calls = []
    monkeypatch.setattr(RUNNER.os, 'killpg', lambda pid, sig: calls.append((pid, sig)))
    child = SimpleNamespace(pid=12345, wait=lambda **kw: 0)
    RUNNER.stop_owned_group(child)
    assert calls == [(12345, RUNNER.signal.SIGTERM), (12345, RUNNER.signal.SIGKILL)]
