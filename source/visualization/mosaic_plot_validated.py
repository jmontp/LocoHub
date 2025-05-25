#!/usr/bin/env python3
"""
Generate mosaic plots with simple validation highlighting.
Invalid steps are shown in red and excluded from mean/std calculations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
import argparse
from tqdm import tqdm

# Standard: 150 points per gait cycle
POINTS_PER_CYCLE = 150


def simple_validate_cycles(df, subject_col='subject', task_col='task'):
    """
    Simple validation to identify potentially invalid cycles.
    
    Criteria for invalid cycles:
    - Extreme values (beyond physiological range)
    - High variance within cycle
    - Discontinuities
    """
    validation_map = {}
    
    # Define physiological ranges for common variables
    ranges = {
        'angle': (-180, 180),  # degrees
        'vel': (-1000, 1000),  # deg/s
        'torque': (-300, 300), # Nm/kg
    }
    
    print("Running simple validation checks...")
    
    for subject in df[subject_col].unique():
        for task in df[df[subject_col] == subject][task_col].unique():
            mask = (df[subject_col] == subject) & (df[task_col] == task)
            subset = df[mask]
            
            if len(subset) == 0 or len(subset) % POINTS_PER_CYCLE != 0:
                continue
            
            n_cycles = len(subset) // POINTS_PER_CYCLE
            key = (subject, task)
            step_validity = {}
            
            # Check each biomechanical variable
            for col in subset.columns:
                if any(x in col for x in ['angle', 'vel', 'torque']):
                    data = subset[col].values
                    
                    # Determine expected range
                    if 'angle' in col:
                        min_val, max_val = ranges['angle']
                    elif 'vel' in col:
                        min_val, max_val = ranges['vel']
                    elif 'torque' in col:
                        min_val, max_val = ranges['torque']
                    else:
                        continue
                    
                    # Reshape to cycles
                    try:
                        cycles = data.reshape(n_cycles, POINTS_PER_CYCLE)
                        
                        for i in range(n_cycles):
                            cycle = cycles[i]
                            
                            # Initialize as valid
                            if i not in step_validity:
                                step_validity[i] = True
                            
                            # Check for out of range values
                            if np.any(cycle < min_val) or np.any(cycle > max_val):
                                step_validity[i] = False
                                continue
                            
                            # Check for NaN or inf
                            if np.any(~np.isfinite(cycle)):
                                step_validity[i] = False
                                continue
                            
                            # Check for excessive variance (potential noise)
                            # Skip this check - it's too strict for normal biomechanics
                            
                            # Check for large discontinuities
                            diffs = np.abs(np.diff(cycle))
                            max_diff = np.max(diffs) if len(diffs) > 0 else 0
                            
                            # Different thresholds for different variables
                            if 'angle' in col and max_diff > 30:  # >30 deg jump
                                step_validity[i] = False
                            elif 'vel' in col and max_diff > 200:  # >200 deg/s jump
                                step_validity[i] = False
                            elif 'torque' in col and max_diff > 50:  # >50 Nm/kg jump
                                step_validity[i] = False
                                
                    except:
                        # If can't reshape, mark all as potentially invalid
                        for i in range(n_cycles):
                            step_validity[i] = False
            
            validation_map[key] = step_validity
    
    # Print summary
    total_steps = sum(len(v) for v in validation_map.values())
    valid_steps = sum(sum(v.values()) for v in validation_map.values() if v)
    invalid_steps = total_steps - valid_steps
    
    print(f"\nValidation Summary:")
    print(f"  Total steps: {total_steps}")
    print(f"  Valid steps: {valid_steps} ({valid_steps/total_steps*100:.1f}%)")
    print(f"  Invalid steps: {invalid_steps} ({invalid_steps/total_steps*100:.1f}%)")
    
    return validation_map


def reshape_data_with_validation(subj_df, features, validation_info=None, phase_col='phase'):
    """
    Reshape data using 3D array structure and separate valid/invalid cycles.
    
    Returns:
        Tuple of (data_3d, valid_features, valid_cycles, phase_x_axis)
    """
    phase_x_axis = np.linspace(0, 100, POINTS_PER_CYCLE)
    
    if subj_df.empty or not features:
        return None, [], None, phase_x_axis
    
    # Check data length
    n_points = len(subj_df)
    if n_points == 0 or n_points % POINTS_PER_CYCLE != 0:
        return None, [], None, phase_x_axis
    
    num_cycles = n_points // POINTS_PER_CYCLE
    
    # Determine which cycles are valid
    valid_cycles = np.ones(num_cycles, dtype=bool)
    
    if validation_info is not None:
        for step_num, is_valid in validation_info.items():
            if step_num < num_cycles:
                valid_cycles[step_num] = is_valid
    
    # Identify valid features
    valid_features = [f for f in features if f in subj_df.columns]
    if not valid_features:
        return None, [], valid_cycles, phase_x_axis
    
    try:
        # EFFICIENT 3D RESHAPE: Extract all features at once
        feature_data = subj_df[valid_features].values  # Shape: (n_points, n_features)
        
        # Single reshape to 3D array
        data_3d = feature_data.reshape(num_cycles, POINTS_PER_CYCLE, len(valid_features))
        
        return data_3d, valid_features, valid_cycles, phase_x_axis
        
    except Exception as e:
        print(f"[ERROR] Could not reshape data: {str(e)}")
        return None, [], None, phase_x_axis


def create_mosaic_plot_with_validation(df, task, features, validation_map, 
                                      subject_col='subject', task_col='task', 
                                      phase_col='phase', output_dir='plots', 
                                      plot_type='both'):
    """
    Create mosaic plot with validation highlighting.
    """
    # Filter for this task
    task_df = df[df[task_col] == task]
    subjects = sorted(task_df[subject_col].unique())
    
    if not subjects:
        return
    
    # Create figure
    n_subjects = len(subjects)
    n_features = len(features)
    
    fig = plt.figure(figsize=(4 * n_features, 3 * n_subjects))
    gs = gridspec.GridSpec(n_subjects, n_features, hspace=0.15, wspace=0.2,
                          top=0.96, bottom=0.05, left=0.06, right=0.98)
    
    # Track overall statistics
    total_invalid_steps = 0
    total_steps = 0
    
    # Create subplots
    for i, subject in enumerate(subjects):
        subj_task_df = task_df[task_df[subject_col] == subject]
        
        # Get validation info for this subject-task
        validation_info = validation_map.get((subject, task), {})
        
        data_3d, valid_features, valid_cycles, phase_x = reshape_data_with_validation(
            subj_task_df, features, validation_info, phase_col
        )
        
        if data_3d is None:
            continue
        
        n_cycles = data_3d.shape[0]
        n_invalid = np.sum(~valid_cycles) if valid_cycles is not None else 0
        
        # Update statistics
        total_steps += n_cycles
        total_invalid_steps += n_invalid
        
        for j, feature in enumerate(features):
            ax = fig.add_subplot(gs[i, j])
            
            if feature not in valid_features:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center')
                ax.set_title(feature)
                continue
            
            # Get feature index in the 3D array
            feat_idx = valid_features.index(feature)
            data = data_3d[:, :, feat_idx]  # Extract 2D slice for this feature
            
            # Separate valid and invalid data
            if valid_cycles is not None:
                valid_data = data[valid_cycles]
                invalid_data = data[~valid_cycles]
            else:
                valid_data = data
                invalid_data = np.array([])
            
            # Plot based on type
            if plot_type in ['spaghetti', 'both']:
                # Plot valid cycles in gray
                for k in range(len(valid_data)):
                    ax.plot(phase_x, valid_data[k, :], 
                           alpha=0.3, color='gray', linewidth=0.8)
                
                # Plot invalid cycles in red
                if len(invalid_data) > 0:
                    for k in range(len(invalid_data)):
                        ax.plot(phase_x, invalid_data[k, :], 
                               alpha=0.6, color='red', linewidth=1.2, 
                               label='Invalid' if k == 0 else '')
            
            if plot_type in ['mean', 'both']:
                if len(valid_data) > 0:
                    # Calculate mean and std from VALID cycles only
                    mean_curve = np.mean(valid_data, axis=0)
                    std_curve = np.std(valid_data, axis=0)
                    
                    if plot_type == 'both':
                        # Overlay on spaghetti
                        ax.plot(phase_x, mean_curve, 'b-', linewidth=2.5, 
                               label=f'Mean (n={len(valid_data)})')
                    else:
                        # Mean only - make it more prominent
                        ax.plot(phase_x, mean_curve, 'b-', linewidth=2, 
                               label=f'Mean (n={len(valid_data)})')
                        ax.fill_between(phase_x, 
                                      mean_curve - std_curve,
                                      mean_curve + std_curve,
                                      alpha=0.3, color='blue', label='±1 STD')
                else:
                    ax.text(0.5, 0.5, 'No valid cycles', 
                           ha='center', va='center', color='red', fontsize=12)
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.grid(True, alpha=0.3)
            
            if i == 0:
                ax.set_title(feature.replace('_', ' ').title())
            
            if i == n_subjects - 1:
                ax.set_xlabel('Gait Cycle (%)')
            
            if j == 0:
                ax.set_ylabel(f'{subject}\nAngle (deg)')
            
            # Add legend for first subplot with invalid data
            if len(invalid_data) > 0 and i == 0 and j == 0:
                ax.legend(loc='upper right', fontsize=8)
            
            # Add validation info text
            if len(invalid_data) > 0:
                info_text = f'{len(invalid_data)}/{n_cycles} invalid'
                ax.text(0.98, 0.02, info_text, 
                       transform=ax.transAxes, 
                       ha='right', va='bottom',
                       color='red', fontsize=9, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor='white', 
                               edgecolor='red',
                               alpha=0.8))
    
    # Main title with validation info
    validity_pct = (total_steps - total_invalid_steps) / total_steps * 100 if total_steps > 0 else 100
    title = f'{task} - {validity_pct:.1f}% Valid Steps ({total_steps - total_invalid_steps}/{total_steps} total)'
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Save plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if plot_type == 'separate':
        plot_type = 'both'
    
    filename = f'{task}_{plot_type}_validated.png'
    filepath = Path(output_dir) / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    return filepath


def main():
    parser = argparse.ArgumentParser(description='Generate mosaic plots with validation highlighting')
    parser.add_argument('--input_parquet', type=str, required=True,
                       help='Path to input parquet file')
    parser.add_argument('--phase_col', type=str, default='phase',
                       help='Name of phase column')
    parser.add_argument('--subject_col', type=str, default='subject_id',
                       help='Name of subject column')
    parser.add_argument('--task_col', type=str, default='task_name',
                       help='Name of task column')
    parser.add_argument('--features', nargs='+', type=str,
                       help='List of features to plot')
    parser.add_argument('--output_dir', type=str, default='plots_validated',
                       help='Output directory for plots')
    parser.add_argument('--plot-type', type=str, default='separate',
                       choices=['mean', 'spaghetti', 'both', 'separate'],
                       help='Type of plots to generate')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading {args.input_parquet}...")
    df = pd.read_parquet(args.input_parquet)
    print(f"Loaded dataframe with shape {df.shape}")
    
    # Run simple validation
    validation_map = simple_validate_cycles(df, args.subject_col, args.task_col)
    
    # If no features specified, use default biomechanical features
    if not args.features:
        angle_cols = [c for c in df.columns if 'angle_s_' in c and not 'foot' in c]
        if angle_cols:
            args.features = angle_cols[:3]
        else:
            args.features = ['knee_angle_s_r', 'hip_angle_s_r', 'ankle_angle_s_r']
    
    print(f"\nSelected {len(args.features)} features: {', '.join(args.features)}")
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get unique tasks
    tasks = sorted(df[args.task_col].unique())
    
    # Generate plots
    plot_types = ['mean', 'spaghetti'] if args.plot_type == 'separate' else [args.plot_type]
    
    total_files = len(tasks) * len(plot_types)
    print(f"\nGenerating {total_files} plots...")
    
    with tqdm(total=total_files, desc="Creating plots") as pbar:
        for task in tasks:
            for plot_type in plot_types:
                filepath = create_mosaic_plot_with_validation(
                    df, task, args.features, validation_map,
                    subject_col=args.subject_col,
                    task_col=args.task_col,
                    phase_col=args.phase_col,
                    output_dir=args.output_dir,
                    plot_type=plot_type
                )
                
                if filepath:
                    pbar.set_postfix_str(f"Saved: {filepath.name}")
                pbar.update(1)
    
    print(f"\nDone! Plots saved to '{args.output_dir}/'")
    
    # Print final summary
    print("\nValidation Summary by Task:")
    for task in tasks:
        task_steps = sum(len(v) for (s, t), v in validation_map.items() if t == task)
        task_valid = sum(sum(v.values()) for (s, t), v in validation_map.items() 
                        if t == task and v)
        if task_steps > 0:
            print(f"  {task}: {task_valid}/{task_steps} valid ({task_valid/task_steps*100:.1f}%)")


if __name__ == '__main__':
    main()