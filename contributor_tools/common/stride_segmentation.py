"""Unified stride/cycle segmentation for biomechanical data.

This module provides segmentation functions for three archetypes:
1. Gait (heel strike to heel strike) - for walking, running, stairs, etc.
2. Standing -> Action -> Standing - for jumps, squats, lunges
3. Sitting <-> Standing transfers - for sit_to_stand, stand_to_sit

Reference: docs/reference/index.md "Segmentation Archetypes" section
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .phase_detection import VerticalGRFConfig, detect_vertical_grf_events


class SegmentationArchetype(Enum):
    """Segmentation archetype types per reference spec."""
    GAIT = "gait"                        # Heel Strike to Heel Strike
    STANDING_ACTION = "standing_action"  # Standing -> Action -> Standing
    SIT_STAND_TRANSFER = "sit_stand"     # Sitting <-> Standing


@dataclass
class SegmentBoundary:
    """A single detected segment with start/end indices and metadata."""

    start_idx: int
    end_idx: int
    start_time_s: float
    end_time_s: float
    duration_s: float
    segment_type: str  # e.g., "stride", "jump", "sit_to_stand"

    # Optional event indices within segment
    events: Dict[str, int] = field(default_factory=dict)
    # e.g., {"toe_off": 45, "contra_heel_strike": 75, "flight_start": 60}

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"flight_duration_s": 0.3, "leg_side": "l"}


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass(frozen=True)
class GaitSegmentationConfig:
    """Configuration for Heel Strike to Heel Strike segmentation.

    Applies to: level_walking, incline_walking, decline_walking,
                stair_ascent, stair_descent, run, walk_backward, hop
    """

    # GRF column names
    grf_vertical_col: str = "grf_vertical_ipsi_BW"
    time_col: str = "time_s"

    # Detection thresholds
    grf_threshold_N: float = 50.0          # GRF threshold for contact detection (N)
    grf_threshold_BW: float = 0.05         # GRF threshold when using BW units
    min_contact_interval_s: float = 0.3    # Minimum time between heel strikes
    smoothing_window: int = 5              # Samples for smoothing

    # Stride duration bounds
    min_stride_duration_s: float = 0.4     # Minimum stride
    max_stride_duration_s: float = 2.5     # Maximum stride

    # Transition stride removal
    skip_first_segments: int = 2           # Skip first N strides
    skip_last_segments: int = 1            # Skip last N strides

    # IQR-based filtering
    use_iqr_filtering: bool = True
    iqr_multiplier: float = 1.5


@dataclass(frozen=True)
class StandingActionConfig:
    """Configuration for Standing -> Action -> Standing segmentation.

    Applies to: jump, squat, lunge
    """

    # GRF columns
    grf_vertical_ipsi_col: str = "grf_vertical_ipsi_BW"
    grf_vertical_contra_col: str = "grf_vertical_contra_BW"
    time_col: str = "time_s"

    # Joint velocity columns (for max velocity computation)
    velocity_cols: Tuple[str, ...] = (
        "hip_flexion_velocity_ipsi_rad_s",
        "hip_flexion_velocity_contra_rad_s",
        "knee_flexion_velocity_ipsi_rad_s",
        "knee_flexion_velocity_contra_rad_s",
        "ankle_dorsiflexion_velocity_ipsi_rad_s",
        "ankle_dorsiflexion_velocity_contra_rad_s",
    )

    # State thresholds (per reference spec)
    standing_grf_threshold_N: float = 600.0     # GRF above which = standing
    standing_grf_threshold_BW: float = 0.8      # ~80% BW for standing
    flight_grf_threshold_N: float = 50.0        # GRF below which = flight
    flight_grf_threshold_BW: float = 0.05       # ~5% BW for flight
    velocity_threshold_deg_s: float = 25.0      # Joint velocity for stable state
    velocity_threshold_rad_s: float = 0.436     # 25 deg/s in radians

    # Duration constraints
    min_stable_duration_s: float = 0.2         # Minimum stable standing duration
    min_flight_duration_s: float = 0.05        # Minimum flight duration (jumps only)
    min_segment_duration_s: float = 0.5        # Minimum total cycle duration
    max_segment_duration_s: float = 4.0        # Maximum total cycle duration

    # Margins
    margin_before_s: float = 0.05              # Extra time before motion onset
    margin_after_s: float = 0.05               # Extra time after motion offset

    # Smoothing
    smooth_window_s: float = 0.05              # Smoothing window in seconds

    # Task-specific flags
    require_flight_phase: bool = False         # True for jumps only

    # IQR filtering
    use_iqr_filtering: bool = True
    iqr_multiplier: float = 1.5


@dataclass(frozen=True)
class SitStandConfig:
    """Configuration for Sitting <-> Standing transfer segmentation.

    Applies to: sit_to_stand, stand_to_sit
    """

    # GRF columns (total vertical = sum of ipsi + contra)
    grf_vertical_ipsi_col: str = "grf_vertical_ipsi_BW"
    grf_vertical_contra_col: str = "grf_vertical_contra_BW"
    time_col: str = "time_s"

    # Joint velocity columns
    velocity_cols: Tuple[str, ...] = (
        "hip_flexion_velocity_ipsi_rad_s",
        "hip_flexion_velocity_contra_rad_s",
        "knee_flexion_velocity_ipsi_rad_s",
        "knee_flexion_velocity_contra_rad_s",
    )

    # State thresholds (per reference spec)
    sitting_grf_threshold_N: float = 400.0     # GRF below which = sitting
    sitting_grf_threshold_BW: float = 0.5      # ~50% BW for sitting
    standing_grf_threshold_N: float = 600.0    # GRF above which = standing
    standing_grf_threshold_BW: float = 0.8     # ~80% BW for standing
    velocity_threshold_deg_s: float = 25.0     # Motion onset/offset threshold
    velocity_threshold_rad_s: float = 0.436    # 25 deg/s in radians

    # Duration constraints
    min_stable_duration_s: float = 0.3         # Minimum stable state duration
    min_segment_duration_s: float = 0.3        # Minimum transfer duration
    max_segment_duration_s: float = 5.0        # Maximum transfer duration

    # Margins
    margin_before_s: float = 0.1               # Extra time before motion onset
    margin_after_s: float = 0.1                # Extra time after motion offset

    # Smoothing
    smooth_window_s: float = 0.3               # Smoothing window in seconds

    # IQR filtering
    use_iqr_filtering: bool = True
    iqr_multiplier: float = 1.5


# =============================================================================
# Task to Archetype Mapping
# =============================================================================

TASK_ARCHETYPE_MAP: Dict[str, SegmentationArchetype] = {
    # Gait tasks
    "level_walking": SegmentationArchetype.GAIT,
    "incline_walking": SegmentationArchetype.GAIT,
    "decline_walking": SegmentationArchetype.GAIT,
    "stair_ascent": SegmentationArchetype.GAIT,
    "stair_descent": SegmentationArchetype.GAIT,
    "run": SegmentationArchetype.GAIT,
    "backward_walking": SegmentationArchetype.GAIT,
    "walk_backward": SegmentationArchetype.GAIT,
    "hop": SegmentationArchetype.GAIT,

    # Standing-action tasks
    "jump": SegmentationArchetype.STANDING_ACTION,
    "squat": SegmentationArchetype.STANDING_ACTION,
    "lunge": SegmentationArchetype.STANDING_ACTION,

    # Sit-stand transfers
    "sit_to_stand": SegmentationArchetype.SIT_STAND_TRANSFER,
    "stand_to_sit": SegmentationArchetype.SIT_STAND_TRANSFER,
}


# =============================================================================
# Utility Functions
# =============================================================================

def estimate_sample_rate(df: pd.DataFrame, time_col: str = "time_s") -> Optional[float]:
    """Estimate sample rate from time column."""
    if time_col not in df.columns:
        return None
    time_values = df[time_col].to_numpy(dtype=float)
    if len(time_values) < 2:
        return None
    diffs = np.diff(time_values)
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return None
    return float(1.0 / np.median(diffs))


def compute_max_joint_velocity(
    df: pd.DataFrame,
    velocity_cols: Tuple[str, ...],
    smooth_window: int = 5
) -> np.ndarray:
    """Compute maximum absolute joint velocity across specified columns.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing velocity columns (in rad/s).
    velocity_cols : Tuple[str, ...]
        Column names to consider.
    smooth_window : int
        Moving average window for smoothing.

    Returns
    -------
    np.ndarray
        Max absolute velocity at each time point (in rad/s).
    """
    available_cols = [c for c in velocity_cols if c in df.columns]
    if not available_cols:
        return np.zeros(len(df))

    vel_matrix = np.abs(df[available_cols].to_numpy())
    max_vel = np.max(vel_matrix, axis=1)

    # Smooth
    if smooth_window > 1 and len(max_vel) > smooth_window:
        kernel = np.ones(smooth_window) / smooth_window
        padded = np.pad(max_vel, (smooth_window // 2, smooth_window - 1 - smooth_window // 2), mode="edge")
        max_vel = np.convolve(padded, kernel, mode="valid")

    return max_vel


def filter_segments_by_duration(
    segments: List[SegmentBoundary],
    min_duration_s: float,
    max_duration_s: float
) -> Tuple[List[SegmentBoundary], int]:
    """Filter segments by absolute duration bounds.

    Returns (filtered_segments, n_removed)
    """
    filtered = [s for s in segments if min_duration_s <= s.duration_s <= max_duration_s]
    return filtered, len(segments) - len(filtered)


def filter_segments_by_duration_iqr(
    segments: List[SegmentBoundary],
    iqr_multiplier: float = 1.5,
    min_floor_s: Optional[float] = None,
    max_ceiling_s: Optional[float] = None
) -> Tuple[List[SegmentBoundary], int, Tuple[float, float]]:
    """Filter segments using IQR-based outlier detection.

    Returns (filtered_segments, n_removed, (lower_bound, upper_bound))
    """
    if len(segments) < 4:
        # Not enough samples for IQR
        if min_floor_s is not None and max_ceiling_s is not None:
            return filter_segments_by_duration(segments, min_floor_s, max_ceiling_s)[0], 0, (min_floor_s, max_ceiling_s)
        return segments, 0, (0.0, float('inf'))

    durations = np.array([s.duration_s for s in segments])
    q1, q3 = np.percentile(durations, [25, 75])
    iqr = q3 - q1

    lower_bound = q1 - iqr_multiplier * iqr
    upper_bound = q3 + iqr_multiplier * iqr

    # Apply floors/ceilings
    if min_floor_s is not None:
        lower_bound = max(lower_bound, min_floor_s)
    if max_ceiling_s is not None:
        upper_bound = min(upper_bound, max_ceiling_s)

    filtered = [s for s in segments if lower_bound <= s.duration_s <= upper_bound]
    return filtered, len(segments) - len(filtered), (lower_bound, upper_bound)


def remove_transition_segments(
    segments: List[SegmentBoundary],
    skip_first: int = 0,
    skip_last: int = 0
) -> Tuple[List[SegmentBoundary], int]:
    """Remove transition segments at trial boundaries.

    Returns (filtered_segments, n_removed)
    """
    if len(segments) <= skip_first + skip_last:
        return [], len(segments)

    end_idx = len(segments) - skip_last if skip_last > 0 else len(segments)
    filtered = segments[skip_first:end_idx]
    return filtered, len(segments) - len(filtered)


def _smooth_signal(signal: np.ndarray, window: int) -> np.ndarray:
    """Apply moving average smoothing."""
    if signal.size == 0 or window <= 1:
        return signal
    kernel = np.ones(window) / window
    padded = np.pad(signal, (window // 2, window - 1 - window // 2), mode="edge")
    return np.convolve(padded, kernel, mode="valid")


# =============================================================================
# Gait Segmentation (Heel Strike to Heel Strike)
# =============================================================================

def segment_gait_cycles(
    df: pd.DataFrame,
    config: GaitSegmentationConfig,
    leg_side: str = "ipsi"
) -> List[SegmentBoundary]:
    """Segment gait data from heel strike to heel strike.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing GRF and time columns.
    config : GaitSegmentationConfig
        Configuration for detection thresholds and filtering.
    leg_side : str
        Which leg's GRF column to use for segmentation.

    Returns
    -------
    List[SegmentBoundary]
        List of detected stride segments.
    """
    if config.grf_vertical_col not in df.columns:
        return []

    if config.time_col not in df.columns:
        return []

    time_values = df[config.time_col].to_numpy(dtype=float)
    grf_values = df[config.grf_vertical_col].to_numpy(dtype=float)

    sample_rate = estimate_sample_rate(df, config.time_col)
    if sample_rate is None:
        sample_rate = 100.0  # Default fallback

    # Determine threshold based on units (BW vs N)
    # If max GRF < 10, assume BW units
    threshold = config.grf_threshold_BW if np.nanmax(grf_values) < 10 else config.grf_threshold_N

    # Smooth GRF
    smoothed = _smooth_signal(grf_values, config.smoothing_window)

    # Detect heel strikes (upward threshold crossing)
    above_threshold = smoothed > threshold
    crossings = np.diff(above_threshold.astype(int))
    heel_strikes = np.where(crossings == 1)[0] + 1

    if len(heel_strikes) < 2:
        return []

    # Filter by minimum interval
    min_interval_samples = int(config.min_contact_interval_s * sample_rate)
    filtered_hs = [int(heel_strikes[0])]
    for hs in heel_strikes[1:]:
        if hs - filtered_hs[-1] >= min_interval_samples:
            filtered_hs.append(int(hs))
    heel_strikes = filtered_hs

    if len(heel_strikes) < 2:
        return []

    # Create segments
    segments = []
    for i in range(len(heel_strikes) - 1):
        start_idx = heel_strikes[i]
        end_idx = heel_strikes[i + 1]

        start_time = time_values[start_idx]
        end_time = time_values[end_idx]
        duration = end_time - start_time

        # Basic duration check
        if not (config.min_stride_duration_s <= duration <= config.max_stride_duration_s):
            continue

        seg = SegmentBoundary(
            start_idx=start_idx,
            end_idx=end_idx,
            start_time_s=start_time,
            end_time_s=end_time,
            duration_s=duration,
            segment_type="stride",
            events={},
            metadata={"leg_side": leg_side}
        )
        segments.append(seg)

    # Remove transition strides
    if config.skip_first_segments > 0 or config.skip_last_segments > 0:
        segments, _ = remove_transition_segments(
            segments, config.skip_first_segments, config.skip_last_segments
        )

    # IQR filtering
    if config.use_iqr_filtering and len(segments) >= 4:
        segments, _, _ = filter_segments_by_duration_iqr(
            segments,
            config.iqr_multiplier,
            config.min_stride_duration_s,
            config.max_stride_duration_s
        )

    return segments


# =============================================================================
# Standing -> Action -> Standing Segmentation (Jump, Squat, Lunge)
# =============================================================================

def segment_standing_action_cycles(
    df: pd.DataFrame,
    config: StandingActionConfig,
    action_type: str = "jump"
) -> List[SegmentBoundary]:
    """Segment cycles that start and end in stable standing.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing GRF, velocity, and time columns.
    config : StandingActionConfig
        Configuration for state thresholds and filtering.
    action_type : str
        Type of action: "jump", "squat", or "lunge".

    Returns
    -------
    List[SegmentBoundary]
        List of detected action segments.
    """
    if config.time_col not in df.columns:
        return []

    time_values = df[config.time_col].to_numpy(dtype=float)
    n_samples = len(time_values)

    sample_rate = estimate_sample_rate(df, config.time_col)
    if sample_rate is None:
        sample_rate = 100.0

    # Compute total vertical GRF
    grf_ipsi = df[config.grf_vertical_ipsi_col].to_numpy() if config.grf_vertical_ipsi_col in df.columns else np.zeros(n_samples)
    grf_contra = df[config.grf_vertical_contra_col].to_numpy() if config.grf_vertical_contra_col in df.columns else np.zeros(n_samples)
    total_grf = grf_ipsi + grf_contra

    # Determine if BW or N units
    is_bw_units = np.nanmax(total_grf) < 10
    standing_thresh = config.standing_grf_threshold_BW if is_bw_units else config.standing_grf_threshold_N
    flight_thresh = config.flight_grf_threshold_BW if is_bw_units else config.flight_grf_threshold_N

    # Smooth GRF
    smooth_samples = max(1, int(config.smooth_window_s * sample_rate))
    smooth_grf = _smooth_signal(total_grf, smooth_samples)

    # Compute max joint velocity
    max_vel = compute_max_joint_velocity(df, config.velocity_cols, smooth_samples)

    # For jumps, detect flight phases first
    require_flight = config.require_flight_phase or action_type == "jump"

    if require_flight:
        # Detect flight phases (GRF below threshold)
        in_flight = smooth_grf < flight_thresh
        flight_changes = np.diff(np.concatenate([[False], in_flight, [False]]).astype(int))
        takeoff_idx = np.where(flight_changes == 1)[0]
        landing_idx = np.where(flight_changes == -1)[0]

        if len(takeoff_idx) == 0 or len(landing_idx) == 0:
            return []

        # Filter valid flight phases by minimum duration
        min_flight_samples = int(config.min_flight_duration_s * sample_rate)
        valid_flights = []
        for i in range(min(len(takeoff_idx), len(landing_idx))):
            if landing_idx[i] > takeoff_idx[i]:
                if landing_idx[i] - takeoff_idx[i] >= min_flight_samples:
                    valid_flights.append((takeoff_idx[i], landing_idx[i]))

        if not valid_flights:
            return []
    else:
        # For squats/lunges, find local minima in GRF (lowest depth points)
        # This is a simplified approach - look for periods where motion happens
        # then returns to stable standing
        valid_flights = None  # Will use velocity-based detection instead

    min_stable_samples = int(config.min_stable_duration_s * sample_rate)
    margin_samples_before = int(config.margin_before_s * sample_rate)
    margin_samples_after = int(config.margin_after_s * sample_rate)

    segments = []

    if require_flight and valid_flights:
        # Process each flight phase
        for flight_i, (flight_start, flight_end) in enumerate(valid_flights):
            # Define search boundaries
            search_start_limit = valid_flights[flight_i - 1][1] if flight_i > 0 else 0
            search_end_limit = valid_flights[flight_i + 1][0] if flight_i < len(valid_flights) - 1 else n_samples

            flight_dur = time_values[flight_end] - time_values[flight_start]

            # Find stable standing BEFORE this jump
            seg_start_idx = flight_start
            for j in range(flight_start, max(0, search_start_limit) - 1, -1):
                # Check if standing (high GRF) and stable (low velocity)
                if smooth_grf[j] > standing_thresh and max_vel[j] < config.velocity_threshold_rad_s:
                    # Check if sustained
                    stable_count = 0
                    for k in range(j, max(0, j - min_stable_samples), -1):
                        if smooth_grf[k] > standing_thresh and max_vel[k] < config.velocity_threshold_rad_s:
                            stable_count += 1
                        else:
                            break
                    if stable_count >= min_stable_samples // 2:
                        seg_start_idx = j
                        break

            # Find stable standing AFTER this jump
            seg_end_idx = flight_end
            for j in range(flight_end, min(n_samples, search_end_limit)):
                if smooth_grf[j] > standing_thresh and max_vel[j] < config.velocity_threshold_rad_s:
                    stable_count = 0
                    for k in range(j, min(n_samples, j + min_stable_samples)):
                        if smooth_grf[k] > standing_thresh and max_vel[k] < config.velocity_threshold_rad_s:
                            stable_count += 1
                        else:
                            break
                    if stable_count >= min_stable_samples // 2:
                        seg_end_idx = j
                        break

            # Add margins
            seg_start_idx = max(0, seg_start_idx - margin_samples_before)
            seg_end_idx = min(n_samples - 1, seg_end_idx + margin_samples_after)

            # Ensure no overlap
            seg_start_idx = max(seg_start_idx, search_start_limit)
            seg_end_idx = min(seg_end_idx, search_end_limit)

            start_time = time_values[seg_start_idx]
            end_time = time_values[seg_end_idx]
            duration = end_time - start_time

            if config.min_segment_duration_s <= duration <= config.max_segment_duration_s:
                seg = SegmentBoundary(
                    start_idx=seg_start_idx,
                    end_idx=seg_end_idx,
                    start_time_s=start_time,
                    end_time_s=end_time,
                    duration_s=duration,
                    segment_type=action_type,
                    events={"flight_start": flight_start, "flight_end": flight_end},
                    metadata={"flight_duration_s": flight_dur}
                )
                segments.append(seg)

    else:
        # Non-flight actions (squat, lunge): detect based on velocity transitions
        # Find periods where velocity exceeds threshold (motion) bounded by stable standing
        in_motion = max_vel > config.velocity_threshold_rad_s

        # Find motion onset and offset
        motion_changes = np.diff(np.concatenate([[False], in_motion, [False]]).astype(int))
        motion_starts = np.where(motion_changes == 1)[0]
        motion_ends = np.where(motion_changes == -1)[0]

        for i in range(min(len(motion_starts), len(motion_ends))):
            motion_start = motion_starts[i]
            motion_end = motion_ends[i]

            if motion_end <= motion_start:
                continue

            # Expand to include stable standing before and after
            seg_start_idx = motion_start
            for j in range(motion_start, -1, -1):
                if smooth_grf[j] > standing_thresh and max_vel[j] < config.velocity_threshold_rad_s:
                    seg_start_idx = j
                    break

            seg_end_idx = motion_end
            for j in range(motion_end, n_samples):
                if smooth_grf[j] > standing_thresh and max_vel[j] < config.velocity_threshold_rad_s:
                    seg_end_idx = j
                    break

            # Add margins
            seg_start_idx = max(0, seg_start_idx - margin_samples_before)
            seg_end_idx = min(n_samples - 1, seg_end_idx + margin_samples_after)

            start_time = time_values[seg_start_idx]
            end_time = time_values[seg_end_idx]
            duration = end_time - start_time

            if config.min_segment_duration_s <= duration <= config.max_segment_duration_s:
                seg = SegmentBoundary(
                    start_idx=seg_start_idx,
                    end_idx=seg_end_idx,
                    start_time_s=start_time,
                    end_time_s=end_time,
                    duration_s=duration,
                    segment_type=action_type,
                    events={},
                    metadata={}
                )
                segments.append(seg)

    # IQR filtering
    if config.use_iqr_filtering and len(segments) >= 4:
        segments, _, _ = filter_segments_by_duration_iqr(
            segments,
            config.iqr_multiplier,
            config.min_segment_duration_s,
            config.max_segment_duration_s
        )

    return segments


# =============================================================================
# Sitting <-> Standing Transfer Segmentation
# =============================================================================

def segment_sit_stand_transfers(
    df: pd.DataFrame,
    config: SitStandConfig,
    transfer_type: str = "both"
) -> List[SegmentBoundary]:
    """Segment sit-to-stand and stand-to-sit transfers.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing GRF, velocity, and time columns.
    config : SitStandConfig
        Configuration for state thresholds and filtering.
    transfer_type : str
        Type of transfers to detect: "sit_to_stand", "stand_to_sit", or "both".

    Returns
    -------
    List[SegmentBoundary]
        List of detected transfer segments.
    """
    if config.time_col not in df.columns:
        return []

    time_values = df[config.time_col].to_numpy(dtype=float)
    n_samples = len(time_values)

    sample_rate = estimate_sample_rate(df, config.time_col)
    if sample_rate is None:
        sample_rate = 100.0

    # Compute total vertical GRF
    grf_ipsi = df[config.grf_vertical_ipsi_col].to_numpy() if config.grf_vertical_ipsi_col in df.columns else np.zeros(n_samples)
    grf_contra = df[config.grf_vertical_contra_col].to_numpy() if config.grf_vertical_contra_col in df.columns else np.zeros(n_samples)
    total_grf = grf_ipsi + grf_contra

    # Determine if BW or N units
    is_bw_units = np.nanmax(total_grf) < 10
    sitting_thresh = config.sitting_grf_threshold_BW if is_bw_units else config.sitting_grf_threshold_N
    standing_thresh = config.standing_grf_threshold_BW if is_bw_units else config.standing_grf_threshold_N

    # Smooth GRF
    smooth_samples = max(1, int(config.smooth_window_s * sample_rate))
    smooth_grf = _smooth_signal(total_grf, smooth_samples)

    # Compute max joint velocity
    max_vel = compute_max_joint_velocity(df, config.velocity_cols, smooth_samples)

    # State machine: determine sitting/standing state at each sample
    states = []
    current_state = "unknown"

    for i in range(n_samples):
        if smooth_grf[i] > standing_thresh:
            new_state = "standing"
        elif smooth_grf[i] < sitting_thresh:
            new_state = "sitting"
        else:
            new_state = current_state if current_state != "unknown" else "transition"
        states.append(new_state)
        current_state = new_state

    # Find state transitions
    transitions = []
    for i in range(1, n_samples):
        if states[i-1] == "sitting" and states[i] == "standing":
            transitions.append(("sit_to_stand", i, time_values[i]))
        elif states[i-1] == "standing" and states[i] == "sitting":
            transitions.append(("stand_to_sit", i, time_values[i]))

    if not transitions:
        return []

    min_stable_samples = int(config.min_stable_duration_s * sample_rate)
    margin_samples_before = int(config.margin_before_s * sample_rate)
    margin_samples_after = int(config.margin_after_s * sample_rate)

    segments = []

    for t_idx, (trans_type, cross_idx, cross_time) in enumerate(transitions):
        # Filter by requested transfer type
        if transfer_type != "both" and trans_type != transfer_type:
            continue

        # Define search boundaries
        search_start_limit = transitions[t_idx - 1][1] if t_idx > 0 else 0
        search_end_limit = transitions[t_idx + 1][1] if t_idx < len(transitions) - 1 else n_samples

        # Find motion onset (velocity rises above threshold going backward from crossing)
        motion_start_idx = cross_idx
        for j in range(cross_idx, max(0, search_start_limit) - 1, -1):
            if max_vel[j] < config.velocity_threshold_rad_s:
                # Check if sustained stability
                stable_count = 0
                for k in range(j, max(0, j - min_stable_samples), -1):
                    if max_vel[k] < config.velocity_threshold_rad_s:
                        stable_count += 1
                    else:
                        break
                if stable_count >= min_stable_samples // 2:
                    motion_start_idx = j
                    break

        # Find motion offset (velocity drops below threshold going forward from crossing)
        motion_end_idx = cross_idx
        for j in range(cross_idx, min(n_samples, search_end_limit)):
            if max_vel[j] < config.velocity_threshold_rad_s:
                stable_count = 0
                for k in range(j, min(n_samples, j + min_stable_samples)):
                    if max_vel[k] < config.velocity_threshold_rad_s:
                        stable_count += 1
                    else:
                        break
                if stable_count >= min_stable_samples // 2:
                    motion_end_idx = j
                    break

        # Add margins
        seg_start_idx = max(0, motion_start_idx - margin_samples_before)
        seg_end_idx = min(n_samples - 1, motion_end_idx + margin_samples_after)

        # Ensure no overlap with adjacent transitions
        seg_start_idx = max(seg_start_idx, search_start_limit)
        seg_end_idx = min(seg_end_idx, search_end_limit)

        start_time = time_values[seg_start_idx]
        end_time = time_values[seg_end_idx]
        duration = end_time - start_time

        if config.min_segment_duration_s <= duration <= config.max_segment_duration_s:
            seg = SegmentBoundary(
                start_idx=seg_start_idx,
                end_idx=seg_end_idx,
                start_time_s=start_time,
                end_time_s=end_time,
                duration_s=duration,
                segment_type=trans_type,
                events={"grf_crossing": cross_idx},
                metadata={"crossing_time_s": cross_time}
            )
            segments.append(seg)

    # IQR filtering
    if config.use_iqr_filtering and len(segments) >= 4:
        segments, _, _ = filter_segments_by_duration_iqr(
            segments,
            config.iqr_multiplier,
            config.min_segment_duration_s,
            config.max_segment_duration_s
        )

    return segments


# =============================================================================
# High-Level Task Router
# =============================================================================

def segment_by_task(
    df: pd.DataFrame,
    task: str,
    config: Optional[Any] = None
) -> List[SegmentBoundary]:
    """Segment data using the appropriate archetype for the given task.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing required columns for the task's archetype.
    task : str
        Canonical task name (e.g., "level_walking", "jump", "sit_to_stand").
    config : Optional config
        Override default configuration. Must match expected archetype.

    Returns
    -------
    List[SegmentBoundary]
        Segmentation result using appropriate archetype.
    """
    archetype = TASK_ARCHETYPE_MAP.get(task)

    if archetype is None:
        # Unknown task, try gait as default
        archetype = SegmentationArchetype.GAIT

    if archetype == SegmentationArchetype.GAIT:
        cfg = config if isinstance(config, GaitSegmentationConfig) else GaitSegmentationConfig()
        return segment_gait_cycles(df, cfg)

    elif archetype == SegmentationArchetype.STANDING_ACTION:
        cfg = config if isinstance(config, StandingActionConfig) else StandingActionConfig()
        # Set require_flight_phase based on task
        if task == "jump" and not isinstance(config, StandingActionConfig):
            cfg = StandingActionConfig(require_flight_phase=True)
        return segment_standing_action_cycles(df, cfg, action_type=task)

    elif archetype == SegmentationArchetype.SIT_STAND_TRANSFER:
        cfg = config if isinstance(config, SitStandConfig) else SitStandConfig()
        transfer_type = task if task in ("sit_to_stand", "stand_to_sit") else "both"
        return segment_sit_stand_transfers(df, cfg, transfer_type=transfer_type)

    return []


__all__ = [
    # Enums
    "SegmentationArchetype",
    # Dataclasses
    "SegmentBoundary",
    "GaitSegmentationConfig",
    "StandingActionConfig",
    "SitStandConfig",
    # Mappings
    "TASK_ARCHETYPE_MAP",
    # Main functions
    "segment_gait_cycles",
    "segment_standing_action_cycles",
    "segment_sit_stand_transfers",
    "segment_by_task",
    # Utilities
    "estimate_sample_rate",
    "compute_max_joint_velocity",
    "filter_segments_by_duration",
    "filter_segments_by_duration_iqr",
    "remove_transition_segments",
]
