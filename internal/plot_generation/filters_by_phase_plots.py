"""
Filters by phase plotting for validation reports - Version 2.
This version implements pass/fail separation for clearer violation visibility.
"""

from typing import Dict, List, Optional
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import warnings

# Removed: validate_task_completeness (no longer needed in unified system)


def get_task_classification(task_name: str) -> str:
    """
    Classify task as 'gait' or 'bilateral' based on name.
    
    Args:
        task_name: Name of the task
        
    Returns:
        'gait' for walking/running/stairs tasks, 'bilateral' for others
    """
    gait_keywords = ['walk', 'run', 'stairs', 'gait', 'stair']
    task_lower = task_name.lower()
    
    for keyword in gait_keywords:
        if keyword in task_lower:
            return 'gait'
    
    return 'bilateral'


def create_filters_by_phase_plot(
    validation_data: Dict, 
    task_name: str, 
    output_dir: str, 
    mode: str = 'kinematic',
    data: Optional[np.ndarray] = None, 
    violations: Optional[Dict[str, List[int]]] = None,
    failing_features: Optional[Dict[int, List[str]]] = None,
    dataset_name: Optional[str] = None, 
    timestamp: Optional[str] = None
) -> str:
    """
    Create a filters by phase plot with pass/fail separation.
    
    Args:
        validation_data: Parsed validation data with ranges
        task_name: Name of the task
        output_dir: Directory to save the plot
        mode: 'kinematic' or 'kinetic'
        data: Optional numpy array with shape (num_strides, 150, num_features)
        violations: DEPRECATED - Optional dict mapping variable names to lists of failed stride indices
        failing_features: NEW - Dict mapping stride indices to lists of failed variable names
        dataset_name: Optional dataset name to display
        timestamp: Optional timestamp to display
        
    Returns:
        Path to the generated plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    
    # Task data validation removed (handled by unified validation system)
    
    # Extract phases dynamically from the validation data
    phases = sorted([int(p) for p in task_data.keys() if str(p).isdigit()])
    
    # Add 100% for cyclical completion if not present
    if 100 not in phases and 0 in task_data:
        phases.append(100)
        task_data[100] = task_data[0].copy()
    
    task_type = get_task_classification(task_name)
    
    # Define variables based on mode
    if mode == 'kinematic':
        variables = [
            'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
            'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
        ]
        variable_labels = [
            'Hip Flexion Angle (Ipsi)', 'Hip Flexion Angle (Contra)',
            'Knee Flexion Angle (Ipsi)', 'Knee Flexion Angle (Contra)',
            'Ankle Dorsiflexion Angle (Ipsi)', 'Ankle Dorsiflexion Angle (Contra)'
        ]
        units = 'rad'
        value_conversion = np.degrees
        unit_suffix = '°'
    elif mode == 'kinetic':
        variables = [
            'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
            'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
            'ankle_dorsiflexion_moment_ipsi_Nm', 'ankle_dorsiflexion_moment_contra_Nm'
        ]
        variable_labels = [
            'Hip Flexion Moment (Ipsi)', 'Hip Flexion Moment (Contra)',
            'Knee Flexion Moment (Ipsi)', 'Knee Flexion Moment (Contra)',
            'Ankle Dorsiflexion Moment (Ipsi)', 'Ankle Dorsiflexion Moment (Contra)'
        ]
        units = 'Nm'
        value_conversion = lambda x: x
        unit_suffix = ''
    elif mode == 'segment':  # Link/segment angles
        variables = [
            'pelvis_tilt_angle_rad', 'pelvis_obliquity_angle_rad', 'pelvis_rotation_angle_rad',
            'trunk_flexion_angle_rad', 'trunk_lateral_angle_rad', 'trunk_rotation_angle_rad',
            'thigh_angle_ipsi_rad', 'thigh_angle_contra_rad',
            'shank_angle_ipsi_rad', 'shank_angle_contra_rad',
            'foot_angle_ipsi_rad', 'foot_angle_contra_rad'
        ]
        variable_labels = [
            'Pelvis Tilt Angle', 'Pelvis Obliquity Angle', 'Pelvis Rotation Angle',
            'Trunk Flexion Angle', 'Trunk Lateral Angle', 'Trunk Rotation Angle',
            'Thigh Angle (Ipsi)', 'Thigh Angle (Contra)',
            'Shank Angle (Ipsi)', 'Shank Angle (Contra)',
            'Foot Angle (Ipsi)', 'Foot Angle (Contra)'
        ]
        units = 'rad'
        value_conversion = np.degrees
        unit_suffix = '°'
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # Create figure with appropriate layout based on number of variables
    n_vars = len(variables)
    if mode == 'segment':
        # For segment angles, use 12x2 layout (12 variables x pass/fail)
        fig, axes = plt.subplots(12, 2, figsize=(14, 24))
    else:
        # For kinematic/kinetic, use 6x2 layout (6 variables x pass/fail)
        fig, axes = plt.subplots(6, 2, figsize=(14, 20))
    
    # Build title
    if mode == 'kinematic':
        mode_label = "Kinematic"
    elif mode == 'kinetic':
        mode_label = "Kinetic"
    elif mode == 'segment':
        mode_label = "Segment Angles"
    else:
        mode_label = mode.capitalize()
    task_type_label = "Gait-Based Task" if task_type == 'gait' else "Bilateral Symmetric Task"
    
    title = f'{task_name.replace("_", " ").title()} - {mode_label} Validation\n{task_type_label}'
    if dataset_name:
        title += f'\nDataset: {dataset_name}'
    if timestamp:
        title += f' | Generated: {timestamp}'
    
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Handle both old and new formats
    if failing_features is None and violations is not None:
        # Convert old format to new format for backward compatibility
        failing_features = {}
        for var_name, stride_list in violations.items():
            for stride_idx in stride_list:
                if stride_idx not in failing_features:
                    failing_features[stride_idx] = []
                if var_name not in failing_features[stride_idx]:
                    failing_features[stride_idx].append(var_name)
    elif failing_features is None:
        failing_features = {}
    
    # Build global set of failed stride indices for ANY variable being plotted
    # A stride is only "clean" if it passes validation for ALL variables
    global_failed_strides = set()
    for stride_idx, failed_vars in failing_features.items():
        # Check if this stride failed validation for any of the variables being plotted
        for var_name in variables:
            if var_name in failed_vars:
                global_failed_strides.add(stride_idx)
                break  # Once we know this stride failed, no need to check other variables
    
    # Process each variable
    for var_idx, (var_name, var_label) in enumerate(zip(variables, variable_labels)):
        # Build variable-specific failed strides (for red plot)
        variable_failed_strides = set()
        for stride_idx, failed_vars in failing_features.items():
            if var_name in failed_vars:
                variable_failed_strides.add(stride_idx)
        
        # Get validation ranges for this variable
        var_ranges = {}
        for phase in phases:
            if phase in task_data and var_name in task_data[phase]:
                var_ranges[phase] = task_data[phase][var_name]
        
        # Determine y-axis range from validation ranges
        all_mins = []
        all_maxs = []
        for phase, ranges in var_ranges.items():
            if 'min' in ranges and 'max' in ranges:
                min_val = ranges['min']
                max_val = ranges['max']
                # Skip None values (missing data placeholders)
                if min_val is None or max_val is None:
                    continue
                # Check for inf/nan after None check
                if not (np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val)):
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
        
        if all_mins and all_maxs:
            y_min = min(all_mins) - 0.1 * (max(all_maxs) - min(all_mins))
            y_max = max(all_maxs) + 0.1 * (max(all_maxs) - min(all_mins))
        else:
            y_min, y_max = -1, 1  # Default range if no valid ranges found
        
        # Plot PASSED strides (left column)
        ax_pass = axes[var_idx, 0]
        passed_count = 0
        
        # Plot data FIRST (behind validation ranges)
        if data is not None and data.size > 0 and var_idx < data.shape[2]:
            phase_percent = np.linspace(0, 100, 150)
            
            for stride_idx in range(data.shape[0]):
                if stride_idx not in global_failed_strides:
                    stride_data = data[stride_idx, :, var_idx]
                    ax_pass.plot(phase_percent, stride_data, color='green', alpha=0.3, linewidth=0.5, zorder=1)
                    passed_count += 1
        
        # Plot validation ranges on TOP of data (higher z-order)
        _plot_validation_ranges(ax_pass, var_ranges, phases, 'lightgreen', value_conversion, unit_suffix)
        
        # Add message if no data available
        if data is None or data.size == 0:
            ax_pass.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                        ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
        
        ax_pass.set_title(f'{var_label} - ✓ Passed ({passed_count} strides)', fontsize=10, fontweight='bold')
        ax_pass.set_xlim(-5, 105)
        ax_pass.set_ylim(y_min, y_max)
        ax_pass.set_xticks([0, 25, 50, 75, 100])
        ax_pass.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_pass.set_ylabel(f'{units}', fontsize=9)
        ax_pass.grid(True, alpha=0.3)
        
        # Only add x-label to bottom row
        last_row_idx = 11 if mode == 'segment' else 5  # 12th variable is at index 11
        if var_idx == last_row_idx:
            x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
            ax_pass.set_xlabel(x_label, fontsize=10)
        
        # Plot FAILED strides (right column)
        ax_fail = axes[var_idx, 1]
        failed_count = 0
        
        # Plot data FIRST (behind validation ranges)
        if data is not None and data.size > 0 and var_idx < data.shape[2]:
            for stride_idx in range(data.shape[0]):
                if stride_idx in variable_failed_strides:
                    stride_data = data[stride_idx, :, var_idx]
                    ax_fail.plot(phase_percent, stride_data, color='red', alpha=0.4, linewidth=0.5, zorder=1)
                    failed_count += 1
        
        # Plot validation ranges on TOP of data (higher z-order)
        _plot_validation_ranges(ax_fail, var_ranges, phases, 'lightcoral', value_conversion, unit_suffix)
        
        # Add message if no data available
        if data is None or data.size == 0:
            ax_fail.text(50, (y_min + y_max) / 2, 'Data Not Available', 
                        ha='center', va='center', fontsize=12, color='gray', alpha=0.7)
        
        ax_fail.set_title(f'{var_label} - ✗ Failed ({failed_count} strides)', fontsize=10, fontweight='bold')
        ax_fail.set_xlim(-5, 105)
        ax_fail.set_ylim(y_min, y_max)
        ax_fail.set_xticks([0, 25, 50, 75, 100])
        ax_fail.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
        ax_fail.grid(True, alpha=0.3)
        
        # Only add x-label to bottom row
        if var_idx == last_row_idx:
            ax_fail.set_xlabel(x_label, fontsize=10)
        
        # Add degree conversion on right y-axis for kinematic and segment plots
        if mode in ['kinematic', 'segment']:
            ax2_pass = ax_pass.twinx()
            ax2_pass.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_pass.set_ylabel('degrees', fontsize=9)
            
            ax2_fail = ax_fail.twinx()
            ax2_fail.set_ylim(value_conversion(y_min), value_conversion(y_max))
            ax2_fail.set_ylabel('degrees', fontsize=9)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    
    # Save the plot
    output_path = Path(output_dir) / f"{task_name}_{mode}_filters_by_phase_with_data.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


def _plot_validation_ranges(ax, var_ranges, phases, color, value_conversion, unit_suffix):
    """Helper function to plot validation range boxes."""
    box_width = 8
    
    # Collect min/max values for each phase (excluding 100% which duplicates 0%)
    phase_mins = []
    phase_maxs = []
    valid_phases = []
    
    for phase in phases:
        if phase not in var_ranges or phase == 100:  # Skip 100% as it duplicates 0%
            continue
            
        ranges = var_ranges[phase]
        if 'min' not in ranges or 'max' not in ranges:
            continue
            
        min_val = ranges['min']
        max_val = ranges['max']
        
        # Skip None values (missing data placeholders)
        if min_val is None or max_val is None:
            continue
        
        if np.isinf(min_val) or np.isinf(max_val) or np.isnan(min_val) or np.isnan(max_val):
            continue
        
        phase_mins.append(min_val)
        phase_maxs.append(max_val)
        valid_phases.append(phase)
        
        # Create rectangle for this phase range with higher z-order
        height = max_val - min_val
        rect = patches.Rectangle(
            (phase - box_width/2, min_val), box_width, height,
            linewidth=1.5, edgecolor='black', 
            facecolor=color, alpha=0.4, zorder=10
        )
        ax.add_patch(rect)
        
        # Add value labels with higher z-order
        if unit_suffix:  # Kinematic - convert to degrees
            min_label = f'{value_conversion(min_val):.0f}{unit_suffix}'
            max_label = f'{value_conversion(max_val):.0f}{unit_suffix}'
        else:  # Kinetic
            min_label = f'{min_val:.1f}'
            max_label = f'{max_val:.1f}'
        
        ax.text(phase, min_val - 0.02, min_label, 
               ha='center', va='top', fontsize=7, fontweight='bold', zorder=11)
        ax.text(phase, max_val + 0.02, max_label, 
               ha='center', va='bottom', fontsize=7, fontweight='bold', zorder=11)
    
    # NO connecting lines between boxes - removed the line plotting code