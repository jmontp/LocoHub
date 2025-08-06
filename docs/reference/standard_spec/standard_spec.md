# Locomotion Data Standard

Standardized format for biomechanical datasets with consistent variable naming and structure.

**Quick Reference:** [Variable Naming](#variable-naming) • [Data Formats](#data-formats) • [Task Definitions](#task-definitions)

## Data Formats

---

### Time-Indexed Data
*Original sampling frequency preserved*

- **Format**: `dataset_time.parquet`
- **Structure**: Continuous time series data
- **Use case**: Temporal analysis, event detection

---

### Phase-Indexed Data  
*Normalized to 150 points per gait cycle*

- **Format**: `dataset_phase.parquet` 
- **Structure**: 150 points per cycle (0-100%)
- **Use case**: Cross-subject comparison, averaging

---

## Variable Naming

**Pattern**: `<joint>_<motion>_<measurement>_<side>_<unit>`

**Examples**:
- `knee_flexion_angle_ipsi_rad`
- `hip_moment_contra_Nm`
- `ankle_flexion_velocity_ipsi_rad_s`

**Sides**:
- `ipsi` - Ipsilateral (same side as leading leg)
- `contra` - Contralateral (opposite side)

**Units**:
- Angles: `rad` (radians)
- Moments: `Nm` (Newton-meters) 
- Velocities: `rad_s` (radians per second)
- Forces: `N` (Newtons)

## Required Columns

**Structural**:
- `subject` - Subject identifier
- `task` - Task name
- `step` - Step/cycle number

**Phase Data**:
- `phase_ipsi` - Gait cycle phase (0-100%) aligned to ipsilateral heel strike

**Time Data**:
- `time_s` - Time in seconds

## Standard Variables

**Joint Angles** (required):
- `hip_flexion_angle_<side>_rad`
- `knee_flexion_angle_<side>_rad` 
- `ankle_dorsiflexion_angle_<side>_rad`

**Segment Angles** (optional):
- `pelvis_sagittal_angle_rad` - Anterior/posterior tilt
- `pelvis_frontal_angle_rad` - Lateral tilt (obliquity)
- `pelvis_transverse_angle_rad` - Axial rotation
- `trunk_sagittal_angle_rad` - Forward/backward lean
- `trunk_frontal_angle_rad` - Lateral bend
- `trunk_transverse_angle_rad` - Axial rotation
- `thigh_sagittal_angle_<side>_rad` - Thigh orientation
- `shank_sagittal_angle_<side>_rad` - Shank orientation
- `foot_sagittal_angle_<side>_rad` - Foot orientation

**Joint Angular Velocities** (optional):
- `hip_flexion_velocity_<side>_rad_s` - Hip flexion/extension angular velocity
- `knee_flexion_velocity_<side>_rad_s` - Knee flexion/extension angular velocity
- `ankle_dorsiflexion_velocity_<side>_rad_s` - Ankle dorsiflexion/plantarflexion angular velocity

**Segment Angular Velocities** (optional):
- `pelvis_sagittal_velocity_rad_s` - Pelvis tilt angular velocity
- `pelvis_frontal_velocity_rad_s` - Pelvis obliquity angular velocity
- `pelvis_transverse_velocity_rad_s` - Pelvis rotation angular velocity
- `trunk_sagittal_velocity_rad_s` - Trunk lean angular velocity
- `trunk_frontal_velocity_rad_s` - Trunk bend angular velocity
- `trunk_transverse_velocity_rad_s` - Trunk rotation angular velocity
- `thigh_sagittal_velocity_<side>_rad_s` - Thigh angular velocity
- `shank_sagittal_velocity_<side>_rad_s` - Shank angular velocity
- `foot_sagittal_velocity_<side>_rad_s` - Foot angular velocity

**Joint Moments** (optional):
- `hip_flexion_moment_<side>_Nm`
- `knee_flexion_moment_<side>_Nm`
- `ankle_dorsiflexion_moment_<side>_Nm`

**Ground Forces** (optional):
- `vertical_grf_<side>_N`
- `anterior_grf_<side>_N`
- `lateral_grf_<side>_N`

## Task Definitions

**Standard Task Names**:
- `level_walking` - Walking on level ground
- `incline_walking` - Walking uphill
- `decline_walking` - Walking downhill  
- `up_stairs` - Stair ascent
- `down_stairs` - Stair descent
- `run` - Running
- `sit_to_stand` - Chair rise
- `jump` - Jumping
- `squats` - Squatting motion

## Sign Conventions

**Joint Angles**:
- **Positive flexion**: Hip, knee, ankle dorsiflexion
- **Negative extension**: Hip, knee, ankle plantarflexion

**Coordinate System**:
- **X**: Anterior (forward)
- **Y**: Superior (up)
- **Z**: Lateral (right)

**Ground Forces**:
- **Positive Y**: Upward (vertical)
- **Positive X**: Forward (anterior)
- **Positive Z**: Rightward (lateral)

## Phase Calculation

**Phase-indexed data normalization**:
1. Detect gait events (heel strike to heel strike)
2. Normalize each cycle to exactly 150 points
3. Calculate phase percentage: `phase_percent = (point_index / 149) * 100`

**Phase Interpretation**:
- `0%` - Heel strike (start of gait cycle)
- `~60%` - Opposite heel strike (typical)
- `100%` - Next heel strike (end of cycle)

## Missing Data

**Handling**:
- Missing values: `NaN` (Not a Number)
- Invalid measurements: `NaN`
- No synthetic data generation

**Quality Flags** (optional):
- `is_reconstructed_<side>` - Boolean flag for filled data
- Use `true` for interpolated/reconstructed values

## File Examples

**Time-indexed**:
```
subject,task,step,time_s,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
SUB01,level_walking,0,0.00,0.123,-0.456
SUB01,level_walking,0,0.01,0.126,-0.445
SUB01,level_walking,1,1.20,0.120,-0.460
```

**Phase-indexed**:
```
subject,task,step,phase_percent,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
SUB01,level_walking,0,0.0,0.123,-0.456
SUB01,level_walking,0,0.7,0.126,-0.445
SUB01,level_walking,0,100.0,0.120,-0.460
SUB01,level_walking,1,0.0,0.125,-0.458
```

## Validation Requirements

**Phase Data Validation**:
- Exactly 150 points per cycle
- Phase values: 0.0 to 100.0
- No gaps in phase progression

**Variable Validation**:
- Joint angles: -π to π radians  
- Realistic biomechanical ranges
- Consistent units across datasets

---

*For detailed implementation examples, see the [Python Tutorial](../tutorials/python/getting_started_python.md) and [MATLAB Tutorial](../tutorials/matlab/getting_started_matlab.md).*