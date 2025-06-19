# Python API Reference

Complete API reference for the LocomotionData Python library.

## Installation

```python
from lib.core.locomotion_analysis import LocomotionData
```

## LocomotionData Class

The main class for loading and analyzing phase-indexed locomotion data.

### Constructor

```python
LocomotionData(
    data_path: Union[str, Path], 
    subject_col: str = 'subject',
    task_col: str = 'task', 
    phase_col: str = 'phase',
    file_type: str = 'auto'
)
```

**Parameters:**
- `data_path` (str or Path): Path to parquet or CSV file with phase-indexed data
- `subject_col` (str): Column name for subject IDs (default: 'subject')
- `task_col` (str): Column name for task names (default: 'task')
- `phase_col` (str): Column name for phase values (default: 'phase')
- `file_type` (str): 'parquet', 'csv', or 'auto' to detect from extension (default: 'auto')

**Raises:**
- `FileNotFoundError`: If data file does not exist
- `ValueError`: If required columns are missing, data format is invalid, or non-standard variable names are detected

**Example:**
```python
# Basic usage
loco = LocomotionData('locomotion_data.parquet')

# Custom column names
loco = LocomotionData('data.csv', phase_col='phase_percent')

# Explicit file type
loco = LocomotionData('data.txt', file_type='csv')
```

### Class Attributes

```python
POINTS_PER_CYCLE = 150  # Expected points per gait cycle

# Standard naming components
STANDARD_JOINTS = ['hip', 'knee', 'ankle']
STANDARD_MOTIONS = ['flexion', 'adduction', 'rotation']
STANDARD_MEASUREMENTS = ['angle', 'velocity', 'moment', 'power']
STANDARD_SIDES = ['contra', 'ipsi']
STANDARD_UNITS = ['rad', 'rad_s', 'Nm', 'Nm_kg', 'W', 'W_kg', 'deg', 'deg_s']

# Standard feature groups (ordered)
ANGLE_FEATURES = [
    'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad',
    'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
]

VELOCITY_FEATURES = [
    'hip_flexion_velocity_ipsi_rad_s', 'hip_flexion_velocity_contra_rad_s',
    'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s',
    'ankle_flexion_velocity_ipsi_rad_s', 'ankle_flexion_velocity_contra_rad_s'
]

MOMENT_FEATURES = [
    'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
    # ... (18 total moment features)
]
```

### Instance Attributes

After initialization, the following attributes are available:

- `df` (DataFrame): The loaded data
- `subjects` (list): Sorted list of unique subject IDs
- `tasks` (list): Sorted list of unique task names
- `features` (list): List of biomechanical features in the dataset
- `feature_mappings` (dict): Mapping of feature names (currently identity mapping)
- `validation_report` (dict): Variable name validation results

## Data Access Methods

### get_subjects()

Get list of unique subjects in the dataset.

```python
get_subjects() -> List[str]
```

**Returns:**
- List of subject IDs, sorted alphabetically

**Example:**
```python
subjects = loco.get_subjects()
# Returns: ['SUB01', 'SUB02', 'SUB03']
```

### get_tasks()

Get list of unique tasks in the dataset.

```python
get_tasks() -> List[str]
```

**Returns:**
- List of task names, sorted alphabetically

**Example:**
```python
tasks = loco.get_tasks()
# Returns: ['decline_walking', 'incline_walking', 'level_walking']
```

### get_cycles()

Get 3D array of gait cycles for a subject-task combination.

```python
get_cycles(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> Tuple[np.ndarray, List[str]]
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to extract. If None, uses all available features

**Returns:**
- `data_3d` (ndarray): 3D array of shape (n_cycles, 150, n_features), or None if no data
- `feature_names` (list): Names of features in same order as last dimension

**Example:**
```python
# Get all features
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
# data_3d.shape = (3, 150, 6)

# Get specific features
data_3d, features = loco.get_cycles('SUB01', 'level_walking', 
                                   ['knee_flexion_angle_contra_rad'])
# data_3d.shape = (3, 150, 1)
```

## Statistical Analysis Methods

### get_mean_patterns()

Calculate mean patterns across cycles for each feature.

```python
get_mean_patterns(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> Dict[str, np.ndarray]
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to analyze

**Returns:**
- Dictionary mapping feature names to mean patterns (150 points each)

**Example:**
```python
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
knee_mean = mean_patterns['knee_flexion_angle_contra_rad']
# knee_mean.shape = (150,)
```

### get_std_patterns()

Calculate standard deviation patterns across cycles.

```python
get_std_patterns(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> Dict[str, np.ndarray]
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to analyze

**Returns:**
- Dictionary mapping feature names to std patterns (150 points each)

### get_summary_statistics()

Get comprehensive summary statistics for all features.

```python
get_summary_statistics(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> pd.DataFrame
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to analyze

**Returns:**
- DataFrame with statistics (mean, std, min, max, median, q25, q75) for each feature

**Example:**
```python
summary = loco.get_summary_statistics('SUB01', 'level_walking')
# Returns DataFrame with shape (6, 7)
# Columns: ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75']
# Index: feature names
```

### get_phase_correlations()

Calculate correlation between features at each phase point.

```python
get_phase_correlations(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> np.ndarray
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to analyze

**Returns:**
- Array of shape (150, n_features, n_features) with correlation matrices at each phase

## Biomechanical Analysis Methods

### calculate_rom()

Calculate Range of Motion (ROM) for joint angles.

```python
calculate_rom(
    subject: str,
    task: str,
    features: Optional[List[str]] = None,
    by_cycle: bool = True
) -> Dict[str, Union[float, np.ndarray]]
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to calculate ROM for
- `by_cycle` (bool): If True, calculate ROM per cycle. If False, overall ROM

**Returns:**
- Dictionary mapping feature names to ROM values
  - If `by_cycle=True`: ndarray with ROM for each cycle
  - If `by_cycle=False`: float with overall ROM

**Example:**
```python
# ROM per cycle
rom_cycle = loco.calculate_rom('SUB01', 'level_walking')
# rom_cycle['knee_flexion_angle_contra_rad'].shape = (3,)

# Overall ROM
rom_overall = loco.calculate_rom('SUB01', 'level_walking', by_cycle=False)
# rom_overall['knee_flexion_angle_contra_rad'] = 0.9935
```

## Data Quality Methods

### validate_cycles()

Validate cycles based on biomechanical constraints.

```python
validate_cycles(
    subject: str,
    task: str,
    features: Optional[List[str]] = None
) -> np.ndarray
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to validate

**Returns:**
- Boolean array of shape (n_cycles,) indicating valid cycles

**Validation Checks:**
- Angle features: Range [-π, π] radians, discontinuities < 30°
- Velocity features: Range [-1000, 1000] deg/s
- Moment features: Range [-300, 300] Nm
- No NaN or infinite values

**Example:**
```python
valid_mask = loco.validate_cycles('SUB01', 'level_walking')
# valid_mask = array([True, True, True])
print(f"Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")
```

### find_outlier_cycles()

Find outlier cycles based on deviation from mean pattern.

```python
find_outlier_cycles(
    subject: str,
    task: str,
    features: Optional[List[str]] = None,
    threshold: float = 2.0
) -> np.ndarray
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str, optional): Features to analyze
- `threshold` (float): Number of standard deviations for outlier threshold

**Returns:**
- Array of outlier cycle indices (0-based)

**Example:**
```python
outliers = loco.find_outlier_cycles('SUB01', 'level_walking', threshold=3.0)
# outliers = array([])  # No outliers found
```

## Variable Name Methods

### get_validation_report()

Get the variable name validation report.

```python
get_validation_report() -> Dict
```

**Returns:**
- Dictionary with keys:
  - `standard_compliant`: List of compliant variable names
  - `non_standard`: List of non-compliant names
  - `warnings`: List of warning messages
  - `errors`: List of error messages

**Example:**
```python
report = loco.get_validation_report()
print(f"Compliant: {len(report['standard_compliant'])}")
print(f"Non-compliant: {len(report['non_standard'])}")
```

### suggest_standard_name()

Suggest a standard-compliant name for a variable.

```python
suggest_standard_name(variable_name: str) -> str
```

**Parameters:**
- `variable_name` (str): Non-standard variable name

**Returns:**
- Suggested standard-compliant name

**Example:**
```python
suggestion = loco.suggest_standard_name('KneeAngle')
# Returns: 'knee_flexion_angle_ipsi_rad'

suggestion = loco.suggest_standard_name('HipMoment_Left')
# Returns: 'hip_flexion_moment_ipsi_Nm'
```

## Data Integration Methods

### merge_with_task_data()

Merge locomotion data with task information.

```python
merge_with_task_data(
    task_data: pd.DataFrame,
    join_keys: List[str] = None,
    how: str = 'outer'
) -> pd.DataFrame
```

**Parameters:**
- `task_data` (DataFrame): DataFrame with task information
- `join_keys` (list of str): Keys to join on. If None, uses [subject_col, task_col]
- `how` (str): Type of join ('inner', 'outer', 'left', 'right')

**Returns:**
- Merged DataFrame

**Raises:**
- `ValueError`: If join keys are missing in either dataset

**Example:**
```python
# Load task metadata
task_info = pd.read_csv('task_info.csv')

# Merge with locomotion data
merged = loco.merge_with_task_data(task_info)
```

## Visualization Methods

All visualization methods require matplotlib. Install with: `pip install matplotlib`

### plot_phase_patterns()

Plot phase-normalized patterns with mean and individual cycles.

```python
plot_phase_patterns(
    subject: str,
    task: str,
    features: List[str],
    plot_type: str = 'both',
    save_path: Optional[str] = None
)
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str): Features to plot
- `plot_type` (str): 'mean', 'spaghetti', or 'both'
- `save_path` (str, optional): Path to save plot

**Raises:**
- `ImportError`: If matplotlib is not installed

**Example:**
```python
loco.plot_phase_patterns('SUB01', 'level_walking',
                        ['knee_flexion_angle_contra_rad'],
                        plot_type='both',
                        save_path='knee_patterns.png')
```

### plot_task_comparison()

Compare mean patterns across multiple tasks.

```python
plot_task_comparison(
    subject: str,
    tasks: List[str],
    features: List[str],
    save_path: Optional[str] = None
)
```

**Parameters:**
- `subject` (str): Subject ID
- `tasks` (list of str): Tasks to compare
- `features` (list of str): Features to plot
- `save_path` (str, optional): Path to save plot

**Example:**
```python
loco.plot_task_comparison('SUB01', 
                         ['level_walking', 'incline_walking'],
                         ['knee_flexion_angle_contra_rad'])
```

### plot_time_series()

Plot time series data (for time-indexed datasets).

```python
plot_time_series(
    subject: str,
    task: str,
    features: List[str],
    time_col: str = 'time_s',
    save_path: Optional[str] = None
)
```

**Parameters:**
- `subject` (str): Subject ID
- `task` (str): Task name
- `features` (list of str): Features to plot
- `time_col` (str): Column name for time data
- `save_path` (str, optional): Path to save plot

**Note:** This method is primarily for time-indexed data. Phase-indexed data may not have time columns.

## Utility Functions

### efficient_reshape_3d()

Standalone function for efficient 3D array reshaping.

```python
efficient_reshape_3d(
    df: pd.DataFrame,
    subject: str,
    task: str,
    features: List[str],
    subject_col: str = 'subject',
    task_col: str = 'task',
    points_per_cycle: int = 150
) -> Tuple[np.ndarray, List[str]]
```

**Parameters:**
- `df` (DataFrame): Phase-indexed locomotion data
- `subject` (str): Subject ID to extract
- `task` (str): Task name to extract
- `features` (list of str): Features to extract
- `subject_col` (str): Column name for subjects
- `task_col` (str): Column name for tasks
- `points_per_cycle` (int): Number of points per gait cycle

**Returns:**
- `data_3d` (ndarray or None): 3D array of shape (n_cycles, points_per_cycle, n_features)
- `valid_features` (list): List of successfully extracted features

## Error Handling

The library performs extensive validation and raises clear errors:

- **FileNotFoundError**: When data file doesn't exist
- **ValueError**: For various data issues:
  - Missing required columns
  - Empty dataset
  - Non-standard variable names
  - Invalid file formats
  - Missing join keys in merge operations
- **ImportError**: When matplotlib is required but not installed

## Performance Notes

- The library uses caching for `get_cycles()` calls to improve performance
- 3D array operations are optimized for phase-indexed data (150 points per cycle)
- Large datasets are handled efficiently with vectorized numpy operations

## Variable Naming Convention

All biomechanical variables must follow the standard convention:
```
<joint>_<motion>_<measurement>_<side>_<unit>
```

Example: `knee_flexion_angle_contra_rad`

- **joint**: hip, knee, ankle
- **motion**: flexion, adduction, rotation
- **measurement**: angle, velocity, moment, power
- **side**: ipsi (ipsilateral), contra (contralateral)
- **unit**: rad, rad_s, Nm, Nm_kg, W, W_kg, deg, deg_s

Non-compliant variable names will raise a ValueError during initialization.