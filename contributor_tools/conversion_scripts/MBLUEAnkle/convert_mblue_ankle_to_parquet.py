#!/usr/bin/env python3
"""
Convert MBLUE Ankle OpenSim Processing dataset to standardized phase-normalized parquet format.

This script converts the MBLUEAnkleOpenSimProcessing dataset (MBLUE Ankle Exoskeleton Study)
to the LocoHub standardized format.

Data structure:
- 10 subjects (AB01-AB11, excluding AB07 who withdrew)
- Two conditions: 'bare' (no exoskeleton) and 'exo' (with ankle exoskeleton)
- Tasks: level walking (0.75, 1.0, 1.25 m/s), incline/decline walking (5, 10 deg),
         sit-to-stand/stand-to-sit, crouch, stair ascent/descent
- Data already phase-normalized to 101 points per stride

Output: Phase-normalized parquet file with 150 points per gait cycle.
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import interp1d
from scipy.io import loadmat
from tqdm import tqdm

# Configuration
NUM_POINTS = 150  # Target points per gait cycle (standard format)
SOURCE_POINTS = 101  # Points in source data
VICON_DATA_PATH = None  # Set via --vicon-path argument or auto-detected

# Mapping from task name to .mot file name prefix (without .mot extension) for BARE condition
BARE_TASK_TO_MOT_FILE = {
    'level_0x75': 'bare_level',
    'level_1x0': 'bare_level',
    'level_1x25': 'bare_level',
    'incline_5deg': 'bare_5deg_incline',
    'incline_10deg': 'bare_10deg_incline',
    'decline_5deg': 'bare_5deg_decline',
    'decline_10deg': 'bare_10deg_decline',
    'STS': 'bare_STS',
    'crouch': 'bare_crouch',
    'stairs': 'bare_stairs_corrected',  # Use corrected file with plate 7-11 data reassigned to 1-2
}

# For EXO condition, .mot file names are: exo_{filename_suffix}.mot
# The filename_suffix comes from FileInfo.mat for each subject/task
# For stairs, use exo_{suffix}_corrected.mot

# Force plate assignments for different tasks (from defineExternalLoadPrefixes.m)
# Format: (right_leg_plate, left_leg_plate)
FORCEPLATE_ASSIGNMENTS = {
    'level': (1, 2),      # level, incline, stairs
    'incline': (1, 2),
    'decline': (2, 1),    # decline swaps plates
    'STS': (4, 5),
    'crouch': (4, 5),
    'stairs': (1, 2),
}


def load_mot_file(mot_path: Path) -> Optional[pd.DataFrame]:
    """
    Load an OpenSim .mot file containing GRF and COP data.

    Args:
        mot_path: Path to the .mot file

    Returns:
        DataFrame with time and force plate columns, or None if file not found
    """
    if not mot_path.exists():
        return None

    try:
        # Read header to find where data starts
        with open(mot_path, 'r') as f:
            lines = f.readlines()

        # Find endheader line
        header_end = 0
        for i, line in enumerate(lines):
            if 'endheader' in line.lower():
                header_end = i
                break

        # Column names are on the line after endheader
        columns = lines[header_end + 1].strip().split('\t')

        # Read data starting after the column names
        data_start = header_end + 2
        data_lines = lines[data_start:]

        # Parse data
        data = []
        for line in data_lines:
            if line.strip():
                values = [float(x) for x in line.strip().split('\t')]
                data.append(values)

        df = pd.DataFrame(data, columns=columns)
        return df

    except Exception as e:
        print(f"  Warning: Could not load {mot_path}: {e}")
        return None


def get_forceplate_assignment(task_key: str) -> Tuple[int, int]:
    """
    Get force plate numbers for right and left legs based on task.

    Args:
        task_key: Task name (e.g., 'level_1x0', 'decline_5deg')

    Returns:
        Tuple of (right_plate_num, left_plate_num)
    """
    if 'decline' in task_key:
        return FORCEPLATE_ASSIGNMENTS['decline']
    elif 'incline' in task_key:
        return FORCEPLATE_ASSIGNMENTS['incline']
    elif 'level' in task_key:
        return FORCEPLATE_ASSIGNMENTS['level']
    elif 'STS' in task_key or 'sit' in task_key or 'stand' in task_key:
        return FORCEPLATE_ASSIGNMENTS['STS']
    elif 'crouch' in task_key:
        return FORCEPLATE_ASSIGNMENTS['crouch']
    elif 'stair' in task_key or 'ascent' in task_key or 'descent' in task_key:
        return FORCEPLATE_ASSIGNMENTS['stairs']
    else:
        return (1, 2)  # Default


def extract_cop_for_stride(
    mot_df: pd.DataFrame,
    start_time: float,
    end_time: float,
    plate_num: int,
    num_points: int = NUM_POINTS,
    negate_anterior: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract and phase-normalize COP data for a single stride.

    COP is extracted and swapped: anterior comes from pz (medial-lateral in OpenSim),
    lateral comes from px (anterior-posterior in OpenSim).

    Args:
        mot_df: DataFrame from .mot file
        start_time: Stride start time (heel strike)
        end_time: Stride end time (next heel strike)
        plate_num: Force plate number (1, 2, etc.)
        num_points: Number of points to interpolate to
        negate_anterior: If True, negate anterior COP (for decline walking where subject walks backwards)

    Returns:
        Tuple of (cop_ap, cop_ml) arrays, each of length num_points
        Values are in meters. Returns NaN arrays if extraction fails.
    """
    cop_ap = np.full(num_points, np.nan)
    cop_ml = np.full(num_points, np.nan)

    if mot_df is None:
        return cop_ml, cop_ap  # Both are NaN arrays, sign doesn't matter

    # Column names for this force plate
    col_px = f'ground_force{plate_num}_px'  # Will become lateral
    col_pz = f'ground_force{plate_num}_pz'  # Will become -anterior
    col_vy = f'ground_force{plate_num}_vy'  # Vertical GRF for masking

    if col_px not in mot_df.columns or col_pz not in mot_df.columns:
        return cop_ml, cop_ap  # Both are NaN arrays, sign doesn't matter

    # Extract time window
    mask = (mot_df['time'] >= start_time) & (mot_df['time'] <= end_time)
    stride_data = mot_df.loc[mask].copy()

    if len(stride_data) < 2:
        return cop_ml, cop_ap  # Both are NaN arrays, sign doesn't matter

    # Get COP data
    time_raw = stride_data['time'].values
    cop_px_raw = stride_data[col_px].values
    cop_pz_raw = stride_data[col_pz].values

    # Mask COP when foot is not in contact (GRF < threshold)
    # COP is meaningless during swing phase
    if col_vy in mot_df.columns:
        grf_vy = stride_data[col_vy].values
        contact_mask = np.abs(grf_vy) > 20.0  # 20N threshold
        cop_px_raw = np.where(contact_mask, cop_px_raw, np.nan)
        cop_pz_raw = np.where(contact_mask, cop_pz_raw, np.nan)

    # Zero COP to heel strike position (make foot-relative)
    # Find first valid contact point and subtract to make relative to heel position
    valid_px = ~np.isnan(cop_px_raw)
    valid_pz = ~np.isnan(cop_pz_raw)
    if np.sum(valid_px) > 0:
        cop_px_offset = cop_px_raw[valid_px][0]
        cop_px_raw = cop_px_raw - cop_px_offset
    if np.sum(valid_pz) > 0:
        cop_pz_offset = cop_pz_raw[valid_pz][0]
        cop_pz_raw = cop_pz_raw - cop_pz_offset

    # Interpolate to standard number of points
    try:
        t_norm = np.linspace(0, 1, len(time_raw))
        t_target = np.linspace(0, 1, num_points)

        # For COP, use linear interpolation with NaN handling
        valid_px = ~np.isnan(cop_px_raw)
        valid_pz = ~np.isnan(cop_pz_raw)

        if np.sum(valid_px) > 1:
            interp_px = interp1d(t_norm[valid_px], cop_px_raw[valid_px],
                                kind='linear', fill_value=np.nan, bounds_error=False)
            cop_ap = interp_px(t_target)

        if np.sum(valid_pz) > 1:
            interp_pz = interp1d(t_norm[valid_pz], cop_pz_raw[valid_pz],
                                kind='linear', fill_value=np.nan, bounds_error=False)
            cop_ml = interp_pz(t_target)

    except Exception:
        pass

    # Swap axes: anterior from pz, lateral from px
    # Negate anterior only for decline walking (participants walk backwards)
    anterior = -cop_ml if negate_anterior else cop_ml
    return anterior, cop_ap


# Subject metadata (mass in kg, sex, age, height in mm)
SUBJECT_INFO = {
    'AB01': {'mass': 83.3, 'sex': 'M', 'age': 28, 'height_mm': 1778},
    'AB02': {'mass': 70.6, 'sex': 'F', 'age': 26, 'height_mm': 1575},
    'AB03': {'mass': 64.4, 'sex': 'F', 'age': 57, 'height_mm': 1625},
    'AB04': {'mass': 69.1, 'sex': 'M', 'age': 24, 'height_mm': 1752},
    'AB05': {'mass': 72.3, 'sex': 'M', 'age': 56, 'height_mm': 1803},
    'AB06': {'mass': 75.9, 'sex': 'M', 'age': 34, 'height_mm': 1828},
    # AB07 withdrew from the study
    'AB08': {'mass': 60.1, 'sex': 'F', 'age': 21, 'height_mm': 1651},
    'AB09': {'mass': 64.8, 'sex': 'F', 'age': 36, 'height_mm': 1676},
    'AB10': {'mass': 54.3, 'sex': 'F', 'age': 25, 'height_mm': 1524},
    'AB11': {'mass': 68.0, 'sex': 'M', 'age': 26, 'height_mm': 1770},
}

# Task mapping: source task name -> (standard_task, task_id, speed_m_s)
TASK_MAPPING = {
    # Level walking
    'level_0x75': ('level_walking', 'level_0.75ms', 0.75),
    'level_1x0': ('level_walking', 'level_1.0ms', 1.0),
    'level_1x25': ('level_walking', 'level_1.25ms', 1.25),
    # Incline/decline walking
    'incline_5deg': ('incline_walking', 'incline_5deg', None),
    'incline_10deg': ('incline_walking', 'incline_10deg', None),
    'decline_5deg': ('decline_walking', 'decline_5deg', None),
    'decline_10deg': ('decline_walking', 'decline_10deg', None),
    # Sit-to-stand transfers (nested under STS)
    'sit_stand': ('sit_to_stand', 'sit_to_stand', None),
    'stand_sit': ('stand_to_sit', 'stand_to_sit', None),
    # Crouch (similar to squat)
    'crouch': ('squat', 'crouch', None),
    # Stairs (nested under stairs)
    'ascent': ('stair_ascent', 'stair_ascent', None),
    'descent': ('stair_descent', 'stair_descent', None),
}


def circular_phase_shift(data: np.ndarray, shift_percent: float = 50.0) -> np.ndarray:
    """
    Circularly shift phase-normalized data by a percentage of the gait cycle.

    In gait, the contralateral leg is approximately 50% out of phase with the
    ipsilateral leg. When data is phase-normalized per-leg (heel strike to heel
    strike), the contra data needs to be shifted to align with the ipsi phase.

    Design Decision: 50% Phase Shift vs Time-Based Synchronization
    ---------------------------------------------------------------
    The source data has timestamps (time_l, time_r) that could enable precise
    time-based synchronization. Analysis showed the actual phase relationship
    varies from ~49.6% to ~51.3% stride-to-stride. However, time-based sync
    has complications:

    1. Boundary conditions: Left and right leg recordings may start/end at
       different times, leaving some strides without overlapping contra data.
       E.g., Left stride 0 (80.6-81.8s) has no overlapping right stride
       (right starts at 81.2s).

    2. Stride count mismatch: Left and right legs may have different numbers
       of detected strides, complicating index-based pairing.

    3. Complexity vs benefit: For this treadmill walking data, the actual
       phase relationship is very close to 50% (within ~1%), so the added
       complexity of time-based sync provides minimal benefit.

    The 50% approximation is standard in gait analysis literature and is
    sufficiently accurate for steady-state treadmill walking. For datasets
    with asymmetric gait or overground walking, time-based sync may be
    worth implementing.

    Args:
        data: Phase-normalized data array (num_points,) or (num_points, N)
        shift_percent: Percentage of gait cycle to shift (default 50%)

    Returns:
        Circularly shifted data array (same shape as input)
    """
    if data.ndim == 1:
        num_points = len(data)
        shift_points = int(round(num_points * shift_percent / 100.0))
        return np.roll(data, shift_points)
    else:
        num_points = data.shape[0]
        shift_points = int(round(num_points * shift_percent / 100.0))
        return np.roll(data, shift_points, axis=0)


def time_sync_contra_data(
    ipsi_times: np.ndarray,
    contra_times: np.ndarray,
    contra_data: np.ndarray,
    num_points: int = NUM_POINTS
) -> np.ndarray:
    """
    Synchronize contralateral data to ipsilateral timing using time-based lookup.

    Instead of assuming a fixed 50% phase offset, this finds what the contra leg
    was actually doing at each ipsi time point by interpolating across contra strides.

    Args:
        ipsi_times: Time array for ipsi stride (101 points)
        contra_times: Time array for all contra strides (101 x n_contra_strides)
        contra_data: Data array for all contra strides (101 x n_contra_strides)
        num_points: Number of output points (default 150)

    Returns:
        Synchronized contra data interpolated to num_points
    """
    if ipsi_times is None or contra_times is None or contra_data is None:
        return np.full(num_points, np.nan)

    # Handle 1D arrays
    if contra_times.ndim == 1:
        contra_times = contra_times.reshape(-1, 1)
    if contra_data.ndim == 1:
        contra_data = contra_data.reshape(-1, 1)

    n_contra_strides = contra_times.shape[1]
    if n_contra_strides == 0:
        return np.full(num_points, np.nan)

    # Get valid ipsi times
    valid_ipsi = ~np.isnan(ipsi_times)
    if np.sum(valid_ipsi) < 2:
        return np.full(num_points, np.nan)

    ipsi_t = ipsi_times[valid_ipsi]
    t_start, t_end = ipsi_t[0], ipsi_t[-1]

    # Build a combined time->value mapping from all contra strides
    # that overlap with the ipsi time range
    all_times = []
    all_values = []

    for stride_idx in range(n_contra_strides):
        contra_t = contra_times[:, stride_idx]
        contra_v = contra_data[:, stride_idx]

        valid = ~np.isnan(contra_t) & ~np.isnan(contra_v)
        if np.sum(valid) < 2:
            continue

        ct = contra_t[valid]
        cv = contra_v[valid]

        # Check if this contra stride overlaps with ipsi time range
        if ct[-1] < t_start or ct[0] > t_end:
            continue

        all_times.extend(ct)
        all_values.extend(cv)

    if len(all_times) < 2:
        return np.full(num_points, np.nan)

    # Sort by time and remove duplicates (keep first occurrence)
    sorted_indices = np.argsort(all_times)
    all_times = np.array(all_times)[sorted_indices]
    all_values = np.array(all_values)[sorted_indices]

    # Remove duplicates
    _, unique_idx = np.unique(all_times, return_index=True)
    all_times = all_times[unique_idx]
    all_values = all_values[unique_idx]

    if len(all_times) < 2:
        return np.full(num_points, np.nan)

    # Interpolate contra data at ipsi time points
    try:
        interp_func = interp1d(all_times, all_values, kind='linear',
                               bounds_error=False, fill_value=np.nan)

        # Generate target times at num_points resolution
        target_times = np.linspace(t_start, t_end, num_points)
        synced_data = interp_func(target_times)

        return synced_data
    except Exception:
        return np.full(num_points, np.nan)


def interpolate_to_phase(data: np.ndarray, num_points: int = NUM_POINTS) -> np.ndarray:
    """
    Interpolate time-series data from 101 to 150 points.

    Args:
        data: Input data array (101 points per stride, N strides)
        num_points: Number of output points (default 150)

    Returns:
        Interpolated data array (num_points x N)
    """
    if data.ndim == 1:
        data = data.reshape(-1, 1)

    n_source = data.shape[0]
    n_strides = data.shape[1]

    if n_source < 2:
        return np.full((num_points, n_strides), np.nan)

    # Create interpolation
    x_original = np.linspace(0, 100, n_source)
    x_target = np.linspace(0, 100, num_points)

    result = np.zeros((num_points, n_strides))
    for i in range(n_strides):
        stride_data = data[:, i]
        valid_mask = ~np.isnan(stride_data)
        if np.sum(valid_mask) < 2:
            result[:, i] = np.nan
            continue
        try:
            interp_func = interp1d(x_original[valid_mask], stride_data[valid_mask],
                                   kind='linear', fill_value='extrapolate')
            result[:, i] = interp_func(x_target)
        except Exception:
            result[:, i] = np.nan

    return result


def compute_velocity_from_angle(angle_rad: np.ndarray, stride_duration_s: float) -> np.ndarray:
    """
    Compute angular velocity from angle data using gradient.

    Args:
        angle_rad: Angle data in radians (150 points)
        stride_duration_s: Duration of stride in seconds

    Returns:
        Angular velocity in rad/s
    """
    if len(angle_rad) < 2 or stride_duration_s <= 0:
        return np.full_like(angle_rad, np.nan)
    dt = stride_duration_s / (len(angle_rad) - 1)
    velocity = np.gradient(angle_rad) / dt
    return velocity


def compute_acceleration_from_velocity(velocity_rad_s: np.ndarray, stride_duration_s: float) -> np.ndarray:
    """Compute angular acceleration from velocity data using gradient."""
    if len(velocity_rad_s) < 2 or stride_duration_s <= 0:
        return np.full_like(velocity_rad_s, np.nan)
    dt = stride_duration_s / (len(velocity_rad_s) - 1)
    acceleration = np.gradient(velocity_rad_s) / dt
    return acceleration


def get_nested_field(data, *keys):
    """
    Safely access nested MATLAB struct fields.

    Args:
        data: MATLAB struct or array
        *keys: Sequence of field names to traverse

    Returns:
        The nested field value or None if not found
    """
    try:
        result = data
        for key in keys:
            if hasattr(result, 'dtype') and result.dtype.names and key in result.dtype.names:
                result = result[key]
                # Unwrap nested arrays
                while hasattr(result, 'shape') and result.shape == (1, 1):
                    result = result[0, 0]
            else:
                return None
        return result
    except (KeyError, IndexError, TypeError):
        return None


def extract_stride_duration(task_data, leg_side: str, stride_idx: int) -> float:
    """
    Extract stride duration from time data.

    Args:
        task_data: Task data struct
        leg_side: 'l' or 'r'
        stride_idx: Stride index

    Returns:
        Stride duration in seconds (default 1.0 if not available)
    """
    time_key = f'time_{leg_side}'
    if hasattr(task_data, 'dtype') and task_data.dtype.names and time_key in task_data.dtype.names:
        time_data = task_data[time_key]
        if time_data.size > 0:
            # time_data may have different shapes
            if time_data.ndim == 2 and stride_idx < time_data.shape[1]:
                stride_time = time_data[:, stride_idx]
                valid = ~np.isnan(stride_time)
                if np.sum(valid) > 1:
                    return stride_time[valid][-1] - stride_time[valid][0]
            elif time_data.ndim == 1:
                return float(time_data[-1] - time_data[0]) if len(time_data) > 1 else 1.0
    # Default stride duration estimate (typical walking ~1.0s)
    return 1.0


def extract_stride_times(task_data, leg_side: str, stride_idx: int) -> Tuple[float, float]:
    """
    Extract start and end times for a stride.

    Args:
        task_data: Task data struct
        leg_side: 'l' or 'r'
        stride_idx: Stride index

    Returns:
        Tuple of (start_time, end_time) in seconds, or (NaN, NaN) if not available
    """
    time_key = f'time_{leg_side}'
    if hasattr(task_data, 'dtype') and task_data.dtype.names and time_key in task_data.dtype.names:
        time_data = task_data[time_key]
        if time_data.size > 0 and time_data.ndim == 2 and stride_idx < time_data.shape[1]:
            stride_time = time_data[:, stride_idx]
            valid = ~np.isnan(stride_time)
            if np.sum(valid) > 1:
                return float(stride_time[valid][0]), float(stride_time[valid][-1])
    return np.nan, np.nan


def process_gait_task(
    task_data,
    subject_id: str,
    subject_mass: float,
    task: str,
    task_id: str,
    speed_m_s: Optional[float],
    condition: str,
    step_offset: int = 0,
    mot_df: Optional[pd.DataFrame] = None,
    task_key: str = ''
) -> Tuple[List[pd.DataFrame], int]:
    """
    Process a gait task (walking, stairs) with left/right strides.

    Args:
        task_data: MATLAB struct with task data
        subject_id: Subject identifier
        subject_mass: Subject mass in kg
        task: Standardized task name
        task_id: Task identifier
        speed_m_s: Walking speed if applicable
        condition: 'bare' or 'exo'
        step_offset: Starting step number
        mot_df: DataFrame from .mot file containing GRF/COP data (optional)
        task_key: Original task key for force plate assignment (e.g., 'level_1x0')

    Returns:
        Tuple of (list of stride DataFrames, next step number)
    """
    strides = []
    step_num = step_offset
    deg2rad = np.pi / 180.0
    body_weight_N = subject_mass * 9.81

    # Determine exo state for task_info
    exo_state = 'no_exo' if condition == 'bare' else 'powered'

    # Build subject metadata (demographics only, exo info goes in task_info)
    info = SUBJECT_INFO.get(subject_id, {})
    subject_metadata = f"weight_kg:{subject_mass:.1f}"
    if 'sex' in info:
        subject_metadata += f",sex:{info['sex']}"
    if 'age' in info:
        subject_metadata += f",age:{info['age']}"

    # Get force plate assignment for COP extraction
    right_plate, left_plate = get_forceplate_assignment(task_key)

    for leg_side in ['l', 'r']:
        # Determine which force plate this leg uses
        ipsi_plate = left_plate if leg_side == 'l' else right_plate
        contra_plate = right_plate if leg_side == 'l' else left_plate
        ipsi = leg_side
        contra = 'r' if leg_side == 'l' else 'l'

        # Get angle data to determine number of strides for this leg
        hip_key = f'hip_flexion_{ipsi}'
        if not (hasattr(task_data, 'dtype') and task_data.dtype.names and hip_key in task_data.dtype.names):
            continue

        hip_ipsi_data = task_data[hip_key]
        if hip_ipsi_data.size == 0:
            continue

        n_strides_ipsi = hip_ipsi_data.shape[1] if hip_ipsi_data.ndim == 2 else 1

        # Get contralateral data and its stride count (may differ from ipsi)
        hip_contra_key = f'hip_flexion_{contra}'
        hip_contra_data = task_data[hip_contra_key] if hip_contra_key in task_data.dtype.names else None
        n_strides_contra = hip_contra_data.shape[1] if (hip_contra_data is not None and hip_contra_data.ndim == 2) else (1 if hip_contra_data is not None else 0)

        for stride_idx in range(n_strides_ipsi):
            # Extract stride duration
            stride_duration_s = extract_stride_duration(task_data, ipsi, stride_idx)

            # Extract stride times for COP lookup
            stride_start, stride_end = extract_stride_times(task_data, ipsi, stride_idx)

            # Extract COP for ipsilateral leg
            # Negate anterior only for decline walking (participants walk backwards)
            is_decline = task == 'decline_walking'
            cop_ap_ipsi, cop_ml_ipsi = extract_cop_for_stride(
                mot_df, stride_start, stride_end, ipsi_plate, NUM_POINTS,
                negate_anterior=is_decline
            )

            # For contra COP extraction
            # For stairs: extract during ipsi time window (no phase shift needed)
            # For walking: extract from contra stride, then phase shift
            is_stair = task in ['stair_ascent', 'stair_descent']

            if is_stair:
                # For stairs, extract contra COP during the ipsi stride time window
                # This gives us concurrent data without needing phase shift
                cop_ap_contra, cop_ml_contra = extract_cop_for_stride(
                    mot_df, stride_start, stride_end, contra_plate, NUM_POINTS,
                    negate_anterior=is_decline
                )
            else:
                # For walking, use contra stride times and phase shift
                contra_idx = min(stride_idx, n_strides_contra - 1) if n_strides_contra > 0 else 0
                contra_start, contra_end = extract_stride_times(task_data, contra, contra_idx)
                cop_ap_contra_raw, cop_ml_contra_raw = extract_cop_for_stride(
                    mot_df, contra_start, contra_end, contra_plate, NUM_POINTS,
                    negate_anterior=is_decline
                )
                # Apply 50% phase shift to contra COP (same as other contra data)
                cop_ap_contra = circular_phase_shift(cop_ap_contra_raw)
                cop_ml_contra = circular_phase_shift(cop_ml_contra_raw)

            # Extract and interpolate kinematics (angles in degrees -> radians)
            # For stairs, use time-based sync; for walking, use 50% phase shift
            use_time_sync = task in ['stair_ascent', 'stair_descent']

            # Get time data for time-based synchronization
            ipsi_time_key = f'time_{ipsi}'
            contra_time_key = f'time_{contra}'
            ipsi_times = None
            contra_times = None

            if use_time_sync:
                if ipsi_time_key in task_data.dtype.names:
                    time_data = task_data[ipsi_time_key]
                    if time_data.ndim == 2 and stride_idx < time_data.shape[1]:
                        ipsi_times = time_data[:, stride_idx]
                if contra_time_key in task_data.dtype.names:
                    contra_times = task_data[contra_time_key]

            # Hip flexion
            hip_ipsi_deg = hip_ipsi_data[:, stride_idx] if hip_ipsi_data.ndim == 2 else hip_ipsi_data
            hip_ipsi_rad = interpolate_to_phase(hip_ipsi_deg * deg2rad).flatten()

            if use_time_sync and ipsi_times is not None and hip_contra_data is not None:
                # Time-based sync: find what contra leg was doing during ipsi stride
                hip_contra_rad = time_sync_contra_data(
                    ipsi_times, contra_times, hip_contra_data * deg2rad, NUM_POINTS
                )
            else:
                # Standard approach: index-based pairing with phase shift
                if hip_contra_data is not None and hip_contra_data.size > 0:
                    if hip_contra_data.ndim == 2:
                        contra_idx = min(stride_idx, hip_contra_data.shape[1] - 1)
                        hip_contra_deg = hip_contra_data[:, contra_idx]
                    else:
                        hip_contra_deg = hip_contra_data
                else:
                    hip_contra_deg = np.full_like(hip_ipsi_deg, np.nan)
                hip_contra_unshifted = interpolate_to_phase(hip_contra_deg * deg2rad).flatten()
                hip_contra_rad = circular_phase_shift(hip_contra_unshifted)

            # Knee angle (negate: source has extension positive, we want flexion positive)
            knee_ipsi_data = task_data[f'knee_angle_{ipsi}']
            knee_contra_data = task_data[f'knee_angle_{contra}'] if f'knee_angle_{contra}' in task_data.dtype.names else None
            knee_ipsi_deg = knee_ipsi_data[:, stride_idx] if knee_ipsi_data.ndim == 2 else knee_ipsi_data
            knee_ipsi_rad = interpolate_to_phase(-knee_ipsi_deg * deg2rad).flatten()

            if use_time_sync and ipsi_times is not None and knee_contra_data is not None:
                knee_contra_rad = time_sync_contra_data(
                    ipsi_times, contra_times, -knee_contra_data * deg2rad, NUM_POINTS
                )
            else:
                if knee_contra_data is not None and knee_contra_data.size > 0:
                    if knee_contra_data.ndim == 2:
                        contra_idx = min(stride_idx, knee_contra_data.shape[1] - 1)
                        knee_contra_deg = knee_contra_data[:, contra_idx]
                    else:
                        knee_contra_deg = knee_contra_data
                else:
                    knee_contra_deg = np.full_like(knee_ipsi_deg, np.nan)
                knee_contra_unshifted = interpolate_to_phase(-knee_contra_deg * deg2rad).flatten()
                knee_contra_rad = circular_phase_shift(knee_contra_unshifted)

            # Ankle dorsiflexion
            ankle_ipsi_data = task_data[f'ankle_angle_{ipsi}']
            ankle_contra_data = task_data[f'ankle_angle_{contra}'] if f'ankle_angle_{contra}' in task_data.dtype.names else None
            ankle_ipsi_deg = ankle_ipsi_data[:, stride_idx] if ankle_ipsi_data.ndim == 2 else ankle_ipsi_data
            ankle_ipsi_rad = interpolate_to_phase(ankle_ipsi_deg * deg2rad).flatten()

            if use_time_sync and ipsi_times is not None and ankle_contra_data is not None:
                ankle_contra_rad = time_sync_contra_data(
                    ipsi_times, contra_times, ankle_contra_data * deg2rad, NUM_POINTS
                )
            else:
                if ankle_contra_data is not None and ankle_contra_data.size > 0:
                    if ankle_contra_data.ndim == 2:
                        contra_idx = min(stride_idx, ankle_contra_data.shape[1] - 1)
                        ankle_contra_deg = ankle_contra_data[:, contra_idx]
                    else:
                        ankle_contra_deg = ankle_contra_data
                else:
                    ankle_contra_deg = np.full_like(ankle_ipsi_deg, np.nan)
                ankle_contra_unshifted = interpolate_to_phase(ankle_contra_deg * deg2rad).flatten()
                ankle_contra_rad = circular_phase_shift(ankle_contra_unshifted)

            # Extract pelvis_tilt (global, same for both legs)
            pelvis_tilt_rad = np.zeros(NUM_POINTS)
            if 'pelvis_tilt' in task_data.dtype.names:
                pelvis_data = task_data['pelvis_tilt']
                if pelvis_data.ndim == 2 and stride_idx < pelvis_data.shape[1]:
                    pelvis_tilt_rad = interpolate_to_phase(pelvis_data[:, stride_idx] * deg2rad).flatten()
                elif pelvis_data.ndim == 1:
                    pelvis_tilt_rad = interpolate_to_phase(pelvis_data * deg2rad).flatten()

            # Compute segment angles from kinematic chain
            # thigh_angle = pelvis_tilt + hip_flexion
            # shank_angle = thigh_angle - knee_flexion (knee is flexion-positive)
            # foot_angle = shank_angle + ankle_dorsiflexion
            thigh_ipsi_rad = pelvis_tilt_rad + hip_ipsi_rad
            thigh_contra_rad = pelvis_tilt_rad + hip_contra_rad
            shank_ipsi_rad = thigh_ipsi_rad - knee_ipsi_rad
            shank_contra_rad = thigh_contra_rad - knee_contra_rad
            foot_ipsi_rad = shank_ipsi_rad + ankle_ipsi_rad
            foot_contra_rad = shank_contra_rad + ankle_contra_rad

            # Compute velocities from angles
            # For time-synced data, angles are already aligned so compute directly
            # For phase-shifted data, we already computed velocity before shifting
            hip_vel_ipsi = compute_velocity_from_angle(hip_ipsi_rad, stride_duration_s)
            hip_vel_contra = compute_velocity_from_angle(hip_contra_rad, stride_duration_s)
            knee_vel_ipsi = compute_velocity_from_angle(knee_ipsi_rad, stride_duration_s)
            knee_vel_contra = compute_velocity_from_angle(knee_contra_rad, stride_duration_s)
            ankle_vel_ipsi = compute_velocity_from_angle(ankle_ipsi_rad, stride_duration_s)
            ankle_vel_contra = compute_velocity_from_angle(ankle_contra_rad, stride_duration_s)

            # Compute segment velocities
            pelvis_vel = compute_velocity_from_angle(pelvis_tilt_rad, stride_duration_s)
            thigh_vel_ipsi = compute_velocity_from_angle(thigh_ipsi_rad, stride_duration_s)
            thigh_vel_contra = compute_velocity_from_angle(thigh_contra_rad, stride_duration_s)
            shank_vel_ipsi = compute_velocity_from_angle(shank_ipsi_rad, stride_duration_s)
            shank_vel_contra = compute_velocity_from_angle(shank_contra_rad, stride_duration_s)
            foot_vel_ipsi = compute_velocity_from_angle(foot_ipsi_rad, stride_duration_s)
            foot_vel_contra = compute_velocity_from_angle(foot_contra_rad, stride_duration_s)

            # Compute accelerations
            hip_acc_ipsi = compute_acceleration_from_velocity(hip_vel_ipsi, stride_duration_s)
            hip_acc_contra = compute_acceleration_from_velocity(hip_vel_contra, stride_duration_s)
            knee_acc_ipsi = compute_acceleration_from_velocity(knee_vel_ipsi, stride_duration_s)
            knee_acc_contra = compute_acceleration_from_velocity(knee_vel_contra, stride_duration_s)
            ankle_acc_ipsi = compute_acceleration_from_velocity(ankle_vel_ipsi, stride_duration_s)
            ankle_acc_contra = compute_acceleration_from_velocity(ankle_vel_contra, stride_duration_s)

            # Extract and interpolate moments (Nm -> Nm/kg)
            # Note: Source moments are in Nm, need to normalize by mass
            hip_mom_ipsi_key = f'hip_flexion_{ipsi}_moment'
            hip_mom_contra_key = f'hip_flexion_{contra}_moment'
            knee_mom_ipsi_key = f'knee_angle_{ipsi}_moment'
            knee_mom_contra_key = f'knee_angle_{contra}_moment'
            ankle_mom_ipsi_key = f'ankle_angle_{ipsi}_moment'
            ankle_mom_contra_key = f'ankle_angle_{contra}_moment'

            hip_mom_ipsi = np.full(NUM_POINTS, np.nan)
            hip_mom_contra = np.full(NUM_POINTS, np.nan)
            knee_mom_ipsi = np.full(NUM_POINTS, np.nan)
            knee_mom_contra = np.full(NUM_POINTS, np.nan)
            ankle_mom_ipsi = np.full(NUM_POINTS, np.nan)
            ankle_mom_contra = np.full(NUM_POINTS, np.nan)

            if hip_mom_ipsi_key in task_data.dtype.names:
                mom_data = task_data[hip_mom_ipsi_key]
                if mom_data.ndim == 2 and stride_idx < mom_data.shape[1]:
                    hip_mom_ipsi = interpolate_to_phase(mom_data[:, stride_idx] / subject_mass).flatten()
                elif mom_data.ndim == 1:
                    hip_mom_ipsi = interpolate_to_phase(mom_data / subject_mass).flatten()

            if hip_mom_contra_key in task_data.dtype.names:
                mom_data = task_data[hip_mom_contra_key]
                if use_time_sync and ipsi_times is not None and mom_data is not None:
                    hip_mom_contra = time_sync_contra_data(
                        ipsi_times, contra_times, mom_data / subject_mass, NUM_POINTS
                    )
                elif mom_data.ndim == 2 and mom_data.shape[1] > 0:
                    contra_idx = min(stride_idx, mom_data.shape[1] - 1)
                    hip_mom_contra = circular_phase_shift(interpolate_to_phase(mom_data[:, contra_idx] / subject_mass).flatten())
                elif mom_data.ndim == 1:
                    hip_mom_contra = circular_phase_shift(interpolate_to_phase(mom_data / subject_mass).flatten())

            if knee_mom_ipsi_key in task_data.dtype.names:
                mom_data = task_data[knee_mom_ipsi_key]
                if mom_data.ndim == 2 and stride_idx < mom_data.shape[1]:
                    # Negate knee moment for flexion-positive convention
                    knee_mom_ipsi = interpolate_to_phase(-mom_data[:, stride_idx] / subject_mass).flatten()
                elif mom_data.ndim == 1:
                    knee_mom_ipsi = interpolate_to_phase(-mom_data / subject_mass).flatten()

            if knee_mom_contra_key in task_data.dtype.names:
                mom_data = task_data[knee_mom_contra_key]
                if use_time_sync and ipsi_times is not None and mom_data is not None:
                    knee_mom_contra = time_sync_contra_data(
                        ipsi_times, contra_times, -mom_data / subject_mass, NUM_POINTS
                    )
                elif mom_data.ndim == 2 and mom_data.shape[1] > 0:
                    contra_idx = min(stride_idx, mom_data.shape[1] - 1)
                    knee_mom_contra = circular_phase_shift(interpolate_to_phase(-mom_data[:, contra_idx] / subject_mass).flatten())
                elif mom_data.ndim == 1:
                    knee_mom_contra = circular_phase_shift(interpolate_to_phase(-mom_data / subject_mass).flatten())

            if ankle_mom_ipsi_key in task_data.dtype.names:
                mom_data = task_data[ankle_mom_ipsi_key]
                if mom_data.ndim == 2 and stride_idx < mom_data.shape[1]:
                    ankle_mom_ipsi = interpolate_to_phase(mom_data[:, stride_idx] / subject_mass).flatten()
                elif mom_data.ndim == 1:
                    ankle_mom_ipsi = interpolate_to_phase(mom_data / subject_mass).flatten()

            if ankle_mom_contra_key in task_data.dtype.names:
                mom_data = task_data[ankle_mom_contra_key]
                if use_time_sync and ipsi_times is not None and mom_data is not None:
                    ankle_mom_contra = time_sync_contra_data(
                        ipsi_times, contra_times, mom_data / subject_mass, NUM_POINTS
                    )
                elif mom_data.ndim == 2 and mom_data.shape[1] > 0:
                    contra_idx = min(stride_idx, mom_data.shape[1] - 1)
                    ankle_mom_contra = circular_phase_shift(interpolate_to_phase(mom_data[:, contra_idx] / subject_mass).flatten())
                elif mom_data.ndim == 1:
                    ankle_mom_contra = circular_phase_shift(interpolate_to_phase(mom_data / subject_mass).flatten())

            # Extract and interpolate GRF (N -> BW)
            grf_ipsi_key = f'ForceN_{ipsi}'
            grf_contra_key = f'ForceN_{contra}'

            grf_vert_ipsi = np.full(NUM_POINTS, np.nan)
            grf_vert_contra = np.full(NUM_POINTS, np.nan)

            if grf_ipsi_key in task_data.dtype.names:
                grf_data = task_data[grf_ipsi_key]
                if grf_data.ndim == 2 and stride_idx < grf_data.shape[1]:
                    grf_vert_ipsi = interpolate_to_phase(grf_data[:, stride_idx] / body_weight_N).flatten()
                elif grf_data.ndim == 1:
                    grf_vert_ipsi = interpolate_to_phase(grf_data / body_weight_N).flatten()

            if grf_contra_key in task_data.dtype.names:
                grf_data = task_data[grf_contra_key]
                if use_time_sync and ipsi_times is not None and grf_data is not None:
                    grf_vert_contra = time_sync_contra_data(
                        ipsi_times, contra_times, grf_data / body_weight_N, NUM_POINTS
                    )
                elif grf_data.ndim == 2 and grf_data.shape[1] > 0:
                    contra_idx = min(stride_idx, grf_data.shape[1] - 1)
                    grf_vert_contra = circular_phase_shift(interpolate_to_phase(grf_data[:, contra_idx] / body_weight_N).flatten())
                elif grf_data.ndim == 1:
                    grf_vert_contra = circular_phase_shift(interpolate_to_phase(grf_data / body_weight_N).flatten())

            # Build task_info string (includes exo metadata per reference spec)
            info_parts = [f"leg:{leg_side}"]
            if speed_m_s is not None:
                info_parts.append(f"speed_m_s:{speed_m_s}")
            info_parts.append(f"exo_state:{exo_state}")
            if exo_state == 'powered':
                info_parts.append("exo_joints:ankle")
            task_info_str = ",".join(info_parts)

            # Phase values
            phase = np.linspace(0, 100, NUM_POINTS)
            phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)

            # Mask COP where GRF is below threshold (swing phase)
            # COP is only meaningful during stance when foot is in contact
            GRF_THRESHOLD_BW = 0.05  # 5% body weight
            cop_ap_ipsi = np.where(grf_vert_ipsi > GRF_THRESHOLD_BW, cop_ap_ipsi, np.nan)
            cop_ml_ipsi = np.where(grf_vert_ipsi > GRF_THRESHOLD_BW, cop_ml_ipsi, np.nan)
            cop_ap_contra = np.where(grf_vert_contra > GRF_THRESHOLD_BW, cop_ap_contra, np.nan)
            cop_ml_contra = np.where(grf_vert_contra > GRF_THRESHOLD_BW, cop_ml_contra, np.nan)

            # Create stride DataFrame
            stride_df = pd.DataFrame({
                'subject': f"MBLUE_{subject_id}",
                'subject_metadata': subject_metadata,
                'task': task,
                'task_id': task_id,
                'task_info': task_info_str,
                'step': f"{step_num:03d}",
                'phase_ipsi': phase,
                'phase_ipsi_dot': phase_dot,

                # Joint angles (rad)
                'hip_flexion_angle_ipsi_rad': hip_ipsi_rad,
                'hip_flexion_angle_contra_rad': hip_contra_rad,
                'knee_flexion_angle_ipsi_rad': knee_ipsi_rad,
                'knee_flexion_angle_contra_rad': knee_contra_rad,
                'ankle_dorsiflexion_angle_ipsi_rad': ankle_ipsi_rad,
                'ankle_dorsiflexion_angle_contra_rad': ankle_contra_rad,

                # Joint velocities (rad/s)
                'hip_flexion_velocity_ipsi_rad_s': hip_vel_ipsi,
                'hip_flexion_velocity_contra_rad_s': hip_vel_contra,
                'knee_flexion_velocity_ipsi_rad_s': knee_vel_ipsi,
                'knee_flexion_velocity_contra_rad_s': knee_vel_contra,
                'ankle_dorsiflexion_velocity_ipsi_rad_s': ankle_vel_ipsi,
                'ankle_dorsiflexion_velocity_contra_rad_s': ankle_vel_contra,

                # Joint accelerations (rad/s^2)
                'hip_flexion_acceleration_ipsi_rad_s2': hip_acc_ipsi,
                'hip_flexion_acceleration_contra_rad_s2': hip_acc_contra,
                'knee_flexion_acceleration_ipsi_rad_s2': knee_acc_ipsi,
                'knee_flexion_acceleration_contra_rad_s2': knee_acc_contra,
                'ankle_dorsiflexion_acceleration_ipsi_rad_s2': ankle_acc_ipsi,
                'ankle_dorsiflexion_acceleration_contra_rad_s2': ankle_acc_contra,

                # Joint moments (Nm/kg)
                'hip_flexion_moment_ipsi_Nm_kg': hip_mom_ipsi,
                'hip_flexion_moment_contra_Nm_kg': hip_mom_contra,
                'knee_flexion_moment_ipsi_Nm_kg': knee_mom_ipsi,
                'knee_flexion_moment_contra_Nm_kg': knee_mom_contra,
                'ankle_dorsiflexion_moment_ipsi_Nm_kg': ankle_mom_ipsi,
                'ankle_dorsiflexion_moment_contra_Nm_kg': ankle_mom_contra,

                # Ground reaction forces (BW) - only vertical available
                'grf_vertical_ipsi_BW': grf_vert_ipsi,
                'grf_vertical_contra_BW': grf_vert_contra,

                # Center of pressure (m) - from raw .mot files
                'cop_anterior_ipsi_m': cop_ap_ipsi,
                'cop_anterior_contra_m': cop_ap_contra,
                'cop_lateral_ipsi_m': cop_ml_ipsi,
                'cop_lateral_contra_m': cop_ml_contra,

                # Segment angles (rad) - computed from kinematic chain
                'pelvis_sagittal_angle_rad': pelvis_tilt_rad,
                'thigh_sagittal_angle_ipsi_rad': thigh_ipsi_rad,
                'thigh_sagittal_angle_contra_rad': thigh_contra_rad,
                'shank_sagittal_angle_ipsi_rad': shank_ipsi_rad,
                'shank_sagittal_angle_contra_rad': shank_contra_rad,
                'foot_sagittal_angle_ipsi_rad': foot_ipsi_rad,
                'foot_sagittal_angle_contra_rad': foot_contra_rad,

                # Segment velocities (rad/s)
                'pelvis_sagittal_velocity_rad_s': pelvis_vel,
                'thigh_sagittal_velocity_ipsi_rad_s': thigh_vel_ipsi,
                'thigh_sagittal_velocity_contra_rad_s': thigh_vel_contra,
                'shank_sagittal_velocity_ipsi_rad_s': shank_vel_ipsi,
                'shank_sagittal_velocity_contra_rad_s': shank_vel_contra,
                'foot_sagittal_velocity_ipsi_rad_s': foot_vel_ipsi,
                'foot_sagittal_velocity_contra_rad_s': foot_vel_contra,
            })

            strides.append(stride_df)
            step_num += 1

    return strides, step_num


def process_bilateral_task(
    task_data,
    subject_id: str,
    subject_mass: float,
    task: str,
    task_id: str,
    condition: str,
    step_offset: int = 0,
    mot_df: Optional[pd.DataFrame] = None,
    task_key: Optional[str] = None
) -> Tuple[List[pd.DataFrame], int]:
    """
    Process a bilateral task (sit-to-stand, squat) - no left/right separation.

    Uses left leg as ipsilateral reference.
    """
    strides = []
    step_num = step_offset
    deg2rad = np.pi / 180.0
    body_weight_N = subject_mass * 9.81

    # Determine exo state for task_info
    exo_state = 'no_exo' if condition == 'bare' else 'powered'

    # Build subject metadata (demographics only, exo info goes in task_info)
    info = SUBJECT_INFO.get(subject_id, {})
    subject_metadata = f"weight_kg:{subject_mass:.1f}"
    if 'sex' in info:
        subject_metadata += f",sex:{info['sex']}"
    if 'age' in info:
        subject_metadata += f",age:{info['age']}"

    # Use left as ipsi, right as contra
    ipsi, contra = 'l', 'r'

    # Get angle data to determine number of cycles
    hip_key = f'hip_flexion_{ipsi}'
    if not (hasattr(task_data, 'dtype') and task_data.dtype.names and hip_key in task_data.dtype.names):
        return strides, step_num

    hip_data = task_data[hip_key]
    if hip_data.size == 0:
        return strides, step_num

    n_cycles = hip_data.shape[1] if hip_data.ndim == 2 else 1

    for cycle_idx in range(n_cycles):
        # Extract stride duration (use 'time' if available, otherwise estimate)
        stride_duration_s = 2.0  # Default for sit-stand ~2s
        if 'time' in task_data.dtype.names:
            time_data = task_data['time']
            if time_data.size > 0:
                if time_data.ndim == 2 and cycle_idx < time_data.shape[1]:
                    t = time_data[:, cycle_idx]
                    valid = ~np.isnan(t)
                    if np.sum(valid) > 1:
                        stride_duration_s = t[valid][-1] - t[valid][0]
                elif time_data.ndim == 1 and len(time_data) > 1:
                    stride_duration_s = time_data[-1] - time_data[0]

        # Extract and interpolate kinematics
        hip_ipsi_deg = task_data[f'hip_flexion_{ipsi}'][:, cycle_idx] if hip_data.ndim == 2 else hip_data
        hip_contra_deg = task_data[f'hip_flexion_{contra}'][:, cycle_idx] if task_data[f'hip_flexion_{contra}'].ndim == 2 else task_data[f'hip_flexion_{contra}']
        hip_ipsi_rad = interpolate_to_phase(hip_ipsi_deg * deg2rad).flatten()
        hip_contra_rad = interpolate_to_phase(hip_contra_deg * deg2rad).flatten()

        knee_ipsi_deg = task_data[f'knee_angle_{ipsi}'][:, cycle_idx] if task_data[f'knee_angle_{ipsi}'].ndim == 2 else task_data[f'knee_angle_{ipsi}']
        knee_contra_deg = task_data[f'knee_angle_{contra}'][:, cycle_idx] if task_data[f'knee_angle_{contra}'].ndim == 2 else task_data[f'knee_angle_{contra}']
        knee_ipsi_rad = interpolate_to_phase(-knee_ipsi_deg * deg2rad).flatten()
        knee_contra_rad = interpolate_to_phase(-knee_contra_deg * deg2rad).flatten()

        ankle_ipsi_deg = task_data[f'ankle_angle_{ipsi}'][:, cycle_idx] if task_data[f'ankle_angle_{ipsi}'].ndim == 2 else task_data[f'ankle_angle_{ipsi}']
        ankle_contra_deg = task_data[f'ankle_angle_{contra}'][:, cycle_idx] if task_data[f'ankle_angle_{contra}'].ndim == 2 else task_data[f'ankle_angle_{contra}']
        ankle_ipsi_rad = interpolate_to_phase(ankle_ipsi_deg * deg2rad).flatten()
        ankle_contra_rad = interpolate_to_phase(ankle_contra_deg * deg2rad).flatten()

        # Extract pelvis_tilt (global, same for both legs)
        pelvis_tilt_rad = np.zeros(NUM_POINTS)
        if 'pelvis_tilt' in task_data.dtype.names:
            pelvis_data = task_data['pelvis_tilt']
            if pelvis_data.ndim == 2 and cycle_idx < pelvis_data.shape[1]:
                pelvis_tilt_rad = interpolate_to_phase(pelvis_data[:, cycle_idx] * deg2rad).flatten()
            elif pelvis_data.ndim == 1:
                pelvis_tilt_rad = interpolate_to_phase(pelvis_data * deg2rad).flatten()

        # Compute segment angles from kinematic chain
        # thigh_angle = pelvis_tilt + hip_flexion
        # shank_angle = thigh_angle - knee_flexion (knee is flexion-positive)
        # foot_angle = shank_angle + ankle_dorsiflexion
        thigh_ipsi_rad = pelvis_tilt_rad + hip_ipsi_rad
        thigh_contra_rad = pelvis_tilt_rad + hip_contra_rad
        shank_ipsi_rad = thigh_ipsi_rad - knee_ipsi_rad
        shank_contra_rad = thigh_contra_rad - knee_contra_rad
        foot_ipsi_rad = shank_ipsi_rad + ankle_ipsi_rad
        foot_contra_rad = shank_contra_rad + ankle_contra_rad

        # Compute velocities and accelerations
        hip_vel_ipsi = compute_velocity_from_angle(hip_ipsi_rad, stride_duration_s)
        hip_vel_contra = compute_velocity_from_angle(hip_contra_rad, stride_duration_s)
        knee_vel_ipsi = compute_velocity_from_angle(knee_ipsi_rad, stride_duration_s)
        knee_vel_contra = compute_velocity_from_angle(knee_contra_rad, stride_duration_s)
        ankle_vel_ipsi = compute_velocity_from_angle(ankle_ipsi_rad, stride_duration_s)
        ankle_vel_contra = compute_velocity_from_angle(ankle_contra_rad, stride_duration_s)

        # Compute segment velocities
        pelvis_vel = compute_velocity_from_angle(pelvis_tilt_rad, stride_duration_s)
        thigh_vel_ipsi = compute_velocity_from_angle(thigh_ipsi_rad, stride_duration_s)
        thigh_vel_contra = compute_velocity_from_angle(thigh_contra_rad, stride_duration_s)
        shank_vel_ipsi = compute_velocity_from_angle(shank_ipsi_rad, stride_duration_s)
        shank_vel_contra = compute_velocity_from_angle(shank_contra_rad, stride_duration_s)
        foot_vel_ipsi = compute_velocity_from_angle(foot_ipsi_rad, stride_duration_s)
        foot_vel_contra = compute_velocity_from_angle(foot_contra_rad, stride_duration_s)

        hip_acc_ipsi = compute_acceleration_from_velocity(hip_vel_ipsi, stride_duration_s)
        hip_acc_contra = compute_acceleration_from_velocity(hip_vel_contra, stride_duration_s)
        knee_acc_ipsi = compute_acceleration_from_velocity(knee_vel_ipsi, stride_duration_s)
        knee_acc_contra = compute_acceleration_from_velocity(knee_vel_contra, stride_duration_s)
        ankle_acc_ipsi = compute_acceleration_from_velocity(ankle_vel_ipsi, stride_duration_s)
        ankle_acc_contra = compute_acceleration_from_velocity(ankle_vel_contra, stride_duration_s)

        # Extract moments (Nm -> Nm/kg)
        hip_mom_ipsi = np.full(NUM_POINTS, np.nan)
        hip_mom_contra = np.full(NUM_POINTS, np.nan)
        knee_mom_ipsi = np.full(NUM_POINTS, np.nan)
        knee_mom_contra = np.full(NUM_POINTS, np.nan)
        ankle_mom_ipsi = np.full(NUM_POINTS, np.nan)
        ankle_mom_contra = np.full(NUM_POINTS, np.nan)

        for side, dst_ipsi, dst_contra in [(ipsi, True, False), (contra, False, True)]:
            for joint, sign in [('hip_flexion', 1), ('knee_angle', -1), ('ankle_angle', 1)]:
                mom_key = f'{joint}_{side}_moment'
                if mom_key in task_data.dtype.names:
                    mom_data = task_data[mom_key]
                    if mom_data.ndim == 2 and cycle_idx < mom_data.shape[1]:
                        mom_interp = interpolate_to_phase(sign * mom_data[:, cycle_idx] / subject_mass).flatten()
                    elif mom_data.ndim == 1:
                        mom_interp = interpolate_to_phase(sign * mom_data / subject_mass).flatten()
                    else:
                        continue

                    if side == ipsi:
                        if 'hip' in joint:
                            hip_mom_ipsi = mom_interp
                        elif 'knee' in joint:
                            knee_mom_ipsi = mom_interp
                        else:
                            ankle_mom_ipsi = mom_interp
                    else:
                        if 'hip' in joint:
                            hip_mom_contra = mom_interp
                        elif 'knee' in joint:
                            knee_mom_contra = mom_interp
                        else:
                            ankle_mom_contra = mom_interp

        # Extract GRF
        grf_vert_ipsi = np.full(NUM_POINTS, np.nan)
        grf_vert_contra = np.full(NUM_POINTS, np.nan)

        for side, is_ipsi in [(ipsi, True), (contra, False)]:
            grf_key = f'ForceN_{side}'
            if grf_key in task_data.dtype.names:
                grf_data = task_data[grf_key]
                if grf_data.ndim == 2 and cycle_idx < grf_data.shape[1]:
                    grf_interp = interpolate_to_phase(grf_data[:, cycle_idx] / body_weight_N).flatten()
                elif grf_data.ndim == 1:
                    grf_interp = interpolate_to_phase(grf_data / body_weight_N).flatten()
                else:
                    continue

                if is_ipsi:
                    grf_vert_ipsi = grf_interp
                else:
                    grf_vert_contra = grf_interp

        # Phase values
        phase = np.linspace(0, 100, NUM_POINTS)
        phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)

        # Extract COP from .mot file if available
        # For bilateral tasks, both feet are on the ground so no phase shift needed
        cop_ap_ipsi = np.full(NUM_POINTS, np.nan)
        cop_ap_contra = np.full(NUM_POINTS, np.nan)
        cop_ml_ipsi = np.full(NUM_POINTS, np.nan)
        cop_ml_contra = np.full(NUM_POINTS, np.nan)

        if mot_df is not None and task_key is not None:
            # Get force plate assignment for this task
            right_plate, left_plate = get_forceplate_assignment(task_key)
            # ipsi=left, contra=right for bilateral tasks
            ipsi_plate = left_plate
            contra_plate = right_plate

            # Extract stride times if available (use 'l' as reference leg for bilateral)
            start_time, end_time = extract_stride_times(task_data, 'l', cycle_idx)

            if start_time is not None and end_time is not None:
                # Bilateral tasks are never decline walking, but use consistent logic
                is_decline = task == 'decline_walking'
                cop_ap_ipsi, cop_ml_ipsi = extract_cop_for_stride(
                    mot_df, start_time, end_time, ipsi_plate,
                    negate_anterior=is_decline)
                cop_ap_contra, cop_ml_contra = extract_cop_for_stride(
                    mot_df, start_time, end_time, contra_plate,
                    negate_anterior=is_decline)

        # Mask COP where GRF is below threshold (swing phase)
        # COP is only meaningful during stance when foot is in contact
        GRF_THRESHOLD_BW = 0.05  # 5% body weight
        cop_ap_ipsi = np.where(grf_vert_ipsi > GRF_THRESHOLD_BW, cop_ap_ipsi, np.nan)
        cop_ml_ipsi = np.where(grf_vert_ipsi > GRF_THRESHOLD_BW, cop_ml_ipsi, np.nan)
        cop_ap_contra = np.where(grf_vert_contra > GRF_THRESHOLD_BW, cop_ap_contra, np.nan)
        cop_ml_contra = np.where(grf_vert_contra > GRF_THRESHOLD_BW, cop_ml_contra, np.nan)

        # Build task_info string (includes exo metadata per reference spec)
        task_info_parts = ["leg:l", f"exo_state:{exo_state}"]
        if exo_state == 'powered':
            task_info_parts.append("exo_joints:ankle")
        task_info_str = ",".join(task_info_parts)

        # Create DataFrame
        stride_df = pd.DataFrame({
            'subject': f"MBLUE_{subject_id}",
            'subject_metadata': subject_metadata,
            'task': task,
            'task_id': task_id,
            'task_info': task_info_str,
            'step': f"{step_num:03d}",
            'phase_ipsi': phase,
            'phase_ipsi_dot': phase_dot,

            'hip_flexion_angle_ipsi_rad': hip_ipsi_rad,
            'hip_flexion_angle_contra_rad': hip_contra_rad,
            'knee_flexion_angle_ipsi_rad': knee_ipsi_rad,
            'knee_flexion_angle_contra_rad': knee_contra_rad,
            'ankle_dorsiflexion_angle_ipsi_rad': ankle_ipsi_rad,
            'ankle_dorsiflexion_angle_contra_rad': ankle_contra_rad,

            'hip_flexion_velocity_ipsi_rad_s': hip_vel_ipsi,
            'hip_flexion_velocity_contra_rad_s': hip_vel_contra,
            'knee_flexion_velocity_ipsi_rad_s': knee_vel_ipsi,
            'knee_flexion_velocity_contra_rad_s': knee_vel_contra,
            'ankle_dorsiflexion_velocity_ipsi_rad_s': ankle_vel_ipsi,
            'ankle_dorsiflexion_velocity_contra_rad_s': ankle_vel_contra,

            'hip_flexion_acceleration_ipsi_rad_s2': hip_acc_ipsi,
            'hip_flexion_acceleration_contra_rad_s2': hip_acc_contra,
            'knee_flexion_acceleration_ipsi_rad_s2': knee_acc_ipsi,
            'knee_flexion_acceleration_contra_rad_s2': knee_acc_contra,
            'ankle_dorsiflexion_acceleration_ipsi_rad_s2': ankle_acc_ipsi,
            'ankle_dorsiflexion_acceleration_contra_rad_s2': ankle_acc_contra,

            'hip_flexion_moment_ipsi_Nm_kg': hip_mom_ipsi,
            'hip_flexion_moment_contra_Nm_kg': hip_mom_contra,
            'knee_flexion_moment_ipsi_Nm_kg': knee_mom_ipsi,
            'knee_flexion_moment_contra_Nm_kg': knee_mom_contra,
            'ankle_dorsiflexion_moment_ipsi_Nm_kg': ankle_mom_ipsi,
            'ankle_dorsiflexion_moment_contra_Nm_kg': ankle_mom_contra,

            'grf_vertical_ipsi_BW': grf_vert_ipsi,
            'grf_vertical_contra_BW': grf_vert_contra,

            # Center of pressure (m) - from raw .mot files
            'cop_anterior_ipsi_m': cop_ap_ipsi,
            'cop_anterior_contra_m': cop_ap_contra,
            'cop_lateral_ipsi_m': cop_ml_ipsi,
            'cop_lateral_contra_m': cop_ml_contra,

            # Segment angles (rad) - computed from kinematic chain
            'pelvis_sagittal_angle_rad': pelvis_tilt_rad,
            'thigh_sagittal_angle_ipsi_rad': thigh_ipsi_rad,
            'thigh_sagittal_angle_contra_rad': thigh_contra_rad,
            'shank_sagittal_angle_ipsi_rad': shank_ipsi_rad,
            'shank_sagittal_angle_contra_rad': shank_contra_rad,
            'foot_sagittal_angle_ipsi_rad': foot_ipsi_rad,
            'foot_sagittal_angle_contra_rad': foot_contra_rad,

            # Segment velocities (rad/s)
            'pelvis_sagittal_velocity_rad_s': pelvis_vel,
            'thigh_sagittal_velocity_ipsi_rad_s': thigh_vel_ipsi,
            'thigh_sagittal_velocity_contra_rad_s': thigh_vel_contra,
            'shank_sagittal_velocity_ipsi_rad_s': shank_vel_ipsi,
            'shank_sagittal_velocity_contra_rad_s': shank_vel_contra,
            'foot_sagittal_velocity_ipsi_rad_s': foot_vel_ipsi,
            'foot_sagittal_velocity_contra_rad_s': foot_vel_contra,
        })

        strides.append(stride_df)
        step_num += 1

    return strides, step_num


def process_subject(
    mat_path: Path,
    subject_id: str,
    condition_filter: str = 'all',
    vicon_data_path: Optional[Path] = None
) -> pd.DataFrame:
    """
    Process all data for a single subject.

    Args:
        mat_path: Path to NormalizedStrides.mat file
        subject_id: Subject identifier (e.g., 'AB01')
        condition_filter: 'all', 'bare', or 'exo'
        vicon_data_path: Path to Vicon data directory containing .mot files (optional)

    Returns:
        Combined DataFrame of all strides
    """
    # Load MATLAB file
    try:
        mat_data = loadmat(str(mat_path), squeeze_me=False, struct_as_record=True)
    except Exception as e:
        print(f"  Error loading {mat_path}: {e}")
        return pd.DataFrame()

    # Navigate to dataOut
    if 'dataOut' not in mat_data:
        print(f"  No dataOut in {mat_path}")
        return pd.DataFrame()

    data_out = mat_data['dataOut']
    while data_out.shape == (1, 1):
        data_out = data_out[0, 0]

    subject_mass = SUBJECT_INFO.get(subject_id, {}).get('mass', 70.0)
    all_strides = []

    # Load FileInfo.mat to get exo filename_suffixes
    exo_suffixes = {}
    file_info_path = mat_path.parent / f"{subject_id}_FileInfo.mat"
    if file_info_path.exists():
        try:
            file_info = loadmat(str(file_info_path), squeeze_me=True, struct_as_record=False)
            subj_info = file_info['subject_info']
            if hasattr(subj_info, 'exo'):
                for task_key in ['level_0x75', 'level_1x0', 'level_1x25',
                                 'incline_5deg', 'incline_10deg',
                                 'decline_5deg', 'decline_10deg',
                                 'STS', 'crouch', 'stairs']:
                    if hasattr(subj_info.exo, task_key):
                        task_info = getattr(subj_info.exo, task_key)
                        if hasattr(task_info, 'filename_suffix'):
                            exo_suffixes[task_key] = task_info.filename_suffix
        except Exception as e:
            print(f"    Warning: Could not load FileInfo.mat: {e}")

    # Find subject's Vicon data folder (contains date subfolder with .mot files)
    mot_files_cache = {}  # Cache loaded .mot files by task
    subject_vicon_path = None
    if vicon_data_path is not None:
        subject_vicon_path = vicon_data_path / subject_id
        if subject_vicon_path.exists():
            # Find date subfolder (format: MMDDYYYY) - use most recent date
            date_folders = [d for d in subject_vicon_path.iterdir() if d.is_dir() and d.name[0].isdigit()]
            if date_folders:
                # Sort by date (MMDDYYYY -> YYYYMMDD for proper sorting)
                def date_sort_key(d):
                    name = d.name
                    if len(name) == 8:  # MMDDYYYY format
                        return name[4:8] + name[0:4]  # YYYYMMDD
                    return name
                date_folders.sort(key=date_sort_key, reverse=True)
                subject_vicon_path = date_folders[0]  # Use most recent date folder
                print(f"    Found Vicon data: {subject_vicon_path}")
            else:
                print(f"    Warning: No date folder found in {subject_vicon_path}")
                subject_vicon_path = None
        else:
            print(f"    Warning: Vicon path not found: {subject_vicon_path}")
            subject_vicon_path = None

    def get_mot_file(task_key: str, condition: str = 'bare') -> Optional[pd.DataFrame]:
        """Load .mot file for task and condition, using cache."""
        if subject_vicon_path is None:
            return None

        # Determine .mot file name based on condition
        if condition == 'bare':
            mot_name = BARE_TASK_TO_MOT_FILE.get(task_key)
            if mot_name is None:
                return None
            candidates = [mot_name]
        else:  # exo
            suffix = exo_suffixes.get(task_key)
            if suffix is None:
                return None
            # For stairs, use corrected file
            if task_key == 'stairs':
                base = f"exo_{suffix}"
                candidates = [f"{base}_corrected", base]
            else:
                base = f"exo_{suffix}"
                # Try exact match, then with "01" suffix (common variant)
                candidates = [base, f"{base}01"]

        # Try each candidate file name
        for mot_name in candidates:
            cache_key = f"{condition}_{mot_name}"
            if cache_key in mot_files_cache:
                return mot_files_cache[cache_key]

            mot_path = subject_vicon_path / f"{mot_name}.mot"
            mot_df = load_mot_file(mot_path)
            if mot_df is not None:
                mot_files_cache[cache_key] = mot_df
                print(f"      Loaded {mot_path.name} ({len(mot_df)} rows)")
                return mot_df

        # No file found
        return None

    # Process each condition (bare/exo)
    conditions = []
    if condition_filter in ['all', 'bare'] and 'bare' in data_out.dtype.names:
        conditions.append('bare')
    if condition_filter in ['all', 'exo'] and 'exo' in data_out.dtype.names:
        conditions.append('exo')

    for condition in conditions:
        cond_data = data_out[condition]
        while cond_data.shape == (1, 1):
            cond_data = cond_data[0, 0]

        if not hasattr(cond_data, 'dtype') or not cond_data.dtype.names:
            continue

        step_offset = 0

        # Process walking tasks (level, incline, decline)
        for task_key in ['level_0x75', 'level_1x0', 'level_1x25',
                         'incline_5deg', 'incline_10deg',
                         'decline_5deg', 'decline_10deg']:
            if task_key not in cond_data.dtype.names:
                continue

            task_data = cond_data[task_key]
            while hasattr(task_data, 'shape') and task_data.shape == (1, 1):
                task_data = task_data[0, 0]

            if not hasattr(task_data, 'dtype') or not task_data.dtype.names:
                continue

            task, task_id, speed = TASK_MAPPING.get(task_key, (None, None, None))
            if task is None:
                continue

            # Load .mot file for COP extraction
            mot_df = get_mot_file(task_key, condition)

            strides, step_offset = process_gait_task(
                task_data, subject_id, subject_mass,
                task, task_id, speed, condition, step_offset,
                mot_df=mot_df, task_key=task_key
            )
            all_strides.extend(strides)

        # Process STS (sit-to-stand / stand-to-sit)
        if 'STS' in cond_data.dtype.names:
            sts_data = cond_data['STS']
            while hasattr(sts_data, 'shape') and sts_data.shape == (1, 1):
                sts_data = sts_data[0, 0]

            if hasattr(sts_data, 'dtype') and sts_data.dtype.names:
                for sub_task in ['sit_stand', 'stand_sit']:
                    if sub_task not in sts_data.dtype.names:
                        continue

                    sub_data = sts_data[sub_task]
                    while hasattr(sub_data, 'shape') and sub_data.shape == (1, 1):
                        sub_data = sub_data[0, 0]

                    if not hasattr(sub_data, 'dtype') or not sub_data.dtype.names:
                        continue

                    task, task_id, _ = TASK_MAPPING.get(sub_task, (None, None, None))
                    if task is None:
                        continue

                    # Load .mot file for STS COP extraction
                    mot_df = get_mot_file('STS', condition)

                    strides, step_offset = process_bilateral_task(
                        sub_data, subject_id, subject_mass,
                        task, task_id, condition, step_offset,
                        mot_df=mot_df, task_key='STS'
                    )
                    all_strides.extend(strides)

        # Process crouch (squat)
        if 'crouch' in cond_data.dtype.names:
            crouch_data = cond_data['crouch']
            while hasattr(crouch_data, 'shape') and crouch_data.shape == (1, 1):
                crouch_data = crouch_data[0, 0]

            if hasattr(crouch_data, 'dtype') and crouch_data.dtype.names:
                task, task_id, _ = TASK_MAPPING.get('crouch', (None, None, None))
                if task is not None:
                    # Load .mot file for crouch COP extraction
                    mot_df = get_mot_file('crouch', condition)

                    strides, step_offset = process_bilateral_task(
                        crouch_data, subject_id, subject_mass,
                        task, task_id, condition, step_offset,
                        mot_df=mot_df, task_key='crouch'
                    )
                    all_strides.extend(strides)

        # Process stairs
        if 'stairs' in cond_data.dtype.names:
            stairs_data = cond_data['stairs']
            while hasattr(stairs_data, 'shape') and stairs_data.shape == (1, 1):
                stairs_data = stairs_data[0, 0]

            if hasattr(stairs_data, 'dtype') and stairs_data.dtype.names:
                for direction in ['ascent', 'descent']:
                    if direction not in stairs_data.dtype.names:
                        continue

                    dir_data = stairs_data[direction]
                    while hasattr(dir_data, 'shape') and dir_data.shape == (1, 1):
                        dir_data = dir_data[0, 0]

                    if not hasattr(dir_data, 'dtype') or not dir_data.dtype.names:
                        continue

                    task, task_id, _ = TASK_MAPPING.get(direction, (None, None, None))
                    if task is None:
                        continue

                    # Load .mot file for stairs COP extraction
                    mot_df = get_mot_file('stairs', condition)

                    # Stairs may be nested by step number (s2, s3, s4)
                    for step_key in dir_data.dtype.names:
                        step_data = dir_data[step_key]
                        while hasattr(step_data, 'shape') and step_data.shape == (1, 1):
                            step_data = step_data[0, 0]

                        if not hasattr(step_data, 'dtype') or not step_data.dtype.names:
                            continue

                        # Use step-specific task_id
                        step_task_id = f"{task_id}_{step_key}"

                        strides, step_offset = process_gait_task(
                            step_data, subject_id, subject_mass,
                            task, step_task_id, None, condition, step_offset,
                            mot_df=mot_df, task_key='stairs'
                        )
                        all_strides.extend(strides)

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert MBLUE Ankle dataset to parquet')
    parser.add_argument('--input', '-i', type=str,
                       default='../MBLUEAnkleOpenSimProcessing/Subject_Data',
                       help='Path to Subject_Data folder')
    parser.add_argument('--output', '-o', type=str, default='mblue_ankle_phase.parquet',
                       help='Output parquet filename')
    parser.add_argument('--output-dir', type=str, default='../../../converted_datasets',
                       help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                       help='Specific subjects to process (e.g., AB01 AB02)')
    parser.add_argument('--condition', '-c', type=str, choices=['all', 'bare', 'exo'],
                       default='all', help='Filter by condition')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: process only first subject')
    parser.add_argument('--vicon-path', type=str, default=None,
                       help='Path to Vicon data directory containing raw .mot files (for COP extraction)')

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    if not input_path.exists():
        # Try relative to script location
        script_dir = Path(__file__).parent
        input_path = script_dir / args.input
        if not input_path.exists():
            print(f"Error: Input path not found: {args.input}")
            return

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).parent / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup Vicon data path for COP extraction
    vicon_path = None
    if args.vicon_path:
        vicon_path = Path(args.vicon_path)
        if not vicon_path.exists():
            print(f"Warning: Vicon path not found: {vicon_path}")
            print("  COP data will not be extracted.")
            vicon_path = None
        else:
            print(f"Vicon data path: {vicon_path}")

    # Find subject files
    mat_files = sorted(input_path.glob('*_NormalizedStrides.mat'))

    if args.subjects:
        mat_files = [f for f in mat_files if any(s in f.name for s in args.subjects)]

    if args.test:
        mat_files = mat_files[:1]
        print(f"Test mode: processing only {mat_files[0].name}")

    print(f"Found {len(mat_files)} subject files")
    print(f"Condition filter: {args.condition}")

    # Process each subject
    all_data = []

    for mat_file in tqdm(mat_files, desc="Processing subjects"):
        subject_id = mat_file.name.replace('_NormalizedStrides.mat', '')
        print(f"\nProcessing {subject_id}...")

        subject_data = process_subject(mat_file, subject_id, args.condition, vicon_path)

        if not subject_data.empty:
            all_data.append(subject_data)
            n_strides = len(subject_data) // NUM_POINTS
            print(f"  Extracted {n_strides} strides")
        else:
            print(f"  No valid strides found")

    # Combine and save
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        output_path = output_dir / args.output

        print(f"\nSaving to {output_path}")
        print(f"Total rows: {len(combined_df)}")
        print(f"Total strides: {len(combined_df) // NUM_POINTS}")
        print(f"Unique subjects: {combined_df['subject'].nunique()}")
        print(f"Tasks: {combined_df['task'].unique().tolist()}")

        combined_df.to_parquet(output_path, index=False)
        print("Done!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
