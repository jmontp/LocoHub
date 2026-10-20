"""Marker mapping and IK weights for Gait120 → Rajagopal model.

Gait120 marker names follow a Plug-in Gait style convention (e.g., RKNE, RANK).
The Rajagopal 2016 model uses anatomical landmarks and cluster markers (e.g., RLFC, RLMAL, RTH2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


GAIT120_TO_RAJAGOPAL: Dict[str, str] = {
    # Pelvis markers (exact match)
    "LASI": "LASI",
    "RASI": "RASI",
    "LPSI": "LPSI",
    "RPSI": "RPSI",
    # Thigh clusters (use mid-thigh marker in Rajagopal)
    "LTHI": "LTH2",
    "RTHI": "RTH2",
    # Knee (lateral femoral condyle)
    "LKNE": "LLFC",
    "RKNE": "RLFC",
    # Shank clusters (use mid-shank marker in Rajagopal)
    "LTIB": "LTB2",
    "RTIB": "RTB2",
    # Ankle (lateral malleolus)
    "LANK": "LLMAL",
    "RANK": "RLMAL",
    # Foot markers
    "LHEE": "LCAL",
    "RHEE": "RCAL",
    "LTOE": "LTOE",
    "RTOE": "RTOE",
}


IK_MARKER_WEIGHTS_GAIT120: Dict[str, float] = {
    # Pelvis anatomical landmarks
    "LASI": 20.0,
    "RASI": 20.0,
    "LPSI": 20.0,
    "RPSI": 20.0,
    # Knee/ankle anatomical landmarks
    "LLFC": 10.0,
    "RLFC": 10.0,
    "LLMAL": 10.0,
    "RLMAL": 10.0,
    # Heel/toe
    "LCAL": 5.0,
    "RCAL": 5.0,
    "LTOE": 5.0,
    "RTOE": 5.0,
    # Clusters
    "LTH2": 2.0,
    "RTH2": 2.0,
    "LTB2": 2.0,
    "RTB2": 2.0,
}


def rename_markers_in_trc(
    *,
    trc_in: Path,
    trc_out: Path,
    marker_map: Optional[Dict[str, str]] = None,
) -> Path:
    """Rename TRC markers to match model marker names.

    This is a thin wrapper around `common.opensim_preprocessing.prepare_trc_for_opensim`
    so dataset code can do local renaming if needed.
    """
    if marker_map is None:
        marker_map = GAIT120_TO_RAJAGOPAL
    from common.opensim_preprocessing import prepare_trc_for_opensim

    return prepare_trc_for_opensim(trc_path=Path(trc_in), output_path=Path(trc_out), marker_map=marker_map, rotate_y_90=False)

