#!/usr/bin/env python3
"""
Phase Progression Validation Plots - Version 5.0

Creates validation plots showing how joint angle ranges change across movement phases.
X-axis: Phase progression (0%, 25%, 50%, 75%) - NEW PHASE SYSTEM
Y-axis: Joint angle ranges (with bounding boxes)

NEW FEATURES:
- Updated to 0%, 25%, 50%, 75% phase system
- Automatic contralateral offset logic for gait-based tasks
- Task-appropriate bilateral handling (gait vs bilateral symmetric)
- Enhanced biomechanical accuracy with standard gait timing

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


def apply_contralateral_offset(task_data: Dict, task_name: str) -> Dict:
    """
    Apply contralateral offset logic for gait-based tasks.
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
    phases = [0, 25, 50, 75]
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


def parse_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations.md file to extract joint angle ranges.
    Updated for v5.0 with new phase system and contralateral offset logic.
    
    Args:
        file_path: Path to the validation_expectations.md file
        
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
            phase_pattern = r'#### Phase (\d+)%.*?\n\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=####|\*\*Contralateral|\*\*Note:|\*\*Kinematic|$)'
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
        validation_data[task] = apply_contralateral_offset(validation_data[task], task)
    
    return validation_data


def create_phase_progression_plot(validation_data: Dict, task_name: str, output_dir: str) -> str:
    """
    Create a phase progression plot for a specific task showing joint ranges across phases.
    Updated for v5.0 with new phase system and contralateral offset logic.
    
    Args:
        validation_data: Parsed validation data
        task_name: Name of the task
        output_dir: Directory to save the plot
        
    Returns:
        Path to the generated plot
    """
    if task_name not in validation_data:
        raise ValueError(f"Task {task_name} not found in validation data")
    
    task_data = validation_data[task_name]
    phases = [0, 25, 50, 75]  # Updated to new phase system
    task_type = get_task_classification(task_name)
    
    # Create figure with subplots for each joint type
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    
    # Add task classification to title
    task_type_label = "Gait-Based Task (Contralateral Offset)" if task_type == 'gait' else "Bilateral Symmetric Task"
    fig.suptitle(f'{task_name.replace("_", " ").title()} - Joint Range Progression Across Phases\n{task_type_label}', 
                 fontsize=16, fontweight='bold')
    
    # Define joint types and colors
    joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
    sides = ['left', 'right']
    
    # Colors for different joint types
    joint_colors = {
        'hip_flexion_angle': '#FF6B6B',    # Red
        'knee_flexion_angle': '#4ECDC4',   # Teal  
        'ankle_flexion_angle': '#45B7D1'   # Blue
    }
    
    # First pass: collect all data to determine shared y-axis ranges for each joint type
    joint_y_ranges = {}
    for joint_idx, joint_type in enumerate(joint_types):
        all_mins = []
        all_maxs = []
        
        for side in sides:
            joint_var = f'{joint_type}_{side}'
            
            for phase in phases:
                if phase in task_data and joint_var in task_data[phase]:
                    min_val = task_data[phase][joint_var]['min']
                    max_val = task_data[phase][joint_var]['max']
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
        
        if all_mins and all_maxs:
            # Add some padding to the range
            data_range = max(all_maxs) - min(all_mins)
            padding = data_range * 0.1  # 10% padding
            joint_y_ranges[joint_type] = {
                'min': min(all_mins) - padding,
                'max': max(all_maxs) + padding
            }
    
    # Second pass: create plots with shared y-axis ranges
    for joint_idx, joint_type in enumerate(joint_types):
        for side_idx, side in enumerate(sides):
            ax = axes[joint_idx, side_idx]
            joint_var = f'{joint_type}_{side}'
            
            # Extract data for this joint across phases
            phase_mins = []
            phase_maxs = []
            valid_phases = []
            
            for phase in phases:
                if phase in task_data and joint_var in task_data[phase]:
                    min_val = task_data[phase][joint_var]['min']
                    max_val = task_data[phase][joint_var]['max']
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
                        facecolor=joint_colors[joint_type], alpha=0.6
                    )
                    ax.add_patch(rect)
                    
                    # Add min/max value labels
                    ax.text(phase, min_val - 0.05, f'{np.degrees(min_val):.0f}°', 
                           ha='center', va='top', fontsize=8, fontweight='bold')
                    ax.text(phase, max_val + 0.05, f'{np.degrees(max_val):.0f}°', 
                           ha='center', va='bottom', fontsize=8, fontweight='bold')
                
                # Plot connecting lines to show progression
                ax.plot(valid_phases, phase_mins, 'o-', color='darkred', linewidth=2, 
                       markersize=6, label='Min Range', alpha=0.8)
                ax.plot(valid_phases, phase_maxs, 'o-', color='darkblue', linewidth=2, 
                       markersize=6, label='Max Range', alpha=0.8)
                
                # Fill area between min and max
                ax.fill_between(valid_phases, phase_mins, phase_maxs, 
                               color=joint_colors[joint_type], alpha=0.2)
            
            # Customize axes - Updated for new phase system
            ax.set_xlim(-5, 80)  # Adjusted for 0-75% range
            ax.set_xticks(phases)
            ax.set_xticklabels([f'{p}%' for p in phases])
            
            # Update x-axis label based on task type
            x_label = 'Gait Phase' if task_type == 'gait' else 'Movement Phase'
            ax.set_xlabel(x_label, fontsize=11)
            ax.set_ylabel(f'{joint_type.replace("_", " ").title()} (radians)', fontsize=11)
            ax.set_title(f'{side.title()} Leg', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Set shared y-axis range for this joint type
            if joint_type in joint_y_ranges:
                y_min = joint_y_ranges[joint_type]['min']
                y_max = joint_y_ranges[joint_type]['max']
                ax.set_ylim(y_min, y_max)
            
            # Add degree labels on right axis
            ax2 = ax.twinx()
            rad_ticks = ax.get_yticks()
            deg_ticks = np.degrees(rad_ticks)
            ax2.set_yticks(rad_ticks)
            ax2.set_yticklabels([f'{deg:.0f}°' for deg in deg_ticks])
            ax2.set_ylabel(f'{joint_type.replace("_", " ").title()} (degrees)', fontsize=11)
            ax2.set_ylim(ax.get_ylim())
            
            # Add legend only to the first subplot
            if joint_idx == 0 and side_idx == 0:
                ax.legend(loc='upper left', fontsize=9)
    
    # Adjust layout and save
    plt.tight_layout()
    
    # Save the figure
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{task_name}_phase_progression.png"
    filepath = os.path.join(output_dir, filename)
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filepath


def main():
    """Main function to generate phase progression plots."""
    
    parser = argparse.ArgumentParser(
        description='Generate phase progression validation plots'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='validation_images',
        help='Output directory for validation plots (default: validation_images)'
    )
    parser.add_argument(
        '--validation-file',
        type=str,
        default='docs/standard_spec/validation_expectations.md',
        help='Path to validation_expectations.md file'
    )
    parser.add_argument(
        '--tasks',
        type=str,
        nargs='*',
        help='Specific tasks to generate plots for (default: all tasks)'
    )
    
    args = parser.parse_args()
    
    # Find the validation expectations file
    if os.path.exists(args.validation_file):
        validation_file = args.validation_file
    else:
        # Try from project root
        project_root = Path(__file__).parent.parent.parent
        validation_file = project_root / args.validation_file
        if not validation_file.exists():
            print(f"Error: Could not find validation file at {args.validation_file}")
            return 1
    
    print(f"Parsing validation expectations from: {validation_file}")
    
    # Parse the validation expectations
    try:
        validation_data = parse_validation_expectations(str(validation_file))
        print(f"Successfully parsed data for {len(validation_data)} tasks")
        
    except Exception as e:
        print(f"Error parsing validation file: {e}")
        return 1
    
    # Determine which tasks to process
    if args.tasks:
        tasks_to_process = [task for task in args.tasks if task in validation_data]
        if not tasks_to_process:
            print(f"Error: None of the specified tasks found in validation data")
            return 1
    else:
        tasks_to_process = list(validation_data.keys())
    
    # Generate plots for each task
    generated_files = []
    
    print(f"\nGenerating phase progression plots to: {args.output_dir}")
    
    for task_name in tasks_to_process:
        try:
            filepath = create_phase_progression_plot(validation_data, task_name, args.output_dir)
            generated_files.append(filepath)
            print(f"  - Generated: {filepath}")
            
        except Exception as e:
            print(f"Error generating plot for {task_name}: {e}")
            continue
    
    print(f"\n✅ Successfully generated {len(generated_files)} phase progression plots!")
    print("\nGenerated files:")
    for filepath in generated_files:
        print(f"  - {filepath}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())