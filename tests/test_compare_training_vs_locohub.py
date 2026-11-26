"""Synthetic tests for contributor_tools/compare_training_vs_locohub.py.

Every array here is made up (seeded noise, sums of sines) with answers known by construction. No LocoHub or training data is
read. Passing these tests shows the matching and statistics code works on known inputs; it says nothing about the real files.
"""
import math

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools import compare_training_vs_locohub as cmp

MAPS = cmp.column_maps(0.100)
BY_NAME = {m.name: m for m in MAPS}


def noise(n, seed):
    rng = np.random.default_rng(seed)
    return np.convolve(rng.standard_normal(n), np.ones(9) / 9, mode='same') * 3.0


# ------------------------------------------------------------------------------------------------ mapping
def test_mapping_units_signs_and_cop_shift():
    assert BY_NAME['ankle_angle'].scale == pytest.approx(180.0 / math.pi)
    assert BY_NAME['ankle_angle'].unit == 'deg' and BY_NAME['ankle_moment'].scale == 1.0
    assert all(m.sign == 1.0 for m in MAPS)
    assert BY_NAME['cop_anterior'].lh_offset == pytest.approx(0.100)
    assert cmp.column_maps(0.0)[-1].lh_offset == 0.0
    assert BY_NAME['cop_anterior'].his_flag == 'cop_ok' and BY_NAME['vertical_force'].his_flag == 'fz_measured'
    assert cmp.lh_name(BY_NAME['ankle_moment'], 'left') == 'ankle_dorsiflexion_moment_left_Nm_kg'
    assert cmp.lh_name(BY_NAME['ankle_moment'], 'ipsi') == 'ankle_dorsiflexion_moment_ipsi_Nm_kg'
    sizes = {m.name: m.size for m in MAPS}
    assert sizes['ankle_angle'] == 2.0 and sizes['ankle_moment'] == 0.05 and sizes['cop_anterior'] == 0.02


def test_every_mapped_training_column_is_either_mapped_or_listed():
    mapped = {m.his for m in MAPS}
    assert not mapped & set(cmp.HIS_ROLES)           # a compared value column is never listed as "not compared"
    assert {m.his_flag for m in MAPS if m.his_flag} <= set(cmp.HIS_ROLES)      # flags are described as validity flags


def test_norm_subject_and_name_match():
    assert cmp.norm_subject('UM21_AB03') == 'AB03' and cmp.norm_subject('GT21_AB12') == 'AB12'
    assert cmp.name_match('levelground_ccw_fast_01_01', 'levelground_ccw_fast_01_01')
    assert cmp.name_match('levelground_ccw_fast_01_01+1', 'levelground_ccw_fast_01_01')
    assert cmp.name_match('treadmill_01_01_seg02', 'treadmill_01_01')
    assert not cmp.name_match('treadmill_01_10', 'treadmill_01_1')
    assert not cmp.name_match('stair_1_l_01_02', 'stair_1_r_01_02')


# ------------------------------------------------------------------------------------------------ helpers
def test_interp_nodes_exact_node_between_and_missing_neighbour():
    t = np.arange(5) * 0.005
    y = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
    v = cmp.interp_nodes(t, y, np.array([0.0, 0.005, 0.0025, 0.01, 0.0175, -0.1, 0.5]))
    assert v[0] == 1.0 and np.isnan(v[1]) and np.isnan(v[2]) and v[3] == 3.0
    assert v[4] == pytest.approx(4.5) and np.isnan(v[5]) and np.isnan(v[6])


def test_uniform_grid_places_samples_and_leaves_gaps():
    t = np.array([0.0, 0.005, 0.015])
    g = cmp.uniform_grid(t, np.array([1.0, 2.0, 4.0]), 0.0)
    assert len(g) == 4 and g[0] == 1.0 and g[1] == 2.0 and np.isnan(g[2]) and g[3] == 4.0
    with pytest.raises(ValueError):
        cmp.uniform_grid(np.array([-1.0]), np.array([1.0]), 0.0)


def test_iter_runs_groups_and_refuses_returning_keys():
    b1 = {'k': np.array(['a', 'a', 'b'], dtype=object), 'v': np.array([1.0, 2.0, 3.0])}
    b2 = {'k': np.array(['b', 'b', 'c'], dtype=object), 'v': np.array([4.0, 5.0, 6.0])}
    runs = {k: v['v'].tolist() for k, v in cmp.iter_runs(iter([b1, b2]), 'k')}
    assert runs == {'a': [1.0, 2.0], 'b': [3.0, 4.0, 5.0], 'c': [6.0]}
    bad = {'k': np.array(['a'], dtype=object), 'v': np.array([9.0])}
    with pytest.raises(ValueError):
        list(cmp.iter_runs(iter([b1, b2, bad]), 'k'))


# ------------------------------------------------------------------------------------------------ statistics
def test_acc_matches_direct_numpy_over_chunks():
    rng = np.random.default_rng(3)
    x = rng.normal(1.0, 2.0, 5000)
    y = x - 0.3 + rng.normal(0.0, 0.5, 5000)
    x[::50] = np.nan
    y[7::90] = np.nan
    acc = cmp.Acc(1.0, keep_abs=True, hist=True)
    for lo in range(0, 5000, 777):
        acc.add(x[lo:lo + 777], y[lo:lo + 777])
    both = np.isfinite(x) & np.isfinite(y)
    d = x[both] - y[both]
    r = acc.row()
    assert r['n_positions'] == 5000 and r['n_matched'] == int(both.sum())
    assert r['bias'] == pytest.approx(d.mean(), abs=1e-12)
    assert r['rms'] == pytest.approx(math.sqrt(np.mean(d ** 2)), abs=1e-12)
    assert r['corr'] == pytest.approx(np.corrcoef(x[both], y[both])[0, 1], abs=1e-12)
    assert r['frac_exceed'] == pytest.approx(np.mean(np.abs(d) > 1.0))
    assert r['p95_abs'] == pytest.approx(np.percentile(np.abs(d), 95)) and r['p95_exact']
    assert r['coverage_his'] == pytest.approx(np.isfinite(x).mean()) and r['coverage_lh'] == pytest.approx(np.isfinite(y).mean())
    assert r['n_his_only'] == int((np.isfinite(x) & ~np.isfinite(y)).sum())
    assert acc.hist.p95() == pytest.approx(np.percentile(np.abs(d), 95), abs=acc.hist.width * 1.01)


def test_hist_p95_is_inf_when_beyond_range_and_acc_with_no_overlap_is_nan():
    h = cmp.AbsHist(1.0)
    h.add(np.full(100, 1000.0))
    assert h.p95() == math.inf
    acc = cmp.Acc(1.0)
    acc.add(np.array([np.nan, 1.0]), np.array([2.0, np.nan]))
    r = acc.row()
    assert r['n_matched'] == 0 and math.isnan(r['bias']) and r['n_his_only'] == 1 and r['n_lh_only'] == 1


# ------------------------------------------------------------------------------------------------ alignment
def test_best_alignment_recovers_lag_and_sign():
    y = noise(3000, 1)
    x = y[400:1400].copy()
    fit = cmp.best_alignment(x, y, 300)
    assert fit['lag'] == 400 and fit['sign'] == 1 and fit['rms'] < 1e-12 and fit['n'] == 1000
    fit = cmp.best_alignment(-x, y, 300)
    assert fit['lag'] == 400 and fit['sign'] == -1 and fit['rms'] < 1e-12
    y2 = y.copy()
    y2[500:520] = np.nan                       # gaps in the long series do not move the answer
    assert cmp.best_alignment(x, y2, 300)['lag'] == 400
    assert cmp.best_alignment(x[:50], y, 300) is None      # too little data
    fit = cmp.best_alignment(y[10:900], y[:1000], 300)     # negative and positive offsets both handled
    assert fit['lag'] == 10
    fit = cmp.best_alignment(y[:900], y[10:1000], 300)
    assert fit['lag'] == -10


def G(f):
    f = np.asarray(f, float)
    return np.sin(2 * np.pi * f / 137.3) + 0.6 * np.sin(2 * np.pi * f / 71.9 + 1.0) + 0.3 * np.sin(2 * np.pi * f / 29.3 + 2.0)


def test_frames_series_and_stride_times_on_known_frames():
    a, b = 11, 110
    vals = G(a + np.arange(150) * (b - a) / 149)
    s = cmp.frames_series([(a, b, vals)])
    assert len(s) == 110 and np.all(np.isnan(s[:10]))
    assert np.nanmax(np.abs(s[10:] - G(np.arange(11, 111)))) < 5e-3
    tq = cmp.um21_stride_times(a, b, 1)               # segment starts at frame 1: frame 11 is 0.10 s in
    assert tq[0] == pytest.approx(0.10) and tq[-1] == pytest.approx(1.09) and len(tq) == 150
    assert cmp.parse_observation('um21:Streaming/AB01/Tread/i0:right:frames:965:1142') == ('right', 965, 1142)
    with pytest.raises(ValueError):
        cmp.parse_observation('um21:Streaming/AB01/Tread/i0:right:cycle3')


# ------------------------------------------------------------------------------------------------ GT21 end to end
def write_gt21_inputs(tmp_path):
    n_lh, off, m = 2000, 300, 1000
    t_lh = 100.0 + np.arange(n_lh) * 0.005
    sig = {}
    lh_cols = {'source_recording_id': ['AB06/levelground/lg_01'] * n_lh, 'time_s': t_lh}
    his_cols = {'recording_id': ['AB06|lg_01'] * m, 'subject': ['AB06'] * m, 'task': ['level_walking'] * (m // 2) + ['incline_walking'] * (m // 2),
                'time_s': np.arange(m) * 0.005}
    for k, mp in enumerate(MAPS):
        right = noise(n_lh, 10 + k)
        left = noise(n_lh, 50 + k)
        sig[mp.name] = right
        lh_cols[mp.lh.format(R='right')] = (right - mp.lh_offset) / mp.scale
        lh_cols[mp.lh.format(R='left')] = (left - mp.lh_offset) / mp.scale
        his = right[off:off + m] / mp.scale
        if mp.name == 'ankle_angle':
            his = his + 0.01                          # known bias of 0.01 rad
        if mp.name == 'cop_anterior':
            his = his + 0.005                         # known bias of 5 mm (after the 0.100 m origin shift)
        his_cols[mp.his] = his
    his_cols['fz_measured'] = np.array([False] * 10 + [True] * (m - 10))
    his_cols['cop_ok'] = np.ones(m, np.float32)
    his_path, lh_path = tmp_path / 'his.parquet', tmp_path / 'time.parquet'
    pq.write_table(pa.table(his_cols), his_path, row_group_size=300)
    pq.write_table(pa.table(lh_cols), lh_path, row_group_size=300)
    return his_path, lh_path, off


def test_gt21_subject_known_offsets_leg_and_differences(tmp_path):
    his_path, lh_path, off = write_gt21_inputs(tmp_path)
    cfg = cmp.Cfg(rss_cap_mib=1e6)
    col = cmp.Collector('gt21', MAPS, tmp_path)
    cmp.compare_gt21_subject(his_path, lh_path, 'AB06', cfg, col, MAPS, 'synthetic')
    (al,) = col.align
    assert al['status'] == 'matched' and al['leg'] == 'right' and al['lag_samples'] == off and al['sign_of_best_fit'] == 'same'
    assert al['time_offset_s'] == pytest.approx(100.0 + off * 0.005) and al['align_rms_Nm_kg'] < 1e-9
    assert al['other_leg_rms_Nm_kg'] > 0.5
    rows = {r['column']: r for r in col.overall_rows()}
    assert rows['ankle_angle']['n_matched'] == 1000 and rows['ankle_angle']['bias'] == pytest.approx(0.01 * 180 / math.pi, abs=1e-9)
    assert rows['ankle_angle']['rms'] == pytest.approx(0.01 * 180 / math.pi, abs=1e-9) and rows['ankle_angle']['frac_exceed'] == 0.0
    assert rows['ankle_angle']['corr'] == pytest.approx(1.0, abs=1e-9)
    assert rows['ankle_moment']['rms'] < 1e-9 and rows['ankle_moment']['n_positions'] == 1000
    assert rows['cop_anterior']['bias'] == pytest.approx(0.005, abs=1e-9)
    assert rows['vertical_force']['n_matched'] == 990 and rows['vertical_force']['coverage_his'] == pytest.approx(0.99)
    assert rows['vertical_force']['n_lh_only'] == 10 and rows['vertical_force']['n_his_only'] == 0   # 10 unmeasured training rows are NaN
    tasks = {(r['task'], r['column']): r for r in col.rows if r['scope'] == 'subject_task'}
    assert tasks[('level_walking', 'ankle_moment')]['n_positions'] == 500 and tasks[('incline_walking', 'ankle_moment')]['n_positions'] == 500
    assert not col.unmatched


def test_gt21_unpaired_and_failed_alignment_are_listed_not_hidden(tmp_path):
    his_path, lh_path, _ = write_gt21_inputs(tmp_path)
    # the same LocoHub file, but the training recording carries a different name: nothing pairs, both sides are listed
    t = pq.read_table(his_path).to_pydict()
    t['recording_id'] = ['AB06|other_name'] * len(t['time_s'])
    other = tmp_path / 'his_other.parquet'
    pq.write_table(pa.table(t), other)
    col = cmp.Collector('gt21', MAPS, tmp_path)
    cmp.compare_gt21_subject(other, lh_path, 'AB06', cmp.Cfg(rss_cap_mib=1e6), col, MAPS)
    reasons = {(u['side'], u['reason']) for u in col.unmatched}
    assert ('locohub', 'no training recording with this name') in reasons
    assert any(s == 'training' for s, _ in reasons) and col.align[0]['status'] == 'no_candidate'
    # a training moment that is unrelated noise of the same name fails the alignment guard and stays out of the statistics
    t = pq.read_table(his_path).to_pydict()
    t[BY_NAME['ankle_moment'].his] = list(noise(len(t['time_s']), 99))
    bad = tmp_path / 'his_bad.parquet'
    pq.write_table(pa.table(t), bad)
    col = cmp.Collector('gt21', MAPS, tmp_path)
    cmp.compare_gt21_subject(bad, lh_path, 'AB06', cmp.Cfg(rss_cap_mib=1e6), col, MAPS)
    assert col.align[0]['status'] == 'alignment_failed'
    assert all(r['n_positions'] == 0 for r in col.overall_rows())
    assert any('alignment failed' in u['reason'] for u in col.unmatched)


def test_gt21_root_prefers_finished_rb07_over_r2(tmp_path):
    for name in ('gt21_rb06_export_AB06_r2', 'gt21_rb07_export_AB06', 'gt21_rb06_export_AB07_r2', 'gt21_rb07_export_AB07'):
        (tmp_path / name).mkdir()
    for name in ('gt21_rb06_export_AB06_r2', 'gt21_rb07_export_AB06', 'gt21_rb06_export_AB07_r2'):
        (tmp_path / name / 'time.parquet').write_bytes(b'')
        (tmp_path / name / 'run_summary.json').write_text('{}')
    assert cmp.gt21_root(tmp_path, 'AB06')[1] == 'rb07'
    assert cmp.gt21_root(tmp_path, 'AB07')[1] == 'rb06_r2'            # rb07 folder exists but has no run_summary.json yet
    assert cmp.gt21_root(tmp_path, 'AB08')[0] is None


# ------------------------------------------------------------------------------------------------ UM21 end to end
def write_um21_inputs(tmp_path, start=40):
    m = 2999
    t = np.arange(m) * 0.005
    frame = start + 100.0 * t                        # his time_s = (frame - start) / 100
    his_cols = {'recording_id': ['UM21_AB01|Tread_i0_s1_seg03'] * m + ['UM21_AB01|Run_2x5'] * 200,
                'subject': ['UM21_AB01'] * (m + 200), 'task': ['level_walking'] * (m + 200),
                'time_s': np.r_[t, np.arange(200) * 0.005]}
    g = {mp.name: (lambda f, k=k: G(f + 3.0 * k)) for k, mp in enumerate(MAPS)}      # a different known shape per column
    for mp in MAPS:
        vals = g[mp.name](frame) / mp.scale
        his_cols[mp.his] = np.r_[vals, np.zeros(200)]
    his_cols['fz_measured'] = np.ones(m + 200, bool)
    his_cols['cop_ok'] = np.ones(m + 200, np.float32)
    ph = {k: [] for k in ('source_recording_id', 'observation_id', 'reference_side', 'subject', 'phase_ipsi')}
    cols = {mp.lh.format(R='ipsi'): [] for mp in MAPS if mp.name != 'vertical_force'}      # package v4 has no force
    rec = 'um21:Streaming/AB01/Tread/i0'
    strides = [(100 + 100 * k, 199 + 100 * k) for k in range(16)]
    for a, b in strides + [(100, 199)]:
        side = 'right' if (a, b) != (100, 199) or len(ph['observation_id']) < 16 * 150 else 'left'
        f = a + np.arange(150) * (b - a) / 149
        ph['source_recording_id'] += [rec] * 150
        ph['observation_id'] += [f'{rec}:{side}:frames:{a}:{b}'] * 150
        ph['reference_side'] += [side] * 150
        ph['subject'] += ['UM21_AB01'] * 150
        ph['phase_ipsi'] += list(np.linspace(0, 100, 150))
        for mp in MAPS:
            if mp.name == 'vertical_force':
                continue
            v = g[mp.name](f) if side == 'right' else np.full(150, 777.0)           # the left-leg stride must be ignored
            cols[mp.lh.format(R='ipsi')] += list((v - mp.lh_offset) / mp.scale)
    his_path, lh_path = tmp_path / 'his_um.parquet', tmp_path / 'phase.parquet'
    pq.write_table(pa.table(his_cols), his_path, row_group_size=500)
    pq.write_table(pa.table({**ph, **cols}), lh_path, row_group_size=450)
    return his_path, lh_path


def test_um21_subject_finds_segment_start_and_compares_stride_windows(tmp_path):
    his_path, lh_path = write_um21_inputs(tmp_path, start=40)
    col = cmp.Collector('um21', MAPS, tmp_path)
    cmp.compare_um21_subject(his_path, lh_path, 'AB01', cmp.Cfg(rss_cap_mib=1e6), col, MAPS)
    seg = [a for a in col.align if a.get('his_recording', '').endswith('seg03')]
    assert len(seg) == 1 and seg[0]['status'] == 'matched' and seg[0]['segment_start_frame'] == 40
    assert seg[0]['strides'] == 14 and seg[0]['rows_compared'] == 14 * 150     # k = 14, 15 end after the segment
    left = [a for a in col.align if a['status'] == 'strides_not_in_a_matched_segment']
    assert len(left) == 1 and left[0]['strides'] == 2
    rows = {r['column']: r for r in col.overall_rows()}
    assert rows['ankle_moment']['n_matched'] == 14 * 150 and abs(rows['ankle_moment']['bias']) < 2e-3
    assert rows['ankle_moment']['p95_abs'] < 2e-3 and rows['ankle_moment']['corr'] > 0.9999
    assert rows['ankle_angle']['frac_exceed'] == 0.0
    assert rows['vertical_force']['n_matched'] == 0 and rows['vertical_force']['coverage_lh'] == 0.0
    assert 'vertical_force' in col.unavailable
    assert any('Run_2x5' in u['recording'] for u in col.unmatched)               # not a treadmill collection
    assert {r['task'] for r in col.rows if r['scope'] == 'subject_task'} == {'level_walking'}


def test_um21_comparison_reports_a_constant_cop_difference(tmp_path):
    his_path, lh_path = write_um21_inputs(tmp_path, start=77)
    col = cmp.Collector('um21', MAPS, tmp_path)
    maps = cmp.column_maps(0.100)
    cmp.compare_um21_subject(his_path, lh_path, 'AB01', cmp.Cfg(rss_cap_mib=1e6), col, maps)
    seg = [a for a in col.align if a.get('his_recording', '').endswith('seg03')][0]
    assert seg['segment_start_frame'] == 77
    # The training file is built from the same shapes with the origin shift included, so the bias is 0; with a different
    # shift the reported bias moves by exactly that much (the shift is a stated assumption, not a fitted value).
    col2 = cmp.Collector('um21', cmp.column_maps(0.120), tmp_path)
    cmp.compare_um21_subject(his_path, lh_path, 'AB01', cmp.Cfg(rss_cap_mib=1e6), col2, cmp.column_maps(0.120))
    b1 = {r['column']: r for r in col.overall_rows()}['cop_anterior']['bias']
    b2 = {r['column']: r for r in col2.overall_rows()}['cop_anterior']['bias']
    assert abs(b1) < 2e-3 and b2 - b1 == pytest.approx(-0.020, abs=2e-3)


def test_run_refuses_a_nonempty_output_directory_and_gt21_needs_subjects(tmp_path):
    with pytest.raises(SystemExit):
        cmp.main(['run', '--dataset', 'gt21', '--out-dir', str(tmp_path / 'new')])
    (tmp_path / 'full').mkdir()
    (tmp_path / 'full' / 'x').write_text('1')
    args = cmp.build_parser().parse_args(['run', '--dataset', 'um21', '--out-dir', str(tmp_path / 'full'), '--his-file', str(tmp_path / 'none.parquet')])
    with pytest.raises(SystemExit):
        cmp.run(args)


def test_name_match_training_ids_repeat_the_mode():
    assert cmp.name_match('treadmill_treadmill_01_01_speed_0.50_seg01', 'treadmill_01_01')
    assert cmp.name_match('ramp_ramp_1_l_01_01_walk-rampdescent_seg01+2', 'ramp_1_l_01_01')
    assert not cmp.name_match('treadmill_treadmill_02_01_speed_0.55_seg01', 'treadmill_01_01')


def test_best_alignment_finds_short_gappy_segment_in_periodic_series():
    # synthetic: periodic gait-like series, a short copy with gaps taken at a known lag (and a sign flip)
    rng = np.random.default_rng(7)
    k = np.arange(4000)
    y = np.sin(2 * np.pi * k / 200.0) * (1 + 0.3 * np.sin(2 * np.pi * k / 1100.0)) + 0.05 * rng.standard_normal(4000)
    x = y[1288:1288 + 300].copy() * -1.0
    x[100:140] = np.nan
    fit = cmp.best_alignment(x, y, 100)
    assert fit['lag'] == 1288 and fit['sign'] == -1 and fit['rms'] < 1e-12


def test_name_match_ignores_letter_case_of_the_recording_name():
    assert cmp.name_match('treadmill_Treadmill_01_01_speed_0.50_seg01', 'Treadmill_01_01')
    assert cmp.name_match('ramp_Ramp_2_R_01_01_rampascent_seg01+1', 'Ramp_2_R_01_01')
    assert not cmp.name_match('ramp_Ramp_2_R_01_01_rampascent_seg01', 'Ramp_2_R_01_02')


# ------------------------------------------------------------------------------------------------ wrap classifier (SYNTHETIC)
def test_classify_wrap_rule_on_made_up_offsets():
    # SYNTHETIC: offsets (training minus LocoHub) with known classes under the stated rule
    y = np.zeros(12)
    d = np.array([0.0, 5.0, 80.0, 89.0, 120.0, 150.0, 170.0, 200.0, 360.0, 350.0, -340.0, 720.0 + 15.0])
    w, k, diff = cmp.classify_wrap(d, y)
    #            0     5     80    89    120   150    170   200   360   350  -340  735
    assert list(w) == [False, False, False, False, False, False, True, True, True, True, True, True]
    assert list(k[6:]) == [1, 1, 2, 2, -2, 4]
    # exactly 20 degrees from a multiple counts, 21 does not; exactly 90 is not past 90
    w2, _, _ = cmp.classify_wrap(np.array([160.0, 159.0, 90.0, 91.0]), np.zeros(4))
    assert list(w2) == [True, False, False, False]      # 91 is 89 from 180: not within 20
    w3, _, _ = cmp.classify_wrap(np.array([np.nan, 360.0]), np.array([0.0, np.nan]))
    assert not w3.any()


def test_widen_marks_two_samples_each_side():
    m = np.zeros(12, bool)
    m[5] = True
    assert list(np.flatnonzero(cmp.widen(m))) == [3, 4, 5, 6, 7]
    m2 = np.zeros(6, bool)
    m2[0] = True
    assert list(np.flatnonzero(cmp.widen(m2))) == [0, 1, 2]
    assert not cmp.widen(np.zeros(4, bool)).any()


def test_wrap_variants_correct_by_known_multiples():
    # SYNTHETIC: 100 clean samples with a 3 degree offset, 10 whole-turn wraps (+360), 5 half-turn flips (+180), 4 odd large offsets (+130)
    rng = np.random.default_rng(7)
    y = rng.normal(0, 10, 119)
    x = y + 3.0
    x[100:110] += 360.0
    x[110:115] += 180.0
    x[115:119] += 130.0
    w, k, v = cmp.wrap_variants(x, y)
    assert int(w.sum()) == 15 and not w[115:].any()
    nx, ny = v['non_wrapped']
    assert len(nx) == 104 and np.mean(nx[:100] - ny[:100]) == pytest.approx(3.0)
    c360x, c360y = v['corrected_360']
    assert len(c360x) == 114       # the 5 half-turn flips are left out of the whole-turn-only correction
    assert np.abs(c360x[:110] - c360y[:110] - 3.0).max() < 1e-9
    callx, cally = v['corrected_all']
    assert len(callx) == 119 and np.abs(callx[:115] - cally[:115] - 3.0).max() < 1e-9
    assert np.mean(callx[115:] - cally[115:]) == pytest.approx(133.0)    # untouched: not a wrap under the rule


def test_gt21_wrap_analysis_end_to_end_on_made_up_wraps(tmp_path):
    # SYNTHETIC: training ankle angle gets +360 on rows 100-199 and +180 on rows 400-449; velocity gets a spike at the first wrap row
    his_path, lh_path, off = write_gt21_inputs(tmp_path)
    t = pq.read_table(his_path).to_pandas()
    t.loc[100:199, 'ankle_dorsiflexion_angle_ipsi_rad'] += 2 * math.pi
    t.loc[400:449, 'ankle_dorsiflexion_angle_ipsi_rad'] += math.pi
    vel = t['dtheta_raw'].to_numpy().copy()
    vel[100] += 1000.0 / (180 / math.pi)
    t['dtheta_raw'] = vel
    pq.write_table(pa.Table.from_pandas(t, preserve_index=False), tmp_path / 'his2.parquet', row_group_size=300)
    col = cmp.Collector('gt21', MAPS, tmp_path)
    col.wrap = cmp.WrapCollector('gt21', MAPS)
    cmp.compare_gt21_subject(tmp_path / 'his2.parquet', lh_path, 'AB06', cmp.Cfg(rss_cap_mib=1e6, wrap_analysis=True), col, MAPS, 'synthetic')
    stats, counts, recs = col.wrap.rows()
    c = {(r['scope'], r['column']): r for r in counts}
    assert c[('dataset', 'ankle_angle')]['n_wrapped'] == 150 and c[('dataset', 'ankle_angle')]['n_whole_turn'] == 100
    assert c[('dataset', 'ankle_angle')]['n_half_turn'] == 50 and c[('subject', 'ankle_angle')]['n_wrapped'] == 150
    assert c[('dataset', 'shank_angle')]['n_wrapped'] == 0
    s = {(r['scope'], r['column'], r['variant']): r for r in stats}
    bias = 0.01 * 180 / math.pi
    assert s[('dataset', 'ankle_angle', 'non_wrapped')]['n_matched'] == 850
    assert s[('dataset', 'ankle_angle', 'non_wrapped')]['bias'] == pytest.approx(bias, abs=1e-9)
    assert s[('dataset', 'ankle_angle', 'corrected_all')]['bias'] == pytest.approx(bias, abs=1e-9)
    assert s[('dataset', 'ankle_angle', 'corrected_all')]['n_matched'] == 1000
    assert s[('dataset', 'ankle_angle', 'corrected_360')]['n_matched'] == 950
    assert s[('dataset', 'ankle_angle', 'all')]['rms'] > 50
    # the existing, default statistics are unchanged by the flag
    assert {r['column']: r for r in col.overall_rows()}['ankle_angle']['n_matched'] == 1000
    # velocity: samples 98..102 are widened out (and none else are flagged around row 400-449 beyond 398..451)
    v_all, v_ex = s[('dataset', 'ankle_velocity', 'all')], s[('dataset', 'ankle_velocity', 'excluding_near_wrap')]
    kept = 1000 - (len(set(range(98, 202)) | set(range(398, 452))))
    assert v_ex['n_matched'] == kept
    assert v_ex['rms'] < 1e-6 < v_all['rms']
    (rec,) = [r for r in recs if r['column'] == 'ankle_angle']
    assert rec['n_wrapped'] == 150 and rec['wrapped_share'] == pytest.approx(0.15) and rec['his_recording'] == 'AB06|lg_01'
    assert rec['median_all_offset_deg'] == pytest.approx(bias, abs=1e-6)       # 850 of 1000 samples are unwrapped
    assert rec['median_wrapped_offset_deg'] == pytest.approx(360 + bias, abs=1e-6)     # 100 whole-turn vs 50 half-turn samples
    assert [r['n_wrapped'] for r in recs if r['column'] == 'foot_angle'] == [0]
