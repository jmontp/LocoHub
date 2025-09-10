# Dataset Conversion Guide

Practical guide for converting your biomechanical data to the standardized format. Expect this process to take 1-2 weeks for your first dataset.

## Prerequisites

Before starting conversion:

1. **Python environment** with required packages:
   ```bash
   pip install pandas numpy pyarrow tqdm matplotlib pyyaml
   ```

2. **Your dataset** in any structured format (CSV, MAT, HDF5, C3D, etc.)

3. **Understanding of your data**:
   - Sampling frequency (typically 100-1000 Hz)
   - Variable names and their units (degrees vs radians)
   - Task/condition labels (what activities were performed)
   - Subject identifiers (how subjects are coded)

4. **Time commitment**: Plan for 1-2 weeks for your first conversion:
   - Days 1-3: Understanding the format and requirements
   - Days 4-7: Writing and debugging your conversion script  
   - Week 2: Validation, troubleshooting, and refinement

## Step 1: Understand the Target Format

### Required Structure

Every standardized dataset must have:

```python
# Required columns
required_columns = [
    'subject_id',      # Subject ID with dataset prefix (e.g., 'UM21_AB01')
    'subject_metadata', # Optional demographics (e.g., 'age:25,sex:M')
    'task',            # Task name (e.g., 'level_walking', 'up_stairs')
    'phase_percent',   # 0-100 for phase data, or time in seconds
]

# Biomechanical variables following standard naming
biomech_variables = [
    'knee_flexion_angle_ipsi_rad',      # Knee angle, ipsilateral, radians
    'knee_flexion_angle_contra_rad',    # Knee angle, contralateral, radians
    'hip_flexion_angle_ipsi_rad',       # Hip angle, ipsilateral, radians
    'hip_moment_ipsi_Nm',               # Hip moment, ipsilateral, Newton-meters
    # ... more variables as available
]
```

### Standard Task Names

Use these exact task names (case-sensitive):

- `level_walking` - Walking on level ground
- `incline_walking` - Walking uphill (typically 5-10°)
- `decline_walking` - Walking downhill (typically 5-10°)
- `stair_ascent` - Going up stairs
- `stair_descent` - Going down stairs
- `run` - Running at any speed
- `sit_to_stand` - Sit-to-stand transition
- `squats` - Squatting motion

**Note**: If your data has different inclines or speeds, keep the standard task name and document specifics in metadata.

## Step 2: Create Your Conversion Script

### Basic Template

```python
#!/usr/bin/env python3
"""
Convert [Your Dataset Name] to standardized format
"""

import pandas as pd
import numpy as np
from pathlib import Path

def convert_to_standard_format(input_path, output_path):
    """
    Convert dataset to standardized parquet format.
    """
    
    # 1. Load your data
    data = load_your_data(input_path)
    
    # 2. Add dataset prefix to subject IDs
    # Replace 'UM21' with your dataset code
    data['subject_id'] = 'UM21_' + data['subject_id'].astype(str)
    
    # 3. Add subject metadata if available (optional)
    # Example: data['subject_metadata'] = 'age:25,sex:M,height_m:1.75'
    
    # 4. Map variable names
    variable_mapping = {
        # Your variable name: Standard name
        'knee_angle_left': 'knee_flexion_angle_ipsi_rad',
        'knee_angle_right': 'knee_flexion_angle_contra_rad',
        'hip_angle_left': 'hip_flexion_angle_ipsi_rad',
        # Add all your mappings
    }
    
    # 5. Rename columns
    data = data.rename(columns=variable_mapping)
    
    # 6. Convert units if needed
    if 'knee_flexion_angle_ipsi_rad' in data.columns:
        # If your data is in degrees, convert to radians
        data['knee_flexion_angle_ipsi_rad'] = np.deg2rad(data['knee_flexion_angle_ipsi_rad'])
    
    # 7. Standardize task names
    task_mapping = {
        'walking': 'level_walking',
        'stairs_up': 'up_stairs',
        'stairs_down': 'down_stairs',
        # Add your task mappings
    }
    data['task'] = data['task'].map(task_mapping)
    
    # 8. Ensure required columns exist
    assert 'subject_id' in data.columns
    assert 'task' in data.columns
    assert 'phase_percent' in data.columns or 'time' in data.columns
    
    # 9. Save as parquet
    data.to_parquet(output_path, index=False)
    print(f"Converted dataset saved to {output_path}")
    
    return data

def load_your_data(input_path):
    """
    Load your specific data format.
    """
    # Example for CSV
    return pd.read_csv(input_path)
    
    # Example for MATLAB
    # import scipy.io
    # mat_data = scipy.io.loadmat(input_path)
    # return process_mat_data(mat_data)

if __name__ == "__main__":
    input_file = "path/to/your/data.csv"
    output_file = "converted_datasets/your_dataset_time.parquet"
    
    convert_to_standard_format(input_file, output_file)
```

## Step 3: Handle Different Data Types

### Time-Indexed Data

If your data is sampled at regular intervals:

```python
def process_time_indexed_data(data, sampling_freq=100):
    """
    Process time-indexed biomechanical data.
    """
    # Add time column if not present
    if 'time' not in data.columns:
        n_samples = len(data)
        data['time'] = np.arange(n_samples) / sampling_freq
    
    # Ensure proper ordering
    data = data.sort_values(['subject_id', 'task', 'time'])
    
    return data
```

### Phase-Indexed Data

If your data is already normalized to gait cycles:

```python
def process_phase_indexed_data(data):
    """
    Process phase-indexed biomechanical data.
    """
    # Ensure 150 points per cycle
    cycles = []
    for (subject, task), group in data.groupby(['subject_id', 'task']):
        n_cycles = len(group) // 150
        
        for cycle in range(n_cycles):
            cycle_data = group.iloc[cycle*150:(cycle+1)*150].copy()
            cycle_data['phase_percent'] = np.linspace(0, 100, 150)
            cycle_data['cycle_id'] = cycle
            cycles.append(cycle_data)
    
    return pd.concat(cycles, ignore_index=True)
```

## Step 4: Convert Time to Phase (if needed)

!!! warning "Phase Converter Coming Soon"
    The automatic phase conversion tool is currently under development.
    For now, implement phase normalization in your conversion script.
    See the UMich example for a working implementation.

To normalize to phase in your script:

```python
def normalize_to_phase(time_data, n_points=150):
    """
    Normalize time-series data to phase (0-100% of gait cycle).
    """
    # Detect gait cycles (e.g., using peak detection)
    # Interpolate each cycle to exactly 150 points
    # Add phase_percent column: np.linspace(0, 100, 150)
    pass  # See examples for full implementation
```

## Step 5: Validate Your Conversion

### Quick Validation Check (Recommended First Step)

```bash
# Use the quick validation tool for immediate feedback
python contributor_tools/quick_validation_check.py \
    converted_datasets/your_dataset_phase.parquet

# Expected output:
# ✓ level_walking: 95% pass (380/400 strides)
# ✓ incline_walking: 92% pass (368/400 strides)  
# ⚠ stair_ascent: 73% pass (292/400 strides)

# Add --plot flag to see visual validation
python contributor_tools/quick_validation_check.py \
    converted_datasets/your_dataset_phase.parquet --plot
```

This gives you immediate feedback on whether your conversion is on track.

### Filter Out Invalid Strides

If validation shows some failures, you can create a filtered dataset:

```bash
# Remove strides that fail validation
python contributor_tools/create_filtered_dataset.py \
    converted_datasets/your_dataset_phase.parquet

# Creates: your_dataset_phase_filtered.parquet
# Only includes strides passing all biomechanical checks
```

### Full Validation Report

```bash
# Generate detailed validation report with plots
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet \
    --generate-plots

# The report shows:
# - Which variables are failing at which phases
# - Whether failures are systematic (check your conversion)
# - Visual plots comparing your data to expected ranges
```

## Common Conversion Patterns

### Pattern 1: Multiple Files to Single Dataset

```python
def combine_multiple_files(file_pattern, dataset_code='UM21'):
    """
    Combine multiple subject files into single dataset.
    """
    from pathlib import Path
    
    all_data = []
    for file_path in Path(".").glob(file_pattern):
        # Extract subject ID from filename
        raw_subject_id = file_path.stem  
        
        # Determine population code based on subject naming or metadata
        # Example: if 'AB' in raw_subject_id -> able-bodied
        if 'AB' in raw_subject_id:
            population_code = 'AB'
            subject_num = raw_subject_id.replace('AB', '')
        else:
            # Default to AB if not specified
            population_code = 'AB'
            subject_num = raw_subject_id
            
        # Create properly formatted subject ID
        subject_id = f"{dataset_code}_{population_code}{subject_num.zfill(2)}"
        
        data = pd.read_csv(file_path)
        data['subject_id'] = subject_id
        all_data.append(data)
    
    return pd.concat(all_data, ignore_index=True)
```

### Pattern 2: Wide to Long Format

```python
def wide_to_long_format(wide_data):
    """
    Convert wide format (one row per cycle) to long format.
    """
    # Example: columns like knee_0, knee_1, ..., knee_149
    
    long_data = []
    for idx, row in wide_data.iterrows():
        # Extract cycle data
        knee_values = [row[f'knee_{i}'] for i in range(150)]
        
        # Create long format
        cycle_df = pd.DataFrame({
            'subject_id': [row['subject_id']] * 150,
            'task': [row['task']] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'knee_flexion_angle_ipsi_rad': knee_values,
        })
        long_data.append(cycle_df)
    
    return pd.concat(long_data, ignore_index=True)
```

### Pattern 3: Unit Conversions

```python
def convert_units(data):
    """
    Convert all units to standard format.
    """
    # Angles: degrees to radians
    angle_columns = [col for col in data.columns if 'angle' in col]
    for col in angle_columns:
        data[col] = np.deg2rad(data[col])
    
    # Forces: pounds to Newtons
    force_columns = [col for col in data.columns if 'force' in col]
    for col in force_columns:
        data[col] = data[col] * 4.44822  # lbs to N
    
    # Distances: inches to meters
    distance_columns = [col for col in data.columns if 'position' in col]
    for col in distance_columns:
        data[col] = data[col] * 0.0254  # inches to meters
    
    return data
```

## Troubleshooting Common Issues

### Issue: Wrong units (degrees vs radians)

**Symptom**: Validation shows values like 45.0 for angles (likely degrees)

```python
# Solution: Convert to radians
import numpy as np
data['knee_flexion_angle_ipsi_rad'] = np.deg2rad(data['knee_angle_degrees'])
```

### Issue: Sign conventions (flexion/extension)

**Symptom**: Negative values where positive expected or vice versa

```python  
# Solution: Check and flip signs if needed
# Plot your data first to understand the convention
data['hip_flexion_angle_ipsi_rad'] = -data['hip_angle']  # Flip sign
```

### Issue: Memory errors with large datasets

```python
# Process in chunks
def process_large_dataset(input_path, output_path, chunk_size=100000):
    chunks = []
    for chunk in pd.read_csv(input_path, chunksize=chunk_size):
        processed = convert_chunk(chunk)
        chunks.append(processed)
    
    result = pd.concat(chunks, ignore_index=True)
    result.to_parquet(output_path)
```

### Issue: Mixed sampling frequencies

```python
# Resample to consistent frequency
def resample_data(data, target_freq=100):
    from scipy import interpolate
    
    resampled = []
    for (subject, task), group in data.groupby(['subject_id', 'task']):
        # Create interpolation function
        f = interpolate.interp1d(group['time'], group['knee_flexion_angle_ipsi_rad'])
        
        # New time points
        new_time = np.arange(group['time'].min(), group['time'].max(), 1/target_freq)
        
        # Interpolate
        new_data = pd.DataFrame({
            'subject_id': subject,
            'task': task,
            'time': new_time,
            'knee_flexion_angle_ipsi_rad': f(new_time)
        })
        resampled.append(new_data)
    
    return pd.concat(resampled)
```

## Practical Tips

1. **Start small**: Convert one subject first, validate, then scale up
2. **Check units early**: Most validation failures are unit issues (degrees/radians)
3. **Visualize your data**: Plot before validating to spot obvious problems
4. **Use the quick validator**: Get immediate feedback during development
5. **Don't aim for 100% validation**: 90%+ is typical for real data

## Next Steps

After successful conversion:

1. **Run quick validation** to get immediate pass/fail statistics
2. **Create filtered dataset** if you have some invalid strides
3. **Generate full report** for detailed analysis and plots
4. **Document your conversion** with a README explaining your choices
5. **Test with analysis tools** to ensure compatibility:
   ```python
   from user_libs.python.locomotion_data import LocomotionData
   loco = LocomotionData('your_dataset_phase.parquet')
   # Try basic operations
   ```

---

**Need help?** 
- Check working examples: `contributor_tools/conversion_scripts/`
- Quick questions: GitHub Discussions
- Bug reports: GitHub Issues
- Response time: Usually within 24 hours