"""
Marker mapping from Plug-in-Gait (PiG) to OpenSim Rajagopal model.

The StrokePiG dataset uses the full-body Plug-in-Gait marker set (43 markers).
This module provides mapping to the Rajagopal 2015 model markers for IK.

Plug-in-Gait marker set (lower body):
    Pelvis: LASI, RASI, LPSI, RPSI
    Thigh:  LTHI, RTHI (wand markers)
    Knee:   LKNE, RKNE (lateral epicondyle)
    Shank:  LTIB, RTIB (wand markers)
    Ankle:  LANK, RANK (lateral malleolus)
    Foot:   LHEE, RHEE (calcaneus), LTOE, RTOE (2nd metatarsal head)
"""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd


# Plug-in-Gait to Rajagopal model marker mapping
# Key = PiG marker name, Value = Rajagopal marker name
PIG_TO_RAJAGOPAL = {
    # Pelvis markers (same names in both models)
    'LASI': 'LASI',
    'RASI': 'RASI',
    'LPSI': 'LPSI',
    'RPSI': 'RPSI',

    # Thigh tracking markers
    'LTHI': 'LTH2',   # Left thigh cluster marker
    'RTHI': 'RTH2',   # Right thigh cluster marker

    # Knee markers - PiG uses lateral epicondyle
    'LKNE': 'LLFC',   # Left lateral femoral condyle
    'RKNE': 'RLFC',   # Right lateral femoral condyle

    # Shank tracking markers
    'LTIB': 'LTB2',   # Left tibial cluster marker
    'RTIB': 'RTB2',   # Right tibial cluster marker

    # Ankle markers - PiG uses lateral malleolus
    'LANK': 'LLMAL',  # Left lateral malleolus
    'RANK': 'RLMAL',  # Right lateral malleolus

    # Foot markers
    'LHEE': 'LCAL',   # Left calcaneus
    'RHEE': 'RCAL',   # Right calcaneus
    'LTOE': 'LTOE',   # Left toe (2nd met head)
    'RTOE': 'RTOE',   # Right toe (2nd met head)
}

# Segment marker pairs for geometric scaling (Rajagopal marker names).
# Keys must match OpenSim body names in the Rajagopal model.
# Only anatomical landmark pairs are used; wand/cluster markers (RTH2, RTB2, etc.)
# are excluded because their distance to joint markers does not scale with segment
# length. Segments without pairs (femur, tibia, torso, etc.) receive a mass-based
# uniform scale factor from opensim_scaling.py.
STROKEPIG_SEGMENT_MARKER_PAIRS = {
    "pelvis": ("LASI", "RASI"),
    "calcn_r": ("RCAL", "RTOE"),
    "calcn_l": ("LCAL", "LTOE"),
}

# Full upper body mapping (for full-body model if needed)
PIG_TO_RAJAGOPAL_UPPER = {
    # Head
    'LFHD': 'LFHD',
    'RFHD': 'RFHD',
    'LBHD': 'LBHD',
    'RBHD': 'RBHD',

    # Trunk
    'C7': 'C7',
    'T10': 'T10',
    'CLAV': 'CLAV',
    'STRN': 'STRN',

    # Shoulders
    'LSHO': 'LSHO',
    'RSHO': 'RSHO',

    # Arms
    'LELB': 'LELB',
    'RELB': 'RELB',
    'LWRA': 'LWRA',
    'RWRA': 'RWRA',
    'LWRB': 'LWRB',
    'RWRB': 'RWRB',
    'LFIN': 'LFIN',
    'RFIN': 'RFIN',
}


# IK marker weights for Rajagopal model with PiG markers
# Higher weights for anatomical landmarks, lower for tracking markers
IK_MARKER_WEIGHTS_PIG = {
    # Pelvis - high weight (well-defined anatomical landmarks)
    'LASI': 20.0,
    'RASI': 20.0,
    'LPSI': 20.0,
    'RPSI': 20.0,

    # Knee - high weight (anatomical landmarks)
    'LLFC': 15.0,   # mapped from LKNE
    'RLFC': 15.0,   # mapped from RKNE

    # Ankle - high weight (anatomical landmarks)
    'LLMAL': 15.0,  # mapped from LANK
    'RLMAL': 15.0,  # mapped from RANK

    # Foot - medium weight
    'LCAL': 10.0,   # mapped from LHEE
    'RCAL': 10.0,   # mapped from RHEE
    'LTOE': 10.0,
    'RTOE': 10.0,

    # Thigh tracking - lower weight (soft tissue artifact)
    'LTH2': 5.0,    # mapped from LTHI
    'RTH2': 5.0,    # mapped from RTHI

    # Shank tracking - lower weight (soft tissue artifact)
    'LTB2': 5.0,    # mapped from LTIB
    'RTB2': 5.0,    # mapped from RTIB
}


def rename_markers_in_trc(trc_path: Path, output_path: Path,
                          mapping: Optional[Dict[str, str]] = None) -> bool:
    """
    Rename markers in a TRC file from PiG to Rajagopal naming.

    Args:
        trc_path: Path to input TRC file
        output_path: Path for output TRC file
        mapping: Custom marker mapping (default: PIG_TO_RAJAGOPAL)

    Returns:
        True if successful
    """
    if mapping is None:
        mapping = PIG_TO_RAJAGOPAL

    try:
        with open(trc_path, 'r') as f:
            lines = f.readlines()

        if len(lines) < 4:
            return False

        # Line 4 (index 3) contains marker names
        marker_line = lines[3]
        for pig_name, raj_name in mapping.items():
            # Replace marker names (tab-separated, avoid partial matches)
            marker_line = marker_line.replace(f'\t{pig_name}\t', f'\t{raj_name}\t')
            # Handle start/end of line
            if marker_line.startswith(pig_name + '\t'):
                marker_line = raj_name + '\t' + marker_line[len(pig_name) + 1:]

        lines[3] = marker_line

        with open(output_path, 'w') as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Warning: Could not rename markers in {trc_path}: {e}")
        return False


def get_pig_markers_from_c3d_labels(labels: list) -> Dict[str, str]:
    """
    Identify PiG markers from C3D point labels and return mapping.

    C3D files may have extra computed labels (CentreOfMass, Angles, etc.)
    This filters to just the actual marker labels.

    Args:
        labels: List of point labels from C3D file

    Returns:
        Dictionary mapping found PiG marker names to themselves
    """
    # All possible PiG marker names (lower body + upper body)
    all_pig_markers = set(PIG_TO_RAJAGOPAL.keys()) | set(PIG_TO_RAJAGOPAL_UPPER.keys())

    found = {}
    for label in labels:
        label_stripped = label.strip()
        if label_stripped in all_pig_markers:
            found[label_stripped] = label_stripped

    return found
