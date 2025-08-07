#!/usr/bin/env python3
"""
Mock Dataset Generator for Testing

Created: 2025-08-07
Purpose: Generate a small, reproducible mock dataset for testing tutorials

This script creates a mock phase-indexed locomotion dataset with:
- 3 subjects (SUB01, SUB02, SUB03)
- 3 tasks (level_walking, incline_walking, decline_walking)
- 5 cycles per subject/task combination
- 150 points per cycle (0-100% gait cycle)
- Realistic biomechanical patterns using parameterized sine waves
- Smooth variation between cycles by adding noise to parameters, not output
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add parent directory for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from user_libs.python.feature_constants import (
    ANGLE_FEATURES,
    MOMENT_FEATURES,
    SEGMENT_ANGLE_FEATURES
)


def generate_sine_wave(phase_percent, base_params, noise_scale=0.1):
    """
    Generate a sine wave with parameter noise for realistic variation.
    
    Parameters:
    -----------
    phase_percent : array
        Phase values from 0 to 100
    base_params : dict
        Base parameters: amplitude, phase_shift, offset, frequency
    noise_scale : float
        Scale of gaussian noise to add to parameters
    
    Returns:
    --------
    array : Generated sine wave
    """
    # Add noise to parameters, not output
    amplitude = base_params['amplitude'] * (1 + np.random.randn() * noise_scale)
    phase_shift = base_params['phase_shift'] + np.random.randn() * noise_scale
    offset = base_params['offset'] + np.random.randn() * noise_scale * 0.1
    frequency = base_params.get('frequency', 1.0)
    
    # Generate smooth sine wave
    return amplitude * np.sin(2 * np.pi * frequency * phase_percent / 100 + phase_shift) + offset


def get_joint_parameters(joint, motion, task):
    """
    Get realistic base parameters for each joint/motion/task combination.
    
    Parameters are based on typical biomechanical ranges (in radians).
    """
    params = {}
    
    # Task-specific modifiers
    task_modifier = {
        'level_walking': 1.0,
        'incline_walking': 1.1,  # Slightly increased range for incline
        'decline_walking': 0.9   # Slightly decreased range for decline
    }
    
    # Hip flexion (typical range: -20 to 40 degrees = -0.35 to 0.70 rad)
    if joint == 'hip' and 'flexion' in motion:
        params = {
            'amplitude': 0.52 * task_modifier[task],
            'phase_shift': 0,
            'offset': 0.17,
            'frequency': 1.0
        }
    
    # Knee flexion (typical range: 0 to 70 degrees = 0 to 1.22 rad)
    elif joint == 'knee' and 'flexion' in motion:
        params = {
            'amplitude': 0.61 * task_modifier[task],
            'phase_shift': -np.pi/4,  # Knee lags hip
            'offset': 0.61,  # Center around 35 degrees
            'frequency': 1.0
        }
    
    # Ankle dorsiflexion (typical range: -20 to 20 degrees = -0.35 to 0.35 rad)
    elif joint == 'ankle' and 'dorsiflexion' in motion:
        params = {
            'amplitude': 0.35 * task_modifier[task],
            'phase_shift': -np.pi/2,  # Ankle lags knee
            'offset': 0,
            'frequency': 1.0
        }
    
    # Joint moments (normalized, typical range: -2 to 2 Nm/kg)
    elif 'moment' in motion:
        params = {
            'amplitude': 1.0 * task_modifier[task],
            'phase_shift': np.random.uniform(-np.pi, np.pi),
            'offset': 0,
            'frequency': 1.0 if 'flexion' in motion else 2.0  # Double frequency for adduction
        }
    
    # Segment angles (pelvis, trunk, thigh, shank, foot)
    elif joint in ['pelvis', 'trunk']:
        params = {
            'amplitude': 0.1 * task_modifier[task],  # Small motion
            'phase_shift': np.random.uniform(-np.pi, np.pi),
            'offset': 0.05,
            'frequency': 1.0 if 'sagittal' in motion else 2.0
        }
    elif joint in ['thigh', 'shank', 'foot']:
        params = {
            'amplitude': 0.3 * task_modifier[task],
            'phase_shift': np.random.uniform(-np.pi, np.pi),
            'offset': 0.1,
            'frequency': 1.0
        }
    
    # Default parameters for anything else
    else:
        params = {
            'amplitude': 0.2,
            'phase_shift': 0,
            'offset': 0,
            'frequency': 1.0
        }
    
    return params


def generate_mock_dataset():
    """
    Generate the complete mock dataset.
    
    Returns:
    --------
    DataFrame : Mock phase-indexed locomotion data
    """
    # Configuration
    subjects = ['SUB01', 'SUB02', 'SUB03']
    tasks = ['level_walking', 'incline_walking', 'decline_walking']
    n_cycles = 5
    points_per_cycle = 150
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Collect all data
    all_data = []
    
    for subject in subjects:
        for task in tasks:
            for cycle_id in range(n_cycles):
                # Generate phase percent (0-100)
                phase_percent = np.linspace(0, 100, points_per_cycle, endpoint=False)
                
                # Initialize data for this cycle
                cycle_data = {
                    'subject': [subject] * points_per_cycle,
                    'task': [task] * points_per_cycle,
                    'cycle_id': [f"{subject}_{task}_{cycle_id:03d}"] * points_per_cycle,
                    'phase_percent': phase_percent,
                    'phase_ipsi': phase_percent,  # LocomotionData expects this column
                    'phase_contra': phase_percent  # Add contra as well for completeness
                }
                
                # Generate kinematic angles
                for feature in ANGLE_FEATURES:
                    # Parse feature name
                    parts = feature.split('_')
                    joint = parts[0]
                    motion = '_'.join(parts[1:-2])  # Handle multi-word motions
                    side = parts[-2]
                    
                    # Get base parameters
                    params = get_joint_parameters(joint, motion, task)
                    
                    # Add slight offset for contralateral side
                    if side == 'contra':
                        params['phase_shift'] += 0.5 * np.pi  # Half cycle offset
                    
                    # Generate data
                    cycle_data[feature] = generate_sine_wave(phase_percent, params, noise_scale=0.1)
                
                # Generate selected kinetic moments (subset for smaller file)
                selected_moments = [
                    'hip_flexion_moment_ipsi_Nm',
                    'hip_flexion_moment_contra_Nm',
                    'knee_flexion_moment_ipsi_Nm',
                    'knee_flexion_moment_contra_Nm',
                    'ankle_dorsiflexion_moment_ipsi_Nm',
                    'ankle_dorsiflexion_moment_contra_Nm'
                ]
                
                for feature in selected_moments:
                    parts = feature.split('_')
                    joint = parts[0]
                    motion = '_'.join(parts[1:-2])
                    side = parts[-2]
                    
                    params = get_joint_parameters(joint, 'moment', task)
                    
                    if side == 'contra':
                        params['phase_shift'] += 0.5 * np.pi
                    
                    # Scale moments by subject "body weight" (60-80 kg)
                    body_weight = 60 + int(subject[-2:]) * 10
                    params['amplitude'] *= body_weight
                    
                    cycle_data[feature] = generate_sine_wave(phase_percent, params, noise_scale=0.15)
                
                # Generate selected segment angles
                selected_segments = [
                    'pelvis_sagittal_angle_rad',
                    'trunk_sagittal_angle_rad',
                    'thigh_sagittal_angle_ipsi_rad',
                    'thigh_sagittal_angle_contra_rad',
                    'shank_sagittal_angle_ipsi_rad',
                    'shank_sagittal_angle_contra_rad'
                ]
                
                for feature in selected_segments:
                    parts = feature.split('_')
                    segment = parts[0]
                    plane = parts[1]
                    
                    params = get_joint_parameters(segment, plane, task)
                    
                    if 'contra' in feature:
                        params['phase_shift'] += 0.5 * np.pi
                    
                    cycle_data[feature] = generate_sine_wave(phase_percent, params, noise_scale=0.1)
                
                # Convert to DataFrame and append
                cycle_df = pd.DataFrame(cycle_data)
                all_data.append(cycle_df)
    
    # Combine all cycles
    dataset = pd.concat(all_data, ignore_index=True)
    
    # Add metadata columns
    dataset['dataset'] = 'mock_dataset'
    dataset['collection_date'] = '2025-08-07'
    dataset['processing_date'] = '2025-08-07'
    
    return dataset


def main():
    """Generate and save the mock dataset."""
    print("Generating mock dataset...")
    
    # Generate dataset
    dataset = generate_mock_dataset()
    
    # Create output directory
    output_dir = Path(__file__).parent / 'mock_data'
    output_dir.mkdir(exist_ok=True)
    
    # Save as parquet
    output_file = output_dir / 'mock_dataset_phase.parquet'
    dataset.to_parquet(output_file, index=False)
    
    # Print summary
    print(f"\nDataset generated successfully!")
    print(f"Location: {output_file}")
    print(f"Shape: {dataset.shape}")
    print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"\nSubjects: {dataset['subject'].unique().tolist()}")
    print(f"Tasks: {dataset['task'].unique().tolist()}")
    print(f"Cycles per subject/task: {dataset.groupby(['subject', 'task'])['cycle_id'].nunique().iloc[0]}")
    print(f"Features: {len(dataset.columns) - 7} biomechanical variables")
    print(f"\nSample features:")
    biomech_cols = [col for col in dataset.columns if col not in 
                    ['subject', 'task', 'cycle_id', 'phase_percent', 'dataset', 'collection_date', 'processing_date']]
    for col in biomech_cols[:5]:
        print(f"  - {col}")
    print(f"  ... and {len(biomech_cols) - 5} more")


if __name__ == "__main__":
    main()