# Functional Data Analysis (FDA) Implementation Guide

**Status**: ✅ **COMPLETE** - Full FDA capabilities implemented and tested  
**Version**: 2.0.0  
**Created**: 2025-06-19  

## Overview

This guide describes the comprehensive Functional Data Analysis (FDA) capabilities now available in the locomotion data standardization framework. The implementation provides complete FDA workflows for biomechanical gait analysis using basis function representation, functional PCA, curve registration, and functional regression.

## 🎯 Key Features

### ✅ **Complete FDA System**
- **Basis Function Representation**: B-splines and Fourier basis systems
- **Curve Smoothing**: Automated smoothing parameter selection via GCV
- **Functional Data Objects**: Efficient representation and manipulation
- **Integration**: Seamless integration with existing LocomotionData API

### ✅ **Functional PCA**
- **Pattern Analysis**: Extract principal components from gait curves
- **Biomechanical Interpretation**: Automatic interpretation of PC patterns
- **Variance Analysis**: Scree plots and explained variance
- **Subject Loading**: Individual subject pattern analysis

### ✅ **Curve Registration and Alignment**
- **Landmark Registration**: Align curves based on gait events
- **Continuous Registration**: Dynamic time warping alignment
- **Quality Assessment**: Registration quality metrics
- **Multi-method Comparison**: Compare different registration approaches

### ✅ **Functional Regression**
- **Function-on-Scalar**: Analyze demographic effects on gait patterns
- **Scalar-on-Function**: Predict outcomes from gait curves
- **Function-on-Function**: Joint coupling and curve relationships
- **Statistical Inference**: Hypothesis testing with functional F-tests

### ✅ **Publication-Ready Visualizations**
- **FDA-Specific Plots**: Specialized plots for functional data
- **Biomechanical Context**: Gait phase annotations and interpretations
- **Comprehensive Analysis**: Multi-panel analysis visualizations
- **Publication Quality**: High-resolution, professionally styled plots

## 🚀 Quick Start

### Basic Usage

```python
from lib.core import FDALocomotionData, FunctionalPCA, CurveRegistration, FunctionalRegression

# Load data with FDA capabilities
fda_loco = FDALocomotionData('gait_data.parquet')

# Create functional data objects
fda_curves = fda_loco.create_functional_data(
    subject='SUB01', 
    task='level_walking',
    features=['knee_flexion_angle_contra_rad'],
    basis_type='bspline',
    n_basis=15,
    smooth=True
)

# Functional PCA
fpca = FunctionalPCA()
pca_results = fpca.fit(fda_curves['knee_flexion_angle_contra_rad'], 'knee_angle')

# Print results
print(f"PC1 explains {pca_results.explained_variance_ratio[0]:.1%} of variance")
print(f"Biomechanical interpretation: {pca_results.interpretations['PC1']}")
```

### Complete Workflow Example

```python
from lib.core import FDAWorkflowExample

# Run complete FDA analysis
workflow = FDAWorkflowExample(output_dir='my_fda_analysis')

# Example 1: Basic FDA analysis
results1 = workflow.example_1_basic_fda_analysis('gait_data.parquet')

# Example 2: Registration comparison
results2 = workflow.example_2_registration_comparison('gait_data.parquet')

# Example 3: Functional regression
results3 = workflow.example_3_functional_regression('gait_data.parquet')

# Example 4: Complete integrated workflow
results4 = workflow.example_4_complete_workflow('gait_data.parquet')
```

## 📚 Detailed API Reference

### FDALocomotionData Class

Extends the standard `LocomotionData` class with FDA capabilities:

```python
# Initialize with FDA capabilities
fda_loco = FDALocomotionData(data_path, subject_col='subject', task_col='task')

# Create functional data objects
fda_dict = fda_loco.create_functional_data(
    subject='SUB01',
    task='level_walking', 
    features=['knee_flexion_angle_contra_rad', 'hip_flexion_angle_contra_rad'],
    basis_type='bspline',  # or 'fourier'
    n_basis=15,
    smooth=True,
    lambda_val=None  # Auto-select via GCV
)

# Smooth existing functional data
smoothed_dict = fda_loco.smooth_curves(fda_dict, method='gcv')

# Evaluate at specific points
eval_points = np.linspace(0, 100, 200)
evaluated_dict = fda_loco.evaluate_functional_data(fda_dict, eval_points)

# Get derivatives (velocity, acceleration)
velocity_dict = fda_loco.get_functional_derivatives(fda_dict, order=1)
accel_dict = fda_loco.get_functional_derivatives(fda_dict, order=2)
```

### Functional PCA

```python
from lib.core import FunctionalPCA

fpca = FunctionalPCA(center=True)

# Fit PCA to functional data
pca_results = fpca.fit(
    fda_obj=fda_dict['knee_flexion_angle_contra_rad'],
    feature_name='knee_angle',
    n_components=5
)

# Access results
print(f"Explained variance: {pca_results.explained_variance_ratio}")
print(f"PC functions shape: {pca_results.pc_functions.shape}")
print(f"PC scores shape: {pca_results.pc_scores.shape}")

# Get biomechanical interpretation
for pc_name, interpretation in pca_results.interpretations.items():
    print(f"{pc_name}: {interpretation['biomechanical_meaning']}")

# Reconstruct curves using subset of PCs
reconstructed = pca_results.get_reconstruction(n_components=3)

# Get ±2σ curves for visualization
plus_curve, minus_curve = pca_results.get_pc_curves(pc_idx=0, n_std=2.0)
```

### Curve Registration

```python
from lib.core import CurveRegistration

registration = CurveRegistration()

# Get original curves
data_3d, features = fda_loco.get_cycles('SUB01', 'level_walking')
curves = data_3d[:, :, 0]  # First feature
eval_points = np.linspace(0, 100, 150)

# Landmark registration
landmark_results = registration.landmark_registration(
    curves=curves,
    eval_points=eval_points,
    feature_name='knee_flexion_angle'
)

# Continuous registration
continuous_results = registration.continuous_registration(
    curves=curves,
    eval_points=eval_points,
    feature_name='knee_flexion_angle',
    lambda_reg=0.01
)

# Compare methods
metrics1 = registration.compute_registration_metrics(landmark_results, curves)
metrics2 = registration.compute_registration_metrics(continuous_results, curves)

print(f"Landmark variance reduction: {metrics1['variance_reduction']:.1%}")
print(f"Continuous variance reduction: {metrics2['variance_reduction']:.1%}")
```

### Functional Regression

```python
from lib.core import FunctionalRegression

regression = FunctionalRegression(n_basis=15, basis_type='bspline')

# Function-on-scalar regression (demographics -> gait)
predictors = np.column_stack([age, bmi, height])  # Subject demographics
fos_results = regression.function_on_scalar_regression(
    fda_obj=fda_dict['knee_flexion_angle_contra_rad'],
    predictors=predictors,
    predictor_names=['age', 'bmi', 'height'],
    feature_name='knee_angle'
)

print(f"Function-on-scalar R²: {fos_results.r_squared:.3f}")

# Scalar-on-function regression (gait -> outcomes)
outcomes = walking_speed  # Scalar outcome variable
sof_results = regression.scalar_on_function_regression(
    fda_obj=fda_dict['knee_flexion_angle_contra_rad'],
    response=outcomes,
    response_name='walking_speed',
    feature_name='knee_angle'
)

print(f"Scalar-on-function R²: {sof_results.r_squared:.3f}")

# Function-on-function regression (joint coupling)
fof_results = regression.function_on_function_regression(
    predictor_fda=fda_dict['hip_flexion_angle_contra_rad'],
    response_fda=fda_dict['knee_flexion_angle_contra_rad'],
    predictor_name='hip_angle',
    response_name='knee_angle'
)

print(f"Function-on-function R²: {fof_results.r_squared:.3f}")

# Cross-validation
cv_metrics = regression.cross_validate_model(
    fda_obj=fda_dict['knee_flexion_angle_contra_rad'],
    target=outcomes,
    model_type='scalar_on_function',
    cv_folds=5
)

print(f"CV R²: {cv_metrics['mean_r2']:.3f} ± {cv_metrics['std_r2']:.3f}")
```

### Visualization

```python
from lib.core import FDAVisualization

viz = FDAVisualization(style='publication')

# Overview of functional data
viz.plot_functional_data_overview(
    fda_dict=fda_dict,
    save_path='fda_overview.png'
)

# Comprehensive PCA analysis
viz.plot_comprehensive_pca_analysis(
    pca_results=pca_results,
    original_curves=curves,
    save_path='pca_analysis.png'
)

# Registration comparison
viz.plot_registration_comparison(
    original_curves=curves,
    registration_results=[landmark_results, continuous_results],
    method_names=['Landmark', 'Continuous'],
    eval_points=eval_points,
    feature_name='knee_flexion_angle',
    save_path='registration_comparison.png'
)

# Functional regression summary
viz.plot_functional_regression_summary(
    regression_results=fos_results,
    save_path='regression_analysis.png'
)
```

## 🔬 Research Applications

### 1. Gait Pattern Analysis
```python
# Analyze gait patterns across different tasks
tasks = ['level_walking', 'incline_walking', 'decline_walking']
pca_results_by_task = {}

for task in tasks:
    fda_curves = fda_loco.create_functional_data('SUB01', task)
    pca_results = fpca.fit(fda_curves['knee_flexion_angle_contra_rad'], f'knee_{task}')
    pca_results_by_task[task] = pca_results

# Compare principal patterns across tasks
comparison = fpca.compare_pc_loadings(pca_results_by_task, pc_idx=0)
print(comparison)
```

### 2. Demographic Effects on Gait
```python
# Analyze how age affects gait patterns
subjects_data = []
age_data = []

for subject in fda_loco.subjects:
    fda_curves = fda_loco.create_functional_data(subject, 'level_walking')
    subjects_data.append(fda_curves['knee_flexion_angle_contra_rad'])
    age_data.append(subject_demographics[subject]['age'])

# Combine functional data objects
combined_fda = combine_functional_data_objects(subjects_data)

# Function-on-scalar regression
age_effects = regression.function_on_scalar_regression(
    combined_fda, np.array(age_data).reshape(-1, 1), ['age'], 'knee_angle')

# Identify phases where age has significant effects
significant_regions = age_effects.get_significant_regions(alpha=0.05)
print(f"Age significantly affects gait at: {significant_regions}")
```

### 3. Clinical Outcome Prediction
```python
# Predict clinical outcomes from gait patterns
clinical_scores = load_clinical_outcomes()  # Load outcome measures

# Use functional data to predict outcomes
prediction_results = regression.scalar_on_function_regression(
    combined_fda, clinical_scores, 'clinical_score', 'knee_angle')

# Cross-validate prediction model
cv_results = regression.cross_validate_model(
    combined_fda, clinical_scores, 'scalar_on_function', cv_folds=10)

print(f"Prediction accuracy: R² = {cv_results['mean_r2']:.3f}")
print(f"Clinical interpretation: Gait explains {cv_results['mean_r2']*100:.1f}% of outcome variance")
```

### 4. Joint Coupling Analysis
```python
# Analyze coupling between hip and knee during gait
hip_fda = fda_loco.create_functional_data('SUB01', 'level_walking', ['hip_flexion_angle_contra_rad'])
knee_fda = fda_loco.create_functional_data('SUB01', 'level_walking', ['knee_flexion_angle_contra_rad'])

# Function-on-function regression
coupling_results = regression.function_on_function_regression(
    hip_fda['hip_flexion_angle_contra_rad'],
    knee_fda['knee_flexion_angle_contra_rad'],
    'hip_angle', 'knee_angle'
)

print(f"Hip-knee coupling strength: R² = {coupling_results.r_squared:.3f}")

# Analyze coupling at component level
for i, r2 in enumerate(coupling_results.r_squared_components):
    print(f"PC{i+1} coupling: R² = {r2:.3f}")
```

## 🎨 Visualization Gallery

The FDA implementation provides comprehensive visualizations:

### 1. **Functional Data Overview**
- Individual curves with mean ± SD envelopes
- Gait phase annotations
- Feature-specific color schemes

### 2. **Comprehensive PCA Analysis**
- Scree plots with variance explained
- Principal component functions
- Mean function with variability
- Biomechanical interpretation annotations

### 3. **Registration Quality Assessment**
- Before/after alignment comparison
- Cross-sectional variance reduction
- Warping function visualization
- Method comparison plots

### 4. **Functional Regression Diagnostics**
- Coefficient functions with significance regions
- Observed vs fitted plots
- Residual analysis
- Component contribution analysis

## 🔧 Technical Implementation

### Basis Function Systems

**B-spline Basis**:
- Optimal for smooth gait curves
- Automatic knot placement
- Efficient derivative computation
- Local support properties

**Fourier Basis**:
- Natural for periodic gait patterns
- Frequency domain representation
- Global support properties
- Harmonic analysis capabilities

### Smoothing Methods

**Generalized Cross-Validation (GCV)**:
- Automatic smoothing parameter selection
- Balances fit quality vs smoothness
- Robust to outliers
- Computationally efficient

**Penalized Least Squares**:
- Roughness penalty on derivatives
- Flexible penalty weights
- Handles irregular sampling
- Maintains biomechanical constraints

### Statistical Methods

**Functional PCA**:
- SVD-based computation
- Automatic biomechanical interpretation
- Explained variance analysis
- Subject loading patterns

**Registration Algorithms**:
- Landmark-based alignment
- Continuous dynamic warping
- Quality metric computation
- Multiple method comparison

**Functional Regression**:
- PC-based dimension reduction
- Statistical inference with p-values
- Cross-validation for model selection
- Multiple regression types

## 📊 Performance Characteristics

### Computational Efficiency
- **Memory**: Efficient coefficient storage vs full curve arrays
- **Speed**: Vectorized operations for multiple curves
- **Scalability**: Linear scaling with number of subjects
- **Caching**: Intelligent caching of expensive computations

### Statistical Properties
- **Robustness**: Handles missing data and outliers
- **Validity**: Proper statistical inference with p-values
- **Accuracy**: Cross-validated prediction accuracy
- **Interpretability**: Biomechanical context and meaning

### Quality Assurance
- **Validation**: Comprehensive input validation
- **Testing**: Full integration test suite
- **Documentation**: Complete API documentation
- **Examples**: Real-world analysis examples

## 🛠️ Dependencies

### Required
- **numpy**: Numerical computations
- **pandas**: Data manipulation  
- **scipy**: Scientific computing and statistics

### Optional  
- **matplotlib**: Visualization (recommended)
- **seaborn**: Enhanced plotting (optional)
- **sklearn**: Cross-validation (fallback implementation provided)

### Installation
```bash
# Minimal installation (core functionality)
pip install numpy pandas scipy

# Full installation (with visualization)
pip install numpy pandas scipy matplotlib seaborn

# Development installation
pip install numpy pandas scipy matplotlib seaborn sklearn
```

## 🚦 Status and Roadmap

### ✅ **Completed (v2.0.0)**
- Core FDA infrastructure with basis functions
- Functional PCA with biomechanical interpretation  
- Curve registration and alignment methods
- Functional regression analysis
- Publication-ready visualizations
- Complete workflow examples
- Integration testing

### 🔄 **Future Enhancements**
- Advanced registration methods (elastic registration)
- Multivariate functional PCA
- Functional mixed-effects models
- Real-time FDA analysis capabilities
- Interactive visualization dashboard

### 📝 **Documentation Status**
- ✅ Implementation guide (this document)
- ✅ API reference documentation
- ✅ Tutorial examples
- ✅ Research application examples
- ✅ Integration testing

## 🤝 Contributing

The FDA implementation is designed for extensibility:

1. **Add New Basis Functions**: Extend `BasisFunction` class
2. **Custom Registration**: Implement new registration algorithms
3. **Enhanced Visualization**: Add domain-specific plot types
4. **Performance Optimization**: Optimize computational bottlenecks

## 📞 Support

For questions, issues, or contributions related to the FDA implementation:

1. **Technical Issues**: Check integration test results
2. **Usage Questions**: Refer to example workflows
3. **Research Applications**: Consult application examples
4. **Performance**: Review computational characteristics

---

## Summary

The FDA implementation provides a complete, production-ready functional data analysis system specifically designed for biomechanical gait analysis. With comprehensive capabilities spanning basis representation, PCA, registration, regression, and visualization, it enables sophisticated analyses while maintaining ease of use and biomechanical interpretability.

The system is built on solid mathematical foundations, provides statistical rigor with proper inference, and delivers publication-quality results. All components are thoroughly tested and documented, making it ready for immediate use in biomechanical research.

**Key Benefits**:
- 🎯 **Complete FDA System**: All components integrated and tested
- 🔬 **Research-Ready**: Real-world examples and applications  
- 📊 **Publication-Quality**: Professional visualizations and analysis
- 🚀 **Easy to Use**: Intuitive API with comprehensive documentation
- 💪 **Robust**: Statistical rigor with proper inference
- 🔧 **Extensible**: Designed for customization and enhancement

The FDA implementation represents a significant advancement in locomotion data analysis capabilities, providing researchers with powerful tools for understanding gait patterns, demographic effects, clinical outcomes, and biomechanical relationships.