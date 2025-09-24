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

## Task Definitions

The table below supplements the naming rules with high-level guidance for each standard task. All phase-indexed datasets use 150 samples per cycle. Unless otherwise noted, `phase_ipsi` is 0% at ipsilateral heel strike and 100% at the next ipsilateral heel strike.

### level_walking

- **Activity Summary**: Comfortable-speed overground/treadmill walking on level surface.
- **Phase Definition**: 0% ipsilateral heel strike, 50% contralateral heel strike, 100% next ipsilateral heel strike.
- **Key Events**: HS (0%), Contralateral HS (50%), Toe-offs near 60%/10%.
- **Typical `task_id`**: `level`, `level_fast`, `level_slow`.
- **Common `task_info` keys**: `speed_m_s`, `treadmill`, `surface`.
- **Validation Notes**: Expect symmetric sagittal kinematics; large pelvis/trunk offsets usually indicate coordinate issues.

### incline_walking

- **Activity Summary**: Uphill walking on ramps or treadmills at constant grade.
- **Phase Definition**: Same as level walking (HS-to-HS).
- **Key Events**: Ipsilateral HS (0%), contralateral HS (≈50%), toe-off events shifted earlier due to incline.
- **Typical `task_id`**: `incline_5deg`, `incline_10deg`.
- **Common `task_info` keys**: `incline_deg` (positive), `speed_m_s`, `assistance` (e.g., handrail).
- **Validation Notes**: Expect increased hip/knee flexion and ankle dorsiflexion; check for forward trunk lean consistency.

### decline_walking

- **Activity Summary**: Downhill walking on ramps or treadmills at constant grade.
- **Phase Definition**: HS-to-HS as above.
- **Key Events**: Ipsilateral HS (0%), contralateral HS (≈50%), toe-off events often delayed relative to level.
- **Typical `task_id`**: `decline_5deg`, `decline_10deg` (negative grade).
- **Common `task_info` keys**: `incline_deg` (negative value), `speed_m_s`.
- **Validation Notes**: Expect increased knee flexion moments eccentrically; vertical GRF peaks may exceed level walking.

### stair_ascent

- **Activity Summary**: Ascending standard stairs at self-selected speed.
- **Phase Definition**: 0% ipsilateral foot initial contact on a step; 100% next ipsilateral contact on subsequent step.
- **Key Events**: Initial contact (0%), contralateral contact (≈50%), ipsilateral push-off (≈60%).
- **Typical `task_id`**: `stair_ascent`, `stair_ascent_depth20cm`.
- **Common `task_info` keys**: `step_height_m`, `step_width_m`, `handrail`.
- **Validation Notes**: Monitor hip/knee flexion angles (>90° typical); GRF may include handrail load if captured.

### stair_descent

- **Activity Summary**: Descending stairs at controlled speed.
- **Phase Definition**: Same as stair ascent: ipsilateral contacts define 0%/100%.
- **Key Events**: Initial contact on upper step (0%), contralateral contact (≈50%), ipsilateral loading on lower step (≈60%).
- **Typical `task_id`**: `stair_descent`, `stair_descent_depth20cm`.
- **Common `task_info` keys**: `step_height_m`, `handrail`.
- **Validation Notes**: Expect larger eccentric quadriceps moments; verify trunk remains upright around mid-step.

### run

- **Activity Summary**: Running/jogging at targeted speed on level surface.
- **Phase Definition**: 0% ipsilateral foot contact, 100% next ipsilateral contact (includes aerial phases).
- **Key Events**: Initial contact (0%), mid-stance (~25%), toe-off (~40%), contralateral contact (~50%), flight periods near mid-cycle.
- **Typical `task_id`**: `run_2_5_m_s`, `run_3_0_m_s`.
- **Common `task_info` keys**: `speed_m_s`, `treadmill`, `surface`, `footwear`.
- **Validation Notes**: Two vertical GRF peaks and zero-load intervals (flight) should appear; check for extreme pelvis rotations.

### sit_to_stand (cyclic)

- **Activity Summary**: Sit-to-stand-to-sit sequence captured as one 150-point cycle for consistency with phase indexing.
- **Phase Definition**:
  - 0%: Seated start, trunk flexion initiated.
  - 25%: Seat-off (center of mass leaving chair).
  - 50%: Full standing (hips/knees extended).
  - 75%: Controlled descent.
  - 100%: Reseated (back to initial posture).
- **Key Events**: Seat-off (~25%), peak extension (~50%), seat-contact (~90-100%).
- **Typical `task_id`**: `sit_to_stand_to_sit`.
- **Common `task_info` keys**: `seat_height_m`, `arm_support` (none, hands_on_thighs, handrails).
- **Validation Notes**: Expect asymmetrical GRFs if arm support used. Clarify in documentation that the dataset encodes both directions in a single cycle to maintain cyclicity.

> **Note:** If a study requires separate segments (e.g., standalone stand-to-sit trials), store them as independent tasks with explicit phase definitions, but the standard dataset format assumes the combined cycle above.

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
