"""Add original joint components to verified UM21 treadmill staging files.

Preserves existing columns exactly, writes a new root, and independently checks
every added component after each recording. Anatomical mappings remain unapproved.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import json
from pathlib import Path
import resource
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
from contributor_tools.reconvert_umich_running import source_components


def readback(base_path, output_path, trial):
    """Independent interpolation plus exact preservation of all existing columns."""
    import numpy as np
    import pyarrow.parquet as pq
    from scipy.interpolate import interp1d
    from itertools import zip_longest
    finite_count = 0
    error = 0.
    count = 0
    base = pq.ParquetFile(base_path).iter_batches(batch_size=150, use_threads=False)
    output = pq.ParquetFile(output_path).iter_batches(batch_size=150, use_threads=False)
    for original_batch, new_batch in zip_longest(base, output):
        if original_batch is None or new_batch is None:
            raise ValueError('Recording row counts changed')
        original = original_batch.to_pandas(use_threads=False)
        new = new_batch.to_pandas(use_threads=False)
        if not original.equals(new[original.columns]):
            raise ValueError('An existing column changed')
        start = int(round(original.source_start_time_s.iloc[0] * 100))
        end = int(round(original.source_end_time_s.iloc[0] * 100))
        raw_clock = np.arange(start, end + 1, dtype=float)
        target = np.linspace(start, end, 150)
        expected_names = set()
        for group, kind, unit in [('jointAngles', 'joint_angle', 'deg'), ('jointForces', 'joint_force', 'N_kg'),
                                  ('jointMoments', 'joint_moment', 'Nm_kg'), ('jointPowers', 'joint_power', 'W_kg')]:
            if group not in trial:
                continue
            for name, dataset in trial[group].items():
                expected = interp1d(raw_clock, dataset[:, start:end + 1], axis=1, bounds_error=True)(target)
                for component, values in enumerate(expected):
                    column = f'source_{kind}_{name.lower()}_component_{component}_{unit}'
                    expected_names.add(column)
                    actual = new[column].to_numpy()
                    np.testing.assert_allclose(actual, values, atol=1e-9, rtol=1e-10, equal_nan=True)
                    finite = np.isfinite(values)
                    finite_count += int(finite.sum())
                    if finite.any():
                        error = max(error, float(np.max(abs(actual[finite] - values[finite]))))
        if set(new.columns) - set(original.columns) != expected_names:
            raise ValueError('Added columns do not match source component coverage')
        count += 1
    return {'observations_checked': count, 'finite_source_values_checked': finite_count,
            'maximum_error': error, 'existing_columns_exactly_preserved': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-root', type=Path, required=True)
    parser.add_argument('--base-readback', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--max-recordings', type=int)
    args = parser.parse_args()
    if args.max_recordings is not None and args.max_recordings < 1:
        parser.error('max-recordings must be positive')
    os.nice(max(0, 19 - os.nice(0)))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    import h5py
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    base_summary = args.base_root / 'conversion_summary.json'
    base = json.loads(base_summary.read_text())
    checked = json.loads(args.base_readback.read_text())
    if checked['status'] != 'all_tread_sagittal_exports_checked_unreviewed' or checked['summary_sha256'] != digest(base_summary):
        raise ValueError('Verified base summary required')
    verified = {(r['subject'], r['condition']): r for r in checked['records']}
    if set(verified) != {(r['subject'], r['condition']) for r in base['recordings']}:
        raise ValueError('Readback does not cover every base recording')
    source = Path(base['source']['path'])
    if digest(source) != base['source']['sha256'] or checked['source_sha256'] != base['source']['sha256']:
        raise ValueError('Source changed since base readback')
    source_stat = source.stat()
    ensure_storage_headroom(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=False)
    code_paths = [Path(__file__), ROOT / 'contributor_tools/reconvert_umich_running.py',
                  ROOT / 'contributor_tools/reconvert_umich_streaming.py', ROOT / 'contributor_tools/reconvert_recording.py']
    code = {str(p): digest(p) for p in code_paths}
    for p in code_paths:
        target = args.output_root / 'code' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    report = {'status': 'running', 'pid': os.getpid(), 'scientific_approval': False,
        'source_sha256': base['source']['sha256'], 'base_summary_sha256': digest(base_summary),
        'base_readback_sha256': digest(args.base_readback), 'code_sha256': code, 'planned_recordings': len(base['recordings']),
        'records': [], 'limitations': ['Original joint components only; forceplates and markers remain separate',
            'Canonical kinetic axes/signs and ankle convention remain unverified',
            'Preserves the existing accepted cycles and exclusion ledger; does not approve their segmentation policy']}
    def save():
        target = args.output_root / 'conversion_summary.json'
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(target)
    save()
    try:
        with h5py.File(source, 'r', rdcc_nbytes=1024**2) as handle:
            for record in base['recordings']:
                if (args.output_root / 'STOP_AFTER_CURRENT').exists():
                    report['status'] = 'stopped_by_request'
                    break
                if args.max_recordings and len(report['records']) >= args.max_recordings:
                    report['status'] = 'partial_requested_limit'
                    break
                ensure_storage_headroom(args.output_root)
                if shutil.disk_usage('/mnt/c').free < 1024**3:
                    raise OSError('C free space below 1 GiB')
                available = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))) * 1024
                if available < 2 * 1024**3:
                    raise MemoryError('Available memory below 2 GiB')
                if any(digest(Path(p)) != sha for p, sha in code.items()):
                    raise RuntimeError('Code changed during reconstruction')
                subject, condition = record['subject'], record['condition']
                original = args.base_root / record['path']
                if digest(original) != record['sha256']:
                    raise ValueError('Base output changed')
                ledger = original.parent / 'candidate_ledger.jsonl'
                ledger_hash = verified[(subject, condition)]['ledger_sha256']
                if digest(ledger) != ledger_hash:
                    raise ValueError('Base exclusion ledger changed since readback')
                trial = handle[f'Streaming/{subject}/Tread/{condition}']
                folder = args.output_root / subject / condition
                folder.mkdir(parents=True)
                output = folder / 'phase.parquet'
                writer = None
                mapping = None
                try:
                    for batch in pq.ParquetFile(original).iter_batches(batch_size=150, use_threads=False):
                        frame = batch.to_pandas(use_threads=False)
                        if len(frame) != 150 or frame.observation_id.nunique() != 1:
                            raise ValueError('Base observation boundaries changed')
                        start = int(round(frame.source_start_time_s.iloc[0] * 100)) + 1
                        end = int(round(frame.source_end_time_s.iloc[0] * 100)) + 1
                        values, current = source_components(trial, start, end)
                        if set(values) & set(frame.columns) or (mapping is not None and current != mapping):
                            raise ValueError('Conflicting source schema')
                        mapping = current
                        table = pa.Table.from_pandas(pd.concat([frame, pd.DataFrame(values)], axis=1), preserve_index=False)
                        if writer is None:
                            writer = pq.ParquetWriter(output.with_suffix('.partial'), table.schema, compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None:
                        writer.close()
                comparison = readback(original, output.with_suffix('.partial'), trial)
                if comparison['observations_checked'] != record['observations']:
                    raise ValueError('Observation count changed')
                output.with_suffix('.partial').replace(output)
                (folder / 'source_columns.json').write_text(json.dumps(mapping, indent=2) + '\n')
                shutil.copyfile(ledger, folder / 'candidate_ledger.jsonl')
                if digest(folder / 'candidate_ledger.jsonl') != ledger_hash:
                    raise ValueError('Exclusion ledger changed during copy')
                report['records'].append({'subject': subject, 'condition': condition, **comparison,
                    'source_columns': len(mapping), 'output_sha256': digest(output), 'base_output_sha256': record['sha256'],
                    'ledger_sha256': ledger_hash, 'source_columns_sha256': digest(folder / 'source_columns.json')})
                save()
        if report['status'] == 'running':
            report['status'] = 'all_tread_joint_components_readback_unreviewed'
        if (source.stat().st_size, source.stat().st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns):
            raise ValueError('Source changed during reconstruction')
        if any(digest(Path(p)) != sha for p, sha in code.items()):
            raise RuntimeError('Code changed during reconstruction')
    except Exception as error:
        report.update(status='failed', reason=str(error))
        raise
    finally:
        save()
    print(json.dumps({'status': report['status'], 'recordings': len(report['records'])}))


if __name__ == '__main__':
    main()
