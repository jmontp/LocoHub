#!/usr/bin/env python3
"""
Update Validation Images Script

This script reads the validated biomechanical ranges from the validation_expectations_kinematic.md file
and generates kinematic pose visualizations for all tasks and phases.

Usage:
    python update_validation_images.py [--output-dir OUTPUT_DIR] [--validation-file FILE]

The script will:
1. Run unit tests on the markdown parser to ensure functionality
2. Parse the validation_expectations_kinematic.md file to extract joint angle ranges
3. Generate pose visualizations for each task and phase (0%, 25%, 50%, 75%)
4. Save images to the specified output directory
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


def run_parser_unit_tests() -> bool:
    """
    Run unit tests on the markdown parser using test data.
    
    Returns:
        True if all tests pass, False otherwise
    """
    try:
        # Path to test validation file
        test_file = 'docs/standard_spec/test_validation_parser.md'
        
        if not os.path.exists(test_file):
            print(f"⚠️  Warning: Test file not found at {test_file}")
            return True  # Don't fail if test file is missing
        
        print(f"🧪 Running unit tests on markdown parser...")
        
        # Parse the test file
        test_data = parse_validation_expectations(test_file)
        
        # Test 1: Task detection
        expected_task = 'test_walking_parser'
        if expected_task not in test_data:
            print(f"❌ Test 1 FAILED: Expected task '{expected_task}' not found")
            return False
        print(f"✅ Test 1 PASSED: Task detection")
        
        # Test 2: Phase parsing
        expected_phases = {0, 25, 50, 75}
        actual_phases = set(test_data[expected_task].keys())
        if not expected_phases.issubset(actual_phases):
            print(f"❌ Test 2 FAILED: Expected phases {expected_phases}, got {actual_phases}")
            return False
        print(f"✅ Test 2 PASSED: Phase parsing")
        
        # Test 3: Variable extraction
        phase_0_data = test_data[expected_task][0]
        expected_vars = {'hip_flexion_angle_ipsi', 'knee_flexion_angle_ipsi', 'ankle_flexion_angle_ipsi'}
        actual_vars = set(phase_0_data.keys())
        if not expected_vars.issubset(actual_vars):
            print(f"❌ Test 3 FAILED: Expected variables {expected_vars}, got {actual_vars}")
            return False
        print(f"✅ Test 3 PASSED: Variable extraction")
        
        # Test 4: Value parsing
        hip_data = phase_0_data['hip_flexion_angle_ipsi']
        if not (isinstance(hip_data['min'], (int, float)) and isinstance(hip_data['max'], (int, float))):
            print(f"❌ Test 4 FAILED: Values should be numeric, got {hip_data}")
            return False
        if hip_data['min'] >= hip_data['max']:
            print(f"❌ Test 4 FAILED: Min should be < Max, got {hip_data}")
            return False
        print(f"✅ Test 4 PASSED: Value parsing and validation")
        
        # Test 5: Negative value handling
        ankle_data = phase_0_data['ankle_flexion_angle_ipsi']
        if ankle_data['min'] != -0.1 or ankle_data['max'] != 0.1:
            print(f"❌ Test 5 FAILED: Expected ankle range -0.1 to 0.1, got {ankle_data}")
            return False
        print(f"✅ Test 5 PASSED: Negative value handling")
        
        print(f"🎉 All parser unit tests PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Unit tests FAILED with error: {e}")
        return False


def parse_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations_kinematic.md file to extract joint angle ranges.
    
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
                
                # Parse table rows for joint angles - Updated to handle degree format
                row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \([^)]+\) \| ([-\d.]+) \([^)]+\) \| (\w+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for variable, min_val, max_val, unit in rows:
                    # Extract bilateral joint angles (both ipsi and contra legs)
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
    
    return validation_data


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
        task_data: Phase data for the task (contains only ipsilateral data)
        task_name: Name of the task
        
    Returns:
        Updated task data with contralateral ranges computed
    """
    task_type = get_task_classification(task_name)
    
    if task_type == 'bilateral':
        # Bilateral tasks already have both legs specified in validation expectations
        return task_data
    
    # For gait tasks, compute contralateral leg ranges with 50% offset
    phases = [0, 25, 50, 75, 100]  # Include 100% for cyclical completion
    joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
    
    # Create a new task_data copy to avoid modifying original
    updated_task_data = {}
    for phase in [0, 25, 50, 75]:  # Only process existing phases
        if phase in task_data:
            updated_task_data[phase] = task_data[phase].copy()
        else:
            updated_task_data[phase] = {}
    
    # Apply contralateral offset logic
    for phase in [0, 25, 50, 75]:
        if phase in task_data:
            # Calculate contralateral phase with 50% offset
            contralateral_phase = (phase + 50) % 100
            
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
            
            # Copy ipsilateral data to contralateral for the offset phase
            for joint_type in joint_types:
                ipsi_joint = f'{joint_type}_ipsi'
                contra_joint = f'{joint_type}_contra'
                
                if ipsi_joint in task_data[source_phase]:
                    if phase not in updated_task_data:
                        updated_task_data[phase] = {}
                    updated_task_data[phase][contra_joint] = task_data[source_phase][ipsi_joint].copy()
    
    return updated_task_data


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
        
        # Apply contralateral offset logic for gait-based tasks
        phase_data_with_offset = apply_contralateral_offset(phase_data, task_name)
        
        # Process each phase
        for phase, joint_ranges in phase_data_with_offset.items():
            if joint_ranges:  # Only generate if we have data
                # Generate the visualization
                filepath = generator.generate_range_visualization(
                    task_name, phase, joint_ranges, output_dir
                )
                print(f"  - Generated: {filepath}")


def main():
    """Main function to update validation images."""
    
    parser = argparse.ArgumentParser(
        description='Update validation images based on validation_expectations_kinematic.md'
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
        default='docs/standard_spec/validation_expectations_kinematic.md',
        help='Path to validation_expectations_kinematic.md file'
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip unit tests (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Run unit tests first (unless skipped)
    if not args.skip_tests:
        if not run_parser_unit_tests():
            print("❌ Unit tests failed. Aborting to prevent parsing errors.")
            print("   Use --skip-tests to bypass (not recommended)")
            return 1
        print("")  # Add spacing after tests
    
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