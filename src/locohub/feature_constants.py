#!/usr/bin/env python3
"""
Locomotion Data Feature Constants

Created: 2025-06-11 with user permission
Purpose: Centralized feature definitions and mappings for the LocomotionData library

Intent:
This module provides the single source of truth for biomechanical feature ordering and mappings
used throughout the locomotion data standardization framework. It defines the canonical feature
order that matches plotting function expectations and ensures consistency across all components.

The feature order defined here matches the plotting function expectations:
[hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra]

**PRIMARY FUNCTIONS:**
1. **Standard Feature Arrays**: Defines canonical feature ordering for kinematic/kinetic variables
2. **Feature Index Mappings**: Maps variable names to array indices for consistent access
3. **Cross-System Consistency**: Ensures LocomotionData, validation, and visualization all align

Usage:
    from lib.python.feature_constants import ANGLE_FEATURES, MOMENT_FEATURES, get_kinematic_feature_map
    
    # Get ordered feature list
    features = ANGLE_FEATURES  # ['hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad', ...]
    
    # Get feature index mapping
    feature_map = get_kinematic_feature_map()  # {'hip_flexion_angle_ipsi_rad': 0, ...}
    
    # Check feature order
    data_array = data[:, :, feature_map['knee_flexion_angle_ipsi_rad']]  # Always gets correct index
"""

from typing import Dict

from internal.config_management import task_registry as _task_registry

# Metadata and time/phase columns
METADATA_COLUMNS = [
    'subject',
    'subject_metadata',
    'task',
    'task_id',
    'task_info',
    'step',
]
PHASE_COLUMNS = ['phase_ipsi', 'phase_contra', 'phase_ipsi_dot']
TIME_COLUMNS = ['time_s']

# Standard feature groups - ordered to match plotting function expectations
# Order: [hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra]

# Kinematic features (joint angles)
ANGLE_FEATURES = [
    'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', 
    'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
]

# Kinematic velocities (joint velocities)
VELOCITY_FEATURES = [
    'hip_flexion_velocity_ipsi_rad_s', 'hip_flexion_velocity_contra_rad_s',
    'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s',
    'ankle_dorsiflexion_velocity_ipsi_rad_s', 'ankle_dorsiflexion_velocity_contra_rad_s'
]

# Kinematic accelerations (joint accelerations)
ACCELERATION_FEATURES = [
    'hip_flexion_acceleration_ipsi_rad_s2', 'hip_flexion_acceleration_contra_rad_s2',
    'knee_flexion_acceleration_ipsi_rad_s2', 'knee_flexion_acceleration_contra_rad_s2',
    'ankle_dorsiflexion_acceleration_ipsi_rad_s2', 'ankle_dorsiflexion_acceleration_contra_rad_s2'
]

# Segment angular velocities
SEGMENT_VELOCITY_FEATURES = [
    'pelvis_sagittal_velocity_rad_s', 'pelvis_frontal_velocity_rad_s', 'pelvis_transverse_velocity_rad_s',
    'trunk_sagittal_velocity_rad_s', 'trunk_frontal_velocity_rad_s', 'trunk_transverse_velocity_rad_s',
    'thigh_sagittal_velocity_ipsi_rad_s', 'thigh_sagittal_velocity_contra_rad_s',
    'shank_sagittal_velocity_ipsi_rad_s', 'shank_sagittal_velocity_contra_rad_s',
    'foot_sagittal_velocity_ipsi_rad_s', 'foot_sagittal_velocity_contra_rad_s'
]

# Kinetic features (joint moments) - Standard order: [hip, knee, ankle] x [flexion, adduction, rotation] x [ipsi, contra]
MOMENT_FEATURES = [
    'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
    'hip_adduction_moment_ipsi_Nm', 'hip_adduction_moment_contra_Nm',
    'hip_rotation_moment_ipsi_Nm', 'hip_rotation_moment_contra_Nm',
    'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
    'knee_adduction_moment_ipsi_Nm', 'knee_adduction_moment_contra_Nm',
    'knee_rotation_moment_ipsi_Nm', 'knee_rotation_moment_contra_Nm',
    'ankle_dorsiflexion_moment_ipsi_Nm', 'ankle_dorsiflexion_moment_contra_Nm',
    'ankle_adduction_moment_ipsi_Nm', 'ankle_adduction_moment_contra_Nm',
    'ankle_rotation_moment_ipsi_Nm', 'ankle_rotation_moment_contra_Nm'
]

# Alternative kinetic features (normalized by body weight)
MOMENT_FEATURES_NORMALIZED = [
    'hip_flexion_moment_ipsi_Nm_kg', 'hip_flexion_moment_contra_Nm_kg',
    'hip_adduction_moment_ipsi_Nm_kg', 'hip_adduction_moment_contra_Nm_kg',
    'hip_rotation_moment_ipsi_Nm_kg', 'hip_rotation_moment_contra_Nm_kg',
    'knee_flexion_moment_ipsi_Nm_kg', 'knee_flexion_moment_contra_Nm_kg',
    'knee_adduction_moment_ipsi_Nm_kg', 'knee_adduction_moment_contra_Nm_kg',
    'knee_rotation_moment_ipsi_Nm_kg', 'knee_rotation_moment_contra_Nm_kg',
    'ankle_dorsiflexion_moment_ipsi_Nm_kg', 'ankle_dorsiflexion_moment_contra_Nm_kg',
    'ankle_adduction_moment_ipsi_Nm_kg', 'ankle_adduction_moment_contra_Nm_kg',
    'ankle_rotation_moment_ipsi_Nm_kg', 'ankle_rotation_moment_contra_Nm_kg'
]

# Ground reaction force features (raw)
# Naming: <signal_type>_<axis>_<leg_side>_<unit>
# Example: grf_vertical_ipsi_N
GRF_FEATURES = [
    'grf_vertical_ipsi_N', 'grf_vertical_contra_N',
    'grf_anterior_ipsi_N', 'grf_anterior_contra_N',
    'grf_lateral_ipsi_N', 'grf_lateral_contra_N'
]

# Ground reaction force features (weight-normalized)
# Example: grf_vertical_ipsi_BW
GRF_FEATURES_NORMALIZED = [
    'grf_vertical_ipsi_BW', 'grf_vertical_contra_BW',
    'grf_anterior_ipsi_BW', 'grf_anterior_contra_BW',
    'grf_lateral_ipsi_BW', 'grf_lateral_contra_BW'
]

# Center of pressure features
# Naming already follows: <signal_type>_<axis>_<leg_side>_<unit>
COP_FEATURES = [
    'cop_anterior_ipsi_m', 'cop_anterior_contra_m',
    'cop_lateral_ipsi_m', 'cop_lateral_contra_m',
    'cop_vertical_ipsi_m', 'cop_vertical_contra_m'
]

# Segment angle features (link/segment orientations in space)
# Uses anatomical plane naming convention:
# - Sagittal plane: flexion/extension movements (forward/backward tilt)
# - Frontal plane: abduction/adduction movements (side-to-side tilt)
# - Transverse plane: rotation movements (axial rotation for long bones)
SEGMENT_ANGLE_FEATURES = [
    'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad',
    'trunk_sagittal_angle_rad', 'trunk_frontal_angle_rad', 'trunk_transverse_angle_rad', 
    'thigh_sagittal_angle_ipsi_rad', 'thigh_sagittal_angle_contra_rad',
    'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_contra_rad',
    'foot_sagittal_angle_ipsi_rad', 'foot_sagittal_angle_contra_rad'
]

# All kinetic features combined
ALL_KINETIC_FEATURES = MOMENT_FEATURES + MOMENT_FEATURES_NORMALIZED + GRF_FEATURES + GRF_FEATURES_NORMALIZED + COP_FEATURES

# All kinematic features combined (angles + segments + velocities + accelerations)
ALL_KINEMATIC_FEATURES = (
    ANGLE_FEATURES
    + SEGMENT_ANGLE_FEATURES
    + VELOCITY_FEATURES
    + ACCELERATION_FEATURES
    + SEGMENT_VELOCITY_FEATURES
)

# Canonical column groupings for quick schema reference
CANONICAL_COLUMN_GROUPS = {
    'metadata': METADATA_COLUMNS,
    'phase': PHASE_COLUMNS,
    'time': TIME_COLUMNS,
    'joint_angles': ANGLE_FEATURES,
    'joint_velocities': VELOCITY_FEATURES,
    'joint_accelerations': ACCELERATION_FEATURES,
    'segment_angles': SEGMENT_ANGLE_FEATURES,
    'segment_velocities': SEGMENT_VELOCITY_FEATURES,
    'moments': MOMENT_FEATURES,
    'moments_normalized': MOMENT_FEATURES_NORMALIZED,
    'grf': GRF_FEATURES,
    'grf_normalized': GRF_FEATURES_NORMALIZED,
    'cop': COP_FEATURES,
}

# Phase- and time-indexed canonical column orders (phase-specific columns are optional)
PHASE_CANONICAL_COLUMNS = (
    METADATA_COLUMNS
    + PHASE_COLUMNS
    + ANGLE_FEATURES
    + SEGMENT_ANGLE_FEATURES
    + VELOCITY_FEATURES
    + ACCELERATION_FEATURES
    + SEGMENT_VELOCITY_FEATURES
    + MOMENT_FEATURES_NORMALIZED
    + GRF_FEATURES_NORMALIZED
    + COP_FEATURES
)

TIME_CANONICAL_COLUMNS = (
    METADATA_COLUMNS
    + TIME_COLUMNS
    + ANGLE_FEATURES
    + SEGMENT_ANGLE_FEATURES
    + VELOCITY_FEATURES
    + ACCELERATION_FEATURES
    + SEGMENT_VELOCITY_FEATURES
    + MOMENT_FEATURES_NORMALIZED
    + GRF_FEATURES_NORMALIZED
    + COP_FEATURES
)


def get_kinematic_feature_map() -> Dict[str, int]:
    """
    Get feature index mapping for kinematic variables.
    
    Returns:
        Dictionary mapping variable names to array indices (0-5)
    """
    feature_map = {}
    
    # Standard naming convention
    for i, feature in enumerate(ANGLE_FEATURES):
        feature_map[feature] = i
    
    # Legacy naming convention (for backward compatibility)
    legacy_features = [
        'hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
        'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
        'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra'
    ]
    for i, feature in enumerate(legacy_features):
        feature_map[feature] = i
    
    return feature_map


def get_kinetic_feature_map() -> Dict[str, int]:
    """
    Get feature index mapping for kinetic variables.
    
    Returns:
        Dictionary mapping variable names to array indices (0-5)
    """
    feature_map = {}
    
    # Standard naming convention (Nm)
    for i, feature in enumerate(MOMENT_FEATURES):
        feature_map[feature] = i
    
    # Normalized naming convention (Nm/kg)
    for i, feature in enumerate(MOMENT_FEATURES_NORMALIZED):
        feature_map[feature] = i
    
    return feature_map


def get_velocity_feature_map() -> Dict[str, int]:
    """
    Get feature index mapping for velocity variables.
    
    Returns:
        Dictionary mapping variable names to array indices (0-5)
    """
    feature_map = {}
    
    # Standard naming convention
    for i, feature in enumerate(VELOCITY_FEATURES):
        feature_map[feature] = i
    
    return feature_map


def get_feature_list(mode: str) -> list:
    """
    Get the ordered feature list for the specified mode.
    
    Args:
        mode: 'kinematic', 'kinetic', or 'velocity'
        
    Returns:
        List of feature names in canonical order
        
    Raises:
        ValueError: If mode is not supported
    """
    if mode == 'kinematic':
        return ANGLE_FEATURES.copy()
    elif mode == 'kinetic':
        return ALL_KINETIC_FEATURES.copy()
    elif mode == 'velocity':
        return VELOCITY_FEATURES.copy()
    else:
        raise ValueError(f"Unsupported mode: {mode}. Use 'kinematic', 'kinetic', or 'velocity'")


# Legacy GRF naming aliases (old -> new) for backward compatibility
LEGACY_GRF_ALIASES: Dict[str, str] = {
    # Raw GRF (N)
    'vertical_grf_ipsi_N': 'grf_vertical_ipsi_N',
    'vertical_grf_contra_N': 'grf_vertical_contra_N',
    'anterior_grf_ipsi_N': 'grf_anterior_ipsi_N',
    'anterior_grf_contra_N': 'grf_anterior_contra_N',
    'lateral_grf_ipsi_N': 'grf_lateral_ipsi_N',
    'lateral_grf_contra_N': 'grf_lateral_contra_N',
    # Normalized GRF (BW)
    'vertical_grf_ipsi_BW': 'grf_vertical_ipsi_BW',
    'vertical_grf_contra_BW': 'grf_vertical_contra_BW',
    'anterior_grf_ipsi_BW': 'grf_anterior_ipsi_BW',
    'anterior_grf_contra_BW': 'grf_anterior_contra_BW',
    'lateral_grf_ipsi_BW': 'grf_lateral_ipsi_BW',
    'lateral_grf_contra_BW': 'grf_lateral_contra_BW',
}


def get_valid_tasks(category: str = None) -> list:
    """Expose canonical task names via the user library API."""

    return _task_registry.get_valid_tasks(category)


def is_valid_task(task_name: str) -> bool:
    """Return True if *task_name* is part of the canonical registry."""

    return _task_registry.is_valid_task(task_name)


def get_feature_map(mode: str) -> Dict[str, int]:
    """
    Get feature index mapping for the specified mode.
    
    Args:
        mode: 'kinematic', 'kinetic', or 'velocity'
        
    Returns:
        Dictionary mapping variable names to array indices
        
    Raises:
        ValueError: If mode is not supported
    """
    if mode == 'kinematic':
        return get_kinematic_feature_map()
    elif mode == 'kinetic':
        return get_kinetic_feature_map()
    elif mode == 'velocity':
        return get_velocity_feature_map()
    else:
        raise ValueError(f"Unsupported mode: {mode}. Use 'kinematic', 'kinetic', or 'velocity'")


def get_sagittal_features() -> list:
    """
    Get list of sagittal plane features for validation and plotting.
    
    Returns list of (variable_name, display_label) tuples for all sagittal plane features
    including kinematic, kinetic, velocity, and segment angle variables.
    
    Returns:
        List of tuples containing (feature_name, display_label)
    """
    return [
        # Joint angles
        ('hip_flexion_angle_ipsi_rad', 'Hip Flexion Angle (Ipsi)'),
        ('hip_flexion_angle_contra_rad', 'Hip Flexion Angle (Contra)'),
        ('knee_flexion_angle_ipsi_rad', 'Knee Flexion Angle (Ipsi)'),
        ('knee_flexion_angle_contra_rad', 'Knee Flexion Angle (Contra)'),
        ('ankle_dorsiflexion_angle_ipsi_rad', 'Ankle Dorsiflexion Angle (Ipsi)'),
        ('ankle_dorsiflexion_angle_contra_rad', 'Ankle Dorsiflexion Angle (Contra)'),
        # Joint moments (weight-normalized)
        ('hip_flexion_moment_ipsi_Nm_kg', 'Hip Flexion Moment (Ipsi)'),
        ('hip_flexion_moment_contra_Nm_kg', 'Hip Flexion Moment (Contra)'),
        ('knee_flexion_moment_ipsi_Nm_kg', 'Knee Flexion Moment (Ipsi)'),
        ('knee_flexion_moment_contra_Nm_kg', 'Knee Flexion Moment (Contra)'),
        ('ankle_dorsiflexion_moment_ipsi_Nm_kg', 'Ankle Dorsiflexion Moment (Ipsi)'),
        ('ankle_dorsiflexion_moment_contra_Nm_kg', 'Ankle Dorsiflexion Moment (Contra)'),
        # Ground reaction forces (weight-normalized)
        ('grf_vertical_ipsi_BW', 'Vertical GRF (Ipsi)'),
        ('grf_vertical_contra_BW', 'Vertical GRF (Contra)'),
        ('grf_anterior_ipsi_BW', 'Anterior GRF (Ipsi)'),
        ('grf_anterior_contra_BW', 'Anterior GRF (Contra)'),
        ('grf_lateral_ipsi_BW', 'Lateral GRF (Ipsi)'),
        ('grf_lateral_contra_BW', 'Lateral GRF (Contra)'),
        # Center of pressure
        ('cop_anterior_ipsi_m', 'COP Anterior (Ipsi)'),
        ('cop_anterior_contra_m', 'COP Anterior (Contra)'),
        ('cop_lateral_ipsi_m', 'COP Lateral (Ipsi)'),
        ('cop_lateral_contra_m', 'COP Lateral (Contra)'),
        ('cop_vertical_ipsi_m', 'COP Vertical (Ipsi)'),
        ('cop_vertical_contra_m', 'COP Vertical (Contra)'),
        # Joint angular velocities
        ('hip_flexion_velocity_ipsi_rad_s', 'Hip Flexion Velocity (Ipsi)'),
        ('hip_flexion_velocity_contra_rad_s', 'Hip Flexion Velocity (Contra)'),
        ('knee_flexion_velocity_ipsi_rad_s', 'Knee Flexion Velocity (Ipsi)'),
        ('knee_flexion_velocity_contra_rad_s', 'Knee Flexion Velocity (Contra)'),
        ('ankle_dorsiflexion_velocity_ipsi_rad_s', 'Ankle Dorsiflexion Velocity (Ipsi)'),
        ('ankle_dorsiflexion_velocity_contra_rad_s', 'Ankle Dorsiflexion Velocity (Contra)'),
        # Segment angles
        ('pelvis_sagittal_angle_rad', 'Pelvis Sagittal Angle'),
        ('trunk_sagittal_angle_rad', 'Trunk Sagittal Angle'),
        ('thigh_sagittal_angle_ipsi_rad', 'Thigh Sagittal Angle (Ipsi)'),
        ('thigh_sagittal_angle_contra_rad', 'Thigh Sagittal Angle (Contra)'),
        ('shank_sagittal_angle_ipsi_rad', 'Shank Sagittal Angle (Ipsi)'),
        ('shank_sagittal_angle_contra_rad', 'Shank Sagittal Angle (Contra)'),
        ('foot_sagittal_angle_ipsi_rad', 'Foot Sagittal Angle (Ipsi)'),
        ('foot_sagittal_angle_contra_rad', 'Foot Sagittal Angle (Contra)'),
        # Segment angular velocities
        ('pelvis_sagittal_velocity_rad_s', 'Pelvis Sagittal Velocity'),
        ('trunk_sagittal_velocity_rad_s', 'Trunk Sagittal Velocity'),
        ('thigh_sagittal_velocity_ipsi_rad_s', 'Thigh Sagittal Velocity (Ipsi)'),
        ('thigh_sagittal_velocity_contra_rad_s', 'Thigh Sagittal Velocity (Contra)'),
        ('shank_sagittal_velocity_ipsi_rad_s', 'Shank Sagittal Velocity (Ipsi)'),
        ('shank_sagittal_velocity_contra_rad_s', 'Shank Sagittal Velocity (Contra)'),
        ('foot_sagittal_velocity_ipsi_rad_s', 'Foot Sagittal Velocity (Ipsi)'),
        ('foot_sagittal_velocity_contra_rad_s', 'Foot Sagittal Velocity (Contra)')
    ]


def get_task_classification(task_name: str) -> str:
    """
    Classify a task as 'gait' or 'bilateral' based on its name.
    
    This classification determines how the task is treated in validation and visualization:
    - 'gait': Walking, running, stairs tasks with alternating leg patterns
    - 'bilateral': Symmetric tasks like squats, jumps, sit-to-stand
    
    Note: This function handles both standard and impaired population task names.
    For example, both 'level_walking' and 'level_walking_stroke' are classified as 'gait'.
    
    Args:
        task_name: Name of the task to classify (e.g., 'level_walking', 'level_walking_stroke')
        
    Returns:
        'gait' for walking/running/stairs tasks, 'bilateral' for others
    """
    # Remove population suffixes before classification
    # Common suffixes: _stroke, _amputee, _tfa, _tta, _pd, _sci, _cp, _ms, _oa, _cva
    population_suffixes = [
        '_stroke', '_amputee', '_tfa', '_tta', '_pd', '_sci', 
        '_cp', '_ms', '_oa', '_cva', '_parkinsons'
    ]
    
    task_lower = task_name.lower()
    
    # Remove population suffix if present
    for suffix in population_suffixes:
        if task_lower.endswith(suffix):
            task_lower = task_lower[:-len(suffix)]
            break
    
    # Check for gait-related keywords
    gait_keywords = ['walk', 'run', 'stairs', 'gait', 'stair']
    
    for keyword in gait_keywords:
        if keyword in task_lower:
            return 'gait'
    
    return 'bilateral'
