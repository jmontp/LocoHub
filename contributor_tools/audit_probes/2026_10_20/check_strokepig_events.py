"""Bounded, independent source-event and IK comparison for TVC03/BWA6.

Checks the declared angle transforms; does not establish clinical side or forces.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import hashlib
import io
import json
from pathlib import Path
import struct

import ezc3d
import numpy as np
import pandas as pd

SOURCE = Path('/mnt/s/locomotion_data/50_StrokePiG/TVC03')
OUTPUT = Path('converted_datasets/reconversion_v2/strokepig_events_pilot_20261020')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    mot = SOURCE / 'BWA6_ik.mot'
    c3d_path = SOURCE / 'BWA6.c3d'
    body = mot.read_text().split('endheader', 1)[1].strip()
    raw = pd.read_csv(io.StringIO(body), sep=r'\s+')
    c3d = ezc3d.c3d(str(c3d_path))
    events = c3d['parameters']['EVENT']
    times = np.asarray(events['TIMES']['value'])
    strikes = sorted(times[0, i] * 60 + times[1, i]
                     for i, (label, side) in enumerate(zip(events['LABELS']['value'], events['CONTEXTS']['value']))
                     if label.strip().lower() == 'foot strike' and side.strip().lower() == 'left')
    with c3d_path.open('rb') as stream:
        header = stream.read(512)
    original_first_frame = struct.unpack('<H', header[6:8])[0]
    rate = c3d['header']['points']['frame_rate']
    assert abs(raw.time.iloc[0] - original_first_frame / rate) < 1e-8
    parquet = OUTPUT / 'strokepig/source/TVC03/BWA6_ik/phase.parquet'
    converted = pd.read_parquet(parquet)
    groups = list(converted.groupby('observation_id', sort=False))
    assert len(groups) == len(strikes) - 1 == 3
    errors = {}
    for (_, curve), start, end in zip(groups, strikes, strikes[1:]):
        assert len(curve) == 150
        assert abs(curve.source_start_time_s.iloc[0] - start) < 1e-4
        assert abs(curve.source_end_time_s.iloc[0] - end) < 1e-4
        assert set(curve.affected_side) == {'unknown'}
        info = json.loads(curve.task_info.iloc[0])
        assert info['phase_boundary_method'] == 'source_c3d_foot_strike_annotations'
        assert len(info['segmentation_candidates']) == 3
        a, b = int(curve.source_start_sample.iloc[0]), int(curve.source_end_sample.iloc[0])
        clock = raw.time.to_numpy()[a:b+1]
        target = np.linspace(clock[0], clock[-1], 150)
        for role, leg in [('ipsi', 'l'), ('contra', 'r')]:
            for src, dst in [('hip_flexion', 'hip_flexion'), ('knee_angle', 'knee_flexion'), ('ankle_angle', 'ankle_dorsiflexion')]:
                expected = np.interp(target, clock, raw[f'{src}_{leg}'].to_numpy()[a:b+1]) * np.pi / 180
                col = f'{dst}_angle_{role}_rad'
                np.testing.assert_allclose(curve[col], expected, atol=1e-10, rtol=1e-10)
                errors[col] = max(errors.get(col, 0), float(np.max(abs(curve[col] - expected))))
    report = {'observations_checked': len(groups), 'rows_checked': len(converted),
              'source_foot_strikes_s': strikes, 'max_absolute_errors': errors,
              'sha256': {str(p): digest(p) for p in [mot, c3d_path, parquet, Path(__file__)]},
              'limitations': ['Single recording only', 'Clinical side unknown', 'Force/COP and model sign conventions not independently verified']}
    (OUTPUT / 'source_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
