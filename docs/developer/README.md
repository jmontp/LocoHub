# Developer Guide

Core functionality: Dataset conversion and validation visualization.

## What This Project Does

1. **Converts biomechanical datasets** to standardized parquet format
2. **Validates data quality** with visual reports
3. **Provides data access** via Python library

## Project Structure

```
locomotion-data-standardization/
├── lib/
│   ├── core/                     
│   │   └── locomotion_analysis.py    # Data loading interface
│   └── validation/               
│       ├── dataset_validator_phase.py # Validation engine
│       └── filters_by_phase_plots.py  # Plot generation
├── contributor_scripts/          
│   ├── validation_ranges/        # Validation config (YAML)
│   ├── conversion_scripts/       # Dataset converters
│   │   ├── Umich_2021/          
│   │   ├── Gtech_2023/          
│   │   └── AddBiomechanics/     
│   └── create_dataset_validation_report.py  # Main validation script
└── converted_datasets/           # Standardized parquet files
```

## Converting Datasets

Each dataset has converters in `contributor_scripts/conversion_scripts/[dataset]/`

### Example: UMich 2021
```bash
cd contributor_scripts/conversion_scripts/Umich_2021/
matlab -batch "convert_umich_phase_to_parquet"
# Output: converted_datasets/umich_2021_phase.parquet
```

### Example: GTech 2023
```bash
cd contributor_scripts/conversion_scripts/Gtech_2023/
python3 convert_gtech_all_to_parquet.py
# Output: converted_datasets/gtech_2023_phase.parquet
```

## Validating Datasets

Generate validation report with visualization:

```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet
```

Output:
- Validation report (markdown)
- Kinematic plots showing data vs. expected ranges
- Success rate indicators

## Using the Data

```python
from lib.core.locomotion_analysis import LocomotionData

# Load dataset
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get 3D array for analysis
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
# Returns: (n_cycles, 150, n_features) numpy array
```

## Data Format Requirements

### Phase-Indexed Format
- 150 points per gait cycle
- 0-100% gait cycle progression

### Required Columns
- `subject` - Subject identifier
- `task` - Task name (e.g., 'level_walking')
- `step` - Step/cycle number
- `phase_percent` - 0 to 100

### Standard Variable Names
```
# Angles (radians)
hip_flexion_angle_ipsi_rad
hip_flexion_angle_contra_rad
knee_flexion_angle_ipsi_rad
knee_flexion_angle_contra_rad
ankle_flexion_angle_ipsi_rad
ankle_flexion_angle_contra_rad

# Moments (Nm)
hip_flexion_moment_ipsi_Nm
knee_flexion_moment_ipsi_Nm
ankle_flexion_moment_ipsi_Nm
```

## Validation System

### Configuration
YAML files in `contributor_scripts/validation_ranges/`:
- `kinematic_ranges.yaml` - Joint angle ranges
- `kinetic_ranges.yaml` - Moment ranges

### How It Works
1. Loads expected ranges from YAML
2. Compares data against ranges
3. Generates plots with data overlaid
4. Reports success percentage

### Contralateral Logic
For gait tasks, contralateral data is automatically generated from ipsilateral ranges with 50% phase offset.

## Adding a New Dataset

### 1. Create Converter Directory
```bash
mkdir contributor_scripts/conversion_scripts/NewDataset/
```

### 2. Write Converter Script
```python
import pandas as pd
import numpy as np

# Load raw data
raw_data = load_your_data()

# Convert to standard format
converted = []
for subject in subjects:
    for task in tasks:
        for cycle in gait_cycles:
            cycle_df = pd.DataFrame({
                'subject': subject,
                'task': task,
                'step': cycle_num,
                'phase_percent': np.linspace(0, 100, 150),
                'hip_flexion_angle_ipsi_rad': resample_to_150(hip_data),
                # ... other variables
            })
            converted.append(cycle_df)

# Save
final_df = pd.concat(converted)
final_df.to_parquet('converted_datasets/newdataset_phase.parquet')
```

### 3. Validate
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/newdataset_phase.parquet
```

## View Documentation

```bash
cd docs/user_guide
mkdocs serve
# Navigate to: http://localhost:8000
```

## Quick Reference

See [Scripts Cheat Sheet](../reference/scripts_cheatsheet.md) for all commands.