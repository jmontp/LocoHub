# API Reference

Comprehensive technical documentation for developers and researchers integrating the locomotion data standardization platform.

## Quick Navigation

- **[LocomotionData API](locomotion-data-api.md)** - Core data analysis class
- **[Validation API](validation-api.md)** - Dataset validation and quality assessment  
- **[Integration Guides](../integration/README.md)** - Platform integration patterns
- **[Developer Workflows](../developer/README.md)** - Contributing and extending the platform

## API Overview

The platform provides three main APIs:

### Core Analysis API
```python
from lib.core.locomotion_analysis import LocomotionData

# Load and analyze data
loco = LocomotionData('dataset_phase.parquet')
data_3d, features = loco.get_cycles('SUB01', 'level_walking')
```

### Validation API  
```python
from lib.validation.dataset_validator_phase import DatasetValidator

# Validate dataset quality
validator = DatasetValidator('dataset_phase.parquet')
report_path = validator.run_validation()
```

### Feature Constants API
```python
from lib.core.feature_constants import ANGLE_FEATURES, get_feature_list

# Get standard variable ordering
kinematic_vars = get_feature_list('kinematic')
```

## Design Principles

- **Minimal, Understandable Code**: Functions do one thing well
- **Explicit Error Handling**: Clear error messages over silent failures
- **Standard Compliance**: Strict variable naming and data format validation
- **Performance Optimized**: Efficient 3D array operations for large datasets
- **Extensible Architecture**: Easy to add new validation rules and data sources

## Getting Started

1. **For Analysis**: Start with [LocomotionData API](locomotion-data-api.md)
2. **For Validation**: See [Validation API](validation-api.md)  
3. **For Integration**: Check [Integration Guides](../integration/README.md)
4. **For Contributing**: Review [Developer Workflows](../developer/README.md)