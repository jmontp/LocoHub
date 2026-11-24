"""Synthetic tests for GT21-RB03 segmentation and the stance force mask (all inputs are made-up arrays with known answers)."""
import io
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from contributor_tools import gt21_rb_segment as sg
from contributor_tools import run_gt21_rb_segment as rn


def sawtooth(starts, n, dt=0.005):
    """Heel-strike percentage: 0 at each listed start sample, rising linearly to just under 100 before the next one."""
    pct = np.zeros(n)
    pct[starts[0] - 1] = 99.0
    for a, b in zip(starts[:-1], starts[1:]):
        pct[a:b] = 100.0 * (np.arange(b - a)) / (b - a)
    pct[starts[-1]:] = 0.2 * np.arange(n - starts[-1])          # the last cycle is cut by the end of the recording
    return np.arange(n) * dt, pct


# ---- force mask ---------------------------------------------------------------------------------------------
def test_force_mask_threshold_values():
    bw = 700.0
    v = np.array([0.0, 0.02, 0.03, 0.5, np.nan, 0.0, 0.5])   # 0 N, 14 N, 21 N, 350 N, missing, 0 N swing, 350 N swing
    stance = np.array([1, 1, 1, 1, 1, 0, 0], bool)
    m, st = sg.force_missing_mask(stance, v, bw)
    assert m.tolist() == [True, True, False, False, True, False, False]
    assert st['masked'] == 3 and st['already_missing'] == 1 and st['was_exactly_zero'] == 1
    assert st['was_small_positive_or_negative'] == 1
    assert st['stances'] == 1 and st['stances_fully_masked'] == 0 and st['stances_with_edge_samples_masked'] == 1


def test_force_mask_exact_threshold_is_kept_and_whole_unowned_stance_is_masked():
    bw = 1000.0
    v = np.array([0.02, 0.0, 0.0, 0.0, 0.0])                 # exactly 20 N is kept
    m, _ = sg.force_missing_mask(np.array([1, 0, 1, 1, 0], bool), v, bw)
    assert m.tolist() == [False, False, True, True, False]
    _, st = sg.force_missing_mask(np.array([0, 0, 1, 1, 0], bool), v, bw)
    assert st['stances'] == 1 and st['stances_fully_masked'] == 1


def test_apply_force_mask_sets_nan_not_zero_and_leaves_other_samples():
    cols = {f'grf_{k}_left_BW': np.array([1.0, 2.0, 3.0]) for k in ('vertical', 'anterior', 'lateral')}
    out = sg.apply_force_mask(cols, 'left', np.array([False, True, False]))
    for k in out:
        assert np.isnan(out[k][1]) and out[k][0] == 1.0 and out[k][2] == 3.0
    assert cols['grf_vertical_left_BW'][1] == 2.0            # input untouched


# ---- source events and step definition ----------------------------------------------------------------------
def test_resets_and_pairs():
    t, p = sawtooth([3, 203, 403, 600], 700)
    assert sg.resets(p).tolist() == [3, 203, 403, 600]
    np.testing.assert_allclose(sg.event_times(t, p), np.array([3, 203, 403, 600]) * 0.005)   # falls of more than 50 points


# ---- labels and dispositions --------------------------------------------------------------------------------
W = [{'label': 'idle', 'start_header': 0.0, 'end_header': 1.0}, {'label': 'walk-stairascent', 'start_header': 1.005, 'end_header': 3.0},
     {'label': 'stairascent', 'start_header': 3.005, 'end_header': 8.0}, {'label': 'stairdescent', 'start_header': 8.005, 'end_header': 12.0}]


def step(mode, meta, t0, t1, span=(0.0, 20.0)):
    n = 4000
    h = np.arange(n) * 0.005
    a, b = int(round(t0 / 0.005)), int(round(t1 / 0.005))
    p = np.zeros(n)
    p[a - 1] = 99.0
    p[a:b] = 100.0 * np.arange(b - a) / (b - a)
    return sg.classify_step(mode, meta, float(h[a]), float(h[b]), h, p, a, b, span)


def stair_meta(height=4):
    return {'read_ok': True, 'label_present': True, 'label_windows': W, 'stair_height_top_level': height}


def test_stair_inside_window_gets_source_label_height_and_direction():
    r = step('stair', stair_meta(5), 4.0, 5.2)
    assert (r['disposition'], r['label'], r['step_class'], r['direction']) == ('eligible', 'stairascent', 'steady', 'ascent')
    assert r['stair_height_m'] == 0.127
    r = step('stair', stair_meta(5), 9.0, 10.2)
    assert r['label'] == 'stairdescent' and r['direction'] == 'descent'
    r = step('stair', stair_meta(5), 1.5, 2.5)
    assert r['label'] == 'walk-stairascent' and r['step_class'] == 'transition'


def test_straddling_step_is_listed_never_labelled():
    r = step('stair', stair_meta(), 2.5, 3.7)
    assert r['disposition'] == 'excluded' and r['reason'] == 'straddles_label_windows' and r['label'] is None
    assert r['labels_overlapped'] == ['walk-stairascent', 'stairascent']


def test_idle_and_unmapped_labels_have_a_reason():
    r = step('stair', stair_meta(), 0.1, 0.9)
    assert r['disposition'] == 'excluded' and r['label'] is None and r['reason'] == 'label_not_mapped_to_a_task: idle'


def test_missing_terrain_value_is_never_defaulted():
    for bad in (None, [], 0, -4, float('nan'), 'four'):
        r = step('stair', stair_meta(bad), 4.0, 5.2)
        assert r['disposition'] == 'excluded' and r['reason'] == 'source_stair_height_missing_or_not_positive'
        assert r['stair_height_m'] is None
    ramp = {'read_ok': True, 'label_present': True, 'ramp_incline_top_level': [],
            'label_windows': [{'label': 'rampascent', 'start_header': 0.0, 'end_header': 20.0}]}
    r = step('ramp', ramp, 4.0, 5.2)
    assert r['reason'] == 'source_incline_missing_or_not_positive' and r['incline_deg'] is None


def test_ramp_descent_incline_is_negative_ascent_positive():
    wins = [{'label': 'rampascent', 'start_header': 0.0, 'end_header': 9.0}, {'label': 'rampdescent', 'start_header': 9.005, 'end_header': 19.0}]
    meta = {'read_ok': True, 'label_present': True, 'ramp_incline_top_level': 7.8, 'label_windows': wins}
    assert step('ramp', meta, 2.0, 3.0)['incline_deg'] == 7.8
    r = step('ramp', meta, 12.0, 13.0)
    assert r['incline_deg'] == -7.8 and r['direction'] == 'descent'


def test_treadmill_steps_are_held_not_labelled_and_levelground_turn_not_mapped():
    meta = {'read_ok': True, 'label_present': False, 'trial_start': 1.0, 'trial_end': 19.0}
    r = step('treadmill', meta, 4.0, 5.0)
    assert r['disposition'] == 'held' and r['label'] is None
    assert step('treadmill', meta, 0.2, 1.2)['reason'] == 'outside_trial_window'
    lw = {'read_ok': True, 'label_present': True, 'label_windows': [{'label': 'turn1', 'start_header': 0.0, 'end_header': 19.0}]}
    r = step('levelground', lw, 4.0, 5.0)
    assert r['reason'] == 'label_not_mapped_to_a_task: turn1'


def test_no_converted_table_is_a_reason_not_an_error():
    n = 4000
    h = np.arange(n) * 0.005
    p = np.zeros(n)
    p[799] = 99.0
    p[800:1000] = np.arange(200) * 0.5
    r = sg.classify_step('stair', stair_meta(), float(h[800]), float(h[1000]), h, p, 800, 1000, None)
    assert r['reason'] == 'recording_not_converted_in_pass'


# ---- force check --------------------------------------------------------------------------------------------
def test_force_check_offsets_and_unloaded_foot():
    t = np.arange(0, 4, 0.005)
    f = np.zeros_like(t)
    f[(t >= 1.02)] = 600.0                                    # rises through 20 N at 1.02 s
    r = sg.force_check(t, f, 1.0, 1.0, 2.0)
    assert r['status'] == 'agrees_within_50_ms' and abs(r['offset_ms'] - 20.0) < 1e-6
    r = sg.force_check(t, f, 0.9, 0.9, 2.0)                   # 120 ms late: found but beyond 50 ms
    assert r['status'] == 'nearest_crossing_beyond_50_ms' and abs(r['offset_ms'] - 120.0) < 1e-6
    r = sg.force_check(t, np.zeros_like(t), 1.0, 1.0, 2.0)
    assert r['status'] == 'foot_never_reaches_threshold_in_step'


# ---- authors' cutting and classification --------------------------------------------------------------------
def test_authors_intervals_cut_like_segment_gc():
    t, p = sawtooth([20, 220, 430, 600], 650)
    iv = sg.authors_intervals(t, p)
    assert [(i['kind'], i['start_index'], i['end_index']) for i in iv] == [
        ('partial_first', 18, 20), ('interior', 20, 220), ('interior', 220, 430), ('interior', 430, 600), ('partial_last', 600, 649)]


def test_authors_class_ramp_and_stair_known_cases():
    assert sg.authors_class('ramp', ['rampascent'], [], []) == 'rampascent'
    assert sg.authors_class('ramp', ['idle', 'walk-rampascent'], [], []) == 'discard'
    assert sg.authors_class('ramp', ['walk-rampascent', 'rampascent'], ['l', 'r'], []) == 'rampascent'
    assert sg.authors_class('ramp', ['walk-rampascent', 'rampascent'], ['r', 'l'], []) == 'walk-rampascent'
    assert sg.authors_class('stair', ['walk-stairascent', 'stairascent'], ['l', 'r'], []) == 'stairascent'
    assert sg.authors_class('stair', ['stairascent', 'stairascent-walk'], ['l', 'r'], []) == 'stairascent-walk'
    assert sg.authors_class('stair', ['stairdescent'], ['l', 'r'], ['l', 'r']) == 'stairdescent'
    assert sg.authors_class('stair', ['stairascent'], [], []) == 'stairascent'
    assert sg.authors_class('stair', ['walk-stairdescent', 'stairdescent', 'idle'], [], []) == 'case_not_found'
    assert sg.authors_class('levelground', ['walk'], [], []) == 'not_reproduced'


# ---- end to end on a made-up recording like the failed stair recording ---------------------------------------
def make_recording(tmp):
    n = 4000
    starts_r = [400, 700, 1000, 1300, 1600, 1900, 2200]
    starts_l = [550, 850, 1150, 1450, 1750, 2050]
    tr, pr = sawtooth(starts_r, n)
    tl, pl = sawtooth(starts_l, n)
    gc = {'right': {'Header': tr, 'HeelStrike': pr, 'ToeOff': np.zeros(n)}, 'left': {'Header': tl, 'HeelStrike': pl, 'ToeOff': np.zeros(n)}}
    t = tr
    stance = {'right': np.zeros(n, bool), 'left': np.zeros(n, bool)}
    vert = {'right': np.zeros(n), 'left': np.zeros(n)}
    for leg, st in (('right', starts_r), ('left', starts_l)):
        for a in st[:-1]:
            stance[leg][a:a + 180] = True
            vert[leg][a + 4:a + 176] = 1.0                     # loaded only here; samples a..a+3 and a+176..a+179 are in stance with 0
    table = {'time_s': t, 'stance_left': stance['left'], 'stance_right': stance['right'],
             'grf_vertical_left_BW': vert['left'], 'grf_vertical_right_BW': vert['right']}
    return gc, table


def test_segment_recording_end_to_end_synthetic(tmp_path):
    gc, table = make_recording(tmp_path)
    # six windows like the failed stair file: each holds ONE right-leg strike, so no right step fits inside a window
    wins = []
    bounds = [0, 2.5, 3.9, 5.4, 6.9, 8.4, 9.9, 11.4, 99]
    names = ['idle', 'walk-stairascent', 'stairascent', 'stairascent-walk', 'idle', 'walk-stairdescent', 'stairdescent', 'stairdescent-walk']
    for i, nme in enumerate(names):
        wins.append({'label': nme, 'start_header': bounds[i] + (0.005 if i else 0), 'end_header': bounds[i + 1]})
    meta = {'read_ok': True, 'label_present': True, 'label_windows': wins, 'stair_height_top_level': 4, 'trans_leg_ascent': ['l', 'r'],
            'trans_leg_descent': ['l', 'r']}
    row = {'subject': 'ABxx', 'session': 's', 'mode': 'stair', 'recording': 'stair_synth', 'source': 'synthetic'}
    steps_f, auth_f = io.StringIO(), io.StringIO()
    entry = rn.segment_recording(row, meta, gc, table, 700.0, tmp_path / 'mask', steps_f, auth_f)
    steps = [json.loads(x) for x in steps_f.getvalue().splitlines()]
    assert entry['resets'] == {'left': 6, 'right': 7}
    assert len(steps) == (entry['resets']['right'] - 1) + (entry['resets']['left'] - 1)
    assert sum(entry['steps_by_disposition'].values()) == len(steps)            # every step has exactly one disposition
    assert all(s['disposition'] in ('eligible', 'excluded', 'held') for s in steps)
    assert all(s['reason'] is None for s in steps if s['disposition'] == 'eligible')
    assert entry['status'] in ('segmented', 'excluded_no_eligible_step')
    # mask: samples a..a+3 and a+176..a+179 of each stance are in stance with 0 N, so masked: 8 per stance
    assert entry['force_mask']['right']['masked'] == 8 * 6 and entry['force_mask']['right']['stances'] == 6
    layer = pq.read_table(tmp_path / 'mask' / 'ABxx' / 'stair' / 'stair_synth.parquet').to_pandas()
    assert layer.force_missing_right.sum() == 48 and layer.force_missing_left.sum() == 40
    # authors' intervals: our right steps are the interior intervals, all matched at 0 ms
    auth = [json.loads(x) for x in auth_f.getvalue().splitlines()]
    interior = [a for a in auth if a['kind'] == 'interior']
    assert len(interior) == 6 and all(a['status'] == 'matched' and a['start_offset_ms'] == 0.0 for a in interior)
    assert not [a for a in auth if a['status'] == 'missed']


def test_recording_with_no_eligible_step_is_a_listed_exclusion(tmp_path):
    gc, table = make_recording(tmp_path)
    meta = {'read_ok': True, 'label_present': True, 'stair_height_top_level': 4,
            'label_windows': [{'label': 'idle', 'start_header': 0.0, 'end_header': 99.0}]}
    row = {'subject': 'ABxx', 'session': 's', 'mode': 'stair', 'recording': 'stair_idle', 'source': 'synthetic'}
    entry = rn.segment_recording(row, meta, gc, None, None, tmp_path / 'mask', io.StringIO(), io.StringIO())
    assert entry['status'] == 'excluded_no_eligible_step' and 'label_not_mapped_to_a_task: idle' in entry['reason']
    assert entry['table_available'] is False and 'force_mask' not in entry
