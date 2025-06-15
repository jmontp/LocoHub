# CLI Tool Specifications

**Command-line interface patterns and entry point specifications.**

## Critical Priority CLI Tools

### conversion_generate_phase_dataset.py (UC-C03)
**Purpose:** Convert time-indexed to phase-indexed datasets

```bash
# Basic conversion
conversion_generate_phase_dataset.py time_dataset.parquet

# Conversion with custom output
conversion_generate_phase_dataset.py time_dataset.parquet --output phase_dataset.parquet

# Batch conversion
conversion_generate_phase_dataset.py data/*_time.parquet --batch --output-dir phase_data/
```

### validation_dataset_report.py (UC-C02)
**Purpose:** Comprehensive validation and quality assessment

```bash
# Basic validation
validation_dataset_report.py dataset.parquet

# Validation with animated GIFs
validation_dataset_report.py dataset.parquet --generate-gifs

# Custom output directory
validation_dataset_report.py dataset.parquet --output-dir validation_results/

# Batch validation
validation_dataset_report.py data/*.parquet --batch --summary batch_summary.md
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

**Arguments for conversion_generate_phase_dataset.py:**
- `file_path` (required): Path to time-indexed parquet file
- `--output, -o`: Output file path for phase dataset
- `--batch`: Enable batch processing
- `--output-dir`: Output directory for batch processing
- `--force`: Overwrite existing files

**Arguments for validation_dataset_report.py:**
- `file_path` (required): Path to dataset file (phase or time)
- `--output-dir, -o`: Output directory for reports and plots
- `--generate-gifs`: Generate animated GIF visualizations
- `--batch`: Enable batch processing
- `--summary`: Path for batch summary report
- `--verbose, -v`: Detailed progress output

## High Priority CLI Tools

### validation_compare_datasets.py (UC-V01)
**Purpose:** Systematic comparison of multiple datasets

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
**Purpose:** Automatically optimize validation ranges

```bash
# Tune ranges using percentile method
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95

# With visualization
validation_auto_tune_spec.py --dataset data/*.parquet --method percentile_95 --generate-gifs

# Preview changes
validation_auto_tune_spec.py --dataset data/*.parquet --method iqr --preview
```

### validation_manual_tune_spec.py (UC-V04)
**Purpose:** Interactive editing of validation rules

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
**Purpose:** Debug validation failures with detailed analysis

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