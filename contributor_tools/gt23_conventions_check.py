"""Second, independent implementation of the GT23-C06 angle and foot-frame arithmetic (checking code only).

Deliberately different from gt23_conventions.py: scalar Python loops, scipy rotations for the Euler tables
(intrinsic 'YZX'), a person-frame basis built by Gram-Schmidt from the ASIS line, complex-number angles, and the
foot frame built from an explicit 3x3 basis. It shares no function with the primary code. It is run on every
``step``-th sample of a recording and compared with the primary output.
"""
import cmath
import math

import numpy as np
from scipy.spatial.transform import Rotation

FOOT_ORIGIN = 0.1


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _scale(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _basis_from_asis(lasi, rasi):
    """Rows: forward, up, right. Right is taken along the ASIS line (horizontal part), forward = up x right_unit... built
    so that forward x up = right."""
    up = [0.0, 1.0, 0.0]
    w = _sub(rasi, lasi)
    w = _sub(w, _scale(up, _dot(w, up)))          # horizontal part of the ASIS line
    right = _scale(w, 1.0 / _norm(w))
    forward = _cross(up, right)                    # up x right = forward (since forward x up = right)
    return forward, up, right


def _phase_from_down(vec, basis):
    f, u, _ = basis
    return cmath.phase(complex(-_dot(vec, u), _dot(vec, f)))   # angle measured from the downward direction


def _phase_from_forward(vec, basis):
    f, u, _ = basis
    return cmath.phase(complex(_dot(vec, f), _dot(vec, u)))


def angles_at(i, m, e):
    """Segment and joint angles of one leg at sample i. ``m`` holds marker arrays (n, 3) in metres by name, ``e`` holds
    the Euler arrays (n, 3) by body name; the leg is chosen by the keys (m['asis_l'] ... see the caller)."""
    basis = _basis_from_asis(m['LASI'][i], m['RASI'][i])
    asis = [(m['LASI'][i][k] + m['RASI'][i][k]) / 2 for k in range(3)]
    psis = [(m['LPSI'][i][k] + m['RPSI'][i][k]) / 2 for k in range(3)]
    out = {'pelvis': _phase_from_forward(_sub(asis, psis), basis)}
    for side in 'LR':
        s = side.lower()
        femur = Rotation.from_euler('YZX', e[f'femur_{s}'][i]).as_matrix()
        tibia = Rotation.from_euler('YZX', e[f'tibia_{s}'][i]).as_matrix()
        thigh_down = [-femur[0][1], -femur[1][1], -femur[2][1]]
        shank_down = [-tibia[0][1], -tibia[1][1], -tibia[2][1]]
        toe = [(m[f'{side}MT1'][i][k] + m[f'{side}MT5'][i][k]) / 2 for k in range(3)]
        thigh = _phase_from_down(thigh_down, basis)
        shank = _phase_from_down(shank_down, basis)
        foot = _phase_from_forward(_sub(toe, m[f'{side}CAL'][i]), basis)
        out[side] = {'thigh': thigh, 'shank': shank, 'foot': foot, 'hip': thigh - out['pelvis'], 'knee': thigh - shank,
                     'ankle': foot - shank}
    return out


def cop_at(i, m, cop_lab, side):
    """Pressure point of one leg at sample i in the foot frame via an explicit basis matrix."""
    heel = m[f'{side}CAL'][i]
    toe = [(m[f'{side}MT1'][i][k] + m[f'{side}MT5'][i][k]) / 2 for k in range(3)]
    ankle = [(m[f'{side}ANK'][i][k] + m[f'{side}MANK'][i][k]) / 2 for k in range(3)]
    ef = _sub(toe, heel)
    ef = _scale(ef, 1.0 / _norm(ef))
    up = [0.0, 1.0, 0.0]
    eu = _sub(up, _scale(ef, _dot(up, ef)))
    eu = _scale(eu, 1.0 / _norm(eu))
    er = _cross(ef, eu)
    q = _sub(cop_lab[i], ankle)
    lat = _dot(q, er)
    return [_dot(q, ef) - FOOT_ORIGIN, _dot(q, eu), lat if side == 'R' else -lat]


def compare(primary, markers, euler, cop_lab, step=25):
    """Largest absolute difference between this implementation and ``primary`` (dict of column arrays named as the
    runner's output columns) on every ``step``-th sample where the inputs are finite. Radians and metres."""
    n = len(markers['LASI'])
    worst = {'angles_rad': 0.0, 'cop_m': 0.0}
    used = {'angle_samples': 0, 'cop_samples': 0}
    names = {'thigh': 'thigh_sagittal_angle_{}_rad', 'shank': 'shank_sagittal_angle_{}_rad',
             'foot': 'foot_sagittal_angle_{}_rad', 'hip': 'hip_flexion_angle_{}_rad', 'knee': 'knee_flexion_angle_{}_rad',
             'ankle': 'ankle_dorsiflexion_angle_{}_rad'}
    for i in range(0, n, step):
        need = ['LASI', 'RASI', 'LPSI', 'RPSI', 'LCAL', 'RCAL', 'LMT1', 'LMT5', 'RMT1', 'RMT5']
        if not all(np.isfinite(markers[k][i]).all() for k in need) or not all(np.isfinite(euler[k][i]).all() for k in euler):
            continue
        a = angles_at(i, markers, euler)
        if np.isfinite(primary['pelvis_sagittal_angle_rad'][i]):
            worst['angles_rad'] = max(worst['angles_rad'], abs(a['pelvis'] - primary['pelvis_sagittal_angle_rad'][i]))
            used['angle_samples'] += 1
        for side, word in (('L', 'left'), ('R', 'right')):
            for k, pat in names.items():
                p = primary[pat.format(word)][i]
                if np.isfinite(p):
                    worst['angles_rad'] = max(worst['angles_rad'], abs(a[side][k] - p))
            ok = all(np.isfinite(markers[f'{side}{k}'][i]).all() for k in ('ANK', 'MANK')) and np.isfinite(cop_lab[side][i]).all()
            if ok and np.isfinite(primary[f'cop_anterior_{word}_m'][i]):
                c = cop_at(i, markers, cop_lab[side], side)
                for val, col in zip(c, ('anterior', 'vertical', 'lateral')):
                    worst['cop_m'] = max(worst['cop_m'], abs(val - primary[f'cop_{col}_{word}_m'][i]))
                used['cop_samples'] += 1
    return worst, used
