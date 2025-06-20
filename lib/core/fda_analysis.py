#!/usr/bin/env python3
"""
Functional Data Analysis for Locomotion Data

Created: 2025-06-19 with user permission
Purpose: Comprehensive FDA capabilities for biomechanical curve analysis

Intent:
This module provides functional data analysis tools specifically designed for biomechanical
gait analysis. It extends the existing LocomotionData class with FDA capabilities including
basis function representation, curve smoothing, functional PCA, and registration methods.

The implementation uses scipy and numpy for efficient computation while maintaining
compatibility with the existing LocomotionData API and 3D array operations.

Features:
- B-spline and Fourier basis function systems
- Curve smoothing with optimal lambda selection
- Functional data objects for gait curves
- Integration with existing LocomotionData infrastructure
- Efficient handling of irregularly sampled data
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union, Any
import warnings
from pathlib import Path

# Core scientific computing
from scipy.interpolate import BSpline, splrep, splev
from scipy.optimize import minimize_scalar
from scipy.linalg import svd, eigh
from scipy.stats import f

# Import from existing library
try:
    from .locomotion_analysis import LocomotionData
    from .feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES
except ImportError:
    from locomotion_analysis import LocomotionData
    from feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class FunctionalDataObject:
    """
    Represents functional data using basis function expansions.
    
    This class stores curves as coefficients in a basis function system,
    enabling efficient functional data analysis operations.
    """
    
    def __init__(self, coefficients: np.ndarray, basis: 'BasisFunction', 
                 domain: Tuple[float, float] = (0, 100)):
        """
        Initialize functional data object.
        
        Parameters
        ----------
        coefficients : ndarray
            Basis function coefficients of shape (n_curves, n_basis)
        basis : BasisFunction
            Basis function system used for representation
        domain : tuple
            Domain of the functions (start, end)
        """
        self.coefficients = np.asarray(coefficients)
        self.basis = basis
        self.domain = domain
        
        if self.coefficients.ndim == 1:
            self.coefficients = self.coefficients.reshape(1, -1)
        
        self.n_curves, self.n_basis = self.coefficients.shape
    
    def evaluate(self, eval_points: np.ndarray) -> np.ndarray:
        """
        Evaluate functional data at specified points.
        
        Parameters
        ----------
        eval_points : ndarray
            Points at which to evaluate functions
            
        Returns
        -------
        values : ndarray
            Function values of shape (n_curves, len(eval_points))
        """
        basis_matrix = self.basis.evaluate(eval_points)
        return self.coefficients @ basis_matrix.T
    
    def derivative(self, order: int = 1) -> 'FunctionalDataObject':
        """
        Compute derivative of functional data.
        
        Parameters
        ----------
        order : int
            Order of derivative
            
        Returns
        -------
        deriv_fd : FunctionalDataObject
            Derivative functional data object
        """
        deriv_basis = self.basis.derivative(order)
        return FunctionalDataObject(self.coefficients, deriv_basis, self.domain)
    
    def mean(self) -> 'FunctionalDataObject':
        """Compute mean function."""
        mean_coeff = np.mean(self.coefficients, axis=0, keepdims=True)
        return FunctionalDataObject(mean_coeff, self.basis, self.domain)
    
    def std(self) -> 'FunctionalDataObject':  
        """Compute standard deviation function."""
        std_coeff = np.std(self.coefficients, axis=0, keepdims=True)
        return FunctionalDataObject(std_coeff, self.basis, self.domain)


class BasisFunction:
    """Base class for basis function systems."""
    
    def __init__(self, n_basis: int, domain: Tuple[float, float] = (0, 100)):
        self.n_basis = n_basis
        self.domain = domain
    
    def evaluate(self, eval_points: np.ndarray) -> np.ndarray:
        """Evaluate basis functions at given points."""
        raise NotImplementedError
    
    def derivative(self, order: int = 1) -> 'BasisFunction':
        """Return basis for derivatives."""
        raise NotImplementedError


class BSplineBasis(BasisFunction):
    """B-spline basis function system."""
    
    def __init__(self, n_basis: int, domain: Tuple[float, float] = (0, 100),
                 order: int = 4):
        super().__init__(n_basis, domain)
        self.order = order
        
        # Create knot sequence
        n_interior = n_basis - order
        if n_interior < 0:
            raise ValueError(f"Need at least {order} basis functions for order {order}")
        
        interior_knots = np.linspace(domain[0], domain[1], n_interior + 2)[1:-1]
        self.knots = np.concatenate([
            np.repeat(domain[0], order),
            interior_knots,
            np.repeat(domain[1], order)
        ])
    
    def evaluate(self, eval_points: np.ndarray) -> np.ndarray:
        """Evaluate B-spline basis functions."""
        eval_points = np.asarray(eval_points)
        basis_matrix = np.zeros((len(eval_points), self.n_basis))
        
        for i in range(self.n_basis):
            # Create B-spline for this basis function
            coeff = np.zeros(self.n_basis)
            coeff[i] = 1.0
            basis_matrix[:, i] = BSpline(self.knots, coeff, self.order - 1)(eval_points)
        
        return basis_matrix
    
    def derivative(self, order: int = 1) -> 'BSplineBasis':
        """Return B-spline basis for derivatives."""
        if order >= self.order:
            warnings.warn(f"Derivative order {order} >= basis order {self.order}")
        
        # Create new basis with reduced order
        new_order = max(1, self.order - order)
        return BSplineBasis(self.n_basis, self.domain, new_order)


class FourierBasis(BasisFunction):
    """Fourier basis function system."""
    
    def __init__(self, n_basis: int, domain: Tuple[float, float] = (0, 100),
                 period: Optional[float] = None):
        super().__init__(n_basis, domain)
        self.period = period or (domain[1] - domain[0])
        
        # Ensure odd number of basis functions for symmetric representation
        if n_basis % 2 == 0:
            self.n_basis = n_basis + 1
            warnings.warn(f"Adjusted n_basis to {self.n_basis} for symmetric Fourier basis")
    
    def evaluate(self, eval_points: np.ndarray) -> np.ndarray:
        """Evaluate Fourier basis functions."""
        eval_points = np.asarray(eval_points)
        basis_matrix = np.zeros((len(eval_points), self.n_basis))
        
        # Normalize points to [0, 2π]
        normalized_points = 2 * np.pi * (eval_points - self.domain[0]) / self.period
        
        # Constant term
        basis_matrix[:, 0] = 1.0
        
        # Sine and cosine terms
        n_pairs = (self.n_basis - 1) // 2
        for k in range(1, n_pairs + 1):
            basis_matrix[:, 2*k-1] = np.cos(k * normalized_points)
            if 2*k < self.n_basis:
                basis_matrix[:, 2*k] = np.sin(k * normalized_points)
        
        return basis_matrix
    
    def derivative(self, order: int = 1) -> 'FourierBasis':
        """Return Fourier basis for derivatives."""
        # For Fourier basis, derivatives just change the coefficients
        return FourierBasis(self.n_basis, self.domain, self.period)


class FDALocomotionData(LocomotionData):
    """
    Extended LocomotionData class with Functional Data Analysis capabilities.
    
    This class provides FDA methods while maintaining full compatibility
    with the existing LocomotionData API and 3D array operations.
    """
    
    def __init__(self, data_path: Union[str, Path], **kwargs):
        """Initialize FDA-enabled locomotion data."""
        super().__init__(data_path, **kwargs)
        
        # FDA-specific attributes
        self._fda_cache = {}
        self.default_basis_type = 'bspline'
        self.default_n_basis = 15
    
    def create_functional_data(self, subject: str, task: str, 
                             features: Optional[List[str]] = None,
                             basis_type: str = 'bspline',
                             n_basis: int = 15,
                             smooth: bool = True,
                             lambda_val: Optional[float] = None) -> Dict[str, FunctionalDataObject]:
        """
        Convert 3D locomotion data to functional data objects.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str
            Task name
        features : list of str, optional
            Features to convert. If None, uses all available features.
        basis_type : str
            'bspline' or 'fourier'
        n_basis : int
            Number of basis functions
        smooth : bool
            Whether to smooth the data during conversion
        lambda_val : float, optional
            Smoothing parameter. If None, uses GCV.
            
        Returns
        -------
        fda_dict : dict
            Dictionary mapping feature names to FunctionalDataObject instances
        """
        # Check cache
        cache_key = (subject, task, tuple(features) if features else None,
                    basis_type, n_basis, smooth, lambda_val)
        if cache_key in self._fda_cache:
            return self._fda_cache[cache_key]
        
        # Get 3D data
        data_3d, feature_names = self.get_cycles(subject, task, features)
        if data_3d is None:
            return {}
        
        # Create basis function
        domain = (0, 100)  # Phase percentage domain
        if basis_type == 'bspline':
            basis = BSplineBasis(n_basis, domain)
        elif basis_type == 'fourier':
            basis = FourierBasis(n_basis, domain)
        else:
            raise ValueError(f"Unknown basis type: {basis_type}")
        
        # Convert each feature to functional data
        fda_dict = {}
        phase_points = np.linspace(0, 100, self.POINTS_PER_CYCLE)
        
        for i, feature in enumerate(feature_names):
            # Extract curves for this feature
            curves = data_3d[:, :, i]  # (n_cycles, 150)
            
            # Convert to functional data
            if smooth:
                fda_obj = self._fit_smooth_functional_data(
                    curves, phase_points, basis, lambda_val)
            else:
                fda_obj = self._fit_functional_data(curves, phase_points, basis)
            
            fda_dict[feature] = fda_obj
        
        # Cache result
        self._fda_cache[cache_key] = fda_dict
        return fda_dict
    
    def _fit_functional_data(self, curves: np.ndarray, eval_points: np.ndarray,
                           basis: BasisFunction) -> FunctionalDataObject:
        """Fit curves to basis functions using least squares."""
        # Evaluate basis at data points
        basis_matrix = basis.evaluate(eval_points)  # (150, n_basis)
        
        # Solve for coefficients for each curve
        coefficients = []
        for curve in curves:
            # Least squares fit: curve = basis_matrix @ coeff
            coeff, _, _, _ = np.linalg.lstsq(basis_matrix, curve, rcond=None)
            coefficients.append(coeff)
        
        coefficients = np.array(coefficients)  # (n_curves, n_basis)
        return FunctionalDataObject(coefficients, basis, basis.domain)
    
    def _fit_smooth_functional_data(self, curves: np.ndarray, eval_points: np.ndarray,
                                  basis: BasisFunction, lambda_val: Optional[float] = None) -> FunctionalDataObject:
        """Fit curves with smoothing penalty."""
        # For B-splines, use scipy's smoothing spline
        if isinstance(basis, BSplineBasis):
            coefficients = []
            for curve in curves:
                # Remove NaN/inf values
                valid_mask = np.isfinite(curve)
                if np.sum(valid_mask) < 10:  # Need minimum points
                    warnings.warn("Too few valid points for smoothing")
                    coeff = np.zeros(basis.n_basis)
                else:
                    valid_points = eval_points[valid_mask]
                    valid_curve = curve[valid_mask]
                    
                    # Use scipy's smoothing spline
                    if lambda_val is None:
                        # Use default smoothing
                        tck, _ = splrep(valid_points, valid_curve, s=len(valid_points))
                    else:
                        tck, _ = splrep(valid_points, valid_curve, s=lambda_val*len(valid_points))
                    
                    # Convert to our basis representation (approximation)
                    smoothed_curve = splev(eval_points, tck)
                    basis_matrix = basis.evaluate(eval_points)
                    coeff, _, _, _ = np.linalg.lstsq(basis_matrix, smoothed_curve, rcond=None)
                
                coefficients.append(coeff)
            
            coefficients = np.array(coefficients)
            return FunctionalDataObject(coefficients, basis, basis.domain)
        
        else:
            # For other bases, use penalized least squares
            return self._penalized_least_squares(curves, eval_points, basis, lambda_val)
    
    def _penalized_least_squares(self, curves: np.ndarray, eval_points: np.ndarray,
                               basis: BasisFunction, lambda_val: Optional[float] = None) -> FunctionalDataObject:
        """Penalized least squares fitting with roughness penalty."""
        # Evaluate basis and its second derivative
        basis_matrix = basis.evaluate(eval_points)  # (n_points, n_basis)
        
        # Create roughness penalty matrix (second derivative)
        penalty_points = np.linspace(basis.domain[0], basis.domain[1], 101)
        try:
            deriv2_basis = basis.derivative(2)
            deriv2_matrix = deriv2_basis.evaluate(penalty_points)
            penalty_matrix = deriv2_matrix.T @ deriv2_matrix
        except:
            # Fallback: use identity matrix as penalty
            penalty_matrix = np.eye(basis.n_basis)
        
        # Determine lambda if not provided
        if lambda_val is None:
            lambda_val = self._select_smoothing_parameter(
                curves[0], eval_points, basis_matrix, penalty_matrix)
        
        # Solve penalized least squares for each curve
        coefficients = []
        XTX = basis_matrix.T @ basis_matrix
        regularized_matrix = XTX + lambda_val * penalty_matrix
        
        for curve in curves:
            XTy = basis_matrix.T @ curve
            try:
                coeff = np.linalg.solve(regularized_matrix, XTy)
            except np.linalg.LinAlgError:
                # Fallback to pseudo-inverse
                coeff = np.linalg.pinv(regularized_matrix) @ XTy
            coefficients.append(coeff)
        
        coefficients = np.array(coefficients)
        return FunctionalDataObject(coefficients, basis, basis.domain)
    
    def _select_smoothing_parameter(self, curve: np.ndarray, eval_points: np.ndarray,
                                  basis_matrix: np.ndarray, penalty_matrix: np.ndarray) -> float:
        """Select optimal smoothing parameter using GCV."""
        def gcv_score(log_lambda):
            lambda_val = 10**log_lambda
            XTX = basis_matrix.T @ basis_matrix
            regularized_matrix = XTX + lambda_val * penalty_matrix
            
            try:
                # Compute hat matrix
                inv_matrix = np.linalg.inv(regularized_matrix)
                hat_matrix = basis_matrix @ inv_matrix @ basis_matrix.T
                
                # Compute residuals
                fitted = hat_matrix @ curve
                residuals = curve - fitted
                
                # GCV score
                rss = np.sum(residuals**2)
                trace_hat = np.trace(hat_matrix)
                n = len(curve)
                
                if trace_hat >= n:
                    return np.inf
                
                gcv = rss / (n - trace_hat)**2
                return gcv
                
            except np.linalg.LinAlgError:
                return np.inf
        
        # Search for optimal lambda
        result = minimize_scalar(gcv_score, bounds=(-6, 2), method='bounded')
        return 10**result.x
    
    def smooth_curves(self, fda_dict: Dict[str, FunctionalDataObject],
                     lambda_val: Optional[float] = None,
                     method: str = 'gcv') -> Dict[str, FunctionalDataObject]:
        """
        Apply additional smoothing to functional data.
        
        Parameters
        ----------
        fda_dict : dict
            Dictionary of FunctionalDataObject instances
        lambda_val : float, optional
            Smoothing parameter. If None, auto-select based on method.
        method : str
            'gcv' for generalized cross-validation
            
        Returns
        -------
        smoothed_dict : dict
            Dictionary of smoothed FunctionalDataObject instances
        """
        smoothed_dict = {}
        
        for feature, fda_obj in fda_dict.items():
            # Re-evaluate and smooth
            eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
            curves = fda_obj.evaluate(eval_points)
            
            # Apply smoothing
            smoothed_fda = self._fit_smooth_functional_data(
                curves, eval_points, fda_obj.basis, lambda_val)
            smoothed_dict[feature] = smoothed_fda
        
        return smoothed_dict
    
    def evaluate_functional_data(self, fda_dict: Dict[str, FunctionalDataObject],
                               eval_points: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """
        Evaluate functional data at specified points.
        
        Parameters
        ----------
        fda_dict : dict
            Dictionary of FunctionalDataObject instances
        eval_points : ndarray, optional
            Points to evaluate at. If None, uses standard 150 phase points.
            
        Returns
        -------
        evaluated_dict : dict
            Dictionary mapping features to evaluated curves
        """
        if eval_points is None:
            eval_points = np.linspace(0, 100, 150)
        
        evaluated_dict = {}
        for feature, fda_obj in fda_dict.items():
            evaluated_dict[feature] = fda_obj.evaluate(eval_points)
        
        return evaluated_dict
    
    def get_functional_derivatives(self, fda_dict: Dict[str, FunctionalDataObject],
                                 order: int = 1,
                                 eval_points: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """
        Compute derivatives of functional data.
        
        Parameters
        ----------
        fda_dict : dict
            Dictionary of FunctionalDataObject instances
        order : int
            Order of derivative (1 for velocity, 2 for acceleration)
        eval_points : ndarray, optional
            Points to evaluate derivatives at
            
        Returns
        -------
        derivatives_dict : dict
            Dictionary mapping features to derivative curves
        """
        if eval_points is None:
            eval_points = np.linspace(0, 100, 150)
        
        derivatives_dict = {}
        for feature, fda_obj in fda_dict.items():
            try:
                deriv_obj = fda_obj.derivative(order)
                derivatives_dict[feature] = deriv_obj.evaluate(eval_points)
            except Exception as e:
                warnings.warn(f"Could not compute derivative for {feature}: {e}")
                derivatives_dict[feature] = np.zeros((fda_obj.n_curves, len(eval_points)))
        
        return derivatives_dict


# Utility functions for FDA analysis
def create_phase_points(n_points: int = 150, domain: Tuple[float, float] = (0, 100)) -> np.ndarray:
    """Create evenly spaced phase points."""
    return np.linspace(domain[0], domain[1], n_points)


def validate_functional_data(fda_obj: FunctionalDataObject, 
                           feature_name: str = "unknown") -> Dict[str, Any]:
    """
    Validate functional data object for biomechanical reasonableness.
    
    Parameters
    ----------
    fda_obj : FunctionalDataObject
        Functional data to validate
    feature_name : str
        Name of the feature for context
        
    Returns
    -------
    validation_report : dict
        Dictionary with validation results
    """
    report = {
        'feature': feature_name,
        'n_curves': fda_obj.n_curves,
        'n_basis': fda_obj.n_basis,
        'domain': fda_obj.domain,
        'warnings': [],
        'errors': []
    }
    
    # Evaluate at standard points
    eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
    curves = fda_obj.evaluate(eval_points)
    
    # Check for reasonable values
    if 'angle' in feature_name.lower():
        # Angle checks (assuming radians)
        extreme_values = np.any(np.abs(curves) > 2*np.pi)
        if extreme_values:
            report['warnings'].append("Some angle values exceed ±2π radians")
    
    elif 'moment' in feature_name.lower():
        # Moment checks
        extreme_values = np.any(np.abs(curves) > 500)  # Nm
        if extreme_values:
            report['warnings'].append("Some moment values exceed ±500 Nm")
    
    # Check for NaN/inf
    has_invalid = np.any(~np.isfinite(curves))
    if has_invalid:
        report['errors'].append("Contains NaN or infinite values")
    
    # Check curve smoothness (second derivative)
    try:
        deriv2_obj = fda_obj.derivative(2)
        deriv2_curves = deriv2_obj.evaluate(eval_points)
        roughness = np.mean(deriv2_curves**2, axis=1)
        
        # Flag extremely rough curves
        rough_threshold = np.percentile(roughness, 95) * 3
        rough_curves = np.sum(roughness > rough_threshold)
        if rough_curves > 0:
            report['warnings'].append(f"{rough_curves} curves appear very rough")
            
    except Exception:
        report['warnings'].append("Could not assess curve smoothness")
    
    return report


if __name__ == '__main__':
    # Example usage
    print("FDA Analysis Module - Example Usage")
    print("===================================")
    
    # This would typically be used with real data:
    # fda_loco = FDALocomotionData('gait_data.parquet')
    # fda_curves = fda_loco.create_functional_data('SUB01', 'level_walking')
    # smoothed_curves = fda_loco.smooth_curves(fda_curves)
    
    # Demonstrate basis functions
    print("\nDemonstrating basis functions:")
    
    # B-spline basis
    bspline_basis = BSplineBasis(n_basis=10, domain=(0, 100))
    eval_pts = np.linspace(0, 100, 50)
    bspline_matrix = bspline_basis.evaluate(eval_pts)
    print(f"B-spline basis matrix shape: {bspline_matrix.shape}")
    
    # Fourier basis  
    fourier_basis = FourierBasis(n_basis=11, domain=(0, 100))
    fourier_matrix = fourier_basis.evaluate(eval_pts)
    print(f"Fourier basis matrix shape: {fourier_matrix.shape}")
    
    print("\nFDA module ready for use with LocomotionData!")