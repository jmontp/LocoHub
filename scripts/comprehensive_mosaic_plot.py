#!/usr/bin/env python3
"""
Create comprehensive mosaic plots with ALL biomechanical features.
Optimized for large numbers of features.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
import argparse
import sys

POINTS_PER_CYCLE = 150


def create_comprehensive_plot(df, task, subject_col='subject', task_col='task', 
                            output_dir='plots'):
    """Create a comprehensive plot with all key biomechanical features."""
    
    # Define feature groups
    feature_groups = {
        'Right Angles': ['hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'],
        'Right Velocities': ['hip_flexion_velocity_right_rad_s', 'knee_flexion_velocity_right_rad_s', 'ankle_flexion_velocity_right_rad_s'],
        'Right Moments': ['hip_flexion_moment_right_Nm', 'knee_flexion_moment_right_Nm', 'ankle_flexion_moment_right_Nm'],
        'Left Angles': ['hip_flexion_angle_left_rad', 'knee_flexion_angle_left_rad', 'ankle_flexion_angle_left_rad'],
        'Left Velocities': ['hip_flexion_velocity_left_rad_s', 'knee_flexion_velocity_left_rad_s', 'ankle_flexion_velocity_left_rad_s'],
        'Left Moments': ['hip_flexion_moment_left_Nm', 'knee_flexion_moment_left_Nm', 'ankle_flexion_moment_left_Nm'],
        'Frontal Angles R': ['hip_adduction_angle_right_rad', 'ankle_inversion_angle_right_rad'],
        'Frontal Angles L': ['hip_adduction_angle_left_rad', 'ankle_inversion_angle_left_rad'],
        'Transverse Angles': ['hip_rotation_angle_right_rad', 'hip_rotation_angle_left_rad']
    }
    
    # Filter for this task
    task_df = df[df[task_col] == task]
    subjects = sorted(task_df[subject_col].unique())
    
    if not subjects:
        print(f"No subjects found for task '{task}'")
        return
    
    # Create large figure with subplots for each feature group
    n_groups = len(feature_groups)
    n_subjects = len(subjects)
    
    fig = plt.figure(figsize=(24, 3 * n_subjects))
    gs = gridspec.GridSpec(n_subjects, n_groups, hspace=0.3, wspace=0.3,
                          top=0.96, bottom=0.02, left=0.04, right=0.98)
    
    phase_x = np.linspace(0, 100, POINTS_PER_CYCLE)
    
    # Plot each subject
    for i, subject in enumerate(subjects):
        subj_task_df = task_df[task_df[subject_col] == subject]
        
        if len(subj_task_df) == 0 or len(subj_task_df) % POINTS_PER_CYCLE != 0:
            continue
            
        n_cycles = len(subj_task_df) // POINTS_PER_CYCLE
        
        # Get all features we need for this subject
        all_group_features = []
        for group_features in feature_groups.values():
            all_group_features.extend(group_features)
        
        # Filter to valid features
        valid_features = [f for f in all_group_features if f in subj_task_df.columns]
        
        if not valid_features:
            continue
            
        # EFFICIENT 3D RESHAPE: Extract all features at once
        feature_data = subj_task_df[valid_features].values
        data_3d = feature_data.reshape(n_cycles, POINTS_PER_CYCLE, len(valid_features))
        
        # Create mapping of feature names to indices
        feature_to_idx = {f: i for i, f in enumerate(valid_features)}
        
        # Plot each feature group
        for j, (group_name, features) in enumerate(feature_groups.items()):
            ax = fig.add_subplot(gs[i, j])
            
            # Plot each feature in the group
            colors = plt.cm.tab10(np.linspace(0, 1, len(features)))
            
            for k, (feature, color) in enumerate(zip(features, colors)):
                if feature not in feature_to_idx:
                    continue
                
                # Extract data from 3D array
                feat_idx = feature_to_idx[feature]
                data = data_3d[:, :, feat_idx]
                
                # Calculate mean and std
                mean_curve = np.mean(data, axis=0)
                std_curve = np.std(data, axis=0)
                
                # Plot mean with shaded std
                label = feature.split('_')[0] + '_' + feature.split('_')[-1]
                ax.plot(phase_x, mean_curve, color=color, linewidth=2, label=label)
                ax.fill_between(phase_x, mean_curve - std_curve, mean_curve + std_curve,
                              alpha=0.2, color=color)
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.grid(True, alpha=0.3)
            
            if i == 0:
                ax.set_title(group_name, fontsize=10, fontweight='bold')
            if i == n_subjects - 1:
                ax.set_xlabel('Gait Cycle (%)', fontsize=8)
            if j == 0:
                ax.set_ylabel(f'{subject}\n\nValue', fontsize=8)
            
            # Legend only for first subject
            if i == 0:
                ax.legend(loc='upper right', fontsize=6, ncol=1)
            
            # Set reasonable y-limits based on feature type
            if 'Angle' in group_name:
                ax.set_ylim(-90, 90)
            elif 'Velocit' in group_name:
                ax.set_ylim(-500, 500)
            elif 'Torque' in group_name:
                ax.set_ylim(-150, 150)
    
    # Main title
    fig.suptitle(f'Comprehensive Biomechanics: {task} ({n_subjects} subjects)', 
                fontsize=16, fontweight='bold')
    
    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = output_path / f'{task}_comprehensive.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f"Saved: {filename}")
    return filename


def create_super_comprehensive_plot(df, task, subject_col='subject', task_col='task', 
                                  output_dir='plots'):
    """Create a plot with ALL available features."""
    
    # Get all biomechanical features
    exclude_cols = ['subject', 'task', 'task_info', 'activity_number', 'phase', 
                    'time_r', 'time_l', 'is_reconstructed_r', 'is_reconstructed_l',
                    'grf_r', 'grf_l', 'phase_r', 'phase_l']
    
    all_features = [col for col in df.columns if col not in exclude_cols 
                    and not col.startswith('grf_') 
                    and not col.endswith('_x') 
                    and not col.endswith('_y') 
                    and not col.endswith('_z')
                    and not 'COP' in col.upper()
                    and not 'Force' in col]
    
    # Filter for main biomechanical variables
    main_features = [f for f in all_features if any(x in f for x in ['angle', 'vel', 'torque', 'moment'])]
    
    print(f"Plotting {len(main_features)} features for {task}")
    
    # Filter for this task
    task_df = df[df[task_col] == task]
    subjects = sorted(task_df[subject_col].unique())[:3]  # Limit to 3 subjects for space
    
    if not subjects:
        return
    
    # Calculate grid dimensions
    n_features = len(main_features)
    n_cols = 6  # 6 features per row
    n_rows = int(np.ceil(n_features / n_cols))
    
    # Create figure for each subject
    for subject in subjects:
        subj_task_df = task_df[task_df[subject_col] == subject]
        
        if len(subj_task_df) == 0 or len(subj_task_df) % POINTS_PER_CYCLE != 0:
            continue
            
        n_cycles = len(subj_task_df) // POINTS_PER_CYCLE
        
        # Filter to valid features for this subject
        valid_features = [f for f in main_features if f in subj_task_df.columns]
        
        if not valid_features:
            continue
            
        # EFFICIENT 3D RESHAPE: Extract all features at once
        feature_data = subj_task_df[valid_features].values
        data_3d = feature_data.reshape(n_cycles, POINTS_PER_CYCLE, len(valid_features))
        
        # Create mapping
        feature_to_idx = {f: i for i, f in enumerate(valid_features)}
        
        fig = plt.figure(figsize=(3 * n_cols, 2 * n_rows))
        gs = gridspec.GridSpec(n_rows, n_cols, hspace=0.4, wspace=0.3,
                              top=0.95, bottom=0.05, left=0.05, right=0.98)
        
        phase_x = np.linspace(0, 100, POINTS_PER_CYCLE)
        
        # Plot each feature
        for idx, feature in enumerate(main_features):
            row = idx // n_cols
            col = idx % n_cols
            
            if row >= n_rows:
                break
                
            ax = fig.add_subplot(gs[row, col])
            
            if feature not in feature_to_idx:
                ax.text(0.5, 0.5, 'N/A', ha='center', va='center')
                ax.set_title(feature[:15], fontsize=6)
                continue
            
            # Extract data from 3D array
            feat_idx = feature_to_idx[feature]
            data = data_3d[:, :, feat_idx]
            
            # Plot mean and individual cycles
            mean_curve = np.mean(data, axis=0)
            
            # Plot a few individual cycles
            for i in range(min(5, n_cycles)):
                ax.plot(phase_x, data[i], 'gray', alpha=0.2, linewidth=0.5)
            
            # Plot mean
            ax.plot(phase_x, mean_curve, 'b-', linewidth=1.5)
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.set_title(feature[:20], fontsize=6)
            ax.tick_params(labelsize=5)
            
            if row == n_rows - 1:
                ax.set_xlabel('Cycle %', fontsize=5)
        
        # Main title
        fig.suptitle(f'ALL Features: {subject} - {task} ({n_cycles} cycles)', 
                    fontsize=12, fontweight='bold')
        
        # Save
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = output_path / f'{task}_{subject}_all_features.png'
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        print(f"Saved: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive biomechanics plots')
    parser.add_argument('--input_parquet', type=str, required=True)
    parser.add_argument('--output_dir', type=str, default='plots_comprehensive')
    parser.add_argument('--mode', type=str, choices=['grouped', 'all'], default='grouped',
                       help='grouped: organized by feature type, all: every feature')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading {args.input_parquet}...")
    df = pd.read_parquet(args.input_parquet)
    print(f"Loaded {len(df)} rows")
    
    # Get unique tasks
    tasks = df['task'].unique()
    print(f"Found {len(tasks)} tasks")
    
    # Create plots for each task
    for task in tasks:
        print(f"\nProcessing {task}...")
        if args.mode == 'grouped':
            create_comprehensive_plot(df, task, output_dir=args.output_dir)
        else:
            create_super_comprehensive_plot(df, task, output_dir=args.output_dir)
    
    print(f"\nDone! All plots saved to {args.output_dir}/")


if __name__ == '__main__':
    main()