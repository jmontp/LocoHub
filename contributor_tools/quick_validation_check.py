#!/usr/bin/env python3
"""
Quick Validation Check - Fast Validation with Optional Plotting

A fast validation tool that shows pass/fail statistics with optional plot generation.
Useful for rapid validation checks during dataset conversion and debugging.

Usage:
    # Text-only validation (default)
    python quick_validation_check.py converted_datasets/gtech_2021_phase.parquet
    
    # With custom ranges
    python quick_validation_check.py dataset.parquet --ranges custom_ranges.yaml
    
    # Generate plots for all tasks (shows interactively)
    python quick_validation_check.py dataset.parquet --plot
    
    # Generate plot for specific task (shows interactively)
    python quick_validation_check.py dataset.parquet --plot --task level_walking
    
    # Save plots to directory instead of showing
    python quick_validation_check.py dataset.parquet --plot --output-dir ./my_plots
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.validation_engine.validator import Validator
from user_libs.python.locomotion_data import LocomotionData


def generate_plots(dataset_path: str, validator: Validator, task_filter: Optional[str] = None, 
                  output_dir: Optional[str] = None, use_column_names: bool = False,
                  show_local_passing: bool = False) -> None:
    """
    Generate validation plots using the same plotting functions as report generator.
    
    Args:
        dataset_path: Path to dataset
        validator: Initialized validator
        task_filter: Optional single task to plot (if None, plot all)
        output_dir: Where to save plots (if None, show interactively)
        use_column_names: If True, use actual column names instead of pretty labels
        show_local_passing: If True, show locally passing strides in yellow
    """
    from internal.plot_generation.filters_by_phase_plots import create_task_combined_plot
    import matplotlib.pyplot as plt
    
    locomotion_data = LocomotionData(dataset_path, phase_col='phase_ipsi')
    dataset_name = Path(dataset_path).stem
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Determine which tasks to plot
    all_tasks = locomotion_data.get_tasks()
    if task_filter:
        if task_filter not in all_tasks:
            print(f"❌ Task '{task_filter}' not found in dataset")
            print(f"Available tasks: {', '.join(sorted(all_tasks))}")
            return
        tasks = [task_filter]
    else:
        tasks = all_tasks
    
    # Set output directory only if explicitly specified
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        print(f"\n📁 Output directory: {output_dir}")
        show = False  # If output_dir is specified, save files instead of showing
    else:
        show = True  # Default to showing plots if no output_dir specified
    
    # Generate plots for each task
    print(f"\n🎨 Generating plots for {len(tasks)} task(s)...")
    
    for task in sorted(tasks):
        print(f"\n📍 Processing {task}...")
        
        try:
            # Get validation failures for this task
            failures = validator._validate_task_with_failing_features(locomotion_data, task)
            
            # Get task data
            data_3d, features = locomotion_data.get_cycles(subject=None, task=task)
            
            if data_3d.size == 0:
                print(f"  ⚠️  No data available for {task}")
                continue
            
            # Get validation config for this task
            task_config = validator.config_manager.get_task_data(task)
            
            # Generate plot using the same function as report generator
            plot_path = create_task_combined_plot(
                validation_data=task_config,
                task_name=task,
                output_dir=str(output_dir) if output_dir else None,
                data_3d=data_3d,
                feature_names=features,
                failing_features=failures,
                dataset_name=dataset_name,
                timestamp=timestamp,
                show_interactive=show,
                use_column_names=use_column_names,
                show_local_passing=show_local_passing
            )
            
            if plot_path and not show:
                print(f"  ✅ Plot saved: {Path(plot_path).name}")
            elif show:
                print(f"  ✅ Plot displayed")
                
        except Exception as e:
            print(f"  ❌ Error generating plot for {task}: {e}")
            continue
    
    if show:
        # Just use matplotlib's normal display
        plt.show()
    elif output_dir:
        print(f"\n✅ All plots saved to: {output_dir}")



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
    print(f"Phase Structure: {phase_icon} {result['phase_message']}")
    
    # Task summary
    print(f"\nTasks Validated: {stats['num_tasks']}")
    
    if result['violations']:
        print("\n" + "-"*70)
        print("TASK SUMMARY")
        print("-"*70)
        
        for task, violations in sorted(result['violations'].items()):
            # Count total failures for this task
            total_failures = sum(len(v) for v in violations.values())
            
            if total_failures > 0:
                # Count unique features that failed
                failed_features = len(violations)
                print(f"\n📍 {task}: {total_failures} stride failures across {failed_features} features")
            else:
                print(f"\n📍 {task}: ✅ All features passed")
    else:
        print("\n✅ All validations passed!")
    
    # Summary statistics
    print("\n" + "-"*70)
    print("SUMMARY")
    print("-"*70)
    print(f"Total Strides: {stats['total_strides']:,}")
    print(f"Pass Rate: {stats['pass_rate']:.1%}")
    print(f"Variable Pass Rate: {stats['variable_pass_rate']:.1%}")
    
    print("\n" + "="*70)




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
        "--plot",
        action="store_true",
        help="Generate validation plots"
    )
    
    parser.add_argument(
        "--task",
        help="Generate plot for specific task only (e.g., level_walking)"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Directory to save plots (if not specified, plots are shown interactively)"
    )
    
    parser.add_argument(
        "--use-column-names",
        action="store_true",
        help="Use actual column names instead of pretty labels in plots"
    )
    
    parser.add_argument(
        "--show-local-passing",
        action="store_true",
        help="Show locally passing strides in yellow (pass current feature but fail others)"
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
        
        # Always print summary
        print_validation_summary(result)
        
        # Optional plot generation
        if args.plot:
            # Check for conflicting options
            if args.task and not args.plot:
                print("\n⚠️  Warning: --task requires --plot to be specified")
            
            generate_plots(
                dataset_path=str(dataset_path),
                validator=validator,
                task_filter=args.task,
                output_dir=args.output_dir,
                use_column_names=args.use_column_names,
                show_local_passing=args.show_local_passing
            )
        elif args.task or args.output_dir:
            print("\n⚠️  Note: --task and --output-dir require --plot to be specified")
        
        # Return exit code based on validation result
        return 0 if result['passed'] else 1
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())