#!/usr/bin/env python3
"""
Demo Dataset Generator for dataset_validator_phase.py

Created: 2025-06-10 with user permission
Purpose: Generate test/demo datasets in phase-indexed parquet format to validate the
         integrated dataset_validator_phase.py that uses LocomotionData library.

Intent:
This script creates realistic phase-indexed datasets that can be used to test and
demonstrate the dataset_validator_phase.py functionality. It follows the patterns
established in demo_step_classifier.py but creates complete parquet datasets that
match the LocomotionData library's expected format.

**PRIMARY FUNCTIONS:**
1. **Dataset Generation**: Create phase-indexed parquet files with realistic gait data
2. **Validation Testing**: Generate datasets with known violations for accuracy testing
3. **Integration Demo**: Show complete workflow from data creation to validation reports
4. **Performance Testing**: Test LocomotionData integration with realistic dataset sizes

Usage:
    python source/tests/demo_dataset_validator_phase.py
    
    # Then test the generated dataset:
    python source/validation/dataset_validator_phase.py --dataset source/tests/test_data/demo_dataset_phase.parquet

Key Features:
- Creates realistic phase-indexed datasets (150 points per gait cycle)
- Multiple subjects and tasks for comprehensive testing
- Known validation violations for accuracy verification
- Compatible with LocomotionData library format requirements
- Standard variable naming conventions
- Proper phase column structure
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import warnings

# Add source directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source'))

from validation.step_classifier import StepClassifier

def print_banner(title):
    """Print a formatted banner for section separation."""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print('='*60)

def create_realistic_gait_cycle(task: str = 'level_walking', validation_ranges: Dict = None) -> np.ndarray:
    """
    Create realistic gait cycle data for 6 joint angles over 150 phase points.
    
    Args:
        task: Task name for determining gait patterns
        validation_ranges: Optional validation ranges to ensure data stays within bounds
        
    Returns:
        Array of shape (150, 6) with joint angles in radians
    """
    phase_points = np.linspace(0, 100, 150)  # Phase percentage 0-100%
    
    # Define joint patterns based on typical gait biomechanics
    if task == 'level_walking':
        # Hip flexion patterns (ipsi and contra with phase offset)
        hip_ipsi = 0.3 * np.sin(np.radians(phase_points * 3.6)) + 0.15
        hip_contra = 0.3 * np.sin(np.radians(phase_points * 3.6 + 180)) + 0.15
        
        # Knee flexion patterns  
        knee_ipsi = 0.4 * np.sin(np.radians(phase_points * 7.2)) + 0.3
        knee_contra = 0.4 * np.sin(np.radians(phase_points * 7.2 + 180)) + 0.3
        
        # Ankle flexion patterns
        ankle_ipsi = 0.15 * np.sin(np.radians(phase_points * 3.6 + 90)) - 0.05
        ankle_contra = 0.15 * np.sin(np.radians(phase_points * 3.6 + 270)) - 0.05
        
    elif task == 'incline_walking':
        # Modified patterns for incline walking (more hip flexion, different ankle)
        hip_ipsi = 0.4 * np.sin(np.radians(phase_points * 3.6)) + 0.25
        hip_contra = 0.4 * np.sin(np.radians(phase_points * 3.6 + 180)) + 0.25
        
        knee_ipsi = 0.5 * np.sin(np.radians(phase_points * 7.2)) + 0.4
        knee_contra = 0.5 * np.sin(np.radians(phase_points * 7.2 + 180)) + 0.4
        
        ankle_ipsi = 0.2 * np.sin(np.radians(phase_points * 3.6 + 45)) + 0.1
        ankle_contra = 0.2 * np.sin(np.radians(phase_points * 3.6 + 225)) + 0.1
        
    elif task == 'running':
        # Running patterns (higher amplitudes, faster oscillations)
        hip_ipsi = 0.5 * np.sin(np.radians(phase_points * 3.6)) + 0.2
        hip_contra = 0.5 * np.sin(np.radians(phase_points * 3.6 + 180)) + 0.2
        
        knee_ipsi = 0.8 * np.sin(np.radians(phase_points * 7.2)) + 0.5
        knee_contra = 0.8 * np.sin(np.radians(phase_points * 7.2 + 180)) + 0.5
        
        ankle_ipsi = 0.3 * np.sin(np.radians(phase_points * 3.6 + 90)) + 0.1
        ankle_contra = 0.3 * np.sin(np.radians(phase_points * 3.6 + 270)) + 0.1
        
    else:  # Default to level walking
        hip_ipsi = 0.3 * np.sin(np.radians(phase_points * 3.6)) + 0.15
        hip_contra = 0.3 * np.sin(np.radians(phase_points * 3.6 + 180)) + 0.15
        knee_ipsi = 0.4 * np.sin(np.radians(phase_points * 7.2)) + 0.3
        knee_contra = 0.4 * np.sin(np.radians(phase_points * 7.2 + 180)) + 0.3
        ankle_ipsi = 0.15 * np.sin(np.radians(phase_points * 3.6 + 90)) - 0.05
        ankle_contra = 0.15 * np.sin(np.radians(phase_points * 3.6 + 270)) - 0.05
    
    # Combine into standard variable order matching LocomotionData.ANGLE_FEATURES
    gait_cycle = np.column_stack([
        hip_contra,   # hip_flexion_angle_contra_rad
        knee_contra,  # knee_flexion_angle_contra_rad  
        ankle_contra, # ankle_flexion_angle_contra_rad
        hip_ipsi,     # hip_flexion_angle_ipsi_rad
        knee_ipsi,    # knee_flexion_angle_ipsi_rad
        ankle_ipsi    # ankle_flexion_angle_ipsi_rad
    ])
    
    # Add realistic noise
    noise_scale = 0.02  # 2% noise
    gait_cycle += np.random.normal(0, noise_scale, gait_cycle.shape)
    
    return gait_cycle

def create_phase_indexed_dataset(
    subjects: List[str], 
    tasks: List[str], 
    steps_per_subject_task: int = 5,
    validation_scenarios: Dict = None,
    include_wrong_columns: bool = False,
    include_wrong_tasks: bool = False
) -> pd.DataFrame:
    """
    Create a complete phase-indexed dataset in parquet format compatible with LocomotionData.
    
    Args:
        subjects: List of subject IDs
        tasks: List of task names (should match validation expectations)
        steps_per_subject_task: Number of gait cycles per subject-task combination
        validation_scenarios: Optional dict specifying which steps should have violations
        include_wrong_columns: If True, use incorrect column names to test error handling
        include_wrong_tasks: If True, use incorrect task names to test error handling
        
    Returns:
        DataFrame in phase-indexed format ready for parquet export
    """
    print(f"📊 Creating phase-indexed dataset:")
    print(f"   • {len(subjects)} subjects: {subjects}")
    print(f"   • {len(tasks)} tasks: {tasks}")
    print(f"   • {steps_per_subject_task} steps per subject-task")
    if include_wrong_columns:
        print(f"   ⚠️  Using INCORRECT column names for testing error handling")
    if include_wrong_tasks:
        print(f"   ⚠️  Using INCORRECT task names for testing error handling")
    
    all_data = []
    
    # Standard variable names matching validation expectations
    if include_wrong_columns:
        # Intentionally wrong column names for testing error handling
        angle_variables = [
            'hip_angle_contra_deg',  # Wrong: should be hip_flexion_angle_contra_rad
            'knee_angle_contra_deg', # Wrong: should be knee_flexion_angle_contra_rad
            'ankle_angle_contra_deg', # Wrong: should be ankle_flexion_angle_contra_rad
            'hip_angle_ipsi_deg',    # Wrong: should be hip_flexion_angle_ipsi_rad
            'knee_angle_ipsi_deg',   # Wrong: should be knee_flexion_angle_ipsi_rad
            'ankle_angle_ipsi_deg'   # Wrong: should be ankle_flexion_angle_ipsi_rad
        ]
    else:
        # Correct variable names matching validation expectations and LocomotionData.ANGLE_FEATURES
        angle_variables = [
            'hip_flexion_angle_contra_rad',
            'knee_flexion_angle_contra_rad', 
            'ankle_flexion_angle_contra_rad',
            'hip_flexion_angle_ipsi_rad',
            'knee_flexion_angle_ipsi_rad',
            'ankle_flexion_angle_ipsi_rad'
        ]
    
    total_steps = 0
    violation_count = 0
    
    for subject in subjects:
        for task in tasks:
            for step in range(steps_per_subject_task):
                # Create realistic gait cycle data
                gait_data = create_realistic_gait_cycle(task)  # Shape: (150, 6)
                
                # Apply validation scenarios (introduce known violations)
                if validation_scenarios and subject in validation_scenarios:
                    scenario = validation_scenarios[subject]
                    if task in scenario and step in scenario[task]:
                        violations = scenario[task][step]
                        for var_idx, violation in violations.items():
                            if var_idx < len(angle_variables):
                                # Set violation value at specific phases
                                violation_phases = violation.get('phases', [0, 37, 75, 112])  # 0%, 25%, 50%, 75%
                                violation_value = violation.get('value', 0.8)
                                
                                for phase_idx in violation_phases:
                                    if 0 <= phase_idx < 150:
                                        gait_data[phase_idx, var_idx] = violation_value
                                        violation_count += 1
                
                # Create DataFrame for this step
                step_data = []
                for phase_idx in range(150):
                    row = {
                        'subject': subject,
                        'task': task,
                        'step': step,
                        'phase_percent': phase_idx * (100/149),  # 0-100%
                        'time': phase_idx * 0.008,  # Approximate time assuming 1.2s gait cycle
                    }
                    
                    # Add joint angle data
                    for var_idx, var_name in enumerate(angle_variables):
                        row[var_name] = gait_data[phase_idx, var_idx]
                    
                    step_data.append(row)
                
                all_data.extend(step_data)
                total_steps += 1
    
    df = pd.DataFrame(all_data)
    
    print(f"✅ Dataset created:")
    print(f"   • Total rows: {len(df):,}")
    print(f"   • Total steps: {total_steps}")
    print(f"   • Columns: {len(df.columns)}")
    print(f"   • Intentional violations: {violation_count}")
    
    return df

def create_validation_scenarios() -> Dict:
    """
    Create validation scenarios with known violations for testing accuracy.
    Uses correct task names that match validation expectations.
    
    Returns:
        Dictionary specifying which steps should have violations
    """
    return {
        'SUB01': {
            'level_walking': {
                0: {  # Step 0 has hip violations
                    0: {'value': 0.8, 'phases': [0, 37, 75, 112]},  # hip_flexion_angle_contra_rad
                },
                1: {  # Step 1 has hip violations  
                    0: {'value': 0.9, 'phases': [0, 37, 75, 112]},  # hip_flexion_angle_contra_rad
                }
            },
            'incline_walking': {
                2: {  # Step 2 has knee violations
                    1: {'value': 1.5, 'phases': [0, 37, 75, 112]},  # knee_flexion_angle_contra_rad
                }
            }
        },
        'SUB02': {
            'decline_walking': {  # Changed from 'running' to 'decline_walking' (valid task name)
                0: {  # Step 0 has ankle violations
                    2: {'value': -0.5, 'phases': [0, 37, 75, 112]},  # ankle_flexion_angle_contra_rad
                },
                3: {  # Step 3 has mixed violations
                    0: {'value': 0.8, 'phases': [0, 37]},  # hip violations at 0%, 25%
                    4: {'value': 1.2, 'phases': [75, 112]},  # knee_ipsi violations at 50%, 75%
                }
            }
        }
    }

def create_test_datasets(output_dir: Path):
    """
    Create multiple test datasets for comprehensive testing.
    
    Args:
        output_dir: Directory to save the parquet files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    subjects = ['SUB01', 'SUB02', 'SUB03']
    
    # Use correct task names that match validation expectations
    # From docs/standard_spec/validation_expectations_kinematic.md:
    # level_walking, incline_walking, decline_walking, up_stairs, down_stairs, run, sit_to_stand, jump, squats
    correct_tasks = ['level_walking', 'incline_walking', 'decline_walking']
    
    # Dataset 1: Clean dataset with no violations (correct format)
    print_banner("Creating Clean Dataset")
    clean_df = create_phase_indexed_dataset(
        subjects=subjects,
        tasks=correct_tasks,
        steps_per_subject_task=3
    )
    
    clean_path = output_dir / "demo_clean_phase.parquet"
    clean_df.to_parquet(clean_path, index=False)
    print(f"✅ Saved: {clean_path}")
    
    # Dataset 2: Dataset with known violations (correct format)
    print_banner("Creating Validation Test Dataset")
    validation_scenarios = create_validation_scenarios()
    
    violation_df = create_phase_indexed_dataset(
        subjects=subjects,
        tasks=correct_tasks,
        steps_per_subject_task=5,
        validation_scenarios=validation_scenarios
    )
    
    violation_path = output_dir / "demo_violations_phase.parquet"
    violation_df.to_parquet(violation_path, index=False)
    print(f"✅ Saved: {violation_path}")
    
    # Dataset 3: Large dataset for performance testing (correct format)
    print_banner("Creating Large Performance Test Dataset")
    large_subjects = [f'SUB{i:02d}' for i in range(1, 6)]  # 5 subjects (reduced for efficiency)
    large_tasks = ['level_walking', 'incline_walking', 'decline_walking', 'squats']
    
    large_df = create_phase_indexed_dataset(
        subjects=large_subjects,
        tasks=large_tasks,
        steps_per_subject_task=4
    )
    
    large_path = output_dir / "demo_large_phase.parquet"
    large_df.to_parquet(large_path, index=False)
    print(f"✅ Saved: {large_path}")
    
    # Dataset 4: EDGE CASE - Wrong column names (should fail validation)
    print_banner("Creating Edge Case Dataset - Wrong Columns")
    wrong_columns_df = create_phase_indexed_dataset(
        subjects=subjects[:2],  # Smaller dataset for error testing
        tasks=correct_tasks[:2],
        steps_per_subject_task=2,
        include_wrong_columns=True
    )
    
    wrong_columns_path = output_dir / "demo_wrong_columns_phase.parquet"
    wrong_columns_df.to_parquet(wrong_columns_path, index=False)
    print(f"✅ Saved: {wrong_columns_path}")
    
    # Dataset 5: EDGE CASE - Wrong task names (should exit gracefully)
    print_banner("Creating Edge Case Dataset - Wrong Tasks")
    wrong_tasks = ['normal_walking', 'uphill_walking', 'jogging']  # These don't match validation expectations
    
    wrong_tasks_df = create_phase_indexed_dataset(
        subjects=subjects[:2],
        tasks=wrong_tasks,
        steps_per_subject_task=2,
        include_wrong_tasks=True
    )
    
    wrong_tasks_path = output_dir / "demo_wrong_tasks_phase.parquet"
    wrong_tasks_df.to_parquet(wrong_tasks_path, index=False)
    print(f"✅ Saved: {wrong_tasks_path}")
    
    return [clean_path, violation_path, large_path, wrong_columns_path, wrong_tasks_path]

def validate_dataset_format(df: pd.DataFrame, dataset_name: str):
    """
    Validate that the dataset format is compatible with LocomotionData library.
    
    Args:
        df: Dataset DataFrame
        dataset_name: Name for reporting
    """
    print(f"\n🔍 Validating format for {dataset_name}:")
    
    # Check required columns
    required_cols = ['subject', 'task', 'step', 'phase_percent']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"   ❌ Missing required columns: {missing_cols}")
    else:
        print(f"   ✅ All required columns present")
    
    # Check angle variables
    angle_vars = [col for col in df.columns if 'angle' in col and 'rad' in col]
    print(f"   📊 Found {len(angle_vars)} angle variables")
    
    # Check step structure
    if 'step' in df.columns:
        step_sizes = df.groupby(['subject', 'task', 'step']).size()
        if step_sizes.nunique() == 1 and step_sizes.iloc[0] == 150:
            print(f"   ✅ All steps have exactly 150 points")
        else:
            print(f"   ⚠️  Step sizes vary: {step_sizes.min()} to {step_sizes.max()}")
    
    # Check phase column
    if 'phase_percent' in df.columns:
        phase_range = (df['phase_percent'].min(), df['phase_percent'].max())
        print(f"   📊 Phase range: {phase_range[0]:.1f}% to {phase_range[1]:.1f}%")
        
        # Check if phases are evenly distributed per step
        sample_step = df[(df['subject'] == df['subject'].iloc[0]) & 
                        (df['task'] == df['task'].iloc[0]) & 
                        (df['step'] == df['step'].iloc[0])]
        if len(sample_step) == 150:
            phase_diff = np.diff(sample_step['phase_percent'].values)
            if np.allclose(phase_diff, phase_diff[0], atol=0.1):
                print(f"   ✅ Phases evenly distributed")
            else:
                print(f"   ⚠️  Phase distribution irregular")

def run_command_line_validator(dataset_path: Path, expected_to_pass: bool) -> Dict[str, any]:
    """
    Run the dataset validator as a command-line script and capture results.
    
    Args:
        dataset_path: Path to the dataset to validate
        expected_to_pass: Whether validation is expected to succeed
        
    Returns:
        Dictionary with validation results and status
    """
    import subprocess
    import sys
    
    # Command to run the validator
    cmd = [
        sys.executable, 
        "source/validation/dataset_validator_phase.py", 
        "--dataset", str(dataset_path)
    ]
    
    result = {
        'dataset': dataset_path.name,
        'expected_to_pass': expected_to_pass,
        'command_succeeded': False,
        'output': '',
        'error': '',
        'validation_report_exists': False,
        'validation_plots_exist': False,
        'report_path': None,
        'plot_paths': []
    }
    
    try:
        # Run the command and capture output
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120  # 2 minute timeout
        )
        
        result['output'] = process.stdout
        result['error'] = process.stderr
        result['command_succeeded'] = (process.returncode == 0)
        
        # Check for generated validation report
        output_dir = project_root / "source/tests/sample_plots/validation_reports" / dataset_path.stem
        report_path = output_dir / f"{dataset_path.stem}_validation_report.md"
        
        if report_path.exists():
            result['validation_report_exists'] = True
            result['report_path'] = str(report_path)
            
            # Check for validation plots
            plot_files = list(output_dir.glob("*_filters_by_phase_with_data.png"))
            if plot_files:
                result['validation_plots_exist'] = True
                result['plot_paths'] = [str(p) for p in plot_files]
        
    except subprocess.TimeoutExpired:
        result['error'] = "Command timed out after 120 seconds"
    except Exception as e:
        result['error'] = str(e)
    
    return result

def verify_validation_outputs(results: List[Dict]) -> Dict[str, any]:
    """
    Verify that validation outputs match expected behavior.
    
    Args:
        results: List of validation results from run_command_line_validator
        
    Returns:
        Dictionary with verification summary
    """
    verification = {
        'all_tests_passed': True,
        'successful_validations': 0,
        'failed_validations': 0,
        'edge_cases_handled': 0,
        'unexpected_behaviors': [],
        'generated_reports': [],
        'generated_plots': []
    }
    
    for result in results:
        dataset_name = result['dataset']
        expected_to_pass = result['expected_to_pass']
        command_succeeded = result['command_succeeded']
        
        if expected_to_pass:
            if command_succeeded and result['validation_report_exists']:
                verification['successful_validations'] += 1
                verification['generated_reports'].append(result['report_path'])
                verification['generated_plots'].extend(result['plot_paths'])
            else:
                verification['all_tests_passed'] = False
                verification['unexpected_behaviors'].append({
                    'dataset': dataset_name,
                    'issue': 'Expected to pass but failed',
                    'error': result['error']
                })
        else:
            # Edge case - should fail gracefully
            # Check both stdout and stderr for validation failure message
            validation_failed = ("VALIDATION FAILED" in result['error'] or 
                               "VALIDATION FAILED" in result['output'])
            
            if not command_succeeded and validation_failed:
                verification['edge_cases_handled'] += 1
            else:
                verification['all_tests_passed'] = False
                verification['unexpected_behaviors'].append({
                    'dataset': dataset_name,
                    'issue': 'Expected to fail gracefully but did not',
                    'output': result['output'][:500] + '...' if len(result['output']) > 500 else result['output'],
                    'error': result['error'][:500] + '...' if len(result['error']) > 500 else result['error'],
                    'command_succeeded': command_succeeded,
                    'has_validation_failed': validation_failed
                })
    
    verification['failed_validations'] = len([r for r in results if not r['expected_to_pass']])
    
    return verification

def demo_dataset_validator_integration(test_datasets: List[Path]) -> Dict[str, any]:
    """
    Test integration with dataset_validator_phase.py by running it as a command-line tool.
    
    Args:
        test_datasets: List of paths to test datasets
        
    Returns:
        Dictionary with comprehensive test results
    """
    print_banner("Testing Command-Line Dataset Validator Integration")
    
    # Define expected behavior for each dataset
    dataset_expectations = {
        'demo_clean_phase.parquet': True,      # Should pass
        'demo_violations_phase.parquet': True, # Should pass (with violations detected)
        'demo_large_phase.parquet': True,     # Should pass (performance test)
        'demo_wrong_columns_phase.parquet': False, # Should fail - wrong columns
        'demo_wrong_tasks_phase.parquet': False,   # Should fail - wrong tasks
    }
    
    print(f"🧪 Testing {len(test_datasets)} datasets with command-line validator...")
    
    # Run validation for each dataset
    results = []
    for dataset_path in test_datasets:
        dataset_name = dataset_path.name
        expected_to_pass = dataset_expectations.get(dataset_name, True)
        
        print(f"\n📊 Testing: {dataset_name}")
        print(f"   Expected: {'✅ Should pass' if expected_to_pass else '❌ Should fail gracefully'}")
        
        result = run_command_line_validator(dataset_path, expected_to_pass)
        results.append(result)
        
        # Print immediate feedback
        if expected_to_pass:
            if result['command_succeeded'] and result['validation_report_exists']:
                print(f"   ✅ SUCCESS: Validation completed, report generated")
                print(f"   📄 Report: {Path(result['report_path']).name}")
                if result['plot_paths']:
                    print(f"   📊 Plots: {len(result['plot_paths'])} generated")
            else:
                print(f"   ❌ FAILED: {result['error'][:100]}...")
        else:
            if not result['command_succeeded'] and "VALIDATION FAILED" in result['error']:
                print(f"   ✅ EXPECTED FAILURE: Failed gracefully as expected")
            else:
                print(f"   ❌ UNEXPECTED: Should have failed but didn't")
    
    # Verify all results
    print_banner("Verification Summary")
    verification = verify_validation_outputs(results)
    
    return {
        'results': results,
        'verification': verification
    }

def create_expected_failures_report(validation_scenarios: Dict, output_dir: Path):
    """
    Create a report documenting expected validation failures for accuracy testing.
    
    Args:
        validation_scenarios: Scenarios with intentional violations
        output_dir: Directory to save the report
    """
    report_content = """# Expected Validation Failures Report

## Purpose
This report documents the intentional violations introduced in the demo datasets
for testing the accuracy of the dataset_validator_phase.py system.

## Validation Scenarios

"""
    
    total_expected = 0
    
    for subject, subject_scenarios in validation_scenarios.items():
        report_content += f"### Subject: {subject}\n\n"
        
        for task, task_scenarios in subject_scenarios.items():
            report_content += f"#### Task: {task}\n\n"
            
            for step, step_violations in task_scenarios.items():
                report_content += f"**Step {step}:**\n"
                
                for var_idx, violation in step_violations.items():
                    # Map variable index to name
                    var_names = [
                        'hip_flexion_angle_contra_rad',
                        'knee_flexion_angle_contra_rad', 
                        'ankle_flexion_angle_contra_rad',
                        'hip_flexion_angle_ipsi_rad',
                        'knee_flexion_angle_ipsi_rad',
                        'ankle_flexion_angle_ipsi_rad'
                    ]
                    
                    var_name = var_names[var_idx] if var_idx < len(var_names) else f"Variable_{var_idx}"
                    value = violation.get('value', 'N/A')
                    phases = violation.get('phases', [])
                    
                    report_content += f"- `{var_name}`: Set to {value} rad at phases {phases}\n"
                    
                    # Count expected failures (efficient approach: 1 per phase)
                    total_expected += len(phases)
                
                report_content += "\n"
    
    report_content += f"""
## Expected Validation Results

### Efficient Validation Approach
The validation system uses representative phase validation, checking only key phases
(0%, 25%, 50%, 75%) rather than all 150 points per gait cycle.

### Total Expected Failures
Based on the scenarios above, the validation system should detect approximately
**{total_expected}** validation failures when using the efficient approach.

### Accuracy Testing
When running dataset_validator_phase.py on the demo_violations_phase.parquet dataset,
the number of detected failures should match this expected count for 100% accuracy.

---
*Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by demo_dataset_validator_phase.py*
"""
    
    report_path = output_dir / "expected_failures_report.md"
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    print(f"📄 Expected failures report saved: {report_path}")
    return total_expected

def main():
    """Run the complete demo dataset generation and testing workflow."""
    print("🎯 Demo Dataset Generator for dataset_validator_phase.py")
    print("="*60)
    print("This script creates test datasets and validates the dataset_validator_phase.py command-line tool")
    
    # Create output directory
    output_dir = Path(__file__).parent / "test_data"
    
    # Clean up previous validation reports
    validation_reports_dir = Path(__file__).parent / "sample_plots" / "validation_reports"
    if validation_reports_dir.exists():
        import shutil
        shutil.rmtree(validation_reports_dir)
        print("🧹 Cleaned up previous validation reports")
    
    # Generate test datasets
    print_banner("Generating Test Datasets")
    test_datasets = create_test_datasets(output_dir)
    
    # Validate dataset formats
    print_banner("Validating Dataset Formats")
    for dataset_path in test_datasets:
        df = pd.read_parquet(dataset_path)
        validate_dataset_format(df, dataset_path.name)
    
    # Create expected failures report
    print_banner("Creating Expected Failures Report")
    validation_scenarios = create_validation_scenarios()
    expected_failures = create_expected_failures_report(validation_scenarios, output_dir)
    
    # Test integration with dataset_validator_phase.py command-line tool
    integration_results = demo_dataset_validator_integration(test_datasets)
    
    # Final status report
    print_banner("Final Test Results")
    verification = integration_results['verification']
    
    if verification['all_tests_passed']:
        print("✅ Working as expected! Check out the reports here:")
        print(f"\n📊 Successfully validated {verification['successful_validations']} datasets")
        print(f"🚫 Properly handled {verification['edge_cases_handled']} edge cases")
        
        print(f"\n📄 Generated validation reports:")
        for report_path in verification['generated_reports']:
            print(f"   • {Path(report_path).relative_to(Path.cwd())}")
        
        print(f"\n📈 Generated validation plots:")
        plot_count_by_dataset = {}
        for plot_path in verification['generated_plots']:
            dataset_name = Path(plot_path).parent.name
            plot_count_by_dataset[dataset_name] = plot_count_by_dataset.get(dataset_name, 0) + 1
        
        for dataset, count in plot_count_by_dataset.items():
            print(f"   • {dataset}: {count} plots")
        
        print(f"\n📂 All outputs saved in: source/tests/sample_plots/validation_reports/")
        
        return True
        
    else:
        print("❌ Not working as expected! Here are the errors:")
        
        for behavior in verification['unexpected_behaviors']:
            print(f"\n🐛 Issue with {behavior['dataset']}:")
            print(f"   Problem: {behavior['issue']}")
            if 'error' in behavior:
                print(f"   Error: {behavior['error'][:200]}...")
        
        print(f"\n📊 Test Summary:")
        print(f"   • Successful validations: {verification['successful_validations']}")
        print(f"   • Edge cases handled: {verification['edge_cases_handled']}")
        print(f"   • Unexpected behaviors: {len(verification['unexpected_behaviors'])}")
        
        if verification['generated_plots']:
            print(f"\n📈 Plots that were generated:")
            for plot_path in verification['generated_plots']:
                print(f"   • {Path(plot_path).relative_to(Path.cwd())}")
        
        return False

if __name__ == "__main__":
    main()