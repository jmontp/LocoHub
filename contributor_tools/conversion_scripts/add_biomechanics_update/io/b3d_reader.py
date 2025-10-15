"""Streaming reader for AddBiomechanics B3D files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List

import numpy as np
import pandas as pd

try:  # pragma: no cover - nimblephysics is optional in test environment
    import nimblephysics as nimble
except ImportError:  # pragma: no cover - exercised when dependency missing
    nimble = None


_POSE_INDEX_MAP = {
    "pelvis_sagittal_angle_rad": 0,
    "pelvis_frontal_angle_rad": 1,
    "pelvis_transverse_angle_rad": 2,
    "hip_flexion_angle_contra_rad": 6,
    "hip_adduction_angle_contra_rad": 7,
    "hip_rotation_angle_contra_rad": 8,
    "knee_flexion_angle_contra_rad": 9,
    "ankle_flexion_angle_contra_rad": 10,
    "ankle_rotation_angle_contra_rad": 11,
    "hip_flexion_angle_ipsi_rad": 13,
    "hip_adduction_angle_ipsi_rad": 14,
    "hip_rotation_angle_ipsi_rad": 15,
    "knee_flexion_angle_ipsi_rad": 16,
    "ankle_flexion_angle_ipsi_rad": 17,
    "ankle_rotation_angle_ipsi_rad": 18,
}

_VEL_INDEX_MAP = {
    "pelvis_sagittal_velocity_rad_s": 0,
    "pelvis_frontal_velocity_rad_s": 1,
    "pelvis_transverse_velocity_rad_s": 2,
    "hip_flexion_velocity_contra_rad_s": 6,
    "hip_adduction_velocity_contra_rad_s": 7,
    "hip_rotation_velocity_contra_rad_s": 8,
    "knee_flexion_velocity_contra_rad_s": 9,
    "ankle_flexion_velocity_contra_rad_s": 10,
    "ankle_rotation_velocity_contra_rad_s": 11,
    "hip_flexion_velocity_ipsi_rad_s": 13,
    "hip_adduction_velocity_ipsi_rad_s": 14,
    "hip_rotation_velocity_ipsi_rad_s": 15,
    "knee_flexion_velocity_ipsi_rad_s": 16,
    "ankle_flexion_velocity_ipsi_rad_s": 17,
    "ankle_rotation_velocity_ipsi_rad_s": 18,
}

_TORQUE_INDEX_MAP = {
    "hip_flexion_moment_contra_Nm": 6,
    "hip_adduction_moment_contra_Nm": 7,
    "hip_rotation_moment_contra_Nm": 8,
    "knee_flexion_moment_contra_Nm": 9,
    "ankle_flexion_moment_contra_Nm": 10,
    "ankle_rotation_moment_contra_Nm": 11,
    "hip_flexion_moment_ipsi_Nm": 13,
    "hip_adduction_moment_ipsi_Nm": 14,
    "hip_rotation_moment_ipsi_Nm": 15,
    "knee_flexion_moment_ipsi_Nm": 16,
    "ankle_flexion_moment_ipsi_Nm": 17,
    "ankle_rotation_moment_ipsi_Nm": 18,
}


@dataclass
class B3DReader:
    """Yield normalized dataframe chunks from B3D sources."""

    dataset_root: Path
    dataset_name: str
    chunk_size: int = 1_000_000

    def __post_init__(self) -> None:
        self._dataset_root = Path(self.dataset_root).expanduser().resolve()
        self._dataset_path = (self._dataset_root / self.dataset_name).resolve()
        if not self._dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset path '{self._dataset_path}' does not exist"
            )
        self._b3d_files: List[Path] = sorted(self._dataset_path.rglob("*.b3d"))
        if not self._b3d_files:
            raise FileNotFoundError(
                f"No .b3d files found under '{self._dataset_path}'"
            )

    # ---------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stream_frames(self) -> Iterator[pd.DataFrame]:
        """Stream dataframe chunks from the dataset folder."""

        if nimble is None:  # pragma: no cover - requires optional dependency
            raise ImportError(
                "nimblephysics is required to read B3D files. "
                "Install the dependency or run within the MATLAB environment."
            )

        for file_path in self._b3d_files:
            yield from self._stream_subject_file(file_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _stream_subject_file(self, file_path: Path) -> Iterator[pd.DataFrame]:
        subject_disk = nimble.biomechanics.SubjectOnDisk(str(file_path))
        subject_mass = float(subject_disk.getMassKg())
        subject_name = self._normalise_subject_name(file_path.stem)

        num_trials = subject_disk.getNumTrials()
        for trial_idx in range(num_trials):
            trial_name = subject_disk.getTrialOriginalName(trial_idx)
            timestep = float(subject_disk.getTrialTimestep(trial_idx))

            frames = subject_disk.readFrames(trial_idx, 0, self.chunk_size)
            if not frames:
                continue

            accum_time = 0.0
            records = []
            for frame_index, frame in enumerate(frames):
                # We use the second processing pass which contains dynamics
                state = frame.processingPasses[1]
                record = self._frame_to_record(
                    state,
                    subject_name,
                    subject_mass,
                    trial_name,
                    frame_index,
                    accum_time,
                )
                records.append(record)
                accum_time += timestep

            if records:
                yield pd.DataFrame.from_records(records)

    def _frame_to_record(
        self,
        state,
        subject_name: str,
        subject_mass: float,
        trial_name: str,
        frame_index: int,
        time_s: float,
    ) -> dict:
        poses = np.asarray(state.pos, dtype=float)
        vels = np.asarray(state.vel, dtype=float)
        torques = np.asarray(state.tau, dtype=float)
        grf = np.asarray(state.groundContactForceInRootFrame, dtype=float)
        cop = np.asarray(state.groundContactCenterOfPressureInRootFrame, dtype=float)
        contact = np.asarray(state.contact, dtype=int)
        com_pos = np.asarray(state.comPos, dtype=float)
        com_vel = np.asarray(state.comVel, dtype=float)

        record = {
            "dataset": self.dataset_name,
            "subject": subject_name,
            "subject_mass": subject_mass,
            "task_raw": trial_name,
            "trial_id": trial_name,
            "frame_index": frame_index,
            "time_s": time_s,
            "contact_contra": int(contact[0]) if contact.size > 0 else 0,
            "contact_ipsi": int(contact[1]) if contact.size > 1 else 0,
            "grf_vertical_contra_N": float(grf[1]) if grf.size >= 2 else 0.0,
            "grf_vertical_ipsi_N": float(grf[4]) if grf.size >= 5 else 0.0,
            "grf_ap_contra_N": float(grf[0]) if grf.size >= 1 else 0.0,
            "grf_ap_ipsi_N": float(grf[3]) if grf.size >= 4 else 0.0,
            "grf_ml_contra_N": float(grf[2]) if grf.size >= 3 else 0.0,
            "grf_ml_ipsi_N": float(grf[5]) if grf.size >= 6 else 0.0,
            "cop_contra_x_m": float(cop[0]) if cop.size >= 1 else np.nan,
            "cop_contra_y_m": float(cop[1]) if cop.size >= 2 else np.nan,
            "cop_contra_z_m": float(cop[2]) if cop.size >= 3 else np.nan,
            "cop_ipsi_x_m": float(cop[3]) if cop.size >= 4 else np.nan,
            "cop_ipsi_y_m": float(cop[4]) if cop.size >= 5 else np.nan,
            "cop_ipsi_z_m": float(cop[5]) if cop.size >= 6 else np.nan,
            "com_position_x_m": float(com_pos[0]) if com_pos.size >= 1 else np.nan,
            "com_position_y_m": float(com_pos[1]) if com_pos.size >= 2 else np.nan,
            "com_position_z_m": float(com_pos[2]) if com_pos.size >= 3 else np.nan,
            "com_velocity_x_m_s": float(com_vel[0]) if com_vel.size >= 1 else np.nan,
            "com_velocity_y_m_s": float(com_vel[1]) if com_vel.size >= 2 else np.nan,
            "com_velocity_z_m_s": float(com_vel[2]) if com_vel.size >= 3 else np.nan,
        }

        for name, idx in _POSE_INDEX_MAP.items():
            if idx < len(poses):
                record[name] = float(poses[idx])

        for name, idx in _VEL_INDEX_MAP.items():
            if idx < len(vels):
                record[name] = float(vels[idx])

        for name, idx in _TORQUE_INDEX_MAP.items():
            if idx < len(torques):
                record[name] = float(torques[idx])

        return record

    @staticmethod
    def _normalise_subject_name(raw_name: str) -> str:
        if "_split" in raw_name:
            raw_name = raw_name.split("_split")[0]
        return raw_name.replace(".b3d", "")
