# Python Library Tutorial for Locomotion Data Analysis

[Skip to main content](#main-content)

This tutorial demonstrates how to use the **LocomotionData** library for efficient analysis of standardized locomotion data.

<a name="main-content"></a> The library provides a high-level interface for common operations like loading data, filtering, phase-based analysis, validation, and visualization.

## Prerequisites

Ensure you have the required packages:
```bash
pip install pandas numpy matplotlib pyarrow seaborn
```

## 0. Setup and Import

**Important**: Make sure you are running your Python script from the **project root directory**.

```python
import sys
import os
from pathlib import Path

# Verify we're in the project root
current_dir = Path.cwd()
print(f"Current working directory: {current_dir}")

# Add the correct library path
lib_core_path = current_dir / "lib" / "core"
if lib_core_path.exists():
    sys.path.append(str(lib_core_path))
    print("✅ Added lib/core to Python path")
else:
    print("❌ Error: lib/core not found. Make sure you're in the project root directory.")
    print("Project root should contain: README.md, lib/, docs/, etc.")

# Import the library
from locomotion_analysis import LocomotionData
import pandas as pd
import numpy as np
```

## 1. Loading Data

The `LocomotionData` class can load both parquet and CSV files:

```python
# Load phase-indexed parquet data (recommended)
loco = LocomotionData('path/to/gtech_2023_phase.parquet')

# Or load CSV data
# loco = LocomotionData('path/to/data.csv', file_type='csv')

# View basic information
print(f"Loaded {len(loco.df)} rows")
print(f"Subjects: {', '.join(loco.get_subjects()[:5])}...")
print(f"Tasks: {', '.join(loco.get_tasks())}")
print(f"Features: {len(loco.features)} biomechanical features")
```

## 2. Basic Data Exploration

```python
# Get available subjects and tasks
subjects = loco.get_subjects()
tasks = loco.get_tasks()

print(f"Available subjects: {subjects}")
print(f"Available tasks: {tasks}")

# Show available features
print("\nBiomechanical features:")
for feature in loco.features[:10]:  # Show first 10
    print(f"  - {feature}")
```

## 3. Efficient 3D Data Access

The core strength of the library is converting phase-indexed data into 3D arrays for efficient analysis:

```python
# Get 3D array for a specific subject-task
subject = subjects[0]
task = 'normal_walk'

# Extract all features
data_3d, feature_names = loco.get_cycles(subject, task)

if data_3d is not None:
    print(f"Data shape: {data_3d.shape}")  # (n_cycles, 150, n_features)
    print(f"Found {data_3d.shape[0]} gait cycles")
    print(f"Features extracted: {len(feature_names)}")
else:
    print("No data found for this subject-task combination")

# Extract specific features only
angle_features = ['hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad']
angle_data, angle_names = loco.get_cycles(subject, task, angle_features)
print(f"Angle data shape: {angle_data.shape}")
```

## 4. Data Validation

Automatically validate cycles based on biomechanical constraints:

```python
# Validate all cycles
valid_mask = loco.validate_cycles(subject, task)
print(f"Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")

# Get details on invalid cycles
invalid_indices = np.where(~valid_mask)[0]
if len(invalid_indices) > 0:
    print(f"Invalid cycle indices: {invalid_indices}")
```

## 5. Statistical Analysis

### Mean and Standard Deviation Patterns

```python
# Get mean patterns for each feature
mean_patterns = loco.get_mean_patterns(subject, task, angle_features)
std_patterns = loco.get_std_patterns(subject, task, angle_features)

# Display mean pattern for knee angle
if 'knee_flexion_angle_right_rad' in mean_patterns:
    knee_mean = mean_patterns['knee_flexion_angle_right_rad']
    print(f"Knee angle: mean = {np.mean(knee_mean):.3f} rad, "
          f"peak = {np.max(knee_mean):.3f} rad")
```

### Range of Motion (ROM) Analysis

```python
# Calculate ROM per cycle
rom_per_cycle = loco.calculate_rom(subject, task, angle_features, by_cycle=True)

# Calculate overall ROM
rom_overall = loco.calculate_rom(subject, task, angle_features, by_cycle=False)

# Display results
for feature in angle_features:
    if feature in rom_per_cycle:
        rom_cycles = rom_per_cycle[feature]
        rom_total = rom_overall[feature]
        print(f"{feature}:")
        print(f"  ROM per cycle: {np.mean(rom_cycles):.3f} ± {np.std(rom_cycles):.3f} rad")
        print(f"  Overall ROM: {rom_total:.3f} rad")
```

### Summary Statistics

```python
# Get comprehensive summary statistics
summary = loco.get_summary_statistics(subject, task, angle_features)
print("\nSummary Statistics:")
print(summary)
```

## 6. Outlier Detection

```python
# Find outlier cycles
outlier_indices = loco.find_outlier_cycles(subject, task, angle_features, threshold=2.0)
print(f"Outlier cycles (>2 std): {outlier_indices}")

# Find outlier cycles with stricter threshold
strict_outliers = loco.find_outlier_cycles(subject, task, angle_features, threshold=1.5)
print(f"Outlier cycles (>1.5 std): {strict_outliers}")
```

## 7. Data Merging

If you have additional task information, you can merge it with the locomotion data:

```python
# Create example task data
task_data = pd.DataFrame({
    'subject': [subject, subject],
    'task': ['normal_walk', 'incline_walk'],
    'speed_m_s': [1.2, 1.0],
    'incline_deg': [0, 5]
})

# Merge with locomotion data
merged_df = loco.merge_with_task_data(task_data, how='inner')
print(f"Merged data shape: {merged_df.shape}")
print(f"New columns: {set(merged_df.columns) - set(loco.df.columns)}")
```

## 8. Visualization

The library provides comprehensive plotting utilities for phase-normalized locomotion data with three main plot types.

### Phase Pattern Plotting

The library offers three plotting styles for phase-normalized data:

```python
# 1. Spaghetti plots - show all individual cycles
loco.plot_phase_patterns(subject, task, angle_features, 
                        plot_type='spaghetti', 
                        save_path='spaghetti_plot.png')

# 2. Mean ± standard deviation plots with shaded confidence bands
loco.plot_phase_patterns(subject, task, angle_features, 
                        plot_type='mean',
                        save_path='mean_patterns.png')

# 3. Combined plots - both individual cycles and mean pattern overlay
loco.plot_phase_patterns(subject, task, angle_features, 
                        plot_type='both', 
                        save_path='phase_patterns.png')
```

**Plot Features:**
- **Gray lines**: Valid cycles passing biomechanical validation
- **Red lines**: Invalid cycles failing validation criteria  
- **Blue line**: Mean pattern across valid cycles only
- **Blue shaded area**: ±1 standard deviation (in 'mean' mode)
- **Automatic layout**: Intelligent subplot arrangement (up to 3 columns)

### Task Comparison Plots

Compare mean patterns across different tasks for the same subject:

```python
# Compare multiple tasks for the same subject
available_tasks = ['normal_walk', 'incline_walk', 'decline_walk']
# Filter to only available tasks in dataset
valid_tasks = [task for task in available_tasks if task in loco.get_tasks()]

if len(valid_tasks) > 1:
    loco.plot_task_comparison(subject, valid_tasks, angle_features,
                             save_path='task_comparison.png')
```

### Time Series Plotting

For time-indexed data analysis:

```python
# Plot time series data (useful for time-indexed datasets)
if 'time_s' in loco.df.columns:
    loco.plot_time_series(subject, task, angle_features,
                         time_col='time_s', 
                         save_path='time_series.png')
```

### Custom Plotting with Raw Data

Access underlying 3D arrays for advanced custom visualizations:

```python
import matplotlib.pyplot as plt

# Get 3D data arrays
data_3d, feature_names = loco.get_cycles(subject, task, angle_features)
valid_mask = loco.validate_cycles(subject, task, angle_features)

# Create custom percentile plot
fig, axes = plt.subplots(1, len(feature_names), figsize=(15, 4))
phase_x = np.linspace(0, 100, 150)

for i, feature in enumerate(feature_names):
    feat_data = data_3d[:, :, i]
    valid_data = feat_data[valid_mask, :]
    
    # Calculate percentiles
    p25 = np.percentile(valid_data, 25, axis=0)
    p50 = np.percentile(valid_data, 50, axis=0)  # Median
    p75 = np.percentile(valid_data, 75, axis=0)
    
    # Plot with custom styling
    axes[i].fill_between(phase_x, p25, p75, alpha=0.3, 
                        color='lightblue', label='IQR (25-75%)')
    axes[i].plot(phase_x, p50, 'navy', linewidth=2, label='Median')
    
    axes[i].set_xlabel('Gait Cycle (%)')
    axes[i].set_ylabel(feature.replace('_', ' '))
    axes[i].set_title(feature, fontsize=10)
    axes[i].legend()
    axes[i].grid(True, alpha=0.3)
    axes[i].set_xlim([0, 100])

plt.tight_layout()
plt.savefig('custom_percentile_plot.png', dpi=300, bbox_inches='tight')
plt.show()
```

## 9. Advanced Analysis Example

Here's a complete workflow for analyzing gait variability:

```python
def analyze_gait_variability(loco, subject, task, features):
    """Comprehensive gait variability analysis."""
    
    print(f"\n=== Gait Variability Analysis: {subject} - {task} ===")
    
    # 1. Get data and validate
    data_3d, feature_names = loco.get_cycles(subject, task, features)
    if data_3d is None:
        print("No data found")
        return
    
    valid_mask = loco.validate_cycles(subject, task, features)
    n_valid = np.sum(valid_mask)
    n_total = len(valid_mask)
    
    print(f"Valid cycles: {n_valid}/{n_total} ({n_valid/n_total*100:.1f}%)")
    
    # 2. Calculate metrics for valid cycles only
    valid_data = data_3d[valid_mask, :, :]
    
    # 3. Analyze each feature
    results = {}
    for i, feature in enumerate(feature_names):
        feat_data = valid_data[:, :, i]
        
        # Mean pattern
        mean_pattern = np.mean(feat_data, axis=0)
        
        # Cycle-to-cycle variability (CV)
        cycle_means = np.mean(feat_data, axis=1)
        cv = np.std(cycle_means) / np.mean(cycle_means) * 100
        
        # Step-to-step variability at each phase
        phase_cv = np.std(feat_data, axis=0) / np.mean(feat_data, axis=0) * 100
        mean_phase_cv = np.mean(phase_cv)
        
        # Range of motion
        rom_values = np.max(feat_data, axis=1) - np.min(feat_data, axis=1)
        rom_cv = np.std(rom_values) / np.mean(rom_values) * 100
        
        results[feature] = {
            'cycle_cv': cv,
            'phase_cv': mean_phase_cv,
            'rom_cv': rom_cv,
            'mean_rom': np.mean(rom_values)
        }
        
        print(f"\n{feature}:")
        print(f"  Cycle-to-cycle CV: {cv:.1f}%")
        print(f"  Phase-to-phase CV: {mean_phase_cv:.1f}%")
        print(f"  ROM CV: {rom_cv:.1f}%")
        print(f"  Mean ROM: {np.mean(rom_values):.3f} rad")
    
    # 4. Find most variable feature
    cvs = [results[f]['cycle_cv'] for f in feature_names]
    most_variable = feature_names[np.argmax(cvs)]
    print(f"\nMost variable feature: {most_variable} (CV = {max(cvs):.1f}%)")
    
    return results

# Run the analysis
features_to_analyze = ['hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad']
variability_results = analyze_gait_variability(loco, subject, task, features_to_analyze)
```

## 10. Batch Processing Multiple Subjects

```python
def batch_process_subjects(loco, task, features, max_subjects=5):
    """Process multiple subjects and compare results."""
    
    subjects = loco.get_subjects()[:max_subjects]  # Limit for demo
    results = {}
    
    print(f"\n=== Batch Processing {len(subjects)} subjects for {task} ===")
    
    for subject in subjects:
        print(f"\nProcessing {subject}...")
        
        # Get data
        data_3d, _ = loco.get_cycles(subject, task, features)
        if data_3d is None:
            print(f"  No data for {subject}")
            continue
        
        # Validate and get statistics
        valid_mask = loco.validate_cycles(subject, task, features)
        mean_patterns = loco.get_mean_patterns(subject, task, features)
        rom_data = loco.calculate_rom(subject, task, features, by_cycle=False)
        
        results[subject] = {
            'n_cycles': data_3d.shape[0],
            'n_valid': np.sum(valid_mask),
            'mean_patterns': mean_patterns,
            'rom_data': rom_data
        }
        
        print(f"  Cycles: {data_3d.shape[0]} (valid: {np.sum(valid_mask)})")
    
    # Compare ROM across subjects
    print(f"\n=== ROM Comparison ===")
    for feature in features:
        print(f"\n{feature}:")
        for subject in results:
            if feature in results[subject]['rom_data']:
                rom = results[subject]['rom_data'][feature]
                print(f"  {subject}: {rom:.3f} rad")
    
    return results

# Run batch processing
batch_results = batch_process_subjects(loco, 'normal_walk', angle_features)
```

## 11. Export Results

```python
# Export summary statistics to CSV
summary_stats = loco.get_summary_statistics(subject, task)
summary_stats.to_csv('summary_statistics.csv')
print("Summary statistics saved to summary_statistics.csv")

# Export ROM data
rom_data = loco.calculate_rom(subject, task, by_cycle=True)
rom_df = pd.DataFrame(rom_data)
rom_df.to_csv('rom_per_cycle.csv', index=False)
print("ROM data saved to rom_per_cycle.csv")
```

## Conclusion

This tutorial covered the main features of the LocomotionData library:

- **Efficient data loading** from parquet or CSV files
- **3D array operations** for fast cycle-based analysis
- **Automatic validation** based on biomechanical constraints
- **Statistical analysis** including mean patterns, ROM, and variability
- **Visualization** with phase patterns and task comparisons
- **Data merging** with task information
- **Batch processing** for multiple subjects

The library provides a powerful, efficient interface for analyzing standardized locomotion data while maintaining the flexibility to access underlying data structures when needed.

For more advanced usage, see the source code in `lib/core/locomotion_analysis.py` which includes additional methods and customization options.