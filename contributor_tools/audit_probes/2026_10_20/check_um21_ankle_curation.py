"""Compare anomalous preserved treadmill ankle curves with original curation.

The 50-degree first-sample threshold only reproduces the legacy offset trigger.
It is not a physiological acceptance limit or a reason to rotate source values.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource

resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
import h5py
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
pa.set_cpu_count(1)
pa.set_io_thread_count(1)
ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat'
    base = ROOT / 'converted_datasets/reconversion_v2/um21_tread_corrected_20261020'
    records = []
    with h5py.File(source, 'r', rdcc_nbytes=1024**2) as handle:
        for subject, condition in [('AB07', 'i10'), ('AB08', 'i0')]:
            curated = {}
            for task, speed in handle[f'Normalized/{subject}/Walk'].items():
                if condition not in speed or not isinstance(speed[condition], h5py.Group):
                    continue
                block = speed[condition]
                details = block['events/StrideDetails'][...].T
                assert details.ndim == 2 and details.shape[1] == 4
                for i, (start, end, duration, leg) in enumerate(details):
                    assert start == int(start) and end == int(end) and end - start == duration
                    assert leg in (1, 2)
                    key = ('left' if leg == 1 else 'right', int(start), int(end))
                    assert key not in curated
                    ds = block['jointAngles/AnkleAngles']
                    values = ds[i, 0, :] if ds.ndim == 3 else ds[0, :]
                    assert len(values) == 150
                    curated[key] = {'task': task, 'first_ankle_deg': float(values[0]),
                                    'minimum_ankle_deg': float(np.min(values)), 'maximum_ankle_deg': float(np.max(values))}
            path = base / subject / condition / 'phase.parquet'
            entry = {'subject': subject, 'condition': condition, 'output_sha256': digest(path),
                     'curated_observations': len(curated), 'exported_observations': 0,
                     'exported_present_in_original_curation': 0, 'legacy_offset_trigger_cases': [],
                     'matched_ipsilateral_first_sample_max_error_deg': 0.}
            columns = ['observation_id', 'reference_side', 'source_start_time_s', 'source_end_time_s',
                       'source_ankle_sagittal_angle_ipsi_rad', 'source_ankle_sagittal_angle_contra_rad']
            for batch in pq.ParquetFile(path).iter_batches(batch_size=150, columns=columns, use_threads=False):
                frame = batch.to_pandas(use_threads=False)
                side = frame.reference_side.iloc[0]
                start = int(round(frame.source_start_time_s.iloc[0] * 100)) + 1
                end = int(round(frame.source_end_time_s.iloc[0] * 100)) + 1
                key = (side, start, end)
                entry['exported_observations'] += 1
                if key in curated:
                    entry['exported_present_in_original_curation'] += 1
                    first = float(frame.source_ankle_sagittal_angle_ipsi_rad.iloc[0] * 180 / np.pi)
                    entry['matched_ipsilateral_first_sample_max_error_deg'] = max(
                        entry['matched_ipsilateral_first_sample_max_error_deg'], abs(first - curated[key]['first_ankle_deg']))
                for role in ('ipsi', 'contra'):
                    values = frame[f'source_ankle_sagittal_angle_{role}_rad'].to_numpy() * 180 / np.pi
                    if np.isfinite(values[0]) and abs(values[0]) > 50:
                        entry['legacy_offset_trigger_cases'].append({'observation_id': frame.observation_id.iloc[0],
                            'reference_side': side, 'signal_side': side if role == 'ipsi' else 'right' if side == 'left' else 'left',
                            'role': role, 'start_frame': start, 'end_frame': end,
                            'first_deg': float(values[0]), 'minimum_deg': float(np.min(values)), 'maximum_deg': float(np.max(values)),
                            'reference_cycle_present_in_original_curation': key in curated,
                            'curated_reference_ankle': curated.get(key)})
            records.append(entry)
    report = {'scientific_approval': False, 'records': records,
        'source_normalized_sha256': digest(source), 'probe_sha256': digest(Path(__file__)),
        'source_readme_sha256': digest(ROOT / 'contributor_tools/conversion_scripts/Umich_2021/R01 Dataset README.pdf'),
        'vicon_angle_reference': 'https://help.vicon.com/download/attachments/11611993/Plug-in%20Gait%20Reference%20Guide.pdf#page=89',
        'limitations': ['Two source recordings selected after a full treadmill ankle-range scan',
            'Reference-cycle inclusion does not approve the contralateral signal in that window',
            'Original curation does not establish why a specific cycle was omitted',
            'Legacy 50-degree offset trigger is not a validation bound']}
    (args.output_root / 'curation_comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps([{k: v for k, v in r.items() if k != 'legacy_offset_trigger_cases'} |
                      {'offset_trigger_cases': len(r['legacy_offset_trigger_cases'])} for r in records]))


if __name__ == '__main__':
    main()
