# Validation Ranges Directory

This directory contains YAML configuration files that define acceptable biomechanical ranges for dataset validation.

## Purpose

Validation ranges ensure that converted datasets contain physiologically plausible values. The validation system checks if biomechanical variables (joint angles, moments, forces) fall within expected ranges at specific phases of the gait cycle.

## Files

### Default Ranges

- **`validation_ranges.yaml`** - Consolidated validation ranges for healthy adult populations
  - Generated from UMich 2021 dataset
  - Covers standard locomotion tasks (walking, stairs, running)
  - Uses 95th percentile statistical method

### Custom Ranges (User-Created)

You can create custom range files for:
- Special populations (elderly, children, clinical)
- Novel activities (sports, rehabilitation)
- Equipment-specific constraints (prosthetics, exoskeletons)

## File Structure

All YAML files follow this structure:

```yaml
version: '1.0'
generated: 'YYYY-MM-DD HH:MM:SS'
dataset: 'source_dataset_name'
method: 'generation_method'
description: 'Optional description'

tasks:
  task_name:              # e.g., level_walking, up_stairs
    phases:
      'phase_percent':    # '0', '25', '50', or '75'
        variable_name:    # Standard biomechanical variable
          min: value      # Minimum acceptable value
          max: value      # Maximum acceptable value
```

## How Validation Works

1. The validator loads ranges from this directory
2. For each data point at phases 0%, 25%, 50%, 75% of the gait cycle
3. Checks if values fall within the specified min/max ranges
4. Reports violations and calculates pass rate
5. Target: ≥90% pass rate for acceptance

## Creating Custom Ranges

### Option 1: Generate from Your Data

```bash
# Automatically generate ranges from your dataset
python ../../contributor_tools/automated_fine_tuning.py \
    --dataset your_dataset_phase.parquet \
    --method percentile_95
```

This creates:
- `kinematic_ranges.yaml` - Joint angles and velocities
- `kinetic_ranges.yaml` - Forces and moments

### Option 2: Copy and Modify

```bash
# Start with default ranges
cp validation_ranges.yaml custom_population_ranges.yaml

# Edit ranges for your population
# e.g., reduce knee flexion range for elderly population
```

### Option 3: Create from Scratch

Use `example_custom_ranges.yaml` as a template for completely new activities.

## Using Custom Ranges

To validate with custom ranges:

```bash
python ../../contributor_tools/create_dataset_validation_report.py \
    --dataset your_dataset.parquet \
    --config-dir /path/to/this/directory/
```

## Standard Variables

Common variables that should be included:

### Kinematic (Angles in radians)
- `hip_flexion_angle_ipsi_rad`
- `hip_flexion_angle_contra_rad`
- `knee_flexion_angle_ipsi_rad`
- `knee_flexion_angle_contra_rad`
- `ankle_flexion_angle_ipsi_rad`
- `ankle_flexion_angle_contra_rad`

### Kinetic (Moments in Nm, Forces in N)
- `hip_flexion_moment_ipsi_Nm`
- `hip_adduction_moment_ipsi_Nm`
- `knee_flexion_moment_ipsi_Nm`
- `ankle_flexion_moment_ipsi_Nm`
- `grf_vertical_ipsi_N`

## Statistical Methods

When using `automated_fine_tuning.py`:

- **`percentile_95`** (Recommended): 2.5th to 97.5th percentiles
- **`mean_3std`**: Mean ± 3 standard deviations
- **`iqr_expansion`**: Q1-1.5×IQR to Q3+1.5×IQR
- **`percentile_90`**: 5th to 95th percentiles
- **`conservative`**: Min/max with 5% buffer

## Best Practices

1. **Start with existing data**: Generate ranges from your actual dataset
2. **Review generated ranges**: Check for biomechanical plausibility
3. **Document your choices**: Note why ranges were adjusted
4. **Test incrementally**: Validate a subset before full dataset
5. **Share your ranges**: Help others with similar populations

## Troubleshooting

### "No config file found"
- Ensure YAML files exist in this directory
- Check file permissions

### Low validation pass rate
- Review if your population needs custom ranges
- Check unit conversions (degrees vs radians)
- Consider using more conservative statistical method

### Ranges seem too restrictive
- Try `percentile_90` or `conservative` methods
- Manually adjust specific problematic ranges

## Contributing

If you create ranges for a new population or activity:
1. Document the population characteristics
2. Note any special considerations
3. Consider submitting as a reference for others

---

For more information, see the [Validation Reference](../../docs/contributing/validation_reference.md).