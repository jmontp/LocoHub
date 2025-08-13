# Converted Datasets

Standardized biomechanical datasets ready for analysis.

**Documentation:** [Dataset Documentation](../docs/datasets_documentation/) • [Format Specification](../docs/standard_spec/standard_spec.md) • [Tutorials](../docs/tutorials/)

## Available Datasets

**GTech 2021** - Georgia Tech 2021 study:
- `gtech_2021_phase.parquet` - Phase-indexed dataset (150 points/cycle) 
- **Documentation:** [dataset_gtech_2021.md](../docs/reference/datasets_documentation/dataset_gtech_2021.md)

**GTech 2023** - Georgia Tech 2023 study:
- `gtech_2023_phase.parquet` - Phase-indexed dataset (150 points/cycle)
- **Documentation:** [dataset_gtech_2023.md](../docs/reference/datasets_documentation/dataset_gtech_2023.md)

**UMich 2021** - University of Michigan treadmill study:
- `umich_2021_phase.parquet` - Phase-indexed dataset (150 points/cycle)
- **Documentation:** [dataset_umich_2021.md](../docs/reference/datasets_documentation/dataset_umich_2021.md)

---

## Data Format

**Variable Naming:** `<joint>_<motion>_<measurement>_<side>_<unit>`
- Examples: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`

**Data Types:**
- **Time-indexed:** Original sampling frequency with `time_s` column
- **Phase-indexed:** 150 points per gait cycle with `phase_percent` column

---

## Quick Start

**Python:**
```python
import pandas as pd
data = pd.read_parquet('gtech_2021_phase.parquet')
```

**MATLAB:**
```matlab
data = readtable('gtech_2021_phase.parquet');
```

---

## Documentation

For detailed information on each dataset:
- **Dataset Documentation:** [docs/datasets_documentation/](../docs/datasets_documentation/)
- **Usage Tutorials:** [docs/tutorials/](../docs/tutorials/)
- **Format Specification:** [docs/standard_spec/](../docs/standard_spec/)

---

*These datasets are cleaned, tested, and ready for reproducible biomechanical research.*