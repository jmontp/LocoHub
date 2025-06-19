# Basic Biomechanical Metrics

This tutorial covers fundamental biomechanical metrics calculation using LocomotionData. Learn to compute range of motion, peak values, symmetry indices, and phase-specific metrics commonly used in locomotion research.

## Prerequisites

- Basic Python knowledge
- Understanding of biomechanical variables (joint angles, moments)
- LocomotionData library installed

## Overview

The LocomotionData library provides built-in methods for calculating common biomechanical metrics:

1. **Range of Motion (ROM)** - Joint angle excursion during gait cycles
2. **Statistical Summaries** - Mean, std, min/max across cycles
3. **Peak Values and Timing** - Maximum/minimum values and their phase occurrence
4. **Symmetry Indices** - Bilateral comparisons between limbs
5. **Phase-Specific Metrics** - Values at key gait events

## Loading Test Data

```python
import numpy as np
import pandas as pd
from locomotion_analysis import LocomotionData

# Load phase-indexed data
loco = LocomotionData('your_dataset_phase.parquet')

# Get available subjects and tasks
subjects = loco.get_subjects()
tasks = loco.get_tasks()
features = loco.features  # All biomechanical variables

print(f"Dataset contains {len(subjects)} subjects, {len(tasks)} tasks")
print(f"Available features: {len(features)}")
```

## 1. Range of Motion (ROM) Calculations

ROM quantifies the total angular excursion of a joint during movement.

### Calculate ROM for Single Joint

```python
# Calculate knee ROM for all cycles
subject = subjects[0]
task = 'walking'

rom_data = loco.calculate_rom(
    subject, 
    task, 
    features=['knee_flexion_angle_ipsi_rad'],
    by_cycle=True  # Returns ROM per cycle
)

# Extract results
knee_rom = rom_data['knee_flexion_angle_ipsi_rad']
print(f"Knee ROM: {np.mean(knee_rom):.2f} ± {np.std(knee_rom):.2f} rad")
print(f"  In degrees: {np.rad2deg(np.mean(knee_rom)):.1f}°")
```

### Calculate ROM for Multiple Joints

```python
# Analyze ROM for all lower limb joints
joint_features = [
    'hip_flexion_angle_ipsi_rad',
    'knee_flexion_angle_ipsi_rad', 
    'ankle_flexion_angle_ipsi_rad'
]

rom_data = loco.calculate_rom(subject, task, features=joint_features)

# Display results
print("\nJoint ROM Summary:")
for joint, rom_values in rom_data.items():
    joint_name = joint.split('_')[0].capitalize()
    mean_rom = np.mean(rom_values)
    std_rom = np.std(rom_values)
    print(f"{joint_name}: {np.rad2deg(mean_rom):.1f} ± {np.rad2deg(std_rom):.1f}°")
```

### Overall vs Per-Cycle ROM

```python
# Per-cycle ROM (default)
rom_per_cycle = loco.calculate_rom(subject, task, 
                                   features=['knee_flexion_angle_ipsi_rad'],
                                   by_cycle=True)

# Overall ROM across all cycles
rom_overall = loco.calculate_rom(subject, task,
                                features=['knee_flexion_angle_ipsi_rad'], 
                                by_cycle=False)

print(f"ROM per cycle: {rom_per_cycle['knee_flexion_angle_ipsi_rad'].shape}")
print(f"ROM overall: {rom_overall['knee_flexion_angle_ipsi_rad']:.3f} rad")
```

## 2. Statistical Summaries

Get comprehensive statistics for biomechanical variables.

```python
# Get summary statistics
summary = loco.get_summary_statistics(
    subject, 
    task,
    features=['knee_flexion_angle_ipsi_rad', 'knee_flexion_moment_ipsi_Nm']
)

print("\nSummary Statistics:")
print(summary)
print(f"\nColumns: {summary.columns.tolist()}")
# Includes: mean, std, min, max, median, q25, q75
```

### Interpreting Summary Statistics

```python
# Extract specific metrics
for feature in summary.index:
    mean_val = summary.loc[feature, 'mean']
    std_val = summary.loc[feature, 'std']
    range_val = summary.loc[feature, 'max'] - summary.loc[feature, 'min']
    
    print(f"\n{feature}:")
    print(f"  Mean ± SD: {mean_val:.3f} ± {std_val:.3f}")
    print(f"  Range: {range_val:.3f}")
    print(f"  IQR: {summary.loc[feature, 'q75'] - summary.loc[feature, 'q25']:.3f}")
```

## 3. Peak Values and Timing

Identify maximum/minimum values and when they occur in the gait cycle.

```python
# Get cycle data
data_3d, feature_names = loco.get_cycles(
    subject, 
    task,
    features=['knee_flexion_angle_ipsi_rad']
)

if data_3d is not None:
    n_cycles, n_points, n_features = data_3d.shape
    phase = np.linspace(0, 100, n_points)
    
    # Analyze each cycle
    peak_values = []
    peak_phases = []
    
    for cycle in range(n_cycles):
        cycle_data = data_3d[cycle, :, 0]  # First feature
        
        # Find peak flexion
        peak_idx = np.argmax(cycle_data)
        peak_val = cycle_data[peak_idx]
        peak_phase = phase[peak_idx]
        
        peak_values.append(peak_val)
        peak_phases.append(peak_phase)
    
    print(f"\nPeak Knee Flexion Analysis:")
    print(f"  Mean peak: {np.rad2deg(np.mean(peak_values)):.1f}°")
    print(f"  Occurs at: {np.mean(peak_phases):.1f}% of gait cycle")
    print(f"  Timing variability: {np.std(peak_phases):.1f}%")
```

### Finding Multiple Peaks

```python
# Knee flexion often has two peaks in walking
from scipy.signal import find_peaks

mean_pattern = loco.get_mean_patterns(subject, task, 
                                     features=['knee_flexion_angle_ipsi_rad'])

if mean_pattern:
    knee_mean = mean_pattern['knee_flexion_angle_ipsi_rad']
    
    # Find peaks with minimum prominence
    peaks, properties = find_peaks(knee_mean, prominence=0.1)
    
    print(f"\nFound {len(peaks)} peaks in knee flexion:")
    for i, peak_idx in enumerate(peaks):
        peak_phase = (peak_idx / len(knee_mean)) * 100
        peak_value = knee_mean[peak_idx]
        print(f"  Peak {i+1}: {np.rad2deg(peak_value):.1f}° at {peak_phase:.1f}%")
```

## 4. Bilateral Symmetry Analysis

Compare ipsilateral and contralateral limb patterns.

```python
# Extract bilateral data
bilateral_features = [
    'knee_flexion_angle_ipsi_rad',
    'knee_flexion_angle_contra_rad'
]

mean_patterns = loco.get_mean_patterns(subject, task, features=bilateral_features)

if mean_patterns:
    ipsi_pattern = mean_patterns['knee_flexion_angle_ipsi_rad']
    contra_pattern = mean_patterns['knee_flexion_angle_contra_rad']
    
    # Calculate symmetry index (SI)
    # SI = 2 * |ipsi - contra| / (ipsi + contra) * 100
    si_values = 2 * np.abs(ipsi_pattern - contra_pattern) / (ipsi_pattern + contra_pattern) * 100
    mean_si = np.mean(si_values)
    
    print(f"\nKnee Symmetry Index: {mean_si:.1f}%")
    print(f"  <10% = Good symmetry")
    print(f"  10-20% = Mild asymmetry") 
    print(f"  >20% = Significant asymmetry")
```

### Cross-Correlation for Phase Shift

```python
# Analyze phase shift between limbs
from scipy.signal import correlate

# Normalize patterns
ipsi_norm = (ipsi_pattern - np.mean(ipsi_pattern)) / np.std(ipsi_pattern)
contra_norm = (contra_pattern - np.mean(contra_pattern)) / np.std(contra_pattern)

# Cross-correlation
correlation = correlate(ipsi_norm, contra_norm, mode='same')
lag = np.arange(-len(correlation)//2, len(correlation)//2)

# Find peak correlation
peak_corr_idx = np.argmax(correlation)
phase_shift = lag[peak_corr_idx] / len(ipsi_pattern) * 100

print(f"\nPhase shift between limbs: {phase_shift:.1f}% of cycle")
print(f"Expected ~50% for normal walking")
```

## 5. Phase-Specific Metrics

Extract values at key gait events.

```python
# Define key gait events (% of cycle)
gait_events = {
    'heel_strike': 0,
    'loading_response': 10,
    'midstance': 30,
    'terminal_stance': 50,
    'preswing': 60,
    'toe_off': 62,
    'midswing': 80,
    'terminal_swing': 95
}

# Get mean patterns
features_to_analyze = ['knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
mean_patterns = loco.get_mean_patterns(subject, task, features=features_to_analyze)

if mean_patterns:
    print("\nJoint Angles at Key Gait Events:")
    print("-" * 50)
    
    for event_name, event_phase in gait_events.items():
        # Find closest phase index
        phase_idx = int(event_phase / 100 * 150)  # 150 points per cycle
        
        print(f"\n{event_name.replace('_', ' ').title()} ({event_phase}%):")
        for feature in features_to_analyze:
            value = mean_patterns[feature][phase_idx]
            joint_name = feature.split('_')[0]
            print(f"  {joint_name}: {np.rad2deg(value):.1f}°")
```

## 6. Comprehensive Metrics Report

Create a complete biomechanical analysis report.

```python
def generate_metrics_report(loco, subject, task):
    """Generate comprehensive metrics report for a subject/task"""
    
    print(f"\n{'='*60}")
    print(f"BIOMECHANICAL METRICS REPORT")
    print(f"Subject: {subject} | Task: {task}")
    print(f"{'='*60}")
    
    # 1. Get cycle information
    data_3d, features = loco.get_cycles(subject, task)
    if data_3d is None:
        print("No data available")
        return
    
    n_cycles = data_3d.shape[0]
    print(f"\nData Summary: {n_cycles} gait cycles analyzed")
    
    # 2. ROM Analysis
    print(f"\n{'Range of Motion Analysis':^40}")
    print("-" * 40)
    
    kinematic_features = [f for f in features if 'angle' in f and 'ipsi' in f]
    rom_data = loco.calculate_rom(subject, task, features=kinematic_features)
    
    for feature, rom_values in rom_data.items():
        joint = feature.split('_')[0]
        mean_rom = np.rad2deg(np.mean(rom_values))
        std_rom = np.rad2deg(np.std(rom_values))
        print(f"{joint:>10}: {mean_rom:>6.1f} ± {std_rom:>4.1f}°")
    
    # 3. Peak Values
    print(f"\n{'Peak Values Analysis':^40}")
    print("-" * 40)
    
    for i, feature in enumerate(kinematic_features[:3]):  # First 3 joints
        feature_data = data_3d[:, :, i]
        peaks = np.max(feature_data, axis=1)
        joint = feature.split('_')[0]
        print(f"{joint:>10}: {np.rad2deg(np.mean(peaks)):>6.1f} ± {np.rad2deg(np.std(peaks)):>4.1f}°")
    
    # 4. Symmetry Analysis (if bilateral data available)
    ipsi_features = [f for f in features if 'ipsi' in f and 'angle' in f]
    contra_features = [f.replace('ipsi', 'contra') for f in ipsi_features if f.replace('ipsi', 'contra') in features]
    
    if contra_features:
        print(f"\n{'Bilateral Symmetry Analysis':^40}")
        print("-" * 40)
        
        mean_patterns = loco.get_mean_patterns(subject, task)
        for ipsi_feat in ipsi_features[:3]:
            contra_feat = ipsi_feat.replace('ipsi', 'contra')
            if contra_feat in mean_patterns:
                ipsi_data = mean_patterns[ipsi_feat]
                contra_data = mean_patterns[contra_feat]
                
                # Simple symmetry index
                si = np.mean(np.abs(ipsi_data - contra_data))
                joint = ipsi_feat.split('_')[0]
                print(f"{joint:>10}: {np.rad2deg(si):>6.2f}° mean difference")
    
    print(f"\n{'='*60}")

# Run the report
generate_metrics_report(loco, subjects[0], 'walking')
```

## Advanced Metrics Considerations

### Temporal Metrics

While this tutorial focuses on phase-normalized data, temporal metrics require time-indexed data:

```python
# Note: Requires time-indexed data
# Examples of temporal metrics:
# - Stride time
# - Cadence (steps/minute)
# - Walking speed
# - Stance/swing duration

print("\nTemporal Metrics Note:")
print("The current LocomotionData implementation focuses on phase-normalized")
print("data (150 points per cycle). For temporal metrics like stride time")
print("or cadence, use time-indexed datasets with the time_s column.")
```

### Joint Power and Work

```python
# Check if power data is available
power_features = [f for f in loco.features if 'power' in f]

if power_features:
    # Calculate work (integral of power)
    data_3d, features = loco.get_cycles(subject, task, features=power_features[:1])
    
    if data_3d is not None:
        # Approximate work using trapezoidal integration
        # Note: This is phase-normalized, not time-based
        power_data = data_3d[0, :, 0]  # First cycle
        work = np.trapz(power_data) / 150  # Normalize by points
        print(f"\nPhase-normalized work: {work:.2f} W·phase")
else:
    print("\nNo power data available in this dataset")
```

## Current Limitations

The LocomotionData library currently has some limitations for advanced metrics:

1. **Temporal Metrics**: The library is optimized for phase-indexed data. Calculating stride time, cadence, or walking speed requires additional time information not currently integrated.

2. **Joint Coordination**: Methods for calculating continuous relative phase or vector coding are not built-in.

3. **Energy Metrics**: Metabolic cost calculations or mechanical energy analysis require additional implementations.

4. **Clinical Scores**: Gait deviation indices or clinical assessment scores need custom implementations.

5. **Statistical Testing**: The library provides descriptive statistics but not hypothesis testing or group comparisons.

## Best Practices

1. **Always check data availability** before calculating metrics:
   ```python
   if data_3d is not None and data_3d.shape[0] > 0:
       # Calculate metrics
   ```

2. **Report variability** alongside mean values:
   ```python
   print(f"ROM: {mean:.1f} ± {std:.1f}°")
   ```

3. **Use appropriate units** (convert radians to degrees for angles):
   ```python
   angle_deg = np.rad2deg(angle_rad)
   ```

4. **Consider biomechanical context** when interpreting metrics
   - Normal ROM values vary by task and population
   - Asymmetry thresholds depend on clinical context

5. **Validate calculations** with known patterns
   - Knee flexion should have ~60-70° ROM in walking
   - Hip flexion peaks during swing phase

## Summary

This tutorial covered fundamental biomechanical metrics using LocomotionData:

- **ROM calculations** for joint excursion analysis
- **Statistical summaries** for data characterization  
- **Peak detection** for identifying key biomechanical events
- **Symmetry indices** for bilateral comparisons
- **Phase-specific values** for gait event analysis

The library provides efficient methods for these common calculations while maintaining a simple, intuitive API. For more advanced analyses, consider combining these basic metrics or implementing custom calculations using the extracted 3D data arrays.

## Next Steps

- Explore visualization methods to display metrics graphically
- Compare metrics across different tasks or conditions
- Implement custom metrics using the raw 3D data arrays
- Integrate with statistical packages for group comparisons