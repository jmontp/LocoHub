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

# Standard feature groups - ordered to match plotting function expectations
# Order: [hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra]

# Kinematic features (joint angles)
ANGLE_FEATURES = [
    'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
    'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', 
    'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
]

# Kinematic velocities (joint angular velocities)
VELOCITY_FEATURES = [
    'hip_flexion_velocity_ipsi_rad_s', 'hip_flexion_velocity_contra_rad_s',
    'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s',
    'ankle_flexion_velocity_ipsi_rad_s', 'ankle_flexion_velocity_contra_rad_s'
]

# Kinetic features (joint moments) - Standard order: [hip, knee, ankle] x [flexion, adduction, rotation] x [ipsi, contra]
MOMENT_FEATURES = [
    'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
    'hip_adduction_moment_ipsi_Nm', 'hip_adduction_moment_contra_Nm',
    'hip_rotation_moment_ipsi_Nm', 'hip_rotation_moment_contra_Nm',
    'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
    'knee_adduction_moment_ipsi_Nm', 'knee_adduction_moment_contra_Nm',
    'knee_rotation_moment_ipsi_Nm', 'knee_rotation_moment_contra_Nm',
    'ankle_flexion_moment_ipsi_Nm', 'ankle_flexion_moment_contra_Nm',
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
    'ankle_flexion_moment_ipsi_Nm_kg', 'ankle_flexion_moment_contra_Nm_kg',
    'ankle_adduction_moment_ipsi_Nm_kg', 'ankle_adduction_moment_contra_Nm_kg',
    'ankle_rotation_moment_ipsi_Nm_kg', 'ankle_rotation_moment_contra_Nm_kg'
]

# Ground reaction force features
GRF_FEATURES = [
    'vertical_grf_N', 'ap_grf_N', 'ml_grf_N'
]

# Center of pressure features  
COP_FEATURES = [
    'cop_x_m', 'cop_y_m', 'cop_z_m'
]

# All kinetic features combined
ALL_KINETIC_FEATURES = MOMENT_FEATURES + GRF_FEATURES + COP_FEATURES


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