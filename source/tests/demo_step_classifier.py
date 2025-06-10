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
    python3 source/tests/demo_step_classifier.py

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
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source'))

from validation.step_classifier import StepClassifier


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
    
    # Create step mapping (6 steps, all level_walking)
    step_task_mapping = {i: 'level_walking' for i in range(6)}
    
    print("📊 Sample validation failures:")
    for i, failure in enumerate(sample_failures):
        print(f"   {i+1}. {failure['variable']}: {failure['value']:.3f} (expected {failure['expected_min']:.3f}-{failure['expected_max']:.3f})")
    
    print(f"\n📋 Step-task mapping: {len(step_task_mapping)} steps, all 'level_walking'")
    
    # Classify for hip feature (should be red since hip has violations)
    print(f"\n🎯 Classifying for 'hip_flexion_angle_ipsi' feature:")
    hip_colors = classifier.classify_steps_for_feature(
        sample_failures, step_task_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {hip_colors}")
    print(f"   Interpretation: All steps RED because hip has local violations")
    
    # Classify for knee feature (should be red since knee has violations)
    print(f"\n🎯 Classifying for 'knee_flexion_angle_contra' feature:")
    knee_colors = classifier.classify_steps_for_feature(
        sample_failures, step_task_mapping, 'knee_flexion_angle_contra', 'kinematic'
    )
    print(f"   Result: {knee_colors}")
    print(f"   Interpretation: All steps RED because knee has local violations")
    
    # Classify for ankle feature (should be pink since ankle has no violations but others do)
    print(f"\n🎯 Classifying for 'ankle_flexion_angle_ipsi' feature:")
    ankle_colors = classifier.classify_steps_for_feature(
        sample_failures, step_task_mapping, 'ankle_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {ankle_colors}")
    print(f"   Interpretation: All steps PINK because ankle has no violations but other features do")


def demo_multi_task_classification():
    """Demonstrate classification with multiple tasks."""
    print_banner("Multi-Task Classification")
    
    classifier = StepClassifier()
    
    # Create failures for different tasks
    multi_task_failures = [
        # Level walking failures
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Hip violation in level walking'
        },
        # Incline walking failures
        {
            'task': 'incline_walking',
            'variable': 'knee_flexion_angle_contra',
            'phase': 50.0,
            'value': 1.5,
            'expected_min': 0.0,
            'expected_max': 0.15,
            'failure_reason': 'Knee violation in incline walking'
        },
        # Running failures
        {
            'task': 'running',
            'variable': 'ankle_flexion_angle_ipsi',
            'phase': 75.0,
            'value': -0.5,
            'expected_min': -0.1,
            'expected_max': 0.2,
            'failure_reason': 'Ankle violation in running'
        }
    ]
    
    # Create mixed step mapping
    multi_step_mapping = {
        0: 'level_walking',     # Has hip violation
        1: 'level_walking',     # Has hip violation
        2: 'incline_walking',   # Has knee violation
        3: 'incline_walking',   # Has knee violation
        4: 'running',           # Has ankle violation
        5: 'running',           # Has ankle violation
        6: 'squats',            # No violations
        7: 'squats'             # No violations
    }
    
    print("📊 Multi-task validation failures:")
    for failure in multi_task_failures:
        print(f"   • {failure['task']}: {failure['variable']} violation")
    
    print(f"\n📋 Step distribution:")
    task_counts = {}
    for step_idx, task in multi_step_mapping.items():
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
    for step_idx, color in enumerate(hip_colors):
        task = multi_step_mapping[step_idx]
        if color == 'red':
            print(f"      Step {step_idx} ({task}): RED - has local hip violation")
        elif color == 'pink':
            print(f"      Step {step_idx} ({task}): PINK - has other violations")
        else:
            print(f"      Step {step_idx} ({task}): GRAY - no violations")
    
    # Test knee feature classification
    print(f"\n🎯 Knee feature classification:")
    knee_colors = classifier.classify_steps_for_feature(
        multi_task_failures, multi_step_mapping, 'knee_flexion_angle_contra', 'kinematic'
    )
    
    print(f"   Step colors: {knee_colors}")
    print(f"   Expected: level_walking=PINK, incline_walking=RED, running=PINK, squats=GRAY")


def demo_kinematic_vs_kinetic():
    """Demonstrate difference between kinematic and kinetic classification."""
    print_banner("Kinematic vs Kinetic Classification")
    
    classifier = StepClassifier()
    
    # Show feature mappings
    print("🦴 Kinematic features (joint angles):")
    kinematic_features = classifier.get_feature_map('kinematic')
    for feature, idx in kinematic_features.items():
        print(f"   {idx}: {feature}")
    
    print("\n💪 Kinetic features (forces/moments):")
    kinetic_features = classifier.get_feature_map('kinetic')
    for feature, idx in kinetic_features.items():
        print(f"   {idx}: {feature}")
    
    # Create kinetic failures
    kinetic_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_moment_ipsi_Nm_kg',
            'phase': 25.0,
            'value': 1.5,
            'expected_min': -0.1,
            'expected_max': 0.3,
            'failure_reason': 'Hip moment too high'
        }
    ]
    
    step_mapping = {0: 'level_walking', 1: 'level_walking'}
    
    print(f"\n🎯 Kinetic classification for 'hip_moment_ipsi_Nm_kg':")
    kinetic_colors = classifier.classify_steps_for_feature(
        kinetic_failures, step_mapping, 'hip_moment_ipsi_Nm_kg', 'kinetic'
    )
    print(f"   Result: {kinetic_colors}")
    print(f"   Both steps RED because hip moment has local violations")
    
    print(f"\n🎯 Kinetic classification for 'knee_moment_ipsi_Nm_kg':")
    knee_kinetic_colors = classifier.classify_steps_for_feature(
        kinetic_failures, step_mapping, 'knee_moment_ipsi_Nm_kg', 'kinetic'
    )
    print(f"   Result: {knee_kinetic_colors}")
    print(f"   Both steps PINK because knee moment has no violations but hip does")


def demo_edge_cases():
    """Demonstrate edge cases and error handling."""
    print_banner("Edge Cases and Error Handling")
    
    classifier = StepClassifier()
    
    # Test with no failures
    print("🔍 Test 1: No validation failures")
    no_failures = []
    step_mapping = {0: 'level_walking', 1: 'level_walking', 2: 'running'}
    
    colors = classifier.classify_steps_for_feature(
        no_failures, step_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {colors}")
    print(f"   All steps GRAY because no violations exist")
    
    # Test with empty step mapping
    print(f"\n🔍 Test 2: Empty step mapping")
    empty_mapping = {}
    empty_colors = classifier.classify_steps_for_feature(
        no_failures, empty_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    print(f"   Result: {empty_colors}")
    print(f"   Empty array because no steps to classify")
    
    # Test invalid mode
    print(f"\n🔍 Test 3: Invalid mode handling")
    try:
        classifier.get_feature_map('invalid_mode')
        print(f"   ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"   SUCCESS: Properly caught error - {e}")
    
    # Test large dataset
    print(f"\n🔍 Test 4: Large dataset performance")
    large_mapping = {i: 'level_walking' for i in range(1000)}
    large_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Test failure'
        }
    ]
    
    import time
    start_time = time.time()
    large_colors = classifier.classify_steps_for_feature(
        large_failures, large_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
    )
    end_time = time.time()
    
    print(f"   Classified {len(large_colors)} steps in {(end_time - start_time)*1000:.2f}ms")
    print(f"   All steps: {large_colors[0]} (first 5: {large_colors[:5]})")


def demo_comprehensive_report():
    """Demonstrate comprehensive classification report generation."""
    print_banner("Comprehensive Classification Report")
    
    classifier = StepClassifier()
    
    # Create realistic mixed scenario
    realistic_failures = [
        {'task': 'level_walking', 'variable': 'hip_flexion_angle_ipsi', 'phase': 25.0, 'value': 0.8, 'expected_min': 0.15, 'expected_max': 0.6, 'failure_reason': 'Hip too high'},
        {'task': 'level_walking', 'variable': 'knee_flexion_angle_contra', 'phase': 50.0, 'value': 1.5, 'expected_min': 0.0, 'expected_max': 0.15, 'failure_reason': 'Knee too high'},
        {'task': 'incline_walking', 'variable': 'ankle_flexion_angle_ipsi', 'phase': 75.0, 'value': -0.5, 'expected_min': -0.1, 'expected_max': 0.2, 'failure_reason': 'Ankle too low'},
        {'task': 'running', 'variable': 'hip_flexion_angle_contra', 'phase': 25.0, 'value': 1.2, 'expected_min': 0.3, 'expected_max': 0.9, 'failure_reason': 'Hip contra too high'}
    ]
    
    realistic_mapping = {
        0: 'level_walking',     # hip + knee violations
        1: 'level_walking',     # hip + knee violations
        2: 'incline_walking',   # ankle violation
        3: 'incline_walking',   # ankle violation
        4: 'running',           # hip contra violation
        5: 'running',           # hip contra violation
        6: 'squats',            # no violations
        7: 'squats',            # no violations
        8: 'squats'             # no violations
    }
    
    print("📊 Creating comprehensive report for realistic scenario:")
    print(f"   • 9 total steps across 4 different tasks")
    print(f"   • 4 different variables with violations")
    print(f"   • Mix of valid and invalid steps")
    
    # Generate comprehensive report
    report = classifier.create_step_classification_report(
        realistic_failures, realistic_mapping, 'kinematic'
    )
    
    print(f"\n📋 Report Summary:")
    print(f"   Total steps: {report['total_steps']}")
    print(f"   Mode: {report['mode']}")
    print(f"   Valid steps: {report['summary']['valid_steps']}")
    print(f"   Steps with local violations: {report['summary']['local_violation_steps']}")
    print(f"   Steps with other violations: {report['summary']['other_violation_steps']}")
    
    print(f"\n📊 Per-feature breakdown:")
    for feature_name, stats in report['by_feature'].items():
        total_violating = stats['local_violations'] + stats['other_violations']
        print(f"   {feature_name}:")
        print(f"      Valid: {stats['valid']}, Local violations: {stats['local_violations']}, Other violations: {stats['other_violations']}")
    
    print(f"\n🎨 Feature classifications (first 3 features):")
    feature_names = list(report['feature_classifications'].keys())[:3]
    for feature_name in feature_names:
        colors = report['feature_classifications'][feature_name]
        print(f"   {feature_name}: {colors}")


def demo_integration_example():
    """Demonstrate how to use step classifier with validation plotting."""
    print_banner("Live Integration with Filter by Phase Plotter")
    
    # Import the actual plotting function
    try:
        from validation.filters_by_phase_plots import create_filters_by_phase_plot
        plotting_available = True
    except ImportError as e:
        print(f"⚠️  Could not import plotting function: {e}")
        plotting_available = False
        return
    
    classifier = StepClassifier()
    
    print("🔗 Creating actual validation plots with step classification...")
    
    # Create realistic validation data
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
    
    # Create realistic gait data with some violations
    num_steps = 6
    num_points = 150
    num_features = 6
    
    data = np.zeros((num_steps, num_points, num_features))
    phase_percent = np.linspace(0, 100, num_points)
    
    # Create realistic gait patterns
    for step in range(num_steps):
        step_offset = (step - 3) * 0.02  # Small variation per step
        
        # Hip flexion pattern (typical gait cycle)
        hip_pattern = 0.25 * np.sin(2 * np.pi * phase_percent / 100) + 0.3
        data[step, :, 0] = hip_pattern + step_offset  # hip_ipsi
        data[step, :, 1] = hip_pattern + step_offset  # hip_contra
        
        # Knee flexion pattern (stance/swing phases)
        knee_pattern = 0.4 * np.sin(np.pi * phase_percent / 100) + 0.4
        data[step, :, 2] = knee_pattern + step_offset  # knee_ipsi
        data[step, :, 3] = knee_pattern + step_offset  # knee_contra
        
        # Ankle flexion pattern (dorsi/plantarflexion)
        ankle_pattern = -0.15 * np.sin(2 * np.pi * phase_percent / 100) - 0.1
        data[step, :, 4] = ankle_pattern + step_offset  # ankle_ipsi
        data[step, :, 5] = ankle_pattern + step_offset  # ankle_contra
    
    # Add violations to specific steps for demonstration
    data[0, :, 0] += 0.5  # Step 0: Hip violation (too high)
    data[2, :, 2] += 0.8  # Step 2: Knee violation (too high) 
    data[4, :, 4] -= 0.4  # Step 4: Ankle violation (too low)
    
    # Create validation failures based on the data violations
    sample_failures = [
        {
            'task': 'level_walking',
            'variable': 'hip_flexion_angle_ipsi',
            'phase': 25.0,
            'value': 0.8,
            'expected_min': 0.15,
            'expected_max': 0.6,
            'failure_reason': 'Hip flexion too high'
        },
        {
            'task': 'level_walking', 
            'variable': 'knee_flexion_angle_ipsi',
            'phase': 50.0,
            'value': 1.2,
            'expected_min': 0.5,
            'expected_max': 0.8,
            'failure_reason': 'Knee flexion too high'
        },
        {
            'task': 'level_walking',
            'variable': 'ankle_flexion_angle_ipsi',
            'phase': 75.0,
            'value': -0.5,
            'expected_min': -0.1,
            'expected_max': 0.2,
            'failure_reason': 'Ankle flexion too low'
        }
    ]
    
    # Create step mapping
    step_task_mapping = {i: 'level_walking' for i in range(num_steps)}
    
    # Create output directory
    output_dir = Path(__file__).parent / "sample_plots" / "demo_step_classifier"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Data shape: {data.shape} (steps, time_points, features)")
    print(f"⚠️  Violations added to steps: 0 (hip), 2 (knee), 4 (ankle)")
    
    # Demonstrate different classification scenarios
    scenarios = [
        {
            'name': 'summary_classification',
            'description': 'Summary classification (any violation = red)',
            'step_colors': classifier.get_step_summary_classification(sample_failures, step_task_mapping)
        },
        {
            'name': 'hip_feature_specific',
            'description': 'Hip-specific classification (hip violations = red, others = pink)',
            'step_colors': classifier.classify_steps_for_feature(
                sample_failures, step_task_mapping, 'hip_flexion_angle_ipsi', 'kinematic'
            )
        },
        {
            'name': 'knee_feature_specific', 
            'description': 'Knee-specific classification (knee violations = red, others = pink)',
            'step_colors': classifier.classify_steps_for_feature(
                sample_failures, step_task_mapping, 'knee_flexion_angle_ipsi', 'kinematic'
            )
        },
        {
            'name': 'ankle_feature_specific',
            'description': 'Ankle-specific classification (ankle violations = red, others = pink)',
            'step_colors': classifier.classify_steps_for_feature(
                sample_failures, step_task_mapping, 'ankle_flexion_angle_ipsi', 'kinematic'
            )
        }
    ]
    
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
                data=data,
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
    
    print(f"""
🔗 Integration Summary:

The step classifier successfully integrated with the filters_by_phase_plots function
to generate validation plots with colored step overlays:

1. **Summary Classification**: Shows all steps with any violations as red
2. **Feature-Specific**: Shows local violations as red, other violations as pink
3. **Real Data**: Uses actual gait data with realistic violation patterns
4. **Visual Output**: Creates publication-ready validation plots

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
• Integration examples in dataset_validator.py
""")


if __name__ == "__main__":
    main()