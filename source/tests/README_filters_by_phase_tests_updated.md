# Filters by Phase Plots - Updated Testing Documentation

This document describes the updated test framework for the refactored `filters_by_phase_plots.py` functionality with clean separation of concerns.

## Overview

The `filters_by_phase_plots.py` module has been refactored with a cleaner architecture:

1. **Validation logic**: Handled externally by user or helper functions
2. **Plotting logic**: Focuses purely on visualization  
3. **Step classification**: Passed as a simple array of color types

## New Interface

### Function Signature
```python
def create_filters_by_phase_plot(validation_data: Dict, task_name: str, output_dir: str, 
                                mode: str = 'kinematic', data: np.ndarray = None, 
                                step_colors: np.ndarray = None) -> str:
```

### Key Changes
- **`step_colors`**: Now accepts a numpy array with shape `(num_steps,)` instead of computing violations internally
- **Cleaner separation**: Validation logic is separate from plotting logic
- **More flexible**: Users can implement any step classification method

### Step Color Types
Steps are color-coded based on the `step_colors` array:

- **'gray'**: Valid steps (no violations)
- **'red'**: Steps with violations in the current feature being plotted (local violations)  
- **'pink'**: Steps with violations in other features (global violations)

## Usage Examples

### 1. Manual Step Classification
```python
import numpy as np
from filters_by_phase_plots import create_filters_by_phase_plot

# Create test data
data = np.random.randn(5, 150, 6)  # 5 steps, 150 phase points, 6 features

# Manual step classification
step_colors = np.array(['gray', 'red', 'pink', 'gray', 'red'])

# Generate plot
filepath = create_filters_by_phase_plot(
    validation_data=validation_data,
    task_name='level_walking',
    output_dir='output/',
    mode='kinematic',
    data=data,
    step_colors=step_colors
)
```

### 2. Automatic Validation-Based Classification
```python
from filters_by_phase_plots import create_filters_by_phase_plot, classify_step_violations

# Define feature mapping
feature_map = {
    ('hip_flexion_angle', 'ipsi'): 0,
    ('hip_flexion_angle', 'contra'): 1,
    ('knee_flexion_angle', 'ipsi'): 2,
    ('knee_flexion_angle', 'contra'): 3,
    ('ankle_flexion_angle', 'ipsi'): 4,
    ('ankle_flexion_angle', 'contra'): 5
}

# Automatically classify steps based on validation expectations
step_colors = classify_step_violations(
    data, validation_data['level_walking'], feature_map, 'kinematic', 0  # For hip ipsi feature
)

# Generate plot with auto-classified colors
filepath = create_filters_by_phase_plot(
    validation_data=validation_data,
    task_name='level_walking',
    output_dir='output/',
    mode='kinematic',
    data=data,
    step_colors=step_colors
)
```

### 3. Backwards Compatibility (No Step Colors)
```python
# If step_colors is None, all steps default to gray
filepath = create_filters_by_phase_plot(
    validation_data=validation_data,
    task_name='level_walking',
    output_dir='output/',
    mode='kinematic',
    data=data
    # step_colors=None (default)
)
```

## Helper Functions

### `classify_step_violations()`
```python
def classify_step_violations(data: np.ndarray, task_data: Dict, feature_map: Dict, 
                           mode: str, current_feature_idx: int) -> np.ndarray:
```

**Purpose**: Automatically classify steps based on validation expectations for a specific feature.

**Returns**: Array with shape `(num_steps,)` containing color types ('red', 'pink', 'gray').

### `detect_filter_violations()` (Legacy)
```python
def detect_filter_violations(data: np.ndarray, task_data: Dict, feature_map: Dict, 
                           mode: str, current_feature_idx: int) -> Tuple[set, set]:
```

**Purpose**: Legacy function that returns sets of violating step indices. Use `classify_step_violations()` for new code.

## Test Files

### 1. `demo_new_step_colors_interface.py`
**New demonstration script** showing the updated interface:

#### Features:
- ✅ **Basic plotting** without step colors
- ✅ **Manual step classification** with custom colors
- ✅ **Automatic classification** using validation expectations
- ✅ **Clean temporary file handling**

#### Example Output:
```
🎨 Demo: New step_colors interface for filters_by_phase_plots
============================================================

1. Basic plot without step colors (all gray):
   ✅ Generated: /tmp/tmp123/level_walking_kinematic_filters_by_phase_with_data.png

2. Plot with custom step colors:
   ✅ Generated: /tmp/tmp456/level_walking_kinematic_filters_by_phase_with_data.png
   Step colors used: ['gray' 'red' 'pink' 'gray' 'red']

3. Plot with automatic validation-based step colors:
   ✅ Generated: /tmp/tmp789/level_walking_kinematic_filters_by_phase_with_data.png
   Auto-classified colors: ['pink' 'pink' 'red' 'red' 'red']
```

### 2. Updated Test Files
Both existing test files have been updated to work with the new interface:

- **`test_filters_by_phase_plots.py`**: Full pytest suite (updated imports)
- **`integration_test_filters_plots.py`**: Standalone integration tests (updated imports)

## Benefits of New Architecture

### 1. **Clean Separation of Concerns**
- Validation logic is separate from plotting logic
- Plotting function focuses purely on visualization
- Easier to test and maintain

### 2. **Flexibility**
- Users can implement any step classification method
- Not tied to specific validation expectations format
- Easy to integrate with different validation systems

### 3. **Simplicity** 
- Just pass an array of colors - no complex configuration
- Clear and intuitive interface
- Easy to understand and debug

### 4. **Performance**
- Validation is computed once, plotting uses the results
- No repeated validation computations during plotting
- Easier to optimize validation algorithms separately

### 5. **Backwards Compatibility**
- Existing code continues to work (step_colors=None)
- Helper functions provide automatic classification
- Gradual migration path for existing users

## Running the Updated Tests

### New Demo Script
```bash
python3 source/tests/demo_new_step_colors_interface.py
```

### Existing Test Suites (Updated)
```bash
# Pytest suite
cd source/tests/
pytest test_filters_by_phase_plots.py -v

# Standalone integration tests  
python3 source/tests/integration_test_filters_plots.py
```

## Migration Guide

### For Existing Code
Old code that relied on automatic violation detection still works:

```python
# Old way (still works)
filepath = create_filters_by_phase_plot(
    validation_data, task_name, output_dir, mode, data=data
)
```

### For New Code
Use the cleaner step classification approach:

```python
# New way (recommended)
step_colors = classify_step_violations(data, task_data, feature_map, mode, feature_idx)
filepath = create_filters_by_phase_plot(
    validation_data, task_name, output_dir, mode, data=data, step_colors=step_colors
)
```

### For Custom Validation Logic
Implement your own classification:

```python
# Custom classification
step_colors = np.array(['gray'] * num_steps)  # Start with all valid
# Apply your custom logic here...
step_colors[custom_violation_indices] = 'red'

filepath = create_filters_by_phase_plot(
    validation_data, task_name, output_dir, mode, data=data, step_colors=step_colors
)
```

This updated architecture provides a much cleaner and more flexible approach to step classification while maintaining backwards compatibility and providing helpful utilities for common use cases.