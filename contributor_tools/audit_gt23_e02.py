"""GT23-E02 readback: compares a GT23-E02 root with the GT23-E01 root it supersedes, recording by recording.

Written separately from the runner (it imports neither run_gt23_e02 nor gt23_fixes). For every recording that the E02 root
re-exports it checks, on the written tables:

  1. the E02 root holds exactly the observations (identity, row count, order) of that recording in the E01 root, no more;
  2. every cell is identical to E01 (bit for bit, missing equals missing) except
       a. angle cells (segment and joint angles in radians): time-table samples differ by a whole multiple of 2 pi; a phase
          sample either differs by a whole multiple of 2 pi or lies between two source samples of which one was changed
          (its interpolation crossed a wrap pair); the finite/missing pattern is unchanged;
       b. foot-frame pressure-point columns of step_ups recordings: all missing, with the stated reason in held_signals and the
          step-up note added to task_info, nothing else in those two strings changed;
  3. the set of changed cells equals the changes.jsonl log exactly (same observation, column and sample, same old and new value);
  4. unchanged recordings are absent from the E02 root; superseded recordings are the ones the summary lists.
Streams in 4096-row batches; one table at a time. Run through the guarded launcher.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
for _k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_k, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

TWO_PI = 2 * np.pi
BASE = 'converted_datasets/reconversion_v2'
STR_COLUMNS = ('subject', 'source_recording_id', 'observation_id', 'reference_side', 'observation_type', 'task', 'task_id',
               'task_info', 'subject_metadata', 'held_signals')
ANGLE_PREFIXES = ('pelvis_sagittal_angle', 'thigh_sagittal_angle', 'shank_sagittal_angle', 'foot_sagittal_angle',
                  'hip_flexion_angle', 'knee_flexion_angle', 'ankle_dorsiflexion_angle')
COP_PREFIXES = ('cop_anterior_', 'cop_vertical_', 'cop_lateral_')
STEP_UP_NOTE_START = 'step_up foot-frame pressure point is held'
STEP_UP_REASON_START = 'held: the foot stands on a step of about 0.5 m'
BATCH = 4096
TOL = 1e-9


def is_angle(c):
    return c.endswith('_rad') and c.startswith(ANGLE_PREFIXES)


def is_cop(c):
    return c.startswith(COP_PREFIXES) and c.endswith('_m')


def peak_rss_mib():
    return round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


class Stream:
    """Row batches of one table (optionally only rows of the given recordings), as dict of numpy arrays / string lists."""

    def __init__(self, path, keep=None):
        self.pf = pq.ParquetFile(str(path), buffer_size=0)
        self.it = self.pf.iter_batches(batch_size=BATCH, use_threads=False)
        self.keep = pa.array(sorted(keep), type=pa.string()) if keep is not None else None
        self.buf = None
        self.names = list(self.pf.schema_arrow.names)
        self.done = False

    def _next(self):
        for batch in self.it:
            if self.keep is not None:
                mask = pc.is_in(batch.column('source_recording_id'), value_set=self.keep)
                batch = batch.filter(mask)
            if batch.num_rows:
                return {n: (batch.column(n).to_pylist() if n in STR_COLUMNS else batch.column(n).to_numpy(zero_copy_only=False))
                        for n in self.names}
        self.done = True
        return None

    def take(self, n):
        """Exactly n rows (fewer only at the end)."""
        out, have = [], 0
        while have < n:
            if self.buf is None:
                self.buf = self._next()
                if self.buf is None:
                    break
            m = len(self.buf[self.names[0]])
            k = min(n - have, m)
            out.append({c: v[:k] for c, v in self.buf.items()})
            rest = {c: v[k:] for c, v in self.buf.items()}
            self.buf = rest if m - k else None
            have += k
        if not out:
            return None
        return {c: (np.concatenate([o[c] for o in out]) if c not in STR_COLUMNS else [x for o in out for x in o[c]]) for c in self.names}


def compare_table(kind, e01_path, e02_path, recordings, step_up_recs, changes, report):
    """Walk both tables in step. kind: 'phase' or 'time'."""
    keep = list(recordings)
    a = Stream(e01_path, keep)
    b = Stream(e02_path)
    diffs = set()
    counter = {}
    rows = 0
    while True:
        y = b.take(BATCH)
        if y is None:
            break
        x = a.take(len(y['source_recording_id']))
        n = len(y['source_recording_id'])
        if x is None or len(x['source_recording_id']) != n:
            report['problems'].append(f'{kind}: E01 has fewer rows than E02 at row {rows}')
            return diffs, rows
        for c in STR_COLUMNS:
            if c in ('task_info', 'held_signals'):
                continue
            if x[c] != y[c]:
                report['problems'].append(f'{kind}: {c} differs near row {rows}')
                return diffs, rows
        index_col = 'phase_ipsi' if kind == 'phase' else 'time_s'
        if not np.array_equal(x[index_col], y[index_col]):
            report['problems'].append(f'{kind}: {index_col} differs near row {rows}')
            return diffs, rows
        recs = y['source_recording_id']
        if kind == 'phase':
            idx_arr = np.rint(np.asarray(y['phase_ipsi']) * 149 / 100.0).astype(int)
        else:
            idx_arr = np.zeros(n, dtype=int)
            for j in range(n):
                k = (y['observation_id'][j], y['reference_side'][j], recs[j])
                idx_arr[j] = counter.get(k, 0)
                counter[k] = idx_arr[j] + 1
        is_su = np.array([r in step_up_recs for r in recs])
        # string columns that may change only for step_ups recordings
        for i in np.flatnonzero([(x['task_info'][j] != y['task_info'][j]) or (x['held_signals'][j] != y['held_signals'][j]) for j in range(n)]):
            if not is_su[i]:
                report['problems'].append(f'{kind}: task_info or held_signals changed outside a step_ups recording at row {rows + i}')
                continue
            ti_old, ti_new = json.loads(x['task_info'][i]), json.loads(y['task_info'][i])
            lim_old, lim_new = ti_old.pop('limits', []), ti_new.pop('limits', [])
            if ti_old != ti_new or lim_new[:len(lim_old)] != lim_old or len(lim_new) != len(lim_old) + 1 \
                    or not str(lim_new[-1]).startswith(STEP_UP_NOTE_START):
                report['problems'].append(f'{kind}: task_info differs by more than the step-up note at row {rows + i}')
            h_old, h_new = json.loads(x['held_signals'][i]), json.loads(y['held_signals'][i])
            added = {k for k in h_new if k not in h_old}
            if any(h_new[k] != h_old[k] for k in h_old) or not all(is_cop(k) for k in added) \
                    or not all(str(h_new[k]).startswith(STEP_UP_REASON_START) for k in added):
                report['problems'].append(f'{kind}: held_signals differs by more than the held pressure point at row {rows + i}')
        for c in a.names:
            if c in STR_COLUMNS or c == index_col:
                continue
            xv, yv = x[c], y[c]
            same = (xv == yv) | (np.isnan(xv) & np.isnan(yv))
            bad = np.flatnonzero(~same)
            if not len(bad):
                continue
            for i in bad:
                rec = recs[i]
                key = (y['observation_id'][i], y['reference_side'][i])
                idx = int(idx_arr[i])
                if is_angle(c) and np.isfinite(xv[i]) and np.isfinite(yv[i]):
                    d = (yv[i] - xv[i]) / TWO_PI
                    whole = abs(d - round(d)) * TWO_PI <= TOL
                    if kind == 'time' and not whole:
                        report['problems'].append(f'time: {c} changed by a non-whole turn at row {rows + i}')
                    diffs.add((kind, key[0], key[1], c, idx, float(xv[i]), float(yv[i]), whole))
                elif c.endswith('_rad_s') and c.split('_velocity_')[0] in ('hip_flexion', 'knee_flexion', 'ankle_dorsiflexion') \
                        and np.isfinite(xv[i]) and np.isfinite(yv[i]):
                    diffs.add((kind, key[0], key[1], c, idx, float(xv[i]), float(yv[i]), False))
                    report['speed_cells_changed'] = report.get('speed_cells_changed', 0) + 1
                elif is_cop(c) and rec in step_up_recs and np.isnan(yv[i]) and np.isfinite(xv[i]):
                    report['held_cop_cells'] = report.get('held_cop_cells', 0) + 1
                elif is_cop(c) and rec in step_up_recs and np.isnan(yv[i]) and np.isnan(xv[i]):
                    pass
                else:
                    report['problems'].append(f'{kind}: unexplained change in {c} at row {rows + i} ({rec})')
                    if len(report['problems']) > 50:
                        return diffs, rows
        rows += n
    rest = a.take(1)
    if rest is not None:
        report['problems'].append(f'{kind}: E01 holds more rows of the re-exported recordings than E02')
    return diffs, rows


def run(args):
    sub = args.subject
    e01 = ROOT / (args.e01_root or f'{BASE}/gt23_pl_e01_batch_{sub}')
    e02 = ROOT / args.e02_root
    out = ROOT / args.output_root
    out.mkdir(parents=True, exist_ok=False)
    summary = json.loads((e02 / 'e02_summary.json').read_text())
    exported = set(f'{sub}/{r}' for r in summary['recordings_exported'])
    scan = jsonl(e02 / 'scan.jsonl')
    step_up = {f'{sub}/{r["recording"]}' for r in scan if r['step_up_hold']}
    report = {'subject': sub, 'e02_root': args.e02_root, 'problems': [], 'checks': {}}
    changes = jsonl(e02 / 'changes.jsonl')
    # 1. observation sets
    obs01 = [o for o in jsonl(e01 / 'observations.jsonl') if o['source_recording_id'] in exported]
    obs02 = jsonl(e02 / 'observations.jsonl')
    key = lambda o: (o['table'], o['observation_id'], o['reference_side'], o['rows'], o['observation_type'])  # noqa: E731
    report['checks']['observation_sets_equal'] = [key(o) for o in obs01] == [key(o) for o in obs02]
    if not report['checks']['observation_sets_equal']:
        report['problems'].append('the E02 observations are not the E01 observations of the re-exported recordings, in order')
    report['observations'] = len(obs02)
    # unchanged recordings absent
    present = {o['source_recording_id'] for o in obs02}
    report['checks']['only_exported_recordings_present'] = present == exported
    if present != exported:
        report['problems'].append('recordings in the E02 root differ from the summary list')
    # 2. cell comparison
    all_diffs = set()
    rows = {}
    for kind in ('phase', 'time'):
        d, r = compare_table(kind, e01 / f'{kind}.parquet', e02 / f'{kind}.parquet', exported, step_up, changes, report)
        all_diffs |= d
        rows[kind] = r
    report['rows_compared'] = rows
    # 3. equal to the log
    logged = {(c['table'], c['observation_id'], c['reference_side'], c['column'], c['sample_index'], c['old_rad'], c['new_rad'])
              for c in changes}
    seen = {(k, o, s, c, i, ov, nv) for (k, o, s, c, i, ov, nv, _w) in all_diffs}
    only_log = logged - seen
    only_seen = seen - logged
    report['checks']['changed_cells_equal_log'] = not only_log and not only_seen
    report['changed_cells'] = len(seen)
    report['changed_cells_by_table'] = {t: sum(1 for s in seen if s[0] == t) for t in ('phase', 'time')}
    report['phase_cells_not_whole_turn'] = sum(1 for d in all_diffs if d[0] == 'phase' and not d[7] and not d[3].endswith('_rad_s'))
    report.setdefault('speed_cells_changed', 0)
    report['observations_with_changed_cells'] = len({(s[0], s[1], s[2]) for s in seen})
    if only_log or only_seen:
        report['problems'].append(f'log and tables differ: {len(only_log)} only in the log, {len(only_seen)} only in the tables')
        report['examples_only_log'] = sorted(only_log)[:3]
        report['examples_only_seen'] = sorted(only_seen)[:3]
    report['status'] = 'pass' if not report['problems'] else 'fail'
    report['peak_rss_mib'] = peak_rss_mib()
    tmp = out / 'audit_report.tmp'
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    tmp.replace(out / 'audit_report.json')
    return 0 if report['status'] == 'pass' else 1


CODE = ('contributor_tools/audit_gt23_e02.py', 'contributor_tools/guarded_launcher.py')


def make_spec(args):
    from contributor_tools import guarded_launcher as gl
    e01 = f'{BASE}/gt23_pl_e01_batch_{args.subject}'
    command = ['python3', 'contributor_tools/audit_gt23_e02.py', 'run', '--subject', args.subject, '--e02-root', args.e02_root,
               '--output-root', args.output_root]
    bindings = {c: gl.sha256_file(ROOT / c) for c in CODE}
    for root, names in ((e01, ('run_summary.json', 'observations.jsonl', 'phase.parquet', 'time.parquet')),
                        (args.e02_root, ('run_summary.json', 'observations.jsonl', 'phase.parquet', 'time.parquet', 'changes.jsonl',
                                         'scan.jsonl', 'e02_summary.json'))):
        for n in names:
            bindings[f'{root}/{n}'] = gl.sha256_file(ROOT / root / n)
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root,
            'receipt_path': args.receipt, 'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30,
            'poll_seconds': 15, 'startup_memory_mib': {'linux': 3584, 'windows': 2816},
            'runtime_memory_mib': {'linux': 2048, 'windows': 2048}, 'expected_output_names': ['audit_report.json'],
            'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('run')
    s.add_argument('--subject', required=True)
    s.add_argument('--e02-root', required=True)
    s.add_argument('--e01-root')
    s.add_argument('--output-root', required=True)
    s = sub.add_parser('spec')
    s.add_argument('--subject', required=True)
    s.add_argument('--e02-root', required=True)
    s.add_argument('--job-id', required=True)
    s.add_argument('--output-root', required=True)
    s.add_argument('--receipt', required=True)
    s.add_argument('--spec-out', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
