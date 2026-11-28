"""GT23-S01 tests. Everything here is SYNTHETIC: constructed traces with known crossing times, not GT23 data."""
import json
from pathlib import Path

import numpy as np
import pytest
import scipy.io as sio

from contributor_tools import gt23_segmentation as seg
from contributor_tools import run_gt23_s01 as runner

DT = 0.005


def trace(n, rises, width):
    """Force 0 N except 100 N for ``width`` samples after each rise index."""
    f = np.zeros(n)
    for r in rises:
        f[r:r + width] = 100.0
    return f


def test_rising_crossing_is_first_sample_at_or_above_threshold():
    f = np.zeros(100)
    f[10:20] = [5, 19.9, 20.0, 50, 50, 50, 50, 50, 5, 0]  # first sample >= 20 N is index 12
    f[40:45] = [10, 25, 30, 30, 0]                         # index 41
    idx = seg.rising_crossings(f)
    assert idx.tolist() == [12, 41]
    t = np.arange(100) * DT
    assert [round(t[i], 6) for i in idx] == [0.06, 0.205]


def test_nan_never_counts_as_a_crossing():
    f = np.zeros(20)
    f[5] = np.nan
    f[6:10] = 100.0  # 5 is NaN, so the step into index 6 is not a crossing
    assert seg.rising_crossings(f).tolist() == []


def test_gait_segments_every_interval_has_status_and_reason():
    n = 2000
    t = np.arange(n) * DT
    # rises at 0.5, 1.5, 2.0 (short 0.5 s ok), 2.2 (0.2 s: too short), 9.0 (long gap 6.8 s), 9.8 (final contact)
    rises = [int(x / DT) for x in (0.5, 1.5, 2.0, 2.2, 9.0)]
    f = trace(n, rises, 20)
    f[int(2.3 / DT):int(2.3 / DT) + 5] = 100.0  # no effect on crossings
    segs = seg.gait_segments(t, f, 'L')
    got = [(round(s['start_s'], 3), s['status'], s['reason']) for s in segs]
    assert got[0] == (0.5, 'accepted', None) and segs[0]['end_s'] == pytest.approx(1.5)
    assert got[1] == (1.5, 'accepted', None) and segs[1]['duration_s'] == pytest.approx(0.5)
    assert got[2] == (2.0, 'excluded', 'shorter_than_0.3_s')
    assert got[3][1:] == ('excluded', 'longer_than_5_s') and got[3][0] == 2.2
    assert got[4] == (9.0, 'excluded', 'last_contact_has_no_following_contact')
    assert len(segs) == 5  # nothing dropped


def test_gait_segment_with_missing_force_is_listed_not_dropped():
    n = 1000
    t = np.arange(n) * DT
    f = trace(n, [100, 300], 40)
    f[200] = np.nan
    segs = seg.gait_segments(t, f, 'R')
    assert segs[0]['status'] == 'excluded' and segs[0]['reason'] == 'force_not_a_number_inside_stride'


def test_missing_plate_gives_zero_segments_not_invented_ones():
    f = np.full(500, np.nan)
    assert seg.gait_segments(np.arange(500) * DT, f, 'R') == []
    assert seg.plate_state(f) == 'plate_missing_all_samples_not_a_number'
    assert seg.plate_state(np.zeros(10)) == 'plate_never_reaches_threshold'


def test_marker_speed_of_known_constant_velocity():
    n = 400
    t = np.arange(n) * DT
    pos = np.zeros((n, 4, 3))
    pos[:, :, 0] = (1000.0 * 0.8 * t)[:, None]  # 0.8 m/s along x, in mm
    s = seg.marker_speed(t, pos)
    assert np.allclose(s[5:-5], 0.8)
    assert np.isnan(s[:5]).all() and np.isnan(s[-5:]).all()
    pos[100, 2, 1] = np.nan  # one missing marker sample: speed is missing around it, never filled
    s2 = seg.marker_speed(t, pos)
    assert np.isnan(s2[95]) and np.isnan(s2[105]) and np.isfinite(s2[94]) and np.isfinite(s2[106])


def test_window_segments_known_spans_and_reasons():
    n = 1200
    t = np.arange(n) * DT
    s = np.zeros(n)
    s[100:300] = 1.0   # span 1: samples 100..299
    s[340:500] = 1.0   # 40 samples (0.2 s) after span 1: bridged, one window 100..499
    s[600:610] = 1.0   # 10 samples (0.05 s): shorter than the debounce time
    s[800:900] = 0.4   # below threshold: nothing
    s[1000:1100] = 0.7
    segs = seg.window_segments(t, s)
    spans = [(x['start_index'], x['end_index'], x['status'], x['reason']) for x in segs]
    assert spans == [(100, 499, 'accepted', None), (600, 609, 'excluded', 'shorter_than_0.25_s'),
                     (1000, 1099, 'accepted', None)]
    assert segs[0]['start_s'] == pytest.approx(0.5)


def test_window_span_open_at_edge_and_next_to_missing_marker_are_excluded():
    n = 300
    t = np.arange(n) * DT
    s = np.zeros(n)
    s[:50] = 1.0
    s[100:160] = 1.0
    s[99] = np.nan
    segs = seg.window_segments(t, s)
    assert [x['reason'] for x in segs] == ['span_open_at_recording_edge', 'span_boundary_next_to_missing_marker']


def test_match_authors_offsets_and_reasons():
    ours = [{'side': 'L', 'start_s': 1.0, 'end_s': 2.0, 'status': 'accepted', 'reason': None},
            {'side': 'L', 'start_s': 2.0, 'end_s': None, 'status': 'excluded', 'reason': 'last_contact_has_no_following_contact'},
            {'side': 'L', 'start_s': 5.2, 'end_s': 6.2, 'status': 'accepted', 'reason': None}]
    authors = [{'side': 'L', 'start': 1.0, 'end': 2.005},   # exact start, end 5 ms earlier than authors
               {'side': 'L', 'start': 2.01, 'end': 3.0},    # nearest is the excluded record
               {'side': 'L', 'start': 5.0, 'end': 6.0},     # 200 ms away: beyond a 50 ms tolerance
               {'side': 'R', 'start': 1.0, 'end': 2.0}]     # no right-leg record at all
    res = seg.match_authors(ours, authors, 50.0)
    assert res[0]['status'] == 'matched' and res[0]['start_offset_ms'] == pytest.approx(0.0)
    assert res[0]['end_offset_ms'] == pytest.approx(-5.0)
    assert res[1]['status'] == 'missed' and res[1]['reason'].startswith('nearest_record_excluded')
    assert res[2]['status'] == 'missed' and res[2]['reason'] == 'no_record_starts_within_tolerance'
    assert res[2]['nearest_start_offset_ms'] == pytest.approx(200.0)
    assert res[3]['status'] == 'missed' and res[3]['reason'] == 'no_record_for_this_leg'


def test_tasks_partition_and_unknown_task_stops():
    all_tasks = seg.GAIT_TASKS + seg.WINDOW_PELVIS_TASKS + seg.WINDOW_TRUNK_TASKS + seg.CONTINUOUS_TASKS
    assert len(all_tasks) == 26 and len(set(all_tasks)) == 26
    assert seg.task_of('stairs_1_10') == 'stairs' and seg.task_of('step_ups') == 'step_ups'
    assert seg.task_of('normal_walk_1') == 'normal_walk' and seg.task_class('lift_weight') == 'window_trunk'
    with pytest.raises(seg.UnknownTask):
        seg.task_of('hopscotch_1')
    with pytest.raises(seg.UnknownTask):
        seg.task_of('walk_1')


# ---- end to end on a tiny synthetic participant -------------------------------------------------------------

def write_source(root):
    raw = root / 'RawData' / 'AB01'
    n = 3000
    t = np.arange(n) * DT
    left = trace(n, [200, 400, 600, 800], 120)
    right = np.full(n, np.nan)
    for rec, force in (('normal_walk_1', left), ('poses_1', np.zeros(n))):
        d = raw / 'CSV_Data' / rec
        d.mkdir(parents=True)
        lines = ['time,RForceY_Vertical,LForceY_Vertical'] + [
            f'{float(t[i])!r},NaN,{float(force[i])!r}' for i in range(n)]
        (d / 'GroundFrame_GRFs.csv').write_text('\n'.join(lines) + '\n')
    # squats_1 window rule: pelvis moving at 1 m/s from 1.0 s to 2.0 s
    d = raw / 'CSV_Data' / 'squats_1'
    d.mkdir(parents=True)
    lines = ['time,RForceY_Vertical,LForceY_Vertical'] + [f'{float(t[i])!r},0.0,0.0' for i in range(n)]
    (d / 'GroundFrame_GRFs.csv').write_text('\n'.join(lines) + '\n')
    names = ['C7', 'LASI', 'RASI', 'LPSI', 'RPSI']
    head = ['PathFileType\t4\t(X/Y/Z)\tx.trc', 'DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits',
            f'200\t200\t{n}\t{len(names)}\tmm', 'Frame#\tTime\t' + '\t'.join(m + '\t\t' for m in names),
            '\t\t' + '\t'.join(f'X{i}\tY{i}\tZ{i}' for i in range(len(names))), '']
    x = np.where(t < 1.0, 0.0, np.where(t < 2.0, (t - 1.0) * 1000.0, 1000.0))
    rows = [f'{i + 1}\t{float(t[i])!r}\t' + '\t'.join(f'{float(x[i] + 10 * k)!r}\t0.0\t0.0' for k in range(len(names))) for i in range(n)]
    (raw / 'MarkerData').mkdir()
    (raw / 'MarkerData' / 'squats_1.trc').write_text('\n'.join(head + rows) + '\n')
    seg_dir = root / 'Segmentation' / 'AB01'
    seg_dir.mkdir(parents=True)
    # authors: left strides at 1.0-2.0 and 2.0-3.0 s (exact), plus one right-leg window the missing plate cannot give
    sio.savemat(seg_dir / 'normal_walk_1_1-2_parsing.mat', {'left': np.array([[1.0, 2.0], [2.0, 3.0]]),
                                                            'right': np.array([[1.0, 2.0]])})
    sio.savemat(seg_dir / 'squats_1_0lbs_parsing.mat', {'left': np.array([[1.0, 2.0]]), 'right': np.array([[1.0, 2.0]])})
    files = []
    for f, rec, left_n, right_n in (('normal_walk_1_1-2_parsing.mat', 'normal_walk_1', 2, 1), ('squats_1_0lbs_parsing.mat', 'squats_1', 1, 1)):
        files.append({'file': f, 'recording': rec, 'sha256': runner.rd.sha256_file(seg_dir / f), 'windows_left': left_n,
                      'windows_right': right_n})
    return {'files': files, 'unassigned_files': [], 'recordings_with_windows': ['normal_walk_1', 'squats_1'],
            'recordings_in_source': 3, 'subject': 'AB01'}


def test_end_to_end_synthetic_participant(tmp_path, monkeypatch):
    src = tmp_path / 'src'
    events = write_source(src)
    ev_root = tmp_path / 'events'
    ev_root.mkdir()
    (ev_root / 'events_AB01.json').write_text(json.dumps(events))
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'BASE', tmp_path / 'out')
    out = tmp_path / 'out' / 'AB01'
    args = runner.argparse.Namespace(output_root=out, subject='AB01', records=None, events_root='events', x01_root=None, source=src)
    assert runner.run(args) == 0
    ledger = {e['recording']: e for e in map(json.loads, (out / 'ledger.jsonl').read_text().splitlines())}
    assert ledger['poses_1']['disposition'] == 'continuous_recording'
    assert ledger['normal_walk_1']['plates'] == {'L': 'plate_present', 'R': 'plate_missing_all_samples_not_a_number'}
    assert ledger['normal_walk_1']['segments']['accepted_R'] == 0  # no right strides are invented
    wins = [json.loads(x) for x in (out / 'authors_windows.jsonl').read_text().splitlines()]
    assert len(wins) == 5  # every authors' window has a result line
    nw = [w for w in wins if w['recording'] == 'normal_walk_1']
    lefts = [w for w in nw if w['side'] == 'L']
    assert [w['status'] for w in lefts] == ['matched', 'matched'] and [w['start_offset_ms'] for w in lefts] == [0.0, 0.0]
    right = [w for w in nw if w['side'] == 'R'][0]
    assert right['status'] == 'missed' and 'plate_missing' in right['reason']
    sq = [w for w in wins if w['recording'] == 'squats_1']
    assert all(w['status'] == 'matched' for w in sq)
    assert all(abs(w['start_offset_ms']) <= 60 for w in sq)  # half the 50 ms speed window; a known smoothing lag
    segs = [json.loads(x) for x in (out / 'segments.jsonl').read_text().splitlines()]
    # strides before and after the authors' windows stay with an unknown label; the matched ones carry the file
    assert {s['disposition'] for s in segs if s['recording'] == 'normal_walk_1'} >= {'accepted_matches_authors_window',
                                                                                    'accepted_not_in_authors_windows'}
    assert all(s['authors_file'] is None for s in segs if s['disposition'] == 'accepted_not_in_authors_windows')
