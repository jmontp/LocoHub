"""Georgia Tech 2023 conventions (GT23-C06): segment angles, joint angles, foot-frame pressure point, force frame.

Pure functions, no file access. The standard is docs/reference/index.md (decided 2026-11-23):

* Lab frame of the source: +Y up, markers in mm. The person's right is  forward x up, so the forward direction is
  up x (right ASIS - left ASIS), measured at every sample (plan default G4).
* Segment angles are counterclockwise-positive in the (forward, up) plane. Thigh and shank are measured from straight
  down (distal end forward positive), foot (heel to toe) and pelvis (PSIS to ASIS) from forward horizontal.
* Joint angles are differences: hip = thigh - pelvis, knee = thigh - shank, ankle = foot - shank. There is no other zero.
* Thigh and shank long axes come from the authors' scaled model (Transforms_Euler: body y axis points to the proximal
  joint). The Euler order that reproduces the authors' orientations is intrinsic Y-Z-X with the file's columns taken in
  file order (the column names are not the axis names); R = Ry(a1) Rz(a2) Rx(a3) maps body axes to the lab.
* Pressure point in the foot's own frame: origin 100 mm forward of the ankle centre along heel to toe, anterior along
  heel to toe, up perpendicular to it (the vertical with its heel-to-toe part removed, no roll), sideways outward.
* Forward and sideways force are filled only where a heading is allowed (forward walking); lab axes elsewhere.

Geometry of the authors' scaled model (talus origin, ankle centre, hip centre) is re-implemented here from the .osim
text and checked on GT23 data; the survey values (talus origin 0.04877 m anterior of the calcaneus origin, ankle
centre about 35.7 mm below the ankle-marker midpoint) are claims of the energy-shaping-ML survey
(docs/maintainers/handoffs/ESML-crosswalk.json) and are only compared with, never imported.
"""
import re

import numpy as np

UP = np.array([0.0, 1.0, 0.0])
FOOT_ORIGIN_M = 0.1
STANCE_N = 20.0
RATE_HZ = 200.0


# ------------------------------------------------------------------------------------------------ vectors
def unit(v):
    """Row-wise unit vectors; a zero or nonfinite row becomes NaN."""
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    with np.errstate(invalid='ignore', divide='ignore'):
        out = v / n
    out[(n[..., 0] == 0)] = np.nan
    return out


def heading(lasi, rasi):
    """Forward horizontal unit vectors, up x (right ASIS - left ASIS), one per sample."""
    return unit(np.cross(UP, np.asarray(rasi, float) - np.asarray(lasi, float)))


def right_axis(fwd):
    """The person's right, forward x up (the standard's +z)."""
    return np.cross(np.asarray(fwd, float), UP)


def sag(v, fwd):
    """Forward and up components of lab vectors (n, 3) for a forward direction (n, 3)."""
    v = np.asarray(v, float)
    return np.stack([np.sum(v * fwd, axis=-1), v @ UP], axis=-1)


def angle_from_down(v2):
    """Counterclockwise angle of a proximal-to-distal (forward, up) vector from straight down (distal forward > 0)."""
    return np.arctan2(v2[..., 0], -v2[..., 1])


def angle_from_forward(v2):
    """Counterclockwise angle of a (forward, up) vector from forward horizontal (toes up > 0)."""
    return np.arctan2(v2[..., 1], v2[..., 0])


def wrap(a):
    return (np.asarray(a, float) + np.pi) % (2 * np.pi) - np.pi


# ------------------------------------------------------------------------------------------------ rotations
def _rx(a):
    c, s, o, i = np.cos(a), np.sin(a), np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([i, o, o], -1), np.stack([o, c, -s], -1), np.stack([o, s, c], -1)], -2)


def _ry(a):
    c, s, o, i = np.cos(a), np.sin(a), np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, o, s], -1), np.stack([o, i, o], -1), np.stack([-s, o, c], -1)], -2)


def _rz(a):
    c, s, o, i = np.cos(a), np.sin(a), np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, -s, o], -1), np.stack([s, c, o], -1), np.stack([o, o, i], -1)], -2)


def euler_yzx(a1, a2, a3):
    """Body-to-lab rotation matrices (n, 3, 3) from the Transforms_Euler columns in file order (radians)."""
    return _ry(np.asarray(a1, float)) @ _rz(np.asarray(a2, float)) @ _rx(np.asarray(a3, float))


# ------------------------------------------------------------------------------------------------ segment and joint angles
def segment_angle_set(fwd, asis_mid, psis_mid, thigh_down, shank_down, heel, toe):
    """Segment angles (radians) in the plane of ``fwd``.

    thigh_down, shank_down: lab vectors pointing proximal to distal (n, 3). heel, toe: lab points (n, 3).
    """
    return {'pelvis': angle_from_forward(sag(asis_mid - psis_mid, fwd)),
            'thigh': angle_from_down(sag(thigh_down, fwd)),
            'shank': angle_from_down(sag(shank_down, fwd)),
            'foot': angle_from_forward(sag(toe - heel, fwd))}


def joint_angles(seg):
    """The standard's zero: joint angles are differences of segment angles."""
    return {'hip': seg['thigh'] - seg['pelvis'], 'knee': seg['thigh'] - seg['shank'], 'ankle': seg['foot'] - seg['shank']}


def composition_error(pelvis, thigh, shank, foot, hip, knee, ankle):
    """Largest |thigh - pelvis - hip|, |thigh - knee - shank|, |shank + ankle - foot| over samples where all are finite."""
    errs = [0.0]
    for a, b, c in ((thigh - pelvis, hip, None), (thigh - knee, shank, None), (shank + ankle, foot, None)):
        d = np.abs(a - b)
        d = d[np.isfinite(d)]
        if d.size:
            errs.append(float(d.max()))
    return max(errs)


def central_derivative(x, dt=1.0 / RATE_HZ):
    """(x[i+1] - x[i-1]) / (2 dt) with the difference wrapped to (-pi, pi]; NaN where a neighbour is not finite.
    No smoothing. Angles are in radians, so the result is rad/s."""
    x = np.asarray(x, float)
    out = np.full(x.shape, np.nan)
    if len(x) > 2:
        out[1:-1] = wrap(x[2:] - x[:-2]) / (2.0 * dt)
    return out


# ------------------------------------------------------------------------------------------------ foot frame
def foot_axes(heel, toe):
    """Foot frame (n, 3) unit axes: anterior along heel to toe, up perpendicular to it (no roll), right = anterior x up."""
    e_f = unit(np.asarray(toe, float) - np.asarray(heel, float))
    up = UP - np.sum(UP * e_f, axis=-1, keepdims=True) * e_f
    e_u = unit(up)
    return e_f, e_u, np.cross(e_f, e_u)


def foot_frame_point(point, ankle, heel, toe, leg):
    """Lab points (n, 3) in the foot frame: (anterior, vertical, lateral) metres, origin 100 mm forward of ankle."""
    e_f, e_u, e_r = foot_axes(heel, toe)
    q = np.asarray(point, float) - np.asarray(ankle, float)
    lateral = np.sum(q * e_r, axis=-1)
    return {'anterior': np.sum(q * e_f, axis=-1) - FOOT_ORIGIN_M, 'vertical': np.sum(q * e_u, axis=-1),
            'lateral': lateral if leg == 'R' else -lateral}


def plate_point(cop_x, cop_y, cop_z, vertical_force):
    """Lab pressure point (n, 3) from the source plate columns. The height is the source's own COPY_Vertical (a raised
    plate such as a stair or curb has a nonzero surface height), never assumed 0; a sample whose height is not finite,
    or whose vertical force is missing or below 20 N, is NaN."""
    p = np.stack([np.asarray(cop_x, float), np.asarray(cop_y, float), np.asarray(cop_z, float)], axis=1)
    f = np.asarray(vertical_force, float)
    p[~(np.isfinite(f) & (f >= STANCE_N))] = np.nan
    return p


def heel_above_plate(heel, plate_height):
    """Median height of the heel marker above the recorded plate surface over samples where both are finite (None if none)."""
    ok = np.isfinite(np.asarray(heel, float)) & np.isfinite(np.asarray(plate_height, float))
    return float(np.median(np.asarray(heel, float)[ok] - np.asarray(plate_height, float)[ok])) if ok.any() else None


def foot_frame_force(force, heel, toe):
    """Lab force (n, 3) as (anterior, vertical) foot-frame components (for the quasi-static ankle moment)."""
    e_f, e_u, _ = foot_axes(heel, toe)
    force = np.asarray(force, float)
    return np.sum(force * e_f, axis=-1), np.sum(force * e_u, axis=-1)


def ankle_moment_quasi_static(anterior, vertical, force_anterior, force_vertical):
    """Internal ankle moment (dorsiflexor positive) about the ankle centre from the ground force at the pressure point.

    The pressure point is given relative to the foot-frame origin, so the lever from the ankle is (anterior + 0.1,
    vertical). External torque tau = rx*Fy - ry*Fx (counterclockwise positive); the internal moment on the foot is -tau.
    """
    rx = np.asarray(anterior, float) + FOOT_ORIGIN_M
    return -(rx * force_vertical - np.asarray(vertical, float) * force_anterior)


# ------------------------------------------------------------------------------------------------ headings by span
def merge_spans(spans, n):
    """Merge inclusive [start, end] sample spans (overlapping or touching) clipped to [0, n-1]."""
    out = []
    for a, b in sorted((max(0, int(a)), min(n - 1, int(b))) for a, b in spans if b >= a):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def heading_by_span(fwd, spans):
    """Forward direction held fixed within each span: the normalised mean of the per-sample horizontal headings
    over the span's finite samples. Samples outside every span get NaN. Returns (heading (n, 3), report per span)."""
    n = len(fwd)
    out = np.full((n, 3), np.nan)
    report = []
    for a, b in spans:
        seg = fwd[a:b + 1]
        ok = np.isfinite(seg).all(axis=1)
        if not ok.any():
            report.append({'start': int(a), 'end': int(b), 'finite_samples': 0, 'max_dev_deg': None})
            continue
        m = unit(seg[ok].mean(axis=0))
        out[a:b + 1] = m
        dev = np.degrees(np.arccos(np.clip(seg[ok] @ m, -1, 1)))
        report.append({'start': int(a), 'end': int(b), 'finite_samples': int(ok.sum()), 'max_dev_deg': float(dev.max()),
                       'heading_deg_about_up': float(np.degrees(np.arctan2(-m[2], m[0])))})
    return out, report


def fill_heading_by_contact(held, fwd, loaded):
    """Loaded samples (own plate at or above 20 N) that no stride or window span covers get the heading of their own
    contact: the normalised mean horizontal heading over that contiguous loaded run. Samples not loaded stay as they
    are. Returns (new heading (n, 3), number of contacts filled, loaded samples filled, loaded samples left missing)."""
    out = held.copy()
    loaded = np.asarray(loaded, bool)
    edges = np.flatnonzero(np.diff(np.concatenate(([0], loaded.astype(int), [0]))))
    runs_filled, samples = 0, 0
    for a, b in zip(edges[::2], edges[1::2]):
        gap = ~np.isfinite(out[a:b]).all(axis=1)
        if not gap.any():
            continue
        seg = fwd[a:b]
        ok = np.isfinite(seg).all(axis=1)
        if not ok.any():
            continue
        out[a:b][gap] = unit(seg[ok].mean(axis=0))
        runs_filled += 1
        samples += int(gap.sum())
    left = int((loaded & ~np.isfinite(out).all(axis=1)).sum())
    return out, runs_filled, samples, left


def force_forward_sideways(force, fwd, leg):
    """Forward and sideways (outward from that leg) force components for a given forward direction (n, 3)."""
    force = np.asarray(force, float)
    r = right_axis(fwd)
    side = np.sum(force * r, axis=-1)
    return np.sum(force * fwd, axis=-1), (side if leg == 'R' else -side)


# ------------------------------------------------------------------------------------------------ the authors' scaled model
JOINT_PARENT = {'hip': 'pelvis', 'knee': 'femur', 'ankle': 'tibia', 'subtalar': 'talus'}


def parse_osim(text):
    """Markers (body, location) and joint locations of an OpenSim 3.x model: location_in_parent (in the parent body
    frame) of hip, knee, ankle and subtalar joints per side, in metres. Raises KeyError for anything missing."""
    markers = {m.group(1): (m.group(2).strip(), np.array(m.group(3).split(), float))
               for m in re.finditer(r'<Marker name="([^"]+)">.*?<body>([^<]*)</body>.*?<location>([^<]*)</location>', text, re.S)}
    joints = {}
    for m in re.finditer(r'<CustomJoint name="([^"]+)">\s*(?:<!--.*?-->\s*)*<parent_body>([^<]*)</parent_body>'
                         r'(?:\s*<!--.*?-->)*\s*<location_in_parent>([^<]*)</location_in_parent>', text, re.S):
        joints[m.group(1)] = (m.group(2).strip(), np.array(m.group(3).split(), float))
    return markers, joints


def model_geometry(text, side):
    """Constants of one leg from the model text: hip centre in the pelvis frame, knee centre in the femur frame,
    ankle centre in the tibia frame, subtalar location in the talus frame, and the local positions of the markers used
    for the checks. ``side`` is 'r' or 'l'."""
    markers, joints = parse_osim(text)
    s = side
    pick = {}
    for key, names in (('hip', (f'hip_{s}',)), ('knee', (f'knee_{s}', f'walker_knee_{s}')), ('ankle', (f'ankle_{s}',)),
                       ('subtalar', (f'subtalar_{s}',))):
        found = [n for n in names if n in joints]
        if not found:
            raise KeyError(f'joint {names} not in model')
        parent, loc = joints[found[0]]
        if parent != f'{JOINT_PARENT[key]}' + ('' if key == 'hip' else f'_{s}'):
            raise KeyError(f'joint {found[0]} has parent {parent}, expected {JOINT_PARENT[key]}')
        pick[key] = loc
    S = s.upper()
    out = {'hip_in_pelvis': pick['hip'], 'knee_in_femur': pick['knee'], 'ankle_in_tibia': pick['ankle'],
           'subtalar_in_talus': pick['subtalar'], 'markers': {}}
    for name, body in ((f'{S}ANK', f'tibia_{s}'), (f'{S}MANK', f'tibia_{s}'), (f'{S}CAL', f'calcn_{s}'),
                       (f'{S}KNE', f'femur_{s}'), (f'{S}MKNE', f'femur_{s}'), (f'{S}MT1', f'calcn_{s}'), (f'{S}MT5', f'calcn_{s}'), ('LASI', 'pelvis'), ('RASI', 'pelvis'),
                       ('LPSI', 'pelvis'), ('RPSI', 'pelvis')):
        if name not in markers:      # a subject's model can lack a marker (AB03 has no ASIS markers); users must check
            continue
        b, loc = markers[name]
        if b != body:
            raise KeyError(f'marker {name} is on {b}, expected {body}')
        out['markers'][name] = loc
    return out


def body_origin(marker_lab, marker_local, rotation):
    """Body origin in the lab from one marker: marker_lab - R @ marker_local (n, 3)."""
    return np.asarray(marker_lab, float) - np.einsum('nij,j->ni', rotation, marker_local)


def model_ankle_centre_via_tibia(lank, lmank, geo, r_tibia):
    """Talus (ankle joint) centre in the lab from the two ankle markers, the tibia orientation and the model's
    marker and joint locations in the tibia frame; the mean of the two marker routes."""
    c = geo['ankle_in_tibia']
    r1 = np.asarray(lank, float) + np.einsum('nij,j->ni', r_tibia, c - geo['markers'][next(k for k in geo['markers'] if k.endswith('ANK') and 'M' not in k)])
    r2 = np.asarray(lmank, float) + np.einsum('nij,j->ni', r_tibia, c - geo['markers'][next(k for k in geo['markers'] if k.endswith('MANK'))])
    return (r1 + r2) / 2.0


def model_talus_origin_via_calcn(cal, geo, r_calcn, r_talus):
    """Talus origin in the lab from the heel marker: the calcaneus origin is the heel marker minus R_calcn @ local
    marker position; the talus origin is the calcaneus origin minus R_talus @ subtalar location in the talus frame."""
    key = next(k for k in geo['markers'] if k.endswith('CAL'))
    calcn_origin = body_origin(cal, geo['markers'][key], r_calcn)
    return calcn_origin - np.einsum('nij,j->ni', r_talus, geo['subtalar_in_talus'])


def model_hip_centre(pelvis_markers, geo, r_pelvis):
    """Hip centre in the lab: the pelvis origin (mean over the four pelvis markers of marker - R @ local) plus
    R_pelvis @ hip location in the pelvis frame. NaN where any pelvis marker is missing."""
    origins = [body_origin(pelvis_markers[k], geo['markers'][k], r_pelvis) for k in ('LASI', 'RASI', 'LPSI', 'RPSI')]
    origin = np.mean(origins, axis=0)
    return origin + np.einsum('nij,j->ni', r_pelvis, geo['hip_in_pelvis'])
