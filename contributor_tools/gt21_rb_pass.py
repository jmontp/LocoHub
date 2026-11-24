"""Georgia Tech 2021 merged pass (GT21-RB02 plates and forces + GT21-RB04 conventions): pure functions, no file access.

One continuous 200 Hz table per recording is built from one read of the source tables (markers, force plates, gait
cycle tables, inverse-dynamics moments). Segmentation into steps (RB03) and the 150-sample export (RB05) run on this
table later. The standard is docs/reference/index.md (24 November 2026). Decisions applied:

* D-REF-1/2/4: joint angles are differences of gravity-referenced segment angles (hip = thigh - pelvis, knee = thigh -
  shank, ankle = foot - shank); each leg is measured in its own vertical plane, the one perpendicular to that leg's knee
  flexion axis; the pelvis uses mid-PSIS to mid-ASIS (horizontal part). The centre of pressure is in the ankle (foot)
  frame inside the leg plane, origin 100 mm forward of the ankle centre, lateral outward from the leg.
* D-GT21-C01-1 = B: sideways force and centre of pressure positive outward for each leg.
* D-GT21-C01-2 = C: pelvis tilt from the ASIS and PSIS markers.
* D-GT21-REB-1 = C: GT21 has lateral-only knee and ankle markers, so the knee flexion axis and the ankle centre come
  from the authors' scaled OpenSim model, placed each frame by a rigid fit of the model's markers on each body to the
  measured markers (no OpenSim installation; the model text supplies marker positions and joint locations).
* Body weight: SubjectInfo Weight is in kilograms (VariableUnits "kg"). BW = Weight x 9.81 N and Nm/kg = moment / Weight.
  The model mass is never used.

Re-implemented here, with their own tests, from descriptions in docs/maintainers/handoffs/ESML-crosswalk.json and from
the energy-shaping-ML project's ankle_expressivity/gt21_force.py (plate ownership by marker distance with an
ambiguous two-feet zone and an events fallback; forces and CoP summed over a foot's plates; thresholds 50 N contact,
1 N edge, 100 N vote, 1/3-2/3 ambiguous band; CoP rows beyond the foot-frame limits left missing) and from
cop_reference_gt21.m (ankle centre from the tibia offset of the scaled model). Credit: that project (Jose Montes
Perez's energy-shaping ML work). Nothing is imported from it and none of its outputs were opened. The geometry and the
per-leg plane maths are ported from contributor_tools/gt23_conventions.py (GT23-C06) as copies, not imports.

Missing stays missing: no value is filled, interpolated across a gap or invented. Unassigned or ambiguous plate
contacts give no force for either foot and are counted. Trunk is not produced (no source). No scientific approval.
"""
import math
import re
from xml.etree import ElementTree as ET

import numpy as np

UP = np.array([0.0, 1.0, 0.0])
G = 9.81
FOOT_ORIGIN_M = 0.1
# Plate contact and ownership thresholds (energy-shaping ML values, adopted; see the module note).
CONTACT_N, EDGE_N, VOTE_N = 50.0, 1.0, 100.0
BRIDGE_SAMPLES = 4
AMBIGUOUS = (1.0 / 3.0, 2.0 / 3.0)
EVENT_DROP = 50.0
# CoP is kept only with at least 0.2 BW on the foot and inside these foot-frame limits.
COP_MIN_BW = 0.2
COP_MAX_ANTERIOR_M = 0.5
COP_MAX_LATERAL_M = 0.10
Z_GATE = math.cos(math.radians(45.0))      # lab Z axis must lie within 45 degrees of the walking direction
LEGS = ('right', 'left')
SIDE = {'right': 'R', 'left': 'L'}

PELVIS_MARKERS = ('L_ASIS', 'R_ASIS', 'L_PSIS', 'R_PSIS')
THIGH_CLUSTER = ('Thigh_Upper', 'Thigh_Front', 'Thigh_Rear', 'Knee_Lat')
SHANK_CLUSTER = ('Shank_Upper', 'Shank_Front', 'Shank_Rear', 'Ankle_Lat')
FOOT_MARKERS = ('Heel', 'Toe_Tip')
MIN_FIT_MARKERS = 3
# Per-frame geometry hold, fixed before r4 from the r3 pilot distributions (medians 1-5 mm residual and 4-10 deg axis angle;
# p95 at most 17 mm and 17 deg): a frame whose pelvis, femur or tibia rigid-fit residual exceeds 20 mm (about four times the
# worst median, above every observed p95), or whose knee axis is more than 45 degrees from the lateral-knee-marker direction
# (about three times the worst p95), has that leg's segment angles, joint angles, speeds and CoP set to missing. Not tuned to a
# pass rate. Force and moments do not depend on the fit and are kept.
HOLD_RESIDUAL_M = 0.020
HOLD_AXIS_RAD = math.radians(45.0)
HOLD_RESIDUAL, HOLD_AXIS = 1, 2          # bit values of the per-frame hold code


class RecordingExcluded(Exception):
    """The recording cannot be processed; the message is the listed reason. Never a reason to stop a batch."""


# ------------------------------------------------------------------------------------------------ vectors and angles
def unit(v):
    """Row-wise unit vectors; a zero or nonfinite row becomes NaN."""
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    with np.errstate(invalid='ignore', divide='ignore'):
        out = v / n
    out[~np.isfinite(n[..., 0]) | (n[..., 0] == 0)] = np.nan
    return out


def sag(v, fwd):
    """(forward, up) components of lab vectors for forward directions (n, 3)."""
    v = np.asarray(v, float)
    return np.stack([np.sum(v * fwd, axis=-1), v @ UP], axis=-1)


def angle_from_down(v2):
    """Counterclockwise angle of a proximal-to-distal (forward, up) vector from straight down (distal end forward > 0)."""
    return np.arctan2(v2[..., 0], -v2[..., 1])


def angle_from_forward(v2):
    """Counterclockwise angle of a (forward, up) vector from forward horizontal (toes up > 0)."""
    return np.arctan2(v2[..., 1], v2[..., 0])


def wrap(a):
    return (np.asarray(a, float) + np.pi) % (2 * np.pi) - np.pi


def horizontal(v):
    v = np.asarray(v, float)
    return v - (v @ UP)[:, None] * UP


def pelvis_forward(asis_mid, psis_mid):
    """Pelvis forward: horizontal part of mid-PSIS to mid-ASIS, unit (n, 3)."""
    return unit(horizontal(np.asarray(asis_mid, float) - np.asarray(psis_mid, float)))


def pelvis_angle(asis_mid, psis_mid):
    """Pelvis angle in its own plane: increases when the front rises; anterior tilt is negative."""
    d = np.asarray(asis_mid, float) - np.asarray(psis_mid, float)
    return angle_from_forward(sag(d, pelvis_forward(asis_mid, psis_mid)))


def knee_axis_to_right(axis, right_ref):
    """Orient a knee flexion axis (n, 3) so it points to the person's right: its component along right_ref (n, 3), the
    person's right from the pelvis, is positive. A zero component gives NaN (the side cannot be told)."""
    axis = np.asarray(axis, float)
    s = np.sign(np.sum(axis * np.asarray(right_ref, float), axis=-1))
    out = axis * s[:, None]
    out[s == 0] = np.nan
    return out


def plane_forward(axis_to_right):
    """Forward direction of the vertical plane perpendicular to an axis: up x (the axis's horizontal part), unit."""
    return unit(np.cross(UP, horizontal(axis_to_right)))


def segment_angles(fwd_leg, hip, knee, ankle, heel, toe):
    """Thigh, shank and foot angles of one leg in that leg's plane. Centres and markers are lab points (n, 3)."""
    return {'thigh': angle_from_down(sag(np.asarray(knee, float) - np.asarray(hip, float), fwd_leg)),
            'shank': angle_from_down(sag(np.asarray(ankle, float) - np.asarray(knee, float), fwd_leg)),
            'foot': angle_from_forward(sag(np.asarray(toe, float) - np.asarray(heel, float), fwd_leg))}


def joint_angles(pelvis, thigh, shank, foot):
    """The standard's zero: joint angles are differences of segment angles."""
    return {'hip': thigh - pelvis, 'knee': thigh - shank, 'ankle': foot - shank}


def central_derivative(x, t):
    """(x[i+1] - x[i-1]) / (t[i+1] - t[i-1]) with the difference wrapped to (-pi, pi]; NaN where a neighbour is not
    finite and at both ends. No smoothing. Angles in radians give rad/s."""
    x, t = np.asarray(x, float), np.asarray(t, float)
    out = np.full(x.shape, np.nan)
    if len(x) > 2:
        out[1:-1] = wrap(x[2:] - x[:-2]) / (t[2:] - t[:-2])
    return out


# ------------------------------------------------------------------------------------------------ foot frame
def foot_axes(fwd_leg, foot_angle):
    """Unit axes (n, 3) of the ankle frame in the leg's plane: anterior = forward rotated up by the foot angle, up
    perpendicular to it in the plane, right = anterior x up (the plane normal, to the person's right)."""
    c, s = np.cos(foot_angle)[:, None], np.sin(foot_angle)[:, None]
    e_f = c * fwd_leg + s * UP
    e_u = -s * fwd_leg + c * UP
    return e_f, e_u, np.cross(e_f, e_u)


def foot_frame_point(point, ankle, fwd_leg, foot_angle, leg):
    """Lab points (n, 3) in the ankle frame as (anterior, vertical, lateral) metres. Origin: 100 mm forward of the ankle
    centre along heel to toe. Lateral is outward from that leg (the right axis for the right leg, minus it for the left)."""
    e_f, e_u, e_r = foot_axes(fwd_leg, foot_angle)
    q = np.asarray(point, float) - np.asarray(ankle, float)
    lateral = np.sum(q * e_r, axis=-1)
    return {'anterior': np.sum(q * e_f, axis=-1) - FOOT_ORIGIN_M, 'vertical': np.sum(q * e_u, axis=-1),
            'lateral': lateral if leg == 'right' else -lateral}


def mask_cop(cop, vgrf):
    """Missing where under 0.2 BW, nonfinite, at the plate-origin placeholder, or outside the foot-frame limits.
    Returns (masked dict, counts per reason). Order of reasons is fixed; a sample is counted once under its first."""
    a, v, l = (np.asarray(cop[k], float).copy() for k in ('anterior', 'vertical', 'lateral'))
    vgrf = np.asarray(vgrf, float)
    reasons = {}
    taken = np.zeros(len(a), bool)
    for name, bad in (('under_contact_threshold', ~(vgrf >= COP_MIN_BW)),
                      ('nonfinite', ~(np.isfinite(a) & np.isfinite(v) & np.isfinite(l))),
                      ('outside_foot_frame_limits', (np.abs(a) > COP_MAX_ANTERIOR_M) | (np.abs(l) > COP_MAX_LATERAL_M))):
        new = bad & ~taken
        reasons[name] = int(new.sum())
        taken |= bad
    a[taken], v[taken], l[taken] = np.nan, np.nan, np.nan
    return {'anterior': a, 'vertical': v, 'lateral': l}, reasons


# ------------------------------------------------------------------------------------------------ rigid fit
def rigid_fit(local, measured):
    """Per-frame rigid fit of a body's model markers to measured markers.

    local (k, 3): marker positions in the body frame. measured (n, k, 3): lab positions. Returns rotation (n, 3, 3), origin
    (n, 3) (lab position of the body-frame origin) and rms residual (n); NaN for a frame with any nonfinite marker, fewer
    than three markers, or collinear markers. Least squares via SVD (Kabsch), reflections removed."""
    local = np.asarray(local, float)
    meas = np.asarray(measured, float)
    n = len(meas)
    R = np.full((n, 3, 3), np.nan)
    t = np.full((n, 3), np.nan)
    rms = np.full(n, np.nan)
    if local.shape[0] < MIN_FIT_MARKERS or n == 0:
        return R, t, rms
    ok = np.isfinite(meas).all(axis=(1, 2))
    if not ok.any():
        return R, t, rms
    m = meas[ok]
    lc = local.mean(axis=0)
    mc = m.mean(axis=1)
    a = local - lc
    H = np.einsum('ki,nkj->nij', a, m - mc[:, None, :])
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(np.einsum('nji,nkj->nik', Vt, U)))      # det(V U^T)
    D = np.zeros((len(m), 3, 3))
    D[:, 0, 0] = D[:, 1, 1] = 1.0
    D[:, 2, 2] = d
    Rk = np.einsum('nji,njk,nlk->nil', Vt, D, U)                        # V D U^T
    tk = mc - np.einsum('nij,j->ni', Rk, lc)
    res = np.einsum('nij,kj->nki', Rk, local) + tk[:, None, :] - m
    r = np.sqrt((res ** 2).sum(axis=2).mean(axis=1))
    bad = ~(S[:, 1] > 1e-9 * np.maximum(S[:, 0], 1e-300))               # collinear markers
    Rk[bad], tk[bad], r[bad] = np.nan, np.nan, np.nan
    R[ok], t[ok], rms[ok] = Rk, tk, r
    return R, t, rms


def apply_pose(R, t, local_point):
    """Lab position (n, 3) of a body-frame point for per-frame poses."""
    return t + np.einsum('nij,j->ni', R, np.asarray(local_point, float))


# ------------------------------------------------------------------------------------------------ the scaled model
def _vec(text):
    return np.array(text.split(), float)


def _last(name):
    return name.strip().split('/')[-1]


def euler_xyz_body_fixed(angles):
    """OpenSim orientation (body-fixed X, then Y, then Z; radians) as a rotation matrix: R = Rx Ry Rz."""
    ax, ay, az = (float(v) for v in angles)
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz


def _function_spec(ta):
    """Transform function of a TransformAxis as a plain spec: ('constant', v), ('linear', slope, intercept),
    ('spline', x, y) for SimmSpline or NaturalCubicSpline, ('scaled', factor, inner). Anything else is ('unknown',)."""
    for el in ta:
        if el.tag == 'Constant':
            return ('constant', float(el.findtext('value')))
        if el.tag == 'LinearFunction':
            c = _vec(el.findtext('coefficients'))
            return ('linear', float(c[0]), float(c[1]))
        if el.tag in ('SimmSpline', 'NaturalCubicSpline'):
            return ('spline', _vec(el.findtext('x')), _vec(el.findtext('y')))
        if el.tag == 'function':                                   # wrapper element inside a MultiplierFunction
            return _function_spec(el)
        if el.tag == 'MultiplierFunction':
            return ('scaled', float(el.findtext('scale')), _function_spec(el))
    return ('unknown',)


def eval_function(spec, q):
    """Value of a function spec at coordinate values q (n,); NaN outside a spline's range, or for an unknown function."""
    q = np.asarray(q, float)
    kind = spec[0]
    if kind == 'constant':
        return np.full(q.shape, spec[1])
    if kind == 'linear':
        return spec[1] * q + spec[2]
    if kind == 'scaled':
        return spec[1] * eval_function(spec[2], q)
    if kind == 'spline':
        from scipy.interpolate import CubicSpline
        x, y = spec[1], spec[2]
        out = CubicSpline(x, y, bc_type='natural')(np.where((q >= x[0]) & (q <= x[-1]), q, np.nan))
        return out
    return np.full(q.shape, np.nan)


def parse_osim(text):
    """Markers {name: (body, location)} and joints {name: dict} of an OpenSim 3 or 4 model text.

    A joint has parent_body, parent_location, parent_orientation, child_body, child_location, and axes (a list of
    (coordinate name, axis in the parent frame)). Raises ValueError for DOCTYPE or ENTITY declarations (the model comes
    from a download) and KeyError for a joint whose frames cannot be resolved."""
    if '<!DOCTYPE' in text or '<!ENTITY' in text:
        raise ValueError('model file declares a DOCTYPE or ENTITY; refused')
    root = ET.fromstring(text)
    markers = {}
    for m in root.iter('Marker'):
        loc = m.findtext('location')
        body = m.findtext('socket_parent_frame') or m.findtext('body')
        if loc and body:
            markers[m.get('name')] = (_last(body), _vec(loc))
    joints = {}
    for js in root.iter('JointSet'):
        for j in js.iter():
            if not j.tag.endswith('Joint') or j.get('name') is None:
                continue
            frames = {f.get('name'): f for f in j.iter('PhysicalOffsetFrame')}
            if j.findtext('socket_parent_frame'):                       # OpenSim 4 layout
                def frame(socket):
                    f = frames[_last(j.findtext(socket))]
                    return (_last(f.findtext('socket_parent')), _vec(f.findtext('translation') or '0 0 0'),
                            _vec(f.findtext('orientation') or '0 0 0'))
                pb, pl, po = frame('socket_parent_frame')
                cb, cl, _ = frame('socket_child_frame')
            elif j.findtext('parent_body'):                             # OpenSim 3 layout
                pb, pl = _last(j.findtext('parent_body')), _vec(j.findtext('location_in_parent') or '0 0 0')
                po = _vec(j.findtext('orientation_in_parent') or '0 0 0')
                cb, cl = j.get('name'), _vec(j.findtext('location') or '0 0 0')
            else:
                continue
            axes, translations = [], []
            for ta in j.iter('TransformAxis'):
                coords, axis = (ta.findtext('coordinates') or '').strip(), ta.findtext('axis')
                if coords and axis and (ta.get('name') or '').startswith('rotation'):
                    axes.append((coords, _vec(axis)))
                if axis and (ta.get('name') or '').startswith('translation'):
                    translations.append((coords, _vec(axis), _function_spec(ta)))
            joints[j.get('name')] = dict(parent_body=pb, parent_location=pl, parent_orientation=po, child_body=cb,
                                         child_location=cl, axes=axes, translations=translations)
    return markers, joints


def model_geometry(text, side):
    """Constants of one leg from the model text, in metres in the named body frames:
    hip centre in the pelvis, knee centre in the femur, knee flexion axis in the femur, ankle centre in the tibia, the
    knee centre as seen from the tibia (a cross-check), and every marker's body and location. ``side`` is 'r' or 'l'."""
    markers, joints = parse_osim(text)
    s = side
    for name, parent in ((f'hip_{s}', 'pelvis'), (f'knee_{s}', f'femur_{s}'), (f'ankle_{s}', f'tibia_{s}')):
        if name not in joints:
            raise KeyError(f'joint {name} not in model')
        if joints[name]['parent_body'] != parent:
            raise KeyError(f'joint {name} has parent {joints[name]["parent_body"]}, expected {parent}')
    knee = joints[f'knee_{s}']
    if knee['child_body'] != f'tibia_{s}':
        raise KeyError(f'knee_{s} child is {knee["child_body"]}, expected tibia_{s}')
    flex = [a for c, a in knee['axes'] if c == f'knee_angle_{s}']
    if len(flex) != 1:
        raise KeyError(f'knee_{s} needs exactly one rotation axis for knee_angle_{s}; found {len(flex)}')
    axis_femur = euler_xyz_body_fixed(knee['parent_orientation']) @ (flex[0] / np.linalg.norm(flex[0]))
    return {'hip_in_pelvis': joints[f'hip_{s}']['parent_location'], 'knee_in_femur': knee['parent_location'],
            'knee_axis_in_femur': axis_femur, 'knee_in_tibia': knee['child_location'],
            'knee_axis_in_parent': flex[0] / np.linalg.norm(flex[0]), 'knee_parent_orientation': knee['parent_orientation'],
            'knee_translations': knee['translations'],
            'ankle_in_tibia': joints[f'ankle_{s}']['parent_location'], 'markers': markers}


def body_marker_set(geo, body, names, available):
    """Marker names (from ``names``, with the side prefix already applied) that sit on ``body`` in the model and exist in
    the measured data, with their model locations (k, 3). Raises RecordingExcluded if fewer than three."""
    use = [n for n in names if n in geo['markers'] and geo['markers'][n][0] == body and n in available]
    if len(use) < MIN_FIT_MARKERS:
        raise RecordingExcluded(f'fewer than {MIN_FIT_MARKERS} fit markers on {body}: have {use}')
    return use, np.array([geo['markers'][n][1] for n in use])


def rodrigues(axis, q):
    """Rotation matrices (n, 3, 3) about a fixed unit axis by angles q (n,)."""
    a = np.asarray(axis, float)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0.0]])
    q = np.asarray(q, float)
    return np.eye(3) + np.sin(q)[:, None, None] * K + (1 - np.cos(q))[:, None, None] * (K @ K)


def knee_angle_from_fits(geo_leg, Rf, Rt):
    """Knee coordinate (radians, OpenSim sense: flexion negative) from the relative rotation of the fitted tibia in the
    fitted femur, about the model's knee axis."""
    Rpo = euler_xyz_body_fixed(geo_leg['knee_parent_orientation'])
    Rj = Rpo.T @ np.einsum('nji,njk->nik', Rf, Rt)
    a = geo_leg['knee_axis_in_parent']
    vee = 0.5 * np.stack([Rj[:, 2, 1] - Rj[:, 1, 2], Rj[:, 0, 2] - Rj[:, 2, 0], Rj[:, 1, 0] - Rj[:, 0, 1]], axis=1)
    return np.arctan2(vee @ a, 0.5 * (np.trace(Rj, axis1=1, axis2=2) - 1.0))


def knee_from_femur(geo_leg, Rf, tf, Rt):
    """Cross-check: the knee centre reached from the femur fit through the model's knee joint (parent location plus the
    angle-dependent translation functions, evaluated at the knee angle taken from the fits). NaN where a function is
    unknown or out of range."""
    q = knee_angle_from_fits(geo_leg, Rf, Rt)
    Rpo = euler_xyz_body_fixed(geo_leg['knee_parent_orientation'])
    tr = np.zeros((len(q), 3))
    for coords, axis, spec in geo_leg['knee_translations']:
        tr += eval_function(spec, q)[:, None] * np.asarray(axis, float)[None, :]
    child = np.einsum('nij,j->ni', rodrigues(geo_leg['knee_axis_in_parent'], q), np.asarray(geo_leg['knee_in_tibia'], float))
    local = np.asarray(geo_leg['knee_in_femur'], float) + (tr + child) @ Rpo.T
    return tf + np.einsum('nij,nj->ni', Rf, local)


def leg_centres(geo_leg, geo_pelvis_source, P, side):
    """Hip, knee, ankle centres, knee axis (to the person's right) and fit diagnostics for one leg.

    geo_leg: model_geometry for the leg. geo_pelvis_source: the geometry of either leg (the pelvis markers and body are
    shared; the hip centre of this leg comes from geo_leg). P: dict of measured marker positions in metres (n, 3).
    Every marker used in a body fit must be finite in a frame for that frame to have a pose; nothing is filled."""
    s, S = side, SIDE[{'r': 'right', 'l': 'left'}[side]]
    names = {k: v for k, v in P.items()}
    pel_names, pel_loc = body_marker_set(geo_leg, 'pelvis', PELVIS_MARKERS, names)
    Rp, tp, rms_p = rigid_fit(pel_loc, np.stack([P[n] for n in pel_names], axis=1))
    fem_names, fem_loc = body_marker_set(geo_leg, f'femur_{s}', [f'{S}_{m}' for m in THIGH_CLUSTER], names)
    Rf, tf, rms_f = rigid_fit(fem_loc, np.stack([P[n] for n in fem_names], axis=1))
    tib_names, tib_loc = body_marker_set(geo_leg, f'tibia_{s}', [f'{S}_{m}' for m in SHANK_CLUSTER], names)
    Rt, tt, rms_t = rigid_fit(tib_loc, np.stack([P[n] for n in tib_names], axis=1))
    hip = apply_pose(Rp, tp, geo_leg['hip_in_pelvis'])
    # The knee centre is the knee joint's child frame origin, placed by the tibia fit. (The scaled models give the femur
    # side no fixed knee location: the knee translates with the angle through spline functions.)
    knee = apply_pose(Rt, tt, geo_leg['knee_in_tibia'])
    ankle = apply_pose(Rt, tt, geo_leg['ankle_in_tibia'])
    knee_via_femur = knee_from_femur(geo_leg, Rf, tf, Rt)
    axis = np.einsum('nij,j->ni', Rf, geo_leg['knee_axis_in_femur'])
    return {'hip': hip, 'knee': knee, 'ankle': ankle, 'knee_axis_raw': axis,
            'knee_route_gap_m': np.linalg.norm(knee - knee_via_femur, axis=1),
            'fit_rms_m': {'pelvis': rms_p, f'femur_{s}': rms_f, f'tibia_{s}': rms_t},
            'fit_markers': {'pelvis': pel_names, f'femur_{s}': fem_names, f'tibia_{s}': tib_names}}


def geometry_hold(residuals, axis_angle):
    """Per-frame hold code (int8): 1 residual over 20 mm in any given fit, 2 knee-axis angle over 45 degrees, 3 both, 0 neither.
    residuals: list of rms arrays (m); axis_angle: radians or None when the lateral knee marker is absent (that check is then
    not applied, and the ledger says so). NaN values never count as exceeding (those frames are already missing)."""
    code = np.zeros(len(residuals[0]), np.int8)
    with np.errstate(invalid='ignore'):
        for r in residuals:
            code |= np.where(np.asarray(r) > HOLD_RESIDUAL_M, HOLD_RESIDUAL, 0).astype(np.int8)
        if axis_angle is not None:
            code |= np.where(np.asarray(axis_angle) > HOLD_AXIS_RAD, HOLD_AXIS, 0).astype(np.int8)
    return code


def knee_axis_marker_angle(axis_to_right, knee, hip, lateral_marker, side):
    """Diagnostic: angle (radians) between the model's knee axis (to the person's right) and the horizontal-free direction
    from the knee centre to the lateral knee marker, projected perpendicular to the thigh. For the left leg the lateral
    marker lies to the person's left, so the expected direction is its negative. NaN where undefined."""
    thigh = unit(np.asarray(knee, float) - np.asarray(hip, float))
    d = np.asarray(lateral_marker, float) - np.asarray(knee, float)
    d = d - np.sum(d * thigh, axis=-1, keepdims=True) * thigh
    a = np.asarray(axis_to_right, float)
    a = a - np.sum(a * thigh, axis=-1, keepdims=True) * thigh
    if side == 'left':
        d = -d
    cosang = np.sum(unit(a) * unit(d), axis=-1)
    return np.arccos(np.clip(cosang, -1, 1))


# ------------------------------------------------------------------------------------------------ body weight
def weight_kg_from_subject_info(info):
    """Declared body mass in kilograms from the RB01 subject_info export. The unit must be recorded as kg; anything else
    is refused (the model mass is never a substitute)."""
    names, units, values = info.get('variable_names') or [], info.get('variable_units') or [], info.get('values') or {}
    if 'Weight' not in names or 'Weight' not in values:
        raise RecordingExcluded('subject info has no Weight')
    unit_ = units[names.index('Weight')] if names.index('Weight') < len(units) else ''
    if str(unit_).strip().lower() != 'kg':
        raise RecordingExcluded(f'Weight unit is {unit_!r}, not kg')
    w = float(values['Weight'])
    if not (math.isfinite(w) and 20.0 <= w <= 300.0):
        raise RecordingExcluded(f'Weight {w} kg is outside 20-300 kg')
    return w


def body_weight_newton(weight_kg):
    return weight_kg * G


# ------------------------------------------------------------------------------------------------ plates: ownership
def _runs(mask):
    edges = np.diff(np.r_[0, np.asarray(mask, np.int8), 0])
    return np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)


def contact_runs(vy, contact_n=CONTACT_N, edge_n=EDGE_N, bridge=BRIDGE_SAMPLES):
    """[a, b) of every run of vertical force above edge_n, dips of at most ``bridge`` samples bridged, that holds a sample
    above contact_n. NaN counts as unloaded."""
    v = np.nan_to_num(np.asarray(vy, float), nan=0.0)
    starts, stops = _runs(v > edge_n)
    if len(starts) > 1:
        keep = np.r_[True, starts[1:] - stops[:-1] > bridge]
        starts, stops = starts[keep], np.r_[stops[np.flatnonzero(keep)[1:] - 1], stops[-1]]
    core = np.r_[0, np.cumsum(v > contact_n)]
    return [(int(a), int(b)) for a, b in zip(starts, stops) if core[b] > core[a]]


def left_fraction(cop, foot_right, foot_left, vy, vote_n=VOTE_N):
    """(fraction of voting samples where the left foot is nearer the plate CoP, number of voting samples). A voting
    sample has vertical force above vote_n and every coordinate finite; distances are 3-D."""
    d_r = np.linalg.norm(np.asarray(cop, float) - foot_right, axis=1)
    d_l = np.linalg.norm(np.asarray(cop, float) - foot_left, axis=1)
    vote = (np.nan_to_num(np.asarray(vy, float)) > vote_n) & np.isfinite(d_r) & np.isfinite(d_l)
    n = int(vote.sum())
    return (float(np.mean(d_l[vote] < d_r[vote])) if n else float('nan')), n


def contact_owner(frac_left, n_votes, stance_right, stance_left):
    """(foot or None, rule). The marker vote where any sample voted; a fraction strictly inside the ambiguous band gives
    the contact to neither foot. With no voting sample the foot in stance over more of the contact's loaded samples owns
    it (events fallback); a tie or no events gives neither."""
    if n_votes:
        if AMBIGUOUS[0] < frac_left < AMBIGUOUS[1]:
            return None, 'ambiguous'
        return ('left' if frac_left > 0.5 else 'right'), 'markers'
    if stance_left != stance_right:
        return ('left' if stance_left > stance_right else 'right'), 'events'
    return None, 'unassigned'


def event_samples(gc, t):
    """Sample indices on clock ``t`` of heel strikes and toe offs from a gait-cycle table (dict with Header, HeelStrike,
    ToeOff in percent of cycle): an event is where the percentage drops by more than 50. Events whose time is farther
    than half a sample from the grid are dropped and counted. Returns (heel_strikes, toe_offs, dropped)."""
    out, dropped = [], 0
    if gc is None:
        return np.zeros(0, int), np.zeros(0, int), 0
    h = np.asarray(gc['Header'], float)
    half = 0.5 * float(np.median(np.diff(t))) if len(t) > 1 else 0.0
    for col in ('HeelStrike', 'ToeOff'):
        x = np.asarray(gc[col], float)
        times = h[np.flatnonzero(np.diff(x) < -EVENT_DROP) + 1]
        idx = np.searchsorted(t, times)
        idx = np.clip(idx, 1, len(t) - 1) if len(t) > 1 else idx
        nearest = np.where(np.abs(t[idx - 1] - times) <= np.abs(t[idx] - times), idx - 1, idx) if len(t) > 1 else idx
        ok = np.abs(t[nearest] - times) <= half + 1e-9 if len(t) else np.zeros(len(times), bool)
        dropped += int((~ok).sum())
        out.append(np.unique(nearest[ok]))
    return out[0], out[1], dropped


def stance_mask(n, heel_strikes, toe_offs):
    """Heel strike to the next toe off. Before a first toe off that precedes every heel strike, and after a heel strike
    that no toe off follows, the foot stands."""
    hs, to = np.sort(np.asarray(heel_strikes, int)), np.sort(np.asarray(toe_offs, int))
    m = np.zeros(n, bool)
    if len(to) and (not len(hs) or to[0] < hs[0]):
        m[:max(0, min(int(to[0]), n))] = True
    for h in hs:
        k = np.searchsorted(to, h, side='right')
        end = int(to[k]) if k < len(to) else n
        m[max(0, int(h)):max(0, min(end, n))] = True
    return m


def assign_plates(plates, foot_right, foot_left, stance_right, stance_left):
    """Ownership of every plate contact by marker geometry (overground).

    plates: list of dicts with name, vy (n), cop (n, 3). foot_*: heel-toe midpoints (n, 3). stance_*: bool (n) or None
    when the leg has no gait events. Returns own = {'right': (n, P) bool, 'left': ...}, unowned (n, P) bool and the list of
    contact records (plate, a, b, owner, rule, left_fraction, votes, peak_n)."""
    n = len(foot_right)
    P = len(plates)
    own = {leg: np.zeros((n, P), bool) for leg in LEGS}
    unowned = np.zeros((n, P), bool)
    contacts = []
    stance = {'right': stance_right, 'left': stance_left}
    for p, plate in enumerate(plates):
        vy = np.asarray(plate['vy'], float)
        for a, b in contact_runs(vy):
            sl = slice(a, b)
            frac, votes = left_fraction(plate['cop'][sl], foot_right[sl], foot_left[sl], vy[sl])
            core = np.nan_to_num(vy[sl]) > CONTACT_N
            overlap = {leg: int((stance[leg][sl] & core).sum()) if stance[leg] is not None else 0 for leg in LEGS}
            who, rule = contact_owner(frac, votes, overlap['right'], overlap['left'])
            (own[who] if who else unowned)[sl, p] = True
            contacts.append(dict(plate=plate['name'], a=a, b=b, owner=who or '', rule=rule, left_fraction=frac,
                                 votes=votes, peak_n=float(np.nanmax(vy[sl]))))
    return own, unowned, contacts


def treadmill_ownership(plate_names, n):
    """Named treadmill plates: Treadmill_R is the right foot's, Treadmill_L the left foot's, for every sample. A foot
    whose named plate is absent owns nothing."""
    own = {leg: np.zeros((n, len(plate_names)), bool) for leg in LEGS}
    for p, name in enumerate(plate_names):
        if name == 'Treadmill_R':
            own['right'][:, p] = True
        elif name == 'Treadmill_L':
            own['left'][:, p] = True
    return own, np.zeros((n, len(plate_names)), bool)


# ------------------------------------------------------------------------------------------------ plates: forces
def contact_zsign(owned_any, fwd):
    """Sign of the lab Z axis along the walking direction for each loaded contact of a foot.

    owned_any: bool (n), true where the foot owns a loaded plate. fwd: pelvis forward (n, 3). The heading of a contact is
    the normalised mean horizontal heading over its run of loaded samples; the sign is that of its Z component, and it is
    defined only if the heading lies within 45 degrees of the Z axis. Returns (sign (n) with NaN elsewhere, report)."""
    n = len(owned_any)
    sign = np.full(n, np.nan)
    runs = gated = 0
    for a, b in zip(*_runs(owned_any)):
        seg = fwd[a:b]
        ok = np.isfinite(seg).all(axis=1)
        if not ok.any():
            continue
        runs += 1
        m = unit(seg[ok].mean(axis=0, keepdims=True))[0]
        if np.isfinite(m).all() and abs(m[2]) >= Z_GATE:
            sign[a:b] = 1.0 if m[2] > 0 else -1.0
        else:
            gated += 1
    return sign, {'contacts': runs, 'failed_45_degree_gate': gated}


def foot_forces(own_leg, plates, bw_newton, zsign, leg):
    """Force and lab CoP of one foot summed over the plates it owns.

    own_leg (n, P) bool. plates: list of dicts with vx, vy, vz (N) and cop (n, 3) (m). Signs: vertical = sum vy (up);
    anterior = zsign x sum vz (the walking direction on the lab Z axis, signed by the pelvis heading); lateral outward
    = -zsign x sum vx for the right leg and +zsign x sum vx for the left leg (the person's right is the forward direction
    crossed with up, which on the Z axis is -zsign x X). Forces are in body weights and are NaN only where no plate
    value exists in the recording (all plates NaN), never zero-filled; anterior and lateral are NaN where zsign is NaN
    and the foot is loaded. The lab CoP is the vertical-force-weighted mean over owned loaded plates."""
    n = own_leg.shape[0]
    P = len(plates)
    vx = np.stack([np.nan_to_num(plates[p]['vx']) for p in range(P)], axis=1) if P else np.zeros((n, 0))
    vy = np.stack([np.nan_to_num(plates[p]['vy']) for p in range(P)], axis=1) if P else np.zeros((n, 0))
    vz = np.stack([np.nan_to_num(plates[p]['vz']) for p in range(P)], axis=1) if P else np.zeros((n, 0))
    cop = np.stack([plates[p]['cop'] for p in range(P)], axis=1) if P else np.zeros((n, 0, 3))
    all_nan = np.stack([np.isnan(plates[p]['vy']) for p in range(P)], axis=1).all(axis=1) if P else np.ones(n, bool)
    fy = np.where(own_leg, vy, 0.0)
    fz = np.where(own_leg, vz, 0.0).sum(axis=1)
    fx = np.where(own_leg, vx, 0.0).sum(axis=1)
    vert = fy.sum(axis=1)
    w = np.where(own_leg & (vy > 0) & np.isfinite(cop).all(axis=2), vy, 0.0)
    ws = w.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        point = np.where(ws[:, None] > 0, np.einsum('np,npk->nk', w, np.nan_to_num(cop)) / ws[:, None], np.nan)
    loaded = vert > EDGE_N
    sgn = 1.0 if leg == 'left' else -1.0
    ant = zsign * fz / bw_newton
    lat = sgn * zsign * fx / bw_newton
    ant[~loaded & np.isnan(zsign)] = np.where(all_nan, np.nan, 0.0)[~loaded & np.isnan(zsign)]  # unloaded foot: no force
    lat[~loaded & np.isnan(zsign)] = np.where(all_nan, np.nan, 0.0)[~loaded & np.isnan(zsign)]
    vgrf = vert / bw_newton
    vgrf[all_nan] = np.nan
    ant[all_nan], lat[all_nan] = np.nan, np.nan
    return {'vertical_BW': vgrf, 'anterior_BW': ant, 'lateral_BW': lat, 'cop_lab': point, 'loaded': loaded}


def interp_to_clock(t_new, t_src, y):
    """Linear interpolation onto a new clock; NaN outside the source span and where either neighbour is nonfinite.
    A source sample exactly on the new clock is returned unchanged."""
    t_new, t_src, y = np.asarray(t_new, float), np.asarray(t_src, float), np.asarray(y, float)
    out = np.full(len(t_new), np.nan)
    inside = (t_new >= t_src[0]) & (t_new <= t_src[-1])
    j = np.clip(np.searchsorted(t_src, t_new[inside], side='right') - 1, 0, len(t_src) - 2)
    t0, t1, y0, y1 = t_src[j], t_src[j + 1], y[j], y[j + 1]
    with np.errstate(invalid='ignore', divide='ignore'):
        w = (t_new[inside] - t0) / (t1 - t0)
        val = y0 + w * (y1 - y0)
    val = np.where(t_new[inside] == t0, y0, val)
    out[inside] = val
    return out


def interp_cop(t_new, t_src, cop_xyz, vy):
    """CoP onto a new clock only where both bracketing source samples carry load (vertical force above 1 N) and finite
    coordinates; elsewhere NaN (a CoP interpolated through an unloaded plate is not a measurement)."""
    n = len(t_new)
    out = np.full((n, 3), np.nan)
    loaded = np.nan_to_num(np.asarray(vy, float)) > EDGE_N
    ok_src = loaded & np.isfinite(cop_xyz).all(axis=1)
    inside = (t_new >= t_src[0]) & (t_new <= t_src[-1])
    j = np.clip(np.searchsorted(t_src, t_new, side='right') - 1, 0, len(t_src) - 2)
    on_grid = inside & (t_src[j] == t_new)
    both = inside & ok_src[j] & (ok_src[j + 1] | on_grid)
    for k in range(3):
        v = interp_to_clock(t_new, t_src, np.where(ok_src, cop_xyz[:, k], np.nan))
        out[both, k] = v[both]
    return out


# ------------------------------------------------------------------------------------------------ one recording
def _marker_array(table, name):
    cols = [f'{name}_{a}' for a in 'xyz']
    if not all(c in table for c in cols):
        return None
    return np.stack([np.asarray(table[c], float) for c in cols], axis=1) / 1000.0     # millimetres to metres


def fp_plates(fp):
    """Plate prefixes with all six channels (vx, vy, vz, px, py, pz), in table order."""
    out = []
    for c in fp:
        if c.endswith('_vy'):
            prefix = c[:-3]
            if all(f'{prefix}_{k}' in fp for k in ('vx', 'vy', 'vz', 'px', 'py', 'pz')):
                out.append(prefix)
    return out


def _quant(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not x.size:
        return None
    return {'n': int(x.size), 'median': float(np.median(x)), 'p95': float(np.percentile(x, 95)), 'max': float(x.max())}


def process_recording(markers, fp, gc_left, gc_right, idt, geo, weight_kg, mode):
    """The merged pass for one recording. Inputs are dicts of float arrays (the named columns of each source table; gc and
    id may be None), ``geo`` = {'r': model_geometry(text,'r'), 'l': model_geometry(text,'l')}, weight_kg the declared mass,
    mode one of levelground, ramp, stair, treadmill. Returns (columns, ledger): columns is a dict of equal-length arrays on
    the marker clock (time_s first), ledger a JSON-ready dict. Raises RecordingExcluded with the reason."""
    t = np.asarray(markers.get('Header', []), float)
    if t.size < 3 or not np.isfinite(t).all() or not (np.diff(t) > 0).all():
        raise RecordingExcluded('invalid_marker_clock')
    n = len(t)
    needed = list(PELVIS_MARKERS) + [f'{S}_{m}' for S in 'RL' for m in FOOT_MARKERS]
    P = {}
    for name in set(needed) | {f'{S}_{m}' for S in 'RL' for m in THIGH_CLUSTER + SHANK_CLUSTER}:
        a = _marker_array(markers, name)
        if a is not None:
            P[name] = a
    missing = sorted(set(needed) - set(P))
    if missing:
        raise RecordingExcluded(f'missing_markers: {",".join(missing)}')
    width = np.nanmedian(np.linalg.norm(P['R_ASIS'] - P['L_ASIS'], axis=1)) if np.isfinite(P['R_ASIS']).any() else np.nan
    if not (0.10 <= width <= 0.40):
        raise RecordingExcluded(f'marker_scale: median ASIS width {width} m is not 0.10-0.40 m (units?)')
    asis_mid, psis_mid = (P['L_ASIS'] + P['R_ASIS']) / 2, (P['L_PSIS'] + P['R_PSIS']) / 2
    fwd_pelvis = pelvis_forward(asis_mid, psis_mid)
    right_ref = np.cross(fwd_pelvis, UP)
    pelvis = pelvis_angle(asis_mid, psis_mid)
    cols = {'time_s': t, 'pelvis_sagittal_angle_rad': pelvis, 'pelvis_forward_lab_x': fwd_pelvis[:, 0],
            'pelvis_forward_lab_z': fwd_pelvis[:, 2]}
    ledger = {'n_samples': n, 'mode': mode, 'weight_kg': weight_kg, 'body_weight_N': body_weight_newton(weight_kg),
              'median_dt_s': float(np.median(np.diff(t))), 'fit': {}, 'legs': {}}
    legs = {}
    for leg in LEGS:
        s, S = SIDE[leg].lower(), SIDE[leg]
        c = leg_centres(geo[s], geo[s], P, s)
        axis = knee_axis_to_right(c['knee_axis_raw'], right_ref)
        fwd_leg = plane_forward(axis)
        seg = segment_angles(fwd_leg, c['hip'], c['knee'], c['ankle'], P[f'{S}_Heel'], P[f'{S}_Toe_Tip'])
        seg['pelvis'] = pelvis
        ang = knee_axis_marker_angle(axis, c['knee'], c['hip'], P[f'{S}_Knee_Lat'], leg) if f'{S}_Knee_Lat' in P else None
        hold = geometry_hold(list(c['fit_rms_m'].values()), ang)
        held = hold > 0
        seg = {k: np.where(held, np.nan, v) for k, v in seg.items() if k != 'pelvis'} | {'pelvis': pelvis}
        ja = joint_angles(pelvis, seg['thigh'], seg['shank'], seg['foot'])
        legs[leg] = dict(c=c, fwd=fwd_leg, seg=seg, ja=ja, held=held)
        ledger['fit'][leg] = {'markers': c['fit_markers'], 'rms_mm': {k: _quant(v * 1000) for k, v in c['fit_rms_m'].items()},
                              'knee_route_gap_mm': _quant(c['knee_route_gap_m'] * 1000),
                              'geometry_hold': {'rule': {'residual_mm': HOLD_RESIDUAL_M * 1000, 'axis_deg': 45.0,
                                                         'axis_check_applied': ang is not None},
                                                'held_frames': int(held.sum()), 'by_residual': int((hold & HOLD_RESIDUAL > 0).sum()),
                                                'by_axis': int((hold & HOLD_AXIS > 0).sum()),
                                                'both': int((hold == 3).sum()), 'n_frames': n}}
        if ang is not None:
            ledger['fit'][leg]['knee_axis_vs_lateral_marker_deg'] = _quant(np.degrees(ang))
        cols[f'geometry_hold_{leg}'] = hold
        for k in ('thigh', 'shank', 'foot'):
            cols[f'{k}_sagittal_angle_{leg}_rad'] = seg[k]
        for k, name in (('hip', 'hip_flexion'), ('knee', 'knee_flexion'), ('ankle', 'ankle_dorsiflexion')):
            cols[f'{name}_angle_{leg}_rad'] = ja[k]
            cols[f'{name}_velocity_{leg}_rad_s'] = np.where(held, np.nan, central_derivative(ja[k], t))
    # ---- plates
    ledger['plates'] = {'channels': [], 'unavailable_reason': None, 'contacts': [], 'assignment': {}}
    prefixes = fp_plates(fp) if fp else []
    ft = np.asarray(fp.get('Header', []), float) if fp else np.zeros(0)
    fp_ok = bool(prefixes) and ft.size > 2 and np.isfinite(ft).all() and (np.diff(ft) > 0).all()
    if not fp_ok:
        ledger['plates']['unavailable_reason'] = 'no_plate_channels' if not prefixes else 'invalid_fp_clock'
        prefixes = []
    plates = []
    for p in prefixes:
        cop_src = np.stack([np.asarray(fp[f'{p}_{k}'], float) for k in ('px', 'py', 'pz')], axis=1)
        vy_src = np.asarray(fp[f'{p}_vy'], float)
        plates.append({'name': p,
                       'vx': interp_to_clock(t, ft, fp[f'{p}_vx']), 'vy': interp_to_clock(t, ft, vy_src),
                       'vz': interp_to_clock(t, ft, fp[f'{p}_vz']), 'cop': interp_cop(t, ft, cop_src, vy_src)})
    ledger['plates']['channels'] = prefixes
    ev, stance = {}, {}
    for leg, gc in (('right', gc_right), ('left', gc_left)):
        hs, to, dropped = event_samples(gc, t)
        ev[leg] = {'heel_strikes': int(len(hs)), 'toe_offs': int(len(to)), 'off_grid_dropped': dropped}
        stance[leg] = stance_mask(n, hs, to) if (len(hs) or len(to)) else None
    ledger['events'] = ev
    if mode == 'treadmill':
        own, unowned = treadmill_ownership(prefixes, n)
        ledger['plates']['assignment']['rule'] = 'named_treadmill_plates'
    else:
        foot = {leg: (P[f'{SIDE[leg]}_Heel'] + P[f'{SIDE[leg]}_Toe_Tip']) / 2.0 for leg in LEGS}
        own, unowned, contacts = assign_plates(plates, foot['right'], foot['left'], stance['right'], stance['left'])
        ledger['plates']['contacts'] = contacts
        ledger['plates']['assignment']['rule'] = 'marker_vote_ambiguous_band_events_fallback'
        ledger['plates']['assignment']['by_rule'] = {r: sum(1 for x in contacts if x['rule'] == r)
                                                     for r in ('markers', 'events', 'ambiguous', 'unassigned')}
    bw = body_weight_newton(weight_kg)
    for leg in LEGS:
        S = SIDE[leg]
        L = legs[leg]
        f = foot_forces(own[leg], plates, bw, np.full(n, np.nan), leg) if plates else None
        if f is None:
            nan = np.full(n, np.nan)
            for k in ('grf_vertical', 'grf_anterior', 'grf_lateral'):
                cols[f'{k}_{leg}_BW'] = nan
            for k in ('anterior', 'vertical', 'lateral'):
                cols[f'cop_{k}_{leg}_m'] = nan
            cols[f'plate_loaded_{leg}'] = np.zeros(n, bool)
            ledger['legs'][leg] = {'no_plate_channels': True}
            continue
        zsign, zrep = contact_zsign(f['loaded'], fwd_pelvis)
        f = foot_forces(own[leg], plates, bw, zsign, leg)
        cop_ff = foot_frame_point(f['cop_lab'], L['c']['ankle'], L['fwd'], L['seg']['foot'], leg)
        cop_m, reasons = mask_cop(cop_ff, f['vertical_BW'])
        reasons['geometry_hold'] = int((L['held'] & np.isfinite(cop_m['anterior'])).sum())
        for k in cop_m:
            cop_m[k] = np.where(L['held'], np.nan, cop_m[k])
        cols[f'grf_vertical_{leg}_BW'] = f['vertical_BW']
        cols[f'grf_anterior_{leg}_BW'] = f['anterior_BW']
        cols[f'grf_lateral_{leg}_BW'] = f['lateral_BW']
        for k in ('anterior', 'vertical', 'lateral'):
            cols[f'cop_{k}_{leg}_m'] = cop_m[k]
        cols[f'plate_loaded_{leg}'] = f['loaded']
        flat = f['loaded'] & (np.abs(L['seg']['foot']) < 0.0873) & np.isfinite(f['cop_lab'][:, 1]) & np.isfinite(L['c']['ankle'][:, 1])
        heel_h = (P[f'{S}_Heel'][:, 1] - f['cop_lab'][:, 1])[flat]
        ankle_marker_h = (P[f'{S}_Ankle_Lat'][:, 1] - f['cop_lab'][:, 1])[flat]
        ledger['legs'][leg] = {'z_gate': zrep, 'heel_marker_above_plate_flat_foot_m': _quant(heel_h),
                               'ankle_lat_marker_above_plate_flat_foot_m': _quant(ankle_marker_h),
                               'model_ankle_in_tibia_m': [float(v) for v in geo[SIDE[leg].lower()]['ankle_in_tibia']], 'cop_masked': reasons, 'loaded_samples': int(f['loaded'].sum()),
                               'ankle_height_above_plate_flat_foot_m': _quant((L['c']['ankle'][:, 1] - f['cop_lab'][:, 1])[flat]),
                               'simultaneous_owned_plates_samples': int((np.where(own[leg], np.array([np.nan_to_num(p['vy']) for p in plates]).T > EDGE_N, False).sum(axis=1) > 1).sum()),
                               'stance_from_events': stance[leg] is not None}
    for leg in LEGS:
        cols[f'stance_{leg}'] = stance[leg] if stance[leg] is not None else np.zeros(n, bool)
    # ---- inverse-dynamics moments (Nm / Weight in kg; the standard's signs: knee flexor = -knee_angle moment)
    ledger['moments'] = {'available': False}
    it = np.asarray(idt.get('Header', []), float) if idt else np.zeros(0)
    if idt and it.size > 2 and np.isfinite(it).all() and (np.diff(it) > 0).all():
        ledger['moments'] = {'available': True, 'unit': 'Nm/kg (id moment / declared Weight in kg)'}
        for leg in LEGS:
            s = SIDE[leg].lower()
            for name, src, sign in (('hip_flexion', f'hip_flexion_{s}_moment', 1.0), ('knee_flexion', f'knee_angle_{s}_moment', -1.0),
                                    ('ankle_dorsiflexion', f'ankle_angle_{s}_moment', 1.0)):
                cols[f'{name}_moment_{leg}_Nm_kg'] = (sign * interp_to_clock(t, it, idt[src]) / weight_kg) if src in idt else np.full(n, np.nan)
    else:
        for leg in LEGS:
            for name in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion'):
                cols[f'{name}_moment_{leg}_Nm_kg'] = np.full(n, np.nan)
    ledger['finite_fraction'] = {k: float(np.isfinite(v).mean()) for k, v in cols.items() if v.dtype.kind == 'f'}
    return cols, ledger
