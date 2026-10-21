"""Compare the native GT23 pilot to measured COP and original calcn transforms.

The transform CSVs are lossless native reads of source MATLAB table entries.
This verifies coordinate arithmetic/timing, not scientific frame conventions.
"""
import resource
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
pa.set_cpu_count(1); pa.set_io_thread_count(1)

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'converted_datasets/reconversion_v2/gt23_native_time_pilot_20261020'
SOURCE = Path('/mnt/s/locomotion_data/Gtech_2023/RawData/AB01/CSV_Data/ball_toss_1')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def main(base=BASE, source=SOURCE):
    BASE, SOURCE = base, source
    status = json.loads((BASE / 'native_status.json').read_text(encoding='utf-8-sig'))
    assert status['status'] == 'completed' and status['exit_code'] == 0
    output = pd.read_parquet(BASE / 'time.parquet')
    t0, t1 = output.source_start_time_s.iloc[0], output.source_end_time_s.iloc[0]
    angles = pd.read_csv(SOURCE / 'Joint_Angle.csv')
    target = angles.time.to_numpy()
    target = target[(target >= t0) & (target <= t1)]
    assert len(target) == len(output)
    np.testing.assert_allclose(output.time_s, target - target[0], atol=1e-12)
    forces = pd.read_csv(SOURCE / 'GroundFrame_GRFs.csv')
    forces = forces[(forces.time >= t0) & (forces.time <= t1)]
    mass = json.loads(output.subject_metadata.iloc[0])['weight_kg']
    errors = {}
    reference = output.reference_leg.unique()
    assert len(reference) == 1 and reference[0] in ('left', 'right')
    ipsi = 'l' if reference[0] == 'left' else 'r'
    for role, side in [('ipsi', ipsi), ('contra', 'r' if ipsi == 'l' else 'l')]:
        transforms = pd.read_csv(BASE / f'source_calcn_{side}.csv')
        times = transforms.time.to_numpy()
        gt = forces.time.to_numpy()
        nearest = np.searchsorted((times[:-1] + times[1:]) / 2, gt, side='right')
        rotation = np.stack([transforms[f'r{i}{j}'].to_numpy()[nearest]
                             for i in range(1, 4) for j in range(1, 4)], axis=1).reshape(-1, 3, 3)
        translation = transforms[['translation1', 'translation2', 'translation3']].to_numpy()[nearest]
        global_cop = forces[[f'{side.upper()}COPX', f'{side.upper()}COPY_Vertical', f'{side.upper()}COPZ']].to_numpy()
        local = np.einsum('nji,nj->ni', rotation, global_cop - translation)
        local[(gt < times[0]) | (gt > times[-1])] = np.nan
        expected = np.column_stack([np.interp(target, gt, local[:, i], left=np.nan, right=np.nan) for i in range(3)])
        vertical_force = np.interp(target, gt, forces[f'{side.upper()}ForceY_Vertical'], left=np.nan, right=np.nan) / (mass * 9.81)
        bad = ~(vertical_force >= .2) | (abs(expected[:, 0]) > .5) | (abs(expected[:, 2]) > .5)
        expected[bad] = np.nan
        for axis, i in [('anterior', 0), ('vertical', 1), ('lateral', 2)]:
            col = f'cop_{axis}_{role}_m'
            np.testing.assert_allclose(output[col], expected[:, i], atol=1e-8, rtol=1e-8, equal_nan=True)
            finite = np.isfinite(expected[:, i])
            errors[col] = {'finite_samples': int(finite.sum()),
                          'max_error': float(np.max(abs(output[col].to_numpy()[finite] - expected[finite, i]))) if finite.any() else None}
    assert any(v['finite_samples'] for v in errors.values()), 'No loaded COP samples checked'
    # Compare source joint values independently of the prepared CSV input view.
    # This proves routing/arithmetic, not the physical sign convention itself.
    for kind, filename, labels, scale in [
        ('angle', 'Joint_Angle.csv', ['hip_flexion', 'knee_angle', 'ankle_angle'], np.pi/180),
        ('velocity', 'Joint_Velocities.csv', ['hip_flexion_velocity', 'knee_velocity', 'ankle_velocity'], np.pi/180),
        ('moment', 'Joint_Moments.csv', ['hip_flexion', 'knee_angle', 'ankle_angle'], 1),
    ]:
        raw = pd.read_csv(SOURCE / filename)
        assert np.all(np.diff(raw.time) > 0)
        for role, side in [('ipsi', ipsi), ('contra', 'r' if ipsi == 'l' else 'l')]:
            for source_name, name, sign in zip(labels, ['hip_flexion', 'knee_flexion', 'ankle_dorsiflexion'], [1, -1, 1]):
                source_column = f'{source_name}_{side}' + ('_moment' if kind == 'moment' else '')
                unit = {'angle': 'rad', 'velocity': 'rad_s', 'moment': 'Nm_kg'}[kind]
                col = f'{name}_{kind}_{role}_{unit}'
                expected = np.interp(target, raw.time, raw[source_column]*sign*scale, left=np.nan, right=np.nan)
                np.testing.assert_allclose(output[col], expected, atol=1e-8, rtol=1e-8, equal_nan=True)
                finite = np.isfinite(expected)
                errors[col] = {'finite_samples': int(finite.sum()),
                    'max_error': float(np.max(abs(output[col].to_numpy()[finite]-expected[finite]))) if finite.any() else None}
    paths = [BASE / 'time.parquet', BASE / 'source_calcn_l.csv', BASE / 'source_calcn_r.csv', Path(__file__)]
    paths += [SOURCE / name for name in ['Joint_Angle.csv', 'Joint_Velocities.csv', 'Joint_Moments.csv', 'GroundFrame_GRFs.csv']]
    report = {'rows': len(output), 'checks': errors, 'sha256': {str(p): digest(p) for p in paths},
              'limitations': ['One continuous window only', 'Frame semantics/contact thresholds not independently validated',
                              'Full GT23 phase and time reconstruction pending']}
    (BASE / 'source_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--source', type=Path, default=SOURCE)
    args = parser.parse_args()
    main(args.base, args.source)
