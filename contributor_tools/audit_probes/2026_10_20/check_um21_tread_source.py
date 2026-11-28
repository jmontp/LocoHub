"""Independent all-recording UM21 treadmill source and event readback.

Reads a single cycle at a time. No converter code is imported. This checks
the partial sagittal staging export, not unexported signals or source validity.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource

resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import h5py
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.interpolate import interp1d
pa.set_cpu_count(1)
pa.set_io_thread_count(1)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary_path = args.batch / 'conversion_summary.json'
    summary = json.loads(summary_path.read_text())
    source = Path(summary['source']['path'])
    assert digest(source) == summary['source']['sha256']
    report = {'status': 'running', 'scientific_approval': False,
              'source_sha256': summary['source']['sha256'], 'summary_sha256': digest(summary_path),
              'probe_sha256': digest(Path(__file__)), 'records': [],
              'limitations': ['Checks the partial sagittal export only; forces, kinetics and other components remain unexported',
                              'Checks declared 100 Hz sampling, not physical calibration or source event correctness',
                              'Ankle canonical mapping and joint-derived segment orientations remain unverified']}
    target = args.output / 'source_comparison.json'
    def save():
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        temp.replace(target)
    save()
    try:
        with h5py.File(source, 'r', rdcc_nbytes=1024**2) as handle:
            available = {(s, c) for s in handle['Streaming'] if 'Tread' in handle[f'Streaming/{s}']
                         for c in handle[f'Streaming/{s}/Tread'] if c in ('d10', 'd5', 'i0', 'i5', 'i10')}
            assert {(r['subject'], r['condition']) for r in summary['recordings']} == available
            for record in summary['recordings']:
                folder = args.batch / record['subject'] / record['condition']
                parquet = folder / 'phase.parquet'
                assert digest(parquet) == record['sha256']
                trial = handle[f"Streaming/{record['subject']}/Tread/{record['condition']}"]
                events = trial['events']
                expected_pairs = {(side, int(a), int(b)) for side, name in [('left', 'LHS'), ('right', 'RHS')]
                                  for a, b in zip(events[name][...].reshape(-1)[:-1], events[name][...].reshape(-1)[1:])}
                ledger_path = folder / 'candidate_ledger.jsonl'
                ledger = [json.loads(line) for line in ledger_path.read_text().splitlines()]
                keys = [(x['side'], x['start'], x['end']) for x in ledger]
                assert len(keys) == len(set(keys)) and set(keys) == expected_pairs
                accepted = {x['observation_id']: x for x in ledger if x.get('status') == 'written_unreviewed'}
                cuts = events['cutPoints'][...].T
                labels = [''.join(chr(int(c)) for c in handle[ref][...].reshape(-1))
                          for ref in events['tasks'][...].reshape(-1)]
                for item in ledger:
                    matches = [i for i, (a, b) in enumerate(cuts) if a <= item['start'] and item['end'] <= b]
                    if 'excluded' in item:
                        assert len(matches) != 1 or not (labels[matches[0]].startswith('s') or labels[matches[0]] in ('a0x2','a0x5','d0x2','d0x5'))
                    else:
                        assert len(matches) == 1 and item['label'] == labels[matches[0]]
                seen = set()
                maximum_error = 0.
                finite_values = 0
                for batch in pq.ParquetFile(parquet).iter_batches(batch_size=150, use_threads=False):
                    frame = batch.to_pandas(use_threads=False)
                    assert len(frame) == 150 and frame.observation_id.nunique() == 1
                    identity = frame.observation_id.iloc[0]
                    assert identity not in seen
                    seen.add(identity)
                    item = accepted[identity]
                    start, end = item['start'], item['end']
                    assert frame.reference_side.eq(item['side']).all()
                    assert frame.task_id.eq(item['label']).all()
                    np.testing.assert_allclose(frame.source_start_time_s, (start - 1) / 100, atol=1e-12, rtol=0)
                    np.testing.assert_allclose(frame.source_end_time_s, (end - 1) / 100, atol=1e-12, rtol=0)
                    clock = np.arange(end - start + 1) / 100
                    times = np.linspace(0, clock[-1], 150)
                    np.testing.assert_allclose(frame.time_s, times, atol=1e-12, rtol=0)
                    np.testing.assert_allclose(frame.phase_ipsi, np.linspace(0, 100, 150), atol=1e-12, rtol=0)
                    pairs = [('RPelvisAngles', 'pelvis_sagittal_angle_rad', False)]
                    for role, leg in [('ipsi', 'R' if item['side'] == 'right' else 'L'),
                                      ('contra', 'L' if item['side'] == 'right' else 'R')]:
                        pairs += [(leg + 'HipAngles', f'hip_flexion_angle_{role}_rad', True),
                                  (leg + 'KneeAngles', f'knee_flexion_angle_{role}_rad', True),
                                  (leg + 'AnkleAngles', f'source_ankle_sagittal_angle_{role}_rad', False)]
                        assert frame[f'ankle_dorsiflexion_angle_{role}_rad'].isna().all()
                    for source_name, column, velocity in pairs:
                        raw = trial['jointAngles'][source_name][0, start - 1:end]
                        expected = interp1d(clock, raw, kind='linear', bounds_error=True)(times) * np.pi / 180
                        comparisons = [(column, expected)]
                        if velocity:
                            derivative = np.gradient(expected, times)
                            derivative[~np.isfinite(expected)] = np.nan
                            comparisons.append((column.replace('_angle_', '_velocity_').replace('_rad', '_rad_s'), derivative))
                        for name, expected_values in comparisons:
                            actual = frame[name].to_numpy()
                            np.testing.assert_allclose(actual, expected_values, atol=1e-9, rtol=1e-9, equal_nan=True)
                            valid = np.isfinite(expected_values)
                            finite_values += int(valid.sum())
                            if valid.any():
                                maximum_error = max(maximum_error, float(np.max(abs(actual[valid] - expected_values[valid]))))
                assert seen == set(accepted)
                assert len(seen) == record['observations']
                report['records'].append({'subject': record['subject'], 'condition': record['condition'],
                    'observations': len(seen), 'source_pairs': len(expected_pairs), 'excluded_pairs': len(ledger) - len(seen),
                    'finite_values_checked': finite_values, 'maximum_error': maximum_error,
                    'output_sha256': record['sha256'], 'ledger_sha256': digest(ledger_path)})
                save()
        report['status'] = 'all_tread_sagittal_exports_checked_unreviewed'
    except Exception as error:
        report.update(status='failed', reason=str(error))
        raise
    finally:
        save()
    print(json.dumps({'status': report['status'], 'recordings': len(report['records']),
                      'observations': sum(r['observations'] for r in report['records'])}))


if __name__ == '__main__':
    main()
