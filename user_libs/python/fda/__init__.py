"""
Functional Data Analysis (FDA) for biomechanical curves.

Advanced analysis tools for continuous gait patterns.
"""

from .analysis import (
    FDALocomotionData,
    FunctionalDataObject,
    BSplineBasis,
    FourierBasis
)
from .registration import (
    CurveRegistration,
    RegistrationResults
)
from .visualization import FDAVisualization

__all__ = [
    'FDALocomotionData',
    'FunctionalDataObject',
    'BSplineBasis',
    'FourierBasis',
    'CurveRegistration',
    'RegistrationResults',
    'FDAVisualization'
]