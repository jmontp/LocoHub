# Code Standards

Guidelines for writing consistent, maintainable code.

## Python Style

### Formatting
```python
# Use Black for auto-formatting
black lib/ tests/ --line-length 100

# Check style with flake8
flake8 lib/ --max-line-length 100
```

### Naming Conventions
```python
# Variables: snake_case
knee_angle_data = load_data()

# Constants: UPPER_SNAKE_CASE
MAX_KNEE_FLEXION = 2.5  # radians

# Classes: PascalCase
class LocomotionData:
    pass

# Private methods: leading underscore
def _internal_helper():
    pass
```

### Type Hints
```python
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd

def process_data(
    data: pd.DataFrame,
    variables: List[str],
    task: Optional[str] = None
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Process locomotion data.
    
    Args:
        data: Input dataframe with locomotion data
        variables: List of variable names to process
        task: Optional task filter
        
    Returns:
        Tuple of (data_array, statistics_dict)
    """
    # Implementation
    return data_array, stats
```

### Docstrings
```python
def calculate_stride_metrics(data: np.ndarray) -> Dict[str, float]:
    """Calculate stride-level metrics from gait data.
    
    Computes temporal and spatial metrics for each stride including
    stride length, cadence, and symmetry indices.
    
    Args:
        data: 3D array of shape (n_strides, 150, n_variables)
            containing phase-normalized gait data.
    
    Returns:
        Dictionary with keys:
            - 'stride_length': Average stride length in meters
            - 'cadence': Steps per minute
            - 'symmetry_index': Left-right symmetry (0-1)
    
    Raises:
        ValueError: If data shape is invalid
        RuntimeError: If calculation fails
    
    Example:
        >>> data = LocomotionData('dataset.parquet').data_matrix
        >>> metrics = calculate_stride_metrics(data)
        >>> print(f"Cadence: {metrics['cadence']:.1f} steps/min")
    """
```

## MATLAB Style

### Function Headers
```matlab
function [output1, output2] = processLocomotionData(input_data, options)
%PROCESSLOCOMOTIONDATA Process locomotion data for analysis
%
% Syntax:
%   output = processLocomotionData(input_data)
%   [output1, output2] = processLocomotionData(input_data, options)
%
% Description:
%   Processes raw locomotion data and returns analyzed results.
%
% Inputs:
%   input_data - Struct with fields 'data' and 'metadata'
%   options    - (Optional) Struct with processing options
%
% Outputs:
%   output1 - Processed data matrix
%   output2 - Statistics structure
%
% Example:
%   data = load('walking_data.mat');
%   results = processLocomotionData(data);
%
% See also: LOCOMOTIONDATA, VALIDATEDATA

% Author: Your Name
% Date: 2024-03-15
% Version: 1.0
```

### Variable Naming
```matlab
% Use camelCase for variables
kneeAngleData = loadData();

% Use UPPER_CASE for constants
MAX_KNEE_FLEXION = 2.5;  % radians

% Use descriptive names
numberOfStrides = size(data, 1);  % Not: n = size(data, 1)
```

## Documentation Standards

### Code Comments
```python
# Good: Explain why, not what
# Convert to radians because validation expects radians
angle_rad = np.deg2rad(angle_deg)

# Bad: Redundant comment
# Set x to 5
x = 5

# Good: Complex logic explanation
# Use 3D array operations instead of loops for 100x speedup.
# Shape: (n_strides, 150, n_vars) -> (n_strides, n_vars)
mean_values = data_matrix.mean(axis=1)
```

### README Files
```markdown
# Module/Directory Name

Brief description of what this module does.

## Overview
More detailed explanation of the module's purpose and design.

## Usage
```python
# Code example showing basic usage
from module import MainClass
obj = MainClass()
result = obj.process()
```

## Files
- `main.py` - Core functionality
- `utils.py` - Helper functions
- `constants.py` - Configuration values

## Testing
```bash
pytest tests/test_module.py
```
```

### Changelog Entries
```markdown
## [1.2.0] - 2024-03-15

### Added
- New pelvis_tilt_angle variable to standard variables
- Automated validation range tuning

### Changed
- Improved performance of LocomotionData loading by 50%
- Updated knee moment sign convention (breaking change)

### Fixed
- Bug in phase normalization for incomplete cycles
- Memory leak in validation plotting

### Deprecated
- Old GTech converter (use GTech_2023 instead)
```

## Git Commit Messages

### Format
```
<type>: <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples
```bash
# Good: Clear and specific
git commit -m "fix: Correct knee moment sign convention

Knee extension moments were incorrectly negative. Changed sign
convention to match Winter (2009) where positive = extension.

Fixes #123"

# Good: Feature addition
git commit -m "feat: Add automated validation range tuning

Implements statistical method to suggest validation ranges
based on multiple reference datasets. Reduces manual tuning
time from hours to minutes.

Closes #456"

# Bad: Vague
git commit -m "Fixed stuff"
git commit -m "Updates"
```

## Code Review Checklist

Before submitting PR:

- [ ] Tests pass locally (`pytest tests/`)
- [ ] Code formatted (`black lib/ tests/`)
- [ ] Type hints added for new functions
- [ ] Docstrings updated/added
- [ ] No commented-out code
- [ ] No print statements (use logging)
- [ ] Changes documented in CHANGELOG
- [ ] PR description explains why, not just what

## Performance Guidelines

### Use NumPy Operations
```python
# Good: Vectorized operation
mean_values = data_matrix.mean(axis=1)

# Bad: Python loops
mean_values = []
for stride in data_matrix:
    mean_values.append(stride.mean())
```

### Profile Before Optimizing
```python
import cProfile
import pstats

# Profile code
profiler = cProfile.Profile()
profiler.enable()

# Your code here
process_large_dataset()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(10)  # Top 10 time consumers
```

### Memory Efficiency
```python
# Good: Generator for large datasets
def load_subjects(file_pattern):
    for file in glob.glob(file_pattern):
        yield pd.read_parquet(file)

# Bad: Loading all at once
def load_subjects(file_pattern):
    return [pd.read_parquet(f) for f in glob.glob(file_pattern)]
```

## Security Considerations

- Never commit credentials or API keys
- Validate all file paths before reading/writing
- Use `pathlib` for path operations
- Sanitize user inputs in web interfaces
- Keep dependencies updated

## Next: [Release Process](releases.md)