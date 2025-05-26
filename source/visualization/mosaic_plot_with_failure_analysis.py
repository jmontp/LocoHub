#!/usr/bin/env python3
"""
Generate mosaic plots with validation integration and failure analysis.
Invalid steps are shown in red and excluded from mean/std calculations.
Additionally, semantic bar charts show the reasons for validation failures.
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
from collections import defaultdict
# Add parent directory to path to import validation module
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tests'))
from validation_blueprint_enhanced import BiomechanicsValidator

# Standard: 150 points per gait cycle
POINTS_PER_CYCLE = 150


def get_validation_results_with_reasons(df, subject_col='subject', task_col='task'):
    """Run validation and return results with step validity flags and failure reasons."""
    print("Running validation on dataset...")
    
    # Check if dataset uses old or new naming convention
    uses_old_names = 'hip_angle_s_r' in df.columns
    
    if uses_old_names:
        # Dataset already uses old names, no mapping needed
        df_validate = df.copy()
    else:
        # Map new names back to old for validation
        name_mapping = {
            'hip_flexion_angle_right_rad': 'hip_angle_s_r',
            'hip_flexion_angle_left_rad': 'hip_angle_s_l',
            'knee_flexion_angle_right_rad': 'knee_angle_s_r',
            'knee_flexion_angle_left_rad': 'knee_angle_s_l',
            'ankle_flexion_angle_right_rad': 'ankle_angle_s_r',
            'ankle_flexion_angle_left_rad': 'ankle_angle_s_l',
        }
        
        # Create a copy with renamed columns for validation
        df_validate = df.copy()
        for new_name, old_name in name_mapping.items():
            if new_name in df_validate.columns:
                df_validate[old_name] = df_validate[new_name]
    
    # Also rename subject and task columns if needed
    if subject_col != 'subject_id':
        df_validate['subject_id'] = df_validate[subject_col]
    if task_col != 'task_name':
        df_validate['task_name'] = df_validate[task_col]
    
    # Run validation in comprehensive mode
    validator = BiomechanicsValidator(df_validate, mode='comprehensive')
    validated_df = validator.validate()
    
    # Create a mapping of subject-task-step to validity and failure reasons
    validation_map = {}
    failure_reasons_map = {}
    
    for subject in df[subject_col].unique():
        for task in df[df[subject_col] == subject][task_col].unique():
            key = (subject, task)
            
            # Get validation results for this subject-task
            mask = (validated_df['subject_id'] == subject) & (validated_df['task_name'] == task)
            subset = validated_df[mask]
            
            if len(subset) == 0:
                continue
                
            # Get step numbers and their validity
            n_points = len(subset)
            n_cycles = n_points // POINTS_PER_CYCLE
            
            if n_cycles > 0 and 'validation_codes' in subset.columns:
                # Reshape validation codes
                val_codes = subset['validation_codes'].values
                val_codes_reshaped = val_codes.reshape(n_cycles, POINTS_PER_CYCLE)
                
                step_validity = {}
                step_failures = {}
                
                for i in range(n_cycles):
                    # Check if all points in this cycle are valid
                    cycle_codes = val_codes_reshaped[i]
                    
                    # Collect all unique error codes for this cycle
                    all_error_codes = set()
                    for point_codes in cycle_codes:
                        if isinstance(point_codes, list) and len(point_codes) > 0:
                            all_error_codes.update(point_codes)
                    
                    is_valid = len(all_error_codes) == 0
                    step_validity[i] = is_valid
                    
                    if not is_valid:
                        # Convert error codes to descriptions
                        step_failures[i] = {
                            code: BiomechanicsValidator.ERROR_CODES.get(code, f"Unknown error {code}")
                            for code in all_error_codes
                        }
                    
                validation_map[key] = step_validity
                failure_reasons_map[key] = step_failures
    
    # Print validation summary
    total_steps = sum(len(v) for v in validation_map.values())
    valid_steps = sum(sum(v.values()) for v in validation_map.values())
    invalid_steps = total_steps - valid_steps
    
    print(f"\nValidation Summary:")
    print(f"  Total steps: {total_steps}")
    print(f"  Valid steps: {valid_steps} ({valid_steps/total_steps*100:.1f}%)")
    print(f"  Invalid steps: {invalid_steps} ({invalid_steps/total_steps*100:.1f}%)")
    
    # Get failure report
    failure_report = validator.get_failure_report()
    
    return validation_map, failure_reasons_map, failure_report


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


def create_failure_analysis_plot(failure_reasons_map, task, output_dir='plots'):
    """Create a bar chart showing failure reasons for a specific task."""
    # Aggregate failure reasons across all subjects for this task
    failure_counts = defaultdict(int)
    
    for (subject, task_name), step_failures in failure_reasons_map.items():
        if task_name == task:
            for step_num, failures in step_failures.items():
                for error_code, description in failures.items():
                    failure_counts[description] += 1
    
    if not failure_counts:
        print(f"No validation failures found for task '{task}'")
        return
    
    # Sort by count
    sorted_failures = sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    descriptions = [item[0] for item in sorted_failures]
    counts = [item[1] for item in sorted_failures]
    
    # Create horizontal bar chart for better readability
    y_pos = np.arange(len(descriptions))
    bars = ax.barh(y_pos, counts, color='red', alpha=0.7)
    
    # Add value labels on bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                str(count), va='center')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(descriptions, fontsize=10)
    ax.set_xlabel('Number of Failed Steps', fontsize=12)
    ax.set_title(f'Validation Failure Reasons for {task}', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / f"{task}_failure_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved failure analysis plot to {output_file}")


def create_mosaic_plot_with_validation(df, task, features, validation_map, failure_reasons_map,
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
        failure_info = failure_reasons_map.get((subject, task), {})
        
        # Reshape data
        reshaped_data, phase_x = reshape_data_with_validation(
            subj_task_df, features, validation_info, phase_col
        )
        
        if not reshaped_data:
            continue
        
        # Update statistics
        if validation_info:
            total_steps += len(validation_info)
            total_invalid_steps += sum(1 for v in validation_info.values() if not v)
        
        for j, feat in enumerate(features):
            ax = fig.add_subplot(gs[i, j])
            
            if feat not in reshaped_data:
                ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                       transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
                continue
            
            feat_data = reshaped_data[feat]
            
            # Plot based on type
            if plot_type in ['spaghetti', 'both']:
                # Plot valid cycles in blue
                if feat_data['valid'].size > 0:
                    for cycle in feat_data['valid']:
                        ax.plot(phase_x, cycle, 'b-', alpha=0.3, linewidth=0.8)
                
                # Plot invalid cycles in red
                if feat_data['invalid'].size > 0:
                    for cycle in feat_data['invalid']:
                        ax.plot(phase_x, cycle, 'r-', alpha=0.5, linewidth=1.2)
            
            if plot_type in ['mean', 'both'] and feat_data['valid'].size > 0:
                # Calculate mean and std only from valid cycles
                mean_valid = np.mean(feat_data['valid'], axis=0)
                std_valid = np.std(feat_data['valid'], axis=0)
                
                # Plot mean ± std
                ax.plot(phase_x, mean_valid, 'k-', linewidth=2, label='Mean (valid)')
                ax.fill_between(phase_x, mean_valid - std_valid, mean_valid + std_valid,
                              alpha=0.3, color='gray', label='±1 SD')
            
            # Add failure annotations for this subject
            if failure_info and i == 0:  # Only add to first row
                n_invalid = len([k for k, v in validation_info.items() if not v])
                if n_invalid > 0:
                    # Get unique failure reasons
                    all_reasons = set()
                    for step_failures in failure_info.values():
                        all_reasons.update(step_failures.values())
                    
                    # Create a short summary
                    reason_text = f"{n_invalid} invalid steps"
                    if len(all_reasons) <= 2:
                        reason_text += ":\n" + "\n".join(list(all_reasons)[:2])
                    else:
                        reason_text += f":\n{len(all_reasons)} different issues"
                    
                    ax.text(0.02, 0.98, reason_text, transform=ax.transAxes,
                           fontsize=8, va='top', ha='left', color='red',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='red', alpha=0.8))
            
            # Formatting
            ax.set_xlim(0, 100)
            ax.grid(True, alpha=0.3)
            
            if i == 0:
                ax.set_title(feat.replace('_', ' ').title(), fontsize=10)
            if i == n_subjects - 1:
                ax.set_xlabel('Gait Cycle %', fontsize=9)
            else:
                ax.set_xticklabels([])
            
            if j == 0:
                ax.set_ylabel(f'{subject}\n{feat.split("_")[-1]}', fontsize=9)
            
            # Add legend to first plot
            if i == 0 and j == 0 and plot_type == 'both':
                ax.legend(loc='upper right', fontsize=8)
    
    # Add overall title with validation stats
    title = f'{task.replace("_", " ").title()} - All Features'
    if total_steps > 0:
        title += f'\n({total_invalid_steps}/{total_steps} invalid steps = {total_invalid_steps/total_steps*100:.1f}%)'
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Save plot
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    suffix = 'validated_with_analysis'
    output_file = Path(output_dir) / f"{task}_{plot_type}_{suffix}.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved {task} plot to {output_file}")
    
    # Also create failure analysis plot
    create_failure_analysis_plot(failure_reasons_map, task, output_dir)


def main():
    parser = argparse.ArgumentParser(description='Generate mosaic plots with validation and failure analysis')
    parser.add_argument('--input', '-i', type=str, required=True,
                       help='Path to input parquet file')
    parser.add_argument('--output-dir', '-o', type=str, default='plots',
                       help='Output directory for plots')
    parser.add_argument('--subject-col', type=str, default='subject',
                       help='Name of subject column')
    parser.add_argument('--task-col', type=str, default='task',
                       help='Name of task column')
    parser.add_argument('--phase-col', type=str, default='phase',
                       help='Name of phase column')
    parser.add_argument('--plot-type', type=str, default='both',
                       choices=['spaghetti', 'mean', 'both'],
                       help='Type of plot to generate')
    parser.add_argument('--tasks', nargs='+', type=str,
                       help='Specific tasks to plot (default: all)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input}...")
    df = pd.read_parquet(args.input)
    
    # Get unique tasks
    if args.tasks:
        tasks = args.tasks
    else:
        tasks = sorted(df[args.task_col].unique())
    
    print(f"Found {len(tasks)} tasks to process")
    
    # Get feature columns - exclude metadata columns
    metadata_cols = {args.subject_col, args.task_col, args.phase_col, 'step_number'}
    features = [col for col in df.columns if col not in metadata_cols]
    print(f"Found {len(features)} features to plot")
    
    # Run validation with failure analysis
    validation_map, failure_reasons_map, failure_report = get_validation_results_with_reasons(
        df, args.subject_col, args.task_col
    )
    
    # Print overall failure summary
    print("\nTop validation failures across all tasks:")
    if not failure_report.empty:
        summary = failure_report.groupby(['error_code', 'description'])['count'].sum().reset_index()
        summary = summary.sort_values('count', ascending=False).head(10)
        for _, row in summary.iterrows():
            print(f"  {row['description']}: {row['count']} occurrences")
    
    # Create output subdirectory
    dataset_name = Path(args.input).stem
    output_subdir = Path(args.output_dir) / f'validated_{dataset_name}'
    output_subdir.mkdir(parents=True, exist_ok=True)
    
    # Process each task
    for task in tqdm(tasks, desc="Generating plots"):
        create_mosaic_plot_with_validation(
            df, task, features, validation_map, failure_reasons_map,
            args.subject_col, args.task_col, args.phase_col,
            str(output_subdir), args.plot_type
        )
    
    print(f"\nAll plots saved to {output_subdir}")


if __name__ == '__main__':
    main()