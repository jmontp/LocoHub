#!/usr/bin/env python3
"""CORE-FOOT-01 readback: compare a rebuilt package (GT23 v12, GT21 v2, UM21 v6) with the package it was rebuilt from.

Independent of the builder, the adapters and foot_flat.py: the offsets are read from docs/quality/audits/foot-flat-offsets.json
and the rotation and the limits are written out again here. Tables are streamed in lockstep, 3,000 rows at a time. Run only
through contributor_tools.guarded_launcher (one worker, nice 19, 768 MiB address space). Writes one small JSON; repairs nothing.

  R1  new package: manifest.sha256, every file's sha256 and bytes (as the builder recorded them)
  R2  rows of the new full table equal the old ones in identity and order (old rows restricted to the new package's observations)
  R3  every column except foot angle, ankle angle, CoP anterior and CoP vertical is bit-identical to the old package
  R4  foot and ankle angle: new = old - person offset (<= 1e-12 rad); NaN and null pattern identical; people without an offset exact
  R5  ankle - (foot - shank) residual in degrees, old and new (limit 1e-9 deg)
  R6  CoP lateral bit-identical (R3); CoP anterior/vertical = rotation of the old point by the offset (<= 1e-12 m), origin 0.1 m undone
      and reapplied; NaN pattern identical
  R7  new filtered table = new full table without the observations the new assessment failed (every column, bit for bit)
  R8  L1 (ankle) and L5 (CoP) failure counts recomputed from the new full table equal the new assessment.jsonl
  R9  observation sets, status changes and exclusions.csv against the old package: every change is a listed membership change
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
import math
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = "converted_datasets/reconversion_v2"
OFFSETS = "docs/quality/audits/foot-flat-offsets.json"
EXTRA = ("source_export", "quality_status", "failed_limits", "limitations", "lineage_id", "assessment_id")
TOL_ANGLE_RAD = 1e-12
TOL_COP_M = 1e-12
TOL_COMPOSITION_DEG = 1e-9
STEP = 3000
L1 = (-80.0, 50.0)
L5 = {"cop_anterior": (-0.5, 0.5), "cop_vertical": (-0.3, 0.3)}
LIMITS_BY_TABLE = {"GT23": {"phase": True, "time": True}, "GT21": {"phase": True, "time": True}, "UM21": {"phase": True, "time": False}}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------ aligned streaming
def stream(path, columns=None, keep_ids=None, skip_ids=None):
    """Tables of up to STEP rows of one parquet file (only `columns`; they must include observation_id when an id filter is given),
    optionally restricted to / without the given observation ids."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    for b in pf.iter_batches(batch_size=STEP, columns=columns, use_threads=False):
        t = pa.Table.from_batches([b])
        if keep_ids is not None:
            t = t.filter(pc.is_in(t.column("observation_id"), value_set=keep_ids))
        if skip_ids is not None:
            t = t.filter(pc.invert(pc.is_in(t.column("observation_id"), value_set=skip_ids)))
        if t.num_rows:
            yield t


def parquet_names(path):
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).schema_arrow.names


def chunks(seq, n):
    seq = list(seq)
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def lockstep(a, b):
    """Yield (table_a, table_b) of equal length from two table iterators; raises if the total lengths differ."""
    import pyarrow as pa
    bufa, bufb, na, nb = [], [], 0, 0
    ea = eb = False
    while True:
        while not ea and na < STEP:
            try:
                t = next(a)
                bufa.append(t); na += t.num_rows
            except StopIteration:
                ea = True
        while not eb and nb < STEP:
            try:
                t = next(b)
                bufb.append(t); nb += t.num_rows
            except StopIteration:
                eb = True
        m = min(na, nb)
        if m == 0:
            if na or nb:
                raise ValueError(f"row counts differ: {na} rows left in the old stream, {nb} in the new")
            return
        ta, tb = pa.concat_tables(bufa), pa.concat_tables(bufb)
        yield ta.slice(0, m), tb.slice(0, m)
        bufa = [ta.slice(m)] if na > m else []
        bufb = [tb.slice(m)] if nb > m else []
        na, nb = na - m, nb - m
        if ea and eb and not na and not nb:
            return


def arr(col):
    a = col.combine_chunks() if hasattr(col, "combine_chunks") else col
    mask = a.is_null().to_numpy(zero_copy_only=False)
    return np.array(a.to_numpy(zero_copy_only=False), dtype=float), mask


def bit_equal(ca, cb):
    import pyarrow as pa
    if str(ca.type) != str(cb.type):
        return False
    if pa.types.is_dictionary(ca.type):      # dictionaries differ between files; compare the decoded values
        return ca.cast(ca.type.value_type).equals(cb.cast(cb.type.value_type))
    if pa.types.is_floating(ca.type):
        xa, ma = arr(ca)
        xb, mb = arr(cb)
        return bool(np.array_equal(ma, mb) and np.array_equal(xa.view(np.uint64)[~ma], xb.view(np.uint64)[~mb]))
    return bool(ca.equals(cb))


def plan(names):
    names = list(names)
    foot = [n for n in names if n.startswith("foot_sagittal_angle_") and n.endswith("_rad")]
    ankle = [n for n in names if n.startswith("ankle_dorsiflexion_angle_") and n.endswith("_rad")]
    cop = [(n, "cop_vertical_" + n[len("cop_anterior_"):]) for n in names
           if n.startswith("cop_anterior_") and n.endswith("_m") and "cop_vertical_" + n[len("cop_anterior_"):] in names]
    return foot, ankle, cop


def side_of(col):
    for tag in ("ipsi", "contra", "left", "right"):
        if f"_{tag}_" in col:
            return tag
    return None


# ------------------------------------------------------------------ one table
CHUNK = 3          # columns per pass: the package tables carry long JSON strings, so a table is read a few columns at a time


def compare_table(table, old_root, new_root, offsets, keep_ids, new_failed, new_entries, check_limits, out):
    fname = f"full_{table}.parquet"
    op, np_ = ROOT / old_root / fname, ROOT / new_root / fname
    base_old = [n for n in parquet_names(op) if n not in EXTRA]
    base_new = [n for n in parquet_names(np_) if n not in EXTRA]
    if base_old != base_new:
        raise ValueError("base column lists differ")
    foot, ankle, cop = plan(base_old)
    changed = set(foot + ankle + [c for p in cop for c in p])
    shank = [n for n in base_old if n.startswith("shank_sagittal_angle_")]
    ident = ["observation_id", "reference_side"]
    pass_a = ident + ["subject"] + [c for c in dict.fromkeys(foot + ankle + shank + [c for p in cop for c in p])]
    ident_f = ident if keep_ids is not None else []
    res = {"rows": 0, "columns_bit_identical_checked": set(), "bit_identical_failures": {}, "angle_max_dev_rad": 0.0,
           "angle_rows_shifted": 0, "angle_rows_uncorrected_exact": 0, "angle_pattern_mismatch": 0, "angle_uncorrected_not_exact": 0,
           "composition_max_residual_deg_old": 0.0, "composition_max_residual_deg_new": 0.0,
           "cop_max_dev_m": 0.0, "cop_pattern_mismatch": 0, "cop_uncorrected_not_exact": 0, "cop_samples_rotated": 0,
           "extra_columns_rows_different": {c: 0 for c in EXTRA}, "quality_status_changed_observations": set(),
           "l1_l5_recount": None, "l1_l5_mismatches": [], "passes": 0}
    counts = collections.defaultdict(int)       # ((obs, side), col) -> violations recounted from the new full table
    # pass A: identity, subject, shank (bit-identical) and the changed columns (analysed)
    for ta, tb in lockstep(stream(op, pass_a, keep_ids), stream(np_, pass_a)):
        res["rows"] += ta.num_rows
        for c in ident + ["subject"] + shank:
            res["columns_bit_identical_checked"].add(c)
            if not bit_equal(ta.column(c), tb.column(c)):
                res["bit_identical_failures"][c] = res["bit_identical_failures"].get(c, 0) + 1
        subj = ta.column("subject").to_pylist()
        off = np.array([offsets.get(s_, 0.0) for s_ in subj])
        act = off != 0.0
        res["angle_rows_shifted"] += int(act.sum())
        vals = {}
        for c in foot + ankle:
            xa, ma = arr(ta.column(c))
            xb, mb = arr(tb.column(c))
            vals[c] = (xa, xb)
            if not np.array_equal(ma, mb) or not np.array_equal(np.isnan(xa), np.isnan(xb)):
                res["angle_pattern_mismatch"] += 1
            fin = np.isfinite(xa) & np.isfinite(xb)
            dev = np.abs(xb - (xa - off))
            res["angle_max_dev_rad"] = max(res["angle_max_dev_rad"], float(dev[fin & act].max()) if (fin & act).any() else 0.0)
            un = fin & ~act
            if un.any() and not np.array_equal(xa[un].view(np.uint64), xb[un].view(np.uint64)):
                res["angle_uncorrected_not_exact"] += 1
            res["angle_rows_uncorrected_exact"] += int(un.sum())
        for a_col in ankle:
            tag = side_of(a_col)
            f_col = next((c for c in foot if side_of(c) == tag), None)
            s_col = next((c for c in shank if side_of(c) == tag), None)
            if f_col is None or s_col is None:
                continue
            sh, _ = arr(ta.column(s_col))
            (fa, fb), (aa, ab) = vals[f_col], vals[a_col]
            ok = np.isfinite(fa) & np.isfinite(sh) & np.isfinite(aa) & np.isfinite(fb) & np.isfinite(ab)
            if ok.any():
                res["composition_max_residual_deg_old"] = max(res["composition_max_residual_deg_old"],
                                                              float(np.degrees(np.abs(aa - (fa - sh))[ok]).max()))
                res["composition_max_residual_deg_new"] = max(res["composition_max_residual_deg_new"],
                                                              float(np.degrees(np.abs(ab - (fb - sh))[ok]).max()))
        c_, s_ = np.cos(off), np.sin(off)
        newcop = {}
        for an, ve in cop:
            a0, ma0 = arr(ta.column(an)); a1, ma1 = arr(tb.column(an))
            v0, mv0 = arr(ta.column(ve)); v1, mv1 = arr(tb.column(ve))
            newcop[an], newcop[ve] = a1, v1
            if not (np.array_equal(np.isnan(a0), np.isnan(a1)) and np.array_equal(np.isnan(v0), np.isnan(v1))
                    and np.array_equal(ma0, ma1) and np.array_equal(mv0, mv1)):
                res["cop_pattern_mismatch"] += 1
            both = np.isfinite(a0) & np.isfinite(v0)
            ex_a = (a0 + 0.1) * c_ - v0 * s_ - 0.1
            ex_v = (a0 + 0.1) * s_ + v0 * c_
            r = both & act
            if r.any():
                res["cop_max_dev_m"] = max(res["cop_max_dev_m"], float(np.abs(a1 - ex_a)[r].max()), float(np.abs(v1 - ex_v)[r].max()))
                res["cop_samples_rotated"] += int(r.sum())
            u = (np.isfinite(a0) | np.isfinite(v0)) & ~act
            if u.any() and not (np.array_equal(a0[u].view(np.uint64), a1[u].view(np.uint64)) and
                                np.array_equal(v0[u].view(np.uint64), v1[u].view(np.uint64))):
                res["cop_uncorrected_not_exact"] += 1
        if check_limits:
            oid = tb.column("observation_id").to_pylist()
            sd = tb.column("reference_side").to_pylist()
            starts = [0] + [i for i in range(1, len(oid)) if oid[i] != oid[i - 1] or sd[i] != sd[i - 1]] + [len(oid)]
            for a, b in zip(starts[:-1], starts[1:]):
                key = (oid[a], sd[a])
                for c in ankle:
                    x = np.degrees(vals[c][1][a:b])
                    n = int((np.isfinite(x) & ((x < L1[0]) | (x > L1[1]))).sum())
                    if n:
                        counts[(key, c)] += n
                for c, x_all in newcop.items():
                    lo, hi = L5["cop_anterior" if c.startswith("cop_anterior") else "cop_vertical"]
                    x = x_all[a:b]
                    n = int((np.isfinite(x) & ((x < lo) | (x > hi))).sum())
                    if n:
                        counts[(key, c)] += n
    res["passes"] += 1
    # passes B: every other base column, bit for bit
    others = [c for c in base_old if c not in changed and c not in pass_a]
    for group in chunks(others, CHUNK):
        cols = ident_f + group
        n_rows = 0
        for ta, tb in lockstep(stream(op, cols, keep_ids), stream(np_, cols)):
            n_rows += ta.num_rows
            for c in group:
                res["columns_bit_identical_checked"].add(c)
                if not bit_equal(ta.column(c), tb.column(c)):
                    res["bit_identical_failures"][c] = res["bit_identical_failures"].get(c, 0) + 1
        if n_rows != res["rows"]:
            raise ValueError(f"pass over {group}: {n_rows} rows, pass A had {res['rows']}")
        res["passes"] += 1
    # passes E: the identity columns the builder appends
    for group in (["source_export", "quality_status"], ["failed_limits", "limitations"], ["lineage_id", "assessment_id"]):
        cols = ident + group
        for ta, tb in lockstep(stream(op, cols, keep_ids), stream(np_, cols)):
            for c in group:
                if c in ("lineage_id", "assessment_id"):
                    res["extra_columns_rows_different"][c] += ta.num_rows
                    continue
                da, db = ta.column(c).combine_chunks().to_pylist(), tb.column(c).combine_chunks().to_pylist()
                diff = [i for i, (x, y) in enumerate(zip(da, db)) if x != y]
                res["extra_columns_rows_different"][c] += len(diff)
                if c == "quality_status":
                    oid = tb.column("observation_id").to_pylist()
                    sd = tb.column("reference_side").to_pylist()
                    res["quality_status_changed_observations"].update((oid[i], sd[i]) for i in diff)
        res["passes"] += 1
    res["columns_bit_identical_checked"] = sorted(res["columns_bit_identical_checked"])
    if check_limits:
        want = {}
        for key, e in new_entries.items():
            if e["table"] != table:
                continue
            for c, d in e["failed_samples"].items():
                n = d.get("L1", 0) if c.startswith("ankle_dorsiflexion_angle_") else d.get("L5", 0)
                if n and (c.startswith("ankle_dorsiflexion_angle_") or c.startswith(("cop_anterior_", "cop_vertical_"))):
                    want[(key, c)] = n
        keys = set(want) | set(counts)
        bad = [(k[0][0], k[0][1], k[1], want.get(k, 0), counts.get(k, 0)) for k in keys if want.get(k, 0) != counts.get(k, 0)]
        res["l1_l5_recount"] = {"observation_columns_with_failures_in_assessment": len(want), "recount": len(counts), "mismatches": len(bad)}
        res["l1_l5_mismatches"] = sorted(bad)[:20]
    else:
        res["l1_l5_recount"] = "not applicable: this table carries no L1/L5 assessment"
    res["quality_status_changed_observations"] = sorted(res["quality_status_changed_observations"])
    return res


def compare_filtered(table, new_root, new_failed_ids):
    """new filtered = new full without the failed observations, every column, bit for bit (a few columns per pass)."""
    fp, fq = ROOT / new_root / f"full_{table}.parquet", ROOT / new_root / f"filtered_{table}.parquet"
    names = parquet_names(fp)
    if names != parquet_names(fq):
        raise ValueError("column lists differ")
    rows, bad = 0, collections.Counter()
    for group in chunks([n for n in names if n != "observation_id"], CHUNK):
        cols = ["observation_id"] + group
        n_rows = 0
        for ta, tb in lockstep(stream(fp, cols, skip_ids=new_failed_ids), stream(fq, cols)):
            n_rows += ta.num_rows
            for c in cols:
                if not bit_equal(ta.column(c), tb.column(c)):
                    bad[c] += 1
        rows = n_rows
    return {"rows": rows, "columns_with_differences": dict(bad)}


# ------------------------------------------------------------------ package-level facts
_EMPTY = {}


def read_assessment(root):
    """{(observation_id, reference_side): small dict}; only the facts the readback needs stay in memory."""
    out = {}
    it = sys.intern
    with open(ROOT / root / "assessment.jsonl") as f:
        for line in f:
            e = json.loads(line)
            fs = {it(c): {it(k): v for k, v in d.items()} for c, d in e["failed_samples"].items()} or _EMPTY
            out[(e["observation_id"], it(e["reference_side"]))] = {
                "table": it(e["table"]), "status": it(e["status"]), "failed_samples": fs, "subject": it(e["subject"]),
                "rows": int(e["rows"])}
    return out


def read_exclusions(root):
    with open(ROOT / root / "exclusions.csv", newline="") as f:
        return list(csv.DictReader(f))


def check_manifest(root):
    p = ROOT / root
    m = json.loads((p / "manifest.json").read_text())
    ok_top = (p / "manifest.sha256").read_text().split()[0] == sha256_file(p / "manifest.json")
    bad = []
    for rel, v in m["files"].items():
        if (p / rel).stat().st_size != v["bytes"] or sha256_file(p / rel) != v["sha256"]:
            bad.append(rel)
    on_disk = sorted(x.relative_to(p).as_posix() for x in p.rglob("*") if x.is_file() and x.name not in ("manifest.json", "manifest.sha256"))
    return {"manifest_sha256_ok": ok_top, "files_with_wrong_hash_or_size": bad, "files_not_in_manifest": sorted(set(on_disk) - set(m["files"]))}


def run(args):
    t0 = time.time()
    old_root = f"{BASE}/{args.old_package}"
    new_root = f"{BASE}/{args.new_package}"
    offs = json.loads((ROOT / OFFSETS).read_text())["datasets"][args.dataset]
    offsets = {s: float(v["offset_rad"]) for s, v in offs["people"].items() if v.get("offset_rad") is not None}
    tables = ["phase", "time"] if args.tables == "both" else [args.tables]
    out_dir = (ROOT / args.output_root).resolve()
    out_dir.mkdir(parents=True, exist_ok=False)
    result = {"dataset": args.dataset, "old_package": args.old_package, "new_package": args.new_package, "tables": tables,
              "offsets_sha256": sha256_file(ROOT / OFFSETS), "people_with_offset": len(offsets),
              "people_without_offset": offs["persons_without_offset"], "checks": []}

    def check(cid, desc, ok, detail=None):
        result["checks"].append({"id": cid, "check": desc, "pass": bool(ok), "detail": detail})

    if not args.skip_manifest:
        mf = check_manifest(new_root)
        check("R1", "new package manifest and every file hash/size as recorded", mf["manifest_sha256_ok"] and not mf["files_with_wrong_hash_or_size"]
              and not mf["files_not_in_manifest"], mf)
    new_a, old_all = read_assessment(new_root), read_assessment(old_root)
    only_new, only_old = set(new_a) - set(old_all), set(old_all) - set(new_a)
    old_a = {k: {"status": v["status"]} for k, v in old_all.items() if k in new_a}
    del old_all
    check("R9a", "observation set of the new package equals the old package (restricted to the new package's observations in a pilot)",
          not only_new and (args.subset or not only_old), {"only_in_new": len(only_new), "only_in_old": len(only_old)})
    flips = {k: (old_a[k]["status"], new_a[k]["status"]) for k in new_a if k in old_a and old_a[k]["status"] != new_a[k]["status"]}
    newly_failed = sorted(k for k, (a, b) in flips.items() if b == "failed")
    recovered = sorted(k for k, (a, b) in flips.items() if b != "failed")
    with open(ROOT / new_root / "evidence/foot_flat_membership_changes.csv", newline="") as f:
        listed = {(r["observation_id"], r["reference_side"], r["table"]): (r["status_before"], r["status_after"]) for r in csv.DictReader(f)}
    flips_with_table = {(k[0], k[1], new_a[k]["table"]): v for k, v in flips.items()}
    check("R9b", "every status change is listed once in evidence/foot_flat_membership_changes.csv and nothing else is listed",
          flips_with_table == listed, {"status_changes": len(flips), "newly_failed": len(newly_failed), "recovered": len(recovered), "listed": len(listed)})
    # exclusions.csv
    ex_old = read_exclusions(old_root)
    ex_new = read_exclusions(new_root)
    if args.subset:
        if args.dataset == "UM21":
            recs = {r["source_recording_id"] for r in json.loads((ROOT / new_root / "dataset_index.json").read_text())["recordings"]}
            ex_old = [r for r in ex_old if r["source_recording_id"] in recs]
        else:
            subjects = {v["subject"] for v in new_a.values()}
            ex_old = [r for r in ex_old if r["subject"] in subjects]
    key = lambda r: json.dumps(r, sort_keys=True)  # noqa: E731
    up_old = sorted(key(r) for r in ex_old if r["kind"] != "assessment_failed")
    up_new = sorted(key(r) for r in ex_new if r["kind"] != "assessment_failed")
    check("R9c", "exclusions.csv: every non-assessment (upstream) row is identical to the old package", up_old == up_new,
          {"old": len(up_old), "new": len(up_new)})
    af_old = {r["exclusion_id"] for r in ex_old if r["kind"] == "assessment_failed"}
    af_new = {r["exclusion_id"] for r in ex_new if r["kind"] == "assessment_failed"}
    exp_new = (af_old | {f"{k[0]}|{k[1]}" for k in newly_failed}) - {f"{k[0]}|{k[1]}" for k in recovered}
    check("R9d", "exclusions.csv assessment rows = old rows + newly failed - recovered, exactly", af_new == exp_new,
          {"old": len(af_old), "new": len(af_new), "expected": len(exp_new)})
    all_ids_new = {r["exclusion_id"] for r in ex_new}
    check("R9e", "every failed observation of the new assessment is in exclusions.csv exactly once",
          sorted(f"{k[0]}|{k[1]}" for k, v in new_a.items() if v["status"] == "failed") == sorted(r["exclusion_id"] for r in ex_new if r["kind"] == "assessment_failed"))
    # counts
    di_old = json.loads((ROOT / old_root / "dataset_index.json").read_text())["counts"]
    di_new = json.loads((ROOT / new_root / "dataset_index.json").read_text())["counts"]
    result["counts_old"], result["counts_new"] = di_old, di_new
    n_failed_new = sum(1 for v in new_a.values() if v["status"] == "failed")
    n_failed_old = sum(1 for v in old_a.values() if v["status"] == "failed")
    check("R9f", "failed observations: new = old + newly failed - recovered; full observations unchanged; filtered = full - failed",
          n_failed_new == n_failed_old + len(newly_failed) - len(recovered) and di_new["observations_full"] == di_new["observations_filtered"] + di_new["failed_observations"]
          and di_new["failed_observations"] == n_failed_new and (args.subset or di_new["observations_full"] == di_old["observations_full"]),
          {"failed_old": n_failed_old, "failed_new": n_failed_new})
    keep_ids = None
    import pyarrow as pa
    keep_ids = pa.array(sorted({k[0] for k in new_a})) if args.subset else None
    failed_ids = pa.array(sorted({k[0] for k, v in new_a.items() if v["status"] == "failed"}))
    for table in tables:
        entries = {k: v for k, v in new_a.items() if v["table"] == table}
        r = compare_table(table, old_root, new_root, offsets, keep_ids, failed_ids, entries, LIMITS_BY_TABLE[args.dataset][table], result)
        rows_expected = sum(v["rows"] for v in entries.values())
        flipped_ids = {k for k in flips if new_a[k]["table"] == table}
        check(f"R2.{table}", f"{table}: rows of the new full table equal the assessed rows and the old rows of the same observations",
              r["rows"] == rows_expected, {"rows": r["rows"], "assessed_rows": rows_expected})
        check(f"R3.{table}", f"{table}: every column except foot/ankle/CoP anterior+vertical is bit-identical to the old package",
              not r["bit_identical_failures"], {"columns_checked": len(r["columns_bit_identical_checked"]), "passes": r["passes"], "failures": r["bit_identical_failures"]})
        check(f"R4.{table}", f"{table}: foot and ankle angle = old - person offset (<= 1e-12 rad), patterns identical, uncorrected people exact",
              r["angle_max_dev_rad"] <= TOL_ANGLE_RAD and not r["angle_pattern_mismatch"] and not r["angle_uncorrected_not_exact"],
              {k: r[k] for k in ("angle_max_dev_rad", "angle_rows_shifted", "angle_rows_uncorrected_exact", "angle_pattern_mismatch", "angle_uncorrected_not_exact")})
        check(f"R5.{table}", f"{table}: ankle - (foot - shank) residual < 1e-9 deg after the change",
              r["composition_max_residual_deg_new"] < TOL_COMPOSITION_DEG,
              {"max_residual_deg_old": r["composition_max_residual_deg_old"], "max_residual_deg_new": r["composition_max_residual_deg_new"]})
        check(f"R6.{table}", f"{table}: CoP anterior/vertical = rotated old point (<= 1e-12 m), patterns identical, uncorrected people exact",
              r["cop_max_dev_m"] <= TOL_COP_M and not r["cop_pattern_mismatch"] and not r["cop_uncorrected_not_exact"],
              {k: r[k] for k in ("cop_max_dev_m", "cop_samples_rotated", "cop_pattern_mismatch", "cop_uncorrected_not_exact")})
        check(f"R8.{table}", f"{table}: L1/L5 failure counts recomputed from the new full table equal the new assessment",
              (r["l1_l5_recount"]["mismatches"] == 0) if isinstance(r["l1_l5_recount"], dict) else True,
              {"recount": r["l1_l5_recount"], "first_mismatches": r["l1_l5_mismatches"]})
        qs = set(r["quality_status_changed_observations"])
        check(f"R9g.{table}", f"{table}: rows whose quality_status changed belong exactly to the status-changed observations",
              qs == {k for k in flips if new_a[k]["table"] == table}, {"changed_observations": len(qs), "expected": len(flipped_ids)})
        result.setdefault("extra_columns_rows_different", {})[table] = r["extra_columns_rows_different"]
        f = compare_filtered(table, new_root, failed_ids)
        exp_f = rows_expected - sum(v["rows"] for k, v in entries.items() if v["status"] == "failed")
        check(f"R7.{table}", f"{table}: new filtered = new full without the failed observations, bit for bit, every column",
              not f["columns_with_differences"] and f["rows"] == exp_f, {"rows": f["rows"], "expected_rows": exp_f, "columns_with_differences": f["columns_with_differences"]})
    result["all_pass"] = all(c["pass"] for c in result["checks"])
    result["resources"] = {"peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                           "wall_seconds": round(time.time() - t0, 1)}
    (out_dir / "readback.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"all_pass": result["all_pass"], "failed": [c["id"] for c in result["checks"] if not c["pass"]], **result["resources"]}))
    return 0 if result["all_pass"] else 1


def plan_job(args):
    from contributor_tools.guarded_launcher import validate_spec
    tag = args.tag
    out_root = f"{BASE}/core_foot_01_readback_{tag}"
    cmd = ["python3", "contributor_tools/readback_foot_flat.py", "run", "--output-root", out_root, "--dataset", args.dataset,
           "--old-package", args.old_package, "--new-package", args.new_package, "--tables", args.tables]
    if args.subset:
        cmd.append("--subset")
    if args.skip_manifest:
        cmd.append("--skip-manifest")
    bindings = {"contributor_tools/readback_foot_flat.py": sha256_file(ROOT / "contributor_tools/readback_foot_flat.py"),
                f"{BASE}/{args.new_package}/manifest.json": sha256_file(ROOT / BASE / args.new_package / "manifest.json"),
                f"{BASE}/{args.old_package}/manifest.json": sha256_file(ROOT / BASE / args.old_package / "manifest.json"),
                OFFSETS: sha256_file(ROOT / OFFSETS)}
    spec = {"job_id": f"CORE-FOOT-01-readback-{tag}", "command": cmd, "cwd": str(ROOT), "output_root": out_root,
            "receipt_path": f"docs/quality/audits/core-foot-01-readback-launcher-receipt-{tag}.json", "bindings": bindings,
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["readback.json"], "address_space_mib": 768}
    validate_spec(spec)
    path = ROOT / f"docs/quality/audits/core-foot-01-readback-spec-{tag}.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    for name in ("run", "plan"):
        s = sub.add_parser(name)
        s.add_argument("--dataset", choices=("GT23", "GT21", "UM21"), required=True)
        s.add_argument("--old-package", required=True)
        s.add_argument("--new-package", required=True)
        s.add_argument("--tables", choices=("phase", "time", "both"), default="both")
        s.add_argument("--subset", action="store_true", help="new package is a pilot: compare with the old rows of its observations only")
        s.add_argument("--skip-manifest", action="store_true", help="hash check of the new package's files is a separate job")
        if name == "run":
            s.add_argument("--output-root", required=True)
        else:
            s.add_argument("--tag", required=True)
    args = p.parse_args(argv)
    return run(args) if args.step == "run" else plan_job(args)


if __name__ == "__main__":
    sys.exit(main())
