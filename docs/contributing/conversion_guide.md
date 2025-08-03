# Dataset Conversion Guide

Step-by-step guide for converting biomechanical datasets to the standardized format.

## Prerequisites

Before starting conversion:

1. **Python environment** with required packages:
   ```bash
   pip install pandas numpy pyarrow tqdm
   ```

2. **Your dataset** in a structured format (CSV, MAT, HDF5, etc.)

3. **Understanding of your data**:
   - Sampling frequency (for time-indexed data)
   - Variable names and units
   - Task/condition labels
   - Subject identifiers

## Step 1: Understand the Target Format

### Required Structure

Every standardized dataset must have:

```python
# Required columns
required_columns = [
    'subject_id',      # Unique subject identifier
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

Use these exact task names:

- `level_walking` - Walking on level ground
- `incline_walking` - Walking uphill
- `decline_walking` - Walking downhill
- `up_stairs` - Ascending stairs
- `down_stairs` - Descending stairs
- `run` - Running
- `sit_to_stand` - Sit-to-stand transition
- `squats` - Squatting motion

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
    
    # 2. Map variable names
    variable_mapping = {
        # Your variable name: Standard name
        'knee_angle_left': 'knee_flexion_angle_ipsi_rad',
        'knee_angle_right': 'knee_flexion_angle_contra_rad',
        'hip_angle_left': 'hip_flexion_angle_ipsi_rad',
        # Add all your mappings
    }
    
    # 3. Rename columns
    data = data.rename(columns=variable_mapping)
    
    # 4. Convert units if needed
    if 'knee_flexion_angle_ipsi_rad' in data.columns:
        # If your data is in degrees, convert to radians
        data['knee_flexion_angle_ipsi_rad'] = np.deg2rad(data['knee_flexion_angle_ipsi_rad'])
    
    # 5. Standardize task names
    task_mapping = {
        'walking': 'level_walking',
        'stairs_up': 'up_stairs',
        'stairs_down': 'down_stairs',
        # Add your task mappings
    }
    data['task'] = data['task'].map(task_mapping)
    
    # 6. Ensure required columns exist
    assert 'subject_id' in data.columns
    assert 'task' in data.columns
    assert 'phase_percent' in data.columns or 'time' in data.columns
    
    # 7. Save as parquet
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

For time-indexed data without phase information:

```bash
# Use the provided conversion tool
python conversion_generate_phase_dataset.py converted_datasets/your_dataset_time.parquet

# This automatically:
# - Detects gait cycles
# - Normalizes to 150 points per cycle
# - Creates phase_percent column (0-100)
```

## Step 5: Validate Your Conversion

### Quick Validation Check

```python
def validate_converted_data(data_path):
    """
    Quick validation of converted dataset.
    """
    data = pd.read_parquet(data_path)
    
    # Check required columns
    required = ['subject_id', 'task', 'phase_percent']
    missing = [col for col in required if col not in data.columns]
    if missing:
        print(f"❌ Missing required columns: {missing}")
        return False
    
    # Check phase structure
    phase_counts = data.groupby(['subject_id', 'task']).size()
    if not all(count % 150 == 0 for count in phase_counts):
        print("❌ Not all cycles have 150 points")
        return False
    
    # Check value ranges
    if data['phase_percent'].min() < 0 or data['phase_percent'].max() > 100:
        print("❌ Phase percent outside 0-100 range")
        return False
    
    print("✓ Basic validation passed")
    return True
```

### Full Validation

```bash
# Run comprehensive validation
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet

# Check the report for:
# - Pass rate (should be ≥90%)
# - Specific violations
# - Suggestions for fixes
```

## Common Conversion Patterns

### Pattern 1: Multiple Files to Single Dataset

```python
def combine_multiple_files(file_pattern):
    """
    Combine multiple subject files into single dataset.
    """
    from pathlib import Path
    
    all_data = []
    for file_path in Path(".").glob(file_pattern):
        subject_id = file_path.stem  # Extract subject ID from filename
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

## Troubleshooting

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

## Next Steps

After successful conversion:

1. **Validate thoroughly** using the validation tool
2. **Document your dataset** with a README
3. **Test with analysis tools** to ensure compatibility
4. **Share your code** so others can reproduce the conversion

---

**Need help?** Check the working examples in `contributor_tools/conversion_scripts/` or open an issue on GitHub.