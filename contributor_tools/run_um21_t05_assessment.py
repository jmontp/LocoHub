#!/usr/bin/env python3
"""UM21-T05 time assessment: the UM21-Q01 v3 limits on the continuous time table (L2 only), as a structured assessment.

Limits are those of run_um21_q01v3_assessment.py, unchanged in value and in rule:
  L2  change of more than 30 degrees between adjacent 100 Hz samples, on the published angle columns of the time table
      (pelvis, and thigh, shank, foot, hip, knee, ankle of each leg), only between two finite samples. This is the only limit
      applied to the time table. L1 (joint angle range) and L5 (centre-of-pressure range) are phase-table limits and stay
      there (the same split GT23-Q01 v2 uses: L2 on the time table, everything else per stride).
  Columns without a limit are 'unchecked'; missing or held columns are 'unchecked_all_missing'. A missing column is never a pass.
  A time observation that has an L2 jump is 'failed' in the full variant and left out of the filtered variant (an observation is
  the unit whose samples stay together). Frames held by rule P1 are NaN, so no jump is counted across them.

The phase assessment is NOT changed: package v4 phase statuses stay exactly as UM21-Q01 v3 assigned them (its L2 already runs on
the 100 Hz frame series and is mapped to the stride windows). This job only reports how the time-table jumps line up with the
v3 phase L2 failures (agreement evidence, not a rule): per channel, jumps inside stride windows that v3 also found, jumps v3
found that the time table does not show (and the reverse). Differences are expected for the pelvis (Vicon in the time table,
markers in the v3 L2 series) and are listed, not hidden.

Stages: ``pilot`` (the pilot time root) and ``full`` (the nine full time roots). Each root is hash-checked against its clean
launcher receipt. ``plan`` writes a guarded-launcher spec; ``run`` only through ``python3 -m contributor_tools.guarded_launcher``.
scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools import run_um21_q01v3_assessment as q01  # noqa: E402
from contributor_tools import run_um21_t05_time as t05  # noqa: E402
from contributor_tools import um21_time_export as tx  # noqa: E402

TASK_ID = "UM21-T05"
RUNNER = "contributor_tools/run_um21_t05_assessment.py"
VERSION = "v2"
AUDITS = t05.AUDITS
BASE = t05.BASE
RSS_CAP_MIB = 300.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3


def stage_time_stages(stage):
    return ["pilot"] if stage == "pilot" else [s for s in t05.STAGES if s != "pilot"]


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-assess-{stage}-{VERSION}", "spec": f"{AUDITS}/um21-t05-assess-{stage}-spec-{VERSION}.json",
            "output_root": f"{BASE}/um21_t05_assess_{stage}_{VERSION}",
            "receipt": f"{AUDITS}/um21-t05-assess-{stage}-launcher-receipt-{VERSION}.json"}


def stage_recordings(stage):
    out = []
    for s in stage_time_stages(stage):
        out += t05.stage_recordings(s)
    return sorted(out)


def verify_time_root(time_stage):
    """Hash every output of one time job against its clean launcher receipt. Returns (root, {relative path: sha256})."""
    p = t05.stage_paths(time_stage)
    r = json.loads((ROOT / p["receipt"]).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{p['receipt']} is not a clean completed run")
    if Path(r["spec"]["output_root"]).resolve() != (ROOT / p["output_root"]).resolve():
        raise ValueError("the receipt is for another output root")
    got = {}
    for o in r["outputs"]:
        h = q01.sha256_file(ROOT / p["output_root"] / o["path"])
        if h != o["sha256"]:
            raise ValueError(f"{p['output_root']}/{o['path']} differs from the hash in {p['receipt']}")
        got[o["path"]] = h
    return p["output_root"], got


def read_part(path):
    """One recording's time part -> (meta dict, time_s, {column: array}, held dict)."""
    import pyarrow.parquet as pq
    with open(path, "rb") as fh:
        t = pq.ParquetFile(fh, buffer_size=0).read(use_threads=False)
    meta = {c: t.column(c)[0].as_py() for c in tx.IDENTITY_STR}
    held = json.loads(t.column("held_signals")[0].as_py() or "{}")
    cols = {c: t.column(c).to_numpy(zero_copy_only=False).astype(float) for c in tx.time_columns()}
    return meta, t.column("time_s").to_numpy(zero_copy_only=False).astype(float), cols, held


def v3_l2_failures(path, recordings):
    """{(recording, leg, phase channel, frame)} of the UM21-Q01 v3 L2 failures of the selected recordings."""
    sel = {tx.recording_id(r): r for r in recordings}
    out = set()
    with open(path) as f:
        for line in f:
            x = json.loads(line)
            if x.get("limit") != "L2":
                continue
            rec = x["observation_id"].rsplit(":", 4)[0]
            if rec in sel:
                p = tx.parse_id(x["observation_id"])
                out.add((sel[rec], p["side"], x["channel"], int(x["frame"])))
    return out


def phase_windows(path, recordings):
    sel = {tx.recording_id(r): r for r in recordings}
    out = {}
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            r = sel.get(e["source_recording_id"])
            if r is not None:
                p = tx.parse_id(e["observation_id"])
                out.setdefault((r, p["side"]), []).append((p["a"], p["b"]))
    return out


def l2_agreement(time_fails, v3, windows, recordings):
    """Per channel family: time jumps total / inside a stride window of that leg / matched by a v3 phase L2 failure; v3
    failures not reproduced. Pelvis jumps are matched against either leg."""
    rows = {}
    time_keys = set()
    for x in time_fails:
        rec = x["recording"]
        legs = ("left", "right") if x["channel"] == tx.PELVIS else (("left",) if "_left_" in x["channel"] else ("right",))
        for leg in legs:
            ch = tx.phase_name(x["channel"], leg)
            inside = any(a <= x["frame"] + 1 <= b and a <= x["frame"] <= b for a, b in windows.get((rec, leg), []))
            time_keys.add((rec, leg, ch, x["frame"], inside))
            r = rows.setdefault(ch, {"time_jumps": 0, "inside_stride_windows": 0, "also_in_v3": 0})
            r["time_jumps"] += 1
            r["inside_stride_windows"] += int(inside)
            r["also_in_v3"] += int(inside and (rec, leg, ch, x["frame"]) in v3)
    seen = {(k[0], k[1], k[2], k[3]) for k in time_keys}
    v3_missing = {}
    for k in v3:
        if k[0] in recordings and k not in seen:
            v3_missing[k[2]] = v3_missing.get(k[2], 0) + 1
    return {"by_phase_channel": rows, "v3_phase_l2_failures_not_seen_in_time_table_by_channel": v3_missing,
            "v3_phase_l2_failures_total": len([k for k in v3 if k[0] in recordings])}


def build_spec(stage):
    p = stage_paths(stage)
    b = {}
    for rel in (RUNNER, "contributor_tools/run_um21_t05_time.py", t05.EXPORT, "contributor_tools/run_um21_q01v3_assessment.py",
                f"{t05.Q01_ROOT}/observations.jsonl", f"{t05.Q01_ROOT}/failures.jsonl"):
        b[rel] = q01.sha256_file(ROOT / rel)
    for ts in stage_time_stages(stage):
        rel = t05.stage_paths(ts)["receipt"]
        b[rel] = q01.sha256_file(ROOT / rel)
    return {"job_id": p["job_id"], "command": ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage],
            "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"], "bindings": b,
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 1024}],
            "expected_output_names": ["time_assessment.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": q01.sha256_file(path)}))


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    if q01._mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    started = time.time()
    recordings = stage_recordings(args.stage)
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    entries_total, fails_all, per_rec, parts = 0, [], {}, {}
    inputs = {}
    by_limit = {}
    with open(out / "time_observations.jsonl", "x") as fo, open(out / "time_failures.jsonl", "x") as ff:
        for ts in stage_time_stages(args.stage):
            root, hashes = verify_time_root(ts)
            summary = json.loads((ROOT / root / "time_summary.json").read_text())
            inputs[root] = {"time_summary_sha256": hashes["time_summary.json"]}
            for rec_info in summary["records"]:
                rec = rec_info["recording"]
                rel = rec_info["part"]
                if hashes[rel] != rec_info["sha256"]:
                    raise ValueError(f"{root}/{rel}: hash differs from time_summary.json")
                meta, t, cols, held = read_part(ROOT / root / rel)
                flags = tx.limitation_flags(rec_info["summary"])
                extra = {"force_published_by_leg": {leg: bool(v.get("force", {}).get("published")) for leg, v in rec_info["summary"]["legs"].items()},
                         "cop_published_by_leg": {leg: bool(v.get("cop", {}).get("published")) for leg, v in rec_info["summary"]["legs"].items()},
                         "glitch_frames_by_leg": {leg: v.get("glitch_frames") for leg, v in rec_info["summary"]["legs"].items()},
                         "pelvis_right_left_max_abs_diff_rad": rec_info["summary"].get("pelvis_right_left_max_abs_diff_rad"),
                         "pending_by_ruling": rec in tx.PENDING_BY_RULING}
                entry, fails = tx.build_time_entry(meta, t, cols, held, flags, extra)
                fo.write(json.dumps(entry, sort_keys=True) + "\n")
                for x in fails:
                    x = {**x, "recording": rec}
                    ff.write(json.dumps(x) + "\n")
                    fails_all.append(x)
                for lim in entry["failed_limits"]:
                    by_limit[lim] = by_limit.get(lim, 0) + 1
                entries_total += 1
                per_rec[rec] = {"rows": entry["rows"], "status": entry["status"], "failed_limits": entry["failed_limits"],
                                "l2_jumps": len(fails), "root": root, "part": rel, "sha256": rec_info["sha256"]}
                parts[rec] = {"path": f"{root}/{rel}", "sha256": rec_info["sha256"], "observation_id": entry["observation_id"]}
                del cols
                if _peak_rss_mib() > RSS_CAP_MIB:
                    raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    if sorted(per_rec) != recordings:
        raise ValueError("the time roots do not cover exactly the reviewed recordings")
    obs_path = ROOT / t05.Q01_ROOT / "observations.jsonl"
    agree = l2_agreement(fails_all, v3_l2_failures(ROOT / t05.Q01_ROOT / "failures.jsonl", recordings),
                         phase_windows(obs_path, recordings), set(recordings))
    assessment = {
        "task_id": TASK_ID, "version": VERSION, "stage": args.stage, "scientific_approval": False,
        "note": "automated structured assessment of the time table; independent review follows",
        "profile": {"based_on": q01.PROFILE["profile_id"], "applied_to_time_table": ["L2"], "L2_threshold_deg": tx.L2_JUMP_DEG,
                    "not_applied_to_time_table": ["L1", "L5", "L3"],
                    "why": "same limits as UM21-Q01 v3; L2 is the only limit evaluated on the time table, the others stay per stride on the phase table",
                    "review_status": "draft_limits_unreviewed_scientific_approval_false"},
        "phase_assessment": "unchanged (UM21-Q01 v3 statuses stay as they are; see l2_agreement for the cross-check)",
        "totals": {"time_observations": entries_total, "failed": sum(1 for r in per_rec.values() if r["status"] == "failed"),
                   "rows": sum(r["rows"] for r in per_rec.values()), "l2_jumps": len(fails_all)},
        "failed_by_limit_observations": by_limit, "l2_agreement": agree, "per_record": per_rec, "parts": parts,
        "inputs": inputs,
        "sidecar_files": {n: {"sha256": q01.sha256_file(out / n), "bytes": (out / n).stat().st_size}
                          for n in ("time_observations.jsonl", "time_failures.jsonl")},
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
        "code_sha256": {RUNNER: q01.sha256_file(ROOT / RUNNER), t05.EXPORT: q01.sha256_file(ROOT / t05.EXPORT)}}
    with open(out / "time_assessment.json", "x") as f:
        json.dump(t05._clean(assessment), f, indent=1, allow_nan=False)
    print(json.dumps({"totals": assessment["totals"], "failed_by_limit": by_limit, "peak_rss_mib": assessment["resources"]["peak_rss_mib"]}))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.stage) or 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
