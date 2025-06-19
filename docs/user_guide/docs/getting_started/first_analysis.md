# Your First Biomechanical Analysis

This guide walks you through a complete biomechanical analysis workflow using the locomotion data standardization library. You'll learn how to load data, perform basic analysis, visualize findings, and interpret results.

## Prerequisites

- Python 3.8+
- Locomotion data standardization library installed
- Basic understanding of biomechanical variables

## Example Dataset

We'll use test datasets provided with the library:
- **Phase-indexed data**: `tests/test_locomotion_data.csv` or `tests/test_data/demo_clean_phase.parquet`
- **Content**: Phase-normalized gait data (150 points per cycle)
- **Variables**: Hip, knee, and ankle flexion angles (bilateral)

## Complete Analysis Workflow

### 1. Load and Explore Data

```python
from lib.core.locomotion_analysis import LocomotionData
import numpy as np
import pandas as pd

# Option 1: Load phase-indexed CSV data
loco = LocomotionData('tests/test_locomotion_data.csv')

# Option 2: Load phase-indexed parquet data (with custom phase column)
# loco = LocomotionData(
#     'tests/test_data/demo_clean_phase.parquet',
#     phase_col='phase_percent'  # This file uses 'phase_percent' not 'phase'
# )

# Option 3: For time-series data with custom columns
# loco = LocomotionData(
#     'tests/locomotion_data.csv',
#     subject_col='subject_id',
#     task_col='task_id'
# )

# Explore available subjects and tasks
subjects = loco.get_subjects()
tasks = loco.get_tasks()

print(f"Subjects in dataset: {subjects}")
print(f"Tasks performed: {tasks}")
print(f"Number of biomechanical variables: {len(loco.features)}")
```

### 2. Basic Data Quality Assessment

```python
# Select a subject and task for analysis
subject = 'SUB01'
task = 'normal_walk'

# Validate gait cycles
valid_mask = loco.validate_cycles(subject, task)
n_valid = np.sum(valid_mask)
n_total = len(valid_mask)

print(f"\nData Quality for {subject} - {task}:")
print(f"Valid cycles: {n_valid}/{n_total} ({100*n_valid/n_total:.1f}%)")

# Find outlier cycles
outlier_indices = loco.find_outlier_cycles(subject, task, threshold=2.0)
print(f"Outlier cycles detected: {len(outlier_indices)}")

if len(outlier_indices) > 0:
    print(f"Outlier cycle indices: {outlier_indices}")
```

### 3. Calculate Biomechanical Metrics

#### Range of Motion (ROM)

```python
# Calculate ROM for all joint angles
rom_data = loco.calculate_rom(subject, task, by_cycle=True)

# Display ROM statistics
print("\nRange of Motion Analysis:")
for feature, rom_values in rom_data.items():
    if 'angle' in feature:  # Focus on joint angles
        mean_rom = np.mean(rom_values)
        std_rom = np.std(rom_values)
        print(f"{feature}: {mean_rom:.3f} ± {std_rom:.3f} rad")
        print(f"  ({np.degrees(mean_rom):.1f} ± {np.degrees(std_rom):.1f} deg)")
```

#### Summary Statistics

```python
# Get comprehensive summary statistics
summary_stats = loco.get_summary_statistics(subject, task)

# Display key metrics for knee flexion
print("\nKnee Flexion Angle Statistics (bilateral):")
knee_features = [col for col in summary_stats.index if 'knee' in col and 'angle' in col]

for feature in knee_features:
    stats = summary_stats.loc[feature]
    print(f"\n{feature}:")
    print(f"  Mean: {stats['mean']:.3f} rad ({np.degrees(stats['mean']):.1f}°)")
    print(f"  Range: [{stats['min']:.3f}, {stats['max']:.3f}] rad")
    print(f"         [{np.degrees(stats['min']):.1f}°, {np.degrees(stats['max']):.1f}°]")
    print(f"  Std Dev: {stats['std']:.3f} rad ({np.degrees(stats['std']):.1f}°)")
```

### 4. Phase-Based Analysis

```python
# Get mean patterns across gait cycle
mean_patterns = loco.get_mean_patterns(subject, task)
std_patterns = loco.get_std_patterns(subject, task)

# Analyze phase-specific characteristics
print("\nPhase-Based Analysis:")

# The data has 150 points per gait cycle
# Key phases: 0% = heel strike, ~60% = toe-off, 100% = next heel strike

# Identify key gait events from knee angle
knee_angle_ipsi = mean_patterns.get('knee_flexion_angle_ipsi_rad', None)

if knee_angle_ipsi is not None:
    # Phase indices (150 points total)
    heel_strike_idx = 0  # 0% of gait cycle
    mid_stance_idx = 15  # ~10% of gait cycle
    toe_off_idx = 90     # ~60% of gait cycle
    mid_swing_idx = 120  # ~80% of gait cycle
    
    # Extract phase-specific values
    print(f"Knee flexion at key phases:")
    print(f"  Heel Strike (0%): {np.degrees(knee_angle_ipsi[heel_strike_idx]):.1f}°")
    print(f"  Mid Stance (10%): {np.degrees(knee_angle_ipsi[mid_stance_idx]):.1f}°")
    print(f"  Toe Off (60%): {np.degrees(knee_angle_ipsi[toe_off_idx]):.1f}°")
    print(f"  Mid Swing (80%): {np.degrees(knee_angle_ipsi[mid_swing_idx]):.1f}°")
    
    # Find peak knee flexion in swing
    swing_phase = knee_angle_ipsi[90:]  # 60-100% of cycle
    peak_flexion = np.max(swing_phase)
    peak_flexion_phase = 60 + (np.argmax(swing_phase) / 1.5)
    
    print(f"\nPeak knee flexion: {np.degrees(peak_flexion):.1f}° at {peak_flexion_phase:.1f}% of cycle")
```

### 5. Bilateral Comparison

```python
# Compare ipsilateral vs contralateral patterns
features_to_compare = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']

print("\nBilateral Symmetry Analysis:")
for base_feature in features_to_compare:
    ipsi_feature = f"{base_feature}_ipsi_rad"
    contra_feature = f"{base_feature}_contra_rad"
    
    if ipsi_feature in mean_patterns and contra_feature in mean_patterns:
        ipsi_pattern = mean_patterns[ipsi_feature]
        contra_pattern = mean_patterns[contra_feature]
        
        # Calculate symmetry index (normalized RMSE)
        rmse = np.sqrt(np.mean((ipsi_pattern - contra_pattern)**2))
        range_motion = np.max(ipsi_pattern) - np.min(ipsi_pattern)
        symmetry_index = 100 * (1 - rmse/range_motion)
        
        print(f"{base_feature}: {symmetry_index:.1f}% symmetric")
```

### 6. Visualization

```python
# Plot joint angle patterns
features_to_plot = [
    'knee_flexion_angle_ipsi_rad',
    'hip_flexion_angle_ipsi_rad',
    'ankle_flexion_angle_ipsi_rad'
]

# Create phase pattern plots (if matplotlib is available)
try:
    loco.plot_phase_patterns(
        subject, 
        task, 
        features_to_plot,
        plot_type='both',  # Show both individual cycles and mean
        save_path='first_analysis_patterns.png'
    )
    print("\nPhase pattern plot saved to 'first_analysis_patterns.png'")
except ImportError:
    print("\nMatplotlib not available for plotting. Install with: pip install matplotlib")
```

### 7. Clinical Interpretation

```python
# Analyze specific biomechanical parameters
print("\nClinical Interpretation Guidelines:")

# Check knee flexion ROM
knee_rom = rom_data.get('knee_flexion_angle_ipsi_rad', [])
if len(knee_rom) > 0:
    mean_knee_rom = np.degrees(np.mean(knee_rom))
    
    print(f"\nKnee Flexion ROM: {mean_knee_rom:.1f}°")
    if mean_knee_rom < 50:
        print("  → Below normal range (typically 60-70° for normal walking)")
        print("  → May indicate stiff knee gait or quadriceps weakness")
    elif mean_knee_rom > 80:
        print("  → Above normal range")
        print("  → May indicate excessive knee flexion or crouch gait")
    else:
        print("  → Within typical range for normal walking")

# Check for asymmetry
print("\nAsymmetry Assessment:")
if symmetry_index < 90:
    print(f"  → Significant asymmetry detected ({symmetry_index:.1f}%)")
    print("  → Consider further assessment for unilateral impairment")
else:
    print(f"  → Good bilateral symmetry ({symmetry_index:.1f}%)")
```

## Complete Example Script

Here's a complete script combining all analyses:

```python
#!/usr/bin/env python3
"""
First biomechanical analysis example
"""

from lib.core.locomotion_analysis import LocomotionData
import numpy as np

def main():
    # Load data
    loco = LocomotionData('tests/test_locomotion_data.csv')
    
    # Select subject and task
    subject = 'SUB01'
    task = 'normal_walk'
    
    print(f"Analyzing {subject} - {task}")
    print("="*50)
    
    # Data quality
    valid_mask = loco.validate_cycles(subject, task)
    print(f"\nData Quality: {np.sum(valid_mask)}/{len(valid_mask)} valid cycles")
    
    # ROM analysis
    rom_data = loco.calculate_rom(subject, task)
    knee_rom = rom_data.get('knee_flexion_angle_ipsi_rad', 0)
    if isinstance(knee_rom, np.ndarray):
        knee_rom = np.mean(knee_rom)
    print(f"\nKnee ROM: {np.degrees(knee_rom):.1f}°")
    
    # Summary statistics
    summary = loco.get_summary_statistics(subject, task)
    knee_stats = summary.loc['knee_flexion_angle_ipsi_rad']
    print(f"Knee angle range: [{np.degrees(knee_stats['min']):.1f}°, "
          f"{np.degrees(knee_stats['max']):.1f}°]")
    
    # Mean patterns
    mean_patterns = loco.get_mean_patterns(subject, task)
    print(f"\nComputed mean patterns for {len(mean_patterns)} variables")
    
    # Visualization (if available)
    try:
        loco.plot_phase_patterns(
            subject, task,
            ['knee_flexion_angle_ipsi_rad'],
            save_path='knee_analysis.png'
        )
        print("\nSaved knee angle plot to 'knee_analysis.png'")
    except:
        print("\nPlotting not available")
    
    print("\nAnalysis complete!")

if __name__ == '__main__':
    main()
```

## Next Steps

1. **Expand to Multiple Subjects**: Use loops to analyze entire cohorts
2. **Task Comparison**: Compare biomechanics across different walking conditions
3. **Advanced Statistics**: Implement SPM or other continuous analysis methods
4. **Custom Visualizations**: Create publication-ready figures
5. **Integration with Task Data**: Merge with external metadata for richer analyses

## Common Issues and Solutions

### Issue: No data found for subject/task
**Solution**: Check exact subject IDs and task names using `loco.get_subjects()` and `loco.get_tasks()`

### Issue: Variables not following standard naming
**Solution**: The library enforces standard naming convention. Ensure your data uses:
- Format: `<joint>_<motion>_<measurement>_<side>_<unit>`
- Example: `knee_flexion_angle_ipsi_rad`

### Issue: Invalid cycle detection
**Solution**: Review the validation criteria. Cycles are marked invalid if they contain:
- Angles outside ±180° (±π radians)
- Large discontinuities (>30° jumps)
- NaN or infinite values

## Current Limitations

The library currently provides:
- ✅ Basic statistical analysis (mean, std, ROM)
- ✅ Data quality assessment (validation, outlier detection)
- ✅ Phase-normalized analysis
- ✅ Basic visualization capabilities
- ✅ Multi-subject/task data handling

Not yet implemented:
- ❌ Automatic gait event detection
- ❌ Time-normalized analysis (only phase-normalized)
- ❌ Advanced statistical methods (SPM, PCA)
- ❌ Kinetic variable analysis helpers
- ❌ Direct clinical interpretation algorithms

## Summary

This guide demonstrated a complete biomechanical analysis workflow:
1. Loading standardized locomotion data
2. Assessing data quality
3. Calculating key biomechanical metrics
4. Performing phase-based analysis
5. Comparing bilateral patterns
6. Visualizing results
7. Interpreting findings clinically

The locomotion data standardization library provides the foundation for reproducible biomechanical research. While some advanced features are still in development, the core functionality enables meaningful gait analysis with minimal code.