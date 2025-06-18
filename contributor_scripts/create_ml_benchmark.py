"""
create_ml_benchmark.py

Created: 2025-06-18 with user permission
Purpose: CLI for creating ML benchmarks from multiple datasets with stratification

Intent: Provides command-line interface for creating standardized ML benchmarks
with proper train/test splits, demographic balance, and subject-level leakage prevention.
Supports multiple datasets, custom stratification, and quality validation.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import logging
from typing import List, Dict, Optional
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.validation.benchmark_creator import BenchmarkCreator, BenchmarkMetadata

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load dataset from parquet file with validation."""
    try:
        df = pd.read_parquet(dataset_path)
        logger.info(f"Loaded dataset: {len(df)} cycles, {df['subject_id'].nunique()} subjects")
        return df
    except Exception as e:
        logger.error(f"Failed to load dataset {dataset_path}: {e}")
        raise


def combine_datasets(dataset_paths: List[Path], dataset_names: Optional[List[str]] = None) -> pd.DataFrame:
    """Combine multiple datasets with source tracking."""
    if dataset_names and len(dataset_names) != len(dataset_paths):
        raise ValueError("Number of dataset names must match number of dataset paths")
    
    combined_data = []
    
    for i, path in enumerate(dataset_paths):
        df = load_dataset(path)
        
        # Add dataset source
        source_name = dataset_names[i] if dataset_names else f"dataset_{i+1}"
        df['dataset_source'] = source_name
        
        combined_data.append(df)
        logger.info(f"Added {source_name}: {len(df)} cycles")
    
    combined_df = pd.concat(combined_data, ignore_index=True)
    logger.info(f"Combined dataset: {len(combined_df)} total cycles, "
               f"{combined_df['subject_id'].nunique()} total subjects")
    
    return combined_df


def validate_dataset_requirements(df: pd.DataFrame, stratify_columns: List[str]) -> None:
    """Validate dataset meets benchmark creation requirements."""
    required_columns = ['subject_id', 'cycle_id']
    missing_required = [col for col in required_columns if col not in df.columns]
    
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")
    
    missing_stratify = [col for col in stratify_columns if col not in df.columns]
    if missing_stratify:
        raise ValueError(f"Missing stratification columns: {missing_stratify}")
    
    # Check for reasonable number of subjects
    n_subjects = df['subject_id'].nunique()
    if n_subjects < 10:
        logger.warning(f"Small number of subjects ({n_subjects}) may lead to unreliable splits")
    
    # Check for missing values in key columns
    key_columns = ['subject_id'] + stratify_columns
    for col in key_columns:
        if df[col].isna().any():
            logger.warning(f"Missing values detected in {col}")


def print_dataset_summary(df: pd.DataFrame, stratify_columns: List[str]) -> None:
    """Print comprehensive dataset summary."""
    print("\n" + "="*50)
    print("DATASET SUMMARY")
    print("="*50)
    
    print(f"Total cycles: {len(df):,}")
    print(f"Total subjects: {df['subject_id'].nunique():,}")
    
    if 'task' in df.columns:
        print(f"Tasks: {', '.join(df['task'].unique())}")
    
    if 'dataset_source' in df.columns:
        print("\nDataset sources:")
        source_counts = df.groupby('dataset_source')['subject_id'].nunique()
        for source, count in source_counts.items():
            print(f"  {source}: {count} subjects")
    
    print("\nDemographic distribution:")
    for col in stratify_columns:
        if col in df.columns:
            unique_subjects = df.drop_duplicates('subject_id')
            counts = unique_subjects[col].value_counts()
            print(f"  {col}:")
            for category, count in counts.items():
                percentage = count / len(unique_subjects) * 100
                print(f"    {category}: {count} subjects ({percentage:.1f}%)")


def print_quality_report(quality_report: Dict) -> None:
    """Print benchmark quality report."""
    print("\n" + "="*50)
    print("BENCHMARK QUALITY REPORT")
    print("="*50)
    
    # Overall quality score
    score = quality_report.get('overall_quality_score', 0)
    print(f"Overall Quality Score: {score:.3f}/1.000")
    
    if score >= 0.9:
        print("✅ EXCELLENT - Benchmark meets high quality standards")
    elif score >= 0.8:
        print("✅ GOOD - Benchmark meets quality standards")
    elif score >= 0.7:
        print("⚠️  ACCEPTABLE - Some quality concerns, review recommended")
    else:
        print("❌ POOR - Quality issues detected, improvement needed")
    
    # Subject leakage check
    print("\nSubject Leakage Check:")
    leakage = quality_report.get('subject_leakage', {})
    for check, passed in leakage.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check}: {status}")
    
    # Demographic balance
    print("\nDemographic Balance:")
    balance = quality_report.get('demographic_balance', {})
    for demo, categories in balance.items():
        print(f"  {demo}:")
        for category, imbalance in categories.items():
            if imbalance < 0.05:
                status = "✅ BALANCED"
            elif imbalance < 0.1:
                status = "⚠️  SLIGHT IMBALANCE"
            else:
                status = "❌ IMBALANCED"
            print(f"    {category}: {imbalance:.3f} {status}")
    
    # Split sizes
    print("\nSplit Sizes:")
    sizes = quality_report.get('split_sizes', {})
    for key, value in sizes.items():
        if key.endswith('_subjects'):
            split_name = key.replace('_subjects', '')
            print(f"  {split_name}: {value} subjects")


def create_benchmark_config(args) -> Dict:
    """Create benchmark configuration from CLI arguments."""
    config = {
        'train_ratio': args.train_ratio,
        'validation_ratio': args.validation_ratio,
        'test_ratio': args.test_ratio,
        'stratify_columns': args.stratify_columns,
        'random_seed': args.random_seed,
        'balance_tolerance': args.balance_tolerance,
        'min_samples_per_split': args.min_samples_per_split,
        'memory_efficient': args.memory_efficient,
        'chunk_size': args.chunk_size
    }
    return config


def main():
    """Main CLI function for benchmark creation."""
    parser = argparse.ArgumentParser(
        description="Create ML benchmarks from locomotion datasets with stratified sampling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single dataset benchmark
  python create_ml_benchmark.py data/gtech_2023_phase.parquet --output benchmarks/

  # Multi-dataset benchmark
  python create_ml_benchmark.py data/gtech_2023_phase.parquet data/umich_2021_phase.parquet \\
    --dataset-names "GTech2023" "UMich2021" --output benchmarks/

  # Custom stratification
  python create_ml_benchmark.py data/dataset.parquet --stratify-columns age_group sex condition \\
    --train-ratio 0.8 --test-ratio 0.2 --validation-ratio 0.0

  # Memory-efficient processing
  python create_ml_benchmark.py large_dataset.parquet --memory-efficient --chunk-size 500
        """
    )
    
    # Dataset arguments
    parser.add_argument('datasets', nargs='+', type=Path,
                       help='Paths to input datasets (parquet files)')
    parser.add_argument('--dataset-names', nargs='+',
                       help='Names for datasets (must match number of datasets)')
    
    # Output arguments
    parser.add_argument('--output', '-o', type=Path, required=True,
                       help='Output directory for benchmark files')
    parser.add_argument('--benchmark-name', default='ml_benchmark',
                       help='Name for the benchmark (default: ml_benchmark)')
    
    # Split configuration
    parser.add_argument('--train-ratio', type=float, default=0.7,
                       help='Training set ratio (default: 0.7)')
    parser.add_argument('--validation-ratio', type=float, default=0.15,
                       help='Validation set ratio (default: 0.15)')
    parser.add_argument('--test-ratio', type=float, default=0.15,
                       help='Test set ratio (default: 0.15)')
    
    # Stratification options
    parser.add_argument('--stratify-columns', nargs='+', 
                       default=['sex', 'age_group'],
                       help='Columns for demographic stratification (default: sex age_group)')
    parser.add_argument('--balance-tolerance', type=float, default=0.05,
                       help='Maximum allowed demographic imbalance (default: 0.05)')
    
    # Quality controls
    parser.add_argument('--min-samples-per-split', type=int, default=3,
                       help='Minimum subjects per split (default: 3)')
    parser.add_argument('--random-seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    
    # Memory efficiency
    parser.add_argument('--memory-efficient', action='store_true',
                       help='Use memory-efficient streaming processing')
    parser.add_argument('--chunk-size', type=int, default=1000,
                       help='Chunk size for streaming processing (default: 1000)')
    
    # Analysis options
    parser.add_argument('--skip-quality-check', action='store_true',
                       help='Skip detailed quality validation')
    parser.add_argument('--export-metadata-only', action='store_true',
                       help='Export only metadata without split files')
    
    args = parser.parse_args()
    
    try:
        # Validate inputs
        for dataset_path in args.datasets:
            if not dataset_path.exists():
                raise FileNotFoundError(f"Dataset not found: {dataset_path}")
        
        # Create output directory
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Load and combine datasets
        if len(args.datasets) == 1:
            df = load_dataset(args.datasets[0])
        else:
            df = combine_datasets(args.datasets, args.dataset_names)
        
        # Validate dataset requirements
        validate_dataset_requirements(df, args.stratify_columns)
        
        # Print dataset summary
        print_dataset_summary(df, args.stratify_columns)
        
        # Create benchmark configuration
        config = create_benchmark_config(args)
        
        # Create benchmark
        creator = BenchmarkCreator(config)
        
        # Create splits
        if args.memory_efficient:
            logger.info("Creating memory-efficient stratified splits...")
            splits = creator.create_stratified_splits_streaming(df)
        else:
            logger.info("Creating stratified splits...")
            splits = creator.create_stratified_splits(df)
        
        # Print split summary
        print("\n" + "="*50)
        print("SPLIT SUMMARY")
        print("="*50)
        for split_name, split_df in splits.items():
            n_subjects = split_df['subject_id'].nunique() if len(split_df) > 0 else 0
            n_cycles = len(split_df)
            print(f"{split_name.title()}: {n_subjects} subjects, {n_cycles} cycles")
        
        # Quality validation
        if not args.skip_quality_check:
            logger.info("Validating benchmark quality...")
            quality_report = creator.validate_benchmark_quality(splits)
            print_quality_report(quality_report)
        
        # Export benchmark
        if not args.export_metadata_only:
            logger.info("Exporting benchmark files...")
            creator.export_benchmark(splits, args.output, args.benchmark_name)
        else:
            logger.info("Exporting metadata only...")
            all_data = pd.concat(splits.values(), ignore_index=True)
            metadata = creator.generate_benchmark_metadata(splits, all_data)
            metadata_path = args.output / f"{args.benchmark_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                f.write(metadata.to_json())
            logger.info(f"Metadata exported to {metadata_path}")
        
        print(f"\n✅ Benchmark creation completed successfully!")
        print(f"📁 Output directory: {args.output}")
        
    except Exception as e:
        logger.error(f"Benchmark creation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()