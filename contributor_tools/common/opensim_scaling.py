"""OpenSim model scaling utilities.

This module provides ScaleTool wrappers used by contributor conversion scripts.
It is designed to import cleanly even when OpenSim is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple
import math
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
class ScalingConfig:
    preserve_mass_distribution: bool = True
    min_scale: float = 0.5
    max_scale: float = 1.8


def get_model_marker_names(model_path: Path) -> Sequence[str]:
    markers = _parse_osim_marker_locations(model_path)
    return sorted(markers.keys())


def verify_marker_correspondence(model_path: Path, trc_path: Path) -> Dict[str, Sequence[str]]:
    trc_markers = set(_read_trc_markers(trc_path))
    model_markers = set(get_model_marker_names(model_path))
    return {
        "trc_only": sorted(trc_markers - model_markers),
        "model_only": sorted(model_markers - trc_markers),
        "intersection": sorted(trc_markers & model_markers),
    }


def scale_model_with_measurements(
    *,
    generic_model_path: Path,
    output_model_path: Path,
    subject_mass_kg: float,
    subject_height_m: Optional[float] = None,
    config: ScalingConfig = ScalingConfig(),
    working_dir: Optional[Path] = None,
) -> Path:
    """Fallback scaling that applies a uniform scale based on mass^(1/3).

    This is not as accurate as marker-based scaling, but it ensures geometry is
    scaled (unlike mass-only scaling).
    """
    length_scale = float((subject_mass_kg / _get_model_mass_kg(generic_model_path)) ** (1.0 / 3.0))
    length_scale = float(np.clip(length_scale, config.min_scale, config.max_scale))
    body_names = _parse_osim_body_names(generic_model_path)
    scale_factors = {b: (length_scale, length_scale, length_scale) for b in body_names} or {
        "pelvis": (length_scale, length_scale, length_scale)
    }
    return scale_model_with_static_trial(
        generic_model_path=generic_model_path,
        static_trc_path=None,
        output_model_path=output_model_path,
        subject_mass_kg=subject_mass_kg,
        subject_height_m=subject_height_m,
        scale_factors=scale_factors,
        config=config,
        working_dir=working_dir,
    )


def compute_scale_factors_from_marker_pairs(
    *,
    model_path: Path,
    static_trc_path: Path,
    segment_marker_pairs: Dict[str, Tuple[str, str]],
    config: ScalingConfig = ScalingConfig(),
) -> Dict[str, Tuple[float, float, float]]:
    """Compute per-segment uniform scale factors using marker-pair distances.

    This intentionally uses marker pairs that are on the same segment in the model,
    so that the model reference distance can be computed from marker local locations
    without needing a pose/state.
    """
    marker_locations = _parse_osim_marker_locations(model_path)
    trc_positions = _read_trc_positions_m(static_trc_path)

    scale_factors: Dict[str, Tuple[float, float, float]] = {}
    for segment, (marker_a, marker_b) in segment_marker_pairs.items():
        if marker_a not in trc_positions or marker_b not in trc_positions:
            continue
        if marker_a not in marker_locations or marker_b not in marker_locations:
            continue

        model_ref = _model_marker_pair_distance_m(marker_locations, marker_a, marker_b)
        if not math.isfinite(model_ref) or model_ref <= 0:
            continue

        static_dist = _trc_marker_pair_distance_m(trc_positions[marker_a], trc_positions[marker_b])
        if not math.isfinite(static_dist) or static_dist <= 0:
            continue

        ratio = static_dist / model_ref
        ratio = float(np.clip(ratio, config.min_scale, config.max_scale))
        scale_factors[segment] = (ratio, ratio, ratio)

    return scale_factors


def create_scale_setup_xml(
    *,
    generic_model_path: Path,
    static_trc_path: Optional[Path],
    output_model_path: Path,
    subject_mass_kg: float,
    subject_height_m: Optional[float],
    scale_factors: Dict[str, Tuple[float, float, float]],
    output_scale_file_path: Path,
    output_marker_file_path: Optional[Path],
    output_motion_file_path: Optional[Path],
    preserve_mass_distribution: bool,
    time_range: Optional[Tuple[float, float]],
    setup_path: Optional[Path] = None,
) -> Path:
    """Create a ScaleTool setup XML for OpenSim 4.x."""
    if setup_path is None:
        setup_path = output_model_path.with_suffix(".ScaleTool.xml")
    # OpenSim 4.5+ uses the nested <ScaleSet> inside <ModelScaler> (not a
    # "scale_set_file" property). If we emit the wrong schema, ScaleTool will
    # silently ignore the manual scale factors and apply identity scales.
    root = ET.Element("OpenSimDocument", Version="40600")
    scale_tool = ET.SubElement(root, "ScaleTool")

    ET.SubElement(scale_tool, "mass").text = f"{subject_mass_kg:.6f}"
    if subject_height_m is not None:
        # OpenSim ScaleTool stores height in mm (informational only).
        ET.SubElement(scale_tool, "height").text = f"{subject_height_m * 1000.0:.6f}"

    generic_maker = ET.SubElement(scale_tool, "GenericModelMaker")
    ET.SubElement(generic_maker, "model_file").text = str(generic_model_path)

    model_scaler = ET.SubElement(scale_tool, "ModelScaler")
    ET.SubElement(model_scaler, "apply").text = "true"
    ET.SubElement(model_scaler, "scaling_order").text = "manualScale"

    measurement_set = ET.SubElement(model_scaler, "MeasurementSet")
    ET.SubElement(measurement_set, "objects")
    ET.SubElement(measurement_set, "groups")

    scale_set = ET.SubElement(model_scaler, "ScaleSet")
    objects = ET.SubElement(scale_set, "objects")
    for segment, (sx, sy, sz) in scale_factors.items():
        scale = ET.SubElement(objects, "Scale", name=f"{segment}_scale")
        ET.SubElement(scale, "scales").text = f"{sx:.8f} {sy:.8f} {sz:.8f}"
        ET.SubElement(scale, "segment").text = segment
        ET.SubElement(scale, "apply").text = "true"
    ET.SubElement(scale_set, "groups")

    if static_trc_path is not None:
        ET.SubElement(model_scaler, "marker_file").text = str(static_trc_path)
    ET.SubElement(model_scaler, "time_range").text = (
        f"{time_range[0]:.6f} {time_range[1]:.6f}" if time_range is not None else "-1 -1"
    )
    ET.SubElement(model_scaler, "preserve_mass_distribution").text = "true" if preserve_mass_distribution else "false"
    ET.SubElement(model_scaler, "output_model_file").text = str(output_model_path)
    ET.SubElement(model_scaler, "output_scale_file").text = str(output_scale_file_path)

    marker_placer = ET.SubElement(scale_tool, "MarkerPlacer")
    ET.SubElement(marker_placer, "apply").text = "true" if static_trc_path is not None else "false"
    ik_task_set = ET.SubElement(marker_placer, "IKTaskSet")
    ET.SubElement(ik_task_set, "objects")
    ET.SubElement(ik_task_set, "groups")
    if static_trc_path is not None:
        ET.SubElement(marker_placer, "marker_file").text = str(static_trc_path)
    ET.SubElement(marker_placer, "time_range").text = (
        f"{time_range[0]:.6f} {time_range[1]:.6f}" if time_range is not None else "-1 -1"
    )
    ET.SubElement(marker_placer, "output_model_file").text = str(output_model_path)
    if output_motion_file_path is not None:
        ET.SubElement(marker_placer, "output_motion_file").text = str(output_motion_file_path)
    if output_marker_file_path is not None:
        ET.SubElement(marker_placer, "output_marker_file").text = str(output_marker_file_path)
    ET.SubElement(marker_placer, "max_marker_movement").text = "-1"

    tree = ET.ElementTree(root)
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(setup_path, encoding="utf-8", xml_declaration=True)
    return setup_path


def scale_model_with_static_trial(
    *,
    generic_model_path: Path,
    static_trc_path: Optional[Path],
    output_model_path: Path,
    subject_mass_kg: float,
    subject_height_m: Optional[float] = None,
    scale_factors: Optional[Dict[str, Tuple[float, float, float]]] = None,
    segment_marker_pairs: Optional[Dict[str, Tuple[str, str]]] = None,
    config: ScalingConfig = ScalingConfig(),
    working_dir: Optional[Path] = None,
) -> Path:
    """Scale a model, preferring marker-pair scaling when a static TRC is available."""
    generic_model_path = Path(generic_model_path)
    output_model_path = Path(output_model_path)
    static_trc_path = Path(static_trc_path) if static_trc_path is not None else None

    if working_dir is None:
        working_dir = output_model_path.parent
    working_dir = Path(working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)

    # Put ScaleTool inputs/outputs in `working_dir` and reference them via
    # relative paths. This avoids OpenSim path resolution issues when absolute
    # paths are combined with a tool's working directory.
    tool_generic_model_path = working_dir / "generic_model.osim"
    if tool_generic_model_path.resolve() != generic_model_path.resolve():
        shutil.copyfile(generic_model_path, tool_generic_model_path)
    tool_generic_model_ref = Path(tool_generic_model_path.name)

    tool_static_trc_ref: Optional[Path] = None
    if static_trc_path is not None:
        tool_static_trc_path = working_dir / "static_markers.trc"
        if tool_static_trc_path.resolve() != static_trc_path.resolve():
            shutil.copyfile(static_trc_path, tool_static_trc_path)
        tool_static_trc_ref = Path(tool_static_trc_path.name)

    body_names = _parse_osim_body_names(generic_model_path)
    uniform_length_scale = float((subject_mass_kg / _get_model_mass_kg(generic_model_path)) ** (1.0 / 3.0))
    uniform_length_scale = float(np.clip(uniform_length_scale, config.min_scale, config.max_scale))
    uniform_scales = {b: (uniform_length_scale, uniform_length_scale, uniform_length_scale) for b in body_names}

    if scale_factors is None and segment_marker_pairs is not None and static_trc_path is not None:
        marker_pair_scales = compute_scale_factors_from_marker_pairs(
            model_path=generic_model_path,
            static_trc_path=static_trc_path,
            segment_marker_pairs=segment_marker_pairs,
            config=config,
        )
        scale_factors = dict(uniform_scales)
        scale_factors.update(marker_pair_scales)
    if scale_factors is None:
        scale_factors = uniform_scales or {"pelvis": (uniform_length_scale, uniform_length_scale, uniform_length_scale)}

    scale_set_path = working_dir / "scale_set.xml"
    _write_scale_set_xml(scale_factors, scale_set_path)
    scale_set_ref = Path(scale_set_path.name)

    tool_output_model_path = working_dir / "scaled_model.osim"
    tool_output_model_ref = Path(tool_output_model_path.name)

    output_scale_file_path = working_dir / "applied_scales.xml"
    output_scale_ref = Path(output_scale_file_path.name)

    output_marker_file_path = (working_dir / "placed_markers.trc") if tool_static_trc_ref is not None else None
    output_motion_file_path = (working_dir / "scale_motion.mot") if tool_static_trc_ref is not None else None
    output_marker_ref = Path(output_marker_file_path.name) if output_marker_file_path is not None else None
    output_motion_ref = Path(output_motion_file_path.name) if output_motion_file_path is not None else None

    time_range = _infer_trc_time_range(working_dir / tool_static_trc_ref) if tool_static_trc_ref is not None else None

    setup_xml = create_scale_setup_xml(
        generic_model_path=tool_generic_model_ref,
        static_trc_path=tool_static_trc_ref,
        output_model_path=tool_output_model_ref,
        subject_mass_kg=subject_mass_kg,
        subject_height_m=subject_height_m,
        scale_factors=scale_factors,
        output_scale_file_path=output_scale_ref,
        output_marker_file_path=output_marker_ref,
        output_motion_file_path=output_motion_ref,
        preserve_mass_distribution=config.preserve_mass_distribution,
        time_range=time_range,
        setup_path=working_dir / "scale_setup.xml",
    )

    _run_scale_tool(setup_xml, working_dir=working_dir)

    if output_scale_file_path.exists():
        requested_nonidentity = any(
            any(abs(float(s) - 1.0) > 1e-6 for s in scales) for scales in scale_factors.values()
        )
        applied_nonidentity = _scale_set_has_nonidentity_scales(output_scale_file_path)
        if requested_nonidentity and not applied_nonidentity:
            raise RuntimeError(
                "ScaleTool produced identity scales (applied_scales.xml is all 1's) even though non-identity "
                "scale factors were requested. This usually indicates a ScaleTool setup/schema mismatch."
            )

    if not tool_output_model_path.exists():
        raise FileNotFoundError(f"ScaleTool did not produce scaled model at {tool_output_model_path}")
    if tool_output_model_path.resolve() != output_model_path.resolve():
        output_model_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tool_output_model_path, output_model_path)
    return output_model_path


def _run_scale_tool(setup_xml_path: Path, *, working_dir: Path) -> None:
    if OPENSIM_AVAILABLE:
        assert osim is not None
        cwd = Path.cwd()
        try:
            import os

            os.chdir(str(working_dir))
            tool = osim.ScaleTool(str(Path(setup_xml_path).name))
            tool.run()
        finally:
            os.chdir(str(cwd))
        return

    opensim_cmd = shutil.which("opensim-cmd")
    if opensim_cmd is None:
        raise RuntimeError(
            "OpenSim is not available (no Python bindings and no opensim-cmd found). "
            "Install with: conda install -c opensim-org opensim"
        )
    subprocess.run([opensim_cmd, "run-tool", str(setup_xml_path)], cwd=str(working_dir), check=True)


def _infer_trc_time_range(trc_path: Path) -> Optional[Tuple[float, float]]:
    try:
        df = _read_trc_dataframe(trc_path)
        if "Time" not in df.columns or len(df) < 2:
            return None
        return float(df["Time"].iloc[0]), float(df["Time"].iloc[-1])
    except Exception:
        return None


def _get_model_mass_kg(model_path: Path) -> float:
    if not OPENSIM_AVAILABLE:
        return 75.0
    assert osim is not None
    model = osim.Model(str(model_path))
    state = model.initSystem()
    return float(model.getTotalMass(state))


def _write_scale_set_xml(scale_factors: Dict[str, Tuple[float, float, float]], output_path: Path) -> None:
    root = ET.Element("OpenSimDocument", Version="40000")
    scale_set = ET.SubElement(root, "ScaleSet", name="scale_set")
    objects = ET.SubElement(scale_set, "objects")

    for segment, (sx, sy, sz) in scale_factors.items():
        scale = ET.SubElement(objects, "Scale", name=f"{segment}_scale")
        ET.SubElement(scale, "scales").text = f"{sx:.8f} {sy:.8f} {sz:.8f}"
        ET.SubElement(scale, "segment").text = segment
        ET.SubElement(scale, "apply").text = "true"

    ET.SubElement(scale_set, "groups")
    tree = ET.ElementTree(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def _read_trc_markers(trc_path: Path) -> Sequence[str]:
    with open(trc_path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in range(3):
            f.readline()
        marker_line = f.readline().rstrip("\n")
    parts = marker_line.split("\t")
    return [m for m in parts[2:] if m]


def _read_trc_dataframe(trc_path: Path) -> pd.DataFrame:
    with open(trc_path, "r", encoding="utf-8", errors="ignore") as f:
        header = [f.readline() for _ in range(5)]
    # Preserve trailing tab placeholders so the last marker keeps Y/Z columns.
    marker_line = header[3].rstrip("\r\n").split("\t")

    columns = ["Frame", "Time"]
    current_marker = None
    for i, name in enumerate(marker_line[2:], start=2):
        if name:
            current_marker = name
        if current_marker:
            axis = ["X", "Y", "Z"][(i - 2) % 3]
            columns.append(f"{current_marker}_{axis}")

    df = pd.read_csv(trc_path, sep="\t", skiprows=5, header=None)
    df = df.iloc[:, : len(columns)]
    df.columns = columns
    return df


def _read_trc_positions_m(trc_path: Path) -> Dict[str, np.ndarray]:
    df = _read_trc_dataframe(trc_path)

    units_scale = 1.0
    with open(trc_path, "r", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        _ = f.readline()
        units_line = f.readline().strip().split("\t")
    if len(units_line) >= 5:
        units = units_line[4].strip().lower()
        if units in {"mm", "millimeter", "millimeters"}:
            units_scale = 0.001
        elif units in {"cm", "centimeter", "centimeters"}:
            units_scale = 0.01
        elif units in {"m", "meter", "meters"}:
            units_scale = 1.0

    positions: Dict[str, np.ndarray] = {}
    marker_names = sorted({c.rsplit("_", 1)[0] for c in df.columns if c.endswith(("_X", "_Y", "_Z"))})
    for marker in marker_names:
        cols = [f"{marker}_X", f"{marker}_Y", f"{marker}_Z"]
        if any(c not in df.columns for c in cols):
            continue
        arr = df[cols].to_numpy(dtype=float) * units_scale
        positions[marker] = arr
    return positions


def _trc_marker_pair_distance_m(marker_a_xyz: np.ndarray, marker_b_xyz: np.ndarray) -> float:
    if marker_a_xyz.shape != marker_b_xyz.shape or marker_a_xyz.shape[1] != 3:
        return float("nan")
    valid = np.isfinite(marker_a_xyz).all(axis=1) & np.isfinite(marker_b_xyz).all(axis=1)
    if valid.sum() < 5:
        return float("nan")
    d = np.linalg.norm(marker_a_xyz[valid] - marker_b_xyz[valid], axis=1)
    return float(np.nanmedian(d))


def _model_marker_pair_distance_m(
    marker_locations: Dict[str, Tuple[str, np.ndarray]], marker_a: str, marker_b: str
) -> float:
    body_a, loc_a = marker_locations[marker_a]
    body_b, loc_b = marker_locations[marker_b]
    if body_a != body_b:
        return float("nan")
    return float(np.linalg.norm(loc_a - loc_b))


def _parse_osim_marker_locations(model_path: Path) -> Dict[str, Tuple[str, np.ndarray]]:
    tree = ET.parse(str(model_path))
    root = tree.getroot()
    marker_set = root.find(".//MarkerSet/objects")
    if marker_set is None:
        return {}

    markers: Dict[str, Tuple[str, np.ndarray]] = {}
    for marker in marker_set.findall("Marker"):
        name = marker.attrib.get("name")
        if not name:
            continue
        parent = marker.findtext("socket_parent_frame", default="")
        body = parent.rsplit("/", 1)[-1] if "/" in parent else parent
        loc_text = marker.findtext("location", default="").strip()
        parts = [p for p in loc_text.split() if p]
        if len(parts) != 3:
            continue
        loc = np.array([float(parts[0]), float(parts[1]), float(parts[2])], dtype=float)
        markers[name] = (body.replace("bodyset/", ""), loc)
    return markers


def _parse_osim_body_names(model_path: Path) -> Sequence[str]:
    tree = ET.parse(str(model_path))
    root = tree.getroot()
    bodies = root.find(".//BodySet/objects")
    if bodies is None:
        return []
    out = []
    for body in bodies.findall("Body"):
        name = body.attrib.get("name")
        if name:
            out.append(name)
    return sorted(set(out))


def _scale_set_has_nonidentity_scales(scale_set_path: Path) -> bool:
    try:
        tree = ET.parse(str(scale_set_path))
        root = tree.getroot()
        for scales_text in root.findall(".//Scale/scales"):
            if scales_text.text is None:
                continue
            parts = [p for p in scales_text.text.strip().split() if p]
            if len(parts) != 3:
                continue
            values = [float(p) for p in parts]
            if any(abs(v - 1.0) > 1e-6 for v in values):
                return True
        return False
    except Exception:
        return False
