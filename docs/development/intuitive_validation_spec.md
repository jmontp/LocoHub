# Intuitive Biomechanical Validation Specification

## Overview

The Intuitive Biomechanical Validation system provides phase-based validation using clinically intuitive expected joint angle ranges at key gait phases. This complements the existing 5-layer validation system by providing more interpretable test cases based on clinical gait analysis knowledge.

## Key Features

- **Phase-based validation** using expected joint angle ranges at heel strike (0-10%) and mid-stance (45-55%)
- **Task-specific adjustments** for different cyclic activities
- **Velocity validation** through phase derivatives (d_angle/d_phase)
- **Comprehensive error tracking** showing which tasks and measurements fail validation
- **Clinical interpretation** with severity assessment (Mild/Moderate/Severe)

## Supported Cyclic Tasks

The validation system only operates on tasks with meaningful phase relationships:

- `level_walking` - Normal walking on level ground
- `incline_walking` - Walking on inclined surfaces
- `decline_walking` - Walking on declined surfaces  
- `run` - Running gait patterns
- `up_stairs` - Stair ascent
- `down_stairs` - Stair descent
- `sit_to_stand` - Rising from seated position
- `squats` - Deep squat movements
- `jump` - Jumping activities

Non-cyclic tasks (poses, ball_toss, etc.) are automatically skipped since they don't have meaningful phase progressions.

## Validation Framework

### 1. Phase Windows

Two critical phases are validated for each joint:

#### Heel Strike Phase (0-10%)
- **Purpose**: Initial contact and loading response
- **Clinical significance**: Joint positioning for impact absorption and stability
- **Typical patterns**:
  - Hip: Slight flexion for limb advancement
  - Knee: Near neutral for initial contact
  - Ankle: Near neutral or slight dorsiflexion

#### Mid-Stance Phase (45-55%)
- **Purpose**: Single limb support and forward progression
- **Clinical significance**: Peak loading and stability requirements
- **Typical patterns**:
  - Hip: Near neutral to slight extension
  - Knee: Slight flexion for shock absorption
  - Ankle: Dorsiflexion for forward progression

### 2. Expected Joint Angle Ranges

Ranges are defined in radians following the sign convention:
- **Hip extension**: Positive
- **Knee extension**: Positive  
- **Ankle dorsiflexion**: Positive

#### Level Walking (Baseline)

| Joint | Heel Strike (0-10%) | Mid-Stance (45-55%) |
|-------|---------------------|---------------------|
| Hip Flexion | 15-25° | -5-5° (neutral) |
| Knee Flexion | -5-5° (neutral) | 10-25° |
| Ankle Flexion | -5-5° (neutral) | 5-15° (dorsiflexed) |
| Hip Adduction | -10-10° | -8-8° |

#### Task-Specific Adjustments

**Incline Walking**:
- Increased hip flexion (20-35° at heel strike)
- Greater knee flexion for absorption
- More ankle dorsiflexion

**Running**:
- Higher hip flexion (25-40° at heel strike)
- Increased knee flexion for impact
- More dynamic ranges throughout

**Stair Ascent**:
- High hip flexion (35-50° at heel strike)
- Very high knee flexion (60-80° at heel strike)
- Sustained ankle dorsiflexion

**Squats**:
- Extreme flexion ranges (60-90° hip, 90-130° knee)
- Symmetric cycle patterns

### 3. Velocity Validation

Angular velocities are validated by computing phase derivatives:

```
d(angle)/d(phase) vs measured_velocity
```

**Validation Rules**:
- Sign consistency between phase derivative and measured velocity
- Tolerance for noise (±0.01 rad/s threshold)
- Only applied to cyclic tasks with continuous phase progression

**Error Detection**:
- Positive phase derivative with negative measured velocity
- Negative phase derivative with positive measured velocity

## Error Classification

### Error Types

1. **angle_out_of_range**: Joint angle outside expected range for task/phase
2. **velocity_sign_inconsistency**: Velocity direction inconsistent with phase progression

### Severity Assessment

**Mild** (< 10° deviation):
- Minor biomechanical variations
- Likely within normal population variance
- May indicate measurement noise

**Moderate** (10-20° deviation):
- Noticeable biomechanical differences
- May indicate compensation strategies
- Requires investigation

**Severe** (> 20° deviation):
- Significant biomechanical abnormalities
- Likely measurement errors or pathological movement
- Requires immediate attention

## Error Tracking Table

The comprehensive error table provides:

| Column | Description |
|--------|-------------|
| `task_name` | Activity being performed |
| `joint` | Specific joint measurement |
| `phase` | Phase window (heel_strike, mid_stance, all_phases) |
| `error_type` | Type of validation failure |
| `count` | Number of validation failures |
| `severity_avg` | Average severity score (1=Mild, 2=Moderate, 3=Severe) |
| `severity_distribution` | Breakdown of severity levels |

## Clinical Interpretation

### Common Error Patterns

**High Velocity Inconsistencies**:
- May indicate poor phase detection
- Could suggest measurement synchronization issues
- Common in transition phases

**Heel Strike Angle Errors**:
- Often related to foot strike patterns
- May indicate clearance or stability issues
- Critical for injury risk assessment

**Mid-Stance Angle Errors**:
- Related to loading response and stability
- May indicate strength or balance deficits
- Important for functional capacity

### Validation Workflow

1. **Load phase-indexed data** with required columns (`phase_%`, `task_name`)
2. **Filter to cyclic tasks** automatically
3. **Apply phase-window validation** for each joint at heel strike and mid-stance
4. **Validate velocity consistency** using phase derivatives
5. **Generate error table** summarizing failures by task and measurement
6. **Assess clinical significance** using severity scoring

## Integration with Existing Validation

The intuitive validation system complements the existing 5-layer validation:

- **Layer 0-4**: Technical and biomechanical constraints
- **Intuitive Layer**: Clinical interpretation and phase-specific expectations

Both systems can be run in parallel to provide comprehensive validation coverage:
- Technical validation ensures data integrity
- Intuitive validation provides clinical context

## Usage Example

```python
from validation_intuitive_biomechanics import IntuitiveValidator

# Load phase-indexed data
validator = IntuitiveValidator(df)
validated_df = validator.validate()

# Get results
error_table = validator.get_error_table()
clinical_report = validator.get_clinical_report()

# Export comprehensive tables
validator.export_expectations_table("expected_ranges.csv")
error_table.to_csv("validation_errors.csv")
```

## Implementation Notes

### Performance Considerations
- Only processes cyclic tasks (reduces computation)
- Vectorized operations for phase window detection
- Efficient groupby operations for velocity validation

### Extensibility
- Easy to add new cyclic tasks with specific ranges
- Modular phase window definitions
- Configurable severity thresholds

### Validation Quality
- Based on published biomechanical research
- Clinically relevant phase windows
- Task-specific adjustments from literature

This intuitive validation system provides clinically meaningful validation that complements technical data quality checks, enabling better interpretation of biomechanical data quality and identification of movement patterns that warrant further investigation.