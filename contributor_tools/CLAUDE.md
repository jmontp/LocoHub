# CLAUDE.md - Contributor Tools

## Overview

Tools and utilities for dataset contributors to convert, validate, and tune biomechanical datasets for the standardization framework.

## Purpose

**Enable dataset contribution**. These tools help research teams convert their proprietary data formats to the standardized parquet format and validate compliance with biomechanical expectations.

## Directory Structure

```
contributor_tools/
├── conversion_scripts/         # Dataset-specific conversion scripts
│   ├── Umich_2021/            # University of Michigan dataset
│   ├── Gtech_2023/            # Georgia Tech dataset
│   └── AddBiomechanics/      # Stanford AddBiomechanics format
├── validation_ranges/          # YAML validation specifications
│   ├── default_ranges.yaml    # Standard validation ranges
│   └── custom_ranges.yaml     # Dataset-specific overrides
├── create_dataset_validation_report.py  # Full validation reports with plots
├── quick_validation_check.py            # Fast text-only validation
└── interactive_validation_tuner.py      # GUI for tuning validation ranges
```

## Core Tools

### create_dataset_validation_report.py
- **Purpose**: Generate comprehensive validation reports with plots
- **Usage**: 
  ```bash
  python create_dataset_validation_report.py --dataset converted_datasets/umich_2021_phase.parquet
  ```
- **Output**: 
  - Markdown report in `docs/reference/datasets_documentation/validation_reports/`
  - PNG plots with pass/fail visualization
  - Automatic documentation index update
- **Options**:
  - `--ranges-file`: Use custom validation ranges YAML

### quick_validation_check.py
- **Purpose**: Fast, lightweight validation without plot generation
- **Features**:
  - Text-only output for rapid feedback
  - Pass/fail statistics by task and feature type
  - Categorized failures (kinematics, kinetics, GRF, segments)
  - Verbose mode for detailed feature analysis
  - Exit code indicates validation success (0) or failure (1)
- **Usage**:
  ```bash
  # Basic validation check
  python quick_validation_check.py converted_datasets/gtech_2021_phase.parquet
  
  # With custom validation ranges
  python quick_validation_check.py dataset.parquet --ranges custom_ranges.yaml
  
  # Verbose mode with detailed analysis
  python quick_validation_check.py dataset.parquet --verbose
  ```
- **Output**: Console-only summary showing:
  - Overall pass rate (stride-level)
  - Task-by-task breakdown
  - Feature failures grouped by type
  - Summary statistics

### interactive_validation_tuner.py
- **Purpose**: Visual GUI for tuning validation ranges
- **Features**:
  - Side-by-side pass/fail stride visualization
  - Draggable validation boxes for real-time adjustment
  - Toggle between radians and degrees
  - Export tuned ranges to YAML
- **Usage**:
  ```bash
  python interactive_validation_tuner.py
  ```
- **Workflow**:
  1. Load dataset and current validation ranges
  2. Visually adjust min/max boxes
  3. See validation results update in real-time
  4. Save tuned ranges for use in reports

## Conversion Scripts

### Standard Structure
Each dataset converter should:
1. Read raw data files (CSV, MAT, C3D, etc.)
2. Extract heel strikes or gait events
3. Interpolate to 150 points per cycle
4. Apply naming conventions (ipsi/contra or left/right)
5. Output phase-indexed parquet file

### Example: Umich_2021
```matlab
% convert_umich_phase_to_parquet.m
- Loads OpenSim outputs
- Processes heel strike events
- Generates 150-point cycles
- Handles coordinate transformations
- Outputs standardized parquet
```

### Required Output Columns
- **Metadata**: `subject`, `task`, `step`
- **Phase**: `phase_ipsi`, `phase_contra` (0-1 normalized)
- **Kinematics**: Joint angles in radians with `_rad` suffix
- **Kinetics**: Joint moments in Nm with `_Nm` suffix
- **Optional**: GRF, COP, segment angles

## Validation Ranges

### default_ranges.yaml Structure
```yaml
tasks:
  level_walking:
    only_sagittal_ipsi: true  # Auto-generate contra features
    0:  # Phase percentage
      knee_flexion_angle_ipsi_rad:
        min: 0.0
        max: 0.3
    25:
      knee_flexion_angle_ipsi_rad:
        min: 0.2
        max: 0.6
```

### Key Features
- **Arbitrary Phase Points**: Not limited to 0/25/50/75
- **Auto-Contralateral**: Set `only_sagittal_ipsi: true` to auto-generate
- **Task-Specific**: Different ranges per task
- **Extensible**: Add new variables as needed

### Tuning Workflow
1. Start with `default_ranges.yaml`
2. Use `interactive_validation_tuner.py` to adjust
3. Export to `custom_ranges.yaml`
4. Generate report with custom ranges

## Common Conversion Patterns

### MATLAB to Parquet
```matlab
% Standard pattern for MATLAB converters
num_points_per_step = 150;
phase_percent = linspace(0, 100, num_points_per_step)';

% Interpolate to standard phase
for step_idx = 1:num_steps
    time_interp = linspace(step_start, step_end, num_points_per_step)';
    knee_angle_interp = interp1(raw_time, raw_knee_angle, time_interp);
end

% Write to parquet
parquetwrite(output_file, combined_data);
```

### Python to Parquet
```python
import pandas as pd
import numpy as np

# Standard phase array
phase_percent = np.linspace(0, 100, 150)

# Interpolate data
from scipy.interpolate import interp1d
f = interp1d(raw_time, raw_data, kind='linear')
interpolated = f(time_interp)

# Save to parquet
df.to_parquet('output_phase.parquet', engine='pyarrow')
```

## Validation Best Practices

### Initial Validation
1. Run quick check for immediate feedback (`quick_validation_check.py`)
2. Generate full report with plots for visual review
3. Check for systematic biases

### Range Refinement
1. Use interactive tuner for problem variables
2. Consider population characteristics
3. Document any dataset-specific issues

### Quality Metrics
- **>90% Pass Rate**: Excellent quality
- **70-90% Pass Rate**: Acceptable with notes
- **<70% Pass Rate**: Needs investigation

## Contributing a New Dataset

### Step-by-Step Process
1. **Create Conversion Script**
   - New folder in `conversion_scripts/YourDataset/`
   - Follow existing patterns (see Umich_2021)
   - Document data sources and assumptions

2. **Convert to Parquet**
   - Generate both time and phase versions if possible
   - Ensure 150 points per cycle for phase data
   - Use standard variable naming

3. **Validate Dataset**
   ```bash
   # Quick check first
   python quick_validation_check.py your_dataset_phase.parquet
   
   # Then full report if needed
   python create_dataset_validation_report.py --dataset your_dataset_phase.parquet
   ```

4. **Tune Ranges if Needed**
   - Use interactive tuner for adjustments
   - Document rationale for custom ranges
   - Save as `your_dataset_ranges.yaml`

5. **Submit for Review**
   - Include conversion script
   - Provide validation report
   - Document any limitations

## Troubleshooting

### Common Issues

**Missing Variables**
- Not all datasets have all variables
- Validator handles gracefully with NaN
- Document what's available

**Phase Alignment**
- Ensure exactly 150 points per cycle
- Check heel strike detection accuracy
- Verify ipsi/contra assignment

**Unit Conversions**
- Angles must be in radians (not degrees)
- Moments in Nm (not Nm/kg initially)
- Document any unit transformations

### Debug Tools
```python
# Check dataset structure
from user_libs.python.locomotion_data import LocomotionData
data = LocomotionData('your_dataset.parquet')
print(data.features)  # Available variables
print(data.get_tasks())  # Available tasks
print(data.df.shape)  # Dataset dimensions
```

## Future Enhancements

- Automated conversion from C3D files
- Web-based validation interface
- Cloud-based conversion pipeline
- Automated quality scoring

---

*These tools enable the community to contribute standardized datasets. Maintain clear examples and documentation.*