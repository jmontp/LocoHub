# CLAUDE.md - Gtech 2021 Conversion

Process Georgia Tech 2021 dataset (Camargo et al. J Biomech) with 22 subjects performing multiple locomotion tasks.

## Dataset Overview

**Source**: CAMARGO_ET_AL_J_BIOMECH_DATASET
**Subjects**: 22 able-bodied participants (AB06-AB30, excluding AB22, AB26, AB27, AB29)
**Tasks**: Level ground walking, ramp ascent/descent, stair ascent/descent, treadmill walking
**Data Type**: OpenSim-processed biomechanical data

## Key Scripts

**Main Conversion**:
- `convert_gtech_2021_phase_to_parquet.m` - **METHOD 2**: Phase-indexed conversion with velocities calculated AFTER interpolation for exoskeleton control consistency
- `convert_gtech_2021_phase_advanced.m` - Advanced version using EpicToolbox

**Utilities**:
- `utilities/detect_heel_strikes_from_markers.m` - Fallback heel strike detection

**Dependencies**:
- `scripts/EpicToolbox/` - Data processing toolkit
- `scripts/MoCapTools/` - C3D file handling
- `scripts/lib/` - Helper functions (getHeelStrikes, etc.)

## Data Structure

**Input Directory Structure**:
```
CAMARGO_ET_AL_J_BIOMECH_DATASET/
├── AB06/
│   └── 10_09_18/
│       ├── levelground/
│       │   ├── conditions/  # Trial metadata
│       │   ├── ik/         # Joint angles
│       │   ├── id/         # Joint moments
│       │   ├── gcLeft/     # Left heel strikes
│       │   ├── gcRight/    # Right heel strikes
│       │   ├── emg/        # EMG data
│       │   └── jp/         # Joint powers
│       ├── ramp/
│       ├── stair/
│       └── treadmill/
├── SubjectInfo.mat  # Subject masses
└── scripts/         # Processing tools
```

**Output**:
- `gtech_2021_phase.parquet` - Phase-indexed (150 points/cycle)

## Processing Pipeline

### Basic Workflow
1. Load subject mass data from SubjectInfo.mat
2. Iterate through subjects and ambulation modes
3. Load trial data from subdirectories (ik, id, gcRight, etc.)
4. Segment by heel strikes (gcRight/gcLeft data)
5. Interpolate to 150 points per cycle
6. Normalize moments by body mass
7. Map task names to standard convention
8. Export to parquet format

### Advanced Workflow (using EpicToolbox)
1. Initialize FileManager for efficient file handling
2. Compute EMG normalization from treadmill trials
3. Load trials using EpicToolbox functions
4. Apply complex stride classification logic
5. Use Topics functions for normalization and interpolation
6. Filter transitions and invalid strides

## Key Features

**Data Processing**:
- Complex trial classification (stand-walk transitions, turns, etc.)
- EMG normalization based on treadmill walking at 1.35 m/s
- Automatic handling of missing data fields
- Fallback heel strike detection from markers

**Quality Control**:
- Filters idle periods and transitions
- Validates steady-state walking for treadmill
- Handles direction-specific tasks (ascent/descent)
- Discards invalid or incomplete strides

## Task Mapping

**Standard Conversions**:
```
levelground → level_walking
treadmill → level_walking (treadmill:true)
ramp + ascent → incline_walking  
ramp + descent → decline_walking
stair + ascent → stair_ascent
stair + descent → stair_descent
```

**Speed Mapping**:
- slow → 0.8 m/s
- normal → 1.0 m/s  
- fast → 1.2 m/s

## Variable Naming

**Angles** (radians):
- `ankle_angle` → `ankle_angle_ipsi_rad`
- `knee_angle` → `knee_flexion_angle_ipsi_rad`
- `hip_flexion` → `hip_flexion_angle_ipsi_rad`

**Moments** (Nm, normalized by mass):
- `ankle_moment` → `ankle_moment_ipsi_Nm`
- `knee_moment` → `knee_moment_ipsi_Nm`
- `hip_flexion_moment` → `hip_moment_ipsi_Nm`

**Sign Conventions**:
- Moments multiplied by -1 to match standard convention

## Usage

### Basic Conversion
```matlab
% Run basic conversion
cd contributor_tools/conversion_scripts/Gtech_2021/
convert_gtech_2021_phase_to_parquet
```

### Advanced Conversion (with EpicToolbox)
```matlab
% Run advanced conversion with filtering
cd contributor_tools/conversion_scripts/Gtech_2021/
convert_gtech_2021_phase_advanced
```

## Troubleshooting

**Common Issues**:

1. **Missing heel strike data**:
   - Script checks gcRight/gcLeft folders
   - Falls back to marker-based detection if needed

2. **Subject exclusions**:
   - AB27: No global angles available
   - AB100: Has mean/std instead of raw data
   - AB22, AB26, AB29: Not included in dataset

3. **Path issues**:
   - Ensure CAMARGO_ET_AL_J_BIOMECH_DATASET folder is in script directory
   - Check that scripts/EpicToolbox is accessible

4. **Memory issues**:
   - Process subjects in batches if needed
   - Clear workspace between subjects

## Performance

**Processing Time**:
- ~5-10 minutes per subject
- Total: ~2-3 hours for all 22 subjects

**Data Size**:
- Input: ~10 GB raw data
- Output: ~500 MB parquet file

## Testing

```matlab
% Test with single subject
subjects = {'AB06'};  % Modify line in script
convert_gtech_2021_phase_to_parquet

% Verify output
data = parquetread('converted_datasets/gtech_2021_phase.parquet');
unique(data.task)  % Check task names
unique(data.subject)  % Check subjects
```

## Notes

- Dataset uses OpenSim-processed data (already has IK/ID)
- Complex stride classification preserves data quality
- EpicToolbox functions handle data efficiently
- Can extend to include EMG, IMU, and marker data

---

*Comprehensive conversion of multi-task biomechanical dataset with sophisticated filtering.*