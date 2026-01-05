#!/usr/bin/env python3
"""
Near-Miss Analysis for Validation Ranges

Identifies strides that "barely fail" validation - candidates for range review.
Uses z-scores from clean (passing) data to distinguish minor outliers from
genuinely deviant data.

This module provides shared functionality for:
- diagnose_validation_failures.py (--flag-marginal option)
- Any future tools needing near-miss detection
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


@dataclass
class PhaseStats:
    """Statistics for a feature at a specific phase, computed from clean data."""
    phase: int
    mean: float
    std: float
    n_samples: int
    bound_min: float
    bound_max: float


@dataclass
class MarginalViolation:
    """A single violation that qualifies as marginal (close to bounds)."""
    phase: int
    direction: str  # 'under' or 'over'
    actual_value: float
    bound: float  # The violated bound (min or max)
    zscore: float  # Z-score from clean mean
    deficit_or_excess: float  # How far outside the bound


@dataclass
class MarginalFailure:
    """A stride that barely fails validation - candidate for review."""
    stride_idx: int
    subject: str
    step: int
    task: str
    n_phases_failed: int
    violations: List[MarginalViolation] = field(default_factory=list)
    max_zscore: float = 0.0

    def add_violation(self, violation: MarginalViolation):
        self.violations.append(violation)
        self.max_zscore = max(self.max_zscore, violation.zscore)


@dataclass
class BoundSuggestion:
    """A suggestion to adjust a validation bound based on marginal failures."""
    task: str
    feature: str
    phase: int
    direction: str  # 'min' or 'max'
    current_bound: float
    suggested_bound: float
    n_marginal_failures: int
    avg_zscore: float
    max_zscore: float
    stride_indices: List[int] = field(default_factory=list)


def compute_clean_statistics(
    df: pd.DataFrame,
    task: str,
    features: List[str],
    config_manager: Any,
    n_phases: int = 150,
    min_clean_strides: int = 10
) -> Dict[str, Dict[int, PhaseStats]]:
    """
    Compute mean and std at each validated phase using only passing strides.

    If no strides pass ALL checks, falls back to computing per-feature statistics
    using strides that pass checks for that specific feature only.

    Args:
        df: Full dataframe with task column
        task: Task name to analyze
        features: List of feature column names
        config_manager: ValidationConfigManager with ranges
        n_phases: Number of phases per stride (default 150)
        min_clean_strides: Minimum strides needed for statistics (default 10)

    Returns:
        Dict mapping feature -> phase -> PhaseStats
    """
    task_df = df[df['task'] == task].copy()
    task_df.reset_index(drop=True, inplace=True)

    n_strides = len(task_df) // n_phases
    if n_strides == 0:
        return {}

    task_ranges = config_manager.get_task_data(task)
    if not task_ranges:
        return {}

    # Reshape to 3D: (strides, phases, features)
    data_3d = task_df[features].values.reshape(n_strides, n_phases, len(features))
    feature_to_idx = {f: i for i, f in enumerate(features)}

    # First pass: identify passing strides (pass ALL checks)
    passing_mask = np.ones(n_strides, dtype=bool)

    for phase_idx, phase_ranges in task_ranges.items():
        phase_idx = int(phase_idx)
        for var_name, var_range in phase_ranges.items():
            if var_name not in feature_to_idx:
                continue
            var_idx = feature_to_idx[var_name]
            min_val = var_range.get('min')
            max_val = var_range.get('max')
            if min_val is None or max_val is None:
                continue

            values = data_3d[:, phase_idx, var_idx]
            valid = np.isfinite(values)
            fails = valid & ((values < min_val) | (values > max_val))
            passing_mask &= ~fails

    n_passing = np.sum(passing_mask)

    # If we have enough globally clean strides, use them
    use_global_clean = n_passing >= min_clean_strides

    if use_global_clean:
        clean_data = data_3d[passing_mask]  # Shape: (n_passing, n_phases, n_features)
    else:
        # Fallback: compute per-feature statistics using feature-specific clean strides
        clean_data = None

    # Second pass: compute stats

    stats: Dict[str, Dict[int, PhaseStats]] = {}

    for phase_idx, phase_ranges in task_ranges.items():
        phase_idx = int(phase_idx)
        for var_name, var_range in phase_ranges.items():
            if var_name not in feature_to_idx:
                continue
            var_idx = feature_to_idx[var_name]
            min_val = var_range.get('min')
            max_val = var_range.get('max')
            if min_val is None or max_val is None:
                continue

            if use_global_clean:
                # Use globally clean strides
                values = clean_data[:, phase_idx, var_idx]
            else:
                # Fallback: compute per-feature clean strides
                # A stride is "clean for this feature" if it passes all checks for this feature
                feature_passing_mask = np.ones(n_strides, dtype=bool)
                for check_phase, check_ranges in task_ranges.items():
                    check_phase = int(check_phase)
                    if var_name in check_ranges:
                        check_range = check_ranges[var_name]
                        check_min = check_range.get('min')
                        check_max = check_range.get('max')
                        if check_min is not None and check_max is not None:
                            check_vals = data_3d[:, check_phase, var_idx]
                            check_valid = np.isfinite(check_vals)
                            check_fails = check_valid & ((check_vals < check_min) | (check_vals > check_max))
                            feature_passing_mask &= ~check_fails

                n_feature_passing = np.sum(feature_passing_mask)
                if n_feature_passing < min_clean_strides:
                    # Not enough clean data even for this feature - use all data
                    # This means z-scores will be less meaningful but we can still proceed
                    values = data_3d[:, phase_idx, var_idx]
                else:
                    values = data_3d[feature_passing_mask, phase_idx, var_idx]

            valid_values = values[np.isfinite(values)]

            if len(valid_values) < min_clean_strides:
                continue

            if var_name not in stats:
                stats[var_name] = {}

            stats[var_name][phase_idx] = PhaseStats(
                phase=phase_idx,
                mean=float(np.mean(valid_values)),
                std=float(np.std(valid_values)),
                n_samples=len(valid_values),
                bound_min=min_val,
                bound_max=max_val
            )

    return stats


def identify_marginal_failures(
    df: pd.DataFrame,
    task: str,
    features: List[str],
    config_manager: Any,
    clean_stats: Dict[str, Dict[int, PhaseStats]],
    max_phases_failed: int = 2,
    max_zscore: float = 2.5,
    n_phases: int = 150
) -> Tuple[List[MarginalFailure], Dict[str, Dict[int, BoundSuggestion]]]:
    """
    Identify strides that barely fail validation.

    A stride is a "marginal failure" if:
    1. It fails at <= max_phases_failed phase checkpoints
    2. All violations have z-score < max_zscore from clean mean

    Args:
        df: Full dataframe
        task: Task name
        features: Feature column names
        config_manager: ValidationConfigManager
        clean_stats: Output from compute_clean_statistics
        max_phases_failed: Maximum phases a stride can fail to be marginal
        max_zscore: Maximum z-score for a violation to be marginal
        n_phases: Phases per stride

    Returns:
        Tuple of (list of MarginalFailure, dict of BoundSuggestion by feature/phase)
    """
    task_df = df[df['task'] == task].copy()
    task_df.reset_index(drop=True, inplace=True)

    n_strides = len(task_df) // n_phases
    if n_strides == 0:
        return [], {}

    task_ranges = config_manager.get_task_data(task)
    if not task_ranges:
        return [], {}

    data_3d = task_df[features].values.reshape(n_strides, n_phases, len(features))
    feature_to_idx = {f: i for i, f in enumerate(features)}

    # Track violations per stride
    stride_violations: Dict[int, List[MarginalViolation]] = {i: [] for i in range(n_strides)}

    # Track suggestions by feature/phase
    suggestions: Dict[str, Dict[int, Dict[str, List]]] = {}  # feature -> phase -> direction -> [values, zscores, indices]

    for phase_idx, phase_ranges in task_ranges.items():
        phase_idx = int(phase_idx)

        for var_name, var_range in phase_ranges.items():
            if var_name not in feature_to_idx:
                continue
            if var_name not in clean_stats or phase_idx not in clean_stats[var_name]:
                continue

            var_idx = feature_to_idx[var_name]
            min_val = var_range.get('min')
            max_val = var_range.get('max')
            if min_val is None or max_val is None:
                continue

            phase_stat = clean_stats[var_name][phase_idx]
            values = data_3d[:, phase_idx, var_idx]

            for stride_idx in range(n_strides):
                val = values[stride_idx]
                if not np.isfinite(val):
                    continue

                # Check for violation
                if val < min_val:
                    deficit = min_val - val
                    # Use minimum std based on the deficit to avoid huge z-scores for tight bounds
                    # If bounds are very tight (e.g., "must be zero"), use deficit as basis
                    range_size = abs(phase_stat.bound_max - phase_stat.bound_min)
                    min_std = max(abs(deficit) * 0.5, range_size * 0.1, 1e-4)
                    effective_std = max(phase_stat.std, min_std)
                    zscore = abs(val - phase_stat.mean) / effective_std

                    violation = MarginalViolation(
                        phase=phase_idx,
                        direction='under',
                        actual_value=val,
                        bound=min_val,
                        zscore=zscore,
                        deficit_or_excess=deficit
                    )
                    stride_violations[stride_idx].append(violation)

                    # Track for suggestion
                    if var_name not in suggestions:
                        suggestions[var_name] = {}
                    if phase_idx not in suggestions[var_name]:
                        suggestions[var_name][phase_idx] = {'min': {'values': [], 'zscores': [], 'indices': []},
                                                            'max': {'values': [], 'zscores': [], 'indices': []}}
                    suggestions[var_name][phase_idx]['min']['values'].append(val)
                    suggestions[var_name][phase_idx]['min']['zscores'].append(zscore)
                    suggestions[var_name][phase_idx]['min']['indices'].append(stride_idx)

                elif val > max_val:
                    excess = val - max_val
                    # Use minimum std based on the excess to avoid huge z-scores for tight bounds
                    range_size = abs(phase_stat.bound_max - phase_stat.bound_min)
                    min_std = max(abs(excess) * 0.5, range_size * 0.1, 1e-4)
                    effective_std = max(phase_stat.std, min_std)
                    zscore = abs(val - phase_stat.mean) / effective_std

                    violation = MarginalViolation(
                        phase=phase_idx,
                        direction='over',
                        actual_value=val,
                        bound=max_val,
                        zscore=zscore,
                        deficit_or_excess=excess
                    )
                    stride_violations[stride_idx].append(violation)

                    if var_name not in suggestions:
                        suggestions[var_name] = {}
                    if phase_idx not in suggestions[var_name]:
                        suggestions[var_name][phase_idx] = {'min': {'values': [], 'zscores': [], 'indices': []},
                                                            'max': {'values': [], 'zscores': [], 'indices': []}}
                    suggestions[var_name][phase_idx]['max']['values'].append(val)
                    suggestions[var_name][phase_idx]['max']['zscores'].append(zscore)
                    suggestions[var_name][phase_idx]['max']['indices'].append(stride_idx)

    # Filter to marginal failures
    marginal_failures = []

    for stride_idx, violations in stride_violations.items():
        if len(violations) == 0:
            continue

        # Count unique phases failed
        phases_failed = len(set(v.phase for v in violations))

        # Check if all violations are marginal
        all_marginal = all(v.zscore <= max_zscore for v in violations)

        if phases_failed <= max_phases_failed and all_marginal:
            row_start = stride_idx * n_phases
            subject = task_df.iloc[row_start]['subject']
            step = task_df.iloc[row_start]['step']

            failure = MarginalFailure(
                stride_idx=stride_idx,
                subject=str(subject),
                step=int(step),
                task=task,
                n_phases_failed=phases_failed
            )
            for v in violations:
                failure.add_violation(v)

            marginal_failures.append(failure)

    # Build bound suggestions from marginal failures only
    bound_suggestions: Dict[str, Dict[int, BoundSuggestion]] = {}
    marginal_indices = set(f.stride_idx for f in marginal_failures)

    for var_name, phase_data in suggestions.items():
        for phase_idx, direction_data in phase_data.items():
            for direction, data in direction_data.items():
                # Filter to only marginal failures
                marginal_mask = [i in marginal_indices for i in data['indices']]
                marginal_values = [v for v, m in zip(data['values'], marginal_mask) if m]
                marginal_zscores = [z for z, m in zip(data['zscores'], marginal_mask) if m]
                marginal_idxs = [i for i, m in zip(data['indices'], marginal_mask) if m]

                if len(marginal_values) == 0:
                    continue

                # Get current bound
                phase_stat = clean_stats[var_name][phase_idx]
                current_bound = phase_stat.bound_min if direction == 'min' else phase_stat.bound_max

                # Suggest new bound with 5% margin
                if direction == 'min':
                    extreme_value = min(marginal_values)
                    margin = abs(extreme_value) * 0.05 if extreme_value != 0 else 0.01
                    suggested = extreme_value - margin
                else:
                    extreme_value = max(marginal_values)
                    margin = abs(extreme_value) * 0.05 if extreme_value != 0 else 0.01
                    suggested = extreme_value + margin

                suggestion = BoundSuggestion(
                    task=task,
                    feature=var_name,
                    phase=phase_idx,
                    direction=direction,
                    current_bound=current_bound,
                    suggested_bound=suggested,
                    n_marginal_failures=len(marginal_values),
                    avg_zscore=float(np.mean(marginal_zscores)),
                    max_zscore=float(np.max(marginal_zscores)),
                    stride_indices=marginal_idxs
                )

                if var_name not in bound_suggestions:
                    bound_suggestions[var_name] = {}

                # Key by phase and direction
                key = f"{phase_idx}_{direction}"
                bound_suggestions[var_name][key] = suggestion

    return marginal_failures, bound_suggestions


def generate_candidate_ranges_yaml(
    current_ranges: dict,
    suggestions: Dict[str, Dict[str, BoundSuggestion]],
    task: str,
    output_path: Path
) -> None:
    """
    Generate a candidate ranges YAML file with suggested values applied.

    The output file is a complete ranges file with suggested bounds already
    applied. Run validation against this file to see the impact before
    deciding to accept.

    Args:
        current_ranges: Current ranges dict (from YAML)
        suggestions: Bound suggestions from identify_marginal_failures
        task: Task name these suggestions apply to
        output_path: Where to write the candidate file
    """
    import yaml
    import copy

    # Deep copy to avoid modifying original
    candidate_ranges = copy.deepcopy(current_ranges)

    # Apply suggestions to the task
    if task in candidate_ranges.get('tasks', {}):
        task_data = candidate_ranges['tasks'][task]
        if 'phases' in task_data:
            for var_name, phase_suggestions in suggestions.items():
                for key, suggestion in phase_suggestions.items():
                    phase_idx = suggestion.phase
                    direction = suggestion.direction

                    if phase_idx in task_data['phases']:
                        if var_name in task_data['phases'][phase_idx]:
                            # Apply the suggested bound
                            task_data['phases'][phase_idx][var_name][direction] = round(suggestion.suggested_bound, 6)

    # Write to file with header comment
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(f"# Candidate Validation Ranges - {task}\n")
        f.write(f"# Suggested bounds from near-miss analysis have been applied.\n")
        f.write(f"# Run validation against this file to see the impact:\n")
        f.write(f"#   python contributor_tools/quick_validation_check.py dataset.parquet --ranges {output_path.name}\n")
        f.write(f"# If satisfied, copy to validation_ranges/default_ranges.yaml\n")
        f.write("#\n")
        yaml.dump(candidate_ranges, f, default_flow_style=False, sort_keys=False)


def print_marginal_summary(
    marginal_failures: List[MarginalFailure],
    suggestions: Dict[str, Dict[str, BoundSuggestion]],
    task: str,
    total_strides: int,
    total_failing: int
):
    """Print a summary of marginal failures for a task."""

    print(f"\n{'='*60}")
    print(f"NEAR-MISS ANALYSIS: {task}")
    print(f"{'='*60}")
    print(f"Total strides: {total_strides}")
    print(f"Total failing: {total_failing} ({100*total_failing/total_strides:.1f}%)")
    print(f"Marginal failures: {len(marginal_failures)} ({100*len(marginal_failures)/total_strides:.1f}%)")

    if not marginal_failures:
        print("\nNo marginal failures found - all failures are significant deviations.")
        return

    print(f"\nThese {len(marginal_failures)} strides fail by small margins and are candidates for review.")

    # Summarize by feature
    print(f"\n{'-'*60}")
    print("SUGGESTED BOUND ADJUSTMENTS")
    print(f"{'-'*60}")

    # Flatten and sort suggestions by number of affected strides
    all_suggestions = []
    for var_name, phase_suggestions in suggestions.items():
        for key, suggestion in phase_suggestions.items():
            all_suggestions.append(suggestion)

    all_suggestions.sort(key=lambda s: s.n_marginal_failures, reverse=True)

    if not all_suggestions:
        print("No bound adjustments suggested.")
        return

    print(f"\n{'Feature':<45} {'Phase':>6} {'Dir':>4} {'Count':>6} {'Avg σ':>6} {'Current':>10} {'Suggest':>10}")
    print("-" * 95)

    for s in all_suggestions[:20]:  # Top 20
        phase_pct = s.phase / 149 * 100
        print(f"{s.feature:<45} {phase_pct:>5.0f}% {s.direction:>4} {s.n_marginal_failures:>6} "
              f"{s.avg_zscore:>6.2f} {s.current_bound:>10.4f} {s.suggested_bound:>10.4f}")
