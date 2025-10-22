#!/usr/bin/env python3
"""
Create Clean Dataset - Remove failing strides from dirty phase data

Automatically determines output filename:
- If input ends with '_dirty.parquet' (or legacy '_raw.parquet'): replaces with '_clean.parquet'
- Otherwise: adds '_clean' before '.parquet'

Examples:
  umich_2021_phase_dirty.parquet → umich_2021_phase_clean.parquet
  some_dataset.parquet → some_dataset_clean.parquet
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional

try:
    import pyarrow as pa
    from pyarrow.parquet import ParquetWriter
except ImportError as exc:
    raise ImportError("pyarrow is required to write parquet files. Install pyarrow before running this script.") from exc

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from internal.validation_engine.validator import Validator
from locohub import LocomotionData


class DatasetCleaner:
    """Clean dataset to keep only biomechanically valid strides."""
    
    def __init__(self, validator: Validator):
        """
        Initialize the dataset cleaner.
        
        Args:
            validator: Initialized Validator instance
        """
        self.validator = validator
    
    def clean_dataset(self, raw_path: str, output_path: str, 
                      exclude_cols: List[str] = None) -> Dict[str, Any]:
        """
        Clean dataset to keep only biomechanically valid strides.
        
        Args:
            raw_path: Path to raw dataset
            output_path: Path for clean output (automatically determined)
            exclude_cols: Columns to ignore during validation AND remove from output
        
        Returns:
            Dictionary with cleaning statistics
        """
        if exclude_cols is None:
            exclude_cols = []
            
        print(f"Loading dataset...")
        
        # Load raw dataset
        locomotion_data = LocomotionData(raw_path)
        df = locomotion_data.df
        
        print(f"Processing {len(locomotion_data.get_tasks())} tasks...")
        
        # Process each task independently, streaming output to parquet to limit memory usage
        total_original = 0
        total_clean = 0
        writer: Optional[ParquetWriter] = None
        writer_schema = None

        for task in locomotion_data.get_tasks():
            task_df = df[df['task'] == task].copy()
            task_df.reset_index(drop=True, inplace=True)

            failures = self.validator._validate_task_with_failing_features(
                locomotion_data, task, ignore_features=exclude_cols)

            n_strides = len(task_df) // 150
            total_original += n_strides

            passing_strides = set(range(n_strides)) - set(failures.keys())
            total_clean += len(passing_strides)

            keep_rows: List[int] = []
            for stride_idx in passing_strides:
                start_row = stride_idx * 150
                end_row = (stride_idx + 1) * 150
                keep_rows.extend(range(start_row, end_row))

            task_df_clean = task_df.iloc[keep_rows]

            if exclude_cols and not task_df_clean.empty:
                cols_to_drop = [col for col in exclude_cols if col in task_df_clean.columns]
                if cols_to_drop:
                    task_df_clean = task_df_clean.drop(columns=cols_to_drop)

            pass_rate = len(passing_strides)/n_strides*100 if n_strides > 0 else 0
            print(f"  {task}: {len(passing_strides)}/{n_strides} strides passed ({pass_rate:.1f}%)")

            if task_df_clean.empty:
                continue

            table = pa.Table.from_pandas(task_df_clean, preserve_index=False)

            if writer is None:
                writer_schema = table.schema
                writer = ParquetWriter(str(output_path), writer_schema, compression='snappy')
            else:
                table = table.select(writer_schema.names)

            writer.write_table(table)

        print("\nSaving clean dataset...")
        if writer is None:
            pd.DataFrame().to_parquet(output_path)
        else:
            writer.close()

        return {
            'original_strides': total_original,
            'clean_strides': total_clean,
            'pass_rate': total_clean / total_original if total_original > 0 else 0,
            'excluded_columns': exclude_cols,
            'output_path': output_path
        }


def determine_output_path(input_path: Path) -> Path:
    """
    Automatically determine output filename based on input.
    
    Rules:
    - If input ends with '_dirty.parquet' (or legacy '_raw.parquet'): replace with '_clean.parquet'
    - Otherwise: insert '_clean' before '.parquet'
    
    Examples:
        dataset_dirty.parquet → dataset_clean.parquet
        dataset.parquet → dataset_clean.parquet
    """
    stem = input_path.stem  # filename without extension
    
    if stem.endswith('_dirty'):
        # Replace '_dirty' with '_clean'
        new_stem = stem[:-6] + '_clean'
    elif stem.endswith('_raw'):
        # Legacy support for older `_raw` exports
        new_stem = stem[:-4] + '_clean'
    else:
        # Add '_clean' to the end
        new_stem = stem + '_clean'
    
    # Same directory as input
    output_path = input_path.parent / f"{new_stem}.parquet"
    return output_path


def main():
    """Main entry point for the cleaning script."""
    parser = argparse.ArgumentParser(
        description="Clean dataset to keep only passing strides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output naming:
  - dataset_dirty.parquet → dataset_clean.parquet
  - dataset.parquet → dataset_clean.parquet

Examples:
  # Basic filtering with default validation ranges
  python create_clean_dataset.py umich_2021_phase_dirty.parquet

  # Exclude experimental columns (ignore in validation AND remove from output)
  python create_clean_dataset.py gtech_2021_phase_dirty.parquet \\
      --exclude-columns "emg_signal_1,emg_signal_2,debug_flag"

  # Use custom validation ranges
  python create_clean_dataset.py dataset_phase_dirty.parquet \\
      --ranges validation_ranges/custom_ranges.yaml
        """
    )
    
    parser.add_argument("dataset",
                       help="Path to dirty phase dataset (e.g., dataset_dirty.parquet)")
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
    
    # Load dataset to validate exclude columns
    print("Loading dataset to validate columns...")
    try:
        temp_locomotion_data = LocomotionData(str(input_path))
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        return 1
    
    # Validate exclude columns exist in dataset
    if exclude_cols:
        available_columns = temp_locomotion_data.df.columns.tolist()
        invalid_cols = [col for col in exclude_cols if col not in available_columns]
        
        if invalid_cols:
            print(f"\n❌ Error: The following columns do not exist in the dataset:")
            for col in invalid_cols:
                print(f"    - {col}")
            
            # Get biomechanical features (most likely candidates for exclusion)
            biomech_features = temp_locomotion_data.features
            
            print(f"\n📊 Available biomechanical features ({len(biomech_features)}):")
            for feature in sorted(biomech_features):
                print(f"    {feature}")
            
            # Also show metadata columns
            metadata_cols = [col for col in available_columns 
                           if col not in biomech_features]
            print(f"\n📋 Available metadata columns ({len(metadata_cols)}):")
            for col in sorted(metadata_cols)[:10]:  # Show first 10
                print(f"    {col}")
            if len(metadata_cols) > 10:
                print(f"    ... and {len(metadata_cols) - 10} more")
            
            return 1
    
    print()  # Add blank line for clarity
    
    # Check if output already exists
    if output_path.exists() and sys.stdin.isatty():
        response = input(f"⚠️  Output file exists: {output_path.name}\n   Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    elif output_path.exists():
        print(f"⚠️  Output file exists: {output_path.name} (no TTY, overwriting)")

    # Release temporary dataset before heavy processing
    del temp_locomotion_data
    from gc import collect as gc_collect
    gc_collect()

    validator = Validator(config_path=ranges_path)

    # Create cleaner and process
    cleaner = DatasetCleaner(validator)
    try:
        stats = cleaner.clean_dataset(
            str(input_path), 
            str(output_path),
            exclude_cols=exclude_cols
        )
        
        # Report results
        print(f"\n" + "="*50)
        print("FILTERING COMPLETE")
        print("="*50)
        print(f"Original: {stats['original_strides']:,} strides")
        print(f"Clean: {stats['clean_strides']:,} strides")
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
