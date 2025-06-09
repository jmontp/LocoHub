#!/usr/bin/env python3
"""
Kinetic Phase Progression Plots Generator

This script generates phase progression validation plots for kinetic variables (forces and moments).
Similar to kinematic plots but focused on GRF and joint moments with normalized units.

Usage:
    python kinetic_phase_progression_plots.py [--task TASK] [--output OUTPUT_DIR]

The script will:
1. Parse validation_expectations_kinetic.md for force/moment ranges
2. Generate phase progression plots showing force/moment evolution across gait cycle
3. Apply contralateral offset logic for gait-based tasks
4. Save plots with kinetic-specific styling and units
"""

import os
import sys
import re
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, List

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


def parse_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
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


def create_kinetic_phase_progression_plot(validation_data: Dict, task_name: str, output_dir: str) -> str:
    """
    Create a kinetic phase progression plot for a specific task showing force/moment ranges across phases.
    
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
    phases = [0, 25, 50, 75, 100]  # Include 100% for cyclical completion
    task_type = get_task_classification(task_name)
    
    # Add 100% phase data (same as 0% to show cyclical nature)
    # For gait tasks, we need to apply the contralateral offset logic to 100% as well
    if 0 in task_data and 100 not in task_data:
        task_data[100] = task_data[0].copy()
        
        # Apply contralateral offset logic for 100% phase in gait tasks
        if task_type == 'gait':
            # For gait tasks, 100% contralateral should be same as 50% ipsilateral (offset logic)
            kinetic_types = ['hip_moment', 'knee_moment', 'ankle_moment']
            
            # If we have phase 50 data, use its ipsilateral data for 100% contralateral
            if 50 in task_data:
                for kinetic_type in kinetic_types:
                    ipsi_var = f'{kinetic_type}_ipsi_Nm_kg'
                    contra_var = f'{kinetic_type}_contra_Nm_kg'
                    
                    if ipsi_var in task_data[50]:
                        task_data[100][contra_var] = task_data[50][ipsi_var].copy()
    
    # Create figure with subplots for each variable type
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    
    # Add task classification to title
    task_type_label = "Gait-Based Task (Contralateral Offset)" if task_type == 'gait' else "Bilateral Symmetric Task"
    fig.suptitle(f'{task_name.replace("_", " ").title()} - Kinetic Range Progression Across Phases\\n{task_type_label}', 
                 fontsize=16, fontweight='bold')
    
    # Define kinetic types and colors
    kinetic_types = ['hip_moment', 'knee_moment', 'ankle_moment']
    sides = ['ipsi', 'contra']
    
    # Colors for different kinetic types (different from kinematic colors)
    kinetic_colors = {
        'hip_moment': '#E74C3C',      # Red
        'knee_moment': '#8E44AD',     # Purple  
        'ankle_moment': '#3498DB'     # Blue
    }
    
    # First pass: collect all data to determine shared y-axis ranges for each kinetic type
    kinetic_y_ranges = {}
    for kinetic_idx, kinetic_type in enumerate(kinetic_types):
        all_mins = []
        all_maxs = []
        
        for side in sides:
            kinetic_var = f'{kinetic_type}_{side}_Nm_kg'
            
            for phase in phases:
                if phase in task_data and kinetic_var in task_data[phase]:
                    min_val = task_data[phase][kinetic_var]['min']
                    max_val = task_data[phase][kinetic_var]['max']
                    all_mins.append(min_val)
                    all_maxs.append(max_val)
        
        if all_mins and all_maxs:
            # Add some padding to the range
            data_range = max(all_maxs) - min(all_mins)
            padding = data_range * 0.1  # 10% padding
            kinetic_y_ranges[kinetic_type] = {
                'min': min(all_mins) - padding,
                'max': max(all_maxs) + padding
            }
    
    # Second pass: create plots with shared y-axis ranges
    for kinetic_idx, kinetic_type in enumerate(kinetic_types):
        for side_idx, side in enumerate(sides):
            ax = axes[kinetic_idx, side_idx]
            kinetic_var = f'{kinetic_type}_{side}_Nm_kg'
            
            # Extract data for this kinetic variable across phases
            phase_mins = []
            phase_maxs = []
            valid_phases = []
            
            for phase in phases:
                if phase in task_data and kinetic_var in task_data[phase]:
                    min_val = task_data[phase][kinetic_var]['min']
                    max_val = task_data[phase][kinetic_var]['max']
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
                    x_center = phase
                    x_left = x_center - box_width/2
                    
                    # Draw bounding box
                    rect = plt.Rectangle((x_left, min_val), box_width, height, 
                                       facecolor=kinetic_colors[kinetic_type], 
                                       alpha=0.3, edgecolor=kinetic_colors[kinetic_type], 
                                       linewidth=1)
                    ax.add_patch(rect)
                
                # Draw connecting lines for min and max values
                ax.plot(valid_phases, phase_mins, 'o-', color=kinetic_colors[kinetic_type], 
                       linewidth=2, markersize=6, label='Min Range', alpha=0.8)
                ax.plot(valid_phases, phase_maxs, 's-', color=kinetic_colors[kinetic_type], 
                       linewidth=2, markersize=6, label='Max Range', alpha=0.8)
                
                # Add value labels at min/max points
                for i, phase in enumerate(valid_phases):
                    # Add labels at min and max points
                    ax.text(phase, phase_mins[i], f'{phase_mins[i]:.1f}', 
                           ha='center', va='bottom', fontsize=8, fontweight='bold')
                    ax.text(phase, phase_maxs[i], f'{phase_maxs[i]:.1f}', 
                           ha='center', va='top', fontsize=8, fontweight='bold')
            
            # Set axis properties
            ax.set_xlim(-5, 105)
            if kinetic_type in kinetic_y_ranges:
                ax.set_ylim(kinetic_y_ranges[kinetic_type]['min'], 
                           kinetic_y_ranges[kinetic_type]['max'])
            
            ax.set_xlabel('Gait Phase (%)', fontsize=12)
            ax.set_ylabel(f'{kinetic_type.replace("_", " ").title()} (Nm/kg)', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.set_xticks([0, 25, 50, 75, 100])
            
            # Set title
            side_title = 'Ipsilateral Leg' if side == 'ipsi' else 'Contralateral Leg'
            ax.set_title(f'{side_title}', fontsize=12, fontweight='bold')
            
            # Add legend to first subplot only
            if kinetic_idx == 0 and side_idx == 0:
                ax.legend(loc='upper right', fontsize=10)
    
    # Add overall description
    fig.text(0.02, 0.02, 
             'Reading the Plot: Colored boxes show valid ranges at each phase. '
             'Lines connect min/max values across phases. '
             'Values in Nm/kg (normalized by body mass).',
             fontsize=10, style='italic', wrap=True)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.9, bottom=0.1)
    
    # Save the plot
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{task_name}_kinetic_phase_progression.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_path


def main():
    """Main function to generate kinetic phase progression plots."""
    
    parser = argparse.ArgumentParser(
        description='Generate kinetic phase progression plots from validation_expectations_kinetic.md'
    )
    parser.add_argument(
        '--task', 
        type=str, 
        help='Specific task to generate plot for (default: all tasks)'
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
        default='docs/standard_spec/validation_expectations_kinetic.md',
        help='Path to validation_expectations_kinetic.md file'
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
    
    print(f"Parsing kinetic validation expectations from: {validation_file}")
    
    # Parse the validation expectations
    try:
        validation_data = parse_validation_expectations(str(validation_file))
        print(f"Successfully parsed data for {len(validation_data)} tasks")
    except Exception as e:
        print(f"Error parsing validation file: {e}")
        return 1
    
    print(f"\\nGenerating kinetic phase progression plots to: {args.output_dir}")
    
    # Generate plots for specified task or all tasks
    if args.task:
        if args.task in validation_data:
            tasks_to_process = [args.task]
        else:
            print(f"Error: Task '{args.task}' not found in validation data")
            print(f"Available tasks: {list(validation_data.keys())}")
            return 1
    else:
        tasks_to_process = list(validation_data.keys())
    
    generated_files = []
    for task_name in tasks_to_process:
        try:
            # Apply contralateral offset if needed
            task_data_with_offset = apply_contralateral_offset(validation_data[task_name], task_name)
            validation_data[task_name] = task_data_with_offset
            
            output_path = create_kinetic_phase_progression_plot(validation_data, task_name, args.output_dir)
            generated_files.append(output_path)
            print(f"  - Generated: {output_path}")
        except Exception as e:
            print(f"  - Error generating plot for {task_name}: {e}")
    
    print(f"\\n✅ Successfully generated {len(generated_files)} kinetic phase progression plots!")
    
    if generated_files:
        print(f"\\nGenerated files:")
        for file_path in generated_files:
            print(f"  - {file_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())