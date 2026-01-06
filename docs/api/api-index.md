# API Index

Searchable index of all public methods, classes, and functions in the locomotion data standardization platform.

## Quick Search

- [Classes](#classes) | [Methods](#methods) | [Functions](#functions) | [Constants](#constants)

## Classes

### LocomotionData
*Main class for locomotion data analysis*

**Location**: `locohub.locomotion_data.LocomotionData`

**Constructor**:
```python
LocomotionData(
    data_path,
    subject_col: str = 'subject',
    task_col: str = 'task',
    phase_col: str = 'phase_ipsi',
    file_type: str = 'auto',
)
```

**Properties**:
- `subjects: List[str]` - List of unique subject IDs
- `tasks: List[str]` - List of unique task names  
- `features: List[str]` - List of biomechanical feature names
- `POINTS_PER_CYCLE: int = 150` - Standard points per gait cycle
- `ANGLE_FEATURES: List[str]` - Standard joint angle variables
- `VELOCITY_FEATURES: List[str]` - Standard joint velocity variables
- `MOMENT_FEATURES: List[str]` - Standard joint moment variables

**Core Methods**:
- [`get_cycles(subject, task, features=None)`](#get_cycles) - Get 3D array of cycles
- [`get_mean_patterns(subject, task, features=None)`](#get_mean_patterns) - Get mean patterns
- [`get_std_patterns(subject, task, features=None)`](#get_std_patterns) - Get std patterns
- [`validate_cycles(subject, task, features=None)`](#validate_cycles) - Validate cycles
- [`find_outlier_cycles(subject, task, features=None, threshold=2.0)`](#find_outlier_cycles) - Find outliers
- [`get_summary_statistics(subject, task, features=None)`](#get_summary_statistics) - Summary stats
- [`calculate_rom(subject, task, features=None, by_cycle=True)`](#calculate_rom) - Range of motion
- [`get_phase_correlations(subject, task, features=None)`](#get_phase_correlations) - Phase correlations

**Validation Methods**:
- [`get_validation_report()`](#get_validation_report) - Variable name validation
- [`suggest_standard_name(variable_name)`](#suggest_standard_name) - Name suggestions

**Visualization Methods**:
- [`plot_phase_patterns(subject, task, features, plot_type='both', save_path=None)`](#plot_phase_patterns) - Phase plots
- [`plot_task_comparison(subject, tasks, features, save_path=None)`](#plot_task_comparison) - Task comparison

**Data Methods**:
- [`merge_with_task_data(task_data, join_keys=None, how='outer')`](#merge_with_task_data) - Merge data

### Validator
*Dataset validation engine*

**Location**: `internal.validation_engine.validator.Validator`

**Constructor**:
```python
Validator(config_path: Optional[pathlib.Path] = None)
```

**Core Methods**:
- [`validate(dataset_path, ignore_features=None)`](#validate) – Load a parquet file and return validation results
- [`validate_dataset(locomotion_data, ignore_features=None, task_filter=None)`](#validate_dataset) – Validate an existing `LocomotionData` object

**Related Types**:
- `TaskValidationDetails` – dataclass capturing per-task statistics, exposed in the `tasks` key of the validator output

### Interactive Validation Tuning
*Visual optimization of validation ranges*

**Tool**: `contributor_tools/interactive_validation_tuner.py`

**Features**:
- Visual comparison of passing vs failing strides
- Real-time range adjustment with drag interface
- Multi-variable failure analysis
- YAML export for range configurations

## Methods

### get_cycles
**Class**: LocomotionData  
**Signature**: `get_cycles(subject: str, task: str, features: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]`

Get 3D array of cycles for a subject-task combination.

**Parameters**:
- `subject`: Subject ID
- `task`: Task name  
- `features`: Features to extract (None = all available)

**Returns**:
- `data_3d`: 3D array of shape (n_cycles, 150, n_features)
- `feature_names`: Feature names in order

**Example**:
```python
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
print(f"Shape: {data_3d.shape}")  # (n_cycles, 150, n_features)
```

### get_mean_patterns  
**Class**: LocomotionData  
**Signature**: `get_mean_patterns(subject: str, task: str, features: Optional[List[str]] = None) -> Dict[str, np.ndarray]`

Get mean patterns for each feature.

**Returns**: Dictionary mapping feature names to mean patterns (150 points)

**Example**:
```python
patterns = loco.get_mean_patterns('SUB01', 'level_walking')
knee_pattern = patterns['knee_flexion_angle_contra_rad']
```

### get_std_patterns
**Class**: LocomotionData  
**Signature**: `get_std_patterns(subject: str, task: str, features: Optional[List[str]] = None) -> Dict[str, np.ndarray]`

Get standard deviation patterns for each feature.

**Returns**: Dictionary mapping feature names to std patterns (150 points)

### validate_cycles
**Class**: LocomotionData  
**Signature**: `validate_cycles(subject: str, task: str, features: Optional[List[str]] = None) -> np.ndarray`

Validate cycles based on biomechanical constraints.

**Returns**: Boolean array of shape (n_cycles,) indicating valid cycles

**Example**:
```python
valid_mask = loco.validate_cycles('SUB01', 'level_walking')
print(f"Valid: {np.sum(valid_mask)}/{len(valid_mask)}")
```

### find_outlier_cycles
**Class**: LocomotionData  
**Signature**: `find_outlier_cycles(subject: str, task: str, features: Optional[List[str]] = None, threshold: float = 2.0) -> np.ndarray`

Find outlier cycles based on deviation from mean pattern.

**Parameters**:
- `threshold`: Number of standard deviations for outlier threshold

**Returns**: Indices of outlier cycles

### get_summary_statistics
**Class**: LocomotionData  
**Signature**: `get_summary_statistics(subject: str, task: str, features: Optional[List[str]] = None) -> pd.DataFrame`

Get summary statistics for all features.

**Returns**: DataFrame with statistics (mean, std, min, max, etc.)

### calculate_rom
**Class**: LocomotionData  
**Signature**: `calculate_rom(subject: str, task: str, features: Optional[List[str]] = None, by_cycle: bool = True) -> Dict[str, Union[float, np.ndarray]]`

Calculate Range of Motion (ROM) for features.

**Parameters**:
- `by_cycle`: If True, ROM per cycle. If False, overall ROM.

**Returns**: ROM values for each feature

### get_phase_correlations  
**Class**: LocomotionData  
**Signature**: `get_phase_correlations(subject: str, task: str, features: Optional[List[str]] = None) -> np.ndarray`

Calculate correlation between features at each phase point.

**Returns**: Array of shape (150, n_features, n_features) with correlation matrices

### get_validation_report
**Class**: LocomotionData  
**Signature**: `get_validation_report() -> Dict`

Get variable name validation report.

**Returns**: Dictionary with 'standard_compliant', 'non_standard', 'warnings', 'errors'

### suggest_standard_name
**Class**: LocomotionData  
**Signature**: `suggest_standard_name(variable_name: str) -> str`

Suggest standard compliant name for a variable.

**Parameters**:
- `variable_name`: Non-compliant variable name

**Returns**: Suggested standard name

### plot_phase_patterns
**Class**: LocomotionData  
**Signature**: `plot_phase_patterns(subject: str, task: str, features: List[str], plot_type: str = 'both', save_path: Optional[str] = None)`

Plot phase-normalized patterns.

**Parameters**:
- `features`: Features to plot
- `plot_type`: 'mean', 'spaghetti', or 'both'
- `save_path`: Optional path to save plot

### plot_task_comparison
**Class**: LocomotionData  
**Signature**: `plot_task_comparison(subject: str, tasks: List[str], features: List[str], save_path: Optional[str] = None)`

Plot comparison of mean patterns across tasks.

### merge_with_task_data
**Class**: LocomotionData  
**Signature**: `merge_with_task_data(task_data: pd.DataFrame, join_keys: List[str] = None, how: str = 'outer') -> pd.DataFrame`

Merge locomotion data with task information.

**Parameters**:
- `task_data`: DataFrame with task information
- `join_keys`: Keys to join on (None = [subject_col, task_col])
- `how`: Type of join ('inner', 'outer', 'left', 'right')

### validate
**Class**: Validator  
**Signature**: `validate(dataset_path: str, ignore_features: Optional[List[str]] = None) -> Dict[str, Any]`

Validate a phase-indexed parquet file against the active YAML ranges.

**Parameters**:
- `dataset_path`: Path to the dataset file
- `ignore_features`: Optional list of variable names to skip during validation

**Returns**: Dictionary with schema status, per-task failures, and aggregate statistics

**Example**:
```python
from contributor_tools.common.validation import Validator

validator = Validator()
results = validator.validate('converted_datasets/umich_2021_phase_clean.parquet')
print(results['stats']['pass_rate'])
```

### validate_dataset
**Class**: Validator  
**Signature**: `validate_dataset(locomotion_data: LocomotionData, ignore_features: Optional[List[str]] = None, task_filter: Optional[List[str]] = None) -> Dict[str, Any]`

Validate an in-memory `LocomotionData` object (for advanced workflows that re-use
loaded data).

**Parameters**:
- `locomotion_data`: Preloaded dataset
- `ignore_features`: Optional list of column names to skip
- `task_filter`: Optional list restricting validation to specific tasks

**Returns**: Validation results using the same schema as `validate`


## Functions

### efficient_reshape_3d
**Location**: `locohub.locomotion_data.efficient_reshape_3d`  
**Signature**: `efficient_reshape_3d(df: pd.DataFrame, subject: str, task: str, features: List[str], subject_col: str = 'subject', task_col: str = 'task', points_per_cycle: int = 150) -> Tuple[np.ndarray, List[str]]`

Standalone function for efficient 3D reshaping.

**Parameters**:
- `df`: Phase-indexed locomotion data
- `subject`: Subject ID to extract
- `task`: Task name to extract  
- `features`: Features to extract
- `subject_col`: Subject column name
- `task_col`: Task column name
- `points_per_cycle`: Points per cycle (default: 150)

**Returns**:
- `data_3d`: 3D array or None
- `valid_features`: List of extracted features

### get_feature_list
**Location**: `locohub.feature_constants.get_feature_list`  
**Signature**: `get_feature_list(mode: str) -> list`

Get ordered feature list for specified mode.

**Parameters**:
- `mode`: 'kinematic', 'kinetic', or 'velocity'

**Returns**: List of feature names in canonical order

**Example**:
```python
kinematic_vars = get_feature_list('kinematic')
kinetic_vars = get_feature_list('kinetic')
```

### get_feature_map
**Location**: `locohub.feature_constants.get_feature_map`  
**Signature**: `get_feature_map(mode: str) -> Dict[str, int]`

Get feature index mapping for specified mode.

**Parameters**:
- `mode`: 'kinematic', 'kinetic', or 'velocity'

**Returns**: Dictionary mapping variable names to array indices

## Constants

### ANGLE_FEATURES
**Location**: `locohub.feature_constants.ANGLE_FEATURES`  
**Type**: `List[str]`

Standard joint angle variables in canonical order:
```python
[
    'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', 
    'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
]
```

### VELOCITY_FEATURES  
**Location**: `locohub.feature_constants.VELOCITY_FEATURES`  
**Type**: `List[str]`

Standard joint velocity variables (rad/s) matching the canonical phase exports.

### MOMENT_FEATURES
**Location**: `locohub.feature_constants.MOMENT_FEATURES`  
**Type**: `List[str]`

Standard joint moment variables including flexion, adduction, and rotation for all joints.

### ALL_KINETIC_FEATURES
**Location**: `locohub.feature_constants.ALL_KINETIC_FEATURES`  
**Type**: `List[str]`

Combined kinetic features including moments, ground reaction forces, and center of pressure.

## Usage Patterns

### Basic Analysis Workflow

```python
from locohub import LocomotionData

# 1. Load data
loco = LocomotionData('dataset_phase.parquet')

# 2. Get cycles  
data_3d, features = loco.get_cycles('SUB01', 'level_walking')

# 3. Calculate statistics
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
rom_data = loco.calculate_rom('SUB01', 'level_walking')

# 4. Quality assessment
valid_mask = loco.validate_cycles('SUB01', 'level_walking')
outliers = loco.find_outlier_cycles('SUB01', 'level_walking')
```

### Validation Workflow

```python
from contributor_tools.common.validation import Validator

# 1. Create validator
validator = Validator()

# 2. Run validation
results = validator.validate('converted_datasets/umich_2021_phase_clean.parquet')

# 3. Check results
print(f"Stride pass rate: {results['stats']['pass_rate']:.2%}")
```

### Feature Constants Usage

```python
from locohub.feature_constants import get_feature_list, ANGLE_FEATURES

# Get standard features
kinematic_vars = get_feature_list('kinematic')
kinetic_vars = get_feature_list('kinetic')

# Use predefined constants
data_3d, features = loco.get_cycles('SUB01', 'level_walking', ANGLE_FEATURES)
```

## Error Handling

Common error patterns and handling:

```python
try:
    loco = LocomotionData('dataset.parquet')
except FileNotFoundError:
    print("Dataset file not found")
except ValueError as e:
    print(f"Invalid dataset format: {e}")

try:
    data_3d, features = loco.get_cycles('SUB01', 'level_walking')
    if data_3d is None:
        print("No data available for this subject-task combination")
except Exception as e:
    print(f"Error getting cycles: {e}")
```

## Performance Notes

- **Memory**: LocomotionData caches 3D arrays for repeated access
- **Speed**: 3D operations are ~100x faster than pandas groupby
- **Optimization**: Use specific feature lists to reduce memory usage
- **Parallel**: Methods are thread-safe for read operations

## See Also

- **[LocomotionData](#locomotiondata)** - Detailed API overview
- **[Validator](#validator)** - Validation system overview  
- **[Tutorials](../tutorials/index.md)** - End-to-end examples
- **[Maintainers](../maintainers/index.md)** - Release and governance
