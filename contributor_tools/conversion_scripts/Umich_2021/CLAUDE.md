# CLAUDE.md - UMich 2021 Conversion

Process University of Michigan 2021 treadmill walking data (10 subjects, incline conditions).

## Key Scripts

**MATLAB Conversion**:
- `convert_umich_time_to_parquet.m` - Time-indexed conversion
- `convert_umich_phase_to_parquet.m` - Phase-indexed conversion (150 points/cycle)
- `convert_umich_events_to_parquet.m` - **METHOD 2**: Events-based conversion with velocities calculated AFTER interpolation for exoskeleton control consistency

**Documentation**:
- `umich_2021_mat_structure.md` - MATLAB data structure details
- `R01 Dataset README.pdf` - Original dataset documentation
- `verify_umich_data.ipynb` - Python verification notebook

## Data Characteristics

**Input**:
- MATLAB .mat files with structured biomechanical data
- Treadmill walking at multiple incline conditions
- 10 subjects (S01-S10) with consistent data structure

**Output**:
- `umich_2021_time.parquet` - Time-indexed dataset
- `umich_2021_phase.parquet` - Phase-indexed (150 points/cycle)
- Metadata files for subjects and task conditions

## Processing Pipeline

```
MATLAB .mat files → convert_umich_time_to_parquet.m → Time-indexed Parquet
                                                           ↓
Phase-indexed Parquet ← convert_umich_phase_to_parquet.m ← Metadata extraction
```

## Key Features

**Data Processing**:
- High-quality controlled treadmill locomotion
- Multiple incline conditions per subject
- Detailed kinematic and kinetic measurements
- Consistent data structure across subjects

**Quality Assurance**:
- Structured MATLAB data format (documented in `umich_2021_mat_structure.md`)
- Python verification notebook for cross-validation
- Original researcher documentation available

## MATLAB Processing

**Conversion Workflow**:
```matlab
% Load and process all subjects
subjects = {'S01', 'S02', ..., 'S10'};
for s = 1:length(subjects)
    subject_data = load([subjects{s} '_data.mat']);
    % Process kinematics, kinetics, and metadata
    % Apply standardized variable naming
    % Export to Parquet format
end
```

## Performance

**Processing Characteristics**:
- Lightweight compared to other datasets
- Consistent MATLAB data structure enables efficient processing
- Fast conversion due to smaller dataset size

## Testing

```matlab
% Run MATLAB conversion
convert_umich_time_to_parquet();
convert_umich_phase_to_parquet();

% Verify with Python
run('verify_umich_data.ipynb');
```

---

*Straightforward conversion of high-quality controlled treadmill walking data.*