#!/usr/bin/env python3
"""GT23-Q01 job specs for the guarded launcher (spec subcommand) and, later, the summary step."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import run_gt23_q01_assessment as q  # noqa: E402

AUDIT = "docs/quality/audits"


def build_spec(job, stage, subjects, version):
    out_root = f"{q.BASE}/gt23_q01_{job}{version}"
    b = {q.RUNNER: q.sha256_file(ROOT / q.RUNNER), "contributor_tools/guarded_launcher.py":
         q.sha256_file(ROOT / "contributor_tools/guarded_launcher.py"), q.README: q.sha256_file(ROOT / q.README)}
    for s in subjects:
        root = q.root_for(s)
        for n in ("run_summary.json", "observations.jsonl"):
            b[f"{root}/{n}"] = q.sha256_file(ROOT / root / n)
        b[f"{q.BASE}/gt23_e01_audit_{s}/audit_report.json"] = q.sha256_file(ROOT / q.BASE / f"gt23_e01_audit_{s}" / "audit_report.json")
    return {"job_id": f"gt23-q01-{job}{version}",
            "command": ["python3", q.RUNNER, "run", "--output-root", out_root, "--stage", stage, "--subjects", ",".join(subjects)],
            "cwd": str(ROOT), "output_root": out_root, "receipt_path": f"{AUDIT}/gt23-q01-{job}{version}-launcher-receipt.json",
            "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": [subjects[0]], "address_space_mib": q.ADDRESS_SPACE_MIB}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("spec")
    s.add_argument("--job", required=True, help="pilot or batch_ABxx")
    s.add_argument("--version", default="")
    r = sub.add_parser("summary")
    r.add_argument("--pattern", required=True)
    r.add_argument("--subjects", required=True)
    r.add_argument("--output-root", required=True)
    a = p.parse_args()
    if a.cmd == "summary":
        return summary(a.pattern, tuple(a.subjects.split(",")), a.output_root)
    if a.job == "pilot":
        spec = build_spec("pilot", "pilot", q.PILOT_SUBJECTS, a.version)
    else:
        subj = a.job.split("_")[1]
        spec = build_spec(a.job, "full", (subj,), a.version)
    from contributor_tools.guarded_launcher import validate_spec
    validate_spec(spec)
    path = ROOT / AUDIT / f"gt23-q01-{a.job}{a.version}-spec.json"
    with path.open("x") as f:
        json.dump(spec, f, indent=2)
    print(path)


# ---------------------------------------------------------------- summary
def summary(roots_pattern, subjects, out_root):
    """Combine the participant assessments, resolve the flags, decide the stairs pressure point. Read-only on inputs."""
    import os
    ass, tot, by_part = q.summarize(roots_pattern, None, subjects)
    cop = {}
    flight, s5, limitations, held, states = {}, {}, {}, {}, {}
    cycles_side = {}
    fail_by_task = {}
    worst, failing = [], []
    for s, a in ass.items():
        for task, v in a["foot_frame_cop_by_task"].items():
            d = cop.setdefault(task, {"observations": 0, "finite_samples": 0, "failed_L5_samples": 0, "observations_with_finite_cop": 0})
            for k in d:
                d[k] += v[k]
        for tid, v in a["flight_by_task"].items():
            d = flight.setdefault(tid, {"cycles_with_both_forces": 0, "flight_cycles": 0, "shares": []})
            d["cycles_with_both_forces"] += v["cycles_with_both_forces"]
            d["flight_cycles"] += v["flight_cycles"]
            d["shares"] += v["both_unloaded_shares"]
        for tid, v in a["side_check_s5_by_task"].items():
            d = s5.setdefault(tid, {})
            for k, n in v.items():
                d[k] = d.get(k, 0) + n
        for fl, v in a["limitations"].items():
            d = limitations.setdefault(fl, {"observations": 0, "recordings": 0, "by_participant": {}, "tasks": {}})
            d["observations"] += v["observations"]
            d["recordings"] += len(v["recordings"])
            d["by_participant"][s] = {"observations": v["observations"], "recordings": len(v["recordings"])}
            for t, n in v["tasks"].items():
                d["tasks"][t] = d["tasks"].get(t, 0) + n
        for c, n in a["held_columns_not_checked_no_column"].items():
            held[c] = held.get(c, 0) + n
        for ch, st in a["channel_states"].items():
            d = states.setdefault(ch, {})
            for k, n in st.items():
                d[k] = d.get(k, 0) + n
        for sd, n in a["cycles_by_reference_side"].items():
            cycles_side.setdefault(s, {})[sd] = n
        for t, v in a["failed_observations_by_task_and_limit"].items():
            d = fail_by_task.setdefault(t, {})
            for l, n in v.items():
                d[l] = d.get(l, 0) + n
        worst += a["worst_examples"]
        failing += [{**f, "participant": s} for f in a["failing_observations"]]
    flight_out = {}
    for tid, v in flight.items():
        sh = sorted(v["shares"])
        flight_out[tid] = {"cycles_with_both_forces": v["cycles_with_both_forces"], "flight_cycles": v["flight_cycles"],
                           "median_both_unloaded_share": sh[len(sh) // 2] if sh else None}
    res = {"task_id": q.TASK_ID, "scientific_approval": False, "subjects": list(subjects), "profile": q.PROFILE,
           "totals": tot, "by_participant": by_part, "failed_observations_by_task_and_limit": fail_by_task,
           "worst_examples": sorted(worst, key=lambda f: -abs(f["value"]))[:10],
           "failing_observations_listed": failing[:300], "failing_observations_total": sum(
               a["failing_observations_total"] for a in ass.values()),
           "channel_states_by_column": states, "held_columns_not_checked_no_column": held,
           "cycles_by_reference_side": cycles_side, "side_check_s5_by_task": s5, "flight_by_task": flight_out,
           "foot_frame_cop_by_task": cop, "limitations": limitations}
    # stairs rule (written before data, in PROFILE["stairs_cop_rule"])
    c06 = json.loads((ROOT / q.C06_SUMMARY).read_text())
    out_share = c06["cop_outside_foot_share_by_task"]
    slope = c06["ankle_moment_slope_by_task"]
    st = {"c06_summary": q.C06_SUMMARY, "c06_summary_sha256": q.sha256_file(ROOT / q.C06_SUMMARY),
          "outside_foot_share_stairs": out_share.get("stairs"), "outside_foot_share_normal_walk": out_share.get("normal_walk"),
          "ankle_moment_ratio_stairs": slope.get("stairs"), "ankle_moment_ratio_normal_walk": slope.get("normal_walk")}
    fin = sum(cop.get(t, {}).get("finite_samples", 0) for t in ("stair_ascent", "stair_descent"))
    bad = sum(cop.get(t, {}).get("failed_L5_samples", 0) for t in ("stair_ascent", "stair_descent"))
    st.update({"stairs_cop_finite_samples": fin, "stairs_cop_failed_L5_samples": bad,
               "stairs_cop_failed_L5_share": (bad / fin) if fin else None})
    hold = (fin == 0) or (bad / fin > 0.01) or (
        st["outside_foot_share_stairs"]["median"] > st["outside_foot_share_normal_walk"]["median"])
    st["decision"] = "hold" if hold else "keep_published"
    res["stairs_cop"] = st
    out = ROOT / out_root
    out.mkdir(parents=True, exist_ok=False)
    with open(out / "assessment_summary.json", "x") as f:
        json.dump(res, f, indent=1, allow_nan=False)
    print(json.dumps({"stairs_cop": st["decision"], "totals": tot}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
