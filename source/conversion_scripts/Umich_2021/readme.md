# Human Lower-Limb Biomechanics and Wearable Sensors Dataset

**Gait and Non-Cyclic Activity Biomechanics** — *A comprehensive, open-source dataset of lower limb kinematics and kinetics during continuously varying locomotion* (Reznick et al., 2021). [Publication](https://doi.org/10.1038/s41597-021-01057-9)

## 1. Overview & Citation
- **Description**:  
  Data from ten able-bodied participants performing:  
  - Level, incline (5°, 10°) and decline (−5°, −10°) walking at 0.8, 1.0, 1.2 m/s  
  - Running at 1.8, 2.0, 2.2, 2.4 m/s  
  - Constant acceleration/deceleration walking and running (±0.2, ±0.5 m/s²)  
  - Walk–run and run–walk transitions  
  - Sit-to-stand and stand-to-sit  
  - Stair ascent/descent at 20°, 25°, 30°, 35°  
  Collected with Vicon motion capture and Bertec instrumented treadmill; includes both time-continuous and stride-normalized (phase) representations :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}  
- **Citation**:  
  Reznick, E.*, Embry, K.*, Neuman, R., Bolívar, E., Fey, N., & Gregg, R. (2021).  
  *Human lower-limb kinematics and kinetics during continuously varying locomotion*.  
  Scientific Data, 8, 112. https://doi.org/10.1038/s41597-021-01057-9

## 2. Download & Setup
1. **Download**:  
   [Figshare Collection (3.47 GB)](https://springernature.figshare.com/collections/_/5175254)  
   Detailed metadata: [Figshare download](https://springernature.figshare.com/ndownloader/files/28998039)  
2. **Directory Structure**:
```

data/
├── metadata\_subject.parquet
├── metadata\_task.parquet
├── time/
│   └── \*.parquet
└── phase/
└── \*.parquet

````
3. **Environment**:
```bash
pip install pandas pyarrow
````

4. **Configuration**:
   Edit the top of each conversion script (or pass `--data-dir data/`) so it points to your local `data/` folder.

## 3. Task Descriptions & Kinetics Availability

* Full schema: [task\_definitions.md](task_definitions.md)
* **Included Tasks**:

  | Task                                                       | Kinematics | Kinetics\* | Force Plates |
  | ---------------------------------------------------------- | :--------: | :--------: | :----------: |
  | **Level Walking** (0°)                                     |      ✓     |      ✓     |       ✓      |
  | **Incline / Decline Walking** (±5°, ±10°)                  |      ✓     |      ✓     |       ✓      |
  | **Steady-State Running** (level)                           |      ✓     |      ✓     |       ✓      |
  | **Accelerated / Decelerated Locomotion** (±0.2, ±0.5 m/s²) |      ✓     |      ✓     |       ✓      |
  | **Walk–Run / Run–Walk Transitions**                        |      ✓     |      ✓     |       ✓      |
  | **Sit-to-Stand & Stand-to-Sit**                            |      ✓     |      ✗     |      ✓‡      |
  | **Stair Ascent & Descent** (20°, 25°, 30°, 35°)            |      ✓     |      ✗     |       ✗      |

  \*Joint kinetics (forces, moments, powers)
  ‡Force-plate data available but may require additional filtering

## 4. Reference Documentation Links

* [Units & Conventions](units_and_conventions.md)
* [Sign Conventions](sign_conventions.md)
* [Phase Calculation](phase_calculation.md)
* [Task Definitions](task_definitions.md)

## 5. Variables Not Included

Expect `NaN` or absence for:

* Hip adduction/rotation; ankle inversion/eversion angles
* Frontal/transverse angular velocities
* Global link orientations/velocities (torso, thigh, shank, foot in X/Y/Z)
* Load/treadmill parameters: `load_weight_kg`, `treadmill_speed_m_s`, `path_length_m`, `step_height_m`

## 6. Usage Examples

* **Python**:

  ```python
  import pandas as pd
  meta = pd.read_parquet('data/metadata_task.parquet')
  data = pd.read_parquet('data/time/dataset_time.parquet')
  df = data.merge(meta, on=['subject_id','task_id'], how='left')
  df_walk = df[df.task_name=='Level Walking']
  ```
* **MATLAB**:

  ```matlab
  ds = parquetDatastore('data');
  tbl = read(ds);
  meta = parquetread('data/metadata_task.parquet');
  T = outerjoin(tbl, meta, 'Keys', 'task_id');
  ```

## 7. Quality & Known Issues

* Missing optional channels appear as `NaN`.
* Filter by `task_id` to avoid time discontinuities at task boundaries.
* Joint kinetics are not available for sit-to-stand or stairs.
* Force-plate data below 20 N may be noisy; apply smoothing for event detection.

## 8. Version & Support

* **Version**: v1.0.0 (see `CHANGELOG.md`)
* **Original Dataset Maintainer**:
  Robert D. Gregg IV, Ph.D.
  Associate Professor, Robotics Institute, University of Michigan
  Email: [rgregg@ieee.org](mailto:rgregg@ieee.org)&#x20;
* **Standardized Dataset Maintainer**:
  Jose Montes-Perez
  Email: [email@example.com](mailto:email@example.com)
* **Issues**:

  * For **standardization script** bugs or feature requests, please open an issue at [GitHub Issues](https://github.com/your/repo/issues).
  * For questions or corrections related to the **original dataset**, please contact the original dataset maintainer.
