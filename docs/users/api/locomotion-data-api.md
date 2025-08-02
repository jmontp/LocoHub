# LocomotionData API Reference

Comprehensive API documentation for the `LocomotionData` class - the core data analysis interface.

## Class Overview

The `LocomotionData` class provides efficient 3D array operations for phase-indexed biomechanical data with strict variable naming validation and comprehensive data quality assessment.

```python
from lib.core.locomotion_analysis import LocomotionData

# Initialize with phase-indexed data
loco = LocomotionData('dataset_phase.parquet')
```

## Constructor

### `LocomotionData(data_path, subject_col='subject', task_col='task', phase_col='phase', file_type='auto')`

Initialize with phase-indexed locomotion data.

**Parameters:**
- `data_path` (str | Path): Path to parquet or CSV file with phase-indexed data
- `subject_col` (str): Column name for subject IDs (default: 'subject')
- `task_col` (str): Column name for task names (default: 'task')  
- `phase_col` (str): Column name for phase values (default: 'phase')
- `file_type` (str): 'parquet', 'csv', or 'auto' to detect from extension

**Raises:**
- `FileNotFoundError`: If data file does not exist
- `ValueError`: If required columns are missing or data format is invalid

**Example:**
```python
# Standard usage
loco = LocomotionData('gait_data_phase.parquet')

# Custom column names
loco = LocomotionData('data.csv', subject_col='participant_id', 
                     task_col='activity', phase_col='phase_percent')
```

## Class Properties

### `subjects: List[str]`
List of unique subject IDs in the dataset.

### `tasks: List[str]`  
List of unique task names in the dataset.

### `features: List[str]`
List of biomechanical feature names in the dataset.

### `POINTS_PER_CYCLE: int = 150`
Standard number of points per gait cycle for phase-indexed data.

### Standard Feature Arrays
- `ANGLE_FEATURES`: Standard joint angle variables
- `VELOCITY_FEATURES`: Standard joint velocity variables  
- `MOMENT_FEATURES`: Standard joint moment variables

## Core Data Access Methods

### `get_cycles(subject, task, features=None)`

Get 3D array of cycles for a subject-task combination.

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (List[str], optional): Features to extract. If None, uses all available features.

**Returns:**
- `data_3d` (np.ndarray): 3D array of shape (n_cycles, 150, n_features)
- `feature_names` (List[str]): Names of features in same order as last dimension

**Example:**
```python
# Get all available features
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
print(f"Shape: {data_3d.shape}")  # (n_cycles, 150, n_features)

# Get specific features
kinematic_data, features = loco.get_cycles('SUB01', 'level_walking', 
                                         loco.ANGLE_FEATURES)
```

### `get_mean_patterns(subject, task, features=None)`

Get mean patterns for each feature.

**Returns:**
- `dict`: Dictionary mapping feature names to mean patterns (150 points)

**Example:**
```python
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
knee_pattern = mean_patterns['knee_flexion_angle_contra_rad']
print(f"Mean knee flexion: {knee_pattern[:5]}...")  # First 5 points
```

### `get_std_patterns(subject, task, features=None)`

Get standard deviation patterns for each feature.

**Returns:**
- `dict`: Dictionary mapping feature names to std patterns (150 points)

## Data Quality Methods

### `validate_cycles(subject, task, features=None)`

Validate cycles based on biomechanical constraints.

**Returns:**
- `valid_mask` (np.ndarray): Boolean array of shape (n_cycles,) indicating valid cycles

**Example:**
```python
valid_mask = loco.validate_cycles('SUB01', 'level_walking')
print(f"Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")

# Use mask to filter data
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
valid_data = data_3d[valid_mask, :, :]
```

### `find_outlier_cycles(subject, task, features=None, threshold=2.0)`

Find outlier cycles based on deviation from mean pattern.

**Parameters:**
- `threshold` (float): Number of standard deviations for outlier threshold

**Returns:**
- `outlier_indices` (np.ndarray): Indices of outlier cycles

**Example:**
```python
outliers = loco.find_outlier_cycles('SUB01', 'level_walking', threshold=2.5)
print(f"Found {len(outliers)} outlier cycles: {outliers}")
```

## Statistical Analysis Methods

### `get_summary_statistics(subject, task, features=None)`

Get summary statistics for all features.

**Returns:**
- `summary` (pd.DataFrame): Summary statistics including mean, std, min, max, etc.

**Example:**
```python
stats = loco.get_summary_statistics('SUB01', 'level_walking')
print(stats.loc['knee_flexion_angle_contra_rad'])
```

### `calculate_rom(subject, task, features=None, by_cycle=True)`

Calculate Range of Motion (ROM) for features.

**Parameters:**
- `by_cycle` (bool): If True, calculate ROM per cycle. If False, overall ROM.

**Returns:**
- `rom_data` (dict): ROM values for each feature

**Example:**
```python
# ROM per cycle
rom_per_cycle = loco.calculate_rom('SUB01', 'level_walking', by_cycle=True)
knee_rom = rom_per_cycle['knee_flexion_angle_contra_rad']
print(f"Knee ROM per cycle: {knee_rom[:5]}...")

# Overall ROM
overall_rom = loco.calculate_rom('SUB01', 'level_walking', by_cycle=False)
print(f"Overall knee ROM: {overall_rom['knee_flexion_angle_contra_rad']:.3f} rad")
```

### `get_phase_correlations(subject, task, features=None)`

Calculate correlation between features at each phase point.

**Returns:**
- `correlations` (np.ndarray): Array of shape (150, n_features, n_features) with correlation matrices

**Example:**
```python
correlations = loco.get_phase_correlations('SUB01', 'level_walking')
# Correlation between knee and ankle at heel strike (phase 0)
knee_ankle_corr = correlations[0, 2, 4]  # Assuming knee=2, ankle=4
```

## Data Manipulation Methods

### `merge_with_task_data(task_data, join_keys=None, how='outer')`

Merge locomotion data with task information.

**Parameters:**
- `task_data` (pd.DataFrame): DataFrame with task information
- `join_keys` (List[str]): Keys to join on. If None, uses [subject_col, task_col]
- `how` (str): Type of join ('inner', 'outer', 'left', 'right')

**Returns:**
- `merged_df` (pd.DataFrame): Merged data

## Validation Methods

### `get_validation_report()`

Get variable name validation report.

**Returns:**
- `dict`: Report with 'standard_compliant', 'non_standard', 'warnings', 'errors' keys

**Example:**
```python
report = loco.get_validation_report()
print(f"Standard compliant: {len(report['standard_compliant'])}")
print(f"Non-standard: {len(report['non_standard'])}")
for error in report['errors']:
    print(f"Error: {error}")
```

### `suggest_standard_name(variable_name)`

Suggest standard compliant name for a variable.

**Parameters:**
- `variable_name` (str): Non-compliant variable name

**Returns:**
- `str`: Suggested standard name

**Example:**
```python
suggestion = loco.suggest_standard_name('R_knee_angle')
print(f"Suggested name: {suggestion}")  # 'knee_flexion_angle_ipsi_rad'
```

## Visualization Methods

### `plot_phase_patterns(subject, task, features, plot_type='both', save_path=None)`

Plot phase-normalized patterns.

**Parameters:**
- `features` (List[str]): Features to plot
- `plot_type` (str): 'mean', 'spaghetti', or 'both'
- `save_path` (str, optional): Path to save plot

**Example:**
```python
# Plot mean patterns with individual cycles
loco.plot_phase_patterns('SUB01', 'level_walking', 
                        ['knee_flexion_angle_contra_rad'],
                        plot_type='both',
                        save_path='knee_patterns.png')
```

### `plot_task_comparison(subject, tasks, features, save_path=None)`

Plot comparison of mean patterns across tasks.

**Example:**
```python
loco.plot_task_comparison('SUB01', 
                         ['level_walking', 'incline_walking'],
                         ['knee_flexion_angle_contra_rad'])
```

## Advanced Usage Patterns

### Batch Processing Multiple Subjects

```python
# Process all subjects for a specific task
results = {}
for subject in loco.subjects:
    data_3d, features = loco.get_cycles(subject, 'level_walking')
    if data_3d is not None:
        valid_mask = loco.validate_cycles(subject, 'level_walking')
        results[subject] = {
            'total_cycles': data_3d.shape[0],
            'valid_cycles': np.sum(valid_mask),
            'mean_patterns': loco.get_mean_patterns(subject, 'level_walking')
        }
```

### Quality Assessment Pipeline

```python
def assess_data_quality(loco, subject, task):
    """Comprehensive data quality assessment."""
    # Get data
    data_3d, features = loco.get_cycles(subject, task)
    if data_3d is None:
        return None
    
    # Validation checks
    valid_mask = loco.validate_cycles(subject, task)
    outliers = loco.find_outlier_cycles(subject, task)
    stats = loco.get_summary_statistics(subject, task)
    
    return {
        'total_cycles': data_3d.shape[0],
        'valid_cycles': np.sum(valid_mask),
        'outlier_cycles': len(outliers),
        'quality_score': np.sum(valid_mask) / data_3d.shape[0],
        'summary_stats': stats
    }

# Run for all subjects and tasks
quality_results = {}
for subject in loco.subjects:
    quality_results[subject] = {}
    for task in loco.tasks:
        quality_results[subject][task] = assess_data_quality(loco, subject, task)
```

### Custom Feature Analysis

```python
# Define custom feature set
custom_features = [
    'hip_flexion_angle_ipsi_rad',
    'knee_flexion_angle_ipsi_rad', 
    'ankle_flexion_angle_ipsi_rad'
]

# Analyze just ipsilateral leg
for subject in loco.subjects[:5]:  # First 5 subjects
    data_3d, features = loco.get_cycles(subject, 'level_walking', custom_features)
    if data_3d is not None:
        # Calculate joint coordination
        correlations = loco.get_phase_correlations(subject, 'level_walking', custom_features)
        
        # Hip-knee correlation at mid-stance (phase 75)
        hip_knee_corr = correlations[75, 0, 1]
        print(f"{subject}: Hip-knee correlation at mid-stance: {hip_knee_corr:.3f}")
```

## Error Handling

The API provides explicit error handling with clear error messages:

```python
try:
    loco = LocomotionData('nonexistent.parquet')
except FileNotFoundError as e:
    print(f"File not found: {e}")

try:
    data_3d, features = loco.get_cycles('INVALID_SUBJECT', 'level_walking')
except ValueError as e:
    print(f"Invalid subject: {e}")

# Check for warnings about data quality
import warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    loco = LocomotionData('low_quality_data.parquet')
    if w:
        for warning in w:
            print(f"Warning: {warning.message}")
```

## Performance Considerations

- **3D Array Operations**: 100x faster than pandas groupby operations
- **Caching**: Results are cached for repeated calls with same parameters
- **Memory Efficient**: Only loads requested features into memory
- **Batch Processing**: Process multiple subjects/tasks efficiently

```python
# Efficient batch processing
import time

start_time = time.time()
all_data = {}
for subject in loco.subjects:
    for task in loco.tasks:
        # Efficient 3D array extraction
        data_3d, features = loco.get_cycles(subject, task)
        all_data[(subject, task)] = data_3d

elapsed = time.time() - start_time
print(f"Processed {len(all_data)} subject-task combinations in {elapsed:.2f}s")
```

## Next Steps

- **Integration Patterns**: See [Integration Guides](../integration/README.md)
- **Validation API**: Check [Validation API](validation-api.md)
- **Examples Library**: Review `lib/core/examples.py` for complete workflows