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

## Project Structure

### Audience-Based Organization
```
docs/
├── users/          # Researchers using the data
├── contributors/   # Teams adding new datasets
├── maintainers/    # Developers improving the system
└── reference/      # Shared technical specifications
```

### Key Directories
- **lib/core/** - LocomotionData analysis library
- **lib/validation/** - Dataset validation tools
- **contributor_scripts/** - Dataset conversion scripts
- **converted_datasets/** - Standardized parquet files
- **tests/** - Comprehensive test suite


## Development Philosophy

**Human-managed, focused development**. This project prioritizes working code over planning documents.

**Key Principles**:
- **Working code first**: Implement, test, then document
- **User-focused**: Every feature must serve one of our three audiences
- **Validated data**: All datasets must pass biomechanical validation
- **No over-engineering**: Build what's needed now, not theoretical futures

## Working with this Project

**For Users**: 
- Start with `docs/users/tutorials/`
- Use `LocomotionData` class from `lib/core/locomotion_analysis.py`
- See example workflows in `lib/core/examples.py`

**For Contributors**:
- Review `docs/reference/standard_spec/` for data format
- Use existing converters in `contributor_scripts/` as templates
- Validate with tools in `lib/validation/`

**For Maintainers**:
- Architecture docs in `docs/maintainers/`
- Run tests with `pytest tests/`
- Follow existing code patterns in `lib/`

## Common Tasks

```python
# Load and analyze data
from lib.core.locomotion_analysis import LocomotionData
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Validate new dataset
from lib.validation.dataset_validator_phase import PhaseValidator
validator = PhaseValidator()
results = validator.validate('new_dataset.parquet')
```

## Git Workflow

```bash
# Always use specific files, never -A
git add lib/core/specific_file.py
git commit -m "Clear, action-focused message

Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>"
```

## Development Status

**Active Development**: Breaking changes expected. Focus on correctness over compatibility.

---

*Follow these guidelines to maintain the project's minimal, effective codebase.*