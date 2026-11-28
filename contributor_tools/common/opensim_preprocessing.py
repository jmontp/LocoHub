"""Pre-processing utilities for OpenSim inputs (TRC/GRF)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _rotate_y_90(x: float, y: float, z: float) -> Tuple[float, float, float]:
    return -z, y, x


def prepare_trc_for_opensim(
    *,
    trc_path: Path,
    output_path: Path,
    marker_map: Optional[Dict[str, str]] = None,
    rotate_y_90: bool = False,
) -> Path:
    markers, data, rate, units = _read_trc_file(trc_path)
    if marker_map:
        markers, data = _remap_markers(markers, data, marker_map)
    if rotate_y_90:
        data = _rotate_trc_data(data, len(markers))
    _write_trc_file(output_path, markers, data, rate=rate, units=units)
    return output_path


def prepare_grf_mot_for_opensim(
    *,
    grf_mot_path: Path,
    output_path: Path,
    rotate_y_90: bool = False,
) -> Path:
    if not rotate_y_90:
        if grf_mot_path.resolve() == output_path.resolve():
            return output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(grf_mot_path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        return output_path

    df = _read_mot_as_dataframe(grf_mot_path)
    df_rot = _rotate_grf_dataframe(df)
    _write_mot_from_dataframe(output_path, df_rot, name="rotated_grf")
    return output_path


def _read_trc_file(trc_path: Path) -> Tuple[List[str], np.ndarray, float, str]:
    with open(trc_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    rate_line = lines[2].strip().split("\t")
    rate = float(rate_line[0])
    units = rate_line[4].strip() if len(rate_line) >= 5 else "mm"

    marker_line = lines[3].strip().split("\t")
    markers = [m for m in marker_line[2:] if m]

    data = []
    for line in lines[6:]:
        if not line.strip():
            continue
        vals = line.strip().split("\t")
        row = [float(v) if v else np.nan for v in vals]
        data.append(row)

    return markers, np.array(data, dtype=float), rate, units


def _write_trc_file(output_path: Path, markers: List[str], data: np.ndarray, *, rate: float, units: str) -> None:
    n_frames = data.shape[0]
    n_markers = len(markers)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"PathFileType\t4\t(X/Y/Z)\t{output_path.name}\n")
        f.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        f.write(f"{rate:.2f}\t{rate:.2f}\t{n_frames}\t{n_markers}\t{units}\t{rate:.2f}\t1\t{n_frames}\n")
        f.write("Frame#\tTime\t" + "\t\t\t".join(markers) + "\t\t\n")
        xyz_line = "\t"
        for i in range(n_markers):
            xyz_line += f"\tX{i+1}\tY{i+1}\tZ{i+1}"
        f.write(xyz_line + "\n\n")
        for i in range(n_frames):
            line = f"{int(data[i, 0])}\t{data[i, 1]:.5f}"
            for j in range(n_markers):
                col = 2 + j * 3
                line += f"\t{data[i, col]:.5f}\t{data[i, col+1]:.5f}\t{data[i, col+2]:.5f}"
            f.write(line + "\n")


def _remap_markers(markers: List[str], data: np.ndarray, marker_map: Dict[str, str]) -> Tuple[List[str], np.ndarray]:
    mapped = [(i, m, marker_map[m]) for i, m in enumerate(markers) if m in marker_map]
    if not mapped:
        raise ValueError("No markers could be mapped for OpenSim input preparation.")
    new_markers = [new for _, _, new in mapped]
    new_data = np.zeros((data.shape[0], 2 + len(mapped) * 3), dtype=float)
    new_data[:, :2] = data[:, :2]
    for new_idx, (orig_idx, _, _) in enumerate(mapped):
        orig_col = 2 + orig_idx * 3
        new_col = 2 + new_idx * 3
        new_data[:, new_col : new_col + 3] = data[:, orig_col : orig_col + 3]
    return new_markers, new_data


def _rotate_trc_data(data: np.ndarray, n_markers: int) -> np.ndarray:
    rotated = data.copy()
    for marker_idx in range(n_markers):
        col = 2 + marker_idx * 3
        xyz = rotated[:, col : col + 3]
        out = np.empty_like(xyz)
        for i in range(xyz.shape[0]):
            out[i, 0], out[i, 1], out[i, 2] = _rotate_y_90(float(xyz[i, 0]), float(xyz[i, 1]), float(xyz[i, 2]))
        rotated[:, col : col + 3] = out
    return rotated


def _read_mot_as_dataframe(mot_path: Path) -> pd.DataFrame:
    with open(mot_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == "endheader":
            header_idx = i + 1
            break
    if header_idx is None:
        raise ValueError(f"Invalid .mot file: {mot_path}")
    columns = lines[header_idx].strip().split()
    data = []
    for line in lines[header_idx + 1 :]:
        if not line.strip():
            continue
        data.append([float(x) for x in line.strip().split()])
    return pd.DataFrame(data, columns=columns)


def _write_mot_from_dataframe(output_path: Path, df: pd.DataFrame, *, name: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"{name}\n")
        f.write("version=1\n")
        f.write(f"nRows={len(df)}\n")
        f.write(f"nColumns={len(df.columns)}\n")
        f.write("inDegrees=no\n")
        f.write("endheader\n")
        f.write("\t".join(df.columns) + "\n")
        for _, row in df.iterrows():
            f.write("\t".join(f"{float(v):.6f}" for v in row.to_list()) + "\n")


def _rotate_grf_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rotated = df.copy()
    for fp in ("1", "2"):
        fx_col, fy_col, fz_col = f"ground_force{fp}_vx", f"ground_force{fp}_vy", f"ground_force{fp}_vz"
        if fx_col in rotated.columns:
            fx, fy, fz = rotated[fx_col].to_numpy(), rotated[fy_col].to_numpy(), rotated[fz_col].to_numpy()
            rotated[fx_col], rotated[fy_col], rotated[fz_col] = -fz, fy, fx

        px_col, py_col, pz_col = f"ground_force{fp}_px", f"ground_force{fp}_py", f"ground_force{fp}_pz"
        if px_col in rotated.columns:
            px, py, pz = rotated[px_col].to_numpy(), rotated[py_col].to_numpy(), rotated[pz_col].to_numpy()
            rotated[px_col], rotated[py_col], rotated[pz_col] = -pz, py, px

        tx_col, ty_col, tz_col = f"ground_torque{fp}_x", f"ground_torque{fp}_y", f"ground_torque{fp}_z"
        if tx_col in rotated.columns:
            tx, ty, tz = rotated[tx_col].to_numpy(), rotated[ty_col].to_numpy(), rotated[tz_col].to_numpy()
            rotated[tx_col], rotated[ty_col], rotated[tz_col] = -tz, ty, tx
    return rotated

