# Validation Reference

Understanding how dataset validation works and how to ensure data quality.

## Setting Up Validation Ranges

Before you can validate your dataset, you need validation ranges that define acceptable biomechanical values for your population.

### Default Validation Ranges

The project includes default validation ranges for healthy adult populations:
```
contributor_tools/validation_ranges/default_ranges.yaml
```

These ranges were generated from the UMich 2021 dataset and cover standard locomotion tasks.

### When You Need Custom Ranges

You'll need custom validation ranges for:
- **Special populations**: Elderly, children, clinical populations
- **Pathological gait**: Neurological conditions, amputees, injury recovery
- **Novel activities**: Sports movements, rehabilitation exercises
- **Equipment constraints**: Exoskeletons, prosthetics, assistive devices
- **Different measurement systems**: Motion capture vs IMU-based systems

### Creating Custom Validation Ranges

#### Method 1: Generate from Your Data (Recommended)

Use the interactive validation tuner to generate ranges based on your dataset:

```bash
# Interactive visual tuning with real-time feedback
python contributor_tools/interactive_validation_tuner.py
# Then adjust ranges visually and save

# The interactive tuner provides visual feedback for setting ranges
# based on your actual data distribution
```

This creates a YAML file in `contributor_tools/validation_ranges/` with
all your tuned validation ranges for the dataset.

#### Method 2: Modify Existing Ranges

For populations similar to healthy adults:

1. Copy the default ranges:
   ```bash
   cp contributor_tools/validation_ranges/default_ranges.yaml \
      contributor_tools/validation_ranges/my_population_ranges.yaml
   ```

2. Adjust ranges based on your population's characteristics:
   ```yaml
   # Example: Elderly population might have reduced range of motion
   level_walking:
     phases:
       '25':
         knee_flexion_angle_ipsi_rad:
           min: 0.3    # Less flexion than young adults
           max: 1.0    # (default might be 0.5 to 1.2)
   ```

3. Use your custom file for validation:
   ```bash
   python contributor_tools/create_dataset_validation_report.py \
       --dataset your_dataset.parquet \
       --ranges-file contributor_tools/validation_ranges/my_population_ranges.yaml
   ```

#### Method 3: Manual Creation

For completely new activities or special requirements:

```yaml
# contributor_tools/validation_ranges/custom_activity_ranges.yaml
version: '1.0'
generated: '2024-01-15 10:30:00'
dataset: 'special_population_dataset'
method: 'expert_defined'
description: 'Validation ranges for wheelchair propulsion'

tasks:
  wheelchair_propulsion:
    phases:
      '0':    # Start of push phase
        shoulder_flexion_angle_ipsi_rad:
          min: -0.5
          max: 0.3
        elbow_flexion_angle_ipsi_rad:
          min: 1.2
          max: 2.0
      '50':   # Mid-push
        shoulder_flexion_angle_ipsi_rad:
          min: 0.5
          max: 1.5
        elbow_flexion_angle_ipsi_rad:
          min: 0.8
          max: 1.8
```

### YAML Structure Reference

```yaml
version: '1.0'                    # Format version
generated: 'YYYY-MM-DD HH:MM:SS'  # When created
dataset: 'dataset_name'           # Source dataset
method: 'method_used'             # How ranges were determined

tasks:
  task_name:                      # e.g., level_walking
    phases:
      '0':                        # Phase percentage (0, 25, 50, 75)
        variable_name:            # Standard variable name
          min: -0.5               # Minimum acceptable value
          max: 1.5                # Maximum acceptable value
```

### Using Custom Validation Ranges

Once you've created your custom ranges:

```bash
# Validate using custom ranges
python contributor_tools/create_dataset_validation_report.py \
    --dataset your_dataset_phase.parquet \
    --ranges-file contributor_tools/validation_ranges/your_custom_ranges.yaml
```

The validator will use your specified YAML file for validation.

## What Gets Validated?

The validation system checks three main aspects of your dataset:

### 1. Structure Validation
- **Phase indexing**: Exactly 150 points per gait cycle
- **Required columns**: `subject_id`, `task`, `phase_percent`
- **Data completeness**: No missing cycles or incomplete data

### 2. Variable Naming
- **Standard names**: Variables must use exact standard names
- **Units in names**: e.g., `_rad` for radians, `_Nm` for Newton-meters
- **Laterality markers**: `_ipsi` and `_contra` for sided measurements

### 3. Biomechanical Range Validation
- **Physiological ranges**: Values must be within human biomechanical limits
- **Phase-specific checks**: Different ranges at different points in gait cycle
- **Task-specific ranges**: Different expected ranges for walking vs stairs

## Running Validation

### Basic Command

```bash
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet
```

### What It Produces

1. **Validation Report** (Markdown file):
   - Overall pass rate
   - Detailed violation list
   - Suggestions for fixes

2. **Validation Plots** (Optional):
   - Visual representation of violations
   - Phase-specific range checks
   - Comparison with expected ranges

## Understanding Validation Results

### Pass Rate Calculation

```
Validation Score = (Passing Checks / Total Checks) × 100

Where:
- Total Checks = num_strides × num_variables × num_phases
- Passing Checks = Values within acceptable ranges
```

**Goal**: Identify and understand any systematic issues in your data

### Reading the Report

Example validation report structure:

```markdown
# Validation Report: your_dataset_phase

## Summary
- Phase Structure: Valid (150 points per cycle)
- Tasks Validated: 8/8
- Data Quality: Good (minimal violations)

## Violations by Task

### level_walking
- knee_flexion_angle_ipsi_rad: 3 violations at phase 75%
  - Expected: -0.5 to 0.8 rad
  - Found: -0.7 rad (2 occurrences)

### up_stairs
- No violations
```

## Common Validation Issues

### Issue 1: Wrong Variable Names

**Problem**: Variable names don't match standard exactly
```
❌ Found: knee_angle_left
✓ Expected: knee_flexion_angle_ipsi_rad
```

**Solution**: Use exact standard names in your conversion script:
```python
variable_mapping = {
    'knee_angle_left': 'knee_flexion_angle_ipsi_rad',
    'hip_angle_left': 'hip_flexion_angle_ipsi_rad',
}
data = data.rename(columns=variable_mapping)
```

### Issue 2: Wrong Units

**Problem**: Data in degrees instead of radians
```
❌ Knee angle value: 45.0 (likely degrees)
✓ Expected range: -0.5 to 1.5 (radians)
```

**Solution**: Convert units during processing:
```python
# Convert degrees to radians
data['knee_flexion_angle_ipsi_rad'] = np.deg2rad(data['knee_angle_degrees'])
```

### Issue 3: Phase Structure Issues

**Problem**: Not exactly 150 points per cycle
```
❌ Found: 100 points per cycle
✓ Required: 150 points per cycle
```

**Solution**: Use the phase conversion tool:
```bash
python conversion_generate_phase_dataset.py your_dataset_time.parquet
```

### Issue 4: Out-of-Range Values

**Problem**: Biomechanically impossible values
```
❌ Hip flexion: 3.5 rad (200 degrees) at phase 50%
✓ Expected: -0.5 to 2.0 rad
```

**Possible Causes & Solutions**:

1. **Sign convention error**:
   ```python
   # Flip sign if needed
   data['hip_flexion_angle_ipsi_rad'] = -data['hip_flexion_angle_ipsi_rad']
   ```

2. **Offset error**:
   ```python
   # Remove systematic offset
   data['hip_flexion_angle_ipsi_rad'] -= offset_value
   ```

3. **Outlier data points**:
   ```python
   # Filter extreme outliers (use cautiously)
   q99 = data['hip_flexion_angle_ipsi_rad'].quantile(0.99)
   q01 = data['hip_flexion_angle_ipsi_rad'].quantile(0.01)
   data = data[(data['hip_flexion_angle_ipsi_rad'] > q01) & 
               (data['hip_flexion_angle_ipsi_rad'] < q99)]
   ```

## Validation Ranges

### Kinematic Variables (Angles & Velocities)

Example ranges for knee flexion during level walking:

| Phase | Variable | Min (rad) | Max (rad) |
|-------|----------|-----------|-----------|
| 0%    | knee_flexion_angle_ipsi | -0.2 | 0.3 |
| 25%   | knee_flexion_angle_ipsi | 0.5 | 1.2 |
| 50%   | knee_flexion_angle_ipsi | -0.1 | 0.4 |
| 75%   | knee_flexion_angle_ipsi | 0.8 | 1.4 |

### Kinetic Variables (Forces & Moments)

Example ranges for hip moment during level walking:

| Phase | Variable | Min (Nm) | Max (Nm) |
|-------|----------|----------|----------|
| 0%    | hip_moment_ipsi | -50 | 100 |
| 25%   | hip_moment_ipsi | -75 | 125 |
| 50%   | hip_moment_ipsi | -100 | 80 |
| 75%   | hip_moment_ipsi | -60 | 120 |

## Advanced Validation Options

### Generate Validation Plots

```bash
python contributor_tools/create_dataset_validation_report.py \
    --dataset your_dataset_phase.parquet \
    --generate-plots
```

This creates visual plots showing:
- Your data distribution
- Expected ranges
- Violation points highlighted

### Custom Validation Ranges

If your dataset has special characteristics (e.g., pathological gait):

```python
# Contact maintainers to discuss custom validation ranges
# Document special characteristics in your dataset README
```

## Interpreting Results

### Minimal Violations

```
✓ Few scattered outliers
✓ Consistent patterns across subjects
✓ Biologically plausible values
→ Ready for contribution!
```

### Systematic Issues

```
⚠ Consistent violations at specific phases
⚠ Possible unit conversion issues
→ Review the specific variables flagged
→ Consider if custom ranges needed for your population
```

### Major Problems

```
❌ Widespread violations across variables
❌ Values outside biological limits
→ Check unit conversions (degrees vs radians)
→ Verify variable mappings
→ Review data processing pipeline
```

## Getting Help with Validation

1. **Check error messages carefully** - They indicate specific issues
2. **Review similar datasets** - See how they handle validation
3. **Use visualization** - Plot your data to spot issues
4. **Ask for help** - Open an issue with your validation report

## Tips for Success

1. **Start with a subset**: Validate one subject first
2. **Check units carefully**: Most failures are unit conversion issues
3. **Visualize your data**: Plot before validating to spot obvious issues
4. **Compare with reference**: Load `umich_2021_phase.parquet` as reference
5. **Document exceptions**: If your data has valid reasons for violations

---

**Remember**: The validation system ensures data quality and compatibility across the ecosystem. A thorough validation helps everyone use your data effectively.