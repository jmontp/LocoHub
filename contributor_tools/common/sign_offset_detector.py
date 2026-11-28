"""Sagittal sign and offset detector (CORE-04).

Design and decision rules: docs/maintainers/sign-offset-detector-design.md.

Target convention is LocoHub rule B (decision D-UM21-C03-1 = B, task DOC-03):
the person faces right (+x walking direction, +y up, +z the person's right side,
out of the page). Segment angles (pelvis, thigh, shank, foot) are
counterclockwise positive, so pelvis anterior tilt is negative. Joint angles and
internal moments are positive in their named direction: hip flexion, knee
flexion and ankle dorsiflexion positive; hip flexor, knee flexor and ankle
dorsiflexor moments positive. Joint angle = JOINT_CCW[joint] x (distal -
proximal segment); internal moment = JOINT_CCW[joint] x the counterclockwise
moment on the distal segment (the knee is the only joint with factor -1).

Everything works on in-memory arrays shaped ``(units, samples)``. A unit is one
stride/cycle or one fixed block of a continuous recording; one leg per call.
Angles are radians, moments N*m/kg, power W/kg. Positions, centre of pressure
and ground reaction force are ``(units, samples, 2)`` arrays with components
``[forward, up]`` in the target frame (GRF acts on the body).

``sign`` always means ``target ~= sign * source``. Offsets are reported as
``sign * source - reference`` and are never applied. A sign is applied only
when independent evidence is unambiguous (verdict ``apply``); everything else
is flagged or abstains. No threshold here was tuned on research data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional
import warnings

import numpy as np

SCHEMA_VERSION = "sign-offset-detector/0.1"

TARGET_CONVENTION = {
    "rule": "D-UM21-C03-1 option B: person faces right (+x walking, +y up, "
            "+z the person's right side); segments counterclockwise positive; joint "
            "angles and internal moments positive in their named direction",
    "rule_id": "B",
    "pelvis_tilt": "anterior tilt negative (front down is clockwise)",
    "thigh_angle": "knee ahead of hip positive",
    "shank_angle": "ankle ahead of knee positive",
    "foot_angle": "toes up positive",
    "hip_angle": "flexion positive",
    "knee_angle": "flexion positive",
    "ankle_angle": "dorsiflexion positive",
    "hip_moment": "internal, flexor positive",
    "knee_moment": "internal, flexor positive (extensor negative)",
    "ankle_moment": "internal, dorsiflexor positive (plantarflexor negative)",
    "power": "moment x joint angular velocity; generation positive",
}

JOINTS = ("hip", "knee", "ankle")
# Rule B: named joint direction = JOINT_CCW x counterclockwise on the distal segment.
# Knee flexion swings the shank back (clockwise), so the knee factor is -1.
JOINT_CCW = {"hip": 1, "knee": -1, "ankle": 1}
# distal segment = proximal segment + JOINT_CCW x joint angle (rule B):
# thigh = pelvis + hip, shank = thigh - knee, foot = shank + ankle.
CHAIN = (
    ("thigh_angle", "pelvis_tilt", "hip_angle"),
    ("shank_angle", "thigh_angle", "knee_angle"),
    ("foot_angle", "shank_angle", "ankle_angle"),
)
LEVER_ARM_STRENGTH = {"ankle": "strong", "knee": "moderate", "hip": "weak"}
# Late-stance plantarflexor moment needs forward progression with heel-off.
LATE_STANCE_TASKS = {"level_walking", "incline_walking", "decline_walking",
                     "stair_ascent", "stair_descent", "run"}
# Knee asymmetry also relies on the walking duty factor (knee near straight in stance).
KNEE_HINGE_TASKS = {"level_walking", "incline_walking", "decline_walking"}
# Cross-family tests (CORE-04 phase 3). Each task set is the walking assumption of
# the test; outside it the test abstains.
LEG_GATE_TASKS = {"level_walking", "incline_walking", "decline_walking", "stair_ascent", "run"}
HIP_STANCE_TASKS = {"level_walking", "incline_walking", "decline_walking", "stair_ascent", "run"}
ANKLE_PUSHOFF_TASKS = {"level_walking", "incline_walking", "decline_walking", "stair_ascent", "run"}
HIP_MOMENT_TIMING_TASKS = {"level_walking", "incline_walking", "decline_walking"}
# Hip H3 limited to level walking on 2026-10-31, AFTER seeing UM21 data: on a 10-degree
# incline (AB03/i10 R, verifier run) hip power around toe-off was negative in 84 of 90
# strides and pulled the hip angle and moment into conflict. Logged scope change.
POWER_TIMING_TASKS = {"ankle": {"level_walking", "incline_walking", "stair_ascent", "run"},
                      "hip": {"level_walking"}}
# Winter (2009), Biomechanics and Motor Control of Human Movement, 4th ed., Table 4.1:
# segment mass / body mass, COM from the proximal end / length, radius of gyration
# about the COM / length. Used only to weigh inertial terms in a sign test.
WINTER_SEGMENTS = {"thigh": (0.100, 0.433, 0.323), "shank": (0.0465, 0.433, 0.302),
                   "foot": (0.0145, 0.50, 0.475)}
# Tests that read a channel's shape at fixed plate timing. A column taken from the other
# leg (half a cycle late) flips them exactly as it flips a reference-waveform test when the
# channel is nearly antisymmetric over half a cycle (e.g. a near-sinusoidal hip).
PLATE_TIMING_TESTS = {"late_stance_plantarflexor", "hip_stance_extension",
                      "ankle_pushoff_plantarflexion", "hip_moment_timing", "power_timing"}

STRENGTH_SCORE = {"strong": 2, "moderate": 1, "weak": 0, "documentation": 0}

# Evidence families. A sign is applied only when agreeing moderate/strong tests come
# from at least `min_families` different families; one test, or several tests of one
# family, give at most `suggest`. Default "fine" groups by failure mode (marker
# geometry, joint anatomy, plate geometry, plate timing, power identity). "coarse"
# (kinematic vs force plate vs power identity) is kept as an option only.
FAMILY_GROUPINGS = {
    "coarse": {"reference_angle": "kinematic", "knee_hinge_asymmetry": "kinematic",
               "derived:segment_chain": "kinematic", "lever_arm": "force_plate",
               "late_stance_plantarflexor": "force_plate",
               "hip_stance_extension": "force_plate", "ankle_pushoff_plantarflexion": "force_plate",
               "hip_moment_timing": "force_plate", "power_timing": "force_plate",
               "inverse_dynamics_light": "force_plate",
               "derived:power_identity": "power_identity"},
    "fine": {"reference_angle": "marker_geometry", "knee_hinge_asymmetry": "joint_anatomy",
             "derived:segment_chain": "marker_geometry", "lever_arm": "plate_geometry",
             "late_stance_plantarflexor": "plate_timing",
             "hip_stance_extension": "plate_timing", "ankle_pushoff_plantarflexion": "plate_timing",
             "hip_moment_timing": "plate_timing", "power_timing": "plate_timing",
             "inverse_dynamics_light": "plate_geometry",
             "derived:power_identity": "power_identity"},
}
# CoP heel-to-toe progression is only expected in forward heel-strike walking.
COP_PROGRESSION_TASKS = {"level_walking", "incline_walking", "decline_walking"}
# Contact floor for the stance mask, by declared vertical GRF unit (no mass needed).
STANCE_FLOOR = {"N_per_kg": 0.5, "BW": 0.05, "N": 20.0}
# Plausibility of the declared GRF unit: the median per-unit peak vertical GRF must lie
# in [0.4, 4] body weights (quiet standing on one plate to running). For N the body
# mass is the declared one, or a broad adult band (30-200 kg) when none is declared;
# no subject mass is invented. The units differ by about 10x or more, so a wrong
# declaration falls outside the band.
GRF_PEAK_BW_BAND = (0.4, 4.0)
GRF_MASS_BAND_KG = (30.0, 200.0)
G = 9.81

DEFAULTS = {
    "min_units": 5,               # units that must cast a vote before a test decides
    "unit_agreement": 0.9,        # fraction of voting units that must agree
    "min_samples_per_unit": 10,
    "r_reference": 0.8,           # |r| of channel vs marker/segment reference
    "r_lever_arm": 0.6,           # |r| of moment vs quasi-static GRF moment (stance)
    "r_power": 0.8,               # |r| of power vs moment x joint speed
    "r_template": 0.5,            # weak template evidence only
    "chain_margin": 0.5,          # best sign pattern RMS <= margin x second best
    "knee_min_range_rad": 0.5,    # about 29 deg excursion needed
    "knee_excursion_ratio": 2.0,  # larger excursion side / smaller side
    "late_stance_fraction": 0.25,  # |late-stance mean| >= fraction x unit peak |moment|
    "stance_grf_fraction": 0.05,  # stance = vertical GRF above 5% of unit peak ...
                                  # ... and above STANCE_FLOOR[grf_unit] (declared)
    "branch_deg": 100.0,          # |wrapped distance from channel median|
    "branch_jump_deg": 90.0,      # one-sample jump that marks a branch-run boundary
    "vertical_order_min": 0.9,    # fraction of frames with hip above knee above ankle
    "frame_check_min": 0.9,       # fraction of units with heel-to-toe CoP progression
    "cop_foot_margin_m": 0.03,    # CoP may sit this far outside the heel-toe marker span
    "cop_foot_min": 0.8,          # fraction of a unit's stance samples with CoP in that span
    "vertical_order_min_frames": 50,  # visible frames needed to confirm (= 5 units x 10 samples)
    "offset_tolerance_rad": 0.035,  # about 2 deg; smaller offsets are not flagged
    "scale_band": (0.8, 1.25),    # reference slope magnitude outside -> scale review
    "units_slope_band": (0.1, 10.0),  # outside -> units mismatch: the test abstains
    "half_turn_rad": np.pi / 2,   # |offset| above this -> conflict (branch or zero mismatch)
    "min_families": 2,            # independent evidence families needed to apply
    "family_grouping": "fine",
    "leg_gate_min": 0.9,          # units whose knee peak lies in swing, for the plate-leg gate
    "hip_stance_edge": 0.05,      # fraction of stance averaged at each end
    "hip_stance_min_rad": 0.20,   # |hip change over stance| needed to vote (about 11 deg)
    "ankle_pushoff_window": 0.25,  # last fraction of stance
    "ankle_pushoff_min_rad": 0.10,  # |ankle change over that window| needed (about 6 deg)
    "hip_moment_early": 0.20,     # first fraction of stance
    "hip_moment_late": 0.30,      # last fraction of stance
    "hip_moment_contrast": 0.25,  # |late - early| >= fraction x unit peak |moment|
    "power_window_ankle": 0.25,   # last fraction of stance (ankle push-off, A2)
    "power_window_hip": 0.10,     # +- fraction of stance length around toe-off (hip H3)
    "power_timing_fraction": 0.15,  # |window mean| >= fraction x unit peak |power|
    "id_lowpass_hz": 6.0,         # marker low-pass before differentiation (ID-light)
    "r_id_light": 0.6,            # |r| of hip moment vs ID-light estimate
    "half_cycle_margin": 0.05,    # median |r| gap between lag 0 and a half-unit lag
    "bootstrap_resamples": 2000,
    "bootstrap_seed": 20261030,
}


@dataclass
class Evidence:
    """One test on one channel."""
    test: str
    channel: str
    strength: str
    sign: Optional[int] = None
    reason: str = ""
    units: int = 0
    units_voting: int = 0
    units_agreeing: int = 0
    stats: dict = field(default_factory=dict)
    offset: Optional[dict] = None

    @property
    def abstained(self):
        return self.sign is None


@dataclass
class Relation:
    """Product of channel signs implied by a physical identity."""
    test: str
    channels: tuple
    strength: str
    product: Optional[int] = None
    reason: str = ""
    units: int = 0
    units_voting: int = 0
    units_agreeing: int = 0
    stats: dict = field(default_factory=dict)


# ---------------------------------------------------------------- helpers
def _wrap(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


def _circular_centre(x):
    """Robust centre that ignores 360-degree wraps: the median of the angles after
    re-expressing them within +-pi of their circular mean."""
    x = np.asarray(x, float)
    z = np.exp(1j * x[np.isfinite(x)])
    if not z.size:
        return 0.0
    c0 = float(np.angle(z.mean()))
    return float(np.median(c0 + _wrap(x[np.isfinite(x)] - c0)))


def reexpress_near_centre(x):
    """Same angles, re-expressed within +-pi of the channel's robust circular centre.

    Removes 360-degree wraps (and a reference that straddles +-pi) before fitting.
    """
    c = _circular_centre(x)
    return c + _wrap(np.asarray(x, float) - c)


def _fit(y, x, min_n):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < min_n:
        return None
    xc, yc = x[ok] - x[ok].mean(), y[ok] - y[ok].mean()
    sxx, syy = float((xc * xc).sum()), float((yc * yc).sum())
    if sxx <= 0 or syy <= 0:
        return None
    sxy = float((xc * yc).sum())
    return sxy / sxx, sxy / np.sqrt(sxx * syy)


def _vote(unit_signs, p):
    """unit_signs: list of +1/-1/None. Returns (sign or None, voting, agreeing, reason)."""
    votes = [s for s in unit_signs if s is not None]
    if len(votes) < p["min_units"]:
        return None, len(votes), 0, f"only {len(votes)} units cast a vote (< {p['min_units']})"
    pos = sum(1 for s in votes if s > 0)
    lead = 1 if pos * 2 >= len(votes) else -1
    agree = pos if lead > 0 else len(votes) - pos
    if agree / len(votes) < p["unit_agreement"]:
        return None, len(votes), agree, f"units split {agree}/{len(votes)}"
    return lead, len(votes), agree, ""


def _bootstrap_offset(values, p):
    # Differences are wrapped to (-pi, pi]: a 360-degree storage wrap is not an offset.
    v = _wrap(np.asarray([x for x in values if np.isfinite(x)], float))
    if len(v) < p["min_units"]:
        return None
    rng = np.random.default_rng(p["bootstrap_seed"])
    idx = rng.integers(0, len(v), size=(p["bootstrap_resamples"], len(v)))
    meds = np.median(v[idx], axis=1)
    est = float(np.median(v))
    lo, hi = (float(q) for q in np.percentile(meds, [2.5, 97.5]))
    flag = (lo > 0 or hi < 0) and abs(est) > p["offset_tolerance_rad"]
    return {"estimate": est, "ci95": [lo, hi], "units": len(v),
            "flag_for_review": bool(flag), "applied": False}


def stance_from_grf(grf_vertical, unit, fraction=DEFAULTS["stance_grf_fraction"]):
    """Stance mask: vertical GRF above `fraction` of each unit's peak and above the
    contact floor for its declared unit (N_per_kg, BW or N), so a unit without
    contact is not called stance. An undeclared unit is refused."""
    if unit not in STANCE_FLOOR:
        raise ValueError(f"GRF unit {unit!r} not declared; use one of {sorted(STANCE_FLOOR)}")
    floor = STANCE_FLOOR[unit]
    g = np.asarray(grf_vertical, float)
    peak = np.nanmax(np.where(np.isfinite(g), g, -np.inf), axis=1, keepdims=True)
    return np.nan_to_num(g, nan=-np.inf) > np.maximum(fraction * peak, floor)


def grf_unit_check(grf_vertical, unit, body_mass_kg=None):
    """Is the declared vertical-GRF unit plausible for these data?

    Median of the per-unit peak vertical GRF, compared with [0.4, 4] body weights
    expressed in the declared unit. Returns a dict with result pass/fail/unknown.
    """
    g = np.asarray(grf_vertical, float)
    if unit not in STANCE_FLOOR:
        return {"result": "unknown", "reason": f"GRF unit {unit!r} not declared"}
    if not np.isfinite(g).any():
        return {"result": "unknown", "reason": "no finite vertical GRF"}
    rows = g[np.isfinite(g).any(axis=1)]  # units without any finite GRF (withheld) do not vote
    peak = float(np.median(np.nanmax(rows, axis=1)))
    lo, hi = GRF_PEAK_BW_BAND
    if unit == "N_per_kg":
        band = (lo * G, hi * G)
    elif unit == "BW":
        band = (lo, hi)
    else:
        m_lo, m_hi = ((body_mass_kg, body_mass_kg) if body_mass_kg
                      else GRF_MASS_BAND_KG)
        band = (lo * G * m_lo, hi * G * m_hi)
    ok = band[0] <= peak <= band[1]
    return {"result": "pass" if ok else "fail", "unit": unit,
            "median_unit_peak": peak, "plausible_band": [float(band[0]), float(band[1])],
            "units_with_grf": int(len(rows)),
            "mass_basis": ("declared" if body_mass_kg else "30-200 kg band")
            if unit == "N" else None}


def _longest_run(mask_row):
    """(start, stop) indices of the longest True run, wrapping around the end."""
    n = len(mask_row)
    if not mask_row.any():
        return None
    shift = 0
    if mask_row[0] and mask_row[-1] and not mask_row.all():
        shift = int(np.argmin(mask_row))  # first False
    m = np.roll(mask_row, -shift)
    best, start = (0, 0, 0), None
    for i, v in enumerate(np.append(m, False)):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start > best[0]:
                best = (i - start, start, i)
            start = None
    return [(k + shift) % n for k in range(best[1], best[2])]


# ---------------------------------------------------------- marker geometry
def forward_axis(rear, front, up):
    """Unit forward vector from rear->front points (e.g. heel->toe), (..., 3) arrays."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    d = (np.asarray(front) - np.asarray(rear)).reshape(-1, 3)
    d = d[np.isfinite(d).all(axis=1)]
    h = d - np.outer(d @ up, up)
    f = np.median(h, axis=0)
    return f / np.linalg.norm(f)


def project_sagittal(points, forward, up):
    """Lab (..., 3) points -> (..., 2) [forward, up]. Lab handedness does not matter."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    fwd = np.asarray(forward, float)
    fwd = fwd - (fwd @ up) * up
    fwd /= np.linalg.norm(fwd)
    p = np.asarray(points, float)
    return np.stack([p @ fwd, p @ up], axis=-1)


def long_axis_angle(proximal, distal):
    """Segment angle from straight down, distal end forward positive (counterclockwise)."""
    d = np.asarray(distal) - np.asarray(proximal)
    return np.arctan2(d[..., 0], -d[..., 1])


def horizontal_axis_angle(rear, front):
    """Angle of rear->front from forward horizontal, front up positive (counterclockwise)."""
    d = np.asarray(front) - np.asarray(rear)
    return np.arctan2(d[..., 1], d[..., 0])


def vertical_order_fraction(pts):
    """Fraction of visible frames where every upper point (pelvis markers, hip, knee) is above
    the foot point (ankle, else heel, else toe), sagittal [forward, up].

    Holds in walking, stairs, squats and sit-to-stand (unlike hip above knee). An
    inverted up vector mirrors every marker angle; this check exposes it. Returns
    None when no foot point or no upper point is present.
    """
    foot = next((pts[k] for k in ("ankle", "heel", "toe") if k in pts), None)
    uppers = [pts[k] for k in ("pelvis_rear", "pelvis_front", "hip", "knee") if k in pts]
    if foot is None or not uppers:
        return None
    return vertical_order_check(pts)["fraction"]


def vertical_order_check(pts, min_frames=DEFAULTS["vertical_order_min_frames"],
                         min_fraction=DEFAULTS["vertical_order_min"]):
    """Vertical-order check with the number of visible frames it rests on.

    Frames with a missing marker are not evidence either way, so only visible frames
    are judged. 'fail' needs any visible frames with too few in order (an inversion
    shows in every frame); 'pass' needs at least `min_frames` visible frames;
    otherwise 'unknown'.
    """
    foot = next((pts[k] for k in ("ankle", "heel", "toe") if k in pts), None)
    uppers = [pts[k] for k in ("pelvis_rear", "pelvis_front", "hip", "knee") if k in pts]
    if foot is None or not uppers:
        return {"fraction": None, "visible_frames": 0, "required_frames": min_frames,
                "result": "unknown", "reason": "no foot point or no upper point"}
    foot_y = np.asarray(foot, float)[..., 1]
    ok = np.ones(np.shape(foot_y), bool)
    seen = np.isfinite(foot_y)
    for up in uppers:
        up_y = np.asarray(up, float)[..., 1]
        ok &= up_y > foot_y
        seen &= np.isfinite(up_y)
    n = int(np.sum(seen))
    frac = float(np.mean(ok[seen])) if n else None
    if frac is None:
        result = "unknown"
    elif frac < min_fraction:
        result = "fail"
    else:
        result = "pass" if n >= min_frames else "unknown"
    return {"fraction": frac, "visible_frames": n, "required_frames": min_frames, "result": result}


class MarkerAngle(np.ndarray):
    """A marker-derived angle array that carries its vertical-order check.

    The guard travels with the array, so a dict copy or a key selection of the
    marker references keeps it; detect_leg checks it on input. An explicit
    np.asarray() conversion is a deliberate act and is the caller's responsibility.
    """
    def __new__(cls, values, vertical_order):
        obj = np.asarray(values, float).view(cls)
        obj.vertical_order = dict(vertical_order)
        return obj

    def __array_finalize__(self, obj):
        self.vertical_order = getattr(obj, "vertical_order", None)


class MarkerAngles(dict):
    """Marker reference angles plus the vertical-order check that guards them."""
    vertical_order = None


def marker_reference_angles(pts, min_vertical_order=DEFAULTS["vertical_order_min"]):
    """Rule-B segment and joint angles from sagittal points ([forward, up]).

    Keys used when present: pelvis_rear, pelvis_front, hip, knee, ankle, heel, toe.
    The zeros are the marker definitions' zeros (e.g. pelvis PSIS->ASIS line), so
    offsets against them are differences in zero definition, not errors.
    """
    chk = vertical_order_check(pts, min_fraction=min_vertical_order)
    if chk["result"] == "fail":
        raise ValueError(f"pelvis/hip/knee above the foot in only {chk['fraction']:.0%} of "
                         f"{chk['visible_frames']} visible frames; the up vector is probably inverted")
    out = MarkerAngles()
    out.vertical_order = {**chk, "required": min_vertical_order}
    if {"pelvis_rear", "pelvis_front"} <= pts.keys():
        out["pelvis_tilt"] = horizontal_axis_angle(pts["pelvis_rear"], pts["pelvis_front"])
    if {"hip", "knee"} <= pts.keys():
        out["thigh_angle"] = long_axis_angle(pts["hip"], pts["knee"])
    if {"knee", "ankle"} <= pts.keys():
        out["shank_angle"] = long_axis_angle(pts["knee"], pts["ankle"])
    if {"heel", "toe"} <= pts.keys():
        out["foot_angle"] = horizontal_axis_angle(pts["heel"], pts["toe"])
    for distal, proximal, joint in CHAIN:
        if distal in out and proximal in out:
            c = JOINT_CCW[joint.split("_")[0]]
            out[joint] = _wrap(c * (np.asarray(out[distal]) - np.asarray(out[proximal])))
    for k in list(out):
        out[k] = MarkerAngle(out[k], out.vertical_order)
    return out


# ------------------------------------------------------------ branch screens
def alternate_branch_frames(c1, c2, c3, degrees=True):
    """Frames whose Cardan middle angle is outside [-90, 90]: the second solution."""
    lim = 90.0 if degrees else np.pi / 2
    return np.abs(np.asarray(c2)) > lim


def reexpress_alternate(c1, c2, c3, degrees=True):
    """Proposed (not applied) re-expression to the principal Cardan solution."""
    half = 180.0 if degrees else np.pi

    def w(x):
        return (x + half) % (2 * half) - half
    return w(np.asarray(c1) + half), w(half - np.asarray(c2)), w(np.asarray(c3) + half)


def screen_branch(x, p=DEFAULTS):
    """Single sagittal channel screen. Returns (fit_values, mask, summary).

    - 360-degree wraps are the same angle: the fitting copy is re-expressed within
      +-180 deg of the channel's robust circular centre (source not changed).
    - A branch run is a run of frames more than `branch_deg` from the median that
      starts or ends with a one-sample jump above `branch_jump_deg`, or fills a whole
      unit. Branch frames are masked from fits.
    - Continuous excursions far from the median (e.g. deep knee flexion in a squat)
      are reported as `far_from_median_frames` and are not masked.
    """
    x = np.asarray(x, float)
    med = _circular_centre(x)
    d = x - med
    w = _wrap(d)
    wrap360 = (np.abs(d) > np.pi) & (np.abs(w) <= np.pi / 2) & np.isfinite(x)
    fit = med + w
    far = (np.abs(w) > np.deg2rad(p["branch_deg"])) & np.isfinite(x)
    jump = np.deg2rad(p["branch_jump_deg"])
    mask = np.zeros_like(far)
    runs = []
    for u in range(far.shape[0]):
        idx = np.flatnonzero(far[u])
        if not idx.size:
            continue
        cuts = np.flatnonzero(np.diff(idx) > 1)
        for a, b in zip(np.r_[0, cuts + 1], np.r_[cuts, idx.size - 1]):
            i0, i1 = int(idx[a]), int(idx[b]) + 1
            n = far.shape[1]
            edge_jumps = []
            if i0 > 0:
                edge_jumps.append(abs(_wrap(fit[u, i0] - fit[u, i0 - 1])) > jump)
            if i1 < n:
                edge_jumps.append(abs(_wrap(fit[u, i1] - fit[u, i1 - 1])) > jump)
            if any(edge_jumps) or (i0 == 0 and i1 == n):
                mask[u, i0:i1] = True
                runs.append([int(u), i0, i1])
    return fit, mask, {"branch_180_frames": int(mask.sum()),
                       "far_from_median_frames": int((far & ~mask).sum()),
                       "wrap_360_frames": int(wrap360.sum()),
                       "units_touched": int(mask.any(axis=1).sum()),
                       "runs_unit_start_stop": runs[:20], "runs_total": len(runs),
                       "action": "branch frames masked from fits; 360-degree wraps "
                                 "re-expressed in the fitting copy; source not changed"}


def _half_cycle(r0, rh, p):
    """Compare a reference-waveform fit at lag 0 with the same fit after shifting the
    channel by half a unit (units are gait cycles). 'half': the channel fits better half a
    cycle late (a column from the other leg?); 'ambiguous': lag 0 and the half-cycle lag
    cannot be told apart, so a column mislabel would look like a sign flip; 'lag0'."""
    if not r0 or not rh:
        return {"result": "unknown"}
    m0, mh = float(np.median(np.abs(r0))), float(np.median(np.abs(rh)))
    res = ("half" if mh >= m0 + p["half_cycle_margin"] else
           "ambiguous" if m0 - mh < p["half_cycle_margin"] else "lag0")
    return {"result": res, "median_abs_r_lag0": round(m0, 3), "median_abs_r_half": round(mh, 3)}


def _apply_half_cycle(ev, hc):
    ev.stats["half_cycle"] = hc
    if hc["result"] == "half":
        ev.sign = None
        ev.offset = None
        ev.reason = ("channel fits the reference better half a cycle late "
                     "(column from the other leg?)")
    elif hc["result"] == "ambiguous":
        ev.stats["half_cycle_ambiguous"] = True
    return ev


# ------------------------------------------------------------------- tests
def reference_angle_test(channel, values, reference, p=DEFAULTS, source="marker"):
    """Strong: channel vs an independent rule-B angle (markers or independent segments).

    Channel and reference are each re-expressed near their robust circular centre,
    so values straddling +-pi (or 360-degree wraps) cannot flip the slope.
    """
    for name, arr in (("channel", values), ("reference", reference)):
        if np.isfinite(arr).any() and np.nanmax(np.abs(arr)) > 2 * np.pi:
            return Evidence(f"reference_angle:{source}", channel, "strong", None,
                            f"{name} |value| > 2*pi: units mismatch (degrees?)",
                            values.shape[0], stats={"scale_review": True})
    reference = reexpress_near_centre(reference)
    values = reexpress_near_centre(values)
    signs, slopes, rs, r_half = [], [], [], []
    half = values.shape[1] // 2
    for u in range(values.shape[0]):
        f = _fit(values[u], reference[u], p["min_samples_per_unit"])
        if f is None:
            signs.append(None)
            continue
        slope, r = f
        slopes.append(slope)
        rs.append(r)
        fh = _fit(np.roll(values[u], half), reference[u], p["min_samples_per_unit"])
        if fh is not None:
            r_half.append(fh[1])
        signs.append(int(np.sign(slope)) if abs(r) >= p["r_reference"] else None)
    sign, nv, na, why = _vote(signs, p)
    ev = Evidence(f"reference_angle:{source}", channel, "strong", sign, why,
                  values.shape[0], nv, na)
    if slopes:
        mag = float(np.median(np.abs(slopes)))
        lo, hi = p["scale_band"]
        ev.stats = {"median_abs_slope": mag, "median_abs_r": float(np.median(np.abs(rs))),
                    "scale_review": not (lo <= mag <= hi)}
        ulo, uhi = p["units_slope_band"]
        if sign is not None and not (ulo <= mag <= uhi):
            ev.sign, sign = None, None
            ev.reason = f"slope magnitude {mag:.3g} outside [{ulo}, {uhi}]: units mismatch"
    if sign is not None:
        unit_off = [float(np.nanmedian(_wrap(sign * values[u] - reference[u])))
                    for u in range(values.shape[0]) if signs[u] == sign]
        ev.offset = _bootstrap_offset(unit_off, p)
        if ev.offset:
            ev.offset["reference"] = f"{source} rule-B angle (its own zero definition)"
            if abs(ev.offset["estimate"]) > p["half_turn_rad"]:
                ev.stats["half_turn_offset"] = True
    return _apply_half_cycle(ev, _half_cycle(rs, r_half, p))


def plate_frame_check(cop, ankle_pos, grf, stance, p=DEFAULTS, task=None, heel=None, toe=None):
    """Check that force-plate data share the target forward axis.

    - CoP progression: during each unit's main stance, (CoP - ankle) forward moves
      from heel toward toe (last-quarter mean > first-quarter mean). Needs ankle
      positions. Run only for forward heel-strike walking (COP_PROGRESSION_TASKS);
      otherwise 'unknown', because backward or toe walking moves the CoP toe-to-heel
      and would pass a mirrored frame.
    - Braking then propulsion: anterior GRF mean < 0 in the first third of stance
      and > 0 in the last third (steady forward walking). Checked only if supplied.
    - CoP within the foot: in each unit's stance, the CoP forward position lies
      within the heel-toe marker span (+- `cop_foot_margin_m`) in at least
      `cop_foot_min` of the samples. This tests the adapter's CoP registration
      (plate origin vs marker origin), which progression cannot see: a constant
      CoP shift leaves progression intact but moves every lever arm. Needs heel
      and toe positions; runs for any task.
    Each check is 'pass', 'fail' or 'unknown'.
    """
    def vote(fn):
        signs = []
        for u in range(stance.shape[0]):
            run = _longest_run(stance[u])
            signs.append(fn(u, run) if run and len(run) >= 2 * p["min_samples_per_unit"]
                         else None)
        votes = [s for s in signs if s is not None]
        if len(votes) < p["min_units"]:
            return "unknown", len(votes), 0
        pos = sum(1 for s in votes if s > 0)
        if pos / len(votes) >= p["frame_check_min"]:
            return "pass", len(votes), pos
        if (len(votes) - pos) / len(votes) >= p["frame_check_min"]:
            return "fail", len(votes), pos
        return "unknown", len(votes), pos

    out = {}
    if task not in COP_PROGRESSION_TASKS:
        out["cop_progression"] = {"result": "unknown",
                                  "reason": f"task {task!r} not forward heel-strike walking"}
    elif ankle_pos is None:
        out["cop_progression"] = {"result": "unknown", "reason": "no ankle positions"}
    else:
        rel = cop[..., 0] - ankle_pos[..., 0]

        def prog(u, run):
            q = max(len(run) // 4, 1)
            d = np.nanmean(rel[u, run[-q:]]) - np.nanmean(rel[u, run[:q]])
            return None if not np.isfinite(d) or d == 0 else int(np.sign(d))
        r, nv, na = vote(prog)
        out["cop_progression"] = {"result": r, "units_voting": nv, "units_forward": na}
    if heel is None or toe is None:
        out["cop_within_foot"] = {"result": "unknown", "reason": "no heel and toe positions"}
    else:
        lo = np.fmin(heel[..., 0], toe[..., 0]) - p["cop_foot_margin_m"]
        hi = np.fmax(heel[..., 0], toe[..., 0]) + p["cop_foot_margin_m"]
        inside = (cop[..., 0] >= lo) & (cop[..., 0] <= hi)
        ok_samples = np.isfinite(cop[..., 0]) & np.isfinite(lo) & np.isfinite(hi)

        def within(u, run):
            m = np.zeros(stance.shape[1], bool)
            m[run] = True
            m &= ok_samples[u]
            if m.sum() < p["min_samples_per_unit"]:
                return None
            return 1 if inside[u, m].mean() >= p["cop_foot_min"] else -1
        r, nv, na = vote(within)
        fracs = [float(inside[u][stance[u] & ok_samples[u]].mean()) for u in range(stance.shape[0])
                 if (stance[u] & ok_samples[u]).sum() >= p["min_samples_per_unit"]]
        out["cop_within_foot"] = {"result": r, "units_voting": nv, "units_inside": na,
                                  "median_inside_fraction": float(np.median(fracs)) if fracs else None}
    fx = grf[..., 0]
    if task not in COP_PROGRESSION_TASKS:
        out["braking_propulsion"] = {"result": "unknown",
                                     "reason": f"task {task!r} not forward walking"}
    elif not np.isfinite(fx).any():
        out["braking_propulsion"] = {"result": "unknown", "reason": "no anterior GRF"}
    else:
        def brake(u, run):
            t = max(len(run) // 3, 1)
            early, late = np.nanmean(fx[u, run[:t]]), np.nanmean(fx[u, run[-t:]])
            if early < 0 < late:
                return 1
            if early > 0 > late:
                return -1
            return None
        r, nv, na = vote(brake)
        out["braking_propulsion"] = {"result": r, "units_voting": nv, "units_pass": na}
    return out


def lever_arm_test(joint, moment, joint_pos, cop, grf, stance, p=DEFAULTS, frame=None):
    """Quasi-static internal moment -(r x F)_z on the distal segment during stance,
    times JOINT_CCW (rule B: knee flexor positive).

    Ignores segment weight and inertia, so strength depends on the joint:
    ankle strong, knee moderate, hip weak.
    """
    ch = f"{joint}_moment"
    strength = LEVER_ARM_STRENGTH[joint]
    frame = frame or {}
    cop_check = frame.get("cop_progression", {}).get("result", "unknown")
    foot_check = frame.get("cop_within_foot", {}).get("result", "unknown")
    if cop_check == "fail":
        return Evidence("lever_arm", ch, strength, None,
                        "plate frame check failed: CoP moves toe-to-heel relative to the "
                        "ankle (forward axis reversed?)", moment.shape[0], stats={"frame": frame})
    if foot_check == "fail":
        return Evidence("lever_arm", ch, strength, None,
                        "plate frame check failed: stance CoP outside the heel-toe marker span "
                        "(CoP registration?)", moment.shape[0], stats={"frame": frame})
    if (cop_check != "pass" or foot_check != "pass") and strength == "strong":
        strength = "moderate"  # unchecked frame or registration: cannot be strong
    fx = grf[..., 0]
    if frame.get("braking_propulsion", {}).get("result") == "fail":
        fx = np.full_like(fx, np.nan)  # anterior GRF sign unverified: drop it
    vertical_only = not np.isfinite(fx).any()
    fx = np.zeros_like(grf[..., 1]) if vertical_only else fx
    fy = grf[..., 1]
    st = stance & np.isfinite(fy)
    if st.sum() == 0 or np.nanmedian(fy[st]) <= 0:
        return Evidence("lever_arm", ch, strength, None,
                        "no stance with upward vertical GRF on the body", moment.shape[0])
    r = cop - joint_pos
    lever = -JOINT_CCW[joint] * (r[..., 0] * fy - r[..., 1] * fx)
    signs, slopes, rs, r_half = [], [], [], []
    half = moment.shape[1] // 2
    for u in range(moment.shape[0]):
        m = st[u]
        f = _fit(np.where(m, moment[u], np.nan), np.where(m, lever[u], np.nan),
                 p["min_samples_per_unit"])
        if f is None:
            signs.append(None)
            continue
        slopes.append(f[0])
        rs.append(f[1])
        signs.append(int(np.sign(f[0])) if abs(f[1]) >= p["r_lever_arm"] else None)
        fh = _fit(np.where(m, np.roll(moment[u], half), np.nan), np.where(m, lever[u], np.nan),
                  p["min_samples_per_unit"])
        if fh is not None:
            r_half.append(fh[1])
    sign, nv, na, why = _vote(signs, p)
    ev = Evidence("lever_arm", ch, strength, sign, why, moment.shape[0], nv, na,
                  {"median_slope": float(np.median(slopes)) if slopes else None,
                   "vertical_only": vertical_only, "frame": frame,
                   "note": "slope below 1 is expected: inertia and weight ignored"})
    return _apply_half_cycle(ev, _half_cycle(rs, r_half, p))


def late_stance_ankle_test(moment, stance, task, p=DEFAULTS, gate=None):
    """Moderate: after heel-off the CoP is under the forefoot, ahead of the ankle,
    so the internal ankle moment is plantarflexor (negative under rule B)."""
    ch = "ankle_moment"
    if task not in LATE_STANCE_TASKS:
        return Evidence("late_stance_plantarflexor", ch, "moderate", None,
                        f"task {task!r} not a forward-progression task", moment.shape[0])
    if gate and gate.get("result") == "fail":
        return Evidence("late_stance_plantarflexor", ch, "moderate", None, GATE_FAIL,
                        moment.shape[0], stats={"leg_assignment": gate})
    signs, means = [], []
    for u in range(moment.shape[0]):
        run = _longest_run(stance[u])
        if not run or len(run) < 2 * p["min_samples_per_unit"]:
            signs.append(None)
            continue
        late = moment[u, run[len(run) // 2:]]
        mean = float(np.nanmean(late))
        peak = float(np.nanmax(np.abs(moment[u])))
        means.append(mean)
        signs.append((1 if mean < 0 else -1)
                     if peak > 0 and abs(mean) >= p["late_stance_fraction"] * peak else None)
    sign, nv, na, why = _vote(signs, p)
    return Evidence("late_stance_plantarflexor", ch, "moderate", sign, why,
                    moment.shape[0], nv, na,
                    {"median_late_stance_mean": float(np.median(means)) if means else None})


GATE_FAIL = ("plate-to-leg check failed: the knee's largest excursion falls inside this "
             "plate's stance (plate belongs to the other leg, or the knee pattern is outside "
             "the gate's assumption, e.g. a steep incline with a flexed stance knee)")


def leg_assignment_check(knee, stance, task, p=DEFAULTS):
    """Plate-to-leg gate for plate-timed tests (sign-independent).

    In walking, running and stair ascent the knee's largest excursion from its median
    (the swing flexion peak) happens in swing. If it falls inside this plate's stance in
    most units, the plate (or the units) belong to the other leg. Uses |knee - median|,
    so the knee channel's own sign does not matter.
    """
    if knee is None:
        return {"result": "unknown", "reason": "no knee angle channel"}
    if stance is None:
        return {"result": "unknown", "reason": "no stance mask"}
    if task not in LEG_GATE_TASKS:
        return {"result": "unknown", "reason": f"task {task!r} outside the gate's assumptions"}
    votes, no_stance = [], 0
    for u in range(knee.shape[0]):
        x = knee[u]
        if np.isfinite(x).sum() < p["min_samples_per_unit"]:
            continue
        if not np.any(stance[u]):  # no stance information (e.g. GRF withheld): no vote, not "swing"
            no_stance += 1
            continue
        k = int(np.nanargmax(np.abs(x - np.nanmedian(x))))
        votes.append(1 if not stance[u, k] else -1)
    if len(votes) < p["min_units"]:
        return {"result": "unknown", "reason": f"only {len(votes)} units", "units": len(votes),
                "units_without_stance": no_stance}
    swing = sum(v > 0 for v in votes) / len(votes)
    result = ("pass" if swing >= p["leg_gate_min"] else
              "fail" if 1 - swing >= p["leg_gate_min"] else "unknown")
    return {"result": result, "units": len(votes), "knee_peak_in_swing_fraction": round(swing, 3),
            "units_without_stance": no_stance}


def _timing_test(name, channel, values, stance, task, tasks, gate, unit_vote, p):
    """Shared shell of the plate-timed tests (family plate_timing, strength moderate)."""
    n = values.shape[0]
    if task not in tasks:
        return Evidence(name, channel, "moderate", None,
                        f"task {task!r} outside this test's walking assumptions", n)
    if stance is None:
        return Evidence(name, channel, "moderate", None, "no stance mask (no force plate)", n)
    if gate and gate.get("result") == "fail":
        return Evidence(name, channel, "moderate", None, GATE_FAIL, n,
                        stats={"leg_assignment": gate})
    signs, stat = [], []
    for u in range(n):
        run = _longest_run(stance[u])
        if not run or len(run) < 2 * p["min_samples_per_unit"]:
            signs.append(None)
            continue
        with warnings.catch_warnings():  # all-NaN windows (masked frames) give no vote
            warnings.simplefilter("ignore", RuntimeWarning)
            vote, value = unit_vote(values[u], run)
        signs.append(vote)
        if value is not None and np.isfinite(value):
            stat.append(value)
    sign, nv, na, why = _vote(signs, p)
    return Evidence(name, channel, "moderate", sign, why, n, nv, na,
                    {"median_unit_statistic": float(np.median(stat)) if stat else None,
                     "leg_assignment": (gate or {}).get("result", "unknown")})


def _ends(x, run, frac):
    e = max(1, int(round(frac * len(run))))
    return float(np.nanmean(x[run[:e]])), float(np.nanmean(x[run[-e:]]))


def hip_stance_extension_test(values, stance, task, gate=None, p=DEFAULTS):
    """Moderate (plate timing): over a planted foot the body progresses forward, so the
    hip extends from contact to toe-off; the rule-B hip angle falls over stance."""
    def vote(x, run):
        start, end = _ends(x, run, p["hip_stance_edge"])
        d = end - start
        if not np.isfinite(d) or abs(d) < p["hip_stance_min_rad"]:
            return None, d
        return (1 if d < 0 else -1), d
    return _timing_test("hip_stance_extension", "hip_angle", values, stance, task,
                        HIP_STANCE_TASKS, gate, vote, p)


def ankle_pushoff_test(values, stance, task, gate=None, p=DEFAULTS):
    """Moderate (plate timing): from heel rise to toe-off the foot pivots on the forefoot
    while the shank rotates forward, so the ankle plantarflexes; the rule-B ankle angle
    falls over the last quarter of stance."""
    def vote(x, run):
        w = max(4, int(round(p["ankle_pushoff_window"] * len(run))))
        seg = run[-w:]
        d = float(np.nanmean(x[seg[-3:]]) - np.nanmean(x[seg[:3]]))
        if not np.isfinite(d) or abs(d) < p["ankle_pushoff_min_rad"]:
            return None, d
        return (1 if d < 0 else -1), d
    return _timing_test("ankle_pushoff_plantarflexion", "ankle_angle", values, stance, task,
                        ANKLE_PUSHOFF_TASKS, gate, vote, p)


def hip_moment_timing_test(moment, stance, task, gate=None, p=DEFAULTS):
    """Moderate (plate timing): early stance the GRF passes in front of the hip (internal
    extensor), late stance behind it (internal flexor). Rule B: late - early > 0."""
    def vote(x, run):
        a = max(1, int(round(p["hip_moment_early"] * len(run))))
        b = max(1, int(round(p["hip_moment_late"] * len(run))))
        c = float(np.nanmean(x[run[-b:]]) - np.nanmean(x[run[:a]]))
        peak = float(np.nanmax(np.abs(x))) if np.isfinite(x).any() else 0.0
        if not np.isfinite(c) or peak == 0 or abs(c) < p["hip_moment_contrast"] * peak:
            return None, c
        return (1 if c > 0 else -1), c
    return _timing_test("hip_moment_timing", "hip_moment", moment, stance, task,
                        HIP_MOMENT_TIMING_TASKS, gate, vote, p)


def power_timing_test(joint, power, stance, task, gate=None, p=DEFAULTS):
    """Moderate (plate timing): generation around push-off is positive whatever the angle
    and moment conventions: ankle push-off (A2, last 25 % of stance) and hip pre-swing /
    initial-swing flexor generation (H3, +-10 % of stance length around toe-off)."""
    def vote(x, run):
        w = max(3, int(round(p[f"power_window_{joint}"] * len(run))))
        if joint == "hip":
            idx = [(run[-1] + k) % len(x) for k in range(-w + 1, w + 1)]
        else:
            idx = run[-w:]
        m = float(np.nanmean(x[idx]))
        peak = float(np.nanmax(np.abs(x))) if np.isfinite(x).any() else 0.0
        if not np.isfinite(m) or peak == 0 or abs(m) < p["power_timing_fraction"] * peak:
            return None, m
        return (1 if m > 0 else -1), m
    return _timing_test("power_timing", f"{joint}_power", power, stance, task,
                        POWER_TIMING_TASKS[joint], gate, vote, p)


def _cross2(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def inverse_dynamics_light(points, cop, grf_per_kg, durations_s, p=DEFAULTS):
    """Planar Newton-Euler hip moment per kg (rule B: internal, flexor positive).

    points: sagittal hip, knee, ankle, heel, toe (units, samples, 2) in metres;
    grf_per_kg on the foot (units, samples, 2), zero or NaN in swing; durations_s:
    seconds per unit. Segments: thigh hip->knee, shank knee->ankle, foot heel->toe with
    Winter (2009) mass, COM and radius-of-gyration fractions. Positions are low-pass
    filtered (zero-lag Butterworth, 2nd order, `id_lowpass_hz`) before differentiation.
    Units are heel strike to heel strike, so they are nearly periodic once the linear
    drift (overground translation) is removed: each point is detrended, padded
    periodically, filtered and differentiated on the padded series, then cropped. This
    avoids filter edge transients of about fs / cutoff samples at each unit end.
    Returns NaN for units with missing points. A sign test input, not an ID result.
    """
    from scipy.signal import butter, filtfilt
    n_u, n = points["hip"].shape[:2]
    out = np.full((n_u, n), np.nan)
    g = np.array([0.0, -G])
    for u in range(n_u):
        dt = float(durations_s[u]) / (n - 1)
        fs = 1.0 / dt
        if not np.isfinite(dt) or dt <= 0 or p["id_lowpass_hz"] >= 0.5 * fs:
            continue
        b, a = butter(2, p["id_lowpass_hz"] / (0.5 * fs))
        pad = min(n - 2, int(np.ceil(3 * fs / p["id_lowpass_hz"])))
        s_idx = np.arange(-pad, n + pad)[:, None] / (n - 1)
        P = {}
        for k in ("hip", "knee", "ankle", "heel", "toe"):
            x = np.asarray(points[k][u], float)
            if not np.isfinite(x).all():
                break
            slope = x[-1] - x[0]
            x0 = x - np.arange(n)[:, None] / (n - 1) * slope
            xp = np.concatenate([x0[-pad - 1:-1], x0, x0[1:pad + 1]])
            P[k] = filtfilt(b, a, xp, axis=0) + s_idx * slope
        if len(P) < 5:
            continue
        keep = slice(pad, pad + n)
        seg = {}
        for name, (prox, dist) in (("thigh", ("hip", "knee")), ("shank", ("knee", "ankle")),
                                   ("foot", ("heel", "toe"))):
            frac, com, rho = WINTER_SEGMENTS[name]
            v = P[dist] - P[prox]
            length = float(np.mean(np.hypot(v[keep, 0], v[keep, 1])))
            c = P[prox] + com * v
            theta = np.unwrap(np.arctan2(v[:, 1], v[:, 0]))
            alpha = np.gradient(np.gradient(theta, dt), dt)[keep]
            acc = np.gradient(np.gradient(c, dt, axis=0), dt, axis=0)[keep]
            seg[name] = (frac, frac * (rho * length) ** 2, c[keep], alpha, acc)
        P = {k: v[keep] for k, v in P.items()}
        F = np.nan_to_num(np.asarray(grf_per_kg[u], float))
        q = np.asarray(cop[u], float)
        mf, If, cf, af, accf = seg["foot"]
        q = np.where(np.isfinite(q), q, cf)
        Fa = mf * (accf - g) - F
        Ma = If * af - _cross2(q - cf, F) - _cross2(P["ankle"] - cf, Fa)
        ms, Is, cs, a_s, accs = seg["shank"]
        Fk = ms * (accs - g) + Fa
        Mk = Is * a_s + Ma - _cross2(P["knee"] - cs, Fk) + _cross2(P["ankle"] - cs, Fa)
        mt, It, ct, at, acct = seg["thigh"]
        Fh = mt * (acct - g) + Fk
        Mh = It * at + Mk - _cross2(P["hip"] - ct, Fh) + _cross2(P["knee"] - ct, Fk)
        out[u] = JOINT_CCW["hip"] * Mh
    return out


def id_light_test(moment, estimate, frame, p=DEFAULTS):
    """Moderate (plate geometry): hip moment vs the ID-light estimate over whole units."""
    ch, n = "hip_moment", moment.shape[0]
    failed = [k for k, v in (frame or {}).items() if v.get("result") == "fail"]
    if failed:
        return Evidence("inverse_dynamics_light", ch, "moderate", None,
                        f"plate frame check failed ({', '.join(failed)})", n, stats={"frame": frame})
    signs, slopes, rs, r_half = [], [], [], []
    for u in range(n):
        f = _fit(moment[u], estimate[u], p["min_samples_per_unit"])
        if f is None:
            signs.append(None)
            continue
        slopes.append(f[0])
        rs.append(f[1])
        signs.append(int(np.sign(f[0])) if abs(f[1]) >= p["r_id_light"] else None)
        fh = _fit(np.roll(moment[u], moment.shape[1] // 2), estimate[u], p["min_samples_per_unit"])
        if fh is not None:
            r_half.append(fh[1])
    sign, nv, na, why = _vote(signs, p)
    ev = Evidence("inverse_dynamics_light", ch, "moderate", sign, why, n, nv, na,
                  {"median_slope": float(np.median(slopes)) if slopes else None,
                   "segments": "Winter (2009) Table 4.1", "frame": frame})
    return _apply_half_cycle(ev, _half_cycle(rs, r_half, p))


def knee_hinge_test(values, task, p=DEFAULTS):
    """Moderate: the knee hyperextends little, so in walking its large swing
    excursion is flexion (positive under rule B). Depends on walking duty factor."""
    ch = "knee_angle"
    if task not in KNEE_HINGE_TASKS:
        return Evidence("knee_hinge_asymmetry", ch, "moderate", None,
                        f"task {task!r} not a walking task", values.shape[0])
    signs = []
    for u in range(values.shape[0]):
        x = values[u][np.isfinite(values[u])]
        if x.size < p["min_samples_per_unit"]:
            signs.append(None)
            continue
        med = np.median(x)
        hi, lo = x.max() - med, med - x.min()
        if hi + lo < p["knee_min_range_rad"]:
            signs.append(None)
        elif hi >= p["knee_excursion_ratio"] * lo:
            signs.append(1)   # large excursion on the positive side: flexion positive already
        elif lo >= p["knee_excursion_ratio"] * hi:
            signs.append(-1)
        else:
            signs.append(None)
    sign, nv, na, why = _vote(signs, p)
    return Evidence("knee_hinge_asymmetry", ch, "moderate", sign, why, values.shape[0], nv, na)


def template_test(channel, values, template, citation, p=DEFAULTS):
    """Weak, circular: correlation with a cited typical waveform. Never applies a sign."""
    signs = []
    for u in range(values.shape[0]):
        f = _fit(values[u], np.asarray(template, float), p["min_samples_per_unit"])
        signs.append(None if f is None or abs(f[1]) < p["r_template"] else int(np.sign(f[1])))
    sign, nv, na, why = _vote(signs, p)
    return Evidence("template", channel, "weak", sign, why, values.shape[0], nv, na,
                    {"citation": citation})


def documentation_evidence(channel, sign, citation):
    """Source statement. Never counts toward applying; disagreement with data is a conflict."""
    return Evidence("documentation", channel, "documentation", int(sign), "", 0, 0, 0,
                    {"citation": citation})


def chain_relation(distal, proximal, joint, vals, p=DEFAULTS):
    """distal = proximal + JOINT_CCW x joint (rule B). Fits the source sign pattern up
    to a global flip.

    Returns two pairwise relations: sign(distal)*sign(proximal), sign(distal)*sign(joint).
    """
    d, q, j = vals[distal], vals[proximal], vals[joint]
    c = JOINT_CCW[joint.split("_")[0]]
    patterns = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    unit_pat, best_rms = [], []
    for u in range(d.shape[0]):
        rms = []
        for a, b in patterns:
            res = d[u] - a * q[u] - b * j[u]
            res = res[np.isfinite(res)]
            rms.append(np.sqrt(np.mean((res - res.mean()) ** 2))
                       if res.size >= p["min_samples_per_unit"] else np.nan)
        rms = np.asarray(rms)
        if not np.isfinite(rms).all():
            unit_pat.append(None)
            continue
        order = np.argsort(rms)
        best_rms.append(float(rms[order[0]]))
        unit_pat.append(int(order[0]) if rms[order[0]] <= p["chain_margin"] * rms[order[1]]
                        else None)
    votes = [x for x in unit_pat if x is not None]
    rels = []
    lead = max(set(votes), key=votes.count) if votes else None
    agree = votes.count(lead) if votes else 0
    ok = len(votes) >= p["min_units"] and agree / max(len(votes), 1) >= p["unit_agreement"]
    why = "" if ok else (f"units split {agree}/{len(votes)}" if len(votes) >= p["min_units"]
                         else f"only {len(votes)} units cast a vote")
    a, b = patterns[lead] if ok else (None, None)
    stats = {"median_best_rms_rad": float(np.median(best_rms)) if best_rms else None,
             "note": "residual includes zero-definition offsets of all three channels"}
    # Fitted b multiplies the source joint, so b = c * sign(distal) * sign(joint).
    for other, prod in ((proximal, a), (joint, None if b is None else c * b)):
        rels.append(Relation("segment_chain", (distal, other), "strong", prod, why,
                             d.shape[0], len(votes), agree, stats))
    return rels


def power_relation(joint, vals, dt=None, p=DEFAULTS):
    """power = moment x joint speed. Constrains sign(moment)*sign(angle)*sign(power).

    Phase data (dt None) use the per-sample derivative: a positive factor, sign-only.
    """
    m, q, pw = vals[f"{joint}_moment"], vals[f"{joint}_angle"], vals[f"{joint}_power"]
    w = np.gradient(q, axis=1) / (dt if dt else 1.0)
    signs, slopes = [], []
    for u in range(m.shape[0]):
        f = _fit(pw[u], m[u] * w[u], p["min_samples_per_unit"])
        if f is None:
            signs.append(None)
            continue
        slopes.append(f[0])
        signs.append(int(np.sign(f[1])) if abs(f[1]) >= p["r_power"] else None)
    prod, nv, na, why = _vote(signs, p)
    return Relation("power_identity", (f"{joint}_moment", f"{joint}_angle", f"{joint}_power"),
                    "strong", prod, why, m.shape[0], nv, na,
                    {"median_slope": float(np.median(slopes)) if slopes and dt else None,
                     "slope_meaningful": bool(dt)})


# --------------------------------------------------------------- combining
def _family(test, grouping):
    key = test if test.startswith("derived:") else test.split(":")[0]
    return FAMILY_GROUPINGS[grouping].get(key)


def combine(evidence, min_families=DEFAULTS["min_families"],
            grouping=DEFAULTS["family_grouping"]):
    """Per-channel verdict from a list of Evidence for one channel.

    apply needs agreeing moderate/strong tests from >= `min_families` families
    (score >= 2 as well); a single test or a single family gives at most suggest.
    """
    data = [e for e in evidence if not e.abstained and e.strength != "documentation"]
    docs = [e for e in evidence if not e.abstained and e.strength == "documentation"]
    strong_like = [e for e in data if STRENGTH_SCORE[e.strength] > 0]
    signs = {e.sign for e in strong_like}
    if len(signs) > 1:
        return {"verdict": "conflict", "sign": None, "confidence": "none",
                "reason": "moderate/strong tests disagree"}
    if not strong_like:
        weak = {e.sign for e in data}
        hint = weak.pop() if len(weak) == 1 else None
        return {"verdict": "abstain", "sign": None, "confidence": "none",
                "reason": "only weak evidence" if data else "no test decided",
                "weak_hint": hint}
    lead = signs.pop()
    if any(d.sign != lead for d in docs):
        return {"verdict": "conflict", "sign": None, "confidence": "none",
                "reason": "source documentation disagrees with data evidence"}
    score = sum(STRENGTH_SCORE[e.strength] for e in strong_like)
    # A column from the other leg flips every fixed-timing shape test together: when a
    # reference-waveform test cannot tell lag 0 from a half-cycle lag, it and the
    # plate-timed tests count as one family.
    ambiguous = any(e.stats.get("half_cycle_ambiguous") for e in strong_like)

    def fam(e):
        if ambiguous and (e.stats.get("half_cycle_ambiguous") or e.test in PLATE_TIMING_TESTS):
            return "fixed_timing_shape"
        return _family(e.test, grouping)
    families = sorted({f for f in (fam(e) for e in strong_like) if f})
    weak_dissent = any(e.sign != lead for e in data if e.strength == "weak")
    if score >= 2 and len(families) >= min_families:
        conf = "high" if score >= 4 and not weak_dissent else "medium"
        return {"verdict": "apply", "sign": lead, "confidence": conf, "families": families,
                "reason": f"score {score} from families {', '.join(families)}"
                          + ("; weak evidence dissents" if weak_dissent else "")}
    return {"verdict": "suggest", "sign": lead, "confidence": "medium" if score >= 2 else "low",
            "families": families,
            "reason": f"{len(strong_like)} agreeing test(s) from {len(families)} famil"
                      f"{'y' if len(families) == 1 else 'ies'} ({', '.join(families) or 'none'}); "
                      f"apply needs {min_families}; flagged for review"
                      + ("; half-cycle ambiguous: a column from the other leg would look "
                         "the same" if ambiguous else "")}


def _propagate(verdicts, evidence, relations, **combine_kw):
    """Resolve contradictions first, then derive one hop.

    1. Every decided relation whose channels all carry a sign (`apply` or
       `suggest`) is checked against one snapshot; every member of every
       contradicting relation becomes `conflict`, whatever the relation order.
    2. A decided relation whose other channels are all still `apply` (from direct
       evidence, after step 1) yields derived evidence for its remaining channel.
       Derivations read a snapshot taken after step 1, so relation order does not
       matter and derived signs never derive further.
    """
    before = dict(verdicts)  # every relation is judged against the same snapshot
    decided = ("apply", "suggest")
    contradicted = [rel for rel in relations if rel.product is not None
                    and all(before.get(c, {}).get("verdict") in decided for c in rel.channels)
                    and int(np.prod([before[c]["sign"] for c in rel.channels])) != rel.product]
    for rel in contradicted:
        for c in rel.channels:
            evidence[c].append(Evidence(f"derived:{rel.test}", c, "strong", None,
                                        f"relation {'/'.join(rel.channels)} inconsistent "
                                        "with applied or suggested signs"))
            verdicts[c] = {"verdict": "conflict", "sign": None, "confidence": "none",
                           "reason": f"{rel.test} contradicts applied or suggested signs"}
    anchors = {c: v["sign"] for c, v in verdicts.items() if v.get("verdict") == "apply"}
    touched = set()
    for rel in relations:
        if rel.product is None:
            continue
        applied = [c for c in rel.channels if c in anchors]
        missing = [c for c in rel.channels if c not in anchors]
        if len(missing) != 1 or missing[0] not in evidence:
            continue
        target = missing[0]
        if verdicts[target].get("verdict") == "conflict":
            continue  # conflicts are sticky: no later step may downgrade them
        derived = rel.product * int(np.prod([anchors[c] for c in applied]))
        evidence[target].append(Evidence(
            f"derived:{rel.test}", target, rel.strength, derived,
            f"from {rel.test} with applied {', '.join(applied)}", rel.units,
            rel.units_voting, rel.units_agreeing))
        touched.add(target)
    for target in touched:
        new = combine(evidence[target], **combine_kw)
        if verdicts[target].get("verdict") != "conflict":
            verdicts[target] = new
    return verdicts


# ------------------------------------------------------------------ driver
def detect_leg(dataset, leg, channels, *, reference_angles=None, joint_positions=None,
               cop=None, grf=None, stance=None, dt=None, task=None, documentation=(),
               templates=None, source_columns=None, params=None, marker_points=None,
               grf_unit=None, body_mass_kg=None, cop_registration=None, unit_durations_s=None):
    """Run every applicable test for one leg and return a JSON-serialisable report.

    channels: logical name (keys of TARGET_CONVENTION, plus ``<joint>_power``)
    -> (units, samples) source array. reference_angles: rule-B angles from an
    independent source (e.g. ``marker_reference_angles``). documentation:
    iterable of (channel, sign, citation). templates: channel -> (template, citation).
    marker_points: sagittal points (see ``marker_reference_angles``); when given, the
    vertical-order check is recorded and marker angles/joint centres fill gaps in
    ``reference_angles`` / ``joint_positions``. Marker references are used only
    when the vertical-order check passes (an unknown check blocks them).
    grf_unit: declared vertical GRF unit (N_per_kg, BW or N), needed to derive a
    stance mask from ``grf``; without it, pass ``stance`` or force-plate tests abstain.
    cop_registration: the adapter's rule for putting CoP and markers on one origin
    (recorded in the report; the plate frame check tests it when heel/toe exist).
    unit_durations_s: seconds per unit; needed by the ID-light hip test.
    """
    p = dict(DEFAULTS, **(params or {}))
    ckw = {"min_families": p["min_families"], "grouping": p["family_grouping"]}
    vals = {k: np.array(v, float) for k, v in channels.items()}
    ref = dict(reference_angles or {})
    marker_checks = None
    vo = getattr(reference_angles, "vertical_order", None)
    if vo is not None and vo.get("result") != "pass":
        ref = {}
        marker_checks = {**vo, "action": "marker references not used: vertical order "
                                         "could not be confirmed"}
    dropped = [k for k, v in ref.items() if isinstance(v, MarkerAngle)
               and (v.vertical_order or {}).get("result") != "pass"]
    for k in dropped:
        marker_checks = {**(ref[k].vertical_order or {"result": "unknown"}),
                         "action": "marker references not used: vertical order could "
                                   "not be confirmed (guard carried by the arrays)",
                         "dropped": sorted(dropped)}
        del ref[k]
    joint_positions = dict(joint_positions or {})
    if marker_points is not None:
        vchk = vertical_order_check(marker_points, p["vertical_order_min_frames"],
                                    p["vertical_order_min"])
        marker_checks = {"vertical_order_fraction": vchk["fraction"],
                         "visible_frames": vchk["visible_frames"],
                         "required_frames": vchk["required_frames"],
                         "required": p["vertical_order_min"]}
        try:
            mref = marker_reference_angles(marker_points, p["vertical_order_min"])
            marker_checks["result"] = mref.vertical_order["result"]
            if marker_checks["result"] == "pass":
                for k, v in mref.items():
                    ref.setdefault(k, v)
                for j in JOINTS:
                    if j in marker_points:
                        joint_positions.setdefault(j, np.asarray(marker_points[j], float))
            else:
                marker_checks["action"] = ("marker references not used: no foot and upper "
                                           "marker pair to confirm the up vector")
        except ValueError as exc:
            marker_checks.update(result="fail", reason=str(exc),
                                 action="marker references not used")
    screens, refused = {}, {}
    for k in list(vals):
        if k.endswith("_angle") or k == "pelvis_tilt":
            peak = np.nanmax(np.abs(vals[k])) if np.isfinite(vals[k]).any() else 0.0
            if peak > 2 * np.pi:
                refused[k] = (f"|value| reaches {peak:.1f} > 2*pi: not radians "
                              "(degrees?); convert units before detection")
                continue
            fit, mask, summary = screen_branch(vals[k], p)
            vals[k] = np.where(mask, np.nan, fit)
            if mask.any() or summary["wrap_360_frames"] or summary["far_from_median_frames"]:
                screens[k] = summary
    stance_note, grf_check = None, None
    if grf is not None and grf_unit is not None:
        grf_check = grf_unit_check(grf[..., 1], grf_unit, body_mass_kg)
        if grf_check["result"] != "pass":
            stance_note = (f"declared GRF unit {grf_unit!r} implausible for the data "
                           f"(median peak {grf_check.get('median_unit_peak', float('nan')):.3g}, "
                           f"band {grf_check.get('plausible_band')}): force-plate tests abstain")
            grf, cop, stance = None, None, None
    if stance is None and grf is not None:
        if grf_unit in STANCE_FLOOR:
            stance = stance_from_grf(grf[..., 1], grf_unit, p["stance_grf_fraction"])
        else:
            stance_note = (f"GRF unit {grf_unit!r} not declared (N_per_kg, BW or N): "
                           "no stance mask")
    frame = None
    if grf is not None and cop is not None and stance is not None:
        feet = marker_points if (marker_points is not None and marker_checks
                                 and marker_checks.get("result") == "pass") else {}
        frame = plate_frame_check(cop, joint_positions.get("ankle"), grf, stance, p, task,
                                  feet.get("heel"), feet.get("toe"))

    gate = (leg_assignment_check(vals.get("knee_angle") if "knee_angle" not in refused else None,
                                 stance, task, p) if stance is not None else None)
    ev = {k: [] for k in vals}
    for k, why in refused.items():
        ev[k].append(Evidence("units_check", k, "strong", None, why, vals[k].shape[0]))
    for k, v in vals.items():
        if k in refused:
            continue
        if k in ref:
            ev[k].append(reference_angle_test(k, v, np.asarray(ref[k], float), p))
        if templates and k in templates:
            ev[k].append(template_test(k, v, templates[k][0], templates[k][1], p))
    if "knee_angle" in vals and "knee_angle" not in refused:
        ev["knee_angle"].append(knee_hinge_test(vals["knee_angle"], task, p))
    for k, test in (("hip_angle", hip_stance_extension_test), ("ankle_angle", ankle_pushoff_test)):
        if k in vals and k not in refused:
            ev[k].append(test(vals[k], stance, task, gate, p))
    for j in ("hip", "ankle"):
        if f"{j}_power" in vals:
            ev[f"{j}_power"].append(power_timing_test(j, vals[f"{j}_power"], stance, task, gate, p))
    for j in JOINTS:
        mk = f"{j}_moment"
        if mk not in vals:
            continue
        if grf is None or cop is None or stance is None:
            ev[mk].append(Evidence("lever_arm", mk, LEVER_ARM_STRENGTH[j], None,
                                   stance_note or "no force plate (GRF/CoP) data",
                                   vals[mk].shape[0]))
        elif not joint_positions or j not in joint_positions:
            ev[mk].append(Evidence("lever_arm", mk, LEVER_ARM_STRENGTH[j], None,
                                   "no joint-centre positions", vals[mk].shape[0]))
        else:
            ev[mk].append(lever_arm_test(j, vals[mk], joint_positions[j], cop, grf, stance, p,
                                         frame))
        if j == "ankle":
            if stance is None:
                ev[mk].append(Evidence("late_stance_plantarflexor", mk, "moderate", None,
                                       stance_note or "no stance mask (no force plate)",
                                       vals[mk].shape[0]))
            else:
                ev[mk].append(late_stance_ankle_test(vals[mk], stance, task, p, gate))
        if j == "hip":
            ev[mk].append(hip_moment_timing_test(vals[mk], stance, task, gate, p))
            ev[mk].append(_id_light_evidence(vals[mk], marker_points, marker_checks, cop, grf,
                                             grf_unit, body_mass_kg, unit_durations_s, frame, p))
    for c, s, cite in documentation:
        if c in ev:
            ev[c].append(documentation_evidence(c, s, cite))

    relations = []
    usable = {k for k in vals if k not in refused}
    for chain in CHAIN:
        if all(c in usable for c in chain):
            relations.extend(chain_relation(*chain, vals, p))
    for j in JOINTS:
        if all(f"{j}_{x}" in usable for x in ("moment", "angle", "power")):
            relations.append(power_relation(j, vals, dt, p))

    verdicts = {}
    for k, e in ev.items():
        verdicts[k] = combine(e, **ckw)
        half = [x for x in e if x.stats.get("half_turn_offset")]
        if half:  # rule 6: whatever the sign evidence says; sticky through propagation
            verdicts[k] = {"verdict": "conflict", "sign": None, "confidence": "none",
                           "reason": "half-turn offset: branch or zero-definition mismatch "
                                     f"({half[0].offset['estimate']:.2f} rad)"}
    verdicts = _propagate(verdicts, ev, relations, **ckw)

    report = {"schema_version": SCHEMA_VERSION, "dataset": dataset, "leg": leg,
              "task": task, "index": "time" if dt else "phase_or_unknown",
              "target_convention": TARGET_CONVENTION, "scientific_approval": False,
              "parameters": {k: list(v) if isinstance(v, tuple) else v for k, v in p.items()},
              "marker_checks": marker_checks, "plate_frame_check": frame,
              "grf_unit_check": grf_check, "leg_assignment_check": gate,
              "cop_registration": cop_registration or "undeclared",
              "channels": {}, "relations": [asdict(r) for r in relations], "log": []}
    for k in vals:
        v = verdicts[k]
        off = next((e.offset for e in ev[k]
                    if e.offset and (e.sign == v["sign"] or e.stats.get("half_turn_offset"))),
                   None)
        report["channels"][k] = {
            "source_column": (source_columns or {}).get(k),
            **v,
            "sign_applied": v["verdict"] == "apply",
            "offset": off or {"estimate": None, "ci95": None, "applied": False,
                              "reason": "no independent reference angle"},
            "evidence": [asdict(e) for e in ev[k]],
            "branch_screen": screens.get(k),
        }
        if v["verdict"] == "apply":
            used = [f"{e.test}({e.strength}, {e.units_agreeing}/{e.units_voting})"
                    for e in ev[k] if e.sign == v["sign"]]
            report["log"].append(f"apply sign {v['sign']:+d} to {k}: " + ", ".join(used))
        if off and off.get("flag_for_review"):
            report["log"].append(f"flag offset on {k}: {off['estimate']:.4f} rad "
                                 f"[{off['ci95'][0]:.4f}, {off['ci95'][1]:.4f}]; not applied")
    return _clean(report)


def _id_light_evidence(moment, marker_points, marker_checks, cop, grf, grf_unit, body_mass_kg,
                       durations, frame, p):
    n = moment.shape[0]
    need = ("hip", "knee", "ankle", "heel", "toe")
    why = None
    if grf is None or cop is None:
        why = "no force plate (GRF/CoP) data"
    elif marker_points is None or not all(k in marker_points for k in need):
        why = "needs hip, knee, ankle, heel and toe marker points"
    elif not marker_checks or marker_checks.get("result") != "pass":
        why = "marker vertical-order check did not pass"
    elif durations is None:
        why = "no unit durations (accelerations need time)"
    scale = {"N_per_kg": 1.0, "BW": G}.get(grf_unit)
    if why is None and scale is None:
        scale = 1.0 / body_mass_kg if (grf_unit == "N" and body_mass_kg) else None
        if scale is None:
            why = f"GRF unit {grf_unit!r} cannot be expressed per kg without a declared mass"
    if why:
        return Evidence("inverse_dynamics_light", "hip_moment", "moderate", None, why, n)
    est = inverse_dynamics_light({k: np.asarray(marker_points[k], float) for k in need},
                                 cop, np.asarray(grf, float) * scale,
                                 np.asarray(durations, float), p)
    return id_light_test(moment, est, frame, p)


def apply_signs(channels, report):
    """Multiply only channels whose verdict is `apply`. Offsets are never applied."""
    out, log = {}, []
    for k, v in channels.items():
        c = report["channels"].get(k, {})
        if c.get("sign_applied"):
            out[k] = c["sign"] * np.asarray(v, float)
            log.append(f"{k}: x{c['sign']:+d}")
        else:
            out[k] = np.asarray(v, float)
    return out, log


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o
