# Data Format Specifications and Standards

Comprehensive reference for locomotion data formats, column requirements, validation rules, and format specifications.

**Quick Reference:** [File Formats](#file-formats) • [Column Requirements](#column-requirements) • [Phase vs Time Indexing](#phase-vs-time-indexing) • [Validation Rules](#validation-rules) • [Variable Naming](#variable-naming)

## File Formats

### Supported File Types

**Primary Format**: Apache Parquet (`.parquet`)
- **Binary format**: High compression, fast read/write
- **Schema preservation**: Maintains data types and metadata
- **Cross-platform**: Compatible with Python, R, MATLAB, Spark
- **Memory efficient**: Columnar storage with compression

**Legacy Format**: CSV (`.csv`) - Limited support
- **Text format**: Human readable but larger file sizes
- **Use case**: Data inspection, legacy system compatibility
- **Limitations**: No automatic type inference, slower I/O

### Dataset Naming Convention

**Pattern**: `{institution}_{year}_{indexing}.parquet`

**Examples**:
- `umich_2021_time.parquet` - Time-indexed University of Michigan 2021 dataset
- `gtech_2023_phase.parquet` - Phase-indexed Georgia Tech 2023 dataset
- `addbiomechanics_2024_phase.parquet` - AddBiomechanics consortium dataset

## Phase vs Time Indexing

### Time-Indexed Data

**Format**: `dataset_time.parquet`

**Characteristics**:
- Original sampling frequency preserved (e.g., 100Hz, 1000Hz)
- Variable time intervals between samples
- Event-based analysis capability
- Raw temporal data preservation

**Structure**:
```
subject,task,step,time_s,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
SUB01,level_walking,0,0.000,0.123,-0.456
SUB01,level_walking,0,0.010,0.126,-0.445
SUB01,level_walking,0,0.020,0.128,-0.440
SUB01,level_walking,1,1.200,0.120,-0.460
```

**Use Cases**:
- Temporal analysis and event detection
- Signal processing and filtering
- Real-time analysis applications
- Variable frequency data collection

**Validation Requirements**:
- Monotonic time progression within each step
- Consistent sampling frequency (when applicable)
- No missing time stamps
- Realistic temporal ranges

### Phase-Indexed Data

**Format**: `dataset_phase.parquet`

**Characteristics**:
- Normalized to exactly 150 points per gait cycle
- Phase percentage from 0% to 100%
- Cross-subject comparison enabled
- Movement cycle standardization

**Structure**:
```
subject,task,step,phase_percent,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
SUB01,level_walking,0,0.0,0.123,-0.456
SUB01,level_walking,0,0.7,0.126,-0.445
SUB01,level_walking,0,1.3,0.128,-0.440
SUB01,level_walking,0,100.0,0.120,-0.460
```

**Phase Calculation**:
1. **Gait Event Detection**: Identify heel strike to heel strike
2. **Cycle Extraction**: Extract complete movement cycles
3. **Normalization**: Resample to exactly 150 points
4. **Phase Assignment**: `phase_percent = (point_index / 149) * 100`

**Use Cases**:
- Cross-subject statistical analysis
- Movement pattern comparison
- Average cycle computation
- Biomechanical research

**Validation Requirements**:
- Exactly 150 points per cycle
- Phase values: 0.0 to 100.0
- No gaps in phase progression
- Smooth phase transitions

## Column Requirements

### Structural Columns (Required)

| Column | Type | Description | Example Values |
|--------|------|-------------|----------------|
| `subject` | string | Subject identifier | `SUB01`, `PARTICIPANT_A` |
| `task` | string | Movement task name | `level_walking`, `incline_walking` |
| `step` | integer | Step/cycle number | `0`, `1`, `2`, `...` |

### Temporal Columns (Format-Specific)

**Time-Indexed Data**:
| Column | Type | Description | Range |
|--------|------|-------------|-------|
| `time_s` | float64 | Time in seconds | `0.0` to trial duration |

**Phase-Indexed Data**:
| Column | Type | Description | Range |
|--------|------|-------------|-------|
| `phase_percent` | float64 | Gait cycle phase | `0.0` to `100.0` |

### Biomechanical Data Columns

**Joint Angles** (Kinematic - Required):
```python
# Standard naming pattern: {joint}_flexion_angle_{side}_rad
hip_flexion_angle_ipsi_rad      # Hip flexion, ipsilateral side
hip_flexion_angle_contra_rad    # Hip flexion, contralateral side
knee_flexion_angle_ipsi_rad     # Knee flexion, ipsilateral side
knee_flexion_angle_contra_rad   # Knee flexion, contralateral side
ankle_flexion_angle_ipsi_rad    # Ankle flexion, ipsilateral side
ankle_flexion_angle_contra_rad  # Ankle flexion, contralateral side
```

**Joint Moments** (Kinetic - Optional):
```python
# Standard naming pattern: {joint}_flexion_moment_{side}_Nm
hip_flexion_moment_ipsi_Nm      # Hip flexion moment
hip_flexion_moment_contra_Nm
knee_flexion_moment_ipsi_Nm     # Knee flexion moment
knee_flexion_moment_contra_Nm
ankle_flexion_moment_ipsi_Nm    # Ankle flexion moment
ankle_flexion_moment_contra_Nm
```

**Ground Reaction Forces** (Optional):
```python
# Standard naming pattern: {direction}_grf_{normalization}
vertical_grf_N          # Vertical ground reaction force (Newtons)
ap_grf_N               # Anterior-posterior GRF
ml_grf_N               # Medial-lateral GRF
vertical_grf_N_kg      # Body weight normalized (N/kg)
ap_grf_N_kg            # Body weight normalized
ml_grf_N_kg            # Body weight normalized
```

### Data Types

| Variable Type | Data Type | Precision | Example |
|---------------|-----------|-----------|---------|
| Identifiers | `string` | UTF-8 | `"SUB01"` |
| Integers | `int64` | 64-bit | `42` |
| Measurements | `float64` | 64-bit | `0.523599` |
| Time | `float64` | 64-bit | `1.250000` |
| Phase | `float64` | 64-bit | `67.114094` |

## Variable Naming

### Naming Convention

**Pattern**: `{joint}_{motion}_{measurement}_{side}_{unit}`

**Components**:
- **Joint**: `hip`, `knee`, `ankle`
- **Motion**: `flexion`, `adduction`, `rotation`
- **Measurement**: `angle`, `moment`, `velocity`
- **Side**: `ipsi`, `contra`
- **Unit**: `rad`, `Nm`, `rad_s`, `N`, `N_kg`

### Side Conventions

**Ipsilateral (`ipsi`)**:
- Same side as the leading/reference leg
- Primary leg for movement analysis
- Typically right leg for right-side-dominant subjects

**Contralateral (`contra`)**:
- Opposite side from leading/reference leg
- Supporting leg during movement phases
- Provides bilateral comparison data

### Joint Angle Definitions

**Hip Flexion** (`hip_flexion_angle_{side}_rad`):
- **Positive**: Thigh forward relative to pelvis
- **Zero**: Vertical thigh alignment (anatomical position)
- **Range**: -0.35 to 1.92 radians (-20° to 110°)

**Knee Flexion** (`knee_flexion_angle_{side}_rad`):
- **Zero**: Full extension (OpenSim standard)
- **Positive**: Knee bending (flexion)
- **Range**: 0 to 2.44 radians (0° to 140°)

**Ankle Flexion** (`ankle_flexion_angle_{side}_rad`):
- **Zero**: Foot flat on ground (neutral position)
- **Positive**: Dorsiflexion (toes up)
- **Negative**: Plantarflexion (toes down)
- **Range**: -0.44 to 0.70 radians (-25° to 40°)

## Validation Rules

### Structural Validation

**Required Columns Check**:
```python
# Phase-indexed datasets
required_cols = ['subject', 'task', 'step', 'phase_percent']

# Time-indexed datasets  
required_cols = ['subject', 'task', 'step', 'time_s']

# At least one kinematic variable required
kinematic_required = any([
    'hip_flexion_angle_ipsi_rad',
    'knee_flexion_angle_ipsi_rad', 
    'ankle_flexion_angle_ipsi_rad'
])
```

**Data Type Validation**:
- Subject identifiers: Non-empty strings
- Task names: Valid task from approved list
- Step numbers: Non-negative integers
- Time/phase values: Positive floats
- Biomechanical measurements: Float64 with realistic ranges

### Phase-Indexed Validation

**Cycle Structure**:
- Exactly 150 points per cycle
- Phase values: 0.0, 0.671..., 1.342..., ..., 100.0
- Monotonic phase progression
- No missing phase points

**Phase Validation Logic**:
```python
def validate_phase_structure(data):
    for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
        # Check point count
        assert len(group) == 150, f"Cycle {subject}-{task}-{step} has {len(group)} points, expected 150"
        
        # Check phase range
        phases = group['phase_percent'].values
        assert phases[0] == 0.0, f"First phase should be 0.0, got {phases[0]}"
        assert phases[-1] == 100.0, f"Last phase should be 100.0, got {phases[-1]}"
        
        # Check monotonic progression
        assert all(phases[i] <= phases[i+1] for i in range(len(phases)-1)), "Non-monotonic phase progression"
```

### Biomechanical Range Validation

**Joint Angle Ranges** (Phase-specific validation):
- Hip flexion: Task-specific ranges at 0%, 25%, 50%, 75% phases
- Knee flexion: Biomechanically realistic ranges per movement phase  
- Ankle flexion: Phase-appropriate dorsi/plantarflexion limits

**Range Validation Example**:
```python
# Level walking knee flexion ranges (radians)
LEVEL_WALKING_KNEE_RANGES = {
    0:   {'min': -0.1, 'max': 0.3},   # Heel strike: slight flexion
    25:  {'min': 0.0, 'max': 0.4},    # Mid-stance: controlled flexion
    50:  {'min': 0.8, 'max': 1.2},    # Toe-off: peak flexion
    75:  {'min': 0.2, 'max': 0.8}     # Mid-swing: swing flexion
}
```

**Kinetic Range Validation**:
- Joint moments: Physiologically reasonable peak values
- Ground reaction forces: Within expected body weight multiples
- Force patterns: Consistent with movement biomechanics

### Task-Specific Validation

**Approved Task Names**:
```python
STANDARD_TASKS = {
    'level_walking': 'Walking on level ground',
    'incline_walking': 'Walking uphill',
    'decline_walking': 'Walking downhill',
    'up_stairs': 'Stair ascent',
    'down_stairs': 'Stair descent',
    'run': 'Running',
    'sit_to_stand': 'Chair rise',
    'jump': 'Jumping movement',
    'squats': 'Squatting exercise'
}
```

**Task Validation**:
- Task names must match approved list exactly
- Movement patterns consistent with task definition
- Appropriate duration and cycle characteristics
- Expected force and moment magnitudes

## Quality Assurance

### Missing Data Handling

**Permitted Missing Values**:
- `NaN` for missing biomechanical measurements
- Empty cells for optional kinetic data
- No synthetic data generation

**Quality Flags** (Optional):
```python
is_reconstructed_ipsi       # Boolean: True if data interpolated
is_reconstructed_contra     # Boolean: True if data interpolated
quality_score              # Float: 0.0-1.0 data quality metric
```

### Data Integrity Checks

**Consistency Validation**:
- Bilateral data correlation (ipsi vs contra patterns)
- Temporal/phase continuity
- Cross-variable relationships
- Subject-specific consistency across trials

**Outlier Detection**:
- Statistical outliers beyond 3 standard deviations
- Biomechanically implausible values
- Sudden discontinuities in time series
- Inconsistent movement patterns

### Validation Pipeline

**Automated Validation Steps**:
1. **Structure Check**: Column names, data types, required fields
2. **Format Validation**: Phase/time indexing requirements
3. **Range Validation**: Biomechanical plausibility checks
4. **Pattern Validation**: Movement-specific expectations
5. **Quality Assessment**: Data completeness and consistency

**Validation Output**:
- **Pass/Fail Status**: Overall dataset validation result
- **Error Report**: Detailed list of validation failures
- **Warning Report**: Potential quality concerns
- **Quality Metrics**: Completeness, consistency, accuracy scores

## Implementation Examples

### Loading Data with Validation

**Python Example**:
```python
from lib.core.locomotion_analysis import LocomotionData

# Load and validate phase-indexed data
data = LocomotionData.from_parquet('gtech_2023_phase.parquet')

# Automatic validation on load
if data.validate():
    print("Dataset passed all validation checks")
    print(f"Shape: {data.shape}")
    print(f"Tasks: {data.get_tasks()}")
else:
    print("Validation failures detected")
    data.show_validation_report()
```

**MATLAB Example**:
```matlab
% Load phase-indexed data
data = LocomotionData('umich_2021_phase.parquet');

% Check validation status
if data.is_valid()
    fprintf('Dataset validation: PASSED\n');
    fprintf('Subjects: %d, Tasks: %d, Steps: %d\n', ...
        data.n_subjects, data.n_tasks, data.n_steps);
else
    data.show_validation_report();
end
```

### Custom Validation

**Extending Validation Rules**:
```python
from lib.validation.dataset_validator_phase import PhaseDatasetValidator

# Create custom validator
validator = PhaseDatasetValidator()

# Add custom biomechanical range
validator.add_custom_range(
    variable='knee_flexion_angle_ipsi_rad',
    task='level_walking',
    phase=50,  # Toe-off
    min_val=0.8,
    max_val=1.2
)

# Validate dataset
results = validator.validate(data)
```

---

*This specification ensures consistent, high-quality biomechanical datasets across all supported formats and validation systems.*