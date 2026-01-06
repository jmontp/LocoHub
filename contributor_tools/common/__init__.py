"""Common utilities for contributor tools."""

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
]
