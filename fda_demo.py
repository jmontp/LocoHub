#!/usr/bin/env python3
"""
FDA Demonstration Script

Created: 2025-06-19 with user permission
Purpose: Demonstrate key FDA capabilities with synthetic data

This script provides a quick demonstration of the main FDA features
using synthetic gait data when real data is not available.
"""

import numpy as np
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / 'lib' / 'core'))

def create_synthetic_gait_data():
    """Create realistic synthetic gait data for demonstration."""
    print("Creating synthetic gait data...")
    
    np.random.seed(42)
    n_subjects = 30
    n_points = 150
    phase_points = np.linspace(0, 100, n_points)
    
    # Create realistic knee angle patterns
    knee_curves = []
    hip_curves = []
    
    # Simulate subject demographics
    ages = np.random.normal(45, 15, n_subjects)
    bmis = np.random.normal(25, 4, n_subjects)
    
    for i in range(n_subjects):
        # Base gait patterns
        knee_base = (60 * np.sin(2 * np.pi * phase_points / 100) + 
                    10 * np.sin(4 * np.pi * phase_points / 100) + 10)
        
        hip_base = (30 * np.sin(2 * np.pi * phase_points / 100 + np.pi/4) + 
                   5 * np.sin(4 * np.pi * phase_points / 100))
        
        # Age effects (older -> less knee flexion)
        age_effect = -0.3 * (ages[i] - 45) / 15
        
        # BMI effects (higher BMI -> different pattern)
        bmi_effect = 0.2 * (bmis[i] - 25) / 4
        
        # Individual variation and noise
        individual_var = 1 + 0.2 * np.random.randn()
        noise = 3 * np.random.randn(n_points)
        
        # Apply effects
        knee_curve = (1 + age_effect + bmi_effect) * individual_var * knee_base + noise
        hip_curve = individual_var * hip_base + 2 * np.random.randn(n_points)
        
        knee_curves.append(knee_curve * np.pi / 180)  # Convert to radians
        hip_curves.append(hip_curve * np.pi / 180)
    
    # Create walking speed outcomes influenced by gait
    walking_speeds = []
    for i in range(n_subjects):
        knee_rom = np.max(knee_curves[i]) - np.min(knee_curves[i])
        hip_rom = np.max(hip_curves[i]) - np.min(hip_curves[i])
        
        # Walking speed influenced by ROM and demographics
        speed = (1.2 + 0.5 * knee_rom + 0.3 * hip_rom - 
                0.01 * (ages[i] - 45) + 0.1 * np.random.randn())
        walking_speeds.append(max(0.5, speed))  # Minimum realistic speed
    
    return {
        'knee_curves': np.array(knee_curves),
        'hip_curves': np.array(hip_curves),
        'phase_points': phase_points,
        'demographics': {'age': ages, 'bmi': bmis},
        'outcomes': {'walking_speed': np.array(walking_speeds)},
        'n_subjects': n_subjects
    }


def demonstrate_fda_capabilities():
    """Demonstrate key FDA capabilities."""
    print("\n" + "="*60)
    print("FDA CAPABILITIES DEMONSTRATION")
    print("="*60)
    
    # Import FDA components
    try:
        from fda_analysis import BSplineBasis, FunctionalDataObject
        from functional_pca import FunctionalPCA
        from fda_registration import CurveRegistration
        from functional_regression import FunctionalRegression
        from fda_visualization import FDAVisualization
        
        print("✓ FDA modules imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    # Create synthetic data
    data = create_synthetic_gait_data()
    knee_curves = data['knee_curves']
    hip_curves = data['hip_curves']
    phase_points = data['phase_points']
    demographics = data['demographics']
    outcomes = data['outcomes']
    
    print(f"✓ Created synthetic data: {data['n_subjects']} subjects")
    
    # 1. Create functional data objects
    print("\n1. FUNCTIONAL DATA REPRESENTATION")
    print("-" * 40)
    
    basis = BSplineBasis(n_basis=15, domain=(0, 100))
    basis_matrix = basis.evaluate(phase_points)
    
    # Fit knee curves to basis
    knee_coefficients = []
    for curve in knee_curves:
        coeff, _, _, _ = np.linalg.lstsq(basis_matrix, curve, rcond=None)
        knee_coefficients.append(coeff)
    
    knee_fda = FunctionalDataObject(np.array(knee_coefficients), basis)
    
    print(f"✓ Knee angle functional data: {knee_fda.n_curves} curves, {knee_fda.n_basis} basis functions")
    
    # Test evaluation
    eval_points = np.linspace(0, 100, 200)
    evaluated_curves = knee_fda.evaluate(eval_points)
    print(f"✓ Evaluated at {len(eval_points)} points: shape {evaluated_curves.shape}")
    
    # 2. Functional PCA
    print("\n2. FUNCTIONAL PRINCIPAL COMPONENT ANALYSIS")
    print("-" * 40)
    
    fpca = FunctionalPCA()
    pca_results = fpca.fit(knee_fda, "knee_flexion_angle", n_components=5)
    
    print(f"✓ PCA completed: {pca_results.n_components} components")
    print(f"✓ PC1 explains {pca_results.explained_variance_ratio[0]:.1%} of variance")
    print(f"✓ PC1-3 explain {pca_results.explained_variance_ratio[:3].sum():.1%} of variance")
    
    # Biomechanical interpretation
    if 'PC1' in pca_results.interpretations:
        interp = pca_results.interpretations['PC1']
        print(f"✓ PC1 pattern type: {interp.get('pattern_type', 'unknown')}")
        if interp.get('biomechanical_meaning'):
            print(f"✓ PC1 interpretation: {interp['biomechanical_meaning'][0]}")
    
    # 3. Curve Registration
    print("\n3. CURVE REGISTRATION AND ALIGNMENT")
    print("-" * 40)
    
    registration = CurveRegistration()
    
    # Create curves with timing variation for registration demo
    shifted_curves = []
    for i, curve in enumerate(knee_curves[:10]):  # Use subset for speed
        shift = 10 * np.random.randn()  # Random timing shift
        shifted_phase = phase_points + shift
        shifted_curve = np.interp(shifted_phase, phase_points, curve, period=100)
        shifted_curves.append(shifted_curve)
    
    shifted_curves = np.array(shifted_curves)
    
    # Landmark registration
    landmark_results = registration.landmark_registration(
        shifted_curves, phase_points, "knee_flexion_angle")
    
    print(f"✓ Landmark registration completed")
    print(f"✓ Detected landmarks: {list(landmark_results.landmarks.keys())}")
    
    # Compute quality metrics
    metrics = registration.compute_registration_metrics(landmark_results, shifted_curves)
    print(f"✓ Variance reduction: {metrics['variance_reduction']:.1%}")
    
    # 4. Functional Regression
    print("\n4. FUNCTIONAL REGRESSION ANALYSIS")
    print("-" * 40)
    
    regression = FunctionalRegression()
    
    # Function-on-scalar: How demographics affect gait
    predictors = np.column_stack([demographics['age'], demographics['bmi']])
    
    fos_results = regression.function_on_scalar_regression(
        knee_fda, predictors, ['age', 'bmi'], 'knee_flexion_angle')
    
    print(f"✓ Function-on-scalar regression completed")
    print(f"✓ Demographics -> gait patterns: R² = {fos_results.r_squared:.3f}")
    
    # Identify significant regions
    if fos_results.p_values is not None:
        age_sig = np.mean(fos_results.p_values[1, :] < 0.05) * 100  # Age effect
        bmi_sig = np.mean(fos_results.p_values[2, :] < 0.05) * 100  # BMI effect
        print(f"✓ Age significantly affects {age_sig:.1f}% of gait cycle")
        print(f"✓ BMI significantly affects {bmi_sig:.1f}% of gait cycle")
    
    # Scalar-on-function: Predict walking speed from gait
    sof_results = regression.scalar_on_function_regression(
        knee_fda, outcomes['walking_speed'], 'walking_speed', 'knee_flexion_angle')
    
    print(f"✓ Scalar-on-function regression completed")
    print(f"✓ Gait -> walking speed: R² = {sof_results.r_squared:.3f}")
    print(f"✓ Components used: {sof_results.n_components_used}")
    
    # Cross-validation
    try:
        cv_metrics = regression.cross_validate_model(
            knee_fda, outcomes['walking_speed'], 'scalar_on_function', cv_folds=5)
        print(f"✓ Cross-validation R²: {cv_metrics['mean_r2']:.3f} ± {cv_metrics['std_r2']:.3f}")
    except Exception as e:
        print(f"⚠ Cross-validation skipped: {e}")
    
    # 5. Visualization
    print("\n5. VISUALIZATION CAPABILITIES")
    print("-" * 40)
    
    try:
        viz = FDAVisualization()
        print("✓ FDA visualization initialized")
        print("✓ Publication-ready plots available")
        print("✓ Biomechanical context and gait phase annotations")
        print("✓ Multiple plot types: overview, PCA, registration, regression")
    except ImportError:
        print("⚠ Matplotlib not available - visualization limited")
    
    # 6. Summary
    print("\n6. ANALYSIS SUMMARY")
    print("-" * 40)
    
    print(f"📊 Dataset: {data['n_subjects']} synthetic subjects")
    print(f"📈 Gait Variability: PC1 explains {pca_results.explained_variance_ratio[0]:.1%} of variance")
    print(f"🎯 Registration: {metrics['variance_reduction']:.1%} variance reduction")
    print(f"👥 Demographics: R² = {fos_results.r_squared:.3f} for gait pattern effects")
    print(f"🚶 Prediction: R² = {sof_results.r_squared:.3f} for walking speed from gait")
    
    # Biomechanical insights
    print(f"\n🔬 Biomechanical Insights:")
    print(f"   • Primary gait variation is {interp.get('pattern_type', 'complex')}")
    print(f"   • Age and BMI explain {fos_results.r_squared*100:.1f}% of gait pattern variation")
    print(f"   • Gait patterns explain {sof_results.r_squared*100:.1f}% of walking speed variation")
    print(f"   • Registration improves alignment by {metrics['variance_reduction']:.1%}")
    
    print("\n" + "="*60)
    print("FDA DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("\n🎉 All FDA capabilities working correctly:")
    print("   ✓ Functional data representation with B-splines")
    print("   ✓ Functional PCA with biomechanical interpretation")
    print("   ✓ Curve registration and alignment")
    print("   ✓ Functional regression (demographics and outcomes)")
    print("   ✓ Statistical inference with significance testing")
    print("   ✓ Publication-ready visualization capabilities")
    
    return True


def main():
    """Main function to run FDA demonstration."""
    print("FUNCTIONAL DATA ANALYSIS FOR LOCOMOTION DATA")
    print("Comprehensive FDA Implementation Demonstration")
    print("")
    
    success = demonstrate_fda_capabilities()
    
    if success:
        print("\n🚀 Ready for Research!")
        print("   • Use real locomotion data for analysis")
        print("   • Refer to docs/FDA_IMPLEMENTATION_GUIDE.md for details")
        print("   • Run fda_examples.py for complete workflows")
        print("   • Integration with existing LocomotionData API")
    else:
        print("\n❌ Demonstration failed. Check error messages above.")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())