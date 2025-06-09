#!/usr/bin/env python3
"""
Update Validation Images Script

This script reads the validated biomechanical ranges from the validation_expectations.md file
and generates kinematic pose visualizations for all tasks and phases.

Usage:
    python update_validation_images.py [--output-dir OUTPUT_DIR]

The script will:
1. Parse the validation_expectations.md file to extract joint angle ranges
2. Generate pose visualizations for each task and phase (0%, 33%, 50%, 66%)
3. Save images to the specified output directory
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source'))

from visualization.kinematic_pose_generator import KinematicPoseGenerator


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


def generate_all_validation_images(validation_data: Dict, output_dir: str):
    """
    Generate validation images for all tasks and phases.
    
    Args:
        validation_data: Parsed validation data
        output_dir: Directory to save images
    """
    generator = KinematicPoseGenerator()
    
    # Process each task
    for task_name, phase_data in validation_data.items():
        print(f"\nGenerating images for task: {task_name}")
        
        # Process each phase
        for phase, joint_ranges in phase_data.items():
            if joint_ranges:  # Only generate if we have data
                # Generate the visualization
                filepath = generator.generate_range_visualization(
                    task_name, phase, joint_ranges, output_dir
                )
                print(f"  - Generated: {filepath}")


def main():
    """Main function to update validation images."""
    
    parser = argparse.ArgumentParser(
        description='Update validation images based on validation_expectations.md'
    )
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='validation_images',
        help='Output directory for validation images (default: validation_images)'
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
        project_root = Path(__file__).parent.parent
        validation_file = project_root / args.validation_file
        if not validation_file.exists():
            print(f"Error: Could not find validation file at {args.validation_file}")
            return 1
    
    print(f"Parsing validation expectations from: {validation_file}")
    
    # Parse the validation expectations
    try:
        validation_data = parse_validation_expectations(str(validation_file))
        print(f"Successfully parsed data for {len(validation_data)} tasks")
        
        # Count total phases
        total_phases = sum(len(phases) for phases in validation_data.values())
        print(f"Total phase points to generate: {total_phases}")
        
    except Exception as e:
        print(f"Error parsing validation file: {e}")
        return 1
    
    # Generate all validation images
    print(f"\nGenerating validation images to: {args.output_dir}")
    try:
        generate_all_validation_images(validation_data, args.output_dir)
        print(f"\n✅ Successfully generated validation images!")
        
    except Exception as e:
        print(f"Error generating images: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())