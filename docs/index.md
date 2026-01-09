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
| Dataset | Tasks | Documentation | Phase (Clean) | Phase | Time |
|---------|-------|---------------|---------------|-------|------|
| Carter 2023 | Level Walking, Run | <a class="md-button md-button--primary" href="datasets/ca23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/w39ow0zyumsuy5h97d6ji/Carter2023_phase.parquet?rlkey=ce6ivefjv2mjlr220gi29akzg&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/o8vihgaafvdgeh9rc8mrt/Carter2023_time.parquet?rlkey=4t5ebkso47hq549p8rwpcvhz1&dl=0">Download</a> |
| Falisse 2016 | Level Walking | <a class="md-button md-button--primary" href="datasets/fa16/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/wfhx2r7dvfq488r7bobgf/Falisse2016_phase.parquet?rlkey=0wevpipyw7o1s8esh37i6u0z3&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/0dit0pa5xtdiufvsqxey8/Falisse2016_time.parquet?rlkey=0tx3j7n6xi3sxcr3kl6b7wdx0&dl=0">Download</a> |
| Fregly 2012 | Dynamic Walk, Level Walking | <a class="md-button md-button--primary" href="datasets/fr12/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/1juam1mcd1k6rdydcs14l/Fregly2012_phase.parquet?rlkey=5bgk857m5o5df3mvi9rauvpx4&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/30yy5vhnsr2ka6ctjnhjn/Fregly2012_time.parquet?rlkey=xehsvxwcjay7fphja73eklb0g&dl=0">Download</a> |
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | <a class="md-button md-button--primary" href="datasets/gt24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2021 | Level Walking, Stair Ascent, Stair Descent, Transition | <a class="md-button md-button--primary" href="datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=0">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | <a class="md-button md-button--primary" href="datasets/gt23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vd24hcu6yo55qya0t0xmx/gtech_2023_phase_raw.parquet?rlkey=gdwjf6km2xc8mn92mvh495ubc&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Hamner 2013 | Run | <a class="md-button md-button--primary" href="datasets/ha13/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/j6m9cq9eayebpnu1bvuyr/Hamner2013_phase.parquet?rlkey=eunj072xaizyf2gs8wxh04hbg&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/t51xh652f8v07olcfel1x/Hamner2013_time.parquet?rlkey=hgvulr5esgzb4dowpy9calfnx&dl=0">Download</a> |
| Han 2023 (GroundLink) | Jump, Level Walking | <a class="md-button md-button--primary" href="datasets/ha23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/1chsrssvvyewhqje7ofbt/Han2023_phase.parquet?rlkey=ysluyovs3qofdkj3h7w5wl3n0&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vqsb9e2si12d14dgu6cso/Han2023_time.parquet?rlkey=5hk6moxc3kdp71595x8tytuwr&dl=0">Download</a> |
| MBLUE Ankle Exoskeleton Study | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | <a class="md-button md-button--primary" href="datasets/mb24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/6xr64078wfvsxee4xfz7v/mblue_ankle_phase.parquet?rlkey=owrklzpaonrkgdhly74u2thr6&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Moore 2015 | Level Walking | <a class="md-button md-button--primary" href="datasets/mo15/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/61asnr4ilj7u31ijhdf08/Moore2015_phase.parquet?rlkey=lqwog90fpji77kbwsez5kkef9&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dranutsq3gzsclquuybmw/Moore2015_time.parquet?rlkey=ztjocfg1djqskatqr8sxlpq50&dl=0">Download</a> |
| Tan 2021 | Run | <a class="md-button md-button--primary" href="datasets/ta21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/0bruspclw3p76lxc68ndz/Tan2021_phase.parquet?rlkey=otswnntxbbe696pcg52380ad7&dl=0">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=0">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/ofvynp9s4x34e3jrhgau8/Tan2021_time.parquet?rlkey=bwj72e17t5s0vvskxp66bp20e&dl=0">Download</a> |
| Tan 2022 | Dynamic Walk | <a class="md-button md-button--primary" href="datasets/ta22/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/1sy2ytdybptl68pceazo7/Tan2022_phase.parquet?rlkey=frivulvhnyvp2y2k3mhxfargu&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/t3ck317o5hfwyfl33z5u2/Tan2022_time.parquet?rlkey=givu3fqupobe3n6hb5g8lhwsb&dl=0">Download</a> |
| Tiziana 2019 (Lencioni) | Level Walking | <a class="md-button md-button--primary" href="datasets/ti19/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/4th0yvoffqhj0tv79ljap/Tiziana2019_phase.parquet?rlkey=kt1z8kqesipv5ew37gf2btlld&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/zdwefhcckbwar78w731lu/Tiziana2019_time.parquet?rlkey=qkk9dlsrhuhvr4k9cj3excmis&dl=0">Download</a> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | <a class="md-button md-button--primary" href="datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/q37ioia7zmpkxqtw5dtw6/umich_2021_phase_clean.parquet?rlkey=j9cgoam6nz7mwtadcacqff3rn&dl=0">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dpk4wgtger1ktdoqrlxbr/umich_2021_phase_dirty.parquet?rlkey=rrjtx05woy1fd1du6oguai6x0&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> |
| UMich 2024 (Knee Exoskeleton) | Decline Walking, Incline Walking, Level Walking, Squat, Stair Ascent, Stair Descent | <a class="md-button md-button--primary" href="datasets/um24k/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/modvp9vqkzn3ezsgvmtxe/umich_2024_knee_exo_phase.parquet?rlkey=8ipitw8y88t7cdf7jblrd36h2&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| van der Zee 2022 | Level Walking | <a class="md-button md-button--primary" href="datasets/vz22/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/aoigw5td9wagxgjbntp9h/vanderZee2022_phase.parquet?rlkey=wtxg0zfzqlay96km7ou27eiz1&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/olbhe0u43m822uq4sy0yj/vanderZee2022_time.parquet?rlkey=hft8ro74ro7h496xbl7md3dwb&dl=0">Download</a> |
| Wang 2023 | Jump, Level Walking, Lunge, Run | <a class="md-button md-button--primary" href="datasets/wa23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/k1sl9uvikaqp41h2wdp8f/Wang2023_phase.parquet?rlkey=l9rkpdhdwyw81yk1h2olaizi5&dl=0">Download</a> | <span class="md-button md-button--disabled">—</span> | <a class="md-button" href="https://www.dropbox.com/scl/fi/g3tfjcmxnzy0mrsrqczxw/Wang2023_time.parquet?rlkey=l1oguxyizffwrgi8qw9w6ktzd&dl=0">Download</a> |
<!-- DATASET_TABLE_END -->

More details and validation reports: [Datasets Reference](datasets/index.md).

## Learn and Contribute

- Tutorials: [Start here](tutorials/index.md)
- API: [Overview](api/api-index.md)
- Contribute data: [Guide](contributing/index.md)

## Funding

This work was supported by the National Institute of Biomedical Imaging and Bioengineering of the NIH under Award Number R01EB031166. The content is solely the responsibility of the authors and does not necessarily represent the official views of the NIH.
