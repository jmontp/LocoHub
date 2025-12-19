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
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from scipy.interpolate import interp1d
from tqdm import tqdm

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

# Task mapping: source task name patterns -> (standard_task, task_id_template)
TASK_MAPPING = {
    # Level walking at different speeds (walking = no flight phase)
    r'normal_walk.*_0-6': ('level_walking', 'level_0.6ms'),
    r'normal_walk.*_1-2': ('level_walking', 'level_1.2ms'),
    r'normal_walk.*_1-8': ('level_walking', 'level_1.8ms'),
    # Fast speeds have flight phase (17-22% of gait cycle) -> classify as run
    r'normal_walk.*_2-0': ('run', 'run_2.0ms'),
    r'normal_walk.*_2-5': ('run', 'run_2.5ms'),
    # Shuffle and skip have non-standard gait - exclude from level_walking
    r'normal_walk.*_shuffle': (None, 'shuffle'),  # Exclude: lateral shuffling
    r'normal_walk.*_skip': (None, 'skip'),  # Exclude: skipping gait

    # Incline/decline walking
    r'incline_walk.*_up5': ('incline_walking', 'incline_5deg'),
    r'incline_walk.*_up10': ('incline_walking', 'incline_10deg'),
    r'incline_walk.*_down5': ('decline_walking', 'decline_5deg'),
    r'incline_walk.*_down10': ('decline_walking', 'decline_10deg'),

    # Stairs
    r'stairs.*_up': ('stair_ascent', 'stair_ascent'),
    r'stairs.*_down': ('stair_descent', 'stair_descent'),

    # Other activities
    r'sit_to_stand': ('sit_to_stand', 'sit_to_stand'),
    r'squats': ('squat', 'squat'),
    r'walk_backward': ('backward_walking', 'backward_walking'),
    r'meander': (None, 'meander'),  # Exclude: non-straight path walking
    r'curb_up': ('stair_ascent', 'curb_up'),
    r'curb_down': ('stair_descent', 'curb_down'),
    r'step_ups': ('stair_ascent', 'step_up'),

    # Dynamic activities (may not have clear gait cycles)
    r'jump': ('jump', 'jump'),
    r'lunges': ('lunge', 'lunge'),
    r'cutting': ('cutting', 'cutting'),
}

# Subject mass data (kg) from readme
# Phase1And2 masses (w/o exo | w/ exo - we use w/ exo since all data collected with exo worn)
SUBJECT_MASS_PHASE12 = {
    'BT01': 87.02, 'BT02': 79.09, 'BT03': 101.52, 'BT04': 106.04,
    'BT06': 85.78, 'BT07': 70.61, 'BT08': 75.67, 'BT09': 88.97,
    'BT10': 100.11, 'BT11': 56.98, 'BT12': 84.62, 'BT13': 96.74,
    'BT14': 74.35, 'BT15': 65.87, 'BT16': 72.03, 'BT17': 67.36,
}

# Phase3 masses (w/ exo)
SUBJECT_MASS_PHASE3 = {
    'BT01': 84.28, 'BT02': 79.10, 'BT13': 96.03,
    'BT18': 74.96, 'BT19': 76.84, 'BT20': 62.50,
    'BT21': 65.86, 'BT22': 84.27, 'BT23': 74.24, 'BT24': 84.84,
}

# Collection phase info:
# Phase 1 (BT01-BT12): Unpowered data + some heuristic controller trials
# Phase 2 (BT13-BT17): Preliminary neural network model, all powered
# Phase 3 (BT01,BT02,BT13,BT18-BT24): Final model validation, all powered
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
    - 'unknown': Cannot determine state

    Note: All subjects wore the clothing-integrated exoskeleton during data collection.
    """
    if '_on' in task_folder:
        return 'powered'
    elif '_off' in task_folder:
        return 'worn_unpowered'
    else:
        # Phase 2 and 3 were mostly powered
        if collection_phase >= 2:
            return 'powered'
        return 'unknown'


def get_subject_mass(subject_id: str, data_source: str) -> float:
    """Get subject mass based on ID and data source."""
    if 'Phase3' in data_source or subject_id in PHASE3_SUBJECTS:
        if subject_id in SUBJECT_MASS_PHASE3:
            return SUBJECT_MASS_PHASE3[subject_id]

    if subject_id in SUBJECT_MASS_PHASE12:
        return SUBJECT_MASS_PHASE12[subject_id]

    print(f"  Warning: No mass data for {subject_id}, using 75 kg default")
    return 75.0


def detect_heel_strikes(grf_vertical: np.ndarray, threshold: float = GRF_THRESHOLD_N) -> List[int]:
    """
    Detect heel strikes from vertical GRF using threshold crossing.

    Heel strike is detected when GRF crosses upward through threshold.

    Args:
        grf_vertical: Vertical ground reaction force array (N)
        threshold: Force threshold for detection (N)

    Returns:
        List of indices where heel strikes occur
    """
    # Find upward crossings through threshold
    above_threshold = grf_vertical > threshold
    crossings = np.diff(above_threshold.astype(int))
    heel_strikes = np.where(crossings == 1)[0] + 1  # +1 because diff reduces length by 1

    return heel_strikes.tolist()


def detect_toe_offs(grf_vertical: np.ndarray, threshold: float = GRF_THRESHOLD_N) -> List[int]:
    """
    Detect toe-offs from vertical GRF using threshold crossing.

    Toe-off is detected when GRF crosses downward through threshold.

    Args:
        grf_vertical: Vertical ground reaction force array (N)
        threshold: Force threshold for detection (N)

    Returns:
        List of indices where toe-offs occur
    """
    above_threshold = grf_vertical > threshold
    crossings = np.diff(above_threshold.astype(int))
    toe_offs = np.where(crossings == -1)[0] + 1

    return toe_offs.tolist()


def filter_strides_by_duration_iqr(
    heel_strikes: List[int],
    sampling_rate: float = SAMPLING_RATE,
    iqr_multiplier: float = IQR_MULTIPLIER
) -> List[int]:
    """
    Filter heel strikes to remove strides with outlier durations.

    Uses IQR method: keep strides where Q1 - iqr_multiplier*IQR < duration < Q3 + iqr_multiplier*IQR

    Args:
        heel_strikes: List of heel strike indices
        sampling_rate: Sampling rate in Hz
        iqr_multiplier: Multiplier for IQR bounds (default 1.5)

    Returns:
        Filtered list of heel strikes
    """
    if len(heel_strikes) < 4:  # Need enough strides to compute quartiles
        return heel_strikes

    # Compute stride durations in seconds
    durations = np.diff(heel_strikes) / sampling_rate

    # Compute IQR bounds
    q1, q3 = np.percentile(durations, [25, 75])
    iqr = q3 - q1
    lower_bound = q1 - iqr_multiplier * iqr
    upper_bound = q3 + iqr_multiplier * iqr

    # Keep heel strikes that form valid-duration strides
    valid_mask = (durations >= lower_bound) & (durations <= upper_bound)

    # Build filtered list: keep HS[i] if stride from HS[i] to HS[i+1] is valid
    filtered = []
    for i, is_valid in enumerate(valid_mask):
        if is_valid:
            if not filtered:
                filtered.append(heel_strikes[i])  # Include start of valid stride
            filtered.append(heel_strikes[i + 1])  # Include end of valid stride

    return filtered


def remove_transition_strides(
    heel_strikes: List[int],
    skip_first: int = SKIP_FIRST_STRIDES,
    skip_last: int = SKIP_LAST_STRIDES
) -> List[int]:
    """
    Remove transition strides at the beginning and end of a trial.

    Args:
        heel_strikes: List of heel strike indices
        skip_first: Number of strides to skip at beginning (default 2)
        skip_last: Number of strides to skip at end (default 1)

    Returns:
        Filtered list of heel strikes
    """
    # Need at least skip_first + skip_last + 2 heel strikes for 1 valid stride
    min_required = skip_first + skip_last + 2
    if len(heel_strikes) < min_required:
        return []

    # Skip first N strides means start from heel_strike[skip_first]
    # Skip last N strides means end at heel_strike[-(skip_last+1)] to get end of last valid stride
    start_idx = skip_first
    end_idx = len(heel_strikes) - skip_last

    return heel_strikes[start_idx:end_idx]


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


def map_task_name(task_folder: str) -> Tuple[Optional[str], Optional[str], Dict]:
    """
    Map source task folder name to standardized task name and ID.

    Args:
        task_folder: Source folder name (e.g., 'normal_walk_1_1_1-2_on')

    Returns:
        Tuple of (task_name, task_id, task_info_dict)
    """
    task_info = {}

    # Check if exoskeleton is powered
    if '_on' in task_folder:
        task_info['exo_powered'] = True
    elif '_off' in task_folder:
        task_info['exo_powered'] = False
    else:
        task_info['exo_powered'] = None

    # Extract speed if present (e.g., '1-2' -> 1.2 m/s)
    speed_match = re.search(r'(\d)-(\d)', task_folder)
    if speed_match:
        speed = float(f"{speed_match.group(1)}.{speed_match.group(2)}")
        task_info['speed_m_s'] = speed

    # Find matching task pattern
    for pattern, (task_name, task_id) in TASK_MAPPING.items():
        if re.search(pattern, task_folder):
            return task_name, task_id, task_info

    # Default: use folder name as task
    return None, None, task_info


def load_trial_data(trial_path: Path, subject_id: str) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load all CSV files for a trial.

    Args:
        trial_path: Path to trial folder
        subject_id: Subject identifier (e.g., 'BT24')

    Returns:
        Dictionary with DataFrames for each data type
    """
    trial_name = trial_path.name
    prefix = f"{subject_id}_{trial_name}_"

    data = {}

    # Required files
    required_files = ['angle_filt', 'moment_filt', 'grf', 'velocity']
    optional_files = ['moment_filt_bio', 'power', 'power_bio']

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
    exo_state: str
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
        exo_state: Exoskeleton state ('powered', 'worn_unpowered', 'unknown')

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

    # Extract and interpolate GRF (normalize by body weight)
    grf_df = data['grf']
    body_weight_N = subject_mass * 9.81

    # GRF columns: fp_<side>_force_<xyz>, fp_<side>_cop_<xyz>
    # y is vertical, x is mediolateral, z is anterior-posterior
    grf_vert_ipsi = interpolate_to_phase(
        grf_df[f'fp_{ipsi}_force_y'].values[start_idx:end_idx] / body_weight_N
    )
    grf_vert_contra = interpolate_to_phase(
        grf_df[f'fp_{contra}_force_y'].values[start_idx:end_idx] / body_weight_N
    )
    grf_ant_ipsi = interpolate_to_phase(
        grf_df[f'fp_{ipsi}_force_z'].values[start_idx:end_idx] / body_weight_N
    )
    grf_ant_contra = interpolate_to_phase(
        grf_df[f'fp_{contra}_force_z'].values[start_idx:end_idx] / body_weight_N
    )
    grf_lat_ipsi = interpolate_to_phase(
        grf_df[f'fp_{ipsi}_force_x'].values[start_idx:end_idx] / body_weight_N
    )
    grf_lat_contra = interpolate_to_phase(
        grf_df[f'fp_{contra}_force_x'].values[start_idx:end_idx] / body_weight_N
    )

    # COP (already in meters)
    cop_ant_ipsi = interpolate_to_phase(grf_df[f'fp_{ipsi}_cop_z'].values[start_idx:end_idx])
    cop_ant_contra = interpolate_to_phase(grf_df[f'fp_{contra}_cop_z'].values[start_idx:end_idx])
    cop_lat_ipsi = interpolate_to_phase(grf_df[f'fp_{ipsi}_cop_x'].values[start_idx:end_idx])
    cop_lat_contra = interpolate_to_phase(grf_df[f'fp_{contra}_cop_x'].values[start_idx:end_idx])
    cop_vert_ipsi = interpolate_to_phase(grf_df[f'fp_{ipsi}_cop_y'].values[start_idx:end_idx])
    cop_vert_contra = interpolate_to_phase(grf_df[f'fp_{contra}_cop_y'].values[start_idx:end_idx])

    # Build task_info string
    info_parts = [f"leg:{leg_side}"]
    for k, v in task_info.items():
        if v is not None:
            info_parts.append(f"{k}:{v}")
    task_info_str = ",".join(info_parts)

    # Build subject metadata
    # Format: weight_kg:<mass>,phase:<1|2|3>,exo:<powered|worn_unpowered|unknown>
    subject_metadata = f"weight_kg:{subject_mass:.1f},phase:{collection_phase},exo:{exo_state}"

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

        # Joint moments (Nm/kg)
        'hip_flexion_moment_ipsi_Nm_kg': hip_mom_ipsi,
        'hip_flexion_moment_contra_Nm_kg': hip_mom_contra,
        'knee_flexion_moment_ipsi_Nm_kg': knee_mom_ipsi,
        'knee_flexion_moment_contra_Nm_kg': knee_mom_contra,
        'ankle_dorsiflexion_moment_ipsi_Nm_kg': ankle_mom_ipsi,
        'ankle_dorsiflexion_moment_contra_Nm_kg': ankle_mom_contra,

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
    })

    return stride_df


def process_trial(
    trial_path: Path,
    subject_id: str,
    subject_mass: float,
    data_source: str
) -> List[pd.DataFrame]:
    """
    Process all strides in a trial.

    Args:
        trial_path: Path to trial folder
        subject_id: Subject identifier
        subject_mass: Subject mass in kg
        data_source: Data source folder name (e.g., 'Parsed', 'Phase3')

    Returns:
        List of stride DataFrames
    """
    # Map task name
    task_folder = trial_path.name
    task, task_id, task_info = map_task_name(task_folder)

    if task is None:
        # Skip unmapped tasks for now
        return []

    # Determine collection phase and exo state
    collection_phase = get_collection_phase(subject_id, data_source)
    exo_state = get_exo_state(task_folder, collection_phase)

    # Load data
    data = load_trial_data(trial_path, subject_id)
    if data is None:
        return []

    # Detect heel strikes for both legs
    grf_df = data['grf']

    strides = []
    step_num = 0

    for leg_side in ['l', 'r']:
        grf_col = f'fp_{leg_side}_force_y'
        if grf_col not in grf_df.columns:
            continue

        grf_vertical = grf_df[grf_col].values
        heel_strikes = detect_heel_strikes(grf_vertical)

        # Apply transition stride removal (skip first 2, last 1 strides per trial)
        heel_strikes = remove_transition_strides(heel_strikes)

        # Apply IQR-based duration filtering to remove outlier strides
        heel_strikes = filter_strides_by_duration_iqr(heel_strikes)

        if len(heel_strikes) < 2:
            continue

        # Process each stride (heel strike to heel strike)
        for i in range(len(heel_strikes) - 1):
            start_idx = heel_strikes[i]
            end_idx = heel_strikes[i + 1]

            stride_df = process_stride(
                data=data,
                start_idx=start_idx,
                end_idx=end_idx,
                subject_id=subject_id,
                subject_mass=subject_mass,
                task=task,
                task_id=task_id,
                task_info=task_info,
                step_num=step_num,
                leg_side=leg_side,
                collection_phase=collection_phase,
                exo_state=exo_state
            )

            if stride_df is not None:
                strides.append(stride_df)
                step_num += 1

    return strides


def process_subject(subject_path: Path, subject_id: str, data_source: str) -> pd.DataFrame:
    """
    Process all trials for a subject.

    Args:
        subject_path: Path to subject folder
        subject_id: Subject identifier
        data_source: Data source folder name (e.g., 'Parsed', 'Phase3')

    Returns:
        Combined DataFrame of all strides
    """
    subject_mass = get_subject_mass(subject_id, data_source)
    collection_phase = get_collection_phase(subject_id, data_source)

    print(f"  Mass: {subject_mass:.1f} kg, Phase: {collection_phase}")

    all_strides = []

    # Get all trial folders
    trial_folders = [f for f in subject_path.iterdir() if f.is_dir()]

    for trial_path in tqdm(trial_folders, desc=f"  {subject_id} trials", leave=False):
        strides = process_trial(trial_path, subject_id, subject_mass, data_source)
        all_strides.extend(strides)

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert GaTech 2024 TaskAgnostic to parquet')
    parser.add_argument('--input', '-i', type=str, default='Parsed',
                       help='Path to Parsed data folder')
    parser.add_argument('--output', '-o', type=str, default='gtech_2024_phase.parquet',
                       help='Output parquet filename')
    parser.add_argument('--output-dir', type=str, default='../../../converted_datasets',
                       help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                       help='Specific subjects to process (e.g., BT24)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: process only first subject')

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"Error: Input path not found: {input_path}")
        return

    # Find subjects
    subject_folders = sorted([f for f in input_path.iterdir() if f.is_dir()])

    if args.subjects:
        subject_folders = [f for f in subject_folders if f.name in args.subjects]

    if args.test:
        subject_folders = subject_folders[:1]
        print(f"Test mode: processing only {subject_folders[0].name}")

    print(f"Found {len(subject_folders)} subjects to process")

    # Process each subject
    all_data = []

    for subject_path in tqdm(subject_folders, desc="Processing subjects"):
        subject_id = subject_path.name
        print(f"\nProcessing {subject_id}...")

        subject_data = process_subject(subject_path, subject_id, args.input)

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

        combined_df.to_parquet(output_path, index=False)
        print("Done!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
