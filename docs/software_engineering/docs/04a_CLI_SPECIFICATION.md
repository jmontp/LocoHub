---
title: CLI Specification
tags: [cli, tools, commands]
status: ready
---

# CLI Specification

!!! info ":desktop_computer: **You are here** → Command-Line Interface Reference"
    **Purpose:** Complete CLI tool specifications with usage patterns and canonical names
    
    **Who should read this:** Developers, tool users, automation engineers
    
    **Value:** Authoritative reference for all CLI tools and their proper usage
    
    **:clock4: Reading time:** 20 minutes | **:hammer_and_wrench: Tools:** 8 primary CLI tools

!!! abstract ":zap: TL;DR - Essential CLI Commands"
    ```bash
    # Primary validation workflow
    validation_dataset_report.py dataset_phase.parquet --generate-gifs
    
    # Quick dataset comparison
    validation_compare_datasets.py data/*.parquet --output comparison.md
    
    # Specification management
    validation_manual_tune_spec.py --edit kinematic --task walking
    ```

**Command-line interface patterns and entry point specifications with canonical tool names.**

## Critical Priority CLI Tools

### validation_dataset_report.py (UC-C02) - PRIMARY VALIDATION TOOL

!!! tip ":trophy: **Primary Tool** - Most Important CLI Command"
    **Purpose:** Comprehensive validation and quality assessment of phase-indexed datasets
    
    **Priority:** :red_circle: **CRITICAL** - This is the main validation tool for the platform
    
    **Use Case:** Every dataset must pass through this tool before contribution

!!! example "Common Usage Patterns"
    === "Basic Validation"
        ```bash
        # Standard validation with comprehensive report
        validation_dataset_report.py dataset_phase.parquet
        ```
        **Use case:** Initial dataset quality assessment
        
    === "Visual Validation"  
        ```bash
        # Validation with animated GIF visualizations (computationally intensive)
        validation_dataset_report.py dataset_phase.parquet --generate-gifs
        ```
        **Use case:** Deep visual inspection of biomechanical patterns
        
    === "Custom Specifications"
        ```bash
        # Validation with custom specifications
        validation_dataset_report.py dataset_phase.parquet --specs custom_validation_specs.yaml
        ```
        **Use case:** Testing with modified validation ranges
        
    === "Batch Processing"
        ```bash
        # Batch validation with summary report
        validation_dataset_report.py data/*_phase.parquet --batch --summary validation_summary.md
        ```
        **Use case:** Validating multiple datasets simultaneously
        
    === "Strict Mode"
        ```bash
        # Strict validation mode (fail on warnings)
        validation_dataset_report.py dataset_phase.parquet --strict --output-dir validation_results/
        ```
        **Use case:** Final validation before dataset publication

**Core Arguments:**
- `file_path` (required): Path to phase-indexed parquet file
- `--output-dir, -o`: Output directory for reports and plots (default: current directory)
- `--generate-gifs`: Generate animated GIF visualizations (default: False, computationally intensive)
- `--specs`: Custom validation specification file (default: built-in specifications)
- `--strict`: Fail on any validation warnings (default: False)
- `--batch`: Enable batch processing for multiple files
- `--summary`: Path for batch validation summary report
- `--verbose, -v`: Detailed progress output and diagnostics
- `--quiet, -q`: Minimal output for automation
- `--format`: Output format (markdown, json, html) (default: markdown)
- `--no-plots`: Disable plot generation to save time

**Standard Outputs:**
- `{dataset_name}_validation_report.md`: Comprehensive validation report
- `{dataset_name}_quality_metrics.json`: Machine-readable quality assessment
- `{dataset_name}_{task}_kinematic_filters_by_phase.png`: Kinematic validation plots
- `{dataset_name}_{task}_kinetic_filters_by_phase.png`: Kinetic validation plots
- `{dataset_name}_{task}_animation.gif`: Animated visualizations (with --generate-gifs)
- `validation_summary.md`: Batch processing summary (with --batch)

### conversion_generate_phase_dataset.py (UC-C03) - LEGACY SUPPORT
**Purpose:** Convert time-indexed to phase-indexed datasets

**Priority:** MEDIUM - Most datasets already include phase-indexed versions

```bash
# Basic conversion (rarely needed for existing datasets)
conversion_generate_phase_dataset.py time_dataset.parquet

# Conversion with validation
conversion_generate_phase_dataset.py time_dataset.parquet --validate --output phase_dataset.parquet
```

**Arguments:**
- `file_path` (required): Path to time-indexed parquet file
- `--output, -o`: Output file path for phase dataset
- `--validate`: Run validation on generated phase dataset
- `--force`: Overwrite existing files
- `--verbose, -v`: Detailed progress output

## High Priority CLI Tools

### validation_compare_datasets.py (UC-V01)
**Purpose:** Systematic statistical comparison of multiple datasets

**Priority:** HIGH - Essential for multi-dataset analysis

```bash
# Compare two datasets
validation_compare_datasets.py dataset1.parquet dataset2.parquet

# Multi-dataset comparison with report
validation_compare_datasets.py data/*.parquet --output comparison_report.md

# Statistical comparison
validation_compare_datasets.py dataset1.parquet dataset2.parquet --alpha 0.01
```

**Arguments:**
- `datasets` (required): Paths to dataset files to compare
- `--output, -o`: Output report path
- `--plots`: Generate comparison plots
- `--alpha`: Statistical significance level (default: 0.05)
- `--effect-size`: Minimum effect size threshold
- `--variables`: Specific variables to compare
- `--tasks`: Specific tasks to compare

### validation_auto_tune_spec.py (UC-V05)
**Purpose:** Automatically optimize validation ranges using statistical methods

**Priority:** HIGH - Critical for maintaining validation accuracy

```bash
# Tune ranges using percentile method
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95

# With visualization
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95 --generate-gifs

# Preview changes
validation_auto_tune_spec.py --dataset data/*.parquet --method iqr --preview
```

### validation_manual_tune_spec.py (UC-V04)
**Purpose:** Interactive editing and management of validation specifications

**Priority:** HIGH - Required for validation specification maintenance

```bash
# Edit kinematic ranges
validation_manual_tune_spec.py --edit kinematic

# Edit specific task
validation_manual_tune_spec.py --edit kinetic --task walking

# With visualization
validation_manual_tune_spec.py --edit all --generate-gifs
```

**Arguments:**
- `--edit`: Edit specific task and variable
- `--interactive`: Enable interactive editing mode
- `--import-ranges`: Import ranges from file
- `--export`: Export specifications to file
- `--task`: Specific task to manage
- `--variable`: Specific variable to manage
- `--commit`: Commit changes with message
- `--history`: Show change history
- `--validate`: Validate changes against test datasets

## Medium Priority CLI Tools

### validation_investigate_errors.py (UC-V03)
**Purpose:** Debug and analyze validation failures with detailed diagnostics

**Priority:** MEDIUM - Important for troubleshooting validation issues

```bash
# Investigate specific validation failures
validation_investigate_errors.py dataset.parquet --variable knee_flexion_angle_ipsi_rad

# Pattern analysis of validation failures
investigate_errors.py dataset.parquet --failure-patterns --output debug_report.html

# Statistical analysis of outliers
investigate_errors.py dataset.parquet --outlier-analysis --threshold 3.0
```

**Arguments:**
- `file_path` (required): Path to dataset with validation failures
- `--stride`: Specific stride ID to investigate
- `--variable`: Specific variable to analyze
- `--failure-patterns`: Analyze patterns in validation failures
- `--outlier-analysis`: Statistical outlier analysis
- `--threshold`: Outlier detection threshold
- `--context`: Include biomechanical context
- `--recommendations`: Generate fix recommendations

### create_benchmarks.py (UC-A01)
**Purpose:** Create machine learning benchmarks with stratified data splits

**Priority:** MEDIUM - Important for ML applications

```bash
# Create subject-level splits
create_benchmarks.py dataset.parquet --strategy subject --train 0.7 --test 0.2 --val 0.1

# Temporal splits for time series analysis
create_benchmarks.py dataset.parquet --strategy temporal --output ml_benchmark/

# Export in multiple ML framework formats
create_benchmarks.py dataset.parquet --formats scikit pytorch tensorflow --output ml_ready/
```

**Arguments:**
- `file_path` (required): Path to quality dataset
- `--strategy`: Split strategy (subject, temporal, task, random)
- `--train`: Training set ratio (default: 0.7)
- `--test`: Test set ratio (default: 0.2)
- `--val`: Validation set ratio (default: 0.1)
- `--formats`: Export formats (scikit, pytorch, tensorflow, csv)
- `--output, -o`: Output directory
- `--metadata`: Include detailed metadata
- `--baseline`: Calculate baseline performance metrics

### publish_datasets.py (UC-A02)
**Purpose:** Package and prepare datasets for public distribution

**Priority:** MEDIUM - Required for dataset publication

```bash
# Package dataset for release
publish_datasets.py dataset.parquet --version 1.0.0 --output release_v1.0.0/

# Multi-format release with documentation
publish_datasets.py dataset.parquet --formats parquet csv matlab --docs --checksums
```

**Arguments:**
- `file_path` (required): Path to validated dataset
- `--version`: Release version number
- `--formats`: Export formats (parquet, csv, matlab)
- `--output, -o`: Release output directory
- `--docs`: Generate comprehensive documentation
- `--checksums`: Generate integrity verification files
- `--anonymize`: Anonymize sensitive information
- `--license`: License information file

## CLI Pattern Standards

### Common Arguments
All CLI tools follow these common patterns consistent with interface standards:

**Standard Arguments (All Tools):**
- `--help, -h`: Show help message and exit
- `--version`: Show version information
- `--verbose, -v`: Enable verbose logging output
- `--quiet, -q`: Minimal output for automation scripts
- `--output, -o`: Output directory or file path
- `--config`: Configuration file override

**Tool-Specific Arguments:**
```bash
# Validation Tools
--generate-gifs         Generate animated GIF visualizations (computationally intensive)
--specs FILE           Custom validation specifications file
--strict               Fail on any validation warnings
--batch                Enable batch processing for multiple files
--summary FILE         Path for batch validation summary report

# Conversion Tools (Legacy)
--validate             Run validation on generated phase dataset
--force                Overwrite existing output files

# Analysis Tools
--split-strategy TYPE  Data splitting method (subject, temporal, task, random)
--formats LIST         Export formats for ML frameworks
```

**Exit Codes (Aligned with Interface Standards):**
- `0`: EXIT_SUCCESS - Operation completed successfully
- `1`: EXIT_GENERAL_ERROR - General error (catch-all)
- `2`: EXIT_INVALID_ARGS - Invalid command line arguments
- `3`: EXIT_DATA_ERROR - Data quality or format error
- `4`: EXIT_VALIDATION_ERROR - Validation failure
- `5`: EXIT_CONFIG_ERROR - Configuration file error
- `6`: EXIT_PERMISSION_ERROR - File permission or access error
- `7`: EXIT_RESOURCE_ERROR - Insufficient resources (memory, disk)

### Error Handling (Interface Standard Compliance)
- **Structured Error Messages**: ERROR: {error_type}: {error_description}
- **Context Information**: File path, variable names, biomechanical context
- **Actionable Suggestions**: Recommended fixes based on error type
- **Progress Reporting**: Standardized progress display for long operations
- **Graceful Interruption**: Clean handling of Ctrl+C and system signals
- **Detailed Diagnostics**: Available via `--verbose` flag

### Output Formats (Standardized)
- **Markdown**: Human-readable reports (default for all tools)
- **JSON**: Machine-readable structured data (quality metrics, metadata)
- **HTML**: Rich formatted reports with embedded plots
- **PNG/GIF**: Validation plots and animations
- **YAML**: Configuration and specification files

### File Naming Conventions (Interface Standard)
```bash
# Dataset outputs
{dataset_name}_time.parquet           # Time-indexed data
{dataset_name}_phase.parquet          # Phase-indexed data (150 points/cycle)

# Validation reports
{dataset_name}_validation_report.md   # Main validation report
{dataset_name}_quality_metrics.json   # Machine-readable metrics

# Validation plots
{dataset_name}_{task}_kinematic_filters_by_phase.png
{dataset_name}_{task}_kinetic_filters_by_phase.png
{dataset_name}_{task}_animation.gif   # With --generate-gifs

# Tool reports
{tool_name}_report.md                 # General tool reports
{tool_name}_configuration.yaml        # Tool configuration
```

### Configuration Management (Interface Standard Aligned)
```yaml
# Standard configuration structure
tool_name: "validation_dataset_report"
version: "1.0.0"

# Input/Output Settings
input:
  format: "auto"  # auto, parquet, csv
  validation_level: "moderate"  # strict, moderate, lenient
  
output:
  directory: "./output"
  formats: ["markdown", "json"]
  include_plots: true
  
# Processing Settings
processing:
  memory_limit_gb: 8
  parallel_processing: true
  
# Validation Settings (for validation tools)
validation:
  specs_file: "auto"  # auto, custom file path
  generate_gifs: false
  strict_mode: false
```

**Configuration Hierarchy:**
1. Command-line arguments (highest priority)
2. Project configuration: `locomotion_config.yaml`  
3. Global configuration: `~/.locomotion_data/config.yaml`
4. Built-in defaults (lowest priority)

## COMPLETE CANONICAL TOOL NAME REFERENCE

**Use these exact names for consistency across all 19 software engineering documents:**

### Primary CLI Tools
- `validation_dataset_report.py` - Main validation and quality assessment tool
- `validation_compare_datasets.py` - Multi-dataset statistical comparison
- `validation_investigate_errors.py` - Validation failure debugging and analysis
- `validation_auto_tune_spec.py` - Automated validation range optimization
- `validation_manual_tune_spec.py` - Interactive validation specification editing
- `conversion_generate_phase_dataset.py` - Time-to-phase conversion (legacy support)
- `create_benchmarks.py` - ML benchmark creation with stratified splits
- `publish_datasets.py` - Dataset packaging for public distribution

### Core Library Modules
- `locomotion_analysis.py` - LocomotionData class with 3D array operations
- `feature_constants.py` - Feature definitions and mappings (single source of truth)
- `dataset_validator_phase.py` - Phase-indexed dataset validation engine
- `dataset_validator_time.py` - Time-indexed dataset validation engine
- `filters_by_phase_plots.py` - Phase-based validation plot generator
- `forward_kinematics_plots.py` - Joint angle visualization generator
- `step_classifier.py` - Gait cycle step classification
- `validation_expectations_parser.py` - Markdown validation rule parser

### Visualization and Animation
- `walking_animator.py` - Walking pattern animation generator
- `generate_validation_plots.py` - Unified plot generation script
- `generate_validation_gifs.py` - Animated GIF generation for validation
- `refresh_validation_gifs.py` - GIF regeneration automation

### Testing Framework
- `test_tutorial_getting_started_python.py` - Python tutorial validation tests
- `test_tutorial_library_python.py` - Python library comprehensive tests
- `test_tutorial_getting_started_matlab.m` - MATLAB tutorial validation tests
- `test_tutorial_library_matlab.m` - MATLAB library comprehensive tests
- `demo_dataset_validator_phase.py` - Visual validation demonstration
- `demo_filters_by_phase_plots.py` - Filter plots demonstration
- `demo_step_classifier.py` - Step classification demonstration

### Utility Scripts
- `check_file_structure.py` - Repository structure validation
- `check_parquet_structure.py` - Parquet file validation
- `memory_safe_validator.py` - Memory-efficient validation
- `quick_phase_check.py` - Fast phase validation
- `validate_all_datasets.sh` - Comprehensive dataset validation script

**Tool Priority Classification:**
- **CRITICAL**: `validation_dataset_report.py` (primary validation tool)
- **HIGH**: `validation_compare_datasets.py`, `validation_auto_tune_spec.py`, `validation_manual_tune_spec.py`
- **MEDIUM**: `validation_investigate_errors.py`, `create_benchmarks.py`, `publish_datasets.py`
- **LEGACY**: `conversion_generate_phase_dataset.py` (existing datasets have phase data)

This canonical reference ensures consistent tool naming across all documentation and prevents naming conflicts or confusion in the software engineering documentation suite.

---

## 🧭 Navigation Context

!!! info "**📍 You are here:** Command-Line Interface Complete Reference"
    **⬅️ Previous:** [Interface Spec](04_INTERFACE_SPEC.md) - Interface and API overview
    
    **➡️ Next:** [Data Contracts](04b_DATA_CONTRACTS.md) - Interface contracts and data structures
    
    **📖 Reading time:** 12 minutes
    
    **🎯 Prerequisites:** [Interface Spec](04_INTERFACE_SPEC.md) - Understanding of interface overview
    
    **🔄 Follow-up sections:** Data contracts, Interface standards

!!! tip "**Cross-References & Related Content**"
    **🔗 Interface Overview:** [Interface Spec](04_INTERFACE_SPEC.md) - High-level interface summary referencing these tools
    
    **🔗 User Tools:** [User Roles & Entry Points](01a_USER_ROLES.md) - User-specific tool catalog with priorities
    
    **🔗 Implementation Planning:** [Implementation Guide](05_IMPLEMENTATION_GUIDE.md) - Development strategy for building these tools
    
    **🔗 Testing Reference:** [Test Strategy](06_TEST_STRATEGY.md) - How these CLI tools are tested and validated
    
    **🔗 Standards Compliance:** [Interface Standards](04c_INTERFACE_STANDARDS.md) - CLI patterns and standards implemented by these tools