"""
Parse subject metadata from the StrokePiG dataset.

Metadata sources:
- SubjectChar.xlsx: Anthropometric measurements (mass, height, leg lengths, etc.)
- *.mp files: Vicon-generated anthropometric parameters per subject

Note: Affected side information is not currently available in the dataset files.
This must be provided externally or inferred from the data.
"""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import pandas as pd


def parse_mp_file(mp_path: Path) -> Dict[str, float]:
    """
    Parse a Vicon .mp (model parameters) file.

    The .mp format has lines like:
        $Bodymass = 66.9
        $Height = 1710

    Args:
        mp_path: Path to the .mp file

    Returns:
        Dictionary mapping parameter names to values
    """
    params = {}

    if not mp_path.exists():
        return params

    try:
        with open(mp_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('$') and '=' in line:
                    # Parse: $ParamName = value
                    match = re.match(r'\$(\w+)\s*=\s*([-\d.eE]+)', line)
                    if match:
                        name = match.group(1)
                        try:
                            value = float(match.group(2))
                            params[name] = value
                        except ValueError:
                            pass
    except Exception as e:
        print(f"Warning: Could not parse {mp_path}: {e}")

    return params


def find_mp_file(subject_path: Path) -> Optional[Path]:
    """
    Find the .mp file for a subject.

    StrokePiG naming pattern: TVC-{num}.mp within the subject folder.

    Args:
        subject_path: Path to subject folder (e.g., .../TVC03/)

    Returns:
        Path to .mp file or None if not found
    """
    # Try different naming patterns
    mp_files = list(subject_path.glob("*.mp"))

    if mp_files:
        return mp_files[0]

    return None


def get_subject_id_from_folder(folder_name: str) -> str:
    """
    Extract normalized subject ID from folder name.

    Args:
        folder_name: e.g., 'TVC03', 'TVC47'

    Returns:
        Normalized ID, e.g., 'TVC03'
    """
    # Ensure consistent format
    match = re.match(r'TVC(\d+)', folder_name)
    if match:
        return f"TVC{int(match.group(1)):02d}"
    return folder_name


def load_subject_char_xlsx(xlsx_path: Path) -> pd.DataFrame:
    """
    Load the SubjectChar.xlsx metadata file.

    The file has a transposed format:
    - Rows are parameter names (LABEL column)
    - Columns are subject IDs (TVC03, TVC04, ...)

    Args:
        xlsx_path: Path to SubjectChar.xlsx

    Returns:
        DataFrame with subjects as rows and parameters as columns
    """
    df = pd.read_excel(xlsx_path)

    # Transpose so subjects are rows
    df_t = df.set_index('LABEL').drop(columns=['TYPE', 'UNIT'], errors='ignore').T
    df_t.index.name = 'subject_id'
    df_t = df_t.reset_index()

    return df_t


def parse_numeric_value(value: Any) -> Optional[float]:
    """
    Parse a numeric value that may have European decimal notation.

    Args:
        value: Value from Excel (may be string with comma, int, or float)

    Returns:
        Float value or None if unparseable
    """
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Handle European comma notation (e.g., "66,9" -> 66.9)
        value = value.replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return None

    return None


def get_subject_metadata(
    subject_id: str,
    dataset_path: Path,
    subject_char_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Get metadata for a subject from all available sources.

    Priority:
    1. .mp file in subject folder (most accurate)
    2. SubjectChar.xlsx (fallback)

    Args:
        subject_id: Subject ID (e.g., 'TVC03')
        dataset_path: Root path to StrokePiG dataset
        subject_char_df: Pre-loaded SubjectChar DataFrame (optional)

    Returns:
        Dictionary with:
        - mass_kg: Body mass in kg
        - height_m: Height in meters
        - affected_side: 'l', 'r', or 'unknown'
        - leg_length_l_m: Left leg length in meters
        - leg_length_r_m: Right leg length in meters
        - sex: Sex if available
    """
    metadata = {
        'mass_kg': 70.0,  # Default
        'height_m': 1.70,  # Default
        'affected_side': 'unknown',  # Not available in dataset
        'leg_length_l_m': 0.85,
        'leg_length_r_m': 0.85,
        'sex': 'unknown',
    }

    subject_path = dataset_path / subject_id

    # Try to get from .mp file first (most accurate)
    mp_path = find_mp_file(subject_path)
    if mp_path:
        mp_params = parse_mp_file(mp_path)

        if 'Bodymass' in mp_params:
            metadata['mass_kg'] = mp_params['Bodymass']

        if 'Height' in mp_params:
            # Height in .mp is typically in mm
            height_val = mp_params['Height']
            if height_val > 100:  # Likely mm
                metadata['height_m'] = height_val / 1000.0
            else:  # Likely already in meters
                metadata['height_m'] = height_val

        if 'LLegLength' in mp_params:
            leg_l = mp_params['LLegLength']
            metadata['leg_length_l_m'] = leg_l / 1000.0 if leg_l > 10 else leg_l

        if 'RLegLength' in mp_params:
            leg_r = mp_params['RLegLength']
            metadata['leg_length_r_m'] = leg_r / 1000.0 if leg_r > 10 else leg_r

    # Fall back to SubjectChar.xlsx if .mp not available or missing data
    if subject_char_df is not None:
        subject_row = subject_char_df[
            subject_char_df['subject_id'] == subject_id
        ]

        if not subject_row.empty:
            row = subject_row.iloc[0]

            if metadata['mass_kg'] == 70.0 and 'Bodymass' in row:
                mass = parse_numeric_value(row['Bodymass'])
                if mass and mass > 0:
                    metadata['mass_kg'] = mass

            if metadata['height_m'] == 1.70 and 'Height' in row:
                height = parse_numeric_value(row['Height'])
                if height:
                    if height > 100:  # mm
                        metadata['height_m'] = height / 1000.0
                    else:
                        metadata['height_m'] = height

            if 'LLegLength' in row:
                leg_l = parse_numeric_value(row['LLegLength'])
                if leg_l:
                    metadata['leg_length_l_m'] = leg_l / 1000.0 if leg_l > 10 else leg_l

            if 'RLegLength' in row:
                leg_r = parse_numeric_value(row['RLegLength'])
                if leg_r:
                    metadata['leg_length_r_m'] = leg_r / 1000.0 if leg_r > 10 else leg_r

    return metadata


def get_subject_mass(subject_id: str, dataset_path: Path) -> float:
    """Get subject body mass in kg."""
    metadata = get_subject_metadata(subject_id, dataset_path)
    return metadata['mass_kg']


def get_subject_height(subject_id: str, dataset_path: Path) -> float:
    """Get subject height in meters."""
    metadata = get_subject_metadata(subject_id, dataset_path)
    return metadata['height_m']


def list_all_subjects(dataset_path: Path) -> list:
    """
    List all subject IDs in the dataset.

    Args:
        dataset_path: Root path to StrokePiG dataset

    Returns:
        Sorted list of subject IDs (e.g., ['TVC03', 'TVC04', ...])
    """
    subjects = []
    for folder in sorted(dataset_path.iterdir()):
        if folder.is_dir() and folder.name.startswith('TVC'):
            subjects.append(folder.name)
    return subjects


# Affected side mapping (to be populated externally if available)
# Format: {'TVC03': 'l', 'TVC04': 'r', ...}
# This would need to come from clinical records or additional metadata
AFFECTED_SIDE_MAP: Dict[str, str] = {}


def get_affected_side(subject_id: str) -> str:
    """
    Get the affected (paretic) side for a stroke survivor.

    Args:
        subject_id: Subject ID (e.g., 'TVC03')

    Returns:
        'l' for left, 'r' for right, or 'unknown' if not available
    """
    return AFFECTED_SIDE_MAP.get(subject_id, 'unknown')


def set_affected_side_map(mapping: Dict[str, str]):
    """
    Set the affected side mapping from external data.

    Args:
        mapping: Dictionary mapping subject IDs to affected side ('l' or 'r')
    """
    global AFFECTED_SIDE_MAP
    AFFECTED_SIDE_MAP = mapping
