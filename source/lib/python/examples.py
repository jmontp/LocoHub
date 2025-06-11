#!/usr/bin/env python3
"""
Real-World Examples for LocomotionData Library

Created: 2025-06-11 with user permission
Purpose: Comprehensive real-world examples demonstrating practical usage patterns

Intent:
This module provides realistic, practical examples of how to use the LocomotionData library
for common biomechanical analysis tasks. Examples are based on actual research workflows
and demonstrate best practices for:

**PRIMARY FUNCTIONS:**
1. **Data Loading**: Loading and validating various dataset formats
2. **Quality Assessment**: Identifying and handling data quality issues
3. **Statistical Analysis**: Computing meaningful biomechanical metrics
4. **Comparative Analysis**: Comparing conditions, subjects, and populations
5. **Visualization**: Creating publication-ready plots and figures

Usage:
    python examples.py --example basic_analysis
    python examples.py --example quality_assessment
    python examples.py --example comparative_study

Each example includes:
- Real-world context and motivation
- Step-by-step implementation
- Common pitfalls and solutions
- Interpretation guidelines
- Publication-ready output

These examples serve as templates for researchers conducting biomechanical
analysis with standardized locomotion datasets.
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
import argparse
import warnings

# Optional imports
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    
try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

# Add library path
sys.path.append(os.path.dirname(__file__))

try:
    from locomotion_analysis import LocomotionData
except ImportError:
    print("Error: Could not import LocomotionData. Make sure the library is in the Python path.")
    sys.exit(1)


def example_1_basic_gait_analysis():
    """
    Example 1: Basic Gait Analysis
    
    Research Question: What are the normal knee flexion patterns during walking?
    
    This example demonstrates:
    - Loading standardized locomotion data
    - Extracting gait cycles for analysis
    - Computing mean patterns and variability
    - Creating publication-ready plots
    """
    print("=" * 60)
    print("EXAMPLE 1: Basic Gait Analysis")
    print("=" * 60)
    print("Research Question: What are normal knee flexion patterns during walking?")
    print()
    
    # Create synthetic dataset representing realistic gait data
    print("1. Creating sample dataset...")
    sample_data = create_realistic_gait_data()
    
    # Save temporary file
    temp_file = 'temp_gait_data.parquet'
    sample_data.to_parquet(temp_file)
    
    try:
        # Load data with LocomotionData
        print("2. Loading data with LocomotionData...")
        loco = LocomotionData(temp_file)
        
        print(f"   ✓ Loaded data: {len(loco.get_subjects())} subjects, {len(loco.get_tasks())} tasks")
        print(f"   ✓ Available features: {len(loco.features)}")
        
        # Analyze knee flexion patterns
        print("\n3. Analyzing knee flexion patterns...")
        subject = loco.get_subjects()[0]
        task = 'normal_walk'
        
        # Extract knee flexion data
        knee_features = ['knee_flexion_angle_contra_rad', 'knee_flexion_angle_ipsi_rad']
        data_3d, feature_names = loco.get_cycles(subject, task, knee_features)
        
        if data_3d is not None:
            print(f"   ✓ Extracted {data_3d.shape[0]} gait cycles")
            
            # Compute statistics
            mean_patterns = loco.get_mean_patterns(subject, task, knee_features)
            std_patterns = loco.get_std_patterns(subject, task, knee_features)
            rom_data = loco.calculate_rom(subject, task, knee_features)
            
            print(f"   ✓ Contra knee ROM: {np.mean(rom_data['knee_flexion_angle_contra_rad']):.2f} ± {np.std(rom_data['knee_flexion_angle_contra_rad']):.2f} rad")
            print(f"   ✓ Ipsi knee ROM: {np.mean(rom_data['knee_flexion_angle_ipsi_rad']):.2f} ± {np.std(rom_data['knee_flexion_angle_ipsi_rad']):.2f} rad")
            
            # Create visualization
            print("\n4. Creating visualization...")
            create_knee_analysis_plot(mean_patterns, std_patterns, rom_data)
            
            # Quality assessment
            print("\n5. Quality assessment...")
            valid_mask = loco.validate_cycles(subject, task, knee_features)
            outliers = loco.find_outlier_cycles(subject, task, knee_features)
            
            print(f"   ✓ Valid cycles: {np.sum(valid_mask)}/{len(valid_mask)}")
            print(f"   ✓ Outlier cycles: {len(outliers)}")
            
        print("\n✅ Analysis complete! Check 'knee_analysis.png' for results.")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)


def example_2_quality_assessment_workflow():
    """
    Example 2: Data Quality Assessment Workflow
    
    Research Question: How can we systematically assess data quality in biomechanical datasets?
    
    This example demonstrates:
    - Automated quality checks
    - Outlier detection and handling
    - Data completeness assessment
    - Quality reporting
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Data Quality Assessment Workflow")
    print("=" * 60)
    print("Research Question: How can we systematically assess data quality?")
    print()
    
    # Create dataset with quality issues
    print("1. Creating dataset with known quality issues...")
    sample_data = create_data_with_quality_issues()
    
    temp_file = 'temp_quality_data.parquet'
    sample_data.to_parquet(temp_file)
    
    try:
        print("2. Loading and analyzing data quality...")
        loco = LocomotionData(temp_file)
        
        # Comprehensive quality assessment
        quality_report = perform_quality_assessment(loco)
        
        print("\n3. Quality Assessment Results:")
        print(f"   📊 Total subjects: {quality_report['total_subjects']}")
        print(f"   📊 Total cycles analyzed: {quality_report['total_cycles']}")
        print(f"   ✅ Valid cycles: {quality_report['valid_cycles']} ({quality_report['valid_percentage']:.1f}%)")
        print(f"   ⚠️  Outlier cycles: {quality_report['outlier_cycles']}")
        print(f"   ❌ Invalid cycles: {quality_report['invalid_cycles']}")
        
        print("\n4. Variable name validation:")
        validation_report = loco.get_validation_report()
        print(f"   ✅ Standard compliant: {len(validation_report['standard_compliant'])}")
        print(f"   ⚠️  Non-standard: {len(validation_report['non_standard'])}")
        
        if validation_report['warnings']:
            print("   📝 Warnings:")
            for warning in validation_report['warnings'][:3]:  # Show first 3
                print(f"      - {warning}")
        
        print("\n5. Recommendations:")
        provide_quality_recommendations(quality_report, validation_report)
        
        print("\n✅ Quality assessment complete!")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def example_3_comparative_biomechanics_study():
    """
    Example 3: Comparative Biomechanics Study
    
    Research Question: How do joint kinematics differ between normal walking and fast walking?
    
    This example demonstrates:
    - Multi-condition comparison
    - Statistical testing
    - Effect size calculation
    - Clinical interpretation
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Comparative Biomechanics Study")
    print("=" * 60)
    print("Research Question: How do joint kinematics differ between walking speeds?")
    print()
    
    print("1. Creating multi-condition dataset...")
    sample_data = create_multi_condition_data()
    
    temp_file = 'temp_comparative_data.parquet'
    sample_data.to_parquet(temp_file)
    
    try:
        print("2. Loading comparative dataset...")
        loco = LocomotionData(temp_file)
        
        print("3. Performing comparative analysis...")
        comparison_results = perform_comparative_analysis(loco)
        
        print("\n4. Statistical Results:")
        for joint, results in comparison_results.items():
            print(f"   {joint.title()} Flexion:")
            print(f"     Normal: {results['normal_mean']:.3f} ± {results['normal_std']:.3f} rad")
            print(f"     Fast: {results['fast_mean']:.3f} ± {results['fast_std']:.3f} rad")
            print(f"     Difference: {results['difference']:.3f} rad")
            print(f"     Effect size: {results['effect_size']:.2f}")
            print(f"     Interpretation: {results['interpretation']}")
            print()
        
        print("5. Creating comparative visualization...")
        create_comparative_plot(loco, comparison_results)
        
        print("✅ Comparative analysis complete! Check 'comparative_analysis.png'")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def example_4_population_analysis():
    """
    Example 4: Population-Level Analysis
    
    Research Question: What are population norms for gait parameters across age groups?
    
    This example demonstrates:
    - Population-level statistics
    - Age group comparisons
    - Normative data creation
    - Clinical reference ranges
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Population Analysis")
    print("=" * 60)
    print("Research Question: What are population norms across age groups?")
    print()
    
    print("1. Creating population dataset...")
    sample_data = create_population_data()
    
    temp_file = 'temp_population_data.parquet'
    sample_data.to_parquet(temp_file)
    
    try:
        print("2. Loading population dataset...")
        loco = LocomotionData(temp_file)
        
        print("3. Computing population statistics...")
        
        # Age group analysis
        age_groups = {
            'Young Adults (20-30)': [f'SUB{i:02d}' for i in range(1, 6)],
            'Middle Age (40-50)': [f'SUB{i:02d}' for i in range(6, 11)],
            'Older Adults (60-70)': [f'SUB{i:02d}' for i in range(11, 16)]
        }
        
        population_stats = compute_population_statistics(loco, age_groups)
        
        print("\n4. Population Norms:")
        for age_group, stats in population_stats.items():
            print(f"   {age_group}:")
            for param, values in stats.items():
                mean_val = np.mean(values)
                std_val = np.std(values)
                ci_lower = np.percentile(values, 2.5)
                ci_upper = np.percentile(values, 97.5)
                print(f"     {param}: {mean_val:.3f} ± {std_val:.3f} rad (95% CI: {ci_lower:.3f}-{ci_upper:.3f})")
            print()
        
        print("5. Creating population visualization...")
        create_population_plot(population_stats)
        
        print("✅ Population analysis complete! Check 'population_analysis.png'")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# Helper functions for creating realistic datasets

def create_realistic_gait_data():
    """Create realistic gait data for examples."""
    np.random.seed(42)
    
    subjects = ['SUB01', 'SUB02', 'SUB03']
    tasks = ['normal_walk']
    n_cycles = 8
    points_per_cycle = 150
    
    data = []
    
    for subject in subjects:
        for task in tasks:
            for cycle in range(n_cycles):
                phase = np.linspace(0, 100, points_per_cycle)
                
                # Realistic knee flexion pattern (0-60 degrees converted to radians)
                knee_base = 0.5236 * np.sin(2 * np.pi * phase / 100) + 0.1745  # Base pattern
                knee_base = np.clip(knee_base, 0, 1.047)  # Clip to 0-60 degrees
                
                # Add subject variability
                subject_offset = (int(subject[-1]) - 1) * 0.087  # 5 degree offset per subject
                
                # Add cycle variability
                cycle_noise = np.random.normal(0, 0.052, points_per_cycle)  # 3 degree std
                
                for i in range(points_per_cycle):
                    data.append({
                        'subject': subject,
                        'task': task,
                        'phase': phase[i],
                        'cycle': cycle,
                        'knee_flexion_angle_contra_rad': knee_base[i] + subject_offset + cycle_noise[i],
                        'knee_flexion_angle_ipsi_rad': knee_base[i] + subject_offset + cycle_noise[i] + 0.017,  # Slight asymmetry
                        'hip_flexion_angle_contra_rad': 0.4 * np.sin(2 * np.pi * phase[i] / 100),
                        'ankle_flexion_angle_contra_rad': 0.2 * np.sin(2 * np.pi * phase[i] / 100 - np.pi/2)
                    })
    
    return pd.DataFrame(data)


def create_data_with_quality_issues():
    """Create dataset with known quality issues for testing."""
    np.random.seed(42)
    
    data = []
    for i in range(600):  # 4 cycles of 150 points
        phase = (i % 150) * (100/149)
        cycle = i // 150
        
        # Base pattern
        knee_angle = 0.5 * np.sin(2 * np.pi * phase / 100) + 0.1
        
        # Introduce quality issues
        if i == 75:  # NaN value
            knee_angle = np.nan
        elif i == 225:  # Unrealistic spike
            knee_angle = 5.0
        elif cycle == 2:  # Noisy cycle
            knee_angle += np.random.normal(0, 0.5)
        
        data.append({
            'subject': 'SUB01',
            'task': 'normal_walk',
            'phase': phase,
            'cycle': cycle,
            'knee_flexion_angle_contra_rad': knee_angle,
            'hip_flexion_angle_contra_rad': 0.4 * np.sin(2 * np.pi * phase / 100),
            'old_naming_knee_angle': knee_angle  # Non-standard naming
        })
    
    return pd.DataFrame(data)


def create_multi_condition_data():
    """Create multi-condition dataset for comparative analysis."""
    np.random.seed(42)
    
    subjects = ['SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05']
    tasks = ['normal_walk', 'fast_walk']
    n_cycles = 6
    points_per_cycle = 150
    
    data = []
    
    for subject in subjects:
        for task in tasks:
            for cycle in range(n_cycles):
                phase = np.linspace(0, 100, points_per_cycle)
                
                # Task-specific modifications
                speed_factor = 1.3 if task == 'fast_walk' else 1.0
                
                for i in range(points_per_cycle):
                    # Joint patterns with speed effects
                    hip_angle = 0.4 * speed_factor * np.sin(2 * np.pi * phase[i] / 100)
                    knee_angle = 0.6 * speed_factor * np.sin(2 * np.pi * phase[i] / 100 - np.pi/4)
                    ankle_angle = 0.3 * speed_factor * np.sin(2 * np.pi * phase[i] / 100 - np.pi/2)
                    
                    # Add noise
                    noise = np.random.normal(0, 0.03)
                    
                    data.append({
                        'subject': subject,
                        'task': task,
                        'phase': phase[i],
                        'cycle': cycle,
                        'hip_flexion_angle_contra_rad': hip_angle + noise,
                        'knee_flexion_angle_contra_rad': knee_angle + noise,
                        'ankle_flexion_angle_contra_rad': ankle_angle + noise
                    })
    
    return pd.DataFrame(data)


def create_population_data():
    """Create population dataset with age effects."""
    np.random.seed(42)
    
    # 15 subjects across 3 age groups
    n_subjects = 15
    tasks = ['normal_walk']
    n_cycles = 5
    points_per_cycle = 150
    
    data = []
    
    for subject_idx in range(n_subjects):
        subject = f'SUB{subject_idx+1:02d}'
        
        # Age group effects
        if subject_idx < 5:  # Young adults
            age_factor = 1.0
        elif subject_idx < 10:  # Middle age
            age_factor = 0.95
        else:  # Older adults
            age_factor = 0.85
        
        for task in tasks:
            for cycle in range(n_cycles):
                phase = np.linspace(0, 100, points_per_cycle)
                
                for i in range(points_per_cycle):
                    # Age-related changes in joint patterns
                    hip_angle = 0.4 * age_factor * np.sin(2 * np.pi * phase[i] / 100)
                    knee_angle = 0.6 * age_factor * np.sin(2 * np.pi * phase[i] / 100 - np.pi/4)
                    ankle_angle = 0.3 * age_factor * np.sin(2 * np.pi * phase[i] / 100 - np.pi/2)
                    
                    # Add individual variation
                    noise = np.random.normal(0, 0.05)
                    
                    data.append({
                        'subject': subject,
                        'task': task,
                        'phase': phase[i],
                        'cycle': cycle,
                        'hip_flexion_angle_contra_rad': hip_angle + noise,
                        'knee_flexion_angle_contra_rad': knee_angle + noise,
                        'ankle_flexion_angle_contra_rad': ankle_angle + noise
                    })
    
    return pd.DataFrame(data)


# Analysis functions

def perform_quality_assessment(loco):
    """Perform comprehensive quality assessment."""
    total_subjects = len(loco.get_subjects())
    total_cycles = 0
    valid_cycles = 0
    outlier_cycles = 0
    
    for subject in loco.get_subjects():
        for task in loco.get_tasks():
            data_3d, _ = loco.get_cycles(subject, task)
            if data_3d is not None:
                n_cycles = data_3d.shape[0]
                total_cycles += n_cycles
                
                valid_mask = loco.validate_cycles(subject, task)
                valid_cycles += np.sum(valid_mask)
                
                outliers = loco.find_outlier_cycles(subject, task)
                outlier_cycles += len(outliers)
    
    return {
        'total_subjects': total_subjects,
        'total_cycles': total_cycles,
        'valid_cycles': valid_cycles,
        'valid_percentage': (valid_cycles / total_cycles * 100) if total_cycles > 0 else 0,
        'outlier_cycles': outlier_cycles,
        'invalid_cycles': total_cycles - valid_cycles
    }


def perform_comparative_analysis(loco):
    """Perform comparative analysis between conditions."""
    subjects = loco.get_subjects()
    joints = ['hip', 'knee', 'ankle']
    
    results = {}
    
    for joint in joints:
        feature = f'{joint}_flexion_angle_contra_rad'
        
        normal_roms = []
        fast_roms = []
        
        for subject in subjects:
            # Normal walking
            normal_rom = loco.calculate_rom(subject, 'normal_walk', [feature])
            if feature in normal_rom:
                normal_roms.extend(normal_rom[feature])
            
            # Fast walking
            fast_rom = loco.calculate_rom(subject, 'fast_walk', [feature])
            if feature in fast_rom:
                fast_roms.extend(fast_rom[feature])
        
        if normal_roms and fast_roms:
            normal_mean = np.mean(normal_roms)
            normal_std = np.std(normal_roms)
            fast_mean = np.mean(fast_roms)
            fast_std = np.std(fast_roms)
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((len(normal_roms)-1)*normal_std**2 + (len(fast_roms)-1)*fast_std**2) / 
                               (len(normal_roms) + len(fast_roms) - 2))
            effect_size = (fast_mean - normal_mean) / pooled_std
            
            # Interpretation
            if abs(effect_size) < 0.2:
                interpretation = "Negligible difference"
            elif abs(effect_size) < 0.5:
                interpretation = "Small effect"
            elif abs(effect_size) < 0.8:
                interpretation = "Medium effect"
            else:
                interpretation = "Large effect"
            
            results[joint] = {
                'normal_mean': normal_mean,
                'normal_std': normal_std,
                'fast_mean': fast_mean,
                'fast_std': fast_std,
                'difference': fast_mean - normal_mean,
                'effect_size': effect_size,
                'interpretation': interpretation
            }
    
    return results


def compute_population_statistics(loco, age_groups):
    """Compute population statistics by age group."""
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad']
    
    population_stats = {}
    
    for group_name, subjects in age_groups.items():
        group_stats = {feature: [] for feature in features}
        
        for subject in subjects:
            if subject in loco.get_subjects():
                rom_data = loco.calculate_rom(subject, 'normal_walk', features)
                for feature in features:
                    if feature in rom_data:
                        group_stats[feature].extend(rom_data[feature])
        
        population_stats[group_name] = group_stats
    
    return population_stats


def provide_quality_recommendations(quality_report, validation_report):
    """Provide data quality recommendations."""
    print("   📋 Based on quality assessment:")
    
    if quality_report['valid_percentage'] < 80:
        print("      ⚠️  Low data quality detected. Consider:")
        print("         - Reviewing data collection protocols")
        print("         - Implementing stricter quality control")
        print("         - Excluding low-quality subjects/trials")
    
    if quality_report['outlier_cycles'] > quality_report['total_cycles'] * 0.1:
        print("      ⚠️  High outlier rate. Consider:")
        print("         - Adjusting outlier detection threshold")
        print("         - Manual review of flagged cycles")
        print("         - Investigating systematic measurement errors")
    
    if len(validation_report['non_standard']) > 0:
        print("      ⚠️  Non-standard variable names detected. Consider:")
        print("         - Renaming variables to follow standard convention")
        print("         - Using standardized datasets for better compatibility")
        print("         - Implementing automated name mapping")


# Visualization functions

def create_knee_analysis_plot(mean_patterns, std_patterns, rom_data):
    """Create knee analysis visualization."""
    if not MATPLOTLIB_AVAILABLE:
        print("   ⚠️  matplotlib not available, skipping visualization")
        return
    
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Mean patterns
    plt.subplot(2, 2, 1)
    phase_x = np.linspace(0, 100, 150)
    
    for feature in mean_patterns:
        mean_curve = mean_patterns[feature]
        std_curve = std_patterns[feature]
        
        label = 'Contralateral' if 'contra' in feature else 'Ipsilateral'
        color = 'blue' if 'contra' in feature else 'red'
        
        plt.plot(phase_x, np.degrees(mean_curve), color=color, linewidth=2, label=label)
        plt.fill_between(phase_x, np.degrees(mean_curve - std_curve), 
                        np.degrees(mean_curve + std_curve), alpha=0.3, color=color)
    
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Knee Flexion (degrees)')
    plt.title('Mean Knee Flexion Patterns')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Plot 2: ROM comparison
    plt.subplot(2, 2, 2)
    rom_values = [np.degrees(rom_data['knee_flexion_angle_contra_rad']), 
                  np.degrees(rom_data['knee_flexion_angle_ipsi_rad'])]
    labels = ['Contralateral', 'Ipsilateral']
    
    plt.boxplot(rom_values, labels=labels)
    plt.ylabel('Range of Motion (degrees)')
    plt.title('Knee Flexion ROM Distribution')
    plt.grid(True, alpha=0.3)
    
    # Plot 3: Cycle-to-cycle variability
    plt.subplot(2, 2, 3)
    contra_std = np.degrees(np.mean(std_patterns['knee_flexion_angle_contra_rad']))
    ipsi_std = np.degrees(np.mean(std_patterns['knee_flexion_angle_ipsi_rad']))
    
    plt.bar(['Contralateral', 'Ipsilateral'], [contra_std, ipsi_std], 
           color=['blue', 'red'], alpha=0.7)
    plt.ylabel('Average Std Dev (degrees)')
    plt.title('Cycle-to-Cycle Variability')
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Summary statistics
    plt.subplot(2, 2, 4)
    plt.text(0.1, 0.8, 'Summary Statistics:', fontsize=14, fontweight='bold')
    plt.text(0.1, 0.6, f'Contralateral ROM: {np.mean(np.degrees(rom_data["knee_flexion_angle_contra_rad"])):.1f}° ± {np.std(np.degrees(rom_data["knee_flexion_angle_contra_rad"])):.1f}°')
    plt.text(0.1, 0.4, f'Ipsilateral ROM: {np.mean(np.degrees(rom_data["knee_flexion_angle_ipsi_rad"])):.1f}° ± {np.std(np.degrees(rom_data["knee_flexion_angle_ipsi_rad"])):.1f}°')
    plt.text(0.1, 0.2, f'Asymmetry: {abs(np.mean(np.degrees(rom_data["knee_flexion_angle_contra_rad"])) - np.mean(np.degrees(rom_data["knee_flexion_angle_ipsi_rad"]))):.1f}°')
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig('knee_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_comparative_plot(loco, comparison_results):
    """Create comparative analysis visualization."""
    if not MATPLOTLIB_AVAILABLE:
        print("   ⚠️  matplotlib not available, skipping visualization")
        return
    
    plt.figure(figsize=(15, 5))
    
    joints = list(comparison_results.keys())
    
    for i, joint in enumerate(joints):
        plt.subplot(1, 3, i+1)
        
        results = comparison_results[joint]
        
        # Create bar plot with error bars
        conditions = ['Normal', 'Fast']
        means = [results['normal_mean'], results['fast_mean']]
        stds = [results['normal_std'], results['fast_std']]
        
        bars = plt.bar(conditions, np.degrees(means), yerr=np.degrees(stds), 
                      capsize=5, alpha=0.7, color=['blue', 'orange'])
        
        plt.ylabel('Range of Motion (degrees)')
        plt.title(f'{joint.title()} Flexion ROM')
        plt.grid(True, alpha=0.3)
        
        # Add effect size annotation
        plt.text(0.5, max(np.degrees(means)) * 0.9, 
                f'Effect size: {results["effect_size"]:.2f}\n{results["interpretation"]}', 
                ha='center', va='center', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('comparative_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def create_population_plot(population_stats):
    """Create population analysis visualization."""
    if not MATPLOTLIB_AVAILABLE:
        print("   ⚠️  matplotlib not available, skipping visualization")
        return
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    joints = ['hip', 'knee', 'ankle']
    age_groups = list(population_stats.keys())
    colors = ['skyblue', 'lightgreen', 'salmon']
    
    for i, joint in enumerate(joints):
        ax = axes[i]
        feature = f'{joint}_flexion_angle_contra_rad'
        
        group_means = []
        group_stds = []
        
        for group in age_groups:
            if feature in population_stats[group] and len(population_stats[group][feature]) > 0:
                values = np.degrees(population_stats[group][feature])
                group_means.append(np.mean(values))
                group_stds.append(np.std(values))
            else:
                group_means.append(0)
                group_stds.append(0)
        
        bars = ax.bar(age_groups, group_means, yerr=group_stds, 
                     capsize=5, alpha=0.7, color=colors)
        
        ax.set_ylabel('Range of Motion (degrees)')
        ax.set_title(f'{joint.title()} Flexion ROM by Age')
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels for better readability
        ax.set_xticklabels(age_groups, rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig('population_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def main():
    """Main function to run examples."""
    parser = argparse.ArgumentParser(description='LocomotionData Library Examples')
    parser.add_argument('--example', type=str, choices=['basic', 'quality', 'comparative', 'population', 'all'],
                       default='all', help='Which example to run')
    
    args = parser.parse_args()
    
    print("LocomotionData Library - Real-World Examples")
    print("=" * 60)
    print("Demonstrating practical biomechanical analysis workflows")
    print()
    
    # Set matplotlib backend for non-interactive use
    if MATPLOTLIB_AVAILABLE:
        import matplotlib
        matplotlib.use('Agg')
    else:
        print("⚠️  matplotlib not available - visualizations will be skipped")
        print("   Install with: pip install matplotlib")
        print()
    
    if args.example == 'basic' or args.example == 'all':
        example_1_basic_gait_analysis()
    
    if args.example == 'quality' or args.example == 'all':
        example_2_quality_assessment_workflow()
    
    if args.example == 'comparative' or args.example == 'all':
        example_3_comparative_biomechanics_study()
    
    if args.example == 'population' or args.example == 'all':
        example_4_population_analysis()
    
    print("\n" + "=" * 60)
    print("🎉 All examples completed successfully!")
    print("Generated files:")
    if os.path.exists('knee_analysis.png'):
        print("  - knee_analysis.png")
    if os.path.exists('comparative_analysis.png'):
        print("  - comparative_analysis.png")
    if os.path.exists('population_analysis.png'):
        print("  - population_analysis.png")
    print("\nThese examples demonstrate the full capabilities of the LocomotionData library")
    print("for real-world biomechanical research applications.")


if __name__ == "__main__":
    main()