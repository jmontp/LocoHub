"""
Mapping between current implementation naming convention and target documentation convention.

Current pattern: <joint>_<measurement>_<plane>_<side>
Target pattern: <joint>_<motion>_<measurement>_<side>_<unit> (with ipsi/contra specified)

This module provides the mapping needed to transition from the implemented naming
to the documented naming convention using ipsilateral/contralateral terminology.
"""

# Mapping from current names to new names
NAMING_MAPPING = {
    # Hip angles (sagittal plane)
    'hip_angle_s_r': 'hip_flexion_angle_rad',
    'hip_angle_s_l': 'hip_flexion_angle_rad',  # Will need _ipsi suffix
    
    # Hip angles (frontal plane)
    'hip_angle_f_r': 'hip_adduction_angle_rad',
    'hip_angle_f_l': 'hip_adduction_angle_rad',  # Will need _ipsi suffix
    
    # Hip angles (transverse plane)
    'hip_angle_t_r': 'hip_rotation_angle_rad',
    'hip_angle_t_l': 'hip_rotation_angle_rad',  # Will need _ipsi suffix
    
    # Knee angles (sagittal plane)
    'knee_angle_s_r': 'knee_flexion_angle_rad',
    'knee_angle_s_l': 'knee_flexion_angle_rad',  # Will need _ipsi suffix
    
    # Ankle angles (sagittal plane)
    'ankle_angle_s_r': 'ankle_flexion_angle_rad',
    'ankle_angle_s_l': 'ankle_flexion_angle_rad',  # Will need _ipsi suffix
    
    # Ankle angles (frontal plane)
    'ankle_angle_f_r': 'ankle_inversion_angle_rad',
    'ankle_angle_f_l': 'ankle_inversion_angle_rad',  # Will need _ipsi suffix
    
    # Ankle angles (transverse plane)
    'ankle_angle_t_r': 'ankle_rotation_angle_rad',
    'ankle_angle_t_l': 'ankle_rotation_angle_rad',  # Will need _ipsi suffix
    
    # Hip velocities
    'hip_vel_s_r': 'hip_flexion_velocity_rad_s',
    'hip_vel_s_l': 'hip_flexion_velocity_rad_s',  # Will need _ipsi suffix
    'hip_vel_f_r': 'hip_adduction_velocity_rad_s',
    'hip_vel_f_l': 'hip_adduction_velocity_rad_s',  # Will need _ipsi suffix
    'hip_vel_t_r': 'hip_rotation_velocity_rad_s',
    'hip_vel_t_l': 'hip_rotation_velocity_rad_s',  # Will need _ipsi suffix
    
    # Knee velocities
    'knee_vel_s_r': 'knee_flexion_velocity_rad_s',
    'knee_vel_s_l': 'knee_flexion_velocity_rad_s',  # Will need _ipsi suffix
    
    # Ankle velocities
    'ankle_vel_s_r': 'ankle_flexion_velocity_rad_s',
    'ankle_vel_s_l': 'ankle_flexion_velocity_rad_s',  # Will need _ipsi suffix
    'ankle_vel_f_r': 'ankle_inversion_velocity_rad_s',
    'ankle_vel_f_l': 'ankle_inversion_velocity_rad_s',  # Will need _ipsi suffix
    'ankle_vel_t_r': 'ankle_rotation_velocity_rad_s',
    'ankle_vel_t_l': 'ankle_rotation_velocity_rad_s',  # Will need _ipsi suffix
    
    # Hip torques/moments
    'hip_torque_s_r': 'hip_moment_Nm',
    'hip_torque_s_l': 'hip_moment_Nm',  # Will need _ipsi suffix
    'hip_torque_f_r': 'hip_moment_frontal_Nm',  # Not in docs, but following pattern
    'hip_torque_f_l': 'hip_moment_frontal_Nm',  # Will need _ipsi suffix
    'hip_torque_t_r': 'hip_moment_transverse_Nm',  # Not in docs, but following pattern
    'hip_torque_t_l': 'hip_moment_transverse_Nm',  # Will need _ipsi suffix
    
    # Knee torques/moments
    'knee_torque_s_r': 'knee_moment_Nm',
    'knee_torque_s_l': 'knee_moment_Nm',  # Will need _ipsi suffix
    
    # Ankle torques/moments
    'ankle_torque_s_r': 'ankle_moment_Nm',
    'ankle_torque_s_l': 'ankle_moment_Nm',  # Will need _ipsi suffix
}

# Function to handle ipsi/contra suffixes
def apply_side_suffix(new_name, old_name):
    """
    Apply ipsi/contra suffix to the new name based on the old name.
    
    Using ipsilateral/contralateral terminology:
    - _contra for contralateral side (right side in original convention)
    - _ipsi for ipsilateral side (left side in original convention)
    """
    if old_name.endswith('_l'):
        # Ipsilateral side - add _ipsi before unit
        if '_rad' in new_name:
            base, unit = new_name.rsplit('_rad', 1)
            return f"{base}_ipsi_rad{unit}"
        elif '_Nm' in new_name:
            base = new_name.rsplit('_Nm', 1)[0]
            return f"{base}_ipsi_Nm"
        elif '_rad_s' in new_name:
            base = new_name.rsplit('_rad_s', 1)[0]
            return f"{base}_ipsi_rad_s"
        else:
            return f"{new_name}_ipsi"
    else:
        # Contralateral side - add _contra suffix
        if '_rad' in new_name:
            base, unit = new_name.rsplit('_rad', 1)
            return f"{base}_contra_rad{unit}"
        elif '_Nm' in new_name:
            base = new_name.rsplit('_Nm', 1)[0]
            return f"{base}_contra_Nm"
        elif '_rad_s' in new_name:
            base = new_name.rsplit('_rad_s', 1)[0]
            return f"{base}_contra_rad_s"
        else:
            return f"{new_name}_contra"

def get_new_column_name(old_name):
    """Convert old column name to new column name with ipsi/contra suffix."""
    if old_name in NAMING_MAPPING:
        new_name = NAMING_MAPPING[old_name]
        return apply_side_suffix(new_name, old_name)
    return old_name  # Return unchanged if not in mapping

def get_all_old_column_names():
    """Get a list of all old column names that need to be changed."""
    return list(NAMING_MAPPING.keys())

def get_all_new_column_names():
    """Get a list of all new column names (with ipsi/contra suffixes)."""
    new_names = []
    for old_name, base_new_name in NAMING_MAPPING.items():
        new_names.append(apply_side_suffix(base_new_name, old_name))
    return new_names

# Create reverse mapping for going from new to old names
def create_reverse_mapping():
    """Create a mapping from new ipsi/contra names back to old names."""
    reverse_map = {}
    for old_name in NAMING_MAPPING:
        new_name = get_new_column_name(old_name)
        reverse_map[new_name] = old_name
    return reverse_map

REVERSE_MAPPING = create_reverse_mapping()

if __name__ == "__main__":
    # Print example mappings
    print("Example naming convention mappings (ipsi/contra):")
    print("-" * 60)
    examples = [
        'hip_angle_s_r', 'hip_angle_s_l',
        'knee_torque_s_r', 'knee_torque_s_l',
        'ankle_vel_f_r', 'ankle_vel_f_l'
    ]
    for old_name in examples:
        new_name = get_new_column_name(old_name)
        print(f"{old_name:20} -> {new_name}")
    
    print("\nNote: _l maps to _ipsi (ipsilateral), _r maps to _contra (contralateral)")