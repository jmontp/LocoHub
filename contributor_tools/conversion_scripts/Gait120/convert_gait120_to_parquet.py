#!/usr/bin/env python3
"""
Convert Gait120 dataset to standardized phase-normalized parquet format.

This script converts the Gait120 dataset (Comprehensive Human Locomotion and
Electromyography Dataset) to the LocoHub standardized format.

Dataset:
- Paper: https://www.nature.com/articles/s41597-025-05391-0
- DOI: 10.6084/m9.figshare.27677016
- 120 healthy male subjects (ages 20-59)
- 7 tasks: level walking, stair ascent/descent, slope ascent/descent, sit-to-stand, stand-to-sit
- ~6,882 movement cycles
- OpenSim .mot files with joint angles in degrees

Data structure:
    S001/
        JointAngle/
            LevelWalking/
                Trial01/
                    Step01.mot, Step02.mot, ...
            StairAscent/
            StairDescent/
            SlopeAscent/
            SlopeDescent/
            SitToStand/
            StandToSit/
        MotionCapture/
            {Task}/
                TRC/  # Marker data
                MOT/  # Force plate data (only for level walking, STS tasks)
        EMG/  # Not used in this conversion

Sign conventions in source data:
- Hip: flexion +, adduction +, internal rotation +
- Knee: EXTENSION + (need to negate for flexion+ standard)
- Ankle: dorsiflexion +

Output: Phase-normalized parquet file with 150 points per gait cycle.
"""

import os
import re
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from scipy.interpolate import interp1d
from tqdm import tqdm

# Configuration
NUM_POINTS = 150  # Target points per gait cycle (standard format)
DEG2RAD = np.pi / 180.0

# Task mapping: source folder name -> (standard_task, task_id)
TASK_MAPPING = {
    'LevelWalking': ('level_walking', 'level_walking'),
    'StairAscent': ('stair_ascent', 'stair_ascent'),
    'StairDescent': ('stair_descent', 'stair_descent'),
    'SlopeAscent': ('incline_walking', 'slope_ascent'),
    'SlopeDescent': ('decline_walking', 'slope_descent'),
    'SitToStand': ('sit_to_stand', 'sit_to_stand'),
    'StandToSit': ('stand_to_sit', 'stand_to_sit'),
}

# Expected column names in the .mot files (OpenSim Rajagopal model)
# Note: Actual column names will be verified at runtime from first file
EXPECTED_ANGLE_COLUMNS = [
    'time',
    'pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
    'pelvis_tx', 'pelvis_ty', 'pelvis_tz',
    'hip_flexion_r', 'hip_adduction_r', 'hip_rotation_r',
    'knee_angle_r',
    'ankle_angle_r',
    'hip_flexion_l', 'hip_adduction_l', 'hip_rotation_l',
    'knee_angle_l',
    'ankle_angle_l',
    # May also have: lumbar, arm, subtalar, mtp coordinates
]


def load_mot_file(mot_path: Path) -> Optional[pd.DataFrame]:
    """
    Load an OpenSim .mot file containing joint angle or force data.

    .mot format:
    - Header section ending with "endheader"
    - Column names on line after endheader
    - Tab-separated data rows

    Args:
        mot_path: Path to the .mot file

    Returns:
        DataFrame with time and data columns, or None if file not found/invalid
    """
    if not mot_path.exists():
        return None

    try:
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
                try:
                    values = [float(x) for x in line.strip().split('\t')]
                    data.append(values)
                except ValueError:
                    continue

        if not data:
            return None

        df = pd.DataFrame(data, columns=columns)
        return df

    except Exception as e:
        print(f"  Warning: Could not load {mot_path}: {e}")
        return None


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


def circular_phase_shift(data: np.ndarray, shift_percent: float = 50.0) -> np.ndarray:
    """
    Circularly shift phase-normalized data by a percentage of the gait cycle.

    In gait, the contralateral leg is approximately 50% out of phase with the
    ipsilateral leg.

    Args:
        data: Phase-normalized data array
        shift_percent: Percentage of gait cycle to shift (default 50%)

    Returns:
        Circularly shifted data array (same shape as input)
    """
    num_points = len(data)
    shift_points = int(round(num_points * shift_percent / 100.0))
    return np.roll(data, shift_points)


def estimate_stride_duration_from_mot(df: pd.DataFrame) -> float:
    """
    Estimate stride duration from .mot file time column.

    Args:
        df: DataFrame from .mot file with 'time' column

    Returns:
        Duration in seconds (default 1.0 if cannot compute)
    """
    if 'time' in df.columns and len(df) > 1:
        time_vals = df['time'].values
        duration = time_vals[-1] - time_vals[0]
        if duration > 0:
            return duration
    return 1.0  # Default estimate


def get_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Create mapping from expected column names to actual column names in the data.

    The Gait120 dataset uses OpenSim Rajagopal model column names:
    - hip_flexion_r, hip_flexion_l
    - hip_adduction_r, hip_adduction_l
    - hip_rotation_r, hip_rotation_l
    - knee_angle_r, knee_angle_l
    - ankle_angle_r, ankle_angle_l
    - pelvis_tilt, pelvis_list, pelvis_rotation

    Args:
        df: DataFrame from a .mot file

    Returns:
        Dictionary mapping standard names to actual column names in df
    """
    columns = set(df.columns)
    mapping = {}

    # Time column
    if 'time' in columns:
        mapping['time'] = 'time'

    # Pelvis columns (global orientation)
    for col in ['pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
                'pelvis_tx', 'pelvis_ty', 'pelvis_tz']:
        if col in columns:
            mapping[col] = col

    # Lower limb joints - exact match for Gait120 naming
    for side in ['r', 'l']:
        suffix = f'_{side}'

        # Hip
        for joint in ['hip_flexion', 'hip_adduction', 'hip_rotation']:
            col_name = f'{joint}{suffix}'
            if col_name in columns:
                mapping[col_name] = col_name

        # Knee (uses 'knee_angle' in Gait120)
        knee_col = f'knee_angle{suffix}'
        if knee_col in columns:
            mapping[knee_col] = knee_col

        # Ankle (uses 'ankle_angle' in Gait120)
        ankle_col = f'ankle_angle{suffix}'
        if ankle_col in columns:
            mapping[ankle_col] = ankle_col

    return mapping


def process_step_file(
    mot_path: Path,
    subject_id: str,
    task: str,
    task_id: str,
    step_num: int,
    leg_side: str = 'r',
    subject_mass_kg: float = 70.0
) -> Optional[pd.DataFrame]:
    """
    Process a single step .mot file into standardized format.

    Args:
        mot_path: Path to the Step*.mot file
        subject_id: Subject identifier (e.g., 'G120_S001')
        task: Standardized task name
        task_id: Task identifier
        step_num: Step number for this subject/task
        leg_side: Which leg is ipsilateral ('r' or 'l')
        subject_mass_kg: Subject mass in kg

    Returns:
        DataFrame with 150 rows (one per phase point) or None if invalid
    """
    # Load .mot file
    df = load_mot_file(mot_path)
    if df is None or len(df) < 10:
        return None

    # Get column mapping
    col_map = get_column_mapping(df)

    # Check for required columns
    ipsi = leg_side
    contra = 'l' if leg_side == 'r' else 'r'

    # Gait120 uses knee_angle and ankle_angle (not knee_flexion, ankle_dorsiflexion)
    required_ipsi = [f'hip_flexion_{ipsi}', f'knee_angle_{ipsi}', f'ankle_angle_{ipsi}']
    required_contra = [f'hip_flexion_{contra}', f'knee_angle_{contra}', f'ankle_angle_{contra}']

    has_ipsi = all(c in col_map for c in required_ipsi)
    has_contra = all(c in col_map for c in required_contra)

    if not has_ipsi:
        return None

    # Estimate stride duration
    stride_duration_s = estimate_stride_duration_from_mot(df)

    # Extract kinematics for ipsilateral leg (convert degrees to radians)
    # Source sign convention: hip flexion +, knee EXTENSION +, ankle dorsiflexion +
    # Target sign convention: hip flexion +, knee FLEXION +, ankle dorsiflexion +
    # Need to NEGATE knee angle

    def get_col(name: str) -> np.ndarray:
        """Get column data directly from DataFrame."""
        if name in df.columns:
            return df[name].values
        return np.zeros(len(df))

    # Hip flexion (no sign change needed)
    hip_ipsi_deg = get_col(f'hip_flexion_{ipsi}')
    hip_contra_deg = get_col(f'hip_flexion_{contra}') if has_contra else np.full_like(hip_ipsi_deg, np.nan)
    hip_ipsi_rad = interpolate_to_phase(hip_ipsi_deg * DEG2RAD)
    hip_contra_rad = interpolate_to_phase(hip_contra_deg * DEG2RAD)

    # Knee angle (NEGATE: source extension+ -> standard flexion+)
    # Gait120 uses 'knee_angle_r' and 'knee_angle_l'
    knee_ipsi_deg = get_col(f'knee_angle_{ipsi}')
    knee_contra_deg = get_col(f'knee_angle_{contra}') if has_contra else np.full_like(knee_ipsi_deg, np.nan)
    knee_ipsi_rad = interpolate_to_phase(-knee_ipsi_deg * DEG2RAD)  # Negate for flexion+
    knee_contra_rad = interpolate_to_phase(-knee_contra_deg * DEG2RAD)  # Negate for flexion+

    # Ankle dorsiflexion (no sign change needed)
    # Gait120 uses 'ankle_angle_r' and 'ankle_angle_l'
    ankle_ipsi_deg = get_col(f'ankle_angle_{ipsi}')
    ankle_contra_deg = get_col(f'ankle_angle_{contra}') if has_contra else np.full_like(ankle_ipsi_deg, np.nan)
    ankle_ipsi_rad = interpolate_to_phase(ankle_ipsi_deg * DEG2RAD)
    ankle_contra_rad = interpolate_to_phase(ankle_contra_deg * DEG2RAD)

    # For gait tasks, apply 50% phase shift to contralateral data
    # For bilateral tasks (sit-stand), no phase shift
    is_bilateral = task in ['sit_to_stand', 'stand_to_sit', 'squat']
    if not is_bilateral and has_contra:
        hip_contra_rad = circular_phase_shift(hip_contra_rad)
        knee_contra_rad = circular_phase_shift(knee_contra_rad)
        ankle_contra_rad = circular_phase_shift(ankle_contra_rad)

    # Pelvis tilt (global reference)
    pelvis_tilt_deg = get_col('pelvis_tilt')
    pelvis_tilt_rad = interpolate_to_phase(pelvis_tilt_deg * DEG2RAD) if 'pelvis_tilt' in col_map else np.zeros(NUM_POINTS)

    # Compute segment angles from kinematic chain
    # thigh_angle = pelvis_tilt + hip_flexion
    # shank_angle = thigh_angle - knee_flexion (knee is flexion-positive now)
    # foot_angle = shank_angle + ankle_dorsiflexion
    thigh_ipsi_rad = pelvis_tilt_rad + hip_ipsi_rad
    thigh_contra_rad = pelvis_tilt_rad + hip_contra_rad
    shank_ipsi_rad = thigh_ipsi_rad - knee_ipsi_rad
    shank_contra_rad = thigh_contra_rad - knee_contra_rad
    foot_ipsi_rad = shank_ipsi_rad + ankle_ipsi_rad
    foot_contra_rad = shank_contra_rad + ankle_contra_rad

    # Compute velocities
    hip_vel_ipsi = compute_velocity_from_angle(hip_ipsi_rad, stride_duration_s)
    hip_vel_contra = compute_velocity_from_angle(hip_contra_rad, stride_duration_s)
    knee_vel_ipsi = compute_velocity_from_angle(knee_ipsi_rad, stride_duration_s)
    knee_vel_contra = compute_velocity_from_angle(knee_contra_rad, stride_duration_s)
    ankle_vel_ipsi = compute_velocity_from_angle(ankle_ipsi_rad, stride_duration_s)
    ankle_vel_contra = compute_velocity_from_angle(ankle_contra_rad, stride_duration_s)

    # Segment velocities
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

    # Phase values
    phase = np.linspace(0, 100, NUM_POINTS)
    phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)

    # Build task_info string
    task_info_parts = [f"leg:{leg_side}", "exo_state:no_exo"]
    task_info_str = ",".join(task_info_parts)

    # Build subject metadata
    subject_metadata = f"weight_kg:{subject_mass_kg:.1f},sex:M"

    # Create stride DataFrame
    stride_df = pd.DataFrame({
        'subject': subject_id,
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

    return stride_df


def process_task(
    task_path: Path,
    subject_id: str,
    task_name: str,
    task: str,
    task_id: str,
    subject_mass_kg: float = 70.0,
    step_offset: int = 0
) -> Tuple[List[pd.DataFrame], int]:
    """
    Process all steps for a single task.

    Args:
        task_path: Path to the task folder (e.g., .../JointAngle/LevelWalking/)
        subject_id: Subject identifier
        task_name: Original task folder name
        task: Standardized task name
        task_id: Task identifier
        subject_mass_kg: Subject mass
        step_offset: Starting step number

    Returns:
        Tuple of (list of stride DataFrames, next step number)
    """
    strides = []
    step_num = step_offset

    # Find all trial folders
    trial_folders = sorted([d for d in task_path.iterdir() if d.is_dir()])

    if not trial_folders:
        # Check if .mot files are directly in task folder
        mot_files = sorted(task_path.glob('*.mot'))
        if mot_files:
            trial_folders = [task_path]

    for trial_folder in trial_folders:
        # Find all step .mot files in this trial
        if trial_folder == task_path:
            mot_files = sorted(task_path.glob('*.mot'))
        else:
            mot_files = sorted(trial_folder.glob('Step*.mot'))
            if not mot_files:
                mot_files = sorted(trial_folder.glob('*.mot'))

        for mot_file in mot_files:
            # Process for both legs (ipsi = right, then ipsi = left)
            for leg_side in ['r', 'l']:
                stride_df = process_step_file(
                    mot_path=mot_file,
                    subject_id=subject_id,
                    task=task,
                    task_id=task_id,
                    step_num=step_num,
                    leg_side=leg_side,
                    subject_mass_kg=subject_mass_kg
                )

                if stride_df is not None:
                    strides.append(stride_df)
                    step_num += 1

    return strides, step_num


def process_subject(
    subject_path: Path,
    subject_num: int,
    test_mode: bool = False
) -> pd.DataFrame:
    """
    Process all tasks for a single subject.

    Args:
        subject_path: Path to subject folder (e.g., .../S001/)
        subject_num: Subject number for ID generation
        test_mode: If True, only process first task

    Returns:
        Combined DataFrame of all strides
    """
    subject_folder = subject_path.name
    subject_id = f"G120_{subject_folder}"

    # Extract subject number for mass estimation (no individual mass data available)
    # Using average male mass as estimate
    subject_mass_kg = 75.0  # Approximate, can be updated if metadata available

    all_strides = []
    step_offset = 0

    # Find JointAngle folder
    joint_angle_path = subject_path / 'JointAngle'
    if not joint_angle_path.exists():
        # Try alternate naming
        joint_angle_path = subject_path / 'Joint_Angle'
        if not joint_angle_path.exists():
            print(f"  Warning: No JointAngle folder found for {subject_folder}")
            return pd.DataFrame()

    # Process each task folder
    task_folders = sorted([d for d in joint_angle_path.iterdir() if d.is_dir()])

    for task_folder in task_folders:
        task_name = task_folder.name

        # Map to standard task name
        if task_name not in TASK_MAPPING:
            print(f"  Skipping unknown task: {task_name}")
            continue

        task, task_id = TASK_MAPPING[task_name]

        strides, step_offset = process_task(
            task_path=task_folder,
            subject_id=subject_id,
            task_name=task_name,
            task=task,
            task_id=task_id,
            subject_mass_kg=subject_mass_kg,
            step_offset=step_offset
        )

        all_strides.extend(strides)

        if test_mode:
            break  # Only process first task in test mode

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def explore_data_structure(input_path: Path) -> Dict[str, Any]:
    """
    Explore the downloaded dataset structure and report findings.

    Args:
        input_path: Path to the Gait120 dataset root

    Returns:
        Dictionary with structure information
    """
    info = {
        'subject_count': 0,
        'subjects': [],
        'task_folders': set(),
        'sample_columns': [],
        'issues': []
    }

    # Find subject folders
    subject_folders = sorted([d for d in input_path.iterdir()
                             if d.is_dir() and d.name.startswith('S')])
    info['subject_count'] = len(subject_folders)
    info['subjects'] = [f.name for f in subject_folders[:5]] + ['...'] if len(subject_folders) > 5 else [f.name for f in subject_folders]

    if not subject_folders:
        info['issues'].append("No subject folders found (expected S001, S002, ...)")
        return info

    # Examine first subject
    first_subject = subject_folders[0]
    joint_angle_path = first_subject / 'JointAngle'

    if not joint_angle_path.exists():
        info['issues'].append(f"No JointAngle folder in {first_subject.name}")
        return info

    # Get task folders
    task_folders = sorted([d.name for d in joint_angle_path.iterdir() if d.is_dir()])
    info['task_folders'] = task_folders

    # Find a sample .mot file and get columns
    for task_folder in (joint_angle_path / t for t in task_folders):
        mot_files = list(task_folder.glob('**/*.mot'))
        if mot_files:
            sample_df = load_mot_file(mot_files[0])
            if sample_df is not None:
                info['sample_columns'] = list(sample_df.columns)
                info['sample_file'] = str(mot_files[0].relative_to(input_path))
                break

    return info


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert Gait120 dataset to parquet')
    parser.add_argument('--input', '-i', type=str,
                        default='/mnt/s/locomotion_data/Gait120',
                        help='Path to Gait120 dataset folder')
    parser.add_argument('--output', '-o', type=str, default='gait120_phase.parquet',
                        help='Output parquet filename')
    parser.add_argument('--output-dir', type=str, default='../../../converted_datasets',
                        help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                        help='Specific subjects to process (e.g., S001 S002)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only first subject and first task')
    parser.add_argument('--explore', action='store_true',
                        help='Explore data structure and print report (no conversion)')

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path not found: {input_path}")
        print("\nTo download the dataset, run:")
        print("  bash contributor_tools/conversion_scripts/Gait120/download_gait120.sh")
        return

    # Explore mode - just print data structure info
    if args.explore:
        print("Exploring data structure...")
        print("=" * 60)
        info = explore_data_structure(input_path)
        print(f"Subject folders found: {info['subject_count']}")
        print(f"Sample subjects: {info['subjects']}")
        print(f"Task folders: {info['task_folders']}")
        if info['sample_columns']:
            print(f"\nSample .mot file: {info.get('sample_file', 'N/A')}")
            print(f"Columns ({len(info['sample_columns'])}): {info['sample_columns']}")
        if info['issues']:
            print(f"\nIssues: {info['issues']}")
        return

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).parent / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find subject folders
    subject_folders = sorted([d for d in input_path.iterdir()
                             if d.is_dir() and d.name.startswith('S')])

    if args.subjects:
        subject_folders = [f for f in subject_folders if f.name in args.subjects]

    if args.test:
        subject_folders = subject_folders[:1]
        print(f"Test mode: processing only {subject_folders[0].name}")

    print(f"Found {len(subject_folders)} subject folders")

    # Process each subject
    all_data = []

    for i, subject_path in enumerate(tqdm(subject_folders, desc="Processing subjects")):
        print(f"\nProcessing {subject_path.name}...")

        subject_data = process_subject(subject_path, i + 1, test_mode=args.test)

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

        # Show task distribution
        task_counts = combined_df.groupby('task').size() // NUM_POINTS
        print("\nStrides per task:")
        for task, count in task_counts.items():
            print(f"  {task}: {count}")

        combined_df.to_parquet(output_path, index=False)
        print("\nDone!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
