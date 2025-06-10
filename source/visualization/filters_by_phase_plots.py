#!/usr/bin/env python3
"""
Unified Filters by Phase Validation Plots Generator - Version 6.0

Creates validation plots showing how joint angle ranges and kinetic variables filter data across movement phases.
X-axis: Phase progression (0%, 25%, 50%, 75%, 100%) - NEW PHASE SYSTEM with cyclical completion
Y-axis: Joint angle ranges or kinetic variable ranges (with bounding boxes)

UNIFIED FEATURES:
- Single script handles both kinematic (joint angles) and kinetic (forces/moments) validation
- Updated to 0%, 25%, 50%, 75%, 100% phase system with cyclical completion
- Automatic contralateral offset logic for gait-based tasks
- Task-appropriate bilateral handling (gait vs bilateral symmetric)
- Enhanced biomechanical accuracy with standard gait timing
- Toggle between kinematic and kinetic validation modes

Generates separate plots for each task to avoid overcrowding.
"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import validation expectations parser
from validation.validation_expectations_parser import (
    parse_kinematic_validation_expectations,
    parse_kinetic_validation_expectations,
    apply_contralateral_offset_kinematic,
    apply_contralateral_offset_kinetic
)


def get_task_classification(task_name: str) -> str:
    """
    Classify tasks as either gait-based (with contralateral offset) or bilateral symmetric.
    
    Args:
        task_name: Name of the task
        
    Returns:
        Task classification: 'gait' or 'bilateral'
    """
    gait_tasks = {
        'level_walking', 'incline_walking', 'decline_walking', 
        'up_stairs', 'down_stairs', 'run'
    }
    bilateral_tasks = {
        'sit_to_stand', 'jump', 'squats'
    }
    
    if task_name in gait_tasks:
        return 'gait'
    elif task_name in bilateral_tasks:
        return 'bilateral'
    else:
        # Default to gait for unknown tasks
        return 'gait'




def classify_step_violations(data: np.ndarray, task_data: Dict, feature_map: Dict, mode: str, current_feature_idx: int) -> np.ndarray:
    """
    Classify steps based on validation violations for the current feature being plotted.
    
    Args:
        data: Array with shape (num_steps, 150, num_features)
        task_data: Validation data for specific task phases
        feature_map: Mapping of (variable_type, side) to feature indices
        mode: 'kinematic' or 'kinetic'
        current_feature_idx: Index of the feature being plotted (for local violations)
        
    Returns:
        Array with shape (num_steps,) containing color types for each step:
        - 'red': Steps with violations in the current feature (local violations)
        - 'pink': Steps with violations in other features (global violations but not local)
        - 'gray': Valid steps (no violations)
    """
    num_steps = data.shape[0]
    phases = [0, 25, 50, 75, 100]
    
    # Map phase percentages to indices in the 150-point array
    phase_indices = [int(phase * 1.5) for phase in phases]  # 0%, 25%, 50%, 75%, 100% -> indices 0, 37, 75, 112, 150
    phase_indices[-1] = 149  # Ensure last index is within bounds
    
    global_violating_steps = set()
    local_violating_steps = set()
    
    # Check each step for violations
    for step_idx in range(num_steps):
        step_violates_global = False
        step_violates_local = False
        
        # Check all features for this step
        for (var_type, side), feature_idx in feature_map.items():
            if feature_idx >= data.shape[2]:
                continue
                
            # Get variable name for validation lookup
            if mode == 'kinematic':
                var_name = f'{var_type}_{side}'
            else:  # kinetic
                var_name = f'{var_type}_{side}_Nm_kg'
            
            # Check this feature at each phase point
            for phase, phase_idx in zip(phases, phase_indices):
                if phase in task_data and var_name in task_data[phase]:
                    min_val = task_data[phase][var_name]['min']
                    max_val = task_data[phase][var_name]['max']
                    
                    # Get data value at this phase
                    data_val = data[step_idx, phase_idx, feature_idx]
                    
                    # Check if this value violates the range
                    if data_val < min_val or data_val > max_val:
                        step_violates_global = True
                        
                        # Check if this is the current feature
                        if feature_idx == current_feature_idx:
                            step_violates_local = True
        
        if step_violates_global:
            global_violating_steps.add(step_idx)
        if step_violates_local:
            local_violating_steps.add(step_idx)
    
    # Convert to color classification array
    step_colors = np.full(num_steps, 'gray', dtype='<U5')  # Default all to gray
    
    for step_idx in range(num_steps):
        if step_idx in local_violating_steps:
            step_colors[step_idx] = 'red'  # Local violations (current feature)
        elif step_idx in global_violating_steps:
            step_colors[step_idx] = 'pink'  # Global violations (other features)
    
    return step_colors


def detect_filter_violations(data: np.ndarray, task_data: Dict, feature_map: Dict, mode: str, current_feature_idx: int) -> Tuple[set, set]:
    """
    Legacy function for detecting violations. Use classify_step_violations instead for new code.
    
    Args:
        data: Numpy array with shape (num_steps, 150, num_features)
        task_data: Task validation ranges organized by phase
        feature_map: Mapping from (var_type, side) to feature index
        mode: 'kinematic' or 'kinetic'
        current_feature_idx: Index of the current feature being plotted
        
    Returns:
        Tuple of (global_violating_steps, local_violating_steps)
        - global_violating_steps: set of step indices that violate any filter
        - local_violating_steps: set of step indices that violate the current feature filter
    """
    step_colors = classify_step_violations(data, task_data, feature_map, mode, current_feature_idx)
    
    global_violating_steps = set()
    local_violating_steps = set()
    
    for step_idx, color in enumerate(step_colors):
        if color == 'red':
            local_violating_steps.add(step_idx)
            global_violating_steps.add(step_idx)
        elif color == 'pink':
            global_violating_steps.add(step_idx)
    
    return global_violating_steps, local_violating_steps


def create_filters_by_phase_plot(validation_data: Dict, task_name: str, output_dir: str, mode: str = 'kinematic', 
                                 data: np.ndarray = None, step_colors: np.ndarray = None) -> str:
    """
    Create a filters by phase plot for a specific task showing ranges across phases.
    Updated for v6.0 with unified kinematic/kinetic plotting.
    
    Args:
        validation_data: Parsed validation data
        task_name: Name of the task
        output_dir: Directory to save the plot
        mode: 'kinematic' for joint angles or 'kinetic' for forces/moments
        data: Optional numpy array with shape (num_steps, 150, num_features) containing actual data to plot
              Each feature corresponds to one plot (ordered by: hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra)
        step_colors: Optional array with shape (num_steps,) containing color types for each step:
                    - 'gray': valid steps (no violations)
                    - 'red': steps with violations in the current feature (local violations)
                    - 'pink': steps with violations in other features (global violations)
        
    Returns:
        Path to the generated filters by phase plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    phases = [0, 25, 50, 75, 100]  # Updated to include 100% for cyclical completion
    task_type = get_task_classification(task_name)
    
    # Add 100% phase data (same as 0% to show cyclical nature)
    if 0 in task_data and 100 not in task_data:
        task_data[100] = task_data[0].copy()
        
        # Apply contralateral offset logic for 100% phase in gait tasks
        if task_type == 'gait':
            if mode == 'kinematic':
                joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
                if 50 in task_data:
                    for joint_type in joint_types:
                        ipsi_joint = f'{joint_type}_ipsi'
                        contra_joint = f'{joint_type}_contra'
                        if ipsi_joint in task_data[50]:
                            task_data[100][contra_joint] = task_data[50][ipsi_joint].copy()
            elif mode == 'kinetic':
                kinetic_types = ['hip_moment', 'knee_moment', 'ankle_moment']
                if 50 in task_data:
                    for kinetic_type in kinetic_types:
                        ipsi_var = f'{kinetic_type}_ipsi_Nm_kg'
                        contra_var = f'{kinetic_type}_contra_Nm_kg'
                        if ipsi_var in task_data[50]:
                            task_data[100][contra_var] = task_data[50][ipsi_var].copy()
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    
    # Add task classification to title
    task_type_label = "Gait-Based Task (Contralateral Offset)" if task_type == 'gait' else "Bilateral Symmetric Task"
    mode_label = "Kinematic" if mode == 'kinematic' else "Kinetic"
    fig.suptitle(f'{task_name.replace("_", " ").title()} - {mode_label} Range Filters by Phase\n{task_type_label}', 
                 fontsize=16, fontweight='bold')
    
    # Define variable types and colors based on mode
    if mode == 'kinematic':
        var_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
        colors = {
            'hip_flexion_angle': '#FF6B6B',    # Red
            'knee_flexion_angle': '#4ECDC4',   # Teal  
            'ankle_flexion_angle': '#45B7D1'   # Blue
        }
        units = 'radians'
        value_conversion = np.degrees  # Convert to degrees for display
        unit_suffix = '°'
    else:  # kinetic
        var_types = ['hip_moment', 'knee_moment', 'ankle_moment']
        colors = {
            'hip_moment': '#E74C3C',      # Red
            'knee_moment': '#8E44AD',     # Purple  
            'ankle_moment': '#3498DB'     # Blue
        }
        units = 'Nm/kg'
        value_conversion = lambda x: x  # No conversion for kinetic values
        unit_suffix = ''
    
    sides = ['ipsi', 'contra']
    
    # First pass: collect all data to determine shared y-axis ranges for each variable type
    var_y_ranges = {}
    for var_idx, var_type in enumerate(var_types):
        all_mins = []
        all_maxs = []
        
        for side in sides:
            if mode == 'kinematic':
                var_name = f'{var_type}_{side}'
            else:  # kinetic
                var_name = f'{var_type}_{side}_Nm_kg'
            
            for phase in phases:
                if phase in task_data and var_name in task_data[phase]:
                    min_val = task_data[phase][var_name]['min']
                    max_val = task_data[phase][var_name]['max']
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
        
        if all_mins and all_maxs:
            # Add some padding to the range
            data_range = max(all_maxs) - min(all_mins)
            padding = data_range * 0.1  # 10% padding
            var_y_ranges[var_type] = {
                'min': min(all_mins) - padding,
                'max': max(all_maxs) + padding
            }
    
    # Second pass: create plots with shared y-axis ranges
    for var_idx, var_type in enumerate(var_types):
        for side_idx, side in enumerate(sides):
            ax = axes[var_idx, side_idx]
            
            if mode == 'kinematic':
                var_name = f'{var_type}_{side}'
            else:  # kinetic
                var_name = f'{var_type}_{side}_Nm_kg'
            
            # Extract data for this variable across phases
            phase_mins = []
            phase_maxs = []
            valid_phases = []
            
            for phase in phases:
                if phase in task_data and var_name in task_data[phase]:
                    min_val = task_data[phase][var_name]['min']
                    max_val = task_data[phase][var_name]['max']
                    phase_mins.append(min_val)
                    phase_maxs.append(max_val)
                    valid_phases.append(phase)
            
            if valid_phases:
                # Create bounding boxes for each phase
                box_width = 8  # Width of each phase box
                for i, phase in enumerate(valid_phases):
                    min_val = phase_mins[i]
                    max_val = phase_maxs[i]
                    
                    # Create rectangle for this phase range
                    height = max_val - min_val
                    
                    rect = patches.Rectangle(
                        (phase - box_width/2, min_val), box_width, height,
                        linewidth=2, edgecolor='black', 
                        facecolor=colors[var_type], alpha=0.6
                    )
                    ax.add_patch(rect)
                    
                    # Add min/max value labels
                    if mode == 'kinematic':
                        min_label = f'{value_conversion(min_val):.0f}{unit_suffix}'
                        max_label = f'{value_conversion(max_val):.0f}{unit_suffix}'
                    else:
                        min_label = f'{min_val:.1f}'
                        max_label = f'{max_val:.1f}'
                    
                    ax.text(phase, min_val - 0.05, min_label, 
                           ha='center', va='top', fontsize=8, fontweight='bold')
                    ax.text(phase, max_val + 0.05, max_label, 
                           ha='center', va='bottom', fontsize=8, fontweight='bold')
                
                # Plot connecting lines to show progression
                ax.plot(valid_phases, phase_mins, 'o-', color='darkred', linewidth=2, 
                       markersize=6, label='Min Range', alpha=0.8)
                ax.plot(valid_phases, phase_maxs, 'o-', color='darkblue', linewidth=2, 
                       markersize=6, label='Max Range', alpha=0.8)
                
                # Fill area between min and max
                ax.fill_between(valid_phases, phase_mins, phase_maxs, 
                               color=colors[var_type], alpha=0.2)
            
            # Plot actual data if provided
            if data is not None:
                # Map variable and side to feature index
                if mode == 'kinematic':
                    feature_map = {
                        ('hip_flexion_angle', 'ipsi'): 0,
                        ('hip_flexion_angle', 'contra'): 1,
                        ('knee_flexion_angle', 'ipsi'): 2,
                        ('knee_flexion_angle', 'contra'): 3,
                        ('ankle_flexion_angle', 'ipsi'): 4,
                        ('ankle_flexion_angle', 'contra'): 5
                    }
                else:  # kinetic
                    feature_map = {
                        ('hip_moment', 'ipsi'): 0,
                        ('hip_moment', 'contra'): 1,
                        ('knee_moment', 'ipsi'): 2,
                        ('knee_moment', 'contra'): 3,
                        ('ankle_moment', 'ipsi'): 4,
                        ('ankle_moment', 'contra'): 5
                    }
                
                # Get feature index for current subplot
                if (var_type, side) in feature_map:
                    feature_idx = feature_map[(var_type, side)]
                    
                    if feature_idx < data.shape[2]:
                        # Extract data for this feature across all steps
                        feature_data = data[:, :, feature_idx]  # Shape: (num_steps, 150)
                        
                        # Create phase percentage array (0 to 100%)
                        phase_percent = np.linspace(0, 100, 150)
                        
                        # Plot each step with appropriate color coding
                        legend_added = {'red': False, 'pink': False, 'gray': False}
                        
                        for step_idx in range(feature_data.shape[0]):
                            step_data = feature_data[step_idx, :]
                            
                            # Determine color and style based on step_colors array
                            if step_colors is not None and step_idx < len(step_colors):
                                color_type = step_colors[step_idx]
                                if color_type == 'red':
                                    color = 'red'  # Bright red for local violations
                                    alpha = 0.8
                                    linewidth = 1.0
                                    label = 'Local Violation' if not legend_added['red'] else ""
                                    legend_added['red'] = True
                                elif color_type == 'pink':
                                    color = 'hotpink'  # Pink for other violations
                                    alpha = 0.6
                                    linewidth = 0.8
                                    label = 'Other Violation' if not legend_added['pink'] else ""
                                    legend_added['pink'] = True
                                else:  # 'gray' or any other value defaults to gray
                                    color = 'gray'  # Valid steps
                                    alpha = 0.3
                                    linewidth = 0.5
                                    label = 'Valid Steps' if not legend_added['gray'] else ""
                                    legend_added['gray'] = True
                            else:
                                # Default to gray if no color mapping provided
                                color = 'gray'
                                alpha = 0.3
                                linewidth = 0.5
                                label = 'Valid Steps' if not legend_added['gray'] else ""
                                legend_added['gray'] = True
                            
                            ax.plot(phase_percent, step_data, 
                                   color=color, alpha=alpha, linewidth=linewidth, label=label)
                        
                        # Plot mean trajectory
                        mean_trajectory = np.mean(feature_data, axis=0)
                        ax.plot(phase_percent, mean_trajectory, 
                               color='black', linewidth=2, label='Mean Data')
            
            # Customize axes
            ax.set_xlim(-5, 105)
            ax.set_xticks(phases)
            ax.set_xticklabels([f'{p}%' for p in phases])
            
            # Update x-axis label based on task type
            x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
            ax.set_xlabel(x_label, fontsize=11)
            ax.set_ylabel(f'{var_type.replace("_", " ").title()} ({units})', fontsize=11)
            leg_title = 'Ipsilateral Leg' if side == 'ipsi' else 'Contralateral Leg'
            ax.set_title(leg_title, fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Set shared y-axis range for this variable type
            if var_type in var_y_ranges:
                y_min = var_y_ranges[var_type]['min']
                y_max = var_y_ranges[var_type]['max']
                ax.set_ylim(y_min, y_max)
            
            # Add degree labels on right axis for kinematic plots
            if mode == 'kinematic':
                ax2 = ax.twinx()
                rad_ticks = ax.get_yticks()
                deg_ticks = np.degrees(rad_ticks)
                ax2.set_yticks(rad_ticks)
                ax2.set_yticklabels([f'{deg:.0f}°' for deg in deg_ticks])
                ax2.set_ylabel(f'{var_type.replace("_", " ").title()} (degrees)', fontsize=11)
                ax2.set_ylim(ax.get_ylim())
            
            # Add legend only to the first subplot
            if var_idx == 0 and side_idx == 0:
                if data is not None:
                    ax.legend(loc='upper left', fontsize=9)
                else:
                    ax.legend(loc='upper left', fontsize=9)
    
    # Adjust layout and save
    plt.tight_layout()
    
    # Save the figure
    os.makedirs(output_dir, exist_ok=True)
    data_suffix = "_with_data" if data is not None else ""
    filename = f"{task_name}_{mode}_filters_by_phase{data_suffix}.png"
    filepath = os.path.join(output_dir, filename)
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filepath


def main():
    """Main function to generate unified filters by phase plots."""
    
    parser = argparse.ArgumentParser(
        description='Generate unified filters by phase validation plots for kinematic or kinetic data'
    )
    parser.add_argument(
        '--mode',
        type=str,
        choices=['kinematic', 'kinetic', 'both'],
        default='kinematic',
        help='Type of validation plots to generate (default: kinematic)'
    )
    # Hard-coded output directory for validation images
    validation_output_dir = 'docs/standard_spec/validation'
    parser.add_argument(
        '--kinematic-file',
        type=str,
        default='docs/standard_spec/validation_expectations_kinematic.md',
        help='Path to validation_expectations_kinematic.md file'
    )
    parser.add_argument(
        '--kinetic-file',
        type=str,
        default='docs/standard_spec/validation_expectations_kinetic.md',
        help='Path to validation_expectations_kinetic.md file'
    )
    parser.add_argument(
        '--tasks',
        type=str,
        nargs='*',
        help='Specific tasks to generate plots for (default: all tasks)'
    )
    
    args = parser.parse_args()
    
    generated_files = []
    
    # Process kinematic plots
    if args.mode in ['kinematic', 'both']:
        # Find the kinematic validation expectations file
        if os.path.exists(args.kinematic_file):
            kinematic_file = args.kinematic_file
        else:
            # Try from project root
            project_root = Path(__file__).parent.parent.parent
            kinematic_file = project_root / args.kinematic_file
            if not kinematic_file.exists():
                print(f"Error: Could not find kinematic validation file at {args.kinematic_file}")
                return 1
        
        print(f"Parsing kinematic validation expectations from: {kinematic_file}")
        
        # Parse the kinematic validation expectations
        try:
            kinematic_data = parse_kinematic_validation_expectations(str(kinematic_file))
            print(f"Successfully parsed kinematic data for {len(kinematic_data)} tasks")
            
        except Exception as e:
            print(f"Error parsing kinematic validation file: {e}")
            return 1
        
        # Determine which tasks to process for kinematic
        if args.tasks:
            tasks_to_process = [task for task in args.tasks if task in kinematic_data]
            if not tasks_to_process:
                print(f"Error: None of the specified tasks found in kinematic validation data")
                return 1
        else:
            tasks_to_process = list(kinematic_data.keys())
        
        # Generate kinematic plots for each task
        print(f"\nGenerating kinematic filters by phase plots to: {validation_output_dir}")
        
        for task_name in tasks_to_process:
            try:
                filepath = create_filters_by_phase_plot(kinematic_data, task_name, validation_output_dir, 'kinematic')
                generated_files.append(filepath)
                print(f"  - Generated: {filepath}")
                
            except Exception as e:
                print(f"Error generating kinematic plot for {task_name}: {e}")
                continue
    
    # Process kinetic plots
    if args.mode in ['kinetic', 'both']:
        # Find the kinetic validation expectations file
        if os.path.exists(args.kinetic_file):
            kinetic_file = args.kinetic_file
        else:
            # Try from project root
            project_root = Path(__file__).parent.parent.parent
            kinetic_file = project_root / args.kinetic_file
            if not kinetic_file.exists():
                print(f"Error: Could not find kinetic validation file at {args.kinetic_file}")
                return 1
        
        print(f"Parsing kinetic validation expectations from: {kinetic_file}")
        
        # Parse the kinetic validation expectations
        try:
            kinetic_data = parse_kinetic_validation_expectations(str(kinetic_file))
            print(f"Successfully parsed kinetic data for {len(kinetic_data)} tasks")
            
        except Exception as e:
            print(f"Error parsing kinetic validation file: {e}")
            return 1
        
        # Determine which tasks to process for kinetic
        if args.tasks:
            tasks_to_process = [task for task in args.tasks if task in kinetic_data]
            if not tasks_to_process:
                print(f"Error: None of the specified tasks found in kinetic validation data")
                return 1
        else:
            tasks_to_process = list(kinetic_data.keys())
        
        # Generate kinetic plots for each task
        print(f"\nGenerating kinetic filters by phase plots to: {validation_output_dir}")
        
        for task_name in tasks_to_process:
            try:
                # Apply contralateral offset if needed
                task_data_with_offset = apply_contralateral_offset_kinetic(kinetic_data[task_name], task_name)
                kinetic_data[task_name] = task_data_with_offset
                
                filepath = create_filters_by_phase_plot(kinetic_data, task_name, validation_output_dir, 'kinetic')
                generated_files.append(filepath)
                print(f"  - Generated: {filepath}")
                
            except Exception as e:
                print(f"Error generating kinetic plot for {task_name}: {e}")
                continue
    
    print(f"\n✅ Successfully generated {len(generated_files)} filters by phase plots!")
    print("\nGenerated files:")
    for filepath in generated_files:
        print(f"  - {filepath}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())