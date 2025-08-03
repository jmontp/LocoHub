"""
Statistical analysis tools for biomechanical data.

Mixed effects models, functional PCA, and regression methods.
"""

from .functional_pca import (
    FunctionalPCA,
    FunctionalPCAResults
)
from .functional_regression import (
    FunctionalRegression,
    FunctionalRegressionResults
)

try:
    from .mixed_effects import (
        MixedEffectsLocomotion,
        MixedEffectsResults
    )
    MIXED_EFFECTS_AVAILABLE = True
except ImportError:
    MIXED_EFFECTS_AVAILABLE = False

__all__ = [
    'FunctionalPCA',
    'FunctionalPCAResults',
    'FunctionalRegression',
    'FunctionalRegressionResults'
]

if MIXED_EFFECTS_AVAILABLE:
    __all__.extend(['MixedEffectsLocomotion', 'MixedEffectsResults'])