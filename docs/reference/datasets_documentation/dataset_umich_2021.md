# UMich 2021 Dataset

## **The Effect of Walking Incline and Speed on Human Leg Kinematics, Kinetics, and EMG**

## Overview
**Brief Description**: Comprehensive treadmill-based locomotion dataset including walking at various speeds and inclines, running, and transitions between activities.

**Collection Year**: 2018-2021

**Institution**: University of Michigan, Department of Robotics, Mechanical Engineering, and Electrical and Computer Engineering

**Principal Investigators**: Robert D. Gregg IV, Ph.D. (Locomotor Control Systems Laboratory)

## Citation Information

### Primary Citation
```
Locomotor Control Systems Laboratory. (2021). University of Michigan Treadmill Locomotion Dataset. 
University of Michigan, Ann Arbor. [Contact lab for access]
```

### Associated Publications
1. Gregg, R.D. et al. "The Effect of Walking Incline and Speed on Human Leg Kinematics, Kinetics, and EMG" 
   IEEE DataPort (2018). https://ieee-dataport.org/open-access/effect-walking-incline-and-speed-human-leg-kinematics-kinetics-and-emg
2. Related publications available at: https://scholar.google.com/citations?user=hEypYOEAAAAJ&hl=en

### Acknowledgments
This research was supported by:
- NIH Director's New Innovator Award (2013) - $2.3 million over 5 years for phase-based control research
- NIH R01 Grant (2018) - $2.2 million for investigation of agile powered prosthetic leg control
- NIH R01 Grant (2021) - $1.7 million for design and control of modular powered orthoses

## Dataset Contents

### Subjects
- **Total Subjects**: 10 (UM21_AB01 - UM21_AB10)
- **Subject ID Format**: `UM21_AB##` (Dataset: UMich 2021, Population: Able-bodied)
- **Demographics**:
  - Age Range: 20-60 years
  - Sex Distribution: 5F/5M
  - Height Range: 1617-1900 mm
  - Weight Range: 53.7-87.0 kg
  - Mean Age: 30.4 years
  - Mean Weight: 74.63 kg
  - Mean Height: 1727.8 mm
- **Population**: All able-bodied (AB) healthy adults

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| level_walking | Level walking | Continuous | 0° (level) | Treadmill |
| incline_walking | Incline walking | Continuous | 5° incline | Treadmill |
| decline_walking | Decline walking | Continuous | -10° decline | Treadmill |

### Data Columns (Standardized Format)
- **Variables**: 45 biomechanical features (kinematics, kinetics, segment angles)
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/umich_2021_phase.parquet`
- **Units**: All angles in radians, moments normalized by body weight (Nm/kg)

## Contact Information
- **Dataset Curator**: Robert D. Gregg IV, Ph.D.
- **Lab Website**: https://gregg.engin.umich.edu/
- **Lab Email**: locolab@umich.edu
- **Technical Support**: Contact via lab email

## Funding Acknowledgment
This dataset was collected with support from:
- NIH Director's New Innovator Award (DP2HD080349)
- NIH R01 Grant for agile powered prosthetic legs (R01HD094772)
- Burroughs Wellcome Fund Career Award at the Scientific Interface ($500,000)

## Lab Description
The Locomotor Control Systems Laboratory is a highly interdisciplinary environment dedicated to scientific innovation, 
clinical translation, and individual career development. The lab develops high-performance control systems for robotic 
prostheses and orthoses to enable mobility and improve quality of life for persons with disabilities. The research 
approaches this needs-driven work from the perspective of dynamical systems and control theory, investigating and 
translating concepts from legged robotics into transformative solutions for physical rehabilitation.

Dr. Gregg's research interests include actuator design and control, nonlinear control theory, and biomechanics of 
human locomotion. He is most known for his works on bipedal locomotion control and wearable robotics, with research 
focusing on integrating human biomechanics insights into robot control algorithms to improve natural movement efficiency.

## Usage

```python
from user_libs.python.locomotion_data import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

## Data Validation

<div class="validation-summary" markdown>

### 📊 Validation Status

**Validation Configuration:**
- **Ranges File**: `default_ranges.yaml`
- **SHA256**: `137767ae...` (first 8 chars)
- **Archived Copy**: [`umich_2021_phase_2025-08-07_175552_ranges.yaml`](validation_archives/umich_2021_phase_2025-08-07_175552_ranges.yaml)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Status** | 99.7% Valid | ✅ PASSED |
| **Phase Structure** | 150 points/cycle | ✅ Valid |
| **Tasks Validated** | 3 tasks | ✅ Complete |
| **Total Checks** | 396,096 | - |
| **Violations** | 1,261 | ⚠️ Present |

### 📈 Task-Specific Validation

#### Decline Walking
![Decline Walking](validation_plots/umich_2021_phase_decline_walking_all_features_validation.png)
*19 sagittal features validated*

#### Incline Walking
![Incline Walking](validation_plots/umich_2021_phase_incline_walking_all_features_validation.png)
*19 sagittal features validated*

#### Level Walking
![Level Walking](validation_plots/umich_2021_phase_level_walking_all_features_validation.png)
*19 sagittal features validated*

</div>

**Last Validated**: 2025-08-07 17:55:52

---
*Last Updated: January 2025*