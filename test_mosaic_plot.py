#!/usr/bin/env python3
"""
Test script to verify mosaic plot PNG export functionality
This creates synthetic data matching the standard format and tests the export
"""

import numpy as np
import sys
import os

# Add the source directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'source', 'visualization'))

def create_test_data():
    """Create synthetic phase-indexed data matching the standard format"""
    print("Creating synthetic test data...")
    
    # Standard: 150 points per gait cycle
    POINTS_PER_CYCLE = 150
    num_subjects = 3
    num_cycles_per_subject = 5
    
    # Create data for level_walking task
    data = []
    
    for subj_idx in range(num_subjects):
        subject_id = f"TEST_S{subj_idx+1:02d}"
        
        for cycle in range(num_cycles_per_subject):
            # Generate phase values 0-100 for each cycle
            phase = np.linspace(0, 100, POINTS_PER_CYCLE)
            
            # Generate synthetic joint angles (in radians)
            # Hip: ~0.3 to 0.6 rad range
            hip_angle = 0.45 + 0.15 * np.sin(2 * np.pi * phase / 100) + 0.05 * np.random.randn(POINTS_PER_CYCLE)
            
            # Knee: ~0.95 to 1.2 rad range  
            knee_angle = 1.075 + 0.125 * np.sin(2 * np.pi * phase / 100 - np.pi/4) + 0.05 * np.random.randn(POINTS_PER_CYCLE)
            
            # Ankle: ~-0.3 to 0.25 rad range
            ankle_angle = -0.025 + 0.275 * np.sin(2 * np.pi * phase / 100 - np.pi/2) + 0.05 * np.random.randn(POINTS_PER_CYCLE)
            
            # Create rows for this cycle
            for i in range(POINTS_PER_CYCLE):
                data.append({
                    'subject_id': subject_id,
                    'task_name': 'level_walking',
                    'phase_r': phase[i],
                    'hip_angle_s_r': hip_angle[i],
                    'knee_angle_s_r': knee_angle[i],
                    'ankle_angle_s_r': ankle_angle[i],
                    'time_s': cycle * 1.2 + i * 0.008  # ~150Hz sampling
                })
    
    return data

def test_png_export():
    """Test the PNG export functionality"""
    print("\n=== Testing Mosaic Plot PNG Export ===\n")
    
    # Check if required modules are available
    try:
        import pandas as pd
        import plotly.graph_objects as go
        print("✓ pandas and plotly are available")
    except ImportError as e:
        print(f"✗ Missing required module: {e}")
        print("\nTo test PNG export, you need to install:")
        print("  python3 -m pip install pandas plotly kaleido pyarrow")
        return
    
    # Create test dataframe
    test_data = create_test_data()
    df = pd.DataFrame(test_data)
    
    print(f"\nCreated test dataset:")
    print(f"  Shape: {df.shape}")
    print(f"  Subjects: {df['subject_id'].nunique()}")
    print(f"  Tasks: {df['task_name'].unique()}")
    print(f"  Points per subject: {len(df) // df['subject_id'].nunique()}")
    
    # Verify data compliance
    print("\nVerifying standard compliance:")
    for subject in df['subject_id'].unique():
        subj_data = df[df['subject_id'] == subject]
        points = len(subj_data)
        cycles = points / 150
        if points % 150 == 0:
            print(f"  ✓ {subject}: {points} points ({int(cycles)} complete cycles)")
        else:
            print(f"  ✗ {subject}: {points} points ({cycles:.2f} cycles) - NOT COMPLIANT")
    
    # Test the mosaic plotter
    print("\nTesting mosaic plotter...")
    try:
        from mozaic_plot import visualize_tasks
        
        # Run with PNG export
        output_dir = "test_plots"
        figs = visualize_tasks(
            df,
            phase_col='phase_r',
            subject_col='subject_id', 
            task_col='task_name',
            features=['hip_angle_s_r', 'knee_angle_s_r', 'ankle_angle_s_r'],
            plots_dir=output_dir,
            diagnostic_mode=True,
            export_png=True
        )
        
        print(f"\n✓ Successfully generated {len(figs)} plots")
        
        # Check for PNG files
        png_dir = os.path.join(output_dir, "png")
        if os.path.exists(png_dir):
            png_files = [f for f in os.listdir(png_dir) if f.endswith('.png')]
            print(f"\nPNG files created in {png_dir}:")
            for png in png_files:
                print(f"  - {png}")
        else:
            print(f"\n✗ PNG directory not created at {png_dir}")
            
    except Exception as e:
        print(f"\n✗ Error during plotting: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_png_export()