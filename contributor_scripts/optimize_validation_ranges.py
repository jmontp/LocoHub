#!/usr/bin/env python3
"""
Optimize Validation Ranges CLI

Created: 2025-06-18 with user permission
Purpose: CLI tool for statistical validation range optimization across multiple datasets

Intent:
This script provides a command-line interface for optimizing validation ranges
using statistical analysis of multiple datasets. Supports memory-efficient
processing of large datasets with streaming statistics and various optimization
methods (percentile, standard deviation, IQR).

**Key Features:**
1. **Multi-Dataset Analysis**: Process multiple datasets with configurable weights
2. **Memory Efficiency**: Stream large datasets without memory exhaustion
3. **Multiple Methods**: Percentile, standard deviation, and IQR-based optimization
4. **False Positive Targeting**: Optimize ranges for specific error rates
5. **Integration Ready**: Output compatible with existing validation system

Usage:
    # Optimize using percentile method (5th-95th percentiles)
    python optimize_validation_ranges.py --datasets dataset1_phase.parquet dataset2_phase.parquet --method percentile --percentiles 5 95
    
    # Optimize for target false positive rate
    python optimize_validation_ranges.py --datasets dataset1_phase.parquet --target-fp-rate 0.05
    
    # Process large datasets in chunks
    python optimize_validation_ranges.py --datasets large_dataset_phase.parquet --chunk-size 10000 --method std_dev
"""

import argparse
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from lib.validation.range_optimizer import RangeOptimizer
    from lib.validation.validation_expectations_parser import ValidationExpectationsParser
    from lib.core.feature_constants import ANGLE_FEATURES, MOMENT_FEATURES
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running from the project root directory.")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationRangeOptimizer:
    """
    CLI interface for validation range optimization.
    
    Handles dataset loading, optimization, and output generation
    with memory-efficient processing for large datasets.
    """
    
    def __init__(self, chunk_size: int = 50000):
        """
        Initialize optimizer.
        
        Args:
            chunk_size: Size of chunks for processing large datasets
        """
        self.optimizer = RangeOptimizer()
        self.chunk_size = chunk_size
        self.processed_datasets = []
    
    def load_dataset(self, dataset_path: str, weight: float = 1.0) -> bool:
        """
        Load dataset for optimization.
        
        Args:
            dataset_path: Path to parquet dataset
            weight: Weight for this dataset in optimization
            
        Returns:
            True if successfully loaded
        """
        try:
            dataset_path = Path(dataset_path)
            if not dataset_path.exists():
                logger.error(f"Dataset not found: {dataset_path}")
                return False
            
            logger.info(f"Loading dataset: {dataset_path} (weight: {weight})")
            
            # Read parquet file
            df = pd.read_parquet(dataset_path)
            
            # Validate required columns (check for phase or phase_percent)
            phase_col = None
            if 'phase' in df.columns:
                phase_col = 'phase'
            elif 'phase_percent' in df.columns:
                phase_col = 'phase_percent'
            else:
                logger.error(f"Dataset missing 'phase' or 'phase_percent' column: {dataset_path}")
                return False
            
            # Filter to phase-indexed data (should be exactly 150 points per cycle)
            phase_data = df[df[phase_col].notna()]
            
            if len(phase_data) == 0:
                logger.error(f"No phase-indexed data found in: {dataset_path}")
                return False
            
            # Extract biomechanical features
            biomech_features = self._extract_biomechanical_features(phase_data)
            
            if not biomech_features:
                logger.error(f"No biomechanical features found in: {dataset_path}")
                return False
            
            # Process in chunks if dataset is large
            if len(phase_data) > self.chunk_size:
                self._process_large_dataset(dataset_path.stem, phase_data, biomech_features, weight)
            else:
                # Process entire dataset
                feature_data = {}
                for feature in biomech_features:
                    values = phase_data[feature].dropna().values
                    if len(values) > 0:
                        feature_data[feature] = values
                
                self.optimizer.add_dataset(dataset_path.stem, feature_data, weight)
            
            self.processed_datasets.append({
                'name': dataset_path.stem,
                'path': str(dataset_path),
                'weight': weight,
                'rows': len(phase_data),
                'features': len(biomech_features)
            })
            
            logger.info(f"Successfully loaded {len(phase_data)} rows with {len(biomech_features)} features")
            return True
            
        except Exception as e:
            logger.error(f"Error loading dataset {dataset_path}: {e}")
            return False
    
    def _extract_biomechanical_features(self, df: pd.DataFrame) -> List[str]:
        """
        Extract biomechanical feature columns from dataframe.
        
        Args:
            df: Dataset dataframe
            
        Returns:
            List of biomechanical feature column names
        """
        biomech_features = []
        
        # Check for angle features
        for feature in ANGLE_FEATURES:
            if feature in df.columns:
                biomech_features.append(feature)
        
        # Check for moment features
        for feature in MOMENT_FEATURES:
            if feature in df.columns:
                biomech_features.append(feature)
        
        return biomech_features
    
    def _process_large_dataset(self, 
                              dataset_name: str, 
                              df: pd.DataFrame, 
                              features: List[str], 
                              weight: float):
        """
        Process large dataset in chunks to avoid memory issues.
        
        Args:
            dataset_name: Dataset identifier
            df: Dataset dataframe
            features: List of feature names to process
            weight: Dataset weight
        """
        logger.info(f"Processing large dataset {dataset_name} in chunks of {self.chunk_size}")
        
        total_chunks = (len(df) + self.chunk_size - 1) // self.chunk_size
        
        for chunk_idx in range(total_chunks):
            start_idx = chunk_idx * self.chunk_size
            end_idx = min((chunk_idx + 1) * self.chunk_size, len(df))
            
            chunk_df = df.iloc[start_idx:end_idx]
            
            # Extract feature data for chunk
            chunk_data = {}
            for feature in features:
                if feature in chunk_df.columns:
                    values = chunk_df[feature].dropna().values
                    if len(values) > 0:
                        chunk_data[feature] = values
            
            if chunk_data:
                self.optimizer.add_data_chunk(f"{dataset_name}_chunk_{chunk_idx}", chunk_data)
            
            if (chunk_idx + 1) % 10 == 0:
                logger.info(f"Processed chunk {chunk_idx + 1}/{total_chunks}")
    
    def optimize_ranges(self, 
                       method: str,
                       features: Optional[List[str]] = None,
                       **method_kwargs) -> Dict[str, Dict[str, float]]:
        """
        Optimize validation ranges using specified method.
        
        Args:
            method: Optimization method
            features: Features to optimize (None for all available)
            **method_kwargs: Method-specific parameters
            
        Returns:
            Optimized ranges dictionary
        """
        if features is None:
            features = self.optimizer.aggregator.get_feature_names()
        
        if not features:
            logger.error("No features available for optimization")
            return {}
        
        logger.info(f"Optimizing ranges for {len(features)} features using {method} method")
        
        try:
            optimized_ranges = self.optimizer.optimize_ranges(
                method=method,
                features=features,
                **method_kwargs
            )
            
            logger.info(f"Successfully optimized ranges for {len(optimized_ranges)} features")
            return optimized_ranges
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
            return {}
    
    def optimize_for_target_fp_rate(self, 
                                   features: Optional[List[str]] = None,
                                   target_fp_rate: float = 0.05,
                                   tolerance: float = 0.01) -> Dict[str, Dict[str, float]]:
        """
        Optimize ranges for target false positive rate.
        
        Args:
            features: Features to optimize
            target_fp_rate: Target false positive rate
            tolerance: Tolerance for target rate
            
        Returns:
            Optimized ranges
        """
        if features is None:
            features = self.optimizer.aggregator.get_feature_names()
        
        logger.info(f"Optimizing for target FP rate: {target_fp_rate:.3f} ± {tolerance:.3f}")
        
        try:
            optimized_ranges = self.optimizer.optimize_for_fp_rate(
                features=features,
                target_fp_rate=target_fp_rate,
                tolerance=tolerance
            )
            
            return optimized_ranges
            
        except Exception as e:
            logger.error(f"Error during FP rate optimization: {e}")
            return {}
    
    def calculate_current_fp_rates(self, validation_file: str) -> Dict[str, float]:
        """
        Calculate false positive rates for current validation ranges.
        
        Args:
            validation_file: Path to validation expectations file
            
        Returns:
            False positive rates for each feature
        """
        try:
            parser = ValidationExpectationsParser()
            current_ranges = parser.read_validation_data(validation_file)
            
            # Convert to flat range format
            flat_ranges = {}
            for task, task_data in current_ranges.items():
                for phase, phase_data in task_data.items():
                    for feature, range_dict in phase_data.items():
                        # Use a representative range (could be averaged across phases/tasks)
                        if feature not in flat_ranges:
                            flat_ranges[feature] = range_dict
            
            fp_rates = self.optimizer.calculate_false_positive_rates(flat_ranges)
            return fp_rates
            
        except Exception as e:
            logger.error(f"Error calculating current FP rates: {e}")
            return {}
    
    def generate_report(self, 
                       optimized_ranges: Dict[str, Dict[str, float]],
                       method: str,
                       output_file: Optional[str] = None) -> str:
        """
        Generate optimization report.
        
        Args:
            optimized_ranges: Optimized ranges
            method: Optimization method used
            output_file: Optional output file path
            
        Returns:
            Report as string
        """
        summary = self.optimizer.get_optimization_summary()
        
        report_lines = [
            "# Validation Range Optimization Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Method: {method}",
            "",
            "## Datasets Processed",
        ]
        
        for dataset in self.processed_datasets:
            report_lines.append(f"- **{dataset['name']}**: {dataset['rows']} rows, "
                              f"{dataset['features']} features (weight: {dataset['weight']})")
        
        report_lines.extend([
            "",
            f"**Total Observations**: {summary['total_observations']:,}",
            "",
            "## Optimized Ranges",
            ""
        ])
        
        for feature, range_dict in optimized_ranges.items():
            feature_info = summary['features'].get(feature, {})
            count = feature_info.get('count', 0)
            mean = feature_info.get('mean', 0)
            std = feature_info.get('std', 0)
            
            report_lines.extend([
                f"### {feature}",
                f"- **Range**: [{range_dict['min']:.4f}, {range_dict['max']:.4f}]",
                f"- **Statistics**: mean={mean:.4f}, std={std:.4f}, n={count:,}",
                ""
            ])
        
        report = "\n".join(report_lines)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report)
                logger.info(f"Report saved to: {output_file}")
            except Exception as e:
                logger.error(f"Error saving report: {e}")
        
        return report
    
    def export_ranges_json(self, 
                          optimized_ranges: Dict[str, Dict[str, float]],
                          output_file: str):
        """
        Export optimized ranges to JSON file.
        
        Args:
            optimized_ranges: Optimized ranges
            output_file: Output JSON file path
        """
        try:
            export_data = {
                'metadata': {
                    'generated': datetime.now().isoformat(),
                    'datasets': self.processed_datasets,
                    'total_observations': sum(
                        self.optimizer.aggregator.get_feature_calculator(f).get_count() 
                        for f in self.optimizer.aggregator.get_feature_names()
                        if self.optimizer.aggregator.get_feature_calculator(f)
                    )
                },
                'optimized_ranges': optimized_ranges
            }
            
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Ranges exported to: {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting ranges: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Optimize validation ranges using statistical analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Dataset arguments
    parser.add_argument(
        '--datasets',
        nargs='+',
        required=True,
        help='Paths to phase-indexed parquet datasets'
    )
    
    parser.add_argument(
        '--weights',
        nargs='+',
        type=float,
        help='Weights for each dataset (default: equal weights)'
    )
    
    # Optimization method arguments
    parser.add_argument(
        '--method',
        choices=['percentile', 'std_dev', 'iqr'],
        default='percentile',
        help='Optimization method (default: percentile)'
    )
    
    parser.add_argument(
        '--percentiles',
        nargs=2,
        type=float,
        default=[5, 95],
        help='Lower and upper percentiles for percentile method (default: 5 95)'
    )
    
    parser.add_argument(
        '--num-std-dev',
        type=float,
        default=2.5,
        help='Number of standard deviations for std_dev method (default: 2.5)'
    )
    
    parser.add_argument(
        '--iqr-multiplier',
        type=float,
        default=1.5,
        help='IQR multiplier for iqr method (default: 1.5)'
    )
    
    # Target false positive rate
    parser.add_argument(
        '--target-fp-rate',
        type=float,
        help='Target false positive rate (overrides method selection)'
    )
    
    parser.add_argument(
        '--fp-tolerance',
        type=float,
        default=0.01,
        help='Tolerance for target FP rate optimization (default: 0.01)'
    )
    
    # Feature selection
    parser.add_argument(
        '--features',
        nargs='+',
        help='Specific features to optimize (default: all available)'
    )
    
    parser.add_argument(
        '--kinematic-only',
        action='store_true',
        help='Optimize only kinematic features (angles)'
    )
    
    parser.add_argument(
        '--kinetic-only',
        action='store_true',
        help='Optimize only kinetic features (moments)'
    )
    
    # Processing options
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=50000,
        help='Chunk size for processing large datasets (default: 50000)'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir',
        default='optimization_results',
        help='Output directory for results (default: optimization_results)'
    )
    
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report only, do not update validation files'
    )
    
    parser.add_argument(
        '--compare-current',
        help='Path to current validation file for comparison'
    )
    
    # Logging
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if args.weights and len(args.weights) != len(args.datasets):
        parser.error("Number of weights must match number of datasets")
    
    if args.kinematic_only and args.kinetic_only:
        parser.error("Cannot specify both --kinematic-only and --kinetic-only")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize optimizer
    logger.info("Initializing validation range optimizer")
    range_optimizer = ValidationRangeOptimizer(chunk_size=args.chunk_size)
    
    # Load datasets
    weights = args.weights or [1.0] * len(args.datasets)
    successful_loads = 0
    
    for dataset_path, weight in zip(args.datasets, weights):
        if range_optimizer.load_dataset(dataset_path, weight):
            successful_loads += 1
    
    if successful_loads == 0:
        logger.error("No datasets successfully loaded")
        sys.exit(1)
    
    logger.info(f"Successfully loaded {successful_loads}/{len(args.datasets)} datasets")
    
    # Determine features to optimize
    if args.features:
        features = args.features
    elif args.kinematic_only:
        features = ANGLE_FEATURES
    elif args.kinetic_only:
        features = MOMENT_FEATURES
    else:
        features = None  # All available
    
    # Optimize ranges
    if args.target_fp_rate is not None:
        logger.info(f"Optimizing for target false positive rate: {args.target_fp_rate}")
        optimized_ranges = range_optimizer.optimize_for_target_fp_rate(
            features=features,
            target_fp_rate=args.target_fp_rate,
            tolerance=args.fp_tolerance
        )
        method_desc = f"target_fp_rate_{args.target_fp_rate}"
    else:
        logger.info(f"Optimizing using {args.method} method")
        
        if args.method == 'percentile':
            method_kwargs = {'percentiles': tuple(args.percentiles)}
        elif args.method == 'std_dev':
            method_kwargs = {'num_std_dev': args.num_std_dev}
        elif args.method == 'iqr':
            method_kwargs = {'iqr_multiplier': args.iqr_multiplier}
        else:
            method_kwargs = {}
        
        optimized_ranges = range_optimizer.optimize_ranges(
            method=args.method,
            features=features,
            **method_kwargs
        )
        method_desc = args.method
    
    if not optimized_ranges:
        logger.error("No ranges were optimized")
        sys.exit(1)
    
    # Generate timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Generate report
    report_file = output_dir / f"optimization_report_{method_desc}_{timestamp}.md"
    report = range_optimizer.generate_report(optimized_ranges, method_desc, str(report_file))
    
    # Export to JSON
    json_file = output_dir / f"optimized_ranges_{method_desc}_{timestamp}.json"
    range_optimizer.export_ranges_json(optimized_ranges, str(json_file))
    
    # Compare with current ranges if requested
    if args.compare_current:
        logger.info(f"Comparing with current validation file: {args.compare_current}")
        current_fp_rates = range_optimizer.calculate_current_fp_rates(args.compare_current)
        
        if current_fp_rates:
            comparison_file = output_dir / f"fp_rate_comparison_{timestamp}.json"
            comparison_data = {
                'current_fp_rates': current_fp_rates,
                'optimized_ranges': optimized_ranges,
                'comparison_timestamp': datetime.now().isoformat()
            }
            
            with open(comparison_file, 'w') as f:
                json.dump(comparison_data, f, indent=2)
            
            logger.info(f"False positive rate comparison saved to: {comparison_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("OPTIMIZATION COMPLETE")
    print("="*60)
    print(f"Method: {method_desc}")
    print(f"Features optimized: {len(optimized_ranges)}")
    print(f"Datasets processed: {successful_loads}")
    print(f"Results saved to: {output_dir}")
    print("\nKey outputs:")
    print(f"  - Report: {report_file}")
    print(f"  - JSON: {json_file}")
    if args.compare_current and current_fp_rates:
        print(f"  - Comparison: {comparison_file}")
    
    if not args.report_only:
        print("\nNext steps:")
        print("  1. Review the optimization report")
        print("  2. Update validation expectation files with optimized ranges")
        print("  3. Test with validation datasets to verify false positive rates")


if __name__ == '__main__':
    main()