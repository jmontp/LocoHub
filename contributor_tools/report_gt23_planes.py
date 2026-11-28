"""GT23-PL01 comparison report: side-view planes (new) against the lab-plane angles of the previous C06 pass (batch3).

Reads only the angle columns of each recording, in 4096-row batches, one recording at a time. Writes one JSON.
Per recording and angle column: largest one-sample change (deg) and number of one-sample changes above 90 deg, for both
roots, plus the ledger-level offsets against the publisher per participant and leg. No data arrays are written.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import sys

os.environ.setdefault('ARROW_DEFAULT_MEMORY_POOL', 'system')
ROOT = Path(__file__).resolve().parents[1]
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

SUBJECTS = ('AB01', 'AB02', 'AB03', 'AB05', 'AB06', 'AB07', 'AB08', 'AB09', 'AB10', 'AB11', 'AB12', 'AB13')
OLD = 'converted_datasets/reconversion_v2/gt23_c06_batch3_{}'
NEW = 'converted_datasets/reconversion_v2/gt23_planes_batch_{}'
COLS = [f'{k}_sagittal_angle_{w}_rad' for k in ('thigh', 'shank', 'foot') for w in ('left', 'right')] + \
       [f'{k}_{w}_rad' for k in ('hip_flexion_angle', 'knee_flexion_angle', 'ankle_dorsiflexion_angle') for w in ('left', 'right')] + \
       ['pelvis_sagittal_angle_rad']
WINDOW = {'AB10': ('meander_1', 'foot_sagittal_angle_right_rad'), 'AB11': ('turn_and_step_1', 'foot_sagittal_angle_left_rad')}


def jump_stats(path):
    """Per column: finite share, largest one-sample change in degrees, number of changes above 90 deg, and share of
    samples with |angle| above 90 deg. Only consecutive finite samples count as a change."""
    pf = pq.ParquetFile(str(path), buffer_size=0)
    stats = {c: {'n': 0, 'fin': 0, 'max': 0.0, 'over90': 0, 'abs_over90': 0, 'prev': np.nan} for c in COLS}
    for batch in pf.iter_batches(batch_size=4096, columns=COLS, use_threads=False):
        for i, c in enumerate(COLS):
            x = np.degrees(batch.column(i).to_numpy(zero_copy_only=False))
            s = stats[c]
            full = np.concatenate(([s['prev']], x))
            d = np.abs(np.diff(full))
            d = d[np.isfinite(d)]
            if d.size:
                s['max'] = max(s['max'], float(d.max()))
                s['over90'] += int((d > 90).sum())
            s['n'] += len(x)
            s['fin'] += int(np.isfinite(x).sum())
            s['abs_over90'] += int((np.abs(x[np.isfinite(x)]) > 90).sum())
            s['prev'] = float(x[-1])
    return {c: {'finite_share': round(s['fin'] / s['n'], 6), 'max_one_sample_change_deg': round(s['max'], 3), 'changes_over_90_deg': s['over90'],
                'samples_abs_over_90_deg': s['abs_over90']} for c, s in stats.items()}


def run(args):
    out = {'recordings': {}, 'peak_rss_mib': None}
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    old_summary = json.loads((ROOT / args.old_summary).read_text())
    new_summary = json.loads((ROOT / args.new_summary).read_text())
    for s in SUBJECTS:
        for line in (ROOT / NEW.format(s) / 'ledger.jsonl').read_text().splitlines():
            rec = json.loads(line)['recording']
            old = jump_stats(ROOT / OLD.format(s) / f'{rec}.parquet')
            new = jump_stats(ROOT / NEW.format(s) / f'{rec}.parquet')
            out['recordings'][f'{s}/{rec}'] = {'old': old, 'new': new}
    rows = out['recordings']
    out['recordings_with_a_jump_over_90_deg'] = {
        'old': sorted(k for k, v in rows.items() if any(c['changes_over_90_deg'] for c in v['old'].values())),
        'new': sorted(k for k, v in rows.items() if any(c['changes_over_90_deg'] for c in v['new'].values()))}
    out['largest_one_sample_change_deg'] = {'old': max(c['max_one_sample_change_deg'] for v in rows.values() for c in v['old'].values()),
                                            'new': max(c['max_one_sample_change_deg'] for v in rows.values() for c in v['new'].values())}
    out['samples_abs_over_90_deg_total'] = {k: sum(c['samples_abs_over_90_deg'] for v in rows.values() for c in v[k].values()) for k in ('old', 'new')}
    out['focus'] = {f'{s}/{rec}/{col}': {'old': rows[f'{s}/{rec}']['old'][col], 'new': rows[f'{s}/{rec}']['new'][col]} for s, (rec, col) in WINDOW.items()}
    out['offsets_vs_publisher_deg'] = {}
    for key, v in new_summary['per_subject_leg'].items():
        o = old_summary['per_subject_leg'][key]
        out['offsets_vs_publisher_deg'][key] = {j: {'old': None if o[j]['offset_deg'] is None else round(o[j]['offset_deg']['median'], 2),
                                                    'new': None if v[j]['offset_deg'] is None else round(v[j]['offset_deg']['median'], 2),
                                                    'old_walking': None if o[j]['offset_deg_walking_tasks'] is None else round(o[j]['offset_deg_walking_tasks']['median'], 2),
                                                    'new_walking': None if v[j]['offset_deg_walking_tasks'] is None else round(v[j]['offset_deg_walking_tasks']['median'], 2)}
                                                for j in ('hip', 'knee', 'ankle')}
    out['held_columns'] = {'old': old_summary['held_columns'], 'new': new_summary['held_columns']}
    out['composition_max_abs_err_rad'] = new_summary['composition_max_abs_err_rad']
    out['second_implementation_max_abs_diff'] = new_summary['second_implementation_max_abs_diff']
    out['peak_rss_mib'] = round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)
    (out_root / 'report.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    (out_root / 'run_summary.json').write_text(json.dumps({'status': 'report_done_unreviewed', 'recordings': len(rows), 'peak_rss_mib': out['peak_rss_mib']}, indent=1) + '\n')
    return 0


def make_spec(args):
    sys.path.insert(0, str(ROOT))
    from contributor_tools import guarded_launcher as gl
    code = ('contributor_tools/report_gt23_planes.py', 'contributor_tools/guarded_launcher.py')
    command = ['python3', 'contributor_tools/report_gt23_planes.py', 'run', '--output-root', args.output_root,
               '--old-summary', args.old_summary, '--new-summary', args.new_summary]
    bindings = {c: gl.sha256_file(ROOT / c) for c in code}
    bindings[args.old_summary] = gl.sha256_file(ROOT / args.old_summary)
    bindings[args.new_summary] = gl.sha256_file(ROOT / args.new_summary)
    for s in SUBJECTS:
        bindings[f'{NEW.format(s)}/ledger.jsonl'] = gl.sha256_file(ROOT / NEW.format(s) / 'ledger.jsonl')
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root, 'receipt_path': args.receipt,
            'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816}, 'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['report.json', 'run_summary.json'], 'address_space_mib': 768}
    with Path(args.spec_out).open('x') as stream:
        json.dump(spec, stream, indent=2)
        stream.write('\n')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'spec'):
        s = sub.add_parser(name)
        s.add_argument('--output-root', required=True)
        s.add_argument('--old-summary', required=True)
        s.add_argument('--new-summary', required=True)
        if name == 'spec':
            s.add_argument('--job-id', required=True)
            s.add_argument('--receipt', required=True)
            s.add_argument('--spec-out', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
