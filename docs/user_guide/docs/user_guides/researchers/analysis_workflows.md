# Researcher Analysis Workflows

This guide provides practical workflows for biomechanical researchers using the locomotion data standardization library. It covers common research scenarios from multi-subject analysis to statistical testing.

## Overview

The locomotion analysis library provides tools for:

- Loading standardized phase-indexed biomechanical data
- Computing mean patterns and variability metrics
- Identifying outliers and data quality issues
- Creating publication-ready visualizations
- Performing basic statistical comparisons

## Prerequisites

```python
# Import required libraries
import numpy as np
import pandas as pd
from locomotion_analysis import LocomotionData
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
```

## Common Research Workflows

### 1. Multi-Subject Group Analysis

Analyze patterns across multiple subjects to identify population-level trends.

```python
# Load dataset
loco = LocomotionData('your_dataset_phase.parquet')

# Get all subjects
subjects = loco.get_subjects()
print(f"Found {len(subjects)} subjects")

# Collect mean patterns for each subject
all_knee_patterns = []
subject_labels = []

for subject in subjects:
    try:
        # Get mean knee flexion pattern for level walking
        mean_pattern = loco.get_mean_patterns(
            subject, 
            'level_walking',
            features=['knee_flexion_angle_ipsi_rad']
        )
        
        if mean_pattern is not None:
            all_knee_patterns.append(mean_pattern['knee_flexion_angle_ipsi_rad'])
            subject_labels.append(subject)
    except:
        print(f"Skipping {subject} - no level walking data")

# Convert to numpy array for analysis
knee_matrix = np.array(all_knee_patterns)
print(f"Collected data from {knee_matrix.shape[0]} subjects")

# Compute group statistics
group_mean = np.mean(knee_matrix, axis=0)
group_std = np.std(knee_matrix, axis=0)
group_ci_lower = group_mean - 1.96 * group_std / np.sqrt(len(all_knee_patterns))
group_ci_upper = group_mean + 1.96 * group_std / np.sqrt(len(all_knee_patterns))

# Visualize group pattern
phases = np.linspace(0, 100, 150)
plt.figure(figsize=(10, 6))
plt.plot(phases, group_mean, 'k-', linewidth=2, label='Group Mean')
plt.fill_between(phases, group_ci_lower, group_ci_upper, alpha=0.3, label='95% CI')
plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion (rad)')
plt.title(f'Group Knee Flexion Pattern (n={len(all_knee_patterns)})')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

### 2. Cross-Task Comparison

Compare biomechanical patterns across different locomotion tasks.

```python
# Compare level vs incline walking
subject = 'SUB01'  # Example subject

# Get patterns for different tasks
level_pattern = loco.get_mean_patterns(
    subject, 'level_walking',
    features=['knee_flexion_angle_ipsi_rad', 'hip_moment_ipsi_Nm']
)

incline_pattern = loco.get_mean_patterns(
    subject, 'incline_walking', 
    features=['knee_flexion_angle_ipsi_rad', 'hip_moment_ipsi_Nm']
)

# Use built-in comparison visualization
loco.plot_task_comparison(
    subject,
    ['level_walking', 'incline_walking'],
    features=['knee_flexion_angle_ipsi_rad']
)

# Manual statistical comparison
if level_pattern is not None and incline_pattern is not None:
    # Extract patterns
    level_knee = level_pattern['knee_flexion_angle_ipsi_rad']
    incline_knee = incline_pattern['knee_flexion_angle_ipsi_rad']
    
    # Compute differences
    knee_diff = incline_knee - level_knee
    
    # Find peak differences
    max_diff_idx = np.argmax(np.abs(knee_diff))
    max_diff_phase = max_diff_idx / 150 * 100  # Convert to % gait cycle
    max_diff_value = knee_diff[max_diff_idx]
    
    print(f"Maximum difference: {np.rad2deg(max_diff_value):.1f}° at {max_diff_phase:.1f}% gait cycle")
    
    # ROM comparison
    level_rom = loco.calculate_rom(subject, 'level_walking')
    incline_rom = loco.calculate_rom(subject, 'incline_walking')
    
    if level_rom is not None and incline_rom is not None:
        print(f"Level walking knee ROM: {np.rad2deg(level_rom['knee_flexion_angle_ipsi_rad']):.1f}°")
        print(f"Incline walking knee ROM: {np.rad2deg(incline_rom['knee_flexion_angle_ipsi_rad']):.1f}°")
```

### 3. Statistical Testing Approaches

Perform statistical comparisons between conditions or groups.

```python
# Example: Compare knee ROM between two groups
group1_subjects = ['SUB01', 'SUB02', 'SUB03']  # e.g., healthy controls
group2_subjects = ['SUB04', 'SUB05', 'SUB06']  # e.g., patient group

# Collect ROM data for each group
group1_rom = []
group2_rom = []

for subject in group1_subjects:
    rom = loco.calculate_rom(subject, 'level_walking')
    if rom is not None:
        group1_rom.append(np.rad2deg(rom['knee_flexion_angle_ipsi_rad']))

for subject in group2_subjects:
    rom = loco.calculate_rom(subject, 'level_walking')
    if rom is not None:
        group2_rom.append(np.rad2deg(rom['knee_flexion_angle_ipsi_rad']))

# Perform t-test
if len(group1_rom) > 0 and len(group2_rom) > 0:
    t_stat, p_value = stats.ttest_ind(group1_rom, group2_rom)
    
    print(f"Group 1 knee ROM: {np.mean(group1_rom):.1f} ± {np.std(group1_rom):.1f}°")
    print(f"Group 2 knee ROM: {np.mean(group2_rom):.1f} ± {np.std(group2_rom):.1f}°")
    print(f"t-statistic: {t_stat:.3f}, p-value: {p_value:.3f}")
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((np.std(group1_rom)**2 + np.std(group2_rom)**2) / 2)
    cohens_d = (np.mean(group1_rom) - np.mean(group2_rom)) / pooled_std
    print(f"Cohen's d: {cohens_d:.3f}")
```

### 4. Data Quality Assessment

Identify and handle outliers or poor quality data before analysis.

```python
# Check data quality for a subject
subject = 'SUB01'
task = 'level_walking'

# Validate cycles
valid_mask = loco.validate_cycles(subject, task)
print(f"Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")

# Find outliers
outlier_indices = loco.find_outlier_cycles(subject, task)
print(f"Outlier cycles: {len(outlier_indices)}")

# Get only valid, non-outlier cycles
data_3d, features = loco.get_cycles(subject, task)
if data_3d is not None:
    # Create clean mask (valid and not outlier)
    clean_mask = valid_mask.copy()
    clean_mask[outlier_indices] = False
    
    # Extract clean data
    clean_data = data_3d[clean_mask, :, :]
    print(f"Clean cycles for analysis: {clean_data.shape[0]}")
    
    # Compute statistics on clean data only
    knee_idx = features.index('knee_flexion_angle_ipsi_rad')
    clean_knee_patterns = clean_data[:, :, knee_idx]
    
    mean_pattern = np.mean(clean_knee_patterns, axis=0)
    std_pattern = np.std(clean_knee_patterns, axis=0)
```

### 5. Exporting Data for External Analysis

Export processed data for analysis in other software (R, SPSS, etc.).

```python
# Example: Export summary statistics for all subjects
export_data = []

for subject in loco.get_subjects():
    for task in loco.get_tasks():
        # Get summary statistics
        stats = loco.get_summary_statistics(subject, task)
        
        if stats is not None:
            # Extract key metrics
            row = {
                'subject': subject,
                'task': task,
                'knee_rom_deg': np.rad2deg(stats['knee_flexion_angle_ipsi_rad']['rom']),
                'knee_mean_deg': np.rad2deg(stats['knee_flexion_angle_ipsi_rad']['mean']),
                'hip_moment_peak_Nm': stats['hip_moment_ipsi_Nm']['max'],
                'n_valid_cycles': stats['n_cycles']
            }
            export_data.append(row)

# Create DataFrame and export
df_export = pd.DataFrame(export_data)
df_export.to_csv('biomechanics_summary.csv', index=False)
print(f"Exported {len(df_export)} records to biomechanics_summary.csv")

# Export time-series data for specific analysis
# Get mean patterns for a group
group_patterns = []
for subject in group1_subjects:
    pattern = loco.get_mean_patterns(subject, 'level_walking')
    if pattern is not None:
        pattern_df = pd.DataFrame(pattern)
        pattern_df['subject'] = subject
        pattern_df['phase'] = np.arange(150)
        group_patterns.append(pattern_df)

if group_patterns:
    combined_patterns = pd.concat(group_patterns)
    combined_patterns.to_csv('group_patterns.csv', index=False)
    print(f"Exported patterns for {len(group_patterns)} subjects")
```

## Common Research Questions

### Q1: How do I identify responders vs non-responders to an intervention?

```python
# Pre/post intervention analysis
pre_subjects = ['SUB01_PRE', 'SUB02_PRE', 'SUB03_PRE']
post_subjects = ['SUB01_POST', 'SUB02_POST', 'SUB03_POST']

changes = []
for i, (pre, post) in enumerate(zip(pre_subjects, post_subjects)):
    pre_rom = loco.calculate_rom(pre, 'level_walking')
    post_rom = loco.calculate_rom(post, 'level_walking')
    
    if pre_rom is not None and post_rom is not None:
        knee_change = np.rad2deg(post_rom['knee_flexion_angle_ipsi_rad'] - 
                                pre_rom['knee_flexion_angle_ipsi_rad'])
        changes.append(knee_change)

# Define responder threshold (e.g., >5 degrees improvement)
responder_threshold = 5.0
responders = [c > responder_threshold for c in changes]
print(f"Responders: {sum(responders)}/{len(responders)}")
```

### Q2: How do I analyze bilateral asymmetry?

```python
# Compare ipsilateral vs contralateral patterns
ipsi_pattern = loco.get_mean_patterns(
    'SUB01', 'level_walking',
    features=['knee_flexion_angle_ipsi_rad']
)
contra_pattern = loco.get_mean_patterns(
    'SUB01', 'level_walking', 
    features=['knee_flexion_angle_contra_rad']
)

if ipsi_pattern is not None and contra_pattern is not None:
    # Compute symmetry index at each phase
    ipsi = ipsi_pattern['knee_flexion_angle_ipsi_rad']
    contra = contra_pattern['knee_flexion_angle_contra_rad']
    
    # Symmetry index: (ipsi - contra) / (ipsi + contra) * 100
    symmetry_index = (ipsi - contra) / (ipsi + contra) * 100
    
    # Mean absolute symmetry index
    mean_asi = np.mean(np.abs(symmetry_index))
    print(f"Mean Absolute Symmetry Index: {mean_asi:.1f}%")
```

### Q3: How do I perform phase-specific analysis?

```python
# Analyze specific gait phases
data_3d, features = loco.get_cycles('SUB01', 'level_walking')

if data_3d is not None:
    knee_idx = features.index('knee_flexion_angle_ipsi_rad')
    
    # Define phase ranges (% gait cycle)
    loading_response = slice(0, 15)  # 0-10% gait cycle
    midstance = slice(15, 45)  # 10-30% gait cycle
    terminal_stance = slice(45, 75)  # 30-50% gait cycle
    
    # Extract phase-specific data
    lr_values = data_3d[:, loading_response, knee_idx]
    ms_values = data_3d[:, midstance, knee_idx]
    ts_values = data_3d[:, terminal_stance, knee_idx]
    
    # Compute phase-specific metrics
    print(f"Loading Response: {np.rad2deg(np.mean(lr_values)):.1f} ± {np.rad2deg(np.std(lr_values)):.1f}°")
    print(f"Midstance: {np.rad2deg(np.mean(ms_values)):.1f} ± {np.rad2deg(np.std(ms_values)):.1f}°")
    print(f"Terminal Stance: {np.rad2deg(np.mean(ts_values)):.1f} ± {np.rad2deg(np.std(ts_values)):.1f}°")
```

## Current Limitations

The locomotion analysis library currently has some limitations researchers should be aware of:

1. **No built-in group comparison methods** - Manual implementation required for between-group statistics
2. **Limited export functionality** - Manual DataFrame creation needed for external analysis
3. **No mixed-effects modeling** - For hierarchical data, export to R or specialized software required
4. **Basic statistical tests only** - Complex analyses require external tools
5. **No automatic report generation** - Results must be manually compiled
6. **Limited support for longitudinal analysis** - Time-series comparisons need custom implementation

## Recommendations for Extended Analysis

For analyses beyond the current library capabilities:

1. **Export to R/SPSS**: Use the export patterns shown above to create CSV files for advanced statistical modeling
2. **Use scipy.stats**: For additional statistical tests (ANOVA, non-parametric tests)
3. **Implement custom functions**: Build wrapper functions for repeated analyses
4. **Consider statsmodels**: For regression analyses and mixed models in Python

## Example: Complete Research Workflow

Here's a complete workflow for a typical research question:

```python
def analyze_intervention_effects(loco, control_subjects, intervention_subjects, task='level_walking'):
    """
    Analyze the effects of an intervention on gait biomechanics.
    
    Returns summary statistics and effect sizes.
    """
    results = {
        'control': {'subjects': [], 'knee_rom': [], 'hip_moment_peak': []},
        'intervention': {'subjects': [], 'knee_rom': [], 'hip_moment_peak': []}
    }
    
    # Collect control group data
    for subject in control_subjects:
        rom = loco.calculate_rom(subject, task)
        stats = loco.get_summary_statistics(subject, task)
        
        if rom is not None and stats is not None:
            results['control']['subjects'].append(subject)
            results['control']['knee_rom'].append(np.rad2deg(rom['knee_flexion_angle_ipsi_rad']))
            results['control']['hip_moment_peak'].append(stats['hip_moment_ipsi_Nm']['max'])
    
    # Collect intervention group data
    for subject in intervention_subjects:
        rom = loco.calculate_rom(subject, task)
        stats = loco.get_summary_statistics(subject, task)
        
        if rom is not None and stats is not None:
            results['intervention']['subjects'].append(subject)
            results['intervention']['knee_rom'].append(np.rad2deg(rom['knee_flexion_angle_ipsi_rad']))
            results['intervention']['hip_moment_peak'].append(stats['hip_moment_ipsi_Nm']['max'])
    
    # Perform statistical comparisons
    comparisons = {}
    
    for metric in ['knee_rom', 'hip_moment_peak']:
        control_data = results['control'][metric]
        intervention_data = results['intervention'][metric]
        
        if len(control_data) > 0 and len(intervention_data) > 0:
            # T-test
            t_stat, p_value = stats.ttest_ind(control_data, intervention_data)
            
            # Effect size
            pooled_std = np.sqrt((np.std(control_data)**2 + np.std(intervention_data)**2) / 2)
            cohens_d = (np.mean(intervention_data) - np.mean(control_data)) / pooled_std
            
            comparisons[metric] = {
                'control_mean': np.mean(control_data),
                'control_std': np.std(control_data),
                'intervention_mean': np.mean(intervention_data),
                'intervention_std': np.std(intervention_data),
                't_statistic': t_stat,
                'p_value': p_value,
                'cohens_d': cohens_d
            }
    
    return results, comparisons

# Use the function
control = ['SUB01', 'SUB02', 'SUB03']
intervention = ['SUB04', 'SUB05', 'SUB06']
results, stats = analyze_intervention_effects(loco, control, intervention)

# Display results
for metric, comparison in stats.items():
    print(f"\n{metric}:")
    print(f"  Control: {comparison['control_mean']:.2f} ± {comparison['control_std']:.2f}")
    print(f"  Intervention: {comparison['intervention_mean']:.2f} ± {comparison['intervention_std']:.2f}")
    print(f"  p-value: {comparison['p_value']:.3f}, Cohen's d: {comparison['cohens_d']:.3f}")
```

## Next Steps

For more advanced analyses, researchers may need to:

1. Export data using the patterns shown above
2. Implement custom statistical functions
3. Use specialized biomechanics software for specific analyses
4. Contribute additional analysis methods to the library

The locomotion analysis library provides a solid foundation for biomechanical research, with room for growth based on community needs.