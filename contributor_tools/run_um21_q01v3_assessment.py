#!/usr/bin/env python3
"""UM21-Q01 v3: compose the v3 observation table from the verified S02 v7 outputs and assess it (structured assessment).

Inputs (all read-only, hash-checked against the clean launcher receipts):
  * the v2 review bundle (um21_r01_review_v2/full.parquet): identity and task columns, source clocks, joint moments and
    joint powers (carried unchanged; held powers stay held);
  * the S02 v7 components (um21_s02_frame_full_v7): marker-based segment and joint angles, velocities, and the foot-frame
    centre of pressure ("estimated plate position"; held legs are all missing), plus the S02 ledger and summary;
  * Streaming.mat markers (read one recording at a time) for the per-frame checks below.

Decisions applied: D-UM21-Q01-1 = B (structure plus coarse physical limits, blatant errors only); D-UM21-S02-1 = A (the
centre of pressure is published labelled "estimated plate position", gated on hold-out ankle-moment r >= 0.95 and toe-off end
within 4 cm in 95 percent of strides); D-UM21-S02-2 = A (each leg is judged and published on its own). Held-back data stays
pending as it is (the i10 recordings of AB01, AB02, AB03, AB04/d10 and AB10/d5): no further investigation here.

Layers
  structural  S1 150 contiguous samples 0..149 on the inclusive phase grid, S2 id parses and its side equals reference_side,
              S3 unique ids (checked per recording by the builder), L4 non-finite samples reported as missing (never a
              pass), L3 stride time (reported only).
  plausibility
    L1  hip, knee and ankle angle outside [-50, 150], [-30, 165], [-80, 50] degrees (published 150-sample values).
    L2  change of more than 30 degrees between adjacent samples, evaluated ONLY on the 100 Hz frame series of the markers
        (pelvis, thigh, shank, foot, hip, knee, ankle) inside the stride window and mapped to the observation. GT23 showed that
        the same limit on a resampled phase grid is not meaningful, so the published 150 samples are not used for L2.
    L5  foot-frame centre of pressure beyond 0.5 m (anterior) or 0.3 m (vertical, lateral) of the foot origin (as in GT23).
    P1  per-frame plane-glitch rule (chosen BEFORE the results were looked at, on the verifier's suggestion): in any frame in
        which a leg's own side-view plane is more than 60 degrees away from the walking direction, that leg's angles are
        held. Published columns that depend on the leg plane are set missing for every stride whose window contains such a
        frame: thigh, shank, foot, hip, knee and ankle angle, thigh, shank and foot velocity, and the three centre-of-pressure
        columns (the foot frame is built in the same plane; that last item is an agent choice, logged). The pelvis does not
        use the leg plane and is kept. Held columns are named in held_signals with the reason; they are never a pass.
A column without a limit is "unchecked". Missing or held columns are "unchecked_all_missing". Angle columns are radians and are
converted with numpy.degrees; a column whose unit suffix is unknown refuses the run. scientific_approval is false.
Run only through contributor_tools.guarded_launcher (one worker, nice 19, 768 MiB address space).
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # must precede pyarrow (768 MiB address-space cap)
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from contributor_tools import run_um21_s02_frame as s02  # noqa: E402  (geometry functions, bound by hash)

TASK_ID = "UM21-Q01"
RUNNER = "contributor_tools/run_um21_q01v3_assessment.py"
VERSION = "v3"
AUDITS = "docs/quality/audits"
S02_ROOT = "converted_datasets/reconversion_v2/um21_s02_frame_full_v7"
S02_RECEIPT = f"{AUDITS}/um21-s02-full-launcher-receipt-v7.json"
S02_VERIFY = "docs/maintainers/handoffs/UM21-S02-verify.json"
V2_ROOT = s02.V2_ROOT
V2_FULL = s02.V2_FULL
V2_EXCLUSIONS = f"{V2_ROOT}/exclusions.csv"
# clean, both legs published; both legs held plus held powers; reversed heading; one leg held and one published; the stride
# whose window contains plane-glitch frames; a recording held by the 95 percent plate-assignment rule
PILOT_RECORDINGS = ("AB01/i0", "AB03/i10", "AB04/i0", "AB07/d10", "AB08/i0", "AB10/d5")
PENDING_BY_RULING = frozenset({"AB01/i10", "AB02/i10", "AB03/i10", "AB04/d10", "AB10/d5"})
N = 150
RSS_CAP_MIB = 400.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
FRAME_HZ = 100.0
FAILED = "failed"
NOT_FAILED = "no_failure_found"
ID_RE = re.compile(r"^um21:Streaming/(AB\d{2})/Tread/([di]\d+):(right|left):frames:(\d+):(\d+)$")

# ---- limits (L1, L2 are the values of UM21-Q01 v2 and GT23-Q01; the test file asserts equality with the earlier module)
L1_BOUNDS_DEG = {"hip_flexion_angle_ipsi_rad": (-50.0, 150.0), "knee_flexion_angle_ipsi_rad": (-30.0, 165.0),
                 "ankle_dorsiflexion_angle_ipsi_rad": (-80.0, 50.0)}
L2_JUMP_DEG = 30.0
L3_RANGE_S = (0.4, 2.5)
L5_BOUNDS_M = {"cop_anterior_ipsi_m": (-0.5, 0.5), "cop_vertical_ipsi_m": (-0.3, 0.3), "cop_lateral_ipsi_m": (-0.3, 0.3)}
PLANE_GLITCH_DEG = 60.0

S02_TO_PUBLISHED = {
    "pelvis_tilt": "pelvis_sagittal_angle_rad", "hip_angle": "hip_flexion_angle_ipsi_rad",
    "knee_angle": "knee_flexion_angle_ipsi_rad", "ankle_angle": "ankle_dorsiflexion_angle_ipsi_rad",
    "thigh_angle": "thigh_sagittal_angle_ipsi_rad", "shank_angle": "shank_sagittal_angle_ipsi_rad",
    "foot_angle": "foot_sagittal_angle_ipsi_rad", "pelvis_tilt_velocity": "pelvis_sagittal_velocity_rad_s",
    "thigh_angle_velocity": "thigh_sagittal_velocity_ipsi_rad_s", "shank_angle_velocity": "shank_sagittal_velocity_ipsi_rad_s",
    "foot_angle_velocity": "foot_sagittal_velocity_ipsi_rad_s", "cop_anterior": "cop_anterior_ipsi_m",
    "cop_vertical": "cop_vertical_ipsi_m", "cop_lateral": "cop_lateral_ipsi_m"}
V2_CARRIED = ("hip_flexion_moment_ipsi_Nm_kg", "knee_flexion_moment_ipsi_Nm_kg", "ankle_dorsiflexion_moment_ipsi_Nm_kg",
              "hip_flexion_power_ipsi_W_kg", "knee_flexion_power_ipsi_W_kg", "ankle_dorsiflexion_power_ipsi_W_kg")
IDENTITY_STR = ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id",
                "task_info")
IDENTITY_NUM = ("phase_ipsi", "source_start_time_s", "source_end_time_s")
# published data columns in table order
DATA_COLUMNS = ("pelvis_sagittal_angle_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
                "ankle_dorsiflexion_angle_ipsi_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
                "foot_sagittal_angle_ipsi_rad", "pelvis_sagittal_velocity_rad_s", "thigh_sagittal_velocity_ipsi_rad_s",
                "shank_sagittal_velocity_ipsi_rad_s", "foot_sagittal_velocity_ipsi_rad_s", *V2_CARRIED,
                "cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m")
ANGLE_COLUMNS = tuple(c for c in DATA_COLUMNS if c.endswith("_angle_rad") or c.endswith("_angle_ipsi_rad"))
COP_COLUMNS = ("cop_anterior_ipsi_m", "cop_vertical_ipsi_m", "cop_lateral_ipsi_m")
LEG_PLANE_COLUMNS = ("hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad", "ankle_dorsiflexion_angle_ipsi_rad",
                     "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad", "foot_sagittal_angle_ipsi_rad",
                     "thigh_sagittal_velocity_ipsi_rad_s", "shank_sagittal_velocity_ipsi_rad_s",
                     "foot_sagittal_velocity_ipsi_rad_s", *COP_COLUMNS)
FRAME_SERIES = ("pelvis_sagittal_angle_rad", "thigh_sagittal_angle_ipsi_rad", "shank_sagittal_angle_ipsi_rad",
                "foot_sagittal_angle_ipsi_rad", "hip_flexion_angle_ipsi_rad", "knee_flexion_angle_ipsi_rad",
                "ankle_dorsiflexion_angle_ipsi_rad")
UNIT_SUFFIXES = (("_rad_s", "rad/s"), ("_rad", "rad"), ("_Nm_kg", "N*m/kg"), ("_W_kg", "W/kg"), ("_m", "m"))
COP_LABEL = s02.COP_LABEL
COP_REASON_PREFIX = "foot-frame centre of pressure held: "
GAP_REASON = ("column missing for this stride in the S02 v7 table: a marker it needs is not visible in the stride window, "
              "or the pelvis differs from the marker pelvis by more than 1 degree (S02 ledger columns_all_missing)")
GLITCH_REASON = (f"leg plane more than {PLANE_GLITCH_DEG:g} degrees from the walking direction in at least one frame of "
                 "the stride window (rule P1)")

PROFILE = {
    "profile_id": "um21_q01_v3_coarse_limits",
    "decision": "D-UM21-Q01-1 = B: structure plus coarse physical limits; blatant errors only",
    "review_status": "draft_limits_unreviewed_scientific_approval_false",
    "population": "able-bodied adults (UMich 2021 treadmill walking: level, incline, decline)",
    "no_tuning": "Limits were written before any v7 data were read and are not changed to reach a pass rate.",
    "limits": {
        "L1": {"bounds_deg": dict(L1_BOUNDS_DEG), "layer": "plausibility",
               "evidence": "textbook end of range plus a 30 degree margin chosen here (carried from UM21-Q01 v2; the textbook "
                           "values were never confirmed against a primary text)"},
        "L2": {"threshold_deg": L2_JUMP_DEG, "layer": "plausibility", "columns": list(FRAME_SERIES),
               "evaluated_on": "100 Hz marker frame series inside each stride window, mapped to the observation; not on the "
                               "resampled 150-sample values (GT23 lesson)"},
        "L5": {"bounds_m": dict(L5_BOUNDS_M), "layer": "plausibility",
               "evidence": "a foot is about 0.25 m long and 0.1 m wide (as in GT23-Q01); chosen, not fitted"},
        "L4": {"layer": "structural", "what": "non-finite samples are reported as missing and are never a pass"},
        "L3": {"layer": "structural", "range_s": list(L3_RANGE_S), "what": "stride time; reported, never a filter"},
        "P1": {"layer": "plausibility_hold", "plane_deviation_deg": PLANE_GLITCH_DEG,
               "what": "per-frame plane-glitch rule: frames whose leg plane is more than 60 degrees from the walking direction "
                       "hold that leg's plane-dependent columns for the stride (a hold, not a failure)",
               "held_columns": list(LEG_PLANE_COLUMNS)},
    },
    "unchecked": ["velocities", "moments", "powers", "range of pelvis, thigh, shank and foot angles (L2 only)"],
}


class UnitError(ValueError):
    pass


def unit_of(column):
    for suffix, unit in UNIT_SUFFIXES:
        if column.endswith(suffix):
            return unit
    raise UnitError(f"unknown unit for column {column!r}; refusing to assess")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _mem_available():
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    return 0


# ---------------------------------------------------------------- pure rules (tested with synthetic data)
def parse_id(oid):
    m = ID_RE.match(oid or "")
    if not m:
        return None
    sub, cond, side, a, b = m.groups()
    return {"subject": sub, "condition": cond, "side": side, "a": int(a), "b": int(b)}


def plane_deviation_deg(plane_forward, walking_forward):
    """Angle in degrees between each frame's leg-plane forward direction (n, 3) and the walking direction (3,). NaN where
    the plane is undefined."""
    c = np.sum(np.asarray(plane_forward, float) * np.asarray(walking_forward, float), axis=1)
    return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))


def glitch_mask(deviation_deg, limit=PLANE_GLITCH_DEG):
    """True in frames whose finite plane deviation is more than the limit."""
    d = np.asarray(deviation_deg, float)
    with np.errstate(invalid="ignore"):
        return np.isfinite(d) & (d > limit)


def window_has_glitch(mask, a, b):
    """Frames a..b are 1-based inclusive (the id's frame window)."""
    return bool(np.any(mask[a - 1:b]))


def frame_jump_flags(series_rad, glitched, limit_deg=L2_JUMP_DEG):
    """Per frame f (f >= 1): True when |series[f] - series[f-1]| exceeds limit_deg, both frames finite and neither a
    glitch frame. Index 0 is False."""
    x = np.degrees(np.asarray(series_rad, float))
    d = np.zeros(len(x), bool)
    if len(x) > 1:
        with np.errstate(invalid="ignore"):
            ok = np.isfinite(x[1:]) & np.isfinite(x[:-1]) & ~glitched[1:] & ~glitched[:-1]
            d[1:] = ok & (np.abs(np.diff(x)) > limit_deg)
    return d


def stride_jump_pairs(flags, a, b):
    """0-based frame indices f of jump pairs (f-1, f) inside the 1-based inclusive window a..b (frames a-1 .. b-1)."""
    return [int(i) + a for i in np.flatnonzero(flags[a:b])]


def limit_failures(column, x_published):
    """[(limit, sample_index, value, reason)] for L1 and L5 on one 150-sample published column. Non-finite samples never
    fail and never count as evidence of passing."""
    x = np.asarray(x_published, float)
    out = []
    fin = np.isfinite(x)
    if column in L1_BOUNDS_DEG:
        lo, hi = L1_BOUNDS_DEG[column]
        v = np.degrees(x)
        for i in np.flatnonzero(fin & ((v < lo) | (v > hi))):
            out.append(("L1", int(i), float(v[i]), f"{column} {v[i]:.1f} deg outside [{lo:g}, {hi:g}] deg"))
    if column in L5_BOUNDS_M:
        lo, hi = L5_BOUNDS_M[column]
        for i in np.flatnonzero(fin & ((x < lo) | (x > hi))):
            out.append(("L5", int(i), float(x[i]), f"{column} {x[i]:.3f} m outside [{lo:g}, {hi:g}] m"))
    return out


def channel_state(column, x, held, failed, l2_checked):
    """State of one column of one observation."""
    if held or not np.isfinite(np.asarray(x, float)).any():
        return "unchecked_all_missing"
    has_limit = column in L1_BOUNDS_DEG or column in L5_BOUNDS_M or (column in FRAME_SERIES and l2_checked)
    if not has_limit:
        return "unchecked"
    if failed:
        return "fail"
    return "pass" if (column in L1_BOUNDS_DEG or column in L5_BOUNDS_M) else "pass_jump_only"


def apply_plane_hold(arrays, held):
    """Rule P1: set the plane-dependent columns missing and name them held. Mutates arrays and held."""
    for c in LEG_PLANE_COLUMNS:
        arrays[c] = np.full(N, np.nan)
        held[c] = GLITCH_REASON if c not in held else held[c] + "; " + GLITCH_REASON


def assess_observation(meta, arrays, held, jump_frames, glitch_in_window, plane_deviation_max, cop_status, pending_ruling):
    """One observation. meta: identity strings and the sample indices ('phase'); arrays: published column -> 150 values (after
    holds); held: column -> reason; jump_frames: published frame series -> 0-based frames with an L2 jump. Returns (entry,
    failure_rows)."""
    oid, side = meta["observation_id"], meta["reference_side"]
    parsed = parse_id(oid)
    problems = []
    if list(meta["phase"]) != list(range(N)):
        problems.append("S1 samples are not 0..149 contiguous")
    if parsed is None:
        problems.append("S2 id does not parse")
    elif parsed["side"] != side:
        problems.append(f"S2 reference_side {side!r} differs from the id side {parsed['side']!r}")
    for c, x in arrays.items():
        unit_of(c)
        if len(x) != N:
            problems.append(f"S1 column {c} has {len(x)} samples")
    st = (parsed["b"] - parsed["a"]) / FRAME_HZ if parsed else None
    fails, failed_samples, states, missing = [], {}, {}, {}
    for c in DATA_COLUMNS:
        x = np.asarray(arrays[c], float)
        bad = np.flatnonzero(~np.isfinite(x))
        if len(bad):
            missing[c] = {"missing": int(len(bad)), "first": int(bad[0]), "last": int(bad[-1])}
        found = []
        for lim, i, v, why in limit_failures(c, x):
            found.append({"limit": lim, "sample_index": i, "frame": None, "value": v, "reason": why})
        l2_checked = c in FRAME_SERIES and c not in held and bool(np.isfinite(x).any())
        if l2_checked:
            for fr in jump_frames.get(c, []):
                found.append({"limit": "L2", "sample_index": None, "frame": int(fr), "value": None,
                              "reason": f"{c} changes more than {L2_JUMP_DEG:g} deg between 100 Hz frames {fr - 1} and {fr}"})
        for f in found:
            fails.append({"observation_id": oid, "reference_side": side, "table": "phase", "channel": c, **f})
            failed_samples.setdefault(c, {}).setdefault(f["limit"], 0)
            failed_samples[c][f["limit"]] += 1
        states[c] = channel_state(c, x, c in held, bool(found), l2_checked)
    limits = sorted({x["limit"] for x in fails})
    status = FAILED if (limits or problems) else NOT_FAILED
    channel_states = {}
    for c, s in states.items():
        channel_states.setdefault(s, []).append(c)
    lim_flags = ["moments_powers_from_v2", "knee_marker_labels_swapped"]
    if cop_status == "published":
        lim_flags.append("cop_estimated_plate_position")
    if any(held.get(c, "").startswith(COP_REASON_PREFIX) for c in COP_COLUMNS):
        lim_flags.append("cop_held_leg")
        if pending_ruling:
            lim_flags.append("cop_held_pending_ruling")
    if any(c.endswith("_W_kg") for c in held):
        lim_flags.append("powers_held_sign_unsettled")
    if any(c in missing and missing[c]["missing"] == N for c in ANGLE_COLUMNS):
        lim_flags.append("angle_columns_missing_in_stride")
    if glitch_in_window:
        lim_flags.append("plane_glitch_hold")
    entry = {
        "observation_id": oid, "reference_side": side, "table": "phase", "observation_type": meta["observation_type"],
        "subject": meta["subject"], "source_recording_id": meta["source_recording_id"], "task": meta["task"],
        "task_id": meta["task_id"], "rows": N, "status": status,
        "failed_limits": (limits + (["structural"] if problems else [])) if status == FAILED else [],
        "failed_channels": sorted(failed_samples), "failed_samples": failed_samples, "limitations": lim_flags,
        "flight": None,
        "attributes": {"stride_time_s": st,
                       "L3_stride_time_outside_range_reported_only": bool(st is not None and not (L3_RANGE_S[0] <= st <= L3_RANGE_S[1])),
                       "cop_status": cop_status, "cop_label": COP_LABEL if cop_status == "published" else None,
                       "pending_by_ruling": bool(pending_ruling), "plane_glitch_frames_in_window": bool(glitch_in_window),
                       "max_plane_deviation_deg_in_window": plane_deviation_max,
                       "structural_state": "fail" if problems else "pass", "structural_problems": problems,
                       "missing_samples": missing},
        "held_signals": dict(held), "channel_states": channel_states,
    }
    return entry, fails


def leg_cop_verdicts(summary_record):
    """[(leg, verdict, reasons, metrics)] from one S02 summary record."""
    out = []
    for leg, v in sorted(summary_record["legs"].items()):
        g, p = v["cop_gate"], v.get("plate", {})
        ep = p.get("endpoint_check_0p2bw") or {}
        out.append((leg, g["verdict"], list(g.get("reasons", [])),
                    {"strides": v["strides"], "holdout_r": (p.get("ankle_holdout") or {}).get("r"),
                     "toe_within_4cm_fraction": ep.get("fraction_within_4cm_toe"),
                     "plate_assignment_same_plate_fraction": (p.get("plate_assignment") or {}).get("same_plate_loaded_within_5_frames_fraction"),
                     "loaded_fraction": p.get("loaded_fraction")}))
    return out


# ---------------------------------------------------------------- inputs
def receipt_outputs(rel):
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise ValueError(f"{rel} is not a clean completed run")
    return {o["path"]: o["sha256"] for o in r["outputs"]}


def read_v2_recording(path, recording):
    """[(meta, clock, phase, carried)] for one recording of the v2 bundle in file order. carried = the moments and powers.
    Row groups are read one at a time; rows are checked to be 150 samples on the inclusive grid."""
    import pyarrow.parquet as pq
    subject, cond = recording.split("/")
    marker = f"um21:Streaming/{subject}/Tread/{cond}:"
    cols = [*IDENTITY_STR, *IDENTITY_NUM, "held_signals", *V2_CARRIED]
    rows = {}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for g in range(pf.metadata.num_row_groups):
            ids = pf.read_row_group(g, columns=["observation_id"], use_threads=False).column(0).to_pylist()
            if not ids[0].startswith(marker) and not ids[-1].startswith(marker):
                continue
            tab = pf.read_row_group(g, columns=cols, use_threads=False)
            d = {c: (tab.column(c).to_pylist() if (c in IDENTITY_STR or c == "held_signals") else
                     tab.column(c).to_numpy(zero_copy_only=False)) for c in cols}
            for i, oid in enumerate(d["observation_id"]):
                if not oid.startswith(marker):
                    continue
                r = rows.setdefault(oid, {"meta": {c: d[c][i] for c in (*IDENTITY_STR, "held_signals")},
                                          "clock": (float(d["source_start_time_s"][i]), float(d["source_end_time_s"][i])),
                                          "phase": [], **{c: [] for c in V2_CARRIED}})
                r["phase"].append(float(d["phase_ipsi"][i]))
                for c in V2_CARRIED:
                    r[c].append(float(d[c][i]))
    grid = np.linspace(0.0, 100.0, N)
    out = []
    for oid, r in rows.items():
        if len(r["phase"]) != N or not np.allclose(r["phase"], grid, atol=1e-9):
            raise ValueError(f"{oid}: v2 rows are not the 150-sample inclusive grid in order")
        out.append((r["meta"], r["clock"], np.array(r["phase"]), {c: np.array(r[c]) for c in V2_CARRIED}))
    return out


def read_component(path, expected_sha256):
    """The S02 v7 table of one recording: {observation_id: {"side", s02 column: (150,)}} in file order."""
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"{path} differs from its S02 v7 receipt hash")
    import pyarrow.parquet as pq
    with open(path, "rb") as fh:
        t = pq.ParquetFile(fh, buffer_size=0).read(use_threads=False)
    ids, sides = t.column("observation_id").to_pylist(), t.column("reference_side").to_pylist()
    samples = t.column("sample").to_numpy(zero_copy_only=False)
    cols = [c for c in t.schema.names if c not in ("observation_id", "reference_side", "sample")]
    unknown = [c for c in cols if c not in S02_TO_PUBLISHED]
    if unknown:
        raise ValueError(f"{path}: unexpected columns {unknown}")
    data = {c: t.column(c).to_numpy(zero_copy_only=False).astype(float) for c in cols}
    order, seen = [], set()
    for oid in ids:
        if oid not in seen:
            seen.add(oid)
            order.append(oid)
    out = {}
    for k, oid in enumerate(order):
        a = k * N
        if ids[a:a + N] != [oid] * N or list(samples[a:a + N]) != list(range(N)):
            raise ValueError(f"{path}: {oid} is not 150 contiguous samples 0..149")
        out[oid] = {"side": sides[a], **{c: data[c][a:a + N] for c in cols}}
    return out


def frame_checks(trial):
    """Per leg: plane deviation per frame, glitch mask and L2 jump flags per frame series, from one recording's markers."""
    n = int(trial["markers"]["RASI"].shape[1])
    mk, _ = s02.read_markers(trial, n)
    asi_mid, psi_mid = (mk["LASI"] + mk["RASI"]) / 2, (mk["LPSI"] + mk["RPSI"]) / 2
    fwd = s02.heading(asi_mid, psi_mid)
    hjc = s02.hip_centres(mk["RASI"], mk["LASI"], mk["RPSI"], mk["LPSI"])
    pelvis = s02.pelvis_angle_own_plane(asi_mid, psi_mid)
    out = {"frames": n}
    for side, leg in (("R", "right"), ("L", "left")):
        fl = s02.plane_forward(s02.knee_axis_to_right(mk[side + s02.KNEE_LATERAL_MARKER], mk[side + s02.KNEE_MEDIAL_MARKER], side))
        dev = plane_deviation_deg(fl, fwd)
        gl = glitch_mask(dev)
        knee = (mk[side + "KNE"] + mk[side + "KNEM"]) / 2
        ankle = (mk[side + "ANK"] + mk[side + "ANKM"]) / 2
        hip = hjc["right" if side == "R" else "left"]
        seg = s02.leg_segment_angles(fl, knee - hip, ankle - knee, mk[side + "HEE"], mk[side + "TOE"])
        series = {"pelvis_sagittal_angle_rad": pelvis, "thigh_sagittal_angle_ipsi_rad": seg["thigh"],
                  "shank_sagittal_angle_ipsi_rad": seg["shank"], "foot_sagittal_angle_ipsi_rad": seg["foot"],
                  "hip_flexion_angle_ipsi_rad": seg["thigh"] - pelvis, "knee_flexion_angle_ipsi_rad": seg["thigh"] - seg["shank"],
                  "ankle_dorsiflexion_angle_ipsi_rad": seg["foot"] - seg["shank"]}
        flags = {c: frame_jump_flags(x, gl) for c, x in series.items()}
        out[leg] = {"dev": dev, "glitch": gl, "flags": flags, "glitch_frames": int(gl.sum()),
                    "finite_plane_frames": int(np.isfinite(dev).sum()),
                    "max_dev_deg": (float(np.nanmax(dev)) if np.isfinite(dev).any() else None)}
    return out


def compose_recording(rec, handle, comp_dir, comp_hashes, v2_path, summary_rec, ledger_rec):
    """Compose and assess one recording. Returns (entries, failures, rows, evidence)."""
    subject, cond = rec.split("/")
    v2 = read_v2_recording(v2_path, rec)
    rel = f"components/{subject}/{cond}/s02.parquet"
    comp = read_component(Path(comp_dir) / rel, comp_hashes[rel])
    if [m["observation_id"] for m, *_ in v2] != list(comp):
        raise ValueError(f"{rec}: observation ids of v2 and S02 v7 differ")
    fr = frame_checks(handle[f"Streaming/{subject}/Tread/{cond}"])
    verdicts = {leg: (v, why, met) for leg, v, why, met in leg_cop_verdicts(summary_rec)}
    entries, fails, rows, glitch_rows = [], [], [], []
    for meta_v2, clock, phase, carried in v2:
        oid = meta_v2["observation_id"]
        parsed = parse_id(oid)
        if parsed is None:
            raise ValueError(f"{oid}: id does not parse")
        leg = parsed["side"]
        c = comp[oid]
        if c["side"] != meta_v2["reference_side"] or c["side"] != leg:
            raise ValueError(f"{oid}: side differs between id, v2 and S02")
        arrays = {S02_TO_PUBLISHED[k]: v.copy() for k, v in c.items() if k in S02_TO_PUBLISHED}
        arrays.update({k: v.copy() for k, v in carried.items()})
        lacking = [x for x in DATA_COLUMNS if x not in arrays]
        if lacking:
            raise ValueError(f"{oid}: composed table lacks {lacking}")
        held = {}
        for col, why in (json.loads(meta_v2["held_signals"] or "{}") or {}).items():   # v2 powers held: sign unsettled
            if col not in arrays or np.isfinite(arrays[col]).any():
                raise ValueError(f"{oid}: v2 held column {col} is absent or has finite values")
            held[col] = why
        cop_note = (ledger_rec["strides"].get(oid) or {}).get("held", {}).get("cop")
        if cop_note is not None or verdicts[leg][0] == "held":
            if np.isfinite(np.stack([arrays[x] for x in COP_COLUMNS])).any():
                raise ValueError(f"{oid}: S02 holds the centre of pressure but the table has finite values")
            why = cop_note or "; ".join(verdicts[leg][1])
            for x in COP_COLUMNS:
                held[x] = COP_REASON_PREFIX + why
        for k in (ledger_rec["strides"].get(oid) or {}).get("columns_all_missing", []):
            held[S02_TO_PUBLISHED[k]] = GAP_REASON
        f = fr[leg]
        glitch = window_has_glitch(f["glitch"], parsed["a"], parsed["b"])
        if glitch:
            apply_plane_hold(arrays, held)
        win_dev = f["dev"][parsed["a"] - 1:parsed["b"]]
        max_dev = float(np.nanmax(win_dev)) if np.isfinite(win_dev).any() else None
        jumps = {col: ([] if glitch else stride_jump_pairs(flags, parsed["a"], parsed["b"])) for col, flags in f["flags"].items()}
        if any(held.get(x, "").startswith(COP_REASON_PREFIX) for x in COP_COLUMNS):
            cop_status = "held"
        else:
            cop_status = "published" if np.isfinite(np.stack([arrays[x] for x in COP_COLUMNS])).any() else "no_loaded_samples"
        meta = {k: meta_v2[k] for k in ("observation_id", "reference_side", "observation_type", "subject",
                                        "source_recording_id", "task", "task_id")}
        meta["phase"] = list(range(N))
        entry, fl = assess_observation(meta, arrays, held, jumps, glitch, max_dev, cop_status, rec in PENDING_BY_RULING)
        entries.append(entry)
        fails.extend(fl)
        if glitch:
            glitch_rows.append({"observation_id": oid, "recording": rec, "leg": leg, "max_plane_deviation_deg": max_dev,
                                "frames_over_limit_in_window": int(np.sum(f["glitch"][parsed["a"] - 1:parsed["b"]]))})
        rows.append((meta_v2, clock, phase, arrays, held))
    evidence = {"legs": {leg: {"frames_over_60_deg": fr[leg]["glitch_frames"], "finite_plane_frames": fr[leg]["finite_plane_frames"],
                               "max_plane_deviation_deg": fr[leg]["max_dev_deg"], "cop_verdict": verdicts[leg][0],
                               "cop_reasons": verdicts[leg][1], "cop_metrics": verdicts[leg][2]}
                         for leg in ("right", "left") if leg in verdicts},
                "glitch_strides": glitch_rows}
    return entries, fails, rows, evidence


def part_schema():
    import pyarrow as pa
    fields = [pa.field(c, pa.string()) for c in IDENTITY_STR] + [pa.field(c, pa.float64()) for c in IDENTITY_NUM]
    fields += [pa.field(c, pa.float64()) for c in DATA_COLUMNS] + [pa.field("held_signals", pa.string())]
    return pa.schema(fields)


def write_part(path, rows):
    """One recording's composed table part (150 rows per observation, file order). Returns its sha256."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    cols = {c: [] for c in (*IDENTITY_STR, *IDENTITY_NUM, *DATA_COLUMNS, "held_signals")}
    for meta, clock, phase, arrays, held in rows:
        for c in IDENTITY_STR:
            cols[c].extend([meta[c]] * N)
        cols["phase_ipsi"].extend(phase.tolist())
        cols["source_start_time_s"].extend([clock[0]] * N)
        cols["source_end_time_s"].extend([clock[1]] * N)
        for c in DATA_COLUMNS:
            cols[c].extend(np.asarray(arrays[c], float).tolist())
        cols["held_signals"].extend([json.dumps(held, sort_keys=True)] * N)
    pq.write_table(pa.table(cols, schema=part_schema()), str(path), compression="zstd", row_group_size=3000,
                   store_schema=False)
    return sha256_file(path)


# ---------------------------------------------------------------- spec and job
def stage_recordings(stage):
    if stage == "pilot":
        return list(PILOT_RECORDINGS)
    return sorted(s02.stage_recordings("full"))


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}", "spec": f"{AUDITS}/um21-q01v3-{stage}-spec.json",
            "output_root": f"converted_datasets/reconversion_v2/um21_q01v3_{stage}",
            "receipt": f"{AUDITS}/um21-q01v3-{stage}-launcher-receipt.json"}


def bound_files():
    b = dict(s02.bindings())
    for rel in (RUNNER, S02_RECEIPT, S02_VERIFY, f"{S02_ROOT}/s02_summary.json", f"{S02_ROOT}/s02_ledger.json", V2_EXCLUSIONS):
        b[rel] = sha256_file(ROOT / rel)
    return b


def build_spec(stage, pilot_receipt=None):
    p = stage_paths(stage)
    cmd = ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
           "--recordings", ",".join(stage_recordings(stage))]
    b = bound_files()
    if stage == "full":
        cmd += ["--pilot-receipt", pilot_receipt]
        b[pilot_receipt] = sha256_file(ROOT / pilot_receipt)
    return {"job_id": p["job_id"], "command": cmd, "cwd": str(ROOT), "output_root": p["output_root"],
            "receipt_path": p["receipt"], "bindings": b, "timeout_seconds": 3600, "kill_after_seconds": 30,
            "poll_seconds": 15, "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048}, "expected_output_names": ["assessment.json"],
            "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage, pilot_receipt=None):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage, pilot_receipt)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": sha256_file(path)}))


def check_pilot(rel):
    r = json.loads((ROOT / rel).read_text())
    if r.get("status") != "completed" or r.get("clean_success") is not True:
        raise SystemExit("refused: the pilot receipt is not a clean completed run")
    cmd = r["spec"]["command"]
    if cmd[cmd.index("--stage") + 1] != "pilot":
        raise SystemExit("refused: the receipt is not a pilot run")
    if r["spec"]["bindings"].get(RUNNER) != sha256_file(ROOT / RUNNER):
        raise SystemExit("refused: the pilot ran different code than the current runner")


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the pilot sample or the 44 reviewed recordings")
    if args.stage == "full":
        if not args.pilot_receipt:
            raise SystemExit("refused: a full run needs --pilot-receipt")
        check_pilot(args.pilot_receipt)
    if _mem_available() < MIN_AVAILABLE_BYTES:
        raise MemoryError("less than 2 GiB available; not started")
    comp_hashes = receipt_outputs(S02_RECEIPT)
    summary = json.loads((ROOT / S02_ROOT / "s02_summary.json").read_text())
    ledger = json.loads((ROOT / S02_ROOT / "s02_ledger.json").read_text())
    srec = {r["recording"]: r for r in summary["records"]}
    if args.stage == "full" and recordings != sorted(summary["recordings"]):
        raise ValueError("the recordings differ from those of the S02 v7 run")
    if summary["v2_full_sha256"] != sha256_file(ROOT / V2_FULL):
        raise ValueError("the v2 table differs from the one S02 v7 was built on")
    source = ROOT / s02.t04.SOURCE
    c03 = json.loads((ROOT / s02.t04.C03).read_text())["source"]
    st = source.stat()
    if (st.st_size, st.st_mtime_ns) != (c03["bytes"], c03["mtime_ns"]):
        raise ValueError("Streaming.mat size/mtime differ from the UM21-C03 record")
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "parts").mkdir()
    started = time.time()
    import h5py
    totals = {"observations": 0, "failed": 0, "rows": 0}
    by_limit, by_channel, per_rec, legs_out, glitch_all, part_hashes = {}, {}, {}, [], [], {}
    with h5py.File(source, "r", rdcc_nbytes=1024 ** 2) as handle, open(out / "observations.jsonl", "x") as fo, \
            open(out / "failures.jsonl", "x") as ff:
        for rec in recordings:
            if _mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            entries, fails, rows, ev = compose_recording(rec, handle, ROOT / S02_ROOT, comp_hashes, ROOT / V2_FULL,
                                                         srec[rec], ledger[rec])
            name = f"parts/{rec.replace('/', '_')}.parquet"
            part_hashes[name] = write_part(out / name, rows)
            for e in entries:
                fo.write(json.dumps(e, sort_keys=True) + "\n")
                totals["observations"] += 1
                totals["rows"] += N
                if e["status"] == FAILED:
                    totals["failed"] += 1
                    for lim in e["failed_limits"]:
                        by_limit[lim] = by_limit.get(lim, 0) + 1
            for x in fails:
                ff.write(json.dumps(x) + "\n")
                k = f"{x['limit']}:{x['channel']}"
                by_channel[k] = by_channel.get(k, 0) + 1
            for leg, d in ev["legs"].items():
                legs_out.append({"recording": rec, "leg": leg, **d, "strides": d["cop_metrics"]["strides"]})
            glitch_all.extend(ev["glitch_strides"])
            per_rec[rec] = {"observations": len(entries), "failed": sum(1 for e in entries if e["status"] == FAILED),
                            "part_sha256": part_hashes[name], "peak_rss_mib": round(_peak_rss_mib(), 1)}
            print(f"{rec} done, {len(entries)} observations, {per_rec[rec]['failed']} failed, peak RSS {_peak_rss_mib():.0f} MiB",
                  flush=True)
            del entries, fails, rows
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    after = source.stat()
    unchanged = (after.st_size, after.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
    full = args.stage == "full"
    pub = [l for l in legs_out if l["cop_verdict"] == "pass"]
    held = [l for l in legs_out if l["cop_verdict"] != "pass"]
    expected_ok = (not full) or (totals["observations"] == 7545 and len(legs_out) == 88 and len(pub) == 60 and len(held) == 28)
    assessment = {
        "task_id": TASK_ID, "version": VERSION, "stage": args.stage, "scientific_approval": False,
        "note": "automated structured assessment on the S02 v7 table; independent review follows",
        "profile": PROFILE,
        "decisions_applied": ["D-UM21-Q01-1 = B", "D-UM21-S02-1 = A", "D-UM21-S02-2 = A",
                              "held-back data stays pending as it is (ruling, no further investigation)"],
        "inputs": {"s02_receipt": S02_RECEIPT, "s02_root": S02_ROOT, "v2_full_sha256": summary["v2_full_sha256"],
                   "source_unchanged_after_run": unchanged},
        "totals": {**totals, "expected_for_full": {"observations": 7545, "legs": 88, "cop_legs_published": 60, "cop_legs_held": 28},
                   "matches_expected": expected_ok},
        "failed_by_limit_observations": by_limit, "failed_samples_by_limit_and_channel": by_channel,
        "cop_legs": {"published": [{k: l[k] for k in ("recording", "leg", "strides", "cop_metrics")} for l in pub],
                     "held": [{k: l[k] for k in ("recording", "leg", "strides", "cop_reasons", "cop_metrics")} for l in held],
                     "pending_by_ruling_recordings": sorted(PENDING_BY_RULING),
                     "label": COP_LABEL, "rule": s02.GATE},
        "plane_glitch_rule": {"limit_deg": PLANE_GLITCH_DEG, "chosen": "before results were looked at; verifier suggestion",
                              "legs": [{"recording": l["recording"], "leg": l["leg"], "frames_over_60_deg": l["frames_over_60_deg"],
                                        "finite_plane_frames": l["finite_plane_frames"],
                                        "max_plane_deviation_deg": l["max_plane_deviation_deg"]} for l in legs_out],
                              "strides_held": glitch_all},
        "per_record": per_rec, "part_sha256": part_hashes,
        "sidecar_files": {n: {"sha256": sha256_file(out / n), "bytes": (out / n).stat().st_size}
                          for n in ("observations.jsonl", "failures.jsonl")},
        "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                      "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                      "wall_seconds": round(time.time() - started, 1)},
    }
    with open(out / "assessment.json", "x") as f:
        json.dump(assessment, f, indent=1, allow_nan=False)
    print(json.dumps({"totals": totals, "failed_by_limit": by_limit, "cop_legs_published": len(pub), "cop_legs_held": len(held),
                      "glitch_strides": len(glitch_all), "peak_rss_mib": assessment["resources"]["peak_rss_mib"]}))
    return 0 if (expected_ok and unchanged) else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan")
    pp.add_argument("--stage", choices=("pilot", "full"), required=True)
    pp.add_argument("--pilot-receipt")
    pr = sub.add_parser("run")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "full"), required=True)
    pr.add_argument("--recordings", required=True)
    pr.add_argument("--pilot-receipt")
    args = p.parse_args(argv)
    if args.step == "plan":
        if args.stage == "full" and not args.pilot_receipt:
            raise SystemExit("a full plan needs --pilot-receipt")
        return plan(args.stage, args.pilot_receipt)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
