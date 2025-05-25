#!/usr/bin/env python3
"""
Efficient mosaic plot generator using 3D array structure.
This implementation uses the (num_cycles, num_phase_points, num_features) structure
for better performance when processing multiple features.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
import argparse
import time


POINTS_PER_CYCLE = 150


def efficient_reshape_3d(df, subject, task, features, subject_col='subject', 
                        task_col='task', points_per_cycle=POINTS_PER_CYCLE):
    """
    Efficiently reshape data into 3D array (num_cycles, num_phase_points, num_features).
    
    Returns:
        data_3d: 3D numpy array of shape (n_cycles, 150, n_features)
        feature_names: List of feature names (same order as last dimension)
        valid_mask: Boolean array indicating which features were successfully extracted
    """
    # Filter for specific subject and task
    mask = (df[subject_col] == subject) & (df[task_col] == task)
    subset = df[mask]
    
    if len(subset) == 0:
        return None, features, np.zeros(len(features), dtype=bool)
    
    # Get number of cycles
    n_points = len(subset)
    n_cycles = n_points // points_per_cycle
    
    if n_points % points_per_cycle != 0:
        print(f"Warning: {n_points} points not divisible by {points_per_cycle}")
        return None, features, np.zeros(len(features), dtype=bool)
    
    # Check which features exist
    valid_features = [f for f in features if f in subset.columns]
    valid_mask = np.array([f in subset.columns for f in features])
    
    if not valid_features:
        return None, features, valid_mask
    
    # Extract all valid features at once as 2D array
    feature_data = subset[valid_features].values  # Shape: (n_points, n_valid_features)
    
    # Reshape to 3D: (n_cycles * 150, n_features) → (n_cycles, 150, n_features)
    data_3d_valid = feature_data.reshape(n_cycles, points_per_cycle, len(valid_features))
    
    # Create full array with NaN for missing features
    data_3d = np.full((n_cycles, points_per_cycle, len(features)), np.nan)
    data_3d[:, :, valid_mask] = data_3d_valid
    
    return data_3d, features, valid_mask


def validate_cycles_3d(data_3d, feature_names):
    """
    Validate all cycles using the 3D array structure.
    Returns boolean array of shape (n_cycles,) indicating valid cycles.
    """
    n_cycles, n_phases, n_features = data_3d.shape
    valid_cycles = np.ones(n_cycles, dtype=bool)
    
    # Define reasonable ranges for each feature type
    for i, feature in enumerate(feature_names):
        feature_data = data_3d[:, :, i]  # Extract all cycles for this feature
        
        if np.all(np.isnan(feature_data)):
            continue
            
        # Check ranges based on feature type
        if 'angle' in feature:
            # Angles should be between -180 and 180 degrees
            out_of_range = np.any((feature_data < -180) | (feature_data > 180), axis=1)
            valid_cycles &= ~out_of_range
            
            # Check for large discontinuities
            diffs = np.diff(feature_data, axis=1)
            large_jumps = np.any(np.abs(diffs) > 30, axis=1)  # 30 degree jumps
            valid_cycles &= ~large_jumps
            
        elif 'torque' in feature:
            # Torques should be reasonable (mass-normalized)
            out_of_range = np.any(np.abs(feature_data) > 10, axis=1)  # 10 Nm/kg is very high
            valid_cycles &= ~out_of_range
    
    return valid_cycles


def create_efficient_mosaic_plot(df, task, feature_groups, subject_col='subject', 
                               task_col='task', phase_col='phase', output_dir='plots_3d',
                               show_validation=True):
    """
    Create mosaic plot using efficient 3D array operations.
    """
    # Filter for this task
    task_df = df[df[task_col] == task]
    subjects = sorted(task_df[subject_col].unique())
    
    if not subjects:
        print(f"No subjects found for task: {task}")
        return
    
    # Create figure
    n_subjects = len(subjects)
    n_groups = len(feature_groups)
    
    fig = plt.figure(figsize=(4 * n_groups, 3 * n_subjects))
    gs = gridspec.GridSpec(n_subjects, n_groups, hspace=0.3, wspace=0.3)
    
    # Phase x-axis
    phase_x = np.linspace(0, 100, POINTS_PER_CYCLE)
    
    # Process each subject
    for subj_idx, subject in enumerate(subjects):
        # Get all features we need
        all_features = []
        for group_features in feature_groups.values():
            all_features.extend(group_features)
        
        # Efficient 3D reshape for all features at once
        start_time = time.time()
        data_3d, feature_names, valid_mask = efficient_reshape_3d(
            df, subject, task, all_features, subject_col, task_col
        )
        reshape_time = time.time() - start_time
        
        if data_3d is None:
            continue
            
        n_cycles = data_3d.shape[0]
        print(f"{subject}: Reshaped {n_cycles} cycles x {len(all_features)} features in {reshape_time*1000:.1f}ms")
        
        # Validate cycles if requested
        if show_validation:
            valid_cycles = validate_cycles_3d(data_3d, feature_names)
            n_valid = np.sum(valid_cycles)
            print(f"  Valid cycles: {n_valid}/{n_cycles} ({n_valid/n_cycles*100:.1f}%)")
        else:
            valid_cycles = np.ones(n_cycles, dtype=bool)
        
        # Plot each feature group
        feature_idx = 0
        for group_idx, (group_name, group_features) in enumerate(feature_groups.items()):
            ax = fig.add_subplot(gs[subj_idx, group_idx])
            
            # Extract data for this group using slicing
            group_size = len(group_features)
            group_data = data_3d[:, :, feature_idx:feature_idx + group_size]
            feature_idx += group_size
            
            # Plot each feature in the group
            for feat_idx, feature in enumerate(group_features):
                if not valid_mask[feature_names.index(feature)]:
                    continue
                    
                feat_data = group_data[:, :, feat_idx]
                
                if show_validation:
                    # Plot invalid cycles in red
                    invalid_data = feat_data[~valid_cycles]
                    for cycle in invalid_data:
                        ax.plot(phase_x, cycle, 'r-', alpha=0.3, linewidth=0.5)
                    
                    # Plot valid cycles in gray
                    valid_data = feat_data[valid_cycles]
                    for cycle in valid_data[:min(10, len(valid_data))]:
                        ax.plot(phase_x, cycle, 'gray', alpha=0.3, linewidth=0.5)
                    
                    # Calculate and plot mean of valid cycles only
                    if len(valid_data) > 0:
                        mean_curve = np.mean(valid_data, axis=0)
                        ax.plot(phase_x, mean_curve, 'b-', linewidth=2, 
                               label=f'{feature} (n={len(valid_data)})')
                else:
                    # Plot all cycles
                    for i in range(min(10, n_cycles)):
                        ax.plot(phase_x, feat_data[i], 'gray', alpha=0.3, linewidth=0.5)
                    
                    # Plot mean
                    mean_curve = np.mean(feat_data, axis=0)
                    ax.plot(phase_x, mean_curve, 'b-', linewidth=2, label=feature)
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.set_xlabel('Gait Cycle %' if subj_idx == n_subjects - 1 else '')
            ax.set_title(f'{subject}: {group_name}' if subj_idx == 0 else group_name)
            ax.legend(fontsize=6, loc='best')
            ax.grid(True, alpha=0.3)
    
    # Main title
    title = f'Task: {task} - 3D Array Efficient Processing'
    if show_validation:
        title += ' (with validation)'
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    suffix = '_validated' if show_validation else ''
    filename = output_path / f'{task}_3d_efficient{suffix}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f"\nSaved: {filename}")


def main():
    parser = argparse.ArgumentParser(description='Efficient mosaic plot using 3D arrays')
    parser.add_argument('--input_parquet', type=str, required=True,
                       help='Path to phase-indexed parquet file')
    parser.add_argument('--output_dir', type=str, default='plots_3d_efficient',
                       help='Output directory for plots')
    parser.add_argument('--validation', action='store_true',
                       help='Show validation highlighting')
    parser.add_argument('--tasks', nargs='+', 
                       help='Specific tasks to plot (default: all)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input_parquet}...")
    df = pd.read_parquet(args.input_parquet)
    
    # Define feature groups
    feature_groups = {
        'Sagittal Angles': ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r'],
        'Sagittal Velocities': ['hip_vel_s_r', 'knee_vel_s_r', 'ankle_vel_s_r'],
        'Sagittal Torques': ['hip_torque_s_r', 'knee_torque_s_r', 'ankle_torque_s_r']
    }
    
    # Get tasks to plot
    if args.tasks:
        tasks = args.tasks
    else:
        tasks = sorted(df['task'].unique())
    
    print(f"\nProcessing {len(tasks)} tasks using 3D array structure...")
    
    # Process each task
    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Processing task: {task}")
        print(f"{'='*60}")
        
        create_efficient_mosaic_plot(
            df, task, feature_groups,
            output_dir=args.output_dir,
            show_validation=args.validation
        )
    
    print(f"\nAll plots saved to {args.output_dir}/")


if __name__ == '__main__':
    main()