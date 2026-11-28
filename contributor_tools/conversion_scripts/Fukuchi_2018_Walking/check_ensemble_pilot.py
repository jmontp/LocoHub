"""Independent small source readback for the Fukuchi ensemble pilot.

Schedule after conversion in the serial slot. Never validates raw gait cycles.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def source_identity(paths):
    names = [Path(path).name for path in paths]
    matches = [re.fullmatch(r'(WBDS(\d{2})walkO([SCF]))(ang|knt)\.txt', name) for name in names]
    assert len(matches) == 2 and all(matches), 'expected one angle and one kinetics source'
    assert {match.group(4) for match in matches} == {'ang', 'knt'}
    assert len({match.group(1) for match in matches}) == 1, 'source condition mismatch'
    return matches[0].group(2), matches[0].group(3), matches[0].group(1)


def verify_bindings(bindings):
    for path, expected in bindings.items():
        assert digest(path) == expected, 'Readback input changed: '+str(path)


def validate_frame(frame, sources, source_paths):
    """Independent synthetic-testable value and identity checks; no converter imports."""
    import numpy as np
    subject, condition, stem = source_identity(source_paths)
    source_id = 'fu18:v6:participant_condition_ensemble:'+stem
    expected_info = {
        'environment': 'overground', 'source_condition': condition,
        'speed_category': {'S': 'slow', 'C': 'comfortable', 'F': 'fast'}[condition],
        'source_grid_samples': 101, 'export_grid_samples': 150,
        'resampling': 'linear interpolation of source ensemble, not recovery of individual strides',
        'timing': 'normalized phase only; original cycle durations unavailable',
        'aggregation': 'source participant-condition mean; cycle membership/count/SD unavailable',
        'canonical_sign_scope': 'right sagittal angles/moments from author script labels; left stays source-only',
        'source_doi': '10.6084/m9.figshare.5722711.v6'}
    for column, expected in {'subject': 'FU18_'+subject, 'task': 'level_walking',
                             'task_id': 'overground_'+condition,
                             'source_recording_id': source_id}.items():
        assert frame[column].eq(expected).all(), column
    assert all(json.loads(value) == expected_info for value in frame.task_info), 'task_info'
    assert len(frame) == 300 and frame.observation_id.nunique() == 2
    assert frame.observation_type.eq('ensemble_curve').all() and frame.observation_kind.eq('ensemble').all()
    assert frame.source_start_time_s.isna().all() and frame.source_end_time_s.isna().all()
    assert not any(c in frame for c in ['time_s', 'phase_contra', 'cycle_duration_s', 'step_duration_s'])
    targets = np.linspace(0, 100, 150)
    checked = 0; max_error = 0.
    expected_canonical = {
        'RHipAngleZ': ('hip_flexion_angle_ipsi_rad', np.pi/180),
        'RKneeAngleZ': ('knee_flexion_angle_ipsi_rad', np.pi/180),
        'RAnkleAngleZ': ('ankle_dorsiflexion_angle_ipsi_rad', np.pi/180),
        'RHipMomentZ': ('hip_flexion_moment_ipsi_Nm_kg', 1.),
        'RKneeMomentZ': ('knee_flexion_moment_ipsi_Nm_kg', -1.),
        'RAnkleMomentZ': ('ankle_dorsiflexion_moment_ipsi_Nm_kg', -1.),
    }
    metadata_columns = {'subject', 'task', 'task_id', 'source_recording_id', 'observation_id',
                        'reference_side', 'observation_kind', 'observation_type', 'phase_ipsi',
                        'task_info', 'source_start_time_s', 'source_end_time_s'}
    assert sources and all(re.fullmatch(r'[RL](?:PelvisAngle|HipAngle|KneeAngle|AnkleAngle|FootAngle|HipMoment|KneeMoment|AnkleMoment|GRF)[XYZ]', name) for name in sources)
    source_columns = {'source_'+name+'_'+('deg' if 'Angle' in name else 'Nm_kg' if 'Moment' in name else 'N_kg') for name in sources}
    canonical_columns = {target for name, (target, _) in expected_canonical.items() if name in sources}
    assert frame.columns.is_unique and set(frame.columns) == metadata_columns | source_columns | canonical_columns, 'unexpected or missing columns'
    # np.interp differs from converter's explicit scalar interpolation.
    for side, prefix in [('right', 'R'), ('left', 'L')]:
        leg = frame[frame.reference_side == side]
        assert len(leg) == 150
        assert leg.observation_id.eq(source_id+':'+side).all(), 'observation_id'
        assert any(name.startswith(prefix) for name in sources)
        np.testing.assert_allclose(leg.phase_ipsi, targets, rtol=0, atol=1e-10)
        for name, values in sources.items():
            unit = 'deg' if 'Angle' in name else 'Nm_kg' if 'Moment' in name else 'N_kg'
            column = 'source_'+name+'_'+unit
            if not name.startswith(prefix):
                assert leg[column].isna().all()
                continue
            expected = np.interp(targets, np.arange(101), values)
            np.testing.assert_allclose(leg[column], expected, rtol=1e-12, atol=1e-10, equal_nan=True)
            finite = np.isfinite(expected)
            checked += int(finite.sum())
            if finite.any():
                max_error = max(max_error, float(np.max(abs(leg[column].to_numpy()[finite]-expected[finite]))))
            if name in expected_canonical:
                canonical, scale = expected_canonical[name]
                np.testing.assert_allclose(leg[canonical], expected*scale, rtol=1e-12, atol=1e-10, equal_nan=True)
        if side == 'left':
            assert all(leg[c].isna().all() for c in canonical_columns)
    return checked, max_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS'):
        os.environ[name] = '1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (768*1024**2, 768*1024**2))
    os.nice(max(0, 19-os.nice(0)))
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    manifest_path = args.output_root/'conversion_manifest.json'
    manifest_hash = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    bindings = {manifest_path: manifest_hash}
    verify_bindings(bindings)
    assert manifest['status'] == 'converted_ensemble_unreviewed'
    assert manifest['individual_cycles'] == 0
    assert manifest['rows'] == 300 and manifest['ensembles'] == 2
    assert manifest['scientific_approval'] is False
    source_identity(manifest['source_files'])
    output = args.output_root/'ensemble.parquet'
    assert output.stat().st_size <= 4*1024**2 and digest(output) == manifest['output_sha256']
    bindings[output] = manifest['output_sha256']
    bindings.update({Path(name): value for name, value in manifest['source_files'].items()})
    source_dirs = {Path(name).parent for name in manifest['source_files']}
    assert len(source_dirs) == 1
    bindings[next(iter(source_dirs))/'range_acquisition.json'] = manifest['acquisition_sha256']
    bindings[Path(__file__).with_name('convert_ensemble_pilot.py')] = manifest['converter_sha256']
    bindings[Path(__file__).parent/'source_evidence/wbdsExploratoryDA.m'] = manifest['sign_evidence_sha256']
    verify_bindings(bindings)
    sources = {}
    for name, expected_hash in manifest['source_files'].items():
        path = Path(name)
        assert path.stat().st_size <= 1024**2 and digest(path) == expected_hash
        source = pd.read_csv(path, sep='\t')
        assert len(source) == 101
        np.testing.assert_allclose(source.Time, np.arange(101), rtol=0, atol=1e-8)
        for column in source:
            if column != 'Time':
                assert column not in sources
                sources[column] = source[column].to_numpy()
    frame = pd.read_parquet(output)
    checked, max_error = validate_frame(frame, sources, manifest['source_files'])
    verify_bindings(bindings)
    report = {'status': 'ensemble_source_values_checked_unreviewed', 'scientific_approval': False,
              'manifest_sha256': manifest_hash, 'verified_input_sha256': {str(p): h for p, h in bindings.items()}, 'reviewer_sha256': digest(Path(__file__)),
              'ensembles': 2, 'individual_cycles': 0, 'finite_source_values_checked': checked,
              'max_abs_source_error': max_error,
              'limitations': ['Source ensemble interpolation only; no individual cycle reconstruction',
                             'No event, cycle duration, cycle count or standard deviation approval',
                             'Right sagittal sign mapping supported by author labels; left canonical channels missing']}
    verify_bindings(bindings)
    destination = args.output_root/'source_readback.json'
    with destination.open('x') as stream:
        json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
