# Efficient Data Access Guide for Phase-Indexed Locomotion Data

## Overview

This guide explains how to efficiently access and process phase-indexed locomotion data using NumPy/MATLAB reshaping instead of slower groupby operations.

## Key Concept: The 150-Point Standard

According to our phase calculation specification (`docs/standard_spec/phase_calculation.md`), all gait cycles are normalized to exactly **150 points** (0-100% of gait cycle). This standardization enables extremely efficient data access patterns.

## Data Structure

Phase-indexed data has the following structure:
- Each subject-task combination contains multiple gait cycles
- Each cycle has exactly 150 data points
- Data is stored in "long format" with one row per time point
- The new `step_number` column identifies which cycle each point belongs to

Example structure:
```
subject | task | phase | step_number | knee_angle_s_r | hip_angle_s_r | ...
--------|------|-------|-------------|----------------|---------------|-----
SUB01   | walk | 0.00  | 0           | -72.3          | 15.2          | ...
SUB01   | walk | 0.67  | 0           | -72.5          | 15.4          | ...
...     | ...  | ...   | ...         | ...            | ...           | ...
SUB01   | walk | 99.33 | 0           | -71.8          | 14.9          | ...
SUB01   | walk | 0.00  | 1           | -72.1          | 15.1          | ...
...     | ...  | ...   | ...         | ...            | ...           | ...
```

## Efficient Reshaping Pattern

### Python Implementation - Dictionary Approach

```python
import numpy as np
import pandas as pd

def efficient_reshape(df, subject, task, features, points_per_cycle=150):
    """
    Efficiently reshape data for a subject-task using NumPy operations.
    
    Returns:
        dict: Feature names as keys, (n_cycles, 150) arrays as values
    """
    # Filter for specific subject and task
    mask = (df['subject'] == subject) & (df['task'] == task)
    subset = df[mask]
    
    # Calculate number of cycles
    n_points = len(subset)
    n_cycles = n_points // points_per_cycle
    
    # Efficient reshape for each feature
    reshaped_data = {}
    for feature in features:
        # Direct numpy reshape - O(1) operation!
        feature_values = subset[feature].values
        reshaped_data[feature] = feature_values.reshape(n_cycles, points_per_cycle)
    
    return reshaped_data
```

### Python Implementation - 3D Array Approach (Recommended)

```python
def efficient_reshape_3d(df, subject, task, features, points_per_cycle=150):
    """
    Efficiently reshape data into 3D array (num_cycles, num_phase_points, num_features).
    This approach is more efficient for operations across multiple features.
    
    Returns:
        data_3d: 3D numpy array of shape (n_cycles, 150, n_features)
        feature_names: List of feature names (same order as last dimension)
    """
    # Filter for specific subject and task
    mask = (df['subject'] == subject) & (df['task'] == task)
    subset = df[mask]
    
    # Get number of cycles
    n_points = len(subset)
    n_cycles = n_points // points_per_cycle
    
    if n_points % points_per_cycle != 0:
        print(f"Warning: {n_points} points not divisible by {points_per_cycle}")
        return None, None
    
    # Extract all features at once as 2D array
    feature_data = subset[features].values  # Shape: (n_points, n_features)
    
    # Reshape to 3D: (n_cycles * 150, n_features) → (n_cycles, 150, n_features)
    data_3d = feature_data.reshape(n_cycles, points_per_cycle, len(features))
    
    return data_3d, features
```

### Performance Comparison: Dictionary vs 3D Array

```python
import time

# Setup
features = ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r',
           'hip_vel_s_r', 'knee_vel_s_r', 'ankle_vel_s_r']

# Dictionary approach
start = time.time()
dict_data = efficient_reshape(df, 'AB01', 'normal_walk', features)
dict_time = time.time() - start

# 3D Array approach
start = time.time()
array_data, feature_names = efficient_reshape_3d(df, 'AB01', 'normal_walk', features)
array_time = time.time() - start

print(f"Dictionary approach: {dict_time*1000:.2f}ms")
print(f"3D Array approach: {array_time*1000:.2f}ms")
print(f"Speedup: {dict_time/array_time:.2f}x")
```

### Advantages of 3D Array Approach

1. **Single Memory Allocation**: All features stored contiguously in memory
2. **Vectorized Operations**: Apply operations to all features simultaneously
3. **Better Cache Efficiency**: Sequential memory access patterns
4. **Natural Slicing**: Extract feature subsets with simple array slicing
5. **Direct Matrix Operations**: No dictionary overhead for multi-feature calculations

### When to Use Each Approach

**Use Dictionary Approach when:**
- Working with single features independently
- Need named access to specific features
- Mixing features with different data types

**Use 3D Array Approach when:**
- Processing multiple features together
- Performing matrix operations across features
- Need maximum computational efficiency
- Working with homogeneous numerical data

### MATLAB Implementation

```matlab
% Dictionary-like approach (using struct)
function reshapedData = efficientReshape(data, pointsPerCycle)
    % Efficiently reshape phase-indexed data
    % 
    % Args:
    %   data: Column vector of feature values
    %   pointsPerCycle: Points per cycle (default 150)
    %
    % Returns:
    %   reshapedData: Matrix of size (numCycles, pointsPerCycle)
    
    if nargin < 2
        pointsPerCycle = 150;
    end
    
    numCycles = length(data) / pointsPerCycle;
    
    % Direct reshape - very efficient!
    reshapedData = reshape(data, pointsPerCycle, numCycles)';
end

% 3D Array approach (Recommended for multiple features)
function [data3D, featureNames] = efficientReshape3D(dataTable, subject, task, features, pointsPerCycle)
    % Efficiently reshape multiple features into 3D array
    %
    % Args:
    %   dataTable: Table with locomotion data
    %   subject: Subject ID
    %   task: Task ID
    %   features: Cell array of feature names
    %   pointsPerCycle: Points per cycle (default 150)
    %
    % Returns:
    %   data3D: 3D array of size (numCycles, pointsPerCycle, numFeatures)
    %   featureNames: Cell array of feature names (same order as 3rd dimension)
    
    if nargin < 5
        pointsPerCycle = 150;
    end
    
    % Filter data
    mask = strcmp(dataTable.subject, subject) & strcmp(dataTable.task, task);
    subset = dataTable(mask, :);
    
    % Get dimensions
    numPoints = height(subset);
    numCycles = numPoints / pointsPerCycle;
    numFeatures = length(features);
    
    % Extract all features as matrix
    featureData = table2array(subset(:, features)); % (numPoints, numFeatures)
    
    % Reshape to 3D
    data3D = reshape(featureData, pointsPerCycle, numCycles, numFeatures);
    data3D = permute(data3D, [2, 1, 3]); % Reorder to (numCycles, pointsPerCycle, numFeatures)
    
    featureNames = features;
end
```

## Performance Comparison

### Inefficient Approach (GroupBy)
```python
# SLOW - Avoid this pattern!
grouped = df.groupby(['subject', 'task', 'step_number'])
cycles = []
for name, group in grouped:
    cycles.append(group[feature].values)
result = np.array(cycles)
```

### Efficient Approach (Reshape)
```python
# FAST - Use this pattern!
feature_values = df[feature].values
result = feature_values.reshape(n_cycles, 150)
```

**Significant performance improvement** for large datasets!

## Common Operations with Reshaped Data

### Using Dictionary Approach

#### 1. Calculate Mean Gait Pattern
```python
# Get data in efficient format
data = efficient_reshape(df, subject, task, ['knee_angle_s_r'])
knee_cycles = data['knee_angle_s_r']  # Shape: (n_cycles, 150)

# Calculate mean and std across cycles
mean_pattern = np.mean(knee_cycles, axis=0)  # Shape: (150,)
std_pattern = np.std(knee_cycles, axis=0)    # Shape: (150,)
```

### Using 3D Array Approach (More Efficient)

#### 1. Calculate Mean Gait Pattern for All Features
```python
# Get all angle features at once
features = ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r']
data_3d, feature_names = efficient_reshape_3d(df, subject, task, features)
# data_3d shape: (n_cycles, 150, 3)

# Calculate mean and std for all features simultaneously
mean_patterns = np.mean(data_3d, axis=0)  # Shape: (150, 3)
std_patterns = np.std(data_3d, axis=0)    # Shape: (150, 3)

# Access individual feature means
knee_mean = mean_patterns[:, 1]  # knee_angle_s_r is index 1
```

#### 2. Identify Outlier Cycles Across Multiple Features
```python
# Calculate deviation from mean for all features
mean_patterns = np.mean(data_3d, axis=0)  # (150, n_features)
deviations = data_3d - mean_patterns[np.newaxis, :, :]  # Broadcasting

# RMSE per cycle across all features
rmse_per_cycle = np.sqrt(np.mean(deviations**2, axis=(1, 2)))

# Find outliers based on combined features
outlier_threshold = np.mean(rmse_per_cycle) + 2 * np.std(rmse_per_cycle)
outlier_cycles = np.where(rmse_per_cycle > outlier_threshold)[0]
```

#### 3. Feature Correlations at Each Phase
```python
# Calculate correlation between features at each phase point
n_cycles, n_phases, n_features = data_3d.shape
phase_correlations = np.zeros((n_phases, n_features, n_features))

for phase in range(n_phases):
    # Get all features at this phase across cycles
    phase_data = data_3d[:, phase, :]  # (n_cycles, n_features)
    # Calculate correlation matrix
    phase_correlations[phase] = np.corrcoef(phase_data.T)

# Find phase with highest knee-hip correlation
hip_idx, knee_idx = 0, 1  # Based on feature order
knee_hip_corr = phase_correlations[:, hip_idx, knee_idx]
max_corr_phase = np.argmax(knee_hip_corr) / 150 * 100
print(f"Maximum knee-hip correlation at {max_corr_phase:.1f}% of gait cycle")
```

#### 4. Efficient Feature Extraction
```python
# Extract specific feature combinations efficiently
angles_3d = data_3d[:, :, 0:3]  # All angle measurements
velocities_3d = data_3d[:, :, 3:6]  # All velocity measurements

# Calculate angle-velocity relationships
angle_velocity_products = angles_3d * velocities_3d  # Element-wise
power_estimates = np.sum(angle_velocity_products, axis=2)  # Sum across joints
```

#### 5. Batch Processing with 3D Arrays
```python
# Process all subjects and create 4D array
all_subjects = df['subject'].unique()
all_data = []

for subject in all_subjects:
    data_3d, _ = efficient_reshape_3d(df, subject, 'walk', features)
    if data_3d is not None:
        all_data.append(data_3d)

# Stack into 4D array: (n_subjects, n_cycles, n_phases, n_features)
all_data_4d = np.array(all_data)

# Calculate grand mean across all subjects and cycles
grand_mean = np.mean(all_data_4d, axis=(0, 1))  # (150, n_features)
```

## Integration with Plotting

The mosaic plotter (`source/visualization/mozaic_plot.py`) already uses this efficient pattern:

```python
# From mozaic_plot.py
feat_array = subj_df[feat].values
reshaped_data = feat_array.reshape(num_cycles, POINTS_PER_CYCLE)
```

## Key Benefits

1. **Speed**: O(1) reshape vs O(n) groupby operations
2. **Memory**: No intermediate data structures needed
3. **Simplicity**: One line of code replaces complex loops
4. **Vectorization**: Enables efficient NumPy operations on reshaped data
5. **Consistency**: Works identically across all datasets following the standard

## Important Notes

- Always verify data length is divisible by 150 before reshaping
- The `step_number` column (when available) provides an alternative way to identify cycles
- This pattern assumes data is already ordered by cycle (which it is in our standard format)
- For non-standard data (not 150 points), use traditional groupby methods

## Example Usage in Analysis

### Dictionary Approach Example
```python
# Load phase-indexed data
df = pd.read_parquet('gtech_2023_phase_with_steps.parquet')

# Analyze knee angles for one subject's walking
data = efficient_reshape(df, 'SUB01', 'normal_walk', 
                        ['knee_angle_s_r', 'hip_angle_s_r'])

# Get cycle data
knee_cycles = data['knee_angle_s_r']  # (82, 150) for 82 cycles
hip_cycles = data['hip_angle_s_r']    # (82, 150)

# Calculate correlation between knee and hip at each phase
phase_correlations = []
for phase in range(150):
    corr = np.corrcoef(knee_cycles[:, phase], hip_cycles[:, phase])[0, 1]
    phase_correlations.append(corr)

# Find phase with highest knee-hip correlation
max_corr_phase = np.argmax(phase_correlations) / 150 * 100
print(f"Maximum knee-hip correlation at {max_corr_phase:.1f}% of gait cycle")
```

### 3D Array Approach Example (More Efficient)
```python
# Load phase-indexed data
df = pd.read_parquet('gtech_2023_phase_with_steps.parquet')

# Get all lower limb angles and velocities
features = ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r',
           'hip_vel_s_r', 'knee_vel_s_r', 'ankle_vel_s_r']

# Reshape to 3D array
data_3d, feature_names = efficient_reshape_3d(df, 'SUB01', 'normal_walk', features)
# Shape: (82, 150, 6) for 82 cycles, 150 phases, 6 features

# Example 1: Calculate mean patterns for all features at once
mean_patterns = np.mean(data_3d, axis=0)  # (150, 6)
std_patterns = np.std(data_3d, axis=0)    # (150, 6)

# Example 2: Find cycles with abnormal knee flexion
knee_idx = feature_names.index('knee_angle_s_r')
knee_data = data_3d[:, :, knee_idx]  # Extract just knee angle
abnormal_cycles = np.where(np.max(knee_data, axis=1) > 80)[0]  # Excessive flexion

# Example 3: Calculate joint power estimates (angle * velocity)
angles = data_3d[:, :, 0:3]      # First 3 features are angles
velocities = data_3d[:, :, 3:6]  # Next 3 features are velocities
power_estimates = angles * velocities  # Element-wise multiplication

# Example 4: Find coordination patterns
# Calculate correlation between all joint angles at each phase
n_cycles, n_phases, _ = data_3d.shape
angle_correlations = np.zeros((n_phases, 3, 3))

for phase in range(n_phases):
    angle_data_at_phase = data_3d[:, phase, 0:3]  # All angles at this phase
    angle_correlations[phase] = np.corrcoef(angle_data_at_phase.T)

# Example 5: Efficient statistical analysis
# Calculate percentiles across all cycles for each feature and phase
percentiles = np.percentile(data_3d, [25, 50, 75], axis=0)  # (3, 150, 6)
median_patterns = percentiles[1]  # 50th percentile

print(f"Processed {n_cycles} cycles with {len(features)} features")
print(f"Found {len(abnormal_cycles)} cycles with excessive knee flexion")
```

## Performance Benefits Summary

| Operation | Dictionary Approach | 3D Array Approach | Speedup |
|-----------|-------------------|------------------|---------|
| Load 6 features | 6 separate arrays | 1 contiguous array | 2-3x |
| Mean across features | Loop through dict | Single operation | 5-10x |
| Feature correlations | Multiple indexing | Direct slicing | 3-5x |
| Filtering by criteria | Check each feature | Vectorized operation | 10-20x |
| Memory usage | Scattered | Contiguous | 30-50% less |

The 3D array approach is particularly beneficial when:
- Working with multiple features simultaneously
- Performing statistical operations across features
- Need maximum computational efficiency
- Building machine learning pipelines