# Data Playground

**Safe environment to experiment with biomechanical data analysis - explore freely without fear of breaking anything.**

<div class="playground-intro" markdown>
:material-flask: **What is the Data Playground?**

The playground provides a risk-free environment where you can:

- **Experiment freely** with real biomechanical data
- **Modify analysis parameters** and see immediate results  
- **Learn by doing** with guided experiments
- **Download everything** for use in your own research
- **Progress gradually** from simple to advanced analyses

</div>

<div class="grid cards" markdown>

-   :material-download: **Downloadable Notebooks**
    
    ---
    
    Pre-configured Jupyter notebooks with sample data and complete analyses
    
    [:octicons-arrow-right-24: Get Notebooks](notebooks/)

-   :material-speedometer: **Quick Experiments**
    
    ---
    
    5-minute analysis tasks with immediate visual results
    
    [:octicons-arrow-right-24: Try Experiments](quick_experiments/)

-   :material-tune: **Parameter Explorer**
    
    ---
    
    Interactive parameter adjustment with real-time visualization updates
    
    [:octicons-arrow-right-24: Explore Parameters](parameter_explorer/)

-   :material-school: **Learning Challenges**
    
    ---
    
    Progressive complexity challenges to build your analysis skills
    
    [:octicons-arrow-right-24: Take Challenges](learning_challenges/)

</div>

## Featured Playground Activities

### 1. Interactive Gait Analysis

<div class="playground-activity" markdown>

**What you'll do:** Load a dataset, filter for a specific task, and create visualizations

**Time required:** 5 minutes

**Skills gained:** Data loading, filtering, basic plotting

??? example "Try It Now - Gait Analysis"
    
    **Step 1: Load and Explore Data**
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Load sample dataset (included in playground)
    data = pd.read_parquet('sample_data/playground_dataset.parquet')
    
    # Explore the data structure
    print("Dataset shape:", data.shape)
    print("Available columns:", data.columns.tolist())
    print("Unique tasks:", data['task'].unique())
    print("Unique subjects:", data['subject_id'].unique())
    ```
    
    **Step 2: Filter and Visualize**
    ```python
    # Filter for level walking from one subject
    subject_1_walking = data[
        (data['subject_id'] == 'S001') & 
        (data['task'] == 'level_walking')
    ]
    
    # Create your first gait plot
    plt.figure(figsize=(12, 8))
    
    # Plot knee angle across gait cycle
    plt.subplot(2, 1, 1)
    plt.plot(subject_1_walking['phase_percent'], 
             np.rad2deg(subject_1_walking['knee_flexion_angle_ipsi_rad']), 
             'b-', linewidth=2, label='Knee Flexion')
    plt.ylabel('Angle (degrees)')
    plt.title('Joint Angles - Level Walking')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot hip angle
    plt.subplot(2, 1, 2)
    plt.plot(subject_1_walking['phase_percent'], 
             np.rad2deg(subject_1_walking['hip_flexion_angle_ipsi_rad']), 
             'r-', linewidth=2, label='Hip Flexion')
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Angle (degrees)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    ```
    
    **Step 3: Experiment with Parameters**
    ```python
    # Try different subjects or tasks
    SUBJECT_ID = 'S002'  # Change this!
    TASK = 'incline_walking'  # Change this!
    
    # Rerun the analysis with new parameters
    filtered_data = data[
        (data['subject_id'] == SUBJECT_ID) & 
        (data['task'] == TASK)
    ]
    
    # Plot and compare...
    ```
    
    **Download this notebook:** [:material-download: gait_analysis_playground.ipynb](notebooks/gait_analysis_playground.ipynb)

</div>

### 2. Multi-Task Comparison Challenge

<div class="playground-activity" markdown>

**What you'll do:** Compare joint patterns across different locomotion tasks

**Time required:** 10 minutes

**Skills gained:** Data grouping, statistical comparison, advanced plotting

??? example "Try It Now - Task Comparison"
    
    **Step 1: Setup Comparison**
    ```python
    # Define tasks to compare
    tasks_to_compare = ['level_walking', 'incline_walking', 'up_stairs']
    colors = ['blue', 'orange', 'red']
    
    # Create figure with subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    joints = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_ipsi_rad']
    joint_names = ['Hip Flexion', 'Knee Flexion', 'Ankle Dorsiflexion']
    ```
    
    **Step 2: Plot Comparisons**
    ```python
    for i, (joint, joint_name) in enumerate(zip(joints, joint_names)):
        for task, color in zip(tasks_to_compare, colors):
            task_data = data[data['task'] == task]
            
            # Calculate mean and std across subjects
            mean_angle = task_data.groupby('phase_percent')[joint].mean()
            std_angle = task_data.groupby('phase_percent')[joint].std()
            
            # Plot mean line
            axes[i].plot(mean_angle.index, np.rad2deg(mean_angle.values), 
                        color=color, linewidth=2, label=task.replace('_', ' ').title())
            
            # Add confidence bands (optional)
            axes[i].fill_between(mean_angle.index, 
                                np.rad2deg((mean_angle - std_angle).values),
                                np.rad2deg((mean_angle + std_angle).values),
                                color=color, alpha=0.2)
        
        axes[i].set_title(joint_name)
        axes[i].set_xlabel('Gait Cycle (%)')
        axes[i].set_ylabel('Angle (degrees)')
        axes[i].legend()
        axes[i].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    ```
    
    **Step 3: Statistical Analysis**
    ```python
    # Compare peak values across tasks
    import scipy.stats as stats
    
    peak_values = {}
    for task in tasks_to_compare:
        task_data = data[data['task'] == task]
        peak_values[task] = np.rad2deg(task_data['knee_flexion_angle_ipsi_rad'].max())
    
    print("Peak knee flexion by task:")
    for task, peak in peak_values.items():
        print(f"  {task}: {peak:.1f}°")
    
    # Perform statistical test
    # ... add your statistical comparison here ...
    ```
    
    **Download this notebook:** [:material-download: task_comparison_playground.ipynb](notebooks/task_comparison_playground.ipynb)

</div>

### 3. Data Quality Explorer

<div class="playground-activity" markdown>

**What you'll do:** Explore data validation features and quality metrics

**Time required:** 15 minutes

**Skills gained:** Data validation, quality assessment, outlier detection

??? example "Try It Now - Quality Analysis"
    
    **Step 1: Basic Quality Checks**
    ```python
    # Check for missing data
    print("Missing data summary:")
    missing_summary = data.isnull().sum()
    print(missing_summary[missing_summary > 0])
    
    # Check data ranges
    print("\nData range summary:")
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    for col in numeric_cols[:5]:  # Show first 5 numeric columns
        print(f"{col}: {data[col].min():.3f} to {data[col].max():.3f}")
    ```
    
    **Step 2: Outlier Detection**
    ```python
    # Detect outliers using IQR method
    def detect_outliers(series):
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return (series < lower_bound) | (series > upper_bound)
    
    # Check knee angle outliers
    knee_angle_deg = np.rad2deg(data['knee_flexion_angle_ipsi_rad'])
    outliers = detect_outliers(knee_angle_deg)
    
    print(f"Found {outliers.sum()} potential outliers in knee flexion angle")
    print(f"Outlier percentage: {100 * outliers.sum() / len(data):.2f}%")
    
    # Visualize outliers
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.boxplot(knee_angle_deg, vert=True)
    plt.ylabel('Knee Flexion (degrees)')
    plt.title('Knee Flexion Distribution')
    
    plt.subplot(1, 2, 2)
    plt.scatter(range(len(knee_angle_deg)), knee_angle_deg, 
                c=outliers, cmap='coolwarm', alpha=0.6)
    plt.xlabel('Data Point Index')
    plt.ylabel('Knee Flexion (degrees)')
    plt.title('Outlier Detection (Red = Outlier)')
    plt.colorbar(label='Outlier Status')
    
    plt.tight_layout()
    plt.show()
    ```
    
    **Step 3: Biomechanical Validation**
    ```python
    # Check against biomechanical expectations
    validation_ranges = {
        'knee_flexion_angle_ipsi_rad': (-0.2, 2.0),  # -11° to 115°
        'hip_flexion_angle_ipsi_rad': (-0.5, 1.2),   # -29° to 69°
        'ankle_dorsiflexion_angle_ipsi_rad': (-0.8, 0.5)  # -46° to 29°
    }
    
    validation_results = {}
    for variable, (min_val, max_val) in validation_ranges.items():
        if variable in data.columns:
            within_range = ((data[variable] >= min_val) & 
                           (data[variable] <= max_val))
            validation_results[variable] = {
                'pass_rate': within_range.mean(),
                'outliers': (~within_range).sum()
            }
    
    print("Biomechanical validation results:")
    for var, results in validation_results.items():
        print(f"  {var}:")
        print(f"    Pass rate: {results['pass_rate']:.1%}")
        print(f"    Outliers: {results['outliers']} points")
    ```
    
    **Download this notebook:** [:material-download: quality_explorer_playground.ipynb](notebooks/quality_explorer_playground.ipynb)

</div>

## Interactive Parameter Playground

### Real-Time Analysis Adjustment

<div class="parameter-playground" markdown>

**Try adjusting these parameters and see immediate results:**

#### Filtering Parameters
```python
# Adjustable parameters - modify these values!
SUBJECT_IDS = ['S001', 'S002', 'S003']  # Which subjects to include
TASKS = ['level_walking']                # Which tasks to analyze  
PHASE_RANGE = (0, 100)                  # Gait cycle percentage range
JOINT_OF_INTEREST = 'knee_flexion_angle_ipsi_rad'  # Which joint to focus on

# Apply filters
filtered_data = data[
    (data['subject_id'].isin(SUBJECT_IDS)) &
    (data['task'].isin(TASKS)) &
    (data['phase_percent'] >= PHASE_RANGE[0]) &
    (data['phase_percent'] <= PHASE_RANGE[1])
]

# Visualize results
plt.figure(figsize=(12, 6))
for subject in SUBJECT_IDS:
    subject_data = filtered_data[filtered_data['subject_id'] == subject]
    plt.plot(subject_data['phase_percent'], 
             np.rad2deg(subject_data[JOINT_OF_INTEREST]), 
             label=f'Subject {subject}', linewidth=2)

plt.xlabel('Gait Cycle (%)')
plt.ylabel('Joint Angle (degrees)')
plt.title(f'{JOINT_OF_INTEREST.replace("_", " ").title()} - {TASKS[0].replace("_", " ").title()}')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

# Summary statistics
print(f"Analysis summary for {len(SUBJECT_IDS)} subjects:")
print(f"  Mean peak angle: {np.rad2deg(filtered_data[JOINT_OF_INTEREST].max()):.1f}°")
print(f"  Mean minimum angle: {np.rad2deg(filtered_data[JOINT_OF_INTEREST].min()):.1f}°")
print(f"  Range of motion: {np.rad2deg(filtered_data[JOINT_OF_INTEREST].max() - filtered_data[JOINT_OF_INTEREST].min()):.1f}°")
```

#### Visualization Parameters
```python
# Plot customization parameters
PLOT_STYLE = 'seaborn'  # Options: 'seaborn', 'ggplot', 'classic'
COLOR_SCHEME = 'viridis'  # Options: 'viridis', 'plasma', 'coolwarm'
FIGURE_SIZE = (12, 8)     # Width, height in inches
LINE_WIDTH = 2            # Line thickness
SHOW_CONFIDENCE_BANDS = True  # Show standard deviation bands
SHOW_INDIVIDUAL_CYCLES = False  # Show individual gait cycles

# Apply style
plt.style.use(PLOT_STYLE)

# Create customized plot
fig, ax = plt.subplots(figsize=FIGURE_SIZE)

if SHOW_INDIVIDUAL_CYCLES:
    # Plot individual gait cycles with transparency
    for subject in SUBJECT_IDS:
        subject_data = filtered_data[filtered_data['subject_id'] == subject]
        ax.plot(subject_data['phase_percent'], 
                np.rad2deg(subject_data[JOINT_OF_INTEREST]), 
                alpha=0.3, linewidth=1)

# Plot mean line
mean_data = filtered_data.groupby('phase_percent')[JOINT_OF_INTEREST].mean()
ax.plot(mean_data.index, np.rad2deg(mean_data.values), 
        linewidth=LINE_WIDTH, color='red', label='Mean')

if SHOW_CONFIDENCE_BANDS:
    std_data = filtered_data.groupby('phase_percent')[JOINT_OF_INTEREST].std()
    ax.fill_between(mean_data.index,
                    np.rad2deg((mean_data - std_data).values),
                    np.rad2deg((mean_data + std_data).values),
                    alpha=0.3, color='red', label='±1 SD')

ax.set_xlabel('Gait Cycle (%)')
ax.set_ylabel('Joint Angle (degrees)')
ax.set_title(f'{JOINT_OF_INTEREST.replace("_", " ").title()} Analysis')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

</div>

## Learning Challenges

### Progressive Skill Building

<div class="challenges-grid" markdown>

#### Beginner Challenges

=== "Challenge 1: First Plot"
    **Goal:** Load data and create your first gait cycle plot
    
    **Skills:** Data loading, basic plotting
    
    **Time:** 5 minutes
    
    **Success criteria:**
    - [ ] Load sample dataset successfully
    - [ ] Filter for one subject and task
    - [ ] Create knee angle plot across gait cycle
    - [ ] Add axis labels and title
    
    [:material-play: Start Challenge](learning_challenges/beginner/#challenge-1)

=== "Challenge 2: Multi-Joint View"
    **Goal:** Create subplot showing hip, knee, and ankle angles
    
    **Skills:** Subplots, multiple data series
    
    **Time:** 10 minutes
    
    **Success criteria:**
    - [ ] Create 3-panel subplot
    - [ ] Plot different joint angles in each panel
    - [ ] Use different colors for each joint
    - [ ] Add grid and legends
    
    [:material-play: Start Challenge](learning_challenges/beginner/#challenge-2)

=== "Challenge 3: Task Comparison"
    **Goal:** Compare same joint across different tasks
    
    **Skills:** Data filtering, overlaying plots
    
    **Time:** 15 minutes
    
    **Success criteria:**
    - [ ] Filter data for multiple tasks
    - [ ] Overlay plots with different colors
    - [ ] Add legend distinguishing tasks
    - [ ] Calculate and report peak values
    
    [:material-play: Start Challenge](learning_challenges/beginner/#challenge-3)

</div>

<div class="challenges-grid" markdown>

#### Intermediate Challenges

=== "Challenge 4: Statistical Analysis"
    **Goal:** Perform statistical comparison between groups
    
    **Skills:** Statistical testing, error bars, significance
    
    **Time:** 20 minutes
    
    **Success criteria:**
    - [ ] Calculate means and standard deviations
    - [ ] Perform appropriate statistical test
    - [ ] Create bar plot with error bars
    - [ ] Report statistical significance
    
    [:material-play: Start Challenge](learning_challenges/intermediate/#challenge-4)

=== "Challenge 5: Quality Assessment"
    **Goal:** Implement data quality checks and validation
    
    **Skills:** Outlier detection, validation ranges, quality metrics
    
    **Time:** 25 minutes
    
    **Success criteria:**
    - [ ] Detect outliers using statistical methods
    - [ ] Apply biomechanical validation ranges
    - [ ] Create quality report summary
    - [ ] Visualize quality metrics
    
    [:material-play: Start Challenge](learning_challenges/intermediate/#challenge-5)

=== "Challenge 6: Advanced Visualization"
    **Goal:** Create publication-quality multi-panel figure
    
    **Skills:** Advanced plotting, figure layout, styling
    
    **Time:** 30 minutes
    
    **Success criteria:**
    - [ ] Create complex multi-panel layout
    - [ ] Apply consistent styling and colors
    - [ ] Add detailed annotations
    - [ ] Export publication-ready figure
    
    [:material-play: Start Challenge](learning_challenges/intermediate/#challenge-6)

</div>

## Playground Safety Features

### Error-Safe Environment

<div class="safety-features" markdown>

#### What Makes It Safe?

- **Read-Only Data**: Original datasets cannot be modified
- **Isolated Environment**: Experiments don't affect system files
- **Automatic Backups**: Work is saved automatically
- **Reset Capability**: Start fresh at any time
- **Guided Recovery**: Help when things go wrong

#### Built-in Safety Checks

```python
# Automatic data validation
def safe_data_load(filename):
    """Load data with automatic validation and error handling"""
    try:
        data = pd.read_parquet(filename)
        
        # Basic validation checks
        if data.empty:
            raise ValueError("Dataset is empty")
        
        required_columns = ['subject_id', 'task', 'phase_percent']
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        print(f"✅ Successfully loaded {len(data)} rows of data")
        return data
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        print("💡 Try using one of the sample datasets in the playground/")
        return None

# Example usage
data = safe_data_load('sample_data/playground_dataset.parquet')
```

#### Helpful Error Messages

```python
# Smart error handling with suggestions
def smart_plot(data, x_col, y_col):
    """Create plot with helpful error messages"""
    try:
        plt.plot(data[x_col], data[y_col])
        plt.show()
        
    except KeyError as e:
        available_cols = list(data.columns)
        print(f"❌ Column {e} not found")
        print(f"💡 Available columns: {available_cols[:5]}...")
        print(f"💡 Did you mean: {find_similar_column(str(e), available_cols)}")
        
    except Exception as e:
        print(f"❌ Plotting error: {e}")
        print("💡 Check that your data has numeric values")
        print("💡 Try data.head() to inspect your data first")

def find_similar_column(target, columns):
    """Find most similar column name"""
    import difflib
    matches = difflib.get_close_matches(target, columns, n=1)
    return matches[0] if matches else "No similar columns found"
```

</div>

## Next Steps from Playground

### After Experimenting

1. **[View Advanced Examples](../examples/)** - See more sophisticated analyses
2. **[Download Full Datasets](../getting_started/installation/)** - Get complete research datasets
3. **[Join Community](../community/)** - Share your discoveries
4. **[Contribute Back](../contributor_guide/)** - Add your own data or tools

### Export Your Work

- **Download notebooks** with your modifications
- **Export figures** in publication-ready formats
- **Share analyses** with colleagues
- **Build on playground** experiments in your research

---

*The playground is designed to be educational and non-destructive. Experiment freely - you can't break anything!*