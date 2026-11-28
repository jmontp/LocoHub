"""Synthetic scalar metadata fixtures; no dataset or numerical imports."""
import pytest
from contributor_tools.audit_gt21_treadmill_metadata import require_metadata, rounded_region_speed


def test_mean_uses_complete_region_not_one_cycle_or_target():
    assert rounded_region_speed([1.01, 1.01, 1.02]) == 1.01
    require_metadata('level_walking', 'level',
                     {'speed_m_s': 1.01, 'treadmill': True, 'surface': 'treadmill'}, 1.01)


@pytest.mark.parametrize('values', [[], [float('nan')], [float('inf')], [1.0, 1.01]])
def test_missing_and_rounding_boundary_refused(values):
    with pytest.raises(ValueError):
        rounded_region_speed(values)


@pytest.mark.parametrize('key,value', [('speed_m_s', 1.0), ('speed_m_s', True),
    ('speed_m_s', float('nan')), ('treadmill', 'true'), ('treadmill', 1), ('surface', 'overground')])
def test_wrong_source_metadata_rejected(key, value):
    metadata = {'speed_m_s': 1.01, 'treadmill': True, 'surface': 'treadmill'}
    metadata[key] = value
    with pytest.raises(ValueError):
        require_metadata('level_walking', 'level', metadata, 1.01)


@pytest.mark.parametrize('task,task_id', [('run', 'level'), ('level_walking', 'turn_left')])
def test_wrong_task_rejected(task, task_id):
    with pytest.raises(ValueError):
        require_metadata(task, task_id,
                         {'speed_m_s': 1.01, 'treadmill': True, 'surface': 'treadmill'}, 1.01)
