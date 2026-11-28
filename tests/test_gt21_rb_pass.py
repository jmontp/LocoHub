"""GT21 merged pass (RB02 + RB04): SYNTHETIC fixtures only. Every expected value is imposed or computed by hand from the
standard (docs/reference/index.md), not by calling the code under test. Nothing here reads real data."""
import math

import numpy as np
import pytest

from contributor_tools import gt21_rb_pass as rb

UPV = np.array([0.0, 1.0, 0.0])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


# body frame of a person facing -Z with right = +X: x forward, y up, z right
R0 = np.array([[0, 0, 1.0], [0, 1, 0], [-1, 0, 0]])      # columns: x_body->(0,0,-1), y->(0,1,0), z->(1,0,0)


def test_body_frame_convention():
    assert np.allclose(R0 @ [1, 0, 0], [0, 0, -1]) and np.allclose(R0 @ [0, 0, 1], [1, 0, 0])


# ---------------------------------------------------------------------------------------------- rigid fit
def test_rigid_fit_recovers_known_pose_and_rejects_reflection():
    rng = np.random.default_rng(7)
    local = rng.normal(size=(4, 3))
    R = ry(0.7) @ rz(-0.4)
    t = np.array([0.3, 1.1, -2.0])
    meas = (local @ R.T + t)[None]
    Rf, tf, rms = rb.rigid_fit(local, meas)
    assert np.allclose(Rf[0], R, atol=1e-12) and np.allclose(tf[0], t, atol=1e-12) and rms[0] < 1e-12
    mirrored = local * np.array([1, 1, -1])
    Rm, _, _ = rb.rigid_fit(local, mirrored[None])
    assert np.isclose(np.linalg.det(Rm[0]), 1.0)


def test_rigid_fit_nan_and_collinear_frames_stay_missing():
    local = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1.0]])
    meas = np.stack([local, local, local[:, :]])
    meas[1, 2, 0] = np.nan
    R, t, rms = rb.rigid_fit(local, meas)
    assert np.isfinite(R[0]).all() and np.isnan(R[1]).all() and np.isfinite(R[2]).all()
    line = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0.0]])
    assert np.isnan(rb.rigid_fit(line, line[None])[0]).all()


# ---------------------------------------------------------------------------------------------- angles
def test_pelvis_angle_posterior_tilt_positive_and_anterior_negative():
    # mid-ASIS 0.18 m forward of mid-PSIS and h above it; angle = atan2(h, 0.18) from forward horizontal.
    for h, sign in ((0.03, 1), (-0.03, -1), (0.0, 0)):
        a = rb.pelvis_angle(np.array([[0.18, h, 0.0]]), np.array([[0.0, 0.0, 0.0]]))[0]
        assert np.isclose(a, math.atan2(h, 0.18)) and (np.sign(a) == sign)


@pytest.mark.parametrize('yaw', [0.0, 0.9, -2.4, 3.0])
def test_leg_plane_angles_equal_imposed_angles_for_any_heading(yaw):
    thigh, shank, foot = 0.5, -0.2, 0.15          # imposed segment angles
    R = ry(yaw)
    fwd = R @ np.array([1.0, 0, 0])
    right = R @ np.array([0.0, 0, 1.0])
    # hip origin, knee below-forward by the thigh angle, ankle likewise (lengths 0.4)
    hip = np.array([0.0, 1.0, 0.0])
    knee = hip + 0.4 * (math.sin(thigh) * fwd - math.cos(thigh) * UPV)
    ankle = knee + 0.4 * (math.sin(shank) * fwd - math.cos(shank) * UPV)
    heel = ankle - 0.05 * UPV
    toe = heel + 0.2 * (math.cos(foot) * fwd + math.sin(foot) * UPV)
    axis = rb.knee_axis_to_right(np.array([-right]), right[None])          # given reversed, must be re-oriented
    assert np.allclose(axis[0], right)
    fl = rb.plane_forward(axis)
    assert np.allclose(fl[0], fwd, atol=1e-12)
    seg = rb.segment_angles(fl, hip[None], knee[None], ankle[None], heel[None], toe[None])
    assert np.allclose([seg['thigh'][0], seg['shank'][0], seg['foot'][0]], [thigh, shank, foot], atol=1e-12)
    pel = np.array([0.05])
    ja = rb.joint_angles(pel, seg['thigh'], seg['shank'], seg['foot'])
    assert np.isclose(ja['knee'][0], thigh - shank) and np.isclose(ja['hip'][0], thigh - 0.05)
    assert np.isclose(ja['ankle'][0], foot - shank)
    # composition thigh = pelvis + hip, shank = thigh - knee, foot = shank + ankle to 1e-12
    assert abs(seg['thigh'][0] - (pel[0] + ja['hip'][0])) < 1e-12
    assert abs(seg['shank'][0] - (seg['thigh'][0] - ja['knee'][0])) < 1e-12
    assert abs(seg['foot'][0] - (seg['shank'][0] + ja['ankle'][0])) < 1e-12


def test_flexed_knee_is_positive_and_standing_hip_about_ten_degrees_by_design():
    # thigh forward 60 deg, shank straight down: knee flexion +60 deg (1.047 rad)
    assert np.isclose(rb.joint_angles(np.array([0.0]), np.array([math.radians(60)]), np.array([0.0]), np.array([0.0]))['knee'][0],
                      math.radians(60))
    # standing straight: thigh 0, pelvis tilted 10 deg forward means PSIS-ASIS line rises... hip = thigh - pelvis
    pel = rb.pelvis_angle(np.array([[math.cos(math.radians(-10)), math.sin(math.radians(-10)), 0.0]]), np.zeros((1, 3)))
    assert np.isclose(pel[0], math.radians(-10))
    assert np.isclose(rb.joint_angles(pel, np.array([0.0]), np.array([0.0]), np.array([0.0]))['hip'][0], math.radians(10))


def test_central_derivative_uses_real_clock_and_wraps():
    t = np.array([0.0, 0.1, 0.2, 0.4, 0.5])
    x = 2.0 * t
    d = rb.central_derivative(x, t)
    assert np.allclose(d[1:-1], 2.0) and np.isnan(d[0]) and np.isnan(d[-1])
    assert np.isclose(rb.central_derivative(np.array([3.1, 3.1 + 0.1 - 2 * math.pi, 3.1 + 0.2]), np.array([0, 1, 2.0]))[1],
                      (rb.wrap(0.2)) / 2.0)
    x = np.array([1.0, np.nan, 3.0, 4.0])
    d = rb.central_derivative(x, np.arange(4.0))
    assert np.isclose(d[1], 1.0) and np.isnan(d[2]) and np.isnan(d[0])      # only a missing neighbour makes it missing


# ---------------------------------------------------------------------------------------------- foot frame
def _frame(side, yaw=0.0, foot=0.2):
    fwd = ry(yaw) @ np.array([1.0, 0, 0])
    return np.array([fwd]), foot


def test_foot_frame_origin_and_points():
    fwd, phi = _frame('right', yaw=0.8, foot=0.3)
    ankle = np.array([[0.2, 0.1, -0.4]])
    e_f = math.cos(phi) * fwd[0] + math.sin(phi) * UPV
    e_u = -math.sin(phi) * fwd[0] + math.cos(phi) * UPV
    right = np.cross(fwd[0], UPV)
    ph = np.array([phi])
    for leg in ('right', 'left'):
        r = rb.foot_frame_point(ankle, ankle, fwd, ph, leg)                          # the ankle centre itself
        assert np.allclose([r['anterior'][0], r['vertical'][0], r['lateral'][0]], [-0.1, 0, 0])
        r = rb.foot_frame_point(ankle + 0.1 * e_f, ankle, fwd, ph, leg)              # 0.1 m forward along heel to toe
        assert np.allclose([r['anterior'][0], r['vertical'][0], r['lateral'][0]], 0, atol=1e-12)
        r = rb.foot_frame_point(ankle + 0.1 * e_f + 0.03 * e_u, ankle, fwd, ph, leg)
        assert np.isclose(r['vertical'][0], 0.03)
    # outward: +right for the right leg, -right for the left leg
    p = ankle + 0.1 * e_f + 0.02 * right
    assert np.isclose(rb.foot_frame_point(p, ankle, fwd, ph, 'right')['lateral'][0], 0.02)
    assert np.isclose(rb.foot_frame_point(ankle + 0.1 * e_f - 0.02 * right, ankle, fwd, ph, 'left')['lateral'][0], 0.02)


def test_foot_frame_is_unchanged_by_a_rigid_rotation_about_vertical_and_translation():
    fwd, phi = _frame('right', yaw=0.2, foot=-0.1)
    ankle, pt = np.array([[0.0, 0.1, 0.0]]), np.array([[0.15, 0.02, 0.03]])
    base = rb.foot_frame_point(pt, ankle, fwd, np.array([phi]), 'right')
    R, shift = ry(1.3), np.array([[5.0, 0.0, -2.0]])
    moved = rb.foot_frame_point(pt @ R.T + shift, ankle @ R.T + shift, fwd @ R.T, np.array([phi]), 'right')
    for k in base:
        assert np.allclose(base[k], moved[k], atol=1e-12)


def test_cop_mask_reasons():
    cop = {'anterior': np.array([0.0, 0.0, 0.7, 0.0, np.nan, 0.0]), 'vertical': np.zeros(6),
           'lateral': np.array([0.0, 0.0, 0.0, 0.2, 0.0, 0.0])}
    v = np.array([0.5, 0.1, 0.5, 0.5, 0.5, 0.5])
    out, why = rb.mask_cop(cop, v)
    assert np.isfinite(out['anterior']).tolist() == [True, False, False, False, False, True]
    assert why == {'under_contact_threshold': 1, 'nonfinite': 1, 'outside_foot_frame_limits': 2}


# ---------------------------------------------------------------------------------------------- plate ownership
def test_contact_runs_bridge_and_threshold():
    vy = np.zeros(40)
    vy[5:15] = 200
    vy[8:10] = 0.0                       # a 2-sample dip is bridged
    vy[20:25] = 30                       # never above 50 N: not a contact
    vy[30:36] = 500
    assert rb.contact_runs(vy) == [(5, 15), (30, 36)]


def test_left_right_swapped_fixture_gives_the_other_plate_to_each_foot():
    n = 30
    foot_r = np.tile([0.1, 0.0, 0.0], (n, 1))
    foot_l = np.tile([-0.1, 0.0, 0.0], (n, 1))
    # plate A is under the LEFT foot (x = -0.1), plate B under the RIGHT foot: plate order is the opposite of foot order
    A = {'name': 'FP1', 'vy': np.r_[np.zeros(5), np.full(20, 600.0), np.zeros(5)], 'cop': np.tile([-0.09, 0, 0.0], (n, 1))}
    B = {'name': 'FP2', 'vy': np.r_[np.zeros(5), np.full(20, 700.0), np.zeros(5)], 'cop': np.tile([0.11, 0, 0.0], (n, 1))}
    own, un, contacts = rb.assign_plates([A, B], foot_r, foot_l, None, None)
    assert own['left'][:, 0].sum() == 20 and own['right'][:, 1].sum() == 20
    assert own['left'][:, 1].sum() == 0 and own['right'][:, 0].sum() == 0 and not un.any()
    assert [c['rule'] for c in contacts] == ['markers', 'markers']


def test_ambiguous_two_feet_zone_gives_neither_foot_and_is_counted():
    n = 20
    # CoP midway between feet half of the time: left fraction 0.5 is inside (1/3, 2/3)
    foot_r, foot_l = np.tile([0.1, 0, 0.0], (n, 1)), np.tile([-0.1, 0, 0.0], (n, 1))
    cop = np.tile([0.05, 0, 0.0], (n, 1))
    cop[::2, 0] = -0.05
    P = {'name': 'FP3', 'vy': np.full(n, 400.0), 'cop': cop}
    own, un, contacts = rb.assign_plates([P], foot_r, foot_l, None, None)
    assert not own['right'].any() and not own['left'].any() and un.all() and contacts[0]['rule'] == 'ambiguous'


def test_events_fallback_when_markers_cannot_vote_and_tie_stays_unassigned():
    n = 20
    nan3 = np.full((n, 3), np.nan)
    P = {'name': 'FP1', 'vy': np.full(n, 400.0), 'cop': np.zeros((n, 3))}
    st_l = np.zeros(n, bool)
    st_l[2:18] = True
    st_r = np.zeros(n, bool)
    st_r[10:12] = True
    own, un, c = rb.assign_plates([P], nan3, nan3, st_r, st_l)
    assert own['left'].all() and c[0]['rule'] == 'events'
    own, un, c = rb.assign_plates([P], nan3, nan3, None, None)
    assert un.all() and c[0]['rule'] == 'unassigned'


def test_named_treadmill_plates():
    own, un = rb.treadmill_ownership(['Treadmill_R', 'Treadmill_L', 'Other'], 5)
    assert own['right'][:, 0].all() and own['left'][:, 1].all() and not own['right'][:, 1:].any() and not own['left'][:, [0, 2]].any()


def test_event_samples_and_stance():
    t = np.arange(0, 2.0, 0.005)
    hs = np.mod(np.arange(len(t)) * 0.5, 100.0)                      # 0..100 % in 1 s: one drop, at t = 1.0 (sample 200)
    to = np.mod(np.arange(len(t)) * 0.5 + 60.0, 100.0)                # drops at t = 0.4 and 1.4 (samples 80, 280)
    h, o, dropped = rb.event_samples({'Header': t, 'HeelStrike': hs, 'ToeOff': to}, t)
    assert h.tolist() == [200] and o.tolist() == [80, 280] and dropped == 0
    m = rb.stance_mask(len(t), h, o)
    assert m[:80].all()          # before the first toe off, which precedes every heel strike
    assert not m[80:200].any() and m[200:280].all() and not m[280:].any()
    assert rb.event_samples(None, t)[0].size == 0


# ---------------------------------------------------------------------------------------------- forces
@pytest.mark.parametrize('zsign', [-1.0, 1.0])
def test_force_signs_and_outward_sideways_for_both_legs(zsign):
    n = 4
    bw = 700.0
    # person walks along zsign * lab Z; person's right is -zsign * lab X
    right_lab_x = -zsign
    # right foot: ground pushes forward 0.1 BW, outward (to the person's right) 0.05 BW, up 0.5 BW
    def plate(out_dir_x):
        return {'name': 'P', 'vx': np.full(n, out_dir_x * 0.05 * bw), 'vy': np.full(n, 0.5 * bw),
                'vz': np.full(n, zsign * 0.1 * bw), 'cop': np.zeros((n, 3))}
    own = np.ones((n, 1), bool)
    zs = np.full(n, zsign)
    r = rb.foot_forces(own, [plate(right_lab_x)], bw, zs, 'right')
    assert np.allclose(r['vertical_BW'], 0.5) and np.allclose(r['anterior_BW'], 0.1) and np.allclose(r['lateral_BW'], 0.05)
    l = rb.foot_forces(own, [plate(-right_lab_x)], bw, zs, 'left')       # left foot's outward is the person's left
    assert np.allclose(l['anterior_BW'], 0.1) and np.allclose(l['lateral_BW'], 0.05)
    # the opposite push is negative (inward)
    r_in = rb.foot_forces(own, [plate(-right_lab_x)], bw, zs, 'right')
    assert np.allclose(r_in['lateral_BW'], -0.05)


def test_force_sums_over_owned_plates_only_and_cop_is_force_weighted():
    n = 3
    bw = 100.0
    a = {'name': 'A', 'vx': np.zeros(n), 'vy': np.full(n, 300.0), 'vz': np.zeros(n), 'cop': np.tile([0.0, 0, 0.0], (n, 1))}
    b = {'name': 'B', 'vx': np.zeros(n), 'vy': np.full(n, 100.0), 'vz': np.zeros(n), 'cop': np.tile([0.4, 0, 0.0], (n, 1))}
    c = {'name': 'C', 'vx': np.zeros(n), 'vy': np.full(n, 999.0), 'vz': np.zeros(n), 'cop': np.tile([9.0, 0, 0.0], (n, 1))}
    own = np.array([[True, True, False]] * n)
    f = rb.foot_forces(own, [a, b, c], bw, np.full(n, -1.0), 'right')
    assert np.allclose(f['vertical_BW'], 4.0) and np.allclose(f['cop_lab'][:, 0], 0.1)


def test_missing_force_is_missing_not_zero():
    n = 3
    nanp = {'name': 'A', 'vx': np.full(n, np.nan), 'vy': np.full(n, np.nan), 'vz': np.full(n, np.nan), 'cop': np.full((n, 3), np.nan)}
    f = rb.foot_forces(np.ones((n, 1), bool), [nanp], 700.0, np.full(n, -1.0), 'left')
    assert np.isnan(f['vertical_BW']).all() and np.isnan(f['anterior_BW']).all()


def test_contact_zsign_and_45_degree_gate():
    n = 12
    fwd = np.tile([0.0, 0.0, -1.0], (n, 1))
    loaded = np.zeros(n, bool)
    loaded[2:6] = True
    loaded[8:11] = True
    fwd[8:11] = [math.sin(math.radians(60)), 0.0, -math.cos(math.radians(60))]      # 60 deg off Z: gated out
    s, rep = rb.contact_zsign(loaded, fwd)
    assert (s[2:6] == -1).all() and np.isnan(s[8:11]).all() and np.isnan(s[:2]).all()
    assert rep == {'contacts': 2, 'failed_45_degree_gate': 1}


def test_interpolation_never_bridges_a_gap_or_unloaded_plate():
    ts = np.arange(0, 0.02, 0.001)
    y = np.arange(len(ts), dtype=float)
    assert np.allclose(rb.interp_to_clock(np.array([0.0025, 0.01]), ts, y), [2.5, 10.0])
    assert np.isnan(rb.interp_to_clock(np.array([-0.001, 0.5]), ts, y)).all()
    y2 = y.copy()
    y2[3] = np.nan
    assert np.isnan(rb.interp_to_clock(np.array([0.0025]), ts, y2)[0])
    vy = np.zeros(len(ts))
    vy[5:] = 100.0
    cop = np.zeros((len(ts), 3))
    cop[:, 0] = 7.0
    out = rb.interp_cop(np.array([0.0045, 0.0055, 0.005]), ts, cop, vy)
    assert np.isnan(out[0]).all() and np.allclose(out[1], [7, 0, 0]) and np.allclose(out[2], [7, 0, 0])


# ---------------------------------------------------------------------------------------------- body weight
def test_weight_is_kg_only_and_bw_uses_it():
    info = {'variable_names': ['Subject', 'Weight'], 'variable_units': ['', 'kg'], 'values': {'Weight': 74.84}}
    assert rb.weight_kg_from_subject_info(info) == 74.84
    assert rb.body_weight_newton(74.84) == pytest.approx(74.84 * 9.81)
    for bad in ({'variable_names': ['Weight'], 'variable_units': ['lb'], 'values': {'Weight': 165.0}},
                {'variable_names': ['Weight'], 'variable_units': [''], 'values': {'Weight': 74.0}},
                {'variable_names': ['Weight'], 'variable_units': ['kg'], 'values': {'Weight': 7.0}},
                {'variable_names': ['Age'], 'variable_units': [''], 'values': {'Age': 20}}):
        with pytest.raises(rb.RecordingExcluded):
            rb.weight_kg_from_subject_info(bad)


# ---------------------------------------------------------------------------------------------- the scaled model
def osim_text(side, hip_z, kneelat_z):
    s = side
    return f'''<?xml version="1.0"?><OpenSimDocument><Model>
<MarkerSet><objects>
<Marker name="L_ASIS"><socket_parent_frame>/bodyset/pelvis</socket_parent_frame><location>0.1 0 -0.12</location></Marker>
<Marker name="R_ASIS"><socket_parent_frame>/bodyset/pelvis</socket_parent_frame><location>0.1 0 0.12</location></Marker>
<Marker name="L_PSIS"><socket_parent_frame>/bodyset/pelvis</socket_parent_frame><location>-0.08 0.03 -0.05</location></Marker>
<Marker name="R_PSIS"><socket_parent_frame>/bodyset/pelvis</socket_parent_frame><location>-0.08 0.03 0.05</location></Marker>
<Marker name="{s.upper()}_Thigh_Upper"><socket_parent_frame>/bodyset/femur_{s}</socket_parent_frame><location>0.02 -0.1 0.05</location></Marker>
<Marker name="{s.upper()}_Thigh_Front"><socket_parent_frame>/bodyset/femur_{s}</socket_parent_frame><location>0.06 -0.2 0.0</location></Marker>
<Marker name="{s.upper()}_Thigh_Rear"><socket_parent_frame>/bodyset/femur_{s}</socket_parent_frame><location>-0.05 -0.2 -0.02</location></Marker>
<Marker name="{s.upper()}_Knee_Lat"><socket_parent_frame>/bodyset/femur_{s}</socket_parent_frame><location>0 -0.4 {kneelat_z}</location></Marker>
<Marker name="{s.upper()}_Shank_Upper"><socket_parent_frame>/bodyset/tibia_{s}</socket_parent_frame><location>0.02 -0.1 0.05</location></Marker>
<Marker name="{s.upper()}_Shank_Front"><socket_parent_frame>/bodyset/tibia_{s}</socket_parent_frame><location>0.06 -0.2 0.0</location></Marker>
<Marker name="{s.upper()}_Shank_Rear"><socket_parent_frame>/bodyset/tibia_{s}</socket_parent_frame><location>-0.05 -0.2 -0.02</location></Marker>
<Marker name="{s.upper()}_Ankle_Lat"><socket_parent_frame>/bodyset/tibia_{s}</socket_parent_frame><location>0 -0.4 {kneelat_z}</location></Marker>
</objects></MarkerSet>
<JointSet><objects>
<CustomJoint name="hip_{s}"><socket_parent_frame>pelvis_offset</socket_parent_frame><socket_child_frame>femur_{s}_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="pelvis_offset"><socket_parent>../../pelvis</socket_parent><translation>0 -0.08 {hip_z}</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="femur_{s}_offset"><socket_parent>../../femur_{s}</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames></CustomJoint>
<CustomJoint name="knee_{s}"><socket_parent_frame>femur_{s}_offset</socket_parent_frame><socket_child_frame>tibia_{s}_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="femur_{s}_offset"><socket_parent>../../femur_{s}</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="tibia_{s}_offset"><socket_parent>../../tibia_{s}</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames>
 <SpatialTransform><TransformAxis name="rotation1"><coordinates>knee_angle_{s}</coordinates><axis>0 0 1</axis><LinearFunction name="function"><coefficients> 1 0</coefficients></LinearFunction></TransformAxis>
 <TransformAxis name="rotation2"><coordinates></coordinates><axis>0 1 0</axis><Constant name="function"><value>0</value></Constant></TransformAxis>
 <TransformAxis name="translation1"><coordinates>knee_angle_{s}</coordinates><axis>1 0 0</axis><SimmSpline name="function"><x>-2 -1 0 1</x><y>0 0 0 0</y></SimmSpline></TransformAxis>
 <TransformAxis name="translation2"><coordinates>knee_angle_{s}</coordinates><axis>0 1 0</axis><MultiplierFunction name="function"><function><SimmSpline name="function"><x>-2 -1 0 1</x><y>-0.21 -0.205 -0.20 -0.195</y></SimmSpline></function><scale>2.0</scale></MultiplierFunction></TransformAxis>
 <TransformAxis name="translation3"><coordinates></coordinates><axis>0 0 1</axis><Constant name="function"><value>0</value></Constant></TransformAxis></SpatialTransform></CustomJoint>
<CustomJoint name="ankle_{s}"><socket_parent_frame>tibia_{s}_offset</socket_parent_frame><socket_child_frame>talus_{s}_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="tibia_{s}_offset"><socket_parent>../../tibia_{s}</socket_parent><translation>0 -0.4 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="talus_{s}_offset"><socket_parent>../../talus_{s}</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames></CustomJoint>
</objects></JointSet></Model></OpenSimDocument>'''


def osim_both():
    """One model text carrying both legs: the right model plus the left side's own markers and joints."""
    r, l = osim_text('r', 0.08, 0.05), osim_text('l', -0.08, -0.05)
    l_markers = ''.join(line + '\n' for line in l.split('\n') if line.startswith('<Marker name="L_') and 'ASIS' not in line and 'PSIS' not in line)
    l_joints = l.split('<JointSet><objects>')[1].split('</objects></JointSet>')[0]
    r = r.replace('</objects></MarkerSet>', l_markers + '</objects></MarkerSet>', 1)
    return r.replace('</objects></JointSet>', l_joints + '</objects></JointSet>', 1)


def test_model_geometry_parses_opensim4_text_and_refuses_entities():
    g = rb.model_geometry(osim_text('r', 0.08, 0.05), 'r')
    assert np.allclose(g['hip_in_pelvis'], [0, -0.08, 0.08]) and np.allclose(g['knee_in_femur'], 0) and len(g['knee_translations']) == 3
    assert np.allclose(g['ankle_in_tibia'], [0, -0.4, 0]) and np.allclose(g['knee_axis_in_femur'], [0, 0, 1])
    assert g['markers']['R_Ankle_Lat'][0] == 'tibia_r'
    with pytest.raises(KeyError):
        rb.model_geometry(osim_text('r', 0.08, 0.05), 'l')
    with pytest.raises(ValueError):
        rb.parse_osim('<!DOCTYPE x [<!ENTITY a "b">]><x/>')


def test_euler_orientation_rotates_the_knee_axis():
    text = osim_text('r', 0.08, 0.05).replace('<orientation>0 0 0</orientation></PhysicalOffsetFrame>\n <PhysicalOffsetFrame name="tibia_r_offset">'
                                              '<socket_parent>../../tibia_r</socket_parent><translation>0 0 0',
                                              '<orientation>1.5707963267948966 0 0</orientation></PhysicalOffsetFrame>\n <PhysicalOffsetFrame name="tibia_r_offset">'
                                              '<socket_parent>../../tibia_r</socket_parent><translation>0 0 0', 1)
    g = rb.model_geometry(text, 'r')
    assert np.allclose(g['knee_axis_in_femur'], [0, -1, 0], atol=1e-12)        # Rx(90 deg) maps z to -y


# ---------------------------------------------------------------------------------------------- a whole synthetic recording
def build_walker(yaw, n=12, pelvis_tilt=0.1, thigh=(0.4, -0.3), shank=(-0.1, 0.1), foot=(0.0, 0.0), mass=70.0):
    """Marker, plate, gait and id tables for a person standing with imposed segment angles, at 200 Hz, treadmill-style
    named plates. Body frames: x forward, y up (proximal), z right; imposed angle a is a rotation about z (counterclockwise,
    distal end forward)."""
    models = {s: osim_text(s, 0.08 if s == 'r' else -0.08, 0.05 if s == 'r' else -0.05) for s in 'rl'}
    geo = {s: rb.model_geometry(models[s], s) for s in 'rl'}
    Ry = ry(yaw)
    Rbase = Ry @ R0
    pel_origin = np.array([0.0, 1.0, 0.0])
    Rp = Rbase @ rz(pelvis_tilt)
    mk = {}
    def put(name, lab):
        for k, a in enumerate('xyz'):
            mk[f'{name}_{a}'] = np.full(n, lab[k] * 1000.0)
    for name in rb.PELVIS_MARKERS:
        put(name, pel_origin + Rp @ geo['r']['markers'][name][1])
    truth = {}
    for i, (s, leg) in enumerate((('r', 'right'), ('l', 'left'))):
        S = s.upper()
        hip = pel_origin + Rp @ geo[s]['hip_in_pelvis']
        Rf = Rbase @ rz(thigh[i])
        knee = hip + Rf @ -geo[s]['hip_in_pelvis'] * 0   # femur origin = hip centre (child offset 0)
        femur_origin = hip
        q = shank[i] - thigh[i]                      # OpenSim knee coordinate: flexion negative
        knee = femur_origin + Rf @ np.array([0.0, -0.40 + 0.01 * q, 0.0])
        Rt = Rbase @ rz(shank[i])
        tibia_origin = knee
        ankle = tibia_origin + Rt @ geo[s]['ankle_in_tibia']
        for m in rb.THIGH_CLUSTER:
            put(f'{S}_{m}', femur_origin + Rf @ geo[s]['markers'][f'{S}_{m}'][1])
        for m in rb.SHANK_CLUSTER:
            put(f'{S}_{m}', tibia_origin + Rt @ geo[s]['markers'][f'{S}_{m}'][1])
        fwd = Rbase @ np.array([1.0, 0, 0])
        e_f = math.cos(foot[i]) * fwd + math.sin(foot[i]) * UPV
        heel = ankle - 0.08 * UPV - 0.1 * e_f
        put(f'{S}_Heel', heel)
        put(f'{S}_Toe_Tip', heel + 0.25 * e_f)
        truth[leg] = dict(ankle=ankle, knee=knee, hip=hip, e_f=e_f, fwd=fwd)
    t = np.arange(n) / 200.0
    markers = {'Header': t, **mk}
    ft = np.arange(5 * (n - 1) + 1) / 1000.0
    bw = mass * 9.81
    fp = {'Header': ft}
    right_axis = np.cross(truth['right']['fwd'], UPV)
    for leg, plate in (('right', 'Treadmill_R'), ('left', 'Treadmill_L')):
        tr = truth[leg]
        out = 1.0 if leg == 'right' else -1.0
        cop = tr['ankle'] + 0.13 * tr['e_f'] - 0.08 * UPV + out * 0.02 * right_axis     # foot frame (0.03, -0.08 [flat], 0.02)
        force = 0.5 * bw * UPV + 0.1 * bw * tr['fwd'] + out * 0.05 * bw * right_axis
        for k, a in enumerate('xyz'):
            fp[f'{plate}_v{a}'] = np.full(len(ft), force[k])
            fp[f'{plate}_p{a}'] = np.full(len(ft), cop[k])
    idt = {'Header': t, 'hip_flexion_r_moment': np.full(n, 35.0), 'knee_angle_r_moment': np.full(n, 14.0),
           'ankle_angle_r_moment': np.full(n, 7.0), 'hip_flexion_l_moment': np.full(n, -35.0),
           'knee_angle_l_moment': np.full(n, -14.0), 'ankle_angle_l_moment': np.full(n, -7.0)}
    return markers, fp, idt, geo, mass


@pytest.mark.parametrize('yaw', [0.0, 1.1, -2.0])
def test_recording_known_angles_forces_and_cop(yaw):
    thigh, shank, foot = (0.4, -0.3), (-0.1, 0.1), (0.0, 0.0)
    markers, fp, idt, geo, mass = build_walker(yaw, thigh=thigh, shank=shank, foot=foot)
    cols, led = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    pel = 0.1 + math.atan2(-0.03, 0.18)        # imposed tilt plus the model's own mid-PSIS to mid-ASIS offset (hand computed)
    # mid-ASIS (0.1, 0) and mid-PSIS (-0.08, 0.03): rotated by the imposed 0.1 rad
    assert np.allclose(cols['pelvis_sagittal_angle_rad'], pel, atol=1e-9)
    for i, leg in enumerate(('right', 'left')):
        assert np.allclose(cols[f'thigh_sagittal_angle_{leg}_rad'], thigh[i], atol=1e-9)
        assert np.allclose(cols[f'shank_sagittal_angle_{leg}_rad'], shank[i], atol=1e-9)
        assert np.allclose(cols[f'foot_sagittal_angle_{leg}_rad'], foot[i], atol=1e-9)
        assert np.allclose(cols[f'knee_flexion_angle_{leg}_rad'], thigh[i] - shank[i], atol=1e-9)
        assert np.allclose(cols[f'hip_flexion_angle_{leg}_rad'], thigh[i] - pel, atol=1e-9)
        assert np.allclose(cols[f'ankle_dorsiflexion_angle_{leg}_rad'], foot[i] - shank[i], atol=1e-9)
        assert np.allclose(cols[f'knee_flexion_velocity_{leg}_rad_s'][1:-1], 0.0, atol=1e-9)
        # plates: walking along -Z lab at yaw 0 ... forces were built along the person's forward and right axes, so
        # they come back as +0.5 BW vertical, +0.1 anterior and +0.05 outward whatever the heading allows
        assert np.allclose(cols[f'grf_vertical_{leg}_BW'], 0.5, atol=1e-9)
        # CoP in the ankle frame: (0.03, -0.08, 0.02) as built
        assert np.allclose(cols[f'cop_anterior_{leg}_m'], 0.03, atol=1e-9)
        assert np.allclose(cols[f'cop_vertical_{leg}_m'], -0.08, atol=1e-9)
        assert np.allclose(cols[f'cop_lateral_{leg}_m'], 0.02, atol=1e-9)
    assert led['legs']['right']['cop_masked']['under_contact_threshold'] == 0
    # the two routes to the knee agree (femur fit through the spline translation, tibia fit): imposed geometry is exact
    for leg in ('right', 'left'):
        assert led['fit'][leg]['knee_route_gap_mm']['max'] < 1e-6
        # the model's knee axis points at the lateral knee marker's side: angle ~0 (marker lies on the axis through the knee)
        assert led['fit'][leg]['knee_axis_vs_lateral_marker_deg']['max'] < 1.0
    # moments: Nm / 70 kg; knee flexor is minus the knee_angle moment
    assert np.allclose(cols['hip_flexion_moment_right_Nm_kg'], 0.5) and np.allclose(cols['knee_flexion_moment_right_Nm_kg'], -0.2)
    assert np.allclose(cols['ankle_dorsiflexion_moment_left_Nm_kg'], -0.1)
    assert led['body_weight_N'] == pytest.approx(70.0 * 9.81)


def test_recording_force_direction_is_gated_by_45_degrees_of_lab_z():
    # yaw 0 puts forward on -Z: anterior and lateral exist. Yaw 60 deg is outside the gate: forces stay missing, vertical stays.
    markers, fp, idt, geo, mass = build_walker(0.0)
    cols, _ = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    assert np.allclose(cols['grf_anterior_right_BW'], 0.1) and np.allclose(cols['grf_lateral_right_BW'], 0.05)
    assert np.allclose(cols['grf_lateral_left_BW'], 0.05)
    markers, fp, idt, geo, mass = build_walker(math.radians(60))
    cols, led = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    assert np.isnan(cols['grf_anterior_right_BW']).all() and np.allclose(cols['grf_vertical_right_BW'], 0.5)
    assert led['legs']['right']['z_gate']['failed_45_degree_gate'] == 1
    markers, fp, idt, geo, mass = build_walker(math.pi)           # walking along +Z: still outward positive
    cols, _ = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    assert np.allclose(cols['grf_anterior_left_BW'], 0.1) and np.allclose(cols['grf_lateral_left_BW'], 0.05)
    assert np.allclose(cols['grf_lateral_right_BW'], 0.05)


def test_recording_missing_marker_is_a_listed_exclusion_and_nan_frames_stay_nan():
    markers, fp, idt, geo, mass = build_walker(0.0)
    bad = {k: v for k, v in markers.items() if not k.startswith('R_Heel')}
    with pytest.raises(rb.RecordingExcluded, match='missing_markers: R_Heel_x'.replace('R_Heel_x', 'R_Heel')):
        rb.process_recording(bad, fp, None, None, idt, geo, mass, 'treadmill')
    markers['R_Knee_Lat_x'][4] = np.nan                           # one fit marker missing for one frame
    cols, _ = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    assert np.isnan(cols['thigh_sagittal_angle_right_rad'][4]) and np.isfinite(cols['thigh_sagittal_angle_right_rad'][5])
    assert np.isfinite(cols['thigh_sagittal_angle_left_rad'][4])


def test_recording_without_plates_or_moments_keeps_columns_missing_with_reason():
    markers, fp, idt, geo, mass = build_walker(0.0)
    cols, led = rb.process_recording(markers, None, None, None, None, geo, mass, 'levelground')
    assert np.isnan(cols['grf_vertical_right_BW']).all() and np.isnan(cols['cop_anterior_left_m']).all()
    assert led['plates']['unavailable_reason'] == 'no_plate_channels' and led['moments']['available'] is False
    assert np.isnan(cols['knee_flexion_moment_left_Nm_kg']).all()


def test_recording_scale_check_catches_wrong_units():
    markers, fp, idt, geo, mass = build_walker(0.0)
    big = {k: (v * 1000.0 if k != 'Header' else v) for k, v in markers.items()}
    with pytest.raises(rb.RecordingExcluded, match='marker_scale'):
        rb.process_recording(big, fp, None, None, idt, geo, mass, 'treadmill')


def test_overground_swapped_plates_end_to_end():
    # two plates in the opposite order to the feet: FP1 under the left foot, FP2 under the right foot
    markers, fp, idt, geo, mass = build_walker(0.0)
    tm = {k: v for k, v in fp.items()}
    swapped = {'Header': tm['Header']}
    for a in 'xyz':
        for q in 'vp':
            swapped[f'FP1_{q}{a}'] = tm[f'Treadmill_L_{q}{a}']
            swapped[f'FP2_{q}{a}'] = tm[f'Treadmill_R_{q}{a}']
    cols, led = rb.process_recording(markers, swapped, None, None, idt, geo, mass, 'levelground')
    assert np.allclose(cols['grf_vertical_left_BW'], 0.5) and np.allclose(cols['grf_vertical_right_BW'], 0.5)
    assert led['plates']['assignment']['by_rule']['markers'] == 2
    assert np.allclose(cols['cop_lateral_left_m'], 0.02, atol=1e-9) and np.allclose(cols['cop_lateral_right_m'], 0.02, atol=1e-9)


# ---------------------------------------------------------------------------------------------- runner (fake reader)
def test_runner_writes_parquet_ledger_and_never_stops_on_a_bad_recording(tmp_path):
    import json
    import pyarrow.parquet as pq
    from contributor_tools import run_gt21_rb_pass as run
    markers, fp, idt, geo, mass = build_walker(0.0)
    root = tmp_path / 'src' / 'ABxx'
    (root / 'osimxml').mkdir(parents=True)
    (root / 'osimxml' / 'ABxx.osim').write_text(osim_both())
    labels = tmp_path / 'labels' / 'ABxx'
    labels.mkdir(parents=True)
    (labels / 'subject_info_ABxx.json').write_text(json.dumps(
        {'variable_names': ['Weight'], 'variable_units': ['kg'], 'values': {'Weight': mass}}))
    tables = {'markers': markers, 'fp': fp, 'gcLeft': None, 'gcRight': None, 'id': idt}

    def reader(path):
        ch = path.parent.name
        if path.stem == 'broken':
            raise ValueError('unsupported layout')
        if tables[ch] is None:
            raise FileNotFoundError(path)
        return tables[ch]

    roots = {'t': tmp_path / 'src'}
    out = tmp_path / 'out'
    good = {'subject': 'ABxx', 'session': 's', 'mode': 'treadmill', 'recording': 'treadmill_01_01', 'source': 't'}
    bad = dict(good, recording='broken')
    cache = {}
    e1 = run.process_one(good, out, read=reader, roots=roots, labels=tmp_path / 'labels', geometry_cache=cache)
    e2 = run.process_one(bad, out, read=reader, roots=roots, labels=tmp_path / 'labels', geometry_cache=cache)
    assert e1['status'] == 'converted' and e2['status'] == 'excluded' and 'markers unreadable' in e2['reason']
    t = pq.read_table(out / 'ABxx' / 'treadmill' / 'treadmill_01_01.parquet')
    assert t.num_rows == 12 and 'cop_lateral_left_m' in t.column_names and t.column_names[0] == 'time_s'
    assert e1['channel_read_errors'].keys() == {'gcLeft', 'gcRight'}            # unreadable optional channels are listed
    again = run.process_one(good, out, read=reader, roots=roots, labels=tmp_path / 'labels', geometry_cache=cache)
    assert again['status'] == 'excluded' and 'FileExistsError' in again['reason']  # exclusive create, no overwrite


def test_pilot_records_cover_each_mode_and_a_new_participant_with_a_fixed_seed():
    from contributor_tools import run_gt21_rb_pass as run
    inv = {}
    for s in ('AB06', 'AB17'):
        for m in run.MODES:
            for k in range(1, 6):
                inv[(s, m, f'{m}_{k:02d}')] = {}
    inv[('AB06', 'levelground', 'levelground_ccw_fast_01_01')] = {}
    inv[('AB06', 'treadmill', 'treadmill_01_01')] = {}
    inv[('AB06', 'stair', 'stair_1_l_01_02')] = {}
    a, b = run.pilot_records(inv), run.pilot_records(inv)
    assert a == b and len(a) == 5 and [x.split('/')[1] for x in a] == ['levelground', 'treadmill', 'ramp', 'stair', 'treadmill']
    assert a[0].endswith('levelground_ccw_fast_01_01') and a[3].endswith('stair_1_l_01_02') and a[4].startswith('AB17/')


# ---------------------------------------------------------------------------------------------- per-frame geometry hold
def test_geometry_hold_codes_and_thresholds():
    res_a = np.array([0.0, 0.0199, 0.0201, 0.05, np.nan, 0.001])
    res_b = np.array([0.001, 0.001, 0.001, 0.001, 0.001, 0.001])
    ang = np.radians(np.array([10.0, 44.9, 45.1, 90.0, np.nan, 120.0]))
    code = rb.geometry_hold([res_a, res_b], ang)
    assert code.tolist() == [0, 0, 1 | 2, 1 | 2, 0, 2]          # NaN never counts; exactly at the limit is kept
    assert rb.geometry_hold([res_a, res_b], None).tolist() == [0, 0, 1, 1, 0, 0]       # axis check absent: residual only
    assert rb.HOLD_RESIDUAL_M == 0.020 and np.isclose(np.degrees(rb.HOLD_AXIS_RAD), 45.0)


def test_recording_holds_a_leg_on_a_bad_fit_frame_and_keeps_force_and_the_other_leg():
    markers, fp, idt, geo, mass = build_walker(0.3)
    markers['R_Thigh_Rear_y'][5] += 80.0                           # one marker 80 mm off in one frame: residual well over 20 mm
    markers['L_Shank_Front_x'][8] += 5.0                           # 5 mm: stays under the limit, not held
    cols, led = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    h = led['fit']['right']['geometry_hold']
    assert h['held_frames'] == 1 and h['by_residual'] == 1 and h['by_axis'] == 0 and cols['geometry_hold_right'][5] == 1
    assert led['fit']['left']['geometry_hold']['held_frames'] == 0 and not cols['geometry_hold_left'].any()
    for name in ('thigh_sagittal_angle_right_rad', 'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad',
                 'ankle_dorsiflexion_angle_right_rad', 'cop_anterior_right_m', 'cop_lateral_right_m'):
        assert np.isnan(cols[name][5]) and np.isfinite(cols[name][4])
    # speeds are derived from the held angle: missing at the frame and at both neighbours, finite further out
    v = cols['knee_flexion_velocity_right_rad_s']
    assert np.isnan(v[4:7]).all() and np.isfinite(v[2]) and np.isfinite(v[8])
    assert np.isfinite(cols['grf_vertical_right_BW'][5]) and np.isfinite(cols['hip_flexion_moment_right_Nm_kg'][5])
    assert np.isfinite(cols['pelvis_sagittal_angle_rad'][5])
    assert np.isfinite(cols['thigh_sagittal_angle_left_rad'][8])


def test_recording_ledger_has_height_diagnostics_that_separate_fit_from_marker():
    markers, fp, idt, geo, mass = build_walker(0.0)
    cols, led = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    L = led['legs']['right']
    # imposed: ankle 0.08 m above the CoP at flat foot; the heel marker was placed 0.08 m below the ankle centre
    assert L['ankle_height_above_plate_flat_foot_m']['median'] == pytest.approx(0.08, abs=1e-9)
    assert L['heel_marker_above_plate_flat_foot_m']['median'] == pytest.approx(0.0, abs=1e-9)
    assert L['model_ankle_in_tibia_m'] == [0.0, -0.4, 0.0]


def test_readback_checks_pass_on_a_synthetic_batch_and_catch_a_leak(tmp_path):
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools import run_gt21_rb_readback as rbk
    markers, fp, idt, geo, mass = build_walker(0.3)
    markers['R_Thigh_Rear_y'][5] += 80.0
    cols, led = rb.process_recording(markers, fp, None, None, idt, geo, mass, 'treadmill')
    entry = dict(led, n_samples=led['n_samples'], plates=led['plates'])
    path = tmp_path / 'r.parquet'
    pq.write_table(pa.table({k: pa.array(v) for k, v in cols.items()}), path)
    res, back = rbk.check_stored(path, entry)
    assert res['ok'] and res['held_frames_with_values'] == 0 and res['composition_max_abs_error_rad'] <= 1e-12
    leaked = dict(cols)
    leaked['thigh_sagittal_angle_right_rad'] = np.where(np.arange(12) == 5, 0.1, cols['thigh_sagittal_angle_right_rad'])
    pq.write_table(pa.table({k: pa.array(v) for k, v in leaked.items()}), tmp_path / 'l.parquet')
    assert not rbk.check_stored(tmp_path / 'l.parquet', entry)[0]['ok']        # a value inside a held frame is caught
