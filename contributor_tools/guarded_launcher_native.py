#!/usr/bin/env python3
"""DRAFT native extension of the guarded launcher for ONE MATLAB label-export job (GT21-RB01). NOT REVIEWED, NOT RUN.

guarded_launcher.py cannot stop or clean up a Windows process, so AGENTS.md forbids MATLAB through it. This module is
the reviewed-extension candidate. It changes no limit of guarded_launcher.py and reuses its envelope check, binding
hashes, disk floors, census, memory readings and receipt writer. It runs exactly one fixed MATLAB command:

    matlab.exe -batch "gt21_rb01_label_export('<source>','<out>','<AB##>','<nonce>')" -singleCompThread

Differences from run_job, and why each is needed:
1. The command is NOT free-form. The spec names only subject, source root, output root and receipt; the executable,
   flags, script and function call are constants here, and the script must be bound by sha256. Every substituted
   value is checked against a small character set, so nothing can be injected into the PowerShell or MATLAB text.
2. Preconditions are the launcher's (envelope hash, bindings, output_root absent, disk floors, Linux AND Windows census
   with no worker, Linux available >= 3584 MiB, Windows free >= 2816 MiB), plus: the MATLAB install and the script
   exist, no MATLAB process is running, and the output volume floor is 5 GiB.
3. Launch: PowerShell Start-Process -PassThru starts MATLAB hidden with stdout and stderr redirected to the log (on
   S:, outside output_root). The Windows PID and process creation time are recorded; the command line must contain the
   per-run nonce. The tree (children by ParentProcessId) is the unit that is watched and stopped.
4. Watch every poll (15 s): tree working set (hard cap 2048 MiB), Windows free memory (stop below 2048 MiB), Linux
   available memory (stop below 2048 MiB), timeout, and a STOP request. Any unreadable reading counts as a breach.
5. Stop: only the verified tree. Before any signal the PID's creation time and the nonce in its command line must still
   equal the recorded values (PID reuse guard). Then taskkill /PID <pid> /T (graceful), 30 s grace, then /F /T.
   Nothing else on Windows is ever touched, and the stop path never names a process by image name.
6. After exit: the recorded tree must be gone (re-queried), the Windows census is compared with the one before launch,
   and a new MATLAB or Python worker is flagged (MathWorks background services are listed, not killed). Outputs are hashed.
   clean_success needs all of these. A job that left a process is never reported clean; verify_cleanup re-queries.
7. One launch per launching ancestor per boot uses the launcher's ledger (claim_launch_slot), unchanged.

Not covered (stated limits): a MATLAB that detaches from the tree before the first poll is invisible to the tree walk;
the Windows census after the run is the only check for it. Windows has no address-space limit equivalent here, so the
working-set cap is a polled guard (a fast allocation can overshoot between polls); MATLAB's own start-up is about 1 GB.
Review checklist: docs/maintainers/handoffs/GT21-RB01.json, field native_extension.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

from contributor_tools import guarded_launcher as gl

MATLAB_EXE = r"C:\Program Files\MATLAB\R2023b\bin\matlab.exe"
MATLAB_EXE_WSL = "/mnt/c/Program Files/MATLAB/R2023b/bin/matlab.exe"
SCRIPT = "contributor_tools/conversion_scripts/Gtech_2021/gt21_rb01_label_export.m"
SCRIPT_DIR = "contributor_tools/conversion_scripts/Gtech_2021"
SCHEMA = "locohub.guarded_launcher_native.receipt/1"
TIMEOUT_MAX_S = 1800
GRACE_S = 30
POLL_S = 15
WORKING_SET_CAP_MIB = 2048
RUNTIME_FLOOR_MIB = {"linux": 2048, "windows": 2048}
STARTUP_FLOOR_MIB = {"linux": 3584, "windows": 2816}
OUTPUT_FLOOR_MIB = 5 * 1024
SUBJECT = re.compile(r"AB\d\d")
WIN_PATH = re.compile(r"[A-Za-z]:\\[A-Za-z0-9_ .\-\\()]+")
NONCE = re.compile(r"[0-9a-f]{16}")
ALLOWED_SOURCE_ROOTS = (gl.REPO_ROOT / "contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET",
                        Path("/mnt/s/locomotion_data/gt21_author_mirror_2024_extracted"))
ALLOWED_OUTPUT_ROOTS = (gl.REPO_ROOT / "converted_datasets/reconversion_v2",)
REQUIRED = ("job_id", "subject", "source_root", "output_root", "receipt_path", "bindings", "timeout_seconds")
OPTIONAL = {"expected_output_names": []}


class NativeSpecError(ValueError):
    pass


def validate_native_spec(spec, limits=gl.ENVELOPE_LIMITS):
    """Normalised copy of a native spec; raises NativeSpecError. Stricter-only, like guarded_launcher.validate_spec."""
    if not isinstance(spec, dict):
        raise NativeSpecError("spec must be a JSON object")
    unknown = sorted(set(spec) - set(REQUIRED) - set(OPTIONAL))
    missing = [k for k in REQUIRED if k not in spec]
    if unknown or missing:
        raise NativeSpecError(f"unknown keys {unknown}; missing keys {missing}")
    s = {**OPTIONAL, **spec}
    if not isinstance(s["job_id"], str) or not re.fullmatch(r"[A-Za-z0-9_.\-]+", s["job_id"]):
        raise NativeSpecError("job_id: plain identifier required")
    if not isinstance(s["subject"], str) or not SUBJECT.fullmatch(s["subject"]):
        raise NativeSpecError("subject must look like AB06")
    for key in ("source_root", "output_root", "receipt_path"):
        if not isinstance(s[key], str) or not os.path.isabs(s[key]):
            raise NativeSpecError(f"{key}: absolute path required")
    out, receipt, src = Path(s["output_root"]), Path(s["receipt_path"]), Path(s["source_root"])
    if receipt.suffix != ".json" or out == receipt or out in receipt.parents:
        raise NativeSpecError("receipt_path must be a .json outside output_root")
    if not any(src == a or a in src.parents for a in ALLOWED_SOURCE_ROOTS):
        raise NativeSpecError("source_root must be inside a reviewed source location")
    if not any(a in out.parents for a in ALLOWED_OUTPUT_ROOTS):
        raise NativeSpecError("output_root must be inside a reviewed output location")
    if out == src or src in out.parents or out in src.parents:
        raise NativeSpecError("output_root must not contain or sit inside source_root")
    if not isinstance(s["bindings"], dict) or not all(
            isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in s["bindings"].values()):
        raise NativeSpecError("bindings: {path: lowercase sha256} required")
    if not {SCRIPT, "contributor_tools/guarded_launcher_native.py"} <= set(s["bindings"]):
        raise NativeSpecError("bindings must include the export script and this module")
    if not gl._positive(s["timeout_seconds"], "timeout_seconds") or s["timeout_seconds"] > TIMEOUT_MAX_S:
        raise NativeSpecError(f"timeout_seconds above the native maximum {TIMEOUT_MAX_S}")
    if not isinstance(s["expected_output_names"], list):
        raise NativeSpecError("expected_output_names: list required")
    return s


def to_windows_path(path):
    """wslpath -w, then a strict character check (no quotes, no shell or PowerShell metacharacters)."""
    done = subprocess.run(["wslpath", "-w", str(path)], capture_output=True, check=True, timeout=30)
    text = done.stdout.decode().strip()
    if not WIN_PATH.fullmatch(text):
        raise NativeSpecError(f"path has characters outside the reviewed set: {text!r}")
    return text


def matlab_expression(source_win, out_win, subject, nonce):
    if not (SUBJECT.fullmatch(subject) and NONCE.fullmatch(nonce)):
        raise NativeSpecError("subject or nonce outside the reviewed set")
    for p in (source_win, out_win):
        if not WIN_PATH.fullmatch(p):
            raise NativeSpecError("path outside the reviewed set")
    return f"gt21_rb01_label_export('{source_win}','{out_win}','{subject}','{nonce}')"


def start_script(expression, script_dir_win, log_win, nonce):
    """The one PowerShell text that starts MATLAB. Only values already matched against the strict patterns enter it."""
    if not (NONCE.fullmatch(nonce) and WIN_PATH.fullmatch(script_dir_win) and WIN_PATH.fullmatch(log_win)):
        raise NativeSpecError("start script inputs outside the reviewed set")
    arguments = f'-batch "addpath(\'{script_dir_win}\'); {expression}" -singleCompThread'
    return ("$ErrorActionPreference='Stop'\n"
            f"$p = Start-Process -FilePath '{MATLAB_EXE}' -ArgumentList '{arguments.replace(chr(39), chr(39) * 2)}' "
            f"-WindowStyle Hidden -PassThru -RedirectStandardOutput '{log_win}' "
            f"-RedirectStandardError '{log_win}.err'\n"
            "$c = Get-CimInstance Win32_Process -Filter \"ProcessId=$($p.Id)\"\n"
            "[pscustomobject]@{pid=[int]$p.Id; created=$c.CreationDate.ToUniversalTime().ToString('o')} "
            "| ConvertTo-Json -Compress")


PS_TREE = r"""$ErrorActionPreference='Stop'
$root = {pid}
$all = @(Get-CimInstance Win32_Process)
$seen = New-Object System.Collections.Generic.HashSet[int]
$queue = New-Object System.Collections.Generic.Queue[int]
$queue.Enqueue($root) | Out-Null
$rows = @()
while ($queue.Count -gt 0) {{
  $id = $queue.Dequeue()
  if (-not $seen.Add($id)) {{ continue }}
  foreach ($p in $all) {{
    if ($p.ProcessId -eq $id) {{
      $rows += [pscustomobject]@{{pid=[int]$p.ProcessId; ppid=[int]$p.ParentProcessId; name=$p.Name;
        cmdline=$p.CommandLine; ws=[long]$p.WorkingSetSize;
        created=$(if ($p.CreationDate) {{ $p.CreationDate.ToUniversalTime().ToString('o') }} else {{ $null }})}}
    }}
    if ($p.ParentProcessId -eq $id) {{ $queue.Enqueue([int]$p.ProcessId) }}
  }}
}}
[pscustomobject]@{{tree=$rows}} | ConvertTo-Json -Depth 4 -Compress"""


PS_NONCE = r"""$ErrorActionPreference='Stop'
$rows = @(Get-CimInstance Win32_Process | Where-Object {{ $_.Name -like 'matlab*' -and $_.CommandLine -and $_.CommandLine.Contains('{nonce}') }} |
  ForEach-Object {{ [pscustomobject]@{{pid=[int]$_.ProcessId; ppid=[int]$_.ParentProcessId; name=$_.Name; cmdline=$_.CommandLine; ws=[long]$_.WorkingSetSize;
    created=$(if ($_.CreationDate) {{ $_.CreationDate.ToUniversalTime().ToString('o') }} else {{ $null }})}} }})
[pscustomobject]@{{rows=$rows}} | ConvertTo-Json -Depth 4 -Compress"""


class NativeHost(gl.Host):
    """Adds the Windows tree queries and the taskkill stop. Tests replace every method that touches Windows."""

    def start_matlab(self, script):
        return json.loads(self._powershell(script, timeout=120))

    def windows_tree(self, pid):
        """Rows of the process tree rooted at pid; the root row is first if it still exists. Empty when gone."""
        data = json.loads(self._powershell(PS_TREE.format(pid=int(pid)), timeout=60))
        tree = data.get("tree") or []
        if isinstance(tree, dict):
            tree = [tree]
        return tree

    def find_matlab_by_nonce(self, nonce):
        """matlab* processes whose command line contains the run nonce (an orphan that left the recorded tree)."""
        if not NONCE.fullmatch(nonce):
            raise NativeSpecError("nonce outside the reviewed set")
        data = json.loads(self._powershell(PS_NONCE.format(nonce=nonce), timeout=60))
        rows = data.get("rows") or []
        return [rows] if isinstance(rows, dict) else rows

    def taskkill(self, pid, force):
        flags = "/F /T" if force else "/T"
        self._powershell(f"& taskkill.exe /PID {int(pid)} {flags} | Out-Null; 'ok'", timeout=60)


def tree_identity_ok(tree, identity):
    """The root row must still carry the recorded creation time and the run nonce (guards PID reuse)."""
    root = [r for r in tree if r["pid"] == identity["windows_pid"]]
    return bool(root) and root[0].get("created") == identity["created_utc"] \
        and identity["nonce"] in (root[0].get("cmdline") or "")


def stop_tree(host, identity, grace=None, sleep=time.sleep):
    """Graceful then forced stop of the verified tree. Returns the action list; never touches an unverified PID."""
    grace = GRACE_S if grace is None else grace
    actions = []
    tree = host.windows_tree(identity["windows_pid"])
    if not tree:
        return actions
    if not tree_identity_ok(tree, identity):
        actions.append({"action": "refused_identity_mismatch", "at_utc": gl.utcnow()})
        return actions
    host.taskkill(identity["windows_pid"], force=False)
    actions.append({"action": "taskkill_tree_graceful", "at_utc": gl.utcnow()})
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and host.windows_tree(identity["windows_pid"]):
        sleep(1)
    tree = host.windows_tree(identity["windows_pid"])
    if tree and tree_identity_ok(tree, identity):
        host.taskkill(identity["windows_pid"], force=True)
        actions.append({"action": "taskkill_tree_forced", "at_utc": gl.utcnow()})
    return actions


def adopt_orphan(host, identity, adoptions, attempts=3, sleep=time.sleep):
    """The recorded root has no row. If bin\\matlab.exe was only a stub, the real MATLAB carries the same nonce in its
    command line: record it in ``adoptions`` and make it the watched root. Returns True when one was adopted."""
    for attempt in range(attempts):
        rows = host.find_matlab_by_nonce(identity["nonce"])
        rows = [r for r in rows if r["pid"] != identity["windows_pid"]]
        if rows:
            ids = {r["pid"] for r in rows}
            roots = sorted((r for r in rows if r["ppid"] not in ids), key=lambda r: r.get("created") or "")
            root = roots[0]
            adoptions.append({"at_utc": gl.utcnow(), "from_pid": identity["windows_pid"],
                              "from_created_utc": identity["created_utc"], "to_pid": root["pid"],
                              "to_created_utc": root["created"], "name": root.get("name"),
                              "matches_found": len(rows)})
            identity["windows_pid"], identity["created_utc"] = root["pid"], root["created"]
            return True
        if attempt + 1 < attempts:
            sleep(2)
    return False


def prove_tree_gone(host, identity, attempts=20, sleep=time.sleep):
    for _ in range(attempts):
        if not host.windows_tree(identity["windows_pid"]):
            return {"proven": True, "basis": "recorded Windows process tree no longer exists"}
        sleep(0.5)
    return {"proven": False, "basis": "recorded Windows process tree still exists"}


def run_native_job(spec, host=None, spec_sha256=None, dry_run=False, launch_ledger=None, sleep=time.sleep):
    """One MATLAB job. Mirrors run_job: refuse with a receipt on any failed precondition, else launch and watch."""
    host = host or NativeHost()
    s = validate_native_spec(spec)
    receipt_path = Path(s["receipt_path"])
    log_path = receipt_path.with_suffix(".log")
    if receipt_path.exists() or log_path.exists():
        raise NativeSpecError("receipt or log path already exists; history is never overwritten")
    out_root = Path(s["output_root"])
    r = {"schema": SCHEMA, "job_id": s["job_id"], "status": None, "scientific_approval": False, "spec": s,
         "spec_sha256": spec_sha256, "module_sha256": gl.sha256_file(__file__),
         "launcher_sha256": gl.sha256_file(gl.__file__), "checked_at_utc": gl.utcnow(),
         "fixed_command": {"exe": MATLAB_EXE, "flags": ["-batch", "-singleCompThread"], "script": SCRIPT},
         "chaining": "none; no successor is started"}

    def refuse(reason, **facts):
        r.update(status="refused_precondition", refusal_reason=reason, **facts, finished_at_utc=gl.utcnow(),
                 launched=False)
        if not dry_run:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            gl.write_json(receipt_path, r, exclusive=True)
        return r

    envelope = gl.sha256_file(gl.REPO_ROOT / gl.ENVELOPE)
    if envelope != gl.ENVELOPE_REVIEWED_SHA256:
        return refuse("envelope_changed_since_review")
    if out_root.exists() or out_root.is_symlink():
        return refuse("output_root_exists")
    if not Path(MATLAB_EXE_WSL).is_file():
        return refuse("matlab_not_found")
    r["bindings_before"] = gl.hash_bindings(s["bindings"], gl.REPO_ROOT)
    bad = [k for k, v in r["bindings_before"].items() if not v["matches"]]
    if bad:
        return refuse("binding_mismatch", mismatched_bindings=bad)
    if not (Path(s["source_root"]) / "SubjectInfo.mat").is_file() or not (Path(s["source_root"]) / s["subject"]).is_dir():
        return refuse("source_not_found")
    disk = [{**i, "free_mib": host.disk_free_mib(i["path"]), "passes": None} for i in (
        {"path": str(out_root), "min_free_mib": OUTPUT_FLOOR_MIB},
        {"path": gl.ENVELOPE_LIMITS["c_drive_path"], "min_free_mib": gl.ENVELOPE_LIMITS["c_drive_free_mib_min"]})]
    for d in disk:
        d["passes"] = gl._at_least(d["free_mib"], d["min_free_mib"])
    r["disk_admission"] = disk
    if not all(d["passes"] for d in disk):
        return refuse("disk_admission")
    r["census_before"] = {}
    for side, fn in (("linux", host.linux_census), ("windows", host.windows_census)):
        try:
            r["census_before"][side] = fn()
        except Exception as exc:  # unassessed is never passing
            return refuse(f"{side}_census_unavailable", error=f"{type(exc).__name__}: {exc}")
        if r["census_before"][side]["workers"]:  # includes any running MATLAB
            return refuse(f"foreign_worker_{side}")
    mem = {"linux": host.linux_mem_available_mib(), "windows": r["census_before"]["windows"]["free_physical_mib"]}
    r["startup_memory"] = {k: {"available_mib": mem[k], "reserve_mib": STARTUP_FLOOR_MIB[k],
                               "passes": gl._at_least(mem[k], STARTUP_FLOOR_MIB[k])} for k in mem}
    if not all(v["passes"] for v in r["startup_memory"].values()):
        return refuse("startup_memory_reserve")
    if host.stop_requested:
        return refuse("stopped_by_request_before_launch")
    if dry_run:
        r.update(status="preflight_passed", launched=False)
        return r
    if launch_ledger is not None:
        parent = host.launching_parent()
        ancestors = [] if parent["interactive_terminal"] else host.ledger_ancestors()
        r["launch_ledger"] = {"parent": parent, **gl.claim_launch_slot(
            launch_ledger, host.boot_id(), parent, os.getpid(), ancestors)}
        if r["launch_ledger"].get("refused"):
            return refuse("parent_already_launched")

    nonce = secrets.token_hex(8)
    out_root.mkdir(parents=True)  # the script requires an existing, empty folder; the runner (this module) creates it
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    source_win, out_win = to_windows_path(s["source_root"]), to_windows_path(out_root)
    script_dir_win = to_windows_path(gl.REPO_ROOT / SCRIPT_DIR)
    expression = matlab_expression(source_win, out_win, s["subject"], nonce)
    t0 = time.monotonic()
    identity = {"windows_pid": None, "created_utc": None, "nonce": nonce, "launched_at_utc": gl.utcnow(),
                "log_path": str(log_path)}
    adoptions, start_error = [], None
    r.update(status="running", launched=True, process_identity=identity, adoptions=adoptions)
    try:
        launched = host.start_matlab(start_script(expression, script_dir_win, to_windows_path(log_path), nonce))
        identity["windows_pid"], identity["created_utc"] = launched["pid"], launched["created"]
    except BaseException as exc:  # a process may exist without a recorded identity: look for it by nonce
        start_error = {"error": f"{type(exc).__name__}: {exc}", "during": "start_matlab"}
        if not adopt_orphan(host, identity, adoptions, sleep=sleep):
            r.update(status="launcher_error", job_outcome="launcher_error", launcher_errors=[start_error],
                     clean_success=False, finished_at_utc=gl.utcnow(),
                     note="start failed and no matlab process with the nonce was found")
            gl.write_json(receipt_path, r, exclusive=True)
            return r
    gl.write_json(receipt_path, r, exclusive=True)
    guard = {"polls": 0, "peak_tree_working_set_mib": 0.0, "min_linux_available_mib": None,
             "min_windows_free_mib": None, "breach": None}
    actions, stop_reason, errors = [], None, [start_error] if start_error else []
    try:
        while True:
            tree = host.windows_tree(identity["windows_pid"])
            if not tree:
                if adopt_orphan(host, identity, adoptions, sleep=sleep):  # recorded in the receipt; keep watching it
                    continue
                break
            guard["polls"] += 1
            if not tree_identity_ok(tree, identity):
                stop_reason = "identity_mismatch_not_stopped"
                break
            ws = sum(row["ws"] for row in tree) / 1024**2
            guard["peak_tree_working_set_mib"] = round(max(guard["peak_tree_working_set_mib"], ws), 1)
            readings = {}
            for side, fn in (("linux", host.linux_mem_available_mib), ("windows", host.windows_free_mib)):
                try:
                    readings[side] = fn()
                except Exception:
                    readings[side] = None
            for side, key in (("linux", "min_linux_available_mib"), ("windows", "min_windows_free_mib")):
                if isinstance(readings[side], (int, float)):
                    old = guard[key]
                    guard[key] = round(readings[side] if old is None else min(old, readings[side]), 1)
            low = {k: v for k, v in readings.items() if not gl._at_least(v, RUNTIME_FLOOR_MIB[k])}
            if host.stop_requested:
                stop_reason = "stopped_by_request"
            elif time.monotonic() - t0 > s["timeout_seconds"]:
                stop_reason = "timed_out"
            elif ws > WORKING_SET_CAP_MIB:
                stop_reason, guard["breach"] = "stopped_working_set_cap", {"tree_working_set_mib": round(ws, 1)}
            elif low:
                stop_reason, guard["breach"] = "stopped_resource_guard", {"readings_mib": readings}
            if stop_reason:
                if stop_reason != "identity_mismatch_not_stopped":
                    actions += stop_tree(host, identity, sleep=sleep)
                break
            sleep(POLL_S)
    except BaseException as exc:  # stop what is verified, then record; nothing is retried
        errors.append({"error": f"{type(exc).__name__}: {exc}"})
        try:
            actions += stop_tree(host, identity, sleep=sleep)
        except BaseException as exc2:
            errors.append({"error": f"{type(exc2).__name__}: {exc2}", "during": "error stop"})
    gone = prove_tree_gone(host, identity, sleep=sleep)
    after = {}
    for side, fn in (("linux", host.linux_census), ("windows", host.windows_census)):
        try:
            after[side] = fn()
        except Exception as exc:
            after[side] = {"unavailable": f"{type(exc).__name__}: {exc}"}
    new_win = None if "unavailable" in after["windows"] else gl._windows_new_workers(
        r["census_before"]["windows"], after["windows"])
    outputs = gl.hash_outputs(out_root)
    names = {Path(f["path"]).name for f in outputs if "error" not in f}
    required = [f"labels_{s['subject']}.jsonl", f"subject_info_{s['subject']}.json", *s["expected_output_names"]]
    missing = [n for n in required if n not in names]
    bindings_after = gl.hash_bindings(s["bindings"], gl.REPO_ROOT)
    outcome = stop_reason or ("completed" if not errors else "launcher_error")
    if outcome == "completed" and missing:
        outcome = "failed_outputs_missing"  # root vanished and no orphan took over, yet nothing was written
    checks = {"tree_gone_proven": gone["proven"], "bindings_unchanged": all(v["matches"] for v in bindings_after.values()),
              "linux_no_new_worker": "unavailable" not in after["linux"] and not after["linux"].get("workers"),
              "windows_no_new_worker": None if new_win is None else not new_win,
              "outputs_hashed": all("error" not in f for f in outputs), "expected_outputs_present": not missing,
              "no_stop_needed": not actions}
    r.update(status=outcome, job_outcome=outcome, finished_at_utc=gl.utcnow(),
             wall_time_seconds=round(time.monotonic() - t0, 3), runtime_guard=guard, stop_actions=actions,
             launcher_errors=errors, adoptions=adoptions, tree_gone=gone, census_after=after, windows_new_workers=new_win,
             bindings_after=bindings_after, outputs=outputs, expected_outputs_missing=missing,
             log_sha256=gl.sha256_file(log_path) if log_path.exists() else None, checks=checks,
             clean_success=(outcome == "completed" and all(v is True for v in checks.values())),
             retry="never automatic")
    gl.write_json(receipt_path, r)
    return r


def main(argv=None):
    import argparse
    import signal
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    host = NativeHost()
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, lambda *_: setattr(host, "stop_requested", True))
    gl._lower_own_priority()
    spec_path = Path(args.spec)
    try:
        receipt = run_native_job(json.loads(spec_path.read_text()), host, spec_sha256=gl.sha256_file(spec_path),
                                 dry_run=args.dry_run, launch_ledger=gl.LEDGER_ROOT)
    except NativeSpecError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: receipt.get(k) for k in ("job_id", "status", "refusal_reason", "clean_success")}, indent=2))
    return 0 if receipt["status"] == "preflight_passed" or receipt.get("clean_success") else 1


if __name__ == "__main__":
    sys.exit(main())
