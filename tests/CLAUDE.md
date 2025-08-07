# CLAUDE.md - Tests Directory

Testing and validation framework for the LocoHub project.

**File Creation Requirement**: Ask user permission before creating ANY new test file.

## File Conventions

**CRITICAL File Distinctions**:
- **`test_*.py`**: Headless validation for automated testing (no visual outputs)
- **`demo_*.py`**: Generate plots and visual outputs for user observation

## Test File Standards

**Required Documentation**:
```python
"""
{Test File Name}

Created: YYYY-MM-DD with user permission
Purpose: {One-line summary of what is being tested}

Intent: {Why this test exists and what functionality it validates}
"""
```

**Test Categories**:
- Unit tests for individual methods
- Integration tests with realistic workflows  
- Edge case tests for robustness
- Performance tests for scalability

## Demo File Standards

**Output Directory**: `sample_plots/demo_{module_name}/`
**Plot Naming**: Use descriptive prefixes (`1_baseline_`, `2_with_data_`)

**Required Features**:
- Visual outputs with detailed explanations
- Realistic demonstration scenarios
- Integration patterns with other modules
- Educational value for developers

## Testing Patterns

**pytest Compatibility**:
```python
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
```

**Common Test Methods**:
- `test_initialization()` - Module setup
- `test_{method}_basic()` - Core functionality
- `test_{method}_edge_cases()` - Boundary conditions
- `test_error_handling()` - Exception scenarios
- `test_performance()` - Large dataset handling

## Quality Standards

**Test Requirements**:
- All public methods tested
- Realistic biomechanical data used
- Clear assertion messages
- Performance benchmarks monitored

**Demo Requirements**:
- Publication-ready visual outputs
- Step-by-step explanations
- Before/after comparisons
- Best practices demonstrated

---

*Ensures comprehensive validation while providing educational resources for developers.*