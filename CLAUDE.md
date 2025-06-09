# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Locomotion Data Standardization** project - a framework for converting, validating, and analyzing biomechanical locomotion data from various research datasets into a standardized Parquet-based format.

## 📋 Project Management & Status

**CRITICAL**: Always check and update [`PROJECT_MANAGEMENT.md`](PROJECT_MANAGEMENT.md) when working on this repository.

**Current Focus**: 🚀 **Validation System Biomechanically Verified** (COMPLETED)
**Current Step**: Phase progression validation with bilateral visualization system complete
**Last PM Update**: 2025-06-08
**Next Milestone**: Ready for major architectural changes

### Update Requirements:
- 🔴 **UPDATE PROJECT_MANAGEMENT.md FREQUENTLY** - Whenever work status changes
- Update triggers: Phase completion, significant progress, new blockers, timeline changes
- Include: Progress percentages, current blockers, next action items, risk assessment
- Capture enough context information to resume work after clearing conversation context

### Key Directories
- `source/` - Core library and conversion scripts
- `docs/` - Documentation, tutorials, and specifications  
- `converted_datasets/` - Output directory for standardized datasets
- `scripts/` - Utility scripts for validation and analysis
- `PROJECT_MANAGEMENT.md` - **Current goals, status, and next steps**

## Complete Folder Structure

```
locomotion-data-standardization/
├── 📁 source/
│   ├── conversion_scripts/
│   │   ├── AddBiomechanics/           # OpenSim/AddBiomechanics dataset conversion
│   │   │   ├── README.md             # Conversion instructions and usage
│   │   │   ├── requirements.txt      # Python dependencies (nimblephysics, torch)
│   │   │   ├── convert_addbiomechanics_to_parquet.py  # Main B3D→Parquet converter
│   │   │   ├── add_phase_info.py     # Phase normalization (150 pts/cycle)
│   │   │   ├── add_task_info.py      # Task metadata standardization
│   │   │   ├── b3d_to_parquet.py     # Core B3D file parser
│   │   │   └── Gtech_2021/           # Specific GTech 2021 subset processing
│   │   │       ├── add_task_info.py
│   │   │       └── validate_dataset.py
│   │   ├── Gtech_2023/               # Georgia Tech 2023 dataset conversion
│   │   │   ├── readme.md             # Dataset-specific conversion guide
│   │   │   ├── convert_gtech_all_to_parquet.py      # Main conversion script
│   │   │   ├── combine_subjects_efficient.py        # Subject file merger
│   │   │   ├── process_all_subjects.sh              # Batch processing
│   │   │   ├── RawData/              # Raw input data (not in repo)
│   │   │   │   ├── AB01/ to AB13/    # Subject directories
│   │   │   │   └── Subject_masses.csv
│   │   │   ├── Plots/                # Validation and alignment plots
│   │   │   │   └── AlignmentChecks_RawHS/
│   │   │   └── utilities/            # Helper scripts and benchmarks
│   │   │       ├── convert_gtech_rotm_to_eul_csv.m
│   │   │       ├── plot_leg_alignment.m
│   │   │       └── benchmark_processing.m
│   │   ├── Umich_2021/               # University of Michigan 2021 dataset
│   │   │   ├── readme.md             # MATLAB-based conversion guide
│   │   │   ├── umich_2021_mat_structure.md          # Input data format
│   │   │   ├── convert_umich_time_to_parquet.m      # Time-indexed conversion
│   │   │   ├── convert_umich_phase_to_parquet.m     # Phase-indexed conversion
│   │   │   └── R01 Dataset README.pdf               # Original documentation
│   │   └── CONSOLIDATION_PLAN.md     # Future conversion consolidation
│   ├── lib/                          # Core analysis libraries
│   │   ├── python/                   # Python implementation
│   │   │   └── locomotion_analysis.py # Main LocomotionData class
│   │   └── matlab/                   # MATLAB implementation
│   │       └── LocomotionData.m      # MATLAB LocomotionData class
│   ├── tests/                        # Validation and testing
│   │   ├── validation_blueprint.py           # Basic 5-layer validator
│   │   ├── validation_blueprint_enhanced.py  # Enhanced multi-error validator
│   │   └── validation_blueprint_enhanced.py  # Advanced validation features
│   └── visualization/                # Plotting and animation tools
│       ├── mozaic_plot.py           # Multi-task comparison plots
│       ├── mosaic_plot_validated.py # Validation-integrated plotting
│       ├── mosaic_plot_with_validation.py   # Validation overlay plots
│       ├── mosaic_plot_with_failure_analysis.py # Error analysis plots
│       ├── walking_animator.py      # Animated stick figure generator
│       ├── refresh_validation_gifs.py        # GIF regeneration utility
│       ├── phase_progression_plots.py       # **NEW:** Phase progression validation plots
│       ├── joint_validation_plots.py       # **NEW:** Static joint validation plots
│       ├── kinematic_pose_generator.py     # **UPDATED:** Bilateral pose visualization
│       └── plots/                   # Generated plot outputs
│           ├── comprehensive_gtech_2023/    # Task-specific plots
│           └── validated_gtech_2023/        # Validation-filtered plots
├── 📁 docs/
│   ├── README.md                     # Documentation overview
│   ├── datasets_documentation/       # Dataset-specific documentation
│   │   ├── datasets_glossary.md      # Overview of all datasets
│   │   ├── dataset_addbiomechanics.md # AddBiomechanics implementation
│   │   ├── dataset_gtech_2023.md     # Georgia Tech 2023 implementation
│   │   └── dataset_umich_2021.md     # UMich 2021 implementation
│   ├── development/                  # Development documentation
│   │   ├── NAMING_CONVENTION_UPDATE_SUMMARY.md # Variable naming evolution
│   │   └── PROGRESS_TRACKING.md      # Project status and milestones
│   ├── standard_spec/                # Format specifications
│   │   ├── standard_spec.md          # Primary format specification
│   │   ├── validation_expectations.md # **UPDATED:** Biomechanically verified validation ranges v4.0
│   │   ├── sign_conventions.md       # Joint angle sign definitions
│   │   ├── units_and_conventions.md  # Units and coordinate systems
│   │   ├── phase_calculation.md      # Phase normalization methodology
│   │   ├── task_definitions.md       # Standardized task vocabulary
│   │   ├── task_vocabulary.md        # Task naming conventions
│   │   ├── dataset_template.md       # Template for new datasets
│   │   ├── consolidated_test_matrix.md # Validation test cases
│   │   ├── research_into_test_matrix.md # Test development research
│   │   ├── sign_convention_verification_report.md # **NEW:** Bilateral pose correction documentation
│   │   ├── biomechanical_verification_report.md # **NEW:** Literature-based range verification
│   │   └── kinematic_visualization_guide.md # **NEW:** Guide for interpreting validation plots
│   ├── tutorials/                    # Step-by-step usage guides
│   │   ├── README.md                 # Tutorial overview
│   │   ├── TESTING_STATUS.md         # Tutorial validation status
│   │   ├── python/                   # Python tutorials
│   │   │   ├── getting_started_python.md       # Basic Python usage
│   │   │   ├── library_tutorial_python.md      # Advanced library features
│   │   │   ├── efficient_reshape_guide.md      # 3D array optimization
│   │   │   ├── efficient_data_access.py        # Performance examples
│   │   │   ├── efficient_reshape_3d.py         # 3D array examples
│   │   │   └── test_library.py                 # Test scripts
│   │   ├── matlab/                   # MATLAB tutorials
│   │   │   ├── getting_started_matlab.md       # Basic MATLAB usage
│   │   │   ├── library_tutorial_matlab.md      # Advanced library features
│   │   │   ├── test_library_tutorial.m         # MATLAB test scripts
│   │   │   ├── test_matlab_tutorial.m          # Tutorial validation
│   │   │   └── check_syntax.py                 # MATLAB syntax checker
│   │   └── test_files/               # Tutorial test data
│   │       ├── locomotion_data.csv   # Sample data
│   │       ├── task_info.csv         # Sample metadata
│   │       └── *.png                 # Reference plots
│   └── goal.txt                      # Project objectives
├── 📁 scripts/                       # Utility and validation scripts
│   ├── validate_all_datasets.sh      # Automated validation pipeline
│   ├── memory_safe_validator.py      # Large file validation
│   ├── generate_validation_gifs.py   # Visual validation animations
│   ├── comprehensive_mosaic_plot.py  # Advanced plotting script
│   ├── mosaic_plot_3d_efficient.py   # Optimized 3D plotting
│   ├── quick_phase_check.py          # Fast phase validation
│   ├── check_file_structure.py       # File structure verification
│   ├── check_parquet_structure.py    # Parquet schema validation
│   ├── compare_plotting_performance.py # Performance benchmarking
│   ├── add_step_numbers.py           # Utility for step counting
│   ├── update_validation_table_format.py  # **NEW:** Automated degree format conversion
│   └── update_validation_images.py   # **NEW:** Batch validation image generation
├── 📁 converted_datasets/            # Output directory for standardized data
│   └── (Generated .parquet files)    # Time and phase-indexed datasets
├── 📁 assets/                        # Documentation assets
│   └── joint_angle_references.png    # Sign convention diagrams
├── 📁 validation_images/             # **NEW:** Generated validation visualization
│   ├── *_phase_00_range.png          # Phase 0% (heel strike) validation images
│   ├── *_phase_33_range.png          # Phase 33% (mid-stance) validation images
│   ├── *_phase_50_range.png          # Phase 50% (push-off) validation images
│   ├── *_phase_66_range.png          # Phase 66% (mid-swing) validation images
│   ├── *_phase_progression.png       # Phase progression validation plots
│   ├── hip_validation_ranges.png     # Hip joint validation overview
│   ├── knee_validation_ranges.png    # Knee joint validation overview
│   └── ankle_validation_ranges.png   # Ankle joint validation overview
├── 📁 validation_reports/            # Generated validation outputs
│   └── (Timestamped reports)         # Validation logs and summaries
├── 📁 conda_env/                     # Conda environment (if used)
├── 📁 venv/                         # Python virtual environment (if used)
├── CLAUDE.md                         # This file - Claude Code guidance
├── CLAUDE.local.md                   # Local user preferences (not tracked)
├── README.md                         # Main project documentation
├── CONTRIBUTING.md                   # Contribution guidelines
└── LICENSE                          # MIT License
```

## Common Commands

### Git Guidelines
- Never "git add -A", just add the files that you edit
- Always add co-author information when committing
- For current date information, always use Python: `python3 -c "import datetime; print(datetime.datetime.now().strftime('%Y-%m-%d'))"`

### Python Environment Setup
```bash
# Install dependencies for AddBiomechanics conversion
cd source/conversion_scripts/AddBiomechanics
pip install -r requirements.txt

# Key dependencies: nimblephysics, torch, pandas, pyarrow, numpy, matplotlib
```

### Running Validation
```bash
# Validate all datasets
./scripts/validate_all_datasets.sh

# Memory-safe validation for large files
python scripts/memory_safe_validator.py

# Enhanced validation with detailed reporting
python source/tests/validation_blueprint_enhanced.py
```

## Dataset Conversion Scripts

### 1. AddBiomechanics Dataset
**Location**: `source/conversion_scripts/AddBiomechanics/`
**Main README**: `source/conversion_scripts/AddBiomechanics/README.md`
**Implementation Details**: `docs/datasets_documentation/dataset_addbiomechanics.md`

**Key Scripts**:
- `convert_addbiomechanics_to_parquet.py` - Main conversion from B3D format
- `add_phase_info.py` - Adds phase normalization (150 points/cycle) 
- `add_task_info.py` - Adds task metadata and standardized naming
- `b3d_to_parquet.py` - Core B3D file parser

**Requirements**: `requirements.txt` (includes nimblephysics, torch)
**Usage**: Converts 3D biomechanics data from OpenSim/AddBiomechanics format

### 2. Georgia Tech 2023 Dataset
**Location**: `source/conversion_scripts/Gtech_2023/`
**Main README**: `source/conversion_scripts/Gtech_2023/readme.md`
**Implementation Details**: `docs/datasets_documentation/dataset_gtech_2023.md`

**Key Scripts**:
- `convert_gtech_all_to_parquet.py` - Main conversion script for all subjects
- `combine_subjects_efficient.py` - Merges individual subject files
- `process_all_subjects.sh` - Batch processing script

**Input Data Structure**:
- `RawData/AB01/` to `RawData/AB13/` - Subject directories
- `Subject_masses.csv` - Body mass metadata
- MATLAB `.mat` files with kinematic/kinetic data

**Output**: Both time-indexed and phase-indexed Parquet files

### 3. University of Michigan 2021 Dataset  
**Location**: `source/conversion_scripts/Umich_2021/`
**Main README**: `source/conversion_scripts/Umich_2021/readme.md`
**Implementation Details**: `docs/datasets_documentation/dataset_umich_2021.md`
**Data Structure**: `source/conversion_scripts/Umich_2021/umich_2021_mat_structure.md`

**Key Scripts** (MATLAB):
- `convert_umich_time_to_parquet.m` - Time-indexed conversion
- `convert_umich_phase_to_parquet.m` - Phase-indexed conversion

**Requirements**: MATLAB R2019b+ with Signal Processing Toolbox
**Input**: `.mat` files with treadmill walking data at various inclines

## Current Validation System State

### 🚀 **COMPLETED** (2025-06-08): Comprehensive Phase Progression Validation System
**Location**: `source/tests/` and `source/visualization/`

**MAJOR UPDATE**: **Phase Progression Validation System** - Complete bilateral visualization framework
- ✅ **Phase progression plots** - `phase_progression_plots.py` with temporal validation visualization
- ✅ **Shared y-axis scaling** - Bilateral comparison across rows (hip, knee, ankle)
- ✅ **Enhanced validation expectations** - Degree format annotations "0.15 (9°)" for readability
- ✅ **Biomechanically verified ranges** - All 9 tasks verified against literature (v4.0)
- ✅ **Bilateral kinematic validation** - 36 phase-specific images (4 phases × 9 tasks)
- ✅ **Dynamic visualization** - 9 phase progression plots showing temporal evolution
- ✅ **Task-specific integration** - Plots distributed to individual task sections

**Previous**: **Intuitive Validation System** - `validation_intuitive_biomechanics.py`
- ✅ **Independent task expectations** - No baseline inheritance, standalone descriptions
- ✅ **Step-level debugging** - Pinpoint exact failing data points (Subject_Task_Phase)
- ✅ **Comprehensive fix suggestions** - Actionable debugging guidance
- ✅ **Language model integration** - Structured outputs for automated debugging
- ✅ **Clinical validation** - Phase-based expectations (heel strike 0-10%, mid-stance 45-55%)
- ✅ **Cyclic task focus** - Only validates tasks with meaningful phase relationships

**Demo Script**: `demo_intuitive_validation.py` - Shows complete debugging workflow

### Core Validation Modules (Existing)

1. **Basic Validator**: `validation_blueprint.py`
   - Single error mode (stops at first failure)
   - 5-layer validation system
   - Error codes 0-70

2. **Enhanced Validator**: `validation_blueprint_enhanced.py`  
   - Comprehensive mode (collects all errors)
   - Detailed error reporting
   - Human-readable descriptions
   - CSV export capabilities

### Validation Layers (Traditional System)
1. **Pre-checks** (Codes 1-9): Column existence, naming conventions, vocabulary
2. **Layer 0** (Codes 10-29): Global sanity checks (ranges, units, monotonicity) 
3. **Layer 1-2** (Codes 30-49): Biomechanical envelopes (baseline + task-specific)
4. **Layer 3** (Codes 50-59): Physics consistency (power analysis, cross-variable)
5. **Layer 4** (Codes 60-69): Subject heuristics (neutral pose, stance detection)

### Current Testing Status
- ✅ **Intuitive validation implemented** with step-level debugging
- ✅ **Phase progression validation complete** with bilateral visualization
- ✅ **Biomechanical verification complete** - All ranges validated against literature
- ✅ **Enhanced visualization system** - 45 validation images generated (36 phase-specific + 9 progression plots)
- ✅ **Documentation integration** - Plots distributed to task-specific sections
- ✅ **System ready for deployment** - Comprehensive validation framework operational

### Key Generated Reports
- `biomechanical_expectations.csv` - Complete expectations table
- `debug_report_bug_fix_guide.csv` - Prioritized issues with fix suggestions
- `debug_report_step_errors.csv` - Individual failing data points
- `debug_report_subject_summary.csv` - Per-subject error overview

### Validation Scripts
- `scripts/validate_all_datasets.sh` - Automated pipeline for all datasets
- `scripts/memory_safe_validator.py` - Chunk-based validation for large files
- `scripts/generate_validation_gifs.py` - Visual validation animations

## Data Format Specifications

### Primary Specification
**Location**: `docs/standard_spec/standard_spec.md`
- Complete format specification  
- Variable naming conventions
- Metadata handling (split vs monolithic)
- Schema definitions

### Supporting Specifications  
- `docs/standard_spec/sign_conventions.md` - Joint angle sign definitions
- `docs/standard_spec/units_and_conventions.md` - Units and coordinate systems
- `docs/standard_spec/phase_calculation.md` - Phase normalization methodology
- `docs/standard_spec/task_definitions.md` - Standardized task vocabulary
- **NEW**: `docs/standard_spec/intuitive_validation_spec.md` - Intuitive validation system specification
- **NEW**: `docs/standard_spec/step_level_debugging_guide.md` - Step-level debugging workflow guide

### Variable Naming Convention
Pattern: `<joint>_<motion>_<measurement>_<side>_<unit>`
- Examples: `knee_flexion_angle_right_rad`, `hip_moment_left_Nm`
- Required units: `_rad`, `_N`, `_m`, `_s`, `_kg`, `_Nm`, `_rad_s`

## Library Code

### Python Library
**Location**: `source/lib/python/`
**Main Module**: `locomotion_analysis.py`

**Key Classes**:
- `LocomotionData` - Main data container and analysis class
- Efficient 3D array operations (100x faster than pandas groupby)
- Phase pattern analysis and visualization
- Statistical calculations and validation

### MATLAB Library  
**Location**: `source/lib/matlab/`
**Main Class**: `LocomotionData.m`
- Feature parity with Python version
- Native MATLAB integration
- Optimized for MATLAB workflows

## Visualization Tools

### Main Plotting Scripts
**Location**: `source/visualization/`

- `mozaic_plot.py` - Multi-task comparison plots
- `mosaic_plot_validated.py` - Validation-aware plotting
- `walking_animator.py` - Animated stick figure visualizations  
- `mosaic_plot_3d_efficient.py` - High-performance 3D visualizations

### Plot Output
**Location**: `source/visualization/plots/`
- Organized by dataset and validation status
- PNG exports for documentation
- Validation heatmaps and failure analysis

## Documentation Structure

### Tutorials
**Location**: `docs/tutorials/`

**Python**:
- `python/getting_started_python.md` - Basic usage guide
- `python/library_tutorial_python.md` - Advanced library features
- `python/test_library.py` - Test scripts and examples

**MATLAB**:
- `matlab/getting_started_matlab.md` - Basic usage guide  
- `matlab/library_tutorial_matlab.md` - Advanced library features
- `matlab/test_library_tutorial.m` - Test scripts and examples

### Dataset Documentation
**Location**: `docs/datasets_documentation/`

- `datasets_glossary.md` - Overview of all supported datasets
- `dataset_addbiomechanics.md` - AddBiomechanics implementation details
- `dataset_gtech_2023.md` - Georgia Tech 2023 implementation details  
- `dataset_umich_2021.md` - UMich 2021 implementation details

Each dataset documentation includes:
- Data source and citation information
- Conversion script locations and usage
- Specific implementation challenges
- Validation considerations
- Known limitations and missing data

### Development Documentation
**Location**: `docs/development/`

- `NAMING_CONVENTION_UPDATE_SUMMARY.md` - Variable naming evolution
- `PROGRESS_TRACKING.md` - Project milestones and status

## Testing and Quality Assurance

### Test Files
**Location**: `docs/tutorials/test_files/`
- Sample data for tutorials and testing
- Expected output files for validation
- Reference plots for visual comparison

### Validation Reports
**Location**: `validation_reports/` (generated)
- Timestamped validation runs
- Error summaries by dataset and subject
- Visual validation plots and animations

## Entry Points and Key Files

### Main Entry Points for Different Tasks

**Converting Datasets**:
- AddBiomechanics: `source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py`
- GTech 2023: `source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py`
- UMich 2021: `source/conversion_scripts/Umich_2021/convert_umich_time_to_parquet.m`

**Validation**:
- **NEW Intuitive**: `source/tests/validation_intuitive_biomechanics.py` (step-level debugging)
- **Demo**: `source/tests/demo_intuitive_validation.py` (complete workflow example)
- Comprehensive: `source/tests/validation_blueprint_enhanced.py`
- Memory-safe: `scripts/memory_safe_validator.py`
- Automated pipeline: `scripts/validate_all_datasets.sh`

**Analysis**:
- Python: `source/lib/python/locomotion_analysis.py` → `LocomotionData` class
- MATLAB: `source/lib/matlab/LocomotionData.m` → `LocomotionData` class

**Visualization**:
- Multi-task plots: `source/visualization/mozaic_plot.py`
- Animations: `source/visualization/walking_animator.py`
- Validation plots: `source/visualization/mosaic_plot_validated.py`

### Configuration and Requirements Files

**Python Dependencies**:
- `source/conversion_scripts/AddBiomechanics/requirements.txt` - Heavy dependencies (nimblephysics, torch)
- Project root likely needs: pandas, numpy, pyarrow, matplotlib, plotly

**MATLAB Requirements**:
- MATLAB R2019b+ with Signal Processing Toolbox
- No additional toolboxes required for basic functionality

**File Naming Patterns**:
- Datasets: `<dataset_name>_<time|phase>.parquet`
- Metadata: `metadata_<subject|task>.parquet`
- Monolithic: `<dataset_name>_<time|phase>_monolithic.parquet`
- Validation reports: `<dataset_name>_validation_<timestamp>.csv`

## Implementation Details by Dataset

### AddBiomechanics Implementation
**Input Format**: B3D files (OpenSim biomechanics format)
**Processing Pipeline**:
1. Parse B3D files → Extract biomechanical data
2. Apply standardized variable naming
3. Generate time-indexed Parquet files
4. Run phase detection and normalization
5. Generate phase-indexed Parquet files (150 points/cycle)

**Key Challenges**:
- Heavy dependencies (nimblephysics physics engine)
- Complex 3D biomechanics data parsing
- Multiple coordinate frame transformations

**Known Issues**: See `source/conversion_scripts/AddBiomechanics/README.md` for current limitations

### GTech 2023 Implementation  
**Input Format**: MATLAB .mat files with kinematic/kinetic data
**Processing Pipeline**:
1. Load subject data from `RawData/AB##/` directories
2. Parse kinematic angles and kinetic moments
3. Apply body mass normalization from `Subject_masses.csv`
4. Generate standardized variable names
5. Create both time and phase-indexed outputs

**Key Features**:
- 13 subjects (AB01-AB13)
- 19 different activity types
- EMG and IMU data (if available)
- Comprehensive validation plots in `Plots/AlignmentChecks_RawHS/`

**Known Issues**: Some subjects missing right-leg data, handled as NaN values

### UMich 2021 Implementation
**Input Format**: MATLAB .mat files with treadmill data
**Processing Pipeline**:
1. Load `.mat` files with incline walking data
2. Process multiple incline conditions per subject  
3. Apply OpenSim-based coordinate transformations
4. Generate separate time and phase-indexed files

**Key Features**:
- 10 subjects
- Multiple incline conditions (level, ±5°, ±10°)
- High-quality treadmill data
- MATLAB-based processing only

## Common Workflows

### Converting a New Dataset
1. Create directory in `source/conversion_scripts/<DatasetName>/`
2. Write conversion script following existing patterns
3. Create README.md with usage instructions (see existing READMEs as templates)
4. Add dataset documentation in `docs/datasets_documentation/dataset_<name>.md`
5. Test with validation system using `source/tests/validation_blueprint_enhanced.py`
6. Update main README.md and this CLAUDE.md file

### Running Full Validation Pipeline
```bash
# 1. Run automated validation (creates timestamped reports)
./scripts/validate_all_datasets.sh

# 2. Check reports in validation_reports/<timestamp>/
# 3. Review validation logs for specific error codes
# 4. Fix any validation failures in conversion scripts
# 5. Re-run validation on problematic datasets
```

### Adding New Biomechanical Variables
1. Update variable definitions in `docs/standard_spec/standard_spec.md`
2. Add validation rules in `source/tests/validation_blueprint.py` (Layer 1-2 envelopes)
3. Update library classes in `source/lib/python/locomotion_analysis.py` and `source/lib/matlab/LocomotionData.m`
4. Add visualization support in relevant `source/visualization/` scripts
5. Update tutorials in `docs/tutorials/python/` and `docs/tutorials/matlab/`
6. Add test cases and update documentation

### Debugging Validation Failures
1. **Check error codes**: Reference `source/tests/validation_blueprint.py` lines 30-69 for error definitions
2. **Run enhanced validator**: Use comprehensive mode for full error catalog
3. **Generate validation plots**: Use `source/visualization/mosaic_plot_with_failure_analysis.py`
4. **Check dataset-specific docs**: Review known limitations in `docs/datasets_documentation/`
5. **Verify input data**: Ensure raw data meets expected format from conversion README

## File Relationships and Dependencies

### Conversion Process Flow
```
Raw Data → Conversion Scripts → Standardized Parquet → Validation → Analysis/Visualization
```

### Key File Dependencies
- Conversion scripts depend on dataset-specific READMEs for input format details
- Validation scripts import from `source/tests/validation_blueprint.py`
- Visualization scripts use library classes from `source/lib/`
- All outputs follow specifications in `docs/standard_spec/`

### Cross-References
- Each conversion script README references its corresponding dataset documentation
- Dataset documentation links back to conversion script locations
- Validation results reference specific error codes defined in validation blueprints
- Tutorials reference both library code and example data files

## Troubleshooting Common Issues

### Memory Issues with Large Datasets
- Use `scripts/memory_safe_validator.py` for files >1GB
- Consider chunk-based processing in conversion scripts
- Monitor memory usage during validation

### Validation Failures
- Check `validation_blueprint.py` for specific error code meanings
- Review dataset-specific documentation for known limitations
- Use enhanced validator for detailed error reporting

### Missing Dependencies
- Check requirements.txt files in conversion script directories
- Verify Python/MATLAB version compatibility
- Install missing packages with pip/conda as appropriate

## Performance Considerations

### Optimized Operations
- Use 3D array operations for multi-subject analysis (100x speedup)
- Leverage Parquet format for efficient I/O
- Cache frequently accessed data for repeated analysis

### Large Dataset Handling
- Implement chunked processing for memory efficiency
- Use appropriate data types to minimize memory footprint
- Consider distributed processing for very large datasets

This comprehensive guide should help Claude understand the complete repository structure, relationships between components, and proper workflows for development and analysis tasks.