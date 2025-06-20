# Command-Line Interface (CLI) Tools

Command-line tools for working with locomotion data standardization.

## Overview

The CLI tools provide command-line access to core functionality for:
- Dataset validation and quality assessment
- Data format conversion
- Batch processing operations
- Automated reporting

## Available Commands 

### Data Validation
```bash
# Validate phase-indexed dataset
python -m lib.validation.dataset_validator_phase dataset_phase.parquet

# Generate validation report
python -m lib.validation.generate_validation_plots dataset_phase.parquet --output-dir reports/
```

### Dataset Conversion
```bash
# Convert time-indexed to phase-indexed
python contributor_scripts/convert_to_phase.py dataset_time.parquet

# Batch conversion
python scripts/validate_all_datasets.sh
```

### Quality Assessment
```bash
# Quick structure check
python scripts/check_parquet_structure.py dataset.parquet

# Memory-safe validation
python scripts/memory_safe_validator.py dataset.parquet
```

## Installation

CLI tools are included with the core library installation. See the main documentation for setup instructions.

## Advanced Usage

For advanced CLI usage examples, see the [Python API documentation](python.md) and [library tutorials](../../tutorials/).