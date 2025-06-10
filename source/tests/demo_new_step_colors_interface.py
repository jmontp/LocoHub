#!/usr/bin/env python3
"""
Demo script showing the new step_colors interface for filters_by_phase_plots.py

This demonstrates the cleaner separation of concerns where:
1. Validation logic is handled externally 
2. Plotting function just focuses on visualization
3. Step classification is passed as a simple array
"""

import numpy as np
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add source directories to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source' / 'visualization'))
sys.path.append(str(project_root / 'source'))

from filters_by_phase_plots import (
    create_filters_by_phase_plot, 
    classify_step_violations
)


def demo_new_interface():
    """Demonstrate the new step_colors interface"""
    print("🎨 Demo: New step_colors interface for filters_by_phase_plots")
    print("=" * 60)
    
    # Create simple validation data
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
            }
        }
    }
    
    # Create test data
    num_steps = 5
    num_points = 150
    num_features = 6
    
    data = np.random.randn(num_steps, num_points, num_features) * 0.1 + 0.3
    
    print("\n1. Basic plot without step colors (all gray):")
    temp_dir = tempfile.mkdtemp()
    try:
        filepath = create_filters_by_phase_plot(
            validation_data=validation_data,
            task_name='level_walking',
            output_dir=temp_dir,
            mode='kinematic',
            data=data
        )
        print(f"   ✅ Generated: {filepath}")
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n2. Plot with custom step colors:")
    # Create custom step classification
    step_colors = np.array(['gray', 'red', 'pink', 'gray', 'red'])  # 5 steps
    
    temp_dir = tempfile.mkdtemp()
    try:
        filepath = create_filters_by_phase_plot(
            validation_data=validation_data,
            task_name='level_walking',
            output_dir=temp_dir,
            mode='kinematic',
            data=data,
            step_colors=step_colors
        )
        print(f"   ✅ Generated: {filepath}")
        print(f"   Step colors used: {step_colors}")
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n3. Plot with automatic validation-based step colors:")
    # Use built-in classification function
    feature_map = {
        ('hip_flexion_angle', 'ipsi'): 0,
        ('hip_flexion_angle', 'contra'): 1,
        ('knee_flexion_angle', 'ipsi'): 2,
        ('knee_flexion_angle', 'contra'): 3,
        ('ankle_flexion_angle', 'ipsi'): 4,
        ('ankle_flexion_angle', 'contra'): 5
    }
    
    # Classify steps for hip ipsi feature (index 0)
    auto_step_colors = classify_step_violations(
        data, validation_data['level_walking'], feature_map, 'kinematic', 0
    )
    
    temp_dir = tempfile.mkdtemp()
    try:
        filepath = create_filters_by_phase_plot(
            validation_data=validation_data,
            task_name='level_walking',
            output_dir=temp_dir,
            mode='kinematic',
            data=data,
            step_colors=auto_step_colors
        )
        print(f"   ✅ Generated: {filepath}")
        print(f"   Auto-classified colors: {auto_step_colors}")
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n🎉 Demo completed! Key benefits of new interface:")
    print("   • Clean separation: validation logic vs plotting logic")
    print("   • Flexible: use any step classification method")
    print("   • Simple: just pass an array of colors")
    print("   • Backwards compatible: still includes helper functions")


if __name__ == "__main__":
    demo_new_interface()