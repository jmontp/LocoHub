"""
Generate expected tutorial outputs from the example CSV.

Reads docs/contributing/locohub_example_data.csv and produces publication-ready
reference plots used in the Tutorials. Outputs are saved under:
  docs/users/tutorials/assets/

Requirements: Python 3.9+, pandas, matplotlib

Usage:
  python maintainer_tools/generate_tutorial_outputs.py \
         --csv docs/contributing/locohub_example_data.csv \
         --out docs/users/tutorials/assets \
         --suffix _python

This script is idempotent and will overwrite existing output images.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def ensure_out_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_example(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    # Basic sanity checks for expected columns
    required = [
        "subject",
        "task",
        "phase_ipsi",
        "knee_flexion_angle_ipsi_rad",
        "vertical_grf_ipsi_N",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def mean_std_by_phase(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    grouped = (
        df.groupby("phase_ipsi", as_index=False)[value_col]
        .agg(mean="mean", std="std")
        .sort_values("phase_ipsi")
    )
    return grouped


def plot_mean_sd(
    phase_df: pd.DataFrame,
    value_label: str,
    ylabel: str,
    outfile: Path,
    title: str | None = None,
) -> None:
    plt.figure(figsize=(6.0, 3.6), dpi=150)
    x = phase_df["phase_ipsi"].to_numpy()
    mean = phase_df["mean"].to_numpy()
    sd = phase_df["std"].to_numpy()

    # Shaded band
    plt.fill_between(x, mean - sd, mean + sd, color="#1f77b4", alpha=0.2, linewidth=0)
    # Mean line
    plt.plot(x, mean, color="#1f77b4", linewidth=2.0, label=value_label)

    plt.xlabel("Gait Cycle (%)")
    plt.ylabel(ylabel)
    if title:
        plt.title(title)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(outfile)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tutorial output figures")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("docs/contributing/locohub_example_data.csv"),
        help="Path to the example CSV",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/users/tutorials/assets"),
        help="Output directory for figures",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="_python",
        help="Filename suffix to distinguish language (e.g., _python)",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Optional subject filter (e.g., UM21_AB01)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Optional task filter (e.g., level_walking)",
    )
    args = parser.parse_args()

    ensure_out_dir(args.out)
    df = load_example(args.csv)

    # Optional filters for deterministic outputs
    if args.subject:
        df = df[df["subject"] == args.subject]
    if args.task:
        df = df[df["task"] == args.task]

    # 1) Knee flexion mean ± SD by phase
    knee = mean_std_by_phase(df, "knee_flexion_angle_ipsi_rad")
    plot_mean_sd(
        knee,
        value_label="Knee Flexion (rad)",
        ylabel="Knee Flexion (rad)",
        outfile=args.out / f"expected_knee_flexion_mean_sd{args.suffix}.png",
        title="Knee Flexion: Mean ± SD",
    )

    # 2) Vertical GRF mean ± SD by phase
    grf = mean_std_by_phase(df, "vertical_grf_ipsi_N")
    plot_mean_sd(
        grf,
        value_label="Vertical GRF (N)",
        ylabel="Vertical GRF (N)",
        outfile=args.out / f"expected_vertical_grf_mean_sd{args.suffix}.png",
        title="Vertical GRF: Mean ± SD",
    )
    print(f"Wrote: {args.out / ('expected_knee_flexion_mean_sd' + args.suffix + '.png')}")
    print(f"Wrote: {args.out / ('expected_vertical_grf_mean_sd' + args.suffix + '.png')}")


if __name__ == "__main__":
    main()
