# Contributor Tools Reference

Complete documentation for all tools available to dataset contributors.

## Overview

The project provides several specialized tools to help convert, validate, and tune biomechanical datasets:

| Tool | Purpose | Location |
|------|---------|----------|
| **conversion_generate_phase_dataset.py** | Convert time-indexed to phase-indexed data | Root directory |
| **create_dataset_validation_report.py** | Generate validation reports and plots | `contributor_tools/` |
| **interactive_validation_tuner.py** | GUI for tuning validation ranges | `contributor_tools/` |

---

## Phase Conversion Tool

### conversion_generate_phase_dataset.py

**Purpose**: Converts time-indexed biomechanical data to phase-indexed format with exactly 150 points per gait cycle.

**How it works**:
1. Detects gait cycles using heel strike events or periodic patterns
2. Normalizes each cycle to 150 evenly-spaced points
3. Creates `phase_percent` column (0-100% of gait cycle)
4. Preserves all biomechanical variables during resampling

**Usage**:
```bash
# Basic usage
python conversion_generate_phase_dataset.py converted_datasets/your_dataset_time.parquet

# With custom output name
python conversion_generate_phase_dataset.py input_time.parquet --output output_phase.parquet

# Specify gait event detection method
python conversion_generate_phase_dataset.py input_time.parquet --method heel_strike
```

**Parameters**:
- `input_file`: Path to time-indexed parquet file
- `--output`: (Optional) Custom output filename (default: replaces `_time` with `_phase`)
- `--method`: Cycle detection method (`heel_strike`, `periodic`, `auto`)
- `--min_cycle_points`: Minimum points per cycle for detection (default: 50)
- `--max_cycle_points`: Maximum points per cycle for detection (default: 200)

**Output**:
- Creates `your_dataset_phase.parquet` with:
  - Exactly 150 rows per gait cycle
  - `phase_percent` column: 0, 0.67, 1.34, ..., 99.33, 100
  - All original biomechanical variables preserved
  - `cycle_id` column for cycle identification

**Example Output Structure**:
```
subject_id | task          | cycle_id | phase_percent | knee_flexion_angle_ipsi_rad | ...
SUB01      | level_walking | 0        | 0.00          | 0.123                        | ...
SUB01      | level_walking | 0        | 0.67          | 0.125                        | ...
...        | ...           | ...      | ...           | ...                          | ...
SUB01      | level_walking | 0        | 100.00        | 0.122                        | ...
```

---

## Validation Report Generator

### create_dataset_validation_report.py

**Purpose**: Generates comprehensive validation reports showing how well your dataset conforms to biomechanical standards.

**How validation works**:
- **Phase-based checking**: Validates at specific gait cycle phases (default: 0%, 25%, 50%, 75%)
- **Box intersection**: Checks if values fall within min/max ranges at each phase
- **Visual feedback**: Green = passing all checks, Red = failing specific variables
- **No rigid pass/fail**: Focuses on identifying potential issues for review

**Usage**:
```bash
# Basic validation with default ranges
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet

# Use custom validation ranges
python contributor_tools/create_dataset_validation_report.py \
    --dataset your_dataset_phase.parquet \
    --ranges-file contributor_tools/validation_ranges/custom_ranges.yaml

# Generate validation plots
python contributor_tools/create_dataset_validation_report.py \
    --dataset your_dataset_phase.parquet \
    --generate-plots \
    --output-dir validation_results/
```

**Parameters**:
- `--dataset`: Path to phase-indexed parquet file to validate
- `--ranges-file`: Custom validation ranges YAML (default: `default_ranges.yaml`)
- `--generate-plots`: Create visual validation plots
- `--output-dir`: Directory for reports and plots (default: `validation_reports/`)
- `--tasks`: Specific tasks to validate (default: all)
- `--verbose`: Show detailed validation progress

**Output Files**:
1. **Markdown Report** (`dataset_validation_report.md`):
   - Summary statistics
   - Detailed violation listings
   - Suggestions for common issues

2. **Validation Plots** (if `--generate-plots`):
   - One plot per task showing all variables
   - Green backgrounds: passing ranges
   - Red highlights: failing strides
   - Separate plots for kinematics, kinetics, segments

**Understanding the Validation Process**:

The validation uses a simple box-checking approach at key phases:

```
Phase 0%:   [min_0 ─────────────── max_0]
            └─ Check if value at phase 0 is within this range

Phase 25%:  [min_25 ────────────── max_25]
            └─ Check if value at phase 25 is within this range

Phase 50%:  [min_50 ────────────── max_50]
            └─ Check if value at phase 50 is within this range

Phase 75%:  [min_75 ────────────── max_75]
            └─ Check if value at phase 75 is within this range
```

Each variable at each phase has its own acceptable range based on biomechanical norms.

---

## Interactive Validation Tuner

### interactive_validation_tuner.py

**Purpose**: GUI tool for visually tuning validation ranges by comparing passing and failing strides.

**Key Features**:
- **Side-by-side visualization**: See passing vs failing strides
- **Draggable validation boxes**: Adjust ranges with mouse
- **Real-time feedback**: Instantly see effects of changes
- **Multiple views**: Show globally passing, locally passing, or all strides
- **Unit conversion**: Toggle between radians and degrees
- **YAML export**: Save tuned ranges for use in validation

**Usage**:
```bash
# Launch GUI with dataset
python contributor_tools/interactive_validation_tuner.py

# The GUI will prompt for:
# 1. Dataset file (your_dataset_phase.parquet)
# 2. Validation ranges file (default_ranges.yaml or custom)
# 3. Task and variable to tune
```

**Interface Controls**:

1. **File Selection**:
   - Browse and select dataset file
   - Browse and select validation ranges
   - Auto-loads on startup if files exist

2. **Task/Variable Selection**:
   - Dropdown for available tasks
   - Dropdown for variables in selected task
   - Updates plot when selection changes

3. **Visualization Options**:
   - `Show Locally Passing`: Yellow lines for strides passing current variable only
   - `Show in Degrees`: Convert angular measurements for easier interpretation
   - Pass/Fail columns: Drag boxes to adjust validation ranges

4. **Saving Changes**:
   - `Save Ranges`: Exports tuned ranges to new YAML file
   - Preserves all other variables unchanged
   - Creates timestamped backup of original

**How to Use for Special Populations**:

1. Load your special population dataset
2. Start with default healthy ranges
3. For each variable showing many failures:
   - Visually inspect if failures are legitimate variations
   - Drag boxes to encompass normal variation
   - Save as `population_specific_ranges.yaml`

**Tips for Effective Tuning**:
- Start with kinematic variables (angles) - they're most intuitive
- Use "Show Locally Passing" to identify systematic shifts
- Toggle degrees view for angular variables
- Adjust one phase at a time
- Save incrementally with descriptive names

---

## Creating Custom Validation Ranges

### For Different Populations

Instead of forcing all data into healthy adult ranges, create population-specific validation:

**Option 1: Different Tasks for Different Populations**
```yaml
# In your conversion script, encode population in task name
tasks:
  level_walking_elderly:     # Elderly-specific ranges
    phases:
      '0':
        knee_flexion_angle_ipsi_rad:
          min: 0.1
          max: 0.8  # Reduced ROM expected
  
  level_walking_prosthetic:  # Prosthetic-specific ranges
    phases:
      '0':
        knee_flexion_angle_ipsi_rad:
          min: 0.0  # May have limited flexion
          max: 0.6
```

**Option 2: Separate Validation Files**
```bash
# Structure your validation ranges by population
contributor_tools/validation_ranges/
├── default_ranges.yaml           # Healthy adults
├── elderly_ranges.yaml           # Elderly population
├── prosthetic_ranges.yaml        # Prosthetic users
├── pediatric_ranges.yaml         # Children
└── pathological_ranges.yaml      # Clinical populations
```

**Option 3: Generate from Your Data**
```bash
# Let the data define its own normal ranges
python contributor_tools/automated_fine_tuning.py \
    --dataset special_population_phase.parquet \
    --method percentile_95 \
    --output special_population_ranges.yaml
```

### Understanding Phase-Based Validation

The validation system checks values at specific phases rather than the entire curve:

**Why Phase-Based?**
- Biomechanics vary throughout gait cycle
- Peak knee flexion at ~75% shouldn't apply at 0%
- Allows phase-specific acceptable ranges

**Default Check Points**:
- **0%**: Heel strike (initial contact)
- **25%**: Mid-stance
- **50%**: Toe-off (start of swing)
- **75%**: Mid-swing (peak knee flexion)

**Custom Phase Points**:
You can validate at any phase percentage:
```yaml
tasks:
  detailed_analysis:
    phases:
      '0':    # Heel strike
        knee_flexion_angle_ipsi_rad:
          min: -0.1
          max: 0.3
      '15':   # Loading response
        knee_flexion_angle_ipsi_rad:
          min: 0.2
          max: 0.5
      '33':   # Mid-stance
        knee_flexion_angle_ipsi_rad:
          min: -0.1
          max: 0.2
      '60':   # Initial swing
        knee_flexion_angle_ipsi_rad:
          min: 0.3
          max: 0.8
      '73':   # Peak flexion
        knee_flexion_angle_ipsi_rad:
          min: 0.9
          max: 1.4
```

---

## Troubleshooting Common Issues

### Phase Conversion Issues

**Problem**: "Cannot detect gait cycles"
```bash
# Try different detection methods
python conversion_generate_phase_dataset.py data.parquet --method periodic

# Adjust cycle detection parameters
python conversion_generate_phase_dataset.py data.parquet \
    --min_cycle_points 80 \
    --max_cycle_points 150
```

**Problem**: "Irregular cycle lengths"
- Check if data includes partial cycles at start/end
- Verify consistent sampling rate
- Consider manual cycle marking in your conversion script

### Validation Issues

**Problem**: "All strides failing at specific phase"
- Check for systematic offset in your data
- Verify unit conversions (degrees vs radians)
- Consider population-specific ranges

**Problem**: "Variable not found in validation ranges"
- Ensure variable names match exactly
- Check if variable is in the appropriate category (kinematic/kinetic)
- Add custom ranges for non-standard variables

### Interactive Tuner Issues

**Problem**: "GUI not responding to drags"
- Click on the box edge to start dragging
- Ensure dataset is loaded before adjusting
- Try restarting the tool

**Problem**: "Changes not saving"
- Use "Save Ranges" button before closing
- Check file permissions in output directory
- Verify YAML syntax if manually edited

---

## Best Practices

### When Converting Data
1. Start with a single subject to test your pipeline
2. Validate incrementally - don't wait until the end
3. Document any assumptions or special processing
4. Keep your original data unchanged

### When Validating
1. Use visualization to understand failures before adjusting ranges
2. Don't over-fit ranges to force validation passing
3. Document why you need custom ranges
4. Consider biological plausibility of your data

### When Tuning Ranges
1. Start with the most common task (usually level_walking)
2. Adjust ranges based on multiple subjects, not outliers
3. Be more conservative with kinetic variables
4. Save different range sets for different populations

---

## Getting Help

- **Examples**: See `contributor_tools/conversion_scripts/` for working implementations
- **Issues**: Open a GitHub issue with your validation report
- **Discussion**: Use GitHub Discussions for general questions
- **Direct Support**: Contact maintainers for complex cases

---

*These tools are designed to make dataset contribution as smooth as possible while maintaining high data quality standards.*