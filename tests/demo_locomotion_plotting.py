#!/usr/bin/env python3
"""
Demonstration Script for LocomotionData Plotting Utilities

Created: 2025-06-11 with user permission
Purpose: Comprehensive demonstration of the LocomotionData plotting capabilities showing
         how to use the plotting methods for phase-normalized locomotion data visualization.

Intent:
This script demonstrates the key plotting features of the LocomotionData library:

1. **Phase Pattern Plotting**: Spaghetti plots, mean±std, and combined visualizations
2. **Task Comparison Plotting**: Cross-task mean pattern comparison  
3. **Time Series Plotting**: Time-indexed data visualization
4. **Custom Plotting**: Advanced customization using raw 3D data access
5. **Validation Integration**: Automatic validation overlay with color coding

Output:
Generates demonstration plots in tests/sample_plots/demo_locomotion_plotting/:
- Phase pattern plots (spaghetti, mean, combined modes)
- Task comparison plots with multiple tasks
- Time series plots for time-indexed data
- Custom plotting examples with percentiles and styling
- Validation overlay demonstrations

Usage:
    python3 tests/demo_locomotion_plotting.py

This demo helps developers understand:
- How to visualize phase-normalized locomotion data
- Different plotting modes and their appropriate use cases
- Integration with biomechanical validation systems
- Custom plotting techniques for advanced analysis
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory to path for lib imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def print_banner(title):
    """Print a formatted banner for demo sections."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def demo_setup_data():
    """Create demonstration dataset with realistic biomechanical patterns."""
    print_banner("Setting Up Demonstration Data")
    
    # Create synthetic locomotion data with multiple subjects and tasks
    subjects = ['SUB01', 'SUB02', 'SUB03']
    tasks = ['level_walking', 'incline_walking', 'decline_walking']
    n_cycles = 5
    points_per_cycle = 150
    
    all_data = []
    
    for subject in subjects:
        for task in tasks:
            for cycle in range(n_cycles):
                # Create realistic phase progression
                phase = np.linspace(0, 100, points_per_cycle)
                
                # Generate realistic biomechanical patterns
                # Hip flexion: ~20-30 degrees peak
                hip_base = 0.4 if 'incline' in task else 0.3 if 'decline' in task else 0.35
                hip_flexion = hip_base * np.sin(2 * np.pi * phase / 100) + 0.05 * np.random.randn(points_per_cycle)
                
                # Knee flexion: ~60-70 degrees peak, offset from hip
                knee_base = 1.1 if 'incline' in task else 0.9 if 'decline' in task else 1.0
                knee_flexion = knee_base * np.sin(2 * np.pi * phase / 100 + np.pi/6) + 0.1 * np.random.randn(points_per_cycle)
                
                # Ankle dorsiflexion: ~15-20 degrees, different phase
                ankle_base = 0.25 if 'incline' in task else 0.15 if 'decline' in task else 0.2
                ankle_flexion = ankle_base * np.sin(2 * np.pi * phase / 100 - np.pi/3) + 0.05 * np.random.randn(points_per_cycle)
                
                # Add some subject-specific variation
                subject_factor = 1.0 + 0.1 * int(subject[-1]) - 0.15
                hip_flexion *= subject_factor
                knee_flexion *= subject_factor * 1.05
                ankle_flexion *= subject_factor * 0.95
                
                # Create time series
                time_s = np.linspace(cycle * 1.2, (cycle + 1) * 1.2, points_per_cycle)
                
                # Create data for this cycle
                cycle_data = pd.DataFrame({
                    'subject': subject,
                    'task': task,
                    'step': cycle,
                    'phase_percent': phase,
                    'time_s': time_s,
                    'hip_flexion_angle_contra_rad': hip_flexion,
                    'knee_flexion_angle_contra_rad': knee_flexion,
                    'ankle_flexion_angle_contra_rad': ankle_flexion,
                    'hip_flexion_angle_ipsi_rad': hip_flexion * 0.95 + 0.02 * np.random.randn(points_per_cycle),
                    'knee_flexion_angle_ipsi_rad': knee_flexion * 1.02 + 0.05 * np.random.randn(points_per_cycle),
                    'ankle_flexion_angle_ipsi_rad': ankle_flexion * 0.98 + 0.03 * np.random.randn(points_per_cycle)
                })
                
                all_data.append(cycle_data)
    
    # Combine all data
    df = pd.concat(all_data, ignore_index=True)
    
    print(f"✓ Created demonstration dataset:")
    print(f"  - Subjects: {len(subjects)} ({', '.join(subjects)})")
    print(f"  - Tasks: {len(tasks)} ({', '.join(tasks)})")
    print(f"  - Cycles per subject-task: {n_cycles}")
    print(f"  - Total data points: {len(df):,}")
    
    return df

def demo_phase_pattern_plotting(loco):
    """Demonstrate phase pattern plotting with different modes."""
    print_banner("Phase Pattern Plotting Demonstration")
    
    subject = loco.get_subjects()[0]
    task = loco.get_tasks()[0]
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad']
    
    output_dir = Path("sample_plots/demo_locomotion_plotting")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Plotting for {subject} - {task}")
    
    # 1. Spaghetti plot - show all individual cycles
    print("1. Creating spaghetti plot (individual cycles)...")
    loco.plot_phase_patterns(subject, task, features, 
                            plot_type='spaghetti',
                            save_path=str(output_dir / '1_spaghetti_plot.png'))
    print("   ✓ Saved: 1_spaghetti_plot.png")
    
    # 2. Mean ± standard deviation plot
    print("2. Creating mean±std plot with confidence bands...")
    loco.plot_phase_patterns(subject, task, features,
                            plot_type='mean', 
                            save_path=str(output_dir / '2_mean_std_plot.png'))
    print("   ✓ Saved: 2_mean_std_plot.png")
    
    # 3. Combined plot - both individual cycles and mean
    print("3. Creating combined plot (both modes)...")
    loco.plot_phase_patterns(subject, task, features,
                            plot_type='both',
                            save_path=str(output_dir / '3_combined_plot.png'))
    print("   ✓ Saved: 3_combined_plot.png")
    
    print(f"\n📊 Phase pattern plots demonstrate:")
    print(f"   - Gray lines: Valid cycles passing biomechanical validation")
    print(f"   - Red lines: Invalid cycles failing validation criteria")
    print(f"   - Blue line: Mean pattern across valid cycles only")
    print(f"   - Blue shaded area: ±1 standard deviation (in mean mode)")

def demo_task_comparison_plotting(loco):
    """Demonstrate task comparison plotting."""
    print_banner("Task Comparison Plotting Demonstration")
    
    subject = loco.get_subjects()[0]
    tasks = loco.get_tasks()
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
    
    output_dir = Path("sample_plots/demo_locomotion_plotting")
    
    if len(tasks) > 1:
        print(f"Comparing tasks for {subject}: {', '.join(tasks)}")
        
        # Compare all available tasks
        loco.plot_task_comparison(subject, tasks, features,
                                 save_path=str(output_dir / '4_task_comparison.png'))
        print("   ✓ Saved: 4_task_comparison.png")
        
        # Compare specific tasks
        if len(tasks) >= 2:
            loco.plot_task_comparison(subject, tasks[:2], features,
                                     save_path=str(output_dir / '5_two_task_comparison.png'))
            print("   ✓ Saved: 5_two_task_comparison.png")
        
        print(f"\n📊 Task comparison plots show:")
        print(f"   - Mean patterns for each task overlaid")
        print(f"   - Different colors for each task")
        print(f"   - Clear visualization of task-specific differences")
    else:
        print("⚠️  Only one task available - skipping task comparison")

def demo_time_series_plotting(loco):
    """Demonstrate time series plotting."""
    print_banner("Time Series Plotting Demonstration") 
    
    subject = loco.get_subjects()[0]
    task = loco.get_tasks()[0]
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
    
    output_dir = Path("sample_plots/demo_locomotion_plotting")
    
    if 'time_s' in loco.df.columns:
        print(f"Creating time series plot for {subject} - {task}")
        
        loco.plot_time_series(subject, task, features,
                             time_col='time_s',
                             save_path=str(output_dir / '6_time_series.png'))
        print("   ✓ Saved: 6_time_series.png")
        
        print(f"\n📊 Time series plots show:")
        print(f"   - Raw time-indexed data progression")
        print(f"   - Multiple gait cycles in sequence")
        print(f"   - Useful for identifying temporal patterns")
    else:
        print("⚠️  No time_s column available - skipping time series plotting")

def demo_custom_plotting(loco):
    """Demonstrate custom plotting with raw 3D data access."""
    print_banner("Custom Plotting Demonstration")
    
    import matplotlib.pyplot as plt
    plt.style.use('default')  # Ensure consistent style
    
    subject = loco.get_subjects()[0]
    task = loco.get_tasks()[0]
    features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad']
    
    output_dir = Path("sample_plots/demo_locomotion_plotting")
    
    print(f"Creating custom plots for {subject} - {task}")
    
    # Get 3D data and validation
    data_3d, feature_names = loco.get_cycles(subject, task, features)
    valid_mask = loco.validate_cycles(subject, task, features)
    
    if data_3d is not None:
        # Custom percentile plot
        fig, axes = plt.subplots(1, len(feature_names), figsize=(15, 4))
        if len(feature_names) == 1:
            axes = [axes]
        
        phase_x = np.linspace(0, 100, 150)
        
        for i, feature in enumerate(feature_names):
            feat_data = data_3d[:, :, i]
            valid_data = feat_data[valid_mask, :]
            
            if len(valid_data) > 0:
                # Calculate percentiles
                p10 = np.percentile(valid_data, 10, axis=0)
                p25 = np.percentile(valid_data, 25, axis=0)
                p50 = np.percentile(valid_data, 50, axis=0)  # Median
                p75 = np.percentile(valid_data, 75, axis=0)
                p90 = np.percentile(valid_data, 90, axis=0)
                
                # Plot with custom styling
                axes[i].fill_between(phase_x, p10, p90, alpha=0.2, 
                                   color='lightblue', label='10-90th percentile')
                axes[i].fill_between(phase_x, p25, p75, alpha=0.4, 
                                   color='lightblue', label='25-75th percentile')
                axes[i].plot(phase_x, p50, 'navy', linewidth=2, label='Median')
                
                axes[i].set_xlabel('Gait Cycle (%)')
                axes[i].set_ylabel(feature.replace('_', ' ').title())
                axes[i].set_title(feature.replace('_', ' ').title(), fontsize=10)
                axes[i].grid(True, alpha=0.3)
                axes[i].set_xlim([0, 100])
                if i == 0:
                    axes[i].legend(loc='upper right', fontsize=8)
        
        plt.suptitle(f'{subject} - {task}: Custom Percentile Analysis', fontsize=12)
        plt.tight_layout()
        plt.savefig(str(output_dir / '7_custom_percentile_plot.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("   ✓ Saved: 7_custom_percentile_plot.png")
        
        # Validation overlay demonstration
        fig, axes = plt.subplots(1, len(feature_names), figsize=(15, 4))
        if len(feature_names) == 1:
            axes = [axes]
        
        for i, feature in enumerate(feature_names):
            feat_data = data_3d[:, :, i]
            valid_data = feat_data[valid_mask, :]
            invalid_data = feat_data[~valid_mask, :]
            
            # Plot individual cycles with validation coloring
            for cycle in valid_data:
                axes[i].plot(phase_x, cycle, 'gray', alpha=0.4, linewidth=0.8)
            for cycle in invalid_data:
                axes[i].plot(phase_x, cycle, 'red', alpha=0.6, linewidth=0.8)
            
            # Plot mean
            if len(valid_data) > 0:
                mean_curve = np.mean(valid_data, axis=0)
                axes[i].plot(phase_x, mean_curve, 'blue', linewidth=3, label='Mean (valid cycles)')
            
            axes[i].set_xlabel('Gait Cycle (%)')
            axes[i].set_ylabel(feature.replace('_', ' ').title())
            axes[i].set_title(feature.replace('_', ' ').title(), fontsize=10)
            axes[i].grid(True, alpha=0.3)
            axes[i].set_xlim([0, 100])
            if i == 0:
                axes[i].legend(['Valid cycles', 'Invalid cycles', 'Mean'], loc='upper right', fontsize=8)
        
        plt.suptitle(f'{subject} - {task}: Validation Overlay Demo (Valid: {np.sum(valid_mask)}/{len(valid_mask)})', fontsize=12)
        plt.tight_layout()
        plt.savefig(str(output_dir / '8_validation_overlay_demo.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("   ✓ Saved: 8_validation_overlay_demo.png")
        
        print(f"\n📊 Custom plotting demonstrates:")
        print(f"   - Access to raw 3D data arrays for advanced analysis")
        print(f"   - Percentile-based visualization (10th, 25th, 50th, 75th, 90th)")
        print(f"   - Custom validation overlay with color coding")
        print(f"   - High-resolution export capabilities")
    else:
        print("⚠️  No valid data found for custom plotting")

def main():
    """Run all demonstrations."""
    print("🎨 LocomotionData Plotting Utilities Demonstration")
    print("="*60)
    
    try:
        # Import library
        from lib.core.locomotion_analysis import LocomotionData
        print("✓ Successfully imported LocomotionData library")
        
        # Set up matplotlib for demo
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend for demo
        import matplotlib.pyplot as plt
        
        # Create demonstration data
        df = demo_setup_data()
        
        # Save demo data for inspection
        demo_file = 'demo_locomotion_data.csv'
        df.to_csv(demo_file, index=False)
        print(f"✓ Saved demonstration data to {demo_file}")
        
        # Initialize LocomotionData
        loco = LocomotionData(demo_file, file_type='csv')
        
        # Run demonstrations
        demo_phase_pattern_plotting(loco)
        demo_task_comparison_plotting(loco)
        demo_time_series_plotting(loco)
        demo_custom_plotting(loco)
        
        print_banner("Demo Complete")
        print("🎉 All plotting demonstrations completed successfully!")
        print(f"📁 Generated plots saved in: sample_plots/demo_locomotion_plotting/")
        print(f"📊 Generated {len(list(Path('sample_plots/demo_locomotion_plotting').glob('*.png')))} demonstration plots")
        
        # Cleanup demo data
        if os.path.exists(demo_file):
            os.remove(demo_file)
            print(f"✓ Cleaned up demo data file")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Please ensure the locomotion_analysis library is available")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()