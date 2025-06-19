# Validation Rules Reference

Quick reference for locomotion data validation requirements and quality checks.

## Data Structure Requirements

### Required Columns

**Phase-indexed datasets** (`*_phase.parquet`):
- `subject` - Subject identifier
- `task` - Task name from standard list
- `step` - Step/cycle number  
- `phase_percent` - Gait cycle phase (0-100%)

**Time-indexed datasets** (`*_time.parquet`):
- `subject` - Subject identifier
- `task` - Task name from standard list
- `step` - Step/cycle number
- `time_s` - Time in seconds

### Standard Variables

**Joint Angles** (required):
- `hip_flexion_angle_ipsi_rad`
- `knee_flexion_angle_ipsi_rad`
- `ankle_flexion_angle_ipsi_rad`
- `hip_flexion_angle_contra_rad`
- `knee_flexion_angle_contra_rad`
- `ankle_flexion_angle_contra_rad`

**Moments and Forces** (optional):
- `hip_moment_<side>_Nm`
- `knee_moment_<side>_Nm`
- `ankle_moment_<side>_Nm`
- `vertical_grf_<side>_N`

## Phase-Indexed Requirements

### Structural Validation

| Check | Requirement | Validation |
|:------|:------------|:-----------|
| **Points per cycle** | Exactly 150 points | Each `(subject, task, step)` must have 150 rows |
| **Phase coverage** | 0-100% complete | `phase_percent` from 0.0 to 100.0 |
| **Phase spacing** | Even distribution | Approximately 0.67% increments |
| **Data completeness** | No missing values | No NaN/null in required columns |

### Data Quality Checks

| Check | Criteria | Action |
|:------|:---------|:-------|
| **Range validation** | Values within biomechanical limits | Validate against specification ranges |
| **Temporal consistency** | Smooth phase progression | Check for phase jumps or gaps |
| **Step completeness** | Complete gait cycles only | Remove incomplete cycles |
| **Bilateral coordination** | Ipsi/contra relationship | Verify contralateral offset logic |

## Range Validation

### Joint Angle Limits

**General biomechanical ranges** (approximate):

| Joint | Flexion Range | Extension Range | Units |
|:------|:--------------|:----------------|:------|
| **Hip** | 0 to +2.1 rad | 0 to -0.5 rad | radians |
| **Knee** | 0 to +2.4 rad | 0 to -0.2 rad | radians |
| **Ankle** | -0.5 to +0.5 rad | -0.9 to +0.3 rad | radians |

### Task-Specific Validation

Phase-specific ranges vary by task:
- **Level walking**: Standard gait patterns
- **Incline/decline**: Modified hip/ankle ranges
- **Stairs**: Increased knee flexion
- **Running**: Greater joint excursions
- **Sit-to-stand**: Large hip/knee flexion

### Phase-Based Validation

**Key phases**:
- **0%**: Heel strike (initial contact)
- **25%**: Mid-stance (loading response)
- **50%**: Toe-off (terminal stance)
- **75%**: Mid-swing (swing phase)

**Contralateral offset**:
- Ipsi 0% = Contra 50%
- Ipsi 25% = Contra 75%
- Ipsi 50% = Contra 0%
- Ipsi 75% = Contra 25%

## Standard Tasks

| Task | Code | Requirements |
|:-----|:-----|:-------------|
| Level walking | `level_walking` | Standard gait cycle |
| Incline walking | `incline_walking` | Modified ankle/hip ranges |
| Decline walking | `decline_walking` | Modified ankle/hip ranges |
| Stair ascent | `up_stairs` | Increased knee flexion |
| Stair descent | `down_stairs` | Controlled knee extension |
| Running | `run` | Greater joint excursions |
| Sit-to-stand | `sit_to_stand` | Large hip/knee motion |
| Jumping | `jump` | Ballistic patterns |
| Squats | `squats` | Deep knee flexion |

## Sign Conventions

### Joint Angles
- **Positive**: Flexion (hip, knee), dorsiflexion (ankle)
- **Negative**: Extension (hip, knee), plantarflexion (ankle)

### Coordinate System
- **X**: Anterior (forward, positive)
- **Y**: Superior (up, positive)  
- **Z**: Lateral (right, positive)

## Validation Process

### Phase 1: Structure Check
1. File format validation (parquet)
2. Required column presence
3. Data type validation
4. Shape consistency (150 points for phase data)

### Phase 2: Quality Check
1. Missing value detection
2. Outlier identification
3. Range validation against specifications
4. Temporal consistency verification

### Phase 3: Biomechanical Check
1. Phase-specific range validation
2. Bilateral coordination verification
3. Task-appropriate pattern validation
4. Contralateral offset validation

## Error Types

### Critical Errors
- Missing required columns
- Wrong number of points per cycle
- Data type mismatches
- Complete missing data

### Quality Warnings
- Values outside normal ranges
- Irregular phase spacing
- Missing optional variables
- Incomplete bilateral data

### Biomechanical Flags
- Implausible joint combinations
- Task-inappropriate patterns
- Phase relationship violations
- Extreme outlier values

## Validation Tools

### Command Line
```bash
# Quick validation
python dataset_validator_phase.py --dataset data_phase.parquet

# Full validation with plots
python dataset_validator_phase.py --dataset data_phase.parquet --generate-plots

# Custom output directory
python dataset_validator_phase.py --dataset data_phase.parquet --output reports/
```

### Python API
```python
from lib.validation.dataset_validator_phase import DatasetValidator

# Initialize validator
validator = DatasetValidator('data_phase.parquet')

# Run validation
results = validator.validate_dataset()

# Check results
if results['valid']:
    print("Dataset passed validation")
else:
    print(f"Validation errors: {results['errors']}")
```

## Output Reports

Validation generates:
- **Text report**: Detailed validation results
- **Summary statistics**: Data quality metrics
- **Filter plots**: Phase-based validation visualization
- **Error logs**: Specific validation failures

Reports saved to: `source/tests/sample_plots/validation_reports/{dataset_name}/`