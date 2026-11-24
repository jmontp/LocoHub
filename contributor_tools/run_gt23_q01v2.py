#!/usr/bin/env python3
"""GT23-Q01 assessment v2 (run under GT23-E02): the Q01 limits on the corrected export, with L2 applied to the time table only.

What changes against run_gt23_q01_assessment.py (which is imported, unchanged, for every other rule):

  Input   Per participant the E01 root with the recordings listed in the E02 summary left out, plus the E02 root that replaces
          them. The observation set must equal the E01 observation set exactly (same identities, same row counts).
  L2      CHOICE, written before any v2 result existed (the verifier of Q01 showed that on phase observations of long windows
          150 samples span 11 to 47 s, spacing up to 392 ms, so most phase L2 failures were resampling artifacts): L2 is
          applied to the TIME table only (adjacent 5 ms samples, limit 30 degrees, unchanged). A time-table failure is
          mapped to every phase observation of the same recording whose source span [start_index, end_index] contains both
          samples of the jump; that observation is marked failed on L2 with the source sample indices. Phase observations are
          not tested for L2 on their own 150 samples. The alternative (scaling the limit by the sample spacing) was not used:
          at 392 ms the scaled limit would be about 2,300 degrees and tests nothing.
  L1, L4, L5, L3, S1-S5  Unchanged (same code).
  Flag    'step_up_cop_held' for recordings carrying the E02 step-up note.

scientific_approval is false. Run only through contributor_tools.guarded_launcher.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
from pathlib import Path
import resource
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools import run_gt23_q01_assessment as q  # noqa: E402

TASK_ID = "GT23-E02 (Q01 v2)"
RUNNER = "contributor_tools/run_gt23_q01v2.py"
BASE = q.BASE
E02_PILOT_SUBJECTS = ("AB10", "AB13")   # the two participants with an unwrapped recording of the L2 failures; chosen before the run
READ_BATCH_ROWS_V2 = 2048   # smaller read batches than v1 (4096) to stay under the 300 MiB cap with two roots open; results do not depend on it
STEP_UP_FLAG = "step_up_cop_held"
L2_CHANNEL_PREFIXES = q.L2_PREFIXES

PROFILE_V2 = {
    **q.PROFILE,
    "profile_id": "gt23_q01_coarse_limits_v2",
    "change_against_v1": "L2 on the time table only, mapped to the phase observations that contain the jump; every other limit "
                         "and every number unchanged",
    "l2_choice_logged_before_results": "time table only and mapping (not scaling by sample spacing)",
}


def e02_root(subject):
    return f"{BASE}/gt23_pl_e02_batch_{subject}"


def e02_audit(subject):
    return f"{BASE}/gt23_pl_e02_audit_{subject}/audit_report.json"


def read_table_v2(path, kind, subject, lineage, time_ranges, sink, skip_recordings, drop_l2):
    """q.read_table with two additions: rows of skip_recordings are ignored; L2 can be dropped from the limits."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    seen, counts = set(), {"rows": 0, "observations": 0}
    state = {"cur": None}
    skip = pa.array(sorted(skip_recordings), type=pa.string())
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        names = pf.schema_arrow.names
        for need in q.STR_META + q.CLOCK_COLS + ((q.AXIS_COLS[1],) if kind == "time" else (q.AXIS_COLS[0],)):
            if need not in names:
                raise q.InputError(f"{path} lacks column {need}")
        columns = [c for c in names if c not in q.META_COLS]
        units = {c: q.unit_of(c) for c in columns}
        limits = {c: [l for l in q.column_limits(c) if not (drop_l2 and l[0] == "L2")] for c in columns}
        for c, lims in limits.items():
            for limit, _, _, scale in lims:
                if scale == "deg" and units[c] != "rad":
                    raise q.UnitError(f"{c} is in {units[c]!r}; limits are in degrees, convert first")
        for batch in pf.iter_batches(batch_size=READ_BATCH_ROWS_V2, use_threads=False):
            if len(skip):
                batch = batch.filter(pc.invert(pc.is_in(batch.column("source_recording_id"), value_set=skip)))
            n = batch.num_rows
            if not n:
                continue
            counts["rows"] += n
            enc = {c: batch.column(c).dictionary_encode() for c in q.STR_META}
            idx = {c: enc[c].indices.to_numpy(zero_copy_only=False) for c in q.STR_META}
            data = {c: batch.column(c).to_numpy(zero_copy_only=False).astype(float, copy=False)
                    for c in columns + list(q.CLOCK_COLS) + [q.AXIS_COLS[1] if kind == "time" else q.AXIS_COLS[0]]}
            change = np.flatnonzero((np.diff(idx["observation_id"]) != 0) | (np.diff(idx["reference_side"]) != 0)) + 1
            starts = [0] + [int(x) for x in change]
            ends = [int(x) for x in change] + [n]
            for a, e in zip(starts, ends):
                key = (enc["observation_id"].dictionary[int(idx["observation_id"][a])].as_py(),
                       enc["reference_side"].dictionary[int(idx["reference_side"][a])].as_py())
                strings = {}
                for c in q.CONST_STR:
                    if not np.all(idx[c][a:e] == idx[c][a]):
                        strings[c] = None
                    else:
                        strings[c] = enc[c].dictionary[int(idx[c][a])].as_py()
                cur = state["cur"]
                if cur is None or cur.key != key:
                    if cur is not None:
                        sink(*q.finish_observation(cur, lineage, subject, time_ranges))
                    if key in seen:
                        state.setdefault("repeated", []).append(key)
                    seen.add(key)
                    counts["observations"] += 1
                    cur = state["cur"] = q.Observation(key, kind, columns, limits)
                for c, v in list(strings.items()):
                    if v is None:
                        cur.meta_problems.add(c)
                        del strings[c]
                cur.feed(data, strings, a, e)
        if state["cur"] is not None:
            sink(*q.finish_observation(state["cur"], lineage, subject, time_ranges))
    return counts, columns, units, sorted(seen), state.get("repeated", [])


def phase_channel(time_channel, reference_side):
    """Time-table column (left/right words) -> phase-table column (ipsi/contra roles) for the observation's reference leg."""
    for word, other in (("left", "right"), ("right", "left")):
        if f"_{word}_rad" in time_channel:
            role = "ipsi" if reference_side == word else "contra"
            return time_channel.replace(f"_{word}_rad", f"_{role}_rad")
    return time_channel


def map_l2(entry, fails, hits):
    """Mark a phase observation failed on L2 because a time-table jump lies inside its span. hits: list of failure rows."""
    states = entry["plausibility"]["channel_states"]
    new_fails = []
    per_channel = {}
    for h in hits:
        channel = phase_channel(h["channel"], entry["reference_side"])
        row = {"observation_id": entry["observation_id"], "reference_side": entry["reference_side"], "table": "phase",
               "channel": channel, "limit": "L2", "sample_index": None,
               "mapped_from": {"table": "time", "observation_id": h["observation_id"], "sample_index": h["sample_index"],
                               "time_s": h["time_s"]},
               "value": h["value"], "reason": h["reason"] + " (time table, inside this observation's span)"}
        new_fails.append(row)
        per_channel[channel] = per_channel.get(channel, 0) + 1
    for ch in per_channel:
        for st in list(states):
            if ch in states[st]:
                states[st] = [c for c in states[st] if c != ch]
                if not states[st]:
                    del states[st]
        states.setdefault("fail", []).append(ch)
        states["fail"].sort()
    pl = entry["plausibility"]
    pl["failed_channels"] = sorted(set(pl["failed_channels"]) | set(per_channel))
    pl["failed_limits"] = sorted(set(pl["failed_limits"]) | {"L2"})
    for ch, n in per_channel.items():
        pl["failed_samples"].setdefault(ch, {})["L2"] = n
    entry["overall"] = "failed"
    return fails + new_fails


def l2_only_channels_checked_on_time_table(entry):
    """Phase channels with no limit left after dropping L2 are checked on the time table: label them so, not 'unchecked'."""
    states = entry["plausibility"]["channel_states"]
    moved = [c for c in states.get("unchecked", []) if c.endswith("_rad") and c.startswith(L2_CHANNEL_PREFIXES)]
    if moved:
        states["unchecked"] = [c for c in states["unchecked"] if c not in moved]
        if not states["unchecked"]:
            del states["unchecked"]
        states.setdefault("pass_jump_only_time_table", []).extend(moved)
        states["pass_jump_only_time_table"].sort()


def composite_lineage(e01_root, e02_dir, superseded):
    lin = {k: v for k, v in q.load_lineage(e01_root).items() if v["source_recording_id"] not in superseded}
    for k, v in q.load_lineage(e02_dir).items():
        if k in lin:
            raise q.InputError(f"identity {k} appears in both roots")
        lin[k] = v
    return lin


def check_e02_inputs(subject, e02_dir, e01_root):
    """Hashes of the E02 root equal its run summary, the E02 readback passed, and the superseded list matches."""
    rs = json.loads((e02_dir / "run_summary.json").read_text())
    for name in ("phase.parquet", "time.parquet", "observations.jsonl", "exclusions.jsonl", "authors_windows.jsonl",
                 "recordings.jsonl"):
        if q.sha256_file(e02_dir / name) != rs["sha256"][name]:
            raise q.InputError(f"{e02_dir}/{name} differs from the E02 run summary hash")
    sm = json.loads((e02_dir / "e02_summary.json").read_text())
    for name, digest in sm["sha256"].items():
        if q.sha256_file(e02_dir / name) != digest:
            raise q.InputError(f"{e02_dir}/{name} differs from the E02 summary hash")
    audit = json.loads((ROOT / e02_audit(subject)).read_text())
    if audit.get("status") != "pass":
        raise q.InputError(f"E02 readback of {subject} did not pass")
    return rs, sm, audit


def assess_participant(subject, out_dir):
    e01_dir = ROOT / q.root_for(subject)
    e02_dir = ROOT / e02_root(subject)
    fid = q.source_fidelity(subject, e01_dir)
    rs02, sm02, audit02 = check_e02_inputs(subject, e02_dir, e01_dir)
    superseded = {f"{subject}/{r}" for r in sm02["superseded_e01_recordings"]}
    lineage_e01 = q.load_lineage(e01_dir)
    lineage = composite_lineage(e01_dir, e02_dir, superseded)
    if set(lineage) != set(lineage_e01):
        raise q.InputError("the composite observation set differs from the E01 observation set")
    for k, v in lineage.items():
        if v["rows"] != lineage_e01[k]["rows"]:
            raise q.InputError(f"row count of {k} differs from E01")
    del lineage_e01
    gc.collect()
    out_dir.mkdir(parents=True, exist_ok=False)
    tot, started = q.new_totals(), time.time()
    l2_time = {}          # source_recording_id -> list of L2 failure rows of the time table
    mapped = {"phase_observations_failed_by_mapping": 0, "time_l2_failures": 0}
    with open(out_dir / "observations.jsonl", "x") as fo, open(out_dir / "failures.jsonl", "x") as ff:
        lin_note = {d["source_recording_id"]: False for d in lineage.values() if d["table"] == "time"}
        for sid in sm02["step_up_recordings_held"]:
            lin_note[f"{subject}/{sid}"] = True

        def _step_flag(entry):
            if lin_note.get(entry["source_recording_id"]):
                entry["limitations"].append(STEP_UP_FLAG)

        # time pass over the composite
        def time_sink(entry, fails):
            for f in fails:
                if f["limit"] == "L2":
                    l2_time.setdefault(entry["source_recording_id"], []).append(f)
                    mapped["time_l2_failures"] += 1
            if entry["plausibility"]["failed_samples_not_listed"]:
                for ch, d in entry["plausibility"]["failed_samples_not_listed"].items():
                    if d.get("L2"):
                        raise q.InputError(f"{entry['observation_id']}: L2 failures not listed; mapping would be incomplete")
            _step_flag(entry)
            fo.write(json.dumps(entry, allow_nan=False) + "\n")
            for f in fails:
                ff.write(json.dumps(f, allow_nan=False) + "\n")
            q.accumulate(tot, entry, fails)

        def phase_sink(entry, fails):
            lin = lineage[("phase", entry["observation_id"], entry["reference_side"])]
            hits = []
            a, b = lin["start_index"], lin["end_index"]
            for f in l2_time.get(entry["source_recording_id"], []):
                if a <= f["sample_index"] - 1 and f["sample_index"] <= b:
                    hits.append(f)
            l2_only_channels_checked_on_time_table(entry)
            if hits:
                fails = map_l2(entry, fails, hits)
                mapped["phase_observations_failed_by_mapping"] += 1
            _step_flag(entry)
            fo.write(json.dumps(entry, allow_nan=False) + "\n")
            for f in fails:
                ff.write(json.dumps(f, allow_nan=False) + "\n")
            q.accumulate(tot, entry, fails)

        sources = ((e01_dir, superseded), (e02_dir, set()))
        counts_t = {"rows": 0, "observations": 0}
        counts_p = {"rows": 0, "observations": 0}
        ids_t, ids_p, rep = [], [], []
        units_t = units_p = None
        for root, skip in sources:
            c, cols, units_t, ids, rp = read_table_v2(root / "time.parquet", "time", subject, lineage, {}, time_sink, skip, drop_l2=False)
            counts_t = {k: counts_t[k] + c[k] for k in counts_t}
            ids_t += ids
            rep += rp
        tr = {d["source_recording_id"]: (d["source_start_time_s"], d["source_end_time_s"])
              for (tbl, oid, side), d in lineage.items() if tbl == "time"}
        for root, skip in sources:
            c, cols, units_p, ids, rp = read_table_v2(root / "phase.parquet", "phase", subject, lineage, tr, phase_sink, skip, drop_l2=True)
            counts_p = {k: counts_p[k] + c[k] for k in counts_p}
            ids_p += ids
            rep += rp
    got = {("time", i[0], i[1]) for i in ids_t} | {("phase", i[0], i[1]) for i in ids_p}
    rs = fid["e01_run_summary"]
    problems = []
    if got != set(lineage):
        problems.append(f"S3 observations in the tables and in the lineage differ: {len(got ^ set(lineage))}")
    if rep:
        problems.append(f"S3 identities repeated in separate runs: {rep[:3]}")
    if counts_t["rows"] != rs["time_rows"] or counts_p["rows"] != rs["phase_rows"]:
        problems.append("S1 row counts differ from the E01 run summary (the observation set is the same, so must the rows)")
    for k, v in rs["observations"].items():
        if tot["by_kind"].get(k) != v:
            problems.append(f"S3 observation count of {k}: {tot['by_kind'].get(k)} != E01 {v}")
    pairs = {}
    for (tbl, oid, side), d in lineage.items():
        if tbl == "phase" and d["observation_type"] == "transfer":
            pairs.setdefault(oid, set()).add(side)
    unpaired = sorted(o for o, s in pairs.items() if s != {"left", "right"})
    if unpaired:
        problems.append(f"S3 transfers without both legs: {unpaired[:3]}")
    assessment = {
        "task_id": TASK_ID, "subject": subject, "scientific_approval": False,
        "note": "automated assessment v2 (L2 on the time table only, mapped to phase observations); independent review follows",
        "profile": PROFILE_V2,
        "inputs": {"e01_root": q.root_for(subject), "e02_root": e02_root(subject), "e01_source_fidelity": fid["file_hashes"],
                   "e01_readback": fid["e01_readback"],
                   "e02_run_summary_sha256": rs02["sha256"], "e02_readback_status": audit02["status"],
                   "e02_readback_sha256": q.sha256_file(ROOT / e02_audit(subject)),
                   "superseded_e01_recordings": sorted(superseded), "unit_evidence": fid["unit_evidence"],
                   "units_time_table": units_t, "units_phase_table": units_p},
        "table_problems": problems,
        "l2_mapping": {**mapped, "time_l2_recordings": {k: len(v) for k, v in l2_time.items()}},
        "counts": {"time": counts_t, "phase": counts_p, "observations": tot["observations"], "by_kind": tot["by_kind"]},
        "overall_counts": tot["overall"],
        "failed_observations_by_limit": tot["fail_obs_by_limit"],
        "failed_observations_by_task_and_limit": tot["fail_obs_by_task_limit"],
        "failed_samples_by_limit": tot["fail_samples_by_limit"],
        "failed_samples_by_limit_and_channel": tot["fail_samples_by_limit_channel"],
        "structural_failures_by_problem": tot["structural_fail_by_problem"],
        "worst_examples": sorted(tot["worst"], key=lambda f: -abs(f["value"]))[:10],
        "failing_observations": tot["failing"][:500],
        "failing_observations_total": len(tot["failing"]),
        "channel_states": tot["channel_states"],
        "held_columns_not_checked_no_column": tot["held_by_column"],
        "cycles_by_reference_side": tot["cycles_by_side"],
        "side_check_s5_by_task": tot["s5"],
        "flight_by_task": {k: {"cycles_with_both_forces": v["cycles_with_both_forces"], "flight_cycles": v["flight_cycles"],
                               "both_unloaded_shares": v["shares"]} for k, v in tot["flight"].items()},
        "foot_frame_cop_by_task": tot["cop_by_task"],
        "limitations": tot["limitations"],
        "sidecar_files": {n: {"sha256": q.sha256_file(out_dir / n), "bytes": (out_dir / n).stat().st_size}
                          for n in ("observations.jsonl", "failures.jsonl")},
        "resources": {"peak_rss_mib": round(q._peak_rss_mib(), 1), "wall_seconds": round(time.time() - started, 1)},
    }
    with open(out_dir / "assessment.json", "x") as f:
        json.dump(assessment, f, indent=1, allow_nan=False)
    return assessment


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > q.ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    subjects = tuple(args.subjects.split(","))
    if args.stage == "pilot" and subjects != E02_PILOT_SUBJECTS:
        raise SystemExit("refused: the pilot is exactly " + ",".join(E02_PILOT_SUBJECTS))
    if args.stage == "full" and (len(subjects) != 1 or subjects[0] not in q.SUBJECTS):
        raise SystemExit("refused: a full batch is exactly one participant")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rc = 0
    for s in subjects:
        if q._mem_available() < q.MIN_AVAILABLE_BYTES:
            raise MemoryError("less than 2 GiB available; stopped at a participant boundary")
        a = assess_participant(s, out / s)
        gc.collect()
        print(json.dumps({"subject": s, "observations": a["counts"]["observations"], "overall": a["overall_counts"],
                          "failed_observations_by_limit": a["failed_observations_by_limit"],
                          "l2_mapping": a["l2_mapping"], "table_problems": a["table_problems"],
                          "peak_rss_mib": a["resources"]["peak_rss_mib"]}), flush=True)
        if a["table_problems"]:
            rc = 1
        if q._peak_rss_mib() > q.RSS_CAP_MIB:
            raise MemoryError(f"peak RSS {q._peak_rss_mib():.0f} MiB above {q.RSS_CAP_MIB}; stopped")
    return rc


# ---------------------------------------------------------------- spec and summary
def build_spec(job, stage, subjects, version):
    from contributor_tools.guarded_launcher import validate_spec
    audit_dir = "docs/quality/audits"
    out_root = f"{BASE}/gt23_pl_q01v2_{job}{version}"
    b = {q.RUNNER: q.sha256_file(ROOT / q.RUNNER), RUNNER: q.sha256_file(ROOT / RUNNER),
         "contributor_tools/guarded_launcher.py": q.sha256_file(ROOT / "contributor_tools/guarded_launcher.py"),
         q.README: q.sha256_file(ROOT / q.README)}
    for s in subjects:
        for root in (q.root_for(s), e02_root(s)):
            for n in ("run_summary.json", "observations.jsonl"):
                b[f"{root}/{n}"] = q.sha256_file(ROOT / root / n)
        b[f"{e02_root(s)}/e02_summary.json"] = q.sha256_file(ROOT / e02_root(s) / "e02_summary.json")
        for p in (e02_audit(s), f"{BASE}/gt23_pl_e01_audit_{s}/audit_report.json"):
            b[p] = q.sha256_file(ROOT / p)
    spec = {"job_id": f"gt23-q01v2-{job}{version}",
            "command": ["python3", RUNNER, "run", "--output-root", out_root, "--stage", stage, "--subjects", ",".join(subjects)],
            "cwd": str(ROOT), "output_root": out_root, "receipt_path": f"{audit_dir}/gt23-q01v2-{job}{version}-launcher-receipt.json",
            "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["assessment.json"], "address_space_mib": q.ADDRESS_SPACE_MIB}
    validate_spec(spec)
    return spec, Path(ROOT / audit_dir / f"gt23-q01v2-{job}{version}-spec.json")


def summarize(v2_pattern, v1_pattern, subjects, out_root):
    """Before (v1 batches) and after (v2 batches) failure counts, per limit, per participant and for each observation."""
    before, after = {}, {}
    tb = {"observations": 0, "overall": {}, "by_limit": {}, "samples": {}}
    ta = {"observations": 0, "overall": {}, "by_limit": {}, "samples": {}}
    detail = {}
    for s in subjects:
        a1 = json.loads((ROOT / v1_pattern.format(s) / s / "assessment.json").read_text())
        a2 = json.loads((ROOT / v2_pattern.format(s) / s / "assessment.json").read_text())
        if a2["table_problems"]:
            raise q.InputError(f"{s}: table problems {a2['table_problems'][:2]}")
        for tot, a in ((tb, a1), (ta, a2)):
            tot["observations"] += a["counts"]["observations"]
            for k, v in a["overall_counts"].items():
                tot["overall"][k] = tot["overall"].get(k, 0) + v
            for k, v in a["failed_observations_by_limit"].items():
                tot["by_limit"][k] = tot["by_limit"].get(k, 0) + v
            for k, v in a["failed_samples_by_limit"].items():
                tot["samples"][k] = tot["samples"].get(k, 0) + v
        f1 = _failed_ids(ROOT / v1_pattern.format(s) / s / "observations.jsonl")
        f2 = _failed_ids(ROOT / v2_pattern.format(s) / s / "observations.jsonl")
        detail[s] = {"before_failed": len(f1), "after_failed": len(f2),
                     "failed_before_only": len(set(f1) - set(f2)), "failed_after_only": len(set(f2) - set(f1)),
                     "by_limit_before": a1["failed_observations_by_limit"], "by_limit_after": a2["failed_observations_by_limit"],
                     "l2_mapping": a2["l2_mapping"], "peak_rss_mib": a2["resources"]["peak_rss_mib"]}
        newly = sorted(set(f2) - set(f1))
        detail[s]["failed_after_only_examples"] = [list(x) for x in newly[:5]]
    res = {"task_id": TASK_ID, "scientific_approval": False, "subjects": list(subjects), "profile": PROFILE_V2,
           "before_v1": tb, "after_v2": ta, "by_participant": detail}
    out = ROOT / out_root
    out.mkdir(parents=True, exist_ok=False)
    with open(out / "assessment_summary.json", "x") as f:
        json.dump(res, f, indent=1, allow_nan=False)
    print(json.dumps({"before": tb, "after": ta}))
    return 0


def _failed_ids(path):
    out = []
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            if d["overall"] == "failed":
                out.append((d["table"], d["observation_id"], d["reference_side"]))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--subjects", required=True)
    ps = sub.add_parser("spec")
    ps.add_argument("--job", required=True, help="pilot or batch_ABxx")
    ps.add_argument("--version", default="")
    pm = sub.add_parser("summary")
    pm.add_argument("--v2-pattern", required=True)
    pm.add_argument("--v1-pattern", required=True)
    pm.add_argument("--subjects", required=True)
    pm.add_argument("--output-root", required=True)
    args = p.parse_args(argv)
    if args.step == "run":
        return run(args)
    if args.step == "summary":
        return summarize(args.v2_pattern, args.v1_pattern, tuple(args.subjects.split(",")), args.output_root)
    if args.job == "pilot":
        spec, path = build_spec("pilot", "pilot", E02_PILOT_SUBJECTS, args.version)
    else:
        subj = args.job.split("_")[1]
        spec, path = build_spec(args.job, "full", (subj,), args.version)
    with path.open("x") as f:
        json.dump(spec, f, indent=2)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
