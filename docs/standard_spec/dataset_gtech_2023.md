# Georgia Tech 2023 Multi-Activity Dataset

## Overview
**Brief Description**: Comprehensive motion capture dataset featuring diverse locomotion and daily activities including walking, running, stairs, sports movements, and functional tasks.

**Collection Year**: 2023

**Institution**: Georgia Institute of Technology

**Principal Investigators**: [To be determined]

## Citation Information

### Primary Citation
```
[Authors TBD]. (2023). Georgia Tech Multi-Activity Locomotion Dataset. [Repository TBD]. [DOI/URL TBD]
```

### Associated Publications
1. [To be added when available]

### Acknowledgments
[To be added when available]

## Dataset Contents

### Subjects
- **Total Subjects**: 12 (AB01, AB02, AB03, AB05, AB06, AB07, AB08, AB09, AB10, AB11, AB12, AB13)
- **Demographics**:
  - Age Range: [To be determined]
  - Sex Distribution: [To be determined]
  - Height Range: [To be determined]
  - Weight Range: 62.3-113.5 kg
  - Mean Weight: 76.95 kg
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
| side_shuffle | Lateral movement | Multiple cycles | Left/right | Overground |
| jump | Jumping | Multiple trials | Vertical jumps | Force plates |
| squats | Squatting | Multiple reps | With/without weight | Static |
| lunges | Forward/backward lunges | Multiple reps | Left/right legs | Overground |
| sit_to_stand | Sit-to-stand transitions | Multiple cycles | Chair height | Functional |
| ball_toss | Ball tossing | Multiple trials | Left/mid/right targets | Standing |
| curb_up | Stepping up curb | Multiple cycles | Street curb height | Overground |
| curb_down | Stepping down curb | Multiple cycles | Street curb height | Overground |
| cutting | Sharp turning while jogging | Multiple trials | Left/right | Overground |
| lift_weight | Weight lifting | Multiple trials | Weighted/unweighted bag | Functional |
| step_ups | Step-up exercise | Multiple cycles | Tall platform | Exercise |
| tire_run | High-knee jogging | Continuous | Toe running | Overground |
| turn_and_step | Turn and walk initiation | Multiple trials | Left/right turns | From standing |
| meander | Free-form slow walking | Continuous | Self-selected path | Overground |
| obstacle_walk | Walking with obstacles | Continuous | Foam blocks | 1.0 m/s |
| poses | Static postures | Hold positions | Various poses | Calibration |
| push | External perturbations | Multiple trials | Push/pull by experimenter | Balance |

### Data Columns

#### Kinematic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_angle_s_r/l | Hip flexion/extension angle | degrees | 200 Hz |
| hip_angle_f_r/l | Hip adduction/abduction angle | degrees | 200 Hz |
| hip_angle_t_r/l | Hip internal/external rotation | degrees | 200 Hz |
| knee_angle_s_r/l | Knee flexion/extension angle | degrees | 200 Hz |
| knee_angle_f_r/l | Knee varus/valgus angle | degrees | 200 Hz |
| knee_angle_t_r/l | Knee internal/external rotation | degrees | 200 Hz |
| ankle_angle_s_r/l | Ankle dorsi/plantarflexion angle | degrees | 200 Hz |
| ankle_angle_f_r/l | Ankle inversion/eversion angle | degrees | 200 Hz |
| ankle_angle_t_r/l | Ankle internal/external rotation | degrees | 200 Hz |
| hip_vel_s_r/l | Hip angular velocity (sagittal) | deg/s | 200 Hz |
| knee_vel_s_r/l | Knee angular velocity (sagittal) | deg/s | 200 Hz |
| ankle_vel_s_r/l | Ankle angular velocity (sagittal) | deg/s | 200 Hz |

#### Kinetic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_torque_s_r/l | Hip flexion/extension moment | Nm/kg | 200 Hz |
| hip_torque_f_r/l | Hip adduction/abduction moment | Nm/kg | 200 Hz |
| hip_torque_t_r/l | Hip internal/external rotation moment | Nm/kg | 200 Hz |
| knee_torque_s_r/l | Knee flexion/extension moment | Nm/kg | 200 Hz |
| knee_torque_f_r/l | Knee varus/valgus moment | Nm/kg | 200 Hz |
| knee_torque_t_r/l | Knee internal/external rotation moment | Nm/kg | 200 Hz |
| ankle_torque_s_r/l | Ankle dorsi/plantarflexion moment | Nm/kg | 200 Hz |
| ankle_torque_f_r/l | Ankle inversion/eversion moment | Nm/kg | 200 Hz |
| ankle_torque_t_r/l | Ankle internal/external rotation moment | Nm/kg | 200 Hz |
| ap_grf_r/l | Anterior-posterior ground reaction force | N | 200 Hz |
| vertical_grf_r/l | Vertical ground reaction force | N | 200 Hz |
| ml_grf_r/l | Medial-lateral ground reaction force | N | 200 Hz |

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
- **System**: [To be determined - likely Vicon or similar]
- **Marker Set**: Full-body marker set
- **Sampling Rate**: 200 Hz (native)
- **Camera Count**: [To be determined]

### Force Plates
- **Model**: [To be determined]
- **Sampling Rate**: 200 Hz
- **Configuration**: Ground-embedded and treadmill-integrated

### Additional Sensors
- **EMG System**: Surface EMG at 2000 Hz
- **IMU System**: Wearable IMUs at 200 Hz
- **Virtual Sensors**: Calculated from motion capture data

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
- **License**: [To be determined]
- **Access Process**: Contact dataset maintainers
- **Usage Restrictions**: [To be determined]

## Version History
| Version | Date | Changes | Notes |
|---------|------|---------|-------|
| 1.0 | 2023 | Initial collection | CSV format per trial |
| 2.0 | 2024 | Standardized format | Parquet conversion with unified structure |

## Contact Information
- **Dataset Curator**: [To be determined]
- **Technical Support**: [Contact via repository]
- **Bug Reports**: GitHub issues

## Additional Resources
- **Documentation**: See conversion scripts in `source/conversion_scripts/Gtech_2023/`
- **Code Examples**: See tutorials folder
- **Visualization Tools**: `mosaic_plot.py`, `walking_animator.py`
- **Related Datasets**: UMich 2021, AddBiomechanics

## Funding Acknowledgment
[To be added when available]

---
*Last Updated: January 2025*
*Template Version: 1.0*