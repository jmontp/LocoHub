# Development and Contribution Workflows

Development guide for contributing to the locomotion data standardization framework.

**Quick Start:** [Setup](#setup) • [Code Structure](#code-structure) • [Adding Features](#adding-features) • [Testing](#testing) • [Deployment](#deployment)

## Setup

### Development Environment

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/locomotion-data-standardization.git
cd locomotion-data-standardization
git remote add upstream https://github.com/jmontp/locomotion-data-standardization.git

# Python dependencies
pip install pandas numpy matplotlib pyarrow scipy

# Optional: AddBiomechanics conversion
pip install -r contributor_scripts/AddBiomechanics/requirements.txt

# MATLAB setup (R2019b+)
# Add to MATLAB path: addpath('source/lib/matlab')
```

### Directory Structure

The project follows a clean architecture with separation of concerns:

```
lib/core/                    # Core Python libraries
├── locomotion_analysis.py   # Main LocomotionData class
├── feature_constants.py     # Feature definitions (single source of truth)
└── examples.py              # Usage examples

lib/validation/              # Validation and quality assurance
├── dataset_validator_phase.py    # Main validator
├── filters_by_phase_plots.py     # Validation visualizations
└── validation_expectations_parser.py  # Rule parsing

contributor_scripts/         # Dataset conversion tools
├── AddBiomechanics/        # AddBiomechanics converter
├── Gtech_2023/             # Georgia Tech 2023 converter
└── Umich_2021/             # University of Michigan 2021 converter

tests/                       # Testing framework
├── test_locomotion_data_library.py  # Core library tests
├── demo_*.py               # Visual validation tests
└── test_data/              # Test datasets

docs/                        # Documentation
├── standard_spec/          # Data format specification
├── tutorials/              # User tutorials
└── datasets_documentation/ # Dataset-specific docs
```

## Code Structure

### Core Design Principles

**Minimal, Understandable Code:**
- Single responsibility per function/class
- Clear naming without requiring comments
- Comprehensive error handling with explicit failures
- No code duplication - shared modules for common functionality

**Memory-Safe Operations:**
- Efficient vectorized operations using NumPy
- Lazy loading for large datasets
- Caching mechanisms for expensive operations
- Memory-conscious validation workflows

### Feature Constants System

All biomechanical features are defined in `lib/core/feature_constants.py`:

```python
# Standard feature ordering (matches plotting expectations)
ANGLE_FEATURES = [
    'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', 
    'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
]

# Get feature mappings
from lib.core.feature_constants import get_kinematic_feature_map
feature_map = get_kinematic_feature_map()
```

**Variable Naming Convention:**
`<joint>_<motion>_<measurement>_<side>_<unit>`

Examples:
- `knee_flexion_angle_contra_rad`
- `hip_moment_ipsi_Nm`
- `ankle_flexion_velocity_ipsi_rad_s`

### LocomotionData Class Architecture

```python
class LocomotionData:
    """
    Core class for biomechanical data analysis with 3D array operations.
    
    Architecture:
    - data: 3D numpy array [subjects, time_points, features]
    - Efficient reshape operations with caching
    - Vectorized statistical calculations
    - Integrated plotting capabilities
    """
    
    def __init__(self, data_source, mode='kinematic'):
        # Load data with automatic format detection
        
    def get_3d_array(self):
        # Efficient reshape with caching mechanism
        
    def calculate_statistics(self):
        # Vectorized mean, std, ROM calculations
        
    def plot_trajectories(self):
        # Integrated visualization
```

## Adding Features

### Adding New Datasets

Create converter in `contributor_scripts/YourDataset/`:

```python
def convert_to_parquet(input_path, output_path):
    """
    Convert dataset to standardized format.
    
    Required steps:
    1. Load raw data
    2. Map variables to standard names using feature_constants
    3. Convert units (angles→radians, forces→Newtons)
    4. Add metadata columns: subject, task, phase/time_s
    5. Validate with LocomotionData library
    6. Save as parquet format
    """
    
    # 1. Load raw data
    raw_data = load_dataset_specific_format(input_path)
    
    # 2. Variable mapping
    from lib.core.feature_constants import ANGLE_FEATURES
    variable_mapping = {
        'hip_flex_R': 'hip_flexion_angle_contra_rad',
        'knee_flex_L': 'knee_flexion_angle_ipsi_rad',
        # ... complete mapping
    }
    
    # 3. Unit conversion
    for old_name, new_name in variable_mapping.items():
        if 'angle' in new_name and 'deg' in old_name:
            data[new_name] = np.radians(data[old_name])
    
    # 4. Add required metadata
    data['subject'] = subject_ids
    data['task'] = task_labels  # Must match validation expectations
    data['phase'] = phase_values  # 0-100 for phase-indexed data
    
    # 5. Validation
    from lib.core.locomotion_analysis import LocomotionData
    validator = LocomotionData(data)
    validator.validate_biomechanical_constraints()
    
    # 6. Save
    data.to_parquet(output_path)
```

**Required Documentation:**
Add dataset description to `docs/datasets_documentation/dataset_yourname.md`

### Adding Validation Rules

Validation rules are defined in markdown files:

```markdown
# docs/standard_spec/validation_expectations_kinematic.md

## Walking - Hip Flexion Angle (Ipsilateral)

**Variable:** `hip_flexion_angle_ipsi_rad`
**Task:** `walking`
**Phases:** `0-100`

### Validation Rules
- **Range:** `-0.5` to `1.2` radians
- **ROM:** `0.8` to `1.5` radians
- **Typical Value:** `0.4` radians at mid-stance
```

Rules are automatically parsed by `validation_expectations_parser.py`.

### Adding Library Features

Follow the established patterns:

```python
def new_analysis_method(self, parameter=None):
    """
    Add new analysis capability.
    
    Args:
        parameter: Description with type hints
        
    Returns:
        Analysis results with clear structure
        
    Raises:
        ValueError: Explicit error conditions
    """
    # Input validation
    if parameter is None:
        raise ValueError("Parameter is required")
    
    # Efficient numpy operations
    result = np.vectorized_operation(self.data)
    
    # Return structured results
    return {
        'values': result,
        'metadata': {'method': 'new_analysis_method'},
        'statistics': self._calculate_stats(result)
    }
```

## Testing

### Test Types

**Unit Tests:** `test_*.py` - Automated validation
```bash
python tests/test_locomotion_data_library.py
python tests/test_validation_parser.py
```

**Visual Tests:** `demo_*.py` - Manual inspection
```bash
python tests/demo_dataset_validator_phase.py
python tests/demo_filters_by_phase_plots.py
```

**Integration Tests:** End-to-end workflow validation
```bash
python -c "import sys; sys.path.append('lib/core'); from examples import run_basic_example; run_basic_example()"
```

### Test Patterns

```python
def test_feature_with_edge_cases():
    """Test with comprehensive edge case coverage."""
    
    # Normal case
    result = function_under_test(normal_input)
    assert result.shape == expected_shape
    
    # Edge cases
    with pytest.raises(ValueError, match="specific error"):
        function_under_test(invalid_input)
    
    # Boundary conditions
    boundary_result = function_under_test(boundary_input)
    assert np.allclose(boundary_result, expected_boundary)
    
    # Memory efficiency
    large_input = generate_large_test_data()
    memory_before = get_memory_usage()
    large_result = function_under_test(large_input)
    memory_after = get_memory_usage()
    assert memory_after - memory_before < memory_threshold
```

### MATLAB Testing

```matlab
% tests/test_tutorial_library_matlab.m
function test_tutorial_library_matlab()
    % Add library to path
    addpath('../source/lib/matlab');
    
    % Test basic functionality
    data = LocomotionData('test_data/demo_walking_phase.parquet');
    stats = data.calculate_statistics();
    
    % Validate results
    assert(size(stats.mean, 2) == 6);  % 6 kinematic features
    assert(all(~isnan(stats.mean(:))));  % No NaN values
    
    fprintf('MATLAB library tests passed\n');
end
```

## Deployment

### Pre-commit Checklist

- [ ] **Code Quality:** PEP 8 compliance, type hints, docstrings
- [ ] **Tests Pass:** All unit tests, integration tests, visual demos
- [ ] **Documentation:** Updated tutorials, API docs, examples
- [ ] **No Sensitive Data:** No personal information, API keys, or raw data
- [ ] **Memory Safety:** Large operations tested for memory efficiency

### Commit Message Format

```bash
git commit -m "Add XYZ dataset converter

- Map 23 variables to standard naming convention
- Support multiple walking speeds and inclines
- Include comprehensive biomechanical validation
- Add dataset documentation and examples

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>"
```

### Pull Request Process

1. **Branch:** `git checkout -b feature/descriptive-name`
2. **Develop:** Follow testing and documentation standards
3. **Validate:** Run full test suite, check memory usage
4. **Submit:** Create PR with comprehensive description
5. **Review:** Address feedback, maintain code quality

## Performance Considerations

### Memory-Safe Operations

```python
# Efficient data loading
def load_large_dataset(file_path, chunk_size=10000):
    """Load dataset in chunks to manage memory."""
    chunks = []
    for chunk in pd.read_parquet(file_path, chunksize=chunk_size):
        processed_chunk = process_chunk(chunk)
        chunks.append(processed_chunk)
    return pd.concat(chunks, ignore_index=True)

# Vectorized operations
def efficient_calculation(data_3d):
    """Use numpy broadcasting for 3D operations."""
    # Avoid loops, use vectorized operations
    return np.mean(data_3d, axis=1)  # Mean across time dimension
```

### Validation Performance

```python
# Memory-conscious validation
def validate_large_dataset(data, batch_size=1000):
    """Validate dataset in batches."""
    n_subjects = len(data['subject'].unique())
    
    for i in range(0, n_subjects, batch_size):
        batch_subjects = data['subject'].unique()[i:i+batch_size]
        batch_data = data[data['subject'].isin(batch_subjects)]
        validate_batch(batch_data)
```

## Architecture Guidelines

### Single Source of Truth

- **Feature Definitions:** `lib/core/feature_constants.py`
- **Validation Rules:** `docs/standard_spec/validation_expectations_*.md`
- **Task Definitions:** `docs/standard_spec/task_definitions.md`

### Error Handling Philosophy

```python
# Explicit failures over silent errors
if not self._validate_input(data):
    raise ValueError(f"Invalid data format: {self._get_error_details(data)}")

# Comprehensive error context
try:
    result = complex_operation(data)
except Exception as e:
    raise RuntimeError(f"Operation failed for dataset {dataset_name}: {str(e)}") from e
```

### Refactoring Guidelines

When you see code duplication:

1. **Extract Common Functionality:** Create shared modules
2. **Use Imports Over Copy-Paste:** Import from lib/core or lib/validation
3. **Suggest Better Patterns:** Propose architectural improvements
4. **Maintain Backwards Compatibility:** During pre-release phase, focus on clean implementation

---

*This framework is pre-release. Focus on optimal implementation over migration concerns.*