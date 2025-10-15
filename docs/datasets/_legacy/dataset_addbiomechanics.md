# AddBiomechanics Dataset

## Overview

The AddBiomechanics dataset provides comprehensive biomechanical data from multiple sources.

## Status
- **Current Phase**: Initial integration
- **Expected Completion**: TBD

## Usage

```python
from locohub import LocomotionData

# Load the dataset
data = LocomotionData('converted_datasets/addbiomechanics_phase.parquet')

# Get data for analysis
cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
```
