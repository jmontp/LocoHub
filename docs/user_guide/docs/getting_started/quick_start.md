# Quick Start Guide

Get up and running with standardized locomotion data in 10 minutes.

!!! tip "Prerequisites"
    Make sure you've completed the [Installation](installation/) first.

## What You'll Learn

In this quick start, you'll:

1. Load a standardized dataset
2. Explore the data structure
3. Filter data for specific tasks
4. Create your first visualization
5. Calculate basic biomechanical metrics

## Load Your First Dataset

=== "Python"

    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

    # Load a standardized dataset
    # Note: Replace with actual dataset path
    data = pd.read_parquet('sample_gtech_2023_phase.parquet')
    
    # Explore the dataset
    print(f"Dataset shape: {data.shape}")
    print(f"Columns: {list(data.columns)}")
    print(f"Unique tasks: {data['task'].unique()}")
    print(f"Unique subjects: {data['subject'].unique()}")
    ```

=== "MATLAB"

    ```matlab
    % Load a standardized dataset
    data = readtable('sample_gtech_2023_phase.parquet');
    
    % Explore the dataset
    fprintf('Dataset size: %d rows, %d columns\n', height(data), width(data));
    fprintf('Columns: %s\n', strjoin(data.Properties.VariableNames, ', '));
    fprintf('Unique tasks: %s\n', strjoin(unique(data.task), ', '));
    fprintf('Unique subjects: %s\n', strjoin(unique(data.subject), ', '));
    ```

**Expected Output:**
```
Dataset shape: (1500, 8)
Columns: ['subject', 'task', 'step', 'phase_percent', 'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad', 'vertical_grf_ipsi_N']
Unique tasks: ['level_walking', 'incline_walking', 'up_stairs']
Unique subjects: ['SUB01', 'SUB02', 'SUB03']
```

## Understanding the Data Structure

All standardized datasets follow the same structure:

### Required Columns
- **`subject`**: Subject identifier (e.g., 'SUB01')
- **`task`**: Task name (e.g., 'level_walking')
- **`step`**: Step/cycle number within the trial
- **`phase_percent`**: Gait cycle phase (0-100%)

### Biomechanical Variables
- **Joint angles**: `{joint}_flexion_angle_{side}_rad`
- **Joint moments**: `{joint}_moment_{side}_Nm`
- **Ground forces**: `{direction}_grf_{side}_N`

### Naming Convention
- **Side**: `ipsi` (ipsilateral) or `contra` (contralateral)
- **Units**: Always included in variable name (`rad`, `Nm`, `N`)

## Filter Data for Analysis

Focus on specific conditions for your analysis:

=== "Python"

    ```python
    # Filter for level walking from one subject
    level_walking = data[
        (data['task'] == 'level_walking') & 
        (data['subject'] == 'SUB01')
    ]
    
    print(f"Level walking data: {level_walking.shape[0]} rows")
    print(f"Number of gait cycles: {level_walking['step'].nunique()}")
    
    # Look at one complete gait cycle
    single_cycle = level_walking[level_walking['step'] == 1]
    print(f"Single gait cycle: {single_cycle.shape[0]} points")
    ```

=== "MATLAB"

    ```matlab
    % Filter for level walking from one subject
    level_walking = data(strcmp(data.task, 'level_walking') & ...
                        strcmp(data.subject, 'SUB01'), :);
    
    fprintf('Level walking data: %d rows\n', height(level_walking));
    fprintf('Number of gait cycles: %d\n', length(unique(level_walking.step)));
    
    % Look at one complete gait cycle
    single_cycle = level_walking(level_walking.step == 1, :);
    fprintf('Single gait cycle: %d points\n', height(single_cycle));
    ```

## Create Your First Visualization

Plot knee angle across the gait cycle:

=== "Python"

    ```python
    # Calculate average knee angle across all steps
    avg_knee = level_walking.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(avg_knee.index, np.degrees(avg_knee.values), 'b-', linewidth=2)
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Knee Flexion Angle (degrees)')
    plt.title('Average Knee Angle - Level Walking')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 100)
    
    # Add reference lines
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Full Extension')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('knee_angle_level_walking.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Plot saved as 'knee_angle_level_walking.png'")
    ```

=== "MATLAB"

    ```matlab
    % Calculate average knee angle across all steps
    avg_knee = groupsummary(level_walking, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
    
    % Create the plot
    figure('Position', [100, 100, 800, 500]);
    plot(avg_knee.phase_percent, rad2deg(avg_knee.mean_knee_flexion_angle_ipsi_rad), 'b-', 'LineWidth', 2);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (degrees)');
    title('Average Knee Angle - Level Walking');
    grid on;
    xlim([0, 100]);
    
    % Add reference line
    hold on;
    yline(0, 'k--', 'Alpha', 0.5, 'DisplayName', 'Full Extension');
    legend('Knee Angle', 'Full Extension');
    hold off;
    
    saveas(gcf, 'knee_angle_level_walking.png');
    
    fprintf('Plot saved as ''knee_angle_level_walking.png''\n');
    ```

## Compare Across Tasks

See how gait patterns differ between tasks:

=== "Python"

    ```python
    # Compare knee angles across different tasks
    tasks = ['level_walking', 'incline_walking', 'up_stairs']
    
    plt.figure(figsize=(12, 8))
    
    for i, task in enumerate(tasks):
        if task in data['task'].values:
            task_data = data[data['task'] == task]
            avg_knee = task_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            
            plt.subplot(2, 2, i+1)
            plt.plot(avg_knee.index, np.degrees(avg_knee.values), 'b-', linewidth=2)
            plt.xlabel('Gait Cycle (%)')
            plt.ylabel('Knee Flexion (degrees)')
            plt.title(f'Knee Angle - {task.replace("_", " ").title()}')
            plt.grid(True, alpha=0.3)
            plt.xlim(0, 100)
    
    plt.tight_layout()
    plt.savefig('knee_angle_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Comparison plot saved as 'knee_angle_comparison.png'")
    ```

=== "MATLAB"

    ```matlab
    % Compare knee angles across different tasks
    tasks = {'level_walking', 'incline_walking', 'up_stairs'};
    
    figure('Position', [100, 100, 1200, 800]);
    
    for i = 1:length(tasks)
        task = tasks{i};
        task_data = data(strcmp(data.task, task), :);
        
        if ~isempty(task_data)
            avg_knee = groupsummary(task_data, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
            
            subplot(2, 2, i);
            plot(avg_knee.phase_percent, rad2deg(avg_knee.mean_knee_flexion_angle_ipsi_rad), 'b-', 'LineWidth', 2);
            xlabel('Gait Cycle (%)');
            ylabel('Knee Flexion (degrees)');
            title(['Knee Angle - ', strrep(task, '_', ' ')]);
            grid on;
            xlim([0, 100]);
        end
    end
    
    saveas(gcf, 'knee_angle_comparison.png');
    
    fprintf('Comparison plot saved as ''knee_angle_comparison.png''\n');
    ```

## Calculate Basic Metrics

Extract meaningful biomechanical parameters:

=== "Python"

    ```python
    # Calculate range of motion (ROM) for each gait cycle
    def calculate_rom(group):
        return group.max() - group.min()
    
    # ROM for each step
    knee_rom = level_walking.groupby('step')['knee_flexion_angle_ipsi_rad'].apply(calculate_rom)
    
    print("Knee ROM by step (degrees):")
    print(np.degrees(knee_rom))
    print(f"\nAverage knee ROM: {np.degrees(knee_rom.mean()):.1f} ± {np.degrees(knee_rom.std()):.1f} degrees")
    
    # Peak knee flexion in stance phase (0-60% of gait cycle)
    stance_phase = level_walking[level_walking['phase_percent'] <= 60]
    peak_knee_stance = stance_phase.groupby('step')['knee_flexion_angle_ipsi_rad'].max()
    
    print(f"Peak knee flexion in stance: {np.degrees(peak_knee_stance.mean()):.1f} ± {np.degrees(peak_knee_stance.std()):.1f} degrees")
    ```

=== "MATLAB"

    ```matlab
    % Calculate range of motion (ROM) for each gait cycle
    knee_rom = groupsummary(level_walking, 'step', {'min', 'max'}, 'knee_flexion_angle_ipsi_rad');
    knee_rom.rom = knee_rom.max_knee_flexion_angle_ipsi_rad - knee_rom.min_knee_flexion_angle_ipsi_rad;
    
    fprintf('Knee ROM by step (degrees):\n');
    disp(rad2deg(knee_rom.rom));
    fprintf('Average knee ROM: %.1f ± %.1f degrees\n', ...
        rad2deg(mean(knee_rom.rom)), rad2deg(std(knee_rom.rom)));
    
    % Peak knee flexion in stance phase (0-60% of gait cycle)
    stance_phase = level_walking(level_walking.phase_percent <= 60, :);
    peak_knee_stance = groupsummary(stance_phase, 'step', 'max', 'knee_flexion_angle_ipsi_rad');
    
    fprintf('Peak knee flexion in stance: %.1f ± %.1f degrees\n', ...
        rad2deg(mean(peak_knee_stance.max_knee_flexion_angle_ipsi_rad)), ...
        rad2deg(std(peak_knee_stance.max_knee_flexion_angle_ipsi_rad)));
    ```

## Summary

Congratulations! You've successfully:

- ✅ Loaded a standardized dataset
- ✅ Explored the data structure
- ✅ Filtered data for specific conditions
- ✅ Created visualizations
- ✅ Calculated biomechanical metrics

## What's Next?

### Learn More
- **[Your First Dataset](first_dataset/)** - Complete analysis walkthrough
- **[Python Tutorial](../tutorials/python/getting_started_python/)** - Comprehensive Python guide
- **[MATLAB Tutorial](../tutorials/matlab/getting_started_matlab/)** - Comprehensive MATLAB guide

### Explore Advanced Features
- **[Working with Data](../user_guide/working_with_data/)** - Advanced analysis techniques
- **[Validation Reports](../user_guide/validation_reports/)** - Quality assessment tools
- **[API Reference](../reference/api_reference/)** - Complete function documentation

### Contribute Data
- **[Contributor Guide](../contributor_guide/)** - Add your own datasets
- **[Dataset Conversion](../contributor_guide/dataset_conversion/)** - Technical conversion guide

## Common Next Steps

!!! question "Want to analyze your own data?"
    See the [Contributor Guide](../contributor_guide/) to convert your datasets to the standard format.

!!! question "Need more analysis examples?"
    Check out the comprehensive [Tutorials](../tutorials/) with real-world use cases.

!!! question "Working with large datasets?"
    Learn about memory-efficient techniques in [Working with Data](../user_guide/working_with_data/).

---

*Questions? Check our [Troubleshooting Guide](../user_guide/troubleshooting/) or open an issue on [GitHub](https://github.com/your-org/locomotion-data-standardization/issues).*