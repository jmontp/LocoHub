#!/usr/bin/env python3
"""
Quick Validation Check - Lightweight Text-Only Validation

A fast, text-only validation tool that shows pass/fail statistics without generating plots.
Useful for rapid validation checks during dataset conversion.

Usage:
    python quick_validation_check.py converted_datasets/gtech_2021_phase.parquet
    python quick_validation_check.py dataset.parquet --ranges custom_ranges.yaml
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.validation_engine.validator import Validator


def categorize_features(features: List[str]) -> Dict[str, List[str]]:
    """
    Categorize features by type (kinematics, kinetics, GRF, segments).
    
    Args:
        features: List of feature names
        
    Returns:
        Dictionary with categories as keys and feature lists as values
    """
    categories = {
        'kinematics': [],
        'kinetics': [],
        'grf': [],
        'segments': [],
        'other': []
    }
    
    for feature in features:
        if 'angle' in feature or 'angular_velocity' in feature:
            categories['kinematics'].append(feature)
        elif 'moment' in feature or 'power' in feature:
            categories['kinetics'].append(feature)
        elif 'grf' in feature:
            categories['grf'].append(feature)
        elif 'segment' in feature:
            categories['segments'].append(feature)
        else:
            categories['other'].append(feature)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def print_validation_summary(result: Dict) -> None:
    """
    Print a concise validation summary.
    
    Args:
        result: Validation result dictionary from Validator
    """
    stats = result['stats']
    
    # Header
    print("\n" + "="*70)
    print("QUICK VALIDATION CHECK")
    print("="*70)
    
    # Overall status
    status = "✅ PASSED" if result['passed'] else "❌ FAILED"
    print(f"\nDataset: {stats['dataset']}")
    print(f"Status: {status}")
    print(f"Overall Pass Rate: {stats['pass_rate']:.1%} ({stats['total_strides'] - stats['total_failing_strides']}/{stats['total_strides']} strides)")
    
    # Phase structure
    phase_icon = "✅" if result['phase_valid'] else "❌"
    print(f"\nPhase Structure: {phase_icon} {result['phase_message']}")
    
    # Task breakdown
    print(f"\nTasks Validated: {stats['num_tasks']}")
    
    if result['violations']:
        print("\n" + "-"*70)
        print("TASK-BY-TASK BREAKDOWN")
        print("-"*70)
        
        for task, violations in sorted(result['violations'].items()):
            # Calculate task-specific pass rate
            task_total = sum(len(v) for v in violations.values())
            
            print(f"\n📍 {task.upper()}")
            
            if violations:
                # Categorize failures
                categorized = categorize_features(list(violations.keys()))
                
                for category, features in categorized.items():
                    if features:
                        print(f"\n  {category.title()}:")
                        for feature in sorted(features):
                            if feature in violations:
                                n_failures = len(violations[feature])
                                print(f"    • {feature}: {n_failures} stride failures")
            else:
                print("  ✅ All features passed")
    else:
        print("\n✅ All validations passed!")
    
    # Summary statistics
    print("\n" + "-"*70)
    print("SUMMARY STATISTICS")
    print("-"*70)
    print(f"Total Strides: {stats['total_strides']:,}")
    print(f"Failing Strides: {stats['total_failing_strides']:,}")
    print(f"Pass Rate: {stats['pass_rate']:.1%}")
    print(f"Total Variable Checks: {stats['total_checks']:,}")
    print(f"Total Variable Violations: {stats['total_violations']:,}")
    print(f"Variable Pass Rate: {stats['variable_pass_rate']:.1%}")
    
    print("\n" + "="*70)


def get_failing_features_summary(validator: Validator, dataset_path: str) -> Dict[str, Set[str]]:
    """
    Get a summary of which features are failing across all tasks.
    
    Args:
        validator: Initialized validator instance
        dataset_path: Path to dataset
        
    Returns:
        Dictionary mapping feature names to set of tasks where they fail
    """
    from user_libs.python.locomotion_data import LocomotionData
    
    locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
    tasks = locomotion_data.get_tasks()
    
    feature_failures = {}
    
    for task in tasks:
        failing_features = validator._validate_task_with_failing_features(locomotion_data, task)
        
        # Aggregate by feature
        for stride_idx, failed_vars in failing_features.items():
            for var_name in failed_vars:
                if var_name not in feature_failures:
                    feature_failures[var_name] = set()
                feature_failures[var_name].add(task)
    
    return feature_failures


def main():
    """Main entry point for quick validation check."""
    parser = argparse.ArgumentParser(
        description="Quick validation check - text-only, no plots",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "dataset",
        help="Path to phase-indexed dataset parquet file"
    )
    
    parser.add_argument(
        "--ranges",
        help="Path to validation ranges YAML file (default: default_ranges.yaml)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed feature-by-feature breakdown"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"❌ Error: Dataset file not found: {dataset_path}")
        return 1
    
    # Determine validation ranges file
    if args.ranges:
        ranges_file = Path(args.ranges)
    else:
        ranges_file = Path(__file__).parent / "validation_ranges" / "default_ranges.yaml"
    
    if not ranges_file.exists():
        print(f"❌ Error: Validation ranges file not found: {ranges_file}")
        return 1
    
    print(f"🔍 Validating: {dataset_path.name}")
    print(f"📋 Using ranges: {ranges_file.name}")
    
    try:
        # Initialize validator
        validator = Validator(config_path=ranges_file)
        
        # Run validation
        result = validator.validate(str(dataset_path))
        
        # Print summary
        print_validation_summary(result)
        
        # Optional verbose output
        if args.verbose:
            print("\n" + "="*70)
            print("DETAILED FEATURE ANALYSIS")
            print("="*70)
            
            feature_summary = get_failing_features_summary(validator, str(dataset_path))
            
            if feature_summary:
                categorized = categorize_features(list(feature_summary.keys()))
                
                for category, features in categorized.items():
                    if features:
                        print(f"\n{category.upper()} FAILURES:")
                        for feature in sorted(features):
                            tasks = feature_summary[feature]
                            print(f"  • {feature}: fails in {', '.join(sorted(tasks))}")
            else:
                print("\n✅ No feature failures detected")
        
        # Return exit code based on validation result
        return 0 if result['passed'] else 1
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())