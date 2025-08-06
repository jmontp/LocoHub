# CLAUDE.md - Internal Modules

## Overview

Internal implementation modules for the locomotion data standardization framework. These modules handle validation, visualization, and configuration management behind the scenes.

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
- **Imports**: Feature definitions from `user_libs.python.feature_constants`
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
- Imports FROM `user_libs.python.feature_constants` for definitions
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
2. Import feature definitions from `user_libs.python.feature_constants`
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