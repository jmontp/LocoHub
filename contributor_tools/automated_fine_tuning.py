#!/usr/bin/env python3
"""
Automated Fine-Tuning System - SUSPENDED PENDING BIOMECHANICAL VALIDATION

Created: 2025-06-11 with user permission
Purpose: Automated validation range setting using simple statistical methods

**IMPORTANT: This system is suspended as of 2025-06-20 pending integration of biomechanical constraints**
See biomechanical_constraints_requirements.md for details on required validation.

Intent:
This system automatically sets validation ranges by analyzing the actual data distribution
instead of using complex optimization algorithms. It's fast, simple, and data-driven.

**CORE PHILOSOPHY:**
"Why optimize existing ranges when you can just look at what the data actually looks like?"

**KEY ADVANTAGES:**
1. **Blazing Fast**: Single pass through data - no iterative algorithms
2. **Simple & Intuitive**: Uses standard statistical measures everyone understands  
3. **Data-Driven**: Ranges reflect actual data distribution, not arbitrary bounds
4. **Robust**: Works regardless of current validation state
5. **Explainable**: Clear methodology (e.g., "95% of data falls within these bounds")
6. **Immediate Results**: No waiting for convergence or parameter tuning

**STATISTICAL METHODS:**
- **percentile_95**: 2.5th to 97.5th percentiles (95% coverage, robust to outliers)
- **mean_3std**: Mean ± 3σ (99.7% coverage, assumes normal distribution)
- **iqr_expansion**: Q1-1.5×IQR to Q3+1.5×IQR (standard outlier detection)
- **percentile_90**: 5th to 95th percentiles (90% coverage, very robust)
- **robust_percentile**: 10th to 90th percentiles (80% coverage, conservative)  
- **conservative**: Min/max + 5% buffer (100% current data coverage)

Usage:
    # Recommended default - robust 95% coverage
    python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet
    
    # Conservative outlier-resistant method
    python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --method iqr_expansion
    
    # Normal distribution assumption (fastest)
    python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --method mean_3std

Perfect for initial range setting, quick updates, and evidence-based validation thresholds.
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import sys
import os
import warnings
import time
from datetime import datetime

# Get project root for file paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from user_libs.python.locomotion_data import LocomotionData
from user_libs.python.feature_constants import get_feature_list
from internal.config_management.config_manager import ValidationConfigManager

class AutomatedFineTuner:
    """
    Automated fine-tuning system using simple statistical methods.
    
    This class provides multiple statistical methods for setting validation ranges
    directly from data distributions - fast, simple, and data-driven.
    """
    
    def __init__(self, dataset_path: str, mode: str = 'kinematic'):
        """
        Initialize the statistical range tuner.
        
        Args:
            dataset_path: Path to the dataset parquet file
            mode: 'kinematic' or 'kinetic'
        """
        self.dataset_path = Path(dataset_path)
        self.mode = mode
        self.locomotion_data = None
        
        # Statistical methods available
        self.methods = {
            'mean_3std': self._method_mean_3std,
            'percentile_95': self._method_percentile_95,
            'percentile_90': self._method_percentile_90,
            'iqr_expansion': self._method_iqr_expansion,
            'robust_percentile': self._method_robust_percentile,
            'conservative': self._method_conservative
        }
        
        print(f"🤖 Automated Fine-Tuner Initialized")
        print(f"   📁 Dataset: {self.dataset_path.name}")
        print(f"   🔧 Mode: {self.mode}")
        print(f"   📈 Available methods: {list(self.methods.keys())}")
    
    def load_and_analyze_data(self) -> Dict[str, Dict[int, Dict[str, np.ndarray]]]:
        """
        Load dataset and organize data by task, phase, and variable for analysis.
        
        Returns:
            Dictionary structured as: {task: {phase: {variable: values_array}}}
        """
        print(f"\n📂 Loading and analyzing dataset...")
        
        # Load data using LocomotionData with custom column mapping
        try:
            self.locomotion_data = LocomotionData(str(self.dataset_path))
        except ValueError as e:
            if "Missing required columns: ['phase']" in str(e):
                # Try with phase_percent column mapping
                print(f"   ℹ️  Using 'phase_percent' column mapping for compatibility")
                self.locomotion_data = LocomotionData(
                    str(self.dataset_path),
                    phase_col='phase_percent'
                )
            else:
                raise e
        
        # Get all tasks and subjects
        tasks = self.locomotion_data.get_tasks()
        subjects = self.locomotion_data.get_subjects()
        
        print(f"   📊 Found {len(tasks)} tasks: {tasks}")
        print(f"   👥 Found {len(subjects)} subjects: {subjects}")
        
        # Get standard feature list for the mode
        standard_features = get_feature_list(self.mode)
        
        # Filter to only features actually available in the dataset
        available_features = self.locomotion_data.features
        feature_order = [f for f in standard_features if f in available_features]
        
        # Warn about missing features (but don't fail)
        missing_features = [f for f in standard_features if f not in available_features]
        if missing_features:
            print(f"   ⚠️  Missing {len(missing_features)} standard {self.mode} features: {missing_features[:3]}{'...' if len(missing_features) > 3 else ''}")
        
        print(f"   🔧 Using {len(feature_order)} standard {self.mode} features: {feature_order[:3]}{'...' if len(feature_order) > 3 else feature_order}")
        
        # Phase mapping (convert 0-149 indices to phase percentages)
        phase_indices = {
            0: 0,      # 0% -> index 0
            25: 37,    # 25% -> index ~37
            50: 75,    # 50% -> index ~75
            75: 112    # 75% -> index ~112
        }
        
        # Organize data by task, phase, and variable
        task_phase_data = {}
        
        for task in tasks:
            print(f"\n   🔍 Analyzing task: {task}")
            task_phase_data[task] = {}
            
            # Initialize phase structure
            for phase_pct in phase_indices.keys():
                task_phase_data[task][phase_pct] = {}
                for variable in feature_order:
                    # Convert variable name to match step classifier expectations
                    if variable.endswith('_rad'):
                        var_name = variable[:-4]  # Remove '_rad' suffix
                    else:
                        var_name = variable
                    task_phase_data[task][phase_pct][var_name] = []
            
            # Collect data from all subjects for this task
            total_cycles = 0
            for subject in subjects:
                try:
                    # Get cycles for this subject-task combination
                    cycles_data, feature_names = self.locomotion_data.get_cycles(
                        subject=subject,
                        task=task,
                        features=None
                    )
                    
                    if cycles_data.size == 0:
                        continue
                    
                    total_cycles += cycles_data.shape[0]
                    
                    # Extract values at representative phases
                    for phase_pct, phase_idx in phase_indices.items():
                        for feat_idx, feature_name in enumerate(feature_names):
                            if feat_idx < cycles_data.shape[2]:  # Ensure feature exists
                                # Get variable name for mapping
                                if feature_name.endswith('_rad'):
                                    var_name = feature_name[:-4]
                                else:
                                    var_name = feature_name
                                
                                if var_name in task_phase_data[task][phase_pct]:
                                    # Extract values at this phase from all cycles
                                    phase_values = cycles_data[:, phase_idx, feat_idx]
                                    task_phase_data[task][phase_pct][var_name].extend(phase_values)
                
                except Exception as e:
                    # Subject might not have data for this task
                    continue
            
            print(f"      📈 Total cycles: {total_cycles}")
            
            # Convert lists to numpy arrays for efficient computation
            for phase_pct in task_phase_data[task]:
                for var_name in task_phase_data[task][phase_pct]:
                    values = task_phase_data[task][phase_pct][var_name]
                    if values:
                        task_phase_data[task][phase_pct][var_name] = np.array(values)
                        print(f"      ✅ {var_name} Phase {phase_pct}%: {len(values)} values")
                    else:
                        task_phase_data[task][phase_pct][var_name] = np.array([])
        
        return task_phase_data
    
    def _method_mean_3std(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using mean ± 3 standard deviations.
        
        Covers approximately 99.7% of data assuming normal distribution.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        mean = np.mean(values)
        std = np.std(values)
        
        min_val = mean - 3 * std
        max_val = mean + 3 * std
        
        return min_val, max_val
    
    def _method_percentile_95(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using 2.5th to 97.5th percentiles (95% coverage).
        
        More robust to outliers than mean±3σ method.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        min_val = np.percentile(values, 2.5)
        max_val = np.percentile(values, 97.5)
        
        return min_val, max_val
    
    def _method_percentile_90(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using 5th to 95th percentiles (90% coverage).
        
        Even more robust to outliers, good for noisy data.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        min_val = np.percentile(values, 5)
        max_val = np.percentile(values, 95)
        
        return min_val, max_val
    
    def _method_iqr_expansion(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using IQR expansion: Q1 - 1.5*IQR to Q3 + 1.5*IQR.
        
        Standard method for outlier detection, very robust.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        min_val = q1 - 1.5 * iqr
        max_val = q3 + 1.5 * iqr
        
        return min_val, max_val
    
    def _method_robust_percentile(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using 10th to 90th percentiles (80% coverage).
        
        Very conservative, good for datasets with many outliers.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        min_val = np.percentile(values, 10)
        max_val = np.percentile(values, 90)
        
        return min_val, max_val
    
    def _method_conservative(self, values: np.ndarray) -> Tuple[float, float]:
        """
        Calculate range using min/max with small buffer.
        
        Guarantees 100% of current data passes, with 5% buffer for variation.
        """
        if len(values) == 0:
            return 0.0, 0.0
        
        data_min = np.min(values)
        data_max = np.max(values)
        
        # Add 5% buffer based on range
        range_width = data_max - data_min
        buffer = range_width * 0.05
        
        min_val = data_min - buffer
        max_val = data_max + buffer
        
        return min_val, max_val
    
    def calculate_statistical_ranges(self, task_phase_data: Dict, 
                                   method: str = 'percentile_95') -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Calculate validation ranges using specified statistical method.
        
        Args:
            task_phase_data: Raw data organized by task/phase/variable
            method: Statistical method to use
            
        Returns:
            Validation ranges in standard format: {task: {phase: {variable: {min, max}}}}
        """
        print(f"\n📊 Calculating ranges using method: {method}")
        
        if method not in self.methods:
            raise ValueError(f"Unknown method: {method}. Available: {list(self.methods.keys())}")
        
        stat_method = self.methods[method]
        validation_ranges = {}
        
        for task, task_data in task_phase_data.items():
            print(f"\n   🎯 Processing task: {task}")
            validation_ranges[task] = {}
            
            for phase_pct, phase_data in task_data.items():
                validation_ranges[task][phase_pct] = {}
                
                for var_name, values in phase_data.items():
                    if len(values) > 0:
                        min_val, max_val = stat_method(values)
                        
                        validation_ranges[task][phase_pct][var_name] = {
                            'min': min_val,
                            'max': max_val
                        }
                        
                        print(f"      ✅ {var_name} Phase {phase_pct}%: [{min_val:.3f}, {max_val:.3f}] "
                              f"(from {len(values)} values)")
                    else:
                        # No data available - use NaN to indicate missing data
                        validation_ranges[task][phase_pct][var_name] = {
                            'min': float('nan'),
                            'max': float('nan')
                        }
                        print(f"      ⚠️  {var_name} Phase {phase_pct}%: No data available, using NaN")
        
        return validation_ranges
    
    def generate_statistics_report(self, task_phase_data: Dict, 
                                 validation_ranges: Dict, method: str) -> str:
        """
        Generate a comprehensive statistics report.
        
        Args:
            task_phase_data: Raw data
            validation_ranges: Calculated ranges
            method: Statistical method used
            
        Returns:
            Formatted markdown report
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""# Automated Fine-Tuning Report

**Generated**: {timestamp}  
**Dataset**: {self.dataset_path.name}  
**Method**: {method}  
**Mode**: {self.mode}

## Method Description

"""
        
        # Add method description
        method_descriptions = {
            'mean_3std': "**Mean ± 3 Standard Deviations**: Covers ~99.7% of data assuming normal distribution. Good for well-behaved data.",
            'percentile_95': "**95% Percentile Range** (2.5th to 97.5th percentiles): Covers 95% of data, robust to outliers.",
            'percentile_90': "**90% Percentile Range** (5th to 95th percentiles): Covers 90% of data, very robust to outliers.",
            'iqr_expansion': "**IQR Expansion** (Q1-1.5×IQR to Q3+1.5×IQR): Standard outlier detection method, very robust.",
            'robust_percentile': "**Robust Percentiles** (10th to 90th): Conservative 80% coverage, excellent for noisy data.",
            'conservative': "**Conservative Min/Max**: Guarantees 100% current data coverage with 5% buffer."
        }
        
        report += method_descriptions.get(method, f"Method: {method}") + "\n\n"
        
        # Task summary
        report += "## Task Summary\n\n"
        report += "| Task | Total Data Points | Variables Analyzed | Phases |\n"
        report += "|------|-------------------|-------------------|--------|\n"
        
        for task, task_data in task_phase_data.items():
            total_points = 0
            variables_with_data = set()
            phases = len(task_data)
            
            for phase_pct, phase_data in task_data.items():
                for var_name, values in phase_data.items():
                    if len(values) > 0:
                        total_points += len(values)
                        variables_with_data.add(var_name)
            
            report += f"| {task} | {total_points:,} | {len(variables_with_data)} | {phases} |\n"
        
        # Range summary by task
        for task in validation_ranges:
            report += f"\n## Task: {task}\n\n"
            report += "| Variable | Phase | Min Value | Max Value | Range Width | Data Points |\n"
            report += "|----------|-------|-----------|-----------|-------------|-------------|\n"
            
            for phase_pct in sorted(validation_ranges[task].keys()):
                for var_name, range_data in validation_ranges[task][phase_pct].items():
                    min_val = range_data['min']
                    max_val = range_data['max']
                    width = max_val - min_val
                    
                    # Get data point count
                    data_points = len(task_phase_data[task][phase_pct][var_name])
                    
                    report += f"| {var_name} | {phase_pct}% | {min_val:.3f} | {max_val:.3f} | {width:.3f} | {data_points} |\n"
        
        # Coverage analysis
        report += "\n## Coverage Analysis\n\n"
        report += "This analysis shows how well the calculated ranges cover the actual data:\n\n"
        
        for task, task_data in task_phase_data.items():
            report += f"### {task}\n\n"
            
            total_values = 0
            covered_values = 0
            
            for phase_pct, phase_data in task_data.items():
                for var_name, values in phase_data.items():
                    if len(values) > 0:
                        total_values += len(values)
                        
                        # Check coverage
                        min_range = validation_ranges[task][phase_pct][var_name]['min']
                        max_range = validation_ranges[task][phase_pct][var_name]['max']
                        
                        covered = np.sum((values >= min_range) & (values <= max_range))
                        covered_values += covered
            
            coverage_pct = (covered_values / total_values * 100) if total_values > 0 else 0
            report += f"- **Overall Coverage**: {coverage_pct:.1f}% ({covered_values:,}/{total_values:,} values)\n"
        
        report += f"""
## Statistical Method Benefits

**Efficiency**: Single pass through data - no iterative optimization required  
**Simplicity**: Direct statistical calculation - easy to understand and verify  
**Robustness**: Based on actual data distribution, not dependent on existing ranges  
**Speed**: Typically 10-100x faster than optimization-based approaches  
**Reproducibility**: Deterministic results from same data and method  

## Implementation Notes

- Ranges calculated independently for each task-phase-variable combination
- Representative phases used: 0% (heel strike), 25% (mid-stance), 50% (toe-off), 75% (mid-swing)
- All calculations performed on actual biomechanical data values
- Method can be easily re-run as new data becomes available

---

*Generated by Automated Fine-Tuning System - Simple, Fast, Data-Driven*
"""
        
        return report
    
    def run_statistical_tuning(self, method: str = 'percentile_95',
                             save_ranges: bool = True,
                             save_report: bool = False) -> Dict[str, Any]:
        """
        Run the complete statistical range tuning workflow.
        
        Args:
            method: Statistical method to use
            save_ranges: Whether to save ranges to validation file
            save_report: Whether to save detailed report
            
        Returns:
            Dictionary with results and file paths
        """
        print(f"🚀 Starting Automated Fine-Tuning")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Step 1: Load and analyze data
            task_phase_data = self.load_and_analyze_data()
            
            # Step 2: Calculate ranges using statistical method
            validation_ranges = self.calculate_statistical_ranges(task_phase_data, method)
            
            # Step 3: Generate report
            report_file = None
            if save_report:
                print(f"\n📄 Generating statistics report...")
                report_content = self.generate_statistics_report(
                    task_phase_data, validation_ranges, method
                )
                
                # Save report to proper directory
                reports_dir = project_root / "docs" / "reference" / "validation_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                report_file = reports_dir / f"automated_fine_tuning_report_{method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                with open(report_file, 'w') as f:
                    f.write(report_content)
                print(f"   ✅ Report saved: {report_file.relative_to(project_root)}")
            
            # Step 4: Save ranges to YAML config file
            saved_file = None
            if save_ranges:
                print(f"\n💾 Saving statistical ranges to YAML config...")
                
                # Create ConfigManager and set data
                config_mgr = ValidationConfigManager()
                dataset_name = self.dataset_path.name
                
                # Set the validation data
                config_mgr.set_data(validation_ranges)
                
                # Set metadata
                config_mgr.set_metadata('source_dataset', dataset_name)
                config_mgr.set_metadata('method', method)
                config_mgr.set_metadata('generated_by', 'AutomatedFineTuner')
                config_mgr.set_metadata('description', f'Validation ranges generated from {dataset_name} using {method} method')
                
                # Generate filename based on timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"tuned_ranges_{timestamp}.yaml"
                save_path = config_mgr.config_dir / filename
                
                # Save to YAML config
                config_mgr.save(save_path)
                
                saved_file = str(save_path)
                print(f"   ✅ Ranges saved to: {Path(saved_file).name}")
            
            # Step 5: Generate summary
            end_time = time.time()
            duration = end_time - start_time
            
            # Count total ranges set
            total_ranges = 0
            for task_ranges in validation_ranges.values():
                for phase_ranges in task_ranges.values():
                    total_ranges += len(phase_ranges)
            
            print(f"\n🎉 Automated Fine-Tuning Complete!")
            print(f"{'='*60}")
            print(f"⏱️  Duration: {duration:.1f} seconds")
            print(f"📊 Method: {method}")
            print(f"🎯 Tasks processed: {len(validation_ranges)}")
            print(f"📈 Total ranges set: {total_ranges}")
            print(f"💾 Saved to: {saved_file.split('/')[-1] if saved_file else 'Not saved'}")
            
            return {
                'success': True,
                'method': method,
                'validation_ranges': validation_ranges,
                'task_phase_data': task_phase_data,
                'saved_file': saved_file,
                'report_file': report_file if save_report else None,
                'duration': duration,
                'total_ranges': total_ranges
            }
            
        except Exception as e:
            print(f"\n❌ Statistical tuning failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Automated Fine-Tuning System - Simple, Fast, Data-Driven",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Statistical Methods:
  mean_3std         : Mean ± 3 standard deviations (~99.7% coverage)
  percentile_95     : 2.5th to 97.5th percentiles (95% coverage, robust)
  percentile_90     : 5th to 95th percentiles (90% coverage, very robust)
  iqr_expansion     : Q1-1.5×IQR to Q3+1.5×IQR (standard outlier detection)
  robust_percentile : 10th to 90th percentiles (80% coverage, conservative)
  conservative      : Min/max with 5% buffer (100% coverage)

Examples:
  # Quick 95% coverage (recommended default)
  python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet
  
  # Conservative outlier-resistant method
  python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --method iqr_expansion
  
  # Normal distribution assumption (fast)
  python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --method mean_3std
  
  # Generate detailed report
  python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --save-report
  
  # Generate report only (don't save ranges)
  python contributor_tools/automated_fine_tuning.py --dataset dataset.parquet --no-save-ranges --save-report
        """
    )
    
    parser.add_argument('--dataset', required=True,
                       help='Path to the dataset parquet file')
    parser.add_argument('--method', 
                       choices=['mean_3std', 'percentile_95', 'percentile_90', 
                               'iqr_expansion', 'robust_percentile', 'conservative'],
                       default='percentile_95',
                       help='Statistical method for range calculation')
    parser.add_argument('--mode', choices=['kinematic', 'kinetic'],
                       default='kinematic',
                       help='Validation mode')
    parser.add_argument('--no-save-ranges', action='store_true',
                       help='Generate report only, do not save ranges')
    parser.add_argument('--save-report', action='store_true',
                       help='Save detailed statistical report to docs/reference/validation_reports/')
    
    args = parser.parse_args()
    
    # Validate dataset path
    if not Path(args.dataset).exists():
        print(f"❌ Dataset file not found: {args.dataset}")
        return 1
    
    # Initialize tuner
    tuner = AutomatedFineTuner(
        dataset_path=args.dataset,
        mode=args.mode
    )
    
    # Run statistical tuning
    results = tuner.run_statistical_tuning(
        method=args.method,
        save_ranges=not args.no_save_ranges,
        save_report=args.save_report
    )
    
    return 0 if results['success'] else 1


if __name__ == "__main__":
    exit(main())