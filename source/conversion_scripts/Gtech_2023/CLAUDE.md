# CLAUDE.md - GTech 2023 Conversion Scripts

This file provides Claude Code guidance for working with the Georgia Tech 2023 dataset conversion scripts.

## Overview

The GTech 2023 conversion scripts process biomechanical data from Georgia Tech's 2023 study featuring 13 subjects performing 19 different activities. This dataset includes kinematic, kinetic, EMG, and IMU data converted from MATLAB .mat files to standardized Parquet format.

## Directory Structure

```
Gtech_2023/
├── readme.md                         # Main conversion documentation and usage
├── convert_gtech_all_to_parquet.py   # Main conversion script for all subjects
├── combine_subjects_efficient.py     # Efficient subject file merger
├── process_all_subjects.sh           # Batch processing shell script
├── convert_gtech_phase_to_parquet.m  # MATLAB phase conversion (legacy)
├── _datamissing.txt                  # Documentation of missing data
├── RawData/                          # Raw input data directory (not in repo)
│   ├── AB01/ to AB13/               # Individual subject directories
│   └── Subject_masses.csv           # Body mass metadata
├── Plots/                           # Validation and alignment plots
│   └── AlignmentChecks_RawHS/       # Heel strike alignment validation plots
├── Segmentation/                    # Gait cycle segmentation data
└── utilities/                       # Helper scripts and tools
    ├── convert_gtech_rotm_to_eul_csv.m    # Rotation matrix to Euler conversion
    ├── plot_leg_alignment.m               # Leg alignment visualization
    ├── benchmark_processing.m             # Performance benchmarking
    ├── test_parquet_conversion.m          # Conversion testing
    └── verify_gtech_data.ipynb            # Data verification notebook
```

## Key Scripts and Their Purposes

### 1. `convert_gtech_all_to_parquet.py` - Main Converter
**Purpose**: Primary conversion script that processes all GTech 2023 subjects

**Input Data Structure**:
- **Subject directories**: `RawData/AB01/` through `RawData/AB13/`
- **MATLAB .mat files**: Kinematic and kinetic data per subject
- **Subject metadata**: `RawData/Subject_masses.csv` with body mass information

**Output**:
- `gtech_2023_time.parquet` - Time-indexed dataset
- `gtech_2023_phase.parquet` - Phase-indexed dataset (150 points/cycle)
- Metadata files for subjects and tasks

**Processing Pipeline**:
1. **Load subject data**: Read .mat files for each subject (AB01-AB13)
2. **Parse kinematics**: Extract joint angles from motion capture data
3. **Parse kinetics**: Extract joint moments and ground reaction forces
4. **Apply body mass normalization**: Normalize forces/moments using subject body mass
5. **Standardize variable names**: Apply project naming conventions
6. **Generate time-indexed output**: Preserve original temporal resolution
7. **Perform phase normalization**: Create 150-point gait cycle data
8. **Export standardized Parquet**: Create final standardized datasets

### 2. `combine_subjects_efficient.py` - Subject Merger
**Purpose**: Efficiently combine individual subject files into single dataset

**Features**:
- **Memory-efficient processing**: Handles large datasets without memory issues
- **Chunk-based combination**: Processes subjects in manageable chunks
- **Data validation**: Ensures consistency across subjects
- **Progress monitoring**: Provides processing status updates

**Usage Scenarios**:
- Combining individual subject conversions
- Memory-safe processing of large datasets
- Batch processing multiple conversion outputs

### 3. `process_all_subjects.sh` - Batch Processing
**Purpose**: Shell script for automated batch processing of all subjects

**Features**:
- **Automated pipeline**: Runs complete conversion pipeline
- **Error handling**: Robust error checking and logging
- **Progress tracking**: Monitors processing status
- **Resource management**: Manages memory and disk usage

**Workflow**:
```bash
#!/bin/bash
for subject in AB01 AB02 AB03 ... AB13; do
    echo "Processing $subject..."
    python convert_single_subject.py --subject $subject
    python validate_subject.py --subject $subject
done
python combine_subjects_efficient.py --output gtech_2023_combined.parquet
```

## Dataset Characteristics

### Subject Information
- **Count**: 13 subjects (AB01 through AB13)
- **Demographics**: Adults, mixed gender
- **Body mass data**: Available in `RawData/Subject_masses.csv`
- **Data completeness**: Some subjects missing right-leg data (documented in `_datamissing.txt`)

### Activity Types (19 Tasks)
**Locomotion Activities**:
- `normal_walk` - Self-selected walking speed
- `incline_walk` - Walking on inclined surfaces (±5°, ±10°)
- `decline_walk` - Walking on declined surfaces
- `stairs` - Stair ascent and descent
- `run` - Running at various speeds

**Functional Activities**:
- `sit_to_stand` - Rising from chair
- `stand_to_sit` - Sitting down
- `squats` - Bodyweight squats
- `lunges` - Forward lunges
- `jump` - Vertical jumping

**Sport/Dynamic Activities**:
- `cutting` - Lateral cutting movements
- `side_shuffle` - Lateral shuffling
- `ball_toss` - Ball throwing (left, middle, right)
- `tire_run` - Agility course with tires
- `step_ups` - Step-up exercises

**Specialized Tasks**:
- `lift_weight` - Weight lifting simulation
- `curb_up`/`curb_down` - Curb negotiation
- `obstacle_walk` - Obstacle avoidance walking

### Data Modalities
**Kinematics**:
- 3D joint angles (hip, knee, ankle)
- Segment orientations (pelvis, thigh, shank, foot)
- Joint angular velocities

**Kinetics**:
- Joint moments (normalized by body weight)
- Joint powers
- Ground reaction forces (3D)
- Center of pressure

**Additional Modalities** (if available):
- EMG data from major lower limb muscles
- IMU data from wearable sensors

## Processing Details

### Data Loading and Parsing
**MATLAB .mat File Structure**:
```matlab
% Typical subject file structure
subject_data.AB01.normal_walk_1.kinematics.hip_flexion_angle
subject_data.AB01.normal_walk_1.kinetics.hip_moment
subject_data.AB01.normal_walk_1.forces.vertical_grf
```

**Python Processing**:
```python
import scipy.io as sio
import pandas as pd

# Load MATLAB data
data = sio.loadmat('RawData/AB01/subject_data.mat')

# Extract and standardize variables
hip_flexion = data['subject_data']['AB01']['normal_walk_1']['kinematics']['hip_flexion_angle']
# Apply naming convention: hip_flexion_angle_right_rad
```

### Variable Standardization
**Original → Standardized Mapping**:
- `hip_flexion_angle` → `hip_flexion_angle_right_rad`
- `knee_flexion_angle` → `knee_flexion_angle_right_rad`
- `ankle_flexion_angle` → `ankle_flexion_angle_right_rad`
- `hip_moment` → `hip_moment_right_Nm`
- `vertical_grf` → `vertical_grf_N`

**Unit Conversions**:
- Angles: degrees → radians
- Moments: Normalize by body weight (Nm/kg → Nm using subject mass)
- Forces: Already in Newtons (validate range)

### Phase Normalization Process
1. **Gait Event Detection**:
   - Heel strikes detected using vertical GRF threshold
   - Toe-offs detected using GRF and kinematic patterns
   - Manual verification with alignment plots

2. **Cycle Extraction**:
   - Extract complete gait cycles (heel strike to heel strike)
   - Quality assessment for cycle completeness
   - Filter out incomplete or outlier cycles

3. **Interpolation to 150 Points**:
   - Use cubic spline interpolation
   - Preserve biomechanical patterns
   - Validate interpolation quality

## Quality Control and Validation

### Alignment Validation
**Plot Generation**: `Plots/AlignmentChecks_RawHS/`
- **Purpose**: Visual validation of heel strike detection and cycle alignment
- **Contents**: Plots for each subject and task showing:
  - Vertical GRF with detected heel strikes
  - Joint angle patterns aligned by gait events
  - Quality assessment of gait cycle extraction

**Example Plots**:
- `LegAlignment_Subj_Gtech_2023_AB01_Task_normal_walk_1_TaskInfo_x1_2.png`
- Shows alignment quality for subject AB01, normal walking at 1.2 m/s

### Data Completeness Assessment
**Missing Data Documentation**: `_datamissing.txt`
- Documents known data gaps per subject
- Identifies missing right-leg data
- Provides guidance for analysis considerations

**Common Issues**:
- Some subjects missing right-leg kinematic data
- Incomplete EMG data for certain activities
- Missing trials for specific task conditions

### Validation Integration
**Automatic Validation**:
- All outputs validated using `../../tests/validation_blueprint.py`
- Task-specific validation rules for GTech activities
- Statistical validation of phase normalization

**Manual Verification**:
- Visual inspection using alignment plots
- Cross-subject consistency checks
- Task-specific biomechanical pattern validation

## Integration with Other Components

### With Validation System
- **Standard validation**: Uses 5-layer validation system
- **GTech-specific rules**: Task-specific biomechanical envelopes
- **Visual validation**: Alignment plots for manual inspection

### With Analysis Libraries
- **Python integration**: Compatible with `../../lib/python/locomotion_analysis.py`
- **MATLAB compatibility**: Legacy MATLAB processing available
- **3D array support**: Optimized for efficient multi-subject analysis

### With Documentation
- **Main README**: `readme.md` - detailed usage and data structure
- **Dataset documentation**: `../../../docs/datasets_documentation/dataset_gtech_2023.md`
- **Implementation details**: Cross-referenced with conversion implementation

## Utilities and Helper Scripts

### MATLAB Utilities (`utilities/`)
**`convert_gtech_rotm_to_eul_csv.m`**:
- Convert rotation matrices to Euler angles
- Export to CSV format for Python processing

**`plot_leg_alignment.m`**:
- Generate leg alignment validation plots
- Visual quality control for gait cycle detection

**`benchmark_processing.m`**:
- Performance benchmarking for conversion process
- Memory usage and timing analysis

### Development Tools
**`verify_gtech_data.ipynb`**:
- Jupyter notebook for data verification
- Interactive exploration of conversion outputs
- Quality assessment and debugging

## Common Issues and Troubleshooting

### Data Loading Issues
**MATLAB File Problems**:
- Corrupted .mat files
- Inconsistent data structures across subjects
- Missing variables for specific tasks

**Solutions**:
- Verify file integrity with MATLAB
- Check data structure consistency
- Handle missing data gracefully with NaN values

### Processing Issues
**Memory Problems**:
- Large datasets exceed available memory
- Inefficient data loading patterns

**Solutions**:
- Use `combine_subjects_efficient.py` for memory-safe processing
- Process subjects individually before combining
- Monitor memory usage during processing

### Validation Failures
**Common Failures**:
- Phase normalization errors
- Task naming inconsistencies
- Biomechanical validation failures

**Debugging**:
- Check alignment plots for gait cycle issues
- Verify task naming against controlled vocabulary
- Use enhanced validation for detailed error analysis

## Best Practices for Claude Code

### When Working with GTech 2023 Data
1. **Check data availability**: Verify RawData directory exists and is populated
2. **Use efficient processing**: Leverage `combine_subjects_efficient.py` for large datasets
3. **Validate alignment**: Review alignment plots before proceeding with analysis
4. **Handle missing data**: Account for missing right-leg data in some subjects
5. **Monitor memory**: GTech processing can be memory-intensive

### Performance Optimization
- **Batch processing**: Use shell scripts for automated processing
- **Memory management**: Process subjects individually before combining
- **Parallel processing**: Process independent subjects in parallel
- **Disk management**: Monitor disk space for large intermediate files

### Quality Assurance
- **Visual validation**: Always review alignment plots
- **Cross-subject checks**: Verify consistency across subjects
- **Task validation**: Ensure all 19 tasks are properly represented
- **Statistical validation**: Check phase normalization quality

This GTech 2023 conversion represents a comprehensive multi-activity dataset with robust validation and quality control processes, making it ideal for cross-task biomechanical analysis and machine learning applications.