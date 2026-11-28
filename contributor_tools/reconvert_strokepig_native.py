"""Preserve one StrokePiG native model-output recording in a source companion.

This continuous table retains original component order, residuals and values.
It is not interchangeable with OpenSim IK or an approved standard phase file.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource

import ezc3d
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
pa.set_cpu_count(1)
pa.set_io_thread_count(1)

VICON_REFERENCE = 'https://help.vicon.com/download/attachments/11611993/Plug-in%20Gait%20Reference%20Guide.pdf'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def export(source_root, relative_recording, output_root):
    relative = Path(relative_recording)
    source = (source_root / relative).resolve()
    if relative.is_absolute() or not source.is_relative_to(source_root.resolve()):
        raise ValueError('Recording must be within source root')
    if source.suffix.lower() != '.c3d' or source.stat().st_size > 64 * 1024**2:
        raise ValueError('Expected a C3D file no larger than 64 MiB')
    source_hash = digest(source)
    c3d = ezc3d.c3d(str(source))
    params = c3d['parameters']
    point_params = params['POINT']
    labels = list(point_params['LABELS']['value'])
    points = c3d['data']['points']
    if len(set(labels)) != len(labels) or len(labels) != points.shape[1]:
        raise ValueError('Ambiguous point labels')
    header = c3d['header']['points']
    rate = float(header['frame_rate'])
    first = int(header['first_frame']) + 1
    frames = np.arange(first, first + points.shape[2], dtype=np.int64)
    if not np.isfinite(rate) or rate <= 0 or frames[-1] != header['last_frame'] + 1:
        raise ValueError('Invalid source frame clock')
    recording_id = 'strokepig:native:' + relative.as_posix()
    columns = {'source_frame': pa.array(frames), 'time_s': pa.array(frames / rate)}
    channel_metadata = []
    for group, unit in [('ANGLES', 'ANGLE_UNITS'), ('FORCES', 'FORCE_UNITS'),
                        ('MOMENTS', 'MOMENT_UNITS'), ('POWERS', 'POWER_UNITS')]:
        for label in point_params.get(group, {}).get('value', []):
            if label not in labels:
                raise ValueError(f'Declared model output missing: {label}')
            index = labels.index(label)
            names = [f'{label}__component_{axis}' for axis in (1, 2, 3)] + [f'{label}__residual']
            for component, name in enumerate(names):
                if name in columns:
                    raise ValueError(f'Duplicate source column: {name}')
                columns[name] = pa.array(points[component, index, :])
            channel_metadata.append({'source_label': label, 'source_group': group,
                'columns': names, 'c3d_declared_group_units': list(point_params.get(unit, {}).get('value', []))})
    if not channel_metadata:
        raise ValueError('No native model outputs')
    event_params = params.get('EVENT', {})
    # Keep complete parameter values rather than silently dropping unusual events.
    events = {key: np.asarray(entry['value']).tolist() for key, entry in event_params.items()
              if key != '__METADATA__'}
    processing_mass = np.asarray(params.get('PROCESSING', {}).get('Bodymass', {}).get('value', [])).tolist()
    metadata = {'source_recording_id': recording_id, 'source_recording': relative.as_posix(),
        'source_sha256': source_hash, 'converter_sha256': digest(Path(__file__)),
        'observation_kind': 'continuous_recording', 'subject': relative.parent.name,
        'affected_side': 'unknown', 'source_frame_rate_hz': rate, 'rows': len(frames),
        'channels': channel_metadata, 'source_events': events,
        'source_processing_bodymass': processing_mass, 'scientific_approval': False,
        'limitations': ['Original component order and values; no anatomical sign or axis mapping applied',
            'Residuals retained; invalid samples are not silently filled or removed',
            'Plug-in Gait joint kinetics are mass-normalized despite C3D group labels omitting /kg; normalized GRF has a separate convention',
            'No phase segmentation, clinical laterality assignment, force-plate export or canonical release approval'],
        'unit_reference': VICON_REFERENCE}
    if digest(source) != source_hash:
        raise ValueError('Source changed during export')
    output_root.mkdir(parents=True, exist_ok=False)
    table = pa.table(columns).replace_schema_metadata({b'locohub_source': json.dumps(metadata, allow_nan=False).encode()})
    parquet = output_root / 'source_time.parquet'
    pq.write_table(table, parquet, compression='zstd', row_group_size=1024)
    metadata['output_sha256'] = digest(parquet)
    (output_root / 'source_metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False) + '\n')
    return metadata


def main():
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--recording', required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    report = export(args.source_root, args.recording, args.output_root)
    print(json.dumps({'rows': report['rows'], 'channels': len(report['channels']),
                      'scientific_approval': report['scientific_approval']}))


if __name__ == '__main__':
    main()
