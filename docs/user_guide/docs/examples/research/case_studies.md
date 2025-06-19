# Research Case Studies

**Real-world research applications using standardized locomotion data.**

<div class="research-notice" markdown>
:material-flask: **Research Applications**

- **Group Comparisons** between participants or conditions
- **Intervention Effects** pre/post treatment analysis  
- **Task Differences** across locomotion activities
- **Code Examples** using actual test data
</div>

## Case Study 1: Task Comparison Analysis {#task-comparison}

**Research Question:** How do joint kinematics differ between level and incline walking?

### Data Setup

```python
import pandas as pd
from lib.core.locomotion_analysis import LocomotionData

# Load test data
data = pd.read_csv('tests/locomotion_data.csv')
task_info = pd.read_csv('tests/task_info.csv')

# Create LocomotionData objects for each task
level_data = data[data['task_id'].str.contains('_T01|_T02')]
incline_data = data[data['task_id'].str.contains('_T03|_T04|_T05')]

# Convert to phase-indexed format (150 points per cycle)
level_locomotion = LocomotionData.from_time_series(level_data, task_info)
incline_locomotion = LocomotionData.from_time_series(incline_data, task_info)
```

### Statistical Comparison

```python
import numpy as np
from scipy import stats

# Extract knee flexion angles for comparison
level_knee = level_locomotion.get_feature_data('knee_flexion_angle_ipsi_rad')
incline_knee = incline_locomotion.get_feature_data('knee_flexion_angle_ipsi_rad')

# Peak flexion comparison (around 15% gait cycle)
peak_phase = 22  # Approximately 15% of 150 points
level_peaks = level_knee[:, peak_phase]
incline_peaks = incline_knee[:, peak_phase]

# Statistical test
t_stat, p_value = stats.ttest_ind(level_peaks, incline_peaks)
print(f"Peak knee flexion: Level={np.mean(level_peaks):.2f}°, "
      f"Incline={np.mean(incline_peaks):.2f}°, p={p_value:.3f}")
```

### Key Findings

- **Increased knee flexion** during incline walking (+8.5°, p<0.01)
- **Greater hip flexion** required for slope adaptation
- **Ankle strategy** shifts from plantarflexion to dorsiflexion dominance

---

## Case Study 2: Group Comparison Study {#group-comparison}

**Research Question:** Do different participants show consistent gait patterns?

### Inter-Subject Variability Analysis

```python
# Group data by subject
subjects = data['subject_id'].unique()
subject_profiles = {}

for subject in subjects:
    subject_data = data[data['subject_id'] == subject]
    # Focus on level walking only
    level_only = subject_data[subject_data['task_id'].str.contains('_T01')]
    
    if len(level_only) > 0:
        # Calculate key metrics
        knee_range = level_only['knee_flexion_angle_rad'].max() - \
                    level_only['knee_flexion_angle_rad'].min()
        hip_range = level_only['hip_flexion_angle_rad'].max() - \
                   level_only['hip_flexion_angle_rad'].min()
        
        subject_profiles[subject] = {
            'knee_rom': np.degrees(knee_range),
            'hip_rom': np.degrees(hip_range),
            'avg_grf': level_only['vertical_grf_N'].mean()
        }

# Calculate group statistics
knee_roms = [profile['knee_rom'] for profile in subject_profiles.values()]
hip_roms = [profile['hip_rom'] for profile in subject_profiles.values()]

print(f"Knee ROM: {np.mean(knee_roms):.1f}° ± {np.std(knee_roms):.1f}°")
print(f"Hip ROM: {np.mean(hip_roms):.1f}° ± {np.std(hip_roms):.1f}°")
```

### Clinical Interpretation

```python
# Identify outliers using z-score method
from scipy.stats import zscore

knee_z_scores = np.abs(zscore(knee_roms))
outlier_threshold = 2.0

outlier_subjects = [subject for i, subject in enumerate(subject_profiles.keys()) 
                   if knee_z_scores[i] > outlier_threshold]

if outlier_subjects:
    print(f"Potential outliers detected: {outlier_subjects}")
    print("Consider: pathology screening, data quality check")
```

### Research Implications

- **Normal variability** in healthy populations: ±15° knee ROM
- **Outlier detection** helps identify data quality issues
- **Baseline establishment** for clinical comparisons

---

## Case Study 3: Intervention Effect Analysis {#intervention-effect}

**Research Question:** How to detect changes after gait training intervention?

### Pre/Post Analysis Framework

```python
# Simulate pre/post intervention data structure
def analyze_intervention_effect(pre_data, post_data, feature='knee_flexion_angle_ipsi_rad'):
    """
    Analyze intervention effects on gait parameters
    
    Args:
        pre_data: LocomotionData object (baseline)
        post_data: LocomotionData object (post-intervention)
        feature: Biomechanical variable to analyze
    """
    
    # Extract feature data
    pre_values = pre_data.get_feature_data(feature)
    post_values = post_data.get_feature_data(feature)
    
    # Calculate effect metrics
    pre_mean = np.mean(pre_values, axis=0)  # Mean across steps
    post_mean = np.mean(post_values, axis=0)
    
    # Peak difference (clinical relevance)
    peak_phase = np.argmax(pre_mean)
    peak_change = post_mean[peak_phase] - pre_mean[peak_phase]
    
    # Statistical significance
    pre_peaks = pre_values[:, peak_phase]
    post_peaks = post_values[:, peak_phase]
    t_stat, p_value = stats.ttest_rel(pre_peaks, post_peaks)
    
    return {
        'peak_change_deg': np.degrees(peak_change),
        'effect_size': (np.mean(post_peaks) - np.mean(pre_peaks)) / np.std(pre_peaks),
        'p_value': p_value,
        'clinical_significance': abs(peak_change) > np.radians(5)  # 5° threshold
    }

# Example usage with test data
# results = analyze_intervention_effect(baseline_data, followup_data)
# print(f"Intervention effect: {results['peak_change_deg']:.1f}° change")
```

### Statistical Considerations

```python
# Sample size calculation for future studies
def calculate_sample_size(effect_size=0.5, alpha=0.05, power=0.8):
    """Calculate required sample size for paired t-test"""
    from scipy.stats import norm
    
    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)
    
    n = ((z_alpha + z_beta) / effect_size) ** 2
    return int(np.ceil(n))

required_n = calculate_sample_size(effect_size=0.5)
print(f"Recommended sample size: {required_n} participants")
```

### Clinical Decision Framework

- **Effect Size > 0.5**: Moderate clinical improvement
- **Change > 5°**: Clinically meaningful difference
- **Power > 0.8**: Adequate statistical power for detection
- **Multiple Comparisons**: Adjust p-values when testing multiple features

---

## Common Analysis Patterns {#analysis-patterns}

### Quick Data Exploration

```python
def quick_dataset_summary(locomotion_data):
    """Generate quick summary statistics for any dataset"""
    
    summary = {
        'n_steps': locomotion_data.data.shape[0],
        'n_features': locomotion_data.data.shape[2],
        'tasks': list(locomotion_data.task_names),
        'subjects': len(set(locomotion_data.metadata['subject_id']))
    }
    
    # Key kinematic ranges
    knee_data = locomotion_data.get_feature_data('knee_flexion_angle_ipsi_rad')
    summary['knee_rom_deg'] = float(np.degrees(np.ptp(knee_data)))
    
    return summary

# Example usage
# summary = quick_dataset_summary(your_data)
# print(f"Dataset: {summary['n_steps']} steps, {summary['subjects']} subjects")
```

### Research Best Practices

<div class="best-practices" markdown>
:material-check-circle: **Analysis Checklist**

1. **Data Quality**: Check for missing values, outliers
2. **Statistical Assumptions**: Normality, independence
3. **Multiple Comparisons**: Adjust p-values appropriately  
4. **Effect Size**: Report Cohen's d or similar metrics
5. **Clinical Relevance**: Consider minimum detectable change
6. **Reproducibility**: Document analysis parameters
</div>

## Additional Resources {#resources}

- **Statistical Methods**: See [validation specifications](../../reference/standard_spec/validation_expectations_kinematic.md) for normal ranges
- **Plotting Functions**: Use [biomechanical showcase](../biomechanical_showcase.md) for visualization examples  
- **Data Loading**: Reference [getting started guide](../../getting_started/quick_start.md) for data import procedures
- **Feature Documentation**: Check [feature constants](https://github.com/your-repo/blob/main/lib/core/feature_constants.py) for available variables

---

*These case studies demonstrate common research workflows using standardized locomotion data. Adapt the code examples to your specific research questions and datasets.*