"""
Locomotion Analysis Library
===========================

A Python library for efficient analysis of standardized locomotion data.
"""

from .locomotion_analysis import (
    LocomotionData,
    efficient_reshape_3d
)

__version__ = '1.0.0'
__author__ = 'Locomotion Data Standardization Project'

__all__ = [
    'LocomotionData',
    'efficient_reshape_3d'
]