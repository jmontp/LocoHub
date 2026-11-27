"""Tests for the GT21 knee-centre analysis (A5). DRAFT: written in phase 1, not run.

All inputs are SYNTHETIC: imposed geometry with hand-computed answers (the walker fixture of test_gt21_rb_pass.py, a tiny
hand-written model text). None is GT21 data. They test the arithmetic and bookkeeping, not the scientific question.
"""
import math

import numpy as np
import pytest

from contributor_tools import analyze_gt21_knee_centre as k
from contributor_tools import build_gt21_knee_centre_specs as specs

D = 180.0 / math.pi


# ---------------------------------------------------------------------------------------------- frames and offsets
def test_segment_frame_and_offsets_by_hand():
    hip, knee, fwd = np.array([[0.0, 0.9, 0.0]]), np.array([[0.0, 0.5, 0.0]]), np.array([[1.0, 0.0, 0.0]])
    frame = k.segment_frame(hip, knee, fwd)
    assert np.allclose(frame[0], [[0, -1, 0]]) and np.allclose(frame[1], [[1, 0, 0]]) and np.allclose(frame[2], [[0, 0, 1]])
    # model centre 10 mm in front of, 5 mm above, and 3 mm to the right of the marker estimate
    model = np.array([[0.010, 0.500, 0.003]])
    est = np.array([[0.0, 0.495, 0.0]])
    o = k.offset_in_frame(model, est, frame)
    assert o['ap'][0] == pytest.approx(10.0) and o['pd'][0] == pytest.approx(-5.0) and o['ml'][0] == pytest.approx(3.0)
    assert o['sag'][0] == pytest.approx(math.hypot(10.0, 5.0)) and o['d3'][0] == pytest.approx(math.sqrt(100 + 25 + 9))


def test_frame_anterior_is_made_perpendicular_to_a_tilted_long_axis():
    hip, knee, fwd = np.array([[0.0, 0.0, 0.0]]), np.array([[0.3, -0.4, 0.0]]), np.array([[1.0, 0.0, 0.0]])
    e_pd, e_ap, e_r = k.segment_frame(hip, knee, fwd)
    assert np.allclose(e_pd, [[0.6, -0.8, 0.0]]) and abs(float(np.sum(e_pd * e_ap))) < 1e-12
    assert np.allclose(e_ap, [[0.8, 0.6, 0.0]])       # forward minus its component along the long axis, normalised


def test_lateral_unit_and_marker_centre_by_hand():
    right, long_axis = np.array([[0.0, 0.0, 1.0]]), np.array([[0.0, -0.4, 0.0]])
    assert np.allclose(k.lateral_unit(right, long_axis, 'right'), [[0, 0, 1]])
    assert np.allclose(k.lateral_unit(right, long_axis, 'left'), [[0, 0, -1]])
    # lateral marker 60 mm to the right of the leg line; width 90 mm -> estimate 45 mm medial of the marker: 15 mm right of the line
    c = k.marker_centre(np.array([[0.0, 0.5, 0.060]]), k.lateral_unit(right, long_axis, 'right'), 0.045)
    assert np.allclose(c, [[0.0, 0.5, 0.015]])
    # a base parallel to the long axis has no lateral direction: NaN, not a guess
    assert np.isnan(k.lateral_unit(np.array([[0.0, 1.0, 0.0]]), long_axis, 'right')).all()


def test_degrees_per_mm_and_classification_rules():
    assert k.deg_per_mm_ap(0.4, 0.4) == pytest.approx(5.0e-3 * D)           # (1/0.4 + 1/0.4) per metre, per mm
    assert k.classify(0.9, 0.8, 1.5) == 'geometry_biased'
    assert k.classify(0.1, 0.1, 6.0) == 'posture_real'
    assert k.classify(0.9, 0.9, 5.5) == 'posture_real'                      # marker route still stands flexed
    assert k.classify(0.5, 0.4, 3.5) == 'mixed'
    assert k.classify(float('nan'), 0.5, 1.0) == 'not_determined'


# ---------------------------------------------------------------------------------------------- strides and sampling
def test_stride_windows_use_20_to_35_percent_and_skip_bad_strides():
    t = np.arange(0, 3.3, 0.01)
    w = k.stride_windows([0, 100, 200, 230], t)          # last stride is 0.3 s: outside the duration window
    assert len(w) == 2
    assert w[0][0] == 20 and w[0][-1] == 35 and w[1][0] == 120 and w[1][-1] == 135


def test_sample_items_is_seeded_ordered_and_bounded():
    import random
    a = k.sample_items(range(20), 4, random.Random(5))
    b = k.sample_items(range(20), 4, random.Random(5))
    assert a == b == sorted(a) and len(a) == 4 and len(set(a)) == 4
    assert k.sample_items([1, 2], 4, random.Random(5)) == [1, 2]


# ---------------------------------------------------------------------------------------------- the model alone
def synthetic_osim(ankle=(0.0, -0.4, 0.0), knee_translation_y_slope=0.01):
    """A one-leg OpenSim 4 style text: hip child offset 0, knee parent offset 0, knee y translation = -0.4 + slope * q (a
    spline through exactly linear data, scaled), ankle at the given tibia location, flexion axis z."""
    y = [(-0.2 + 0.5 * knee_translation_y_slope * q) for q in (-2, -1, 0, 1)]
    ys = ' '.join(f'{v:.6f}' for v in y)
    return f'''<?xml version="1.0"?><OpenSimDocument><Model><JointSet><objects>
<CustomJoint name="hip_r"><socket_parent_frame>pelvis_offset</socket_parent_frame><socket_child_frame>femur_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="pelvis_offset"><socket_parent>../../pelvis</socket_parent><translation>0 -0.08 0.08</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="femur_r_offset"><socket_parent>../../femur_r</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames></CustomJoint>
<CustomJoint name="knee_r"><socket_parent_frame>femur_r_offset</socket_parent_frame><socket_child_frame>tibia_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="femur_r_offset"><socket_parent>../../femur_r</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="tibia_r_offset"><socket_parent>../../tibia_r</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames>
 <SpatialTransform><TransformAxis name="rotation1"><coordinates>knee_angle_r</coordinates><axis>0 0 1</axis><LinearFunction name="function"><coefficients> 1 0</coefficients></LinearFunction></TransformAxis>
 <TransformAxis name="translation1"><coordinates>knee_angle_r</coordinates><axis>1 0 0</axis><SimmSpline name="function"><x>-2 -1 0 1</x><y>0 0 0 0</y></SimmSpline></TransformAxis>
 <TransformAxis name="translation2"><coordinates>knee_angle_r</coordinates><axis>0 1 0</axis><MultiplierFunction name="function"><function><SimmSpline name="function"><x>-2 -1 0 1</x><y>{ys}</y></SimmSpline></function><scale>2.0</scale></MultiplierFunction></TransformAxis>
 </SpatialTransform></CustomJoint>
<CustomJoint name="ankle_r"><socket_parent_frame>tibia_r_offset</socket_parent_frame><socket_child_frame>talus_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="tibia_r_offset"><socket_parent>../../tibia_r</socket_parent><translation>{ankle[0]} {ankle[1]} {ankle[2]}</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="talus_r_offset"><socket_parent>../../talus_r</socket_parent><translation>0 0 0</translation><orientation>0 0 0</orientation></PhysicalOffsetFrame></frames></CustomJoint>
</objects></JointSet></Model></OpenSimDocument>'''


def test_model_with_straight_centre_lines_has_no_neutral_offset_and_coupled_knee():
    info = k.inspect_model(synthetic_osim(), 'r', ik_knee_raw_deg=-20.0)
    assert info['neutral_lh_knee_deg'] == pytest.approx(0.0, abs=1e-9)
    assert info['knee_coupled'] is True and 'spline' in info['translation_function_kinds'] or 'scaled' in info['translation_function_kinds']
    assert info['flexion_sign_check_slope'] == pytest.approx(1.0, abs=1e-2)
    # y translation is 2 * (-0.2 + 0.005 q) with q in radians: over +10 to -60 degrees it moves 2 * 0.005 * (0.17453 + 1.04720) m
    assert info['translation_range_mm'][1] == pytest.approx(10.0 * (0.174533 + 1.047198), rel=1e-3)
    assert info['translation_range_mm'][0] == pytest.approx(0.0, abs=1e-9)
    assert info['knee_axis_tilt_from_lateral_deg'] == pytest.approx(0.0, abs=1e-9)
    assert info['knee_parent_rotation_about_flexion_axis_deg'] == pytest.approx(0.0, abs=1e-9)
    # the thigh line is vertical (x translation is zero) and the shank line is the knee rotated by q: knee flexion = -q
    assert info['model_offset_at_ik_deg'] == pytest.approx(0.0, abs=1e-6)


def test_tilted_ankle_location_gives_a_neutral_flexion_offset_that_carries_through():
    # ankle 5 degrees behind the tibia's down direction: centre lines are 5 degrees flexed at q = 0, by hand
    a = (-0.4 * math.sin(math.radians(5)), -0.4 * math.cos(math.radians(5)), 0.0)
    info = k.inspect_model(synthetic_osim(ankle=a), 'r', ik_knee_raw_deg=-20.0)
    assert info['neutral_lh_knee_deg'] == pytest.approx(5.0, abs=1e-6)
    assert info['model_offset_at_ik_deg'] == pytest.approx(5.0, abs=1e-6)          # thigh stays vertical; shank angle = -(5 + 20)
    assert info['model_lh_knee_deg_over_q'][info['q_grid_deg'].index(-20.0)] == pytest.approx(25.0, abs=1e-6)


def test_model_knee_flexion_forward_shift_of_the_joint_point_by_hand():
    info = k.inspect_model(synthetic_osim(), 'r')
    info['_translations'] = [('knee_angle_r', np.array([1.0, 0.0, 0.0]), ('constant', 0.010)),
                             ('knee_angle_r', np.array([0.0, 1.0, 0.0]), ('constant', -0.400))]
    # joint point 10 mm in front of the hip line, 400 mm below the hip; shank straight below it: thigh tilts forward by atan(0.01/0.4)
    assert k.model_knee_flexion(info, [0.0])[0] == pytest.approx(math.degrees(math.atan2(0.010, 0.400)), abs=1e-9)
    # a flexion axis of -z (pointing left) is turned to the person's right before the sign is taken
    info['_axis_parent'] = np.array([0.0, 0.0, -1.0])
    assert k.model_knee_flexion(info, [0.0])[0] == pytest.approx(math.degrees(math.atan2(0.010, 0.400)), abs=1e-9)


def test_compare_models_subtracts_generic_from_scaled():
    s = k.public(k.inspect_model(synthetic_osim(ankle=(-0.03, -0.399, 0.0)), 'r'))
    g = k.public(k.inspect_model(synthetic_osim(), 'r'))
    d = k.compare_models(s, g)
    assert d['neutral_lh_knee_diff_deg'] == pytest.approx(s['neutral_lh_knee_deg'] - g['neutral_lh_knee_deg'])
    assert d['neutral_lh_knee_diff_deg'] > 4.0 and d['knee_child_location_norm_diff_mm'] == pytest.approx(0.0)
    assert not any(key.startswith('_') for key in s)


# ---------------------------------------------------------------------------------------------- whole synthetic recording
def _walker():
    import test_gt21_rb_pass as t          # same tests folder; synthetic fixture only
    return t


def test_marker_route_equals_model_route_when_markers_sit_on_the_model_centre():
    t = _walker()
    # thigh = shank angle for each leg: knee coordinate 0, so the model's knee centre sits level with its lateral marker
    markers, fp, idt, geo, mass = t.build_walker(0.0, thigh=(0.2, 0.1), shank=(0.2, 0.1))
    # the model puts the lateral markers 50 mm lateral of the knee and ankle centres, so a 100 mm width reproduces the centres
    res, route = k.leg_results(markers, geo, hw_knee=0.100, hw_ankle=0.100)
    assert route == 'pass_unchanged'
    for leg in ('right', 'left'):
        r = res[leg]
        for key in ('knee_ap', 'knee_pd', 'knee_ml', 'ankle_ap', 'ankle_pd', 'ankle_ml'):
            assert np.allclose(r['off'][key], 0.0, atol=1e-6), (leg, key)
        assert np.allclose(r['off']['hw_knee_model'], 50.0, atol=1e-6) and np.allclose(r['off']['hw_ankle_model'], 50.0, atol=1e-6)
        for q in k.ANGLES:
            assert np.allclose(r['angles']['both_marker'][q], r['angles']['model'][q], atol=1e-6)
        assert not r['held'].any()
    # imposed angles: thigh = shank, so the knee flexion is zero and the thigh angle is the imposed one
    assert np.allclose(res['right']['angles']['model']['knee'], 0.0, atol=1e-6)
    assert np.allclose(res['right']['angles']['model']['thigh'], 0.2 * D, atol=1e-6)


def test_a_narrower_width_moves_the_estimate_across_the_plane_not_along_the_leg():
    t = _walker()
    markers, fp, idt, geo, mass = t.build_walker(0.0, thigh=(0.2, 0.1), shank=(0.2, 0.1))
    res, _ = k.leg_results(markers, geo, hw_knee=0.080, hw_ankle=0.080)
    # estimate 40 mm medial of the marker, model 50 mm: model minus estimate is 10 mm medial: leftward for the right leg
    assert np.allclose(res['right']['off']['knee_ml'], -10.0, atol=1e-6) and np.allclose(res['left']['off']['knee_ml'], 10.0, atol=1e-6)
    assert np.allclose(res['right']['off']['knee_sag'], 0.0, atol=1e-6)
    assert np.allclose(res['right']['angles']['both_marker']['knee'], res['right']['angles']['model']['knee'], atol=1e-6)


def test_marker_anterior_to_the_model_centre_changes_thigh_shank_and_knee_by_hand():
    t = _walker()
    thigh, shank = 0.4, -0.1
    markers, fp, idt, geo, mass = t.build_walker(0.0, thigh=(thigh, -0.3), shank=(shank, 0.1))
    # move the right lateral knee marker 20 mm along the femur's anterior axis in both the model and the data (fit stays exact)
    Rf = (t.ry(0.0) @ t.R0) @ t.rz(thigh)
    shift = Rf @ np.array([0.02, 0.0, 0.0])
    for i, a in enumerate('xyz'):
        markers[f'R_Knee_Lat_{a}'] = markers[f'R_Knee_Lat_{a}'] + shift[i] * 1000.0
    body, loc = geo['r']['markers']['R_Knee_Lat']
    geo['r']['markers']['R_Knee_Lat'] = (body, np.asarray(loc) + np.array([0.02, 0.0, 0.0]))
    res, _ = k.leg_results(markers, geo, hw_knee=0.100, hw_ankle=0.100)
    r = res['right']
    # the fixture puts the knee at femur (0, -0.4 + 0.01 q) with q = shank - thigh = -0.5, i.e. 5 mm below the marker's height
    q = shank - thigh
    ey = -0.01 * q                                                        # estimate minus knee along the femur's up axis (m)
    assert np.allclose(r['off']['knee_ap'], -20.0, atol=1e-6) and np.allclose(r['off']['knee_pd'], ey * 1000.0, atol=1e-6)
    # estimate in the femur frame: (0.02 forward, -0.4 up) from the hip: the thigh line tilts forward by atan(0.02 / 0.4)
    thigh_marker = thigh + math.atan2(0.02, 0.4)
    # estimate minus model knee in (forward, up): 0.02 along the femur's forward axis and ey along its up axis
    dx = 0.02 * math.cos(thigh) - ey * math.sin(thigh)
    dy = 0.02 * math.sin(thigh) + ey * math.cos(thigh)
    # shank vector (ankle minus estimate): 0.4 along the shank's down direction minus that shift
    sx = 0.4 * math.sin(shank) - dx
    sy = -0.4 * math.cos(shank) - dy
    shank_marker = math.atan2(sx, -sy)
    assert np.allclose(r['angles']['knee_marker']['thigh'], thigh_marker * D, atol=1e-6)
    assert np.allclose(r['angles']['knee_marker']['shank'], shank_marker * D, atol=1e-6)
    assert np.allclose(r['angles']['knee_marker']['knee'], (thigh_marker - shank_marker) * D, atol=1e-6)
    assert np.allclose(r['angles']['model']['knee'], (thigh - shank) * D, atol=1e-6)      # the pass's own route is unchanged
    assert np.allclose(res['left']['off']['knee_ap'], 0.0, atol=1e-6)


def test_summarise_leg_uses_window_and_skips_held_frames():
    n = 10
    arr = np.arange(n, dtype=float)
    leg = {'held': np.array([False] * 4 + [True] + [False] * 5),
           'angles': {v: {q: arr.copy() for q in k.ANGLES} for v in k.VARIANTS},
           'off': {key: arr.copy() for key in k.OFFSETS + ('thigh_len_mm', 'shank_len_mm')},
           'sens_knee': [arr.copy() for _ in k.WIDTH_GRID_M]}
    assert k.summarise_leg(leg)['ang_model_knee'] == pytest.approx(np.mean([0, 1, 2, 3, 5, 6, 7, 8, 9]))
    s = k.summarise_leg(leg, np.arange(3, 8))               # frames 3..7 less held frame 4
    assert s['ang_model_knee'] == pytest.approx(np.mean([3, 5, 6, 7])) and s['n_frames'] == 4
    assert math.isnan(k.summarise_leg(leg, np.array([4]))['ang_model_knee'])       # only a held frame: missing, not zero


def test_combine_and_flat_row_bookkeeping():
    def summary(delta_knee, off_ap, route='pass_unchanged'):
        d = {'route': route, 'n_frames': 5, 'off_thigh_len_mm': 400.0, 'off_shank_len_mm': 400.0}
        for v in k.VARIANTS:
            for q in k.ANGLES:
                d[f'ang_{v}_{q}'] = 10.0 if (v == 'model' and q == 'knee') else (10.0 - delta_knee if q == 'knee' else 1.0)
        for key in k.OFFSETS:
            d[f'off_{key}'] = off_ap if key == 'knee_ap' else 0.0
        for i in range(len(k.WIDTH_GRID_M)):
            d[f'sens_knee_{i}'] = 10.0 - delta_knee
        return d
    static = [summary(6.0, -20.0), summary(8.0, -30.0)]
    walk = [dict(summary(7.0, -25.0), leg='right', recording='s/r')] * 3
    ref = {'thigh': 20.0, 'shank': -5.0, 'knee': 15.0, 'ankle': 0.0}
    a3row = {'mid_knee': 23.0, 'mid_thigh': 21.0, 'mid_shank': -5.0, 'mid_ankle': 0.0, 'lh_knee': 10.0, 'ik_knee': 9.0}
    row = k.flat_row('AB06', [{k_: v for k_, v in s.items() if k_ != 'leg'} for s in static], walk, a3row, ref, None)
    assert row['static_model_knee'] == 10.0 and row['static_both_marker_knee'] == pytest.approx(3.0)
    assert row['static_delta_knee'] == pytest.approx(7.0) and row['static_off_knee_ap'] == pytest.approx(-25.0)
    assert row['walk_delta_knee'] == pytest.approx(7.0) and row['n_walk_strides'] == 3
    assert row['gap_before_knee'] == pytest.approx(8.0) and row['gap_after_knee'] == pytest.approx(1.0)
    assert row['static_width_sensitivity_knee_deg'] == pytest.approx(0.0)
    assert row['static_knee_deg_per_10mm_ap'] == pytest.approx(10.0 * k.deg_per_mm_ap(0.4, 0.4))
    assert row['static_model_minus_a3_knee'] == pytest.approx(0.0)
    # no walking strides: the walking columns are missing, not zero
    empty = k.flat_row('AB07', [], [], None, ref, None)
    assert math.isnan(empty['walk_model_knee']) and math.isnan(empty['gap_after_knee'])


def test_summary_json_shares_and_verdict_on_synthetic_people():
    rows = []
    for i in range(5):
        r = {'subject': f'AB{i:02d}', 'static_model_knee': 7.0, 'static_both_marker_knee': 1.0, 'static_knee_marker_knee': 2.0,
             'static_delta_knee': 6.0, 'walk_delta_knee': 7.0, 'walk_delta_knee_only_knee': 5.0, 'a3_mid_knee': 23.0,
             'static_off_knee_ap': -20.0 - i, 'static_knee_deg_per_10mm_ap': 2.8, 'model_knee_coupled': True}
        for q in ('thigh', 'shank', 'ankle'):
            for key in (f'static_model_{q}', f'static_both_marker_{q}', f'static_knee_marker_{q}', f'static_delta_{q}',
                        f'walk_delta_{q}', f'a3_mid_{q}'):
                r[key] = 1.0
        for label in ('static', 'walk'):
            for key in k.OFFSETS:
                r.setdefault(f'{label}_off_{key}', 0.0)
        for key in ('model_knee_child_location_norm_mm', 'model_knee_axis_tilt_from_lateral_deg',
                    'model_knee_parent_rotation_about_flexion_axis_deg', 'model_neutral_lh_knee_deg', 'model_flexion_sign_check_slope',
                    'model_model_offset_at_ik_deg'):
            r[key] = 0.0
        rows.append(r)
    out = k.summary_json(rows, {'knee': 15.0, 'thigh': 1.0, 'shank': 1.0, 'ankle': 1.0}, {}, {})
    assert out['static_share_removed_knee'] == pytest.approx(6.0 / 7.0)
    assert out['walking']['knee']['mean_gap'] == pytest.approx(8.0) and out['walking']['knee']['mean_corrected_gap'] == pytest.approx(1.0)
    assert out['walking_share_removed_knee'] == pytest.approx(7.0 / 8.0)
    assert out['verdict'] == 'geometry_biased'
    assert out['knee_ap_offset_needed_to_explain_standing_mm'] == pytest.approx(7.0 / 0.28)


# ---------------------------------------------------------------------------------------------- spec, inputs, roots
def test_assumed_widths_are_recorded_as_assumptions():
    assert k.ASSUMED_PARAMETERS['knee_width_m'] == 0.090 and k.ASSUMED_PARAMETERS['ankle_width_m'] == 0.070
    assert 'assumed' in k.ASSUMED_PARAMETERS['source']
    assert (0.09, 0.07) in k.WIDTH_GRID_M


def test_default_roots_and_pilot_people_match_the_static_check():
    from contributor_tools import analyze_gt21_static_pose as a3
    from contributor_tools import build_gt21_static_specs as static_specs
    assert k.STATIC_ROOT == a3.STATIC_ROOT and k.RECON == a3.RECON and k.A3_ROOT == a3.RECON / 'gt21_static_analysis_v1'
    assert specs.PILOT == static_specs.PILOT
    assert specs.OUT == 'converted_datasets/reconversion_v2/gt21_knee_centre_v1'


def test_read_a3_handles_missing_files(tmp_path):
    assert k.read_a3(tmp_path) == ({}, {})
    (tmp_path / 'per_participant.csv').write_text('subject,lh_knee,routes\nAB06,6.5,pass_unchanged\n')
    (tmp_path / 'comparison.json').write_text('{"reference_means_deg": {"mean_of_both": {"knee": 15.0}}}')
    rows, ref = k.read_a3(tmp_path)
    assert rows['AB06']['lh_knee'] == 6.5 and rows['AB06']['routes'] == 'pass_unchanged' and ref == {'knee': 15.0}


def test_inventory_reader_filters_mode_and_sorts(tmp_path):
    p = tmp_path / 'ledger.jsonl'
    p.write_text('\n'.join(['{"subject":"AB06","mode":"levelground","session":"s2","recording":"b","source":"x"}',
                            '{"subject":"AB06","mode":"ramp","session":"s1","recording":"c","source":"x"}',
                            '{"subject":"AB06","mode":"levelground","session":"s1","recording":"a","source":"x"}']) + '\n')
    inv = k.load_inventory(p)
    assert [r['recording'] for r in inv['AB06']] == ['a', 'b']
