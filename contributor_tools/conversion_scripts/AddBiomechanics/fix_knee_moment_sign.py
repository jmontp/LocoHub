#!/usr/bin/env python3
"""
Post-process AddBiomechanics parquet files to fix knee moment sign.

The original conversion had knee angle/velocity negated but not the moment.
This script negates the knee moment columns to match the angle convention.
"""

import sys
import pandas as pd
from pathlib import Path
import argparse


def fix_knee_moment_sign(input_path: Path, output_path: Path = None) -> None:
    """Fix the knee moment sign in a parquet file.

    Args:
        input_path: Path to input parquet file
        output_path: Path to output parquet file (default: overwrites input)
    """
    if output_path is None:
        output_path = input_path

    print(f"Processing: {input_path.name}")
    df = pd.read_parquet(input_path)

    # All knee columns to negate (angle, velocity, and moment)
    knee_moment_cols = [
        'knee_flexion_angle_ipsi_rad',
        'knee_flexion_angle_contra_rad',
        'knee_flexion_velocity_ipsi_rad_s',
        'knee_flexion_velocity_contra_rad_s',
        'knee_flexion_moment_ipsi_Nm_kg',
        'knee_flexion_moment_contra_Nm_kg'
    ]

    modified = False
    for col in knee_moment_cols:
        if col in df.columns:
            df[col] = -df[col]
            print(f"  Negated: {col}")
            modified = True

    if modified:
        df.to_parquet(output_path, index=False)
        print(f"  Saved: {output_path.name}")
    else:
        print(f"  No knee moment columns found, skipping")


def main():
    parser = argparse.ArgumentParser(description="Fix knee moment sign in AddBiomechanics parquet files")
    parser.add_argument('files', nargs='+', help='Parquet files to process')
    parser.add_argument('--output-dir', '-o', help='Output directory (default: overwrite in place)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for file_path in args.files:
        input_path = Path(file_path)
        if not input_path.exists():
            print(f"Skipping (not found): {file_path}")
            continue

        output_path = output_dir / input_path.name if output_dir else input_path
        fix_knee_moment_sign(input_path, output_path)

    print("\nDone!")


if __name__ == '__main__':
    main()
