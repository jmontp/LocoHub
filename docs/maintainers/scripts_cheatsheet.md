# Scripts Cheat Sheet

Essential scripts for dataset conversion and validation visualization.

## 🔄 Dataset Conversion

### UMich 2021 Dataset (MATLAB)
```bash
# Navigate to converter directory
cd contributor_scripts/conversion_scripts/Umich_2021/

# Run MATLAB conversion
matlab -batch "convert_umich_phase_to_parquet"
# Output: converted_datasets/umich_2021_phase.parquet
```

### GTech 2023 Dataset (Python)
```bash
cd contributor_scripts/conversion_scripts/Gtech_2023/
python3 convert_gtech_all_to_parquet.py
# Output: converted_datasets/gtech_2023_phase.parquet
```

### AddBiomechanics Dataset (Python)
```bash
cd contributor_scripts/conversion_scripts/AddBiomechanics/
python3 convert_addbiomechanics_to_parquet.py
# Output: converted_datasets/addbiomechanics_phase.parquet
```

## 🔍 Validation & Visualization

### Generate Validation Report
```bash
# Creates validation report with visualization plots
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet

# Output:
# - Validation report: docs/user_guide/docs/reference/datasets_documentation/validation_reports/umich_2021_phase_validation_report.md
# - Kinematic plots: *_kinematic_filters_by_phase_with_data.png

# Without plots (faster)
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet \
    --no-plots
```

### Generate Validation Plots from Config
```bash
# Generate all validation plots from YAML config
python3 contributor_scripts/generate_validation_plots.py

# Generate for specific tasks
python3 contributor_scripts/generate_validation_plots.py --tasks level_walking decline_walking

# Generate only forward kinematics plots
python3 contributor_scripts/generate_validation_plots.py --forward-kinematic-only --mode kinematic

# Use custom config file
python3 contributor_scripts/generate_validation_plots.py --config path/to/custom_ranges.yaml
```

## 📊 Basic Data Analysis

### Load and Explore Data (Python)
```python
from lib.core.locomotion_analysis import LocomotionData

# Load dataset
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Basic info
print(f"Subjects: {loco.subjects}")
print(f"Tasks: {loco.tasks}")
print(f"Features: {loco.features}")

# Get data for analysis
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
# Returns: (n_cycles, 150, n_features) array
```

### Quick Data Check (Python)
```python
import pandas as pd

# Load and inspect
df = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
print(f"Shape: {df.shape}")
print(f"Subjects: {df['subject'].nunique()}")
print(f"Tasks: {df['task'].unique()}")
```

## 📈 View Documentation

### Serve Documentation Locally
```bash
cd docs/user_guide
mkdocs serve
# Navigate to: http://localhost:8000/reference/datasets_documentation/validation_reports/
```

## 🔧 Configuration

### Validation Ranges
Located in `contributor_tools/validation_ranges/`:
- `kinematic_ranges.yaml` - Joint angle validation ranges
- `kinetic_ranges.yaml` - Force/moment validation ranges

These are automatically loaded by the validation system.

## 🎯 Common Workflow

### Complete Dataset Processing
```bash
# 1. Convert dataset (example with UMich)
cd contributor_scripts/conversion_scripts/Umich_2021/
matlab -batch "convert_umich_phase_to_parquet"

# 2. Validate and generate report (from project root)
cd ../../..
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet

# 3. View results
cd docs/user_guide
mkdocs serve
# Open browser to localhost:8000
```

## 📝 Notes

- All datasets are converted to phase-indexed format (150 points per gait cycle)
- Validation reports include visual plots showing data against expected ranges
- The system uses standardized variable naming (e.g., `hip_flexion_angle_ipsi_rad`)