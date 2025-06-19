# Loading and Exploring Locomotion Data

**Learn the basics of loading and exploring locomotion datasets with the LocomotionData class.**

## Overview

The `LocomotionData` class is your entry point for analyzing standardized biomechanical data. This tutorial covers:

- Different ways to load locomotion datasets
- Exploring data structure (subjects, tasks, features, phases)
- Basic data filtering and subsetting
- Understanding the standardized data format

## Prerequisites

- Python environment with pandas and numpy
- Access to the locomotion analysis library
- Sample data files (provided in tests/)

## Loading Data

### Basic Loading

The simplest way to load data is with a file path:

```python
from lib.core.locomotion_analysis import LocomotionData

# Load phase-indexed data (recommended format)
loco = LocomotionData('tests/test_data/demo_clean_phase.parquet', 
                      phase_col='phase_percent')
```

**Expected output:**
```
Data validation passed: 3 subjects, 3 tasks
Loaded data with 4050 rows, 3 subjects, 3 tasks, 6 features
Variable name validation: All 6 variables are standard compliant
```

### Loading Options

LocomotionData supports different file formats and column configurations:

```python
# Auto-detect file format
loco = LocomotionData('path/to/data.parquet', file_type='auto')

# Specify custom column names
loco = LocomotionData('data.csv', 
                      subject_col='participant_id',
                      task_col='activity', 
                      phase_col='gait_phase')

# Explicitly specify file type
loco = LocomotionData('data.csv', file_type='csv')
```

### Data Format Requirements

LocomotionData expects:

- **Phase-indexed data**: 150 points per gait cycle (0-100% phase)
- **Standard variable names**: `joint_motion_measurement_side_unit`
  - Example: `knee_flexion_angle_contra_rad`
- **Required columns**: subject, task, and phase identifiers

**Warning:** Time-indexed data will load but generate warnings. Convert to phase-indexed format for optimal performance.

## Exploring Data Structure

### Basic Information

Get an overview of your dataset:

```python
# Basic dataset information
print(f"Subjects: {loco.get_subjects()}")
print(f"Tasks: {loco.get_tasks()}")
print(f"Features: {loco.features}")
print(f"Number of features: {len(loco.features)}")
```

**Expected output:**
```
Subjects: ['SUB01', 'SUB02', 'SUB03']
Tasks: ['decline_walking', 'incline_walking', 'level_walking']
Features: ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 
          'ankle_flexion_angle_contra_rad', 'hip_flexion_angle_ipsi_rad', 
          'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
Number of features: 6
```

### Understanding Variable Names

LocomotionData enforces standard naming conventions:

- **joint**: `hip`, `knee`, `ankle`
- **motion**: `flexion`, `adduction`, `rotation`
- **measurement**: `angle`, `velocity`, `moment`, `power`
- **side**: `contra` (contralateral), `ipsi` (ipsilateral)
- **unit**: `rad`, `rad_s`, `Nm`, `deg`, etc.

## Extracting Cycle Data

### Get 3D Array Data

Extract data for specific subject-task combinations:

```python
# Get all cycles for a subject-task
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
print(f"Data shape: {data_3d.shape}")
print(f"Features: {features}")

# Shape interpretation: (n_cycles, 150_phase_points, n_features)
n_cycles, n_phases, n_features = data_3d.shape
print(f"Found {n_cycles} gait cycles, {n_phases} phase points, {n_features} features")
```

**Expected output:**
```
Data shape: (3, 150, 6)
Features: ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 
          'ankle_flexion_angle_contra_rad', 'hip_flexion_angle_ipsi_rad', 
          'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
Found 3 gait cycles, 150 phase points, 6 features
```

### Subset Specific Features

Extract only the features you need:

```python
# Extract specific features
knee_features = ['knee_flexion_angle_contra_rad', 'knee_flexion_angle_ipsi_rad']
data_3d, features = loco.get_cycles('SUB01', 'level_walking', features=knee_features)
print(f"Knee data shape: {data_3d.shape}")
```

## Calculating Summary Statistics

### Mean Patterns

Get mean gait patterns across cycles:

```python
# Calculate mean patterns for all features
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')

# Each pattern has 150 phase points (0-100% gait cycle)
for feature, pattern in mean_patterns.items():
    print(f"{feature}: shape={pattern.shape}, "
          f"range=[{pattern.min():.3f}, {pattern.max():.3f}]")
```

**Expected output:**
```
hip_flexion_angle_contra_rad: shape=(150,), range=[-0.227, 0.493]
knee_flexion_angle_contra_rad: shape=(150,), range=[0.026, 1.018]
ankle_flexion_angle_contra_rad: shape=(150,), range=[-0.226, 0.215]
```

### Standard Deviation Patterns

Assess variability across cycles:

```python
# Calculate standard deviation patterns
std_patterns = loco.get_std_patterns('SUB01', 'level_walking')

for feature, pattern in std_patterns.items():
    print(f"{feature}: mean_std={pattern.mean():.3f}, "
          f"max_variability_phase={pattern.argmax()}")
```

### Summary Statistics

Get comprehensive statistics:

```python
# Get summary statistics across all data points
summary = loco.get_summary_statistics('SUB01', 'level_walking')
print(summary)

# Focus on specific features
print("\\nKnee flexion summary:")
print(summary.loc['knee_flexion_angle_contra_rad'])
```

**Expected output:**
```
                                   mean       std       min       max    median       q25       q75
hip_flexion_angle_contra_rad   0.126427  0.210648 -0.227454  0.492886  0.129632 -0.078389  0.331739
knee_flexion_angle_contra_rad  0.527063  0.285421  0.026284  1.018422  0.539717  0.286665  0.792886
```

## Range of Motion Analysis

### Overall ROM

Calculate range of motion for each feature:

```python
# Calculate overall ROM (across all cycles)
rom_overall = loco.calculate_rom('SUB01', 'level_walking', by_cycle=False)

for feature, rom_value in rom_overall.items():
    print(f"{feature}: {rom_value:.3f} radians ({rom_value*180/3.14159:.1f} degrees)")
```

**Expected output:**
```
hip_flexion_angle_contra_rad: 0.720 radians (41.3 degrees)
knee_flexion_angle_contra_rad: 0.992 radians (56.8 degrees)
ankle_flexion_angle_contra_rad: 0.441 radians (25.3 degrees)
```

### Per-Cycle ROM

Analyze variability between individual cycles:

```python
# Calculate ROM for each cycle
rom_per_cycle = loco.calculate_rom('SUB01', 'level_walking', by_cycle=True)

for feature, rom_array in rom_per_cycle.items():
    print(f"{feature}: mean_ROM={rom_array.mean():.3f}, "
          f"std_ROM={rom_array.std():.3f}, cycles={len(rom_array)}")
```

## Data Quality Assessment

### Cycle Validation

Check data quality with built-in validation:

```python
# Validate cycles based on biomechanical constraints
valid_mask = loco.validate_cycles('SUB01', 'level_walking')
print(f"Valid cycles: {valid_mask.sum()}/{len(valid_mask)}")
print(f"Invalid cycles: {(~valid_mask).sum()}")

if (~valid_mask).any():
    invalid_indices = (~valid_mask).nonzero()[0]
    print(f"Invalid cycle indices: {invalid_indices}")
```

### Outlier Detection

Identify unusual gait cycles:

```python
# Find outlier cycles (default: 2 standard deviations)
outlier_indices = loco.find_outlier_cycles('SUB01', 'level_walking', threshold=2.0)
print(f"Found {len(outlier_indices)} outlier cycles")

if len(outlier_indices) > 0:
    print(f"Outlier cycle indices: {outlier_indices}")
```

## Comparing Across Conditions

### Multiple Tasks

Compare the same subject across different tasks:

```python
# Compare mean patterns across tasks
tasks = loco.get_tasks()
feature = 'knee_flexion_angle_contra_rad'

print(f"Comparing {feature} across tasks:")
for task in tasks:
    mean_patterns = loco.get_mean_patterns('SUB01', task, [feature])
    if feature in mean_patterns:
        pattern = mean_patterns[feature]
        print(f"{task}: peak={pattern.max():.3f} rad, "
              f"min={pattern.min():.3f} rad, ROM={pattern.max()-pattern.min():.3f} rad")
```

### Multiple Subjects

Compare across subjects for the same task:

```python
# Compare subjects for the same task
subjects = loco.get_subjects()
task = 'level_walking'
feature = 'knee_flexion_angle_contra_rad'

print(f"Comparing {feature} for {task}:")
for subject in subjects:
    try:
        summary = loco.get_summary_statistics(subject, task)
        if len(summary) > 0:
            mean_val = summary.loc[feature, 'mean']
            std_val = summary.loc[feature, 'std']
            print(f"{subject}: mean={mean_val:.3f}±{std_val:.3f} rad")
    except:
        print(f"{subject}: No valid data")
```

## Working with Subsets

### Feature Filtering

Work with specific feature types:

```python
# Get only angle features
angle_features = [f for f in loco.features if 'angle' in f]
print(f"Angle features: {angle_features}")

# Get only contralateral features
contra_features = [f for f in loco.features if 'contra' in f]
print(f"Contralateral features: {contra_features}")

# Get only knee features
knee_features = [f for f in loco.features if 'knee' in f]
print(f"Knee features: {knee_features}")
```

### Data Access Patterns

Common patterns for accessing your data:

```python
# Pattern 1: Single subject, single task, all features
data_3d, features = loco.get_cycles('SUB01', 'level_walking')

# Pattern 2: Single subject, single task, specific features
hip_data, hip_features = loco.get_cycles('SUB01', 'level_walking', 
                                        ['hip_flexion_angle_contra_rad'])

# Pattern 3: Mean patterns for comparison
means = loco.get_mean_patterns('SUB01', 'level_walking')

# Pattern 4: Summary statistics for reporting
summary = loco.get_summary_statistics('SUB01', 'level_walking')
```

## Common Issues and Solutions

### Loading Problems

**Issue**: `FileNotFoundError` when loading data
```python
# Solution: Check file path and existence
from pathlib import Path
data_path = Path('your/data/path.parquet')
if data_path.exists():
    loco = LocomotionData(data_path)
else:
    print(f"File not found: {data_path}")
```

**Issue**: `ValueError` for non-standard variable names
```python
# The library enforces standard naming conventions
# Use standard names like: knee_flexion_angle_contra_rad
# Not: knee_angle, Knee_Flexion, knee_flexion_right
```

### Data Access Problems

**Issue**: Empty results from `get_cycles()`
```python
# Check if subject-task combination exists
if 'SUB01' in loco.get_subjects() and 'level_walking' in loco.get_tasks():
    data_3d, features = loco.get_cycles('SUB01', 'level_walking')
    if data_3d is not None:
        print(f"Success: {data_3d.shape}")
    else:
        print("No data found - check data format")
```

**Issue**: Time-indexed vs. Phase-indexed data
```python
# LocomotionData works best with phase-indexed data (150 points per cycle)
# Time-indexed data may load but will generate warnings
# Convert time-indexed to phase-indexed for best results
```

## Next Steps

After mastering basic data loading and exploration:

1. **Visualization**: Learn to plot phase patterns and comparisons
2. **Statistical Analysis**: Perform group comparisons and statistical tests
3. **Data Quality**: Use advanced validation and outlier detection
4. **Custom Analysis**: Develop domain-specific analysis workflows

## Key Takeaways

- LocomotionData requires **phase-indexed data** with **standard variable names**
- Data is organized as **3D arrays**: (n_cycles, 150_phases, n_features)
- Use `get_cycles()` for raw data, `get_mean_patterns()` for averages
- Built-in validation helps ensure data quality
- Feature naming follows strict conventions for consistency

The LocomotionData class provides a solid foundation for biomechanical gait analysis with standardized, validated data access patterns.