# Understanding Validation Reports

Learn how to interpret and use validation reports to assess dataset quality and identify potential issues.

## What Are Validation Reports?

Validation reports provide comprehensive quality assessment for standardized locomotion datasets. They check:

- **Structural integrity**: Correct format and required columns
- **Biomechanical plausibility**: Realistic movement patterns and ranges
- **Data completeness**: Missing data and cycle consistency
- **Statistical quality**: Outlier detection and variability assessment

## Generating Validation Reports

### Python

```python
from locomotion_analysis import validate_dataset

# Generate comprehensive report
report = validate_dataset(
    filepath='gtech_2023_phase.parquet',
    generate_plots=True,
    output_dir='validation_output/',
    detailed=True
)

print(f"Overall Quality Score: {report['overall_score']:.2f}/5.0")
```

### MATLAB

```matlab
% Generate validation report
report = validate_locomotion_dataset('gtech_2023_phase.parquet', ...
    'generate_plots', true, ...
    'output_dir', 'validation_output/', ...
    'detailed', true);

fprintf('Overall Quality Score: %.2f/5.0\n', report.overall_score);
```

### Command Line

```bash
# Quick validation
python validate_dataset.py dataset.parquet

# Comprehensive validation with plots
python validate_dataset.py dataset.parquet --generate-plots --detailed
```

## Report Structure

### Summary Section

```json
{
  "dataset_info": {
    "name": "gtech_2023_phase",
    "subjects": 10,
    "tasks": 3,
    "total_cycles": 487,
    "file_size_mb": 15.2
  },
  "overall_score": 4.3,
  "validation_timestamp": "2024-01-15T10:30:00Z"
}
```

### Quality Scores

**Overall Score (0-5 scale)**:
- **5.0**: Excellent - Publication ready
- **4.0-4.9**: Good - Minor issues only
- **3.0-3.9**: Acceptable - Some quality concerns
- **2.0-2.9**: Poor - Significant issues
- **0-1.9**: Unacceptable - Major problems

**Component Scores**:
- **Structural Quality** (25%): Format compliance, required columns
- **Biomechanical Quality** (40%): Movement plausibility, ranges
- **Completeness Quality** (20%): Missing data, cycle integrity
- **Statistical Quality** (15%): Outliers, consistency

### Detailed Results

#### Structural Validation

```json
{
  "structural_validation": {
    "score": 5.0,
    "status": "PASS",
    "checks": {
      "required_columns": {
        "status": "PASS",
        "missing_columns": []
      },
      "phase_indexing": {
        "status": "PASS", 
        "complete_cycles": 487,
        "incomplete_cycles": 0,
        "points_per_cycle": 150
      },
      "data_types": {
        "status": "PASS",
        "incorrect_types": []
      }
    }
  }
}
```

#### Biomechanical Validation

```json
{
  "biomechanical_validation": {
    "score": 4.2,
    "status": "GOOD",
    "variables": {
      "knee_flexion_angle_ipsi_rad": {
        "score": 4.5,
        "range_check": "PASS",
        "plausibility_score": 0.92,
        "outlier_percentage": 1.2,
        "issues": []
      },
      "hip_flexion_angle_ipsi_rad": {
        "score": 3.8,
        "range_check": "WARNING",
        "plausibility_score": 0.85,
        "outlier_percentage": 3.1,
        "issues": [
          "5 cycles exceed expected hip flexion range (>90°)"
        ]
      }
    }
  }
}
```

#### Completeness Assessment

```json
{
  "completeness_assessment": {
    "score": 4.8,
    "status": "EXCELLENT",
    "missing_data_percentage": 0.2,
    "complete_cycles": 487,
    "partial_cycles": 0,
    "subject_coverage": {
      "SUB01": {"cycles": 52, "completeness": 1.0},
      "SUB02": {"cycles": 48, "completeness": 0.98}
    }
  }
}
```

## Understanding Validation Plots

Validation reports include several types of visualizations:

### 1. Range Validation Plots

![Range Validation Example](../assets/range_validation_example.png)

Shows data distribution against expected biomechanical ranges:

- **Green zones**: Normal/expected ranges
- **Yellow zones**: Caution ranges (unusual but possible)
- **Red zones**: Outlier ranges (likely errors)

**Interpretation**:
- Most data should fall in green zones
- <5% in yellow zones is acceptable
- Any data in red zones needs investigation

### 2. Phase Pattern Plots

![Phase Pattern Example](../assets/phase_pattern_example.png)

Displays average movement patterns across gait cycle:

- **Solid lines**: Mean patterns by task
- **Shaded areas**: ±1 standard deviation
- **Reference lines**: Literature-based normal ranges

**What to look for**:
- Smooth, physiologically reasonable curves
- Appropriate task differences
- Reasonable variability (not too tight or too loose)

### 3. Outlier Detection Plots

![Outlier Detection Example](../assets/outlier_detection_example.png)

Identifies potential data quality issues:

- **Box plots**: Show distribution quartiles
- **Individual points**: Outliers beyond whiskers
- **Color coding**: Severity of outliers

**Action items**:
- Investigate red outliers (likely errors)
- Review yellow outliers (possible but unusual)
- Document any retained outliers

### 4. Consistency Plots

![Consistency Example](../assets/consistency_example.png)

Assess within-subject and within-task consistency:

- **Coefficient of variation**: Lower is more consistent
- **Cycle-to-cycle correlation**: Higher indicates good repeatability
- **Subject variability**: Expected range of individual differences

## Interpreting Quality Scores

### Excellent Quality (4.5-5.0)

**Characteristics**:
- All structural checks pass
- <2% outliers, all within reasonable bounds
- Missing data <1%
- Smooth, physiologically plausible patterns
- Good within-subject consistency

**Actions**:
- ✅ Ready for publication and sharing
- Document any minor issues in metadata
- Consider as reference dataset for validation

### Good Quality (3.5-4.4)

**Characteristics**:
- Minor structural issues (easily fixable)
- 2-5% outliers, mostly in caution ranges
- Missing data 1-3%
- Generally plausible patterns with some variability
- Acceptable consistency

**Actions**:
- 🔧 Address identified issues before sharing
- Review and document outliers
- Consider filtering problematic cycles
- Suitable for most research applications

### Acceptable Quality (2.5-3.4)

**Characteristics**:
- Some structural issues requiring attention
- 5-10% outliers, some in error ranges  
- Missing data 3-7%
- Some biomechanically questionable patterns
- Higher than expected variability

**Actions**:
- 🚨 Significant revision needed
- Investigate root causes of quality issues
- May require additional data processing
- Consider contacting data contributors for clarification

### Poor Quality (<2.5)

**Characteristics**:
- Major structural problems
- >10% outliers or extreme values
- Missing data >7%
- Biomechanically implausible patterns
- Poor consistency

**Actions**:
- ❌ Not suitable for current sharing
- Requires substantial rework
- May need to return to raw data
- Consider exclusion from dataset collection

## Common Issues and Solutions

### Issue: High Outlier Percentage

**Symptoms**:
- Biomechanical score <3.0
- Many points in red outlier zones
- Unrealistic joint angle ranges

**Possible Causes**:
1. **Unit conversion errors** (degrees vs radians)
2. **Coordinate system inconsistencies**
3. **Marker dropout or tracking errors**
4. **Incorrect gait event detection**

**Solutions**:
```python
# Check units
import numpy as np
knee_deg = np.degrees(data['knee_flexion_angle_ipsi_rad'])
print(f"Knee range: {knee_deg.min():.1f}° to {knee_deg.max():.1f}°")

# Expected: roughly -10° to 120° for normal walking
if knee_deg.max() > 200:
    print("Values appear to be in wrong units")

# Check coordinate system
hip_deg = np.degrees(data['hip_flexion_angle_ipsi_rad'])
if hip_deg.mean() < 0:
    print("Hip angles may have wrong sign convention")
```

### Issue: Phase Indexing Errors

**Symptoms**:
- Structural score <3.0
- Incomplete cycle warnings
- Irregular phase progression

**Possible Causes**:
1. **Incorrect gait event detection**
2. **Missing heel strikes**
3. **Inconsistent interpolation**

**Solutions**:
```python
# Check phase indexing
cycle_lengths = data.groupby(['subject', 'task', 'step']).size()
print("Cycle length distribution:")
print(cycle_lengths.value_counts())

# Check phase values
phase_ranges = data.groupby(['subject', 'task', 'step'])['phase_percent'].agg(['min', 'max'])
print("Phase range issues:")
print(phase_ranges[(phase_ranges['min'] != 0) | (phase_ranges['max'] != 100)])
```

### Issue: High Missing Data

**Symptoms**:
- Completeness score <3.0
- Many NaN values
- Incomplete cycles

**Possible Causes**:
1. **Marker occlusion during capture**
2. **Equipment malfunctions**
3. **Incomplete trials**

**Solutions**:
```python
# Assess missing data patterns
missing_summary = data.isnull().sum()
print("Missing data by variable:")
print(missing_summary[missing_summary > 0])

# Check if missing data is systematic
missing_by_cycle = data.groupby(['subject', 'task', 'step']).apply(
    lambda x: x.isnull().sum().sum()
)
print("Cycles with missing data:")
print(missing_by_cycle[missing_by_cycle > 0])
```

## Using Validation Reports

### For Dataset Contributors

1. **Quality Assessment**: Determine if dataset meets sharing standards
2. **Issue Identification**: Find specific problems to address
3. **Documentation**: Record known limitations and quality metrics
4. **Improvement Tracking**: Monitor quality improvements over time

### For Data Users

1. **Dataset Selection**: Choose appropriate datasets for research needs
2. **Quality Awareness**: Understand limitations and potential biases
3. **Analysis Planning**: Account for data quality in statistical analysis
4. **Result Interpretation**: Consider quality when drawing conclusions

### For Validation Tuning

1. **Range Optimization**: Adjust validation ranges based on data patterns
2. **Threshold Setting**: Set appropriate quality thresholds for different use cases
3. **Method Validation**: Ensure validation methods detect real quality issues

## Best Practices

### Before Analysis

1. **Always review validation report** before using dataset
2. **Check quality scores** for variables you plan to analyze
3. **Review outlier plots** and consider filtering strategies
4. **Document quality decisions** in your analysis methods

### During Analysis

1. **Filter based on quality scores** if needed
2. **Account for missing data** in statistical models
3. **Report quality metrics** alongside results
4. **Consider quality as covariate** in complex analyses

### When Sharing Results

1. **Include validation summary** in methods section
2. **Report any quality-based exclusions**
3. **Acknowledge dataset limitations**
4. **Provide access to validation reports**

## Advanced Validation

### Custom Quality Criteria

```python
# Define custom validation criteria
custom_criteria = {
    'knee_flexion_strictness': 'high',
    'outlier_threshold': 2.5,  # standard deviations
    'missing_data_tolerance': 0.02,  # 2%
    'consistency_threshold': 0.15  # CV threshold
}

report = validate_dataset(
    'dataset.parquet',
    custom_criteria=custom_criteria
)
```

### Multi-Dataset Validation

```python
# Compare quality across datasets
datasets = ['gtech_2023_phase.parquet', 'umich_2021_phase.parquet']
comparison = compare_dataset_quality(datasets)

print("Quality comparison:")
print(comparison.summary_table)
```

### Longitudinal Quality Tracking

```python
# Track quality over time (for evolving datasets)
quality_history = track_dataset_quality(
    dataset_versions=['v1.0', 'v1.1', 'v1.2'],
    metrics=['overall_score', 'biomech_score', 'completeness']
)

plot_quality_trends(quality_history)
```

## Next Steps

- **[Working with Data](working_with_data/)** - Advanced analysis techniques
- **[Troubleshooting](troubleshooting/)** - Solutions for common problems
- **[Contributor Guide](../contributor_guide/)** - Improving dataset quality
- **[API Reference](../reference/api_reference/)** - Validation function details

---

*Validation reports are essential for ensuring data quality and research reproducibility. Always review and understand the quality assessment before using datasets for analysis.*