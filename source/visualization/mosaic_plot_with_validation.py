#!/usr/bin/env python3
"""
Generate mosaic plots with validation integration.
Invalid steps are shown in red and excluded from mean/std calculations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
import argparse
from tqdm import tqdm
import sys
import os
# Add parent directory to path to import validation module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tests'))
try:
    from validation_blueprint_enhanced import validate_phase_indexed_df
except ImportError:
    from validation_blueprint import validate_phase_indexed_df

# Standard: 150 points per gait cycle
POINTS_PER_CYCLE = 150


def get_validation_results(df, subject_col='subject', task_col='task'):
    """Run validation and return results with step validity flags."""
    print("Running validation on dataset...")
    
    # Run validation
    validated_df, summary = validate_phase_indexed_df(
        df, 
        mode='comprehensive',
        subject_col=subject_col,
        task_col=task_col
    )
    
    # Create a mapping of subject-task-step to validity
    validation_map = {}
    
    for subject in df[subject_col].unique():
        for task in df[df[subject_col] == subject][task_col].unique():
            key = (subject, task)
            
            # Get validation results for this subject-task
            mask = (validated_df[subject_col] == subject) & (validated_df[task_col] == task)
            subset = validated_df[mask]
            
            if len(subset) == 0:
                continue
                
            # Get step numbers and their validity
            if 'step_number' in subset.columns:
                step_validity = {}
                for step_num in subset['step_number'].unique():
                    step_mask = subset['step_number'] == step_num
                    step_data = subset[step_mask]
                    
                    # Check if all rows in this step are valid
                    if 'validation_codes' in step_data.columns:
                        # Step is valid if all rows have empty validation codes
                        is_valid = step_data['validation_codes'].apply(
                            lambda x: len(x) == 0 if isinstance(x, list) else True
                        ).all()
                    else:
                        is_valid = True
                        
                    step_validity[step_num] = is_valid
                    
                validation_map[key] = step_validity
            else:
                # If no step numbers, check by reshaping
                n_points = len(subset)
                n_cycles = n_points // POINTS_PER_CYCLE
                
                if n_cycles > 0 and 'validation_codes' in subset.columns:
                    # Reshape validation codes
                    val_codes = subset['validation_codes'].values
                    val_codes_reshaped = val_codes.reshape(n_cycles, POINTS_PER_CYCLE)
                    
                    step_validity = {}
                    for i in range(n_cycles):
                        # Check if all points in this cycle are valid
                        cycle_codes = val_codes_reshaped[i]
                        is_valid = all(len(x) == 0 if isinstance(x, list) else True 
                                     for x in cycle_codes)
                        step_validity[i] = is_valid
                        
                    validation_map[key] = step_validity
    
    # Print validation summary
    total_steps = sum(len(v) for v in validation_map.values())
    valid_steps = sum(sum(v.values()) for v in validation_map.values())
    invalid_steps = total_steps - valid_steps
    
    print(f"\nValidation Summary:")
    print(f"  Total steps: {total_steps}")
    print(f"  Valid steps: {valid_steps} ({valid_steps/total_steps*100:.1f}%)")
    print(f"  Invalid steps: {invalid_steps} ({invalid_steps/total_steps*100:.1f}%)")
    
    return validation_map, summary


def reshape_data_with_validation(subj_df, features, validation_info=None, phase_col='phase'):
    """
    Reshape data and separate valid/invalid cycles based on validation results.
    
    Returns:
        dict: Feature data with 'valid' and 'invalid' arrays
        array: Phase x-axis values
    """
    reshaped_feature_data = {}
    phase_x_axis = np.linspace(0, 100, POINTS_PER_CYCLE)
    
    if subj_df.empty or not features:
        return {}, None
    
    # Get the first feature to determine data length
    first_feature_data = subj_df[features[0]].values
    if len(first_feature_data) == 0 or len(first_feature_data) % POINTS_PER_CYCLE != 0:
        return {}, None
    
    num_cycles = len(first_feature_data) // POINTS_PER_CYCLE
    
    # Determine which cycles are valid
    valid_cycles = np.ones(num_cycles, dtype=bool)
    
    if validation_info is not None:
        # validation_info is a dict of step_number -> is_valid
        for step_num, is_valid in validation_info.items():
            if step_num < num_cycles:
                valid_cycles[step_num] = is_valid
    
    # Reshape each feature
    for feat in features:
        if feat not in subj_df.columns:
            continue
        
        feat_array = subj_df[feat].values
        if len(feat_array) != len(first_feature_data):
            continue
        
        try:
            # Reshape all data
            all_data = feat_array.reshape(num_cycles, POINTS_PER_CYCLE)
            
            # Separate valid and invalid cycles
            valid_data = all_data[valid_cycles]
            invalid_data = all_data[~valid_cycles]
            
            reshaped_feature_data[feat] = {
                'all': all_data,
                'valid': valid_data,
                'invalid': invalid_data,
                'valid_mask': valid_cycles
            }
            
        except ValueError as e:
            print(f"[ERROR] Could not reshape '{feat}': {str(e)}")
            continue
    
    return reshaped_feature_data, phase_x_axis


def create_mosaic_plot_with_validation(df, task, features, validation_map, 
                                      subject_col='subject', task_col='task', 
                                      phase_col='phase', output_dir='plots', 
                                      plot_type='both'):
    """
    Create mosaic plot with validation highlighting.
    Invalid steps are shown in red and excluded from mean/std.
    """
    # Filter for this task
    task_df = df[df[task_col] == task]
    subjects = sorted(task_df[subject_col].unique())
    
    if not subjects:
        print(f"[WARN] No subjects found for task '{task}'")
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
        validation_info = validation_map.get((subject, task), None)
        
        reshaped_data, phase_x = reshape_data_with_validation(
            subj_task_df, features, validation_info, phase_col
        )
        
        if not reshaped_data:
            continue
        
        for j, feature in enumerate(features):
            ax = fig.add_subplot(gs[i, j])
            
            if feature not in reshaped_data:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center')
                ax.set_title(feature)
                continue
            
            data_dict = reshaped_data[feature]
            valid_data = data_dict['valid']
            invalid_data = data_dict['invalid']
            all_data = data_dict['all']
            
            # Update statistics
            if j == 0:  # Count once per subject
                total_steps += len(all_data)
                total_invalid_steps += len(invalid_data)
            
            # Plot based on type
            if plot_type in ['spaghetti', 'both']:
                # Plot valid cycles in gray
                for k in range(len(valid_data)):
                    ax.plot(phase_x, valid_data[k, :], 
                           alpha=0.3, color='gray', linewidth=0.8)
                
                # Plot invalid cycles in red
                for k in range(len(invalid_data)):
                    ax.plot(phase_x, invalid_data[k, :], 
                           alpha=0.5, color='red', linewidth=1.0, 
                           linestyle='--', label='Invalid' if k == 0 else '')
            
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
                           ha='center', va='center', color='red')
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.grid(True, alpha=0.3)
            
            if i == 0:
                ax.set_title(feature.replace('_', ' ').title())
            
            if i == n_subjects - 1:
                ax.set_xlabel('Gait Cycle (%)')
            
            if j == 0:
                ax.set_ylabel(f'{subject}\nAngle (deg)')
            
            # Add legend for first subplot only
            if i == 0 and j == 0 and len(invalid_data) > 0:
                ax.legend(loc='upper right', fontsize=8)
            
            # Add validation info to subplot
            if len(invalid_data) > 0:
                ax.text(0.02, 0.02, f'{len(invalid_data)} invalid', 
                       transform=ax.transAxes, 
                       color='red', fontsize=8, 
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Main title with validation info
    validity_pct = (total_steps - total_invalid_steps) / total_steps * 100 if total_steps > 0 else 100
    title = f'{task} - {validity_pct:.1f}% Valid Steps ({total_steps - total_invalid_steps}/{total_steps})'
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Save plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    if plot_type == 'separate':
        # This shouldn't be called with separate, but handle it
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
    
    # Get validation results
    validation_map, summary = get_validation_results(df, args.subject_col, args.task_col)
    
    # If no features specified, use default biomechanical features
    if not args.features:
        # Try to find sagittal plane angles
        angle_cols = [c for c in df.columns if 'angle_s_' in c and not 'foot' in c]
        if angle_cols:
            args.features = angle_cols[:3]  # Use first 3
        else:
            args.features = ['knee_angle_s_r', 'hip_angle_s_r', 'ankle_angle_s_r']
    
    print(f"\nSelected {len(args.features)} features: {', '.join(args.features)}")
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get unique tasks
    tasks = df[args.task_col].unique()
    
    # Generate plots
    plot_types = ['mean', 'spaghetti'] if args.plot_type == 'separate' else [args.plot_type]
    
    total_files = len(tasks) * len(plot_types)
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
    for task in sorted(tasks):
        task_steps = sum(1 for (s, t), v in validation_map.items() 
                        if t == task for _ in v)
        task_valid = sum(1 for (s, t), v in validation_map.items() 
                        if t == task for valid in v.values() if valid)
        if task_steps > 0:
            print(f"  {task}: {task_valid}/{task_steps} valid ({task_valid/task_steps*100:.1f}%)")


if __name__ == '__main__':
    main()