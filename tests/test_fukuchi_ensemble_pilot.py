"""Synthetic ensemble semantics; never evidence of real-data regeneration."""
import importlib.util
from pathlib import Path
import math
import pytest

PATH = Path(__file__).resolve().parents[1]/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/convert_ensemble_pilot.py'
SPEC = importlib.util.spec_from_file_location('fukuchi_ensemble', PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_separate_ensembles_preserve_side_without_invented_timing():
    angles = {'Time': list(range(101)), 'RHipAngleZ': [10.]*101, 'LHipAngleZ': [20.]*101}
    moments = {'Time': list(range(101)), 'RKneeMomentZ': [2.]*101, 'LKneeMomentZ': [3.]*101}
    rows = MODULE.build_rows(angles, moments, 'WBDS01walkOC')
    assert len(rows) == 300
    right, left = rows[:150], rows[150:]
    assert right[0]['observation_id'] != left[0]['observation_id']
    assert right[0]['hip_flexion_angle_ipsi_rad'] == pytest.approx(math.pi/18)
    assert right[0]['knee_flexion_moment_ipsi_Nm_kg'] == -2
    assert 'hip_flexion_angle_ipsi_rad' not in left[0]
    assert left[0]['source_LHipAngleZ_deg'] == 20
    for row in rows:
        assert row['observation_type'] == 'ensemble_curve'
        assert math.isnan(row['source_start_time_s']) and math.isnan(row['source_end_time_s'])
        assert 'phase_contra' not in row and 'time_s' not in row


def test_linear_interpolation_known_values_and_missing_gap():
    values = list(range(101))
    assert MODULE.interpolate(values, [0., .5, 100.]) == [0., .5, 100.]
    values[1] = float('nan')
    result = MODULE.interpolate(values, [0., .5, 1., 1.5, 2.])
    assert result[0] == 0 and result[-1] == 2
    assert all(math.isnan(v) for v in result[1:-1])


def test_unreviewed_recording_type_rejected():
    with pytest.raises(ValueError, match='overground'):
        MODULE.build_rows({}, {}, 'WBDS01walkT01')


def test_elapsed_time_cannot_masquerade_as_ensemble_phase(tmp_path):
    source = tmp_path/'curve.txt'
    source.write_text('Time\tRHipAngleZ\n'+'\n'.join(f'{i/100}\t10' for i in range(101)))
    with pytest.raises(ValueError, match='normalized grid'):
        MODULE.read_curve(source)

CHECK_SPEC = importlib.util.spec_from_file_location('fukuchi_check', PATH.with_name('check_ensemble_pilot.py'))
CHECK = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECK)


@pytest.fixture
def synthetic_readback():
    import pandas as pd
    # Intentionally sparse source headers: absence is not an invented measurement.
    angles = {'Time': list(range(101)), 'RHipAngleZ': [10.]*101, 'LHipAngleZ': [20.]*101}
    moments = {'Time': list(range(101)), 'RKneeMomentZ': [2.]*101, 'LKneeMomentZ': [3.]*101}
    frame = pd.DataFrame(MODULE.build_rows(angles, moments, 'WBDS01walkOC'))
    source = {name: values for table in (angles, moments) for name, values in table.items() if name != 'Time'}
    return frame, source, ['WBDS01walkOCang.txt', 'WBDS01walkOCknt.txt']


def test_readback_accepts_explicit_synthetic_ensemble(synthetic_readback):
    checked, error = CHECK.validate_frame(*synthetic_readback)
    assert checked == 600 and error == 0


@pytest.mark.parametrize('column,value', [
    ('subject', 'FU18_02'), ('task', 'running'), ('task_id', 'overground_F'),
    ('source_recording_id', 'wrong'), ('observation_id', 'wrong'), ('reference_side', 'left')])
def test_readback_rejects_identity_corruption(synthetic_readback, column, value):
    frame, sources, paths = synthetic_readback
    frame.loc[73, column] = value
    with pytest.raises(AssertionError):
        CHECK.validate_frame(frame, sources, paths)


def test_readback_checks_metadata_after_first_row(synthetic_readback):
    import json
    frame, sources, paths = synthetic_readback
    info = json.loads(frame.loc[149, 'task_info'])
    info['speed_m_s'] = 1.27
    frame.loc[149, 'task_info'] = json.dumps(info)
    with pytest.raises(AssertionError, match='task_info'):
        CHECK.validate_frame(frame, sources, paths)


@pytest.mark.parametrize('column', ['cycle_count', 'hip_flexion_angle_ipsi_sd_rad', 'time_s', 'invented_signal'])
def test_readback_rejects_extra_columns(synthetic_readback, column):
    frame, sources, paths = synthetic_readback
    frame[column] = 0
    with pytest.raises(AssertionError):
        CHECK.validate_frame(frame, sources, paths)


@pytest.mark.parametrize('row,column', [(25, 'source_LHipAngleZ_deg'), (200, 'hip_flexion_angle_ipsi_rad')])
def test_readback_rejects_opposite_side_contamination(synthetic_readback, row, column):
    frame, sources, paths = synthetic_readback
    frame.loc[row, column] = 9
    with pytest.raises(AssertionError):
        CHECK.validate_frame(frame, sources, paths)


def test_readback_rejects_missing_source_channel(synthetic_readback):
    frame, sources, paths = synthetic_readback
    with pytest.raises(AssertionError, match='columns'):
        CHECK.validate_frame(frame.drop(columns=['source_LHipAngleZ_deg']), sources, paths)


def test_readback_rejects_source_condition_mismatch():
    with pytest.raises(AssertionError, match='condition mismatch'):
        CHECK.source_identity(['WBDS01walkOCang.txt', 'WBDS02walkOCknt.txt'])


@pytest.mark.parametrize('filename', ['conversion_manifest.json', 'source.txt', 'ensemble.parquet'])
def test_readback_binding_detects_change_after_initial_check(tmp_path, filename):
    path = tmp_path/filename
    path.write_bytes(b'original fixture')
    bindings = {path: CHECK.digest(path)}
    CHECK.verify_bindings(bindings)
    path.write_bytes(b'changed fixture')
    with pytest.raises(AssertionError, match='input changed'):
        CHECK.verify_bindings(bindings)
