# Development Setup

Quick setup for working with dataset conversion and validation.

## Requirements

- **Python 3.8+** - For validation and conversion scripts
- **Git** - Version control
- **MATLAB** (optional) - For UMich converter only

## Step 1: Clone Repository

```bash
git clone https://github.com/your-org/locomotion-data-standardization
cd locomotion-data-standardization
```

## Step 2: Python Setup

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Verify Installation

```bash
# Test data loading
python -c "from lib.core.locomotion_analysis import LocomotionData; print('✓ Data library works')"

# Test validation
python -c "from lib.validation.dataset_validator_phase import PhaseValidator; print('✓ Validation works')"
```

## Step 4: Test Core Functionality

### Convert a Dataset
```bash
# Example with GTech (Python)
cd contributor_scripts/conversion_scripts/Gtech_2023/
python3 convert_gtech_all_to_parquet.py
cd ../../..
```

### Generate Validation Report
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/gtech_2023_phase.parquet
```

### View Documentation
```bash
pip install mkdocs mkdocs-material
cd docs/user_guide
mkdocs serve
# Open http://localhost:8000
```

## Step 5: MATLAB Setup (Optional)

For UMich dataset converter only:

```matlab
% Navigate to converter
cd contributor_scripts/conversion_scripts/Umich_2021/

% Run converter
convert_umich_phase_to_parquet
```

## Common Issues

### Import Errors
```bash
# Ensure you're in project root
pwd  # Should show .../locomotion-data-standardization

# Add to PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### MATLAB Parquet Issues
```matlab
% Ensure parquet support is installed
% Check MATLAB documentation for parquetread/parquetwrite
```

## Quick Reference

See [Scripts Cheat Sheet](../reference/scripts_cheatsheet.md) for all essential commands.

## Next Steps

- [Common Tasks](tasks.md) - Maintenance procedures
- [Testing](testing.md) - Test suite guide