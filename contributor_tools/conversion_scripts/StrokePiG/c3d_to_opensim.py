"""
Convert C3D data to OpenSim-compatible TRC and GRF MOT files.

Handles coordinate system rotation from Vicon to OpenSim.

In this dataset, subjects face +X in the static trial but walk in -X direction.
Two rotations are used:

  **Static trial** (for model scaling): (x_vic, z_vic, -y_vic)
    Subject faces +X_osim, matching the model's default forward direction.
    This ensures correct marker placement during ScaleTool.

  **Walking trials** (for IK/ID): (-x_vic, z_vic, y_vic)
    Walking direction (-X_vic) maps to +X_osim (forward).
    IK can track the motion with pelvis_rotation ≈ 0°.

Both rotations correctly preserve left/right anatomy:
  - In the static rotation: +Y_vic (left) → -Z_osim (left in OpenSim)
  - In the walking rotation: when subject faces -X, their right is at +Y_vic → +Z_osim (right)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

from c3d_parser import load_c3d_file, assign_foot_to_plate
from marker_mapping import PIG_TO_RAJAGOPAL


# Physical PiG marker names (lower body only, matching c3d_parser)
PHYSICAL_PIG_MARKERS = [
    'LFHD', 'RFHD', 'LBHD', 'RBHD',
    'C7', 'T10', 'CLAV', 'STRN',
    'LSHO', 'RSHO', 'LELB', 'RELB',
    'LWRA', 'LWRB', 'RWRA', 'RWRB',
    'LFIN', 'RFIN',
    'LASI', 'RASI', 'LPSI', 'RPSI',
    'LTHI', 'RTHI', 'LKNE', 'RKNE',
    'LTIB', 'RTIB', 'LANK', 'RANK',
    'LHEE', 'RHEE', 'LTOE', 'RTOE',
]

# Lower-body PiG markers used for IK (subset of PHYSICAL_PIG_MARKERS)
LOWER_BODY_PIG_MARKERS = list(PIG_TO_RAJAGOPAL.keys())
PELVIS_PIG_MARKERS = {"LASI", "RASI", "LPSI", "RPSI"}


def _rotate_vicon_to_opensim_static(x_vic, y_vic, z_vic):
    """Rotate Vicon coords to OpenSim for static trials: (x, z, -y).

    Subject faces +X_vic in static trial → faces +X_osim (model default).
    Used for scaling so model markers align correctly.
    """
    return x_vic, z_vic, -y_vic


def _rotate_vicon_to_opensim_walking(x_vic, y_vic, z_vic):
    """Rotate Vicon coords to OpenSim for walking trials: (-x, z, y).

    Subject walks in -X_vic → maps to +X_osim (forward).
    When facing -X_vic, subject's right is at +Y_vic → +Z_osim (right). ✓
    """
    return -x_vic, z_vic, y_vic


def _identity_rotation(x_vic, y_vic, z_vic):
    """Return coordinates unchanged."""
    return x_vic, y_vic, z_vic


def _select_walking_rotation(marker_name: str, walking_rotation_mode: str):
    """Select marker rotation strategy for walking trials."""
    if walking_rotation_mode == "all_markers":
        return _rotate_vicon_to_opensim_walking
    if walking_rotation_mode == "pelvis_only":
        if marker_name in PELVIS_PIG_MARKERS:
            return _rotate_vicon_to_opensim_walking
        return _rotate_vicon_to_opensim_static
    if walking_rotation_mode == "none":
        return _identity_rotation
    raise ValueError(
        f"Invalid walking_rotation_mode: {walking_rotation_mode}. "
        "Expected one of: all_markers, pelvis_only, none."
    )


def c3d_markers_to_trc(
    c3d_data: Dict,
    output_path: Path,
    marker_names: Optional[List[str]] = None,
    walking_rotation_mode: str = "all_markers",
) -> Optional[Path]:
    """
    Convert C3D marker data to TRC file with OpenSim coordinate rotation.

    Args:
        c3d_data: Dict from load_c3d_file() with 'markers', 'point_rate', 'time'
        output_path: Path for output TRC file
        marker_names: List of PiG marker names to include (default: lower body)

    Returns:
        Path to written TRC file, or None on failure
    """
    markers_df = c3d_data['markers']
    rate = c3d_data['point_rate']
    time = c3d_data['time']
    n_frames = len(time)

    if marker_names is None:
        marker_names = LOWER_BODY_PIG_MARKERS

    # Filter to markers actually present in the data
    available_markers = []
    for m in marker_names:
        if f'{m}_X' in markers_df.columns:
            available_markers.append(m)

    if not available_markers:
        print(f"Warning: No markers found in C3D data for TRC export")
        return None

    n_markers = len(available_markers)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        # TRC header
        f.write(f"PathFileType\t4\t(X/Y/Z)\t{output_path.name}\n")
        f.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        f.write(f"{rate:.2f}\t{rate:.2f}\t{n_frames}\t{n_markers}\tmm\t{rate:.2f}\t1\t{n_frames}\n")

        # Marker names line
        f.write("Frame#\tTime\t" + "\t\t\t".join(available_markers) + "\t\t\n")

        # XYZ subheader
        xyz_line = "\t"
        for i in range(n_markers):
            xyz_line += f"\tX{i+1}\tY{i+1}\tZ{i+1}"
        f.write(xyz_line + "\n\n")

        # Data rows
        for i in range(n_frames):
            line = f"{i+1}\t{time[i]:.5f}"
            for m in available_markers:
                x_vic = markers_df[f'{m}_X'].iloc[i]
                y_vic = markers_df[f'{m}_Y'].iloc[i]
                z_vic = markers_df[f'{m}_Z'].iloc[i]
                rotate_fn = _select_walking_rotation(m, walking_rotation_mode)
                x_os, y_os, z_os = rotate_fn(x_vic, y_vic, z_vic)
                line += f"\t{x_os:.5f}\t{y_os:.5f}\t{z_os:.5f}"
            f.write(line + "\n")

    return output_path


def c3d_forces_to_grf_mot(
    c3d_data: Dict,
    output_path: Path,
    foot_assignments: Optional[Dict[int, str]] = None,
) -> Optional[Path]:
    """
    Convert C3D force plate data to OpenSim GRF MOT file.

    Columns: time, ground_force1_vx/vy/vz, ground_force1_px/py/pz,
             ground_torque1_x/y/z, ground_force2_vx/vy/vz, ...

    Convention: force1 = right foot (calcn_r), force2 = left foot (calcn_l)

    Args:
        c3d_data: Dict from load_c3d_file()
        output_path: Path for output MOT file
        foot_assignments: Override plate→foot mapping {plate_num: 'l'|'r'}

    Returns:
        Path to written MOT file, or None on failure
    """
    forces_df = c3d_data['forces']
    markers_df = c3d_data['markers']
    time = c3d_data['time']
    n_frames = len(time)

    # Auto-assign feet if not provided
    if foot_assignments is None:
        foot_assignments = assign_foot_to_plate(markers_df, forces_df)

    if not foot_assignments:
        return None

    # Aggregate by foot side: right → force1, left → force2
    force_r = np.zeros((n_frames, 3))  # fx, fy, fz
    cop_r = np.full((n_frames, 3), np.nan)  # px, py, pz
    torque_r = np.zeros((n_frames, 3))
    force_l = np.zeros((n_frames, 3))
    cop_l = np.full((n_frames, 3), np.nan)
    torque_l = np.zeros((n_frames, 3))

    # Minimum force for sign correction and valid COP (100N filters plate noise)
    min_force_N = 100.0

    for fp_num, foot_side in foot_assignments.items():
        fz_col = f'fp{fp_num}_fz'
        if fz_col not in forces_df.columns:
            continue

        fx = forces_df[f'fp{fp_num}_fx'].values.copy()
        fy = forces_df[f'fp{fp_num}_fy'].values.copy()
        fz = forces_df[f'fp{fp_num}_fz'].values.copy()

        # Ensure vertical GRF is positive (upward)
        contact_mask = np.abs(fz) > min_force_N
        if np.any(contact_mask) and np.mean(fz[contact_mask]) < 0:
            fx = -fx
            fy = -fy
            fz = -fz

        cop_x = forces_df.get(f'fp{fp_num}_cop_x', pd.Series(np.full(n_frames, np.nan))).values
        cop_y = forces_df.get(f'fp{fp_num}_cop_y', pd.Series(np.full(n_frames, np.nan))).values
        cop_z = forces_df.get(f'fp{fp_num}_cop_z', pd.Series(np.zeros(n_frames))).values

        if foot_side == 'r':
            force_r[:, 0] += fx
            force_r[:, 1] += fy
            force_r[:, 2] += fz
            valid = fz > min_force_N
            cop_r[valid, 0] = cop_x[valid]
            cop_r[valid, 1] = cop_y[valid]
            cop_r[valid, 2] = cop_z[valid]
        elif foot_side == 'l':
            force_l[:, 0] += fx
            force_l[:, 1] += fy
            force_l[:, 2] += fz
            valid = fz > min_force_N
            cop_l[valid, 0] = cop_x[valid]
            cop_l[valid, 1] = cop_y[valid]
            cop_l[valid, 2] = cop_z[valid]

    # Replace NaN COP with zeros (OpenSim expects numeric values)
    cop_r = np.nan_to_num(cop_r, nan=0.0)
    cop_l = np.nan_to_num(cop_l, nan=0.0)

    # Apply coordinate rotation: Vicon (x,y,z) → OpenSim (-x, z, y)
    # Forces (N) - rotate direction only
    f1_vx, f1_vy, f1_vz = _rotate_vicon_to_opensim_walking(force_r[:, 0], force_r[:, 1], force_r[:, 2])
    f2_vx, f2_vy, f2_vz = _rotate_vicon_to_opensim_walking(force_l[:, 0], force_l[:, 1], force_l[:, 2])

    # COP (mm → m) - rotate and convert units
    p1_x, p1_y, p1_z = _rotate_vicon_to_opensim_walking(cop_r[:, 0], cop_r[:, 1], cop_r[:, 2])
    p1_x /= 1000.0; p1_y /= 1000.0; p1_z /= 1000.0
    p2_x, p2_y, p2_z = _rotate_vicon_to_opensim_walking(cop_l[:, 0], cop_l[:, 1], cop_l[:, 2])
    p2_x /= 1000.0; p2_y /= 1000.0; p2_z /= 1000.0

    # Torques (Nmm → Nm) - rotate and convert units
    t1_x, t1_y, t1_z = _rotate_vicon_to_opensim_walking(torque_r[:, 0], torque_r[:, 1], torque_r[:, 2])
    t1_x /= 1000.0; t1_y /= 1000.0; t1_z /= 1000.0
    t2_x, t2_y, t2_z = _rotate_vicon_to_opensim_walking(torque_l[:, 0], torque_l[:, 1], torque_l[:, 2])
    t2_x /= 1000.0; t2_y /= 1000.0; t2_z /= 1000.0

    # Write MOT file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        'time',
        'ground_force1_vx', 'ground_force1_vy', 'ground_force1_vz',
        'ground_force1_px', 'ground_force1_py', 'ground_force1_pz',
        'ground_torque1_x', 'ground_torque1_y', 'ground_torque1_z',
        'ground_force2_vx', 'ground_force2_vy', 'ground_force2_vz',
        'ground_force2_px', 'ground_force2_py', 'ground_force2_pz',
        'ground_torque2_x', 'ground_torque2_y', 'ground_torque2_z',
    ]

    with open(output_path, 'w') as f:
        f.write("grf_data\n")
        f.write("version=1\n")
        f.write(f"nRows={n_frames}\n")
        f.write(f"nColumns={len(columns)}\n")
        f.write("inDegrees=no\n")
        f.write("endheader\n")
        f.write("\t".join(columns) + "\n")

        for i in range(n_frames):
            vals = [
                time[i],
                f1_vx[i], f1_vy[i], f1_vz[i],
                p1_x[i], p1_y[i], p1_z[i],
                t1_x[i], t1_y[i], t1_z[i],
                f2_vx[i], f2_vy[i], f2_vz[i],
                p2_x[i], p2_y[i], p2_z[i],
                t2_x[i], t2_y[i], t2_z[i],
            ]
            f.write("\t".join(f"{v:.6f}" for v in vals) + "\n")

    return output_path


def stride_c3d_to_grf_mot(
    c3d_data: Dict,
    output_path: Path,
    start_idx: int,
    end_idx: int,
) -> Optional[Path]:
    """
    Write a stride-specific GRF MOT directly from C3D data.

    Unlike c3d_forces_to_grf_mot() + slice_grf_mot(), this does foot-to-plate
    assignment on the stride slice only, avoiding cross-stride plate confusion.

    Args:
        c3d_data: Dict from load_c3d_file()
        output_path: Path for output MOT file
        start_idx: Start frame index in the C3D data
        end_idx: End frame index (exclusive)

    Returns:
        Path to written MOT file, or None on failure
    """
    forces_df = c3d_data['forces']
    markers_df = c3d_data['markers']
    time = c3d_data['time']

    # Slice to stride
    stride_forces = forces_df.iloc[start_idx:end_idx].reset_index(drop=True)
    stride_markers = markers_df.iloc[start_idx:end_idx].reset_index(drop=True)
    stride_time = time[start_idx:end_idx]
    n_frames = len(stride_forces)

    if n_frames < 5:
        return None

    # Use 100N threshold to filter out plate noise (matches extract_grf_for_stride)
    min_peak_force_N = 100.0

    # Assign feet for this stride only, using high threshold
    foot_assignments = assign_foot_to_plate(
        stride_markers, stride_forces, force_threshold=min_peak_force_N
    )
    if not foot_assignments:
        return None

    # Aggregate by foot side
    min_force_N = min_peak_force_N
    force_r = np.zeros((n_frames, 3))
    cop_r = np.full((n_frames, 3), np.nan)
    torque_r = np.zeros((n_frames, 3))
    force_l = np.zeros((n_frames, 3))
    cop_l = np.full((n_frames, 3), np.nan)
    torque_l = np.zeros((n_frames, 3))

    for fp_num, foot_side in foot_assignments.items():
        fz_col = f'fp{fp_num}_fz'
        if fz_col not in stride_forces.columns:
            continue

        fx = stride_forces[f'fp{fp_num}_fx'].values.copy()
        fy = stride_forces[f'fp{fp_num}_fy'].values.copy()
        fz = stride_forces[f'fp{fp_num}_fz'].values.copy()

        contact_mask = np.abs(fz) > min_force_N
        if np.any(contact_mask) and np.mean(fz[contact_mask]) < 0:
            fx = -fx
            fy = -fy
            fz = -fz

        cop_x = stride_forces.get(f'fp{fp_num}_cop_x',
                                   pd.Series(np.full(n_frames, np.nan))).values
        cop_y = stride_forces.get(f'fp{fp_num}_cop_y',
                                   pd.Series(np.full(n_frames, np.nan))).values
        cop_z = stride_forces.get(f'fp{fp_num}_cop_z',
                                   pd.Series(np.zeros(n_frames))).values

        valid = fz > min_force_N
        if foot_side == 'r':
            force_r[:, 0] += fx
            force_r[:, 1] += fy
            force_r[:, 2] += fz
            cop_r[valid, 0] = cop_x[valid]
            cop_r[valid, 1] = cop_y[valid]
            cop_r[valid, 2] = cop_z[valid]
        elif foot_side == 'l':
            force_l[:, 0] += fx
            force_l[:, 1] += fy
            force_l[:, 2] += fz
            cop_l[valid, 0] = cop_x[valid]
            cop_l[valid, 1] = cop_y[valid]
            cop_l[valid, 2] = cop_z[valid]

    # Check that at least one foot has meaningful contact
    peak_fz_r = np.max(force_r[:, 2]) if np.any(force_r[:, 2] > 0) else 0
    peak_fz_l = np.max(force_l[:, 2]) if np.any(force_l[:, 2] > 0) else 0
    if peak_fz_r < min_peak_force_N and peak_fz_l < min_peak_force_N:
        return None

    cop_r = np.nan_to_num(cop_r, nan=0.0)
    cop_l = np.nan_to_num(cop_l, nan=0.0)

    # Apply coordinate rotation and unit conversion
    f1_vx, f1_vy, f1_vz = _rotate_vicon_to_opensim_walking(force_r[:, 0], force_r[:, 1], force_r[:, 2])
    f2_vx, f2_vy, f2_vz = _rotate_vicon_to_opensim_walking(force_l[:, 0], force_l[:, 1], force_l[:, 2])

    p1_x, p1_y, p1_z = _rotate_vicon_to_opensim_walking(cop_r[:, 0], cop_r[:, 1], cop_r[:, 2])
    p1_x /= 1000.0; p1_y /= 1000.0; p1_z /= 1000.0
    p2_x, p2_y, p2_z = _rotate_vicon_to_opensim_walking(cop_l[:, 0], cop_l[:, 1], cop_l[:, 2])
    p2_x /= 1000.0; p2_y /= 1000.0; p2_z /= 1000.0

    t1_x, t1_y, t1_z = _rotate_vicon_to_opensim_walking(torque_r[:, 0], torque_r[:, 1], torque_r[:, 2])
    t1_x /= 1000.0; t1_y /= 1000.0; t1_z /= 1000.0
    t2_x, t2_y, t2_z = _rotate_vicon_to_opensim_walking(torque_l[:, 0], torque_l[:, 1], torque_l[:, 2])
    t2_x /= 1000.0; t2_y /= 1000.0; t2_z /= 1000.0

    # Zero-base time
    t0 = stride_time[0]
    time_zeroed = stride_time - t0

    # Write MOT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        'time',
        'ground_force1_vx', 'ground_force1_vy', 'ground_force1_vz',
        'ground_force1_px', 'ground_force1_py', 'ground_force1_pz',
        'ground_torque1_x', 'ground_torque1_y', 'ground_torque1_z',
        'ground_force2_vx', 'ground_force2_vy', 'ground_force2_vz',
        'ground_force2_px', 'ground_force2_py', 'ground_force2_pz',
        'ground_torque2_x', 'ground_torque2_y', 'ground_torque2_z',
    ]

    with open(output_path, 'w') as f:
        f.write("grf_data\n")
        f.write("version=1\n")
        f.write(f"nRows={n_frames}\n")
        f.write(f"nColumns={len(columns)}\n")
        f.write("inDegrees=no\n")
        f.write("endheader\n")
        f.write("\t".join(columns) + "\n")

        for i in range(n_frames):
            vals = [
                time_zeroed[i],
                f1_vx[i], f1_vy[i], f1_vz[i],
                p1_x[i], p1_y[i], p1_z[i],
                t1_x[i], t1_y[i], t1_z[i],
                f2_vx[i], f2_vy[i], f2_vz[i],
                p2_x[i], p2_y[i], p2_z[i],
                t2_x[i], t2_y[i], t2_z[i],
            ]
            f.write("\t".join(f"{v:.6f}" for v in vals) + "\n")

    return output_path


def find_static_c3d(subject_path: Path) -> Optional[Path]:
    """
    Find the calibration/static C3D file for a subject.

    Args:
        subject_path: Path to subject folder (e.g., .../TVC03/)

    Returns:
        Path to static C3D file, or None if not found
    """
    # Look for Cal*.c3d files
    cal_files = sorted(subject_path.glob("*Cal*.c3d"))
    if cal_files:
        return cal_files[0]

    # Also try lowercase
    cal_files = sorted(subject_path.glob("*cal*.c3d"))
    if cal_files:
        return cal_files[0]

    return None


def static_c3d_to_trc(
    static_c3d_path: Path,
    output_path: Path,
    marker_names: Optional[List[str]] = None,
) -> Optional[Path]:
    """
    Extract markers from a static C3D file and write as TRC.

    Averages marker positions over the middle 50 frames for stability.
    Applies Vicon → OpenSim coordinate rotation.

    Args:
        static_c3d_path: Path to static/calibration C3D file
        output_path: Path for output TRC file
        marker_names: List of PiG marker names (default: lower body)

    Returns:
        Path to written TRC file, or None on failure
    """
    c3d_data = load_c3d_file(static_c3d_path)
    if c3d_data is None:
        return None

    markers_df = c3d_data['markers']
    rate = c3d_data['point_rate']
    n_total = len(markers_df)

    if marker_names is None:
        marker_names = LOWER_BODY_PIG_MARKERS

    # Filter to available markers
    available_markers = [m for m in marker_names if f'{m}_X' in markers_df.columns]
    if not available_markers:
        print(f"Warning: No markers found in static C3D")
        return None

    # Extract middle 50 frames (OpenSim ScaleTool needs >=2 frames for time range)
    mid = n_total // 2
    half_window = 25
    start = max(0, mid - half_window)
    end = min(n_total, mid + half_window)
    window_df = markers_df.iloc[start:end].reset_index(drop=True)
    time_window = c3d_data['time'][start:end]

    n_markers = len(available_markers)
    n_frames = len(window_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(f"PathFileType\t4\t(X/Y/Z)\t{output_path.name}\n")
        f.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        f.write(f"{rate:.2f}\t{rate:.2f}\t{n_frames}\t{n_markers}\tmm\t{rate:.2f}\t1\t{n_frames}\n")
        f.write("Frame#\tTime\t" + "\t\t\t".join(available_markers) + "\t\t\n")

        xyz_line = "\t"
        for i in range(n_markers):
            xyz_line += f"\tX{i+1}\tY{i+1}\tZ{i+1}"
        f.write(xyz_line + "\n\n")

        # Write all frames from the window
        for i in range(n_frames):
            t = time_window[i] - time_window[0]  # Zero-base time
            line = f"{i+1}\t{t:.5f}"
            for m in available_markers:
                x_vic = window_df[f'{m}_X'].iloc[i]
                y_vic = window_df[f'{m}_Y'].iloc[i]
                z_vic = window_df[f'{m}_Z'].iloc[i]
                x_os, y_os, z_os = _rotate_vicon_to_opensim_static(x_vic, y_vic, z_vic)
                line += f"\t{x_os:.5f}\t{y_os:.5f}\t{z_os:.5f}"
            f.write(line + "\n")

    return output_path


def slice_trc(
    full_trc_path: Path,
    output_path: Path,
    start_idx: int,
    end_idx: int,
) -> Optional[Path]:
    """
    Slice a TRC file to a subset of frames.

    Args:
        full_trc_path: Path to full-trial TRC file
        output_path: Path for sliced output TRC
        start_idx: Start frame index (0-based)
        end_idx: End frame index (exclusive)

    Returns:
        Path to sliced TRC file, or None on failure
    """
    try:
        with open(full_trc_path, 'r') as f:
            lines = f.readlines()

        if len(lines) < 6:
            return None

        # Parse header
        header_lines = lines[:6]
        data_lines = lines[6:]

        # Filter to valid data lines
        data_lines = [l for l in data_lines if l.strip()]

        if end_idx > len(data_lines):
            end_idx = len(data_lines)
        if start_idx >= end_idx:
            return None

        sliced_data = data_lines[start_idx:end_idx]
        n_frames = len(sliced_data)

        # Update header with new frame count
        rate_parts = header_lines[2].strip().split('\t')
        rate_parts[2] = str(n_frames)
        rate_parts[7] = str(n_frames)
        header_lines[2] = '\t'.join(rate_parts) + '\n'

        # Renumber frames and adjust time
        first_time = float(sliced_data[0].strip().split('\t')[1])
        renumbered = []
        for i, line in enumerate(sliced_data):
            parts = line.strip().split('\t')
            parts[0] = str(i + 1)
            parts[1] = f"{float(parts[1]) - first_time:.5f}"
            renumbered.append('\t'.join(parts) + '\n')

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.writelines(header_lines)
            f.writelines(renumbered)

        return output_path

    except Exception as e:
        print(f"Warning: Could not slice TRC: {e}")
        return None


def slice_grf_mot(
    full_mot_path: Path,
    output_path: Path,
    start_idx: int,
    end_idx: int,
) -> Optional[Path]:
    """
    Slice a GRF MOT file to a subset of frames.

    Args:
        full_mot_path: Path to full-trial GRF MOT file
        output_path: Path for sliced output MOT
        start_idx: Start frame index (0-based into data)
        end_idx: End frame index (exclusive)

    Returns:
        Path to sliced MOT file, or None on failure
    """
    try:
        with open(full_mot_path, 'r') as f:
            lines = f.readlines()

        # Find header end
        header_end = 0
        for i, line in enumerate(lines):
            if 'endheader' in line.lower():
                header_end = i
                break

        column_line = lines[header_end + 1]
        data_lines = [l for l in lines[header_end + 2:] if l.strip()]

        if end_idx > len(data_lines):
            end_idx = len(data_lines)
        if start_idx >= end_idx:
            return None

        sliced_data = data_lines[start_idx:end_idx]
        n_rows = len(sliced_data)

        # Adjust time to start at 0
        first_time = float(sliced_data[0].strip().split('\t')[0])
        renumbered = []
        for line in sliced_data:
            parts = line.strip().split('\t')
            parts[0] = f"{float(parts[0]) - first_time:.6f}"
            renumbered.append('\t'.join(parts) + '\n')

        # Count columns
        n_cols = len(column_line.strip().split('\t'))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write("grf_data\n")
            f.write("version=1\n")
            f.write(f"nRows={n_rows}\n")
            f.write(f"nColumns={n_cols}\n")
            f.write("inDegrees=no\n")
            f.write("endheader\n")
            f.write(column_line)
            f.writelines(renumbered)

        return output_path

    except Exception as e:
        print(f"Warning: Could not slice GRF MOT: {e}")
        return None
