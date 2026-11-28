"""GT23-S01 segmentation with our own rules, checked against the authors' labelled strides.

Subcommands
  run      One participant (or named recordings): reads one recording at a time from the publisher's folders
           (read-only), writes a NEW output root with ledger.jsonl (one line per recording), segments.jsonl (one line per
           stride, window or excluded interval), authors_windows.jsonl (one line per authors' window with its
           match result) and run_summary.json. Never overwrites; no data arrays are written.
  spec     Writes the guarded-launcher job spec.
  summary  Adds up participant roots: counts, the 90 dispositions, agreement per task and per leg (offsets in ms),
           and a count comparison with the energy-shaping-ML phase reconstruction audit CSV (read as text, no import).

Event windows are read through the X01 events root (file list, recording assignment, sha256); the window times come
from the authors' small stride files, whose hashes must equal the events root. Python only; no scientific approval.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from contributor_tools import gt23_segmentation as seg  # noqa: E402
from contributor_tools import gt23_source_reader as rd  # noqa: E402

SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
BASE = ROOT / 'converted_datasets/reconversion_v2'
EVENTS_ROOT = 'converted_datasets/reconversion_v2/gt23_x01_events'
SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
X01_ROOTS = {s: f'converted_datasets/reconversion_v2/gt23_x01_batch_{s}' + ('_r2' if s == 'AB01' else '') for s in SUBJECTS}
ESML_CSV = Path('/mnt/s/workspace_docs/energy shaping ml/esml_research/code/hardware_analysis/'
                'dataset_late_stance_audit_20260723/gtech_2023_phase_reconstruction_audit.csv')
CODE = ('contributor_tools/gt23_segmentation.py', 'contributor_tools/run_gt23_s01.py',
        'contributor_tools/gt23_source_reader.py', 'contributor_tools/guarded_launcher.py')
EXPECTED = {'recordings': 488, 'authors_windows': 13119, 'authors_windows_left': 7721, 'authors_windows_right': 5398,
            'recordings_without_windows': 90, 'without_windows_gait': 23, 'without_windows_window': 3,
            'without_windows_continuous': 64}
CLOCK_TOL_S = 1e-5
CHUNK = 20000


class RunError(RuntimeError):
    pass


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def _atomic_json(path, obj):
    temp = Path(path).with_suffix('.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    temp.replace(path)


def read_force(path):
    """Time and both plates' vertical force of one recording, read in chunks (a 1 MB file)."""
    cols = ['time', rd.PLATE_VERTICAL['L'], rd.PLATE_VERTICAL['R']]
    parts = [c for c in pd.read_csv(path, usecols=cols, dtype=np.float64, float_precision='round_trip', chunksize=rd.CHUNK_ROWS)]
    df = pd.concat(parts, ignore_index=True)
    return df['time'].to_numpy(), {'L': df[cols[1]].to_numpy(), 'R': df[cols[2]].to_numpy()}


def read_markers(path, names):
    """Time and positions (n, markers, 3) in mm of the named markers, read in chunks. Missing names fail closed."""
    first, markers, declared = rd.read_trc_header(path)
    missing = [m for m in names if m not in markers]
    if missing:
        raise RunError(f'markers missing from the file: {missing}')
    use, idx = [1], []
    for m in names:
        i = markers.index(m)
        idx.append(2 + 3 * i)
        use += [2 + 3 * i, 3 + 3 * i, 4 + 3 * i]
    order = sorted(set(use))
    pos = {c: k for k, c in enumerate(order)}
    ts, ps = [], []
    for chunk in pd.read_csv(path, sep='\t', skiprows=first, header=None, usecols=order, dtype=np.float64, chunksize=CHUNK):
        arr = chunk.to_numpy(np.float64)
        ts.append(arr[:, pos[1]])
        ps.append(np.stack([arr[:, [pos[c], pos[c + 1], pos[c + 2]]] for c in idx], axis=1))
    return np.concatenate(ts), np.concatenate(ps, axis=0), declared


def check_clock(t, name):
    d = np.abs(np.diff(t) - 1.0 / seg.RATE_HZ)
    if len(t) > 1 and (not np.isfinite(d).all() or d.max() > CLOCK_TOL_S):
        raise RunError(f'{name}: clock is not 200 Hz (max step deviation {np.nanmax(d):.3g} s)')


def authors_windows(subject, events_part, source):
    """Every authors' window of one participant, from the stride files named (and hashed) by the events root."""
    import scipy.io as sio
    out = []
    for item in events_part['files']:
        path = Path(source) / 'Segmentation' / subject / item['file']
        if rd.sha256_file(path) != item['sha256']:
            raise RunError(f'{path.name}: hash differs from the events root')
        mat = sio.loadmat(str(path), simplify_cells=True)
        n = 0
        for key in sorted(k for k in mat if not k.startswith('__') and k != 'types'):
            side = key.split('_')[0]
            arr = np.asarray(mat[key], float)
            if not arr.size:
                continue
            arr = np.atleast_2d(arr)
            if arr.ndim != 2 or arr.shape[1] != 2 or side not in ('left', 'right'):
                raise RunError(f'{path.name}: key {key} is not an n-by-2 left/right matrix')
            for row, (a, b) in enumerate(arr):
                out.append({'subject': subject, 'recording': item['recording'], 'file': item['file'], 'key': key,
                            'side': 'L' if side == 'left' else 'R', 'type': key[len(side) + 1:], 'row': row,
                            'start': float(a), 'end': float(b)})
                n += 1
        if n != item['windows_left'] + item['windows_right']:
            raise RunError(f'{path.name}: {n} windows read, events root says {item["windows_left"] + item["windows_right"]}')
    return out


def segment_recording(subj, rec, x01, windows, source):
    """Segments, authors' match results and the ledger entry for one recording."""
    task = seg.task_of(rec)
    klass = seg.task_class(task)
    entry = {'subject': subj.subject, 'recording': rec, 'task': task, 'task_class': klass, 'rule': seg.RULES[klass],
             'authors_windows': len(windows), 'issues': []}
    folder = subj.raw / 'CSV_Data' / rec
    grf = folder / 'GroundFrame_GRFs.csv'
    grf_sha = rd.sha256_file(grf)
    if x01 is not None and x01['channels']['GroundFrame_GRFs']['sha256'] != grf_sha:
        raise RunError('GroundFrame_GRFs.csv hash differs from the X01 ledger')
    entry['grf_sha256'] = grf_sha
    segments, results = [], []
    if klass == 'continuous':
        if windows:
            raise RunError(f'{rec}: authors have windows for a task with no cycle rule')
        t, _ = read_force(grf)
        check_clock(t, 'GroundFrame_GRFs')
        entry.update(disposition='continuous_recording', rows=int(len(t)), duration_s=float(t[-1] - t[0]),
                     reason='no defensible cycle: README lists the task as not segmented or free-form')
        return entry, segments, results
    if klass == 'gait':
        t, force = read_force(grf)
        check_clock(t, 'GroundFrame_GRFs')
        entry['rows'] = int(len(t))
        entry['plates'] = {s: seg.plate_state(force[s]) for s in 'LR'}
        for s in 'LR':
            for rec_ in seg.gait_segments(t, force[s], s):
                segments.append(rec_)
        entry['disposition'] = 'gait_strides'
        kind = 'gait'
    else:
        names = seg.TRUNK_MARKERS if klass == 'window_trunk' else seg.PELVIS_MARKERS
        trc = subj.raw / 'MarkerData' / f'{rec}.trc'
        trc_sha = rd.sha256_file(trc)
        if x01 is not None and x01['markers']['sha256'] != trc_sha:
            raise RunError('marker file hash differs from the X01 ledger')
        t, pos, declared = read_markers(trc, names)
        check_clock(t, 'marker file')
        entry.update(rows=int(len(t)), markers=list(names), marker_sha256=trc_sha, disposition='window_segments')
        speed = seg.marker_speed(t, pos)
        entry['speed_finite_share'] = round(float(np.isfinite(speed).mean()), 6)
        segments = seg.window_segments(t, speed)
        kind = 'window'
    for n, s in enumerate(segments):
        s['segment_id'] = f'{subj.subject}/{rec}/{s["side"]}/{s["start_index"]:07d}'
        s['authors_match'] = []
    tol = seg.MATCH_TOLERANCE_MS[kind]
    entry['match_tolerance_ms'] = tol
    res = seg.match_authors(segments, windows, tol, same_side=(kind == 'gait'))
    for w, r in zip(windows, res):
        r = dict(r)
        if r['status'] == 'missed' and kind == 'gait' and r['reason'] == 'no_record_for_this_leg':
            r['reason'] = f'no_contact_on_{w["side"]}_plate: {entry["plates"][w["side"]]}'
        if r['segment_index'] is not None and r['status'] == 'matched':
            segments[r['segment_index']]['authors_match'].append(f'{w["file"]}:{w["key"]}:{w["row"]}')
        results.append({**w, **r})
    for s in segments:
        matched = bool(s['authors_match'])
        s['label_source'] = 'authors_window' if matched else 'unknown'
        s['authors_file'] = sorted({m.split(':')[0] for m in s['authors_match']})[0] if matched else None
        if s['status'] == 'excluded':
            s['disposition'] = 'excluded'
        elif matched:
            s['disposition'] = 'accepted_matches_authors_window'
        elif windows:
            s['disposition'] = 'accepted_not_in_authors_windows'
        else:
            s['disposition'] = 'accepted_recording_has_no_authors_windows'
    entry['segments'] = {'accepted': sum(s['status'] == 'accepted' for s in segments),
                         'excluded': sum(s['status'] == 'excluded' for s in segments)}
    for s in 'LR' if kind == 'gait' else ():
        entry['segments'][f'accepted_{s}'] = sum(x['status'] == 'accepted' for x in segments if x['side'] == s)
    return entry, segments, results


def run(args):
    out = Path(args.output_root).resolve()
    source = Path(args.source).resolve()
    if not out.is_relative_to(BASE) or out == source or source in out.parents:
        raise RunError('a new output root under converted_datasets/reconversion_v2 (never the source) is required')
    if args.subject not in SUBJECTS:
        raise RunError(f'unknown participant {args.subject}')
    wanted = None
    if args.records:
        wanted = []
        for item in args.records:
            subject, rec = item.split('/')
            if subject != args.subject:
                raise RunError(f'record {item} is not for {args.subject}')
            wanted.append(rec)
    out.mkdir(parents=True, exist_ok=False)
    summary = {'status': 'running', 'scientific_approval': False, 'subject': args.subject, 'pilot_records': wanted,
               'recordings_done': 0,
               'parameters': {'stance_n': seg.STANCE_N, 'gait_min_s': seg.GAIT_MIN_S, 'gait_max_s': seg.GAIT_MAX_S,
                              'speed_threshold_m_s': seg.SPEED_THRESHOLD_M_S, 'debounce_s': seg.DEBOUNCE_S,
                              'speed_half_span_samples': seg.SPEED_HALF_SPAN_SAMPLES,
                              'match_tolerance_ms': seg.MATCH_TOLERANCE_MS}}
    target = out / 'run_summary.json'
    _atomic_json(target, summary)
    try:
        subj = rd.Subject(source, args.subject)
        recs = subj.recordings()
        events_part = json.loads((ROOT / args.events_root / f'events_{args.subject}.json').read_text())
        if events_part['unassigned_files']:
            raise RunError(f'unassigned event files: {events_part["unassigned_files"]}')
        wins = authors_windows(args.subject, events_part, source)
        by_rec = {}
        for w in wins:
            by_rec.setdefault(w['recording'], []).append(w)
        if not set(by_rec) <= set(recs):
            raise RunError(f'authors windows for recordings not in the source: {sorted(set(by_rec) - set(recs))}')
        x01 = {}
        if args.x01_root:
            for line in (ROOT / args.x01_root / 'ledger.jsonl').read_text().splitlines():
                e = json.loads(line)
                x01[e['recording']] = e
        if wanted is not None:
            missing = [r for r in wanted if r not in recs]
            if missing:
                raise RunError(f'named recordings not in the source: {missing}')
            recs = wanted
        n_win_done, failed = 0, 0
        with (out / 'ledger.jsonl').open('x') as ledger, (out / 'segments.jsonl').open('x') as segf, \
                (out / 'authors_windows.jsonl').open('x') as winf:
            for rec in recs:
                try:
                    entry, segments, results = segment_recording(subj, rec, x01.get(rec) if args.x01_root else None,
                                                                 by_rec.get(rec, []), source)
                    entry['status'] = 'ok'
                    for i, s in enumerate(segments):
                        segf.write(rd.dumps({'subject': args.subject, 'recording': rec, 'task': entry['task'],
                                             'rule': entry['rule'], 'index': i, **s}) + '\n')
                    for r in results:
                        winf.write(rd.dumps({**r, 'task': entry['task'], 'rule': entry['rule']}) + '\n')
                    n_win_done += len(results)
                except Exception as error:  # a recording that cannot be segmented is named; unknown task stops the job
                    if isinstance(error, seg.UnknownTask):
                        raise
                    entry = {'subject': args.subject, 'recording': rec, 'status': 'failed',
                             'issues': [f'{type(error).__name__}: {error}']}
                    failed += 1
                ledger.write(rd.dumps(entry) + '\n')
                for f in (ledger, segf, winf):
                    f.flush()
                summary['recordings_done'] += 1
                summary['peak_rss_mib'] = peak_rss_mib()
                _atomic_json(target, summary)
        summary['recordings_failed'] = failed
        summary['authors_windows_total'] = len(wins)
        summary['authors_windows_accounted'] = n_win_done
        full = wanted is None
        if full and not failed and n_win_done != len(wins):
            raise RunError(f'{len(wins) - n_win_done} authors windows not accounted for')
        summary['status'] = 'participant_done_unreviewed' if not failed else 'recordings_failed'
    except BaseException as error:
        summary.update(status='runner_error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        summary['peak_rss_mib'] = peak_rss_mib()
        _atomic_json(target, summary)
    return 0 if summary['status'] == 'participant_done_unreviewed' else 1


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/run_gt23_s01.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    if args.kind == 'run':
        command += ['--subject', args.subject, '--events-root', EVENTS_ROOT, '--x01-root', X01_ROOTS[args.subject]]
        for r in args.records or []:
            command += ['--records', r]
        command += ['--source', str(SOURCE)]
        bindings[f'{EVENTS_ROOT}/events_{args.subject}.json'] = rd.sha256_file(ROOT / EVENTS_ROOT / f'events_{args.subject}.json')
        bindings[f'{X01_ROOTS[args.subject]}/ledger.jsonl'] = rd.sha256_file(ROOT / X01_ROOTS[args.subject] / 'ledger.jsonl')
        names = ['run_summary.json']
    else:
        command += ['--roots'] + list(args.roots)
        for r in args.roots:
            bindings[f'{r}/run_summary.json'] = rd.sha256_file(ROOT / r / 'run_summary.json')
        names = ['summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names,
            'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def _stats(values):
    v = np.asarray(values, float)
    if not v.size:
        return None
    a = np.abs(v)
    return {'n': int(v.size), 'median_ms': round(float(np.median(v)), 3), 'median_abs_ms': round(float(np.median(a)), 3),
            'p95_abs_ms': round(float(np.percentile(a, 95)), 3), 'max_abs_ms': round(float(a.max()), 3),
            'within_10_ms': int((a <= 10).sum()), 'within_50_ms': int((a <= 50).sum())}


def summarize(args):
    rows_by_sub, led, wins, segs = {}, [], [], []
    for root in args.roots:
        p = Path(ROOT / root)
        led += [json.loads(x) for x in (p / 'ledger.jsonl').read_text().splitlines()]
        wins += [json.loads(x) for x in (p / 'authors_windows.jsonl').read_text().splitlines()]
        segs += [json.loads(x) for x in (p / 'segments.jsonl').read_text().splitlines()]
        rows_by_sub[root] = json.loads((p / 'run_summary.json').read_text())
    problems = []
    for root, s in rows_by_sub.items():
        if s['status'] != 'participant_done_unreviewed':
            problems.append(f'{root}: status {s["status"]}')
    keys = {(e['subject'], e['recording']) for e in led}
    if len(keys) != len(led):
        problems.append('duplicate recordings')
    nowin = [e for e in led if e.get('authors_windows') == 0]
    dispo = {}
    for e in nowin:
        k = {'gait_strides': 'gait', 'window_segments': 'window', 'continuous_recording': 'continuous'}.get(e.get('disposition'))
        dispo[k] = dispo.get(k, 0) + 1
    counts = {'recordings': len(led), 'authors_windows': len(wins),
              'authors_windows_left': sum(w['side'] == 'L' for w in wins),
              'authors_windows_right': sum(w['side'] == 'R' for w in wins),
              'recordings_without_windows': len(nowin), 'without_windows_gait': dispo.get('gait', 0),
              'without_windows_window': dispo.get('window', 0), 'without_windows_continuous': dispo.get('continuous', 0)}
    checks = {k: {'got': counts[k], 'expected': v, 'equal': counts[k] == v} for k, v in EXPECTED.items()}
    if any(e['status'] != 'ok' for e in led):
        problems.append('recordings failed: ' + ', '.join(f"{e['subject']}/{e['recording']}" for e in led if e['status'] != 'ok'))
    # agreement per task and leg
    agree = {}
    for w in wins:
        key = (w['task'], w['side'])
        a = agree.setdefault(key, {'authors': 0, 'matched': 0, 'missed': 0, 'start': [], 'end': [], 'reasons': {}})
        a['authors'] += 1
        if w['status'] == 'matched':
            a['matched'] += 1
            a['start'].append(w['start_offset_ms'])
            if w['end_offset_ms'] is not None:
                a['end'].append(w['end_offset_ms'])
        else:
            a['missed'] += 1
            r = (w['reason'] or '').split(':')[0]
            a['reasons'][r] = a['reasons'].get(r, 0) + 1
    extra = {}
    for s in segs:
        if s['status'] != 'accepted':
            continue
        for side in (s['side'],):
            e = extra.setdefault((s['task'], side), {'accepted': 0, 'matched': 0, 'extra_in_recordings_with_windows': 0,
                                                      'extra_in_recordings_without_windows': 0})
            e['accepted'] += 1
            if s['disposition'] == 'accepted_matches_authors_window':
                e['matched'] += 1
            elif s['disposition'] == 'accepted_not_in_authors_windows':
                e['extra_in_recordings_with_windows'] += 1
            else:
                e['extra_in_recordings_without_windows'] += 1
    excl = {}
    for s in segs:
        if s['status'] == 'excluded':
            k = f'{s["task"]}|{s["reason"]}'
            excl[k] = excl.get(k, 0) + 1
    table = []
    for task, side in sorted(set(agree) | set(extra)):
        a = agree.get((task, side), {'authors': 0, 'matched': 0, 'missed': 0, 'start': [], 'end': [], 'reasons': {}})
        table.append({'task': task, 'side': side, 'authors_windows': a['authors'], 'matched': a['matched'], 'missed': a['missed'],
                      'missed_reasons': a['reasons'], 'start_offset': _stats(a['start']), 'end_offset': _stats(a['end']),
                      'our_accepted': extra.get((task, side), {})})
    # authors' windows where the leg's plate was missing are reported through the reasons above
    plates = {}
    for e in led:
        if e.get('plates'):
            for s, st in e['plates'].items():
                plates[f'{e["task"]}|{s}|{st}'] = plates.get(f'{e["task"]}|{s}|{st}', 0) + 1
    report = {'schema': 'locohub.gt23_s01_summary/1', 'scientific_approval': False, 'roots': list(args.roots),
              'offset_sign': 'ours minus the authors (ms); positive means our time is later',
              'counts': counts, 'acceptance_counts': checks, 'all_counts_equal': all(c['equal'] for c in checks.values()),
              'problems': problems, 'agreement_by_task_and_leg': table, 'excluded_intervals_by_task_and_reason': excl,
              'plate_states_by_task_leg': plates,
              'peak_rss_mib_by_root': {r: s.get('peak_rss_mib') for r, s in rows_by_sub.items()},
              'window_start_tolerance_ms': seg.MATCH_TOLERANCE_MS,
              'no_window_recordings': [{'recording': f"{e['subject']}/{e['recording']}", 'task': e['task'],
                                         'disposition': e['disposition'], 'rule': e['rule'],
                                         'segments': e.get('segments')} for e in nowin]}
    report['esml_count_comparison'] = esml_comparison(led, segs, wins) if ESML_CSV.is_file() else 'comparison file not found'
    (ROOT / args.output_root).mkdir(parents=True, exist_ok=False)
    with (ROOT / args.output_root / 'summary.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    return 0 if report['all_counts_equal'] and not problems else 1


def esml_comparison(led, segs, wins):
    """Compare strides per participant and walking condition with the other project's heel-strike audit (text only)."""
    rows = list(csv.DictReader(ESML_CSV.open()))
    ours = {}
    spans = {}
    for w in wins:
        if w['task'] in ('normal_walk', 'incline_walk') and w['side'] == 'L':
            k = (w['subject'], w['recording'], w['file'])
            lo, hi = spans.get(k, (np.inf, -np.inf))
            spans[k] = (min(lo, w['start']), max(hi, w['end']))
    for s in segs:
        if s['status'] != 'accepted' or s['side'] != 'L' or s['task'] not in ('normal_walk', 'incline_walk'):
            continue
        for (sub, rec, f), (lo, hi) in spans.items():
            if sub == s['subject'] and rec == s['recording'] and lo <= s['start_s'] <= hi:
                ours[(sub, f)] = ours.get((sub, f), 0) + 1
    out = []
    for r in rows:
        out.append({'subject': r['subject'], 'task_id': r['task_id'], 'task_info': r['task_info'],
                    'esml_detected_heel_strikes': r['detected_heel_strikes'], 'esml_accepted_cycles': r['accepted_cycles']})
    mapped = {}
    for r in out:
        sub = r['subject'].replace('GT23_', '')
        info = r['task_info']
        suffix = None
        for tag, name in (('decline_5deg', 'down5'), ('incline_5deg', 'up5'), ('decline_10deg', 'down10'), ('incline_10deg', 'up10')):
            if r['task_id'] == tag:
                suffix = name
        if suffix is None and 'speed' in info:
            v = info.split('speed')[1]
            val = ''.join(ch for ch in v if ch.isdigit() or ch == '.')
            suffix = val.replace('.', '-')
        r['our_condition_suffix'] = suffix
        n = None
        if suffix:
            n = sum(c for (s2, f), c in ours.items() if s2 == sub and f.endswith(f'_{suffix}_parsing.mat'))
        r['our_left_strides_inside_authors_span'] = n
        mapped[r['task_id']] = mapped.get(r['task_id'], 0) + 1
    return {'source': str(ESML_CSV), 'note': 'The other project used a 0.05 BW five-sample moving-average rule and 0.35-2.0 s spacing; counts are a comparison, not a check.',
            'rows': out}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--output-root', type=Path, required=True)
    r.add_argument('--subject', required=True)
    r.add_argument('--records', action='append')
    r.add_argument('--events-root', default=EVENTS_ROOT)
    r.add_argument('--x01-root')
    r.add_argument('--source', type=Path, default=SOURCE)
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('run', 'summary'), default='run')
    s.add_argument('--job-id', required=True)
    s.add_argument('--subject')
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--records', action='append')
    s.add_argument('--roots', nargs='*')
    t = sub.add_parser('summary')
    t.add_argument('--output-root', required=True)
    t.add_argument('--roots', nargs='+', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec, 'summary': summarize}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
