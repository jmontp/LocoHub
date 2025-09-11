---
title: Reference
---

# Reference

Concise, complete description of what’s in the standardized data.

## Data Formats

| Format | File Pattern | Index | Purpose |
|-------|--------------|-------|---------|
| Phase‑Indexed | `*_phase.parquet` | 150 samples, 0–100% | Cross‑subject comparisons, averaging |
| Time‑Indexed | `*_time.parquet` | Seconds | Event detection, raw analysis |

## Required Columns

| Column | Required | Meaning |
|--------|----------|---------|
| `subject` | Yes | Global unique ID (see Subject Naming) |
| `subject_metadata` | Optional | Demographics, key:value (e.g., `age:25,sex:M,height_m:1.75,weight_kg:70`) |
| `task` | Yes | Activity category (see Task Names) |
| `task_id` | Yes | Specific variant (see Task IDs) |
| `task_info` | Yes | Parameter string, key:value (see Task Metadata) |
| `step` | Yes | Cycle index within trial |
| `phase_ipsi` | Phase only | 0–100, phase of ipsilateral limb (heel‑strike to heel‑strike) |
| `time_s` | Time only | Seconds from trial start |

## Task Names, IDs, and Metadata

- Task names (`task`): base activities plus optional population/pathology suffixes.
  - Base: `level_walking`, `incline_walking`, `decline_walking`, `stair_ascent`, `stair_descent`, `run`, `jump`, `sit_to_stand`.
  - Pathology/population suffixes (optional): append `_<suffix>` to denote a special population for the whole task. Examples:
    - `level_walking_stroke`, `level_walking_pd`, `level_walking_sci`
    - `level_walking_tfa`, `level_walking_tta` (transfemoral/transtibial amputee)
    - `stair_ascent_tfa`, `incline_walking_cva`
  - Recommended suffix tokens: `stroke` (or `cva`), `pd`, `sci`, `tfa`, `tta`. Keep lower‑case snake_case.
- Task IDs (`task_id`): short variant labels, e.g., `level`, `incline_5deg`, `incline_10deg`, `decline_5deg`, `stair_ascent`, `stair_descent`.
- Task metadata (`task_info`): comma‑separated key:value pairs.

Common task_info keys

- `speed_m_s:<float>`
- `treadmill:<true|false>`
- `incline_deg:<int>` (positive uphill, negative downhill)
- `step_height_m:<float>` (stairs)
- `step_width_m:<float>` (stairs)
- `surface:<string>` (e.g., overground, treadmill)
- `footwear:<string>` (e.g., barefoot, shoe)
- `assistance:<string>` (e.g., none, handrail)

## Subject Naming

Format: `<DATASET_CODE>_<POPULATION_CODE><SUBJECT_NUMBER>` → `UM21_AB01`, `GT23_AB05`, `PROS_TFA03`.

Population codes

| Code | Population | Recommended task suffix |
|------|------------|-------------------------|
| AB | Able‑bodied | (omit) |
| TFA | Transfemoral amputee | `tfa` |
| TTA | Transtibial amputee | `tta` |
| CVA | Stroke | `stroke` or `cva` |
| PD | Parkinson’s | `pd` |
| SCI | Spinal cord injury | `sci` |
| CP | Cerebral palsy | `cp` |
| TKA | Total knee arthroplasty | `tka` |
| THA | Total hip arthroplasty | `tha` |
| MS | Multiple sclerosis | `ms` |


## Subject Metadata

Optional demographics and clinical context stored in `subject_metadata` as comma‑separated key:value pairs.

Common keys

- `age:<int>`
- `sex:<M|F|Other>`
- `height_m:<float>`
- `weight_kg:<float>`
- `leg_dominance:<left|right|unknown>`
- `impairment:<string>` (e.g., stroke, pd, sci)
- `prosthesis_type:<string>` (e.g., TFA, TTA)
- `prosthesis_side:<ipsi|contra|left|right>`
- `clinical_scores:<string>` (e.g., FuglMeyer:28)
- `notes:<string>` (short free text)

## Variables (What Columns Mean)

Naming pattern: `<joint/segment>_<motion>_<measurement>_<side>_<unit>`

Key categories

- Kinematics (angles): `*_angle_*_rad`
- Kinetics (moments/forces): `*_moment_*_Nm_kg` (mass-normalized)
- Ground reaction forces (GRF): `*_grf_*_BW` (body-weight-normalized)
- Segment orientations: `pelvis_*_angle_rad`, `trunk_*_angle_rad`, `thigh_*_angle_*_rad`, `shank_*_angle_*_rad`, `foot_*_angle_*_rad`

Sides

- `ipsi`: limb that defines phase (`phase_ipsi` is 0% at its heel strike)
- `contra`: opposite limb (≈ 50% phase offset in level walking)

Units

- Angles in radians (`*_rad`)
- Moments are mass‑normalized (`*_Nm_kg`)
- GRFs are body‑weight‑normalized (`*_BW`)

## Column Catalog

Complete list of standard column names used in the conversion scripts and examples. Columns are grouped by category; sides are `ipsi` and `contra` unless noted.

- Required schema: `subject`, `subject_metadata`, `task`, `task_id`, `task_info`, `step`, `phase_ipsi` (phase‑indexed) or `time_s` (time‑indexed)
- Optional schema: `phase_contra`, `dataset`, `collection_date`, `processing_date`

Kinematics — joint angles (radians)

- `hip_flexion_angle_{ipsi,contra}_rad`
- `hip_adduction_angle_{ipsi,contra}_rad`
- `knee_flexion_angle_{ipsi,contra}_rad`
- `ankle_dorsiflexion_angle_{ipsi,contra}_rad`

Kinetics — joint moments (Nm/kg)

- `hip_flexion_moment_{ipsi,contra}_Nm_kg`
- `knee_flexion_moment_{ipsi,contra}_Nm_kg`
- `ankle_dorsiflexion_moment_{ipsi,contra}_Nm_kg`

Segment/link orientations (radians)

- Pelvis: `pelvis_sagittal_angle_rad`, `pelvis_frontal_angle_rad`, `pelvis_transverse_angle_rad`
- Trunk: `trunk_sagittal_angle_rad`, `trunk_frontal_angle_rad`, `trunk_transverse_angle_rad`
- Thigh: `thigh_sagittal_angle_{ipsi,contra}_rad`
- Shank: `shank_sagittal_angle_{ipsi,contra}_rad`
- Foot: `foot_sagittal_angle_{ipsi,contra}_rad`

Angular velocities (radians/second)

- `hip_flexion_angular_velocity_{ipsi,contra}_rad_s`
- `knee_flexion_angular_velocity_{ipsi,contra}_rad_s`
- `ankle_dorsiflexion_angular_velocity_{ipsi,contra}_rad_s`

Ground reaction forces (BW)

- Vertical: `vertical_grf_{ipsi,contra}_BW`
- Anterior–posterior: `anterior_grf_{ipsi,contra}_BW`
- Medio–lateral: `lateral_grf_{ipsi,contra}_BW`

Center of pressure (meters)

- `cop_anterior_{ipsi,contra}_m`
- `cop_lateral_{ipsi,contra}_m`


## Coordinate & Sign Conventions

OpenSim right‑handed frames. Positive rotations follow right‑hand rule.

- Hip flexion (+): thigh forward; Knee flexion (+): heel toward buttocks
- Ankle dorsiflexion (+): toes up; Pelvis sagittal (+): anterior tilt

## Row & Phase/Time Semantics

- Each row = one sample within a step/cycle for a subject+task.
- Phase‑indexed: `phase_ipsi` runs 0→100% in each gait cycle of the ipsilateral limb (150 samples).
- Contra limb is approximately 50% offset in level walking.
- Time‑indexed: `time_s` increases monotonically; cycles delimited by gait events.

## GRF & CoP Variables

- GRF components: `vertical_grf_*`, `anterior_grf_*`, `lateral_grf_*` with suffix `_BW`.
- Center of pressure: `cop_anterior_*_m`, `cop_lateral_*_m` (meters), side‑specific where applicable.

## Naming Rules

- Lowercase snake_case; tokens separated by single underscores.
- Use exact unit suffix tokens: `rad`, `Nm_kg`, `BW`, `m`, `s`.
- Segment/global (no side): e.g., `pelvis_*_angle_rad`, `trunk_*_angle_rad`.
- Side tokens: `ipsi` or `contra` only.

## Optional Columns & Flags

- `phase_contra` (percent): contra limb phase, if present.
- `cycle_id`: optional alias of `step`.
- `dataset`: dataset identifier; `collection_date`, `processing_date` (ISO strings) if available.
- Quality flags (boolean): e.g., `is_reconstructed_<side>` for interpolated values.

Canonical phase column is `phase_ipsi`.


## Related

- Datasets overview: ../datasets/
- Validation ranges: ../datasets/validation_ranges.md
- Maintainers: ../maintainers/
