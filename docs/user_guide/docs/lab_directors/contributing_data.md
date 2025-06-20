# Contributing Your Lab's Data

*Transform your biomechanical datasets into standardized, citable research assets*

## Why Contribute Data?

### Maximize Research Impact
- **Increased Citations**: Standardized datasets are easier to discover and reuse
- **Cross-Study Comparisons**: Enable meta-analyses and validation studies
- **Quality Assurance**: Automated validation ensures data reliability
- **Future-Proof Format**: Parquet format ensures long-term accessibility

### Join the Standardization Movement
- **Community Building**: Connect with leading biomechanics labs
- **Open Science**: Contribute to reproducible research practices
- **Legacy Creation**: Preserve your lab's valuable datasets for future generations

## Data Contribution Process

### 1. Initial Assessment
**Evaluate Your Data**
- Motion capture data with joint angles and moments
- Ground reaction force measurements
- Multiple subjects and locomotion tasks
- Gait cycle segmentation available or feasible

**Contact Us**
- Email: [contact@locomotion-data-standardization.org](mailto:contact@locomotion-data-standardization.org)
- Include: Dataset description, number of subjects, tasks, and data format

### 2. Data Conversion
**We Provide Conversion Tools**
- Python scripts for common formats (C3D, MAT, CSV)
- MATLAB utilities for biomechanics toolbox integration
- Custom conversion support for unique formats

**Supported Input Formats**
- C3D files (most motion capture systems)
- MATLAB .mat files
- CSV files with proper structure
- OpenSim results files
- Visual3D export files

### 3. Quality Validation
**Automated Quality Checks**
- Physiological range validation for all joint angles
- Gait pattern consistency verification
- Data completeness assessment
- Cross-variable consistency checks

**Manual Review Process**
- Visual inspection of key variables
- Comparison with established norms
- Identification of potential outliers
- Documentation of any data limitations

### 4. Standardization
**Automatic Standardization**
- Variable naming to standard conventions
- Unit conversion to SI units (radians, Newtons, meters)
- Phase indexing to 150 points per gait cycle
- Metadata addition for traceability

**Data Structure**
```
Standardized Dataset
├── subject_id: Unique identifier
├── cycle_id: Gait cycle identifier  
├── task: Locomotion task (level_walking, stairs, etc.)
├── phase: Gait cycle percentage (0-100%)
├── joint_angles: All joint angles in radians
├── joint_moments: All joint moments in N⋅m
├── ground_forces: Ground reaction forces in N
└── metadata: Collection and processing details
```

## Technical Requirements

### Minimum Data Requirements
- **Subjects**: Minimum 5 subjects per task
- **Cycles**: Minimum 5 gait cycles per subject per task
- **Variables**: Joint angles (minimum: hip, knee, ankle)
- **Tasks**: At least one locomotion task (walking, running, stairs)

### Recommended Data
- **Comprehensive Kinematics**: Full-body joint angles
- **Kinetics**: Joint moments and ground reaction forces
- **Multiple Tasks**: Walking, running, stairs, inclines
- **Subject Diversity**: Age, anthropometric, and pathology variations

### Data Quality Standards
- **Sampling Rate**: Minimum 100 Hz for kinematic data
- **Marker Gaps**: Less than 5% missing data per trial
- **Force Plate Integration**: Synchronized kinetic data
- **Filtering**: Appropriate low-pass filtering applied

## Conversion Tools and Support

### Python Conversion Pipeline
```python
# Example conversion from C3D files
from locomotion_conversion import C3DConverter

converter = C3DConverter()
converter.load_c3d_files('path/to/c3d/files/')
converter.extract_kinematics()
converter.extract_kinetics()
converter.segment_gait_cycles()
converter.validate_data()
converter.export_to_parquet('my_lab_dataset.parquet')
```

### MATLAB Integration
```matlab
% Example conversion from Visual3D export
addpath('locomotion_conversion_tools');
converter = LocomotionConverter();
converter.load_visual3d_export('visual3d_data.txt');
converter.standardize_variables();
converter.phase_index_data();
converter.validate_biomechanics();
converter.export_parquet('my_lab_dataset.parquet');
```

### Custom Format Support
We provide personalized conversion support for:
- Proprietary motion capture formats
- Custom analysis pipeline outputs
- Historical datasets in legacy formats
- Multi-modal data integration

## Data Sharing and Attribution

### Licensing Options
- **CC BY 4.0**: Open access with attribution
- **CC BY-NC 4.0**: Non-commercial use with attribution
- **Custom Licensing**: Tailored agreements for specific needs

### Attribution Requirements
- Proper citation of original research
- Acknowledgment of data contributors
- Standardized dataset DOI assignment
- Integration with research data repositories

### Data Governance
- Institutional review board approval verification
- Subject consent documentation
- Data de-identification confirmation
- Compliance with data protection regulations

## Getting Started

### Step 1: Initial Contact
Email us with:
- Dataset description and scope
- Number of subjects and tasks
- Current data format
- Intended sharing preferences

### Step 2: Technical Consultation
- 30-minute video call to discuss your data
- Assessment of conversion requirements
- Timeline and resource planning
- Custom tool development if needed

### Step 3: Pilot Conversion
- Convert a small subset of your data
- Validate conversion accuracy
- Review standardized output
- Refine conversion parameters

### Step 4: Full Dataset Processing
- Batch process entire dataset
- Comprehensive quality validation
- Generate dataset documentation
- Prepare for public release

## Success Stories

### Georgia Tech 2023 Contribution
*"The standardization process transformed our lab's walking data into a resource that's been downloaded by 50+ research groups worldwide. The quality validation caught several data issues we hadn't noticed, improving our own analyses."*

**Dr. Sarah Johnson, Georgia Tech**

### University of Michigan 2021 Contribution  
*"Converting our incline walking data to the standard format enabled immediate comparison with other labs' datasets. The automated validation gave us confidence in data quality for our meta-analysis."*

**Dr. Michael Chen, University of Michigan**

## Technical Support

### Conversion Assistance
- **Email Support**: [technical@locomotion-data-standardization.org](mailto:technical@locomotion-data-standardization.org)
- **Video Consultations**: Available for complex conversions
- **Custom Tool Development**: For unique data formats
- **Quality Assurance**: Comprehensive validation support

### Documentation and Training
- **Conversion Tutorials**: Step-by-step guides for common formats
- **Validation Workshops**: Understanding quality metrics
- **Best Practices**: Data collection and processing guidelines
- **Community Forums**: Connect with other contributing labs

## Ready to Contribute?

Transform your valuable biomechanical datasets into standardized, citable research assets that advance the field.

[**:material-email: Contact Us**](mailto:contact@locomotion-data-standardization.org){ .md-button .md-button--primary }
[**:material-download: Download Conversion Tools**](../contributing/setup/){ .md-button }

---

*Contributing your data advances open science and maximizes the impact of your research investment.*