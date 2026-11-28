"""HIST-06: map the HIST-05 AddBiomechanics frames (Falisse, Tan running, Tan walking) to LocoHub names.

Input: one participant folder written by HIST-05 (frames.parquet, conversion.json, dynamics_model.osim):
one row per frame from the dynamics pass, source names (dofNN_pos/vel/acc/tau by DOF index, <body>_force/
cop/torque_xyz in the AddBiomechanics world frame). Evidence for every rule below is in
docs/quality/audits/hist06-addbiomechanics-mapping.json (citations) and
docs/quality/audits/hist06-addb-mapping-probe.json (read-only probe of the 33 participants).

Per participant the adapter

1. checks the model before reading any frame: the dynamics model's 25 coordinates, the two enforced
   patellofemoral couplers (knee_angle_<s>_beta = knee_angle_<s>), the ground_pelvis transform
   (Rz(tilt) Rx(list) Ry(rotation), zero offset orientations), gravity (0, -9.80665, 0) and exactly 23
   DOF columns. DOF k is the k-th model coordinate after removing the two coupled beta coordinates (H23);
   reading the first 23 coordinates in order (H_order) is refuted by the probe (dof10 would equal dof09);
2. per trial (one source_recording_id) applies the task rule: MAP-TAN-TASK (a Tan trial whose original
   name does not match its study's protocol pattern gets no task label, goes into no task table, and is
   kept with its source name; the same rule is applied to Falisse names); Tan running protocol trials
   keep 'run' (HIST-04 table); Tan walking and Falisse labels only from the answer to D-HIST-06-2;
3. per trial computes the walking direction for the rule-B frame (+x walking, +y up, +z = x cross y):
   treadmill trials from the principal horizontal axis of within-stance CoP displacement, overground
   trials from the mean horizontal COM velocity, each oriented and checked (<= 45 deg) against the pelvis
   facing direction. Trials without forward locomotion (sit-to-stand, calibration, unlabeled) keep only
   vertical force and vertical CoP until D-GT23-C01-1 defines forward for them;
4. per trial and leg passes the untransformed hip, knee and ankle angles and generalized forces, and the
   pelvis pitch (asin of the up component of the pelvis anterior axis: heading-independent, because the
   source pelvis_tilt is a ground-relative Euler angle that is pelvic obliquity when the person faces
   +-z, as in Falisse sit-to-stand and all Tan running trials), to the CORE-11 hook
   (sign_application.run_sign_application) on units: strides (heel strike to heel strike of that foot from
   its recorded vertical force, every frame finite whatever its flag, 0.4-2.5 s, resampled to 150 samples)
   for locomotion trials, else fixed blocks
   of BLOCK_FRAMES frames. Adapters never pass signs: the audited signs come from the committed table.
   The model definition (forward-kinematics probe) is passed as documentation only;
5. AFTER the hook applies each published channel's logged multiplier (exactly +1 or -1) to the whole trial,
   derives thigh, shank and foot with derive_segment_angles and velocities with derive_angular_velocities
   (spacing = source timestep) from published channels only, and writes one row per frame and reference
   leg (reference_side right and left, ipsi = that leg). Held channels are not written under LocoHub names.

GRF and CoP: the AddBiomechanics contact force is the ground reaction force on the contact body, in the
world frame (nimblephysics FramePass.groundContactForce docs); y is up (model gravity). The recorded force
and CoP are written on every frame, whatever AddBiomechanics' per-frame missing_grf_reason flag says
(coordinator ruling on HIST-06-verify F1 under José's keep-recorded-values rule); the flag is carried
unchanged, with its source label, as a quality column for users to filter on. A force value is empty only
where the source value is absent (NaN); a recorded zero force stays zero. CoP is empty where that foot's
recorded vertical force is not positive, independent of the flag: the source stores an undefined CoP as an
exact (0, 0, 0) placeholder (HIST-06-verify F3). Stride boundaries come from the recorded
vertical force, so a flagged frame does not break a stride. Lateral force and CoP are
positive outward for each leg. Moments stay in N*m (_Nm columns); per-kg moments and body-weight forces
divide by the source's recorded participant mass (entered_mass_kg, the B3D header mass) under José's standing
rule of 2026-11-02 (keep recorded values; no refits): the AddBiomechanics fitted dynamics-model mass is never
used to normalize and stays a metadata column only; a missing or non-positive recorded mass leaves the
per-kg and body-weight columns empty. Hip adduction and rotation keep the source
sign (OpenSim adduction +, internal rotation +; frontal and transverse rule not yet adopted).

This module reads only what the caller hands it and writes nothing. scientific_approval is false.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = ROOT / "contributor_tools/common/sign_application.py"


def load_by_path(name, path):
    """Import one repository module from its file without package __init__ files (as the UM21 adapter)."""
    path = Path(path).resolve()
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
    if Path(module.__file__).resolve() != path:
        raise ImportError(f"{name} is already imported from {module.__file__}, not {path}")
    return module


sa = load_by_path("contributor_tools.common.sign_application", HOOK_FILE)

ADAPTER_PATH = Path(__file__).resolve()
MAPPING_VERSION = "hist06-addb-mapping/0.1"
MAPPING_RECORD = "docs/quality/audits/hist06-addbiomechanics-mapping.json"
PROBE_RECORD = "docs/quality/audits/hist06-addb-mapping-probe.json"
STUDIES = {  # HIST-05 slug -> (dataset key in the audited-sign table, AddBiomechanics folder)
    "fa16": ("FA16", "Falisse2017_Formatted_No_Arm"),
    "ta21": ("TA21", "Tan2021_Formatted_No_Arm"),
    "ta22": ("TA22", "Tan2022_Formatted_No_Arm"),
}
H25 = ("pelvis_tilt", "pelvis_list", "pelvis_rotation", "pelvis_tx", "pelvis_ty", "pelvis_tz",
       "hip_flexion_r", "hip_adduction_r", "hip_rotation_r", "knee_angle_r", "knee_angle_r_beta", "ankle_angle_r",
       "subtalar_angle_r", "mtp_angle_r", "hip_flexion_l", "hip_adduction_l", "hip_rotation_l", "knee_angle_l",
       "knee_angle_l_beta", "ankle_angle_l", "subtalar_angle_l", "mtp_angle_l", "lumbar_extension",
       "lumbar_bending", "lumbar_rotation")
COUPLED = ("knee_angle_r_beta", "knee_angle_l_beta")
H23 = tuple(c for c in H25 if c not in COUPLED)
DOF = {c: i for i, c in enumerate(H23)}  # coordinate -> DOF column index (H23, probe section dof_order)
GRAVITY = (0.0, -9.80665, 0.0)
SIDES = {"right": "r", "left": "l"}
OTHER = {"right": "left", "left": "right"}
CONTACT = {"right": "calcn_r", "left": "calcn_l"}
HOOK_JOINTS = (("hip", "hip_flexion_{s}"), ("knee", "knee_angle_{s}"), ("ankle", "ankle_angle_{s}"))
LOCOHUB_JOINT = {"hip": "hip_flexion", "knee": "knee_flexion", "ankle": "ankle_dorsiflexion"}
FRONTAL_TRANSVERSE = (("hip_adduction", "hip_adduction_{s}"), ("hip_rotation", "hip_rotation_{s}"))
SEGMENTS = ("thigh", "shank", "foot")
CLEAN = "notMissingGRF"
HS_THRESHOLD_N = 50.0
HS_MIN_OFF_FRAMES = 5
STRIDE_S = (0.4, 2.5)
N_SAMPLES = 150
BLOCK_FRAMES = 100
DIRECTION_MAX_DEG = 45.0
MIN_TRAVEL_M_S = 0.2
STANCE_MIN_FRAMES = 10
PELVIS_SOURCE = ("derived: asin(up component of the pelvis anterior axis); ground_pelvis = Rz(dof00) Rx(dof01) "
                 "Ry(dof02), body-fixed (dynamics_model.osim); posterior tilt (front up) positive by construction")
COP_REGISTRATION = ("none needed: no markers; CoP and GRF both in the AddBiomechanics world frame, projected on "
                    "the trial's walking direction and up")

TAN_RUN_RE = re.compile(r"(nike|mini)_(SR|SI|baseline)_(24|28)")
TAN_WALK = frozenset({"baseline", "fpa", "step_width", "trunk_sway"})
FALISSE_RE = re.compile(r"(Gait|STS|StairUp)_[0-9]+")

TASK_DECISION = "D-HIST-06-2"
NORMALIZATION_MASS_COLUMN = "entered_mass_kg"  # recorded participant mass (B3D header); never the fitted mass
NORMALIZATION_RULE = ("recorded participant mass (entered_mass_kg) under José's standing rule of 2026-11-02: "
                      "keep recorded values, no refits; the fitted dynamics-model mass is not used")
TASK_OPTIONS = {  # answer -> {slug: {name family: task}}; letters equal the decision in the HIST-06 handoff
    "A": {"ta22": {"baseline": "level_walking"}, "fa16": {"Gait": "level_walking", "StairUp": "stair_ascent"}},
    "B": {"ta22": {n: "level_walking" for n in TAN_WALK}, "fa16": {"Gait": "level_walking", "StairUp": "stair_ascent"}},
    "C": {"ta22": {n: "level_walking" for n in TAN_WALK},
          "fa16": {"Gait": "level_walking", "StairUp": "stair_ascent", "STS": "sit_to_stand"}},
}
# Model definition from the forward-kinematics probe (documentation only: it never applies a sign).
MODEL_DOCUMENTATION = {
    "pelvis_tilt": "pelvis pitch derived from the model's ground_pelvis transform: front up (posterior) positive",
    "hip_angle": "hip_flexion_<s>: +q rotates the femur counterclockwise about +z (flexion), both sides",
    "knee_angle": "knee_angle_<s> (walker_knee, range 0 to 2.09 rad): +q rotates the tibia clockwise about +z (flexion)",
    "ankle_angle": "ankle_angle_<s>: +q rotates the talus counterclockwise about +z (dorsiflexion)",
    "hip_moment": "generalized force along hip_flexion_<s>: internal, same sense as the coordinate",
    "knee_moment": "generalized force along knee_angle_<s>: internal, same sense as the coordinate",
    "ankle_moment": "generalized force along ankle_angle_<s>: internal, same sense as the coordinate",
}


class ModelMismatchError(ValueError):
    """The participant's model or columns do not match the evidence the mapping rests on."""


class OutOfScopeError(ValueError):
    """A member, participant or recording id outside HIST-06 (or a dropped Falisse subject)."""


# ---------------------------------------------------------------- scope, ids and task rule
def study_of(member):
    hits = [s for s, (_, folder) in STUDIES.items() if f"/{folder}/" in member]
    if len(hits) != 1:
        raise OutOfScopeError(f"not a HIST-06 study member: {member!r}")
    return hits[0]


def recording_pattern(slug):
    folder = STUDIES[slug][1]
    return rf"(train|test)/No_Arm/{folder}/([A-Za-z0-9_]+)/\2\.b3d#trial[0-9]+"


def check_recording(slug, recording):
    if not isinstance(recording, str) or not re.fullmatch(recording_pattern(slug), recording):
        raise OutOfScopeError(f"recording {recording!r} is not a {slug} HIST-05 source_recording_id")
    subject = recording.split("/")[3]
    if slug == "fa16" and subject in ("subject_1", "subject_7", "subject_8"):
        raise OutOfScopeError(f"{subject} is dropped by D-HIST-04-2 = A")
    return subject


def protocol_match(slug, original):
    """True when the original trial name matches the study's protocol pattern (MAP-TAN-TASK)."""
    if not isinstance(original, str):
        return False
    if slug == "ta21":
        return TAN_RUN_RE.fullmatch(original) is not None
    if slug == "ta22":
        return original in TAN_WALK
    return FALISSE_RE.fullmatch(original) is not None


def _family(slug, original):
    return original if slug == "ta22" else original.split("_")[0]


def task_label(slug, original, task_answer):
    """(task or None, rule text). No label for non-protocol names; Tan walking and Falisse only by decision."""
    if not protocol_match(slug, original):
        return None, (f"MAP-TAN-TASK: original name {original!r} does not match the {slug} protocol pattern; no "
                      "task label, in no task table, kept with its source name")
    if slug == "ta21":
        return "run", "Tan running protocol name (HIST-04 table): run"
    if task_answer not in TASK_OPTIONS:
        return None, f"pending {TASK_DECISION} (answer {task_answer!r}): no task label yet"
    task = TASK_OPTIONS[task_answer].get(slug, {}).get(_family(slug, original))
    return task, f"{TASK_DECISION} = {task_answer}: {_family(slug, original)} -> {task}"


def locomotion(slug, original):
    """(kind, detector task assumption) for the sign evidence; not a release label. kind: treadmill,
    overground or None (no forward locomotion: sit-to-stand, calibration, non-protocol names)."""
    if not protocol_match(slug, original):
        return None, None
    if slug == "ta21":
        return "treadmill", "run"
    if slug == "ta22":
        return "treadmill", "level_walking"
    fam = _family(slug, original)
    return {"Gait": ("overground", "level_walking"), "StairUp": ("overground", "stair_ascent")}.get(fam, (None, None))


def decision_answers(backlog):
    """Recorded answers of the HIST-06 decisions (None when absent, open or deferred)."""
    out = {}
    for key, did, options in (("task", TASK_DECISION, TASK_OPTIONS),):
        d = next((x for x in backlog.get("decisions", []) if x.get("id") == did), None)
        ans = None if d is None else d.get("answer")
        out[key] = ans if ans in options else None
        out[key + "_record"] = {"id": did, "answer": ans,
                                "answered_at_utc": None if d is None else d.get("answered_at_utc")}
    return out


# ---------------------------------------------------------------- model checks
def _floats(s):
    return [float(x) for x in s.split()]


def check_model(osim_bytes, conversion, column_names):
    """Facts about the participant model, or ModelMismatchError. Reads only the given bytes and lists."""
    problems = []
    if hashlib.sha256(osim_bytes).hexdigest() != conversion.get("dynamics_model_sha256"):
        problems.append("dynamics_model.osim sha256 differs from conversion.json")
    text = osim_bytes.decode("utf8", "replace")
    coords = re.findall(r"<Coordinate\s+name=\"([^\"]*)\"", text)
    if tuple(coords) != H25 or tuple(conversion.get("model_coordinates") or ()) != H25:
        problems.append("model coordinates differ from the 25 the mapping was built on")
    for s in "rl":
        m = re.search(rf"<CoordinateCouplerConstraint\s+name=\"[^\"]*\">((?:(?!</CoordinateCouplerConstraint>).)*"
                      rf"<dependent_coordinate_name>\s*knee_angle_{s}_beta\s*<(?:(?!</CoordinateCouplerConstraint>).)*)"
                      r"</CoordinateCouplerConstraint>", text, re.S)
        ok = False
        if m:
            b = m.group(1)
            ind = re.search(r"<independent_coordinate_names>\s*([^<]*?)\s*<", b)
            coef = re.search(r"<coefficients>([^<]*)</coefficients>", b)
            enforced = re.search(r"<isEnforced>\s*true\s*<", b)
            ok = bool(ind and ind.group(1) == f"knee_angle_{s}" and coef and _floats(coef.group(1)) == [1.0, 0.0]
                      and enforced)
        if not ok:
            problems.append(f"no enforced coupler knee_angle_{s}_beta = knee_angle_{s}")
    gp = re.search(r"<CustomJoint\s+name=\"ground_pelvis\">(.*?)</CustomJoint>", text, re.S)
    want = (("rotation1", "pelvis_tilt", [0.0, 0.0, 1.0]), ("rotation2", "pelvis_list", [1.0, 0.0, 0.0]),
            ("rotation3", "pelvis_rotation", [0.0, 1.0, 0.0]))
    if not gp:
        problems.append("no ground_pelvis CustomJoint")
    else:
        for name, coord, axis in want:
            ta = re.search(rf"<TransformAxis\s+name=\"{name}\">(.*?)</TransformAxis>", gp.group(1), re.S)
            ok = (ta and re.search(rf"<coordinates>\s*{coord}\s*<", ta.group(1))
                  and _floats(re.search(r"<axis>([^<]*)<", ta.group(1)).group(1)) == axis
                  and re.search(r"<LinearFunction[^>]*>\s*<coefficients>\s*1\s+0\s*<", ta.group(1)))
            if not ok:
                problems.append(f"ground_pelvis {name} is not {coord} about {axis} (linear 1 0)")
        oris = re.findall(r"<orientation>([^<]*)</orientation>", gp.group(1))
        if len(oris) != 2 or any(_floats(o) != [0.0, 0.0, 0.0] for o in oris):
            problems.append("ground_pelvis offset frames are not unrotated")
    g = re.search(r"<gravity>([^<]*)</gravity>", text)
    if not g or not np.allclose(_floats(g.group(1)), GRAVITY, atol=1e-9):
        problems.append("model gravity is not (0, -9.80665, 0): +y is not up")
    dofs = sorted(c for c in column_names if re.fullmatch(r"dof[0-9]{2}_pos", c))
    if dofs != [f"dof{i:02d}_pos" for i in range(len(H23))]:
        problems.append(f"expected {len(H23)} DOF position columns dof00-dof22, found {len(dofs)}")
    for side in SIDES:
        for q in ("force", "cop"):
            for a in "xyz":
                if f"{CONTACT[side]}_{q}_{a}" not in column_names:
                    problems.append(f"missing {CONTACT[side]}_{q}_{a}")
    if problems:
        raise ModelMismatchError("; ".join(problems))
    return {"coordinates": "H25 (dynamics_model.osim)", "dof_rule": "H23: model order without the coupled "
            "knee_angle_r_beta and knee_angle_l_beta (enforced couplers, linear 1 0)", "gravity": list(GRAVITY),
            "ground_pelvis": "Rz(pelvis_tilt) Rx(pelvis_list) Ry(pelvis_rotation), unrotated offsets",
            "dynamics_model_sha256": conversion.get("dynamics_model_sha256")}


def required_columns(column_names):
    cols = [f"dof{DOF[c]:02d}_{q}" for c in ("pelvis_tilt", "pelvis_list", "pelvis_rotation") for q in ("pos",)]
    for side in SIDES:
        s = SIDES[side]
        for _, coord in HOOK_JOINTS + FRONTAL_TRANSVERSE:
            cols += [f"dof{DOF[coord.format(s=s)]:02d}_{q}" for q in ("pos", "tau")]
        cols += [f"{CONTACT[side]}_{q}_{a}" for q in ("force", "cop") for a in "xyz"]
    cols += ["com_vel_x", "com_vel_z", "missing_grf_reason", "time_s", "source_frame_index", "source_timestep_s",
             "source_trial_index", "source_recording_id", "observation_id", "source_original_trial_name",
             "subject", "task_info", "subject_metadata", "entered_mass_kg", "dynamics_model_mass_kg"]
    missing = [c for c in cols if c not in column_names]
    if missing:
        raise ModelMismatchError(f"frames file lacks {missing}")
    return list(dict.fromkeys(cols))


# ---------------------------------------------------------------- geometry
def pelvis_anterior_axis(tilt, lst, rot):
    """First column of Rz(tilt) Rx(list) Ry(rotation): the pelvis anterior axis in the world frame."""
    ct, st, cl, sl, cr, sr = (np.cos(tilt), np.sin(tilt), np.cos(lst), np.sin(lst), np.cos(rot), np.sin(rot))
    v = np.stack([cr, sl * sr, -cl * sr], -1)  # Rx(l) Ry(r) e_x, with Ry(r) e_x = (cr, 0, -sr)
    x = ct * v[..., 0] - st * v[..., 1]
    y = st * v[..., 0] + ct * v[..., 1]
    return np.stack([x, y, v[..., 2]], -1)


def pelvis_pitch(tilt, lst, rot):
    """Rule-B pelvis sagittal angle: asin of the up component of the anterior axis (front up positive)."""
    a = pelvis_anterior_axis(tilt, lst, rot)
    return np.arcsin(np.clip(a[..., 1], -1.0, 1.0))


def horizontal_unit(v):
    h = np.array([v[0], 0.0, v[2]], float)
    n = np.linalg.norm(h)
    return None if not np.isfinite(n) or n == 0 else h / n


def frame_basis(x_dir):
    """Rule-B basis from a horizontal walking direction: x', y' = up, z' = x' cross y'."""
    x = np.asarray(x_dir, float)
    y = np.array([0.0, 1.0, 0.0])
    return x, y, np.cross(x, y)


def _runs(mask):
    """(start, stop) of runs of True."""
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def walking_direction(kind, heading, com_vel_xz=None, cops=None, fys=None):
    """{'direction': unit (3,) or None, 'basis', 'angle_to_facing_deg', 'ok', 'reason'}.

    treadmill: principal horizontal axis of within-stance CoP displacement (both feet; stance = runs of
    vertical force > HS_THRESHOLD_N of at least STANCE_MIN_FRAMES frames), oriented with the facing direction.
    overground: mean horizontal COM velocity (at least MIN_TRAVEL_M_S). Either must lie within
    DIRECTION_MAX_DEG of the facing direction."""
    out = {"direction": None, "basis": None, "angle_to_facing_deg": None, "ok": False, "reason": None}
    if heading is None:
        out["reason"] = "no stable facing direction"
        return out
    if kind == "overground":
        v = np.nanmean(np.asarray(com_vel_xz, float), axis=0)
        speed = float(np.hypot(v[0], v[1]))
        if not np.isfinite(speed) or speed < MIN_TRAVEL_M_S:
            out["reason"] = f"mean horizontal COM speed {speed:.3f} m/s below {MIN_TRAVEL_M_S}"
            return out
        d = np.array([v[0], 0.0, v[1]]) / speed
        out["basis"] = f"mean horizontal COM velocity ({speed:.3f} m/s)"
    elif kind == "treadmill":
        disp = []
        for cop, fy in zip(cops, fys):
            on = np.isfinite(fy) & (fy > HS_THRESHOLD_N) & np.all(np.isfinite(cop), axis=1)
            for a, b in _runs(on):
                if b - a >= STANCE_MIN_FRAMES:
                    disp.append([cop[b - 1, 0] - cop[a, 0], cop[b - 1, 2] - cop[a, 2]])
        if len(disp) < 5:
            out["reason"] = f"{len(disp)} stance CoP displacements (need 5)"
            return out
        disp = np.asarray(disp)
        w, vec = np.linalg.eigh(disp.T @ disp)
        axis = vec[:, -1]
        d = np.array([axis[0], 0.0, axis[1]])
        if d @ heading < 0:
            d = -d
        out["basis"] = (f"principal axis of {len(disp)} within-stance CoP displacements (axial; eigenvalue ratio "
                        f"{w[-1] / max(w[0], 1e-12):.1f}), oriented with the pelvis facing direction")
    else:
        out["reason"] = "no forward locomotion in this trial (forward undefined until D-GT23-C01-1)"
        return out
    ang = math.degrees(math.acos(max(-1.0, min(1.0, float(d @ heading)))))
    out.update(direction=d, angle_to_facing_deg=round(ang, 2))
    if ang > DIRECTION_MAX_DEG:
        out["reason"] = f"walking direction {ang:.1f} deg from the facing direction (max {DIRECTION_MAX_DEG})"
        return out
    out["ok"] = True
    return out


def facing(tilt, lst, rot):
    """Trial facing direction (horizontal unit vector) from the pelvis anterior axis, with its resultant."""
    a = pelvis_anterior_axis(tilt, lst, rot)
    yaw = np.arctan2(-a[:, 2], a[:, 0])
    z = np.mean(np.exp(1j * yaw))
    res = float(abs(z))
    if res < 0.9:
        return None, res
    m = math.atan2(z.imag, z.real)
    return np.array([math.cos(m), 0.0, -math.sin(m)]), res


# ---------------------------------------------------------------- units for the hook
def heel_strikes(fy):
    """Frames where the vertical force rises to >= HS_THRESHOLD_N after >= HS_MIN_OFF_FRAMES finite frames below."""
    fy = np.asarray(fy, float)
    below = np.isfinite(fy) & (fy < HS_THRESHOLD_N)
    out = []
    for i in range(HS_MIN_OFF_FRAMES, len(fy)):
        if np.isfinite(fy[i]) and fy[i] >= HS_THRESHOLD_N and below[i - HS_MIN_OFF_FRAMES:i].all():
            out.append(i)
    return out


def stride_pairs(fy, dt):
    """(a, b) 0-based inclusive frames: consecutive heel strikes, 0.4-2.5 s apart, every frame finite."""
    fy = np.asarray(fy, float)
    hs = heel_strikes(fy)
    return [(a, b) for a, b in zip(hs[:-1], hs[1:])
            if STRIDE_S[0] <= (b - a) * dt <= STRIDE_S[1] and np.isfinite(fy[a:b + 1]).all()]


def resample(x, pairs):
    x = np.asarray(x, float)
    out = []
    for a, b in pairs:
        seg = x[a:b + 1]
        src = np.arange(seg.shape[0])
        grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
        if seg.ndim == 1:
            out.append(np.interp(grid, src, seg))
        else:
            out.append(np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1))
    return np.ascontiguousarray(np.array(out, dtype=np.float64))


def blocks(x, n_frames):
    x = np.asarray(x, float)
    k = n_frames // BLOCK_FRAMES
    return np.ascontiguousarray(x[:k * BLOCK_FRAMES].reshape((k, BLOCK_FRAMES) + x.shape[1:]).astype(np.float64))


@dataclass
class Trial:
    slug: str
    recording: str
    subject: str
    original_name: str
    observation_id: str
    dt: float
    data: dict                 # column -> numpy array (one trial, frame order)
    flags: np.ndarray          # missing_grf_reason per frame (object array of str)
    meta: dict = field(default_factory=dict)


def trial_from_table(slug, table):
    """Trial from a pyarrow table holding one source_recording_id (frame order checked)."""
    data = {}
    for c in table.column_names:
        col = table.column(c)
        if c in ("missing_grf_reason", "source_recording_id", "observation_id", "source_original_trial_name",
                 "subject", "task_info", "subject_metadata"):
            data[c] = np.array(col.to_pylist(), dtype=object)
        else:
            data[c] = col.to_numpy(zero_copy_only=False)
    rid = set(data["source_recording_id"].tolist())
    if len(rid) != 1:
        raise ValueError(f"a trial table must hold one source_recording_id, got {len(rid)}")
    fr = data["source_frame_index"]
    if not np.array_equal(fr, np.arange(len(fr))):
        raise ValueError("frames are not in source order 0..n-1")
    steps = set(np.asarray(data["source_timestep_s"]).tolist())
    if len(steps) != 1:
        raise ValueError("more than one source timestep in a trial")
    recording = rid.pop()
    return Trial(slug=slug, recording=recording, subject=check_recording(slug, recording),
                 original_name=data["source_original_trial_name"][0], observation_id=data["observation_id"][0],
                 dt=float(steps.pop()), data=data, flags=data["missing_grf_reason"])


# ---------------------------------------------------------------- per trial
def _col(trial, coord, q):
    return np.asarray(trial.data[f"dof{DOF[coord]:02d}_{q}"], dtype=np.float64)


def grf_world(trial, side):
    """(force (n,3), cop (n,3)) for one foot. Force as recorded on every frame: the missing_grf_reason flag
    blanks nothing (it is carried as a column); only source NaN stays NaN and a recorded zero stays zero. CoP
    is NaN where that foot's recorded vertical force is not positive (the source's (0, 0, 0) placeholder for an
    undefined CoP), independent of the flag."""
    f = np.stack([np.asarray(trial.data[f"{CONTACT[side]}_force_{a}"], np.float64) for a in "xyz"], -1)
    c = np.stack([np.asarray(trial.data[f"{CONTACT[side]}_cop_{a}"], np.float64) for a in "xyz"], -1)
    c = np.where((f[:, 1] > 0)[:, None], c, np.nan)  # NaN > 0 is False: no CoP without a recorded load
    return f, c


def trial_frame(trial):
    """Facing, walking direction and rule-B basis for one trial (dict, JSON-able plus arrays)."""
    tilt, lst, rot = (_col(trial, c, "pos") for c in ("pelvis_tilt", "pelvis_list", "pelvis_rotation"))
    head, res = facing(tilt, lst, rot)
    kind, det_task = locomotion(trial.slug, trial.original_name)
    forces = {s: grf_world(trial, s) for s in SIDES}
    wd = walking_direction(kind, head,
                           com_vel_xz=np.stack([trial.data["com_vel_x"], trial.data["com_vel_z"]], -1),
                           cops=[forces[s][1] for s in SIDES], fys=[forces[s][0][:, 1] for s in SIDES])
    basis = frame_basis(wd["direction"]) if wd["ok"] else None
    return {"facing": head, "facing_resultant": round(res, 4), "kind": kind, "detector_task": det_task,
            "walking": wd, "basis": basis, "forces": forces,
            "pelvis_pitch": pelvis_pitch(tilt, lst, rot)}


def leg_inputs(trial, frame, side):
    """Hook channels (units, samples), unit ids, evidence and facts for one leg."""
    s = SIDES[side]
    f, c = frame["forces"][side]
    n = len(f)
    pairs = stride_pairs(f[:, 1], trial.dt) if frame["kind"] else []
    full = {"pelvis_tilt": frame["pelvis_pitch"]}
    columns = {"pelvis_tilt": PELVIS_SOURCE}
    for j, coord in HOOK_JOINTS:
        name = coord.format(s=s)
        full[f"{j}_angle"] = _col(trial, name, "pos")
        full[f"{j}_moment"] = _col(trial, name, "tau")
        columns[f"{j}_angle"] = f"dof{DOF[name]:02d}_pos ({name}, rad)"
        columns[f"{j}_moment"] = f"dof{DOF[name]:02d}_tau ({name} generalized force, N*m)"
    if frame["basis"] is not None:
        x, y, _ = frame["basis"]
        grf2 = np.stack([f @ x, f[:, 1]], -1)
        cop2 = np.stack([c @ x, c[:, 1]], -1)
    else:
        grf2 = np.stack([np.full(n, np.nan), f[:, 1]], -1)
        cop2 = None
    if pairs:
        unit = "stride"
        chans = {k: resample(v, pairs) for k, v in full.items()}
        ev_grf, ev_cop = resample(grf2, pairs), (resample(cop2, pairs) if cop2 is not None else None)
        durations = np.array([(b - a) * trial.dt for a, b in pairs], dtype=np.float64)
        ids = [f"{trial.recording}:{side}:frames:{a}:{b}" for a, b in pairs]
    else:
        unit = "block"
        k = n // BLOCK_FRAMES
        if k == 0:
            return None
        chans = {key: blocks(v, n) for key, v in full.items()}
        ev_grf, ev_cop = blocks(grf2, n), (blocks(cop2, n) if cop2 is not None else None)
        durations = np.full(k, BLOCK_FRAMES * trial.dt, dtype=np.float64)
        ids = [f"{trial.recording}:{side}:block:{i * BLOCK_FRAMES}:{(i + 1) * BLOCK_FRAMES - 1}" for i in range(k)]
    # timing tests assume stride units: fixed blocks never carry a task assumption
    evidence = {"grf": ev_grf, "grf_unit": "N", "task": frame["detector_task"] if pairs else None,
                "unit_durations_s": durations, "cop_registration": COP_REGISTRATION}
    if ev_cop is not None:
        evidence["cop"] = ev_cop
    return {"side": side, "unit": unit, "pairs": [list(map(int, p)) for p in pairs], "unit_ids": ids,
            "channels": chans, "full": full, "source_columns": columns, "evidence": evidence}


def documentation_items(dataset):
    return [(k, 1, f"{dataset} dynamics_model.osim forward-kinematics probe ({PROBE_RECORD}): {text}",
             f"hist06-model:S-{k.replace('_', '.')}") for k, text in MODEL_DOCUMENTATION.items()]


def apply_trial(trial, detector_sha256, *, backlog_path=sa.BACKLOG_PATH, audited_path=sa.AUDITED_PATH,
                mode="pilot", answers=None):
    """Hook per leg, then continuous published channels, derived segments and velocities for one trial.
    Returns a dict with per-leg applications, the continuous published channels and the trial log."""
    dataset = STUDIES[trial.slug][0]
    frame = trial_frame(trial)
    legs, published, log_legs = {}, {}, {}
    for side in SIDES:
        inp = leg_inputs(trial, frame, side)
        if inp is None:
            log_legs[side] = {"hook": "not run: fewer than one block of frames"}
            continue
        in_hash = {k: sa.array_sha256(a) for k, a in inp["channels"].items()}
        app = sa.run_sign_application(dataset=dataset, leg=side, group_id=f"{trial.recording}:{side}",
                                      recording=trial.recording, unit_ids=inp["unit_ids"],
                                      channels=inp["channels"], detector_sha256=detector_sha256,
                                      source_columns=inp["source_columns"], documentation=documentation_items(dataset),
                                      evidence=inp["evidence"], mode=mode, backlog_path=backlog_path,
                                      audited_path=audited_path)
        if {k: sa.array_sha256(a) for k, a in inp["channels"].items()} != in_hash:
            raise RuntimeError("an adapter input channel changed during sign application")
        ch = app.log["channels"]
        cont = {}
        for k, c in ch.items():
            if c["publication"] == "publish":
                a = inp["full"][k][None, :]
                cont[k] = np.negative(a) if c["multiplier"] == -1 else a.copy()  # exact, as the hook
        legs[side] = {"application": app, "inputs": inp, "continuous": cont}
        log_legs[side] = {"unit": inp["unit"], "units": len(inp["unit_ids"]), "stride_frames": inp["pairs"],
                          "published": sorted(cont), "held": sorted(k for k, c in ch.items() if c["publication"] == "hold"),
                          "multipliers": {k: c["multiplier"] for k, c in ch.items()},
                          "continuous_sha256": {k: sa.array_sha256(a) for k, a in cont.items()},
                          "counts": app.log["counts"]}
    # pelvis: one channel shared by both legs; published only when both legs publish it with one multiplier
    pel = [legs[s]["application"].log["channels"].get("pelvis_tilt") for s in legs]
    pelvis_ok = (len(pel) == 2 and all(p and p["publication"] == "publish" for p in pel)
                 and pel[0]["multiplier"] == pel[1]["multiplier"])
    derived, vel_logs, seg_logs = {}, {}, {}
    for side, leg in legs.items():
        app, cont = leg["application"], dict(leg["continuous"])
        log = json.loads(json.dumps(app.log))
        if not pelvis_ok:
            cont.pop("pelvis_tilt", None)
            if "pelvis_tilt" in log["channels"]:
                log["channels"]["pelvis_tilt"]["publication"] = "hold"
        view = sa.SignApplication(channels=cont, log=log, review=[], report={})
        segs, seg_log = sa.derive_segment_angles(view)
        angles = {k: v for k, v in cont.items() if k.endswith("_angle") or k == "pelvis_tilt"}
        angles.update(segs)
        vels, vel_log = sa.derive_angular_velocities(angles, trial.dt) if angles else ({}, {"derived": {}})
        derived[side] = {**cont, **segs, **vels}
        seg_logs[side], vel_logs[side] = seg_log, vel_log
    return {"frame": frame, "legs": legs, "pelvis_published": pelvis_ok, "channels": derived,
            "log": {"recording": trial.recording, "dataset": dataset, "original_name": trial.original_name,
                    "dt_s": trial.dt, "frames": int(len(trial.flags)),
                    "facing": None if frame["facing"] is None else [round(float(v), 4) for v in frame["facing"]],
                    "facing_resultant": frame["facing_resultant"], "locomotion": frame["kind"],
                    "detector_task_assumption": frame["detector_task"],
                    "walking_direction": {k: (v.round(4).tolist() if isinstance(v, np.ndarray) else v)
                                          for k, v in frame["walking"].items()},
                    "pelvis_published": pelvis_ok, "legs": log_legs, "segments": seg_logs,
                    "velocities": {s: {k: d["from"] for k, d in v.get("derived", {}).items()} for s, v in vel_logs.items()},
                    "grf_frames_flagged_kept": int((trial.flags != CLEAN).sum()),
                    "grf_source_nan_frames": {s: int(np.isnan(frame["forces"][s][0]).any(axis=1).sum()) for s in SIDES},
                    "grf_flag_counts": {str(k): int(v) for k, v in zip(*np.unique(trial.flags.astype(str), return_counts=True))}}}


# ---------------------------------------------------------------- rows
SAGITTAL_COLUMNS = [f"{LOCOHUB_JOINT[j]}_{q}_{r}_{u}" for j in ("hip", "knee", "ankle")
                    for q, u in (("angle", "rad"), ("velocity", "rad_s")) for r in ("ipsi", "contra")]
SEGMENT_COLUMNS = [f"{seg}_sagittal_{q}_{r}_{u}" for seg in SEGMENTS for q, u in (("angle", "rad"), ("velocity", "rad_s"))
                   for r in ("ipsi", "contra")]
MOMENT_COLUMNS = [f"{LOCOHUB_JOINT[j]}_moment_{r}_Nm" for j in ("hip", "knee", "ankle") for r in ("ipsi", "contra")]
FT_COLUMNS = [f"{n}_{q}_{r}_{u}" for n in ("hip_adduction", "hip_rotation")
              for q, u in (("angle", "rad"), ("moment", "Nm")) for r in ("ipsi", "contra")]
GRF_COLUMNS = [f"grf_{a}_{r}_N" for a in ("vertical", "anterior", "lateral") for r in ("ipsi", "contra")]
COP_COLUMNS = [f"cop_{a}_{r}_m" for a in ("anterior", "vertical", "lateral") for r in ("ipsi", "contra")]
NORMALIZED = ([c.replace("_Nm", "_Nm_kg") for c in MOMENT_COLUMNS]
              + [c.replace("_N", "_BW") for c in GRF_COLUMNS])
SIGNAL_COLUMNS = (["pelvis_sagittal_angle_rad", "pelvis_sagittal_velocity_rad_s"] + SAGITTAL_COLUMNS
                  + SEGMENT_COLUMNS + MOMENT_COLUMNS + FT_COLUMNS + GRF_COLUMNS + COP_COLUMNS + NORMALIZED)
ID_STR = ["dataset", "subject", "source_recording_id", "observation_id", "reference_side", "observation_type",
          "task", "task_id", "task_info", "subject_metadata", "source_original_trial_name", "missing_grf_reason",
          "normalization_mass_basis", "mapping_version"]
ID_INT = ["source_trial_index", "source_frame_index"]
ID_FLT = ["time_s", "normalization_mass_kg"]


def trial_rows(trial, result, answers):
    """Columns (dict name -> array) for both reference legs of one trial (2 x frames rows)."""
    n = len(trial.flags)
    task, rule = task_label(trial.slug, trial.original_name, answers.get("task"))
    recorded = np.asarray(trial.data[NORMALIZATION_MASS_COLUMN], float)
    if len(set(recorded.tolist())) > 1 and np.isfinite(recorded).any():
        raise ValueError(f"{NORMALIZATION_MASS_COLUMN} is not constant in {trial.recording}")
    mass = float(recorded[0]) if len(recorded) else math.nan
    mass_ok = bool(np.isfinite(mass) and mass > 0)  # missing or non-positive: per-kg columns stay empty
    if not mass_ok:
        mass = math.nan
    info = json.loads(trial.data["task_info"][0])
    info.update({"task_rule": rule, "in_task_table": task is not None, "protocol_match":
                 protocol_match(trial.slug, trial.original_name),
                 "detector_task_assumption": result["frame"]["detector_task"],
                 "walking_direction_basis": result["frame"]["walking"]["basis"],
                 "walking_direction_ok": result["frame"]["walking"]["ok"],
                 "mapping_record": MAPPING_RECORD})
    info_json = json.dumps(info, sort_keys=True)
    basis = result["frame"]["basis"]
    out = {c: [] for c in ID_STR + ID_INT + ID_FLT + SIGNAL_COLUMNS}
    nanv = np.full(n, np.nan)

    def get(side, name):
        a = result["channels"].get(side, {}).get(name)
        return nanv if a is None else np.asarray(a).reshape(-1)

    for ref in SIDES:
        roles = {"ipsi": ref, "contra": OTHER[ref]}
        cols = {}
        pel = get(ref, "pelvis_tilt") if result["pelvis_published"] else nanv
        cols["pelvis_sagittal_angle_rad"] = pel
        cols["pelvis_sagittal_velocity_rad_s"] = (get(ref, "pelvis_tilt_velocity") if result["pelvis_published"] else nanv)
        for role, side in roles.items():
            s = SIDES[side]
            for j in ("hip", "knee", "ankle"):
                stem = LOCOHUB_JOINT[j]
                cols[f"{stem}_angle_{role}_rad"] = get(side, f"{j}_angle")
                cols[f"{stem}_velocity_{role}_rad_s"] = get(side, f"{j}_angle_velocity")
                cols[f"{stem}_moment_{role}_Nm"] = get(side, f"{j}_moment")
            for seg in SEGMENTS:
                cols[f"{seg}_sagittal_angle_{role}_rad"] = get(side, f"{seg}_angle")
                cols[f"{seg}_sagittal_velocity_{role}_rad_s"] = get(side, f"{seg}_angle_velocity")
            for name, coord in FRONTAL_TRANSVERSE:  # source sign (OpenSim named direction); no hook
                c = coord.format(s=s)
                cols[f"{name}_angle_{role}_rad"] = _col(trial, c, "pos")
                cols[f"{name}_moment_{role}_Nm"] = _col(trial, c, "tau")
            f, cp = result["frame"]["forces"][side]
            cols[f"grf_vertical_{role}_N"] = f[:, 1]
            cols[f"cop_vertical_{role}_m"] = cp[:, 1]
            if basis is not None:
                x, _, z = basis
                out_sign = 1.0 if side == "right" else -1.0  # lateral = outward for each leg
                cols[f"grf_anterior_{role}_N"] = f @ x
                cols[f"grf_lateral_{role}_N"] = out_sign * (f @ z)
                cols[f"cop_anterior_{role}_m"] = cp @ x
                cols[f"cop_lateral_{role}_m"] = out_sign * (cp @ z)
            else:
                for k in (f"grf_anterior_{role}_N", f"grf_lateral_{role}_N", f"cop_anterior_{role}_m",
                          f"cop_lateral_{role}_m"):
                    cols[k] = nanv
        for c in MOMENT_COLUMNS:
            cols[c.replace("_Nm", "_Nm_kg")] = cols[c] / mass if mass_ok else nanv
        for c in GRF_COLUMNS:
            cols[c.replace("_N", "_BW")] = cols[c] / (mass * -GRAVITY[1]) if mass_ok else nanv
        ids = {"dataset": trial.slug, "subject": trial.subject, "source_recording_id": trial.recording,
               "observation_id": trial.observation_id, "reference_side": ref,
               "observation_type": "continuous_recording", "task": task, "task_id": trial.original_name,
               "task_info": info_json, "subject_metadata": trial.data["subject_metadata"][0],
               "source_original_trial_name": trial.original_name,
               "normalization_mass_basis": (NORMALIZATION_RULE if mass_ok else
                                            f"{NORMALIZATION_RULE}; recorded mass missing or not positive: "
                                            "per-kg and body-weight columns empty"),
               "mapping_version": MAPPING_VERSION}
        for k, v in ids.items():
            out[k].extend([v] * n)
        out["missing_grf_reason"].extend(trial.flags.tolist())
        out["source_trial_index"].extend(np.asarray(trial.data["source_trial_index"]).tolist())
        out["source_frame_index"].extend(np.asarray(trial.data["source_frame_index"]).tolist())
        out["time_s"].extend(np.asarray(trial.data["time_s"], float).tolist())
        out["normalization_mass_kg"].extend([mass] * n)
        for c in SIGNAL_COLUMNS:
            out[c].extend(np.asarray(cols[c], float).tolist())
    return out, {"task": task, "task_rule": rule, "in_task_table": task is not None,
                 "normalization_mass_kg": mass if mass_ok else None}


def arrow_schema():
    import pyarrow as pa
    return pa.schema([(c, pa.string()) for c in ID_STR] + [(c, pa.int64()) for c in ID_INT]
                     + [(c, pa.float64()) for c in ID_FLT + SIGNAL_COLUMNS])
