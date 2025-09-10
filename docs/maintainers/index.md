# Maintainer Guide

Maintaining the locomotion data standardization system's core functionality.

## Quick References

- 🚀 **[Scripts Cheat Sheet](scripts_cheatsheet.md)** - Quick reference for all essential scripts
- 📚 **[Developer Guide](developer_guide.md)** - Detailed development workflows

## Core System Components

### 1. 🔄 **Dataset Conversion**
Converting biomechanical data to standardized parquet format:
- `contributor_scripts/conversion_scripts/` - Dataset-specific converters
- `converted_datasets/` - Standardized output files
- Phase-indexed format: 150 points per gait cycle

### 2. 🔍 **Validation & Visualization**
Validating data quality with visual reports:
- `internal/validation_engine/validator.py` - Core validation engine
- `contributor_tools/validation_ranges/` - YAML configuration
- `contributor_tools/quick_validation_check.py` - Fast validation for contributors
- `contributor_tools/create_filtered_dataset.py` - Filter to valid strides only
- `contributor_tools/create_dataset_validation_report.py` - Full report generator (maintainer tool)

### 3. 📊 **Data Access Library**
Python interface for loading standardized data:
- `lib/core/locomotion_analysis.py` - Main LocomotionData class
- `lib/core/feature_constants.py` - Standard variable definitions
- 3D numpy array access for efficient analysis

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/your-org/locomotion-data-standardization
cd locomotion-data-standardization
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Test a conversion (example with GTech)
cd contributor_scripts/conversion_scripts/Gtech_2023/
python3 convert_gtech_all_to_parquet.py

# 3. Quick validation check (for contributors)
cd ../../..
python3 contributor_tools/quick_validation_check.py \
    converted_datasets/gtech_2023_phase.parquet

# 4. Generate full validation report (for documentation)
python3 contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/gtech_2023_phase.parquet
# Note: This generates markdown reports and requires mkdocs serve to view

# 5. View documentation
mkdocs serve
# Open http://localhost:8000
```

## Key Files to Know

| File | Purpose | Location |
|------|---------|----------|
| Dataset Converters | Convert raw data to standard | `contributor_tools/conversion_scripts/*/` |
| Validation Config | Expected data ranges | `contributor_tools/validation_ranges/*.yaml` |
| Validation Engine | Core validation logic | `internal/validation_engine/validator.py` |
| Quick Validator | Fast validation for contributors | `contributor_tools/quick_validation_check.py` |
| Filter Tool | Create validated dataset | `contributor_tools/create_filtered_dataset.py` |
| Report Generator | Full documentation reports | `contributor_tools/create_dataset_validation_report.py` |
| Data Interface | Load standardized data | `user_libs/python/locomotion_data.py` |

## Common Maintenance Tasks

### Converting a New Dataset
1. Create converter in `contributor_scripts/conversion_scripts/NewDataset/`
2. Follow existing converter patterns (UMich, GTech, AddBiomechanics)
3. Output to `converted_datasets/dataset_phase.parquet`
4. Validate with report generator

### Updating Validation Ranges
1. Edit YAML files in `contributor_tools/validation_ranges/`
2. Regenerate validation reports to see impact
3. Test with affected datasets

### Adding a New Variable
1. Add to `lib/core/feature_constants.py`
2. Update validation YAML configs
3. Update converter scripts if needed

## Key Scripts Reference

See [Scripts Cheat Sheet](../reference/scripts_cheatsheet.md) for all commands.

### Essential Workflows
```bash
# Convert dataset
cd contributor_tools/conversion_scripts/[Dataset]/
# Run converter (MATLAB or Python)

# Quick validation (for contributors)
python3 contributor_tools/quick_validation_check.py \
    converted_datasets/dataset_phase.parquet

# Filter to valid strides only
python3 contributor_tools/create_filtered_dataset.py \
    converted_datasets/dataset_phase_raw.parquet

# Full validation report (for maintainers)
python3 contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/dataset_phase.parquet
# Generates markdown documentation with plots

# Load data for analysis
python3
>>> from user_libs.python.locomotion_data import LocomotionData
>>> data = LocomotionData('converted_datasets/dataset_phase.parquet')
```

### Report Generator for Documentation

The `create_dataset_validation_report.py` tool is primarily for maintainers who need to:
- Generate publication-ready validation reports
- Create markdown documentation with embedded plots
- Update the documentation website with validation results
- Archive validation ranges with SHA256 hashes

**Note:** This tool requires `mkdocs serve` to view the generated reports properly, as it creates markdown files with relative image paths designed for the documentation system.

## Documentation

- [Setup Guide](setup.md) - Environment setup
- [Common Tasks](tasks.md) - Detailed maintenance procedures
- [Testing](testing.md) - Test suite information