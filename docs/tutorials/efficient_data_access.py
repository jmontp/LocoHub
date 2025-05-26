#!/usr/bin/env python3
"""
Efficient Data Access Tutorial for Locomotion Data

This tutorial demonstrates efficient methods to access and process phase-indexed
locomotion data using NumPy reshaping instead of pandas groupby operations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time


def load_and_prepare_data(parquet_file):
    """Load phase-indexed data with step numbers."""
    df = pd.read_parquet(parquet_file)
    return df


def efficient_reshape_method(df, subject, task, features, points_per_cycle=150):
    """
    Efficiently reshape data for a subject-task using NumPy operations.
    
    Returns:
        dict: Dictionary with feature names as keys and (n_cycles, 150) arrays as values
    """
    # Filter for specific subject and task
    mask = (df['subject'] == subject) & (df['task'] == task)
    subset = df[mask]
    
    # Get number of cycles
    n_points = len(subset)
    n_cycles = n_points // points_per_cycle
    
    if n_points % points_per_cycle != 0:
        print(f"Warning: {n_points} points not divisible by {points_per_cycle}")
        return None
    
    # Efficient reshape for each feature
    reshaped_data = {}
    for feature in features:
        if feature in subset.columns:
            # Direct numpy reshape - assumes data is already ordered by step_number then phase
            feature_values = subset[feature].values
            reshaped_data[feature] = feature_values.reshape(n_cycles, points_per_cycle)
    
    return reshaped_data


def groupby_method(df, subject, task, features):
    """
    Traditional groupby method for comparison (SLOWER).
    """
    # Filter for specific subject and task
    subset = df[(df['subject'] == subject) & (df['task'] == task)]
    
    # Group by step number
    grouped = subset.groupby('step_number')
    
    reshaped_data = {}
    for feature in features:
        cycles_list = []
        for step, group in grouped:
            cycles_list.append(group[feature].values)
        reshaped_data[feature] = np.array(cycles_list)
    
    return reshaped_data


def demonstrate_efficiency():
    """Compare efficiency of reshape vs groupby methods."""
    print("=" * 60)
    print("EFFICIENCY COMPARISON: Reshape vs GroupBy")
    print("=" * 60)
    
    # Load data
    parquet_file = "source/conversion_scripts/Gtech_2023/gtech_2023_phase_with_steps.parquet"
    df = load_and_prepare_data(parquet_file)
    
    # Test parameters
    subject = df['subject'].iloc[0]
    task = df[df['subject'] == subject]['task'].iloc[0]
    features = ['knee_flexion_angle_right_rad', 'hip_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad']
    
    print(f"\nTesting with: {subject} - {task}")
    print(f"Features: {features}")
    
    # Time reshape method
    start_time = time.time()
    reshaped_data = efficient_reshape_method(df, subject, task, features)
    reshape_time = time.time() - start_time
    
    # Time groupby method
    start_time = time.time()
    grouped_data = groupby_method(df, subject, task, features)
    groupby_time = time.time() - start_time
    
    print(f"\nReshape method: {reshape_time:.4f} seconds")
    print(f"GroupBy method: {groupby_time:.4f} seconds")
    print(f"Speedup: {groupby_time/reshape_time:.1f}x faster")
    
    # Verify results are identical
    for feature in features:
        if not np.allclose(reshaped_data[feature], grouped_data[feature]):
            print(f"WARNING: Results differ for {feature}!")
        else:
            print(f"✓ Results match for {feature}")


def plot_efficient_data():
    """Demonstrate plotting with efficiently reshaped data."""
    # Load data
    parquet_file = "source/conversion_scripts/Gtech_2023/gtech_2023_phase_with_steps.parquet"
    df = load_and_prepare_data(parquet_file)
    
    # Get data for one subject-task
    subject = df['subject'].iloc[0]
    task = 'normal_walk'  # Use a walking task
    features = ['knee_flexion_angle_right_rad', 'hip_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad']
    
    # Efficiently reshape data
    reshaped_data = efficient_reshape_method(df, subject, task, features)
    
    if reshaped_data is None:
        print("No data found for this subject-task")
        return
    
    # Create phase axis (0-100%)
    phase_x = np.linspace(0, 100, 150)
    
    # Plot all cycles as spaghetti plot with mean
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for idx, (feature, ax) in enumerate(zip(features, axes)):
        data = reshaped_data[feature]
        n_cycles = data.shape[0]
        
        # Plot all cycles in gray
        for i in range(n_cycles):
            ax.plot(phase_x, data[i, :], 'gray', alpha=0.3, linewidth=0.8)
        
        # Plot mean in blue
        mean_curve = np.mean(data, axis=0)
        std_curve = np.std(data, axis=0)
        ax.plot(phase_x, mean_curve, 'b-', linewidth=2, label='Mean')
        ax.fill_between(phase_x, 
                       mean_curve - std_curve,
                       mean_curve + std_curve,
                       alpha=0.3, color='blue')
        
        # Formatting
        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Angle (deg)')
        ax.set_title(feature.replace('_', ' ').title())
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    plt.suptitle(f'{subject} - {task}')
    plt.tight_layout()
    plt.show()


def batch_process_subjects():
    """Demonstrate batch processing multiple subjects efficiently."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING EXAMPLE")
    print("=" * 60)
    
    # Load data
    parquet_file = "source/conversion_scripts/Gtech_2023/gtech_2023_phase_with_steps.parquet"
    df = load_and_prepare_data(parquet_file)
    
    # Process all subjects for a specific task
    task = 'normal_walk'
    feature = 'knee_angle_s_r'
    
    subjects = df[df['task'] == task]['subject'].unique()
    print(f"\nProcessing {len(subjects)} subjects for task: {task}")
    
    # Collect mean curves for all subjects
    mean_curves = {}
    
    start_time = time.time()
    for subject in subjects:
        reshaped_data = efficient_reshape_method(df, subject, task, [feature])
        if reshaped_data and feature in reshaped_data:
            mean_curves[subject] = np.mean(reshaped_data[feature], axis=0)
    
    process_time = time.time() - start_time
    print(f"Processed {len(mean_curves)} subjects in {process_time:.2f} seconds")
    print(f"Average time per subject: {process_time/len(mean_curves):.3f} seconds")
    
    # Plot all subject means
    phase_x = np.linspace(0, 100, 150)
    plt.figure(figsize=(10, 6))
    
    for subject, mean_curve in mean_curves.items():
        plt.plot(phase_x, mean_curve, alpha=0.7, label=subject)
    
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Knee Angle (deg)')
    plt.title(f'Mean Knee Angle Across Subjects - {task}')
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()


def advanced_analysis_example():
    """Show advanced analysis using the efficient structure."""
    print("\n" + "=" * 60)
    print("ADVANCED ANALYSIS EXAMPLE")
    print("=" * 60)
    
    # Load data
    parquet_file = "source/conversion_scripts/Gtech_2023/gtech_2023_phase_with_steps.parquet"
    df = load_and_prepare_data(parquet_file)
    
    subject = df['subject'].iloc[0]
    task = 'normal_walk'
    
    # Get knee angle data
    knee_data = efficient_reshape_method(df, subject, task, ['knee_angle_s_r'])
    
    if knee_data is None:
        return
    
    knee_angles = knee_data['knee_angle_s_r']
    n_cycles, n_points = knee_angles.shape
    
    print(f"\nAnalyzing {n_cycles} gait cycles")
    
    # 1. Range of Motion (ROM) per cycle
    rom_per_cycle = np.max(knee_angles, axis=1) - np.min(knee_angles, axis=1)
    print(f"\nROM Statistics:")
    print(f"  Mean ROM: {np.mean(rom_per_cycle):.1f}°")
    print(f"  Std ROM: {np.std(rom_per_cycle):.1f}°")
    
    # 2. Peak timing analysis
    peak_indices = np.argmax(knee_angles, axis=1)
    peak_phases = peak_indices / n_points * 100
    print(f"\nPeak Timing:")
    print(f"  Mean peak phase: {np.mean(peak_phases):.1f}%")
    print(f"  Std peak phase: {np.std(peak_phases):.1f}%")
    
    # 3. Cycle-to-cycle variability
    mean_curve = np.mean(knee_angles, axis=0)
    deviations = knee_angles - mean_curve[np.newaxis, :]
    rmse_per_cycle = np.sqrt(np.mean(deviations**2, axis=1))
    print(f"\nCycle Variability:")
    print(f"  Mean RMSE from average: {np.mean(rmse_per_cycle):.2f}°")
    
    # 4. Identify outlier cycles
    outlier_threshold = np.mean(rmse_per_cycle) + 2 * np.std(rmse_per_cycle)
    outlier_cycles = np.where(rmse_per_cycle > outlier_threshold)[0]
    print(f"\nOutlier cycles (>2 std from mean): {outlier_cycles.tolist()}")


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_efficiency()
    # plot_efficient_data()  # Uncomment to see plots
    # batch_process_subjects()  # Uncomment to see batch processing
    advanced_analysis_example()