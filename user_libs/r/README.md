# LocomotionData R Package

> **Status: Development** - This R package is part of the locomotion data standardization framework and mirrors the Python API.

An R package for loading, processing, and analyzing standardized biomechanical locomotion data. Provides S4 classes for efficient handling of phase-indexed gait cycle data with comprehensive validation, statistical analysis, and publication-ready visualization tools.

## Features

- **Strict Variable Name Validation**: Enforces standard naming convention (`<joint>_<motion>_<measurement>_<side>_<unit>`)
- **Efficient 3D Array Operations**: Optimized for gait cycle analysis with caching
- **Comprehensive Data Quality Assessment**: Built-in validation and outlier detection
- **Advanced Statistical Analysis**: Mixed-effects models, Bayesian analysis, correlation analysis
- **Machine Learning Tools**: PCA, t-SNE, UMAP, clustering, classification with cross-validation
- **Bayesian Statistics**: t-tests, ANOVA, correlation analysis with Bayes factors
- **Publication-Ready Visualizations**: ggplot2-based plotting with customizable themes
- **Multi-Format Data Loading**: Support for parquet and CSV files

## Installation

### Dependencies

The package requires several R packages. Install them first:

```r
# Core dependencies
install.packages(c(
  "methods", "data.table", "arrow", "ggplot2", 
  "dplyr", "tibble", "readr", "magrittr", "lme4",
  "BayesFactor", "randomForest", "e1071", "cluster"
))

# Optional for enhanced functionality
install.packages(c(
  "testthat", "knitr", "rmarkdown", "fda", 
  "plotly", "viridis", "patchwork", "coda",
  "factoextra", "corrplot", "Rtsne", "umap",
  "caret", "pROC", "ROCR"
))
```

### From Source

```r
# Install from local source (development)
devtools::install("path/to/locomotion-data-standardization/source/lib/r")

# Or install dependencies and load source
source("path/to/locomotion-data-standardization/source/lib/r/R/LocomotionData-package.R")
```

## Quick Start

```r
library(LocomotionData)

# Load standardized locomotion data
loco <- loadLocomotionData("gait_data.parquet")

# Basic analysis
cycles_result <- getCycles(loco, "SUB01", "normal_walk")
mean_patterns <- getMeanPatterns(loco, "SUB01", "normal_walk")
rom_data <- calculateROM(loco, "SUB01", "normal_walk")

# Quality assessment
valid_mask <- validateCycles(loco, "SUB01", "normal_walk")
outliers <- findOutlierCycles(loco, "SUB01", "normal_walk")

# Visualization
plotPhasePatterns(loco, "SUB01", "normal_walk", 
                 c("knee_flexion_angle_contra_rad"))
```

## Package Architecture

### S4 Class System

The package uses S4 classes to provide a robust object-oriented interface:

```r
# LocomotionData class structure
setClass("LocomotionData",
  slots = list(
    data = "data.table",           # Raw locomotion data
    subjects = "character",        # Unique subject IDs  
    tasks = "character",           # Unique task names
    features = "character",        # Biomechanical features
    data_path = "character",       # Original file path
    subject_col = "character",     # Subject column name
    task_col = "character",        # Task column name
    phase_col = "character",       # Phase column name
    feature_mappings = "list",     # Feature name mappings
    validation_report = "list",    # Variable validation results
    cache = "list",                # 3D array cache
    points_per_cycle = "integer"   # Points per gait cycle (150)
  )
)
```

### Method Signatures

Core methods mirror the Python API:

```r
# Data access methods
getSubjects(object)
getTasks(object) 
getFeatures(object)
getCycles(object, subject, task, features = NULL)
getMeanPatterns(object, subject, task, features = NULL)
getStdPatterns(object, subject, task, features = NULL)

# Analysis methods
validateCycles(object, subject, task, features = NULL)
findOutlierCycles(object, subject, task, features = NULL, threshold = 2.0)
getSummaryStatistics(object, subject, task, features = NULL)
calculateROM(object, subject, task, features = NULL, by_cycle = TRUE)

# Validation methods
getValidationReport(object)
isStandardCompliant(variable_name)
suggestStandardName(variable_name)

# Plotting methods
plotPhasePatterns(object, subject, task, features, plot_type = "both")
plotTaskComparison(object, subject, tasks, features)
plotTimeSeries(object, subject, task, features, time_col = "time_s")
```

## Variable Naming Convention

**Standard Format**: `<joint>_<motion>_<measurement>_<side>_<unit>`

### Examples

- `knee_flexion_angle_contra_rad` - Knee flexion angle, contralateral side, radians
- `hip_flexion_moment_ipsi_Nm` - Hip flexion moment, ipsilateral side, Newton-meters
- `ankle_flexion_velocity_contra_rad_s` - Ankle flexion velocity, contralateral side, rad/s

### Components

- **Joints**: `hip`, `knee`, `ankle`
- **Motions**: `flexion`, `adduction`, `rotation`
- **Measurements**: `angle`, `velocity`, `moment`, `power`
- **Sides**: `contra` (contralateral), `ipsi` (ipsilateral)
- **Units**: `rad`, `rad_s`, `Nm`, `Nm_kg`, `W`, `W_kg`, `deg`, `deg_s`, `N`, `m`

## Feature Constants

The package provides predefined feature lists for consistency:

```r
# Kinematic features (joint angles)
ANGLE_FEATURES        # 6 features: hip, knee, ankle x ipsi, contra

# Velocity features (joint angular velocities)  
VELOCITY_FEATURES     # 6 features: hip, knee, ankle x ipsi, contra

# Kinetic features (joint moments)
MOMENT_FEATURES       # 18 features: 3 joints x 3 motions x 2 sides
MOMENT_FEATURES_NORMALIZED  # Normalized by body weight

# Ground reaction forces and center of pressure
GRF_FEATURES          # Vertical, AP, ML components
COP_FEATURES          # X, Y, Z coordinates

# Access feature mappings
kinematic_map <- getKinematicFeatureMap()
kinetic_map <- getKineticFeatureMap()
all_constants <- getFeatureConstants()
```

## Data Format Requirements

### Phase-Indexed Data

- **150 points per gait cycle** (0-100% normalized)
- **Required columns**: subject, task, phase
- **Standard features**: Follow naming convention
- **File formats**: Parquet (preferred) or CSV

### Example Data Structure

```
subject | task        | phase | knee_flexion_angle_contra_rad | ...
--------|-------------|-------|-------------------------------|----
SUB01   | normal_walk | 0.0   | 0.12                         | ...
SUB01   | normal_walk | 0.67  | 0.15                         | ...
...     | ...         | ...   | ...                          | ...
SUB01   | normal_walk | 100.0 | 0.11                         | ...
```

## Validation Framework

### Automatic Validation

The package performs several validation checks:

1. **File Format**: Parquet/CSV loading with error handling
2. **Required Columns**: Subject, task, phase columns must exist
3. **Data Dimensions**: Must have complete gait cycles (divisible by 150)
4. **Phase Range**: Values should be 0-100%
5. **Variable Names**: Must follow standard convention
6. **Biomechanical Constraints**: Range and continuity checks

### Cycle Validation

```r
# Validate individual cycles
valid_mask <- validateCycles(loco, "SUB01", "normal_walk")

# Validation criteria:
# - Angles: -π to π radians, no large discontinuities (>30°)
# - Velocities: ±1000°/s (±17.45 rad/s)  
# - Moments: ±300 Nm
# - No NaN or infinite values
```

## Visualization

### Phase Pattern Plots

```r
# Mean patterns with confidence bands
plotPhasePatterns(loco, "SUB01", "normal_walk", features, plot_type = "mean")

# Individual cycles (spaghetti plot)
plotPhasePatterns(loco, "SUB01", "normal_walk", features, plot_type = "spaghetti")

# Combined view
plotPhasePatterns(loco, "SUB01", "normal_walk", features, plot_type = "both")
```

### Task Comparison

```r
# Compare mean patterns across tasks
plotTaskComparison(loco, "SUB01", 
                  tasks = c("normal_walk", "fast_walk"),
                  features = c("knee_flexion_angle_contra_rad"))
```

### Customization

All plots return ggplot objects for further customization:

```r
p <- plotPhasePatterns(loco, "SUB01", "normal_walk", features)
p + ggplot2::theme_minimal() + ggplot2::labs(title = "Custom Title")
```

## Performance Features

### Caching System

- **Automatic caching** of 3D array results
- **Cache key**: subject + task + features combination
- **Memory efficient** for repeated analyses

### Efficient Data Structures

- **data.table** backend for fast operations
- **3D arrays** with named dimensions
- **Vectorized operations** for statistical analysis

### Batch Processing

```r
# Standalone function for batch processing
result <- efficientReshape3D(
  data = data_table,
  subject = "SUB01",
  task = "normal_walk", 
  features = feature_list,
  points_per_cycle = 150
)
```

## Integration with R Ecosystem

### Compatible Packages

- **data.table**: High-performance data manipulation
- **ggplot2**: Publication-ready visualizations
- **arrow**: Efficient parquet file handling
- **fda**: Functional data analysis (suggested)
- **lme4**: Mixed-effects modeling (suggested)

### Workflow Integration

```r
# Extract data for external analysis
cycles_result <- getCycles(loco, "SUB01", "normal_walk")
data_3d <- cycles_result$data_3d

# Use with other packages
library(fda)
basis <- create.bspline.basis(c(0, 100), nbasis = 15)
fd_object <- Data2fd(y = data_3d[,,1], argvals = 0:99, basisobj = basis)
```

## Testing Framework

The package includes comprehensive tests using testthat:

```r
# Run tests
devtools::test()

# Test coverage
covr::package_coverage()
```

### Test Categories

- **Feature constants**: Verify predefined feature lists
- **Validation functions**: Test naming convention checks
- **Utility functions**: Unit conversions, phase calculations
- **S4 methods**: Class functionality and error handling

## Development Status

### Completed Components

- ✅ **Package structure**: DESCRIPTION, NAMESPACE, directory layout
- ✅ **S4 class definition**: LocomotionData class with all slots
- ✅ **Feature constants**: Complete feature definitions and mappings
- ✅ **Validation framework**: Variable naming and data format validation
- ✅ **Core methods**: Data access, analysis, and quality assessment
- ✅ **Plotting system**: ggplot2-based visualization methods
- ✅ **Utility functions**: Unit conversion, phase calculation helpers
- ✅ **Mixed-effects modeling**: Complete lme4 integration with biomech templates
- ✅ **Bayesian analysis**: BayesFactor integration with t-tests, ANOVA, correlation
- ✅ **Machine learning**: PCA, t-SNE, UMAP, clustering, classification
- ✅ **ML workflows**: Cross-validation, hyperparameter tuning, feature selection
- ✅ **Testing framework**: Comprehensive test suite with testthat
- ✅ **Documentation**: Roxygen2 documentation and vignettes

### Next Steps

1. **Implementation Testing**: Test with real locomotion datasets
2. **Method Refinement**: Optimize performance and add missing features
3. **Integration Testing**: Validate against Python API for consistency
4. **Advanced Visualizations**: Additional plot types and customization
5. **Package Building**: R CMD check compliance and CRAN preparation

## Advanced Statistical Analysis

### Bayesian Analysis

The package provides comprehensive Bayesian statistical analysis capabilities:

```r
# Bayesian t-test comparing conditions
bayes_result <- bayes_ttest_biomech(
  loco_data, 
  feature = "knee_flexion_angle_contra_rad",
  condition1 = "normal_walk",
  condition2 = "fast_walk",
  summary_type = "mean"
)

# Bayesian ANOVA for multiple conditions
anova_result <- bayes_anova_biomech(
  loco_data,
  feature = "knee_flexion_angle_contra_rad",
  conditions = c("normal_walk", "fast_walk", "incline_walk")
)

# Bayesian correlation analysis
corr_result <- bayes_correlation_biomech(
  loco_data,
  feature1 = "knee_flexion_angle_contra_rad",
  feature2 = "hip_flexion_angle_contra_rad",
  condition = "normal_walk"
)

# Interpret Bayes factors
interpret_bayes_factor(bayes_result$bayes_factor)
```

### Mixed-Effects Modeling

Advanced hierarchical modeling for biomechanical research:

```r
# Prepare data for mixed-effects modeling
mixed_data <- prepare_mixed_effects_data(loco_data, include_phase = TRUE)

# Fit gait analysis model
gait_model <- fit_gait_analysis_model(
  loco_data,
  outcome = "knee_flexion_angle_contra_rad",
  tasks = c("normal_walk", "fast_walk")
)

# Compare different subject groups
group_info <- c("SUB01" = "control", "SUB02" = "patient")
group_model <- fit_group_comparison_model(loco_data, outcome, group_info)

# Model comparison and diagnostics
diagnostics <- run_model_diagnostics(gait_model)
assumptions <- check_model_assumptions(gait_model)
```

## Machine Learning and Data Mining

### Data Preparation and Dimensionality Reduction

```r
# Prepare data for machine learning
ml_data <- prepare_ml_data(
  loco_data,
  summary_type = "mean",  # or "rom", "full_cycle", "peak_values"
  normalize = TRUE
)

# Principal Component Analysis
pca_result <- biomech_pca(ml_data, n_components = 5)

# t-SNE for non-linear dimensionality reduction
tsne_result <- biomech_tsne(ml_data, dims = 2, perplexity = 30)

# UMAP for visualization
umap_result <- biomech_umap(ml_data, n_components = 2)
```

### Clustering and Classification

```r
# K-means clustering
kmeans_result <- biomech_kmeans(ml_data, k = 3)

# Hierarchical clustering
hclust_result <- biomech_hierarchical(ml_data, method = "ward.D2")

# Random Forest classification
rf_result <- biomech_random_forest(ml_data, target = "tasks", ntree = 500)

# Support Vector Machine
svm_result <- biomech_svm(ml_data, target = "tasks", kernel = "radial")
```

### Complete ML Workflows

```r
# Feature selection
fs_result <- biomech_feature_selection(
  ml_data, 
  target = "tasks", 
  method = "importance",
  n_features = 10
)

# Cross-validation with subject grouping
cv_result <- biomech_cross_validation(
  ml_data,
  target = "tasks",
  method = "random_forest",
  folds = 5
)

# Hyperparameter tuning
tuning_result <- biomech_hyperparameter_tuning(
  ml_data,
  target = "tasks",
  method = "random_forest",
  cv_folds = 5
)

# Model comparison
comparison <- biomech_model_comparison(
  ml_data,
  target = "tasks",
  methods = c("random_forest", "svm"),
  feature_selection = TRUE
)

# Complete ML pipeline
pipeline_result <- biomech_ml_pipeline(
  loco_data,
  target = "tasks",
  summary_type = "mean",
  feature_selection = TRUE,
  hyperparameter_tuning = TRUE,
  methods = c("random_forest", "svm")
)
```

## Python API Compatibility

This R package is designed to mirror the Python LocomotionData API:

| Python Method | R Method | Status |
|---------------|----------|---------|
| `LocomotionData()` | `loadLocomotionData()` | ✅ Complete |
| `get_cycles()` | `getCycles()` | ✅ Complete |
| `get_mean_patterns()` | `getMeanPatterns()` | ✅ Complete |
| `validate_cycles()` | `validateCycles()` | ✅ Complete |
| `plot_phase_patterns()` | `plotPhasePatterns()` | ✅ Complete |
| `find_outlier_cycles()` | `findOutlierCycles()` | ✅ Complete |
| `calculate_rom()` | `calculateROM()` | ✅ Complete |
| `get_validation_report()` | `getValidationReport()` | ✅ Complete |

## Contributing

This package is part of the larger locomotion data standardization project. For contributing guidelines, see the main project documentation.

## License

MIT License - see the main project LICENSE file.

## Citation

```
Montes Pérez, J.A. (2025). LocomotionData R Package: Standardized Biomechanical 
Data Analysis. Locomotion Data Standardization Framework.
```

---

**Note**: This is a development version. The API may change before the first stable release.