# CLAUDE.md - UMich 2021 Conversion Scripts

This file provides Claude Code guidance for working with the University of Michigan 2021 dataset conversion scripts.

## Overview

The UMich 2021 conversion scripts process treadmill walking data from a University of Michigan study featuring 10 subjects walking at various incline conditions. This dataset focuses on high-quality controlled treadmill locomotion with detailed kinematic and kinetic measurements.

## Directory Structure

```
Umich_2021/
├── readme.md                         # Main conversion documentation and usage
├── umich_2021_mat_structure.md       # Detailed MATLAB data structure documentation
├── convert_umich_time_to_parquet.m   # MATLAB time-indexed conversion script
├── convert_umich_phase_to_parquet.m  # MATLAB phase-indexed conversion script
├── R01 Dataset README.pdf            # Original dataset documentation from researchers
└── verify_umich_data.ipynb           # Python verification notebook
```

## Key Scripts and Their Purposes

### 1. `convert_umich_time_to_parquet.m` - Time-Indexed Converter
**Purpose**: Primary MATLAB script for converting UMich data to time-indexed Parquet format

**Input Data**:
- MATLAB .mat files with structured biomechanical data
- Treadmill walking data at multiple incline conditions
- 10 subjects with consistent data structure

**Output**:
- `umich_2021_time.parquet` - Time-indexed dataset preserving original sampling
- `metadata_subject.parquet` - Subject demographic and anthropometric data
- `metadata_task.parquet` - Task condition metadata (speed, incline)

**MATLAB Processing Pipeline**:
```matlab
%% Main conversion workflow
function convert_umich_time_to_parquet()
    % 1. Load all subject .mat files
    subjects = {'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08', 'S09', 'S10'};
    
    % 2. Initialize data containers
    all_data = [];
    subject_meta = [];
    task_meta = [];
    
    % 3. Process each subject
    for s = 1:length(subjects)
        subject_data = load([subjects{s} '_data.mat']);
        
        % 4. Extract kinematics and kinetics for each condition
        conditions = fieldnames(subject_data.conditions);
        for c = 1:length(conditions)
            % Parse condition data
            [kinematics, kinetics, metadata] = parse_condition_data(subject_data, conditions{c});
            
            % Apply standardized naming
            standardized_data = apply_naming_convention(kinematics, kinetics);
            
            % Add metadata
            standardized_data.subject_id = repmat(subjects{s}, height(standardized_data), 1);
            standardized_data.task_id = repmat([subjects{s} '_' conditions{c}], height(standardized_data), 1);
            
            % Accumulate data
            all_data = [all_data; standardized_data];
        end
    end
    
    % 5. Export to Parquet using Python interface
    export_to_parquet(all_data, 'umich_2021_time.parquet');
end
```

### 2. `convert_umich_phase_to_parquet.m` - Phase-Indexed Converter
**Purpose**: MATLAB script for phase-normalized conversion (150 points per gait cycle)

**Phase Processing Features**:
- **Gait event detection**: Automated heel strike and toe-off detection
- **Cycle extraction**: Extract complete gait cycles from continuous treadmill data
- **Phase normalization**: Interpolate to 150 points per cycle using spline interpolation
- **Quality filtering**: Remove incomplete or outlier cycles

**MATLAB Phase Processing**:
```matlab
function convert_umich_phase_to_parquet()
    % Load time-indexed data
    time_data = load_time_indexed_data();
    
    % Process each subject and condition
    phase_data = [];
    for each subject and condition
        % Detect gait events
        [heel_strikes, toe_offs] = detect_gait_events(vertical_grf, time);
        
        % Extract gait cycles
        cycles = extract_gait_cycles(data, heel_strikes);
        
        % Phase normalize each cycle
        for cycle = 1:length(cycles)
            normalized_cycle = phase_normalize_cycle(cycles{cycle}, 150);
            normalized_cycle.phase_percent = linspace(0, 100, 150)';
            phase_data = [phase_data; normalized_cycle];
        end
    end
    
    % Export phase-indexed data
    export_to_parquet(phase_data, 'umich_2021_phase.parquet');
end
```

## Dataset Characteristics

### Subject Information
- **Count**: 10 subjects (S01 through S10)
- **Demographics**: Healthy adults, mixed gender
- **Anthropometrics**: Height, weight, leg length measurements available
- **Data quality**: High-quality controlled laboratory data

### Experimental Conditions
**Incline Walking Conditions**:
- **Level walking**: 0° incline at self-selected speed
- **Incline walking**: +5° and +10° uphill walking
- **Decline walking**: -5° and -10° downhill walking
- **Speed variations**: Multiple speeds tested per condition

**Controlled Variables**:
- **Treadmill speed**: Precisely controlled and recorded
- **Incline angle**: Accurate incline measurement
- **Environment**: Controlled laboratory conditions
- **Data collection**: Synchronized force plates and motion capture

### Data Modalities
**Kinematics** (Primary focus):
- 3D joint angles: hip, knee, ankle (sagittal, frontal, transverse planes)
- Segment angles: pelvis, thigh, shank, foot orientations
- Angular velocities for all joints

**Kinetics**:
- 3D ground reaction forces
- Joint moments (computed using inverse dynamics)
- Joint powers
- Center of pressure trajectories

**Temporal Parameters**:
- Gait cycle timing
- Stance and swing phase durations
- Step length and cadence measurements

## MATLAB Data Structure

### Input File Organization
**File Structure** (detailed in `umich_2021_mat_structure.md`):
```matlab
% Subject file structure (e.g., S01_data.mat)
S01_data.mat:
  .subject_info
    .height_m
    .weight_kg
    .age_years
    .gender
  .conditions
    .level_0deg
      .kinematics
        .hip_flexion_angle_deg
        .knee_flexion_angle_deg
        .ankle_flexion_angle_deg
      .kinetics
        .hip_moment_Nm
        .knee_moment_Nm
        .ankle_moment_Nm
      .forces
        .vertical_grf_N
        .ap_grf_N
        .ml_grf_N
      .temporal
        .time_s
        .gait_events
    .incline_5deg
      % Same structure as level_0deg
    .decline_5deg
      % Same structure as level_0deg
```

### Variable Mapping
**Original MATLAB → Standardized Naming**:
```matlab
% Joint angles
hip_flexion_angle_deg → hip_flexion_angle_right_rad
knee_flexion_angle_deg → knee_flexion_angle_right_rad
ankle_flexion_angle_deg → ankle_flexion_angle_right_rad

% Joint moments  
hip_moment_Nm → hip_moment_right_Nm
knee_moment_Nm → knee_moment_right_Nm
ankle_moment_Nm → ankle_moment_right_Nm

% Ground reaction forces
vertical_grf_N → vertical_grf_N
ap_grf_N → ap_grf_N
ml_grf_N → ml_grf_N
```

### Unit Conversions
**Required Conversions**:
- **Angles**: degrees → radians (`deg * pi/180`)
- **Moments**: May require body weight normalization
- **Forces**: Typically already in Newtons
- **Time**: Ensure consistent time base (seconds)

## MATLAB Requirements and Setup

### MATLAB Version Requirements
- **Minimum**: MATLAB R2019b
- **Recommended**: MATLAB R2021a or later
- **Required toolboxes**: Signal Processing Toolbox for filtering and analysis

### Required MATLAB Functions
**Built-in Functions Used**:
- `load()` - Loading .mat files
- `fieldnames()` - Structure field extraction
- `interp1()` - Spline interpolation for phase normalization
- `findpeaks()` - Gait event detection
- `table()` - Data organization

**Custom Functions Needed**:
```matlab
function [hs, to] = detect_gait_events(vgrf, time)
    % Heel strike detection using vertical GRF
    threshold = 0.1 * max(vgrf);  % 10% of max GRF
    [~, hs_idx] = findpeaks(vgrf, 'MinPeakHeight', threshold, 'MinPeakDistance', 100);
    hs = time(hs_idx);
    
    % Toe-off detection (simplified)
    [~, to_idx] = findpeaks(-vgrf, 'MinPeakHeight', -threshold, 'MinPeakDistance', 50);
    to = time(to_idx);
end
```

### Python Integration for Parquet Export
**MATLAB-Python Interface**:
```matlab
function export_to_parquet(data, filename)
    % Convert MATLAB table to Python pandas DataFrame
    py.importlib.import_module('pandas');
    
    % Convert data types appropriately
    for col = 1:width(data)
        if isnumeric(data{:,col})
            data_py.(data.Properties.VariableNames{col}) = py.numpy.array(data{:,col});
        else
            data_py.(data.Properties.VariableNames{col}) = py.list(data{:,col});
        end
    end
    
    % Create DataFrame and export
    df = py.pandas.DataFrame(data_py);
    df.to_parquet(filename, pyargs('index', false));
end
```

## Quality Control and Validation

### Data Quality Checks
**Automated Validation**:
- **Completeness**: Verify all subjects have all conditions
- **Range validation**: Check joint angles within physiological ranges
- **Temporal consistency**: Ensure proper time progression
- **Event detection quality**: Validate gait event detection

**MATLAB Quality Control**:
```matlab
function validate_conversion_quality(original_data, converted_data)
    % Check data preservation
    original_cycles = count_gait_cycles(original_data);
    converted_cycles = height(converted_data) / 150;  % 150 points per cycle
    
    if abs(original_cycles - converted_cycles) > 0.1
        warning('Gait cycle count mismatch detected');
    end
    
    % Validate joint angle ranges
    validate_joint_ranges(converted_data);
    
    % Check phase normalization quality
    validate_phase_normalization(converted_data);
end
```

### Visual Validation
**Verification Notebook**: `verify_umich_data.ipynb`
- Python-based verification of MATLAB conversion outputs
- Statistical comparison of time vs phase-indexed data
- Visualization of phase normalization quality
- Cross-subject consistency checks

## Integration with Project Components

### With Validation System
- **Standard validation**: Uses `../../tests/validation_blueprint.py`
- **Incline-specific rules**: Validation rules for inclined walking biomechanics
- **MATLAB-specific checks**: Validation of MATLAB conversion process

### With Analysis Libraries
- **Python compatibility**: Outputs compatible with `../../lib/python/locomotion_analysis.py`
- **MATLAB analysis**: Can be analyzed using `../../lib/matlab/LocomotionData.m`
- **Cross-platform**: Supports both Python and MATLAB analysis workflows

### With Documentation
- **README**: `readme.md` - MATLAB usage and data structure
- **Data structure**: `umich_2021_mat_structure.md` - detailed input format
- **Dataset docs**: `../../../docs/datasets_documentation/dataset_umich_2021.md`

## Common Issues and Troubleshooting

### MATLAB-Specific Issues
**Installation Problems**:
- Missing Signal Processing Toolbox
- MATLAB-Python interface configuration issues
- Version compatibility problems

**Data Loading Issues**:
- Corrupted .mat files
- Inconsistent data structures
- Memory limitations with large datasets

### Conversion Issues
**Phase Normalization Problems**:
- Poor gait event detection in noisy data
- Inconsistent cycle lengths
- Interpolation artifacts

**Solutions**:
```matlab
% Improve gait event detection
function improved_heel_strike_detection(vgrf, time)
    % Apply smoothing filter first
    filtered_vgrf = smoothdata(vgrf, 'gaussian', 10);
    
    % Use adaptive threshold
    threshold = 0.1 * mean(maxk(filtered_vgrf, 5));
    
    % Detect with minimum distance constraint
    [~, hs_idx] = findpeaks(filtered_vgrf, 'MinPeakHeight', threshold, 'MinPeakDistance', 0.8*mean_cycle_length);
end
```

### Output Validation Issues
**Common Validation Failures**:
- Unit conversion errors (degrees vs radians)
- Sign convention problems
- Missing or incorrect metadata

**Debugging Tools**:
- Use verification notebook for detailed output analysis
- Compare with expected biomechanical patterns
- Visual inspection of phase normalization results

## Best Practices for Claude Code

### When Working with UMich 2021 Data
1. **Use MATLAB environment**: This dataset requires MATLAB for conversion
2. **Check toolbox availability**: Verify Signal Processing Toolbox is installed
3. **Validate data structure**: Review `umich_2021_mat_structure.md` before processing
4. **Test with single subject**: Verify pipeline with one subject before batch processing
5. **Monitor phase quality**: Carefully validate phase normalization results

### MATLAB Development Guidelines
- **Modular functions**: Break conversion into smaller, testable functions
- **Error handling**: Implement robust error checking for missing data
- **Memory management**: Clear variables to manage memory with large datasets
- **Documentation**: Comment MATLAB code thoroughly for future maintenance

### Integration Considerations
- **Python verification**: Always verify MATLAB outputs using Python notebook
- **Cross-platform testing**: Test outputs in both MATLAB and Python environments
- **Version control**: Track MATLAB code changes carefully
- **Reproducibility**: Document exact MATLAB version and toolbox versions used

This UMich 2021 conversion represents a MATLAB-centric processing pipeline for high-quality treadmill locomotion data, requiring careful attention to MATLAB environment setup and phase normalization quality control.