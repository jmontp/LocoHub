# Converted Datasets

Local reconstruction and historical data artifacts. No dataset has completed final scientific review. See the [reconstruction backlog](../docs/maintainers/backlog.html) for current evidence and remaining work.

**Documentation:** [Datasets](../docs/datasets/index.html) • [Schema Reference](../docs/reference/index.html) • [Tutorials](../docs/tutorials/)

## Historical filenames

These names describe earlier exports, not approved releases. Use the dataset pages for source information and current limitations; use the reconstruction backlog to distinguish staged corrections from historical files.

**GTech 2021** (Georgia Tech locomotion study)
- `gtech_2021_phase_clean.parquet` – Phase-indexed dataset with failing strides removed
- `gtech_2021_phase_dirty.parquet` – Full export prior to validation filtering
- **Documentation:** [Georgia Tech 2021](../docs/datasets/gt21/index.html)

**GTech 2023** (Georgia Tech locomotion study)
- `gtech_2023_phase_raw.parquet` – Raw phase export (no validation envelope yet)
- **Documentation:** [Georgia Tech 2023](../docs/datasets/gt23/index.html)

**UMich 2021** (University of Michigan treadmill study)
- `umich_2021_phase_clean.parquet`
- `umich_2021_phase_dirty.parquet`
- **Documentation:** [UMich 2021](../docs/datasets/um21/index.html)

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
data = parquetread('gtech_2021_phase.parquet');
```

---

## Documentation

For detailed information on each dataset:
- **Dataset Documentation:** [docs/datasets/](../docs/datasets/)
- **Usage Tutorials:** [docs/tutorials/](../docs/tutorials/)
- **Schema Reference:** [File format](../docs/reference/index.html)

---

Historical filenames such as `clean` describe prior filtering, not verified scientific correctness. Corrected outputs and independent source checks are still being produced.
