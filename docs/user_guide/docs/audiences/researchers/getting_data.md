# Getting Research Data

*Quick access to validated biomechanical datasets for immediate analysis*

## Download Validated Datasets

### Available Research Collections

**Georgia Tech 2023 Collection**
- **Tasks**: Level walking, incline/decline walking, stair climbing, running
- **Subjects**: 13 healthy adults  
- **Cycles**: 500+ validated gait cycles
- **Quality**: 100% validated with physiological range checks
- **Format**: Phase-indexed (150 points per cycle) and time-indexed

**University of Michigan 2021 Collection**  
- **Tasks**: Level, incline, and decline walking
- **Subjects**: 12 healthy adults
- **Cycles**: 600+ validated gait cycles  
- **Quality**: 100% validated with comprehensive quality checks
- **Format**: Phase-indexed (150 points per cycle) and time-indexed

### Quick Download

[**:material-download: Download All Datasets**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button .md-button--primary }

## Load Data in 3 Lines

=== "Python"

    ```python
    from locomotion_analysis import LocomotionData
    
    # Load Georgia Tech 2023 phase-indexed data
    data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
    
    # Access specific variable (3D array: subjects × cycles × phase_points)
    knee_angles = data.get_variable_3d('knee_flexion_angle_ipsi_rad')
    ```

=== "MATLAB"

    ```matlab
    % Load Georgia Tech 2023 phase-indexed data
    data = LocomotionData('gtech_2023_phase.parquet');
    
    % Access specific variable  
    knee_angles = data.get_variable('knee_flexion_angle_ipsi_rad');
    ```

## Research Workflow Examples

### Cross-Study Comparison
```python
# Load multiple datasets
gtech_data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
umich_data = LocomotionData.from_parquet('umich_2021_phase.parquet')

# Filter to same task
gtech_walking = gtech_data.filter_task('level_walking')
umich_walking = umich_data.filter_task('level_walking')

# Compare knee angles
gtech_knee = gtech_walking.get_average_trajectory('knee_flexion_angle_ipsi_rad')
umich_knee = umich_walking.get_average_trajectory('knee_flexion_angle_ipsi_rad')

# Plot comparison
import matplotlib.pyplot as plt
plt.plot(gtech_knee, label='Georgia Tech 2023')
plt.plot(umich_knee, label='University of Michigan 2021')
plt.legend()
plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion (rad)')
plt.title('Cross-Study Knee Angle Comparison')
```

### Publication-Ready Analysis
```python
# Load data and filter to research condition
data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
walking_data = data.filter_task('level_walking')

# Calculate statistics across all subjects and cycles
knee_mean = walking_data.get_average_trajectory('knee_flexion_angle_ipsi_rad')
knee_std = walking_data.get_std_trajectory('knee_flexion_angle_ipsi_rad')

# Create publication plot with confidence intervals
phase_percent = np.linspace(0, 100, 150)
plt.fill_between(phase_percent, knee_mean - knee_std, knee_mean + knee_std, 
                 alpha=0.3, label='±1 SD')
plt.plot(phase_percent, knee_mean, 'b-', linewidth=2, label='Mean')
plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion Angle (rad)')
plt.title('Knee Flexion During Level Walking (n=13 subjects)')
plt.legend()
plt.grid(True, alpha=0.3)
```

## Data Quality Assurance

### Validation Status
All datasets pass comprehensive quality checks:

- **Physiological Range Validation**: Joint angles within expected human ranges
- **Gait Pattern Validation**: Realistic gait cycle shapes and timing
- **Data Completeness**: No missing values or corrupted cycles
- **Cross-Variable Consistency**: Kinematic and kinetic data alignment
- **Temporal Consistency**: Phase indexing exactly 150 points per cycle

### Quality Reports
Each dataset includes detailed validation reports:
- Range validation plots for each joint and task
- Statistical summaries of all variables
- Outlier detection and filtering results
- Cross-validation with literature norms

## Troubleshooting Data Issues

### Common Solutions

**File Loading Issues**
```python
# Verify file exists and is readable
import os
assert os.path.exists('gtech_2023_phase.parquet'), "Dataset file not found"

# Check file integrity
data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
print(f"Loaded {data.n_subjects} subjects, {data.n_cycles} cycles")
```

**Memory Management for Large Datasets**
```python
# Load specific subjects only
data = LocomotionData.from_parquet('gtech_2023_phase.parquet', 
                                   subjects=['subject_01', 'subject_02'])

# Or filter immediately after loading
data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
walking_only = data.filter_task('level_walking')  # Reduces memory usage
```

**Variable Name Reference**
```python
# List all available variables
print(data.get_variable_names())

# Find specific variables
kinematic_vars = [var for var in data.get_variable_names() 
                  if 'angle' in var]
kinetic_vars = [var for var in data.get_variable_names() 
                if 'moment' in var or 'force' in var]
```

## Next Steps

- **[Quick Start Tutorial](../getting_started/quick_start/)** - Your first analysis in 10 minutes
- **[Analysis Workflows](../user_guides/researchers/analysis_workflows/)** - Research-specific examples  
- **[API Reference](../reference/api/python/)** - Complete function documentation
- **[Dataset Documentation](../reference/datasets_documentation/)** - Detailed variable descriptions

## Need Help?

- **[GitHub Issues](https://github.com/your-org/locomotion-data-standardization/issues)** - Bug reports and questions
- **[Community Forum](mailto:contact@locomotion-data-standardization.org)** - Connect with other researchers
- **[Technical Support](../user_guide/troubleshooting/)** - Common issues and solutions