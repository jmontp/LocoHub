# Biomechanical Data Standard

**Complete Technical Reference for Locomotion Data Standardization**

---

## Quick Navigation

[📊 Data Formats](#data-structure-specification) | [🔤 Variables](#variable-naming-system) | [📐 Conventions](#coordinate-system--conventions) | [✅ Validation](#validation-requirements) | [📝 Examples](#implementation-examples)

---

## 1. Data Structure Specification

### Data Format Comparison

| Aspect | Time-Indexed | Phase-Indexed |
|--------|--------------|---------------|
| **File Pattern** | `dataset_time.parquet` | `dataset_phase.parquet` |
| **Structure** | Continuous time series | 150 points per cycle |
| **Index** | Time in seconds | Phase 0-100% |
| **Use Case** | Event detection, raw analysis | Cross-subject comparison |
| **Storage** | Larger (variable samples/cycle) | Compact (fixed 150 points) |

### Required Columns

#### Metadata Columns (Required for All Datasets)
- `subject` - Subject identifier (e.g., "Gtech_2023_AB01")
- `task` - Biomechanical category (e.g., "level_walking")
- `task_id` - Task variant with primary parameter (e.g., "incline_10deg")
- `task_info` - Metadata in key:value format (e.g., "incline_deg:10,speed_m_s:1.2")
- `step` - Step/cycle number (integer)

#### Phase Columns (Phase-Indexed Only)
- `phase_ipsi` - Gait cycle phase 0-100% aligned to ipsilateral heel strike

#### Time Columns (Time-Indexed Only)
- `time_s` - Time in seconds from trial start

---

## 2. Coordinate System & Conventions

### OpenSim Coordinate System

```
        Y (Superior) ↑
                     |
                     |
        ————————————————————→ X (Anterior)
                    /
                   /
                  ↓ Z (Right)
```

**Right-Hand Rule**: Positive rotations follow right-hand curl around axis

### Reference Frames
- **Global Frame**: Laboratory/world coordinate system
- **Segment Frames**: Local to each body segment
- **Joint Frames**: Defined at joint centers

---

## 3. Variable Naming System

### Naming Pattern
`<joint/segment>_<motion>_<measurement>_<side>_<unit>`

### Comprehensive Variable Reference

#### Joint Angles (Kinematics)

| Variable | Description | Unit | Typical Range | Sign Convention |
|----------|-------------|------|---------------|-----------------|
| `hip_flexion_angle_ipsi_rad` | Hip flexion/extension | rad | -0.35 to 1.92 | (+) flexion, (-) extension |
| `hip_adduction_angle_ipsi_rad` | Hip ab/adduction | rad | -0.35 to 0.52 | (+) adduction, (-) abduction |
| `hip_rotation_angle_ipsi_rad` | Hip int/ext rotation | rad | -0.52 to 0.52 | (+) external, (-) internal |
| `knee_flexion_angle_ipsi_rad` | Knee flexion/extension | rad | -0.17 to 2.44 | (+) flexion, (-) extension |
| `ankle_dorsiflexion_angle_ipsi_rad` | Ankle dorsi/plantar | rad | -0.44 to 0.70 | (+) dorsiflexion, (-) plantarflexion |
| `ankle_eversion_angle_ipsi_rad` | Ankle in/eversion | rad | -0.26 to 0.35 | (+) eversion, (-) inversion |

#### Joint Moments (Kinetics)

| Variable | Description | Unit | Typical Range | Sign Convention |
|----------|-------------|------|---------------|-----------------|
| `hip_flexion_moment_ipsi_Nm` | Hip flexion/extension moment | Nm | -80 to 80 | (+) flexor moment |
| `knee_flexion_moment_ipsi_Nm` | Knee flexion/extension moment | Nm | -60 to 40 | (+) flexor moment |
| `ankle_dorsiflexion_moment_ipsi_Nm` | Ankle dorsi/plantar moment | Nm | -120 to 20 | (+) dorsiflexor moment |

#### Segment Angles (Absolute Orientations)

| Variable | Description | Unit | Typical Range | Sign Convention |
|----------|-------------|------|---------------|-----------------|
| `pelvis_sagittal_angle_rad` | Pelvis anterior/posterior tilt | rad | -0.17 to 0.35 | (+) anterior tilt |
| `pelvis_frontal_angle_rad` | Pelvis lateral tilt | rad | -0.17 to 0.17 | (+) right side up |
| `pelvis_transverse_angle_rad` | Pelvis axial rotation | rad | -0.26 to 0.26 | (+) right forward |
| `trunk_sagittal_angle_rad` | Trunk forward/backward lean | rad | -0.26 to 0.52 | (+) forward lean |
| `thigh_sagittal_angle_ipsi_rad` | Thigh segment angle | rad | -0.52 to 1.57 | (+) forward from vertical |
| `shank_sagittal_angle_ipsi_rad` | Shank segment angle | rad | -0.70 to 1.22 | (+) forward from vertical |
| `foot_sagittal_angle_ipsi_rad` | Foot segment angle | rad | -0.52 to 0.52 | (+) toe up |

#### Joint Velocities

| Variable | Description | Unit | Typical Range |
|----------|-------------|------|---------------|
| `hip_flexion_velocity_ipsi_rad_s` | Hip angular velocity | rad/s | -4.0 to 4.0 |
| `knee_flexion_velocity_ipsi_rad_s` | Knee angular velocity | rad/s | -8.0 to 8.0 |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | Ankle angular velocity | rad/s | -6.0 to 6.0 |

#### Ground Reaction Forces

| Variable | Description | Unit | Typical Range | Sign Convention |
|----------|-------------|------|---------------|-----------------|
| `vertical_grf_ipsi_N` | Vertical GRF | N | 0 to 1500 | (+) upward |
| `anterior_grf_ipsi_N` | Anterior-posterior GRF | N | -200 to 200 | (+) forward/propulsive |
| `lateral_grf_ipsi_N` | Medial-lateral GRF | N | -100 to 100 | (+) lateral/rightward |

---

## 4. Biomechanical Definitions

### Joint Angle Definitions

<details>
<summary><b>Hip Joint Angles</b></summary>

#### Hip Flexion/Extension
- **Zero**: Anatomical position (thigh aligned with trunk)
- **Positive**: Hip flexion (thigh moves forward)
- **Negative**: Hip extension (thigh moves backward)
- **Normal Walking Range**: -20° to 30° (-0.35 to 0.52 rad)
- **Maximum Range**: -30° to 120° (-0.52 to 2.09 rad)

#### Hip Adduction/Abduction
- **Zero**: Neutral position
- **Positive**: Hip adduction (thigh toward midline)
- **Negative**: Hip abduction (thigh away from midline)
- **Normal Walking Range**: -5° to 10° (-0.09 to 0.17 rad)

#### Hip Rotation
- **Zero**: Neutral rotation
- **Positive**: External rotation (foot points outward)
- **Negative**: Internal rotation (foot points inward)
- **Normal Walking Range**: -15° to 15° (-0.26 to 0.26 rad)

</details>

<details>
<summary><b>Knee Joint Angles</b></summary>

#### Knee Flexion/Extension
- **Zero**: Full extension (straight leg)
- **Positive**: Knee flexion (heel toward buttocks)
- **Negative**: Hyperextension (beyond straight)
- **Normal Walking Range**: 0° to 60° (0 to 1.05 rad)
- **Maximum Range**: -10° to 140° (-0.17 to 2.44 rad)

#### Knee Varus/Valgus
- **Zero**: Neutral alignment
- **Positive**: Valgus (knee toward midline)
- **Negative**: Varus (knee away from midline)
- **Normal Range**: -5° to 5° (-0.09 to 0.09 rad)

</details>

<details>
<summary><b>Ankle Joint Angles</b></summary>

#### Ankle Dorsiflexion/Plantarflexion
- **Zero**: Neutral position (foot at 90° to shank)
- **Positive**: Dorsiflexion (toes point up)
- **Negative**: Plantarflexion (toes point down)
- **Normal Walking Range**: -25° to 20° (-0.44 to 0.35 rad)
- **Maximum Range**: -50° to 40° (-0.87 to 0.70 rad)

#### Ankle Inversion/Eversion
- **Zero**: Neutral position
- **Positive**: Eversion (sole faces outward)
- **Negative**: Inversion (sole faces inward)
- **Normal Range**: -20° to 15° (-0.35 to 0.26 rad)

</details>

### Segment Angle Relationships

#### Mathematical Formulas

```
Segment angles are calculated from joint angles using chain relationships:

pelvis_angle = absolute pelvis orientation (from motion capture)
thigh_angle = pelvis_sagittal_angle + hip_flexion_angle
shank_angle = thigh_angle - knee_flexion_angle
foot_angle = shank_angle - ankle_dorsiflexion_angle
```

#### Visual Chain Representation

```
Pelvis (absolute) 
    ↓ [+ hip_flexion]
Thigh Segment
    ↓ [- knee_flexion]
Shank Segment
    ↓ [- ankle_flexion]
Foot Segment
```

### Forces and Moments

#### Ground Reaction Forces (GRF)

**Coordinate Convention**:
- **Vertical (Y)**: Positive upward
- **Anterior-Posterior (X)**: Positive forward (propulsive)
- **Medial-Lateral (Z)**: Positive rightward

**Typical Values (Walking)**:
- Vertical: 1.0-1.2 × body weight
- A-P: ±0.2 × body weight
- M-L: ±0.05 × body weight

#### Joint Moments

**Sign Convention**: Right-hand rule around joint axis
- **Positive**: Creates positive joint angle change
- **Negative**: Creates negative joint angle change

**Peak Values (Walking, normalized to body mass)**:
- Hip: 0.8-1.1 Nm/kg
- Knee: 0.4-0.6 Nm/kg
- Ankle: 1.2-1.6 Nm/kg

---

## 5. Task Classification System

### Three-Level Hierarchy

#### Level 1: Task (Biomechanical Category)
Primary activity classification:
- `level_walking` - Walking on level ground
- `incline_walking` - Walking uphill
- `decline_walking` - Walking downhill
- `stair_ascent` - Walking up stairs
- `stair_descent` - Walking down stairs
- `run` - Running
- `sit_to_stand` - Rising from chair
- `stand_to_sit` - Sitting down
- `jump` - Jumping activities
- `squats` - Squatting motion

#### Level 2: Task ID (Primary Parameter)
Specific variant with main parameter:
- Walking: `level`, `incline_5deg`, `incline_10deg`, `decline_5deg`
- Stairs: `stair_ascent`, `stair_descent`
- Other: Task-specific identifiers

#### Level 3: Task Info (Detailed Metadata)
Key-value pairs in format: `"key1:value1,key2:value2"`

**Common Keys**:
- `speed_m_s` - Movement speed (m/s)
- `incline_deg` - Incline angle (degrees)
- `treadmill` - Boolean (true/false)
- `steps` - Number of stairs
- `height_m` - Step/platform height

**Examples**:
```
"speed_m_s:1.2,treadmill:true"
"incline_deg:10,speed_m_s:1.0,treadmill:true"
"steps:8,height_m:0.15,speed_m_s:0.8"
```

---

## 6. Phase Calculation & Alignment

### Phase Normalization

Phase-indexed data uses exactly **150 points per gait cycle**:
- **0%** (index 0): Initial contact (heel strike)
- **50%** (index 75): Approximate opposite heel strike
- **100%** (index 149): Next ipsilateral heel strike

### Index to Phase Conversion

```python
phase_percent = (point_index / 149) * 100
point_index = int(phase_percent * 1.49)
```

### Contralateral Offset

Contralateral data is shifted by 50% of the cycle:
```python
phase_contra = (phase_ipsi + 50) % 100
index_contra = (index_ipsi + 75) % 150
```

---

## 7. Validation Requirements

### Data Quality Checks

#### Structural Validation
- ✓ Exactly 150 points per cycle (phase data)
- ✓ Phase values 0.0 to 100.0
- ✓ No gaps in phase progression
- ✓ Required columns present
- ✓ Consistent subject/task naming

#### Biomechanical Validation
- ✓ Joint angles within anatomical limits
- ✓ Segment angle relationships mathematically consistent
- ✓ Forces and moments within typical ranges
- ✓ No sudden discontinuities (>3σ jumps)

### Validation Ranges

Validation ranges are task-specific and defined in YAML:

```yaml
tasks:
  level_walking:
    phases:
      0:  # Heel strike
        knee_flexion_angle_ipsi_rad:
          min: -0.05
          max: 0.3
      50:  # Mid-stance
        knee_flexion_angle_ipsi_rad:
          min: -0.1
          max: 0.2
```

---

## 8. Implementation Examples

### Loading Data (Python)

```python
from user_libs.python.locomotion_data import LocomotionData

# Load phase-indexed data
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get cycles for a subject/task
cycles_3d, features = data.get_cycles(
    subject='SUB01',
    task='level_walking',
    features=['knee_flexion_angle_ipsi_rad', 'hip_flexion_moment_ipsi_Nm']
)

# Calculate mean patterns
mean_patterns = data.get_mean_patterns('SUB01', 'level_walking')
```

### Converting Units

```python
import numpy as np

# Degrees to radians
angle_rad = angle_deg * np.pi / 180

# Radians to degrees  
angle_deg = angle_rad * 180 / np.pi

# Phase index to percent
phase_percent = index / 1.49

# Percent to phase index
index = int(phase_percent * 1.49)
```

### Data Conversion Checklist

- [ ] Identify source coordinate system
- [ ] Map variable names to standard
- [ ] Convert units (degrees → radians)
- [ ] Detect gait events (heel strikes)
- [ ] Interpolate to 150 points per cycle
- [ ] Apply ipsi/contra naming
- [ ] Add required metadata columns
- [ ] Validate against ranges
- [ ] Generate validation report

---

## 9. Common Pitfalls & Solutions

| Issue | Solution |
|-------|----------|
| **Negative knee angles** | OpenSim uses 0° = full extension, not anatomical position |
| **Phase alignment** | Ensure heel strike = 0%, not toe-off |
| **Unit confusion** | All angles in radians, all moments in Nm |
| **Missing contra data** | Generate from ipsi with 50% phase shift |
| **Coordinate flips** | Check sign conventions match OpenSim |

---

## 10. References

1. **OpenSim Documentation**: [Coordinate Systems and Joint Definitions](https://simtk-confluence.stanford.edu/display/OpenSim/Coordinate+Systems)
2. **Winter, D.A.** (2009). Biomechanics and Motor Control of Human Movement (4th ed.)
3. **Perry, J. & Burnfield, J.** (2010). Gait Analysis: Normal and Pathological Function
4. **ISB Recommendations**: Wu et al. (2002, 2005) - Joint coordinate systems

---

*Last Updated: 2024 | Version: 2.0 | Locomotion Data Standardization Framework*