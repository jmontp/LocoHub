"""
Locomotion Analysis Library with Functional Data Analysis
=========================================================

A comprehensive Python library for efficient analysis of standardized locomotion data
with advanced functional data analysis (FDA) capabilities.

Features:
- Standard locomotion data analysis with 3D array operations
- Functional data analysis with basis function representation
- Functional PCA for gait pattern analysis
- Curve registration and alignment methods
- Functional regression for biomechanical modeling
- Publication-ready FDA visualizations
"""

# Core locomotion analysis
from .locomotion_analysis import (
    LocomotionData,
    efficient_reshape_3d
)

# Functional data analysis components
from .fda_analysis import (
    FDALocomotionData,
    FunctionalDataObject,
    BasisFunction,
    BSplineBasis,
    FourierBasis,
    validate_functional_data,
    create_phase_points
)

from .functional_pca import (
    FunctionalPCA,
    FunctionalPCAResults
)

from .fda_registration import (
    CurveRegistration,
    RegistrationResults
)

from .functional_regression import (
    FunctionalRegression,
    FunctionalRegressionResults
)

from .fda_visualization import (
    FDAVisualization
)

from .fda_examples import (
    FDAWorkflowExample,
    run_all_examples
)

# Mixed effects models (if available)
try:
    from .mixed_effects_models import (
        MixedEffectsAnalysis,
        fit_linear_mixed_model,
        plot_mixed_effects_results
    )
    MIXED_EFFECTS_AVAILABLE = True
except ImportError:
    MIXED_EFFECTS_AVAILABLE = False

__version__ = '2.0.0'
__author__ = 'Locomotion Data Standardization Project'

__all__ = [
    # Core locomotion analysis
    'LocomotionData',
    'efficient_reshape_3d',
    
    # FDA core components
    'FDALocomotionData',
    'FunctionalDataObject',
    'BasisFunction',
    'BSplineBasis', 
    'FourierBasis',
    'validate_functional_data',
    'create_phase_points',
    
    # FDA analysis methods
    'FunctionalPCA',
    'FunctionalPCAResults',
    'CurveRegistration',
    'RegistrationResults',
    'FunctionalRegression',
    'FunctionalRegressionResults',
    
    # FDA visualization
    'FDAVisualization',
    
    # FDA examples and workflows
    'FDAWorkflowExample',
    'run_all_examples',
    
    # Mixed effects (if available)
    'MIXED_EFFECTS_AVAILABLE'
]

# Add mixed effects to __all__ if available
if MIXED_EFFECTS_AVAILABLE:
    __all__.extend([
        'MixedEffectsAnalysis',
        'fit_linear_mixed_model', 
        'plot_mixed_effects_results'
    ])