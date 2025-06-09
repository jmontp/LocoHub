#!/usr/bin/env python3
"""
Phase Range Validation Image Generator - Version 5.0

Generates individual validation range images for each task and phase point.
Updated for the new 0%, 25%, 50%, 75% phase system with contralateral offset logic.

Creates stick figure visualizations showing the min/max joint angle ranges 
at each phase point for validation documentation.
"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'source'))

from visualization.phase_progression_plots import parse_validation_expectations, get_task_classification


def generate_stick_figure(joint_angles: Dict[str, Tuple[float, float]], title: str, 
                         save_path: str, task_type: str = 'gait') -> None:
    """
    Generate a stick figure showing min/max joint angle ranges.
    
    Args:
        joint_angles: Dictionary with joint angles {joint_name: (min, max)}
        title: Title for the plot
        save_path: Path to save the image
        task_type: 'gait' or 'bilateral' for different visualization styles
    """
    
    fig, (ax_min, ax_max) = plt.subplots(1, 2, figsize=(12, 8))
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Extract angles for both legs
    angles = {}
    for side in ['left', 'right']:
        angles[side] = {}
        for joint in ['hip', 'knee', 'ankle']:
            joint_key = f'{joint}_flexion_angle_{side}'
            if joint_key in joint_angles:
                angles[side][joint] = joint_angles[joint_key]
            else:
                # Default fallback values
                angles[side][joint] = (0.0, 0.5)
    
    # Generate stick figures for min and max configurations
    for ax, config in [(ax_min, 'min'), (ax_max, 'max')]:
        # Draw both legs
        for side, color in [('left', 'blue'), ('right', 'red')]:
            if side in angles:
                hip_angle = angles[side]['hip'][0 if config == 'min' else 1]
                knee_angle = angles[side]['knee'][0 if config == 'min' else 1]
                ankle_angle = angles[side]['ankle'][0 if config == 'min' else 1]
                
                # Forward kinematics with proper joint angle interpretation
                x_offset = -0.2 if side == 'left' else 0.2
                
                # Hip position (pelvis attachment point)
                hip_x = x_offset
                hip_y = 1.0
                
                # Thigh segment (hip flexion from vertical reference)
                # Positive hip flexion = thigh rotated forward (positive x direction)
                thigh_length = 0.4
                thigh_angle_from_vertical = hip_angle  # Hip flexion angle
                thigh_x = hip_x + thigh_length * np.sin(thigh_angle_from_vertical)
                thigh_y = hip_y - thigh_length * np.cos(thigh_angle_from_vertical)
                
                # Shank segment (knee flexion relative to thigh)
                # Positive knee flexion = shank rotated backward relative to thigh
                shank_length = 0.4
                shank_angle_from_vertical = thigh_angle_from_vertical - knee_angle
                shank_x = thigh_x + shank_length * np.sin(shank_angle_from_vertical)
                shank_y = thigh_y - shank_length * np.cos(shank_angle_from_vertical)
                
                # Foot segment (ankle dorsiflexion relative to shank)
                # Positive ankle flexion = foot dorsiflexed (toes up relative to shank)
                foot_length = 0.15
                foot_angle_from_vertical = shank_angle_from_vertical + ankle_angle
                foot_x = shank_x + foot_length * np.sin(foot_angle_from_vertical)
                foot_y = shank_y - foot_length * np.cos(foot_angle_from_vertical)
                
                # Draw leg segments
                ax.plot([hip_x, thigh_x], [hip_y, thigh_y], color=color, linewidth=3, alpha=0.8, label=f'{side.title()} Leg')
                ax.plot([thigh_x, shank_x], [thigh_y, shank_y], color=color, linewidth=3, alpha=0.8)
                ax.plot([shank_x, foot_x], [shank_y, foot_y], color=color, linewidth=3, alpha=0.8)
                
                # Draw joints
                ax.plot(hip_x, hip_y, 'ko', markersize=6)
                ax.plot(thigh_x, thigh_y, 'ko', markersize=6)
                ax.plot(shank_x, shank_y, 'ko', markersize=6)
        
        # Draw pelvis/torso
        ax.plot([-0.3, 0.3], [1.0, 1.0], 'k-', linewidth=4)
        ax.plot([0, 0], [1.0, 1.5], 'k-', linewidth=4)
        
        # Ground line
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        
        # Formatting
        ax.set_xlim(-0.8, 0.8)
        ax.set_ylim(-0.2, 1.6)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(f'{config.title()} Configuration')
        ax.legend(loc='upper right', fontsize=8)
        
        # Add angle annotations
        if side in angles:
            for i, (joint, angle_range) in enumerate(angles['left'].items()):
                angle_val = angle_range[0 if config == 'min' else 1]
                ax.text(-0.7, 1.4 - i*0.1, f'{joint.title()}: {np.degrees(angle_val):.0f}°', 
                       fontsize=8, ha='left')
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


def generate_all_phase_images(validation_data: Dict, output_dir: str) -> List[str]:
    """
    Generate phase range validation images for all tasks and phases.
    
    Args:
        validation_data: Parsed validation data
        output_dir: Directory to save images
        
    Returns:
        List of generated file paths
    """
    generated_files = []
    phases = [0, 25, 50, 75]  # New phase system
    
    for task_name, task_data in validation_data.items():
        task_type = get_task_classification(task_name)
        task_label = task_name.replace('_', ' ').title()
        
        for phase in phases:
            if phase in task_data:
                # Extract joint angles for this phase
                joint_angles = {}
                for joint_var, ranges in task_data[phase].items():
                    if 'flexion_angle' in joint_var:
                        joint_angles[joint_var] = (ranges['min'], ranges['max'])
                
                if joint_angles:
                    # Phase labels
                    if task_type == 'gait':
                        if phase == 0:
                            phase_label = "Heel Strike"
                        elif phase == 25:
                            phase_label = "Mid-Stance"
                        elif phase == 50:
                            phase_label = "Toe-Off"
                        elif phase == 75:
                            phase_label = "Mid-Swing"
                    else:  # bilateral
                        if phase == 0:
                            phase_label = "Initial"
                        elif phase == 25:
                            phase_label = "Early Phase"
                        elif phase == 50:
                            phase_label = "Mid Phase"
                        elif phase == 75:
                            phase_label = "Late Phase"
                    
                    # Generate image
                    title = f'{task_label} - Phase {phase}% ({phase_label})'
                    filename = f'{task_name}_phase_{phase:02d}_range.png'
                    save_path = os.path.join(output_dir, filename)
                    
                    generate_stick_figure(joint_angles, title, save_path, task_type)
                    generated_files.append(save_path)
    
    return generated_files


def main():
    """Main function to generate phase range validation images."""
    
    parser = argparse.ArgumentParser(
        description='Generate phase range validation images for v5.0 system'
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
        
    except Exception as e:
        print(f"Error parsing validation file: {e}")
        return 1
    
    # Generate all phase range images
    print(f"\nGenerating phase range images to: {args.output_dir}")
    
    try:
        generated_files = generate_all_phase_images(validation_data, args.output_dir)
        
        print(f"\n✅ Successfully generated {len(generated_files)} phase range images!")
        print(f"\nGenerated {len(generated_files)} individual phase range images")
        print("Files generated for phases: 0%, 25%, 50%, 75% (new v5.0 system)")
        
        # Show breakdown by task
        tasks = set(os.path.basename(f).split('_phase_')[0] for f in generated_files)
        print(f"Tasks covered: {len(tasks)} ({', '.join(sorted(tasks))})")
        
    except Exception as e:
        print(f"Error generating images: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())