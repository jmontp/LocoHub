# Common Maintenance Tasks

Step-by-step guides for typical maintenance activities.

## Adding a New Biomechanical Variable

When researchers need a new variable (e.g., `pelvis_tilt_angle_abs_rad`):

### 1. Update Feature Constants

```python
# lib/core/feature_constants.py

STANDARD_VARIABLES = [
    # ... existing variables ...
    'pelvis_tilt_angle_abs_rad',  # Add new variable
]

# Add to appropriate category
KINEMATIC_VARIABLES = [
    # ... existing ...
    'pelvis_tilt_angle_abs_rad',
]
```

### 2. Add Validation Ranges

```markdown
# docs/standard_spec/validation_expectations_kinematic.md

## Pelvis Kinematics

### pelvis_tilt_angle_abs_rad
- **Range**: [-0.35, 0.35]  # ±20 degrees
- **Mean**: ~0.0
- **Units**: radians
- **Sign**: Positive = anterior tilt
- **Source**: Winter (2009) Biomechanics
```

### 3. Update Tests

```python
# tests/test_feature_constants.py

def test_pelvis_variables():
    """Test pelvis variables are properly defined."""
    assert 'pelvis_tilt_angle_abs_rad' in STANDARD_VARIABLES
    assert 'pelvis_tilt_angle_abs_rad' in KINEMATIC_VARIABLES
```

### 4. Document Changes

```bash
# Update CHANGELOG
echo "- Added pelvis_tilt_angle_abs_rad to standard variables" >> CHANGELOG.md

# Commit with clear message
git add -p  # Review changes
git commit -m "Add pelvis tilt angle to standard variables

Added pelvis_tilt_angle_abs_rad with validation ranges based on
Winter (2009) normative data. Required for posture analysis studies."
```

## Fixing a Bug

Example: Users report incorrect sign convention for knee moments.

### 1. Create Failing Test

```python
# tests/test_knee_moment_sign.py

def test_knee_moment_sign_convention():
    """Knee extension moment should be positive."""
    data = LocomotionData('test_data/demo_phase.parquet')
    knee_moments = data.get_variable('knee_moment_ipsi_Nm')
    
    # During stance phase (0-60%), expect positive values
    stance_mean = knee_moments[:, :90, :].mean()
    assert stance_mean > 0, f"Knee moment sign wrong: {stance_mean}"
```

### 2. Run Test to Confirm

```bash
pytest tests/test_knee_moment_sign.py -v
# FAILED: Knee moment sign wrong: -15.3
```

### 3. Fix the Bug

```python
# lib/core/locomotion_analysis.py

def _convert_sign_conventions(self, data):
    """Apply standard sign conventions."""
    # Fix: Knee moments were inverted
    if 'knee_moment_ipsi_Nm' in data.columns:
        data['knee_moment_ipsi_Nm'] *= -1  # Correct the sign
    return data
```

### 4. Verify Fix

```bash
# Run specific test
pytest tests/test_knee_moment_sign.py -v
# PASSED

# Run full test suite to ensure no regressions
pytest tests/
```

### 5. Document Fix

```python
# Add comment explaining the fix
# lib/core/locomotion_analysis.py

def _convert_sign_conventions(self, data):
    """Apply standard sign conventions.
    
    Note: Prior to v1.2.0, knee moments had incorrect sign.
    Positive now correctly indicates extension moment.
    """
```

## Updating Validation Rules

When validation is too strict/loose based on new data:

### 1. Analyze Current Failures

```python
# scripts/analyze_validation_failures.py

from lib.validation.dataset_validator_phase import PhaseValidator

validator = PhaseValidator()
results = validator.validate('problematic_dataset.parquet')

# Check what's failing
for variable, stats in results['failed_variables'].items():
    print(f"{variable}: {stats['percent_invalid']:.1f}% invalid")
    print(f"  Current range: {stats['expected_range']}")
    print(f"  Data range: [{stats['data_min']:.2f}, {stats['data_max']:.2f}]")
```

### 2. Run Automated Tuner

```python
# lib/validation/automated_fine_tuning.py

from lib.validation.automated_fine_tuning import AutomatedFineTuner

tuner = AutomatedFineTuner()
new_ranges = tuner.suggest_ranges(
    datasets=['dataset1.parquet', 'dataset2.parquet'],
    variable='knee_flexion_angle_ipsi_rad',
    task='stair_ascent'
)

print(f"Suggested range: {new_ranges}")
# Suggested range: [-0.35, 2.45] (was [-0.2, 2.0])
```

### 3. Update Specification

```markdown
# docs/standard_spec/validation_expectations_kinematic.md

## Knee Kinematics - Stair Ascent

### knee_flexion_angle_ipsi_rad
- **Range**: [-0.35, 2.45]  # Updated based on N=50 subjects
- **Previous**: [-0.2, 2.0]
- **Reason**: Larger flexion during stair ascent than expected
- **Date Updated**: 2024-03-15
- **Datasets Used**: GTech_2023, UMich_2021
```

### 4. Test Impact

```bash
# Re-validate datasets with new ranges
python lib/validation/dataset_validator_phase.py dataset1.parquet
# Check that previously failing data now passes
```

## Adding a New Dataset Converter

For a new data source (e.g., "Stanford_2024"):

### 1. Create Converter Structure

```bash
mkdir -p contributor_scripts/Stanford_2024
cd contributor_scripts/Stanford_2024

# Create files
touch __init__.py
touch convert_stanford_to_parquet.py
touch README.md
```

### 2. Implement Converter

```python
# contributor_scripts/Stanford_2024/convert_stanford_to_parquet.py

import pandas as pd
import numpy as np
from lib.core.feature_constants import STANDARD_VARIABLES

def convert_stanford_to_standard(raw_file, output_file):
    """Convert Stanford format to standard parquet."""
    
    # Load raw data (format specific)
    raw_data = pd.read_csv(raw_file)
    
    # Map to standard names
    name_mapping = {
        'KneeAngle': 'knee_flexion_angle_ipsi_rad',
        'HipMoment': 'hip_moment_ipsi_Nm',
        # ... more mappings
    }
    
    # Rename columns
    data = raw_data.rename(columns=name_mapping)
    
    # Convert units if needed
    data['knee_flexion_angle_ipsi_rad'] = np.deg2rad(
        data['knee_flexion_angle_ipsi_rad']
    )
    
    # Ensure 150 points per cycle
    # ... resampling code ...
    
    # Save as parquet
    data.to_parquet(output_file)
    print(f"Converted {output_file}")
```

### 3. Add Documentation

```markdown
# contributor_scripts/Stanford_2024/README.md

# Stanford 2024 Dataset Converter

Converts Stanford Biomechanics Lab data to standard format.

## Data Source
- **Lab**: Stanford Human Performance Lab
- **Year**: 2024
- **Subjects**: 20 healthy adults
- **Tasks**: Walking, running, jumping

## Usage
```python
python convert_stanford_to_parquet.py input.csv output.parquet
```

## Original Format
- CSV files with 100Hz sampling
- Angles in degrees
- Moments normalized to body mass

## Conversions Applied
- Angles: degrees → radians
- Resampling: 100Hz → 150 points/cycle
- Sign conventions: Stanford → Standard
```

### 4. Test Converter

```python
# tests/test_stanford_converter.py

def test_stanford_converter():
    """Test Stanford converter produces valid output."""
    # Convert sample data
    convert_stanford_to_standard('sample.csv', 'output.parquet')
    
    # Validate output
    validator = PhaseValidator()
    results = validator.validate('output.parquet')
    assert results['valid'], f"Validation failed: {results['errors']}"
```

## Debugging Validation Failures

When a dataset fails validation unexpectedly:

### 1. Get Detailed Report

```python
# scripts/debug_validation.py

from lib.validation.dataset_validator_phase import PhaseValidator
import matplotlib.pyplot as plt

validator = PhaseValidator(verbose=True)
results = validator.validate('failing_dataset.parquet')

# Print detailed stats
print(f"Dataset: {results['dataset_name']}")
print(f"Valid strides: {results['valid_strides']}/{results['total_strides']}")

# Plot problem variables
for var in results['failed_variables'][:3]:  # Top 3 problems
    validator.plot_variable_distribution(var)
    plt.show()
```

### 2. Check Specific Strides

```python
# Investigate individual failing strides
data = LocomotionData('failing_dataset.parquet')

failing_strides = results['invalid_stride_ids']
for stride_id in failing_strides[:5]:
    stride_data = data.get_stride(stride_id)
    
    # Check for NaNs
    if np.isnan(stride_data).any():
        print(f"Stride {stride_id}: Contains NaNs")
    
    # Check ranges
    for var in STANDARD_VARIABLES:
        values = stride_data[var]
        if values.max() > expected_max or values.min() < expected_min:
            print(f"Stride {stride_id}, {var}: Out of range")
```

### 3. Common Issues and Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| Wrong units | Values 57x too large | Convert radians/degrees |
| Sign flip | Negative when should be positive | Multiply by -1 |
| Bad resampling | Jagged patterns | Check interpolation method |
| Missing data | NaN values | Interpolate or exclude strides |
| Wrong task label | All strides failing | Check task column values |

## Next: [Testing Guide](testing.md)