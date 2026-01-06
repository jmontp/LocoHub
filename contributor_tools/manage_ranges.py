#!/usr/bin/env python3
"""
Manage validation ranges for biomechanical datasets.

This tool provides CLI commands to:
- Generate validation ranges from parquet data
- Update existing ranges in YAML files
- Show current ranges for specific tasks

Usage:
    # Generate ranges for specific tasks from data
    python manage_ranges.py generate dataset.parquet --tasks sit_to_stand stand_to_sit

    # Generate ranges and update the default ranges file
    python manage_ranges.py generate dataset.parquet --tasks sit_to_stand --update

    # Show current ranges for a task
    python manage_ranges.py show --task sit_to_stand

    # List all tasks with defined ranges
    python manage_ranges.py list
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from typing import Dict, List, Optional, Tuple

# Default paths
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_RANGES_PATH = PROJECT_ROOT / "contributor_tools" / "validation_ranges" / "default_ranges.yaml"

# Phase checkpoints as percentages (0-100) for YAML output
# The data uses normalized phase_ipsi values (0.0 to ~1.0)
# 0%: heel strike, 15%: braking peak (GRF), 50%: propulsion peak / contra HS, 75%: late swing
PHASE_CHECKPOINTS = [0, 15, 25, 50, 75]  # Percentage values for YAML keys

# Features to generate ranges for
DEFAULT_FEATURES = [
    'pelvis_sagittal_angle_rad',
    'pelvis_frontal_angle_rad',
    'pelvis_transverse_angle_rad',
    'hip_flexion_angle_ipsi_rad',
    'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad',
    'knee_flexion_angle_contra_rad',
    'ankle_dorsiflexion_angle_ipsi_rad',
    'ankle_dorsiflexion_angle_contra_rad',
    'hip_flexion_moment_ipsi_Nm_kg',
    'hip_flexion_moment_contra_Nm_kg',
    'knee_flexion_moment_ipsi_Nm_kg',
    'knee_flexion_moment_contra_Nm_kg',
    'ankle_dorsiflexion_moment_ipsi_Nm_kg',
    'ankle_dorsiflexion_moment_contra_Nm_kg',
    'grf_vertical_ipsi_BW',
    'grf_vertical_contra_BW',
    'grf_anterior_ipsi_BW',
    'grf_anterior_contra_BW',
    'grf_lateral_ipsi_BW',
    'grf_lateral_contra_BW',
    'cop_anterior_ipsi_m',
    'cop_anterior_contra_m',
    'cop_lateral_ipsi_m',
    'cop_lateral_contra_m',
    'cop_vertical_ipsi_m',
    'cop_vertical_contra_m',
    'thigh_sagittal_angle_ipsi_rad',
    'thigh_sagittal_angle_contra_rad',
    'shank_sagittal_angle_ipsi_rad',
    'shank_sagittal_angle_contra_rad',
    'foot_sagittal_angle_ipsi_rad',
    'foot_sagittal_angle_contra_rad',
]


def load_ranges(ranges_path: Path) -> dict:
    """Load validation ranges from YAML file."""
    with open(ranges_path, 'r') as f:
        return yaml.safe_load(f)


def save_ranges(ranges: dict, ranges_path: Path):
    """Save validation ranges to YAML file."""
    with open(ranges_path, 'w') as f:
        yaml.dump(ranges, f, default_flow_style=False, sort_keys=False)


def compute_bounds_iqr(values: np.ndarray, multiplier: float = 2.0) -> Tuple[float, float]:
    """Compute bounds using IQR method.

    Args:
        values: Array of values
        multiplier: IQR multiplier for bounds (default 2.0)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return float(lower), float(upper)


def compute_bounds_percentile(values: np.ndarray, lower_pct: float = 1.0, upper_pct: float = 99.0) -> Tuple[float, float]:
    """Compute bounds using percentiles.

    Args:
        values: Array of values
        lower_pct: Lower percentile (default 1.0)
        upper_pct: Upper percentile (default 99.0)

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    lower = np.percentile(values, lower_pct)
    upper = np.percentile(values, upper_pct)
    return float(lower), float(upper)


def generate_ranges_for_task(
    df: pd.DataFrame,
    task_name: str,
    features: List[str],
    method: str = 'iqr',
    iqr_multiplier: float = 2.0,
    min_samples: int = 10,
    existing_phases: List[int] = None
) -> Dict:
    """Generate validation ranges for a task from data.

    Args:
        df: DataFrame with biomechanical data
        task_name: Name of task to generate ranges for
        features: List of feature names to include
        method: 'iqr' or 'percentile'
        iqr_multiplier: IQR multiplier if method='iqr'
        min_samples: Minimum samples required at each phase
        existing_phases: Phase checkpoints from existing YAML (if any).
                        Falls back to PHASE_CHECKPOINTS if None.

    Returns:
        Dictionary with ranges in YAML format
    """
    task_df = df[df['task'] == task_name]
    n_strides = len(task_df) // 150

    if n_strides == 0:
        print(f"  Warning: No data found for task '{task_name}'")
        return {}

    print(f"  Generating ranges for {task_name} ({n_strides} strides)")

    ranges = {'phases': {}}

    # Determine phase column format
    phase_col = 'phase_ipsi'
    if phase_col not in task_df.columns:
        print(f"  Warning: No phase_ipsi column found")
        return {}

    phase_values = task_df[phase_col].unique()
    max_phase = max(phase_values)

    # Determine phase format:
    # - Normalized: 0.0 to ~1.0
    # - Percentage: 0 to 100
    # - Indexed: 0 to 149
    if max_phase < 2.0:
        phase_format = 'normalized'
    elif max_phase <= 100.0:
        phase_format = 'percentage'
    else:
        phase_format = 'indexed'

    # Use existing phases from YAML if provided, otherwise use defaults
    phase_checkpoints = existing_phases if existing_phases else PHASE_CHECKPOINTS

    for phase_pct in phase_checkpoints:
        # Convert percentage to the format used in data
        if phase_format == 'normalized':
            # Data uses 0.0 to ~1.0
            target_phase = phase_pct / 100.0
            tolerance = 0.01  # 1% tolerance
        elif phase_format == 'percentage':
            # Data uses 0 to 100 (percentage)
            target_phase = float(phase_pct)
            tolerance = 1.0  # 1% tolerance
        else:
            # Data uses 0 to 149 (phase index)
            target_phase = phase_pct * 149 / 100
            tolerance = 0.5

        phase_mask = (task_df[phase_col] >= target_phase - tolerance) & \
                     (task_df[phase_col] <= target_phase + tolerance)

        phase_data = task_df[phase_mask]

        if len(phase_data) == 0:
            print(f"    Phase {phase_pct}%: no data found")
            continue

        phase_ranges = {}

        for feat in features:
            if feat not in phase_data.columns:
                continue

            values = phase_data[feat].dropna().values
            if len(values) < min_samples:
                continue

            if method == 'iqr':
                lower, upper = compute_bounds_iqr(values, iqr_multiplier)
            else:
                lower, upper = compute_bounds_percentile(values)

            # Ensure lower < upper
            if lower >= upper:
                epsilon = max(1e-4, abs(lower) * 0.05)
                lower -= epsilon
                upper += epsilon

            phase_ranges[feat] = {
                'min': round(lower, 6),
                'max': round(upper, 6)
            }

        if phase_ranges:
            ranges['phases'][phase_pct] = phase_ranges
            print(f"    Phase {phase_pct}%: {len(phase_ranges)} features")

    return ranges


def cmd_generate(args):
    """Generate validation ranges from dataset."""
    # Load dataset
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset not found: {dataset_path}")
        return 1

    print(f"Loading dataset: {dataset_path}")
    df = pd.read_parquet(dataset_path)

    # Get available tasks
    available_tasks = df['task'].unique().tolist()

    # Determine which tasks to process
    if args.tasks:
        tasks = args.tasks
        for task in tasks:
            if task not in available_tasks:
                print(f"Warning: Task '{task}' not found in dataset")
    else:
        tasks = available_tasks

    # Determine features to use
    features = args.features if args.features else DEFAULT_FEATURES

    print(f"\nGenerating ranges for {len(tasks)} task(s) using {args.method} method")
    print(f"IQR multiplier: {args.iqr_multiplier}")
    print()

    # Load existing ranges to get phase checkpoints (if updating)
    ranges_path = Path(args.ranges) if args.ranges else DEFAULT_RANGES_PATH
    existing = load_ranges(ranges_path) if ranges_path.exists() else {'tasks': {}}

    # Generate ranges for each task
    all_ranges = {}
    for task in tasks:
        # Get existing phases for this task (if any) from YAML
        existing_phases = None
        if task in existing.get('tasks', {}):
            task_data = existing['tasks'][task]
            if 'phases' in task_data:
                existing_phases = sorted([int(p) for p in task_data['phases'].keys()])

        task_ranges = generate_ranges_for_task(
            df, task, features,
            method=args.method,
            iqr_multiplier=args.iqr_multiplier,
            existing_phases=existing_phases
        )
        if task_ranges:
            all_ranges[task] = task_ranges

    # Output results
    if args.update:
        # Update existing ranges file (reuse already-loaded existing)
        print(f"\nUpdating ranges file: {ranges_path}")

        for task, task_ranges in all_ranges.items():
            if task not in existing['tasks']:
                # New task - add entirely
                existing['tasks'][task] = task_ranges
            else:
                # Existing task - merge features at each phase
                existing_task = existing['tasks'][task]
                if 'phases' not in existing_task:
                    existing_task['phases'] = {}
                for phase, phase_ranges in task_ranges.get('phases', {}).items():
                    if phase not in existing_task['phases']:
                        existing_task['phases'][phase] = {}
                    # Merge features (new values override existing)
                    existing_task['phases'][phase].update(phase_ranges)
            print(f"  Updated: {task}")

        save_ranges(existing, ranges_path)
        print(f"\n✅ Ranges file updated successfully")
    else:
        # Print to stdout
        print("\n--- Generated Ranges (YAML) ---\n")
        output = {'tasks': all_ranges}
        print(yaml.dump(output, default_flow_style=False, sort_keys=False))

        if not args.update:
            print("\nTip: Add --update to write these ranges to the default ranges file")

    return 0


def cmd_show(args):
    """Show current ranges for a task."""
    ranges_path = Path(args.ranges) if args.ranges else DEFAULT_RANGES_PATH

    if not ranges_path.exists():
        print(f"Error: Ranges file not found: {ranges_path}")
        return 1

    ranges = load_ranges(ranges_path)

    if args.task not in ranges['tasks']:
        print(f"Error: Task '{args.task}' not found in ranges file")
        print(f"Available tasks: {list(ranges['tasks'].keys())}")
        return 1

    task_ranges = ranges['tasks'][args.task]
    print(f"=== {args.task} ===\n")
    print(yaml.dump({args.task: task_ranges}, default_flow_style=False, sort_keys=False))

    return 0


def cmd_list(args):
    """List all tasks with defined ranges."""
    ranges_path = Path(args.ranges) if args.ranges else DEFAULT_RANGES_PATH

    if not ranges_path.exists():
        print(f"Error: Ranges file not found: {ranges_path}")
        return 1

    ranges = load_ranges(ranges_path)

    print(f"Tasks with defined ranges in {ranges_path.name}:\n")
    for task in sorted(ranges['tasks'].keys()):
        task_data = ranges['tasks'][task]
        if 'phases' in task_data:
            n_phases = len(task_data['phases'])
            n_features = sum(len(phase_data) for phase_data in task_data['phases'].values())
            print(f"  {task}: {n_phases} phases, {n_features} feature-phase combinations")
        else:
            print(f"  {task}: (empty)")

    return 0


def cmd_widen(args):
    """Widen existing validation ranges for specific features."""
    ranges_path = Path(args.ranges) if args.ranges else DEFAULT_RANGES_PATH

    if not ranges_path.exists():
        print(f"Error: Ranges file not found: {ranges_path}")
        return 1

    ranges = load_ranges(ranges_path)

    # Determine which tasks to process
    available_tasks = list(ranges.get('tasks', {}).keys())
    if args.tasks:
        tasks = args.tasks
        for task in tasks:
            if task not in available_tasks:
                print(f"Warning: Task '{task}' not found in ranges file")
    else:
        tasks = available_tasks

    # Features to widen
    features = args.features

    # Expansion parameters
    expand_pct = args.percent / 100.0 if args.percent else 0.0
    expand_abs = args.absolute if args.absolute else 0.0

    if expand_pct == 0 and expand_abs == 0:
        print("Error: Must specify --percent or --absolute expansion amount")
        return 1

    print(f"Widening ranges in: {ranges_path.name}")
    print(f"Features: {', '.join(features)}")
    print(f"Tasks: {', '.join(tasks) if args.tasks else 'all'}")
    if expand_pct > 0:
        print(f"Expansion: {args.percent}% on each side")
    if expand_abs > 0:
        print(f"Expansion: ±{expand_abs} absolute")
    print()

    changes_made = 0

    for task in tasks:
        if task not in ranges['tasks']:
            continue

        task_data = ranges['tasks'][task]
        if 'phases' not in task_data:
            continue

        task_changes = 0
        for phase, phase_data in task_data['phases'].items():
            for feat in features:
                if feat not in phase_data:
                    continue

                feat_range = phase_data[feat]
                old_min = feat_range['min']
                old_max = feat_range['max']

                # Calculate expansion
                range_width = old_max - old_min

                # Percentage expansion (based on range width)
                pct_expand = range_width * expand_pct / 2.0

                # Apply both percentage and absolute expansion
                new_min = old_min - pct_expand - expand_abs
                new_max = old_max + pct_expand + expand_abs

                feat_range['min'] = round(new_min, 6)
                feat_range['max'] = round(new_max, 6)
                task_changes += 1

        if task_changes > 0:
            print(f"  {task}: widened {task_changes} feature-phase bounds")
            changes_made += task_changes

    if changes_made > 0:
        save_ranges(ranges, ranges_path)
        print(f"\n✅ Widened {changes_made} bounds in {ranges_path.name}")
    else:
        print("\n⚠️  No matching features found to widen")

    return 0


def cmd_delete(args):
    """Delete tasks from a validation ranges file."""
    ranges_path = Path(args.ranges) if args.ranges else DEFAULT_RANGES_PATH

    if not ranges_path.exists():
        print(f"Error: Ranges file not found: {ranges_path}")
        return 1

    ranges = load_ranges(ranges_path)

    if 'tasks' not in ranges:
        print("Error: No 'tasks' section in ranges file")
        return 1

    tasks_to_delete = args.tasks
    deleted = []
    not_found = []

    for task in tasks_to_delete:
        if task in ranges['tasks']:
            del ranges['tasks'][task]
            deleted.append(task)
        else:
            not_found.append(task)

    if not_found:
        print(f"Warning: Tasks not found: {', '.join(not_found)}")

    if deleted:
        save_ranges(ranges, ranges_path)
        print(f"✅ Deleted {len(deleted)} task(s) from {ranges_path.name}: {', '.join(deleted)}")
    else:
        print("⚠️  No tasks were deleted")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage validation ranges for biomechanical datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate ranges from dataset')
    gen_parser.add_argument('dataset', help='Path to parquet dataset')
    gen_parser.add_argument('--tasks', nargs='+', help='Tasks to generate ranges for (default: all)')
    gen_parser.add_argument('--features', nargs='+', help='Features to include (default: common biomechanical features)')
    gen_parser.add_argument('--method', choices=['iqr', 'percentile'], default='iqr',
                          help='Method for computing bounds (default: iqr)')
    gen_parser.add_argument('--iqr-multiplier', type=float, default=2.0,
                          help='IQR multiplier for bounds (default: 2.0)')
    gen_parser.add_argument('--update', action='store_true',
                          help='Update the ranges file instead of printing to stdout')
    gen_parser.add_argument('--ranges', help='Path to ranges YAML file (default: default_ranges.yaml)')

    # Show command
    show_parser = subparsers.add_parser('show', help='Show ranges for a task')
    show_parser.add_argument('--task', required=True, help='Task name to show')
    show_parser.add_argument('--ranges', help='Path to ranges YAML file')

    # List command
    list_parser = subparsers.add_parser('list', help='List tasks with defined ranges')
    list_parser.add_argument('--ranges', help='Path to ranges YAML file')

    # Widen command
    widen_parser = subparsers.add_parser('widen', help='Widen ranges for specific features')
    widen_parser.add_argument('--features', nargs='+', required=True,
                             help='Features to widen (required)')
    widen_parser.add_argument('--tasks', nargs='+',
                             help='Tasks to apply to (default: all tasks)')
    widen_parser.add_argument('--percent', type=float,
                             help='Percentage to expand range on each side (e.g., 10 = 10%%)')
    widen_parser.add_argument('--absolute', type=float,
                             help='Absolute amount to expand on each side (e.g., 0.05)')
    widen_parser.add_argument('--ranges', help='Path to ranges YAML file (default: default_ranges.yaml)')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete tasks from ranges file')
    delete_parser.add_argument('--tasks', nargs='+', required=True,
                              help='Tasks to delete (required)')
    delete_parser.add_argument('--ranges', help='Path to ranges YAML file (default: default_ranges.yaml)')

    args = parser.parse_args()

    if args.command == 'generate':
        return cmd_generate(args)
    elif args.command == 'show':
        return cmd_show(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'widen':
        return cmd_widen(args)
    elif args.command == 'delete':
        return cmd_delete(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
