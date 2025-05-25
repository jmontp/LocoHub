
# Dataset Title with Publication Link

**Dataset Name** — *Title of Study* (Author et al., Year). [Publication](https://doi.org/your-doi-here)

## 1. Overview & Citation
- **Description**: Brief summary of the dataset’s scope.
- **Citation**: Author, A. et al. (Year). *Title of paper*. Journal, Volume(Issue), pages. DOI link.

## 2. Download & Setup
1. **Download**: Instructions or link to obtain data (e.g., via Zenodo, institutional FTP).
2. **Directory Structure**: After download, organize files as:


data/
├── metadata\_subject.parquet
├── metadata\_task.parquet
├── time/
│   └── \*.parquet
└── phase/
└── \*.parquet

3. **Environment**: Install required packages or modules (e.g., `pip install your-standardizer`).
4. **Configuration**: Point scripts to your local `data/` folder (via config file or command-line argument).

## 3. Task Descriptions
- Link to `task_definitions.md` for full schema.
- **Included Tasks**: `level_walking`, `incline_walking`, `decline_walking`, `run`, `meander`, `cutting`, `obstacle_walk`, `side_shuffle`, `curb_up`, `curb_down`, `up_stairs`, `down_stairs`, `sit_to_stand`, `stand_to_sit`, `poses`, `lift_weight`, `push`, `jump`, `lunges`, `squats`, `ball_toss_l`, `ball_toss_m`, `ball_toss_r`.

## 4. Reference Documentation Links
For detailed specifications, see the centralized standard docs:
- [Units & Conventions](units_and_conventions.md)
- [Sign Conventions](sign_conventions.md)
- [Phase Calculation](phase_calculation.md)
- [Task Definitions](task_definitions.md)

## 5. Variables Not Included in This Dataset
This dataset omits the following standard variables; users should expect `NaN` or absence:
- Joint angles: `hip_adduction_angle`, `hip_rotation_angle`, `ankle_inversion_angle`, `ankle_rotation_angle`
- Joint velocities: frontal/transverse angular velocities
- Global link orientations and velocities: torso, thigh, shank, foot in X/Y/Z
- Load-specific parameters: `load_weight_kg`, `treadmill_speed_m_s`, `path_length_m`, `step_height_m`

## 6. Usage Examples Usage Examples
- **Python Example**:
```python
import pandas as pd

# Load metadata and time-series
meta = pd.read_parquet('data/metadata_task.parquet')
data = pd.read_parquet('data/time/dataset_time.parquet')

# Merge on task_id
df = data.merge(meta, on=['subject_id','task_id'], how='left')

# Filter a specific task
df_walk = df[df.task_name=='level_walking']
````

* **MATLAB Example**:

  ```matlab
  ds = parquetDatastore('data');
  tbl = read(ds);
  meta = parquetread('data/metadata_task.parquet');
  T = outerjoin(tbl, meta, 'Keys', 'task_id');
  ```

## 5. Quality & Known Issues

* Missing optional channels show as `NaN`.
* Time discontinuities at task boundaries—filter by `task_id` before continuous analyses.
* Force plate data unreliable below 20 N; heel-strike events may require smoothing.

## 6. Version & Support

* **Version**: vX.Y.Z (See `CHANGELOG.md` for details)
* **Maintainer**: Name, [email@example.com](mailto:email@example.com)
* **Issues**: Please report bugs or questions at [Issue Tracker](https://github.com/your/repo/issues)
