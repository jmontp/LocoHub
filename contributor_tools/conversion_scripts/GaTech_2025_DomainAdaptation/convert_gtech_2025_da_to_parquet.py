#!/usr/bin/env python3
"""
Convert GaTech 2025 Domain Adaptation dataset to standardized phase-normalized parquet format.

This script converts the "Deep Domain Adaptation Eliminates Costly Data Required for
Task-Agnostic Wearable Robotic Control" dataset (Science Robotics 2025) to the LocoHub
standardized format.

Source: https://repository.gatech.edu/entities/publication/d6798aa7-541e-4f6e-980e-4855cdd3f629
Paper: Scherpereel et al., Science Robotics (2025)

Data structure:
- 8 subjects (BT01-BT08) — different participants from GaTech_2024_TaskAgnostic
- 6 activity categories (walking, backward walking, stairs, ball toss, cutting, sit-stand)
- 3 model variants per trial (baseline, 4t4s, 0task)
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
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))
from common.stride_segmentation import (
    SegmentationArchetype,
    SegmentBoundary,
    GaitSegmentationConfig,
    SitStandConfig,
    TASK_ARCHETYPE_MAP,
    segment_gait_cycles,
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
TASK_MAPPING = {
    # Level walking at different speeds
    r'normal_walk.*_0-6': ('level_walking', 'level_0.6ms', {'incline_deg': 0.0}),
    r'normal_walk.*_1-2': ('level_walking', 'level_1.2ms', {'incline_deg': 0.0}),
    r'normal_walk.*_1-8': ('level_walking', 'level_1.8ms', {'incline_deg': 0.0}),
    # Shuffle is lateral, exclude
    r'normal_walk.*_shuffle': (None, 'shuffle', {}),

    # Stairs
    r'stairs.*_up': ('stair_ascent', 'stair_ascent', {'incline_deg': 0.0}),
    r'stairs.*_down': ('stair_descent', 'stair_descent', {'incline_deg': 0.0}),

    # Backward walking
    r'walk_backward.*_0-6': ('backward_walking', 'backward_0.6ms', {'incline_deg': 0.0}),
    r'walk_backward.*_0-8': ('backward_walking', 'backward_0.8ms', {'incline_deg': 0.0}),
    r'walk_backward.*_1-0': ('backward_walking', 'backward_1.0ms', {'incline_deg': 0.0}),

    # Sit-to-stand
    r'sit_to_stand': ('sit_to_stand', 'sit_to_stand', {'incline_deg': 0.0}),

    # Non-cyclic activities (exclude from standard tasks)
    r'cutting': (None, 'cutting', {}),
    r'ball_toss': (None, 'ball_toss', {}),
    r'start_stop': (None, 'start_stop', {}),
}

# Subject mass data (kg) from readme
# Format: subject_id -> {'without_exo': mass, 'with_exo': mass}
# Using with_exo mass since all data collected with exo worn
SUBJECT_MASS = {
    'BT01': {'without_exo': 88.38, 'with_exo': 95.33},
    'BT02': {'without_exo': 57.92, 'with_exo': 64.94},
    'BT03': {'without_exo': 63.90, 'with_exo': 70.68},
    'BT04': {'without_exo': 55.85, 'with_exo': 62.64},
    'BT05': {'without_exo': 65.49, 'with_exo': 72.45},
    'BT06': {'without_exo': 64.01, 'with_exo': 70.72},
    'BT07': {'without_exo': 73.95, 'with_exo': 81.23},
    'BT08': {'without_exo': 76.28, 'with_exo': 83.31},
}

# Known model variant abbreviations
MODEL_VARIANTS = {'baseline', '4t4s', '0task'}


def get_subject_mass(subject_id: str) -> float:
    """Get subject mass (with exo) in kg."""
    if subject_id in SUBJECT_MASS:
        return SUBJECT_MASS[subject_id]['with_exo']
    print(f"  Warning: No mass data for {subject_id}, using 75 kg default")
    return 75.0


def get_model_variant(folder_name: str) -> Optional[str]:
    """
    Extract the model variant from a task folder name.

    The model variant (baseline, 4t4s, 0task) is embedded in the folder name,
    e.g. 'normal_walk_1_baseline_1-2_on' -> 'baseline'

    Returns:
        Model variant string or None if not recognized
    """
    for variant in MODEL_VARIANTS:
        # Check for variant as a word boundary in the folder name
        if f'_{variant}_' in folder_name or folder_name.startswith(f'{variant}_'):
            return variant
    return None


def interpolate_to_phase(data: np.ndarray, num_points: int = NUM_POINTS) -> np.ndarray:
    """Interpolate time-series data to fixed number of phase points (0-100%)."""
    if len(data) < 2:
        return np.full(num_points, np.nan)

    x_original = np.linspace(0, 100, len(data))
    x_target = np.linspace(0, 100, num_points)

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
    """Compute angular velocity from angle data using gradient."""
    dt = stride_duration_s / (len(angle_rad) - 1)
    return np.gradient(angle_rad) / dt


def compute_acceleration_from_velocity(velocity_rad_s: np.ndarray, stride_duration_s: float) -> np.ndarray:
    """Compute angular acceleration from velocity data using gradient."""
    dt = stride_duration_s / (len(velocity_rad_s) - 1)
    return np.gradient(velocity_rad_s) / dt


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
    """
    deg2rad = np.pi / 180.0

    foot_gz = imu_df[f'foot_imu_{side}_gyro_z'].values * deg2rad
    shank_gz = imu_df[f'shank_imu_{side}_gyro_z'].values * deg2rad
    thigh_gz = imu_df[f'thigh_imu_{side}_gyro_z'].values * deg2rad

    foot_angle = np.cumsum(foot_gz) * dt + offset
    ankle_angle = np.cumsum(shank_gz - foot_gz) * dt
    knee_angle = np.cumsum(thigh_gz - shank_gz) * dt

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
    For tasks without a flat-foot midstance phase (sit_to_stand, stand_to_sit).
    """
    deg2rad = np.pi / 180.0

    thigh_ax = imu_df[f'thigh_imu_{side}_accel_x'].values
    thigh_ay = imu_df[f'thigh_imu_{side}_accel_y'].values
    shank_ax = imu_df[f'shank_imu_{side}_accel_x'].values
    shank_ay = imu_df[f'shank_imu_{side}_accel_y'].values
    foot_ax = imu_df[f'foot_imu_{side}_accel_x'].values
    foot_ay = imu_df[f'foot_imu_{side}_accel_y'].values

    thigh_gz = imu_df[f'thigh_imu_{side}_gyro_z'].values * deg2rad
    shank_gz = imu_df[f'shank_imu_{side}_gyro_z'].values * deg2rad
    foot_gz = imu_df[f'foot_imu_{side}_gyro_z'].values * deg2rad

    n = min(init_samples, len(thigh_ax))
    thigh_init = np.arctan2(np.mean(thigh_ax[:n]), np.mean(thigh_ay[:n]))
    shank_init = np.arctan2(np.mean(shank_ax[:n]), np.mean(shank_ay[:n]))
    foot_init = np.arctan2(np.mean(foot_ax[:n]), np.mean(foot_ay[:n]))

    thigh_delta = np.cumsum(thigh_gz) * dt
    shank_delta = np.cumsum(shank_gz) * dt
    foot_delta = np.cumsum(foot_gz) * dt

    thigh_angle = thigh_init + thigh_delta
    shank_angle = shank_init + shank_delta
    foot_angle = foot_init + foot_delta

    standing_samples = min(init_samples, len(thigh_angle))
    if transfer_type == 'sit_to_stand':
        thigh_offset = np.mean(thigh_angle[-standing_samples:])
        shank_offset = np.mean(shank_angle[-standing_samples:])
        foot_offset = np.mean(foot_angle[-standing_samples:])
    else:
        thigh_offset = np.mean(thigh_angle[:standing_samples])
        shank_offset = np.mean(shank_angle[:standing_samples])
        foot_offset = np.mean(foot_angle[:standing_samples])

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
    """Calculate single foot angle offset by averaging midstance across all strides."""
    deg2rad = np.pi / 180.0
    midstance_values = []

    for stride_imu in stride_imu_list:
        if stride_imu.empty:
            continue

        foot_gz_col = f'foot_imu_{side}_gyro_z'
        if foot_gz_col not in stride_imu.columns:
            continue

        foot_gz = stride_imu[foot_gz_col].values * deg2rad
        foot_angle_raw = np.cumsum(foot_gz) * dt

        n = len(foot_angle_raw)
        ms_start = int(0.15 * n)
        ms_end = int(0.35 * n)

        if ms_end > ms_start:
            midstance_values.append(np.mean(foot_angle_raw[ms_start:ms_end]))

    if not midstance_values:
        return 0.0

    avg_midstance = np.mean(midstance_values)
    return ground_slope_rad - avg_midstance


def map_task_name(task_folder: str) -> Tuple[Optional[str], Optional[str], Dict]:
    """Map source task folder name to standardized task name and ID.

    Folder names include model variant and exo state, e.g.:
        'normal_walk_1_baseline_1-2_on'
        'stairs_1_4t4s_3_up_on'
        'sit_to_stand_1_0task_short-arm_on'
    """
    task_info = {}

    # Extract speed if present (e.g., '1-2' -> 1.2 m/s)
    # Be careful not to match stair numbers like '_3_up' or '_10_down'
    # Speed pattern: digit-digit at end or before _on
    speed_match = re.search(r'_(\d)-(\d)_', task_folder)
    if speed_match:
        speed = float(f"{speed_match.group(1)}.{speed_match.group(2)}")
        task_info['speed_m_s'] = speed

    for pattern, (task_name, task_id, task_metadata) in TASK_MAPPING.items():
        if re.search(pattern, task_folder):
            task_info.update(task_metadata)
            return task_name, task_id, task_info

    return None, None, task_info


def load_trial_data(trial_path: Path, subject_id: str) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Load all CSV files for a trial.

    Args:
        trial_path: Path to trial folder containing CSVs
        subject_id: Subject identifier (e.g., 'BT01')

    Returns:
        Dictionary with DataFrames for each data type
    """
    folder_name = trial_path.name
    prefix = f"{subject_id}_{folder_name}_"

    data = {}

    required_files = ['angle_filt', 'moment_filt', 'grf', 'velocity', 'insole_sim']
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
    model_variant: str,
    imu_df: Optional[pd.DataFrame] = None,
    imu_dt: float = 0.005,
    segment_angle_offset_ipsi: float = 0.0,
    segment_angle_offset_contra: float = 0.0,
    use_accel_init: bool = False,
    skip_segment_angles: bool = False
) -> Optional[pd.DataFrame]:
    """
    Process a single stride from heel strike to heel strike.

    Returns:
        DataFrame with 150 rows (one per phase point) or None if invalid
    """
    stride_len = end_idx - start_idx
    if stride_len < MIN_STRIDE_SAMPLES or stride_len > MAX_STRIDE_SAMPLES:
        return None

    time_data = data['angle_filt']['time'].values
    stride_duration_s = time_data[end_idx] - time_data[start_idx]

    if stride_duration_s <= 0:
        return None

    ipsi = leg_side
    contra = 'r' if leg_side == 'l' else 'l'

    phase = np.linspace(0, 100, NUM_POINTS)
    phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)

    # Extract and interpolate kinematics
    angle_df = data['angle_filt']
    deg2rad = np.pi / 180.0

    # Hip flexion (OpenSim: flexion positive — matches our convention)
    hip_ipsi_deg = angle_df[f'hip_flexion_{ipsi}'].values[start_idx:end_idx]
    hip_contra_deg = angle_df[f'hip_flexion_{contra}'].values[start_idx:end_idx]
    hip_ipsi_rad = interpolate_to_phase(hip_ipsi_deg * deg2rad)
    hip_contra_rad = interpolate_to_phase(hip_contra_deg * deg2rad)

    # Knee flexion (OpenSim: extension positive — negate for flexion positive)
    knee_ipsi_deg = angle_df[f'knee_angle_{ipsi}'].values[start_idx:end_idx]
    knee_contra_deg = angle_df[f'knee_angle_{contra}'].values[start_idx:end_idx]
    knee_ipsi_rad = interpolate_to_phase(-knee_ipsi_deg * deg2rad)
    knee_contra_rad = interpolate_to_phase(-knee_contra_deg * deg2rad)

    # Ankle dorsiflexion (OpenSim: plantarflexion positive — keep as-is, dorsiflexion = negative plantarflexion)
    ankle_ipsi_deg = angle_df[f'ankle_angle_{ipsi}'].values[start_idx:end_idx]
    ankle_contra_deg = angle_df[f'ankle_angle_{contra}'].values[start_idx:end_idx]
    ankle_ipsi_rad = interpolate_to_phase(ankle_ipsi_deg * deg2rad)
    ankle_contra_rad = interpolate_to_phase(ankle_contra_deg * deg2rad)

    # Compute velocities and accelerations
    hip_vel_ipsi = compute_velocity_from_angle(hip_ipsi_rad, stride_duration_s)
    hip_vel_contra = compute_velocity_from_angle(hip_contra_rad, stride_duration_s)
    knee_vel_ipsi = compute_velocity_from_angle(knee_ipsi_rad, stride_duration_s)
    knee_vel_contra = compute_velocity_from_angle(knee_contra_rad, stride_duration_s)
    ankle_vel_ipsi = compute_velocity_from_angle(ankle_ipsi_rad, stride_duration_s)
    ankle_vel_contra = compute_velocity_from_angle(ankle_contra_rad, stride_duration_s)

    hip_acc_ipsi = compute_acceleration_from_velocity(hip_vel_ipsi, stride_duration_s)
    hip_acc_contra = compute_acceleration_from_velocity(hip_vel_contra, stride_duration_s)
    knee_acc_ipsi = compute_acceleration_from_velocity(knee_vel_ipsi, stride_duration_s)
    knee_acc_contra = compute_acceleration_from_velocity(knee_vel_contra, stride_duration_s)
    ankle_acc_ipsi = compute_acceleration_from_velocity(ankle_vel_ipsi, stride_duration_s)
    ankle_acc_contra = compute_acceleration_from_velocity(ankle_vel_contra, stride_duration_s)

    # Compute segment angles from IMU
    if skip_segment_angles:
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
        stride_imu = imu_df.iloc[start_idx:end_idx].reset_index(drop=True)

        if use_accel_init:
            thigh_seg_ipsi_raw, shank_seg_ipsi_raw, foot_seg_ipsi_raw = compute_segment_angles_from_imu_with_accel_init(
                stride_imu, ipsi, imu_dt, transfer_type=task
            )
            thigh_seg_contra_raw, shank_seg_contra_raw, foot_seg_contra_raw = compute_segment_angles_from_imu_with_accel_init(
                stride_imu, contra, imu_dt, transfer_type=task
            )
        else:
            thigh_seg_ipsi_raw, shank_seg_ipsi_raw, foot_seg_ipsi_raw = compute_segment_angles_from_imu(
                stride_imu, ipsi, imu_dt, offset=segment_angle_offset_ipsi
            )
            thigh_seg_contra_raw, shank_seg_contra_raw, foot_seg_contra_raw = compute_segment_angles_from_imu(
                stride_imu, contra, imu_dt, offset=segment_angle_offset_contra
            )

        thigh_seg_ipsi = interpolate_to_phase(thigh_seg_ipsi_raw)
        thigh_seg_contra = interpolate_to_phase(thigh_seg_contra_raw)
        shank_seg_ipsi = interpolate_to_phase(shank_seg_ipsi_raw)
        shank_seg_contra = interpolate_to_phase(shank_seg_contra_raw)
        foot_seg_ipsi = interpolate_to_phase(foot_seg_ipsi_raw)
        foot_seg_contra = interpolate_to_phase(foot_seg_contra_raw)

        thigh_seg_vel_ipsi = compute_velocity_from_angle(thigh_seg_ipsi, stride_duration_s)
        thigh_seg_vel_contra = compute_velocity_from_angle(thigh_seg_contra, stride_duration_s)
        shank_seg_vel_ipsi = compute_velocity_from_angle(shank_seg_ipsi, stride_duration_s)
        shank_seg_vel_contra = compute_velocity_from_angle(shank_seg_contra, stride_duration_s)
        foot_seg_vel_ipsi = compute_velocity_from_angle(foot_seg_ipsi, stride_duration_s)
        foot_seg_vel_contra = compute_velocity_from_angle(foot_seg_contra, stride_duration_s)
    else:
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
    # Use moment_filt for TOTAL moments (bio + exo)
    moment_df = data['moment_filt']
    hip_mom_ipsi = interpolate_to_phase(
        moment_df[f'hip_flexion_{ipsi}_moment'].values[start_idx:end_idx]
    )
    hip_mom_contra = interpolate_to_phase(
        moment_df[f'hip_flexion_{contra}_moment'].values[start_idx:end_idx]
    )
    knee_mom_ipsi = interpolate_to_phase(
        -moment_df[f'knee_angle_{ipsi}_moment'].values[start_idx:end_idx]
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

    # Biological moments (total - exo contribution)
    if 'moment_filt_bio' in data:
        bio_moment_df = data['moment_filt_bio']
        hip_bio_mom_ipsi = interpolate_to_phase(
            bio_moment_df[f'hip_flexion_{ipsi}_moment'].values[start_idx:end_idx]
        )
        hip_bio_mom_contra = interpolate_to_phase(
            bio_moment_df[f'hip_flexion_{contra}_moment'].values[start_idx:end_idx]
        )
        knee_bio_mom_ipsi = interpolate_to_phase(
            -bio_moment_df[f'knee_angle_{ipsi}_moment'].values[start_idx:end_idx]
        )
        knee_bio_mom_contra = interpolate_to_phase(
            -bio_moment_df[f'knee_angle_{contra}_moment'].values[start_idx:end_idx]
        )
        ankle_bio_mom_ipsi = interpolate_to_phase(
            bio_moment_df[f'ankle_angle_{ipsi}_moment'].values[start_idx:end_idx]
        )
        ankle_bio_mom_contra = interpolate_to_phase(
            bio_moment_df[f'ankle_angle_{contra}_moment'].values[start_idx:end_idx]
        )
    else:
        hip_bio_mom_ipsi = np.full(NUM_POINTS, np.nan)
        hip_bio_mom_contra = np.full(NUM_POINTS, np.nan)
        knee_bio_mom_ipsi = np.full(NUM_POINTS, np.nan)
        knee_bio_mom_contra = np.full(NUM_POINTS, np.nan)
        ankle_bio_mom_ipsi = np.full(NUM_POINTS, np.nan)
        ankle_bio_mom_contra = np.full(NUM_POINTS, np.nan)

    # Exo assistance moments (interaction torque)
    # Exo sign convention: extension positive — negate for our flexion positive
    # Torque in exo.csv is Nm (absolute), divide by mass for Nm/kg
    if 'exo' in data:
        exo_df = data['exo']
        hip_assist_ipsi = interpolate_to_phase(
            -exo_df[f'hip_angle_{ipsi}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        hip_assist_contra = interpolate_to_phase(
            -exo_df[f'hip_angle_{contra}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        knee_assist_ipsi = interpolate_to_phase(
            -exo_df[f'knee_angle_{ipsi}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
        knee_assist_contra = interpolate_to_phase(
            -exo_df[f'knee_angle_{contra}_torque_interaction'].values[start_idx:end_idx] / subject_mass
        )
    else:
        hip_assist_ipsi = np.zeros(NUM_POINTS)
        hip_assist_contra = np.zeros(NUM_POINTS)
        knee_assist_ipsi = np.zeros(NUM_POINTS)
        knee_assist_contra = np.zeros(NUM_POINTS)

    ankle_assist_ipsi = np.zeros(NUM_POINTS)
    ankle_assist_contra = np.zeros(NUM_POINTS)

    # GRF (normalize by body weight)
    grf_df = data['grf']
    body_weight_N = subject_mass * 9.81

    # Vertical GRF (y = vertical in OpenSim global frame)
    grf_vert_ipsi = interpolate_to_phase(
        grf_df[f'fp_{ipsi}_force_y'].values[start_idx:end_idx] / body_weight_N
    )
    grf_vert_contra = interpolate_to_phase(
        grf_df[f'fp_{contra}_force_y'].values[start_idx:end_idx] / body_weight_N
    )

    # Anterior GRF (negate z: +z = braking -> we want +z = propulsion)
    grf_ant_ipsi_raw = -grf_df[f'fp_{ipsi}_force_z'].values[start_idx:end_idx] / body_weight_N
    grf_ant_contra_raw = -grf_df[f'fp_{contra}_force_z'].values[start_idx:end_idx] / body_weight_N

    # Auto-correct sign if walking in negative Z direction
    start_check = int(len(grf_ant_ipsi_raw) * 0.4)
    end_check = int(len(grf_ant_ipsi_raw) * 0.6)
    if end_check > start_check:
        mean_pushoff = np.nanmean(grf_ant_ipsi_raw[start_check:end_check])
        if mean_pushoff < 0:
            grf_ant_ipsi_raw = -grf_ant_ipsi_raw
            grf_ant_contra_raw = -grf_ant_contra_raw

    grf_ant_ipsi = interpolate_to_phase(grf_ant_ipsi_raw)
    grf_ant_contra = interpolate_to_phase(grf_ant_contra_raw)

    # Lateral GRF (auto-correct: ipsi should be negative = medial)
    grf_lat_ipsi_raw = grf_df[f'fp_{ipsi}_force_x'].values[start_idx:end_idx] / body_weight_N
    grf_lat_contra_raw = grf_df[f'fp_{contra}_force_x'].values[start_idx:end_idx] / body_weight_N

    end_stance = int(len(grf_lat_ipsi_raw) * 0.6)
    if end_stance > 0:
        mean_lat_ipsi = np.nanmean(grf_lat_ipsi_raw[:end_stance])
        if mean_lat_ipsi > 0:
            grf_lat_ipsi_raw = -grf_lat_ipsi_raw
            grf_lat_contra_raw = -grf_lat_contra_raw

    grf_lat_ipsi = interpolate_to_phase(grf_lat_ipsi_raw)
    grf_lat_contra = interpolate_to_phase(grf_lat_contra_raw)

    # COP from insole_sim (foot-relative coordinates)
    insole_df = data['insole_sim']
    cop_ant_ipsi = interpolate_to_phase(insole_df[f'insole_{ipsi}_cop_x'].values[start_idx:end_idx])
    cop_ant_contra = interpolate_to_phase(insole_df[f'insole_{contra}_cop_x'].values[start_idx:end_idx])
    cop_lat_ipsi = interpolate_to_phase(insole_df[f'insole_{ipsi}_cop_z'].values[start_idx:end_idx])
    cop_lat_contra = interpolate_to_phase(insole_df[f'insole_{contra}_cop_z'].values[start_idx:end_idx])
    cop_vert_ipsi = np.zeros(NUM_POINTS)
    cop_vert_contra = np.zeros(NUM_POINTS)

    # Build task_info string
    info_parts = [f"leg:{leg_side}"]
    info_parts.append("exo_state:powered")
    info_parts.append("exo_joints:hip_knee")
    info_parts.append(f"model:{model_variant}")

    for k, v in task_info.items():
        if v is not None:
            info_parts.append(f"{k}:{v}")
    task_info_str = ",".join(info_parts)

    # Subject metadata
    subject_metadata = f"weight_kg:{subject_mass:.1f}"

    # Create output DataFrame
    stride_df = pd.DataFrame({
        'subject': f"GT25D_{subject_id}",
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

        # Joint moments - total (Nm/kg)
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

        # Joint moments - biological (Nm/kg)
        'hip_flexion_biological_moment_ipsi_Nm_kg': hip_bio_mom_ipsi,
        'hip_flexion_biological_moment_contra_Nm_kg': hip_bio_mom_contra,
        'knee_flexion_biological_moment_ipsi_Nm_kg': knee_bio_mom_ipsi,
        'knee_flexion_biological_moment_contra_Nm_kg': knee_bio_mom_contra,
        'ankle_dorsiflexion_biological_moment_ipsi_Nm_kg': ankle_bio_mom_ipsi,
        'ankle_dorsiflexion_biological_moment_contra_Nm_kg': ankle_bio_mom_contra,

        # Assistance flag
        'assistance_active': True,  # All trials in this dataset are powered

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

        # Segment angles (rad)
        'thigh_sagittal_angle_ipsi_rad': thigh_seg_ipsi,
        'thigh_sagittal_angle_contra_rad': thigh_seg_contra,
        'shank_sagittal_angle_ipsi_rad': shank_seg_ipsi,
        'shank_sagittal_angle_contra_rad': shank_seg_contra,
        'foot_sagittal_angle_ipsi_rad': foot_seg_ipsi,
        'foot_sagittal_angle_contra_rad': foot_seg_contra,

        # Segment velocities (rad/s)
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
    """Prepare a DataFrame with standardized column names for segmentation."""
    grf_df = data['grf']
    angle_df = data['angle_filt']

    ipsi = leg_side
    contra = 'r' if leg_side == 'l' else 'l'

    n_samples = len(grf_df)

    if 'time' in angle_df.columns:
        time_s = angle_df['time'].values
    elif 'time' in grf_df.columns:
        time_s = grf_df['time'].values
    else:
        time_s = np.arange(n_samples) / SAMPLING_RATE

    grf_ipsi = grf_df[f'fp_{ipsi}_force_y'].values if f'fp_{ipsi}_force_y' in grf_df.columns else np.zeros(n_samples)
    grf_contra = grf_df[f'fp_{contra}_force_y'].values if f'fp_{contra}_force_y' in grf_df.columns else np.zeros(n_samples)

    vel_df = data.get('velocity', pd.DataFrame())
    deg2rad = np.pi / 180.0

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
    """Segment sit-to-stand or stand-to-sit transfers."""
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
        sitting_grf_threshold_N=400.0,
        standing_grf_threshold_N=600.0,
        velocity_threshold_rad_s=0.436,
        use_iqr_filtering=True,
        iqr_multiplier=IQR_MULTIPLIER,
    )
    return segment_sit_stand_transfers(seg_df, config, transfer_type=transfer_type)


def process_trial(
    trial_path: Path,
    subject_id: str,
) -> List[pd.DataFrame]:
    """
    Process all strides in a trial.

    Args:
        trial_path: Path to trial folder containing CSVs
        subject_id: Subject identifier

    Returns:
        List of stride DataFrames
    """
    folder_name = trial_path.name

    task, task_id, task_info = map_task_name(folder_name)

    if task is None:
        return []

    model_variant = get_model_variant(folder_name) or 'unknown'

    subject_mass = get_subject_mass(subject_id)

    data = load_trial_data(trial_path, subject_id)
    if data is None:
        return []

    # Load IMU data
    imu_df = None
    imu_dt = 1.0 / SAMPLING_RATE

    prefix = f"{subject_id}_{folder_name}_"
    imu_path = trial_path / f"{prefix}imu_sim.csv"

    try:
        if imu_path.exists():
            imu_df = pd.read_csv(imu_path)
            if imu_df is not None and 'time' in imu_df.columns and len(imu_df) > 1:
                imu_dt = np.mean(np.diff(imu_df['time'].values))
    except Exception as e:
        print(f"  Warning: Could not load IMU data: {e}")
        imu_df = None

    archetype = TASK_ARCHETYPE_MAP.get(task, SegmentationArchetype.GAIT)

    strides = []
    step_num = 0

    if archetype == SegmentationArchetype.SIT_STAND_TRANSFER:
        seg_df = prepare_segmentation_df(data, 'l')
        segments = segment_trial_sit_stand(seg_df, transfer_type="both")

        for seg in segments:
            actual_task = seg.segment_type
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
                model_variant=model_variant,
                imu_df=imu_df,
                imu_dt=imu_dt,
                use_accel_init=True
            )
            if stride_df is not None:
                strides.append(stride_df)
                step_num += 1

    else:
        # Gait tasks: process each leg independently with two-pass segment angle
        ground_slope_deg = task_info.get('incline_deg', 0.0)
        ground_slope_rad = np.radians(ground_slope_deg)

        for leg_side in ['l', 'r']:
            seg_df = prepare_segmentation_df(data, leg_side)
            segments = segment_trial_gait(seg_df, leg_side)

            # Two-pass: calculate offset first, then process strides
            stride_imu_list = []
            offset_ipsi = 0.0
            offset_contra = 0.0

            if imu_df is not None:
                for seg in segments:
                    if len(imu_df) > seg.end_idx:
                        stride_imu = imu_df.iloc[seg.start_idx:seg.end_idx].reset_index(drop=True)
                        stride_imu_list.append(stride_imu)

                offset_ipsi = calculate_foot_angle_offset(stride_imu_list, leg_side, imu_dt, ground_slope_rad)
                contra_side = 'r' if leg_side == 'l' else 'l'
                offset_contra = calculate_foot_angle_offset(stride_imu_list, contra_side, imu_dt, ground_slope_rad)

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
                    model_variant=model_variant,
                    imu_df=imu_df,
                    imu_dt=imu_dt,
                    segment_angle_offset_ipsi=offset_ipsi,
                    segment_angle_offset_contra=offset_contra
                )
                if stride_df is not None:
                    strides.append(stride_df)
                    step_num += 1

    return strides


def process_subject(subject_path: Path, subject_id: str) -> pd.DataFrame:
    """
    Process all trials for a subject.

    Folder structure (flat, model variant embedded in folder name):
        subject_path/
            normal_walk_1_baseline_1-2_on/
                BT01_normal_walk_1_baseline_1-2_on_angle_filt.csv
                ...
            normal_walk_1_4t4s_1-2_on/
                ...

    Args:
        subject_path: Path to subject folder
        subject_id: Subject identifier

    Returns:
        Combined DataFrame of all strides
    """
    subject_mass = get_subject_mass(subject_id)
    print(f"  Mass (with exo): {subject_mass:.1f} kg")

    all_strides = []

    # Get all trial folders (each is a unique task+model combination)
    trial_folders = sorted([f for f in subject_path.iterdir() if f.is_dir()])

    for trial_path in tqdm(trial_folders, desc=f"  {subject_id} trials", leave=False):
        strides = process_trial(trial_path, subject_id)
        all_strides.extend(strides)

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert GaTech 2025 Domain Adaptation to parquet')
    parser.add_argument('--input', '-i', type=str, default=None,
                       help='Path to Parsed data folder')
    parser.add_argument('--output', '-o', type=str, default='gtech_2025_da_phase_dirty.parquet',
                       help='Output parquet filename')
    parser.add_argument('--output-dir', type=str,
                       default=str(Path(__file__).resolve().parent.parent.parent.parent / 'converted_datasets'),
                       help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                       help='Specific subjects to process (e.g., BT01)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: process only first subject')

    args = parser.parse_args()

    # Setup paths
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find input data
    input_path = None
    if args.input:
        input_path = Path(args.input)
    else:
        # Default location
        default_path = Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed')
        if default_path.exists():
            input_path = default_path
        else:
            # Try without Parsed subfolder
            default_base = Path('/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation')
            if default_base.exists():
                # Check for Parsed subfolder
                parsed_path = default_base / 'Parsed'
                if parsed_path.exists():
                    input_path = parsed_path
                else:
                    # Check if subjects are directly in the base
                    subjects = [f for f in default_base.iterdir() if f.is_dir() and f.name.startswith('BT')]
                    if subjects:
                        input_path = default_base

    if input_path is None or not input_path.exists():
        print("Error: No input data found. Use --input to specify path.")
        print("Default location: /mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed")
        return

    print(f"Input: {input_path}")

    # Find subject folders
    subject_folders = sorted([f for f in input_path.iterdir() if f.is_dir() and f.name.startswith('BT')])

    if not subject_folders:
        print(f"Error: No subject folders (BT*) found in {input_path}")
        return

    if args.subjects:
        subject_folders = [f for f in subject_folders if f.name in args.subjects]

    if args.test:
        subject_folders = subject_folders[:1]
        print(f"Test mode: processing only {subject_folders[0].name}")

    print(f"Found {len(subject_folders)} subjects: {[f.name for f in subject_folders]}")

    # Process each subject
    all_data = []

    for subject_path in tqdm(subject_folders, desc="Processing subjects"):
        subject_id = subject_path.name
        print(f"\nProcessing {subject_id}...")

        subject_data = process_subject(subject_path, subject_id)

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

        # Show model variant distribution
        model_counts = combined_df['task_info'].str.extract(r'model:(\w+)')[0].value_counts()
        print(f"\nModel variants (strides):")
        for variant, count in model_counts.items():
            print(f"  {variant}: {count // NUM_POINTS}")

        combined_df.to_parquet(output_path, index=False)
        print("Done!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
