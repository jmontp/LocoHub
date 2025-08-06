# CLAUDE.md - User Libraries (Python)

## Overview

User-facing Python library for biomechanical data analysis and locomotion research. This is the primary interface for researchers working with standardized locomotion datasets.

## Purpose

**Public API for locomotion data analysis**. All code here is designed for external use by researchers, data scientists, and clinicians analyzing biomechanical data.

## Core Modules

### locomotion_data.py
- **Purpose**: Main data loading and analysis interface
- **Key Class**: `LocomotionData` - Loads parquet files, extracts cycles, computes statistics
- **Usage**: Primary entry point for all data analysis workflows

### feature_constants.py
- **Purpose**: Single source of truth for biomechanical feature definitions
- **Constants**: `ANGLE_FEATURES`, `MOMENT_FEATURES`, `SEGMENT_ANGLE_FEATURES`
- **Functions**: 
  - `get_sagittal_features()` - Returns sagittal plane features with display labels
  - `get_task_classification()` - Classifies tasks as 'gait' or 'bilateral'
  - `get_feature_map()` - Maps feature names to array indices
- **Critical**: Maintains consistent feature ordering across all components

### statistics/
- **Purpose**: Advanced statistical analysis methods
- **Modules**:
  - `functional_pca.py` - Functional principal component analysis
  - `functional_regression.py` - Functional regression models
  - `mixed_effects.py` - Mixed effects models for hierarchical data
- **Usage**: Statistical modeling beyond basic descriptive statistics

### fda/
- **Purpose**: Functional data analysis tools
- **Modules**:
  - `analysis.py` - Core FDA methods
  - `registration.py` - Curve registration and alignment
  - `visualization.py` - FDA-specific plotting
- **Usage**: Advanced curve analysis for biomechanical waveforms

## Usage Patterns

### Basic Data Loading
```python
from user_libs.python.locomotion_data import LocomotionData

# Load dataset
data = LocomotionData('converted_datasets/umich_2021_phase.parquet')

# Get cycles for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```

### Feature Definitions
```python
from user_libs.python.feature_constants import (
    get_sagittal_features,
    get_task_classification,
    ANGLE_FEATURES
)

# Get feature list with labels
sagittal_features = get_sagittal_features()

# Classify task type
task_type = get_task_classification('decline_walking')  # Returns 'gait'
```

### Statistical Analysis
```python
from user_libs.python.statistics.functional_pca import FunctionalPCA

# Perform functional PCA
fpca = FunctionalPCA(n_components=3)
scores = fpca.fit_transform(cycles_3d)
```

## Design Principles

1. **User-First**: APIs designed for research workflows, not implementation details
2. **Stable Interface**: Breaking changes avoided; deprecation warnings used
3. **Self-Documenting**: Clear docstrings with examples
4. **Type Hints**: Full type annotations for IDE support

## Relationship to Other Components

- **Imports from**: Nothing (self-contained user library)
- **Imported by**: 
  - `internal/` modules for feature definitions
  - `contributor_tools/` for data validation
  - User scripts and notebooks

## Common Tasks

### Get Available Features
```python
from user_libs.python.locomotion_data import LocomotionData

data = LocomotionData('dataset.parquet')
print(data.features)  # List all available biomechanical variables
print(data.get_tasks())  # List all available tasks
```

### Extract Mean Patterns
```python
# Get average patterns across cycles
mean_patterns = data.get_mean_patterns('SUB01', 'level_walking')
```

### Calculate Range of Motion
```python
# Compute ROM for all features
rom_data = data.calculate_rom('SUB01', 'level_walking')
```

## Important Notes

- **Feature Ordering**: Always use `feature_constants.py` for consistent indexing
- **Phase Indexing**: All phase data has exactly 150 points per cycle (0-100% gait cycle)
- **Units**: Angles in radians (suffix `_rad`), moments in Nm (suffix `_Nm`)
- **Coordinate System**: Ipsilateral/contralateral convention with phase alignment

## Future Extensions

Planned additions (coordinate with maintainers):
- EMG signal processing
- Force plate integration
- Real-time streaming analysis
- Machine learning pipelines

---

*This is the primary interface for researchers. Keep APIs stable and well-documented.*