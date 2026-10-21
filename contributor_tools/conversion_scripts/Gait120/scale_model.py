"""Anthropometric helpers for Gait120 conversion scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
import math


def load_anthropometric_data(gait120_root: Path) -> pd.DataFrame:
    """Load official Gait120 anthropometrics spreadsheet.

    Looks first in `gait120_root/Anthropometric_Data_Participants.xlsx`, then falls back
    to the copy committed alongside this conversion script.
    """
    gait120_root = Path(gait120_root)
    local_copy = Path(__file__).parent / "Anthropometric_Data_Participants.xlsx"
    candidate = gait120_root / "Anthropometric_Data_Participants.xlsx"
    xlsx_path = candidate if candidate.exists() else local_copy
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Anthropometrics file not found at {candidate} or {local_copy}")

    df = pd.read_excel(xlsx_path)
    if "Subject" not in df.columns:
        raise ValueError(f"Unexpected anthropometrics schema in {xlsx_path}")
    return df


def get_subject_anthropometrics(subject_folder: str, gait120_root: Path) -> Dict[str, Any]:
    df = load_anthropometric_data(gait120_root)
    subj = str(subject_folder).strip()
    row = df.loc[df["Subject"].astype(str) == subj]
    if len(row) != 1:
        raise ValueError(f"Expected one anthropometric record for {subj}, found {len(row)}")
    r = row.iloc[0]

    height_mm = float(r["Height(mm)"])
    mass_kg = float(r["Bodymass(Kg)"])
    leg_mm = float(r["Leglength(mm)"])
    height_mm = height_mm if math.isfinite(height_mm) and height_mm > 0 else math.nan
    mass_kg = mass_kg if math.isfinite(mass_kg) and mass_kg > 0 else math.nan
    leg_mm = leg_mm if math.isfinite(leg_mm) and leg_mm > 0 else math.nan

    out: Dict[str, Any] = {
        "subject": subj,
        "height_m": height_mm / 1000.0,
        "mass_kg": mass_kg,
        "leg_length_m": leg_mm / 1000.0,
    }
    for key in ["KneeWidth(mm)", "AnkleWidth(mm)", "ShoulderOffset(mm)", "ElbowWidth(mm)", "WristWidth(mm)", "HandThickness(mm)"]:
        if key in r.index:
            out[key.replace("(mm)", "").replace(" ", "_").lower()] = float(r[key]) / 1000.0
    return out


def get_subject_mass(subject_folder: str, gait120_root: Path) -> float:
    return float(get_subject_anthropometrics(subject_folder, gait120_root)["mass_kg"])


def get_subject_height(subject_folder: str, gait120_root: Path) -> float:
    return float(get_subject_anthropometrics(subject_folder, gait120_root)["height_m"])

