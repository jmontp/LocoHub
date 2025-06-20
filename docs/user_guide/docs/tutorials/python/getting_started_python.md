# Getting Started with Python for Locomotion Data Analysis

[Skip to main content](#main-content)

**Learning Path**: [5-Minute Quick Start](#5-minute-quick-start) → [30-Minute Complete Guide](#30-minute-complete-guide) → [Advanced Library Tutorial](library_tutorial_python.md)

This tutorial provides a progressive guide for working with standardized locomotion data using Python, designed for different time commitments and skill levels.

<a name="main-content"></a>

---

## 5-Minute Quick Start
**⏱️ Time Required**: 5 minutes  
**Prerequisites**: Basic Python knowledge  
**Goal**: Load data, view structure, create your first plot

This ultra-quick introduction gets you analyzing locomotion data immediately.

### Setup
```bash
pip install pandas matplotlib
```

### Load and Explore Data
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load sample data (use your own file path)
df = pd.read_csv('locomotion_data.csv')
print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")
print("\nFirst 3 rows:")
print(df.head(3))
```

### Quick Visualization
```python
# Plot knee angle over time
df_subset = df[df['task_id'] == df['task_id'].iloc[0]]  # First task only
plt.figure(figsize=(10, 4))
plt.plot(df_subset['time_s'], df_subset['knee_flexion_angle_rad'])
plt.xlabel('Time (s)')
plt.ylabel('Knee Angle (rad)')
plt.title('Knee Flexion Angle - Quick View')
plt.grid(True)
plt.show()
print("✅ Your first locomotion data plot is ready!")
```

**Next Steps**: Continue to the [30-Minute Complete Guide](#30-minute-complete-guide) for joining data, filtering by tasks, and phase-based analysis.

---

## 30-Minute Complete Guide
**⏱️ Time Required**: 30 minutes  
**Prerequisites**: Completed [5-Minute Quick Start](#5-minute-quick-start)  
**Goal**: Master common workflows including data joining, task filtering, and phase-based analysis

This section covers the essential workflows you'll use regularly in locomotion data analysis.

### Extended Setup

Ensure you have Pandas and Matplotlib installed. If not, you can install them using pip:

```bash
pip install pandas matplotlib numpy
```

**Important**: Make sure you are running your Python script from the **project root directory** (the directory containing `README.md`, `lib/`, `docs/`, etc.).

In your Python script or Jupyter notebook, you'll typically start by importing the necessary libraries:

```python
import pandas as pd
import numpy as np # Often useful for numerical operations
import matplotlib.pyplot as plt # For plotting
import os # For operating system dependent functionality like getting current directory
import sys
from pathlib import Path

# Verify you're in the correct directory
current_dir = Path.cwd()
print(f"Current working directory: {current_dir}")

# Add library paths for locomotion analysis (if needed)
if (current_dir / "lib" / "core").exists():
    sys.path.append(str(current_dir / "lib" / "core"))
    print("✅ Added lib/core to Python path")
else:
    print("⚠️  Warning: lib/core not found. Make sure you're in the project root directory.")
```

**Running the Examples/Test Script:**

The code examples in this tutorial are designed to match the `test_python_tutorial.py` script located in the `docs/tutorials/test_files/` directory. To run these examples:
1.  Ensure you have `locomotion_data.csv` and `task_info.csv` in the same directory as your script (or the test script). You can copy them from the `docs/tutorials/test_files/` directory if needed.
2.  Navigate to that directory in your terminal.
3.  Run the script using: `python your_script_name.py` (or `python test_python_tutorial.py` for the provided test script).

The test script wraps all operations in a `try...except` block to catch errors. For clarity, this tutorial presents code in separate blocks.

### 1. Loading Your Data

Let's assume your standardized locomotion data is stored in CSV files. Create these files in the same directory where you are running your Python script.

**File 1: `locomotion_data.csv`**

Create a file named `locomotion_data.csv` with the following content:

```csv
time_s,step_id,subject_id,task_id,knee_flexion_angle_rad,hip_flexion_angle_rad,ankle_flexion_angle_rad,cop_x_m,cop_y_m,vertical_grf_N
0.01,1,P001,P001_T01,0.178,0.089,0.052,0.10,0.05,650.2
0.02,1,P001,P001_T01,0.218,0.108,0.063,0.11,0.06,680.5
0.03,1,P001,P001_T01,0.264,0.122,0.075,0.12,0.07,700.3
0.04,2,P001,P001_T02,0.354,0.183,0.087,0.15,0.10,720.8
0.05,2,P001,P001_T02,0.384,0.197,0.093,0.16,0.11,750.2
0.06,2,P001,P001_T02,0.447,0.224,0.105,0.17,0.12,760.5
0.07,3,P001,P001_T01,0.155,0.075,0.045,0.09,0.04,620.1
0.08,3,P001,P001_T01,0.182,0.087,0.055,0.10,0.05,640.3
0.09,3,P001,P001_T01,0.230,0.107,0.068,0.11,0.06,660.7
0.10,3,P001,P001_T01,0.279,0.131,0.079,0.12,0.07,680.9
```

**File 2: `task_info.csv`**

Create a file named `task_info.csv` with the following content:

```csv
step_id,task_id,task_name,subject_id,ground_inclination_deg,walking_speed_m_s
1,P001_T01,level_walking,P001,0,1.2
2,P001_T02,incline_walking,P001,5,1.5
3,P001_T01,level_walking,P001,0,1.2
```

Now, let's load this data using Pandas:

```python
print("Working directory:", os.getcwd())
# Load the data from the CSV files
try:
    df_locomotion = pd.read_csv('locomotion_data.csv')
    df_tasks = pd.read_csv('task_info.csv')

    print("\nLocomotion Data:")
    print(df_locomotion.head(3)) # Show first 3 rows
    print("\nTask Information:")
    print(df_tasks) # Show all task info (it's small)
except FileNotFoundError:
    print("Error: Ensure 'locomotion_data.csv' and 'task_info.csv' exist in the current directory.")
    # Create empty dataframes to allow the rest of the script to run without error, though plots/results will be empty.
    df_locomotion = pd.DataFrame({'time_s': [], 'step_id': [], 'knee_flexion_angle_rad': [], 'hip_flexion_angle_rad': [], 'ankle_flexion_angle_rad': [], 'cop_x_m': [], 'cop_y_m': [], 'vertical_grf_N': []})
    df_tasks = pd.DataFrame({'step_id': [], 'task_id': [], 'task_name': [], 'subject_id': [], 'ground_inclination_deg': [], 'walking_speed_m_s': []})

```

This setup provides `df_locomotion` with time-series data and `df_tasks` with information about the tasks performed.

### 2. Combining Locomotion Data with Task Data (Outer Join)

To analyze locomotion features in the context of specific tasks, you'll often need to combine these datasets. An **outer join** is useful if you want to keep all records from both dataframes, filling in missing values with `NaN` where a match isn't found. In Pandas, `pd.merge()` is used for this.

Let's assume we want to join on the common keys `step_id`, `task_id`, and `subject_id`.

```python
# Perform an outer join on common keys
# This ensures that all locomotion data and all task data are preserved.
# If a key combination exists in one DataFrame but not the other,
# the columns from the other DataFrame will be filled with NaN for that row.
df_combined = pd.merge(df_locomotion, df_tasks, on=['step_id', 'task_id', 'subject_id'], how='outer')

print("\nCombined Data (first 3 rows):")
print(df_combined.head(3))
```

**Why an outer join?**
*   You might have locomotion data that wasn't assigned a task (it will still be included).
*   You might have task definitions for which no locomotion data was recorded (they will also be included, though less common in this specific example structure).
In many cases, a `left` join (keeping all records from `df_locomotion` and matching task info) or an `inner` join (keeping only records where the key combination exists in both) might be more appropriate depending on your specific data and analysis goals.

### 3. Filtering for a Particular Task

Once your data is combined, you can easily filter it to focus on a specific task. For example, let's filter the data for the 'incline_walking' task.

```python
# Filter for a specific task, e.g., 'incline_walking'
df_incline_walking = df_combined[df_combined['task_name'] == 'incline_walking']
print("\nData for 'incline_walking' task:")
print(df_incline_walking)

# You can also filter by other criteria, e.g., subject_id or step_id
# df_subject_p001 = df_combined[df_combined['subject_id'] == 'P001']
```

This allows you to isolate the data segments relevant to your particular research question or analysis.

### 4. Phase-Based Averaging for Gait Analysis

A common operation in biomechanics is to normalize gait cycles to 0-100% phase and then generate average curves across multiple steps or subjects. This allows for comparing gait patterns regardless of differences in cycle duration.

**Example: Averaging knee angle across steps by phase percentage**

For this example, we'll add a `phase_%` column to our locomotion data (representing 0-100% of each step) and then bin this phase data to calculate averages.

```python
# First, let's create sample phase data
# In a real dataset, this might come from a separate phase-normalized data file or be calculated.
df_with_phase = df_locomotion.copy()
for step in df_locomotion['step_id'].unique():
    step_mask = df_locomotion['step_id'] == step
    num_points = step_mask.sum()
    df_with_phase.loc[step_mask, 'phase_%'] = np.linspace(0, 100, num_points)

# Now let's use phase bins to group data points at similar phases across different steps
phase_bins = np.linspace(0, 100, 101)  # 101 bins for 0-100% (e.g., 0, 1, ..., 100)
labels = phase_bins[:-1]  # Use 0, 1, ..., 99 as the labels for bins [0-1), [1-2), ..., [99-100]

# Bin the data by phase percentage
df_with_phase['phase_bin'] = pd.cut(df_with_phase['phase_%'], bins=phase_bins, labels=labels, include_lowest=True)

# Now we can get the average knee angle for each phase bin across all steps
phase_averages = df_with_phase.groupby('phase_bin', observed=False)['knee_flexion_angle_rad'].mean()

print("\nAverage knee flexion angle by phase (first 5 phases):")
print(phase_averages.head(5))

# We can also compare different tasks by phase
# First, merge df_with_phase (which has phase_bin) with df_tasks to get task_name
# Using an inner join to ensure we only consider data points that have both phase and task information
df_with_phase_and_task = pd.merge(df_with_phase, df_tasks, on=['step_id', 'task_id', 'subject_id'], how='inner')

phase_by_task = {}
for task in df_with_phase_and_task['task_name'].unique():
    if pd.notnull(task):  # Skip NaN values if any (though inner join should prevent them here)
        task_data = df_with_phase_and_task[df_with_phase_and_task['task_name'] == task]
        phase_by_task[task] = task_data.groupby('phase_bin', observed=False)['knee_flexion_angle_rad'].mean()

print("\nPhase-based knee flexion angle by task (first 3 phases):")
for task, data in phase_by_task.items():
    print(f"Task: {task}")
    print(data.head(3))
```

Note: The standardized data format may also provide data already indexed by phase (e.g., in Parquet files), typically with 150 equally spaced points per gait cycle. Working with such pre-processed phase-indexed data can simplify these types of analyses.

### 5. Basic Plotting

Visualizing your data is a crucial step. Matplotlib is a widely used library for plotting in Python.
The test script saves plots to files rather than displaying them interactively.

**Example 5.1: Plotting a time-series feature for a specific task**

Let's plot the `knee_flexion_angle_rad` over time for the 'incline_walking' task and save it to a file.

```python
# Using df_incline_walking from section 3
if not df_incline_walking.empty:
    plt.figure(figsize=(10, 4))
    plt.plot(df_incline_walking['time_s'], df_incline_walking['knee_flexion_angle_rad'], marker='o', linestyle='-')
    plt.xlabel('Time (s)')
    plt.ylabel('Knee Flexion Angle (rad)')
    plt.title('Knee Flexion Angle during Incline Walking')
    plt.grid(True)
    plt.savefig('knee_angle_incline.png') # Save the plot
    print("\nPlot saved as 'knee_angle_incline.png'")
else:
    print("\nNo data available for 'incline_walking' task to plot.")

# Example 5.2: Comparing average feature values across tasks (Bar Plot)
# Using phase_by_task from section 4
if phase_by_task: # Check if the dictionary is not empty
    plt.figure(figsize=(8, 5))
    # Calculate the mean of the phase-averaged data for each task for the bar plot
    task_means = {task: data.mean() for task, data in phase_by_task.items() if not data.empty}
    
    if task_means: # Ensure there are means to plot
        plt.bar(list(task_means.keys()), list(task_means.values()))
        plt.xlabel('Task Name')
        plt.ylabel('Average Knee Flexion Angle (rad)')
        plt.title('Average Knee Flexion Angle by Task (mean of phase averages)')
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout() # Adjust layout to prevent labels from overlapping
        plt.savefig('knee_angle_by_task.png') # Save the plot
        print("Plot saved as 'knee_angle_by_task.png'")
    else:
        print("\nNo averaged data means available to plot by task.")
else:
    print("\nNo phase_by_task data available to plot.")

```

### 6. Calculating Derived Metrics

Often, you'll need to compute new metrics from your existing data.

**Example 6.1: Calculate Knee Angle Range of Motion (RoM) per step**

Let's calculate the knee angle RoM for each step in the 'level_walking' task. RoM can be defined as (max value - min value) of the angle within each step. We use `df_with_phase_and_task` from Section 4 as it contains the necessary columns.

```python
# Using df_with_phase_and_task from section 4, which includes 'task_name'
# Filter for level_walking data
df_level_walking = df_with_phase_and_task[df_with_phase_and_task['task_name'] == 'level_walking']

if not df_level_walking.empty:
    # Group by step_id and then calculate RoM for knee_flexion_angle_rad
    knee_rom_per_step = df_level_walking.groupby('step_id')['knee_flexion_angle_rad'].apply(lambda x: x.max() - x.min())
    knee_rom_per_step = knee_rom_per_step.rename('knee_flexion_angle_rom_rad')

    print("\nKnee Flexion Angle ROM per step during 'level_walking':")
    print(knee_rom_per_step)

    # You can merge this back into your task-specific dataframe or the combined dataframe if needed
    # df_level_walking = pd.merge(df_level_walking, knee_rom_per_step, on='step_id', how='left')
else:
    print("\nNo data available for 'level_walking' task to calculate RoM.")

# Final message similar to the test script
print("\nPython tutorial operations completed (mimicking test script structure).")
```

**🎉 Congratulations!** You've completed the 30-minute guide and can now:
- Join locomotion data with task information
- Filter data by specific tasks or conditions  
- Perform phase-based analysis for gait cycle comparisons
- Create visualizations and calculate derived metrics

**Ready for Advanced Analysis?** Continue to the [Advanced Library Tutorial](library_tutorial_python.md) for 3D data operations, validation, statistical analysis, and batch processing.

---

## Summary

This tutorial covered progressive operations for handling standardized locomotion data in Python:
*   Loading data with Pandas.
*   Joining different data sources using `pd.merge()`.
*   Filtering data based on task information or other criteria.
*   Analyzing data using phase-based normalization and averaging.
*   Creating basic plots and saving them using Matplotlib.
*   Calculating derived metrics like Range of Motion.

These examples provide a starting point. Depending on the complexity of your data and analyses, you might explore more advanced Pandas functionalities, time-series analysis libraries, or specific biomechanics-focused Python packages.

Refer to the [Pandas documentation](https://pandas.pydata.org/pandas-docs/stable/) for more comprehensive information on its capabilities. Consult your dataset's specific metadata and the [Units & Conventions](../../standard_spec/units_and_conventions.md) documentation for details on column names, units, and conventions.