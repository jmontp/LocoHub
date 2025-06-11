#!/usr/bin/env python3
"""
Dataset Validator (Phase-based)

Entry point script for validating phase-based locomotion datasets using LocomotionData library
and validation system integration. Provides comprehensive validation with efficient 3D operations.

This validator:
1. Loads phase-based parquet datasets using LocomotionData library (requires _phase.parquet format)
2. Leverages LocomotionData's efficient 3D array operations for data manipulation
3. Uses StepClassifier.validate_data_against_specs() for consistent validation
4. Reports validation failures with detailed analysis
5. Generates filters by phase plots with step validation overlays (optional)

**Library Integration:**
- Uses lib.python.locomotion_analysis.LocomotionData for efficient data loading and manipulation
- Uses validation.step_classifier.StepClassifier for validation logic (single source of truth)
- Uses validation.filters_by_phase_plots.create_filters_by_phase_plot for visualization
- Ensures consistency with specification files and other validation tools

**Performance Features:**
- Efficient 3D array operations via LocomotionData (100x faster than pandas groupby)
- Representative phase validation (0%, 25%, 50%, 75%) via StepClassifier
- Step color classification: gray (valid), red (violations), pink (other violations)
- Support for both kinematic (joint angles) and kinetic (forces/moments) validation
- Automatic contralateral offset handling for gait-based tasks

Usage:
    python dataset_validator_phase.py --dataset <dataset>_phase.parquet [--output validation_reports/] [--no-plots]
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

# Import library modules
try:
    from validation.filters_by_phase_plots import create_filters_by_phase_plot
    from validation.step_classifier import StepClassifier
    from lib.python.locomotion_analysis import LocomotionData
except ImportError as e:
    raise ImportError(f"Could not import required library modules: {e}")

class DatasetValidator:
    """
    Focused dataset validator that validates phase-based locomotion datasets
    against kinematic and kinetic expectations from specification files.
    
    Uses LocomotionData library for efficient data loading and manipulation,
    combined with StepClassifier for robust validation against specifications.
    """
    
    def __init__(self, dataset_path: str, output_dir: str = None, generate_plots: bool = True):
        """
        Initialize the dataset validator.
        
        Args:
            dataset_path: Path to the phase-based dataset parquet file (must be *_phase.parquet)
            output_dir: Directory to save validation reports (default: source/tests/sample_plots/validation_reports)
            generate_plots: Whether to generate filters by phase plots with validation overlays (default: True)
        """
        self.dataset_path = dataset_path
        self.generate_plots = generate_plots
        
        # Extract dataset name for use in output files
        self.dataset_name = Path(dataset_path).stem  # Extract dataset name without .parquet extension
        
        # Set default output directory to sample_plots if not specified
        if output_dir is None:
            # Find the source/tests directory using absolute path resolution
            current_file = Path(__file__).resolve()  # Absolute path to this file
            validation_dir = current_file.parent     # source/validation/
            source_dir = validation_dir.parent       # source/
            tests_dir = source_dir / "tests"         # source/tests/
            output_dir = tests_dir / "sample_plots" / "validation_reports" / self.dataset_name
        
        # Create output directory structure
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reports and plots go in the same directory for better organization
        self.reports_dir = self.output_dir
        self.plots_dir = self.output_dir
        
        # Initialize step classifier (needed for both validation and visualization)
        self.step_classifier = StepClassifier()
            
        # Load validation expectations from specification files using the step classifier
        try:
            self.kinematic_expectations = self.step_classifier.load_validation_ranges_from_specs('kinematic')
        except FileNotFoundError:
            print("⚠️  Warning: Kinematic validation expectations not found")
            self.kinematic_expectations = {}
        
        try:
            self.kinetic_expectations = self.step_classifier.load_validation_ranges_from_specs('kinetic')
        except FileNotFoundError:
            print("⚠️  Warning: Kinetic validation expectations not found")
            self.kinetic_expectations = {}
        
        # Storage for validation results
        self.validation_results = {}
        self.step_failures = []
        
        # Initialize LocomotionData object (will be set when dataset is loaded)
        self.locomotion_data = None
        
    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that the dataset contains required columns for validation.
        
        Args:
            df: Dataset DataFrame
            
        Raises:
            ValueError: If required columns are missing
        """
        # Required structural columns
        required_structural_cols = ['subject', 'task', 'step']
        missing_structural = [col for col in required_structural_cols if col not in df.columns]
        
        if missing_structural:
            raise ValueError(
                f"❌ VALIDATION FAILED: Missing required structural columns: {missing_structural}\n"
                f"Expected columns: {required_structural_cols}\n"
                f"Available columns: {list(df.columns)}\n"
                f"Dataset must include subject, task, and step identification columns."
            )
        
        # Required biomechanical columns (from LocomotionData.ANGLE_FEATURES)
        required_angle_features = [
            'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_contra_rad', 
            'ankle_flexion_angle_contra_rad',
            'hip_flexion_angle_ipsi_rad',
            'knee_flexion_angle_ipsi_rad',
            'ankle_flexion_angle_ipsi_rad'
        ]
        
        available_angle_features = [col for col in required_angle_features if col in df.columns]
        missing_angle_features = [col for col in required_angle_features if col not in df.columns]
        
        if len(available_angle_features) == 0:
            raise ValueError(
                f"❌ VALIDATION FAILED: No required biomechanical variables found\n"
                f"Expected angle variables: {required_angle_features}\n"
                f"Available columns: {list(df.columns)}\n"
                f"Dataset must include standard joint angle variables in radians.\n"
                f"Note: Variable names must follow exact naming convention:\n"
                f"  <joint>_flexion_angle_<side>_rad"
            )
        
        if missing_angle_features:
            print(f"⚠️  Warning: Missing some angle features: {missing_angle_features}")
            print(f"   Available angle features: {available_angle_features}")
            print(f"   Validation will proceed with available features only.")
    
    def _validate_task_coverage(self, df: pd.DataFrame) -> None:
        """
        Validate that the dataset contains tasks with validation expectations.
        
        Args:
            df: Dataset DataFrame
            
        Raises:
            ValueError: If no tasks have validation expectations
        """
        if 'task' not in df.columns:
            raise ValueError("❌ VALIDATION FAILED: Dataset missing 'task' column")
        
        # Get unique tasks in dataset
        dataset_tasks = set(df['task'].unique())
        
        # Get tasks with validation expectations
        kinematic_tasks = set(self.kinematic_expectations.keys()) if self.kinematic_expectations else set()
        kinetic_tasks = set(self.kinetic_expectations.keys()) if self.kinetic_expectations else set()
        validation_tasks = kinematic_tasks.union(kinetic_tasks)
        
        # Check for overlap
        valid_tasks = dataset_tasks.intersection(validation_tasks)
        invalid_tasks = dataset_tasks - validation_tasks
        
        if len(valid_tasks) == 0:
            available_tasks = sorted(list(validation_tasks))
            dataset_task_list = sorted(list(dataset_tasks))
            
            raise ValueError(
                f"❌ VALIDATION FAILED: No tasks in dataset have validation expectations\n"
                f"Dataset tasks: {dataset_task_list}\n"
                f"Available validation tasks: {available_tasks}\n"
                f"At least one task must match validation expectations.\n"
                f"Common valid task names: level_walking, incline_walking, decline_walking, \n"
                f"                        up_stairs, down_stairs, run, sit_to_stand, jump, squats"
            )
        
        if invalid_tasks:
            print(f"⚠️  Warning: Some tasks have no validation expectations: {sorted(list(invalid_tasks))}")
            print(f"   Valid tasks found: {sorted(list(valid_tasks))}")
            print(f"   Validation will proceed with valid tasks only.")
    
    def load_dataset(self) -> LocomotionData:
        """Load and validate the dataset structure using LocomotionData library. Only works with phase-based datasets."""
        # Check if this is a phase-based dataset according to standard spec
        if '_phase' not in str(self.dataset_path):
            raise ValueError(
                f"Validation only works with phase-based datasets.\n"
                f"Expected filename pattern: <dataset>_phase.parquet\n"
                f"Provided: {self.dataset_path}\n"
                f"Please convert to phase-based format first (150 points per gait cycle)."
            )
        
        try:
            # Use LocomotionData library for loading and validation
            self.locomotion_data = LocomotionData(self.dataset_path)
            
            print(f"✅ Loaded phase-based dataset using LocomotionData library")
            print(f"   Subjects: {len(self.locomotion_data.get_subjects())}")
            print(f"   Tasks: {len(self.locomotion_data.get_tasks())}")
            print(f"   Features: {len(self.locomotion_data.features)}")
            
            # Get the DataFrame for additional validation
            df = self.locomotion_data.df
            
            # EXPLICIT VALIDATION CHECKS - These will raise clear errors for edge cases
            print(f"🔍 Performing explicit validation checks...")
            
            # Check 1: Required columns for validation
            self._validate_required_columns(df)
            print(f"   ✅ Required columns validation passed")
            
            # Check 2: Task coverage (must have tasks with validation expectations)
            self._validate_task_coverage(df)
            print(f"   ✅ Task coverage validation passed")
            
            # Additional validation for phase-based structure
            phase_columns = [col for col in df.columns if 'phase' in col.lower()]
            if not any(col in df.columns for col in ['phase_percent', 'phase_%', 'phase_r', 'phase_l']):
                raise ValueError(
                    f"❌ VALIDATION FAILED: Phase-based dataset missing phase column.\n"
                    f"Expected: 'phase_percent', 'phase_%', 'phase_r', or 'phase_l'\n"
                    f"Available columns: {list(df.columns)[:10]}...\n"
                    f"Found phase-related columns: {phase_columns}"
                )
            
            # Verify step structure using LocomotionData's efficient operations
            if 'step' in df.columns or 'cycle' in df.columns:
                step_col = 'step' if 'step' in df.columns else 'cycle'
                if 'subject' in df.columns and 'task' in df.columns:
                    step_sizes = df.groupby(['subject', 'task', step_col]).size()
                    expected_size = 150
                    if not step_sizes.between(140, 160).all():  # Allow some tolerance
                        print(f"⚠️  WARNING: Some steps don't have ~150 points as expected for phase data")
                        print(f"   Step sizes range: {step_sizes.min()} to {step_sizes.max()}")
            
            print(f"✅ All validation checks passed - dataset is ready for validation")
            return self.locomotion_data
        except Exception as e:
            raise RuntimeError(f"Error loading dataset with LocomotionData: {e}")
    
    
    def validate_step_against_expectations(self, step_data: pd.DataFrame, task: str, 
                                         validation_type: str = "kinematic") -> List[Dict]:
        """
        Validate a single step against expectations using the step classifier library.
        
        Args:
            step_data: DataFrame containing step data with phase column
            task: Task name for validation
            validation_type: "kinematic" or "kinetic"
            
        Returns:
            List of validation failure dictionaries
        """
        # Convert step data to format expected by step classifier
        step_data_array = self._convert_single_step_to_array(step_data, validation_type)
        
        # Create step task mapping (single step)
        step_task_mapping = {0: task}
        
        # Use step classifier to validate this step
        failures = self.step_classifier.validate_data_against_specs(
            step_data_array, task, step_task_mapping, validation_type
        )
        
        return failures
    
    def _convert_single_step_to_array(self, step_data: pd.DataFrame, validation_type: str) -> np.ndarray:
        """
        Convert single step DataFrame to array format expected by step classifier.
        
        Args:
            step_data: DataFrame containing step data with phase column
            validation_type: "kinematic" or "kinetic"
            
        Returns:
            Array with shape (1, 150, num_features)
        """
        # Define standard variable order
        if validation_type == 'kinematic':
            variables = [
                'hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
                'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
                'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra'
            ]
        elif validation_type == 'kinetic':
            variables = [
                'hip_moment_ipsi_Nm_kg', 'hip_moment_contra_Nm_kg',
                'knee_moment_ipsi_Nm_kg', 'knee_moment_contra_Nm_kg',
                'ankle_moment_ipsi_Nm_kg', 'ankle_moment_contra_Nm_kg'
            ]
        else:
            raise ValueError(f"Unknown validation type: {validation_type}")
        
        # Check which variables are available in the data
        available_variables = [var for var in variables if var in step_data.columns]
        if not available_variables:
            raise ValueError(f"No {validation_type} variables found in step data. Expected: {variables}")
        
        # Create array with shape (1, 150, num_features)
        step_array = np.zeros((1, 150, len(available_variables)))
        
        # Extract and resample data to 150 points
        for var_idx, var_name in enumerate(available_variables):
            var_data = step_data[var_name].values
            
            # Resample to 150 points if needed
            if len(var_data) != 150:
                old_indices = np.linspace(0, len(var_data)-1, len(var_data))
                new_indices = np.linspace(0, len(var_data)-1, 150)
                var_data = np.interp(new_indices, old_indices, var_data)
            
            step_array[0, :, var_idx] = var_data
        
        return step_array
    
    def _validate_step_3d_data(self, step_data_3d: np.ndarray, features: List[str], 
                              task: str, validation_type: str, subject: str, step_idx: int, global_step_idx: int = None) -> List[Dict]:
        """
        Validate a single step using 3D array data from LocomotionData.
        
        Args:
            step_data_3d: 3D step data with shape (150, n_features)
            features: List of feature names corresponding to last dimension
            task: Task name for validation
            validation_type: "kinematic" or "kinetic"
            subject: Subject ID for error reporting
            step_idx: Step index for error reporting (local to subject-task)
            global_step_idx: Global step index for plotting alignment (optional)
            
        Returns:
            List of validation failure dictionaries
        """
        # Convert 3D data to format expected by step classifier
        step_data_array = step_data_3d.reshape(1, 150, len(features))  # Shape: (1, 150, n_features)
        
        # Create step task mapping (single step)
        step_task_mapping = {0: task}
        
        # Use step classifier to validate this step
        failures = self.step_classifier.validate_data_against_specs(
            step_data_array, task, step_task_mapping, validation_type
        )
        
        # Add subject and step information to failures for better error reporting
        for failure in failures:
            failure['subject'] = subject
            failure['step_index'] = step_idx  # Local step index within subject-task
            failure['step'] = global_step_idx if global_step_idx is not None else step_idx  # Global step index for plotting
            failure['step_id'] = f"{subject}_{task}_{step_idx}"
        
        return failures
    
    def _get_phase_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the phase column in the dataset."""
        phase_columns = ['phase_percent', 'phase_%', 'phase_r', 'phase_l']
        for col in phase_columns:
            if col in df.columns:
                return col
        return None
    
    
    def validate_dataset(self, locomotion_data: LocomotionData) -> Dict[str, any]:
        """
        Validate entire dataset against kinematic and kinetic expectations using LocomotionData.
        
        Args:
            locomotion_data: LocomotionData object with loaded dataset
            
        Returns:
            Dictionary containing validation results and failure analysis
        """
        print("🔍 Starting dataset validation using LocomotionData...")
        
        validation_results = {
            'total_steps': 0,
            'valid_steps': 0,
            'failed_steps': 0,
            'kinematic_failures': [],
            'kinetic_failures': [],
            'tasks_validated': [],
            'task_step_counts': {}  # Track steps per task for percentage calculations
        }
        
        # Get all subjects and tasks from LocomotionData
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        print(f"📊 Validating {len(subjects)} subjects across {len(tasks)} tasks")
        
        total_steps = 0
        global_step_index = 0  # Track global step index for plotting alignment
        
        # Iterate through each subject-task combination
        for subject in subjects:
            for task in tasks:
                if task not in validation_results['tasks_validated']:
                    validation_results['tasks_validated'].append(task)
                    validation_results['task_step_counts'][task] = {'total': 0, 'failed': 0, 'valid': 0}
                
                # Get 3D data for this subject-task combination
                try:
                    # Get kinematic data if available
                    kinematic_data_3d = None
                    kinematic_features = None
                    if self.kinematic_expectations and task in self.kinematic_expectations:
                        kinematic_features = [f for f in locomotion_data.ANGLE_FEATURES if f in locomotion_data.features]
                        if kinematic_features:
                            kinematic_data_3d, _ = locomotion_data.get_cycles(subject, task, kinematic_features)
                    
                    # Get kinetic data if available
                    kinetic_data_3d = None
                    kinetic_features = None
                    if self.kinetic_expectations and task in self.kinetic_expectations:
                        kinetic_features = [f for f in locomotion_data.MOMENT_FEATURES if f in locomotion_data.features]
                        if kinetic_features:
                            kinetic_data_3d, _ = locomotion_data.get_cycles(subject, task, kinetic_features)
                    
                    # Determine number of steps from available data
                    n_steps = 0
                    if kinematic_data_3d is not None:
                        n_steps = kinematic_data_3d.shape[0]
                    elif kinetic_data_3d is not None:
                        n_steps = kinetic_data_3d.shape[0]
                    
                    if n_steps == 0:
                        continue  # No data for this subject-task combination
                    
                    total_steps += n_steps
                    validation_results['task_step_counts'][task]['total'] += n_steps
                    
                    # Validate each step
                    for step_idx in range(n_steps):
                        step_valid = True
                        
                        # Validate kinematic data for this step
                        if kinematic_data_3d is not None and self.kinematic_expectations and task in self.kinematic_expectations:
                            try:
                                step_kinematic_data = kinematic_data_3d[step_idx, :, :]  # Shape: (150, n_features)
                                kinematic_failures = self._validate_step_3d_data(
                                    step_kinematic_data, kinematic_features, task, "kinematic", subject, step_idx, global_step_index
                                )
                                if kinematic_failures:
                                    validation_results['kinematic_failures'].extend(kinematic_failures)
                                    step_valid = False
                            except Exception as e:
                                print(f"⚠️  Warning: Could not validate kinematic data for {subject}-{task} step {step_idx}: {e}")
                        
                        # Validate kinetic data for this step
                        if kinetic_data_3d is not None and self.kinetic_expectations and task in self.kinetic_expectations:
                            try:
                                step_kinetic_data = kinetic_data_3d[step_idx, :, :]  # Shape: (150, n_features)
                                kinetic_failures = self._validate_step_3d_data(
                                    step_kinetic_data, kinetic_features, task, "kinetic", subject, step_idx, global_step_index
                                )
                                if kinetic_failures:
                                    validation_results['kinetic_failures'].extend(kinetic_failures)
                                    step_valid = False
                            except Exception as e:
                                print(f"⚠️  Warning: Could not validate kinetic data for {subject}-{task} step {step_idx}: {e}")
                        
                        if step_valid:
                            validation_results['valid_steps'] += 1
                            validation_results['task_step_counts'][task]['valid'] += 1
                        else:
                            validation_results['failed_steps'] += 1
                            validation_results['task_step_counts'][task]['failed'] += 1
                        
                        global_step_index += 1
                
                except Exception as e:
                    print(f"⚠️  Warning: Could not process {subject}-{task}: {e}")
                    continue
        
        validation_results['total_steps'] = total_steps
        
        # Store for failure analysis
        self.step_failures = validation_results['kinematic_failures'] + validation_results['kinetic_failures']
        
        print(f"📊 Validation completed: {validation_results['valid_steps']}/{total_steps} steps passed")
        
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
    
    def generate_validation_report(self, validation_results: Dict, task_plots: Dict[str, Dict[str, str]] = None) -> str:
        """
        Generate a comprehensive validation report in the requested format.
        
        Args:
            validation_results: Results from dataset validation
            task_plots: Dictionary of task plots organized by task and mode
            
        Returns:
            Path to the generated report file
        """
        report_path = self.reports_dir / f"{self.dataset_name}_validation_report.md"
        
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
            
            # Task-by-task validation plots and results
            if task_plots:
                f.write("## Task Validation Results\n\n")
                
                for task_name in sorted(validation_results['tasks_validated']):
                    f.write(f"### {task_name.replace('_', ' ').title()}\n\n")
                    
                    # Include plots if available
                    if task_name in task_plots:
                        if 'kinematic' in task_plots[task_name]:
                            kinematic_plot_name = Path(task_plots[task_name]['kinematic']).name
                            f.write(f"**Kinematic Validation:**\n")
                            f.write(f"![{task_name} Kinematic Validation]({kinematic_plot_name})\n\n")
                        
                        if 'kinetic' in task_plots[task_name]:
                            kinetic_plot_name = Path(task_plots[task_name]['kinetic']).name
                            f.write(f"**Kinetic Validation:**\n")
                            f.write(f"![{task_name} Kinetic Validation]({kinetic_plot_name})\n\n")
                    
                    # Add task-specific failure summary with percentages
                    task_kinematic_failures = [f for f in validation_results['kinematic_failures'] 
                                             if f.get('task') == task_name]
                    task_kinetic_failures = [f for f in validation_results['kinetic_failures'] 
                                           if f.get('task') == task_name]
                    total_task_failures = len(task_kinematic_failures) + len(task_kinetic_failures)
                    
                    # Get step counts and calculate percentages for this task
                    task_counts = validation_results.get('task_step_counts', {}).get(task_name, {'total': 0, 'failed': 0, 'valid': 0})
                    total_steps_task = task_counts['total']
                    failed_steps_task = task_counts['failed']
                    valid_steps_task = task_counts['valid']
                    
                    if total_steps_task > 0:
                        failure_percentage = (failed_steps_task / total_steps_task) * 100
                        success_percentage = (valid_steps_task / total_steps_task) * 100
                        
                        f.write(f"**Step Summary**: {failed_steps_task}/{total_steps_task} failed steps ({failure_percentage:.1f}%)\n")
                        f.write(f"**Success Rate**: {success_percentage:.1f}%\n\n")
                    
                    if total_task_failures > 0:
                        f.write(f"**Validation Issues**: {total_task_failures} failures detected\n")
                        if task_kinematic_failures:
                            f.write(f"- Kinematic: {len(task_kinematic_failures)} failures\n")
                        if task_kinetic_failures:
                            f.write(f"- Kinetic: {len(task_kinetic_failures)} failures\n")
                    else:
                        f.write(f"**Status**: ✅ All validation checks passed\n")
                    
                    f.write("\n")
            
            # Detailed failure analysis
            total_failures = len(validation_results['kinematic_failures']) + len(validation_results['kinetic_failures'])
            
            if total_failures == 0:
                f.write("## ✅ No Validation Failures\n\n")
                f.write("All steps passed validation against expected ranges.\n")
            else:
                f.write(f"## ⚠️ Detailed Failure Analysis ({total_failures} total)\n\n")
                
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
    
    def _convert_dataset_to_plotting_format(self, locomotion_data: LocomotionData) -> Tuple[np.ndarray, Dict, Dict[str, str], str, List[str]]:
        """
        Convert LocomotionData to format expected by plotting functions.
        
        Args:
            locomotion_data: LocomotionData object
            
        Returns:
            Tuple of (data_array, task_step_mapping, step_task_mapping, plot_mode, variables_used)
        """
        # Define standard variable order for plotting
        kinematic_variables = locomotion_data.ANGLE_FEATURES
        kinetic_variables = locomotion_data.MOMENT_FEATURES
        
        # Check for exact matches with available features
        available_kinematic = [var for var in kinematic_variables if var in locomotion_data.features]
        available_kinetic = [var for var in kinetic_variables if var in locomotion_data.features]
        
        # Use kinematic if available, otherwise kinetic
        if available_kinematic:
            variables_to_use = available_kinematic
            plot_mode = 'kinematic'
        elif available_kinetic:
            variables_to_use = available_kinetic
            plot_mode = 'kinetic'
        else:
            raise ValueError(f"No standard kinematic or kinetic variables found in dataset. Expected kinematic: {kinematic_variables} or kinetic: {kinetic_variables}")
        
        # Create mapping from step index to task
        task_step_mapping = {}  # {task: [step_indices]}
        step_task_mapping = {}  # {step_index: task}
        
        # Collect all step data using LocomotionData's efficient operations
        all_step_data = []
        step_index = 0
        
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        for subject in subjects:
            for task in tasks:
                try:
                    # Get 3D data for this subject-task combination
                    data_3d, features = locomotion_data.get_cycles(subject, task, variables_to_use)
                    
                    if data_3d is None or data_3d.shape[0] == 0:
                        continue  # No data for this subject-task combination
                    
                    # Track task mapping for each step
                    n_steps = data_3d.shape[0]
                    if task not in task_step_mapping:
                        task_step_mapping[task] = []
                    
                    for step_offset in range(n_steps):
                        task_step_mapping[task].append(step_index + step_offset)
                        step_task_mapping[step_index + step_offset] = task
                    
                    # Add all steps from this subject-task to our collection
                    for step_offset in range(n_steps):
                        step_data = data_3d[step_offset, :, :]  # Shape: (150, n_features)
                        all_step_data.append(step_data)
                    
                    step_index += n_steps
                    
                except Exception as e:
                    print(f"⚠️  Warning: Could not process {subject}-{task} for plotting: {e}")
                    continue
        
        if not all_step_data:
            raise ValueError("No valid step data found for plotting")
        
        # Convert to final array format
        data_array = np.stack(all_step_data, axis=0)  # Shape: (num_steps, 150, num_features)
        
        return data_array, task_step_mapping, step_task_mapping, plot_mode, variables_to_use
    
    def _generate_step_colors_from_validation(self, validation_results: Dict, 
                                            step_task_mapping: Dict[str, str], 
                                            plot_mode: str) -> np.ndarray:
        """
        Generate step color classifications based on validation results using the step classifier.
        
        Args:
            validation_results: Validation results from validate_dataset
            step_task_mapping: Mapping from step index to task name
            plot_mode: 'kinematic' or 'kinetic' - determines which failures to use
            
        Returns:
            Array of step colors with shape (num_steps,)
        """
        # Get appropriate failures based on plot mode
        if plot_mode == 'kinematic':
            failures = validation_results.get('kinematic_failures', [])
        elif plot_mode == 'kinetic':
            failures = validation_results.get('kinetic_failures', [])
        else:
            # Use all failures for unknown modes
            failures = (validation_results.get('kinematic_failures', []) + 
                       validation_results.get('kinetic_failures', []))
        
        # Use step classifier to generate colors
        # Use summary classification since we don't know the specific feature
        step_colors = self.step_classifier.get_step_summary_classification(
            failures, step_task_mapping
        )
        
        return step_colors
    
    def _generate_validation_plots(self, locomotion_data: LocomotionData, validation_results: Dict) -> Dict[str, Dict[str, str]]:
        """
        Generate both kinematic and kinetic validation plots for each task.
        
        Args:
            locomotion_data: LocomotionData object
            validation_results: Results from dataset validation
            
        Returns:
            Dictionary mapping task names to plot types and their file paths
            Format: {task_name: {'kinematic': path, 'kinetic': path}}
        """
        if not self.generate_plots:
            return {}
        
        task_plots = {}
        
        # Get all subjects and tasks
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        print(f"📊 Generating validation plots for {len(tasks)} tasks...")
        
        # Generate plots for each task
        for task_name in tasks:
            task_plots[task_name] = {}
            print(f"   📈 Processing task: {task_name}")
            
            # Generate kinematic plots if data and expectations exist
            try:
                if task_name in self.kinematic_expectations:
                    kinematic_features = [f for f in locomotion_data.ANGLE_FEATURES if f in locomotion_data.features]
                    if kinematic_features:
                        # Get kinematic data and step colors
                        kinematic_data_3d, task_step_mapping, step_task_mapping = self._get_task_data_for_plotting(
                            locomotion_data, subjects, [task_name], kinematic_features
                        )
                        
                        kinematic_step_colors = self._generate_step_colors_from_validation(
                            validation_results, step_task_mapping, 'kinematic'
                        )
                        
                        
                        # Generate kinematic plot
                        kinematic_plot_path = create_filters_by_phase_plot(
                            validation_data={task_name: self.kinematic_expectations[task_name]},
                            task_name=task_name,
                            output_dir=str(self.plots_dir),
                            mode='kinematic',
                            data=kinematic_data_3d,
                            step_colors=kinematic_step_colors
                        )
                        
                        task_plots[task_name]['kinematic'] = kinematic_plot_path
                        print(f"      ✅ Kinematic: {Path(kinematic_plot_path).name}")
                    else:
                        print(f"      ⚠️  No kinematic features found")
                else:
                    print(f"      ⚠️  No kinematic expectations for {task_name}")
            except Exception as e:
                print(f"      ❌ Kinematic plot failed: {e}")
            
            # Generate kinetic plots if data and expectations exist
            try:
                if task_name in self.kinetic_expectations:
                    kinetic_features = [f for f in locomotion_data.MOMENT_FEATURES if f in locomotion_data.features]
                    if kinetic_features:
                        # Get kinetic data and step colors
                        kinetic_data_3d, task_step_mapping, step_task_mapping = self._get_task_data_for_plotting(
                            locomotion_data, subjects, [task_name], kinetic_features
                        )
                        
                        kinetic_step_colors = self._generate_step_colors_from_validation(
                            validation_results, step_task_mapping, 'kinetic'
                        )
                        
                        
                        # Generate kinetic plot
                        kinetic_plot_path = create_filters_by_phase_plot(
                            validation_data={task_name: self.kinetic_expectations[task_name]},
                            task_name=task_name,
                            output_dir=str(self.plots_dir),
                            mode='kinetic',
                            data=kinetic_data_3d,
                            step_colors=kinetic_step_colors
                        )
                        
                        task_plots[task_name]['kinetic'] = kinetic_plot_path
                        print(f"      ✅ Kinetic: {Path(kinetic_plot_path).name}")
                    else:
                        print(f"      ⚠️  No kinetic features found")
                else:
                    print(f"      ⚠️  No kinetic expectations for {task_name}")
            except Exception as e:
                print(f"      ❌ Kinetic plot failed: {e}")
        
        return task_plots
    
    def _get_task_data_for_plotting(self, locomotion_data: LocomotionData, subjects: List[str], 
                                   tasks: List[str], features: List[str]) -> Tuple[np.ndarray, Dict, Dict[int, str]]:
        """
        Get 3D data array and step mappings for specific tasks and features.
        
        Args:
            locomotion_data: LocomotionData object
            subjects: List of subject IDs
            tasks: List of task names
            features: List of feature names
            
        Returns:
            Tuple of (data_array, task_step_mapping, step_task_mapping)
        """
        all_step_data = []
        task_step_mapping = {}  # {task: [step_indices]}
        step_task_mapping = {}  # {step_index: task}
        step_index = 0
        
        for subject in subjects:
            for task in tasks:
                try:
                    # Get 3D data for this subject-task combination
                    data_3d, _ = locomotion_data.get_cycles(subject, task, features)
                    
                    if data_3d is None or data_3d.shape[0] == 0:
                        continue  # No data for this subject-task combination
                    
                    # Track task mapping for each step
                    n_steps = data_3d.shape[0]
                    if task not in task_step_mapping:
                        task_step_mapping[task] = []
                    
                    for step_offset in range(n_steps):
                        task_step_mapping[task].append(step_index + step_offset)
                        step_task_mapping[step_index + step_offset] = task
                    
                    # Add all steps from this subject-task to our collection
                    for step_offset in range(n_steps):
                        step_data = data_3d[step_offset, :, :]  # Shape: (150, n_features)
                        all_step_data.append(step_data)
                    
                    step_index += n_steps
                    
                except Exception as e:
                    print(f"      ⚠️  Could not process {subject}-{task}: {e}")
                    continue
        
        if not all_step_data:
            raise ValueError("No valid step data found for plotting")
        
        # Convert to final array format
        data_array = np.stack(all_step_data, axis=0)  # Shape: (num_steps, 150, num_features)
        
        return data_array, task_step_mapping, step_task_mapping
    
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
        # Load dataset using LocomotionData library
        locomotion_data = self.load_dataset()
        
        # Validate dataset using LocomotionData's efficient operations
        validation_results = self.validate_dataset(locomotion_data)
        
        # Generate plots if enabled
        task_plots = {}
        if self.generate_plots:
            task_plots = self._generate_validation_plots(locomotion_data, validation_results)
        
        # Generate report with task plots
        report_path = self.generate_validation_report(validation_results, task_plots)
        
        # Print summary
        print(f"\n✅ Validation completed!")
        print(f"📊 Results: {validation_results['valid_steps']}/{validation_results['total_steps']} steps passed")
        
        total_failures = len(validation_results['kinematic_failures']) + len(validation_results['kinetic_failures'])
        if total_failures > 0:
            print(f"⚠️  {total_failures} validation failures found")
        else:
            print("✅ No validation failures - dataset is high quality!")
            
        print(f"📄 Full report: {report_path}")
        
        if task_plots:
            total_plots = sum(len(plots) for plots in task_plots.values())
            print(f"📊 Generated {total_plots} validation plots in: {self.plots_dir}")
            for task_name, plots in task_plots.items():
                for plot_type, plot_path in plots.items():
                    print(f"   📈 {task_name} {plot_type}: {Path(plot_path).name}")
        
        return report_path


def main():
    """Main function to run the dataset validator."""
    parser = argparse.ArgumentParser(description="Validate phase-based locomotion datasets against specification ranges")
    parser.add_argument("--dataset", required=True, help="Path to phase-based dataset parquet file (*_phase.parquet)")
    parser.add_argument("--output", default=None, help="Output directory for validation reports (default: source/tests/sample_plots/validation_reports/<dataset_name>)")
    parser.add_argument("--no-plots", action="store_true", help="Disable generation of validation plots")
    
    args = parser.parse_args()
    
    try:
        # Create dataset validator
        validator = DatasetValidator(args.dataset, args.output, generate_plots=not args.no_plots)
        
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