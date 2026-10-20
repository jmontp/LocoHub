"""
C3D file parsing for the StrokePiG dataset.

Extracts marker trajectories and force plate data from C3D files using ezc3d.
Handles coordinate system mapping and COP computation for Type 2 force plates.

Coordinate system (Vicon global):
- X: walking direction (positive to negative = forward)
- Y: medial-lateral
- Z: vertical (up)

Force plate channels (Type 2):
- Fx, Fy, Fz: forces in global coordinate frame
- Mx, My, Mz: moments in global coordinate frame

COP computation for Type 2:
- COP_x = (-My * dz - Mx) / Fz + plate_center_x  (simplified)
- COP_y = (Mx * dz + My) / Fz + plate_center_y   (simplified)
where dz is the plate thickness (origin Z offset)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import ezc3d
    EZC3D_AVAILABLE = True
except ImportError:
    EZC3D_AVAILABLE = False


def load_c3d_file(c3d_path: Path) -> Optional[Dict]:
    """
    Load a C3D file and extract marker and force plate data.

    Args:
        c3d_path: Path to the C3D file

    Returns:
        Dictionary with:
        - 'markers': DataFrame with marker positions (mm)
        - 'forces': DataFrame with force plate data (N, Nm)
        - 'point_rate': marker sampling rate (Hz)
        - 'analog_rate': analog sampling rate (Hz)
        - 'time': time array at marker rate
        Or None if loading fails
    """
    if not EZC3D_AVAILABLE:
        print("Warning: ezc3d not installed. Cannot parse C3D files.")
        return None

    if not c3d_path.exists():
        return None

    try:
        c3d = ezc3d.c3d(str(c3d_path))
    except Exception as e:
        print(f"Warning: Could not load {c3d_path}: {e}")
        return None

    point_rate = c3d['header']['points']['frame_rate']
    analog_rate = c3d['header']['analogs']['frame_rate']
    first_frame = c3d['header']['points']['first_frame']
    n_frames = c3d['data']['points'].shape[2]

    # Time array at marker frame rate
    time = np.arange(n_frames) / point_rate + first_frame / point_rate

    # Extract markers
    markers_df = _extract_markers(c3d, time)

    # Extract force plate data
    forces_df = _extract_force_plates(c3d, time)

    return {
        'markers': markers_df,
        'forces': forces_df,
        'point_rate': point_rate,
        'analog_rate': analog_rate,
        'time': time,
    }


def _extract_markers(c3d, time: np.ndarray) -> pd.DataFrame:
    """
    Extract marker trajectories from C3D data.

    Args:
        c3d: ezc3d.c3d object
        time: time array

    Returns:
        DataFrame with columns: Time, MarkerName_X, MarkerName_Y, MarkerName_Z
    """
    points = c3d['data']['points']  # (4, n_markers, n_frames)
    labels = c3d['parameters']['POINT']['LABELS']['value']
    n_frames = points.shape[2]

    # Only extract physical markers (not computed angles, forces, etc.)
    # Physical markers are the first ~34 labels (PiG markers)
    physical_markers = [
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

    data = {'Time': time}

    for marker_name in physical_markers:
        if marker_name in labels:
            idx = labels.index(marker_name)
            data[f'{marker_name}_X'] = points[0, idx, :n_frames]
            data[f'{marker_name}_Y'] = points[1, idx, :n_frames]
            data[f'{marker_name}_Z'] = points[2, idx, :n_frames]

    return pd.DataFrame(data)


def _extract_force_plates(c3d, time: np.ndarray) -> pd.DataFrame:
    """
    Extract force plate data from C3D analog channels.

    Downsamples analog data to marker frame rate and computes COP.

    Args:
        c3d: ezc3d.c3d object
        time: time array at marker rate

    Returns:
        DataFrame with columns:
        - time
        - fp{n}_fx, fp{n}_fy, fp{n}_fz (forces in N)
        - fp{n}_cop_x, fp{n}_cop_y, fp{n}_cop_z (COP in mm)
    """
    analog = c3d['data']['analogs'][0]  # (n_channels, n_analog_samples)
    analog_labels = c3d['parameters']['ANALOG']['LABELS']['value']

    point_rate = c3d['header']['points']['frame_rate']
    analog_rate = c3d['header']['analogs']['frame_rate']
    ratio = int(analog_rate / point_rate)
    n_frames = len(time)

    fp_params = c3d['parameters']['FORCE_PLATFORM']
    n_plates = fp_params['USED']['value'][0]
    corners = fp_params['CORNERS']['value']  # (3, 4, n_plates)
    origins = fp_params['ORIGIN']['value']   # (3, n_plates)

    # Channel mapping for Type 2 force plates
    # Channels are: Fx, Fy, Fz, Mx, My, Mz for each plate
    channels = fp_params['CHANNEL']['value']  # (6, n_plates)

    data = {'time': time}

    for fp_idx in range(min(n_plates, 4)):  # Max 4 force plates
        fp_num = fp_idx + 1

        # Get channel indices (1-indexed in C3D)
        ch_fx = channels[0, fp_idx] - 1
        ch_fy = channels[1, fp_idx] - 1
        ch_fz = channels[2, fp_idx] - 1
        ch_mx = channels[3, fp_idx] - 1
        ch_my = channels[4, fp_idx] - 1
        ch_mz = channels[5, fp_idx] - 1

        # Extract raw analog channels
        fx_raw = analog[ch_fx, :]
        fy_raw = analog[ch_fy, :]
        fz_raw = analog[ch_fz, :]
        mx_raw = analog[ch_mx, :]
        my_raw = analog[ch_my, :]
        mz_raw = analog[ch_mz, :]

        # Downsample to marker rate (average each block)
        n_analog_needed = n_frames * ratio
        if len(fx_raw) < n_analog_needed:
            n_frames_actual = len(fx_raw) // ratio
        else:
            n_frames_actual = n_frames

        fx = fx_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)
        fy = fy_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)
        fz = fz_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)
        mx = mx_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)
        my = my_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)
        mz = mz_raw[:n_frames_actual * ratio].reshape(n_frames_actual, ratio).mean(axis=1)

        # Pad if needed
        if n_frames_actual < n_frames:
            pad_len = n_frames - n_frames_actual
            fx = np.pad(fx, (0, pad_len), constant_values=0)
            fy = np.pad(fy, (0, pad_len), constant_values=0)
            fz = np.pad(fz, (0, pad_len), constant_values=0)
            mx = np.pad(mx, (0, pad_len), constant_values=0)
            my = np.pad(my, (0, pad_len), constant_values=0)
            mz = np.pad(mz, (0, pad_len), constant_values=0)

        # Store forces
        data[f'fp{fp_num}_fx'] = fx
        data[f'fp{fp_num}_fy'] = fy
        data[f'fp{fp_num}_fz'] = fz

        # Compute COP for Type 2 force plate
        # Moments (Nmm) are measured at the electrical origin.
        # Electrical origin position in global coords:
        #   origin = plate_center + offset  (X,Y)
        #   origin_z = -dz  (dz is positive downward into plate)
        #
        # COP on surface (Z=0) from cross product M = (COP - origin) × F:
        #   COP_x = origin_x - (My - dz * Fx) / Fz
        #   COP_y = origin_y + (Mx + dz * Fy) / Fz

        plate_center_x = np.mean(corners[0, :, fp_idx])
        plate_center_y = np.mean(corners[1, :, fp_idx])
        elec_x = plate_center_x + origins[0, fp_idx]
        elec_y = plate_center_y + origins[1, fp_idx]
        dz = origins[2, fp_idx]  # mm, positive downward

        # Store plate center for foot-to-plate assignment
        data[f'fp{fp_num}_center_x'] = np.full(n_frames, plate_center_x)
        data[f'fp{fp_num}_center_y'] = np.full(n_frames, plate_center_y)

        # COP is only meaningful when there's significant vertical force
        fz_threshold = 20.0  # N
        contact_mask = np.abs(fz) > fz_threshold

        cop_x = np.full(n_frames, np.nan)
        cop_y = np.full(n_frames, np.nan)

        if np.any(contact_mask):
            # All quantities in mm and N: moments in Nmm, dz in mm
            cop_x[contact_mask] = elec_x - (my[contact_mask] - dz * fx[contact_mask]) / fz[contact_mask]
            cop_y[contact_mask] = elec_y + (mx[contact_mask] + dz * fy[contact_mask]) / fz[contact_mask]

        data[f'fp{fp_num}_cop_x'] = cop_x
        data[f'fp{fp_num}_cop_y'] = cop_y
        data[f'fp{fp_num}_cop_z'] = np.zeros(n_frames)  # Floor level

    return pd.DataFrame(data)


def assign_foot_to_plate(
    markers_df: pd.DataFrame,
    forces_df: pd.DataFrame,
    force_threshold: float = 20.0,
) -> Dict[int, str]:
    """
    Determine which foot (left/right) contacts each force plate.

    Uses heel marker proximity to plate center during the contact period.

    Args:
        markers_df: Marker DataFrame with LHEE_*, RHEE_* columns
        forces_df: Force plate DataFrame
        force_threshold: Minimum vertical force (N) for contact detection

    Returns:
        Dictionary mapping plate number to foot side: {1: 'l', 2: 'r', ...}
    """
    assignments = {}

    for fp_num in range(1, 5):
        fz_col = f'fp{fp_num}_fz'
        center_x_col = f'fp{fp_num}_center_x'
        center_y_col = f'fp{fp_num}_center_y'

        if fz_col not in forces_df.columns:
            continue

        fz = forces_df[fz_col].values
        contact_mask = np.abs(fz) > force_threshold

        if not np.any(contact_mask):
            continue

        # Get mid-contact frame
        contact_frames = np.where(contact_mask)[0]
        mid_frame = contact_frames[len(contact_frames) // 2]

        # Check which heel marker is closer to the plate center during contact
        lhee_x = markers_df.get('LHEE_X', pd.Series(dtype=float))
        lhee_y = markers_df.get('LHEE_Y', pd.Series(dtype=float))
        rhee_x = markers_df.get('RHEE_X', pd.Series(dtype=float))
        rhee_y = markers_df.get('RHEE_Y', pd.Series(dtype=float))

        if len(lhee_x) == 0 or len(rhee_x) == 0:
            continue
        if mid_frame >= len(lhee_x):
            continue

        # Use plate center (always available, stored by _extract_force_plates)
        if center_x_col in forces_df.columns:
            ref_x = forces_df[center_x_col].iloc[0]
            ref_y = forces_df[center_y_col].iloc[0]
        else:
            # Fallback to COP
            cop_x = forces_df.get(f'fp{fp_num}_cop_x')
            cop_y = forces_df.get(f'fp{fp_num}_cop_y')
            if cop_x is None:
                continue
            ref_x = np.nanmean(cop_x.values[contact_mask])
            ref_y = np.nanmean(cop_y.values[contact_mask])
            if np.isnan(ref_x):
                continue

        # Distance from each heel to plate center at mid-contact
        l_dist = np.sqrt(
            (lhee_x.iloc[mid_frame] - ref_x) ** 2 +
            (lhee_y.iloc[mid_frame] - ref_y) ** 2
        )
        r_dist = np.sqrt(
            (rhee_x.iloc[mid_frame] - ref_x) ** 2 +
            (rhee_y.iloc[mid_frame] - ref_y) ** 2
        )

        if l_dist < r_dist:
            assignments[fp_num] = 'l'
        else:
            assignments[fp_num] = 'r'

    return assignments


def extract_grf_for_stride(
    forces_df: pd.DataFrame,
    markers_df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    ipsi_side: str,
    body_mass_kg: float,
    num_points: int = 150,
) -> Optional[Dict[str, np.ndarray]]:
    """
    Extract and phase-normalize GRF data for a single stride.

    Assigns force plates to ipsi/contra based on heel marker proximity,
    then phase-normalizes to num_points.

    Args:
        forces_df: Force plate DataFrame for the full trial
        markers_df: Marker DataFrame for the full trial
        start_idx: Start index of stride
        end_idx: End index of stride
        ipsi_side: 'l' or 'r' for ipsilateral (affected) leg
        body_mass_kg: Subject body mass
        num_points: Number of phase points

    Returns:
        Dictionary with GRF arrays, or None if no force data
    """
    from scipy.interpolate import interp1d

    contra_side = 'r' if ipsi_side == 'l' else 'l'
    stride_forces = forces_df.iloc[start_idx:end_idx].copy()
    stride_markers = markers_df.iloc[start_idx:end_idx].copy()
    n_samples = len(stride_forces)

    if n_samples < 10:
        return None

    body_weight_N = body_mass_kg * 9.81

    # Minimum peak force for a plate to be considered as having real contact
    # (filters out noise from plates not in the walking path)
    min_peak_force_N = 100.0

    # Assign force plates to feet for this stride, using higher threshold
    assignments = assign_foot_to_plate(
        stride_markers, stride_forces, force_threshold=min_peak_force_N
    )

    if not assignments:
        return None

    # Aggregate forces by side, correcting sign per-plate before aggregation
    ipsi_fz = np.zeros(n_samples)
    ipsi_fx = np.zeros(n_samples)
    ipsi_fy = np.zeros(n_samples)
    contra_fz = np.zeros(n_samples)
    contra_fx = np.zeros(n_samples)
    contra_fy = np.zeros(n_samples)
    ipsi_cop_x = np.full(n_samples, np.nan)
    ipsi_cop_y = np.full(n_samples, np.nan)
    contra_cop_x = np.full(n_samples, np.nan)
    contra_cop_y = np.full(n_samples, np.nan)

    for fp_num, foot_side in assignments.items():
        fz = stride_forces[f'fp{fp_num}_fz'].values.copy()
        fx = stride_forces[f'fp{fp_num}_fx'].values.copy()
        fy = stride_forces[f'fp{fp_num}_fy'].values.copy()
        cop_x = stride_forces[f'fp{fp_num}_cop_x'].values
        cop_y = stride_forces[f'fp{fp_num}_cop_y'].values

        # Correct sign per-plate: ensure vertical GRF is positive (upward)
        contact_mask = np.abs(fz) > min_peak_force_N
        if np.any(contact_mask) and np.mean(fz[contact_mask]) < 0:
            fz = -fz
            fx = -fx
            fy = -fy

        if foot_side == ipsi_side:
            ipsi_fz += fz
            ipsi_fx += fx
            ipsi_fy += fy
            contact = fz > 20
            ipsi_cop_x[contact] = cop_x[contact]
            ipsi_cop_y[contact] = cop_y[contact]
        elif foot_side == contra_side:
            contra_fz += fz
            contra_fx += fx
            contra_fy += fy
            contact = fz > 20
            contra_cop_x[contact] = cop_x[contact]
            contra_cop_y[contact] = cop_y[contact]

    # Phase-normalize
    phase_orig = np.linspace(0, 100, n_samples)
    phase_target = np.linspace(0, 100, num_points)

    def resample(data, fill=0.0):
        try:
            f = interp1d(phase_orig, data, kind='linear',
                        bounds_error=False, fill_value=fill)
            return f(phase_target)
        except Exception:
            return np.full(num_points, np.nan)

    grf_vertical_ipsi = resample(ipsi_fz)
    grf_vertical_contra = resample(contra_fz)
    grf_anterior_ipsi = resample(ipsi_fx)
    grf_anterior_contra = resample(contra_fx)
    grf_lateral_ipsi = resample(ipsi_fy)
    grf_lateral_contra = resample(contra_fy)

    # COP (mm → m)
    cop_ant_ipsi = resample(ipsi_cop_x, fill=np.nan) / 1000.0
    cop_lat_ipsi = resample(ipsi_cop_y, fill=np.nan) / 1000.0
    cop_ant_contra = resample(contra_cop_x, fill=np.nan) / 1000.0
    cop_lat_contra = resample(contra_cop_y, fill=np.nan) / 1000.0

    return {
        'grf_vertical_ipsi_N': grf_vertical_ipsi,
        'grf_vertical_contra_N': grf_vertical_contra,
        'grf_anterior_ipsi_N': grf_anterior_ipsi,
        'grf_anterior_contra_N': grf_anterior_contra,
        'grf_lateral_ipsi_N': grf_lateral_ipsi,
        'grf_lateral_contra_N': grf_lateral_contra,
        'grf_vertical_ipsi_BW': grf_vertical_ipsi / body_weight_N,
        'grf_vertical_contra_BW': grf_vertical_contra / body_weight_N,
        'grf_anterior_ipsi_BW': grf_anterior_ipsi / body_weight_N,
        'grf_anterior_contra_BW': grf_anterior_contra / body_weight_N,
        'grf_lateral_ipsi_BW': grf_lateral_ipsi / body_weight_N,
        'grf_lateral_contra_BW': grf_lateral_contra / body_weight_N,
        'cop_anterior_ipsi_m': cop_ant_ipsi,
        'cop_lateral_ipsi_m': cop_lat_ipsi,
        'cop_anterior_contra_m': cop_ant_contra,
        'cop_lateral_contra_m': cop_lat_contra,
    }


def find_c3d_for_mot(mot_path: Path) -> Optional[Path]:
    """
    Find the corresponding C3D file for an IK MOT file.

    Naming conventions:
    - MOT: BWA6_ik.mot or BWA6_test_ik.mot or BWA6_test_rotated_ik.mot
    - C3D: BWA6.c3d

    Args:
        mot_path: Path to the IK MOT file

    Returns:
        Path to corresponding C3D file, or None if not found
    """
    # Extract base trial name from MOT filename
    # BWA6_ik.mot -> BWA6
    # BWA6_test_ik.mot -> BWA6
    # BWA6_test_rotated_ik.mot -> BWA6
    stem = mot_path.stem  # e.g., "BWA6_ik" or "BWA6_test_rotated_ik"

    # Remove _ik suffix and any _test, _rotated suffixes
    trial_name = stem.replace('_ik', '').replace('_test_rotated', '').replace('_test', '')

    c3d_path = mot_path.parent / f"{trial_name}.c3d"
    if c3d_path.exists():
        return c3d_path

    # Try with different separators (BWA_6 vs BWA6)
    # Some subjects use underscores
    import re
    match = re.match(r'(BWA)_?(\d+)', trial_name)
    if match:
        prefix = match.group(1)
        num = match.group(2)
        for pattern in [f"{prefix}{num}.c3d", f"{prefix}_{num}.c3d"]:
            p = mot_path.parent / pattern
            if p.exists():
                return p

    return None
