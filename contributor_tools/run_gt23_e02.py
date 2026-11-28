"""GT23-E02 runner: angle-wrap fix and step-up pressure-point hold, then a re-export of only what changes.

Subcommands
  run      One participant. Scans every recording of the participant (C06 angle and speed columns only, one recording at a
           time) with the rules in gt23_fixes.py. Recordings with no changed sample and no step-up hold are listed as
           unchanged and are NOT exported. Every other recording is exported with the E01 rules (run_gt23_e01.process_recording)
           from the C06 columns after the fixes, into a NEW root:
             phase.parquet, time.parquet, observations.jsonl, exclusions.jsonl, authors_windows.jsonl, recordings.jsonl,
             README.md, run_summary.json         (same layout as an E01 root, changed recordings only)
             scan.jsonl                          every recording: changed samples per column, time-table L2 jumps before and
                                                 after, each published jump classified as wrap or not a wrap
             changes.jsonl                       every changed sample, per observation (table, column, index, old, new, turns)
             step_up_evidence.jsonl              heel height above the plate surface on loaded samples, per step_ups recording
             e02_summary.json                    counts and the superseded list (E01 recordings this root replaces)
  spec     Writes the guarded-launcher job spec.
  summary  Adds participant roots.

The E01 files are never touched. Memory: one recording resident, as in E01.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import types

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from contributor_tools import gt23_export as ex  # noqa: E402
from contributor_tools import gt23_fixes as fx  # noqa: E402
from contributor_tools import run_gt23_e01 as e01  # noqa: E402
from contributor_tools import gt23_segmentation as seg  # noqa: E402
from contributor_tools import gt23_source_reader as rd  # noqa: E402

TWO_PI = fx.TWO_PI
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')
SUBJECTS = e01.SUBJECTS
BASE = e01.BASE
X01_ROOT = lambda s: f'{BASE}/gt23_x01_batch_{s}' + ('_r2' if s == 'AB01' else '')  # noqa: E731
CODE = ('contributor_tools/gt23_fixes.py', 'contributor_tools/run_gt23_e02.py') + e01.CODE + (
    'contributor_tools/gt23_segmentation.py', 'contributor_tools/gt23_conventions.py', 'contributor_tools/run_gt23_c06.py')
SCHEMA_ID = 'locohub.gt23_e02/1'
SCAN_COLUMNS = ['pelvis_sagittal_angle_rad']
for _s in fx.SIDES:
    SCAN_COLUMNS += [f'{k}_sagittal_angle_{_s}_rad' for k in ('thigh', 'shank', 'foot')]
    SCAN_COLUMNS += [f'{w}_angle_{_s}_rad' for _, w in fx.JOINTS] + [f'{w}_velocity_{_s}_rad_s' for _, w in fx.JOINTS]
ANGLE_COLUMNS = [c for c in SCAN_COLUMNS if c.endswith('_rad')]
EVIDENCE_NOTE = ('Superseded: the recordings listed in e02_summary.json are replaced by this root; the same recordings in the '
                 'E01 root of this participant (gt23_pl_e01_batch_<AB>) are superseded and kept as evidence.')


class FixError(RuntimeError):
    pass


def read_columns(path, names):
    pf = pq.ParquetFile(str(path), buffer_size=0)
    have = set(pf.schema_arrow.names)
    names = [n for n in names if n in have]
    parts = {n: [] for n in names}
    for batch in pf.iter_batches(batch_size=e01.READ_BATCH, columns=names, use_threads=False):
        for n in names:
            parts[n].append(batch.column(n).to_numpy(zero_copy_only=False))
    return {n: np.concatenate(v).astype(np.float64, copy=False) for n, v in parts.items()}


def jump_report(old, new, cap=50):
    """Time-table L2 jumps (30 degrees between neighbours, as Q01 L2) before and after, per angle column."""
    out = {}
    for c in ANGLE_COLUMNS:
        if c not in old:
            continue
        after = new.get(c, old[c])
        wrap_idx, remains = fx.classify_jumps(old[c], after)
        if len(wrap_idx) or len(remains):
            def row(i):
                return {'index': int(i), 'published_step_deg': float(np.degrees(old[c][i] - old[c][i - 1])),
                        'step_after_deg': float(np.degrees(after[i] - after[i - 1]))}
            out[c] = {'published_failures': int(len(wrap_idx) + len(remains)), 'wrap_removed': int(len(wrap_idx)),
                      'not_a_wrap_remains': int(len(remains)),
                      'wrap_samples': [row(i) for i in wrap_idx[:cap]], 'not_a_wrap_samples': [row(i) for i in remains[:cap]]}
    return out


def scan_recording(path):
    """(old columns, new columns changed, change report, jump report) for one recording; nothing is written."""
    old = read_columns(path, SCAN_COLUMNS)
    new, report = fx.fix_angles(old)
    return old, new, report, jump_report(old, new)


def heel_evidence(subject, rec, c06_cols):
    """Heel height above the recorded plate surface on loaded samples, per leg (markers from the source, evidence only)."""
    from contributor_tools import run_gt23_c06 as c06mod
    trc = SOURCE / 'RawData' / subject / 'MarkerData' / f'{rec}.trc'
    mk, absent, n = c06mod.read_markers(trc, ('LCAL', 'RCAL'))
    out = {}
    for side, S in (('left', 'L'), ('right', 'R')):
        out[side] = fx.heel_gap_evidence(mk[f'{S}CAL'][:, 1], c06_cols[f'cop_lab_y_{side}_m'], c06_cols[f'grf_lab_y_{side}_N'])
        if f'{S}CAL' in absent:
            out[side]['marker_absent'] = True
    return out


class State:
    """Per-recording context shared by the patched reader and writers."""
    rec = None
    old = {}            # id(new array) -> old array (only columns that changed)
    name_of = {}        # id(new array) -> C06 column name
    calls = []          # results of ex.phase_samples calls for the observation being built
    changes = []        # output rows
    held_cop = False


STATE = State()
_orig_read_all = e01.read_all
_orig_phase = ex.phase_samples
_orig_limits = ex.recording_limits
_orig_readme = e01.readme_text


def patched_read_all(path):
    d = _orig_read_all(path)
    if 'gt23_planes_batch_' not in str(path):
        return d
    rec = Path(path).stem
    new, report = fx.fix_angles({c: d[c] for c in SCAN_COLUMNS if c in d})
    STATE.old, STATE.name_of, STATE.calls = {}, {}, []
    for name, arr in new.items():
        STATE.old[name] = d[name]
        d[name] = arr
    if STATE.held_cop:
        cop_new, _ = fx.hold_step_up_cop(d, {})
        d.update(cop_new)
    STATE.rec = rec
    STATE.changed_names = set(new)
    for name in new:
        STATE.name_of[id(d[name])] = name
    STATE.old_by_id = {id(d[n]): STATE.old[n] for n in new}
    STATE.changed_idx = {n: set(report[n]['indices'].tolist()) for n in new}
    return d


def patched_phase(values, a, b, n=ex.N_PHASE):
    out = _orig_phase(values, a, b, n)
    old = STATE.old_by_id.get(id(values))
    if old is None:
        STATE.calls.append(None)
    else:
        STATE.calls.append((_orig_phase(old, a, b, n), STATE.name_of[id(values)], a, b))
    return out


def patched_limits(subject, entry, task):
    limits = _orig_limits(subject, entry, task)
    if task == fx.STEP_UP_TASK:
        limits.append(fx.STEP_UP_NOTE)
    return limits


class LoggingWriters(e01.Writers):
    def add_phase(self, obs):
        meta = obs['meta']
        names = list(obs['values'])
        if len(names) != len(STATE.calls):
            raise FixError('phase value count differs from the number of recorded interpolations')
        for name, call in zip(names, STATE.calls):
            if call is None:
                continue
            old, src, a, b = call
            new = obs['values'][name]
            self._log_phase(meta, name, src, old, new, a, b)
        STATE.calls = []
        super().add_phase(obs)

    def write_time(self, meta, held_json, time_s, signals):
        for name, arr in signals.items():
            old = STATE.old_by_id.get(id(arr))
            if old is not None:
                self._log('time', meta, name, STATE.name_of[id(arr)], old, arr, 'time_s', time_s)
        super().write_time(meta, held_json, time_s, signals)

    def _log_phase(self, meta, name, src, old, new, a, b):
        """Phase samples are interpolated between two source samples (lo, hi). A changed phase sample is a whole turn when both
        neighbours moved by whole turns together; a sample interpolated across a wrap pair changes by a fraction of a turn
        because the published interpolation mixed the two branches. The second kind needs a changed source sample at lo or hi."""
        if not np.array_equal(np.isfinite(old), np.isfinite(new)):
            raise FixError('finite pattern changed in a phase observation')
        steps = np.arange(ex.N_PHASE, dtype=np.int64) * (b - a)
        lo = a + steps // (ex.N_PHASE - 1)
        hi = np.minimum(lo + 1, b)
        changed_source = STATE.changed_idx[src]
        speed = src.endswith('_rad_s')
        for i in np.flatnonzero(np.isfinite(old) & (new != old)):
            turns = (new[i] - old[i]) / TWO_PI
            whole = (not speed) and abs(turns - round(turns)) * TWO_PI <= fx.MULTIPLE_TOL
            if not whole and not ({int(lo[i]), int(hi[i])} & changed_source):
                raise FixError(f'{meta["observation_id"]} {name}[{i}] changed by a fraction of a turn without a changed source sample')
            STATE.changes.append({'table': 'phase', 'observation_id': meta['observation_id'], 'reference_side': meta['reference_side'],
                                  'source_recording_id': meta['source_recording_id'], 'column': name, 'c06_column': src,
                                  'sample_index': int(i), 'axis': float(i) * 100.0 / (ex.N_PHASE - 1),
                                  'source_index_lo': int(lo[i]), 'source_index_hi': int(hi[i]),
                                  'old_rad': float(old[i]), 'new_rad': float(new[i]),
                                  'kind': 'speed_rederived' if speed else 'whole_turns' if whole else 'interpolated_across_a_wrap',
                                  'whole_turns': int(round(turns)) if whole else None})

    def _log(self, table, meta, name, src, old, new, axis, time_s=None):
        if src.endswith('_rad_s'):                       # speeds are re-derived, not shifted; expected to be unchanged
            idx = np.flatnonzero(np.isfinite(old) & (new != old))
        else:
            idx = fx.check_whole_turns(old, new)       # time table: every changed angle sample is a whole multiple of 360 degrees
        for i in idx:
            STATE.changes.append({'table': table, 'observation_id': meta['observation_id'], 'reference_side': meta['reference_side'],
                                  'source_recording_id': meta['source_recording_id'], 'column': name, 'c06_column': src,
                                  'sample_index': int(i), 'axis': float(time_s[i]), 'old_rad': float(old[i]), 'new_rad': float(new[i]),
                                  'kind': 'speed_rederived' if src.endswith('_rad_s') else 'whole_turns',
                                  'whole_turns': None if src.endswith('_rad_s') else int(round((new[i] - old[i]) / TWO_PI))})


def readme_extra(subject):
    return (_orig_readme(subject).replace('(GT23-E01, unreviewed)', '(GT23-E02, unreviewed; changed recordings only)') +
            '\n## GT23-E02 changes\n'
            '- Segment angles are unwrapped along each continuous recording before the joint angles are differenced; only whole '
            'multiples of 360 degrees were added to any angle sample, and each changed sample is listed in `changes.jsonl`.\n'
            f'- {fx.STEP_UP_NOTE}\n- {EVIDENCE_NOTE}\n')


def run(args):
    subject = args.subject
    out_root = ROOT / args.output_root
    if out_root.exists() and any(out_root.iterdir()):
        raise FixError(f'{out_root} is not empty; never overwrite')
    roots = e01.roots_for(subject, args.base)
    ledger = {r['recording']: r for r in e01.jsonl(ROOT / roots['s01'] / 'ledger.jsonl')}
    c06 = {r['recording']: r for r in e01.jsonl(ROOT / roots['c06'] / 'ledger.jsonl')}
    wanted = args.records or sorted(ledger)
    scan_rows, export, evidence = [], [], []
    for rec in wanted:
        task = seg.task_of(rec)
        path = ROOT / roots['c06'] / c06[rec]['output']['file']
        old, new, report, jumps = scan_recording(path)
        hold = fx.step_up_hold(task)
        row = {'subject': subject, 'recording': rec, 'task': task, 'rows': int(len(old['pelvis_sagittal_angle_rad'])),
               'changed_samples_by_column': {c: int(len(v['indices'])) for c, v in report.items()},
               'time_table_l2_jumps': jumps, 'step_up_hold': hold,
               'whole_turns_only': True, 'c06_sha256': c06[rec]['output']['sha256']}
        if hold:
            ev = heel_evidence(subject, rec, read_columns(path, ['cop_lab_y_left_m', 'cop_lab_y_right_m', 'grf_lab_y_left_N', 'grf_lab_y_right_N']))
            evidence.append({'subject': subject, 'recording': rec, 'heel_above_plate_loaded_samples': ev,
                             'reference_line_m': fx.RAISED_GAP_M, 'rule': 'task step_ups (not a data threshold)'})
        row['exported'] = bool(report or hold)
        scan_rows.append(row)
        if row['exported']:
            export.append(rec)
        del old, new
    out_root.mkdir(parents=True, exist_ok=True)
    STATE.changes = []
    if export:
        saved = (e01.Writers, ex.phase_samples, ex.recording_limits, e01.readme_text, e01.read_all, e01.process_recording)
        e01.Writers = LoggingWriters
        ex.phase_samples = patched_phase
        ex.recording_limits = patched_limits
        e01.readme_text = readme_extra
        e01.read_all = patched_read_all
        orig_process = e01.process_recording

        def process(subject_, rec_name, s01_row, segs, authors, c06_entry, m01_entry, roots_, mass, writers, report_):
            STATE.held_cop = fx.step_up_hold(s01_row['task'])
            entry = dict(c06_entry)
            if STATE.held_cop:
                probe = {f'cop_{k}_{s}_m': np.zeros(1) for s in fx.SIDES for k in fx.COP_KEYS}
                _, held = fx.hold_step_up_cop(probe, c06_entry['held_columns'])
                entry['held_columns'] = held
            return orig_process(subject_, rec_name, s01_row, segs, authors, entry, m01_entry, roots_, mass, writers, report_)

        e01.process_recording = process
        ns = types.SimpleNamespace(subject=subject, output_root=args.output_root, records=export, base=args.base)
        try:
            rc = e01.run(ns)
        finally:
            (e01.Writers, ex.phase_samples, ex.recording_limits, e01.readme_text, e01.read_all, e01.process_recording) = saved
        if rc:
            return rc
    else:
        rc = 0
    with (out_root / 'scan.jsonl').open('x') as f:
        for r in scan_rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    with (out_root / 'changes.jsonl').open('x') as f:
        for r in STATE.changes:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    with (out_root / 'step_up_evidence.jsonl').open('x') as f:
        for r in evidence:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    by_obs = {}
    for r in STATE.changes:
        by_obs.setdefault((r['table'], r['observation_id'], r['reference_side']), 0)
        by_obs[(r['table'], r['observation_id'], r['reference_side'])] += 1
    summary = {'schema': SCHEMA_ID, 'subject': subject, 'recordings_scanned': len(wanted), 'recordings_exported': export,
               'recordings_unchanged_not_exported': [r['recording'] for r in scan_rows if not r['exported']],
               'superseded_e01_recordings': export, 'superseded_e01_root': f'{BASE}/gt23_pl_e01_batch_{subject}',
               'observations_with_changed_angle_samples': len(by_obs),
               'observations_with_changed_angle_samples_by_table': {t: sum(1 for k in by_obs if k[0] == t) for t in ('phase', 'time')},
               'changed_angle_sample_entries': len(STATE.changes),
               'changed_source_samples_by_recording': {r['recording']: r['changed_samples_by_column'] for r in scan_rows if r['changed_samples_by_column']},
               'step_up_recordings_held': [r['recording'] for r in scan_rows if r['step_up_hold']],
               'peak_rss_mib': e01.peak_rss_mib(), 'scientific_approval': False}
    for name in ('scan.jsonl', 'changes.jsonl', 'step_up_evidence.jsonl'):
        summary.setdefault('sha256', {})[name] = rd.sha256_file(out_root / name)
    tmp = out_root / 'e02_summary.tmp'
    tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    tmp.replace(out_root / 'e02_summary.json')
    return rc


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    command = ['python3', 'contributor_tools/run_gt23_e02.py', args.kind, '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    bindings[e01.README] = gl.sha256_file(ROOT / e01.README)
    if args.kind == 'run':
        command += ['--subject', args.subject]
        for r in args.records or []:
            command += ['--records', r]
        roots = e01.roots_for(args.subject)
        for p in (f"{roots['c06']}/ledger.jsonl", f"{roots['m01']}/ledger.jsonl", f"{roots['s01']}/ledger.jsonl",
                  f"{roots['s01']}/segments.jsonl", f"{roots['s01']}/authors_windows.jsonl"):
            bindings[p] = gl.sha256_file(ROOT / p)
        names = ['e02_summary.json']
    else:
        command += ['--roots'] + list(args.roots)
        for r in args.roots:
            bindings[f'{r}/e02_summary.json'] = gl.sha256_file(ROOT / r / 'e02_summary.json')
        names = ['summary.json']
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': names, 'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def summarize(args):
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    sums = [json.loads((ROOT / r / 'e02_summary.json').read_text()) for r in args.roots]
    summary = {'participants': [s['subject'] for s in sums], 'recordings_scanned': sum(s['recordings_scanned'] for s in sums),
               'recordings_exported': sum(len(s['recordings_exported']) for s in sums),
               'superseded_e01_recordings': {s['subject']: s['superseded_e01_recordings'] for s in sums},
               'observations_with_changed_angle_samples': sum(s['observations_with_changed_angle_samples'] for s in sums),
               'changed_angle_sample_entries': sum(s['changed_angle_sample_entries'] for s in sums),
               'changed_source_samples_by_recording': {s['subject']: s['changed_source_samples_by_recording'] for s in sums
                                                       if s['changed_source_samples_by_recording']},
               'step_up_recordings_held': {s['subject']: s['step_up_recordings_held'] for s in sums},
               'peak_rss_mib_by_participant': {s['subject']: s['peak_rss_mib'] for s in sums}, 'scientific_approval': False}
    (out_root / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--output-root', required=True)
    s.add_argument('--subject', required=True, choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--base', default=BASE)
    s = sub.add_parser('spec')
    s.add_argument('--kind', choices=('run', 'summary'), required=True)
    s.add_argument('--job-id', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    s.add_argument('--subject', choices=SUBJECTS)
    s.add_argument('--records', action='append')
    s.add_argument('--roots', nargs='*')
    s = sub.add_parser('summary')
    s.add_argument('--output-root', required=True)
    s.add_argument('--roots', nargs='+', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec, 'summary': summarize}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
