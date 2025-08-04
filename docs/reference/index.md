# Reference Documentation

Technical reference for dataset conversion and validation.

## 🚀 [Scripts Cheat Sheet](scripts_cheatsheet.md)
Quick reference for all essential scripts - conversion, validation, and data access.

## 📋 [Data Standard Specification](standard_spec/standard_spec.md)
Complete specification for the locomotion data standard:
- [Variable naming and structure](standard_spec/standard_spec.md)
- [Units and sign conventions](standard_spec/units_and_conventions.md)
- [Standard task definitions](standard_spec/task_definitions.md)
- [Kinematic validation ranges](standard_spec/validation_expectations_kinematic.md)
- [Kinetic validation ranges](standard_spec/validation_expectations_kinetic.md)

## Core Components

### Dataset Conversion
Scripts to convert biomechanical data to standardized format:
- **UMich 2021** - MATLAB converter in `contributor_scripts/conversion_scripts/Umich_2021/`
- **GTech 2023** - Python converter in `contributor_scripts/conversion_scripts/Gtech_2023/`
- **AddBiomechanics** - Python converter in `contributor_scripts/conversion_scripts/AddBiomechanics/`

### Validation System
Visual validation and quality assessment:
- **Validation Reports** - Generated in `docs/user_guide/docs/reference/datasets_documentation/validation_reports/`
- **Configuration** - YAML files in `contributor_tools/validation_ranges/`
- **Visualization** - Plots showing data overlaid on expected ranges

### Data Access
Python library for loading and analyzing standardized data:
- **LocomotionData** - Main interface in `lib/core/locomotion_analysis.py`
- **3D Array Access** - Efficient numpy operations on gait cycles
- **Standard Features** - Defined in `lib/core/feature_constants.py`

## Data Format Overview

**Phase-Indexed Format**: 150 points per gait cycle (0-100%)

**Standard Naming**: `<joint>_<motion>_<measurement>_<side>_<unit>`

**Example Variables**:
- `knee_flexion_angle_ipsi_rad` - Knee angle (radians)
- `hip_flexion_moment_contra_Nm` - Hip moment (Newton-meters)

See [Data Standard Specification](standard_spec/standard_spec.md) for complete details.

## Common Tasks

### Convert a Dataset
```bash
cd contributor_scripts/conversion_scripts/[dataset]/
# Run converter script (MATLAB or Python)
```

### Validate a Dataset
```bash
python3 contributor_scripts/create_dataset_validation_report.py \
    --dataset converted_datasets/dataset_phase.parquet
```

### Load Data for Analysis
```python
from lib.core.locomotion_analysis import LocomotionData

loco = LocomotionData('converted_datasets/dataset_phase.parquet')
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
```

## Available Datasets

### Converted Datasets
Located in `converted_datasets/`:
- `umich_2021_phase.parquet` - University of Michigan 2021
- `gtech_2023_phase.parquet` - Georgia Tech 2023
- `addbiomechanics_phase.parquet` - AddBiomechanics

### Validation Reports
View at: `/reference/datasets_documentation/validation_reports/` when running MkDocs

## Further Information

- [Developer Guide](../developer/README.md) - Detailed development workflows
- [Scripts Cheat Sheet](scripts_cheatsheet.md) - Quick command reference
- [Maintainer Tasks](../maintainers/tasks.md) - System maintenance