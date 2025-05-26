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

All conversion scripts output to the `converted_datasets/` folder in the project root.

#### AddBiomechanics Dataset
```bash
# Convert B3D files to standardized parquet format
python source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py
# Output: converted_datasets/<dataset_name>.parquet

# Add phase information to existing parquet files
python source/conversion_scripts/AddBiomechanics/add_phase_info.py

# Add task information
python source/conversion_scripts/AddBiomechanics/add_task_info.py
```

#### Georgia Tech 2023 Dataset
```bash
# Convert all subjects (configure base_path in script first)
python source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py
# Output: converted_datasets/gtech_2023_time.parquet

# Convert individual subject
python source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py AB01
# Output: converted_datasets/gtech_2023_time_AB01.parquet

# Combine individual subjects efficiently
python source/conversion_scripts/Gtech_2023/combine_subjects_efficient.py
# Output: converted_datasets/gtech_2023_time.parquet

# Phase-based conversion (MATLAB)
matlab -batch "cd('source/conversion_scripts/Gtech_2023'); convert_gtech_phase_to_parquet"
# Output: converted_datasets/gtech_2023_phase.parquet
```

#### UMich 2021 Dataset
```bash
# Run MATLAB scripts for conversion
matlab -batch "cd('source/conversion_scripts/Umich_2021'); convert_umich_time_to_parquet"
# Output: converted_datasets/umich_2021_time.parquet

matlab -batch "cd('source/conversion_scripts/Umich_2021'); convert_umich_phase_to_parquet"
# Output: converted_datasets/umich_2021_phase.parquet
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

#### Variable Naming Pattern (TRANSITION IN PROGRESS)

**Current Implementation (being phased out):**
`<joint>_<measurement>_<plane>_<side>`
- Joints: `hip`, `knee`, `ankle`
- Measurements: `angle`, `vel`, `torque`
- Planes: `s` (sagittal), `f` (frontal), `t` (transverse)
- Sides: `r` (right), `l` (left)
Examples: `hip_angle_s_r`, `knee_torque_s_l`, `ankle_vel_f_r`

**New Convention (target - as per docs/standard_spec/units_and_conventions.md):**
`<joint>_<motion>_<measurement>_<side>_<unit>`
- Full descriptive motion terms: `flexion`, `adduction`, `rotation`
- Measurements: `angle`, `velocity`, `moment`
- Sides: `right`, `left` (as suffixes before units)
- Units appended: `_rad`, `_rad_s`, `_Nm`
Examples: `hip_flexion_angle_right_rad`, `knee_moment_left_Nm`, `ankle_flexion_velocity_right_rad_s`

**Mapping Tool Available:**
Use `source/naming_convention_mapping.py` for conversion between old and new names.

**Status:** 
- ~23 files need updating (18 Python, 5 MATLAB)
- Conversion scripts, visualization tools, and library code all use old convention
- Migration in progress as of January 2025

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
- Dataset-specific information

Key files to reference:
- `docs/standard_spec/phase_calculation.md` - Phase normalization requirements
- `docs/standard_spec/standard_spec.md` - Overall data format specification
- `docs/standard_spec/sign_conventions.md` - Biomechanical sign conventions
- `docs/standard_spec/units_and_conventions.md` - Units and naming conventions
- `docs/standard_spec/datasets_glossary.md` - Summary of all available datasets
- `docs/standard_spec/dataset_template.md` - Template for documenting new datasets
- `docs/standard_spec/dataset_umich_2021.md` - UMich 2021 dataset details
- `docs/standard_spec/dataset_gtech_2023.md` - GTech 2023 dataset details

### Dataset Documentation
When adding new datasets or updating existing ones:
1. Use `dataset_template.md` to create comprehensive documentation
2. Update `datasets_glossary.md` with a summary entry
3. Keep all dataset documentation files synchronized with actual data

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

## Project Organization

### Plot Output Structure
All visualization outputs should be saved in `source/visualization/plots/` with descriptive subdirectories:

```
source/visualization/plots/
├── validated_<dataset>_<year>/     # Validation plots showing invalid cycles in red
├── comprehensive_<dataset>_<year>/ # All features organized by type
└── <analysis_type>_<dataset>_<year>/  # Other analysis-specific plots
```

**Important Guidelines:**
- Never save plots in the project root directory
- Always include dataset name and year in directory names (e.g., `gtech_2023`, `umich_2021`)
- Use lowercase with underscores for directory names
- Clean up test outputs after validation
- Document new plot types in the visualization script that generates them