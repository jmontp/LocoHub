#!/usr/bin/env python3
"""
Convert StrokePiG dataset to standardized phase-normalized parquet format.

This script converts the 50_StrokePiG stroke survivor gait dataset to the
LocoHub standardized format.

Dataset:
- 51 stroke survivors (TVC03-TVC60 with gaps)
- Level walking trials (BWA = "Bare foot Walking Affected" side first)
- Plug-in Gait marker set (43 markers)
- Pre-computed IK in .mot format (OpenSim Rajagopal model)
- 100 Hz sampling rate

Data structure:
    TVC03/
        BWA6.c3d, BWA7.c3d, BWA8.c3d  # Walking trials (C3D format)
        BWA6.trc, BWA7.trc, BWA8.trc  # Marker data (TRC format)
        BWA6_ik.mot, ...              # Pre-computed IK results
        TVC-3.mp                       # Anthropometric parameters
        TVC-3 Cal 04.c3d              # Calibration/static trial

Sign conventions in source data (OpenSim Rajagopal, scaled for this dataset):
- Hip: flexion +, adduction +, internal rotation +
- Knee: flexion + (range [0, 2.09] rad, 0 at full extension)
- Ankle: dorsiflexion +

Output: Phase-normalized parquet file with 150 points per gait cycle.

Clinical convention:
- ipsi = anatomical reference leg; use the affected leg when known
- Unknown affected side stays unknown, with left used only as the reference
- Strides are segmented from reference-leg heel strike

Usage:
    python convert_strokepig_to_parquet.py --input /mnt/s/locomotion_data/50_StrokePiG

    # Test single subject
    python convert_strokepig_to_parquet.py --test --subject TVC03

    # Explore data structure
    python convert_strokepig_to_parquet.py --explore
"""

import os
import re
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from scipy.interpolate import interp1d
from tqdm import tqdm

# Add path for common utilities - use direct file imports to avoid
# triggering common/__init__.py which may reference uninstalled modules
_common_dir = str(Path(__file__).parent.parent.parent / 'common')
sys.path.insert(0, _common_dir)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from derivatives import (
    compute_velocity_from_shifted_angle,
    compute_acceleration_from_velocity,
)
try:
    from stride_segmentation import (
        segment_gait_cycles,
        GaitSegmentationConfig,
    )
except ImportError:
    from common.stride_segmentation import (
        segment_gait_cycles,
        GaitSegmentationConfig,
    )

# Import local metadata parser
from metadata_parser import (
    get_subject_metadata,
    load_subject_char_xlsx,
    list_all_subjects,
    get_affected_side,
    set_affected_side_map,
)

# Import C3D parser for GRF extraction
from c3d_parser import (
    load_c3d_file,
    load_c3d_events,
    extract_grf_for_stride,
    find_c3d_for_mot,
    EZC3D_AVAILABLE,
)

# Import marker mapping
from marker_mapping import (
    PIG_TO_RAJAGOPAL,
    IK_MARKER_WEIGHTS_PIG,
    STROKEPIG_SEGMENT_MARKER_PAIRS,
)

# Import C3D→OpenSim conversion
from c3d_to_opensim import (
    c3d_markers_to_trc,
    c3d_forces_to_grf_mot,
    stride_c3d_to_grf_mot,
    find_static_c3d,
    static_c3d_to_trc,
    slice_trc,
    slice_grf_mot,
)

# Conditional imports for pipeline mode
try:
    from common.opensim_pipeline import OpenSimPipeline, PipelineConfig
    from common.opensim_ik import IKConfig
    from common.opensim_inverse_dynamics import InverseDynamicsConfig, OPENSIM_AVAILABLE
    from common.opensim_scaling import ScalingConfig
except ImportError:
    OPENSIM_AVAILABLE = False

# Configuration
NUM_POINTS = 150  # Target points per gait cycle (standard format)
DEG2RAD = np.pi / 180.0
SAMPLE_RATE = 100  # Hz
GRF_CONTACT_BW_THRESHOLD = 0.05

# Task mapping for StrokePiG (all trials are level walking)
# Clinical population is carried in subject metadata.
TASK_MAPPING = {
    'BWA': ('level_walking', 'level_walking'),  # (task, task_id base)
}

# Pipeline mode globals
RUN_FULL_PIPELINE = False
_opensim_pipeline: Optional['OpenSimPipeline'] = None
USE_PIPELINE_KINEMATICS = False
WALKING_MARKER_ROTATION_MODE = "all_markers"


def load_mot_file(mot_path: Path) -> Optional[pd.DataFrame]:
    """
    Load an OpenSim .mot file containing joint angle data.

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


def interpolate_to_phase(data, num_points=NUM_POINTS, source_time=None):
    """Resample observed samples without bridging missing measurements."""
    values = np.asarray(data, dtype=float)
    if len(values) < 2:
        return np.full(num_points, np.nan)
    times = np.arange(len(values)) if source_time is None else np.asarray(source_time)
    if len(times) != len(values) or not np.isfinite(times).all() or not (np.diff(times) > 0).all():
        raise ValueError('Signal samples must match an increasing source clock')
    return np.interp(np.linspace(times[0], times[-1], num_points), times,
                     np.where(np.isfinite(values), values, np.nan))


def circular_phase_shift(data: np.ndarray, shift_percent: float = 50.0) -> np.ndarray:
    """
    Circularly shift phase-normalized data by a percentage of the gait cycle.

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
    return 1.2  # Default estimate for stroke gait


def get_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """
    Create mapping from expected column names to actual column names in the data.

    Args:
        df: DataFrame from a .mot file

    Returns:
        Dictionary mapping standard names to actual column names in df
    """
    columns = set(df.columns)
    mapping = {}

    if 'time' in columns:
        mapping['time'] = 'time'

    for col in ['pelvis_tilt', 'pelvis_list', 'pelvis_rotation',
                'pelvis_tx', 'pelvis_ty', 'pelvis_tz']:
        if col in columns:
            mapping[col] = col

    for side in ['r', 'l']:
        suffix = f'_{side}'

        for joint in ['hip_flexion', 'hip_adduction', 'hip_rotation']:
            col_name = f'{joint}{suffix}'
            if col_name in columns:
                mapping[col_name] = col_name

        knee_col = f'knee_angle{suffix}'
        if knee_col in columns:
            mapping[knee_col] = knee_col

        ankle_col = f'ankle_angle{suffix}'
        if ankle_col in columns:
            mapping[ankle_col] = ankle_col

    return mapping


def detect_heel_strikes_from_kinematics(
    df: pd.DataFrame,
    side: str = 'l',
    sample_rate: float = SAMPLE_RATE
) -> List[int]:
    """
    Detect heel strikes from kinematic data when GRF is not available.

    Uses ankle dorsiflexion peaks (local maxima) as proxy for heel strikes.

    Args:
        df: DataFrame with joint angle columns
        side: 'l' or 'r' for which leg
        sample_rate: Sampling rate in Hz

    Returns:
        List of heel strike indices
    """
    ankle_col = f'ankle_angle_{side}'
    if ankle_col not in df.columns:
        return []

    ankle = df[ankle_col].values

    # Smooth the signal
    from scipy.ndimage import uniform_filter1d
    ankle_smooth = uniform_filter1d(ankle, size=5)

    # Find peaks (local maxima in dorsiflexion)
    from scipy.signal import find_peaks
    min_distance = int(0.5 * sample_rate)  # At least 0.5s between strikes
    peaks, _ = find_peaks(ankle_smooth, distance=min_distance)

    return peaks.tolist()


def segment_trial_into_strides(df, affected_side='l', sample_rate=SAMPLE_RATE, source_events=None):
    """Use annotated foot strikes when available; label inferred boundaries."""
    side = {'l':'left','r':'right'}[affected_side]
    annotated = [e['time_s'] for e in (source_events or [])
                 if e['label'].lower() == 'foot strike' and e['side'] == side]
    ledger=[]
    if annotated:
        df.attrs['phase_boundary_method']='source_c3d_foot_strike_annotations'
        if 'time' not in df:
            raise ValueError('Source event alignment requires the original IK timestamps')
        clock=df.time.to_numpy(dtype=float)
        if not np.isfinite(clock).all() or not (np.diff(clock)>0).all():
            raise ValueError('IK timestamps must be finite and strictly increasing')
        events=sorted(set(annotated));strides=[]
        for start,end in zip(events[:-1],events[1:]):
            a=int(np.argmin(abs(clock-start)));b=int(np.argmin(abs(clock-end)))
            accepted=abs(clock[a]-start)<=1e-4 and abs(clock[b]-end)<=1e-4 and b-a+1>=10
            ledger.append({'start_time_s':start,'end_time_s':end,'accepted':bool(accepted),
                           'reason':'source_annotations' if accepted else 'events_not_on_available_ik_clock'})
            if accepted:strides.append((a,b))
    else:
        df.attrs['phase_boundary_method']='inferred_ankle_dorsiflexion_peaks_unverified'
        strikes=detect_heel_strikes_from_kinematics(df,affected_side,sample_rate)
        strides=[]
        for a,b in zip(strikes[:-1],strikes[1:]):
            duration=float(df.time.iloc[b]-df.time.iloc[a]) if 'time' in df else np.nan
            accepted=np.isfinite(duration) and .6<=duration<=4.
            ledger.append({'start_sample':int(a),'end_sample':int(b),'accepted':bool(accepted),
                           'reason':'inferred_boundary' if accepted else 'inferred_duration_outside_0.6_to_4_seconds'})
            if accepted:strides.append((a,b))
    df.attrs['segmentation_candidates']=ledger
    return strides


def c3d_index_for_time(c3d_data, time_s):
    clock=np.asarray(c3d_data['time'])
    index=int(np.argmin(abs(clock-time_s)))
    if not np.isfinite(time_s) or abs(clock[index]-time_s)>1e-4:
        raise ValueError('C3D and IK timestamps do not align')
    return index


def reference_side_for_subject(subject_metadata: Dict[str, Any]) -> str:
    """Choose an anatomical reference without imputing clinical laterality."""
    side = str(subject_metadata.get('affected_side', 'unknown')).lower()
    return side if side in ('l', 'r') else 'l'


def process_stride(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    affected_side: str,
    subject_mass_kg: float,
    stride_num: int,
) -> Optional[Dict[str, np.ndarray]]:
    """
    Process a single stride segment into phase-normalized data.

    Args:
        df: Full trial DataFrame
        start_idx: Start index of stride
        end_idx: End index of stride
        affected_side: 'l' or 'r' for affected leg (ipsi)
        subject_mass_kg: Subject body mass
        stride_num: Stride number for identification

    Returns:
        Dictionary with phase-normalized kinematics, or None if invalid
    """
    if start_idx < 0 or end_idx >= len(df) or end_idx <= start_idx:
        return None
    if affected_side not in {'l', 'r'}:
        raise ValueError('Anatomical reference side must be l or r')
    # Extract both observed boundary samples.
    stride_df = df.iloc[start_idx:end_idx + 1].copy()
    n_samples = len(stride_df)

    if n_samples < 10:
        return None

    # Determine ipsi/contra sides
    ipsi = affected_side.lower()
    contra = 'r' if ipsi == 'l' else 'l'

    if 'time' not in stride_df:
        return None
    source_time = stride_df.time.to_numpy(dtype=float)
    if not np.isfinite(source_time).all() or not (np.diff(source_time) > 0).all():
        return None
    stride_duration_s = source_time[-1] - source_time[0]
    def resample(values):
        return interpolate_to_phase(values, source_time=source_time)

    def get_col(name: str) -> np.ndarray:
        if name in stride_df.columns:
            return stride_df[name].values
        return np.full(n_samples, np.nan)

    # Extract and phase-normalize kinematics
    # Hip flexion (no sign change)
    hip_ipsi_deg = get_col(f'hip_flexion_{ipsi}')
    hip_contra_deg = get_col(f'hip_flexion_{contra}')
    hip_ipsi_rad = resample(hip_ipsi_deg * DEG2RAD)
    hip_contra_rad = resample(hip_contra_deg * DEG2RAD)

    # Knee angle (NO negation: this model uses flexion-positive convention,
    # with knee_angle range [0, 2.09] rad i.e. 0 at full extension)
    knee_ipsi_deg = get_col(f'knee_angle_{ipsi}')
    knee_contra_deg = get_col(f'knee_angle_{contra}')
    knee_ipsi_rad = resample(knee_ipsi_deg * DEG2RAD)
    knee_contra_rad = resample(knee_contra_deg * DEG2RAD)

    # Ankle dorsiflexion (no sign change)
    ankle_ipsi_deg = get_col(f'ankle_angle_{ipsi}')
    ankle_contra_deg = get_col(f'ankle_angle_{contra}')
    ankle_ipsi_rad = resample(ankle_ipsi_deg * DEG2RAD)
    ankle_contra_rad = resample(ankle_contra_deg * DEG2RAD)

    # Pelvis tilt
    pelvis_tilt_deg = get_col('pelvis_tilt')
    pelvis_tilt_rad = resample(pelvis_tilt_deg * DEG2RAD)

    # Compute segment angles from kinematic chain
    thigh_ipsi_rad = pelvis_tilt_rad + hip_ipsi_rad
    thigh_contra_rad = pelvis_tilt_rad + hip_contra_rad
    shank_ipsi_rad = thigh_ipsi_rad - knee_ipsi_rad
    shank_contra_rad = thigh_contra_rad - knee_contra_rad
    foot_ipsi_rad = shank_ipsi_rad + ankle_ipsi_rad
    foot_contra_rad = shank_contra_rad + ankle_contra_rad

    # Compute velocities (no discontinuity since we segment at heel strike)
    hip_vel_ipsi = compute_velocity_from_shifted_angle(
        hip_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    hip_vel_contra = compute_velocity_from_shifted_angle(
        hip_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    knee_vel_ipsi = compute_velocity_from_shifted_angle(
        knee_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    knee_vel_contra = compute_velocity_from_shifted_angle(
        knee_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    ankle_vel_ipsi = compute_velocity_from_shifted_angle(
        ankle_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    ankle_vel_contra = compute_velocity_from_shifted_angle(
        ankle_contra_rad, stride_duration_s, discontinuity_idx=None
    )

    # Segment velocities
    pelvis_vel = compute_velocity_from_shifted_angle(
        pelvis_tilt_rad, stride_duration_s, discontinuity_idx=None
    )
    thigh_vel_ipsi = compute_velocity_from_shifted_angle(
        thigh_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    thigh_vel_contra = compute_velocity_from_shifted_angle(
        thigh_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    shank_vel_ipsi = compute_velocity_from_shifted_angle(
        shank_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    shank_vel_contra = compute_velocity_from_shifted_angle(
        shank_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    foot_vel_ipsi = compute_velocity_from_shifted_angle(
        foot_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    foot_vel_contra = compute_velocity_from_shifted_angle(
        foot_contra_rad, stride_duration_s, discontinuity_idx=None
    )

    # Compute accelerations
    hip_acc_ipsi = compute_acceleration_from_velocity(
        hip_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    hip_acc_contra = compute_acceleration_from_velocity(
        hip_vel_contra, stride_duration_s, discontinuity_idx=None
    )
    knee_acc_ipsi = compute_acceleration_from_velocity(
        knee_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    knee_acc_contra = compute_acceleration_from_velocity(
        knee_vel_contra, stride_duration_s, discontinuity_idx=None
    )
    ankle_acc_ipsi = compute_acceleration_from_velocity(
        ankle_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    ankle_acc_contra = compute_acceleration_from_velocity(
        ankle_vel_contra, stride_duration_s, discontinuity_idx=None
    )

    return {
        'stride_duration_s': stride_duration_s,
        'phase_boundary_method': df.attrs.get('phase_boundary_method', 'unverified_supplied_indices'),
        'segmentation_candidates': df.attrs.get('segmentation_candidates', []),
        'ipsi_side': ipsi,
        'source_start_sample': start_idx,
        'source_end_sample': end_idx,
        'source_start_time_s': float(stride_df['time'].iloc[0]) if 'time' in stride_df else np.nan,
        'source_end_time_s': float(stride_df['time'].iloc[-1]) if 'time' in stride_df else np.nan,
        # Joint angles
        'hip_flexion_angle_ipsi_rad': hip_ipsi_rad,
        'hip_flexion_angle_contra_rad': hip_contra_rad,
        'knee_flexion_angle_ipsi_rad': knee_ipsi_rad,
        'knee_flexion_angle_contra_rad': knee_contra_rad,
        'ankle_dorsiflexion_angle_ipsi_rad': ankle_ipsi_rad,
        'ankle_dorsiflexion_angle_contra_rad': ankle_contra_rad,
        # Joint velocities
        'hip_flexion_velocity_ipsi_rad_s': hip_vel_ipsi,
        'hip_flexion_velocity_contra_rad_s': hip_vel_contra,
        'knee_flexion_velocity_ipsi_rad_s': knee_vel_ipsi,
        'knee_flexion_velocity_contra_rad_s': knee_vel_contra,
        'ankle_dorsiflexion_velocity_ipsi_rad_s': ankle_vel_ipsi,
        'ankle_dorsiflexion_velocity_contra_rad_s': ankle_vel_contra,
        # Joint accelerations
        'hip_flexion_acceleration_ipsi_rad_s2': hip_acc_ipsi,
        'hip_flexion_acceleration_contra_rad_s2': hip_acc_contra,
        'knee_flexion_acceleration_ipsi_rad_s2': knee_acc_ipsi,
        'knee_flexion_acceleration_contra_rad_s2': knee_acc_contra,
        'ankle_dorsiflexion_acceleration_ipsi_rad_s2': ankle_acc_ipsi,
        'ankle_dorsiflexion_acceleration_contra_rad_s2': ankle_acc_contra,
        # Segment angles
        'pelvis_sagittal_angle_rad': pelvis_tilt_rad,
        'thigh_sagittal_angle_ipsi_rad': thigh_ipsi_rad,
        'thigh_sagittal_angle_contra_rad': thigh_contra_rad,
        'shank_sagittal_angle_ipsi_rad': shank_ipsi_rad,
        'shank_sagittal_angle_contra_rad': shank_contra_rad,
        'foot_sagittal_angle_ipsi_rad': foot_ipsi_rad,
        'foot_sagittal_angle_contra_rad': foot_contra_rad,
        # Segment velocities
        'pelvis_sagittal_velocity_rad_s': pelvis_vel,
        'thigh_sagittal_velocity_ipsi_rad_s': thigh_vel_ipsi,
        'thigh_sagittal_velocity_contra_rad_s': thigh_vel_contra,
        'shank_sagittal_velocity_ipsi_rad_s': shank_vel_ipsi,
        'shank_sagittal_velocity_contra_rad_s': shank_vel_contra,
        'foot_sagittal_velocity_ipsi_rad_s': foot_vel_ipsi,
        'foot_sagittal_velocity_contra_rad_s': foot_vel_contra,
    }


def process_trial_with_pipeline(
    mot_path: Path,
    subject_id: str,
    subject_metadata: Dict[str, Any],
    step_offset: int = 0,
) -> Tuple[List[pd.DataFrame], int]:
    """
    Process a single trial using the full OpenSim pipeline (Scale → IK → ID).

    Uses pre-computed IK for kinematics by default, with optional override from
    pipeline IK outputs.

    Args:
        mot_path: Path to the IK .mot file
        subject_id: Subject identifier
        subject_metadata: Subject metadata dict
        step_offset: Starting step number

    Returns:
        Tuple of (list of stride DataFrames, next step number)
    """
    global _opensim_pipeline

    df = load_mot_file(mot_path)
    if df is None or len(df) < 50:
        return [], step_offset

    affected_side = reference_side_for_subject(subject_metadata)

    # Segment into strides using kinematic detection (same as default mode)
    strides = segment_trial_into_strides(
        df, affected_side, source_events=load_c3d_events(find_c3d_for_mot(mot_path)))
    if not strides:
        return [], step_offset

    # Load corresponding C3D
    c3d_path = find_c3d_for_mot(mot_path)
    if c3d_path is None:
        # Fall back to default processing (no pipeline without C3D)
        return _process_strides_default(
            df, strides, mot_path, subject_id, subject_metadata, step_offset
        )

    c3d_data = load_c3d_file(c3d_path)
    if c3d_data is None:
        return _process_strides_default(
            df, strides, mot_path, subject_id, subject_metadata, step_offset
        )

    # Get or create static TRC for this subject
    subject_path = mot_path.parent
    cache_dir = _opensim_pipeline.cache_dir if _opensim_pipeline else subject_path
    static_trc_path = _get_or_create_static_trc(subject_path, cache_dir)

    if static_trc_path is None:
        print(f"  Warning: No static C3D found for {subject_id}, skipping pipeline")
        return _process_strides_default(
            df, strides, mot_path, subject_id, subject_metadata, step_offset
        )

    # Write full-trial TRC from C3D (markers don't have plate assignment issues)
    trial_name = mot_path.stem.replace('_ik', '')
    trial_cache = cache_dir / "trials" / subject_id
    trial_cache.mkdir(parents=True, exist_ok=True)

    full_trc_path = c3d_markers_to_trc(
        c3d_data,
        trial_cache / f"{trial_name}.trc",
        walking_rotation_mode=WALKING_MARKER_ROTATION_MODE,
    )

    # Process each stride
    stride_dfs = []
    step_num = step_offset
    body_weight_N = subject_metadata['mass_kg'] * 9.81

    for start_idx, end_idx in strides:
        # Process kinematics from pre-computed IK (unchanged)
        result = process_stride(
            df, start_idx, end_idx,
            affected_side,
            subject_metadata['mass_kg'],
            step_num,
        )
        if result is None:
            continue

        stride_duration_s = result['stride_duration_s']
        ipsi_side = result['ipsi_side']

        # Extract GRF from C3D (same as default mode)
        grf_data = None
        if c3d_data is not None:
            try:
                grf_data = extract_grf_for_stride(
                    forces_df=c3d_data['forces'],
                    markers_df=c3d_data['markers'],
                    start_idx=c3d_index_for_time(c3d_data, result['source_start_time_s']),
                    end_idx=c3d_index_for_time(c3d_data, result['source_end_time_s']) + 1,
                    ipsi_side=ipsi_side,
                    body_mass_kg=subject_metadata['mass_kg'],
                    num_points=NUM_POINTS,
                )
            except Exception:
                pass

        # Run pipeline for moments (if GRF available)
        moment_data = None
        if _opensim_pipeline is not None and full_trc_path is not None:
            stride_key = f"{subject_id}_{trial_name}_{step_num:03d}"
            stride_cache = cache_dir / "strides" / subject_id
            stride_cache.mkdir(parents=True, exist_ok=True)

            # Slice stride TRC from full trial
            stride_trc = slice_trc(
                full_trc_path,
                stride_cache / f"{stride_key}.trc",
                start_idx, end_idx,
            )
            # Write stride GRF MOT directly from C3D (per-stride foot assignment)
            stride_grf = stride_c3d_to_grf_mot(
                c3d_data,
                stride_cache / f"{stride_key}_grf.mot",
                start_idx, end_idx,
            )

            if stride_trc is not None:
                try:
                    pipeline_result = _opensim_pipeline.process_stride(
                        subject_id=subject_id,
                        static_trc_path=static_trc_path,
                        stride_trc_path=stride_trc,
                        subject_mass_kg=subject_metadata['mass_kg'],
                        ipsi_side=ipsi_side,
                        grf_mot_path=stride_grf,
                        subject_height_m=subject_metadata.get('height_m'),
                        stride_key=stride_key,
                        phase_normalize=True,
                    )

                    if pipeline_result.success and pipeline_result.moments_phase:
                        moment_data = pipeline_result.moments_phase
                        if USE_PIPELINE_KINEMATICS and pipeline_result.kinematics_phase:
                            result = _override_result_with_pipeline_kinematics(
                                base_result=result,
                                pipeline_kinematics=pipeline_result.kinematics_phase,
                            )
                    elif pipeline_result.error_message:
                        print(f"  Pipeline stride {step_num}: {pipeline_result.error_message}")
                except Exception as e:
                    print(f"  Pipeline error stride {step_num}: {e}")

        # Build stride DataFrame (same structure as default mode)
        stride_df = _build_stride_dataframe(
            result, grf_data, moment_data,
            subject_id, subject_metadata,
            ipsi_side, stride_duration_s, step_num,
            f"sp50:{subject_id}/{mot_path.name}",
        )
        stride_dfs.append(stride_df)
        step_num += 1

    return stride_dfs, step_num


def _get_or_create_static_trc(subject_path: Path, cache_dir: Path) -> Optional[Path]:
    """Get or create static TRC from calibration C3D (cached per subject)."""
    subject_id = subject_path.name
    cached = cache_dir / "static" / f"{subject_id}_static.trc"
    if cached.exists():
        return cached

    static_c3d = find_static_c3d(subject_path)
    if static_c3d is None:
        return None

    cached.parent.mkdir(parents=True, exist_ok=True)
    return static_c3d_to_trc(static_c3d, cached)


def _override_result_with_pipeline_kinematics(
    *,
    base_result: Dict[str, np.ndarray],
    pipeline_kinematics: Dict[str, np.ndarray],
) -> Dict[str, np.ndarray]:
    """Rebuild stride result using pipeline IK phase angles where available."""
    stride_duration_s = float(base_result['stride_duration_s'])
    ipsi_side = str(base_result['ipsi_side'])

    def _select_angle(key: str) -> np.ndarray:
        if key in pipeline_kinematics:
            return np.asarray(pipeline_kinematics[key], dtype=float)
        return np.asarray(base_result[key], dtype=float)

    hip_ipsi_rad = _select_angle('hip_flexion_angle_ipsi_rad')
    hip_contra_rad = _select_angle('hip_flexion_angle_contra_rad')
    knee_ipsi_rad = _select_angle('knee_flexion_angle_ipsi_rad')
    knee_contra_rad = _select_angle('knee_flexion_angle_contra_rad')
    ankle_ipsi_rad = _select_angle('ankle_dorsiflexion_angle_ipsi_rad')
    ankle_contra_rad = _select_angle('ankle_dorsiflexion_angle_contra_rad')
    pelvis_tilt_rad = _select_angle('pelvis_sagittal_angle_rad')

    # Compute segment angles from kinematic chain
    thigh_ipsi_rad = pelvis_tilt_rad + hip_ipsi_rad
    thigh_contra_rad = pelvis_tilt_rad + hip_contra_rad
    shank_ipsi_rad = thigh_ipsi_rad - knee_ipsi_rad
    shank_contra_rad = thigh_contra_rad - knee_contra_rad
    foot_ipsi_rad = shank_ipsi_rad + ankle_ipsi_rad
    foot_contra_rad = shank_contra_rad + ankle_contra_rad

    # Joint velocities
    hip_vel_ipsi = compute_velocity_from_shifted_angle(
        hip_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    hip_vel_contra = compute_velocity_from_shifted_angle(
        hip_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    knee_vel_ipsi = compute_velocity_from_shifted_angle(
        knee_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    knee_vel_contra = compute_velocity_from_shifted_angle(
        knee_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    ankle_vel_ipsi = compute_velocity_from_shifted_angle(
        ankle_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    ankle_vel_contra = compute_velocity_from_shifted_angle(
        ankle_contra_rad, stride_duration_s, discontinuity_idx=None
    )

    # Segment velocities
    pelvis_vel = compute_velocity_from_shifted_angle(
        pelvis_tilt_rad, stride_duration_s, discontinuity_idx=None
    )
    thigh_vel_ipsi = compute_velocity_from_shifted_angle(
        thigh_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    thigh_vel_contra = compute_velocity_from_shifted_angle(
        thigh_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    shank_vel_ipsi = compute_velocity_from_shifted_angle(
        shank_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    shank_vel_contra = compute_velocity_from_shifted_angle(
        shank_contra_rad, stride_duration_s, discontinuity_idx=None
    )
    foot_vel_ipsi = compute_velocity_from_shifted_angle(
        foot_ipsi_rad, stride_duration_s, discontinuity_idx=None
    )
    foot_vel_contra = compute_velocity_from_shifted_angle(
        foot_contra_rad, stride_duration_s, discontinuity_idx=None
    )

    # Joint accelerations
    hip_acc_ipsi = compute_acceleration_from_velocity(
        hip_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    hip_acc_contra = compute_acceleration_from_velocity(
        hip_vel_contra, stride_duration_s, discontinuity_idx=None
    )
    knee_acc_ipsi = compute_acceleration_from_velocity(
        knee_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    knee_acc_contra = compute_acceleration_from_velocity(
        knee_vel_contra, stride_duration_s, discontinuity_idx=None
    )
    ankle_acc_ipsi = compute_acceleration_from_velocity(
        ankle_vel_ipsi, stride_duration_s, discontinuity_idx=None
    )
    ankle_acc_contra = compute_acceleration_from_velocity(
        ankle_vel_contra, stride_duration_s, discontinuity_idx=None
    )

    return {
        **base_result,  # Preserve source intervals when pipeline kinematics replace IK.
        'stride_duration_s': stride_duration_s,
        'ipsi_side': ipsi_side,
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
        'pelvis_sagittal_angle_rad': pelvis_tilt_rad,
        'thigh_sagittal_angle_ipsi_rad': thigh_ipsi_rad,
        'thigh_sagittal_angle_contra_rad': thigh_contra_rad,
        'shank_sagittal_angle_ipsi_rad': shank_ipsi_rad,
        'shank_sagittal_angle_contra_rad': shank_contra_rad,
        'foot_sagittal_angle_ipsi_rad': foot_ipsi_rad,
        'foot_sagittal_angle_contra_rad': foot_contra_rad,
        'pelvis_sagittal_velocity_rad_s': pelvis_vel,
        'thigh_sagittal_velocity_ipsi_rad_s': thigh_vel_ipsi,
        'thigh_sagittal_velocity_contra_rad_s': thigh_vel_contra,
        'shank_sagittal_velocity_ipsi_rad_s': shank_vel_ipsi,
        'shank_sagittal_velocity_contra_rad_s': shank_vel_contra,
        'foot_sagittal_velocity_ipsi_rad_s': foot_vel_ipsi,
        'foot_sagittal_velocity_contra_rad_s': foot_vel_contra,
    }


def _process_strides_default(
    df: pd.DataFrame,
    strides: List[Tuple[int, int]],
    mot_path: Path,
    subject_id: str,
    subject_metadata: Dict[str, Any],
    step_offset: int,
) -> Tuple[List[pd.DataFrame], int]:
    """Fallback: process strides without pipeline (NaN moments)."""
    affected_side = reference_side_for_subject(subject_metadata)

    c3d_data = None
    if EZC3D_AVAILABLE:
        c3d_path = find_c3d_for_mot(mot_path)
        if c3d_path is not None:
            c3d_data = load_c3d_file(c3d_path)

    stride_dfs = []
    step_num = step_offset

    for start_idx, end_idx in strides:
        result = process_stride(
            df, start_idx, end_idx,
            affected_side,
            subject_metadata['mass_kg'],
            step_num,
        )
        if result is None:
            continue

        ipsi_side = result['ipsi_side']
        stride_duration_s = result['stride_duration_s']

        grf_data = None
        if c3d_data is not None:
            try:
                grf_data = extract_grf_for_stride(
                    forces_df=c3d_data['forces'],
                    markers_df=c3d_data['markers'],
                    start_idx=c3d_index_for_time(c3d_data, result['source_start_time_s']),
                    end_idx=c3d_index_for_time(c3d_data, result['source_end_time_s']) + 1,
                    ipsi_side=ipsi_side,
                    body_mass_kg=subject_metadata['mass_kg'],
                    num_points=NUM_POINTS,
                )
            except Exception:
                pass

        stride_df = _build_stride_dataframe(
            result, grf_data, None,
            subject_id, subject_metadata,
            ipsi_side, stride_duration_s, step_num,
            f"sp50:{subject_id}/{mot_path.name}",
        )
        stride_dfs.append(stride_df)
        step_num += 1

    return stride_dfs, step_num


def _build_stride_dataframe(
    result: Dict[str, np.ndarray],
    grf_data: Optional[Dict[str, np.ndarray]],
    moment_data: Optional[Dict[str, np.ndarray]],
    subject_id: str,
    subject_metadata: Dict[str, Any],
    ipsi_side: str,
    stride_duration_s: float,
    step_num: int,
    source_recording_id: str,
) -> pd.DataFrame:
    """Build a single stride DataFrame from processed results."""
    phase = np.linspace(0, 100, NUM_POINTS)
    phase_dot = np.full(NUM_POINTS, 100.0 / stride_duration_s)
    nan_array = np.full(NUM_POINTS, np.nan)

    def _to_array(values: Optional[np.ndarray]) -> np.ndarray:
        if values is None:
            return nan_array.copy()
        arr = np.asarray(values, dtype=float)
        if arr.shape[0] != NUM_POINTS:
            return nan_array.copy()
        return arr

    def _has_side_contact(side: str) -> bool:
        if grf_data is None:
            return False
        vertical_bw = grf_data.get(f'grf_vertical_{side}_BW')
        if vertical_bw is None:
            return False
        arr = np.asarray(vertical_bw, dtype=float)
        finite = np.isfinite(arr)
        if not np.any(finite):
            return False
        return bool(np.nanmax(np.abs(arr[finite])) >= GRF_CONTACT_BW_THRESHOLD)

    id_has_ipsi_grf = _has_side_contact('ipsi')
    id_has_contra_grf = _has_side_contact('contra')
    id_has_any_grf = id_has_ipsi_grf or id_has_contra_grf
    id_moments_from_pipeline = moment_data is not None
    id_is_bilateral_valid = id_moments_from_pipeline and id_has_ipsi_grf and id_has_contra_grf

    clinical_side = str(subject_metadata.get('affected_side', 'unknown')).lower()
    clinical_side = {'l': 'left', 'r': 'right'}.get(clinical_side, 'unknown')
    reference_side = {'l': 'left', 'r': 'right'}[ipsi_side]
    task_info_str = json.dumps({
        'leg': ipsi_side, 'affected_side': clinical_side,
        'reference_side': reference_side,
        'reference_side_basis': 'affected_side' if clinical_side != 'unknown' else 'anatomical_default',
        'exo_state': 'no_exo',
        'phase_boundary_method': result.get('phase_boundary_method', 'unverified_supplied_indices'),
        'segmentation_candidates': result.get('segmentation_candidates', []),
        'id_has_ipsi_grf': id_has_ipsi_grf,
        'id_has_contra_grf': id_has_contra_grf,
        'id_has_any_grf': id_has_any_grf,
        'id_moments_from_pipeline': id_moments_from_pipeline,
        'id_is_bilateral_valid': id_is_bilateral_valid,
    }, sort_keys=True)
    mass = subject_metadata['mass_kg']
    metadata = {
        'weight_kg': float(mass) if mass is not None and np.isfinite(mass) else None,
        'affected_side': clinical_side, 'population': 'stroke',
    }
    height = subject_metadata.get('height_m')
    if height is not None and np.isfinite(height):
        metadata['height_m'] = float(height)
    subject_metadata_str = json.dumps(metadata, sort_keys=True, allow_nan=False)
    observation_id = (
        f"{source_recording_id}:samples:{result['source_start_sample']}:"
        f"{result['source_end_sample']}:{reference_side}"
    )

    # Moment columns: use pipeline output if available, else NaN
    hip_mom_ipsi = nan_array.copy()
    hip_mom_contra = nan_array.copy()
    knee_mom_ipsi = nan_array.copy()
    knee_mom_contra = nan_array.copy()
    ankle_mom_ipsi = nan_array.copy()
    ankle_mom_contra = nan_array.copy()

    if moment_data is not None:
        hip_mom_ipsi = _to_array(moment_data.get('hip_flexion_moment_ipsi_Nm_kg'))
        hip_mom_contra = _to_array(moment_data.get('hip_flexion_moment_contra_Nm_kg'))
        knee_mom_ipsi = _to_array(moment_data.get('knee_flexion_moment_ipsi_Nm_kg'))
        knee_mom_contra = _to_array(moment_data.get('knee_flexion_moment_contra_Nm_kg'))
        ankle_mom_ipsi = _to_array(moment_data.get('ankle_dorsiflexion_moment_ipsi_Nm_kg'))
        ankle_mom_contra = _to_array(moment_data.get('ankle_dorsiflexion_moment_contra_Nm_kg'))

        if not id_has_ipsi_grf:
            hip_mom_ipsi = nan_array.copy()
            knee_mom_ipsi = nan_array.copy()
            ankle_mom_ipsi = nan_array.copy()
        if not id_has_contra_grf:
            hip_mom_contra = nan_array.copy()
            knee_mom_contra = nan_array.copy()
            ankle_mom_contra = nan_array.copy()

    return pd.DataFrame({
        'subject': f"SP50_{subject_id}",
        'subject_metadata': subject_metadata_str,
        'task': 'level_walking',
        'task_id': 'level_walking',
        'task_info': task_info_str,
        'step': observation_id,
        'source_recording_id': source_recording_id,
        'observation_id': observation_id,
        'observation_type': 'individual_cycle',
        'reference_side': reference_side,
        'affected_side': clinical_side,
        'source_start_time_s': result['source_start_time_s'],
        'source_end_time_s': result['source_end_time_s'],
        'source_start_sample': result['source_start_sample'],
        'source_end_sample': result['source_end_sample'],
        'phase_ipsi': phase,
        'phase_ipsi_dot': phase_dot,

        # Joint angles
        'hip_flexion_angle_ipsi_rad': result['hip_flexion_angle_ipsi_rad'],
        'hip_flexion_angle_contra_rad': result['hip_flexion_angle_contra_rad'],
        'knee_flexion_angle_ipsi_rad': result['knee_flexion_angle_ipsi_rad'],
        'knee_flexion_angle_contra_rad': result['knee_flexion_angle_contra_rad'],
        'ankle_dorsiflexion_angle_ipsi_rad': result['ankle_dorsiflexion_angle_ipsi_rad'],
        'ankle_dorsiflexion_angle_contra_rad': result['ankle_dorsiflexion_angle_contra_rad'],

        # Joint velocities
        'hip_flexion_velocity_ipsi_rad_s': result['hip_flexion_velocity_ipsi_rad_s'],
        'hip_flexion_velocity_contra_rad_s': result['hip_flexion_velocity_contra_rad_s'],
        'knee_flexion_velocity_ipsi_rad_s': result['knee_flexion_velocity_ipsi_rad_s'],
        'knee_flexion_velocity_contra_rad_s': result['knee_flexion_velocity_contra_rad_s'],
        'ankle_dorsiflexion_velocity_ipsi_rad_s': result['ankle_dorsiflexion_velocity_ipsi_rad_s'],
        'ankle_dorsiflexion_velocity_contra_rad_s': result['ankle_dorsiflexion_velocity_contra_rad_s'],

        # Joint accelerations
        'hip_flexion_acceleration_ipsi_rad_s2': result['hip_flexion_acceleration_ipsi_rad_s2'],
        'hip_flexion_acceleration_contra_rad_s2': result['hip_flexion_acceleration_contra_rad_s2'],
        'knee_flexion_acceleration_ipsi_rad_s2': result['knee_flexion_acceleration_ipsi_rad_s2'],
        'knee_flexion_acceleration_contra_rad_s2': result['knee_flexion_acceleration_contra_rad_s2'],
        'ankle_dorsiflexion_acceleration_ipsi_rad_s2': result['ankle_dorsiflexion_acceleration_ipsi_rad_s2'],
        'ankle_dorsiflexion_acceleration_contra_rad_s2': result['ankle_dorsiflexion_acceleration_contra_rad_s2'],

        # Segment angles
        'pelvis_sagittal_angle_rad': result['pelvis_sagittal_angle_rad'],
        'thigh_sagittal_angle_ipsi_rad': result['thigh_sagittal_angle_ipsi_rad'],
        'thigh_sagittal_angle_contra_rad': result['thigh_sagittal_angle_contra_rad'],
        'shank_sagittal_angle_ipsi_rad': result['shank_sagittal_angle_ipsi_rad'],
        'shank_sagittal_angle_contra_rad': result['shank_sagittal_angle_contra_rad'],
        'foot_sagittal_angle_ipsi_rad': result['foot_sagittal_angle_ipsi_rad'],
        'foot_sagittal_angle_contra_rad': result['foot_sagittal_angle_contra_rad'],

        # Segment velocities
        'pelvis_sagittal_velocity_rad_s': result['pelvis_sagittal_velocity_rad_s'],
        'thigh_sagittal_velocity_ipsi_rad_s': result['thigh_sagittal_velocity_ipsi_rad_s'],
        'thigh_sagittal_velocity_contra_rad_s': result['thigh_sagittal_velocity_contra_rad_s'],
        'shank_sagittal_velocity_ipsi_rad_s': result['shank_sagittal_velocity_ipsi_rad_s'],
        'shank_sagittal_velocity_contra_rad_s': result['shank_sagittal_velocity_contra_rad_s'],
        'foot_sagittal_velocity_ipsi_rad_s': result['foot_sagittal_velocity_ipsi_rad_s'],
        'foot_sagittal_velocity_contra_rad_s': result['foot_sagittal_velocity_contra_rad_s'],

        # GRF (from C3D if available, else NaN)
        'grf_vertical_ipsi_N': grf_data['grf_vertical_ipsi_N'] if grf_data else nan_array,
        'grf_vertical_contra_N': grf_data['grf_vertical_contra_N'] if grf_data else nan_array,
        'grf_anterior_ipsi_N': grf_data['grf_anterior_ipsi_N'] if grf_data else nan_array,
        'grf_anterior_contra_N': grf_data['grf_anterior_contra_N'] if grf_data else nan_array,
        'grf_lateral_ipsi_N': grf_data['grf_lateral_ipsi_N'] if grf_data else nan_array,
        'grf_lateral_contra_N': grf_data['grf_lateral_contra_N'] if grf_data else nan_array,
        'grf_vertical_ipsi_BW': grf_data['grf_vertical_ipsi_BW'] if grf_data else nan_array,
        'grf_vertical_contra_BW': grf_data['grf_vertical_contra_BW'] if grf_data else nan_array,
        'grf_anterior_ipsi_BW': grf_data['grf_anterior_ipsi_BW'] if grf_data else nan_array,
        'grf_anterior_contra_BW': grf_data['grf_anterior_contra_BW'] if grf_data else nan_array,
        'grf_lateral_ipsi_BW': grf_data['grf_lateral_ipsi_BW'] if grf_data else nan_array,
        'grf_lateral_contra_BW': grf_data['grf_lateral_contra_BW'] if grf_data else nan_array,

        # COP (from C3D if available, else NaN)
        'cop_anterior_ipsi_m': grf_data['cop_anterior_ipsi_m'] if grf_data else nan_array,
        'cop_lateral_ipsi_m': grf_data['cop_lateral_ipsi_m'] if grf_data else nan_array,
        'cop_anterior_contra_m': grf_data['cop_anterior_contra_m'] if grf_data else nan_array,
        'cop_lateral_contra_m': grf_data['cop_lateral_contra_m'] if grf_data else nan_array,

        # Moments (from pipeline if available, else NaN)
        'hip_flexion_moment_ipsi_Nm_kg': hip_mom_ipsi,
        'hip_flexion_moment_contra_Nm_kg': hip_mom_contra,
        'knee_flexion_moment_ipsi_Nm_kg': knee_mom_ipsi,
        'knee_flexion_moment_contra_Nm_kg': knee_mom_contra,
        'ankle_dorsiflexion_moment_ipsi_Nm_kg': ankle_mom_ipsi,
        'ankle_dorsiflexion_moment_contra_Nm_kg': ankle_mom_contra,
    })


def process_trial_file(
    mot_path: Path,
    subject_id: str,
    subject_metadata: Dict[str, Any],
    step_offset: int = 0,
) -> Tuple[List[pd.DataFrame], int]:
    """
    Process a single trial .mot file into multiple stride DataFrames.

    When RUN_FULL_PIPELINE is True, dispatches to process_trial_with_pipeline()
    to run Scale → IK → ID for joint moments.

    Args:
        mot_path: Path to the IK .mot file
        subject_id: Subject identifier
        subject_metadata: Subject metadata dict
        step_offset: Starting step number

    Returns:
        Tuple of (list of stride DataFrames, next step number)
    """
    if RUN_FULL_PIPELINE:
        return process_trial_with_pipeline(
            mot_path, subject_id, subject_metadata, step_offset
        )

    df = load_mot_file(mot_path)
    if df is None or len(df) < 50:
        return [], step_offset

    # Unknown clinical laterality does not prevent using an anatomical reference.
    affected_side = reference_side_for_subject(subject_metadata)

    # Segment into strides
    strides = segment_trial_into_strides(
        df, affected_side, source_events=load_c3d_events(find_c3d_for_mot(mot_path)))

    if not strides:
        return [], step_offset

    # Try to load corresponding C3D file for GRF data
    c3d_data = None
    if EZC3D_AVAILABLE:
        c3d_path = find_c3d_for_mot(mot_path)
        if c3d_path is not None:
            c3d_data = load_c3d_file(c3d_path)

    # Process each stride
    stride_dfs = []
    step_num = step_offset

    body_weight_N = subject_metadata['mass_kg'] * 9.81

    for start_idx, end_idx in strides:
        result = process_stride(
            df, start_idx, end_idx,
            affected_side,
            subject_metadata['mass_kg'],
            step_num,
        )

        if result is None:
            continue

        stride_duration_s = result['stride_duration_s']
        ipsi_side = result['ipsi_side']

        # Extract GRF from C3D if available
        grf_data = None
        if c3d_data is not None:
            try:
                grf_data = extract_grf_for_stride(
                    forces_df=c3d_data['forces'],
                    markers_df=c3d_data['markers'],
                    start_idx=c3d_index_for_time(c3d_data, result['source_start_time_s']),
                    end_idx=c3d_index_for_time(c3d_data, result['source_end_time_s']) + 1,
                    ipsi_side=ipsi_side,
                    body_mass_kg=subject_metadata['mass_kg'],
                    num_points=NUM_POINTS,
                )
            except Exception as e:
                pass  # Fall back to NaN placeholders

        stride_df = _build_stride_dataframe(
            result=result,
            grf_data=grf_data,
            moment_data=None,
            subject_id=subject_id,
            subject_metadata=subject_metadata,
            ipsi_side=ipsi_side,
            stride_duration_s=stride_duration_s,
            step_num=step_num,
            source_recording_id=f"sp50:{subject_id}/{mot_path.name}",
        )

        stride_dfs.append(stride_df)
        step_num += 1

    return stride_dfs, step_num


def process_subject(
    subject_path: Path,
    dataset_path: Path,
    subject_char_df: Optional[pd.DataFrame] = None,
    test_mode: bool = False,
) -> pd.DataFrame:
    """
    Process all trials for a single subject.

    Args:
        subject_path: Path to subject folder
        dataset_path: Root dataset path
        subject_char_df: Pre-loaded SubjectChar DataFrame
        test_mode: If True, only process first trial

    Returns:
        Combined DataFrame of all strides
    """
    subject_id = subject_path.name

    # Get subject metadata
    metadata = get_subject_metadata(subject_id, dataset_path, subject_char_df)

    all_strides = []
    step_offset = 0

    # Find all IK MOT files
    mot_files = sorted(subject_path.glob("*_ik.mot"))

    if not mot_files:
        print(f"  No IK MOT files found for {subject_id}")
        return pd.DataFrame()

    for mot_file in mot_files:
        # Skip calibration trials
        if 'Cal' in mot_file.name:
            continue

        strides, step_offset = process_trial_file(
            mot_path=mot_file,
            subject_id=subject_id,
            subject_metadata=metadata,
            step_offset=step_offset,
        )

        all_strides.extend(strides)

        if test_mode:
            break

    if all_strides:
        return pd.concat(all_strides, ignore_index=True)
    else:
        return pd.DataFrame()


def explore_data_structure(input_path: Path) -> Dict[str, Any]:
    """
    Explore the dataset structure and report findings.

    Args:
        input_path: Path to the StrokePiG dataset root

    Returns:
        Dictionary with structure information
    """
    info = {
        'subject_count': 0,
        'subjects': [],
        'file_counts': {},
        'sample_columns': [],
        'issues': []
    }

    # Find subject folders
    subject_folders = sorted([d for d in input_path.iterdir()
                             if d.is_dir() and d.name.startswith('TVC')])
    info['subject_count'] = len(subject_folders)
    info['subjects'] = ([f.name for f in subject_folders[:5]] +
                        ['...'] if len(subject_folders) > 5 else
                        [f.name for f in subject_folders])

    if not subject_folders:
        info['issues'].append("No subject folders found (expected TVC03, TVC04, ...)")
        return info

    # Count file types across all subjects
    c3d_count = 0
    trc_count = 0
    mot_count = 0
    mp_count = 0

    for subject_folder in subject_folders:
        c3d_count += len(list(subject_folder.glob("*.c3d")))
        trc_count += len(list(subject_folder.glob("*.trc")))
        mot_count += len(list(subject_folder.glob("*_ik.mot")))
        mp_count += len(list(subject_folder.glob("*.mp")))

    info['file_counts'] = {
        'C3D files': c3d_count,
        'TRC files': trc_count,
        'IK MOT files': mot_count,
        'MP files': mp_count,
    }

    # Examine first subject's first IK file
    first_subject = subject_folders[0]
    mot_files = sorted(first_subject.glob("*_ik.mot"))

    if mot_files:
        sample_df = load_mot_file(mot_files[0])
        if sample_df is not None:
            info['sample_columns'] = list(sample_df.columns)
            info['sample_file'] = str(mot_files[0].relative_to(input_path))
            info['sample_rows'] = len(sample_df)

    return info


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(description='Convert StrokePiG dataset to parquet')
    parser.add_argument('--input', '-i', type=str,
                        default='/mnt/s/locomotion_data/50_StrokePiG',
                        help='Path to StrokePiG dataset folder')
    parser.add_argument('--output', '-o', type=str, default='strokepig_phase.parquet',
                        help='Output parquet filename')
    parser.add_argument('--output-dir', type=str, default='../../../converted_datasets',
                        help='Output directory')
    parser.add_argument('--subjects', '-s', nargs='+', type=str, default=None,
                        help='Specific subjects to process (e.g., TVC03 TVC04)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process only first subject and first trial')
    parser.add_argument('--subject', type=str, default=None,
                        help='Single subject to process (for testing)')
    parser.add_argument('--explore', action='store_true',
                        help='Explore data structure and print report (no conversion)')
    parser.add_argument('--affected-side-file', type=str, default=None,
                        help='Path to CSV file mapping subject IDs to affected side (l/r)')
    parser.add_argument('--run-ik', action='store_true',
                        help='Run full OpenSim pipeline (Scale → IK → ID) for joint moments')
    parser.add_argument('--use-pipeline-kinematics', action='store_true',
                        help='In --run-ik mode, replace pre-computed MOT kinematics with pipeline IK kinematics')
    parser.add_argument('--walking-marker-rotation', type=str, default='all_markers',
                        choices=['all_markers', 'pelvis_only', 'none'],
                        help='Marker rotation strategy for walking TRC generation in --run-ik mode')
    parser.add_argument('--pipeline-cache', type=str, default=None,
                        help='Directory for cached scaled models and IK results')
    parser.add_argument('--opensim-model', type=str, default=None,
                        help='Path to Rajagopal .osim model (default: Gait120 model)')

    args = parser.parse_args()

    # Setup paths
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path not found: {input_path}")
        return

    # Explore mode
    if args.explore:
        print("Exploring data structure...")
        print("=" * 60)
        info = explore_data_structure(input_path)
        print(f"Subject folders found: {info['subject_count']}")
        print(f"Sample subjects: {info['subjects']}")
        print(f"\nFile counts:")
        for ftype, count in info['file_counts'].items():
            print(f"  {ftype}: {count}")
        if info['sample_columns']:
            print(f"\nSample IK file: {info.get('sample_file', 'N/A')}")
            print(f"  Rows: {info.get('sample_rows', 'N/A')}")
            print(f"  Columns ({len(info['sample_columns'])}): {info['sample_columns'][:15]}...")
        if info['issues']:
            print(f"\nIssues: {info['issues']}")
        return

    # Load affected side mapping if provided
    if args.affected_side_file:
        try:
            affected_df = pd.read_csv(args.affected_side_file)
            mapping = dict(zip(affected_df['subject_id'], affected_df['affected_side']))
            set_affected_side_map(mapping)
            print(f"Loaded affected side mapping for {len(mapping)} subjects")
        except Exception as e:
            print(f"Warning: Could not load affected side file: {e}")

    # Load SubjectChar.xlsx if available
    subject_char_path = input_path / 'SubjectChar.xlsx'
    subject_char_df = None
    if subject_char_path.exists():
        try:
            subject_char_df = load_subject_char_xlsx(subject_char_path)
            print(f"Loaded SubjectChar.xlsx with {len(subject_char_df)} subjects")
        except Exception as e:
            print(f"Warning: Could not load SubjectChar.xlsx: {e}")

    # Setup output directory
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).parent / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize OpenSim pipeline if --run-ik
    global RUN_FULL_PIPELINE, _opensim_pipeline
    global USE_PIPELINE_KINEMATICS, WALKING_MARKER_ROTATION_MODE
    if args.run_ik:
        RUN_FULL_PIPELINE = True
        USE_PIPELINE_KINEMATICS = bool(args.use_pipeline_kinematics)
        WALKING_MARKER_ROTATION_MODE = str(args.walking_marker_rotation)
        if OPENSIM_AVAILABLE:
            # Find model path
            if args.opensim_model:
                model_path = Path(args.opensim_model)
            else:
                # Default: use Gait120's Rajagopal model
                model_path = (Path(__file__).parent.parent / 'Gait120' /
                              'rajagopal_gait120.osim')

            if model_path.exists():
                cache_dir = (Path(args.pipeline_cache) if args.pipeline_cache
                             else output_dir / 'opensim_cache')

                pipeline_config = PipelineConfig(
                    scaling=ScalingConfig(preserve_mass_distribution=True),
                    ik=IKConfig(marker_weights=IK_MARKER_WEIGHTS_PIG, accuracy=1e-5),
                    id=InverseDynamicsConfig(lowpass_cutoff_hz=6.0),
                    cache_scaled_models=True,
                    cache_ik_results=True,
                    cache_dir=cache_dir,
                    num_phase_points=NUM_POINTS,
                    rotate_y_90=False,  # Rotation handled in c3d_to_opensim.py
                    marker_map=PIG_TO_RAJAGOPAL,
                    segment_marker_pairs=STROKEPIG_SEGMENT_MARKER_PAIRS,
                )
                _opensim_pipeline = OpenSimPipeline(
                    generic_model_path=model_path,
                    output_dir=cache_dir,
                    config=pipeline_config,
                )
                print("Full pipeline mode: ENABLED (Scale → IK → ID)")
                print(f"  Using model: {model_path.name}")
                print(f"  Cache dir: {cache_dir}")
                print(f"  Walking marker rotation: {WALKING_MARKER_ROTATION_MODE}")
                print(f"  Use pipeline kinematics: {USE_PIPELINE_KINEMATICS}")
            else:
                print(f"Warning: --run-ik requested but model not found: {model_path}")
                print("  Falling back to pre-computed IK (moments will be NaN)")
                RUN_FULL_PIPELINE = False
        else:
            print("Warning: --run-ik requested but OpenSim not available")
            print("  Falling back to pre-computed IK (moments will be NaN)")
            RUN_FULL_PIPELINE = False

    if not RUN_FULL_PIPELINE:
        print("Processing mode: Using pre-computed IK from MOT files")
        print("  Moments: NaN placeholders (use --run-ik for joint moments)")

    # Find subject folders
    subject_folders = sorted([d for d in input_path.iterdir()
                             if d.is_dir() and d.name.startswith('TVC')])

    # Filter subjects
    if args.subject:
        subject_folders = [f for f in subject_folders if f.name == args.subject]
    elif args.subjects:
        subject_folders = [f for f in subject_folders if f.name in args.subjects]

    if args.test:
        subject_folders = subject_folders[:1]
        print(f"Test mode: processing only {subject_folders[0].name if subject_folders else 'none'}")

    print(f"Found {len(subject_folders)} subject folders")

    # Process each subject
    all_data = []

    for subject_path in tqdm(subject_folders, desc="Processing subjects"):
        print(f"\nProcessing {subject_path.name}...")

        subject_data = process_subject(
            subject_path, input_path,
            subject_char_df,
            test_mode=args.test
        )

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

        combined_df.to_parquet(output_path, index=False)
        print("\nDone!")
    else:
        print("No data to save!")


if __name__ == '__main__':
    main()
