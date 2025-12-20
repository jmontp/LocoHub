#!/usr/bin/env python3
"""
Convert UMich 2024 Knee Exoskeleton dataset to standardized phase-normalized parquet format.

This script converts the "A Versatile Knee Exoskeleton Mitigates Quadriceps Fatigue
in Lifting, Lowering, and Carrying Tasks" dataset (Science Robotics 2024) to the
LocoHub standardized format.

Source: https://doi.org/10.5061/dryad.z34tmpgks
Paper: https://doi.org/10.1126/scirobotics.adr8282

Data structure:
- 10 able-bodied subjects
- 6 tasks: squat lift-lower (LL), level walking (LW), stair ascent (SA),
  stair descent (SD), ramp ascent (RA), ramp descent (RD)
- Data is already ensemble-averaged to 101 points (0-100% cycle)
- Bilateral knee exoskeleton worn during all trials

Variables available:
- Knee angle (degrees, flexion positive)
- Thigh segment angle (degrees, anterior to vertical positive)
- Shank segment angle (degrees, anterior to vertical positive)
- Exo torque (Nm, extension positive)
- Ground reaction force (body-weight normalized)
- EMG data (not included in phase conversion - see note)

Note on EMG: The dataset includes %MVC-normalized EMG for quadriceps and hamstrings
across bare and exo conditions. EMG data is not converted here as the standardized
format focuses on kinematics and kinetics. Raw EMG data can be accessed from the
source dataset.

Output: Phase-normalized parquet file with 150 points per gait cycle.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.io import loadmat
from scipy.interpolate import interp1d
from typing import Dict, List, Tuple, Optional
import argparse


# Configuration
NUM_POINTS_INPUT = 101  # Input data has 101 points (0-100%)
NUM_POINTS_OUTPUT = 150  # Output standardized to 150 points
NUM_SUBJECTS = 10

# Task mapping: source task code -> (standard_task, task_id)
TASK_MAPPING = {
    'LL': ('squat', 'squat_lifting'),  # Squat lift-lower
    'LW': ('level_walking', 'level'),  # Level walking
    'SA': ('stair_ascent', 'stair_ascent'),  # Stair ascent (7 inch steps)
    'SD': ('stair_descent', 'stair_descent'),  # Stair descent
    'RA': ('incline_walking', 'incline_15deg'),  # Ramp ascent (15 degrees)
    'RD': ('decline_walking', 'decline_15deg'),  # Ramp descent
}

# Task metadata based on paper methods
TASK_INFO = {
    'LL': 'variant:squat_lifting,assistance:exo_worn',
    'LW': 'treadmill:false,assistance:exo_worn',
    'SA': 'step_height_m:0.178,step_number:4,assistance:exo_worn',  # 7 inches = 0.178m
    'SD': 'step_height_m:0.178,step_number:4,assistance:exo_worn',
    'RA': 'incline_deg:15,treadmill:false,assistance:exo_worn',
    'RD': 'incline_deg:-15,treadmill:false,assistance:exo_worn',
}


def interpolate_to_phase(data: np.ndarray, num_points_out: int = NUM_POINTS_OUTPUT) -> np.ndarray:
    """
    Interpolate time-series data from input points to output points.

    Args:
        data: Input data array (NUM_POINTS_INPUT,)
        num_points_out: Number of output points (default 150)

    Returns:
        Interpolated data array of length num_points_out
    """
    if len(data) < 2:
        return np.full(num_points_out, np.nan)

    x_original = np.linspace(0, 100, len(data))
    x_target = np.linspace(0, 100, num_points_out)

    # Handle NaN values
    valid_mask = ~np.isnan(data)
    if np.sum(valid_mask) < 2:
        return np.full(num_points_out, np.nan)

    try:
        interp_func = interp1d(x_original[valid_mask], data[valid_mask],
                               kind='linear', fill_value='extrapolate')
        return interp_func(x_target)
    except Exception:
        return np.full(num_points_out, np.nan)


def compute_velocity_from_angle(angle_rad: np.ndarray, assumed_stride_duration_s: float = 1.0) -> np.ndarray:
    """
    Compute angular velocity from angle data using gradient.

    Note: Since data is ensemble-averaged, we use an assumed typical stride duration.
    This provides approximate velocities for validation purposes.

    Args:
        angle_rad: Angle data in radians (150 points)
        assumed_stride_duration_s: Assumed stride duration in seconds

    Returns:
        Angular velocity in rad/s
    """
    dt = assumed_stride_duration_s / (len(angle_rad) - 1)
    velocity = np.gradient(angle_rad) / dt
    return velocity


def compute_acceleration_from_velocity(velocity_rad_s: np.ndarray, assumed_stride_duration_s: float = 1.0) -> np.ndarray:
    """
    Compute angular acceleration from velocity data using gradient.
    """
    dt = assumed_stride_duration_s / (len(velocity_rad_s) - 1)
    acceleration = np.gradient(velocity_rad_s) / dt
    return acceleration


def load_s1_data(data_path: Path) -> Dict:
    """
    Load dataset_S1.mat file.

    Returns:
        Dictionary containing exo and emg structures
    """
    mat_data = loadmat(data_path, squeeze_me=True)
    return mat_data


def get_nested_field(struct, *fields):
    """
    Get a nested field from a MATLAB struct loaded by scipy.

    Args:
        struct: The MATLAB struct (numpy array with dtype.names)
        *fields: Field names to traverse

    Returns:
        The value at the nested field path
    """
    current = struct
    for field in fields:
        if hasattr(current, 'dtype') and current.dtype.names:
            idx = current.dtype.names.index(field)
            current = current[()][idx]
        elif isinstance(current, np.ndarray) and current.dtype.names:
            current = current[field]
        else:
            current = current[field]
    return current


def process_task(
    exo_data,
    task_code: str,
    task_name: str,
    task_id: str,
    task_info: str,
) -> List[pd.DataFrame]:
    """
    Process all subjects for a single task.

    Args:
        exo_data: Exoskeleton sensor data structure (numpy structured array)
        task_code: Original task code (e.g., 'LL')
        task_name: Standardized task name
        task_id: Task identifier
        task_info: Task metadata string

    Returns:
        List of DataFrames, one per subject
    """
    strides = []

    # Get task data arrays (101 x 10: phase x subjects)
    # Access nested fields from MATLAB struct
    knee_angle_deg = get_nested_field(exo_data, 'kneeAngle', task_code)  # (101, 10)
    thigh_angle_deg = get_nested_field(exo_data, 'thighAngle', task_code)
    shank_angle_deg = get_nested_field(exo_data, 'shankAngle', task_code)
    torque_nm = get_nested_field(exo_data, 'torque', task_code)  # Extension positive
    grf_bw = get_nested_field(exo_data, 'grf', task_code)

    # Degrees to radians conversion
    deg2rad = np.pi / 180.0

    for subj_idx in range(NUM_SUBJECTS):
        subj_num = subj_idx + 1  # 1-indexed subject number

        # Extract single subject data
        knee_deg = knee_angle_deg[:, subj_idx]
        thigh_deg = thigh_angle_deg[:, subj_idx]
        shank_deg = shank_angle_deg[:, subj_idx]
        torque = torque_nm[:, subj_idx]
        grf = grf_bw[:, subj_idx]

        # Skip if data is all NaN
        if np.all(np.isnan(knee_deg)) or np.all(np.isnan(grf)):
            continue

        # Interpolate to 150 points
        knee_rad = interpolate_to_phase(knee_deg * deg2rad)
        thigh_rad = interpolate_to_phase(thigh_deg * deg2rad)
        shank_rad = interpolate_to_phase(shank_deg * deg2rad)
        grf_interp = interpolate_to_phase(grf)

        # Convert torque: extension positive -> flexion positive (negate)
        # Note: Torque is in Nm, not mass-normalized. We'll flag this.
        torque_interp = interpolate_to_phase(-torque)

        # Compute velocities and accelerations
        # Use task-specific assumed stride durations
        if task_code in ['LW', 'RA', 'RD']:
            stride_dur = 1.1  # Walking ~1.1s per stride
        elif task_code in ['SA', 'SD']:
            stride_dur = 1.5  # Stairs ~1.5s per step
        else:  # LL (squat)
            stride_dur = 3.0  # Squat rep ~3s

        knee_vel = compute_velocity_from_angle(knee_rad, stride_dur)
        knee_acc = compute_acceleration_from_velocity(knee_vel, stride_dur)
        thigh_vel = compute_velocity_from_angle(thigh_rad, stride_dur)
        shank_vel = compute_velocity_from_angle(shank_rad, stride_dur)

        # Create phase array
        phase = np.linspace(0, 100, NUM_POINTS_OUTPUT)

        # Build DataFrame for this subject-task combination
        # Note: This dataset only has knee angle, not hip/ankle
        # We populate available fields and leave others as NaN
        nan_array = np.full(NUM_POINTS_OUTPUT, np.nan)

        stride_df = pd.DataFrame({
            'subject': f"UM24_AB{subj_num:02d}",
            'subject_metadata': 'population:able_bodied,exo:worn_powered',
            'task': task_name,
            'task_id': task_id,
            'task_info': task_info,
            'step': '001',  # Ensemble average = single representative cycle
            'phase_ipsi': phase,

            # Joint angles (rad) - only knee available
            'hip_flexion_angle_ipsi_rad': nan_array,
            'hip_flexion_angle_contra_rad': nan_array,
            'knee_flexion_angle_ipsi_rad': knee_rad,
            'knee_flexion_angle_contra_rad': nan_array,  # Bilateral data not separated
            'ankle_dorsiflexion_angle_ipsi_rad': nan_array,
            'ankle_dorsiflexion_angle_contra_rad': nan_array,

            # Joint velocities (rad/s)
            'hip_flexion_velocity_ipsi_rad_s': nan_array,
            'hip_flexion_velocity_contra_rad_s': nan_array,
            'knee_flexion_velocity_ipsi_rad_s': knee_vel,
            'knee_flexion_velocity_contra_rad_s': nan_array,
            'ankle_dorsiflexion_velocity_ipsi_rad_s': nan_array,
            'ankle_dorsiflexion_velocity_contra_rad_s': nan_array,

            # Joint accelerations (rad/s^2)
            'hip_flexion_acceleration_ipsi_rad_s2': nan_array,
            'hip_flexion_acceleration_contra_rad_s2': nan_array,
            'knee_flexion_acceleration_ipsi_rad_s2': knee_acc,
            'knee_flexion_acceleration_contra_rad_s2': nan_array,
            'ankle_dorsiflexion_acceleration_ipsi_rad_s2': nan_array,
            'ankle_dorsiflexion_acceleration_contra_rad_s2': nan_array,

            # Joint moments - torque from exo (not mass-normalized)
            # Stored as absolute Nm, user should divide by mass if needed
            'knee_flexion_moment_ipsi_Nm_kg': nan_array,  # No mass data available
            'knee_flexion_moment_contra_Nm_kg': nan_array,
            'hip_flexion_moment_ipsi_Nm_kg': nan_array,
            'hip_flexion_moment_contra_Nm_kg': nan_array,
            'ankle_dorsiflexion_moment_ipsi_Nm_kg': nan_array,
            'ankle_dorsiflexion_moment_contra_Nm_kg': nan_array,

            # Ground reaction forces (BW)
            'grf_vertical_ipsi_BW': grf_interp,
            'grf_vertical_contra_BW': nan_array,
            'grf_anterior_ipsi_BW': nan_array,
            'grf_anterior_contra_BW': nan_array,
            'grf_lateral_ipsi_BW': nan_array,
            'grf_lateral_contra_BW': nan_array,

            # Segment angles (rad)
            'pelvis_sagittal_angle_rad': nan_array,
            'pelvis_frontal_angle_rad': nan_array,
            'pelvis_transverse_angle_rad': nan_array,
            'trunk_sagittal_angle_rad': nan_array,
            'trunk_frontal_angle_rad': nan_array,
            'trunk_transverse_angle_rad': nan_array,
            'thigh_sagittal_angle_ipsi_rad': thigh_rad,
            'thigh_sagittal_angle_contra_rad': nan_array,
            'shank_sagittal_angle_ipsi_rad': shank_rad,
            'shank_sagittal_angle_contra_rad': nan_array,
            'foot_sagittal_angle_ipsi_rad': nan_array,
            'foot_sagittal_angle_contra_rad': nan_array,

            # Exo-specific columns (custom extension)
            'exo_torque_knee_ipsi_Nm': torque_interp,
        })

        strides.append(stride_df)

    return strides


def main():
    """Main conversion function."""
    parser = argparse.ArgumentParser(
        description='Convert UMich 2024 Knee Exoskeleton dataset to parquet'
    )
    parser.add_argument(
        '--input', '-i', type=str,
        default=str(Path(__file__).parent / 'dataset_S1.mat'),
        help='Path to dataset_S1.mat file'
    )
    parser.add_argument(
        '--output', '-o', type=str,
        default='umich_2024_knee_exo_phase.parquet',
        help='Output parquet filename'
    )
    parser.add_argument(
        '--output-dir', type=str,
        default='../../../converted_datasets',
        help='Output directory'
    )

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {input_path}")
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return

    # Load data
    mat_data = loadmat(input_path, squeeze_me=True)

    # Extract exo structure
    exo_data = mat_data['exo']

    print(f"Processing {NUM_SUBJECTS} subjects across {len(TASK_MAPPING)} tasks...")

    # Process each task
    all_strides = []

    for task_code, (task_name, task_id) in TASK_MAPPING.items():
        print(f"  Processing task: {task_code} -> {task_name}")
        task_info = TASK_INFO.get(task_code, '')

        strides = process_task(
            exo_data=exo_data,
            task_code=task_code,
            task_name=task_name,
            task_id=task_id,
            task_info=task_info,
        )
        all_strides.extend(strides)

    # Combine all data
    if all_strides:
        combined_df = pd.concat(all_strides, ignore_index=True)
        output_path = output_dir / args.output

        print(f"\nSaving to: {output_path}")
        print(f"Total rows: {len(combined_df)}")
        print(f"Total strides: {len(combined_df) // NUM_POINTS_OUTPUT}")
        print(f"Unique subjects: {combined_df['subject'].nunique()}")
        print(f"Tasks: {combined_df['task'].unique().tolist()}")

        combined_df.to_parquet(output_path, index=False)
        print("Done!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
