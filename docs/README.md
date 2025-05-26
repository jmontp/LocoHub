# 📚 Locomotion Data Standardization Documentation

Welcome to the documentation for the Locomotion Data Standardization project! This guide will help you navigate our documentation and find the resources you need.

## 🎯 Quick Start Guides

### New to the Project?
Start with our tutorials to get up and running quickly:

- **[Python Getting Started Guide](tutorials/python/getting_started_python.md)** - Learn the basics of loading and analyzing locomotion data with Python
- **[MATLAB Getting Started Guide](tutorials/matlab/getting_started_matlab.md)** - Get started with MATLAB analysis tools
- **[Library Usage Tutorial (Python)](tutorials/python/library_tutorial_python.md)** - Deep dive into the Python library features
- **[Library Usage Tutorial (MATLAB)](tutorials/matlab/library_tutorial_matlab.md)** - Comprehensive MATLAB library guide

## 📋 Documentation Structure

### 📐 [Standard Specifications](standard_spec/)
Technical specifications and conventions for the standardized data format:

- **[standard_spec.md](standard_spec/standard_spec.md)** - Core data format specification (time vs phase indexing)
- **[units_and_conventions.md](standard_spec/units_and_conventions.md)** - Variable naming conventions and units
- **[sign_conventions.md](standard_spec/sign_conventions.md)** - Biomechanical sign conventions with visual diagrams
- **[phase_calculation.md](standard_spec/phase_calculation.md)** - How gait cycles are normalized to 150 points
- **[task_vocabulary.md](standard_spec/task_vocabulary.md)** - Standardized task names and descriptions
- **[task_definitions.md](standard_spec/task_definitions.md)** - Metadata schema for task information

### 🗃️ [Dataset Documentation](datasets_documentation/)
Detailed information about available datasets:

- **[datasets_glossary.md](datasets_documentation/datasets_glossary.md)** - Overview of all available datasets
- **[dataset_gtech_2023.md](datasets_documentation/dataset_gtech_2023.md)** - Georgia Tech 2023 dataset details
- **[dataset_umich_2021.md](datasets_documentation/dataset_umich_2021.md)** - University of Michigan 2021 dataset details

### 🎓 [Tutorials](tutorials/)
Step-by-step guides and examples:

#### Python Tutorials
- **[getting_started_python.md](tutorials/python/getting_started_python.md)** - Basic data loading and visualization
- **[library_tutorial_python.md](tutorials/python/library_tutorial_python.md)** - Advanced library features
- **[efficient_reshape_guide.md](tutorials/python/efficient_reshape_guide.md)** - Performance optimization techniques

#### MATLAB Tutorials  
- **[getting_started_matlab.md](tutorials/matlab/getting_started_matlab.md)** - MATLAB basics for locomotion data
- **[library_tutorial_matlab.md](tutorials/matlab/library_tutorial_matlab.md)** - Full MATLAB library reference

### 🔧 [Development Documentation](development/)
Internal documentation for contributors:

- **[PROGRESS_TRACKING.md](development/PROGRESS_TRACKING.md)** - Project roadmap and task tracking
- **[NAMING_CONVENTION_UPDATE_SUMMARY.md](development/NAMING_CONVENTION_UPDATE_SUMMARY.md)** - Migration status for naming conventions

## 🚀 Common Tasks

### I want to...

**Load and visualize data:**
- Python: See [Getting Started Python](tutorials/python/getting_started_python.md)
- MATLAB: See [Getting Started MATLAB](tutorials/matlab/getting_started_matlab.md)

**Understand the data format:**
- Read the [Standard Specification](standard_spec/standard_spec.md)
- Check [Units and Conventions](standard_spec/units_and_conventions.md)

**Convert my own dataset:**
- See [Contributing Guide](../CONTRIBUTING.md) for adding new converters
- Use [Dataset Template](standard_spec/dataset_template.md) for documentation

**Perform advanced analysis:**
- Python: [Library Tutorial](tutorials/python/library_tutorial_python.md)
- MATLAB: [Library Tutorial](tutorials/matlab/library_tutorial_matlab.md)

**Find specific task definitions:**
- Check [Task Vocabulary](standard_spec/task_vocabulary.md)
- See [Task Definitions Schema](standard_spec/task_definitions.md)

## 📊 Key Concepts

### Data Formats
- **Time-indexed**: Continuous time series at original sampling rate
- **Phase-indexed**: Normalized to 150 points per gait cycle

### Variable Naming
Pattern: `<joint>_<motion>_<measurement>_<side>_<unit>`  
Example: `knee_flexion_angle_left_rad`

### Validation Layers
1. Physics constraints (joint angle limits)
2. Continuity checks
3. Statistical outlier detection
4. Completeness verification
5. Cross-variable consistency

## 🔍 Finding Information

### By Topic
- **Biomechanics**: [Sign Conventions](standard_spec/sign_conventions.md), [Units](standard_spec/units_and_conventions.md)
- **Data Processing**: [Phase Calculation](standard_spec/phase_calculation.md), [Tutorials](tutorials/)
- **Datasets**: [Glossary](datasets_documentation/datasets_glossary.md), Individual dataset docs
- **Development**: [Contributing](../CONTRIBUTING.md), [Progress Tracking](development/PROGRESS_TRACKING.md)

### By Experience Level
- **Beginner**: Start with [tutorials](tutorials/)
- **Intermediate**: Explore [library documentation](tutorials/python/library_tutorial_python.md)
- **Advanced**: Check [standard specifications](standard_spec/) and [contribute](../CONTRIBUTING.md)

## 💡 Tips

1. **Always check units** - Our standard uses radians for angles, m/s for velocities
2. **Use 3D arrays** for efficient multi-cycle analysis (see [reshape guide](tutorials/python/efficient_reshape_guide.md))
3. **Validate your data** using the built-in validation functions
4. **Follow naming conventions** to ensure compatibility

## 🤝 Need Help?

- Check if your question is answered in the relevant tutorial
- Look for similar examples in the documentation
- Open an issue on GitHub for bugs or unclear documentation
- See [Contributing Guide](../CONTRIBUTING.md) for how to improve docs

---

*This documentation is actively maintained. If you find errors or have suggestions, please contribute!*