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
| Dataset | Tasks | Documentation | Clean Dataset | Full Dataset |
|---------|-------|---------------|---------------|---------------|
| Carter 2023 | Level Walking, Run | <a class="md-button md-button--primary" href="datasets/ca23/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Falisse 2016 | Level Walking | <a class="md-button md-button--primary" href="datasets/fa16/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Fregly 2012 | Dynamic Walk, Level Walking | <a class="md-button md-button--primary" href="datasets/fr12/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | <a class="md-button md-button--primary" href="datasets/gt24/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Gtech 2021 | Level Walking, Stair Ascent, Stair Descent, Transition | <a class="md-button md-button--primary" href="datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/h2aitlo77ujndhcqzhswo/gtech_2021_phase_clean.parquet?rlkey=zitswlvbc7g8bgt2f3jx3zyfx&st=26wq9hpi&raw=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/fvv83iipnhtapkaa1z70g/gtech_2021_phase_dirty.parquet?rlkey=fp7q7a3b0t8t6bivc9lynu5uj&st=idfk1sk4&raw=1">Download</a> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | <a class="md-button md-button--primary" href="datasets/gt23/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Hamner 2013 | Run | <a class="md-button md-button--primary" href="datasets/ha13/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Han 2023 (GroundLink) | Jump, Level Walking | <a class="md-button md-button--primary" href="datasets/ha23/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Moore 2015 | Level Walking | <a class="md-button md-button--primary" href="datasets/mo15/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Tan 2021 | Run | <a class="md-button md-button--primary" href="datasets/ta21/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Tan 2022 | Dynamic Walk | <a class="md-button md-button--primary" href="datasets/ta22/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Tiziana 2019 (Lencioni) | Level Walking | <a class="md-button md-button--primary" href="datasets/ti19/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | <a class="md-button md-button--primary" href="datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/typd1b24lfks6unjdiagf/umich_2021_phase_clean.parquet?rlkey=il6z7dnfs5i9n96tc90h1s244&st=vasjkbl2&raw=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/21mbjl4g148idosnl5li1/umich_2021_phase_dirty.parquet?rlkey=jbcy3l53wgapuyc2e3k2pgbn6&st=tuctu1y2&raw=1">Download</a> |
| UMich 2024 (Knee Exoskeleton) | Decline Walking, Incline Walking, Level Walking, Squat, Stair Ascent, Stair Descent | <a class="md-button md-button--primary" href="datasets/um24k/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| van der Zee 2022 | Level Walking | <a class="md-button md-button--primary" href="datasets/vz22/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
| Wang 2023 | Jump, Level Walking, Lunge, Run | <a class="md-button md-button--primary" href="datasets/wa23/">Docs</a> | <span class="md-button md-button--disabled">Coming soon</span> | <span class="md-button md-button--disabled">Coming soon</span> |
<!-- DATASET_TABLE_END -->

More details and validation reports: [Datasets Reference](datasets/index.md).

## Learn and Contribute

- Tutorials: [Start here](tutorials/index.md)
- API: [Overview](api/api-index.md)
- Contribute data: [Guide](contributing/index.md)

## Funding

This work was supported by the National Institute of Biomedical Imaging and Bioengineering of the NIH under Award Number R01EB031166. The content is solely the responsibility of the authors and does not necessarily represent the official views of the NIH.
