# Gtech 2021 Dataset

## **A comprehensive, open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions**

## Overview

**Brief Description**: Comprehensive open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions. Contains 3-dimensional biomechanical and wearable sensor data from 22 able-bodied adults with joint-level kinematics, moments, and powers processed using OpenSim inverse dynamics.

**Collection Year**: 2018-2019  
**Dataset Size**: ~2.5 GB (parquet format)  
**License**: Creative Commons Attribution 4.0 (CC-BY 4.0)

**Institution**: Georgia Institute of Technology, George W. Woodruff School of Mechanical Engineering and Institute of Robotics and Intelligent Machines

**Principal Investigators**: Jonathan Camargo, Aditya Ramanathan, Will Flanagan, Aaron Young (EPIC Lab - Exoskeleton and Prosthetic Intelligent Controls Lab)

## Citation Information

### Primary Citation
```
@article{CAMARGO2021110320,
  title = {A comprehensive, open-source dataset of lower limb biomechanics in multiple conditions of stairs, ramps, and level-ground ambulation and transitions},
  journal = {Journal of Biomechanics},
  volume = {119},
  pages = {110320},
  year = {2021},
  issn = {0021-9290},
  doi = {https://doi.org/10.1016/j.jbiomech.2021.110320},
  author = {Jonathan Camargo and Aditya Ramanathan and Will Flanagan and Aaron Young},
  keywords = {Locomotion biomechanics, stairs, ramps, level-ground, treadmill, wearable sensors, open dataset}
}
```

### Associated Publications
- Published online: February 20, 2021
- DOI: https://doi.org/10.1016/j.jbiomech.2021.110320
- Dataset hosted on Mendeley Data (3 parts due to size):
  - Part 1: https://doi.org/10.17632/x78gzbp7n4.3
  - Part 2: https://doi.org/10.17632/gwtkr3hv7r.3
  - Part 3: https://doi.org/10.17632/svzfpxr3fy.3

### Acknowledgments
This comprehensive dataset offers a source of locomotion information for applications in locomotion recognition, developments in robotic assistive devices, and improvement of biomimetic controllers that better adapt to terrain conditions.

## Dataset Contents

### Subjects
- **Total Subjects**: 22 (Gtech_2021_AB06 through Gtech_2021_AB29, excluding AB16)
- **Subject ID Format**: `Gtech_2021_XX##` (Dataset: Gtech 2021, Population: Able-bodied)
- **Demographics**:
  - Age Range: 19.0 - 33.0 years
  - Sex Distribution: 13 males, 9 females
  - Height Range: 1520 - 1800 mm
  - Weight Range: 52.2 - 96.2 kg
  - Mean Age: 21.6 ± 3.6 years
  - Mean Weight: 68.5 ± 11.3 kg
  - Mean Height: 1705 ± 74 mm
- **Population**: Able-bodied

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| decline_walking | Decline Walking | Continuous | Ramp descent at 6 inclinations: 5.2°, 7.8°, 9.2°, 11°, 12.4°, 18° | Includes transitions between level and ramp |
| incline_walking | Incline Walking | Continuous | Ramp ascent at 6 inclinations: 5.2°, 7.8°, 9.2°, 11°, 12.4°, 18° | Includes transitions between level and ramp |
| level_walking | Level Walking | Continuous | 3 speeds: slow (~0.8 m/s), normal (~1.0 m/s), fast (~1.2 m/s) | Includes both clockwise and counterclockwise circuits |
| stair_ascent | Stair Ascent | Continuous | 4 step heights: 10.16 cm (4"), 12.70 cm (5"), 15.24 cm (6"), 17.78 cm (7") | Based on ADA guidelines |
| stair_descent | Stair Descent | Continuous | 4 step heights: 10.16 cm (4"), 12.70 cm (5"), 15.24 cm (6"), 17.78 cm (7") | Based on ADA guidelines |

### Data Columns (Standardized Format)
- **Variables**: 17 primary biomechanical features (expandable to 45+ with all planes)
- **Format**: Phase-indexed (150 points per gait cycle)
- **File**: `converted_datasets/gtech_2021_phase.parquet`
- **Units**: 
  - Angles: radians
  - Moments: Nm/kg (normalized by body weight)
  - Powers: W/kg (normalized by body weight)
  - Coordinate System: Right-hand rule, Z-up

## Data Collection Methods

### Motion Capture System
- **System**: Vicon Motion Capture (16 T40-S cameras)
- **Sampling Rate**: 200 Hz
- **Marker Protocol**: Modified Plug-in Gait with additional tracking markers
- **Force Plates**: Bertec split-belt instrumented treadmill (1000 Hz)

### Wearable Sensors
- **IMUs**: 7 Delsys Trigno sensors (lower limb segments)
- **EMG**: 7 channels (major lower limb muscles)
- **Goniometers**: Knee and ankle joint angle sensors
- **Sampling Rate**: 2000 Hz (EMG), 150 Hz (IMU)

### Processing Pipeline
- **Inverse Dynamics**: OpenSim 4.0 with gait2392 model
- **Filtering**: 4th order Butterworth (6 Hz cutoff for kinematics, 25 Hz for kinetics)
- **Cycle Detection**: Heel strike events from force plates
- **Phase Normalization**: Cubic spline interpolation to 150 points

## Laboratory Facilities

### EPIC Lab Terrain Park
- Unique configurable terrain environment
- Multiple stair heights (4"-7" rise)
- Adjustable ramp (0-18° incline/decline)
- Level ground walking circuit
- Force plate instrumentation throughout
- Full motion capture coverage

## Contact Information
- **Dataset Curator**: Jonathan Camargo, PhD Candidate (at time of publication)
- **Lab Website**: https://www.epic.gatech.edu/
- **Lab Email**: Contact through lab website
- **Technical Support**: EPIC Lab at Georgia Tech
- **Data Access**: https://www.epic.gatech.edu/opensource-biomechanics-camargo-et-al/

## Usage

```python
from user_libs.python.locomotion_data import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/gtech_2021_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

## Data Validation

<div class="validation-summary" markdown>

### 📊 Validation Status

**Validation Configuration:**
- **Ranges File**: `default_ranges.yaml`
- **SHA256**: `76ab6a11...` (first 8 chars)
- **Archived Copy**: [`gtech_2021_phase_2025-08-07_220959_ranges.yaml`](validation_archives/gtech_2021_phase_2025-08-07_220959_ranges.yaml)

| Metric | Value | Status |
|--------|-------|--------|
| **Overall Status** | 99.7% Valid | ✅ PASSED |
| **Phase Structure** | 150 points/cycle | ✅ Valid |
| **Tasks Validated** | 5 tasks | ✅ Complete |
| **Total Checks** | 530,016 | - |
| **Violations** | 1,554 | ⚠️ Present |

### 📈 Task-Specific Validation

#### Decline Walking
![Decline Walking](validation_plots/gtech_2021_phase_decline_walking_all_features_validation.png)
*19 sagittal features validated*

**Subject Failure Distribution:**
![Decline Walking Subject Failures](validation_plots/gtech_2021_phase_decline_walking_subject_failures.png)

#### Incline Walking
![Incline Walking](validation_plots/gtech_2021_phase_incline_walking_all_features_validation.png)
*19 sagittal features validated*

**Subject Failure Distribution:**
![Incline Walking Subject Failures](validation_plots/gtech_2021_phase_incline_walking_subject_failures.png)

#### Level Walking
![Level Walking](validation_plots/gtech_2021_phase_level_walking_all_features_validation.png)
*19 sagittal features validated*

**Subject Failure Distribution:**
![Level Walking Subject Failures](validation_plots/gtech_2021_phase_level_walking_subject_failures.png)

#### Stair Ascent
![Stair Ascent](validation_plots/gtech_2021_phase_stair_ascent_all_features_validation.png)
*19 sagittal features validated*

**Subject Failure Distribution:**
![Stair Ascent Subject Failures](validation_plots/gtech_2021_phase_stair_ascent_subject_failures.png)

#### Stair Descent
![Stair Descent](validation_plots/gtech_2021_phase_stair_descent_all_features_validation.png)
*19 sagittal features validated*

**Subject Failure Distribution:**
![Stair Descent Subject Failures](validation_plots/gtech_2021_phase_stair_descent_subject_failures.png)

</div>

**Last Validated**: 2025-08-07 22:09:59

---
*Last Updated: August 2025*