#!/usr/bin/env python3
"""
Consolidated Validation System

This module combines all validation-related functionality into a single, cohesive system.
It merges the functionality from:
- dataset_validator_phase.py (main orchestrator)
- phase_validator.py (enhanced validation)
- step_classifier.py (classification logic)
- validation_offset_utils.py (utilities)

This consolidation reduces complexity, eliminates circular dependencies, and provides
a single source of truth for all validation operations.

Key Components:
1. **Validation Utilities** - Contralateral offset logic and completeness checks
2. **Step Classification** - Color-coding logic for validation visualization
3. **Dataset Validation** - Main validation orchestrator for phase-based datasets
4. **Enhanced Validation** - Strict 150-point enforcement and batch processing

Usage:
    from internal.validation_engine.validator import DatasetValidator, StepClassifier
    
    # For dataset validation
    validator = DatasetValidator(dataset_path)
    results = validator.run_validation()
    
    # For step classification
    classifier = StepClassifier()
    step_colors = classifier.validate_and_classify_from_specs(...)
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
from datetime import datetime
import warnings
from dataclasses import dataclass

# Import external dependencies
try:
    from user_libs.python.locomotion_data import LocomotionData
    from user_libs.python.feature_constants import (
        ANGLE_FEATURES, MOMENT_FEATURES, 
        get_kinematic_feature_map, get_kinetic_feature_map,
        get_feature_list
    )
except ImportError as e:
    raise ImportError(f"Could not import required library modules: {e}")


# ============================================================================
# SECTION 1: VALIDATION UTILITIES (from validation_offset_utils.py)
# ============================================================================

def apply_contralateral_offset_kinematic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]], 
    task_name: str = None
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Apply contralateral offset logic for kinematic variables.
    
    For gait-based tasks, the contralateral leg is 50% out of phase:
    - Phase 0% ipsilateral = Phase 50% contralateral
    - Phase 25% ipsilateral = Phase 75% contralateral
    - Phase 50% ipsilateral = Phase 0% contralateral
    - Phase 75% ipsilateral = Phase 25% contralateral
    
    Args:
        phase_data: Dictionary with phase percentages as keys
        task_name: Name of the task (for determining if offset should apply)
        
    Returns:
        Dictionary with contralateral variables added based on offset logic
    """
    # Gait-based tasks where contralateral offset applies
    gait_tasks = [
        'level_walking', 'incline_walking', 'decline_walking',
        'stair_ascent', 'stair_descent', 'running', 'sprinting',
        'up_stairs', 'down_stairs', 'run'
    ]
    
    # Check if this is a gait task
    is_gait_task = task_name and any(task in task_name.lower() for task in gait_tasks)
    
    if not is_gait_task:
        return phase_data
    
    # Create a copy to avoid modifying the original
    result = {}
    
    # Phase offset mapping for contralateral leg
    phase_offset_map = {
        0: 50,
        25: 75,
        50: 0,
        75: 25,
        95: 45  # Special case for 95% phase if present
    }
    
    for phase_pct, variables in phase_data.items():
        result[phase_pct] = {}
        
        # Copy all ipsilateral variables
        for var_name, var_range in variables.items():
            if '_ipsi' in var_name:
                result[phase_pct][var_name] = var_range.copy()
        
        # Add contralateral variables from offset phase
        if phase_pct in phase_offset_map:
            offset_phase = phase_offset_map[phase_pct]
            if offset_phase in phase_data:
                for var_name, var_range in phase_data[offset_phase].items():
                    if '_ipsi' in var_name:
                        # Create contralateral version
                        contra_name = var_name.replace('_ipsi', '_contra')
                        result[phase_pct][contra_name] = var_range.copy()
    
    return result


def apply_contralateral_offset_kinetic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]],
    task_name: str = None
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Apply contralateral offset logic for kinetic variables.
    
    For gait-based tasks, the contralateral leg is 50% out of phase.
    Same logic as kinematic but for force/moment variables.
    
    Args:
        phase_data: Dictionary with phase percentages as keys
        task_name: Name of the task
        
    Returns:
        Dictionary with contralateral variables added
    """
    # Gait-based tasks where contralateral offset applies
    gait_tasks = [
        'level_walking', 'incline_walking', 'decline_walking',
        'stair_ascent', 'stair_descent', 'running', 'sprinting',
        'up_stairs', 'down_stairs', 'run'
    ]
    
    # Check if this is a gait task
    is_gait_task = task_name and any(task in task_name.lower() for task in gait_tasks)
    
    if not is_gait_task:
        return phase_data
    
    # Create a copy to avoid modifying the original
    result = {}
    
    # Phase offset mapping for contralateral leg
    phase_offset_map = {
        0: 50,
        25: 75,
        50: 0,
        75: 25,
        95: 45  # Special case for 95% phase if present
    }
    
    for phase_pct, variables in phase_data.items():
        result[phase_pct] = {}
        
        # Copy all ipsilateral variables
        for var_name, var_range in variables.items():
            if '_ipsi' in var_name:
                result[phase_pct][var_name] = var_range.copy()
        
        # Add contralateral variables from offset phase
        if phase_pct in phase_offset_map:
            offset_phase = phase_offset_map[phase_pct]
            if offset_phase in phase_data:
                for var_name, var_range in phase_data[offset_phase].items():
                    if '_ipsi' in var_name:
                        # Create contralateral version
                        contra_name = var_name.replace('_ipsi', '_contra')
                        result[phase_pct][contra_name] = var_range.copy()
    
    return result


def validate_task_completeness(
    phase_data: Dict[int, Dict[str, Dict[str, float]]],
    task_name: str,
    mode: str
) -> bool:
    """
    Validate that a task has complete phase and variable coverage.
    
    Args:
        phase_data: Dictionary with phase data
        task_name: Name of the task
        mode: 'kinematic' or 'kinetic'
        
    Returns:
        True if validation passes
    """
    required_phases = [0, 25, 50, 75]
    
    # Check required phases exist
    for phase in required_phases:
        if phase not in phase_data:
            print(f"⚠️  Warning: Task '{task_name}' missing phase {phase}% in {mode} validation")
            return False
    
    # Check each phase has variables
    for phase in required_phases:
        if not phase_data[phase]:
            print(f"⚠️  Warning: Task '{task_name}' has no variables at phase {phase}% in {mode} validation")
            return False
    
    return True


# ============================================================================
# SECTION 2: STEP CLASSIFICATION (from step_classifier.py)
# ============================================================================

class StepClassifier:
    """
    Classifies steps based on validation violations for visualization purposes.
    
    This class provides methods to determine how steps should be color-coded in
    validation plots based on their violation status and the specific feature
    being visualized.
    """
    
    def __init__(self):
        """Initialize the step classifier."""
        # Import feature mappings from shared module for consistency
        self.kinematic_feature_map = get_kinematic_feature_map()
        self.kinetic_feature_map = get_kinetic_feature_map()
        
        # Initialize config manager for loading validation ranges
        from internal.config_management.config_manager import ValidationConfigManager
        self.config_manager = ValidationConfigManager()
        
        # Representative phase indices for efficient validation
        self.representative_phase_indices = {
            0: 0,      # 0% phase -> index 0
            25: 37,    # 25% phase -> index ~37 (37.5)
            50: 75,    # 50% phase -> index 75
            75: 112    # 75% phase -> index ~112 (112.5)
        }
        
        # Color mapping for step status
        self.color_map = {
            'valid': '#28a745',     # Green for valid steps
            'local': '#dc3545',     # Red for local violations
            'other': '#ffc107',     # Yellow for other violations
            'invalid': '#6c757d'    # Gray for invalid/missing data
        }
    
    def validate_data_against_specs(
        self,
        data: np.ndarray,
        task_name: str,
        feature_names: List[str],
        mode: str = 'kinematic'
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Validate biomechanical data against specification ranges.
        
        Uses representative phase validation (0%, 25%, 50%, 75%) for efficient checking.
        
        Args:
            data: 3D array of shape (num_steps, 150, num_features)
            task_name: Name of the locomotion task
            feature_names: List of feature names corresponding to data dimensions
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Tuple of:
            - Boolean array of shape (num_steps, num_features) indicating violations
            - Dictionary with detailed validation statistics
        """
        num_steps, num_points, num_features = data.shape
        
        # Ensure we have exactly 150 points per gait cycle
        if num_points != 150:
            raise ValueError(f"Expected 150 points per gait cycle, got {num_points}")
        
        # Load validation ranges from config
        validation_ranges = self.config_manager.load_validation_ranges(mode)
        
        # Apply contralateral offset if needed
        if mode == 'kinematic':
            validation_ranges = {
                task: apply_contralateral_offset_kinematic(ranges, task)
                for task, ranges in validation_ranges.items()
            }
        else:
            validation_ranges = {
                task: apply_contralateral_offset_kinetic(ranges, task)
                for task, ranges in validation_ranges.items()
            }
        
        # Get ranges for this specific task
        if task_name not in validation_ranges:
            print(f"⚠️  Warning: No validation ranges found for task '{task_name}' in {mode} mode")
            return np.zeros((num_steps, num_features), dtype=bool), {}
        
        task_ranges = validation_ranges[task_name]
        
        # Initialize violation matrix
        violations = np.zeros((num_steps, num_features), dtype=bool)
        
        # Statistics tracking
        stats = {
            'total_checks': 0,
            'violations_by_phase': {phase: 0 for phase in self.representative_phase_indices.keys()},
            'violations_by_feature': {feat: 0 for feat in feature_names}
        }
        
        # Validate at representative phases only
        for phase_pct, phase_idx in self.representative_phase_indices.items():
            if phase_pct not in task_ranges:
                continue
                
            phase_ranges = task_ranges[phase_pct]
            
            # Check each feature
            for feat_idx, feat_name in enumerate(feature_names):
                # Handle unit suffixes for matching
                if mode == 'kinematic' and not feat_name.endswith('_rad'):
                    feat_name_with_unit = f"{feat_name}_rad"
                elif mode == 'kinetic' and not feat_name.endswith('_Nm'):
                    feat_name_with_unit = f"{feat_name}_Nm"
                else:
                    feat_name_with_unit = feat_name
                
                # Also try without unit suffix
                feat_name_no_unit = feat_name.replace('_rad', '').replace('_Nm', '')
                
                # Try to find the feature in the ranges
                if feat_name_with_unit in phase_ranges:
                    feat_range = phase_ranges[feat_name_with_unit]
                elif feat_name_no_unit in phase_ranges:
                    feat_range = phase_ranges[feat_name_no_unit]
                elif feat_name in phase_ranges:
                    feat_range = phase_ranges[feat_name]
                else:
                    continue
                
                # Extract min and max values
                min_val = feat_range.get('min', -float('inf'))
                max_val = feat_range.get('max', float('inf'))
                
                # Check each step at this phase
                for step_idx in range(num_steps):
                    value = data[step_idx, phase_idx, feat_idx]
                    stats['total_checks'] += 1
                    
                    # Check if value is outside range
                    if value < min_val or value > max_val:
                        violations[step_idx, feat_idx] = True
                        stats['violations_by_phase'][phase_pct] += 1
                        stats['violations_by_feature'][feature_names[feat_idx]] += 1
        
        # Calculate summary statistics
        stats['total_violations'] = np.sum(violations)
        stats['violation_rate'] = stats['total_violations'] / stats['total_checks'] if stats['total_checks'] > 0 else 0
        stats['steps_with_violations'] = np.sum(np.any(violations, axis=1))
        stats['features_with_violations'] = np.sum(np.any(violations, axis=0))
        
        return violations, stats
    
    def classify_steps_for_feature(
        self,
        violations: np.ndarray,
        feature_idx: int,
        feature_names: List[str]
    ) -> List[str]:
        """
        Classify steps for visualization based on violations.
        
        Args:
            violations: Boolean array of shape (num_steps, num_features)
            feature_idx: Index of the feature being visualized
            feature_names: List of feature names
            
        Returns:
            List of color codes for each step
        """
        num_steps = violations.shape[0]
        step_colors = []
        
        for step_idx in range(num_steps):
            step_violations = violations[step_idx, :]
            
            if not np.any(step_violations):
                # No violations - valid step
                step_colors.append(self.color_map['valid'])
            elif step_violations[feature_idx]:
                # Local violation (in the feature being plotted)
                step_colors.append(self.color_map['local'])
            else:
                # Other violations (in different features)
                step_colors.append(self.color_map['other'])
        
        return step_colors
    
    def validate_and_classify_from_specs(
        self,
        data: np.ndarray,
        task_name: str,
        feature_names: List[str],
        feature_idx: int,
        mode: str = 'kinematic'
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Complete validation and classification workflow.
        
        Args:
            data: 3D array of shape (num_steps, 150, num_features)
            task_name: Name of the locomotion task
            feature_names: List of feature names
            feature_idx: Index of the feature being visualized
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Tuple of:
            - List of color codes for each step
            - Dictionary with validation statistics
        """
        # Validate data against specifications
        violations, stats = self.validate_data_against_specs(
            data, task_name, feature_names, mode
        )
        
        # Classify steps for the specific feature
        step_colors = self.classify_steps_for_feature(
            violations, feature_idx, feature_names
        )
        
        return step_colors, stats


# ============================================================================
# SECTION 3: DATASET VALIDATOR (from dataset_validator_phase.py)
# ============================================================================

class DatasetValidator:
    """
    Comprehensive dataset validator for phase-based locomotion datasets.
    
    This validator combines functionality from the original dataset_validator_phase
    and enhanced phase_validator for complete validation capabilities.
    """
    
    def __init__(self, dataset_path: str, output_dir: str = None, generate_plots: bool = True):
        """
        Initialize the dataset validator.
        
        Args:
            dataset_path: Path to the phase-based dataset parquet file
            output_dir: Directory to save validation reports
            generate_plots: Whether to generate validation plots
        """
        self.dataset_path = dataset_path
        self.generate_plots = generate_plots
        
        # Extract dataset name for use in output files
        self.dataset_name = Path(dataset_path).stem
        
        # Set default output directory if not specified
        if output_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            output_dir = project_root / "docs" / "user_guide" / "docs" / "reference" / "datasets_documentation" / "validation_reports"
        
        # Create output directory structure
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reports and plots go in the same directory
        self.reports_dir = self.output_dir
        self.plots_dir = self.output_dir
        
        # Initialize step classifier for validation
        self.step_classifier = StepClassifier()
        
        # Initialize config manager
        from internal.config_management.config_manager import ValidationConfigManager
        self.config_manager = ValidationConfigManager()
        
        # Load validation expectations from YAML config
        try:
            self.kinematic_expectations = self.config_manager.load_validation_ranges('kinematic')
            self.kinetic_expectations = self.config_manager.load_validation_ranges('kinetic')
        except Exception as e:
            print(f"⚠️  Warning: Could not load validation expectations: {e}")
            self.kinematic_expectations = {}
            self.kinetic_expectations = {}
    
    def load_dataset(self) -> LocomotionData:
        """Load the dataset using LocomotionData library."""
        try:
            # Try loading with default phase column
            locomotion_data = LocomotionData(self.dataset_path)
        except ValueError as e:
            # Try with phase_percent column if phase column doesn't exist
            if "Missing required columns" in str(e) and "phase" in str(e):
                locomotion_data = LocomotionData(self.dataset_path, phase_col='phase_percent')
            else:
                raise e
        
        return locomotion_data
    
    def validate_phase_structure(self, locomotion_data: LocomotionData) -> Dict[str, Any]:
        """
        Validate that the dataset has proper phase structure.
        
        Args:
            locomotion_data: Loaded locomotion dataset
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'issues': [],
            'stats': {}
        }
        
        # Get basic dataset info
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        results['stats']['num_subjects'] = len(subjects)
        results['stats']['num_tasks'] = len(tasks)
        results['stats']['total_cycles'] = 0
        
        # Check each subject-task combination
        for subject in subjects:
            for task in tasks:
                try:
                    # Get cycles for this combination
                    cycles, features = locomotion_data.get_cycles(
                        subject=subject,
                        task=task,
                        features=None
                    )
                    
                    if cycles.size == 0:
                        continue
                    
                    num_cycles, num_points, num_features = cycles.shape
                    results['stats']['total_cycles'] += num_cycles
                    
                    # Check for exactly 150 points
                    if num_points != 150:
                        results['valid'] = False
                        results['issues'].append(
                            f"Subject {subject}, Task {task}: Expected 150 points per cycle, got {num_points}"
                        )
                    
                except Exception as e:
                    results['issues'].append(
                        f"Error processing Subject {subject}, Task {task}: {e}"
                    )
        
        return results
    
    def validate_against_specifications(
        self, 
        locomotion_data: LocomotionData
    ) -> Dict[str, Any]:
        """
        Validate dataset against biomechanical specifications.
        
        Args:
            locomotion_data: Loaded locomotion dataset
            
        Returns:
            Dictionary with validation results by task and mode
        """
        results = {
            'kinematic': {},
            'kinetic': {},
            'summary': {
                'total_steps': 0,
                'valid_steps': 0,
                'validation_rate': 0.0
            }
        }
        
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        for task in tasks:
            # Process kinematic validation
            if task in self.kinematic_expectations:
                results['kinematic'][task] = self._validate_task(
                    locomotion_data, task, 'kinematic', subjects
                )
            
            # Process kinetic validation
            if task in self.kinetic_expectations:
                results['kinetic'][task] = self._validate_task(
                    locomotion_data, task, 'kinetic', subjects
                )
        
        # Calculate summary statistics
        for mode_results in [results['kinematic'], results['kinetic']]:
            for task_results in mode_results.values():
                if 'stats' in task_results:
                    results['summary']['total_steps'] += task_results['stats'].get('total_checks', 0)
                    results['summary']['valid_steps'] += (
                        task_results['stats'].get('total_checks', 0) - 
                        task_results['stats'].get('total_violations', 0)
                    )
        
        if results['summary']['total_steps'] > 0:
            results['summary']['validation_rate'] = (
                results['summary']['valid_steps'] / results['summary']['total_steps']
            )
        
        return results
    
    def _validate_task(
        self,
        locomotion_data: LocomotionData,
        task: str,
        mode: str,
        subjects: List[str]
    ) -> Dict[str, Any]:
        """
        Validate a specific task in a specific mode.
        
        Args:
            locomotion_data: Loaded dataset
            task: Task name
            mode: 'kinematic' or 'kinetic'
            subjects: List of subjects
            
        Returns:
            Validation results for this task
        """
        # Determine which features to validate
        if mode == 'kinematic':
            standard_features = get_feature_list('kinematic')
        else:
            standard_features = get_feature_list('kinetic')
        
        # Filter to available features
        available_features = locomotion_data.features
        features_to_validate = [f for f in standard_features if f in available_features]
        
        if not features_to_validate:
            return {'error': f'No {mode} features found for validation'}
        
        # Collect all data for this task
        all_steps = []
        
        for subject in subjects:
            try:
                cycles, feature_names = locomotion_data.get_cycles(
                    subject=subject,
                    task=task,
                    features=features_to_validate
                )
                
                if cycles.size > 0:
                    all_steps.append(cycles)
            except:
                continue
        
        if not all_steps:
            return {'error': f'No data found for task {task}'}
        
        # Concatenate all steps
        all_steps_array = np.concatenate(all_steps, axis=0)
        
        # Validate using step classifier
        violations, stats = self.step_classifier.validate_data_against_specs(
            all_steps_array, task, features_to_validate, mode
        )
        
        return {
            'violations': violations,
            'stats': stats,
            'num_steps': all_steps_array.shape[0],
            'features': features_to_validate
        }
    
    def generate_validation_plots(
        self,
        locomotion_data: LocomotionData,
        validation_results: Dict[str, Any]
    ) -> List[str]:
        """
        Generate validation plots for the dataset.
        
        Args:
            locomotion_data: Loaded dataset
            validation_results: Results from validation
            
        Returns:
            List of generated plot file paths
        """
        plot_files = []
        
        # Import plot generation functions
        from internal.plot_generation.filters_by_phase_plots import create_filters_by_phase_plot
        
        for mode in ['kinematic', 'kinetic']:
            mode_results = validation_results.get(mode, {})
            
            for task, task_results in mode_results.items():
                if 'error' in task_results:
                    continue
                
                try:
                    # Generate plot for this task
                    plot_path = create_filters_by_phase_plot(
                        validation_data=self.kinematic_expectations if mode == 'kinematic' else self.kinetic_expectations,
                        task_name=task,
                        output_dir=str(self.plots_dir),
                        mode=mode,
                        data=None,  # We could overlay actual data here
                        step_colors=None,
                        dataset_name=self.dataset_name,
                        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                    
                    if plot_path:
                        plot_files.append(plot_path)
                        
                except Exception as e:
                    print(f"⚠️  Warning: Could not generate plot for {task} ({mode}): {e}")
        
        return plot_files
    
    def generate_report(
        self,
        phase_results: Dict[str, Any],
        validation_results: Dict[str, Any],
        plot_files: List[str]
    ) -> str:
        """
        Generate markdown validation report.
        
        Args:
            phase_results: Results from phase structure validation
            validation_results: Results from specification validation
            plot_files: List of generated plot files
            
        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine overall status
        validation_rate = validation_results['summary']['validation_rate']
        if validation_rate >= 0.95:
            status = "✅ PASSED"
        elif validation_rate >= 0.80:
            status = "⚠️ PARTIAL"
        else:
            status = "❌ FAILED"
        
        # Build report content
        report = f"""# Dataset Validation Report: {self.dataset_name}

**Generated**: {timestamp}  
**Status**: {status} ({validation_rate*100:.1f}% valid)

## Phase Structure Validation

- **Subjects**: {phase_results['stats']['num_subjects']}
- **Tasks**: {phase_results['stats']['num_tasks']}
- **Total Cycles**: {phase_results['stats']['total_cycles']}
- **Structure Valid**: {'✅ Yes' if phase_results['valid'] else '❌ No'}

"""
        
        if phase_results['issues']:
            report += "### Issues Found:\n"
            for issue in phase_results['issues'][:10]:  # Limit to first 10 issues
                report += f"- {issue}\n"
            report += "\n"
        
        # Add validation results
        report += "## Biomechanical Validation\n\n"
        
        for mode in ['kinematic', 'kinetic']:
            mode_results = validation_results.get(mode, {})
            if mode_results:
                report += f"### {mode.title()} Validation\n\n"
                
                for task, task_results in mode_results.items():
                    if 'error' in task_results:
                        report += f"- **{task}**: ⚠️ {task_results['error']}\n"
                    elif 'stats' in task_results:
                        stats = task_results['stats']
                        violation_rate = stats.get('violation_rate', 0)
                        report += f"- **{task}**: {(1-violation_rate)*100:.1f}% valid ({task_results['num_steps']} steps)\n"
                
                report += "\n"
        
        # Add plots section if any were generated
        if plot_files and self.generate_plots:
            report += "## Validation Plots\n\n"
            for plot_file in plot_files:
                plot_name = Path(plot_file).name
                report += f"![{plot_name}]({plot_name})\n\n"
        
        # Save report
        report_path = self.reports_dir / f"{self.dataset_name}_validation_report.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        return str(report_path)
    
    def run_validation(self) -> str:
        """
        Run complete validation workflow.
        
        Returns:
            Path to generated validation report
        """
        print(f"\n🔍 Validating dataset: {self.dataset_name}")
        print("="*60)
        
        # Load dataset
        print("📂 Loading dataset...")
        locomotion_data = self.load_dataset()
        
        # Validate phase structure
        print("🔍 Validating phase structure...")
        phase_results = self.validate_phase_structure(locomotion_data)
        
        # Validate against specifications
        print("📊 Validating against biomechanical specifications...")
        validation_results = self.validate_against_specifications(locomotion_data)
        
        # Generate plots if requested
        plot_files = []
        if self.generate_plots:
            print("📈 Generating validation plots...")
            plot_files = self.generate_validation_plots(locomotion_data, validation_results)
        
        # Generate report
        print("📄 Generating validation report...")
        report_path = self.generate_report(phase_results, validation_results, plot_files)
        
        print(f"\n✅ Validation complete!")
        print(f"📄 Report saved: {report_path}")
        
        return report_path


# ============================================================================
# SECTION 4: ENHANCED PHASE VALIDATOR (from phase_validator.py)
# ============================================================================

@dataclass
class PhaseValidationResult:
    """Container for phase validation results."""
    is_valid: bool
    num_points: int
    expected_points: int = 150
    message: str = ""
    details: Dict[str, Any] = None


class EnhancedPhaseValidator(DatasetValidator):
    """
    Enhanced validator with strict 150-point enforcement and batch processing.
    
    This class extends the base DatasetValidator with additional capabilities
    for memory-efficient processing and stricter validation rules.
    """
    
    def __init__(self, dataset_path: str, output_dir: str = None, generate_plots: bool = True):
        """Initialize enhanced validator."""
        super().__init__(dataset_path, output_dir, generate_plots)
        
        # Enhanced validation settings
        self.strict_mode = True
        self.batch_size = 100  # Process in batches for memory efficiency
        self.enable_caching = True
        self._validation_cache = {}
    
    def enable_batch_processing(self, batch_size: int = 100):
        """
        Enable memory-efficient batch processing for large datasets.
        
        Args:
            batch_size: Number of steps to process at once
        """
        self.batch_size = batch_size
        print(f"✅ Batch processing enabled with batch size: {batch_size}")
    
    def validate_strict_phase_length(self, data: np.ndarray) -> PhaseValidationResult:
        """
        Strictly validate that each gait cycle has exactly 150 points.
        
        Args:
            data: Array with shape (..., num_points, ...)
            
        Returns:
            PhaseValidationResult with validation details
        """
        # Find the phase dimension (should be 150)
        phase_dim = None
        for i, dim_size in enumerate(data.shape):
            if dim_size == 150:
                phase_dim = i
                break
        
        if phase_dim is None:
            # Check if any dimension is close to 150
            for i, dim_size in enumerate(data.shape):
                if 140 <= dim_size <= 160:
                    return PhaseValidationResult(
                        is_valid=False,
                        num_points=dim_size,
                        message=f"Phase dimension has {dim_size} points, expected exactly 150"
                    )
            
            return PhaseValidationResult(
                is_valid=False,
                num_points=0,
                message="No dimension with 150 points found"
            )
        
        return PhaseValidationResult(
            is_valid=True,
            num_points=150,
            message="Phase structure validated successfully"
        )
    
    def validate_large_dataset(self) -> str:
        """
        Validate large datasets using batch processing.
        
        Returns:
            Path to validation report
        """
        print(f"\n🔍 Validating large dataset: {self.dataset_name}")
        print(f"   Using batch processing (batch size: {self.batch_size})")
        print("="*60)
        
        # Load dataset
        print("📂 Loading dataset...")
        locomotion_data = self.load_dataset()
        
        # Get dataset dimensions
        subjects = locomotion_data.get_subjects()
        tasks = locomotion_data.get_tasks()
        
        total_combinations = len(subjects) * len(tasks)
        processed = 0
        
        # Process in batches
        all_results = {
            'phase_validation': {'valid': True, 'issues': [], 'stats': {}},
            'kinematic': {},
            'kinetic': {},
            'summary': {'total_steps': 0, 'valid_steps': 0}
        }
        
        for task in tasks:
            print(f"\n📊 Processing task: {task}")
            
            # Process subjects in batches
            for batch_start in range(0, len(subjects), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(subjects))
                batch_subjects = subjects[batch_start:batch_end]
                
                print(f"   Batch {batch_start//self.batch_size + 1}: Subjects {batch_start+1}-{batch_end}")
                
                # Validate batch
                batch_results = self._validate_task(
                    locomotion_data, task, 'kinematic', batch_subjects
                )
                
                # Aggregate results
                if task not in all_results['kinematic']:
                    all_results['kinematic'][task] = batch_results
                else:
                    # Merge batch results
                    self._merge_batch_results(all_results['kinematic'][task], batch_results)
                
                processed += len(batch_subjects)
                progress = (processed / total_combinations) * 100
                print(f"   Progress: {progress:.1f}%")
        
        # Generate report
        report_path = self.generate_report(
            all_results['phase_validation'],
            all_results,
            []
        )
        
        return report_path
    
    def _merge_batch_results(self, accumulated: Dict, batch: Dict):
        """Merge batch results into accumulated results."""
        if 'stats' in batch:
            if 'stats' not in accumulated:
                accumulated['stats'] = batch['stats']
            else:
                # Merge statistics
                for key in ['total_checks', 'total_violations']:
                    accumulated['stats'][key] = accumulated['stats'].get(key, 0) + batch['stats'].get(key, 0)
                
                # Recalculate rates
                if accumulated['stats']['total_checks'] > 0:
                    accumulated['stats']['violation_rate'] = (
                        accumulated['stats']['total_violations'] / 
                        accumulated['stats']['total_checks']
                    )
        
        if 'num_steps' in batch:
            accumulated['num_steps'] = accumulated.get('num_steps', 0) + batch['num_steps']
    
    def validate_comprehensive(self) -> str:
        """
        Run comprehensive validation with all enhanced features.
        
        Returns:
            Path to validation report
        """
        if self.batch_size and self.batch_size < 1000:
            # Use batch processing for large datasets
            return self.validate_large_dataset()
        else:
            # Use standard validation
            return self.run_validation()


# ============================================================================
# MAIN ENTRY POINT (if run as script)
# ============================================================================

def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Validate phase-based locomotion datasets"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to phase-based dataset parquet file"
    )
    parser.add_argument(
        "--output",
        help="Output directory for validation reports"
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generation of validation plots"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Enable batch processing with specified batch size"
    )
    parser.add_argument(
        "--enhanced",
        action="store_true",
        help="Use enhanced validator with strict 150-point enforcement"
    )
    
    args = parser.parse_args()
    
    # Choose validator based on options
    if args.enhanced or args.batch_size:
        validator = EnhancedPhaseValidator(
            args.dataset,
            args.output,
            not args.no_plots
        )
        if args.batch_size:
            validator.enable_batch_processing(args.batch_size)
        report_path = validator.validate_comprehensive()
    else:
        validator = DatasetValidator(
            args.dataset,
            args.output,
            not args.no_plots
        )
        report_path = validator.run_validation()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())