# Umich 2021 Filtered Dataset

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
- **Total Subjects**: 10 (UMF21_XX01 - UMF21_XX10)
- **Subject ID Format**: `UMF21_XX##` (Dataset: Umich 2021 Filtered, Population: )
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
| sit_to_stand | Sit To Stand | Continuous | [TODO: Add conditions] | [TODO: Add notes] |
| stand_to_sit | Stand To Sit | Continuous | [TODO: Add conditions] | [TODO: Add notes] |

### Data Columns (Standardized Format)
- **Variables**: 78 columns including biomechanical features
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/umich_2021_filtered_phase.parquet`
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
data = LocomotionData('converted_datasets/umich_2021_filtered_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```


## Data Validation

<div class="validation-summary" markdown>

### 📊 Validation Status

**Validation Configuration:**
- **Ranges File**: `default_ranges.yaml`
- **SHA256**: `c232030c...` (first 8 chars)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Status** | 100.0% Valid | ✅ PASSED |
| **Phase Structure** | 150 points/cycle | ✅ Valid |
| **Tasks Validated** | 6 tasks | ✅ Complete |
| **Total Checks** | 513,504 | - |
| **Violations** | 0 | ✅ None |

### 🔄 Velocity Consistency Validation

Validates that velocities match angles using the chain rule: `dθ/dt = (dθ/dφ) × (dφ/dt)`

| Velocity Variable | Status | Mean Error (rad/s) | Max Error (rad/s) | Strides Checked |
|-------------------|--------|-------------------|-------------------|-----------------|
| ankle dorsiflexion velocity contra (rad/s) | ❌ Fail | 0.773 | 1.747 | 27/27 |
| ankle dorsiflexion velocity ipsi (rad/s) | ❌ Fail | 0.796 | 1.831 | 27/27 |
| foot sagittal velocity contra (rad/s) | ❌ Fail | 1.788 | 3.116 | 27/27 |
| foot sagittal velocity ipsi (rad/s) | ❌ Fail | 1.785 | 3.012 | 27/27 |
| hip flexion velocity contra (rad/s) | ❌ Fail | 0.965 | 1.627 | 27/27 |
| hip flexion velocity ipsi (rad/s) | ❌ Fail | 0.936 | 1.627 | 27/27 |
| knee flexion velocity contra (rad/s) | ❌ Fail | 1.621 | 2.879 | 27/27 |
| knee flexion velocity ipsi (rad/s) | ❌ Fail | 1.604 | 2.777 | 27/27 |
| pelvis frontal velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| pelvis sagittal velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| pelvis transverse velocity (rad/s) | 🔄 Calculated | - | - | No stored velocities to compare |
| shank sagittal velocity contra (rad/s) | ❌ Fail | 1.664 | 3.927 | 27/27 |
| shank sagittal velocity ipsi (rad/s) | ❌ Fail | 1.426 | 2.412 | 27/27 |
| thigh sagittal velocity contra (rad/s) | ❌ Fail | 1.617 | 5.303 | 27/27 |
| thigh sagittal velocity ipsi (rad/s) | ❌ Fail | 0.969 | 1.635 | 27/27 |
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
![Decline Walking](../validation_plots/umich_2021_phase_filtered_decline_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Decline Walking Subject Failures](../validation_plots/umich_2021_phase_filtered_decline_walking_subject_failures.png)

#### Incline Walking
![Incline Walking](../validation_plots/umich_2021_phase_filtered_incline_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Incline Walking Subject Failures](../validation_plots/umich_2021_phase_filtered_incline_walking_subject_failures.png)

#### Level Walking
![Level Walking](../validation_plots/umich_2021_phase_filtered_level_walking_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Level Walking Subject Failures](../validation_plots/umich_2021_phase_filtered_level_walking_subject_failures.png)

#### Run
![Run](../validation_plots/umich_2021_phase_filtered_run_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Run Subject Failures](../validation_plots/umich_2021_phase_filtered_run_subject_failures.png)

#### Sit To Stand
![Sit To Stand](../validation_plots/umich_2021_phase_filtered_sit_to_stand_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Sit To Stand Subject Failures](../validation_plots/umich_2021_phase_filtered_sit_to_stand_subject_failures.png)

#### Stand To Sit
![Stand To Sit](../validation_plots/umich_2021_phase_filtered_stand_to_sit_all_features_validation.png)
*46 sagittal features validated*

**Subject Failure Distribution:**
![Stand To Sit Subject Failures](../validation_plots/umich_2021_phase_filtered_stand_to_sit_subject_failures.png)

</div>

**Last Validated**: 2025-08-20 09:43:07
---
*Last Updated: August 2025*
