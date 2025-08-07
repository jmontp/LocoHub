# Tutorial 1: Loading Data Efficiently

## Overview

Learn how to load biomechanical datasets efficiently, understanding memory implications and column selection strategies.

## Learning Objectives

- Load phase-indexed and time-indexed datasets
- Select specific columns to reduce memory usage
- Understand the data structure and available variables
- List subjects, tasks, and measurement variables

## Full Dataset Loading

### Basic Loading

=== "Using Library"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    
    # Load a complete phase-indexed dataset
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Check dataset size
    print(f"Dataset shape: {data.shape}")
    print(f"Memory usage: {data.memory_usage() / 1024**2:.2f} MB")
    ```

=== "Using Raw Data"
    ```python
    import pandas as pd
    
    # Load a complete phase-indexed dataset
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    # Check dataset size
    print(f"Dataset shape: {data.shape}")
    print(f"Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    ```

### Understanding the Structure

=== "Using Library"
    ```python
    # View column names
    print("Available columns:")
    print(data.get_variables())
    
    # Check data types
    print("\nData types:")
    print(data.dtypes)
    
    # Preview first few rows
    print("\nFirst 5 rows:")
    print(data.head())
    ```

=== "Using Raw Data"
    ```python
    # View column names
    print("Available columns:")
    print(data.columns.tolist())
    
    # Check data types
    print("\nData types:")
    print(data.dtypes)
    
    # Preview first few rows
    print("\nFirst 5 rows:")
    print(data.head())
    ```

## Memory-Efficient Loading

### Column Selection

=== "Using Library"
    ```python
    # Load only specific biomechanical variables
    selected_columns = [
        'subject', 
        'task', 
        'cycle_id',
        'phase_percent',
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad'
    ]
    
    # Load with column selection
    data_efficient = LocomotionData(
        'converted_datasets/umich_2021_phase.parquet',
        columns=selected_columns
    )
    
    # Compare memory usage
    print(f"Full dataset: {data.memory_usage() / 1024**2:.2f} MB")
    print(f"Selected columns: {data_efficient.memory_usage() / 1024**2:.2f} MB")
    ```

=== "Using Raw Data"
    ```python
    # Load only specific biomechanical variables
    selected_columns = [
        'subject', 
        'task', 
        'cycle_id',
        'phase_percent',
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad'
    ]
    
    # Load with column selection
    data_efficient = pd.read_parquet(
        'converted_datasets/umich_2021_phase.parquet',
        columns=selected_columns
    )
    
    # Compare memory usage
    print(f"Full dataset: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print(f"Selected columns: {data_efficient.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    ```

### Loading Variable Groups

```python
# Load only kinematic variables
kinematic_columns = ['subject', 'task', 'cycle_id', 'phase_percent']
kinematic_columns.extend([col for col in data.columns if 'angle' in col])

data_kinematics = LocomotionData(
    'converted_datasets/umich_2021_phase.parquet',
    columns=kinematic_columns
)

# Load only kinetic variables
kinetic_columns = ['subject', 'task', 'cycle_id', 'phase_percent']
kinetic_columns.extend([col for col in data.columns if 'moment' in col or 'force' in col])

data_kinetics = LocomotionData(
    'converted_datasets/umich_2021_phase.parquet',
    columns=kinetic_columns
)
```

## Exploring Available Data

### List Subjects and Tasks

=== "Using Library"
    ```python
    # Get unique subjects
    subjects = data.get_subjects()
    print(f"Number of subjects: {len(subjects)}")
    print(f"Subject IDs: {subjects[:5]}...")  # Show first 5
    
    # Get unique tasks
    tasks = data.get_tasks()
    print(f"Available tasks: {tasks}")
    
    # Count cycles per task
    for task in tasks:
        n_cycles = data.count_cycles(task=task)
        print(f"{task}: {n_cycles} cycles")
    ```

=== "Using Raw Data"
    ```python
    # Get unique subjects
    subjects = data['subject'].unique()
    print(f"Number of subjects: {len(subjects)}")
    print(f"Subject IDs: {subjects[:5]}...")  # Show first 5
    
    # Get unique tasks
    tasks = data['task'].unique()
    print(f"Available tasks: {tasks}")
    
    # Count cycles per task
    for task in tasks:
        task_data = data[data['task'] == task]
        n_cycles = len(task_data['cycle_id'].unique())
        print(f"{task}: {n_cycles} cycles")
    ```

### Understanding Variable Naming

```python
# Identify variable types
angles = [col for col in data.columns if 'angle' in col]
moments = [col for col in data.columns if 'moment' in col]
forces = [col for col in data.columns if 'force' in col]

print(f"Joint angles: {len(angles)} variables")
print(f"Joint moments: {len(moments)} variables")
print(f"Ground reaction forces: {len(forces)} variables")

# Understanding naming convention
print("\nNaming convention examples:")
print("- knee_flexion_angle_ipsi_rad: Ipsilateral knee flexion angle in radians")
print("- hip_moment_contra_Nm: Contralateral hip moment in Newton-meters")
print("- grf_vertical_N: Vertical ground reaction force in Newtons")
```

## Time-Indexed vs Phase-Indexed Data

### Loading Different Data Types

```python
# Phase-indexed: 150 points per gait cycle
data_phase = LocomotionData('converted_datasets/umich_2021_phase.parquet')
print(f"Phase data points per cycle: {len(data_phase[data_phase['cycle_id'] == data_phase['cycle_id'].iloc[0]])}")

# Time-indexed: original sampling frequency
data_time = LocomotionData('converted_datasets/umich_2021_time.parquet')
print(f"Time data shape: {data_time.shape}")
print(f"Sampling info available in time data: {' time' in data_time.columns}")
```

## Practice Exercises

### Exercise 1: Memory Optimization
Load the Georgia Tech 2023 dataset with only the variables needed to analyze knee and ankle kinematics during stair climbing.

### Exercise 2: Data Exploration
Write a function that prints a summary of a dataset including:
- Number of subjects
- Available tasks
- Number of cycles per task
- List of bilateral variables (both ipsi and contra versions)

### Exercise 3: Smart Loading
Create a function that automatically selects columns based on keywords:
```python
def load_by_keywords(filepath, keywords=['knee', 'hip'], include_metadata=True):
    """Load dataset with variables matching keywords."""
    # Your implementation here
    pass
```

## Key Takeaways

1. **Always consider memory** when loading large datasets
2. **Use column selection** to load only what you need
3. **Understand the structure** before analysis:
   - Phase-indexed: 150 points per cycle
   - Time-indexed: original sampling rate
4. **Variable naming convention**:
   - Joint_motion_side_unit
   - ipsi = ipsilateral, contra = contralateral
   - rad = radians, Nm = Newton-meters, N = Newtons

## Next Steps

[Continue to Tutorial 2: Data Filtering →](02_data_filtering.md)

Learn how to filter your loaded data by task, subject, and other criteria for focused analysis.