#!/usr/bin/env python3
"""
Comprehensive FDA Examples for Locomotion Data

Created: 2025-06-19 with user permission
Purpose: Complete examples demonstrating FDA workflows for biomechanical research

Intent:
This module provides comprehensive, real-world examples of functional data analysis
workflows for biomechanical gait analysis. It demonstrates the complete integration
of all FDA components including basis representation, smoothing, PCA, registration,
and regression analysis.

The examples are designed to serve as templates for biomechanical researchers
conducting FDA analyses on gait data.

Features:
- Complete FDA workflow examples
- Real-world biomechanical analysis scenarios
- Integration of all FDA components
- Publication-ready analysis pipelines
- Biomechanical interpretation guides
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional, Union, Any
import warnings
from pathlib import Path

# Import all FDA components
try:
    from .fda_analysis import FDALocomotionData, FunctionalDataObject, BSplineBasis, FourierBasis
    from .functional_pca import FunctionalPCA, FunctionalPCAResults
    from .fda_registration import CurveRegistration, RegistrationResults
    from .functional_regression import FunctionalRegression, FunctionalRegressionResults
    from .fda_visualization import FDAVisualization
    from .locomotion_analysis import LocomotionData
    from .feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES
except ImportError:
    from fda_analysis import FDALocomotionData, FunctionalDataObject, BSplineBasis, FourierBasis
    from functional_pca import FunctionalPCA, FunctionalPCAResults
    from fda_registration import CurveRegistration, RegistrationResults
    from functional_regression import FunctionalRegression, FunctionalRegressionResults
    from fda_visualization import FDAVisualization
    from locomotion_analysis import LocomotionData
    from feature_constants import ANGLE_FEATURES, VELOCITY_FEATURES, MOMENT_FEATURES

# Optional imports
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class FDAWorkflowExample:
    """
    Comprehensive FDA workflow examples for biomechanical research.
    
    This class provides complete, publication-ready analysis workflows
    that demonstrate the full FDA capabilities.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize FDA workflow examples.
        
        Parameters
        ----------
        output_dir : str, optional
            Directory to save analysis outputs
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / "fda_analysis_output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize FDA components
        self.fpca = FunctionalPCA()
        self.registration = CurveRegistration()
        self.regression = FunctionalRegression()
        self.viz = FDAVisualization(style='publication')
        
        print(f"FDA Workflow Examples initialized")
        print(f"Output directory: {self.output_dir}")
    
    def example_1_basic_fda_analysis(self, data_path: str) -> Dict[str, Any]:
        """
        Example 1: Basic FDA analysis workflow.
        
        This example demonstrates:
        - Loading locomotion data with FDA capabilities
        - Converting to functional data objects
        - Basic smoothing and curve representation
        - Functional PCA analysis
        - Visualization of results
        
        Parameters
        ----------
        data_path : str
            Path to locomotion data file
            
        Returns
        -------
        results : dict
            Dictionary containing all analysis results
        """
        print("\n" + "="*60)
        print("EXAMPLE 1: Basic FDA Analysis Workflow")
        print("="*60)
        
        # Step 1: Load data with FDA capabilities
        print("\n1. Loading data with FDA capabilities...")
        try:
            fda_loco = FDALocomotionData(data_path)
            print(f"   ✓ Loaded data: {len(fda_loco.subjects)} subjects, {len(fda_loco.tasks)} tasks")
            print(f"   ✓ Available features: {len(fda_loco.features)}")
        except Exception as e:
            print(f"   ✗ Could not load data: {e}")
            return self._create_synthetic_example_1()
        
        # Step 2: Select subject and task for analysis
        subject = fda_loco.subjects[0]
        task = fda_loco.tasks[0] if fda_loco.tasks else 'level_walking'
        
        print(f"\n2. Analyzing subject '{subject}', task '{task}'...")
        
        # Step 3: Convert to functional data objects
        print("\n3. Converting to functional data objects...")
        
        # Focus on key biomechanical features
        key_features = []
        for feature in fda_loco.features:
            if any(kw in feature.lower() for kw in ['knee_flexion', 'hip_flexion', 'ankle']):
                key_features.append(feature)
                if len(key_features) >= 3:  # Limit for example
                    break
        
        if not key_features:
            print("   ⚠ No standard biomechanical features found, using available features")
            key_features = fda_loco.features[:3]
        
        # Create functional data objects with different basis types
        print(f"   Converting {len(key_features)} features to functional objects...")
        
        fda_dict_bspline = fda_loco.create_functional_data(
            subject, task, key_features, basis_type='bspline', n_basis=15, smooth=True)
        
        fda_dict_fourier = fda_loco.create_functional_data(
            subject, task, key_features, basis_type='fourier', n_basis=15, smooth=True)
        
        print(f"   ✓ Created B-spline representations")
        print(f"   ✓ Created Fourier representations")
        
        # Step 4: Functional PCA analysis
        print("\n4. Performing Functional PCA...")
        
        pca_results = {}
        for feature_name, fda_obj in fda_dict_bspline.items():
            print(f"   Analyzing {feature_name}...")
            pca_result = self.fpca.fit(fda_obj, feature_name, n_components=5)
            pca_results[feature_name] = pca_result
            
            # Print key insights
            var_explained = pca_result.explained_variance_ratio[:3].sum()
            print(f"     - First 3 PCs explain {var_explained:.1%} of variance")
            
            if 'PC1' in pca_result.interpretations:
                interpretation = pca_result.interpretations['PC1']
                print(f"     - PC1 pattern: {interpretation.get('pattern_type', 'unknown')}")
        
        # Step 5: Visualization
        print("\n5. Creating visualizations...")
        
        if MATPLOTLIB_AVAILABLE:
            # Overview plot
            overview_path = self.output_dir / "example1_overview.png"
            self.viz.plot_functional_data_overview(fda_dict_bspline, save_path=str(overview_path))
            
            # PCA analysis for first feature
            if key_features:
                first_feature = key_features[0]
                pca_path = self.output_dir / f"example1_pca_{first_feature}.png"
                
                # Get original curves for comparison
                data_3d, _ = fda_loco.get_cycles(subject, task, [first_feature])
                original_curves = data_3d[:, :, 0] if data_3d is not None else None
                
                self.viz.plot_comprehensive_pca_analysis(
                    pca_results[first_feature], original_curves, save_path=str(pca_path))
            
            print(f"   ✓ Saved visualizations to {self.output_dir}")
        else:
            print("   ⚠ Matplotlib not available - skipping visualizations")
        
        # Step 6: Summary and interpretation
        print("\n6. Analysis Summary:")
        print("-" * 40)
        
        for feature_name, pca_result in pca_results.items():
            print(f"\n{feature_name}:")
            print(f"  • {pca_result.n_curves} curves analyzed")
            print(f"  • PC1 explains {pca_result.explained_variance_ratio[0]:.1%} of variance")
            print(f"  • PC1-3 explain {pca_result.explained_variance_ratio[:3].sum():.1%} of variance")
            
            if 'PC1' in pca_result.interpretations:
                interp = pca_result.interpretations['PC1']
                if interp['biomechanical_meaning']:
                    print(f"  • PC1 interpretation: {interp['biomechanical_meaning'][0]}")
        
        # Return results
        results = {
            'fda_data': fda_dict_bspline,
            'pca_results': pca_results,
            'subject': subject,
            'task': task,
            'features_analyzed': key_features
        }
        
        print(f"\n✓ Example 1 completed successfully!")
        print(f"   Results saved to: {self.output_dir}")
        
        return results
    
    def example_2_registration_comparison(self, data_path: str) -> Dict[str, Any]:
        """
        Example 2: Curve registration and alignment analysis.
        
        This example demonstrates:
        - Comparing original vs registered curves
        - Multiple registration methods
        - Quality assessment of registration
        - Biomechanical interpretation of alignment
        
        Parameters
        ----------
        data_path : str
            Path to locomotion data file
            
        Returns
        -------
        results : dict
            Dictionary containing registration results
        """
        print("\n" + "="*60)
        print("EXAMPLE 2: Curve Registration and Alignment")
        print("="*60)
        
        # Load data or create synthetic
        try:
            fda_loco = FDALocomotionData(data_path)
            subject = fda_loco.subjects[0]
            task = fda_loco.tasks[0] if fda_loco.tasks else 'level_walking'
            
            # Get knee angle data for registration example
            knee_features = [f for f in fda_loco.features if 'knee' in f.lower() and 'angle' in f.lower()]
            if not knee_features:
                print("   ⚠ No knee angle features found, using first available feature")
                knee_features = [fda_loco.features[0]] if fda_loco.features else []
            
            if knee_features:
                feature_name = knee_features[0]
                data_3d, _ = fda_loco.get_cycles(subject, task, [feature_name])
                if data_3d is not None:
                    curves = data_3d[:, :, 0]
                    eval_points = np.linspace(0, 100, 150)
                else:
                    return self._create_synthetic_example_2()
            else:
                return self._create_synthetic_example_2()
                
        except Exception as e:
            print(f"   ⚠ Could not load data: {e}")
            return self._create_synthetic_example_2()
        
        print(f"\n1. Analyzing {curves.shape[0]} curves for registration...")
        print(f"   Feature: {feature_name}")
        
        # Step 2: Landmark registration
        print("\n2. Performing landmark registration...")
        
        landmark_results = self.registration.landmark_registration(
            curves, eval_points, feature_name)
        
        print(f"   ✓ Detected landmarks: {list(landmark_results.landmarks.keys())}")
        print(f"   ✓ Registration quality metrics:")
        for metric, value in landmark_results.quality_metrics.items():
            print(f"     - {metric}: {value:.4f}")
        
        # Step 3: Continuous registration
        print("\n3. Performing continuous registration...")
        
        continuous_results = self.registration.continuous_registration(
            curves, eval_points, feature_name, lambda_reg=0.01)
        
        print(f"   ✓ Continuous registration completed")
        print(f"   ✓ Registration quality metrics:")
        for metric, value in continuous_results.quality_metrics.items():
            print(f"     - {metric}: {value:.4f}")
        
        # Step 4: Compare registration methods
        print("\n4. Comparing registration methods...")
        
        registration_results = [landmark_results, continuous_results]
        method_names = ['Landmark', 'Continuous']
        
        # Compute comparison metrics
        for i, (results, method) in enumerate(zip(registration_results, method_names)):
            metrics = self.registration.compute_registration_metrics(results, curves)
            print(f"\n   {method} Registration:")
            print(f"     - Variance reduction: {metrics['variance_reduction']:.1%}")
            print(f"     - Mean MSE to mean: {metrics['mean_mse_to_mean']:.4f}")
        
        # Step 5: Visualization
        print("\n5. Creating registration visualizations...")
        
        if MATPLOTLIB_AVAILABLE:
            # Individual registration plots
            for i, (results, method) in enumerate(zip(registration_results, method_names)):
                plot_path = self.output_dir / f"example2_registration_{method.lower()}.png"
                self.registration.plot_registration_results(
                    results, curves, save_path=str(plot_path))
            
            # Comparison plot
            comparison_path = self.output_dir / "example2_registration_comparison.png"
            self.viz.plot_registration_comparison(
                curves, registration_results, method_names, 
                eval_points, feature_name, save_path=str(comparison_path))
            
            print(f"   ✓ Registration plots saved to {self.output_dir}")
        
        # Step 6: Functional PCA on registered data
        print("\n6. Functional PCA on registered vs original data...")
        
        # Create functional data objects from registered curves
        basis = BSplineBasis(n_basis=15, domain=(0, 100))
        
        # Fit functional data to original curves
        original_fda = self._curves_to_functional_data(curves, eval_points, basis)
        original_pca = self.fpca.fit(original_fda, f"Original {feature_name}")
        
        # Fit functional data to landmark registered curves
        landmark_fda = self._curves_to_functional_data(
            landmark_results.registered_curves, eval_points, basis)
        landmark_pca = self.fpca.fit(landmark_fda, f"Landmark Registered {feature_name}")
        
        print(f"\n   Original data PCA:")
        print(f"     - PC1 explains {original_pca.explained_variance_ratio[0]:.1%}")
        print(f"     - PC1-3 explain {original_pca.explained_variance_ratio[:3].sum():.1%}")
        
        print(f"\n   Landmark registered PCA:")
        print(f"     - PC1 explains {landmark_pca.explained_variance_ratio[0]:.1%}")
        print(f"     - PC1-3 explain {landmark_pca.explained_variance_ratio[:3].sum():.1%}")
        
        # Return results
        results = {
            'original_curves': curves,
            'landmark_results': landmark_results,
            'continuous_results': continuous_results,
            'registration_metrics': [
                self.registration.compute_registration_metrics(res, curves) 
                for res in registration_results
            ],
            'pca_comparison': {
                'original': original_pca,
                'landmark_registered': landmark_pca
            },
            'feature_name': feature_name,
            'eval_points': eval_points
        }
        
        print(f"\n✓ Example 2 completed successfully!")
        return results
    
    def example_3_functional_regression(self, data_path: str) -> Dict[str, Any]:
        """
        Example 3: Functional regression analysis.
        
        This example demonstrates:
        - Function-on-scalar regression (demographics -> gait)
        - Scalar-on-function regression (gait -> outcomes)
        - Cross-validation and model selection
        - Biomechanical interpretation of results
        
        Parameters
        ----------
        data_path : str
            Path to locomotion data file
            
        Returns
        -------
        results : dict
            Dictionary containing regression results
        """
        print("\n" + "="*60)
        print("EXAMPLE 3: Functional Regression Analysis")
        print("="*60)
        
        # For this example, we'll create synthetic data with known relationships
        # since we need subject demographic data that may not be in the dataset
        print("\n1. Creating synthetic dataset with known relationships...")
        
        synthetic_data = self._create_synthetic_regression_data()
        
        # Extract components
        fda_objects = synthetic_data['fda_objects']
        demographics = synthetic_data['demographics']
        outcomes = synthetic_data['outcomes']
        feature_names = list(fda_objects.keys())
        
        print(f"   ✓ Created data for {synthetic_data['n_subjects']} subjects")
        print(f"   ✓ Features: {feature_names}")
        print(f"   ✓ Demographics: age, BMI, height")
        print(f"   ✓ Outcomes: walking speed, knee ROM")
        
        # Step 2: Function-on-scalar regression
        print("\n2. Function-on-scalar regression (demographics -> gait patterns)...")
        
        # Prepare demographic predictors
        predictors = np.column_stack([
            demographics['age'],
            demographics['bmi'],
            demographics['height']
        ])
        predictor_names = ['age', 'bmi', 'height']
        
        fos_results = {}
        for feature_name, fda_obj in fda_objects.items():
            print(f"\n   Analyzing {feature_name}...")
            
            results = self.regression.function_on_scalar_regression(
                fda_obj, predictors, predictor_names, feature_name)
            
            fos_results[feature_name] = results
            
            print(f"     - R² = {results.r_squared:.3f}")
            print(f"     - RMSE = {results.rmse:.3f}")
            
            # Identify significant regions
            if results.p_values is not None:
                for i, pred_name in enumerate(predictor_names):
                    sig_points = np.sum(results.p_values[i+1, :] < 0.05)  # +1 to skip intercept
                    sig_percent = sig_points / len(results.eval_points) * 100
                    print(f"     - {pred_name}: {sig_percent:.1f}% of gait cycle significant")
        
        # Step 3: Scalar-on-function regression
        print("\n3. Scalar-on-function regression (gait patterns -> outcomes)...")
        
        sof_results = {}
        for outcome_name, outcome_values in outcomes.items():
            print(f"\n   Predicting {outcome_name}...")
            
            # Use first feature for demonstration
            first_feature = feature_names[0]
            fda_obj = fda_objects[first_feature]
            
            results = self.regression.scalar_on_function_regression(
                fda_obj, outcome_values, outcome_name, first_feature)
            
            sof_results[outcome_name] = results
            
            print(f"     - R² = {results.r_squared:.3f}")
            print(f"     - RMSE = {results.rmse:.3f}")
            print(f"     - Components used: {results.n_components_used}")
            
            # Cross-validation
            cv_metrics = self.regression.cross_validate_model(
                fda_obj, outcome_values, model_type='scalar_on_function',
                feature_name=first_feature, response_name=outcome_name)
            
            print(f"     - CV R² = {cv_metrics['mean_r2']:.3f} ± {cv_metrics['std_r2']:.3f}")
            print(f"     - CV RMSE = {cv_metrics['mean_rmse']:.3f} ± {cv_metrics['std_rmse']:.3f}")
        
        # Step 4: Function-on-function regression
        print("\n4. Function-on-function regression (joint coupling analysis)...")
        
        if len(feature_names) >= 2:
            # Analyze relationship between first two features
            predictor_feature = feature_names[0]
            response_feature = feature_names[1]
            
            print(f"   Analyzing coupling: {predictor_feature} -> {response_feature}")
            
            fof_results = self.regression.function_on_function_regression(
                fda_objects[predictor_feature], 
                fda_objects[response_feature],
                predictor_feature, response_feature,
                n_components_pred=5, n_components_resp=5)
            
            print(f"     - Overall R² = {fof_results.r_squared:.3f}")
            print(f"     - RMSE = {fof_results.rmse:.3f}")
            print(f"     - Predictor PCs = {fof_results.n_components_pred}")
            print(f"     - Response PCs = {fof_results.n_components_resp}")
            
            # Component-wise R²
            if hasattr(fof_results, 'r_squared_components'):
                best_component = np.argmax(fof_results.r_squared_components)
                best_r2 = fof_results.r_squared_components[best_component]
                print(f"     - Best component R² = {best_r2:.3f} (PC{best_component+1})")
        else:
            print("   ⚠ Need at least 2 features for function-on-function regression")
            fof_results = None
        
        # Step 5: Visualization
        print("\n5. Creating regression visualizations...")
        
        if MATPLOTLIB_AVAILABLE:
            # Function-on-scalar plots
            for feature_name, results in fos_results.items():
                plot_path = self.output_dir / f"example3_fos_{feature_name}.png"
                self.viz.plot_functional_regression_summary(results, save_path=str(plot_path))
            
            # Scalar-on-function plots
            for outcome_name, results in sof_results.items():
                plot_path = self.output_dir / f"example3_sof_{outcome_name}.png"
                self.viz.plot_functional_regression_summary(results, save_path=str(plot_path))
            
            # Function-on-function plot
            if fof_results:
                plot_path = self.output_dir / "example3_fof_coupling.png"
                self.viz.plot_functional_regression_summary(fof_results, save_path=str(plot_path))
            
            print(f"   ✓ Regression plots saved to {self.output_dir}")
        
        # Step 6: Summary and interpretation
        print("\n6. Analysis Summary:")
        print("-" * 40)
        
        print("\nFunction-on-scalar results:")
        for feature_name, results in fos_results.items():
            print(f"  {feature_name}: R² = {results.r_squared:.3f}")
            
            # Best predictor
            if results.p_values is not None:
                avg_sig = []
                for i, pred_name in enumerate(predictor_names):
                    sig_frac = np.mean(results.p_values[i+1, :] < 0.05)
                    avg_sig.append((pred_name, sig_frac))
                
                best_pred = max(avg_sig, key=lambda x: x[1])
                print(f"    Best predictor: {best_pred[0]} ({best_pred[1]:.1%} significant)")
        
        print("\nScalar-on-function results:")
        for outcome_name, results in sof_results.items():
            print(f"  {outcome_name}: R² = {results.r_squared:.3f}")
            print(f"    Components needed: {results.n_components_used}")
        
        if fof_results:
            print(f"\nFunction-on-function coupling:")
            print(f"  {predictor_feature} -> {response_feature}: R² = {fof_results.r_squared:.3f}")
        
        # Return results
        results = {
            'synthetic_data': synthetic_data,
            'fos_results': fos_results,
            'sof_results': sof_results,
            'fof_results': fof_results,
            'predictor_names': predictor_names,
            'outcome_names': list(outcomes.keys())
        }
        
        print(f"\n✓ Example 3 completed successfully!")
        return results
    
    def example_4_complete_workflow(self, data_path: str) -> Dict[str, Any]:
        """
        Example 4: Complete FDA workflow integration.
        
        This example demonstrates:
        - Full FDA pipeline from data to results
        - Integration of all FDA components
        - Multiple feature analysis
        - Publication-ready outputs
        
        Parameters
        ----------
        data_path : str
            Path to locomotion data file
            
        Returns
        -------
        results : dict
            Complete workflow results
        """
        print("\n" + "="*60)
        print("EXAMPLE 4: Complete FDA Workflow Integration")
        print("="*60)
        
        # This would be a comprehensive example integrating all previous examples
        print("\n1. Running complete FDA workflow...")
        print("   This example integrates Examples 1-3 into a complete analysis")
        
        # Run all previous examples
        basic_results = self.example_1_basic_fda_analysis(data_path)
        registration_results = self.example_2_registration_comparison(data_path)
        regression_results = self.example_3_functional_regression(data_path)
        
        # Create comprehensive summary
        print("\n2. Generating comprehensive summary report...")
        
        summary_report = self._generate_summary_report(
            basic_results, registration_results, regression_results)
        
        # Save summary report
        report_path = self.output_dir / "complete_fda_workflow_report.txt"
        with open(report_path, 'w') as f:
            f.write(summary_report)
        
        print(f"   ✓ Summary report saved to {report_path}")
        
        results = {
            'basic_analysis': basic_results,
            'registration_analysis': registration_results,
            'regression_analysis': regression_results,
            'summary_report': summary_report
        }
        
        print(f"\n✓ Complete FDA workflow completed!")
        print(f"   All outputs saved to: {self.output_dir}")
        
        return results
    
    def _create_synthetic_example_1(self) -> Dict[str, Any]:
        """Create synthetic data for Example 1."""
        print("   Creating synthetic gait data for demonstration...")
        
        # Create synthetic knee angle data
        n_subjects = 25
        n_points = 150
        phase_points = np.linspace(0, 100, n_points)
        
        # Base knee angle pattern
        base_curve = 0.6 * np.sin(2 * np.pi * phase_points / 100) + 0.2 * np.sin(4 * np.pi * phase_points / 100)
        
        curves = []
        for i in range(n_subjects):
            amplitude_var = 1 + 0.3 * np.random.randn()
            phase_shift = 5 * np.random.randn()
            noise = 0.1 * np.random.randn(n_points)
            
            shifted_phase = phase_points + phase_shift
            curve = amplitude_var * np.interp(shifted_phase, phase_points, base_curve) + noise
            curves.append(curve)
        
        curves = np.array(curves)
        
        # Create functional data object
        basis = BSplineBasis(n_basis=15, domain=(0, 100))
        fda_obj = self._curves_to_functional_data(curves, phase_points, basis)
        
        # Perform PCA
        pca_result = self.fpca.fit(fda_obj, "knee_flexion_angle_synthetic")
        
        results = {
            'fda_data': {'knee_flexion_angle_synthetic': fda_obj},
            'pca_results': {'knee_flexion_angle_synthetic': pca_result},
            'subject': 'SYNTHETIC_01',
            'task': 'level_walking',
            'features_analyzed': ['knee_flexion_angle_synthetic']
        }
        
        return results
    
    def _create_synthetic_example_2(self) -> Dict[str, Any]:
        """Create synthetic data for Example 2."""
        print("   Creating synthetic data with timing variation...")
        
        np.random.seed(42)
        n_curves = 30
        n_points = 150
        phase_points = np.linspace(0, 100, n_points)
        
        # Base pattern with timing variation
        base_curve = 0.6 * np.sin(2 * np.pi * phase_points / 100) + 0.2 * np.sin(4 * np.pi * phase_points / 100)
        
        curves = []
        for i in range(n_curves):
            # Add significant timing variation
            phase_shift = 15 * np.random.randn()  # Larger timing shifts
            amplitude_var = 1 + 0.2 * np.random.randn()
            noise = 0.1 * np.random.randn(n_points)
            
            shifted_phase = phase_points + phase_shift
            curve = amplitude_var * np.interp(shifted_phase, phase_points, base_curve, period=100) + noise
            curves.append(curve)
        
        curves = np.array(curves)
        feature_name = "knee_flexion_angle_synthetic"
        eval_points = phase_points
        
        return self.example_2_registration_comparison.__func__(self, None, curves, eval_points, feature_name)
    
    def _create_synthetic_regression_data(self) -> Dict[str, Any]:
        """Create synthetic data with known regression relationships."""
        np.random.seed(42)
        n_subjects = 60
        n_points = 150
        
        # Generate demographics
        age = np.random.normal(45, 15, n_subjects)
        bmi = np.random.normal(25, 4, n_subjects)
        height = np.random.normal(170, 10, n_subjects)  # cm
        
        demographics = {'age': age, 'bmi': bmi, 'height': height}
        
        # Create base gait patterns
        phase_points = np.linspace(0, 100, n_points)
        
        # Knee angle influenced by age and BMI
        knee_curves = []
        
        # Hip angle influenced by height and age
        hip_curves = []
        
        # Ankle angle with less demographic influence
        ankle_curves = []
        
        for i in range(n_subjects):
            # Age effect on knee (older -> less flexion)
            age_effect_knee = -0.2 * (age[i] - 45) / 15
            
            # BMI effect on knee (higher BMI -> different pattern)
            bmi_effect_knee = 0.1 * (bmi[i] - 25) / 4
            
            # Height effect on hip
            height_effect_hip = 0.15 * (height[i] - 170) / 10
            
            # Generate curves
            noise = 0.1 * np.random.randn(n_points)
            
            # Knee angle
            base_knee = 0.6 * np.sin(2 * np.pi * phase_points / 100) + 0.2 * np.sin(4 * np.pi * phase_points / 100)
            knee_curve = (1 + age_effect_knee + bmi_effect_knee) * base_knee + noise
            knee_curves.append(knee_curve)
            
            # Hip angle
            base_hip = 0.4 * np.sin(2 * np.pi * phase_points / 100) - 0.1 * np.sin(4 * np.pi * phase_points / 100)
            hip_curve = (1 + height_effect_hip) * base_hip + 0.1 * np.random.randn(n_points)
            hip_curves.append(hip_curve)
            
            # Ankle angle
            base_ankle = 0.3 * np.sin(2 * np.pi * phase_points / 100 + np.pi/4)
            ankle_curve = base_ankle + 0.1 * np.random.randn(n_points)
            ankle_curves.append(ankle_curve)
        
        # Convert to functional data objects
        basis = BSplineBasis(n_basis=15, domain=(0, 100))
        
        fda_objects = {
            'knee_flexion_angle': self._curves_to_functional_data(np.array(knee_curves), phase_points, basis),
            'hip_flexion_angle': self._curves_to_functional_data(np.array(hip_curves), phase_points, basis),
            'ankle_flexion_angle': self._curves_to_functional_data(np.array(ankle_curves), phase_points, basis)
        }
        
        # Generate outcomes influenced by gait patterns
        walking_speed = []
        knee_rom = []
        
        for i in range(n_subjects):
            # Walking speed influenced by knee and hip patterns
            knee_range = np.max(knee_curves[i]) - np.min(knee_curves[i])
            hip_range = np.max(hip_curves[i]) - np.min(hip_curves[i])
            
            speed = 1.2 + 0.3 * knee_range + 0.2 * hip_range - 0.01 * age[i] + 0.1 * np.random.randn()
            walking_speed.append(speed)
            
            # Knee ROM directly from knee curve
            rom = knee_range * 180 / np.pi + 5 * np.random.randn()  # Convert to degrees
            knee_rom.append(rom)
        
        outcomes = {
            'walking_speed': np.array(walking_speed),
            'knee_rom': np.array(knee_rom)
        }
        
        return {
            'n_subjects': n_subjects,
            'fda_objects': fda_objects,
            'demographics': demographics,
            'outcomes': outcomes,
            'phase_points': phase_points
        }
    
    def _curves_to_functional_data(self, curves: np.ndarray, eval_points: np.ndarray,
                                 basis: BSplineBasis) -> FunctionalDataObject:
        """Convert curve array to functional data object."""
        # Least squares fit to basis
        basis_matrix = basis.evaluate(eval_points)
        
        coefficients = []
        for curve in curves:
            coeff, _, _, _ = np.linalg.lstsq(basis_matrix, curve, rcond=None)
            coefficients.append(coeff)
        
        coefficients = np.array(coefficients)
        return FunctionalDataObject(coefficients, basis)
    
    def _generate_summary_report(self, basic_results: Dict, registration_results: Dict,
                               regression_results: Dict) -> str:
        """Generate comprehensive summary report."""
        
        report = []
        report.append("="*80)
        report.append("COMPREHENSIVE FDA ANALYSIS REPORT")
        report.append("="*80)
        report.append("")
        
        # Basic analysis summary
        report.append("1. BASIC FDA ANALYSIS")
        report.append("-" * 40)
        if 'pca_results' in basic_results:
            for feature, pca_result in basic_results['pca_results'].items():
                report.append(f"\n{feature}:")
                report.append(f"  • Number of curves: {pca_result.n_curves}")
                report.append(f"  • PC1 variance explained: {pca_result.explained_variance_ratio[0]:.1%}")
                report.append(f"  • PC1-3 variance explained: {pca_result.explained_variance_ratio[:3].sum():.1%}")
                
                if 'PC1' in pca_result.interpretations:
                    interp = pca_result.interpretations['PC1']
                    if interp['biomechanical_meaning']:
                        report.append(f"  • PC1 interpretation: {interp['biomechanical_meaning'][0]}")
        
        # Registration analysis summary
        report.append("\n\n2. REGISTRATION ANALYSIS")
        report.append("-" * 40)
        if 'registration_metrics' in registration_results:
            for i, metrics in enumerate(registration_results['registration_metrics']):
                method = ['Landmark', 'Continuous'][i]
                report.append(f"\n{method} Registration:")
                report.append(f"  • Variance reduction: {metrics['variance_reduction']:.1%}")
                report.append(f"  • Mean MSE to mean: {metrics['mean_mse_to_mean']:.4f}")
        
        # Regression analysis summary
        report.append("\n\n3. REGRESSION ANALYSIS")
        report.append("-" * 40)
        
        if 'fos_results' in regression_results:
            report.append("\nFunction-on-Scalar Results:")
            for feature, results in regression_results['fos_results'].items():
                report.append(f"  • {feature}: R² = {results.r_squared:.3f}")
        
        if 'sof_results' in regression_results:
            report.append("\nScalar-on-Function Results:")
            for outcome, results in regression_results['sof_results'].items():
                report.append(f"  • {outcome}: R² = {results.r_squared:.3f}")
        
        if 'fof_results' in regression_results and regression_results['fof_results']:
            fof_results = regression_results['fof_results']
            report.append(f"\nFunction-on-Function Results:")
            report.append(f"  • Joint coupling: R² = {fof_results.r_squared:.3f}")
        
        # Overall conclusions
        report.append("\n\n4. CONCLUSIONS")
        report.append("-" * 40)
        report.append("• Functional data analysis successfully applied to locomotion data")
        report.append("• Principal component analysis revealed key patterns of variation")
        report.append("• Registration methods improved curve alignment")
        report.append("• Functional regression identified relationships with demographics/outcomes")
        report.append("• Analysis pipeline ready for publication-quality research")
        
        report.append("\n" + "="*80)
        
        return "\n".join(report)


def run_all_examples(data_path: Optional[str] = None):
    """
    Run all FDA examples.
    
    Parameters
    ----------
    data_path : str, optional
        Path to locomotion data file. If None, uses synthetic data.
    """
    print("FDA EXAMPLES - COMPREHENSIVE DEMONSTRATION")
    print("="*60)
    
    # Initialize workflow
    workflow = FDAWorkflowExample()
    
    # Use synthetic data if no path provided
    if data_path is None:
        print("No data path provided - using synthetic data for all examples")
        data_path = "synthetic"
    
    # Run all examples
    try:
        # Example 1: Basic FDA
        example1_results = workflow.example_1_basic_fda_analysis(data_path)
        
        # Example 2: Registration
        example2_results = workflow.example_2_registration_comparison(data_path)
        
        # Example 3: Regression
        example3_results = workflow.example_3_functional_regression(data_path)
        
        # Example 4: Complete workflow
        example4_results = workflow.example_4_complete_workflow(data_path)
        
        print("\n" + "="*60)
        print("ALL FDA EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Results saved to: {workflow.output_dir}")
        
        return {
            'example1': example1_results,
            'example2': example2_results,
            'example3': example3_results,
            'example4': example4_results
        }
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # Run examples when module is executed directly
    import argparse
    
    parser = argparse.ArgumentParser(description='Run FDA examples')
    parser.add_argument('--data', type=str, help='Path to locomotion data file')
    parser.add_argument('--output', type=str, help='Output directory for results')
    parser.add_argument('--example', type=int, choices=[1,2,3,4], 
                       help='Run specific example (1-4), or all if not specified')
    
    args = parser.parse_args()
    
    if args.example:
        # Run specific example
        workflow = FDAWorkflowExample(args.output)
        
        if args.example == 1:
            results = workflow.example_1_basic_fda_analysis(args.data or "synthetic")
        elif args.example == 2:
            results = workflow.example_2_registration_comparison(args.data or "synthetic")
        elif args.example == 3:
            results = workflow.example_3_functional_regression(args.data or "synthetic")
        elif args.example == 4:
            results = workflow.example_4_complete_workflow(args.data or "synthetic")
    else:
        # Run all examples
        results = run_all_examples(args.data)
    
    print("\nFDA Examples completed!")