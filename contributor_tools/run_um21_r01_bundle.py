#!/usr/bin/env python3
"""UM21-R01: build the local UMich 2021 treadmill review bundle (bundle only; no documentation page).

Inputs are the T04 v2 sign-applied strides (enumerated from the ten launcher receipts), the single Q01
assessment (assessment.json, observations.jsonl, failures.jsonl), the T03 phase tables (task labels and source
clocks only) and the C03 ledger. Nothing is repaired except what Jose decided:
  D-UM21-C03-2 = C  AB07/i10 right-ankle stretch: re-express (c1 + 180 deg, wrapped) the strides that lie wholly
                    inside a ledger run, drop strides with sudden jumps, log every re-expressed sample.
  D-UM21-T04-2 = A  the 15 strides outside the 50-250 frame rule are left out with a listed reason.
Held power channels keep a column (all missing) and are named per observation in `held_signals`.

Writes only under a new output root. Run only through contributor_tools.guarded_launcher (one worker, nice 19,
768 MiB address space). One recording is resident at a time; pyarrow uses the system pool, buffer_size=0,
batches of 4096 rows, no threads, small row groups. scientific_approval is false.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
import argparse
import csv
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools import run_um21_q01_assessment as q01  # noqa: E402  (pure assessment functions, bound by hash)

TASK_ID = "UM21-R01"
RUNNER = "contributor_tools/run_um21_r01_bundle.py"
VERSION = "v2"  # v1 pilot stopped on a stride sharing one boundary frame with a run; its root is INVALID
Q01_ROOT = "converted_datasets/reconversion_v2/um21_q01_full_v2"
Q01_RECEIPT = "docs/quality/audits/um21-q01-full-launcher-receipt-v2.json"
T03_RECEIPTS = ("docs/quality/audits/um21-t03-batch0-launcher-receipt.json",
                "docs/quality/audits/um21-t03-batch1-launcher-receipt.json",
                "docs/quality/audits/um21-t03-v2-batch2-launcher-receipt.json",
                "docs/quality/audits/um21-t03-v2-batch3-launcher-receipt.json",
                "docs/quality/audits/um21-t03-v2-batch4-launcher-receipt.json",
                "docs/quality/audits/um21-t03-v2-batch5-launcher-receipt.json",
                "docs/quality/audits/um21-t03-v2-batch6-launcher-receipt.json")
C03_CENSUS = "docs/quality/audits/um21-c03-episode-census.json"
C03_CONVENTIONS = "docs/quality/audits/um21-c03-conventions.json"
PILOT_RECORDINGS = ("AB03/i10", "AB07/i10")  # AB03/i10: held power columns; AB07/i10: ankle stretch
STRIDE_RECORDING = "AB07/i10"
STRIDE_SIDE = "right"
N = 150
ROW_GROUP_ROWS = 3000
RSS_CAP_MIB = 400.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3

# T04 channel -> (published column, unit, family, status). Foot columns are not released: D-UM21-C01-1 covers
# thigh and shank only, and the foot angle carries the same ankle offset in the stretch.
COLUMNS = {
    "pelvis_tilt": ("pelvis_sagittal_angle_rad", "rad", "partly_checked"),
    "hip_angle": ("hip_flexion_angle_ipsi_rad", "rad", "checked"),
    "knee_angle": ("knee_flexion_angle_ipsi_rad", "rad", "checked"),
    "ankle_angle": ("ankle_dorsiflexion_angle_ipsi_rad", "rad", "offset_unverified"),
    "thigh_angle": ("thigh_sagittal_angle_ipsi_rad", "rad", "partly_checked"),
    "shank_angle": ("shank_sagittal_angle_ipsi_rad", "rad", "partly_checked"),
    "pelvis_tilt_velocity": ("pelvis_sagittal_velocity_rad_s", "rad/s", "unchecked"),
    "thigh_angle_velocity": ("thigh_sagittal_velocity_ipsi_rad_s", "rad/s", "unchecked"),
    "shank_angle_velocity": ("shank_sagittal_velocity_ipsi_rad_s", "rad/s", "unchecked"),
    "hip_moment": ("hip_flexion_moment_ipsi_Nm_kg", "N*m/kg", "unchecked"),
    "knee_moment": ("knee_flexion_moment_ipsi_Nm_kg", "N*m/kg", "unchecked"),
    "ankle_moment": ("ankle_dorsiflexion_moment_ipsi_Nm_kg", "N*m/kg", "unchecked"),
    "hip_power": ("hip_flexion_power_ipsi_W_kg", "W/kg", "unchecked"),
    "knee_power": ("knee_flexion_power_ipsi_W_kg", "W/kg", "unchecked"),
    "ankle_power": ("ankle_dorsiflexion_power_ipsi_W_kg", "W/kg", "unchecked"),
}
POWER_CHANNELS = ("hip_power", "knee_power", "ankle_power")
NOT_RELEASED = {"foot_angle": "not covered by D-UM21-C01-1 (thigh and shank only); carries the ankle offset",
                "foot_angle_velocity": "not covered by D-UM21-C01-1 (thigh and shank only)"}
HELD_TEXT = "held: sign unsettled"
IDENTITY = ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task",
            "task_id", "task_info", "phase_ipsi", "source_start_time_s", "source_end_time_s")
EXTRA = ("quality_status", "failed_limits", "held_signals", "ankle_reexpressed", "lineage_id", "assessment_id")
CONTRALATERAL = ("No contralateral columns: T04 publishes each stride's own leg only, so the opposite leg is a separate "
                 "observation with its own identity; its values are never copied into this one.")


# ------------------------------------------------------------------ pure rules (tested with synthetic data)
def wrap_deg(x):
    """Wrap degrees into [-180, 180)."""
    return (np.asarray(x, dtype=float) + 180.0) % 360.0 - 180.0


def reexpress_ankle_rad(x_rad):
    """Alternate-solution rule for the first Cardan component: c1 -> wrap(c1 + 180 deg). Input and output in radians;
    NaN stays NaN. Returns (new_rad, raw_deg, new_deg)."""
    raw = np.degrees(np.asarray(x_rad, dtype=float))
    new = wrap_deg(raw + 180.0)
    return np.radians(new), raw, new


def classify_stride(a, b, runs0, step0):
    """a, b: 0-based source frames of the stride (frames:a:b). runs0: [(first, last)] 0-based alternate-branch runs.
    step0: 0-based frames with a one-frame orientation step over 20 deg. Returns 'outside', 'inside_clean',
    'inside_jump' or 'partial' (overlaps a run by two or more frames without lying inside it: must not occur)."""
    inside = any(r0 <= a and b <= r1 for r0, r1 in runs0)
    # a stride whose end (or start) frame is the shared boundary frame of a run overlaps it by one frame only:
    # that is not a stretch stride (its other 149 samples lie outside); two or more shared frames without lying
    # inside is a partial overlap and must not occur.
    touches = any(min(b, r1) - max(a, r0) + 1 >= 2 for r0, r1 in runs0)
    if inside:
        return "inside_jump" if any(a <= s <= b for s in step0) else "inside_clean"
    return "partial" if touches else "outside"


def has_jump(deg, limit=q01.L2_JUMP_DEG):
    d = np.diff(np.asarray(deg, dtype=float))
    ok = np.isfinite(d)
    return bool(np.any(np.abs(d[ok]) > limit))


def exclusion_row(oid, recording, side, stage, code, reason, decision, in_full, in_filtered):
    return {"observation_id": oid, "recording": recording, "reference_side": side, "stage": stage, "reason_code": code,
            "reason": reason, "decision": decision, "in_full_variant": in_full, "in_filtered_variant": in_filtered}


def account(full_ids, filtered_ids, upstream_ids, exclusions):
    """Every observation named in the T04 tables or the unmapped list is accounted for exactly once:
    released in both variants, in full only (a listed filtered-stage exclusion), or in neither (listed)."""
    problems = []
    listed = {e["observation_id"]: e for e in exclusions}
    if len(listed) != len(exclusions):
        problems.append("an observation is listed twice in the exclusions")
    for oid in upstream_ids:
        in_f, in_filt, ex = oid in full_ids, oid in filtered_ids, listed.get(oid)
        if in_filt and not in_f:
            problems.append(f"{oid} is in filtered but not in full")
        elif in_f and in_filt and ex:
            problems.append(f"{oid} is released in both variants but listed as excluded")
        elif in_f and not in_filt and not (ex and ex["in_full_variant"] and not ex["in_filtered_variant"]):
            problems.append(f"{oid} is missing from filtered without a filtered-only exclusion")
        elif not in_f and not (ex and not ex["in_full_variant"] and not ex["in_filtered_variant"]):
            problems.append(f"{oid} is absent from both variants without a listed exclusion")
    extra = set(listed) - set(upstream_ids)
    if extra:
        problems.append(f"exclusions name observations outside the input set: {sorted(extra)[:3]}")
    return problems


def held_status(channel, decision):
    """Per-observation held text for a power channel (None when published)."""
    return HELD_TEXT if channel in POWER_CHANNELS and decision == "hold" else None


# ------------------------------------------------------------------ small helpers
sha256_file = q01.sha256_file
_peak_rss_mib = q01._peak_rss_mib
_mem_available = q01._mem_available


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_json_hashed(rel, expected=None):
    p = ROOT / rel
    h = sha256_file(p)
    if expected and h != expected:
        raise ValueError(f"{rel} differs from its expected hash")
    return json.loads(p.read_text()), h


def condition_of(recording_id):
    return recording_id.rsplit("/", 1)[-1]


def t03_phase_files():
    """{(recording): [(path, sha256)]} for components/ABxx/cond/phase.parquet from the seven T03 receipts."""
    import re
    out = {}
    for rel in T03_RECEIPTS:
        r = json.loads((ROOT / rel).read_text())
        if r.get("status") != "completed" or r.get("clean_success") is not True:
            raise ValueError(f"{rel} is not a clean completed run")
        base = Path(r["spec"]["output_root"])
        if (base / "INVALID_DO_NOT_USE.txt").exists():
            raise ValueError(f"{base} is marked INVALID")
        for o in r["outputs"]:
            m = re.fullmatch(r"components/(AB\d{2})/([di]\d+)/phase\.parquet", o["path"])
            if m:
                out.setdefault(f"{m.group(1)}/{m.group(2)}", []).append((str(base / o["path"]), o["sha256"]))
    return out


T03_META_COLUMNS = ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task",
                    "task_id", "task_info", "phase_ipsi", "source_start_time_s", "source_end_time_s")


def read_t03_meta(path, expected_sha256):
    """{observation_id: metadata} from a T03 phase table; metadata columns only, constant within an observation,
    phase grid exactly 150 inclusive samples."""
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"{path} differs from its T03 receipt hash")
    import pyarrow.parquet as pq
    grid = np.linspace(0.0, 100.0, N)
    meta, cur, buf = {}, None, []

    def flush():
        if cur is None:
            return
        rows = buf
        first = rows[0]
        for r in rows:
            for k in T03_META_COLUMNS:
                if k != "phase_ipsi" and r[k] != first[k] and not (r[k] != r[k] and first[k] != first[k]):
                    raise ValueError(f"{cur}: {k} changes inside the observation")
        ph = np.array([r["phase_ipsi"] for r in rows], dtype=float)
        if len(rows) != N or not np.allclose(ph, grid, atol=1e-9):
            raise ValueError(f"{cur}: phase grid is not the 150-sample inclusive 0-100 grid")
        meta[cur] = {k: first[k] for k in T03_META_COLUMNS if k != "phase_ipsi"}

    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for b in pf.iter_batches(batch_size=q01.READ_BATCH_ROWS, columns=list(T03_META_COLUMNS), use_threads=False):
            for r in b.to_pylist():
                if r["observation_id"] != cur:
                    flush()
                    if r["observation_id"] in meta:
                        raise ValueError(f"{r['observation_id']} appears in more than one run in {path}")
                    cur, buf = r["observation_id"], []
                buf.append(r)
        flush()
    return meta


# ------------------------------------------------------------------ one recording
def lineage(ledger_hashes):
    return sha256_bytes(json.dumps(ledger_hashes, sort_keys=True).encode())


def build_recording(rec, info, t03, q01_entries, c03, ctx):
    """Returns (observation dicts, rows dict for full, exclusions, reexpression log rows, amendments, summary)."""
    ids, sides, samples, data, unknown = q01.read_table(info["table"], info["table_sha256"])
    if sha256_file(info["map"]) != info["map_sha256"]:
        raise ValueError(f"{info['map']} differs from its T04 receipt hash")
    omap = json.loads(Path(info["map"]).read_text())
    runs, repeated = q01.group_observations(ids)
    problems = []
    if repeated:
        problems.append(f"ids appear in more than one run: {sorted(set(repeated))[:3]}")
    if unknown:
        problems.append(f"table has columns outside the T04 channel list: {unknown}")
    mapped = {o["observation_id"]: o for o in omap["observations"] if o["status"] == "mapped"}
    if {r[0] for r in runs} != set(mapped):
        problems.append("table ids differ from the mapped ids in the observation map")
    decisions = omap["recording_rule"]["decisions"]
    held = {ch for ch in POWER_CHANNELS if decisions[ch]["decision"] == "hold"}
    for ch in POWER_CHANNELS:
        if (ch in held) == (ch in data):
            problems.append(f"{ch}: held decision and column presence disagree")
    for ch in COLUMNS:
        if ch not in POWER_CHANNELS and ch not in data:
            problems.append(f"{ch} missing from the T04 table")
    t03_meta = t03
    units_data, _ = q01.convert_to_degrees(data)  # degrees only for assessment of amended strides
    obs_rows, exclusions, relog, amend = [], [], [], []
    n_rows = len(ids)
    out = {}
    for ch, (name, unit, _status) in COLUMNS.items():
        out[name] = np.array(data[ch], dtype=float) if ch in data else np.full(n_rows, np.nan)
    ankle_name = COLUMNS["ankle_angle"][0]
    keep_rows = np.ones(n_rows, dtype=bool)
    reexpressed_rows = np.zeros(n_rows, dtype=bool)
    ledger = {"recording": rec, "strides": []}
    for oid, a, b in runs:
        parsed = q01.parse_observation_id(oid)
        entry = q01_entries[oid]
        before = {"overall": entry["overall"], "failed_limits": entry["plausibility"]["failed_limits"],
                  "failed_channels": entry["plausibility"]["failed_channels"]}
        status = {"overall": entry["overall"], "failed_limits": list(before["failed_limits"]),
                  "failed_channels": list(before["failed_channels"]), "reexpressed": False}
        if rec == STRIDE_RECORDING and parsed["side"] == STRIDE_SIDE:
            kind = classify_stride(parsed["start"], parsed["end"], c03["runs0"], c03["step0"])
            if kind == "partial":
                problems.append(f"{oid}: touches an alternate-branch run without lying inside it")
            if kind in ("inside_clean", "inside_jump"):
                mults = {mapped[oid]["leg_channel_multipliers"]["ankle_angle"]["multiplier"]}
                new_rad, raw_deg, new_deg = reexpress_ankle_rad(data["ankle_angle"][a:b])
                data_jump = has_jump(new_deg)
                row = {"observation_id": oid, "census_class": kind, "ankle_multiplier": sorted(mults),
                       "data_jump_after_reexpression": data_jump, "in_ledger_pairs": [parsed["start"], parsed["end"]] in c03["inside_pairs"]}
                if kind == "inside_jump" or data_jump:
                    keep_rows[a:b] = False
                    why = ("census: one-frame orientation step inside the stride" if kind == "inside_jump" else "")
                    why += ("; " if why and data_jump else "") + ("a jump of more than 30 deg between adjacent samples remains after re-expression" if data_jump else "")
                    exclusions.append(exclusion_row(
                        oid, rec, parsed["side"], "release_membership", "c03_2_sudden_jump",
                        f"AB07/i10 right-ankle stretch stride dropped: {why}", "D-UM21-C03-2 = C", False, False))
                    row["result"] = "dropped"
                    ledger["strides"].append(row)
                    continue
                out[ankle_name][a:b] = new_rad
                reexpressed_rows[a:b] = True
                for i in range(N):
                    relog.append({"observation_id": oid, "sample_index": i, "phase_percent": round(i * 100.0 / (N - 1), 6),
                                  "raw_deg": float(raw_deg[i]), "reexpressed_deg": float(new_deg[i]),
                                  "rule": "c1 -> wrap(c1 + 180 deg)"})
                arrays = {c: (units_data[c][a:b] if c in units_data and c not in NOT_RELEASED else None) for c in q01.CHANNELS}
                arrays["ankle_angle"] = new_deg
                new_entry, _ = q01.assess_observation(oid, sides[a], samples[a:b], arrays, {c: "deg" if c in q01.L2_CHANNELS else q01.COLUMN_UNITS[c] for c in q01.CHANNELS})
                status = {"overall": new_entry["overall"], "failed_limits": new_entry["plausibility"]["failed_limits"],
                          "failed_channels": new_entry["plausibility"]["failed_channels"], "reexpressed": True}
                amend.append({"observation_id": oid, "recording": rec, "before": before,
                              "after": {"overall": new_entry["overall"], "failed_limits": new_entry["plausibility"]["failed_limits"],
                                        "failed_channels": new_entry["plausibility"]["failed_channels"],
                                        "ankle_state": new_entry["plausibility"]["channels"]["ankle_angle"]},
                              "reason": "right-ankle stretch re-expressed (D-UM21-C03-2 = C); same L1/L2 limits re-checked; "
                                        "foot_angle is not released and is not re-checked"})
                row["result"] = "re_expressed"
                ledger["strides"].append(row)
        mt = t03_meta.get(oid)
        if mt is None:
            problems.append(f"{oid}: not in the T03 table")
            continue
        if mt["reference_side"] != sides[a]:
            problems.append(f"{oid}: T03 side {mt['reference_side']!r} differs from T04 {sides[a]!r}")
        heldlist = sorted(COLUMNS[c][0] for c in POWER_CHANNELS if c in held)
        obs_rows.append({"oid": oid, "a": a, "b": b, "meta": mt, "overall": status["overall"],
                         "failed_limits": status["failed_limits"], "failed_channels": status["failed_channels"], "reexpressed": status["reexpressed"],
                         "held": heldlist, "kept": bool(keep_rows[a]), "recording": rec})
    summary = {"recording": rec, "table_sha256": info["table_sha256"], "map_sha256": info["map_sha256"],
               "t03_phase_sha256": omap["t03_phase_sha256"], "held_power_channels": sorted(held),
               "held_power_reasons": {ch: decisions[ch].get("decided_by") for ch in held},
               "record_problems": problems, "ledger": ledger if ledger["strides"] else None}
    return obs_rows, out, exclusions, relog, amend, summary, samples


def to_table(rec_rows, out, schema, ctx, upto_filtered=False):
    """Arrow table of the kept observations of one recording (full) or of the passing ones (filtered)."""
    import pyarrow as pa
    sel = [o for o in rec_rows if o["kept"] and (not upto_filtered or o["overall"] != "failed")]
    cols = {k: [] for k in schema.names}
    idx = []
    for o in sel:
        a, b, m = o["a"], o["b"], o["meta"]
        idx.extend(range(a, b))
        for k in ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id",
                  "task_info"):
            cols[k].extend([m[k]] * N)
        cols["phase_ipsi"].extend(np.linspace(0.0, 100.0, N).tolist())
        cols["source_start_time_s"].extend([m["source_start_time_s"]] * N)
        cols["source_end_time_s"].extend([m["source_end_time_s"]] * N)
        cols["quality_status"].extend([o["overall"]] * N)
        cols["failed_limits"].extend([json.dumps(o["failed_limits"])] * N)
        cols["held_signals"].extend([json.dumps({c: HELD_TEXT for c in o["held"]}) if o["held"] else "{}"] * N)
        cols["ankle_reexpressed"].extend([o["reexpressed"]] * N)
        cols["lineage_id"].extend([ctx["lineage_id"]] * N)
        cols["assessment_id"].extend([ctx["assessment_id"]] * N)
    idx = np.array(idx, dtype=int)
    for name, _u, _s in COLUMNS.values():
        cols[name] = out[name][idx] if len(idx) else np.array([], dtype=float)
    arrays = [pa.array(cols[f.name], type=f.type) for f in schema]
    return pa.Table.from_arrays(arrays, schema=schema), len(sel)


def make_schema():
    import pyarrow as pa
    fields = [pa.field("subject", pa.string()), pa.field("source_recording_id", pa.string()),
              pa.field("observation_id", pa.string()), pa.field("reference_side", pa.string()),
              pa.field("observation_type", pa.string()), pa.field("task", pa.string()), pa.field("task_id", pa.string()),
              pa.field("task_info", pa.string()), pa.field("phase_ipsi", pa.float64()),
              pa.field("source_start_time_s", pa.float64()), pa.field("source_end_time_s", pa.float64())]
    fields += [pa.field(name, pa.float64()) for name, _u, _s in COLUMNS.values()]
    fields += [pa.field("quality_status", pa.string()), pa.field("failed_limits", pa.string()),
               pa.field("held_signals", pa.string()), pa.field("ankle_reexpressed", pa.bool_()),
               pa.field("lineage_id", pa.string()), pa.field("assessment_id", pa.string())]
    return pa.schema(fields)


# ------------------------------------------------------------------ readback (what the index, preview and tests bind)
def readback(path, preview=False):
    """Stream one variant: row/observation counts, 150-grid check, finite counts per column, optional preview sums."""
    import pyarrow.parquet as pq
    schema_names = None
    rows = 0
    obs = {}
    finite = {}
    prev_id, prev_idx = None, None
    bad_grid = 0
    held_finite = 0
    groups = {}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        schema_names = pf.schema_arrow.names
        n_groups = pf.metadata.num_row_groups
        max_rg = max((pf.metadata.row_group(i).num_rows for i in range(n_groups)), default=0)
        for b in pf.iter_batches(batch_size=q01.READ_BATCH_ROWS, use_threads=False):
            oid = b.column("observation_id").to_pylist()
            ph = b.column("phase_ipsi").to_numpy(zero_copy_only=False)
            pidx = np.rint(ph * (N - 1) / 100.0).astype(int)
            if np.max(np.abs(ph - pidx * 100.0 / (N - 1))) > 1e-9:
                bad_grid += 1
            for i, o in enumerate(oid):
                if o == prev_id:
                    if pidx[i] != prev_idx + 1:
                        bad_grid += 1
                else:
                    if prev_id is not None and prev_idx != N - 1:
                        bad_grid += 1
                    if pidx[i] != 0 or o in obs:
                        bad_grid += 1
                prev_id, prev_idx = o, int(pidx[i])
                obs[o] = obs.get(o, 0) + 1
            rows += len(oid)
            for ch, (name, _u, _s) in COLUMNS.items():
                x = b.column(name).to_numpy(zero_copy_only=False)
                finite[name] = finite.get(name, 0) + int(np.isfinite(x).sum())
            hs = np.array(b.column("held_signals").to_pylist())
            for text in set(hs.tolist()):
                if text != "{}":
                    m = hs == text
                    for name in json.loads(text):
                        held_finite += int(np.isfinite(b.column(name).to_numpy(zero_copy_only=False)[m]).sum())
            if preview:
                rid = b.column("source_recording_id").to_pylist()
                tsk = b.column("task").to_pylist()
                sd = b.column("reference_side").to_pylist()
                keys = [(condition_of(r), t, s) for r, t, s in zip(rid, tsk, sd)]
                for key in set(keys):
                    sel = np.array([k == key for k in keys])
                    g = groups.setdefault(key, {"obs": set(), **{name: [np.zeros(N), np.zeros(N), np.zeros(N)]
                                                                 for name, _u, _s in COLUMNS.values()}})
                    g["obs"].update(o for o, k in zip(oid, keys) if k == key)
                    for ch, (name, _u, _s) in COLUMNS.items():
                        x = b.column(name).to_numpy(zero_copy_only=False)[sel]
                        ok = np.isfinite(x)
                        np.add.at(g[name][0], pidx[sel][ok], 1.0)
                        np.add.at(g[name][1], pidx[sel][ok], x[ok])
                        np.add.at(g[name][2], pidx[sel][ok], x[ok] ** 2)
        if prev_id is not None and prev_idx != N - 1:
            bad_grid += 1
    short = [o for o, c in obs.items() if c != N]
    return {"rows": rows, "observations": len(obs), "observation_ids": obs, "bad_grid_events": bad_grid + len(short),
            "finite_values_by_column": finite, "columns": schema_names, "row_groups": n_groups,
            "max_row_group_rows": max_rg, "preview_groups": groups,
            "finite_values_in_held_columns": held_finite}


def preview_json(groups, binding):
    out = []
    for key in sorted(groups):
        g = groups[key]
        entry = {"condition": key[0], "task": key[1], "reference_side": key[2], "observations": len(g["obs"]), "columns": {}}
        for _ch, (name, _u, _s) in COLUMNS.items():
            n, s1, s2 = g[name]
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = np.where(n > 0, s1 / np.maximum(n, 1), np.nan)
                var = np.where(n > 1, (s2 - n * mean ** 2) / np.maximum(n - 1, 1), np.nan)
            sd = np.sqrt(np.maximum(var, 0.0))
            entry["columns"][name] = {"n": [int(v) for v in n],
                                      "mean": [None if not np.isfinite(v) else round(float(v), 6) for v in mean],
                                      "sd": [None if not np.isfinite(v) else round(float(v), 6) for v in sd]}
        out.append(entry)
    return {"description": "mean and sample standard deviation per phase sample (150 points, 0 to 100 percent) of the "
                           "FILTERED variant, by treadmill condition, task and reference side; computed from the "
                           "written filtered.parquet. Held columns have n = 0. No smoothing.",
            "binding": binding, "groups": out}


# ------------------------------------------------------------------ job
def stage_recordings(stage):
    return list(PILOT_RECORDINGS) if stage == "pilot" else sorted(q01.t04_records())


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}",
            "spec": f"docs/quality/audits/um21-r01-{stage}-spec-{VERSION}.json",
            "output_root": f"converted_datasets/reconversion_v2/um21_r01_review_{stage}_{VERSION}" if stage == "pilot"
            else f"converted_datasets/reconversion_v2/um21_r01_review_{VERSION}",
            "receipt": f"docs/quality/audits/um21-r01-{stage}-launcher-receipt-{VERSION}.json"}


def bound_files():
    b = {RUNNER: None, "contributor_tools/run_um21_q01_assessment.py": None, Q01_RECEIPT: None, C03_CENSUS: None,
         C03_CONVENTIONS: None}
    for sub in q01.SUBJECTS:
        b[q01.T04_RECEIPT.format(sub)] = None
    for rel in T03_RECEIPTS:
        b[rel] = None
    for n in ("assessment.json", "observations.jsonl", "failures.jsonl"):
        b[f"{Q01_ROOT}/{n}"] = None
    return {k: sha256_file(ROOT / k) for k in b}


def build_spec(stage):
    p = stage_paths(stage)
    return {"job_id": p["job_id"],
            "command": ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
                        "--recordings", ",".join(stage_recordings(stage))],
            "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"], "bindings": bound_files(),
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["manifest.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path)}))


def load_c03():
    census, h1 = load_json_hashed(C03_CENSUS)
    conv, h2 = load_json_hashed(C03_CONVENTIONS)
    be = conv["ankle_episode_census"]["branch_episode"]
    fe = census["figure_episode"]
    if (fe["recording"], fe["side"], be["recording"], be["side"]) != ("AB07/i10", "R", "AB07/i10", "R"):
        raise ValueError("C03 ledger is not the AB07/i10 right ankle")
    return {"runs0": [(r0 - 1, r1 - 1) for r0, r1 in be["runs_1based"]],
            "step0": [s - 1 for s in be["orientation_step_over_20deg_frames_1based"]],
            "inside_pairs": fe["inside_pairs"], "sha256": {C03_CENSUS: h1, C03_CONVENTIONS: h2},
            "census_counts": {"inside_strides": fe["n_inside"], "outside_strides": fe["n_outside"],
                              "inside_without_step_over_20deg": be["inside_strides_without_orientation_step_over_20deg"]}}


def write_csv(path, rows, fields):
    with open(path, "x", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def run(args):
    import pyarrow.parquet as pq
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the pilot sample or the 44 T04 records")
    if _mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    started = time.time()
    records = q01.t04_records()
    t03_files = t03_phase_files()
    assessment, a_hash = load_json_hashed(f"{Q01_ROOT}/assessment.json")
    side = assessment["sidecar_files"]
    obs_path, fail_path = ROOT / Q01_ROOT / "observations.jsonl", ROOT / Q01_ROOT / "failures.jsonl"
    if sha256_file(obs_path) != side["observations.jsonl"]["sha256"] or sha256_file(fail_path) != side["failures.jsonl"]["sha256"]:
        raise ValueError("Q01 sidecar files differ from the hashes in assessment.json")
    q01_entries = {}
    with open(obs_path) as f:
        for line in f:
            e = json.loads(line)
            q01_entries[e["observation_id"]] = e
    if len(q01_entries) != 7547:
        raise ValueError("Q01 observations.jsonl does not hold 7,547 entries")
    unmapped_all = assessment["unmapped_observations"]
    c03 = load_c03()
    binding_hashes = bound_files()
    lineage_id = lineage({k: v for k, v in binding_hashes.items() if k != RUNNER})
    ctx = {"lineage_id": lineage_id, "assessment_id": a_hash}
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    schema = make_schema()
    full_w = pq.ParquetWriter(str(out / "full.parquet"), schema, compression="zstd")
    filt_w = pq.ParquetWriter(str(out / "filtered.parquet"), schema, compression="zstd")
    exclusions, relog, amend, summaries, upstream_ids, recs_index = [], [], [], [], [], []
    held_rows, ledgers, record_problems = [], [], {}
    try:
        for rec in recordings:
            if _mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            info = records[rec]
            omap = json.loads(Path(info["map"]).read_text())
            cands = [(p, h) for p, h in t03_files.get(rec, []) if h == omap["t03_phase_sha256"]]
            if len(cands) != 1:
                raise ValueError(f"{rec}: expected exactly one T03 phase table with hash {omap['t03_phase_sha256']}")
            t03 = read_t03_meta(*cands[0])
            rows, outarr, ex, rl, am, summ, _samples = build_recording(rec, info, t03, q01_entries, c03, ctx)
            exclusions.extend(ex)
            relog.extend(rl)
            amend.extend(am)
            summ["t03_phase_path"] = cands[0][0]
            for o in omap["observations"]:
                upstream_ids.append(o["observation_id"])
            for o in omap["observations"]:
                if o["status"] != "mapped":
                    exclusions.append(exclusion_row(o["observation_id"], rec, o["leg"], "upstream_not_released",
                                                    "t04_2_outside_stride_rule", o["reason"], "D-UM21-T04-2 = A", False, False))
            for ch in summ["held_power_channels"]:
                held_rows.append({"recording": rec, "column": COLUMNS[ch][0], "status": HELD_TEXT,
                                  "reason": summ["held_power_reasons"][ch], "observations": len(rows)})
            if summ["ledger"]:
                ledgers.append(summ["ledger"])
            summaries.append(summ)
            if summ["record_problems"]:
                record_problems[rec] = summ["record_problems"]
            tf, n_full = to_table(rows, outarr, schema, ctx, upto_filtered=False)
            tp, n_filt = to_table(rows, outarr, schema, ctx, upto_filtered=True)
            full_w.write_table(tf, row_group_size=ROW_GROUP_ROWS)
            filt_w.write_table(tp, row_group_size=ROW_GROUP_ROWS)
            for o in rows:
                if o["kept"] and o["overall"] == "failed":
                    exclusions.append(exclusion_row(
                        o["oid"], rec, o["meta"]["reference_side"], "filtered_variant_only", "q01_limit_failed",
                        "failed coarse limit(s) " + ", ".join(sorted(o["failed_limits"])) + " on " +
                        ", ".join(o["failed_channels"]) + " (Q01 assessment)",
                        "D-UM21-Q01-1 = B", True, False))
            recs_index.append({"recording": rec, "subject": rec.split("/")[0], "condition": condition_of(rec),
                               "t04_mapped_observations": len(rows) + sum(1 for e in ex if e["stage"] == "release_membership"),
                               "full": n_full, "filtered": n_filt,
                               "unmapped": sum(1 for o in omap["observations"] if o["status"] != "mapped"),
                               "dropped_c03_2": sum(1 for e in ex if e["reason_code"] == "c03_2_sudden_jump"),
                               "held_power_columns": [COLUMNS[c][0] for c in summ["held_power_channels"]]})
            print(f"{rec}: full {n_full} filtered {n_filt}, peak RSS {_peak_rss_mib():.0f} MiB", flush=True)
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    finally:
        full_w.close()
        filt_w.close()
    return finish(args, out, schema, recordings, exclusions, relog, amend, summaries, upstream_ids, recs_index,
                  held_rows, ledgers, record_problems, assessment, a_hash, binding_hashes, lineage_id, c03, unmapped_all,
                  q01_entries, started)


def finish(args, out, schema, recordings, exclusions, relog, amend, summaries, upstream_ids, recs_index, held_rows,
           ledgers, record_problems, assessment, a_hash, binding_hashes, lineage_id, c03, unmapped_all, q01_entries, started):
    write_csv(out / "exclusions.csv", exclusions,
              ["observation_id", "recording", "reference_side", "stage", "reason_code", "reason", "decision",
               "in_full_variant", "in_filtered_variant"])
    write_csv(out / "ankle_reexpression_log.csv", relog,
              ["observation_id", "sample_index", "phase_percent", "raw_deg", "reexpressed_deg", "rule"])
    with open(out / "assessment_amendments.jsonl", "x") as f:
        for a in amend:
            f.write(json.dumps(a) + "\n")
    write_csv(out / "held_signals.csv", held_rows, ["recording", "column", "status", "reason", "observations"])
    full_sha, filt_sha = sha256_file(out / "full.parquet"), sha256_file(out / "filtered.parquet")
    rb_full = readback(out / "full.parquet")
    rb_filt = readback(out / "filtered.parquet", preview=True)
    full_ids, filt_ids = set(rb_full["observation_ids"]), set(rb_filt["observation_ids"])
    problems = account(full_ids, filt_ids, upstream_ids, exclusions)
    in_pilot = len(recordings) != 44
    # expected counts
    exp = {}
    if not in_pilot:
        exp = {"t04_observations_in_tables": 7547, "unmapped": 15, "full": 7545, "filtered": 7544}
    counts = {"upstream_observations": len(upstream_ids), "full": len(full_ids), "filtered": len(filt_ids),
              "full_rows": rb_full["rows"], "filtered_rows": rb_filt["rows"],
              "exclusions_total": len(exclusions),
              "exclusions_by_reason_code": {}, "exclusions_by_stage": {}}
    for e in exclusions:
        counts["exclusions_by_reason_code"][e["reason_code"]] = counts["exclusions_by_reason_code"].get(e["reason_code"], 0) + 1
        counts["exclusions_by_stage"][e["stage"]] = counts["exclusions_by_stage"].get(e["stage"], 0) + 1
    relog_ids = {r["observation_id"] for r in relog}
    after_ok = [a for a in amend if a["after"]["overall"] == "no_failure_found"]
    binding = {"full_sha256": full_sha, "filtered_sha256": filt_sha,
               "exclusions_sha256": sha256_file(out / "exclusions.csv"),
               "counts": {k: counts[k] for k in ("upstream_observations", "full", "filtered", "full_rows", "filtered_rows")},
               "lineage_id": lineage_id, "assessment_id": a_hash,
               "assessment_files": {n: assessment["sidecar_files"][n]["sha256"] for n in ("observations.jsonl", "failures.jsonl")},
               "amendments_sha256": sha256_file(out / "assessment_amendments.jsonl"),
               "reexpression_log_sha256": sha256_file(out / "ankle_reexpression_log.csv")}
    checks = [
        ("T1", "every observation has exactly 150 rows on the inclusive 0-100 phase grid, rows ordered, in both variants",
         0, rb_full["bad_grid_events"] + rb_filt["bad_grid_events"]),
        ("T2", "full and filtered write the same column list", rb_full["columns"], rb_filt["columns"]),
        ("T3", "every input observation is released in both variants, in full only, or listed as left out (no gaps)", [], problems),
        ("T4", "no problems were recorded while reading any recording", {}, record_problems),
        ("T5", "every filtered observation is also in full", [], sorted(filt_ids - full_ids)),
        ("T6", "full minus filtered equals the filtered-variant-only exclusions",
         counts["exclusions_by_stage"].get("filtered_variant_only", 0), len(full_ids) - len(filt_ids)),
        ("T7", "every re-expressed stride is logged for all 150 samples", len(amend) * N, len(relog)),
        ("T8", "held power columns hold no finite value where an observation names them held", 0,
         rb_full["finite_values_in_held_columns"] + rb_filt["finite_values_in_held_columns"]),
    ]
    if exp:
        n_unm = counts["exclusions_by_reason_code"].get("t04_2_outside_stride_rule", 0)
        seen = {"t04_observations_in_tables": len(upstream_ids) - n_unm, "unmapped": n_unm,
                "full": len(full_ids), "filtered": len(filt_ids)}
        checks += [("T9", f"{k} equals the expected total", v, seen[k]) for k, v in exp.items()]
    test_rows = [{"id": i, "check": d, "expected": e, "observed": o, "pass": e == o} for i, d, e, o in checks]
    test_summary = {"scientific_approval": False, "binding": binding,
                    "checks": test_rows, "all_pass": all(t["pass"] for t in test_rows),
                    "note": "Computed by the bundle runner from the written files. The pytest results for the runner's rules are in "
                            "the UM21-R01 handoff."}
    index = {"release": f"um21-treadmill-review-{VERSION}", "scientific_approval": False, "stage": args.stage,
             "binding": binding, "recordings": recs_index,
             "columns": [{"column": name, "status": status, "unit": unit, "finite_values_full": rb_full["finite_values_by_column"][name],
                          "finite_values_filtered": rb_filt["finite_values_by_column"][name]}
                         for _ch, (name, unit, status) in COLUMNS.items()]}
    preview = preview_json(rb_filt["preview_groups"], binding)
    for name, obj in (("dataset_index.json", index), ("phase_preview.json", preview), ("test_summary.json", test_summary)):
        with open(out / name, "x") as f:
            json.dump(obj, f, indent=1, allow_nan=False)
    manifest = {"schema": "locohub.um21_review_bundle/1", "task_id": TASK_ID, "stage": args.stage, "scientific_approval": False,
                "local_only": True, "no_upload_no_publish": True,
                "binding": binding, "counts": counts,
                "column_status": {name: {"status": status, "unit": unit, "t04_channel": ch,
                                        "finite_values_full": rb_full["finite_values_by_column"][name],
                                        "finite_values_filtered": rb_filt["finite_values_by_column"][name]}
                                  for ch, (name, unit, status) in COLUMNS.items()},
                "columns_not_released": NOT_RELEASED, "held_status_text": HELD_TEXT, "contralateral": CONTRALATERAL,
                "identity_columns": list(IDENTITY), "extra_columns": list(EXTRA),
                "input_bindings_sha256": binding_hashes, "c03_ledger": {**c03["census_counts"],
                                                                         "runs_0based": c03["runs0"], "step_frames_0based": c03["step0"]},
                "c03_ledger_per_stride": ledgers, "amendments": len(amend),
                "amendments_after_recheck_no_failure": len(after_ok),
                "t03_phase_tables": {s["recording"]: {"path": s["t03_phase_path"], "sha256": s["t03_phase_sha256"]} for s in summaries},
                "files": {}, "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)),
                                           "nice": os.nice(0), "wall_seconds": round(time.time() - started, 1),
                                           "row_groups_full": rb_full["row_groups"], "max_row_group_rows": rb_full["max_row_group_rows"]}}
    with open(out / "README.md", "x") as f:
        f.write("# UMich 2021 treadmill review bundle (local, not published)\n\n"
                "Review copy only; no scientific approval. `full.parquet` keeps every released stride and records its "
                "quality status; `filtered.parquet` leaves out strides that failed a coarse limit. `exclusions.csv` lists "
                "every stride left out of either file with its reason. Held power columns are present but missing, with "
                "`held_signals` naming them. Ankle angle zero offset is unverified. See `manifest.json` for hashes.\n")
    for n in sorted(os.listdir(out)):
        if n not in ("manifest.json", "manifest.sha256"):
            manifest["files"][n] = {"sha256": sha256_file(out / n), "bytes": (out / n).stat().st_size}
    with open(out / "manifest.json", "x") as f:
        json.dump(manifest, f, indent=1, allow_nan=False)
    with open(out / "manifest.sha256", "x") as f:
        f.write(f"{sha256_file(out / 'manifest.json')}  manifest.json\n")
    for n in os.listdir(out):
        try:
            os.chmod(out / n, 0o444)
        except OSError:
            pass
    print(json.dumps({"counts": {k: counts[k] for k in ("upstream_observations", "full", "filtered", "exclusions_total")},
                      "by_reason": counts["exclusions_by_reason_code"], "tests_pass": test_summary["all_pass"],
                      "peak_rss_mib": manifest["resources"]["peak_rss_mib"]}))
    return 0 if (test_summary["all_pass"] and not problems and not record_problems) else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--recordings", required=True)
    args = p.parse_args(argv)
    if args.step == "plan":
        return plan(args.stage)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
