# Common Maintenance Tasks

Practical guides for maintaining the conversion and validation system.

## Adding a New Dataset Converter

### 1. Create Converter Directory
```bash
mkdir -p contributor_scripts/conversion_scripts/NewDataset/
```

### 2. Write Converter Script
```python
# contributor_scripts/conversion_scripts/NewDataset/convert_to_parquet.py

import pandas as pd
import numpy as np

def convert_to_standard():
    # Load raw data
    raw_data = load_your_data()
    
    # Convert to standard format
    # - 150 points per gait cycle
    # - Standard variable names
    # - Phase-indexed (0-100%)
    
    # Save as parquet
    df.to_parquet('../../../converted_datasets/newdataset_phase.parquet')
```

### 3. Validate Output
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/newdataset_phase.parquet
```

## Updating Validation Ranges

When validation is too strict/loose:

### 1. Edit YAML Configuration
```yaml
# contributor_scripts/validation_ranges/kinematic_ranges.yaml

tasks:
  level_walking:
    phases:
      '0':
        hip_flexion_angle_ipsi_rad: 
          min: -0.35  # Adjust as needed
          max: 1.2
```

### 2. Regenerate Validation Report
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/dataset_phase.parquet
```

### 3. Review Visual Output
Check generated plots to verify ranges are appropriate.

## Adding a New Variable

### 1. Update Feature Constants
```python
# lib/core/feature_constants.py

STANDARD_VARIABLES = [
    # ... existing ...
    'new_variable_name_ipsi_unit',
]
```

### 2. Add to Validation Config
```yaml
# contributor_scripts/validation_ranges/kinematic_ranges.yaml
# Add ranges for the new variable
```

### 3. Update Converters
Add the new variable to relevant dataset converters.

## Debugging Validation Failures

### 1. Run Validation Report
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/failing_dataset.parquet
```

### 2. Check Generated Plots
- Look for outliers in visualization plots
- Check if data exceeds expected ranges
- Verify phase alignment (0-100%)

### 3. Common Issues

| Issue | Solution |
|-------|----------|
| Wrong units | Convert deg↔rad in converter |
| Sign flip | Multiply by -1 in converter |
| Bad resampling | Check interpolation to 150 points |
| Wrong task label | Fix task column in converter |

## Quick Command Reference

See [Scripts Cheat Sheet](../reference/scripts_cheatsheet.md) for complete command list.

### Essential Commands
```bash
# Convert dataset
cd contributor_scripts/conversion_scripts/[Dataset]/
# Run converter

# Validate
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/dataset_phase.parquet

# Load data
python3
>>> from lib.core.locomotion_analysis import LocomotionData
>>> data = LocomotionData('converted_datasets/dataset_phase.parquet')
```