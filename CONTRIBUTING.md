# Contributing to Locomotion Data Standardization

Thank you for your interest in contributing to the Locomotion Data Standardization project! This guide will help you get started with contributing to our codebase.

## 🎯 Ways to Contribute

We welcome contributions in several areas:

- **New Dataset Converters**: Add support for additional biomechanics datasets
- **Feature Enhancements**: Implement new biomechanical variables or analysis methods
- **Validation Rules**: Improve data quality checks and biomechanical constraints
- **Visualization Tools**: Create new plotting functions or improve existing ones
- **Documentation**: Enhance tutorials, fix typos, or clarify explanations
- **Bug Fixes**: Report or fix issues you encounter

## 🚀 Getting Started

### 1. Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/locomotion-data-standardization.git
   cd locomotion-data-standardization
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/jmontp/locomotion-data-standardization.git
   ```

### 2. Set Up Your Environment

**Python Setup:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For specific converters (e.g., AddBiomechanics)
cd source/conversion_scripts/AddBiomechanics
pip install -r requirements.txt
```

**MATLAB Setup:**
- Ensure MATLAB R2019b or later is installed
- Add the library path: `addpath('source/lib/matlab')`

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# Or for bug fixes:
git checkout -b fix/issue-description
```

## 📝 Development Guidelines

### Code Style

**Python:**
- Follow PEP 8 style guidelines
- Use descriptive variable names
- Add type hints where appropriate
- Maximum line length: 100 characters

**MATLAB:**
- Use camelCase for function names
- Use descriptive variable names
- Include function headers with descriptions
- Indent with 4 spaces

### Variable Naming Convention

Follow our standardized naming pattern:
```
<joint>_<motion>_<measurement>_<side>_<unit>
```

Examples:
- `hip_flexion_angle_right_rad`
- `knee_flexion_velocity_left_rad_s`
- `ankle_moment_right_Nm`

See `docs/standard_spec/units_and_conventions.md` for full details.

### Documentation Standards

- All functions must have docstrings/headers
- Include examples in docstrings where helpful
- Update relevant documentation when adding features
- Add your dataset to `docs/datasets_documentation/` if contributing a converter

## 🔧 Adding a New Dataset Converter

1. **Create converter directory**: `source/conversion_scripts/YourDataset/`

2. **Implement converter script** following this template:
   ```python
   """
   Converter for YourDataset to standardized parquet format.
   
   Dataset description: Brief description
   Original format: CSV/MAT/etc.
   Subjects: N
   Tasks: List main tasks
   """
   
   def convert_to_parquet(input_path, output_path):
       # 1. Load raw data
       # 2. Map column names to standard names
       # 3. Convert units (angles to rad, forces to N)
       # 4. Add required metadata columns
       # 5. Validate data structure
       # 6. Save as parquet
   ```

3. **Create dataset documentation**: `docs/datasets_documentation/dataset_yourdataset.md`
   - Use `docs/standard_spec/dataset_template.md` as a template
   - Include sample data structure
   - Document any dataset-specific quirks

4. **Update the glossary**: Add entry to `docs/datasets_documentation/datasets_glossary.md`

5. **Add tests**: Create validation script to verify conversion

## ✅ Testing Your Changes

### Python Testing
```bash
# Run validation on your converted data
python source/tests/validation_blueprint.py your_dataset.parquet

# Test library functionality
cd docs/tutorials/python
python test_library.py
```

### MATLAB Testing
```matlab
% Test library functionality
cd('docs/tutorials/matlab')
test_library_tutorial
```

### Pre-commit Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are descriptive
- [ ] No sensitive data or credentials included

## 📤 Submitting Your Contribution

### 1. Commit Your Changes

Write clear, descriptive commit messages:
```bash
git add .
git commit -m "Add XYZ dataset converter with phase normalization support

- Implement converter for XYZ lab format
- Map 23 biomechanical variables to standard names
- Add support for multiple walking speeds
- Include dataset documentation"
```

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create a Pull Request

1. Go to your fork on GitHub
2. Click "New Pull Request"
3. Select your feature branch
4. Fill out the PR template:
   - Describe what changes you made
   - Reference any related issues
   - Include test results or examples
   - Note any breaking changes

### 4. PR Review Process

- Maintainers will review your code
- Address any requested changes
- Once approved, your PR will be merged

## 🐛 Reporting Issues

### Bug Reports

Include:
- Dataset and version affected
- Steps to reproduce
- Expected vs actual behavior
- Error messages and stack traces
- Environment details (OS, Python/MATLAB version)

### Feature Requests

Include:
- Use case description
- Proposed implementation approach
- Examples from other tools/papers
- Potential impact on existing code

## 💡 Best Practices

### For Dataset Converters

1. **Preserve raw data**: Never modify source files
2. **Handle edge cases**: Missing data, inconsistent formats
3. **Validate thoroughly**: Check biomechanical constraints
4. **Document assumptions**: Note any data interpolation or filtering
5. **Maintain traceability**: Map original to standard column names

### For Library Enhancements

1. **Backward compatibility**: Don't break existing functionality
2. **Performance**: Use vectorized operations, test with large datasets
3. **Cross-platform**: Ensure Python/MATLAB compatibility
4. **Examples**: Add usage examples to docstrings

## 🏗️ Project Architecture

Understanding the codebase structure:

```
source/
├── lib/                      # Core libraries
│   ├── python/              # Python analysis library
│   └── matlab/              # MATLAB analysis library
├── conversion_scripts/       # Dataset-specific converters
│   ├── AddBiomechanics/     
│   ├── Gtech_2023/          
│   └── Umich_2021/          
└── visualization/           # Plotting tools

docs/
├── tutorials/               # Usage guides
├── standard_spec/          # Format specifications
└── datasets_documentation/ # Dataset details
```

## 🤝 Community Guidelines

- Be respectful and constructive
- Help others in discussions
- Give credit where due
- Follow the code of conduct

## 📧 Questions?

- Open an issue for questions
- Check existing issues/PRs first
- Join discussions in the issues section

Thank you for contributing to making biomechanics data more accessible and standardized!

---

*By contributing, you agree that your contributions will be licensed under the project's MIT License.*