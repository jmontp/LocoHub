<!-- removed homepage title hiding and hero styles -->

# LocoHub

Researchers collect locomotion datasets with different sampling schemes, variable names, and metadata conventions, which makes cross-study analysis slow and error-prone. Manually processing each dataset typically takes hours per person and often requires extra post-processing to repair data issues and align conventions, and folks without a biomechanics background often lack the knowledge to even start that cleanup. LocoHub standardizes these independent datasets into a shared schema, percent-normalized gait cycles, and validated metadata so you can compare studies, reproduce analyses, and build new models without reformatting everything from scratch. Standardized biomechanical datasets and simple tools to load, filter, and analyze them in Python and MATLAB.

## What the data looks like

Each row is one point in a percent‑normalized gait cycle (typically 150 samples from 0–100%). Columns include subject/task metadata and standardized biomechanical variables.

| subject | subject_metadata            | task           | task_id               | task_info                        | step | phase_ipsi | knee_flexion_angle_ipsi_rad | hip_flexion_moment_ipsi_Nm_kg |
|---------|-----------------------------|----------------|-----------------------|-----------------------------------|------|------------|-----------------------------|------------------------------|
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0      | 1    | 0.00       | 0.524                       | 0.85                         |
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0      | 1    | 0.67       | 0.531                       | 0.82                         |
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0      | 1    | 1.33       | 0.559                       | 0.81                         |
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0      | 1    | 2.00       | 0.576                       | 0.80                         |
| …          | …                           | …              | …                     | …                                 | …    | …          | …                           | …                            |
| UM21_AB01  | age:25,sex:M,height_m:1.75 | level_walking  | level_walking_normal  | speed_m_s:1.2,incline_deg:0      | 1    | 99.33      | 0.507                       | 0.80                         |

- Metadata columns: `subject`, optional `subject_metadata`, `task`, `task_id`, `task_info`, `step`, and `phase_ipsi`.
- Variable columns follow the naming convention `joint_motion_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`, `hip_flexion_moment_ipsi_Nm_kg`).

### More details and definitions

- [Reference](reference/index.md)


## Quickstart

=== "Using Raw Data"

    === "Python"
    ```python
    import pandas as pd

    # Load phase-indexed parquet directly
    df = pd.read_parquet('umich_2021_phase.parquet')

    # Filter to a subject + task of interest
    subset = df[(df['task'] == 'level_walking') & (df['subject'] == 'UM21_AB01')]

    # Access normalized phase and a variable
    phase = subset['phase_ipsi'].to_numpy()
    knee = subset['knee_flexion_angle_ipsi_rad'].to_numpy()
    ```

    === "MATLAB"
    ```matlab
    % Load phase-indexed parquet directly (R2021b+)
    T = parquetread('umich_2021_phase.parquet');

    % Filter to a subject + task of interest
    subset = T(T.task == "level_walking" & T.subject == "UM21_AB01", :);

    % Access normalized phase and a variable
    phase = subset.phase_ipsi;
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

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Quality | Documentation | Download |
|---------|-------|---------|---------------|----------|
| [Georgia Tech 2021](https://jmontp.github.io/LocoHub/datasets/gtech_2021_raw/) | Level Walking, Incline Walking, Decline Walking, Stair Ascent, Stair Descent | ⚠️ Partial (89.2%) | [Docs](https://jmontp.github.io/LocoHub/datasets/gtech_2021_raw/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [Georgia Tech 2021 (Filtered)](https://jmontp.github.io/LocoHub/datasets/gtech_2021_filtered/) | Level Walking, Incline Walking, Decline Walking, Stair Ascent, Stair Descent | ✅ Validated | [Docs](https://jmontp.github.io/LocoHub/datasets/gtech_2021_filtered/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [University of Michigan 2021](https://jmontp.github.io/LocoHub/datasets/umich_2021_raw/) | Level Walking, Incline Walking, Decline Walking, Run, Sit To Stand, Stand To Sit | ⚠️ Partial (92.7%) | [Docs](https://jmontp.github.io/LocoHub/datasets/umich_2021_raw/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [University of Michigan 2021 (Filtered)](https://jmontp.github.io/LocoHub/datasets/umich_2021_filtered/) | Level Walking, Incline Walking, Decline Walking, Run, Sit To Stand, Stand To Sit | ✅ Validated | [Docs](https://jmontp.github.io/LocoHub/datasets/umich_2021_filtered/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
<!-- DATASET_TABLE_END -->

More details and validation reports: [Datasets Reference](datasets/index.md).

## Learn and Contribute

- Tutorials: [Start here](tutorials/index.md)
- API: [Overview](api/api-index.md)
- Contribute data: [Guide](contributing/index.md)

## Funding

This work was supported by the National Institute of Biomedical Imaging and Bioengineering of the NIH under Award Number R01EB031166. The content is solely the responsibility of the authors and does not necessarily represent the official views of the NIH.
