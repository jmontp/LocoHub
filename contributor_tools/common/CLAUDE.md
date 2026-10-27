# Common Utilities

Shared Python libraries for biomechanical data processing, used by conversion scripts and validation tools.

## Files

| File | Purpose |
|------|---------|
| `stride_segmentation.py` | Unified stride/cycle segmentation for all task types |
| `phase_detection.py` | Low-level GRF-based gait event detection |
| `near_miss_analysis.py` | Marginal failure analysis for validation tuning |
| `opensim_inverse_dynamics.py` | OpenSim-based inverse dynamics computation |
| `opensim_scaling.py` | OpenSim ScaleTool wrapper for model scaling |
| `opensim_ik.py` | OpenSim IKTool wrapper for inverse kinematics |
| `opensim_pipeline.py` | Orchestrates Scale → IK → ID pipeline |
| `force_plate.py` | Force plate data processing and leg assignment |
| `derivatives.py` | Velocity/acceleration computation from angle data |

## Stride Segmentation (`stride_segmentation.py`)

Unified library for segmenting biomechanical time-series data into cycles/strides. Implements three segmentation archetypes per the reference specification in `docs/reference/index.md`.

### Segmentation Archetypes

#### 1. Gait (Heel Strike to Heel Strike)

**Tasks:** level_walking, incline_walking, decline_walking, stair_ascent, stair_descent, run, backward_walking, hop

**Detection:** Upward GRF threshold crossing (configurable, default 50N or 0.05 BW)

```python
from common.stride_segmentation import segment_gait_cycles, GaitSegmentationConfig

config = GaitSegmentationConfig(
    grf_vertical_col='grf_vertical_ipsi_BW',
    time_col='time_s',
    grf_threshold_N=50.0,          # For N units
    grf_threshold_BW=0.05,         # For BW units (auto-detected)
    min_stride_duration_s=0.4,
    max_stride_duration_s=2.5,
    skip_first_segments=2,         # Remove transition strides
    skip_last_segments=1,
    use_iqr_filtering=True,
    iqr_multiplier=1.5,
)
segments = segment_gait_cycles(df, config, leg_side="ipsi")
```

#### 2. Standing → Action → Standing

**Tasks:** jump, squat, lunge

**Detection:**
- **Jump:** Requires flight phase (GRF < 50N for ≥50ms), bounded by stable standing
- **Squat/Lunge:** Velocity-based motion detection bounded by stable standing

**Stable standing:** GRF > 600N AND max joint velocity < 25 deg/s

```python
from common.stride_segmentation import segment_standing_action_cycles, StandingActionConfig

config = StandingActionConfig(
    grf_vertical_ipsi_col='grf_vertical_ipsi_N',
    grf_vertical_contra_col='grf_vertical_contra_N',
    time_col='time_s',
    velocity_cols=('hip_flexion_velocity_ipsi_rad_s', ...),
    standing_grf_threshold_N=600.0,
    flight_grf_threshold_N=50.0,
    velocity_threshold_rad_s=0.436,  # 25 deg/s
    require_flight_phase=True,       # True for jumps
    min_flight_duration_s=0.05,
)
segments = segment_standing_action_cycles(df, config, action_type="jump")
```

#### 3. Sitting ↔ Standing Transfers

**Tasks:** sit_to_stand, stand_to_sit

**Detection:** GRF state machine with velocity-based motion onset/offset

**States:**
- Sitting: Total GRF < 400N
- Standing: Total GRF > 600N
- Transition: Between thresholds

**Motion boundaries:** Velocity crosses 25 deg/s threshold

```python
from common.stride_segmentation import segment_sit_stand_transfers, SitStandConfig

config = SitStandConfig(
    grf_vertical_ipsi_col='grf_vertical_ipsi_N',
    grf_vertical_contra_col='grf_vertical_contra_N',
    time_col='time_s',
    velocity_cols=('hip_flexion_velocity_ipsi_rad_s', ...),
    sitting_grf_threshold_N=400.0,
    standing_grf_threshold_N=600.0,
    velocity_threshold_rad_s=0.436,  # 25 deg/s
    margin_before_s=0.1,
    margin_after_s=0.1,
)
segments = segment_sit_stand_transfers(df, config, transfer_type="sit_to_stand")
```

### High-Level Task Router

Automatically routes to the correct archetype based on task name:

```python
from common.stride_segmentation import segment_by_task

# Uses TASK_ARCHETYPE_MAP to select correct function
segments = segment_by_task(df, task="level_walking")  # → segment_gait_cycles
segments = segment_by_task(df, task="jump")           # → segment_standing_action_cycles
segments = segment_by_task(df, task="sit_to_stand")   # → segment_sit_stand_transfers
```

### Result Dataclass

All segmentation functions return `List[SegmentBoundary]`:

```python
@dataclass
class SegmentBoundary:
    start_idx: int          # Start index in source DataFrame
    end_idx: int            # End index in source DataFrame
    start_time_s: float     # Start time in seconds
    end_time_s: float       # End time in seconds
    duration_s: float       # Segment duration
    segment_type: str       # e.g., "stride", "jump", "sit_to_stand"
    events: Dict[str, int]  # Event indices within segment (e.g., {"toe_off": 45})
    metadata: Dict[str, Any]  # Additional info (e.g., {"flight_duration_s": 0.3})
```

### Task to Archetype Mapping

```python
TASK_ARCHETYPE_MAP = {
    # Gait
    "level_walking": SegmentationArchetype.GAIT,
    "incline_walking": SegmentationArchetype.GAIT,
    "decline_walking": SegmentationArchetype.GAIT,
    "stair_ascent": SegmentationArchetype.GAIT,
    "stair_descent": SegmentationArchetype.GAIT,
    "run": SegmentationArchetype.GAIT,
    "backward_walking": SegmentationArchetype.GAIT,
    "hop": SegmentationArchetype.GAIT,

    # Standing Action
    "jump": SegmentationArchetype.STANDING_ACTION,
    "squat": SegmentationArchetype.STANDING_ACTION,
    "lunge": SegmentationArchetype.STANDING_ACTION,

    # Sit-Stand Transfer
    "sit_to_stand": SegmentationArchetype.SIT_STAND_TRANSFER,
    "stand_to_sit": SegmentationArchetype.SIT_STAND_TRANSFER,
}
```

### Utility Functions

```python
# Filter segments by IQR-based duration outlier detection
filtered, n_removed, bounds = filter_segments_by_duration_iqr(
    segments, iqr_multiplier=1.5
)

# Remove transition segments at trial boundaries
filtered, n_removed = remove_transition_segments(
    segments, skip_first=2, skip_last=1
)

# Compute max joint velocity across multiple columns
max_vel = compute_max_joint_velocity(df, velocity_cols, smooth_window=5)

# Estimate sample rate from time column
sample_rate = estimate_sample_rate(df, time_col='time_s')
```

### Unit Auto-Detection

The library auto-detects whether GRF data is in Newtons or body weight (BW) units:
- If `max(GRF) < 10`: assumes BW units, uses `*_threshold_BW` values
- Otherwise: assumes Newton units, uses `*_threshold_N` values

## Phase Detection (`phase_detection.py`)

Lower-level module for GRF-based gait event detection. Used internally by `stride_segmentation.py`.

```python
from common.phase_detection import detect_vertical_grf_events, VerticalGRFConfig

config = VerticalGRFConfig(
    grf_col='grf_vertical_ipsi_BW',
    time_col='time_s',
    threshold=0.05,
    min_contact_interval_s=0.3,
)
events = detect_vertical_grf_events(df, config)
# events.heel_strikes: np.ndarray of indices
# events.toe_offs: np.ndarray of indices
```

## Near-Miss Analysis (`near_miss_analysis.py`)

Identifies marginal validation failures for range tuning. Used by `diagnose_validation_failures.py`.

**Marginal failure criteria:**
- Fails at ≤ `max_phases_failed` phase checkpoints (default: 2)
- Each violation is within `max_zscore` standard deviations of clean data mean (default: 2.5)

```python
from common.near_miss_analysis import identify_marginal_failures

marginal_strides = identify_marginal_failures(
    df,
    ranges_yaml,
    max_zscore=2.5,
    max_phases_failed=2
)
```

## Default Thresholds (Reference Specification)

| Parameter | Value | Usage |
|-----------|-------|-------|
| Heel strike GRF | 20-50 N / 0.02-0.05 BW | Gait contact detection |
| Standing GRF | 600 N / 0.8 BW | Stable standing state |
| Sitting GRF | 400 N / 0.5 BW | Seated state |
| Flight GRF | 50 N / 0.05 BW | Airborne state (jumps) |
| Velocity threshold | 25 deg/s (0.436 rad/s) | Motion onset/offset |
| Min stable duration | 0.2-0.3 s | State confirmation |
| IQR multiplier | 1.5 | Duration outlier detection |

## OpenSim Inverse Dynamics (`opensim_inverse_dynamics.py`)

Wrapper for OpenSim's InverseDynamicsTool to compute joint moments from kinematics and GRF data.

### Requirements

- OpenSim 4.4+ with Python bindings: `conda install -c opensim-org opensim`
- Musculoskeletal model file (.osim)
- Kinematics file (.mot) with joint angles
- GRF file (.mot) with force plate data

### Quick Start

```python
from common.opensim_inverse_dynamics import (
    OPENSIM_AVAILABLE,
    compute_inverse_dynamics_for_stride,
    interpolate_to_phase,
)

if OPENSIM_AVAILABLE:
    moments = compute_inverse_dynamics_for_stride(
        model_path=Path('model.osim'),
        ik_mot_path=Path('kinematics.mot'),
        grf_mot_path=Path('forces.mot'),
        ipsi_side='r',
        body_mass_kg=75.0,
    )

    # Phase-normalize the moments
    if moments is not None:
        hip_moment = interpolate_to_phase(
            moments['hip_flexion_moment_ipsi_Nm_kg'],
            moments['time'],
            num_points=150
        )
```

### Functions

| Function | Purpose |
|----------|---------|
| `check_opensim_available()` | Check if OpenSim Python API is installed |
| `setup_external_loads()` | Create external loads XML for force plates |
| `run_inverse_dynamics()` | Run OpenSim ID tool |
| `read_sto_file()` | Parse OpenSim .sto output files |
| `extract_sagittal_moments()` | Extract hip, knee, ankle moments with sign conventions |
| `modify_rajagopal_model()` | Lock secondary knee DOFs for single-DOF knee models |
| `disable_model_forces()` | Disable muscles/reserves so ID outputs net moments |
| `compute_inverse_dynamics_for_stride()` | High-level function for single stride ID |

### Sign Conventions

The module automatically handles sign convention conversion:

| Joint | OpenSim Convention | LocoHub Standard | Action |
|-------|-------------------|------------------|--------|
| Hip flexion | Flexion + | Flexion + | None |
| Knee | Extension + | Flexion + | Negate |
| Ankle | Dorsiflexion + | Dorsiflexion + | None |

### Configuration

```python
from common.opensim_inverse_dynamics import InverseDynamicsConfig

config = InverseDynamicsConfig(
    lowpass_cutoff_hz=6.0,      # Filter cutoff for kinematics
    disable_model_forces=True,  # Disable muscles/reserves so output reflects net ID moments
    subtract_inertia_baseline=False,  # Only use if you explicitly want to remove inertial baseline
    right_foot_body='calcn_r',   # Body name for right foot forces
    left_foot_body='calcn_l',    # Body name for left foot forces
    force1_identifier='ground_force1',  # Force plate 1 column prefix
    force2_identifier='ground_force2',  # Force plate 2 column prefix
)
```

## OpenSim Model Scaling (`opensim_scaling.py`)

Wrapper for OpenSim's ScaleTool to scale musculoskeletal models using static marker trials.

### Quick Start

```python
from common.opensim_scaling import (
    OPENSIM_AVAILABLE,
    scale_model_with_static_trial,
    scale_model_with_measurements,
    ScalingConfig,
)

if OPENSIM_AVAILABLE:
    scaled_model = scale_model_with_static_trial(
        generic_model_path='rajagopal.osim',
        static_trc_path='static_trial.trc',
        output_model_path='scaled_model.osim',
        subject_mass_kg=75.0,
    )
```

### Functions

| Function | Purpose |
|----------|---------|
| `scale_model_with_static_trial()` | Scale model using static marker trial |
| `scale_model_with_measurements()` | Scale model using height/mass only |
| `get_model_marker_names()` | Get list of markers defined in model |
| `verify_marker_correspondence()` | Check which TRC markers match model |
| `create_scale_setup_xml()` | Create ScaleTool setup file |

## OpenSim Inverse Kinematics (`opensim_ik.py`)

Wrapper for OpenSim's InverseKinematicsTool to compute joint angles from marker data.

### Quick Start

```python
from common.opensim_ik import (
    OPENSIM_AVAILABLE,
    run_inverse_kinematics,
    IKConfig,
    IKResult,
)

if OPENSIM_AVAILABLE:
    result = run_inverse_kinematics(
        model_path='scaled_model.osim',
        trc_path='markers.trc',
        output_mot_path='ik_output.mot',
    )
    if result.success:
        print(f"IK completed with RMS error: {result.rms_error}")
```

### Functions

| Function | Purpose |
|----------|---------|
| `run_inverse_kinematics()` | Run IK on marker data |
| `read_mot_file()` | Parse OpenSim .mot files |
| `get_ik_coordinate_names()` | Get model coordinates |
| `validate_ik_against_reference()` | Compare IK output to reference |
| `create_ik_setup_xml()` | Create IKTool setup file |

## OpenSim Pipeline (`opensim_pipeline.py`)

High-level orchestrator for the complete Scale → IK → ID workflow.

### Quick Start

```python
from common.opensim_pipeline import (
    OpenSimPipeline,
    PipelineConfig,
    StrideResult,
)

pipeline = OpenSimPipeline(
    generic_model_path='rajagopal.osim',
    output_dir='opensim_output/',
)

# Process a stride
result = pipeline.process_stride(
    subject_id='S011',
    static_trc_path='S011/Static/static.trc',
    stride_trc_path='S011/LevelWalking/stride.trc',
    grf_mot_path='S011/LevelWalking/grf.mot',
    subject_mass_kg=75.0,
    ipsi_side='r',
)

if result.success:
    kinematics = result.kinematics_phase  # Phase-normalized
    moments = result.moments_phase        # Phase-normalized
```

### Features

- **Model caching:** Scaled models are cached per subject
- **IK caching:** IK results can be cached to avoid recomputation
- **Phase normalization:** Optional automatic phase normalization
- **Configurable:** IK marker weights, ID filter settings, etc.

### Configuration

```python
from common.opensim_pipeline import PipelineConfig
from common.opensim_scaling import ScalingConfig
from common.opensim_ik import IKConfig
from common.opensim_inverse_dynamics import InverseDynamicsConfig

config = PipelineConfig(
    scaling=ScalingConfig(preserve_mass_distribution=True),
    ik=IKConfig(marker_weights={'LASI': 10.0, 'RASI': 10.0, ...}),
    id=InverseDynamicsConfig(lowpass_cutoff_hz=6.0),
    cache_scaled_models=True,
    cache_ik_results=True,
    num_phase_points=150,
)
```

## Example: Using in a Conversion Script

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.stride_segmentation import (
    TASK_ARCHETYPE_MAP,
    SegmentationArchetype,
    segment_gait_cycles,
    segment_sit_stand_transfers,
    GaitSegmentationConfig,
    SitStandConfig,
)

def process_trial(df, task):
    archetype = TASK_ARCHETYPE_MAP.get(task, SegmentationArchetype.GAIT)

    if archetype == SegmentationArchetype.GAIT:
        config = GaitSegmentationConfig(grf_vertical_col='fp_force_y')
        return segment_gait_cycles(df, config)

    elif archetype == SegmentationArchetype.SIT_STAND_TRANSFER:
        config = SitStandConfig(
            grf_vertical_ipsi_col='fp_l_force_y',
            grf_vertical_contra_col='fp_r_force_y',
        )
        return segment_sit_stand_transfers(df, config, transfer_type=task)

    # ... handle other archetypes
```

## Example: Using OpenSim Pipeline

```python
from common.opensim_pipeline import OpenSimPipeline, PipelineConfig
from common.opensim_ik import IKConfig

# Initialize pipeline
pipeline = OpenSimPipeline(
    generic_model_path=Path('model.osim'),
    output_dir=Path('output/'),
    config=PipelineConfig(
        ik=IKConfig(marker_weights={'LASI': 10.0, 'RASI': 10.0}),
    ),
)

# Process multiple strides for a subject
for stride_trc in stride_files:
    result = pipeline.process_stride(
        subject_id='S001',
        static_trc_path=static_trc,
        stride_trc_path=stride_trc,
        grf_mot_path=grf_mot,
        subject_mass_kg=75.0,
        ipsi_side='r',
    )

    if result.success:
        # Use result.kinematics_phase and result.moments_phase
        pass
```
