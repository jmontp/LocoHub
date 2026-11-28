#!/usr/bin/env python3
"""UM21-T05: export the UMich 2021 treadmill recordings as continuous time series (100 Hz source clock, no resampling).

Rules are in um21_time_export.py. This runner only wires them to the verified inputs:

  * S02 v7 summary (um21_s02_frame_full_v7/s02_summary.json, hash-checked against its clean launcher receipt): the plate
    registration (axis, sign, belt tilt, fitted shift) and the centre-of-pressure verdict of each recording and leg. Nothing is
    re-fitted here, so the time table uses exactly the registration behind package v4.
  * UM21-Q01 v3 root (um21_q01v3_full, hash-checked against its clean launcher receipt): identity (subject, task, task_id) and
    the held columns of the phase strides (observations.jsonl), and the stride task_info of the phase part of each recording.
  * Streaming.mat, one recording at a time (markers, plates, Vicon pelvis and moments); body mass from ParticipantDetails.

Output (a NEW root per job; v4 and every earlier root are only read):
  parts/ABxx_<cond>.time.parquet   one continuous_recording observation per recording (reference_side 'none', left/right columns)
  time_summary.json                per recording: registration used, holds, force and CoP status, finite counts, hashes, peak RSS

Stages: ``pilot`` (the six package-pilot recordings: clean, held CoP both legs, reversed pelvis heading, plane-glitch stride,
plate-assignment hold) and ``full-b01`` .. ``full-b09`` (the 44 recordings in sorted order, five per job, the last four).
A full-bNN job needs a clean pilot receipt of the same bound code.

``plan``  writes and validates a guarded-launcher spec (reads only to hash bound files).
``run``   the job; only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json`` (nice 19, 768 MiB address space).
Memory: one recording resident (markers 18 x n x 3, plates 6 x 10 n, columns about 60 x n float64); Parquet row groups of 4096 rows.
scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # before pyarrow (768 MiB address-space cap)
import argparse
import gc
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools import run_um21_q01v3_assessment as q01  # noqa: E402  (receipt helpers, constants; bound by hash)
from contributor_tools import run_um21_s02_frame as s02  # noqa: E402
from contributor_tools import um21_time_export as tx  # noqa: E402

TASK_ID = "UM21-T05"
RUNNER = "contributor_tools/run_um21_t05_time.py"
EXPORT = "contributor_tools/um21_time_export.py"
VERSION = "v3"
AUDITS = q01.AUDITS
BASE = "converted_datasets/reconversion_v2"
Q01_ROOT = f"{BASE}/um21_q01v3_full"
Q01_RECEIPT = f"{AUDITS}/um21-q01v3-full-launcher-receipt.json"
S02_ROOT = q01.S02_ROOT
S02_RECEIPT = q01.S02_RECEIPT
S02_SUMMARY = f"{S02_ROOT}/s02_summary.json"
PILOT_RECORDINGS = q01.PILOT_RECORDINGS
ADDRESS_SPACE_MIB = 768
RSS_CAP_MIB = 300.0
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
ROWS_PER_GROUP = 4096
N_BATCHES = 9
STAGES = ("pilot",) + tuple(f"full-b{k:02d}" for k in range(1, N_BATCHES + 1))
EXPECTED_RECORDINGS = 44


# ------------------------------------------------------------------ inputs
def all_recordings():
    """The 44 recordings of package v4 (keys of the Q01 v3 assessment), sorted."""
    return sorted(json.loads((ROOT / Q01_ROOT / "assessment.json").read_text())["per_record"])


def stage_recordings(stage):
    if stage == "pilot":
        return list(PILOT_RECORDINGS)
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage}")
    recs = all_recordings()
    if len(recs) != EXPECTED_RECORDINGS:
        raise ValueError(f"expected {EXPECTED_RECORDINGS} recordings, the Q01 v3 job has {len(recs)}")
    return tx.batches(recs)[int(stage[-2:]) - 1]


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-time-{stage}-{VERSION}", "spec": f"{AUDITS}/um21-t05-time-{stage}-spec-{VERSION}.json",
            "output_root": f"{BASE}/um21_t05_time_{stage}_{VERSION}",
            "receipt": f"{AUDITS}/um21-t05-time-{stage}-launcher-receipt-{VERSION}.json"}


def verified_hashes():
    """sha256 of the bound input files named in the two clean launcher receipts (outputs only)."""
    return {"s02": q01.receipt_outputs(S02_RECEIPT), "q01": q01.receipt_outputs(Q01_RECEIPT)}


def read_phase_entries(path, recordings):
    """{recording id 'ABxx/cond': [assessment entries of the phase strides]} streamed from observations.jsonl."""
    want = {tx.recording_id(r): r for r in recordings}
    out = {r: [] for r in recordings}
    with open(path) as f:
        for line in f:
            e = json.loads(line)
            r = want.get(e["source_recording_id"])
            if r is not None:
                out[r].append({k: e[k] for k in ("observation_id", "reference_side", "subject", "task", "task_id", "held_signals",
                                                 "source_recording_id")})
    return out


def read_task_infos(part_path):
    import pyarrow.parquet as pq
    with open(part_path, "rb") as fh:
        t = pq.ParquetFile(fh, buffer_size=0).read(columns=["task_info"], use_threads=False)
    return set(t.column("task_info").to_pylist())


def part_schema():
    import pyarrow as pa
    cols = tx.time_columns()
    fields = [pa.field(c, pa.string()) for c in tx.IDENTITY_STR] + [pa.field("time_s", pa.float64())]
    fields += [pa.field(c, pa.float64()) for c in tx.CLOCKS] + [pa.field(c, pa.float64()) for c in cols]
    fields += [pa.field("held_signals", pa.string())]
    return pa.schema(fields)


def write_part(path, meta, result):
    """Stream one recording to a Parquet file in row groups of ROWS_PER_GROUP rows. Returns sha256."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    schema = part_schema()
    t, cols = result["time_s"], result["columns"]
    n = len(t)
    held_json = tx.dumps(result["held"])
    w = pq.ParquetWriter(str(path), schema, compression="zstd", store_schema=False)
    try:
        for lo in range(0, n, ROWS_PER_GROUP):
            hi = min(lo + ROWS_PER_GROUP, n)
            m = hi - lo
            arrays = []
            for f in schema:
                if f.name in tx.IDENTITY_STR:
                    arrays.append(pa.repeat(pa.scalar(meta[f.name], pa.string()), m))
                elif f.name == "held_signals":
                    arrays.append(pa.repeat(pa.scalar(held_json, pa.string()), m))
                elif f.name == "time_s":
                    arrays.append(pa.array(t[lo:hi], type=pa.float64()))
                elif f.name in tx.CLOCKS:
                    arrays.append(pa.repeat(pa.scalar(float(t[0] if f.name == "source_start_time_s" else t[-1]), pa.float64()), m))
                else:
                    arrays.append(pa.array(cols[f.name][lo:hi], type=pa.float64()))
            w.write_table(pa.Table.from_arrays(arrays, schema=schema), row_group_size=ROWS_PER_GROUP)
    finally:
        w.close()
    return q01.sha256_file(path)


def reload_check(path, result):
    """Row count, time axis and finite counts of the written file against the arrays that were written. Returns findings."""
    import pyarrow.parquet as pq
    findings = []
    finite = {c: 0 for c in tx.time_columns()}
    rows, last = 0, -1.0
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for b in pf.iter_batches(batch_size=ROWS_PER_GROUP, use_threads=False):
            ts = b.column("time_s").to_numpy(zero_copy_only=False)
            if rows == 0 and ts[0] != 0.0:
                findings.append("time_s does not start at 0")
            if not np.all(np.diff(ts) > 0) or ts[0] <= last and rows:
                findings.append("time_s not increasing")
            last = float(ts[-1])
            rows += len(ts)
            for c in finite:
                finite[c] += int(np.isfinite(b.column(c).to_numpy(zero_copy_only=False)).sum())
    if rows != len(result["time_s"]):
        findings.append(f"{rows} rows written, {len(result['time_s'])} expected")
    for c, k in finite.items():
        if k != int(np.isfinite(result["columns"][c]).sum()):
            findings.append(f"{c}: finite count differs after reload")
    return findings


def meta_for(recording, entries, infos, n, mass, summary):
    sub, cond = recording.split("/")
    subs = {e["subject"] for e in entries}
    if len(subs) != 1:
        raise ValueError(f"{recording}: the phase strides disagree on subject: {sorted(subs)}")
    subject = next(iter(subs))
    # A continuous treadmill recording spans several phase tasks (level, transition), so, as in the GT21 time table,
    # task = continuous_recording and task_id = the recording kind; the phase tasks stay in the phase table.
    task, task_id = "continuous_recording", "treadmill_recording"
    merged, dropped = tx.merge_task_info(infos)
    merged.update({"time_scope": "continuous_trial", "source_recording": tx.recording_id(recording), "condition": cond,
                   "frames": int(n), "sampling_rate_hz": tx.FRAME_HZ,
                   "clock": "time_s = (frame - 1) / 100; frame 1 is the first sample of the recording",
                   "plate_sampling": "force-plate force and centre of pressure at the plate samples that coincide with the 100 Hz frames (every 10th sample of the 1 kHz plate); no averaging or interpolation",
                   "force_units": "body weights = plate force in N / (body_mass_kg x 9.81)",
                   "body_mass_kg": mass, "body_mass_source": f"Streaming/{sub}/ParticipantDetails Bodymass (kg)",
                   "phase_strides_in_package_v4": len(entries), "task_info_keys_not_constant_across_strides": dropped})
    return {"subject": subject, "source_recording_id": tx.recording_id(recording),
            "observation_id": tx.time_observation_id(recording, n), "reference_side": "none",
            "observation_type": "continuous_recording", "task": task, "task_id": task_id, "task_info": tx.dumps(merged)}


# ------------------------------------------------------------------ spec and job
def bindings(stage, pilot_receipt=None):
    b = dict(s02.bindings())
    for rel in (RUNNER, EXPORT, "contributor_tools/run_um21_q01v3_assessment.py", S02_RECEIPT, S02_SUMMARY, Q01_RECEIPT,
                f"{Q01_ROOT}/assessment.json", f"{Q01_ROOT}/observations.jsonl"):
        b[rel] = q01.sha256_file(ROOT / rel)
    if pilot_receipt:
        b[pilot_receipt] = q01.sha256_file(ROOT / pilot_receipt)
    return b


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--recordings", ",".join(stage_recordings(stage))]
    if stage != "pilot":
        if not pilot_receipt:
            raise SystemExit("a full batch needs --pilot-receipt")
        cmd += ["--pilot-receipt", pilot_receipt]
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": bindings(stage, pilot_receipt), "timeout_seconds": 3600,
            "kill_after_seconds": 30, "poll_seconds": 15, "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": p["output_root"], "min_free_mib": 1024}],
            "expected_output_names": ["time_summary.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": q01.sha256_file(path), "recordings": stage_recordings(stage)}))


def check_pilot(rel):
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise SystemExit("refused: the pilot receipt is not a clean completed run")
    cmd = r["spec"]["command"]
    if cmd[cmd.index("--stage") + 1] != "pilot":
        raise SystemExit("refused: the receipt is not a pilot run")
    for f in (RUNNER, EXPORT):
        if r["spec"]["bindings"].get(f) != q01.sha256_file(ROOT / f):
            raise SystemExit(f"refused: the pilot ran different code than the current {f}")


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the reviewed sample for this stage")
    if args.stage != "pilot":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full batch needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    if q01._mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    for r in recordings:
        s02.um21.check_recording(r)
    hashes = verified_hashes()
    summary_path = ROOT / S02_SUMMARY
    if q01.sha256_file(summary_path) != hashes["s02"]["s02_summary.json"]:
        raise ValueError("s02_summary.json differs from its launcher receipt")
    s02_records = {r["recording"]: r for r in json.loads(summary_path.read_text())["records"]}
    obs_path = ROOT / Q01_ROOT / "observations.jsonl"
    if q01.sha256_file(obs_path) != hashes["q01"]["observations.jsonl"]:
        raise ValueError("observations.jsonl differs from its launcher receipt")
    entries_by_rec = read_phase_entries(obs_path, recordings)
    source = ROOT / s02.t04.SOURCE
    c03 = json.loads((ROOT / s02.t04.C03).read_text())["source"]
    st = source.stat()
    if (st.st_size, st.st_mtime_ns) != (c03["bytes"], c03["mtime_ns"]):
        raise ValueError("Streaming.mat size/mtime differ from the UM21-C03 record")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "parts").mkdir()
    started = time.time()
    import h5py
    records, part_hashes = [], {}
    with h5py.File(source, "r", rdcc_nbytes=1024 ** 2) as handle:
        for rec in recordings:
            if q01._mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            subject, cond = rec.split("/")
            entries = entries_by_rec[rec]
            if not entries or rec not in s02_records:
                raise ValueError(f"{rec}: no phase strides or no S02 record")
            part_rel = f"parts/{rec.replace('/', '_')}.parquet"
            q01_part = ROOT / Q01_ROOT / part_rel
            if q01.sha256_file(q01_part) != hashes["q01"][part_rel]:
                raise ValueError(f"{part_rel} differs from the Q01 v3 receipt")
            regs = {leg: tx.registration_from_summary(s02_records[rec]["legs"].get(leg)) for leg in ("right", "left")}
            holds = tx.holds_from_phase_entries(entries)
            mass = s02.um21.participant_mass(handle, subject)
            trial = handle[f"Streaming/{subject}/Tread/{cond}"]
            res = tx.process_time_recording(trial, rec, regs, holds, mass)
            meta = meta_for(rec, entries, read_task_infos(q01_part), res["summary"]["frames"], mass, res["summary"])
            path = out / "parts" / f"{subject}_{cond}.time.parquet"
            sha = write_part(path, meta, res)
            findings = reload_check(path, res)
            part_hashes[f"parts/{path.name}"] = sha
            records.append({"recording": rec, "observation_id": meta["observation_id"], "rows": res["summary"]["frames"],
                            "part": f"parts/{path.name}", "sha256": sha, "registration": {k: {kk: vv for kk, vv in v.items()} for k, v in regs.items()},
                            "holds_windows": {k: len(v) for k, v in holds.items()}, "held_columns": res["held"],
                            "summary": res["summary"], "task": meta["task"], "task_id": meta["task_id"],
                            "reload_findings": findings, "peak_rss_mib": round(_peak_rss_mib(), 1)})
            print(f"{rec} done, {res['summary']['frames']} frames, {len(res['held'])} held columns, peak RSS {_peak_rss_mib():.0f} MiB",
                  flush=True)
            del res, trial
            gc.collect()
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    after = source.stat()
    unchanged = (after.st_size, after.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
    summary = {"task_id": TASK_ID, "stage": args.stage, "version": VERSION, "scientific_approval": False,
               "note": "time export evidence only; independent readback and review follow", "recordings": recordings,
               "inputs": {"s02_summary_sha256": hashes["s02"]["s02_summary.json"], "q01_observations_sha256": hashes["q01"]["observations.jsonl"]},
               "code_sha256": {RUNNER: q01.sha256_file(ROOT / RUNNER), EXPORT: q01.sha256_file(ROOT / EXPORT)},
               "tolerance_rules_in_export": tx.TOLERANCES, "records": records, "part_sha256": part_hashes,
               "source_unchanged_after_run": unchanged,
               "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                             "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                             "wall_seconds": round(time.time() - started, 1)}}
    with open(out / "time_summary.json", "x") as f:
        json.dump(_clean(summary), f, indent=1, allow_nan=False)
    print(json.dumps({"peak_rss_mib": summary["resources"]["peak_rss_mib"], "source_unchanged": unchanged}))
    return 0 if unchanged and not any(r["reload_findings"] for r in records) else 1


def _clean(o):
    """JSON-safe copy: NaN/inf become None, numpy scalars become Python numbers, tuples become lists."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan", help="write and validate the job spec")
    pp.add_argument("--stage", choices=STAGES, required=True)
    pp.add_argument("--pilot-receipt")
    pr = sub.add_parser("run", help="the job; only through contributor_tools.guarded_launcher")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=STAGES, required=True)
    pr.add_argument("--recordings", required=True)
    pr.add_argument("--pilot-receipt")
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.stage, args.pilot_receipt) or 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
