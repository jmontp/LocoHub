#!/usr/bin/env python3
"""
Filters by Phase Validation Plots Library

Library module for generating validation plots showing joint angle and kinetic variable ranges across movement phases.
X-axis: Phase progression (0%, 25%, 50%, 75%, 100%) with cyclical completion
Y-axis: Variable ranges with validation bounding boxes

LIBRARY FEATURES:
- Handles both kinematic (joint angles) and kinetic (forces/moments) validation
- Phase system with 0%, 25%, 50%, 75%, 100% progression and cyclical completion
- Automatic contralateral offset logic for gait-based tasks
- Task-appropriate bilateral handling (gait vs bilateral symmetric)
- Enhanced biomechanical accuracy with standard gait timing
- Support for both validation modes (kinematic/kinetic)

**ENTRY POINTS:**
This is a library module. For standalone execution, use these entry points:
- source/validation/generate_validation_plots.py - Generate validation plots
- source/tests/demo_filters_by_phase_plots.py - Interactive demonstration
- source/validation/dataset_validator_phase.py - Full validation with plots
- source/validation/dataset_validator_time.py - Time-indexed validation with plots

Generates separate plots for each task to avoid visual overcrowding.
"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, List, Tuple

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import validation offset utilities
from validation.validation_offset_utils import (
    apply_contralateral_offset_kinematic,
    apply_contralateral_offset_kinetic,
    validate_task_completeness
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
        step_colors: Optional array with shape (num_steps, num_features) containing color types for each step-feature combination:
                    - 'green': valid (no violations)
                    - 'red': local violation (violation in current feature)
                    - 'yellow': other violation (violations in other features)
                    If shape is (num_steps,), will use same color for all features of each step (backward compatibility)
        
    Returns:
        Path to the generated filters by phase plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    
    # Validate that task data is complete - fail explicitly if missing required data
    validate_task_completeness(task_data, task_name, mode)
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
                kinetic_types = ['hip_flexion_moment', 'knee_flexion_moment', 'ankle_flexion_moment']
                if 50 in task_data:
                    for kinetic_type in kinetic_types:
                        ipsi_var = f'{kinetic_type}_ipsi_Nm'
                        contra_var = f'{kinetic_type}_contra_Nm'
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
            'hip_flexion_angle': '#D3D3D3',    # Light Gray
            'knee_flexion_angle': '#D3D3D3',   # Light Gray  
            'ankle_flexion_angle': '#D3D3D3'   # Light Gray
        }
        units = 'radians'
        value_conversion = np.degrees  # Convert to degrees for display
        unit_suffix = '°'
    else:  # kinetic
        var_types = ['hip_flexion_moment', 'knee_flexion_moment', 'ankle_flexion_moment']
        colors = {
            'hip_flexion_moment': '#D3D3D3',      # Light Gray
            'knee_flexion_moment': '#D3D3D3',     # Light Gray  
            'ankle_flexion_moment': '#D3D3D3'     # Light Gray
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
                var_name = f'{var_type}_{side}_Nm'
            
            for phase in phases:
                if phase == 100:  # Skip 100% phase as it's computed from 0%
                    continue
                    
                # Data is guaranteed to exist due to validation
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
                var_name = f'{var_type}_{side}_Nm'
            
            # Extract data for this variable across phases
            phase_mins = []
            phase_maxs = []
            valid_phases = []
            
            for phase in phases:
                # Data is guaranteed to exist due to validation (except 100% which is computed from 0%)
                if phase in task_data:
                    min_val = task_data[phase][var_name]['min']
                    max_val = task_data[phase][var_name]['max']
                    phase_mins.append(min_val)
                    phase_maxs.append(max_val)
                    valid_phases.append(phase)
            
            # Plot actual data FIRST if provided (so it appears behind the filters)
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
                        ('hip_flexion_moment', 'ipsi'): 0,
                        ('hip_flexion_moment', 'contra'): 1,
                        ('knee_flexion_moment', 'ipsi'): 2,
                        ('knee_flexion_moment', 'contra'): 3,
                        ('ankle_flexion_moment', 'ipsi'): 4,
                        ('ankle_flexion_moment', 'contra'): 5
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
                        legend_added = {'red': False, 'yellow': False, 'green': False}
                        
                        for step_idx in range(feature_data.shape[0]):
                            step_data = feature_data[step_idx, :]
                            
                            # Determine color and style based on step_colors array
                            color_type = 'gray'  # Default color
                            
                            if step_colors is not None and step_idx < step_colors.shape[0]:
                                if len(step_colors.shape) == 2:
                                    # 2D array: step_colors[step_idx, feature_idx]
                                    if feature_idx < step_colors.shape[1]:
                                        color_type = step_colors[step_idx, feature_idx]
                                else:
                                    # 1D array: step_colors[step_idx] (backward compatibility)
                                    color_type = step_colors[step_idx]
                            
                            # Apply color styling with reduced alpha so filters are visible
                            if color_type == 'red':
                                color = 'red'  # Bright red for local violations
                                alpha = 0.4  # Reduced from 0.8
                                linewidth = 1.0
                                label = 'Local Violation' if not legend_added['red'] else ""
                                legend_added['red'] = True
                            elif color_type == 'yellow':
                                color = 'yellow'  # Yellow for other violations
                                alpha = 0.3  # Reduced from 0.6
                                linewidth = 0.8
                                label = 'Other Violation' if not legend_added['yellow'] else ""
                                legend_added['yellow'] = True
                            else:  # 'green' or any other value defaults to green
                                color = 'green'  # Valid steps
                                alpha = 0.2  # Reduced from 0.3
                                linewidth = 0.5
                                label = 'Valid Steps' if not legend_added['green'] else ""
                                legend_added['green'] = True
                            
                            ax.plot(phase_percent, step_data, 
                                   color=color, alpha=alpha, linewidth=linewidth, label=label)
            
            # Create bounding boxes for each phase (plotted AFTER data so they're visible)
            box_width = 8  # Width of each phase box
            for i, phase in enumerate(valid_phases):
                min_val = phase_mins[i]
                max_val = phase_maxs[i]
                
                # Create rectangle for this phase range with reduced alpha
                height = max_val - min_val
                
                rect = patches.Rectangle(
                    (phase - box_width/2, min_val), box_width, height,
                    linewidth=1, edgecolor='black', 
                    facecolor=colors[var_type], alpha=0.5  # Reduced from default 0.6
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
            
            # Plot connecting lines to show progression (on top of everything)
            ax.plot(valid_phases, phase_mins, 'o-', color='black', linewidth=2, 
                   markersize=6, alpha=0.8)  # Changed to black for visibility
            ax.plot(valid_phases, phase_maxs, 'o-', color='black', linewidth=2, 
                   markersize=6, alpha=0.8)  # Changed to black for visibility
            
            # Fill area between min and max with reduced alpha
            ax.fill_between(valid_phases, phase_mins, phase_maxs, 
                           color=colors[var_type], alpha=0.1)  # Reduced for visibility
            
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
            
            # Add legend only to the first subplot - always show all three categories
            if var_idx == 0 and side_idx == 0:
                if data is not None:
                    # Ensure all three legend categories are always present
                    from matplotlib.lines import Line2D
                    legend_elements = [
                        Line2D([0], [0], color='green', linewidth=2, alpha=0.7, label='Valid Steps'),
                        Line2D([0], [0], color='red', linewidth=2, alpha=0.8, label='Local Violation'), 
                        Line2D([0], [0], color='yellow', linewidth=2, alpha=0.6, label='Other Violation')
                    ]
                    ax.legend(handles=legend_elements, loc='upper left', fontsize=9)
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

