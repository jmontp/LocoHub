"""UM21-T05: pure functions for the UMich 2021 continuous time export (treadmill recordings of package v4).

Nothing here reads a file. The runner (run_um21_t05_time.py) hands in arrays or a mapping shaped like the h5py group of one
recording (markers, forceplates, jointAngles, jointMoments); tests hand in synthetic stand-ins.

Rules (all inherited; nothing new about the science is decided here):

* Clock. Kinematics, moments and the plate force and centre of pressure are all on the source frame clock: 100 Hz, frame f
  (1-based) at time (f - 1) / 100 s, so time_s = arange(n) / 100. No resampling. The 1 kHz plate is read at the plate samples
  that coincide with the frames (index 10 * i); the nine plate samples between two frames are not in the table (this is what
  the GT21 time table does as well: one clock per table, 200 Hz there).
* Angles. Same S02 v7 geometry as package v4 (run_um21_s02_frame.py, imported, not copied): per-leg side-view plane from the
  knee markers (KNEM lateral, KNE medial), thigh/shank/foot in that plane, pelvis from the audited-sign Vicon channel (kept
  as in S02), hip = thigh - pelvis, knee = thigh - shank, ankle = foot - shank. A frame whose leg plane is more than 60
  degrees from the walking direction holds that leg's plane-dependent columns (rule P1, applied per frame here, per stride in
  the phase table). A marker gap leaves the dependent columns missing at that frame; nothing is filled.
* Velocity. numpy.gradient(angle, 0.01, edge_order=1) (the T04 method with the source frame spacing); NaN propagates to the
  neighbouring samples.
* Moments. As stored (Nm/kg, internal, already in the named direction; audited sign +1), exact zero triples missing.
* Power. moment x LocoHub joint speed (D-REF-5): hip = thigh - pelvis speed, knee = thigh - shank speed, ankle = foot - shank
  speed; missing wherever either factor is missing.
* Ground force (new in the time table; the phase table has none). Plate force (N, the source README says N/kg but the
  stride-mean total equals body weight in N, UM21-SLOPE) is turned into the walking-direction frame with the registration S02
  fitted for that leg (plate axis, sign, belt tilt), negated to be the force on the person, divided by body weight
  (mass x 9.81, mass from ParticipantDetails, never invented), and published as grf_vertical (up), grf_anterior (walking
  direction) and grf_lateral (outward from that leg). A sample whose plate carries less than 20 N (the foot is off its plate)
  is 0 BW; a sample whose plate value is not finite is missing. A leg's force is held (all missing, reason recorded) when the
  registration is unknown, the body mass is missing, the plate was not loaded at 95 percent of the leg's heel strikes, or the
  recording is one of the held-back (pending by ruling) recordings.
* Centre of pressure. The S02 rule, per frame: plate point turned with the same registration, shifted by the S02 fitted
  (forward, up, lateral) plate shift, then expressed in the ankle frame of the leg plane. Published only for a leg whose S02
  gate passed and not for a held-back recording; unloaded samples (< 20 N) are missing, never 0.
* Held-back recordings (CoP pending by ruling): AB01/i10, AB02/i10, AB03/i10, AB04/d10, AB10/d5 keep CoP missing; their force
  is held too (their plate registration was never investigated; logged as a conservative choice in UM21-T05-plan.json).

scientific_approval is false everywhere.
"""
from __future__ import annotations

import json
import re

import numpy as np

FRAME_HZ = 100.0
DT = 1.0 / FRAME_HZ
PLATE_PER_FRAME = 10
LOAD_N = 20.0
GRAVITY = 9.81
N_PHASE = 150
L2_JUMP_DEG = 30.0
PLANE_GLITCH_DEG = 60.0
ASSIGNMENT_MIN = 0.95
PENDING_BY_RULING = frozenset({"AB01/i10", "AB02/i10", "AB03/i10", "AB04/d10", "AB10/d5"})
PELVIS_SIGN_DEFAULT = -1.0                  # audited sign for pelvis tilt (rule B), docs/audited_signs.json UM21-pelvis_tilt
PELVIS_SIGN_EXCEPTIONS = {"AB04/i0": 1.0}   # D-UM21-P01-1 = C: the stored tilt of this recording is reversed; correction -1 on top
BATCH_SIZE = 5
ID_RE = re.compile(r"^um21:Streaming/(AB\d{2})/Tread/([di]\d+):(right|left):frames:(\d+):(\d+)$")

PELVIS = "pelvis_sagittal_angle_rad"
PELVIS_VEL = "pelvis_sagittal_velocity_rad_s"
SEG_ANGLES = ("thigh_sagittal_angle_{w}_rad", "shank_sagittal_angle_{w}_rad", "foot_sagittal_angle_{w}_rad")
JOINT_ANGLES = ("hip_flexion_angle_{w}_rad", "knee_flexion_angle_{w}_rad", "ankle_dorsiflexion_angle_{w}_rad")
SEG_VELOCITIES = ("thigh_sagittal_velocity_{w}_rad_s", "shank_sagittal_velocity_{w}_rad_s", "foot_sagittal_velocity_{w}_rad_s")
MOMENTS = ("hip_flexion_moment_{w}_Nm_kg", "knee_flexion_moment_{w}_Nm_kg", "ankle_dorsiflexion_moment_{w}_Nm_kg")
POWERS = ("hip_flexion_power_{w}_W_kg", "knee_flexion_power_{w}_W_kg", "ankle_dorsiflexion_power_{w}_W_kg")
GRFS = ("grf_vertical_{w}_BW", "grf_anterior_{w}_BW", "grf_lateral_{w}_BW")
COPS = ("cop_anterior_{w}_m", "cop_vertical_{w}_m", "cop_lateral_{w}_m")
LEG_TEMPLATES = SEG_ANGLES + JOINT_ANGLES + SEG_VELOCITIES + MOMENTS + POWERS + GRFS + COPS
# plane-dependent columns held by rule P1 (frame level here); same list as the phase table
PLANE_TEMPLATES = SEG_ANGLES + JOINT_ANGLES + SEG_VELOCITIES + COPS
L2_TEMPLATES = SEG_ANGLES + JOINT_ANGLES            # 100 Hz angle series checked by L2 (pelvis is checked once)
SIDES = (("R", "right"), ("L", "left"))
IDENTITY_STR = ("subject", "source_recording_id", "observation_id", "reference_side", "observation_type", "task", "task_id",
                "task_info")
CLOCKS = ("source_start_time_s", "source_end_time_s")

REASON_PLANE = "leg plane undefined: the knee marker names disagree with the data for this leg (no leg-plane angles)"
REASON_GAP = "no finite value in this recording: the markers or channel it needs are not visible or not recorded"
REASON_GLITCH = "leg plane more than 60 degrees from the walking direction in every visible frame (rule P1)"
REASON_MOMENT = "no finite moment in the source channel for this leg in this recording"
REASON_POWER = "power missing: the moment or the joint speed is missing at every sample"
REASON_FORCE_NO_REG = "force held: the plate registration (axis and sign) could not be determined for this leg"
REASON_FORCE_NO_MASS = "force held: body mass unavailable in the source (never invented)"
REASON_FORCE_ASSIGN = "force held: the plate was loaded at fewer than 95 percent of this leg's heel strikes"
REASON_FORCE_PENDING = ("force held: held-back recording (pending by ruling); its plate registration was not investigated")
REASON_COP_PREFIX = "foot-frame centre of pressure held: "
REASON_COP_PENDING = "held-back recording (pending by ruling); not investigated further"


# ------------------------------------------------------------------ names
def word(leg):
    return leg


def time_columns():
    names = [PELVIS, PELVIS_VEL]
    for leg in ("left", "right"):
        names += [t.format(w=leg) for t in LEG_TEMPLATES]
    return names


def leg_columns(leg, templates=LEG_TEMPLATES):
    return [t.format(w=leg) for t in templates]


def phase_name(time_col, leg):
    """Time column -> the phase-table column of the same signal for a stride whose reference leg is ``leg``."""
    if time_col in (PELVIS, PELVIS_VEL):
        return time_col
    if f"_{leg}_" not in time_col:
        raise KeyError(f"{time_col} is not a {leg} column")
    return time_col.replace(f"_{leg}_", "_ipsi_")


def time_observation_id(recording, frames):
    sub, cond = recording.split("/")
    return f"um21:Streaming/{sub}/Tread/{cond}:continuous:frames:1:{int(frames)}"


def recording_id(recording):
    sub, cond = recording.split("/")
    return f"um21:Streaming/{sub}/Tread/{cond}"


def batches(recordings, size=BATCH_SIZE):
    r = sorted(recordings)
    return [r[i:i + size] for i in range(0, len(r), size)]


def parse_id(oid):
    m = ID_RE.match(oid or "")
    if not m:
        return None
    sub, cond, side, a, b = m.groups()
    return {"recording": f"{sub}/{cond}", "side": side, "a": int(a), "b": int(b)}


# ------------------------------------------------------------------ small pure rules
def pelvis_sign(recording):
    return PELVIS_SIGN_EXCEPTIONS.get(recording, PELVIS_SIGN_DEFAULT)


def signed_pelvis(raw_deg, recording):
    """Source pelvis tilt component 1 (degrees, zero triples already NaN) -> LocoHub segment angle (rad)."""
    return pelvis_sign(recording) * np.radians(np.asarray(raw_deg, float))


def velocity(x, dt=DT):
    """T04 derivative method on the source clock: central differences inside, one-sided at the ends, NaN propagates."""
    x = np.asarray(x, float)
    if x.size < 2:
        return np.full(x.shape, np.nan)
    v = np.gradient(x, dt, edge_order=1)
    v[~np.isfinite(x)] = np.nan          # no velocity at a frame whose own angle is missing
    return v


def power(moment, speed):
    m, v = np.asarray(moment, float), np.asarray(speed, float)
    out = np.full(m.shape, np.nan)
    ok = np.isfinite(m) & np.isfinite(v)
    out[ok] = m[ok] * v[ok]
    return out


def window_mask(n, windows):
    """Frames covered by 1-based inclusive windows (a, b)."""
    m = np.zeros(n, bool)
    for a, b in windows:
        m[max(a, 1) - 1:min(b, n)] = True
    return m


def plane_deviation_deg(plane_forward, walking_forward):
    c = np.sum(np.asarray(plane_forward, float) * np.asarray(walking_forward, float), axis=1)
    with np.errstate(invalid="ignore"):
        return np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))


def glitch_mask(deviation_deg, limit=PLANE_GLITCH_DEG):
    d = np.asarray(deviation_deg, float)
    with np.errstate(invalid="ignore"):
        return np.isfinite(d) & (d > limit)


def l2_jumps(series_rad, limit_deg=L2_JUMP_DEG):
    """0-based frame indices f >= 1 where |x[f] - x[f-1]| exceeds the limit with both frames finite (the Q01 L2 rule)."""
    x = np.degrees(np.asarray(series_rad, float))
    if len(x) < 2:
        return []
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(x[1:]) & np.isfinite(x[:-1])
        return [int(i) + 1 for i in np.flatnonzero(ok & (np.abs(np.diff(x)) > limit_deg))]


def force_hold_reason(reg, mass_kg, recording):
    """None when the leg's plate force is published, else the reason it is held."""
    if recording in PENDING_BY_RULING:
        return REASON_FORCE_PENDING
    if reg is None or reg.get("axis") is None or reg.get("sign") is None:
        return REASON_FORCE_NO_REG
    if not mass_kg or mass_kg <= 0:
        return REASON_FORCE_NO_MASS
    frac = reg.get("assignment_same_plate")
    if frac is None or frac < ASSIGNMENT_MIN:
        return REASON_FORCE_ASSIGN
    return None


def cop_hold_reason(reg, recording):
    """None when the leg's centre of pressure is published, else the reason it is held."""
    if recording in PENDING_BY_RULING:
        return REASON_COP_PREFIX + REASON_COP_PENDING
    if reg is None or reg.get("cop_verdict") != "pass" or reg.get("shift") is None:
        why = "; ".join(reg.get("cop_reasons", [])) if reg else ""
        return REASON_COP_PREFIX + (why or "the S02 gate did not pass for this leg")
    return None


def registration_from_summary(leg_summary):
    """Plate registration of one leg from an S02 v7 summary record (summary['records'][i]['legs'][leg])."""
    plate = (leg_summary or {}).get("plate", {}) or {}
    gate = (leg_summary or {}).get("cop_gate", {}) or {}
    fit = plate.get("fit") or {}
    shift = None
    if fit.get("forward_m") is not None and fit.get("up_m") is not None:
        lat = fit.get("lateral_m")
        shift = (float(fit["forward_m"]), float(fit["up_m"]), float(lat) if lat is not None else 0.0)   # S02: None -> 0.0
    pa = plate.get("plate_assignment") or {}
    return {"axis": plate.get("axis"), "sign": plate.get("sign"), "tilt_deg": plate.get("tilt_used_deg"), "shift": shift,
            "cop_verdict": gate.get("verdict"), "cop_reasons": list(gate.get("reasons", [])),
            "assignment_same_plate": pa.get("same_plate_loaded_within_5_frames_fraction"),
            "assignment_other_plate": pa.get("other_plate_loaded_in_same_window_fraction")}


HOLD_PHASE_COLUMNS = ("pelvis_sagittal_angle_rad", "hip_flexion_angle_ipsi_rad", "hip_flexion_moment_ipsi_Nm_kg",
                      "knee_flexion_moment_ipsi_Nm_kg", "ankle_dorsiflexion_moment_ipsi_Nm_kg")


def holds_from_phase_entries(entries):
    """{time column: [(a, b), ...]} frame windows of the package-v4 phase strides whose pelvis, hip angle or moment is held
    (assessment entries of table 'phase', key held_signals). Marker-gap and plane holds are not carried: the time series
    reproduces those from the markers frame by frame."""
    holds = {}
    for e in entries:
        p = parse_id(e["observation_id"])
        if p is None:
            raise ValueError(f"{e['observation_id']}: id does not parse")
        for col in e.get("held_signals", {}):
            if col in HOLD_PHASE_COLUMNS:
                tcol = col if col == PELVIS else col.replace("_ipsi_", f"_{p['side']}_")
                holds.setdefault(tcol, []).append((p["a"], p["b"]))
    return holds


def merge_task_info(texts):
    """Keys of the stride task_info JSON texts that are identical in every stride of a recording (None for no texts).
    Returns (merged dict, dropped key list)."""
    docs = [json.loads(t) for t in sorted(set(texts)) if t]
    if not docs:
        return {}, []
    keys = set().union(*[set(d) for d in docs])
    merged = {k: docs[0][k] for k in keys if all(k in d and d[k] == docs[0].get(k) for d in docs)}
    return merged, sorted(keys - set(merged))


def _s02():
    from contributor_tools import run_um21_s02_frame as s02   # the bound S02 v7 geometry (not copied)
    return s02


# ------------------------------------------------------------------ plate force and centre of pressure
def grf_bw(f_frames, reg, mass_kg, leg, s02=None):
    """Plate force at the frame instants (3, n) in N -> (grf (3, n) in BW [vertical, anterior, lateral], loaded mask).
    0 where the plate is finite and below 20 N, NaN where it is not finite."""
    s02 = s02 or _s02()
    f = np.asarray(f_frames, float)
    finite = np.isfinite(f).all(axis=0)
    loaded = finite & (-f[2] > LOAD_N)
    masked = f.copy()
    masked[:, ~loaded] = np.nan
    person = s02.force_to_person(masked, reg["axis"], reg["sign"], np.radians(reg["tilt_deg"] or 0.0))   # fwd, up, right
    bw = mass_kg * GRAVITY
    lateral = person[2] if leg == "right" else -person[2]
    out = np.stack([person[1], person[0], lateral]) / bw
    out[:, finite & ~loaded] = 0.0
    out[:, ~finite] = np.nan
    return out, loaded


# ------------------------------------------------------------------ one recording
def process_time_recording(trial, recording, regs, holds, mass_kg, s02=None):
    """Whole-recording time columns.

    trial: mapping like the h5py group (markers, forceplates, jointAngles, jointMoments).
    regs: {'right': registration, 'left': registration} from registration_from_summary.
    holds: {time column: [(a, b), ...]} 1-based inclusive stride windows whose package-v4 phase value is held for that column
           (only pelvis and moment columns and the joint-angle columns are looked at; geometry holds come from the data).
    Returns {"time_s", "columns", "held", "summary"}.
    """
    s02 = s02 or _s02()
    n = int(trial["markers"]["RASI"].shape[1])
    mk, _cov = s02.read_markers(trial, n)
    asi_mid, psi_mid = (mk["LASI"] + mk["RASI"]) / 2, (mk["LPSI"] + mk["RPSI"]) / 2
    fwd = s02.heading(asi_mid, psi_mid)
    rvec = s02.right_axis(fwd)
    hjc = s02.hip_centres(mk["RASI"], mk["LASI"], mk["RPSI"], mk["LPSI"])
    up = s02.UP
    cols, reasons, summary = {}, {}, {"recording": recording, "frames": n, "legs": {}}

    def comp1(group, name):
        x = np.asarray(trial[group][name][...], np.float64)
        if x.shape != (3, n):
            raise ValueError(f"{recording}/{group}/{name}: shape {x.shape}, expected (3, {n})")
        x = x.copy()
        x[:, (x == 0).all(axis=0)] = np.nan   # exact (0, 0, 0) triples are zero fill (UM21-C03)
        return x[0]

    # pelvis: audited-sign Vicon tilt (right-side channel for the single published column), holds from the package-v4 phase
    pelv_r = signed_pelvis(comp1("jointAngles", "RPelvisAngles"), recording)
    pelv_l = signed_pelvis(comp1("jointAngles", "LPelvisAngles"), recording)
    summary["pelvis_right_left_max_abs_diff_rad"] = (float(np.nanmax(np.abs(pelv_r - pelv_l))) if np.isfinite(pelv_r - pelv_l).any() else None)
    pelvis = np.where(window_mask(n, holds.get(PELVIS, [])), np.nan, pelv_r)
    cols[PELVIS] = pelvis
    cols[PELVIS_VEL] = velocity(pelvis)
    for side, leg in SIDES:
        reg = regs.get(leg)
        info = summary["legs"].setdefault(leg, {})
        hip = hjc["right" if side == "R" else "left"]
        knee = (mk[side + "KNE"] + mk[side + "KNEM"]) / 2
        ankle = (mk[side + "ANK"] + mk[side + "ANKM"]) / 2
        fl = s02.plane_forward(s02.knee_axis_to_right(mk[side + s02.KNEE_LATERAL_MARKER], mk[side + s02.KNEE_MEDIAL_MARKER], side))
        away = lambda name: np.abs((mk[side + name] - asi_mid) @ rvec)   # noqa: E731
        knee_sep = float(np.nanmedian(away(s02.KNEE_LATERAL_MARKER)) - np.nanmedian(away(s02.KNEE_MEDIAL_MARKER)))
        plane_valid = bool(np.isfinite(knee_sep) and knee_sep > s02.KNEE_SEPARATION_MIN_M)
        seg = s02.leg_segment_angles(fl, knee - hip, ankle - knee, mk[side + "HEE"], mk[side + "TOE"])
        glitch = glitch_mask(plane_deviation_deg(fl, fwd))
        thigh, shank, foot = (np.where(glitch, np.nan, seg[k]) for k in ("thigh", "shank", "foot"))
        if not plane_valid:
            thigh = shank = foot = np.full(n, np.nan)
        hip_a, knee_a, ankle_a = thigh - pelvis, thigh - shank, foot - shank
        angle = dict(zip(leg_columns(leg, SEG_ANGLES + JOINT_ANGLES), (thigh, shank, foot, hip_a, knee_a, ankle_a)))
        for name, series in angle.items():
            h = holds.get(name)
            cols[name] = np.where(window_mask(n, h), np.nan, series) if h else series
        thigh, shank, foot = (cols[c] for c in leg_columns(leg, SEG_ANGLES))
        v_t, v_s, v_f = velocity(thigh), velocity(shank), velocity(foot)
        for name, series in zip(leg_columns(leg, SEG_VELOCITIES), (v_t, v_s, v_f)):
            cols[name] = series
        # moments (as stored) and power = moment x joint speed
        pre = {"right": "R", "left": "L"}[leg]
        for j, (tmpl, src) in enumerate(zip(MOMENTS, ("Hip", "Knee", "Ankle"))):
            name = tmpl.format(w=leg)
            m = comp1("jointMoments", f"{pre}{src}Moment")
            h = holds.get(name)
            cols[name] = np.where(window_mask(n, h), np.nan, m) if h else m
        cols[POWERS[0].format(w=leg)] = power(cols[MOMENTS[0].format(w=leg)], v_t - cols[PELVIS_VEL])
        cols[POWERS[1].format(w=leg)] = power(cols[MOMENTS[1].format(w=leg)], v_t - v_s)
        cols[POWERS[2].format(w=leg)] = power(cols[MOMENTS[2].format(w=leg)], v_f - v_s)
        info.update({"plane_valid": plane_valid, "knee_lateral_minus_medial_m": knee_sep, "glitch_frames": int(glitch.sum()),
                     "finite_plane_frames": int(np.isfinite(plane_deviation_deg(fl, fwd)).sum())})
        # plate force and centre of pressure at the frame instants
        sub = slice(0, PLATE_PER_FRAME * n, PLATE_PER_FRAME)
        f_raw = np.asarray(trial["forceplates"][side + "Force"][...], np.float64)
        c_raw = np.asarray(trial["forceplates"][side + "CoP"][...], np.float64)
        if f_raw.shape != (3, PLATE_PER_FRAME * n) or c_raw.shape != f_raw.shape:
            raise ValueError(f"{recording} {leg}: plate samples {f_raw.shape} != (3, {PLATE_PER_FRAME} x {n})")
        f_s, c_s = f_raw[:, sub].copy(), c_raw[:, sub].copy()
        del f_raw, c_raw
        why_f = force_hold_reason(reg, mass_kg, recording)
        if why_f is None:
            grf, loaded = grf_bw(f_s, reg, mass_kg, leg, s02)
            info["force"] = {"published": True, "loaded_fraction": float(loaded.mean()),
                             "zero_fraction": float(np.mean(grf[0] == 0.0)), "nonfinite_fraction": float(np.mean(~np.isfinite(grf[0])))}
        else:
            grf = np.full((3, n), np.nan)
            info["force"] = {"published": False, "reason": why_f}
            reasons.update({c: why_f for c in leg_columns(leg, GRFS)})
        for name, series in zip(leg_columns(leg, GRFS), grf):
            cols[name] = series
        why_c = cop_hold_reason(reg, recording)
        if why_c is None and not plane_valid:
            why_c = REASON_COP_PREFIX + REASON_PLANE
        if why_c is None:
            force_m, cop_m, loaded_c = s02.mask_unloaded(f_s, c_s)
            tilt = np.radians(reg["tilt_deg"] or 0.0)
            cop_lab = s02.plate_to_person(cop_m[:2], reg["axis"], reg["sign"], tilt) + np.asarray(reg["shift"], float)[:, None]
            lab_pt = cop_lab[0][:, None] * fwd + cop_lab[1][:, None] * up + cop_lab[2][:, None] * rvec
            ok = np.isfinite(ankle).all(axis=1) & np.isfinite(foot) & np.isfinite(fl).all(axis=1)
            pt = np.where(ok[:, None], lab_pt, np.nan)
            cf = s02.foot_frame_point(pt, ankle, fl, foot, leg)    # foot angle with the glitch hold already applied
            info["cop"] = {"published": True, "loaded_fraction": float(loaded_c.mean())}
        else:
            cf = np.full((3, n), np.nan)
            info["cop"] = {"published": False, "reason": why_c}
            reasons.update({c: why_c for c in leg_columns(leg, COPS)})
        for name, series in zip(leg_columns(leg, COPS), cf):
            cols[name] = series
        if not plane_valid:
            reasons.update({c: REASON_PLANE for c in leg_columns(leg, SEG_ANGLES + JOINT_ANGLES + SEG_VELOCITIES)})
    order = time_columns()
    missing = [c for c in order if c not in cols]
    if missing:
        raise ValueError(f"columns not produced: {missing}")
    cols = {c: np.asarray(cols[c], float) for c in order}
    held = {}
    for c in order:
        if np.isfinite(cols[c]).any():
            continue
        held[c] = reasons.get(c) or _default_reason(c)
    summary["finite_samples"] = {c: int(np.isfinite(v).sum()) for c, v in cols.items()}
    return {"time_s": np.arange(n) / FRAME_HZ, "columns": cols, "held": held, "summary": summary}


def _default_reason(name):
    if "_moment_" in name:
        return REASON_MOMENT
    if "_power_" in name:
        return REASON_POWER
    if name.startswith("grf_"):
        return REASON_FORCE_NO_REG
    return REASON_GAP


# ------------------------------------------------------------------ assessment of the time observation (L2 only)
FAILED = "failed"
NOT_FAILED = "no_failure_found"


def time_l2_checked_columns():
    names = [PELVIS]
    for leg in ("left", "right"):
        names += leg_columns(leg, L2_TEMPLATES)
    return names


def build_time_entry(meta, time_s, columns, held, limitation_flags, attributes_extra=None):
    """Structured assessment entry of one continuous recording and its L2 failure rows.

    L2 (adjacent 100 Hz samples, 30 degrees) is the only limit applied to the time table (same value as UM21-Q01 v3; L1 and
    L5 stay on the phase table). Other columns are 'unchecked'. Missing or held columns are 'unchecked_all_missing'. Jumps are
    only found between two finite samples (a frame held by rule P1 is NaN, so no jump is counted across it)."""
    n = len(time_s)
    fails, failed_samples = [], {}
    states = {}
    for c in columns:
        x = columns[c]
        if c in held or not np.isfinite(x).any():
            states[c] = "unchecked_all_missing"
            continue
        if c in time_l2_checked_columns():
            hits = l2_jumps(x)
            for f in hits:
                fails.append({"observation_id": meta["observation_id"], "reference_side": "none", "table": "time", "channel": c,
                              "limit": "L2", "sample_index": f, "frame": f, "value": float(np.degrees(x[f] - x[f - 1])),
                              "time_s": float(time_s[f]),
                              "reason": f"{c} changes more than {L2_JUMP_DEG:g} deg between 100 Hz samples {f - 1} and {f}"})
            if hits:
                failed_samples[c] = {"L2": len(hits)}
            states[c] = "fail" if hits else "pass_jump_only"
        else:
            states[c] = "unchecked"
    limits = ["L2"] if fails else []
    problems = []
    if n < 2 or not np.all(np.diff(time_s) > 0):
        problems.append("S1 time_s is not strictly increasing with at least two samples")
    if problems:
        limits.append("structural")
    by_state = {}
    for c, s in states.items():
        by_state.setdefault(s, []).append(c)
    status = FAILED if limits else NOT_FAILED
    entry = {"observation_id": meta["observation_id"], "reference_side": "none", "table": "time",
             "observation_type": "continuous_recording", "subject": meta["subject"],
             "source_recording_id": meta["source_recording_id"], "task": meta["task"], "task_id": meta["task_id"], "rows": int(n),
             "status": status, "failed_limits": limits if status == FAILED else [], "failed_channels": sorted(failed_samples),
             "failed_samples": failed_samples, "limitations": list(limitation_flags), "flight": None,
             "attributes": {"frames": int(n), "duration_s": float(time_s[-1] - time_s[0]) if n > 1 else 0.0,
                            "sampling_rate_hz": FRAME_HZ, "structural_state": "fail" if problems else "pass",
                            "structural_problems": problems, "l2_scope": "time table only (100 Hz source samples)",
                            **(attributes_extra or {})},
             "held_signals": dict(held), "channel_states": by_state}
    return entry, fails


def limitation_flags(summary):
    """Per-recording limitation ids of the time observation (texts live in the v5 package adapter)."""
    flags = ["time_table_source_rate", "moments_from_source_sign_applied", "power_from_moment_and_speed",
             "knee_marker_labels_swapped", "time_pelvis_vicon_single_column"]
    legs = summary["legs"]
    if any(v.get("cop", {}).get("published") for v in legs.values()):
        flags.append("cop_estimated_plate_position")
    if any(not v.get("cop", {}).get("published") for v in legs.values()):
        flags.append("cop_held_leg")
    if summary["recording"] in PENDING_BY_RULING:
        flags.append("cop_held_pending_ruling")
    if any(v.get("force", {}).get("published") for v in legs.values()):
        flags.append("time_grf_plate_force")
    if any(not v.get("force", {}).get("published") for v in legs.values()):
        flags.append("time_grf_held_leg")
    if any(v.get("glitch_frames") for v in legs.values()):
        flags.append("plane_glitch_hold")
    return flags


# ------------------------------------------------------------------ readback: time samples at a stride window -> 150 points
def resample_window(x, a, b, n_out=N_PHASE):
    """Frames a..b (1-based, inclusive) of a frame series on the inclusive n_out-point grid, linear interpolation, the same
    rule as the phase table (um21_sign_adapter.resample). NaN neighbours give NaN."""
    seg = np.asarray(x, float)[a - 1:b]
    src = np.arange(seg.shape[0])
    grid = np.linspace(0, seg.shape[0] - 1, n_out)
    return np.interp(grid, src, seg)


# Tolerances, written down before any time result was read. angle/moment columns are the same linear interpolation of the
# same frame series, so they must agree to rounding; velocities are derived on a different clock (150-point stride grid in the
# phase table, 10 ms source frames here), so they agree only up to finite-difference error; the centre of pressure is built
# from 1 kHz plate samples interpolated at fractional frames in the phase table and from the sample at each frame here.
TOLERANCES = {
    "angle_max_abs_rad": 1e-9,               # thigh, shank, foot, knee, ankle
    "pelvis_hip_max_abs_rad": 1e-6,          # pelvis and hip: the phase table uses the same-side Vicon pelvis, the time table the right one
    "moment_max_abs_Nm_kg": 1e-9,
    "velocity_nrms_max": 0.03,               # per stride, rms(phase - time) / rms(phase); at least 99 percent of strides must pass
    "velocity_strides_pass_fraction_min": 0.99,
    "cop_median_abs_m": 0.001,
    "cop_p99_abs_m": 0.005,
    # share of samples finite in only one of the two tables (stance edges). Bound by construction: the 1 kHz mask moves the edge
    # by under 1 ms, the 100 Hz mask by up to one 10 ms frame at each of the two edges, i.e. about 3 of the ~90 stance samples
    # of a 150-point stride (3.3 percent); 5 percent leaves room for short stances and is not tuned to any result.
    "cop_finite_mismatch_fraction_max": 0.05,
    "clock_abs_s": 1e-9,
}


def compare_series(kind, phase_vals, time_vals):
    """Compare one stride's 150 phase values with the resampled time values. Returns a dict with the numbers and 'pass'."""
    p, t = np.asarray(phase_vals, float), np.asarray(time_vals, float)
    both = np.isfinite(p) & np.isfinite(t)
    only_phase, only_time = int((np.isfinite(p) & ~np.isfinite(t)).sum()), int((~np.isfinite(p) & np.isfinite(t)).sum())
    out = {"n_both": int(both.sum()), "only_phase_finite": only_phase, "only_time_finite": only_time}
    if not both.any():
        # no sample finite in both: nothing to compare. Finiteness differences are counted and reported (the phase table holds a
        # whole stride for a plane or marker gap, the time table only the frames of the gap), not gated.
        out.update({"pass": True, "max_abs": None})
        return out
    d = np.abs(p[both] - t[both])
    out["max_abs"] = float(d.max())
    if kind in ("angle", "pelvis_hip", "moment"):
        lim = {"angle": TOLERANCES["angle_max_abs_rad"], "pelvis_hip": TOLERANCES["pelvis_hip_max_abs_rad"],
               "moment": TOLERANCES["moment_max_abs_Nm_kg"]}[kind]
        out["pass"] = bool(d.max() <= lim)   # values where both tables are finite; finiteness differences are reported, not gated
        out["limit"] = lim
    elif kind == "velocity":
        rms_p = float(np.sqrt(np.mean(p[both] ** 2)))
        nrms = float(np.sqrt(np.mean((p[both] - t[both]) ** 2)) / rms_p) if rms_p > 0 else None
        out["nrms"] = nrms
        out["pass"] = bool(nrms is not None and nrms <= TOLERANCES["velocity_nrms_max"])
        out["limit"] = TOLERANCES["velocity_nrms_max"]
    elif kind == "power":
        # reported, not gated (T05-F): power is moment x joint speed on two different clocks
        rms_p = float(np.sqrt(np.mean(p[both] ** 2)))
        out["nrms"] = float(np.sqrt(np.mean((p[both] - t[both]) ** 2)) / rms_p) if rms_p > 0 else None
        out["pass"] = True
    elif kind == "cop":
        out["median_abs"], out["p99_abs"] = float(np.median(d)), float(np.percentile(d, 99))
        out["pass"] = None   # decided over the whole leg: medians/p99 pooled and the finite-mismatch fraction (see leg_cop_verdict)
        out["abs_values_pooled"] = d
    else:
        raise ValueError(kind)
    return out


def leg_cop_verdict(pooled_abs, n_finite, n_only_phase, n_only_time):
    """Pass/fail of the centre of pressure of one leg of one recording from pooled stride comparisons."""
    if n_finite == 0:
        return {"pass": n_only_phase == 0 and n_only_time == 0, "n_finite": 0}
    d = np.asarray(pooled_abs, float)
    mismatch = (n_only_phase + n_only_time) / float(n_finite + n_only_phase + n_only_time)
    med, p99 = (float(np.median(d)), float(np.percentile(d, 99))) if d.size else (None, None)
    ok = bool(d.size and med <= TOLERANCES["cop_median_abs_m"] and p99 <= TOLERANCES["cop_p99_abs_m"]
              and mismatch <= TOLERANCES["cop_finite_mismatch_fraction_max"])
    return {"pass": ok, "n_finite": int(n_finite), "median_abs_m": med, "p99_abs_m": p99, "finite_mismatch_fraction": mismatch,
            "only_phase": int(n_only_phase), "only_time": int(n_only_time)}


def dumps(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
