# Maintainer Guide

Maintaining the locomotion data standardization system's core functionality.

## Core System Components

### 1. 🔄 **Dataset Conversion**
Converting biomechanical data to standardized parquet format:
- `contributor_scripts/conversion_scripts/` - Dataset-specific converters
- `converted_datasets/` - Standardized output files
- Phase-indexed format: 150 points per gait cycle

### 2. 🔍 **Validation & Visualization**
Validating data quality with visual reports:
- `lib/validation/dataset_validator_phase.py` - Validation engine
- `contributor_tools/validation_ranges/` - YAML configuration
- `contributor_scripts/create_dataset_validation_report.py` - Report generator
- Generates plots with data overlaid on expected ranges

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

# 3. Generate validation report
cd ../../..
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/gtech_2023_phase.parquet

# 4. View documentation
cd docs/user_guide
mkdocs serve
# Open http://localhost:8000
```

## Key Files to Know

| File | Purpose | Location |
|------|---------|----------|
| Dataset Converters | Convert raw data to standard | `contributor_scripts/conversion_scripts/*/` |
| Validation Config | Expected data ranges | `contributor_tools/validation_ranges/*.yaml` |
| Validation Engine | Checks data quality | `lib/validation/dataset_validator_phase.py` |
| Data Interface | Load standardized data | `lib/core/locomotion_analysis.py` |
| Report Generator | Create validation reports | `contributor_scripts/create_dataset_validation_report.py` |

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
cd contributor_scripts/conversion_scripts/[Dataset]/
# Run converter (MATLAB or Python)

# Validate dataset
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/dataset_phase.parquet

# Load data for analysis
python3
>>> from lib.core.locomotion_analysis import LocomotionData
>>> data = LocomotionData('converted_datasets/dataset_phase.parquet')
```

## Documentation

- [Setup Guide](setup.md) - Environment setup
- [Common Tasks](tasks.md) - Detailed maintenance procedures
- [Testing](testing.md) - Test suite information