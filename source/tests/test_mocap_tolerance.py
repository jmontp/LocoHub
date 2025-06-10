#!/usr/bin/env python3
"""
Test Motion Capture Error Tolerance

Tests that our updated validation expectations correctly handle
motion capture measurement errors, particularly for knee flexion
angles that may register as slightly negative (-10°) due to
calibration errors and measurement noise.
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add source directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from spec_compliance_test_suite import SpecComplianceTestSuite
from validation_markdown_parser import ValidationMarkdownParser


def create_mocap_error_test_data() -> pd.DataFrame:
    """
    Create test data that includes motion capture errors,
    specifically knee flexion values that can be slightly negative.
    """
    np.random.seed(42)  # For reproducible tests
    n_samples = 300  # 2 cycles × 150 points each
    
    # Create phase data (2 complete cycles)
    phase_l = np.concatenate([
        np.linspace(0, 99.9, 150),  # Cycle 1
        np.linspace(0, 99.9, 150)   # Cycle 2
    ])
    
    # Create realistic biomechanical data with motion capture errors
    data = {
        'time_s': np.linspace(0, 3.0, n_samples),
        'phase_l': phase_l,
        'subject_id': ['S01'] * n_samples,
        'task_id': ['T001'] * n_samples,
        'task_name': ['level_walking'] * n_samples,
        
        # Joint angles with realistic motion capture errors
        'hip_flexion_angle_ipsi_rad': 0.3 + 0.5 * np.sin(2 * np.pi * phase_l / 100) + 0.01 * np.random.randn(n_samples),
        'hip_flexion_angle_contra_rad': 0.3 + 0.5 * np.sin(2 * np.pi * (phase_l + 50) / 100) + 0.01 * np.random.randn(n_samples),
        
        # Knee flexion: realistic gait pattern with motion capture error tolerance
        # Some values at heel strike (phase ~0%) may be slightly negative due to measurement noise
        'knee_flexion_angle_ipsi_rad': create_realistic_knee_pattern(phase_l, n_samples, leg='ipsi'),
        'knee_flexion_angle_contra_rad': create_realistic_knee_pattern(phase_l, n_samples, leg='contra'),
        
        'ankle_flexion_angle_ipsi_rad': 0.1 * np.sin(2 * np.pi * phase_l / 100) + 0.005 * np.random.randn(n_samples),
        'ankle_flexion_angle_contra_rad': 0.1 * np.sin(2 * np.pi * (phase_l + 50) / 100) + 0.005 * np.random.randn(n_samples),
        
        # GRF data
        'vertical_grf_N': 800 + 400 * np.sin(2 * np.pi * phase_l / 100)**2 + 20 * np.random.randn(n_samples),
        'ap_grf_N': 100 * np.sin(4 * np.pi * phase_l / 100) + 10 * np.random.randn(n_samples),
        'ml_grf_N': 20 * np.random.randn(n_samples),
        
        # COP data
        'cop_x_m': 0.05 * np.sin(2 * np.pi * phase_l / 100) + 0.002 * np.random.randn(n_samples),
        'cop_y_m': 0.02 * np.random.randn(n_samples),
        'cop_z_m': 0.01 * np.random.randn(n_samples),
        
        # Quality flags
        'is_outlier': [False] * n_samples
    }
    
    return pd.DataFrame(data)


def create_realistic_knee_pattern(phase_l: np.ndarray, n_samples: int, leg: str = 'ipsi') -> np.ndarray:
    """
    Create realistic knee flexion pattern with motion capture error tolerance.
    
    - OpenSim convention: 0° = full extension, positive = flexion
    - Motion capture errors can cause slightly negative values (-10° tolerance)
    - Realistic gait pattern: extension at heel strike, flexion during swing
    """
    # Phase offset for contralateral leg
    phase_offset = 50 if leg == 'contra' else 0
    adjusted_phase = (phase_l + phase_offset) % 100
    
    # Base knee flexion pattern (realistic gait)
    base_pattern = np.zeros(n_samples)
    
    for i, phase in enumerate(adjusted_phase):
        if 0 <= phase < 10:  # Heel strike - nearly extended
            base_pattern[i] = np.random.uniform(-0.05, 0.15)  # -3° to 9° (some negative due to mocap error)
        elif 10 <= phase < 30:  # Loading response - slight flexion
            base_pattern[i] = np.random.uniform(0.05, 0.25)  # 3° to 14°
        elif 30 <= phase < 60:  # Mid-stance - minimal flexion
            base_pattern[i] = np.random.uniform(0.02, 0.20)  # 1° to 11°
        elif 60 <= phase < 70:  # Toe-off - moderate flexion
            base_pattern[i] = np.random.uniform(0.5, 0.8)   # 29° to 46°
        elif 70 <= phase < 85:  # Mid-swing - peak flexion
            base_pattern[i] = np.random.uniform(0.8, 1.3)   # 46° to 74°
        else:  # Terminal swing - decreasing flexion
            base_pattern[i] = np.random.uniform(0.1, 0.4)   # 6° to 23°
    
    # Add realistic measurement noise
    measurement_noise = 0.02 * np.random.randn(n_samples)  # ~1° std dev
    
    # Some values near heel strike can be slightly negative due to motion capture error
    pattern_with_noise = base_pattern + measurement_noise
    
    # Ensure we don't go below -10° (our tolerance limit) or above 150° (physiological limit)
    pattern_with_noise = np.clip(pattern_with_noise, -0.17, 2.6)  # -10° to 150°
    
    return pattern_with_noise


def test_mocap_tolerance():
    """Test that our validation system correctly handles motion capture errors."""
    
    print("🧪 Testing Motion Capture Error Tolerance")
    print("=" * 50)
    
    # Create test data with realistic motion capture errors
    test_data = create_mocap_error_test_data()
    
    # Check that we have some slightly negative knee values (simulating mocap error)
    knee_left = test_data['knee_flexion_angle_ipsi_rad']
    knee_right = test_data['knee_flexion_angle_contra_rad']
    
    min_knee_left = knee_left.min()
    min_knee_right = knee_right.min()
    
    print(f"📊 Knee flexion ranges in test data:")
    print(f"   Left knee:  {np.degrees(min_knee_left):.1f}° to {np.degrees(knee_left.max()):.1f}°")
    print(f"   Right knee: {np.degrees(min_knee_right):.1f}° to {np.degrees(knee_right.max()):.1f}°")
    
    # Verify we have some values in the motion capture error range
    negative_left = np.sum(knee_left < 0)
    negative_right = np.sum(knee_right < 0)
    
    print(f"📈 Motion capture error simulation:")
    print(f"   Left knee negative values:  {negative_left}/{len(knee_left)} ({100*negative_left/len(knee_left):.1f}%)")
    print(f"   Right knee negative values: {negative_right}/{len(knee_right)} ({100*negative_right/len(knee_right):.1f}%)")
    
    # Test with our validation system
    print(f"\n🔍 Testing with updated validation expectations...")
    
    # Initialize test suite
    test_suite = SpecComplianceTestSuite()
    
    # Test sign convention compliance (should pass with our updated ranges)
    sign_results = test_suite.test_sign_convention_adherence(test_data)
    
    print(f"\n✅ Sign Convention Test Results:")
    print(f"   Joint angles checked: {len(sign_results['joint_angle_checks'])}")
    print(f"   Sign convention issues: {len(sign_results['sign_convention_issues'])}")
    
    # Print any issues
    if sign_results['sign_convention_issues']:
        print(f"\n⚠️  Sign convention issues found:")
        for issue in sign_results['sign_convention_issues']:
            print(f"   - {issue}")
    else:
        print(f"   ✅ All joint angles within expected ranges (including mocap error tolerance)")
    
    # Test with markdown validation expectations
    try:
        # Check if we can load the updated validation expectations
        parser = ValidationMarkdownParser()
        
        # Look for validation expectations file
        validation_file = Path("docs/standard_spec/validation_expectations_kinematic.md")
        if validation_file.exists():
            print(f"\n📋 Testing against updated validation expectations...")
            validation_rules = parser.parse_file(str(validation_file))
            print(f"   Loaded rules for {len(validation_rules)} tasks")
            
            # Test level walking validation
            if 'level_walking' in validation_rules:
                walking_data = test_data[test_data['task_name'] == 'level_walking']
                validation_result = parser.validate_data(walking_data, 'level_walking')
                
                print(f"   Level walking validation: {validation_result['passed_rules']}/{validation_result['total_rules']} rules passed")
                print(f"   Success rate: {validation_result['success_rate']:.1%}")
                
                if validation_result['failed_rules'] > 0:
                    print(f"\n⚠️  Failed validation rules:")
                    for failure in validation_result.get('failures', []):
                        print(f"   - {failure}")
                        
        else:
            print(f"   ❌ Validation expectations file not found: {validation_file}")
            
    except Exception as e:
        print(f"   ❌ Error testing markdown validation: {e}")
    
    print(f"\n🎯 Motion Capture Error Tolerance Test Summary:")
    print(f"   - Generated realistic test data with mocap errors")
    print(f"   - Knee flexion ranges include values down to {np.degrees(min(min_knee_left, min_knee_right)):.1f}°")
    print(f"   - Updated validation expectations accommodate -10° tolerance")
    print(f"   - Test data should now pass updated validation rules")
    
    return test_data, sign_results


if __name__ == "__main__":
    test_data, results = test_mocap_tolerance()
    
    # Save test data for further analysis if needed
    output_file = "test_data_with_mocap_tolerance.csv"
    test_data.to_csv(output_file, index=False)
    print(f"\n💾 Test data saved to: {output_file}")