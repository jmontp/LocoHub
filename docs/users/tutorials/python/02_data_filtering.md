# Tutorial 2: Data Filtering

## Overview

After loading data, filtering is the most critical skill. Learn to extract specific subsets of data for focused analysis, reducing computation time and improving clarity.

## Learning Objectives

- Filter data by task, subject, and variables
- Combine multiple filter conditions
- Create reusable filtered datasets
- Understand filtering performance implications

## Basic Filtering Operations

### Filter by Task

=== "Using Library"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    
    # Load the dataset
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Filter for level walking only
    level_walking = data.filter_task('level_walking')
    print(f"Original data: {len(data)} rows")
    print(f"Level walking only: {len(level_walking)} rows")
    
    # Filter for multiple tasks
    walking_tasks = ['level_walking', 'incline_walking', 'decline_walking']
    all_walking = data.filter_tasks(walking_tasks)
    print(f"All walking tasks: {len(all_walking)} rows")
    ```

=== "Using Raw Data"
    ```python
    import pandas as pd
    
    # Load the dataset
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    # Filter for level walking only
    level_walking = data[data['task'] == 'level_walking']
    print(f"Original data: {len(data)} rows")
    print(f"Level walking only: {len(level_walking)} rows")
    
    # Filter for multiple tasks
    walking_tasks = ['level_walking', 'incline_walking', 'decline_walking']
    all_walking = data[data['task'].isin(walking_tasks)]
    print(f"All walking tasks: {len(all_walking)} rows")
    ```

### Filter by Subject

=== "Using Library"
    ```python
    # Single subject
    subject_01 = data.filter_subject('SUB01')
    print(f"SUB01 data: {len(subject_01)} rows")
    
    # Multiple subjects
    subjects_of_interest = ['SUB01', 'SUB02', 'SUB03']
    selected_subjects = data.filter_subjects(subjects_of_interest)
    print(f"Selected subjects: {len(selected_subjects)} rows")
    
    # Exclude specific subjects
    excluded = ['SUB10', 'SUB11']  # e.g., outliers or incomplete data
    all_subjects = data.get_subjects()
    keep_subjects = [s for s in all_subjects if s not in excluded]
    filtered_data = data.filter_subjects(keep_subjects)
    print(f"After exclusion: {len(filtered_data)} rows")
    ```

=== "Using Raw Data"
    ```python
    # Single subject
    subject_01 = data[data['subject'] == 'SUB01']
    print(f"SUB01 data: {len(subject_01)} rows")
    
    # Multiple subjects
    subjects_of_interest = ['SUB01', 'SUB02', 'SUB03']
    selected_subjects = data[data['subject'].isin(subjects_of_interest)]
    print(f"Selected subjects: {len(selected_subjects)} rows")
    
    # Exclude specific subjects
    excluded = ['SUB10', 'SUB11']  # e.g., outliers or incomplete data
    filtered_data = data[~data['subject'].isin(excluded)]
    print(f"After exclusion: {len(filtered_data)} rows")
    ```

## Combining Filter Conditions

### Multiple Criteria

=== "Using Library"
    ```python
    # Level walking for specific subjects
    level_walking_subset = data.filter(
        task='level_walking',
        subjects=['SUB01', 'SUB02', 'SUB03']
    )
    
    # All walking tasks except decline for healthy subjects
    healthy_subjects = ['SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05']
    walking_healthy = data.filter(
        subjects=healthy_subjects,
        exclude_tasks=['decline_walking'],
        task_contains='walking'
    )
    ```

=== "Using Raw Data"
    ```python
    # Level walking for specific subjects
    level_walking_subset = data[
        (data['task'] == 'level_walking') & 
        (data['subject'].isin(['SUB01', 'SUB02', 'SUB03']))
    ]
    
    # All walking tasks except decline for healthy subjects
    healthy_subjects = ['SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05']
    walking_healthy = data[
        (data['task'] != 'decline_walking') &
        (data['subject'].isin(healthy_subjects)) &
        (data['task'].str.contains('walking'))
    ]
    ```

### Using Query Method

=== "Using Library"
    ```python
    # Library approach uses filter method with kwargs
    filtered = data.filter(
        task='level_walking',
        subjects=['SUB01', 'SUB02', 'SUB03']
    )
    
    # With minimum cycles
    min_cycles = 5
    selected_task = 'level_walking'
    filtered = data.filter(task=selected_task, min_cycle=min_cycles)
    ```

=== "Using Raw Data"
    ```python
    # More readable syntax for complex filters
    filtered = data.query(
        "task == 'level_walking' and subject in ['SUB01', 'SUB02', 'SUB03']"
    )
    
    # With variables
    min_cycles = 5
    selected_task = 'level_walking'
    filtered = data.query(
        f"task == '{selected_task}' and cycle_id >= {min_cycles}"
    )
    ```

## Filtering by Cycle Characteristics

### Select Specific Cycles

=== "Using Library"
    ```python
    # First 5 cycles per subject-task combination
    first_5_cycles = data.get_first_n_cycles(n=5)
    
    # Or specific cycle numbers
    cycles_1_to_3 = data.filter_cycles([1, 2, 3])
    ```

=== "Using Raw Data"
    ```python
    # First 5 cycles per subject-task combination
    def get_first_n_cycles(df, n=5):
        """Get first n cycles for each subject-task combination."""
        return df.groupby(['subject', 'task']).apply(
            lambda x: x[x['cycle_id'].isin(x['cycle_id'].unique()[:n])]
        ).reset_index(drop=True)
    
    first_5_cycles = get_first_n_cycles(data, n=5)
    ```

### Filter by Cycle Quality

=== "Using Library"
    ```python
    # Remove cycles with missing data
    clean_data = data.remove_incomplete_cycles(
        check_columns=['knee_flexion_angle_ipsi_rad']
    )
    
    # Get quality metrics
    quality_stats = data.get_cycle_quality_stats()
    print(f"Cycles with complete knee data: {quality_stats['complete_cycles']}")
    ```

=== "Using Raw Data"
    ```python
    # Remove cycles with missing data
    complete_cycles = []
    for (subject, task, cycle), group in data.groupby(['subject', 'task', 'cycle_id']):
        if not group['knee_flexion_angle_ipsi_rad'].isna().any():
            complete_cycles.append(group)
    
    clean_data = pd.concat(complete_cycles)
    print(f"Cycles with complete knee data: {len(clean_data['cycle_id'].unique())}")
    ```

## Filtering Variables

### Select Variable Groups

=== "Using Library"
    ```python
    # Keep only essential columns for analysis
    analysis_data = data.select_variable_group('kinematics', side='ipsi')
    
    # Or select multiple groups
    analysis_data = data.select_variables(
        groups=['kinematics', 'kinetics'],
        side='ipsi'
    )
    
    print(f"Reduced from {len(data.columns)} to {len(analysis_data.columns)} columns")
    ```

=== "Using Raw Data"
    ```python
    # Keep only essential columns for analysis
    essential_cols = ['subject', 'task', 'cycle_id', 'phase_percent']
    
    # Add specific biomechanical variables
    kinematic_vars = [col for col in data.columns if 'angle' in col and 'ipsi' in col]
    analysis_data = data[essential_cols + kinematic_vars]
    
    print(f"Reduced from {len(data.columns)} to {len(analysis_data.columns)} columns")
    ```

### Create Variable Subsets

=== "Using Library"
    ```python
    # Separate ipsilateral and contralateral
    ipsi_data = data.get_side_data('ipsi')
    contra_data = data.get_side_data('contra')
    
    # Lower body only
    lower_body_data = data.get_body_region('lower')
    # Or specific joints
    lower_body_data = data.select_joints(['hip', 'knee', 'ankle'])
    ```

=== "Using Raw Data"
    ```python
    # Separate ipsilateral and contralateral
    ipsi_data = data[['subject', 'task', 'cycle_id', 'phase_percent'] + 
                      [col for col in data.columns if 'ipsi' in col]]
    
    contra_data = data[['subject', 'task', 'cycle_id', 'phase_percent'] + 
                        [col for col in data.columns if 'contra' in col]]
    
    # Lower body only
    lower_body_keywords = ['hip', 'knee', 'ankle', 'grf']
    lower_body_cols = [col for col in data.columns 
                       if any(keyword in col for keyword in lower_body_keywords)]
    lower_body_data = data[['subject', 'task', 'cycle_id', 'phase_percent'] + lower_body_cols]
    ```

## Efficient Filtering Patterns

### Create Reusable Filters

```python
class DataFilter:
    """Reusable filtering operations for locomotion data."""
    
    @staticmethod
    def get_task(df, task_name):
        """Filter by single task."""
        return df[df['task'] == task_name]
    
    @staticmethod
    def get_subject_task(df, subject, task):
        """Filter by subject and task."""
        return df[(df['subject'] == subject) & (df['task'] == task)]
    
    @staticmethod
    def get_walking_tasks(df):
        """Get all walking-related tasks."""
        walking_tasks = df['task'].unique()
        walking_tasks = [t for t in walking_tasks if 'walking' in t]
        return df[df['task'].isin(walking_tasks)]
    
    @staticmethod
    def remove_incomplete_cycles(df, check_columns):
        """Remove cycles with missing data in specified columns."""
        complete_mask = ~df[check_columns].isna().any(axis=1)
        return df[complete_mask]

# Usage
filter = DataFilter()
level_walking = filter.get_task(data, 'level_walking')
sub01_level = filter.get_subject_task(data, 'SUB01', 'level_walking')
walking_only = filter.get_walking_tasks(data)
```

### Chain Filters Efficiently

=== "Using Library"
    ```python
    # Chain filter methods
    filtered = (data
        .filter_task('level_walking')
        .filter_subject('SUB01')
        .filter_cycles(range(10))
    )
    
    # Or use single filter call
    filtered = data.filter(
        task='level_walking',
        subject='SUB01',
        max_cycle=9
    )
    ```

=== "Using Raw Data"
    ```python
    # Inefficient: Multiple copies
    filtered1 = data[data['task'] == 'level_walking']
    filtered2 = filtered1[filtered1['subject'] == 'SUB01']
    filtered3 = filtered2[filtered2['cycle_id'] < 10]
    
    # Efficient: Single operation
    filtered = data[
        (data['task'] == 'level_walking') &
        (data['subject'] == 'SUB01') &
        (data['cycle_id'] < 10)
    ]
    
    # Or use pipe for clarity
    filtered = (data
        .pipe(lambda df: df[df['task'] == 'level_walking'])
        .pipe(lambda df: df[df['subject'] == 'SUB01'])
        .pipe(lambda df: df[df['cycle_id'] < 10])
    )
    ```

## Saving Filtered Datasets

=== "Using Library"
    ```python
    # Save filtered subset for reuse
    level_walking_clean = data.filter_task('level_walking').remove_incomplete_cycles()
    
    # Save using library methods
    level_walking_clean.save('processed/level_walking_clean.parquet')
    
    # Or export to different formats
    level_walking_clean.export_csv('processed/level_walking_clean.csv')
    
    # Load filtered data later
    saved_data = LocomotionData('processed/level_walking_clean.parquet')
    ```

=== "Using Raw Data"
    ```python
    # Save filtered subset for reuse
    level_walking_clean = data[
        (data['task'] == 'level_walking') &
        (~data['knee_flexion_angle_ipsi_rad'].isna())
    ]
    
    # Save as parquet (maintains data types)
    level_walking_clean.to_parquet('processed/level_walking_clean.parquet')
    
    # Save as CSV (human-readable)
    level_walking_clean.to_csv('processed/level_walking_clean.csv', index=False)
    
    # Load filtered data later
    saved_data = pd.read_parquet('processed/level_walking_clean.parquet')
    ```

## Practice Exercises

### Exercise 1: Complex Filter
Create a filter that selects:
- Only incline and decline walking
- First 3 subjects
- Cycles 5-10
- Only knee and hip variables

### Exercise 2: Filter Function
Write a function that filters data based on a configuration dictionary:
```python
config = {
    'tasks': ['level_walking', 'incline_walking'],
    'subjects': ['SUB01', 'SUB02'],
    'min_cycle': 5,
    'max_cycle': 15,
    'variables': ['knee', 'hip']  # keywords
}

def filter_by_config(data, config):
    # Your implementation
    pass
```

### Exercise 3: Quality Control
Create a function that returns only "good" cycles:
- Complete data (no NaN values)
- Within 2 standard deviations of mean cycle duration
- Has all 150 phase points

## Key Takeaways

1. **Filter early and often** - Work with focused subsets
2. **Combine conditions efficiently** - Use & (and), | (or), ~ (not)
3. **Save filtered datasets** - Avoid repeating complex filters
4. **Think about memory** - Filter before heavy computations
5. **Create reusable filters** - Build a library of common operations

## Next Steps

[Continue to Tutorial 3: Basic Visualization →](03_visualization.md)

Learn to create phase averages, spaghetti plots, and publication-ready figures with your filtered data.