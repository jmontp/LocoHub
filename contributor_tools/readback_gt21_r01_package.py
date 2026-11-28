#!/usr/bin/env python3
"""GT21-R01 v1 readback: re-check the written package from its files, separately from the builder and the adapter.

It does not import the adapter, the shared builder or the Q01 runner; the limits are written out again here and the export
(source) facts are read from the export roots themselves (run_summary.json, observations.jsonl, exclusions.jsonl, tables).
Package tables are read in batches of 3,000 rows. It writes one small JSON and repairs nothing. Run only through
contributor_tools.guarded_launcher.

  R1  manifest.sha256, every file's sha256 and bytes, no file outside the manifest
  R2  the same binding in manifest, dataset_index, phase_preview, test_summary and limitations; binding hashes equal the files
  R3  every input in inputs_sha256 still hashes to its value; export files equal the hashes in each export's own run_summary
  R4  tables: phase = 150 rows per observation on the inclusive grid, time = strictly increasing time; contiguous, unique
  R5  full = filtered + failed (assessment.jsonl); observation set of full = observation set of the export's observations.jsonl;
      per-observation value sums identical on kept observations; row counts equal the export run summaries
  R6  exclusions.csv: upstream rows equal the export exclusions.jsonl (ids and reason counts); every failed observation once
  R7  held columns hold no finite value in the full tables
  R8  L1 (hip, knee, ankle angles) and L5 (pressure point) recomputed from the full tables equal the assessment's L1/L5 failures
  R9  seeded sample (subjects, phase observations, time recordings): every column equals the export value for value
  R10 power = moment x joint speed on every row of the sampled observations; manifest/limitations say what they must
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

try:  # few arenas, large blocks via mmap, prompt trimming (address-space cap)
    import ctypes
    _LIBC = ctypes.CDLL("libc.so.6")
    _LIBC.mallopt(-8, 2)            # M_ARENA_MAX
    _LIBC.mallopt(-3, 256 * 1024)   # M_MMAP_THRESHOLD
    _LIBC.mallopt(-1, 256 * 1024)   # M_TRIM_THRESHOLD
except OSError:  # pragma: no cover
    _LIBC = None


def trim():
    if _LIBC is not None:
        _LIBC.malloc_trim(0)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACKAGE = "converted_datasets/reconversion_v2/gt21_r01_package_v1"
EXPORT = "converted_datasets/reconversion_v2/gt21_rb07_export_{}"
SEED = 20261207
N = 150
ADDRESS_SPACE_MIB = 768
ROOT_OUT = "converted_datasets/reconversion_v2/gt21_r01_readback_v1"
EXTRA = ("source_export", "quality_status", "failed_limits", "limitations", "lineage_id", "assessment_id")
JOINTS = ("hip_flexion", "knee_flexion", "ankle_dorsiflexion")
BOUNDS_DEG = {"hip_flexion": (-50, 150), "knee_flexion": (-30, 165), "ankle_dorsiflexion": (-80, 50)}
COP_LIM = {"anterior": 0.5, "vertical": 0.3, "lateral": 0.3}
SIDES = {"phase": ("ipsi", "contra"), "time": ("left", "right")}
IDX = {"phase": "phase_ipsi", "time": "time_s"}
REQUIRED_LIMITATIONS = ("held_frames_in_angles", "plate_dropout_samples", "early_source_heel_strike_short_left_stance",
                        "left_stance_unavailable_no_toe_off", "left_treadmill_stance_from_belt_force", "p1_unchecked",
                        "ankle_zero_offset_unreviewed", "source_is_authors_2024_copy")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


class Info:
    """Per-observation state, slotted (85,000 observations x 2 tables x 2 variants must fit the memory cap)."""
    __slots__ = ("rows", "quality", "fcount", "fsum", "L", "held_cols")
    NONE = frozenset()

    def __init__(self, quality, held_cols):
        self.rows, self.quality, self.fcount, self.fsum, self.L, self.held_cols = 0, sys.intern(quality), 0, 0.0, Info.NONE, held_cols

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def add_limit(self, x):
        self.L = self.L | {x}


def subject_of(oid):
    return oid.split("/")[0]


def angle_cols(table):
    return {(j, sd): f"{j}_angle_{sd}_rad" for j in JOINTS for sd in SIDES[table]}


def cop_cols(table):
    return {(a, sd): f"cop_{a}_{sd}_m" for a in COP_LIM for sd in SIDES[table]}


def stream_table(path, table, want=frozenset(), canon=None):
    """One pass: per observation key rows, order checks, held json, quality, finite counts, sums, L1/L5 findings; values of
    the wanted observations (all non-extra columns)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    info, bad, values = {}, collections.Counter(), {}
    held_cache, held_viol = {}, []
    last, closed, prev_idx = None, set(), {}
    ac, cc = angle_cols(table), cop_cols(table)
    with open(path, "rb") as fh:
        plain = pq.ParquetFile(fh, buffer_size=0).schema_arrow
        pf = pq.ParquetFile(fh, buffer_size=0, read_dictionary=[f.name for f in plain if pa.types.is_string(f.type)])
        names = pf.schema_arrow.names
        numeric = [f.name for f in pf.schema_arrow if pa.types.is_floating(f.type)
                   and f.name not in ("phase_ipsi", "time_s", "source_start_time_s", "source_end_time_s")]
        for b in pf.iter_batches(batch_size=2000, use_threads=False):
            trim()
            oid, side = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            idx = b.column(IDX[table]).to_numpy(zero_copy_only=False)
            held, qual = b.column("held_signals").to_pylist(), b.column("quality_status").to_pylist()
            num = {c: b.column(c).to_numpy(zero_copy_only=False) for c in numeric}
            wanted_cols = None
            i = 0
            while i < len(oid):
                j = i
                while j < len(oid) and oid[j] == oid[i] and side[j] == side[i]:
                    j += 1
                key = (oid[i], side[i])
                if canon is not None:
                    key = canon.setdefault(key, key)  # one key object per observation across tables and variants
                if key != last:
                    if key in closed:
                        bad["non_contiguous"] += 1
                    if last is not None:
                        closed.add(last)
                    last = key
                r = info.get(key)
                if r is None:
                    r = info[key] = Info(qual[i], None)
                    hj = held_cache.get(held[i])
                    if hj is None:
                        hv = json.loads(held[i] or "{}")
                        hj = held_cache[held[i]] = list(hv if isinstance(hv, list) else hv)
                    r.held_cols = hj
                seg = idx[i:j]
                if table == "phase":
                    want_idx = np.arange(r["rows"], r["rows"] + (j - i)) * 100.0 / (N - 1)
                    if not np.allclose(seg, want_idx, atol=1e-9, rtol=0):
                        bad["phase_grid"] += 1
                else:
                    if not (np.all(np.isfinite(seg)) and np.all(np.diff(seg) > 0) and (key not in prev_idx or seg[0] > prev_idx[key])):
                        bad["time_order"] += 1
                    prev_idx[key] = float(seg[-1])
                r["rows"] += j - i
                for c in numeric:
                    x = num[c][i:j]
                    fin = np.isfinite(x)
                    n_fin = int(fin.sum())
                    r["fcount"] += n_fin
                    r["fsum"] += float(x[fin].sum())
                    if n_fin and c in r["held_cols"]:
                        held_viol.append((key, c))
                for (jn, sd), c in ac.items():
                    lo, hi = BOUNDS_DEG[jn]
                    x = np.degrees(num[c][i:j])
                    with np.errstate(invalid="ignore"):
                        if np.any(np.isfinite(x) & ((x < lo) | (x > hi))):
                            r.add_limit("L1")
                for (a, sd), c in cc.items():
                    x = num[c][i:j]
                    with np.errstate(invalid="ignore"):
                        if np.any(np.isfinite(x) & (np.abs(x) > COP_LIM[a])):
                            r.add_limit("L5")
                if key in want:
                    v = values.setdefault(key, {c: [] for c in names if c not in EXTRA})
                    add_values(v, b, i, j - i)
                i = j
    values = {k: finish(v) for k, v in values.items()}
    return {"names": names, "numeric": numeric, "info": info, "bad": dict(bad), "values": values, "held_viol": held_viol}


def collect_export(path, table, want):
    """Values of the wanted observations from an export table file (all columns), streamed."""
    import pyarrow.parquet as pq
    values = {}
    import pyarrow as pa
    with open(path, "rb") as fh:
        plain = pq.ParquetFile(fh, buffer_size=0).schema_arrow
        pf = pq.ParquetFile(fh, buffer_size=0, read_dictionary=[f.name for f in plain if pa.types.is_string(f.type)])
        names = pf.schema_arrow.names
        for b in pf.iter_batches(batch_size=2000, use_threads=False):
            trim()
            oid, side = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            i = 0
            while i < len(oid):
                j = i
                while j < len(oid) and oid[j] == oid[i] and side[j] == side[i]:
                    j += 1
                key = (oid[i], side[i])
                if key in want:
                    v = values.setdefault(key, {c: [] for c in names})
                    add_values(v, b, i, j - i)
                i = j
    return {k: finish(v) for k, v in values.items()}


def add_values(store, b, i, n, skip=()):
    """Append rows i..i+n of batch b to store: float columns as numpy chunks, other columns run-length encoded."""
    import pyarrow as pa
    for c in list(store):
        col = b.column(c).slice(i, n)
        if pa.types.is_floating(col.type):
            store[c].append(col.to_numpy(zero_copy_only=False))
        else:
            runs = store[c]
            for v in col.to_pylist():
                if runs and runs[-1][0] == v:
                    runs[-1][1] += 1
                else:
                    runs.append([v, 1])


def finish(store):
    out = {}
    for c, v in store.items():
        out[c] = np.concatenate(v) if v and isinstance(v[0], np.ndarray) else v
    return out


def same_columns(a, b):
    """Two finished stores equal column by column (NaN equal; strings by run-length encoding)."""
    bad = []
    for c in a:
        x, y = a[c], b.get(c)
        if isinstance(x, np.ndarray):
            if y is None or x.shape != y.shape or not np.array_equal(x, y, equal_nan=True):
                bad.append(c)
        elif x != y:
            bad.append(c)
    return bad


def same_values(a, b):
    """Equal lists of python values with NaN == NaN."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(x, float) and isinstance(y, float):
            if not (x == y or (x != x and y != y)):
                return False
        elif x != y:
            return False
    return True


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    started = time.time()
    pkg = ROOT / args.package_root
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks = []

    def check(cid, text, expected, observed):
        ok = expected == observed
        big = len(json.dumps([expected, observed], default=str)) > 3000
        checks.append({"id": cid, "check": text, "expected": {"size": len(expected)} if (ok and big) else expected,
                       "observed": {"size": len(observed)} if (ok and big) else observed, "pass": ok})

    manifest = json.loads((pkg / "manifest.json").read_text())
    tables = manifest["tables"]
    check("R1a", "manifest.sha256 equals the sha256 of manifest.json", sha256_file(pkg / "manifest.json"),
          (pkg / "manifest.sha256").read_text().split()[0])
    on_disk = {p.relative_to(pkg).as_posix() for p in pkg.rglob("*") if p.is_file()} - {"manifest.json", "manifest.sha256"}
    check("R1b", "the files on disk are exactly the files in the manifest", sorted(manifest["files"]), sorted(on_disk))
    check("R1c", "sha256 and bytes of every file equal the manifest", [],
          [f for f, v in manifest["files"].items() if sha256_file(pkg / f) != v["sha256"] or (pkg / f).stat().st_size != v["bytes"]])
    binding = manifest["binding"]
    others = {n: json.loads((pkg / n).read_text()).get("binding") for n in
              ("dataset_index.json", "phase_preview.json", "test_summary.json", "limitations.json")}
    check("R2a", "the same binding in dataset_index, phase_preview, test_summary and limitations", [],
          sorted(n for n, b in others.items() if b != binding))
    wrong = [f"{v}_{t}" for v in ("full", "filtered") for t in tables if binding.get(f"{v}_{t}.parquet") != sha256_file(pkg / f"{v}_{t}.parquet")]
    wrong += [k for k, f in (("exclusions_sha256", "exclusions.csv"), ("assessment_sha256", "assessment.jsonl"))
              if binding.get(k) != sha256_file(pkg / f)]
    check("R2b", "binding hashes equal the files", [], wrong)
    check("R2c", "tables are phase and time", ["phase", "time"], tables)
    check("R2d", "scientific_approval false and local only, in manifest and test_summary and limitations-free flags",
          [False, True, True, False], [manifest["scientific_approval"], manifest["local_only"], manifest["no_upload_no_publish"],
                                       json.loads((pkg / "test_summary.json").read_text())["scientific_approval"]])
    # R3 inputs and the export's own run summaries
    check("R3a", "every input in inputs_sha256 still hashes to its recorded value", [],
          [k for k, v in manifest["inputs_sha256"].items() if sha256_file(ROOT / k) != v])
    subjects = sorted({k.split("gt21_rb07_export_")[1].split("/")[0] for k in manifest["inputs_sha256"] if "gt21_rb07_export_" in k})
    summ = {s: json.loads((ROOT / EXPORT.format(s) / "run_summary.json").read_text()) for s in subjects}
    mism = [f"{s}/{n}" for s in subjects for n, h in summ[s]["sha256"].items()
            if manifest["inputs_sha256"].get(f"{EXPORT.format(s)}/{n}") != h]
    check("R3b", "export files used equal the hashes in each export's own run_summary.json", [], mism)
    # assessment, exclusions
    assess = {}
    dup = []
    with open(pkg / "assessment.jsonl") as f:
        for line in f:
            e = json.loads(line)
            k = (e["observation_id"], e["reference_side"])
            if k in assess:
                dup.append(k)
            assess[k] = {"status": sys.intern(e["status"]), "failed_limits": [sys.intern(x) for x in e["failed_limits"]]}
    check("R5x", "assessment.jsonl lists every observation once", [], dup[:5])
    failed = {k for k, e in assess.items() if e["status"] == "failed"}
    with open(pkg / "exclusions.csv", newline="") as f:
        excl = list(csv.DictReader(f))
    # export facts
    src_keys = set()
    for s in subjects:
        with open(ROOT / EXPORT.format(s) / "observations.jsonl") as f:
            for line in f:
                o = json.loads(line)
                src_keys.add((o["observation_id"], o["reference_side"]))
        with open(ROOT / EXPORT.format(s) / "recordings.jsonl") as f:
            for line in f:
                r = json.loads(line)
                if r["status"] == "exported":
                    src_keys.add((r["source_recording_id"] + "/continuous", "none"))
    # tables
    full, filt, canon = {}, {}, {}
    for t in tables:
        full[t] = stream_table(pkg / f"full_{t}.parquet", t, canon=canon)
        filt[t] = stream_table(pkg / f"filtered_{t}.parquet", t, canon=canon)
    check("R4a", "no grid, order, contiguity or duplicate problems in any table file",
          {f"{v}_{t}": {} for v in ("full", "filtered") for t in tables},
          {f"{v}_{t}": d[t]["bad"] for v, d in (("full", full), ("filtered", filt)) for t in tables})
    check("R4b", "every phase observation has exactly 150 rows, both variants", [],
          [k for d in (full, filt) for k, r in d["phase"]["info"].items() if r["rows"] != N][:10])
    check("R4c", "full and filtered have identical column lists, per table", [full[t]["names"] for t in tables],
          [filt[t]["names"] for t in tables])
    check("R4d", "extra columns are the six documented ones, last", [list(EXTRA)] * 2, [full[t]["names"][-6:] for t in tables])
    fk = set().union(*[set(full[t]["info"]) for t in tables])
    tk = set().union(*[set(filt[t]["info"]) for t in tables])
    check("R5a", "observations in full equal the assessed observations", sorted(assess), sorted(fk))
    check("R5b", "full = filtered + failed with no gap or overlap", sorted(failed), sorted(fk - tk))
    check("R5c", "filtered is a subset of full", 0, len(tk - fk))
    diffs = [k for t in tables for k in set(filt[t]["info"]) if any(
        not np.isclose(full[t]["info"][k]["fsum"], filt[t]["info"][k]["fsum"], rtol=1e-9, atol=1e-6) or full[t]["info"][k]["fcount"] != filt[t]["info"][k]["fcount"]
        for _ in (0,))]
    check("R5d", "kept observations have identical finite counts and value sums (over all numeric columns, rtol 1e-9: batch boundaries change the summation order) in full and filtered", [], diffs[:10])
    check("R5e", "quality_status is failed exactly for the failed observations in full, never in filtered", [],
          [k for t in tables for k, r in full[t]["info"].items() if (r["quality"] == "failed") != (k in failed)][:10] +
          [k for t in tables for k, r in filt[t]["info"].items() if r["quality"] != "no_failure_found"][:10])
    check("R5f", "observations in full equal the export's own observations.jsonl and recordings.jsonl", sorted(src_keys), sorted(fk))
    check("R5g", "full phase rows = 150 x phase observations = sum of export run_summary phase_rows; time rows likewise",
          [sum(v["phase_rows"] for v in summ.values()), sum(v["time_rows"] for v in summ.values())],
          [sum(r["rows"] for r in full["phase"]["info"].values()), sum(r["rows"] for r in full["time"]["info"].values())])
    check("R5h", "filtered rows = full rows minus the rows of the failed observations, per table",
          {t: sum(r["rows"] for r in full[t]["info"].values()) - sum(full[t]["info"][k]["rows"] for k in failed if k in full[t]["info"]) for t in tables},
          {t: sum(r["rows"] for r in filt[t]["info"].values()) for t in tables})
    # R6 exclusions
    src_ex = []
    for s in subjects:
        with open(ROOT / EXPORT.format(s) / "exclusions.jsonl") as f:
            src_ex += [json.loads(line) for line in f]
    up = [r for r in excl if r["stage"] == "upstream_not_released"]
    check("R6a", "upstream exclusion ids equal the step ids in the exports' exclusions.jsonl, once each",
          sorted(x["step_id"] or f"{x['source_recording_id']}#recording" for x in src_ex), sorted(r["exclusion_id"] for r in up))
    check("R6b", "upstream exclusion counts by source reason text equal the export's counts",
          dict(collections.Counter(x["reason"] for x in src_ex)),
          dict(collections.Counter(r["reason"].split("): ", 1)[1] for r in up)))
    check("R6c", "every failed observation is listed once as filtered_variant_only, and nothing else is", sorted(k[0] + "|" + k[1] for k in failed),
          sorted(r["exclusion_id"] for r in excl if r["stage"] == "filtered_variant_only"))
    check("R6d", "exclusion rows = upstream + failed, no other stage", len(src_ex) + len(failed), len(excl))
    check("R6e", "no upstream exclusion names an observation in the full tables", [],
          [r["exclusion_id"] for r in up if r["observation_id"]])
    # R7 held columns
    held_bad = [v for t in tables for v in full[t]["held_viol"]]
    check("R7", "held columns hold no finite value in the full tables", [], held_bad[:10])
    # R8 L1/L5
    rec = {f"{k[0]}|{k[1]}": sorted(v["L"]) for t in tables for k, v in full[t]["info"].items() if v["L"]}
    ass = {f"{k[0]}|{k[1]}": sorted(set(e["failed_limits"]) & {"L1", "L5"}) for k, e in assess.items()
           if set(e["failed_limits"]) & {"L1", "L5"}}
    check("R8", "L1 and L5 failures recomputed from the full tables equal the assessment's L1 and L5 failures, per observation", ass, rec)
    # R9 / R10 seeded sample
    rng = random.Random(SEED)
    sample_subjects = rng.sample(subjects, min(3, len(subjects)))
    want = {}
    for t in tables:
        for s in sample_subjects:
            keys = sorted(k for k in full[t]["info"] if subject_of(k[0]) == s)
            want[(t, s)] = set(rng.sample(keys, min(30 if t == "phase" else 3, len(keys))))
    import gc
    gc.collect()
    trim()
    pk_vals = {}
    for t in tables:
        union = set().union(*[want[(t, s)] for s in sample_subjects])
        pk_vals[t] = stream_table(pkg / f"full_{t}.parquet", t, want=union)["values"]
    mism, compared, power_dev = [], 0, 0
    for (t, s), keys in sorted(want.items()):
        ex = collect_export(ROOT / EXPORT.format(s) / f"{t}.parquet", t, keys)
        for k in sorted(keys):
            if k not in ex:
                mism.append(f"{k[0]}: missing in export")
                continue
            compared += len(pk_vals[t][k])
            mism += [f"{k[0]} {c}" for c in same_columns(pk_vals[t][k], ex[k])]
            for j in JOINTS:
                for sd in SIDES[t]:
                    m = pk_vals[t][k][f"{j}_moment_{sd}_Nm_kg"]
                    v = pk_vals[t][k][f"{j}_velocity_{sd}_rad_s"]
                    p = pk_vals[t][k][f"{j}_power_{sd}_W_kg"]
                    new = m * v
                    ok = np.isfinite(m) & np.isfinite(v)
                    if not np.array_equal(np.isfinite(p), ok) or np.any(np.abs(p[ok] - new[ok]) > 1e-12 * np.maximum(1, np.abs(new[ok]))):
                        power_dev += 1
    check("R9", "sampled observations: every non-extra column equals the export value for value (NaN equal)", [], mism[:20])
    check("R10a", "sampled observations: power = moment x joint speed, missing exactly where either is missing", 0, power_dev)
    lim = json.loads((pkg / "limitations.json").read_text())
    ids = {x["id"] for x in lim["limitations"]}
    check("R10b", "limitations.json names every required limitation", [], [i for i in REQUIRED_LIMITATIONS if i not in ids])
    txt = {x["id"]: x["text"] for x in lim["limitations"]}
    check("R10c", "the toe-off limitation states the right-foot accuracy (0 ms median, 15 ms p95, 195 ms worst)", True,
          all(s in txt.get("left_treadmill_stance_from_belt_force", "") for s in ("0 ms", "15 ms", "195 ms")))
    report = {"task_id": "GT21-R01-readback", "version": "v1", "scientific_approval": False, "package": args.package_root,
              "seed": SEED, "sampled_subjects": sample_subjects, "sampled_observations": {f"{t}:{s}": len(v) for (t, s), v in want.items()},
              "columns_compared": compared, "checks": checks, "all_pass": all(c["pass"] for c in checks),
              "resources": {"peak_rss_mib": round(peak_rss_mib(), 1), "wall_seconds": round(time.time() - started, 1)}}
    with open(out / "readback.json", "x") as f:
        json.dump(report, f, indent=1, default=str)
    print(json.dumps({"all_pass": report["all_pass"], "failed": [c["id"] for c in checks if not c["pass"]],
                      "peak_rss_mib": report["resources"]["peak_rss_mib"]}))
    return 0 if report["all_pass"] else 1


def plan(package_root, tag, out_root):
    from contributor_tools.guarded_launcher import validate_spec
    bind = {"contributor_tools/readback_gt21_r01_package.py": sha256_file(Path(__file__)),
            f"{package_root}/manifest.json": sha256_file(ROOT / package_root / "manifest.json")}
    spec = {"job_id": f"GT21-R01-readback-{tag}",
            "command": ["python3", "contributor_tools/readback_gt21_r01_package.py", "run", "--output-root", out_root,
                        "--package-root", package_root],
            "cwd": str(ROOT), "output_root": out_root, "receipt_path": f"docs/quality/audits/gt21-r01-readback-launcher-receipt-{tag}.json",
            "bindings": bind, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["readback.json"], "address_space_mib": ADDRESS_SPACE_MIB}
    validate_spec(spec)
    path = ROOT / f"docs/quality/audits/gt21-r01-readback-spec-{tag}.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--package-root", default=PACKAGE)
    pp = sub.add_parser("plan")
    pp.add_argument("--package-root", default=PACKAGE)
    pp.add_argument("--tag", default="v1")
    pp.add_argument("--output-root", default=ROOT_OUT)
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.package_root, args.tag, args.output_root)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
