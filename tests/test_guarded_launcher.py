"""Synthetic tests for contributor_tools/guarded_launcher.py.

Every job here is a tiny dummy command (sleep, sh, python -c) writing to a
pytest temporary directory. Linux/Windows censuses, memory and disk readings
are injected fakes; process-group scans and cleanup proofs use the real /proc
because the dummy processes are real. No research data is read and no
LocoHub job is launched.
"""
import hashlib
import json
import subprocess
import sys
import time

import pytest

from contributor_tools import guarded_launcher as gl

PY = sys.executable


class FakeHost(gl.Host):
    """Real /proc for process identity; synthetic census, memory and disk."""

    def __init__(self, linux_workers=(), windows_workers=(), linux_mem=(8000,), windows_mem=(8000,),
                 disk_free=100_000, windows_after=None, windows_error=False):
        super().__init__()
        self.linux_workers, self.windows_workers = list(linux_workers), list(windows_workers)
        self.linux_mem, self.windows_mem = list(linux_mem), list(windows_mem)
        self.disk_free, self.windows_after, self.windows_error = disk_free, windows_after, windows_error
        self.windows_calls = 0

    def linux_census(self):
        return {"checked_at_utc": gl.utcnow(), "boot_id": self.boot_id(), "process_count": 3,
                "excluded_self_and_ancestors": [], "workers": self.linux_workers}

    def windows_census(self):
        if self.windows_error:
            raise RuntimeError("synthetic: powershell unavailable")
        self.windows_calls += 1
        workers = self.windows_workers
        if self.windows_calls > 1 and self.windows_after is not None:
            workers = self.windows_after
        return {"checked_at_utc": gl.utcnow(), "last_boot_utc": "2026-09-07T21:16:10Z",
                "process_count": 5, "free_physical_mib": self.windows_mem[0], "workers": workers}

    @staticmethod
    def _next(values):
        return values.pop(0) if len(values) > 1 else values[0]

    def linux_mem_available_mib(self):
        return self._next(self.linux_mem)

    def windows_free_mib(self):
        return self._next(self.windows_mem)

    def disk_free_mib(self, path):
        return self.disk_free


def make_spec(tmp_path, command, **overrides):
    bound = tmp_path / "bound_code.py"
    if not bound.exists():
        bound.write_text("# synthetic bound file\n")
    spec = {
        "job_id": "synthetic_test_job",
        "command": command,
        "cwd": str(tmp_path),
        "output_root": "out",
        "receipt_path": "receipts/job.json",
        "bindings": {"bound_code.py": hashlib.sha256(bound.read_bytes()).hexdigest()},
        "timeout_seconds": 20,
        "kill_after_seconds": 1,
        "poll_seconds": 0.1,
        "disk_admission": [{"path": str(tmp_path), "min_free_mib": 5120}],
        "startup_memory_mib": {"linux": 3584, "windows": 2816},
        "runtime_memory_mib": {"linux": 2048, "windows": 2048},
    }
    spec.update(overrides)
    return spec


WRITE_OUTPUT = [PY, "-c", "import os; os.makedirs('out'); open('out/phase.parquet','w').write('x');"
                "print(os.environ['OMP_NUM_THREADS'], os.environ['ARROW_NUM_THREADS'])"]


def assert_not_launched(tmp_path, receipt, reason):
    assert receipt["status"] == "refused_precondition"
    assert receipt["refusal_reason"] == reason
    assert receipt["launched"] is False and "process_identity" not in receipt
    assert not (tmp_path / "receipts/job.log").exists()
    assert json.loads((tmp_path / "receipts/job.json").read_text())["refusal_reason"] == reason


def test_success_receipt_binds_hashes_censuses_and_cleanup(tmp_path):
    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT, expected_output_names=["phase.parquet"]),
                         FakeHost(), spec_sha256="0" * 64)
    assert receipt["status"] == "completed" and receipt["exit_code"] == 0
    assert receipt["clean_success"] is True
    assert receipt["checks"] == {"cleanup_proven": True, "bindings_unchanged": True,
                                 "envelope_unchanged": True, "linux_no_new_worker": True,
                                 "windows_no_new_worker": True, "no_orphans_at_leader_exit": True,
                                 "outputs_hashed": True, "expected_outputs_present": True}
    assert receipt["envelope"]["sha256"] == gl.ENVELOPE_REVIEWED_SHA256
    # Output hash is checked against an independently computed value.
    assert receipt["outputs"] == [{"path": "phase.parquet", "bytes": 1,
                                   "sha256": hashlib.sha256(b"x").hexdigest()}]
    on_disk = json.loads((tmp_path / "receipts/job.json").read_text())
    assert on_disk == json.loads(json.dumps(receipt))
    for key in ("bindings_before", "bindings_after", "census_before", "census_after",
                "process_identity", "cleanup_proof", "wall_time_seconds",
                "peak_rss_kib_largest_process", "launcher_sha256", "spec_sha256", "log_sha256"):
        assert key in receipt, key
    ident = receipt["process_identity"]
    assert ident["pgid"] == ident["leader_pid"]  # setsid-equivalent new session
    assert ident["argv"][:10] == ["timeout", "--signal=TERM", "--kill-after=1s", "20",
                                  "nice", "-n", "19", "ionice", "-c", "3"]
    assert receipt["cleanup_proof"]["basis"] == "same_boot_proc_scan"
    assert receipt["peak_rss_kib_largest_process"] > 0
    # Single-threaded environment reached the child.
    assert (tmp_path / "receipts/job.log").read_text().split() == ["1", "1"]


def test_binding_mismatch_refuses_without_launch(tmp_path):
    spec = make_spec(tmp_path, WRITE_OUTPUT)
    (tmp_path / "bound_code.py").write_text("# edited after binding\n")
    receipt = gl.run_job(spec, FakeHost())
    assert_not_launched(tmp_path, receipt, "binding_mismatch")
    assert receipt["mismatched_bindings"] == ["bound_code.py"]
    assert not (tmp_path / "out").exists()


def test_existing_output_root_refuses(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out/history.txt").write_text("keep")
    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), FakeHost())
    assert_not_launched(tmp_path, receipt, "output_root_exists")
    assert (tmp_path / "out/history.txt").read_text() == "keep"


@pytest.mark.parametrize("host, reason", [
    (FakeHost(linux_workers=[{"pid": 4242, "cmdline": "python3 contributor_tools/x.py"}]),
     "foreign_worker_linux"),
    (FakeHost(windows_workers=[{"pid": 50688, "name": "MATLAB.exe"}]), "foreign_worker_windows"),
    (FakeHost(windows_error=True), "windows_census_unavailable"),
    (FakeHost(linux_mem=(3000,)), "startup_memory_reserve"),
    (FakeHost(disk_free=1000), "disk_admission"),
])
def test_census_memory_and_disk_refusals(tmp_path, host, reason):
    assert_not_launched(tmp_path, gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), host), reason)


def test_existing_receipt_is_never_overwritten(tmp_path):
    (tmp_path / "receipts").mkdir()
    (tmp_path / "receipts/job.json").write_text("history")
    with pytest.raises(gl.SpecError):
        gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), FakeHost())
    assert (tmp_path / "receipts/job.json").read_text() == "history"


def test_spec_rejects_pid_waits_successors_and_multithreading(tmp_path):
    for extra in ({"wait_for_pid": 402226}, {"next_job": "x"}):
        with pytest.raises(gl.SpecError):
            gl.validate_spec({**make_spec(tmp_path, WRITE_OUTPUT), **extra})
    with pytest.raises(gl.SpecError):
        gl.validate_spec(make_spec(tmp_path, WRITE_OUTPUT, thread_env={"OMP_NUM_THREADS": "4"}))
    with pytest.raises(gl.SpecError):
        gl.validate_spec(make_spec(tmp_path, WRITE_OUTPUT, receipt_path="out/job.json"))


def test_timeout_kills_term_ignoring_job_and_proves_cleanup(tmp_path):
    ignore_term = [PY, "-c", "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                             "time.sleep(30)"]
    t0 = time.monotonic()
    receipt = gl.run_job(make_spec(tmp_path, ignore_term, timeout_seconds=1), FakeHost())
    assert time.monotonic() - t0 < 10
    assert receipt["status"] == "timed_out" and receipt["exit_code"] == -9  # timeout SIGKILLs its group after grace
    assert receipt["cleanup_proof"]["proven"] is True
    assert receipt["clean_success"] is False


def test_memory_breach_stops_group_with_grandchild(tmp_path):
    # Second Linux reading (first runtime poll) drops below the 2048 MiB reserve.
    host = FakeHost(linux_mem=(8000, 100))
    t0 = time.monotonic()
    receipt = gl.run_job(make_spec(tmp_path, ["sh", "-c", "sleep 30 & sleep 30"]), host)
    assert time.monotonic() - t0 < 10
    assert receipt["status"] == "stopped_resource_guard"
    assert receipt["runtime_guard"]["breach"]["readings_mib"]["linux"] == 100
    assert receipt["stop_actions"][0]["signal"] == "SIGTERM"
    assert receipt["cleanup_proof"]["proven"] is True
    assert receipt["retry"] == "never automatic"


def test_unreadable_runtime_memory_counts_as_breach(tmp_path):
    class Unreadable(FakeHost):
        def windows_free_mib(self):
            raise RuntimeError("synthetic: query failed")

    receipt = gl.run_job(make_spec(tmp_path, ["sleep", "30"]), Unreadable())
    assert receipt["status"] == "stopped_resource_guard"
    assert receipt["runtime_guard"]["breach"]["readings_mib"]["windows"] is None


def test_orphan_left_in_group_is_stopped_before_proof(tmp_path):
    receipt = gl.run_job(make_spec(tmp_path, ["sh", "-c", "sleep 30 & exit 0"]), FakeHost())
    assert receipt["status"] == "completed"
    assert [o["state"] for o in receipt["orphans_at_leader_exit"]] != []
    assert receipt["cleanup_proof"]["proven"] is True
    assert receipt["checks"]["no_orphans_at_leader_exit"] is False and not receipt["clean_success"]


def test_new_windows_worker_after_run_is_flagged(tmp_path):
    host = FakeHost(windows_after=[{"pid": 1, "name": "MATLAB.exe", "created": "t"}])
    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), host)
    assert receipt["checks"]["windows_no_new_worker"] is False
    assert receipt["clean_success"] is False


def test_binding_changed_during_run_is_flagged(tmp_path):
    cmd = [PY, "-c", "open('bound_code.py','a').write('# changed\\n')"]
    receipt = gl.run_job(make_spec(tmp_path, cmd), FakeHost())
    assert receipt["status"] == "completed"
    assert receipt["checks"]["bindings_unchanged"] is False and not receipt["clean_success"]


def test_cleanup_proof_reboot_case_and_live_leader(tmp_path):
    host = gl.Host()
    gone = {"boot_id": "synthetic-previous-boot", "pgid": 999_999_999, "leader_pid": 999_999_999,
            "leader_start_ticks": 1}
    assert gl.prove_cleanup(host, gone)["basis"] == "reboot"
    import os
    me = {"boot_id": host.boot_id(), "pgid": os.getpgid(0), "leader_pid": os.getpid(),
          "leader_start_ticks": host.stat(os.getpid())["start_ticks"]}
    proof = gl.prove_cleanup(host, me, attempts=1)
    assert proof["proven"] is False and proof["leader_pid_with_same_start_ticks_present"]


def test_worker_classifier_on_synthetic_process_rows(tmp_path):
    (tmp_path / "contributor_tools").mkdir()
    (tmp_path / "tests").mkdir()
    rows = {
        "producer script": (["python3", "contributor_tools/extend_umich_tread_source.py"], True),
        "MCP helper with cwd in repo": (["/srv/.venv/bin/python", "-m", "alex_mcp.server"], False),
        "repo script by relative path": (["python3", "tests/foo.py"], True),
        "inline code in repo": (["/usr/bin/python3", "-c", "pass"], True),
        "pytest in repo": (["python3", "-m", "pytest", "-q"], True),
        "repo package module": (["python3", "-m", "contributor_tools.guarded_launcher"], True),
        "shell tool reading research data": (["bfs", "converted_datasets"], True),  # R2-4
        "unrelated shell tool": (["bfs", "/tmp"], False),
    }
    for label, (argv, expected) in rows.items():
        row = {"argv": argv, "cwd": str(tmp_path)}
        assert gl.is_linux_worker(row, tmp_path) is expected, label
    assert gl.is_linux_worker({"argv": ["/opt/MATLAB/bin/matlab"], "cwd": "/"}, tmp_path)
    assert gl.is_windows_worker({"name": "MATLAB.exe"})
    assert gl.is_windows_worker({"name": "python.exe"})
    assert not gl.is_windows_worker({"name": "MathWorksServiceHost.exe"})
    assert gl.is_windows_worker({"name": "cmd.exe", "cmdline": "opensim-cmd run-tool x"})


# ------------------------------------------------ round-2 review fixes ---

def test_envelope_limits_match_pm01_text():
    # Independent check: each enforced value appears verbatim in the PM-01 envelope.
    text = (gl.REPO_ROOT / gl.ENVELOPE).read_text()
    for phrase in ("S: free >= 5 GiB", "C: free >= 1 GiB", "MemAvailable >= 3584 MiB",
                   "FreePhysicalMemory >= 2816 MiB", "Poll every 15 s: Linux MemAvailable >= 2048 MiB",
                   "Windows FreePhysicalMemory >= 2048 MiB", "--kill-after=30s 3600",
                   '"address_space_mib": 768'):
        assert phrase in text, phrase
    lim = gl.ENVELOPE_LIMITS
    assert (lim["output_volume_free_mib_min"], lim["c_drive_free_mib_min"]) == (5120, 1024)
    assert lim["startup_memory_mib_min"] == {"linux": 3584, "windows": 2816}
    assert lim["runtime_memory_mib_min"] == {"linux": 2048, "windows": 2048}
    assert (lim["timeout_seconds_max"], lim["kill_after_seconds_max"], lim["poll_seconds_max"]) == (3600, 30, 15)


def test_spec_cannot_raise_timeout_grace_or_address_space(tmp_path):
    for override in ({"timeout_seconds": 3601}, {"kill_after_seconds": 31},
                     {"address_space_mib": 769}):
        with pytest.raises(gl.SpecError):
            gl.validate_spec(make_spec(tmp_path, WRITE_OUTPUT, **override))


def test_envelope_floors_are_added_even_if_spec_omits_disk(tmp_path):
    seen = []

    class Disk(FakeHost):
        def disk_free_mib(self, path):
            seen.append(str(path))
            return 2000 if str(path) == "/mnt/c" else 100_000

    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT, disk_admission=[]), Disk(), dry_run=True)
    assert receipt["status"] == "preflight_passed"
    assert seen[:2] == [str(tmp_path / "out"), "/mnt/c"]

    class LowC(FakeHost):
        def disk_free_mib(self, path):
            return 1000 if str(path) == "/mnt/c" else 100_000

    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT, disk_admission=[]), LowC())
    assert_not_launched(tmp_path, receipt, "disk_admission")


def test_changed_envelope_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(gl, "ENVELOPE_REVIEWED_SHA256", "f" * 64)
    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), FakeHost())
    assert_not_launched(tmp_path, receipt, "envelope_changed_since_review")


def test_output_root_created_during_preconditions_refuses(tmp_path):
    class Racer(FakeHost):
        def windows_census(self):
            (tmp_path / "out").mkdir(exist_ok=True)  # synthetic concurrent writer
            return super().windows_census()

    receipt = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), Racer())
    assert_not_launched(tmp_path, receipt, "output_root_exists")


def test_refusal_receipt_is_written_exclusively(tmp_path):
    class Late(FakeHost):
        def windows_census(self):
            (tmp_path / "receipts").mkdir(exist_ok=True)
            (tmp_path / "receipts/job.json").write_text("another launcher's receipt")
            raise RuntimeError("synthetic: census failed")

    with pytest.raises(FileExistsError):
        gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), Late())
    assert (tmp_path / "receipts/job.json").read_text() == "another launcher's receipt"


def test_address_space_limit_is_applied_and_observed(tmp_path):
    cmd = [PY, "-c", "import resource,time; print(resource.getrlimit(resource.RLIMIT_AS)[0]); time.sleep(0.5)"]
    receipt = gl.run_job(make_spec(tmp_path, cmd, address_space_mib=768), FakeHost())
    assert receipt["status"] == "completed"
    assert (tmp_path / "receipts/job.log").read_text().split() == [str(768 * 1024**2)]
    assert receipt["runtime_guard"]["observed_address_space_limits"] == [str(768 * 1024**2)]


def test_killed_launcher_ends_job_promptly_via_parent_death_signal(tmp_path):
    spec = make_spec(tmp_path, ["sleep", "60"])  # timeout 20 s, so only PDEATHSIG ends it early
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    driver = ("import json, sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
              "from contributor_tools import guarded_launcher as gl\n"
              "from test_guarded_launcher import FakeHost\n"
              "gl.run_job(json.load(open(%r)), FakeHost())\n"
              ) % (str(gl.REPO_ROOT), str(gl.REPO_ROOT / "tests"), str(tmp_path / "spec.json"))
    import subprocess
    proc = subprocess.Popen([PY, "-c", driver], start_new_session=True)
    receipt = tmp_path / "receipts/job.json"
    try:
        end = time.monotonic() + 10
        while not receipt.exists() and time.monotonic() < end:
            time.sleep(0.05)
        ident = json.loads(receipt.read_text())["process_identity"]
        assert ident["parent_death_signal"] == "SIGTERM"
    finally:
        proc.kill()  # our own synthetic driver
        proc.wait()
    end = time.monotonic() + 5
    live = lambda: [m for m in gl.Host().group_members(ident["pgid"]) if m["state"] != "Z"]
    while live() and time.monotonic() < end:
        time.sleep(0.1)
    assert not live()


def test_ancestor_exemption_rules():
    exempt = [["/init"], ["tmux"], ["-zsh"], ["/usr/bin/zsh", "-c", "python3 -m contributor_tools.x"],
              ["timeout", "180", "python3", "-m", "contributor_tools.guarded_launcher"],
              ["node", "/usr/lib/node_modules/claude/cli.js"]]
    not_exempt = [["python3", "contributor_tools/run_queue.py"], ["python3", "-m", "pytest"],
                  ["bash", "run_queue.sh"], ["/mnt/c/Program Files/MATLAB/bin/matlab.exe"]]
    assert all(gl.ancestor_is_exempt({"argv": a}) for a in exempt)
    assert not any(gl.ancestor_is_exempt({"argv": a}) for a in not_exempt)


# ------------------------------------------------ round-3 review fixes ---

def test_nan_reading_at_runtime_is_a_breach(tmp_path):
    host = FakeHost(linux_mem=(8000, float("nan")))
    receipt = gl.run_job(make_spec(tmp_path, ["sleep", "30"]), host)
    assert receipt["status"] == "stopped_resource_guard"


def test_nan_reading_at_startup_refuses(tmp_path):
    assert_not_launched(tmp_path, gl.run_job(make_spec(tmp_path, WRITE_OUTPUT),
                                             FakeHost(linux_mem=(float("nan"),))),
                        "startup_memory_reserve")


def test_finalisation_failure_still_writes_terminal_receipt_with_exit(tmp_path, monkeypatch):
    def boom(root):
        raise RuntimeError("synthetic finalisation bug")

    monkeypatch.setattr(gl, "hash_outputs", boom)
    receipt = gl.run_job(make_spec(tmp_path, [PY, "-c", "raise SystemExit(3)"]), FakeHost())
    on_disk = json.loads((tmp_path / "receipts/job.json").read_text())
    assert on_disk["status"] == "launcher_error" and on_disk["job_outcome"] == "failed"
    assert on_disk["exit_code"] == 3 and on_disk["clean_success"] is False
    assert on_disk["finalisation_errors"][0]["step"] == "outputs"


def test_launch_ledger_allows_one_launch_per_parent(tmp_path, monkeypatch):
    parent = {"pid": 4242, "start_ticks": 99, "cmdline": "synthetic driver",
              "interactive_terminal": False}
    monkeypatch.setattr(FakeHost, "launching_parent", lambda self: parent)
    ledger = tmp_path / "ledger"
    first = gl.run_job(make_spec(tmp_path, WRITE_OUTPUT), FakeHost(), launch_ledger=ledger)
    assert first["status"] == "completed" and first["launch_ledger"]["claimed"] is True
    second = gl.run_job(make_spec(tmp_path, ["touch", "launched"], output_root="out2",
                                  receipt_path="receipts/job2.json"), FakeHost(), launch_ledger=ledger)
    assert second["refusal_reason"] == "parent_already_launched" and second["launched"] is False
    assert not (tmp_path / "launched").exists()
    # A person at an interactive terminal is exempt (documented).
    parent["interactive_terminal"] = True
    third = gl.run_job(make_spec(tmp_path, ["true"], output_root="out3",
                                 receipt_path="receipts/job3.json"), FakeHost(), launch_ledger=ledger)
    assert third["status"] == "completed" and third["launch_ledger"]["claimed"] is False


def test_launching_parent_skips_exec_wrappers(tmp_path):
    # A real dummy chain: sh -> timeout -> python. The ledger key must be the sh.
    probe = ("import json; from contributor_tools import guarded_launcher as gl;"
             "print(json.dumps(gl.Host().launching_parent()))")
    out = subprocess.run(["sh", "-c", f"timeout 20 {PY} -c '{probe}'; echo $$"],
                         cwd=gl.REPO_ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    parent, sh_pid = json.loads(out[0]), int(out[1])
    assert parent["pid"] == sh_pid and parent["interactive_terminal"] is False


def test_cli_form_and_shell_mode_classifiers():
    assert gl.is_launcher_cli(["python3", "-m", "contributor_tools.guarded_launcher", "run", "s.json"])
    assert gl.is_launcher_cli(["/usr/bin/python3", "-X", "utf8", "contributor_tools/guarded_launcher.py"])
    assert not gl.is_launcher_cli(["python3", "-c", "import contributor_tools.guarded_launcher"])
    assert not gl.is_launcher_cli(["python3", "driver.py", "contributor_tools/guarded_launcher.py"])
    assert gl._shell_mode(["bash", "-ec", "x"]) == "command"
    assert gl._shell_mode(["bash", "-l"]) == "interactive"
    assert gl._shell_mode(["bash", "queue.sh", "-c", "x"]) == "script"


# ------------------------------------------------ round-4 review fixes ---

class TreeHost(FakeHost):
    """Synthetic ancestor tree for the ledger walk; other PIDs (the dummy job) use
    the real /proc. A tree value of None marks an ancestor that vanished."""

    def __init__(self, tree, start, **kw):
        super().__init__(**kw)
        self.tree, self.start = tree, start  # pid -> (ppid, argv, interactive) or None

    def _parent_pid(self):
        return self.start

    def stat(self, pid):
        if pid not in self.tree:
            return super().stat(pid)
        if self.tree[pid] is None:
            return None
        return {"state": "S", "ppid": self.tree[pid][0], "pgid": -pid, "sid": -pid,
                "start_ticks": 1000 + pid}

    def argv(self, pid):
        if pid not in self.tree:
            return super().argv(pid)
        return self.tree[pid][1] if self.tree[pid] else []

    def interactive_terminal(self, pid, argv):
        return bool(self.tree.get(pid)) and self.tree[pid][2]


TREE = {
    500: (400, ["sh", "-c", "cd /tmp && python3 -m contributor_tools.guarded_launcher run s"], False),
    400: (300, ["python3", "driver.py"], False),
    300: (200, ["bash", "-c", "for s in a b; do python3 driver.py; done"], False),
    200: (100, ["claude"], False),
    100: (1, ["-zsh"], True),
    1: (0, ["/init"], False),
}


def test_ledger_walk_claims_shells_and_stops_at_agent_host():
    host = TreeHost(TREE, 500)
    assert host.launching_parent()["pid"] == 500
    assert [row["pid"] for row in host.ledger_ancestors()] == [500, 300]  # python driver is a census worker


def test_ledger_walk_stops_at_interactive_terminal():
    tree = {600: (100, ["bash", "-c", "x"], False), 100: (1, ["-zsh"], True), 1: (0, ["/init"], False)}
    assert [row["pid"] for row in TreeHost(tree, 600).ledger_ancestors()] == [600]


def test_vanished_ancestor_fails_closed(tmp_path):
    tree = {500: (400, ["sh", "-c", "x"], False), 400: None}  # 400 is gone mid-lookup
    receipt = gl.run_job(make_spec(tmp_path, ["touch", "launched"]), TreeHost(tree, 500),
                         launch_ledger=tmp_path / "ledger")
    assert_not_launched(tmp_path, receipt, "launch_ledger_unavailable")


def test_second_launch_under_a_shared_ancestor_is_refused(tmp_path):
    # Two iterations of a loop: fresh sh -c each time, same outer bash.
    tree = dict(TREE)
    tree[501] = (400, ["sh", "-c", "cd /tmp && python3 -m contributor_tools.guarded_launcher run t"], False)
    ledger = tmp_path / "ledger"
    first = gl.run_job(make_spec(tmp_path, ["true"]), TreeHost(tree, 500), launch_ledger=ledger)
    second = gl.run_job(make_spec(tmp_path, ["touch", "launched"], output_root="o2",
                                  receipt_path="receipts/job2.json"), TreeHost(tree, 501), launch_ledger=ledger)
    assert first["status"] == "completed"
    assert second["refusal_reason"] == "parent_already_launched" and not (tmp_path / "launched").exists()


def test_failed_final_write_is_launcher_error_and_listed_by_verify_cleanup(tmp_path, monkeypatch):
    real = gl.write_json
    receipt = tmp_path / "receipts/job.json"

    def flaky(path, obj, exclusive=False):
        if gl.Path(path) == receipt and obj.get("status") != "running":
            raise OSError("synthetic: final write failed")
        return real(path, obj, exclusive)

    monkeypatch.setattr(gl, "write_json", flaky)
    gl.run_job(make_spec(tmp_path, ["true"]), FakeHost())
    report = gl.verify_cleanup(gl.Host(), receipt)
    assert report["primary_status"] == "running"
    assert [(f["kind"], f["status"]) for f in report["fallback_receipts"]] == [("final", "launcher_error")]
    assert report["cleanup_proof"]["proven"] is True


def test_huge_json_integer_is_a_spec_error(tmp_path):
    with pytest.raises(gl.SpecError):
        gl.validate_spec(make_spec(tmp_path, WRITE_OUTPUT, timeout_seconds=10**400))
