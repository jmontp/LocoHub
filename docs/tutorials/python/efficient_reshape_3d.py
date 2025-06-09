#!/usr/bin/env python3
"""
Efficient Data Access Tutorial - 3D Array Implementation
Uses (num_cycles, num_phase_points, num_features) structure
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time


def efficient_reshape_3d(df, subject, task, features, points_per_cycle=150):
    """
    Efficiently reshape data into 3D array (num_cycles, num_phase_points, num_features).
    
    Args:
        df: DataFrame with phase-indexed data
        subject: Subject ID
        task: Task name
        features: List of feature column names
        points_per_cycle: Number of points per gait cycle (default 150)
    
    Returns:
        data_3d: 3D numpy array of shape (n_cycles, 150, n_features)
        feature_names: List of feature names (same order as last dimension)
    """
    # Filter for specific subject and task
    mask = (df['subject'] == subject) & (df['task'] == task)
    subset = df[mask]
    
    # Get number of cycles
    n_points = len(subset)
    n_cycles = n_points // points_per_cycle
    
    if n_points % points_per_cycle != 0:
        print(f"Warning: {n_points} points not divisible by {points_per_cycle}")
        return None, None
    
    # Extract features as 2D array first
    feature_data = subset[features].values  # Shape: (n_points, n_features)
    
    # Reshape to 3D
    # From (n_cycles * 150, n_features) to (n_cycles, 150, n_features)
    data_3d = feature_data.reshape(n_cycles, points_per_cycle, len(features))
    
    return data_3d, features


def demonstrate_3d_operations():
    """Demonstrate efficient operations with 3D array structure."""
    print("=" * 60)
    print("3D ARRAY OPERATIONS DEMONSTRATION")
    print("=" * 60)
    
    # Load data
    parquet_file = "source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet"
    df = pd.read_parquet(parquet_file)
    
    # Test parameters
    subject = df['subject'].iloc[0]
    task = 'normal_walk'
    features = ['knee_flexion_angle_contra_rad', 'hip_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad']
    
    # Get 3D array
    data_3d, feature_names = efficient_reshape_3d(df, subject, task, features)
    
    if data_3d is None:
        print("No data found")
        return
    
    print(f"\nData shape: {data_3d.shape}")
    print(f"  Cycles: {data_3d.shape[0]}")
    print(f"  Phase points: {data_3d.shape[1]}")
    print(f"  Features: {data_3d.shape[2]} ({', '.join(feature_names)})")
    
    # 1. Calculate mean across cycles for all features at once
    print("\n1. Mean patterns for all features:")
    mean_patterns = np.mean(data_3d, axis=0)  # Shape: (150, 3)
    for i, feat in enumerate(feature_names):
        print(f"   {feat}: mean={np.mean(mean_patterns[:, i]):.1f}°")
    
    # 2. Calculate range of motion for all cycles and features
    print("\n2. Range of Motion (ROM) analysis:")
    rom_all = np.max(data_3d, axis=1) - np.min(data_3d, axis=1)  # Shape: (n_cycles, 3)
    for i, feat in enumerate(feature_names):
        print(f"   {feat}: mean ROM={np.mean(rom_all[:, i]):.1f}°, std={np.std(rom_all[:, i]):.1f}°")
    
    # 3. Find peak timing for all cycles
    print("\n3. Peak timing analysis:")
    peak_indices = np.argmax(data_3d, axis=1)  # Shape: (n_cycles, 3)
    peak_phases = peak_indices / data_3d.shape[1] * 100
    for i, feat in enumerate(feature_names):
        print(f"   {feat}: mean peak at {np.mean(peak_phases[:, i]):.1f}% ± {np.std(peak_phases[:, i]):.1f}%")
    
    # 4. Cross-correlation between features
    print("\n4. Feature correlations at each phase point:")
    correlations = []
    for phase in range(data_3d.shape[1]):
        # Get all cycles at this phase point
        phase_data = data_3d[:, phase, :]  # Shape: (n_cycles, 3)
        # Calculate correlation between knee and hip
        corr = np.corrcoef(phase_data[:, 0], phase_data[:, 1])[0, 1]
        correlations.append(corr)
    
    max_corr_phase = np.argmax(correlations) / data_3d.shape[1] * 100
    print(f"   Max knee-hip correlation at {max_corr_phase:.1f}% of gait cycle")


def efficient_validation_3d(data_3d, feature_names):
    """
    Validate cycles using 3D array structure.
    
    Returns:
        valid_mask: Boolean array of shape (n_cycles,)
    """
    n_cycles = data_3d.shape[0]
    valid_mask = np.ones(n_cycles, dtype=bool)
    
    # Check each cycle
    for i in range(n_cycles):
        cycle_data = data_3d[i, :, :]  # Shape: (150, n_features)
        
        # Check for NaN or inf
        if np.any(~np.isfinite(cycle_data)):
            valid_mask[i] = False
            continue
        
        # Check for large jumps in any feature
        diffs = np.abs(np.diff(cycle_data, axis=0))  # Shape: (149, n_features)
        max_jumps = np.max(diffs, axis=0)  # Max jump per feature
        
        # Apply thresholds based on feature names
        for j, feat in enumerate(feature_names):
            if 'angle' in feat and max_jumps[j] > 30:  # 30° threshold
                valid_mask[i] = False
                break
    
    return valid_mask


def plot_with_3d_data(data_3d, feature_names, valid_mask=None):
    """Create plots using 3D array data."""
    phase_x = np.linspace(0, 100, data_3d.shape[1])
    
    fig, axes = plt.subplots(1, data_3d.shape[2], figsize=(15, 5))
    if data_3d.shape[2] == 1:
        axes = [axes]
    
    for i, (ax, feat) in enumerate(zip(axes, feature_names)):
        # Get feature data
        feature_data = data_3d[:, :, i]  # Shape: (n_cycles, 150)
        
        if valid_mask is not None:
            # Plot valid cycles
            valid_data = feature_data[valid_mask]
            invalid_data = feature_data[~valid_mask]
            
            # Plot invalid in red
            for cycle in invalid_data:
                ax.plot(phase_x, cycle, 'r-', alpha=0.3, linewidth=0.8)
            
            # Plot valid in gray
            for cycle in valid_data:
                ax.plot(phase_x, cycle, 'gray', alpha=0.3, linewidth=0.8)
            
            # Mean from valid only
            if len(valid_data) > 0:
                mean_curve = np.mean(valid_data, axis=0)
                ax.plot(phase_x, mean_curve, 'b-', linewidth=2, 
                       label=f'Mean (n={len(valid_data)})')
        else:
            # Plot all cycles
            for cycle in feature_data:
                ax.plot(phase_x, cycle, 'gray', alpha=0.3, linewidth=0.8)
            
            # Mean from all
            mean_curve = np.mean(feature_data, axis=0)
            ax.plot(phase_x, mean_curve, 'b-', linewidth=2, label='Mean')
        
        ax.set_xlabel('Gait Cycle (%)')
        ax.set_ylabel('Angle (deg)')
        ax.set_title(feat.replace('_', ' ').title())
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    plt.tight_layout()
    plt.show()


def batch_process_3d(df, task, features):
    """Process multiple subjects efficiently with 3D arrays."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING WITH 3D ARRAYS")
    print("=" * 60)
    
    subjects = df[df['task'] == task]['subject'].unique()
    print(f"\nProcessing {len(subjects)} subjects for task: {task}")
    
    # Collect all subject data
    all_means = []
    all_roms = []
    
    start_time = time.time()
    
    for subject in subjects:
        data_3d, _ = efficient_reshape_3d(df, subject, task, features)
        
        if data_3d is not None:
            # Calculate mean patterns
            mean_pattern = np.mean(data_3d, axis=0)  # (150, n_features)
            all_means.append(mean_pattern)
            
            # Calculate ROM
            rom = np.mean(np.max(data_3d, axis=1) - np.min(data_3d, axis=1), axis=0)
            all_roms.append(rom)
    
    process_time = time.time() - start_time
    
    # Convert to arrays
    all_means = np.array(all_means)  # (n_subjects, 150, n_features)
    all_roms = np.array(all_roms)    # (n_subjects, n_features)
    
    print(f"\nProcessed in {process_time:.2f} seconds")
    print(f"Mean patterns shape: {all_means.shape}")
    print(f"ROM values shape: {all_roms.shape}")
    
    # Calculate population statistics
    print("\nPopulation statistics:")
    for i, feat in enumerate(features):
        print(f"{feat}:")
        print(f"  Mean ROM across subjects: {np.mean(all_roms[:, i]):.1f}°")
        print(f"  ROM variability (std): {np.std(all_roms[:, i]):.1f}°")


def compare_methods():
    """Compare dictionary vs 3D array performance."""
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON: Dictionary vs 3D Array")
    print("=" * 60)
    
    # Load data
    df = pd.read_parquet("source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet")
    subject = df['subject'].iloc[0]
    task = 'normal_walk'
    features = ['knee_flexion_angle_contra_rad', 'hip_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad', 
                'knee_flexion_velocity_contra_rad_s', 'hip_flexion_velocity_contra_rad_s', 'ankle_flexion_velocity_contra_rad_s']
    
    # Method 1: Dictionary (original)
    start_time = time.time()
    mask = (df['subject'] == subject) & (df['task'] == task)
    subset = df[mask]
    dict_data = {}
    for feat in features:
        dict_data[feat] = subset[feat].values.reshape(-1, 150)
    
    # Calculate means
    dict_means = {feat: np.mean(data, axis=0) for feat, data in dict_data.items()}
    dict_time = time.time() - start_time
    
    # Method 2: 3D Array
    start_time = time.time()
    data_3d, _ = efficient_reshape_3d(df, subject, task, features)
    
    # Calculate means for all features at once
    array_means = np.mean(data_3d, axis=0)  # (150, 6)
    array_time = time.time() - start_time
    
    print(f"\nDictionary method: {dict_time*1000:.2f} ms")
    print(f"3D Array method: {array_time*1000:.2f} ms")
    print(f"Speedup: {dict_time/array_time:.1f}x")
    
    # Verify results are identical
    print("\nVerifying results match:")
    for i, feat in enumerate(features):
        dict_mean = dict_means[feat]
        array_mean = array_means[:, i]
        matches = np.allclose(dict_mean, array_mean)
        print(f"  {feat}: {'✓' if matches else '✗'}")


def advanced_3d_analysis():
    """Advanced analysis using 3D array operations."""
    print("\n" + "=" * 60)
    print("ADVANCED 3D ARRAY ANALYSIS")
    print("=" * 60)
    
    # Load data
    df = pd.read_parquet("source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet")
    subject = df['subject'].iloc[0]
    task = 'normal_walk'
    
    # Get angles and velocities
    angle_features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad']
    vel_features = ['hip_flexion_velocity_contra_rad_s', 'knee_flexion_velocity_contra_rad_s', 'ankle_flexion_velocity_contra_rad_s']
    
    angles_3d, _ = efficient_reshape_3d(df, subject, task, angle_features)
    vels_3d, _ = efficient_reshape_3d(df, subject, task, vel_features)
    
    if angles_3d is None or vels_3d is None:
        return
    
    print(f"\nAngles shape: {angles_3d.shape}")
    print(f"Velocities shape: {vels_3d.shape}")
    
    # 1. Joint coordination analysis
    print("\n1. Joint Coordination (angle-angle plots):")
    # Get knee vs hip angles for all cycles at once
    knee_angles = angles_3d[:, :, 1]  # (n_cycles, 150)
    hip_angles = angles_3d[:, :, 0]   # (n_cycles, 150)
    
    # Calculate phase-specific correlations
    phase_corrs = []
    for phase in range(angles_3d.shape[1]):
        corr = np.corrcoef(knee_angles[:, phase], hip_angles[:, phase])[0, 1]
        phase_corrs.append(corr)
    
    max_corr_idx = np.argmax(np.abs(phase_corrs))
    max_corr = phase_corrs[max_corr_idx]
    print(f"   Max knee-hip correlation: {max_corr:.3f} at {max_corr_idx/1.5:.1f}% gait")
    
    # 2. Power calculation (torque would be needed for real power)
    print("\n2. Pseudo-Power Analysis (angle × velocity):")
    # Element-wise multiplication of angles and velocities
    pseudo_power = angles_3d * vels_3d  # (n_cycles, 150, 3)
    
    # Mean power curves
    mean_power = np.mean(pseudo_power, axis=0)  # (150, 3)
    
    for i, joint in enumerate(['Hip', 'Knee', 'Ankle']):
        peak_power = np.max(np.abs(mean_power[:, i]))
        peak_phase = np.argmax(np.abs(mean_power[:, i])) / 1.5
        print(f"   {joint}: peak at {peak_phase:.1f}% ({peak_power:.0f} deg²/s)")
    
    # 3. Symmetry analysis (if we had both legs)
    print("\n3. Cycle-to-cycle consistency:")
    # Calculate coefficient of variation at each phase point
    cvs = np.std(angles_3d, axis=0) / (np.abs(np.mean(angles_3d, axis=0)) + 1e-6)
    mean_cvs = np.mean(cvs, axis=0)  # Mean CV for each joint
    
    for i, joint in enumerate(angle_features):
        print(f"   {joint}: CV = {mean_cvs[i]:.3f}")


def save_and_load_3d():
    """Demonstrate saving and loading 3D arrays efficiently."""
    print("\n" + "=" * 60)
    print("SAVING AND LOADING 3D ARRAYS")
    print("=" * 60)
    
    # Create example 3D data
    n_cycles, n_points, n_features = 100, 150, 6
    data_3d = np.random.randn(n_cycles, n_points, n_features) * 20
    feature_names = ['hip_angle', 'knee_angle', 'ankle_angle', 
                     'hip_vel', 'knee_vel', 'ankle_vel']
    
    # Save as NPZ (compressed numpy)
    np.savez_compressed('example_gait_data.npz', 
                       data=data_3d, 
                       features=feature_names,
                       subject='SUB01',
                       task='walk')
    
    # Load back
    loaded = np.load('example_gait_data.npz')
    loaded_data = loaded['data']
    loaded_features = loaded['features']
    
    print(f"Saved shape: {data_3d.shape}")
    print(f"Loaded shape: {loaded_data.shape}")
    print(f"File size: {os.path.getsize('example_gait_data.npz') / 1024:.1f} KB")
    
    # Clean up
    import os
    os.remove('example_gait_data.npz')


if __name__ == "__main__":
    # Run demonstrations
    demonstrate_3d_operations()
    compare_methods()
    batch_process_3d(
        pd.read_parquet("source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet"),
        'normal_walk',
        ['knee_flexion_angle_right_rad', 'hip_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad']
    )
    advanced_3d_analysis()
    # save_and_load_3d()  # Uncomment to test saving/loading