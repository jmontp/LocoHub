# Gtech 2021 Filtered Dataset

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
- **Total Subjects**: 15 (GTF21_AB01 - GTF21_AB15)
- **Subject ID Format**: `GTF21_AB##` (Dataset: Gtech 2021 Filtered, Population: Able-bodied)
- **Demographics**:
  - Age Range: [TODO: Add age range]
  - Sex Distribution: [TODO: Add M/F distribution]
  - Height Range: [TODO: Add height range in mm]
  - Weight Range: [TODO: Add weight range in kg]
  - Mean Age: [TODO: Add mean age]
  - Mean Weight: [TODO: Add mean weight]
  - Mean Height: [TODO: Add mean height]
- **Population**: Able-bodied

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| decline_walking | Decline Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| incline_walking | Incline Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| level_walking | Level Walking | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| stair_ascent | Stair Ascent | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| stair_descent | Stair Descent | Continuous | [TODO: Add conditions] | [TODO: Add notes] |

### Data Columns (Standardized Format)
- **Variables**: 46 columns including biomechanical features
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/gtech_2021_filtered_phase.parquet`
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
data = LocomotionData('converted_datasets/gtech_2021_filtered_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```


## Data Validation

<div class="validation-summary" markdown>

### 📊 Validation Status

**Validation Configuration:**
- **Ranges File**: `default_ranges.yaml`
- **SHA256**: `c232030c...` (first 8 chars)
- **Archived Copy**: [`gtech_2021_phase_filtered_2025-08-20_093801_ranges.yaml`](../validation_archives/gtech_2021_phase_filtered_2025-08-20_093801_ranges.yaml)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Status** | 100.0% Valid | ✅ PASSED |
| **Phase Structure** | 150 points/cycle | ✅ Valid |
| **Tasks Validated** | 5 tasks | ✅ Complete |
| **Total Checks** | 407,424 | - |
| **Violations** | 0 | ✅ None |

### 🔄 Velocity Consistency Validation

Validates that velocities match angles using the chain rule: `dθ/dt = (dθ/dφ) × (dφ/dt)`

| Velocity Variable | Status | Mean Error (rad/s) | Max Error (rad/s) | Strides Checked |
|-------------------|--------|-------------------|-------------------|-----------------|
| ankle dorsiflexion velocity contra (rad/s) | ❌ Fail | 0.855 | 1.465 | 88/88 |
| ankle dorsiflexion velocity ipsi (rad/s) | ❌ Fail | 0.877 | 1.415 | 88/88 |
| foot sagittal velocity contra (rad/s) | ❌ Fail | 1.955 | 2.496 | 88/88 |
| foot sagittal velocity ipsi (rad/s) | ❌ Fail | 1.987 | 2.548 | 88/88 |
| hip flexion velocity contra (rad/s) | ❌ Fail | 1.112 | 1.403 | 88/88 |
| hip flexion velocity ipsi (rad/s) | ❌ Fail | 1.108 | 1.404 | 88/88 |
| knee flexion velocity contra (rad/s) | ❌ Fail | 1.656 | 2.123 | 88/88 |
| knee flexion velocity ipsi (rad/s) | ❌ Fail | 1.673 | 2.041 | 88/88 |
| pelvis frontal velocity (rad/s) | ⚠️ N/A | - | - | Angle column pelvis_frontal_angle_rad not found |
| pelvis sagittal velocity (rad/s) | ✅ Pass | 0.296 | 0.465 | 88/88 |
| pelvis transverse velocity (rad/s) | ⚠️ N/A | - | - | Angle column pelvis_transverse_angle_rad not found |
| shank sagittal velocity contra (rad/s) | ❌ Fail | 1.592 | 1.970 | 88/88 |
| shank sagittal velocity ipsi (rad/s) | ❌ Fail | 1.594 | 1.870 | 88/88 |
| thigh sagittal velocity contra (rad/s) | ❌ Fail | 1.141 | 1.453 | 88/88 |
| thigh sagittal velocity ipsi (rad/s) | ❌ Fail | 1.199 | 1.619 | 88/88 |
| trunk frontal velocity (rad/s) | ⚠️ N/A | - | - | Angle column trunk_frontal_angle_rad not found |
| trunk sagittal velocity (rad/s) | ✅ Pass | 0.296 | 0.465 | 88/88 |
| trunk transverse velocity (rad/s) | ⚠️ N/A | - | - | Angle column trunk_transverse_angle_rad not found |

**Legend**:
- ✅ **Pass**: Mean error < 0.5 rad/s between stored and calculated velocities
- ❌ **Fail**: Mean error ≥ 0.5 rad/s (velocities inconsistent with angles)
- 🔄 **Calculated**: No stored velocities; values computed from angles
- ⚠️ **N/A**: Corresponding angle data not available

### 📈 Task-Specific Validation

#### Decline Walking
![Decline Walking](../validation_plots/gtech_2021_phase_filtered_decline_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Decline Walking Subject Failures](../validation_plots/gtech_2021_phase_filtered_decline_walking_subject_failures.png)

#### Incline Walking
![Incline Walking](../validation_plots/gtech_2021_phase_filtered_incline_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Incline Walking Subject Failures](../validation_plots/gtech_2021_phase_filtered_incline_walking_subject_failures.png)

#### Level Walking
![Level Walking](../validation_plots/gtech_2021_phase_filtered_level_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Level Walking Subject Failures](../validation_plots/gtech_2021_phase_filtered_level_walking_subject_failures.png)

#### Stair Ascent
![Stair Ascent](../validation_plots/gtech_2021_phase_filtered_stair_ascent_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Stair Ascent Subject Failures](../validation_plots/gtech_2021_phase_filtered_stair_ascent_subject_failures.png)

#### Stair Descent
![Stair Descent](../validation_plots/gtech_2021_phase_filtered_stair_descent_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Stair Descent Subject Failures](../validation_plots/gtech_2021_phase_filtered_stair_descent_subject_failures.png)

</div>

**Last Validated**: 2025-08-20 09:38:01
---
*Last Updated: August 2025*
