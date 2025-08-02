# Maintaining the Locomotion Data System

Welcome! This guide helps you maintain and improve the locomotion data standardization system.

## What You're Maintaining

The locomotion data standardization system converts biomechanical research data into a common format for analysis. It consists of three main parts:

### 1. Core Libraries (`lib/`)
- **LocomotionData** - Python/MATLAB classes for loading and analyzing gait data
- **Validation System** - Ensures data quality through biomechanical checks
- **Feature Constants** - Single source of truth for variable names

### 2. Dataset Converters (`contributor_scripts/`)
- **GTech 2023** - Georgia Tech treadmill data
- **UMich 2021** - University of Michigan incline walking
- **AddBiomechanics** - OpenSim-based datasets

### 3. Documentation & Tests
- **User tutorials** - Python, MATLAB, R examples
- **Test suite** - Unit and integration tests
- **Validation specs** - Biomechanical range definitions

## Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/locomotion-data-standardization
cd locomotion-data-standardization

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run tests to verify setup
pytest tests/

# 4. Build documentation locally
mkdocs serve

# 5. Make your first change
# Edit lib/core/feature_constants.py to add a new variable
# Run tests to ensure nothing breaks
pytest tests/test_locomotion_data_library.py
```

## Key Files to Know

| File | Purpose | When to Edit |
|------|---------|--------------|
| `lib/core/locomotion_analysis.py` | Main data loading class | Adding new analysis methods |
| `lib/core/feature_constants.py` | Variable name definitions | Adding new biomechanical variables |
| `lib/validation/dataset_validator_phase.py` | Phase data validation | Updating validation logic |
| `docs/standard_spec/validation_expectations_*.md` | Validation ranges | Adjusting acceptable data ranges |

## Common Tasks

### Adding a New Variable
1. Edit `lib/core/feature_constants.py`
2. Add validation ranges to `docs/standard_spec/validation_expectations_*.md`
3. Update tests in `tests/`
4. Document in relevant tutorials

### Fixing a Bug
1. Create a test that reproduces the issue
2. Fix the bug in the relevant module
3. Ensure all tests pass
4. Update documentation if behavior changed

### Updating Validation Rules
1. Edit the markdown specs in `docs/standard_spec/`
2. Run the automated tuner if needed
3. Test with sample datasets
4. Document the reasoning for changes

## Next Steps

- [Set up your development environment](setup.md)
- [Understand the architecture](architecture.md)
- [Learn common maintenance tasks](tasks.md)
- [Review testing practices](testing.md)

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check `docs/` for detailed specs
- **Tests**: Look at `tests/` for usage examples

## Project Philosophy

This project prioritizes:
1. **Data Quality** - Validation is mandatory, not optional
2. **Reproducibility** - Same input always produces same output
3. **Simplicity** - Clear code over clever code
4. **Documentation** - Every decision should be documented