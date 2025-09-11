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

- Task names (`task`): `level_walking`, `incline_walking`, `decline_walking`, `stair_ascent`, `stair_descent`, `run`, `jump`, `sit_to_stand`.
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

| Code | Population |
|------|------------|
| AB | Able‑bodied |
| TFA | Transfemoral amputee |
| TTA | Transtibial amputee |
| CVA | Stroke |
| PD | Parkinson’s |
| SCI | Spinal cord injury |

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
- Kinetics (moments/forces): `*_moment_*_Nm`, `*_moment_*_Nm_kg`
- Ground reaction forces (GRF): `*_grf_*_N`, `*_grf_*_BW`
- Segment orientations: `pelvis_*_angle_rad`, `trunk_*_angle_rad`, `thigh_*_angle_*_rad`, `shank_*_angle_*_rad`, `foot_*_angle_*_rad`

Sides

- `ipsi`: limb that defines phase (`phase_ipsi` is 0% at its heel strike)
- `contra`: opposite limb (≈ 50% phase offset in level walking)

Units

- Angles in radians (`*_rad`)
- Moments in Newton‑meters (`*_Nm`) or mass‑normalized (`*_Nm_kg`)
- GRFs in Newtons (`*_N`) or body‑weight‑normalized (`*_BW`)

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

- GRF components: `vertical_grf_*`, `anterior_grf_*`, `lateral_grf_*` with suffix `_N` or `_BW`.
- Center of pressure: `cop_anterior_*_m`, `cop_lateral_*_m` (meters), side‑specific where applicable.

## Naming Rules

- Lowercase snake_case; tokens separated by single underscores.
- Use exact unit suffix tokens: `rad`, `Nm`, `Nm_kg`, `N`, `BW`, `m`, `s`.
- Segment/global (no side): e.g., `pelvis_*_angle_rad`, `trunk_*_angle_rad`.
- Side tokens: `ipsi` or `contra` only.

## Optional Columns & Flags

- `phase_contra` (percent): contra limb phase, if present.
- `cycle_id`: optional alias of `step`.
- `dataset`: dataset identifier; `collection_date`, `processing_date` (ISO strings) if available.
- Quality flags (boolean): e.g., `is_reconstructed_<side>` for interpolated values.

Canonical phase column is `phase_ipsi`.

Note: Validation procedures, ranges, and reports are documented in the Datasets section; this page focuses on the standard itself.

## Related

- Datasets overview: ../datasets/
- Validation ranges: ../datasets/validation_ranges.md
- Maintainers: ../maintainers/
