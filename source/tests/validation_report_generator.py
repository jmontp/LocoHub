#!/usr/bin/env python3
"""
Comprehensive Validation Report Generator

This script generates comprehensive validation reports that include:
1. Forward kinematic pose visualizations (reusing existing code)
2. Phase progression plots (reusing existing code) 
3. NEW: Spaghetti plots with pass/fail coloring per dataset
4. NEW: Failure analysis with task/phase debugging information

The goal is to create visual validation reports that show:
- Expected ranges (gray = pass, red = fail)
- Individual step trajectories across all subjects/trials
- Specific failure points for debugging

Usage:
    python validation_report_generator.py --dataset DATASET_NAME [--output OUTPUT_DIR]
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import existing plotting modules
try:
    from visualization.filters_by_phase_plots import parse_kinematic_validation_expectations, parse_kinetic_validation_expectations, apply_contralateral_offset_kinematic
    from visualization.forward_kinematics_plots import KinematicPoseGenerator
except ImportError as e:
    print(f"Warning: Could not import existing plotting modules: {e}")
    print("Some functionality may be limited.")

class ValidationReportGenerator:
    """
    Comprehensive validation report generator with spaghetti plots and failure analysis.
    """
    
    def __init__(self, dataset_path: str, output_dir: str = "docs/datasets_documentation"):
        """
        Initialize the validation report generator.
        
        Args:
            dataset_path: Path to the dataset parquet file
            output_dir: Directory to save validation reports (default: docs/datasets_documentation)
        """
        self.dataset_path = dataset_path
        
        # Create dataset-specific folder in dataset documentation
        dataset_name = Path(dataset_path).stem  # Extract dataset name without .parquet extension
        self.output_dir = Path(output_dir) / f"{dataset_name}_validation"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different plot types
        self.spaghetti_dir = self.output_dir / "spaghetti_plots"
        self.kinematic_dir = self.output_dir / "kinematic_poses" 
        self.progression_dir = self.output_dir / "phase_progression"
        self.reports_dir = self.output_dir / "analysis_reports"
        
        for dir_path in [self.spaghetti_dir, self.kinematic_dir, self.progression_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)
            
        # Load validation expectations
        self.kinematic_expectations = self._load_kinematic_expectations()
        self.kinetic_expectations = self._load_kinetic_expectations()
        
        # Storage for validation results
        self.validation_results = {}
        self.failure_analysis = []
        
        # Task mapping from dataset names to validation expectation names
        self.task_mapping = {
            'normal_walk': 'level_walking',
            'incline_walk': 'incline_walking', 
            'decline_walk': 'decline_walking',
            'stairs': 'up_stairs',  # Could be up or down, needs refinement
            'sit_to_stand': 'sit_to_stand',
            'jump': 'jump',
            'squats': 'squats'
        }
        
        # Variable mapping from dataset names to validation expectation names
        self.variable_mapping = {
            'hip_flexion_angle_right_rad': 'hip_flexion_angle_ipsi',
            'hip_flexion_angle_left_rad': 'hip_flexion_angle_contra',
            'knee_flexion_angle_right_rad': 'knee_flexion_angle_ipsi', 
            'knee_flexion_angle_left_rad': 'knee_flexion_angle_contra',
            'ankle_flexion_angle_right_rad': 'ankle_flexion_angle_ipsi',
            'ankle_flexion_angle_left_rad': 'ankle_flexion_angle_contra'
        }
        
    def _load_kinematic_expectations(self) -> Dict:
        """Load kinematic validation expectations from markdown file."""
        expectations_path = Path(__file__).parent.parent.parent / "docs" / "standard_spec" / "validation_expectations_kinematic.md"
        if expectations_path.exists():
            try:
                return parse_validation_expectations(str(expectations_path))
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
        """Load and prepare the dataset for validation. Only works with phase-based datasets."""
        # Check if this is a phase-based dataset according to standard spec
        if '_phase' not in str(self.dataset_path):
            print(f"ERROR: Validation reports only work with phase-based datasets.")
            print(f"Expected filename pattern: <dataset>_phase.parquet")
            print(f"Provided: {self.dataset_path}")
            print(f"Please convert to phase-based format first (150 points per gait cycle).")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(self.dataset_path)
            print(f"Loaded phase-based dataset with {len(df)} rows and {len(df.columns)} columns")
            
            # Verify phase-based structure (should have phase column)
            phase_columns = [col for col in df.columns if 'phase' in col.lower()]
            if not any(col in df.columns for col in ['phase_percent', 'phase_%', 'phase_r', 'phase_l']):
                print(f"ERROR: Phase-based dataset missing phase column.")
                print(f"Expected: 'phase_percent', 'phase_%', 'phase_r', or 'phase_l' column")
                print(f"Available columns: {list(df.columns)[:10]}...")
                print(f"Found phase-related columns: {phase_columns}")
                return pd.DataFrame()
            
            # Verify step structure (each step should have ~150 points)
            if 'step' in df.columns or 'cycle' in df.columns:
                step_col = 'step' if 'step' in df.columns else 'cycle'
                step_sizes = df.groupby(['subject', 'task', step_col]).size()
                expected_size = 150
                if not step_sizes.between(140, 160).all():  # Allow some tolerance
                    print(f"WARNING: Some steps don't have ~150 points as expected for phase data")
                    print(f"Step sizes range: {step_sizes.min()} to {step_sizes.max()}")
            
            return df
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return pd.DataFrame()
    
    def _calculate_phase_from_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate phase percentage from time data for cyclic tasks.
        Properly identifies individual steps/cycles and reshapes each to 150 points.
        """
        df = df.copy()
        
        # Check if we can identify individual steps/cycles
        if 'step' in df.columns or 'cycle' in df.columns:
            # Use existing step/cycle information
            step_col = 'step' if 'step' in df.columns else 'cycle'
            
            def calc_phase_for_step(group):
                # Each step/cycle gets reshaped to 150 points (0-100%)
                group = group.sort_values('time')
                group['phase_percent'] = np.linspace(0, 100, len(group))
                return group
            
            group_cols = ['subject', 'task', step_col] if 'subject' in df.columns else ['task', step_col]
            df = df.groupby(group_cols).apply(calc_phase_for_step, include_groups=False).reset_index()
            
        elif 'subject' in df.columns and 'task' in df.columns:
            # Try to detect steps from force data or other cyclic patterns
            def detect_and_phase_steps(group):
                group = group.sort_values('time').copy()
                
                # Simple step detection: assume consistent time intervals represent steps
                # For GTech data, assume ~150 points per step (common sampling)
                total_points = len(group)
                estimated_steps = max(1, total_points // 150)
                
                # Create artificial step boundaries
                step_size = total_points // estimated_steps
                steps = []
                
                for i in range(estimated_steps):
                    start_idx = i * step_size
                    end_idx = (i + 1) * step_size if i < estimated_steps - 1 else total_points
                    
                    step_data = group.iloc[start_idx:end_idx].copy()
                    step_data['step'] = i + 1
                    step_data['phase_percent'] = np.linspace(0, 100, len(step_data))
                    steps.append(step_data)
                
                return pd.concat(steps, ignore_index=True)
            
            df = df.groupby(['subject', 'task']).apply(detect_and_phase_steps, include_groups=False).reset_index()
            
        else:
            # Fallback: treat entire dataset as single cycle
            df = df.sort_values('time')
            df['phase_percent'] = np.linspace(0, 100, len(df))
        
        return df
    
    def validate_step(self, row: pd.Series, task: str, variable: str, expected_range: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate a single step against expected ranges.
        
        Args:
            row: Data row containing step information
            task: Task name
            variable: Variable name to validate
            expected_range: Dictionary with 'min' and 'max' values
            
        Returns:
            Tuple of (is_valid, failure_reason)
        """
        if variable not in row:
            return False, f"Variable {variable} not found in data"
        
        value = row[variable]
        if pd.isna(value):
            return False, f"Variable {variable} is NaN"
        
        min_val = expected_range['min']
        max_val = expected_range['max']
        
        if value < min_val:
            return False, f"Value {value:.3f} below minimum {min_val:.3f}"
        elif value > max_val:
            return False, f"Value {value:.3f} above maximum {max_val:.3f}"
        else:
            return True, "Valid"
    
    def generate_validation_plot_with_spaghetti(self, df: pd.DataFrame, dataset_task: str, 
                                               expectations: Dict, plot_type: str = "kinematic") -> str:
        """
        Generate validation expectation plot with spaghetti traces overlayed (like existing validation plots).
        
        Args:
            df: Dataset DataFrame
            dataset_task: Task name as it appears in the dataset
            expectations: Validation expectations dictionary
            plot_type: Either "kinematic" or "kinetic"
            
        Returns:
            Path to saved plot file
        """
        # Map dataset task to validation task
        validation_task = self.task_mapping.get(dataset_task, dataset_task)
        
        if validation_task not in expectations:
            print(f"Warning: No validation expectations found for task {validation_task}")
            return ""
        
        # Filter data for this task
        task_data = df[df['task_name'] == dataset_task].copy() if 'task_name' in df.columns else df.copy()
        
        if task_data.empty:
            print(f"Warning: No data found for task {dataset_task}")
            return ""
        
        # Get phase values
        if 'phase_percent' in task_data.columns:
            phase_col = 'phase_percent'
        elif 'phase_%' in task_data.columns:
            phase_col = 'phase_%'
        elif 'phase_l' in task_data.columns:
            phase_col = 'phase_l'
        elif 'phase_r' in task_data.columns:
            phase_col = 'phase_r'
        else:
            print(f"Warning: No phase column found for {dataset_task}")
            return ""
        
        # Create figure with subplots like existing validation plots (6 subplots: 3 joints x 2 legs)
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{dataset_task.replace("_", " ").title()} - Validation with Dataset Traces', fontsize=16)
        
        joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
        leg_types = ['ipsi', 'contra']
        phases = [0, 25, 50, 75, 100]
        
        for row, leg in enumerate(leg_types):
            for col, joint in enumerate(joint_types):
                ax = axes[row, col]
                validation_variable = f"{joint}_{leg}"
                
                # Find corresponding dataset variable
                dataset_variable = None
                for dataset_var, val_var in self.variable_mapping.items():
                    if val_var == validation_variable:
                        dataset_variable = dataset_var
                        break
                
                if dataset_variable is None or dataset_variable not in task_data.columns:
                    ax.text(0.5, 0.5, f'No data for\\n{validation_variable}', 
                           ha='center', va='center', transform=ax.transAxes)
                    ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                    continue
                
                # Plot validation expectation boxes (thinner/more transparent)
                for phase in phases:
                    if phase in expectations[validation_task]:
                        if validation_variable in expectations[validation_task][phase]:
                            exp_range = expectations[validation_task][phase][validation_variable]
                            min_val = exp_range['min']
                            max_val = exp_range['max']
                            
                            # Create thinner validation box
                            rect = patches.Rectangle((phase-2, min_val), 4, max_val-min_val,
                                                   linewidth=1, edgecolor='blue', 
                                                   facecolor='lightblue', alpha=0.3)
                            ax.add_patch(rect)
                            
                            # Add min/max lines
                            ax.plot([phase-2, phase+2], [min_val, min_val], 'b-', linewidth=2)
                            ax.plot([phase-2, phase+2], [max_val, max_val], 'b-', linewidth=2)
                
                # Group data by individual steps for spaghetti traces
                group_cols = []
                if 'subject' in task_data.columns:
                    group_cols.append('subject')
                if 'step' in task_data.columns:
                    group_cols.append('step')
                elif 'trial' in task_data.columns:
                    group_cols.append('trial')
                
                if not group_cols:
                    # Create artificial step grouping if no step info available
                    task_data['group_id'] = task_data.index // 150
                    group_cols = ['group_id']
                
                # Plot spaghetti traces
                for group_name, group_data in task_data.groupby(group_cols):
                    if dataset_variable not in group_data.columns:
                        continue
                    
                    group_data = group_data.sort_values(phase_col)
                    phases_data = group_data[phase_col].values
                    values_data = group_data[dataset_variable].values
                    
                    # Validate trajectory
                    trajectory_valid = True
                    for idx, (phase_val, value) in enumerate(zip(phases_data, values_data)):
                        closest_phase = min(phases, key=lambda x: abs(x - phase_val))
                        if closest_phase in expectations[validation_task]:
                            if validation_variable in expectations[validation_task][closest_phase]:
                                exp_range = expectations[validation_task][closest_phase][validation_variable]
                                if value < exp_range['min'] or value > exp_range['max']:
                                    trajectory_valid = False
                                    # Record failure
                                    self.failure_analysis.append({
                                        'task': dataset_task,
                                        'validation_task': validation_task,
                                        'variable': validation_variable,
                                        'dataset_variable': dataset_variable,
                                        'phase': phase_val,
                                        'value': value,
                                        'subject': group_name[0] if isinstance(group_name, tuple) else group_name,
                                        'trial': group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else 'N/A',
                                        'expected_min': exp_range['min'],
                                        'expected_max': exp_range['max']
                                    })
                    
                    # Plot trajectory with appropriate color
                    color = 'gray' if trajectory_valid else 'red'
                    alpha = 0.3 if trajectory_valid else 0.6
                    linewidth = 0.5 if trajectory_valid else 0.8
                    ax.plot(phases_data, values_data, color=color, alpha=alpha, linewidth=linewidth)
                
                # Formatting
                ax.set_xlim(-5, 105)
                ax.set_xlabel('Phase (%)')
                ax.set_ylabel(f'{joint.replace("_", " ").title()} (rad)')
                ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                ax.grid(True, alpha=0.3)
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='gray', alpha=0.6, label='Valid trajectories'),
            Line2D([0], [0], color='red', alpha=0.6, label='Invalid trajectories'),
            patches.Patch(facecolor='lightblue', alpha=0.3, label='Validation ranges')
        ]
        fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"{dataset_task}_validation_with_spaghetti.png"
        plot_path = self.spaghetti_dir / plot_filename
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
    
    def _get_units(self, variable: str) -> str:
        """Get units for a variable based on naming convention."""
        if '_rad' in variable:
            return 'rad'
        elif '_Nm' in variable:
            return 'Nm'
        elif '_N' in variable:
            return 'N'
        elif '_m' in variable:
            return 'm'
        else:
            return 'units'
    
    def generate_forward_kinematic_plots(self, df: pd.DataFrame, dataset_task: str, validation_task: str) -> List[str]:
        """
        Generate forward kinematic pose plots for a task using actual dataset data.
        
        Args:
            df: Dataset DataFrame
            dataset_task: Task name as it appears in the dataset
            validation_task: Task name for validation expectations
            
        Returns:
            List of paths to generated plot files
        """
        plot_paths = []
        
        if validation_task not in self.kinematic_expectations:
            print(f"Warning: No kinematic expectations found for task {validation_task}")
            return plot_paths
        
        # Filter data for this task
        task_data = df[df['task_name'] == dataset_task].copy() if 'task_name' in df.columns else df.copy()
        
        if task_data.empty:
            print(f"Warning: No data found for task {dataset_task}")
            return plot_paths
        
        # Get phase column
        phase_col = None
        for col in ['phase_l', 'phase_r', 'phase_percent', 'phase_%']:
            if col in task_data.columns:
                phase_col = col
                break
        
        if phase_col is None:
            print(f"Warning: No phase column found for {dataset_task}")
            return plot_paths
        
        try:
            # Generate poses for each phase
            for phase in [0, 25, 50, 75]:
                if phase in self.kinematic_expectations[validation_task]:
                    plot_path = self.kinematic_dir / f"{dataset_task}_phase_{phase:02d}_kinematic.png"
                    
                    # Get data near this phase (within ±2.5%)
                    phase_data = task_data[
                        (task_data[phase_col] >= phase - 2.5) & 
                        (task_data[phase_col] <= phase + 2.5)
                    ]
                    
                    if not phase_data.empty:
                        # Extract actual joint angles from dataset
                        joint_angles = {}
                        
                        # Get right leg angles (ipsilateral)
                        if 'hip_flexion_angle_right_rad' in phase_data.columns:
                            joint_angles['hip_flexion'] = phase_data['hip_flexion_angle_right_rad'].mean()
                        if 'knee_flexion_angle_right_rad' in phase_data.columns:
                            joint_angles['knee_flexion'] = phase_data['knee_flexion_angle_right_rad'].mean()
                        if 'ankle_flexion_angle_right_rad' in phase_data.columns:
                            joint_angles['ankle_flexion'] = phase_data['ankle_flexion_angle_right_rad'].mean()
                        
                        # Generate simple stick figure plot
                        self._generate_stick_figure_plot(joint_angles, dataset_task, phase, str(plot_path))
                        plot_paths.append(str(plot_path))
                            
        except Exception as e:
            print(f"Error generating kinematic plots for {dataset_task}: {e}")
            
        return plot_paths
    
    def _generate_stick_figure_plot(self, joint_angles: Dict[str, float], task: str, phase: int, plot_path: str):
        """
        Generate a simple stick figure plot showing joint poses.
        
        Args:
            joint_angles: Dictionary of joint angles in radians
            task: Task name
            phase: Phase percentage
            plot_path: Path to save the plot
        """
        import matplotlib.pyplot as plt
        import numpy as np
        
        fig, ax = plt.subplots(1, 1, figsize=(8, 10))
        
        # Define segment lengths (normalized)
        thigh_length = 0.4
        shank_length = 0.4
        foot_length = 0.15
        
        # Hip is at origin
        hip_x, hip_y = 0, 0
        
        # Get joint angles with defaults
        hip_angle = joint_angles.get('hip_flexion', 0.0)
        knee_angle = joint_angles.get('knee_flexion', 0.0)
        ankle_angle = joint_angles.get('ankle_flexion', 0.0)
        
        # Calculate knee position
        knee_x = hip_x + thigh_length * np.sin(hip_angle)
        knee_y = hip_y - thigh_length * np.cos(hip_angle)
        
        # Calculate ankle position (knee angle is relative to thigh)
        shank_angle = hip_angle + knee_angle
        ankle_x = knee_x + shank_length * np.sin(shank_angle)
        ankle_y = knee_y - shank_length * np.cos(shank_angle)
        
        # Calculate toe position (ankle angle is relative to shank)
        foot_angle = shank_angle + ankle_angle
        toe_x = ankle_x + foot_length * np.cos(foot_angle)
        toe_y = ankle_y + foot_length * np.sin(foot_angle)
        
        # Plot segments
        ax.plot([hip_x, knee_x], [hip_y, knee_y], 'b-', linewidth=4, label='Thigh')
        ax.plot([knee_x, ankle_x], [knee_y, ankle_y], 'r-', linewidth=4, label='Shank')
        ax.plot([ankle_x, toe_x], [ankle_y, toe_y], 'g-', linewidth=4, label='Foot')
        
        # Plot joints
        ax.plot(hip_x, hip_y, 'ko', markersize=8, label='Hip')
        ax.plot(knee_x, knee_y, 'ko', markersize=8, label='Knee')
        ax.plot(ankle_x, ankle_y, 'ko', markersize=8, label='Ankle')
        
        # Add ground line
        ax.axhline(y=-0.9, color='brown', linewidth=3, alpha=0.7, label='Ground')
        
        # Formatting
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(-1.0, 0.2)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Horizontal Position (normalized)')
        ax.set_ylabel('Vertical Position (normalized)')
        ax.set_title(f'{task.replace("_", " ").title()} - Phase {phase}%\\n'
                    f'Hip: {np.degrees(hip_angle):.1f}°, Knee: {np.degrees(knee_angle):.1f}°, Ankle: {np.degrees(ankle_angle):.1f}°')
        
        # Add text with angle values
        textstr = f'Joint Angles:\\nHip: {np.degrees(hip_angle):.1f}°\\nKnee: {np.degrees(knee_angle):.1f}°\\nAnkle: {np.degrees(ankle_angle):.1f}°'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_phase_progression_plots(self, df: pd.DataFrame, dataset_task: str, validation_task: str) -> List[str]:
        """
        Generate phase progression plots for a task using actual dataset data.
        
        Args:
            df: Dataset DataFrame
            dataset_task: Task name as it appears in the dataset
            validation_task: Task name for validation expectations
            
        Returns:
            List of paths to generated plot files
        """
        plot_paths = []
        
        # Filter data for this task
        task_data = df[df['task_name'] == dataset_task].copy() if 'task_name' in df.columns else df.copy()
        
        if task_data.empty:
            print(f"Warning: No data found for task {dataset_task}")
            return plot_paths
        
        # Get phase column
        phase_col = None
        for col in ['phase_l', 'phase_r', 'phase_percent', 'phase_%']:
            if col in task_data.columns:
                phase_col = col
                break
        
        if phase_col is None:
            print(f"Warning: No phase column found for {dataset_task}")
            return plot_paths
        
        # Generate kinematic phase progression
        try:
            kinematic_plot_path = self.progression_dir / f"{dataset_task}_kinematic_progression.png"
            self._generate_kinematic_progression_plot(task_data, dataset_task, validation_task, phase_col, str(kinematic_plot_path))
            plot_paths.append(str(kinematic_plot_path))
        except Exception as e:
            print(f"Error generating kinematic progression plot for {dataset_task}: {e}")
        
        # Generate kinetic phase progression  
        try:
            kinetic_plot_path = self.progression_dir / f"{dataset_task}_kinetic_progression.png"
            self._generate_kinetic_progression_plot(task_data, dataset_task, validation_task, phase_col, str(kinetic_plot_path))
            plot_paths.append(str(kinetic_plot_path))
        except Exception as e:
            print(f"Error generating kinetic progression plot for {dataset_task}: {e}")
            
        return plot_paths
    
    def _generate_kinematic_progression_plot(self, task_data: pd.DataFrame, dataset_task: str, validation_task: str, phase_col: str, plot_path: str):
        """Generate kinematic phase progression plot with dataset traces and validation ranges."""
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{dataset_task.replace("_", " ").title()} - Kinematic Phase Progression', fontsize=16)
        
        joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
        leg_types = ['ipsi', 'contra']
        phases = [0, 25, 50, 75, 100]
        
        for row, leg in enumerate(leg_types):
            for col, joint in enumerate(joint_types):
                ax = axes[row, col]
                validation_variable = f"{joint}_{leg}"
                
                # Find corresponding dataset variable
                dataset_variable = None
                for dataset_var, val_var in self.variable_mapping.items():
                    if val_var == validation_variable:
                        dataset_variable = dataset_var
                        break
                
                if dataset_variable is None or dataset_variable not in task_data.columns:
                    ax.text(0.5, 0.5, f'No data for\\n{validation_variable}', 
                           ha='center', va='center', transform=ax.transAxes)
                    ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                    continue
                
                # Plot validation expectation boxes
                if validation_task in self.kinematic_expectations:
                    for phase in phases:
                        if phase in self.kinematic_expectations[validation_task]:
                            if validation_variable in self.kinematic_expectations[validation_task][phase]:
                                exp_range = self.kinematic_expectations[validation_task][phase][validation_variable]
                                min_val = exp_range['min']
                                max_val = exp_range['max']
                                
                                # Create validation box
                                rect = patches.Rectangle((phase-2, min_val), 4, max_val-min_val,
                                                       linewidth=1, edgecolor='blue', 
                                                       facecolor='lightblue', alpha=0.3)
                                ax.add_patch(rect)
                
                # Plot dataset traces (sample some trajectories to avoid overcrowding)
                group_cols = []
                if 'subject_id' in task_data.columns:
                    group_cols.append('subject_id')
                if 'step_number' in task_data.columns:
                    group_cols.append('step_number')
                elif 'trial' in task_data.columns:
                    group_cols.append('trial')
                
                if not group_cols:
                    # Create artificial step grouping if no step info available
                    task_data_copy = task_data.copy()
                    task_data_copy['group_id'] = task_data_copy.index // 150
                    group_cols = ['group_id']
                    grouped_data = task_data_copy
                else:
                    grouped_data = task_data
                
                # Sample every 10th trajectory to avoid overcrowding
                trajectory_count = 0
                for group_name, group_data in grouped_data.groupby(group_cols):
                    if trajectory_count % 10 != 0:  # Sample every 10th
                        trajectory_count += 1
                        continue
                    
                    if dataset_variable not in group_data.columns:
                        continue
                    
                    group_data = group_data.sort_values(phase_col)
                    phases_data = group_data[phase_col].values
                    values_data = group_data[dataset_variable].values
                    
                    ax.plot(phases_data, values_data, color='gray', alpha=0.2, linewidth=0.5)
                    trajectory_count += 1
                    
                    if trajectory_count > 100:  # Limit total trajectories
                        break
                
                # Plot mean trajectory
                mean_data = task_data.groupby(phase_col)[dataset_variable].mean()
                ax.plot(mean_data.index, mean_data.values, 'red', linewidth=2, label='Mean')
                
                # Formatting
                ax.set_xlim(-5, 105)
                ax.set_xlabel('Phase (%)')
                ax.set_ylabel(f'{joint.replace("_", " ").title()} (rad)')
                ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                ax.grid(True, alpha=0.3)
                ax.legend()
        
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_kinetic_progression_plot(self, task_data: pd.DataFrame, dataset_task: str, validation_task: str, phase_col: str, plot_path: str):
        """Generate kinetic phase progression plot with dataset traces."""
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{dataset_task.replace("_", " ").title()} - Kinetic Phase Progression', fontsize=16)
        
        joint_types = ['hip_flexion_moment', 'knee_flexion_moment', 'ankle_flexion_moment']
        leg_types = ['right', 'left']
        
        for row, leg in enumerate(leg_types):
            for col, joint in enumerate(joint_types):
                ax = axes[row, col]
                dataset_variable = f"{joint}_{leg}_Nm"
                
                if dataset_variable not in task_data.columns:
                    ax.text(0.5, 0.5, f'No data for\\n{dataset_variable}', 
                           ha='center', va='center', transform=ax.transAxes)
                    ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                    continue
                
                # Plot dataset traces (sample some trajectories)
                group_cols = []
                if 'subject_id' in task_data.columns:
                    group_cols.append('subject_id')
                if 'step_number' in task_data.columns:
                    group_cols.append('step_number')
                elif 'trial' in task_data.columns:
                    group_cols.append('trial')
                
                if not group_cols:
                    # Create artificial step grouping
                    task_data_copy = task_data.copy()
                    task_data_copy['group_id'] = task_data_copy.index // 150
                    group_cols = ['group_id']
                    grouped_data = task_data_copy
                else:
                    grouped_data = task_data
                
                # Sample every 10th trajectory
                trajectory_count = 0
                for group_name, group_data in grouped_data.groupby(group_cols):
                    if trajectory_count % 10 != 0:  # Sample every 10th
                        trajectory_count += 1
                        continue
                    
                    group_data = group_data.sort_values(phase_col)
                    phases_data = group_data[phase_col].values
                    values_data = group_data[dataset_variable].values
                    
                    ax.plot(phases_data, values_data, color='blue', alpha=0.2, linewidth=0.5)
                    trajectory_count += 1
                    
                    if trajectory_count > 100:  # Limit total trajectories
                        break
                
                # Plot mean trajectory
                mean_data = task_data.groupby(phase_col)[dataset_variable].mean()
                ax.plot(mean_data.index, mean_data.values, 'red', linewidth=2, label='Mean')
                
                # Formatting
                ax.set_xlim(-5, 105)
                ax.set_xlabel('Phase (%)')
                ax.set_ylabel(f'{joint.replace("_", " ").title()} (Nm)')
                ax.set_title(f'{joint.replace("_", " ").title()} ({leg.title()})')
                ax.grid(True, alpha=0.3)
                ax.legend()
        
        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_failure_analysis_report(self) -> str:
        """
        Generate a detailed failure analysis report with debugging information.
        
        Returns:
            Path to the generated report file
        """
        report_path = self.reports_dir / "failure_analysis.md"
        
        with open(report_path, 'w') as f:
            f.write("# Validation Failure Analysis Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Dataset**: {self.dataset_path}\n\n")
            
            if not self.failure_analysis:
                f.write("## ✅ No Validation Failures Found\n\n")
                f.write("All data points passed validation against expected ranges.\n")
                return str(report_path)
            
            f.write(f"## 🚨 Validation Failures Summary\n\n")
            f.write(f"**Total Failures**: {len(self.failure_analysis)}\n\n")
            
            # Group failures by task
            failures_by_task = {}
            for failure in self.failure_analysis:
                task = failure['task']
                if task not in failures_by_task:
                    failures_by_task[task] = []
                failures_by_task[task].append(failure)
            
            for task, failures in failures_by_task.items():
                f.write(f"### Task: {task.replace('_', ' ').title()}\n\n")
                f.write(f"**Failures in this task**: {len(failures)}\n\n")
                
                # Group by variable
                failures_by_var = {}
                for failure in failures:
                    var = failure['variable']
                    if var not in failures_by_var:
                        failures_by_var[var] = []
                    failures_by_var[var].append(failure)
                
                for variable, var_failures in failures_by_var.items():
                    f.write(f"#### Variable: {variable}\n\n")
                    f.write(f"**Failures**: {len(var_failures)}\n\n")
                    
                    # Create failure details table
                    f.write("| Subject | Trial | Phase | Value | Expected Min | Expected Max | Issue |\n")
                    f.write("|---------|-------|-------|-------|--------------|--------------|-------|\n")
                    
                    for failure in var_failures[:10]:  # Limit to first 10 for readability
                        issue = "Below min" if failure['value'] < failure['expected_min'] else "Above max"
                        f.write(f"| {failure['subject']} | {failure['trial']} | {failure['phase']:.1f}% | "
                               f"{failure['value']:.3f} | {failure['expected_min']:.3f} | "
                               f"{failure['expected_max']:.3f} | {issue} |\n")
                    
                    if len(var_failures) > 10:
                        f.write(f"\n*... and {len(var_failures) - 10} more failures*\n")
                    
                    f.write("\n")
                
            f.write("\n## 🔧 Debugging Recommendations\n\n")
            f.write("1. **Check data collection protocols** for tasks with high failure rates\n")
            f.write("2. **Verify sensor calibration** for variables consistently out of range\n") 
            f.write("3. **Review subject instructions** for tasks with biomechanical implausibilities\n")
            f.write("4. **Consider updating validation ranges** if failures represent normal variation\n")
            
        return str(report_path)
    
    def generate_comprehensive_report(self, tasks: Optional[List[str]] = None) -> str:
        """
        Generate a comprehensive validation report for specified tasks.
        
        Args:
            tasks: List of task names to include. If None, includes all available tasks.
            
        Returns:
            Path to the main report file
        """
        # Load dataset
        df = self.load_dataset()
        if df.empty:
            print("Error: Could not load dataset")
            return ""
        
        # Determine tasks to analyze
        if tasks is None:
            available_tasks = df['task_name'].unique() if 'task_name' in df.columns else ['unknown_task']
            # Map dataset tasks to validation tasks and filter for those with expectations
            tasks = []
            for dataset_task in available_tasks:
                validation_task = self.task_mapping.get(dataset_task, dataset_task)
                if validation_task in self.kinematic_expectations:
                    tasks.append(dataset_task)
        
        # Clear previous failure analysis
        self.failure_analysis = []
        
        # Generate plots for each task
        task_reports = {}
        
        for dataset_task in tasks:
            print(f"Processing task: {dataset_task}")
            validation_task = self.task_mapping.get(dataset_task, dataset_task)
            
            task_reports[dataset_task] = {
                'spaghetti_plots': [],
                'kinematic_poses': [],
                'progression_plots': []
            }
            
            # Generate validation plots with spaghetti overlays for kinematic variables
            if validation_task in self.kinematic_expectations:
                spaghetti_path = self.generate_validation_plot_with_spaghetti(
                    df, dataset_task, self.kinematic_expectations, "kinematic"
                )
                if spaghetti_path:
                    task_reports[dataset_task]['spaghetti_plots'].append(spaghetti_path)
            
            # Generate validation plots with spaghetti overlays for kinetic variables (if available)
            if validation_task in self.kinetic_expectations:
                kinetic_spaghetti_path = self.generate_validation_plot_with_spaghetti(
                    df, dataset_task, self.kinetic_expectations, "kinetic"
                )
                if kinetic_spaghetti_path:
                    task_reports[dataset_task]['spaghetti_plots'].append(kinetic_spaghetti_path)
            
            # Generate forward kinematic plots with actual dataset data
            kinematic_paths = self.generate_forward_kinematic_plots(df, dataset_task, validation_task)
            task_reports[dataset_task]['kinematic_poses'].extend(kinematic_paths)
            
            # Generate phase progression plots with actual dataset data
            progression_paths = self.generate_phase_progression_plots(df, dataset_task, validation_task)
            task_reports[dataset_task]['progression_plots'].extend(progression_paths)
        
        # Generate failure analysis report
        failure_report_path = self.generate_failure_analysis_report()
        
        # Generate main Markdown report
        main_report_path = self.output_dir / "validation_report.md"
        self._generate_markdown_report(main_report_path, task_reports, failure_report_path)
        
        print(f"\n✅ Comprehensive validation report generated: {main_report_path}")
        print(f"📊 Failure analysis report: {failure_report_path}")
        print(f"📁 Plot directories: {self.spaghetti_dir}, {self.kinematic_dir}, {self.progression_dir}")
        
        return str(main_report_path)
    
    def _generate_markdown_report(self, report_path: Path, task_reports: Dict, failure_report_path: str):
        """Generate a Markdown report with embedded plots and analysis."""
        with open(report_path, 'w') as f:
            f.write("# Locomotion Data Validation Report\n\n")
            
            # Summary section
            f.write("## Summary\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Dataset:** `{self.dataset_path}`\n\n")
            f.write(f"**Total Validation Failures:** {len(self.failure_analysis)}\n\n")
            f.write(f"**Tasks Analyzed:** {len(task_reports)}\n\n")
            
            # Table of contents
            f.write("## Tasks\n\n")
            for task in task_reports.keys():
                task_title = task.replace('_', ' ').title()
                f.write(f"- [{task_title}](#{task.replace('_', '-')})\n")
            f.write("\n")
            
            # Task sections
            for task, reports in task_reports.items():
                task_title = task.replace('_', ' ').title()
                f.write(f"## {task_title}\n\n")
                
                # Task statistics
                task_failures = [f for f in self.failure_analysis if f['task'] == task]
                f.write(f"**Validation Failures:** {len(task_failures)}\n\n")
                
                # Skip separate spaghetti plots - they're now integrated into phase progression
                
                # Forward kinematic plots
                if reports['kinematic_poses']:
                    f.write("### Forward Kinematic Poses\n\n")
                    for plot_path in reports['kinematic_poses']:
                        plot_name = Path(plot_path).name
                        relative_path = Path(plot_path).relative_to(self.output_dir)
                        f.write(f"![{plot_name}]({relative_path})\n\n")
                
                # Phase progression plots
                if reports['progression_plots']:
                    f.write("### Phase Progression Analysis\n\n")
                    for plot_path in reports['progression_plots']:
                        plot_name = Path(plot_path).name
                        relative_path = Path(plot_path).relative_to(self.output_dir)
                        f.write(f"![{plot_name}]({relative_path})\n\n")
            
            f.write(f"## Detailed Failure Analysis\n\n")
            relative_failure_path = Path(failure_report_path).relative_to(self.output_dir)
            f.write(f"For detailed failure analysis, see: [{Path(failure_report_path).name}]({relative_failure_path})\n\n")


def main():
    """Main function to run the validation report generator."""
    parser = argparse.ArgumentParser(description="Generate comprehensive validation reports")
    parser.add_argument("--dataset", required=True, help="Path to dataset parquet file")
    parser.add_argument("--output", default="docs/datasets_documentation", help="Output directory for reports")
    parser.add_argument("--tasks", nargs="*", help="Specific tasks to analyze (default: all)")
    
    args = parser.parse_args()
    
    # Create report generator
    generator = ValidationReportGenerator(args.dataset, args.output)
    
    # Generate comprehensive report
    report_path = generator.generate_comprehensive_report(args.tasks)
    
    if report_path:
        print(f"\n🎉 Validation report completed successfully!")
        print(f"📄 Main report: {report_path}")
    else:
        print("❌ Failed to generate validation report")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())