#!/usr/bin/env python3
"""
Test Tutorial 06: Publication Outputs

Created: 2025-08-07
Purpose: Test all code examples from Tutorial 06 - Publication Outputs

This test validates creation of publication-ready figures, tables, and
statistical reports from the tutorial.
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

# Output directory for publication figures
PLOT_DIR = Path(__file__).parent / 'publication_outputs'
PLOT_DIR.mkdir(parents=True, exist_ok=True)


def setup_publication_style():
    """Set up publication-quality plotting style."""
    # Create output directory
    PLOT_DIR.mkdir(exist_ok=True)
    
    # Set publication style
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['lines.linewidth'] = 1.5
    
    print(f"Publication outputs will be saved to: {PLOT_DIR}")


def test_publication_figure():
    """Test creating publication-quality figure."""
    print("Testing publication figure creation...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Create multi-panel figure
    fig, axes = plt.subplots(2, 3, figsize=(12, 8))
    fig.suptitle('Sagittal Plane Joint Kinematics During Walking', fontsize=14, fontweight='bold')
    
    joints = ['Hip', 'Knee', 'Ankle']
    features = [
        'hip_flexion_angle_ipsi_rad',
        'knee_flexion_angle_ipsi_rad',
        'ankle_dorsiflexion_angle_ipsi_rad'
    ]
    tasks = ['level_walking', 'incline_walking']
    task_labels = ['Level Walking', 'Incline Walking']
    
    for row, (task, task_label) in enumerate(zip(tasks, task_labels)):
        for col, (joint, feature) in enumerate(zip(joints, features)):
            ax = axes[row, col]
            
            # Get group data
            all_patterns = []
            for subject in data.get_subjects():
                mean_patterns = data.get_mean_patterns(subject, task)
                if feature in mean_patterns:
                    pattern = np.degrees(mean_patterns[feature]['mean'].values)
                    all_patterns.append(pattern)
            
            if all_patterns:
                # Calculate group mean and std
                group_array = np.array(all_patterns)
                group_mean = np.mean(group_array, axis=0)
                group_std = np.std(group_array, axis=0)
                phase = np.linspace(0, 100, 150)
                
                # Plot with shading
                ax.plot(phase, group_mean, 'b-', linewidth=2)
                ax.fill_between(phase, 
                               group_mean - group_std,
                               group_mean + group_std,
                               alpha=0.3, color='blue')
                
                # Formatting
                ax.set_xlim(0, 100)
                ax.grid(True, alpha=0.3, linewidth=0.5)
                
                if row == 1:
                    ax.set_xlabel('Gait Cycle (%)')
                if col == 0:
                    ax.set_ylabel(f'{task_label}\nAngle (degrees)')
                if row == 0:
                    ax.set_title(f'{joint} Flexion')
    
    plt.tight_layout()
    
    # Save figure
    fig_path = PLOT_DIR / 'publication_kinematics.png'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    assert fig_path.exists(), "Publication figure not created"
    print(f"  Created figure: {fig_path.name}")
    print("✓ Publication figure successful")


def test_summary_table():
    """Test creating publication-ready summary table."""
    print("\nTesting summary table creation...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Create summary statistics table
    summary_data = []
    
    for subject in data.get_subjects():
        for task in data.get_tasks():
            # Calculate ROM
            rom_data = data.calculate_rom(subject, task)
            
            # Get mean patterns for peak values
            mean_patterns = data.get_mean_patterns(subject, task)
            
            row = {
                'Subject': subject,
                'Task': task.replace('_', ' ').title(),
                'N_Cycles': 5
            }
            
            # Add ROM values
            for joint in ['hip', 'knee', 'ankle']:
                if joint == 'ankle':
                    feature = f'{joint}_dorsiflexion_angle_ipsi_rad'
                else:
                    feature = f'{joint}_flexion_angle_ipsi_rad'
                
                if feature in rom_data:
                    rom_deg = np.degrees(np.mean(rom_data[feature]))
                    row[f'{joint.capitalize()}_ROM'] = f"{rom_deg:.1f}"
                
                if feature in mean_patterns:
                    peak_deg = np.degrees(np.max(mean_patterns[feature]['mean']))
                    row[f'{joint.capitalize()}_Peak'] = f"{peak_deg:.1f}"
            
            summary_data.append(row)
    
    # Create DataFrame
    summary_df = pd.DataFrame(summary_data)
    
    # Group by task and calculate means
    grouped = summary_df.groupby('Task').agg({
        'N_Cycles': 'sum',
        'Hip_ROM': lambda x: f"{np.mean([float(v) for v in x]):.1f} ± {np.std([float(v) for v in x]):.1f}",
        'Knee_ROM': lambda x: f"{np.mean([float(v) for v in x]):.1f} ± {np.std([float(v) for v in x]):.1f}",
        'Ankle_ROM': lambda x: f"{np.mean([float(v) for v in x]):.1f} ± {np.std([float(v) for v in x]):.1f}"
    })
    
    # Save table
    table_path = PLOT_DIR / 'summary_table.csv'
    grouped.to_csv(table_path)
    
    assert table_path.exists(), "Summary table not created"
    print(f"  Created table with {len(summary_df)} rows")
    print(f"  Saved to: {table_path.name}")
    print("\n  Sample of grouped data:")
    print(grouped.head())
    
    print("\n✓ Summary table successful")


def test_statistical_report():
    """Test generating statistical comparison report."""
    print("\nTesting statistical report...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    report_lines = []
    report_lines.append("STATISTICAL ANALYSIS REPORT")
    report_lines.append("="*50)
    report_lines.append("")
    
    # Compare tasks
    report_lines.append("Task Comparison (Level vs Incline Walking)")
    report_lines.append("-"*40)
    
    for feature_name in ['knee_flexion_angle_ipsi_rad']:
        level_values = []
        incline_values = []
        
        for subject in data.get_subjects():
            level_rom = data.calculate_rom(subject, 'level_walking')
            incline_rom = data.calculate_rom(subject, 'incline_walking')
            
            if feature_name in level_rom:
                level_values.extend(level_rom[feature_name])
                incline_values.extend(incline_rom[feature_name])
        
        if level_values and incline_values:
            level_mean = np.degrees(np.mean(level_values))
            level_std = np.degrees(np.std(level_values))
            incline_mean = np.degrees(np.mean(incline_values))
            incline_std = np.degrees(np.std(incline_values))
            
            report_lines.append(f"\nKnee Flexion ROM:")
            report_lines.append(f"  Level Walking:   {level_mean:.1f} ± {level_std:.1f} deg")
            report_lines.append(f"  Incline Walking: {incline_mean:.1f} ± {incline_std:.1f} deg")
            report_lines.append(f"  Difference:      {incline_mean - level_mean:.1f} deg")
            
            # Effect size
            pooled_std = np.sqrt((level_std**2 + incline_std**2) / 2)
            cohens_d = (incline_mean - level_mean) / pooled_std
            report_lines.append(f"  Effect Size:     {cohens_d:.2f}")
    
    # Save report
    report_path = PLOT_DIR / 'statistical_report.txt'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    assert report_path.exists(), "Statistical report not created"
    print(f"  Generated report with {len(report_lines)} lines")
    print(f"  Saved to: {report_path.name}")
    print("✓ Statistical report successful")


def test_export_for_analysis():
    """Test exporting data for external analysis."""
    print("\nTesting data export...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Export wide format for SPSS/R
    export_data = []
    
    for subject in data.get_subjects():
        for task in data.get_tasks():
            cycles_3d, features = data.get_cycles(subject, task)
            
            if cycles_3d is not None:
                # Calculate summary metrics for each cycle
                for cycle_idx in range(cycles_3d.shape[0]):
                    row = {
                        'SubjectID': subject,
                        'Task': task,
                        'CycleNum': cycle_idx + 1
                    }
                    
                    # Add peak and ROM for each feature
                    for feat_idx, feature in enumerate(features):
                        if 'angle' in feature:
                            cycle_data = cycles_3d[cycle_idx, :, feat_idx]
                            row[f'{feature}_peak'] = np.max(cycle_data)
                            row[f'{feature}_rom'] = np.max(cycle_data) - np.min(cycle_data)
                            row[f'{feature}_mean'] = np.mean(cycle_data)
                    
                    export_data.append(row)
    
    # Convert to DataFrame
    export_df = pd.DataFrame(export_data)
    
    # Save in multiple formats
    csv_path = PLOT_DIR / 'data_export.csv'
    export_df.to_csv(csv_path, index=False)
    
    # Save as Excel (if openpyxl available)
    try:
        excel_path = PLOT_DIR / 'data_export.xlsx'
        export_df.to_excel(excel_path, index=False)
        print(f"  Exported to Excel: {excel_path.name}")
    except:
        print("  Note: Excel export skipped (install openpyxl)")
    
    assert csv_path.exists(), "CSV export not created"
    print(f"  Exported {len(export_df)} rows to CSV")
    print(f"  Columns: {len(export_df.columns)}")
    print("✓ Data export successful")


def test_ensemble_average_figure():
    """Test creating ensemble average figure with confidence intervals."""
    print("\nTesting ensemble average figure...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    colors = {'level_walking': 'blue', 'incline_walking': 'red', 'decline_walking': 'green'}
    
    for task, color in colors.items():
        # Collect all cycles across subjects
        all_cycles = []
        
        for subject in data.get_subjects():
            cycles_3d, features = data.get_cycles(subject, task)
            if cycles_3d is not None and 'knee_flexion_angle_ipsi_rad' in features:
                knee_idx = features.index('knee_flexion_angle_ipsi_rad')
                knee_cycles = cycles_3d[:, :, knee_idx]
                all_cycles.append(knee_cycles)
        
        if all_cycles:
            # Stack all cycles
            all_cycles = np.vstack(all_cycles)
            
            # Calculate ensemble statistics
            mean_curve = np.degrees(np.mean(all_cycles, axis=0))
            std_curve = np.degrees(np.std(all_cycles, axis=0))
            n_cycles = all_cycles.shape[0]
            
            # Calculate 95% CI
            sem = std_curve / np.sqrt(n_cycles)
            ci_95 = 1.96 * sem
            
            phase = np.linspace(0, 100, 150)
            
            # Plot mean with CI
            ax.plot(phase, mean_curve, color=color, linewidth=2, 
                   label=f"{task.replace('_', ' ').title()} (n={n_cycles})")
            ax.fill_between(phase, mean_curve - ci_95, mean_curve + ci_95,
                           alpha=0.2, color=color)
    
    ax.set_xlabel('Gait Cycle (%)', fontsize=11)
    ax.set_ylabel('Knee Flexion Angle (degrees)', fontsize=11)
    ax.set_title('Ensemble Average Knee Kinematics with 95% CI', fontsize=12, fontweight='bold')
    ax.legend(loc='best', frameon=True, fancybox=False)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.set_xlim(0, 100)
    
    # Add vertical lines for gait events
    ax.axvline(x=60, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(60, ax.get_ylim()[0] + 2, 'Toe-off', ha='center', fontsize=8)
    
    plt.tight_layout()
    
    # Save figure
    fig_path = PLOT_DIR / 'ensemble_average.png'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    assert fig_path.exists(), "Ensemble figure not created"
    print(f"  Created ensemble figure: {fig_path.name}")
    print("✓ Ensemble average figure successful")


def test_latex_table_generation():
    """Test generating LaTeX-formatted table."""
    print("\nTesting LaTeX table generation...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Create simple summary data
    latex_lines = []
    latex_lines.append("\\begin{table}[h]")
    latex_lines.append("\\centering")
    latex_lines.append("\\caption{Range of Motion Summary (degrees)}")
    latex_lines.append("\\begin{tabular}{lccc}")
    latex_lines.append("\\hline")
    latex_lines.append("Task & Hip & Knee & Ankle \\\\")
    latex_lines.append("\\hline")
    
    for task in ['level_walking', 'incline_walking', 'decline_walking']:
        task_label = task.replace('_', ' ').title()
        
        rom_values = {'hip': [], 'knee': [], 'ankle': []}
        
        for subject in data.get_subjects():
            rom_data = data.calculate_rom(subject, task)
            
            for joint in rom_values.keys():
                if joint == 'ankle':
                    feature = f'{joint}_dorsiflexion_angle_ipsi_rad'
                else:
                    feature = f'{joint}_flexion_angle_ipsi_rad'
                
                if feature in rom_data:
                    rom_values[joint].extend(np.degrees(rom_data[feature]))
        
        # Calculate means and stds
        hip_str = f"{np.mean(rom_values['hip']):.1f} $\\pm$ {np.std(rom_values['hip']):.1f}"
        knee_str = f"{np.mean(rom_values['knee']):.1f} $\\pm$ {np.std(rom_values['knee']):.1f}"
        ankle_str = f"{np.mean(rom_values['ankle']):.1f} $\\pm$ {np.std(rom_values['ankle']):.1f}"
        
        latex_lines.append(f"{task_label} & {hip_str} & {knee_str} & {ankle_str} \\\\")
    
    latex_lines.append("\\hline")
    latex_lines.append("\\end{tabular}")
    latex_lines.append("\\end{table}")
    
    # Save LaTeX table
    latex_path = PLOT_DIR / 'latex_table.tex'
    with open(latex_path, 'w') as f:
        f.write('\n'.join(latex_lines))
    
    assert latex_path.exists(), "LaTeX table not created"
    print(f"  Generated LaTeX table with {len(latex_lines)} lines")
    print(f"  Saved to: {latex_path.name}")
    print("✓ LaTeX table successful")


def cleanup_outputs():
    """Remove publication outputs after successful run."""
    print("\nCleaning up publication outputs...")
    if PLOT_DIR.exists():
        for file in PLOT_DIR.iterdir():
            file.unlink()
        PLOT_DIR.rmdir()
    print("✓ Cleanup complete")


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TUTORIAL 06: PUBLICATION OUTPUTS")
    print("="*60)
    
    # Check mock dataset exists
    if not MOCK_DATASET.exists():
        print(f"ERROR: Mock dataset not found at {MOCK_DATASET}")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    try:
        setup_publication_style()
        
        test_publication_figure()
        test_summary_table()
        test_statistical_report()
        test_export_for_analysis()
        test_ensemble_average_figure()
        test_latex_table_generation()
        
        cleanup_outputs()
        
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
