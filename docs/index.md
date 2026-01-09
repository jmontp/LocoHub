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
    from locohub import LocomotionData

    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    cycles, features = subset.get_cycles('UM21_AB01', 'level_walking')
    ```

    === "MATLAB"
    ```matlab
    addpath('libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    [cycles, features] = level.getCycles('UM21_AB01', 'level_walking');
    ```

<!-- Removed trust indicators for a simpler, utilitarian homepage -->

## Download Datasets

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Strides | Documentation | Phase (Clean) | Phase | Time |
|---------|-------|---------|---------------|---------------|-------|------|
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 19,849 | <a class="md-button md-button--primary" href="datasets/gt24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2021 | Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition | 19,519 | <a class="md-button md-button--primary" href="datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | 2,940 | <a class="md-button md-button--primary" href="datasets/gt23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/xey8lljbjly0pl0o00vsb/gtech_2023_phase_clean.parquet?rlkey=ax2bk96imonvj3xb57nkho4x5&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vd24hcu6yo55qya0t0xmx/gtech_2023_phase_raw.parquet?rlkey=gdwjf6km2xc8mn92mvh495ubc&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| MBLUE Ankle Exoskeleton Study | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 15,825 | <a class="md-button md-button--primary" href="datasets/mb24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/i1q5vcoq85ot958993fv5/mblue_ankle_phase_clean.parquet?rlkey=olktfihwldiu87fuamcko788q&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/6xr64078wfvsxee4xfz7v/mblue_ankle_phase.parquet?rlkey=owrklzpaonrkgdhly74u2thr6&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | 14,240 | <a class="md-button md-button--primary" href="datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/q37ioia7zmpkxqtw5dtw6/umich_2021_phase_clean.parquet?rlkey=j9cgoam6nz7mwtadcacqff3rn&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dpk4wgtger1ktdoqrlxbr/umich_2021_phase_dirty.parquet?rlkey=rrjtx05woy1fd1du6oguai6x0&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
<!-- DATASET_TABLE_END -->

More details and validation reports: [Datasets Reference](datasets/index.md).

## Learn and Contribute

- Tutorials: [Start here](tutorials/index.md)
- API: [Overview](api/api-index.md)
- Contribute data: [Guide](contributing/index.md)

## Funding

This work was supported by the National Institute of Biomedical Imaging and Bioengineering of the NIH under Award Number R01EB031166. The content is solely the responsibility of the authors and does not necessarily represent the official views of the NIH.
