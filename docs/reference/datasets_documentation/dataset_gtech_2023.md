# GTech 2023 Dataset

## Overview

The Georgia Tech 2023 dataset is currently being processed for standardization.

## Status
- **Current Phase**: Data conversion and validation
- **Expected Completion**: TBD

## Usage

```python
from user_libs.python.locomotion_data import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/gtech_2023_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```
