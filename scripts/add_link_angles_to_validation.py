#!/usr/bin/env python3
"""
Add link/segment angles to validation configuration and fix ankle terminology.
"""

import yaml
import numpy as np
from pathlib import Path

def deg_to_rad(deg):
    """Convert degrees to radians."""
    return np.radians(deg)

def create_link_angle_ranges():
    """Create educated ranges for link/segment angles based on biomechanical literature."""
    
    # All ranges in radians (converted from degrees)
    link_ranges = {
        # Pelvis angles (relative to global/lab frame)
        'pelvis_tilt_angle_rad': {
            'min': deg_to_rad(-10),
            'max': deg_to_rad(20)
        },
        'pelvis_obliquity_angle_rad': {
            'min': deg_to_rad(-10),
            'max': deg_to_rad(10)
        },
        'pelvis_rotation_angle_rad': {
            'min': deg_to_rad(-10),
            'max': deg_to_rad(10)
        },
        
        # Trunk angles (relative to global/lab frame)
        'trunk_flexion_angle_rad': {
            'min': deg_to_rad(-5),
            'max': deg_to_rad(15)
        },
        'trunk_lateral_angle_rad': {
            'min': deg_to_rad(-10),
            'max': deg_to_rad(10)
        },
        'trunk_rotation_angle_rad': {
            'min': deg_to_rad(-8),
            'max': deg_to_rad(8)
        },
        
        # Thigh segment angles (relative to vertical)
        'thigh_angle_ipsi_rad': {
            'min': deg_to_rad(-20),
            'max': deg_to_rad(70)
        },
        'thigh_angle_contra_rad': {
            'min': deg_to_rad(-20),
            'max': deg_to_rad(70)
        },
        
        # Shank segment angles (relative to vertical)
        'shank_angle_ipsi_rad': {
            'min': deg_to_rad(-30),
            'max': deg_to_rad(30)
        },
        'shank_angle_contra_rad': {
            'min': deg_to_rad(-30),
            'max': deg_to_rad(30)
        },
        
        # Foot segment angles (relative to horizontal)
        'foot_angle_ipsi_rad': {
            'min': deg_to_rad(-30),
            'max': deg_to_rad(20)
        },
        'foot_angle_contra_rad': {
            'min': deg_to_rad(-30),
            'max': deg_to_rad(20)
        }
    }
    
    return link_ranges

def fix_ankle_terminology(data):
    """Replace ankle_flexion with ankle_dorsiflexion throughout the configuration."""
    
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            # Fix the key if it contains ankle_flexion
            new_key = key.replace('ankle_flexion_angle', 'ankle_dorsiflexion_angle')
            new_key = new_key.replace('ankle_flexion_moment', 'ankle_dorsiflexion_moment')
            
            # Recursively process the value
            new_data[new_key] = fix_ankle_terminology(value)
        return new_data
    elif isinstance(data, list):
        return [fix_ankle_terminology(item) for item in data]
    else:
        return data

def add_link_angles_to_task_phases(task_data, link_ranges):
    """Add link angle ranges to all phases of a task."""
    
    # Get phase-specific adjustments for gait tasks
    # These are rough estimates based on typical gait biomechanics
    phase_adjustments = {
        '0': {  # Heel strike
            'pelvis_tilt_angle_rad': {'min': deg_to_rad(5), 'max': deg_to_rad(15)},
            'thigh_angle_ipsi_rad': {'min': deg_to_rad(20), 'max': deg_to_rad(40)},
            'shank_angle_ipsi_rad': {'min': deg_to_rad(-10), 'max': deg_to_rad(10)},
            'foot_angle_ipsi_rad': {'min': deg_to_rad(-5), 'max': deg_to_rad(10)}
        },
        '25': {  # Mid-stance
            'pelvis_tilt_angle_rad': {'min': deg_to_rad(0), 'max': deg_to_rad(12)},
            'thigh_angle_ipsi_rad': {'min': deg_to_rad(-5), 'max': deg_to_rad(15)},
            'shank_angle_ipsi_rad': {'min': deg_to_rad(5), 'max': deg_to_rad(20)},
            'foot_angle_ipsi_rad': {'min': deg_to_rad(-10), 'max': deg_to_rad(5)}
        },
        '50': {  # Toe-off
            'pelvis_tilt_angle_rad': {'min': deg_to_rad(-5), 'max': deg_to_rad(10)},
            'thigh_angle_ipsi_rad': {'min': deg_to_rad(-20), 'max': deg_to_rad(0)},
            'shank_angle_ipsi_rad': {'min': deg_to_rad(-25), 'max': deg_to_rad(-5)},
            'foot_angle_ipsi_rad': {'min': deg_to_rad(-30), 'max': deg_to_rad(-10)}
        },
        '75': {  # Mid-swing
            'pelvis_tilt_angle_rad': {'min': deg_to_rad(5), 'max': deg_to_rad(15)},
            'thigh_angle_ipsi_rad': {'min': deg_to_rad(20), 'max': deg_to_rad(50)},
            'shank_angle_ipsi_rad': {'min': deg_to_rad(10), 'max': deg_to_rad(30)},
            'foot_angle_ipsi_rad': {'min': deg_to_rad(-5), 'max': deg_to_rad(15)}
        }
    }
    
    # Add link angles to each phase
    for phase, phase_data in task_data.get('phases', {}).items():
        if str(phase).isdigit():
            # Get phase-specific ranges or use defaults
            phase_key = str(phase)
            
            for var_name, default_range in link_ranges.items():
                # Use phase-specific adjustment if available
                if phase_key in phase_adjustments and var_name in phase_adjustments[phase_key]:
                    phase_data[var_name] = phase_adjustments[phase_key][var_name]
                else:
                    # Use default range
                    phase_data[var_name] = default_range.copy()
    
    return task_data

def main():
    """Main function to update validation configuration."""
    
    # Path to validation config
    config_path = Path('contributor_scripts/validation_ranges/validation_ranges.yaml')
    
    # Load existing configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Fix ankle terminology throughout
    print("Fixing ankle terminology (flexion -> dorsiflexion)...")
    config = fix_ankle_terminology(config)
    
    # Get link angle ranges
    link_ranges = create_link_angle_ranges()
    
    # Add link angles to each task
    print("Adding link/segment angles to validation configuration...")
    for task_name in config.get('tasks', {}):
        print(f"  Processing task: {task_name}")
        config['tasks'][task_name] = add_link_angles_to_task_phases(
            config['tasks'][task_name], 
            link_ranges
        )
    
    # Update metadata
    config['description'] = 'Consolidated validation ranges for all biomechanical features including link/segment angles'
    config['feature_types'] = {
        'kinematic': ['joint_angles', 'segment_angles'],
        'kinetic': ['moments', 'forces'],
        'segment': ['link_angles', 'absolute_angles']
    }
    
    # Save updated configuration
    output_path = config_path
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120)
    
    print(f"\nConfiguration updated successfully!")
    print(f"  - Fixed ankle terminology: ankle_flexion -> ankle_dorsiflexion")
    print(f"  - Added {len(link_ranges)} link/segment angle variables")
    print(f"  - Updated {len(config.get('tasks', {}))} tasks")
    print(f"  - Saved to: {output_path}")

if __name__ == "__main__":
    main()