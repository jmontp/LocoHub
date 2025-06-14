# CLI Tool Specifications

**Command-line interface patterns and entry point specifications.**

## Critical Priority CLI Tools

### validate_phase_data.py (UC-C02)
**Purpose:** Validate phase-indexed dataset with stride-level filtering

```bash
# Basic validation with default settings
validate_phase_data.py dataset.parquet

# Comprehensive validation with plots and custom output
validate_phase_data.py dataset.parquet --output-dir validation_results --plots --verbose

# Batch validation of multiple datasets
validate_phase_data.py data/*.parquet --parallel --summary-report batch_results.md

# Validation with custom specifications
validate_phase_data.py dataset.parquet --specs custom_validation_specs.md --strict
```

**Arguments:**
- `file_path` (required): Path to phase-indexed parquet file
- `--output-dir, -o`: Output directory for reports and plots (default: current directory)
- `--plots, -p`: Generate validation plots (default: True)
- `--verbose, -v`: Detailed progress output
- `--parallel`: Enable parallel processing for batch validation
- `--summary-report`: Path for batch validation summary
- `--specs`: Custom validation specification file
- `--strict`: Fail on any validation warnings
- `--no-plots`: Disable plot generation
- `--format`: Output format (markdown, json, html)

**Outputs:**
- Validation report (markdown)
- Stride filtering results
- Validation plots (if enabled)
- Quality metrics summary

### validate_time_data.py (UC-C02)
**Purpose:** Validate time-indexed dataset with temporal integrity checks

```bash
# Basic time series validation
validate_time_data.py dataset.parquet

# Validation with sampling frequency checks
validate_time_data.py dataset.parquet --expected-freq 100 --tolerance 0.05

# Temporal integrity assessment
validate_time_data.py dataset.parquet --check-gaps --max-gap 0.1
```

**Arguments:**
- `file_path` (required): Path to time-indexed parquet file
- `--output-dir, -o`: Output directory for reports
- `--expected-freq`: Expected sampling frequency (Hz)
- `--tolerance`: Frequency tolerance (default: 0.02)
- `--check-gaps`: Enable temporal gap detection
- `--max-gap`: Maximum acceptable gap (seconds)
- `--format`: Output format (markdown, json, html)

### generate_validation_plots.py (UC-C03)
**Purpose:** Generate validation visualizations and specification plots

```bash
# Generate plots for validated dataset
generate_validation_plots.py --data dataset.parquet --output plots/

# Generate specification-only plots (without data)
generate_validation_plots.py --specs-only --tasks walking running --output spec_plots/

# Generate specific plot types
generate_validation_plots.py --data dataset.parquet --types forward_kinematics phase_ranges --output plots/

# Batch plot generation
generate_validation_plots.py --data data/*.parquet --batch --output batch_plots/
```

**Arguments:**
- `--data`: Path to dataset file (required unless --specs-only)
- `--specs-only`: Generate specification plots without data
- `--tasks`: Specific tasks to plot (default: all available)
- `--types`: Plot types (forward_kinematics, phase_ranges, validation_overlays)
- `--output, -o`: Output directory
- `--batch`: Batch processing mode
- `--format`: Plot format (png, svg, pdf)
- `--dpi`: Plot resolution (default: 300)

## High Priority CLI Tools

### assess_quality.py (UC-V01)
**Purpose:** Generate comprehensive dataset quality assessment

```bash
# Basic quality assessment
assess_quality.py dataset.parquet

# Quality assessment with metrics export
assess_quality.py dataset.parquet --export-metrics quality_timeline.json

# Multi-dataset quality comparison
assess_quality.py dataset1.parquet dataset2.parquet --compare --output quality_comparison.html
```

**Arguments:**
- `file_path` (required): Path to dataset file(s)
- `--export-metrics`: Export quality metrics to JSON
- `--compare`: Compare multiple datasets
- `--output, -o`: Output file path
- `--threshold`: Quality threshold for pass/fail
- `--detailed`: Include detailed outlier analysis
- `--population-norms`: Population norms reference file

### compare_datasets.py (UC-V02)
**Purpose:** Systematic comparison of multiple datasets

```bash
# Compare two datasets
compare_datasets.py dataset1.parquet dataset2.parquet

# Multi-dataset comparison with visual outputs
compare_datasets.py data/*.parquet --output comparison_report.html --plots

# Statistical comparison with custom significance level
compare_datasets.py dataset1.parquet dataset2.parquet --alpha 0.01 --effect-size 0.3
```

**Arguments:**
- `datasets` (required): Paths to dataset files to compare
- `--output, -o`: Output report path
- `--plots`: Generate comparison plots
- `--alpha`: Statistical significance level (default: 0.05)
- `--effect-size`: Minimum effect size threshold
- `--variables`: Specific variables to compare
- `--tasks`: Specific tasks to compare

### auto_tune_ranges.py (UC-V05)
**Purpose:** Automatically optimize validation ranges

```bash
# Tune ranges using percentile method
auto_tune_ranges.py data/*.parquet --method percentile --confidence 0.95

# Preview range changes without applying
auto_tune_ranges.py data/*.parquet --method statistical --preview-only

# Apply tuned ranges to specifications
auto_tune_ranges.py data/*.parquet --method percentile --apply --backup
```

**Arguments:**
- `datasets` (required): Dataset files for range calculation
- `--method`: Tuning method (percentile, statistical, robust)
- `--confidence`: Confidence level for range calculation
- `--preview-only`: Show changes without applying
- `--apply`: Apply changes to specification files
- `--backup`: Create backup before applying changes
- `--variables`: Specific variables to tune
- `--tasks`: Specific tasks to tune

### manage_validation_specs.py (UC-V04)
**Purpose:** Interactive management of validation specifications

```bash
# Interactive editing of specific variable ranges
manage_validation_specs.py --edit walking knee_flexion_angle_ipsi_rad --interactive

# Import ranges from literature or statistical analysis
manage_validation_specs.py --import-ranges literature_ranges.json --task walking

# Export current specifications
manage_validation_specs.py --export current_specs.json

# Version control and change tracking
manage_validation_specs.py --commit "Updated knee flexion ranges based on new data"
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

### investigate_errors.py (UC-V03)
**Purpose:** Debug validation failures with detailed analysis

```bash
# Investigate specific validation failures
investigate_errors.py dataset.parquet --stride S001_001 --variable knee_flexion_angle_ipsi_rad

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
**Purpose:** Create ML benchmarks with stratified splits

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
**Purpose:** Prepare datasets for public release

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
All CLI tools follow these common patterns:

**Standard Arguments:**
- `--help, -h`: Show help message and exit
- `--version`: Show version information
- `--verbose, -v`: Verbose output
- `--quiet, -q`: Suppress non-error output
- `--output, -o`: Output directory or file
- `--config`: Configuration file path

**Exit Codes:**
- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: File not found
- `4`: Validation failure
- `5`: Processing error

### Error Handling
- Clear error messages with actionable suggestions
- Progress reporting for long-running operations
- Graceful handling of interrupted operations
- Detailed logging available via `--verbose`

### Output Formats
- **Markdown**: Human-readable reports (default)
- **JSON**: Machine-readable structured data
- **HTML**: Rich formatted reports with plots
- **CSV**: Tabular data for analysis

### Configuration
- Global configuration via `~/.locomotion_data/config.yaml`
- Per-project configuration via `locomotion_config.yaml`
- Command-line arguments override configuration files
- Environment variables for sensitive settings