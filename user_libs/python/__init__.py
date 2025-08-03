"""
Python user library for locomotion data analysis.

Core classes and functions for biomechanical data processing.
"""

from .locomotion_data import LocomotionData, efficient_reshape_3d
from .feature_constants import (
    ANGLE_FEATURES,
    VELOCITY_FEATURES, 
    MOMENT_FEATURES,
    GRF_FEATURES,
    COP_FEATURES,
    ALL_KINETIC_FEATURES,
    get_feature_list,
    get_kinematic_feature_map,
    get_kinetic_feature_map
)

__all__ = [
    'LocomotionData',
    'efficient_reshape_3d',
    'ANGLE_FEATURES',
    'VELOCITY_FEATURES',
    'MOMENT_FEATURES',
    'GRF_FEATURES',
    'COP_FEATURES',
    'ALL_KINETIC_FEATURES',
    'get_feature_list',
    'get_kinematic_feature_map',
    'get_kinetic_feature_map'
]