#!/usr/bin/env python3
"""
Demonstration of Intuitive Biomechanical Validation

This script shows how to use the new intuitive validation system alongside
the existing validation framework to provide more clinically interpretable
validation results.

Usage:
    python demo_intuitive_validation.py [parquet_file]
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add the source directory to path for imports
sys.path.append(str(Path(__file__).parent))

from validation_intuitive_biomechanics import IntuitiveValidator
from validation_blueprint_enhanced import BiomechanicsValidator

def demo_intuitive_validation(parquet_file: str = None):
    """
    Demonstrate the intuitive validation system with real or synthetic data.
    
    Args:
        parquet_file: Path to parquet file, or None to use synthetic data
    """
    
    if parquet_file and Path(parquet_file).exists():
        print(f"Loading data from {parquet_file}")
        df = pd.read_parquet(parquet_file)
        
        # Ensure required columns exist
        required_cols = ['subject_id', 'task_name', 'phase_%']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Warning: Missing required columns: {missing_cols}")
            print("Using synthetic data instead...")
            df = create_synthetic_data()
    else:
        print("Creating synthetic biomechanical data for demonstration...")
        df = create_synthetic_data()
    
    print(f"\nDataset Info:")
    print(f"- Rows: {len(df):,}")
    print(f"- Subjects: {df['subject_id'].nunique()}")
    print(f"- Tasks: {df['task_name'].nunique()}")
    print(f"- Tasks: {list(df['task_name'].unique())}")
    
    # Run intuitive validation
    print("\n" + "="*60)
    print("INTUITIVE BIOMECHANICAL VALIDATION")
    print("="*60)
    
    intuitive_validator = IntuitiveValidator(df)
    validated_df = intuitive_validator.validate()
    
    print(f"\nIntuitive Validation Results:")
    print(f"- Valid rows: {validated_df['validation_intuitive'].sum():,}")
    print(f"- Invalid rows: {(~validated_df['validation_intuitive']).sum():,}")
    print(f"- Success rate: {validated_df['validation_intuitive'].mean()*100:.1f}%")
    
    # Generate clinical report and error table
    clinical_report = intuitive_validator.get_clinical_report()
    error_table = intuitive_validator.get_error_table()
    step_errors = intuitive_validator.get_step_level_errors()
    bug_fix_report = intuitive_validator.get_bug_fix_report()
    
    if len(clinical_report) > 0:
        print(f"\nClinical Issues Found: {len(clinical_report)}")
        print("\nTop 10 Clinical Issues:")
        print(clinical_report[['joint_phase', 'task', 'actual_angle_deg', 
                              'expected_min_deg', 'expected_max_deg', 'severity']].head(10))
        
        # Summary by severity
        print(f"\nSeverity Breakdown:")
        severity_counts = clinical_report['severity'].value_counts()
        for severity, count in severity_counts.items():
            print(f"- {severity}: {count}")
    else:
        print("\n✓ No clinical issues found!")
    
    # Show comprehensive error table
    if len(error_table) > 0:
        print("\n" + "="*60)
        print("COMPREHENSIVE ERROR TABLE")
        print("="*60)
        print(f"\nErrors by Task and Measurement:")
        print(error_table[['task_name', 'joint', 'phase', 'error_type', 'count', 'severity_avg']])
        
        # Summary statistics
        print(f"\nError Summary:")
        print(f"- Total error instances: {error_table['count'].sum()}")
        print(f"- Tasks with errors: {error_table['task_name'].nunique()}")
        print(f"- Joints with errors: {error_table['joint'].nunique()}")
        print(f"- Average severity: {error_table['severity_avg'].mean():.2f}")
        
        # Most problematic combinations
        top_errors = error_table.nlargest(5, 'count')
        print(f"\nTop 5 Most Problematic Task-Joint Combinations:")
        for _, row in top_errors.iterrows():
            print(f"- {row['task_name']} / {row['joint']} / {row['phase']}: {row['count']} errors (severity: {row['severity_avg']:.1f})")
    else:
        print("\n✓ No validation errors found in error table!")
    
    # Show step-level debugging information
    if len(step_errors) > 0:
        print("\n" + "="*60)
        print("STEP-LEVEL DEBUGGING INFORMATION")
        print("="*60)
        print(f"\nTotal failing steps: {len(step_errors)}")
        
        # Show example of most problematic steps
        worst_steps = step_errors.nlargest(5, 'deviation_deg')
        print(f"\nTop 5 Most Problematic Steps:")
        for _, step in worst_steps.iterrows():
            print(f"- {step['step_id']}: {step['joint']} = {step['actual_value_deg']:.1f}° "
                  f"(expected: {step['expected_min_deg']:.1f}-{step['expected_max_deg']:.1f}°) "
                  f"Severity: {step['severity']}")
    
    # Show bug fix report
    if len(bug_fix_report) > 0:
        print("\n" + "="*60)
        print("BUG FIX GUIDANCE")
        print("="*60)
        print(f"\nActionable debugging information:")
        print(bug_fix_report[['subject_id', 'task_name', 'joint', 'error_count', 
                              'typical_severity', 'fix_suggestion']].head(10))
        
        # Highlight most critical issues
        critical_issues = bug_fix_report[bug_fix_report['typical_severity'] == 'Severe'].head(3)
        if len(critical_issues) > 0:
            print(f"\n🚨 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
            for _, issue in critical_issues.iterrows():
                print(f"\n📍 {issue['subject_id']} / {issue['task_name']} / {issue['joint']}:")
                print(f"   💢 {issue['error_count']} severe errors (avg deviation: {issue['avg_deviation_deg']:.1f}°)")
                print(f"   🔧 Fix: {issue['fix_suggestion']}")
    
    # Compare with traditional validation
    print("\n" + "="*60)
    print("TRADITIONAL VALIDATION COMPARISON")
    print("="*60)
    
    try:
        # Add required columns for traditional validator
        if 'task_id' not in validated_df.columns:
            validated_df['task_id'] = validated_df['task_name']
        if 'time_s' not in validated_df.columns:
            validated_df['time_s'] = validated_df.index * 0.01  # Synthetic time
        
        traditional_validator = BiomechanicsValidator(validated_df, mode='comprehensive')
        traditional_result = traditional_validator.validate()
        
        print(f"\nTraditional Validation Results:")
        if 'is_valid' in traditional_result.columns:
            print(f"- Valid rows: {traditional_result['is_valid'].sum():,}")
            print(f"- Invalid rows: {(~traditional_result['is_valid']).sum():,}")
            print(f"- Success rate: {traditional_result['is_valid'].mean()*100:.1f}%")
        
        # Get failure report
        traditional_report = traditional_validator.get_failure_report()
        if len(traditional_report) > 0:
            print(f"\nTraditional Issues Found: {len(traditional_report)}")
            print("\nTop Traditional Issues:")
            print(traditional_report.head())
    
    except Exception as e:
        print(f"Traditional validation failed: {e}")
    
    # Export expectations table for reference
    print("\n" + "="*60)
    print("EXPORTING REFERENCE TABLES")
    print("="*60)
    
    output_dir = Path("validation_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Export expectations table
    expectations_file = output_dir / "biomechanical_expectations.csv"
    intuitive_validator.export_expectations_table(str(expectations_file))
    
    # Export validation results
    if len(clinical_report) > 0:
        clinical_file = output_dir / "clinical_validation_report.csv" 
        clinical_report.to_csv(clinical_file, index=False)
        print(f"Clinical report saved to {clinical_file}")
    
    # Export error table
    if len(error_table) > 0:
        error_table_file = output_dir / "validation_error_table.csv"
        error_table.to_csv(error_table_file, index=False)
        print(f"Error table saved to {error_table_file}")
    
    # Export comprehensive debugging reports
    if len(step_errors) > 0:
        base_debug_path = str(output_dir / "debug_report")
        intuitive_validator.export_debugging_reports(base_debug_path)
    
    # Export validated dataset
    validated_file = output_dir / "validated_dataset.csv"
    validated_df.to_csv(validated_file, index=False)
    print(f"Validated dataset saved to {validated_file}")
    
    print(f"\n✓ Demo completed! Check {output_dir}/ for output files.")
    
    return validated_df, clinical_report

def create_synthetic_data():
    """Create realistic synthetic biomechanical data for demonstration"""
    np.random.seed(42)
    
    subjects = ['S01', 'S02', 'S03']
    tasks = ['level_walking', 'incline_walking', 'up_stairs', 'run', 'squats']
    
    data_list = []
    
    for subject in subjects:
        for task in tasks:
            # Each task has 150 phase points (0-100%)
            phases = np.linspace(0, 100, 150)
            
            # Generate realistic joint angle patterns based on task
            if task == 'level_walking':
                hip_angles = 0.3 + 0.2 * np.sin(phases * np.pi / 50) + np.random.normal(0, 0.05, 150)
                knee_angles = 1.0 + 0.3 * np.sin(phases * np.pi / 50 + np.pi/4) + np.random.normal(0, 0.1, 150)
                ankle_angles = 0.1 + 0.15 * np.sin(phases * np.pi / 50 - np.pi/3) + np.random.normal(0, 0.05, 150)
                
            elif task == 'incline_walking':
                hip_angles = 0.5 + 0.25 * np.sin(phases * np.pi / 50) + np.random.normal(0, 0.05, 150)
                knee_angles = 1.1 + 0.35 * np.sin(phases * np.pi / 50 + np.pi/4) + np.random.normal(0, 0.1, 150)
                ankle_angles = 0.2 + 0.2 * np.sin(phases * np.pi / 50 - np.pi/3) + np.random.normal(0, 0.05, 150)
                
            elif task == 'up_stairs':
                hip_angles = 0.7 + 0.4 * np.sin(phases * np.pi / 50) + np.random.normal(0, 0.1, 150)
                knee_angles = 1.4 + 0.5 * np.sin(phases * np.pi / 50 + np.pi/4) + np.random.normal(0, 0.15, 150)
                ankle_angles = 0.3 + 0.25 * np.sin(phases * np.pi / 50 - np.pi/3) + np.random.normal(0, 0.08, 150)
                
            elif task == 'run':
                hip_angles = 0.4 + 0.35 * np.sin(phases * np.pi / 50) + np.random.normal(0, 0.08, 150)
                knee_angles = 1.2 + 0.6 * np.sin(phases * np.pi / 50 + np.pi/4) + np.random.normal(0, 0.15, 150)
                ankle_angles = 0.15 + 0.3 * np.sin(phases * np.pi / 50 - np.pi/3) + np.random.normal(0, 0.1, 150)
                
            elif task == 'squats':
                # Squats have a different pattern - more like a symmetric cycle
                cycle_factor = np.cos(phases * 2 * np.pi / 100)  # Full cycle
                hip_angles = 1.0 + 0.5 * cycle_factor + np.random.normal(0, 0.1, 150)
                knee_angles = 1.8 + 0.7 * cycle_factor + np.random.normal(0, 0.15, 150)
                ankle_angles = 0.4 + 0.3 * cycle_factor + np.random.normal(0, 0.08, 150)
            
            # Calculate velocities (simplified)
            hip_velocities = np.gradient(hip_angles) * 100 + np.random.normal(0, 0.5, 150)  # Scale by phase rate
            knee_velocities = np.gradient(knee_angles) * 100 + np.random.normal(0, 0.5, 150)
            ankle_velocities = np.gradient(ankle_angles) * 100 + np.random.normal(0, 0.5, 150)
            
            # Add some outliers for demonstration (5% of data)
            outlier_mask = np.random.random(150) < 0.05
            hip_angles[outlier_mask] += np.random.normal(0, 0.5, outlier_mask.sum())
            knee_angles[outlier_mask] += np.random.normal(0, 0.8, outlier_mask.sum())
            
            # Create task data
            task_data = pd.DataFrame({
                'subject_id': subject,
                'task_name': task,
                'task_id': f"{subject}_{task}",
                'phase_%': phases,
                'hip_flexion_angle_rad': hip_angles,
                'knee_flexion_angle_rad': knee_angles,
                'ankle_flexion_angle_rad': ankle_angles,
                'hip_adduction_angle_rad': np.random.normal(0, 0.1, 150),
                'hip_flexion_velocity_rad_s': hip_velocities,
                'knee_flexion_velocity_rad_s': knee_velocities,
                'ankle_flexion_velocity_rad_s': ankle_velocities,
            })
            
            data_list.append(task_data)
    
    return pd.concat(data_list, ignore_index=True)

if __name__ == '__main__':
    # Check if parquet file was provided as argument
    parquet_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("="*60)
    print("INTUITIVE BIOMECHANICAL VALIDATION DEMO")
    print("="*60)
    print("This demo shows phase-based validation using clinically")
    print("intuitive expected joint angle ranges at key gait phases.")
    print()
    
    validated_df, clinical_report = demo_intuitive_validation(parquet_file)