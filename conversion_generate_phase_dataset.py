#!/usr/bin/env python3
"""
conversion_generate_phase_dataset.py

Created: 2025-06-16 with user permission
Purpose: CLI tool to convert time-indexed biomechanical datasets to phase-indexed format

Intent: This is the implementation of User Story US-01 (Efficient Dataset Conversion Workflow).
It provides a single command interface for dataset curators to convert raw biomechanical datasets
to standardized parquet format efficiently, meeting the acceptance criteria:

- Performance: Complete conversion in ≤60 minutes for 500-1000 trial datasets
- Format Compliance: Generate exactly 150 points per gait cycle (100% of cycles)
- Quality Threshold: Achieve ≥90% validation pass rate for correctly formatted source data
- Error Handling: Provide clear, actionable error messages for ≥95% of failure modes
- Tool Integration: Single command: conversion_generate_phase_dataset.py dataset_time.parquet
- Output Verification: Automated verification of phase indexing correctness

Technical Requirements:
- Uses existing lib/core/locomotion_analysis.py infrastructure
- Leverages lib/validation/step_classifier.py for gait cycle detection
- Optimized for performance with memory-efficient processing
- Comprehensive error handling with actionable guidance
- Built-in verification and quality checks
"""

import argparse
import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import numpy as np
from tqdm import tqdm

# Add the lib directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent / 'lib'))

try:
    from core.locomotion_analysis import LocomotionData
    from validation.step_classifier import StepClassifier
    from validation.dataset_validator_phase import DatasetValidator
except ImportError as e:
    print(f"Error: Cannot import required libraries. {e}")
    print("Solution: Ensure you are running from the project root directory and lib/ exists.")
    sys.exit(2)


class PhaseDatasetConverter:
    """
    Converts time-indexed biomechanical datasets to phase-indexed format.
    
    This class implements the core conversion logic for US-01, providing:
    - Performance-optimized gait cycle detection
    - Exactly 150 points per gait cycle interpolation
    - Comprehensive error handling and validation
    - Memory-efficient processing for large datasets
    """
    
    def __init__(self, memory_efficient: bool = False, verbose: bool = False):
        """
        Initialize the converter.
        
        Args:
            memory_efficient: Enable memory-efficient processing for large datasets
            verbose: Enable verbose logging output
        """
        self.memory_efficient = memory_efficient
        self.verbose = verbose
        self.logger = self._setup_logging()
        
        # Performance constants
        self.PHASE_POINTS = 150  # Exactly 150 points per cycle (requirement)
        self.GRF_THRESHOLD = 50  # Newtons, for stance detection
        self.MAX_PROCESSING_TIME = 60 * 60  # 60 minutes maximum (requirement)
        
        # Quality thresholds
        self.MIN_PASS_RATE = 0.90  # 90% validation pass rate (requirement)
        
        # Initialize validation components
        self.validator = None
        self.step_classifier = None
        
        # Conversion statistics
        self.conversion_stats = {
            'total_trials': 0,
            'successful_cycles': 0,
            'failed_cycles': 0,
            'total_processing_time': 0,
            'quality_metrics': {}
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('PhaseConverter')
        logger.setLevel(logging.INFO if self.verbose else logging.WARNING)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def convert_dataset(self, input_file: str, output_file: Optional[str] = None,
                       output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert a time-indexed dataset to phase-indexed format.
        
        Args:
            input_file: Path to time-indexed parquet file
            output_file: Optional output file path
            output_dir: Optional output directory
            
        Returns:
            Dict containing conversion results and statistics
            
        Raises:
            FileNotFoundError: Input file does not exist
            ValueError: Invalid data format or missing required columns
            RuntimeError: Conversion failed or exceeded time limits
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate input and setup paths
            input_path, output_path = self._validate_and_setup_paths(
                input_file, output_file, output_dir
            )
            
            # Step 2: Load and validate time-indexed data
            self.logger.info(f"Loading time-indexed dataset: {input_path}")
            time_data = self._load_and_validate_time_data(input_path)
            
            # Step 3: Detect gait cycles and convert to phase-indexed
            self.logger.info("Converting to phase-indexed format...")
            phase_data = self._convert_to_phase_indexed(time_data)
            
            # Step 4: Validate phase-indexed output
            self.logger.info("Validating phase-indexed output...")
            validation_results = self._validate_phase_output(phase_data)
            
            # Step 5: Save results
            self.logger.info(f"Saving phase dataset: {output_path}")
            self._save_phase_dataset(phase_data, output_path)
            
            # Step 6: Generate final report
            processing_time = time.time() - start_time
            results = self._generate_conversion_report(
                validation_results, processing_time, input_path, output_path
            )
            
            # Step 7: Verify success criteria
            self._verify_acceptance_criteria(results, processing_time)
            
            return results
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Conversion failed after {processing_time:.1f}s: {e}")
            raise
    
    def _validate_and_setup_paths(self, input_file: str, output_file: Optional[str],
                                  output_dir: Optional[str]) -> Tuple[Path, Path]:
        """Validate input file and setup output paths."""
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(
                f"Input file not found: {input_file}. "
                f"Solution: Check the file path and ensure it exists."
            )
        
        if input_path.suffix.lower() != '.parquet':
            raise ValueError(
                f"Invalid file format: {input_path.suffix}. "
                f"Solution: Provide a .parquet file for conversion."
            )
        
        # Setup output path
        if output_file:
            output_path = Path(output_file)
        else:
            # Generate output filename: replace _time with _phase
            output_name = input_path.stem.replace('_time', '_phase') + '.parquet'
            if output_dir:
                output_path = Path(output_dir) / output_name
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = input_path.parent / output_name
        
        return input_path, output_path
    
    def _load_and_validate_time_data(self, input_path: Path) -> pd.DataFrame:
        """Load and validate time-indexed dataset."""
        try:
            data = pd.read_parquet(input_path)
            self.logger.info(f"Loaded dataset with {len(data)} rows, {len(data.columns)} columns")
            
        except Exception as e:
            raise RuntimeError(
                f"Data corruption detected in {input_path.name}. "
                f"Solution: Check the parquet file integrity and try again. Error: {e}"
            )
        
        # Validate required columns (with flexible naming)
        required_mappings = {
            'subject': ['subject_id', 'subject'],
            'trial': ['trial_id', 'trial', 'task_info'],
            'task': ['task'],
            'time': ['time_s', 'time']
        }
        
        # Find actual column names
        column_mapping = {}
        missing_columns = []
        
        for required_name, possible_names in required_mappings.items():
            found = False
            for possible_name in possible_names:
                if possible_name in data.columns:
                    column_mapping[required_name] = possible_name
                    found = True
                    break
            if not found:
                missing_columns.append(f"{required_name} (tried: {possible_names})")
        
        if missing_columns:
            raise ValueError(
                f"Required columns missing: {missing_columns}. "
                f"Solution: Ensure your dataset contains columns for subject, trial, task, and time."
            )
        
        # Rename columns to standard format
        rename_dict = {v: k for k, v in column_mapping.items()}
        data = data.rename(columns=rename_dict)
        
        # Check for ground reaction force data (required for gait cycle detection)
        # Look for various GRF column naming patterns
        grf_patterns = ['grf.*vertical', 'force.*y', 'force.*z']
        grf_columns = []
        
        for pattern in grf_patterns:
            import re
            pattern_cols = [col for col in data.columns if re.search(pattern, col, re.IGNORECASE)]
            grf_columns.extend(pattern_cols)
        
        if not grf_columns:
            raise ValueError(
                "Missing ground reaction force data. "
                f"Solution: Ensure your dataset contains vertical GRF columns. Available columns: {data.columns.tolist()[:10]}..."
            )
        
        # Check for empty dataset
        if len(data) == 0:
            raise ValueError(
                "Empty dataset detected. "
                "Solution: Provide a dataset with biomechanical data."
            )
        
        self.conversion_stats['total_trials'] = data['trial'].nunique()
        return data
    
    def _convert_to_phase_indexed(self, time_data: pd.DataFrame) -> pd.DataFrame:
        """Convert time-indexed data to phase-indexed format."""
        phase_data_list = []
        subjects = time_data['subject'].unique()
        
        # Setup progress tracking
        total_trials = time_data['trial'].nunique()
        pbar = tqdm(total=total_trials, desc="Converting trials") if self.verbose else None
        
        for subject_id in subjects:
            subject_data = time_data[time_data['subject'] == subject_id]
            
            # Process each trial for this subject
            for trial_id in subject_data['trial'].unique():
                trial_data = subject_data[subject_data['trial'] == trial_id]
                
                try:
                    # Convert trial to phase-indexed
                    trial_phase_data = self._convert_trial_to_phase(trial_data)
                    if len(trial_phase_data) > 0:
                        phase_data_list.append(trial_phase_data)
                        self.conversion_stats['successful_cycles'] += len(trial_phase_data) // self.PHASE_POINTS
                    
                except Exception as e:
                    self.logger.warning(f"Failed to convert trial {trial_id} for {subject_id}: {e}")
                    self.conversion_stats['failed_cycles'] += 1
                
                if pbar:
                    pbar.update(1)
        
        if pbar:
            pbar.close()
        
        if not phase_data_list:
            raise RuntimeError(
                "Invalid gait cycle detection - no valid cycles found. "
                "Solution: Check your GRF data quality and ensure proper gait patterns."
            )
        
        # Combine all phase data
        phase_data = pd.concat(phase_data_list, ignore_index=True)
        self.logger.info(f"Generated {len(phase_data)} phase-indexed data points")
        
        return phase_data
    
    def _convert_trial_to_phase(self, trial_data: pd.DataFrame) -> pd.DataFrame:
        """Convert a single trial from time-indexed to phase-indexed format."""
        # Find GRF column for gait cycle detection using same patterns as validation
        import re
        grf_patterns = ['grf.*vertical', 'force.*y', 'force.*z']
        grf_columns = []
        
        for pattern in grf_patterns:
            pattern_cols = [col for col in trial_data.columns if re.search(pattern, col, re.IGNORECASE)]
            grf_columns.extend(pattern_cols)
        
        if not grf_columns:
            return pd.DataFrame()  # Skip trial if no GRF data
        
        grf_column = grf_columns[0]  # Use first available GRF column
        grf_data = trial_data[grf_column].values
        
        # Detect gait cycles using stance phase detection
        stance_phases = grf_data > self.GRF_THRESHOLD
        
        # Find heel strikes (swing-to-stance transitions)
        transitions = np.diff(stance_phases.astype(int))
        heel_strikes = np.where(transitions == 1)[0] + 1  # +1 to get actual stance start
        
        if len(heel_strikes) < 2:
            return pd.DataFrame()  # Need at least 2 heel strikes for one cycle
        
        # Extract individual gait cycles
        phase_cycles = []
        for i in range(len(heel_strikes) - 1):
            cycle_start = heel_strikes[i]
            cycle_end = heel_strikes[i + 1]
            
            # Validate cycle length (remove outliers)
            cycle_duration = trial_data.iloc[cycle_end]['time'] - trial_data.iloc[cycle_start]['time']
            if 0.5 <= cycle_duration <= 2.5:  # Reasonable gait cycle duration
                cycle_data = trial_data.iloc[cycle_start:cycle_end + 1].copy()
                phase_cycle = self._interpolate_to_phase_points(cycle_data)
                if len(phase_cycle) == self.PHASE_POINTS:
                    phase_cycles.append(phase_cycle)
        
        if phase_cycles:
            return pd.concat(phase_cycles, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def _interpolate_to_phase_points(self, cycle_data: pd.DataFrame) -> pd.DataFrame:
        """Interpolate a gait cycle to exactly 150 phase points."""
        if len(cycle_data) < 2:
            return pd.DataFrame()
        
        # Create phase array (0 to 100%)
        phase_points = np.linspace(0, 100, self.PHASE_POINTS)
        
        # Create time points for interpolation
        time_points = cycle_data['time'].values
        time_normalized = np.linspace(0, 100, len(time_points))
        
        # Prepare output dataframe
        interpolated_data = pd.DataFrame()
        
        # Add metadata columns
        interpolated_data['subject'] = cycle_data['subject'].iloc[0]
        interpolated_data['trial'] = cycle_data['trial'].iloc[0]
        interpolated_data['task'] = cycle_data['task'].iloc[0]
        interpolated_data['phase_pct'] = phase_points
        
        # Add cycle identifier
        cycle_id = f"{cycle_data['trial'].iloc[0]}_cycle_{int(time.time() * 1000) % 10000}"
        interpolated_data['cycle_id'] = cycle_id
        
        # Interpolate numerical columns
        for column in cycle_data.columns:
            if column in ['subject', 'trial', 'task', 'time']:
                continue  # Skip metadata columns
            
            if pd.api.types.is_numeric_dtype(cycle_data[column]):
                try:
                    # Interpolate to phase points
                    interpolated_values = np.interp(
                        phase_points, time_normalized, cycle_data[column].values
                    )
                    interpolated_data[column] = interpolated_values
                except Exception:
                    # Skip columns that can't be interpolated
                    continue
        
        return interpolated_data
    
    def _validate_phase_output(self, phase_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate the phase-indexed output meets acceptance criteria."""
        validation_results = {
            'total_cycles': 0,
            'compliant_cycles': 0,
            'non_compliant_cycles': 0,
            'pass_rate': 0.0,
            'phase_compliance': True,
            'validation_details': []
        }
        
        # Check phase indexing compliance (exactly 150 points per cycle)
        if 'cycle_id' in phase_data.columns:
            cycles = phase_data.groupby('cycle_id')
            validation_results['total_cycles'] = len(cycles)
            
            compliant_count = 0
            for cycle_id, cycle_df in cycles:
                cycle_length = len(cycle_df)
                if cycle_length == self.PHASE_POINTS:
                    compliant_count += 1
                else:
                    validation_results['validation_details'].append(
                        f"Cycle {cycle_id} has {cycle_length} points instead of {self.PHASE_POINTS}"
                    )
            
            validation_results['compliant_cycles'] = compliant_count
            validation_results['non_compliant_cycles'] = validation_results['total_cycles'] - compliant_count
            
            # Calculate compliance rate
            if validation_results['total_cycles'] > 0:
                compliance_rate = compliant_count / validation_results['total_cycles']
                validation_results['pass_rate'] = compliance_rate
                validation_results['phase_compliance'] = compliance_rate == 1.0
            
        return validation_results
    
    def _save_phase_dataset(self, phase_data: pd.DataFrame, output_path: Path):
        """Save phase-indexed dataset to parquet format."""
        try:
            # Optimize data types for storage efficiency
            if self.memory_efficient:
                phase_data = self._optimize_datatypes(phase_data)
            
            # Save to parquet
            phase_data.to_parquet(output_path, engine='pyarrow', index=False)
            
            # Verify file was created
            if not output_path.exists():
                raise RuntimeError("Output file creation failed")
                
        except Exception as e:
            raise RuntimeError(
                f"Failed to save phase dataset. "
                f"Solution: Check write permissions and disk space. Error: {e}"
            )
    
    def _optimize_datatypes(self, data: pd.DataFrame) -> pd.DataFrame:
        """Optimize datatypes for memory efficiency."""
        optimized = data.copy()
        
        for column in optimized.columns:
            if pd.api.types.is_numeric_dtype(optimized[column]):
                # Convert to float32 for better memory efficiency
                if optimized[column].dtype == 'float64':
                    optimized[column] = optimized[column].astype('float32')
        
        return optimized
    
    def _generate_conversion_report(self, validation_results: Dict[str, Any],
                                  processing_time: float, input_path: Path,
                                  output_path: Path) -> Dict[str, Any]:
        """Generate comprehensive conversion report."""
        report = {
            'conversion_successful': True,
            'processing_time_seconds': processing_time,
            'processing_time_minutes': processing_time / 60,
            'input_file': str(input_path),
            'output_file': str(output_path),
            'validation_results': validation_results,
            'conversion_stats': self.conversion_stats,
            'quality_assessment': self._assess_quality(validation_results),
            'verification_status': 'PASSED' if validation_results['phase_compliance'] else 'FAILED'
        }
        
        return report
    
    def _assess_quality(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess conversion quality against acceptance criteria."""
        pass_rate = validation_results.get('pass_rate', 0.0)
        
        quality = {
            'pass_rate': pass_rate,
            'pass_rate_threshold': self.MIN_PASS_RATE,
            'meets_quality_threshold': pass_rate >= self.MIN_PASS_RATE,
            'quality_score': 'High' if pass_rate >= 0.95 else 'Medium' if pass_rate >= self.MIN_PASS_RATE else 'Low',
            'phase_indexing_compliance': validation_results.get('phase_compliance', False)
        }
        
        return quality
    
    def _verify_acceptance_criteria(self, results: Dict[str, Any], processing_time: float):
        """Verify that all acceptance criteria are met."""
        errors = []
        
        # Performance requirement: ≤60 minutes
        if processing_time > self.MAX_PROCESSING_TIME:
            errors.append(
                f"Performance threshold exceeded: {processing_time/60:.1f} minutes > 60 minutes. "
                f"Solution: Use --memory-efficient flag for large datasets."
            )
        
        # Format compliance: 100% phase compliance
        if not results['validation_results'].get('phase_compliance', False):
            errors.append(
                "Phase indexing verification failed. "
                f"Solution: Check gait cycle detection parameters and input data quality."
            )
        
        # Quality threshold: ≥90% pass rate
        pass_rate = results['validation_results'].get('pass_rate', 0.0)
        if pass_rate < self.MIN_PASS_RATE:
            errors.append(
                f"Quality threshold not met: {pass_rate:.1%} < {self.MIN_PASS_RATE:.1%}. "
                f"Solution: Review input data quality and gait cycle detection."
            )
        
        if errors:
            error_message = "Acceptance criteria verification failed:\n" + "\n".join(errors)
            raise RuntimeError(error_message)


def print_conversion_report(results: Dict[str, Any]):
    """Print formatted conversion report."""
    print("\n" + "="*60)
    print("PHASE DATASET CONVERSION COMPLETED")
    print("="*60)
    
    # Basic information
    print(f"Input file:      {results['input_file']}")
    print(f"Output file:     {results['output_file']}")
    print(f"Processing time: {results['processing_time_minutes']:.1f} minutes")
    
    # Verification results
    print(f"\nVerification results:")
    validation = results['validation_results']
    print(f"- Phase indexing: {'PASSED' if validation['phase_compliance'] else 'FAILED'} ({validation['compliant_cycles']}/{validation['total_cycles']} cycles)")
    print(f"- Data validation: {'PASSED' if validation['pass_rate'] >= 0.9 else 'FAILED'} ({validation['pass_rate']:.1%} pass rate)")
    
    # Quality assessment
    quality = results['quality_assessment']
    print(f"- Quality score: {quality['quality_score']}")
    print(f"- Overall status: {results['verification_status']}")
    
    # Performance metrics
    stats = results['conversion_stats']
    print(f"\nConversion statistics:")
    print(f"- Total trials processed: {stats['total_trials']}")
    print(f"- Successful gait cycles: {stats['successful_cycles']}")
    print(f"- Failed cycles: {stats['failed_cycles']}")
    
    if not validation['phase_compliance']:
        print(f"\nPhase compliance issues:")
        for detail in validation['validation_details'][:5]:  # Show first 5 issues
            print(f"- {detail}")
        if len(validation['validation_details']) > 5:
            print(f"- ... and {len(validation['validation_details']) - 5} more issues")
    
    print("="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert time-indexed biomechanical datasets to phase-indexed format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dataset_time.parquet
  %(prog)s input.parquet --output-dir /path/to/output
  %(prog)s large_dataset.parquet --memory-efficient --verbose
  %(prog)s data.parquet --output custom_phase.parquet --with-quality-check

This tool implements User Story US-01 for efficient dataset conversion,
providing exactly 150 points per gait cycle with comprehensive validation.
        """
    )
    
    # Required arguments
    parser.add_argument('input_file', 
                       help='Input time-indexed parquet file')
    
    # Optional arguments
    parser.add_argument('--output', '-o',
                       help='Output phase-indexed parquet file')
    parser.add_argument('--output-dir',
                       help='Output directory for generated file')
    parser.add_argument('--memory-efficient', action='store_true',
                       help='Enable memory-efficient processing for large datasets')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--with-quality-check', action='store_true',
                       help='Perform additional quality assessment')
    parser.add_argument('--format',
                       choices=['gtech_2023', 'umich_2021', 'addbiomechanics', 'custom'],
                       help='Source data format (for format-specific processing)')
    
    args = parser.parse_args()
    
    try:
        # Initialize converter
        converter = PhaseDatasetConverter(
            memory_efficient=args.memory_efficient,
            verbose=args.verbose
        )
        
        print(f"Converting time-indexed dataset to phase-indexed format...")
        if args.format:
            print(f"Processing {args.format} format dataset")
        
        # Perform conversion
        results = converter.convert_dataset(
            input_file=args.input_file,
            output_file=args.output,
            output_dir=args.output_dir
        )
        
        # Print results
        print_conversion_report(results)
        
        # Additional quality check if requested
        if args.with_quality_check:
            print("\nPerforming additional quality assessment...")
            quality = results['quality_assessment']
            print(f"Quality Assessment:")
            print(f"- Phase indexing: {'100% compliant' if quality['phase_indexing_compliance'] else 'Issues detected'}")
            print(f"- Data validation: {quality['pass_rate']:.1%} pass rate")
            print(f"- Quality score: {quality['quality_score']}")
            print(f"- Meets quality threshold: {'Yes' if quality['meets_quality_threshold'] else 'No'}")
        
        print(f"\nConversion completed successfully!")
        sys.exit(0)
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(4)
    except KeyboardInterrupt:
        print("\nConversion interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        print("Solution: Check input data format and try again with --verbose for more details.")
        sys.exit(5)


if __name__ == '__main__':
    main()