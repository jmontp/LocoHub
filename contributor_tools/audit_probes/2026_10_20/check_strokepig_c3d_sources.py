"""Inventory native StrokePiG signals and events, one bounded C3D at a time.

Source unit labels are recorded verbatim, not accepted as canonical units.
This is a read-only source census, not scientific approval or a conversion.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import resource

resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import ezc3d
import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def value(c3d, group, name, default=()):
    return c3d['parameters'].get(group, {}).get(name, {}).get('value', default)


def inspect(path):
    if path.stat().st_size > 64 * 1024**2:
        return {'status': 'deferred_input_limit', 'bytes': path.stat().st_size}
    before = sha256(path)
    c = ezc3d.c3d(str(path))
    labels = list(value(c, 'POINT', 'LABELS'))
    points = c['data']['points']
    header = c['header']['points']
    rate = float(header['frame_rate'])
    assert rate > 0 and np.isfinite(rate)
    assert len(set(labels)) == len(labels) == points.shape[1]
    assert header['last_frame'] - header['first_frame'] + 1 == points.shape[2]
    # ezc3d's header frame is zero based; EVENT times use source frame/rate.
    start = (header['first_frame'] + 1) / rate
    end = (header['last_frame'] + 1) / rate
    signals = {}
    for category, unit_key in [('ANGLES', 'ANGLE_UNITS'), ('FORCES', 'FORCE_UNITS'),
                                ('MOMENTS', 'MOMENT_UNITS'), ('POWERS', 'POWER_UNITS')]:
        members = list(value(c, 'POINT', category))
        channels = []
        for name in members:
            if name not in labels:
                channels.append({'label': name, 'present': False})
                continue
            i = labels.index(name)
            a = points[:3, i, :]
            finite = np.isfinite(a)
            channels.append({'label': name, 'present': True,
                'finite_components': int(finite.sum()), 'components': int(a.size),
                'nonzero_components': int(np.count_nonzero(a[finite])),
                'negative_residual_frames': int((points[3, i, :] < 0).sum())})
        signals[category] = {'declared_units': list(value(c, 'POINT', unit_key)),
                             'channels': channels}
    times = np.asarray(value(c, 'EVENT', 'TIMES'), dtype=float)
    event_labels = list(value(c, 'EVENT', 'LABELS'))
    contexts = list(value(c, 'EVENT', 'CONTEXTS'))
    used = int(value(c, 'EVENT', 'USED', [0])[0])
    assert len(event_labels) == len(contexts) == used
    assert not used or times.shape == (2, used)
    events = []
    for i, (label, side) in enumerate(zip(event_labels, contexts)):
        t = float(times[0, i] * 60 + times[1, i])
        assert np.isfinite(t)
        events.append({'label': label, 'side': side, 'time_s': t,
                       'inside_point_clock': start - 1e-5 <= t <= end + 1e-5})
    masses = [float(x) for x in value(c, 'PROCESSING', 'Bodymass')]
    assert all(np.isfinite(x) for x in masses)
    assert before == sha256(path), 'Source changed while reading'
    return {'status': 'inventoried', 'sha256': before, 'point_frames': points.shape[2],
            'rate_hz': rate, 'start_s': start, 'end_s': end, 'signals': signals,
            'events': events, 'processing_bodymass': masses,
            'marker_sets': list(value(c, 'SUBJECTS', 'MARKER_SETS'))}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory', type=Path, required=True)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output-root', type=Path, required=True)
    args = p.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=False)
    inventory = json.loads(args.inventory.read_text())
    subjects = {s['subject']: s for s in inventory['subject_metadata']}
    records = []
    report = {'status': 'running', 'scientific_approval': False,
              'inventory_sha256': sha256(args.inventory), 'probe_sha256': sha256(Path(__file__)),
              'records': records,
              'limitations': ['No anatomical axis, sign or normalization convention approved',
                              'Declared group units may not describe normalized channels',
                              'No event correctness or clinical laterality inferred']}
    target = args.output_root / 'source_census.json'
    for source in inventory['c3d_sources']:
        if source['kind'] != 'walking':
            continue
        record = {'source_recording': source['source_recording'], 'subject': source['subject']}
        try:
            record.update(inspect(args.source_root / source['source_recording']))
        except Exception as error:
            record.update(status='inspection_failed', error=f'{type(error).__name__}: {error}')
        selected = subjects[source['subject']]['selected_mass_kg']
        record['selected_metadata_mass_kg'] = selected
        masses = record.get('processing_bodymass', [])
        record['processing_mass_comparison'] = (
            'missing' if len(masses) != 1 or selected is None else
            'matches' if abs(masses[0] - selected) <= 1e-4 else 'disagrees')
        records.append(record)
        temp = target.with_suffix('.tmp')
        temp.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        temp.replace(target)
        gc.collect()
    report['status'] = 'source_census_complete_unreviewed'
    report['counts'] = dict(Counter(r['status'] for r in records))
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'recordings': len(records), 'counts': report['counts'],
                     'mass_mismatches': [r['source_recording'] for r in records
                                         if r['processing_mass_comparison'] == 'disagrees'],
                     'missing_processing_mass': [r['source_recording'] for r in records
                                                 if r['processing_mass_comparison'] == 'missing']}))


if __name__ == '__main__':
    main()
