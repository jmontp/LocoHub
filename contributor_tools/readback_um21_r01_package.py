#!/usr/bin/env python3
"""UM21-R01 v3 readback: re-check the written package from its files, separately from the builder and the adapter.

The checks below do not import the adapter, the shared builder or the Q01 runner; the limits are written out again here. The
readback reads the package tables in batches of 3,000 rows, the source tables of three seeded recordings one at a time, and
writes one small JSON. It does not repair anything. Run only through contributor_tools.guarded_launcher.

  R1  manifest.sha256, every file's sha256 and bytes, no file outside the manifest
  R2  the same binding in manifest, dataset_index, phase_preview, test_summary and limitations; binding hashes equal the files
  R3  every input in inputs_sha256 still hashes to its recorded value
  R4  tables: 150 rows per observation on the inclusive grid, contiguous, unique; identical columns; no time table
  R5  full = filtered + failed (assessment.jsonl), per-observation value sums identical on the kept observations
  R6  exclusions.csv: stages and counts; observations + upstream exclusions = 7,562; every failed observation listed once
  R7  held columns hold no finite value; held CoP legs (S02 v7 verdicts) are all missing; passing legs publish values
  R8  L1 (hip, knee, ankle) and L5 (CoP) recomputed from the table agree with the assessment's failures
  R9  seeded recordings: every column equals its source (S02 v7 component or v2 row) except plane-glitch holds
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import random
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACKAGE = "converted_datasets/reconversion_v2/um21_r01_package_v3"
S02_ROOT = "converted_datasets/reconversion_v2/um21_s02_frame_full_v7"
S02_RECEIPT = "docs/quality/audits/um21-s02-full-launcher-receipt-v7.json"
V2_FULL = "converted_datasets/reconversion_v2/um21_r01_review_v2/full.parquet"
SEED = 20261206
N = 150
ADDRESS_SPACE_MIB = 768
ROOT_OUT = "converted_datasets/reconversion_v2/um21_r01_readback_v3"
BOUNDS_DEG = {"hip_flexion_angle_ipsi_rad": (-50, 150), "knee_flexion_angle_ipsi_rad": (-30, 165),
              "ankle_dorsiflexion_angle_ipsi_rad": (-80, 50)}
COP_BOUNDS = {"cop_anterior_ipsi_m": 0.5, "cop_vertical_ipsi_m": 0.3, "cop_lateral_ipsi_m": 0.3}
COP = tuple(COP_BOUNDS)
S02_NAMES = {"pelvis_tilt": "pelvis_sagittal_angle_rad", "hip_angle": "hip_flexion_angle_ipsi_rad",
             "knee_angle": "knee_flexion_angle_ipsi_rad", "ankle_angle": "ankle_dorsiflexion_angle_ipsi_rad",
             "thigh_angle": "thigh_sagittal_angle_ipsi_rad", "shank_angle": "shank_sagittal_angle_ipsi_rad",
             "foot_angle": "foot_sagittal_angle_ipsi_rad", "pelvis_tilt_velocity": "pelvis_sagittal_velocity_rad_s",
             "thigh_angle_velocity": "thigh_sagittal_velocity_ipsi_rad_s", "shank_angle_velocity": "shank_sagittal_velocity_ipsi_rad_s",
             "foot_angle_velocity": "foot_sagittal_velocity_ipsi_rad_s", "cop_anterior": "cop_anterior_ipsi_m",
             "cop_vertical": "cop_vertical_ipsi_m", "cop_lateral": "cop_lateral_ipsi_m"}
V2_COLS = ("hip_flexion_moment_ipsi_Nm_kg", "knee_flexion_moment_ipsi_Nm_kg", "ankle_dorsiflexion_moment_ipsi_Nm_kg",
           "hip_flexion_power_ipsi_W_kg", "knee_flexion_power_ipsi_W_kg", "ankle_dorsiflexion_power_ipsi_W_kg")
V2_IDENTITY = ("subject", "source_recording_id", "reference_side", "observation_type", "task", "task_id", "task_info")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def stream_table(path, want_values=()):
    """Per observation key: rows, grid ok, held json, finite counts and value sums per numeric column (and, for the wanted
    observations, the values). Batches of 3,000 rows."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    info, order, values, bad = {}, [], {}, collections.Counter()
    last, closed = None, set()
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        names = pf.schema_arrow.names
        numeric = [f.name for f in pf.schema_arrow if pa.types.is_floating(f.type) and f.name not in
                   ("phase_ipsi", "source_start_time_s", "source_end_time_s")]
        for b in pf.iter_batches(batch_size=3000, use_threads=False):
            oid, side = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            ph = b.column("phase_ipsi").to_numpy(zero_copy_only=False)
            held = b.column("held_signals").to_pylist()
            q = b.column("quality_status").to_pylist()
            num = {c: b.column(c).to_numpy(zero_copy_only=False) for c in numeric}
            i = 0
            while i < len(oid):
                j = i
                while j < len(oid) and oid[j] == oid[i] and side[j] == side[i]:
                    j += 1
                key = (oid[i], side[i])
                if key != last:
                    if key in closed:
                        bad["non_contiguous"] += 1
                    if last is not None:
                        closed.add(last)
                    last = key
                r = info.get(key)
                if r is None:
                    r = info[key] = {"rows": 0, "grid_ok": True, "held": held[i], "quality": q[i],
                                     "finite": collections.Counter(), "sum": collections.Counter()}
                    order.append(key)
                k0 = r["rows"]
                if not np.allclose(ph[i:j], np.linspace(0, 100, N)[k0:k0 + (j - i)], atol=1e-9):
                    r["grid_ok"] = False
                r["rows"] += j - i
                for c in numeric:
                    x = num[c][i:j]
                    fin = np.isfinite(x)
                    r["finite"][c] += int(fin.sum())
                    r["sum"][c] += float(x[fin].sum())
                if key in want_values:
                    v = values.setdefault(key, {c: [] for c in numeric})
                    for c in numeric:
                        v[c].extend(num[c][i:j].tolist())
                i = j
    return {"names": names, "numeric": numeric, "info": info, "order": order, "bad": dict(bad), "values": values}


def run(args):
    global PACKAGE
    PACKAGE = args.package_root
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    import pyarrow.parquet as pq
    started = time.time()
    pkg = ROOT / PACKAGE
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks = []

    def check(cid, text, expected, observed):
        ok = expected == observed
        big = len(json.dumps([expected, observed], default=str)) > 3000
        checks.append({"id": cid, "check": text, "expected": {"size": len(expected)} if (ok and big) else expected,
                       "observed": {"size": len(observed)} if (ok and big) else observed, "pass": ok})

    # R1 manifest and files
    manifest = json.loads((pkg / "manifest.json").read_text())
    check("R1a", "manifest.sha256 equals the sha256 of manifest.json", sha256_file(pkg / "manifest.json"),
          (pkg / "manifest.sha256").read_text().split()[0])
    on_disk = {p.relative_to(pkg).as_posix() for p in pkg.rglob("*") if p.is_file()} - {"manifest.json", "manifest.sha256"}
    check("R1b", "the files on disk are exactly the files in the manifest", sorted(manifest["files"]), sorted(on_disk))
    check("R1c", "sha256 and bytes of every file equal the manifest", [],
          [f for f, v in manifest["files"].items() if sha256_file(pkg / f) != v["sha256"] or (pkg / f).stat().st_size != v["bytes"]])
    # R2 binding
    binding = manifest["binding"]
    others = {n: json.loads((pkg / n).read_text()).get("binding") for n in
              ("dataset_index.json", "phase_preview.json", "test_summary.json", "limitations.json")}
    check("R2a", "the same binding in dataset_index, phase_preview, test_summary and limitations", [],
          sorted(n for n, b in others.items() if b != binding))
    wrong = [k for k in ("full_phase", "filtered_phase") if binding.get(f"{k}.parquet") != sha256_file(pkg / f"{k}.parquet")]
    wrong += [k for k, f in (("exclusions_sha256", "exclusions.csv"), ("assessment_sha256", "assessment.jsonl"))
              if binding.get(k) != sha256_file(pkg / f)]
    check("R2b", "binding hashes equal the files", [], wrong)
    check("R2c", "tables listed in the manifest are the phase table only; no time file", ["phase"],
          manifest["tables"] if not list(pkg.glob("*_time.parquet")) else ["time file present"])
    # R3 inputs
    check("R3", "every input in inputs_sha256 still hashes to its recorded value", [],
          [k for k, v in manifest["inputs_sha256"].items() if sha256_file(ROOT / k) != v])
    # assessment, exclusions
    assess = {}
    with open(pkg / "assessment.jsonl") as f:
        for line in f:
            e = json.loads(line)
            k = (e["observation_id"], e["reference_side"])
            if k in assess:
                checks.append({"id": "R5x", "check": "duplicate assessment entry", "expected": None, "observed": k, "pass": False})
            assess[k] = e
    failed = {k for k, e in assess.items() if e["status"] == "failed"}
    with open(pkg / "exclusions.csv", newline="") as f:
        excl = list(csv.DictReader(f))
    # R4/R5 tables
    full = stream_table(pkg / "full_phase.parquet")
    filt = stream_table(pkg / "filtered_phase.parquet")
    check("R4a", "no row-grid, contiguity or duplicate problems in either table", {"full": {}, "filtered": {}}, {"full": full["bad"], "filtered": filt["bad"]})
    check("R4b", "every observation has exactly 150 rows on the inclusive grid, both tables", [],
          [k for t in (full, filt) for k, r in t["info"].items() if r["rows"] != N or not r["grid_ok"]])
    check("R4c", "full and filtered have identical column lists", full["names"], filt["names"])
    fk, tk = set(full["info"]), set(filt["info"])
    check("R5a", "observations in full equal the assessed observations", sorted(assess), sorted(fk))
    check("R5b", "full = filtered + failed with no gap or overlap", sorted(failed), sorted(fk - tk))
    check("R5c", "filtered is a subset of full", 0, len(tk - fk))
    diffs = [k for k in tk & fk if any(abs(full["info"][k]["sum"][c] - filt["info"][k]["sum"][c]) > 0 or
                                       full["info"][k]["finite"][c] != filt["info"][k]["finite"][c] for c in full["numeric"])]
    check("R5d", "kept observations have identical finite counts and value sums in full and filtered", [], diffs)
    check("R5e", "quality_status is failed exactly for the failed observations in full, and never in filtered", [],
          [k for k, r in full["info"].items() if (r["quality"] == "failed") != (k in failed)] +
          [k for k, r in filt["info"].items() if r["quality"] != "no_failure_found"])
    # R6 exclusions
    by_stage = collections.Counter(r["stage"] for r in excl)
    listed = collections.Counter(r["observation_id"] for r in excl if r["stage"] == "filtered_variant_only")
    check("R6a", "every failed observation is listed once as filtered_variant_only, and nothing else is", sorted(k[0] for k in failed),
          sorted(listed.elements()))
    upstream = by_stage["upstream_not_released"] + by_stage["release_membership"]
    check("R6b", "full-run totals: 7,545 observations + 17 upstream exclusions = 7,562 (pilot packages skip this)",
          (7562 if len(fk) == 7545 else None), (len(fk) + upstream if len(fk) == 7545 else None))
    check("R6c", "no exclusion row names an observation that is in the full table unless it is a filtered_variant_only row", [],
          [r["observation_id"] for r in excl if r["stage"] != "filtered_variant_only" and (r["observation_id"], r["reference_side"]) in fk])
    # R7 held columns and CoP legs
    held_bad = []
    for k, r in full["info"].items():
        for col in json.loads(r["held"] or "{}"):
            if r["finite"].get(col, 0):
                held_bad.append((k, col))
    check("R7a", "held columns hold no finite value in the full table", [], held_bad[:10])
    summary = json.loads((ROOT / S02_ROOT / "s02_summary.json").read_text())
    verdict = {(r["recording"], leg): v["cop_gate"]["verdict"] for r in summary["records"] for leg, v in r["legs"].items()}
    cop_fin = collections.defaultdict(int)
    leg_obs = collections.defaultdict(int)
    for (oid, side), r in full["info"].items():
        parts = oid.split(":")[1].split("/")
        rec = f"{parts[1]}/{parts[3]}"
        leg_obs[(rec, side)] += 1
        cop_fin[(rec, side)] += sum(r["finite"].get(c, 0) for c in COP)
    present = {k: v for k, v in verdict.items() if k in leg_obs}
    check("R7b", "legs held by the S02 v7 gate have every centre-of-pressure value missing", [],
          sorted(f"{k[0]}:{k[1]}" for k, v in present.items() if v == "held" and cop_fin[k]))
    check("R7c", "legs passed by the S02 v7 gate publish at least some centre-of-pressure values", [],
          sorted(f"{k[0]}:{k[1]}" for k, v in present.items() if v == "pass" and not cop_fin[k]))
    # R8 recompute L1 and L5 from the table, independent of the assessment code
    # (a second streaming pass over the full table, per observation)
    recomputed = collections.defaultdict(set)
    with open(pkg / "full_phase.parquet", "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for b in pf.iter_batches(batch_size=3000, columns=["observation_id", "reference_side", *BOUNDS_DEG, *COP], use_threads=False):
            oid, side = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            for c, (lo, hi) in BOUNDS_DEG.items():
                x = np.degrees(b.column(c).to_numpy(zero_copy_only=False))
                with np.errstate(invalid="ignore"):
                    bad = np.flatnonzero(np.isfinite(x) & ((x < lo) | (x > hi)))
                for i in bad:
                    recomputed[(oid[i], side[i])].add("L1")
            for c, lim in COP_BOUNDS.items():
                x = b.column(c).to_numpy(zero_copy_only=False)
                with np.errstate(invalid="ignore"):
                    bad = np.flatnonzero(np.isfinite(x) & (np.abs(x) > lim))
                for i in bad:
                    recomputed[(oid[i], side[i])].add("L5")
    in_assessment = {f"{k[0]}|{k[1]}": sorted(set(assess[k]["failed_limits"]) & {"L1", "L5"}) for k in assess
                     if set(assess[k]["failed_limits"]) & {"L1", "L5"}}
    check("R8", "L1 and L5 failures recomputed from the table equal the assessment's L1 and L5 failures, per observation", in_assessment,
          {f"{k[0]}|{k[1]}": sorted(v) for k, v in recomputed.items()})
    check("R8b", "L2 is not rechecked here (it needs the marker frame series); the assessment lists L2 failures as", "not rechecked",
          "not rechecked")
    # R9 seeded recordings against their sources
    recs = sorted({f"{o.split(':')[1].split('/')[1]}/{o.split(':')[1].split('/')[3]}" for o, _ in fk})
    sample = random.Random(SEED).sample(recs, min(3, len(recs)))
    want = {k for k in fk if f"{k[0].split(':')[1].split('/')[1]}/{k[0].split(':')[1].split('/')[3]}" in sample}
    sub = stream_table(pkg / "full_phase.parquet", want_values=want)
    glitch_held = {k for k, r in full["info"].items() if "rule P1" in (r["held"] or "")}
    receipt = {o["path"]: o["sha256"] for o in json.loads((ROOT / S02_RECEIPT).read_text())["outputs"]}
    mism, compared = [], 0
    for rec in sample:
        subj, cond = rec.split("/")
        rel = f"components/{subj}/{cond}/s02.parquet"
        if sha256_file(ROOT / S02_ROOT / rel) != receipt[rel]:
            mism.append(f"{rel}: hash")
            continue
        t = pq.read_table(ROOT / S02_ROOT / rel, use_threads=False)
        ids = t.column("observation_id").to_pylist()
        idx = {}
        for i, o in enumerate(ids):
            idx.setdefault(o, []).append(i)
        for k in [k for k in want if f"{k[0].split(':')[1].split('/')[1]}/{k[0].split(':')[1].split('/')[3]}" == rec]:
            if k in glitch_held:
                continue
            rows = idx[k[0]]
            for s02c, name in S02_NAMES.items():
                src = np.array(t.column(s02c).to_numpy(zero_copy_only=False))[rows]
                got = np.array(sub["values"][k][name])
                same = np.array_equal(np.isnan(src), np.isnan(got)) and np.allclose(src[~np.isnan(src)], got[~np.isnan(got)], rtol=0, atol=0)
                compared += 1
                if not same:
                    mism.append(f"{k[0]} {name}")
        # v2 columns (moments, powers) and identity columns, value for value
        marker = f"um21:Streaming/{subj}/Tread/{cond}:"
        v2 = {}
        with open(ROOT / V2_FULL, "rb") as fh:
            pf = pq.ParquetFile(fh, buffer_size=0)
            for g in range(pf.metadata.num_row_groups):
                ids = pf.read_row_group(g, columns=["observation_id"], use_threads=False).column(0).to_pylist()
                if not ids[0].startswith(marker) and not ids[-1].startswith(marker):
                    continue
                tab = pf.read_row_group(g, columns=["observation_id", "reference_side", *V2_COLS], use_threads=False)
                o2, s2 = tab.column("observation_id").to_pylist(), tab.column("reference_side").to_pylist()
                arr = {c: tab.column(c).to_numpy(zero_copy_only=False) for c in V2_COLS}
                for i, o in enumerate(o2):
                    if o.startswith(marker):
                        d = v2.setdefault((o, s2[i]), {c: [] for c in V2_COLS})
                        for c in V2_COLS:
                            d[c].append(arr[c][i])
        for k, d in v2.items():
            if k not in want or k in glitch_held:
                continue
            for c in V2_COLS:
                src, got = np.array(d[c]), np.array(sub["values"][k][c])
                compared += 1
                if not (np.array_equal(np.isnan(src), np.isnan(got)) and np.array_equal(src[~np.isnan(src)], got[~np.isnan(got)])):
                    mism.append(f"{k[0]} {c}")
        if {k for k in want if k[0].startswith(marker)} != set(v2) & want:
            mism.append(f"{rec}: v2 and package observations differ")
    check("R9", "sampled recordings: every published column equals its source value-for-value", [], mism[:20])
    report = {"task_id": "UM21-R01-readback", "version": "v3", "scientific_approval": False, "package": PACKAGE,
              "seed": SEED, "sampled_recordings": sample, "columns_compared": compared, "checks": checks,
              "all_pass": all(c["pass"] for c in checks),
              "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "wall_seconds": round(time.time() - started, 1)}}
    with open(out / "readback.json", "x") as f:
        json.dump(report, f, indent=1, default=str)
    print(json.dumps({"all_pass": report["all_pass"], "failed": [c["id"] for c in checks if not c["pass"]],
                      "peak_rss_mib": report["resources"]["peak_rss_mib"]}))
    return 0 if report["all_pass"] else 1


def plan(package_root, tag):
    from contributor_tools.guarded_launcher import validate_spec
    manifest = json.loads((ROOT / package_root / "manifest.json").read_text())
    bind = {"contributor_tools/readback_um21_r01_package.py": sha256_file(Path(__file__)),
            S02_RECEIPT: sha256_file(ROOT / S02_RECEIPT), f"{S02_ROOT}/s02_summary.json": sha256_file(ROOT / S02_ROOT / "s02_summary.json"),
            f"{package_root}/manifest.json": sha256_file(ROOT / package_root / "manifest.json")}
    out_root = ROOT_OUT if tag == "v3" else f"{ROOT_OUT}_{tag}"
    spec = {"job_id": f"UM21-R01-readback-{tag}",
            "command": ["python3", "contributor_tools/readback_um21_r01_package.py", "run", "--output-root", out_root,
                        "--package-root", package_root],
            "cwd": str(ROOT), "output_root": out_root, "receipt_path": f"docs/quality/audits/um21-r01-readback-launcher-receipt-{tag}.json",
            "bindings": bind, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["readback.json"], "address_space_mib": ADDRESS_SPACE_MIB}
    validate_spec(spec)
    path = ROOT / f"docs/quality/audits/um21-r01-readback-spec-{tag}.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path), "package_files": len(manifest["files"])}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    sub.add_parser("plan")
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--package-root", default=PACKAGE)
    pp = sub.choices["plan"]
    pp.add_argument("--package-root", default=PACKAGE)
    pp.add_argument("--tag", default="v3")
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.package_root, args.tag)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
