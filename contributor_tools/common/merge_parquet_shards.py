#!/usr/bin/env python3
"""Merge parquet shards without loading a complete dataset into memory."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq


def merge_parquet_shards(
    shards: Iterable[Path],
    output_path: Path,
    *,
    row_group_size: int = 65_536,
    batch_size: int = 65_536,
) -> int:
    """Stream ordered shards into one parquet file and return its row count."""

    shard_paths = [Path(path) for path in shards]
    if not shard_paths:
        raise ValueError('No parquet shards were provided')
    if row_group_size < 1 or batch_size < 1:
        raise ValueError('row_group_size and batch_size must be positive')

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = pa.unify_schemas(
        [pq.ParquetFile(path).schema_arrow for path in shard_paths],
        promote_options='permissive',
    )
    rows_written = 0
    temporary = tempfile.NamedTemporaryFile(
        prefix=f'.{output_path.name}.', suffix='.partial', dir=output_path.parent, delete=False
    )
    temporary_path = Path(temporary.name)
    temporary.close()

    try:
        with pq.ParquetWriter(temporary_path, schema=schema, compression='snappy') as writer:
            for shard_path in shard_paths:
                parquet_file = pq.ParquetFile(shard_path)
                for batch in parquet_file.iter_batches(
                    batch_size=batch_size, use_threads=False
                ):
                    if not batch.schema.equals(schema, check_metadata=False):
                        batch = pa.RecordBatch.from_arrays(
                            [
                                (
                                    batch.column(batch.schema.get_field_index(field.name)).cast(field.type)
                                    if batch.schema.get_field_index(field.name) >= 0
                                    else pa.nulls(batch.num_rows, type=field.type)
                                )
                                for field in schema
                            ],
                            schema=schema,
                        )
                    writer.write_batch(batch, row_group_size=row_group_size)
                    rows_written += batch.num_rows
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shard_dir', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--row-group-size', type=int, default=65_536)
    parser.add_argument('--batch-size', type=int, default=65_536)
    args = parser.parse_args()

    shards = sorted(args.shard_dir.glob('*.parquet'))
    rows = merge_parquet_shards(
        shards,
        args.output,
        row_group_size=args.row_group_size,
        batch_size=args.batch_size,
    )
    print(f'Merged {len(shards)} shards and {rows} rows into {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
