#!/usr/bin/env python3
"""
Compare performance between dictionary-based and 3D array-based plotting approaches.
"""

import numpy as np
import pandas as pd
import time
import argparse


POINTS_PER_CYCLE = 150


def old_approach_dict(df, subject, task, features, subject_col='subject', task_col='task'):
    """Original dictionary-based approach (current implementation)."""
    # Filter data
    mask = (df[subject_col] == subject) & (df[task_col] == task)
    subset = df[mask]
    
    if len(subset) == 0:
        return None
    
    n_cycles = len(subset) // POINTS_PER_CYCLE
    
    # Process each feature separately
    reshaped_data = {}
    for feature in features:
        if feature in subset.columns:
            feat_array = subset[feature].values
            reshaped_data[feature] = feat_array.reshape(n_cycles, POINTS_PER_CYCLE)
    
    return reshaped_data


def new_approach_3d(df, subject, task, features, subject_col='subject', task_col='task'):
    """New 3D array approach."""
    # Filter data
    mask = (df[subject_col] == subject) & (df[task_col] == task)
    subset = df[mask]
    
    if len(subset) == 0:
        return None, features
    
    n_cycles = len(subset) // POINTS_PER_CYCLE
    
    # Extract all features at once
    valid_features = [f for f in features if f in subset.columns]
    feature_data = subset[valid_features].values
    
    # Single reshape operation
    data_3d = feature_data.reshape(n_cycles, POINTS_PER_CYCLE, len(valid_features))
    
    return data_3d, valid_features


def compute_statistics_dict(reshaped_data):
    """Compute statistics using dictionary approach."""
    means = {}
    stds = {}
    correlations = {}
    
    # Calculate means and stds
    for feature, data in reshaped_data.items():
        means[feature] = np.mean(data, axis=0)
        stds[feature] = np.std(data, axis=0)
    
    # Calculate correlations between first two features
    if len(reshaped_data) >= 2:
        features = list(reshaped_data.keys())
        feat1_data = reshaped_data[features[0]]
        feat2_data = reshaped_data[features[1]]
        
        phase_corrs = []
        for phase in range(POINTS_PER_CYCLE):
            corr = np.corrcoef(feat1_data[:, phase], feat2_data[:, phase])[0, 1]
            phase_corrs.append(corr)
        correlations['phase_correlations'] = phase_corrs
    
    return means, stds, correlations


def compute_statistics_3d(data_3d, feature_names):
    """Compute statistics using 3D array approach."""
    # All statistics in single operations
    means = np.mean(data_3d, axis=0)  # (150, n_features)
    stds = np.std(data_3d, axis=0)    # (150, n_features)
    
    # Correlations between all features at each phase
    n_cycles, n_phases, n_features = data_3d.shape
    correlations = np.zeros((n_phases, n_features, n_features))
    
    for phase in range(n_phases):
        phase_data = data_3d[:, phase, :]  # (n_cycles, n_features)
        if n_cycles > 1:
            correlations[phase] = np.corrcoef(phase_data.T)
    
    return means, stds, correlations


def benchmark_approaches(df, n_iterations=10):
    """Benchmark both approaches."""
    # Test parameters
    subject = df['subject'].iloc[0]
    task = df['task'].iloc[0]
    features = ['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r',
                'hip_vel_s_r', 'knee_vel_s_r', 'ankle_vel_s_r',
                'hip_torque_s_r', 'knee_torque_s_r', 'ankle_torque_s_r']
    
    # Ensure we have the features
    available_features = [f for f in features if f in df.columns]
    print(f"Testing with {len(available_features)} features")
    
    # Benchmark dictionary approach
    dict_times = []
    for _ in range(n_iterations):
        start = time.time()
        
        # Reshape
        reshaped_dict = old_approach_dict(df, subject, task, available_features)
        
        # Compute statistics
        if reshaped_dict:
            means, stds, corrs = compute_statistics_dict(reshaped_dict)
        
        dict_times.append(time.time() - start)
    
    # Benchmark 3D array approach
    array_times = []
    for _ in range(n_iterations):
        start = time.time()
        
        # Reshape
        data_3d, valid_features = new_approach_3d(df, subject, task, available_features)
        
        # Compute statistics
        if data_3d is not None:
            means, stds, corrs = compute_statistics_3d(data_3d, valid_features)
        
        array_times.append(time.time() - start)
    
    # Results
    dict_mean = np.mean(dict_times) * 1000  # Convert to ms
    array_mean = np.mean(array_times) * 1000
    
    print(f"\nPerformance Comparison ({n_iterations} iterations):")
    print(f"Dictionary approach: {dict_mean:.2f}ms (±{np.std(dict_times)*1000:.2f}ms)")
    print(f"3D Array approach:   {array_mean:.2f}ms (±{np.std(array_times)*1000:.2f}ms)")
    print(f"Speedup: {dict_mean/array_mean:.2f}x")
    
    # Memory efficiency estimate
    n_cycles = len(df[(df['subject'] == subject) & (df['task'] == task)]) // POINTS_PER_CYCLE
    dict_memory = len(available_features) * n_cycles * POINTS_PER_CYCLE * 8  # 8 bytes per float64
    array_memory = n_cycles * POINTS_PER_CYCLE * len(available_features) * 8
    
    print(f"\nMemory usage (approximate):")
    print(f"Dictionary: {dict_memory/1024:.1f} KB (scattered)")
    print(f"3D Array:   {array_memory/1024:.1f} KB (contiguous)")
    
    # Test multi-subject processing
    print(f"\nMulti-subject processing test:")
    subjects = df['subject'].unique()[:5]  # Test with 5 subjects
    
    # Dictionary approach
    start = time.time()
    for subj in subjects:
        reshaped = old_approach_dict(df, subj, task, available_features)
    dict_multi_time = time.time() - start
    
    # 3D approach
    start = time.time()
    all_data = []
    for subj in subjects:
        data_3d, _ = new_approach_3d(df, subj, task, available_features)
        if data_3d is not None:
            all_data.append(data_3d)
    if all_data:
        # Stack into 4D array for batch processing
        # Check if all arrays have the same shape
        shapes = [d.shape for d in all_data]
        if len(set(shapes)) == 1:  # All shapes are the same
            all_data_4d = np.array(all_data)
            grand_mean = np.mean(all_data_4d, axis=(0, 1))
        else:
            # Handle different shapes by computing mean separately
            print(f"    Note: Different cycle counts across subjects: {shapes}")
    array_multi_time = time.time() - start
    
    print(f"Dictionary ({len(subjects)} subjects): {dict_multi_time*1000:.2f}ms")
    print(f"3D Array ({len(subjects)} subjects):   {array_multi_time*1000:.2f}ms")
    print(f"Speedup: {dict_multi_time/array_multi_time:.2f}x")


def main():
    parser = argparse.ArgumentParser(description='Compare plotting performance')
    parser.add_argument('--input_parquet', type=str, required=True)
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of iterations for benchmarking')
    
    args = parser.parse_args()
    
    print(f"Loading data from {args.input_parquet}...")
    df = pd.read_parquet(args.input_parquet)
    
    print(f"Data shape: {df.shape}")
    print(f"Subjects: {df['subject'].nunique()}")
    print(f"Tasks: {df['task'].nunique()}")
    
    benchmark_approaches(df, args.iterations)


if __name__ == '__main__':
    main()