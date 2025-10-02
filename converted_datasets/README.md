# Converted Datasets

Standardized biomechanical datasets ready for analysis.

**Documentation:** [Datasets](../docs/datasets/index.md) • [Schema Reference](../docs/reference/index.md) • [Tutorials](../docs/tutorials/)

## Available Datasets

**GTech 2021** (Georgia Tech locomotion study)
- `gtech_2021_phase_clean.parquet` – Phase-indexed dataset with failing strides removed
- `gtech_2021_phase_dirty.parquet` – Full export prior to validation filtering
- **Documentation:** [docs/datasets/gt21.md](../docs/datasets/gt21.md)

**GTech 2023** (AddBiomechanics export)
- `gtech_2023_phase_raw.parquet` – Raw phase export (no validation envelope yet)
- **Documentation:** [docs/datasets/_legacy/dataset_gtech_2023.md](../docs/datasets/_legacy/dataset_gtech_2023.md)

**UMich 2021** (University of Michigan treadmill study)
- `umich_2021_phase_clean.parquet`
- `umich_2021_phase_dirty.parquet`
- **Documentation:** [docs/datasets/um21.md](../docs/datasets/um21.md)

---

## Data Format

**Variable Naming:** `<joint>_<motion>_<measurement>_<side>_<unit>`
- Examples: `knee_flexion_angle_ipsi_rad`, `hip_flexion_moment_contra_Nm_kg`

**Data Types:**
- **Phase-indexed:** 150 samples per gait cycle with `phase_ipsi` column
- **Time-indexed:** Stored separately when available; see dataset docs for details

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
- **Dataset Documentation:** [docs/datasets/](../docs/datasets/)
- **Usage Tutorials:** [docs/tutorials/](../docs/tutorials/)
- **Schema Reference:** [docs/reference/index.md](../docs/reference/index.md)

---

*These datasets are cleaned, tested, and ready for reproducible biomechanical research.*
