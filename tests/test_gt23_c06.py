"""GT23-C06 tests. EVERY fixture here is SYNTHETIC (built by construction from chosen angles and points); nothing
reads Georgia Tech data and nothing here regenerates or validates the scientific dataset."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import gt23_conventions as cv  # noqa: E402
from contributor_tools import gt23_conventions_check as chk  # noqa: E402

RAD = np.radians


def person(thigh, shank, foot, pelvis, yaw, hip=(0.0, 1.0), lthigh=0.45, lshank=0.45):
    """One synthetic pose (single sample) of a person whose forward direction is rotated by ``yaw`` about the vertical.
    Returns lab markers (metres), Euler rows (file order, intrinsic Y-Z-X) and the sagittal truth, all by construction.
    Lab: +Y up, forward = (cos yaw, 0, -sin yaw), right = forward x up = (sin yaw, 0, cos yaw)."""
    f = np.array([np.cos(yaw), 0.0, -np.sin(yaw)])
    up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up)

    def p3(a, b, lateral=0.0):
        return a * f + b * up + lateral * r
    hip_p = np.array(hip)
    knee = hip_p + lthigh * np.array([np.sin(RAD(thigh)), -np.cos(RAD(thigh))])
    ankle = knee + lshank * np.array([np.sin(RAD(shank)), -np.cos(RAD(shank))])
    e = np.array([np.cos(RAD(foot)), np.sin(RAD(foot))])
    heel = ankle - 0.07 * e
    toe = heel + 0.21 * e
    psis = np.array([-0.05, 1.05])
    asis = psis + 0.1 * np.array([np.cos(RAD(pelvis)), np.sin(RAD(pelvis))])
    m = {'LASI': p3(*asis, -0.13), 'RASI': p3(*asis, 0.13), 'LPSI': p3(*psis, -0.05), 'RPSI': p3(*psis, 0.05),
         'LCAL': p3(*heel, -0.1), 'RCAL': p3(*heel, 0.1), 'LANK': p3(*ankle, -0.115), 'LMANK': p3(*ankle, -0.085),
         'RANK': p3(*ankle, 0.115), 'RMANK': p3(*ankle, 0.085),
         'LMT1': p3(*toe, -0.06), 'LMT5': p3(*toe, -0.14), 'RMT1': p3(*toe, 0.06), 'RMT5': p3(*toe, 0.14)}
    # left foot toe midpoint must be on the line from heel: heel lateral -0.1, toes mean -0.1 (symmetric about it)
    m = {k: v[None, :] for k, v in m.items()}
    # Euler rows: body y axis points to the proximal joint, rotated by the segment angle about the person's right axis.
    eul = {f'{b}_{s}': np.array([[yaw, RAD(a), 0.0]]) for b, a in (('femur', thigh), ('tibia', shank)) for s in 'lr'}
    return m, eul


def run_pose(thigh, shank, foot, pelvis, yaw):
    m, eul = person(thigh, shank, foot, pelvis, yaw)
    fwd = cv.heading(m['LASI'], m['RASI'])
    rot = {k: cv.euler_yzx(*[eul[k][:, i] for i in range(3)]) for k in eul}
    toe = (m['LMT1'] + m['LMT5']) / 2
    seg = cv.segment_angle_set(fwd, (m['LASI'] + m['RASI']) / 2, (m['LPSI'] + m['RPSI']) / 2, -rot['femur_l'][:, :, 1],
                               -rot['tibia_l'][:, :, 1], m['LCAL'], toe)
    return seg, cv.joint_angles(seg), m, eul


@pytest.mark.parametrize('yaw', [0.0, 0.7, -2.4])
def test_known_values_42_40_30_any_heading(yaw):
    # synthetic: thigh +30, shank -10, foot +20, pelvis -12 deg -> hip 42, knee 40, ankle 30 deg, whatever the heading
    seg, j, _, _ = run_pose(30, -10, 20, -12, yaw)
    assert np.degrees([seg['thigh'][0], seg['shank'][0], seg['foot'][0], seg['pelvis'][0]]) == pytest.approx([30, -10, 20, -12], abs=1e-9)
    assert np.degrees([j['hip'][0], j['knee'][0], j['ankle'][0]]) == pytest.approx([42, 40, 30], abs=1e-9)


def test_standing_straight_is_zero_knee_and_zero_ankle_when_foot_flat():
    seg, j, _, _ = run_pose(0, 0, 0, 0, 1.0)
    assert j['knee'][0] == pytest.approx(0, abs=1e-12)
    assert j['ankle'][0] == pytest.approx(0, abs=1e-12)


def test_knee_flexed_is_positive_and_anterior_pelvic_tilt_negative():
    _, j, _, _ = run_pose(20, -40, 0, 0, 0.3)
    assert np.degrees(j['knee'][0]) == pytest.approx(60, abs=1e-9)
    seg, _, _, _ = run_pose(0, 0, 0, -15, 0.3)   # ASIS below PSIS: anterior tilt
    assert np.degrees(seg['pelvis'][0]) == pytest.approx(-15, abs=1e-9)


def test_composition_to_1e12():
    rng = np.random.default_rng(7)   # recorded seed
    cols = {k: [] for k in ('pelvis', 'thigh', 'shank', 'foot', 'hip', 'knee', 'ankle')}
    for t, s, f, p, y in rng.uniform(-60, 60, (60, 5)):
        seg, j, _, _ = run_pose(t, s, f, p, y / 20)
        for k, v in {**seg, **j}.items():
            cols[k].append(v[0])
    a = {k: np.array(v) for k, v in cols.items()}
    assert cv.composition_error(a['pelvis'], a['thigh'], a['shank'], a['foot'], a['hip'], a['knee'], a['ankle']) < 1e-12


def test_euler_order_is_intrinsic_yzx_file_order():
    from scipy.spatial.transform import Rotation
    rng = np.random.default_rng(3)
    ang = rng.uniform(-1.2, 1.2, (20, 3))
    mine = cv.euler_yzx(ang[:, 0], ang[:, 1], ang[:, 2])
    ref = Rotation.from_euler('YZX', ang).as_matrix()
    assert np.max(np.abs(mine - ref)) < 1e-12


def test_second_implementation_agrees_with_primary_on_synthetic_poses():
    seg, j, m, eul = run_pose(30, -10, 20, -12, 0.9)
    primary = {'pelvis_sagittal_angle_rad': seg['pelvis']}
    for side in ('left', 'right'):
        for k in ('thigh', 'shank', 'foot'):
            primary[f'{k}_sagittal_angle_{side}_rad'] = seg[k]
        primary[f'hip_flexion_angle_{side}_rad'] = j['hip']
        primary[f'knee_flexion_angle_{side}_rad'] = j['knee']
        primary[f'ankle_dorsiflexion_angle_{side}_rad'] = j['ankle']
        for k in ('anterior', 'vertical', 'lateral'):
            primary[f'cop_{k}_{side}_m'] = np.array([np.nan])
    worst, used = chk.compare(primary, m, eul, {'L': np.full((1, 3), np.nan), 'R': np.full((1, 3), np.nan)}, step=1)
    assert used['angle_samples'] == 1
    assert worst['angles_rad'] < 1e-12


def test_foot_frame_pressure_point_known_values():
    # flat foot, heading 40 deg: ankle at lab origin + (0, 0.08), heel 0.07 behind, toe 0.14 ahead of the ankle, 0.1 m origin
    yaw = RAD(40)
    f = np.array([np.cos(yaw), 0.0, -np.sin(yaw)])
    r = np.cross(f, [0, 1, 0])
    ankle = np.array([[1.0, 0.08, 2.0]])
    heel = ankle + np.array([[0, -0.08, 0]]) - 0.07 * f
    toe = heel + 0.21 * f
    point = ankle + np.array([[0, -0.08, 0]]) + 0.05 * f + 0.02 * r   # 5 cm forward of the ankle, 2 cm to the right, on the floor
    right = cv.foot_frame_point(point, ankle, heel, toe, 'R')
    left = cv.foot_frame_point(point, ankle, heel, toe, 'L')
    assert right['anterior'][0] == pytest.approx(0.05 - 0.1, abs=1e-12)
    assert right['vertical'][0] == pytest.approx(-0.08, abs=1e-12)
    assert right['lateral'][0] == pytest.approx(0.02, abs=1e-12)
    assert left['lateral'][0] == pytest.approx(-0.02, abs=1e-12)    # outward from the left leg is toward the left


def test_foot_frame_tilted_foot_and_independent_second_implementation():
    seg, j, m, eul = run_pose(5, -5, 25, 0, 0.4)      # toes up 25 deg
    ankle = (m['RANK'] + m['RMANK']) / 2
    toe = (m['RMT1'] + m['RMT5']) / 2
    # a point 0.1 m forward of the ankle along the foot and 0.03 m up from the foot: foot-frame (0, 0.03, 0)
    e_f = (toe - m['RCAL']) / np.linalg.norm(toe - m['RCAL'])
    e_u = np.array([[-np.sin(RAD(25)) * np.cos(0.4), np.cos(RAD(25)), np.sin(RAD(25)) * np.sin(0.4)]])
    point = ankle + 0.1 * e_f + 0.03 * e_u
    ff = cv.foot_frame_point(point, ankle, m['RCAL'], toe, 'R')
    assert ff['anterior'][0] == pytest.approx(0.0, abs=1e-9)
    assert ff['vertical'][0] == pytest.approx(0.03, abs=1e-9)
    assert ff['lateral'][0] == pytest.approx(0.0, abs=1e-9)
    c = chk.cop_at(0, {k: v for k, v in m.items()}, point, 'R')
    assert c == pytest.approx([0.0, 0.03, 0.0], abs=1e-9)


def test_quasi_static_ankle_moment_sign_and_value():
    # vertical force 700 N at 0.05 m ahead of the ankle axis (pressure point 0.05 m from the 0.1 m origin... anterior=-0.05)
    m = cv.ankle_moment_quasi_static(np.array([-0.05]), np.array([-0.08]), np.array([0.0]), np.array([700.0]))
    assert m[0] == pytest.approx(-35.0)            # plantarflexor (negative): lever 0.05 m ahead of the ankle
    m2 = cv.ankle_moment_quasi_static(np.array([-0.05]), np.array([-0.08]), np.array([100.0]), np.array([700.0]))
    assert m2[0] == pytest.approx(-(0.05 * 700.0 - (-0.08) * 100.0))


def test_force_forward_sideways_and_mirror():
    yaw = RAD(25)
    fwd = np.array([[np.cos(yaw), 0, -np.sin(yaw)]])
    r = np.cross(fwd, [0, 1, 0])
    force = 30.0 * fwd + 10.0 * r + 500.0 * np.array([[0, 1, 0]])
    a_r, s_r = cv.force_forward_sideways(force, fwd, 'R')
    a_l, s_l = cv.force_forward_sideways(force, fwd, 'L')
    assert (a_r[0], s_r[0]) == pytest.approx((30.0, 10.0))
    assert s_l[0] == pytest.approx(-10.0)           # mirrored: outward from the left leg is toward the left
    assert a_l[0] == pytest.approx(30.0)


def test_heading_held_per_span_and_nan_outside():
    ang = np.radians(np.array([0, 4, -4, 0, 90, 90]))
    fwd = np.stack([np.cos(ang), np.zeros(6), -np.sin(ang)], axis=1)
    spans = cv.merge_spans([(0, 2), (2, 3), (5, 5)], 6)
    assert spans == [(0, 3), (5, 5)]
    held, rep = cv.heading_by_span(fwd, spans)
    assert np.degrees(np.arctan2(-held[0, 2], held[0, 0])) == pytest.approx(0.0, abs=1e-9)
    assert np.all(np.isnan(held[4])) and np.allclose(held[5], fwd[5])
    assert rep[0]['max_dev_deg'] == pytest.approx(4.0, abs=1e-9)


def test_central_derivative_and_nan_edges():
    t = np.arange(50) / 200.0
    x = np.radians(40.0) * t                       # 40 deg/s
    d = cv.central_derivative(x)
    assert np.isnan(d[0]) and np.isnan(d[-1])
    assert d[1:-1] == pytest.approx(np.radians(40.0), rel=1e-12)
    x2 = x.copy()
    x2[10] = np.nan
    d2 = cv.central_derivative(x2)
    assert np.isnan(d2[9]) and np.isnan(d2[11]) and np.isfinite(d2[10])


def test_derivative_wraps_across_pi():
    a = cv.wrap(np.array([3.1, 3.14, -3.13, -3.09]))
    d = cv.central_derivative(a, dt=1.0)
    assert d[1] == pytest.approx((cv.wrap(-3.13 - 3.1)) / 2)


OSIM = """<Joint>
<CustomJoint name="hip_r">
<parent_body>pelvis</parent_body>
<!--c-->
<location_in_parent>-0.08 -0.06 0.09</location_in_parent>
</CustomJoint>
<CustomJoint name="knee_r">
<parent_body>femur_r</parent_body>
<location_in_parent>0 -0.4 0</location_in_parent>
</CustomJoint>
<CustomJoint name="ankle_r">
<parent_body>tibia_r</parent_body>
<location_in_parent>0 -0.5 0</location_in_parent>
</CustomJoint>
<CustomJoint name="subtalar_r">
<parent_body>talus_r</parent_body>
<location_in_parent>-0.05 -0.04 0.008</location_in_parent>
</CustomJoint>
<Marker name="RANK"><body>tibia_r</body><location>0.01 -0.46 0.05</location></Marker>
<Marker name="RMANK"><body>tibia_r</body><location>0.01 -0.46 -0.04</location></Marker>
<Marker name="RCAL"><body>calcn_r</body><location>-0.02 0.04 0.01</location></Marker>
<Marker name="RKNE"><body>femur_r</body><location>0 -0.4 0.06</location></Marker>
<Marker name="RMKNE"><body>femur_r</body><location>0 -0.4 -0.06</location></Marker>
<Marker name="LASI"><body>pelvis</body><location>0 0.02 -0.14</location></Marker>
<Marker name="RASI"><body>pelvis</body><location>0 0.02 0.14</location></Marker>
<Marker name="LPSI"><body>pelvis</body><location>-0.18 0.06 -0.06</location></Marker>
<Marker name="RPSI"><body>pelvis</body><location>-0.18 0.06 0.06</location></Marker>
"""


def test_model_geometry_parse_and_ankle_centre_known_value():
    geo = cv.model_geometry(OSIM, 'r')
    assert geo['ankle_in_tibia'] == pytest.approx([0, -0.5, 0])
    assert geo['hip_in_pelvis'] == pytest.approx([-0.08, -0.06, 0.09])
    # tibia upright (identity), origin at lab (1, 1, 1): markers at origin + local, ankle centre at origin + (0, -0.5, 0)
    origin = np.array([[1.0, 1.0, 1.0]])
    r = np.eye(3)[None]
    lank = origin + geo['markers']['RANK']
    lmank = origin + geo['markers']['RMANK']
    c = cv.model_ankle_centre_via_tibia(lank, lmank, geo, r)
    assert c[0] == pytest.approx(origin[0] + np.array([0, -0.5, 0]))
    # 36 mm below the marker midpoint along the tibia: midpoint y local = -0.46 -> 0.04 below the midpoint here (by construction)
    mid = (lank + lmank) / 2
    assert (c - mid)[0] == pytest.approx([-0.01, -0.04, -0.005], abs=1e-12)
    # hip centre with a rotated pelvis
    rp = cv.euler_yzx(np.array([0.5]), np.array([0.1]), np.array([-0.05]))
    porigin = np.array([[0.3, 0.9, -0.2]])
    pel = {k: porigin + np.einsum('nij,j->ni', rp, geo['markers'][k]) for k in ('LASI', 'RASI', 'LPSI', 'RPSI')}
    hip = cv.model_hip_centre(pel, geo, rp)
    assert hip[0] == pytest.approx((porigin + np.einsum('nij,j->ni', rp, geo['hip_in_pelvis']))[0], abs=1e-12)
    # talus origin from the heel marker, calcaneus and talus rotations
    rc = cv.euler_yzx(np.array([0.2]), np.array([0.1]), np.array([0.0]))
    rt = cv.euler_yzx(np.array([0.2]), np.array([0.05]), np.array([0.0]))
    talus = np.array([[0.5, 0.1, 0.4]])
    calcn_origin = talus + np.einsum('nij,j->ni', rt, geo['subtalar_in_talus'])
    cal = calcn_origin + np.einsum('nij,j->ni', rc, geo['markers']['RCAL'])
    assert cv.model_talus_origin_via_calcn(cal, geo, rc, rt)[0] == pytest.approx(talus[0], abs=1e-12)


def test_missing_marker_stays_missing_and_nothing_is_filled():
    seg, j, m, eul = run_pose(30, -10, 20, -12, 0.3)
    lasi = m['LASI'].copy()
    lasi[:] = np.nan
    fwd = cv.heading(lasi, m['RASI'])
    assert np.isnan(fwd).all()
    toe = (m['LMT1'] + m['LMT5']) / 2
    rot = {k: cv.euler_yzx(*[eul[k][:, i] for i in range(3)]) for k in eul}
    s = cv.segment_angle_set(fwd, (lasi + m['RASI']) / 2, (m['LPSI'] + m['RPSI']) / 2, -rot['femur_l'][:, :, 1], -rot['tibia_l'][:, :, 1], m['LCAL'], toe)
    assert all(np.isnan(v).all() for v in s.values())


def test_contact_heading_fills_only_uncovered_loaded_samples():
    ang = np.radians(np.array([0, 0, 10, 10, 10, 30, 30, 0]))
    fwd = np.stack([np.cos(ang), np.zeros(8), -np.sin(ang)], axis=1)
    held = np.full((8, 3), np.nan)
    held[0:2] = fwd[0]                              # a stride span covers samples 0-1 only
    loaded = np.array([1, 1, 1, 1, 1, 0, 0, 0], bool)  # one contact over samples 0-4
    out, runs, filled, left = cv.fill_heading_by_contact(held, fwd, loaded)
    assert (runs, filled, left) == (1, 3, 0)
    assert np.allclose(out[0], fwd[0]) and np.allclose(out[2], out[4]) and np.allclose(out[2], cv.unit(fwd[0:5].mean(axis=0)))   # the whole contact's mean heading
    assert np.all(np.isnan(out[5:]))               # unloaded samples are never filled
