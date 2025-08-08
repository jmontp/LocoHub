# Quick Start Guide

[Skip to main content](#main-content)

Get up and running with standardized locomotion data in 5 minutes.

<a name="main-content"></a>

!!! tip "Prerequisites"
    Make sure you've completed the [Installation](installation/) first.

## Biomechanics Primer

!!! info "New to Gait Analysis?"
    **Gait Cycle**: The walking pattern from heel strike to the next heel strike of the same foot (typically 1-2 seconds)
    
    **Phase-Indexed Data**: Normalizes each gait cycle to exactly 150 data points (0-100% of cycle), enabling comparison across different walking speeds and individuals
    
    **Key Variables**: 
    - Joint angles (knee_flexion_angle) measure how much joints bend/extend
    - Joint moments (hip_moment) measure forces acting around joints
    - Ipsilateral/Contralateral: Same-side vs opposite-side relative to a reference

## What You'll Learn

In this quick start, you'll:

1. Load a standardized dataset using the LocomotionData class
2. Explore the data structure
3. Extract gait cycle data
4. Create your first visualization
5. Calculate basic biomechanical metrics

## Load Your First Dataset

=== "Python"

    ```python
    # Import the locomotion analysis library
    import sys
    sys.path.append('lib/core')  # Adjust path to your installation
    from locomotion_analysis import LocomotionData
    import numpy as np
    import matplotlib.pyplot as plt

    # Load a standardized dataset with built-in validation
    # Using demo data included with the library
    # Note: Specify phase column name if different from default
    loco = LocomotionData('tests/test_data/demo_clean_phase.parquet',
                         phase_col='phase_percent')
    
    # Explore the dataset
    print(f"Subjects: {loco.get_subjects()}")
    print(f"Tasks: {loco.get_tasks()}")
    
    # Check data validation
    validation_report = loco.get_validation_report()
    print(f"Valid features: {validation_report['standard_compliant']}")
    ```

=== "MATLAB"

    ```matlab
    % Load a standardized dataset
    data = readtable('tests/test_data/demo_clean_phase.parquet');
    
    % Explore the dataset
    fprintf('Dataset size: %d rows, %d columns\n', height(data), width(data));
    fprintf('Columns: %s\n', strjoin(data.Properties.VariableNames, ', '));
    fprintf('Unique tasks: %s\n', strjoin(unique(data.task), ', '));
    fprintf('Unique subjects: %s\n', strjoin(unique(data.subject), ', '));
    ```

**Expected Output:**
```
Subjects: ['SUB01', 'SUB02', 'SUB03']
Tasks: ['decline_walking', 'incline_walking', 'level_walking']
Valid features: ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad', 'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
```

## Understanding the Data Structure

All standardized datasets follow the same structure:

### Required Columns
- **`subject`**: Subject identifier (e.g., 'SUB01')
- **`task`**: Task name (e.g., 'level_walking')
- **`step`**: Step/cycle number within the trial
- **`phase_percent`**: Gait cycle phase (0-100%)

### Biomechanical Variables
The demo dataset includes joint angles for the lower extremity:
- **Joint angles**: `{joint}_flexion_angle_{side}_rad`
  - Hip: `hip_flexion_angle_ipsi_rad`, `hip_flexion_angle_contra_rad`
  - Knee: `knee_flexion_angle_ipsi_rad`, `knee_flexion_angle_contra_rad`
  - Ankle: `ankle_flexion_angle_ipsi_rad`, `ankle_flexion_angle_contra_rad`

### Naming Convention
- **Side**: `ipsi` (ipsilateral) or `contra` (contralateral)
- **Units**: Always included in variable name (`rad` for radians)
- **Phase**: Data is phase-indexed with exactly 150 points per gait cycle (0-100%)

## Extract Gait Cycle Data

Use the LocomotionData class methods to extract structured gait cycle data:

=== "Python"

    ```python
    # Extract gait cycles for level walking from one subject
    cycles, features = loco.get_cycles('SUB01', 'level_walking')
    
    print(f"Cycles shape: {cycles.shape}")  # (n_cycles, 150, n_features)
    print(f"Features: {features}")
    print(f"Number of gait cycles: {cycles.shape[0]}")
    print(f"Points per cycle: {cycles.shape[1]}")
    
    # Get mean patterns across all cycles
    mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
    print(f"Mean knee angle range: {np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad'].min()):.1f} to {np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad'].max()):.1f} degrees")
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

**Expected Output:**
```
Cycles shape: (3, 150, 6)
Features: ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad', 'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
Number of gait cycles: 3
Points per cycle: 150
Mean knee angle range: -6.2 to 40.5 degrees
```

## Create Your First Visualization

Use the built-in plotting methods to create publication-ready figures:

=== "Python"

    ```python
    # Create a phase pattern plot using the LocomotionData method
    fig = loco.plot_phase_patterns('SUB01', 'level_walking', 
                                   ['knee_flexion_angle_ipsi_rad'])
    
    # Save the plot
    plt.savefig('knee_angle_level_walking.png', dpi=300, bbox_inches='tight')
    print("Plot saved as 'knee_angle_level_walking.png'")
    
    # Optional: Create a custom plot with mean patterns
    mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
    phase_points = np.linspace(0, 100, 150)  # 150 points from 0-100%
    
    plt.figure(figsize=(10, 6))
    plt.plot(phase_points, np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad']), 
             'b-', linewidth=2, label='Knee Flexion')
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Joint Angle (degrees)')
    plt.title('SUB01 - Level Walking: Knee Flexion Angle')
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 100)
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Full Extension')
    plt.legend()
    plt.tight_layout()
    plt.savefig('custom_knee_plot.png', dpi=300, bbox_inches='tight')
    print("Custom plot saved as 'custom_knee_plot.png'")
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

Compare gait patterns between different locomotion tasks:

=== "Python"

    ```python
    # Compare knee angles across different tasks
    tasks = ['level_walking', 'incline_walking', 'decline_walking']
    phase_points = np.linspace(0, 100, 150)
    
    plt.figure(figsize=(15, 5))
    
    for i, task in enumerate(tasks):
        mean_patterns = loco.get_mean_patterns('SUB01', task)
        
        plt.subplot(1, 3, i+1)
        plt.plot(phase_points, np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad']), 
                 'b-', linewidth=2)
        plt.xlabel('Gait Cycle (%)')
        plt.ylabel('Knee Flexion (degrees)')
        plt.title(f'{task.replace("_", " ").title()}')
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 100)
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    plt.savefig('knee_angle_task_comparison.png', dpi=300, bbox_inches='tight')
    print("Task comparison plot saved as 'knee_angle_task_comparison.png'")
    
    # Use built-in task comparison method
    fig = loco.plot_task_comparison('SUB01', tasks, ['knee_flexion_angle_ipsi_rad'])
    plt.savefig('builtin_task_comparison.png', dpi=300, bbox_inches='tight')
    print("Built-in comparison plot saved as 'builtin_task_comparison.png'")
    ```

=== "MATLAB"

    ```matlab
    % Compare knee angles across different tasks
    tasks = {'level_walking', 'incline_walking', 'decline_walking'};
    
    figure('Position', [100, 100, 1200, 400]);
    
    for i = 1:length(tasks)
        task = tasks{i};
        task_data = data(strcmp(data.task, task), :);
        
        if ~isempty(task_data)
            avg_knee = groupsummary(task_data, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
            
            subplot(1, 3, i);
            plot(avg_knee.phase_percent, rad2deg(avg_knee.mean_knee_flexion_angle_ipsi_rad), 'b-', 'LineWidth', 2);
            xlabel('Gait Cycle (%)');
            ylabel('Knee Flexion (degrees)');
            title(strrep(task, '_', ' '));
            grid on;
            xlim([0, 100]);
            yline(0, 'k--', 'Alpha', 0.5);
        end
    end
    
    saveas(gcf, 'knee_angle_task_comparison.png');
    
    fprintf('Task comparison plot saved as ''knee_angle_task_comparison.png''\n');
    ```

## Calculate Basic Metrics

Extract meaningful biomechanical parameters using built-in analysis methods:

=== "Python"

    ```python
    # Get summary statistics for the gait cycles
    stats = loco.get_summary_statistics('SUB01', 'level_walking')
    
    print("Summary Statistics for Level Walking:")
    print(f"Number of cycles: {stats['cycle_count']}")
    print(f"Phase points per cycle: {stats['phase_points']}")
    
    # Calculate range of motion (ROM) from the 3D cycle data
    cycles, features = loco.get_cycles('SUB01', 'level_walking')
    
    # ROM for knee angle across all cycles
    knee_idx = features.index('knee_flexion_angle_ipsi_rad')
    knee_rom_per_cycle = np.max(cycles[:, :, knee_idx], axis=1) - np.min(cycles[:, :, knee_idx], axis=1)
    
    print(f"\nKnee ROM Analysis:")
    print(f"ROM per cycle (degrees): {np.degrees(knee_rom_per_cycle)}")
    print(f"Average ROM: {np.degrees(knee_rom_per_cycle.mean()):.1f} ± {np.degrees(knee_rom_per_cycle.std()):.1f} degrees")
    
    # Peak values during stance phase (first 60% of gait cycle)
    stance_points = int(0.6 * 150)  # 60% of 150 points
    peak_knee_stance = np.max(cycles[:, :stance_points, knee_idx], axis=1)
    
    print(f"Peak knee flexion in stance: {np.degrees(peak_knee_stance.mean()):.1f} ± {np.degrees(peak_knee_stance.std()):.1f} degrees")
    
    # Compare mean patterns between subjects
    mean_sub1 = loco.get_mean_patterns('SUB01', 'level_walking')
    mean_sub2 = loco.get_mean_patterns('SUB02', 'level_walking')
    
    diff = np.degrees(mean_sub1['knee_flexion_angle_ipsi_rad'] - mean_sub2['knee_flexion_angle_ipsi_rad'])
    print(f"Mean difference between SUB01 and SUB02: {diff.mean():.1f} ± {diff.std():.1f} degrees")
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

- ✅ Loaded a standardized dataset with the LocomotionData class
- ✅ Explored the data structure and validation features
- ✅ Extracted structured gait cycle data (3D arrays)
- ✅ Created publication-ready visualizations
- ✅ Calculated biomechanical metrics and statistics

## Key Concepts Learned

### Data Organization
- **Phase-indexed data**: 150 points per gait cycle (0-100%)
- **3D arrays**: (n_cycles, 150_points, n_features) for efficient analysis
- **Standard naming**: Consistent variable names with units included

### LocomotionData Methods
- `get_subjects()`, `get_tasks()` - Explore available data
- `get_cycles()` - Extract 3D gait cycle arrays
- `get_mean_patterns()` - Calculate ensemble averages
- `plot_phase_patterns()` - Built-in visualization
- `get_summary_statistics()` - Basic descriptive statistics

## What's Next?

### Learn More
- **[Your First Dataset](first_dataset/)** - Complete analysis walkthrough
- **[Python Tutorial](../tutorials/python/getting_started_python/)** - Comprehensive Python guide
- **[MATLAB Tutorial](../tutorials/matlab/getting_started_matlab/)** - Comprehensive MATLAB guide

### Explore Advanced Features
- **[Working with Data](../user_guide/working_with_data/)** - Advanced analysis techniques
- **[Validation Reports](../user_guide/validation_reports/)** - Quality assessment tools
- **[API Reference](../reference/api_reference/)** - Complete function documentation

### Real Datasets
- **[Dataset Documentation](../reference/datasets_documentation/)** - Available standardized datasets
- **[Contributor Guide](../contributor_guide/)** - Add your own datasets
- **[Dataset Conversion](../contributor_guide/dataset_conversion/)** - Technical conversion guide

## Common Next Steps

!!! question "Want to analyze your own data?"
    See the [Contributor Guide](../contributor_guide/) to convert your datasets to the standard format.

!!! question "Need more analysis examples?"
    Check out the comprehensive [Tutorials](../tutorials/) with real-world use cases.

!!! question "Working with large datasets?"
    Learn about memory-efficient techniques in [Working with Data](../user_guide/working_with_data/).

!!! tip "Demo Data Location"
    The demo data used in this guide is located at: `tests/test_data/demo_clean_phase.parquet`
    
    You can use this for testing and learning before working with your own datasets.

## Troubleshooting

!!! warning "Common Issues"

    **ImportError: No module named 'locomotion_analysis'**
    
    Make sure the path to `lib/core` is correct for your installation:
    ```python
    import sys
    sys.path.append('/path/to/your/locomotion-data-standardization/lib/core')
    ```

    **ValueError: Missing required columns**
    
    Your dataset may use different column names. Specify them explicitly:
    ```python
    loco = LocomotionData('your_data.parquet',
                         subject_col='participant_id',
                         task_col='condition', 
                         phase_col='gait_percent')
    ```

    **Empty plots or no output**
    
    For non-interactive environments, save plots instead of showing them:
    ```python
    import matplotlib
    matplotlib.use('Agg')  # Use before importing pyplot
    import matplotlib.pyplot as plt
    ```

---

*Questions? Check our [Troubleshooting Guide](../user_guide/troubleshooting/) or open an issue on [GitHub](https://github.com/your-org/locomotion-data-standardization/issues).*