"""CORE-FOOT-01 step 1: per-person foot-flat offsets for GT23, GT21 and UM21 -> docs/quality/audits/foot-flat-offsets.json.

Offset = median over the person's matched level-walking strides of the per-stride median ipsilateral foot angle over 20-35
percent of the stride, read from the filtered phase table of the current package (GT23 v11, GT21 v1, UM21 v5). The level
match is build_review_sheet_cross_dataset.TASKS['level'] (imported, not copied). A person without a matched level stride has
no offset and stays uncorrected. Read-only probe: one table at a time, 4096-row batches, three or four columns of interest,
nothing under converted_datasets/ is written.

  python3 contributor_tools/compute_foot_flat_offsets.py --selftest      # synthetic, reads no data
  OMP_NUM_THREADS=1 ARROW_DEFAULT_MEMORY_POOL=system MPLBACKEND=Agg prlimit --as=$((600*1024*1024)) -- \
    nice -n 19 ionice -c 3 python3 contributor_tools/compute_foot_flat_offsets.py --run
"""
import os
for _k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_k] = "1"
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import importlib.util
import json
import resource
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("foot_flat", ROOT / "contributor_tools/common/foot_flat.py")
ff = importlib.util.module_from_spec(spec)
sys.modules["foot_flat"] = ff
spec.loader.exec_module(ff)

OUT = ROOT / "docs/quality/audits/foot-flat-offsets.json"
PKG = "converted_datasets/reconversion_v2"
BATCH = 4096


def collect(ds, A):
    import pyarrow.parquet as pq
    label, folder, _ = A.DATASETS[ds]
    path = ROOT / PKG / folder / "filtered_phase.parquet"
    pf = pq.ParquetFile(path)
    cols = ["subject", "observation_id", "observation_type", "task", "task_info", "phase_ipsi", "foot_sagittal_angle_ipsi_rad"]
    match = A.TASKS["level"]["match"]
    group, subj_of, foot = {}, {}, {}
    subjects, cycles = {}, {}
    for batch in pf.iter_batches(BATCH, columns=cols, use_threads=False):
        ids = batch.column("observation_id").to_numpy(zero_copy_only=False)
        uniq, first, inv = np.unique(ids, return_index=True, return_inverse=True)
        ok = np.zeros(len(uniq), dtype=bool)
        for k, (u, f) in enumerate(zip(uniq, first)):
            if u not in group:
                s = batch.column("subject")[int(f)].as_py()
                m = False
                if batch.column("observation_type")[int(f)].as_py() == "individual_cycle":
                    cycles[s] = cycles.get(s, 0) + 1
                    info = json.loads(batch.column("task_info")[int(f)].as_py() or "{}")
                    m = bool(match(ds, batch.column("task")[int(f)].as_py(), info))
                subjects.setdefault(s, 0)
                group[u] = m
                if m:
                    subj_of[u] = s
                    foot[u] = np.full(ff.N, np.nan)
                    subjects[s] += 1
            ok[k] = group[u]
        if not ok.any():
            continue
        row_ok = ok[inv]
        ph = np.rint(np.array(batch.column("phase_ipsi").to_numpy(zero_copy_only=False), dtype=float) / 100 * (ff.N - 1)).astype(np.int64)
        fv = np.array(batch.column("foot_sagittal_angle_ipsi_rad").to_numpy(zero_copy_only=False), dtype=float)
        for k in np.flatnonzero(ok):
            sel = (inv == k)
            good = np.isfinite(fv[sel])
            foot[uniq[k]][ph[sel][good]] = fv[sel][good]
    strides = [(subj_of[u], u, foot[u]) for u in foot]
    people = ff.person_offsets(strides)
    allsubj = sorted(subjects)
    return {"package": f"{PKG}/{folder}", "table": "filtered_phase.parquet",
            "input_sha256_from_package_manifest": json.loads((ROOT / PKG / folder / "manifest.json").read_text())["files"]["filtered_phase.parquet"]["sha256"],
            "level_match": "build_review_sheet_cross_dataset.TASKS['level'] (individual cycles, level walking at 1.2 m/s +-0.05; UM21 at 0 deg)",
            "people": people, "persons_in_filtered_phase_table": allsubj,
            "matched_level_strides_by_person_before_nan_check": {s: subjects[s] for s in allsubj},
            "persons_without_offset": [s for s in allsubj if s not in people],
            "individual_cycles_by_person": {s: cycles.get(s, 0) for s in allsubj}}


def selftest():
    rng = np.random.default_rng(3)
    foot = rng.normal(0, 0.5, ff.N)
    foot[ff.MID] = np.radians(4.0)
    assert abs(ff.stride_median_rad(foot) - np.radians(4.0)) < 1e-12
    p = ff.person_offsets([("a", "o1", foot), ("a", "o2", foot + np.radians(2)), ("a", "o3", foot - np.radians(2)),
                           ("b", "o4", foot + np.radians(10)), ("c", "o5", np.full(ff.N, np.nan))])
    assert abs(p["a"]["offset_deg"] - 4.0) < 1e-9 and p["a"]["n_strides"] == 3 and abs(p["b"]["offset_deg"] - 14.0) < 1e-9
    assert "c" not in p
    print("selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--run" not in sys.argv:
        raise SystemExit(__doc__)
    from contributor_tools import build_review_sheet_cross_dataset as A
    out = {"task_id": "CORE-FOOT-01", "decision": "D-REF-6 = A",
           "definition": "offset (rad) = median over matched level-walking strides of the per-stride median ipsilateral foot angle "
                         "over 20-35 percent of the stride, filtered phase table; foot and ankle := value - offset",
           "datasets": {}}
    for ds in A.DATASETS:
        out["datasets"][ds] = collect(ds, A)
        d = out["datasets"][ds]
        print(ds, {s: round(v["offset_deg"], 2) for s, v in d["people"].items()}, "uncorrected:", d["persons_without_offset"],
              f"peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MiB", flush=True)
    with open(OUT, "x", encoding="utf-8") as f:
        f.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
