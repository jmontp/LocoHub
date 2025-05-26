# University of Michigan 2021 Dataset Converter

This directory contains conversion scripts for the University of Michigan 2021 human lower-limb biomechanics dataset.

## Dataset Citation

Reznick, E.*, Embry, K.R.*, Neuman, R., Bolívar-Nieto, E., Fey, N.P. & Gregg, R.D. **Lower-limb kinematics and kinetics during continuously varying human locomotion**. Sci Data 8, 282 (2021). https://doi.org/10.1038/s41597-021-01057-9

[Link to publication](https://doi.org/10.1038/s41597-021-01057-9)

## Detailed Documentation

For comprehensive dataset information including structure, variables, and usage examples, see:
- 📖 [**University of Michigan 2021 Dataset Documentation**](../../../docs/datasets_documentation/dataset_umich_2021.md)

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
```

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

# UMich 2021 Dataset Conversion

This directory contains scripts to convert the University of Michigan 2021 locomotion dataset from its original MATLAB `.mat` format to standardized Parquet files following the locomotion data standardization specifications.

## Prerequisites

- MATLAB (tested with R2020b or newer)
- Python 3.7+ with the following packages:
  - pandas
  - numpy
  - pyarrow
  - argparse
  - subprocess
- The original dataset files:
  - `Streaming.mat` - Contains time-series locomotion data
  - `Normalized.mat` - Contains phase-normalized locomotion data

## Files Description

- `convert_umich_time_to_parquet.m` - Converts time-series data to standardized parquet format
- `convert_umich_phase_to_parquet.m` - Converts phase-normalized data to standardized parquet format
- `run_umich_conversion.py` - Python script to run both MATLAB conversion scripts and validate outputs
- `umich_2021_mat_structure.md` - Documentation of the original dataset's MATLAB structure

## Generated Output Files

The conversion scripts generate the following Parquet files:

1. `umich_2021_time.parquet` - Time-series locomotion data
2. `umich_2021_phase.parquet` - Phase-normalized locomotion data
3. `metadata_task_time.parquet` - Task/trial metadata for time-series data
4. `metadata_task_phase.parquet` - Task/trial metadata for phase-normalized data
5. `metadata_subject.parquet` - Subject demographic information

## How to Run

### Option 1: Using the Python Runner (Recommended)

```bash
python run_umich_conversion.py
```

This will:
1. Check if all required files are present
2. Run both MATLAB conversion scripts
3. Verify all output files were generated
4. Run visualization tools if available

#### Command-line Options

- `--no-vis`: Skip visualization step
- `--output-dir PATH`: Specify output directory for parquet files (default: current directory)

Example:
```bash
python run_umich_conversion.py --output-dir ../../data/umich_2021
```

### Option 2: Manual MATLAB Execution

1. Start MATLAB
2. Navigate to this directory
3. Run the conversion scripts:

```matlab
% For time-series conversion
run('convert_umich_time_to_parquet.m');

% For phase-normalized conversion
run('convert_umich_phase_to_parquet.m');
```

## Schema Information

The output Parquet files follow the standard schema defined in the repository's `docs/standard_spec` directory.

Key specifications:
- Subject IDs are prefixed with 'Umich_2021_'
- Time data is in seconds
- Phase data is normalized to 0-100%
- Angular measurements are in radians
- Forces are in Newtons
- Distances/positions are in meters
- Subject metadata includes demographics like age, gender, height, etc.

## Troubleshooting

- **Missing .mat files**: Ensure both `Streaming.mat` and `Normalized.mat` are in the current directory
- **MATLAB errors**: Check that your MATLAB installation includes the `parquetwrite` function
- **Memory issues**: Processing large .mat files may require substantial RAM; reduce other memory usage or increase MATLAB's memory allocation

## Data Source Notes

- The `Normalized.mat` file is used for generating the phase-based parquet file (`umich_2021_phase.parquet`).
- **Potential Missing Data in `Normalized.mat`**:
    - The `jointAngles` field (and its subfields like `HipAngles`, `KneeAngles`, `AnkleAngles`, `PelvisAngles`) may be missing for some `Run` and `Walk` trials for certain subjects.
    - The `Tread` (treadmill trial) data may be entirely missing for some subjects.
    - The `jointMoments` field (and its subfields) may also be missing for some trials.
    - Similarly, the `forceplates` field (and its subfields `Force`, `CoP`) may be missing for some trials.
- **Script Behavior for Missing Data**:
    - The `convert_umich_phase_to_parquet.m` script attempts to determine the number of strides for a trial first from `jointAngles.HipAngles`, and if not available, then from `forceplates.Force`.
    - If the number of strides cannot be determined (i.e., both essential fields are missing or empty), the trial is skipped, and a message is logged to the console.
    - If a trial is processed but specific data fields (e.g., `jointAngles`, `jointMoments`, or `forceplates`, or their sub-components) are missing or empty, the corresponding columns in the output `umich_2021_phase.parquet` file will be filled with `NaN` values. Warning messages will also be logged to the console indicating which data was missing for a given `task_id`.
    - All columns specified in the data standard are always included in the output table, even if they consist entirely of `NaNs` due to missing source data.

### Stair Data Specifics

- **`i0` Secondary Condition for Stairs**: For `Stair` tasks, secondary condition names like `i20`, `in20`, `i25`, `in25`, etc., are used to determine `task_name` as `up_stairs` (for `iXX`) or `down_stairs` (for `inXX`). The numeric part (e.g., 20, 25) indicates the staircase inclination in degrees.
- Based on dataset documentation and author feedback, `Stair` task conditions with a secondary condition of `i0` (which would imply a 0-degree stair incline) are treated as typos. 
- The conversion script (`convert_umich_phase_to_parquet.m` and `convert_umich_time_to_parquet.m`) assumes these `i0` conditions for `Stair` tasks actually represent `up_stairs` (ascent), likely intended to be a non-zero incline (e.g., `i20`). The `ground_inclination_deg` field for all stair tasks remains `NaN` as per the data standard, as this field is for global ground/ramp incline, not staircase incline.
- **`stair_inclination_deg` Field**: For tasks `up_stairs` and `down_stairs`, the `metadata_task_time.parquet` and `metadata_task_phase.parquet` files now include a `stair_inclination_deg` column. This column stores the inclination of the staircase in degrees. For conditions labeled 'i0' in the original data, this field is populated with 20 degrees, reflecting the assumption mentioned above. For other stair conditions like 'i20', 'i30', 'i40', the corresponding degree value (20, 30, 40) is used. The `step_height_m` field is also included for these tasks but populated with `NaN` as this information is not available in the source dataset.
