#!/usr/bin/env python3
"""
Test Tutorial 03: Basic Visualization

Created: 2025-08-07
Purpose: Test all code examples from Tutorial 03 - Visualization

This test validates that all visualization code from the tutorial works
correctly with our mock dataset. Uses non-interactive backend to avoid
display requirements.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
import warnings

# Set matplotlib backend before importing pyplot
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Add parent directory for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from locohub import LocomotionData

# Path to mock dataset
MOCK_DATASET = Path(__file__).parent / 'mock_data' / 'mock_dataset_phase.parquet'

# Output directory for test plots
PLOT_DIR = Path(__file__).parent / 'test_plots'
PLOT_DIR.mkdir(parents=True, exist_ok=True)


def setup_plotting():
    """Set up plotting style and directory."""
    # Create plot directory if needed
    PLOT_DIR.mkdir(exist_ok=True)
    
    # Try to use seaborn style if available
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
    except:
        try:
            plt.style.use('seaborn-darkgrid')
        except:
            pass  # Use default style
    
    print(f"Plots will be saved to: {PLOT_DIR}")


def test_compute_phase_average():
    """Test computing phase averages."""
    print("Testing phase average computation...")
    
    # Using Library
    data = LocomotionData(str(MOCK_DATASET))
    level_walking = data.filter(task='level_walking', subject='SUB01')
    
    # Compute average using library method
    mean_patterns = level_walking.get_mean_patterns('SUB01', 'level_walking')
    
    assert 'knee_flexion_angle_ipsi_rad' in mean_patterns
    assert 'mean' in mean_patterns['knee_flexion_angle_ipsi_rad']
    assert 'std' in mean_patterns['knee_flexion_angle_ipsi_rad']
    
    knee_mean = mean_patterns['knee_flexion_angle_ipsi_rad']['mean']
    knee_std = mean_patterns['knee_flexion_angle_ipsi_rad']['std']
    
    # Should have 150 points
    assert len(knee_mean) == 150, f"Expected 150 points, got {len(knee_mean)}"
    assert len(knee_std) == 150, f"Expected 150 points, got {len(knee_std)}"
    
    print(f"  Mean range: {knee_mean.min():.3f} to {knee_mean.max():.3f} rad")
    print(f"  Std range: {knee_std.min():.3f} to {knee_std.max():.3f} rad")
    
    print("✓ Phase average computation successful")


def test_raw_phase_average():
    """Test computing phase averages with raw pandas."""
    print("\nTesting raw pandas phase average...")
    
    data = pd.read_parquet(MOCK_DATASET)
    level_walking = data[(data['task'] == 'level_walking') & (data['subject'] == 'SUB01')]
    
    def compute_phase_average(data, variable):
        """Compute mean and std across cycles for each phase point."""
        grouped = data.groupby('phase_percent')[variable]
        mean_curve = grouped.mean()
        std_curve = grouped.std()
        return mean_curve, std_curve
    
    # Compute average knee flexion
    knee_mean, knee_std = compute_phase_average(level_walking, 'knee_flexion_angle_ipsi_rad')
    
    assert len(knee_mean) == 150, f"Expected 150 points, got {len(knee_mean)}"
    assert len(knee_std) == 150, f"Expected 150 points, got {len(knee_std)}"
    
    print(f"  Computed mean and std for {len(knee_mean)} phase points")
    print("✓ Raw phase average successful")


def test_phase_average_plot():
    """Test creating phase average plot with std bands."""
    print("\nTesting phase average plot...")
    
    data = LocomotionData(str(MOCK_DATASET))
    level_walking = data.filter(task='level_walking', subject='SUB01')
    
    # Get mean patterns
    mean_patterns = level_walking.get_mean_patterns('SUB01', 'level_walking')
    knee_mean = mean_patterns['knee_flexion_angle_ipsi_rad']['mean']
    knee_std = mean_patterns['knee_flexion_angle_ipsi_rad']['std']
    
    # Convert to degrees
    knee_mean_deg = np.degrees(knee_mean)
    knee_std_deg = np.degrees(knee_std)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    phase_percent = knee_mean_deg.index
    ax.plot(phase_percent, knee_mean_deg, 'b-', linewidth=2, label='Mean')
    ax.fill_between(phase_percent, 
                     knee_mean_deg - knee_std_deg, 
                     knee_mean_deg + knee_std_deg, 
                     alpha=0.3, 
                     color='blue',
                     label='±1 SD')
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=12)
    ax.set_ylabel('Knee Flexion (degrees)', fontsize=12)
    ax.set_title('Knee Flexion During Level Walking', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Save plot
    plot_path = PLOT_DIR / 'phase_average_with_std.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    assert plot_path.exists(), "Plot file not created"
    print(f"  Saved plot to: {plot_path.name}")
    print("✓ Phase average plot successful")


def test_spaghetti_plot():
    """Test creating spaghetti plot showing all cycles."""
    print("\nTesting spaghetti plot...")
    
    data = LocomotionData(str(MOCK_DATASET))
    sub1_level = data.filter(subject='SUB01', task='level_walking')
    
    # Create spaghetti plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot each cycle
    cycles = sub1_level.df['cycle_id'].unique()
    for cycle in cycles:
        cycle_data = sub1_level.df[sub1_level.df['cycle_id'] == cycle]
        cycle_data = cycle_data.sort_values('phase_percent')
        
        knee_deg = np.degrees(cycle_data['knee_flexion_angle_ipsi_rad'].values)
        phase = cycle_data['phase_percent'].values
        
        ax.plot(phase, knee_deg, alpha=0.5, linewidth=1)
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=12)
    ax.set_ylabel('Knee Flexion (degrees)', fontsize=12)
    ax.set_title('All Gait Cycles - Knee Flexion', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Save plot
    plot_path = PLOT_DIR / 'spaghetti_plot.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    assert plot_path.exists(), "Plot file not created"
    print(f"  Plotted {len(cycles)} cycles")
    print(f"  Saved plot to: {plot_path.name}")
    print("✓ Spaghetti plot successful")


def test_combined_plot():
    """Test creating combined mean + spaghetti plot."""
    print("\nTesting combined plot...")
    
    data = LocomotionData(str(MOCK_DATASET))
    sub1_level = data.filter(subject='SUB01', task='level_walking')
    
    # Get mean patterns
    mean_patterns = sub1_level.get_mean_patterns('SUB01', 'level_walking')
    knee_mean = mean_patterns['knee_flexion_angle_ipsi_rad']['mean']
    knee_std = mean_patterns['knee_flexion_angle_ipsi_rad']['std']
    
    # Create combined plot
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot individual cycles (spaghetti)
    cycles = sub1_level.df['cycle_id'].unique()
    for cycle in cycles:
        cycle_data = sub1_level.df[sub1_level.df['cycle_id'] == cycle]
        cycle_data = cycle_data.sort_values('phase_percent')
        
        knee_deg = np.degrees(cycle_data['knee_flexion_angle_ipsi_rad'].values)
        phase = cycle_data['phase_percent'].values
        
        ax.plot(phase, knee_deg, 'gray', alpha=0.3, linewidth=0.5)
    
    # Add mean and std
    phase_percent = knee_mean.index
    knee_mean_deg = np.degrees(knee_mean)
    knee_std_deg = np.degrees(knee_std)
    
    ax.plot(phase_percent, knee_mean_deg, 'b-', linewidth=2.5, label='Mean')
    ax.fill_between(phase_percent,
                     knee_mean_deg - knee_std_deg,
                     knee_mean_deg + knee_std_deg,
                     alpha=0.3, color='blue', label='±1 SD')
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=12)
    ax.set_ylabel('Knee Flexion (degrees)', fontsize=12)
    ax.set_title('Knee Flexion - Individual Cycles and Mean', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Save plot
    plot_path = PLOT_DIR / 'combined_plot.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    assert plot_path.exists(), "Plot file not created"
    print(f"  Saved plot to: {plot_path.name}")
    print("✓ Combined plot successful")


def test_multi_variable_plot():
    """Test plotting multiple variables."""
    print("\nTesting multi-variable plot...")
    
    data = LocomotionData(str(MOCK_DATASET))
    sub1_level = data.filter(subject='SUB01', task='level_walking')
    
    # Get mean patterns for multiple joints
    mean_patterns = sub1_level.get_mean_patterns('SUB01', 'level_walking')
    
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))
    
    joints = ['hip', 'knee', 'ankle']
    features = [
        'hip_flexion_angle_ipsi_rad',
        'knee_flexion_angle_ipsi_rad',
        'ankle_dorsiflexion_angle_ipsi_rad'
    ]
    
    for idx, (ax, joint, feature) in enumerate(zip(axes, joints, features)):
        if feature in mean_patterns:
            mean = np.degrees(mean_patterns[feature]['mean'])
            std = np.degrees(mean_patterns[feature]['std'])
            phase = mean.index
            
            ax.plot(phase, mean, 'b-', linewidth=2)
            ax.fill_between(phase, mean - std, mean + std, alpha=0.3, color='blue')
            
            ax.set_ylabel(f'{joint.capitalize()} Flexion (deg)', fontsize=11)
            ax.set_title(f'{joint.capitalize()} Joint Angle', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, 100)
    
    axes[-1].set_xlabel('Gait Cycle (%)', fontsize=12)
    
    plt.tight_layout()
    
    # Save plot
    plot_path = PLOT_DIR / 'multi_variable_plot.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    assert plot_path.exists(), "Plot file not created"
    print(f"  Plotted {len(joints)} joints")
    print(f"  Saved plot to: {plot_path.name}")
    print("✓ Multi-variable plot successful")


def test_task_comparison_plot():
    """Test comparing multiple tasks."""
    print("\nTesting task comparison plot...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    tasks = ['level_walking', 'incline_walking', 'decline_walking']
    colors = ['blue', 'red', 'green']
    
    for task, color in zip(tasks, colors):
        task_data = data.filter(subject='SUB01', task=task)
        mean_patterns = task_data.get_mean_patterns('SUB01', task)
        
        if 'knee_flexion_angle_ipsi_rad' in mean_patterns:
            knee_mean = np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad']['mean'])
            knee_std = np.degrees(mean_patterns['knee_flexion_angle_ipsi_rad']['std'])
            phase = knee_mean.index
            
            ax.plot(phase, knee_mean, color=color, linewidth=2, label=task.replace('_', ' ').title())
            ax.fill_between(phase, knee_mean - knee_std, knee_mean + knee_std, 
                           alpha=0.2, color=color)
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=12)
    ax.set_ylabel('Knee Flexion (degrees)', fontsize=12)
    ax.set_title('Knee Flexion Across Different Walking Tasks', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 100)
    
    # Save plot
    plot_path = PLOT_DIR / 'task_comparison_plot.png'
    plt.savefig(plot_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    assert plot_path.exists(), "Plot file not created"
    print(f"  Compared {len(tasks)} tasks")
    print(f"  Saved plot to: {plot_path.name}")
    print("✓ Task comparison plot successful")


def test_library_plotting_methods():
    """Test LocomotionData built-in plotting methods."""
    print("\nTesting library plotting methods...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Test phase pattern plots
    plot_path = PLOT_DIR / 'library_phase_patterns.png'
    data.plot_phase_patterns(
        'SUB01', 'level_walking',
        ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'],
        plot_type='both',
        save_path=str(plot_path)
    )
    assert plot_path.exists(), "Library plot not created"
    print(f"  Created phase pattern plot: {plot_path.name}")
    
    # Test task comparison plot
    plot_path = PLOT_DIR / 'library_task_comparison.png'
    data.plot_task_comparison(
        'SUB01',
        ['level_walking', 'incline_walking'],
        ['knee_flexion_angle_ipsi_rad'],
        save_path=str(plot_path)
    )
    assert plot_path.exists(), "Task comparison plot not created"
    print(f"  Created task comparison plot: {plot_path.name}")
    
    print("✓ Library plotting methods successful")


def cleanup_plots():
    """Remove test plots after successful run."""
    print("\nCleaning up test plots...")
    if PLOT_DIR.exists():
        for plot_file in PLOT_DIR.glob('*.png'):
            plot_file.unlink()
        PLOT_DIR.rmdir()
    print("✓ Cleanup complete")


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TUTORIAL 03: VISUALIZATION")
    print("="*60)
    
    # Check mock dataset exists
    if not MOCK_DATASET.exists():
        print(f"ERROR: Mock dataset not found at {MOCK_DATASET}")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    try:
        setup_plotting()
        
        test_compute_phase_average()
        test_raw_phase_average()
        test_phase_average_plot()
        test_spaghetti_plot()
        test_combined_plot()
        test_multi_variable_plot()
        test_task_comparison_plot()
        test_library_plotting_methods()
        
        cleanup_plots()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
