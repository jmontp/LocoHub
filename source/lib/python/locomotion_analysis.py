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
import matplotlib.pyplot as plt


class LocomotionData:
    """
    Main class for locomotion data analysis using efficient 3D array operations.
    """
    
    POINTS_PER_CYCLE = 150
    
    # Standard feature groups
    ANGLE_FEATURES = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad',
                      'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
    
    VELOCITY_FEATURES = ['hip_flexion_velocity_contra_rad_s', 'knee_flexion_velocity_contra_rad_s', 'ankle_flexion_velocity_contra_rad_s',
                         'hip_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_ipsi_rad_s', 'ankle_flexion_velocity_ipsi_rad_s']
    
    MOMENT_FEATURES = ['hip_flexion_moment_contra_Nm', 'knee_flexion_moment_contra_Nm', 'ankle_flexion_moment_contra_Nm',
                       'hip_flexion_moment_ipsi_Nm', 'knee_flexion_moment_ipsi_Nm', 'ankle_flexion_moment_ipsi_Nm']
    
    def __init__(self, data_path: Union[str, Path], 
                 subject_col: str = 'subject',
                 task_col: str = 'task',
                 phase_col: str = 'phase',
                 file_type: str = 'auto'):
        """
        Initialize with phase-indexed locomotion data.
        
        Parameters
        ----------
        data_path : str or Path
            Path to parquet or CSV file with phase-indexed data
        subject_col : str
            Column name for subject IDs
        task_col : str
            Column name for task names
        phase_col : str
            Column name for phase values
        file_type : str
            'parquet', 'csv', or 'auto' to detect from extension
        """
        self.data_path = Path(data_path)
        self.subject_col = subject_col
        self.task_col = task_col
        self.phase_col = phase_col
        
        # Load data based on file type
        if file_type == 'auto':
            file_type = 'parquet' if self.data_path.suffix == '.parquet' else 'csv'
        
        if file_type == 'parquet':
            self.df = pd.read_parquet(self.data_path)
        else:
            self.df = pd.read_csv(self.data_path)
        
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
    
    def merge_with_task_data(self, task_data: pd.DataFrame, 
                           join_keys: List[str] = None,
                           how: str = 'outer') -> pd.DataFrame:
        """
        Merge locomotion data with task information.
        
        Parameters
        ----------
        task_data : DataFrame
            DataFrame with task information
        join_keys : list of str
            Keys to join on. If None, uses [subject_col, task_col]
        how : str
            Type of join ('inner', 'outer', 'left', 'right')
            
        Returns
        -------
        merged_df : DataFrame
            Merged data
        """
        if join_keys is None:
            join_keys = [self.subject_col, self.task_col]
        
        # Ensure join keys exist in both dataframes
        missing_keys = set(join_keys) - set(self.df.columns)
        if missing_keys:
            raise ValueError(f"Join keys {missing_keys} not found in locomotion data")
        
        missing_keys = set(join_keys) - set(task_data.columns)
        if missing_keys:
            raise ValueError(f"Join keys {missing_keys} not found in task data")
        
        merged_df = pd.merge(self.df, task_data, on=join_keys, how=how)
        return merged_df
    
    def calculate_rom(self, subject: str, task: str, 
                     features: Optional[List[str]] = None,
                     by_cycle: bool = True) -> Dict[str, Union[float, np.ndarray]]:
        """
        Calculate Range of Motion (ROM) for features.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str
            Task name
        features : list of str, optional
            Features to calculate ROM for
        by_cycle : bool
            If True, calculate ROM per cycle. If False, overall ROM.
            
        Returns
        -------
        rom_data : dict
            ROM values for each feature
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            return {}
        
        rom_data = {}
        
        for i, feature in enumerate(feature_names):
            feat_data = data_3d[:, :, i]  # (n_cycles, 150)
            
            if by_cycle:
                # ROM per cycle
                rom_data[feature] = np.max(feat_data, axis=1) - np.min(feat_data, axis=1)
            else:
                # Overall ROM
                rom_data[feature] = np.max(feat_data) - np.min(feat_data)
        
        return rom_data
    
    def plot_time_series(self, subject: str, task: str, features: List[str],
                        time_col: str = 'time_s', save_path: Optional[str] = None):
        """
        Plot time series data for specific features.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str
            Task name
        features : list of str
            Features to plot
        time_col : str
            Column name for time data
        save_path : str, optional
            Path to save plot
        """
        # Filter data
        mask = (self.df[self.subject_col] == subject) & (self.df[self.task_col] == task)
        subset = self.df[mask]
        
        if len(subset) == 0:
            print(f"No data found for {subject} - {task}")
            return
        
        # Create subplots
        n_features = len(features)
        fig, axes = plt.subplots(n_features, 1, figsize=(12, 3*n_features), sharex=True)
        
        if n_features == 1:
            axes = [axes]
        
        for i, feature in enumerate(features):
            if feature in subset.columns and time_col in subset.columns:
                axes[i].plot(subset[time_col], subset[feature], 'b-', linewidth=1)
                axes[i].set_ylabel(feature.replace('_', ' '))
                axes[i].grid(True, alpha=0.3)
            else:
                axes[i].text(0.5, 0.5, f'Feature {feature} not found', 
                           ha='center', va='center', transform=axes[i].transAxes)
        
        axes[-1].set_xlabel('Time (s)')
        plt.title(f'{subject} - {task}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_phase_patterns(self, subject: str, task: str, features: List[str],
                           plot_type: str = 'both', save_path: Optional[str] = None):
        """
        Plot phase-normalized patterns.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str  
            Task name
        features : list of str
            Features to plot
        plot_type : str
            'mean', 'spaghetti', or 'both'
        save_path : str, optional
            Path to save plot
        """
        data_3d, feature_names = self.get_cycles(subject, task, features)
        
        if data_3d is None:
            print(f"No data found for {subject} - {task}")
            return
        
        # Get valid cycles
        valid_mask = self.validate_cycles(subject, task, features)
        
        # Create subplots
        n_features = len(feature_names)
        n_cols = min(3, n_features)
        n_rows = int(np.ceil(n_features / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        
        # Handle different subplot configurations
        if n_rows == 1 and n_cols == 1:
            axes = np.array([axes])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)
        
        phase_x = np.linspace(0, 100, self.POINTS_PER_CYCLE)
        
        for i, feature in enumerate(feature_names):
            row = i // n_cols
            col = i % n_cols
            ax = axes[row, col] if n_rows > 1 and n_cols > 1 else axes.flat[i]
            
            feat_data = data_3d[:, :, i]
            valid_data = feat_data[valid_mask, :]
            invalid_data = feat_data[~valid_mask, :]
            
            # Plot individual cycles
            if plot_type in ['spaghetti', 'both']:
                # Valid cycles in gray
                for cycle in valid_data:
                    ax.plot(phase_x, cycle, 'gray', alpha=0.3, linewidth=0.8)
                # Invalid cycles in red
                for cycle in invalid_data:
                    ax.plot(phase_x, cycle, 'red', alpha=0.5, linewidth=0.8)
            
            # Plot mean pattern
            if plot_type in ['mean', 'both'] and len(valid_data) > 0:
                mean_curve = np.mean(valid_data, axis=0)
                std_curve = np.std(valid_data, axis=0)
                
                if plot_type == 'mean':
                    ax.fill_between(phase_x, mean_curve - std_curve, 
                                   mean_curve + std_curve, alpha=0.3, color='blue')
                
                ax.plot(phase_x, mean_curve, 'blue', linewidth=2, label='Mean')
            
            ax.set_xlabel('Gait Cycle (%)')
            ax.set_ylabel(feature.replace('_', ' '))
            ax.set_title(feature, fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xlim([0, 100])
        
        # Hide empty subplots
        for i in range(n_features, n_rows * n_cols):
            axes.flat[i].set_visible(False)
        
        plt.suptitle(f'{subject} - {task} (Valid: {np.sum(valid_mask)}/{len(valid_mask)} cycles)')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_task_comparison(self, subject: str, tasks: List[str], features: List[str],
                           save_path: Optional[str] = None):
        """
        Plot comparison of mean patterns across tasks.
        
        Parameters
        ----------
        subject : str
            Subject ID
        tasks : list of str
            Tasks to compare
        features : list of str
            Features to plot
        save_path : str, optional
            Path to save plot
        """
        # Create subplots
        n_features = len(features)
        n_cols = min(3, n_features)
        n_rows = int(np.ceil(n_features / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        
        # Handle different subplot configurations
        if n_rows == 1 and n_cols == 1:
            axes = np.array([axes])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)
        
        phase_x = np.linspace(0, 100, self.POINTS_PER_CYCLE)
        colors = plt.cm.tab10(np.linspace(0, 1, len(tasks)))
        
        for i, feature in enumerate(features):
            row = i // n_cols
            col = i % n_cols
            ax = axes[row, col] if n_rows > 1 and n_cols > 1 else axes.flat[i]
            
            for j, task in enumerate(tasks):
                mean_patterns = self.get_mean_patterns(subject, task, [feature])
                if feature in mean_patterns:
                    ax.plot(phase_x, mean_patterns[feature], 
                           color=colors[j], linewidth=2, label=task)
            
            ax.set_xlabel('Gait Cycle (%)')
            ax.set_ylabel(feature.replace('_', ' '))
            ax.set_title(feature, fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xlim([0, 100])
            ax.legend()
        
        # Hide empty subplots
        for i in range(n_features, n_rows * n_cols):
            axes.flat[i].set_visible(False)
        
        plt.suptitle(f'{subject} - Task Comparison')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()


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