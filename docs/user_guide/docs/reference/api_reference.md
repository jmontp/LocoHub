# API Reference

Complete reference for functions and classes in the Locomotion Data Standardization library.

## Python Library

### LocomotionData Class

The main class for working with standardized datasets.

```python
from locomotion_analysis import LocomotionData

# Load dataset
data = LocomotionData('dataset_phase.parquet')
```

#### Constructor

```python
LocomotionData(filepath, format='auto')
```

**Parameters:**
- `filepath` (str): Path to the dataset file
- `format` (str): File format ('parquet', 'csv', 'auto')

**Returns:**
- LocomotionData object with loaded dataset

#### Core Methods

##### `filter()`
Filter data by conditions.

```python
filtered = data.filter(
    tasks=['level_walking', 'incline_walking'],
    subjects=['SUB01', 'SUB02'],
    phase_range=(0, 60)  # Stance phase only
)
```

**Parameters:**
- `tasks` (list): Task names to include
- `subjects` (list): Subject IDs to include  
- `phase_range` (tuple): Min and max phase percentage
- `quality_threshold` (float): Minimum quality score (0-1)

**Returns:**
- New LocomotionData object with filtered data

##### `get_cycles()`
Extract individual gait cycles.

```python
cycles = data.get_cycles(
    subject='SUB01',
    task='level_walking',
    variables=['knee_flexion_angle_ipsi_rad']
)
```

**Parameters:**
- `subject` (str): Subject identifier
- `task` (str): Task name
- `variables` (list): Variables to extract

**Returns:**
- 3D numpy array (cycles × phase_points × variables)

##### `calculate_metrics()`
Compute biomechanical metrics.

```python
metrics = data.calculate_metrics([
    'range_of_motion',
    'peak_flexion',
    'peak_timing'
])
```

**Parameters:**
- `metrics` (list): Metric names to calculate

**Returns:**
- pandas DataFrame with metrics by cycle

#### Analysis Methods

##### `plot_average_pattern()`
Create average gait pattern plots.

```python
fig = data.plot_average_pattern(
    variable='knee_flexion_angle_ipsi_rad',
    group_by='task',
    show_variability=True
)
```

**Parameters:**
- `variable` (str): Variable to plot
- `group_by` (str): Grouping variable ('task', 'subject')
- `show_variability` (bool): Include error bands
- `save_path` (str): File path to save plot

**Returns:**
- matplotlib Figure object

##### `compare_tasks()`
Statistical comparison between tasks.

```python
results = data.compare_tasks(
    variable='knee_flexion_angle_ipsi_rad',
    metric='peak_value',
    test='anova'
)
```

**Parameters:**
- `variable` (str): Variable to analyze
- `metric` (str): Metric to compare
- `test` (str): Statistical test ('anova', 'ttest', 'kruskal')

**Returns:**
- Dictionary with statistical results

### Validation Functions

#### `validate_dataset()`
Comprehensive dataset validation.

```python
from locomotion_analysis import validate_dataset

report = validate_dataset(
    filepath='dataset.parquet',
    generate_plots=True,
    output_dir='validation_output/'
)
```

**Parameters:**
- `filepath` (str): Path to dataset file
- `generate_plots` (bool): Create validation plots
- `output_dir` (str): Directory for output files

**Returns:**
- Validation report dictionary

#### `check_biomechanical_plausibility()`
Check if data values are biomechanically reasonable.

```python
from locomotion_analysis import check_biomechanical_plausibility

plausibility = check_biomechanical_plausibility(
    data=data_array,
    variable='knee_flexion_angle_ipsi_rad'
)
```

**Parameters:**
- `data` (array): Data values to check
- `variable` (str): Variable name for context

**Returns:**
- Dictionary with plausibility scores and flags

### Conversion Functions

#### `convert_to_phase_indexed()`
Convert time-indexed data to phase-indexed format.

```python
from locomotion_analysis import convert_to_phase_indexed

phase_data = convert_to_phase_indexed(
    time_data,
    heel_strikes,
    n_points=150
)
```

**Parameters:**
- `time_data` (DataFrame): Time-indexed dataset
- `heel_strikes` (array): Heel strike time indices
- `n_points` (int): Points per gait cycle (default: 150)

**Returns:**
- Phase-indexed DataFrame

#### `standardize_variable_names()`
Apply standard naming convention to variables.

```python
from locomotion_analysis import standardize_variable_names

standardized = standardize_variable_names(
    data,
    mapping_file='variable_mapping.json'
)
```

**Parameters:**
- `data` (DataFrame): Dataset with original variable names
- `mapping_file` (str): Path to variable mapping file

**Returns:**
- DataFrame with standardized variable names

## MATLAB Functions

### Data Loading

#### `load_locomotion_data()`
Load standardized locomotion dataset.

```matlab
data = load_locomotion_data('dataset_phase.parquet');
```

**Parameters:**
- `filepath` (char): Path to dataset file

**Returns:**
- Table with locomotion data

#### `filter_locomotion_data()`
Filter dataset by conditions.

```matlab
filtered_data = filter_locomotion_data(data, ...
    'tasks', {'level_walking', 'incline_walking'}, ...
    'subjects', {'SUB01', 'SUB02'}, ...
    'phase_range', [0, 60]);
```

**Parameters:**
- `data` (table): Input dataset
- `'tasks'` (cell): Task names to include
- `'subjects'` (cell): Subject IDs to include
- `'phase_range'` (array): Min and max phase percentage

**Returns:**
- Filtered table

### Analysis Functions

#### `calculate_gait_metrics()`
Compute standard gait metrics.

```matlab
metrics = calculate_gait_metrics(data, ...
    'variables', {'knee_flexion_angle_ipsi_rad'}, ...
    'metrics', {'rom', 'peak_flexion', 'peak_timing'});
```

**Parameters:**
- `data` (table): Locomotion dataset
- `'variables'` (cell): Variables to analyze
- `'metrics'` (cell): Metrics to calculate

**Returns:**
- Table with metrics by cycle

#### `plot_gait_patterns()`
Create gait pattern visualizations.

```matlab
fig = plot_gait_patterns(data, ...
    'variable', 'knee_flexion_angle_ipsi_rad', ...
    'group_by', 'task', ...
    'show_individual', false);
```

**Parameters:**
- `data` (table): Input dataset
- `'variable'` (char): Variable to plot
- `'group_by'` (char): Grouping variable
- `'show_individual'` (logical): Show individual cycles

**Returns:**
- Figure handle

### Validation Functions

#### `validate_locomotion_dataset()`
Validate dataset quality and structure.

```matlab
report = validate_locomotion_dataset('dataset.parquet', ...
    'generate_plots', true, ...
    'output_dir', 'validation_output/');
```

**Parameters:**
- `filepath` (char): Path to dataset file
- `'generate_plots'` (logical): Create validation plots
- `'output_dir'` (char): Directory for output files

**Returns:**
- Validation report structure

#### `check_phase_indexing()`
Verify phase indexing is correct.

```matlab
is_valid = check_phase_indexing(data);
```

**Parameters:**
- `data` (table): Phase-indexed dataset

**Returns:**
- Logical indicating if phase indexing is valid

## Constants and Variables

### Standard Variable Names

```python
# Joint angles (required)
REQUIRED_ANGLES = [
    'hip_flexion_angle_ipsi_rad',
    'knee_flexion_angle_ipsi_rad', 
    'ankle_flexion_angle_ipsi_rad',
    'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_contra_rad',
    'ankle_flexion_angle_contra_rad'
]

# Joint moments (optional)
OPTIONAL_MOMENTS = [
    'hip_moment_ipsi_Nm',
    'knee_moment_ipsi_Nm',
    'ankle_moment_ipsi_Nm',
    'hip_moment_contra_Nm',
    'knee_moment_contra_Nm',
    'ankle_moment_contra_Nm'
]

# Ground reaction forces (optional)
OPTIONAL_FORCES = [
    'vertical_grf_ipsi_N',
    'anterior_grf_ipsi_N',
    'lateral_grf_ipsi_N',
    'vertical_grf_contra_N',
    'anterior_grf_contra_N',
    'lateral_grf_contra_N'
]
```

### Standard Tasks

```python
STANDARD_TASKS = [
    'level_walking',
    'incline_walking',
    'decline_walking',
    'up_stairs',
    'down_stairs',
    'run',
    'sit_to_stand',
    'jump',
    'squats'
]
```

### Validation Ranges

```python
# Joint angle ranges (radians)
ANGLE_RANGES = {
    'hip_flexion_angle': (-0.52, 1.57),    # -30° to 90°
    'knee_flexion_angle': (-0.17, 2.09),   # -10° to 120°
    'ankle_flexion_angle': (-0.87, 0.52)   # -50° to 30°
}

# Phase indexing requirements
PHASE_REQUIREMENTS = {
    'points_per_cycle': 150,
    'phase_min': 0.0,
    'phase_max': 100.0,
    'phase_tolerance': 0.1
}
```

## Error Handling

### Common Exceptions

#### `DataValidationError`
Raised when dataset fails validation checks.

```python
try:
    data = LocomotionData('invalid_dataset.parquet')
except DataValidationError as e:
    print(f"Validation failed: {e}")
```

#### `IncompleteDataError`
Raised when required variables are missing.

```python
try:
    metrics = data.calculate_metrics(['invalid_metric'])
except IncompleteDataError as e:
    print(f"Missing data: {e}")
```

#### `PhaseIndexingError`
Raised when phase indexing is incorrect.

```python
try:
    phase_data = convert_to_phase_indexed(time_data, heel_strikes)
except PhaseIndexingError as e:
    print(f"Phase indexing failed: {e}")
```

## Examples

### Basic Analysis Workflow

```python
# Load and filter data
data = LocomotionData('gtech_2023_phase.parquet')
walking_data = data.filter(tasks=['level_walking'])

# Calculate metrics
metrics = walking_data.calculate_metrics([
    'range_of_motion', 'peak_flexion', 'peak_timing'
])

# Create visualization
fig = walking_data.plot_average_pattern(
    variable='knee_flexion_angle_ipsi_rad',
    group_by='subject',
    show_variability=True
)

# Statistical comparison
results = walking_data.compare_tasks(
    variable='knee_flexion_angle_ipsi_rad',
    metric='range_of_motion'
)
```

### Dataset Conversion

```python
# Convert custom format to standard
from locomotion_analysis import DatasetConverter

converter = DatasetConverter()
converter.load_custom_format('lab_data.mat')
converter.detect_gait_events()
converter.apply_phase_indexing(n_points=150)
converter.standardize_variables()
converter.validate_quality()
converter.save_parquet('standardized_dataset.parquet')
```

### Quality Assessment

```python
# Comprehensive validation
report = validate_dataset(
    'new_dataset.parquet',
    generate_plots=True,
    output_dir='quality_check/'
)

# Check specific quality criteria
plausibility = check_biomechanical_plausibility(
    data.get_variable('knee_flexion_angle_ipsi_rad'),
    variable='knee_flexion_angle_ipsi_rad'
)

print(f"Quality score: {report['overall_score']:.2f}")
print(f"Plausibility: {plausibility['score']:.2f}")
```

## Version Information

**Current Version**: 1.0.0  
**API Stability**: Stable  
**Backward Compatibility**: Maintained within major version  
**Update Frequency**: Monthly minor releases, quarterly major releases  

## Support

- **Documentation**: [User Guide](../user_guide/)
- **Tutorials**: [Getting Started](../tutorials/)
- **Issues**: [GitHub Issues](https://github.com/your-org/locomotion-data-standardization/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/locomotion-data-standardization/discussions)

---

*This API reference is automatically updated with each release. For the latest functions and features, see the development documentation.*