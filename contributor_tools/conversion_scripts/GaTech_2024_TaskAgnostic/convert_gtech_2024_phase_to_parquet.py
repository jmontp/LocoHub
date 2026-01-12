#!/usr/bin/env python3
"""
Convert GaTech 2024 TaskAgnostic dataset to standardized phase-normalized parquet format.

This script converts the "Task-agnostic exoskeleton control via biological joint moment estimation"
dataset (Nature 2024) to the LocoHub standardized format.

Source: https://repository.gatech.edu/handle/1853/75759
Paper: https://www.nature.com/articles/s41586-024-08157-7

Data structure:
- 25 subjects total (Phase1And2: BT01-BT17, Phase3: BT01, BT02, BT13, BT18-BT24)
- 28 activities per subject
- 200 Hz sampling rate
- CSV files with joint angles, moments, velocities, GRF, etc.

Output: Phase-normalized parquet file with 150 points per gait cycle.
"""

import os
import re
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import interp1d
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Also add src directory for locohub imports (required by common/validation)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))
from common.stride_segmentation import (
    SegmentationArchetype,
    SegmentBoundary,
    GaitSegmentationConfig,
    StandingActionConfig,
    SitStandConfig,
    TASK_ARCHETYPE_MAP,
    segment_gait_cycles,
    segment_standing_action_cycles,
    segment_sit_stand_transfers,
    filter_segments_by_duration_iqr,
    remove_transition_segments,
)

# Configuration
NUM_POINTS = 150  # Points per gait cycle
GRF_THRESHOLD_N = 20.0  # Threshold for heel strike detection (N)
MIN_STRIDE_SAMPLES = 100  # Minimum samples for valid stride (~0.5s at 200Hz)
MAX_STRIDE_SAMPLES = 600  # Maximum samples for valid stride (~3s at 200Hz)
SAMPLING_RATE = 200  # Hz

# Stride filtering parameters
SKIP_FIRST_STRIDES = 2  # Transition strides to skip at trial start
SKIP_LAST_STRIDES = 1   # Transition strides to skip at trial end
IQR_MULTIPLIER = 1.5    # IQR multiplier for stride duration outlier detection

# Task mapping: source task name patterns -> (standard_task, task_id_template, metadata)
# Metadata includes incline_deg for ground slope (used for segment angle correction)
TASK_MAPPING = {
    # Level walking at different speeds (walking = no flight phase)
    r'normal_walk.*_0-6': ('level_walking', 'level_0.6ms', {'incline_deg': 0.0}),
    r'normal_walk.*_1-2': ('level_walking', 'level_1.2ms', {'incline_deg': 0.0}),
    r'normal_walk.*_1-8': ('level_walking', 'level_1.8ms', {'incline_deg': 0.0}),
    # Fast speeds have flight phase (17-22% of gait cycle) -> classify as run
    r'normal_walk.*_2-0': ('run', 'run_2.0ms', {'incline_deg': 0.0}),
    r'normal_walk.*_2-5': ('run', 'run_2.5ms', {'incline_deg': 0.0}),
    # Shuffle and skip have non-standard gait - exclude from level_walking
    r'normal_walk.*_shuffle': (None, 'shuffle', {}),  # Exclude: lateral shuffling
    r'normal_walk.*_skip': (None, 'skip', {}),  # Exclude: skipping gait

    # Incline/decline walking - actual slope from folder name
    r'incline_walk.*_up5': ('incline_walking', 'incline_5deg', {'incline_deg': 5.0}),
    r'incline_walk.*_up10': ('incline_walking', 'incline_10deg', {'incline_deg': 10.0}),
    r'incline_walk.*_down5': ('decline_walking', 'decline_5deg', {'incline_deg': -5.0}),
    r'incline_walk.*_down10': ('decline_walking', 'decline_10deg', {'incline_deg': -10.0}),

    # Stairs - foot lands flat on step surface
    r'stairs.*_up': ('stair_ascent', 'stair_ascent', {'incline_deg': 0.0}),
    r'stairs.*_down': ('stair_descent', 'stair_descent', {'incline_deg': 0.0}),

    # Other activities
    r'sit_to_stand': ('sit_to_stand', 'sit_to_stand', {'incline_deg': 0.0}),
    r'squats': ('squat', 'squat', {'incline_deg': 0.0}),
    r'walk_backward': ('backward_walking', 'backward_walking', {'incline_deg': 0.0}),
    r'meander': (None, 'meander', {}),  # Exclude: non-straight path walking
    r'curb_up': ('stair_ascent', 'curb_up', {'incline_deg': 0.0}),
    r'curb_down': ('stair_descent', 'curb_down', {'incline_deg': 0.0}),
    r'step_ups': ('stair_ascent', 'step_up', {'incline_deg': 0.0}),

    # Dynamic activities (may not have clear gait cycles)
    r'jump': ('jump', 'jump', {'incline_deg': 0.0}),
    r'lunges': ('lunge', 'lunge', {'incline_deg': 0.0}),
    r'cutting': ('cutting', 'cutting', {'incline_deg': 0.0}),
}

# Subject mass data (kg) from readme
# Phase1And2 masses - using w/ exo mass since all data collected with exo worn
# Format: subject_id -> mass_kg
SUBJECT_MASS_PHASE12 = {
    'BT01': 87.02, 'BT02': 79.09, 'BT03': 101.52, 'BT04': 106.04,
    'BT06': 85.78, 'BT07': 70.61, 'BT08': 75.67, 'BT09': 88.97,
    'BT10': 100.11, 'BT11': 56.98, 'BT12': 84.62, 'BT13': 96.74,
    'BT14': 74.35, 'BT15': 65.87, 'BT16': 72.03, 'BT17': 67.36,
}

# Phase3 masses - includes day1 (with exo) and day2 (with and without exo) for some subjects
# Format: subject_id -> {'with_exo': mass, 'without_exo': mass, 'day2_with_exo': mass, 'day2_without_exo': mass}
# Note: 5 subjects (BT02, BT13, BT18, BT23, BT24) have day 2 no-exo data
SUBJECT_MASS_PHASE3 = {
    'BT01': {'with_exo': 84.28, 'without_exo': 77.29},
    'BT02': {'with_exo': 79.10, 'without_exo': 72.33,
             'day2_with_exo': 76.74, 'day2_without_exo': 69.83},
    'BT13': {'with_exo': 96.03, 'without_exo': 88.99,
             'day2_with_exo': 93.80, 'day2_without_exo': 86.91},
    'BT18': {'with_exo': 74.96, 'without_exo': 67.96,
             'day2_with_exo': 75.23, 'day2_without_exo': 68.37},
    'BT19': {'with_exo': 76.84, 'without_exo': 69.95},
    'BT20': {'with_exo': 62.50, 'without_exo': 55.44},
    'BT21': {'with_exo': 65.86, 'without_exo': 58.85},
    'BT22': {'with_exo': 84.27, 'without_exo': 76.79},
    'BT23': {'with_exo': 74.24, 'without_exo': 67.23,
             'day2_with_exo': 73.93, 'day2_without_exo': 67.16},
    'BT24': {'with_exo': 84.84, 'without_exo': 77.79,
             'day2_with_exo': 87.15, 'day2_without_exo': 79.56},
}

# Subjects with day 2 no-exo data available
SUBJECTS_WITH_NOEXO_DATA = ['BT02', 'BT13', 'BT18', 'BT23', 'BT24']

# Collection phase info:
# Phase 1 (BT01-BT12): Data collected with exo worn - both powered (_on) and unpowered (_off) trials
# Phase 2 (BT13-BT17): Preliminary neural network model, all powered (_on)
# Phase 3 (BT01,BT02,BT13,BT18-BT24): Final model validation
#   - Day 1: All subjects, all powered (_on)
#   - Day 2: 5 subjects (BT02, BT13, BT18, BT23, BT24) have no-exo data (_noexo)
PHASE1_SUBJECTS = ['BT01', 'BT02', 'BT03', 'BT04', 'BT06', 'BT07', 'BT08', 'BT09', 'BT10', 'BT11', 'BT12']
PHASE2_SUBJECTS = ['BT13', 'BT14', 'BT15', 'BT16', 'BT17']
PHASE3_SUBJECTS = ['BT01', 'BT02', 'BT13', 'BT18', 'BT19', 'BT20', 'BT21', 'BT22', 'BT23', 'BT24']


def get_collection_phase(subject_id: str, data_source: str) -> int:
    """
    Determine collection phase based on subject ID and data source folder.

    Args:
        subject_id: Subject identifier (e.g., 'BT01')
        data_source: Either 'Phase1And2' or 'Phase3'

    Returns:
        Collection phase (1, 2, or 3)
    """
    if 'Phase3' in data_source or data_source == 'Parsed':
        # If loading from Phase3 folder, it's phase 3
        if subject_id in PHASE3_SUBJECTS:
            return 3

    # Phase1And2 data
    if subject_id in PHASE1_SUBJECTS:
        return 1
    elif subject_id in PHASE2_SUBJECTS:
        return 2

    return 3  # Default to phase 3 for unknown


def get_exo_state(task_folder: str, collection_phase: int) -> str:
    """
    Determine exoskeleton state from task name and collection phase.

    Returns human-readable exo state:
    - 'powered': Exoskeleton worn and providing active assistance
    - 'worn_unpowered': Exoskeleton worn but not providing assistance
    - 'no_exo': No exoskeleton worn (bare/natural walking) - Phase 3 day 2 only
    - 'unknown': Cannot determine state

    Task naming conventions:
    - '_on': Exoskeleton powered
    - '_off': Exoskeleton worn but unpowered
    - '_hilo': Human In the Loop Optimization - exo powered with optimized controller
    - '_noexo' or '_bare': No exoskeleton (Phase 3 day 2 testing)
    """
    # Check for no-exo condition first (Phase 3 day 2 testing)
    if '_noexo' in task_folder or '_bare' in task_folder:
        return 'no_exo'
    elif '_on' in task_folder or '_hilo' in task_folder:
        return 'powered'
    elif '_off' in task_folder:
        return 'worn_unpowered'
    else:
        # Phase 2 and 3 were mostly powered
        if collection_phase >= 2:
            return 'powered'
        return 'unknown'


def is_day2_trial(task_folder: str) -> bool:
    """
    Determine if a trial is from day 2 testing.

    Day 2 trials for Phase 3 subjects include no-exo data.
    The naming convention for day 2 trials may include '_noexo', '_bare',
    or a day identifier in the folder name.
    """
    return '_noexo' in task_folder or '_bare' in task_folder


def get_subject_mass(subject_id: str, data_source: str, exo_state: str = 'powered',
                     is_day2: bool = False) -> float:
    """
    Get subject mass based on ID, data source, and exo state.

    Args:
        subject_id: Subject identifier (e.g., 'BT24')
        data_source: Data source folder name (e.g., 'Parsed', 'Phase3')
        exo_state: Exoskeleton state ('powered', 'worn_unpowered', 'no_exo')
        is_day2: Whether this is day 2 data (relevant for Phase 3 subjects)

    Returns:
        Subject mass in kg
    """
    # Phase 3 subjects have detailed mass info
    if 'Phase3' in data_source or subject_id in PHASE3_SUBJECTS:
        if subject_id in SUBJECT_MASS_PHASE3:
            mass_data = SUBJECT_MASS_PHASE3[subject_id]

            # For no-exo trials (day 2), use without_exo mass
            if exo_state == 'no_exo':
                if is_day2 and 'day2_without_exo' in mass_data:
                    return mass_data['day2_without_exo']
                return mass_data.get('without_exo', mass_data.get('with_exo', 75.0))

            # For exo trials, use with_exo mass
            if is_day2 and 'day2_with_exo' in mass_data:
                return mass_data['day2_with_exo']
            return mass_data.get('with_exo', 75.0)

    # Phase 1 and 2 subjects have single mass value (with exo)
    if subject_id in SUBJECT_MASS_PHASE12:
        return SUBJECT_MASS_PHASE12[subject_id]

    print(f"  Warning: No mass data for {subject_id}, using 75 kg default")
    return 75.0


def interpolate_to_phase(data: np.ndarray, num_points: int = NUM_POINTS) -> np.ndarray:
    """
    Interpolate time-series data to fixed number of phase points (0-100%).

    Args:
        data: Input data array
        num_points: Number of output points (default 150)

    Returns:
        Interpolated data array of length num_points
    """
    if len(data) < 2:
        return np.full(num_points, np.nan)

    # Create interpolation function
    x_original = np.linspace(0, 100, len(data))
    x_target = np.linspace(0, 100, num_points)

    # Handle NaN values
    valid_mask = ~np.isnan(data)
    if np.sum(valid_mask) < 2:
        return np.full(num_points, np.nan)

    try:
        interp_func = interp1d(x_original[valid_mask], data[valid_mask],
                               kind='linear', fill_value='extrapolate')
        return interp_func(x_target)
    except Exception:
        return np.full(num_points, np.nan)


def compute_velocity_from_angle(angle_rad: np.ndarray, stride_duration_s: float) -> np.ndarray:
    """
    Compute angular velocity from angle data using gradient.

    Args:
        angle_rad: Angle data in radians (150 points)
        stride_duration_s: Duration of stride in seconds

    Returns:
        Angular velocity in rad/s
    """
    # Gradient gives derivative in terms of sample spacing
    # We have 150 points over stride_duration_s seconds
    dt = stride_duration_s / (len(angle_rad) - 1)
    velocity = np.gradient(angle_rad) / dt
    return velocity


def compute_acceleration_from_velocity(velocity_rad_s: np.ndarray, stride_duration_s: float) -> np.ndarray:
    """
    Compute angular acceleration from velocity data using gradient.
    """
    dt = stride_duration_s / (len(velocity_rad_s) - 1)
    acceleration = np.gradient(velocity_rad_s) / dt
    return acceleration


def compute_segment_angles_from_imu(
    imu_df: pd.DataFrame,
    side: str,
    dt: float,
    offset: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute segment angles using foot gyro integration + forward kinematics.

    Algorithm:
    1. Integrate foot gyroscope to get foot angle trajectory
    2. Apply pre-calculated offset (from midstance correction)
    3. Forward kinematics from foot up: shank = foot + ankle, thigh = shank + knee

    The offset should be calculated once per subject/task by averaging the
    midstance foot angle across all strides and comparing to the expected
    ground slope (see calculate_foot_angle_offset()).

    Note: Gyroscope data is in deg/s, so we convert to rad/s before integration.

    Args:
        imu_df: DataFrame with IMU gyroscope data
        side: 'l' or 'r' for left or right leg
        dt: Time step between samples in seconds
        offset: Pre-calculated foot angle offset (radians)

    Returns:
        (thigh_angle, shank_angle, foot_angle) in radians
    """
    deg2rad = np.pi / 180.0

    # Get gyroscope data (sagittal plane rotation = gyro_z, convert from deg/s to rad/s)
    foot_gz = imu_df[f'foot_imu_{side}_gyro_z'].values * deg2rad
    shank_gz = imu_df[f'shank_imu_{side}_gyro_z'].values * deg2rad
    thigh_gz = imu_df[f'thigh_imu_{side}_gyro_z'].values * deg2rad

    # Integrate foot gyro to get foot angle + apply offset
    foot_angle = np.cumsum(foot_gz) * dt + offset

    # Forward kinematics from foot up
    # Joint angles from gyro differences (validated 0.999+ correlation with FK ground truth)
    ankle_angle = np.cumsum(shank_gz - foot_gz) * dt
    knee_angle = np.cumsum(thigh_gz - shank_gz) * dt

    # Segment angles via kinematic chain
    shank_angle = foot_angle + ankle_angle
    thigh_angle = shank_angle + knee_angle

    return thigh_angle, shank_angle, foot_angle


def compute_segment_angles_from_imu_with_accel_init(
    imu_df: pd.DataFrame,
    side: str,
    dt: float,
    init_samples: int = 20,
    transfer_type: str = 'sit_to_stand'
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute segment angles using accelerometer initialization + gyro integration.

    For tasks without a flat-foot midstance phase (sit_to_stand, stand_to_sit),
    use accelerometer at the start of the segment to get initial orientation,
    then integrate gyroscope for the trajectory.

    Standing pose correction: After computing raw angles, apply an offset so that
    the standing phase is centered at 0 radians (vertical). This is analogous to
    the midstance correction used for gait tasks.

    Algorithm:
    1. Average accelerometer at start (first N samples) to get initial angles
    2. Integrate gyroscopes for trajectory (relative changes)
    3. Add initial angles to integrated values
    4. Apply standing pose correction (offset so standing phase = 0)

    Note: Gyroscope data is in deg/s, so we convert to rad/s before integration.

    Args:
        imu_df: DataFrame with IMU data (accelerometer + gyroscope)
        side: 'l' or 'r' for left or right leg
        dt: Time step between samples in seconds
        init_samples: Number of samples to average for initial angle (default 20 = 100ms at 200Hz)
        transfer_type: 'sit_to_stand' or 'stand_to_sit' - determines where standing phase is

    Returns:
        (thigh_angle, shank_angle, foot_angle) in radians
    """
    deg2rad = np.pi / 180.0

    # Get accelerometer data for initial orientation
    thigh_ax = imu_df[f'thigh_imu_{side}_accel_x'].values
    thigh_ay = imu_df[f'thigh_imu_{side}_accel_y'].values
    shank_ax = imu_df[f'shank_imu_{side}_accel_x'].values
    shank_ay = imu_df[f'shank_imu_{side}_accel_y'].values
    foot_ax = imu_df[f'foot_imu_{side}_accel_x'].values
    foot_ay = imu_df[f'foot_imu_{side}_accel_y'].values

    # Get gyroscope data for trajectory (in deg/s, convert to rad/s)
    thigh_gz = imu_df[f'thigh_imu_{side}_gyro_z'].values * deg2rad
    shank_gz = imu_df[f'shank_imu_{side}_gyro_z'].values * deg2rad
    foot_gz = imu_df[f'foot_imu_{side}_gyro_z'].values * deg2rad

    # Compute initial angles from accelerometer (average first N samples)
    # atan2(accel_x, accel_y) gives angle from vertical in sagittal plane
    n = min(init_samples, len(thigh_ax))
    thigh_init = np.arctan2(np.mean(thigh_ax[:n]), np.mean(thigh_ay[:n]))
    shank_init = np.arctan2(np.mean(shank_ax[:n]), np.mean(shank_ay[:n]))
    foot_init = np.arctan2(np.mean(foot_ax[:n]), np.mean(foot_ay[:n]))

    # Integrate gyroscopes for trajectory (relative change from start)
    thigh_delta = np.cumsum(thigh_gz) * dt
    shank_delta = np.cumsum(shank_gz) * dt
    foot_delta = np.cumsum(foot_gz) * dt

    # Combine: initial angle + trajectory
    thigh_angle = thigh_init + thigh_delta
    shank_angle = shank_init + shank_delta
    foot_angle = foot_init + foot_delta

    # Apply standing pose correction: offset so standing phase = 0 radians
    # Standing phase location depends on transfer type:
    # - sit_to_stand: standing is at the END (last N samples)
    # - stand_to_sit: standing is at the BEGINNING (first N samples)
    standing_samples = min(init_samples, len(thigh_angle))
    if transfer_type == 'sit_to_stand':
        # Standing is at the end
        thigh_offset = np.mean(thigh_angle[-standing_samples:])
        shank_offset = np.mean(shank_angle[-standing_samples:])
        foot_offset = np.mean(foot_angle[-standing_samples:])
    else:  # stand_to_sit
        # Standing is at the beginning
        thigh_offset = np.mean(thigh_angle[:standing_samples])
        shank_offset = np.mean(shank_angle[:standing_samples])
        foot_offset = np.mean(foot_angle[:standing_samples])

    # Apply offset (standing = 0)
    thigh_angle = thigh_angle - thigh_offset
    shank_angle = shank_angle - shank_offset
    foot_angle = foot_angle - foot_offset

    return thigh_angle, shank_angle, foot_angle


def calculate_foot_angle_offset(
    stride_imu_list: List[pd.DataFrame],
    side: str,
    dt: float,
    ground_slope_rad: float
) -> float:
    """
    Calculate single foot angle offset by averaging midstance across all strides.

    During midstance (15-35% of gait cycle), the foot is flat on the ground.
    The foot angle should equal the ground slope. We average this across all
    strides to get a robust offset that's applied consistently.

    Note: Gyroscope data is in deg/s, so we convert to rad/s before integration.

    Args:
        stride_imu_list: List of IMU DataFrames, one per stride
        side: 'l' or 'r' for left or right leg
        dt: Time step between samples in seconds
        ground_slope_rad: Expected foot angle at midstance (ground slope in radians)

    Returns:
        Offset to add to integrated foot angle (radians)
    """
    deg2rad = np.pi / 180.0
    midstance_values = []

    for stride_imu in stride_imu_list:
        if stride_imu.empty:
            continue

        foot_gz_col = f'foot_imu_{side}_gyro_z'
        if foot_gz_col not in stride_imu.columns:
            continue

        # Convert from deg/s to rad/s
        foot_gz = stride_imu[foot_gz_col].values * deg2rad
        foot_angle_raw = np.cumsum(foot_gz) * dt

        # Midstance region (15-35% of stride)
        n = len(foot_angle_raw)
        ms_start = int(0.15 * n)
        ms_end = int(0.35 * n)

        if ms_end > ms_start:
            midstance_values.append(np.mean(foot_angle_raw[ms_start:ms_end]))

    if not midstance_values:
        return 0.0

    # Single offset = expected ground slope - average measured midstance angle
    avg_midstance = np.mean(midstance_values)
    return ground_slope_rad - avg_midstance


def get_expected_foot_angle_for_task(task: str, task_info: Dict) -> float:
    """
    Get the expected foot angle during mid-stance based on task type.

    During mid-stance (15-35% of gait), the foot is flat on the ground.
    For level walking, the foot angle should be 0.
    For incline/decline, the foot angle matches the slope.

    Args:
        task: Task name (e.g., 'level_walking', 'incline_walking')
        task_info: Dictionary with task metadata (may contain slope info)

    Returns:
        Expected foot angle in radians (positive = foot tilted up/dorsiflexed)
    """
    deg2rad = np.pi / 180.0

    # Extract slope from task_info if available
    slope_deg = task_info.get('slope_deg', 0.0)

    if task == 'level_walking':
        return 0.0
    elif task == 'incline_walking':
        # Foot tilted up on incline (positive angle)
        return slope_deg * deg2rad if slope_deg else 10.0 * deg2rad  # Default 10 deg
    elif task == 'decline_walking':
        # Foot tilted down on decline (negative angle)
        return -slope_deg * deg2rad if slope_deg else -10.0 * deg2rad  # Default -10 deg
    elif task in ['stair_ascent', 'stair_descent']:
        # Stairs have varying foot angles, use 0 as reference
        return 0.0
    elif task == 'run':
        # Running on level ground
        return 0.0
    else:
        # Default: assume level ground
        return 0.0


def apply_midstance_bias_correction(
    thigh_angle: np.ndarray,
    shank_angle: np.ndarray,
    foot_angle: np.ndarray,
    expected_foot_angle: float = 0.0,
    midstance_start_pct: float = 0.15,
    midstance_end_pct: float = 0.35,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Apply bias correction to segment angles using mid-stance foot angle.

    During mid-stance, the foot is flat on the ground. We calculate the average
    foot angle during this phase and subtract the bias from ALL segment angles.
    This preserves joint angles (differences between segments) while correcting
    the global reference.

    Args:
        thigh_angle: Phase-normalized thigh angle (N_PHASE_POINTS values)
        shank_angle: Phase-normalized shank angle
        foot_angle: Phase-normalized foot angle
        expected_foot_angle: Expected foot angle at mid-stance (rad)
        midstance_start_pct: Start of mid-stance as fraction (0.15 = 15%)
        midstance_end_pct: End of mid-stance as fraction (0.35 = 35%)

    Returns:
        Bias-corrected (thigh_angle, shank_angle, foot_angle)
    """
    n_points = len(foot_angle)

    # Calculate indices for mid-stance phase
    start_idx = int(midstance_start_pct * n_points)
    end_idx = int(midstance_end_pct * n_points)

    # Calculate average foot angle during mid-stance
    midstance_foot_avg = np.mean(foot_angle[start_idx:end_idx])

    # Calculate bias (difference from expected)
    bias = midstance_foot_avg - expected_foot_angle

    # Apply same bias correction to all segments
    # This preserves joint angles (thigh-shank, shank-foot differences)
    thigh_corrected = thigh_angle - bias
    shank_corrected = shank_angle - bias
    foot_corrected = foot_angle - bias

    return thigh_corrected, shank_corrected, foot_corrected


def map_task_name(task_folder: str) -> Tuple[Optional[str], Optional[str], Dict]:
    """
    Map source task folder name to standardized task name and ID.

    Args:
        task_folder: Source folder name (e.g., 'normal_walk_1_1_1-2_on')

    Returns:
        Tuple of (task_name, task_id, task_info_dict)
    """
    task_info = {}

    # Exo state and controller are set later in process_stride based on get_exo_state()
    # Extract exo controller type if present
    if '_hilo' in task_folder:
        task_info['exo_controller'] = 'hilo'

    # Extract speed if present (e.g., '1-2' -> 1.2 m/s)
    speed_match = re.search(r'(\d)-(\d)', task_folder)
    if speed_match:
        speed = float(f"{speed_match.group(1)}.{speed_match.group(2)}")
        task_info['speed_m_s'] = speed

    # Find matching task pattern
    for pattern, (task_name, task_id, task_metadata) in TASK_MAPPING.items():
        if re.search(pattern, task_folder):
            # Merge task metadata (incline_deg, etc.) into task_info
            task_info.update(task_metadata)
            return task_name, task_id, task_info

    # Default: use folder name as task
    return None, None, task_info


def load_trial_data(trial_path: Path, subject_id: str,
                    exo_state: str = 'powered') -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load all CSV files for a trial.

    Args:
        trial_path: Path to trial folder
        subject_id: Subject identifier (e.g., 'BT24')
        exo_state: Exoskeleton state - affects which files are required

    Returns:
        Dictionary with DataFrames for each data type
    """
    trial_name = trial_path.name
    prefix = f"{subject_id}_{trial_name}_"

    data = {}

    # Required files for all trials
    required_files = ['angle_filt', 'moment_filt', 'grf', 'velocity', 'insole_sim']

    # For no-exo trials, moment_filt_bio doesn't exist (no exo torque to subtract)
    # and exo.csv won't have real sensor data
    if exo_state == 'no_exo':
        optional_files = ['power', 'power_bio', 'exo', 'exo_sim']
    else:
        optional_files = ['moment_filt_bio', 'power', 'power_bio', 'exo', 'exo_sim']

    for file_type in required_files + optional_files:
        file_path = trial_path / f"{prefix}{file_type}.csv"
        if file_path.exists():
            try:
                data[file_type] = pd.read_csv(file_path)
            except Exception as e:
                if file_type in required_files:
                    print(f"  Warning: Failed to load {file_path.name}: {e}")
                    return None
        elif file_type in required_files:
            print(f"  Warning: Missing required file {file_path.name}")
            return None

    return data


def process_stride(
    data: Dict[str, pd.DataFrame],
    start_idx: int,
    end_idx: int,
    subject_id: str,
    subject_mass: float,
    task: str,
    task_id: str,
    task_info: Dict,
    step_num: int,
    leg_side: str,
    collection_phase: int,
    exo_state: str,
    is_day2: bool = False,
    imu_df: Optional[pd.DataFrame] = None,
    imu_dt: float = 0.005,
    segment_angle_offset_ipsi: float = 0.0,
    segment_angle_offset_contra: float = 0.0,
    use_accel_init: bool = False,
    skip_segment_angles: bool = False
) -> Optional[pd.DataFrame]:
    """
    Process a single stride from heel strike to heel strike.

    Args:
        data: Dictionary of DataFrames
        start_idx: Start index (heel strike)
        end_idx: End index (next heel strike)
        subject_id: Subject identifier
        subject_mass: Subject mass in kg
        task: Standardized task name
        task_id: Task identifier
        task_info: Additional task info
        step_num: Step number for this trial
        leg_side: 'l' or 'r' for left/right leg
        collection_phase: Data collection phase (1, 2, or 3)
        exo_state: Exoskeleton state ('powered', 'worn_unpowered', 'no_exo', 'unknown')
        is_day2: Whether this is day 2 data (Phase 3 only)
        imu_df: Optional IMU DataFrame with gyroscope data for segment angles
        imu_dt: Time step for IMU data in seconds (default 0.005 = 200Hz)
        segment_angle_offset_ipsi: Pre-calculated foot angle offset for ipsilateral leg (rad)
        segment_angle_offset_contra: Pre-calculated foot angle offset for contralateral leg (rad)
        use_accel_init: If True, use accelerometer for initial orientation (for sit-stand tasks)
        skip_segment_angles: If True, set all segment angles to NaN (for tasks like run)

    Returns:
        DataFrame with 150 rows (one per phase point) or None if invalid
    """
    # Validate stride length
    stride_len = end_idx - start_idx
    if stride_len < MIN_STRIDE_SAMPLES or stride_len > MAX_STRIDE_SAMPLES:
        return None

    # Calculate stride duration
    time_data = data['angle_filt']['time'].values
    stride_duration_s = time_data[end_idx] - time_data[start_idx]

    if stride_duration_s <= 0:
        return None

    # Determine ipsilateral (striking leg) and contralateral sides
    ipsi = leg_side
    contra = 'r' if leg_side == 'l' else 'l'

    # Initialize output arrays
    phase = np.linspace(0, 100, NUM_POINTS)
    phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)  # %/s

    # Extract and interpolate kinematics
    angle_df = data['angle_filt']

    # Degrees to radians conversion
    deg2rad = np.pi / 180.0

    # Hip flexion
    hip_ipsi_deg = angle_df[f'hip_flexion_{ipsi}'].values[start_idx:end_idx]
    hip_contra_deg = angle_df[f'hip_flexion_{contra}'].values[start_idx:end_idx]
    hip_ipsi_rad = interpolate_to_phase(hip_ipsi_deg * deg2rad)
    hip_contra_rad = interpolate_to_phase(hip_contra_deg * deg2rad)

    # Knee flexion (note: source data may have extension positive, need to check)
    knee_ipsi_deg = angle_df[f'knee_angle_{ipsi}'].values[start_idx:end_idx]
    knee_contra_deg = angle_df[f'knee_angle_{contra}'].values[start_idx:end_idx]
    # Negate to make flexion positive (consistent with other datasets)
    knee_ipsi_rad = interpolate_to_phase(-knee_ipsi_deg * deg2rad)
    knee_contra_rad = interpolate_to_phase(-knee_contra_deg * deg2rad)

    # Ankle dorsiflexion
    ankle_ipsi_deg = angle_df[f'ankle_angle_{ipsi}'].values[start_idx:end_idx]
    ankle_contra_deg = angle_df[f'ankle_angle_{contra}'].values[start_idx:end_idx]
    ankle_ipsi_rad = interpolate_to_phase(ankle_ipsi_deg * deg2rad)
    ankle_contra_rad = interpolate_to_phase(ankle_contra_deg * deg2rad)

    # Compute velocities
    hip_vel_ipsi = compute_velocity_from_angle(hip_ipsi_rad, stride_duration_s)
    hip_vel_contra = compute_velocity_from_angle(hip_contra_rad, stride_duration_s)
    knee_vel_ipsi = compute_velocity_from_angle(knee_ipsi_rad, stride_duration_s)
    knee_vel_contra = compute_velocity_from_angle(knee_contra_rad, stride_duration_s)
    ankle_vel_ipsi = compute_velocity_from_angle(ankle_ipsi_rad, stride_duration_s)
    ankle_vel_contra = compute_velocity_from_angle(ankle_contra_rad, stride_duration_s)

    # Compute accelerations
    hip_acc_ipsi = compute_acceleration_from_velocity(hip_vel_ipsi, stride_duration_s)
    hip_acc_contra = compute_acceleration_from_velocity(hip_vel_contra, stride_duration_s)
    knee_acc_ipsi = compute_acceleration_from_velocity(knee_vel_ipsi, stride_duration_s)
    knee_acc_contra = compute_acceleration_from_velocity(knee_vel_contra, stride_duration_s)
    ankle_acc_ipsi = compute_acceleration_from_velocity(ankle_vel_ipsi, stride_duration_s)
    ankle_acc_contra = compute_acceleration_from_velocity(ankle_vel_contra, stride_duration_s)

    # Compute segment angles from IMU gyroscope integration + forward kinematics
    # Offset is calculated once per subject/task and passed in (two-pass approach)
    if skip_segment_angles:
        # Skip segment angles for this task (e.g., run) - fill with NaN
        thigh_seg_ipsi = np.full(NUM_POINTS, np.nan)
        thigh_seg_contra = np.full(NUM_POINTS, np.nan)
        shank_seg_ipsi = np.full(NUM_POINTS, np.nan)
        shank_seg_contra = np.full(NUM_POINTS, np.nan)
        foot_seg_ipsi = np.full(NUM_POINTS, np.nan)
        foot_seg_contra = np.full(NUM_POINTS, np.nan)
        thigh_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        thigh_seg_vel_contra = np.full(NUM_POINTS, np.nan)
        shank_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        shank_seg_vel_contra = np.full(NUM_POINTS, np.nan)
        foot_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        foot_seg_vel_contra = np.full(NUM_POINTS, np.nan)
    elif imu_df is not None and len(imu_df) > end_idx:
        # Extract stride-specific IMU data
        stride_imu = imu_df.iloc[start_idx:end_idx].reset_index(drop=True)

        if use_accel_init:
            # Use accelerometer initialization for sit-stand tasks (no midstance phase)
            # Pass task to apply standing pose correction at correct end
            thigh_seg_ipsi_raw, shank_seg_ipsi_raw, foot_seg_ipsi_raw = compute_segment_angles_from_imu_with_accel_init(
                stride_imu, ipsi, imu_dt, transfer_type=task
            )
            thigh_seg_contra_raw, shank_seg_contra_raw, foot_seg_contra_raw = compute_segment_angles_from_imu_with_accel_init(
                stride_imu, contra, imu_dt, transfer_type=task
            )
        else:
            # Use gyro integration with midstance correction (gait tasks)
            thigh_seg_ipsi_raw, shank_seg_ipsi_raw, foot_seg_ipsi_raw = compute_segment_angles_from_imu(
                stride_imu, ipsi, imu_dt, offset=segment_angle_offset_ipsi
            )
            thigh_seg_contra_raw, shank_seg_contra_raw, foot_seg_contra_raw = compute_segment_angles_from_imu(
                stride_imu, contra, imu_dt, offset=segment_angle_offset_contra
            )

        # Interpolate to phase-normalized points
        thigh_seg_ipsi = interpolate_to_phase(thigh_seg_ipsi_raw)
        thigh_seg_contra = interpolate_to_phase(thigh_seg_contra_raw)
        shank_seg_ipsi = interpolate_to_phase(shank_seg_ipsi_raw)
        shank_seg_contra = interpolate_to_phase(shank_seg_contra_raw)
        foot_seg_ipsi = interpolate_to_phase(foot_seg_ipsi_raw)
        foot_seg_contra = interpolate_to_phase(foot_seg_contra_raw)

        # Compute segment velocities
        thigh_seg_vel_ipsi = compute_velocity_from_angle(thigh_seg_ipsi, stride_duration_s)
        thigh_seg_vel_contra = compute_velocity_from_angle(thigh_seg_contra, stride_duration_s)
        shank_seg_vel_ipsi = compute_velocity_from_angle(shank_seg_ipsi, stride_duration_s)
        shank_seg_vel_contra = compute_velocity_from_angle(shank_seg_contra, stride_duration_s)
        foot_seg_vel_ipsi = compute_velocity_from_angle(foot_seg_ipsi, stride_duration_s)
        foot_seg_vel_contra = compute_velocity_from_angle(foot_seg_contra, stride_duration_s)
    else:
        # No IMU data available - fill with NaN
        thigh_seg_ipsi = np.full(NUM_POINTS, np.nan)
        thigh_seg_contra = np.full(NUM_POINTS, np.nan)
        shank_seg_ipsi = np.full(NUM_POINTS, np.nan)
        shank_seg_contra = np.full(NUM_POINTS, np.nan)
        foot_seg_ipsi = np.full(NUM_POINTS, np.nan)
        foot_seg_contra = np.full(NUM_POINTS, np.nan)
        thigh_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        thigh_seg_vel_contra = np.full(NUM_POINTS, np.nan)
        shank_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        shank_seg_vel_contra = np.full(NUM_POINTS, np.nan)
        foot_seg_vel_ipsi = np.full(NUM_POINTS, np.nan)
        foot_seg_vel_contra = np.full(NUM_POINTS, np.nan)

    # Extract and interpolate kinetics (moments already in Nm/kg)
    # Use biological moments if available, otherwise filtered moments
    moment_key = 'moment_filt_bio' if 'moment_filt_bio' in data else 'moment_filt'
    moment_df = data[moment_key]

    hip_mom_ipsi = interpolate_to_phase(
        moment_df[f'hip_flexion_{ipsi}_moment'].values[start_idx:end_idx]
    )
    hip_mom_contra = interpolate_to_phase(
        moment_df[f'hip_flexion_{contra}_moment'].values[start_idx:end_idx]
    )
    knee_mom_ipsi = interpolate_to_phase(
        -moment_df[f'knee_angle_{ipsi}_moment'].values[start_idx:end_idx]  # Negate for flexion positive
    )
    knee_mom_contra = interpolate_to_phase(
        -moment_df[f'knee_angle_{contra}_moment'].values[start_idx:end_idx]
    )
    ankle_mom_ipsi = interpolate_to_phase(
        moment_df[f'ankle_angle_{ipsi}_moment'].values[start_idx:end_idx]
    )
    ankle_mom_contra = interpolate_to_phase(
        moment_df[f'ankle_angle_{contra}_moment'].values[start_idx:end_idx]
    )

    # Extract assistance moments from exo data (interaction torque)
    # Exo sign convention: extension positive, flexion negative
    # Our convention: flexion positive - so negate hip and knee
    # Note: This exo only has hip and knee actuators, no ankle
    # Torque units in exo.csv are Nm (absolute), divide by mass for Nm/kg
    if 'exo' in data:
        exo_df = data['exo']
        # Hip assistance (negate: exo extension+ -> our flexion+)
        hip_assist_ipsi = interpolate_to_phase(
            -exo_df[f'hip_angle_{ipsi}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        hip_assist_contra = interpolate_to_phase(
            -exo_df[f'hip_angle_{contra}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        # Knee assistance (negate: exo extension+ -> our flexion+)
        knee_assist_ipsi = interpolate_to_phase(
            -exo_df[f'knee_angle_{ipsi}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        knee_assist_contra = interpolate_to_phase(
            -exo_df[f'knee_angle_{contra}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
    else:
        # No exo data available - fill with zeros
        hip_assist_ipsi = np.zeros(NUM_POINTS)
        hip_assist_contra = np.zeros(NUM_POINTS)
        knee_assist_ipsi = np.zeros(NUM_POINTS)
        knee_assist_contra = np.zeros(NUM_POINTS)

    # Ankle has no exo actuator
    ankle_assist_ipsi = np.zeros(NUM_POINTS)
    ankle_assist_contra = np.zeros(NUM_POINTS)

    # Determine if assistance was actively applied
    assistance_active = (exo_state == 'powered')

    # Extract and interpolate GRF (normalize by body weight)
    grf_df = data['grf']
    body_weight_N = subject_mass * 9.81

    # GRF columns: fp_<side>_force_<xyz>, fp_<side>_cop_<xyz>
    # OpenSim global frame: y is vertical, x is mediolateral, z is anterior-posterior
    # Sign conventions for standardized output:
    #   - Vertical: positive = upward (supporting body weight)
    #   - Anterior: positive = propulsion (forward force on body)
    #   - Lateral: ipsi negative (medial force on body), contra positive
    grf_vert_ipsi = interpolate_to_phase(
        grf_df[f'fp_{ipsi}_force_y'].values[start_idx:end_idx] / body_weight_N
    )
    grf_vert_contra = interpolate_to_phase(
        grf_df[f'fp_{contra}_force_y'].values[start_idx:end_idx] / body_weight_N
    )
    # Negate z to make positive = propulsion (forward force)
    # Raw data has +z = braking at heel strike, -z = propulsion at push-off
    grf_ant_ipsi_raw = -grf_df[f'fp_{ipsi}_force_z'].values[start_idx:end_idx] / body_weight_N
    grf_ant_contra_raw = -grf_df[f'fp_{contra}_force_z'].values[start_idx:end_idx] / body_weight_N

    # Flip sign if walking in negative Z direction (decline walking)
    # At ~50% of stride (push-off), GRF anterior should be positive (propulsion)
    check_idx_grf = len(grf_ant_ipsi_raw) // 2
    if check_idx_grf > 0:
        # Check mean around push-off phase (40-60% of stride)
        start_check = int(len(grf_ant_ipsi_raw) * 0.4)
        end_check = int(len(grf_ant_ipsi_raw) * 0.6)
        mean_pushoff = np.nanmean(grf_ant_ipsi_raw[start_check:end_check])
        if mean_pushoff < 0:
            grf_ant_ipsi_raw = -grf_ant_ipsi_raw
            grf_ant_contra_raw = -grf_ant_contra_raw

    grf_ant_ipsi = interpolate_to_phase(grf_ant_ipsi_raw)
    grf_ant_contra = interpolate_to_phase(grf_ant_contra_raw)
    # GRF lateral: Apply sign correction based on actual data
    # Convention: ipsi should be largely negative (medial force pushing body toward midline)
    #             contra should be positive (from ipsi's reference frame)
    # Check the mean over stance phase and flip if needed
    grf_lat_ipsi_raw = grf_df[f'fp_{ipsi}_force_x'].values[start_idx:end_idx] / body_weight_N
    grf_lat_contra_raw = grf_df[f'fp_{contra}_force_x'].values[start_idx:end_idx] / body_weight_N

    # Check mean lateral GRF for ipsi during stance (0-60% of stride)
    # Ipsi mean should be negative
    end_stance = int(len(grf_lat_ipsi_raw) * 0.6)
    if end_stance > 0:
        mean_lat_ipsi = np.nanmean(grf_lat_ipsi_raw[:end_stance])
        if mean_lat_ipsi > 0:
            # Flip sign so ipsi is negative
            grf_lat_ipsi_raw = -grf_lat_ipsi_raw
            grf_lat_contra_raw = -grf_lat_contra_raw

    grf_lat_ipsi = interpolate_to_phase(grf_lat_ipsi_raw)
    grf_lat_contra = interpolate_to_phase(grf_lat_contra_raw)

    # COP (Center of Pressure) - from insole_sim (foot-relative coordinates)
    # insole_sim provides COP in OpenSim foot frame (already foot-relative)
    # Columns: insole_<side>_cop_x (anterior), insole_<side>_cop_z (lateral)
    insole_df = data['insole_sim']
    cop_ant_ipsi = interpolate_to_phase(insole_df[f'insole_{ipsi}_cop_x'].values[start_idx:end_idx])
    cop_ant_contra = interpolate_to_phase(insole_df[f'insole_{contra}_cop_x'].values[start_idx:end_idx])
    cop_lat_ipsi = interpolate_to_phase(insole_df[f'insole_{ipsi}_cop_z'].values[start_idx:end_idx])
    cop_lat_contra = interpolate_to_phase(insole_df[f'insole_{contra}_cop_z'].values[start_idx:end_idx])
    # No vertical COP in insole_sim (COP is on 2D foot surface)
    cop_vert_ipsi = np.zeros(NUM_POINTS)
    cop_vert_contra = np.zeros(NUM_POINTS)

    # Build task_info string with exoskeleton metadata per standard
    info_parts = [f"leg:{leg_side}"]

    # Add exo_state to task_info (standard key)
    info_parts.append(f"exo_state:{exo_state}")

    # Add exo_joints when exoskeleton is worn (this exo has hip and knee actuators)
    if exo_state in ('powered', 'worn_unpowered'):
        info_parts.append("exo_joints:hip_knee")

    for k, v in task_info.items():
        if v is not None:
            info_parts.append(f"{k}:{v}")
    task_info_str = ",".join(info_parts)

    # Build subject metadata
    # Format: weight_kg:<mass>,phase:<1|2|3>,day:<1|2>
    # Note: exo_state moved to task_info per standard (exo state is task-level, not subject-level)
    day_str = "2" if is_day2 else "1"
    subject_metadata = f"weight_kg:{subject_mass:.1f},phase:{collection_phase},day:{day_str}"

    # Create output DataFrame
    stride_df = pd.DataFrame({
        'subject': f"GT24_{subject_id}",
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

        # Joint moments - biological (Nm/kg)
        'hip_flexion_moment_ipsi_Nm_kg': hip_mom_ipsi,
        'hip_flexion_moment_contra_Nm_kg': hip_mom_contra,
        'knee_flexion_moment_ipsi_Nm_kg': knee_mom_ipsi,
        'knee_flexion_moment_contra_Nm_kg': knee_mom_contra,
        'ankle_dorsiflexion_moment_ipsi_Nm_kg': ankle_mom_ipsi,
        'ankle_dorsiflexion_moment_contra_Nm_kg': ankle_mom_contra,

        # Joint moments - assistance (Nm/kg)
        'hip_flexion_assistance_moment_ipsi_Nm_kg': hip_assist_ipsi,
        'hip_flexion_assistance_moment_contra_Nm_kg': hip_assist_contra,
        'knee_flexion_assistance_moment_ipsi_Nm_kg': knee_assist_ipsi,
        'knee_flexion_assistance_moment_contra_Nm_kg': knee_assist_contra,
        'ankle_dorsiflexion_assistance_moment_ipsi_Nm_kg': ankle_assist_ipsi,
        'ankle_dorsiflexion_assistance_moment_contra_Nm_kg': ankle_assist_contra,

        # Assistance flag
        'assistance_active': assistance_active,

        # Ground reaction forces (BW)
        'grf_vertical_ipsi_BW': grf_vert_ipsi,
        'grf_vertical_contra_BW': grf_vert_contra,
        'grf_anterior_ipsi_BW': grf_ant_ipsi,
        'grf_anterior_contra_BW': grf_ant_contra,
        'grf_lateral_ipsi_BW': grf_lat_ipsi,
        'grf_lateral_contra_BW': grf_lat_contra,

        # Center of pressure (m)
        'cop_anterior_ipsi_m': cop_ant_ipsi,
        'cop_anterior_contra_m': cop_ant_contra,
        'cop_lateral_ipsi_m': cop_lat_ipsi,
        'cop_lateral_contra_m': cop_lat_contra,
        'cop_vertical_ipsi_m': cop_vert_ipsi,
        'cop_vertical_contra_m': cop_vert_contra,

        # Segment angles (rad) - computed from IMU gyroscope integration
        'thigh_sagittal_angle_ipsi_rad': thigh_seg_ipsi,
        'thigh_sagittal_angle_contra_rad': thigh_seg_contra,
        'shank_sagittal_angle_ipsi_rad': shank_seg_ipsi,
        'shank_sagittal_angle_contra_rad': shank_seg_contra,
        'foot_sagittal_angle_ipsi_rad': foot_seg_ipsi,
        'foot_sagittal_angle_contra_rad': foot_seg_contra,

        # Segment velocities (rad/s) - computed from segment angles
        'thigh_sagittal_velocity_ipsi_rad_s': thigh_seg_vel_ipsi,
        'thigh_sagittal_velocity_contra_rad_s': thigh_seg_vel_contra,
        'shank_sagittal_velocity_ipsi_rad_s': shank_seg_vel_ipsi,
        'shank_sagittal_velocity_contra_rad_s': shank_seg_vel_contra,
        'foot_sagittal_velocity_ipsi_rad_s': foot_seg_vel_ipsi,
        'foot_sagittal_velocity_contra_rad_s': foot_seg_vel_contra,
    })

    return stride_df


def prepare_segmentation_df(
    data: Dict[str, pd.DataFrame],
    leg_side: str
) -> pd.DataFrame:
    """
    Prepare a DataFrame with standardized column names for segmentation.

    Args:
        data: Dictionary of raw DataFrames
        leg_side: 'l' or 'r' for ipsilateral leg

    Returns:
        DataFrame ready for stride_segmentation functions
    """
    grf_df = data['grf']
    angle_df = data['angle_filt']

    ipsi = leg_side
    contra = 'r' if leg_side == 'l' else 'l'

    n_samples = len(grf_df)

    # Time column (from angle_filt or grf)
    if 'time' in angle_df.columns:
        time_s = angle_df['time'].values
    elif 'time' in grf_df.columns:
        time_s = grf_df['time'].values
    else:
        time_s = np.arange(n_samples) / SAMPLING_RATE

    # GRF in Newtons (the segmentation library can handle N or BW)
    grf_ipsi = grf_df[f'fp_{ipsi}_force_y'].values if f'fp_{ipsi}_force_y' in grf_df.columns else np.zeros(n_samples)
    grf_contra = grf_df[f'fp_{contra}_force_y'].values if f'fp_{contra}_force_y' in grf_df.columns else np.zeros(n_samples)

    # Velocity columns (if available)
    vel_df = data.get('velocity', pd.DataFrame())
    deg2rad = np.pi / 180.0

    # Build velocity arrays (convert deg/s to rad/s if needed)
    hip_vel_ipsi = np.zeros(n_samples)
    hip_vel_contra = np.zeros(n_samples)
    knee_vel_ipsi = np.zeros(n_samples)
    knee_vel_contra = np.zeros(n_samples)

    if not vel_df.empty and len(vel_df) == n_samples:
        if f'hip_flexion_{ipsi}_velocity' in vel_df.columns:
            hip_vel_ipsi = vel_df[f'hip_flexion_{ipsi}_velocity'].values * deg2rad
        if f'hip_flexion_{contra}_velocity' in vel_df.columns:
            hip_vel_contra = vel_df[f'hip_flexion_{contra}_velocity'].values * deg2rad
        if f'knee_angle_{ipsi}_velocity' in vel_df.columns:
            knee_vel_ipsi = vel_df[f'knee_angle_{ipsi}_velocity'].values * deg2rad
        if f'knee_angle_{contra}_velocity' in vel_df.columns:
            knee_vel_contra = vel_df[f'knee_angle_{contra}_velocity'].values * deg2rad

    return pd.DataFrame({
        'time_s': time_s,
        'grf_vertical_ipsi_N': grf_ipsi,
        'grf_vertical_contra_N': grf_contra,
        'hip_flexion_velocity_ipsi_rad_s': hip_vel_ipsi,
        'hip_flexion_velocity_contra_rad_s': hip_vel_contra,
        'knee_flexion_velocity_ipsi_rad_s': knee_vel_ipsi,
        'knee_flexion_velocity_contra_rad_s': knee_vel_contra,
    })


def segment_trial_gait(
    seg_df: pd.DataFrame,
    leg_side: str
) -> List[SegmentBoundary]:
    """Segment gait cycles using heel strike detection."""
    config = GaitSegmentationConfig(
        grf_vertical_col='grf_vertical_ipsi_N',
        time_col='time_s',
        grf_threshold_N=GRF_THRESHOLD_N,
        min_stride_duration_s=MIN_STRIDE_SAMPLES / SAMPLING_RATE,
        max_stride_duration_s=MAX_STRIDE_SAMPLES / SAMPLING_RATE,
        skip_first_segments=SKIP_FIRST_STRIDES,
        skip_last_segments=SKIP_LAST_STRIDES,
        use_iqr_filtering=True,
        iqr_multiplier=IQR_MULTIPLIER,
    )
    return segment_gait_cycles(seg_df, config, leg_side=leg_side)


def segment_trial_sit_stand(
    seg_df: pd.DataFrame,
    transfer_type: str = "sit_to_stand"
) -> List[SegmentBoundary]:
    """Segment sit-to-stand or stand-to-sit transfers using GRF state machine."""
    config = SitStandConfig(
        grf_vertical_ipsi_col='grf_vertical_ipsi_N',
        grf_vertical_contra_col='grf_vertical_contra_N',
        time_col='time_s',
        velocity_cols=(
            'hip_flexion_velocity_ipsi_rad_s',
            'hip_flexion_velocity_contra_rad_s',
            'knee_flexion_velocity_ipsi_rad_s',
            'knee_flexion_velocity_contra_rad_s',
        ),
        # Thresholds in Newtons (data is in N, not BW)
        sitting_grf_threshold_N=400.0,
        standing_grf_threshold_N=600.0,
        velocity_threshold_rad_s=0.436,  # 25 deg/s
        use_iqr_filtering=True,
        iqr_multiplier=IQR_MULTIPLIER,
    )
    return segment_sit_stand_transfers(seg_df, config, transfer_type=transfer_type)


def segment_trial_jump(
    seg_df: pd.DataFrame
) -> List[SegmentBoundary]:
    """Segment jump cycles using flight phase detection."""
    config = StandingActionConfig(
        grf_vertical_ipsi_col='grf_vertical_ipsi_N',
        grf_vertical_contra_col='grf_vertical_contra_N',
        time_col='time_s',
        velocity_cols=(
            'hip_flexion_velocity_ipsi_rad_s',
            'hip_flexion_velocity_contra_rad_s',
            'knee_flexion_velocity_ipsi_rad_s',
            'knee_flexion_velocity_contra_rad_s',
        ),
        # Thresholds in Newtons
        standing_grf_threshold_N=600.0,
        flight_grf_threshold_N=50.0,
        velocity_threshold_rad_s=0.436,  # 25 deg/s
        require_flight_phase=True,
        use_iqr_filtering=True,
        iqr_multiplier=IQR_MULTIPLIER,
    )
    return segment_standing_action_cycles(seg_df, config, action_type="jump")


def segment_trial_standing_action(
    seg_df: pd.DataFrame,
    action_type: str = "squat"
) -> List[SegmentBoundary]:
    """Segment squat/lunge cycles using velocity-based detection."""
    config = StandingActionConfig(
        grf_vertical_ipsi_col='grf_vertical_ipsi_N',
        grf_vertical_contra_col='grf_vertical_contra_N',
        time_col='time_s',
        velocity_cols=(
            'hip_flexion_velocity_ipsi_rad_s',
            'hip_flexion_velocity_contra_rad_s',
            'knee_flexion_velocity_ipsi_rad_s',
            'knee_flexion_velocity_contra_rad_s',
        ),
        standing_grf_threshold_N=600.0,
        velocity_threshold_rad_s=0.436,
        require_flight_phase=False,
        use_iqr_filtering=True,
        iqr_multiplier=IQR_MULTIPLIER,
    )
    return segment_standing_action_cycles(seg_df, config, action_type=action_type)


def process_trial(
    trial_path: Path,
    subject_id: str,
    data_source: str,
    exo_filter: str = 'all'
) -> List[pd.DataFrame]:
    """
    Process all strides in a trial.

    Args:
        trial_path: Path to trial folder
        subject_id: Subject identifier
        data_source: Data source folder name (e.g., 'Parsed', 'Phase3')
        exo_filter: Filter by exo state ('all', 'exo', 'noexo')

    Returns:
        List of stride DataFrames
    """
    # Map task name
    task_folder = trial_path.name
    task, task_id, task_info = map_task_name(task_folder)

    if task is None:
        # Skip unmapped tasks for now
        return []

    # Determine collection phase, exo state, and day
    collection_phase = get_collection_phase(subject_id, data_source)
    exo_state = get_exo_state(task_folder, collection_phase)
    is_day2 = is_day2_trial(task_folder)

    # Apply exo filter
    if exo_filter == 'exo' and exo_state == 'no_exo':
        return []  # Skip no-exo trials when filtering for exo only
    if exo_filter == 'noexo' and exo_state != 'no_exo':
        return []  # Skip exo trials when filtering for no-exo only

    # Get subject mass based on exo state and day
    subject_mass = get_subject_mass(subject_id, data_source, exo_state, is_day2)

    # Load data
    data = load_trial_data(trial_path, subject_id, exo_state)
    if data is None:
        return []

    # Load IMU data for segment angle computation
    # Try Parsed format first (*_imu_sim.csv), then Complete format (Virtual_IMUs.csv)
    imu_df = None
    imu_dt = 1.0 / SAMPLING_RATE  # Default: 200Hz = 0.005s

    # Parsed format: {subject}_{trial}_imu_sim.csv (no header rows to skip)
    trial_name = trial_path.name
    prefix = f"{subject_id}_{trial_name}_"
    imu_path_parsed = trial_path / f"{prefix}imu_sim.csv"

    # Complete format: Virtual_IMUs.csv (2 header rows to skip)
    imu_path_complete = trial_path / "Virtual_IMUs.csv"

    try:
        if imu_path_parsed.exists():
            imu_df = pd.read_csv(imu_path_parsed)  # No header rows to skip
        elif imu_path_complete.exists():
            imu_df = pd.read_csv(imu_path_complete, skiprows=2)  # OpenSim format

        if imu_df is not None and 'time' in imu_df.columns and len(imu_df) > 1:
            imu_dt = np.mean(np.diff(imu_df['time'].values))
    except Exception as e:
        print(f"  Warning: Could not load IMU data: {e}")
        imu_df = None

    # Determine segmentation archetype
    archetype = TASK_ARCHETYPE_MAP.get(task, SegmentationArchetype.GAIT)

    strides = []
    step_num = 0

    # For sit-stand and standing-action tasks, process both legs together
    # since these are bilateral movements
    # Note: For non-gait tasks, we still use offset=0 (no midstance correction)
    # since they don't have a flat-foot midstance phase
    if archetype == SegmentationArchetype.SIT_STAND_TRANSFER:
        # Use left leg as reference (ipsi), right as contra
        seg_df = prepare_segmentation_df(data, 'l')
        # Extract BOTH transfer types from sit-stand trials
        # The trial contains alternating sit_to_stand and stand_to_sit movements
        segments = segment_trial_sit_stand(seg_df, transfer_type="both")

        for seg in segments:
            # Use the actual segment type (sit_to_stand or stand_to_sit)
            actual_task = seg.segment_type  # "sit_to_stand" or "stand_to_sit"
            actual_task_id = actual_task

            stride_df = process_stride(
                data=data,
                start_idx=seg.start_idx,
                end_idx=seg.end_idx,
                subject_id=subject_id,
                subject_mass=subject_mass,
                task=actual_task,
                task_id=actual_task_id,
                task_info=task_info,
                step_num=step_num,
                leg_side='l',
                collection_phase=collection_phase,
                exo_state=exo_state,
                is_day2=is_day2,
                imu_df=imu_df,
                imu_dt=imu_dt,
                use_accel_init=True  # Use accelerometer for initial orientation (no midstance phase)
            )
            if stride_df is not None:
                strides.append(stride_df)
                step_num += 1

    elif archetype == SegmentationArchetype.STANDING_ACTION:
        seg_df = prepare_segmentation_df(data, 'l')
        if task == 'jump':
            segments = segment_trial_jump(seg_df)
        else:
            segments = segment_trial_standing_action(seg_df, action_type=task)

        # Non-gait tasks: use 0 offset (no midstance flat-foot correction)
        offset_ipsi = 0.0
        offset_contra = 0.0

        for seg in segments:
            stride_df = process_stride(
                data=data,
                start_idx=seg.start_idx,
                end_idx=seg.end_idx,
                subject_id=subject_id,
                subject_mass=subject_mass,
                task=task,
                task_id=task_id,
                task_info=task_info,
                step_num=step_num,
                leg_side='l',
                collection_phase=collection_phase,
                exo_state=exo_state,
                is_day2=is_day2,
                imu_df=imu_df,
                imu_dt=imu_dt,
                segment_angle_offset_ipsi=offset_ipsi,
                segment_angle_offset_contra=offset_contra
            )
            if stride_df is not None:
                strides.append(stride_df)
                step_num += 1

    else:
        # Gait tasks: process each leg independently with two-pass segment angle calculation
        # Get ground slope from task metadata for midstance correction
        ground_slope_deg = task_info.get('incline_deg', 0.0)
        ground_slope_rad = np.radians(ground_slope_deg)

        # Skip segment angles for run task (midstance correction doesn't apply)
        skip_seg_angles = (task == 'run')

        for leg_side in ['l', 'r']:
            seg_df = prepare_segmentation_df(data, leg_side)
            segments = segment_trial_gait(seg_df, leg_side)

            # Two-pass approach for segment angles (skip if run task)
            # Pass 1: Collect stride IMU data and calculate offset
            stride_imu_list = []
            offset_ipsi = 0.0
            offset_contra = 0.0

            if not skip_seg_angles and imu_df is not None:
                for seg in segments:
                    if len(imu_df) > seg.end_idx:
                        stride_imu = imu_df.iloc[seg.start_idx:seg.end_idx].reset_index(drop=True)
                        stride_imu_list.append(stride_imu)

                # Calculate offset once for this leg/task combination
                offset_ipsi = calculate_foot_angle_offset(stride_imu_list, leg_side, imu_dt, ground_slope_rad)
                contra_side = 'r' if leg_side == 'l' else 'l'
                offset_contra = calculate_foot_angle_offset(stride_imu_list, contra_side, imu_dt, ground_slope_rad)

            # Pass 2: Process each stride with the calculated offset
            for seg in segments:
                stride_df = process_stride(
                    data=data,
                    start_idx=seg.start_idx,
                    end_idx=seg.end_idx,
                    subject_id=subject_id,
                    subject_mass=subject_mass,
                    task=task,
                    task_id=task_id,
                    task_info=task_info,
                    step_num=step_num,
                    leg_side=leg_side,
                    collection_phase=collection_phase,
                    exo_state=exo_state,
                    is_day2=is_day2,
                    imu_df=imu_df,
                    imu_dt=imu_dt,
                    segment_angle_offset_ipsi=offset_ipsi,
                    segment_angle_offset_contra=offset_contra,
                    skip_segment_angles=skip_seg_angles
                )
                if stride_df is not None:
                    strides.append(stride_df)
                    step_num += 1

    return strides


def process_subject(subject_path: Path, subject_id: str, data_source: str,
                    exo_filter: str = 'all') -> pd.DataFrame:
    """
    Process all trials for a subject.

    Args:
        subject_path: Path to subject folder
        subject_id: Subject identifier
        data_source: Data source folder name (e.g., 'Parsed', 'Phase3')
        exo_filter: Filter by exo state ('all', 'exo', 'noexo')

    Returns:
        Combined DataFrame of all strides
    """
    collection_phase = get_collection_phase(subject_id, data_source)
    has_noexo = subject_id in SUBJECTS_WITH_NOEXO_DATA

    # Get default mass for display (actual mass is computed per-trial based on exo state)
    default_mass = get_subject_mass(subject_id, data_source)
    print(f"  Default mass: {default_mass:.1f} kg, Phase: {collection_phase}, Has no-exo data: {has_noexo}")

    all_strides = []

    # Get all trial folders
    trial_folders = [f for f in subject_path.iterdir() if f.is_dir()]

    for trial_path in tqdm(trial_folders, desc=f"  {subject_id} trials", leave=False):
        strides = process_trial(trial_path, subject_id, data_source, exo_filter)
        all_strides.extend(strides)

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert GaTech 2024 TaskAgnostic to parquet')
    parser.add_argument('--input', '-i', type=str, default=None,
                       help='Path to data folder (or use --base-path for Phase1And2 + Phase3)')
    parser.add_argument('--base-path', type=str, default=None,
                       help='Base path containing Phase1And2 and Phase3 subfolders')
    parser.add_argument('--output', '-o', type=str, default='gtech_2024_phase.parquet',
                       help='Output parquet filename')
    parser.add_argument('--output-dir', type=str, default='../../../converted_datasets',
                       help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                       help='Specific subjects to process (e.g., BT24)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: process only first subject')

    # No-exo data flags (for Phase 3 day 2 testing - BT02, BT13, BT18, BT23, BT24)
    parser.add_argument('--include-noexo', action='store_true',
                       help='Include no-exo trials (day 2 testing for BT02, BT13, BT18, BT23, BT24)')
    parser.add_argument('--noexo-only', action='store_true',
                       help='Only process no-exo trials (excludes exo trials)')
    parser.add_argument('--exo-filter', type=str, choices=['all', 'exo', 'noexo'],
                       default='all',
                       help='Filter by exo state: all (default), exo (only exo trials), noexo (only no-exo trials)')

    args = parser.parse_args()

    # Handle noexo flag interactions
    if args.noexo_only:
        args.exo_filter = 'noexo'
    elif not args.include_noexo and args.exo_filter == 'all':
        # By default, include all available data
        args.exo_filter = 'all'

    # Setup paths
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect input paths - support both single input and base-path with Phase1And2/Phase3
    input_paths = []

    def find_subjects_path(phase_path: Path) -> Optional[Path]:
        """Find the path containing subject folders (BT01, BT02, etc.)."""
        # Check if subjects are directly in the path
        direct_subjects = [f for f in phase_path.iterdir() if f.is_dir() and f.name.startswith('BT')]
        if direct_subjects:
            return phase_path
        # Check for nested 'Parsed' folder
        parsed_path = phase_path / 'Parsed'
        if parsed_path.exists():
            nested_subjects = [f for f in parsed_path.iterdir() if f.is_dir() and f.name.startswith('BT')]
            if nested_subjects:
                return parsed_path
        return None

    if args.base_path:
        base = Path(args.base_path)
        # Try both naming conventions: Phase1And2 or Phase1And2_Parsed
        for phase12_name in ['Phase1And2', 'Phase1And2_Parsed']:
            phase12_path = base / phase12_name
            if phase12_path.exists():
                subjects_path = find_subjects_path(phase12_path)
                if subjects_path:
                    input_paths.append(('Phase1And2', subjects_path))
                    print(f"Found Phase1And2 subjects at: {subjects_path}")
                    break
        for phase3_name in ['Phase3', 'Phase3_Parsed']:
            phase3_path = base / phase3_name
            if phase3_path.exists():
                subjects_path = find_subjects_path(phase3_path)
                if subjects_path:
                    input_paths.append(('Phase3', subjects_path))
                    print(f"Found Phase3 subjects at: {subjects_path}")
                    break
        if not input_paths:
            print(f"Error: No Phase1And2 or Phase3 folders found in {base}")
            return
    elif args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input path not found: {input_path}")
            return
        input_paths.append((input_path.name, input_path))
    else:
        # Default: try to find Phase1And2 and Phase3 in common location
        default_base = Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic')
        if default_base.exists():
            for phase12_name in ['Phase1And2', 'Phase1And2_Parsed']:
                phase12_path = default_base / phase12_name
                if phase12_path.exists():
                    subjects_path = find_subjects_path(phase12_path)
                    if subjects_path:
                        input_paths.append(('Phase1And2', subjects_path))
                        print(f"Found Phase1And2 subjects at: {subjects_path}")
                        break
            for phase3_name in ['Phase3', 'Phase3_Parsed']:
                phase3_path = default_base / phase3_name
                if phase3_path.exists():
                    subjects_path = find_subjects_path(phase3_path)
                    if subjects_path:
                        input_paths.append(('Phase3', subjects_path))
                        print(f"Found Phase3 subjects at: {subjects_path}")
                        break
        if not input_paths:
            print("Error: No input specified. Use --input, --base-path, or ensure data exists at default location")
            return

    # Collect all subject folders from all input paths
    subject_folders = []
    for data_source, input_path in input_paths:
        folders = sorted([f for f in input_path.iterdir() if f.is_dir()])
        for f in folders:
            subject_folders.append((data_source, f))

    if args.subjects:
        subject_folders = [(ds, f) for ds, f in subject_folders if f.name in args.subjects]

    if args.test:
        subject_folders = subject_folders[:1]
        print(f"Test mode: processing only {subject_folders[0][1].name}")

    # Count unique subjects (same subject may appear in multiple phases)
    unique_subjects = set(f.name for _, f in subject_folders)
    print(f"Found {len(subject_folders)} subject-phase combinations ({len(unique_subjects)} unique subjects)")
    print(f"Exo filter: {args.exo_filter}")

    # Process each subject
    all_data = []

    for data_source, subject_path in tqdm(subject_folders, desc="Processing subjects"):
        subject_id = subject_path.name
        print(f"\nProcessing {subject_id} from {data_source}...")

        subject_data = process_subject(subject_path, subject_id, data_source, args.exo_filter)

        if not subject_data.empty:
            all_data.append(subject_data)
            print(f"  Extracted {len(subject_data) // NUM_POINTS} strides")
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

        # Show exo state distribution (now in task_info per standard)
        exo_states = combined_df['task_info'].str.extract(r'exo_state:(\w+)')[0].value_counts()
        print(f"\nExo states (strides):")
        for state, count in exo_states.items():
            print(f"  {state}: {count // NUM_POINTS}")

        combined_df.to_parquet(output_path, index=False)
        print("Done!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
