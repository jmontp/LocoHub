# Tutorial 3: Basic Visualization

## Overview

Learn to create essential biomechanical visualizations: phase averages with standard deviation bands, spaghetti plots showing all cycles, and publication-ready figures.

## Learning Objectives

- Compute and plot phase averages
- Add standard deviation shading
- Create spaghetti plots
- Customize plots for publication
- Compare multiple conditions

## Setup and Imports

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from user_libs.python.locomotion_data import LocomotionData

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')

# Load and filter data
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
level_walking = data[(data['task'] == 'level_walking') & (data['subject'] == 'SUB01')]
```

## Computing Phase Averages

### Basic Phase Average

```python
def compute_phase_average(data, variable):
    """Compute mean and std across cycles for each phase point."""
    # Group by phase_percent and compute statistics
    grouped = data.groupby('phase_percent')[variable]
    
    mean_curve = grouped.mean()
    std_curve = grouped.std()
    
    return mean_curve, std_curve

# Compute average knee flexion
knee_mean, knee_std = compute_phase_average(level_walking, 'knee_flexion_angle_ipsi_rad')

# Convert to degrees for plotting
knee_mean_deg = np.degrees(knee_mean)
knee_std_deg = np.degrees(knee_std)
```

### Using Built-in Methods

```python
# Using LocomotionData methods
mean_patterns = level_walking.get_mean_patterns('SUB01', 'level_walking')

# Access specific variable
knee_mean = mean_patterns['knee_flexion_angle_ipsi_rad']
```

## Creating Basic Plots

### Phase Average with Standard Deviation

```python
def plot_phase_average_with_std(phase_percent, mean, std, title='', ylabel='', xlabel='Gait Cycle (%)'):
    """Create phase average plot with ±1 SD shading."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot mean line
    ax.plot(phase_percent, mean, 'b-', linewidth=2, label='Mean')
    
    # Add standard deviation shading
    ax.fill_between(phase_percent, 
                     mean - std, 
                     mean + std, 
                     alpha=0.3, 
                     color='blue',
                     label='±1 SD')
    
    # Formatting
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    # Set x-axis limits
    ax.set_xlim(0, 100)
    
    return fig, ax

# Create the plot
phase_percent = knee_mean_deg.index
fig, ax = plot_phase_average_with_std(
    phase_percent,
    knee_mean_deg,
    knee_std_deg,
    title='Knee Flexion During Level Walking',
    ylabel='Knee Flexion (degrees)'
)

plt.show()
```

### Multiple Standard Deviation Bands

```python
def plot_with_confidence_bands(phase_percent, mean, std, title=''):
    """Plot with multiple confidence intervals."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot mean
    ax.plot(phase_percent, mean, 'b-', linewidth=2, label='Mean')
    
    # Add multiple SD bands
    ax.fill_between(phase_percent, mean - 2*std, mean + 2*std, 
                     alpha=0.15, color='blue', label='±2 SD (95%)')
    ax.fill_between(phase_percent, mean - std, mean + std, 
                     alpha=0.3, color='blue', label='±1 SD (68%)')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Angle (degrees)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    return fig, ax
```

## Spaghetti Plots

### Plot All Cycles

```python
def create_spaghetti_plot(data, variable, title=''):
    """Plot all individual cycles overlaid."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot each cycle
    for cycle_id in data['cycle_id'].unique():
        cycle_data = data[data['cycle_id'] == cycle_id]
        values = np.degrees(cycle_data[variable].values)  # Convert to degrees
        phase = cycle_data['phase_percent'].values
        
        ax.plot(phase, values, alpha=0.3, linewidth=0.5, color='gray')
    
    # Add mean on top
    mean_curve = data.groupby('phase_percent')[variable].mean()
    ax.plot(mean_curve.index, np.degrees(mean_curve.values), 
            'r-', linewidth=2, label='Mean')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Angle (degrees)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    return fig, ax

# Create spaghetti plot
fig, ax = create_spaghetti_plot(
    level_walking,
    'knee_flexion_angle_ipsi_rad',
    'All Knee Flexion Cycles - Level Walking'
)
plt.show()
```

### Spaghetti with Highlighted Mean

```python
def spaghetti_with_highlights(data, variable, highlight_outliers=True):
    """Spaghetti plot with mean and outlier detection."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Calculate statistics for outlier detection
    all_cycles = []
    for cycle_id in data['cycle_id'].unique():
        cycle_data = data[data['cycle_id'] == cycle_id]
        values = np.degrees(cycle_data[variable].values)
        all_cycles.append(values)
    
    all_cycles = np.array(all_cycles)
    mean_cycle = np.mean(all_cycles, axis=0)
    std_cycle = np.std(all_cycles, axis=0)
    
    # Plot individual cycles
    for i, cycle in enumerate(all_cycles):
        # Check if cycle is outlier (>2 SD from mean at any point)
        is_outlier = np.any(np.abs(cycle - mean_cycle) > 2 * std_cycle)
        
        if is_outlier and highlight_outliers:
            ax.plot(range(150), cycle, 'r-', alpha=0.5, linewidth=0.5)
        else:
            ax.plot(range(150), cycle, 'gray', alpha=0.3, linewidth=0.5)
    
    # Plot mean
    ax.plot(range(150), mean_cycle, 'b-', linewidth=3, label='Mean')
    
    # Add SD bands
    ax.fill_between(range(150), 
                     mean_cycle - std_cycle, 
                     mean_cycle + std_cycle,
                     alpha=0.2, color='blue')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Angle (degrees)')
    ax.set_title(f'{variable} - All Cycles with Outliers Highlighted')
    ax.legend()
    
    # Convert x-axis to percentage
    ax.set_xticks(np.linspace(0, 150, 6))
    ax.set_xticklabels(['0', '20', '40', '60', '80', '100'])
    
    return fig, ax
```

## Comparing Conditions

### Side-by-Side Comparison

```python
def compare_conditions(data, variable, conditions_dict):
    """Compare multiple conditions side by side."""
    fig, axes = plt.subplots(1, len(conditions_dict), figsize=(15, 5))
    
    if len(conditions_dict) == 1:
        axes = [axes]
    
    for ax, (condition_name, condition_filter) in zip(axes, conditions_dict.items()):
        # Filter data
        condition_data = data[condition_filter]
        
        # Compute mean and std
        mean = condition_data.groupby('phase_percent')[variable].mean()
        std = condition_data.groupby('phase_percent')[variable].std()
        
        # Convert to degrees
        mean_deg = np.degrees(mean)
        std_deg = np.degrees(std)
        
        # Plot
        ax.plot(mean_deg.index, mean_deg.values, 'b-', linewidth=2)
        ax.fill_between(mean_deg.index, 
                        mean_deg - std_deg, 
                        mean_deg + std_deg,
                        alpha=0.3)
        
        ax.set_title(condition_name)
        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Angle (degrees)')
        ax.set_xlim(0, 100)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

# Example: Compare different walking conditions
conditions = {
    'Level Walking': data['task'] == 'level_walking',
    'Incline Walking': data['task'] == 'incline_walking',
    'Decline Walking': data['task'] == 'decline_walking'
}

fig = compare_conditions(data[data['subject'] == 'SUB01'], 
                         'knee_flexion_angle_ipsi_rad',
                         conditions)
plt.show()
```

### Overlay Comparison

```python
def overlay_conditions(data, variable, conditions_dict, colors=None):
    """Overlay multiple conditions on same plot."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if colors is None:
        colors = plt.cm.Set1(np.linspace(0, 1, len(conditions_dict)))
    
    for i, (condition_name, condition_filter) in enumerate(conditions_dict.items()):
        # Filter and compute statistics
        condition_data = data[condition_filter]
        mean = condition_data.groupby('phase_percent')[variable].mean()
        std = condition_data.groupby('phase_percent')[variable].std()
        
        # Convert to degrees
        mean_deg = np.degrees(mean)
        std_deg = np.degrees(std)
        
        # Plot
        ax.plot(mean_deg.index, mean_deg.values, 
                color=colors[i], linewidth=2, label=condition_name)
        ax.fill_between(mean_deg.index,
                        mean_deg - std_deg,
                        mean_deg + std_deg,
                        alpha=0.2, color=colors[i])
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=12)
    ax.set_ylabel('Angle (degrees)', fontsize=12)
    ax.set_title(f'{variable.replace("_", " ").title()}', fontsize=14)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    return fig, ax

# Create overlay plot
fig, ax = overlay_conditions(
    data[data['subject'] == 'SUB01'],
    'knee_flexion_angle_ipsi_rad',
    conditions
)
plt.show()
```

## Publication-Ready Figures

### Professional Styling

```python
def create_publication_plot(data, variable, title='', save_path=None):
    """Create publication-quality figure."""
    # Set publication style
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial']
    plt.rcParams['font.size'] = 10
    
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
    
    # Compute statistics
    mean = data.groupby('phase_percent')[variable].mean()
    std = data.groupby('phase_percent')[variable].std()
    sem = data.groupby('phase_percent')[variable].sem()  # Standard error
    
    # Convert to degrees
    mean_deg = np.degrees(mean)
    std_deg = np.degrees(std)
    sem_deg = np.degrees(sem)
    
    # Plot with confidence interval
    ax.plot(mean_deg.index, mean_deg.values, 
            'k-', linewidth=1.5, label='Mean')
    
    # Use SEM for tighter confidence bands in publications
    ax.fill_between(mean_deg.index,
                    mean_deg - 1.96*sem_deg,  # 95% CI
                    mean_deg + 1.96*sem_deg,
                    alpha=0.3, color='gray',
                    label='95% CI')
    
    # Formatting
    ax.set_xlabel('Gait Cycle (%)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Angle (°)', fontsize=11, fontweight='bold')
    
    if title:
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    
    # Clean up axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, 100)
    
    # Add vertical lines for gait events (typical values)
    ax.axvline(x=60, color='gray', linestyle='--', alpha=0.5, linewidth=0.5)
    ax.text(60, ax.get_ylim()[0], 'Toe-off', ha='center', va='bottom', fontsize=8)
    
    ax.legend(frameon=False, loc='upper right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig, ax
```

## Practice Exercises

### Exercise 1: Multi-Variable Plot
Create a figure showing hip, knee, and ankle flexion on the same plot with different colors.

### Exercise 2: Bilateral Comparison
Plot ipsilateral vs contralateral knee flexion with appropriate labeling.

### Exercise 3: Statistical Bands
Create a plot showing mean, median, and quartiles instead of mean ± SD.

## Key Takeaways

1. **Always compute statistics properly** - Group by phase_percent
2. **Convert units for display** - Radians to degrees for angles
3. **Use transparency** - Alpha values for overlapping data
4. **Label everything** - Axes, units, conditions
5. **Save high-resolution** - 300 DPI for publications

## Next Steps

[Continue to Tutorial 4: Cycle Analysis →](04_cycle_analysis.md)

Learn to extract and analyze individual gait cycles, calculate ROM, peak values, and timing metrics.