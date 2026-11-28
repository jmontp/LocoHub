"""High-level OpenSim Scale → IK → ID pipeline with caching."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .opensim_scaling import ScalingConfig, scale_model_with_static_trial
from .opensim_ik import IKConfig, read_mot_file as read_ik_mot_file, run_inverse_kinematics
from .opensim_inverse_dynamics import (
    InverseDynamicsConfig,
    OPENSIM_AVAILABLE,
    compute_inverse_dynamics_for_stride,
    interpolate_to_phase,
)


@dataclass(frozen=True)
class PipelineConfig:
    scaling: ScalingConfig = ScalingConfig()
    ik: IKConfig = IKConfig()
    id: InverseDynamicsConfig = InverseDynamicsConfig()
    cache_scaled_models: bool = True
    cache_ik_results: bool = True
    cache_dir: Optional[Path] = None
    num_phase_points: int = 150
    rotate_y_90: bool = False
    marker_map: Dict[str, str] = field(default_factory=dict)
    segment_marker_pairs: Dict[str, Tuple[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class StrideResult:
    success: bool
    scaled_model_path: Optional[Path] = None
    ik_mot_path: Optional[Path] = None
    id_sto_path: Optional[Path] = None
    kinematics_phase: Optional[Dict[str, np.ndarray]] = None
    moments_phase: Optional[Dict[str, np.ndarray]] = None
    error_message: Optional[str] = None


class OpenSimPipeline:
    def __init__(self, *, generic_model_path: Path, output_dir: Path, config: PipelineConfig = PipelineConfig()):
        self.generic_model_path = Path(generic_model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config

        if self.config.cache_dir is None:
            self.cache_dir = self.output_dir
        else:
            self.cache_dir = Path(self.config.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.scaled_models_dir = self.cache_dir / "scaled_models"
        self.ik_dir = self.cache_dir / "ik"
        self.id_dir = self.cache_dir / "id"
        self.prep_dir = self.cache_dir / "prepared_inputs"
        for d in (self.scaled_models_dir, self.ik_dir, self.id_dir, self.prep_dir):
            d.mkdir(parents=True, exist_ok=True)

    def process_stride(
        self,
        *,
        subject_id: str,
        static_trc_path: Path,
        stride_trc_path: Path,
        subject_mass_kg: float,
        ipsi_side: str,
        grf_mot_path: Optional[Path] = None,
        subject_height_m: Optional[float] = None,
        stride_key: Optional[str] = None,
        phase_normalize: bool = True,
    ) -> StrideResult:
        if not OPENSIM_AVAILABLE:
            return StrideResult(success=False, error_message="OpenSim Python API not available")

        stride_key = stride_key or f"{subject_id}_{Path(stride_trc_path).stem}"

        try:
            prepared_static = self._prepare_trc(static_trc_path, f"{subject_id}_static")
            prepared_stride = self._prepare_trc(stride_trc_path, stride_key)
            prepared_grf = self._prepare_grf(grf_mot_path, stride_key) if grf_mot_path is not None else None

            scaled_model = self._get_or_create_scaled_model(
                subject_id=subject_id,
                static_trc_path=prepared_static,
                subject_mass_kg=subject_mass_kg,
                subject_height_m=subject_height_m,
            )

            ik_out = self._get_or_run_ik(scaled_model, prepared_stride, stride_key=stride_key)
            kinematics_phase = extract_sagittal_kinematics(
                ik_mot_path=ik_out,
                ipsi_side=ipsi_side,
                num_points=self.config.num_phase_points,
            )

            moments = None
            id_sto_path = None
            if prepared_grf is not None:
                moments = compute_inverse_dynamics_for_stride(
                    model_path=scaled_model,
                    ik_mot_path=ik_out,
                    grf_mot_path=prepared_grf,
                    ipsi_side=ipsi_side,
                    body_mass_kg=subject_mass_kg,
                    config=self.config.id,
                    work_dir=self.id_dir / stride_key,
                )
                id_sto_path = (self.id_dir / stride_key / "id_output.sto") if moments is not None else None

            moments_phase = None
            if moments is not None and phase_normalize and "time" in moments:
                time_s = moments["time"]
                moments_phase = {}
                for k, v in moments.items():
                    if k == "time":
                        continue
                    moments_phase[k] = interpolate_to_phase(v, time_s, num_points=self.config.num_phase_points)

            return StrideResult(
                success=True,
                scaled_model_path=scaled_model,
                ik_mot_path=ik_out,
                id_sto_path=id_sto_path,
                moments_phase=moments_phase,
                kinematics_phase=kinematics_phase or None,
            )
        except Exception as e:
            return StrideResult(success=False, error_message=str(e))

    def _get_or_create_scaled_model(
        self,
        *,
        subject_id: str,
        static_trc_path: Path,
        subject_mass_kg: float,
        subject_height_m: Optional[float],
    ) -> Path:
        out_path = self.scaled_models_dir / f"{subject_id}.osim"
        if self.config.cache_scaled_models and out_path.exists():
            return out_path

        scale_factors = None
        if self.config.segment_marker_pairs:
            scale_factors = None

        scaled = scale_model_with_static_trial(
            generic_model_path=self.generic_model_path,
            static_trc_path=static_trc_path,
            output_model_path=out_path,
            subject_mass_kg=subject_mass_kg,
            subject_height_m=subject_height_m,
            scale_factors=scale_factors,
            segment_marker_pairs=self.config.segment_marker_pairs or None,
            config=self.config.scaling,
            working_dir=self.scaled_models_dir / subject_id,
        )
        return scaled

    def _get_or_run_ik(self, scaled_model_path: Path, stride_trc_path: Path, *, stride_key: str) -> Path:
        out_path = self.ik_dir / f"{stride_key}.mot"
        if self.config.cache_ik_results and out_path.exists():
            return out_path
        res = run_inverse_kinematics(
            model_path=scaled_model_path,
            trc_path=stride_trc_path,
            output_mot_path=out_path,
            config=self.config.ik,
            results_dir=self.ik_dir,
        )
        if not res.success or res.output_mot_path is None:
            raise RuntimeError(res.error_message or "IK failed")
        return res.output_mot_path

    def _prepare_trc(self, trc_path: Path, key: str) -> Path:
        from .opensim_preprocessing import prepare_trc_for_opensim

        return prepare_trc_for_opensim(
            trc_path=Path(trc_path),
            output_path=self.prep_dir / f"{key}.trc",
            marker_map=self.config.marker_map or None,
            rotate_y_90=self.config.rotate_y_90,
        )

    def _prepare_grf(self, mot_path: Path, key: str) -> Path:
        from .opensim_preprocessing import prepare_grf_mot_for_opensim

        return prepare_grf_mot_for_opensim(
            grf_mot_path=Path(mot_path),
            output_path=self.prep_dir / f"{key}_grf.mot",
            rotate_y_90=self.config.rotate_y_90,
        )


def extract_sagittal_kinematics(
    *,
    ik_mot_path: Path,
    ipsi_side: str,
    num_points: int = 150,
) -> Dict[str, np.ndarray]:
    """Extract phase-normalized sagittal kinematics from an IK .mot file.

    OpenSim IK output is in degrees; this returns radians in LocoHub naming.
    """
    ik_mot_path = Path(ik_mot_path)
    ipsi_side = str(ipsi_side).lower()
    num_points = int(num_points)

    if ipsi_side not in {"r", "l"}:
        raise ValueError(f"ipsi_side must be 'r' or 'l', got: {ipsi_side}")

    ik_df = read_ik_mot_file(ik_mot_path)
    if "time" not in ik_df.columns or len(ik_df) < 2:
        return {}

    contra_side = "l" if ipsi_side == "r" else "r"
    time_s = ik_df["time"].to_numpy(dtype=float)

    def maybe_interp_deg(col_name: str) -> Optional[np.ndarray]:
        if col_name not in ik_df.columns:
            return None
        values_deg = ik_df[col_name].to_numpy(dtype=float)
        values_rad = np.deg2rad(values_deg)
        return interpolate_to_phase(values_rad, time_s, num_points=num_points)

    out: Dict[str, np.ndarray] = {}

    hip_ipsi = maybe_interp_deg(f"hip_flexion_{ipsi_side}")
    hip_contra = maybe_interp_deg(f"hip_flexion_{contra_side}")
    knee_ipsi = maybe_interp_deg(f"knee_angle_{ipsi_side}")
    knee_contra = maybe_interp_deg(f"knee_angle_{contra_side}")
    ankle_ipsi = maybe_interp_deg(f"ankle_angle_{ipsi_side}")
    ankle_contra = maybe_interp_deg(f"ankle_angle_{contra_side}")
    pelvis = maybe_interp_deg("pelvis_tilt")

    if hip_ipsi is not None:
        out["hip_flexion_angle_ipsi_rad"] = hip_ipsi
    if hip_contra is not None:
        out["hip_flexion_angle_contra_rad"] = hip_contra
    if knee_ipsi is not None:
        out["knee_flexion_angle_ipsi_rad"] = knee_ipsi
    if knee_contra is not None:
        out["knee_flexion_angle_contra_rad"] = knee_contra
    if ankle_ipsi is not None:
        out["ankle_dorsiflexion_angle_ipsi_rad"] = ankle_ipsi
    if ankle_contra is not None:
        out["ankle_dorsiflexion_angle_contra_rad"] = ankle_contra
    if pelvis is not None:
        out["pelvis_sagittal_angle_rad"] = pelvis

    return out
