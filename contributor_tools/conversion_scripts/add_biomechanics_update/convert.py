"""CLI entry point for converting AddBiomechanics datasets to locomotion parquet files.

This script orchestrates the full pipeline:
    1. Enumerate requested datasets from configuration or CLI flags.
    2. Stream frames from B3D sources.
    3. Normalize columns and metadata to the canonical schema.
    4. Detect heel strikes and segment strides.
    5. Emit time- and phase-indexed parquet exports.

The implementation will rely on shared utilities housed in sibling modules of
this package and contributor_tools/common.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

from . import config, schemas, task_mappings
from .io import b3d_reader, writers
from .utils import stride_events, metadata


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Build the CLI argument parser and return parsed arguments."""

    parser = argparse.ArgumentParser(
        description="Convert AddBiomechanics B3D datasets to locomotion parquet format",
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        required=True,
        help="Root directory containing dataset folders with B3D files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory where time and phase parquet files will be written.",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        nargs="*",
        help="Optional subset of dataset names to convert (defaults to all known).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Number of frames per processing chunk when streaming from B3D.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing parquet exports if they already exist.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    """Entry point used by both CLI and tests."""

    args = parse_args(argv)
    dataset_config = config.load_dataset_config(args.datasets)

    for dataset_name in dataset_config.dataset_names:
        config.ensure_output_layout(args.output_root, dataset_name, overwrite=args.overwrite)
        reader = b3d_reader.B3DReader(
            dataset_root=args.input_root,
            dataset_name=dataset_name,
            chunk_size=args.chunk_size,
        )
        for chunk in reader.stream_frames():
            normalized_chunk = schemas.normalize_columns(chunk, dataset_name)
            task_mappings.apply_task_metadata(normalized_chunk, dataset_name)
            metadata.attach_subject_metadata(normalized_chunk, dataset_name)
            events = stride_events.detect_events(normalized_chunk)
            writers.write_time_chunk(
                normalized_chunk,
                events,
                args.output_root,
                dataset_name,
            )
            writers.write_phase_chunk(
                normalized_chunk,
                events,
                args.output_root,
                dataset_name,
            )


if __name__ == "__main__":
    main()
