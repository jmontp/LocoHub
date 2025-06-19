# Publication-Ready Plots for Research Papers

Generate high-quality figures suitable for academic publications using the LocomotionData library.

## Quick Start

```python
from lib.core.locomotion_analysis import LocomotionData
import matplotlib.pyplot as plt

# Load your data
loco = LocomotionData('your_dataset_phase.parquet')

# Set publication style
plt.style.use('seaborn-v0_8-paper')
plt.rcParams['font.size'] = 12
plt.rcParams['axes.linewidth'] = 1.5
```

## Publication Figure Types

### 1. Mean ± Standard Deviation Plots

Classic biomechanics visualization with confidence bands:

```python
# Select kinematic variables
features = ['hip_flexion_angle_ipsi_rad', 
           'knee_flexion_angle_ipsi_rad',
           'ankle_flexion_angle_ipsi_rad']

# Create publication figure
loco.plot_phase_patterns(
    subject='SUB01',
    task='level_walking', 
    features=features,
    plot_type='mean',
    save_path='fig1_kinematics.png'
)
```

### 2. Task Comparison Figures

Compare biomechanical patterns across locomotion tasks:

```python
# Compare walking conditions
tasks = ['level_walking', 'incline_walking', 'decline_walking']

loco.plot_task_comparison(
    subject='SUB01',
    tasks=tasks,
    features=['knee_flexion_angle_ipsi_rad'],
    save_path='fig2_task_comparison.png'
)
```

### 3. Multi-Panel Figures

Create journal-ready multi-panel layouts:

```python
import matplotlib.pyplot as plt
import numpy as np

# Get data for custom plotting
data_3d, feature_names = loco.get_cycles('SUB01', 'level_walking', features)
valid_mask = loco.validate_cycles('SUB01', 'level_walking', features)

# Create publication figure
fig, axes = plt.subplots(3, 1, figsize=(6, 8), sharex=True)
phase_x = np.linspace(0, 100, 150)

for i, (ax, feature) in enumerate(zip(axes, feature_names)):
    # Extract valid data
    feat_data = data_3d[:, :, i]
    valid_data = feat_data[valid_mask, :]
    
    # Calculate statistics
    mean_curve = np.mean(valid_data, axis=0)
    std_curve = np.std(valid_data, axis=0)
    
    # Plot with publication styling
    ax.fill_between(phase_x, 
                   mean_curve - std_curve,
                   mean_curve + std_curve,
                   alpha=0.3, color='#1f77b4', 
                   label='±1 SD')
    ax.plot(phase_x, mean_curve, 
           color='#1f77b4', linewidth=2,
           label='Mean')
    
    # Format axes
    ax.set_ylabel(f'{feature.split("_")[0].title()}\n(rad)')
    ax.set_xlim(0, 100)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    if i == 0:
        ax.legend(loc='upper right', frameon=False)

axes[-1].set_xlabel('Gait Cycle (%)')
plt.tight_layout()
plt.savefig('fig3_kinematics_panel.png', dpi=300, bbox_inches='tight')
```

### 4. Statistical Comparison Plots

Show group differences with error bars:

```python
# Calculate peak values across subjects
subjects = loco.get_subjects()
peak_knee_angles = []

for subject in subjects:
    mean_patterns = loco.get_mean_patterns(
        subject, 'level_walking', 
        ['knee_flexion_angle_ipsi_rad']
    )
    if 'knee_flexion_angle_ipsi_rad' in mean_patterns:
        peak_angle = np.max(mean_patterns['knee_flexion_angle_ipsi_rad'])
        peak_knee_angles.append(peak_angle)

# Create bar plot with error bars
fig, ax = plt.subplots(figsize=(6, 4))
x = np.arange(len(subjects))
mean_peak = np.mean(peak_knee_angles)
std_peak = np.std(peak_knee_angles)

ax.bar(x, peak_knee_angles, color='#1f77b4', alpha=0.7)
ax.axhline(mean_peak, color='red', linestyle='--', 
          label=f'Mean: {mean_peak:.2f}±{std_peak:.2f} rad')
ax.set_xticks(x)
ax.set_xticklabels(subjects)
ax.set_ylabel('Peak Knee Flexion (rad)')
ax.set_xlabel('Subject')
ax.legend()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('fig4_peak_comparison.png', dpi=300, bbox_inches='tight')
```

### 5. Percentile-Based Visualization

Show data distribution with percentile bands:

```python
# Get data
data_3d, _ = loco.get_cycles('SUB01', 'level_walking', 
                            ['knee_flexion_angle_ipsi_rad'])
valid_mask = loco.validate_cycles('SUB01', 'level_walking',
                                 ['knee_flexion_angle_ipsi_rad'])

# Calculate percentiles
valid_data = data_3d[valid_mask, :, 0]
p10 = np.percentile(valid_data, 10, axis=0)
p25 = np.percentile(valid_data, 25, axis=0)
p50 = np.percentile(valid_data, 50, axis=0)
p75 = np.percentile(valid_data, 75, axis=0)
p90 = np.percentile(valid_data, 90, axis=0)

# Create publication figure
fig, ax = plt.subplots(figsize=(6, 4))
phase_x = np.linspace(0, 100, 150)

# Plot percentile bands
ax.fill_between(phase_x, p10, p90, alpha=0.2, 
               color='#1f77b4', label='10-90th percentile')
ax.fill_between(phase_x, p25, p75, alpha=0.4,
               color='#1f77b4', label='25-75th percentile')
ax.plot(phase_x, p50, color='#d62728', linewidth=2,
       label='Median')

# Format
ax.set_xlabel('Gait Cycle (%)')
ax.set_ylabel('Knee Flexion (rad)')
ax.set_xlim(0, 100)
ax.legend(loc='upper right', frameon=False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('fig5_percentiles.png', dpi=300, bbox_inches='tight')
```

## Publication Formatting Guidelines

### Figure Size and Resolution

```python
# Standard single-column figure
fig, ax = plt.subplots(figsize=(3.5, 3))  # inches

# Double-column figure
fig, ax = plt.subplots(figsize=(7, 4))

# Save at high resolution
plt.savefig('figure.png', dpi=300, bbox_inches='tight')
plt.savefig('figure.pdf', bbox_inches='tight')  # Vector format
```

### Font and Style Settings

```python
# Set publication-ready defaults
plt.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica'],
    'axes.linewidth': 1.5,
    'lines.linewidth': 2,
    'patch.linewidth': 1,
    'grid.linewidth': 0.5,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
    'xtick.major.size': 4,
    'ytick.major.size': 4
})
```

### Color Schemes

```python
# Colorblind-friendly palette
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', 
          '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']

# Grayscale for print
grays = ['#000000', '#404040', '#808080', '#bfbfbf']

# Apply to task comparison
for i, task in enumerate(tasks):
    ax.plot(phase_x, data, color=colors[i % len(colors)], 
            label=task)
```

## Export Options

### Vector Formats

```python
# PDF for LaTeX inclusion
plt.savefig('figure.pdf', format='pdf', bbox_inches='tight')

# EPS for older journals
plt.savefig('figure.eps', format='eps', bbox_inches='tight')

# SVG for web/editing
plt.savefig('figure.svg', format='svg', bbox_inches='tight')
```

### Raster Formats

```python
# PNG with transparent background
plt.savefig('figure.png', dpi=300, transparent=True,
            bbox_inches='tight')

# TIFF for some journals
plt.savefig('figure.tiff', dpi=300, compression='lzw',
            bbox_inches='tight')
```

## Common Research Figure Examples

### Ensemble Average Curves

```python
# Standard biomechanics ensemble plot
features = ['hip_flexion_angle_ipsi_rad',
           'hip_moment_ipsi_Nm',
           'hip_power_ipsi_W']

fig, axes = plt.subplots(3, 1, figsize=(4, 8), sharex=True)

for ax, feature in zip(axes, features):
    # Get mean pattern
    mean_patterns = loco.get_mean_patterns('SUB01', 
                                          'level_walking',
                                          [feature])
    if feature in mean_patterns:
        ax.plot(phase_x, mean_patterns[feature], 
               'k-', linewidth=2)
    
    # Add reference lines
    ax.axhline(0, color='gray', linestyle='-', 
              linewidth=0.5, alpha=0.5)
    ax.axvline(60, color='gray', linestyle='--',
              linewidth=0.5, alpha=0.5)  # Toe-off
    
    # Format
    ax.set_ylabel(feature.split('_')[0].title())
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

axes[-1].set_xlabel('Gait Cycle (%)')
plt.tight_layout()
```

### Between-Group Comparisons

```python
# Compare two groups/conditions
conditions = ['normal_walking', 'pathological_walking']
colors = ['#1f77b4', '#d62728']

fig, ax = plt.subplots(figsize=(5, 4))

for i, condition in enumerate(conditions):
    # Get mean and std
    data_3d, _ = loco.get_cycles('SUB01', condition, 
                                ['knee_flexion_angle_ipsi_rad'])
    valid_mask = loco.validate_cycles('SUB01', condition,
                                     ['knee_flexion_angle_ipsi_rad'])
    valid_data = data_3d[valid_mask, :, 0]
    
    mean_curve = np.mean(valid_data, axis=0)
    std_curve = np.std(valid_data, axis=0)
    
    # Plot with shaded error
    ax.plot(phase_x, mean_curve, color=colors[i], 
           linewidth=2, label=condition)
    ax.fill_between(phase_x, 
                   mean_curve - std_curve,
                   mean_curve + std_curve,
                   alpha=0.2, color=colors[i])

ax.set_xlabel('Gait Cycle (%)')
ax.set_ylabel('Knee Flexion (rad)')
ax.legend(frameon=False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
```

## Current Limitations

### Missing Publication Features

1. **Statistical Annotations**: No built-in significance testing or p-value annotations
2. **3D Kinematics**: Limited support for 3D joint angle visualization
3. **Stick Figures**: No animated stick figure generation
4. **Phase Events**: Manual annotation required for gait events (heel strike, toe-off)
5. **SPM Analysis**: Statistical Parametric Mapping not integrated

### Workarounds

```python
# Add phase events manually
ax.axvline(60, color='red', linestyle='--', 
          alpha=0.5, label='Toe-off')
ax.text(60, ax.get_ylim()[1]*0.9, 'TO', 
       ha='center', fontsize=8)

# Add significance bars manually
from matplotlib.patches import Rectangle
sig_region = Rectangle((20, ax.get_ylim()[1]*0.95), 
                      30, ax.get_ylim()[1]*0.02,
                      facecolor='black')
ax.add_patch(sig_region)
ax.text(35, ax.get_ylim()[1]*0.98, '*', 
       ha='center', fontsize=12)
```

## Best Practices

1. **Consistent Styling**: Define style settings at script start
2. **Vector Formats**: Use PDF/SVG for final submission
3. **Color Choice**: Consider colorblind accessibility
4. **Data Validation**: Only plot validated cycles
5. **Clear Labels**: Use descriptive axis labels with units
6. **Figure Legends**: Place outside plot area when possible

## Example: Complete Publication Figure

```python
# Full example for a research paper
import matplotlib.pyplot as plt
import numpy as np
from lib.core.locomotion_analysis import LocomotionData

# Set publication style
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'sans-serif',
    'axes.linewidth': 1.5,
    'lines.linewidth': 2
})

# Load data
loco = LocomotionData('test_data.csv', file_type='csv')

# Create figure
fig, axes = plt.subplots(2, 2, figsize=(7, 6))

# Panel A: Kinematics
ax = axes[0, 0]
features = ['knee_flexion_angle_ipsi_rad']
mean_patterns = loco.get_mean_patterns('SUB01', 
                                      'level_walking',
                                      features)
phase_x = np.linspace(0, 100, 150)
ax.plot(phase_x, mean_patterns[features[0]], 'k-', linewidth=2)
ax.set_xlabel('Gait Cycle (%)')
ax.set_ylabel('Knee Angle (rad)')
ax.set_title('A. Knee Kinematics', loc='left')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Panel B: Task comparison
ax = axes[0, 1]
tasks = ['level_walking', 'incline_walking']
colors = ['#1f77b4', '#d62728']
for i, task in enumerate(tasks):
    patterns = loco.get_mean_patterns('SUB01', task, features)
    if features[0] in patterns:
        ax.plot(phase_x, patterns[features[0]], 
               color=colors[i], label=task.replace('_', ' '))
ax.set_xlabel('Gait Cycle (%)')
ax.set_ylabel('Knee Angle (rad)')
ax.set_title('B. Task Comparison', loc='left')
ax.legend(frameon=False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Panel C: Subject variability
ax = axes[1, 0]
# (Add percentile plot code here)
ax.set_title('C. Inter-subject Variability', loc='left')

# Panel D: Peak values
ax = axes[1, 1]
# (Add bar plot code here)
ax.set_title('D. Peak Comparisons', loc='left')

plt.tight_layout()
plt.savefig('figure_multipanel.pdf', bbox_inches='tight')
plt.savefig('figure_multipanel.png', dpi=300, bbox_inches='tight')
```

## Resources

- [Matplotlib Publication Guidelines](https://matplotlib.org/stable/tutorials/introductory/customizing.html)
- [Scientific Color Maps](https://www.nature.com/articles/s41467-020-19160-7)
- [Journal Figure Requirements](https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions)