#!/usr/bin/env python3
"""
Tutorial Test: Python Getting Started Guide

Created: 2025-06-11 (moved from docs/tutorials/python/)
Purpose: Validates the Python getting started tutorial functionality and examples

Intent:
This test script validates all functionality covered in the Python getting started tutorial,
ensuring that basic data loading and manipulation operations work correctly for:

**PRIMARY FUNCTIONS:**
1. **Data Loading**: Verify CSV data loading from tutorial test files
2. **Data Joining**: Test pandas merge operations on locomotion and task data
3. **Task Filtering**: Validate filtering operations for specific locomotion tasks
4. **Phase Analysis**: Test phase-based data manipulation and groupby operations
5. **Basic Calculations**: Verify range of motion and summary statistics

Usage:
    cd source/tests
    python test_tutorial_getting_started_python.py

Expected Output:
- Successful data loading from test CSV files
- Data combination and filtering results
- Phase-based analysis outputs
- Range of motion calculations
- Tutorial completion confirmation

This test ensures new users can successfully follow the getting started guide
and perform basic biomechanical data analysis operations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

print("Working directory:", os.getcwd())
print("Testing Python tutorial...")

# 1. Loading Data
try:
    df_locomotion = pd.read_csv('../../docs/tutorials/test_files/locomotion_data.csv')
    df_tasks = pd.read_csv('../../docs/tutorials/test_files/task_info.csv')

    print("\nLocomotion Data:")
    print(df_locomotion.head(3))
    print("\nTask Information:")
    print(df_tasks)
    
    # 2. Combining Data (Outer Join)
    df_combined = pd.merge(df_locomotion, df_tasks, on=['step_id', 'task_id', 'subject_id'], how='outer')
    print("\nCombined Data (first 3 rows):")
    print(df_combined.head(3))

    # 3. Filtering for a Particular Task
    df_incline_walking = df_combined[df_combined['task_name'] == 'incline_walking']
    print("\nData for 'incline_walking' task:")
    print(df_incline_walking)

    # 4. Phase-Based Analysis with Efficient Reshaping
    # For phase-indexed data (with 150 points per cycle), we can use efficient reshaping
    # instead of groupby operations for better performance
    
    # 4.1 Simulate phase-indexed data structure
    # In real datasets, phase data comes pre-normalized to 150 points per cycle
    df_with_phase = df_locomotion.copy()
    
    # Add phase column (0-100%) for each step
    df_with_phase['phase_%'] = 0.0
    df_with_phase['step_number'] = 0
    
    for i, step in enumerate(df_locomotion['step_id'].unique()):
        step_mask = df_locomotion['step_id'] == step
        num_points = step_mask.sum()
        
        # Simulate 150-point normalization
        if num_points > 0:
            # In real data, this would be exactly 150 points
            phase_values = np.linspace(0, 100 * (149/150), num_points)
            df_with_phase.loc[step_mask, 'phase_%'] = phase_values
            df_with_phase.loc[step_mask, 'step_number'] = i
    
    # 4.2 Efficient reshape method (recommended for phase-indexed data)
    # Group by subject and task for efficient processing
    df_with_phase = pd.merge(df_with_phase, df_tasks, on=['step_id', 'task_id', 'subject_id'], how='inner')
    
    # Example: Get all cycles for one task efficiently
    level_walking = df_with_phase[df_with_phase['task_name'] == 'level_walking']
    if len(level_walking) > 0:
        # In real phase-indexed data with 150 points per cycle:
        # n_cycles = len(level_walking) // 150
        # knee_data = level_walking['knee_flexion_angle_rad'].values.reshape(n_cycles, 150)
        
        # For this demo with variable points:
        unique_steps = level_walking['step_number'].unique()
        print(f"\nEfficient processing for level_walking:")
        print(f"  Number of cycles: {len(unique_steps)}")
        
        # Calculate mean curve efficiently
        if len(unique_steps) > 0:
            # Collect data for each cycle
            cycle_data = []
            for step_num in unique_steps:
                cycle = level_walking[level_walking['step_number'] == step_num]['knee_flexion_angle_rad'].values
                if len(cycle) > 0:
                    cycle_data.append(cycle)
            
            # For demonstration, show statistics
            cycle_lengths = [len(c) for c in cycle_data]
            print(f"  Cycle lengths: min={min(cycle_lengths)}, max={max(cycle_lengths)}, mean={np.mean(cycle_lengths):.1f}")
    
    # 4.3 Traditional phase binning method (for comparison)
    phase_bins = np.linspace(0, 100, 101)
    labels = phase_bins[:-1]
    df_with_phase['phase_bin'] = pd.cut(df_with_phase['phase_%'], bins=phase_bins, labels=labels, include_lowest=True)
    
    # Calculate average by phase
    phase_averages = df_with_phase.groupby('phase_bin')['knee_flexion_angle_rad'].mean()
    print("\nAverage knee flexion angle by phase (first 5 phases):")
    print(phase_averages.head(5))
    
    # Compare tasks by phase
    phase_by_task = {}
    for task in df_with_phase['task_name'].unique():
        if pd.notnull(task):
            task_data = df_with_phase[df_with_phase['task_name'] == task]
            phase_by_task[task] = task_data.groupby('phase_bin')['knee_flexion_angle_rad'].mean()
    
    print("\nPhase-based knee flexion angle by task (first 3 phases):")
    for task, data in phase_by_task.items():
        print(f"Task: {task}")
        print(data.head(3))

    # 5. Basic Plotting
    # 5.1 Plot time-series (save to file)
    plt.figure(figsize=(10, 4))
    plt.plot(df_incline_walking['time_s'], df_incline_walking['knee_flexion_angle_rad'], marker='o', linestyle='-')
    plt.xlabel('Time (s)')
    plt.ylabel('Knee Flexion Angle (rad)')
    plt.title('Knee Flexion Angle during Incline Walking')
    plt.grid(True)
    plt.savefig('knee_angle_incline.png')
    print("\nPlot saved as 'knee_angle_incline.png'")

    # 5.2 Bar plot of average by task
    plt.figure(figsize=(8, 5))
    task_means = {task: data.mean() for task, data in phase_by_task.items()}
    plt.bar(list(task_means.keys()), list(task_means.values()))
    plt.xlabel('Task Name')
    plt.ylabel('Average Knee Flexion Angle (rad)')
    plt.title('Average Knee Flexion Angle by Task')
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig('knee_angle_by_task.png')
    print("Plot saved as 'knee_angle_by_task.png'")

    # 6. Calculating Derived Metrics
    # Calculate ROM (Range of Motion) for knee_flexion_angle_rad
    # Filter for level_walking data
    df_level_walking = df_with_phase[df_with_phase['task_name'] == 'level_walking']
    knee_rom_per_step = df_level_walking.groupby('step_id')['knee_flexion_angle_rad'].apply(lambda x: x.max() - x.min())
    knee_rom_per_step = knee_rom_per_step.rename('knee_flexion_angle_rom_rad')
    print("\nKnee Flexion Angle ROM per step by task:")
    print(knee_rom_per_step)

    print("\nPython tutorial test completed successfully!")

except Exception as e:
    print(f"Error during testing: {e}") 