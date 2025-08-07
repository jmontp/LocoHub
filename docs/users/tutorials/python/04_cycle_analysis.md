# Tutorial 4: Cycle Analysis

## Overview

Learn to analyze individual gait cycles, calculate biomechanical metrics, and identify patterns and outliers in your data.

## Learning Objectives

- Extract and analyze individual gait cycles
- Calculate range of motion and peak values
- Perform bilateral comparisons
- Detect outlier cycles
- Extract cycle-by-cycle features for statistical analysis

## Setup

=== "Using Library"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Load data
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Filter for analysis
    subject_data = data.filter(subject='SUB01', task='level_walking')
    ```

=== "Using Raw Data"
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Load data
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    # Filter for analysis
    subject_data = data[(data['subject'] == 'SUB01') & 
                        (data['task'] == 'level_walking')]
    ```

## Extracting Individual Cycles

### Get All Cycles for Analysis

=== "Using Library"
    ```python
    # Extract cycles as 3D array
    cycles_3d, features = subject_data.get_cycles('SUB01', 'level_walking')
    
    # Shape: (n_cycles, n_phases, n_variables)
    print(f"Number of cycles: {cycles_3d.shape[0]}")
    print(f"Points per cycle: {cycles_3d.shape[1]}")  # Should be 150
    print(f"Number of variables: {cycles_3d.shape[2]}")
    
    # Access specific cycle
    cycle_1 = cycles_3d[0, :, :]  # First cycle, all phases, all variables
    ```

=== "Using Raw Data"
    ```python
    # Group by cycle and reshape
    cycles = []
    cycle_ids = subject_data['cycle_id'].unique()
    
    # Get variable columns (exclude metadata)
    var_cols = [col for col in subject_data.columns 
                if col not in ['subject', 'task', 'cycle_id', 'phase_percent']]
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        cycles.append(cycle_data[var_cols].values)
    
    cycles_3d = np.array(cycles)
    print(f"Number of cycles: {cycles_3d.shape[0]}")
    print(f"Points per cycle: {cycles_3d.shape[1]}")
    print(f"Number of variables: {cycles_3d.shape[2]}")
    ```

### Extract Specific Variables

=== "Using Library"
    ```python
    # Get specific variable across all cycles
    knee_cycles = subject_data.get_variable_cycles(
        'knee_flexion_angle_ipsi_rad',
        subject='SUB01',
        task='level_walking'
    )
    
    # Convert to degrees
    knee_cycles_deg = np.degrees(knee_cycles)
    
    # Shape: (n_cycles, n_phases)
    print(f"Knee data shape: {knee_cycles_deg.shape}")
    ```

=== "Using Raw Data"
    ```python
    # Extract knee flexion for all cycles
    knee_cycles = []
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        knee_values = cycle_data['knee_flexion_angle_ipsi_rad'].values
        knee_cycles.append(knee_values)
    
    knee_cycles = np.array(knee_cycles)
    knee_cycles_deg = np.degrees(knee_cycles)
    
    print(f"Knee data shape: {knee_cycles_deg.shape}")
    ```

## Calculating Cycle Metrics

### Range of Motion (ROM)

=== "Using Library"
    ```python
    # Calculate ROM for all variables
    rom_all = subject_data.calculate_rom('SUB01', 'level_walking')
    
    # Get specific joint ROM
    knee_rom = rom_all['knee_flexion_angle_ipsi_rad']
    print(f"Knee ROM: {np.degrees(knee_rom):.1f}°")
    
    # ROM per cycle
    rom_per_cycle = subject_data.calculate_rom_per_cycle(
        'SUB01', 'level_walking', 
        'knee_flexion_angle_ipsi_rad'
    )
    
    print(f"ROM mean: {np.degrees(np.mean(rom_per_cycle)):.1f}°")
    print(f"ROM std: {np.degrees(np.std(rom_per_cycle)):.1f}°")
    ```

=== "Using Raw Data"
    ```python
    # Calculate ROM for knee flexion
    rom_per_cycle = []
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        knee_values = cycle_data['knee_flexion_angle_ipsi_rad'].values
        rom = np.max(knee_values) - np.min(knee_values)
        rom_per_cycle.append(rom)
    
    rom_per_cycle = np.array(rom_per_cycle)
    
    print(f"Knee ROM: {np.degrees(np.mean(rom_per_cycle)):.1f}°")
    print(f"ROM mean: {np.degrees(np.mean(rom_per_cycle)):.1f}°")
    print(f"ROM std: {np.degrees(np.std(rom_per_cycle)):.1f}°")
    ```

### Peak Values and Timing

=== "Using Library"
    ```python
    # Get peak values and their timing
    peaks = subject_data.get_peak_values(
        'SUB01', 'level_walking',
        'knee_flexion_angle_ipsi_rad'
    )
    
    # For each cycle
    for i, peak_info in enumerate(peaks):
        print(f"Cycle {i+1}:")
        print(f"  Max: {np.degrees(peak_info['max_value']):.1f}° at {peak_info['max_phase']:.0f}% GC")
        print(f"  Min: {np.degrees(peak_info['min_value']):.1f}° at {peak_info['min_phase']:.0f}% GC")
    ```

=== "Using Raw Data"
    ```python
    # Calculate peak values and timing for each cycle
    peaks = []
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        knee_values = cycle_data['knee_flexion_angle_ipsi_rad'].values
        phase_values = cycle_data['phase_percent'].values
        
        max_idx = np.argmax(knee_values)
        min_idx = np.argmin(knee_values)
        
        peak_info = {
            'cycle_id': cycle_id,
            'max_value': knee_values[max_idx],
            'max_phase': phase_values[max_idx],
            'min_value': knee_values[min_idx],
            'min_phase': phase_values[min_idx]
        }
        peaks.append(peak_info)
    
    # Display results
    for i, peak_info in enumerate(peaks[:5]):  # Show first 5
        print(f"Cycle {peak_info['cycle_id']}:")
        print(f"  Max: {np.degrees(peak_info['max_value']):.1f}° at {peak_info['max_phase']:.0f}% GC")
        print(f"  Min: {np.degrees(peak_info['min_value']):.1f}° at {peak_info['min_phase']:.0f}% GC")
    ```

### Stride Characteristics

=== "Using Library"
    ```python
    # Calculate stride characteristics
    stride_features = subject_data.get_stride_features('SUB01', 'level_walking')
    
    # Display average values
    print(f"Stride time: {stride_features['stride_time_mean']:.3f} ± {stride_features['stride_time_std']:.3f} s")
    print(f"Cadence: {stride_features['cadence_mean']:.1f} ± {stride_features['cadence_std']:.1f} steps/min")
    print(f"Stance phase: {stride_features['stance_percent_mean']:.1f} ± {stride_features['stance_percent_std']:.1f}%")
    ```

=== "Using Raw Data"
    ```python
    # Estimate stride characteristics from data structure
    # Note: Actual timing requires time-indexed data
    n_cycles = len(cycle_ids)
    
    # Estimate stance phase (typically toe-off around 60% for normal walking)
    stance_percentages = []
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        # This is a simplified example - actual detection would use GRF or kinematics
        stance_percent = 60  # Placeholder
        stance_percentages.append(stance_percent)
    
    print(f"Number of cycles: {n_cycles}")
    print(f"Estimated stance phase: {np.mean(stance_percentages):.1f}%")
    ```

## Bilateral Comparisons

### Ipsilateral vs Contralateral

=== "Using Library"
    ```python
    # Compare bilateral variables
    bilateral = subject_data.compare_bilateral(
        'SUB01', 'level_walking',
        variable='knee_flexion_angle'  # Will compare _ipsi vs _contra
    )
    
    # Symmetry index
    print(f"Symmetry index: {bilateral['symmetry_index']:.2f}")
    print(f"Phase shift: {bilateral['phase_shift']:.1f}°")
    print(f"Correlation: {bilateral['correlation']:.3f}")
    
    # Plot comparison
    bilateral.plot_comparison()
    ```

=== "Using Raw Data"
    ```python
    # Compare ipsi vs contra knee flexion
    ipsi_values = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    contra_values = subject_data.groupby('phase_percent')['knee_flexion_angle_contra_rad'].mean()
    
    # Calculate symmetry index (multiple methods exist)
    # Method 1: Normalized difference
    symmetry_index = 200 * np.mean(np.abs(ipsi_values - contra_values) / 
                                   (ipsi_values + contra_values))
    
    # Correlation
    correlation = np.corrcoef(ipsi_values, contra_values)[0, 1]
    
    print(f"Symmetry index: {symmetry_index:.2f}")
    print(f"Correlation: {correlation:.3f}")
    
    # Plot comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    phase = ipsi_values.index
    ax.plot(phase, np.degrees(ipsi_values), 'b-', label='Ipsilateral', linewidth=2)
    ax.plot(phase, np.degrees(contra_values), 'r--', label='Contralateral', linewidth=2)
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Knee Flexion (degrees)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.show()
    ```

## Outlier Detection

### Statistical Outliers

=== "Using Library"
    ```python
    # Detect outlier cycles
    outliers = subject_data.detect_outliers(
        'SUB01', 'level_walking',
        method='zscore',  # or 'iqr', 'isolation_forest'
        threshold=3
    )
    
    print(f"Found {len(outliers['outlier_cycles'])} outlier cycles")
    print(f"Outlier cycle IDs: {outliers['outlier_cycles']}")
    
    # Get clean data without outliers
    clean_data = subject_data.remove_outliers(
        'SUB01', 'level_walking',
        outlier_cycles=outliers['outlier_cycles']
    )
    ```

=== "Using Raw Data"
    ```python
    # Detect outliers using z-score method
    from scipy import stats
    
    # Calculate z-scores for ROM
    rom_per_cycle = []
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        knee_values = cycle_data['knee_flexion_angle_ipsi_rad'].values
        rom = np.max(knee_values) - np.min(knee_values)
        rom_per_cycle.append(rom)
    
    rom_per_cycle = np.array(rom_per_cycle)
    z_scores = np.abs(stats.zscore(rom_per_cycle))
    
    # Identify outliers (z-score > 3)
    outlier_mask = z_scores > 3
    outlier_cycles = cycle_ids[outlier_mask]
    
    print(f"Found {len(outlier_cycles)} outlier cycles")
    print(f"Outlier cycle IDs: {outlier_cycles}")
    
    # Remove outliers
    clean_data = subject_data[~subject_data['cycle_id'].isin(outlier_cycles)]
    ```

### Visual Outlier Inspection

=== "Using Library"
    ```python
    # Visualize all cycles with outliers highlighted
    fig = subject_data.plot_cycles_with_outliers(
        'SUB01', 'level_walking',
        'knee_flexion_angle_ipsi_rad',
        outlier_cycles=outliers['outlier_cycles']
    )
    
    # Interactive outlier selection
    selected_outliers = subject_data.interactive_outlier_selection(
        'SUB01', 'level_walking',
        'knee_flexion_angle_ipsi_rad'
    )
    ```

=== "Using Raw Data"
    ```python
    # Plot all cycles with outliers highlighted
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot normal cycles in gray
    for cycle_id in cycle_ids:
        if cycle_id not in outlier_cycles:
            cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
            ax.plot(cycle_data['phase_percent'], 
                   np.degrees(cycle_data['knee_flexion_angle_ipsi_rad']),
                   'gray', alpha=0.3, linewidth=0.5)
    
    # Plot outlier cycles in red
    for cycle_id in outlier_cycles:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        ax.plot(cycle_data['phase_percent'],
               np.degrees(cycle_data['knee_flexion_angle_ipsi_rad']),
               'r-', alpha=0.7, linewidth=1)
    
    # Add mean curve
    mean_curve = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    ax.plot(mean_curve.index, np.degrees(mean_curve.values),
           'b-', linewidth=2, label='Mean')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Knee Flexion (degrees)')
    ax.set_title('Cycle Outlier Detection')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.show()
    ```

## Cycle-by-Cycle Features

### Extract Discrete Parameters

=== "Using Library"
    ```python
    # Extract comprehensive features for each cycle
    cycle_features = subject_data.extract_cycle_features(
        'SUB01', 'level_walking',
        features=['rom', 'peaks', 'timing', 'symmetry']
    )
    
    # Convert to DataFrame for analysis
    features_df = cycle_features.to_dataframe()
    
    # Display summary statistics
    print(features_df.describe())
    
    # Export for statistical software
    features_df.to_csv('cycle_features.csv', index=False)
    ```

=== "Using Raw Data"
    ```python
    # Extract multiple features per cycle
    features_list = []
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        
        # Knee flexion features
        knee_ipsi = cycle_data['knee_flexion_angle_ipsi_rad'].values
        knee_contra = cycle_data['knee_flexion_angle_contra_rad'].values
        
        # Hip flexion features
        hip_ipsi = cycle_data['hip_flexion_angle_ipsi_rad'].values
        
        features = {
            'cycle_id': cycle_id,
            'knee_rom_ipsi': np.max(knee_ipsi) - np.min(knee_ipsi),
            'knee_max_ipsi': np.max(knee_ipsi),
            'knee_min_ipsi': np.min(knee_ipsi),
            'knee_max_phase': cycle_data['phase_percent'].values[np.argmax(knee_ipsi)],
            'hip_rom_ipsi': np.max(hip_ipsi) - np.min(hip_ipsi),
            'hip_max_ipsi': np.max(hip_ipsi),
            'bilateral_knee_corr': np.corrcoef(knee_ipsi, knee_contra)[0, 1]
        }
        features_list.append(features)
    
    # Create DataFrame
    features_df = pd.DataFrame(features_list)
    
    # Convert radians to degrees for angular measurements
    angle_cols = [col for col in features_df.columns if 'rom' in col or 'max' in col or 'min' in col]
    for col in angle_cols:
        if 'phase' not in col:
            features_df[col] = np.degrees(features_df[col])
    
    # Display summary
    print(features_df.describe())
    
    # Export
    features_df.to_csv('cycle_features.csv', index=False)
    ```

### Feature Correlation Matrix

=== "Using Library"
    ```python
    # Create correlation matrix of cycle features
    correlation_matrix = cycle_features.compute_correlations()
    
    # Visualize correlations
    fig = cycle_features.plot_correlation_matrix(
        method='pearson',
        show_values=True,
        cmap='coolwarm'
    )
    
    # Find highly correlated features
    high_corr = cycle_features.find_correlated_features(threshold=0.7)
    print(f"Highly correlated feature pairs: {high_corr}")
    ```

=== "Using Raw Data"
    ```python
    import seaborn as sns
    
    # Compute correlation matrix
    correlation_matrix = features_df.corr()
    
    # Visualize
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, fmt='.2f', 
                cmap='coolwarm', center=0, 
                square=True, linewidths=1,
                cbar_kws={"shrink": 0.8})
    ax.set_title('Cycle Features Correlation Matrix')
    plt.tight_layout()
    plt.show()
    
    # Find highly correlated features
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            if abs(correlation_matrix.iloc[i, j]) > 0.7:
                high_corr_pairs.append(
                    (correlation_matrix.columns[i], 
                     correlation_matrix.columns[j],
                     correlation_matrix.iloc[i, j])
                )
    
    print("Highly correlated feature pairs:")
    for feat1, feat2, corr in high_corr_pairs:
        print(f"  {feat1} - {feat2}: {corr:.3f}")
    ```

## Quality Metrics

### Cycle Quality Assessment

=== "Using Library"
    ```python
    # Assess quality of each cycle
    quality_metrics = subject_data.assess_cycle_quality(
        'SUB01', 'level_walking',
        checks=['completeness', 'smoothness', 'consistency']
    )
    
    # Get high-quality cycles only
    good_cycles = quality_metrics.get_good_cycles(
        min_quality_score=0.8
    )
    
    print(f"High-quality cycles: {len(good_cycles)} out of {len(cycle_ids)}")
    
    # Quality report
    quality_metrics.generate_report('cycle_quality_report.pdf')
    ```

=== "Using Raw Data"
    ```python
    # Assess cycle quality
    quality_scores = []
    
    for cycle_id in cycle_ids:
        cycle_data = subject_data[subject_data['cycle_id'] == cycle_id]
        
        # Check completeness (no missing data)
        completeness = 1.0 - cycle_data.isna().any(axis=1).mean()
        
        # Check consistency (compare to mean pattern)
        knee_values = cycle_data['knee_flexion_angle_ipsi_rad'].values
        mean_pattern = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean().values
        consistency = np.corrcoef(knee_values, mean_pattern)[0, 1]
        
        # Combined quality score
        quality_score = (completeness + consistency) / 2
        
        quality_scores.append({
            'cycle_id': cycle_id,
            'completeness': completeness,
            'consistency': consistency,
            'quality_score': quality_score
        })
    
    quality_df = pd.DataFrame(quality_scores)
    
    # Filter high-quality cycles
    good_cycles = quality_df[quality_df['quality_score'] > 0.8]['cycle_id'].values
    
    print(f"High-quality cycles: {len(good_cycles)} out of {len(cycle_ids)}")
    print(f"Average quality score: {quality_df['quality_score'].mean():.3f}")
    ```

## Practice Exercises

### Exercise 1: Multi-Joint Analysis
Extract and compare ROM for hip, knee, and ankle across all cycles. Identify which joint shows the most variability.

### Exercise 2: Temporal Parameters
Calculate the timing of peak knee flexion for each cycle and analyze its variability. Is timing more consistent than magnitude?

### Exercise 3: Asymmetry Detection
Develop a comprehensive asymmetry score combining multiple bilateral variables. Which subjects show the highest asymmetry?

### Exercise 4: Feature Selection
From all extracted cycle features, identify the minimum set that explains 90% of the variance using PCA.

## Key Takeaways

1. **Cycle extraction** enables detailed analysis of gait patterns
2. **Multiple metrics** (ROM, peaks, timing) characterize each cycle
3. **Outlier detection** improves data quality and identifies abnormal patterns
4. **Bilateral comparisons** reveal asymmetries and coordination
5. **Feature extraction** prepares data for statistical analysis and machine learning

## Next Steps

[Continue to Tutorial 5: Group Analysis →](05_group_analysis.md)

Learn to aggregate data across subjects and perform group-level statistical comparisons.