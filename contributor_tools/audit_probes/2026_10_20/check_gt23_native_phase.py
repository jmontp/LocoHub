"""Check both curb conditions and anatomical routing against GT23 originals."""
import resource
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
from scipy.io import loadmat
pa.set_cpu_count(1); pa.set_io_thread_count(1)

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'converted_datasets/reconversion_v2/gt23_native_phase_pilot_20261020'
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parsing = SOURCE / 'Segmentation/AB01/curb_down_1_parsing.mat'
    events = loadmat(parsing)
    folder = SOURCE / 'RawData/AB01/CSV_Data/curb_down_1'
    angles = pd.read_csv(folder / 'Joint_Angle.csv')
    moments = pd.read_csv(folder / 'Joint_Moments.csv')
    frame = pd.read_parquet(BASE / 'phase.parquet')
    errors = {}; checked = []; expected = []
    for condition in ['left', 'right']:
        # Each source condition contains anatomically named left/right fields.
        # The earliest starting interval selects the reference in this source.
        reference = min(['left', 'right'], key=lambda side: events[f'{side}_{condition}'][0, 0])
        expected.extend((condition, reference, float(a), float(b)) for a, b in events[f'{reference}_{condition}'])
    for _, curve in frame.groupby('observation_id', sort=False):
        assert len(curve) == 150
        info = json.loads(curve.task_info.iloc[0])
        condition = info['source_condition']; reference = curve.reference_side.iloc[0]
        a = float(curve.source_start_time_s.iloc[0]); b = float(curve.source_end_time_s.iloc[0])
        checked.append((condition, reference, a, b))
        target = np.linspace(a, b, 150)
        np.testing.assert_allclose(curve.phase_ipsi, np.linspace(0, 100, 150), atol=1e-12)
        ref = reference[0]
        for role, leg in [('ipsi', ref), ('contra', 'r' if ref == 'l' else 'l')]:
            for raw, canonical, sign in [('hip_flexion', 'hip_flexion', 1), ('knee_angle', 'knee_flexion', -1), ('ankle_angle', 'ankle_dorsiflexion', 1)]:
                for table, source_col, col, scale in [
                    (angles, f'{raw}_{leg}', f'{canonical}_angle_{role}_rad', sign*np.pi/180),
                    (moments, f'{raw}_{leg}_moment', f'{canonical}_moment_{role}_Nm_kg', sign),
                ]:
                    selection = table[(table.time >= a) & (table.time <= b)]
                    values = np.interp(target, selection.time, selection[source_col]*scale, left=np.nan, right=np.nan)
                    np.testing.assert_allclose(curve[col], values, atol=1e-9, rtol=1e-9, equal_nan=True)
                    finite = np.isfinite(values)
                    errors[col] = max(errors.get(col, 0), float(np.max(abs(curve[col].to_numpy()[finite]-values[finite]))) if finite.any() else 0)
    assert sorted(checked) == sorted(expected)
    assert len(checked) == 10 and len(frame) == 1500
    report = {'observations': len(checked), 'rows': len(frame), 'source_intervals': checked,
              'max_errors': errors, 'parsing_sha256': digest(parsing),
              'output_sha256': digest(BASE/'phase.parquet'), 'probe_sha256': digest(Path(__file__)),
              'limitations': ['One curb recording only', 'Unit/sign/frame semantics need broader source verification',
                              'Other tasks, inferred transfer events and full reconstruction pending']}
    (BASE/'source_comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
