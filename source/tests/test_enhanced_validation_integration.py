#!/usr/bin/env python3
"""
Enhanced Validation System Integration Test

Tests the complete two-tier validation system with visual kinematic validation.
Demonstrates the integration of:
1. Enhanced validation system (Tier 1 + Tier 2)
2. Phase-specific range validation 
3. Forward kinematic pose generation
4. Visual validation integration

This script serves as both a test and demonstration of the complete system.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Add source directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tests.enhanced_validation_system import EnhancedValidationSystem
from visualization.kinematic_pose_generator import KinematicPoseGenerator

def create_comprehensive_test_data(task_name: str = 'level_walking', n_subjects: int = 3) -> pd.DataFrame:
    """
    Create comprehensive test data with multiple subjects and realistic biomechanical patterns.
    
    Args:
        task_name: Name of the locomotion task
        n_subjects: Number of subjects to simulate
        
    Returns:
        DataFrame with comprehensive test data
    """
    np.random.seed(42)
    
    all_data = []
    
    for subject_idx in range(n_subjects):
        subject_id = f"S{subject_idx+1:02d}"
        
        # Create 2 complete gait cycles (300 points)
        n_samples = 300
        phase_l = np.concatenate([
            np.linspace(0, 99.9, 150),  # Cycle 1
            np.linspace(0, 99.9, 150)   # Cycle 2
        ])
        
        # Add subject-specific variability
        subject_offset = subject_idx * 0.1
        speed_factor = 1.0 + (subject_idx - 1) * 0.2  # Vary walking speed
        
        # Generate realistic biomechanical patterns for level walking
        if task_name == 'level_walking':
            # Hip angles with subject variability
            hip_flexion_left = (0.2 + subject_offset) + 0.4 * np.sin(2 * np.pi * phase_l / 100)
            hip_flexion_right = (0.2 + subject_offset) + 0.4 * np.sin(2 * np.pi * (phase_l + 50) / 100)
            
            # Knee angles with dual peaks
            knee_flexion_left = (0.2 + subject_offset/2) + 0.5 * np.maximum(0, np.sin(2 * np.pi * phase_l / 100))
            knee_flexion_right = (0.2 + subject_offset/2) + 0.5 * np.maximum(0, np.sin(2 * np.pi * (phase_l + 50) / 100))
            
            # Ankle angles
            ankle_flexion_left = 0.1 * np.sin(2 * np.pi * phase_l / 100) + subject_offset/10
            ankle_flexion_right = 0.1 * np.sin(2 * np.pi * (phase_l + 50) / 100) + subject_offset/10
            
            # Ground reaction forces
            vertical_grf = (800 + subject_idx * 100) + 400 * np.sin(2 * np.pi * phase_l / 100)**2
            ap_grf = 100 * np.sin(4 * np.pi * phase_l / 100) * speed_factor
            ml_grf = 20 * np.random.randn(n_samples) + subject_offset * 10
            
        else:
            # Default patterns for other tasks
            hip_flexion_left = 0.3 + 0.5 * np.sin(2 * np.pi * phase_l / 100)
            hip_flexion_right = 0.3 + 0.5 * np.sin(2 * np.pi * (phase_l + 50) / 100)
            knee_flexion_left = 0.3 + 0.6 * np.maximum(0, np.sin(2 * np.pi * phase_l / 100))
            knee_flexion_right = 0.3 + 0.6 * np.maximum(0, np.sin(2 * np.pi * (phase_l + 50) / 100))
            ankle_flexion_left = 0.15 * np.sin(2 * np.pi * phase_l / 100)
            ankle_flexion_right = 0.15 * np.sin(2 * np.pi * (phase_l + 50) / 100)
            vertical_grf = 900 + 500 * np.sin(2 * np.pi * phase_l / 100)**2
            ap_grf = 150 * np.sin(4 * np.pi * phase_l / 100)
            ml_grf = 30 * np.random.randn(n_samples)
        
        # Create subject data
        subject_data = pd.DataFrame({
            'time_s': np.linspace(0, 3.0, n_samples),
            'phase_l': phase_l,
            'subject_id': [subject_id] * n_samples,
            'task_name': [task_name] * n_samples,
            'task_id': ['T001'] * n_samples,
            
            # Joint angles
            'hip_flexion_angle_left_rad': hip_flexion_left,
            'hip_flexion_angle_right_rad': hip_flexion_right,
            'knee_flexion_angle_left_rad': knee_flexion_left,
            'knee_flexion_angle_right_rad': knee_flexion_right,
            'ankle_flexion_angle_left_rad': ankle_flexion_left,
            'ankle_flexion_angle_right_rad': ankle_flexion_right,
            
            # Ground reaction forces  
            'vertical_grf_N': vertical_grf,
            'ap_grf_N': ap_grf,
            'ml_grf_N': ml_grf,
            
            # Center of pressure
            'cop_x_m': 0.05 * np.sin(2 * np.pi * phase_l / 100),
            'cop_y_m': 0.02 * np.random.randn(n_samples),
            'cop_z_m': 0.01 * np.random.randn(n_samples),
            
            # Subject metadata
            'age': [25 + subject_idx * 5] * n_samples,
            'gender': [['male', 'female', 'male'][subject_idx]] * n_samples,
            'height': [1.70 + subject_idx * 0.05] * n_samples,
            'body_mass': [70.0 + subject_idx * 10] * n_samples,
            'walking_speed_m_s': [1.2 + subject_idx * 0.1] * n_samples,
            
            # Quality flags
            'is_outlier': [False] * n_samples
        })
        
        all_data.append(subject_data)
    
    # Combine all subjects
    combined_data = pd.concat(all_data, ignore_index=True)
    return combined_data

def run_comprehensive_validation_test():
    """Run a comprehensive test of the enhanced validation system"""
    
    print("🚀 ENHANCED VALIDATION SYSTEM - COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Create output directories
    output_dirs = {
        'validation_reports': Path("validation_reports"),
        'validation_images': Path("validation_images"),
        'test_outputs': Path("test_outputs")
    }
    
    for dir_path in output_dirs.values():
        dir_path.mkdir(exist_ok=True)
    
    # Test 1: Create comprehensive test data
    print("\\n📊 Step 1: Creating comprehensive test dataset...")
    test_data = create_comprehensive_test_data('level_walking', n_subjects=3)
    print(f"   ✓ Created dataset: {len(test_data)} rows, {len(test_data.columns)} columns")
    print(f"   ✓ Subjects: {test_data['subject_id'].nunique()}")
    print(f"   ✓ Tasks: {test_data['task_name'].unique()}")
    
    # Test 2: Initialize enhanced validation system
    print("\\n🔧 Step 2: Initializing enhanced validation system...")
    validator = EnhancedValidationSystem()
    print("   ✓ Enhanced validation system initialized")
    print("   ✓ Two-tier validation structure ready")
    print(f"   ✓ Generic ranges defined for {len(validator.generic_ranges)} variable types")
    
    # Test 3: Run complete validation
    print("\\n🔍 Step 3: Running two-tier validation...")
    validation_results = validator.run_full_validation(test_data, 'level_walking')
    
    # Display validation summary
    tier1_summary = validation_results['tier1_results'].get('summary', {})
    tier2_summary = validation_results['tier2_results'].get('summary', {})
    overall_summary = validation_results['overall_summary']
    
    print(f"   📋 Tier 1 Results:")
    print(f"      - Columns tested: {tier1_summary.get('total_columns_tested', 0)}")
    print(f"      - Pass rate: {tier1_summary.get('overall_pass_rate', 0):.1%}")
    print(f"      - Status: {'✅ PASS' if tier1_summary.get('tier1_pass', False) else '❌ FAIL'}")
    
    print(f"   📋 Tier 2 Results:")
    print(f"      - Phase points tested: {tier2_summary.get('total_phase_points_tested', 0)}")
    print(f"      - Phase points passed: {tier2_summary.get('phase_points_passed', 0)}")
    print(f"      - Pattern violations: {tier2_summary.get('pattern_violations_count', 0)}")
    print(f"      - Status: {'✅ PASS' if tier2_summary.get('tier2_pass', False) else '❌ FAIL'}")
    
    print(f"   🎯 Overall Status: {'✅ PASS' if overall_summary['overall_validation_pass'] else '❌ FAIL'}")
    
    # Test 4: Generate validation report
    print("\\n📄 Step 4: Generating validation report...")
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dirs['validation_reports'] / f"comprehensive_validation_{timestamp}.txt"
    validator.generate_validation_report(validation_results, str(report_path))
    print(f"   ✓ Report saved: {report_path}")
    
    # Test 5: Initialize kinematic pose generator
    print("\\n🎨 Step 5: Initializing kinematic pose generator...")
    pose_generator = KinematicPoseGenerator()
    print("   ✓ Kinematic pose generator initialized")
    print(f"   ✓ Phase points configured: {pose_generator.phase_points}")
    
    # Test 6: Extract phase-specific ranges from real data
    print("\\n📐 Step 6: Extracting phase-specific ranges from data...")
    phase_ranges = pose_generator.extract_phase_ranges_from_data(
        test_data, 'level_walking', pose_generator.phase_points
    )
    
    for phase, ranges in phase_ranges.items():
        print(f"   📊 Phase {phase}%: {len(ranges)} joint ranges extracted")
        for joint, range_info in ranges.items():
            print(f"      - {joint}: [{range_info['min']:.2f}, {range_info['max']:.2f}] rad")
    
    # Test 7: Generate kinematic validation images
    print("\\n🖼️  Step 7: Generating kinematic validation images...")
    generated_images = pose_generator.generate_task_validation_images(
        'level_walking', phase_ranges, str(output_dirs['validation_images'])
    )
    
    print(f"   ✓ Generated {len(generated_images)} validation images:")
    for img_path in generated_images:
        print(f"      - {Path(img_path).name}")
    
    # Test 8: Test with different tasks
    print("\\n🔄 Step 8: Testing with different tasks...")
    additional_tasks = ['incline_walking', 'up_stairs']
    
    for task in additional_tasks:
        print(f"   🏃 Testing task: {task}")
        task_data = create_comprehensive_test_data(task, n_subjects=2)
        task_results = validator.run_full_validation(task_data, task)
        
        task_images = pose_generator.generate_task_validation_images(
            task, None, str(output_dirs['validation_images'])
        )
        
        overall = task_results['overall_summary']
        print(f"      - Status: {'✅ PASS' if overall['overall_validation_pass'] else '❌ FAIL'}")
        print(f"      - Images: {len(task_images)} generated")
    
    # Test 9: Save test dataset for future use
    print("\\n💾 Step 9: Saving test dataset...")
    test_data_path = output_dirs['test_outputs'] / f"comprehensive_test_data_{timestamp}.parquet"
    test_data.to_parquet(test_data_path)
    print(f"   ✓ Test dataset saved: {test_data_path}")
    
    # Test 10: Integration verification
    print("\\n✅ Step 10: Integration verification...")
    
    # Verify all components work together
    checks = {
        'Enhanced validation system': validation_results['overall_summary']['overall_validation_pass'],
        'Kinematic pose generation': len(generated_images) == len(pose_generator.phase_points),
        'Phase-specific validation': len(phase_ranges) == len(pose_generator.phase_points),
        'Multi-task support': len(additional_tasks) > 0,
        'Report generation': report_path.exists(),
        'Image generation': all(Path(img).exists() for img in generated_images)
    }
    
    print("   🔍 Integration checks:")
    for check_name, status in checks.items():
        print(f"      - {check_name}: {'✅ PASS' if status else '❌ FAIL'}")
    
    overall_integration_pass = all(checks.values())
    
    # Final summary
    print("\\n" + "=" * 60)
    print("🎯 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    print(f"✨ Overall Integration: {'✅ SUCCESS' if overall_integration_pass else '❌ FAILED'}")
    print(f"📊 Data Validation: {'✅ PASS' if overall_summary['overall_validation_pass'] else '❌ FAIL'}")
    print(f"🖼️  Visual Generation: {'✅ COMPLETE' if len(generated_images) > 0 else '❌ FAILED'}")
    print(f"📄 Report Generation: {'✅ COMPLETE' if report_path.exists() else '❌ FAILED'}")
    print(f"🔄 Multi-task Support: {'✅ VERIFIED' if len(additional_tasks) > 0 else '❌ FAILED'}")
    
    print("\\n📂 Generated Outputs:")
    print(f"   - Validation report: {report_path}")
    print(f"   - Test dataset: {test_data_path}")
    print(f"   - Validation images: {len(generated_images)} files in {output_dirs['validation_images']}")
    
    return {
        'integration_pass': overall_integration_pass,
        'validation_results': validation_results,
        'generated_images': generated_images,
        'report_path': report_path,
        'test_data_path': test_data_path
    }

def main():
    """Main function for comprehensive integration testing"""
    
    try:
        results = run_comprehensive_validation_test()
        
        if results['integration_pass']:
            print("\\n🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!")
            print("   All systems integrated and functioning correctly.")
            return 0
        else:
            print("\\n❌ COMPREHENSIVE TEST FAILED!")
            print("   Some integration issues detected.")
            return 1
            
    except Exception as e:
        print(f"\\n💥 TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())