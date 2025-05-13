# Standard Specification

## Overview
This repository standardizes locomotion datasets into a consistent Parquet-based format, providing both **time-indexed** and **phase-indexed** tables. Supported modalities include:
- Joint Angles
- Joint Kinetics (moments, powers)
- Link (global) Angles
- Ground Reaction Forces (GRFs)
- Center of Pressure (COP)

Time-indexed tables preserve the source sampling frequency. Phase-indexed tables normalize each gait cycle to a fixed number of points for cross-subject comparison.

**Limitations:**
- Currently supports only the modalities listed above.
- Some datasets have missing right-leg data or incomplete segmentation; missing values are handled as NaN (see Section 9).
- Each Parquet file may contain multiple `task_id` entries. Time is generally **discontinuous** between tasks, especially at transition points. For continuous analysis within a task, it is recommended to filter by `task_id`.

## Contents
1. [File Format & Schema](#file-format--schema)
2. [Metadata Block](#metadata-block)
3. [Column Naming Convention](#column-naming-convention)
4. [Units & Conventions](units_and_conventions.md)
5. [Sign Conventions](sign_conventions.md)
6. [Temporal & Phase Indexing](#temporal--phase-indexing)
   - [6.1 Temporal Indexing](#temporal-indexing)
   - [6.2 Phase Calculation](phase_calculation.md)
7. [Task Vocabulary](#task-vocabulary)
8. [Coordinate Frames](#coordinate-frames)
9. [Missing Data & Quality Flags](#missing-data--quality-flags)

---

## 0. Variable Coverage

The standardized format includes both required and optional biomechanical variables:

- **Global Link Angles** (RECOMMENDED): orientation of torso, thigh, shank, and foot segments in global coordinates, following OpenSim's XYZ frame.
- **Joint Angles** (3DOF Schema):
  - Sagittal plane (required): `hip_flexion_angle_rad`, `knee_flexion_angle_rad`, `ankle_flexion_angle_rad`
  - Frontal/transverse planes (optional): `hip_adduction_angle_rad`, `hip_rotation_angle_rad`, `ankle_inversion_angle_rad`, `ankle_rotation_angle_rad`
- These optional fields should be included in the schema and populated as `NaN` where not available.

## 1. File Format & Schema
- **Format:** Apache Parquet
- **Filename convention:** `<dataset>_<time|phase>.parquet`
- **Schema:** Defined in `reference/schema_definition.json`
  - Time tables include `time_s` column
  - Phase tables include `phase_<r|l>%` column

## 2. Metadata Handling

To avoid row-level duplication of attributes:

- **metadata_subject.parquet**: a dimension table containing one row per `subject_id` with demographics and static subject info:
  - `subject_id`
  - Demographics: `age`, `gender`, `height`, `body_mass`, etc.

- **metadata_task.parquet**: a dimension table containing one row per `task_id` (or trial) with session/task-specific constants:
  - `subject_id`, `task_id`
  - Task parameters: `ground_inclination_deg`, `walking_speed_m_s`, any other protocol settings

- **Fact Tables** (`<dataset>_<time|phase>.parquet`): include only the foreign keys:
  - `subject_id`
  - `task_id`

Consumers join both dimension tables to the fact tables on these keys to reconstruct full records without redundant storage. For quick filtering by task parameters (e.g., walking_speed), see the How-To guide for an example merge snippet.

## 3. Column Naming Convention
- Use **snake_case** for all column names
- Append unit suffix for clarity: `_kg`, `_rad`, `_deg`, `_N`, `_m`, `_s.`
- Examples:
  - `hip_flexion_angle_rad`
  - `knee_moment_Nm`
  - `vertical_grf_N`
  - `cop_y_m`

## 6. Temporal & Phase Indexing
### 6.1 Temporal Indexing
- Column `time_s`: seconds, monotonic increasing within a task.
- Time is **discontinuous across task transitions** in a multi-task file.
- Sampling rate given by metadata `sampling_frequency_hz`.

### 6.2 Phase Calculation
See detailed algorithm in [phase_calculation.md](phase_calculation.md).

## 7. Task Vocabulary

Defined in `reference/task_vocabulary.csv`. Each `task_name` **must** be drawn from the following standardized list:

### Locomotion
- `level_walking`
- `incline_walking`
- `decline_walking`
- `run`
- `up_stairs`
- `down_stairs`

### Transitions
- `sit_to_stand`
- `stand_to_sit`
- `poses`

### Load-bearing Tasks
- `lift_weight`
- `push`
- `jump`
- `lunges`
- `squats`

### Object Interaction
- `ball_toss_l`
- `ball_toss_m`
- `ball_toss_r`

### Misc. 
- `meander`
- `cutting`
- `obstacle_walk`
- `side_shuffle`
- `curb_up`
- `curb_down`

Each row in the dataset must include a `task_id` and `task_name` that match one of these values. New tasks must be explicitly added to the controlled vocabulary and documented in the changelog.

## 8. Coordinate Frames

- **Global frame:** OpenSim convention — X-forward, Y-up, Z-right (right-handed)
- **Local link frames:** consistent per dataset and aligned with OpenSim's right-handed coordinate system. Visualize a person walking to the left, where the local axes should match OpenSim's conventions for limb segment orientation.

## 9. Missing Data & Quality Flags

- Missing values are `NaN`
- Outliers are flagged in boolean column `is_outlier`
