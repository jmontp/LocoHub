# Dataset Name

## Overview
**Brief Description**: [1-2 sentence summary of the dataset's purpose and scope]

**Collection Year**: [Year]

**Institution**: [Institution name and department]

**Principal Investigators**: [PI names and affiliations]

## Citation Information

### Primary Citation
```
[Authors]. ([Year]). [Dataset title]. [Repository/Archive]. [DOI/URL]
```

### Associated Publications
1. [List any papers that describe the dataset or use it]
2. [Include DOI links where available]

### Acknowledgments
[Any specific acknowledgment text required by the dataset creators or funding sources]

## Dataset Contents

### Subjects
- **Total Subjects**: [Number]
- **Demographics**:
  - Age Range: [min-max years]
  - Sex Distribution: [M/F counts]
  - Height Range: [min-max cm]
  - Weight Range: [min-max kg]
  - Additional Characteristics: [e.g., healthy/pathological, activity level]

### Tasks Included
| Task ID | Task Description | Duration/Cycles | Conditions | Notes |
|---------|------------------|-----------------|------------|-------|
| [ID] | [Description] | [Time/cycles] | [Speed/incline/etc] | [Special notes] |

### Data Columns

#### Kinematic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| [name] | [description] | [units] | [Hz] |

#### Kinetic Variables
| Variable Name | Description | Units | Sampling Rate |
|--------------|-------------|-------|---------------|
| [name] | [description] | [units] | [Hz] |

#### Additional Data (if applicable)
| Variable Name | Type | Description | Units | Sampling Rate |
|--------------|------|-------------|-------|---------------|
| [name] | [EMG/IMU/etc] | [description] | [units] | [Hz] |

### File Structure
```
dataset_name/
├── time_series/
│   └── [file_naming_pattern].parquet
├── phase_normalized/
│   └── [file_naming_pattern].parquet
└── metadata/
    └── [any additional metadata files]
```

## Data Collection Methods

### Motion Capture System
- **System**: [e.g., Vicon, OptiTrack]
- **Marker Set**: [e.g., Plug-in Gait, custom]
- **Sampling Rate**: [Hz]
- **Camera Count**: [Number]

### Force Plates (if applicable)
- **Model**: [Manufacturer and model]
- **Sampling Rate**: [Hz]
- **Configuration**: [e.g., embedded in walkway, treadmill-mounted]

### Additional Sensors (if applicable)
- **EMG System**: [Details]
- **IMU System**: [Details]
- **Other**: [Details]

### Processing Pipeline
1. [Step 1: e.g., marker labeling]
2. [Step 2: e.g., gap filling]
3. [Step 3: e.g., filtering specifications]
4. [Step 4: e.g., inverse kinematics/dynamics]

## Known Issues and Limitations

### Data Quality Issues
- [Issue 1: e.g., marker occlusions in specific tasks]
- [Issue 2: e.g., force plate saturation in running trials]

### Missing Data
- [Subject IDs with missing trials]
- [Tasks with incomplete data]
- [Specific variables with gaps]

### Processing Artifacts
- [Any known artifacts from processing]
- [Recommended exclusion criteria]

## Usage Notes

### Recommended Use Cases
- [Appropriate research applications]
- [Validated analyses with this dataset]

### Not Recommended For
- [Limitations on use]
- [Analyses that may be problematic]

### Data Access Requirements
- **License**: [Open/Restricted/Custom]
- **Access Process**: [How to obtain the data]
- **Usage Restrictions**: [Any specific restrictions]

## Version History
| Version | Date | Changes | Notes |
|---------|------|---------|-------|
| 1.0 | [Date] | Initial release | [Notes] |

## Contact Information
- **Dataset Curator**: [Name, email]
- **Technical Support**: [Contact info]
- **Bug Reports**: [Where to report issues]

## Additional Resources
- **Documentation**: [Links to additional docs]
- **Code Examples**: [Links to example scripts]
- **Visualization Tools**: [Available tools]
- **Related Datasets**: [Similar or complementary datasets]

## Funding Acknowledgment
[Grant numbers and funding agencies that supported this work]

---
*Last Updated: [Date]*
*Template Version: 1.0*