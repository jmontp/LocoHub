"""Independent verification tests for contributor_tools/guarded_launcher.py.

Written by the UM21-T02 launcher reviewer, separately from
tests/test_guarded_launcher.py. Every job is a dummy command (sleep, sh,
python -c) in a pytest temporary directory. Censuses, memory and disk are
synthetic unless a test says it reads the real /proc (read only). Nothing here
reads research data, runs powershell, or signals a process this test did not
start itself.

Tests marked xfail(strict=True) encode required fixes from
docs/maintainers/handoffs/UM21-T02-launcher-verify.json. They must flip to
passing (and the marker be removed) once the fix lands. Round-1 markers were
removed by the worker in round 2 (teardown-only change accepted by the reviewer).
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from contributor_tools import guarded_launcher as gl

PY = sys.executable
REPO = Path(__file__).resolve().parents[1]
# PM-01 envelope values, copied by hand from
# docs/quality/audits/pm01-um21-tread-pilot-handoff.json.
PM01 = {"timeout": 3600, "kill_after": 30, "poll": 15, "disk_s": 5 * 1024, "disk_c": 1024,
        "start_linux": 3584, "start_windows": 2816, "run_linux": 2048, "run_windows": 2048}


class SynthHost(gl.Host):
    """Real /proc identity; synthetic census/memory/disk unless overridden."""

    def __init__(self, mem=None, win_mem=None, token=None):
        super().__init__()
        self.mem = list(mem or [8192])
        self.win_mem = list(win_mem or [8192])
        self.token = token  # argv token that marks a "worker" in the synthetic Linux census

    def _pop(self, seq):
        value = seq.pop(0) if len(seq) > 1 else seq[0]
        if isinstance(value, Exception):
            raise value
        return value

    def linux_census(self):
        workers = []
        if self.token:
            for pid in self._pids():
                try:
                    argv = (self.proc / str(pid) / "cmdline").read_bytes().split(b"\0")
                except OSError:
                    continue
                if self.token.encode() in argv:
                    workers.append({"pid": pid, "cmdline": "synthetic token"})
        return {"checked_at_utc": gl.utcnow(), "boot_id": self.boot_id(), "process_count": 1,
                "excluded_self_and_ancestors": [], "workers": workers}

    def windows_census(self):
        return {"checked_at_utc": gl.utcnow(), "last_boot_utc": "synthetic", "process_count": 1,
                "free_physical_mib": self._pop(list(self.win_mem)), "workers": []}

    def linux_mem_available_mib(self):
        return self._pop(self.mem)

    def windows_free_mib(self):
        return self._pop(self.win_mem)

    def disk_free_mib(self, path):
        return 50_000


def spec_for(tmp_path, command, **kw):
    code = tmp_path / "bound.txt"
    code.write_text("synthetic binding\n")
    spec = {"job_id": "verify_synthetic", "command": command, "cwd": str(tmp_path),
            "output_root": "job_out", "receipt_path": "rc/job.json",
            "bindings": {"bound.txt": hashlib.sha256(b"synthetic binding\n").hexdigest()},
            "timeout_seconds": 10, "kill_after_seconds": 1, "poll_seconds": 0.1,
            "disk_admission": [{"path": str(tmp_path), "min_free_mib": PM01["disk_s"]}],
            "startup_memory_mib": {"linux": PM01["start_linux"], "windows": PM01["start_windows"]},
            "runtime_memory_mib": {"linux": PM01["run_linux"], "windows": PM01["run_windows"]}}
    spec.update(kw)
    return spec


def group_alive(pgid, start_ticks=None):
    """Read-only /proc scan for live members of a process group."""
    host = gl.Host()
    return [m for m in host.group_members(pgid) if m["state"] != "Z"]


# ------------------------------------------------------------- envelope ---

def test_child_runs_in_new_session_at_idle_priority_single_threaded(tmp_path):
    probe = [PY, "-c", (
        "import os, subprocess, json;"
        "io = subprocess.run(['ionice', '-p', str(os.getpid())], capture_output=True, text=True).stdout.strip();"
        "print(json.dumps({'pgid': os.getpgid(0), 'sid': os.getsid(0), 'nice': os.nice(0), 'io': io,"
        "'env': {k: os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS',"
        "'MKL_NUM_THREADS','ARROW_NUM_THREADS','NUMEXPR_NUM_THREADS']}}))")]
    r = gl.run_job(spec_for(tmp_path, probe), SynthHost())
    seen = json.loads((tmp_path / "rc/job.log").read_text())
    leader = r["process_identity"]["leader_pid"]
    assert seen["pgid"] == seen["sid"] == leader == r["process_identity"]["pgid"]
    assert seen["nice"] == 19 and seen["io"] == "idle"
    assert set(seen["env"].values()) == {"1"}
    assert r["process_identity"]["argv"][:3] == ["timeout", "--signal=TERM", "--kill-after=1s"]


def test_running_receipt_with_identity_exists_while_job_runs(tmp_path):
    peek = [PY, "-c", "import json, os, time; time.sleep(0.5);"
                      "r = json.load(open('rc/job.json'));"
                      "print(r['status'], r['process_identity']['pgid'] == os.getpgid(0))"]
    r = gl.run_job(spec_for(tmp_path, peek), SynthHost())
    assert (tmp_path / "rc/job.log").read_text().split() == ["running", "True"]
    assert r["status"] == "completed"


# --------------------------------------------------------- admission edges ---

@pytest.mark.parametrize("linux, windows, admitted", [
    (PM01["start_linux"], PM01["start_windows"], True),        # equality passes (>=)
    (PM01["start_linux"] - 0.1, PM01["start_windows"], False),
    (PM01["start_linux"], PM01["start_windows"] - 0.1, False),
])
def test_startup_reserve_boundaries(tmp_path, linux, windows, admitted):
    r = gl.run_job(spec_for(tmp_path, ["true"]), SynthHost(mem=[linux], win_mem=[windows]),
                   dry_run=True)
    assert (r["status"] == "preflight_passed") is admitted
    assert not (tmp_path / "rc").exists()  # dry run writes nothing


def test_unreadable_linux_startup_memory_launches_nothing(tmp_path):
    host = SynthHost(mem=[RuntimeError("synthetic: meminfo unreadable")])
    with pytest.raises(RuntimeError):
        gl.run_job(spec_for(tmp_path, ["touch", "launched"]), host)
    assert not (tmp_path / "launched").exists() and not (tmp_path / "rc/job.log").exists()


@pytest.mark.parametrize("payload", [
    '{"processes": [], "free_physical_kib": 0, "last_boot_utc": "x"}',  # null -> [long] 0
    'not json', '{"processes": []}'])
def test_real_windows_parser_fails_closed(tmp_path, payload):
    class PS(SynthHost):
        windows_census = gl.Host.windows_census

        def _powershell(self, script, timeout=120):
            return payload

    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), PS())
    assert r["status"] == "refused_precondition" and r["launched"] is False
    assert not (tmp_path / "launched").exists()


def test_unreadable_linux_runtime_memory_is_a_breach(tmp_path):
    host = SynthHost(mem=[8192, RuntimeError("synthetic")])
    r = gl.run_job(spec_for(tmp_path, ["sleep", "20"]), host)
    assert r["status"] == "stopped_resource_guard"
    assert r["runtime_guard"]["breach"]["readings_mib"]["linux"] is None
    assert r["checks"]["cleanup_proven"] is True


# ----------------------------------------------------------- exit codes ---

def test_untimed_sigkill_is_failed_not_timed_out(tmp_path):
    # Stands in for an OOM kill well before the timeout.
    r = gl.run_job(spec_for(tmp_path, [PY, "-c", "import os; os.kill(os.getpid(), 9)"]), SynthHost())
    assert r["status"] == "failed" and r["exit_code"] in (-9, 137)


def test_job_exit_124_before_timeout_is_failed(tmp_path):
    r = gl.run_job(spec_for(tmp_path, [PY, "-c", "raise SystemExit(124)"]), SynthHost())
    assert r["status"] == "failed" and r["exit_code"] == 124


def test_term_honouring_timeout_reports_124(tmp_path):
    r = gl.run_job(spec_for(tmp_path, ["sleep", "20"], timeout_seconds=1), SynthHost())
    assert r["status"] == "timed_out" and r["exit_code"] == 124
    assert r["checks"]["cleanup_proven"] is True


# ------------------------------------------------------- process safety ---

def test_stop_never_signals_the_launchers_own_group(tmp_path):
    hits = []
    old = {s: signal.signal(s, lambda n, f: hits.append(n)) for s in (signal.SIGTERM, signal.SIGHUP)}
    sibling = subprocess.Popen(["sleep", "30"])  # same process group as pytest
    try:
        breach = SynthHost(mem=[8192, 10])
        r = gl.run_job(spec_for(tmp_path, ["sh", "-c", "sleep 30 & sleep 30"]), breach)
        r2 = gl.run_job(spec_for(tmp_path, ["sh", "-c", "sleep 30 & exit 0"],
                                 output_root="o2", receipt_path="rc/job2.json"), SynthHost())
        assert r["status"] == "stopped_resource_guard" and r2["orphans_at_leader_exit"]
        assert hits == [] and sibling.poll() is None
        for rec in (r, r2):
            assert rec["process_identity"]["pgid"] != os.getpgid(0)
            assert not group_alive(rec["process_identity"]["pgid"])
    finally:
        sibling.kill()
        sibling.wait()
        for s, h in old.items():
            signal.signal(s, h)


def test_term_ignoring_job_gets_term_then_kill_after_grace(tmp_path):
    stubborn = [PY, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"]
    t0 = time.monotonic()
    r = gl.run_job(spec_for(tmp_path, stubborn, kill_after_seconds=2), SynthHost(mem=[8192, 10]))
    took = time.monotonic() - t0
    assert [a["signal"] for a in r["stop_actions"]][:1] == ["SIGTERM"]
    assert 2 <= took < 10
    assert r["status"] == "stopped_resource_guard" and r["checks"]["cleanup_proven"] is True


def test_killed_launcher_leaves_job_bounded_by_timeout(tmp_path):
    """If the launcher is SIGKILLed, the job is unguarded but timeout still ends it."""
    spec = spec_for(tmp_path, ["sleep", "60"], timeout_seconds=2, kill_after_seconds=1)
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    driver = (
        "import json, sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "from contributor_tools import guarded_launcher as gl\n"
        "from test_guarded_launcher_verify import SynthHost\n"
        "gl.run_job(json.load(open(%r)), SynthHost())\n"
    ) % (str(REPO), str(REPO / "tests"), str(tmp_path / "spec.json"))
    proc = subprocess.Popen([PY, "-c", driver], start_new_session=True)
    receipt = tmp_path / "rc/job.json"
    try:
        deadline = time.monotonic() + 10
        while not receipt.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        ident = json.loads(receipt.read_text())["process_identity"]
    finally:
        proc.kill()  # our own driver process
        proc.wait()
    end = time.monotonic() + spec["timeout_seconds"] + spec["kill_after_seconds"] + 5
    while group_alive(ident["pgid"]) and time.monotonic() < end:
        time.sleep(0.1)
    assert not group_alive(ident["pgid"])
    assert json.loads(receipt.read_text())["status"] == "running"  # receipt never finalised


# --------------------------------------------- required fixes (xfail strict) ---

@pytest.mark.parametrize("override", [
    {"startup_memory_mib": {"linux": 1, "windows": 1}},
    {"runtime_memory_mib": {"linux": 1, "windows": 1}},
    {"disk_admission": [{"path": "/", "min_free_mib": 1}]},
    {"poll_seconds": 600},
])
def test_spec_cannot_weaken_pm01_thresholds(tmp_path, override):
    with pytest.raises(gl.SpecError):
        gl.validate_spec(spec_for(tmp_path, ["true"], **override))


def test_unexpected_error_mid_run_stops_group_and_finalises_receipt(tmp_path):
    class Broken(SynthHost):
        def group_members(self, pgid):
            if self.armed:  # fail once, as a one-off bug would
                self.armed = False
                raise RuntimeError("synthetic launcher bug")
            return super().group_members(pgid)

    host = Broken()
    host.armed = False
    orig_exited = gl._leader_exited

    def arm(pid):  # arm once, after launch, so only the monitoring loop fails
        if not getattr(host, "fired", False):
            host.armed = host.fired = True
        return orig_exited(pid)

    gl._leader_exited, ident = arm, None
    try:
        try:
            gl.run_job(spec_for(tmp_path, ["sleep", "30"]), host)
        except RuntimeError:
            pass
        receipt = json.loads((tmp_path / "rc/job.json").read_text())
        ident = receipt["process_identity"]
        assert receipt["status"] != "running"
        assert not group_alive(ident["pgid"])
    finally:
        gl._leader_exited = orig_exited
        try:  # the launcher normally reaps the leader itself (worker note, round 2)
            unreaped = ident and os.waitid(os.P_PID, ident["leader_pid"],
                                           os.WEXITED | os.WNOHANG | os.WNOWAIT) is None
        except ChildProcessError:
            unreaped = False
        if unreaped:
            os.killpg(ident["pgid"], signal.SIGKILL)  # our own unreaped child's group
        if ident:
            try:
                os.waitpid(ident["leader_pid"], 0)
            except ChildProcessError:
                pass


def test_stop_requested_during_preconditions_launches_nothing(tmp_path):
    host = SynthHost()
    host.stop_requested = True
    r = gl.run_job(spec_for(tmp_path, ["sleep", "5"]), host)
    assert r["launched"] is False


def test_descendant_that_escapes_the_group_is_not_clean(tmp_path):
    token = f"verify-escapee-{uuid.uuid4().hex}"
    cmd = ["sh", "-c", f"setsid {PY} -c 'import time; time.sleep(3)' {token} & exit 0"]
    try:
        r = gl.run_job(spec_for(tmp_path, cmd), SynthHost(token=token))
        assert r["census_after"]["linux"]["workers"], "synthetic census must see the escapee"
        assert r["clean_success"] is False
    finally:
        end = time.monotonic() + 6  # let our escapee exit on its own
        while SynthHost(token=token).linux_census()["workers"] and time.monotonic() < end:
            time.sleep(0.1)


def test_launcher_refuses_to_signal_when_child_shares_its_group(tmp_path):
    # Sacrificial driver in its own session: if the launcher signals "its" group,
    # only the driver and its dummy job are hit.
    spec = spec_for(tmp_path, ["sh", "-c", "sleep 2 & exit 0"])
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    driver = (
        "import json, subprocess, sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "from contributor_tools import guarded_launcher as gl\n"
        "from test_guarded_launcher_verify import SynthHost\n"
        "real = subprocess.Popen\n"
        "def no_session(*a, **k):\n"
        "    k['start_new_session'] = False\n"
        "    return real(*a, **k)\n"
        "gl.subprocess.Popen = no_session\n"
        "try:\n"
        "    gl.run_job(json.load(open(%r)), SynthHost())\n"
        "except Exception:\n"
        "    pass\n"
    ) % (str(REPO), str(REPO / "tests"), str(tmp_path / "spec.json"))
    proc = subprocess.run([PY, "-c", driver], start_new_session=True, timeout=60)
    assert proc.returncode == 0  # currently the launcher SIGTERMs its own group (-15)


def test_python_worker_ancestor_is_not_excluded():
    me = {"argv": Path(f"/proc/{os.getpid()}/cmdline").read_bytes().decode().split("\0")[:-1],
          "cwd": os.getcwd()}
    if not gl.is_linux_worker(me):
        pytest.skip("run as `python3 -m pytest` from the repository root")
    out = subprocess.run([PY, "-c", "import json; from contributor_tools import guarded_launcher as gl;"
                                    "print(json.dumps([w['pid'] for w in gl.Host().linux_census()['workers']]))"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert os.getpid() in json.loads(out)  # a driver could otherwise chain launches


@pytest.mark.parametrize("argv, cwd", [
    (["/usr/bin/python3", "/home/u/.local/bin/pytest", "--run-integration"], "REPO"),
    (["python3", "-m", "ipykernel_launcher", "-f", "/run/user/1000/kernel.json"], "REPO"),
    (["python3", str(REPO / "tests" / "anything.py")], "/tmp"),
])
def test_census_detects_repo_python_workers(argv, cwd):
    assert gl.is_linux_worker({"argv": argv, "cwd": str(REPO) if cwd == "REPO" else cwd})


# ------------------------------------------------- census classifications ---

@pytest.mark.parametrize("argv, worker", [
    (["/mnt/c/Program Files/MATLAB/R2023b/bin/matlab.exe", "-batch", "run('x')"], True),
    (["/mnt/c/Program Files/MATLAB/R2023b/bin/win64/MATLAB.exe", "-nosplash"], True),
    (["/home/u/miniconda3/envs/lh/bin/python3.11", "contributor_tools/x.py"], True),
    (["/home/u/.venv/bin/python", "-X", "importtime", "-m", "contributor_tools.y"], True),
    (["python3", "-I", "-c", "import pandas"], True),
    # MCP servers as they actually run on this host, cwd inside the repository
    (["/mnt/s/workspace/mcp_servers/alex-mcp/.venv/bin/python", "-m", "alex_mcp.server"], False),
    (["/mnt/s/workspace/mcp_servers/zotero-mcp/.venv/bin/python3",
      "/mnt/s/workspace/mcp_servers/zotero-mcp/.venv/bin/zotero-mcp", "serve"], False),
    (["/mnt/s/workspace/mcp_servers/crossref-mcp/.venv/bin/python",
      "/mnt/s/workspace/mcp_servers/crossref-mcp/crossref_server.py"], False),
    (["node", "/usr/lib/node_modules/claude/cli.js"], False),
])
def test_linux_classifier(argv, worker):
    assert gl.is_linux_worker({"argv": argv, "cwd": str(REPO)}) is worker


@pytest.mark.parametrize("row, worker", [
    ({"name": "MATLAB.exe", "cmdline": None}, True),           # other-user process, no cmdline
    ({"name": "matlab.exe", "cmdline": '"C:\\x\\matlab.exe" -r "cd(\'S:\\w\')"'}, True),
    ({"name": "pythonw.exe", "cmdline": None}, True),
    ({"name": "opensim-cmd.exe", "cmdline": "opensim-cmd run-tool ik.xml"}, True),
    ({"name": "MathWorksServiceHost.exe", "cmdline": "x"}, False),
    ({"name": "powershell.exe", "cmdline": "powershell.exe -NoProfile -Command " + gl.PS_CENSUS}, False),
    ({"name": "wsl.exe", "cmdline": "wsl.exe"}, False),
])
def test_windows_classifier(row, worker):
    assert gl.is_windows_worker(row) is worker


# ================================================================ round 2 ===
# Reviewer round 2 against launcher sha256 fa9f0fb0... Same rules: dummy jobs,
# synthetic census, only processes this test starts are signalled.

def _driver_source(spec_file, extra=""):
    return (
        "import json, sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "from contributor_tools import guarded_launcher as gl\n"
        "from test_guarded_launcher_verify import SynthHost\n%s"
        "gl.run_job(json.load(open(%r)), SynthHost())\n"
    ) % (str(REPO), str(REPO / "tests"), extra, str(spec_file))


@pytest.mark.parametrize("override", [
    {"timeout_seconds": 3601}, {"kill_after_seconds": 31}, {"poll_seconds": 15.01},
    {"timeout_seconds": float("inf")}, {"address_space_mib": 769},
    {"disk_admission": [{"path": "/", "min_free_mib": 1023}]},
    {"startup_memory_mib": {"linux": 3583, "windows": 2816}},
    {"runtime_memory_mib": {"linux": 2048, "windows": 2047}},
])
def test_r2_envelope_maxima_and_floors(tmp_path, override):
    with pytest.raises(gl.SpecError):
        gl.validate_spec(spec_for(tmp_path, ["true"], **override))


@pytest.mark.parametrize("override", [
    {"poll_seconds": float("nan")},
    {"runtime_memory_mib": {"linux": float("nan"), "windows": float("nan")}},
    {"startup_memory_mib": {"linux": 4000, "windows": float("nan")}},
    {"timeout_seconds": float("nan")},
])
def test_r2_non_finite_thresholds_are_rejected(tmp_path, override):
    # json.loads accepts NaN; NaN compares False with every floor and maximum.
    assert json.loads(json.dumps(override))  # NaN survives a JSON spec file
    with pytest.raises(gl.SpecError):
        gl.validate_spec(spec_for(tmp_path, ["true"], **override))


def test_r2_nan_runtime_reserve_disables_the_memory_guard(tmp_path):
    """Shows the consequence: with NaN reserves a 10 MiB reading is no breach."""
    spec = spec_for(tmp_path, ["sleep", "1"],
                    runtime_memory_mib={"linux": float("nan"), "windows": float("nan")})
    try:
        r = gl.run_job(spec, SynthHost(mem=[8192, 10], win_mem=[8192, 10]))
    except gl.SpecError:
        return  # fixed: rejected at validation
    assert r["runtime_guard"]["breach"] is not None, "10 MiB available was not a breach"


def test_r2_envelope_floors_always_admitted(tmp_path):
    r = gl.run_job(spec_for(tmp_path, ["true"], disk_admission=[]), SynthHost(), dry_run=True)
    floors = {(d["path"], d["min_free_mib"]) for d in r["disk_admission"]}
    assert ("/mnt/c", 1024) in floors and (str(tmp_path / "job_out"), 5120) in floors


def test_r2_changed_envelope_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "ENVELOPE_REVIEWED_SHA256", "0" * 64)
    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), SynthHost())
    assert r["refusal_reason"] == "envelope_changed_since_review"
    assert not (tmp_path / "launched").exists()


def test_r2_stop_set_during_preconditions_launches_nothing(tmp_path):
    class LateStop(SynthHost):
        def windows_census(self):
            self.stop_requested = True  # arrives mid-preconditions, after the source hash
            return super().windows_census()

    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), LateStop())
    assert r["launched"] is False and not (tmp_path / "launched").exists()


def test_r2_running_receipt_write_failure_stops_group(tmp_path, monkeypatch):
    real = gl.write_json

    def flaky(path, obj, exclusive=False):
        if obj.get("status") == "running":
            raise OSError("synthetic: disk full")
        return real(path, obj, exclusive)

    monkeypatch.setattr(gl, "write_json", flaky)
    r = gl.run_job(spec_for(tmp_path, ["sh", "-c", "sleep 30 & sleep 30"]), SynthHost())
    assert r["status"] == "launcher_error"
    assert not group_alive(r["process_identity"]["pgid"])
    conflict = list((tmp_path / "rc").glob("job.conflict-*.json"))
    assert len(conflict) == 1 and json.loads(conflict[0].read_text())["status"] == "launcher_error"


def test_r2_cleanup_proof_exception_is_recorded_not_clean(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("synthetic proof failure")

    monkeypatch.setattr(gl, "prove_cleanup", boom)
    r = gl.run_job(spec_for(tmp_path, ["true"]), SynthHost())
    on_disk = json.loads((tmp_path / "rc/job.json").read_text())
    assert on_disk["status"] != "running" and on_disk["clean_success"] is False
    assert on_disk["checks"]["cleanup_proven"] is False


def test_r2_unreadable_output_file_still_finalises_receipt(tmp_path):
    job = [PY, "-c", "import os; os.makedirs('job_out'); open('job_out/x', 'w').write('1');"
                     "os.chmod('job_out/x', 0)"]
    try:
        gl.run_job(spec_for(tmp_path, job), SynthHost())
    except OSError:
        pass
    finally:
        os.chmod(tmp_path / "job_out/x", 0o600)
    assert json.loads((tmp_path / "rc/job.json").read_text())["status"] != "running"


def test_r2_pdeathsig_on_timeout_leader_reaches_grandchild(tmp_path):
    token = f"verify-pdeath-{uuid.uuid4().hex}"
    cmd = ["sh", "-c", f"{PY} -c 'import time; time.sleep(60)' {token}"]  # grandchild of timeout
    spec = spec_for(tmp_path, cmd, timeout_seconds=60, kill_after_seconds=2)
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    proc = subprocess.Popen([PY, "-c", _driver_source(tmp_path / "spec.json")], start_new_session=True)
    receipt = tmp_path / "rc/job.json"
    try:
        end = time.monotonic() + 10
        while time.monotonic() < end and not SynthHost(token=token).linux_census()["workers"]:
            time.sleep(0.05)
        assert SynthHost(token=token).linux_census()["workers"], "grandchild never started"
        ident = json.loads(receipt.read_text())["process_identity"]
        assert ident["parent_death_signal"] == "SIGTERM"
    finally:
        proc.kill()  # our own driver
        proc.wait()
    t0 = time.monotonic()
    while SynthHost(token=token).linux_census()["workers"] and time.monotonic() - t0 < 10:
        time.sleep(0.1)
    assert not SynthHost(token=token).linux_census()["workers"]
    assert time.monotonic() - t0 < 2 + 3  # kill-after grace plus margin, far below the 60 s timeout
    assert not group_alive(ident["pgid"])


def test_r2_address_space_limit_reaches_job_and_is_observed(tmp_path):
    job = [PY, "-c", "import resource, time; print(resource.getrlimit(resource.RLIMIT_AS)[0]);"
                     "time.sleep(0.5)"]
    r = gl.run_job(spec_for(tmp_path, job, address_space_mib=512), SynthHost())
    assert (tmp_path / "rc/job.log").read_text().split() == [str(512 * 1024**2)]
    assert str(512 * 1024**2) in r["runtime_guard"]["observed_address_space_limits"]


def test_r2_escapee_outside_repo_without_patterns_is_missed_documented(tmp_path):
    """Residual limit: a setsid escapee in a neutral cwd matches no worker rule."""
    row = {"argv": [PY, "-c", "import time; time.sleep(3)"], "cwd": "/"}
    assert gl.is_linux_worker(row) is False


@pytest.mark.parametrize("argv, exempt", [
    (["/usr/bin/zsh", "-c", "source snap.sh && eval 'python3 -m contributor_tools.guarded_launcher run s.json'"], True),
    (["tmux"], True), (["-zsh"], True),
    (["timeout", "4000", "python3", "driver.py"], True),  # timeout itself; the python child is caught
    (["python3", "driver.py"], False), (["bash", "queue.sh"], False),
    pytest.param(["bash", "queue.sh", "-c", "x"], False),  # script file given a -c argument
])
def test_r2_ancestor_exemption(argv, exempt):
    assert gl.ancestor_is_exempt({"argv": argv}) is exempt


def test_r2_library_driver_is_not_exempt_as_launcher_itself():
    """A python driver that imports run_job is 'the launcher itself' to the census."""
    out = subprocess.run(
        [PY, "-c", "import json, os; from contributor_tools import guarded_launcher as gl;"
                   "print(json.dumps({'me': os.getpid(),"
                   "'workers': [w['pid'] for w in gl.Host().linux_census()['workers']]}))"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    seen = json.loads(out)
    assert seen["me"] in seen["workers"], "a library loop over run_job would pass every census"



# ================================================================ round 3 ===
# Reviewer round 3 against launcher sha256 a2a9abc8... The ledger probes run
# run_job with a synthetic census and a dummy `true` job under real shells, so
# the launching-parent lookup reads the real /proc. Nothing else is launched.

LEDGER_PROBE = '''
import json, sys
sys.path.insert(0, {repo!r}); sys.path.insert(0, {tests!r})
from contributor_tools import guarded_launcher as gl
from test_guarded_launcher_verify import SynthHost, spec_for
from pathlib import Path
base = Path(sys.argv[1]) / sys.argv[2]
base.mkdir(parents=True)
r = gl.run_job(spec_for(base, ["true"]), SynthHost(), launch_ledger={ledger!r})
print(json.dumps([r["status"], r.get("refusal_reason")]))
'''


def _ledger_loop(tmp_path, shell_loop):
    ledger = tmp_path / "ledger"
    # The probe's file name contains 'guarded_launcher' and is written literally into
    # the loop text, as a real launcher invocation would be (no env-var indirection).
    probe = tmp_path / "guarded_launcher_probe.py"
    probe.write_text(LEDGER_PROBE.format(repo=str(REPO), tests=str(REPO / "tests"), ledger=str(ledger)))
    shell_loop = shell_loop.replace("$PROBE", f"{PY} {probe} {tmp_path}")
    out = subprocess.run(["bash", "-c", shell_loop], capture_output=True, text=True,
                         timeout=120, cwd=tmp_path).stdout
    return [json.loads(line) for line in out.splitlines() if line.startswith("[")]


def test_r3_ledger_blocks_a_plain_shell_loop(tmp_path):
    runs = _ledger_loop(tmp_path, 'for i in 1 2; do $PROBE run$i; done')
    assert runs == [["completed", None], ["refused_precondition", "parent_already_launched"]]


def test_r3_ledger_blocks_xargs(tmp_path):
    runs = _ledger_loop(tmp_path, 'printf "1\\n2\\n" | xargs -I{} $PROBE run{}')
    assert [r[1] for r in runs] == [None, "parent_already_launched"]


@pytest.mark.parametrize("loop", [
    'for i in 1 2; do sh -c "cd /tmp && $PROBE run$i"; done',
    'printf "1\\n2\\n" | xargs -I{} sh -c "$PROBE run{}"',
    'for i in 1 2; do bash -c "$PROBE run$i; echo done"; done',
])
def test_r3_ledger_blocks_a_fresh_shell_per_iteration(tmp_path, loop):
    runs = _ledger_loop(tmp_path, loop)
    assert [r[1] for r in runs] == [None, "parent_already_launched"]


def test_r3_dry_run_does_not_consume_a_slot(tmp_path):
    ledger = tmp_path / "ledger"
    r = gl.run_job(spec_for(tmp_path, ["true"]), SynthHost(), dry_run=True, launch_ledger=ledger)
    assert r["status"] == "preflight_passed"
    assert not ledger.exists() or not any(ledger.rglob("*.json"))


def test_r3_corrupt_ledger_entry_still_blocks(tmp_path):
    host = SynthHost()
    parent = host.launching_parent()
    entry = tmp_path / "ledger" / host.boot_id() / f"{parent['pid']}-{parent['start_ticks']}.json"
    entry.parent.mkdir(parents=True)
    entry.write_text("{not json")
    if parent["interactive_terminal"]:
        pytest.skip("pytest launched from an interactive terminal is ledger-exempt by design")
    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), host, launch_ledger=tmp_path / "ledger")
    assert r["refusal_reason"] == "parent_already_launched"
    assert not (tmp_path / "launched").exists()


def test_r3_unusable_ledger_fails_closed(tmp_path):
    blocker = tmp_path / "ledger"
    blocker.write_text("a file where the ledger directory should be")
    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), SynthHost(), launch_ledger=blocker)
    if r.get("launch_ledger", {}).get("exempt"):
        pytest.skip("interactive terminal parent")
    assert r["refusal_reason"] == "launch_ledger_unavailable"
    assert not (tmp_path / "launched").exists()


def test_r3_failed_final_write_leaves_a_discoverable_terminal_fallback(tmp_path, monkeypatch):
    real = gl.write_json
    receipt = tmp_path / "rc/job.json"

    def flaky(path, obj, exclusive=False):
        if Path(path) == receipt and obj.get("status") != "running":
            raise OSError("synthetic: final write failed")
        return real(path, obj, exclusive)

    monkeypatch.setattr(gl, "write_json", flaky)
    r = gl.run_job(spec_for(tmp_path, ["true"]), SynthHost())
    running = json.loads(receipt.read_text())
    assert running["status"] == "running"  # the primary receipt cannot be finalised
    pid = running["process_identity"]["leader_pid"]
    fallback = receipt.with_suffix(f".final-{pid}.json")  # derivable from the running receipt
    final = json.loads(fallback.read_text())
    assert final["status"] != "running" and final["clean_success"] is False
    assert final["finalisation_errors"][-1]["step"] == "receipt_write"
    # Note: status here stays the job outcome ('completed'); other finalisation
    # errors set 'launcher_error' (recommendation R3-3).


def test_r3_missing_prctl_refuses_before_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "_libc_prctl", lambda: None)
    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), SynthHost())
    assert r["refusal_reason"] == "parent_death_signal_unavailable"
    assert not (tmp_path / "launched").exists()


def test_r3_failing_prctl_in_child_refuses_and_runs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "_libc_prctl", lambda: (lambda *a: -1))
    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), SynthHost())
    assert r["status"] == "refused_precondition" and r["refusal_reason"] == "launch_failed"
    assert not (tmp_path / "launched").exists()


@pytest.mark.parametrize("override", [
    {"startup_memory_mib": {"linux": 10**400, "windows": 2816}},
    {"disk_admission": [{"path": "/", "min_free_mib": 10**400}]},
])
def test_r3_huge_integers_never_validate(tmp_path, override):
    with pytest.raises((gl.SpecError, OverflowError)):  # OverflowError: fails closed, not a SpecError
        gl.validate_spec(spec_for(tmp_path, ["true"], **override))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, "4000"])
def test_r3_non_finite_or_missing_readings_never_admit(value):
    assert gl._at_least(value, 1) is False


@pytest.mark.parametrize("argv, worker", [
    (["ls", "converted_datasets/"], True),  # conservative false positive, documented
    (["tail", "-f", "converted_datasets/x/log.txt"], True),
    (["/mnt/s/workspace/mcp_servers/alex-mcp/.venv/bin/python", "-m", "alex_mcp.server"], False),
    (["node", "/usr/lib/node_modules/claude/cli.js"], False),
])
def test_r3_converted_datasets_pattern(argv, worker):
    assert gl.is_linux_worker({"argv": argv, "cwd": "/"}) is worker


# ================================================================ round 4 ===
# Reviewer round 4 against launcher sha256 8df6f115...

@pytest.mark.parametrize("loop", [
    'make -s -f Makefile',                                       # simple recipe lines, exec'd by make
    'nohup bash -c "$PROBE run1; $PROBE run2" 2>/dev/null; cat nohup.out',
    'for i in 1 2; do find . -maxdepth 0 -exec sh -c "$PROBE run$i; true" \\; ; done',
])
def test_r4_ledger_blocks_make_nohup_and_find(tmp_path, loop):
    (tmp_path / "Makefile").write_text("all:\n\t$(P) run1\n\tcd . && $(P) run2\n")
    probe = f"{PY} {tmp_path / 'guarded_launcher_probe.py'} {tmp_path}"
    loop = loop.replace("make -s -f Makefile", f"make -s -f Makefile P='{probe}'")
    runs = _ledger_loop(tmp_path, loop)
    assert [r[1] for r in runs] == [None, "parent_already_launched"]


def test_r4_vanishing_parent_fails_closed(tmp_path):
    class Vanishing(SynthHost):
        def stat(self, pid):
            return None if pid == os.getppid() else super().stat(pid)

    r = gl.run_job(spec_for(tmp_path, ["touch", "launched"]), Vanishing(),
                   launch_ledger=tmp_path / "ledger")
    assert r["refusal_reason"] == "launch_ledger_unavailable"
    assert not (tmp_path / "launched").exists()


def test_r4_verify_cleanup_reports_fallback_receipts(tmp_path):
    rc = tmp_path / "rc"
    rc.mkdir()
    (rc / "job.json").write_text(json.dumps({"status": "running", "process_identity": {
        "boot_id": "synthetic-previous-boot", "pgid": 999_999_999, "leader_pid": 999_999_999,
        "leader_start_ticks": 1}}))
    (rc / "job.final-4242.json").write_text(json.dumps({"status": "launcher_error"}))
    (rc / "job.conflict-4343.json").write_text("{corrupt")
    (rc / "other.final-1.json").write_text(json.dumps({"status": "completed"}))  # another job
    out = gl.verify_cleanup(gl.Host(), rc / "job.json")
    found = {(Path(f["path"]).name, f["kind"], f["status"].split(":")[0]) for f in out["fallback_receipts"]}
    assert found == {("job.final-4242.json", "final", "launcher_error"),
                     ("job.conflict-4343.json", "conflict", "unreadable")}
    assert out["primary_status"] == "running" and out["cleanup_proof"]["basis"] == "reboot"


def test_r4_failed_final_write_sets_launcher_error(tmp_path, monkeypatch):
    real, receipt = gl.write_json, tmp_path / "rc/job.json"

    def flaky(path, obj, exclusive=False):
        if Path(path) == receipt and obj.get("status") != "running":
            raise OSError("synthetic")
        return real(path, obj, exclusive)

    monkeypatch.setattr(gl, "write_json", flaky)
    gl.run_job(spec_for(tmp_path, ["true"]), SynthHost())
    final = next((tmp_path / "rc").glob("job.final-*.json"))
    assert json.loads(final.read_text())["status"] == "launcher_error"


def test_r4_production_cli_uses_unmodified_host():
    """The _parent_pid test hook is reachable only by subclassing in-process."""
    src = Path(gl.__file__).read_text()
    main_src = src[src.index("def main("):]
    assert "host = Host()" in main_src and "_parent_pid" not in main_src
    assert "launch_ledger=LEDGER_ROOT" in main_src
    assert gl.Host()._parent_pid() == os.getppid()
