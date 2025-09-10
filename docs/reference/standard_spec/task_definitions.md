# Task Definitions

Comprehensive guide to the three-level task classification system for locomotion datasets.

## Quick Navigation

**Walking Tasks**: [Level](#level-walking) • [Incline](#incline-walking) • [Decline](#decline-walking)  
**Stair Tasks**: [Ascent](#stair-ascent) • [Descent](#stair-descent)  
**Dynamic Tasks**: [Running](#running) • [Jumping](#jumping)  
**Functional Tasks**: [Sit to Stand](#sit-to-stand) • [Squats](#squats)

## Three-Level Task Classification System

Our data standard uses a hierarchical system to organize task information across three required columns:

1. **`task`** - Biomechanical category for grouping similar activities
2. **`task_id`** - Specific variant with primary distinguishing parameter  
3. **`task_info`** - Detailed metadata in parseable key:value format

This system enables:
- Efficient filtering by biomechanical category (`task`)
- Quick selection of specific conditions (`task_id`)
- Access to detailed experimental parameters (`task_info`)

**Design Note**: The primary parameter (e.g., incline angle) appears in both `task_id` and `task_info`. This intentional redundancy serves different purposes:
- `task_id` enables fast filtering and grouping without parsing
- `task_info` provides complete metadata in a consistent parseable format
- This allows queries like "all 10° inclines" using task_id OR "all inclines between 5-15°" by parsing task_info

## Data Storage Format

### Column Requirements

All phase-indexed and time-indexed datasets must include these columns:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `task` | string | Biomechanical category | `"incline_walking"` |
| `task_id` | string | Primary variant identifier | `"incline_10deg"` |
| `task_info` | string | Metadata in key:value format | `"incline_deg:10,speed_m_s:1.2"` |

### Task Info Format Specification

**Format**: `"key1:value1,key2:value2,key3:value3"`

**Rules**:
- Keys contain units in the name (e.g., `speed_m_s` not `speed`)
- Values are primitives only (float, int, boolean, string)
- No spaces around colons or commas
- Boolean values: `true` or `false` (lowercase)
- Missing values: omit the key entirely

**Type Conversion**:
- Numbers without decimals → integer
- Numbers with decimals → float  
- `true`/`false` → boolean
- Everything else → string

## Task Reference

Complete documentation for each standardized task type.

### Quick Reference Table

| Task | Task ID Examples | Primary Use |
|------|-----------------|-------------|
| `level_walking` | `level` | Baseline gait analysis |
| `incline_walking` | `incline_5deg`, `incline_10deg` | Uphill locomotion |
| `decline_walking` | `decline_5deg`, `decline_10deg` | Downhill locomotion |
| `stair_ascent` | `stair_ascent` | Stair climbing analysis |
| `stair_descent` | `stair_descent` | Stair descent analysis |
| `run` | `run` | Running gait |
| `jump` | `jump` | Jumping mechanics |
| `sit_to_stand` | `sit_to_stand` | Functional mobility |
| `squats` | `squats` | Exercise analysis |

---

### Level Walking

**Description**: Walking on level ground (0° incline)

**Task**: `level_walking`  
**Task ID**: `level`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `speed_m_s` | float | Walking speed in m/s | 0.8 - 1.8 |
| `treadmill` | boolean | Treadmill vs overground | true/false |
| `self_selected` | boolean | Self-selected pace | true/false |
| `steady_state` | boolean | Constant speed vs changing | true/false |
| `acceleration_phase` | string | Speed change direction | "accelerating", "decelerating" |
| `initial_speed_m_s` | float | Starting speed (non-steady) | 0.5 - 2.0 |
| `final_speed_m_s` | float | Ending speed (non-steady) | 0.5 - 2.0 |
| `gait_transition` | boolean | Contains gait transitions | true/false |
| `transition_type` | string | Type of transition | "walk_to_run", "run_to_walk" |

**Examples**: 
- Standard: `"speed_m_s:1.2,treadmill:true"`
- Acceleration: `"steady_state:false,acceleration_phase:accelerating,initial_speed_m_s:1.0,final_speed_m_s:1.8"`
- Walk-to-run: `"gait_transition:true,transition_type:walk_to_run,initial_speed_m_s:1.5,final_speed_m_s:2.5"`

*Note: When `treadmill:false`, overground walking is implied.*

---

### Incline Walking

**Description**: Walking uphill on positive incline

**Task**: `incline_walking`  
**Task ID**: `incline_5deg`, `incline_10deg`, `incline_15deg`, etc.

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `incline_deg` | float | Incline angle (positive) | 5, 10, 15 |
| `speed_m_s` | float | Walking speed in m/s | 0.6 - 1.5 |
| `treadmill` | boolean | Treadmill vs ramp | true/false |

**Example**: `"incline_deg:10,speed_m_s:1.0,treadmill:true"`

---

### Decline Walking

**Description**: Walking downhill on negative incline

**Task**: `decline_walking`  
**Task ID**: `decline_5deg`, `decline_10deg`, `decline_15deg`, etc.

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `incline_deg` | float | Decline angle (negative) | -5, -10, -15 |
| `speed_m_s` | float | Walking speed in m/s | 0.6 - 1.5 |
| `treadmill` | boolean | Treadmill vs ramp | true/false |

**Example**: `"incline_deg:-10,speed_m_s:0.8,treadmill:true"`

---

### Stair Ascent

**Description**: Walking up stairs

**Task**: `stair_ascent`  
**Task ID**: `stair_ascent`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `steps` | int | Number of steps | 4, 8, 12 |
| `height_m` | float | Step height in meters | 0.10 - 0.25 |
| `depth_m` | float | Step depth in meters | 0.25 - 0.35 |
| `speed_m_s` | float | Ascent speed if measured | 0.4 - 0.8 |
| `handrail` | boolean | Handrail availability/use | true/false |
| `step_over_step` | boolean | Reciprocal gait pattern | true/false |
| `step_count_per_cycle` | int | Steps included in one gait cycle | 1, 2 |

**Examples**: 
- Standard stairs: `"steps:8,height_m:0.17,handrail:false,step_over_step:true"`
- Variable height: `"steps:4,height_m:0.20,depth_m:0.30,step_count_per_cycle:1"`

*Note: `height_m` supports variable step heights to accommodate different stair configurations in research settings.*

---

### Stair Descent

**Description**: Walking down stairs

**Task**: `stair_descent`  
**Task ID**: `stair_descent`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `steps` | int | Number of steps | 4, 8, 12 |
| `height_m` | float | Step height in meters | 0.10 - 0.25 |
| `depth_m` | float | Step depth in meters | 0.25 - 0.35 |
| `speed_m_s` | float | Descent speed if measured | 0.3 - 0.7 |
| `handrail` | boolean | Handrail availability/use | true/false |
| `step_over_step` | boolean | Reciprocal gait pattern | true/false |
| `step_count_per_cycle` | int | Steps included in one gait cycle | 1, 2 |

**Examples**: 
- Standard stairs: `"steps:8,height_m:0.17,handrail:true,step_over_step:true"`
- Variable height: `"steps:4,height_m:0.20,depth_m:0.30,step_count_per_cycle:1"`

*Note: `height_m` supports variable step heights to accommodate different stair configurations in research settings.*

---

### Running

**Description**: Running or jogging locomotion

**Task**: `run`  
**Task ID**: `run`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `speed_m_s` | float | Running speed in m/s | 2.0 - 5.0 |
| `treadmill` | boolean | Treadmill vs overground | true/false |
| `incline_deg` | float | Incline if applicable | -5 to 15 |

**Example**: `"speed_m_s:3.0,treadmill:true,incline_deg:0"`

---

### Jumping

**Description**: Various jumping activities

**Task**: `jump`  
**Task ID**: `jump`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `type` | string | Jump type | "vertical", "broad", "drop", "squat" |
| `height_m` | float | Jump or drop height | 0.2 - 0.6 |
| `distance_m` | float | Horizontal distance (broad jump) | 1.0 - 2.5 |
| `repetitions` | int | Number of jumps | 1, 3, 5 |
| `bilateral` | boolean | Two-leg vs single-leg | true/false |

**Example**: `"type:vertical,height_m:0.3,repetitions:1,bilateral:true"`

---

### Sit to Stand

**Description**: Rising from seated to standing position

**Task**: `sit_to_stand`  
**Task ID**: `sit_to_stand`

**Cycle Definition**: Unidirectional movement from sitting → standing (0% → 100%)
- **0%**: Fully seated position
- **100%**: Fully standing position

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `repetitions` | int | Number of rise repetitions | 1, 5, 10 |
| `chair_height_m` | float | Seat height in meters | 0.40 - 0.50 |
| `arms_used` | boolean | Whether arms were used | true/false |
| `speed` | string | Movement speed | "normal", "fast", "slow" |

**Example**: `"repetitions:5,chair_height_m:0.45,arms_used:false,speed:normal"`

---

### Stand to Sit

**Description**: Lowering from standing to seated position

**Task**: `stand_to_sit`  
**Task ID**: `stand_to_sit`

**Cycle Definition**: Unidirectional movement from standing → sitting (0% → 100%)
- **0%**: Fully standing position
- **100%**: Fully seated position

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `repetitions` | int | Number of lower repetitions | 1, 5, 10 |
| `chair_height_m` | float | Seat height in meters | 0.40 - 0.50 |
| `arms_used` | boolean | Whether arms were used | true/false |
| `speed` | string | Movement speed | "normal", "fast", "slow" |

**Example**: `"repetitions:5,chair_height_m:0.45,arms_used:false,speed:normal"`

---

### Squats

**Description**: Squatting exercise motion

**Task**: `squats`  
**Task ID**: `squats`

**Common Metadata**:

| Key | Type | Description | Typical Values |
|-----|------|-------------|----------------|
| `repetitions` | int | Number of squats | 5, 10, 15 |
| `depth` | string | Squat depth | "partial", "parallel", "full" |
| `load_kg` | float | Additional weight if any | 0 - 50 |
| `tempo` | string | Movement tempo | "normal", "slow", "explosive" |

**Example**: `"repetitions:10,depth:parallel,load_kg:0,tempo:normal"`

## Impaired Population Task Naming

### Overview

Tasks performed by impaired populations can be named using population-specific suffixes to distinguish them from standard able-bodied tasks. This is particularly important when:
- Validation ranges differ significantly from able-bodied norms
- Research focuses on population-specific adaptations
- Clinical relevance requires explicit population identification

### Naming Convention

**Format**: `<base_task>_<population_suffix>`

The population suffix indicates the primary impairment affecting locomotion:

| Population | Suffix | Example Task | Description |
|------------|--------|--------------|-------------|
| Stroke | `_stroke` | `level_walking_stroke` | Level walking for stroke survivors |
| Transfemoral Amputee | `_amputee` or `_tfa` | `level_walking_amputee` | Level walking with above-knee prosthesis |
| Transtibial Amputee | `_amputee` or `_tta` | `incline_walking_tta` | Incline walking with below-knee prosthesis |
| Parkinson's | `_pd` | `stair_ascent_pd` | Stair climbing for Parkinson's patients |
| Spinal Cord Injury | `_sci` | `level_walking_sci` | Walking with incomplete SCI |
| Cerebral Palsy | `_cp` | `level_walking_cp` | Walking for individuals with CP |
| Multiple Sclerosis | `_ms` | `level_walking_ms` | Walking for MS patients |

### Task ID and Task Info

- **Task ID** remains consistent with standard tasks (e.g., `level`, `incline_10deg`)
- **Task Info** can include population-specific metadata:

**Stroke-specific metadata**:
```
"speed_m_s:0.8,affected_side:left,FAC_score:5,assistive_device:cane"
```

**Amputee-specific metadata**:
```
"speed_m_s:1.0,prosthetic_type:C-leg,amputation_side:right,K_level:3"
```

**Parkinson's-specific metadata**:
```
"speed_m_s:0.9,medication_state:ON,H_Y_stage:2,freezing_episodes:0"
```

### When to Use Impaired Task Names

**Use impaired task names when**:
1. Biomechanical patterns differ substantially from able-bodied norms
2. Population-specific validation ranges are needed
3. Research explicitly compares within-population variations
4. Clinical protocols require population-specific analysis

**Use standard task names when**:
1. The impaired population follows typical biomechanical patterns
2. Mixed population analysis is the goal
3. The subject ID already provides sufficient population context
4. Comparison with able-bodied controls is primary

### Examples

```python
# Dataset with mixed populations
data = [
    # Able-bodied control
    {"subject": "STUDY_AB01", "task": "level_walking", "task_id": "level"},
    
    # Stroke patient with explicit task naming
    {"subject": "STUDY_CVA01", "task": "level_walking_stroke", "task_id": "level",
     "task_info": "speed_m_s:0.6,affected_side:right,FAC_score:4"},
    
    # Amputee with explicit task naming
    {"subject": "STUDY_TFA01", "task": "level_walking_amputee", "task_id": "level",
     "task_info": "speed_m_s:1.1,prosthetic_type:Genium,K_level:3"}
]
```

### Validation Considerations

Impaired population tasks may require:
- **Asymmetric validation ranges** for affected vs unaffected sides
- **Wider acceptable ranges** to accommodate compensatory patterns
- **Population-specific normative data** for meaningful comparisons
- **Task-specific adaptations** (e.g., step-to-step vs step-over-step stair climbing)

See `contributor_tools/validation_ranges/impaired_ranges.yaml` for population-specific validation templates.

## Usage Examples

### Python Implementation

```python
from user_libs.python.locomotion_data import LocomotionData

# Load dataset
data = LocomotionData('converted_datasets/dataset_phase.parquet')

# Parse task_info string into dictionary
info = data.parse_task_info("incline_deg:10,speed_m_s:1.2,treadmill:true")
# Returns: {'incline_deg': 10, 'speed_m_s': 1.2, 'treadmill': True}

# Filter by specific task_id
incline_10_data = data.filter_by_task_id('incline_10deg')

# Get specific metadata value for a subject-task combination
speed = data.get_task_metadata('SUB01', 'incline_walking', 'speed_m_s')
# Returns: 1.2

# Find all unique task_ids in dataset
task_ids = data.df['task_id'].unique()
```

### MATLAB Implementation

```matlab
% Load parquet file
data = parquetread('dataset_phase.parquet');

% Filter by task
incline_data = data(strcmp(data.task, 'incline_walking'), :);

% Parse task_info (simple approach)
task_info_str = incline_data.task_info{1};
% Parse "incline_deg:10,speed_m_s:1.2" into struct
pairs = strsplit(task_info_str, ',');
for i = 1:length(pairs)
    kv = strsplit(pairs{i}, ':');
    metadata.(kv{1}) = str2double(kv{2});
end
```

## Implementation Notes

### For Dataset Converters

1. **Map native task names** to our standard task categories
2. **Extract primary parameter** for task_id (e.g., incline angle)
3. **Format metadata** as comma-separated key:value pairs
4. **Ensure consistency** - same task should have same task_id format

### For Data Users

1. **Use task for broad filtering** - get all walking data regardless of incline
2. **Use task_id for specific conditions** - get only 10° incline walking
3. **Parse task_info for detailed analysis** - extract exact speeds, dimensions
4. **Handle missing metadata gracefully** - not all datasets have all parameters

### Standard Compliance

- All three columns (task, task_id, task_info) are **required**
- Use exact task names from this reference
- Follow the key:value format strictly for parsing compatibility
- Document any dataset-specific metadata keys

## Future Extensions

Additional tasks can be added following this pattern:
1. Define the biomechanical category (`task`)
2. Identify the primary distinguishing parameter (`task_id`)
3. Document common metadata keys for `task_info`
4. Update converters to map to the new task

---

*For questions about task classification or to propose new task types, see the [Contributing Guide](../../contributing/index.md).*