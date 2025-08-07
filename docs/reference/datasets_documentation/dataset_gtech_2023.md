# Georgia Tech 2023 Multi-Activity Dataset

## Overview
**Brief Description**: Comprehensive motion capture dataset featuring diverse locomotion and daily activities including walking, running, stairs, sports movements, and functional tasks. This dataset captures both cyclic and non-cyclic activities crucial for developing adaptive prosthetics and exoskeletons.

**Collection Year**: 2023

**Institution**: Georgia Institute of Technology, Woodruff School of Mechanical Engineering and Institute of Robotics and Intelligent Machines

**Principal Investigators**: Aaron Young, Ph.D. (EPIC Lab - Exoskeleton and Prosthetic Intelligent Controls Laboratory)

## Citation Information

### Primary Citation
```
Scherpereel, K., Molinaro, D., Inan, O., Shepherd, M., & Young, A. (2023). 
A human lower-limb biomechanics and wearable sensors dataset during cyclic and non-cyclic activities. 
Scientific Data, 10, 917. https://doi.org/10.1038/s41597-023-02341-6
```

### Associated Publications
1. Young, A. et al. (2024). "Task-Agnostic Exoskeleton Control via Biological Joint Moment Estimation." 
   Nature, 635, 337-344.
2. EPIC Lab Open-Source Data & Models: https://www.epic.gatech.edu/open-source-data-models/

### Acknowledgments
This research was supported by:
- NSF National Robotics Initiative (NRI) grants for machine learning in exoskeleton control
- DoD CDMRP funding for intent recognition systems in powered prostheses
- NIH New Investigator Award to Dr. Aaron Young

## Dataset Contents

### Subjects
- **Total Subjects**: 12 (AB01, AB02, AB03, AB05, AB06, AB07, AB08, AB09, AB10, AB11, AB12, AB13)
- **Demographics**:
  - Age Range: 18-35 years (healthy young adults)
  - Sex Distribution: Balanced male/female representation
  - Height Range: Approximately 1.60-1.90 m
  - Weight Range: 62.3-113.5 kg
  - Mean Weight: 76.95 kg
  - Inclusion Criteria: Healthy adults with no musculoskeletal or neurological impairments
  - Note: Subject AB04 excluded from dataset

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| level_walking | Level ground walking | Multiple trials | Various speeds | Treadmill |
| incline_walking | Incline walking | Multiple trials | 5° and 10° inclines | Up/down |
| stairs | Stair climbing | Multiple cycles | Standard stairs | Up/down |
| squats | Squatting | Multiple reps | With/without weight | Static |
| sit_to_stand | Sit-to-stand transitions | Multiple cycles | Chair height | Functional |
| curb_up | Stepping up curb | Multiple cycles | Street curb height | Overground |
| curb_down | Stepping down curb | Multiple cycles | Street curb height | Overground |

### Data Columns (Standardized Format)
- **Variables**: Comprehensive biomechanical features (kinematics, kinetics, segment angles)
- **Format**: Phase-indexed (150 points per gait cycle) for cyclic tasks
- **File**: `converted_datasets/gtech_2023_phase.parquet`
- **Units**: All angles in radians, moments in Nm, forces in N

## Data Collection Methods

### Motion Capture System
- **System**: Vicon Motion Capture System
- **Marker Set**: Full-body marker set (modified Plug-in Gait)
- **Sampling Rate**: 200 Hz (native)
- **Camera Count**: 12-16 cameras for full capture volume

### CAREN System
- **Facility**: Motek Computer-Aided Rehabilitation Environment (CAREN)
- **Components**: 10-camera Vicon system, 16-channel Delsys EMG, instrumented treadmill on 6-DOF Stewart platform
- **Display**: 180° projection screen for immersive environments
- **Software**: Motek D-Flow for real-time data integration

## Contact Information
- **Dataset Curator**: Aaron Young, Ph.D.
- **Lab Website**: https://www.epic.gatech.edu/
- **Lab Email**: epic-lab@gatech.edu
- **Technical Support**: Contact via lab email

## Funding Acknowledgment
This dataset was collected with support from:
- NSF National Robotics Initiative (NRI) for machine learning in robotic exoskeletons
- DoD Congressionally Directed Medical Research Programs (CDMRP) for powered prosthesis intent recognition
- NIH New Investigator Award to Dr. Aaron Young

## Lab Description
The Exoskeleton and Prosthetic Intelligent Controls (EPIC) Lab at Georgia Tech is devoted to the design and 
improvement of powered orthotic and prosthetic control systems. The lab combines machine learning, robotics, 
human biomechanics, and control systems to design wearable robots that improve community mobility for 
individuals with walking disability.

## Usage

```python
from user_libs.python.locomotion_data import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/gtech_2023_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

---
*Last Updated: January 2025*