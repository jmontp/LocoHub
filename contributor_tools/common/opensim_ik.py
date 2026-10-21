"""OpenSim inverse kinematics wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple
import os

import numpy as np
import pandas as pd

try:
    import opensim as osim  # type: ignore

    OPENSIM_AVAILABLE = True
except Exception:
    osim = None
    OPENSIM_AVAILABLE = False


@dataclass(frozen=True)
class IKConfig:
    marker_weights: Dict[str, float] = field(default_factory=dict)
    accuracy: float = 1e-5


@dataclass(frozen=True)
class IKResult:
    success: bool
    output_mot_path: Optional[Path] = None
    rms_error_mm: float = float("nan")
    error_message: Optional[str] = None


def read_mot_file(mot_path: Path) -> pd.DataFrame:
    with open(mot_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "endheader":
            header_idx = i + 1
            break
    if header_idx is None or header_idx >= len(lines):
        raise ValueError(f"Invalid .mot file (missing endheader): {mot_path}")

    columns = lines[header_idx].strip().split()
    data = []
    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        data.append([float(x) for x in line.strip().split()])
    return pd.DataFrame(data, columns=columns)


def get_ik_coordinate_names(mot_path: Path) -> Sequence[str]:
    df = read_mot_file(mot_path)
    return [c for c in df.columns if c != "time"]


def create_ik_setup_xml(*args, **kwargs) -> Path:
    raise NotImplementedError("XML-based IK setup generation is not implemented in this wrapper.")


def validate_ik_against_reference(*args, **kwargs) -> Dict[str, float]:
    raise NotImplementedError("Reference validation is not implemented in this wrapper.")


def run_inverse_kinematics(
    *,
    model_path: Path,
    trc_path: Path,
    output_mot_path: Path,
    config: IKConfig = IKConfig(),
    results_dir: Optional[Path] = None,
) -> IKResult:
    if not OPENSIM_AVAILABLE:
        return IKResult(success=False, error_message="OpenSim Python API not available")

    assert osim is not None
    model_path = Path(model_path)
    trc_path = Path(trc_path)
    output_mot_path = Path(output_mot_path)
    if results_dir is None:
        results_dir = output_mot_path.parent
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    try:
        model = osim.Model(str(model_path))
        ik_tool = osim.InverseKinematicsTool()
        ik_tool.setModel(model)
        ik_tool.setMarkerDataFileName(str(trc_path))
        if hasattr(ik_tool, "set_accuracy"):
            ik_tool.set_accuracy(float(config.accuracy))
        elif hasattr(ik_tool, "setAccuracy"):
            ik_tool.setAccuracy(float(config.accuracy))

        marker_data = osim.MarkerData(str(trc_path))
        start_time = float(marker_data.getStartFrameTime())
        end_time = float(marker_data.getLastFrameTime())
        ik_tool.setStartTime(start_time)
        ik_tool.setEndTime(end_time)

        ik_tool.setOutputMotionFileName(str(output_mot_path))

        trc_markers = set(_read_trc_marker_names(trc_path))
        ik_task_set = ik_tool.upd_IKTaskSet()
        ik_task_set.clearAndDestroy()
        for marker_name, weight in config.marker_weights.items():
            if marker_name not in trc_markers:
                continue
            task = osim.IKMarkerTask()
            task.setName(marker_name)
            task.setApply(True)
            task.setWeight(float(weight))
            ik_task_set.cloneAndAppend(task)

        cwd = os.getcwd()
        try:
            os.chdir(str(results_dir))
            ik_tool.run()
        finally:
            os.chdir(cwd)

        rms_error_mm = _read_rms_marker_error_mm(results_dir / "_ik_marker_errors.sto", n_markers=len(config.marker_weights))
        return IKResult(success=True, output_mot_path=output_mot_path, rms_error_mm=rms_error_mm)
    except Exception as e:
        return IKResult(success=False, error_message=str(e))


def _read_trc_marker_names(trc_path: Path) -> Sequence[str]:
    with open(trc_path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in range(3):
            f.readline()
        marker_line = f.readline().strip().split("\t")
    return [m for m in marker_line[2:] if m]


def _read_rms_marker_error_mm(error_sto_path: Path, *, n_markers: int) -> float:
    if not error_sto_path.exists():
        return float("nan")
    try:
        df = read_mot_file(error_sto_path)
        # OpenSim writes slightly different columns depending on version/config.
        if "marker_error_RMS" in df.columns:
            # In meters.
            return float(df["marker_error_RMS"].mean() * 1000.0)
        if "marker_sum_squared_error" in df.columns:
            mse = float(df["marker_sum_squared_error"].mean())
            denom = max(1, int(n_markers))
            return float(np.sqrt(mse / denom) * 1000.0)
        return float("nan")
    except Exception:
        return float("nan")
