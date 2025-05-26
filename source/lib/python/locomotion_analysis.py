#!/usr/bin/env python3
"""
Locomotion Analysis Library
===========================

A Python library for loading and processing standardized locomotion data.
Implements efficient 3D array operations for phase-indexed biomechanical data.

Example Usage:
--------------
    from locomotion_analysis import LocomotionData
    
    # Load data
    loco = LocomotionData('path/to/data.parquet')
    
    # Get data for specific subject/task
    data_3d = loco.get_cycles('SUB01', 'normal_walk')
    
    # Calculate mean patterns
    mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
    
    # Validate cycles
    valid_mask = loco.validate_cycles('SUB01', 'normal_walk')
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union
import warnings


class LocomotionData:
    """
    Main class for locomotion data analysis using efficient 3D array operations.
    """
    
    POINTS_PER_CYCLE = 150
    
    # Standard feature groups
    ANGLE_FEATURES = ['hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad',
                      'hip_flexion_angle_left_rad', 'knee_flexion_angle_left_rad', 'ankle_flexion_angle_left_rad']
    
    VELOCITY_FEATURES = ['hip_flexion_velocity_right_rad_s', 'knee_flexion_velocity_right_rad_s', 'ankle_flexion_velocity_right_rad_s',
                         'hip_flexion_velocity_left_rad_s', 'knee_flexion_velocity_left_rad_s', 'ankle_flexion_velocity_left_rad_s']
    
    MOMENT_FEATURES = ['hip_flexion_moment_right_Nm', 'knee_flexion_moment_right_Nm', 'ankle_flexion_moment_right_Nm',
                       'hip_flexion_moment_left_Nm', 'knee_flexion_moment_left_Nm', 'ankle_flexion_moment_left_Nm']
    
    def __init__(self, data_path: Union[str, Path], 
                 subject_col: str = 'subject',
                 task_col: str = 'task',
                 phase_col: str = 'phase'):
        """
        Initialize with phase-indexed locomotion data.
        
        Parameters
        ----------
        data_path : str or Path
            Path to parquet file with phase-indexed data
        subject_col : str
            Column name for subject IDs
        task_col : str
            Column name for task names
        phase_col : str
            Column name for phase values
        """
        self.data_path = Path(data_path)
        self.subject_col = subject_col
        self.task_col = task_col
        self.phase_col = phase_col
        
        # Load data
        self.df = pd.read_parquet(self.data_path)
        
        # Cache for 3D arrays
        self._cache = {}
        
        # Identify biomechanical features
        self._identify_features()
        
    def _identify_features(self):
        """Identify available biomechanical features in the dataset."""
        exclude_cols = {self.subject_col, self.task_col, self.phase_col, 
                       'time', 'time_s', 'step_number', 'is_reconstructed_r', 
                       'is_reconstructed_l', 'task_info', 'activity_number'}
        
        self.features = [col for col in self.df.columns 
                        if col not in exclude_cols and 
                        any(x in col for x in ['angle', 'velocity', 'moment'])]
        
        print(f"Loaded data with {len(self.df)} rows, {self.df[self.subject_col].nunique()} subjects, "
              f"{self.df[self.task_col].nunique()} tasks, {len(self.features)} features")
    
    def get_subjects(self) -> List[str]:
        """Get list of unique subjects."""
        return sorted(self.df[self.subject_col].unique())
    
    def get_tasks(self) -> List[str]:
        """Get list of unique tasks."""
        return sorted(self.df[self.task_col].unique())
    
    def get_cycles(self, subject: str, task: str, 
                   features: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """
        Get 3D array of cycles for a subject-task combination.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str
            Task name
        features : list of str, optional
            Features to extract. If None, uses all available features.
            
        Returns
        -------
        data_3d : ndarray
            3D array of shape (n_cycles, 150, n_features)
        feature_names : list
            Names of features in same order as last dimension
        """
        # Check cache
        cache_key = (subject, task, tuple(features) if features else None)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Filter data
        mask = (self.df[self.subject_col] == subject) & (self.df[self.task_col] == task)
        subset = self.df[mask]
        
        if len(subset) == 0:
            warnings.warn(f"No data found for subject '{subject}', task '{task}'")
            return None, []
        
        # Check data length
        n_points = len(subset)
        if n_points % self.POINTS_PER_CYCLE != 0:
            warnings.warn(f"Data length {n_points} not divisible by {self.POINTS_PER_CYCLE}")
            return None, []
        
        n_cycles = n_points // self.POINTS_PER_CYCLE
        
        # Select features
        if features is None:
            features = self.features
        
        valid_features = [f for f in features if f in subset.columns]
        if not valid_features:
            warnings.warn(f"No valid features found")
            return None, []
        
        # Extract and reshape to 3D
        feature_data = subset[valid_features].values
        data_3d = feature_data.reshape(n_cycles, self.POINTS_PER_CYCLE, len(valid_features))
        
        # Cache result
        self._cache[cache_key] = (data_3d, valid_features)
        
        return data_3d, valid_features
    
    def get_mean_patterns(self, subject: str, task: str,
                         features: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
        """
        Get mean patterns for each feature.
        
        Returns
        -------
        dict
            Dictionary mapping feature names to mean patterns (150 points)
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return {}
        
        # Calculate means
        mean_patterns = np.mean(data_3d, axis=0)  # (150, n_features)
        
        # Return as dictionary
        return {feat: mean_patterns[:, i] for i, feat in enumerate(feature_names)}
    
    def get_std_patterns(self, subject: str, task: str,
                        features: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
        """
        Get standard deviation patterns for each feature.
        
        Returns
        -------
        dict
            Dictionary mapping feature names to std patterns (150 points)
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return {}
        
        # Calculate stds
        std_patterns = np.std(data_3d, axis=0)  # (150, n_features)
        
        # Return as dictionary
        return {feat: std_patterns[:, i] for i, feat in enumerate(feature_names)}
    
    def validate_cycles(self, subject: str, task: str,
                       features: Optional[List[str]] = None) -> np.ndarray:
        """
        Validate cycles based on biomechanical constraints.
        
        Returns
        -------
        valid_mask : ndarray
            Boolean array of shape (n_cycles,) indicating valid cycles
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return np.array([])
        
        n_cycles = data_3d.shape[0]
        valid_mask = np.ones(n_cycles, dtype=bool)
        
        # Check each feature
        for i, feature in enumerate(feature_names):
            feat_data = data_3d[:, :, i]
            
            # Range checks
            if 'angle' in feature:
                # Angles are now in radians
                out_of_range = np.any((feat_data < -np.pi) | (feat_data > np.pi), axis=1)
                valid_mask &= ~out_of_range
                
                # Check for large discontinuities
                diffs = np.abs(np.diff(feat_data, axis=1))
                large_jumps = np.any(diffs > 0.5236, axis=1)  # 30 degrees = 0.5236 radians
                valid_mask &= ~large_jumps
                
            elif 'velocity' in feature:
                # Velocities in rad/s
                out_of_range = np.any(np.abs(feat_data) > 17.45, axis=1)  # 1000 deg/s = 17.45 rad/s
                valid_mask &= ~out_of_range
                
            elif 'moment' in feature:
                out_of_range = np.any(np.abs(feat_data) > 300, axis=1)
                valid_mask &= ~out_of_range
            
            # Check for NaN or inf
            has_invalid = np.any(~np.isfinite(feat_data), axis=1)
            valid_mask &= ~has_invalid
        
        return valid_mask
    
    def get_phase_correlations(self, subject: str, task: str,
                              features: Optional[List[str]] = None) -> np.ndarray:
        """
        Calculate correlation between features at each phase point.
        
        Returns
        -------
        correlations : ndarray
            Array of shape (150, n_features, n_features) with correlation matrices
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None or data_3d.shape[0] < 2:
            return None
        
        n_phases = self.POINTS_PER_CYCLE
        n_features = len(feature_names)
        correlations = np.zeros((n_phases, n_features, n_features))
        
        for phase in range(n_phases):
            phase_data = data_3d[:, phase, :]  # (n_cycles, n_features)
            correlations[phase] = np.corrcoef(phase_data.T)
        
        return correlations
    
    def find_outlier_cycles(self, subject: str, task: str,
                           features: Optional[List[str]] = None,
                           threshold: float = 2.0) -> np.ndarray:
        """
        Find outlier cycles based on deviation from mean pattern.
        
        Parameters
        ----------
        threshold : float
            Number of standard deviations for outlier threshold
            
        Returns
        -------
        outlier_indices : ndarray
            Indices of outlier cycles
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return np.array([])
        
        # Calculate mean pattern
        mean_patterns = np.mean(data_3d, axis=0)  # (150, n_features)
        
        # Calculate deviation for each cycle
        deviations = data_3d - mean_patterns[np.newaxis, :, :]
        rmse_per_cycle = np.sqrt(np.mean(deviations**2, axis=(1, 2)))
        
        # Find outliers
        outlier_threshold = np.mean(rmse_per_cycle) + threshold * np.std(rmse_per_cycle)
        outlier_indices = np.where(rmse_per_cycle > outlier_threshold)[0]
        
        return outlier_indices
    
    def get_summary_statistics(self, subject: str, task: str,
                              features: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get summary statistics for all features.
        
        Returns
        -------
        summary : DataFrame
            Summary statistics including mean, std, min, max, etc.
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return pd.DataFrame()
        
        # Reshape to (n_cycles * 150, n_features) for easier statistics
        data_2d = data_3d.reshape(-1, len(feature_names))
        
        # Calculate statistics
        stats = {
            'mean': np.mean(data_2d, axis=0),
            'std': np.std(data_2d, axis=0),
            'min': np.min(data_2d, axis=0),
            'max': np.max(data_2d, axis=0),
            'median': np.median(data_2d, axis=0),
            'q25': np.percentile(data_2d, 25, axis=0),
            'q75': np.percentile(data_2d, 75, axis=0),
        }
        
        # Create DataFrame
        summary = pd.DataFrame(stats, index=feature_names)
        summary.index.name = 'feature'
        
        return summary


def efficient_reshape_3d(df: pd.DataFrame, subject: str, task: str, features: List[str],
                        subject_col: str = 'subject', task_col: str = 'task',
                        points_per_cycle: int = 150) -> Tuple[np.ndarray, List[str]]:
    """
    Standalone function for efficient 3D reshaping.
    
    This is the core reshaping function used throughout the library.
    
    Parameters
    ----------
    df : DataFrame
        Phase-indexed locomotion data
    subject : str
        Subject ID to extract
    task : str
        Task name to extract
    features : list of str
        Features to extract
    subject_col : str
        Column name for subjects
    task_col : str
        Column name for tasks
    points_per_cycle : int
        Number of points per gait cycle (default: 150)
        
    Returns
    -------
    data_3d : ndarray or None
        3D array of shape (n_cycles, points_per_cycle, n_features)
    valid_features : list
        List of successfully extracted features
    """
    # Filter data
    mask = (df[subject_col] == subject) & (df[task_col] == task)
    subset = df[mask]
    
    if len(subset) == 0:
        return None, []
    
    # Check data length
    n_points = len(subset)
    if n_points % points_per_cycle != 0:
        warnings.warn(f"Data length {n_points} not divisible by {points_per_cycle}")
        return None, []
    
    n_cycles = n_points // points_per_cycle
    
    # Filter to valid features
    valid_features = [f for f in features if f in subset.columns]
    if not valid_features:
        return None, []
    
    # Extract all features at once
    feature_data = subset[valid_features].values  # (n_points, n_features)
    
    # Reshape to 3D
    data_3d = feature_data.reshape(n_cycles, points_per_cycle, len(valid_features))
    
    return data_3d, valid_features


# Example usage
if __name__ == '__main__':
    # Example: Load and analyze data
    import argparse
    
    parser = argparse.ArgumentParser(description='Locomotion data analysis example')
    parser.add_argument('--data', type=str, required=True, help='Path to parquet file')
    parser.add_argument('--subject', type=str, help='Subject ID to analyze')
    parser.add_argument('--task', type=str, help='Task to analyze')
    
    args = parser.parse_args()
    
    # Load data
    loco = LocomotionData(args.data)
    
    # Show available subjects and tasks
    print(f"\nAvailable subjects: {', '.join(loco.get_subjects()[:5])}...")
    print(f"Available tasks: {', '.join(loco.get_tasks())}")
    
    # Analyze specific subject/task if provided
    if args.subject and args.task:
        print(f"\nAnalyzing {args.subject} - {args.task}")
        
        # Get summary statistics
        summary = loco.get_summary_statistics(args.subject, args.task)
        print("\nSummary statistics:")
        print(summary)
        
        # Check for outliers
        outliers = loco.find_outlier_cycles(args.subject, args.task)
        print(f"\nFound {len(outliers)} outlier cycles")
        
        # Validate cycles
        valid_mask = loco.validate_cycles(args.subject, args.task)
        print(f"Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")