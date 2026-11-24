#!/usr/bin/env python3
"""UM21-S02: apply the gravity-referenced zero and the foot-frame centre of pressure (docs/reference/index.md).

Per recording (UMich 2021 treadmill, Streaming.mat) and for every observation of the v2 review bundle
(um21_r01_review_v2, read only):

* pelvis, thigh, shank and foot SEGMENT angles from markers, exactly as the standard defines them: thigh and shank
  from straight down (hip centre to knee centre, knee centre to ankle centre), foot (heel to toe) and pelvis (PSIS to
  ASIS) from forward horizontal, counterclockwise positive, forward = the person's facing direction of the recording;
* JOINT angles are plain differences: hip = thigh - pelvis, knee = thigh - shank, ankle = foot - shank;
* velocities from those angles (same derivative method as T04: sa.derive_angular_velocities, stride duration / 149);
* centre of pressure in the foot frame (origin 100 mm forward of the ankle centre along heel-to-toe), from the plate
  centre of pressure after: mm to m, unloaded samples (< 20 N) missing, plate axis and sign fixed from the data, belt
  tilt, and a fitted plate shift (forward, up) from hip and knee moments, with the lateral shift from the foot's
  mean lateral position. The registration is fitted, not measured; independent checks are reported and the columns
  are held (present, all missing, with a reason) for a leg whose checks fail.
* pelvis: the v2 (kept) values, re-checked against the marker pelvis on every stride; a stride that disagrees by more
  than 0.2 deg (median) holds pelvis and hip. Moments are not rewritten; powers stay held (not in this output).

Nothing is filled: a stride with a marker gap loses the columns that need that marker; a sample the plate does not
load has no centre of pressure. New output root only; v2 and the source are read, never written.

``plan``  write and validate a guarded-launcher spec (no research data read except hashing bound files).
``run``   the job; only through ``python3 -m contributor_tools.guarded_launcher run SPEC.json``.
scientific_approval is false everywhere.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_key, "1")
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")  # before pyarrow is imported (T04 B1)
import argparse
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


def _load_by_file(name, path):
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name, None)
            raise
    if Path(module.__file__).resolve() != Path(path).resolve():
        raise ImportError(f"{name} already imported from {module.__file__}")
    return module


t04 = _load_by_file("contributor_tools.run_um21_t04_signs", ROOT / "contributor_tools/run_um21_t04_signs.py")
um21, sa = t04.um21, t04.sa

TASK_ID = "UM21-S02"
RUNNER = "contributor_tools/run_um21_s02_frame.py"
VERSION = "v5"
V2_ROOT = "converted_datasets/reconversion_v2/um21_r01_review_v2"
V2_FULL = f"{V2_ROOT}/full.parquet"
V2_MANIFEST = f"{V2_ROOT}/manifest.json"
PILOT_FIXED = ("AB03/i10", "AB04/i0", "AB07/i10", "AB08/d10")
PILOT_SEED = 20261124
N = 150
FRAME_HZ = 100.0
PLATE_PER_FRAME = 10
FOOT_ORIGIN_M = 0.100          # standard: origin 100 mm forward of the ankle centre along heel-to-toe
LOAD_THRESHOLD_N = 20.0        # source README noise level (agent default, logged)
UP = np.array([0.0, 0.0, 1.0])  # marker frame is gravity-aligned, z up (UM21-C03, C01)
GRAVITY = 9.81
RSS_CAP_MIB = 450.0
ADDRESS_SPACE_MIB = 768
MIN_AVAILABLE_BYTES = 2 * 1024 ** 3
PELVIS_FLAG_DEG = 0.2          # per-stride median |v2 pelvis - marker pelvis| above this is flagged (UM21-C03: 0.03-0.14 deg)
PELVIS_HOLD_DEG = 1.0          # above this the pelvis (and the hip) is held: a clear disagreement, not marker noise (pilot v1: max 0.39 deg)
# PROVISIONAL gate values for the pilot. The full run needs values fixed beforehand by a decision (see the handoff).
GATE = {"toe_endpoint_tolerance_m": 0.04, "toe_endpoint_threshold": "0.2 body weight", "toe_endpoint_fraction_min": 0.95,
        "ankle_holdout_r_min": 0.95, "plate_assignment_fraction_min": 0.95,
        "heel_endpoint": "reported, not a gate: the heel marker sits above and behind the sole",
        "status": "D-UM21-S02-1 = A (Jose): publish the CoP built on the estimated plate position when both checks pass"}
HELD_UNTIL_EXPLAINED = {"AB04/d10": "held until the 20 cm heel-end offset is explained (D-UM21-S02-1)"}
COP_LABEL = "estimated plate position"
FIT_MIN_FORCE_BW = 0.3         # samples loaded above this fraction of body weight enter the shift fit
DEFAULTS = {
    "hip_centre": "Harrington 2007 regression from pelvic width (ASIS-ASIS) and depth (ASIS-mid to PSIS-mid); "
                  "per-recording medians; pelvis frame from the four pelvis markers. Not the Davis/Plug-in Gait "
                  "regression (leg length and marker diameter conventions are not in the source). The "
                  "greater-trochanter marker difference is reported, not used.",
    "ankle_centre": "midpoint of the two malleolus markers (ANK, ANKM); marker radius ignored",
    "knee_centre": "midpoint of the two knee markers (KNE, KNEM)",
    "foot_line": "heel marker to toe marker (marker-defined, not sole-defined)",
    "projection": "planar: foot direction from its forward and up components; sideways axis horizontal",
    "walking_direction": "per recording, mean horizontal PSIS-to-ASIS direction (the person's facing)",
    "marker_gaps": "no gap filling, no marker filtering; a stride with a gap in its window loses every column that "
                   "needs that marker",
    "unloaded_cop": f"plate vertical force below {LOAD_THRESHOLD_N} N: centre of pressure missing, never zero",
    "plate_time": "plate sample j is at time j/1000 s from the first frame (start aligned, 10 samples per frame)",
    "phase_resampling": "linear interpolation on the 150-sample inclusive grid over frames a..b (T04); plate samples "
                        "interpolated only between two loaded samples",
    "plate_axes": "long axis and its sign per recording and plate from the data (correlation of ankle forward "
                  "position with each plate axis in mid-stance); sideways axis from right-handedness (plate z up)",
    "belt_tilt": "magnitude from the nominal condition slope (README), sign from the heel path in mid-stance; "
                 "plate tilted by it about the sideways axis",
    "plate_shift": "forward shift fitted by least squares so that quasi-static ground-force moments about the "
                   "hip and knee match the v2 hip and knee moments (loaded samples above 30 percent body weight); the up "
                   "shift is NOT fitted (not identifiable from the moments) but set by the foot-on-belt rule: the centre "
                   "of pressure lies at the height of the lowest heel or toe marker in mid-stance (the marker height above "
                   "the sole is unknown and not subtracted); the unconstrained two-parameter fit is kept as a diagnostic; "
                   "the lateral shift sets the mean centre-of-pressure lateral position to the mean heel-toe "
                   "midpoint lateral position. The ankle moment is held out for checking.",
    "pelvis": "v2 (Vicon) pelvis kept; per-stride median difference to the marker pelvis above "
              f"{PELVIS_FLAG_DEG} deg is flagged, above {PELVIS_HOLD_DEG} deg holds pelvis and hip",
}
OUT_COLUMNS = ("pelvis_tilt", "hip_angle", "knee_angle", "ankle_angle", "thigh_angle", "shank_angle", "foot_angle",
               "pelvis_tilt_velocity", "thigh_angle_velocity", "shank_angle_velocity", "foot_angle_velocity")
COP_COLUMNS = ("cop_anterior", "cop_vertical", "cop_lateral")
V2_COLUMNS = {"pelvis_tilt": "pelvis_sagittal_angle_rad", "hip_angle": "hip_flexion_angle_ipsi_rad",
              "knee_angle": "knee_flexion_angle_ipsi_rad", "ankle_angle": "ankle_dorsiflexion_angle_ipsi_rad",
              "thigh_angle": "thigh_sagittal_angle_ipsi_rad", "shank_angle": "shank_sagittal_angle_ipsi_rad",
              "hip_moment": "hip_flexion_moment_ipsi_Nm_kg", "knee_moment": "knee_flexion_moment_ipsi_Nm_kg",
              "ankle_moment": "ankle_dorsiflexion_moment_ipsi_Nm_kg"}
MARKERS = ("LASI", "RASI", "LPSI", "RPSI", "RGT", "LGT", "RKNE", "RKNEM", "LKNE", "LKNEM", "RANK", "RANKM", "LANK",
           "LANKM", "RHEE", "RTOE", "LHEE", "LTOE")


# =========================================================== pure geometry (tested with synthetic known values)
def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def right_axis(fwd, up=UP):
    """Horizontal unit vector to the person's right (forward x up = right in the standard frame)."""
    return unit(np.cross(fwd, up))


def heading(asi_mid, psi_mid, up=UP):
    """Forward horizontal unit vector: mean PSIS-to-ASIS direction with its vertical part removed."""
    d = np.nanmean(np.asarray(asi_mid, float) - np.asarray(psi_mid, float), axis=0)
    d = d - (d @ up) * up
    return unit(d)


def sagittal(points, fwd, up=UP):
    """(..., 3) lab points -> (..., 2) forward and up components."""
    p = np.asarray(points, float)
    return np.stack([p @ fwd, p @ up], axis=-1)


def angle_from_down(v):
    """Angle of an (forward, up) vector from straight down, counterclockwise positive (distal end forward > 0)."""
    return np.arctan2(v[..., 0], -v[..., 1])


def angle_from_forward(v):
    """Angle of an (forward, up) vector from forward horizontal, counterclockwise positive (toes up > 0)."""
    return np.arctan2(v[..., 1], v[..., 0])


def segment_angles(p):
    """p: sagittal (n, 2) points asi, psi (pelvis markers, midpoints), hip, knee, ankle, heel, toe centres.
    Returns the four segment angles in radians."""
    return {"pelvis": angle_from_forward(p["asi"] - p["psi"]),
            "thigh": angle_from_down(p["knee"] - p["hip"]),
            "shank": angle_from_down(p["ankle"] - p["knee"]),
            "foot": angle_from_forward(p["toe"] - p["heel"])}


def joint_angles(seg):
    """The standard's zero: joint angles are differences of segment angles."""
    return {"hip": seg["thigh"] - seg["pelvis"], "knee": seg["thigh"] - seg["shank"],
            "ankle": seg["foot"] - seg["shank"]}


HARRINGTON = {"x": (-0.24, -0.0099), "y": (-0.30, -0.0109), "z": (0.33, 0.0073)}  # (slope, offset m)


def hip_centres(rasi, lasi, rpsi, lpsi, up=UP):
    """Right and left hip centres (n, 3) from the four pelvis markers (lab frame, metres), Harrington regression:
    anterior = -0.24 depth - 9.9 mm, vertical = -0.30 width - 10.9 mm, lateral = 0.33 width + 7.3 mm, measured from
    the ASIS midpoint along the pelvis axes (anterior from PSIS-mid to ASIS-mid, orthogonal to the ASIS line)."""
    rasi, lasi, rpsi, lpsi = (np.asarray(a, float) for a in (rasi, lasi, rpsi, lpsi))
    asi_mid, psi_mid = (rasi + lasi) / 2, (rpsi + lpsi) / 2
    w = rasi - lasi
    width = float(np.nanmedian(np.linalg.norm(w, axis=1)))
    e_r = w / np.linalg.norm(w, axis=1, keepdims=True)
    a = asi_mid - psi_mid
    depth = float(np.nanmedian(np.linalg.norm(a, axis=1)))
    a = a - np.sum(a * e_r, axis=1, keepdims=True) * e_r
    e_a = a / np.linalg.norm(a, axis=1, keepdims=True)
    e_u = np.cross(e_r, e_a)
    x = HARRINGTON["x"][0] * depth + HARRINGTON["x"][1]
    y = HARRINGTON["y"][0] * width + HARRINGTON["y"][1]
    z = HARRINGTON["z"][0] * width + HARRINGTON["z"][1]
    base = asi_mid + x * e_a + y * e_u
    return {"right": base + z * e_r, "left": base - z * e_r, "pelvic_width_m": width, "pelvic_depth_m": depth,
            "offsets_m": {"anterior": x, "vertical": y, "lateral": z}}


def window_ok(finite, a, b):
    """True when every frame a..b (1-based, inclusive) is finite."""
    return bool(np.all(finite[a - 1:b]))


def plate_at(values, pos):
    """Linear interpolation of a plate series at fractional sample positions; NaN when either neighbouring plate
    sample is missing (unloaded), even at an exact sample."""
    v = np.asarray(values, float)
    pos = np.asarray(pos, float)
    i0 = np.floor(pos).astype(int)
    w = pos - i0
    i1 = np.minimum(i0 + 1, v.shape[-1] - 1)
    return (1.0 - w) * v[..., i0] + w * v[..., i1]


def mask_unloaded(force, cop_mm, threshold_n=LOAD_THRESHOLD_N):
    """Plate arrays -> (force (3, m), cop (3, m) in metres, loaded mask). Vertical plate force is negative when the
    foot loads the plate. Unloaded samples (and exact zero centre-of-pressure fill) become NaN, never zero."""
    f = np.asarray(force, float).copy()
    c = np.asarray(cop_mm, float).copy() / 1000.0
    loaded = np.isfinite(f).all(axis=0) & (-f[2] > threshold_n) & ~(c == 0).all(axis=0) & np.isfinite(c).all(axis=0)
    f[:, ~loaded] = np.nan
    c[:, ~loaded] = np.nan
    return f, c, loaded


def plate_to_person(cop, axis, sign, tilt_rad, shifts=(0.0, 0.0, 0.0)):
    """Plate centre of pressure (2 or 3, ...) in metres -> (forward, up, right) in the person's frame.
    The plate long axis is plate axis ``axis`` times ``sign``; the plate z axis is up, so the person's right is
    (sign * e_axis) x e_z. The plate surface is tilted by ``tilt_rad`` (positive: rising forward); shifts are
    (forward, up, right) added after the tilt."""
    cop = np.asarray(cop, float)
    p0, p1 = cop[0], cop[1]
    long = sign * (p0 if axis == 0 else p1)
    right = sign * (-p1) if axis == 0 else sign * p0
    return np.stack([long * np.cos(tilt_rad) + shifts[0], long * np.sin(tilt_rad) + shifts[1], right + shifts[2]])


def force_to_person(force, axis, sign, tilt_rad):
    """Plate force (3, ...) -> ground force on the person (forward, up, right): the negative of the plate force,
    turned the same way as the plate."""
    f = np.asarray(force, float)
    f0, f1, fz = f
    gl = -sign * (f0 if axis == 0 else f1)
    gn = -fz
    gr = -(sign * (-f1)) if axis == 0 else -(sign * f0)
    return np.stack([gl * np.cos(tilt_rad) - gn * np.sin(tilt_rad), gl * np.sin(tilt_rad) + gn * np.cos(tilt_rad), gr])


def foot_frame(point, ankle, foot_angle, leg):
    """(forward, up, right) lab-frame points -> foot-frame (anterior, vertical, lateral) metres. The frame's origin
    is 0.1 m forward of the ankle centre along the heel-to-toe direction (planar), anterior along the foot,
    vertical perpendicular to it (up when the foot is flat), lateral outward from that leg (+ right for the right
    leg, + left for the left leg)."""
    point, ankle = np.asarray(point, float), np.asarray(ankle, float)
    c, s = np.cos(foot_angle), np.sin(foot_angle)
    q = point - ankle
    anterior = q[0] * c + q[1] * s - FOOT_ORIGIN_M
    vertical = -q[0] * s + q[1] * c
    lateral = q[2] if leg == "right" else -q[2]
    return np.stack([anterior, vertical, lateral])


def joint_moment_from_force(cop_fu, force_fu, joint_fu, which):
    """Quasi-static internal moment (named direction positive, per kg when the force is per kg) from the ground
    force on the person: the external torque of the force about the joint is tau = rx*Fy - ry*Fx (counterclockwise
    positive); ankle and hip internal moments are -tau, the knee's is +tau (flexion is clockwise rotation of the
    distal segment, dorsiflexion and hip flexion are counterclockwise)."""
    rx, ry = cop_fu[0] - joint_fu[0], cop_fu[1] - joint_fu[1]
    tau = rx * force_fu[1] - ry * force_fu[0]
    return tau if which == "knee" else -tau


def fit_shifts(cop_fu, force_fu, hip_fu, knee_fu, m_hip, m_knee):
    """Least-squares forward and up shifts (dx, dy) of a centre of pressure that make the quasi-static hip and knee
    moments match the given ones. Arrays are 1-D over the samples used. Returns (shift (2,), n, condition)."""
    tau0_h = -joint_moment_from_force(cop_fu, force_fu, hip_fu, "hip")
    tau0_k = joint_moment_from_force(cop_fu, force_fu, knee_fu, "knee")
    a = np.stack([force_fu[1], -force_fu[0]], axis=1)
    big = np.vstack([a, a])
    y = np.concatenate([m_knee - tau0_k, -(m_hip + tau0_h)])
    sol, *_ = np.linalg.lstsq(big, y, rcond=None)
    return sol, int(len(m_knee)), float(np.linalg.cond(big))


def fit_forward_shift(cop_fu, force_fu, hip_fu, knee_fu, m_hip, m_knee, dy):
    """Forward shift dx only, with the up shift dy given (not fitted): least squares of the same hip and knee moment
    equations as fit_shifts, Fy*dx = (target) + Fx*dy. Returns (dx, samples)."""
    tau0_h = -joint_moment_from_force(cop_fu, force_fu, hip_fu, "hip")
    tau0_k = joint_moment_from_force(cop_fu, force_fu, knee_fu, "knee")
    fx = np.concatenate([force_fu[0], force_fu[0]])
    a = np.concatenate([force_fu[1], force_fu[1]])
    t = np.concatenate([m_knee - tau0_k, -(m_hip + tau0_h)]) + fx * dy
    return float(a @ t / (a @ a)), int(len(m_knee))


def loaded_runs(loaded, min_len=300):
    idx = np.flatnonzero(loaded)
    if idx.size == 0:
        return []
    return [(int(g[0]), int(g[-1]) + 1) for g in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(g) >= min_len]


def central(run):
    lo, hi = run
    q = (hi - lo) // 4
    return lo + q, hi - q


def choose_plate_axis(cop, ankle_fwd, runs):
    """Plate axis (0 or 1) and sign whose centre of pressure moves with the ankle's forward position in mid-stance.
    cop: (2, m) metres (NaN unloaded); ankle_fwd: (m,) forward position at plate times. Per loaded run: correlation
    and slope for each axis; the axis with the larger median |r| wins, its median slope sets the sign."""
    stats = {0: [], 1: []}
    for run in runs:
        lo, hi = central(run)
        for k in (0, 1):
            x, y = cop[k, lo:hi], ankle_fwd[lo:hi]
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() > 50 and np.std(x[ok]) > 0 and np.std(y[ok]) > 0:
                stats[k].append((np.corrcoef(x[ok], y[ok])[0, 1], np.polyfit(x[ok], y[ok], 1)[0]))
    out = {}
    for k in (0, 1):
        out[k] = {"runs": len(stats[k]),
                  "median_abs_r": float(np.median([abs(r) for r, _ in stats[k]])) if stats[k] else None,
                  "median_slope": float(np.median([s for _, s in stats[k]])) if stats[k] else None}
    if out[0]["median_abs_r"] is None or out[1]["median_abs_r"] is None:
        return None, out
    axis = 0 if out[0]["median_abs_r"] >= out[1]["median_abs_r"] else 1
    return (axis, 1 if out[axis]["median_slope"] > 0 else -1), out


def belt_slope_deg(heel_fu, runs_frames):
    """Median heel-path slope (up versus forward, degrees) over the mid-stance of loaded runs (frame indices)."""
    slopes = []
    for lo, hi in runs_frames:
        s0, s1 = lo + int(0.3 * (hi - lo)), lo + int(0.6 * (hi - lo))
        x, y = heel_fu[s0:s1, 0], heel_fu[s0:s1, 1]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() > 5 and np.std(x[ok]) > 0:
            slopes.append(float(np.degrees(np.arctan(np.polyfit(x[ok], y[ok], 1)[0]))))
    return (float(np.median(slopes)) if slopes else None), slopes


# =========================================================== bounded readers
def read_markers(trial, n):
    """{name: (n, 3) metres, NaN where the visible flag is not 1}, {name: visible fraction}."""
    out, cov = {}, {}
    for name in MARKERS:
        m = trial["markers"][name][...]
        if m.ndim != 2 or m.shape[0] < 4 or m.shape[1] != n:
            raise ValueError(f"markers/{name}: shape {m.shape}")
        xyz = m[:3].T.astype(np.float64).copy()
        ok = (m[3] == 1) & np.isfinite(xyz).all(axis=1)
        xyz[~ok] = np.nan
        out[name], cov[name] = xyz, float(ok.mean())
    return out, cov


def read_v2_rows(path, recording, columns=tuple(V2_COLUMNS.values())):
    """{observation_id: {column: (150,)}}, in file order, for one recording of the v2 bundle. Reads row groups whose
    observation ids belong to the recording, in batches; nothing else is held. recording is 'ABxx/cond'."""
    import pyarrow.parquet as pq
    subject, cond = recording.split("/")
    marker = f"um21:Streaming/{subject}/Tread/{cond}:"
    rows = {}
    with open(path, "rb") as fh:
        pf = pq.ParquetFile(fh, buffer_size=0)
        for g in range(pf.metadata.num_row_groups):
            ids = pf.read_row_group(g, columns=["observation_id"], use_threads=False).column(0).to_pylist()
            if not ids[0].startswith(marker) and not ids[-1].startswith(marker):
                continue
            tab = pf.read_row_group(g, columns=["observation_id", "phase_ipsi", *columns], use_threads=False)
            ids = tab.column("observation_id").to_pylist()
            cols = {c: tab.column(c).to_numpy(zero_copy_only=False) for c in columns}
            ph = tab.column("phase_ipsi").to_numpy(zero_copy_only=False)
            for i, oid in enumerate(ids):
                if not oid.startswith(marker):
                    continue
                r = rows.setdefault(oid, {"_n": 0, "_phase": [], **{c: [] for c in columns}})
                r["_n"] += 1
                r["_phase"].append(ph[i])
                for c in columns:
                    r[c].append(cols[c][i])
    grid = np.linspace(0.0, 100.0, N)
    for oid, r in rows.items():
        if r["_n"] != N or not np.allclose(r["_phase"], grid, atol=1e-9):
            raise ValueError(f"{oid}: v2 rows are not the 150-sample inclusive grid in order")
        rows[oid] = {c: np.array(r[c], dtype=float) for c in columns}
    return rows


# =========================================================== one recording
def _nan_rows(arr, ok):
    arr[~ok] = np.nan
    return arr


def _quantiles(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return None
    return {"n": int(x.size), "median": float(np.median(x)), "q25": float(np.percentile(x, 25)),
            "q75": float(np.percentile(x, 75)), "min": float(x.min()), "max": float(x.max()),
            "p95": float(np.percentile(x, 95)), "p95_abs": float(np.percentile(np.abs(x), 95))}


def process_recording(trial, recording, v2, mass_kg, nominal_slope_deg, debug=None):
    """One recording. trial: mapping with markers/forceplates/events like the h5py group; v2: {observation_id:
    {v2 column: (150,)}} from read_v2_rows. Returns (obs_ids, sides, out (column -> (N, 150)), cop_unheld, summary,
    ledger). Pure given its inputs (no file access)."""
    n = int(trial["jointAngles"]["RPelvisAngles"].shape[1]) if "jointAngles" in trial else int(
        trial["markers"]["RASI"].shape[1])
    mk, coverage = read_markers(trial, n)
    asi_mid, psi_mid = (mk["LASI"] + mk["RASI"]) / 2, (mk["LPSI"] + mk["RPSI"]) / 2
    fwd = heading(asi_mid, psi_mid)
    rvec = right_axis(fwd)
    hjc = hip_centres(mk["RASI"], mk["LASI"], mk["RPSI"], mk["LPSI"])
    feet_dir = np.nanmean(np.vstack([mk["RTOE"] - mk["RHEE"], mk["LTOE"] - mk["LHEE"]]), axis=0)
    feet_dir -= (feet_dir @ UP) * UP
    agreement = float(np.degrees(np.arccos(np.clip(unit(feet_dir) @ fwd, -1, 1))))

    def sag(p):
        return sagittal(p, fwd)

    def rt(p):
        return np.asarray(p, float) @ rvec

    pelvis_pts = {"asi": sag(asi_mid), "psi": sag(psi_mid)}
    pelvis_frame = angle_from_forward(pelvis_pts["asi"] - pelvis_pts["psi"])
    vis = {k: np.isfinite(v).all(axis=1) for k, v in mk.items()}
    all_pelvis = vis["LASI"] & vis["RASI"] & vis["LPSI"] & vis["RPSI"]
    meta = {"fwd_lab": np.round(fwd, 4).tolist(), "pelvis_axis_vs_foot_axis_deg": round(agreement, 2),
            "frames": n, "marker_visible_fraction": {k: round(v, 4) for k, v in coverage.items()},
            "hip_centre": {k: hjc[k] for k in ("pelvic_width_m", "pelvic_depth_m", "offsets_m")},
            "body_mass_kg": mass_kg}
    ids = list(v2)
    parsed = {oid: t04.parse_observation_id(oid) for oid in ids}
    ledger = {"strides": {}}
    out = {c: np.full((len(ids), N), np.nan) for c in OUT_COLUMNS}
    cop_unheld = {c: np.full((len(ids), N), np.nan) for c in COP_COLUMNS}
    cop_held = {c: np.full((len(ids), N), np.nan) for c in COP_COLUMNS}
    sides = [parsed[o]["leg"] for o in ids]
    summary = {"recording": recording, "meta": meta, "observations": len(ids), "legs": {}}
    t_plate = None
    for side, leg in (("R", "right"), ("L", "left")):
        rows = [i for i, o in enumerate(ids) if parsed[o]["leg"] == leg]
        if not rows:
            continue
        pairs = [(parsed[ids[i]]["a"], parsed[ids[i]]["b"]) for i in rows]
        if any(a < 1 or b > n or b <= a for a, b in pairs):
            raise ValueError(f"{recording} {leg}: a stride window is outside the recording")
        needed = {"pelvis": ["LASI", "RASI", "LPSI", "RPSI"],
                  "thigh": ["LASI", "RASI", "LPSI", "RPSI", side + "KNE", side + "KNEM"],
                  "shank": [side + "KNE", side + "KNEM", side + "ANK", side + "ANKM"],
                  "foot": [side + "HEE", side + "TOE"], "ankle": [side + "ANK", side + "ANKM"]}
        hip = hjc["right" if side == "R" else "left"]
        knee = (mk[side + "KNE"] + mk[side + "KNEM"]) / 2
        ankle = (mk[side + "ANK"] + mk[side + "ANKM"]) / 2
        pts = {"asi": pelvis_pts["asi"], "psi": pelvis_pts["psi"], "hip": sag(hip), "knee": sag(knee),
               "ankle": sag(ankle), "heel": sag(mk[side + "HEE"]), "toe": sag(mk[side + "TOE"])}
        seg = segment_angles(pts)
        alt_foot = angle_from_forward(sag(mk[side + "TOE"]) - sag(ankle))
        thigh_gt = angle_from_down(sag(mk[side + "KNE"] / 2 + mk[side + "KNEM"] / 2) - sag(mk[side + "GT"]))
        # frame-rate series resampled together on every stride's grid: (units, 150, k)
        stack = np.stack([seg["pelvis"], seg["thigh"], seg["shank"], seg["foot"], alt_foot, thigh_gt], axis=1)
        grid = um21.resample(stack, pairs)
        geo = np.stack([pts["ankle"][:, 0], pts["ankle"][:, 1], rt(ankle), pts["knee"][:, 0], pts["knee"][:, 1],
                        pts["hip"][:, 0], pts["hip"][:, 1], pts["heel"][:, 0], pts["heel"][:, 1], rt(mk[side + "HEE"]),
                        pts["toe"][:, 0], pts["toe"][:, 1], rt(mk[side + "TOE"])], axis=1)
        geo_g = um21.resample(geo, pairs)
        # per-stride gap gating (no filling): a column needs every frame of the stride window
        def stride_ok(cols):
            ok = np.ones(len(pairs), bool)
            why = [[] for _ in pairs]
            for j, (a, b) in enumerate(pairs):
                for m in cols:
                    if not window_ok(vis[m], a, b):
                        why[j].append(m)
                        ok[j] = False
            return ok, why
        gate = {k: stride_ok(v) for k, v in needed.items()}
        v2_pelvis = np.stack([v2[ids[i]][V2_COLUMNS["pelvis_tilt"]] for i in rows])
        pel_marker = _nan_rows(grid[:, :, 0].copy(), gate["pelvis"][0])
        diff_deg = np.degrees(v2_pelvis - pel_marker)
        pel_med = np.array([np.nanmedian(r) if np.isfinite(r).any() else np.nan for r in diff_deg])
        pelvis_pass = np.isfinite(pel_med) & (np.abs(pel_med) <= PELVIS_HOLD_DEG)
        pelvis_flag = np.isfinite(pel_med) & (np.abs(pel_med) > PELVIS_FLAG_DEG) & pelvis_pass
        thigh = _nan_rows(grid[:, :, 1].copy(), gate["thigh"][0])
        shank = _nan_rows(grid[:, :, 2].copy(), gate["shank"][0])
        foot = _nan_rows(grid[:, :, 3].copy(), gate["foot"][0])
        pelvis = np.where(pelvis_pass[:, None], v2_pelvis, np.nan)
        hip_a, knee_a, ankle_a = thigh - pelvis, thigh - shank, foot - shank
        spacing = np.array([(b - a) / FRAME_HZ for a, b in pairs]) / (N - 1)
        vel, _ = sa.derive_angular_velocities({"pelvis_tilt": pelvis, "thigh_angle": thigh, "shank_angle": shank,
                                               "foot_angle": foot}, spacing)
        cols = {"pelvis_tilt": pelvis, "hip_angle": hip_a, "knee_angle": knee_a, "ankle_angle": ankle_a,
                "thigh_angle": thigh, "shank_angle": shank, "foot_angle": foot,
                "pelvis_tilt_velocity": vel["pelvis_tilt_velocity"], "thigh_angle_velocity": vel["thigh_angle_velocity"],
                "shank_angle_velocity": vel["shank_angle_velocity"], "foot_angle_velocity": vel["foot_angle_velocity"]}
        for name, arr in cols.items():
            out[name][rows] = arr
        # ---- v2 comparison
        comp = {}
        for name, a_new in (("hip_angle", hip_a), ("knee_angle", knee_a), ("ankle_angle", ankle_a),
                            ("thigh_angle", thigh), ("shank_angle", shank)):
            a_v2 = np.stack([v2[ids[i]][V2_COLUMNS[name]] for i in rows])
            comp[name] = compare_to_v2(a_v2, a_new)
        ank_alt = _nan_rows(grid[:, :, 4].copy(), gate["foot"][0] & gate["ankle"][0]) - shank
        comp["ankle_angle_alt_ankle_to_toe_foot"] = compare_to_v2(
            np.stack([v2[ids[i]][V2_COLUMNS["ankle_angle"]] for i in rows]), ank_alt)
        thigh_gt_g = _nan_rows(grid[:, :, 5].copy(), gate["thigh"][0] & np.array([window_ok(vis[side + "GT"], a, b) for a, b in pairs]))
        d_gt = np.degrees(thigh - thigh_gt_g)
        summary["legs"][leg] = {"strides": len(rows), "v2_comparison": comp,
                                "pelvis_check": {"pass": int(pelvis_pass.sum()), "flagged_above_0.2_deg_kept": int(pelvis_flag.sum()), "held_above_1_deg": int(np.isfinite(pel_med).sum() - pelvis_pass.sum()),
                                                 "not_checked": int((~np.isfinite(pel_med)).sum()),
                                                 "median_diff_deg": _quantiles(pel_med)},
                                "hip_centre_vs_gt_marker_thigh_deg": _quantiles(d_gt),
                                "marker_gap_strides": {k: int((~v[0]).sum()) for k, v in gate.items()}}
        # ---- plate and centre of pressure
        f_raw = np.asarray(trial["forceplates"][side + "Force"][...], dtype=np.float64)
        c_raw = np.asarray(trial["forceplates"][side + "CoP"][...], dtype=np.float64)
        if f_raw.shape != (3, PLATE_PER_FRAME * n) or c_raw.shape != f_raw.shape:
            raise ValueError(f"{recording} {leg}: plate samples {f_raw.shape} != (3, {PLATE_PER_FRAME} x {n})")
        force, cop, loaded = mask_unloaded(f_raw, c_raw)
        del f_raw, c_raw
        m = loaded.size
        if t_plate is None:
            t_plate = np.arange(m) / (FRAME_HZ * PLATE_PER_FRAME)
        t_frame = np.arange(n) / FRAME_HZ
        runs = loaded_runs(loaded)
        reg = {"loaded_fraction": float(loaded.mean()), "loaded_runs": len(runs)}
        leg_sum = summary["legs"][leg]
        leg_sum["plate"] = reg
        cop_ok = gate["ankle"][0] & gate["foot"][0]
        if not runs:
            reg["held_reason"] = "no loaded stance run of 0.3 s or longer"
            _record_hold(ledger, ids, rows, ["cop"], reg["held_reason"])
            continue
        ankle_f_plate = np.interp(t_plate, t_frame, pts["ankle"][:, 0])
        choice, axis_stats = choose_plate_axis(cop[:2], ankle_f_plate, runs)
        reg["axis_stats"] = axis_stats
        if choice is None:
            reg["held_reason"] = "plate axis could not be determined"
            _record_hold(ledger, ids, rows, ["cop"], reg["held_reason"])
            continue
        axis, sign = choice
        slope = axis_stats[axis]["median_slope"]
        reg.update({"axis": axis, "sign": sign, "ankle_vs_plate_axis_slope": slope,
                    "axis_median_abs_r": axis_stats[axis]["median_abs_r"],
                    "other_axis_median_abs_r": axis_stats[1 - axis]["median_abs_r"]})
        runs_frames = [(lo // PLATE_PER_FRAME, hi // PLATE_PER_FRAME) for lo, hi in runs]
        belt, belt_each = belt_slope_deg(pts["heel"], runs_frames)
        alpha = float(np.sign(belt) * nominal_slope_deg) if (nominal_slope_deg and belt) else 0.0
        reg.update({"nominal_slope_deg": nominal_slope_deg, "belt_slope_from_heel_path_deg": belt,
                    "tilt_used_deg": alpha})
        tilt = np.radians(alpha)
        cop_lab0 = plate_to_person(cop[:2], axis, sign, tilt)            # (3, m) forward, up, right; no shift
        frc_lab = force_to_person(force, axis, sign, tilt)
        # midpoint rule (C03 / adapter): reported for comparison and used for the lateral shift
        st = np.zeros(m, bool)
        for run in runs:
            lo, hi = central(run)
            st[lo:hi] = True
        mid_f = np.interp(t_plate, t_frame, (pts["heel"][:, 0] + pts["toe"][:, 0]) / 2)
        low_u = np.interp(t_plate, t_frame, np.fmin(pts["heel"][:, 1], pts["toe"][:, 1]))
        mid_r = np.interp(t_plate, t_frame, (rt(mk[side + "HEE"]) + rt(mk[side + "TOE"])) / 2)
        sel = st & np.isfinite(mid_f) & np.isfinite(cop_lab0[0])
        mid_rule = None
        d_lat = None
        if sel.sum() > 100:
            mid_rule = {"forward": float(np.mean(mid_f[sel]) - np.mean(cop_lab0[0][sel])),
                        "up": float(np.nanmedian(low_u[sel]) - np.nanmedian(cop_lab0[1][sel]))}
            selr = sel & np.isfinite(mid_r)
            d_lat = float(np.mean(mid_r[selr]) - np.mean(cop_lab0[2][selr])) if selr.sum() > 100 else None
        reg["midpoint_rule_shift_m"] = mid_rule
        # lateral sign check: per-run mean lateral position, plate versus markers
        lr = [(np.nanmean(cop_lab0[2][central(r)[0]:central(r)[1]]), np.nanmean(mid_r[central(r)[0]:central(r)[1]]))
              for r in runs]
        lr = np.array([x for x in lr if np.isfinite(x).all()])
        reg["lateral_corr_plate_vs_markers"] = (float(np.corrcoef(lr[:, 0], lr[:, 1])[0, 1]) if len(lr) > 5 and np.std(lr[:, 0]) > 0 and np.std(lr[:, 1]) > 0 else None)
        # grid versions per stride
        pos = np.array([PLATE_PER_FRAME * ((a - 1) + np.arange(N) * (b - a) / (N - 1)) for a, b in pairs])
        cop_g = np.stack([plate_at(cop[0], pos), plate_at(cop[1], pos)])              # (2, units, 150)
        frc_g = np.stack([plate_at(frc_lab[k], pos) for k in range(3)])               # (3, units, 150) lab, N
        cop_lab_g = plate_to_person(cop_g, axis, sign, tilt)                           # (3, units, 150)
        if debug is not None:  # read-only probes: the inputs of the registration, nothing else changes
            debug[leg] = {"cop_g": cop_g, "fp_g": np.stack([plate_at(force[k], pos) for k in range(3)]), "axis": axis,
                          "sign": sign, "tilt": tilt, "geo_g": geo_g, "foot": foot, "cop_ok": cop_ok, "d_lat": d_lat,
                          "mid_rule": mid_rule, "mass": mass_kg, "geo_ok": gate["thigh"][0] & gate["shank"][0],
                          "mom": {j: np.stack([v2[ids[i]][V2_COLUMNS[j + "_moment"]] for i in rows]) for j in ("hip", "knee", "ankle")}}
        # ---- moment fit (hip and knee only); ankle held out
        mom = {j: np.stack([v2[ids[i]][V2_COLUMNS[j + "_moment"]] for i in rows]) for j in ("hip", "knee", "ankle")}
        geo_ok = gate["thigh"][0] & gate["shank"][0]
        per_kg = None if not mass_kg else frc_g / mass_kg
        reg["fit"] = None
        shift = None
        if per_kg is not None:
            use = (np.isfinite(per_kg).all(axis=0) & np.isfinite(cop_lab_g).all(axis=0) & geo_ok[:, None]
                   & np.isfinite(geo_g[:, :, 3:7]).all(axis=2) & np.isfinite(mom["hip"]) & np.isfinite(mom["knee"])
                   & (per_kg[1] > FIT_MIN_FORCE_BW * GRAVITY))
            if use.sum() >= 200:
                hip_fu, knee_fu = geo_g[:, :, 5:7], geo_g[:, :, 3:5]
                d, nfit, cond = fit_shifts(cop_lab_g[:2, use], per_kg[:2, use], hip_fu[use].T, knee_fu[use].T,
                                           mom["hip"][use], mom["knee"][use])
                if mid_rule is not None:
                    # the up (plate-normal) shift is not identifiable from the moments (probe 2026-11-23: it left the
                    # centre of pressure 3-30 cm above the foot); it comes from the foot-on-belt marker rule and only
                    # the forward shift is fitted from the moments
                    dy_used = mid_rule["up"]
                    dx_used, nfit = fit_forward_shift(cop_lab_g[:2, use], per_kg[:2, use], hip_fu[use].T, knee_fu[use].T,
                                                      mom["hip"][use], mom["knee"][use], dy_used)
                    up_source = "foot-on-belt marker rule (lowest heel/toe marker height in mid-stance)"
                else:
                    dx_used, dy_used = float(d[0]), float(d[1])
                    up_source = "moment fit (marker rule unavailable)"
                shift = (float(dx_used), float(dy_used), d_lat if d_lat is not None else 0.0)
                reg["fit"] = {"forward_m": shift[0], "up_m": shift[1], "lateral_m": d_lat, "samples": nfit,
                              "condition_number": cond, "up_source": up_source,
                              "free_two_parameter_fit_forward_m": float(d[0]), "free_two_parameter_fit_up_m": float(d[1])}
                # per-stride spread of the forward shift (up fixed)
                per = []
                for j in range(len(rows)):
                    uj = use[j]
                    if uj.sum() >= 30:
                        if mid_rule is not None:
                            per.append([fit_forward_shift(cop_lab_g[:2, j][:, uj], per_kg[:2, j][:, uj], hip_fu[j][uj].T,
                                                          knee_fu[j][uj].T, mom["hip"][j][uj], mom["knee"][j][uj], dy_used)[0], dy_used])
                        else:
                            dj, _, cj = fit_shifts(cop_lab_g[:2, j][:, uj], per_kg[:2, j][:, uj], hip_fu[j][uj].T,
                                                   knee_fu[j][uj].T, mom["hip"][j][uj], mom["knee"][j][uj])
                            per.append(dj)
                per = np.array(per)
                reg["fit"]["per_stride_forward_m"] = _quantiles(per[:, 0]) if len(per) else None
                reg["fit"]["per_stride_up_m"] = _quantiles(per[:, 1]) if len(per) else None
                # hold-out: ankle moment predicted from the fitted centre of pressure
                ank_fu = geo_g[:, :, 0:2]
                shifted = cop_lab_g[:2] + np.array(shift[:2])[:, None, None]
                use_a = use & np.isfinite(mom["ankle"]) & np.isfinite(ank_fu).all(axis=2)
                pred = joint_moment_from_force(shifted[:, use_a], per_kg[:2, use_a], ank_fu[use_a].T, "ankle")
                pred0 = joint_moment_from_force(cop_lab_g[:2, use_a], per_kg[:2, use_a], ank_fu[use_a].T, "ankle")
                obs = mom["ankle"][use_a]
                peak = float(np.percentile(np.abs(obs), 95)) if obs.size else None
                reg["ankle_holdout"] = {
                    "samples": int(use_a.sum()),
                    "r": float(np.corrcoef(pred, obs)[0, 1]) if use_a.sum() > 10 else None,
                    "rmse_Nm_kg": float(np.sqrt(np.mean((pred - obs) ** 2))) if use_a.sum() else None,
                    "rmse_no_shift_Nm_kg": float(np.sqrt(np.mean((pred0 - obs) ** 2))) if use_a.sum() else None,
                    "p95_abs_observed_Nm_kg": peak,
                    "slope_pred_vs_observed": float(np.polyfit(obs, pred, 1)[0]) if use_a.sum() > 10 else None}
            else:
                reg["fit"] = {"not_fitted": f"only {int(use.sum())} usable samples"}
        else:
            reg["fit"] = {"not_fitted": "body mass unavailable (never invented)"}
        # ---- foot-frame centre of pressure
        if shift is None:
            reg["held_reason"] = "plate shift could not be fitted"
            _record_hold(ledger, ids, rows, ["cop"], reg["held_reason"])
            continue
        shifted_lab = cop_lab_g + np.array(shift)[:, None, None]
        ank_g = np.stack([geo_g[:, :, 0], geo_g[:, :, 1], geo_g[:, :, 2]])
        cop_ok_grid = cop_ok[:, None] & np.isfinite(foot[:, :])
        pt = np.where(cop_ok_grid[None], shifted_lab, np.nan)
        cf = foot_frame(pt, ank_g, foot, leg)                                         # (3, units, 150)
        heel_f = foot_frame(np.stack([geo_g[:, :, 7], geo_g[:, :, 8], geo_g[:, :, 9]]), ank_g, foot, leg)
        toe_f = foot_frame(np.stack([geo_g[:, :, 10], geo_g[:, :, 11], geo_g[:, :, 12]]), ank_g, foot, leg)
        # endpoint check (not used in the fit): first loaded sample of the stance that starts the stride against the
        # heel marker, last sample of that stance against the toe marker, at two load thresholds
        tol = 0.03
        reg["endpoint_check"] = endpoint_report(cf[0], heel_f[0], toe_f[0], None, tol, f"{LOAD_THRESHOLD_N:.0f} N",
                                                vert=cf[1], heel_vert=heel_f[1], toe_vert=toe_f[1])
        if per_kg is not None:
            reg["endpoint_check_0p2bw"] = endpoint_report(cf[0], heel_f[0], toe_f[0], per_kg[1] / GRAVITY > 0.2, tol,
                                                          "0.2 body weight", vert=cf[1], heel_vert=heel_f[1], toe_vert=toe_f[1])
        # plate assignment check: this leg's plate loaded at this leg's heel strikes, the other plate not
        reg["plate_assignment"] = None  # filled by the caller (needs both plates and the events)
        reg["_loaded"] = loaded
        # the centre of pressure outputs
        grid_cop = {"cop_anterior": cf[0], "cop_vertical": cf[1], "cop_lateral": cf[2]}
        for name, arr in grid_cop.items():
            cop_unheld[name][rows] = arr
        reg["_rows"] = rows
        reg["_ids"] = [ids[i] for i in rows]
    # plate assignment (both legs' loaded masks are known only now)
    legs_loaded = {leg: summary["legs"][leg]["plate"].get("_loaded") for leg in summary["legs"]}
    for side, leg in (("R", "right"), ("L", "left")):
        reg = summary["legs"].get(leg, {}).get("plate")
        if reg is None or reg.get("_loaded") is None:
            continue
        other = "left" if leg == "right" else "right"
        hs = np.asarray(trial["events"][side + "HS"][...]).ravel()
        hs = hs[np.isfinite(hs)].astype(int)
        same, oth, tot = 0, 0, 0
        for f in hs:
            if f < 1 or f + 6 > n:
                continue
            seg_s = slice(PLATE_PER_FRAME * (f - 1), PLATE_PER_FRAME * (f + 5))
            tot += 1
            same += bool(reg["_loaded"][seg_s].any())
            lo_ = legs_loaded.get(other)
            oth += bool(lo_ is not None and lo_[seg_s].any())
        reg["plate_assignment"] = {"heel_strikes": tot,
                                   "same_plate_loaded_within_5_frames_fraction": same / tot if tot else None,
                                   "other_plate_loaded_in_same_window_fraction": oth / tot if tot else None}
    # gate per leg
    for leg in list(summary["legs"]):
        reg = summary["legs"][leg]["plate"]
        rows = reg.pop("_rows", None)
        reg.pop("_ids", None)
        reg.pop("_loaded", None)
        if rows is None:
            summary["legs"][leg]["cop_gate"] = {"verdict": "held", "reasons": [reg.get("held_reason", "not computed")]
                                                + ([HELD_UNTIL_EXPLAINED[recording]] if recording in HELD_UNTIL_EXPLAINED else [])}
            continue
        reasons = cop_gate_reasons(reg, recording)
        summary["legs"][leg]["cop_gate"] = {"verdict": "pass" if not reasons else "held", "reasons": reasons,
                                             "gate": GATE, "label": COP_LABEL if not reasons else None}
        r_idx = [i for i, o in enumerate(ids) if parsed[o]["leg"] == leg]
        for name in COP_COLUMNS:
            if not reasons:
                cop_held[name][r_idx] = cop_unheld[name][r_idx]
        if reasons:
            _record_hold(ledger, ids, r_idx, ["cop"], "; ".join(reasons))
    # per-stride ledger of missing columns
    for i, oid in enumerate(ids):
        missing = {c: "marker gap or check failed" for c in OUT_COLUMNS if not np.isfinite(out[c][i]).any()}
        if missing:
            ledger["strides"].setdefault(oid, {}).setdefault("columns_all_missing", sorted(missing))
    return ids, sides, {**out, **cop_held}, cop_unheld, summary, ledger


def cop_gate_reasons(reg, recording):
    """Reasons a leg's centre of pressure is held (empty list: published, labelled "estimated plate position").
    D-UM21-S02-1 = A: pass only if the hold-out ankle moment has r >= 0.95 and the toe-off end (CoP at the last loaded
    sample against the toe marker, 0.2 body weight threshold) is within 4 cm in at least 95 percent of strides.
    The heel end is reported only. Plate assignment and lateral sign are kept as sanity checks."""
    reasons = []
    if recording in HELD_UNTIL_EXPLAINED:
        reasons.append(HELD_UNTIL_EXPLAINED[recording])
    h = reg.get("ankle_holdout")
    if not h or h.get("r") is None:
        reasons.append("hold-out ankle moment not computed")
    elif h["r"] < GATE["ankle_holdout_r_min"]:
        reasons.append(f"hold-out ankle moment r = {h['r']:.3f} below {GATE['ankle_holdout_r_min']}")
    e = reg.get("endpoint_check_0p2bw")
    v = None if not e else e.get("fraction_within_4cm_toe")
    if v is None:
        reasons.append("toe-off end not checkable")
    elif v < GATE["toe_endpoint_fraction_min"]:
        reasons.append(f"toe-off end within 4 cm in {v*100:.0f} percent of strides (needs 95)")
    pa = reg.get("plate_assignment") or {}
    if (pa.get("same_plate_loaded_within_5_frames_fraction") or 0) < GATE["plate_assignment_fraction_min"]:
        reasons.append("plate not loaded at this leg's heel strikes")
    lc = reg.get("lateral_corr_plate_vs_markers")
    if lc is not None and lc < -0.3:
        reasons.append(f"lateral sign disagrees with markers (r = {lc:.2f})")
    return reasons


def endpoint_report(ant, heel_ant, toe_ant, extra_mask, tol, label, max_start=8, vert=None, heel_vert=None, toe_vert=None):
    """ant/heel_ant/toe_ant: (strides, 150) foot-frame anterior positions. Per stride, the first contiguous run of
    finite (and extra_mask) samples is the stance that starts the stride; its first sample is compared with the heel
    marker and its last sample with the toe marker. Skipped (not checked): the run starts after max_start samples
    (stance not at the stride start) or runs to the last sample (no toe-off inside the window)."""
    eh, et, skip, vh, vt = [], [], 0, [], []
    for j in range(ant.shape[0]):
        ok = np.isfinite(ant[j]) & np.isfinite(heel_ant[j]) & np.isfinite(toe_ant[j])
        if extra_mask is not None:
            ok &= extra_mask[j]
        idx = np.flatnonzero(ok)
        if idx.size < 10:
            continue
        k0 = int(idx[0])
        k1 = k0
        while k1 + 1 < ant.shape[1] and ok[k1 + 1]:
            k1 += 1
        if k0 > max_start or k1 >= ant.shape[1] - 1:
            skip += 1
            continue
        eh.append(float(ant[j, k0] - heel_ant[j, k0]))
        et.append(float(ant[j, k1] - toe_ant[j, k1]))
        if vert is not None:
            vh.append(float(vert[j, k0] - heel_vert[j, k0]))
            vt.append(float(vert[j, k1] - toe_vert[j, k1]))
    eh, et = np.array(eh), np.array(et)
    frac = lambda x, t: float(np.mean(np.abs(x) <= t)) if len(x) else None
    return {"threshold": label, "strides_checked": int(len(eh)), "strides_not_checked": skip,
            "first_loaded_minus_heel_m": _quantiles(eh), "last_loaded_minus_toe_m": _quantiles(et),
            "fraction_within_tolerance_heel": frac(eh, tol), "fraction_within_tolerance_toe": frac(et, tol),
            "vertical_offset_heel_m": _quantiles(vh), "vertical_offset_toe_m": _quantiles(vt),
            "fraction_within_4cm_heel": frac(eh, 0.04), "fraction_within_4cm_toe": frac(et, 0.04),
            "fraction_within_5cm_heel": frac(eh, 0.05), "fraction_within_5cm_toe": frac(et, 0.05), "tolerance_m": tol}


def _record_hold(ledger, ids, rows, what, reason):
    for i in rows:
        ledger["strides"].setdefault(ids[i], {}).setdefault("held", {})[",".join(what)] = reason


def compare_to_v2(a_v2, a_new):
    """Agreement of new angles with the v2 angles on the strides where both are present: pooled correlation,
    median per-stride offset (v2 minus new, degrees), the spread of per-stride offsets and median within-stride
    correlation."""
    both = np.isfinite(a_v2) & np.isfinite(a_new)
    full = both.all(axis=1)
    if full.sum() < 2:
        return {"strides_compared": int(full.sum())}
    x, y = a_v2[full], a_new[full]
    off = np.degrees(np.median(x - y, axis=1))
    r_in = [np.corrcoef(x[j], y[j])[0, 1] for j in range(len(x)) if np.std(x[j]) > 0 and np.std(y[j]) > 0]
    pooled = np.corrcoef(x.ravel(), y.ravel())[0, 1] if np.std(x) > 0 and np.std(y) > 0 else None
    return {"strides_compared": int(full.sum()), "pooled_r": None if pooled is None else float(pooled),
            "median_within_stride_r": float(np.median(r_in)) if r_in else None,
            "offset_deg": _quantiles(off), "rms_after_removing_stride_offset_deg": float(np.degrees(np.sqrt(np.mean(
                (x - y - np.median(x - y, axis=1, keepdims=True)) ** 2))))}


# =========================================================== output tables
def composition_error(out):
    """Largest |thigh - pelvis - hip|, |thigh - knee - shank|, |shank + ankle - foot| over finite samples."""
    errs = []
    for a, b, c in (("thigh_angle", "pelvis_tilt", "hip_angle"), ):
        errs.append(np.nanmax(np.abs(out[a] - out[b] - out[c])) if np.isfinite(out[c]).any() else 0.0)
    errs.append(np.nanmax(np.abs(out["thigh_angle"] - out["knee_angle"] - out["shank_angle"])) if np.isfinite(out["knee_angle"]).any() else 0.0)
    errs.append(np.nanmax(np.abs(out["shank_angle"] + out["ankle_angle"] - out["foot_angle"])) if np.isfinite(out["ankle_angle"]).any() else 0.0)
    return float(max(errs))


# =========================================================== independent method re-implemented from the ESML project
# Re-implemented here (nothing imported or copied as code; the method and its constants are credited per function):
# source method: energy-shaping-ML project, code/training/cop_reference_um21.py (read-only reference, 2026-09-25).
# It is an independent cross-check of the plate registration above; its leave-subject-out donor step needs all
# subjects and is exercised on synthetic data only in this version.
PIG_MARKER_RADIUS_M = 0.007          # cop_reference_um21.PIG_MARKER_RADIUS_M (Plug-in Gait default 14 mm marker)
CONTACT_BW = 0.2                     # cop_reference_um21.CONTACT_BW
REGISTRATION_MIN_BW = 0.5            # cop_reference_um21.REGISTRATION_MIN_BW
REGISTRATION_MAX_IQR_M = 0.02        # cop_reference_um21.REGISTRATION_MAX_IQR_M
MIN_DONOR_SUBJECTS = 5               # cop_reference_um21.MIN_DONOR_SUBJECTS
FOOT_FLAT_MAX_PITCH_RATE = 0.5       # rad/s, cop_reference_um21.FOOT_FLAT_MAX_PITCH_RATE
PUSH_OFF_MIN_BW = 0.3                # cop_reference_um21.PUSH_OFF_MIN_BW
PUSH_OFF_MAX_PITCH_RATE = -1.5       # rad/s, cop_reference_um21.PUSH_OFF_MAX_PITCH_RATE
ROCKER_ABOVE_BELT_M = 0.012          # cop_reference_um21.ROCKER_ABOVE_BELT_M (30 GT21 subject-sides; not UM21-measured)
STEADY_SPEEDS = {"s0x8", "s1", "s1x2"}
TREAD_SPEEDS = {"s0x8", "s1", "s1x2", "a0x2", "a0x5", "d0x2", "d0x5"}
# NOT ported: ANKLE_DROP_ALONG_SHANK_M = 0.0357 (a GT23 model constant, per the coordinator's instruction).


def pig_ankle_centre(knee_centre, ank, tib, offset, toward_tib=False):
    """Plug-in Gait chord-function ankle centre per row. Credit: cop_reference_um21.pig_ankle_centre. |J - ANK| =
    offset (= ankle width / 2 + marker radius), J in the plane of knee centre, ANK and TIB, right angle
    knee centre - J - ANK, on the side opposite TIB (medial for a lateral TIB)."""
    a = knee_centre - ank
    length = np.linalg.norm(a, axis=1, keepdims=True)
    e1 = a / length
    normal = np.cross(a, tib - ank)
    e2 = np.cross(normal / np.linalg.norm(normal, axis=1, keepdims=True), e1)
    c = offset / length
    return ank + offset * (c * e1 + (1.0 if toward_tib else -1.0) * np.sqrt(1.0 - c ** 2) * e2)


def belt_frame(seg, fwd, incline_rad, names=("ankle", "midpoint", "pig", "heel", "toe", "met1", "met5")):
    """Markers in belt coordinates (along-belt b, belt normal n), forward positive. Credit:
    cop_reference_um21._walking_frame (forward here is the pelvis heading, not marker +y or heel-to-toe sign)."""
    c, s = np.cos(incline_rad), np.sin(incline_rad)
    out = {}
    for name in names:
        if name in seg:
            x, z = np.asarray(seg[name], float) @ fwd, np.asarray(seg[name], float) @ UP
            out[name + "_b"], out[name + "_n"] = x * c + z * s, -x * s + z * c
    out["line_pitch_b"] = np.arctan2(out["toe_n"] - out["heel_n"], out["toe_b"] - out["heel_b"])
    return out


def sole_reference(level, fwd):
    """Foot-line pitch offset and heights above the belt from level-treadmill segments. Credit:
    cop_reference_um21.sole_reference. level: {collection id: segment}; the belt surface is the push-off rotation
    centre of the rigid foot (heel, toe, 1st and 5th metatarsal; velocities relative to the belt) less
    ROCKER_ABOVE_BELT_M. Also the Plug-in Gait ankle centre minus the malleolar midpoint at loaded foot-flat, along
    the foot axis and normal to the sole, and the fraction of samples whose chord root is nearer the medial marker."""
    pitch, ankle_n, pig_n, pig_b, pig_dn, medial, icr = [], [], [], [], [], [], []
    for cid, seg in level.items():
        n = min(len(seg["ankle"]), len(seg["vgrf_bw"]))
        fr = belt_frame(seg, fwd, 0.0)
        v, p = seg["vgrf_bw"][:n], fr["line_pitch_b"][:n]
        w = np.gradient(p) * FRAME_HZ
        flat = (v > REGISTRATION_MIN_BW) & (np.abs(w) < FOOT_FLAT_MAX_PITCH_RATE) & np.isfinite(p)
        pitch.append(p[flat]); ankle_n.append(fr["ankle_n"][:n][flat]); pig_n.append(fr["pig_n"][:n][flat])
        pig_b.append((fr["pig_b"] - fr["midpoint_b"])[:n][flat]); pig_dn.append((fr["pig_n"] - fr["midpoint_n"])[:n][flat])
        medial.append(seg["pig_medial_root"][:n][flat])
        if cid.rsplit("_", 2)[-2] not in STEADY_SPEEDS:
            continue
        belt = -np.nanmedian(np.gradient(fr["heel_b"][:n])[flat]) * FRAME_HZ
        push = (v > PUSH_OFF_MIN_BW) & (w < PUSH_OFF_MAX_PITCH_RATE)
        for name in (m for m in ("heel", "toe", "met1", "met5") if m + "_b" in fr):
            vel = np.gradient(fr[name + "_b"][:n]) * FRAME_HZ + belt
            icr.append(fr[name + "_n"][:n][push] + vel[push] / w[push])
    pitch, ankle_n, pig_n, pig_b, pig_dn, medial, icr = (np.concatenate(x) if x else np.array([])
                                                         for x in (pitch, ankle_n, pig_n, pig_b, pig_dn, medial, icr))
    if np.isfinite(pitch).sum() < 100 or np.isfinite(icr).sum() < 100:
        return {}
    belt_n = float(np.nanmedian(icr)) - ROCKER_ABOVE_BELT_M
    beta = float(np.nanmedian(pitch))
    phi = pitch - beta
    return dict(sole_line_pitch_rad=beta, belt_height_m=belt_n,
                ankle_height_m=float(np.nanmedian(ankle_n)) - belt_n, pig_ankle_height_m=float(np.nanmedian(pig_n)) - belt_n,
                pig_minus_midpoint_foot_axis_m=float(np.nanmedian(pig_b * np.cos(phi) + pig_dn * np.sin(phi))),
                pig_minus_midpoint_sole_normal_m=float(np.nanmedian(-pig_b * np.sin(phi) + pig_dn * np.cos(phi))),
                pig_root_nearer_medial_marker=float(np.mean(medial)) if len(medial) else float("nan"),
                foot_flat_samples=int(np.isfinite(pitch).sum()), push_off_samples=int(np.isfinite(icr).sum()))


def esml_plate_sign(parts, fwd, incline_deg):
    """Sign of the plate AP axis along the walking direction (plate CoP vs ankle marker). Credit:
    cop_reference_um21.plate_sign."""
    th = np.radians(incline_deg)
    cop, ab = [], []
    for seg in parts:
        n = min(len(seg["ankle"]), len(seg["vgrf_bw"]))
        a = belt_frame(seg, fwd, th)["ankle_b"][:n]
        m = (seg["vgrf_bw"][:n] > REGISTRATION_MIN_BW) & np.isfinite(a) & np.isfinite(seg["cop_ap"][:n])
        cop.append(seg["cop_ap"][:n][m]); ab.append(a[m])
    cop, ab = np.concatenate(cop), np.concatenate(ab)
    if len(cop) < 200:
        return float("nan"), int(len(cop))
    return float(np.sign(np.corrcoef(cop, ab)[0, 1])), int(len(cop))


def moment_registration(parts, fwd, incline_deg, mass, ref, sigma):
    """Plate-to-marker offset of one recording from its own ankle moment about the Plug-in Gait ankle centre. Credit:
    cop_reference_um21.moment_registration. median of (sigma*cop - J_b) - (-tau*m - H_J*f_sign*F_b)/F_n over samples
    above 0.5 BW; CoP along the belt = sigma*cop - offset. Uses this recording's own moment: a diagnostic here."""
    th = np.radians(incline_deg)
    rows, votes, heel = [], [], []
    for seg in parts:
        n = min(len(seg["ankle"]), len(seg["vgrf_bw"]), len(seg["tau"]))
        fr = belt_frame(seg, fwd, th)
        v, cop, jb, mb = seg["vgrf_bw"][:n], seg["cop_ap"][:n], fr["pig_b"][:n], fr["midpoint_b"][:n]
        m = (v > REGISTRATION_MIN_BW) & np.isfinite(jb) & np.isfinite(mb) & np.isfinite(cop)
        rows.append(np.c_[cop[m], jb[m], seg["f_ap"][:n][m], seg["f_n"][:n][m], seg["tau"][:n][m], mb[m]])
        ld = v > CONTACT_BW
        on = np.flatnonzero(ld[1:] & ~ld[:-1]) + 1
        off = np.flatnonzero(~ld[1:] & ld[:-1]) + 1
        for a in on:
            b = off[off > a]
            if len(b) and b[0] - a > 10:
                h = (b[0] - a) // 2
                votes.append(np.sign(np.mean(seg["f_ap"][a + h:b[0]]) - np.mean(seg["f_ap"][a:a + h])))
        heel.append((fr, seg, on[on > 1]))
    X = np.concatenate(rows)
    f_sign = float(np.sign(np.median(votes))) if votes else 1.0
    db_raw = sigma * X[:, 0] - X[:, 1]
    db_id = (-X[:, 4] * mass - ref["pig_ankle_height_m"] * f_sign * X[:, 2]) / X[:, 3]
    offset = float(np.median(db_raw - db_id))
    iqr = float(np.subtract(*np.percentile(db_raw - offset - db_id, [75, 25])))
    H = ref["ankle_height_m"]
    c_heel = []
    for fr, seg, on in heel:
        phi = fr["line_pitch_b"][on] - ref["sole_line_pitch_rad"]
        s_on = (sigma * seg["cop_ap"][on] - fr["ankle_b"][on] - offset - H * np.sin(phi)) / np.cos(phi)
        s_heel = (fr["heel_b"][on] - fr["ankle_b"][on]) * np.cos(phi) + (fr["heel_n"][on] - fr["ankle_n"][on]) * np.sin(phi)
        c_heel.append(s_on - s_heel)
    return dict(offset_m=offset, residual_iqr_m=iqr, corr=float(np.corrcoef(db_raw, db_id)[0, 1]), force_sign=f_sign,
                samples=int(len(X)), donor=bool(iqr <= REGISTRATION_MAX_IQR_M),
                pig_minus_midpoint_b_m=float(np.median(X[:, 1] - X[:, 5])),
                heel_strike_cop_minus_heel_marker_m=float(np.nanmedian(np.concatenate(c_heel))) if c_heel else float("nan"))


def leave_subject_out_offsets(meta, donor_subjects=None):
    """Offset of each recording = median over the OTHER subjects of their own-moment offsets in the same condition,
    walking direction and plate sign (donors need residual IQR <= 20 mm, at least 5 donor subjects). Credit:
    cop_reference_um21.leave_subject_out_offsets and .condition. meta: {subject: {"recordings": {key: {...}}}}."""
    condition = lambda key: key if key.startswith("Tread_") else key.split("_")[0]
    donors = {}
    for subj, sm in meta.items():
        if donor_subjects is not None and subj not in donor_subjects:
            continue
        for key, rec in sm.get("recordings", {}).items():
            diag = rec.get("moment_diagnostic")
            if diag and diag["donor"] and rec.get("status") != "excluded":
                donors.setdefault((condition(key), rec["walk_direction"], rec["plate_sign"]), {}).setdefault(subj, []).append(diag["offset_m"])
    for subj, sm in meta.items():
        for key, rec in sm.get("recordings", {}).items():
            if rec.get("status") == "excluded":
                continue
            group = (condition(key), rec["walk_direction"], rec["plate_sign"])
            per = {t: float(np.median(v)) for t, v in donors.get(group, {}).items() if t != subj}
            if len(per) < MIN_DONOR_SUBJECTS:
                rec.update(status="excluded", reason=f"{len(per)} donor subjects for {group[0]} < {MIN_DONOR_SUBJECTS}")
                continue
            rec.update(status="registered", condition=group[0], registration_offset_m=float(np.median(list(per.values()))),
                       registration_donors=sorted(per))
            if rec.get("moment_diagnostic"):
                rec["moment_diagnostic"]["used_minus_own_moment_offset_m"] = rec["registration_offset_m"] - rec["moment_diagnostic"]["offset_m"]


def _hdf_text(handle, ref):
    return handle[ref][()].tobytes().decode("utf-16-le")


def tread_segments(handle, group, n):
    """[(suffix, start, end)] 1-based frames of the treadmill speed segments (events/tasks and cutPoints), or the
    whole recording. Credit: cop_reference_um21.recordings (treadmill branch)."""
    ev = group["events"] if "events" in group else None
    if ev is not None and "tasks" in ev and "cutPoints" in ev:
        tasks = [_hdf_text(handle, r) for r in ev["tasks"][()].ravel()]
        cut = ev["cutPoints"][()].T
        return [(f"{speed}_seg{i + 1:02d}", max(1, int(round(cut[i, 0]))), min(int(round(cut[i, 1])), n))
                for i, speed in enumerate(tasks) if i < len(cut) and speed in TREAD_SPEEDS]
    return [("full_seg01", 1, n)]


def participant_value(handle, subject, name):
    """A named numeric value of Streaming/<subject>/ParticipantDetails (e.g. 'RightAnkleWidth' in mm), or None."""
    group = handle[f"Streaming/{subject}"]
    cells = group["ParticipantDetails"][()]

    def val(ref):
        a = handle[ref][()]
        cls = handle[ref].attrs.get("MATLAB_class", b"")
        if (cls.decode("ascii", "replace") if isinstance(cls, bytes) else str(cls)) == "char":
            return "".join(chr(c) for c in np.asarray(a).ravel())
        return np.asarray(a, float).ravel()
    for r in range(cells.shape[1]):
        nm, value = val(cells[0, r]), val(cells[1, r])
        if nm == name and np.size(value) == 1:
            return float(value[0])
    return None


def leg_segment(trial, side, start, end, body_weight_n, ankle_width_m, cop_axis=1):
    """Raw channels of frames start..end for one leg at frame rate (plate sampled at 10 x frame). Credit:
    cop_reference_um21._segment (forward/AP plate axis is a parameter here, default 1 as there)."""
    sl = slice(start - 1, end)

    def mk(name):
        m = trial["markers"][name][:, sl]
        xyz = m[:3].T.astype(np.float64)
        xyz[m[3] != 1] = np.nan
        return xyz
    mark = {k: mk(side + k) for k in ("ANK", "ANKM", "HEE", "TOE", "1M", "5M", "KNE", "KNEM", "TIB")}
    n_force = trial["forceplates"][side + "Force"].shape[1]
    idx = np.arange(start - 1, end) * PLATE_PER_FRAME
    idx = idx[idx < n_force]
    force = trial["forceplates"][side + "Force"][:, idx].T
    knee, mid = (mark["KNE"] + mark["KNEM"]) / 2, (mark["ANK"] + mark["ANKM"]) / 2
    off = 0.5 * ankle_width_m + PIG_MARKER_RADIUS_M
    pig = pig_ankle_centre(knee, mark["ANK"], mark["TIB"], off)
    other = pig_ankle_centre(knee, mark["ANK"], mark["TIB"], off, toward_tib=True)
    medial = np.linalg.norm(pig - mark["ANKM"], axis=1) < np.linalg.norm(other - mark["ANKM"], axis=1)
    return dict(ankle=mid, midpoint=mid, pig=pig, pig_medial_root=medial, heel=mark["HEE"], toe=mark["TOE"],
                met1=mark["1M"], met5=mark["5M"], cop_ap=trial["forceplates"][side + "CoP"][cop_axis, idx] / 1000.0,
                f_ap=force[:, cop_axis], f_n=-force[:, 2], vgrf_bw=-force[:, 2] / body_weight_n,
                tau=trial["jointMoments"][side + "AnkleMoment"][0, sl])


# =========================================================== job
def recording_heading(trial):
    def mk(name):
        m = trial["markers"][name][...]
        xyz = m[:3].T.astype(np.float64).copy()
        xyz[m[3] != 1] = np.nan
        return xyz
    return heading((mk("LASI") + mk("RASI")) / 2, (mk("LPSI") + mk("RPSI")) / 2)


def esml_cross_check(handle, subject, cond, trial, mass, legs_summary):
    """Independent cross-check per leg with the re-implemented ESML method (see the port section): subject level-
    treadmill reference, plate sign, own-moment offset, Plug-in Gait ankle centre minus malleolar midpoint. The
    comparison number is the plate offset along the belt: mine = -(forward shift * cos(tilt) + up shift * sin(tilt)),
    theirs = offset_m (CoP along the belt = sigma * plate - offset). Errors are recorded, never raised."""
    out = {}
    fwd = recording_heading(trial)
    signed = -um21.NOMINAL_SLOPE_DEG[cond] if cond.startswith("d") else um21.NOMINAL_SLOPE_DEG[cond]
    n = int(trial["markers"]["RASI"].shape[1])
    for side, leg in (("R", "right"), ("L", "left")):
        try:
            level_group = handle[f"Streaming/{subject}/Tread/i0"]
            level_n = int(level_group["markers"]["RASI"].shape[1])
            fwd_level = fwd if cond == "i0" else recording_heading(level_group)
            width = participant_value(handle, subject, ("Right" if side == "R" else "Left") + "AnkleWidth")
            if width is None or not mass:
                raise ValueError("ankle width or mass unavailable")
            width /= 1000.0
            axis = legs_summary.get(leg, {}).get("plate", {}).get("axis", 1)
            level = {f"Tread_i0_{suf}": leg_segment(level_group, side, a, b, mass * GRAVITY, width, axis)
                     for suf, a, b in tread_segments(handle, level_group, level_n) if b > a}
            ref = sole_reference(level, fwd_level)
            del level
            if not ref:
                raise ValueError("no level-treadmill foot-flat or push-off samples")
            parts = [leg_segment(trial, side, a, b, mass * GRAVITY, width, axis)
                     for suf, a, b in tread_segments(handle, trial, n) if b > a]
            sigma, n_loaded = esml_plate_sign(parts, fwd, signed)
            reg = moment_registration(parts, fwd, signed, mass, ref, sigma)
            plate = legs_summary.get(leg, {}).get("plate", {})
            fit = plate.get("fit") or {}
            mine = None
            if "forward_m" in fit and plate.get("sign") is not None:
                a = np.radians(plate.get("tilt_used_deg", 0.0))
                mine = -(fit["forward_m"] * np.cos(a) + fit["up_m"] * np.sin(a))
                mid = plate.get("midpoint_rule_shift_m")
                mine_mid = -(mid["forward"] * np.cos(a) + mid["up"] * np.sin(a)) if mid else None
            else:
                mine_mid = None
            out[leg] = {"cop_plate_axis_used": axis, "plate_sign_esml": sigma, "plate_sign_mine": plate.get("sign"),
                        "sign_agrees": bool(sigma == plate.get("sign")) if plate.get("sign") is not None else None,
                        "signed_incline_deg": signed, "reference": ref, "moment_registration": reg,
                        "own_moment_offset_m": reg["offset_m"], "my_fitted_offset_m": mine,
                        "my_midpoint_rule_offset_m": mine_mid,
                        "gap_mine_minus_esml_m": None if mine is None else float(mine - reg["offset_m"]),
                        "gap_midpoint_rule_minus_esml_m": None if mine_mid is None else float(mine_mid - reg["offset_m"]),
                        "pig_minus_midpoint_foot_axis_mm": 1000 * ref["pig_minus_midpoint_foot_axis_m"]}
        except Exception as exc:  # recorded, not raised: this is a cross-check
            out[leg] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


def pilot_recordings():
    recs = sorted(t04.t03_records())
    pool = [r for r in recs if r not in PILOT_FIXED]
    return list(PILOT_FIXED) + [random.Random(PILOT_SEED).choice(pool)]


def stage_recordings(stage):
    if stage == "pilot":
        return pilot_recordings()
    if stage == "recheck":  # failing legs of the toe-off gate plus two passing recordings (up-shift fix)
        return ["AB01/i0", "AB01/i10", "AB02/d10", "AB03/i10", "AB08/d10", "AB09/d10", "AB09/i0"]
    if stage == "full":
        return sorted(t04.t03_records())
    raise ValueError(f"unknown stage {stage}")


def stage_paths(stage):
    return {"job_id": f"{TASK_ID}-{stage}-{VERSION}",
            "spec": f"docs/quality/audits/um21-s02-{stage}-spec-{VERSION}.json",
            "output_root": f"converted_datasets/reconversion_v2/um21_s02_frame_{stage}_{VERSION}",
            "receipt": f"docs/quality/audits/um21-s02-{stage}-launcher-receipt-{VERSION}.json"}


def bindings():
    rels = [RUNNER, "contributor_tools/run_um21_t04_signs.py", V2_FULL, V2_MANIFEST, t04.pilot.C03,
            "contributor_tools/adapters/um21_sign_adapter.py", "contributor_tools/common/sign_application.py"]
    b = {r: t04.sha256_file(ROOT / r) for r in rels}
    for job in t04.T03_JOBS:
        rel = t04.T03_RECEIPT.format(job)
        b[rel] = t04.sha256_file(ROOT / rel)
    b[t04.SOURCE] = json.loads((ROOT / t04.C03).read_text())["source"]["sha256_recorded"]
    return b


def build_spec(stage):
    p = stage_paths(stage)
    return {"job_id": p["job_id"],
            "command": ["python3", RUNNER, "run", "--output-root", p["output_root"], "--stage", stage,
                        "--recordings", ",".join(stage_recordings(stage))],
            "cwd": str(ROOT), "output_root": p["output_root"], "receipt_path": p["receipt"], "bindings": bindings(),
            "timeout_seconds": 3600, "kill_after_seconds": 30, "poll_seconds": 15,
            "startup_memory_mib": {"linux": 3584, "windows": 2816},
            "runtime_memory_mib": {"linux": 2048, "windows": 2048},
            "expected_output_names": ["s02_summary.json"], "address_space_mib": ADDRESS_SPACE_MIB}


def plan(stage):
    from contributor_tools.guarded_launcher import validate_spec
    spec = build_spec(stage)
    validate_spec(spec)
    path = ROOT / stage_paths(stage)["spec"]
    with path.open("x", encoding="utf-8") as f:
        f.write(json.dumps(spec, indent=1) + "\n")
    print(json.dumps({"spec": str(path), "sha256": t04.sha256_file(path), "recordings": stage_recordings(stage)}))


def _peak_rss_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run(args):
    if os.nice(0) < 19:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (niceness 19 expected)")
    soft, _ = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY or soft > ADDRESS_SPACE_MIB * 1024 ** 2:
        raise SystemExit("refused: run only through contributor_tools.guarded_launcher (address-space limit expected)")
    recordings = args.recordings.split(",")
    if recordings != stage_recordings(args.stage):
        raise SystemExit("refused: --recordings are not the reviewed sample")
    for r in recordings:
        um21.check_recording(r)
    census_source = ROOT / t04.SOURCE
    c03 = json.loads((ROOT / t04.C03).read_text())["source"]
    st = census_source.stat()
    if (st.st_size, st.st_mtime_ns) != (c03["bytes"], c03["mtime_ns"]):
        raise ValueError("Streaming.mat size/mtime differ from the UM21-C03 record")
    v2_sha = t04.sha256_file(ROOT / V2_FULL)
    out = (ROOT / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.time()
    import h5py
    summaries, ledgers = [], {}
    with h5py.File(census_source, "r", rdcc_nbytes=1024 ** 2) as handle:
        for rec in recordings:
            if t04.pilot._mem_available() < MIN_AVAILABLE_BYTES:
                raise MemoryError("less than 2 GiB available; stopped at a recording boundary")
            subject, cond = rec.split("/")
            v2 = read_v2_rows(ROOT / V2_FULL, rec)
            trial = handle[f"Streaming/{subject}/Tread/{cond}"]
            mass = um21.participant_mass(handle, subject)
            ids, sides, arrays, cop_unheld, summary, ledger = process_recording(
                trial, rec, v2, mass, um21.NOMINAL_SLOPE_DEG[cond])
            summary["esml_crosscheck"] = esml_cross_check(handle, subject, cond, trial, mass, summary["legs"])
            comp_err = composition_error(arrays)
            d = out / "components" / subject / cond
            d.mkdir(parents=True)
            sha = t04.write_observation_table(d / "s02.parquet", ids, arrays, sides)
            findings = t04.reload_check(d / "s02.parquet", ids, arrays)
            sha_u = t04.write_observation_table(d / "cop_unheld.parquet", ids, cop_unheld, sides)
            summary.update({"table_sha256": sha, "cop_unheld_sha256": sha_u, "reload_findings": findings,
                            "composition_max_abs_error_rad": comp_err, "peak_rss_mib": round(_peak_rss_mib(), 1)})
            summaries.append(summary)
            ledgers[rec] = ledger
            print(f"{rec} done, {len(ids)} observations, composition error {comp_err:.2e}, "
                  f"peak RSS {_peak_rss_mib():.0f} MiB", flush=True)
            del v2, arrays, cop_unheld, summary
            import gc
            gc.collect()
            if _peak_rss_mib() > RSS_CAP_MIB:
                raise MemoryError(f"peak RSS {_peak_rss_mib():.0f} MiB above {RSS_CAP_MIB}; stopped")
    after = census_source.stat()
    unchanged = (after.st_size, after.st_mtime_ns) == (st.st_size, st.st_mtime_ns)
    summary = {"task_id": TASK_ID, "stage": args.stage, "scientific_approval": False,
               "note": "pilot evidence only; independent review follows", "recordings": recordings,
               "v2_full_sha256": v2_sha, "defaults": DEFAULTS, "gate": GATE, "cop_label": COP_LABEL,
               "code_sha256": {RUNNER: t04.sha256_file(ROOT / RUNNER)}, "records": summaries,
               "ledger_strides_with_notes": {r: len(l["strides"]) for r, l in ledgers.items()},
               "source_unchanged_after_run": unchanged,
               "resources": {"peak_rss_mib": round(_peak_rss_mib(), 1), "rss_cap_mib": RSS_CAP_MIB,
                             "rlimit_as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "nice": os.nice(0),
                             "wall_seconds": round(time.time() - started, 1)}}
    sa.write_json_exclusive(out / "s02_ledger.json", sa._finite(ledgers))
    sa.write_json_exclusive(out / "s02_summary.json", sa._finite(summary))
    print(json.dumps({"peak_rss_mib": summary["resources"]["peak_rss_mib"], "source_unchanged": unchanged}))
    return 0 if unchanged and not any(s["reload_findings"] for s in summaries) else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)
    pp = sub.add_parser("plan", help="write and validate the job spec")
    pp.add_argument("--stage", choices=("pilot", "recheck", "full"), required=True)
    pr = sub.add_parser("run", help="the job; only through contributor_tools.guarded_launcher")
    pr.add_argument("--output-root", required=True)
    pr.add_argument("--stage", choices=("pilot", "recheck", "full"), required=True)
    pr.add_argument("--recordings", required=True)
    args = p.parse_args(argv)
    if args.step == "plan":
        plan(args.stage)
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
