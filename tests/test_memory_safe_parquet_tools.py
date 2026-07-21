from argparse import Namespace
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from contributor_tools.common.merge_parquet_shards import merge_parquet_shards
from contributor_tools import run_memory_limited_validation
from contributor_tools.audit_dataset_units import audit


def test_merge_parquet_shards_unifies_schema_and_bounds_row_groups(tmp_path):
    first = tmp_path / '001.parquet'
    second = tmp_path / '002.parquet'
    output = tmp_path / 'merged.parquet'
    pd.DataFrame({'subject': ['A'] * 5, 'x': range(5)}).to_parquet(first, index=False)
    pd.DataFrame({'subject': ['B'] * 4, 'x': range(5, 9), 'y': range(4)}).to_parquet(second, index=False)

    rows = merge_parquet_shards([first, second], output, row_group_size=3, batch_size=2)

    parquet_file = pq.ParquetFile(output)
    assert rows == 9
    assert parquet_file.metadata.num_rows == 9
    assert max(
        parquet_file.metadata.row_group(i).num_rows
        for i in range(parquet_file.metadata.num_row_groups)
    ) <= 3
    merged = pd.read_parquet(output)
    assert merged['subject'].tolist() == ['A'] * 5 + ['B'] * 4
    assert merged.loc[:4, 'y'].isna().all()


def test_memory_limited_launcher_builds_systemd_scope(monkeypatch):
    monkeypatch.setattr(run_memory_limited_validation.sys, 'platform', 'linux')
    monkeypatch.setattr(run_memory_limited_validation.shutil, 'which', lambda _: '/usr/bin/systemd-run')
    args = Namespace(memory_high_mb=2048, memory_max_mb=3072, memory_swap_max_mb=512)

    command = run_memory_limited_validation.build_command(args, ['dataset.parquet'])

    assert command[:4] == ['systemd-run', '--user', '--scope', '--quiet']
    assert 'MemoryHigh=2048M' in command
    assert 'MemoryMax=3072M' in command
    assert 'MemorySwapMax=512M' in command
    assert command[-1] == 'dataset.parquet'


def test_unit_audit_scans_every_unit_column(tmp_path):
    dataset = tmp_path / 'units.parquet'
    pd.DataFrame(
        {
            'time_s': [0.0, 0.01],
            'knee_flexion_angle_ipsi_rad': [0.1, 7.0],
            'grf_vertical_ipsi_BW': [1.0, 2.0],
        }
    ).to_parquet(dataset, index=False)

    findings, indices = audit(dataset, batch_size=1, column_chunk_size=1)

    by_column = {item['column']: item for item in findings}
    assert set(by_column) == {'knee_flexion_angle_ipsi_rad', 'grf_vertical_ipsi_BW'}
    assert by_column['knee_flexion_angle_ipsi_rad']['outside'] == 1
    assert by_column['grf_vertical_ipsi_BW']['outside'] == 0
    assert indices == [('time_s', 0.0, 0.01, 0)]
