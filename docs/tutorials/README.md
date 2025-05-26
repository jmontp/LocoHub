# Locomotion Data Analysis Tutorials

This directory contains comprehensive tutorials for analyzing standardized locomotion data using both Python and MATLAB.

## Directory Structure

```
tutorials/
├── python/          # Python tutorials and examples
├── matlab/          # MATLAB tutorials and examples
├── test_files/      # Sample data files for tutorials
└── README.md        # This file
```

## Python Tutorials (`python/`)

### Getting Started
- **`getting_started_python.md`** - Basic pandas operations for locomotion data
- **`library_tutorial_python.md`** - Comprehensive guide to using the LocomotionData library

### Advanced Topics
- **`efficient_data_access.py`** - Efficient methods for accessing phase-indexed data
- **`efficient_reshape_3d.py`** - 3D array reshaping operations
- **`efficient_reshape_guide.md`** - Guide to efficient data reshaping techniques

### Test Scripts
- **`test_python_tutorial.py`** - Test script for basic tutorial operations

## MATLAB Tutorials (`matlab/`)

### Getting Started
- **`getting_started_matlab.md`** - Basic table operations for locomotion data
- **`library_tutorial_matlab.md`** - Comprehensive guide to using the LocomotionData class

### Test Scripts
- **`test_matlab_tutorial.m`** - Test script for basic tutorial operations

## Test Files (`test_files/`)

Sample data files used in tutorials:
- **`locomotion_data.csv`** - Sample locomotion time series data
- **`task_info.csv`** - Sample task information for merging
- **`*.png`** - Example output plots from tutorials

## Quick Start

### Python
```python
# Using the library (recommended)
from source.lib.python.locomotion_analysis import LocomotionData
loco = LocomotionData('path/to/data.parquet')
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
```

### MATLAB
```matlab
% Using the library (recommended)
addpath('source/lib/matlab');
loco = LocomotionData('path/to/data.parquet');
[data3D, features] = loco.getCycles('SUB01', 'normal_walk');
```

## Prerequisites

### Python
- pandas ≥ 1.3.0
- numpy ≥ 1.20.0
- matplotlib ≥ 3.3.0
- pyarrow ≥ 5.0.0

### MATLAB
- MATLAB R2019b or later
- Statistics and Machine Learning Toolbox (optional)

## Tutorial Progression

1. **Start with Getting Started guides** to understand basic data operations
2. **Move to Library tutorials** for production-ready analysis workflows
3. **Explore efficient data access** for performance optimization
4. **Use test files** to practice with sample data

## Additional Resources

- **Library Documentation**: See `source/lib/README.md`
- **Data Format Specification**: See `docs/standard_spec/`
- **Example Datasets**: See `docs/datasets_documentation/`

---

*These tutorials are part of the Locomotion Data Standardization project. For more information, see the main repository README.*