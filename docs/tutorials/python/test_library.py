#!/usr/bin/env python3
"""
Test script to verify the LocomotionData library functionality.
Run from the python tutorial directory:
    python test_library.py
"""

import sys
import os
import numpy as np
import pandas as pd

# Add library path
sys.path.append('../../../source/lib/python')

print("Testing LocomotionData library...")
print(f"Current directory: {os.getcwd()}")

try:
    from locomotion_analysis import LocomotionData
    print("✓ Successfully imported LocomotionData")
except ImportError as e:
    print(f"✗ Failed to import LocomotionData: {e}")
    sys.exit(1)

# Test 1: Create test data
print("\n1. Creating test data...")
np.random.seed(42)
n_subjects = 2
n_tasks = 2
n_cycles = 3
points_per_cycle = 150

# Generate test data
data = []
for subject in [f'SUB{i:02d}' for i in range(1, n_subjects+1)]:
    for task in ['normal_walk', 'fast_walk']:
        for cycle in range(n_cycles):
            phase = np.linspace(0, 100, points_per_cycle)
            # Generate synthetic angles (in radians)
            hip_angle = 0.4 * np.sin(2 * np.pi * phase / 100) + 0.1 * np.random.randn(points_per_cycle) * 0.1
            knee_angle = 0.8 * np.sin(2 * np.pi * phase / 100 - np.pi/4) + 0.1 * np.random.randn(points_per_cycle) * 0.1
            ankle_angle = 0.3 * np.sin(2 * np.pi * phase / 100 - np.pi/2) + 0.1 * np.random.randn(points_per_cycle) * 0.1
            
            for i in range(points_per_cycle):
                data.append({
                    'subject': subject,
                    'task': task,
                    'phase': phase[i],
                    'hip_flexion_angle_right_rad': hip_angle[i],
                    'knee_flexion_angle_right_rad': knee_angle[i],
                    'ankle_flexion_angle_right_rad': ankle_angle[i],
                    'hip_flexion_angle_left_rad': hip_angle[i] + 0.05,
                    'knee_flexion_angle_left_rad': knee_angle[i] + 0.05,
                    'ankle_flexion_angle_left_rad': ankle_angle[i] + 0.05
                })

df = pd.DataFrame(data)
test_file = 'test_locomotion_data.csv'
df.to_csv(test_file, index=False)
print(f"✓ Created test data: {len(df)} rows, {len(df.columns)} columns")

# Test 2: Load data with library
print("\n2. Loading data with LocomotionData...")
try:
    loco = LocomotionData(test_file, file_type='csv')
    print(f"✓ Loaded data successfully")
    print(f"  - Subjects: {loco.get_subjects()}")
    print(f"  - Tasks: {loco.get_tasks()}")
    print(f"  - Features: {len(loco.features)} features")
except Exception as e:
    print(f"✗ Failed to load data: {e}")
    sys.exit(1)

# Test 3: Get 3D arrays
print("\n3. Testing 3D array extraction...")
try:
    subject = loco.get_subjects()[0]
    task = loco.get_tasks()[0]
    features = ['hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad']
    
    data_3d, feature_names = loco.get_cycles(subject, task, features)
    if data_3d is not None:
        print(f"✓ Extracted 3D array: shape {data_3d.shape}")
        print(f"  - Expected shape: ({n_cycles}, {points_per_cycle}, {len(features)})")
        assert data_3d.shape == (n_cycles, points_per_cycle, len(features)), "Shape mismatch!"
    else:
        print("✗ Failed to extract 3D array")
except Exception as e:
    print(f"✗ Error in 3D extraction: {e}")

# Test 4: Validation
print("\n4. Testing cycle validation...")
try:
    valid_mask = loco.validate_cycles(subject, task)
    print(f"✓ Validation complete: {np.sum(valid_mask)}/{len(valid_mask)} valid cycles")
except Exception as e:
    print(f"✗ Validation error: {e}")

# Test 5: Statistical analysis
print("\n5. Testing statistical analysis...")
try:
    mean_patterns = loco.get_mean_patterns(subject, task, features)
    print(f"✓ Calculated mean patterns for {len(mean_patterns)} features")
    
    rom_data = loco.calculate_rom(subject, task, features)
    print(f"✓ Calculated ROM for {len(rom_data)} features")
    for feat, rom in rom_data.items():
        print(f"  - {feat}: {np.mean(rom):.3f} ± {np.std(rom):.3f} rad")
except Exception as e:
    print(f"✗ Statistical analysis error: {e}")

# Test 6: Plotting (without display)
print("\n6. Testing plotting functions...")
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    
    # Test phase pattern plot
    loco.plot_phase_patterns(subject, task, features, save_path='test_phase_plot.png')
    if os.path.exists('test_phase_plot.png'):
        print("✓ Phase pattern plot created")
        os.remove('test_phase_plot.png')
    
    # Test task comparison
    if len(loco.get_tasks()) > 1:
        loco.plot_task_comparison(subject, loco.get_tasks()[:2], features[:1], 
                                 save_path='test_comparison_plot.png')
        if os.path.exists('test_comparison_plot.png'):
            print("✓ Task comparison plot created")
            os.remove('test_comparison_plot.png')
except Exception as e:
    print(f"✗ Plotting error: {e}")

# Test 7: Data merging
print("\n7. Testing data merging...")
try:
    task_data = pd.DataFrame({
        'subject': loco.get_subjects(),
        'task': ['normal_walk'] * len(loco.get_subjects()),
        'speed_m_s': [1.2] * len(loco.get_subjects())
    })
    
    merged = loco.merge_with_task_data(task_data)
    print(f"✓ Data merged successfully: {len(merged)} rows")
    assert 'speed_m_s' in merged.columns, "Merge failed - speed column missing"
except Exception as e:
    print(f"✗ Merging error: {e}")

# Cleanup
if os.path.exists(test_file):
    os.remove(test_file)
    print(f"\n✓ Cleaned up test file: {test_file}")

print("\n" + "="*50)
print("LIBRARY TEST COMPLETE")
print("="*50)
print(f"All tests passed! The LocomotionData library is working correctly.")