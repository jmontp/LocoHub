"""Check every treadmill cycle's task metadata against native source speed CSV.

No numerical imports until check_record is called in the coordinated worker.
"""
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path

from contributor_tools.audit_gt21_adoption_ledger import digest, source_windows, unique


def rounded_region_speed(values):
    if not values or any(not math.isfinite(v) for v in values):
        raise ValueError('Finite source speed samples required')
    mean = math.fsum(values) / len(values)
    # MATLAB mean/sprintf and Python arithmetic may differ at a half-cent tie.
    if abs((mean * 100 - math.floor(mean * 100)) - .5) < 1e-8:
        raise ValueError('Speed rounding boundary requires native reconciliation')
    return float(format(mean, '.2f'))


def require_metadata(task, task_id, metadata, expected_speed):
    if task != 'level_walking' or task_id != 'level':
        raise ValueError('Wrong treadmill task classification')
    if (not isinstance(metadata, dict) or metadata.get('treadmill') is not True
            or metadata.get('surface') != 'treadmill'):
        raise ValueError('Wrong treadmill/surface metadata')
    speed = metadata.get('speed_m_s')
    if (isinstance(speed, bool) or not isinstance(speed, (int, float))
            or not math.isfinite(speed) or abs(speed - expected_speed) > 1e-12):
        raise ValueError('Treadmill speed does not match complete source-region mean')


def check_record(folder, ledger):
    import pyarrow.parquet as pq
    folder = Path(folder)
    manifest_path = folder / 'conversion_manifest.json'
    manifest_hash = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if (manifest['recording']['mode'] != 'treadmill'
            or ledger.get('status') != 'complete_eligible_pairs_checked_unreviewed'
            or ledger.get('manifest_sha256') != manifest_hash):
        raise ValueError('Complete matching treadmill ledger required')
    entry = unique(manifest['compressed_source_tables'],
                   lambda x: x['name'].startswith('source_conditions_'))
    name = entry['name']
    if Path(name).name != name:
        raise ValueError('Unsafe condition export path')
    path = folder / name
    bound = unique(manifest['outputs'], lambda x: x['name'] == name)['sha256']
    phase = folder / 'phase.parquet'
    phase_hash = unique(manifest['outputs'], lambda x: x['name'] == 'phase.parquet')['sha256']
    if digest(path) != bound or digest(phase) != phase_hash:
        raise ValueError('Candidate data changed')
    with gzip.open(path, 'rb') as stream:
        raw = stream.read(64 * 1024**2 + 1)
    if len(raw) > 64 * 1024**2:
        raise MemoryError('Condition CSV exceeds bounded admission')
    if hashlib.sha256(raw).hexdigest() != entry['uncompressed_sha256']:
        raise ValueError('Condition CSV changed')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('Missing/duplicate condition columns')
    clock, speeds = [], []
    for row in reader:
        if len(clock) >= 2_000_000:
            raise MemoryError('Condition row admission exceeded')
        clock.append(float(row['Header'])); speeds.append(float(row['Speed']))
    del raw, reader
    windows = source_windows(clock, speeds, 'treadmill')
    if windows != ledger['source_windows']:
        raise ValueError('Source windows differ from eligible-pair ledger')
    expected = [(w, rounded_region_speed([v for t, v in zip(clock, speeds)
                                         if w['start_s'] <= t <= w['end_s']])) for w in windows]
    seen = set()
    columns = ['observation_id', 'task', 'task_id', 'task_info',
               'source_start_time_s', 'source_end_time_s']
    for batch in pq.ParquetFile(phase).iter_batches(batch_size=150, columns=columns, use_threads=False):
        data = batch.to_pydict()
        if batch.num_rows != 150 or any(len(set(v)) != 1 for v in data.values()):
            raise ValueError('Mixed or partial cycle metadata')
        identity = data['observation_id'][0]
        if identity in seen:
            raise ValueError('Duplicate cycle')
        start, end = data['source_start_time_s'][0], data['source_end_time_s'][0]
        matches = [speed for w, speed in expected if w['start_s'] <= start < end <= w['end_s']]
        if len(matches) != 1:
            raise ValueError('Cycle does not belong to exactly one speed region')
        require_metadata(data['task'][0], data['task_id'][0],
                         json.loads(data['task_info'][0]), matches[0])
        seen.add(identity)
    if not seen or len(seen) != ledger['coverage']['exported_pairs']:
        raise ValueError('Not all ledger observations checked')
    if digest(manifest_path) != manifest_hash or digest(path) != bound or digest(phase) != phase_hash:
        raise ValueError('Evidence changed during metadata audit')
    return {'status': 'all_treadmill_metadata_source_checked_unreviewed',
            'scientific_approval': False, 'observations': len(seen),
            'source_windows': len(windows), 'manifest_sha256': manifest_hash,
            'condition_csv_sha256': bound, 'phase_sha256': phase_hash,
            'probe_sha256': digest(Path(__file__)),
            'limitations': ['Native condition CSV is hash-bound, not independently decoded from opaque MAT',
                            'Tolerance and rounding boundary cases require native reconciliation']}
