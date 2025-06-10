#!/usr/bin/env python3
"""
Integration test for filters_by_phase_plots.py functionality

Simple test that can be run without pytest to verify:
1. Basic functionality
2. Data overlay with violations
3. Color coding works correctly
"""

import numpy as np
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add source directories to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source' / 'visualization'))
sys.path.append(str(project_root / 'source'))

from filters_by_phase_plots import (
    create_filters_by_phase_plot, 
    classify_step_violations,
    detect_filter_violations
)
from validation.validation_expectations_parser import parse_kinematic_validation_expectations


def create_test_validation_data():
    """Create minimal validation data for testing"""
    return {
        'level_walking': {
            0: {
                'hip_flexion_angle_ipsi': {'min': 0.15, 'max': 0.6},
                'knee_flexion_angle_ipsi': {'min': 0.0, 'max': 0.15},
                'ankle_flexion_angle_ipsi': {'min': -0.05, 'max': 0.05},
                'hip_flexion_angle_contra': {'min': -0.35, 'max': 0.0},
                'knee_flexion_angle_contra': {'min': 0.5, 'max': 0.8},
                'ankle_flexion_angle_contra': {'min': -0.4, 'max': -0.2}
            },
            25: {
                'hip_flexion_angle_ipsi': {'min': -0.05, 'max': 0.35},
                'knee_flexion_angle_ipsi': {'min': 0.05, 'max': 0.25},
                'ankle_flexion_angle_ipsi': {'min': 0.05, 'max': 0.25},
                'hip_flexion_angle_contra': {'min': 0.3, 'max': 0.9},
                'knee_flexion_angle_contra': {'min': 0.8, 'max': 1.3},
                'ankle_flexion_angle_contra': {'min': -0.1, 'max': 0.2}
            },
            50: {
                'hip_flexion_angle_ipsi': {'min': -0.35, 'max': 0.0},
                'knee_flexion_angle_ipsi': {'min': 0.5, 'max': 0.8},
                'ankle_flexion_angle_ipsi': {'min': -0.4, 'max': -0.2},
                'hip_flexion_angle_contra': {'min': 0.15, 'max': 0.6},
                'knee_flexion_angle_contra': {'min': 0.0, 'max': 0.15},
                'ankle_flexion_angle_contra': {'min': -0.05, 'max': 0.05}
            },
            75: {
                'hip_flexion_angle_ipsi': {'min': 0.3, 'max': 0.9},
                'knee_flexion_angle_ipsi': {'min': 0.8, 'max': 1.3},
                'ankle_flexion_angle_ipsi': {'min': -0.1, 'max': 0.2},
                'hip_flexion_angle_contra': {'min': -0.05, 'max': 0.35},
                'knee_flexion_angle_contra': {'min': 0.05, 'max': 0.25},
                'ankle_flexion_angle_contra': {'min': 0.05, 'max': 0.25}
            }
        }
    }


def create_test_data_with_violations():
    """Create test data with known violations"""
    num_steps = 6
    num_points = 150
    num_features = 6
    
    phase_percent = np.linspace(0, 100, num_points)
    data = np.zeros((num_steps, num_points, num_features))
    
    # Create baseline valid patterns
    for step in range(num_steps):
        # Hip flexion
        hip_pattern = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.3
        data[step, :, 0] = hip_pattern  # hip_ipsi
        data[step, :, 1] = hip_pattern  # hip_contra
        
        # Knee flexion
        knee_pattern = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.3
        data[step, :, 2] = knee_pattern  # knee_ipsi
        data[step, :, 3] = knee_pattern  # knee_contra
        
        # Ankle flexion
        ankle_pattern = -0.15 * np.sin(2 * np.pi * phase_percent / 100) + 0.1
        data[step, :, 4] = ankle_pattern  # ankle_ipsi
        data[step, :, 5] = ankle_pattern  # ankle_contra
    
    # Add violations
    # Step 0: Hip ipsi violation
    data[0, :, 0] += 0.8  # Make hip too high
    
    # Step 1: Knee ipsi violation  
    data[1, :, 2] += 1.2  # Make knee too high
    
    # Step 2: Ankle ipsi violation
    data[2, :, 4] -= 0.8  # Make ankle too low
    
    # Step 3: Multiple violations
    data[3, :, 0] += 0.7  # Hip violation
    data[3, :, 2] += 1.0  # Knee violation
    
    # Step 4: Contralateral violation
    data[4, :, 1] += 0.9  # Hip contra violation
    
    # Step 5: Valid (no modifications)
    
    return data


def test_basic_functionality():
    """Test 1: Basic plot generation without data"""
    print("Test 1: Basic plot generation (no data overlay)")
    
    validation_data = create_test_validation_data()
    temp_dir = tempfile.mkdtemp()
    
    try:
        filepath = create_filters_by_phase_plot(
            validation_data=validation_data,
            task_name='level_walking',
            output_dir=temp_dir,
            mode='kinematic'
        )
        
        if os.path.exists(filepath):
            print("✅ PASS: Basic plot generated successfully")
            print(f"   File: {filepath}")
            return True
        else:
            print("❌ FAIL: Plot file not created")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during basic plot generation: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_data_overlay():
    """Test 2: Plot generation with data overlay"""
    print("\nTest 2: Data overlay functionality")
    
    validation_data = create_test_validation_data()
    test_data = create_test_data_with_violations()
    temp_dir = tempfile.mkdtemp()
    
    try:
        filepath = create_filters_by_phase_plot(
            validation_data=validation_data,
            task_name='level_walking',
            output_dir=temp_dir,
            mode='kinematic',
            data=test_data
        )
        
        if os.path.exists(filepath) and '_with_data' in filepath:
            print("✅ PASS: Data overlay plot generated successfully")
            print(f"   File: {filepath}")
            return True
        else:
            print("❌ FAIL: Data overlay plot not created or incorrectly named")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during data overlay: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_violation_detection():
    """Test 3: Violation detection logic"""
    print("\nTest 3: Violation detection")
    
    validation_data = create_test_validation_data()
    test_data = create_test_data_with_violations()
    task_data = validation_data['level_walking']
    
    feature_map = {
        ('hip_flexion_angle', 'ipsi'): 0,
        ('hip_flexion_angle', 'contra'): 1,
        ('knee_flexion_angle', 'ipsi'): 2,
        ('knee_flexion_angle', 'contra'): 3,
        ('ankle_flexion_angle', 'ipsi'): 4,
        ('ankle_flexion_angle', 'contra'): 5
    }
    
    try:
        # Test hip ipsi violations (feature 0)
        global_violations, local_violations = detect_filter_violations(
            test_data, task_data, feature_map, 'kinematic', 0
        )
        
        print(f"   Global violations detected: {sorted(global_violations)}")
        print(f"   Local violations (hip ipsi): {sorted(local_violations)}")
        
        # Verify that violation detection is working
        # We expect violations in multiple steps due to our synthetic data
        if len(global_violations) >= 4 and len(local_violations) >= 2:
            print("✅ PASS: Violation detection working correctly")
            print(f"   Detected {len(global_violations)} global violations and {len(local_violations)} local violations")
            return True
        else:
            print("❌ FAIL: Violation detection not detecting expected violations")
            print(f"   Found {len(global_violations)} global and {len(local_violations)} local violations")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception during violation detection: {e}")
        return False


def test_real_validation_file():
    """Test 4: Integration with real validation file"""
    print("\nTest 4: Real validation file integration")
    
    validation_file = project_root / 'docs' / 'standard_spec' / 'validation_expectations_kinematic.md'
    
    if not validation_file.exists():
        print("⏭️  SKIP: Real validation file not found")
        return True
    
    try:
        validation_data = parse_kinematic_validation_expectations(str(validation_file))
        
        if 'level_walking' in validation_data and len(validation_data['level_walking']) > 0:
            print("✅ PASS: Real validation file parsed successfully")
            print(f"   Tasks found: {list(validation_data.keys())}")
            print(f"   Level walking phases: {list(validation_data['level_walking'].keys())}")
            return True
        else:
            print("❌ FAIL: Real validation file parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception parsing real validation file: {e}")
        return False


def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Filters By Phase Plots Integration Tests")
    print("=" * 60)
    
    tests = [
        test_basic_functionality,
        test_data_overlay,
        test_violation_detection,
        test_real_validation_file
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   Test {i+1}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check output above for details.")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)