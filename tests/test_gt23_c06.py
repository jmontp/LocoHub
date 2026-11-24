"""GT23-C06 tests (side-view planes, D-REF-4). EVERY fixture here is SYNTHETIC (built by construction from chosen angles and
points); nothing reads Georgia Tech data and nothing here regenerates or validates the scientific dataset."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools import gt23_conventions as cv  # noqa: E402
from contributor_tools import gt23_conventions_check as chk  # noqa: E402

RAD = np.radians
UP = np.array([0.0, 1.0, 0.0])


def fwd_of(yaw):
    return np.array([np.cos(yaw), 0.0, -np.sin(yaw)])


def person(thigh, shank, foot, pelvis, pelvis_yaw, leg_yaw=None, toe_out=0.0):
    """One synthetic pose (single sample). The pelvis faces ``pelvis_yaw``; both legs lie in vertical planes facing
    ``leg_yaw`` (default: the pelvis yaw) with the stated segment angles in degrees measured in THEIR OWN plane; the feet
    point ``toe_out`` radians outward of the leg plane while keeping the in-plane pitch of a foot of angle ``foot`` before
    the turn (true elevation = foot). Returns lab markers (metres) and Euler rows (file order, intrinsic Y-Z-X)."""
    leg_yaw = pelvis_yaw if leg_yaw is None else leg_yaw
    fp, fl = fwd_of(pelvis_yaw), fwd_of(leg_yaw)
    rp, rl = np.cross(fp, UP), np.cross(fl, UP)

    def pelvis_pt(a, b, lateral=0.0):
        return a * fp + b * UP + lateral * rp
    psis = np.array([-0.05, 1.05])
    asis = psis + 0.1 * np.array([np.cos(RAD(pelvis)), np.sin(RAD(pelvis))])
    m = {'LASI': pelvis_pt(*asis, -0.13), 'RASI': pelvis_pt(*asis, 0.13), 'LPSI': pelvis_pt(*psis, -0.05), 'RPSI': pelvis_pt(*psis, 0.05)}
    hip = np.array([0.0, 1.0])
    knee = hip + 0.45 * np.array([np.sin(RAD(thigh)), -np.cos(RAD(thigh))])
    ankle = knee + 0.45 * np.array([np.sin(RAD(shank)), -np.cos(RAD(shank))])
    for side, sgn in (('L', -1.0), ('R', 1.0)):
        def leg_pt(a, b, lateral=0.0, sgn=sgn):
            return a * fl + b * UP + (sgn * 0.1 + lateral) * rl
        m[f'{side}KNE'] = leg_pt(*knee, sgn * 0.05)        # lateral marker: outward of the knee
        m[f'{side}MKNE'] = leg_pt(*knee, -sgn * 0.05)      # medial marker
        m[f'{side}ANK'] = leg_pt(*ankle, sgn * 0.015)
        m[f'{side}MANK'] = leg_pt(*ankle, -sgn * 0.015)
        # foot: elevation `foot`, horizontal direction turned outward by toe_out about the vertical
        out_dir = sgn * rl
        f_foot = np.cos(toe_out) * fl + np.sin(toe_out) * out_dir
        r_foot = np.cross(f_foot, UP)
        heel = np.array(leg_pt(*ankle)) + np.array([0.0, -0.08, 0.0])
        v = 0.21 * (np.cos(RAD(foot)) * f_foot + np.sin(RAD(foot)) * UP)
        toe = heel + v
        m[f'{side}CAL'] = heel
        m[f'{side}MT1'] = toe + 0.04 * r_foot
        m[f'{side}MT5'] = toe - 0.04 * r_foot
    eul = {f'{b}_{s}': np.array([[leg_yaw, RAD(a), 0.0]]) for b, a in (('femur', thigh), ('tibia', shank)) for s in 'lr'}
    return {k: v[None, :] for k, v in m.items()}, eul


def angles(m, eul, side='L'):
    """Primary-code angles of one leg and the pelvis from a synthetic pose (arrays of length n)."""
    s = side.lower()
    rot = {k: cv.euler_yzx(*[eul[k][:, i] for i in range(3)]) for k in eul}
    fl = cv.plane_forward(cv.knee_axis_to_right(m[f'{side}KNE'], m[f'{side}MKNE'], side))
    toe = (m[f'{side}MT1'] + m[f'{side}MT5']) / 2
    seg = cv.leg_segment_angles(fl, -rot[f'femur_{s}'][:, :, 1], -rot[f'tibia_{s}'][:, :, 1], m[f'{side}CAL'], toe)
    seg['pelvis'] = cv.pelvis_angle((m['LASI'] + m['RASI']) / 2, (m['LPSI'] + m['RPSI']) / 2)
    return seg, cv.joint_angles(seg), fl


@pytest.mark.parametrize('side', ['L', 'R'])
@pytest.mark.parametrize('pelvis_yaw,leg_yaw', [(0.0, 0.0), (0.3, 1.2), (-2.4, 0.9)])
def test_known_values_42_40_30_in_a_rotated_leg_plane(side, pelvis_yaw, leg_yaw):
    # synthetic: thigh +30, shank -10, foot +20 (in the leg plane), pelvis -12 (in its own plane) -> hip 42, knee 40, ankle 30,
    # whatever the leg plane's heading relative to the pelvis
    m, eul = person(30, -10, 20, -12, pelvis_yaw, leg_yaw)
    seg, j, _ = angles(m, eul, side)
    assert np.degrees([seg['thigh'][0], seg['shank'][0], seg['foot'][0], seg['pelvis'][0]]) == pytest.approx([30, -10, 20, -12], abs=1e-9)
    assert np.degrees([j['hip'][0], j['knee'][0], j['ankle'][0]]) == pytest.approx([42, 40, 30], abs=1e-9)


def test_turning_walker_foot_90_degrees_from_walking_direction_stays_defined_and_continuous():
    # the walker turns through 180 degrees over 400 samples while the leg keeps its pose; the legs' heading is 90 degrees
    # off the pelvis heading half of the time (pelvis leads the turn). Every angle stays defined and constant.
    yaws = np.linspace(0.0, np.pi, 400)
    rows = []
    for yaw in yaws:
        pelvis_yaw = yaw - np.pi / 2 * np.sin(yaw)          # swings the pelvis up to 90 degrees away from the leg heading
        m, eul = person(25, -15, 10, -10, pelvis_yaw, yaw)
        seg, j, _ = angles(m, eul, 'R')
        rows.append([seg['thigh'][0], seg['shank'][0], seg['foot'][0], seg['pelvis'][0], j['hip'][0], j['knee'][0], j['ankle'][0]])
    a = np.degrees(np.array(rows))
    assert np.all(np.isfinite(a))
    assert np.max(np.abs(a - a[0])) < 1e-9                       # constant
    assert np.max(np.abs(np.diff(a, axis=0))) < 1e-9             # and so continuous (no jump, no 360-degree branch)
    assert a[0] == pytest.approx([25, -15, 10, -10, 35, 40, 25], abs=1e-9)


def test_old_pelvis_plane_would_sweep_the_foot_through_180_degrees():
    # the same foot measured in a plane 90 degrees away from the leg is ill-defined (this is the retired lab/pelvis-plane
    # behaviour); the leg's own plane gives the stated angle.
    m, eul = person(0, 0, 10, 0, 0.0, 0.0)
    toe = (m['RMT1'] + m['RMT5']) / 2
    v = toe - m['RCAL']
    off_plane = cv.angle_from_forward(cv.sag(v, fwd_of(0.0 - np.pi / 2)))    # a plane turned 90 degrees away
    assert abs(np.degrees(off_plane[0]) - 10) > 60
    seg, _, _ = angles(m, eul, 'R')
    assert np.degrees(seg['foot'][0]) == pytest.approx(10, abs=1e-9)


@pytest.mark.parametrize('side', ['L', 'R'])
def test_toe_out_15_degrees_known_foot_angle_and_pressure_point(side):
    tau, elev = RAD(15), RAD(20)
    m, eul = person(0, 0, 20, 0, 0.4, 0.4, toe_out=tau)
    seg, _, fl = angles(m, eul, side)
    # foot of true elevation 20 deg turned 15 deg out of the leg plane: in-plane angle atan2(sin e, cos e cos tau)
    assert seg['foot'][0] == pytest.approx(np.arctan2(np.sin(elev), np.cos(elev) * np.cos(tau)), abs=1e-12)
    # D-REF-2 as ruled 2026-11-24: the pressure-point frame follows the leg plane, so toe-out is a sideways offset.
    # flat foot: a point 0.1 m ahead of the ankle along the (turned) foot is 0.1*cos(tau) - 0.1 anterior, 0.1*sin(tau) outward
    m, eul = person(0, 0, 0, 0, 0.4, 0.4, toe_out=tau)
    seg, _, fl = angles(m, eul, side)
    ankle = (m[f'{side}ANK'] + m[f'{side}MANK']) / 2
    sgn = 1.0 if side == 'R' else -1.0
    f_foot = np.cos(tau) * fwd_of(0.4) + np.sin(tau) * sgn * np.cross(fwd_of(0.4), UP)
    point = ankle + 0.1 * f_foot[None, :]
    ff = cv.foot_frame_point(point, ankle, fl, seg['foot'], side)
    assert ff['anterior'][0] == pytest.approx(0.1 * np.cos(tau) - 0.1, abs=1e-12)
    assert ff['lateral'][0] == pytest.approx(0.1 * np.sin(tau), abs=1e-12)     # outward from that leg for both legs
    assert ff['vertical'][0] == pytest.approx(0.0, abs=1e-12)


def test_knee_axis_and_plane_forward_directions():
    # right knee: lateral marker on the right; left knee: lateral on the left; both axes point to the person's right
    f = fwd_of(0.7)
    r = np.cross(f, UP)
    lat_r, med_r = np.array([[0, 0.5, 0]]) + 0.05 * r, np.array([[0, 0.5, 0]]) - 0.05 * r
    assert cv.knee_axis_to_right(lat_r, med_r, 'R')[0] == pytest.approx(0.1 * r)
    assert cv.knee_axis_to_right(med_r, lat_r, 'L')[0] == pytest.approx(0.1 * r)   # left: lateral is the one on the left
    assert cv.plane_forward(0.1 * r[None, :] + 0.03 * UP)[0] == pytest.approx(f)    # a tilted axis keeps only its horizontal part
    assert np.isnan(cv.plane_forward(UP[None, :])).all()                            # a vertical axis has no plane


def test_missing_knee_marker_leaves_leg_columns_missing_not_filled():
    m, eul = person(30, -10, 20, -12, 0.3)
    m['RKNE'] = np.full((1, 3), np.nan)
    seg, j, _ = angles(m, eul, 'R')
    assert np.isnan(seg['thigh']).all() and np.isnan(seg['shank']).all() and np.isnan(seg['foot']).all()
    assert np.isnan(j['hip']).all() and np.isnan(j['knee']).all() and np.isnan(j['ankle']).all()
    assert np.isfinite(seg['pelvis']).all()            # the pelvis does not need the knee markers
    left, _, _ = angles(m, eul, 'L')
    assert np.degrees(left['thigh'][0]) == pytest.approx(30, abs=1e-9)    # the other leg is untouched


def test_composition_to_1e12_with_different_planes():
    rng = np.random.default_rng(7)   # recorded seed
    cols = {k: [] for k in ('pelvis', 'thigh', 'shank', 'foot', 'hip', 'knee', 'ankle')}
    for t, s, f, p, y, z in rng.uniform(-60, 60, (60, 6)):
        m, eul = person(t, s, f, p, y / 20, z / 20)
        seg, j, _ = angles(m, eul, 'L')
        for k, v in {**seg, **j}.items():
            cols[k].append(v[0])
    a = {k: np.array(v) for k, v in cols.items()}
    assert cv.composition_error(a['pelvis'], a['thigh'], a['shank'], a['foot'], a['hip'], a['knee'], a['ankle']) < 1e-12


def test_second_implementation_agrees_with_primary_in_rotated_planes_with_toe_out():
    m, eul = person(30, -10, 20, -12, 0.9, 2.0, toe_out=RAD(15))
    primary = {}
    cop_lab = {}
    for side, word in (('L', 'left'), ('R', 'right')):
        seg, j, fl = angles(m, eul, side)
        primary['pelvis_sagittal_angle_rad'] = seg['pelvis']
        for k in ('thigh', 'shank', 'foot'):
            primary[f'{k}_sagittal_angle_{word}_rad'] = seg[k]
        primary[f'hip_flexion_angle_{word}_rad'] = j['hip']
        primary[f'knee_flexion_angle_{word}_rad'] = j['knee']
        primary[f'ankle_dorsiflexion_angle_{word}_rad'] = j['ankle']
        ankle = (m[f'{side}ANK'] + m[f'{side}MANK']) / 2
        point = ankle + np.array([[0.03, -0.07, 0.02]])
        cop_lab[side] = point
        ff = cv.foot_frame_point(point, ankle, fl, seg['foot'], side)
        for k in ('anterior', 'vertical', 'lateral'):
            primary[f'cop_{k}_{word}_m'] = ff[k]
    worst, used = chk.compare(primary, m, eul, cop_lab, step=1)
    assert used['angle_samples'] == 1 and used['cop_samples'] == 2
    assert worst['angles_rad'] < 1e-12 and worst['cop_m'] < 1e-12


def test_raised_plate_height_comes_from_the_source_not_zero():
    # synthetic stair: plate surface 0.5 m above the lab floor; flat foot, ankle 0.08 above the sole, pressure point
    # 5 cm ahead of the ankle on the sole. With the source height the vertical coordinate is -0.08; with height 0 it
    # would be -0.58 (the converted-stairs bug).
    ankle = np.array([[1.0, 0.58, 2.0]])
    fl = np.array([[1.0, 0.0, 0.0]])
    zero = np.zeros(1)
    p = cv.plate_point([1.05], [0.5], [2.0], [700.0])
    ff = cv.foot_frame_point(p, ankle, fl, zero, 'R')
    assert ff['vertical'][0] == pytest.approx(-0.08, abs=1e-12)
    assert ff['anterior'][0] == pytest.approx(0.05 - 0.1, abs=1e-12)
    wrong = cv.foot_frame_point(cv.plate_point([1.05], [0.0], [2.0], [700.0]), ankle, fl, zero, 'R')
    assert wrong['vertical'][0] == pytest.approx(-0.58, abs=1e-12)
    assert np.isnan(cv.plate_point([1.05], [np.nan], [2.0], [700.0])[0, 1])
    assert np.isnan(cv.plate_point([1.05], [0.5], [2.0], [10.0])).all()


def test_foot_frame_tilted_foot_known_values():
    # foot toes up 25 deg in a plane facing 0.4 rad; a point 0.1 m ahead of the ankle along the foot and 0.03 m up from it
    f = fwd_of(0.4)[None, :]
    th = RAD(25)
    ankle = np.array([[1.0, 0.1, 2.0]])
    e_f = np.cos(th) * f + np.sin(th) * UP[None, :]
    e_u = -np.sin(th) * f + np.cos(th) * UP[None, :]
    point = ankle + 0.1 * e_f + 0.03 * e_u
    ff = cv.foot_frame_point(point, ankle, f, np.array([th]), 'R')
    assert (ff['anterior'][0], ff['vertical'][0], ff['lateral'][0]) == pytest.approx((0.0, 0.03, 0.0), abs=1e-12)
    # sideways: 2 cm to the person's right is +0.02 for the right leg and -0.02 for the left leg
    r = np.cross(f, UP[None, :])
    assert cv.foot_frame_point(ankle + 0.1 * e_f + 0.02 * r, ankle, f, np.array([th]), 'R')['lateral'][0] == pytest.approx(0.02)
    assert cv.foot_frame_point(ankle + 0.1 * e_f + 0.02 * r, ankle, f, np.array([th]), 'L')['lateral'][0] == pytest.approx(-0.02)


def test_euler_order_is_intrinsic_yzx_file_order():
    from scipy.spatial.transform import Rotation
    rng = np.random.default_rng(3)
    ang = rng.uniform(-1.2, 1.2, (20, 3))
    mine = cv.euler_yzx(ang[:, 0], ang[:, 1], ang[:, 2])
    ref = Rotation.from_euler('YZX', ang).as_matrix()
    assert np.max(np.abs(mine - ref)) < 1e-12


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


def test_heel_above_plate_separates_flat_plate_from_curb():
    # synthetic: heel marker 0.07 above a flat plate (level walking) versus 0.22 above it on an undocumented curb
    plate = np.array([0.0, 0.0, np.nan, 0.0])
    assert cv.heel_above_plate(np.array([0.07, 0.08, 0.5, 0.06]), plate) == pytest.approx(0.07)
    assert cv.heel_above_plate(np.array([0.22, 0.23, 0.5, 0.21]), plate) == pytest.approx(0.22)
    assert cv.heel_above_plate(np.array([0.1]), np.array([np.nan])) is None
