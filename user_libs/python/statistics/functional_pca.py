#!/usr/bin/env python3
"""
Functional Principal Component Analysis for Locomotion Data

Created: 2025-06-19 with user permission  
Purpose: Phase-based Functional PCA for gait pattern analysis

Intent:
This module provides comprehensive functional PCA capabilities specifically designed for
biomechanical gait analysis. It extracts principal components from gait curves, provides
biomechanical interpretation, and enables pattern analysis across subjects and tasks.

The implementation uses efficient SVD-based methods while providing biomechanical
context and interpretation tools for researchers.

Features:
- Functional PCA with biomechanical interpretation
- Scree plots and explained variance analysis
- Subject loading analysis and pattern visualization
- Cross-task and cross-subject PC comparison
- Publication-ready visualizations
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union, Any
import warnings
from pathlib import Path

# Core scientific computing
from scipy.linalg import svd
from scipy.stats import pearsonr

# Import from existing library
try:
    from .fda_analysis import FunctionalDataObject, FDALocomotionData
    from .feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES
except ImportError:
    from fda_analysis import FunctionalDataObject, FDALocomotionData
    from feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES

# Optional visualization imports
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False


class FunctionalPCAResults:
    """
    Container for functional PCA results with biomechanical interpretation.
    """
    
    def __init__(self, feature_name: str, mean_function: np.ndarray, 
                 pc_functions: np.ndarray, eigenvalues: np.ndarray,
                 pc_scores: np.ndarray, eval_points: np.ndarray,
                 explained_variance_ratio: np.ndarray):
        """
        Initialize functional PCA results.
        
        Parameters
        ----------
        feature_name : str
            Name of the biomechanical feature
        mean_function : ndarray
            Mean function across all curves (n_points,)
        pc_functions : ndarray
            Principal component functions (n_components, n_points)
        eigenvalues : ndarray
            Eigenvalues in decreasing order
        pc_scores : ndarray
            PC scores for each curve (n_curves, n_components)
        eval_points : ndarray
            Evaluation points (phase percentages)
        explained_variance_ratio : ndarray
            Proportion of variance explained by each PC
        """
        self.feature_name = feature_name
        self.mean_function = mean_function
        self.pc_functions = pc_functions
        self.eigenvalues = eigenvalues
        self.pc_scores = pc_scores
        self.eval_points = eval_points
        self.explained_variance_ratio = explained_variance_ratio
        
        self.n_curves, self.n_components = pc_scores.shape
        self.n_points = len(eval_points)
        
        # Add biomechanical interpretation
        self._add_biomechanical_interpretation()
    
    def _add_biomechanical_interpretation(self):
        """Add biomechanical context to PC results."""
        self.interpretations = {}
        
        # Identify key gait phases
        self.heel_strike_phase = 0  # Start of gait cycle
        self.toe_off_phase = int(0.6 * len(self.eval_points))  # ~60% of cycle
        self.mid_stance_phase = int(0.3 * len(self.eval_points))  # ~30% of cycle  
        self.mid_swing_phase = int(0.8 * len(self.eval_points))  # ~80% of cycle
        
        # Analyze each PC
        for i in range(min(5, self.n_components)):  # Focus on first 5 PCs
            interpretation = self._interpret_pc(i)
            self.interpretations[f'PC{i+1}'] = interpretation
    
    def _interpret_pc(self, pc_idx: int) -> Dict[str, Any]:
        """Interpret a specific principal component biomechanically."""
        pc_function = self.pc_functions[pc_idx, :]
        
        interpretation = {
            'explained_variance': self.explained_variance_ratio[pc_idx],
            'biomechanical_meaning': [],
            'key_phases': {},
            'pattern_type': 'unknown'
        }
        
        # Analyze pattern based on feature type
        if 'angle' in self.feature_name.lower():
            interpretation.update(self._interpret_angle_pc(pc_function))
        elif 'moment' in self.feature_name.lower():
            interpretation.update(self._interpret_moment_pc(pc_function))
        elif 'velocity' in self.feature_name.lower():
            interpretation.update(self._interpret_velocity_pc(pc_function))
        
        # Identify key phases where PC has large magnitude
        abs_pc = np.abs(pc_function)
        peak_threshold = np.percentile(abs_pc, 80)
        peak_phases = self.eval_points[abs_pc > peak_threshold]
        
        interpretation['key_phases'] = {
            'peak_phases': peak_phases.tolist(),
            'max_phase': self.eval_points[np.argmax(abs_pc)],
            'max_magnitude': np.max(abs_pc)
        }
        
        return interpretation
    
    def _interpret_angle_pc(self, pc_function: np.ndarray) -> Dict[str, Any]:
        """Interpret angle-based principal component."""
        interpretation = {'biomechanical_meaning': []}
        
        # Check stance vs swing phase patterns
        stance_mean = np.mean(pc_function[:self.toe_off_phase])
        swing_mean = np.mean(pc_function[self.toe_off_phase:])
        
        if abs(stance_mean) > abs(swing_mean):
            interpretation['pattern_type'] = 'stance_dominant'
            interpretation['biomechanical_meaning'].append(
                "Primary variation occurs during stance phase"
            )
        else:
            interpretation['pattern_type'] = 'swing_dominant'
            interpretation['biomechanical_meaning'].append(
                "Primary variation occurs during swing phase"
            )
        
        # Check for loading response pattern (early stance)
        loading_phase = pc_function[:int(0.2 * len(pc_function))]
        if np.std(loading_phase) > 0.5 * np.std(pc_function):
            interpretation['biomechanical_meaning'].append(
                "Significant variation during loading response"
            )
        
        # Check for push-off pattern (late stance)
        pushoff_phase = pc_function[int(0.4 * len(pc_function)):self.toe_off_phase]
        if np.std(pushoff_phase) > 0.5 * np.std(pc_function):
            interpretation['biomechanical_meaning'].append(
                "Significant variation during push-off phase"
            )
        
        return interpretation
    
    def _interpret_moment_pc(self, pc_function: np.ndarray) -> Dict[str, Any]:
        """Interpret moment-based principal component."""
        interpretation = {'biomechanical_meaning': []}
        
        # Check for power generation vs absorption patterns
        early_stance = pc_function[:int(0.2 * len(pc_function))]
        late_stance = pc_function[int(0.4 * len(pc_function)):self.toe_off_phase]
        
        if np.mean(early_stance) * np.mean(late_stance) < 0:
            interpretation['pattern_type'] = 'biphasic_moment'
            interpretation['biomechanical_meaning'].append(
                "Biphasic moment pattern (absorption then generation or vice versa)"
            )
        else:
            interpretation['pattern_type'] = 'monophasic_moment'
            interpretation['biomechanical_meaning'].append(
                "Consistent moment direction throughout stance"
            )
        
        # Check magnitude of moment variation
        max_moment = np.max(np.abs(pc_function))
        if max_moment > 0.5:  # Significant moment variation
            interpretation['biomechanical_meaning'].append(
                "Large variation in moment magnitude"
            )
        
        return interpretation
    
    def _interpret_velocity_pc(self, pc_function: np.ndarray) -> Dict[str, Any]:
        """Interpret velocity-based principal component."""
        interpretation = {'biomechanical_meaning': []}
        
        # Check for acceleration/deceleration patterns
        zero_crossings = np.where(np.diff(np.signbit(pc_function)))[0]
        n_reversals = len(zero_crossings)
        
        if n_reversals == 0:
            interpretation['pattern_type'] = 'monotonic_velocity'
            interpretation['biomechanical_meaning'].append(
                "Consistent velocity direction variation"
            )
        elif n_reversals <= 2:
            interpretation['pattern_type'] = 'simple_velocity'
            interpretation['biomechanical_meaning'].append(
                "Simple velocity reversal pattern"
            )
        else:
            interpretation['pattern_type'] = 'complex_velocity'
            interpretation['biomechanical_meaning'].append(
                "Complex velocity variation with multiple reversals"
            )
        
        return interpretation
    
    def get_reconstruction(self, n_components: Optional[int] = None) -> np.ndarray:
        """
        Reconstruct curves using specified number of components.
        
        Parameters
        ----------
        n_components : int, optional
            Number of components to use. If None, uses all components.
            
        Returns
        -------
        reconstructed : ndarray
            Reconstructed curves (n_curves, n_points)
        """
        if n_components is None:
            n_components = self.n_components
        
        n_components = min(n_components, self.n_components)
        
        # Reconstruct: mean + sum(score_i * pc_i)
        reconstructed = np.zeros((self.n_curves, self.n_points))
        for i in range(self.n_curves):
            reconstructed[i] = self.mean_function.copy()
            for j in range(n_components):
                reconstructed[i] += self.pc_scores[i, j] * self.pc_functions[j, :]
        
        return reconstructed
    
    def get_pc_curves(self, pc_idx: int, n_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get curves representing ±n_std variations along a PC.
        
        Parameters
        ----------
        pc_idx : int
            Principal component index (0-based)
        n_std : float
            Number of standard deviations
            
        Returns
        -------
        plus_curve : ndarray
            Mean + n_std * PC curve
        minus_curve : ndarray  
            Mean - n_std * PC curve
        """
        if pc_idx >= self.n_components:
            raise ValueError(f"PC index {pc_idx} >= n_components {self.n_components}")
        
        pc_std = np.sqrt(self.eigenvalues[pc_idx])
        plus_curve = self.mean_function + n_std * pc_std * self.pc_functions[pc_idx]
        minus_curve = self.mean_function - n_std * pc_std * self.pc_functions[pc_idx]
        
        return plus_curve, minus_curve


class FunctionalPCA:
    """
    Functional Principal Component Analysis for biomechanical curves.
    
    This class performs functional PCA on gait curves with biomechanical
    interpretation and visualization capabilities.
    """
    
    def __init__(self, center: bool = True):
        """
        Initialize Functional PCA analyzer.
        
        Parameters
        ----------
        center : bool
            Whether to center the functions (subtract mean)
        """
        self.center = center
        self.results_cache = {}
    
    def fit(self, fda_obj: FunctionalDataObject, 
            feature_name: str = "unknown",
            n_components: Optional[int] = None,
            eval_points: Optional[np.ndarray] = None) -> FunctionalPCAResults:
        """
        Perform functional PCA on functional data object.
        
        Parameters
        ----------
        fda_obj : FunctionalDataObject
            Functional data to analyze
        feature_name : str
            Name of the biomechanical feature
        n_components : int, optional
            Number of components to extract. If None, extracts all.
        eval_points : ndarray, optional
            Points to evaluate functions at
            
        Returns
        -------
        results : FunctionalPCAResults
            PCA results with biomechanical interpretation
        """
        # Default evaluation points
        if eval_points is None:
            eval_points = np.linspace(fda_obj.domain[0], fda_obj.domain[1], 150)
        
        # Evaluate functional data
        curves = fda_obj.evaluate(eval_points)  # (n_curves, n_points)
        
        # Center the data if requested
        if self.center:
            mean_function = np.mean(curves, axis=0)
            centered_curves = curves - mean_function
        else:
            mean_function = np.zeros(len(eval_points))
            centered_curves = curves
        
        # Perform SVD on centered curves
        # Note: curves are (n_curves, n_points), so we want PCs of the points
        U, s, Vt = svd(centered_curves.T, full_matrices=False)  # Transpose for correct orientation
        
        # Extract components
        n_curves, n_points = curves.shape
        max_components = min(n_curves, n_points)
        
        if n_components is None:
            n_components = max_components
        else:
            n_components = min(n_components, max_components)
        
        # Principal component functions are the columns of U
        pc_functions = U[:, :n_components].T  # (n_components, n_points)
        
        # Eigenvalues
        eigenvalues = (s[:n_components]**2) / (n_curves - 1)
        
        # PC scores are projections of centered curves onto PCs
        pc_scores = centered_curves @ U[:, :n_components]  # (n_curves, n_components)
        
        # Explained variance ratio
        total_variance = np.sum((s**2) / (n_curves - 1))
        explained_variance_ratio = eigenvalues / total_variance
        
        # Create results object
        results = FunctionalPCAResults(
            feature_name=feature_name,
            mean_function=mean_function,
            pc_functions=pc_functions,
            eigenvalues=eigenvalues,
            pc_scores=pc_scores,
            eval_points=eval_points,
            explained_variance_ratio=explained_variance_ratio
        )
        
        return results
    
    def fit_multiple_features(self, fda_dict: Dict[str, FunctionalDataObject],
                            n_components: Optional[int] = None) -> Dict[str, FunctionalPCAResults]:
        """
        Perform functional PCA on multiple features.
        
        Parameters
        ----------
        fda_dict : dict
            Dictionary of FunctionalDataObject instances
        n_components : int, optional
            Number of components per feature
            
        Returns
        -------
        results_dict : dict
            Dictionary mapping feature names to FunctionalPCAResults
        """
        results_dict = {}
        
        for feature_name, fda_obj in fda_dict.items():
            print(f"Performing functional PCA on {feature_name}...")
            results = self.fit(fda_obj, feature_name, n_components)
            results_dict[feature_name] = results
        
        return results_dict
    
    def compare_pc_loadings(self, results_dict: Dict[str, FunctionalPCAResults],
                          pc_idx: int = 0) -> pd.DataFrame:
        """
        Compare PC loadings across features.
        
        Parameters
        ----------
        results_dict : dict
            Dictionary of FunctionalPCAResults
        pc_idx : int
            Principal component index to compare
            
        Returns
        -------
        comparison_df : DataFrame
            Comparison of PC characteristics across features
        """
        comparison_data = []
        
        for feature_name, results in results_dict.items():
            if pc_idx < results.n_components:
                pc_key = f'PC{pc_idx + 1}'
                interpretation = results.interpretations.get(pc_key, {})
                
                comparison_data.append({
                    'feature': feature_name,
                    'pc': pc_key,
                    'explained_variance': results.explained_variance_ratio[pc_idx],
                    'eigenvalue': results.eigenvalues[pc_idx],
                    'pattern_type': interpretation.get('pattern_type', 'unknown'),
                    'max_phase': interpretation.get('key_phases', {}).get('max_phase', np.nan),
                    'max_magnitude': interpretation.get('key_phases', {}).get('max_magnitude', np.nan)
                })
        
        return pd.DataFrame(comparison_data)
    
    def plot_scree(self, results: FunctionalPCAResults, 
                  save_path: Optional[str] = None):
        """
        Plot scree plot showing explained variance.
        
        Parameters
        ----------
        results : FunctionalPCAResults
            PCA results to plot
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        n_components = min(10, len(results.explained_variance_ratio))
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Scree plot
        pc_numbers = np.arange(1, n_components + 1)
        ax1.plot(pc_numbers, results.explained_variance_ratio[:n_components], 'bo-', linewidth=2)
        ax1.set_xlabel('Principal Component')
        ax1.set_ylabel('Explained Variance Ratio')
        ax1.set_title(f'Scree Plot - {results.feature_name}')
        ax1.grid(True, alpha=0.3)
        
        # Add percentage labels
        for i, ratio in enumerate(results.explained_variance_ratio[:n_components]):
            ax1.text(i+1, ratio + 0.01, f'{ratio:.1%}', ha='center', va='bottom')
        
        # Cumulative explained variance
        cumulative = np.cumsum(results.explained_variance_ratio[:n_components])
        ax2.plot(pc_numbers, cumulative, 'ro-', linewidth=2)
        ax2.set_xlabel('Principal Component')
        ax2.set_ylabel('Cumulative Explained Variance')
        ax2.set_title('Cumulative Variance Explained')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0, 1])
        
        # Add 90% line
        ax2.axhline(y=0.9, color='gray', linestyle='--', alpha=0.7)
        ax2.text(n_components/2, 0.92, '90%', ha='center', va='bottom', color='gray')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Scree plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_principal_components(self, results: FunctionalPCAResults,
                                n_components: int = 4,
                                n_std: float = 2.0,
                                save_path: Optional[str] = None):
        """
        Plot principal component functions.
        
        Parameters
        ----------
        results : FunctionalPCAResults
            PCA results to plot
        n_components : int
            Number of components to plot
        n_std : float
            Number of standard deviations for variation curves
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        n_components = min(n_components, results.n_components)
        n_cols = 2
        n_rows = int(np.ceil(n_components / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 3*n_rows))
        if n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for i in range(n_components):
            row = i // n_cols
            col = i % n_cols
            ax = axes[row, col]
            
            # Get PC curves
            plus_curve, minus_curve = results.get_pc_curves(i, n_std)
            
            # Plot mean function
            ax.plot(results.eval_points, results.mean_function, 'k-', 
                   linewidth=2, label='Mean', alpha=0.8)
            
            # Plot PC variation
            ax.plot(results.eval_points, plus_curve, 'r-', 
                   linewidth=2, label=f'+{n_std}σ', alpha=0.8)
            ax.plot(results.eval_points, minus_curve, 'b-', 
                   linewidth=2, label=f'-{n_std}σ', alpha=0.8)
            
            # Fill between for emphasis
            ax.fill_between(results.eval_points, plus_curve, minus_curve, 
                          alpha=0.2, color='gray')
            
            # Formatting
            ax.set_xlabel('Gait Cycle (%)')
            ax.set_ylabel(results.feature_name.replace('_', ' '))
            ax.set_title(f'PC{i+1} ({results.explained_variance_ratio[i]:.1%} variance)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Add biomechanical interpretation if available
            pc_key = f'PC{i+1}'
            if pc_key in results.interpretations:
                interp = results.interpretations[pc_key]
                if interp['biomechanical_meaning']:
                    meaning = interp['biomechanical_meaning'][0]
                    ax.text(0.02, 0.98, meaning, transform=ax.transAxes,
                           fontsize=8, verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Hide empty subplots
        for i in range(n_components, n_rows * n_cols):
            axes.flat[i].set_visible(False)
        
        plt.suptitle(f'Principal Components - {results.feature_name}', fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"PC plot saved to {save_path}")
        else:
            plt.show()
    
    def plot_pc_scores(self, results: FunctionalPCAResults,
                      pc_pairs: List[Tuple[int, int]] = [(0, 1), (0, 2), (1, 2)],
                      subject_info: Optional[pd.DataFrame] = None,
                      color_by: Optional[str] = None,
                      save_path: Optional[str] = None):
        """
        Plot PC score scatter plots.
        
        Parameters
        ----------
        results : FunctionalPCAResults
            PCA results to plot
        pc_pairs : list of tuples
            Pairs of PC indices to plot
        subject_info : DataFrame, optional
            Subject information for coloring points
        color_by : str, optional
            Column name to color points by
        save_path : str, optional
            Path to save plot
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib required for plotting")
        
        n_plots = len(pc_pairs)
        n_cols = min(3, n_plots)
        n_rows = int(np.ceil(n_plots / n_cols))
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        if n_plots == 1:
            axes = [axes]
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for plot_idx, (pc1_idx, pc2_idx) in enumerate(pc_pairs):
            if pc1_idx >= results.n_components or pc2_idx >= results.n_components:
                continue
                
            row = plot_idx // n_cols
            col = plot_idx % n_cols
            ax = axes[row, col] if n_rows > 1 and n_cols > 1 else axes.flat[plot_idx]
            
            # Get scores
            pc1_scores = results.pc_scores[:, pc1_idx]
            pc2_scores = results.pc_scores[:, pc2_idx]
            
            # Plot scatter
            if subject_info is not None and color_by is not None and color_by in subject_info.columns:
                # Color by specified column
                unique_vals = subject_info[color_by].unique()
                colors = plt.cm.tab10(np.linspace(0, 1, len(unique_vals)))
                
                for i, val in enumerate(unique_vals):
                    mask = subject_info[color_by] == val
                    ax.scatter(pc1_scores[mask], pc2_scores[mask], 
                             c=[colors[i]], label=str(val), alpha=0.7, s=50)
                ax.legend()
            else:
                ax.scatter(pc1_scores, pc2_scores, alpha=0.7, s=50)
            
            # Add origin lines
            ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='--', alpha=0.3)
            
            # Formatting
            ax.set_xlabel(f'PC{pc1_idx+1} ({results.explained_variance_ratio[pc1_idx]:.1%})')
            ax.set_ylabel(f'PC{pc2_idx+1} ({results.explained_variance_ratio[pc2_idx]:.1%})')
            ax.set_title(f'PC Scores: PC{pc1_idx+1} vs PC{pc2_idx+1}')
            ax.grid(True, alpha=0.3)
        
        # Hide empty subplots
        for i in range(n_plots, n_rows * n_cols):
            axes.flat[i].set_visible(False)
        
        plt.suptitle(f'PC Score Analysis - {results.feature_name}', fontsize=14)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"PC scores plot saved to {save_path}")
        else:
            plt.show()


if __name__ == '__main__':
    # Example usage and testing
    print("Functional PCA Module - Example Usage")
    print("====================================")
    
    # Create synthetic gait data for demonstration
    np.random.seed(42)
    n_curves = 50
    n_points = 150
    phase_points = np.linspace(0, 100, n_points)
    
    # Simulate knee angle curves with different patterns
    base_curve = 0.6 * np.sin(2 * np.pi * phase_points / 100) + 0.2 * np.sin(4 * np.pi * phase_points / 100)
    
    curves = []
    for i in range(n_curves):
        # Add individual variation
        amplitude_var = 1 + 0.3 * np.random.randn()
        phase_shift = 5 * np.random.randn()
        noise = 0.1 * np.random.randn(n_points)
        
        shifted_phase = phase_points + phase_shift
        curve = amplitude_var * np.interp(shifted_phase, phase_points, base_curve) + noise
        curves.append(curve)
    
    curves = np.array(curves)
    
    print(f"Created synthetic data: {curves.shape[0]} curves, {curves.shape[1]} points")
    
    # Create mock functional data object
    from fda_analysis import BSplineBasis, FunctionalDataObject
    
    basis = BSplineBasis(n_basis=15, domain=(0, 100))
    # Simulate coefficients
    coefficients = np.random.randn(n_curves, 15)
    fda_obj = FunctionalDataObject(coefficients, basis)
    
    # Test functional PCA
    fpca = FunctionalPCA()
    results = fpca.fit(fda_obj, feature_name="knee_flexion_angle_test")
    
    print(f"\nFPCA Results:")
    print(f"- {results.n_components} components extracted")
    print(f"- First 3 PCs explain {results.explained_variance_ratio[:3].sum():.1%} of variance")
    print(f"- PC1: {results.explained_variance_ratio[0]:.1%}")
    print(f"- PC2: {results.explained_variance_ratio[1]:.1%}")
    print(f"- PC3: {results.explained_variance_ratio[2]:.1%}")
    
    # Test interpretation
    if 'PC1' in results.interpretations:
        print(f"\nPC1 Interpretation:")
        interp = results.interpretations['PC1']
        print(f"- Pattern type: {interp['pattern_type']}")
        print(f"- Biomechanical meaning: {interp['biomechanical_meaning']}")
    
    print("\nFunctional PCA module ready for use!")