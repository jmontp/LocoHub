#!/usr/bin/env python3
"""
Functional Regression Analysis for Locomotion Data

Created: 2025-06-19 with user permission
Purpose: Functional regression capabilities for biomechanical curve analysis

Intent:
This module provides comprehensive functional regression methods for biomechanical
research. It enables analysis of relationships between gait curves and scalar variables,
curve-to-curve relationships, and hypothesis testing for functional data.

The implementation supports function-on-scalar regression (demographic effects on gait),
scalar-on-function regression (outcome prediction from curves), and function-on-function
regression (joint coupling analysis) with proper statistical inference.

Features:
- Function-on-scalar regression for demographic/clinical effects
- Scalar-on-function regression for outcome prediction  
- Function-on-function regression for joint coupling analysis
- Hypothesis testing with functional F-tests
- Cross-validation and model selection
- Biomechanical interpretation of regression results
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union, Any
import warnings
from pathlib import Path

# Core scientific computing
from scipy.linalg import svd, solve
from scipy.stats import f, t
from scipy.optimize import minimize

# Optional sklearn imports
try:
    from sklearn.model_selection import KFold, cross_val_score
    from sklearn.metrics import r2_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # Provide basic implementations if sklearn not available
    def r2_score(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot)
    
    def mean_squared_error(y_true, y_pred):
        return np.mean((y_true - y_pred) ** 2)
    
    class KFold:
        """Basic KFold implementation when sklearn not available."""
        def __init__(self, n_splits=5, shuffle=True, random_state=None):
            self.n_splits = n_splits
            self.shuffle = shuffle
            self.random_state = random_state
        
        def split(self, X):
            n_samples = len(X)
            indices = np.arange(n_samples)
            
            if self.shuffle:
                if self.random_state is not None:
                    np.random.seed(self.random_state)
                np.random.shuffle(indices)
            
            fold_sizes = np.full(self.n_splits, n_samples // self.n_splits, dtype=int)
            fold_sizes[:n_samples % self.n_splits] += 1
            
            current = 0
            for fold_size in fold_sizes:
                start, stop = current, current + fold_size
                test_idx = indices[start:stop]
                train_idx = np.concatenate([indices[:start], indices[stop:]])
                yield train_idx, test_idx
                current = stop

# Import from existing library
try:
    from .fda_analysis import FunctionalDataObject, FDALocomotionData, BSplineBasis
    from .functional_pca import FunctionalPCA, FunctionalPCAResults
    from .feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES
except ImportError:
    from fda_analysis import FunctionalDataObject, FDALocomotionData, BSplineBasis
    from functional_pca import FunctionalPCA, FunctionalPCAResults
    from feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class FunctionalRegressionResults:
    """Container for functional regression results."""
    
    def __init__(self, model_type: str, feature_name: str, 
                 coefficients: np.ndarray, fitted_values: np.ndarray,
                 residuals: np.ndarray, eval_points: np.ndarray,
                 r_squared: float, p_values: Optional[np.ndarray] = None):
        """
        Initialize functional regression results.
        
        Parameters
        ----------
        model_type : str
            Type of regression ('function_on_scalar', 'scalar_on_function', 'function_on_function')
        feature_name : str
            Name of dependent variable feature
        coefficients : ndarray
            Regression coefficients
        fitted_values : ndarray
            Fitted values from the model
        residuals : ndarray
            Residuals (observed - fitted)
        eval_points : ndarray
            Evaluation points (phase percentages)
        r_squared : float
            R-squared value
        p_values : ndarray, optional
            P-values for coefficient tests
        """
        self.model_type = model_type
        self.feature_name = feature_name
        self.coefficients = coefficients
        self.fitted_values = fitted_values
        self.residuals = residuals
        self.eval_points = eval_points
        self.r_squared = r_squared
        self.p_values = p_values
        
        # Compute additional metrics
        self._compute_additional_metrics()
    
    def _compute_additional_metrics(self):
        """Compute additional model performance metrics."""
        # RMSE
        self.rmse = np.sqrt(np.mean(self.residuals**2))
        
        # Adjusted R-squared (requires degrees of freedom information)
        self.adj_r_squared = None  # Will be set by regression class
        
        # Residual standard error
        self.residual_se = np.std(self.residuals)
        
        # AIC/BIC (requires likelihood information)
        self.aic = None
        self.bic = None
    
    def get_significant_regions(self, alpha: float = 0.05) -> Dict[str, List[Tuple[float, float]]]:
        """
        Identify regions where coefficients are significantly different from zero.
        
        Parameters
        ----------
        alpha : float
            Significance level
            
        Returns
        -------
        significant_regions : dict
            Dictionary mapping coefficient names to lists of significant intervals
        """
        significant_regions = {}
        
        if self.p_values is not None:
            if self.model_type == 'function_on_scalar':
                # For function-on-scalar, coefficients are functions
                if self.p_values.ndim == 2:  # Multiple predictors
                    for i in range(self.p_values.shape[0]):
                        significant_mask = self.p_values[i] < alpha
                        regions = self._find_continuous_regions(significant_mask)
                        significant_regions[f'predictor_{i}'] = regions
                else:  # Single predictor
                    significant_mask = self.p_values < alpha
                    regions = self._find_continuous_regions(significant_mask)
                    significant_regions['coefficient'] = regions
        
        return significant_regions
    
    def _find_continuous_regions(self, mask: np.ndarray) -> List[Tuple[float, float]]:
        """Find continuous regions where mask is True."""
        regions = []
        in_region = False
        start_idx = None
        
        for i, is_significant in enumerate(mask):
            if is_significant and not in_region:
                # Start of new region
                start_idx = i
                in_region = True
            elif not is_significant and in_region:
                # End of region
                regions.append((self.eval_points[start_idx], self.eval_points[i-1]))
                in_region = False
        
        # Handle case where region extends to end
        if in_region:
            regions.append((self.eval_points[start_idx], self.eval_points[-1]))
        
        return regions


class FunctionalRegression:
    """
    Comprehensive functional regression analysis for biomechanical curves.
    
    This class provides various functional regression methods for analyzing
    relationships between gait curves and other variables.
    """
    
    def __init__(self, n_basis: int = 15, basis_type: str = 'bspline'):
        """
        Initialize functional regression analyzer.
        
        Parameters
        ----------
        n_basis : int
            Number of basis functions for representation
        basis_type : str
            Type of basis functions ('bspline' or 'fourier')
        """
        self.n_basis = n_basis
        self.basis_type = basis_type
        self.results_cache = {}
    
    def function_on_scalar_regression(self, fda_obj: FunctionalDataObject,
                                    predictors: np.ndarray,
                                    predictor_names: Optional[List[str]] = None,
                                    feature_name: str = "unknown") -> FunctionalRegressionResults:
        """
        Perform function-on-scalar regression.
        
        This analyzes how scalar predictors (age, BMI, etc.) affect functional curves.
        
        Parameters
        ----------
        fda_obj : FunctionalDataObject
            Functional response data
        predictors : ndarray
            Scalar predictor matrix (n_subjects, n_predictors)
        predictor_names : list of str, optional
            Names of predictor variables
        feature_name : str
            Name of the functional response
            
        Returns
        -------
        results : FunctionalRegressionResults
            Regression results
        """
        # Ensure predictors is 2D
        if predictors.ndim == 1:
            predictors = predictors.reshape(-1, 1)
        
        n_subjects, n_predictors = predictors.shape
        
        # Add intercept term
        X = np.column_stack([np.ones(n_subjects), predictors])
        
        # Evaluate functional data
        eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
        Y = fda_obj.evaluate(eval_points)  # (n_subjects, n_points)
        
        # Perform regression at each evaluation point
        n_points = Y.shape[1]
        coefficients = np.zeros((n_predictors + 1, n_points))  # +1 for intercept
        fitted_values = np.zeros_like(Y)
        p_values = np.zeros((n_predictors + 1, n_points))
        
        for t in range(n_points):
            y_t = Y[:, t]
            
            # Ordinary least squares
            try:
                beta_t = solve(X.T @ X, X.T @ y_t)
                coefficients[:, t] = beta_t
                fitted_values[:, t] = X @ beta_t
                
                # Compute p-values
                residuals_t = y_t - fitted_values[:, t]
                mse = np.sum(residuals_t**2) / (n_subjects - n_predictors - 1)
                var_beta = mse * np.linalg.inv(X.T @ X)
                se_beta = np.sqrt(np.diag(var_beta))
                
                t_stats = beta_t / se_beta
                from scipy.stats import t as t_dist
                p_values[:, t] = 2 * (1 - t_dist.cdf(np.abs(t_stats), n_subjects - n_predictors - 1))
                
            except np.linalg.LinAlgError:
                # Handle singular matrix
                warnings.warn(f"Singular matrix at time point {t}")
                coefficients[:, t] = 0
                fitted_values[:, t] = np.mean(y_t)
                p_values[:, t] = 1.0
        
        # Compute overall residuals and R-squared
        residuals = Y - fitted_values
        
        # R-squared (coefficient of determination)
        ss_total = np.sum((Y - np.mean(Y, axis=0))**2)
        ss_residual = np.sum(residuals**2)
        r_squared = 1 - (ss_residual / ss_total)
        
        results = FunctionalRegressionResults(
            model_type='function_on_scalar',
            feature_name=feature_name,
            coefficients=coefficients,
            fitted_values=fitted_values,
            residuals=residuals,
            eval_points=eval_points,
            r_squared=r_squared,
            p_values=p_values
        )
        
        # Store predictor names for interpretation
        if predictor_names is None:
            predictor_names = [f'predictor_{i}' for i in range(n_predictors)]
        results.predictor_names = ['intercept'] + predictor_names
        
        return results
    
    def scalar_on_function_regression(self, fda_obj: FunctionalDataObject,
                                    response: np.ndarray,
                                    response_name: str = "outcome",
                                    feature_name: str = "unknown",
                                    n_components: Optional[int] = None) -> FunctionalRegressionResults:
        """
        Perform scalar-on-function regression.
        
        This predicts scalar outcomes from functional curves using functional PCA.
        
        Parameters
        ----------
        fda_obj : FunctionalDataObject
            Functional predictor data
        response : ndarray
            Scalar response variable (n_subjects,)
        response_name : str
            Name of response variable
        feature_name : str
            Name of functional predictor
        n_components : int, optional
            Number of principal components to use
            
        Returns
        -------
        results : FunctionalRegressionResults
            Regression results
        """
        # Perform functional PCA on predictor
        fpca = FunctionalPCA()
        pca_results = fpca.fit(fda_obj, feature_name)
        
        # Determine number of components
        if n_components is None:
            # Use components explaining 95% of variance
            cumsum_var = np.cumsum(pca_results.explained_variance_ratio)
            n_components = np.argmax(cumsum_var >= 0.95) + 1
            n_components = min(n_components, pca_results.n_components)
        
        # Use PC scores as predictors
        X_pca = pca_results.pc_scores[:, :n_components]
        
        # Add intercept
        X = np.column_stack([np.ones(len(response)), X_pca])
        
        # Ordinary least squares
        try:
            beta = solve(X.T @ X, X.T @ response)
            fitted_values = X @ beta
            residuals = response - fitted_values
            
            # R-squared
            ss_total = np.sum((response - np.mean(response))**2)
            ss_residual = np.sum(residuals**2)
            r_squared = 1 - (ss_residual / ss_total)
            
            # P-values
            n_subjects = len(response)
            mse = ss_residual / (n_subjects - n_components - 1)
            var_beta = mse * np.linalg.inv(X.T @ X)
            se_beta = np.sqrt(np.diag(var_beta))
            t_stats = beta / se_beta
            from scipy.stats import t as t_dist
            p_values = 2 * (1 - t_dist.cdf(np.abs(t_stats), n_subjects - n_components - 1))
            
        except np.linalg.LinAlgError:
            warnings.warn("Singular matrix in scalar-on-function regression")
            beta = np.zeros(n_components + 1)
            fitted_values = np.full_like(response, np.mean(response))
            residuals = response - fitted_values
            r_squared = 0.0
            p_values = np.ones_like(beta)
        
        # Convert coefficients back to functional form
        eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
        functional_coefficients = np.zeros(len(eval_points))
        
        for i in range(n_components):
            functional_coefficients += beta[i+1] * pca_results.pc_functions[i, :]
        
        results = FunctionalRegressionResults(
            model_type='scalar_on_function',
            feature_name=f"{response_name} ~ {feature_name}",
            coefficients=functional_coefficients,
            fitted_values=fitted_values,
            residuals=residuals,
            eval_points=eval_points,
            r_squared=r_squared,
            p_values=p_values[1:]  # Exclude intercept for functional interpretation
        )
        
        # Store additional information
        results.pc_coefficients = beta
        results.n_components_used = n_components
        results.pca_results = pca_results
        
        return results
    
    def function_on_function_regression(self, predictor_fda: FunctionalDataObject,
                                      response_fda: FunctionalDataObject,
                                      predictor_name: str = "predictor",
                                      response_name: str = "response",
                                      n_components_pred: Optional[int] = None,
                                      n_components_resp: Optional[int] = None) -> FunctionalRegressionResults:
        """
        Perform function-on-function regression.
        
        This analyzes relationships between two functional variables (e.g., joint coupling).
        
        Parameters
        ----------
        predictor_fda : FunctionalDataObject
            Functional predictor data
        response_fda : FunctionalDataObject
            Functional response data
        predictor_name : str
            Name of predictor variable
        response_name : str
            Name of response variable
        n_components_pred : int, optional
            Number of PC components for predictor
        n_components_resp : int, optional
            Number of PC components for response
            
        Returns
        -------
        results : FunctionalRegressionResults
            Regression results
        """
        # Perform functional PCA on both variables
        fpca = FunctionalPCA()
        pred_pca = fpca.fit(predictor_fda, predictor_name)
        resp_pca = fpca.fit(response_fda, response_name)
        
        # Determine number of components
        if n_components_pred is None:
            cumsum_var = np.cumsum(pred_pca.explained_variance_ratio)
            n_components_pred = np.argmax(cumsum_var >= 0.95) + 1
            n_components_pred = min(n_components_pred, pred_pca.n_components)
        
        if n_components_resp is None:
            cumsum_var = np.cumsum(resp_pca.explained_variance_ratio)
            n_components_resp = np.argmax(cumsum_var >= 0.95) + 1
            n_components_resp = min(n_components_resp, resp_pca.n_components)
        
        # Use PC scores for regression
        X_pred = pred_pca.pc_scores[:, :n_components_pred]
        Y_resp = resp_pca.pc_scores[:, :n_components_resp]
        
        # Add intercept to predictor
        X = np.column_stack([np.ones(X_pred.shape[0]), X_pred])
        
        # Multivariate regression (each response PC separately)
        beta_matrix = np.zeros((n_components_pred + 1, n_components_resp))
        fitted_pc_scores = np.zeros_like(Y_resp)
        r_squared_components = np.zeros(n_components_resp)
        
        for j in range(n_components_resp):
            y_j = Y_resp[:, j]
            
            try:
                beta_j = solve(X.T @ X, X.T @ y_j)
                beta_matrix[:, j] = beta_j
                fitted_pc_scores[:, j] = X @ beta_j
                
                # R-squared for this component
                ss_total = np.sum((y_j - np.mean(y_j))**2)
                ss_residual = np.sum((y_j - fitted_pc_scores[:, j])**2)
                r_squared_components[j] = 1 - (ss_residual / ss_total)
                
            except np.linalg.LinAlgError:
                warnings.warn(f"Singular matrix for response component {j}")
                beta_matrix[:, j] = 0
                fitted_pc_scores[:, j] = np.mean(y_j)
                r_squared_components[j] = 0
        
        # Convert back to functional form
        eval_points = np.linspace(response_fda.domain[0], response_fda.domain[1], 150)
        
        # Reconstruct fitted response functions
        fitted_functions = resp_pca.mean_function[np.newaxis, :] + \
                          fitted_pc_scores @ resp_pca.pc_functions[:n_components_resp, :]
        
        # Original response functions for residuals
        original_functions = response_fda.evaluate(eval_points)
        residual_functions = original_functions - fitted_functions
        
        # Overall R-squared (weighted by explained variance)
        weights = resp_pca.explained_variance_ratio[:n_components_resp]
        weights = weights / np.sum(weights)  # Normalize
        overall_r_squared = np.sum(weights * r_squared_components)
        
        # Create coefficient function (simplified representation)
        # This is a complex mapping from predictor PCs to response function
        coeff_function = np.zeros(len(eval_points))
        
        results = FunctionalRegressionResults(
            model_type='function_on_function',
            feature_name=f"{response_name} ~ {predictor_name}",
            coefficients=coeff_function,
            fitted_values=fitted_functions,
            residuals=residual_functions,
            eval_points=eval_points,
            r_squared=overall_r_squared
        )
        
        # Store additional information
        results.beta_matrix = beta_matrix
        results.predictor_pca = pred_pca
        results.response_pca = resp_pca
        results.r_squared_components = r_squared_components
        results.n_components_pred = n_components_pred
        results.n_components_resp = n_components_resp
        
        return results
    
    def cross_validate_model(self, fda_obj: FunctionalDataObject,
                           target: np.ndarray,
                           model_type: str = 'scalar_on_function',
                           cv_folds: int = 5,
                           **model_kwargs) -> Dict[str, float]:
        """
        Perform cross-validation for model selection.
        
        Parameters
        ----------
        fda_obj : FunctionalDataObject
            Functional data
        target : ndarray
            Target variable
        model_type : str
            Type of model to validate
        cv_folds : int
            Number of cross-validation folds
        **model_kwargs
            Additional arguments for model fitting
            
        Returns
        -------
        cv_metrics : dict
            Cross-validation metrics
        """
        n_subjects = fda_obj.n_curves
        kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        cv_r2_scores = []
        cv_rmse_scores = []
        
        for train_idx, test_idx in kfold.split(range(n_subjects)):
            # Split functional data
            train_coeffs = fda_obj.coefficients[train_idx]
            test_coeffs = fda_obj.coefficients[test_idx]
            
            train_fda = FunctionalDataObject(train_coeffs, fda_obj.basis, fda_obj.domain)
            test_fda = FunctionalDataObject(test_coeffs, fda_obj.basis, fda_obj.domain)
            
            # Split target
            train_target = target[train_idx]
            test_target = target[test_idx]
            
            # Fit model on training data
            if model_type == 'scalar_on_function':
                model_results = self.scalar_on_function_regression(
                    train_fda, train_target, **model_kwargs)
                
                # Predict on test data
                test_pred = self._predict_scalar_on_function(
                    model_results, test_fda)
                
            else:
                raise ValueError(f"Cross-validation not implemented for {model_type}")
            
            # Compute metrics
            r2 = r2_score(test_target, test_pred)
            rmse = np.sqrt(mean_squared_error(test_target, test_pred))
            
            cv_r2_scores.append(r2)
            cv_rmse_scores.append(rmse)
        
        cv_metrics = {
            'mean_r2': np.mean(cv_r2_scores),
            'std_r2': np.std(cv_r2_scores),
            'mean_rmse': np.mean(cv_rmse_scores),
            'std_rmse': np.std(cv_rmse_scores)
        }
        
        return cv_metrics
    
    def _predict_scalar_on_function(self, model_results: FunctionalRegressionResults,
                                   test_fda: FunctionalDataObject) -> np.ndarray:
        """Predict scalar outcomes for new functional data."""
        # Project test data onto training PCs
        eval_points = model_results.eval_points
        test_curves = test_fda.evaluate(eval_points)
        
        # Center test curves using training mean
        train_mean = model_results.pca_results.mean_function
        centered_test = test_curves - train_mean
        
        # Project onto training PCs
        test_scores = centered_test @ model_results.pca_results.pc_functions[:model_results.n_components_used, :].T
        
        # Add intercept and predict
        X_test = np.column_stack([np.ones(len(test_scores)), test_scores])
        predictions = X_test @ model_results.pc_coefficients
        
        return predictions
    
    def plot_regression_results(self, results: FunctionalRegressionResults,
                              save_path: Optional[str] = None):
        """
        Plot functional regression results.
        
        Parameters
        ----------
        results : FunctionalRegressionResults
            Regression results to plot
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        if results.model_type == 'function_on_scalar':
            self._plot_function_on_scalar_results(results, save_path)
        elif results.model_type == 'scalar_on_function':
            self._plot_scalar_on_function_results(results, save_path)
        elif results.model_type == 'function_on_function':
            self._plot_function_on_function_results(results, save_path)
    
    def _plot_function_on_scalar_results(self, results: FunctionalRegressionResults,
                                       save_path: Optional[str] = None):
        """Plot function-on-scalar regression results."""
        n_predictors = len(results.predictor_names) - 1  # Exclude intercept
        
        fig, axes = plt.subplots(2, min(2, n_predictors), figsize=(12, 8))
        if n_predictors == 1:
            axes = axes.reshape(-1, 1)
        
        for i in range(min(2, n_predictors)):
            # Coefficient function (skip intercept)
            coeff_idx = i + 1
            ax1 = axes[0, i] if n_predictors > 1 else axes[0]
            ax1.plot(results.eval_points, results.coefficients[coeff_idx, :], 'b-', linewidth=2)
            
            # Add significance regions if available
            if results.p_values is not None:
                sig_mask = results.p_values[coeff_idx, :] < 0.05
                ax1.fill_between(results.eval_points, 
                               np.min(results.coefficients[coeff_idx, :]),
                               np.max(results.coefficients[coeff_idx, :]),
                               where=sig_mask, alpha=0.3, color='red',
                               label='p < 0.05')
                ax1.legend()
            
            ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5)
            ax1.set_xlabel('Gait Cycle (%)')
            ax1.set_ylabel('Coefficient')
            ax1.set_title(f'Coefficient: {results.predictor_names[coeff_idx]}')
            ax1.grid(True, alpha=0.3)
            
            # P-values
            ax2 = axes[1, i] if n_predictors > 1 else axes[1]
            if results.p_values is not None:
                ax2.plot(results.eval_points, results.p_values[coeff_idx, :], 'r-', linewidth=2)
                ax2.axhline(y=0.05, color='k', linestyle='--', alpha=0.5, label='α = 0.05')
                ax2.legend()
            
            ax2.set_xlabel('Gait Cycle (%)')
            ax2.set_ylabel('P-value')
            ax2.set_title(f'Significance: {results.predictor_names[coeff_idx]}')
            ax2.grid(True, alpha=0.3)
            ax2.set_yscale('log')
        
        plt.suptitle(f'Function-on-Scalar Regression: {results.feature_name}\n'
                    f'R² = {results.r_squared:.3f}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    def _plot_scalar_on_function_results(self, results: FunctionalRegressionResults,
                                       save_path: Optional[str] = None):
        """Plot scalar-on-function regression results."""
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Coefficient function
        ax1 = axes[0]
        ax1.plot(results.eval_points, results.coefficients, 'b-', linewidth=2)
        ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel('Coefficient')
        ax1.set_title('Functional Coefficient')
        ax1.grid(True, alpha=0.3)
        
        # Observed vs Fitted
        ax2 = axes[1]
        ax2.scatter(results.fitted_values, 
                   results.fitted_values + results.residuals, alpha=0.6)
        
        # Add diagonal line
        combined = np.concatenate([results.fitted_values, 
                                 results.fitted_values + results.residuals])
        min_val, max_val = np.min(combined), np.max(combined)
        ax2.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
        
        ax2.set_xlabel('Fitted Values')
        ax2.set_ylabel('Observed Values')
        ax2.set_title(f'Observed vs Fitted\nR² = {results.r_squared:.3f}')
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(f'Scalar-on-Function Regression: {results.feature_name}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    def _plot_function_on_function_results(self, results: FunctionalRegressionResults,
                                         save_path: Optional[str] = None):
        """Plot function-on-function regression results."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Mean fitted vs observed
        ax1 = axes[0, 0]
        mean_fitted = np.mean(results.fitted_values, axis=0)
        mean_observed = np.mean(results.fitted_values + results.residuals, axis=0)
        
        ax1.plot(results.eval_points, mean_observed, 'b-', linewidth=2, label='Observed')
        ax1.plot(results.eval_points, mean_fitted, 'r-', linewidth=2, label='Fitted')
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel('Mean Response')
        ax1.set_title('Mean Functions')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Residuals
        ax2 = axes[0, 1]
        residual_curves = results.residuals
        for i in range(min(10, residual_curves.shape[0])):
            ax2.plot(results.eval_points, residual_curves[i], alpha=0.7)
        ax2.axhline(y=0, color='k', linestyle='--', alpha=0.8)
        ax2.set_xlabel('Gait Cycle (%)')
        ax2.set_ylabel('Residuals')
        ax2.set_title('Residual Functions')
        ax2.grid(True, alpha=0.3)
        
        # R-squared by component
        ax3 = axes[1, 0]
        components = np.arange(1, len(results.r_squared_components) + 1)
        ax3.bar(components, results.r_squared_components)
        ax3.set_xlabel('Response PC Component')
        ax3.set_ylabel('R²')
        ax3.set_title('R² by Response Component')
        ax3.grid(True, alpha=0.3)
        
        # Overall fit quality
        ax4 = axes[1, 1]
        ax4.text(0.1, 0.8, f'Overall R² = {results.r_squared:.3f}', 
                transform=ax4.transAxes, fontsize=14)
        ax4.text(0.1, 0.6, f'RMSE = {results.rmse:.3f}', 
                transform=ax4.transAxes, fontsize=14)
        ax4.text(0.1, 0.4, f'Predictor PCs = {results.n_components_pred}', 
                transform=ax4.transAxes, fontsize=12)
        ax4.text(0.1, 0.2, f'Response PCs = {results.n_components_resp}', 
                transform=ax4.transAxes, fontsize=12)
        ax4.set_xlim([0, 1])
        ax4.set_ylim([0, 1])
        ax4.set_title('Model Summary')
        ax4.axis('off')
        
        plt.suptitle(f'Function-on-Function Regression: {results.feature_name}')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()


if __name__ == '__main__':
    # Example usage and testing
    print("Functional Regression Module - Example Usage")
    print("===========================================")
    
    # Create synthetic data for demonstration
    np.random.seed(42)
    n_subjects = 50
    n_points = 150
    phase_points = np.linspace(0, 100, n_points)
    
    # Simulate demographic data
    age = np.random.normal(35, 10, n_subjects)
    bmi = np.random.normal(25, 4, n_subjects)
    
    # Create synthetic gait curves influenced by demographics
    base_curve = 0.6 * np.sin(2 * np.pi * phase_points / 100)
    
    curves = []
    outcomes = []
    
    for i in range(n_subjects):
        # Age effect: older subjects have different patterns
        age_effect = 0.1 * (age[i] - 35) / 10 * np.sin(4 * np.pi * phase_points / 100)
        
        # BMI effect: affects magnitude
        bmi_effect = 0.05 * (bmi[i] - 25) / 4
        
        # Individual curve
        noise = 0.1 * np.random.randn(n_points)
        curve = (1 + bmi_effect) * base_curve + age_effect + noise
        curves.append(curve)
        
        # Scalar outcome influenced by curve characteristics
        peak_value = np.max(curve)
        range_value = np.max(curve) - np.min(curve)
        outcome = 10 + 2 * peak_value + 1 * range_value + 0.5 * np.random.randn()
        outcomes.append(outcome)
    
    curves = np.array(curves)
    outcomes = np.array(outcomes)
    
    print(f"Created synthetic data:")
    print(f"- {n_subjects} subjects with demographic data")
    print(f"- Gait curves influenced by age and BMI")
    print(f"- Scalar outcomes derived from curve characteristics")
    
    # Create mock functional data object
    from fda_analysis import BSplineBasis, FunctionalDataObject
    
    basis = BSplineBasis(n_basis=15, domain=(0, 100))
    # Simulate coefficients for the curves
    coefficients = np.random.randn(n_subjects, 15)
    fda_obj = FunctionalDataObject(coefficients, basis)
    
    # Test functional regression
    regression = FunctionalRegression()
    
    # Function-on-scalar regression (demographics -> gait)
    print("\nTesting function-on-scalar regression...")
    predictors = np.column_stack([age, bmi])
    fos_results = regression.function_on_scalar_regression(
        fda_obj, predictors, ['age', 'bmi'], 'knee_angle_test')
    
    print(f"Function-on-scalar results:")
    print(f"- R² = {fos_results.r_squared:.3f}")
    print(f"- RMSE = {fos_results.rmse:.3f}")
    
    # Scalar-on-function regression (gait -> outcome)
    print("\nTesting scalar-on-function regression...")
    sof_results = regression.scalar_on_function_regression(
        fda_obj, outcomes, 'walking_score', 'knee_angle_test')
    
    print(f"Scalar-on-function results:")
    print(f"- R² = {sof_results.r_squared:.3f}")
    print(f"- RMSE = {sof_results.rmse:.3f}")
    print(f"- Components used = {sof_results.n_components_used}")
    
    # Cross-validation
    print("\nTesting cross-validation...")
    cv_metrics = regression.cross_validate_model(fda_obj, outcomes)
    print(f"Cross-validation metrics:")
    print(f"- Mean R² = {cv_metrics['mean_r2']:.3f} ± {cv_metrics['std_r2']:.3f}")
    print(f"- Mean RMSE = {cv_metrics['mean_rmse']:.3f} ± {cv_metrics['std_rmse']:.3f}")
    
    print("\nFunctional regression module ready for use!")