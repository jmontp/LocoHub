"""OpenSim inverse dynamics wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

try:
    import opensim as osim  # type: ignore

    OPENSIM_AVAILABLE = True
except Exception:
    osim = None
    OPENSIM_AVAILABLE = False


@dataclass(frozen=True)
class InverseDynamicsConfig:
    lowpass_cutoff_hz: float = 6.0
    lock_secondary_knee_dofs: bool = False
    subtract_inertia_baseline: bool = False
    disable_model_forces: bool = True
    gravity_m_s2: Optional[Tuple[float, float, float]] = None
    right_foot_body: str = "calcn_r"
    left_foot_body: str = "calcn_l"
    force1_identifier: str = "ground_force1"
    force2_identifier: str = "ground_force2"
    torque1_identifier: str = "ground_torque1_"
    torque2_identifier: str = "ground_torque2_"


def check_opensim_available() -> bool:
    return bool(OPENSIM_AVAILABLE or shutil.which("opensim-cmd"))


def modify_rajagopal_model(model: "osim.Model") -> "osim.Model":
    """Lock secondary knee DOFs when explicitly requested.

    Note:
    Locking `knee_angle_*_beta` can over-constrain models that use patellofemoral
    coordinate couplers, so this should be opt-in.
    """
    if not OPENSIM_AVAILABLE:
        return model
    coord_set = model.updCoordinateSet()
    for name in ("knee_angle_r_beta", "knee_angle_l_beta"):
        if coord_set.contains(name):
            coord = coord_set.get(name)
            coord.setDefaultValue(0.0)
            coord.setDefaultLocked(True)
            coord.set_locked(True)
    return model


def disable_model_forces(model: "osim.Model") -> "osim.Model":
    """Disable all model forces (e.g., muscles/reserves) before inverse dynamics.

    OpenSim's InverseDynamicsTool solves for generalized forces *in addition* to
    forces already present in the model. If muscles are present, their passive
    forces can dominate the solution and produce unrealistically large joint
    moments.
    """
    if not OPENSIM_AVAILABLE:
        return model
    force_set = model.updForceSet()
    for i in range(force_set.getSize()):
        force_set.get(i).set_appliesForce(False)
    return model


def setup_external_loads(
    *,
    grf_mot_path: Path,
    output_xml_path: Path,
    config: InverseDynamicsConfig = InverseDynamicsConfig(),
) -> Path:
    grf_mot_path = Path(grf_mot_path).resolve()
    output_xml_path = Path(output_xml_path)
    root = ET.Element("OpenSimDocument", Version="40000")
    ext = ET.SubElement(root, "ExternalLoads", name="external_loads")
    objects = ET.SubElement(ext, "objects")

    f_r = ET.SubElement(objects, "ExternalForce", name="force_r")
    ET.SubElement(f_r, "applied_to_body").text = config.right_foot_body
    ET.SubElement(f_r, "force_expressed_in_body").text = "ground"
    ET.SubElement(f_r, "point_expressed_in_body").text = "ground"
    ET.SubElement(f_r, "force_identifier").text = f"{config.force1_identifier}_v"
    ET.SubElement(f_r, "point_identifier").text = f"{config.force1_identifier}_p"
    ET.SubElement(f_r, "torque_identifier").text = config.torque1_identifier

    f_l = ET.SubElement(objects, "ExternalForce", name="force_l")
    ET.SubElement(f_l, "applied_to_body").text = config.left_foot_body
    ET.SubElement(f_l, "force_expressed_in_body").text = "ground"
    ET.SubElement(f_l, "point_expressed_in_body").text = "ground"
    ET.SubElement(f_l, "force_identifier").text = f"{config.force2_identifier}_v"
    ET.SubElement(f_l, "point_identifier").text = f"{config.force2_identifier}_p"
    ET.SubElement(f_l, "torque_identifier").text = config.torque2_identifier

    ET.SubElement(ext, "datafile").text = str(grf_mot_path)

    tree = ET.ElementTree(root)
    output_xml_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_xml_path, encoding="utf-8", xml_declaration=True)
    return output_xml_path


def run_inverse_dynamics(
    *,
    model_path: Path,
    coordinates_mot_path: Path,
    external_loads_xml_path: Optional[Path],
    output_sto_path: Path,
    config: InverseDynamicsConfig = InverseDynamicsConfig(),
) -> Path:
    model_path = Path(model_path).resolve()
    coordinates_mot_path = Path(coordinates_mot_path).resolve()
    output_sto_path = Path(output_sto_path).resolve()
    external_loads_xml_path = (
        Path(external_loads_xml_path).resolve()
        if external_loads_xml_path is not None
        else None
    )
    output_sto_path.parent.mkdir(parents=True, exist_ok=True)

    if OPENSIM_AVAILABLE:
        assert osim is not None
        model = osim.Model(str(model_path))
        if config.gravity_m_s2 is not None:
            gx, gy, gz = config.gravity_m_s2
            model.setGravity(osim.Vec3(float(gx), float(gy), float(gz)))
        if config.disable_model_forces:
            model = disable_model_forces(model)
        if config.lock_secondary_knee_dofs:
            model = modify_rajagopal_model(model)
        id_tool = osim.InverseDynamicsTool()
        id_tool.setModel(model)
        id_tool.setCoordinatesFileName(str(coordinates_mot_path))
        if external_loads_xml_path is not None:
            id_tool.setExternalLoadsFileName(str(external_loads_xml_path))

        ik_df = read_sto_file(coordinates_mot_path)
        start_time = float(ik_df["time"].iloc[0])
        end_time = float(ik_df["time"].iloc[-1])
        id_tool.setStartTime(start_time)
        id_tool.setEndTime(end_time)
        id_tool.setLowpassCutoffFrequency(float(config.lowpass_cutoff_hz))

        id_tool.setOutputGenForceFileName(output_sto_path.name)
        cwd = os.getcwd()
        try:
            os.chdir(str(output_sto_path.parent))
            id_tool.run()
        finally:
            os.chdir(cwd)
    else:
        opensim_cmd = shutil.which("opensim-cmd")
        if opensim_cmd is None:
            raise RuntimeError("OpenSim not available. Install with: conda install -c opensim-org opensim")
        raise NotImplementedError("CLI-based inverse dynamics is not implemented in this wrapper.")

    if not output_sto_path.exists():
        raise FileNotFoundError(f"InverseDynamicsTool did not produce output at {output_sto_path}")
    return output_sto_path


def read_sto_file(sto_path: Path) -> pd.DataFrame:
    with open(sto_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "endheader":
            header_idx = i + 1
            break
    if header_idx is None or header_idx >= len(lines):
        raise ValueError(f"Invalid .sto/.mot file (missing endheader): {sto_path}")

    columns = lines[header_idx].strip().split()
    data = []
    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        data.append([float(x) for x in line.strip().split()])
    return pd.DataFrame(data, columns=columns)


def extract_sagittal_moments(
    *,
    id_sto_df: pd.DataFrame,
    ipsi_side: str,
    body_mass_kg: float,
) -> Dict[str, np.ndarray]:
    ipsi = ipsi_side.lower()
    if ipsi not in {"r", "l"}:
        raise ValueError(f"ipsi_side must be 'r' or 'l', got: {ipsi_side}")

    def col(name_r: str, name_l: str) -> str:
        return name_r if ipsi == "r" else name_l

    hip_ipsi_col = col("hip_flexion_r_moment", "hip_flexion_l_moment")
    hip_contra_col = col("hip_flexion_l_moment", "hip_flexion_r_moment")
    knee_ipsi_col = col("knee_angle_r_moment", "knee_angle_l_moment")
    knee_contra_col = col("knee_angle_l_moment", "knee_angle_r_moment")
    ankle_ipsi_col = col("ankle_angle_r_moment", "ankle_angle_l_moment")
    ankle_contra_col = col("ankle_angle_l_moment", "ankle_angle_r_moment")

    out: Dict[str, np.ndarray] = {"time": id_sto_df["time"].to_numpy(dtype=float)}

    def get_normed(series: pd.Series) -> np.ndarray:
        return (series.to_numpy(dtype=float) / float(body_mass_kg)).astype(float)

    if hip_ipsi_col in id_sto_df.columns:
        out["hip_flexion_moment_ipsi_Nm_kg"] = get_normed(id_sto_df[hip_ipsi_col])
    if hip_contra_col in id_sto_df.columns:
        out["hip_flexion_moment_contra_Nm_kg"] = get_normed(id_sto_df[hip_contra_col])

    if knee_ipsi_col in id_sto_df.columns:
        out["knee_flexion_moment_ipsi_Nm_kg"] = -get_normed(id_sto_df[knee_ipsi_col])
    if knee_contra_col in id_sto_df.columns:
        out["knee_flexion_moment_contra_Nm_kg"] = -get_normed(id_sto_df[knee_contra_col])

    if ankle_ipsi_col in id_sto_df.columns:
        out["ankle_dorsiflexion_moment_ipsi_Nm_kg"] = get_normed(id_sto_df[ankle_ipsi_col])
    if ankle_contra_col in id_sto_df.columns:
        out["ankle_dorsiflexion_moment_contra_Nm_kg"] = get_normed(id_sto_df[ankle_contra_col])

    return out


def interpolate_to_phase(values: np.ndarray, time_s: np.ndarray, num_points: int = 150) -> np.ndarray:
    if len(values) < 2 or len(time_s) != len(values):
        return np.full(num_points, np.nan)
    t0 = float(time_s[0])
    t1 = float(time_s[-1])
    if not np.isfinite(t0) or not np.isfinite(t1) or t1 <= t0:
        return np.full(num_points, np.nan)
    phase = (time_s - t0) / (t1 - t0)
    target = np.linspace(0.0, 1.0, num_points)
    try:
        return np.interp(target, phase, values).astype(float)
    except Exception:
        return np.full(num_points, np.nan)


def compute_inverse_dynamics_for_stride(
    *,
    model_path: Path,
    ik_mot_path: Path,
    grf_mot_path: Path,
    ipsi_side: str,
    body_mass_kg: float,
    config: InverseDynamicsConfig = InverseDynamicsConfig(),
    work_dir: Optional[Path] = None,
) -> Optional[Dict[str, np.ndarray]]:
    if work_dir is None:
        work_dir = Path(ik_mot_path).parent
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    ext_xml = setup_external_loads(grf_mot_path=grf_mot_path, output_xml_path=work_dir / "external_loads.xml", config=config)
    out_sto = run_inverse_dynamics(
        model_path=model_path,
        coordinates_mot_path=ik_mot_path,
        external_loads_xml_path=ext_xml,
        output_sto_path=work_dir / "id_output.sto",
        config=config,
    )
    df_with_grf = read_sto_file(out_sto)
    moments_with_grf = extract_sagittal_moments(
        id_sto_df=df_with_grf,
        ipsi_side=ipsi_side,
        body_mass_kg=body_mass_kg,
    )

    if not config.subtract_inertia_baseline:
        return moments_with_grf

    out_sto_inertia = run_inverse_dynamics(
        model_path=model_path,
        coordinates_mot_path=ik_mot_path,
        external_loads_xml_path=None,
        output_sto_path=work_dir / "id_inertia_only.sto",
        config=config,
    )
    df_inertia = read_sto_file(out_sto_inertia)
    moments_inertia = extract_sagittal_moments(
        id_sto_df=df_inertia,
        ipsi_side=ipsi_side,
        body_mass_kg=body_mass_kg,
    )

    corrected: Dict[str, np.ndarray] = {"time": moments_with_grf["time"]}
    for key, arr_with in moments_with_grf.items():
        if key == "time":
            continue
        arr_inertia = moments_inertia.get(key)
        if arr_inertia is None or len(arr_inertia) != len(arr_with):
            corrected[key] = arr_with
        else:
            corrected[key] = arr_with - arr_inertia

    return corrected
