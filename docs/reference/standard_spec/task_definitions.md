# Task Definitions

Standardized task vocabulary and metadata structure for locomotion datasets.

## Standard Task Names

**Walking Tasks**:
- `level_walking` - Walking on level ground
- `incline_walking` - Walking uphill (positive incline)
- `decline_walking` - Walking downhill (negative incline)
- `treadmill_walking` - Treadmill walking

**Stair Tasks**:
- `up_stairs` - Stair ascent
- `down_stairs` - Stair descent

**Dynamic Tasks**:
- `run` - Running or jogging
- `jump` - Jumping motion
- `hop` - Single-leg hopping

**Functional Tasks**:
- `sit_to_stand` - Chair rise
- `squats` - Squatting motion
- `lunges` - Lunge exercise

## Task Metadata Schema

**Required Fields**:
- `task_id` - Unique task identifier (e.g., `SUB01_T01`)
- `subject` - Subject identifier
- `task` - Standardized task name

**Optional Parameters**:
- `ground_inclination_deg` - Surface angle (degrees)
- `walking_speed_m_s` - Target speed (m/s)
- `step_height_m` - Step height for stairs (meters)
- `load_weight_kg` - Carried weight (kg)


## Field Details

- **`step_height_m`**: vertical rise of each step, typically used in `up_stairs` and `down_stairs` tasks. Units: meters.
- **`stair_inclination_deg`**: inclination of the staircase itself in degrees. Can be positive for both ascent and descent if describing the physical characteristic of the stairs. Relevant for `up_stairs` and `down_stairs` tasks. Units: degrees.
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
