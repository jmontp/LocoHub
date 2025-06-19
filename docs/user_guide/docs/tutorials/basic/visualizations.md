# Visualization Guide

Explore powerful visualization techniques for standardized locomotion data analysis.

## Quick Start

Visualize gait patterns with the LocomotionData library:

```python
from locomotion_analysis import LocomotionData

# Load data and create basic visualization
loco = LocomotionData('locomotion_data.csv')
loco.plot_phase_patterns('SUB01', 'level_walking', 
                        ['knee_flexion_angle_ipsi_rad'])
```

## Available Plotting Methods

The LocomotionData library provides three core visualization methods:

### 1. Phase Pattern Plots

Display gait cycle patterns normalized to 0-100% of the cycle:

```python
# Show individual cycles (spaghetti plot)
loco.plot_phase_patterns(subject='SUB01', 
                        task='level_walking',
                        features=['knee_flexion_angle_ipsi_rad'],
                        plot_type='spaghetti')

# Show mean ± standard deviation
loco.plot_phase_patterns(subject='SUB01',
                        task='level_walking', 
                        features=['knee_flexion_angle_ipsi_rad'],
                        plot_type='mean')

# Show both individual cycles and mean
loco.plot_phase_patterns(subject='SUB01',
                        task='level_walking',
                        features=['knee_flexion_angle_ipsi_rad'], 
                        plot_type='both')
```

**Visualization Features:**
- Gray lines: Valid cycles passing validation
- Red lines: Invalid cycles failing validation  
- Blue line: Mean pattern (valid cycles only)
- Blue shading: ±1 standard deviation

### 2. Task Comparison Plots

Compare mean patterns across different locomotion tasks:

```python
# Compare walking conditions
loco.plot_task_comparison(subject='SUB01',
                         tasks=['level_walking', 'incline_walking'],
                         features=['knee_flexion_angle_ipsi_rad',
                                  'hip_flexion_angle_ipsi_rad'])
```

**Features:**
- Overlaid mean patterns for each task
- Automatic color assignment
- Synchronized axes for direct comparison

### 3. Time Series Plots

Visualize continuous time-indexed data:

```python
# Plot time series data
loco.plot_time_series(subject='SUB01',
                     task='level_walking',
                     features=['knee_flexion_angle_ipsi_rad'],
                     time_col='time_s')
```

## Customization Options

### Saving Plots

All plotting methods support saving to file:

```python
# Save as high-resolution PNG
loco.plot_phase_patterns('SUB01', 'level_walking',
                        ['knee_flexion_angle_ipsi_rad'],
                        save_path='knee_pattern.png')
```

### Multi-Feature Plotting

Plot multiple biomechanical variables simultaneously:

```python
# Plot multiple joint angles
features = ['hip_flexion_angle_ipsi_rad',
           'knee_flexion_angle_ipsi_rad', 
           'ankle_flexion_angle_ipsi_rad']

loco.plot_phase_patterns('SUB01', 'level_walking', features)
```

The library automatically arranges subplots in a grid layout (max 3 columns).

## Advanced Visualization

### Custom Plotting with 3D Data Access

Access raw 3D arrays for custom visualization:

```python
import matplotlib.pyplot as plt
import numpy as np

# Get 3D data array
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
# data_3d shape: (n_cycles, 150, n_features)

# Custom percentile plot
phase_x = np.linspace(0, 100, 150)
plt.figure(figsize=(10, 6))

# Plot median and percentiles
median = np.median(data_3d[:, :, 0], axis=0)
p25 = np.percentile(data_3d[:, :, 0], 25, axis=0)
p75 = np.percentile(data_3d[:, :, 0], 75, axis=0)

plt.fill_between(phase_x, p25, p75, alpha=0.3, label='25-75%')
plt.plot(phase_x, median, 'b-', linewidth=2, label='Median')

plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion (rad)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### Statistical Visualization

Combine with statistical analysis:

```python
# Get ROM data for visualization
rom_data = loco.calculate_rom('SUB01', 'level_walking')

# Create box plot of ROM values
import matplotlib.pyplot as plt

features = ['hip_flexion_angle_ipsi_rad', 
           'knee_flexion_angle_ipsi_rad']
rom_values = [rom_data[f] for f in features]

plt.figure(figsize=(8, 6))
plt.boxplot(rom_values, labels=[f.split('_')[0] for f in features])
plt.ylabel('Range of Motion (rad)')
plt.title('Joint ROM Comparison')
plt.grid(True, alpha=0.3)
plt.show()
```

### Population-Level Visualization

Visualize data across multiple subjects:

```python
# Plot mean patterns for all subjects
subjects = loco.get_subjects()
phase_x = np.linspace(0, 100, 150)

plt.figure(figsize=(10, 6))
for subject in subjects[:5]:  # First 5 subjects
    patterns = loco.get_mean_patterns(subject, 'level_walking',
                                     ['knee_flexion_angle_ipsi_rad'])
    if 'knee_flexion_angle_ipsi_rad' in patterns:
        plt.plot(phase_x, patterns['knee_flexion_angle_ipsi_rad'],
                label=subject, alpha=0.7)

plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion (rad)')
plt.title('Population Knee Flexion Patterns')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

## Minimal Example Dataset

For testing visualizations with minimal data:

```python
import pandas as pd
import numpy as np

# Create minimal test dataset (150 points = 1 gait cycle)
phase = np.linspace(0, 100, 150)
test_data = pd.DataFrame({
    'subject': 'TEST01',
    'task': 'level_walking',
    'step': 1,
    'phase_percent': phase,
    'knee_flexion_angle_ipsi_rad': 0.8 * np.sin(2*np.pi*phase/100) + 0.2,
    'hip_flexion_angle_ipsi_rad': 0.4 * np.sin(2*np.pi*phase/100 + np.pi/4)
})

# Save and load
test_data.to_csv('test_visual.csv', index=False)
loco = LocomotionData('test_visual.csv')

# Create visualization
loco.plot_phase_patterns('TEST01', 'level_walking',
                        ['knee_flexion_angle_ipsi_rad'])
```

## Best Practices

### Memory-Efficient Plotting

For large datasets, plot subsets:

```python
# Plot only first 10 cycles
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
subset = data_3d[:10, :, :]  # First 10 cycles only

# Custom plot with subset
phase_x = np.linspace(0, 100, 150)
plt.figure(figsize=(8, 5))
for i in range(subset.shape[0]):
    plt.plot(phase_x, subset[i, :, 0], 'gray', alpha=0.5)
plt.xlabel('Gait Cycle (%)')
plt.ylabel('Joint Angle (rad)')
plt.show()
```

### Publication-Ready Figures

Configure matplotlib for publication quality:

```python
import matplotlib.pyplot as plt

# Set publication parameters
plt.rcParams.update({
    'font.size': 12,
    'axes.linewidth': 1.5,
    'lines.linewidth': 2,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

# Create plot
loco.plot_phase_patterns('SUB01', 'level_walking',
                        ['knee_flexion_angle_ipsi_rad'],
                        save_path='publication_figure.png')
```

### Common Visualization Patterns

**1. Clinical Assessment:**
```python
# Compare affected vs unaffected limb
features = ['knee_flexion_angle_ipsi_rad',
           'knee_flexion_angle_contra_rad']
loco.plot_phase_patterns('PATIENT01', 'level_walking', features)
```

**2. Pre/Post Intervention:**
```python
# Compare tasks representing different time points
loco.plot_task_comparison('PATIENT01',
                         ['pre_treatment', 'post_treatment'],
                         ['knee_flexion_angle_ipsi_rad'])
```

**3. Condition Comparison:**
```python
# Compare different walking conditions
tasks = ['level_walking', 'incline_walking', 'fast_walking']
loco.plot_task_comparison('SUB01', tasks,
                         ['hip_flexion_angle_ipsi_rad'])
```

## Troubleshooting

### Missing matplotlib

If matplotlib is not installed:
```bash
pip install matplotlib
```

### Large Dataset Performance

For memory issues with large datasets:
- Use `plot_type='mean'` instead of `'spaghetti'`
- Plot fewer features at once
- Save plots instead of displaying interactively

### Validation Integration

The plotting methods automatically integrate with validation:
- Valid cycles shown in gray
- Invalid cycles shown in red
- Only valid cycles used for mean calculations

## Known Limitations

### Data Format Requirements

The LocomotionData class requires specific column names:
- Default: `subject`, `task`, `phase`
- Custom names can be specified in constructor:
  ```python
  loco = LocomotionData('data.csv', 
                       subject_col='subject_id',
                       task_col='task_id', 
                       phase_col='phase_percent')
  ```

### Missing Visualization Features

Based on current implementation:
1. **3D animations** - No built-in animation support (use custom matplotlib animations)
2. **Interactive plots** - Static plots only (use plotly for interactivity)
3. **Heatmaps** - Not implemented (use seaborn for custom heatmaps)
4. **Statistical overlays** - Limited to mean±std (extend with custom plotting)

### Memory Considerations

For large datasets:
- Plot subsets rather than full datasets
- Use `plot_type='mean'` to avoid memory-intensive spaghetti plots
- Consider batch processing for multi-subject visualizations

## Next Steps

- Explore [Statistical Analysis](statistical_analysis.md) for quantitative metrics
- Learn about [Validation Integration](../validation/overview.md) for quality control
- See [Advanced Patterns](../advanced/patterns.md) for complex analyses

## Summary

The LocomotionData visualization tools provide:
- **Phase pattern plots** for gait cycle analysis with validation overlay
- **Task comparison** for condition effects across activities
- **Time series plots** for continuous time-indexed data
- **Automatic validation** integration showing valid/invalid cycles
- **Customization options** for publication-quality figures

Key features:
- Built-in support for standard biomechanical variables
- Automatic multi-panel layouts for multiple features
- Export to high-resolution images
- Integration with data validation pipeline

Start with the built-in methods and progress to custom visualizations as needed.