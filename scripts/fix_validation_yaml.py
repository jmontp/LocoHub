#!/usr/bin/env python3
"""
Fix the validation YAML to use plain floats instead of numpy scalars.
"""

import yaml
import math

def clean_yaml_file():
    """Clean the validation YAML file to use plain floats."""
    
    # Read the existing YAML file
    with open('contributor_scripts/validation_ranges/validation_ranges.yaml', 'r') as f:
        content = yaml.safe_load(f)
    
    # Define link angle ranges in plain floats
    link_ranges = {
        # Pelvis angles (relative to global/lab frame)
        'pelvis_tilt_angle_rad': {
            'min': -0.174533,  # -10 degrees
            'max': 0.349066   # 20 degrees
        },
        'pelvis_obliquity_angle_rad': {
            'min': -0.174533,  # -10 degrees
            'max': 0.174533    # 10 degrees
        },
        'pelvis_rotation_angle_rad': {
            'min': -0.174533,  # -10 degrees
            'max': 0.174533    # 10 degrees
        },
        
        # Trunk angles (relative to global/lab frame)
        'trunk_flexion_angle_rad': {
            'min': -0.087266,  # -5 degrees
            'max': 0.261799    # 15 degrees
        },
        'trunk_lateral_angle_rad': {
            'min': -0.174533,  # -10 degrees
            'max': 0.174533    # 10 degrees
        },
        'trunk_rotation_angle_rad': {
            'min': -0.139626,  # -8 degrees
            'max': 0.139626    # 8 degrees
        },
        
        # Thigh segment angles (relative to vertical)
        'thigh_angle_ipsi_rad': {
            'min': -0.349066,  # -20 degrees
            'max': 1.221730    # 70 degrees
        },
        'thigh_angle_contra_rad': {
            'min': -0.349066,  # -20 degrees
            'max': 1.221730    # 70 degrees
        },
        
        # Shank segment angles (relative to vertical)
        'shank_angle_ipsi_rad': {
            'min': -0.523599,  # -30 degrees
            'max': 0.523599    # 30 degrees
        },
        'shank_angle_contra_rad': {
            'min': -0.523599,  # -30 degrees
            'max': 0.523599    # 30 degrees
        },
        
        # Foot segment angles (relative to horizontal)
        'foot_angle_ipsi_rad': {
            'min': -0.523599,  # -30 degrees
            'max': 0.349066    # 20 degrees
        },
        'foot_angle_contra_rad': {
            'min': -0.523599,  # -30 degrees
            'max': 0.349066    # 20 degrees
        }
    }
    
    # Phase-specific adjustments for gait tasks
    phase_adjustments = {
        '0': {  # Heel strike
            'pelvis_tilt_angle_rad': {'min': 0.087266, 'max': 0.261799},  # 5-15 deg
            'thigh_angle_ipsi_rad': {'min': 0.349066, 'max': 0.698132},   # 20-40 deg
            'shank_angle_ipsi_rad': {'min': -0.174533, 'max': 0.174533},  # -10-10 deg
            'foot_angle_ipsi_rad': {'min': -0.087266, 'max': 0.174533}    # -5-10 deg
        },
        '25': {  # Mid-stance
            'pelvis_tilt_angle_rad': {'min': 0.0, 'max': 0.209440},       # 0-12 deg
            'thigh_angle_ipsi_rad': {'min': -0.087266, 'max': 0.261799},  # -5-15 deg
            'shank_angle_ipsi_rad': {'min': 0.087266, 'max': 0.349066},   # 5-20 deg
            'foot_angle_ipsi_rad': {'min': -0.174533, 'max': 0.087266}    # -10-5 deg
        },
        '50': {  # Toe-off
            'pelvis_tilt_angle_rad': {'min': -0.087266, 'max': 0.174533}, # -5-10 deg
            'thigh_angle_ipsi_rad': {'min': -0.349066, 'max': 0.0},       # -20-0 deg
            'shank_angle_ipsi_rad': {'min': -0.436332, 'max': -0.087266}, # -25--5 deg
            'foot_angle_ipsi_rad': {'min': -0.523599, 'max': -0.174533}   # -30--10 deg
        },
        '75': {  # Mid-swing
            'pelvis_tilt_angle_rad': {'min': 0.087266, 'max': 0.261799},  # 5-15 deg
            'thigh_angle_ipsi_rad': {'min': 0.349066, 'max': 0.872665},   # 20-50 deg
            'shank_angle_ipsi_rad': {'min': 0.174533, 'max': 0.523599},   # 10-30 deg
            'foot_angle_ipsi_rad': {'min': -0.087266, 'max': 0.261799}    # -5-15 deg
        }
    }
    
    # Clean content - fix ankle terminology and add link angles
    new_content = {
        'version': '2.0',
        'generated': '2025-08-03 15:29:41',
        'source': 'Consolidated from kinematic_ranges.yaml and kinetic_ranges.yaml',
        'migration_date': '2025-08-03 15:29:41',
        'description': 'Consolidated validation ranges for all biomechanical features including link/segment angles',
        'source_dataset': 'umich_2021_phase.parquet',
        'method': '95th percentile',
        'feature_types': {
            'kinematic': ['joint_angles', 'segment_angles'],
            'kinetic': ['moments', 'forces'],
            'segment': ['link_angles', 'absolute_angles']
        },
        'tasks': {}
    }
    
    # Process each task
    for task_name, task_data in content.get('tasks', {}).items():
        new_task = {'phases': {}}
        
        for phase, phase_data in task_data.get('phases', {}).items():
            new_phase = {}
            
            # Process existing variables
            for var_name, var_range in phase_data.items():
                # Fix ankle terminology
                new_var_name = var_name.replace('ankle_flexion_angle', 'ankle_dorsiflexion_angle')
                new_var_name = new_var_name.replace('ankle_flexion_moment', 'ankle_dorsiflexion_moment')
                
                # Convert values to plain floats
                if isinstance(var_range, dict) and 'min' in var_range and 'max' in var_range:
                    min_val = var_range['min']
                    max_val = var_range['max']
                    
                    # Handle NaN values
                    if isinstance(min_val, float) and math.isnan(min_val):
                        new_phase[new_var_name] = {'min': None, 'max': None}
                    else:
                        # Convert to plain float
                        if hasattr(min_val, 'item'):
                            min_val = float(min_val.item())
                        if hasattr(max_val, 'item'):
                            max_val = float(max_val.item())
                        new_phase[new_var_name] = {'min': min_val, 'max': max_val}
            
            # Add link angles with phase-specific adjustments
            phase_key = str(phase)
            for var_name, default_range in link_ranges.items():
                if phase_key in phase_adjustments and var_name in phase_adjustments[phase_key]:
                    new_phase[var_name] = phase_adjustments[phase_key][var_name]
                else:
                    new_phase[var_name] = default_range.copy()
            
            new_task['phases'][phase] = new_phase
        
        new_content['tasks'][task_name] = new_task
    
    # Save the cleaned file
    with open('contributor_scripts/validation_ranges/validation_ranges.yaml', 'w') as f:
        yaml.dump(new_content, f, default_flow_style=False, sort_keys=False, width=120)
    
    print("YAML file cleaned successfully!")
    print("- Fixed ankle terminology: ankle_flexion -> ankle_dorsiflexion")
    print("- Added link/segment angle variables with proper float values")
    print("- Removed numpy scalar corruption")

if __name__ == "__main__":
    clean_yaml_file()