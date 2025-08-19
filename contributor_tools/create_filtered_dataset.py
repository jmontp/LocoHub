#!/usr/bin/env python3
"""
Create Filtered Dataset - Remove failing strides from raw phase data

Automatically determines output filename:
- If input ends with '_raw.parquet': replaces with '_filtered.parquet'
- Otherwise: adds '_filtered' before '.parquet'

Examples:
  umich_2021_phase_raw.parquet → umich_2021_phase_filtered.parquet
  some_dataset.parquet → some_dataset_filtered.parquet
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.validation_engine.validator import Validator
from user_libs.python.locomotion_data import LocomotionData


class DatasetFilter:
    """Filter dataset to keep only biomechanically valid strides."""
    
    def __init__(self, validator: Validator):
        """
        Initialize the dataset filter.
        
        Args:
            validator: Initialized Validator instance
        """
        self.validator = validator
    
    def filter_dataset(self, raw_path: str, output_path: str, 
                      exclude_cols: List[str] = None) -> Dict[str, Any]:
        """
        Filter dataset to keep only passing strides.
        
        Args:
            raw_path: Path to raw dataset
            output_path: Path for filtered output (automatically determined)
            exclude_cols: Columns to ignore during validation AND remove from output
        
        Returns:
            Dictionary with filtering statistics
        """
        if exclude_cols is None:
            exclude_cols = []
            
        print(f"Loading dataset...")
        
        # Load raw dataset
        locomotion_data = LocomotionData(raw_path)
        df = locomotion_data.df
        
        print(f"Processing {len(locomotion_data.get_tasks())} tasks...")
        
        # Process each task independently
        filtered_dfs = []
        total_original = 0
        total_filtered = 0
        
        for task in locomotion_data.get_tasks():
            # Get task-specific dataframe
            task_df = df[df['task'] == task].copy()
            
            # Reset index for this task (0, 1, 2, ...)
            task_df.reset_index(drop=True, inplace=True)
            
            # Get failing strides from validator (ignoring excluded features)
            # Returns {stride_idx: [failed_vars]} where stride_idx is 0-based within task
            failures = self.validator._validate_task_with_failing_features(
                locomotion_data, task, ignore_features=exclude_cols)
            
            # Calculate total strides in this task
            n_strides = len(task_df) // 150
            total_original += n_strides
            
            # Determine which strides to keep (those NOT in failures dict)
            passing_strides = set(range(n_strides)) - set(failures.keys())
            total_filtered += len(passing_strides)
            
            # Build list of row indices to keep
            keep_rows = []
            for stride_idx in passing_strides:
                start_row = stride_idx * 150
                end_row = (stride_idx + 1) * 150
                keep_rows.extend(range(start_row, end_row))
            
            # Filter task dataframe
            task_df_filtered = task_df.iloc[keep_rows]
            
            # Add to list for concatenation
            if len(task_df_filtered) > 0:
                filtered_dfs.append(task_df_filtered)
            
            # Log task statistics
            pass_rate = len(passing_strides)/n_strides*100 if n_strides > 0 else 0
            print(f"  {task}: {len(passing_strides)}/{n_strides} strides passed ({pass_rate:.1f}%)")
        
        # Concatenate all filtered task dataframes
        if filtered_dfs:
            filtered_df = pd.concat(filtered_dfs, ignore_index=True)
        else:
            filtered_df = pd.DataFrame()  # Empty if no passing strides
        
        # Remove excluded columns from output
        if exclude_cols:
            # Only drop columns that actually exist
            cols_to_drop = [col for col in exclude_cols if col in filtered_df.columns]
            if cols_to_drop:
                filtered_df = filtered_df.drop(columns=cols_to_drop)
                print(f"\nRemoved {len(cols_to_drop)} excluded column(s) from output")
        
        # Save filtered dataset
        print(f"\nSaving filtered dataset...")
        filtered_df.to_parquet(output_path)
        
        return {
            'original_strides': total_original,
            'filtered_strides': total_filtered,
            'pass_rate': total_filtered / total_original if total_original > 0 else 0,
            'excluded_columns': exclude_cols,
            'output_path': output_path
        }


def determine_output_path(input_path: Path) -> Path:
    """
    Automatically determine output filename based on input.
    
    Rules:
    - If input ends with '_raw.parquet': replace with '_filtered.parquet'
    - Otherwise: insert '_filtered' before '.parquet'
    
    Examples:
        dataset_raw.parquet → dataset_filtered.parquet
        dataset.parquet → dataset_filtered.parquet
    """
    stem = input_path.stem  # filename without extension
    
    if stem.endswith('_raw'):
        # Replace '_raw' with '_filtered'
        new_stem = stem[:-4] + '_filtered'
    else:
        # Add '_filtered' to the end
        new_stem = stem + '_filtered'
    
    # Same directory as input
    output_path = input_path.parent / f"{new_stem}.parquet"
    return output_path


def main():
    """Main entry point for the filtering script."""
    parser = argparse.ArgumentParser(
        description="Filter dataset to keep only passing strides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output naming:
  - dataset_raw.parquet → dataset_filtered.parquet
  - dataset.parquet → dataset_filtered.parquet

Examples:
  # Basic filtering with default validation ranges
  python create_filtered_dataset.py umich_2021_phase_raw.parquet

  # Exclude experimental columns (ignore in validation AND remove from output)
  python create_filtered_dataset.py gtech_2021_phase_raw.parquet \\
      --exclude-columns "emg_signal_1,emg_signal_2,debug_flag"

  # Use custom validation ranges
  python create_filtered_dataset.py dataset_phase_raw.parquet \\
      --ranges validation_ranges/custom_ranges.yaml
        """
    )
    
    parser.add_argument("dataset",
                       help="Path to raw phase dataset (e.g., dataset_raw.parquet)")
    parser.add_argument("--ranges", 
                       default="validation_ranges/default_ranges.yaml",
                       help="Validation ranges YAML file (default: default_ranges.yaml)")
    parser.add_argument("--exclude-columns", type=str, default="",
                       help="Comma-separated columns to exclude (ignored in validation, removed from output)")
    
    args = parser.parse_args()
    
    # Validate input file exists
    input_path = Path(args.dataset)
    if not input_path.exists():
        print(f"❌ Error: Dataset not found: {args.dataset}")
        return 1
    
    # Determine output path automatically
    output_path = determine_output_path(input_path)
    
    # Parse excluded columns list
    exclude_cols = [c.strip() for c in args.exclude_columns.split(",") if c.strip()]
    
    # Initialize validator
    ranges_path = Path(args.ranges)
    if not ranges_path.exists():
        # Try relative to script directory
        ranges_path = Path(__file__).parent / args.ranges
        if not ranges_path.exists():
            print(f"❌ Error: Validation ranges not found: {args.ranges}")
            return 1
    
    print(f"🔍 Filtering dataset: {input_path.name}")
    print(f"📤 Output will be: {output_path.name}")
    print(f"📋 Using ranges: {ranges_path.name}")
    if exclude_cols:
        print(f"🚫 Excluding columns: {', '.join(exclude_cols)}")
    print()
    
    # Check if output already exists
    if output_path.exists():
        response = input(f"⚠️  Output file exists: {output_path.name}\n   Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    
    validator = Validator(config_path=ranges_path)
    
    # Create filter and process
    filter = DatasetFilter(validator)
    try:
        stats = filter.filter_dataset(
            str(input_path), 
            str(output_path),
            exclude_cols=exclude_cols
        )
        
        # Report results
        print(f"\n" + "="*50)
        print("FILTERING COMPLETE")
        print("="*50)
        print(f"Original: {stats['original_strides']:,} strides")
        print(f"Filtered: {stats['filtered_strides']:,} strides")
        print(f"Pass Rate: {stats['pass_rate']:.1%}")
        print(f"Output: {output_path.name}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during filtering: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())