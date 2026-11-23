"""Synthetic fixtures only (honestly synthetic): a tiny fake participant with known values."""
import json
from pathlib import Path

import numpy as np
import scipy.io as sio

from contributor_tools import audit_gt23_x01 as audit
from contributor_tools import gt23_source_reader as rd
from contributor_tools import run_gt23_x01 as runner

N = 50
T = np.arange(N) / 200.0


def write_csv(path, cols, n=N):
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(cols)
    lines = [','.join(names)]
    for i in range(n):
        lines.append(','.join('NaN' if np.isnan(cols[n][i]) else repr(float(cols[n][i])) for n in names))
    path.write_text('\n'.join(lines) + '\n')


def make_source(root, drop_marker=None, short_euler=False):
    raw = root / 'RawData' / 'AB01'
    rec = raw / 'CSV_Data' / 'normal_walk_1'
    fz = np.where((np.arange(N) % 20) < 10, 100.0, 0.0)
    for ch in rd.CHANNELS:
        cols = {'time': T, 'a': np.linspace(0.1, 1 / 3, N), 'b': np.where(np.arange(N) % 7 == 0, np.nan, 2.5)}
        if ch == 'GroundFrame_GRFs':
            cols = {'time': T, 'LForceY_Vertical': fz, 'RForceY_Vertical': np.zeros(N), 'LCOPX': np.full(N, np.nan)}
        if ch == 'Raw_EMGs':  # 2000 Hz: ten rows per 200 Hz row
            cols = {'time': np.arange(10 * N) / 2000.0, 'emg': np.linspace(0, 1, 10 * N)}
        write_csv(rec / f'{ch}.csv', cols, 10 * N if ch == 'Raw_EMGs' else N)
    markers = ['EXTRA0'] + [m for m in rd.NEEDED_MARKERS if m != drop_marker][:5] + ['EXTRA1'] + [m for m in rd.NEEDED_MARKERS if m != drop_marker][5:] + ['EXTRA']
    head = ['PathFileType\t4\t(X/Y/Z)\tx.trc', 'DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits',
            f'200\t200\t{N}\t{len(markers)}\tmm', 'Frame#\tTime\t' + '\t'.join(m + '\t\t' for m in markers),
            '\t\t' + '\t'.join(f'X{i}\tY{i}\tZ{i}' for i in range(len(markers))), '']
    rows = []
    for i in range(N):
        vals = []
        for k, m in enumerate(markers):
            vals += ['', '', ''] if (m == 'LASI' and i < 10) else [f'{i}.5', f'{k}.25', '3.0']
        rows.append(f'{i + 1}\t{T[i]}\t' + '\t'.join(vals))
    (raw / 'MarkerData').mkdir(parents=True)
    (raw / 'MarkerData' / 'normal_walk_1.trc').write_text('\n'.join(head + rows) + '\n')
    eu = {'time': T[:N - 3 if short_euler else N], 'pelvis_Z': np.zeros(N - 3 if short_euler else N)}
    (raw / 'Transforms_Euler').mkdir()
    lines = ['time,pelvis_Z'] + [f'{t},0.0' for t in eu['time']]
    (raw / 'Transforms_Euler' / 'normal_walk_1.csv').write_text('\n'.join(lines) + '\n')
    (raw / 'Models').mkdir()
    (raw / 'Models' / 'm.osim').write_text('model')
    (raw / 'MotionFile_EH').mkdir()
    (raw / 'MotionFile_EH' / 'IK_results.mot').write_text('ik')
    seg = root / 'Segmentation' / 'AB01'
    seg.mkdir(parents=True)
    sio.savemat(seg / 'normal_walk_1_left_parsing.mat', {'left': np.array([[0.0, 0.1], [0.1, 0.2]]), 'right': np.zeros((0, 2))})
    sio.savemat(seg / 'normal_walk_1_right_parsing.mat', {'right': np.array([[0.0, 0.1]])})
    sio.savemat(seg / 'sit_to_stand_1_parsing.mat', {'left_sitting': np.array([[0.0, 1.0]]), 'left_standing': np.zeros((0, 2)),
                                                     'right_sitting': np.array([[0.0, 1.0], [1.0, 2.0]]), 'types': np.array(['sitting', 'standing'], dtype=object)})
    sio.savemat(seg / 'stray_parsing.mat', {'left': np.zeros((0, 2)), 'right': np.zeros((0, 2))})
    return rd.Subject(root, 'AB01')


def test_channel_roundtrip_is_lossless_and_nan_stays_nan(tmp_path):
    subj = make_source(tmp_path / 'src')
    facts, kept = rd.convert_channel(subj.raw / 'CSV_Data/normal_walk_1/Joint_Angle.csv', tmp_path / 'o.parquet')
    back = rd.parquet_values_digest(tmp_path / 'o.parquet')
    assert facts['rows'] == N and back['rows'] == N and back['values_sha256'] == facts['values_sha256']
    import pyarrow.parquet as pq
    b = pq.read_table(tmp_path / 'o.parquet').column('b').to_numpy()
    assert np.isnan(b[0]) and np.isnan(b[7]) and b[1] == 2.5
    assert pq.read_table(tmp_path / 'o.parquet').column('b').null_count == 0
    assert abs(facts['finite_by_column']['b'] - (1 - 8 / N)) < 1e-6 and facts['time_step_max_abs_dev_s'] < 1e-12


def test_recording_record_known_values(tmp_path):
    subj = make_source(tmp_path / 'src')
    out = tmp_path / 'out'
    e = rd.recording_record(subj, 'normal_walk_1', out, [])
    assert e['status'] == 'ok', e['issues']
    assert len(e['channels']) == 10 and e['channel_rows']['Raw_EMGs'] == 10 * N and e['channel_rows']['Joint_Angle'] == N
    m = e['markers']
    assert m['rows'] == N and m['missing_needed'] == []
    assert m['finite_share']['LASI'] == (N - 10) / N and m['finite_share']['RASI'] == 1.0
    # left plate stance is the first 10 of every 20 samples (50 samples: 10+10+5 = 25 stance... indices 0-9,20-29,40-49 = 30)
    assert m['stance_samples'] == {'L': 30, 'R': 0}
    assert m['finite_share_in_own_stance']['LASI'] == round(20 / 30, 6)  # LASI missing in rows 0-9, stance rows 0-9 lost
    assert m['finite_share_in_own_stance']['RASI'] is None  # no right-plate stance: not claimed
    assert e['plates']['L']['vertical_finite_share'] == 1.0 and e['plates']['R']['vertical_finite_share'] == 1.0


def test_missing_marker_and_row_mismatch_are_named_not_repaired(tmp_path):
    subj = make_source(tmp_path / 'src', drop_marker='RTHC', short_euler=True)
    e = rd.recording_record(subj, 'normal_walk_1', tmp_path / 'out', [])
    assert e['status'] == 'issues'
    assert any('RTHC' in i for i in e['issues']) and any('Transforms_Euler rows' in i for i in e['issues'])


def test_event_files_assigned_and_counted(tmp_path):
    subj = make_source(tmp_path / 'src')
    events, unassigned = rd.event_ledger(subj)
    by = {e['file']: e for e in events}
    assert by['normal_walk_1_left_parsing.mat']['recording'] == 'normal_walk_1'
    assert (by['normal_walk_1_left_parsing.mat']['windows_left'], by['normal_walk_1_left_parsing.mat']['windows_right']) == (2, 0)
    assert by['normal_walk_1_right_parsing.mat']['windows_right'] == 1
    typed = by['sit_to_stand_1_parsing.mat']
    assert (typed['windows_left'], typed['windows_right'], typed['issues']) == (1, 2, [])
    assert typed['windows_by_key']['right_sitting'] == 2
    assert sorted(unassigned) == ['sit_to_stand_1_parsing', 'stray_parsing']  # typed file also has no recording here: sit_to_stand_1 is not in the fixture
    assert by['sit_to_stand_1_parsing.mat']['recording'] is None


def test_assign_prefers_exact_then_longest_prefix():
    got, un = rd.assign_parsing_files(['jump_1_2_parsing', 'jump_1_left_parsing', 'x_parsing'], {'jump_1', 'jump_1_2'})
    assert got == {'jump_1_2_parsing': 'jump_1_2', 'jump_1_left_parsing': 'jump_1'} and un == ['x_parsing']


def test_readme_masses():
    assert rd.parse_readme_masses('AB01: 78.9 kg\nAB03: 113.5 kg\nother')['AB03'] == 113.5


def test_runner_and_independent_audit_agree_then_catch_tamper(tmp_path, monkeypatch):
    src = tmp_path / 'src'
    make_source(src)
    base = tmp_path / 'base'
    base.mkdir()
    monkeypatch.setattr(runner, 'BASE', base)
    code = runner.run(runner.argparse.Namespace(output_root=base / 'b', subject='AB01', records=None, source=src))
    assert code == 0
    summ = json.loads((base / 'b/run_summary.json').read_text())
    assert summ['status'] == 'participant_done_unreviewed' and summ['recordings_done'] == 1
    evroot = tmp_path / 'ev'
    evroot.mkdir()
    subj = rd.Subject(src, 'AB01')
    evs, _ = rd.event_ledger(subj)
    (evroot / 'events_AB01.json').write_text(json.dumps({'files': evs}))
    rep_args = audit.argparse.Namespace(output_root=tmp_path / 'a1', batch_root=base / 'b', events_root=evroot, subject='AB01', records=None, source=src)
    assert audit.audit(rep_args) == 0
    # tamper with a companion: the audit must fail
    p = base / 'b/normal_walk_1/Joint_Angle.parquet'
    p.write_bytes(p.read_bytes()[:-1] + b'\x00')
    rep_args2 = audit.argparse.Namespace(output_root=tmp_path / 'a2', batch_root=base / 'b', events_root=evroot, subject='AB01', records=None, source=src)
    try:
        code2 = audit.audit(rep_args2)
    except Exception:
        code2 = 1
    assert code2 == 1


def test_runner_refuses_output_outside_base_or_inside_source(tmp_path):
    import pytest
    with pytest.raises(runner.RunError):
        runner.run(runner.argparse.Namespace(output_root=tmp_path / 'x', subject='AB01', records=None, source=tmp_path))
