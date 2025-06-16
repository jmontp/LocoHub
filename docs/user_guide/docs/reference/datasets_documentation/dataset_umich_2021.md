# University of Michigan 2021 Treadmill Dataset

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
- **Total Subjects**: 10 (AB01-AB10)
- **Demographics**:
  - Age Range: 20-60 years
  - Sex Distribution: 5F/5M
  - Height Range: 1617-1900 mm
  - Weight Range: 53.7-87.0 kg
  - Mean Age: 30.4 years
  - Mean Weight: 74.63 kg
  - Mean Height: 1727.8 mm

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| Tread.d10 | Decline walking | Continuous | -10° decline | Treadmill |
| Tread.d5 | Decline walking | Continuous | -5° decline | Treadmill |
| Tread.i0 | Level walking | Continuous | 0° (level) | Treadmill |
| Tread.i5 | Incline walking | Continuous | 5° incline | Treadmill |
| Tread.i10 | Incline walking | Continuous | 10° incline | Treadmill |
| Run.s1x8 | Running | Continuous | 1.8 m/s | Level treadmill |
| Run.s2x0 | Running | Continuous | 2.0 m/s | Level treadmill |
| Run.s2x2 | Running | Continuous | 2.2 m/s | Level treadmill |
| Run.s2x4 | Running | Continuous | 2.4 m/s | Level treadmill |
| Wtr | Walk-to-run transition | Transition | Variable | Treadmill |
| Sts | Sit-to-stand | Multiple cycles | N/A | Static task |
| Stair | Stair climbing | Multiple cycles | Standard stairs | Overground |

### Data Columns

#### Kinematic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_angle_s_r/l | Hip flexion/extension angle | degrees | 100 Hz |
| hip_angle_f_r/l | Hip adduction/abduction angle | degrees | 100 Hz |
| hip_angle_t_r/l | Hip internal/external rotation | degrees | 100 Hz |
| knee_angle_s_r/l | Knee flexion/extension angle | degrees | 100 Hz |
| knee_angle_f_r/l | Knee varus/valgus angle | degrees | 100 Hz |
| knee_angle_t_r/l | Knee internal/external rotation | degrees | 100 Hz |
| ankle_angle_s_r/l | Ankle dorsi/plantarflexion angle | degrees | 100 Hz |
| ankle_angle_f_r/l | Ankle inversion/eversion angle | degrees | 100 Hz |
| ankle_angle_t_r/l | Ankle internal/external rotation | degrees | 100 Hz |
| pelvis_angle_s/f/t_r/l | Pelvis angles (3 planes) | degrees | 100 Hz |
| foot_progress_angle_s/f/t_r/l | Foot progression angles | degrees | 100 Hz |

#### Kinetic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| hip_torque_s_r/l | Hip flexion/extension moment | Nm/kg | 100 Hz |
| hip_torque_f_r/l | Hip adduction/abduction moment | Nm/kg | 100 Hz |
| hip_torque_t_r/l | Hip internal/external rotation moment | Nm/kg | 100 Hz |
| knee_torque_s_r/l | Knee flexion/extension moment | Nm/kg | 100 Hz |
| knee_torque_f_r/l | Knee varus/valgus moment | Nm/kg | 100 Hz |
| knee_torque_t_r/l | Knee internal/external rotation moment | Nm/kg | 100 Hz |
| ankle_torque_s_r/l | Ankle dorsi/plantarflexion moment | Nm/kg | 100 Hz |
| ankle_torque_f_r/l | Ankle inversion/eversion moment | Nm/kg | 100 Hz |
| ankle_torque_t_r/l | Ankle internal/external rotation moment | Nm/kg | 100 Hz |
| ap_grf_r/l | Anterior-posterior ground reaction force | N | 100 Hz |
| vertical_grf_r/l | Vertical ground reaction force | N | 100 Hz |
| ml_grf_r/l | Medial-lateral ground reaction force | N | 100 Hz |
| ap_cop_r/l | Anterior-posterior center of pressure | m | 100 Hz |
| vertical_cop_r/l | Vertical center of pressure | m | 100 Hz |
| ml_cop_r/l | Medial-lateral center of pressure | m | 100 Hz |

### File Structure
```
umich_2021/
├── time_series/
│   └── umich_2021_time_series.parquet
├── phase_normalized/
│   └── umich_2021_phase_normalized.parquet
└── metadata/
    ├── Streaming.mat (original)
    └── Normalized.mat (original)
```

## Data Collection Methods

### Motion Capture System
- **System**: Vicon Motion Capture System
- **Marker Set**: Modified Helen Hayes marker set
- **Sampling Rate**: 100 Hz
- **Camera Count**: 10 cameras (when at UT Dallas)

### Force Plates
- **Model**: Bertec Instrumented Treadmill
- **Sampling Rate**: 100 Hz (resampled)
- **Configuration**: Dual-belt treadmill with embedded force plates

### EMG System
- **Model**: Delsys Trigno EMG System
- **Muscles Recorded**: Rectus femoris, biceps femoris, tibialis anterior, gastrocnemius
- **Sampling Rate**: 2000 Hz (downsampled to 100 Hz for analysis)

### Processing Pipeline
1. Motion capture with marker-based system
2. Gap filling and filtering
3. Inverse kinematics for joint angles
4. Inverse dynamics for joint moments
5. Data exported to MATLAB format
6. Conversion to standardized parquet format with sign convention alignment

## Known Issues and Limitations

### Data Quality Issues
- Some subjects may have missing tasks in normalized data (e.g., Tread field missing)
- Joint angles and moments may be missing for certain stride cycles in normalized data
- Force plate data may have saturation during high-impact activities (running)

### Missing Data
- Specific secondary conditions may lack jointAngles, jointMoments, or forceplates fields
- Individual stride cycles may be excluded due to quality issues

### Processing Artifacts
- Sign conventions in raw MAT files differ from OpenSim standards (handled by conversion scripts)
- Knee flexion angle requires negation for proper convention alignment

## Usage Notes

### Recommended Use Cases
- Treadmill walking biomechanics analysis
- Speed and incline effects on gait
- Walk-to-run transition studies
- Comparative analysis across normalized gait cycles

### Not Recommended For
- Overground walking analysis (limited stair data)
- High-speed running (max 2.4 m/s)
- Turning or cutting maneuvers (treadmill constraint)

### Data Access Requirements
- **License**: Research use with appropriate citation
- **Access Process**: Contact Locomotor Control Systems Laboratory (locolab@umich.edu)
- **Usage Restrictions**: Academic research use only, commercial use requires separate agreement

## Version History
| Version | Date | Changes | Notes |
|---------|------|---------|-------|
| 1.0 | 2021 | Initial release | Original MATLAB format |
| 2.0 | 2024 | Standardized format | Converted to parquet with aligned conventions |

## Contact Information
- **Dataset Curator**: Robert D. Gregg IV, Ph.D.
- **Lab Website**: https://gregg.engin.umich.edu/
- **Lab Email**: locolab@umich.edu
- **Technical Support**: Contact via lab email
- **Bug Reports**: GitHub issues on this repository

## Additional Resources
- **Lab Website**: https://locolab.robotics.umich.edu/
- **Lab GitHub**: https://github.com/locolab (if available)
- **Documentation**: `umich_2021_mat_structure.md`
- **Code Examples**: See tutorials folder
- **Visualization Tools**: `walking_animator.py`
- **Related Datasets**: Georgia Tech datasets, AddBiomechanics

## Funding Acknowledgment
This dataset was collected with support from:
- NIH Director's New Innovator Award (DP2HD080349)
- NIH R01 Grant for agile powered prosthetic legs (R01HD094772)
- Burroughs Wellcome Fund Career Award at the Scientific Interface ($500,000)

## Lab Description
The Locomotor Control Systems Laboratory is a highly interdisciplinary environment dedicated to scientific innovation, 
clinical translation, and individual career development. The lab develops high-performance control systems for robotic 
prostheses and orthoses to enable mobility and improve quality of life for persons with disabilities.

---
*Last Updated: January 2025*
*Template Version: 1.0*