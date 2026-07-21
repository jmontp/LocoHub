#!/usr/bin/env python3
"""Audit standardized signal units and broad numerical guardrails."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


UNIT_LIMITS = (
    ('_rad_s2', 'rad/s^2', 10_000.0),
    ('_rad_s', 'rad/s', 100.0),
    ('_Nm_kg', 'Nm/kg', 20.0),
    ('_rad', 'rad', 2 * np.pi),
    ('_BW', 'body weights', 10.0),
    ('_m', 'm', 5.0),
)


def signal_unit(column: str):
    for suffix, unit, limit in UNIT_LIMITS:
        if column.endswith(suffix):
            return unit, limit
    return None


def audit(path: Path, batch_size: int = 16_384, column_chunk_size: int = 8):
    parquet_file = pq.ParquetFile(path)
    signal_columns = [name for name in parquet_file.schema.names if signal_unit(name)]
    findings = []

    for start in range(0, len(signal_columns), column_chunk_size):
        columns = signal_columns[start:start + column_chunk_size]
        aggregates = {
            name: {'min': np.inf, 'max': -np.inf, 'finite': 0, 'infinite': 0, 'outside': 0}
            for name in columns
        }
        for batch in parquet_file.iter_batches(
            columns=columns, batch_size=batch_size, use_threads=False
        ):
            for index, name in enumerate(columns):
                array = pc.cast(batch.column(index), pa.float64(), safe=False)
                values = np.asarray(array.to_numpy(zero_copy_only=False), dtype=float)
                finite = np.isfinite(values)
                unit, limit = signal_unit(name)
                if finite.any():
                    aggregates[name]['min'] = min(aggregates[name]['min'], float(values[finite].min()))
                    aggregates[name]['max'] = max(aggregates[name]['max'], float(values[finite].max()))
                aggregates[name]['finite'] += int(finite.sum())
                aggregates[name]['infinite'] += int(np.isinf(values).sum())
                aggregates[name]['outside'] += int((finite & (np.abs(values) > limit)).sum())

        for name in columns:
            unit, limit = signal_unit(name)
            findings.append({'column': name, 'unit': unit, 'limit': limit, **aggregates[name]})

    index_findings = []
    for name, lower, upper in (
        ('time_s', 0.0, np.inf),
        ('phase_ipsi', 0.0, 100.0),
        ('phase_contra', 0.0, 100.0),
        ('sampling_rate_hz', 0.0, np.inf),
    ):
        if name not in parquet_file.schema.names:
            continue
        minimum = np.inf
        maximum = -np.inf
        invalid = 0
        for batch in parquet_file.iter_batches(columns=[name], batch_size=batch_size, use_threads=False):
            values = np.asarray(
                pc.cast(batch.column(0), pa.float64(), safe=False).to_numpy(zero_copy_only=False),
                dtype=float,
            )
            finite = np.isfinite(values)
            if finite.any():
                minimum = min(minimum, float(values[finite].min()))
                maximum = max(maximum, float(values[finite].max()))
            invalid += int((~finite | (values < lower) | (values > upper)).sum())
        index_findings.append((name, minimum, maximum, invalid))
    return findings, index_findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('datasets', nargs='+', type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.datasets:
        findings, indices = audit(path)
        suspicious = [item for item in findings if item['infinite'] or item['outside']]
        print(f'\n{path}: {len(findings)} unit-bearing columns')
        for name, minimum, maximum, invalid in indices:
            print(f'  {name}: [{minimum:g}, {maximum:g}], invalid={invalid:,}')
            failed |= invalid > 0
        print(f'  suspicious columns: {len(suspicious)}')
        for item in sorted(suspicious, key=lambda value: value['outside'], reverse=True):
            print(
                f"  FAIL {item['column']} ({item['unit']}): "
                f"[{item['min']:.6g}, {item['max']:.6g}], "
                f"outside ±{item['limit']:g}={item['outside']:,}, inf={item['infinite']:,}"
            )
        failed |= bool(suspicious)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
