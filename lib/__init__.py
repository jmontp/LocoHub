"""
Locomotion Data Standardization Library

Created: 2025-06-16 with user permission
Purpose: Python package initialization for lib module

Intent: Provides access to core locomotion data functionality and validation tools
"""

# Import core functionality
from .core import LocomotionData, efficient_reshape_3d

# Import validation tools
from .validation import DatasetValidator, StepClassifier, create_filters_by_phase_plot

__version__ = '1.0.0'
__author__ = 'Locomotion Data Standardization Project'

__all__ = [
    # Core functionality
    'LocomotionData',
    'efficient_reshape_3d',
    # Validation tools
    'DatasetValidator',
    'StepClassifier',
    'create_filters_by_phase_plot'
]