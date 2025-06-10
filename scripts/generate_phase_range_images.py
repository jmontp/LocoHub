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
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Extract angles for both legs using ipsi/contra convention
    angles = {}
    for side in ['ipsi', 'contra']:
        angles[side] = {}
        for joint in ['hip', 'knee', 'ankle']:
            joint_key = f'{joint}_flexion_angle_{side}'
            if joint_key in joint_angles:
                angles[side][joint] = joint_angles[joint_key]
            else:
                # Raise explicit error instead of using defaults
                available_keys = list(joint_angles.keys())
                raise KeyError(f"Required joint angle '{joint_key}' not found in validation data. "
                              f"Available keys: {available_keys}")
    
    # Generate stick figures for min, average, and max configurations
    for config, alpha, linestyle in [('min', 0.1, '--'), ('avg', 1.0, '-'), ('max', 0.1, '-')]:
        # Draw both legs
        for side, color in [('ipsi', 'blue'), ('contra', 'red')]:
            if side in angles:
                # Calculate angles based on configuration
                if config == 'min':
                    hip_angle = angles[side]['hip'][0]
                    knee_angle = angles[side]['knee'][0]
                    ankle_angle = angles[side]['ankle'][0]
                elif config == 'max':
                    hip_angle = angles[side]['hip'][1]
                    knee_angle = angles[side]['knee'][1]
                    ankle_angle = angles[side]['ankle'][1]
                else:  # avg
                    hip_angle = (angles[side]['hip'][0] + angles[side]['hip'][1]) / 2
                    knee_angle = (angles[side]['knee'][0] + angles[side]['knee'][1]) / 2
                    ankle_angle = (angles[side]['ankle'][0] + angles[side]['ankle'][1]) / 2
                
                # Forward kinematics - frontal plane view (looking perpendicular to person)
                # Both legs originate from EXACTLY the same hip position (true frontal plane)
                
                # Hip position (both legs at identical position - no lateral offset)
                hip_x = 0.0  # Identical position for both legs
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
                
                # Foot segment with anatomical reference (0° = foot flat on ground)
                # Add 90° offset so 0° ankle angle = foot horizontal (flat on ground)
                foot_length = 0.15
                # Ankle angle: 0° = foot flat, positive = dorsiflexion (toes up), negative = plantarflexion
                foot_angle_from_horizontal = ankle_angle  # Direct ankle angle interpretation
                foot_angle_from_vertical = shank_angle_from_vertical + foot_angle_from_horizontal + np.pi/2
                foot_x = shank_x + foot_length * np.sin(foot_angle_from_vertical)
                foot_y = shank_y - foot_length * np.cos(foot_angle_from_vertical)
                
                # Create label only for average configuration to avoid legend clutter
                leg_display_name = 'Ipsilateral' if side == 'ipsi' else 'Contralateral'
                leg_label = f'{leg_display_name} Leg' if config == 'avg' else None
                
                # Draw leg segments with varying alpha and line style (no lateral offset)
                ax.plot([hip_x, thigh_x], [hip_y, thigh_y], 
                       color=color, linewidth=3, alpha=alpha, linestyle=linestyle, label=leg_label)
                ax.plot([thigh_x, shank_x], [thigh_y, shank_y], 
                       color=color, linewidth=3, alpha=alpha, linestyle=linestyle)
                ax.plot([shank_x, foot_x], [shank_y, foot_y], 
                       color=color, linewidth=3, alpha=alpha, linestyle=linestyle)
                
                # Draw joints (only for average to avoid clutter)
                if config == 'avg':
                    ax.plot(hip_x, hip_y, 'ko', markersize=6)
                    ax.plot(thigh_x, thigh_y, 'ko', markersize=6)
                    ax.plot(shank_x, shank_y, 'ko', markersize=6)
                    ax.plot(foot_x, foot_y, 'ko', markersize=4)  # Smaller for foot
    
    # Draw pelvis/torso centered (both legs attach here)
    ax.plot([-0.15, 0.15], [1.0, 1.0], 'k-', linewidth=4, label='Pelvis')
    ax.plot([0, 0], [1.0, 1.5], 'k-', linewidth=4)
    
    # Add walking direction arrow
    arrow_y = 1.4
    arrow_start_x = -0.4
    arrow_end_x = 0.4
    ax.annotate('', xy=(arrow_end_x, arrow_y), xytext=(arrow_start_x, arrow_y),
               arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    ax.text(0, arrow_y + 0.05, 'Walking Direction', ha='center', va='bottom', 
           fontsize=10, color='green', fontweight='bold')
    
    # Ground line
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5, label='Ground')
    
    # Add angle annotations showing min/avg/max ranges
    for i, (joint, angle_range) in enumerate(angles['ipsi'].items()):
        min_val = np.degrees(angle_range[0])
        max_val = np.degrees(angle_range[1])
        avg_val = (min_val + max_val) / 2
        ax.text(-0.7, 1.3 - i*0.08, 
               f'{joint.title()}: {min_val:.0f}° / {avg_val:.0f}° / {max_val:.0f}°', 
               fontsize=8, ha='left')
    
    # Add legend explanation
    ax.text(-0.7, 1.0, 'Range: Min / Avg / Max\nAvg: solid line\nMin: dashed (10% alpha)\nMax: solid (10% alpha)', 
           fontsize=7, ha='left', va='top', 
           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
    
    # Formatting
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(-0.2, 1.6)
    ax.set_aspect('equal')
    
    # Remove axes since cartesian coordinates don't have meaningful biomechanical units
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    ax.set_title('Joint Angle Range Visualization\n(Frontal Plane View)', fontsize=12)
    ax.legend(loc='upper right', fontsize=8)
    
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