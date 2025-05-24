# PNG Export Feature for Mosaic Plotter

## Overview
The mosaic plotter now includes PNG export functionality to generate static images of the plots for validation and documentation purposes.

## Usage
```bash
python mozaic_plot.py --input_parquet data.parquet --export-png
```

## What Gets Exported
For each task in the dataset, the plotter exports two PNG files:

1. **`{task_name}_mean_std.png`** - Shows the mean trajectory with standard deviation bands
   - Black line: Mean trajectory across all gait cycles
   - Gray shaded area: ±1 standard deviation band
   - Useful for seeing average patterns and variability

2. **`{task_name}_individual_steps.png`** - Shows individual gait cycles as "spaghetti plot"
   - Each colored line: One complete gait cycle (150 points)
   - Different colors/styles for different cycles
   - Useful for seeing cycle-to-cycle variability and outliers

## Output Structure
```
plots/
├── level_walking.html
├── incline_walking.html
├── ...
└── png/
    ├── level_walking_mean_std.png
    ├── level_walking_individual_steps.png
    ├── incline_walking_mean_std.png
    ├── incline_walking_individual_steps.png
    └── ...
```

## Plot Layout
- **Rows**: One row per subject
- **Columns**: One column per biomechanical feature (e.g., hip_angle_s_r, knee_angle_s_r)
- **X-axis**: Gait cycle phase (0-100%)
- **Y-axis**: Feature value (auto-scaled)

## Requirements
- `plotly`: For generating the plots
- `kaleido`: For static image export (install with `pip install kaleido`)

## Expected Plot Appearance

### Mean + STD View
- Clean visualization showing average biomechanical patterns
- Standard deviation bands indicate normal variability
- Anomalies appear as deviations from the expected bands

### Individual Steps View  
- Multiple overlapping trajectories ("spaghetti")
- Consistent patterns indicate good data quality
- Outlier cycles are easily visible
- Should see 150 points per cycle as per standard

## Validation Checks
When reviewing exported PNGs, look for:

1. **Data Compliance**
   - Each subplot should show complete cycles (no truncated data)
   - Smooth trajectories without discontinuities
   
2. **Biomechanical Validity**
   - Hip angles: ~0.3-0.6 rad range for level walking
   - Knee angles: ~0.95-1.2 rad range for level walking  
   - Ankle angles: ~-0.3-0.25 rad range for level walking
   
3. **Consistency**
   - Similar patterns across subjects for same task
   - Reasonable variability between cycles
   - No extreme outliers or impossible values

## Troubleshooting
- If PNG export fails: Install kaleido (`pip install kaleido`)
- If plots are empty: Check data compliance with 150 points/cycle standard
- If values look wrong: Verify unit conversions (should be in radians)