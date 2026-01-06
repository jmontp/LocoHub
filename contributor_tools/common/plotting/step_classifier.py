#!/usr/bin/env python3
"""
Step Classification for Validation Plots

Classifies steps for color-coding in validation visualization plots.
This functionality is only needed for plot generation, not core validation.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


class StepClassifier:
    """
    Classifies steps based on validation violations for visualization purposes.
    
    This class provides methods to determine how steps should be color-coded in
    validation plots based on their violation status and the specific feature
    being displayed.
    """
    
    def __init__(self):
        """Initialize the step classifier."""
        pass
    
    def classify_steps_for_feature(
        self,
        violations: np.ndarray,
        feature_idx: int
    ) -> np.ndarray:
        """
        Classify steps for a specific feature in validation plots.
        
        Args:
            violations: Boolean array of shape (num_steps, num_features) 
                       indicating violations
            feature_idx: Index of the feature being displayed
            
        Returns:
            Array of color classifications for each step:
            - 'green': No violations in any feature
            - 'red': Violation in the current feature
            - 'yellow': Violations in other features but not current
        """
        num_steps = violations.shape[0]
        colors = np.empty(num_steps, dtype=object)
        
        for step_idx in range(num_steps):
            step_violations = violations[step_idx, :]
            
            if step_violations[feature_idx]:
                # Violation in current feature
                colors[step_idx] = 'red'
            elif np.any(step_violations):
                # Violations in other features
                colors[step_idx] = 'yellow'
            else:
                # No violations
                colors[step_idx] = 'green'
        
        return colors
    
    def classify_all_steps(
        self,
        violations: np.ndarray
    ) -> np.ndarray:
        """
        Classify all steps for all features.
        
        Args:
            violations: Boolean array of shape (num_steps, num_features)
            
        Returns:
            2D array of shape (num_steps, num_features) with color classifications
        """
        num_steps, num_features = violations.shape
        colors = np.empty((num_steps, num_features), dtype=object)
        
        for feature_idx in range(num_features):
            colors[:, feature_idx] = self.classify_steps_for_feature(
                violations, feature_idx
            )
        
        return colors
    
    def get_summary_statistics(
        self,
        colors: np.ndarray
    ) -> Dict[str, int]:
        """
        Get summary statistics from color classifications.
        
        Args:
            colors: Array of color classifications
            
        Returns:
            Dictionary with counts of each color type
        """
        if len(colors.shape) == 1:
            # 1D array
            return {
                'green': np.sum(colors == 'green'),
                'yellow': np.sum(colors == 'yellow'),
                'red': np.sum(colors == 'red'),
                'total': len(colors)
            }
        else:
            # 2D array - count steps where all features are green
            all_green_steps = np.all(colors == 'green', axis=1)
            any_red_steps = np.any(colors == 'red', axis=1)
            any_yellow_steps = np.any(colors == 'yellow', axis=1)
            
            return {
                'all_green': np.sum(all_green_steps),
                'any_red': np.sum(any_red_steps),
                'any_yellow': np.sum(any_yellow_steps),
                'total': colors.shape[0]
            }