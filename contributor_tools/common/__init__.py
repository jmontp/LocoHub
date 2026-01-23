"""Common utilities for contributor tools.

This package contains shared libraries for:
- Data conversion (segmentation, phase detection)
- Validation (validator, config management)
- Plotting (validation plots, forward kinematics)
"""

from .phase_detection import (
    VerticalGRFConfig,
    VerticalGRFEvents,
    detect_vertical_grf_events,
)

from .stride_segmentation import (
    # Enums
    SegmentationArchetype,
    # Dataclasses
    SegmentBoundary,
    GaitSegmentationConfig,
    StandingActionConfig,
    SitStandConfig,
    # Mappings
    TASK_ARCHETYPE_MAP,
    # Main functions
    segment_gait_cycles,
    segment_standing_action_cycles,
    segment_sit_stand_transfers,
    segment_by_task,
    # Utilities
    estimate_sample_rate,
    compute_max_joint_velocity,
    filter_segments_by_duration,
    filter_segments_by_duration_iqr,
    remove_transition_segments,
)

from .config_manager import ValidationConfigManager

from .derivatives import (
    find_discontinuity_index,
    interpolate_discontinuity,
    smooth_velocity_spikes,
    compute_velocity_from_shifted_angle,
    compute_acceleration_from_velocity,
)

from .force_plate import (
    ForcePlateConfig,
    ForcePlateData,
    assign_force_plates_to_legs,
    process_force_plate_data,
    resample_to_phase,
)

# Submodules available as contributor_tools.common.validation and contributor_tools.common.plotting
from . import validation
from . import plotting

__all__ = [
    # phase_detection
    "VerticalGRFConfig",
    "VerticalGRFEvents",
    "detect_vertical_grf_events",
    # stride_segmentation
    "SegmentationArchetype",
    "SegmentBoundary",
    "GaitSegmentationConfig",
    "StandingActionConfig",
    "SitStandConfig",
    "TASK_ARCHETYPE_MAP",
    "segment_gait_cycles",
    "segment_standing_action_cycles",
    "segment_sit_stand_transfers",
    "segment_by_task",
    "estimate_sample_rate",
    "compute_max_joint_velocity",
    "filter_segments_by_duration",
    "filter_segments_by_duration_iqr",
    "remove_transition_segments",
    # config_manager
    "ValidationConfigManager",
    # derivatives
    "find_discontinuity_index",
    "interpolate_discontinuity",
    "smooth_velocity_spikes",
    "compute_velocity_from_shifted_angle",
    "compute_acceleration_from_velocity",
    # force_plate
    "ForcePlateConfig",
    "ForcePlateData",
    "assign_force_plates_to_legs",
    "process_force_plate_data",
    "resample_to_phase",
    # submodules
    "validation",
    "plotting",
]
