#!/usr/bin/env python3
"""
OpenSim Pipeline for Gait120 Dataset

A modular pipeline for Scale -> IK -> ID that supports multiple models.

Usage:
    python opensim_pipeline.py --subject S011 --trial Trial01 --step Step02 --model rajagopal
    python opensim_pipeline.py --subject S011 --trial Trial01 --step Step02 --model gait2392
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import shutil
import tempfile
import os
import sys

# Allow importing `contributor_tools/common` utilities when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Try to import opensim
try:
    import opensim as osim
    OPENSIM_AVAILABLE = True
except ImportError:
    OPENSIM_AVAILABLE = False
    print("Warning: OpenSim not available. Install with: conda install -c opensim-org opensim")


# =============================================================================
# MODEL CONFIGURATIONS
# =============================================================================

@dataclass
class ModelConfig:
    """Configuration for a specific OpenSim model."""
    name: str
    model_file: str
    # Mapping from TRC marker names to model marker names
    marker_map: Dict[str, str]
    # Marker weights for IK (higher = more important)
    marker_weights: Dict[str, float]
    # Default coordinate values for scaling pose
    default_pose: Dict[str, float]


# Rajagopal 2016 model configuration
# Marker names: https://simtk.org/projects/full_body
# RASI/LASI/RPSI/LPSI = pelvis ASIS and PSIS
# RTH1/2/3, LTH1/2/3 = thigh cluster
# RLFC/RMFC = lateral/medial femoral condyle (knee)
# RTB1/2/3, LTB1/2/3 = shank cluster
# RLMAL/RMMAL = lateral/medial malleolus (ankle)
# RCAL/LCAL = calcaneus (heel)
# RTOE/LTOE = toe
RAJAGOPAL_CONFIG = ModelConfig(
    name="rajagopal2016",
    model_file="rajagopal_original.osim",
    marker_map={
        # Pelvis markers (exact match)
        'LASI': 'LASI', 'RASI': 'RASI', 'LPSI': 'LPSI', 'RPSI': 'RPSI',
        # Thigh markers (use mid-thigh cluster marker)
        'LTHI': 'LTH2', 'RTHI': 'RTH2',
        # Knee markers (lateral femoral condyle)
        'LKNE': 'LLFC', 'RKNE': 'RLFC',
        # Shank markers (use mid-shank cluster marker)
        'LTIB': 'LTB2', 'RTIB': 'RTB2',
        # Ankle markers (lateral malleolus)
        'LANK': 'LLMAL', 'RANK': 'RLMAL',
        # Foot markers (heel = calcaneus)
        'LHEE': 'LCAL', 'RHEE': 'RCAL',
        'LTOE': 'LTOE', 'RTOE': 'RTOE',
    },
    marker_weights={
        # Pelvis - highest weight (anatomical landmarks)
        'LASI': 20.0, 'RASI': 20.0, 'LPSI': 20.0, 'RPSI': 20.0,
        # Knee - high weight (anatomical landmarks)
        'LLFC': 10.0, 'RLFC': 10.0,
        # Ankle - high weight (anatomical landmarks)
        'LLMAL': 10.0, 'RLMAL': 10.0,
        # Heel and toe - medium weight
        'LCAL': 5.0, 'RCAL': 5.0,
        'LTOE': 5.0, 'RTOE': 5.0,
        # Thigh/shank clusters - lower weight (soft tissue, more movement artifact)
        'LTH2': 2.0, 'RTH2': 2.0,
        'LTB2': 2.0, 'RTB2': 2.0,
    },
    default_pose={},  # Use model defaults
)

# Gait2392 model configuration (Plug-in Gait compatible)
GAIT2392_CONFIG = ModelConfig(
    name="gait2392",
    model_file="gait2392_simbody.osim",
    marker_map={
        # Gait2392 uses Plug-in Gait marker names directly
        'LASI': 'L.ASIS', 'RASI': 'R.ASIS',
        'LPSI': 'L.PSIS', 'RPSI': 'R.PSIS',
        'LTHI': 'L.Thigh', 'RTHI': 'R.Thigh',
        'LKNE': 'L.Knee', 'RKNE': 'R.Knee',
        'LTIB': 'L.Shank', 'RTIB': 'R.Shank',
        'LANK': 'L.Ankle', 'RANK': 'R.Ankle',
        'LHEE': 'L.Heel', 'RHEE': 'R.Heel',
        'LTOE': 'L.Toe', 'RTOE': 'R.Toe',
    },
    marker_weights={
        'L.ASIS': 20.0, 'R.ASIS': 20.0, 'L.PSIS': 20.0, 'R.PSIS': 20.0,
        'L.Knee': 10.0, 'R.Knee': 10.0,
        'L.Ankle': 10.0, 'R.Ankle': 10.0,
        'L.Heel': 5.0, 'R.Heel': 5.0,
        'L.Toe': 5.0, 'R.Toe': 5.0,
        'L.Thigh': 2.0, 'R.Thigh': 2.0,
        'L.Shank': 2.0, 'R.Shank': 2.0,
    },
    default_pose={},
)

MODEL_CONFIGS = {
    'rajagopal': RAJAGOPAL_CONFIG,
    'gait2392': GAIT2392_CONFIG,
}


# =============================================================================
# FILE I/O UTILITIES
# =============================================================================

def read_trc_file(trc_path: Path) -> Tuple[List[str], np.ndarray, float]:
    """
    Read a TRC file and return marker names, data, and frame rate.

    TRC format:
        Line 1: PathFileType header
        Line 2: Column names (DataRate, CameraRate, etc.)
        Line 3: Values (100.0, 100.0, ...)
        Line 4: Marker names
        Line 5: XYZ labels
        Line 6: Empty
        Line 7+: Data

    Returns:
        markers: List of marker names
        data: Array of shape (n_frames, 2 + n_markers*3) with [frame, time, x1,y1,z1, ...]
        rate: Data rate in Hz
    """
    with open(trc_path) as f:
        lines = f.readlines()

    # Parse header - rate is on line 3 (0-indexed line 2)
    rate_line = lines[2].strip().split('\t')
    rate = float(rate_line[0])

    # Parse marker names (line 4, 0-indexed line 3)
    marker_line = lines[3].strip().split('\t')
    markers = [m for m in marker_line[2:] if m]  # Skip Frame#, Time

    # Parse data (starts at line 7, 0-indexed line 6)
    data = []
    for line in lines[6:]:
        if line.strip():
            vals = line.strip().split('\t')
            row = [float(v) if v else np.nan for v in vals]
            data.append(row)

    return markers, np.array(data), rate


def write_trc_file(output_path: Path, markers: List[str], data: np.ndarray,
                   rate: float = 100.0, units: str = 'mm'):
    """Write marker data to TRC file format."""
    n_frames = data.shape[0]
    n_markers = len(markers)

    with open(output_path, 'w') as f:
        # Header lines
        f.write(f"PathFileType\t4\t(X/Y/Z)\t{output_path.name}\n")
        f.write(f"DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        f.write(f"{rate:.2f}\t{rate:.2f}\t{n_frames}\t{n_markers}\t{units}\t{rate:.2f}\t1\t{n_frames}\n")

        # Marker names
        f.write("Frame#\tTime\t" + "\t\t\t".join(markers) + "\t\t\n")

        # XYZ labels
        xyz_line = "\t"
        for i in range(n_markers):
            xyz_line += f"\tX{i+1}\tY{i+1}\tZ{i+1}"
        f.write(xyz_line + "\n\n")

        # Data
        for i in range(n_frames):
            line = f"{int(data[i, 0])}\t{data[i, 1]:.5f}"
            for j in range(n_markers):
                col = 2 + j * 3
                line += f"\t{data[i, col]:.5f}\t{data[i, col+1]:.5f}\t{data[i, col+2]:.5f}"
            f.write(line + "\n")


def read_mot_file(mot_path: Path) -> pd.DataFrame:
    """Read an OpenSim .mot file and return as DataFrame."""
    with open(mot_path) as f:
        lines = f.readlines()

    # Find header end
    for i, line in enumerate(lines):
        if line.strip().lower() == 'endheader':
            header_idx = i + 1
            break

    # Parse column names and data
    columns = lines[header_idx].strip().split()
    data = []
    for line in lines[header_idx + 1:]:
        if line.strip():
            data.append([float(x) for x in line.strip().split()])

    return pd.DataFrame(data, columns=columns)


def write_mot_file(output_path: Path, df: pd.DataFrame, name: str = "data", *, in_degrees: bool = False):
    """Write DataFrame to OpenSim .mot file format."""
    with open(output_path, 'w') as f:
        f.write(f"{name}\n")
        f.write("version=1\n")
        f.write(f"nRows={len(df)}\n")
        f.write(f"nColumns={len(df.columns)}\n")
        f.write("inDegrees=yes\n" if in_degrees else "inDegrees=no\n")
        f.write("endheader\n")
        f.write('\t'.join(df.columns) + '\n')
        for _, row in df.iterrows():
            f.write('\t'.join([f"{v:.6f}" for v in row]) + '\n')


# =============================================================================
# COORDINATE TRANSFORMATIONS
# =============================================================================

def rotate_y_90(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Rotate coordinates +90° around Y axis.

    This transforms from a coordinate system where subjects walk in -Z
    to one where they walk in +X (OpenSim's forward direction).

    [x, y, z] -> [-z, y, x]
    """
    return -z, y, x


def rotate_trc_data(data: np.ndarray, n_markers: int) -> np.ndarray:
    """Rotate all marker positions in TRC data by +90° around Y."""
    rotated = data.copy()
    for i in range(n_markers):
        col = 2 + i * 3
        for frame in range(data.shape[0]):
            x, y, z = data[frame, col], data[frame, col+1], data[frame, col+2]
            rotated[frame, col], rotated[frame, col+1], rotated[frame, col+2] = rotate_y_90(x, y, z)
    return rotated


def rotate_grf_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rotate GRF force, COP, and torque vectors by +90° around Y."""
    rotated = df.copy()

    # Rotate each force plate's data
    for fp in ['1', '2']:
        # Force vector
        fx_col, fy_col, fz_col = f'ground_force{fp}_vx', f'ground_force{fp}_vy', f'ground_force{fp}_vz'
        if fx_col in rotated.columns:
            fx, fy, fz = rotated[fx_col].values, rotated[fy_col].values, rotated[fz_col].values
            rotated[fx_col], rotated[fy_col], rotated[fz_col] = -fz, fy, fx

        # COP (point of application)
        px_col, py_col, pz_col = f'ground_force{fp}_px', f'ground_force{fp}_py', f'ground_force{fp}_pz'
        if px_col in rotated.columns:
            px, py, pz = rotated[px_col].values, rotated[py_col].values, rotated[pz_col].values
            rotated[px_col], rotated[py_col], rotated[pz_col] = -pz, py, px

        # Torque vector
        tx_col, ty_col, tz_col = f'ground_torque{fp}_x', f'ground_torque{fp}_y', f'ground_torque{fp}_z'
        if tx_col in rotated.columns:
            tx, ty, tz = rotated[tx_col].values, rotated[ty_col].values, rotated[tz_col].values
            rotated[tx_col], rotated[ty_col], rotated[tz_col] = -tz, ty, tx

    return rotated


# =============================================================================
# MARKER PROCESSING
# =============================================================================

def remap_markers(markers: List[str], data: np.ndarray, marker_map: Dict[str, str]) -> Tuple[List[str], np.ndarray]:
    """
    Remap marker names according to model configuration and filter to only mapped markers.

    Args:
        markers: Original marker names from TRC
        data: Original data array
        marker_map: Mapping from TRC names to model names

    Returns:
        new_markers: Remapped marker names
        new_data: Filtered data with only mapped markers
    """
    # Find which markers we can map
    mapped = []
    for i, m in enumerate(markers):
        if m in marker_map:
            mapped.append((i, m, marker_map[m]))

    if not mapped:
        raise ValueError(f"No markers could be mapped. TRC markers: {markers}")

    # Create new data array
    new_markers = [model_name for _, _, model_name in mapped]
    new_data = np.zeros((data.shape[0], 2 + len(mapped) * 3))
    new_data[:, 0:2] = data[:, 0:2]  # Frame and time

    for new_idx, (orig_idx, _, _) in enumerate(mapped):
        orig_col = 2 + orig_idx * 3
        new_col = 2 + new_idx * 3
        new_data[:, new_col:new_col+3] = data[:, orig_col:orig_col+3]

    return new_markers, new_data


# =============================================================================
# OPENSIM PIPELINE
# =============================================================================

class OpenSimPipeline:
    """Pipeline for running OpenSim Scale -> IK -> ID."""

    def __init__(self, model_config: ModelConfig, work_dir: Path, verbose: bool = True):
        self.config = model_config
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        # Find model file
        script_dir = Path(__file__).parent
        self.model_path = script_dir / model_config.model_file
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")

        self._log(f"Using model: {self.config.name}")
        self._log(f"Model file: {self.model_path}")

    def _log(self, msg: str):
        if self.verbose:
            print(f"[Pipeline] {msg}")

    def scale_model(self, static_trc: Path, subject_mass: float,
                    output_model: Optional[Path] = None,
                    rotate: bool = False) -> Path:
        """
        Scale the generic model to a subject using static trial markers.

        Args:
            static_trc: Path to static trial TRC file
            subject_mass: Subject mass in kg
            output_model: Optional output path for scaled model
            rotate: If True, rotate markers +90° around Y axis

        Returns:
            Path to scaled model file
        """
        if output_model is None:
            output_model = self.work_dir / "scaled_model.osim"

        self._log(f"Scaling model with static trial: {static_trc}")
        if rotate:
            self._log("Rotating static markers +90° around Y (align with +X)")

        # Read and remap static markers
        markers, data, rate = read_trc_file(static_trc)
        new_markers, new_data = remap_markers(markers, data, self.config.marker_map)

        # Apply rotation if requested
        if rotate:
            new_data = rotate_trc_data(new_data, len(new_markers))

        # Write remapped TRC
        remapped_trc = self.work_dir / "static_remapped.trc"
        write_trc_file(remapped_trc, new_markers, new_data, rate)

        # Scale using OpenSim ScaleTool with marker-pair based geometric scaling.
        from common.opensim_scaling import ScalingConfig, scale_model_with_static_trial

        segment_marker_pairs = {
            # Use robust marker pairs for scaling:
            # - Pelvis width from ASIS markers
            # - Foot length from heel-to-toe
            # Thigh/shank cluster markers exist but are less reliable for geometric scaling.
            "pelvis": ("LASI", "RASI"),
            "calcn_r": ("RCAL", "RTOE"),
            "calcn_l": ("LCAL", "LTOE"),
        }

        scaled = scale_model_with_static_trial(
            generic_model_path=self.model_path,
            static_trc_path=remapped_trc,
            output_model_path=output_model,
            subject_mass_kg=float(subject_mass),
            subject_height_m=None,
            segment_marker_pairs=segment_marker_pairs,
            config=ScalingConfig(preserve_mass_distribution=True),
            working_dir=self.work_dir / "scale",
        )
        self._log(f"Saved scaled model: {scaled}")
        return scaled

    def run_ik(self, model_path: Path, trc_path: Path,
               output_mot: Optional[Path] = None,
               rotate: bool = False) -> Tuple[Path, float]:
        """
        Run Inverse Kinematics.

        Args:
            model_path: Path to scaled model
            trc_path: Path to marker data TRC file
            output_mot: Optional output path for IK results
            rotate: If True, rotate markers +90° around Y axis

        Returns:
            Tuple of (output_mot_path, rms_error_mm)
        """
        if output_mot is None:
            output_mot = self.work_dir / "ik_output.mot"

        self._log(f"Running IK on: {trc_path}")
        if rotate:
            self._log("Rotating stride markers +90° around Y")

        # Read and remap markers
        markers, data, rate = read_trc_file(trc_path)
        new_markers, new_data = remap_markers(markers, data, self.config.marker_map)

        # Apply rotation if requested
        if rotate:
            new_data = rotate_trc_data(new_data, len(new_markers))

        # Write remapped TRC
        remapped_trc = self.work_dir / "stride_remapped.trc"
        write_trc_file(remapped_trc, new_markers, new_data, rate)

        # Load model
        model = osim.Model(str(model_path))

        # Setup IK tool
        ik_tool = osim.InverseKinematicsTool()
        ik_tool.setModel(model)
        ik_tool.setMarkerDataFileName(str(remapped_trc))

        # Get time range
        marker_data = osim.MarkerData(str(remapped_trc))
        start_time = marker_data.getStartFrameTime()
        end_time = marker_data.getLastFrameTime()
        ik_tool.setStartTime(start_time)
        ik_tool.setEndTime(end_time)
        ik_tool.setOutputMotionFileName(str(output_mot))

        # Set marker weights
        ik_task_set = ik_tool.upd_IKTaskSet()
        for marker in new_markers:
            task = osim.IKMarkerTask()
            task.setName(marker)
            task.setApply(True)
            weight = self.config.marker_weights.get(marker, 1.0)
            task.setWeight(weight)
            ik_task_set.cloneAndAppend(task)

        # Run IK
        ik_tool.run()

        # Get marker error
        error_file = self.work_dir / "_ik_marker_errors.sto"
        rms_error = 0.0
        if error_file.exists():
            error_df = read_mot_file(error_file)
            if 'marker_sum_squared_error' in error_df.columns:
                mse = error_df['marker_sum_squared_error'].mean()
                rms_error = np.sqrt(mse / len(new_markers)) * 1000  # m to mm

        self._log(f"IK complete. RMS marker error: {rms_error:.1f} mm")
        self._log(f"Output: {output_mot}")

        return output_mot, rms_error

    def run_id(self, model_path: Path, ik_mot: Path, grf_mot: Path,
               output_sto: Optional[Path] = None,
               lowpass_cutoff: float = 6.0,
               rotate: bool = False,
               inertia_only: bool = False) -> Path:
        """
        Run Inverse Dynamics.

        Args:
            model_path: Path to scaled model
            ik_mot: Path to IK results
            grf_mot: Path to GRF data
            output_sto: Optional output path for ID results
            lowpass_cutoff: Low-pass filter cutoff frequency for coordinates
            rotate: If True, rotate GRF data +90° around Y axis

        Returns:
            Path to ID output file
        """
        if output_sto is None:
            output_sto = self.work_dir / "id_output.sto"

        if inertia_only:
            self._log("Running ID (inertia-only; no external forces)")
        else:
            self._log(f"Running ID with GRF: {grf_mot}")

        # If rotating, read GRF, rotate, and write to work_dir
        if rotate and not inertia_only:
            self._log("Rotating GRF data +90° around Y")
            grf_df = read_mot_file(grf_mot)
            grf_df = rotate_grf_data(grf_df)
            rotated_grf = self.work_dir / "grf_rotated.mot"
            write_mot_file(rotated_grf, grf_df, name="rotated_grf")
            grf_mot = rotated_grf

        ext_loads_path = None
        if not inertia_only:
            ext_loads_path = self.work_dir / "external_loads.xml"
            self._write_external_loads(ext_loads_path, grf_mot)

        # Load model
        model = osim.Model(str(model_path))

        # Get time range from IK
        ik_df = read_mot_file(ik_mot)
        start_time = ik_df['time'].iloc[0]
        end_time = ik_df['time'].iloc[-1]

        # Setup ID tool
        id_tool = osim.InverseDynamicsTool()
        id_tool.setModel(model)
        id_tool.setCoordinatesFileName(str(ik_mot))
        if ext_loads_path is not None:
            id_tool.setExternalLoadsFileName(str(ext_loads_path))
        id_tool.setStartTime(start_time)
        id_tool.setEndTime(end_time)
        id_tool.setLowpassCutoffFrequency(lowpass_cutoff)
        # Note: OpenSim requires just the filename, not full path
        # It will write to current working directory
        id_tool.setOutputGenForceFileName(output_sto.name)

        # Run ID (must be in work_dir for output)
        orig_dir = os.getcwd()
        os.chdir(str(self.work_dir))
        try:
            id_tool.run()
        finally:
            os.chdir(orig_dir)

        self._log(f"ID complete. Output: {output_sto}")

        return output_sto

    def _write_external_loads(self, output_path: Path, grf_mot: Path):
        """Write external loads XML file for ID."""
        with open(output_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
            f.write('<OpenSimDocument Version="40000">\n')
            f.write('    <ExternalLoads name="gait_forces">\n')
            f.write('        <objects>\n')
            f.write('            <ExternalForce name="force_r">\n')
            f.write('                <applied_to_body>calcn_r</applied_to_body>\n')
            f.write('                <force_expressed_in_body>ground</force_expressed_in_body>\n')
            f.write('                <point_expressed_in_body>ground</point_expressed_in_body>\n')
            f.write('                <force_identifier>ground_force1_v</force_identifier>\n')
            f.write('                <point_identifier>ground_force1_p</point_identifier>\n')
            f.write('                <torque_identifier>ground_torque1_</torque_identifier>\n')
            f.write('            </ExternalForce>\n')
            f.write('            <ExternalForce name="force_l">\n')
            f.write('                <applied_to_body>calcn_l</applied_to_body>\n')
            f.write('                <force_expressed_in_body>ground</force_expressed_in_body>\n')
            f.write('                <point_expressed_in_body>ground</point_expressed_in_body>\n')
            f.write('                <force_identifier>ground_force2_v</force_identifier>\n')
            f.write('                <point_identifier>ground_force2_p</point_identifier>\n')
            f.write('                <torque_identifier>ground_torque2_</torque_identifier>\n')
            f.write('            </ExternalForce>\n')
            f.write('        </objects>\n')
            f.write(f'        <datafile>{grf_mot}</datafile>\n')
            f.write('    </ExternalLoads>\n')
            f.write('</OpenSimDocument>\n')


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='OpenSim Pipeline for Gait120')
    parser.add_argument('--subject', type=str, default='S011', help='Subject ID (e.g., S011)')
    parser.add_argument('--trial', type=str, default='Trial01', help='Trial number')
    parser.add_argument('--step', type=str, default='Step02', help='Step number')
    parser.add_argument('--model', type=str, default='rajagopal',
                        choices=['rajagopal', 'gait2392'], help='Model to use')
    parser.add_argument('--data-dir', type=str,
                        default='/mnt/s/locomotion_data/Gait120',
                        help='Path to Gait120 dataset')
    parser.add_argument('--output-dir', type=str, default='/tmp/opensim_pipeline',
                        help='Output directory for results')
    parser.add_argument('--mass', type=float, default=None,
                        help='Subject mass in kg (auto-detected if not specified)')
    parser.add_argument('--filter-cutoff', type=float, default=6.0,
                        help='Low-pass filter cutoff for ID (Hz)')
    parser.add_argument('--rotate', action='store_true',
                        help='Rotate TRC/GRF data +90° around Y (align walking with +X)')
    parser.add_argument('--inertia-only', action='store_true',
                        help='Run inverse dynamics without external forces (debugging scaling/kinematics)')
    parser.add_argument('--quiet', action='store_true', help='Suppress output')

    args = parser.parse_args()

    if not OPENSIM_AVAILABLE:
        print("Error: OpenSim not available. Please install it first.")
        return 1

    # Setup paths
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    subject_dir = data_dir / args.subject
    if not subject_dir.exists():
        print(f"Error: Subject directory not found: {subject_dir}")
        return 1

    # Find data files
    static_trc = subject_dir / "MotionCapture" / "Static" / "TRC" / "Trial01.trc"
    stride_trc = subject_dir / "MotionCapture" / "LevelWalking" / "TRC" / args.trial / f"{args.step}.trc"
    grf_mot = subject_dir / "MotionCapture" / "LevelWalking" / "MOT" / args.trial / f"{args.step}.mot"

    # Check files exist
    required = [(static_trc, "Static TRC"), (stride_trc, "Stride TRC")]
    if not args.inertia_only:
        required.append((grf_mot, "GRF MOT"))
    for f, name in required:
        if not f.exists():
            print(f"Error: {name} not found: {f}")
            return 1

    # Get subject mass (default to 75 kg if not specified)
    subject_mass = args.mass if args.mass else 75.0

    # Get model config
    model_config = MODEL_CONFIGS[args.model]

    # Create pipeline
    pipeline = OpenSimPipeline(model_config, output_dir, verbose=not args.quiet)

    # Run pipeline
    print(f"\n{'='*60}")
    print(f"OpenSim Pipeline: {args.model.upper()}")
    print(f"Subject: {args.subject}, Trial: {args.trial}, Step: {args.step}")
    if args.rotate:
        print("Coordinate rotation: ENABLED (+90° Y)")
    print(f"{'='*60}\n")

    # 1. Scale model
    scaled_model = pipeline.scale_model(static_trc, subject_mass, rotate=args.rotate)

    # 2. Run IK
    ik_output, rms_error = pipeline.run_ik(scaled_model, stride_trc, rotate=args.rotate)

    # 3. Run ID
    id_output = pipeline.run_id(scaled_model, ik_output, grf_mot,
                                lowpass_cutoff=args.filter_cutoff,
                                rotate=args.rotate,
                                inertia_only=args.inertia_only)

    # 4. Analyze results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}\n")

    # Read IK output and check pelvis rotation
    ik_df = read_mot_file(ik_output)
    if 'pelvis_rotation' in ik_df.columns:
        print(f"Pelvis rotation: [{ik_df['pelvis_rotation'].min():.1f}°, {ik_df['pelvis_rotation'].max():.1f}°]")

    # Read ID output and show joint moments
    id_df = read_mot_file(id_output)

    moment_cols = [
        'hip_flexion_r_moment', 'hip_adduction_r_moment', 'hip_rotation_r_moment',
        'knee_angle_r_moment', 'ankle_angle_r_moment'
    ]

    expected = {
        'hip_flexion_r_moment': (-1.5, 1.5),
        'hip_adduction_r_moment': (-1.0, 1.0),
        'hip_rotation_r_moment': (-0.5, 0.5),
        'knee_angle_r_moment': (-1.0, 1.0),
        'ankle_angle_r_moment': (-0.2, 1.8),
    }

    print(f"\nJoint Moments (Nm/kg):")
    print(f"{'Joint':<30} {'Range':<20} {'Expected':<15} {'Status'}")
    print("-" * 75)

    all_ok = True
    for col in moment_cols:
        if col in id_df.columns:
            vals = id_df[col].values / subject_mass  # Normalize by mass
            exp = expected.get(col, (-2, 2))

            range_str = f"[{vals.min():.2f}, {vals.max():.2f}]"
            exp_str = f"[{exp[0]}, {exp[1]}]"

            # Check if within expected range (with some tolerance)
            tolerance = 2.0  # Allow 2x expected range
            ok = vals.min() >= exp[0] * tolerance and vals.max() <= exp[1] * tolerance
            status = "✓ OK" if ok else "✗ HIGH"
            all_ok = all_ok and ok

            print(f"{col:<30} {range_str:<20} {exp_str:<15} {status}")

    print(f"\n{'='*60}")
    if all_ok:
        print("All joint moments within expected physiological ranges!")
    else:
        print("Some joint moments are outside expected ranges.")
    print(f"{'='*60}\n")

    return 0


if __name__ == '__main__':
    exit(main())
