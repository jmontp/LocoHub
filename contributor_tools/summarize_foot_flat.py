#!/usr/bin/env python3
"""CORE-FOOT-01 summary: before/after counts of one rebuilt package against the package it was rebuilt from.

Reads only the small package files (dataset_index.json, assessment.jsonl streamed, exclusions.csv, evidence CSVs); writes
docs/quality/audits/core-foot-01-summary-<DATASET>.json. Read-only probe (one pass over assessment.jsonl, a few facts per line).

  OMP_NUM_THREADS=1 prlimit --as=$((600*1024*1024)) -- nice -n 19 ionice -c 3 python3 contributor_tools/summarize_foot_flat.py \
      --dataset GT23 --old gt23_r01_review_v11 --new gt23_r01_review_v12
"""
import argparse
import collections
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "converted_datasets/reconversion_v2"


def facts(pkg):
    out = {"failed": collections.Counter(), "by_table_failed": collections.Counter(), "L1_obs": collections.Counter(),
           "L5_obs": collections.Counter(), "obs": collections.Counter(), "ankle_cop_fail_obs": collections.Counter()}
    with open(BASE / pkg / "assessment.jsonl") as f:
        for line in f:
            e = json.loads(line)
            t = e["table"]
            out["obs"][t] += 1
            if e["status"] == "failed":
                out["by_table_failed"][t] += 1
                for c in e["failed_limits"]:
                    out["failed"][f"{t}:{c}"] += 1
            lims = {l for d in e["failed_samples"].values() for l in d}
            if "L1" in lims:
                out["L1_obs"][t] += 1
            if "L5" in lims:
                out["L5_obs"][t] += 1
    return {k: dict(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    a = ap.parse_args()
    off = json.loads((ROOT / "docs/quality/audits/foot-flat-offsets.json").read_text())["datasets"][a.dataset]
    degs = [v["offset_deg"] for v in off["people"].values()]
    di_old = json.loads((BASE / a.old / "dataset_index.json").read_text())["counts"]
    di_new = json.loads((BASE / a.new / "dataset_index.json").read_text())["counts"]
    with open(BASE / a.new / "evidence/foot_flat_membership_changes.csv", newline="") as f:
        flips = list(csv.DictReader(f))
    ts_new = json.loads((BASE / a.new / "test_summary.json").read_text())
    out = {"dataset": a.dataset, "old_package": a.old, "new_package": a.new,
           "offsets_deg": {"people_with_offset": len(degs), "median": statistics.median(degs), "min": min(degs), "max": max(degs),
                           "people_without_offset": off["persons_without_offset"]},
           "counts_before": {k: di_old[k] for k in ("observations_full", "observations_filtered", "failed_observations")} |
                            {"full": di_old["full"], "filtered": di_old["filtered"]},
           "counts_after": {k: di_new[k] for k in ("observations_full", "observations_filtered", "failed_observations")} |
                           {"full": di_new["full"], "filtered": di_new["filtered"]},
           "assessment_before": facts(a.old), "assessment_after": facts(a.new),
           "membership_changes": {"newly_failed": sum(1 for r in flips if r["status_after"] == "failed"),
                                  "recovered": sum(1 for r in flips if r["status_after"] != "failed"),
                                  "by_table_and_direction": dict(collections.Counter(f"{r['table']}:{r['status_before']}->{r['status_after']}" for r in flips)),
                                  "by_cause_after": dict(collections.Counter(r["causes_after"] or "none" for r in flips)),
                                  "by_cause_before": dict(collections.Counter(r["causes_before"] or "none" for r in flips))},
           "builder_checks": {"all_pass": ts_new["all_pass"], "failed": [c["id"] for c in ts_new["checks"] if not c["pass"]]}}
    path = ROOT / f"docs/quality/audits/core-foot-01-summary-{a.dataset}.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: out[k] for k in ("counts_before", "counts_after", "membership_changes")}, indent=1)[:3000])


if __name__ == "__main__":
    sys.exit(main())
