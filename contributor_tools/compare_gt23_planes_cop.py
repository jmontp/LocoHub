"""GT23-PL01 check: the foot-frame pressure-point rerun may change ONLY the cop_anterior/cop_vertical/cop_lateral columns.

Compares every column of every recording between two roots (same recording names), bit for bit (float64 view, NaN equals
NaN). Reads 4096-row batches, one recording at a time. Writes one JSON.
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
COP = ('cop_anterior_', 'cop_vertical_', 'cop_lateral_')


def compare_recording(a_path, b_path):
    fa, fb = pq.ParquetFile(str(a_path), buffer_size=0), pq.ParquetFile(str(b_path), buffer_size=0)
    names = list(fa.schema_arrow.names)
    if names != list(fb.schema_arrow.names) or fa.metadata.num_rows != fb.metadata.num_rows:
        return {'schema_or_rows_differ': True}
    res = {c: {'samples_different': 0, 'max_abs_diff': 0.0} for c in names}
    for ba, bb in zip(fa.iter_batches(batch_size=4096, use_threads=False), fb.iter_batches(batch_size=4096, use_threads=False)):
        for i, c in enumerate(names):
            x = ba.column(i).to_numpy(zero_copy_only=False).astype(np.float64)
            y = bb.column(i).to_numpy(zero_copy_only=False).astype(np.float64)
            same = (x.view(np.int64) == y.view(np.int64)) | (np.isnan(x) & np.isnan(y))
            res[c]['samples_different'] += int((~same).sum())
            both = np.isfinite(x) & np.isfinite(y)
            if both.any():
                res[c]['max_abs_diff'] = max(res[c]['max_abs_diff'], float(np.abs(x[both] - y[both]).max()))
    return res


def run(args):
    out_root = ROOT / args.output_root
    out_root.mkdir(parents=True, exist_ok=False)
    changed_noncop, cop_changed_recs, rows, bad = [], 0, 0, []
    cop_diff_max = 0.0
    per = {}
    for s in SUBJECTS:
        for line in (ROOT / args.new_pattern.format(s) / 'ledger.jsonl').read_text().splitlines():
            rec = json.loads(line)['recording']
            r = compare_recording(ROOT / args.old_pattern.format(s) / f'{rec}.parquet', ROOT / args.new_pattern.format(s) / f'{rec}.parquet')
            if r.get('schema_or_rows_differ'):
                bad.append(f'{s}/{rec}')
                continue
            rows += 1
            nc = {c: v['samples_different'] for c, v in r.items() if not c.startswith(COP) and v['samples_different']}
            if nc:
                changed_noncop.append({'recording': f'{s}/{rec}', 'columns': nc})
            cop = {c: v for c, v in r.items() if c.startswith(COP)}
            if any(v['samples_different'] for v in cop.values()):
                cop_changed_recs += 1
            for v in cop.values():
                cop_diff_max = max(cop_diff_max, v['max_abs_diff'])
            per[f'{s}/{rec}'] = {'cop_samples_different': sum(v['samples_different'] for v in cop.values()), 'cop_max_abs_diff_m': max((v['max_abs_diff'] for v in cop.values()), default=0.0)}
    out = {'recordings_compared': rows, 'schema_or_row_mismatch': bad, 'recordings_with_any_non_cop_column_different': changed_noncop,
           'recordings_with_changed_cop': cop_changed_recs, 'cop_max_abs_diff_m': cop_diff_max, 'per_recording': per,
           'non_cop_bit_identical': not changed_noncop and not bad}
    out['peak_rss_mib'] = round(max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1024, 1)
    (out_root / 'comparison.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    (out_root / 'run_summary.json').write_text(json.dumps({'status': 'compare_done_unreviewed', 'non_cop_bit_identical': out['non_cop_bit_identical'], 'recordings': rows, 'peak_rss_mib': out['peak_rss_mib']}, indent=1) + '\n')
    return 0


def make_spec(args):
    sys.path.insert(0, str(ROOT))
    from contributor_tools import guarded_launcher as gl
    code = ('contributor_tools/compare_gt23_planes_cop.py', 'contributor_tools/guarded_launcher.py')
    command = ['python3', 'contributor_tools/compare_gt23_planes_cop.py', 'run', '--output-root', args.output_root,
               '--old-pattern', args.old_pattern, '--new-pattern', args.new_pattern]
    bindings = {c: gl.sha256_file(ROOT / c) for c in code}
    for s in SUBJECTS:
        bindings[f'{args.new_pattern.format(s)}/ledger.jsonl'] = gl.sha256_file(ROOT / args.new_pattern.format(s) / 'ledger.jsonl')
        bindings[f'{args.old_pattern.format(s)}/ledger.jsonl'] = gl.sha256_file(ROOT / args.old_pattern.format(s) / 'ledger.jsonl')
    spec = {'job_id': args.job_id, 'command': command, 'cwd': str(ROOT), 'output_root': args.output_root, 'receipt_path': args.receipt,
            'bindings': bindings, 'timeout_seconds': 3600, 'kill_after_seconds': 30, 'poll_seconds': 15,
            'startup_memory_mib': {'linux': 3584, 'windows': 2816}, 'runtime_memory_mib': {'linux': 2048, 'windows': 2048},
            'expected_output_names': ['comparison.json', 'run_summary.json'], 'address_space_mib': 768}
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
        s.add_argument('--old-pattern', required=True)
        s.add_argument('--new-pattern', required=True)
        if name == 'spec':
            s.add_argument('--job-id', required=True)
            s.add_argument('--receipt', required=True)
            s.add_argument('--spec-out', required=True)
    args = p.parse_args(argv)
    return {'run': run, 'spec': make_spec}[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
