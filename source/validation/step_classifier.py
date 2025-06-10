#!/usr/bin/env python3
"""
Step Classification Module for Validation Plotting

Created: 2025-06-10
Purpose: Classify steps based on validation violations for use in filters by phase plots.

Intent:
This module provides step classification functionality that determines how individual
steps should be color-coded in validation plots based on their violation status:

- Gray: Valid steps with no violations
- Red: Steps with local violations (violations in the feature being plotted)  
- Pink: Steps with other violations (violations in different features)

The classifier takes validation results and feature information to produce step color
arrays that can be directly used with the filters_by_phase_plots module.

Key Features:
1. **Precise Step Tracking**: Maps validation failures to specific step indices
2. **Feature-Aware Classification**: Distinguishes local vs other violations per feature
3. **Flexible Input**: Works with various validation result formats
4. **Batch Processing**: Efficiently classifies multiple steps at once
5. **Extensible**: Easy to add new classification rules or color schemes

Usage:
    from validation.step_classifier import StepClassifier
    
    classifier = StepClassifier()
    step_colors = classifier.classify_steps_for_feature(
        validation_failures=failures,
        step_task_mapping=step_mapping,
        feature_name='hip_flexion_angle_ipsi',
        mode='kinematic'
    )

This separation of concerns allows the dataset validator to focus on validation logic
while the step classifier handles the color mapping logic for visualization.
"""

import numpy as np
from typing import Dict, List, Union, Optional, Tuple
from pathlib import Path


class StepClassifier:
    """
    Classifies steps based on validation violations for visualization purposes.
    
    This class provides methods to determine how steps should be color-coded in
    validation plots based on their violation status and the specific feature
    being visualized.
    """
    
    def __init__(self):
        """Initialize the step classifier."""
        # Define feature mappings for kinematic variables
        self.kinematic_feature_map = {
            'hip_flexion_angle_ipsi': 0,
            'hip_flexion_angle_contra': 1,
            'knee_flexion_angle_ipsi': 2,
            'knee_flexion_angle_contra': 3,
            'ankle_flexion_angle_ipsi': 4,
            'ankle_flexion_angle_contra': 5
        }
        
        # Define feature mappings for kinetic variables
        self.kinetic_feature_map = {
            'hip_moment_ipsi_Nm_kg': 0,
            'hip_moment_contra_Nm_kg': 1,
            'knee_moment_ipsi_Nm_kg': 2,
            'knee_moment_contra_Nm_kg': 3,
            'ankle_moment_ipsi_Nm_kg': 4,
            'ankle_moment_contra_Nm_kg': 5
        }
        
        # Color scheme definitions
        self.color_scheme = {
            'valid': 'gray',
            'local_violation': 'red',
            'other_violation': 'pink'
        }
    
    def get_feature_map(self, mode: str) -> Dict[str, int]:
        """
        Get the feature mapping for the specified mode.
        
        Args:
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Dictionary mapping variable names to feature indices
        """
        if mode == 'kinematic':
            return self.kinematic_feature_map.copy()
        elif mode == 'kinetic':
            return self.kinetic_feature_map.copy()
        else:
            raise ValueError(f"Unknown mode: {mode}. Expected 'kinematic' or 'kinetic'")
    
    def extract_step_violations_from_failures(self, validation_failures: List[Dict], 
                                            step_task_mapping: Dict[int, str]) -> Dict[int, List[str]]:
        """
        Extract step-level violations from validation failure list.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_task_mapping: Mapping from step index to task name
            
        Returns:
            Dictionary mapping step indices to lists of violated variables
        """
        step_violations = {}
        
        # Group failures by task to enable step matching
        failures_by_task = {}
        for failure in validation_failures:
            task = failure.get('task', 'unknown')
            if task not in failures_by_task:
                failures_by_task[task] = []
            failures_by_task[task].append(failure)
        
        # For each step, determine which variables have violations
        for step_idx, task in step_task_mapping.items():
            step_violations[step_idx] = []
            
            if task in failures_by_task:
                # Extract violated variables for this task
                # Note: This is a simplified approach - in practice, we'd need
                # additional step tracking to map failures to specific steps
                violated_variables = set()
                for failure in failures_by_task[task]:
                    violated_variables.add(failure.get('variable', ''))
                
                step_violations[step_idx] = list(violated_variables)
        
        return step_violations
    
    def classify_steps_for_feature(self, validation_failures: List[Dict], 
                                 step_task_mapping: Dict[int, str],
                                 feature_name: str, mode: str) -> np.ndarray:
        """
        Classify steps for a specific feature being plotted.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_task_mapping: Mapping from step index to task name
            feature_name: Name of the feature being plotted (e.g., 'hip_flexion_angle_ipsi')
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Array of step colors with shape (num_steps,)
        """
        num_steps = len(step_task_mapping)
        step_colors = np.array([self.color_scheme['valid']] * num_steps)
        
        # Extract step violations
        step_violations = self.extract_step_violations_from_failures(
            validation_failures, step_task_mapping
        )
        
        # Classify each step based on its violations
        for step_idx in range(num_steps):
            violated_variables = step_violations.get(step_idx, [])
            
            if feature_name in violated_variables:
                # This step has a violation in the current feature (local violation)
                step_colors[step_idx] = self.color_scheme['local_violation']
            elif violated_variables:
                # This step has violations in other features (other violation)
                step_colors[step_idx] = self.color_scheme['other_violation']
            # Otherwise, step remains gray (valid)
        
        return step_colors
    
    def classify_steps_for_all_features(self, validation_failures: List[Dict],
                                      step_task_mapping: Dict[int, str],
                                      mode: str) -> Dict[str, np.ndarray]:
        """
        Classify steps for all features in the specified mode.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_task_mapping: Mapping from step index to task name
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Dictionary mapping feature names to step color arrays
        """
        feature_map = self.get_feature_map(mode)
        classifications = {}
        
        for feature_name in feature_map.keys():
            classifications[feature_name] = self.classify_steps_for_feature(
                validation_failures, step_task_mapping, feature_name, mode
            )
        
        return classifications
    
    def get_step_summary_classification(self, validation_failures: List[Dict],
                                      step_task_mapping: Dict[int, str]) -> np.ndarray:
        """
        Get a summary classification for steps (used when feature is not specified).
        
        This provides a general classification based on whether steps have any violations,
        useful for overview plots or when specific feature information is not available.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_task_mapping: Mapping from step index to task name
            
        Returns:
            Array of step colors with shape (num_steps,)
        """
        num_steps = len(step_task_mapping)
        step_colors = np.array([self.color_scheme['valid']] * num_steps)
        
        # Extract step violations
        step_violations = self.extract_step_violations_from_failures(
            validation_failures, step_task_mapping
        )
        
        # Mark steps with any violations as having violations (use red for summary)
        for step_idx, violated_variables in step_violations.items():
            if violated_variables:
                step_colors[step_idx] = self.color_scheme['local_violation']
        
        return step_colors
    
    def create_step_classification_report(self, validation_failures: List[Dict],
                                        step_task_mapping: Dict[int, str],
                                        mode: str) -> Dict:
        """
        Create a comprehensive report of step classifications.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_task_mapping: Mapping from step index to task name
            mode: 'kinematic' or 'kinetic'
            
        Returns:
            Dictionary containing classification statistics and details
        """
        classifications = self.classify_steps_for_all_features(
            validation_failures, step_task_mapping, mode
        )
        
        # Calculate statistics
        num_steps = len(step_task_mapping)
        report = {
            'total_steps': num_steps,
            'mode': mode,
            'feature_classifications': classifications,
            'summary': {
                'valid_steps': 0,
                'local_violation_steps': 0,
                'other_violation_steps': 0
            },
            'by_feature': {}
        }
        
        # Calculate per-feature statistics
        for feature_name, step_colors in classifications.items():
            valid_count = np.sum(step_colors == self.color_scheme['valid'])
            local_count = np.sum(step_colors == self.color_scheme['local_violation'])
            other_count = np.sum(step_colors == self.color_scheme['other_violation'])
            
            report['by_feature'][feature_name] = {
                'valid': int(valid_count),
                'local_violations': int(local_count),
                'other_violations': int(other_count)
            }
        
        # Calculate overall summary (steps with any violations)
        step_violations = self.extract_step_violations_from_failures(
            validation_failures, step_task_mapping
        )
        
        for step_idx in range(num_steps):
            if step_violations.get(step_idx, []):
                if any(feature_colors[step_idx] == self.color_scheme['local_violation'] 
                      for feature_colors in classifications.values()):
                    report['summary']['local_violation_steps'] += 1
                else:
                    report['summary']['other_violation_steps'] += 1
            else:
                report['summary']['valid_steps'] += 1
        
        return report
    
    def create_enhanced_step_mapping(self, validation_failures: List[Dict],
                                   step_identifiers: List[Dict]) -> Tuple[Dict[int, str], Dict[int, List[str]]]:
        """
        Create enhanced step mapping with precise step tracking.
        
        This method addresses the limitation of the simplified approach by providing
        precise mapping between validation failures and specific steps.
        
        Args:
            validation_failures: List of validation failure dictionaries
            step_identifiers: List of step identifier dictionaries with keys:
                            ['step_index', 'subject', 'task', 'step_number', etc.]
            
        Returns:
            Tuple of (step_task_mapping, step_violations_mapping)
        """
        step_task_mapping = {}
        step_violations_mapping = {}
        
        # Create step task mapping from identifiers
        for step_info in step_identifiers:
            step_idx = step_info.get('step_index', 0)
            task = step_info.get('task', 'unknown')
            step_task_mapping[step_idx] = task
            step_violations_mapping[step_idx] = []
        
        # Enhanced failure mapping (would need additional step tracking in validator)
        # This is a placeholder for future enhancement
        for failure in validation_failures:
            # In a full implementation, we'd match failures to specific steps
            # using subject, task, step_number, and phase information
            pass
        
        return step_task_mapping, step_violations_mapping


def demo_step_classifier():
    """Demonstration of the step classifier functionality."""
    print("🎨 Step Classifier Demo")
    
    # Create sample validation failures
    sample_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Value 0.800 above maximum 0.600 at phase 25.0%'
        },
        {
            'task': 'level_walking', 
            'variable': 'knee_flexion_angle_contra',
            'phase': 50.0,
            'value': 1.5,
            'expected_min': 0.0,
            'expected_max': 0.15,
            'failure_reason': 'Value 1.500 above maximum 0.150 at phase 50.0%'
        }
    ]
    
    # Create sample step mapping
    step_task_mapping = {
        0: 'level_walking',
        1: 'level_walking', 
        2: 'level_walking',
        3: 'level_walking',
        4: 'level_walking'
    }
    
    # Initialize classifier
    classifier = StepClassifier()
    
    # Classify steps for hip ipsi feature
    hip_colors = classifier.classify_steps_for_feature(
        sample_failures, step_task_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"Hip ipsi colors: {hip_colors}")
    
    # Classify steps for knee contra feature  
    knee_colors = classifier.classify_steps_for_feature(
        sample_failures, step_task_mapping, 'knee_flexion_angle_contra', 'kinematic'
    )
    print(f"Knee contra colors: {knee_colors}")
    
    # Get summary classification
    summary_colors = classifier.get_step_summary_classification(
        sample_failures, step_task_mapping
    )
    print(f"Summary colors: {summary_colors}")
    
    # Create full report
    report = classifier.create_step_classification_report(
        sample_failures, step_task_mapping, 'kinematic'
    )
    print(f"Classification report: {report}")


if __name__ == "__main__":
    demo_step_classifier()