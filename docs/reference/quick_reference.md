# LocoHub Quick Reference

**Print-friendly cheat sheet for daily use**

---

## 📐 Coordinate System

```
Y↑ (Superior)    X→ (Anterior)    Z↓ (Right)
```
**Right-hand rule** for positive rotations

---

## 📊 Data Formats

| **Phase-Indexed** | **Time-Indexed** |
|-------------------|------------------|
| `*_phase.parquet` | `*_time.parquet` |
| 150 points/cycle | Variable samples |
| Phase: 0-100% | Time: seconds |
| For averaging | For raw analysis |

---

## 🔤 Variable Names (Copy-Ready)

### Most Common - Ipsilateral

#### Kinematics
```
hip_flexion_angle_ipsi_rad
knee_flexion_angle_ipsi_rad
ankle_dorsiflexion_angle_ipsi_rad
```

#### Kinetics
```
hip_flexion_moment_ipsi_Nm
knee_flexion_moment_ipsi_Nm
ankle_dorsiflexion_moment_ipsi_Nm
```

#### Segment Angles
```
pelvis_sagittal_angle_rad
trunk_sagittal_angle_rad
thigh_sagittal_angle_ipsi_rad
shank_sagittal_angle_ipsi_rad
foot_sagittal_angle_ipsi_rad
```

---

## ➕➖ Sign Conventions

| **Joint** | **Motion** | **Positive (+)** | **Zero (0)** |
|-----------|------------|------------------|--------------|
| **Hip** | Flexion | Thigh forward | Vertical |
| **Knee** | Flexion | Heel to buttocks | Full extension |
| **Ankle** | Dorsiflexion | Toes up | 90° foot-shank |
| **Pelvis** | Sagittal | Anterior tilt | Neutral |

---

## 🔄 Unit Conversions

```python
# Degrees ↔ Radians
rad = deg * π/180 = deg * 0.01745
deg = rad * 180/π = rad * 57.296

# Phase conversions
percent = index / 1.49
index = int(percent * 1.49)

# Contralateral offset
phase_contra = (phase_ipsi + 50) % 100
index_contra = (index_ipsi + 75) % 150
```

---

## 📏 Typical Ranges (Walking)

### Joint Angles (radians)

| **Joint** | **Min** | **Max** | **(degrees)** |
|-----------|---------|---------|---------------|
| Hip Flexion | -0.35 | 0.52 | -20° to 30° |
| Knee Flexion | -0.05 | 1.05 | -3° to 60° |
| Ankle Dorsiflex | -0.44 | 0.35 | -25° to 20° |

### Joint Moments (Nm/kg)

| **Joint** | **Typical Peak** |
|-----------|------------------|
| Hip | 0.8 - 1.1 |
| Knee | 0.4 - 0.6 |
| Ankle | 1.2 - 1.6 |

### Ground Reaction Forces (× Body Weight)

| **Direction** | **Walking** | **Running** |
|---------------|-------------|-------------|
| Vertical | 1.0 - 1.2 | 2.0 - 2.9 |
| Anterior-Post | ±0.2 | ±0.5 |
| Medial-Lateral | ±0.05 | ±0.1 |

---

## 📝 Required Columns

### All Datasets
- `subject` - Subject ID
- `task` - Activity type
- `task_id` - Specific variant
- `task_info` - Metadata string
- `step` - Cycle number

### Phase Data Only
- `phase_ipsi` - 0-100%

### Time Data Only
- `time_s` - Seconds

---

## 🏷️ Task Classification

### Level 1: Task
`level_walking`, `incline_walking`, `decline_walking`, `stair_ascent`, `stair_descent`, `run`, `sit_to_stand`, `jump`, `squats`

### Level 2: Task ID
`level`, `incline_5deg`, `incline_10deg`, `decline_5deg`, `stair_ascent`, `stair_descent`

### Level 3: Task Info
`"speed_m_s:1.2,treadmill:true,incline_deg:10"`

---

## 🐍 Python Quick Start

```python
from user_libs.python.locomotion_data import LocomotionData

# Load data
data = LocomotionData('dataset_phase.parquet')

# Get cycles
cycles, features = data.get_cycles(
    subject='SUB01',
    task='level_walking'
)

# Mean patterns
means = data.get_mean_patterns('SUB01', 'level_walking')

# Plot
data.plot_phase_patterns(
    'SUB01', 'level_walking',
    ['knee_flexion_angle_ipsi_rad']
)
```

---

## ⚠️ Common Issues

| **Problem** | **Solution** |
|-------------|--------------|
| Negative knee angles | OpenSim: 0° = full extension |
| Wrong phase alignment | 0% = heel strike, not toe-off |
| Unit errors | Use radians, not degrees |
| Missing contra data | Generate from ipsi + 50% phase offset |

---

## 🔍 Validation Checks

✓ 150 points per cycle  
✓ Phase: 0-100%  
✓ Angles in radians  
✓ Required columns present  
✓ Within anatomical limits  

---

## 👥 Impaired Population Tasks

### Task Naming Quick Reference

| **Population** | **Suffix** | **Example** |
|---------------|-----------|------------|
| Stroke | `_stroke` | `level_walking_stroke` |
| Amputee (TFA) | `_tfa` | `incline_walking_tfa` |
| Amputee (TTA) | `_tta` | `decline_walking_tta` |
| Parkinson's | `_pd` | `stair_ascent_pd` |
| SCI | `_sci` | `level_walking_sci` |
| Cerebral Palsy | `_cp` | `level_walking_cp` |

### Common Task Combinations

```python
# Standard tasks (when subject ID has population code)
"level_walking"      # STUDY_CVA01 implies stroke
"incline_walking"    # STUDY_TFA02 implies amputee

# Explicit population tasks (when needed)
"level_walking_stroke"
"incline_walking_amputee"
"stair_ascent_pd"
"level_walking_sci"
```

### Population Metadata Examples

```python
# Stroke
"affected_side:left,FAC_score:5,assistive_device:cane"

# Amputee
"prosthetic_type:C-leg,K_level:3,amputation_side:right"

# Parkinson's
"medication_state:ON,H_Y_stage:2,UPDRS_motor:24"
```

---

## 📚 Key References

- **Coordinate System**: X=Anterior, Y=Superior, Z=Right
- **Phase Points**: 0=heel strike, 50≈opposite heel, 100=next heel
- **Ipsi/Contra**: Ipsi=reference leg, Contra=opposite leg

---

*Locomotion Data Standard v2.0 | Quick Reference*