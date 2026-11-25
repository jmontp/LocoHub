#!/usr/bin/env python3
"""GT21-Q01 independent readback.

Recomputes a seeded sample of the assessment from the export tables with its own code (it imports nothing from the assessment
runner or its base module) and compares the result with the written assessment.jsonl lines. It also checks the whole
assessment files: one line per observation, line counts equal the export run summaries, status consistent with the checks, and
the summary totals equal the sum of the lines.

Sample: for each of the listed participants, up to 20 failed phase observations and 20 other phase observations (seeded random
choice from the assessment lines) plus up to 3 time observations. Recomputed: L1, L5 counts, L2 jumps on the 200 Hz time series
(and their mapping to the phase observations), missing samples, plate-dropout counts, the side check and S1 grid.
Run only through contributor_tools.guarded_launcher. scientific_approval is false.
"""
from __future__ import annotations

import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import json
from pathlib import Path
import random
import resource
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = "converted_datasets/reconversion_v2"
SEED = 20261202
HIP, KNEE, ANKLE = (-50.0, 150.0), (-30.0, 165.0), (-80.0, 50.0)
COP = {"cop_anterior": 0.5, "cop_vertical": 0.3, "cop_lateral": 0.3}
ANGLE_WORDS = ("pelvis_sagittal_angle", "thigh_sagittal_angle", "shank_sagittal_angle", "foot_sagittal_angle",
               "hip_flexion_angle", "knee_flexion_angle", "ankle_dorsiflexion_angle")
META = {"subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id", "task_info",
        "subject_metadata", "phase_ipsi", "time_s", "source_start_time_s", "source_end_time_s", "held_signals"}


def read_selected(path, wanted):
    """{(observation_id, reference_side): {column: array}} for the wanted keys only, streamed in small batches.
    Numeric columns are kept as lists of array slices (joined once per key); string columns keep the first value."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    parts = {}
    ids = pa.array(sorted({k[0] for k in wanted}), type=pa.string())
    skip = ("subject", "observation_type", "task", "task_id", "held_signals", "observation_id", "reference_side")
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for batch in pf.iter_batches(batch_size=2048, use_threads=False):
            keep = pc.is_in(batch.column("observation_id"), value_set=ids)
            if not pc.any(keep).as_py():
                continue
            b = batch.filter(keep)
            oid = np.asarray(b.column("observation_id").to_pylist(), dtype=object)
            side = np.asarray(b.column("reference_side").to_pylist(), dtype=object)
            num = {n: b.column(n).to_numpy(zero_copy_only=False).astype(float) for n in b.schema.names
                   if n not in skip and n not in ("task_info", "subject_metadata", "source_recording_id")}
            for key in wanted:
                idx = np.flatnonzero((oid == key[0]) & (side == key[1]))
                if not len(idx):
                    continue
                d = parts.setdefault(key, {})
                for n in b.schema.names:
                    if n in skip:
                        continue
                    if n in ("task_info", "subject_metadata", "source_recording_id"):
                        d.setdefault(n, [b.column(n)[int(idx[0])].as_py()])
                    else:
                        d.setdefault(n, []).append(num[n][idx])
    return {k: {n: (v if isinstance(v[0], str) else np.concatenate(v)) for n, v in d.items()} for k, d in parts.items()}


def bounds_for(col):
    for word, b in (("hip_flexion_angle", HIP), ("knee_flexion_angle", KNEE), ("ankle_dorsiflexion_angle", ANKLE)):
        if col.startswith(word):
            return b
    return None


def recompute(table, d):
    """Counts for one observation from raw arrays d (own code)."""
    data = {n: v for n, v in d.items() if n not in META and not isinstance(v, list)}
    out = {"L1": {}, "L5": {}, "missing_total": 0, "rows": len(next(iter(data.values())))}
    for n, v in data.items():
        out["missing_total"] += int(np.sum(~np.isfinite(v)))
        b = bounds_for(n) if n.endswith("_rad") else None
        if b:
            x = np.degrees(v[np.isfinite(v)])
            c = int(np.sum((x < b[0]) | (x > b[1])))
            if c:
                out["L1"][n] = c
        for k, lim in COP.items():
            if n.startswith(k) and n.endswith("_m"):
                x = v[np.isfinite(v)]
                c = int(np.sum(np.abs(x) > lim))
                if c:
                    out["L5"][n] = c
    sides = ("left", "right") if table == "time" else ("ipsi", "contra")
    out["dropout"] = {}
    for s in sides:
        g, m = data.get(f"grf_vertical_{s}_BW"), data.get(f"ankle_dorsiflexion_moment_{s}_Nm_kg")
        ok = np.isfinite(g) & np.isfinite(m)
        out["dropout"][s] = int(np.sum(ok & (g == 0.0) & (np.abs(m) > 0.3)))
    if table == "time":
        t = d["time_s"]
        jumps = {}
        for n, v in data.items():
            if n.endswith("_rad") and n.startswith(ANGLE_WORDS):
                ok = np.isfinite(v[1:]) & np.isfinite(v[:-1])
                dd = np.abs(np.diff(np.degrees(v)))
                idx = np.flatnonzero(ok & (dd > 30.0))
                if len(idx):
                    jumps[n] = [float(t[i + 1]) for i in idx]
        out["jumps"] = jumps
    else:
        ph = d["phase_ipsi"]
        out["grid_ok"] = bool(len(ph) == 150 and np.allclose(ph, np.linspace(0, 100, 150), rtol=0, atol=1e-9))
        bw = json.loads(d["subject_metadata"][0]).get("body_weight_N")
        ip = data["grf_vertical_ipsi_BW"] * bw if bw else None
        if ip is None or len(ip) != 150:
            out["s5"] = "unchecked"
        elif not np.isfinite(ip).all():
            out["s5"] = "missing"
        elif ip.max() < 20.0:
            out["s5"] = "unchecked"
        else:
            out["s5"] = "passed" if ip[:60].mean() > ip[90:].mean() else "failed"
    return out


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher")
    rnd = random.Random(SEED)
    roots = {s: ROOT / args.assessment_roots.split(",")[i] for i, s in enumerate(args.subjects.split(","))}
    report = {"task_id": "GT21-Q01 readback", "seed": SEED, "scientific_approval": False, "participants": {}, "failures": []}
    for s, aroot in roots.items():
        lines = [json.loads(x) for x in open(aroot / s / "assessment.jsonl")]
        by = {(l["table"], l["observation_id"], l["reference_side"]): l for l in lines}
        failed = [k for k, l in by.items() if k[0] == "phase" and l["status"] == "failed"]
        other = [k for k, l in by.items() if k[0] == "phase" and l["status"] != "failed"]
        tm = [k for k in by if k[0] == "time"]
        sample = rnd.sample(failed, min(20, len(failed))) + rnd.sample(other, min(20, len(other)))
        tsample = rnd.sample(tm, min(3, len(tm)))
        exp = ROOT / BASE / f"gt21_rb07_export_{s}"
        rs = json.loads((exp / "run_summary.json").read_text())
        part = {"lines": len(lines), "phase_lines": len(failed) + len(other), "time_lines": len(tm),
                "run_summary_phase": rs["phase_observations"], "run_summary_time": rs["continuous_observations"],
                "sample_phase": len(sample), "sample_time": len(tsample), "mismatches": 0}
        checks = {}
        if len(by) != len(lines):
            report["failures"].append(f"{s}: duplicate assessment lines")
        if part["phase_lines"] != rs["phase_observations"] or len(tm) != rs["continuous_observations"]:
            report["failures"].append(f"{s}: line counts differ from the run summary")
        for l in lines:   # status consistent with checks
            c = l["attributes"]["checks"]
            want = bool(l["attributes"]["problems"]) or any(c[k] == "failed" for k in ("L1", "L2", "L5"))
            if (l["status"] == "failed") != want:
                report["failures"].append(f"{s}: status inconsistent for {l['observation_id']}")
                break
        # time observations first (needed for the mapping); one recording at a time
        tkeys = {(k[1], k[2]) for k in tsample}
        need_rec = {by[k]["source_recording_id"] for k in sample}
        for k, l in by.items():
            if k[0] == "time" and l["source_recording_id"] in need_rec:
                tkeys.add((k[1], k[2]))
        jumps_by_rec = {}
        ordered = sorted(tkeys)
        for gi in range(0, len(ordered), 2):    # at most 2 recordings resident at a time
            tdata = read_selected(exp / "time.parquet", set(ordered[gi:gi + 2]))
            for (oid, side), d in tdata.items():
                r = recompute("time", d)
                jumps_by_rec[by[("time", oid, side)]["source_recording_id"]] = r["jumps"]
                if ("time", oid, side) in set(tsample):
                    e = by[("time", oid, side)]
                    bad = []
                    if r["missing_total"] != e["attributes"]["missing_samples_total"]:
                        bad.append("missing")
                    for n, c in r["L1"].items():
                        if e["failed_samples"].get(n, {}).get("L1") != c:
                            bad.append(f"L1 {n}")
                    for n, ts in r["jumps"].items():
                        if e["failed_samples"].get(n, {}).get("L2") != len(ts):
                            bad.append(f"L2 {n}")
                    if sum(len(v) for v in r["jumps"].values()) != sum(v.get("L2", 0) for v in e["failed_samples"].values()):
                        bad.append("L2 total")
                    if sum(r["dropout"].values()) != sum(v["samples"] for v in e["attributes"]["plate_dropout"].values()):
                        bad.append("dropout total")
                    if bad:
                        part["mismatches"] += 1
                        report["failures"].append({"observation": oid, "table": "time", "differences": bad})
            del tdata
        pdata = {}
        for i in range(0, len(sample), 10):
            pdata.update(read_selected(exp / "phase.parquet", {(k[1], k[2]) for k in sample[i:i + 10]}))
        for k in sample:
            _, oid, side = k
            e = by[k]
            d = pdata[(oid, side)]
            r = recompute("phase", d)
            bad = []
            if r["missing_total"] != e["attributes"]["missing_samples_total"]:
                bad.append("missing")
            if not r["grid_ok"]:
                bad.append("grid")
            l1 = {n: v["L1"] for n, v in e["failed_samples"].items() if "L1" in v}
            l5 = {n: v["L5"] for n, v in e["failed_samples"].items() if "L5" in v}
            if l1 != r["L1"]:
                bad.append(f"L1 {l1} != {r['L1']}")
            if l5 != r["L5"]:
                bad.append(f"L5 {l5} != {r['L5']}")
            start, end = float(d["source_start_time_s"][0]), float(d["source_end_time_s"][0])
            mapped = {}
            for n, ts in jumps_by_rec.get(e["source_recording_id"], {}).items():
                role = n
                for word in ("left", "right"):
                    if f"_{word}_" in n:
                        role = n.replace(f"_{word}_", "_ipsi_" if side == word else "_contra_")
                hits = [t for t in ts if start - 1e-9 <= t - 0.005 and t <= end + 1e-9]
                if hits:
                    mapped[role] = len(hits)
            l2 = {n: v["L2"] for n, v in e["failed_samples"].items() if "L2" in v}
            if l2 != mapped:
                bad.append(f"L2 mapped {l2} != {mapped}")
            if e["attributes"]["checks"]["S5"] != r["s5"]:
                bad.append(f"S5 {e['attributes']['checks']['S5']} != {r['s5']}")
            drop = {n: v["samples"] for n, v in e["attributes"]["plate_dropout"].items()}
            if sum(drop.values()) != sum(r["dropout"].values()):
                bad.append("dropout")
            if bad:
                part["mismatches"] += 1
                report["failures"].append({"observation": oid, "table": "phase", "differences": bad})
        del pdata
        report["participants"][s] = part
        print(json.dumps({s: part}), flush=True)
    # whole-set recount from every assessment.jsonl line (all participants), compared with the summary
    summ = json.loads((ROOT / args.summary).read_text())
    count = {"observations": 0, "status": {}, "checks": {}}
    for r in args.all_roots.split(","):
        for path in sorted((ROOT / r).glob("AB*/assessment.jsonl")):
            for x in open(path):
                l = json.loads(x)
                count["observations"] += 1
                count["status"][l["status"]] = count["status"].get(l["status"], 0) + 1
                for c, st in l["attributes"]["checks"].items():
                    d = count["checks"].setdefault(c, {})
                    d[st] = d.get(st, 0) + 1
    report["recount_from_lines"] = count
    if count["observations"] != summ["observations"] or count["status"] != summ["status"] or \
            {c: v for c, v in count["checks"].items()} != summ["totals_per_check"]:
        report["failures"].append("recount of all assessment lines differs from the summary")
    report["peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    report["status"] = "passed" if not report["failures"] else "failed"
    out = ROOT / args.output_root
    out.mkdir(parents=True, exist_ok=False)
    (out / "readback.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({"status": report["status"], "failures": report["failures"][:5], "peak_rss_mib": report["peak_rss_mib"]}))
    return 0 if report["status"] == "passed" else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subjects", required=True)
    p.add_argument("--assessment-roots", required=True, help="comma list, one batch root per subject (same order)")
    p.add_argument("--summary", required=True)
    p.add_argument("--all-roots", required=True, help="comma list of every batch root")
    p.add_argument("--output-root", required=True)
    return run(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
