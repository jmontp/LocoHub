# CLAUDE.md

Guidance for Claude Code when working with the locomotion data standardization project.

**Quick Reference:** [Coding Philosophy](#coding-philosophy) • [File Creation](#file-creation) • [Common Commands](#common-commands)

## Repository Overview

Standardized biomechanical datasets with time-indexed and phase-indexed variants.

**Data Formats**:
- `dataset_time.parquet` - Original sampling frequency
- `dataset_phase.parquet` - 150 points per gait cycle
- Variables: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

**Validation**: Phase-indexed data only, requires exact 150 points per cycle.

## Complete File Index

### Project Root
- **CLAUDE.md** - Main guidance for Claude Code (this file)
- **CLAUDE.local.md** - User's private local instructions with custom slash commands
- **CONTRIBUTING.md** - Contribution guidelines with minimal style
- **LICENSE** - MIT license for open source distribution
- **README.md** - Repository overview and quick start guide
- **scratchpad.md** - Current work context and recent decisions (last 3 context clears)
- **scratchpad_history.md** - Archive of older context clears and project notes

### Documentation (`docs/`)
- **CLAUDE.md** - Documentation directory guidance
- **README.md** - Documentation overview
- **goal.txt** - Project goals and vision

#### Dataset Documentation (`docs/datasets_documentation/`)
- **README.md** - Consolidated dataset reference (merged from datasets_glossary.md)
- **dataset_addbiomechanics.md** - AddBiomechanics dataset implementation details
- **dataset_gtech_2023.md** - Georgia Tech 2023 dataset documentation
- **dataset_umich_2021.md** - University of Michigan 2021 dataset documentation

#### Development Notes (`docs/development/`)
- **NAMING_CONVENTION_UPDATE_SUMMARY.md** - Variable naming changes summary
- **PROGRESS_TRACKING.md** - Development progress tracking
- **biomechanical_verification_report.md** - Biomechanical validation results
- **efficient_reshape_guide.md** - Performance optimization guide
- **intuitive_validation_spec.md** - Validation system design
- **kinematic_visualization_guide.md** - Visualization best practices
- **research_into_test_matrix.md** - Testing strategy research
- **sign_convention_verification_report.md** - Sign convention validation
- **step_level_debugging_guide.md** - Debugging methodology
- **validation_expectations_changelog.md** - Validation rule change history

#### Standard Specification (`docs/standard_spec/`)
- **dataset_template.md** - Template for new dataset documentation
- **phase_calculation.md** - Gait cycle phase calculation methods
- **units_and_conventions.md** - Units, sign conventions, and typical biomechanical values
- **standard_spec.md** - Core data format specification
- **task_definitions.md** - Locomotion task taxonomy
- **validation_expectations_kinematic.md** - Kinematic validation rules and ranges
- **validation_expectations_kinetic.md** - Kinetic validation rules and ranges

##### Validation Images (`docs/standard_spec/validation/`)
- **[task]_forward_kinematics_phase_[00,25,50,75]_range.png** - Joint angle visualization at key phases
- **[task]_kinematic_filters_by_phase.png** - Phase-based kinematic validation plots
- **[task]_kinetic_filters_by_phase.png** - Phase-based kinetic validation plots

#### Tutorials (`docs/tutorials/`)
- **README.md** - Tutorial overview and testing status
- **TESTING_STATUS.md** - Tutorial validation results

##### MATLAB Tutorials (`docs/tutorials/matlab/`)
- **getting_started_matlab.md** - MATLAB quick start guide
- **library_tutorial_matlab.md** - MATLAB library comprehensive tutorial

##### Python Tutorials (`docs/tutorials/python/`)
- **getting_started_python.md** - Python quick start guide
- **library_tutorial_python.md** - Python library comprehensive tutorial

##### Test Files (`docs/tutorials/test_files/`)
- **locomotion_data.csv** - Sample dataset for tutorials
- **task_info.csv** - Task metadata sample
- **[various].png** - Tutorial output validation images

### Core Libraries (`lib/`)

#### Core Functionality (`lib/core/`)
- **locomotion_analysis.py** - Core LocomotionData class with 3D array operations
- **feature_constants.py** - Feature definitions and mappings (single source of truth)
- **examples.py** - Real-world usage examples (4 comprehensive scenarios)
- **__init__.py** - Python package initialization

#### Validation Libraries (`lib/validation/`)
- **dataset_validator_phase.py** - Phase-indexed dataset validation (main validator)
- **dataset_validator_time.py** - Time-indexed dataset validation
- **filters_by_phase_plots.py** - Phase-based validation plot generator
- **forward_kinematics_plots.py** - Joint angle visualization generator
- **generate_validation_plots.py** - Unified plot generation script (static plots)
- **generate_validation_gifs.py** - Animated GIF generation for validation
- **step_classifier.py** - Gait cycle step classification
- **validation_expectations_parser.py** - Markdown validation rule parser
- **automated_fine_tuning.py** - Validation range tuning system
- **__init__.py** - Python package initialization

### Contributor Scripts (`contributor_scripts/`)
- **CONSOLIDATION_PLAN.md** - Dataset consolidation strategy

#### AddBiomechanics (`contributor_scripts/AddBiomechanics/`)
- **CLAUDE.md** - AddBiomechanics conversion guidance
- **README.md** - AddBiomechanics conversion overview
- **b3d_to_parquet.py** - B3D file format to parquet converter
- **convert_addbiomechanics_to_parquet.py** - Main AddBiomechanics converter
- **add_phase_info.py** - Phase calculation for AddBiomechanics data
- **add_task_info.py** - Task metadata addition
- **requirements.txt** - Python dependencies
- **[various].ipynb** - Jupyter notebooks for analysis and validation

##### GTech 2021 (`contributor_scripts/AddBiomechanics/Gtech_2021/`)
- **add_task_info.py** - GTech 2021 task metadata processor
- **validate_dataset.py** - GTech 2021 data validation

#### GTech 2023 (`contributor_scripts/Gtech_2023/`)
- **CLAUDE.md** - GTech 2023 conversion guidance
- **readme.md** - GTech 2023 conversion instructions
- **combine_subjects_efficient.py** - Multi-subject data combination
- **convert_gtech_all_to_parquet.py** - Complete GTech 2023 converter
- **convert_gtech_phase_to_parquet.m** - MATLAB phase conversion
- **process_all_subjects.sh** - Batch processing script

##### Utilities (`contributor_scripts/Gtech_2023/utilities/`)
- **[various].m** - MATLAB utility functions for GTech 2023 processing
- **verify_gtech_data.ipynb** - Data verification notebook

#### UMich 2021 (`contributor_scripts/Umich_2021/`)
- **CLAUDE.md** - UMich 2021 conversion guidance
- **readme.md** - UMich 2021 conversion instructions
- **convert_umich_phase_to_parquet.m** - MATLAB phase-indexed converter
- **convert_umich_time_to_parquet.m** - MATLAB time-indexed converter
- **umich_2021_mat_structure.md** - MATLAB file structure documentation
- **verify_umich_data.ipynb** - Data verification notebook

### Source Code (`source/`)
- **CLAUDE.md** - Source directory guidance

#### Libraries (`source/lib/`)

##### MATLAB Library (`source/lib/matlab/`)
- **LocomotionData.m** - MATLAB LocomotionData class
- **locomotion_helpers.m** - MATLAB utility functions

#### Testing Framework (`source/tests/`)
- **CLAUDE.md** - Testing framework guidance
- **demo_dataset_validator_phase.py** - Visual validation demonstration
- **demo_filters_by_phase_plots.py** - Filter plots demonstration
- **demo_step_classifier.py** - Step classification demonstration
- **test_tutorial_getting_started_matlab.m** - MATLAB tutorial tests
- **test_tutorial_getting_started_python.py** - Python tutorial tests
- **test_tutorial_library_matlab.m** - MATLAB library tests
- **test_tutorial_library_python.py** - Python library tests
- **test_data_with_mocap_tolerance.csv** - Motion capture tolerance test data
- **test_filters_by_phase_plots.py** - Filter plot validation tests
- **test_step_classifier.py** - Step classifier validation tests

##### Test Data (`source/tests/test_data/`)
- **expected_failures_report.md** - Known test failure documentation

##### Sample Outputs (`source/tests/sample_plots/`)
- **[various directories]** - Test output validation images organized by test type


#### Visualization (`source/visualization/`)
- **refresh_validation_gifs.py** - GIF regeneration automation
- **walking_animator.py** - Walking pattern animation generator

##### Visualization Outputs (`source/visualization/plots/`)
- **comprehensive_gtech_2023/** - Complete GTech 2023 visualizations
- **validated_gtech_2023/** - Validated GTech 2023 subset visualizations

### Scripts (`scripts/`)
- **add_step_numbers.py** - Step numbering automation
- **check_file_structure.py** - Repository structure validation
- **check_parquet_structure.py** - Parquet file validation
- **compare_plotting_performance.py** - Performance benchmarking
- **comprehensive_mosaic_plot.py** - Multi-panel visualization
- **generate_phase_range_images.py** - Phase range visualization
- **generate_validation_gifs.py** - Validation GIF generation
- **memory_safe_validator.py** - Memory-efficient validation
- **mosaic_plot_3d_efficient.py** - Efficient 3D plotting
- **quick_phase_check.py** - Fast phase validation
- **update_validation_images.py** - Validation image updates
- **update_validation_table_format.py** - Table format standardization
- **validate_all_datasets.sh** - Comprehensive dataset validation

### Assets (`assets/`)
- **joint_angle_references.png** - Joint angle reference diagram

### Data Directories
- **converted_datasets/** - Standardized parquet files (gitignored)
- **conda_env/** - Conda environment files
- **venv/** - Python virtual environment (gitignored)

## Coding Philosophy

**Minimal, understandable, documented code following software engineering best practices.**

**Core Principles**:
- **Minimal code**: Write just enough, no more
- **Clear intent**: Document why, not what  
- **Explicit failures**: Raise clear errors instead of silent failures
- **Testing required**: All code must be tested
- **No duplication**: Reuse over recreation via shared modules
- **Single source of truth**: Avoid duplicating constants/data across files
- **Imports over copy-paste**: Create shared modules for common functionality
- **Refactor when you see duplication**: Proactively suggest better software engineering practices

## File Creation

**CRITICAL**: Ask user permission before creating ANY new file.

**Required Documentation**:
```python
"""
{File Name}

Created: {YYYY-MM-DD} with user permission
Purpose: {One-line summary}

Intent: {Why this file exists and what problems it solves}
"""
```

**Prohibited Without Permission**:
- New Python modules (.py files)
- New documentation files (.md files)
- New directories or configuration files

## Context Management

**Scratchpad System**: Lightweight project context tracking without complex PM overhead.

**Core Files**:
- `scratchpad.md` - Current work context (last 3 context clears)
- `scratchpad_history.md` - Archive of older work sessions

**Usage Pattern**:
1. Work on tasks normally with Claude Code
2. Use `/my_clear [next_steps]` slash command when ready to clear context
3. Claude intelligently filters context based on next steps and updates scratchpad
4. Start fresh with only relevant continuity preserved

**Smart Filtering**: When next steps are specified, Claude preserves only relevant context:
- **Keeps**: Dependencies, constraining decisions, unfinished related work, blockers
- **Archives**: Completed unrelated work streams  
- **Discards**: Tangential discussions, resolved issues, rejected alternatives

**Benefits**:
- **Context preservation**: No lost work when clearing Claude context
- **Intelligent filtering**: Only keeps context relevant to next steps, reduces noise
- **Minimal overhead**: Simple markdown files, no complex PM system
- **Natural workflow**: Integrates with Claude Code session management
- **Easy review**: Scannable history of recent work and decisions
- **Multi-goal sessions**: Handles sessions with multiple work streams effectively

## Common Commands

**Git**:
- Stage specific files only (never `git add -A`)
- Always include co-author information
- Get current date: `python3 -c "import datetime; print(datetime.datetime.now().strftime('%Y-%m-%d'))"`

**Project Context Management**:
```bash
cat scratchpad.md                     # Current work context and recent decisions
# Use /my_clear slash command to manage context and scratchpad
```

**MATLAB**: Executable at default Windows install location (WSL environment)

## Testing Standards

**Required Tests**:
- **test_*.py**: Headless validation for automated testing
- **demo_*.py**: Visual outputs for user observation
- Unit, integration, validation, and documentation tests

**Code Quality**:
- Single purpose per function/class
- Clear naming without requiring comments
- Comprehensive file headers with intent documentation
- Eliminate redundant functionality

## Documentation Standards

**Minimal yet effective style**:
- Essential information only
- Immediate actionability
- Scannable structure with headers and bullets
- No fluff or verbose descriptions

**Writing Style**:
- Start with action, not explanation
- Use imperative voice ("Load data" not "You can load data")
- Concrete examples over abstract descriptions
- No meta-commentary ("This guide will show you...")

## Decision Guidelines

- When uncertain, consult the user
- Prefer editing existing files over creating new ones
- Raise explicit errors instead of soft failures
- Document intent, not implementation details

## Development Status

**Pre-release**: Tool is not released to public yet. Don't worry about backwards compatibility since people are not using it yet. Focus on clean, optimal implementation over migration concerns.

---

*Follow these guidelines to maintain the project's minimal, effective codebase.*