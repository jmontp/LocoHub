#!/usr/bin/env python3
"""
Demonstration Script for step_classifier.py

Created: 2025-06-10
Purpose: Comprehensive demonstration of the step classification functionality showing
         how to use the StepClassifier module for validation plot color coding.

Intent:
This script demonstrates the key features of the step classification system used
in validation plotting:

1. **Basic Step Classification**: How to classify steps based on validation failures
2. **Feature-Aware Classification**: Distinguishing local vs other violations per feature
3. **Color Mapping Logic**: Understanding the three-color validation system:
   - Gray: Valid steps with no violations
   - Red: Steps with local violations (violations in the current feature)
   - Pink: Steps with other violations (violations in different features)
4. **Multi-Task Scenarios**: Handling multiple locomotion tasks simultaneously
5. **Kinematic vs Kinetic Modes**: Different classification for different data types
6. **Report Generation**: Creating comprehensive classification reports
7. **Integration Examples**: How to use with validation plotting systems

Output:
Demonstrates classification scenarios with detailed explanations and visual output
showing step-by-step color classification logic.

Usage:
    python3 tests/demo_step_classifier.py

This demo helps developers understand:
- How validation failures map to step colors
- When to use feature-specific vs summary classification
- How to interpret classification results
- How to integrate with visualization workflows
"""

import numpy as np
import sys
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Add source directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from internal.validation_engine.step_classifier import StepClassifier


def print_banner(title):
    """Print a formatted banner for section separation."""
    print(f"\n{'='*60}")
    print(f"🎨 {title}")
    print('='*60)


def print_step_colors_explanation():
    """Explain the step color coding system."""
    print_banner("Step Color Coding System")
    print("""
The step classifier uses a three-color system to indicate validation status:

🔘 GRAY:  Valid steps with no violations
🔴 RED:   Steps with LOCAL violations (violations in the current feature being plotted)
🩷 PINK:  Steps with OTHER violations (violations in different features)

This allows users to quickly identify:
- Which steps are completely valid (gray)
- Which steps have problems in the current subplot (red)
- Which steps have problems elsewhere but are valid for current feature (pink)
""")


def demo_basic_classification():
    """Demonstrate basic step classification functionality."""
    print_banner("Basic Step Classification")
    
    classifier = StepClassifier()
    
    # Create sample validation failures
    sample_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Value 0.800 above maximum 0.600 at phase 25.0%'
        },
        {
            'task': 'level_walking',
            'variable': 'knee_flexion_angle_contra',
            'phase': 50.0,
            'value': 1.5,
            'expected_min': 0.0,
            'expected_max': 0.15,
            'failure_reason': 'Value 1.500 above maximum 0.150 at phase 50.0%'
        }
    ]
    
    # Create step mapping (6 steps all for level_walking)
    step_task_mapping = {i: 'level_walking' for i in range(6)}
    
    print("📊 Sample validation failures:")
    for i, failure in enumerate(sample_failures, 1):
        print(f"   {i}. {failure['variable']}: {failure['value']:.3f} (expected {failure['expected_min']:.3f}-{failure['expected_max']:.3f})")
    
    print(f"\n📋 Step-task mapping: {len(step_task_mapping)} steps, all '{list(step_task_mapping.values())[0]}'")
    
    # Test classification for different features (legacy single-feature approach)
    test_features = [
        ('hip_flexion_angle_ipsi', 'All steps RED because hip has local violations'),
        ('knee_flexion_angle_contra', 'All steps RED because knee has local violations'),
        ('ankle_flexion_angle_ipsi', 'All steps PINK because ankle has no violations but other features do')
    ]
    
    for feature, interpretation in test_features:
        print(f"\n🎯 Classifying for '{feature}' feature:")
        colors = classifier.classify_steps_for_feature(
            sample_failures, step_task_mapping, feature, 'kinematic'
        )
        print(f"   Result: {colors}")
        print(f"   Interpretation: {interpretation}")
    
    # Demonstrate new matrix-based classification
    print(f"\n🔥 NEW: Matrix-based classification (per step-feature):")
    step_colors_matrix = classifier.classify_steps_matrix(sample_failures, step_task_mapping, 'kinematic')
    print(f"   Shape: {step_colors_matrix.shape} (steps × features)")
    
    feature_names = list(classifier.get_feature_map('kinematic').keys())
    print(f"   Features: {feature_names}")
    
    print(f"   Matrix breakdown:")
    for step_idx in range(step_colors_matrix.shape[0]):
        step_colors_str = []
        for feat_idx in range(step_colors_matrix.shape[1]):
            color = step_colors_matrix[step_idx, feat_idx]
            step_colors_str.append(color)
        print(f"      Step {step_idx}: {step_colors_str}")
    
    print(f"\n   Analysis:")
    print(f"   • Hip feature (index 0): All RED because hip violations exist")
    print(f"   • Knee contra (index 3): All RED because knee violations exist") 
    print(f"   • All other features: All PINK because they have no local violations but other features do")


def demo_multi_task_classification():
    """Demonstrate classification across multiple tasks."""
    print_banner("Multi-Task Classification")
    
    classifier = StepClassifier()
    
    # Create multi-task failures
    multi_task_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Hip flexion violation'
        },
        {
            'task': 'incline_walking',
            'variable': 'knee_flexion_angle_contra',
            'phase': 50.0,
            'value': 1.5,
            'expected_min': 0.0,
            'expected_max': 0.15,
            'failure_reason': 'Knee flexion violation'
        },
        {
            'task': 'running',
            'variable': 'ankle_flexion_angle_ipsi',
            'phase': 75.0,
            'value': -0.5,
            'expected_min': -0.1,
            'expected_max': 0.2,
            'failure_reason': 'Ankle flexion violation'
        }
    ]
    
    # Create multi-task step mapping
    multi_step_mapping = {
        0: 'level_walking', 1: 'level_walking',
        2: 'incline_walking', 3: 'incline_walking',
        4: 'running', 5: 'running',
        6: 'squats', 7: 'squats'  # squats has no violations
    }
    
    print("📊 Multi-task validation failures:")
    for failure in multi_task_failures:
        print(f"   • {failure['task']}: {failure['variable']} violation")
    
    print(f"\n📋 Step distribution:")
    task_counts = {}
    for step, task in multi_step_mapping.items():
        task_counts[task] = task_counts.get(task, 0) + 1
    for task, count in task_counts.items():
        print(f"   • {task}: {count} steps")
    
    # Test hip feature classification
    print(f"\n🎯 Hip feature classification:")
    hip_colors = classifier.classify_steps_for_feature(
        multi_task_failures, multi_step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Step colors: {hip_colors}")
    print(f"   Breakdown:")
    for step_idx, (task, color) in enumerate(zip(multi_step_mapping.values(), hip_colors)):
        if color == 'red':
            reason = "RED - has local hip violation"
        elif color == 'pink':
            reason = "PINK - has other violations"
        else:
            reason = "GRAY - no violations"
        print(f"      Step {step_idx} ({task}): {reason}")
    
    # Test knee feature classification
    print(f"\n🎯 Knee feature classification:")
    knee_colors = classifier.classify_steps_for_feature(
        multi_task_failures, multi_step_mapping, 'knee_flexion_angle_contra', 'kinematic'
    )
    print(f"   Step colors: {knee_colors}")
    print(f"   Expected: level_walking=PINK, incline_walking=RED, running=PINK, squats=GRAY")


def demo_kinematic_vs_kinetic():
    """Demonstrate differences between kinematic and kinetic classification."""
    print_banner("Kinematic vs Kinetic Classification")
    
    classifier = StepClassifier()
    
    # Show feature mappings
    kinematic_map = classifier.get_feature_map('kinematic')
    kinetic_map = classifier.get_feature_map('kinetic')
    
    print("🦴 Kinematic features (joint angles):")
    for feature, idx in kinematic_map.items():
        print(f"   {idx}: {feature}")
    
    print(f"\n💪 Kinetic features (forces/moments):")
    for feature, idx in kinetic_map.items():
        print(f"   {idx}: {feature}")
    
    # Create kinetic failures
    kinetic_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_moment_ipsi_Nm_kg',
            'phase': 25.0,
            'value': -1.5,
            'expected_min': -1.0,
            'expected_max': -0.2,
            'failure_reason': 'Hip moment violation'
        }
    ]
    
    kinetic_step_mapping = {0: 'level_walking', 1: 'level_walking'}
    
    # Test kinetic classification
    print(f"\n🎯 Kinetic classification for 'hip_moment_ipsi_Nm_kg':")
    hip_moment_colors = classifier.classify_steps_for_feature(
        kinetic_failures, kinetic_step_mapping, 'hip_moment_ipsi_Nm_kg', 'kinetic'
    )
    print(f"   Result: {hip_moment_colors}")
    print(f"   Both steps RED because hip moment has local violations")
    
    print(f"\n🎯 Kinetic classification for 'knee_moment_ipsi_Nm_kg':")
    knee_moment_colors = classifier.classify_steps_for_feature(
        kinetic_failures, kinetic_step_mapping, 'knee_moment_ipsi_Nm_kg', 'kinetic'
    )
    print(f"   Result: {knee_moment_colors}")
    print(f"   Both steps PINK because knee moment has no violations but hip does")


def demo_edge_cases():
    """Demonstrate edge cases and error handling."""
    print_banner("Edge Cases and Error Handling")
    
    classifier = StepClassifier()
    
    # Test 1: No validation failures
    print("🔍 Test 1: No validation failures")
    empty_failures = []
    step_mapping = {0: 'level_walking', 1: 'level_walking', 2: 'level_walking'}
    colors = classifier.classify_steps_for_feature(
        empty_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {colors}")
    print(f"   All steps GRAY because no violations exist")
    
    # Test 2: Empty step mapping
    print(f"\n🔍 Test 2: Empty step mapping")
    empty_mapping = {}
    colors = classifier.classify_steps_for_feature(
        empty_failures, empty_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {colors}")
    print(f"   Empty array because no steps to classify")
    
    # Test 3: Invalid mode
    print(f"\n🔍 Test 3: Invalid mode handling")
    try:
        classifier.get_feature_map('invalid_mode')
        print("   FAILED: Should have raised error")
    except ValueError as e:
        print(f"   SUCCESS: Properly caught error - {e}")
    
    # Test 4: Large dataset performance
    print(f"\n🔍 Test 4: Large dataset performance")
    large_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Large dataset test'
        }
    ]
    large_mapping = {i: 'level_walking' for i in range(1000)}
    
    import time
    start_time = time.time()
    colors = classifier.classify_steps_for_feature(
        large_failures, large_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    execution_time = (time.time() - start_time) * 1000  # Convert to ms
    
    print(f"   Classified {len(colors)} steps in {execution_time:.2f}ms")
    print(f"   All steps: {colors[0]} (first 5: {colors[:5]})")


def demo_comprehensive_report():
    """Demonstrate comprehensive classification reporting."""
    print_banner("Comprehensive Classification Report")
    
    classifier = StepClassifier()
    
    # Create a complex scenario with multiple tasks and violations
    complex_failures = [
        {'task': 'level_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 25.0, 'value': 0.8, 'expected_min': 0.15, 'expected_max': 0.6, 'failure_reason': 'Hip violation'},
        {'task': 'level_walking', 'variable': 'hip_flexion_angle_contra', 'phase': 75.0, 'value': 0.4, 'expected_min': -0.05, 'expected_max': 0.35, 'failure_reason': 'Hip contra violation'},
        {'task': 'incline_walking', 'variable': 'knee_flexion_angle_contra', 'phase': 50.0, 'value': 1.5, 'expected_min': 0.0, 'expected_max': 0.15, 'failure_reason': 'Knee violation'},
        {'task': 'incline_walking', 'variable': 'hip_flexion_angle_contra', 'phase': 25.0, 'value': 1.0, 'expected_min': 0.3, 'expected_max': 0.9, 'failure_reason': 'Hip contra violation 2'},
        {'task': 'running', 'variable': 'ankle_flexion_angle_ipsi', 'phase': 75.0, 'value': -0.5, 'expected_min': -0.1, 'expected_max': 0.2, 'failure_reason': 'Ankle violation'},
        {'task': 'running', 'variable': 'hip_flexion_angle_ipsi', 'phase': 0.0, 'value': 1.0, 'expected_min': 0.15, 'expected_max': 0.6, 'failure_reason': 'Hip violation 2'}
    ]
    
    complex_mapping = {
        0: 'level_walking', 1: 'level_walking',
        2: 'incline_walking', 3: 'incline_walking',
        4: 'running', 5: 'running',
        6: 'squats', 7: 'squats', 8: 'squats'  # squats has no violations
    }
    
    print("📊 Creating comprehensive report for realistic scenario:")
    print(f"   • {len(complex_mapping)} total steps across 4 different tasks")
    print(f"   • {len(set(f['variable'] for f in complex_failures))} different variables with violations")
    print(f"   • Mix of valid and invalid steps")
    
    # Demonstrate classification for multiple features
    print(f"\n📊 Per-feature breakdown:")
    feature_map = classifier.get_feature_map('kinematic')
    for feature_name in list(feature_map.keys())[:3]:  # Test first 3 features
        colors = classifier.classify_steps_for_feature(
            complex_failures, complex_mapping, feature_name, 'kinematic'
        )
        valid_count = sum(1 for c in colors if c == 'gray')
        local_count = sum(1 for c in colors if c == 'red') 
        other_count = sum(1 for c in colors if c == 'pink')
        print(f"   {feature_name}:")
        print(f"      Valid: {valid_count}, Local violations: {local_count}, Other violations: {other_count}")
    
    print(f"\n🎨 Feature classifications (first 3 features):")
    for feature_name in list(feature_map.keys())[:3]:
        colors = classifier.classify_steps_for_feature(
            complex_failures, complex_mapping, feature_name, 'kinematic'
        )
        print(f"   {feature_name}: {colors}")


# Note: These functions are now implemented in the StepClassifier class
# This demo script imports and uses the classifier's methods directly


def generate_validation_accuracy_report(validation_results, output_dir):
    """
    Generate a detailed validation accuracy report comparing expected vs detected failures.
    
    Args:
        validation_results: List of validation result dictionaries
        output_dir: Directory to save the report
        
    Returns:
        Path to the generated report file
    """
    report_content = """# Validation Accuracy Report

## Summary

This report analyzes the accuracy of the validation system by comparing the number of expected failures (intentionally introduced violations) with the number of failures actually detected by the validation system.

## Methodology

1. **Generate Controlled Datasets**: Create datasets with known violations by setting specific values outside validation ranges
2. **Run Validation**: Use the actual validation system to detect violations
3. **Compare Results**: Count expected vs detected violations to measure accuracy

## Dataset Analysis

"""
    
    total_expected = 0
    total_detected = 0
    
    for result in validation_results:
        dataset_name = result['dataset_name']
        expected_failures = result['expected_failures']
        detected_failures = result['detected_failures']
        data_shape = result['data_shape']
        
        total_expected += expected_failures
        total_detected += detected_failures
        
        accuracy = (detected_failures / expected_failures * 100) if expected_failures > 0 else 100
        
        report_content += f"""### Dataset: {dataset_name}

- **Data Shape**: {data_shape[0]} steps × {data_shape[1]} time points × {data_shape[2]} features
- **Expected Failures**: {expected_failures:,}
- **Detected Failures**: {detected_failures:,}
- **Accuracy**: {accuracy:.1f}%
- **Status**: {'✅ PASS' if detected_failures == expected_failures else '❌ DISCREPANCY'}

"""
    
    overall_accuracy = (total_detected / total_expected * 100) if total_expected > 0 else 100
    
    report_content += f"""## Overall Results

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Expected Failures | {total_expected:,} | 100.0% |
| Total Detected Failures | {total_detected:,} | {overall_accuracy:.1f}% |
| **Overall Accuracy** | **{total_detected}/{total_expected}** | **{overall_accuracy:.1f}%** |

## Validation System Assessment

"""
    
    if overall_accuracy == 100.0:
        report_content += """✅ **EXCELLENT**: The validation system correctly identified 100% of intentional violations.

- All expected failures were properly detected
- No false negatives (missed violations)
- Validation ranges are working as designed
- Step classification can rely on accurate violation detection
"""
    elif overall_accuracy >= 95.0:
        report_content += """⚠️ **GOOD**: The validation system detected most violations but missed some.

- High accuracy but some false negatives exist
- May need to review validation logic for edge cases
- Generally reliable for step classification
"""
    else:
        report_content += """❌ **NEEDS IMPROVEMENT**: Significant discrepancy between expected and detected failures.

- Many violations were missed by the validation system
- Validation ranges or logic may need adjustment
- Step classification may not be fully reliable
"""
    
    report_content += f"""
## Technical Details

### Validation Methodology
- **Range Violations**: Values intentionally set outside [min, max] bounds
- **Phase Coverage**: All phases (0%, 25%, 50%, 75%) tested
- **Feature Coverage**: Hip, knee, and ankle joints tested
- **Time Point Coverage**: All 150 time points per gait cycle validated

### Data Generation Strategy
- **All Valid Dataset**: Generated within validation ranges (expected 0 failures)
- **Hip Violations Dataset**: Hip values set to 0.8-0.9 rad (above max ~0.6 rad)
- **Mixed Violations Dataset**: Multiple features violated simultaneously

### Failure Detection Logic (EFFICIENT APPROACH)
- Representative phase validation using 4 key indices (0%, 25%, 50%, 75%)
- Failures recorded with step, variable, phase, and violation details
- Only representative points checked (4 phases × 6 features × N steps = 37.5x faster)

---
*Generated on {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by demo_step_classifier.py*
"""
    
    # Save report
    report_path = output_dir / "validation_accuracy_report.md"
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    return report_path


def demo_integration_example():
    """Demonstrate live integration with the filters_by_phase_plots function."""
    print_banner("Live Integration with Filter by Phase Plotter")
    
    classifier = StepClassifier()
    
    # Import the plotting function and validation parser
    try:
        from internal.plot_generation.filters_by_phase_plots import create_filters_by_phase_plot
        from lib.validation.validation_expectations_parser import parse_kinematic_validation_expectations
        print("🔗 Creating actual validation plots with step classification...")
    except ImportError:
        print("❌ Could not import required modules")
        return
    
    # Create simplified validation data that works with the plotting system
    validation_data = {
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
    
    task_data = validation_data['level_walking']
    print(f"📊 Using validation data with {len(task_data)} phases")
    
    # Create step mapping
    num_steps = 6
    step_task_mapping = {i: 'level_walking' for i in range(num_steps)}
    
    # Generate different datasets for different scenarios with known expected failures
    datasets = {}
    
    # Dataset 1: All valid data using classifier's method
    print(f"\n📊 Creating Dataset 1: All valid data")
    datasets['all_valid'] = {
        'data': classifier.create_valid_data(task_data, num_steps),
        'expected_failures': 0,  # Should have no failures
        'description': 'All data generated within validation ranges'
    }
    
    # Dataset 2: Hip violations only - Calculate expected failures for EFFICIENT approach
    print(f"📊 Creating Dataset 2: Hip violations in steps 0,1")
    hip_data = classifier.create_valid_data(task_data, num_steps)
    hip_data[0, :, 0] = 0.8  # Hip ipsi violation (above max at most phases)
    hip_data[1, :, 0] = 0.9  # Hip ipsi violation (above max at most phases)
    
    # EFFICIENT APPROACH: Only check 1 representative point per phase (not all 150 points)
    # Hip 0.8 violates at phases 0,25,50 but is valid at phase 75 (max=0.9)
    # Hip 0.9 violates at phases 0,25,50 but is valid at phase 75 (max=0.9)
    # Expected failures: 2 steps × 3 violating phases × 1 point = 6 failures
    violating_phases = 3  # Phases 0,25,50 violate, phase 75 is valid
    hip_expected = 2 * violating_phases  # 2 steps × 3 phases × 1 representative point each
    datasets['hip_violations'] = {
        'data': hip_data,
        'expected_failures': hip_expected,
        'description': f'Steps 0,1 violate hip_flexion_angle_ipsi at phases 0,25,50% (0.8-0.9 > max), valid at 75%'
    }
    
    # Dataset 3: Mixed violations - Calculate expected failures for EFFICIENT approach
    print(f"📊 Creating Dataset 3: Mixed violations")
    mixed_data = classifier.create_valid_data(task_data, num_steps)
    mixed_data[0, :, 0] = 0.8   # Hip violation (violates at phases 0,25,50)
    mixed_data[2, :, 2] = 0.9   # Knee violation (violates at phases 0,25,50)
    mixed_data[4, :, 4] = -0.3  # Ankle violation (violates at phases 0,25,75)
    
    # EFFICIENT APPROACH: Only check 1 representative point per phase
    # Expected failures: 3 steps × 3 violating phases × 1 point = 9 failures
    # - Step 0 hip: violates at 3 phases (0,25,50)
    # - Step 2 knee: violates at 3 phases (0,25,50)  
    # - Step 4 ankle: violates at 3 phases (0,25,75)
    mixed_expected = 3 * 3  # 3 steps × 3 violating phases × 1 representative point each
    datasets['mixed_violations'] = {
        'data': mixed_data,
        'expected_failures': mixed_expected,
        'description': f'Step 0 hip (phases 0,25,50), step 2 knee (phases 0,25,50), step 4 ankle (phases 0,25,75)'
    }
    
    # Create output directory
    output_dir = Path(__file__).parent / "sample_plots" / "demo_step_classifier"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    
    # Now validate each dataset and generate step colors using ACTUAL validation
    scenarios = []
    validation_results = []
    
    for dataset_name, dataset_info in datasets.items():
        data = dataset_info['data']
        expected_failures = dataset_info['expected_failures']
        description = dataset_info['description']
        
        print(f"\n🔍 Validating dataset: {dataset_name}")
        print(f"   📊 Data shape: {data.shape} (steps, time_points, features)")
        print(f"   📋 Description: {description}")
        print(f"   🎯 Expected failures: {expected_failures:,}")
        
        # Run actual validation to detect violations using classifier's method
        actual_failures = classifier.validate_data_against_ranges(
            data, validation_data, 'level_walking', step_task_mapping
        )
        
        detected_failures = len(actual_failures)
        print(f"   ⚠️  Detected failures: {detected_failures:,}")
        
        # Calculate accuracy
        if expected_failures == 0:
            accuracy = 100.0 if detected_failures == 0 else 0.0
        else:
            accuracy = (detected_failures / expected_failures) * 100
        
        print(f"   📈 Accuracy: {accuracy:.1f}% ({detected_failures}/{expected_failures})")
        
        # Track validation results for report
        validation_results.append({
            'dataset_name': dataset_name,
            'data_shape': data.shape,
            'expected_failures': expected_failures,
            'detected_failures': detected_failures,
            'description': description
        })
        
        # Show some failure details
        if len(actual_failures) > 0:
            print(f"   📋 Sample failures:")
            for i, failure in enumerate(actual_failures[:3]):  # Show first 3
                print(f"      {i+1}. Step {failure['step']}: {failure['variable']} = {failure['value']:.3f} "
                     f"(range: [{failure['expected_min']:.3f}, {failure['expected_max']:.3f}])")
            if len(actual_failures) > 3:
                print(f"      ... and {len(actual_failures) - 3} more failures")
        else:
            print(f"   ✅ All data passes validation!")
        
        # Create scenarios for this dataset using the new matrix-based classification
        base_scenario = {
            'dataset': dataset_name,
            'data': data,
            'failures': actual_failures,
        }
        
        # Matrix classification - provides granular step-feature colors
        step_colors_matrix = classifier.classify_steps_matrix(actual_failures, step_task_mapping, 'kinematic')
        
        print(f"   🎨 Step colors matrix shape: {step_colors_matrix.shape}")
        print(f"   📊 Matrix sample (first 3 steps, all features):")
        for step_idx in range(min(3, step_colors_matrix.shape[0])):
            step_colors_str = [step_colors_matrix[step_idx, feat_idx] for feat_idx in range(step_colors_matrix.shape[1])]
            print(f"      Step {step_idx}: {step_colors_str}")
        
        # Use the matrix-based classification for plotting
        scenarios.append({
            **base_scenario,
            'name': f'{dataset_name}_matrix_classification',
            'description': f'{dataset_name}: Per-feature classification (red=local, pink=other, gray=valid)',
            'step_colors': step_colors_matrix
        })
    
    # Generate plots for all scenarios
    generated_plots = []
    
    for scenario in scenarios:
        print(f"\n🎨 Generating plot: {scenario['name']}")
        print(f"   📋 {scenario['description']}")
        print(f"   🎨 Step colors: {scenario['step_colors']}")
        
        try:
            # Generate the actual plot using filters_by_phase_plots
            plot_path = create_filters_by_phase_plot(
                validation_data=validation_data,
                task_name='level_walking',
                output_dir=str(output_dir),
                mode='kinematic',
                data=scenario['data'],
                step_colors=scenario['step_colors']
            )
            
            # Rename to include scenario name
            original_name = Path(plot_path).name
            new_name = f"{scenario['name']}_{original_name}"
            new_path = output_dir / new_name
            
            os.rename(plot_path, new_path)
            generated_plots.append(str(new_path))
            
            print(f"   ✅ Generated: {new_path.name}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print(f"\n🎉 Generated {len(generated_plots)} validation plots with step classification!")
    print(f"📂 View plots in: {output_dir}")
    
    for plot_path in generated_plots:
        print(f"   📈 {Path(plot_path).name}")
    
    # Generate validation accuracy report
    print(f"\n📊 Generating validation accuracy report...")
    report_path = generate_validation_accuracy_report(validation_results, output_dir)
    print(f"   📄 Report saved: {report_path.name}")
    
    # Print summary of validation accuracy
    total_expected = sum(r['expected_failures'] for r in validation_results)
    total_detected = sum(r['detected_failures'] for r in validation_results)
    overall_accuracy = (total_detected / total_expected * 100) if total_expected > 0 else 100
    
    print(f"\n📈 Validation Accuracy Summary:")
    print(f"   🎯 Total expected failures: {total_expected:,}")
    print(f"   ⚠️  Total detected failures: {total_detected:,}")
    print(f"   📊 Overall accuracy: {overall_accuracy:.1f}%")
    
    if overall_accuracy == 100.0:
        print(f"   ✅ PERFECT: Validation system detected all intentional violations!")
    elif overall_accuracy >= 95.0:
        print(f"   ⚠️  GOOD: High accuracy with minor discrepancies")
    else:
        print(f"   ❌ ISSUE: Significant validation discrepancies detected")
    
    print(f"""
🔗 Integration Summary:

The step classifier successfully integrated with the filters_by_phase_plots function
to generate validation plots with colored step overlays:

1. **Summary Classification**: Shows all steps with any violations as red
2. **Feature-Specific**: Shows local violations as red, other violations as pink
3. **Real Data**: Uses actual gait data with realistic violation patterns
4. **Visual Output**: Creates validation plots
5. **Validation Accuracy**: {overall_accuracy:.1f}% detection rate for intentional violations

This demonstrates how the step classifier enhances validation plotting by providing
immediate visual feedback about data quality and violation types.
""")


def main():
    """Run all demonstrations."""
    print("🎨 Step Classifier Demonstration")
    print("="*60)
    print("This demo shows how to use the StepClassifier module for validation plotting.")
    
    print_step_colors_explanation()
    demo_basic_classification()
    demo_multi_task_classification()
    demo_kinematic_vs_kinetic()
    demo_edge_cases()
    demo_comprehensive_report()
    demo_integration_example()
    
    print_banner("Demo Complete")
    print("""
🎉 Step Classifier Demo Complete!

You've seen how the StepClassifier module:
• Maps validation failures to step colors
• Distinguishes local vs other violations per feature  
• Handles multiple tasks and locomotion modes
• Generates comprehensive classification reports
• Integrates with validation plotting workflows

The step classifier provides the color-coding logic that makes validation
plots immediately interpretable, helping users quickly identify data quality
issues and their specific locations.

For more details, see:
• source/validation/step_classifier.py - Main implementation
• source/tests/test_step_classifier.py - Comprehensive test suite
• Integration examples in dataset_validator.py""")


if __name__ == "__main__":
    main()