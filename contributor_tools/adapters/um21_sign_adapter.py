"""UMich 2021 (UM21) treadmill adapter for the CORE-11 sign-application hook (task CORE-11-P-UM21).

Per recording (``ABxx/<condition>`` in Streaming.mat, Tread) and leg, the adapter

1. refuses an excluded recording before touching any data. D-UM21-T02-1 = A excludes the five
   recordings that fail the UM21-T02 task-clock check (AB01/d10, AB01/d5, AB08/i10, AB09/i10,
   AB10/i0), and AB01/i5 (its motion arrays are a copy of AB01/i10 and its clock check fails). The
   backlog decision must still carry answer A, or the adapter refuses to run;
2. reads the untransformed source channels, component 1 of each Plug-in Gait triple, one recording at a
   time. The reading follows contributor_tools/probe_core04_um21.py: exact zero triples are NaN, strides
   are consecutive heel strikes 50-250 frames apart (UM21-C03 rule), and each stride is resampled to 150
   samples. The only transform is the unit conversion deg -> rad; moments (N*m/kg) and powers (W/kg, the
   first filled slot) stay as stored. Everything is float64;
3. builds the detector evidence exactly as that probe did: sagittal markers, GRF on the foot, CoP
   registered by the UM21-C03 midpoint rule, task, body mass from ParticipantDetails, stride durations;
4. calls ``sign_application.run_sign_application`` with dataset "UM21", the source recording id and the
   declared detector build (a full sha256; the hook refuses any other build). Adapters never pass signs:
   the audited UM21 signs and the AB04/i0 pelvis correction come from the committed table;
5. AFTER the hook, derives thigh, shank and foot angles with ``derive_segment_angles`` from the
   published channels, and the pelvis, thigh, shank and foot sagittal velocities with
   ``derive_angular_velocities`` from the published pelvis tilt and those derived angles (spacing =
   stride duration / 149, as the UM21 phase converter).

Condition F2 (UM21-P02 verifier): segment angles and their velocities are never read from Streaming.mat,
from the UM21 MATLAB converters, or from contributor_tools/reconvert_umich_streaming.py (lines 91-92 build
thigh and shank from the source-convention pelvis). The adapter passes no segment angle and no
``*_velocity`` channel to the hook and checks that it does not.

Power: the first filled slot must equal the slot the UM21-C03 kinetic-layout record assigns to the recording
(layout 2: component 3 for every joint; otherwise component 1), or the recording fails (PowerSlotError).

The hook is imported from its file (no package __init__ runs). This module reads only what the caller hands
it (an open h5py file or a synthetic stand-in) and the UM21-C03 layout record, and writes nothing. ``scientific_approval`` is false; a pilot result is not a release.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = ROOT / "contributor_tools/common/sign_application.py"


def load_by_path(name, path):
    """Import one repository module from its file, without running package __init__ files (the hook needs only
    the standard library and numpy). An already imported module of that name is reused only when it is the
    same file, so the package import and this path import give one module object."""
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

DATASET = "UM21"
ADAPTER_PATH = Path(__file__).resolve()
RATE_HZ = 100.0  # UM21 joint-angle frame rate (UM21-C03)
PLATE_SAMPLES_PER_FRAME = 10
N_SAMPLES = 150
STRIDE_FRAMES = (50, 250)
RECORDING_RE = re.compile(r"(AB[0-9]{2})/(d10|d5|i0|i5|i10)")
NOMINAL_SLOPE_DEG = {"d10": 10.0, "d5": 5.0, "i0": 0.0, "i5": 5.0, "i10": 10.0}  # README p.2 (UM21-C03)
TASK = {"i0": "level_walking", "i5": "incline_walking", "i10": "incline_walking",
        "d5": "decline_walking", "d10": "decline_walking"}
UP = np.array([0.0, 0.0, 1.0])  # marker frame is gravity-aligned, z up (UM21-C03 plate geometry)
COP_REGISTRATION = ("midpoint rule (UM21-C03): over stance, mean CoP forward = mean heel-toe marker "
                    "midpoint forward; median CoP height = median lowest foot marker height; one constant "
                    "shift per leg and recording; independent of the moment channels")
# Power storage layout per recording (UM21-C03 kinetic_layout, a bound file of the pilot): layout 2 stores
# +(M x w) in component 3 only (components 1 and 2 zero); layout 1 fills components 1-3, component 1 =
# -(M x w). The adapter fails a recording whose first filled slot disagrees with this record.
C03_PATH = ROOT / "docs/quality/audits/um21-c03-conventions.json"
POWER_SLOT = {1: 1, 2: 3}
ANGLES = (("pelvis_tilt", "Pelvis"), ("hip_angle", "Hip"), ("knee_angle", "Knee"), ("ankle_angle", "Ankle"))
JOINTS = (("hip", "Hip"), ("knee", "Knee"), ("ankle", "Ankle"))
LEGS = {"R": "right", "L": "left"}

# D-UM21-T02-1 = A (answered 2026-10-31T06:18:26Z). AB01/i5 leaves under every option (UM21-T02 census).
EXCLUSION_DECISION = {"id": "D-UM21-T02-1", "answer": "A", "task": "UM21-T02"}
_CLOCK = "fails the UM21-T02 treadmill task-clock check; excluded by D-UM21-T02-1 = A"
EXCLUDED = {
    "AB01/d10": _CLOCK, "AB01/d5": _CLOCK, "AB08/i10": _CLOCK, "AB09/i10": _CLOCK, "AB10/i0": _CLOCK,
    "AB01/i5": ("motion arrays are a byte copy of AB01/i10 and the task-clock check fails; held out under "
                "every option of D-UM21-T02-1 and excluded by its answer A"),
}
STRIDE_RULE = ("consecutive source heel strikes (events/<side>HS, 1-based frames) a, b with a >= 1, "
               "b <= frames and 50 <= b - a <= 250; frames a..b inclusive resampled to 150 samples by linear "
               "interpolation (UM21-C03 rule, as contributor_tools/probe_core04_um21.py)")
ORDER = ("exclusion check", "read untransformed source channels and evidence",
         "run_sign_application (bound build, committed audited-sign table)",
         "derive_segment_angles from published channels",
         "derive_angular_velocities from the published pelvis tilt and the derived segment angles")


class ExcludedRecordingError(ValueError):
    """The recording is excluded from the UM21 treadmill scope by a recorded decision."""


class PowerSlotError(ValueError):
    """A recording's filled power slot disagrees with the UM21-C03 kinetic-layout record."""


def power_layout(c03_path=C03_PATH):
    """{'layout_2': frozenset of recording ids, 'source': path, 'sha256': of the bytes read}."""
    data = Path(c03_path).read_bytes()
    rec = json.loads(data)["kinetic_layout"]["power_layout_2_recordings"]
    if not rec or not all(isinstance(r, str) and RECORDING_RE.fullmatch(r) for r in rec):
        raise ValueError("UM21-C03 kinetic_layout.power_layout_2_recordings is empty or malformed")
    return {"layout_2": frozenset(rec), "source": sa._rel(c03_path), "sha256": hashlib.sha256(data).hexdigest()}


def expected_power_slot(recording, layout):
    """(layout number, 1-based source component) the C03 record assigns to every joint of the recording."""
    n = 2 if recording in layout["layout_2"] else 1
    return n, POWER_SLOT[n]


@dataclass
class LegInputs:
    side: str                # 'R' or 'L'
    leg: str                 # 'right' or 'left'
    pairs: list              # (a, b) 1-based heel-strike frames per unit
    unit_ids: list
    channels: dict           # logical name -> float64 (units, 150), source convention
    source_columns: dict
    evidence: dict           # detect_leg keyword arguments
    unit_durations_s: np.ndarray
    power_slots: dict        # joint -> 1-based source component used
    facts: dict


@dataclass
class LegResult:
    recording: str
    leg: str
    group_id: str
    unit_ids: list
    application: sa.SignApplication
    published: dict          # logical name -> published (rule-B) array, published channels only
    segments: dict           # thigh/shank/foot_angle derived after the hook
    segment_log: dict
    velocities: dict         # <angle>_velocity derived after the hook
    velocity_log: dict
    adapter_log: dict


# ---------------------------------------------------------------- scope
def check_recording(recording):
    """(subject, condition) for an in-scope recording id; refuses excluded or malformed ids."""
    if not isinstance(recording, str):
        raise ValueError(f"recording id must be a string, got {type(recording).__name__}")
    m = RECORDING_RE.fullmatch(recording)
    if not m:
        raise ValueError(f"recording {recording!r} is not a UM21 treadmill id (ABxx/d10|d5|i0|i5|i10)")
    if recording in EXCLUDED:
        raise ExcludedRecordingError(f"{recording} refused: {EXCLUDED[recording]}")
    return m.group(1), m.group(2)


def check_exclusion_decision(backlog):
    """The recorded decision behind EXCLUDED, from a parsed backlog; refuses when it is not answered A."""
    dec = next((d for d in backlog.get("decisions", []) if d.get("id") == EXCLUSION_DECISION["id"]), None)
    if dec is None or dec.get("answer") != EXCLUSION_DECISION["answer"]:
        raise ValueError(f"{EXCLUSION_DECISION['id']} answer is "
                         f"{None if dec is None else dec.get('answer')!r}, not {EXCLUSION_DECISION['answer']!r}: "
                         "the UM21 exclusion list no longer matches the decision; update the adapter first")
    return {"id": dec["id"], "answer": dec["answer"], "answered_at_utc": dec.get("answered_at_utc"),
            "excluded": dict(EXCLUDED)}


# ---------------------------------------------------------------- bounded reading (as probe_core04_um21.py)
def strides(hs, length):
    hs = np.asarray(hs).ravel()
    if not np.all(np.isfinite(hs)) or not np.array_equal(hs, np.floor(hs)):
        raise ValueError("heel-strike frames must be finite integers")
    hs = hs.astype(int)
    lo, hi = STRIDE_FRAMES
    return [(int(a), int(b)) for a, b in zip(hs[:-1], hs[1:]) if a >= 1 and b <= length and lo <= b - a <= hi]


def resample(x, pairs):
    """(n,) or (n, k) frame series -> (units, 150) or (units, 150, k) on each stride a..b (1-based, inclusive)."""
    x = np.asarray(x, float)
    out = []
    for a, b in pairs:
        seg = x[a - 1:b]
        src = np.arange(seg.shape[0])
        grid = np.linspace(0, seg.shape[0] - 1, N_SAMPLES)
        if seg.ndim == 1:
            out.append(np.interp(grid, src, seg))
        else:
            out.append(np.stack([np.interp(grid, src, seg[:, k]) for k in range(seg.shape[1])], -1))
    return np.array(out, dtype=np.float64)


def rot_x(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def participant_mass(handle, subject):
    """Bodymass (kg) from Streaming/<subject>/ParticipantDetails (cell array of name, value, unit), as the
    UM21 converters read it. None if absent or not positive (never invented)."""
    group = handle[f"Streaming/{subject}"]
    if "ParticipantDetails" not in group:
        return None
    cells = group["ParticipantDetails"][()]

    def val(ref):
        a = handle[ref][()]
        cls = handle[ref].attrs.get("MATLAB_class", b"")
        if (cls.decode("ascii", "replace") if isinstance(cls, bytes) else str(cls)) == "char":
            return "".join(chr(c) for c in np.asarray(a).ravel())
        return np.asarray(a, float).ravel()
    for r in range(cells.shape[1]):
        name, value, unit = (val(cells[c, r]) for c in range(3))
        if name == "Bodymass" and unit == "kg" and np.size(value) == 1 and value[0] > 0:
            return float(value[0])
    return None


def read_recording(handle, subject, condition, det, expected_slot=None):
    """Untransformed channels and evidence for both legs of one recording. ``det``: the bound detector
    module (sign_application.load_bound_detector), so evidence helpers are the bytes the hook runs.
    expected_slot: the power component the UM21-C03 layout record assigns; a joint whose first filled
    slot differs (or that has none) raises PowerSlotError."""
    base = f"Streaming/{subject}/Tread/{condition}"
    trial = handle[base]
    n = trial["jointAngles"]["RPelvisAngles"].shape[1]

    def comp(group, name):
        x = trial[group][name][...].astype(np.float64)
        if x.ndim != 2 or x.shape != (3, n):
            raise ValueError(f"{base}/{group}/{name}: shape {x.shape}, expected (3, {n})")
        x[:, (x == 0).all(0)] = np.nan  # exact (0,0,0) triples are zero fill (UM21-C03)
        return x

    def marker(name):
        m = trial["markers"][name][...]
        if m.ndim != 2 or m.shape[0] < 4 or m.shape[1] != n:
            raise ValueError(f"{base}/markers/{name}: shape {m.shape}")
        xyz = m[:3].T.astype(np.float64).copy()
        xyz[m[3] != 1] = np.nan
        return xyz

    heels = np.vstack([marker("RHEE"), marker("LHEE")])
    toes = np.vstack([marker("RTOE"), marker("LTOE")])
    fwd = det.forward_axis(heels, toes, UP)
    asi = (marker("LASI") + marker("RASI")) / 2
    psi = (marker("LPSI") + marker("RPSI")) / 2
    pel = np.nanmean(asi - psi, 0)
    pel_h = pel - (pel @ UP) * UP
    axis_agreement_deg = float(np.degrees(np.arccos(np.clip(pel_h @ fwd / np.linalg.norm(pel_h), -1, 1))))

    def sag(p):
        return det.project_sagittal(p, fwd, UP)

    plates = {}
    for s in "RL":
        f = trial["forceplates"][s + "Force"][...]
        cop = trial["forceplates"][s + "CoP"][...]
        if f.shape != (3, PLATE_SAMPLES_PER_FRAME * n) or cop.shape != f.shape:
            raise ValueError(f"{base}: plate samples {f.shape} != (3, {PLATE_SAMPLES_PER_FRAME} x {n})")
        plates[s] = (np.nanmean(np.asarray(f, np.float64).reshape(3, n, PLATE_SAMPLES_PER_FRAME), 2),
                     np.nanmean(np.asarray(cop, np.float64).reshape(3, n, PLATE_SAMPLES_PER_FRAME), 2) / 1000.0)
    nominal = NOMINAL_SLOPE_DEG[condition]
    belt = None
    if nominal:
        # belt-rise sign from the right heel path in mid stance (marker frame), magnitude from the README
        fz_r = -plates["R"][0][2]
        thr = 0.2 * np.nanpercentile(fz_r, 99)
        on = np.flatnonzero(np.diff((fz_r > thr).astype(int)) == 1) + 1
        hee_r = marker("RHEE")
        slopes = []
        for a in on[:40]:
            b = a + 1
            while b < n and fz_r[b] > thr:
                b += 1
            s0, s1 = a + int(.3 * (b - a)), a + int(.6 * (b - a))
            ok = np.isfinite(hee_r[s0:s1, 1]) & np.isfinite(hee_r[s0:s1, 2])
            if ok.sum() > 5:
                slopes.append(np.degrees(np.arctan(np.polyfit(hee_r[s0:s1, 1][ok], hee_r[s0:s1, 2][ok], 1)[0])))
        if not slopes:
            raise ValueError(f"{base}: no mid-stance heel path to orient the {nominal} deg belt tilt")
        belt = float(np.median(slopes))
    alpha = float(np.sign(belt) * nominal) if nominal else 0.0
    rx = rot_x(alpha)
    mass = participant_mass(handle, subject)
    facts = {"recording": f"{subject}/{condition}", "frames": int(n), "task": TASK[condition],
             "body_mass_kg": mass, "body_mass_source": f"Streaming/{subject}/ParticipantDetails Bodymass (kg)",
             "forward_axis_lab": np.round(fwd, 4).tolist(),
             "forward_axis_vs_pelvis_axis_deg": round(axis_agreement_deg, 2),
             "belt_slope_from_heel_path_deg": None if belt is None else round(belt, 2),
             "plate_tilt_used_deg": alpha}

    legs = {}
    for side in "RL":
        pairs = strides(trial["events"][side + "HS"][...], n)
        if not pairs:
            raise ValueError(f"{base} {side}: no stride passes the stride rule")
        pts_lab = {"pelvis_rear": psi, "pelvis_front": asi, "hip": marker(side + "GT"),
                   "knee": (marker(side + "KNE") + marker(side + "KNEM")) / 2,
                   "ankle": (marker(side + "ANK") + marker(side + "ANKM")) / 2,
                   "heel": marker(side + "HEE"), "toe": marker(side + "TOE")}
        pts = {k: sag(v) for k, v in pts_lab.items()}
        leg_len = float(np.nanmedian(pts["hip"][:, 1] - pts["ankle"][:, 1]))
        if not 0.5 <= leg_len <= 1.2:
            raise ValueError(f"{base} {side}: hip-ankle height {leg_len:.3f} not in metres")
        f, cop = plates[side]
        grf = sag((-(rx @ f)).T)  # GRF on the foot = -(plate force)
        cop_s = sag((rx @ np.vstack([cop[0], cop[1], np.zeros(n)])).T)
        st = grf[:, 1] > 0.2 * np.nanpercentile(grf[:, 1], 99)
        mid = (pts["heel"] + pts["toe"]) / 2
        d_fwd = float(np.nanmean(mid[st, 0]) - np.nanmean(cop_s[st, 0]))
        d_up = float(np.nanmedian(np.fmin(pts["heel"][st, 1], pts["toe"][st, 1])) - np.nanmedian(cop_s[st, 1]))
        cop_s = cop_s + [d_fwd, d_up]

        channels, columns = {}, {}
        for k, name in ANGLES:
            channels[k] = np.radians(resample(comp("jointAngles", f"{side}{name}Angles")[0], pairs))
            columns[k] = f"{base}/jointAngles/{side}{name}Angles[component 1] (deg -> rad)"
        for j, name in JOINTS:
            channels[f"{j}_moment"] = resample(comp("jointMoments", f"{side}{name}Moment")[0], pairs)
            columns[f"{j}_moment"] = f"{base}/jointMoments/{side}{name}Moment[component 1] (N*m/kg as stored)"
        slots = {}
        for j, name in JOINTS:
            p = comp("jointPowers", f"{side}{name}Power")
            filled = [c + 1 for c in range(3) if np.nanmax(np.abs(np.nan_to_num(p[c]))) > 0]
            if expected_slot is not None and (not filled or filled[0] != expected_slot):
                raise PowerSlotError(f"{base} {side}{name}Power: first filled slot "
                                     f"{filled[0] if filled else None}, UM21-C03 layout record says {expected_slot}; "
                                     "recording failed")
            if filled:
                slots[j] = filled[0]
                channels[f"{j}_power"] = resample(p[filled[0] - 1], pairs)
                columns[f"{j}_power"] = (f"{base}/jointPowers/{side}{name}Power[component {filled[0]}] "
                                         "(W/kg as stored; first filled slot)")
        durations = np.array([(b - a) / RATE_HZ for a, b in pairs], dtype=np.float64)
        evidence = dict(marker_points={k: resample(v, pairs) for k, v in pts.items()},
                        cop=resample(cop_s, pairs), grf=resample(grf, pairs), task=TASK[condition],
                        grf_unit="N", body_mass_kg=mass, cop_registration=COP_REGISTRATION,
                        unit_durations_s=durations)
        legs[side] = LegInputs(
            side=side, leg=LEGS[side], pairs=pairs,
            unit_ids=[f"um21:Streaming/{subject}/Tread/{condition}:{LEGS[side]}:frames:{a}:{b}" for a, b in pairs],
            channels=channels, source_columns=columns, evidence=evidence, unit_durations_s=durations,
            power_slots=slots,
            facts={"cop_registration_m": {"forward": round(d_fwd, 4), "up": round(d_up, 4)},
                   "hip_ankle_height_m": round(leg_len, 4)})
    return facts, legs


# ---------------------------------------------------------------- hook, then derivations
def _forbidden_inputs(channels):
    return sorted(k for k in channels if k in sa.SEGMENT_CHANNELS or k.endswith(sa.VELOCITY_SUFFIX))


def apply_leg(inputs, recording, detector_sha256, *, backlog_path=sa.BACKLOG_PATH,
              audited_path=sa.AUDITED_PATH, mode="pilot", facts=None, decision=None, layout=None):
    """Hook, then segment angles and velocities from the published channels, for one leg."""
    bad = _forbidden_inputs(inputs.channels)
    if bad:
        raise ValueError(f"segment angles and velocities are derived after the hook, never passed in (F2): {bad}")
    in_hash = {k: sa.array_sha256(a) for k, a in inputs.channels.items()}
    group_id = f"{recording}:{inputs.leg}"
    app = sa.run_sign_application(dataset=DATASET, leg=inputs.leg, group_id=group_id, recording=recording,
                                  unit_ids=inputs.unit_ids, channels=inputs.channels,
                                  detector_sha256=detector_sha256, source_columns=inputs.source_columns,
                                  evidence=inputs.evidence, mode=mode, backlog_path=backlog_path,
                                  audited_path=audited_path)
    log_ch = app.log["channels"]
    published = {k: app.channels[k] for k, c in log_ch.items() if c["publication"] == "publish"}
    segments, segment_log = sa.derive_segment_angles(app)
    angles, not_derived = {}, dict(segment_log["not_derived"])
    if "pelvis_tilt" in published:
        angles["pelvis_tilt"] = published["pelvis_tilt"]
    else:
        not_derived["pelvis_tilt"] = f"pelvis_tilt ({log_ch.get('pelvis_tilt', {}).get('publication', 'not passed')})"
    angles.update(segments)
    spacing = inputs.unit_durations_s / (N_SAMPLES - 1)
    if angles:
        velocities, velocity_log = sa.derive_angular_velocities(angles, spacing)
    else:
        velocities, velocity_log = {}, {"method": sa.VELOCITY_METHOD, "spacing_s": spacing.tolist(), "derived": {}}
    velocity_log["not_derived"] = {k + sa.VELOCITY_SUFFIX: f"angle unavailable: {why}" for k, why in not_derived.items()}
    velocity_log["spacing_rule"] = "per unit: (b - a) / 100 Hz / 149, i.e. stride duration / (150 - 1)"
    if {k: sa.array_sha256(a) for k, a in inputs.channels.items()} != in_hash:
        raise RuntimeError("an adapter input channel changed during sign application")
    adapter_log = {
        "adapter": sa._rel(ADAPTER_PATH), "adapter_sha256": sa.file_sha256(ADAPTER_PATH),
        "dataset": DATASET, "recording": recording, "leg": inputs.leg, "group_id": group_id,
        "scientific_approval": False, "mode": mode, "order": list(ORDER),
        "stride_rule": STRIDE_RULE, "units": len(inputs.unit_ids), "frames_per_unit": [list(p) for p in inputs.pairs],
        "unit_conversion": "angles deg -> rad (x pi/180, numpy.radians); moments and powers as stored; float64",
        "source_columns": dict(inputs.source_columns), "power_slots": dict(inputs.power_slots),
        "hook_inputs": sorted(inputs.channels),
        "not_passed_to_hook": ("segment angles and every *_velocity channel: derived after the hook from published "
                               "channels (UM21-P02 verifier F2); never read from the source, the UM21 MATLAB "
                               "converters or reconvert_umich_streaming.py"),
        "inputs_sha256": in_hash, "recording_facts": facts, "leg_facts": inputs.facts,
        "exclusion_decision": decision, "power_layout": layout,
        "published": sorted(published), "held": sorted(k for k, c in log_ch.items() if c["publication"] == "hold"),
        "derived_segments": sorted(segments), "derived_velocities": sorted(velocities),
    }
    return LegResult(recording=recording, leg=inputs.leg, group_id=group_id, unit_ids=list(inputs.unit_ids),
                     application=app, published=published, segments=segments, segment_log=segment_log,
                     velocities=velocities, velocity_log=velocity_log, adapter_log=adapter_log)


def convert_recording(handle, recording, detector_sha256, *, backlog_path=sa.BACKLOG_PATH,
                      audited_path=sa.AUDITED_PATH, mode="pilot", c03_path=C03_PATH):
    """Both legs of one in-scope recording: (recording facts, [LegResult right, LegResult left]).
    Refuses an excluded recording before any data access; fails a recording whose power slots disagree
    with the UM21-C03 layout record."""
    subject, condition = check_recording(recording)
    decision = check_exclusion_decision(json.loads(Path(backlog_path).read_bytes()))
    layout = power_layout(c03_path)
    number, slot = expected_power_slot(recording, layout)
    layout_log = {"layout": number, "expected_slot": slot, "source": layout["source"], "sha256": layout["sha256"]}
    det = sa.load_bound_detector(detector_sha256)
    facts, legs = read_recording(handle, subject, condition, det, expected_slot=slot)
    results = []
    for side in "RL":
        results.append(apply_leg(legs.pop(side), recording, detector_sha256, backlog_path=backlog_path,
                                 audited_path=audited_path, mode=mode, facts=facts, decision=decision,
                                 layout=layout_log))
    return facts, results

