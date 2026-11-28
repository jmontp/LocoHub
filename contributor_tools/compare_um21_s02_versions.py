#!/usr/bin/env python3
"""UM21-S02: compare two S02 output roots (for example v5 shared plane against v7 per-leg planes), read only.

One recording at a time, columns read in row-group batches. Reports, per subject, the change of each angle column
(new minus old, degrees: median per-stride offset, median per-stride rms after removing the offset, 95th percentile of
absolute difference) and the per-leg centre-of-pressure verdicts of both summaries. Writes one JSON to a new path.
Usage: compare_um21_s02_versions.py OLD_ROOT NEW_ROOT OUT.json
"""
import json
import os
import sys
from pathlib import Path

for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "1")
import numpy as np

ANGLES = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "thigh_angle", "shank_angle", "foot_angle")
N = 150


def read(path, columns):
    import pyarrow.parquet as pq
    out, ids = {c: [] for c in columns}, None
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        parts = []
        for b in pf.iter_batches(batch_size=15000, columns=["observation_id", *columns], use_threads=False):
            parts.append(b)
        for c in columns:
            out[c] = np.concatenate([p.column(c).to_numpy(zero_copy_only=False) for p in parts]).reshape(-1, N)
        ids = [x for p in parts for x in p.column("observation_id").to_pylist()][::N]
    return ids, out


def main(old_root, new_root, out_path):
    old_root, new_root = Path(old_root), Path(new_root)
    per_rec, per_subject = {}, {}
    for d in sorted((new_root / "components").glob("AB*/*")):
        rec = f"{d.parent.name}/{d.name}"
        io, a = read(old_root / "components" / rec / "s02.parquet", ANGLES)
        in_, b = read(d / "s02.parquet", ANGLES)
        if io != in_:
            raise SystemExit(f"{rec}: observation order differs")
        rows = {}
        for c in ANGLES:
            x, y = np.degrees(b[c] - a[c]), None
            ok = np.isfinite(x).all(axis=1)
            both_missing_change = int((np.isfinite(a[c]).any(axis=1) != np.isfinite(b[c]).any(axis=1)).sum())
            if ok.any():
                xx = x[ok]
                off = np.median(xx, axis=1)
                rows[c] = {"strides_compared": int(ok.sum()), "strides_present_in_only_one": both_missing_change,
                           "median_offset_deg": float(np.median(off)),
                           "median_rms_after_offset_deg": float(np.median(np.sqrt(np.mean((xx - off[:, None]) ** 2, axis=1)))),
                           "p95_abs_deg": float(np.percentile(np.abs(xx), 95)), "max_abs_deg": float(np.abs(xx).max())}
            else:
                rows[c] = {"strides_compared": 0, "strides_present_in_only_one": both_missing_change}
        per_rec[rec] = rows
        del a, b
    for rec, rows in per_rec.items():
        subj = rec.split("/")[0]
        for c, r in rows.items():
            if r["strides_compared"]:
                per_subject.setdefault(subj, {}).setdefault(c, []).append(r)
    subject_summary = {s: {c: {"recordings": len(v), "median_of_median_offset_deg": float(np.median([r["median_offset_deg"] for r in v])),
                               "median_of_rms_after_offset_deg": float(np.median([r["median_rms_after_offset_deg"] for r in v])),
                               "max_p95_abs_deg": float(max(r["p95_abs_deg"] for r in v))}
                           for c, v in cols.items()} for s, cols in per_subject.items()}
    sums = {}
    for name, root in (("old", old_root), ("new", new_root)):
        s = json.loads((root / "s02_summary.json").read_text())
        sums[name] = {f"{r['recording']}:{leg}": l["cop_gate"]["verdict"] for r in s["records"] for leg, l in r["legs"].items()}
        sums[name + "_peak_rss_mib"] = s["resources"]["peak_rss_mib"]
    legs = sorted(sums["new"])
    changes = {k: [sums["old"].get(k), sums["new"][k]] for k in legs if sums["old"].get(k) != sums["new"][k]}
    result = {"old": str(old_root), "new": str(new_root), "per_subject": subject_summary, "per_recording": per_rec,
              "cop_published_legs": {"old": sum(v == "pass" for v in sums["old"].values()),
                                     "new": sum(v == "pass" for v in sums["new"].values()), "of": len(legs)},
              "cop_verdict_changes_old_new": changes, "cop_verdicts_new": sums["new"],
              "peak_rss_mib": {"old": sums["old_peak_rss_mib"], "new": sums["new_peak_rss_mib"]}}
    with open(out_path, "x") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({"published": result["cop_published_legs"], "changes": changes}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
