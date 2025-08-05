# CLAUDE.md

Guidance for working with the locomotion data standardization project.

## Project Vision

**Human-managed development** of biomechanical data standardization tools. This project provides researchers with reliable, validated locomotion datasets and analysis libraries.

**Three Target Audiences**:
1. **Users**: Researchers analyzing biomechanical data
2. **Contributors**: Teams converting new datasets to the standard
3. **Maintainers**: Developers improving the core libraries

## Repository Overview

Standardized biomechanical datasets with consistent naming and validation.

**Data Formats**:
- `dataset_time.parquet` - Original sampling frequency
- `dataset_phase.parquet` - 150 points per gait cycle  
- Variables: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

**Core Value**: Validated, reproducible biomechanical datasets for research.

## Actual Project Structure

### Core Implementation
```
user_libs/
├── python/          # Main Python library
│   ├── locomotion_data.py    # Core LocomotionData class
│   ├── feature_constants.py  # Task and variable definitions
│   └── statistics/           # Statistical analysis modules
├── matlab/          # MATLAB analysis tools
└── r/              # R package implementation

internal/           # Backend modules (not user-facing)
├── validation_engine/
│   ├── validator.py          # DatasetValidator class
│   └── report_generator.py   # Validation reports
├── plot_generation/          # Visualization tools
└── config_management/        # Config and specs

contributor_tools/  # Dataset conversion & validation
├── conversion_scripts/       # Dataset-specific converters
│   ├── Umich_2021/
│   ├── Gtech_2023/
│   └── AddBiomechanics/
└── create_dataset_validation_report.py

converted_datasets/ # Standardized parquet files
tests/             # Comprehensive test suite
```

### Documentation
```
docs/
├── users/          # User guides and tutorials
├── reference/      # Data format specifications
│   └── standard_spec/
└── maintainers/    # Development documentation
```

## Development Philosophy

**Human-managed, focused development**. This project prioritizes working code over planning documents.

**Key Principles**:
- **Working code first**: Implement, test, then document
- **User-focused**: Every feature must serve one of our three audiences
- **Validated data**: All datasets must pass biomechanical validation
- **No over-engineering**: Build what's needed now, not theoretical futures

## Working with this Project

**For Users**: 
```python
# Import from user_libs
from user_libs.python.locomotion_data import LocomotionData

# Load and analyze data
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
mean_patterns = data.get_mean_patterns('SUB01', 'level_walking')
```

**For Contributors**:
```bash
# Convert a new dataset
cd contributor_tools/conversion_scripts/YourDataset/
python convert_to_parquet.py

# Validate your dataset (uses default_ranges.yaml)
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet
    
# Use custom validation ranges
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet \
    --ranges-file contributor_tools/validation_ranges/custom_ranges.yaml
```

**For Maintainers**:
```bash
# Run tests
pytest tests/ -v

# Check specific functionality
pytest tests/test_locomotion_data_library.py -k "test_basic_loading"

# Generate validation reports
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet
```

## Common Tasks

### Load and Analyze Data
```python
from user_libs.python.locomotion_data import LocomotionData

# Load phase-indexed data
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Basic analysis
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
mean_patterns = loco.get_mean_patterns('SUB01', 'level_walking')
rom_data = loco.calculate_rom('SUB01', 'level_walking')

# Visualization
loco.plot_phase_patterns('SUB01', 'level_walking', 
                         ['knee_flexion_angle_ipsi_rad'])
```

### Generate Validation Report
```bash
# Basic validation (uses default ranges)
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/umich_2021_phase.parquet
    
# Generates plots with consistent pass/fail visualization:
# - Green: strides passing ALL variables
# - Red: strides failing each specific variable
```

### Convert New Dataset
1. Create conversion script in `contributor_tools/conversion_scripts/YourDataset/`
2. Follow existing patterns (see Umich_2021 or Gtech_2023)
3. Ensure output has required columns and 150 points per cycle
4. Run validation to confirm compliance

## Key Files to Know

- `user_libs/python/locomotion_data.py` - Main analysis class
- `user_libs/python/feature_constants.py` - Valid tasks and variables
- `internal/validation_engine/validator.py` - Unified validation logic
- `contributor_tools/create_dataset_validation_report.py` - Report generator
- `contributor_tools/validation_ranges/default_ranges.yaml` - Default validation ranges
- `tests/test_locomotion_data_library.py` - Usage examples

## Git Workflow

```bash
# Always use specific files, never -A
git add user_libs/python/specific_file.py
git commit -m "Clear, action-focused message

Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>"
```

## Testing Approach

```bash
# Test core functionality
pytest tests/test_locomotion_data_library.py

# Test validation system
pytest tests/test_dataset_validator_phase_coverage.py

# Run all tests
pytest tests/ -v
```

## Advanced Features

### Arbitrary Validation Phases

The validation system supports any phase percentages (0-100), not just the standard 0/25/50/75:

```yaml
# Example: Custom phase points for detailed analysis
tasks:
  detailed_walking:
    phases:
      '10':   # Early stance
        knee_flexion_angle_ipsi_rad:
          min: 0.1
          max: 0.4
      '33':   # One-third through cycle
        knee_flexion_angle_ipsi_rad:
          min: 0.3
          max: 0.8
      '67':   # Two-thirds through cycle
        knee_flexion_angle_ipsi_rad:
          min: 0.6
          max: 1.2
      '90':   # Late swing
        knee_flexion_angle_ipsi_rad:
          min: 0.4
          max: 0.9
```

The system automatically:
- Maps phase percentages to array indices (0-149)
- Handles contralateral offsets for any phase configuration
- Generates plots at specified phase points
- Validates at exactly the phases you define

See `contributor_tools/validation_ranges/default_ranges.yaml` for the current validation ranges.

## Validation System

**Unified Feature-Based**: All biomechanical variables (kinematic, kinetic, segment) validated consistently. Green strides pass ALL variables; red strides show variable-specific failures.

## Development Status

**Active Development**: Breaking changes expected. Focus on correctness over compatibility.

---

*Follow these guidelines to maintain the project's minimal, effective codebase.*