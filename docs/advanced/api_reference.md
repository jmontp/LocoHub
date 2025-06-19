# API Reference Guide

**Complete technical reference for the Locomotion Data Standardization Platform**

## Overview

This comprehensive API reference covers all public methods, classes, and interfaces in the locomotion data platform. Designed for developers and researchers who need detailed technical information for integration and extension.

## Core Libraries

### LocomotionData Class

The main interface for loading and analyzing phase-indexed biomechanical data.

```python
from lib.core.locomotion_analysis import LocomotionData

# Initialize with phase-indexed data
loco = LocomotionData(data_path, subject_col='subject', task_col='task', phase_col='phase')
```

#### Constructor

```python
LocomotionData(data_path: Union[str, Path], 
               subject_col: str = 'subject',
               task_col: str = 'task', 
               phase_col: str = 'phase',
               file_type: str = 'auto')
```

**Parameters:**
- `data_path`: Path to parquet or CSV file with phase-indexed data
- `subject_col`: Column name for subject IDs (default: 'subject')
- `task_col`: Column name for task names (default: 'task')
- `phase_col`: Column name for phase values (default: 'phase')
- `file_type`: File format - 'parquet', 'csv', or 'auto' (default: 'auto')

**Raises:**
- `FileNotFoundError`: If data file does not exist
- `ValueError`: If required columns are missing or data format is invalid

**Example:**
```python
# Load standard format
loco = LocomotionData('dataset_phase.parquet')

# Load with custom column names
loco = LocomotionData('data.csv', 
                      subject_col='participant_id',
                      task_col='movement_type',
                      phase_col='gait_phase_percent')
```

#### Data Access Methods

##### get_cycles()

Extract 3D array of cycles for analysis.

```python
get_cycles(subject: str, task: str, 
           features: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]
```

**Parameters:**
- `subject`: Subject ID to extract
- `task`: Task name to extract
- `features`: List of features to extract (uses all if None)

**Returns:**
- `data_3d`: 3D array with shape (n_cycles, 150, n_features)
- `feature_names`: Names of features in same order as last dimension

**Example:**
```python
# Get all available features
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
print(f"Shape: {data_3d.shape}")  # (n_cycles, 150, n_features)

# Get specific features
angle_features = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
data_3d, features = loco.get_cycles('SUB01', 'normal_walk', angle_features)
```

##### get_mean_patterns()

Calculate mean patterns across gait cycles.

```python
get_mean_patterns(subject: str, task: str, 
                  features: Optional[List[str]] = None) -> Dict[str, np.ndarray]
```

**Returns:**
- Dictionary mapping feature names to mean patterns (150 points each)

**Example:**
```python
mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
knee_angle_mean = mean_patterns['knee_flexion_angle_ipsi_rad']
print(f"Mean knee angle range: {knee_angle_mean.min():.2f} to {knee_angle_mean.max():.2f} rad")
```

##### get_std_patterns()

Calculate standard deviation patterns across gait cycles.

```python
get_std_patterns(subject: str, task: str,
                 features: Optional[List[str]] = None) -> Dict[str, np.ndarray]
```

**Example:**
```python
std_patterns = loco.get_std_patterns('SUB01', 'normal_walk')
knee_angle_std = std_patterns['knee_flexion_angle_ipsi_rad']
print(f"Knee angle variability: {knee_angle_std.mean():.3f} rad average std")
```

#### Analysis Methods

##### validate_cycles()

Validate cycles against biomechanical constraints.

```python
validate_cycles(subject: str, task: str,
                features: Optional[List[str]] = None) -> np.ndarray
```

**Returns:**
- Boolean array of shape (n_cycles,) indicating valid cycles

**Validation Criteria:**
- Joint angles within physiological range (-π to π radians)
- No large discontinuities (>30° jumps)
- Velocities within reasonable bounds (<1000°/s)
- Moments within reasonable bounds (<300 Nm)
- No NaN or infinite values

**Example:**
```python
valid_mask = loco.validate_cycles('SUB01', 'normal_walk')
print(f"Valid cycles: {valid_mask.sum()}/{len(valid_mask)}")

# Use for filtering
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
valid_data = data_3d[valid_mask, :, :]  # Only valid cycles
```

##### find_outlier_cycles()

Detect outlier cycles using statistical methods.

```python
find_outlier_cycles(subject: str, task: str,
                    features: Optional[List[str]] = None,
                    threshold: float = 2.0) -> np.ndarray
```

**Parameters:**
- `threshold`: Number of standard deviations for outlier detection

**Returns:**
- Array of outlier cycle indices

**Example:**
```python
outliers = loco.find_outlier_cycles('SUB01', 'normal_walk', threshold=2.5)
print(f"Found {len(outliers)} outlier cycles: {outliers}")

# Remove outliers from analysis
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
clean_data = np.delete(data_3d, outliers, axis=0)
```

##### calculate_rom()

Calculate Range of Motion (ROM) for joint angles.

```python
calculate_rom(subject: str, task: str,
              features: Optional[List[str]] = None,
              by_cycle: bool = True) -> Dict[str, Union[float, np.ndarray]]
```

**Parameters:**
- `by_cycle`: If True, calculate ROM per cycle; if False, overall ROM

**Example:**
```python
# ROM per cycle
rom_per_cycle = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=True)
knee_rom_cycles = rom_per_cycle['knee_flexion_angle_ipsi_rad']
print(f"Knee ROM: {knee_rom_cycles.mean():.2f} ± {knee_rom_cycles.std():.2f} rad")

# Overall ROM
rom_overall = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=False)
print(f"Overall knee ROM: {rom_overall['knee_flexion_angle_ipsi_rad']:.2f} rad")
```

#### Statistical Methods

##### get_phase_correlations()

Calculate inter-feature correlations at each phase point.

```python
get_phase_correlations(subject: str, task: str,
                       features: Optional[List[str]] = None) -> np.ndarray
```

**Returns:**
- Array of shape (150, n_features, n_features) with correlation matrices

**Example:**
```python
correlations = loco.get_phase_correlations('SUB01', 'normal_walk')
# Correlation between knee and hip at mid-stance (phase 25)
knee_hip_corr = correlations[37, 0, 2]  # phase 25%, hip-knee correlation
print(f"Knee-hip correlation at mid-stance: {knee_hip_corr:.3f}")
```

##### get_summary_statistics()

Comprehensive statistical summary of all features.

```python
get_summary_statistics(subject: str, task: str,
                       features: Optional[List[str]] = None) -> pd.DataFrame
```

**Returns:**
- DataFrame with mean, std, min, max, median, q25, q75 for each feature

**Example:**
```python
stats = loco.get_summary_statistics('SUB01', 'normal_walk')
print(stats.head())
#                                    mean    std     min     max  median
# knee_flexion_angle_ipsi_rad      0.234  0.187  -0.123   0.891   0.198
```

#### Data Management

##### get_subjects() / get_tasks()

Access available subjects and tasks.

```python
subjects = loco.get_subjects()  # Returns sorted list of subject IDs
tasks = loco.get_tasks()        # Returns sorted list of task names
```

##### merge_with_task_data()

Merge locomotion data with external task information.

```python
merge_with_task_data(task_data: pd.DataFrame,
                     join_keys: List[str] = None,
                     how: str = 'outer') -> pd.DataFrame
```

**Example:**
```python
# External task metadata
task_info = pd.DataFrame({
    'subject': ['SUB01', 'SUB01'],
    'task': ['normal_walk', 'fast_walk'],
    'speed_ms': [1.2, 1.8],
    'condition': ['baseline', 'fast']
})

merged_data = loco.merge_with_task_data(task_info)
```

#### Visualization Methods

##### plot_phase_patterns()

Plot phase-normalized gait patterns with validation overlay.

```python
plot_phase_patterns(subject: str, task: str, features: List[str],
                    plot_type: str = 'both', save_path: Optional[str] = None)
```

**Parameters:**
- `plot_type`: 'mean', 'spaghetti', or 'both'
- Colors: Gray (valid cycles), Red (invalid cycles), Blue (mean pattern)

**Example:**
```python
features = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
loco.plot_phase_patterns('SUB01', 'normal_walk', features, 
                         plot_type='both', save_path='gait_patterns.png')
```

##### plot_task_comparison()

Compare mean patterns across different tasks.

```python
plot_task_comparison(subject: str, tasks: List[str], features: List[str],
                     save_path: Optional[str] = None)
```

**Example:**
```python
tasks = ['normal_walk', 'fast_walk', 'incline_walk']
features = ['knee_flexion_angle_ipsi_rad']
loco.plot_task_comparison('SUB01', tasks, features, save_path='task_comparison.png')
```

#### Properties and Constants

```python
# Class constants
loco.POINTS_PER_CYCLE = 150  # Standard phase points per cycle

# Available feature groups (from feature_constants.py)
loco.ANGLE_FEATURES      # Standard kinematic variables
loco.VELOCITY_FEATURES   # Angular velocity variables  
loco.MOMENT_FEATURES     # Joint moment variables

# Validation constants
loco.STANDARD_JOINTS     # ['hip', 'knee', 'ankle']
loco.STANDARD_MOTIONS    # ['flexion', 'adduction', 'rotation']
loco.STANDARD_SIDES      # ['contra', 'ipsi']
loco.STANDARD_UNITS      # ['rad', 'rad_s', 'Nm', 'Nm_kg', ...]
```

## Validation System API

### DatasetValidator Class

Phase-based dataset validation with visualization.

```python
from lib.validation.dataset_validator_phase import DatasetValidator

validator = DatasetValidator(dataset_path, output_dir=None, generate_plots=True)
```

#### Constructor

```python
DatasetValidator(dataset_path: str, output_dir: str = None, generate_plots: bool = True)
```

**Parameters:**
- `dataset_path`: Path to phase-based dataset (*_phase.parquet)
- `output_dir`: Output directory for reports (default: auto-generated)
- `generate_plots`: Whether to generate validation plots (default: True)

#### Methods

##### run_validation()

Execute complete dataset validation workflow.

```python
report_path = validator.run_validation()
```

**Returns:**
- Path to generated validation report

**Process:**
1. Load dataset using LocomotionData
2. Validate against kinematic/kinetic expectations
3. Generate validation plots with step color coding
4. Create comprehensive markdown report

##### load_dataset()

Load and validate dataset structure.

```python
locomotion_data = validator.load_dataset()
```

**Returns:**
- LocomotionData object ready for validation

**Validation Checks:**
- Required columns present (subject, task, step)
- Standard biomechanical variables available
- Tasks have validation expectations
- Phase data structure valid

### StepClassifier Class

Low-level validation against specification ranges.

```python
from lib.validation.step_classifier import StepClassifier

classifier = StepClassifier()
```

#### Methods

##### validate_data_against_specs()

Validate step data against specification ranges.

```python
failures = classifier.validate_data_against_specs(data_array, task, 
                                                  step_task_mapping, validation_type)
```

**Parameters:**
- `data_array`: 3D array (n_steps, 150, n_features)
- `task`: Task name for validation
- `step_task_mapping`: Dict mapping step indices to tasks
- `validation_type`: 'kinematic' or 'kinetic'

**Returns:**
- List of failure dictionaries with detailed information

## Utility Functions

### Efficient 3D Operations

```python
from lib.core.locomotion_analysis import efficient_reshape_3d

data_3d, features = efficient_reshape_3d(df, subject, task, features,
                                          subject_col='subject', task_col='task',
                                          points_per_cycle=150)
```

### Feature Constants

```python
from lib.core.feature_constants import get_feature_list, get_feature_map

# Get ordered feature lists
kinematic_features = get_feature_list('kinematic')
kinetic_features = get_feature_list('kinetic')

# Get feature index mappings
kinematic_map = get_feature_map('kinematic')
feature_index = kinematic_map['knee_flexion_angle_ipsi_rad']
```

## CLI Tools API

### Dataset Release Tool

```python
# Command line usage
python contributor_scripts/create_dataset_release.py \
    --input dataset_phase.parquet \
    --output release/ \
    --version 1.0.0 \
    --validation-report
```

**Features:**
- Comprehensive dataset validation
- Quality assessment reporting
- Release packaging with metadata
- Validation plot generation

### ML Benchmark Creator

```python
# Command line usage
python contributor_scripts/create_ml_benchmark.py \
    --dataset dataset_phase.parquet \
    --tasks normal_walk,fast_walk \
    --output ml_benchmark/ \
    --splits train,val,test
```

**Features:**
- Train/validation/test splits
- Feature extraction for ML
- Benchmark task definitions
- Performance baseline establishment

### Validation Range Optimizer

```python
# Command line usage
python contributor_scripts/optimize_validation_ranges.py \
    --dataset dataset_phase.parquet \
    --task normal_walk \
    --variable knee_flexion_angle_ipsi_rad \
    --method statistical
```

**Features:**
- Statistical range optimization
- Population-based validation tuning
- Specification update workflow
- Range justification reporting

## Error Handling Patterns

### Common Exceptions

```python
try:
    loco = LocomotionData('dataset.parquet')
except FileNotFoundError:
    print("Dataset file not found")
except ValueError as e:
    if "Missing required columns" in str(e):
        print("Dataset missing required columns")
    elif "Non-standard variable name" in str(e):
        print("Variable naming convention violation")
    else:
        print(f"Data validation error: {e}")
```

### Graceful Degradation

```python
# Handle missing features gracefully
data_3d, available_features = loco.get_cycles(subject, task, requested_features)
if data_3d is None:
    print(f"No data available for {subject}-{task}")
else:
    missing_features = set(requested_features) - set(available_features)
    if missing_features:
        print(f"Missing features: {missing_features}")
```

## Performance Considerations

### Memory Management

```python
# For large datasets, process in chunks
subjects = loco.get_subjects()
for subject in subjects:
    data_3d, features = loco.get_cycles(subject, task)
    # Process subject data
    # Data automatically cached for repeated access
```

### Caching Behavior

- 3D arrays cached automatically by subject-task-features key
- Cache cleared when LocomotionData object is destroyed
- Manual cache management not required for typical usage

### Parallel Processing Support

```python
from concurrent.futures import ProcessPoolExecutor

def process_subject(subject):
    return loco.get_summary_statistics(subject, 'normal_walk')

with ProcessPoolExecutor() as executor:
    results = list(executor.map(process_subject, subjects))
```

## Integration Patterns

### With Pandas/NumPy

```python
# Extract to pandas for statistical analysis
stats_df = loco.get_summary_statistics('SUB01', 'normal_walk')
correlation_matrix = stats_df.corr()

# Convert to numpy for mathematical operations
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
mean_pattern = np.mean(data_3d, axis=0)  # Shape: (150, n_features)
```

### With Scikit-learn

```python
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Prepare ML features
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
X = data_3d.reshape(data_3d.shape[0], -1)  # Flatten to (n_cycles, 150*n_features)

# Standardize and apply PCA
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
pca = PCA(n_components=10)
X_reduced = pca.fit_transform(X_scaled)
```

### With Clinical Systems

```python
# Export for clinical analysis
summary = loco.get_summary_statistics('PATIENT_001', 'normal_walk')
rom_data = loco.calculate_rom('PATIENT_001', 'normal_walk')

# Generate clinical report format
clinical_report = {
    'patient_id': 'PATIENT_001',
    'assessment_date': '2024-01-15',
    'knee_rom_degrees': np.degrees(rom_data['knee_flexion_angle_ipsi_rad']),
    'gait_symmetry': calculate_symmetry_index(loco, 'PATIENT_001', 'normal_walk')
}
```

This API reference provides comprehensive technical documentation for all public interfaces in the locomotion data standardization platform.