"""Historical trial names must not become unsupported walking observations."""
import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'contributor_tools/conversion_scripts/AddBiomechanics/dataset_configs.py'
spec = importlib.util.spec_from_file_location('addbiomechanics_task_configs', SOURCE)
configs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configs)


@pytest.mark.parametrize('name', [
    'Gait_1', 'Gait_10', 'Gait_7', 'Gait_8', 'Gait_9',
    'STS_1', 'STS_2', 'STS_5', 'walk_1', 'run_1', 'unknown', '',
])
def test_falisse_names_do_not_authorize_task_or_phase_conversion(name):
    task, task_id, info = configs.get_task_info('Falisse2016', name)
    assert task is None
    assert task_id == name
    assert info == 'task_status:unresolved_source_record_identity'
    assert not configs.is_cyclic_task(task)


def test_unresolved_tasks_remain_null_and_source_names_survive_parquet(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    names = ['Gait_1', 'STS_1', 'STS_2', 'STS_5']
    rows = [dict(zip(('task', 'task_id', 'task_info'),
                     configs.get_task_info('Falisse2016', name))) for name in names]
    path = tmp_path / 'source_names.parquet'
    pq.write_table(pa.Table.from_pylist(rows), path)
    restored = pq.read_table(path).to_pylist()
    assert restored == rows
    assert [row['task_id'] for row in restored] == names
    assert all(row['task'] is None for row in restored)
