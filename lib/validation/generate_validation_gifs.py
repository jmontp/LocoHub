#!/usr/bin/env python3
"""
Validation GIF Generation

Created: 2025-06-11 with user permission
Purpose: Generate animated stick figure visualizations for biomechanical validation

Intent:
Consolidated GIF generation for validation purposes using the new standard specification.
Creates animated stick figures showing joint kinematics for visual validation of dataset quality.
Supports both time-indexed and phase-indexed data with automatic format detection.

Key Features:
- Stick figure animation with joint angles and moments
- Automatic dataset format detection (time vs phase)
- Standard variable naming support
- Parallel processing for multiple datasets
- Integration with validation system
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Arc, FancyArrowPatch
import argparse
import multiprocessing
from pathlib import Path

# Add source directory to path for library imports
sys.path.append(str(Path(__file__).parent.parent))

def calculate_joint_positions(hip_angle, knee_angle, ankle_angle, segment_lengths):
    """Calculate joint positions for stick figure animation."""
    # Hip position (fixed at origin for now)
    hip_x, hip_y = 0, 0
    
    # Calculate thigh end position (knee)
    thigh_length = segment_lengths['thigh']
    knee_x = hip_x + thigh_length * np.sin(hip_angle)
    knee_y = hip_y - thigh_length * np.cos(hip_angle)
    
    # Calculate shank end position (ankle)
    shank_length = segment_lengths['shank']
    total_knee_angle = hip_angle + knee_angle
    ankle_x = knee_x + shank_length * np.sin(total_knee_angle)
    ankle_y = knee_y - shank_length * np.cos(total_knee_angle)
    
    # Calculate foot end position
    foot_length = segment_lengths['foot']
    total_ankle_angle = total_knee_angle + ankle_angle
    foot_x = ankle_x + foot_length * np.sin(total_ankle_angle)
    foot_y = ankle_y - foot_length * np.cos(total_ankle_angle)
    
    return (hip_x, hip_y), (knee_x, knee_y), (ankle_x, ankle_y), (foot_x, foot_y)

def create_stick_figure_animation_from_locomotion_data(loco_data, subject, task, segment_lengths, output_path):
    """Create animated stick figure using LocomotionData library."""
    try:
        # Import LocomotionData library
        from lib.core.locomotion_analysis import LocomotionData
        
        # Get angle features for this subject-task
        angle_features = [f for f in loco_data.ANGLE_FEATURES if f in loco_data.features]
        
        if len(angle_features) < 6:
            print(f"Warning: Insufficient angle features ({len(angle_features)}/6) for {subject}-{task}")
            return False
        
        # Get 3D data for this subject-task
        data_3d, feature_names = loco_data.get_cycles(subject, task, angle_features)
        
        if data_3d is None or data_3d.shape[0] == 0:
            print(f"Warning: No cycle data for {subject}-{task}")
            return False
        
        # Use first cycle for animation (can be made configurable)
        cycle_data = data_3d[0, :, :]  # Shape: (150, n_features)
        n_frames = cycle_data.shape[0]
        
        # Map features to animation variables
        feature_mapping = {}
        for i, feature in enumerate(feature_names):
            if 'hip_flexion_angle_ipsi' in feature:
                feature_mapping['hip_ipsi'] = i
            elif 'hip_flexion_angle_contra' in feature:
                feature_mapping['hip_contra'] = i
            elif 'knee_flexion_angle_ipsi' in feature:
                feature_mapping['knee_ipsi'] = i
            elif 'knee_flexion_angle_contra' in feature:
                feature_mapping['knee_contra'] = i
            elif 'ankle_flexion_angle_ipsi' in feature:
                feature_mapping['ankle_ipsi'] = i
            elif 'ankle_flexion_angle_contra' in feature:
                feature_mapping['ankle_contra'] = i
        
        required_joints = ['hip_ipsi', 'knee_ipsi', 'ankle_ipsi', 'hip_contra', 'knee_contra', 'ankle_contra']
        missing_joints = [j for j in required_joints if j not in feature_mapping]
        
        if missing_joints:
            print(f"Warning: Missing joint mappings {missing_joints} for {subject}-{task}")
            return False
        
        return create_stick_figure_animation(cycle_data, feature_mapping, segment_lengths, output_path, subject, task)
        
    except Exception as e:
        print(f"Error creating animation from LocomotionData: {e}")
        return False

def create_stick_figure_animation(cycle_data, feature_mapping, segment_lengths, output_path, subject, task):
    """Create animated stick figure for biomechanical validation using 3D cycle data."""
    
    n_frames = cycle_data.shape[0]
    if n_frames < 10:
        print(f"Warning: Too few frames ({n_frames}) for {subject}-{task}")
        return False
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(-3, 3)
    ax.set_ylim(-4, 1)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title(f'{subject} - {task} - Kinematic Validation')
    
    # Initialize line objects for both legs
    ipsi_lines = ax.plot([], [], 'b-', linewidth=3, label='Ipsilateral')[0]
    contra_lines = ax.plot([], [], 'r-', linewidth=3, label='Contralateral')[0]
    ax.legend()
    
    def animate(frame):
        """Animation function for each frame."""
        try:
            # Get angles for current frame from cycle data
            hip_ipsi = cycle_data[frame, feature_mapping['hip_ipsi']]
            knee_ipsi = cycle_data[frame, feature_mapping['knee_ipsi']]
            ankle_ipsi = cycle_data[frame, feature_mapping['ankle_ipsi']]
            
            hip_contra = cycle_data[frame, feature_mapping['hip_contra']]
            knee_contra = cycle_data[frame, feature_mapping['knee_contra']]
            ankle_contra = cycle_data[frame, feature_mapping['ankle_contra']]
            
            # Calculate positions for ipsilateral leg
            positions_ipsi = calculate_joint_positions(hip_ipsi, knee_ipsi, ankle_ipsi, segment_lengths)
            
            # Calculate positions for contralateral leg  
            positions_contra = calculate_joint_positions(hip_contra, knee_contra, ankle_contra, segment_lengths)
            
            # Update line data for ipsilateral leg
            x_ipsi = [pos[0] for pos in positions_ipsi]
            y_ipsi = [pos[1] for pos in positions_ipsi]
            ipsi_lines.set_data(x_ipsi, y_ipsi)
            
            # Update line data for contralateral leg (offset slightly)
            x_contra = [pos[0] + 0.2 for pos in positions_contra]  # Small offset for visibility
            y_contra = [pos[1] for pos in positions_contra]
            contra_lines.set_data(x_contra, y_contra)
            
            return ipsi_lines, contra_lines
            
        except Exception as e:
            print(f"Animation error at frame {frame}: {e}")
            return ipsi_lines, contra_lines
    
    # Create animation
    anim = FuncAnimation(fig, animate, frames=n_frames, interval=50, blit=True, repeat=True)
    
    # Save as GIF
    try:
        anim.save(output_path, writer='pillow', fps=20)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving GIF for {subject}-{task}: {e}")
        plt.close(fig)
        return False

def process_dataset_config(config):
    """Process a single dataset configuration using LocomotionData library."""
    dataset_file = config['file']
    subject_task_pairs = config['subject_task_pairs']
    
    print(f"Processing dataset: {dataset_file}")
    
    try:
        # Import LocomotionData library
        from lib.core.locomotion_analysis import LocomotionData
        
        # Load dataset using LocomotionData
        loco_data = LocomotionData(dataset_file)
        
        # Define segment lengths
        segment_lengths = {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5, 'torso': 2.0}
        
        # Create output directory
        output_dir = Path("validation_gifs")
        output_dir.mkdir(exist_ok=True)
        
        # Process each subject-task pair
        for subject, task, jump_frames in subject_task_pairs:
            print(f"  Processing {subject} - {task}")
            
            # Check if subject and task exist in dataset
            if subject not in loco_data.subjects:
                print(f"    Warning: Subject {subject} not found in dataset")
                continue
            
            if task not in loco_data.tasks:
                print(f"    Warning: Task {task} not found in dataset")
                continue
            
            # Create output filename
            safe_subject = subject.replace('/', '_').replace(' ', '_')
            safe_task = task.replace('/', '_').replace(' ', '_')
            output_file = output_dir / f"{safe_subject}_{safe_task}_validation.gif"
            
            # Generate animation using LocomotionData
            success = create_stick_figure_animation_from_locomotion_data(
                loco_data, subject, task, segment_lengths, output_file
            )
            
            if success:
                print(f"    ✓ Generated: {output_file}")
            else:
                print(f"    ✗ Failed: {subject} - {task}")
                
    except Exception as e:
        print(f"Error processing dataset {dataset_file}: {e}")

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description='Generate validation GIFs for biomechanical datasets')
    parser.add_argument('-f', '--file', type=str, help='Path to specific parquet file')
    parser.add_argument('-s', '--subject', type=str, help='Specific subject name')
    parser.add_argument('-t', '--task', type=str, help='Specific task name')
    parser.add_argument('-j', '--jump-frames', type=int, default=0, help='Skip initial frames')
    parser.add_argument('--parallel', action='store_true', help='Process datasets in parallel')
    parser.add_argument('--all-datasets', action='store_true', help='Process all configured datasets')
    
    args = parser.parse_args()
    
    # Dataset configurations - updated for new standard spec
    dataset_configs = [
        {
            'file': 'converted_datasets/gtech_2023_time.parquet',
            'subject_task_pairs': [
                ('AB01', 'normal_walk', 1000),
                ('AB02', 'jump', 1000),
                ('AB03', 'normal_walk', 1000),
                ('AB05', 'stairs', 1000),
                ('AB06', 'sit_to_stand', 1000)
            ]
        },
        {
            'file': 'converted_datasets/umich_2021_phase.parquet', 
            'subject_task_pairs': [
                ('S01', 'level_walking', 0),
                ('S02', 'incline_walking', 0),
                ('S03', 'decline_walking', 0)
            ]
        }
    ]
    
    if args.file and args.subject and args.task:
        # Process single subject-task pair
        config = {
            'file': args.file,
            'subject_task_pairs': [(args.subject, args.task, args.jump_frames)]
        }
        process_dataset_config(config)
        
    elif args.all_datasets:
        # Process all configured datasets
        if args.parallel:
            with multiprocessing.Pool() as pool:
                pool.map(process_dataset_config, dataset_configs)
        else:
            for config in dataset_configs:
                process_dataset_config(config)
    else:
        print("Usage examples:")
        print("  # Single subject-task:")
        print("  python generate_validation_gifs.py -f dataset.parquet -s SUB01 -t level_walking")
        print("  # All datasets:")
        print("  python generate_validation_gifs.py --all-datasets")
        print("  # All datasets in parallel:")
        print("  python generate_validation_gifs.py --all-datasets --parallel")

if __name__ == "__main__":
    main()