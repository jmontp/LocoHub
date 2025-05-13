**File: standard\_spec/task\_definitions.md**

````markdown
# Task Definitions & `metadata_task.parquet` Schema

This document provides explicit definitions for each column in the `metadata_task.parquet` file. Each row represents one unique task instance (identified by `task_id`) performed by a subject.

## Schema Overview
| Column Name                  | Data Type | Required | Description                                                                                         |
|------------------------------|-----------|----------|-----------------------------------------------------------------------------------------------------|
| `task_id`                    | string    | Yes      | Unique identifier for the task/trial (e.g., `S01_T03`)                                               |
| `subject_id`                 | string    | Yes      | Links to `metadata_subject.parquet` subject record                                                   |
| `task_name`                  | string    | Yes      | Standardized name of the task (see Controlled Vocabulary)                                            |
| `start_time_s`               | float     | No       | Relative time (in seconds) when the task begins within the raw recording                             |
| `end_time_s`                 | float     | No       | Relative time (in seconds) when the task ends within the raw recording                               |
| `ground_inclination_deg`     | float     | No       | Surface incline angle in degrees (positive = upward slope)                                           |
| `walking_speed_m_s`          | float     | No       | Nominal or target walking/running speed in meters/second                                             |
| `load_weight_kg`             | float     | No       | Weight lifted or carried during the task (if applicable)                                             |
| `treadmill_speed_m_s`        | float     | No       | Belt speed for treadmill tasks                                                                       |
| `path_length_m`              | float     | No       | Total distance covered during the task                                                                |
| `step_height_m`              | float     | No       | Vertical rise per step, relevant for stair tasks                                                    || `instructions`               | string    | No       | Any verbal or protocol instructions provided to the subject (free-text)                              |
| `notes`                      | string    | No       | Free-text notes about the task (e.g., "data trimmed due to artifact at end")                       |
| `source_marker_column`       | string    | No       | Original dataset column or event marker name for heel-strike (if used for phase calibration)         |
| `source_marker_frame_index`  | int       | No       | Frame index for a provided heel-strike marker                                                        |


## Field Details

- **`step_height_m`**: vertical rise of each step, typically used in `up_stairs` and `down_stairs` tasks. Units: meters.
- **`task_id`**: Prefer a structured format combining subject and trial, e.g. `S01_T03` for Subject 01, Task 03.
- **`task_name`**: Must match one of the entries in `reference/task_vocabulary.csv`.
- **Time Bounds (`start_time_s`, `end_time_s`)**: Used to extract continuous segments for each task; these may be omitted if segmentation is implicit in the fact table.
- **Task Parameters**:
  - `ground_inclination_deg`: slope of treadmill or ramp; positive values indicate an upward incline.
  - `walking_speed_m_s` / `treadmill_speed_m_s`: use exactly one when applicable; leave the other `NaN`.
  - `load_weight_kg`: relevant for load-bearing tasks (e.g., `lift_weight`).
- **Distance Metrics (`path_length_m`)**: total path length; useful for overground walking tasks.
- **Markers for Phase (`source_marker_*`)**: if the dataset includes explicit heel-strike events, store the original marker name or frame index; conversion pipelines may skip GRF-based detection.

## Usage Example
Load metadata and join in Python:

```python
import pandas as pd

# Read dimension and fact
meta_task = pd.read_parquet('metadata_task.parquet')
fact = pd.read_parquet('dataset_time.parquet')

# Merge on task_id
df = fact.merge(meta_task, on='task_id', how='left')
````

---

Please review and suggest any additional fields or clarifications needed for your task definitions."\`\`\`}
