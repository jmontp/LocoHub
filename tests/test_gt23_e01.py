"""GT23-E01 tests. All fixtures are SYNTHETIC (tiny made-up recordings with known ramps); they do not regenerate any
scientific dataset. They check the export rules against independently known values, and that the independent readback
passes on a correct export and fails on a tampered one."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools import audit_gt23_e01 as au
from contributor_tools import gt23_export as ex
from contributor_tools import run_gt23_e01 as rn

SUBJECT = 'AB05'
MASS = 71.5
N = 1200


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_parquet(path, cols):
    schema = pa.schema([(k, pa.float64()) for k in cols])
    pq.write_table(pa.Table.from_arrays([pa.array(v, type=pa.float64()) for v in cols.values()], schema=schema), str(path),
                   row_group_size=500)


def c06_columns():
    t = np.arange(N) / 200.0
    idx = np.arange(N, dtype=float)
    cols = {'time_s': t, 'pelvis_sagittal_angle_rad': 0.001 * idx}
    for side, k in (('left', 1.0), ('right', 2.0)):
        for _tpl, fam, src, _sign, _hold in ex.column_sources('x', side):
            pass
        for tpl, fam, src, sign, hold in (s for s in ex.column_sources('x', side) if s[1] == 'c06'):
            cols[src] = k * idx + (hash(src) % 7)
    return cols


def m01_columns(c06):
    cols = {'time_s': c06['time_s']}
    idx = np.arange(N, dtype=float)
    for side in ('left', 'right'):
        for tpl, fam, src, sign, hold in (s for s in ex.column_sources('x', side) if s[1] == 'm01'):
            if src.endswith('_BW'):
                n_name = src[:-3] + '_N'
                cols[src] = c06[n_name] / (MASS * ex.G)
            else:
                cols[src] = 0.5 * idx * (1 if side == 'left' else -1) + (hash(src) % 5)
    return cols


def build_inputs(base):
    base.mkdir(parents=True)
    roots = rn.roots_for(SUBJECT, str(base))
    for k in roots:
        (Path(roots[k])).mkdir(parents=True)
    recs = {'normal_walk_1': 'gait', 'jump_1': 'window_pelvis', 'poses_1': 'continuous'}
    c06_led, m01_led, s01_led, segments, windows = [], [], [], [], []
    for rec, tclass in recs.items():
        c = c06_columns()
        if rec == 'normal_walk_1':
            for nm in ('grf_lab_y_right_N', 'grf_lab_x_right_N', 'grf_lab_z_right_N', 'cop_anterior_right_m'):
                c[nm] = np.full(N, np.nan)
        if rec == 'poses_1':
            c['grf_anterior_left_N'] = np.full(N, np.nan)
        m = m01_columns(c)
        write_parquet(Path(roots['c06']) / f'{rec}.parquet', c)
        write_parquet(Path(roots['m01']) / f'{rec}.parquet', m)
        held = {'grf_anterior_left_N': 'task has no single forward direction (D-GT23-C01-1 = C); lab-axis force columns hold the force'} if rec == 'poses_1' else {}
        if rec == 'normal_walk_1':
            held = {k: ex.PLATE_MISSING for k in ('grf_lab_y_right_N', 'grf_lab_x_right_N', 'grf_lab_z_right_N', 'cop_anterior_right_m')}
        c06_led.append({'recording': rec, 'rows': N, 'held_columns': held,
                        'output': {'file': f'{rec}.parquet', 'sha256': sha(Path(roots['c06']) / f'{rec}.parquet'), 'rows': N}})
        if rec == 'normal_walk_1':
            entry = {'action': 'rescale', 'how_known': 'exact', 'note_key': 'rescaled', 'factor': 1.1035, 'mass_used_kg': 78.9, 'own_mass_kg': 71.5, 'audit_provenance': {'plausible_divisors_kg': [78.9]}}
        else:
            entry = {'action': 'keep', 'how_known': None, 'note_key': 'cannot_be_told', 'factor': None, 'mass_used_kg': None, 'own_mass_kg': 71.5, 'audit_provenance': {}}
        m01_led.append({'recording': rec, 'subject': SUBJECT, 'rows': N, 'body_weight_mass_kg': MASS,
                        'output': {'file': f'{rec}.parquet', 'sha256': sha(Path(roots['m01']) / f'{rec}.parquet'), 'rows': N}, **entry})
        task = rec.rsplit('_', 1)[0]
        s01_led.append({'recording': rec, 'subject': SUBJECT, 'status': 'ok', 'rows': N, 'task': task, 'task_class': tclass,
                        'disposition': {'gait': 'gait_strides', 'window_pelvis': 'window_segments', 'continuous': 'continuous_recording'}[tclass],
                        'rule': 'synthetic rule', 'authors_windows': 0})

    def seg(rec, task, idx, side, a, b, status='accepted', reason=None, file=None, match=()):
        return {'authors_file': file, 'authors_match': list(match), 'disposition': 'accepted_x' if status == 'accepted' else 'excluded',
                'duration_s': (b - a) / 200.0, 'end_index': b, 'end_s': b / 200.0, 'index': idx,
                'label_source': 'authors_window' if file else 'unknown', 'peak_speed_m_s': None, 'reason': reason, 'recording': rec,
                'rule': 'synthetic rule', 'segment_id': f'{SUBJECT}/{rec}/{side}/{a:07d}', 'side': side, 'start_index': a,
                'start_s': a / 200.0, 'status': status, 'subject': SUBJECT, 'task': task}
    segments += [seg('normal_walk_1', 'normal_walk', 0, 'L', 100, 300, file='normal_walk_1_2-0_parsing.mat',
                     match=['normal_walk_1_2-0_parsing.mat:left:0']),
                 seg('normal_walk_1', 'normal_walk', 1, 'L', 300, 520),
                 seg('normal_walk_1', 'normal_walk', 2, 'L', 520, 530, status='excluded', reason='shorter_than_0.3_s'),
                 seg('normal_walk_1', 'normal_walk', 3, 'R', 130, 331),
                 seg('jump_1', 'jump', 0, 'both', 400, 520),
                 seg('jump_1', 'jump', 1, 'both', 700, 790, file='jump_1_fb_parsing.mat', match=['jump_1_fb_parsing.mat:left:0'])]
    windows += [{'subject': SUBJECT, 'recording': 'normal_walk_1', 'task': 'normal_walk', 'file': 'normal_walk_1_2-0_parsing.mat', 'key': 'left',
                 'row': 0, 'side': 'L', 'start': 0.5, 'end': 1.5, 'status': 'matched', 'reason': None, 'segment_index': 0},
                {'subject': SUBJECT, 'recording': 'normal_walk_1', 'task': 'normal_walk', 'file': 'normal_walk_1_2-0_parsing.mat', 'key': 'left',
                 'row': 1, 'side': 'L', 'start': 5.0, 'end': 5.5, 'status': 'missed', 'reason': 'no_record_starts_within_tolerance', 'segment_index': None},
                {'subject': SUBJECT, 'recording': 'jump_1', 'task': 'jump', 'file': 'jump_1_fb_parsing.mat', 'key': 'left', 'row': 0, 'side': 'L',
                 'start': 3.5, 'end': 3.95, 'status': 'matched', 'reason': None, 'segment_index': 1}]
    for name, rows in (('ledger', c06_led),):
        (Path(roots['c06']) / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    (Path(roots['m01']) / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in m01_led))
    (Path(roots['s01']) / 'ledger.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in s01_led))
    (Path(roots['s01']) / 'segments.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in segments))
    (Path(roots['s01']) / 'authors_windows.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in windows))
    return roots


@pytest.fixture(scope='module')
def export(tmp_path_factory):
    base = tmp_path_factory.mktemp('gt23e01') / 'inputs'
    build_inputs(base)
    out = base.parent / 'out'
    args = argparse.Namespace(subject=SUBJECT, output_root=str(out), records=None, base=str(base))
    assert rn.run(args) == 0
    return base, out


def rows(out, name, columns=None):
    return pq.read_table(str(out / f'{name}.parquet'), columns=columns).to_pandas()


# ------------------------------------------------------------------ pure rules with known values
def test_phase_samples_ramp_and_endpoints():
    x = 2.0 * np.arange(1000)
    v = ex.phase_samples(x, 100, 349)
    assert v[0] == 200.0 and v[-1] == 698.0
    assert np.allclose(v, 2.0 * (100 + np.arange(150) * 249 / 149.0), rtol=0, atol=1e-9)


def test_phase_samples_missing_neighbour_gives_nan_never_fills():
    x = np.arange(500, dtype=float)
    x[200] = np.nan
    v = ex.phase_samples(x, 100, 349)
    pos = 100 + np.arange(150) * 249 / 149.0
    expected_nan = (np.floor(pos) == 200) | ((np.floor(pos) == 199) & (pos % 1 != 0))
    assert np.array_equal(np.isnan(v), expected_nan)


def test_label_rules_known_cases():
    assert ex.authors_label('normal_walk_1', 'normal_walk_1_2-0_parsing.mat') == '2-0'
    assert ex.authors_label('lunges_1', 'lunges_1_parsing.mat') == ''
    assert ex.authors_label('step_ups', 'step_ups_1_left_parsing.mat') == 'left'
    assert ex.authors_label('normal_walk_1', None) is None
    with pytest.raises(ex.LabelError):
        ex.authors_label('normal_walk_1', 'jump_1_fb_parsing.mat')
    assert ex.classify('normal_walk', 'normal_walk_1', '2-0')[:2] == ('run', 'run_2-0')
    assert ex.classify('normal_walk', 'normal_walk_1', 'skip')[:2] == ('agility_drill', 'skip')
    fam, tid, info = ex.classify('normal_walk', 'normal_walk_1', None)
    assert (fam, tid) == ('functional_task', 'normal_walk_unlabelled') and 'speed_m_s' not in info
    fam, tid, info = ex.classify('incline_walk', 'incline_walk_1', 'down5')
    assert (fam, info['incline_deg']) == ('decline_walking', -5)
    assert 'incline_deg' not in ex.classify('incline_walk', 'incline_walk_1', None)[2]
    fam, tid, info = ex.classify('stairs', 'stairs_1_4', None)
    assert fam == 'stair_descent' and info['stair_rise_m'] == 0.152 and info['pass_number'] == 4 and 'step_number' not in info
    assert not any('height' in k for k in ex.classify('curb_up', 'curb_up_1', None)[2])
    with pytest.raises(ex.LabelError):
        ex.classify('normal_walk', 'normal_walk_1', '3-3')
    with pytest.raises(ex.LabelError):
        ex.classify('unknown_task', 'x_1', None)
    with pytest.raises(ex.LabelError):
        ex.classify('stairs', 'stairs_1_1', 'down')


def test_mass_notes_and_limits():
    entry = {'action': 'rescale', 'how_known': 'estimated', 'factor': 1.0416, 'mass_used_kg': 87.6, 'own_mass_kg': 84.1,
             'subject': 'AB09', 'audit_provenance': {'plausible_divisors_kg': []}, 'note_key': 'rescaled'}
    key, note = ex.mass_note(entry)
    assert key == 'rescaled_estimated' and '87.6' in note and '84.1' in note
    assert ex.ab09_divisor_limit(entry)
    assert not ex.ab09_divisor_limit({**entry, 'audit_provenance': {'plausible_divisors_kg': [87.57]}})
    assert ex.mass_key({'action': 'keep', 'note_key': 'own_mass_confirmed'}) == 'own_mass_confirmed'
    with pytest.raises(ValueError):
        ex.mass_key({'action': 'keep', 'note_key': 'mystery'})
    assert any('AB07' in x for x in ex.recording_limits('AB07', {**entry, 'subject': 'AB07'}, 'normal_walk'))
    assert any(x.startswith('curb_up') for x in ex.recording_limits('AB01', {**entry, 'subject': 'AB01'}, 'curb_up'))


def test_column_mapping_names_and_signs():
    cols = {c[0]: c for c in ex.column_sources('ipsi', 'left')}
    assert cols['knee_flexion_moment_ipsi_Nm_kg'][2] == 'knee_angle_l_moment_Nm_kg' and cols['knee_flexion_moment_ipsi_Nm_kg'][3] == -1.0
    assert cols['knee_flexion_power_ipsi_W_kg'][3] == 1.0
    assert cols['grf_vertical_ipsi_N'][2] == 'grf_lab_y_left_N'
    assert cols['grf_vertical_ipsi_BW'][2] == 'grf_lab_y_left_BW'
    assert cols['cop_anterior_ipsi_m'][2] == 'cop_anterior_left_m'
    names = ex.role_columns(('ipsi', 'contra'))
    assert len(names) == len(set(names)) == 1 + 2 * len(ex.LEG_SPECS)


# ------------------------------------------------------------------ end to end on the synthetic participant
def test_observation_counts_and_kinds(export):
    base, out = export
    s = json.loads((out / 'run_summary.json').read_text())
    # gait: 3 accepted strides (L, L, R) -> 3 cycles; window: 2 accepted spans x 2 legs -> 4 transfers; 3 continuous
    assert s['observations'] == {'individual_cycle': 3, 'transfer': 4, 'continuous_recording': 3}
    assert s['phase_rows'] == 7 * 150 and s['time_rows'] == 3 * N
    assert s['continuous_only_recordings'] == 1 and s['exclusions'] == 1
    assert s['exclusions_by_reason'] == {'shorter_than_0.3_s': 1}
    assert s['authors_windows'] == 3 and s['authors_windows_exported'] == 2


def test_every_observation_has_identity_and_150_grid(export):
    base, out = export
    df = rows(out, 'phase')
    grid = np.linspace(0, 100, 150)
    for key, g in df.groupby(['source_recording_id', 'observation_id', 'reference_side']):
        assert len(g) == 150 and np.array_equal(g['phase_ipsi'].to_numpy(), grid)
        assert g['subject'].iloc[0] == SUBJECT and g['task_info'].nunique() == 1
    assert df['reference_side'].isin(['left', 'right']).all()
    assert set(df['observation_type']) == {'individual_cycle', 'transfer'}
    t = rows(out, 'time')
    assert (t['reference_side'] == 'none').all() and set(t['observation_type']) == {'continuous_recording'}


def test_values_equal_known_ramp_and_signs(export):
    base, out = export
    df = rows(out, 'phase')
    g = df[(df['observation_id'] == f'{SUBJECT}/normal_walk_1/L/0000100') & (df['reference_side'] == 'left')].sort_values('phase_ipsi')
    c = c06_columns()
    pos = 100 + np.arange(150) * 200 / 149.0
    expected = np.interp(pos, np.arange(N), c['hip_flexion_angle_left_rad'])
    assert np.allclose(g['hip_flexion_angle_ipsi_rad'], expected, rtol=1e-12, atol=1e-9)
    m = m01_columns(c)
    exp_knee = -np.interp(pos, np.arange(N), m['knee_angle_l_moment_Nm_kg'])
    assert np.allclose(g['knee_flexion_moment_ipsi_Nm_kg'], exp_knee, rtol=1e-12, atol=1e-9)
    # power is not negated
    assert np.allclose(g['knee_flexion_power_ipsi_W_kg'], np.interp(pos, np.arange(N), m['knee_power_l_W_kg']), rtol=1e-12, atol=1e-9)
    # contralateral columns are the other leg over the same span
    assert np.allclose(g['hip_flexion_angle_contra_rad'], np.interp(pos, np.arange(N), c['hip_flexion_angle_right_rad']), rtol=1e-12, atol=1e-9)
    # body weights: N / (mass g)
    assert np.allclose(g['grf_vertical_ipsi_BW'] * MASS * ex.G, g['grf_vertical_ipsi_N'], rtol=1e-12, atol=1e-9)


def test_labels_only_where_s01_matched_and_no_invented_values(export):
    base, out = export
    df = rows(out, 'phase')
    first = df.drop_duplicates('observation_id').set_index('observation_id')
    matched = json.loads(first.loc[f'{SUBJECT}/normal_walk_1/L/0000100', 'task_info'])
    assert matched['authors_label'] == '2-0' and matched['speed_m_s'] == 2.0 and first.loc[f'{SUBJECT}/normal_walk_1/L/0000100', 'task'] == 'run'
    unknown = json.loads(first.loc[f'{SUBJECT}/normal_walk_1/L/0000300', 'task_info'])
    assert unknown['authors_label'] is None and unknown['label_source'] == 'unknown' and 'speed_m_s' not in unknown
    assert first.loc[f'{SUBJECT}/normal_walk_1/L/0000300', 'task'] == 'functional_task'
    jump_unknown = json.loads(first.loc[f'{SUBJECT}/jump_1/both/0000400', 'task_info'])
    assert jump_unknown['authors_label'] is None
    for info in (matched, unknown, jump_unknown):
        assert not any(k in info for k in ('curb_height_m', 'step_height_m', 'height_m', 'step_number'))


def test_window_spans_exported_for_both_legs_with_same_id(export):
    base, out = export
    df = rows(out, 'phase')
    w = df[df['observation_id'] == f'{SUBJECT}/jump_1/both/0000400']
    assert set(w['reference_side']) == {'left', 'right'} and set(w['observation_type']) == {'transfer'}
    left = w[w['reference_side'] == 'left'].sort_values('phase_ipsi')
    right = w[w['reference_side'] == 'right'].sort_values('phase_ipsi')
    assert np.allclose(left['hip_flexion_angle_ipsi_rad'].to_numpy(), right['hip_flexion_angle_contra_rad'].to_numpy())


def test_missing_right_plate_shows_gap_with_reason_not_zeros(export):
    base, out = export
    df = rows(out, 'phase')
    g = df[(df['observation_id'] == f'{SUBJECT}/normal_walk_1/L/0000100') & (df['reference_side'] == 'left')]
    assert g['grf_vertical_contra_N'].isna().all() and g['grf_vertical_contra_BW'].isna().all()
    held = json.loads(g['held_signals'].iloc[0])
    assert held['grf_vertical_contra_N'] == ex.PLATE_MISSING and 'grf_vertical_contra_BW' in held
    assert 'hip_flexion_angle_ipsi_rad' not in held
    # a column that holds data is never listed; the right leg's own columns are present and finite
    r = df[(df['observation_id'] == f'{SUBJECT}/normal_walk_1/R/0000130') & (df['reference_side'] == 'right')]
    assert r['hip_flexion_angle_ipsi_rad'].notna().all()
    assert json.loads(r['held_signals'].iloc[0])['grf_vertical_ipsi_N'] == ex.PLATE_MISSING


def test_continuous_only_recording_has_no_phase_and_keeps_held_column(export):
    base, out = export
    df = rows(out, 'phase')
    assert 'poses_1' not in ' '.join(df['source_recording_id'].unique())
    t = rows(out, 'time', ['source_recording_id', 'task_info', 'held_signals', 'grf_anterior_left_N', 'time_s'])
    p = t[t['source_recording_id'] == f'{SUBJECT}/poses_1']
    assert len(p) == N and p['grf_anterior_left_N'].isna().all()
    assert 'grf_anterior_left_N' in json.loads(p['held_signals'].iloc[0])
    assert json.loads(p['task_info'].iloc[0])['export_scope'] == 'continuous_only'
    assert (t.groupby('source_recording_id')['time_s'].apply(lambda s: bool(np.all(np.diff(s.to_numpy()) > 0)))).all()


def test_mass_note_and_units_note(export):
    base, out = export
    df = rows(out, 'phase', ['observation_id', 'task_info', 'subject_metadata'])
    info = json.loads(df[df['observation_id'] == f'{SUBJECT}/normal_walk_1/L/0000100']['task_info'].iloc[0])
    assert info['mass_note_key'] == 'rescaled_exact' and 'multiplied by 1.1035' in info['mass_note']
    other = json.loads(df[df['observation_id'] == f'{SUBJECT}/jump_1/both/0000400']['task_info'].iloc[0])
    assert other['mass_note_key'] == 'cannot_be_told'
    assert json.loads(df['subject_metadata'].iloc[0])['body_mass_kg'] == MASS
    readme = (out / 'README.md').read_text()
    assert 'N*m' in readme and 'per kilogram' in readme and 'AB09 divisor limit' in readme and 'AB07 right-foot marker offset limit' in readme


def test_never_overwrites_and_streams_by_row_group(export):
    base, out = export
    args = argparse.Namespace(subject=SUBJECT, output_root=str(out), records=None, base=str(base))
    with pytest.raises(rn.ExportError):
        rn.run(args)
    pf = pq.ParquetFile(str(out / 'phase.parquet'))
    assert max(pf.metadata.row_group(i).num_rows for i in range(pf.metadata.num_row_groups)) <= 3000
    pt = pq.ParquetFile(str(out / 'time.parquet'))
    assert max(pt.metadata.row_group(i).num_rows for i in range(pt.metadata.num_row_groups)) <= 4096


def test_changed_input_is_refused(export, tmp_path):
    base, _ = export
    roots = rn.roots_for(SUBJECT, str(base))
    c06 = Path(roots['c06']) / 'jump_1.parquet'
    original = c06.read_bytes()
    try:
        data = bytearray(original)
        data[-20] ^= 0xFF
        c06.write_bytes(bytes(data))
        args = argparse.Namespace(subject=SUBJECT, output_root=str(tmp_path / 'again'), records=['jump_1'], base=str(base))
        with pytest.raises(rn.ExportError, match='C06 output hash'):
            rn.run(args)
    finally:
        c06.write_bytes(original)


# ------------------------------------------------------------------ the independent readback
def audit_args(base, out, report_root, records=None):
    return argparse.Namespace(subject=SUBJECT, output_root=str(report_root), export_root=str(out), records=records, base=str(base))


def test_readback_passes_on_correct_export(export, tmp_path):
    base, out = export
    code = au.run_audit(audit_args(base, out, tmp_path / 'audit'))
    rep = json.loads((tmp_path / 'audit' / 'audit_report.json').read_text())
    assert code == 0, rep['failures']
    assert rep['observations'] == {'individual_cycle': 3, 'transfer': 4, 'continuous_recording': 3}
    assert rep['status'] == 'pass' and rep['max_abs_diff_phase_values'] < 1e-9


def test_readback_decodes_names_like_the_exporter_maps_them():
    for ref in ('left', 'right'):
        for token, side in (('ipsi', ref), ('contra', {'left': 'right', 'right': 'left'}[ref])):
            for name, fam, src, sign, hold in ex.column_sources(token, side):
                got = au.decode(name, ref, 'phase')
                assert got[:3] == (fam, src, sign), name
                assert got[3] == hold
    for side in ('left', 'right'):
        for name, fam, src, sign, hold in ex.column_sources(side, side):
            assert au.decode(name, 'left', 'time')[:3] == (fam, src, sign), name
    assert au.expected_signal_names('phase') == ex.role_columns(('ipsi', 'contra'))
    assert au.expected_signal_names('time') == ex.role_columns(('left', 'right'))


def tampered_copy(out, dst, mutate):
    dst.mkdir()
    for f in out.iterdir():
        (dst / f.name).write_bytes(f.read_bytes())
    mutate(dst)
    return dst


def rewrite_phase(dst, column, func):
    t = pq.read_table(str(dst / 'phase.parquet'))
    arr = t.column(column).to_numpy().copy()
    arr = func(arr)
    idx = t.schema.get_field_index(column)
    t = t.set_column(idx, column, pa.array(arr, type=pa.float64()))
    pq.write_table(t, str(dst / 'phase.parquet'), row_group_size=3000)
    summary = json.loads((dst / 'run_summary.json').read_text())
    summary['sha256']['phase.parquet'] = sha(dst / 'phase.parquet')
    (dst / 'run_summary.json').write_text(json.dumps(summary))


def test_readback_fails_when_a_value_changes(export, tmp_path):
    base, out = export

    def bump(dst):
        rewrite_phase(dst, 'ankle_dorsiflexion_angle_ipsi_rad', lambda a: np.where(np.arange(len(a)) == 77, a + 1e-3, a))
    dst = tampered_copy(out, tmp_path / 'bad1', bump)
    assert au.run_audit(audit_args(base, dst, tmp_path / 'rep1')) == 1
    rep = json.loads((tmp_path / 'rep1' / 'audit_report.json').read_text())
    assert 'phase_signal:values' in rep['failures']


def test_readback_fails_when_knee_sign_is_not_negated(export, tmp_path):
    base, out = export
    dst = tampered_copy(out, tmp_path / 'bad2', lambda d: rewrite_phase(d, 'knee_flexion_moment_ipsi_Nm_kg', lambda a: -a))
    assert au.run_audit(audit_args(base, dst, tmp_path / 'rep2')) == 1


def test_readback_fails_when_a_missing_value_is_zero_filled(export, tmp_path):
    base, out = export
    dst = tampered_copy(out, tmp_path / 'bad3', lambda d: rewrite_phase(d, 'grf_vertical_contra_N', lambda a: np.nan_to_num(a, nan=0.0)))
    assert au.run_audit(audit_args(base, dst, tmp_path / 'rep3')) == 1
    rep = json.loads((tmp_path / 'rep3' / 'audit_report.json').read_text())
    assert any(k.startswith('phase_signal:finite_pattern') or k.startswith('held:') for k in rep['failures'])


def test_readback_fails_when_an_observation_is_dropped(export, tmp_path):
    base, out = export

    def drop(dst):
        t = pq.read_table(str(dst / 'phase.parquet'))
        keep = np.arange(t.num_rows) >= 150
        pq.write_table(t.filter(pa.array(keep)), str(dst / 'phase.parquet'), row_group_size=3000)
        summary = json.loads((dst / 'run_summary.json').read_text())
        summary['sha256']['phase.parquet'] = sha(dst / 'phase.parquet')
        (dst / 'run_summary.json').write_text(json.dumps(summary))
    dst = tampered_copy(out, tmp_path / 'bad4', drop)
    assert au.run_audit(audit_args(base, dst, tmp_path / 'rep4')) == 1
    rep = json.loads((tmp_path / 'rep4' / 'audit_report.json').read_text())
    assert 'accounting:phase_observations_equal_s01' in rep['failures']


def test_readback_fails_when_a_label_is_invented(export, tmp_path):
    base, out = export

    def relabel(dst):
        t = pq.read_table(str(dst / 'phase.parquet'))
        info = t.column('task_info').to_pylist()
        oid = t.column('observation_id').to_pylist()
        new = []
        for i, o in zip(info, oid):
            d = json.loads(i)
            if o.endswith('/normal_walk_1/L/0000300'):
                d['speed_m_s'] = 1.2
            new.append(json.dumps(d, sort_keys=True, separators=(',', ':')))
        t = t.set_column(t.schema.get_field_index('task_info'), 'task_info', pa.array(new, type=pa.string()))
        pq.write_table(t, str(dst / 'phase.parquet'), row_group_size=3000)
        summary = json.loads((dst / 'run_summary.json').read_text())
        summary['sha256']['phase.parquet'] = sha(dst / 'phase.parquet')
        (dst / 'run_summary.json').write_text(json.dumps(summary))
    dst = tampered_copy(out, tmp_path / 'bad5', relabel)
    assert au.run_audit(audit_args(base, dst, tmp_path / 'rep5')) == 1
    rep = json.loads((tmp_path / 'rep5' / 'audit_report.json').read_text())
    assert 'labels:speed_traceable_to_readme' in rep['failures']


def test_readme_facts_parse_known_lines():
    text = Path(au.ROOT / au.README).read_text()
    facts = au.readme_facts(text)
    assert facts['normal_walk']['labels']['2-5']['speed'] == 2.5 and facts['normal_walk']['labels']['skip']['speed'] == 1.2
    assert facts['incline_walk']['header_speed'] == 1.2 and facts['incline_walk']['labels']['down10']['incline'] == -10
    assert au.readme_masses(text)['AB03'] == 113.5
