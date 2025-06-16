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
| normal_walk | Level ground walking | Multiple trials | Various speeds (0.6-2.5 m/s) | Treadmill |
| incline_walk | Incline walking | Multiple trials | 5° and 10° inclines | Up/down |
| stairs | Stair climbing | Multiple cycles | Standard stairs | Up/down |
| dynamic_walk | Variable speed walking | Continuous | Speed changes | Treadmill |
| walk_backward | Backward walking | Continuous | 1.0 m/s | Treadmill |
| weighted_walk | Walking with load | Continuous | 25 lbs weight | 1.0 m/s |
| side_shuffle | Lateral movement | Multiple cycles | Ipsilateral/contralateral | Overground |
| jump | Jumping | Multiple trials | Vertical jumps | Force plates |
| squats | Squatting | Multiple reps | With/without weight | Static |
| lunges | Forward/backward lunges | Multiple reps | Ipsilateral/contralateral legs | Overground |
| sit_to_stand | Sit-to-stand transitions | Multiple cycles | Chair height | Functional |
| ball_toss | Ball tossing | Multiple trials | Left/mid/right targets | Standing |
| curb_up | Stepping up curb | Multiple cycles | Street curb height | Overground |
| curb_down | Stepping down curb | Multiple cycles | Street curb height | Overground |
| cutting | Sharp turning while jogging | Multiple trials | Ipsilateral/contralateral | Overground |
| lift_weight | Weight lifting | Multiple trials | Weighted/unweighted bag | Functional |
| step_ups | Step-up exercise | Multiple cycles | Tall platform | Exercise |
| tire_run | High-knee jogging | Continuous | Toe running | Overground |
| turn_and_step | Turn and walk initiation | Multiple trials | Ipsilateral/contralateral turns | From standing |
| meander | Free-form slow walking | Continuous | Self-selected path | Overground |
| obstacle_walk | Walking with obstacles | Continuous | Foam blocks | 1.0 m/s |
| poses | Static postures | Hold positions | Various poses | Calibration |
| push | External perturbations | Multiple trials | Push/pull by experimenter | Balance |

### Data Columns

#### Kinematic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_flexion_angle_r/l_rad | Hip flexion/extension angle | radians | 200 Hz |
| hip_adduction_angle_r/l_rad | Hip adduction/abduction angle | radians | 200 Hz |
| hip_rotation_angle_r/l_rad | Hip internal/external rotation | radians | 200 Hz |
| knee_flexion_angle_r/l_rad | Knee flexion/extension angle | radians | 200 Hz |
| ankle_dorsiflexion_angle_r/l_rad | Ankle dorsi/plantarflexion angle | radians | 200 Hz |
| ankle_eversion_angle_r/l_rad | Ankle inversion/eversion angle | radians | 200 Hz |
| hip_flexion_velocity_r/l_rad_s | Hip angular velocity (sagittal) | rad/s | 200 Hz |
| hip_adduction_velocity_r/l_rad_s | Hip angular velocity (frontal) | rad/s | 200 Hz |
| hip_rotation_velocity_r/l_rad_s | Hip angular velocity (transverse) | rad/s | 200 Hz |
| knee_flexion_velocity_r/l_rad_s | Knee angular velocity (sagittal) | rad/s | 200 Hz |
| ankle_dorsiflexion_velocity_r/l_rad_s | Ankle angular velocity (sagittal) | rad/s | 200 Hz |
| ankle_eversion_velocity_r/l_rad_s | Ankle angular velocity (frontal) | rad/s | 200 Hz |
| pelvis_angle_s/f/t | Pelvis angles (sagittal/frontal/transverse) | radians | 200 Hz |
| torso_angle_s/f/t | Torso angles (sagittal/frontal/transverse) | radians | 200 Hz |
| thigh_angle_s/f/t_r/l | Thigh segment angles | radians | 200 Hz |
| shank_angle_s/f/t_r/l | Shank segment angles | radians | 200 Hz |
| foot_angle_s/f/t_r/l | Foot segment angles | radians | 200 Hz |

#### Kinetic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_flexion_moment_r/l_Nm | Hip flexion/extension moment | Nm | 200 Hz |
| hip_adduction_moment_r/l_Nm | Hip adduction/abduction moment | Nm | 200 Hz |
| hip_rotation_moment_r/l_Nm | Hip internal/external rotation moment | Nm | 200 Hz |
| knee_flexion_moment_r/l_Nm | Knee flexion/extension moment | Nm | 200 Hz |
| ankle_dorsiflexion_moment_r/l_Nm | Ankle dorsi/plantarflexion moment | Nm | 200 Hz |
| ankle_eversion_moment_r/l_Nm | Ankle inversion/eversion moment | Nm | 200 Hz |
| force_x_r/l | Anterior-posterior ground reaction force | N | 200 Hz |
| force_y_r/l | Medial-lateral ground reaction force | N | 200 Hz |
| force_z_r/l | Vertical ground reaction force | N | 200 Hz |
| COP_x_r/l | Anterior-posterior center of pressure | m | 200 Hz |
| COP_y_r/l | Medial-lateral center of pressure | m | 200 Hz |
| COP_z_r/l | Vertical center of pressure | m | 200 Hz |

#### Additional Data (if applicable)
| Variable Name | Type | Description | Units | Sampling Rate |
|--------------|------|-------------|-------|---------------|
| Raw_EMGs | EMG | Raw electromyography signals | mV | 2000 Hz |
| Real_IMUs | IMU | Real IMU sensor data | Various | 200 Hz |
| Virtual_IMUs | IMU | Virtual IMU calculations | Various | 200 Hz |
| Virtual_Insoles | Pressure | Virtual insole pressure | N | 200 Hz |
| Joint_Powers | Power | Joint power calculations | W/kg | 200 Hz |
| Link_Angles | Kinematics | Segment angles | degrees | 200 Hz |
| Link_Velocities | Kinematics | Segment angular velocities | deg/s | 200 Hz |
| Activity_Flag | Metadata | Activity phase markers | Binary | 200 Hz |

### File Structure
```
gtech_2023/
├── time_series/
│   └── gtech_2023_time.parquet
├── phase_normalized/
│   └── gtech_2023_phase.parquet
├── individual_subjects/
│   └── gtech_2023_time_[subject_id].parquet
└── raw_data/
    └── [subject_id]/CSV_Data/[task_name]/
        ├── Joint_Angle.csv
        ├── Joint_Moments.csv
        ├── GroundFrame_GRFs.csv
        └── [additional files]
```

## Data Collection Methods

### Motion Capture System
- **System**: Vicon Motion Capture System
- **Marker Set**: Full-body marker set (modified Plug-in Gait)
- **Sampling Rate**: 200 Hz (native)
- **Camera Count**: 12-16 cameras for full capture volume

### Force Plates
- **Model**: AMTI Force Plates (ground-embedded) and Bertec Instrumented Treadmill
- **Sampling Rate**: 1000 Hz (downsampled to 200 Hz for synchronization)
- **Configuration**: Multiple ground-embedded plates + dual-belt instrumented treadmill

### Additional Sensors
- **EMG System**: Delsys Trigno Wireless EMG at 2000 Hz
- **IMU System**: Xsens MTw Awinda wireless IMUs at 200 Hz
- **Virtual Sensors**: Calculated from motion capture data (virtual IMUs and insoles)

### CAREN System
- **Facility**: Motek Computer-Aided Rehabilitation Environment (CAREN)
- **Components**: 10-camera Vicon system, 16-channel Delsys EMG, instrumented treadmill on 6-DOF Stewart platform
- **Display**: 180° projection screen for immersive environments
- **Software**: Motek D-Flow for real-time data integration

### Processing Pipeline
1. Motion capture with full-body markers
2. C3D file creation with Visual3D or similar
3. Export to CSV format per trial
4. Mass normalization for kinetic data
5. Conversion to standardized parquet format

## Known Issues and Limitations

### Data Quality Issues
- Some trials may have marker occlusions during complex movements
- EMG data not yet standardized in parquet format
- IMU data not yet integrated into standard format

### Missing Data
- Subject AB04 not included in dataset
- Some subjects may be missing specific trials
- Phase normalization may fail for non-cyclic tasks

### Processing Artifacts
- High-frequency noise in calculated velocities
- Force plate saturation possible during jumping tasks
- Coordinate system conversions required for standard alignment

## Usage Notes

### Recommended Use Cases
- Comprehensive movement analysis across diverse activities
- Sports biomechanics research
- Daily activity biomechanics
- Multi-task movement patterns
- Machine learning on varied movement data

### Not Recommended For
- Clinical gait analysis (healthy subjects only)
- Pediatric or elderly populations
- Pathological movement patterns

### Data Access Requirements
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Access Process**: Contact EPIC Lab at epic-lab@gatech.edu
- **Usage Restrictions**: Academic and commercial use allowed with proper citation

## Version History
| Version | Date | Changes | Notes |
|---------|------|---------|-------|
| 1.0 | 2023 | Initial collection | CSV format per trial |
| 2.0 | 2024 | Standardized format | Parquet conversion with unified structure |

## Contact Information
- **Dataset Curator**: Aaron Young, Ph.D.
- **Lab Website**: https://www.epic.gatech.edu/
- **Lab Email**: epic-lab@gatech.edu
- **Technical Support**: Contact via lab email
- **Bug Reports**: GitHub issues on this repository

## Additional Resources
- **Lab Website**: https://www.epic.gatech.edu/
- **Lab Publications**: https://www.epic.gatech.edu/journal-papers/
- **Open-Source Resources**: https://www.epic.gatech.edu/open-source-data-models/
- **Documentation**: See conversion scripts in `source/conversion_scripts/Gtech_2023/`
- **Code Examples**: See tutorials folder
- **Visualization Tools**: `mosaic_plot.py`, `walking_animator.py`
- **Related Datasets**: UMich 2021, AddBiomechanics

## Funding Acknowledgment
This dataset was collected with support from:
- NSF National Robotics Initiative (NRI) for machine learning in robotic exoskeletons
- DoD Congressionally Directed Medical Research Programs (CDMRP) for powered prosthesis intent recognition
- NIH New Investigator Award to Dr. Aaron Young
- IEEE New Faces of Engineering Award

## Lab Description
The Exoskeleton and Prosthetic Intelligent Controls (EPIC) Lab at Georgia Tech is devoted to the design and 
improvement of powered orthotic and prosthetic control systems. The lab combines machine learning, robotics, 
human biomechanics, and control systems to design wearable robots that improve community mobility for 
individuals with walking disability. The EPIC Lab has state-of-the-art facilities including the CAREN system 
for immersive biomechanics research.

---
*Last Updated: January 2025*
*Template Version: 1.0*