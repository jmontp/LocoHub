# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Python Environment Setup
```bash
# Install dependencies for AddBiomechanics conversion
cd source/conversion_scripts/AddBiomechanics
pip install -r requirements.txt

# Key dependencies: nimblephysics, torch, pandas, pyarrow, numpy, matplotlib
```

### Running Data Converters

#### AddBiomechanics Dataset
```bash
# Convert B3D files to standardized parquet format
python source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py

# Add phase information to existing parquet files
python source/conversion_scripts/AddBiomechanics/add_phase_info.py

# Add task information
python source/conversion_scripts/AddBiomechanics/add_task_info.py
```

#### Georgia Tech 2023 Dataset
```bash
# Convert all Gtech data to parquet (configure base_path in script first)
python source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py

# Time-based conversion
python source/conversion_scripts/Gtech_2023/convert_gtech_time_to_parquet.py
```

#### UMich 2021 Dataset
```bash
# Run MATLAB scripts for conversion
matlab -batch "run('source/conversion_scripts/Umich_2021/convert_umich_time_to_parquet.m')"
matlab -batch "run('source/conversion_scripts/Umich_2021/convert_umich_phase_to_parquet.m')"
```

### Visualization Tools

```bash
# Animate walking data (various options)
python source/visualization/walking_animator.py -f <parquet_file> -s <subject> -t <task>

# Save animation as GIF
python source/visualization/walking_animator.py -f <parquet_file> -s <subject> -t <task> --save-gif

# View pivot table of subjects/tasks
python source/visualization/walking_animator.py -f <parquet_file> --pivot

# Create mosaic plots
python source/visualization/mozaic_plot.py
```

### Validation
```bash
# Run validation blueprint
python source/tests/validation_blueprint.py
```

## High-Level Architecture

### Data Flow Pipeline
1. **Raw Data Sources** → 2. **Dataset-Specific Converters** → 3. **Standardized Parquet** → 4. **Validation** → 5. **Visualization/Analysis**

### Core Data Formats

#### Time-Indexed Format
- Continuous time series data at original sampling frequency
- Columns: `time_s`, biomechanical variables, `subject_id`, `task_id`
- Multiple tasks may be discontinuous in time

#### Phase-Indexed Format
- Normalized to 150 points per gait cycle
- Columns: `phase` (0-100%), biomechanical variables, `subject_id`, `task_id`
- Enables cross-subject gait cycle comparison

### Standardization Conventions

#### Variable Naming Pattern
`<joint>_<measurement>_<plane>_<side>`
- Joints: `hip`, `knee`, `ankle`
- Measurements: `angle`, `vel`, `torque`
- Planes: `s` (sagittal), `f` (frontal), `t` (transverse)
- Sides: `r` (right), `l` (left)

Examples: `hip_angle_s_r`, `knee_torque_s_l`, `ankle_vel_f_r`

#### Sign Conventions (Sagittal Plane)
- Ankle dorsiflexion: Positive
- Knee extension: Positive  
- Hip extension: Positive

### Key Processing Steps

1. **Column Standardization**: Each converter maps dataset-specific names to standard names
2. **Unit Conversion**: Angles to degrees, torques to Nm/kg (mass-normalized)
3. **Coordinate System**: Aligned to OpenSim conventions (X-forward, Y-up, Z-right)
4. **Phase Detection**: Uses kinematic peaks/zero-crossings for gait events
5. **Validation**: 5-layer system checking physics constraints and statistical bounds

### Dataset-Specific Notes

- **AddBiomechanics**: Uses nimblephysics for B3D file parsing, includes full 3D kinematics
- **Gtech 2023**: CSV-based, includes EMG and IMU data (not yet standardized)
- **UMich 2021**: MATLAB format, focuses on treadmill locomotion with inclines

### Interactive Feedback Integration
When performing tasks, use the @interactive-feedback-mcp MCP tool to get user feedback before completing requests, as specified in `.cursor/rules/interactive-feedback.mdc`.

### Documentation Context
Always keep the `/docs` folder contents in context when working on this project. The documentation contains critical information about:
- Standard specifications (e.g., 150 points per gait cycle)
- Sign conventions and coordinate systems
- Data format requirements
- Task definitions and naming conventions

Key files to reference:
- `docs/standard_spec/phase_calculation.md` - Phase normalization requirements
- `docs/standard_spec/standard_spec.md` - Overall data format specification
- `docs/standard_spec/sign_conventions.md` - Biomechanical sign conventions
- `docs/standard_spec/units_and_conventions.md` - Units and naming conventions

## Project Improvement Tracking

This project is actively improving its documentation and standards. When working on improvements:

1. **Always consult PROGRESS_TRACKING.md** - This file contains the roadmap for all planned improvements, organized in phases with specific tasks and status tracking.

2. **Update progress systematically** - When completing any task listed in PROGRESS_TRACKING.md:
   - Change status from 🔴 (Not Started) to 🟡 (In Progress) when beginning work
   - Change to 🟢 (Completed) when finished
   - Add notes about implementation details or blockers

3. **Priority order** - Focus on Phase 1 (Foundation) tasks first, particularly:
   - Visual sign convention diagrams (highest impact)
   - ISB coordinate system documentation
   - Core biomechanical variable additions

4. **Documentation improvements** should follow the new structure outlined in PROGRESS_TRACKING.md, emphasizing:
   - Visual clarity with diagrams and interactive elements
   - Biomechanical rigor with ISB standards
   - User-friendly organization with progressive disclosure