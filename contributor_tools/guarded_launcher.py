#!/usr/bin/env python3
"""Single-job guarded launcher (UM21-T02).

Implements the execution envelope and launch preconditions in
docs/quality/audits/pm01-um21-tread-pilot-handoff.json. One invocation runs
exactly one command and then stops. It never chains a successor, never accepts
a PID to wait on, and only ever signals the process group it created itself,
after verifying that group is the child's own (PGID == SID == leader PID), and
only while that leader is still unreaped (so the PGID cannot have been reused).

Usage (run under the AGENTS.md low-priority prefix):
    python3 -m contributor_tools.guarded_launcher run SPEC.json [--dry-run]
    python3 -m contributor_tools.guarded_launcher verify-cleanup RECEIPT.json

The job spec is a JSON object; see validate_spec() for its fields. Relative
paths resolve against ``cwd`` (default: repository root). The receipt is
written next to its log (``<receipt>.log``); neither may exist beforehand, and
neither may sit inside the output root.

PM-01 values are enforced here, not taken on trust from the spec: ENVELOPE_LIMITS
holds the reviewed values, the envelope file must still have the reviewed
sha256, and a spec may only be stricter (higher reserves and disk floors,
shorter timeout, grace and poll interval). The output volume (>= 5 GiB) and C:
(>= 1 GiB) floors are always added by the launcher.

Known limits (read before use):
- If the launcher itself is SIGKILLed or OOM-killed, nothing polls memory any
  more and the receipt stays 'running'. The job gets SIGTERM from
  PR_SET_PDEATHSIG on its timeout leader, which then applies its own
  --kill-after; even without that, GNU timeout ends it after timeout plus
  kill-after. Recovery is ``verify-cleanup`` on the running receipt.
- The stop path reaches Linux processes only. A native Windows step (e.g.
  MATLAB.exe through WSL interop) has no reviewed stop or cleanup action
  beyond the post-run 'new Windows worker' flag. No MATLAB/native job may use
  this launcher until a reviewed native extension exists.
- After SIGKILL the launcher waits for the leader to exit before reaping it.
  A member stuck in uninterruptible sleep (D state, e.g. on drvfs I/O) can
  block that final wait indefinitely; no further signal is sent, and the
  receipt stays 'running' until it returns.
- The census is conservative: any argv mentioning contributor_tools,
  reconversion_v2, matlab, opensim or locohub (even a grep or an editor), any
  Windows python.exe, or a concurrent pytest in the repository refuses launch.
  Ancestors are exempt only when they are not interpreters running code:
  a shell whose first argument is -c, an interactive shell, tmux, timeout,
  init, the agent host. A shell running a script file is not exempt.
- Launching is CLI-only: the census exempts the launcher's own PID only when
  its argv is ``-m contributor_tools.guarded_launcher`` or ``guarded_launcher.py``.
  A process that imports run_job is itself counted as a worker.
- One launch per launching ancestor per boot: the CLI claims exclusive ledger
  entries (boot_id plus PID and start ticks) for the nearest ancestor that is
  not a pure exec wrapper (timeout, nice, ionice, env, ...) and for every
  further ancestor, up to the first interactive terminal shell, agent host
  (claude, codex), tmux/screen or init, that is a shell, a driver (xargs, find,
  make, parallel, env, nohup, watch) or whose argv names guarded_launcher. If
  any of those entries already exists, the launch is refused. A loop, xargs,
  make, or a loop that starts a fresh ``sh -c`` per iteration therefore gets
  one launch only; the agent tool shell (a fresh ``zsh -c`` per call) gets one
  per call. The walk is bounded (64 ancestors) and fails closed if an ancestor
  disappears during the lookup. Still possible, and prohibited by policy rather
  than code: an interactive terminal shell (stdin is a tty) is exempt, so a
  person typing commands one after another - or a loop typed at that prompt,
  or a deliberately built pseudo-terminal - is not blocked; deleting the
  per-uid ledger directory or pointing TMPDIR elsewhere resets it; and
  separate parents (e.g. a cron entry per job) each get their own launch.
- Receipt fallbacks: if the first exclusive write of the running receipt
  fails, the terminal receipt is written to ``<receipt>.conflict-<leader_pid>.json``;
  if the final write of the primary receipt fails, the primary stays 'running'
  and the terminal receipt (status launcher_error) is written exclusively to
  ``<receipt>.final-<leader_pid>.json``. ``verify-cleanup`` lists both kinds.
- Escape blind spot: a descendant that calls setsid leaves the group and the
  PGID proof. The post-run census catches it only if it matches a worker rule;
  one with a neutral argv and cwd (e.g. ``python -c ...`` in /) is invisible.
  Only cgroup containment would close this.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = "docs/quality/audits/pm01-um21-tread-pilot-handoff.json"
ENVELOPE_REVIEWED_SHA256 = "9f204cfd9ba6b2beb256e4d962778183ec2dd4895fd5009591680cb479a8dee9"
# Values from the envelope's launch_preconditions and execution_envelope.
ENVELOPE_LIMITS = {
    "timeout_seconds_max": 3600,
    "kill_after_seconds_max": 30,
    "poll_seconds_max": 15,
    "startup_memory_mib_min": {"linux": 3584, "windows": 2816},
    "runtime_memory_mib_min": {"linux": 2048, "windows": 2048},
    "output_volume_free_mib_min": 5 * 1024,
    "c_drive_free_mib_min": 1024,
    "c_drive_path": "/mnt/c",
    "address_space_mib_max": 768,
}
SCHEMA = "locohub.guarded_launcher.receipt/2"
THREAD_ENV = {k: "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                                "ARROW_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
REQUIRED = ("job_id", "command", "output_root", "receipt_path", "bindings", "timeout_seconds",
            "startup_memory_mib", "runtime_memory_mib")
OPTIONAL = {"cwd": None, "kill_after_seconds": 30, "poll_seconds": 15, "disk_admission": [],
            "thread_env": THREAD_ENV, "expected_output_names": [], "address_space_mib": None}
# Command-line fragments that mark a LocoHub/native worker (case-insensitive).
LINUX_PATTERNS = ("contributor_tools", "reconversion_v2", "converted_datasets", "matlab",
                  "opensim", "locohub")
WINDOWS_PATTERNS = ("contributor_tools", "reconversion_v2", "locohub", "opensim")
# Python entry points that run repository code when started inside the repository.
REPO_ENTRY_POINTS = {"pytest", "py.test", "ipykernel", "ipykernel_launcher", "ipython", "jupyter",
                     "jupyter-lab", "jupyter-notebook", "jupyter-server", "jupyter-execute",
                     "jupyter-nbconvert"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
# Pure exec wrappers skipped when finding the launching parent for the ledger.
DRIVERS = {"xargs", "find", "make", "gmake", "parallel", "env", "nohup", "watch"}
AGENT_HOSTS = {"claude", "codex"}
WALK_BOUNDARIES = {"init", "systemd", "tmux", "screen"}
MAX_ANCESTOR_WALK = 64
WRAPPERS = {"timeout", "nice", "ionice", "env", "setsid", "nohup", "stdbuf", "time", "chrt",
            "taskset", "prlimit", "flock", "sudo", "doas", "unbuffer"}
LEDGER_ROOT = Path(tempfile.gettempdir()) / f"locohub_guarded_launcher_uid{os.getuid()}"
POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
PS_CENSUS = r"""$ErrorActionPreference='Stop'
$p = @(Get-CimInstance Win32_Process | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId; ppid=[int]$_.ParentProcessId; name=$_.Name; cmdline=$_.CommandLine; created=$(if ($_.CreationDate) { $_.CreationDate.ToUniversalTime().ToString('o') } else { $null })} })
$o = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{processes=$p; free_physical_kib=[long]$o.FreePhysicalMemory; last_boot_utc=$o.LastBootUpTime.ToUniversalTime().ToString('o')} | ConvertTo-Json -Depth 3 -Compress"""
PS_FREE = "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"
PR_SET_PDEATHSIG = 1


class SpecError(ValueError):
    pass


class PreconditionUnreadable(RuntimeError):
    """A startup reading could not be taken; a refusal receipt was written."""


class LauncherError(RuntimeError):
    pass


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj, exclusive=False):
    """Atomic replace for the receipt owner; exclusive create for a first write."""
    text = json.dumps(obj, indent=2, default=str) + "\n"
    if exclusive:
        with open(path, "x") as f:
            f.write(text)
        return
    tmp = Path(f"{path}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _positive(value, name):
    """Finite positive number; NaN and inf are rejected before any comparison."""
    try:
        ok = (not isinstance(value, bool) and isinstance(value, (int, float))
              and math.isfinite(value) and value > 0)
    except OverflowError:  # a JSON integer too large for a float
        ok = False
    if not ok:
        raise SpecError(f"{name}: finite positive number required")
    return value


def _at_least(value, floor):
    """NaN-safe admission comparison: an unreadable or non-finite value never passes."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= floor)


def validate_spec(spec, limits=ENVELOPE_LIMITS):
    """Return a normalized copy of a job spec, or raise SpecError.

    Unknown keys are rejected, so a spec cannot smuggle in a predecessor PID,
    a successor job, or any other field the reviewed envelope does not define.
    Thresholds may only be stricter than ``limits`` (the PM-01 values).
    """
    if not isinstance(spec, dict):
        raise SpecError("spec must be a JSON object")
    _check_limits(limits)
    unknown = sorted(set(spec) - set(REQUIRED) - set(OPTIONAL))
    missing = [k for k in REQUIRED if k not in spec]
    if unknown or missing:
        raise SpecError(f"unknown keys {unknown}; missing keys {missing}")
    s = {**OPTIONAL, **spec}
    if not isinstance(s["job_id"], str) or not s["job_id"]:
        raise SpecError("job_id: non-empty string required")
    if not (isinstance(s["command"], list) and s["command"]
            and all(isinstance(a, str) and a for a in s["command"])):
        raise SpecError("command: non-empty list of strings required")
    cwd = Path(s["cwd"]) if s["cwd"] else REPO_ROOT
    if not cwd.is_absolute() or not cwd.is_dir():
        raise SpecError("cwd: existing absolute directory required")
    s["cwd"] = str(cwd)
    for key in ("output_root", "receipt_path"):
        if not isinstance(s[key], str) or not s[key]:
            raise SpecError(f"{key}: path string required")
        s[key] = str(cwd / s[key])
    out, receipt = Path(s["output_root"]), Path(s["receipt_path"])
    if receipt.suffix != ".json":
        raise SpecError("receipt_path must end in .json")
    if out == receipt or out in receipt.parents:
        raise SpecError("receipt_path must be outside output_root")
    if not isinstance(s["bindings"], dict) or not s["bindings"] or not all(
            isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in s["bindings"].values()):
        raise SpecError("bindings: non-empty {path: lowercase sha256} required")
    for key in ("timeout_seconds", "kill_after_seconds", "poll_seconds"):
        _positive(s[key], key)
        if s[key] > limits[f"{key}_max"]:
            raise SpecError(f"{key} {s[key]} exceeds the PM-01 maximum {limits[f'{key}_max']}")
    if not isinstance(s["disk_admission"], list):
        raise SpecError("disk_admission: list required")
    lowest_disk = min(limits["output_volume_free_mib_min"], limits["c_drive_free_mib_min"])
    for item in s["disk_admission"]:
        if not isinstance(item, dict) or set(item) != {"path", "min_free_mib"}:
            raise SpecError("disk_admission items need exactly path and min_free_mib")
        _positive(item["min_free_mib"], "disk_admission.min_free_mib")
        if item["min_free_mib"] < lowest_disk:
            raise SpecError(f"disk_admission floor below the PM-01 minimum {lowest_disk} MiB")
    for key in ("startup_memory_mib", "runtime_memory_mib"):
        if not isinstance(s[key], dict) or set(s[key]) != {"linux", "windows"}:
            raise SpecError(f"{key}: exactly linux and windows required")
        for side in ("linux", "windows"):
            _positive(s[key][side], f"{key}.{side}")
            if s[key][side] < limits[f"{key}_min"][side]:
                raise SpecError(f"{key}.{side} below the PM-01 reserve {limits[f'{key}_min'][side]}")
    env = s["thread_env"]
    if not isinstance(env, dict) or any(env.get(k) != v for k, v in THREAD_ENV.items()):
        raise SpecError(f"thread_env must set {sorted(THREAD_ENV)} to '1'")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise SpecError("thread_env: string values required")
    if not isinstance(s["expected_output_names"], list):
        raise SpecError("expected_output_names: list required")
    if s["address_space_mib"] is not None:
        _positive(s["address_space_mib"], "address_space_mib")
        if s["address_space_mib"] > limits["address_space_mib_max"]:
            raise SpecError(f"address_space_mib above the PM-01 limit {limits['address_space_mib_max']}")
    return s


def _check_limits(limits):
    for key, value in limits.items():
        for v in (value.values() if isinstance(value, dict) else [value]):
            if not isinstance(v, str):
                _positive(v, f"envelope limit {key}")


def admission_items(s, limits=ENVELOPE_LIMITS):
    """Spec disk items plus the two envelope floors, which a spec cannot omit."""
    return [{"path": s["output_root"], "min_free_mib": limits["output_volume_free_mib_min"],
             "source": "envelope: output volume (S:)"},
            {"path": limits["c_drive_path"], "min_free_mib": limits["c_drive_free_mib_min"],
             "source": "envelope: C:"},
            *({**item, "source": "spec"} for item in s["disk_admission"])]


# ----------------------------------------------------------------- census ---

def _inside(path, root):
    try:
        return Path(path).resolve().is_relative_to(Path(root).resolve())
    except (OSError, ValueError, RuntimeError):
        return False


def _is_python(argv):
    return bool(argv) and Path(argv[0]).name.startswith("python")


def _python_targets_repo(argv, cwd, repo_root):
    """True when a python process runs repository code.

    Any path argument inside the repository counts, whatever the cwd. With the
    cwd inside the repository, so do -c code, an interactive interpreter, a
    repo module, and pytest/Jupyter entry points (module or console script).
    """
    if not _is_python(argv):
        return False
    for a in argv[1:]:
        if a.startswith("-") or not ("/" in a or a.endswith(".py")):
            continue
        p = Path(a)
        if not p.is_absolute():
            if not cwd:
                continue
            p = Path(cwd) / p
        if _inside(p, repo_root):
            return True
    if not cwd or not _inside(cwd, repo_root):
        return False
    args, i = argv[1:], 0
    while i < len(args):
        a = args[i]
        if a == "-c":
            return True
        if a == "-m":
            top = args[i + 1].split(".")[0] if i + 1 < len(args) else ""
            base = Path(cwd)
            return (top in REPO_ENTRY_POINTS or (base / top).is_dir()
                    or (base / f"{top}.py").is_file())
        if a in ("-W", "-X"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return Path(a).name in REPO_ENTRY_POINTS or _inside(Path(cwd) / a, repo_root)
    return True  # interactive interpreter inside the repository


def is_linux_worker(row, repo_root=REPO_ROOT):
    text = " ".join(row["argv"]).lower()
    return any(p in text for p in LINUX_PATTERNS) or _python_targets_repo(
        row["argv"], row.get("cwd"), repo_root)


def ancestor_is_exempt(row):
    """Ancestors may be exempt only if they are not interpreters running code.

    Python, MATLAB and OpenSim ancestors are never exempt, nor is a shell that
    runs a script file (a possible queue driver). Shells with -c or
    interactive shells, tmux, timeout, init and the agent host are exempt.
    """
    argv = row["argv"]
    name = Path(argv[0]).name.lstrip("-").lower() if argv else ""
    if _is_python(argv) or "matlab" in name or "opensim" in name:
        return False
    if name in SHELLS:
        return _shell_mode(argv) in ("command", "interactive")
    return True


def _shell_mode(argv):
    """'command' if the first argument after short options is -c (or a cluster
    such as -ec), 'interactive' with no arguments, else 'script'."""
    for a in argv[1:]:
        if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a):
            return "command"
        if a.startswith("-") and a not in ("-", "--"):
            continue
        return "script"
    return "interactive"


def is_launcher_cli(argv):
    """True only for ``python -m contributor_tools.guarded_launcher`` or the script path."""
    if not _is_python(argv):
        return False
    args = argv[1:]
    for i, a in enumerate(args):
        if a == "-m":
            return i + 1 < len(args) and args[i + 1] == "contributor_tools.guarded_launcher"
        if a in ("-c", "-"):
            return False
        if a in ("-W", "-X"):
            continue
        if a.startswith("-"):
            continue
        if i > 0 and args[i - 1] in ("-W", "-X"):
            continue
        return Path(a).name == "guarded_launcher.py"
    return False


def is_windows_worker(row):
    name = (row.get("name") or "").lower()
    text = (row.get("cmdline") or "").lower()
    return (name.startswith("matlab") or name.startswith("python") or name == "py.exe"
            or any(p in name or p in text for p in WINDOWS_PATTERNS))


def _trim(row):
    out = dict(row)
    if "argv" in out:
        out["cmdline"] = " ".join(out.pop("argv"))[:300]
    elif out.get("cmdline"):
        out["cmdline"] = out["cmdline"][:300]
    return out


class Host:
    """Real host access. Tests override census, memory and disk methods."""

    proc = Path("/proc")

    def __init__(self):
        self.stop_requested = False

    def boot_id(self):
        return (self.proc / "sys/kernel/random/boot_id").read_text().strip()

    def stat(self, pid):
        try:
            text = (self.proc / str(pid) / "stat").read_text()
        except OSError:
            return None
        rest = text[text.rindex(")") + 2:].split()
        return {"state": rest[0], "ppid": int(rest[1]), "pgid": int(rest[2]),
                "sid": int(rest[3]), "start_ticks": int(rest[19])}

    def _pids(self):
        for entry in os.scandir(self.proc):
            if entry.name.isdigit():
                yield int(entry.name)

    def group_members(self, pgid):
        members = []
        for pid in self._pids():
            st = self.stat(pid)
            if st and st["pgid"] == pgid:
                rss = 0
                try:
                    for line in (self.proc / str(pid) / "status").read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            rss = int(line.split()[1])
                except OSError:
                    pass
                members.append({"pid": pid, "state": st["state"],
                                "start_ticks": st["start_ticks"], "rss_kib": rss})
        return members

    def argv(self, pid):
        try:
            return [a for a in (self.proc / str(pid) / "cmdline").read_bytes()
                    .decode("utf-8", "replace").split("\0") if a]
        except OSError:
            return []

    def interactive_terminal(self, pid, argv):
        """An interactive shell whose stdin is a terminal (a person at a prompt)."""
        name = Path(argv[0]).name.lstrip("-") if argv else ""
        if name not in SHELLS or _shell_mode(argv) != "interactive":
            return False
        try:
            stdin = os.readlink(self.proc / str(pid) / "fd/0")
        except OSError:
            return False
        return stdin.startswith("/dev/pts/") or stdin.startswith("/dev/tty")

    def _ancestor(self, pid):
        st = self.stat(pid)
        if st is None:  # gone mid-lookup: never key on a dead PID
            raise LauncherError(f"ancestor {pid} disappeared during the ledger lookup")
        argv = self.argv(pid)
        return st, argv, {"pid": pid, "ppid": st["ppid"], "start_ticks": st["start_ticks"],
                          "cmdline": " ".join(argv)[:300]}

    def _parent_pid(self):
        return os.getppid()

    def launching_parent(self):
        """Nearest ancestor that is not a pure exec wrapper (the first ledger key)."""
        pid = self._parent_pid()
        for _ in range(MAX_ANCESTOR_WALK):
            st, argv, row = self._ancestor(pid)
            if pid <= 1 or not argv or Path(argv[0]).name not in WRAPPERS:
                return {**row, "interactive_terminal": self.interactive_terminal(pid, argv)}
            pid = st["ppid"]
        raise LauncherError("ancestor walk exceeded its bound")

    def ledger_ancestors(self):
        """Further ledger keys: every shell, driver or launcher-naming ancestor up to
        the first interactive terminal, agent host, tmux/screen or init."""
        rows, pid = [], self._parent_pid()
        for _ in range(MAX_ANCESTOR_WALK):
            if pid <= 1:
                return rows
            st, argv, row = self._ancestor(pid)
            name = Path(argv[0]).name.lstrip("-").lower() if argv else ""
            if (name in WALK_BOUNDARIES or name in AGENT_HOSTS
                    or (name == "node" and any("claude" in a for a in argv[1:3]))
                    or self.interactive_terminal(pid, argv)):
                return rows
            if (name in SHELLS or name in DRIVERS
                    or any("guarded_launcher" in a for a in argv)):
                rows.append(row)
            pid = st["ppid"]
        raise LauncherError("ancestor walk exceeded its bound")

    def address_space_limit(self, pid):
        """Soft 'Max address space' of a process as written by the kernel."""
        try:
            for line in (self.proc / str(pid) / "limits").read_text().splitlines():
                if line.startswith("Max address space"):
                    return line.split()[3]
        except OSError:
            return None
        return None

    def _ancestors(self):
        chain, pid = [], os.getppid()
        while pid > 1 and pid not in chain:
            chain.append(pid)
            st = self.stat(pid)
            pid = st["ppid"] if st else 0
        return chain

    def linux_census(self):
        me, ancestors = os.getpid(), set(self._ancestors())
        workers, exempt, count = [], [], 0
        for pid in self._pids():
            st = self.stat(pid)
            try:
                argv = [a for a in (self.proc / str(pid) / "cmdline").read_bytes()
                        .decode("utf-8", "replace").split("\0") if a]
            except OSError:
                continue
            if not st or not argv:
                continue
            count += 1
            try:
                cwd = os.readlink(self.proc / str(pid) / "cwd")
            except OSError:
                cwd = None
            row = {"pid": pid, "start_ticks": st["start_ticks"], "argv": argv, "cwd": cwd}
            if pid == me and is_launcher_cli(argv):
                exempt.append({**_trim(row), "why": "launcher itself (CLI)"})
            elif pid == me:
                workers.append({**_trim(row), "ancestor": False, "why": "library caller of run_job"})
            elif pid in ancestors and ancestor_is_exempt(row):
                exempt.append({**_trim(row), "why": "non-interpreter ancestor"})
            elif is_linux_worker(row) or pid in ancestors:
                workers.append({**_trim(row), "ancestor": pid in ancestors})
        return {"checked_at_utc": utcnow(), "boot_id": self.boot_id(), "process_count": count,
                "exempt": exempt, "workers": workers}

    def _powershell(self, script, timeout=120):
        exe = shutil.which("powershell.exe") or POWERSHELL
        done = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
                              cwd="/mnt/c" if os.path.isdir("/mnt/c") else None,
                              capture_output=True, timeout=timeout, check=True)
        return done.stdout.decode("utf-8", "replace").strip().lstrip("﻿")

    def windows_census(self):
        data = json.loads(self._powershell(PS_CENSUS))
        rows = data["processes"]
        workers = [_trim(r) for r in rows if is_windows_worker(r)]
        return {"checked_at_utc": utcnow(), "last_boot_utc": data["last_boot_utc"],
                "process_count": len(rows), "free_physical_mib": data["free_physical_kib"] / 1024,
                "workers": workers}

    def windows_free_mib(self):
        return int(self._powershell(PS_FREE, timeout=60)) / 1024

    def linux_mem_available_mib(self):
        for line in (self.proc / "meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
        raise RuntimeError("MemAvailable missing from /proc/meminfo")

    def disk_free_mib(self, path):
        anchor = Path(path)
        while not anchor.exists():
            anchor = anchor.parent
        return shutil.disk_usage(anchor).free / 1024**2


# ---------------------------------------------------------------- process ---

def _leader_exited(pid):
    """Exited without reaping (WNOWAIT keeps the PID, hence the PGID, reserved)."""
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def _live_others(host, pgid, pid):
    return [m for m in host.group_members(pgid) if m["pid"] != pid and m["state"] != "Z"]


def stop_group(host, pgid, pid, grace):
    """SIGTERM our own group, wait ``grace`` seconds, then SIGKILL if needed.

    Only called with a verified pgid == pid, while ``pid`` is unreaped.
    """
    if pgid != pid:
        raise LauncherError("refusing to signal a group the job does not lead")
    actions = []

    def send(sig):
        try:
            os.killpg(pgid, sig)
            actions.append({"signal": sig.name, "at_utc": utcnow(), "delivered": True})
        except ProcessLookupError:
            actions.append({"signal": sig.name, "at_utc": utcnow(), "delivered": False})

    send(signal.SIGTERM)
    end = time.monotonic() + grace
    while time.monotonic() < end:
        if _leader_exited(pid) and not _live_others(host, pgid, pid):
            return actions
        time.sleep(0.1)
    send(signal.SIGKILL)
    end = time.monotonic() + 10
    while time.monotonic() < end and not (_leader_exited(pid) and not _live_others(host, pgid, pid)):
        time.sleep(0.1)
    return actions


def prove_cleanup(host, identity, attempts=20, interval=0.5):
    """Cleanup proof from the envelope; never signals anything."""
    for attempt in range(1, attempts + 1):
        boot = host.boot_id()
        if boot != identity["boot_id"]:
            return {"checked_at_utc": utcnow(), "basis": "reboot", "proven": True,
                    "boot_id_at_launch": identity["boot_id"], "boot_id_now": boot,
                    "note": "The boot that ran the job has ended."}
        members = host.group_members(identity["pgid"])
        st = host.stat(identity["leader_pid"])
        same_leader = bool(st and st["start_ticks"] == identity["leader_start_ticks"])
        proven = not members and not same_leader
        if proven or attempt == attempts:
            return {"checked_at_utc": utcnow(), "basis": "same_boot_proc_scan", "proven": proven,
                    "boot_id_now": boot, "pgid_members": members,
                    "leader_pid_with_same_start_ticks_present": same_leader, "attempts": attempt}
        time.sleep(interval)


def hash_bindings(bindings, base):
    out = {}
    for rel, expected in bindings.items():
        path = Path(base) / rel
        try:
            actual, size = sha256_file(path), path.stat().st_size
        except OSError as exc:
            actual = None
            out[rel] = {"expected": expected, "actual": None, "error": type(exc).__name__}
        else:
            out[rel] = {"expected": expected, "actual": actual, "bytes": size}
        out[rel]["matches"] = actual == expected
    return out


def hash_outputs(root):
    """Hash every output file; a file that cannot be read is recorded, not raised."""
    root = Path(root)
    if not root.exists():
        return []
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() or p.is_symlink()):
        rel = path.relative_to(root).as_posix()
        try:
            if path.is_symlink():
                files.append({"path": rel, "symlink_to": os.readlink(path)})
            else:
                files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        except OSError as exc:
            files.append({"path": rel, "error": f"{type(exc).__name__}: {exc}"})
    return files


def _windows_new_workers(before, after):
    seen = {(w.get("pid"), w.get("created")) for w in before.get("workers", [])}
    return [w for w in after.get("workers", []) if (w.get("pid"), w.get("created")) not in seen]


def _child_setup(parent_pid, address_space_bytes, prctl):
    """Runs in the child before exec: die with the launcher; optional RLIMIT_AS."""
    def setup():
        if prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
        if os.getppid() != parent_pid:  # launcher already gone
            os._exit(125)
        if address_space_bytes:
            resource.setrlimit(resource.RLIMIT_AS, (address_space_bytes, address_space_bytes))
    return setup


def _libc_prctl():
    try:
        return ctypes.CDLL(None, use_errno=True).prctl
    except (OSError, AttributeError):
        return None


def claim_launch_slot(ledger_root, boot_id, parent, launcher_pid, ancestors=()):
    """Exclusive per-boot ledger entries for the launching parent and the qualifying
    ancestors above it. Refused if any entry already exists."""
    if parent["interactive_terminal"]:
        return {"claimed": False, "exempt": "interactive terminal shell"}
    folder = Path(ledger_root) / boot_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    keys, seen = [], set()
    for row in (parent, *ancestors):
        key = (row["pid"], row["start_ticks"])
        if key not in seen:
            seen.add(key)
            keys.append(row)
    entries = [folder / f"{row['pid']}-{row['start_ticks']}.json" for row in keys]

    def refused(entry):
        try:
            previous = json.loads(entry.read_text())
        except (OSError, ValueError):
            previous = "unreadable"
        return {"claimed": False, "refused": True, "entry": str(entry), "previous": previous,
                "keys": keys}

    for entry in entries:
        if entry.exists():
            return refused(entry)
    claimed = []
    for row, entry in zip(keys, entries):
        try:  # exclusive create also settles a race between two launchers
            write_json(entry, {"key": row, "launcher_pid": launcher_pid, "at_utc": utcnow()},
                       exclusive=True)
        except FileExistsError:
            return refused(entry)
        claimed.append(str(entry))
    return {"claimed": True, "entries": claimed, "keys": keys}


# ------------------------------------------------------------------- run ---

def run_job(spec, host=None, spec_sha256=None, dry_run=False, launch_ledger=None):
    """Check every precondition, run one job, and return its terminal receipt.

    ``launch_ledger`` (a directory) enables the one-launch-per-parent rule; the
    CLI always passes LEDGER_ROOT. Library callers are refused by the real census.
    """
    host = host or Host()
    s = validate_spec(spec)
    receipt_path = Path(s["receipt_path"])
    log_path = receipt_path.with_suffix(".log")
    if receipt_path.exists() or log_path.exists():
        raise SpecError("receipt or log path already exists; history is never overwritten")
    out_root = Path(s["output_root"])
    r = {"schema": SCHEMA, "job_id": s["job_id"], "status": None, "scientific_approval": False,
         "envelope": {"path": ENVELOPE, "reviewed_sha256": ENVELOPE_REVIEWED_SHA256,
                      "limits": ENVELOPE_LIMITS},
         "spec": s, "spec_sha256": spec_sha256, "launcher_sha256": sha256_file(__file__),
         "checked_at_utc": utcnow(), "chaining": "none; no successor is started"}

    def refuse(reason, **facts):
        r.update(status="refused_precondition", refusal_reason=reason, **facts,
                 finished_at_utc=utcnow(), launched=False)
        if not dry_run:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(receipt_path, r, exclusive=True)  # never replaces another receipt
        return r

    def unreadable(reason, exc):
        refuse(reason, error=f"{type(exc).__name__}: {exc}")
        raise PreconditionUnreadable(f"{reason}: {exc}") from exc

    try:
        r["envelope"]["sha256"] = sha256_file(REPO_ROOT / ENVELOPE)
    except OSError as exc:
        return refuse("envelope_unreadable", error=f"{type(exc).__name__}: {exc}")
    if r["envelope"]["sha256"] != ENVELOPE_REVIEWED_SHA256:
        return refuse("envelope_changed_since_review")
    if out_root.exists() or out_root.is_symlink():
        return refuse("output_root_exists")
    r["bindings_before"] = hash_bindings(s["bindings"], s["cwd"])
    bad = [k for k, v in r["bindings_before"].items() if not v["matches"]]
    if bad:
        return refuse("binding_mismatch", mismatched_bindings=bad)
    disk = []
    for item in admission_items(s):
        try:
            free = host.disk_free_mib(item["path"])
        except Exception as exc:
            unreadable("disk_free_unreadable", exc)
        disk.append({**item, "free_mib": free, "passes": _at_least(free, item["min_free_mib"])})
    r["disk_admission"] = disk
    if not all(d["passes"] for d in disk):
        return refuse("disk_admission")
    r["census_before"] = {}
    for side, fn in (("linux", host.linux_census), ("windows", host.windows_census)):
        try:
            r["census_before"][side] = fn()
        except Exception as exc:  # unassessed is never passing
            return refuse(f"{side}_census_unavailable", error=f"{type(exc).__name__}: {exc}")
        workers = r["census_before"][side]["workers"]
        if workers:
            ancestor = side == "linux" and any(w.get("ancestor") for w in workers)
            return refuse(f"foreign_worker_{side}" + ("_ancestor" if ancestor else ""))
    try:
        mem = {"linux": host.linux_mem_available_mib(),
               "windows": r["census_before"]["windows"]["free_physical_mib"]}
    except Exception as exc:
        unreadable("startup_memory_unreadable", exc)
    r["startup_memory"] = {side: {"available_mib": mem[side],
                                  "reserve_mib": s["startup_memory_mib"][side],
                                  "passes": _at_least(mem[side], s["startup_memory_mib"][side])}
                           for side in ("linux", "windows")}
    if not all(v["passes"] for v in r["startup_memory"].values()):
        return refuse("startup_memory_reserve")
    if out_root.exists() or out_root.is_symlink():  # re-check after the long hash
        return refuse("output_root_exists")
    if host.stop_requested:
        return refuse("stopped_by_request_before_launch")
    prctl = _libc_prctl()
    if prctl is None:
        return refuse("parent_death_signal_unavailable")
    if dry_run:
        r.update(status="preflight_passed", launched=False)
        return r
    if launch_ledger is not None:
        try:
            parent = host.launching_parent()
            ancestors = [] if parent["interactive_terminal"] else host.ledger_ancestors()
            r["launch_ledger"] = {"parent": parent, **claim_launch_slot(
                launch_ledger, host.boot_id(), parent, os.getpid(), ancestors)}
        except Exception as exc:
            return refuse("launch_ledger_unavailable", error=f"{type(exc).__name__}: {exc}")
        if r["launch_ledger"].get("refused"):
            return refuse("parent_already_launched")

    timeout, grace = s["timeout_seconds"], s["kill_after_seconds"]
    argv = ["timeout", "--signal=TERM", f"--kill-after={grace:g}s", f"{timeout:g}",
            "nice", "-n", "19", "ionice", "-c", "3", *s["command"]]
    env = {**os.environ, **s["thread_env"]}
    aspace = int(s["address_space_mib"] * 1024**2) if s["address_space_mib"] else None
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "xb") as log:
        t0 = time.monotonic()
        launched_at = utcnow()
        try:
            proc = subprocess.Popen(argv, cwd=s["cwd"], env=env, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                    preexec_fn=_child_setup(os.getpid(), aspace, prctl))
        except (OSError, subprocess.SubprocessError) as exc:  # nothing is running
            return refuse("launch_failed", error=f"{type(exc).__name__}: {exc}")
    pid = proc.pid
    identity = {"leader_pid": pid, "launched_at_utc": launched_at, "argv": argv,
                "log_path": str(log_path), "parent_death_signal": "SIGTERM",
                "parent_death_signal_set": True}  # setup raises before exec otherwise
    r.update(status="running", launched=True, process_identity=identity)
    group_ok, own_receipt, stop_reason, actions, orphans, errors = False, False, None, [], [], []
    guard = {"poll_seconds": s["poll_seconds"], "reserve_mib": s["runtime_memory_mib"], "polls": 0,
             "min_linux_available_mib": None, "min_windows_free_mib": None, "breach": None,
             "observed_address_space_limits": [], "observed_address_space_by_process": []}
    peak_group_rss = 0

    def observe_limits():
        for m in host.group_members(pid):
            limit = host.address_space_limit(m["pid"])
            if limit not in guard["observed_address_space_limits"]:
                guard["observed_address_space_limits"].append(limit)
            row = {"pid": m["pid"], "start_ticks": m["start_ticks"], "limit": limit,
                   "cmdline": " ".join(host.argv(m["pid"]))[:200]}
            seen = guard["observed_address_space_by_process"]
            if not any((x["pid"], x["start_ticks"], x["limit"], x["cmdline"])
                       == (row["pid"], row["start_ticks"], row["limit"], row["cmdline"]) for x in seen):
                seen.append(row)

    try:
        # Group identity first, so a later failure still leaves a verified group to stop.
        identity["pgid"], identity["sid"] = os.getpgid(pid), os.getsid(pid)
        group_ok = identity["pgid"] == pid == identity["sid"]
        identity["own_session_verified"] = group_ok
        identity["boot_id"] = host.boot_id()
        identity["leader_start_ticks"] = host.stat(pid)["start_ticks"]
        write_json(receipt_path, r, exclusive=True)
        own_receipt = True
        if not group_ok:
            raise LauncherError("child is not the leader of its own session and group")
        observe_limits()
        backstop = timeout + grace + 60
        next_poll = time.monotonic() + s["poll_seconds"]
        while not _leader_exited(pid):
            now = time.monotonic()
            if host.stop_requested:
                stop_reason = "stopped_by_request"
            elif now - t0 > backstop:
                stop_reason = "stopped_launcher_deadline"
            elif now >= next_poll:
                next_poll = now + s["poll_seconds"]
                guard["polls"] += 1
                members = host.group_members(pid)
                peak_group_rss = max(peak_group_rss, sum(m["rss_kib"] for m in members))
                observe_limits()
                readings = {}
                for side, fn in (("linux", host.linux_mem_available_mib),
                                 ("windows", host.windows_free_mib)):
                    try:
                        readings[side] = fn()
                    except Exception:
                        readings[side] = None  # unreadable counts as a breach
                for side, key in (("linux", "min_linux_available_mib"),
                                  ("windows", "min_windows_free_mib")):
                    v = readings[side]
                    if isinstance(v, (int, float)) and math.isfinite(v):
                        guard[key] = round(v if guard[key] is None else min(v, guard[key]), 1)
                low = {k: v for k, v in readings.items()
                       if not _at_least(v, s["runtime_memory_mib"][k])}  # None/NaN breach
                if low:
                    guard["breach"] = {"at_utc": utcnow(), "readings_mib": readings}
                    stop_reason = "stopped_resource_guard"
            if stop_reason:
                actions += stop_group(host, pid, pid, grace)
                break
            time.sleep(min(0.2, s["poll_seconds"]))
        if not _leader_exited(pid):  # SIGKILL was sent; it cannot be ignored
            os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
        orphans = _live_others(host, pid, pid)
        if orphans:  # descendants still in our group after the leader exited
            actions += stop_group(host, pid, pid, grace)
    except BaseException as exc:  # leader still unreaped here: stop it, then finalise
        errors.append({"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})
        try:
            if group_ok:
                actions += stop_group(host, pid, pid, grace)
            elif not _leader_exited(pid):  # unverified group: signal the leader PID only
                os.kill(pid, signal.SIGKILL)
                actions.append({"signal": "SIGKILL", "target": "leader_pid_only", "at_utc": utcnow()})
        except BaseException as exc2:
            errors.append({"error": f"{type(exc2).__name__}: {exc2}", "during": "error stop"})
            try:
                if group_ok:
                    os.killpg(pid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
                actions.append({"signal": "SIGKILL", "fallback": True, "at_utc": utcnow()})
            except ProcessLookupError:
                pass
    _, wstatus, usage = os.wait4(pid, 0)  # reap only now: no signal is sent after this line
    wall = time.monotonic() - t0
    code = os.waitstatus_to_exitcode(wstatus)
    proc.returncode = code
    # GNU timeout (the leader) exits 124 after TERM; after --kill-after it SIGKILLs its
    # group, itself included, so the leader reports -9. A child's fatal signal is
    # re-raised by timeout, so 137 never reaches us; -9 before the timeout is 'failed'.
    if stop_reason:
        outcome = stop_reason
    elif code == 0:
        outcome = "completed"
    elif code in (124, -signal.SIGKILL) and wall >= timeout:
        outcome = "timed_out"
    else:
        outcome = "failed"
    # Facts known at reap are recorded first, so they survive any later failure.
    r.update(status="launcher_error" if errors else outcome, job_outcome=outcome,
             finished_at_utc=utcnow(), exit_code=code, wall_time_seconds=round(wall, 3),
             peak_rss_kib_largest_process=usage.ru_maxrss, peak_group_rss_kib_sampled=peak_group_rss,
             runtime_guard=guard, stop_actions=actions, orphans_at_leader_exit=orphans,
             launcher_errors=errors, finalisation_errors=[], clean_success=False,
             retry="never automatic")
    _finalise(r, s, host, identity, group_ok, out_root, log_path, orphans)
    target = receipt_path if own_receipt else receipt_path.with_suffix(f".conflict-{pid}.json")
    try:
        write_json(target, r, exclusive=not own_receipt)
    except BaseException as exc:
        r["finalisation_errors"].append({"step": "receipt_write", "error": f"{type(exc).__name__}: {exc}"})
        r["status"], r["clean_success"] = "launcher_error", False
        fallback = receipt_path.with_suffix(f".final-{pid}.json")
        try:
            write_json(fallback, r, exclusive=True)
        except BaseException as exc2:
            print(f"guarded_launcher: terminal receipt not written ({exc}; {exc2})", file=sys.stderr)
    return r


def _finalise(r, s, host, identity, group_ok, out_root, log_path, orphans):
    """Post-reap facts. Every step is isolated; a failure is recorded, never raised."""
    def step(name, fn, default=None):
        try:
            return fn()
        except BaseException as exc:
            r["finalisation_errors"].append({"step": name, "error": f"{type(exc).__name__}: {exc}"})
            return default

    if group_ok and "boot_id" in identity:
        cleanup = step("cleanup_proof", lambda: prove_cleanup(host, identity),
                       {"proven": False, "basis": "cleanup_proof_failed"})
    else:
        cleanup = {"proven": False, "basis": "own_session_not_verified"}
    after = {}
    for side, fn in (("linux", host.linux_census), ("windows", host.windows_census)):
        try:
            after[side] = fn()
        except Exception as exc:
            after[side] = {"unavailable": f"{type(exc).__name__}: {exc}"}
    new_win = step("windows_compare", lambda: None if "unavailable" in after["windows"]
                   else _windows_new_workers(r["census_before"]["windows"], after["windows"]))
    bindings_after = step("bindings_after", lambda: hash_bindings(s["bindings"], s["cwd"]), {})
    envelope_after = step("envelope_after", lambda: sha256_file(REPO_ROOT / ENVELOPE))
    outputs = step("outputs", lambda: hash_outputs(out_root), [])
    log_sha = step("log_hash", lambda: sha256_file(log_path))
    names = {Path(f["path"]).name for f in outputs if "error" not in f}
    missing = [n for n in s["expected_output_names"] if n not in names]
    checks = {"cleanup_proven": cleanup.get("proven") is True,
              "bindings_unchanged": bool(bindings_after) and all(
                  v["matches"] for v in bindings_after.values()),
              "envelope_unchanged": envelope_after == ENVELOPE_REVIEWED_SHA256,
              "linux_no_new_worker": ("unavailable" not in after["linux"]
                                      and not after["linux"].get("workers")),
              "windows_no_new_worker": None if new_win is None else not new_win,
              "no_orphans_at_leader_exit": not orphans,
              "outputs_hashed": all("error" not in f for f in outputs),
              "expected_outputs_present": not missing}
    if r["finalisation_errors"] and r["status"] != "launcher_error":
        r["status"] = "launcher_error"
    r.update(cleanup_proof=cleanup, census_after=after, windows_new_workers=new_win,
             bindings_after=bindings_after, outputs=outputs, expected_outputs_missing=missing,
             log_sha256=log_sha, checks=checks,
             clean_success=(r["status"] == "completed" and not r["finalisation_errors"]
                            and all(v is True for v in checks.values())))


def fallback_receipts(receipt):
    """Sibling terminal receipts written when the primary could not be used."""
    receipt = Path(receipt)
    found = []
    for kind in ("final", "conflict"):
        for path in sorted(receipt.parent.glob(f"{receipt.stem}.{kind}-*.json")):
            try:
                status = json.loads(path.read_text()).get("status")
            except (OSError, ValueError) as exc:
                status = f"unreadable: {type(exc).__name__}"
            found.append({"path": str(path), "kind": kind, "status": status})
    return found


def verify_cleanup(host, receipt):
    """Re-run the cleanup proof for a receipt and report any fallback receipts."""
    fallbacks = fallback_receipts(receipt)
    try:
        data = json.loads(Path(receipt).read_text())
    except (OSError, ValueError) as exc:
        data = {"unreadable": f"{type(exc).__name__}: {exc}"}
    identity = data.get("process_identity")
    if identity and "boot_id" in identity and "pgid" in identity:
        proof = prove_cleanup(host, identity, attempts=1)
    else:
        proof = {"proven": False, "basis": "no process identity in the primary receipt"}
    return {"receipt": str(receipt), "primary_status": data.get("status"),
            "cleanup_proof": proof, "fallback_receipts": fallbacks}


def _lower_own_priority():
    os.setpriority(os.PRIO_PROCESS, 0, 19)
    subprocess.run(["ionice", "-c", "3", "-p", str(os.getpid())], check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="check preconditions and run exactly one job")
    run.add_argument("spec")
    run.add_argument("--dry-run", action="store_true", help="preconditions only; write nothing")
    ver = sub.add_parser("verify-cleanup", help="re-run the cleanup proof for a receipt")
    ver.add_argument("receipt")
    args = ap.parse_args(argv)
    host = Host()
    if args.cmd == "verify-cleanup":
        receipt = Path(args.receipt)
        print(json.dumps(verify_cleanup(host, receipt), indent=2))
        return 0

    def request_stop(signum, _frame):
        host.stop_requested = True

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, request_stop)
    _lower_own_priority()
    spec_path = Path(args.spec)
    try:
        receipt = run_job(json.loads(spec_path.read_text()), host,
                          spec_sha256=sha256_file(spec_path), dry_run=args.dry_run,
                          launch_ledger=LEDGER_ROOT)
    except SpecError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except PreconditionUnreadable as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({k: receipt.get(k) for k in ("job_id", "status", "refusal_reason",
                                                    "exit_code", "clean_success")}, indent=2))
    if receipt["status"] in ("refused_precondition", "preflight_passed"):
        return 0 if receipt["status"] == "preflight_passed" else 3
    return 0 if receipt["clean_success"] else 1


if __name__ == "__main__":
    sys.exit(main())
