"""Independent full native-companion readback, including raw header clock."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
import hashlib
import json
from pathlib import Path
import resource
import struct

resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import ezc3d
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
pa.set_cpu_count(1)
pa.set_io_thread_count(1)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    metadata = json.loads((args.output_root / 'source_metadata.json').read_text())
    source = args.source_root / metadata['source_recording']
    assert source.stat().st_size <= 64 * 1024**2
    assert digest(source) == metadata['source_sha256']
    parquet = args.output_root / 'source_time.parquet'
    assert digest(parquet) == metadata['output_sha256']
    c = ezc3d.c3d(str(source))
    with source.open('rb') as stream:
        header = stream.read(512)
        stream.seek((header[0] - 1) * 512)
        parameter_header = stream.read(4)
    assert parameter_header[3] == 84, 'Raw-header probe supports Intel C3D only'
    first, last = struct.unpack('<HH', header[6:10])
    rate = struct.unpack('<f', header[20:24])[0]
    table = pq.ParquetFile(parquet).read(use_threads=False)
    np.testing.assert_array_equal(table['source_frame'].to_numpy(), np.arange(first, last + 1))
    np.testing.assert_allclose(table['time_s'].to_numpy(), np.arange(first, last + 1) / rate, rtol=0, atol=1e-12)
    labels = c['parameters']['POINT']['LABELS']['value']
    checked = 0
    expected_columns = {'source_frame', 'time_s'}
    for category in ['ANGLES', 'FORCES', 'MOMENTS', 'POWERS']:
        for label in c['parameters']['POINT'].get(category, {}).get('value', []):
            index = labels.index(label)
            for component, suffix in enumerate(['component_1', 'component_2', 'component_3', 'residual']):
                name = f'{label}__{suffix}'
                expected_columns.add(name)
                actual = table[name].to_numpy()
                expected = c['data']['points'][component, index]
                np.testing.assert_array_equal(actual, expected)
                checked += len(actual)
    assert set(table.column_names) == expected_columns
    expected_events = {key: np.asarray(entry['value']).tolist()
                       for key, entry in c['parameters'].get('EVENT', {}).items()
                       if key != '__METADATA__'}
    assert metadata['source_events'] == expected_events
    report = {'status': 'exact_source_companion_readback', 'rows': table.num_rows,
        'components_and_residuals_checked': checked, 'source_sha256': digest(source),
        'output_sha256': digest(parquet), 'probe_sha256': digest(Path(__file__)),
        'scientific_approval': False,
        'limitations': ['Same C3D decoding library; raw binary clock checked separately',
                        'No anatomical, segmentation or canonical unit approval']}
    (args.output_root / 'source_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
