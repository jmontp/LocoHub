"""GT21-RB03 runner: segmentation of every source step of both legs, the stance force mask, and the comparison with the
authors' right-leg cutting. Method and rules: contributor_tools/gt21_rb_segment.py.

Reads, one recording at a time: the two source gait tables (gcLeft, gcRight; small), the RB01 label rows of the
participant, and the merged-pass continuous Parquet of the recording (five columns only). Writes into a NEW output root:

  steps.jsonl              one line per source step of each leg: one disposition, label, terrain value, force check, mask counts
  authors_intervals.jsonl  one line per authors' right-leg interval with its match to our right-leg steps and, for ramp
                           and stair, the authors' own class beside our disposition
  ledger.jsonl             one line per recording: one disposition and counts
  force_mask/<ID>/<mode>/<recording>.parquet   derived layer: time_s, force_missing_left, force_missing_right (bool)
  run_summary.json

Never overwrites (exclusive create). No source file is written. Only through
``python3 -m contributor_tools.guarded_launcher run SPEC.json``. No scientific approval is claimed.

Subcommands: run, spec.
"""
import argparse
import gc as pygc
from collections import Counter
import json
import os
from pathlib import Path
import random
import resource
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt21_numeric_source as src  # noqa: E402
from contributor_tools import gt21_rb_segment as sg  # noqa: E402
from contributor_tools.run_gt21_rb_pass import (INVENTORY, LABELS, ROOTS, _json_default, load_inventory,  # noqa: E402
                                                peak_rss_mib, sha256_file)

pa.set_cpu_count(1)             # a 768 MiB address-space cap cannot hold extra worker threads (AB06 batch r1 aborted)
pa.set_io_thread_count(1)
LABELS_RB03 = 'converted_datasets/reconversion_v2/gt21_rb03_authors_fields_20261125'   # RB01 label export plus the RB03 additions
PASS_ROOT = 'converted_datasets/reconversion_v2/gt21_rb_pass_batch_{subject}_20261124'
CODE = ('contributor_tools/gt21_rb_segment.py', 'contributor_tools/run_gt21_rb_segment.py',
        'contributor_tools/gt21_numeric_source.py', 'contributor_tools/gt21_rb_pass.py', 'contributor_tools/run_gt21_rb_pass.py')
TABLE_COLUMNS = ('time_s', 'stance_left', 'stance_right', 'grf_vertical_left_BW', 'grf_vertical_right_BW')
LEGS = ('left', 'right')
MATCH_S = 0.0051          # one 200 Hz sample: authors' interval start and our step start are the same reset or not


def load_labels(subject, labels_root=None):
    rows = {}
    path = Path(labels_root or ROOT / LABELS_RB03) / subject / f'labels_{subject}.jsonl'
    for line in path.read_text().splitlines():
        r = json.loads(line)
        rows[(r['mode'], r['recording'])] = r
    return rows


def load_pass_ledger(subject, pass_root=None):
    root = Path(pass_root or ROOT / PASS_ROOT.format(subject=subject))
    rows = {}
    for line in (root / 'ledger.jsonl').read_text().splitlines():
        r = json.loads(line)
        rows[(r['mode'], r['recording'])] = r
    return root, rows


def read_pass_table(root, entry):
    """Five columns of one continuous table, or None when the pass did not convert the recording."""
    if not entry or entry.get('status') != 'converted':
        return None
    t = pq.read_table(root / entry['parquet'], columns=list(TABLE_COLUMNS), use_threads=False)
    return {c: t.column(c).to_numpy(zero_copy_only=False) for c in TABLE_COLUMNS}


def segment_recording(row, meta, gc, table, bw_n, mask_dir, steps_f, auth_f, out_root=None):
    """Segment one recording. ``gc``: {'left': table dict, 'right': table dict} (Header, HeelStrike, ToeOff)."""
    subject, mode, rec = row['subject'], row['mode'], row['recording']
    entry = {'subject': subject, 'session': row['session'], 'mode': mode, 'recording': rec, 'source': row['source'],
             'resets': {}, 'steps_by_disposition': {}, 'steps_by_reason': {}, 'table_available': table is not None}
    span = (float(table['time_s'][0]), float(table['time_s'][-1])) if table is not None else None
    masks, mask_stats, vertical_n = {}, {}, {}
    if table is not None:
        for leg in LEGS:
            m, st = sg.force_missing_mask(table[f'stance_{leg}'], table[f'grf_vertical_{leg}_BW'], bw_n)
            masks[leg], mask_stats[leg] = m, st
            vertical_n[leg] = table[f'grf_vertical_{leg}_BW'] * bw_n
        entry['force_mask'] = mask_stats
        entry['force_mask_threshold_N'] = sg.FORCE_MASK_N
        out = Path(mask_dir) / subject / mode
        out.mkdir(parents=True, exist_ok=True)
        layer = pa.table({'time_s': pa.array(table['time_s']), 'force_missing_left': pa.array(masks['left']),
                          'force_missing_right': pa.array(masks['right'])})
        with open(out / f'{rec}.parquet', 'xb') as f:
            pq.write_table(layer, f, row_group_size=4096, compression='zstd')
        entry['force_mask_layer'] = f'force_mask/{subject}/{mode}/{rec}.parquet'
    steps = []
    for leg in LEGS:
        g = gc[leg]
        h, pct = np.asarray(g['Header'], float), np.asarray(g['HeelStrike'], float)
        toe = sg.event_times(h, g['ToeOff'])
        rs = sg.resets(pct)
        entry['resets'][leg] = int(len(rs))
        for k in range(len(rs) - 1):
            a, b = int(rs[k]), int(rs[k + 1])
            t0, t1 = float(h[a]), float(h[b])
            c = sg.classify_step_authors(mode, meta, leg, t0, t1, h, pct, a, b, span)
            step = {'step_id': f'{subject}/{mode}/{rec}/{leg}/{k:04d}', 'subject': subject, 'mode': mode, 'recording': rec,
                    'leg': leg, 'k': k, 'start_s': t0, 'end_s': t1, 'duration_s': t1 - t0, 'gc_start_index': a,
                    'gc_end_index': b, 'gc_samples': b - a + 1, 'max_source_pct': float(np.nanmax(pct[a:b + 1])), **c}
            if table is not None:
                t = table['time_s']
                i0, i1 = int(np.searchsorted(t, t0 - 1e-9)), int(np.searchsorted(t, t1 + 1e-9, side='right'))
                stance = np.asarray(table[f'stance_{leg}'], bool)[i0:i1]
                mk = masks[leg][i0:i1]
                step['stance_samples'] = int(stance.sum())
                step['force_missing_stance_samples'] = int(mk.sum())
                step['force_check'] = sg.force_check(t, vertical_n[leg], t0, t0, t1)
                to_in = toe[(toe > t0) & (toe < t1)]
                if to_in.size:
                    crossing = _falling(t, vertical_n[leg], float(to_in[0]))
                    step['force_check']['toe_off_offset_ms'] = crossing
            steps.append(step)
    for s in steps:
        steps_f.write(json.dumps(s, sort_keys=True, default=_json_default) + '\n')
    entry['steps'] = len(steps)
    entry['steps_by_disposition'] = dict(Counter(s['disposition'] for s in steps))
    entry['steps_by_reason'] = dict(Counter(s['reason'] or 'eligible' for s in steps))
    # authors' right-leg cutting
    right = [s for s in steps if s['leg'] == 'right']
    ours = np.array([s['start_s'] for s in right]) if right else np.zeros(0)
    g = gc['right']
    h, pct = np.asarray(g['Header'], float), np.asarray(g['HeelStrike'], float)
    ivs = sg.authors_intervals(h, pct)
    windows = (meta or {}).get('label_windows') or []
    matched_ours = set()
    counts = Counter()
    for iv in ivs:
        near = int(np.argmin(np.abs(ours - iv['start_s']))) if ours.size else None
        off = float((ours[near] - iv['start_s']) * 1000.0) if near is not None else None
        ok = near is not None and abs(off) <= MATCH_S * 1000 and abs(right[near]['end_s'] - iv['end_s']) <= MATCH_S
        rec_line = {'subject': subject, 'mode': mode, 'recording': rec, 'kind': iv['kind'], 'start_s': iv['start_s'],
                    'end_s': iv['end_s'], 'status': 'matched' if ok else 'extra', 'start_offset_ms': off if ok else None,
                    'nearest_start_offset_ms': off, 'our_step_id': right[near]['step_id'] if ok else None,
                    'our_disposition': right[near]['disposition'] if ok else None,
                    'our_reason': right[near]['reason'] if ok else None,
                    'our_label': right[near]['label'] if ok else None}
        if ok:
            matched_ours.add(near)
            rec_line['end_offset_ms'] = float((right[near]['end_s'] - iv['end_s']) * 1000.0)
        if mode == 'treadmill':
            vals = sg.distinct_speed_values(meta, iv['start_s'], iv['end_s'])
            rec_line['authors_class'] = sg.authors_class('treadmill', [], n_speed_values=None if vals is None else len(vals))
        elif meta and meta.get('label_present'):
            seq = [w['label'] for w in sg.overlapped_windows(windows, iv['start_s'], iv['end_s'])]
            rec_line['authors_class'] = sg.authors_class(mode, seq, meta.get('trans_leg_ascent'), meta.get('trans_leg_descent'),
                                                         sg.as_list(meta.get('leading_leg_start')), sg.as_list(meta.get('leading_leg_stop')),
                                                         sg.as_list(meta.get('turn')))
        else:
            rec_line['authors_class'] = 'no_label_table'
        counts[rec_line['status']] += 1
        auth_f.write(json.dumps(rec_line, sort_keys=True, default=_json_default) + '\n')
    for j, s in enumerate(right):
        if j not in matched_ours:
            counts['missed'] += 1
            auth_f.write(json.dumps({'subject': subject, 'mode': mode, 'recording': rec, 'kind': 'our_step_without_authors_interval',
                                     'start_s': s['start_s'], 'end_s': s['end_s'], 'status': 'missed',
                                     'our_step_id': s['step_id'], 'our_disposition': s['disposition'],
                                     'our_reason': s['reason'], 'our_label': s['label'], 'authors_class': None},
                                    sort_keys=True) + '\n')
    entry['authors_right_leg'] = dict(counts)
    # recording disposition: exactly one
    d = entry['steps_by_disposition']
    if d.get('eligible'):
        entry.update(status='segmented', reason=None)
    elif d.get('held'):
        entry.update(status='held', reason=[s['reason'] for s in steps if s['disposition'] == 'held'][0])
    else:
        entry.update(status='excluded_no_eligible_step',
                     reason='; '.join(f'{k}: {v}' for k, v in sorted(Counter(s['reason'] for s in steps).items())) or 'no source steps')
    if table is None:
        entry['table_note'] = 'continuous table not available (recording excluded in the merged pass); steps listed without force data'
    return entry


def _falling(t, v, toe_time):
    """Offset in ms of the nearest falling crossing of the threshold from a source toe off, or None."""
    v = np.asarray(v, float)
    ok = np.isfinite(v[:-1]) & np.isfinite(v[1:])
    with np.errstate(invalid='ignore'):
        hit = ok & (v[:-1] >= sg.FORCE_MASK_N) & (v[1:] < sg.FORCE_MASK_N)
    cr = np.asarray(t, float)[np.flatnonzero(hit) + 1]
    cr = cr[np.abs(cr - toe_time) <= sg.CROSSING_SEARCH_S]
    return float((cr[np.argmin(np.abs(cr - toe_time))] - toe_time) * 1000.0) if cr.size else None


def process_one(row, labels, pass_root, pass_rows, out_root, steps_f, auth_f, roots=None):
    roots = roots or ROOTS
    subject, mode, rec = row['subject'], row['mode'], row['recording']
    base = roots[row['source']] / subject / row['session'] / mode
    try:
        gc = {leg: src.read_numeric_table(base / ('gcLeft' if leg == 'left' else 'gcRight') / f'{rec}.mat') for leg in LEGS}
        for leg in LEGS:
            for col in ('Header', 'HeelStrike', 'ToeOff'):
                if col not in gc[leg]:
                    raise ValueError(f'gc{leg} has no {col} column')
        pe = pass_rows.get((mode, rec))
        table = read_pass_table(pass_root, pe)
        bw = float(pe['body_weight_N']) if pe and pe.get('body_weight_N') else None
        if table is not None and bw is None:
            raise ValueError('no body weight in the pass ledger')
        return segment_recording(row, labels.get((mode, rec)), gc, table, bw, Path(out_root) / 'force_mask', steps_f, auth_f)
    except Exception as exc:                        # never stop the batch; the reason is listed
        return {'subject': subject, 'session': row['session'], 'mode': mode, 'recording': rec, 'source': row['source'],
                'status': 'excluded_unprocessable', 'reason': f'error: {type(exc).__name__}: {exc}'[:400]}


def run(args):
    out_root = Path(args.out_root)
    if out_root.exists() and any(out_root.iterdir()):
        raise SystemExit(f'{out_root} is not empty; outputs go to a new root')
    out_root.mkdir(parents=True, exist_ok=True)
    inv = load_inventory()
    records = list(args.record or [])
    if args.subject:
        records += [f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject]
    if not records:
        raise SystemExit('no recordings named')
    entries, cache = [], {}
    with open(out_root / 'steps.jsonl', 'x') as steps_f, open(out_root / 'authors_intervals.jsonl', 'x') as auth_f:
        for item in records:
            subject, mode, name = item.split('/')
            row = inv.get((subject, mode, name))
            if row is None:
                entries.append({'subject': subject, 'mode': mode, 'recording': name, 'status': 'excluded_unprocessable',
                                'reason': 'not in RB01 inventory'})
                continue
            if subject not in cache:
                cache[subject] = (load_labels(subject),) + load_pass_ledger(subject)
            labels, proot, prows = cache[subject]
            entries.append(process_one(row, labels, proot, prows, out_root, steps_f, auth_f))
            pygc.collect()
            entries[-1]['peak_rss_mib_after'] = peak_rss_mib()
    with open(out_root / 'ledger.jsonl', 'x') as f:
        for e in entries:
            f.write(json.dumps(e, sort_keys=True, default=_json_default) + '\n')
    steps = sum(e.get('steps', 0) for e in entries)
    summary = {'status': 'run_done_unreviewed', 'scientific_approval': False, 'recordings': len(entries),
               'recording_status': dict(Counter(e['status'] for e in entries)), 'steps': steps,
               'unprocessable': [{'recording': f"{e['subject']}/{e['mode']}/{e['recording']}", 'reason': e['reason']}
                                 for e in entries if e['status'] == 'excluded_unprocessable'],
               'force_mask_threshold_N': sg.FORCE_MASK_N, 'peak_rss_mib': peak_rss_mib(),
               'code_sha256': {c: sha256_file(ROOT / c) for c in CODE}}
    with open(out_root / 'run_summary.json', 'x') as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write('\n')
    return 0


def pilot_records(inv, seed=20261126):
    """AB06 levelground, treadmill and the failing stair recording are named; the ramp, a second stair recording and one
    recording of a new participant (extracted from the zips) are drawn with the recorded seed."""
    rng = random.Random(seed)
    out = ['AB06/levelground/levelground_ccw_fast_01_01', 'AB06/treadmill/treadmill_01_01',
           'AB06/stair/stair_1_l_01_02']
    for subject, mode in (('AB06', 'ramp'), ('AB06', 'stair'), ('AB17', 'stair'), ('AB17', 'levelground'), ('AB17', 'treadmill'),
                          ('AB06', 'levelground')):
        names = sorted(r for (s, m, r) in inv if s == subject and m == mode and f'{s}/{m}/{r}' not in out)
        out.append(f'{subject}/{mode}/{rng.choice(names)}')
    return out


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    inv = load_inventory()
    records = [f'{sj}/{m}/{r}' for (sj, m, r) in sorted(inv) if sj == args.subject] if args.subject else (args.record or pilot_records(inv))
    subjects = sorted({r.split('/')[0] for r in records})
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE + ('contributor_tools/guarded_launcher.py',)}
    bindings[INVENTORY] = gl.sha256_file(ROOT / INVENTORY)
    for s in subjects:
        bindings[f'{LABELS_RB03}/{s}/labels_{s}.jsonl'] = gl.sha256_file(ROOT / LABELS_RB03 / s / f'labels_{s}.jsonl')
        pr = PASS_ROOT.format(subject=s)
        bindings[f'{pr}/ledger.jsonl'] = gl.sha256_file(ROOT / pr / 'ledger.jsonl')
    command = ['python3', 'contributor_tools/run_gt21_rb_segment.py', 'run', '--out-root', args.out_root]
    if args.subject:
        command += ['--subject', args.subject]
    else:
        for r in records:
            command += ['--record', r]
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.out_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['run_summary.json', 'ledger.jsonl'], 'address_space_mib': 768,
            'disk_admission': [{'path': str(ROOT / 'converted_datasets'), 'min_free_mib': 15360}]}
    with open(args.spec_out, 'x') as f:
        json.dump(spec, f, indent=2)
        f.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--out-root', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject')
    s = sub.add_parser('spec')
    s.add_argument('--job-id', required=True)
    s.add_argument('--out-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--record', action='append')
    s.add_argument('--subject')
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
