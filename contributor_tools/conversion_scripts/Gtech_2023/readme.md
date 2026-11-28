# Georgia Tech 2023 Dataset Converter

This directory contains conversion scripts for the Georgia Tech 2023 human lower-limb biomechanics dataset.

## Dataset Citation

Scherpereel, K., Molinaro, D., Inan, O. et al. **A human lower-limb biomechanics and wearable sensors dataset during cyclic and non-cyclic activities**. Sci Data 10, 924 (2023). https://doi.org/10.1038/s41597-023-02840-6

[Link to publication](https://www.nature.com/articles/s41597-023-02840-6)

## Detailed Documentation

For comprehensive dataset information including structure, variables, and usage examples, see:
- 📖 [**Georgia Tech 2023 Dataset Documentation**](../../../docs/datasets_documentation/dataset_gtech_2023.md)

## Downloading the Data

1. Visit the Georgia Tech SmartTech repository: https://repository.gatech.edu/entities/publication/20860ffb-71fd-4049-a033-cd0ff308339e
2. Download the following files:
   - **RawDataset.zip** (for time-indexed conversion)
   - **ProcessedData_Standard_Gtech.zip** (for phase-indexed conversion)
3. Extract the downloaded files to the expected directory structure below

## Expected File Structure

The converters consume the raw dataset in this layout (point them at its root via
`GTECH2023_DATA_ROOT`; it does **not** need to sit inside the repo):

```
<GTECH2023_DATA_ROOT>/
├── RawData/
│   ├── AB01/
│   │   ├── CSV_Data/
│   │   │   ├── normal_walk_1/
│   │   │   │   ├── Joint_Angle.csv        # OpenSim IK angles (deg)
│   │   │   │   ├── Joint_Velocities.csv   # deg/s
│   │   │   │   ├── Joint_Moments.csv      # Nm/kg (mass-normalized)
│   │   │   │   ├── Link_Angle.csv         # segment angles (deg), see note
│   │   │   │   └── GroundFrame_GRFs.csv   # GRF + CoP (N, m)
│   │   │   ├── incline_walk_1/  ...
│   │   │   └── ...
│   │   └── Transforms/
│   │       └── <activity>.mat             # 4x4 calcn_l/calcn_r per timestamp (CoP frame)
│   ├── AB02/ ...
│   └── Subject_masses.csv                 # subject_id, mass_kg
└── Segmentation/
    ├── AB01/
    │   ├── normal_walk_1_1-2_parsing.mat  # heel-strike step intervals per sub-activity
    │   └── ...
    └── AB02/ ...
```

Notes:
- A single `CSV_Data/<activity>/` folder holds **all** sub-activities of a trial
  (e.g. every walking speed). The sub-activity label (speed, incline, load) lives in
  the `*_parsing.mat` **filename**, not the folder name — both converters iterate the
  parsing files to recover it.
- `Link_Angle.csv` / `Link_Velocities.csv` are segment angles in **degrees**, generated
  from the rotation matrices by `utilities/convert_gtech_rotm_to_eul_csv.m`
  (`rotm2eul(...,'YZX')` → Z=sagittal, X=frontal, Y=transverse). The `Transforms_Euler`
  folder is deliberately not used (it is in radians).

## Entry Points for Conversion

### 1. Time-Indexed Dataset Generation (recommended: `convert_gtech_2023_time_to_parquet.m`)

Continuous, native-resolution export. Each labeled sub-activity becomes one time window
with `time_s` reset to 0 and a single coarse `step`. Bounded memory: one parquet shard
per subject, streamed into the final file with 65,536-row groups.

```matlab
% In MATLAB (run from anywhere; the script finds its own helpers):
setenv('GTECH2023_DATA_ROOT', 'S:\path\to\Gtech_2023')  % contains RawData/ and Segmentation/
setenv('LOCOHUB_PYTHON', 'wsl.exe python3')             % interpreter with pyarrow for the shard merge
% setenv('GTECH2023_SUBJECT', 'AB01')                   % optional: single subject
run('convert_gtech_2023_time_to_parquet.m')

% Output: converted_datasets/gtech_2023_time.parquet
```

> The legacy `convert_gtech_all_to_parquet.py` predates the current standard
> (raw Newtons, left/right instead of ipsi/contra, no segment reconstruction,
> `step=0`, in-memory accumulation) and is kept only for reference. Use the MATLAB
> converter above.

### 2. Phase-Indexed Dataset Generation

```matlab
% In MATLAB, navigate to this directory and run:
convert_gtech_phase_to_parquet

% Output: converted_datasets/gtech_2023_phase_raw.parquet
```

The time and phase converters share dataset conventions (see below) so their exports
agree signal-for-signal.

## Scripts Overview

### Main Conversion Scripts
- **convert_gtech_2023_time_to_parquet.m** — Time-indexed converter (current standard)
- **convert_gtech_phase_to_parquet.m** — Phase-indexed converter (150 pts/cycle)
- **parse_gtech_activity_matlab.m** — Activity → (task, task_id, task_info) mapping, shared by both
- **convert_gtech_all_to_parquet.py** — Legacy time-indexed converter (deprecated)

### Utilities Folder
- **convert_gtech_rotm_to_eul_csv.m** — Generate `Link_Angle.csv` segment angles from rotation matrices (run first if absent)
- **benchmark_processing.m** — Performance benchmarking
- **plot_leg_alignment.m** — Visualization of leg alignment
- **test_parquet_conversion.m** — Test script for parquet conversion
- **verify_gtech_data.ipynb** — Data verification notebook

## Conventions (both exports)

Standardized to the LocoHub reference frame:
- **Joint angles/velocities/moments** read directly from the OpenSim IK/ID CSVs (not
  reconstructed from a kinematic chain). deg→rad; deg/s→rad/s. Knee angle/velocity/moment
  negated; **ankle left as-is** — the raw OpenSim ankle already follows the standard
  `ankle_dorsiflexion = foot − shank` (dorsiflexion positive) and the ankle moment is
  likewise already correct, so neither is flipped. Hip untouched; pelvis transverse +π/2
  frame offset. Moments are already Nm/kg → renamed only.
- **Segment angles** from `Link_Angle.csv`, Z=sagittal / X=frontal / Y=transverse.
- **GRF**: ForceX→anterior, ForceY_Vertical→vertical, ForceZ→lateral; normalized by body
  weight (`mass·9.81`) → `_BW`.
- **CoP**: transformed into the local calcn (ankle) frame; anterior = local x, lateral =
  local z, vertical = 0. In the time export, CoP is masked to NaN whenever the limb is
  unloaded (vertical GRF < 0.2 BW) or the transformed CoP is non-physical for the ankle
  frame (> 0.5 m away), since off-contact and boundary-transient force-plate CoP is
  meaningless.
- **Sides**: ipsi/contra. The time export sets the reference (ipsi) leg from the leading
  heel strike per window (`reference_leg` column); the phase export uses the leading leg
  at phase 0.

Regression tests: `tests/test_gtech_2023_time_conventions.py`.

## Processing Details

### Time-Indexed Data
- **Sampling rate**: native grid (~200 Hz), recorded per row in `sampling_rate_hz`.
- **Segmentation**: sub-activity labels (walking speeds, incline angles, loads) **are**
  preserved via the parsing-file names; `step` is one coarse id per labeled window.

### Phase-Indexed Data
- **Points per cycle**: 150
- **Phase synchronization**:
  - When true: Both legs start at phase 0
  - When false: One leg has 50% phase offset for temporal alignment
- **Note**: Some right leg data missing due to hardware issues with force plate collection

## Task Naming Conventions

Mapping is performed by `parse_gtech_activity_matlab.m`. Examples:
- `normal_walk` → `level_walking`
- `incline_walk up<N>` → `incline_walking` (`incline_<N>deg`)
- `incline_walk down<N>` → `decline_walking` (`decline_<N>deg`)
- `stairs up` → `stair_ascent`
- `stairs down` → `stair_descent`
- `curb_up`/`step_ups` → `step_up`; `curb_down` → `step_down`
- `sit_to_stand` / `stand_to_sit`, `squats` → `squat`, `jump`, `cutting`
- `dynamic_walk`/`lunges`/`side_shuffle`/`tire_run`/`turn_and_step` → `agility_drill`
