# Mixed-Effects Modeling for Biomechanical Data

## Overview

The mixed-effects modeling system provides advanced statistical analysis capabilities specifically designed for hierarchical biomechanical data. This comprehensive framework integrates with both Python and R environments to deliver publication-ready analyses for gait research, intervention studies, and population comparisons.

## Key Features

### 🔬 **Research-Ready Templates**
- Gait analysis across walking conditions
- Pre/post intervention comparisons
- Group differences (healthy vs. pathological)
- Complex multi-factor experimental designs

### 📊 **Statistical Capabilities**
- Hierarchical modeling with lme4 integration
- Random effects optimization
- Automated model comparison and selection
- Comprehensive diagnostics and assumption checking
- Effect size calculations and interpretation

### 🎯 **Biomechanics-Specific Design**
- Phase-dependent gait cycle modeling
- Joint angle, moment, and force analysis
- Individual subject variability accounting
- Publication-ready visualization tools

## Installation Requirements

### Python Environment
```bash
# Install required packages
pip install rpy2 pandas numpy matplotlib seaborn

# Install R and required packages
# (See R setup section below)
```

### R Environment
```r
# Install required R packages
install.packages(c("lme4", "car", "performance"))

# Optional but recommended
install.packages(c("ggplot2", "dplyr", "tidyr"))
```

## Quick Start

### Basic Gait Analysis

```python
from locomotion_analysis import LocomotionData
from mixed_effects_models import MixedEffectsManager

# Load data
loco = LocomotionData('gait_data.parquet')

# Initialize mixed-effects manager
me_manager = MixedEffectsManager(loco)

# Fit gait analysis model
results = me_manager.templates.gait_analysis_model(
    outcome='knee_flexion_angle_ipsi_rad',
    tasks=['normal_walk', 'fast_walk', 'slow_walk'],
    include_phase=True
)

# View results
summary = me_manager.get_model_summary('gait_analysis')
print(f"Model converged: {summary['converged']}")
print(f"AIC: {summary['aic']:.2f}")
```

### Intervention Effect Analysis

```python
# Compare pre/post intervention
intervention_results = me_manager.templates.intervention_effect_model(
    outcome='knee_flexion_angle_ipsi_rad',
    pre_tasks=['baseline_walk'],
    post_tasks=['post_training_walk']
)

# Extract intervention effect
summary = me_manager.get_model_summary('intervention_effect')
intervention_effect = summary['fixed_effects']['interventionpost']
print(f"Intervention effect: {intervention_effect:.4f} radians")
```

## Core Components

### 1. MixedEffectsManager
Main interface for all mixed-effects modeling operations.

**Key Methods:**
- `prepare_data_for_modeling()` - Convert locomotion data to modeling format
- `fit_basic_hierarchical_model()` - Fit custom mixed-effects models
- `get_model_summary()` - Extract model results and interpretation

### 2. BiomechanicalModels
Pre-built templates for common biomechanical research questions.

**Available Templates:**
- `gait_analysis_model()` - Compare tasks across gait cycle
- `intervention_effect_model()` - Pre/post intervention analysis
- `subject_group_comparison_model()` - Between-group comparisons

### 3. ModelComparison
Automated model selection and validation tools.

**Key Methods:**
- `compare_models()` - Information criteria comparison
- `likelihood_ratio_test()` - Statistical model comparison

### 4. RandomEffectsOptimizer
Intelligent random effects structure recommendations.

**Key Methods:**
- `recommend_random_effects()` - Data-driven structure suggestions
- `test_random_effects_structures()` - Empirical structure comparison

### 5. DiagnosticsEngine
Comprehensive model validation and assumption checking.

**Key Methods:**
- `run_diagnostics()` - Full diagnostic suite
- `check_assumptions()` - Mixed-effects assumption validation

## Model Templates

### Gait Analysis Model

**Research Question:** How do joint kinematics vary across walking conditions throughout the gait cycle?

**Model Specification:**
```
Joint_Angle ~ Task + sin(phase) + cos(phase) + Task:sin(phase) + Task:cos(phase) + (sin(phase) + cos(phase) | Subject)
```

**Use Cases:**
- Comparing walking speeds (slow, normal, fast)
- Analyzing different locomotion tasks (level walking, stairs, slopes)
- Studying gait adaptations to external conditions

**Example:**
```python
results = me_manager.templates.gait_analysis_model(
    outcome='knee_flexion_angle_ipsi_rad',
    tasks=['normal_walk', 'fast_walk', 'stair_ascent'],
    include_phase=True
)
```

### Intervention Effect Model

**Research Question:** How does an intervention affect biomechanical patterns?

**Model Specification:**
```
Joint_Angle ~ Intervention + sin(phase) + cos(phase) + Intervention:sin(phase) + Intervention:cos(phase) + (Intervention + sin(phase) + cos(phase) | Subject)
```

**Use Cases:**
- Training program effectiveness
- Rehabilitation progress tracking
- Treatment outcome assessment
- Device/orthotic impact evaluation

**Example:**
```python
results = me_manager.templates.intervention_effect_model(
    outcome='hip_flexion_moment_ipsi_Nm',
    pre_tasks=['pre_training_walk'],
    post_tasks=['post_training_walk']
)
```

### Group Comparison Model

**Research Question:** How do biomechanical patterns differ between populations?

**Model Specification:**
```
Joint_Angle ~ Group + sin(phase) + cos(phase) + Group:sin(phase) + Group:cos(phase) + (sin(phase) + cos(phase) | Subject)
```

**Use Cases:**
- Healthy vs. pathological populations
- Age group comparisons
- Gender-based analysis
- Athletic vs. sedentary populations

**Example:**
```python
# Define group membership
group_info = {
    'SUB01': 'healthy', 'SUB02': 'healthy',
    'SUB03': 'pathological', 'SUB04': 'pathological'
}

results = me_manager.templates.subject_group_comparison_model(
    outcome='ankle_flexion_angle_ipsi_rad',
    group_info=group_info
)
```

## Random Effects Structure

### Recommendations System

The system automatically recommends appropriate random effects structures based on your data characteristics:

```python
recommendations = me_manager.optimizer.recommend_random_effects(
    outcome='knee_flexion_angle_ipsi_rad',
    predictors=['task_factor', 'phase_sin', 'phase_cos']
)

for rec in recommendations['recommendations']:
    print(f"{rec['structure']}: {rec['description']}")
```

### Common Structures

**Basic Random Intercept:**
```
(1 | subject)
```
- Use when: Limited data per subject
- Accounts for: Baseline differences between subjects

**Random Phase Effects:**
```
(phase_sin + phase_cos | subject)
```
- Use when: Sufficient gait cycle data
- Accounts for: Individual gait pattern differences

**Full Random Effects:**
```
(task_factor + phase_sin + phase_cos | subject)
```
- Use when: Rich dataset with multiple conditions
- Accounts for: Individual responses to all conditions

### Structure Testing

Empirically test multiple structures:

```python
structures = [
    "(1 | subject)",
    "(phase_sin + phase_cos | subject)",
    "(task_factor + phase_sin + phase_cos | subject)"
]

comparison = me_manager.optimizer.test_random_effects_structures(
    outcome='knee_flexion_angle_ipsi_rad',
    predictors=['task_factor', 'phase_sin', 'phase_cos'],
    structures=structures
)

print(comparison[['structure', 'aic', 'bic', 'converged']])
```

## Model Comparison and Selection

### Information Criteria Comparison

```python
# Fit multiple models
model1_results = me_manager.fit_basic_hierarchical_model(...)
model2_results = me_manager.fit_basic_hierarchical_model(...)

# Compare models
comparison = me_manager.comparison.compare_models(['model1', 'model2'])
print(comparison[['model', 'aic', 'bic', 'delta_aic']])
```

### Likelihood Ratio Tests

For nested models:

```python
lrt_result = me_manager.comparison.likelihood_ratio_test('simpler_model', 'complex_model')
print(f"Chi-square: {lrt_result['chi_square']:.3f}")
print(f"p-value: {lrt_result['p_value']:.3f}")
print(f"Interpretation: {lrt_result['interpretation']}")
```

## Model Diagnostics

### Comprehensive Diagnostics

```python
diagnostics = me_manager.diagnostics.run_diagnostics('model_name')

print("Residual Analysis:")
print(f"  Mean: {diagnostics['residuals']['mean']:.4f}")
print(f"  Std: {diagnostics['residuals']['std']:.4f}")

print(f"Model Convergence: {diagnostics['convergence']}")
print(f"Random Effects Available: {diagnostics['random_effects_available']}")
```

### Assumption Checking

```python
assumptions = me_manager.diagnostics.check_assumptions('model_name')

print("Assumption Assessment:")
for assumption, result in assumptions.items():
    print(f"  {assumption}: {result}")
```

## Interpretation and Reporting

### Fixed Effects Interpretation

```python
summary = me_manager.get_model_summary('model_name')

print("Fixed Effects:")
for effect, value in summary['fixed_effects'].items():
    print(f"  {effect}: {value:.4f}")
    
    # Interpret based on effect name
    if 'task' in effect:
        print(f"    Task effect of {abs(value):.3f} radians")
    elif 'phase' in effect:
        print(f"    Phase-dependent variation")
    elif 'intervention' in effect:
        direction = "increase" if value > 0 else "decrease"
        print(f"    Intervention causes {direction} of {abs(value):.3f} radians")
```

### Effect Size Calculation

```python
# Calculate standardized effect sizes
effect_sizes = calculate_effect_sizes(model_results)

print("Effect Size Interpretation:")
if abs(effect_sizes['main_effect']) < 0.1:
    print("  Small effect")
elif abs(effect_sizes['main_effect']) < 0.3:
    print("  Medium effect")
else:
    print("  Large effect")
```

### Clinical Significance

```python
# Example thresholds for knee flexion angle (radians)
SMALL_EFFECT = 0.087  # ~5 degrees
MEDIUM_EFFECT = 0.175  # ~10 degrees
LARGE_EFFECT = 0.349   # ~20 degrees

intervention_effect = summary['fixed_effects']['interventionpost']

if abs(intervention_effect) >= LARGE_EFFECT:
    significance = "clinically large"
elif abs(intervention_effect) >= MEDIUM_EFFECT:
    significance = "clinically moderate"
elif abs(intervention_effect) >= SMALL_EFFECT:
    significance = "clinically small"
else:
    significance = "clinically minimal"

print(f"Clinical significance: {significance}")
```

## Advanced Usage

### Custom Model Specification

```python
# Prepare custom data
data = me_manager.prepare_data_for_modeling(
    subjects=['SUB01', 'SUB02', 'SUB03'],
    tasks=['walking', 'running'],
    features=['knee_flexion_angle_ipsi_rad'],
    include_phase=True
)

# Add custom predictors
data['speed_category'] = data['task'].map({'walking': 'slow', 'running': 'fast'})
data['speed_factor'] = data['speed_category'].astype('category')

# Fit custom model
results = me_manager.fit_basic_hierarchical_model(
    outcome='knee_flexion_angle_ipsi_rad',
    predictors=['speed_factor', 'phase_sin', 'phase_cos', 'speed_factor:phase_sin'],
    random_effects='(phase_sin + phase_cos | subject)',
    data=data,
    model_name='custom_speed_model'
)
```

### Batch Processing

```python
# Analyze multiple outcomes
outcomes = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
results_dict = {}

for outcome in outcomes:
    results_dict[outcome] = me_manager.templates.gait_analysis_model(
        outcome=outcome,
        tasks=['normal_walk', 'fast_walk'],
        model_name=f'gait_{outcome}'
    )

# Compare across outcomes
for outcome, results in results_dict.items():
    print(f"{outcome}: AIC = {results['aic']:.2f}, Converged = {results['converged']}")
```

## Troubleshooting

### Common Issues

**Model Convergence Failures:**
```python
# Check data characteristics
recommendations = me_manager.optimizer.recommend_random_effects(outcome, predictors)
print(f"Subjects: {recommendations['data_summary']['n_subjects']}")
print(f"Obs per subject: {recommendations['data_summary']['mean_obs_per_subject']:.1f}")

# Try simpler random effects structure
if recommendations['data_summary']['mean_obs_per_subject'] < 20:
    random_effects = "(1 | subject)"  # Simplify
```

**Insufficient Data:**
```python
# Check data availability
data = me_manager.prepare_data_for_modeling()
print(f"Total observations: {len(data)}")
print(f"Subjects: {data['subject'].nunique()}")
print(f"Tasks: {data['task'].nunique()}")

# Recommend minimum data requirements
min_subjects = 10
min_obs_per_subject = 15
if data['subject'].nunique() < min_subjects:
    print(f"Warning: Consider collecting data from at least {min_subjects} subjects")
```

**R Integration Issues:**
```python
# Check R availability
from mixed_effects_models import R_AVAILABLE, LME4_AVAILABLE

if not R_AVAILABLE:
    print("Install rpy2: pip install rpy2")
    print("Install R: https://cran.r-project.org/")

if not LME4_AVAILABLE:
    print("Install lme4 in R: install.packages('lme4')")
```

## Best Practices

### Data Requirements
- **Minimum subjects:** 8-10 for basic models, 15+ for complex random effects
- **Observations per subject:** 10+ for random slopes, 30+ for complex structures
- **Data quality:** Ensure proper phase indexing and consistent task naming

### Model Selection Strategy
1. Start with random intercept models
2. Add random slopes based on data characteristics
3. Use information criteria for comparison
4. Validate with likelihood ratio tests
5. Check assumptions and convergence

### Reporting Guidelines
1. Report model specifications clearly
2. Include convergence status and diagnostics
3. Present effect sizes with confidence intervals
4. Discuss clinical/practical significance
5. Acknowledge model limitations

## Integration with Publication Workflows

### Results Export

```python
# Export model summary
summary = me_manager.get_model_summary('model_name')
pd.DataFrame([summary]).to_csv('model_summary.csv')

# Export comparison table
comparison = me_manager.comparison.compare_models(['model1', 'model2'])
comparison.to_csv('model_comparison.csv', index=False)
```

### Visualization Integration

The mixed-effects system integrates with the existing LocomotionData visualization tools:

```python
# Plot model predictions vs. observations
# (Integration with existing plotting methods)
loco.plot_phase_patterns(subject='SUB01', task='normal_walk', 
                        features=['knee_flexion_angle_ipsi_rad'])
```

## Future Enhancements

Planned additions to the mixed-effects modeling system:

- **Cross-validation frameworks** for model validation
- **Bayesian mixed-effects models** for uncertainty quantification
- **Time series extensions** for longitudinal gait analysis
- **Machine learning integration** for automated feature selection
- **Interactive visualization tools** for model exploration

---

*This documentation provides comprehensive guidance for using mixed-effects models in biomechanical research. For specific research questions or advanced applications, consult with a statistician familiar with hierarchical modeling.*