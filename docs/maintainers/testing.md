# Testing Guide

How to run, write, and maintain tests for the locomotion data system.

## Running Tests

### Quick Test
```bash
# Run core tests only (fast)
pytest tests/test_locomotion_data_library.py -v

# Run with coverage
pytest tests/ --cov=lib --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Full Test Suite
```bash
# All tests with verbose output
pytest tests/ -v

# Parallel execution (faster)
pytest tests/ -n auto

# Stop on first failure (debugging)
pytest tests/ -x
```

### Specific Tests
```bash
# Run tests matching a pattern
pytest tests/ -k "validation"

# Run a specific test function
pytest tests/test_validation_parser.py::test_parse_kinematic_spec

# Run with debugging output
pytest tests/ -s  # Shows print statements
```

## Test Organization

```
tests/
├── test_*.py                    # Unit tests
├── demo_*.py                     # Visual demonstrations
├── test_data/                    # Test datasets
│   ├── demo_clean_phase.parquet # Valid data
│   └── demo_violations_phase.parquet # Invalid data
└── sample_plots/                 # Expected output images
```

## Writing Tests

### Basic Test Structure
```python
# tests/test_new_feature.py

import pytest
import numpy as np
from lib.core.locomotion_analysis import LocomotionData

class TestNewFeature:
    """Test suite for new feature."""
    
    def setup_method(self):
        """Run before each test."""
        self.data = LocomotionData('tests/test_data/demo_clean_phase.parquet')
    
    def test_feature_basic(self):
        """Test basic functionality."""
        result = self.data.new_feature()
        assert result is not None
        assert len(result) > 0
    
    def test_feature_edge_case(self):
        """Test edge cases."""
        with pytest.raises(ValueError):
            self.data.new_feature(invalid_param=-1)
```

### Testing Data Processing
```python
def test_data_transformation():
    """Test data transformation preserves shape."""
    # Arrange
    original_data = np.random.randn(10, 150, 20)
    
    # Act
    transformed = transform_function(original_data)
    
    # Assert
    assert transformed.shape == original_data.shape
    assert not np.isnan(transformed).any()
    assert np.allclose(transformed.mean(), 0, atol=0.1)
```

### Testing Validation
```python
def test_validation_catches_errors():
    """Test validator identifies known issues."""
    # Use data with known problems
    validator = PhaseValidator()
    results = validator.validate('tests/test_data/demo_violations_phase.parquet')
    
    # Should fail validation
    assert not results['is_valid']
    assert 'knee_flexion_angle_ipsi_rad' in results['failed_variables']
    assert results['num_invalid_strides'] > 0
```

### Testing File I/O
```python
def test_parquet_round_trip(tmp_path):
    """Test saving and loading preserves data."""
    # Create test data
    original = create_test_dataset()
    
    # Save to temporary file
    output_file = tmp_path / "test.parquet"
    original.to_parquet(output_file)
    
    # Load and compare
    loaded = pd.read_parquet(output_file)
    pd.testing.assert_frame_equal(original, loaded)
```

## Test Fixtures

### Shared Test Data
```python
# tests/conftest.py

import pytest
from lib.core.locomotion_analysis import LocomotionData

@pytest.fixture
def sample_data():
    """Provide sample dataset for tests."""
    return LocomotionData('tests/test_data/demo_clean_phase.parquet')

@pytest.fixture
def invalid_data():
    """Provide dataset with known issues."""
    return LocomotionData('tests/test_data/demo_violations_phase.parquet')

# Use in tests:
def test_with_fixture(sample_data):
    assert sample_data.num_cycles > 0
```

## Testing Best Practices

### 1. Test One Thing
```python
# Good: Focused test
def test_variable_name_validation():
    """Test that invalid variable names raise error."""
    with pytest.raises(ValueError, match="not in standard variables"):
        validate_variable_name("invalid_name")

# Bad: Testing multiple things
def test_everything():
    """Test all the things."""  # Too broad!
```

### 2. Use Descriptive Names
```python
# Good
def test_knee_angle_stays_within_physiological_range():
    
# Bad
def test_1():
```

### 3. Test Edge Cases
```python
def test_empty_dataset():
    """Test behavior with empty data."""
    
def test_single_stride():
    """Test with minimum valid data."""
    
def test_missing_columns():
    """Test graceful handling of incomplete data."""
```

### 4. Use Assertions Wisely
```python
# Good: Specific assertion with message
assert result > 0, f"Expected positive value, got {result}"

# Better: Use pytest.approx for floats
assert result == pytest.approx(expected, rel=1e-3)

# Best: Multiple related assertions
assert result.shape == (10, 150, 20)
assert result.dtype == np.float64
assert not np.isnan(result).any()
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Nightly for full validation suite

### CI Configuration
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=lib
```

## Performance Testing

### Benchmarking
```python
# tests/test_performance.py

import time

def test_loading_performance(benchmark):
    """Test data loading stays fast."""
    def load_data():
        return LocomotionData('large_dataset.parquet')
    
    # Should complete in < 1 second
    result = benchmark(load_data)
    assert benchmark.stats['mean'] < 1.0
```

### Memory Testing
```python
import tracemalloc

def test_memory_usage():
    """Test memory usage stays reasonable."""
    tracemalloc.start()
    
    # Load large dataset
    data = LocomotionData('large_dataset.parquet')
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Should use < 1GB for typical dataset
    assert peak / 1024 / 1024 < 1000  # MB
```

## Debugging Failed Tests

### Get More Information
```bash
# Show local variables on failure
pytest tests/ --showlocals

# Drop into debugger on failure
pytest tests/ --pdb

# Show full diff for assertions
pytest tests/ -vv
```

### Common Issues

| Problem | Solution |
|---------|----------|
| Import errors | Check PYTHONPATH, activate venv |
| File not found | Use absolute paths or pytest fixtures |
| Floating point comparison | Use `pytest.approx()` |
| Random failures | Set random seed, check for race conditions |
| Slow tests | Use pytest-xdist for parallel execution |

## Next: [Code Standards](standards.md)