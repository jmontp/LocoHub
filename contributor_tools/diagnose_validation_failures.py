#!/usr/bin/env python3
"""
Diagnose Validation Failures - Show under/over estimates by task/feature/phase

Analyzes a dataset against validation ranges and reports which features are
failing and whether values are under or over the bounds.

Usage:
    python diagnose_validation_failures.py dataset.parquet
    python diagnose_validation_failures.py dataset.parquet --ranges custom_ranges.yaml
    python diagnose_validation_failures.py dataset.parquet --task level_walking
    python diagnose_validation_failures.py dataset.parquet --top 10  # Show top 10 failing features

Near-miss analysis (identify strides that barely fail):
    python diagnose_validation_failures.py dataset.parquet --flag-marginal
    python diagnose_validation_failures.py dataset.parquet --flag-marginal --export-review
    python diagnose_validation_failures.py dataset.parquet --flag-marginal --max-zscore 2.0 --max-phases 1
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import numpy as np
import pandas as pd

# Ensure repository root and src/ are importable
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from internal.config_management.config_manager import ValidationConfigManager as ConfigManager
from locohub import LocomotionData
from contributor_tools.common.near_miss_analysis import (
    compute_clean_statistics,
    identify_marginal_failures,
    generate_candidate_ranges_yaml,
    print_marginal_summary,
)


def analyze_failures(
    locomotion_data: LocomotionData,
    config_manager: ConfigManager,
    task_filter: str = None,
    feature_filter: str = None,
    export_details: bool = False
) -> Tuple[Dict[str, Any], List[Dict]]:
    """
    Analyze validation failures and categorize as under/over bounds.

    Returns:
        Tuple of (results dict, failure_records list for CSV export)
    """
    df = locomotion_data.df
    features = locomotion_data.features

    tasks = locomotion_data.get_tasks()
    if task_filter:
        tasks = [t for t in tasks if t == task_filter]

    results = {}
    failure_records = []  # For CSV export

    for task in tasks:
        task_df = df[df['task'] == task].copy()
        task_df.reset_index(drop=True, inplace=True)

        n_strides = len(task_df) // 150
        if n_strides == 0:
            continue

        # Get validation ranges for this task
        # Returns {phase_int: {var_name: {min, max}}}
        task_ranges = config_manager.get_task_data(task)
        if not task_ranges:
            continue

        task_results = {
            'total_strides': n_strides,
            'features': {}
        }

        # Reshape data to 3D: (strides, phases, features)
        data_3d = task_df[features].values.reshape(n_strides, 150, len(features))
        feature_to_idx = {f: i for i, f in enumerate(features)}

        for phase_pct, phase_ranges in task_ranges.items():
            phase_pct = int(phase_pct)
            # Convert percentage (0-100) to data index (0-149)
            phase_idx = round(phase_pct / 100 * 149)

            for var_name, var_range in phase_ranges.items():
                if var_name not in feature_to_idx:
                    continue

                # Apply feature filter if specified
                if feature_filter and var_name != feature_filter:
                    continue

                var_idx = feature_to_idx[var_name]
                min_val = var_range.get('min')
                max_val = var_range.get('max')

                if min_val is None or max_val is None:
                    continue

                # Get all values at this phase for this variable
                values = data_3d[:, phase_idx, var_idx]
                valid_mask = np.isfinite(values)

                # Get stride indices for valid values
                valid_indices = np.where(valid_mask)[0]
                valid_values = values[valid_mask]

                if len(valid_values) == 0:
                    continue

                # Count under/over violations
                under_mask = valid_values < min_val
                over_mask = valid_values > max_val

                n_under = np.sum(under_mask)
                n_over = np.sum(over_mask)

                if n_under == 0 and n_over == 0:
                    continue

                # Calculate statistics for failures
                under_values = valid_values[under_mask] if n_under > 0 else np.array([])
                over_values = valid_values[over_mask] if n_over > 0 else np.array([])

                # Export detailed stride-level failures if requested
                if export_details:
                    under_indices = valid_indices[under_mask]
                    over_indices = valid_indices[over_mask]

                    for idx, val in zip(under_indices, under_values):
                        # Get subject/step info from the stride
                        row_start = idx * 150
                        subject = task_df.iloc[row_start]['subject']
                        step = task_df.iloc[row_start]['step']
                        failure_records.append({
                            'task': task,
                            'feature': var_name,
                            'phase': phase_idx,
                            'phase_pct': phase_pct,
                            'stride_idx': int(idx),
                            'subject': subject,
                            'step': step,
                            'violation': 'under',
                            'actual_value': float(val),
                            'bound_min': min_val,
                            'bound_max': max_val,
                            'deficit': float(min_val - val)
                        })

                    for idx, val in zip(over_indices, over_values):
                        row_start = idx * 150
                        subject = task_df.iloc[row_start]['subject']
                        step = task_df.iloc[row_start]['step']
                        failure_records.append({
                            'task': task,
                            'feature': var_name,
                            'phase': phase_idx,
                            'phase_pct': phase_pct,
                            'stride_idx': int(idx),
                            'subject': subject,
                            'step': step,
                            'violation': 'over',
                            'actual_value': float(val),
                            'bound_min': min_val,
                            'bound_max': max_val,
                            'excess': float(val - max_val)
                        })

                if var_name not in task_results['features']:
                    task_results['features'][var_name] = {
                        'phases': {},
                        'total_under': 0,
                        'total_over': 0,
                        'bounds': {'min': min_val, 'max': max_val}
                    }

                phase_info = {
                    'n_under': int(n_under),
                    'n_over': int(n_over),
                    'bounds': {'min': min_val, 'max': max_val}
                }

                if n_under > 0:
                    phase_info['under_stats'] = {
                        'min_value': float(np.min(under_values)),
                        'mean_value': float(np.mean(under_values)),
                        'max_value': float(np.max(under_values)),
                        'deficit': float(min_val - np.min(under_values))
                    }

                if n_over > 0:
                    phase_info['over_stats'] = {
                        'min_value': float(np.min(over_values)),
                        'mean_value': float(np.mean(over_values)),
                        'max_value': float(np.max(over_values)),
                        'excess': float(np.max(over_values) - max_val)
                    }

                task_results['features'][var_name]['phases'][phase_pct] = phase_info
                task_results['features'][var_name]['total_under'] += n_under
                task_results['features'][var_name]['total_over'] += n_over

        results[task] = task_results

    return results, failure_records


def print_report(results: Dict[str, Any], top_n: int = None):
    """Print a human-readable report of validation failures."""

    if not results:
        print("No validation failures found!")
        return

    # Collect all failures for ranking
    all_failures = []

    for task, task_data in results.items():
        print(f"\n{'='*60}")
        print(f"TASK: {task} ({task_data['total_strides']} strides)")
        print('='*60)

        if not task_data['features']:
            print("  No failures for this task.")
            continue

        # Sort features by total failures
        sorted_features = sorted(
            task_data['features'].items(),
            key=lambda x: x[1]['total_under'] + x[1]['total_over'],
            reverse=True
        )

        if top_n:
            sorted_features = sorted_features[:top_n]

        for var_name, var_data in sorted_features:
            total_failures = var_data['total_under'] + var_data['total_over']
            failure_rate = total_failures / task_data['total_strides'] * 100

            all_failures.append({
                'task': task,
                'feature': var_name,
                'under': var_data['total_under'],
                'over': var_data['total_over'],
                'total': total_failures,
                'rate': failure_rate
            })

            print(f"\n  {var_name}:")
            print(f"    Total failures: {total_failures} ({failure_rate:.1f}%)")
            print(f"    Under min: {var_data['total_under']}, Over max: {var_data['total_over']}")

            # Show phase breakdown for top phases
            sorted_phases = sorted(
                var_data['phases'].items(),
                key=lambda x: x[1]['n_under'] + x[1]['n_over'],
                reverse=True
            )[:3]  # Top 3 phases

            for phase_idx, phase_data in sorted_phases:
                phase_pct = phase_idx / 149 * 100
                bounds = phase_data['bounds']

                print(f"    Phase {phase_idx} ({phase_pct:.0f}%): bounds=[{bounds['min']:.4f}, {bounds['max']:.4f}]")

                if phase_data['n_under'] > 0:
                    stats = phase_data['under_stats']
                    print(f"      UNDER ({phase_data['n_under']}): actual min={stats['min_value']:.4f}, "
                          f"deficit={stats['deficit']:.4f}")

                if phase_data['n_over'] > 0:
                    stats = phase_data['over_stats']
                    print(f"      OVER ({phase_data['n_over']}): actual max={stats['max_value']:.4f}, "
                          f"excess={stats['excess']:.4f}")

    # Print summary table
    print(f"\n{'='*60}")
    print("SUMMARY: Top Failing Features Across All Tasks")
    print('='*60)

    sorted_all = sorted(all_failures, key=lambda x: x['total'], reverse=True)[:20]

    print(f"\n{'Task':<20} {'Feature':<45} {'Under':>6} {'Over':>6} {'Total':>6} {'Rate':>7}")
    print("-" * 95)
    for f in sorted_all:
        print(f"{f['task']:<20} {f['feature']:<45} {f['under']:>6} {f['over']:>6} {f['total']:>6} {f['rate']:>6.1f}%")


def suggest_new_bounds(results: Dict[str, Any]):
    """Suggest new bounds based on actual data values."""

    print(f"\n{'='*60}")
    print("SUGGESTED BOUND ADJUSTMENTS")
    print("(Copy these to your validation ranges YAML)")
    print('='*60)

    for task, task_data in results.items():
        suggestions = []

        for var_name, var_data in task_data['features'].items():
            for phase_idx, phase_data in var_data['phases'].items():
                bounds = phase_data['bounds']

                if phase_data['n_under'] > 0:
                    stats = phase_data['under_stats']
                    # Suggest expanding min by 10% margin
                    new_min = stats['min_value'] - abs(stats['min_value']) * 0.1
                    suggestions.append({
                        'var': var_name,
                        'phase': phase_idx,
                        'type': 'min',
                        'old': bounds['min'],
                        'new': new_min,
                        'count': phase_data['n_under']
                    })

                if phase_data['n_over'] > 0:
                    stats = phase_data['over_stats']
                    # Suggest expanding max by 10% margin
                    new_max = stats['max_value'] + abs(stats['max_value']) * 0.1
                    suggestions.append({
                        'var': var_name,
                        'phase': phase_idx,
                        'type': 'max',
                        'old': bounds['max'],
                        'new': new_max,
                        'count': phase_data['n_over']
                    })

        if suggestions:
            print(f"\n{task}:")
            # Sort by count
            suggestions.sort(key=lambda x: x['count'], reverse=True)
            for s in suggestions[:10]:  # Top 10
                print(f"  Phase {s['phase']}, {s['var']}: {s['type']} {s['old']:.4f} -> {s['new']:.4f} ({s['count']} failures)")


def plot_failures(
    locomotion_data: LocomotionData,
    config_manager: ConfigManager,
    task: str,
    feature: str,
    output_path: Optional[str] = None
):
    """
    Plot passing vs failing strides for a specific task/feature.

    Shows all strides with passing in green and failing in red,
    with validation bounds as shaded regions.
    """
    import matplotlib.pyplot as plt

    df = locomotion_data.df
    features = locomotion_data.features

    task_df = df[df['task'] == task].copy()
    task_df.reset_index(drop=True, inplace=True)

    n_strides = len(task_df) // 150
    if n_strides == 0:
        print(f"No strides found for task: {task}")
        return

    if feature not in features:
        print(f"Feature not found: {feature}")
        return

    # Get validation ranges
    task_ranges = config_manager.get_task_data(task)

    # Reshape data
    feature_idx = features.index(feature)
    data_3d = task_df[features].values.reshape(n_strides, 150, len(features))
    feature_data = data_3d[:, :, feature_idx]  # Shape: (n_strides, 150)

    # Determine which strides fail at each phase
    phase_x = np.linspace(0, 100, 150)

    # Collect bounds and failing stride indices
    bounds_min = np.full(150, np.nan)
    bounds_max = np.full(150, np.nan)
    failing_strides = set()

    for phase_idx, phase_ranges in task_ranges.items():
        phase_idx = int(phase_idx)
        if feature in phase_ranges:
            var_range = phase_ranges[feature]
            min_val = var_range.get('min')
            max_val = var_range.get('max')
            if min_val is not None and max_val is not None:
                bounds_min[phase_idx] = min_val
                bounds_max[phase_idx] = max_val

                # Check which strides fail at this phase
                values = feature_data[:, phase_idx]
                for stride_idx, val in enumerate(values):
                    if np.isfinite(val) and (val < min_val or val > max_val):
                        failing_strides.add(stride_idx)

    passing_strides = set(range(n_strides)) - failing_strides

    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left plot: Passing strides
    ax_pass = axes[0]
    ax_pass.set_title(f"PASSING ({len(passing_strides)} strides)", fontsize=12, fontweight='bold', color='green')

    for stride_idx in passing_strides:
        ax_pass.plot(phase_x, feature_data[stride_idx, :], color='green', alpha=0.3, linewidth=0.5)

    # Plot bounds
    valid_bounds = ~np.isnan(bounds_min)
    if np.any(valid_bounds):
        ax_pass.fill_between(phase_x, bounds_min, bounds_max,
                            where=valid_bounds, alpha=0.2, color='blue', label='Valid range')
        ax_pass.plot(phase_x[valid_bounds], bounds_min[valid_bounds], 'b--', linewidth=1, alpha=0.7)
        ax_pass.plot(phase_x[valid_bounds], bounds_max[valid_bounds], 'b--', linewidth=1, alpha=0.7)

    ax_pass.set_xlabel('Gait Cycle (%)')
    ax_pass.set_ylabel(feature)
    ax_pass.set_xlim(0, 100)
    ax_pass.grid(True, alpha=0.3)

    # Right plot: Failing strides
    ax_fail = axes[1]
    ax_fail.set_title(f"FAILING ({len(failing_strides)} strides)", fontsize=12, fontweight='bold', color='red')

    for stride_idx in failing_strides:
        ax_fail.plot(phase_x, feature_data[stride_idx, :], color='red', alpha=0.3, linewidth=0.5)

    # Plot bounds
    if np.any(valid_bounds):
        ax_fail.fill_between(phase_x, bounds_min, bounds_max,
                            where=valid_bounds, alpha=0.2, color='blue', label='Valid range')
        ax_fail.plot(phase_x[valid_bounds], bounds_min[valid_bounds], 'b--', linewidth=1, alpha=0.7)
        ax_fail.plot(phase_x[valid_bounds], bounds_max[valid_bounds], 'b--', linewidth=1, alpha=0.7)

    ax_fail.set_xlabel('Gait Cycle (%)')
    ax_fail.set_ylabel(feature)
    ax_fail.set_xlim(0, 100)
    ax_fail.grid(True, alpha=0.3)

    # Match y-axis limits
    y_min = min(ax_pass.get_ylim()[0], ax_fail.get_ylim()[0])
    y_max = max(ax_pass.get_ylim()[1], ax_fail.get_ylim()[1])
    ax_pass.set_ylim(y_min, y_max)
    ax_fail.set_ylim(y_min, y_max)

    fig.suptitle(f"{task} - {feature}\n({n_strides} total strides)", fontsize=14, fontweight='bold')
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Saved plot: {output_path}")
        plt.close()
    else:
        plt.show()


def plot_all_failing_features(
    locomotion_data: LocomotionData,
    config_manager: ConfigManager,
    results: Dict[str, Any],
    output_dir: Optional[str] = None,
    top_n: int = 10
):
    """Plot top failing features for each task."""
    import matplotlib.pyplot as plt

    for task, task_data in results.items():
        if not task_data['features']:
            continue

        # Sort features by total failures
        sorted_features = sorted(
            task_data['features'].items(),
            key=lambda x: x[1]['total_under'] + x[1]['total_over'],
            reverse=True
        )[:top_n]

        for var_name, var_data in sorted_features:
            if output_dir:
                output_path = Path(output_dir) / f"{task}_{var_name}_failures.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = None

            plot_failures(locomotion_data, config_manager, task, var_name, str(output_path) if output_path else None)


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose validation failures - show under/over estimates",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("dataset", help="Path to parquet dataset")
    parser.add_argument("--ranges", default="validation_ranges/default_ranges.yaml",
                       help="Validation ranges YAML file")
    parser.add_argument("--task", help="Filter to specific task")
    parser.add_argument("--top", type=int, help="Show only top N failing features per task")
    parser.add_argument("--suggest", action="store_true",
                       help="Suggest new bounds based on actual values")
    parser.add_argument("--export-failures", type=str,
                       help="Export failing stride details to CSV file")
    parser.add_argument("--feature", type=str,
                       help="Filter to specific feature (e.g., knee_flexion_angle_ipsi_rad)")
    parser.add_argument("--plot", action="store_true",
                       help="Generate plots showing passing vs failing strides")
    parser.add_argument("--output-dir", type=str,
                       help="Directory to save plots (default: show interactively)")

    # Near-miss analysis arguments
    parser.add_argument("--flag-marginal", action="store_true",
                       help="Identify strides that barely fail (candidates for range review)")
    parser.add_argument("--export-review", action="store_true",
                       help="Export candidate ranges YAML for review (use with --flag-marginal)")
    parser.add_argument("--max-zscore", type=float, default=2.5,
                       help="Max z-score from clean mean for marginal failures (default: 2.5)")
    parser.add_argument("--max-phases", type=int, default=2,
                       help="Max phases a stride can fail to be marginal (default: 2)")

    args = parser.parse_args()

    # Validate inputs
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Error: Dataset not found: {args.dataset}")
        return 1

    ranges_path = Path(args.ranges)
    if not ranges_path.exists():
        ranges_path = Path(__file__).parent / args.ranges
        if not ranges_path.exists():
            print(f"Error: Validation ranges not found: {args.ranges}")
            return 1

    print(f"Loading dataset: {dataset_path.name}")
    locomotion_data = LocomotionData(str(dataset_path))

    print(f"Loading ranges: {ranges_path.name}")
    config_manager = ConfigManager(ranges_path)

    print("Analyzing validation failures...")
    export_details = args.export_failures is not None
    results, failure_records = analyze_failures(
        locomotion_data,
        config_manager,
        task_filter=args.task,
        feature_filter=args.feature,
        export_details=export_details
    )

    print_report(results, args.top)

    if args.suggest:
        suggest_new_bounds(results)

    if args.export_failures:
        if failure_records:
            export_df = pd.DataFrame(failure_records)
            export_df.to_csv(args.export_failures, index=False)
            print(f"\nExported {len(failure_records)} failure records to: {args.export_failures}")
        else:
            print("\nNo failures to export.")

    if args.plot:
        if args.feature and args.task:
            # Plot single feature for single task
            output_path = None
            if args.output_dir:
                Path(args.output_dir).mkdir(parents=True, exist_ok=True)
                output_path = str(Path(args.output_dir) / f"{args.task}_{args.feature}_failures.png")
            plot_failures(locomotion_data, config_manager, args.task, args.feature, output_path)
        elif args.feature:
            # Plot single feature for all tasks
            for task in results.keys():
                output_path = None
                if args.output_dir:
                    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
                    output_path = str(Path(args.output_dir) / f"{task}_{args.feature}_failures.png")
                plot_failures(locomotion_data, config_manager, task, args.feature, output_path)
        else:
            # Plot top failing features
            plot_all_failing_features(
                locomotion_data,
                config_manager,
                results,
                output_dir=args.output_dir,
                top_n=args.top if args.top else 5
            )

    # Near-miss analysis
    if args.flag_marginal:
        import yaml

        print("\n" + "="*60)
        print("NEAR-MISS ANALYSIS")
        print("="*60)
        print(f"Thresholds: max_zscore={args.max_zscore}, max_phases={args.max_phases}")

        # Load current ranges for export
        with open(ranges_path, 'r') as f:
            current_ranges = yaml.safe_load(f)

        df = locomotion_data.df
        features = locomotion_data.features
        tasks = [args.task] if args.task else locomotion_data.get_tasks()

        all_suggestions = {}

        for task in tasks:
            task_df = df[df['task'] == task]
            n_strides = len(task_df) // 150
            if n_strides == 0:
                continue

            # Count total failing strides for this task
            total_failing = 0
            if task in results:
                # A stride fails if it fails any feature at any phase
                # Use the results we already computed
                task_results = results[task]
                # Approximate: count unique failing strides would require recomputation
                # For now, just show the marginal analysis
                total_failing = n_strides - int(n_strides * 0.5)  # Placeholder

            # Compute clean statistics
            clean_stats = compute_clean_statistics(
                df, task, features, config_manager
            )

            if not clean_stats:
                print(f"\n{task}: Not enough clean data for near-miss analysis")
                continue

            # Identify marginal failures
            marginal_failures, suggestions = identify_marginal_failures(
                df, task, features, config_manager, clean_stats,
                max_phases_failed=args.max_phases,
                max_zscore=args.max_zscore
            )

            # Print summary
            print_marginal_summary(
                marginal_failures, suggestions, task,
                n_strides, total_failing
            )

            # Collect suggestions for export
            if suggestions:
                all_suggestions[task] = suggestions

        # Export candidate ranges if requested
        if args.export_review and all_suggestions:
            import copy

            dataset_name = dataset_path.stem
            output_path = Path(f"review_{dataset_name}_candidate_ranges.yaml")

            # Apply all suggestions to a single combined ranges file
            candidate_ranges = copy.deepcopy(current_ranges)

            for task, task_suggestions in all_suggestions.items():
                if task in candidate_ranges.get('tasks', {}):
                    task_data = candidate_ranges['tasks'][task]
                    if 'phases' in task_data:
                        for var_name, phase_suggestions in task_suggestions.items():
                            for key, suggestion in phase_suggestions.items():
                                phase_idx = suggestion.phase
                                direction = suggestion.direction
                                if phase_idx in task_data['phases']:
                                    if var_name in task_data['phases'][phase_idx]:
                                        # Convert to Python float to avoid numpy serialization issues
                                        task_data['phases'][phase_idx][var_name][direction] = float(round(suggestion.suggested_bound, 6))

            # Write combined file
            with open(output_path, 'w') as f:
                f.write(f"# Candidate Validation Ranges\n")
                f.write(f"# Suggested bounds from near-miss analysis applied to: {', '.join(all_suggestions.keys())}\n")
                f.write(f"#\n")
                f.write(f"# Test with:\n")
                f.write(f"#   python contributor_tools/quick_validation_check.py {dataset_path} --ranges {output_path}\n")
                f.write(f"#\n")
                f.write(f"# If satisfied, copy to validation_ranges/default_ranges.yaml\n")
                f.write("#\n")
                yaml.dump(candidate_ranges, f, default_flow_style=False, sort_keys=False)

            print(f"\n✅ Exported candidate ranges: {output_path}")
            print(f"   Test with: python contributor_tools/quick_validation_check.py {dataset_path} --ranges {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
