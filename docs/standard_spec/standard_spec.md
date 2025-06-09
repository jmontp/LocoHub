# Standard Specification (with Monolithic Format Option)

## Overview

This repository standardizes locomotion datasets into a consistent Parquet-based format, providing both **time-indexed** and **phase-indexed** tables. Supported modalities include:

* Joint Angles
* Joint Kinetics (moments, powers)
* Link (global) Angles
* Ground Reaction Forces (GRFs)
* Center of Pressure (COP)

Time-indexed tables preserve the source sampling frequency. Phase-indexed tables normalize each gait cycle to a fixed number of points for cross-subject comparison.

**Limitations:**

* Currently supports only the modalities listed above.
* Some datasets have missing right-leg data or incomplete segmentation; missing values are handled as NaN (see Section 9).
* Each Parquet file may contain multiple `task_id` entries. Time is generally **discontinuous** between tasks, especially at transition points. For continuous analysis within a task, it is recommended to filter by `task_id`.

---

## Contents

1. [Variable Coverage](#variable-coverage)
2. [File Format & Schema](#file-format--schema)

   * [2.1 Normalized (Split) Format](#21-normalized-split-format)
   * [2.2 Monolithic Format](#22-monolithic-format)
3. [Metadata Handling](#metadata-handling)
4. [Column Naming Convention](#column-naming-convention)
5. [Units & Conventions](units_and_conventions.md)
6. [Sign Conventions](sign_conventions.md)
7. [Temporal & Phase Indexing](#temporal--phase-indexing)

   * [7.1 Temporal Indexing](#temporal-indexing)
   * [7.2 Phase Calculation](phase_calculation.md)
8. [Task Vocabulary](#task-vocabulary)
9. [Coordinate Frames](#coordinate-frames)
10. [Missing Data & Quality Flags](#missing-data--quality-flags)
11. [Monolithic Format: Usage Notes](#monolithic-format-usage-notes)
12. [Example: Export to Monolithic Format](#example-export-to-monolithic-format)
13. [Backward Compatibility](#backward-compatibility)
14. [Schema Declaration](#schema-declaration)
15. [Summary Table](#summary-table)

---

## 1. Variable Coverage

The standardized format includes both required and optional biomechanical variables:

* **Global Link Angles** (RECOMMENDED): orientation of torso, thigh, shank, and foot segments in global coordinates, following OpenSim's XYZ frame.
* **Joint Angles** (3DOF Schema):

  * Sagittal plane (required): `hip_flexion_angle_rad`, `knee_flexion_angle_rad`, `ankle_flexion_angle_rad`
  * Frontal/transverse planes (optional): `hip_adduction_angle_rad`, `hip_rotation_angle_rad`, `ankle_inversion_angle_rad`, `ankle_rotation_angle_rad`
* These optional fields should be included in the schema and populated as `NaN` where not available.

## 2. File Format & Schema

Two **organizational formats** are supported:

### 2.1 Normalized ("Split") Format (Recommended for Storage Efficiency)

* **Fact Table**: Main data (e.g., kinematics, kinetics) per sample with `subject_id` and `task_id` as foreign keys.
* **metadata\_subject.parquet**: Static subject info, one row per `subject_id`
* **metadata\_task.parquet**: Task/session info, one row per `task_id`
* **How to use**: Join fact table to metadata tables as needed.
* **Filename example**: `<dataset>_<time|phase>.parquet`

### 2.2 Monolithic Format (All Metadata In-Row)

* **Single Parquet file** with all columns, including:

  * All biomechanical data columns (joint angles, kinetics, etc.)
  * All relevant **subject-level metadata**: `age`, `gender`, `height`, `body_mass`, etc.
  * All **task-level metadata**: `task_id`, `task_name`, `walking_speed_m_s`, `ground_inclination_deg`, etc.
* Each data row contains the full set of metadata relevant to that row’s `subject_id` and `task_id`.
* **Filename example**: `<dataset>_<time|phase>_monolithic.parquet`
* **Storage note**: This approach **increases file size** (repetition of metadata), but simplifies downstream use (no joins needed).

#### 2.2.1 Example Schema (Monolithic Format)

| time\_s | subject\_id | age | gender | height | body\_mass | task\_id | task\_name     | walking\_speed\_m\_s | ... biomech data ... |
| ------- | ----------- | --- | ------ | ------ | ---------- | -------- | -------------- | -------------------- | -------------------- |
| 0.00    | S01         | 23  | male   | 1.78   | 72.1       | T001     | level\_walking | 1.25                 | ...                  |
| 0.01    | S01         | 23  | male   | 1.78   | 72.1       | T001     | level\_walking | 1.25                 | ...                  |

*Subject and task metadata are repeated for every row in the corresponding task.*

---

## 3. Metadata Handling

**Choose one of:**

* **Split/normalized format** for maximum storage efficiency (separate metadata and fact tables, use foreign keys for join).
* **Monolithic/denormalized format** for convenience (all metadata embedded in each row).

**Consumers should check the schema** to detect which format is present:

* If `age`, `gender`, etc., are columns in the data table, it is monolithic.
* If only `subject_id`, `task_id` present, use external metadata tables.

---

## 4. Column Naming Convention

* Use **snake\_case** for all column names
* Append unit suffix for clarity: `_kg`, `_rad`, `_deg`, `_N`, `_m`, `_s.`
* Examples:

  * `hip_flexion_angle_rad`
  * `knee_moment_Nm`
  * `vertical_grf_N`
  * `cop_y_m`

---

## 5. Units & Conventions

See [units\_and\_conventions.md](units_and_conventions.md)

---

## 6. Sign Conventions

See [sign\_conventions.md](sign_conventions.md)

**Key**: All joint angles follow **OpenSim conventions** for maximum compatibility with biomechanical modeling frameworks.

---

## 7. Temporal & Phase Indexing

### 7.1 Temporal Indexing

* Column `time_s`: seconds, monotonic increasing within a task.
* Time is **discontinuous across task transitions** in a multi-task file.
* Sampling rate given by metadata `sampling_frequency_hz`.

### 7.2 Phase Calculation

See detailed algorithm in [phase\_calculation.md](phase_calculation.md).

---

## 8. Task Vocabulary

Defined in `reference/task_vocabulary.csv`. Each `task_name` **must** be drawn from the following standardized list:

### Locomotion

* `level_walking`
* `incline_walking`
* `decline_walking`
* `run`
* `up_stairs`
* `down_stairs`

### Transitions

* `sit_to_stand`
* `stand_to_sit`
* `poses`

### Load-bearing Tasks

* `lift_weight`
* `push`
* `jump`
* `lunges`
* `squats`

### Object Interaction

* `ball_toss_l`
* `ball_toss_m`
* `ball_toss_r`

### Misc.

* `meander`
* `cutting`
* `obstacle_walk`
* `side_shuffle`
* `curb_up`
* `curb_down`

Each row in the dataset must include a `task_id` and `task_name` that match one of these values. New tasks must be explicitly added to the controlled vocabulary and documented in the changelog.

---

## 9. Coordinate Frames

* **Global frame:** OpenSim convention — X-forward, Y-up, Z-right (right-handed)
* **Local link frames:** consistent per dataset and aligned with OpenSim's right-handed coordinate system. Visualize a person walking to the left, where the local axes should match OpenSim's conventions for limb segment orientation.

---

## 10. Missing Data & Quality Flags

* Missing values are `NaN`
* Outliers are flagged in boolean column `is_outlier`

---

## 11. Monolithic Format: Usage Notes

* Use when:

  * Data consumers prioritize ease of analysis (e.g., for scikit-learn, pandas, Excel).
  * Data is being shared for end-users who may not be comfortable with database-style joins.
  * Storage footprint is not a primary concern.

* Avoid if:

  * The dataset is very large and storage/bandwidth is critical.
  * Multiple tasks and subjects result in highly repetitive metadata.

* **When exporting** to monolithic format, merge metadata tables into the main data table using left-joins on `subject_id` and `task_id`, then export to a single Parquet file.

---

## 12. Example: Export to Monolithic Format in Python

```python
import pandas as pd

fact = pd.read_parquet('dataset_time.parquet')
meta_subj = pd.read_parquet('metadata_subject.parquet')
meta_task = pd.read_parquet('metadata_task.parquet')

# Merge in subject metadata
out = fact.merge(meta_subj, on='subject_id', how='left')
# Merge in task metadata
out = out.merge(meta_task, on=['subject_id', 'task_id'], how='left')

out.to_parquet('dataset_time_monolithic.parquet')
```

---

## 13. Backward Compatibility

* Both formats must match the **column naming conventions**, **units**, and **controlled vocabulary**.
* Scripts and code examples should indicate if they require monolithic format.

---

## 14. Schema Declaration

**In each dataset README,** specify whether data is provided in normalized (split) or monolithic format (or both), and how to load each.

---

## 15. Summary Table

| Format     | Structure                                | Pros                       | Cons                     |
| ---------- | ---------------------------------------- | -------------------------- | ------------------------ |
| Split      | Fact + Metadata tables, use keys to join | Storage efficient, modular | Requires join            |
| Monolithic | One table, all metadata per row          | Simple, join-free analysis | Larger files, redundancy |

---
