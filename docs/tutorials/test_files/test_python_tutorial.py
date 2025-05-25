# Test script for Python tutorial
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

print("Working directory:", os.getcwd())
print("Testing Python tutorial...")

# 1. Loading Data
try:
    df_locomotion = pd.read_csv('locomotion_data.csv')
    df_tasks = pd.read_csv('task_info.csv')

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

    # 4. Phase-Based Averaging
    # 4.1 Add phase data for demonstration
    df_with_phase = df_locomotion.copy()
    for step in df_locomotion['step_id'].unique():
        step_mask = df_locomotion['step_id'] == step
        num_points = step_mask.sum()
        df_with_phase.loc[step_mask, 'phase_%'] = np.linspace(0, 100, num_points)

    # Create phase bins
    phase_bins = np.linspace(0, 100, 101)
    labels = phase_bins[:-1]
    df_with_phase['phase_bin'] = pd.cut(df_with_phase['phase_%'], bins=phase_bins, labels=labels, include_lowest=True)

    # Calculate average by phase
    phase_averages = df_with_phase.groupby('phase_bin')['knee_flexion_angle_rad'].mean()
    print("\nAverage knee flexion angle by phase (first 5 phases):")
    print(phase_averages.head(5))

    # Compare tasks by phase
    df_with_phase = pd.merge(df_with_phase, df_tasks, on=['step_id', 'task_id', 'subject_id'], how='inner')
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