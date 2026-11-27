"""Tests for the GT21 standing-pose analysis (A3) and its static-export launcher job. DRAFT: written in phase 1, not run.

All inputs are SYNTHETIC numbers chosen so the expected answer is known by hand; none is GT21 data. They test the arithmetic
(window means, sign and unit conversion, gap and correlation bookkeeping, spec validation), not the scientific question.
"""
import math

import numpy as np
import pytest

from contributor_tools import analyze_gt21_static_pose as a
from contributor_tools import guarded_launcher as gl
from contributor_tools import guarded_launcher_native as gn

D = 180.0 / math.pi


def test_trial_stats_ignores_nonfinite_and_reports_count():
    mean, sd, n = a.trial_stats([1.0, 3.0, np.nan, np.inf])
    assert (mean, n) == (2.0, 2) and sd == pytest.approx(math.sqrt(2.0))
    assert a.trial_stats([np.nan]) [2] == 0 and math.isnan(a.trial_stats([np.nan])[0])


def test_ik_angles_use_locohub_knee_sign_and_units():
    # synthetic: OpenSim knee_angle -12 deg (flexed in OpenSim's sense), hip 5, ankle -3, stored in degrees
    cols = {'hip_flexion_r': np.full(10, 5.0), 'knee_angle_r': np.full(10, -12.0), 'ankle_angle_r': np.full(10, -3.0)}
    out = a.ik_angles(cols, {'knee_angle_r': 'deg', 'hip_flexion_r': 'deg', 'ankle_angle_r': 'deg'}, 'r')
    assert out['knee'] == pytest.approx(12.0) and out['knee_raw'] == pytest.approx(-12.0)
    assert out['hip'] == pytest.approx(5.0) and out['ankle'] == pytest.approx(-3.0) and not out['units_assumed']
    # the same angles in radians
    rad = {k: v / D for k, v in cols.items()}
    out = a.ik_angles(rad, {k: 'rad' for k in rad}, 'r')
    assert out['knee'] == pytest.approx(12.0)
    # no unit text: degrees are assumed and the flag says so
    assert a.ik_angles(cols, {}, 'r')['units_assumed'] is True
    # missing side columns are NaN, not zero
    assert math.isnan(a.ik_angles(cols, {}, 'l')['knee'])


def test_ik_offset_self_check_is_zero_for_offset_of_own_mean():
    ik = np.array([10.0, 11.0, 9.0, 10.5])
    offset = {'knee_angle_r': ik - ik.mean(), 'hip_flexion_r': ik - ik.mean(), 'ankle_angle_r': ik - ik.mean()}
    assert a.ik_offset_self_check(offset, {}, 'r') == pytest.approx(0.0, abs=1e-12)
    offset['knee_angle_r'] = ik - ik.mean() + 2.0
    assert a.ik_offset_self_check(offset, {}, 'r') == pytest.approx(2.0)


def test_window_means_inclusive_window_and_subjects():
    phase = np.tile(np.arange(0, 101, dtype=float), 2)
    subj = np.array(['AB06'] * 101 + ['AB07'] * 101, dtype=object)
    value = np.concatenate([np.arange(0, 101, dtype=float), np.arange(0, 101, dtype=float) + 10.0])
    w = a.WindowMeans()
    w.add(subj[:150], phase[:150], {'knee': value[:150]})    # split across two calls: sums must accumulate
    w.add(subj[150:], phase[150:], {'knee': value[150:]})
    m = w.means()
    assert m['AB06']['knee'] == pytest.approx(27.5)          # mean of 20..35 inclusive
    assert m['AB07']['knee'] == pytest.approx(37.5)
    w2 = a.WindowMeans()
    w2.add(np.array(['AB06'] * 3, dtype=object), np.array([25.0, 30.0, 99.0]), {'knee': np.array([1.0, np.nan, 50.0])})
    assert w2.means()['AB06']['knee'] == 1.0                 # NaN and outside-window rows are not counted
    assert w2.n[('AB06', 'knee')] == 1


def test_subject_key_and_rank_and_pearson():
    assert a.subject_key('GT21_AB06_x') == 'AB06' and a.subject_key('S01') is None
    assert list(a.rank([10, 30, 20, 20])) == [1.0, 4.0, 2.5, 2.5]
    assert a.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert math.isnan(a.pearson([1, 2, 3], [5, 5, 5]))


def test_compare_standing_offset_explains_whole_gap():
    # synthetic: every person's walking knee = reference + own standing offset, so one degree of gap per degree standing
    stand = np.array([0.0, 4.0, 8.0, 12.0])
    ref = 20.0
    c = a.compare(stand, ref + stand, ref)
    assert c['mean_gap'] == pytest.approx(6.0) and c['mean_standing'] == pytest.approx(6.0)
    assert c['pearson_r'] == pytest.approx(1.0) and c['spearman_r'] == pytest.approx(1.0)
    assert c['slope_gap_on_standing'] == pytest.approx(1.0)
    assert c['mean_corrected_gap'] == pytest.approx(0.0, abs=1e-12) and c['sd_corrected_gap'] == pytest.approx(0.0, abs=1e-12)
    assert c['share_of_gap_from_standing'] == pytest.approx(1.0)


def test_compare_constant_gap_unrelated_to_standing():
    # synthetic: a constant 9 degree gap whatever the standing pose: correlation undefined, correction makes it worse
    stand = np.array([-2.0, 0.0, 2.0, 4.0])
    c = a.compare(stand, 30.0 + np.zeros(4), 21.0)
    assert c['mean_gap'] == pytest.approx(9.0) and math.isnan(c['pearson_r'])
    assert c['slope_gap_on_standing'] == pytest.approx(0.0, abs=1e-9)
    assert c['mean_corrected_gap'] == pytest.approx(9.0 - 1.0)       # standing mean is 1.0
    assert c['share_of_gap_from_standing'] == pytest.approx(1.0 / 9.0)


def test_compare_skips_people_without_both_values():
    c = a.compare([1.0, np.nan, 3.0, 5.0], [11.0, 12.0, np.nan, 15.0], 10.0)
    assert c['n'] == 2 and c['mean_gap'] == pytest.approx(3.0)


def test_read_csv_columns_round_trip(tmp_path):
    p = tmp_path / 't.csv'
    p.write_text('Header,R_ASIS_x\n0,1.5\n0.005,NaN\n')
    cols = a.read_csv_columns(p)
    assert list(cols) == ['Header', 'R_ASIS_x'] and cols['Header'][1] == 0.005 and math.isnan(cols['R_ASIS_x'][1])
    p.write_text('Header,R_ASIS_x\n0,1.5,9\n')
    with pytest.raises(ValueError):
        a.read_csv_columns(p)


def test_leg_means_deg_and_both_legs():
    # synthetic columns in radians for 3 frames; right knee 10 deg, left knee 20 deg; pelvis shared
    cols = {}
    for leg, knee in (('right', 10.0), ('left', 20.0)):
        for q, name in a.PASS_COLUMN.items():
            cols[name.format(leg=leg)] = np.full(3, (knee if q == 'knee' else 1.0) / D)
    out = a.leg_means_deg(cols)
    assert out['right']['knee'] == pytest.approx(10.0) and out['left']['knee'] == pytest.approx(20.0)
    assert a.both_legs(out)['knee'] == pytest.approx(15.0) and a.both_legs(out)['pelvis'] == pytest.approx(1.0)
    assert out['n_valid'] == {'right': 3, 'left': 3}


def test_widened_clusters_and_patch_restores():
    from contributor_tools import gt21_rb_pass as rb
    geo = {'r': {'markers': {'R_Thigh_Extra': ('femur_r', None), 'R_Shank_Extra': ('tibia_r', None), 'R_Heel': ('calcn_r', None),
                             'L_Thigh_Extra2': ('femur_l', None)}},
           'l': {'markers': {'L_Thigh_Extra2': ('femur_l', None)}}}
    names = ['R_Thigh_Extra_x', 'R_Shank_Extra_x', 'R_Heel_x', 'L_Thigh_Extra2_x']
    thigh, shank = a.widened_clusters(names, geo)
    assert 'Thigh_Extra' in thigh and 'Thigh_Extra2' in thigh and 'Shank_Extra' in shank and 'Heel' not in thigh + shank
    assert set(rb.THIGH_CLUSTER) <= set(thigh)
    before = rb.THIGH_CLUSTER, rb.SHANK_CLUSTER
    with a.patched_clusters(thigh, shank):
        assert rb.THIGH_CLUSTER == thigh
    assert (rb.THIGH_CLUSTER, rb.SHANK_CLUSTER) == before


def test_model_roots_match_the_merged_pass_runner():
    from contributor_tools import run_gt21_rb_pass as run
    assert a.MODEL_ROOTS == run.ROOTS


def test_participant_row_averages_trials_and_flags_assumed_units():
    def trial(knee_lh, knee_ik, assumed):
        t = {'status': 'ok', 'route': 'pass_unchanged', 'ik_offset_max_abs_mean_deg': 0.1,
             'knee_sd_right': 1.0, 'knee_sd_left': 1.0, 'ik_right_units_assumed': assumed, 'ik_left_units_assumed': assumed}
        for q in a.QUANT:
            t[f'lh_right_{q}'] = t[f'lh_left_{q}'] = knee_lh if q == 'knee' else 0.0
        for k in ('hip', 'knee', 'ankle', 'knee_raw'):
            t[f'ik_right_{k}'] = t[f'ik_left_{k}'] = knee_ik if k == 'knee' else 0.0
        return t
    row = a.participant_row('AB06', [trial(10.0, 4.0, False), trial(14.0, 6.0, True), {'status': 'excluded', 'reason': 'x'}])
    assert row['lh_knee'] == pytest.approx(12.0) and row['ik_knee'] == pytest.approx(5.0)
    assert row['lh_minus_ik_knee'] == pytest.approx(7.0) and row['ik_units_assumed'] is True
    assert row['n_static_trials_ok'] == 2 and row['n_static_trials'] == 3


def _native_spec(tmp_path, job=None, script=gn.STATIC_SCRIPT):
    spec = {'job_id': 'j', 'subject': 'AB06', 'source_root': str(gn.ALLOWED_SOURCE_ROOTS[1]),
            'output_root': str(gl.REPO_ROOT / 'converted_datasets/reconversion_v2/x/AB06'),
            'receipt_path': str(tmp_path / 'r.json'), 'timeout_seconds': 600,
            'bindings': {script: 'a' * 64, 'contributor_tools/guarded_launcher_native.py': 'b' * 64}}
    if job:
        spec['job'] = job
    return spec


def test_native_launcher_static_job_is_selected_by_name_and_bound_to_its_script(tmp_path):
    s = gn.validate_native_spec(_native_spec(tmp_path, 'static'))
    assert s['job'] == 'static'
    with pytest.raises(gn.NativeSpecError):                       # default job (labels) needs the label script bound
        gn.validate_native_spec(_native_spec(tmp_path))
    with pytest.raises(gn.NativeSpecError):                       # unknown job
        gn.validate_native_spec(_native_spec(tmp_path, 'anything'))
    assert gn.validate_native_spec(_native_spec(tmp_path, None, gn.SCRIPT))['job'] == 'labels'


def test_native_launcher_expression_and_required_outputs_per_job():
    nonce = '0123456789abcdef'
    assert gn.matlab_expression('S:\\a', 'S:\\b', 'AB06', nonce).startswith('gt21_rb01_label_export(')
    assert gn.matlab_expression('S:\\a', 'S:\\b', 'AB06', nonce, 'static').startswith('gt21_static_export(')
    with pytest.raises(gn.NativeSpecError):
        gn.matlab_expression('S:\\a', 'S:\\b', 'AB06', nonce, 'other')
    assert gn.JOBS['static']['required']('AB06') == ['static_meta_AB06.json']
    assert gn.JOBS['labels']['required']('AB06') == ['labels_AB06.jsonl', 'subject_info_AB06.json']
