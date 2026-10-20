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

# Ensure internal contributor tools are importable from a direct script invocation
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if src_dir.exists() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from contributor_tools.common.validation import Validator
from contributor_tools.common.dataset_table import DatasetTable


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
        # All selection decisions come from the release engine. Publish bundles
        # with build_dataset_release.py; this compatibility command emits a
        # derivative plus its exact assessment, without changing the input.
        import json
        import os
        import tempfile
        from contributor_tools.common.data_contract import assess_observations, IDENTITY_COLUMNS
        if exclude_cols:
            raise ValueError("Column exclusion is no longer supported. Declare optional signals in the profile.")
        output = Path(output_path)
        sidecar = output.with_suffix(output.suffix + '.quality.json')
        if output.exists() or sidecar.exists():
            raise FileExistsError("Choose a new output filename; filtered artifacts are immutable")
        table = DatasetTable(raw_path)
        assessment = assess_observations(table.df, self.validator.config_manager)
        if not assessment['publishable']:
            raise ValueError("Dataset does not satisfy the release contract: " +
                             str(assessment['contract']['issues']))
        eligible = {
            tuple(item['identity'][column] for column in IDENTITY_COLUMNS)
            for item in assessment['observations'] if item['eligible']
        }
        rows = pd.MultiIndex.from_frame(table.df[list(IDENTITY_COLUMNS)])
        selected = table.df.loc[rows.isin(eligible)]
        total = len(assessment['observations'])
        assessment['input_path'] = str(Path(raw_path).resolve())
        assessment['profile_path'] = str(self.validator.config_path.resolve())
        import hashlib
        def digest(path):
            h = hashlib.sha256()
            with open(path, 'rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    h.update(block)
            return h.hexdigest()
        assessment['input_sha256'] = digest(raw_path)
        assessment['profile_sha256'] = digest(self.validator.config_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent, prefix='.filter-') as temp:
            staged = Path(temp) / output.name
            selected.to_parquet(staged, index=False, row_group_size=16384)
            assessment['output_sha256'] = digest(staged)
            staged_report = Path(temp) / sidecar.name
            staged_report.write_text(json.dumps(assessment, indent=2, allow_nan=False) + '\n')
            # Hard-link promotion refuses an existing destination, including races.
            os.link(staged_report, sidecar)
            try:
                os.link(staged, output)
            except BaseException:
                sidecar.unlink()
                raise
        return {
            'original_strides': total, 'clean_strides': len(eligible),
            'pass_rate': len(eligible) / total if total else 0.0,
            'excluded_columns': [], 'output_path': str(output),
            'quality_path': str(sidecar),
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
    
    if exclude_cols:
        print("Use profile optional_features instead of excluding columns.")
        return 1
    if output_path.exists():
        print("Output exists; choose a new versioned output filename.")
        return 1

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
