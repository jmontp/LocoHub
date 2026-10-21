#!/usr/bin/env python3
"""Preserve UM21 normalized transfer signals without inventing sides or timing.

This source-linked staging export retains the original signal names and units.
It is not an anatomically reconciled bilateral dataset or a release approval.
"""
import argparse
import json
from pathlib import Path
import os
import resource
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def transfer_frame(group, subject, source_task, index):
    import numpy as np
    import pandas as pd
    recording = f'um21:Normalized/{subject}/SitStand/ss/{source_task}'
    identity = f'{recording}:source_curve:{index + 1}'
    task = {'sit2stand': 'sit_to_stand', 'stand2sit': 'stand_to_sit'}[source_task]
    fields = dict(subject=f'UM21_{subject}', source_recording_id=recording,
                  observation_id=identity, step=identity, task=task, task_id=task,
                  observation_type='transfer', reference_side='unknown',
                  phase_ipsi=np.linspace(0, 100, 150), time_s=np.full(150, np.nan),
                  source_start_time_s=np.nan, source_end_time_s=np.nan,
                  task_info=json.dumps({'source_representation': 'unpaired_normalized_limb_curve',
                    'timing_status': 'no_verified_streaming_match',
                    'anatomical_reference_side': 'unknown',
                    'signal_conventions': 'original_source_names_and_plane_indices'}))
    # No interpolation: retain every stored normalized value, including NaNs.
    for family in ['jointAngles', 'forceplates']:
        if family not in group:
            continue
        for name, dataset in group[family].items():
            if dataset.ndim != 3 or dataset.shape[1:] != (3, 150):
                raise ValueError(f'Unexpected source dimensions: {dataset.name}')
            if index >= dataset.shape[0]:
                raise ValueError(f'Source curve count mismatch: {dataset.name}')
            for plane in range(3):
                fields[f'source_{family}_{name}_plane{plane + 1}'] = dataset[index, plane, :]
    return pd.DataFrame(fields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'contributor_tools/conversion_scripts/Umich_2021/Normalized.mat')
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    for key in ['OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS']:
        os.environ[key] = '1'
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    os.nice(max(0, 19-os.nice(0)))
    import h5py
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq
    from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    ensure_storage_headroom(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=False)
    (args.output_root/'converter_snapshot.py').write_bytes(Path(__file__).read_bytes())
    evidence = {'review_status': 'unreviewed', 'complete_dataset': False,
                'source': {'path': str(args.source.resolve()), 'sha256': digest(args.source)},
                'code_sha256': digest(Path(__file__)), 'recordings': [],
                'limitations': ['Anatomical side and streaming time correspondence unresolved.',
                  'Original units and axis/plane meanings retained, not canonicalized.',
                  'Marker arrays represent a different curve count and are not paired by array order.',
                  'No measured bilateral pairing or time derivatives are asserted.']}
    with h5py.File(args.source) as file:
        for subject, source_subject in file['Normalized'].items():
            if 'SitStand/ss' not in source_subject:
                continue
            for task, group in source_subject['SitStand/ss'].items():
                if task not in {'sit2stand', 'stand2sit'}:
                    raise ValueError(f'Unrecognized transfer source: {group.name}')
                ensure_storage_headroom(args.output_root)
                count = group['jointAngles/HipAngles'].shape[0]
                path = args.output_root/f'{subject}_{task}.parquet'
                writer = None
                try:
                    for index in range(count):
                        frame = transfer_frame(group, subject, task, index)
                        table = pa.Table.from_pandas(frame, preserve_index=False)
                        if writer is None: writer = pq.ParquetWriter(path, table.schema, compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None: writer.close()
                # Read every emitted source channel back and compare directly.
                output = pq.ParquetFile(path)
                for index in range(count):
                    frame = output.read_row_group(index, use_threads=False).to_pandas(use_threads=False)
                    assert frame.time_s.isna().all() and set(frame.reference_side) == {'unknown'}
                    for family in ['jointAngles', 'forceplates']:
                        if family not in group: continue
                        for name, dataset in group[family].items():
                            for plane in range(3):
                                np.testing.assert_array_equal(frame[f'source_{family}_{name}_plane{plane+1}'], dataset[index, plane, :])
                evidence['recordings'].append({'subject': subject, 'source_task': task,
                    'source_curves': count, 'rows': count*150, 'output': path.name,
                    'output_sha256': digest(path), 'all_source_channels_roundtrip_equal': True})
    (args.output_root/'conversion_manifest.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps({'recordings': len(evidence['recordings']),
                      'curves': sum(r['source_curves'] for r in evidence['recordings']),
                      'status': 'source_preserved_unreviewed'}))


if __name__ == '__main__': main()
