"""
Force plate data processing utilities.

Handles loading, resampling, and assigning force plate data to ipsi/contra legs
based on gait phase timing.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ForcePlateConfig:
    """Configuration for force plate data processing."""
    # Column name patterns for force plate data
    fp1_vertical_col: str = 'ground_force1_vy'
    fp2_vertical_col: str = 'ground_force2_vy'
    fp1_ap_col: str = 'ground_force1_vx'  # Anterior-posterior
    fp2_ap_col: str = 'ground_force2_vx'
    fp1_ml_col: str = 'ground_force1_vz'  # Medial-lateral
    fp2_ml_col: str = 'ground_force2_vz'
    fp1_cop_x_col: str = 'ground_force1_px'
    fp2_cop_x_col: str = 'ground_force2_px'
    fp1_cop_y_col: str = 'ground_force1_py'
    fp2_cop_y_col: str = 'ground_force2_py'
    fp1_cop_z_col: str = 'ground_force1_pz'
    fp2_cop_z_col: str = 'ground_force2_pz'
    time_col: str = 'time'

    # Phase boundaries for ipsi/contra assignment
    # In gait data segmented at contra heel strike:
    # - 0-60% phase: contra leg in stance
    # - 40-100% phase: ipsi leg in stance
    contra_phase_start: float = 0.0
    contra_phase_end: float = 40.0  # Definitely contra
    ipsi_phase_start: float = 60.0  # Definitely ipsi
    ipsi_phase_end: float = 100.0

    # Minimum force threshold to consider as contact (N)
    contact_threshold_N: float = 20.0


@dataclass
class ForcePlateData:
    """Processed force plate data with ipsi/contra assignment.

    Uses LocoHub standard naming convention:
    - GRF: grf_<axis>_<side>_<unit> (vertical, anterior, lateral)
    - COP: cop_<axis>_<side>_<unit> (anterior, lateral, vertical)
    """
    grf_vertical_ipsi_N: np.ndarray
    grf_vertical_contra_N: np.ndarray
    grf_anterior_ipsi_N: np.ndarray
    grf_anterior_contra_N: np.ndarray
    grf_lateral_ipsi_N: np.ndarray
    grf_lateral_contra_N: np.ndarray
    cop_anterior_ipsi_m: np.ndarray
    cop_lateral_ipsi_m: np.ndarray
    cop_anterior_contra_m: np.ndarray
    cop_lateral_contra_m: np.ndarray

    def to_dict(self) -> Dict[str, np.ndarray]:
        """Convert to dictionary for DataFrame construction."""
        return {
            'grf_vertical_ipsi_N': self.grf_vertical_ipsi_N,
            'grf_vertical_contra_N': self.grf_vertical_contra_N,
            'grf_anterior_ipsi_N': self.grf_anterior_ipsi_N,
            'grf_anterior_contra_N': self.grf_anterior_contra_N,
            'grf_lateral_ipsi_N': self.grf_lateral_ipsi_N,
            'grf_lateral_contra_N': self.grf_lateral_contra_N,
            'cop_anterior_ipsi_m': self.cop_anterior_ipsi_m,
            'cop_lateral_ipsi_m': self.cop_lateral_ipsi_m,
            'cop_anterior_contra_m': self.cop_anterior_contra_m,
            'cop_lateral_contra_m': self.cop_lateral_contra_m,
        }


def resample_to_phase(
    data: np.ndarray,
    phase_original: np.ndarray,
    num_points: int = 150,
    fill_value: float = 0.0
) -> np.ndarray:
    """
    Resample time-series data to fixed phase points.

    Args:
        data: Original data array
        phase_original: Phase values (0-100) for each data point
        num_points: Number of output phase points
        fill_value: Value to use outside interpolation range

    Returns:
        Resampled data array of length num_points
    """
    if len(data) < 2 or len(phase_original) < 2:
        return np.full(num_points, fill_value)

    phase_target = np.linspace(0, 100, num_points)

    try:
        interp_func = interp1d(
            phase_original, data,
            kind='linear',
            bounds_error=False,
            fill_value=fill_value
        )
        return interp_func(phase_target)
    except Exception:
        return np.full(num_points, fill_value)


def assign_force_plates_to_legs(
    fp1_vertical: np.ndarray,
    fp2_vertical: np.ndarray,
    phase: np.ndarray,
    config: ForcePlateConfig = None
) -> Tuple[str, str]:
    """
    Determine which force plate corresponds to ipsi vs contra leg.

    Uses the timing of force application during the gait cycle:
    - Force in early phase (0-40%) indicates contra leg contact
    - Force in late phase (60-100%) indicates ipsi leg contact

    Handles single-leg force plate contact (common in per-step data files).

    Args:
        fp1_vertical: Vertical GRF from force plate 1
        fp2_vertical: Vertical GRF from force plate 2
        phase: Phase values (0-100) for each data point
        config: Force plate configuration

    Returns:
        Tuple of (fp1_assignment, fp2_assignment) where each is 'ipsi', 'contra', or 'none'
    """
    if config is None:
        config = ForcePlateConfig()

    # Create phase masks
    early_mask = phase < config.contra_phase_end
    late_mask = phase > config.ipsi_phase_start

    # Calculate mean force in early and late phases for each plate
    fp1_early = np.mean(np.abs(fp1_vertical[early_mask])) if early_mask.any() else 0
    fp2_early = np.mean(np.abs(fp2_vertical[early_mask])) if early_mask.any() else 0
    fp1_late = np.mean(np.abs(fp1_vertical[late_mask])) if late_mask.any() else 0
    fp2_late = np.mean(np.abs(fp2_vertical[late_mask])) if late_mask.any() else 0

    # Minimum force threshold to consider as significant contact
    min_force = config.contact_threshold_N

    # Check if each force plate has significant force in each phase
    fp1_has_early = fp1_early > min_force
    fp2_has_early = fp2_early > min_force
    fp1_has_late = fp1_late > min_force
    fp2_has_late = fp2_late > min_force

    # Case 1: Both plates have force - use dominance comparison
    if fp1_early > fp2_early and fp2_late > fp1_late:
        return ('contra', 'ipsi')
    elif fp2_early > fp1_early and fp1_late > fp2_late:
        return ('ipsi', 'contra')

    # Case 2: Only one plate has force - assign based on phase timing
    # Late phase force = ipsi leg contact
    if fp2_has_late and not fp1_has_late and not fp1_has_early:
        return ('none', 'ipsi')
    elif fp1_has_late and not fp2_has_late and not fp2_has_early:
        return ('ipsi', 'none')

    # Early phase force = contra leg contact
    if fp1_has_early and not fp2_has_early and not fp2_has_late:
        return ('contra', 'none')
    elif fp2_has_early and not fp1_has_early and not fp1_has_late:
        return ('none', 'contra')

    # Case 3: Ambiguous - use phase-based weighting
    return ('ambiguous', 'ambiguous')


def process_force_plate_data(
    df: pd.DataFrame,
    num_points: int = 150,
    config: ForcePlateConfig = None
) -> Optional[ForcePlateData]:
    """
    Process raw force plate data into phase-normalized ipsi/contra GRF and COP.

    Args:
        df: DataFrame with force plate columns and time
        num_points: Number of output phase points
        config: Force plate configuration

    Returns:
        ForcePlateData with processed GRF/COP arrays, or None if invalid
    """
    if config is None:
        config = ForcePlateConfig()

    # Check required columns
    if config.time_col not in df.columns:
        return None
    if config.fp1_vertical_col not in df.columns or config.fp2_vertical_col not in df.columns:
        return None

    # Calculate phase from time
    t_start = df[config.time_col].min()
    t_end = df[config.time_col].max()
    cycle_duration = t_end - t_start

    if cycle_duration <= 0:
        return None

    phase_original = 100 * (df[config.time_col].values - t_start) / cycle_duration
    phase_target = np.linspace(0, 100, num_points)

    # Helper to get and resample a column
    def get_resampled(col_name: str, fill: float = 0.0) -> np.ndarray:
        if col_name not in df.columns:
            return np.full(num_points, np.nan)
        return resample_to_phase(df[col_name].values, phase_original, num_points, fill)

    # Resample all force plate columns
    fp1_fy = get_resampled(config.fp1_vertical_col)
    fp2_fy = get_resampled(config.fp2_vertical_col)
    fp1_fx = get_resampled(config.fp1_ap_col)
    fp2_fx = get_resampled(config.fp2_ap_col)
    fp1_fz = get_resampled(config.fp1_ml_col)
    fp2_fz = get_resampled(config.fp2_ml_col)

    fp1_px = get_resampled(config.fp1_cop_x_col)
    fp2_px = get_resampled(config.fp2_cop_x_col)
    fp1_py = get_resampled(config.fp1_cop_y_col)
    fp2_py = get_resampled(config.fp2_cop_y_col)
    fp1_pz = get_resampled(config.fp1_cop_z_col)
    fp2_pz = get_resampled(config.fp2_cop_z_col)

    # Determine ipsi/contra assignment
    fp1_assign, fp2_assign = assign_force_plates_to_legs(
        fp1_fy, fp2_fy, phase_target, config
    )

    # Gait120 coordinate convention (and many OpenSim setups):
    # px = X = medial-lateral position
    # py = Y = vertical position (always ~0 for floor-level force plate)
    # pz = Z = anterior-posterior position (walking direction)
    #
    # This matches the TRC marker coordinate system in Gait120.
    # NOTE: Subject walks in -Z direction, so we negate pz for anterior-positive convention.

    # Create NaN arrays for missing data
    nan_array = np.full(num_points, np.nan)

    if fp1_assign == 'contra' and fp2_assign == 'ipsi':
        # FP1 = contra, FP2 = ipsi
        return ForcePlateData(
            grf_vertical_ipsi_N=fp2_fy,
            grf_vertical_contra_N=fp1_fy,
            grf_anterior_ipsi_N=fp2_fx,
            grf_anterior_contra_N=fp1_fx,
            grf_lateral_ipsi_N=fp2_fz,
            grf_lateral_contra_N=fp1_fz,
            cop_anterior_ipsi_m=-fp2_pz,  # Negate pz for anterior-positive
            cop_lateral_ipsi_m=fp2_px,    # px = lateral
            cop_anterior_contra_m=-fp1_pz,
            cop_lateral_contra_m=fp1_px,
        )
    elif fp1_assign == 'ipsi' and fp2_assign == 'contra':
        # FP1 = ipsi, FP2 = contra
        return ForcePlateData(
            grf_vertical_ipsi_N=fp1_fy,
            grf_vertical_contra_N=fp2_fy,
            grf_anterior_ipsi_N=fp1_fx,
            grf_anterior_contra_N=fp2_fx,
            grf_lateral_ipsi_N=fp1_fz,
            grf_lateral_contra_N=fp2_fz,
            cop_anterior_ipsi_m=-fp1_pz,  # Negate pz for anterior-positive
            cop_lateral_ipsi_m=fp1_px,    # px = lateral
            cop_anterior_contra_m=-fp2_pz,
            cop_lateral_contra_m=fp2_px,
        )
    elif fp2_assign == 'ipsi' and fp1_assign == 'none':
        # Only FP2 has data (ipsi leg), contra is NaN
        return ForcePlateData(
            grf_vertical_ipsi_N=fp2_fy,
            grf_vertical_contra_N=nan_array,
            grf_anterior_ipsi_N=fp2_fx,
            grf_anterior_contra_N=nan_array,
            grf_lateral_ipsi_N=fp2_fz,
            grf_lateral_contra_N=nan_array,
            cop_anterior_ipsi_m=-fp2_pz,  # Negate pz for anterior-positive
            cop_lateral_ipsi_m=fp2_px,
            cop_anterior_contra_m=nan_array,
            cop_lateral_contra_m=nan_array,
        )
    elif fp1_assign == 'ipsi' and fp2_assign == 'none':
        # Only FP1 has data (ipsi leg), contra is NaN
        return ForcePlateData(
            grf_vertical_ipsi_N=fp1_fy,
            grf_vertical_contra_N=nan_array,
            grf_anterior_ipsi_N=fp1_fx,
            grf_anterior_contra_N=nan_array,
            grf_lateral_ipsi_N=fp1_fz,
            grf_lateral_contra_N=nan_array,
            cop_anterior_ipsi_m=-fp1_pz,  # Negate pz for anterior-positive
            cop_lateral_ipsi_m=fp1_px,
            cop_anterior_contra_m=nan_array,
            cop_lateral_contra_m=nan_array,
        )
    elif fp1_assign == 'contra' and fp2_assign == 'none':
        # Only FP1 has data (contra leg), ipsi is NaN
        return ForcePlateData(
            grf_vertical_ipsi_N=nan_array,
            grf_vertical_contra_N=fp1_fy,
            grf_anterior_ipsi_N=nan_array,
            grf_anterior_contra_N=fp1_fx,
            grf_lateral_ipsi_N=nan_array,
            grf_lateral_contra_N=fp1_fz,
            cop_anterior_ipsi_m=nan_array,
            cop_lateral_ipsi_m=nan_array,
            cop_anterior_contra_m=-fp1_pz,  # Negate pz for anterior-positive
            cop_lateral_contra_m=fp1_px,
        )
    elif fp2_assign == 'contra' and fp1_assign == 'none':
        # Only FP2 has data (contra leg), ipsi is NaN
        return ForcePlateData(
            grf_vertical_ipsi_N=nan_array,
            grf_vertical_contra_N=fp2_fy,
            grf_anterior_ipsi_N=nan_array,
            grf_anterior_contra_N=fp2_fx,
            grf_lateral_ipsi_N=nan_array,
            grf_lateral_contra_N=fp2_fz,
            cop_anterior_ipsi_m=nan_array,
            cop_lateral_ipsi_m=nan_array,
            cop_anterior_contra_m=-fp2_pz,  # Negate pz for anterior-positive
            cop_lateral_contra_m=fp2_px,
        )
    else:
        # Ambiguous case - use combined force with phase-based assignment
        total_fy = fp1_fy + fp2_fy
        total_fx = fp1_fx + fp2_fx
        total_fz = fp1_fz + fp2_fz

        # Split by phase: early = contra, late = ipsi
        # With smooth transition in overlap region (40-60%)
        contra_weight = np.clip((60 - phase_target) / 20, 0, 1)  # 1 at 0-40%, 0 at 60%+
        ipsi_weight = np.clip((phase_target - 40) / 20, 0, 1)    # 0 at 0-40%, 1 at 60%+

        # Use dominant force plate's COP at each time point
        fp1_dominant = np.abs(fp1_fy) > np.abs(fp2_fy)
        cop_anterior = np.where(fp1_dominant, -fp1_pz, -fp2_pz)  # Negate pz for anterior-positive
        cop_lateral = np.where(fp1_dominant, fp1_px, fp2_px)     # px = lateral

        return ForcePlateData(
            grf_vertical_ipsi_N=total_fy * ipsi_weight,
            grf_vertical_contra_N=total_fy * contra_weight,
            grf_anterior_ipsi_N=total_fx * ipsi_weight,
            grf_anterior_contra_N=total_fx * contra_weight,
            grf_lateral_ipsi_N=total_fz * ipsi_weight,
            grf_lateral_contra_N=total_fz * contra_weight,
            cop_anterior_ipsi_m=cop_anterior,
            cop_lateral_ipsi_m=cop_lateral,
            cop_anterior_contra_m=cop_anterior,
            cop_lateral_contra_m=cop_lateral,
        )
