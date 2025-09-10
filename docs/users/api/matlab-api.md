# MATLAB API Reference

## Overview

The MATLAB API provides native MATLAB functions for analyzing standardized biomechanical datasets.

!!! info "Coming Soon"
    The MATLAB API documentation is currently under development. Check back soon for complete function references.

## Core Functions

### Data Loading

#### `load_locomotion_data`
Load a standardized biomechanical dataset.

```matlab
data = load_locomotion_data(filepath)
data = load_locomotion_data(filepath, 'columns', {'col1', 'col2'})
```

**Parameters:**
- `filepath` (string) - Path to parquet file
- `columns` (cell array, optional) - Specific columns to load

**Returns:**
- `data` (table) - MATLAB table containing the dataset

---

### Data Exploration

#### `get_subjects`
Get unique subject identifiers from dataset.

```matlab
subjects = get_subjects(data)
```

#### `get_tasks`
Get unique task names from dataset.

```matlab
tasks = get_tasks(data)
```

---

### Data Filtering

#### `filter_task`
Filter dataset for a specific task.

```matlab
filtered_data = filter_task(data, 'level_walking')
```

#### `filter_subject`
Filter dataset for a specific subject.

```matlab
filtered_data = filter_subject(data, 'SUB01')
```

---

### Analysis Functions

#### `get_cycles`
Extract individual gait cycles.

```matlab
[cycles_3d, features] = get_cycles(data, subject, task)
```

**Parameters:**
- `data` (table) - Dataset
- `subject` (string) - Subject ID
- `task` (string) - Task name

**Returns:**
- `cycles_3d` (array) - 3D array of cycles (cycles × phase × variables)
- `features` (table) - Cycle-level features

#### `get_mean_patterns`
Compute mean patterns across cycles.

```matlab
mean_patterns = get_mean_patterns(data, subject, task)
```

#### `calculate_rom`
Calculate range of motion for all variables.

```matlab
rom = calculate_rom(data, subject, task)
```

---

### Visualization

#### `plot_phase_patterns`
Create phase-averaged plots with standard deviation bands.

```matlab
plot_phase_patterns(data, subject, task, variables)
plot_phase_patterns(data, subject, task, variables, 'ShowSD', true)
```

**Parameters:**
- `data` (table) - Dataset
- `subject` (string) - Subject ID
- `task` (string) - Task name
- `variables` (cell array) - Variable names to plot
- `ShowSD` (logical, optional) - Show standard deviation bands

---

## Usage Examples

### Basic Workflow

```matlab
% Load data
data = load_locomotion_data('converted_datasets/umich_2021_phase.parquet');

% Filter for specific task
level_walking = filter_task(data, 'level_walking');

% Get mean patterns
mean_patterns = get_mean_patterns(level_walking, 'SUB01', 'level_walking');

% Visualize
plot_phase_patterns(level_walking, 'SUB01', 'level_walking', ...
                   {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'});
```

### Memory-Efficient Loading

```matlab
% Load only specific columns
columns = {'subject', 'task', 'cycle_id', 'phase_percent', ...
           'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
data = load_locomotion_data('dataset.parquet', 'columns', columns);
```

## Data Structures

### Dataset Table
The main data structure is a MATLAB table with columns:
- `subject` - Subject identifier
- `task` - Task name
- `cycle_id` - Gait cycle number
- `phase_percent` - Gait cycle phase (0-100)
- Biomechanical variables (angles in radians, moments in Nm, forces in N)

### Variable Naming Convention
- Format: `joint_motion_side_unit`
- Example: `knee_flexion_angle_ipsi_rad`
  - Joint: knee
  - Motion: flexion
  - Side: ipsi (ipsilateral) or contra (contralateral)
  - Unit: rad (radians)

## See Also

- [Python API Reference](locomotion-data-api.md)
- [Data Format Specification](../../reference/standard_spec/standard_spec.md)
