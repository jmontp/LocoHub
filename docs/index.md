<!-- removed homepage title hiding and hero styles -->

# LocoHub

Standardized biomechanical datasets and simple tools to load, filter, and analyze them in Python and MATLAB.

## What the data looks like

Each row is one point in a percent‑normalized gait cycle (typically 150 samples from 0–100%). Columns include subject/task metadata and standardized biomechanical variables.

| subject_id | subject_metadata            | task           | task_id               | task_info                       | step | phase_percent | knee_flexion_angle_ipsi_rad | hip_moment_ipsi_Nm |
|------------|-----------------------------|----------------|-----------------------|----------------------------------|------|---------------|-----------------------------|--------------------|
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0     | 1    | 0.0           | 0.524                       | 0.85               |
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0     | 1    | 0.67          | 0.541                       | 0.82               |
| GT23_AB05  | age:28,sex:F,height_m:1.68 | incline_walking| incline_10deg         | speed_m_s:1.0,incline_deg:10    | 3    | 0.0           | 0.698                       | 0.90               |
| PROS_TFA03 | age:41,sex:M,prosthesis:TFA | stair_ascent   | stair_ascent_17cm     | step_height_m:0.17,step_w_m:0.28| 2    | 0.0           | 0.873                       | 1.10               |
| …          | …                           | …              | …                     | …                                | …    | …             | …                           | …                  |

- Metadata columns: `subject_id`, optional `subject_metadata`, `task`, `task_id`, `task_info`, `step`, and `phase_percent`.
- Variable columns follow the naming convention `joint_motion_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`, `hip_moment_ipsi_Nm`).

### More details and definitions

- [Reference](reference/index.md)
- [Technical Specification](reference/index.md)
- [Task Definitions](reference/index.md)
- [Validation Ranges](reference/index.md)
- [Data Table Schema](contributing/contributing_skeleton.md)

## Quickstart

=== "Using Raw Data"

    === "Python"
    ```python
    import pandas as pd

    # Load phase-indexed parquet directly
    df = pd.read_parquet('umich_2021_phase.parquet')

    # Filter to a subject + task of interest
    subset = df[(df['task'] == 'level_walking') & (df['subject_id'] == 'UM21_AB01')]

    # Access normalized phase and a variable
    phase = subset['phase_percent'].to_numpy()
    knee = subset['knee_flexion_angle_ipsi_rad'].to_numpy()
    ```

    === "MATLAB"
    ```matlab
    % Load phase-indexed parquet directly (R2021b+)
    T = parquetread('umich_2021_phase.parquet');

    % Filter to a subject + task of interest
    subset = T(T.task == "level_walking" & T.subject_id == "UM21_AB01", :);

    % Access normalized phase and a variable
    phase = subset.phase_percent;
    knee  = subset.knee_flexion_angle_ipsi_rad;
    ```

=== "Using Library"

    === "Python"
    ```python
    from user_libs.python.locomotion_data import LocomotionData

    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    cycles, features = subset.get_cycles('UM21_AB01', 'level_walking')
    ```

    === "MATLAB"
    ```matlab
    addpath('user_libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    [cycles, features] = level.getCycles('UM21_AB01', 'level_walking');
    ```

<!-- Removed trust indicators for a simpler, utilitarian homepage -->

## Download Datasets

| Dataset | Tasks | Quality | Documentation | Download |
|---------|-------|---------|---------------|----------|
| Georgia Tech 2023 | Walking, stairs, inclines | ✓ Validated | [Docs](datasets/dataset_gtech_2023.md) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| Georgia Tech 2021 | Walking, stairs, inclines | ✓ Validated | [Docs](datasets/dataset_gtech_2021.md) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| University of Michigan 2021 | Level, incline, decline walking | ✓ Validated | [Docs](datasets/dataset_umich_2021.md) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| AddBiomechanics | Walking, running, jumping, stairs | Coming Soon | [Docs](datasets/dataset_addbiomechanics.md) | Coming Soon |

More details and validation reports: [Datasets Reference](datasets/).

## Learn and Contribute

- Tutorials: [Start here](tutorials/index.md)
- API: [Overview](api/api-index.md)
- Contribute data: [Guide](contributing/conversion_guide.md) • [Data Table Schema](contributing/contributing_skeleton.md)
