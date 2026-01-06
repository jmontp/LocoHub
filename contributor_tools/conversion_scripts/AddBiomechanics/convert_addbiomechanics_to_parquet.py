#!/usr/bin/env python3
"""
Convert AddBiomechanics B3D files to standardized parquet format.

This script converts B3D files from AddBiomechanics.org to the LocoHub
standardized parquet format, producing both time-indexed and phase-normalized
outputs.

Supported datasets (9 total):
- Moore2015: Treadmill walking at multiple speeds
- Camargo2021: Level/ramp/stair walking
- Fregly2012: Normal and modified walking patterns
- Hamner2013: Running at multiple speeds
- Santos2017: Standing still
- Tan2021: Modified running
- Tan2022: Modified walking
- vanderZee2022: Level walking trials
- Wang2023: Walking, running, and non-cyclic tasks

Usage:
    python convert_addbiomechanics_to_parquet.py --dataset Moore2015 --input /path/to/b3d/files

Output:
    - {dataset}_time.parquet: Time-indexed data (one row per frame)
    - {dataset}_phase.parquet: Phase-normalized data (150 rows per stride)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from tqdm import tqdm

# Add common utilities to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'common'))
from phase_detection import VerticalGRFConfig, detect_vertical_grf_events

from dataset_configs import (
    DATASET_SHORT_CODES,
    get_task_info,
    get_subject_name,
    is_cyclic_task,
    get_supported_datasets,
)

# Configuration
NUM_PHASE_POINTS = 150
GRF_THRESHOLD_N = 50.0
MIN_STRIDE_INTERVAL_S = 0.3
IQR_MULTIPLIER = 1.5  # For outlier stride filtering


def osim_rotation_matrix(x: float, y: float, z: float) -> np.ndarray:
    """
    Generate rotation matrix from Euler angles (x, y, z) in radians.
    Uses XYZ rotation order matching OpenSim conventions.
    """
    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(x), -np.sin(x)],
        [0, np.sin(x), np.cos(x)]
    ])
    R_y = np.array([
        [np.cos(y), 0, np.sin(y)],
        [0, 1, 0],
        [-np.sin(y), 0, np.cos(y)]
    ])
    R_z = np.array([
        [np.cos(z), -np.sin(z), 0],
        [np.sin(z), np.cos(z), 0],
        [0, 0, 1]
    ])
    return np.dot(R_z, np.dot(R_x, R_y))


def compute_segment_angles(
    pelvis_angles: Tuple[float, float, float],
    hip_angles_r: Tuple[float, float, float],
    hip_angles_l: Tuple[float, float, float],
    knee_angle_r: float,
    knee_angle_l: float,
    ankle_angles_r: Tuple[float, float],
    ankle_angles_l: Tuple[float, float],
) -> Dict[str, float]:
    """
    Compute segment angles from joint angles using rotation matrices.

    Returns dict with shank, thigh, and foot sagittal angles for both legs.
    """
    # Pelvis rotation
    R_pelvis = osim_rotation_matrix(pelvis_angles[1], pelvis_angles[2], pelvis_angles[0])

    # Hip rotations
    R_hip_r = osim_rotation_matrix(hip_angles_r[1], hip_angles_r[2], hip_angles_r[0])
    R_hip_l = osim_rotation_matrix(hip_angles_l[1], hip_angles_l[2], hip_angles_l[0])

    # Knee rotations (negative for flexion convention)
    R_knee_r = osim_rotation_matrix(0, 0, -knee_angle_r)
    R_knee_l = osim_rotation_matrix(0, 0, -knee_angle_l)

    # Ankle rotations
    R_ankle_r = osim_rotation_matrix(0, ankle_angles_r[1], ankle_angles_r[0])
    R_ankle_l = osim_rotation_matrix(0, ankle_angles_l[1], ankle_angles_l[0])

    # Compute segment rotation matrices
    R_thigh_r = np.dot(R_pelvis, R_hip_r)
    R_thigh_l = np.dot(R_pelvis, R_hip_l)
    R_shank_r = np.dot(R_thigh_r, R_knee_r)
    R_shank_l = np.dot(R_thigh_l, R_knee_l)
    R_foot_r = np.dot(R_shank_r, R_ankle_r)
    R_foot_l = np.dot(R_shank_l, R_ankle_l)

    return {
        'thigh_sagittal_angle_ipsi_rad': R_thigh_r[1, 0],
        'thigh_sagittal_angle_contra_rad': R_thigh_l[1, 0],
        'shank_sagittal_angle_ipsi_rad': R_shank_r[1, 0],
        'shank_sagittal_angle_contra_rad': R_shank_l[1, 0],
        'foot_sagittal_angle_ipsi_rad': R_foot_r[1, 0],
        'foot_sagittal_angle_contra_rad': R_foot_l[1, 0],
    }


def extract_frame_data(frame, timestep: float, mass_kg: float) -> Dict:
    """
    Extract biomechanical data from a single nimblephysics frame.

    Args:
        frame: nimblephysics frame object
        timestep: Time interval between frames
        mass_kg: Subject mass in kg

    Returns:
        Dictionary with extracted variables
    """
    ss = frame.processingPasses[1]  # Use dynamics processing pass

    # Extract raw data
    poses = ss.pos
    vels = ss.vel
    torques = ss.tau
    grf = ss.groundContactForceInRootFrame
    cop = ss.groundContactCenterOfPressureInRootFrame
    contacted = ss.contact
    com_pos = ss.comPos
    com_vel = ss.comVel

    # Compute segment angles
    seg_angles = compute_segment_angles(
        pelvis_angles=(poses[0], poses[1], poses[2]),
        hip_angles_r=(poses[6], poses[7], poses[8]),
        hip_angles_l=(poses[13], poses[14], poses[15]),
        knee_angle_r=poses[9],
        knee_angle_l=poses[16],
        ankle_angles_r=(poses[10], poses[11]),
        ankle_angles_l=(poses[17], poses[18]),
    )

    # Build record with standardized column names
    # Note: In AddBiomechanics, right leg = ipsi, left leg = contra (by convention)
    record = {
        # Ground reaction forces (Newtons, will be normalized later)
        'grf_vertical_ipsi_N': grf[1],  # right y
        'grf_anterior_ipsi_N': grf[0],  # right x
        'grf_lateral_ipsi_N': grf[2],   # right z
        'grf_vertical_contra_N': grf[4],  # left y
        'grf_anterior_contra_N': grf[3],  # left x
        'grf_lateral_contra_N': grf[5],   # left z

        # Center of pressure (meters)
        'cop_anterior_ipsi_m': cop[0],
        'cop_vertical_ipsi_m': cop[1],
        'cop_lateral_ipsi_m': cop[2],
        'cop_anterior_contra_m': cop[3],
        'cop_vertical_contra_m': cop[4],
        'cop_lateral_contra_m': cop[5],

        # Contact states
        'contact_ipsi': contacted[0],
        'contact_contra': contacted[1],

        # Pelvis angles (radians)
        'pelvis_sagittal_angle_rad': poses[0],
        'pelvis_frontal_angle_rad': poses[1],
        'pelvis_transverse_angle_rad': poses[2],

        # Joint angles - right leg = ipsi (radians)
        'hip_flexion_angle_ipsi_rad': poses[6],
        'hip_adduction_angle_ipsi_rad': poses[7],
        'hip_rotation_angle_ipsi_rad': poses[8],
        'knee_flexion_angle_ipsi_rad': poses[9],
        'ankle_dorsiflexion_angle_ipsi_rad': poses[10],
        'ankle_rotation_angle_ipsi_rad': poses[11],

        # Joint angles - left leg = contra (radians)
        'hip_flexion_angle_contra_rad': poses[13],
        'hip_adduction_angle_contra_rad': poses[14],
        'hip_rotation_angle_contra_rad': poses[15],
        'knee_flexion_angle_contra_rad': poses[16],
        'ankle_dorsiflexion_angle_contra_rad': poses[17],
        'ankle_rotation_angle_contra_rad': poses[18],

        # Pelvis velocities (rad/s)
        'pelvis_sagittal_velocity_rad_s': vels[0],
        'pelvis_frontal_velocity_rad_s': vels[1],
        'pelvis_transverse_velocity_rad_s': vels[2],

        # Joint velocities - ipsi (rad/s)
        'hip_flexion_velocity_ipsi_rad_s': vels[6],
        'hip_adduction_velocity_ipsi_rad_s': vels[7],
        'hip_rotation_velocity_ipsi_rad_s': vels[8],
        'knee_flexion_velocity_ipsi_rad_s': vels[9],
        'ankle_dorsiflexion_velocity_ipsi_rad_s': vels[10],
        'ankle_rotation_velocity_ipsi_rad_s': vels[11],

        # Joint velocities - contra (rad/s)
        'hip_flexion_velocity_contra_rad_s': vels[13],
        'hip_adduction_velocity_contra_rad_s': vels[14],
        'hip_rotation_velocity_contra_rad_s': vels[15],
        'knee_flexion_velocity_contra_rad_s': vels[16],
        'ankle_dorsiflexion_velocity_contra_rad_s': vels[17],
        'ankle_rotation_velocity_contra_rad_s': vels[18],

        # Joint moments - mass normalized (Nm/kg)
        'hip_flexion_moment_ipsi_Nm_kg': torques[6] / mass_kg,
        'hip_adduction_moment_ipsi_Nm_kg': torques[7] / mass_kg,
        'hip_rotation_moment_ipsi_Nm_kg': torques[8] / mass_kg,
        'knee_flexion_moment_ipsi_Nm_kg': torques[9] / mass_kg,
        'ankle_dorsiflexion_moment_ipsi_Nm_kg': torques[10] / mass_kg,
        'ankle_rotation_moment_ipsi_Nm_kg': torques[11] / mass_kg,

        'hip_flexion_moment_contra_Nm_kg': torques[13] / mass_kg,
        'hip_adduction_moment_contra_Nm_kg': torques[14] / mass_kg,
        'hip_rotation_moment_contra_Nm_kg': torques[15] / mass_kg,
        'knee_flexion_moment_contra_Nm_kg': torques[16] / mass_kg,
        'ankle_dorsiflexion_moment_contra_Nm_kg': torques[17] / mass_kg,
        'ankle_rotation_moment_contra_Nm_kg': torques[18] / mass_kg,

        # COM position and velocity
        'com_pos_x_m': com_pos[0],
        'com_pos_y_m': com_pos[1],
        'com_pos_z_m': com_pos[2],
        'com_vel_x_m_s': com_vel[0],
        'com_vel_y_m_s': com_vel[1],
        'com_vel_z_m_s': com_vel[2],

        # Segment angles from rotation matrices
        **seg_angles,
    }

    return record


def process_b3d_file(
    b3d_path: Path,
    dataset: str,
    subject_idx: int,
) -> Optional[pd.DataFrame]:
    """
    Process a single B3D file and return time-indexed DataFrame.

    Args:
        b3d_path: Path to B3D file
        dataset: Dataset name
        subject_idx: Subject index for naming

    Returns:
        DataFrame with extracted data, or None if processing fails
    """
    try:
        import nimblephysics as nimble
    except ImportError:
        raise ImportError("nimblephysics is required. Install with: pip install nimblephysics")

    try:
        subject = nimble.biomechanics.SubjectOnDisk(str(b3d_path))
    except Exception as e:
        print(f"Failed to load {b3d_path}: {e}")
        return None

    mass_kg = subject.getMassKg()
    if mass_kg <= 0:
        mass_kg = 70.0  # Default if mass not available

    # Extract subject name
    original_name = b3d_path.stem
    if '_split' in original_name:
        original_name = original_name.split('_split')[0]
    subject_name = get_subject_name(dataset, original_name, subject_idx)

    records = []
    num_trials = subject.getNumTrials()

    for trial_idx in range(num_trials):
        timestep = subject.getTrialTimestep(trial_idx)
        original_task = subject.getTrialOriginalName(trial_idx)
        task, task_id, task_info = get_task_info(dataset, original_task)

        # Read all frames
        frames = subject.readFrames(trial_idx, 0, 1_000_000)
        accum_time = 0.0

        for frame_idx, frame in enumerate(frames):
            try:
                record = extract_frame_data(frame, timestep, mass_kg)
                record['subject'] = subject_name
                record['subject_metadata'] = f'mass_kg:{mass_kg}'
                record['task'] = task
                record['task_id'] = task_id
                record['task_info'] = task_info
                record['time_s'] = accum_time
                record['frame_number'] = frame_idx
                records.append(record)
                accum_time += timestep
            except Exception as e:
                # Skip problematic frames
                continue

    if not records:
        return None

    df = pd.DataFrame(records)

    # Normalize GRF to body weight
    body_weight_n = mass_kg * 9.81
    for side in ['ipsi', 'contra']:
        for direction in ['vertical', 'anterior', 'lateral']:
            col_n = f'grf_{direction}_{side}_N'
            col_bw = f'grf_{direction}_{side}_BW'
            if col_n in df.columns:
                df[col_bw] = df[col_n] / body_weight_n
                df.drop(columns=[col_n], inplace=True)

    return df


def interpolate_stride(df: pd.DataFrame, num_points: int = NUM_PHASE_POINTS) -> pd.DataFrame:
    """
    Interpolate a single stride to fixed number of phase points.
    """
    n_samples = len(df)
    if n_samples < 2:
        return pd.DataFrame()

    x_orig = np.linspace(0, 100, n_samples)
    x_target = np.linspace(0, 100, num_points)

    result = {'phase_ipsi': x_target}

    # Copy metadata from first row
    for col in ['subject', 'subject_metadata', 'task', 'task_id', 'task_info', 'step']:
        if col in df.columns:
            result[col] = [df[col].iloc[0]] * num_points

    # Interpolate numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    skip_cols = {'frame_number', 'time_s', 'contact_ipsi', 'contact_contra'}

    for col in numeric_cols:
        if col in skip_cols:
            continue
        try:
            values = df[col].values
            valid = ~np.isnan(values)
            if np.sum(valid) >= 2:
                interp_func = interp1d(x_orig[valid], values[valid],
                                       kind='linear', fill_value='extrapolate')
                result[col] = interp_func(x_target)
            else:
                result[col] = np.full(num_points, np.nan)
        except Exception:
            result[col] = np.full(num_points, np.nan)

    # Compute phase_contra (approximately 50% offset for walking)
    result['phase_contra'] = (x_target + 50) % 100
    result['phase_ipsi_dot'] = np.gradient(x_target)

    return pd.DataFrame(result)


def segment_to_strides(
    df: pd.DataFrame,
    grf_col: str = 'grf_vertical_ipsi_BW',
    time_col: str = 'time_s',
) -> List[pd.DataFrame]:
    """
    Segment time-indexed data into individual strides using GRF.

    Returns list of DataFrames, one per stride.
    """
    if grf_col not in df.columns or time_col not in df.columns:
        return []

    try:
        config = VerticalGRFConfig(
            ipsi_col=grf_col,
            contra_col='grf_vertical_contra_BW',
            time_col=time_col,
            threshold=GRF_THRESHOLD_N / 9.81 / 70.0,  # Convert to BW for ~70kg person
            min_interval_s=MIN_STRIDE_INTERVAL_S,
        )
        events = detect_vertical_grf_events(df, config)
        heel_strikes = events.heel_strikes_ipsi
    except Exception:
        # Fallback: simple threshold crossing
        grf = df[grf_col].values
        threshold = 0.1  # BW
        above = grf > threshold
        crossings = np.where(np.diff(above.astype(int)) > 0)[0]
        heel_strikes = crossings

    if len(heel_strikes) < 2:
        return []

    # Filter strides by duration (IQR method)
    time_values = df[time_col].values
    stride_durations = np.diff(time_values[heel_strikes])

    if len(stride_durations) > 3:
        q1, q3 = np.percentile(stride_durations, [25, 75])
        iqr = q3 - q1
        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr
        valid_mask = (stride_durations >= lower) & (stride_durations <= upper)
    else:
        valid_mask = np.ones(len(stride_durations), dtype=bool)

    # Extract strides
    strides = []
    for i, is_valid in enumerate(valid_mask):
        if not is_valid:
            continue
        start_idx = heel_strikes[i]
        end_idx = heel_strikes[i + 1]
        stride_df = df.iloc[start_idx:end_idx].copy()
        stride_df['step'] = f'{i + 1:03d}'
        strides.append(stride_df)

    return strides


def process_dataset(
    dataset: str,
    input_dir: Path,
    output_dir: Path,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Process all B3D files for a dataset.

    Returns paths to output time and phase parquet files.
    """
    if dataset not in get_supported_datasets():
        raise ValueError(f"Unsupported dataset: {dataset}")

    # Find B3D files (recursively search subdirectories)
    b3d_files = list(input_dir.glob('**/*.b3d'))
    if not b3d_files:
        print(f"No B3D files found in {input_dir}")
        return None, None

    print(f"Processing {len(b3d_files)} B3D files for {dataset}...")

    all_time_dfs = []
    all_phase_dfs = []

    for subject_idx, b3d_path in enumerate(tqdm(b3d_files, desc=f'{dataset} subjects')):
        df_time = process_b3d_file(b3d_path, dataset, subject_idx)
        if df_time is None or df_time.empty:
            continue

        all_time_dfs.append(df_time)

        # Segment into strides and phase-normalize for cyclic tasks
        for task_name in df_time['task'].unique():
            if not is_cyclic_task(task_name):
                continue

            task_df = df_time[df_time['task'] == task_name].copy()
            strides = segment_to_strides(task_df)

            for stride_df in strides:
                phase_df = interpolate_stride(stride_df, NUM_PHASE_POINTS)
                if not phase_df.empty:
                    all_phase_dfs.append(phase_df)

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)

    time_path = None
    phase_path = None

    if all_time_dfs:
        combined_time = pd.concat(all_time_dfs, ignore_index=True)
        time_path = output_dir / f'{dataset}_time.parquet'
        combined_time.to_parquet(time_path, index=False)
        print(f"Saved time-indexed data: {time_path} ({len(combined_time)} rows)")

    if all_phase_dfs:
        combined_phase = pd.concat(all_phase_dfs, ignore_index=True)
        phase_path = output_dir / f'{dataset}_phase.parquet'
        combined_phase.to_parquet(phase_path, index=False)
        print(f"Saved phase-normalized data: {phase_path} ({len(combined_phase)} rows)")

    return time_path, phase_path


def main():
    parser = argparse.ArgumentParser(
        description='Convert AddBiomechanics B3D files to standardized parquet format.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python convert_addbiomechanics_to_parquet.py --dataset Moore2015 --input /data/Moore2015
    python convert_addbiomechanics_to_parquet.py --dataset Hamner2013 --input /data/Hamner2013 --output-dir ./output

Supported datasets:
    Moore2015, Camargo2021, Fregly2012, Hamner2013, Santos2017,
    Tan2021, Tan2022, vanderZee2022, Wang2023
        """
    )
    parser.add_argument(
        '--dataset', '-d',
        required=True,
        choices=get_supported_datasets(),
        help='Dataset name to process'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        type=Path,
        help='Input directory containing B3D files'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / 'converted_datasets',
        help='Output directory for parquet files (default: converted_datasets/)'
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input directory does not exist: {args.input}")
        sys.exit(1)

    time_path, phase_path = process_dataset(
        dataset=args.dataset,
        input_dir=args.input,
        output_dir=args.output_dir,
    )

    if time_path is None and phase_path is None:
        print("No data processed. Check input directory and B3D files.")
        sys.exit(1)

    print("\nConversion complete!")


if __name__ == '__main__':
    main()
