#!/usr/bin/env python3
"""
Utility to migrate legacy GRF column names to the new schema.

Old pattern (deprecated):
    vertical_grf_<side>_<unit>, anterior_grf_<side>_<unit>, lateral_grf_<side>_<unit>

New pattern (canonical):
    grf_<axis>_<side>_<unit>, e.g. grf_vertical_ipsi_BW

This script rewrites Parquet files in-place or to a new output path.
It is safe to run multiple times; already-migrated files are skipped.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import pandas as pd

try:
    # Prefer canonical mapping from the Python feature constants
    from locohub.feature_constants import LEGACY_GRF_ALIASES  # type: ignore
except Exception:
    # Fallback: local copy in case locohub is not importable in the environment
    LEGACY_GRF_ALIASES: Dict[str, str] = {
        # Raw GRF (N)
        "vertical_grf_ipsi_N": "grf_vertical_ipsi_N",
        "vertical_grf_contra_N": "grf_vertical_contra_N",
        "anterior_grf_ipsi_N": "grf_anterior_ipsi_N",
        "anterior_grf_contra_N": "grf_anterior_contra_N",
        "lateral_grf_ipsi_N": "grf_lateral_ipsi_N",
        "lateral_grf_contra_N": "grf_lateral_contra_N",
        # Normalized GRF (BW)
        "vertical_grf_ipsi_BW": "grf_vertical_ipsi_BW",
        "vertical_grf_contra_BW": "grf_vertical_contra_BW",
        "anterior_grf_ipsi_BW": "grf_anterior_ipsi_BW",
        "anterior_grf_contra_BW": "grf_anterior_contra_BW",
        "lateral_grf_ipsi_BW": "grf_lateral_ipsi_BW",
        "lateral_grf_contra_BW": "grf_lateral_contra_BW",
    }


def migrate_file(
    input_path: Path,
    output_path: Path | None,
    dry_run: bool,
    flip_cop_anterior: bool,
) -> None:
    df = pd.read_parquet(input_path)

    mapping: Dict[str, str] = {
        old: new for old, new in LEGACY_GRF_ALIASES.items() if old in df.columns
    }

    if not mapping:
        print(f"{input_path}: no legacy GRF columns found; skipping")
    else:
        print(f"{input_path}: renaming columns:")
        for old, new in sorted(mapping.items()):
            print(f"  {old} -> {new}")

    if flip_cop_anterior:
        cop_cols = [
            c for c in df.columns
            if c.startswith("cop_anterior_") and c.endswith("_m")
        ]
        if cop_cols:
            print(f"  flipping sign for COP anterior columns: {', '.join(cop_cols)}")
            if not dry_run:
                df[cop_cols] = -df[cop_cols]
        else:
            print("  no cop_anterior_* columns found to flip")

    if dry_run:
        return

    df = df.rename(columns=mapping)
    target = output_path or input_path
    df.to_parquet(target, index=False)
    print(f"  ✔ wrote migrated file to {target}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate legacy GRF column names (vertical_grf_*) to grf_<axis>_<side>_<unit>."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Parquet files or directories containing Parquet files to migrate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report files and columns that would be changed.",
    )
    parser.add_argument(
        "--flip-cop-anterior",
        action="store_true",
        help="Also flip the sign of any cop_anterior_*_m columns (anterior-positive).",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default=None,
        help="Optional suffix for migrated files (e.g., '_v2'). "
        "If omitted, files are modified in-place.",
    )

    args = parser.parse_args()

    parquet_files = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_file() and p.suffix.lower() == ".parquet":
            parquet_files.append(p)
        elif p.is_dir():
            parquet_files.extend(p.rglob("*.parquet"))
        else:
            print(f"Skipping non-parquet path: {p}")

    if not parquet_files:
        print("No parquet files found to migrate.")
        return

    for src in sorted(parquet_files):
        if args.suffix:
            dst = src.with_name(src.stem + args.suffix + src.suffix)
        else:
            dst = None
        migrate_file(
            src,
            dst,
            dry_run=args.dry_run,
            flip_cop_anterior=args.flip_cop_anterior,
        )


if __name__ == "__main__":
    main()
