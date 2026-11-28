#!/usr/bin/env python3
"""Independent readback of a release package whose joint power was recomputed (CORE-PW01, decision D-REF-5).

Own code: it does not import the adapters, the shared builder or contributor_tools.common.joint_power. It reads the new package
and the previous package (UM21 v3 or GT23 v10) in batches of 3,000 rows, a few columns at a time, with Arrow threads off, and
writes one small JSON. Run only through contributor_tools.guarded_launcher.

  R1  manifest.sha256, sha256 and bytes of every file, no file outside the manifest, binding hashes equal the files
  R2  tables: same columns as the previous package; observations are the same (full) or a subset (pilot)
  R3  every column except the power columns, held_signals, limitations, lineage_id and assessment_id is bit-identical to the
      previous package on the same rows (floats compared by their bits, nulls by position)
  R4  power = moment x joint velocity to 1e-12 wherever both inputs are finite, and missing wherever either is missing
  R5  held_signals equal the previous text except for power keys; no power column named held holds a finite value
  R6  the gap between the previous power and the new power, per observation, median per column (independent of the builder)
  R7  assessment.jsonl and exclusions.csv equal the previous package except for what the assessment says about power
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
ADDRESS_SPACE_MIB = 768
BATCH = 3000
TOL = 1e-12
GT_J = (("hip_flexion", "hip"), ("knee_flexion", "knee"), ("ankle_dorsiflexion", "ankle"))


def _um21():
    sp = {"hip": ("hip_flexion", [("thigh_sagittal_velocity_ipsi_rad_s", 1), ("pelvis_sagittal_velocity_rad_s", -1)]),
          "knee": ("knee_flexion", [("thigh_sagittal_velocity_ipsi_rad_s", 1), ("shank_sagittal_velocity_ipsi_rad_s", -1)]),
          "ankle": ("ankle_dorsiflexion", [("foot_sagittal_velocity_ipsi_rad_s", 1), ("shank_sagittal_velocity_ipsi_rad_s", -1)])}
    specs = [(f"{j}_power_ipsi_W_kg", f"{j}_moment_ipsi_Nm_kg", v) for _, (j, v) in sp.items()]
    return {"tables": {"phase": specs},
            "old_flags": {"moments_powers_from_v2", "powers_held_sign_unsettled"},
            "new_flags": {"moments_from_v2", "power_from_moment_and_speed"}}


def _gt23():
    ph = [(f"{j}_power_{s}_W_kg", f"{j}_moment_{s}_Nm_kg", [(f"{j}_velocity_{s}_rad_s", 1)]) for s in ("ipsi", "contra") for j, _ in GT_J]
    tm = [(f"{j}_power_{s}_W_kg", f"{j}_moment_{s}_Nm_kg", [(f"{j}_velocity_{s}_rad_s", 1)]) for s in ("left", "right") for j, _ in GT_J]
    return {"tables": {"phase": ph, "time": tm}, "old_flags": set(),
            "new_flags": {"power_from_moment_and_speed", "other_powers_source_values"}}


DATASETS = {"um21": _um21, "gt23": _gt23}
SKIP_COMPARE = {"held_signals", "limitations", "lineage_id", "assessment_id"}


class Rep:
    def __init__(self):
        self.checks, self.extra = [], {}

    def check(self, name, ok, detail=""):
        self.checks.append({"id": name, "pass": bool(ok), "detail": str(detail)[:600]})
        print(("PASS " if ok else "FAIL ") + name, "" if ok else str(detail)[:300], flush=True)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def keystr(b):
    return pc.binary_join_element_wise(pc.cast(b.column("observation_id"), pa.string()),
                                       pc.cast(b.column("reference_side"), pa.string()), "|")


def key_set(path):
    ks = set()
    pf = pq.ParquetFile(path, buffer_size=0)
    for b in pf.iter_batches(batch_size=BATCH, columns=["observation_id", "reference_side"], use_threads=False):
        ks.update(pc.unique(keystr(b)).to_pylist())
    return ks


def aligned(new_path, old_path, cols, new_keys):
    """Yield (new batch table, old table of the same rows). The old file may hold more observations; they are skipped."""
    names = ["observation_id", "reference_side", *cols]
    npf = pq.ParquetFile(new_path, buffer_size=0)
    opf = pq.ParquetFile(old_path, buffer_size=0)
    oit = opf.iter_batches(batch_size=BATCH, columns=names, use_threads=False)
    kv = pa.array(sorted(new_keys), type=pa.string())
    buf, have = [], 0
    for nb in npf.iter_batches(batch_size=BATCH, columns=names, use_threads=False):
        n = nb.num_rows
        while have < n:
            ob = next(oit)
            mask = pc.is_in(keystr(ob), value_set=kv)
            t = pa.Table.from_batches([ob]).filter(mask)
            if t.num_rows:
                buf.append(t); have += t.num_rows
        allb = pa.concat_tables(buf)
        yield pa.Table.from_batches([nb]), allb.slice(0, n)
        rest = allb.slice(n)
        buf, have = ([rest] if rest.num_rows else []), rest.num_rows
    for ob in oit:
        t = pa.Table.from_batches([ob]).filter(pc.is_in(keystr(ob), value_set=kv))
        have += t.num_rows
    if have:
        raise ValueError("the previous file has rows the new file lacks")


def same(a, b):
    a, b = a.combine_chunks() if isinstance(a, pa.ChunkedArray) else a, b.combine_chunks() if isinstance(b, pa.ChunkedArray) else b
    if len(a) != len(b):
        return False
    if pa.types.is_floating(a.type):
        if not np.array_equal(a.is_null().to_numpy(zero_copy_only=False), b.is_null().to_numpy(zero_copy_only=False)):
            return False
        x = a.to_numpy(zero_copy_only=False).astype(np.float64); y = b.to_numpy(zero_copy_only=False).astype(np.float64)
        return bool(np.array_equal(x.view(np.int64), y.view(np.int64)))
    if pa.types.is_dictionary(a.type):
        a, b = a.cast(pa.string()), b.cast(pa.string())
    eq = pc.equal(a, b).fill_null(False)
    both_null = pc.and_(a.is_null(), b.is_null())
    return bool(pc.all(pc.or_(eq, both_null)).as_py())


def num(t, name):
    return t.column(name).to_numpy(zero_copy_only=False).astype(np.float64)


def runs(oids, sides):
    out, i, n = [], 0, len(oids)
    while i < n:
        j = i + 1
        while j < n and oids[j] == oids[i] and sides[j] == sides[i]:
            j += 1
        out.append(((oids[i], sides[i]), i, j))
        i = j
    return out


def compare_table(rep, tag, new_path, old_path, table, specs, is_full):
    new_names = pq.ParquetFile(new_path).schema_arrow.names
    old_names = pq.ParquetFile(old_path).schema_arrow.names
    rep.check(f"R2 {tag}: same column list as the previous package", new_names == old_names, (set(new_names) ^ set(old_names)))
    nk, ok_ = key_set(new_path), key_set(old_path)
    rep.check(f"R2 {tag}: observations equal ({'full' if is_full else 'pilot subset'})",
              (nk == ok_) if is_full else (nk <= ok_ and len(nk) > 0), (len(nk), len(ok_)))
    power = {s[0] for s in specs}
    plain = [c for c in new_names if c not in power and c not in SKIP_COMPARE and c not in ("observation_id", "reference_side")]
    bad = []
    for i in range(0, len(plain), 8):
        cols = plain[i:i + 8]
        ok = dict.fromkeys(cols, True)
        for nb, ob in aligned(new_path, old_path, cols, nk):
            for c in cols:
                if ok[c] and not same(nb.column(c), ob.column(c)):
                    ok[c] = False
        bad += [c for c, v in ok.items() if not v]
    rep.check(f"R3 {tag}: {len(plain)} non-power columns bit-identical to the previous package", not bad, bad)
    # power, held
    need = sorted({c for s in specs for c in (s[1], *[v for v, _ in s[2]])})
    pcols = sorted(power)
    maxdiff, pattern_bad, rows, finite_rows = 0.0, 0, 0, 0
    acc = {}
    held_bad, held_finite, held_cache = 0, 0, {}
    # one pass per spec group keeps the number of columns small
    for si in range(0, len(specs), 3):
        grp = specs[si:si + 3]
        cols = sorted({c for s in grp for c in (s[0], s[1], *[v for v, _ in s[2]])} | {"held_signals"})
        for nb, ob in aligned(new_path, old_path, cols, nk):
            oids, sides = nb.column("observation_id").to_pylist(), nb.column("reference_side").to_pylist()
            rr = runs(oids, sides)
            for pw, mo, vel in grp:
                m = num(nb, mo)
                v = None
                for c, sg in vel:
                    x = sg * num(nb, c)
                    v = x if v is None else v + x
                p_new, p_old = num(nb, pw), num(ob, pw)
                ok_in = np.isfinite(m) & np.isfinite(v)
                pattern_bad += int((np.isfinite(p_new) != ok_in).sum())
                if ok_in.any():
                    exp = m[ok_in] * sum(sg * num(nb, c)[ok_in] for c, sg in vel)
                    maxdiff = max(maxdiff, float(np.max(np.abs(p_new[ok_in] - exp))))
                rows += len(p_new); finite_rows += int(np.isfinite(p_new).sum())
                both = np.isfinite(p_new) & np.isfinite(p_old)
                for key, a, b in rr:
                    sel = both[a:b]
                    r = acc.setdefault((pw, key), [0.0, 0.0])
                    d = p_old[a:b][sel] - p_new[a:b][sel]
                    r[0] += float(np.sum(d * d)); r[1] += float(np.sum(p_new[a:b][sel] ** 2))
            nh, oh = nb.column("held_signals").to_pylist(), ob.column("held_signals").to_pylist()
            pset = {s[0] for s in grp}
            for (key, a, b) in rr:
                pair = (nh[a], oh[a])
                if pair not in held_cache:
                    n_, o_ = (json.loads(pair[0]) if pair[0] else {}), (json.loads(pair[1]) if pair[1] else {})
                    held_cache[pair] = ({k: x for k, x in n_.items() if k not in power} == {k: x for k, x in o_.items() if k not in power},
                                        sorted(k for k in n_ if k in power))
                same_rest, named = held_cache[pair]
                named = [k for k in named if k in pset]
                if si == 0 and not same_rest:
                    held_bad += 1
                for pw in named:
                    held_finite += int(np.isfinite(num(nb, pw)[a:b]).sum())
    rep.check(f"R4 {tag}: power = moment x joint velocity to {TOL} ({rows} rows, {finite_rows} finite)", maxdiff <= TOL, f"max abs difference {maxdiff:.3e}")
    rep.check(f"R4 {tag}: power finite exactly where moment and velocity are finite", pattern_bad == 0, pattern_bad)
    rep.check(f"R5 {tag}: held_signals equal the previous text except for power keys", held_bad == 0, held_bad)
    rep.check(f"R5 {tag}: no finite power in a column named held", held_finite == 0, held_finite)
    gaps = {}
    for pw in sorted(power):
        v = [np.sqrt(r[0] / r[1]) for (c, _), r in acc.items() if c == pw and r[1] > 0]
        gaps[pw] = {"median_nrms_previous_vs_new": float(np.median(v)) if v else None, "observations_compared": len(v)}
    rep.extra.setdefault("gap_by_column", {})[tag] = gaps
    rep.extra.setdefault("max_abs_power_difference", {})[tag] = maxdiff


def assessment_compare(rep, new_path, old_path, cfg, is_full):
    pcols = {t: {s[0] for s in sp} for t, sp in cfg["tables"].items()}
    nk = set()
    bad = {"fields": 0, "held": 0, "states": 0, "limits": 0, "missing": 0}
    n = 0
    with open(old_path) as of, open(new_path) as nf:
        old_line = of.readline()
        for line in nf:
            e = json.loads(line)
            n += 1
            key = (e["observation_id"], e["reference_side"])
            o = None
            while old_line:
                cand = json.loads(old_line)
                old_line = of.readline()
                if (cand["observation_id"], cand["reference_side"]) == key and cand["table"] == e["table"]:
                    o = cand
                    break
            if o is None:
                bad["missing"] += 1
                continue
            pc_ = pcols[e["table"]]
            if any(e[k] != o[k] for k in o if k not in ("held_signals", "channel_states", "limitations")) or set(e) != set(o):
                bad["fields"] += 1
            if {k: v for k, v in e["held_signals"].items() if k not in pc_} != {k: v for k, v in o["held_signals"].items() if k not in pc_}:
                bad["held"] += 1
            strip = lambda st: {k: sorted(c for c in v if c not in pc_) for k, v in st.items() if [c for c in v if c not in pc_]}  # noqa: E731
            if strip(e["channel_states"]) != strip(o["channel_states"]):
                bad["states"] += 1
            if [x for x in e["limitations"] if x not in cfg["new_flags"]] != [x for x in o["limitations"] if x not in cfg["old_flags"]]:
                bad["limits"] += 1
    rep.check("R7 assessment.jsonl equals the previous one except for power-related entries", not any(bad.values()), (n, bad))


def run(args):
    cfg = DATASETS[args.dataset]()
    new, old = Path(args.package_root), Path(args.previous_root)
    if not new.is_absolute():
        new = ROOT / new
    if not old.is_absolute():
        old = ROOT / old
    rep = Rep()
    man = json.loads((new / "manifest.json").read_text())
    is_full = man["stage"] == "full"
    rep.check("R1 manifest.sha256 matches manifest.json", (new / "manifest.sha256").read_text().split()[0] == sha(new / "manifest.json"))
    files = sorted(p.relative_to(new).as_posix() for p in new.rglob("*") if p.is_file() and p.name not in ("manifest.json", "manifest.sha256"))
    rep.check("R1 file list equals the manifest", files == sorted(man["files"]))
    badf = [f for f in files if sha(new / f) != man["files"][f]["sha256"] or (new / f).stat().st_size != man["files"][f]["bytes"]]
    rep.check("R1 sha256 and bytes of every file match the manifest", not badf, badf)
    b = man["binding"]
    rep.check("R1 binding hashes equal the files", all(b[k] == sha(new / f) for k, f in
              [(f"{v}_{t}.parquet", f"{v}_{t}.parquet") for v in ("full", "filtered") for t in man["tables"]] +
              [("exclusions_sha256", "exclusions.csv"), ("assessment_sha256", "assessment.jsonl")]))
    for name in ("dataset_index", "phase_preview", "test_summary", "limitations"):
        rep.check(f"R1 {name}.json carries the same binding", json.loads((new / f"{name}.json").read_text())["binding"] == b)
    rep.check("R1 builder checks all passed", json.loads((new / "test_summary.json").read_text())["all_pass"])
    for t, specs in cfg["tables"].items():
        for v in ("full", "filtered"):
            compare_table(rep, f"{v}_{t}", new / f"{v}_{t}.parquet", old / f"{v}_{t}.parquet", t, specs, is_full)
    assessment_compare(rep, new / "assessment.jsonl", old / "assessment.jsonl", cfg, is_full)
    if is_full:
        rep.check("R7 exclusions.csv is byte-identical to the previous one", sha(new / "exclusions.csv") == sha(old / "exclusions.csv"))
    out = Path(args.output_root)
    out = out if out.is_absolute() else ROOT / out
    out.mkdir(parents=True, exist_ok=False)
    res = {"package": str(args.package_root), "previous": str(args.previous_root), "stage": man["stage"],
           "all_pass": all(c["pass"] for c in rep.checks), "checks": rep.checks, **rep.extra,
           "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)}
    (out / "readback.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"all_pass": res["all_pass"], "peak_rss_mib": res["peak_rss_mib"]}))
    return 0 if res["all_pass"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run")
    p.add_argument("--dataset", choices=sorted(DATASETS), required=True)
    p.add_argument("--package-root", required=True)
    p.add_argument("--previous-root", required=True)
    p.add_argument("--output-root", required=True)
    a = p.parse_args()
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if os.nice(0) < 19 or soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher")
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
