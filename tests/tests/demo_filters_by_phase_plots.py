#!/usr/bin/env python3
"""
Demonstration Script for filters_by_phase_plots.py

Created: 2025-06-10
Purpose: Generate comprehensive demonstration plots showcasing the step data and color 
         classification functionality of the filters_by_phase_plots.py module.

Intent:
This script demonstrates the key features of the unified filters by phase plotting system:

1. **Baseline Validation Ranges**: Shows validation boundaries without any data overlay
2. **Step Data Integration**: Demonstrates how to overlay actual step data (150 time points × 6 features)
3. **Step Color Classification System**: Showcases the three-color validation system:
   - Gray: Valid steps with no violations
   - Red: Steps with local violations (violations in the current subplot's feature)
   - Pink: Steps with other violations (violations in different features)
4. **Kinematic vs Kinetic Modes**: Shows both joint angle and force/moment validation
5. **Gait Pattern Visualization**: Realistic biomechanical patterns across gait phases

Output:
Generates 6 demonstration plots in source/tests/sample_plots/demo_filters_by_phase_plots/:
- Baseline validation ranges only
- All valid steps (gray lines)
- Mixed violation scenarios (red/pink/gray)
- All local violations (red lines)
- All other violations (pink lines)
- Kinetic baseline example

Usage:
    python3 source/tests/demo_filters_by_phase_plots.py

This demo helps developers understand how to:
- Structure step data arrays for the plotting function
- Use step color arrays to highlight different violation types
- Interpret the resulting validation plots
- Integrate the plotting system with validation workflows
"""

import numpy as np
import sys
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Add directories to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from lib.validation.filters_by_phase_plots import create_filters_by_phase_plot


def create_demo_plots():
    """Create demonstration plots showing step color functionality"""
    
    # Create output directory (now in tests folder)
    output_dir = Path(__file__).parent / "sample_plots" / "demo_filters_by_phase_plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Creating demo plots in: {output_dir}")
    
    # Create validation data
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
    
    # Create step data with realistic gait patterns
    num_steps = 8
    num_points = 150
    num_features = 6
    
    data = np.zeros((num_steps, num_points, num_features))
    phase_percent = np.linspace(0, 100, num_points)
    
    # Create realistic gait patterns for each step
    for step in range(num_steps):
        step_offset = (step - 4) * 0.02  # Small variation per step
        
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
    
    # Add specific violations to some steps for demonstration
    # Step 0: Hip violation (too high)
    data[0, :, 0] += 0.5
    
    # Step 2: Knee violation (too high) 
    data[2, :, 2] += 0.8
    
    # Step 4: Ankle violation (too low)
    data[4, :, 4] -= 0.4
    
    # Step 6: Multiple violations
    data[6, :, 0] += 0.4  # Hip
    data[6, :, 4] -= 0.3  # Ankle
    
    # Demo scenarios with different step color patterns
    scenarios = [
        {
            'name': '1_no_data_baseline',
            'description': 'Baseline validation ranges only (no step data)',
            'data': None,
            'step_colors': None
        },
        {
            'name': '2_all_valid_steps',
            'description': 'All steps valid (all gray)',
            'data': data,
            'step_colors': np.array(['gray'] * num_steps)
        },
        {
            'name': '3_mixed_violations',
            'description': 'Mixed violation types (red=local, pink=other, gray=valid)',
            'data': data,
            'step_colors': np.array(['red', 'gray', 'red', 'pink', 'red', 'gray', 'red', 'pink'])
        },
        {
            'name': '4_all_local_violations',
            'description': 'All steps with local violations (all red)',
            'data': data,
            'step_colors': np.array(['red'] * num_steps)
        },
        {
            'name': '5_all_other_violations',
            'description': 'All steps with other violations (all pink)',
            'data': data,
            'step_colors': np.array(['pink'] * num_steps)
        }
    ]
    
    generated_files = []
    
    for scenario in scenarios:
        print(f"\n🎨 Generating scenario: {scenario['name']}")
        print(f"   📋 {scenario['description']}")
        
        try:
            filepath = create_filters_by_phase_plot(
                validation_data=validation_data,
                task_name='level_walking',
                output_dir=str(output_dir),
                mode='kinematic',
                data=scenario['data'],
                step_colors=scenario['step_colors']
            )
            
            # Rename file to include scenario name
            original_name = Path(filepath).name
            new_name = f"{scenario['name']}_{original_name}"
            new_filepath = output_dir / new_name
            
            os.rename(filepath, new_filepath)
            generated_files.append(str(new_filepath))
            
            print(f"   ✅ Generated: {new_filepath.name}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Generate a kinetic example too
    print(f"\n🔬 Generating kinetic example...")
    
    kinetic_validation_data = {
        'level_walking': {
            0: {
                'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3},
                'knee_moment_ipsi_Nm_kg': {'min': -0.2, 'max': 0.1},
                'ankle_moment_ipsi_Nm_kg': {'min': -0.3, 'max': 0.3},
                'hip_moment_contra_Nm_kg': {'min': 0.3, 'max': 1.1},
                'knee_moment_contra_Nm_kg': {'min': -0.6, 'max': -0.1},
                'ankle_moment_contra_Nm_kg': {'min': -1.6, 'max': -1.2}
            },
            25: {
                'hip_moment_ipsi_Nm_kg': {'min': -1.0, 'max': -0.2},
                'knee_moment_ipsi_Nm_kg': {'min': -0.4, 'max': 0.2},
                'ankle_moment_ipsi_Nm_kg': {'min': 0.5, 'max': 1.5},
                'hip_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.2},
                'knee_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.3},
                'ankle_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.1}
            },
            50: {
                'hip_moment_ipsi_Nm_kg': {'min': 0.3, 'max': 1.1},
                'knee_moment_ipsi_Nm_kg': {'min': -0.6, 'max': -0.1},
                'ankle_moment_ipsi_Nm_kg': {'min': -1.6, 'max': -1.2},
                'hip_moment_contra_Nm_kg': {'min': -0.1, 'max': 0.3},
                'knee_moment_contra_Nm_kg': {'min': -0.2, 'max': 0.1},
                'ankle_moment_contra_Nm_kg': {'min': -0.3, 'max': 0.3}
            },
            75: {
                'hip_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.2},
                'knee_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.3},
                'ankle_moment_ipsi_Nm_kg': {'min': -0.1, 'max': 0.1},
                'hip_moment_contra_Nm_kg': {'min': -1.0, 'max': -0.2},
                'knee_moment_contra_Nm_kg': {'min': -0.4, 'max': 0.2},
                'ankle_moment_contra_Nm_kg': {'min': 0.5, 'max': 1.5}
            }
        }
    }
    
    try:
        kinetic_filepath = create_filters_by_phase_plot(
            validation_data=kinetic_validation_data,
            task_name='level_walking',
            output_dir=str(output_dir),
            mode='kinetic'
        )
        
        # Rename kinetic file
        new_kinetic_name = f"6_kinetic_baseline_{Path(kinetic_filepath).name}"
        new_kinetic_filepath = output_dir / new_kinetic_name
        os.rename(kinetic_filepath, new_kinetic_filepath)
        generated_files.append(str(new_kinetic_filepath))
        
        print(f"   ✅ Generated: {new_kinetic_filepath.name}")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print(f"\n🎉 Demo complete! Generated {len(generated_files)} plots:")
    for filepath in generated_files:
        print(f"   📄 {Path(filepath).name}")
    
    print(f"\n📂 View plots at: {output_dir}")
    return generated_files


if __name__ == "__main__":
    create_demo_plots()