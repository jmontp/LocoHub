# Filters By Phase Plots Test Suite

This directory contains comprehensive test cases for the enhanced `filters_by_phase_plots.py` functionality, which now supports data overlay with violation highlighting.

## Test Files

### 1. `test_filters_by_phase_plots.py`
**Full pytest-compatible test suite** with comprehensive test coverage:

#### Test Classes:
- **`TestFiltersByPhasePlots`**: Main functionality tests
- **`TestViolationScenarios`**: Specific violation detection scenarios

#### Key Test Cases:
- ✅ **Basic plot generation** (validation ranges only)
- ✅ **Data overlay functionality** (with numpy array data)
- ✅ **Violation detection** (global vs local violations)
- ✅ **Color coding verification** (red/pink highlighting)
- ✅ **Error handling** (missing tasks, wrong data shapes)
- ✅ **Kinematic vs kinetic modes**
- ✅ **Real validation file integration**

#### Fixtures:
- `sample_kinematic_validation_data`: Test validation ranges
- `valid_kinematic_data`: Clean data that passes all filters
- `violating_kinematic_data`: Data with known violations
- `temp_output_dir`: Temporary directory for test outputs

### 2. `integration_test_filters_plots.py`
**Standalone integration test** that runs without external dependencies:

#### Test Functions:
1. **`test_basic_functionality()`**: Basic plot generation without data
2. **`test_data_overlay()`**: Plot generation with data overlay
3. **`test_violation_detection()`**: Violation detection logic
4. **`test_real_validation_file()`**: Integration with actual validation files

#### Features:
- No external dependencies (pytest not required)
- Self-contained test data generation
- Clear pass/fail reporting
- Temporary file cleanup

## New Functionality Tested

### 1. Data Parameter Enhancement
```python
create_filters_by_phase_plot(
    validation_data=validation_data,
    task_name='level_walking',
    output_dir='output/',
    mode='kinematic',
    data=numpy_array  # NEW: Shape (num_steps, 150, num_features)
)
```

**Tested aspects:**
- ✅ Backward compatibility (data=None works as before)
- ✅ Correct data shape handling (num_steps, 150, num_features)
- ✅ Feature mapping (hip_ipsi=0, hip_contra=1, knee_ipsi=2, etc.)
- ✅ File naming with `_with_data` suffix

### 2. Violation Detection System
```python
global_violations, local_violations = detect_filter_violations(
    data, task_data, feature_map, mode, current_feature_idx
)
```

**Tested scenarios:**
- ✅ **Global violations**: Steps that violate any feature filter
- ✅ **Local violations**: Steps that violate the current subplot's feature
- ✅ **Phase-based checking**: Validation at 0%, 25%, 50%, 75%, 100%
- ✅ **Multiple violation types**: Single vs multiple feature violations

### 3. Color-Coded Visualization
**Color scheme tested:**
- 🔴 **Bright red**: Steps violating current feature (local violations)
- 🩷 **Pink**: Steps violating other features (global but not local)
- ⚫ **Gray**: Valid steps (no violations)

**Visual properties tested:**
- ✅ Line thickness increases for violations
- ✅ Alpha transparency highlights violations
- ✅ Legend integration for violation types

## Test Data Scenarios

### Valid Data Pattern
```python
# Realistic gait patterns within validation ranges
hip_pattern = 0.25 * sin(2π * phase / 100) + 0.3      # Valid hip flexion
knee_pattern = 0.4 * sin(π * phase / 100) + 0.3       # Valid knee flexion  
ankle_pattern = -0.15 * sin(2π * phase / 100) + 0.1   # Valid ankle pattern
```

### Violation Test Scenarios
```python
# Step 0: Hip ipsi violation (bright red in hip ipsi plot)
data[0, :, 0] += 0.8  # Exceeds upper validation bound

# Step 1: Knee ipsi violation (bright red in knee ipsi plot)  
data[1, :, 2] += 1.2  # Exceeds upper validation bound

# Step 2: Ankle ipsi violation (bright red in ankle ipsi plot)
data[2, :, 4] -= 0.8  # Below lower validation bound

# Step 3: Multiple violations (red in hip + knee plots)
data[3, :, 0] += 0.7  # Hip violation
data[3, :, 2] += 1.0  # Knee violation

# Step 4: Contralateral violation (red in hip contra plot)
data[4, :, 1] += 0.9  # Hip contra violation

# Step 5: Valid (gray in all plots)
```

## Running the Tests

### Option 1: Full Test Suite (requires pytest)
```bash
cd source/tests/
pytest test_filters_by_phase_plots.py -v
```

### Option 2: Integration Tests (standalone)
```bash
cd /path/to/project/
python3 source/tests/integration_test_filters_plots.py
```

### Option 3: Manual Testing with Synthetic Data
```python
import numpy as np
from filters_by_phase_plots import create_filters_by_phase_plot

# Create test data with violations
data = np.random.randn(10, 150, 6)  # 10 steps, 150 phase points, 6 features
data[0, :, 0] += 2.0  # Add hip violation to step 0

# Generate plot with violation highlighting
filepath = create_filters_by_phase_plot(
    validation_data, 'level_walking', 'output/', 'kinematic', data=data
)
```

## Expected Test Outputs

### Console Output
```
🧪 Running Filters By Phase Plots Integration Tests
============================================================
Test 1: Basic plot generation (no data overlay)
✅ PASS: Basic plot generated successfully

Test 2: Data overlay functionality  
✅ PASS: Data overlay plot generated successfully

Test 3: Violation detection
   Global violations detected: [0, 1, 2, 3, 4]
   Local violations (hip ipsi): [0, 3, 4]
✅ PASS: Violation detection working correctly

Test 4: Real validation file integration
✅ PASS: Real validation file parsed successfully

🎯 Overall: 4/4 tests passed
🎉 All tests passed!
```

### Generated Files
- `level_walking_kinematic_filters_by_phase.png` (validation ranges only)
- `level_walking_kinematic_filters_by_phase_with_data.png` (with data overlay)

## Validation Verification

### Manual Verification Steps
1. **Open generated plots** and verify:
   - Red lines appear for steps with local violations
   - Pink lines appear for steps with global violations  
   - Gray lines appear for valid steps
   - Validation ranges (colored boxes) are displayed correctly

2. **Check violation detection** by examining console output:
   - Global violations should include all violating steps
   - Local violations should be subset of global violations
   - No false positives for valid steps

3. **Verify file naming**:
   - Plots without data: `*_filters_by_phase.png`
   - Plots with data: `*_filters_by_phase_with_data.png`

## Troubleshooting

### Common Issues
1. **"Task not found" error**: Ensure validation data contains the requested task
2. **No violations detected**: Check data ranges vs validation bounds
3. **All steps show violations**: Data might be completely outside valid ranges
4. **Import errors**: Ensure source/visualization is in Python path

### Debug Tips
```python
# Print validation ranges
print(validation_data['level_walking'][0])

# Check data ranges at specific phases
phase_indices = [0, 37, 75, 112, 149]  # 0%, 25%, 50%, 75%, 100%
print(f"Data at key phases: {data[step_idx, phase_indices, feature_idx]}")

# Verify feature mapping
feature_map = {
    ('hip_flexion_angle', 'ipsi'): 0,
    ('hip_flexion_angle', 'contra'): 1,
    # ... etc
}
```

## Future Enhancements

### Planned Test Additions
- [ ] **Kinetic mode comprehensive testing** (forces and moments)
- [ ] **Performance testing** with large datasets (1000+ steps)
- [ ] **Memory usage validation** for different data sizes
- [ ] **Cross-platform testing** (Windows/Mac/Linux)
- [ ] **Edge case testing** (empty data, single step, etc.)

### Test Data Improvements
- [ ] **Real dataset testing** with actual gait data
- [ ] **Pathological pattern testing** (e.g., limping, asymmetric gait)
- [ ] **Task-specific validation** (stairs, running, jumping)
- [ ] **Multi-dataset comparison** testing

This comprehensive test suite ensures the enhanced filters by phase plotting functionality works correctly for validation reporting and data quality assessment in the locomotion data standardization framework.