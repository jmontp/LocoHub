#!/usr/bin/env python3
"""
Dataset Validator

Focused validation script that loads phase-based datasets and validates each step
against the kinematic and kinetic expectations defined in the specification files:
- docs/standard_spec/validation_expectations_kinematic.md
- docs/standard_spec/validation_expectations_kinetic.md

This validator:
1. Loads phase-based parquet datasets (requires _phase.parquet format)
2. Validates each step against expected ranges at key phases (0%, 25%, 50%, 75%)
3. Reports validation failures with detailed analysis
4. Provides step-by-step validation results

Usage:
    python dataset_validator.py --dataset <dataset>_phase.parquet [--output validation_reports/]
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import validation parser modules
try:
    from validation.validation_expectations_parser import parse_kinematic_validation_expectations, parse_kinetic_validation_expectations
except ImportError as e:
    raise ImportError(f"Could not import validation parser modules: {e}")

class DatasetValidator:
    """
    Focused dataset validator that validates phase-based locomotion datasets
    against kinematic and kinetic expectations from specification files.
    """
    
    def __init__(self, dataset_path: str, output_dir: str = "validation_reports"):
        """
        Initialize the dataset validator.
        
        Args:
            dataset_path: Path to the phase-based dataset parquet file (must be *_phase.parquet)
            output_dir: Directory to save validation reports (default: validation_reports)
        """
        self.dataset_path = dataset_path
        
        # Create simple output directory structure
        dataset_name = Path(dataset_path).stem  # Extract dataset name without .parquet extension
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create reports directory
        self.reports_dir = self.output_dir
        self.reports_dir.mkdir(exist_ok=True)
            
        # Load validation expectations from specification files
        self.kinematic_expectations = self._load_kinematic_expectations()
        self.kinetic_expectations = self._load_kinetic_expectations()
        
        # Storage for validation results
        self.validation_results = {}
        self.step_failures = []
        
        # Task mapping from dataset names to validation expectation names
        self.task_mapping = {
            'normal_walk': 'level_walking',
            'level_walking': 'level_walking',
            'incline_walk': 'incline_walking', 
            'incline_walking': 'incline_walking',
            'decline_walk': 'decline_walking',
            'decline_walking': 'decline_walking',
            'up_stairs': 'up_stairs',
            'down_stairs': 'down_stairs',
            'stairs': 'up_stairs',  # Default to up_stairs if not specified
            'sit_to_stand': 'sit_to_stand',
            'jump': 'jump',
            'squats': 'squats',
            'run': 'run',
            'running': 'run'
        }
        
    def _load_kinematic_expectations(self) -> Dict:
        """Load kinematic validation expectations from markdown file."""
        expectations_path = Path(__file__).parent.parent.parent / "docs" / "standard_spec" / "validation_expectations_kinematic.md"
        if expectations_path.exists():
            try:
                return parse_kinematic_validation_expectations(str(expectations_path))
            except Exception as e:
                print(f"Warning: Could not parse kinematic expectations: {e}")
                return {}
        return {}
    
    def _load_kinetic_expectations(self) -> Dict:
        """Load kinetic validation expectations from markdown file."""
        expectations_path = Path(__file__).parent.parent.parent / "docs" / "standard_spec" / "validation_expectations_kinetic.md" 
        if expectations_path.exists():
            try:
                return parse_kinetic_validation_expectations(str(expectations_path))
            except Exception as e:
                print(f"Warning: Could not parse kinetic expectations: {e}")
                return {}
        return {}
    
    def load_dataset(self) -> pd.DataFrame:
        """Load and validate the dataset structure. Only works with phase-based datasets."""
        # Check if this is a phase-based dataset according to standard spec
        if '_phase' not in str(self.dataset_path):
            raise ValueError(
                f"Validation only works with phase-based datasets.\n"
                f"Expected filename pattern: <dataset>_phase.parquet\n"
                f"Provided: {self.dataset_path}\n"
                f"Please convert to phase-based format first (150 points per gait cycle)."
            )
        
        try:
            df = pd.read_parquet(self.dataset_path)
            print(f"✅ Loaded phase-based dataset: {len(df)} rows, {len(df.columns)} columns")
            
            # Verify phase-based structure (should have phase column)
            phase_columns = [col for col in df.columns if 'phase' in col.lower()]
            if not any(col in df.columns for col in ['phase_percent', 'phase_%', 'phase_r', 'phase_l']):
                raise ValueError(
                    f"Phase-based dataset missing phase column.\n"
                    f"Expected: 'phase_percent', 'phase_%', 'phase_r', or 'phase_l'\n"
                    f"Available columns: {list(df.columns)[:10]}...\n"
                    f"Found phase-related columns: {phase_columns}"
                )
            
            # Verify step structure (each step should have ~150 points)
            if 'step' in df.columns or 'cycle' in df.columns:
                step_col = 'step' if 'step' in df.columns else 'cycle'
                if 'subject' in df.columns and 'task' in df.columns:
                    step_sizes = df.groupby(['subject', 'task', step_col]).size()
                    expected_size = 150
                    if not step_sizes.between(140, 160).all():  # Allow some tolerance
                        print(f"⚠️  WARNING: Some steps don't have ~150 points as expected for phase data")
                        print(f"   Step sizes range: {step_sizes.min()} to {step_sizes.max()}")
            
            return df
        except Exception as e:
            raise RuntimeError(f"Error loading dataset: {e}")
    
    def validate_data_point(self, value: float, expected_range: Dict[str, float], variable: str, phase: float) -> Tuple[bool, str]:
        """
        Validate a single data point against expected ranges.
        
        Args:
            value: The data value to validate
            expected_range: Dictionary with 'min' and 'max' values
            variable: Variable name being validated
            phase: Phase percentage where validation occurs
            
        Returns:
            Tuple of (is_valid, failure_reason)
        """
        if pd.isna(value):
            return False, f"NaN value at phase {phase:.1f}%"
        
        min_val = expected_range['min']
        max_val = expected_range['max']
        
        if value < min_val:
            return False, f"Value {value:.3f} below minimum {min_val:.3f} at phase {phase:.1f}%"
        elif value > max_val:
            return False, f"Value {value:.3f} above maximum {max_val:.3f} at phase {phase:.1f}%"
        else:
            return True, "Valid"
    
    def validate_step_against_expectations(self, step_data: pd.DataFrame, task: str, 
                                         expectations_dict: Dict, validation_type: str = "kinematic") -> List[Dict]:
        """
        Validate a single step against expectations at key phases (0%, 25%, 50%, 75%).
        
        Args:
            step_data: DataFrame containing step data with phase column
            task: Task name for validation
            expectations_dict: Dictionary of expectations (kinematic or kinetic)
            validation_type: "kinematic" or "kinetic"
            
        Returns:
            List of validation failure dictionaries
        """
        failures = []
        
        # Map task to validation expectations
        validation_task = self.task_mapping.get(task, task)
        if validation_task not in expectations_dict:
            return [{
                'task': task,
                'validation_task': validation_task,
                'error': f"No validation expectations found for task {validation_task}",
                'variable': 'N/A',
                'phase': 'N/A',
                'value': 'N/A'
            }]
        
        # Get phase column
        phase_col = self._get_phase_column(step_data)
        if phase_col is None:
            return [{
                'task': task,
                'validation_task': validation_task,
                'error': "No phase column found in step data",
                'variable': 'N/A',
                'phase': 'N/A',
                'value': 'N/A'
            }]
        
        # Check key phases: 0%, 25%, 50%, 75%
        key_phases = [0, 25, 50, 75]
        
        for target_phase in key_phases:
            if target_phase not in expectations_dict[validation_task]:
                continue
                
            # Find data points near this phase (within ±2.5%)
            phase_mask = (
                (step_data[phase_col] >= target_phase - 2.5) & 
                (step_data[phase_col] <= target_phase + 2.5)
            )
            phase_data = step_data[phase_mask]
            
            if phase_data.empty:
                continue
                
            # Get the data point closest to target phase
            closest_idx = (phase_data[phase_col] - target_phase).abs().idxmin()
            data_point = step_data.loc[closest_idx]
            actual_phase = data_point[phase_col]
            
            # Validate each expected variable at this phase
            phase_expectations = expectations_dict[validation_task][target_phase]
            
            for var_name, expected_range in phase_expectations.items():
                # Map validation variable to dataset variable
                dataset_var = self._map_validation_to_dataset_variable(var_name, step_data.columns)
                
                if dataset_var is None:
                    continue  # Skip variables not present in dataset
                    
                value = data_point[dataset_var]
                is_valid, failure_reason = self.validate_data_point(
                    value, expected_range, var_name, actual_phase
                )
                
                if not is_valid:
                    failures.append({
                        'task': task,
                        'validation_task': validation_task,
                        'variable': var_name,
                        'dataset_variable': dataset_var,
                        'phase': actual_phase,
                        'target_phase': target_phase,
                        'value': value,
                        'expected_min': expected_range['min'],
                        'expected_max': expected_range['max'],
                        'failure_reason': failure_reason,
                        'validation_type': validation_type
                    })
        
        return failures
    
    def _get_phase_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the phase column in the dataset."""
        phase_columns = ['phase_percent', 'phase_%', 'phase_r', 'phase_l']
        for col in phase_columns:
            if col in df.columns:
                return col
        return None
    
    def _map_validation_to_dataset_variable(self, validation_var: str, dataset_columns: List[str]) -> Optional[str]:
        """Map validation variable name to actual dataset variable name."""
        # Common mapping patterns
        mappings = {
            # Kinematic variables
            'hip_flexion_angle_ipsi': ['hip_flexion_angle_right_rad', 'hip_flexion_angle_r_rad', 'hip_angle_right_rad'],
            'hip_flexion_angle_contra': ['hip_flexion_angle_left_rad', 'hip_flexion_angle_l_rad', 'hip_angle_left_rad'],
            'knee_flexion_angle_ipsi': ['knee_flexion_angle_right_rad', 'knee_flexion_angle_r_rad', 'knee_angle_right_rad'],
            'knee_flexion_angle_contra': ['knee_flexion_angle_left_rad', 'knee_flexion_angle_l_rad', 'knee_angle_left_rad'],
            'ankle_flexion_angle_ipsi': ['ankle_flexion_angle_right_rad', 'ankle_flexion_angle_r_rad', 'ankle_angle_right_rad'],
            'ankle_flexion_angle_contra': ['ankle_flexion_angle_left_rad', 'ankle_flexion_angle_l_rad', 'ankle_angle_left_rad'],
            
            # Kinetic variables
            'hip_moment_ipsi_Nm_kg': ['hip_moment_right_Nm_kg', 'hip_moment_r_Nm_kg', 'hip_flexion_moment_right_Nm'],
            'hip_moment_contra_Nm_kg': ['hip_moment_left_Nm_kg', 'hip_moment_l_Nm_kg', 'hip_flexion_moment_left_Nm'],
            'knee_moment_ipsi_Nm_kg': ['knee_moment_right_Nm_kg', 'knee_moment_r_Nm_kg', 'knee_flexion_moment_right_Nm'],
            'knee_moment_contra_Nm_kg': ['knee_moment_left_Nm_kg', 'knee_moment_l_Nm_kg', 'knee_flexion_moment_left_Nm'],
            'ankle_moment_ipsi_Nm_kg': ['ankle_moment_right_Nm_kg', 'ankle_moment_r_Nm_kg', 'ankle_flexion_moment_right_Nm'],
            'ankle_moment_contra_Nm_kg': ['ankle_moment_left_Nm_kg', 'ankle_moment_l_Nm_kg', 'ankle_flexion_moment_left_Nm'],
            
            # Ground reaction forces
            'vertical_grf_N_kg': ['vertical_grf_N_kg', 'vertical_grf_right_N_kg', 'vgrf_N_kg'],
            'ap_grf_N_kg': ['ap_grf_N_kg', 'anteroposterior_grf_N_kg', 'fore_aft_grf_N_kg'],
            'ml_grf_N_kg': ['ml_grf_N_kg', 'mediolateral_grf_N_kg', 'lateral_grf_N_kg']
        }
        
        if validation_var in mappings:
            for candidate in mappings[validation_var]:
                if candidate in dataset_columns:
                    return candidate
        
        # Try exact match
        if validation_var in dataset_columns:
            return validation_var
            
        return None
    
    def validate_dataset(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Validate entire dataset against kinematic and kinetic expectations.
        
        Args:
            df: Dataset DataFrame
            
        Returns:
            Dictionary containing validation results and failure analysis
        """
        print("🔍 Starting dataset validation...")
        
        validation_results = {
            'total_steps': 0,
            'valid_steps': 0,
            'failed_steps': 0,
            'kinematic_failures': [],
            'kinetic_failures': [],
            'tasks_validated': []
        }
        
        # Get step grouping columns
        group_cols = self._get_step_grouping_columns(df)
        if not group_cols:
            raise ValueError("Cannot identify individual steps in dataset. Need 'step' or 'cycle' column.")
        
        # Group by individual steps and validate each
        step_groups = df.groupby(group_cols)
        total_steps = len(step_groups)
        validation_results['total_steps'] = total_steps
        
        print(f"📊 Found {total_steps} individual steps to validate")
        
        for step_id, step_data in step_groups:
            # Get task for this step
            task = self._get_task_from_step_data(step_data)
            if task not in validation_results['tasks_validated']:
                validation_results['tasks_validated'].append(task)
            
            step_valid = True
            
            # Validate against kinematic expectations
            if self.kinematic_expectations:
                kinematic_failures = self.validate_step_against_expectations(
                    step_data, task, self.kinematic_expectations, "kinematic"
                )
                if kinematic_failures:
                    validation_results['kinematic_failures'].extend(kinematic_failures)
                    step_valid = False
            
            # Validate against kinetic expectations  
            if self.kinetic_expectations:
                kinetic_failures = self.validate_step_against_expectations(
                    step_data, task, self.kinetic_expectations, "kinetic"
                )
                if kinetic_failures:
                    validation_results['kinetic_failures'].extend(kinetic_failures)
                    step_valid = False
            
            if step_valid:
                validation_results['valid_steps'] += 1
            else:
                validation_results['failed_steps'] += 1
        
        # Store for failure analysis
        self.step_failures = validation_results['kinematic_failures'] + validation_results['kinetic_failures']
        
        return validation_results
    
    def _get_step_grouping_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns to group by for individual steps."""
        group_cols = []
        
        if 'subject' in df.columns:
            group_cols.append('subject')
        elif 'subject_id' in df.columns:
            group_cols.append('subject_id')
            
        if 'task' in df.columns:
            group_cols.append('task')
        elif 'task_name' in df.columns:
            group_cols.append('task_name')
            
        if 'step' in df.columns:
            group_cols.append('step')
        elif 'cycle' in df.columns:
            group_cols.append('cycle')
        elif 'step_number' in df.columns:
            group_cols.append('step_number')
        
        return group_cols
    
    def _get_task_from_step_data(self, step_data: pd.DataFrame) -> str:
        """Extract task name from step data."""
        if 'task' in step_data.columns:
            return step_data['task'].iloc[0]
        elif 'task_name' in step_data.columns:
            return step_data['task_name'].iloc[0]
        else:
            return 'unknown_task'
    
    def generate_validation_report(self, validation_results: Dict) -> str:
        """
        Generate a comprehensive validation report.
        
        Args:
            validation_results: Results from dataset validation
            
        Returns:
            Path to the generated report file
        """
        report_path = self.reports_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, 'w') as f:
            f.write("# Dataset Validation Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Dataset**: `{self.dataset_path}`\n\n")
            
            # Summary statistics
            f.write("## Validation Summary\n\n")
            f.write(f"- **Total Steps Validated**: {validation_results['total_steps']}\n")
            f.write(f"- **Valid Steps**: {validation_results['valid_steps']}\n")
            f.write(f"- **Failed Steps**: {validation_results['failed_steps']}\n")
            
            if validation_results['total_steps'] > 0:
                success_rate = (validation_results['valid_steps'] / validation_results['total_steps']) * 100
                f.write(f"- **Success Rate**: {success_rate:.1f}%\n")
            
            f.write(f"- **Tasks Validated**: {', '.join(validation_results['tasks_validated'])}\n\n")
            
            # Failure analysis
            total_failures = len(validation_results['kinematic_failures']) + len(validation_results['kinetic_failures'])
            
            if total_failures == 0:
                f.write("## ✅ No Validation Failures\n\n")
                f.write("All steps passed validation against expected ranges.\n")
            else:
                f.write(f"## ⚠️ Validation Failures ({total_failures} total)\n\n")
                
                # Kinematic failures
                if validation_results['kinematic_failures']:
                    f.write(f"### Kinematic Failures ({len(validation_results['kinematic_failures'])})\n\n")
                    self._write_failure_table(f, validation_results['kinematic_failures'])
                
                # Kinetic failures
                if validation_results['kinetic_failures']:
                    f.write(f"### Kinetic Failures ({len(validation_results['kinetic_failures'])})\n\n")
                    self._write_failure_table(f, validation_results['kinetic_failures'])
            
            # Recommendations
            f.write("\n## Recommendations\n\n")
            if total_failures > 0:
                f.write("1. Review data collection protocols for tasks with high failure rates\n")
                f.write("2. Check sensor calibration for variables consistently out of range\n")
                f.write("3. Verify subject instructions and movement quality\n")
                f.write("4. Consider if validation ranges need updating for your population\n")
            else:
                f.write("1. Dataset appears to be high quality with no validation failures\n")
                f.write("2. Data is ready for analysis and publication\n")
        
        return str(report_path)
    
    def _write_failure_table(self, f, failures: List[Dict]):
        """Write failure information as a markdown table."""
        # Group failures by task and variable for better organization
        failures_by_task = {}
        for failure in failures:
            task = failure['task']
            if task not in failures_by_task:
                failures_by_task[task] = {}
            
            variable = failure['variable']
            if variable not in failures_by_task[task]:
                failures_by_task[task][variable] = []
            
            failures_by_task[task][variable].append(failure)
        
        for task, task_failures in failures_by_task.items():
            f.write(f"#### Task: {task.replace('_', ' ').title()}\n\n")
            
            for variable, var_failures in task_failures.items():
                f.write(f"**Variable: {variable}** ({len(var_failures)} failures)\n\n")
                
                # Create table
                f.write("| Phase | Value | Expected Range | Failure Reason |\n")
                f.write("|-------|-------|----------------|----------------|\n")
                
                for failure in var_failures[:10]:  # Limit to first 10 for readability
                    phase = failure.get('phase', 'N/A')
                    value = failure.get('value', 'N/A')
                    min_val = failure.get('expected_min', 'N/A')
                    max_val = failure.get('expected_max', 'N/A')
                    reason = failure.get('failure_reason', 'Unknown')
                    
                    if isinstance(value, (int, float)):
                        value_str = f"{value:.3f}"
                    else:
                        value_str = str(value)
                        
                    if isinstance(min_val, (int, float)) and isinstance(max_val, (int, float)):
                        range_str = f"{min_val:.3f} to {max_val:.3f}"
                    else:
                        range_str = f"{min_val} to {max_val}"
                    
                    if isinstance(phase, (int, float)):
                        phase_str = f"{phase:.1f}%"
                    else:
                        phase_str = str(phase)
                    
                    f.write(f"| {phase_str} | {value_str} | {range_str} | {reason} |\n")
                
                if len(var_failures) > 10:
                    f.write(f"\n*... and {len(var_failures) - 10} more failures*\n")
                
                f.write("\n")
    
    def run_validation(self) -> str:
        """
        Main method to run complete dataset validation.
        
        Returns:
            Path to the generated validation report
        """
        # Load dataset
        df = self.load_dataset()
        
        # Validate dataset
        validation_results = self.validate_dataset(df)
        
        # Generate report
        report_path = self.generate_validation_report(validation_results)
        
        # Print summary
        print(f"\n✅ Validation completed!")
        print(f"📊 Results: {validation_results['valid_steps']}/{validation_results['total_steps']} steps passed")
        
        total_failures = len(validation_results['kinematic_failures']) + len(validation_results['kinetic_failures'])
        if total_failures > 0:
            print(f"⚠️  {total_failures} validation failures found")
        else:
            print("✅ No validation failures - dataset is high quality!")
            
        print(f"📄 Full report: {report_path}")
        
        return report_path


def main():
    """Main function to run the dataset validator."""
    parser = argparse.ArgumentParser(description="Validate phase-based locomotion datasets against specification ranges")
    parser.add_argument("--dataset", required=True, help="Path to phase-based dataset parquet file (*_phase.parquet)")
    parser.add_argument("--output", default="validation_reports", help="Output directory for validation reports")
    
    args = parser.parse_args()
    
    try:
        # Create dataset validator
        validator = DatasetValidator(args.dataset, args.output)
        
        # Run validation
        report_path = validator.run_validation()
        
        print(f"\n🎉 Dataset validation completed successfully!")
        print(f"📄 Validation report: {report_path}")
        return 0
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())