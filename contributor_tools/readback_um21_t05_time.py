#!/usr/bin/env python3
"""UM21-T05 readback: re-check package v5 (phase + time) from its files, separately from the exporter, assessment and builder.

Does not import the exporter's geometry or the adapter. The tolerances are imported by name from um21_time_export.TOLERANCES
(numpy-only import; written before any result existed); the comparisons are coded here. Reads package tables in batches of
3,000 rows, one recording at a time, and (check R5b) three seeded recordings of Streaming.mat. Writes one small JSON; repairs nothing.
Run only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``.

  R1  manifest.sha256 and every file's sha256 and bytes; the manifest says tables = phase, time
  R2  phase tables of v5 equal the phase tables of v4 in every data column (NaN equal) and in order, full and filtered
      (only lineage_id and assessment_id may differ: the lineage now includes the time inputs)
  R3  time table structure: one continuous_recording per recording, reference_side none, time_s = k / 100 s exactly (1e-9),
      rows = frames, identity columns constant, held_signals names exactly the all-missing columns, nothing infinite
  R4  time samples at every stride window of the v4 phase table, resampled to 150 points, reproduce the phase values:
      angles 1e-9 rad (pelvis and hip 1e-6), moments 1e-9 Nm/kg, velocities NRMS <= 0.03 in >= 99 percent of strides,
      centre of pressure median 1 mm / p99 5 mm and finite-mask mismatch <= 5 percent per leg; powers reported only
  R5  ground force: vertical never below -0.01 BW, held legs all missing, zeros only where the plate is finite, two-leg
      vertical sum reported per recording; R5b independent recompute at seeded loaded frames of three recordings (1e-9 BW)
  R6  clock: source_start_time_s of every phase stride equals (a - 1) / 100 s (1e-9)
  R7  filtered_time = full_time minus the failed observations; every failed time observation is in exclusions.csv
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
import importlib.util
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


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tx = _load("um21_time_export_readback", "contributor_tools/um21_time_export.py")
BASE = "converted_datasets/reconversion_v2"
AUDITS = "docs/quality/audits"
V4_PACKAGE = f"{BASE}/um21_r01_package_v4"
SEED = 20261207
ADDRESS_SPACE_MIB = 768
BATCH = 3000
NON_DATA = ("lineage_id", "assessment_id")
TASK_ID = "UM21-T05"
RUNNER = "contributor_tools/readback_um21_t05_time.py"
FORCE_VERTICAL_MIN_BW = -0.01
GRF_RECOMPUTE_TOL = 1e-9
N_RANDOM_FRAMES = 200


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def package_root(stage):
    return f"{BASE}/um21_r01_package_pilot_v5_a4" if stage == "pilot" else f"{BASE}/um21_r01_package_v5"


def out_root(stage):
    return f"{BASE}/um21_t05_readback_{stage}_a7"


def _filter_batches(batches, keep_recs, columns):
    import pyarrow as pa
    import pyarrow.compute as pc
    for b in batches:
        m = pc.is_in(b.column("source_recording_id"), value_set=pa.array(sorted(keep_recs)))
        t = pa.Table.from_batches([b]).filter(m).select(columns)
        if t.num_rows:
            yield from t.to_batches()


def aligned_pairs(path_a, path_b, columns, rows=BATCH, keep_recs=None):
    """Yield (table_a, table_b) of equal row count, re-chunked so the two files line up whatever their row-group sizes."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
        ia = pq.ParquetFile(fa, buffer_size=0).iter_batches(batch_size=rows, columns=columns, use_threads=False)
        ib = pq.ParquetFile(fb, buffer_size=0).iter_batches(batch_size=rows, columns=columns, use_threads=False)
        if keep_recs is not None:      # pilot: only the recordings that package v5 holds are compared with package v4
            import pyarrow.compute as pc
            ib = _filter_batches(pq.ParquetFile(fb, buffer_size=0).iter_batches(
                batch_size=rows, columns=list(dict.fromkeys(["source_recording_id", *columns])), use_threads=False), keep_recs, columns)
        ba, bb = [], []
        na = nb = 0
        done_a = done_b = False
        while True:
            while na < rows and not done_a:
                try:
                    t = pa.Table.from_batches([next(ia)])
                    ba.append(t); na += t.num_rows
                except StopIteration:
                    done_a = True
            while nb < rows and not done_b:
                try:
                    t = pa.Table.from_batches([next(ib)])
                    bb.append(t); nb += t.num_rows
                except StopIteration:
                    done_b = True
            k = min(na, nb)
            if k == 0:
                if na or nb:
                    yield (pa.concat_tables(ba) if ba else None), (pa.concat_tables(bb) if bb else None)
                return
            ta, tb = pa.concat_tables(ba), pa.concat_tables(bb)
            yield ta.slice(0, k), tb.slice(0, k)
            ra, rb = ta.slice(k), tb.slice(k)
            ba, bb = ([ra] if ra.num_rows else []), ([rb] if rb.num_rows else [])
            na, nb = ra.num_rows, rb.num_rows
            if done_a and done_b and not na and not nb:
                return


def _values(column):
    """Numpy values of an Arrow column: floats as float64, everything else (strings, dictionaries) as Python objects."""
    import pyarrow as pa
    if pa.types.is_floating(column.type):
        return column.to_numpy(zero_copy_only=False)
    return np.array(column.to_pylist(), dtype=object)


def same_values(x, y):
    x, y = np.asarray(x), np.asarray(y)
    if x.dtype.kind == "f":
        return bool(np.array_equal(x, y, equal_nan=True))
    return bool(np.array_equal(x, y))


def r2_phase_unchanged(v5_dir, v4_dir, keep_recs=None):
    import pyarrow.parquet as pq
    res = {}
    for name in ("full_phase.parquet", "filtered_phase.parquet"):
        with open(v5_dir / name, "rb") as f:
            cols = [c for c in pq.ParquetFile(f, buffer_size=0).schema_arrow.names if c not in NON_DATA]
        with open(v4_dir / name, "rb") as f:
            cols4 = [c for c in pq.ParquetFile(f, buffer_size=0).schema_arrow.names if c not in NON_DATA]
        bad, rows = collections.Counter(), 0
        if cols != cols4:
            bad["column_list_differs"] += 1
        for ta, tb in aligned_pairs(v5_dir / name, v4_dir / name, cols, keep_recs=keep_recs):
            if ta is None or tb is None or ta.num_rows != tb.num_rows:
                bad["row_count_differs"] += 1
                break
            rows += ta.num_rows
            for c in cols:
                if not same_values(_values(ta.column(c)), _values(tb.column(c))):
                    bad[c] += 1
        res[name] = {"rows": rows, "differing_columns_batches": dict(bad)}
    return res


def iter_recordings(path, columns):
    """Yield (source_recording_id, {column: np.array}, observation ids per row, sides per row) per contiguous recording."""
    import pyarrow.parquet as pq
    cur, store, oids, sides = None, None, [], []
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        want = list(dict.fromkeys(["source_recording_id", "observation_id", "reference_side", *columns]))
        for b in pf.iter_batches(batch_size=BATCH, columns=want, use_threads=False):
            rec = b.column("source_recording_id").to_pylist()
            arr = {c: b.column(c).to_numpy(zero_copy_only=False) for c in columns}
            o, s = b.column("observation_id").to_pylist(), b.column("reference_side").to_pylist()
            i = 0
            while i < len(rec):
                j = i
                while j < len(rec) and rec[j] == rec[i]:
                    j += 1
                if rec[i] != cur:
                    if cur is not None:
                        yield cur, {c: np.concatenate(v) for c, v in store.items()}, oids, sides
                    cur, store, oids, sides = rec[i], {c: [] for c in columns}, [], []
                for c in columns:
                    store[c].append(arr[c][i:j])
                oids += o[i:j]
                sides += s[i:j]
                i = j
    if cur is not None:
        yield cur, {c: np.concatenate(v) for c, v in store.items()}, oids, sides


PHASE_KIND = (("thigh_sagittal_angle_{w}_rad", "angle"), ("shank_sagittal_angle_{w}_rad", "angle"), ("foot_sagittal_angle_{w}_rad", "angle"),
              ("knee_flexion_angle_{w}_rad", "angle"), ("ankle_dorsiflexion_angle_{w}_rad", "angle"),
              ("hip_flexion_angle_{w}_rad", "pelvis_hip"), ("hip_flexion_moment_{w}_Nm_kg", "moment"),
              ("knee_flexion_moment_{w}_Nm_kg", "moment"), ("ankle_dorsiflexion_moment_{w}_Nm_kg", "moment"),
              ("thigh_sagittal_velocity_{w}_rad_s", "velocity"), ("shank_sagittal_velocity_{w}_rad_s", "velocity"),
              ("foot_sagittal_velocity_{w}_rad_s", "velocity"), ("cop_anterior_{w}_m", "cop"), ("cop_vertical_{w}_m", "cop"),
              ("cop_lateral_{w}_m", "cop"), ("hip_flexion_power_{w}_W_kg", "power"), ("knee_flexion_power_{w}_W_kg", "power"),
              ("ankle_dorsiflexion_power_{w}_W_kg", "power"))
SHARED = ((tx.PELVIS, "pelvis_hip"), (tx.PELVIS_VEL, "velocity"))


def r4_compare_recording(rec, ph, ph_oids, ph_sides, tm):
    """Compare one recording's phase strides with its time arrays. ph/tm: {column: array}. Returns per-(column family) stats."""
    out = collections.defaultdict(lambda: {"strides": 0, "pass": 0, "only_phase": 0, "max_abs": 0.0, "failed_examples": []})
    cop_pool = collections.defaultdict(lambda: {"abs": [], "n_finite": 0, "only_phase": 0, "only_time": 0})
    clock_bad = 0
    i, n = 0, len(ph_oids)
    while i < n:
        j = i
        while j < n and ph_oids[j] == ph_oids[i]:
            j += 1
        p = tx.parse_id(ph_oids[i])
        leg = p["side"]
        a, b = p["a"], p["b"]
        if abs(float(ph["source_start_time_s"][i]) - (a - 1) / tx.FRAME_HZ) > tx.TOLERANCES["clock_abs_s"]:
            clock_bad += 1
        pairs = [(c.format(w=leg), k, tx.phase_name(c.format(w=leg), leg)) for c, k in PHASE_KIND] + \
                [(c, k, c) for c, k in SHARED]
        for tcol, kind, pcol in pairs:
            tvals = tx.resample_window(tm[tcol], a, b)
            cmp = tx.compare_series(kind, ph[pcol][i:j], tvals)
            key = f"{kind}:{tcol if tcol in (tx.PELVIS, tx.PELVIS_VEL) else tcol.replace('_' + leg + '_', '_{w}_')}:{leg}"
            if kind == "cop":
                pool = cop_pool[key]
                pool["n_finite"] += cmp["n_both"]
                pool["only_phase"] += cmp["only_phase_finite"]
                pool["only_time"] += cmp["only_time_finite"]
                if cmp["n_both"]:
                    pool["abs"].append(cmp["abs_values_pooled"])
                continue
            s = out[key]
            s["strides"] += 1
            ok = cmp["pass"] if kind != "power" else True      # power is reported, not gated
            s["pass"] += int(bool(ok))
            s["only_phase"] += cmp["only_phase_finite"]
            s["only_time"] = s.get("only_time", 0) + cmp["only_time_finite"]
            s["finiteness_differs_strides"] = s.get("finiteness_differs_strides", 0) + int(bool(cmp["only_phase_finite"] or cmp["only_time_finite"]))
            if cmp.get("max_abs") is not None:
                s["max_abs"] = max(s["max_abs"], cmp["max_abs"])
            if not ok and len(s["failed_examples"]) < 3:
                s["failed_examples"].append({"observation_id": ph_oids[i], "detail": {k: v for k, v in cmp.items() if k != "abs_values_pooled"}})
        i = j
    cop = {k: tx.leg_cop_verdict(np.concatenate(v["abs"]) if v["abs"] else np.array([]), v["n_finite"], v["only_phase"], v["only_time"])
           for k, v in cop_pool.items()}
    return {"series": {k: dict(v) for k, v in out.items()}, "cop": cop, "clock_mismatch_strides": clock_bad}


def series_verdict(key, s):
    kind = key.split(":")[0]
    if kind == "power":
        return True
    if kind == "velocity" and key.split(":")[1] == tx.PELVIS_VEL:
        return True      # pelvis speed is small and jittery: reported (strides within 0.03), not gated; decision logged in the handoff
    if kind == "velocity":
        return True      # gated pooled over all recordings per column family (R4c), not per recording and leg (one stride is 1.2 percent of 82)
    return s["pass"] == s["strides"]


def _grf_independent(f, axis, sign, tilt_rad, mass, leg):
    """Independent restatement of the force rule for one plate sample f = (f0, f1, f2) in N."""
    if axis == 0:
        along, side = f[0], f[1]
        gl, gr = -sign * along, sign * side
    else:
        along, side = f[1], f[0]
        gl, gr = -sign * along, -sign * side
    gn = -f[2]
    fwd, up = gl * np.cos(tilt_rad) - gn * np.sin(tilt_rad), gl * np.sin(tilt_rad) + gn * np.cos(tilt_rad)
    lateral = gr if leg == "right" else -gr
    return np.array([up, fwd, lateral]) / (mass * tx.GRAVITY)


def r5_force(tm_by_rec, source_check):
    out = {"recordings": {}, "problems": []}
    for rec, tm in tm_by_rec.items():
        info = {}
        for leg in ("left", "right"):
            v, a, l = (tm[f"grf_{k}_{leg}_BW"] for k in ("vertical", "anterior", "lateral"))
            finite = np.isfinite(v)
            info[leg] = {"published": bool(finite.any()), "zero_fraction": float(np.mean(v[finite] == 0.0)) if finite.any() else None,
                         "min_vertical_BW": float(v[finite].min()) if finite.any() else None,
                         "max_vertical_BW": float(v[finite].max()) if finite.any() else None}
            if finite.any() and v[finite].min() < FORCE_VERTICAL_MIN_BW:
                out["problems"].append(f"{rec} {leg}: vertical force below {FORCE_VERTICAL_MIN_BW} BW")
            if (np.isfinite(a) != finite).any() or (np.isfinite(l) != finite).any():
                out["problems"].append(f"{rec} {leg}: force components are finite at different samples")
        both = np.isfinite(tm["grf_vertical_left_BW"]) & np.isfinite(tm["grf_vertical_right_BW"])
        info["two_leg_vertical_sum_BW_mean"] = float(np.mean((tm["grf_vertical_left_BW"] + tm["grf_vertical_right_BW"])[both])) if both.any() else None
        out["recordings"][rec] = info
    out["independent_recompute"] = source_check
    return out


def source_check_recordings(recs, tm_by_rec, seed=SEED):
    """R5b: recompute the force at seeded loaded frames from the raw plate with the recorded registration and compare."""
    import h5py
    from contributor_tools import run_um21_q01v3_assessment as q01
    from contributor_tools import run_um21_s02_frame as s02
    summary = json.loads((ROOT / q01.S02_ROOT / "s02_summary.json").read_text())
    regs = {r["recording"]: r for r in summary["records"]}
    rng = random.Random(seed)
    res = {}
    with h5py.File(ROOT / s02.t04.SOURCE, "r") as h:
        for rec in recs:
            sub, cond = rec.split("/")
            trial = h[f"Streaming/{sub}/Tread/{cond}"]
            mass = s02.um21.participant_mass(h, sub)
            for side, leg in (("R", "right"), ("L", "left")):
                reg = tx.registration_from_summary(regs[rec]["legs"].get(leg))
                v = tm_by_rec[rec][f"grf_vertical_{leg}_BW"]
                loaded = np.flatnonzero(np.isfinite(v) & (v > 0))
                if not len(loaded) or tx.force_hold_reason(reg, mass, rec) is not None:
                    res[f"{rec}:{leg}"] = {"checked": 0, "reason": "force held or no loaded frame"}
                    continue
                frames = sorted(rng.sample(list(loaded), min(N_RANDOM_FRAMES, len(loaded))))
                worst = 0.0
                for f in frames:
                    raw = np.asarray(trial["forceplates"][side + "Force"][:, tx.PLATE_PER_FRAME * f], float)
                    want = _grf_independent(raw, reg["axis"], reg["sign"], np.radians(reg["tilt_deg"] or 0.0), mass, leg)
                    got = np.array([tm_by_rec[rec][f"grf_{k}_{leg}_BW"][f] for k in ("vertical", "anterior", "lateral")])
                    worst = max(worst, float(np.max(np.abs(want - got))))
                res[f"{rec}:{leg}"] = {"checked": len(frames), "max_abs_diff_BW": worst, "pass": worst <= GRF_RECOMPUTE_TOL}
    return res


def r3_time_structure(path, frames_by_rec=None):
    """Per recording: rows, time axis, identity constants, held names versus all-missing columns, infinities."""
    problems, per = [], {}
    cols_all = tx.time_columns()
    for rec, cols, oids, sides in iter_recordings(path, ["time_s", *cols_all]):
        n = len(oids)
        t = cols["time_s"]
        if len(set(oids)) != 1 or set(sides) != {"none"}:
            problems.append(f"{rec}: not exactly one observation with reference_side none")
        if not np.allclose(t, np.arange(n) / tx.FRAME_HZ, atol=1e-9, rtol=0):
            problems.append(f"{rec}: time_s is not k / 100 s")
        for c in cols_all:
            if np.isinf(cols[c]).any():
                problems.append(f"{rec}: infinite value in {c}")
        per[rec] = {"rows": n, "all_missing": sorted(c for c in cols_all if not np.isfinite(cols[c]).any())}
    return per, problems


def held_matches(path, per):
    """held_signals names must equal the all-missing columns, per recording (reads only held_signals and the first row)."""
    import pyarrow.parquet as pq
    bad = []
    seen = set()
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for b in pf.iter_batches(batch_size=BATCH, columns=["source_recording_id", "held_signals"], use_threads=False):
            recs, held = b.column("source_recording_id").to_pylist(), b.column("held_signals").to_pylist()
            for r, h in zip(recs, held):
                if r in seen:
                    continue
                seen.add(r)
                names = sorted(json.loads(h or "{}"))
                if names != per[r]["all_missing"]:
                    bad.append({"recording": r, "held_not_missing": sorted(set(names) - set(per[r]["all_missing"])),
                                "missing_not_held": sorted(set(per[r]["all_missing"]) - set(names))})
    return bad


# ---------------------------------------------------------------- the job
def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    started = time.time()
    v5, v4 = ROOT / package_root(args.stage), ROOT / V4_PACKAGE
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks = []

    def add(cid, text, expected, observed):
        checks.append({"id": cid, "check": text, "expected": expected, "observed": observed, "pass": expected == observed})

    manifest = json.loads((v5 / "manifest.json").read_text())
    ok_files = {rel: (sha256_file(v5 / rel) == m["sha256"] and (v5 / rel).stat().st_size == m["bytes"]) for rel, m in manifest["files"].items()}
    on_disk = sorted(p.relative_to(v5).as_posix() for p in v5.rglob("*") if p.is_file() and p.name not in ("manifest.json", "manifest.sha256"))
    add("R1", "manifest hash, every file's hash and size, no file outside the manifest, tables = phase and time",
        {"bad_files": [], "unlisted": [], "tables": ["phase", "time"]},
        {"bad_files": sorted(k for k, v in ok_files.items() if not v), "unlisted": sorted(set(on_disk) - set(manifest["files"])),
         "tables": manifest["tables"]})
    add("R1b", "manifest.sha256 equals the manifest hash", f"{sha256_file(v5 / 'manifest.json')}  manifest.json",
        (v5 / "manifest.sha256").read_text().strip())
    keep = None
    if args.stage == "pilot":
        import pyarrow.parquet as pq
        keep = set()
        with open(v5 / "full_phase.parquet", "rb") as fh:
            for b in pq.ParquetFile(fh, buffer_size=0).iter_batches(batch_size=BATCH, columns=["source_recording_id"], use_threads=False):
                keep.update(b.column("source_recording_id").to_pylist())
    r2 = r2_phase_unchanged(v5, v4, keep)
    add("R2", "phase tables equal package v4 in every data column, full and filtered", {k: {} for k in r2},
        {k: v["differing_columns_batches"] for k, v in r2.items()})
    per, problems = r3_time_structure(v5 / "full_time.parquet")
    add("R3", "time table structure (one observation per recording, time_s = k/100, no infinity)", [], problems)
    add("R3b", "held_signals names equal the all-missing columns", [], held_matches(v5 / "full_time.parquet", per))
    recs = sorted(r.split("Streaming/")[1].replace("/Tread/", "/") if "Streaming/" in r else r for r in per)
    # R4/R6: stride windows of the v4 phase table
    phase_cols = sorted({f"{pc.format(w='ipsi')}" for pc, _k in PHASE_KIND} | {tx.PELVIS, tx.PELVIS_VEL, "source_start_time_s"})
    wanted = set(recs)
    r4 = {}
    verdicts = {}
    tm_for_force = {}
    keep_force = set(random.Random(SEED).sample(recs, min(3, len(recs))))
    time_iter = iter_recordings(v5 / "full_time.parquet", ["time_s", *tx.time_columns()])
    cur_t = next(time_iter, None)
    # one pass over the v4 phase table (sorted by recording) and the time table in lockstep
    for rec, ph, oids, sides in iter_recordings(v4 / "full_phase.parquet", phase_cols):
        short = rec.split("Streaming/")[1].replace("/Tread/", "/")
        if short not in wanted:
            continue
        while cur_t is not None and cur_t[0] != rec:
            cur_t = next(time_iter, None)
        if cur_t is None:
            raise ValueError(f"{rec}: time table recording missing")
        tm = cur_t[1]
        res = r4_compare_recording(short, ph, oids, sides, tm)
        r4[short] = res
        for k, s in res["series"].items():
            verdicts[(short, k)] = series_verdict(k, s)
        for k, s in res["cop"].items():
            leg = k.rsplit(":", 1)[1]
            x, v = tm[f"cop_anterior_{leg}_m"], tm[f"grf_vertical_{leg}_BW"]
            ok2 = np.isfinite(x[1:]) & np.isfinite(x[:-1]) & (v[1:] > 0.4) & (v[:-1] > 0.4)
            rough = float(np.median(np.abs(np.diff(x))[ok2])) if ok2.any() else None
            s["frame_to_frame_roughness_median_m"] = rough
            # A centre of pressure that is white-noise rough between frames cannot be sampled at two different instants (1 kHz
            # fractional frames in the phase table, frame samples here) to 1 mm: the expected median difference is of the order of
            # the frame-to-frame median step. Such a leg passes on the median alone when the median difference does not exceed
            # that roughness and the finite mismatch is within bounds; it is reported as noise limited (decision T05-H).
            noise_ok = (not s["pass"] and rough is not None and s.get("median_abs_m") is not None and s["median_abs_m"] <= rough
                        and s.get("finite_mismatch_fraction", 1) <= tx.TOLERANCES["cop_finite_mismatch_fraction_max"])
            if noise_ok:
                s["noise_limited"] = True
            verdicts[(short, k)] = bool(s["pass"] or noise_ok)
        tm_for_force[short] = {c: tm[c] for c in tm if c.startswith("grf_")}
        del ph
    add("R4", "time samples at every stride window reproduce the v4 phase values within the stated tolerances",
        [], sorted(f"{r}:{k}" for (r, k), ok in verdicts.items() if not ok))
    pooled = collections.defaultdict(lambda: [0, 0])
    for v in r4.values():
        for k, sr in v["series"].items():
            if k.startswith("velocity:") and k.split(":")[1] != tx.PELVIS_VEL:
                name = k.split(":")[1].replace("{w}", "ipsi")
                pooled[name][0] += sr["strides"]
                pooled[name][1] += sr["pass"]
    add("R4c", "limb segment velocity NRMS <= 0.03 in at least 99 percent of strides, pooled over recordings and legs",
        [], sorted(f"{n}: {b}/{a}" for n, (a, b) in pooled.items() if a and b / a < tx.TOLERANCES["velocity_strides_pass_fraction_min"]))
    add("R4b", "recordings compared equal the recordings of the package", recs, sorted(r4))
    add("R6", "source_start_time_s of every stride equals (a - 1) / 100 s", 0, sum(v["clock_mismatch_strides"] for v in r4.values()))
    src = {}
    if not args.no_source_check:
        src = source_check_recordings(sorted(keep_force), {r: tm_for_force[r] for r in keep_force})
    f5 = r5_force(tm_for_force, src)
    add("R5", "ground force sanity (no vertical force below -0.01 BW, components finite together)", [], f5["problems"])
    if src:
        add("R5b", "independent force recompute at seeded loaded frames", [], sorted(k for k, v in src.items() if v.get("pass") is False))
    # R7: filtered_time = full_time minus failed, exclusions
    import pyarrow.parquet as pq
    with open(v5 / "assessment.jsonl") as f:
        entries = [json.loads(x) for x in f if '"table": "time"' in x]
    failed = sorted(e["observation_id"] for e in entries if e["status"] == "failed")
    perf, _p = r3_time_structure(v5 / "filtered_time.parquet")
    obs_full = {rec: None for rec in per}
    kept = sorted(r for r in per if f"{r}:continuous:frames:1:{per[r]['rows']}" not in failed)
    add("R7", "filtered time recordings equal full time recordings minus the failed observations", kept, sorted(perf))
    with open(v5 / "exclusions.csv", newline="") as f:
        ex = list(csv.DictReader(f))
    add("R7b", "every failed time observation is listed once in exclusions.csv",
        failed, sorted(x["observation_id"] for x in ex if x["kind"] == "assessment_failed" and x["observation_id"] in set(failed)))
    result = {"task_id": TASK_ID, "stage": args.stage, "scientific_approval": False, "package": package_root(args.stage),
              "seed": SEED, "tolerances": tx.TOLERANCES, "checks": checks, "all_pass": all(c["pass"] for c in checks),
              "r4_per_recording": r4, "r5_force": f5, "r2_phase_vs_v4": r2,
              "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)),
                            "nice": os.nice(0), "wall_seconds": round(time.time() - started, 1)}}
    with open(out / "readback.json", "x") as f:
        json.dump(_clean(result), f, indent=1, allow_nan=False)
    print(json.dumps({"all_pass": result["all_pass"], "failed": [c["id"] for c in checks if not c["pass"]]}))
    return 0 if result["all_pass"] else 1


def _clean(o):
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


def build_spec(stage):
    out = out_root(stage)
    b = {k: sha256_file(ROOT / k) for k in (RUNNER, "contributor_tools/um21_time_export.py",
                                           f"{package_root(stage)}/manifest.json", f"{V4_PACKAGE}/manifest.json")}
    return {"job_id": f"{TASK_ID}-readback-{stage}-a7", "command": ["python3", RUNNER, "run", "--output-root", out, "--stage", stage],
            "cwd": str(ROOT), "output_root": out, "receipt_path": f"{AUDITS}/um21-t05-readback-{stage}-a7-launcher-receipt.json",
            "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816}, "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "disk_admission": [{"path": out, "min_free_mib": 1024}],
            "expected_output_names": ["readback.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage)
    validate_spec(spec)
    path = ROOT / f"{AUDITS}/um21-t05-readback-{stage}-a7-spec.json"
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--no-source-check", action="store_true", help="skip R5b (reads Streaming.mat)")
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.stage) or 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
