# Contributing

Essential guide for contributing to locomotion data standardization.

## Contribution Types

**Dataset Converters** • **Validation Rules** • **Library Features** • **Documentation** • **Bug Fixes**

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/locomotion-data-standardization.git
cd locomotion-data-standardization
git remote add upstream https://github.com/jmontp/locomotion-data-standardization.git
```

**Dependencies:**
```bash
pip install pandas numpy matplotlib pyarrow  # Core
pip install -r contributor_tools/conversion_scripts/AddBiomechanics/requirements.txt  # Optional
```

**MATLAB:** R2019b+, `addpath('user_libs/matlab')`

## Standards

**Variable Naming:** `<joint>_<motion>_<measurement>_<side>_<unit>`  
Examples: `knee_flexion_angle_contra_rad`, `hip_flexion_moment_ipsi_Nm_kg`

**Code Style:**
- Python: PEP 8, 100 char lines, type hints
- MATLAB: camelCase, 4 spaces, function headers
- Documentation: All functions need docstrings with examples

## Adding Dataset Converters

**Structure:** `contributor_tools/conversion_scripts/YourDataset/`

**Converter Template:**
```python
def convert_to_parquet(input_path, output_path):
    # 1. Load raw data
    # 2. Map to standard names: joint_motion_measurement_side_unit
    # 3. Convert units (angles→rad, moments→Nm/kg, forces→BW)
    # 4. Add metadata: subject, task, phase/time_s
    # 5. Validate with LocomotionData library
    # 6. Save as parquet
```

**Documentation:** Add to `docs/datasets_documentation/README.md`

## Testing

**Python:**
```bash
python tests/test_locomotion_data_library.py
python -c "from user_libs.python.examples.basic_examples import run_basic_example; run_basic_example()"
```

**MATLAB:**
```matlab
cd('tests')
test_tutorial_library_matlab
```

**Pre-commit:**
- Style guidelines followed
- Tests pass
- Documentation updated
- No sensitive data

## Submitting Contributions

**Commit Messages:**
```bash
git commit -m "Add XYZ dataset converter

- Map 23 variables to standard names
- Support multiple walking speeds  
- Include dataset documentation"
```

**Pull Request:**
1. `git push origin feature/your-feature-name`
2. Create PR on GitHub
3. Describe changes, reference issues, include test results
4. Address review feedback

## Issues

**Bug Reports:** Dataset affected, reproduction steps, error messages, environment details

**Feature Requests:** Use case, implementation approach, examples, impact assessment

## Project Structure

```
user_libs/python/        # Core Python libraries
user_libs/matlab/        # MATLAB libraries
contributor_tools/      # Dataset converters and validation
maintainer_tools/       # Release and benchmark management
internal/               # Core infrastructure
tests/                  # Testing framework
docs/                   # Specifications and tutorials
```

## Best Practices

**Dataset Converters:**
- Preserve raw data
- Handle missing data gracefully
- Validate biomechanical constraints
- Document assumptions
- Maintain traceability

**Library Features:**
- Maintain compatibility
- Use vectorized operations
- Test with large datasets
- Include usage examples

---

*Contributions are licensed under MIT License.*
