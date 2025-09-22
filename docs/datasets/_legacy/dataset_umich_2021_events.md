# Umich 2021 Events Dataset

## Overview

**Brief Description**: [TODO: Add comprehensive description of dataset purpose and scope]

**Collection Year**: [TODO: Add year(s) of data collection]

**Institution**: [TODO: Add institution name and department]

**Principal Investigators**: [TODO: Add PI names and labs]

## Citation Information

### Primary Citation
```
[TODO: Add primary citation in standard format]
```

### Associated Publications
[TODO: Add related publications if any]

### Acknowledgments
[TODO: Add funding sources and acknowledgments]

## Dataset Contents

### Subjects
- **Total Subjects**: 10 (ST21_XX01 - ST21_XX10)
- **Subject ID Format**: `ST21_XX##` (Dataset: Umich 2021 Events, Population: )
- **Demographics**:
  - Age Range: [TODO: Add age range]
  - Sex Distribution: [TODO: Add M/F distribution]
  - Height Range: [TODO: Add height range in mm]
  - Weight Range: [TODO: Add weight range in kg]
  - Mean Age: [TODO: Add mean age]
  - Mean Weight: [TODO: Add mean weight]
  - Mean Height: [TODO: Add mean height]
- **Population**: 

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| decline_walking | Decline Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| incline_walking | Incline Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| level_walking | Level Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| run | Run | Continuous | [TODO: Add conditions] | [TODO: Add notes] |

### Data Columns (Standardized Format)
- **Variables**: 59 columns including biomechanical features
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/umich_2021_events_phase.parquet`
- **Units**: All angles in radians, moments normalized by body weight (Nm/kg)

## Contact Information
- **Dataset Curator**: [TODO: Add curator name and title]
- **Lab Website**: [TODO: Add lab website URL]
- **Lab Email**: [TODO: Add contact email]
- **Technical Support**: [TODO: Add support contact]

## Usage

```python
from user_libs.python.locomotion_data import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/umich_2021_events_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

## Data Validation

<div class="validation-summary" markdown>

### 📊 Validation Status

**Validation Configuration:**
- **Ranges File**: `default_ranges.yaml`
- **SHA256**: `bbf1f9c7...` (first 8 chars)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Status** | 99.6% Valid | ✅ PASSED |
| **Phase Structure** | 150 points/cycle | ✅ Valid |
| **Tasks Validated** | 4 tasks | ✅ Complete |
| **Total Checks** | 541,824 | - |
| **Violations** | 2,116 | ⚠️ Present |

### 🔄 Velocity Consistency Validation

Validates that velocities match angles using the chain rule: `dθ/dt = (dθ/dφ) × (dφ/dt)`

| Velocity Variable | Status | Mean Error (rad/s) | Max Error (rad/s) | Strides Checked |
|-------------------|--------|-------------------|-------------------|-----------------|
| ankle dorsiflexion velocity contra (rad/s) | ❌ Fail | 0.831 | 1.719 | 22/22 |
| ankle dorsiflexion velocity ipsi (rad/s) | ❌ Fail | 0.848 | 1.795 | 22/22 |
| foot sagittal velocity contra (rad/s) | ❌ Fail | 1.945 | 3.116 | 22/22 |
| foot sagittal velocity ipsi (rad/s) | ❌ Fail | 1.941 | 3.012 | 22/22 |
| hip flexion velocity contra (rad/s) | ❌ Fail | 0.991 | 1.603 | 22/22 |
| hip flexion velocity ipsi (rad/s) | ❌ Fail | 0.957 | 1.601 | 22/22 |
| knee flexion velocity contra (rad/s) | ❌ Fail | 4.573 | 7.430 | 22/22 |
| knee flexion velocity ipsi (rad/s) | ❌ Fail | 4.527 | 7.165 | 22/22 |
| pelvis frontal velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| pelvis sagittal velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| pelvis transverse velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| shank sagittal velocity contra (rad/s) | ❌ Fail | 1.847 | 3.927 | 22/22 |
| shank sagittal velocity ipsi (rad/s) | ❌ Fail | 1.562 | 2.412 | 22/22 |
| thigh sagittal velocity contra (rad/s) | ❌ Fail | 1.804 | 5.303 | 22/22 |
| thigh sagittal velocity ipsi (rad/s) | ❌ Fail | 1.009 | 1.635 | 22/22 |
| trunk frontal velocity (rad/s) | ⚠️ N/A | - | - | Angle column trunk_frontal_angle_rad not found |
| trunk sagittal velocity (rad/s) | ⚠️ N/A | - | - | Angle column trunk_sagittal_angle_rad not found |
| trunk transverse velocity (rad/s) | ⚠️ N/A | - | - | Angle column trunk_transverse_angle_rad not found |

**Legend**:
- ✅ **Pass**: Mean error < 0.5 rad/s between stored and calculated velocities
- ❌ **Fail**: Mean error ≥ 0.5 rad/s (velocities inconsistent with angles)
- 🔄 **Calculated**: No stored velocities; values computed from angles
- ⚠️ **N/A**: Corresponding angle data not available

### 📈 Task-Specific Validation

#### Decline Walking
![Decline Walking](../validation_plots/umich_2021_events_phase_decline_walking_all_features_validation.png)
*34 sagittal features validated*

**Subject Failure Distribution:**
![Decline Walking Subject Failures](../validation_plots/umich_2021_events_phase_decline_walking_subject_failures.png)

#### Incline Walking
![Incline Walking](../validation_plots/umich_2021_events_phase_incline_walking_all_features_validation.png)
*34 sagittal features validated*

**Subject Failure Distribution:**
![Incline Walking Subject Failures](../validation_plots/umich_2021_events_phase_incline_walking_subject_failures.png)

#### Level Walking
![Level Walking](../validation_plots/umich_2021_events_phase_level_walking_all_features_validation.png)
*34 sagittal features validated*

**Subject Failure Distribution:**
![Level Walking Subject Failures](../validation_plots/umich_2021_events_phase_level_walking_subject_failures.png)

#### Run
![Run](../validation_plots/umich_2021_events_phase_run_all_features_validation.png)
*34 sagittal features validated*

**Subject Failure Distribution:**
![Run Subject Failures](../validation_plots/umich_2021_events_phase_run_subject_failures.png)

</div>

**Last Validated**: 2025-08-12 09:53:47

---
*Last Updated: August 2025*
