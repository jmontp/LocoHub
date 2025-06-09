#!/usr/bin/env python3
"""
Joint Validation Range Plots

Creates comprehensive validation plots showing joint angle ranges for all tasks and phases.
Generates three plots:
1. Hip angles (left and right) with phase-specific bounding boxes
2. Knee angles (left and right) with phase-specific bounding boxes  
3. Ankle angles (left and right) with phase-specific bounding boxes

Each plot shows all 9 tasks with colored bounding boxes indicating valid ranges at each phase.
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


def parse_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations.md file to extract joint angle ranges.
    
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
        task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## Pattern Definitions|$)'
        task_match = re.search(task_section_pattern, content, re.DOTALL)
        
        if task_match:
            task_content = task_match.group(1)
            
            # Find all phase sections within this task
            phase_pattern = r'#### Phase (\d+)%.*?\n\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=####|\*\*Kinematic|$)'
            phase_matches = re.findall(phase_pattern, task_content, re.DOTALL)
            
            for phase_str, table_content in phase_matches:
                phase = int(phase_str)
                validation_data[task][phase] = {}
                
                # Parse table rows for joint angles
                row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \| ([-\d.]+) \| (\w+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for variable, min_val, max_val, unit in rows:
                    # Extract bilateral joint angles (both left and right legs)
                    if ('_left_rad' in variable or '_right_rad' in variable) and unit == 'rad':
                        # Determine joint type and side
                        if 'hip_flexion_angle' in variable:
                            if '_left_rad' in variable:
                                joint_name = 'hip_flexion_angle_left'
                            elif '_right_rad' in variable:
                                joint_name = 'hip_flexion_angle_right'
                        elif 'knee_flexion_angle' in variable:
                            if '_left_rad' in variable:
                                joint_name = 'knee_flexion_angle_left'
                            elif '_right_rad' in variable:
                                joint_name = 'knee_flexion_angle_right'
                        elif 'ankle_flexion_angle' in variable:
                            if '_left_rad' in variable:
                                joint_name = 'ankle_flexion_angle_left'
                            elif '_right_rad' in variable:
                                joint_name = 'ankle_flexion_angle_right'
                        else:
                            continue
                        
                        validation_data[task][phase][joint_name] = {
                            'min': float(min_val),
                            'max': float(max_val)
                        }
    
    return validation_data


def create_joint_validation_plot(validation_data: Dict, joint_type: str, output_dir: str) -> str:
    """
    Create a validation plot for a specific joint type showing all tasks and phases.
    
    Args:
        validation_data: Parsed validation data
        joint_type: 'hip', 'knee', or 'ankle'
        output_dir: Directory to save the plot
        
    Returns:
        Path to the generated plot
    """
    # Define colors for different phases
    phase_colors = {
        0: '#FF6B6B',    # Red - Heel Strike/Initial
        33: '#4ECDC4',   # Teal - Mid-Stance/Loading
        50: '#45B7D1',   # Blue - Push-Off/Peak
        66: '#96CEB4'    # Green - Mid-Swing/Return
    }
    
    # Define task order and labels
    task_order = [
        'level_walking', 'incline_walking', 'decline_walking',
        'up_stairs', 'down_stairs', 'run',
        'sit_to_stand', 'jump', 'squats'
    ]
    
    task_labels = {
        'level_walking': 'Level Walking',
        'incline_walking': 'Incline Walking', 
        'decline_walking': 'Decline Walking',
        'up_stairs': 'Up Stairs',
        'down_stairs': 'Down Stairs',
        'run': 'Running',
        'sit_to_stand': 'Sit to Stand',
        'jump': 'Jumping',
        'squats': 'Squats'
    }
    
    # Create figure with subplots for left and right legs
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 10))
    fig.suptitle(f'{joint_type.title()} Flexion Angle Validation Ranges', fontsize=16, fontweight='bold')
    
    # Process left and right joints
    for ax, side in [(ax_left, 'left'), (ax_right, 'right')]:
        joint_var = f'{joint_type}_flexion_angle_{side}'
        
        y_pos = 0
        y_labels = []
        y_positions = []
        
        for task in task_order:
            if task in validation_data:
                task_data = validation_data[task]
                
                # Plot bounding boxes for each phase
                for phase in [0, 33, 50, 66]:
                    if phase in task_data and joint_var in task_data[phase]:
                        min_val = task_data[phase][joint_var]['min']
                        max_val = task_data[phase][joint_var]['max']
                        
                        # Create rectangle for this phase range
                        width = max_val - min_val
                        height = 0.15
                        
                        # Offset each phase slightly vertically
                        phase_offset = (phase / 66 - 0.5) * 0.6
                        rect_y = y_pos + phase_offset
                        
                        rect = patches.Rectangle(
                            (min_val, rect_y - height/2), width, height,
                            linewidth=1.5, edgecolor='black', 
                            facecolor=phase_colors[phase], alpha=0.7
                        )
                        ax.add_patch(rect)
                        
                        # Add phase label on first task
                        if task == task_order[0]:
                            ax.text(min_val + width/2, rect_y + height/2 + 0.1, 
                                   f'{phase}%', ha='center', va='bottom', 
                                   fontsize=8, fontweight='bold')
                
                y_labels.append(task_labels[task])
                y_positions.append(y_pos)
                y_pos += 1
        
        # Customize axes
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels)
        ax.set_xlabel(f'{joint_type.title()} Flexion Angle (radians)', fontsize=12)
        ax.set_title(f'{side.title()} Leg', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.set_ylim(-0.5, len(task_order) - 0.5)
        
        # Add degree labels on top axis
        ax2 = ax.twiny()
        rad_ticks = ax.get_xticks()
        deg_ticks = np.degrees(rad_ticks)
        ax2.set_xticks(rad_ticks)
        ax2.set_xticklabels([f'{deg:.0f}°' for deg in deg_ticks])
        ax2.set_xlabel(f'{joint_type.title()} Flexion Angle (degrees)', fontsize=12)
        ax2.set_xlim(ax.get_xlim())
    
    # Add legend
    legend_elements = [
        patches.Patch(color=phase_colors[0], label='Phase 0% (Heel Strike/Initial)'),
        patches.Patch(color=phase_colors[33], label='Phase 33% (Mid-Stance/Loading)'),
        patches.Patch(color=phase_colors[50], label='Phase 50% (Push-Off/Peak)'),
        patches.Patch(color=phase_colors[66], label='Phase 66% (Mid-Swing/Return)')
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=2, 
               bbox_to_anchor=(0.5, -0.02), fontsize=10)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1)
    
    # Save the figure
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{joint_type}_validation_ranges.png"
    filepath = os.path.join(output_dir, filename)
    
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close()
    
    return filepath


def main():
    """Main function to generate joint validation plots."""
    
    parser = argparse.ArgumentParser(
        description='Generate joint validation range plots'
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
    
    # Generate plots for each joint type
    joint_types = ['hip', 'knee', 'ankle']
    generated_files = []
    
    print(f"\nGenerating joint validation plots to: {args.output_dir}")
    
    for joint_type in joint_types:
        try:
            filepath = create_joint_validation_plot(validation_data, joint_type, args.output_dir)
            generated_files.append(filepath)
            print(f"  - Generated: {filepath}")
            
        except Exception as e:
            print(f"Error generating {joint_type} plot: {e}")
            return 1
    
    print(f"\n✅ Successfully generated {len(generated_files)} joint validation plots!")
    print("\nGenerated files:")
    for filepath in generated_files:
        print(f"  - {filepath}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())