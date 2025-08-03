"""
Validation Library

Created: 2025-06-16 with user permission
Purpose: Python package initialization for validation module

Intent: Provides access to validation tools, validators, and plotting functions
"""

from .dataset_validator_phase import DatasetValidator
from .step_classifier import StepClassifier
from .filters_by_phase_plots import create_filters_by_phase_plot
from .config_manager import ValidationConfigManager
from .validation_offset_utils import (
    apply_contralateral_offset_kinematic,
    apply_contralateral_offset_kinetic,
    validate_task_completeness
)

__all__ = [
    'DatasetValidator',
    'StepClassifier', 
    'create_filters_by_phase_plot',
    'ValidationConfigManager',
    'apply_contralateral_offset_kinematic',
    'apply_contralateral_offset_kinetic',
    'validate_task_completeness'
]