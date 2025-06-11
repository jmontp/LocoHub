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

# Add validation module path
sys.path.append(str(Path(__file__).parent))

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

def detect_variable_names(df):
    """Detect variable naming convention and return appropriate column names."""
    columns = df.columns.tolist()
    
    # Try standard naming convention first
    angle_patterns = {
        'hip_ipsi': ['hip_flexion_angle_ipsi_rad'],
        'knee_ipsi': ['knee_flexion_angle_ipsi_rad'], 
        'ankle_ipsi': ['ankle_flexion_angle_ipsi_rad'],
        'hip_contra': ['hip_flexion_angle_contra_rad'],
        'knee_contra': ['knee_flexion_angle_contra_rad'],
        'ankle_contra': ['ankle_flexion_angle_contra_rad']
    }
    
    # Try legacy naming conventions
    legacy_patterns = {
        'hip_ipsi': ['hip_flexion_angle_right_rad', 'hip_angle_right', 'hip_flexion_angle_left_rad'],
        'knee_ipsi': ['knee_flexion_angle_right_rad', 'knee_angle_right', 'knee_flexion_angle_left_rad'],
        'ankle_ipsi': ['ankle_flexion_angle_right_rad', 'ankle_angle_right', 'ankle_flexion_angle_left_rad'],
        'hip_contra': ['hip_flexion_angle_left_rad', 'hip_angle_left', 'hip_flexion_angle_right_rad'],
        'knee_contra': ['knee_flexion_angle_left_rad', 'knee_angle_left', 'knee_flexion_angle_right_rad'],
        'ankle_contra': ['ankle_flexion_angle_left_rad', 'ankle_angle_left', 'ankle_flexion_angle_right_rad']
    }
    
    detected_vars = {}
    
    # Try standard patterns first
    for joint, patterns in angle_patterns.items():
        for pattern in patterns:
            if pattern in columns:
                detected_vars[joint] = pattern
                break
    
    # Fall back to legacy patterns if needed
    for joint, patterns in legacy_patterns.items():
        if joint not in detected_vars:
            for pattern in patterns:
                if pattern in columns:
                    detected_vars[joint] = pattern
                    break
    
    return detected_vars

def create_stick_figure_animation(df, subject, task, segment_lengths, output_path):
    """Create animated stick figure for biomechanical validation."""
    
    # Detect variable names
    vars_dict = detect_variable_names(df)
    required_vars = ['hip_ipsi', 'knee_ipsi', 'ankle_ipsi', 'hip_contra', 'knee_contra', 'ankle_contra']
    
    missing_vars = [var for var in required_vars if var not in vars_dict]
    if missing_vars:
        print(f"Warning: Missing variables {missing_vars} for {subject}-{task}")
        return False
    
    # Extract angle data
    angles_data = {}
    for joint in required_vars:
        col_name = vars_dict[joint]
        angles_data[joint] = df[col_name].values
    
    # Determine animation length
    n_frames = len(df)
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
            # Get angles for current frame
            hip_ipsi = angles_data['hip_ipsi'][frame]
            knee_ipsi = angles_data['knee_ipsi'][frame] 
            ankle_ipsi = angles_data['ankle_ipsi'][frame]
            
            hip_contra = angles_data['hip_contra'][frame]
            knee_contra = angles_data['knee_contra'][frame]
            ankle_contra = angles_data['ankle_contra'][frame]
            
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
    """Process a single dataset configuration."""
    dataset_file = config['file']
    subject_task_pairs = config['subject_task_pairs']
    
    print(f"Processing dataset: {dataset_file}")
    
    try:
        # Load dataset
        df = pd.read_parquet(dataset_file)
        
        # Define segment lengths
        segment_lengths = {'thigh': 1.0, 'shank': 1.0, 'foot': 0.5, 'torso': 2.0}
        
        # Create output directory
        output_dir = Path("validation_gifs")
        output_dir.mkdir(exist_ok=True)
        
        # Process each subject-task pair
        for subject, task, jump_frames in subject_task_pairs:
            print(f"  Processing {subject} - {task}")
            
            # Filter data
            task_data = df[(df['subject'] == subject) & (df['task'] == task)].copy()
            
            if len(task_data) == 0:
                print(f"    Warning: No data found for {subject} - {task}")
                continue
            
            # Skip initial frames if requested
            if jump_frames > 0:
                task_data = task_data.iloc[jump_frames:].reset_index(drop=True)
            
            # Create output filename
            safe_subject = subject.replace('/', '_').replace(' ', '_')
            safe_task = task.replace('/', '_').replace(' ', '_')
            output_file = output_dir / f"{safe_subject}_{safe_task}_validation.gif"
            
            # Generate animation
            success = create_stick_figure_animation(task_data, subject, task, segment_lengths, output_file)
            
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