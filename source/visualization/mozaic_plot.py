#!/usr/bin/env python3
"""
Mosaic plot generator for phase-indexed locomotion data using matplotlib.
Creates a grid of subplots showing biomechanical features across subjects and tasks.

Naming convention follows the standard specification:
- Angles: <joint>_<motion>_angle_<side>_rad (e.g., hip_flexion_angle_right_rad)
- Velocities: <joint>_<motion>_velocity_<side>_rad_s (e.g., knee_flexion_velocity_left_rad_s)
- Moments: <joint>_moment_<side>_Nm (e.g., ankle_moment_right_Nm)
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle
from tqdm import tqdm

# Standard: 150 points per gait cycle
POINTS_PER_CYCLE = 150

def reshape_data_for_subject_task(subj_df, features, phase_col='phase'):
    """
    Reshape subject-task data using efficient 3D array structure.
    
    This function uses the 3D array approach for better performance:
    - Single reshape operation for all features: O(1)
    - Returns (num_cycles, POINTS_PER_CYCLE, num_features) array
    - Better cache efficiency and vectorized operations
    
    Args:
        subj_df: DataFrame filtered for one subject-task combination
        features: List of feature columns to reshape
        phase_col: Name of phase column
        
    Returns:
        Tuple of (data_3d, valid_features, phase_x_axis)
        - data_3d: 3D numpy array or None
        - valid_features: List of successfully extracted features
        - phase_x_axis: Phase values for plotting
    """
    phase_x_axis = np.linspace(0, 100, POINTS_PER_CYCLE)
    
    if subj_df.empty:
        return None, [], phase_x_axis
    
    if phase_col not in subj_df.columns:
        print(f"[ERROR] Phase column '{phase_col}' not found in DataFrame.")
        return None, [], phase_x_axis
    
    if not features:
        return None, [], phase_x_axis
    
    # Check data length
    n_points = len(subj_df)
    if n_points % POINTS_PER_CYCLE != 0:
        subject_id = subj_df.iloc[0].get('subject', subj_df.iloc[0].get('subject_id', 'unknown'))
        task_name = subj_df.iloc[0].get('task', subj_df.iloc[0].get('task_name', 'unknown'))
        
        print(f"[ERROR] Data length {n_points} not divisible by {POINTS_PER_CYCLE}")
        print(f"        Subject: {subject_id}, Task: {task_name}")
        return None, [], phase_x_axis
    
    num_cycles = n_points // POINTS_PER_CYCLE
    
    # Identify valid features
    valid_features = [f for f in features if f in subj_df.columns]
    if not valid_features:
        print(f"[WARN] No valid features found in data")
        return None, [], phase_x_axis
    
    try:
        # EFFICIENT 3D RESHAPE: Extract all features at once
        # This is more efficient than individual reshapes
        feature_data = subj_df[valid_features].values  # Shape: (n_points, n_features)
        
        # Single reshape to 3D array: (n_cycles * 150, n_features) → (n_cycles, 150, n_features)
        data_3d = feature_data.reshape(num_cycles, POINTS_PER_CYCLE, len(valid_features))
        
        return data_3d, valid_features, phase_x_axis
        
    except Exception as e:
        print(f"[ERROR] Could not reshape data: {str(e)}")
        return None, [], phase_x_axis

def create_mosaic_plot(df, task, features, subject_col='subject', task_col='task', 
                      phase_col='phase', output_dir='plots', plot_type='both'):
    """
    Create a mosaic plot for a single task showing multiple subjects and features.
    
    Args:
        df: DataFrame with phase-indexed data
        task: Task name to plot
        features: List of features to plot
        subject_col: Column name for subjects
        task_col: Column name for tasks
        phase_col: Column name for phase
        output_dir: Directory to save plots
        plot_type: 'mean' for mean±std only, 'spaghetti' for cycles only, 'both' for combined
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
    
    # Create subplots
    for i, subject in enumerate(subjects):
        subj_task_df = task_df[task_df[subject_col] == subject]
        data_3d, valid_features, phase_x = reshape_data_for_subject_task(subj_task_df, features, phase_col)
        
        if data_3d is None:
            continue
        
        n_cycles = data_3d.shape[0]
        
        for j, feature in enumerate(features):
            ax = fig.add_subplot(gs[i, j])
            
            if feature in valid_features:
                # Get feature index in the 3D array
                feat_idx = valid_features.index(feature)
                data = data_3d[:, :, feat_idx]  # Extract 2D slice for this feature
                
                # Plot based on type
                if plot_type in ['spaghetti', 'both']:
                    # Plot all cycles for spaghetti
                    for k in range(n_cycles):
                        ax.plot(phase_x, data[k, :], alpha=0.3, color='gray', linewidth=0.8)
                
                if plot_type in ['mean', 'both']:
                    mean_curve = np.mean(data, axis=0)
                    std_curve = np.std(data, axis=0)
                    
                    if plot_type == 'both':
                        # Overlay on spaghetti
                        ax.plot(phase_x, mean_curve, 'b-', linewidth=2.5, label='Mean')
                    else:
                        # Mean only - make it more prominent
                        ax.plot(phase_x, mean_curve, 'b-', linewidth=2, label='Mean')
                        ax.fill_between(phase_x, 
                                      mean_curve - std_curve,
                                      mean_curve + std_curve,
                                      alpha=0.3, color='blue', label='±1 STD')
                
                # Format subplot
                if i == 0:
                    ax.set_title(feature.replace('_', ' ').title(), fontsize=10)
                if j == 0:
                    ax.set_ylabel(f'{subject}\nAngle (rad)', fontsize=9)
                if i == n_subjects - 1:
                    ax.set_xlabel('Gait Cycle (%)', fontsize=9)
                
                ax.grid(True, alpha=0.3)
                ax.set_xlim(0, 100)
                
                # Add cycle info
                ax.text(0.98, 0.98, f'{n_cycles} cycles', 
                       transform=ax.transAxes, 
                       ha='right', va='top', 
                       fontsize=8, alpha=0.7)
            else:
                ax.text(0.5, 0.5, 'No data', 
                       transform=ax.transAxes,
                       ha='center', va='center')
                ax.set_xticks([])
                ax.set_yticks([])
    
    # Add main title
    title_suffix = {'mean': ' (Mean ± STD)', 'spaghetti': ' (All Cycles)', 'both': ''}[plot_type]
    fig.suptitle(f'Task: {task}{title_suffix}', fontsize=14, y=0.99)
    
    # Save figure
    filename_suffix = {'mean': '_mean', 'spaghetti': '_spaghetti', 'both': ''}[plot_type]
    output_path = os.path.join(output_dir, f'{task}{filename_suffix}.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    
    return output_path

def run_diagnostic(df, phase_col='phase', subject_col='subject', task_col='task'):
    """
    Run diagnostic check on data compliance with 150-point standard.
    """
    print("\n=== DIAGNOSTIC MODE: Checking data format compliance ===")
    print(f"Standard specification: Each gait cycle must have exactly {POINTS_PER_CYCLE} points")
    print(f"Phase column: {phase_col}")
    print("\nChecking each subject-task combination:")
    
    issues_found = False
    unique_tasks = df[task_col].unique()
    
    for task in unique_tasks:
        task_df = df[df[task_col] == task]
        for subject in task_df[subject_col].unique():
            subj_task_df = task_df[task_df[subject_col] == subject]
            data_length = len(subj_task_df)
            
            if data_length % POINTS_PER_CYCLE != 0:
                print(f"  ❌ {subject} - {task}: {data_length} points ({data_length/POINTS_PER_CYCLE:.2f} cycles)")
                issues_found = True
            else:
                num_cycles = data_length // POINTS_PER_CYCLE
                print(f"  ✓ {subject} - {task}: {data_length} points ({num_cycles} complete cycles)")
    
    if issues_found:
        print("\n⚠️  Data format issues detected!")
    else:
        print("\n✅ All data complies with the standard format!")
    
    print("\n" + "="*60 + "\n")
    return not issues_found

def main():
    parser = argparse.ArgumentParser(description='Generate mosaic plots for phase-indexed locomotion data')
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
    parser.add_argument('--output_dir', type=str, default='plots',
                       help='Output directory for plots')
    parser.add_argument('--diagnostic', action='store_true',
                       help='Run diagnostic mode to check data compliance')
    parser.add_argument('--plot-type', type=str, default='separate',
                       choices=['mean', 'spaghetti', 'both', 'separate'],
                       help='Type of plots to generate (default: separate creates both)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading {args.input_parquet}...")
    try:
        df = pd.read_parquet(args.input_parquet)
        print(f"Loaded dataframe with shape {df.shape}")
        print(f"Columns: {', '.join(df.columns[:10])}..." if len(df.columns) > 10 else f"Columns: {', '.join(df.columns)}")
    except Exception as e:
        print(f"Error loading parquet file: {e}")
        return
    
    # Run diagnostic if requested
    if args.diagnostic:
        compliant = run_diagnostic(df, args.phase_col, args.subject_col, args.task_col)
        if not compliant:
            response = input("\nContinue with visualization anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting...")
                return
    
    # Auto-detect features if not specified
    if not args.features:
        exclude = {args.phase_col, args.subject_col, args.task_col, 'time', 'time_s', 'phase_l', 'phase_r'}
        numeric_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]
        
        # Filter for actual biomechanical features (containing angle, moment, velocity, etc.)
        biomech_keywords = ['angle', 'moment', 'velocity', 'force', 'grf', 'cop']
        args.features = [c for c in numeric_cols if any(kw in c.lower() for kw in biomech_keywords)][:20]
        
        if not args.features:
            print("No suitable features found. Please specify features manually.")
            return
    
    print(f"\nSelected {len(args.features)} features: {', '.join(args.features)}")
    
    # Create output directory
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created output directory: {args.output_dir}")
    
    # Generate plots for each task
    unique_tasks = df[args.task_col].unique()
    
    # Determine which plot types to create
    if args.plot_type == 'separate':
        plot_types = ['mean', 'spaghetti']
        print(f"\nGenerating separate mean and spaghetti plots for {len(unique_tasks)} tasks...")
    else:
        plot_types = [args.plot_type]
        print(f"\nGenerating {args.plot_type} plots for {len(unique_tasks)} tasks...")
    
    total_plots = len(unique_tasks) * len(plot_types)
    pbar = tqdm(total=total_plots, desc="Creating plots")
    
    for task in unique_tasks:
        for plot_type in plot_types:
            try:
                output_path = create_mosaic_plot(
                    df, task, args.features,
                    subject_col=args.subject_col,
                    task_col=args.task_col,
                    phase_col=args.phase_col,
                    output_dir=args.output_dir,
                    plot_type=plot_type
                )
                pbar.set_postfix_str(f"Saved: {os.path.basename(output_path)}")
            except Exception as e:
                print(f"\n  ✗ Error processing task '{task}' ({plot_type}): {str(e)}")
            pbar.update(1)
    
    pbar.close()
    
    print(f"\nDone! Plots saved to '{args.output_dir}/'")

if __name__ == '__main__':
    main()