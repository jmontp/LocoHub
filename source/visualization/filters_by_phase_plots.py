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


def apply_contralateral_offset_kinematic(task_data: Dict, task_name: str) -> Dict:
    """
    Apply contralateral offset logic for gait-based tasks (kinematic variables).
    For bilateral tasks, return data as-is.
    
    Args:
        task_data: Phase data for the task
        task_name: Name of the task
        
    Returns:
        Updated task data with contralateral ranges computed
    """
    task_type = get_task_classification(task_name)
    
    if task_type == 'bilateral':
        # Bilateral tasks already have both legs specified
        return task_data
    
    # For gait tasks, compute contralateral leg ranges with 50% offset
    phases = [0, 25, 50, 75, 100]
    joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
    
    # Create a new task_data copy to avoid modifying original
    updated_task_data = {}
    for phase in phases:
        if phase in task_data:
            updated_task_data[phase] = task_data[phase].copy()
        else:
            updated_task_data[phase] = {}
    
    # Apply contralateral offset logic
    for phase in phases:
        if phase == 100:
            # 100% phase should be the same as 0% to show cyclical nature
            if 0 in task_data:
                updated_task_data[100] = task_data[0].copy()
                
                # Apply contralateral offset for 100% phase: 100% contra = 50% ipsi
                if 50 in task_data:
                    for joint_type in joint_types:
                        ipsi_joint = f'{joint_type}_ipsi'
                        contra_joint = f'{joint_type}_contra'
                        if ipsi_joint in task_data[50]:
                            updated_task_data[100][contra_joint] = task_data[50][ipsi_joint].copy()
            continue
            
        if phase in task_data:
            # Calculate contralateral phase with 50% offset
            contralateral_phase = (phase + 50) % 100
            if contralateral_phase == 100:
                contralateral_phase = 0
            
            # Map contralateral phase to available phases
            if contralateral_phase == 0:
                source_phase = 0
            elif contralateral_phase == 25:
                source_phase = 25
            elif contralateral_phase == 50:
                source_phase = 50
            elif contralateral_phase == 75:
                source_phase = 75
            else:
                continue
            
            # Copy left leg data to right leg for contralateral phase
            for joint_type in joint_types:
                left_joint = f'{joint_type}_ipsi'
                right_joint = f'{joint_type}_contra'
                
                if left_joint in task_data[source_phase]:
                    if phase not in updated_task_data:
                        updated_task_data[phase] = {}
                    updated_task_data[phase][right_joint] = task_data[source_phase][left_joint].copy()
    
    return updated_task_data


def apply_contralateral_offset_kinetic(task_data: Dict, task_name: str) -> Dict:
    """
    Apply contralateral offset logic for gait-based tasks (kinetic variables).
    For bilateral tasks, return data as-is.
    
    Args:
        task_data: Phase data for the task
        task_name: Name of the task
        
    Returns:
        Updated task data with contralateral ranges computed
    """
    task_type = get_task_classification(task_name)
    
    if task_type == 'bilateral':
        # Bilateral tasks already have both legs specified
        return task_data
    
    # For gait tasks, compute contralateral leg ranges with 50% offset
    phases = [0, 25, 50, 75, 100]
    kinetic_types = ['hip_moment', 'knee_moment', 'ankle_moment', 'vertical_grf', 'ap_grf', 'ml_grf']
    
    updated_task_data = task_data.copy()
    
    for phase in phases:
        if phase not in updated_task_data:
            updated_task_data[phase] = {}
        
        # Apply 50% offset logic for contralateral variables
        # Phase 0% ipsi = Phase 50% contra, Phase 25% ipsi = Phase 75% contra, etc.
        contralateral_phase = (phase + 50) % 100
        
        if contralateral_phase in task_data:
            source_phase = contralateral_phase
        else:
            # Fallback to same phase if offset phase not available
            source_phase = phase
            
        for kinetic_type in kinetic_types:
            # For moments, apply offset logic to ipsi/contra
            if 'moment' in kinetic_type:
                ipsi_var = f'{kinetic_type}_ipsi_Nm_kg'
                contra_var = f'{kinetic_type}_contra_Nm_kg'
                
                if ipsi_var in task_data[source_phase]:
                    updated_task_data[phase][contra_var] = task_data[source_phase][ipsi_var].copy()
            
            # For GRF, forces are shared between legs (no ipsi/contra distinction needed)
            # GRF represents the combined ground reaction, but we can model bilateral patterns
    
    return updated_task_data


def parse_kinematic_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations_kinematic.md file to extract joint angle ranges.
    Updated for v6.0 with new phase system and contralateral offset logic.
    
    Args:
        file_path: Path to the validation_expectations_kinematic.md file
        
    Returns:
        Dictionary structured as: {task_name: {phase: {joint: {min, max}}}}
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Dictionary to store parsed data
    validation_data = {}
    
    # Find all task sections
    task_pattern = r'### Task: ([\w_]+)\n'
    tasks = re.findall(task_pattern, content)
    
    for task in tasks:
        validation_data[task] = {}
        
        # Find the task section
        task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## ✅ \*\*MAJOR UPDATE COMPLETED\*\*|## Joint Validation Range Summary|## Pattern Definitions|$)'
        task_match = re.search(task_section_pattern, content, re.DOTALL)
        
        if task_match:
            task_content = task_match.group(1)
            
            # Find all phase sections within this task - Updated for new phases
            phase_pattern = r'#### Phase (\d+)%.*?\n\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=####|\*\*Contralateral|\*\*Note:|\*\*Forward|$)'
            phase_matches = re.findall(phase_pattern, task_content, re.DOTALL)
            
            for phase_str, table_content in phase_matches:
                phase = int(phase_str)
                validation_data[task][phase] = {}
                
                # Parse table rows for joint angles - Updated to handle degree format
                row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \([^)]+\) \| ([-\d.]+) \([^)]+\) \| (\w+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for variable, min_val, max_val, unit in rows:
                    # Extract bilateral joint angles (both left and right legs)
                    if ('_ipsi_rad' in variable or '_contra_rad' in variable) and unit == 'rad':
                        # Determine joint type and side
                        if 'hip_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'hip_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'hip_flexion_angle_contra'
                        elif 'knee_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'knee_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'knee_flexion_angle_contra'
                        elif 'ankle_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'ankle_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'ankle_flexion_angle_contra'
                        else:
                            continue
                        
                        validation_data[task][phase][joint_name] = {
                            'min': float(min_val),
                            'max': float(max_val)
                        }
        
        # Apply contralateral offset logic for gait-based tasks
        validation_data[task] = apply_contralateral_offset_kinematic(validation_data[task], task)
    
    return validation_data


def parse_kinetic_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations_kinetic.md file to extract force/moment ranges.
    
    Args:
        file_path: Path to the validation_expectations_kinetic.md file
        
    Returns:
        Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Dictionary to store parsed data
    validation_data = {}
    
    # Find all task sections
    task_pattern = r'### Task: ([\w_]+)\n'
    tasks = re.findall(task_pattern, content)
    
    for task in tasks:
        validation_data[task] = {}
        
        # Find the task section
        task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## Research Requirements|$)'
        task_match = re.search(task_section_pattern, content, re.DOTALL)
        
        if task_match:
            task_content = task_match.group(1)
            
            # Find all phase tables within this task
            phase_pattern = r'#### Phase (\d+)% \([^)]+\)\n\| Variable.*?\n((?:\|.*?\n)*)'
            phase_matches = re.findall(phase_pattern, task_content, re.MULTILINE)
            
            for phase_str, table_content in phase_matches:
                phase = int(phase_str)
                validation_data[task][phase] = {}
                
                # Parse each row in the table
                row_pattern = r'\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for row in rows:
                    if len(row) == 5:
                        variable, min_val_str, max_val_str, units, notes = [col.strip() for col in row]
                        
                        # Skip header rows
                        if variable == 'Variable' or '---' in variable:
                            continue
                        
                        # Extract numeric values, handling both simple numbers and degree annotations
                        min_val = extract_numeric_value(min_val_str)
                        max_val = extract_numeric_value(max_val_str)
                        
                        # Store the variable data
                        validation_data[task][phase][variable] = {
                            'min': min_val,
                            'max': max_val
                        }
    
    return validation_data


def extract_numeric_value(value_str: str) -> float:
    """
    Extract numeric value from a string that may contain degree annotations.
    
    Args:
        value_str: String containing numeric value (e.g., "0.1", "-0.5")
        
    Returns:
        Extracted numeric value as float
    """
    # Remove any whitespace
    value_str = value_str.strip()
    
    # Extract the first number found (handles negative numbers)
    match = re.search(r'-?\d*\.?\d+', value_str)
    if match:
        return float(match.group())
    else:
        # Fallback to 0 if no number found
        return 0.0


def create_filters_by_phase_plot(validation_data: Dict, task_name: str, output_dir: str, mode: str = 'kinematic') -> str:
    """
    Create a filters by phase plot for a specific task showing ranges across phases.
    Updated for v6.0 with unified kinematic/kinetic plotting.
    
    Args:
        validation_data: Parsed validation data
        task_name: Name of the task
        output_dir: Directory to save the plot
        mode: 'kinematic' for joint angles or 'kinetic' for forces/moments
        
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
                ax.legend(loc='upper left', fontsize=9)
    
    # Adjust layout and save
    plt.tight_layout()
    
    # Save the figure
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{task_name}_{mode}_filters_by_phase.png"
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
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='validation_images',
        help='Output directory for validation plots (default: validation_images)'
    )
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
        print(f"\nGenerating kinematic filters by phase plots to: {args.output_dir}")
        
        for task_name in tasks_to_process:
            try:
                filepath = create_filters_by_phase_plot(kinematic_data, task_name, args.output_dir, 'kinematic')
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
        print(f"\nGenerating kinetic filters by phase plots to: {args.output_dir}")
        
        for task_name in tasks_to_process:
            try:
                # Apply contralateral offset if needed
                task_data_with_offset = apply_contralateral_offset_kinetic(kinetic_data[task_name], task_name)
                kinetic_data[task_name] = task_data_with_offset
                
                filepath = create_filters_by_phase_plot(kinetic_data, task_name, args.output_dir, 'kinetic')
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