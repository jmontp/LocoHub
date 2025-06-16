# MASTER TOOL NAME MAPPING

**Canonical tool names for standardization across all software engineering documentation.**

*Use these exact names consistently across all 19 software engineering documents to prevent naming conflicts and confusion.*

---

## Primary CLI Tools

### Validation Tools (CRITICAL/HIGH Priority)
- `validation_dataset_report.py` - Main validation and quality assessment tool (PRIMARY TOOL)
- `validation_compare_datasets.py` - Multi-dataset statistical comparison
- `validation_investigate_errors.py` - Validation failure debugging and analysis
- `validation_auto_tune_spec.py` - Automated validation range optimization
- `validation_manual_tune_spec.py` - Interactive validation specification editing

### Data Conversion Tools (LEGACY Priority)
- `conversion_generate_phase_dataset.py` - Time-to-phase conversion (legacy support, most datasets have phase data)

### Analysis and Benchmarking Tools (MEDIUM Priority)
- `create_benchmarks.py` - ML benchmark creation with stratified splits
- `publish_datasets.py` - Dataset packaging for public distribution

---

## Core Library Modules

### Data Processing and Validation
- `locomotion_analysis.py` - LocomotionData class with 3D array operations
- `feature_constants.py` - Feature definitions and mappings (single source of truth)
- `dataset_validator_phase.py` - Phase-indexed dataset validation engine
- `dataset_validator_time.py` - Time-indexed dataset validation engine
- `validation_expectations_parser.py` - Markdown validation rule parser

### Visualization and Plotting
- `filters_by_phase_plots.py` - Phase-based validation plot generator
- `forward_kinematics_plots.py` - Joint angle visualization generator
- `step_classifier.py` - Gait cycle step classification

---

## Visualization and Animation Tools

- `walking_animator.py` - Walking pattern animation generator
- `generate_validation_plots.py` - Unified plot generation script (static plots)
- `generate_validation_gifs.py` - Animated GIF generation for validation
- `refresh_validation_gifs.py` - GIF regeneration automation

---

## Testing Framework

### Test Scripts (Headless Automation)
- `test_tutorial_getting_started_python.py` - Python tutorial validation tests
- `test_tutorial_library_python.py` - Python library comprehensive tests
- `test_tutorial_getting_started_matlab.m` - MATLAB tutorial validation tests
- `test_tutorial_library_matlab.m` - MATLAB library comprehensive tests

### Demo Scripts (Visual Output)
- `demo_dataset_validator_phase.py` - Visual validation demonstration
- `demo_filters_by_phase_plots.py` - Filter plots demonstration  
- `demo_step_classifier.py` - Step classification demonstration

---

## Utility Scripts

### Validation and Quality Assurance
- `check_file_structure.py` - Repository structure validation
- `check_parquet_structure.py` - Parquet file validation
- `memory_safe_validator.py` - Memory-efficient validation for large datasets
- `quick_phase_check.py` - Fast phase validation (structure check only)
- `validate_all_datasets.sh` - Comprehensive dataset validation script

### Development and Maintenance
- `add_step_numbers.py` - Step numbering automation for development
- `compare_plotting_performance.py` - Performance benchmarking for plots
- `update_validation_images.py` - Validation image updates
- `update_validation_table_format.py` - Table format standardization

---

## Standard File Naming Patterns

### Dataset Files
- `{dataset_name}_time.parquet` - Time-indexed data
- `{dataset_name}_phase.parquet` - Phase-indexed data (150 points/cycle)

### Validation Reports  
- `{dataset_name}_validation_report.md` - Main validation report
- `{dataset_name}_quality_metrics.json` - Machine-readable metrics
- `validation_summary.md` - Batch processing summary

### Validation Plots
- `{dataset_name}_{task}_kinematic_filters_by_phase.png` - Kinematic validation plots
- `{dataset_name}_{task}_kinetic_filters_by_phase.png` - Kinetic validation plots
- `{dataset_name}_{task}_forward_kinematics_phase_{00,25,50,75}_range.png` - Joint angle visualization
- `{dataset_name}_{task}_animation.gif` - Animated visualizations (with --generate-gifs)

### Tool Configuration and Reports
- `{tool_name}_report.md` - General tool reports
- `{tool_name}_configuration.yaml` - Tool-specific configuration
- `locomotion_config.yaml` - Project-wide configuration

---

## Priority Classification

### CRITICAL Priority
- `validation_dataset_report.py` - Primary validation tool for the platform

### HIGH Priority  
- `validation_compare_datasets.py` - Essential for multi-dataset analysis
- `validation_auto_tune_spec.py` - Critical for maintaining validation accuracy
- `validation_manual_tune_spec.py` - Required for validation specification maintenance

### MEDIUM Priority
- `validation_investigate_errors.py` - Important for troubleshooting
- `create_benchmarks.py` - Important for ML applications
- `publish_datasets.py` - Required for dataset publication

### LEGACY Priority
- `conversion_generate_phase_dataset.py` - Legacy support (existing datasets have phase data)

---

## Usage Guidelines

1. **Exact Names**: Use these exact tool names across all documentation
2. **No Variations**: Do not use abbreviated or alternative names
3. **Consistent Descriptions**: Use the provided descriptions consistently
4. **Priority Awareness**: Emphasize `validation_dataset_report.py` as the primary tool
5. **Legacy Context**: Always note that `conversion_generate_phase_dataset.py` is legacy support

This master mapping ensures consistency across all 19 software engineering documents and provides a single source of truth for tool naming conventions.