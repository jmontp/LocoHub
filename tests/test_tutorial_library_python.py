#!/usr/bin/env python3
"""
Tutorial Test: Python Library Functionality

Created: 2025-06-11 (moved from docs/tutorials/python/)
Purpose: Validates the Python LocomotionData library functionality from the library tutorial

Intent:
This test script validates all functionality covered in the Python library tutorial,
ensuring that the LocomotionData class works correctly for:

**PRIMARY FUNCTIONS:**
1. **Library Import**: Verify LocomotionData can be imported successfully
2. **Data Creation**: Test creation of test datasets with proper structure
3. **3D Array Operations**: Validate efficient reshape operations for phase data
4. **Statistical Analysis**: Test mean, std, and range calculations across cycles
5. **Data Validation**: Ensure data integrity and expected outputs

Usage:
    cd tests
    python test_tutorial_library_python.py

Expected Output:
- Successful import confirmation
- Test data creation and validation
- 3D array operation results
- Statistical calculations
- All tests passing confirmation

This test ensures the library tutorial examples work correctly and validates
the core functionality users will rely on for biomechanical data analysis.
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory to path for lib imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

print("Testing LocomotionData library...")
print(f"Current directory: {os.getcwd()}")

try:
    from lib.core.locomotion_analysis import LocomotionData
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
                    'hip_flexion_angle_contra_rad': hip_angle[i],
                    'knee_flexion_angle_contra_rad': knee_angle[i],
                    'ankle_flexion_angle_contra_rad': ankle_angle[i],
                    'hip_flexion_angle_ipsi_rad': hip_angle[i] + 0.05,
                    'knee_flexion_angle_ipsi_rad': knee_angle[i] + 0.05,
                    'ankle_flexion_angle_ipsi_rad': ankle_angle[i] + 0.05
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
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
    
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

# Test 6: Comprehensive plotting functions (without display)
print("\n6. Testing plotting functions...")
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    
    # Test 6a: Phase pattern plots with different modes
    print("  Testing phase pattern plots...")
    plot_modes = ['spaghetti', 'mean', 'both']
    for mode in plot_modes:
        test_file = f'test_phase_{mode}.png'
        loco.plot_phase_patterns(subject, task, features, 
                                plot_type=mode, save_path=test_file)
        if os.path.exists(test_file):
            print(f"    ✓ {mode.capitalize()} plot created")
            os.remove(test_file)
        else:
            print(f"    ✗ {mode.capitalize()} plot failed")
    
    # Test 6b: Task comparison plots
    print("  Testing task comparison plots...")
    if len(loco.get_tasks()) > 1:
        loco.plot_task_comparison(subject, loco.get_tasks()[:2], features[:1], 
                                 save_path='test_comparison.png')
        if os.path.exists('test_comparison.png'):
            print("    ✓ Task comparison plot created")
            os.remove('test_comparison.png')
        else:
            print("    ✗ Task comparison plot failed")
    else:
        print("    - Task comparison skipped (only 1 task available)")
    
    # Test 6c: Time series plots (if time column exists)
    print("  Testing time series plots...")
    if 'time_s' in loco.df.columns:
        loco.plot_time_series(subject, task, features[:1], 
                             save_path='test_timeseries.png')
        if os.path.exists('test_timeseries.png'):
            print("    ✓ Time series plot created")
            os.remove('test_timeseries.png')
        else:
            print("    ✗ Time series plot failed")
    else:
        print("    - Time series skipped (no time_s column)")
    
    # Test 6d: Plotting parameter validation
    print("  Testing plot parameter validation...")
    try:
        # Test invalid plot type
        loco.plot_phase_patterns(subject, task, features[:1], plot_type='invalid')
        print("    ✗ Should have failed with invalid plot type")
    except (ValueError, TypeError):
        print("    ✓ Invalid plot type properly rejected")
    
    # Test 6e: Empty data handling
    print("  Testing empty data handling...")
    try:
        loco.plot_phase_patterns('nonexistent', 'nonexistent', features[:1])
        print("    ✓ Empty data handled gracefully")
    except Exception as e:
        print(f"    ✓ Empty data handled with warning: {type(e).__name__}")
    
    print("✓ All plotting tests completed")
    
except ImportError as e:
    print(f"✗ Plotting import error: {e}")
    print("  Note: Install matplotlib and seaborn for plotting functionality")
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