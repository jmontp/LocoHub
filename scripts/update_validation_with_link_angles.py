#!/usr/bin/env python3
"""
Update validation configuration with link angles and fix ankle terminology.
"""

import yaml
import math
from pathlib import Path

def update_validation_config():
    """Update the validation configuration with link angles and fix terminology."""
    
    # Load existing config
    config_path = Path('contributor_scripts/validation_ranges/validation_ranges.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Update metadata
    config['description'] = 'Consolidated validation ranges for all biomechanical features including link/segment angles'
    config['feature_types'] = {
        'kinematic': ['joint_angles', 'segment_angles'],
        'kinetic': ['moments', 'forces'],
        'segment': ['link_angles', 'absolute_angles']
    }
    
    # Define link angle ranges
    link_ranges = {
        # Pelvis angles (relative to global/lab frame)
        'pelvis_tilt_angle_rad': {'min': -0.175, 'max': 0.349},  # -10 to 20 degrees
        'pelvis_obliquity_angle_rad': {'min': -0.175, 'max': 0.175},  # -10 to 10 degrees
        'pelvis_rotation_angle_rad': {'min': -0.175, 'max': 0.175},  # -10 to 10 degrees
        
        # Trunk angles (relative to global/lab frame)
        'trunk_flexion_angle_rad': {'min': -0.087, 'max': 0.262},  # -5 to 15 degrees
        'trunk_lateral_angle_rad': {'min': -0.175, 'max': 0.175},  # -10 to 10 degrees
        'trunk_rotation_angle_rad': {'min': -0.140, 'max': 0.140},  # -8 to 8 degrees
        
        # Thigh segment angles (relative to vertical)
        'thigh_angle_ipsi_rad': {'min': -0.349, 'max': 1.222},  # -20 to 70 degrees
        'thigh_angle_contra_rad': {'min': -0.349, 'max': 1.222},  # -20 to 70 degrees
        
        # Shank segment angles (relative to vertical)
        'shank_angle_ipsi_rad': {'min': -0.524, 'max': 0.524},  # -30 to 30 degrees
        'shank_angle_contra_rad': {'min': -0.524, 'max': 0.524},  # -30 to 30 degrees
        
        # Foot segment angles (relative to horizontal)
        'foot_angle_ipsi_rad': {'min': -0.524, 'max': 0.349},  # -30 to 20 degrees
        'foot_angle_contra_rad': {'min': -0.524, 'max': 0.349}   # -30 to 20 degrees
    }
    
    # Phase-specific adjustments for gait tasks
    phase_adjustments = {
        '0': {  # Heel strike
            'pelvis_tilt_angle_rad': {'min': 0.087, 'max': 0.262},  # 5-15 deg
            'thigh_angle_ipsi_rad': {'min': 0.349, 'max': 0.698},   # 20-40 deg
            'thigh_angle_contra_rad': {'min': -0.349, 'max': 0.175}, # Different for contra at heel strike
            'shank_angle_ipsi_rad': {'min': -0.175, 'max': 0.175},  # -10-10 deg
            'shank_angle_contra_rad': {'min': 0.175, 'max': 0.524}, # Different for contra
            'foot_angle_ipsi_rad': {'min': -0.087, 'max': 0.175},   # -5-10 deg
            'foot_angle_contra_rad': {'min': -0.349, 'max': -0.087} # Different for contra
        },
        '25': {  # Mid-stance
            'pelvis_tilt_angle_rad': {'min': 0.0, 'max': 0.209},    # 0-12 deg
            'thigh_angle_ipsi_rad': {'min': -0.087, 'max': 0.262},  # -5-15 deg
            'thigh_angle_contra_rad': {'min': 0.524, 'max': 1.047}, # Different for contra
            'shank_angle_ipsi_rad': {'min': 0.087, 'max': 0.349},   # 5-20 deg
            'shank_angle_contra_rad': {'min': -0.175, 'max': 0.262}, # Different for contra
            'foot_angle_ipsi_rad': {'min': -0.175, 'max': 0.087},   # -10-5 deg
            'foot_angle_contra_rad': {'min': -0.087, 'max': 0.175}  # Different for contra
        },
        '50': {  # Toe-off (50% is contralateral heel strike for gait)
            'pelvis_tilt_angle_rad': {'min': -0.087, 'max': 0.175}, # -5-10 deg
            'thigh_angle_ipsi_rad': {'min': -0.349, 'max': 0.0},    # -20-0 deg
            'thigh_angle_contra_rad': {'min': 0.349, 'max': 0.698}, # Contra at heel strike
            'shank_angle_ipsi_rad': {'min': -0.436, 'max': -0.087}, # -25--5 deg
            'shank_angle_contra_rad': {'min': -0.175, 'max': 0.175}, # Contra at heel strike
            'foot_angle_ipsi_rad': {'min': -0.524, 'max': -0.175},  # -30--10 deg
            'foot_angle_contra_rad': {'min': -0.087, 'max': 0.175}  # Contra at heel strike
        },
        '75': {  # Mid-swing
            'pelvis_tilt_angle_rad': {'min': 0.087, 'max': 0.262},  # 5-15 deg
            'thigh_angle_ipsi_rad': {'min': 0.349, 'max': 0.873},   # 20-50 deg
            'thigh_angle_contra_rad': {'min': -0.087, 'max': 0.262}, # Contra in mid-stance
            'shank_angle_ipsi_rad': {'min': 0.175, 'max': 0.524},   # 10-30 deg
            'shank_angle_contra_rad': {'min': 0.087, 'max': 0.349}, # Contra in mid-stance
            'foot_angle_ipsi_rad': {'min': -0.087, 'max': 0.262},   # -5-15 deg
            'foot_angle_contra_rad': {'min': -0.175, 'max': 0.087}  # Contra in mid-stance
        }
    }
    
    # Process each task
    for task_name, task_data in config.get('tasks', {}).items():
        if 'phases' not in task_data:
            task_data['phases'] = {}
        
        for phase, phase_data in task_data['phases'].items():
            # Fix ankle terminology and add link angles
            new_phase_data = {}
            
            # Process existing variables
            for var_name, var_range in phase_data.items():
                # Fix ankle terminology
                new_var_name = var_name
                if 'ankle_flexion_angle' in var_name:
                    new_var_name = var_name.replace('ankle_flexion_angle', 'ankle_dorsiflexion_angle')
                elif 'ankle_flexion_moment' in var_name:
                    new_var_name = var_name.replace('ankle_flexion_moment', 'ankle_dorsiflexion_moment')
                
                # Handle NaN values for moments
                if isinstance(var_range, dict):
                    min_val = var_range.get('min')
                    max_val = var_range.get('max')
                    if isinstance(min_val, float) and math.isnan(min_val):
                        new_phase_data[new_var_name] = {'min': None, 'max': None}
                    else:
                        new_phase_data[new_var_name] = var_range
                else:
                    new_phase_data[new_var_name] = var_range
            
            # Add link angles with phase-specific adjustments
            phase_str = str(phase)
            for var_name, default_range in link_ranges.items():
                if phase_str in phase_adjustments and var_name in phase_adjustments[phase_str]:
                    new_phase_data[var_name] = phase_adjustments[phase_str][var_name]
                else:
                    new_phase_data[var_name] = default_range.copy()
            
            task_data['phases'][phase] = new_phase_data
    
    # Save the updated configuration
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120, allow_unicode=True)
    
    print("✅ Validation configuration updated successfully!")
    print(f"  - Fixed ankle terminology: ankle_flexion -> ankle_dorsiflexion")
    print(f"  - Added {len(link_ranges)} link/segment angle variables")
    print(f"  - Applied phase-specific adjustments for gait tasks")
    print(f"  - Saved to: {config_path}")

if __name__ == "__main__":
    update_validation_config()