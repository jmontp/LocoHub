"""Synthetic readback checks detect changes to existing and added signals."""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from contributor_tools.extend_umich_tread_source import readback


def tables(tmp_path):
    original = pd.DataFrame({'source_start_time_s': np.full(150, .1),
                             'source_end_time_s': np.full(150, .12),
                             'observation_id': ['synthetic-cycle'] * 150,
                             'existing_signal': np.arange(150, dtype=float)})
    raw = np.zeros((1, 13))
    raw[0, 10:] = [2., 8., 4.]
    trial = {'jointForces': {'RHipForce': raw}}
    extended = original.copy()
    extended['source_joint_force_rhipforce_component_0_N_kg'] = np.interp(
        np.linspace(0, 2, 150), [0, 1, 2], [2., 8., 4.])
    base_path, output_path = tmp_path / 'base.parquet', tmp_path / 'new.parquet'
    pq.write_table(pa.Table.from_pandas(original, preserve_index=False), base_path)
    pq.write_table(pa.Table.from_pandas(extended, preserve_index=False), output_path)
    return base_path, output_path, trial, extended


def test_source_values_and_existing_columns_checked(tmp_path):
    base, output, trial, _ = tables(tmp_path)
    result = readback(base, output, trial)
    assert result['observations_checked'] == 1
    assert result['finite_source_values_checked'] == 150
    assert result['existing_columns_exactly_preserved'] is True


@pytest.mark.parametrize('column', ['existing_signal', 'source_joint_force_rhipforce_component_0_N_kg'])
def test_modified_value_is_rejected(tmp_path, column):
    base, output, trial, frame = tables(tmp_path)
    frame.loc[35, column] += 1
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), output)
    with pytest.raises((ValueError, AssertionError)):
        readback(base, output, trial)


def test_truncated_output_is_rejected(tmp_path):
    base, output, trial, frame = tables(tmp_path)
    pq.write_table(pa.Table.from_pandas(frame.iloc[:149], preserve_index=False), output)
    with pytest.raises(ValueError):
        readback(base, output, trial)
