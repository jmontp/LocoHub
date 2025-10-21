# AGENTS Guide

Combined agent configuration and operational guidance for the LocoHub repository. This document consolidates the previous `CLAUDE*.md` files and `AGENTS.md` into a single reference.

Most developers can ignore this file; it is aimed at automation or maintainers who need the canonical project instructions.


## Environment Notes

- MATLAB R2023 is available on Windows. Use it when tooling or scripts require native `.mat` readers that aren't accessible from the Linux environment.


## Global Guidance

### Source: Global Guidance (original CLAUDE.md)

Guidance for working with the LocoHub project.

## Project Vision

**Human-managed development** of biomechanical data standardization tools. This project provides researchers with reliable, validated locomotion datasets and analysis libraries.

**Three Target Audiences**:
1. **Users**: Researchers analyzing biomechanical data
2. **Contributors**: Teams converting new datasets to the standard
3. **Maintainers**: Developers improving the core libraries

## Repository Overview

Standardized biomechanical datasets with consistent naming and validation.

**Data Formats**:
- `dataset_time.parquet` - Original sampling frequency
- `dataset_phase.parquet` - 150 points per gait cycle  
- Variables: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

**Core Value**: Validated, reproducible biomechanical datasets for research.

## Actual Project Structure

### Core Implementation
```
user_libs/
├── python/          # Main Python library
│   ├── locomotion_data.py    # Core LocomotionData class
│   └── feature_constants.py  # Task and variable definitions
├── matlab/          # MATLAB analysis tools
└── r/              # R package implementation

internal/           # Backend modules (not user-facing)
├── validation_engine/
│   ├── validator.py          # DatasetValidator class
│   └── report_generator.py   # Validation reports
├── plot_generation/          # Visualization tools
└── config_management/        # Config and specs

contributor_tools/  # Dataset conversion & validation
├── conversion_scripts/       # Dataset-specific converters
│   ├── Umich_2021/
│   ├── Gtech_2023/
│   └── AddBiomechanics/
├── create_dataset_validation_report.py  # Full validation with plots
├── interactive_validation_tuner.py      # GUI for tuning validation ranges
└── quick_validation_check.py            # Lightweight text-only validation

converted_datasets/ # Standardized parquet files
tests/             # Comprehensive test suite
```

### Documentation
```
docs/
├── users/          # User guides and tutorials
├── reference/      # Data format specifications
│   └── standard_spec/
└── maintainers/    # Development documentation
```

## Development Philosophy

**Human-managed, focused development**. This project prioritizes working code over planning documents.

**Key Principles**:
- **Working code first**: Implement, test, then document
- **User-focused**: Every feature must serve one of our three audiences
- **Validated data**: All datasets must pass biomechanical validation
- **No over-engineering**: Build what's needed now, not theoretical futures

## Working with this Project

**For Users**: 
```python
# Import from user_libs
from locohub import LocomotionData

# Load and analyze data
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
mean_patterns = data.get_mean_patterns('SUB01', 'level_walking')
```

**For Contributors**:
```bash
# Convert a new dataset
cd contributor_tools/conversion_scripts/YourDataset/
python convert_to_parquet.py

# Quick validation check (text-only, no plots)
python contributor_tools/quick_validation_check.py \
    converted_datasets/your_dataset_phase.parquet
# Shows pass/fail statistics by task and feature type

# Full validation report with plots (uses default_ranges.yaml)
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet
    
# Use custom validation ranges
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet \
    --ranges-file contributor_tools/validation_ranges/custom_ranges.yaml

# Interactively tune validation ranges with GUI
python contributor_tools/interactive_validation_tuner.py
# Features:
# - Visual comparison of passing/failing strides
# - Draggable validation boxes for real-time adjustment
# - Show locally passing strides (pass current feature, fail others)
# - Toggle between radians and degrees display
# - Auto-load dataset and validation ranges on startup
```

**For Maintainers**:
```bash
# Run tests
pytest tests/ -v

# Check specific functionality
pytest tests/test_locomotion_data_library.py -k "test_basic_loading"

# Generate validation reports
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet
```

## Common Tasks

### Load and Analyze Data
```python
from locohub import LocomotionData

# Load phase-indexed data
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Basic analysis
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
rom_data = loco.calculate_rom('SUB01', 'level_walking')

# Visualization
loco.plot_phase_patterns('SUB01', 'level_walking', 
                         ['knee_flexion_angle_ipsi_rad'])
```

### Generate Validation Report
```bash
# Basic validation (uses default ranges)
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet
    
# Generates plots with consistent pass/fail visualization:
# - Green: strides passing ALL variables
# - Red: strides failing each specific variable
```

### Convert New Dataset
1. Create conversion script in `contributor_tools/conversion_scripts/YourDataset/`
2. Follow existing patterns (see Umich_2021 or Gtech_2023)
3. Ensure output has required columns and 150 points per cycle
4. Run validation to confirm compliance

## Key Files to Know

- `src/locohub/locomotion_data.py` - Main analysis class
- `src/locohub/feature_constants.py` - Valid tasks and variables
- `internal/validation_engine/validator.py` - Unified validation logic
- `contributor_tools/create_dataset_validation_report.py` - Full validation report generator
- `contributor_tools/quick_validation_check.py` - Fast text-only validation
- `contributor_tools/interactive_validation_tuner.py` - Interactive GUI for validation tuning
- `contributor_tools/validation_ranges/default_ranges.yaml` - Default validation ranges
- `tests/test_locomotion_data_library.py` - Usage examples

## Git Workflow

```bash
# Always use specific files, never -A
git add src/locohub/<specific_file>.py
git commit -m "Clear, action-focused message

Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>"
```

## Testing Approach

```bash
# Test core functionality
pytest tests/test_locomotion_data_library.py

# Test validation system
pytest tests/test_dataset_validator_phase_coverage.py

# Run all tests
pytest tests/ -v
```

## Advanced Features

### Arbitrary Validation Phases

The validation system supports any phase percentages (0-100), not just the standard 0/25/50/75:

```yaml
# Example: Custom phase points for detailed analysis
tasks:
  detailed_walking:
    phases:
      '10':   # Early stance
        knee_flexion_angle_ipsi_rad:
          min: 0.1
          max: 0.4
      '33':   # One-third through cycle
        knee_flexion_angle_ipsi_rad:
          min: 0.3
          max: 0.8
      '67':   # Two-thirds through cycle
        knee_flexion_angle_ipsi_rad:
          min: 0.6
          max: 1.2
      '90':   # Late swing
        knee_flexion_angle_ipsi_rad:
          min: 0.4
          max: 0.9
```

The system automatically:
- Maps phase percentages to array indices (0-149)
- Handles contralateral offsets for any phase configuration
- Generates plots at specified phase points
- Validates at exactly the phases you define

See `contributor_tools/validation_ranges/default_ranges.yaml` for the current validation ranges.

### Interactive Validation Tuning

The `interactive_validation_tuner.py` tool provides a GUI for visually tuning validation ranges:

**Features**:
- **Side-by-side visualization**: Passing strides (left) vs failing strides (right)
- **Draggable validation boxes**: Adjust min/max ranges with mouse
- **Real-time updates**: See validation results instantly as you adjust
- **Local vs global passing**: Yellow shows strides passing current feature but failing others
- **Unit conversion**: Toggle between radians and degrees for angular variables
- **YAML compatibility**: Load/save validation ranges in standard format

**Usage Tips**:
- Boxes can be dragged vertically to adjust min/max values
- Pass column boxes can also be dragged horizontally to change phase
- All values stored internally in radians for consistency
- Use "Show Locally Passing" to identify strides with specific issues
- Use "Show in Degrees" for more intuitive angular values

## Validation System

**Unified Feature-Based**: All biomechanical variables (kinematic, kinetic, segment) validated consistently. Green strides pass ALL variables; red strides show variable-specific failures.

## Development Status

**Active Development**: Breaking changes expected. Focus on correctness over compatibility.

---

*Follow these guidelines to maintain the project's minimal, effective codebase.*


## Local Overrides

### Source: Local Overrides (original CLAUDE.local.md)

- When committing code, add co-author information: 
  - Name: José A. Montes Pérez
  - Email: jmontp@umich.edu
  - Git co-author line: Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>

## Custom Slash Commands

### /validate-full
Complete dataset validation and quality assessment:
1. Run `python validation_dataset_report.py {dataset} --generate-gifs`
2. Check for validation failures and quality metrics
3. Generate summary of findings with recommendations
4. Open validation report for review

### /validate-quick
Fast dataset structure check:
1. Verify parquet file structure and required columns
2. Check phase indexing (150 points per cycle)
3. Validate task column against feature_constants
4. Report basic statistics without full biomechanical validation

### /spec-status
Check current validation specification status:
1. List recent changes to validation_expectations_*.md files
2. Show any pending staging files in validation system
3. Report which datasets might be affected by recent changes
4. Check for integrity issues (NaNs, missing cyclic tasks)

### /tune-specs
Interactive validation range tuning:
1. Ask user which task/variable to tune (kinematic/kinetic)
2. Run statistical analysis on available datasets
3. Show proposed ranges with justification
4. Stage changes for review using staging workflow

### /pm-update
Update project management files:
1. Run `python scripts/pm_update.py --check`
2. Update PM_snapshot.md if needed
3. Check for any PM file inconsistencies
4. Summarize current project status and next priorities

### /test-validation
Run validation system tests:
1. Execute relevant test files in source/tests/
2. Check for any failing tests related to validation
3. Report test coverage for PhaseValidator and SpecificationManager
4. Highlight any performance regressions

### /doc-sync
Synchronize documentation with code changes:
1. Check if tutorials need updates based on recent code changes
2. Verify cross-references in software engineering docs are current
3. Update any outdated tool references or file listings
4. Check AGENTS.md guidance alignment with current architecture

### /arch-review
Review architecture consistency:
1. Check C4 diagrams align with current implementation
2. Verify component relationships match actual code structure
3. Look for any outdated tool references in documentation
4. Suggest architecture improvements based on current state

### /convert-phase
Convert time-indexed dataset to phase-indexed:
1. Run `python conversion_generate_phase_dataset.py {time_dataset}`
2. Verify conversion success (exactly 150 points per cycle)
3. Run quick validation on generated phase dataset
4. Report conversion statistics and any issues

### /my_clear [next_steps]
Clear context and manage scratchpad with intelligent filtering:
1. **Context Analysis**: Analyze current session for multiple work streams and completion status
2. **Relevance Filtering**: If next_steps provided, filter context to only preserve information relevant to those next steps:
   - Direct dependencies (files/components that will be modified)
   - Recent decisions that constrain or enable the next work
   - Unfinished work streams that relate to next steps
   - Problems/blockers that might affect future work
   - Architecture decisions that impact next steps
3. **Content Organization**: 
   - **Keep**: Relevant ongoing work, key decisions, dependencies, blockers
   - **Archive**: Completed work streams unrelated to next steps
   - **Discard**: Tangential discussions, resolved debugging, rejected alternatives
4. **MANDATORY Scratchpad Update**: 
   - Read current scratchpad.md to determine next context clear number
   - Add new "Context Clear #N" section with filtered summary
   - Include: accomplishments, technical achievements, key decisions, current status, tools established
   - Update scratchpad.md file with Edit tool
5. **History Management**: If scratchpad.md has >3 context clears, move oldest to scratchpad_history.md
6. **Summary**: Explain what was kept vs filtered and why, confirm scratchpad was updated

**Usage Examples**:
- `/my_clear "implement validation system Phase 1"` - Keep validation architecture, filter out documentation work
- `/my_clear "fix tutorial bugs"` - Keep tutorial-related context, filter out validation system design  
- `/my_clear` - Keep everything (original behavior)

**CRITICAL**: Always read scratchpad.md first, then use Edit tool to update it with the context clear summary


## Internal Modules

### Source: Internal Modules (original CLAUDE.md)

## Overview

Internal implementation modules for the LocoHub framework. These modules handle validation, visualization, and configuration management behind the scenes.

## Purpose

**Backend implementation details**. Code here supports the user-facing APIs and contributor tools but is not intended for direct external use.

## Directory Structure

```
internal/
├── validation_engine/      # Dataset validation logic
│   ├── validator.py       # Core validation orchestration
│   └── report_generator.py # Markdown report generation
├── plot_generation/        # Visualization utilities
│   ├── filters_by_phase_plots.py  # Validation plot creation
│   ├── forward_kinematics_plots.py # Kinematic chain visualization
│   └── step_classifier.py         # Stride classification logic
└── config_management/      # Configuration and specification handling
    └── config_manager.py   # YAML validation ranges management
```

## Core Components

### validation_engine/

**validator.py**
- **Purpose**: Orchestrates dataset validation against biomechanical ranges
- **Key Class**: `Validator` - Validates phase structure and biomechanical values
- **Methods**:
  - `validate()` - Main validation entry point
  - `_validate_task_with_failing_features()` - Returns specific failed variables per stride
- **Uses**: ConfigManager for validation ranges

**report_generator.py**
- **Purpose**: Generates markdown validation reports with embedded plots
- **Key Class**: `ValidationReportGenerator`
- **Output**: Markdown reports in `docs/reference/datasets_documentation/validation_reports/`
- **Features**: Coordinates plot generation, formats statistics, manages output paths

### plot_generation/

**filters_by_phase_plots.py**
- **Purpose**: Creates validation plots showing pass/fail stride separation
- **Functions**:
  - `create_task_combined_plot()` - Multi-feature validation plot
  - `create_single_feature_plot()` - Single feature pass/fail visualization
- **Imports**: Feature definitions from `locohub.feature_constants`
- **Output**: PNG files with dataset name in filename

**step_classifier.py**
- **Purpose**: Classifies strides/steps for validation
- **Key Class**: `StepClassifier`
- **Logic**: Determines which strides pass/fail validation criteria

**forward_kinematics_plots.py**
- **Purpose**: Visualizes kinematic chain and segment orientations
- **Usage**: Advanced biomechanical visualization for debugging

### config_management/

**config_manager.py**
- **Purpose**: Manages validation range specifications from YAML files
- **Key Class**: `ConfigManager`
- **Features**:
  - Loads validation ranges from YAML
  - Auto-generates contralateral features
  - Handles arbitrary phase percentages (not just 0/25/50/75)
- **File Format**: Hierarchical YAML with task → phase → variable → min/max

## Design Patterns

### Separation of Concerns
- **Validation Logic**: Separated from report generation
- **Plot Generation**: Independent from validation engine
- **Configuration**: Externalized to YAML files

### Dependency Flow
```
User Tools → Internal Modules → Never the reverse
```

### Import Strategy
- Imports FROM `locohub.feature_constants` for definitions
- Never exposes internal APIs to user-facing code
- Uses relative imports within internal modules

## Key Interactions

### Validation Flow
1. `ValidationReportGenerator` receives dataset path
2. Calls `Validator.validate()` for biomechanical checks
3. Generates plots via `filters_by_phase_plots`
4. Creates markdown report with embedded images

### Configuration Loading
1. `ConfigManager` reads YAML validation ranges
2. Auto-generates contralateral features if `only_sagittal_ipsi: true`
3. Provides ranges to `Validator` for checking

## Important Implementation Details

### Failing Features Dictionary
- Format: `{stride_index: [list_of_failed_variable_names]}`
- Used for red/green stride separation in plots
- Unified validation across all features

### Plot Filename Convention
- Includes dataset name: `{dataset_name}_{task_name}_all_features_validation.png`
- Prevents overwriting when generating multiple reports

### Phase Handling
- Supports arbitrary phase percentages (0-100)
- Maps percentage to array index (0-149)
- Handles cyclical data (100% = 0% for gait)

## Maintenance Guidelines

### Adding New Validation Checks
1. Extend `Validator` class methods
2. Update `ValidationReportGenerator` for new statistics
3. Modify plot generation if new visualizations needed

### Changing Validation Ranges
1. Edit YAML files in `contributor_tools/validation_ranges/`
2. ConfigManager automatically picks up changes
3. No code changes required

### Adding New Plot Types
1. Create new function in appropriate plot module
2. Import feature definitions from `locohub.feature_constants`
3. Follow pass/fail visualization pattern

## Testing Considerations

- Validation engine has comprehensive tests in `tests/`
- Plot generation tested visually via report generation
- Configuration manager tested with various YAML structures

## Common Issues and Solutions

### Missing Features in Dataset
- Validator handles gracefully with warnings
- Plots show "Data Not Available" for missing features

### Phase Alignment Problems
- Validator checks for exactly 150 points per cycle
- Reports phase structure issues clearly

### Memory Usage with Large Datasets
- Processes data in chunks where possible
- Generates plots sequentially to limit memory

## Future Improvements

- Parallel plot generation for faster reports
- Caching of validation results
- Interactive HTML reports instead of static markdown
- Real-time validation during data collection

---

*Internal modules are implementation details. Keep interfaces clean and maintain separation from user-facing code.*


## Contributor Tools

### Source: Contributor Tools (original CLAUDE.md)

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
from locohub import LocomotionData
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


## Conversion Playbooks / Umich 2021

### Source: Umich 2021 Conversion (original CLAUDE.md)

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


## Conversion Playbooks / Gtech 2021

### Source: Gtech 2021 Conversion (original CLAUDE.md)

Process Georgia Tech 2021 dataset (Camargo et al. J Biomech) with 22 subjects performing multiple locomotion tasks.

## Dataset Overview

**Source**: CAMARGO_ET_AL_J_BIOMECH_DATASET
**Subjects**: 22 able-bodied participants (AB06-AB30, excluding AB22, AB26, AB27, AB29)
**Tasks**: Level ground walking, ramp ascent/descent, stair ascent/descent, treadmill walking
**Data Type**: OpenSim-processed biomechanical data

## Key Scripts

**Main Conversion**:
- `convert_gtech_2021_phase_to_parquet.m` - **METHOD 2 + BILATERAL**: Phase-indexed conversion with velocities calculated AFTER interpolation for exoskeleton control consistency. **NEW**: Bilateral processing treats both legs as ipsilateral, doubling the training data available
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

### Bilateral Processing Workflow
1. Load subject mass data from SubjectInfo.mat
2. Iterate through subjects and ambulation modes
3. Load trial data from subdirectories (ik, id, gcRight, gcLeft, etc.)
4. **NEW**: Process both legs as ipsilateral:
   - Right-leg-initiated strides (using gcRight heel strikes)  
   - Left-leg-initiated strides (using gcLeft heel strikes)
5. For each leg orientation:
   - Segment by heel strikes from appropriate leg
   - Interpolate to 150 points per cycle
   - Apply bilateral variable assignment (ipsi/contra swap based on leg)
   - Normalize moments by body mass
6. Combine bilateral stride data with step identifiers (001_R, 001_L)
7. Map task names to standard convention
8. Export to parquet format with doubled stride count

### Advanced Workflow (using EpicToolbox)
1. Initialize FileManager for efficient file handling
2. Compute EMG normalization from treadmill trials
3. Load trials using EpicToolbox functions
4. Apply complex stride classification logic
5. Use Topics functions for normalization and interpolation
6. Filter transitions and invalid strides

## Data Volume with Bilateral Processing

**Previous (Right-leg only)**:
- ~21 subjects × ~5 tasks × ~15-30 strides = ~8,000 strides
- Total rows: ~1.2M (8,000 strides × 150 points)

**Current (Bilateral processing)**:  
- ~21 subjects × ~5 tasks × ~30-60 strides = ~16,000 strides
- **Doubled training data**: Each original stride now generates both right-initiated and left-initiated versions
- Total rows: ~2.4M (16,000 strides × 150 points)
- Step naming: `001_R`, `001_L`, `002_R`, `002_L`, etc.

## Key Features

**Bilateral Processing**:
- Processes both legs as ipsilateral for maximum training data
- Maintains proper ipsi/contra relationships regardless of leg orientation
- Explicit error checking for missing left gait cycle data
- Step identifiers include leg information (_R/_L suffix)

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


## Conversion Playbooks / Gtech 2023

### Source: GTech 2023 Conversion (original CLAUDE.md)

Process Georgia Tech 2023 biomechanical data (13 subjects, 19 activities).

## Key Scripts

**Main Conversion**:
- `convert_gtech_all_to_parquet.py` - MATLAB .mat → Parquet converter
- `combine_subjects_efficient.py` - Efficient subject data merger
- `process_all_subjects.sh` - Batch processing utility

**Legacy MATLAB**:
- `convert_gtech_phase_to_parquet.m` - Phase conversion (legacy)

## Data Structure

**Input**:
- `RawData/AB01/` through `RawData/AB13/` - Subject directories with .mat files
- `RawData/Subject_masses.csv` - Body mass metadata
- Kinematic, kinetic, EMG, and IMU data

**Output**:
- `gtech_2023_time.parquet` - Time-indexed dataset
- `gtech_2023_phase.parquet` - Phase-indexed (150 points/cycle)

## Processing Pipeline

```
MATLAB .mat files → convert_gtech_all_to_parquet.py → Time-indexed Parquet
                                                            ↓
Subject metadata ← combine_subjects_efficient.py ← Phase-indexed Parquet
```

## Key Features

**Data Processing**:
- 19 different activity types (walking, stairs, jumping, etc.)
- Full kinematic and kinetic data extraction
- EMG and IMU data integration
- Standardized variable naming implementation

**Quality Assurance**:
- Gait cycle segmentation with heel strike detection
- Alignment validation plots in `Plots/AlignmentChecks_RawHS/`
- Missing data documentation in `_datamissing.txt`
- Cross-validation with MATLAB verification tools

## Utilities

**Helper Scripts** (`utilities/`):
- `convert_gtech_rotm_to_eul_csv.m` - Rotation matrix conversions
- `plot_leg_alignment.m` - Leg alignment visualization
- `verify_gtech_data.ipynb` - Data verification notebook
- `benchmark_processing.m` - Performance testing

## Performance

**Processing Characteristics**:
- Moderate memory requirements compared to AddBiomechanics
- Batch processing supported for all 13 subjects
- Efficient subject file merging algorithms

## Testing

```bash
# Process all subjects
python convert_gtech_all_to_parquet.py --input_dir RawData/ --output_dir ./converted/
./process_all_subjects.sh

# Verify conversion
python utilities/verify_gtech_data.ipynb
```

---

*Efficient conversion of comprehensive biomechanical dataset with multiple activity types.*


## Conversion Playbooks / AddBiomechanics

### Source: AddBiomechanics Conversion (original CLAUDE.md)

Transform OpenSim/AddBiomechanics B3D format to standardized Parquet.

## Key Scripts

**Main Conversion**:
- `convert_addbiomechanics_to_parquet.py` - B3D → time-indexed Parquet
- `add_phase_info.py` - Time → phase-indexed (150 points/cycle)
- `add_task_info.py` - Add standardized task metadata

**Core Processing**:
- `b3d_to_parquet.py` - Low-level B3D format parser
- `extract_biomechanics_dataset.sh` - Data extraction utility

## Processing Pipeline

```
B3D Files → convert_addbiomechanics_to_parquet.py → Time-indexed Parquet
                                                         ↓
Phase-indexed Parquet ← add_phase_info.py ← add_task_info.py
```

## Dependencies

**Heavy Requirements** (>2GB total):
- `nimblephysics` - Physics simulation for B3D parsing
- `torch` - Deep learning framework dependency

**Installation**:
```bash
cd source/conversion_scripts/AddBiomechanics
pip install -r requirements.txt
python -c "import nimblephysics; print('Success')"
```

## Key Features

**Data Processing**:
- Full 3D biomechanics with joint angles, moments, GRFs
- Coordinate transformations to OpenSim standard
- Standardized variable naming implementation
- Phase normalization with gait event detection

**Quality Assurance**:
- B3D format validation
- Memory-efficient processing for large files
- Error handling for malformed data
- Output validation against standard specification

## Performance Considerations

**Memory**: Conversion process is memory-intensive (>1GB files)
**Processing Time**: Significant for large datasets
**Storage**: Intermediate files require substantial disk space

## Known Limitations

- Right-leg data may be incomplete for some subjects
- Complex task name mapping from original to standard
- Multiple coordinate frame conversions required
- Large output file sizes (>1GB possible)

## Testing

```bash
# Test core components
python b3d_to_parquet.py --input sample.b3d --output test.parquet
python convert_addbiomechanics_to_parquet.py --input_dir ./b3d_files/ --output_dir ./converted/
python ../../tests/validation_blueprint_enhanced.py --input converted/dataset_phase.parquet
```

---

*Most complex conversion requiring careful dependency and memory management.*
