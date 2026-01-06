#!/usr/bin/env python3
"""
Dataset-specific configurations for AddBiomechanics sub-datasets.

This module contains task mappings, subject naming conventions, and metadata
for the 13 AddBiomechanics sub-datasets.

Standard Task Mappings (from docs/reference/index.md):
- Cyclic (phase-friendly): level_walking, incline_walking, decline_walking,
  stair_ascent, stair_descent, run, squat, jump, dynamic_walk
- Non-cyclic (time-indexed): balance_pose, functional_task

Datasets:
- Moore2015: Treadmill walking at multiple speeds
- Camargo2021: Level, ramp, and stair locomotion
- Fregly2012: Normal and dynamic walking patterns
- Hamner2013: Running at various speeds
- Santos2017: Static standing (balance_pose)
- Tan2021: Running variants
- Tan2022: Dynamic walking variants
- vanderZee2022: Treadmill walking trials
- Wang2023: Walking, running, jumps, squats, functional tasks
- Falisse2016: Walking and running (muscle redundancy study)
- Han2023 (GroundLink): 19 motion types (yoga, dance, sports, locomotion)
- Tiziana2019 (Lencioni): Walking, dynamic walk, stairs (ages 6-72)
- Carter2023: Treadmill running at various speeds and gradients
"""

from typing import Dict, Tuple, Optional
import re

# Dataset short codes for standardized subject naming
# Format: {dataset_name: short_code}
# Note: Camargo2021 excluded - available separately as GT21/Gtech_2021 with original data
DATASET_SHORT_CODES = {
    'Moore2015': 'MO15',
    # 'Camargo2021': 'CA21',  # Skipped - use GT21 instead
    'Fregly2012': 'FR12',
    'Hamner2013': 'HA13',
    'Santos2017': 'SA17',
    'Tan2021': 'TA21',
    'Tan2022': 'TA22',
    'vanderZee2022': 'VZ22',
    'Wang2023': 'WA23',
    # Previously missing datasets - now supported
    'Falisse2016': 'FA16',
    'Han2023': 'HA23',
    'Tiziana2019': 'TI19',
    'Carter2023': 'CA23',
}

# Walking speed mappings for Moore2015 (from PeerJ paper Table 1)
# Trial number -> walking speed in m/s
MOORE2015_SPEED_MAP = {
    # 0.8 m/s trials
    9: 0.8, 12: 0.8, 15: 0.8, 16: 0.8, 19: 0.8, 25: 0.8,
    32: 0.8, 40: 0.8, 46: 0.8, 49: 0.8, 55: 0.8, 61: 0.8,
    67: 0.8, 73: 0.8, 76: 0.8,
    # 1.2 m/s trials
    10: 1.2, 13: 1.2, 17: 1.2, 20: 1.2, 26: 1.2, 31: 1.2,
    41: 1.2, 47: 1.2, 50: 1.2, 56: 1.2, 62: 1.2, 68: 1.2,
    74: 1.2, 77: 1.2,
    # 1.6 m/s trials
    11: 1.6, 14: 1.6, 18: 1.6, 21: 1.6, 27: 1.6, 33: 1.6,
    42: 1.6, 48: 1.6, 51: 1.6, 57: 1.6, 63: 1.6, 69: 1.6,
    75: 1.6, 78: 1.6,
}

# Camargo2021 ramp and stair mappings
CAMARGO2021_RAMP_ANGLES = {
    'ramp_1': 5.2, 'ramp_2': 7.795, 'ramp_3': 9.207,
    'ramp_4': 10.989, 'ramp_5': 12.771, 'ramp_6': 18.0,
}
CAMARGO2021_STAIR_HEIGHTS = {
    'stair_1': 4, 'stair_2': 5, 'stair_3': 6, 'stair_4': 7,  # inches
}


def get_task_info_moore2015(original_task: str) -> Tuple[str, str, str]:
    """Map Moore2015 task to standard format."""
    # Extract trial number from task name
    match = re.search(r'(\d+)', original_task)
    speed = 1.2  # default
    if match:
        trial_num = int(match.group(1))
        speed = MOORE2015_SPEED_MAP.get(trial_num, 1.2)

    task_id = f'level_{speed}ms'
    task_info = f'speed_m_s:{speed},treadmill:true'
    return ('level_walking', task_id, task_info)


def get_task_info_camargo2021(original_task: str) -> Tuple[str, str, str]:
    """Map Camargo2021 task to standard format."""
    task_lower = original_task.lower()

    # Determine speed modifier
    speed = 'normal'
    for s in ['fast', 'slow', 'normal']:
        if s in task_lower:
            speed = s
            break

    # Level/treadmill walking
    if task_lower.startswith('level') or task_lower.startswith('treadmill'):
        return ('level_walking', 'level', f'speed:{speed},treadmill:true')

    # Ramp walking
    for ramp_key, angle in CAMARGO2021_RAMP_ANGLES.items():
        if task_lower.startswith(ramp_key):
            if 'incline' in task_lower or angle > 0:
                return ('incline_walking', f'incline_{angle}deg',
                        f'incline_deg:{angle},speed:{speed}')
            else:
                return ('decline_walking', f'decline_{angle}deg',
                        f'incline_deg:{-angle},speed:{speed}')

    # Stair tasks
    for stair_key, height in CAMARGO2021_STAIR_HEIGHTS.items():
        if task_lower.startswith(stair_key):
            if 'ascent' in task_lower or 'up' in task_lower:
                return ('stair_ascent', f'stair_{height}in',
                        f'step_height_in:{height}')
            else:
                return ('stair_descent', f'stair_{height}in',
                        f'step_height_in:{height}')

    # Default for ramp/stair prefixes
    if task_lower.startswith('ramp'):
        return ('incline_walking', 'ramp', f'speed:{speed}')
    if task_lower.startswith('stair'):
        return ('stair_ascent', 'stair', '')

    return ('level_walking', 'level', f'speed:{speed}')


def get_task_info_fregly2012(original_task: str) -> Tuple[str, str, str]:
    """Map Fregly2012 task to standard format."""
    task_lower = original_task.lower()

    # Normal gait
    if 'ngait' in task_lower:
        return ('level_walking', 'level', 'variant:normal_gait')

    # Modified walking patterns
    modified_patterns = {
        'mtpgait': 'medial_thrust_pole',
        'medthrust': 'medial_thrust',
        'mtgait': 'medial_thrust',
        'wpgait': 'walking_pole',
        'tsgait': 'trunk_sway',
        'mildcrouch': 'mild_crouch',
        'crouch_og': 'crouch',
        'bouncy': 'bouncy',
        'smooth': 'smooth',
        'rightturn': 'right_turn',
    }

    for pattern, variant in modified_patterns.items():
        if pattern in task_lower:
            return ('dynamic_walk', f'modified_{variant}', f'variant:{variant}')

    return ('level_walking', 'level', '')


def get_task_info_hamner2013(original_task: str) -> Tuple[str, str, str]:
    """Map Hamner2013 running task to standard format."""
    # Extract speed from task name (run200, run300, run400, run500)
    match = re.search(r'run(\d+)', original_task.lower())
    if match:
        speed_code = int(match.group(1))
        speed = speed_code / 100.0  # 200 -> 2.0 m/s
        return ('run', f'run_{speed}ms', f'speed_m_s:{speed}')
    return ('run', 'run', '')


def get_task_info_santos2017(original_task: str) -> Tuple[str, str, str]:
    """Map Santos2017 task to standard format (standing only)."""
    return ('balance_pose', 'standing', 'variant:static_standing')


def get_task_info_tan2021(original_task: str) -> Tuple[str, str, str]:
    """Map Tan2021 modified running task to standard format."""
    return ('run', 'modified_run', f'variant:modified,original_task:{original_task}')


def get_task_info_tan2022(original_task: str) -> Tuple[str, str, str]:
    """Map Tan2022 modified walking task to standard format."""
    return ('dynamic_walk', 'modified_walk', f'variant:modified,original_task:{original_task}')


def get_task_info_vanderzee2022(original_task: str) -> Tuple[str, str, str]:
    """Map vanderZee2022 task to standard format."""
    # Extract trial number
    trial_num = original_task.replace('trial', '').strip()
    return ('level_walking', 'level', f'trial_number:{trial_num},treadmill:true')


def get_task_info_wang2023(original_task: str) -> Tuple[str, str, str]:
    """Map Wang2023 task to standard format."""
    task_lower = original_task.lower()

    if 'walk' in task_lower:
        return ('level_walking', 'level', '')
    if 'run' in task_lower:
        return ('run', 'run', '')
    if 'static_pose' in task_lower:
        return ('balance_pose', 'static_pose', '')
    if 'jump' in task_lower:
        return ('jump', 'jump', '')
    if 'lunge' in task_lower:
        return ('lunge', 'lunge_forward', '')
    if 'squat' in task_lower:
        return ('squat', 'squat', '')
    if 'land' in task_lower:
        return ('jump', 'landing', 'variant:landing')

    return ('functional_task', original_task, '')


def get_task_info_falisse2016(original_task: str) -> Tuple[str, str, str]:
    """
    Map Falisse2016 task to standard format.
    Dataset contains walking and running trials for muscle redundancy studies.
    """
    task_lower = original_task.lower()

    if 'run' in task_lower:
        return ('run', 'run', 'source:muscle_redundancy_study')
    if 'walk' in task_lower:
        return ('level_walking', 'level', 'source:muscle_redundancy_study')

    # Default to walking if unclear
    return ('level_walking', 'level', f'original_task:{original_task}')


def get_task_info_han2023(original_task: str) -> Tuple[str, str, str]:
    """
    Map Han2023 (GroundLink) task to standard format.
    Dataset has 19 motion types including yoga, dance, sports, and locomotion.
    """
    task_lower = original_task.lower()

    # Locomotion
    if 'walk' in task_lower:
        return ('level_walking', 'level', '')

    # Yoga poses (balance/static)
    yoga_poses = ['tree', 'chair', 'warrior', 'dog', 'side_stretch', 'stretch']
    for pose in yoga_poses:
        if pose in task_lower:
            return ('balance_pose', f'yoga_{pose}', 'category:yoga')

    # Dynamic activities
    if 'jump' in task_lower or 'jumping' in task_lower:
        return ('jump', 'jumping_jack', '')
    if 'hop' in task_lower:
        return ('hop', 'hop_single', '')
    if 'squat' in task_lower:
        return ('squat', 'squat', '')
    if 'taichi' in task_lower or 'tai_chi' in task_lower:
        return ('functional_task', 'taichi', 'category:martial_arts')
    if 'lambada' in task_lower or 'dance' in task_lower:
        return ('functional_task', 'dance', 'category:dance')
    if 'high_leg' in task_lower or 'highleg' in task_lower:
        return ('functional_task', 'high_leg', '')

    # Sports
    if 'swing' in task_lower or 'tennis' in task_lower:
        return ('functional_task', 'tennis_swing', 'category:sports')
    if 'serv' in task_lower:
        return ('functional_task', 'tennis_serve', 'category:sports')
    if 'kick' in task_lower or 'soccer' in task_lower:
        return ('functional_task', 'soccer_kick', 'category:sports')

    # Static
    if 'stand' in task_lower or 'idle' in task_lower or 'casual' in task_lower:
        return ('balance_pose', 'casual_stand', '')

    return ('functional_task', original_task, '')


def get_task_info_tiziana2019(original_task: str) -> Tuple[str, str, str]:
    """
    Map Tiziana2019 (Lencioni) task to standard format.
    Dataset has 50 subjects (ages 6-72) doing walking variants and stairs.
    Tasks: walking (multiple speeds), toe-walking, heel-walking, stair up/down.
    """
    task_lower = original_task.lower()

    # Stair tasks
    if 'stair' in task_lower or task_lower in ['u', 'up']:
        if 'down' in task_lower or 'd' in task_lower:
            return ('stair_descent', 'stair_descent', '')
        return ('stair_ascent', 'stair_ascent', '')

    # Modified walking (dynamic walk variants)
    if 'toe' in task_lower or task_lower == 't':
        return ('dynamic_walk', 'toe_walking', 'variant:toe_walking')
    if 'heel' in task_lower or task_lower == 'h':
        return ('dynamic_walk', 'heel_walking', 'variant:heel_walking')

    # Level walking (various speeds)
    if 'fast' in task_lower:
        return ('level_walking', 'level_fast', 'speed:fast')
    if 'slow' in task_lower:
        return ('level_walking', 'level_slow', 'speed:slow')

    # Default to level walking
    return ('level_walking', 'level', '')


def get_task_info_carter2023(original_task: str) -> Tuple[str, str, str]:
    """
    Map Carter2023 task to standard format.
    Dataset has 50 runners on treadmill at various speeds and gradients.
    Conditions: walking, running, flat/uphill/downhill.
    """
    task_lower = original_task.lower()

    # Determine gradient
    gradient = 'flat'
    gradient_info = ''
    if 'uphill' in task_lower or 'incline' in task_lower or 'up' in task_lower:
        gradient = 'uphill'
        gradient_info = 'gradient:uphill'
    elif 'downhill' in task_lower or 'decline' in task_lower or 'down' in task_lower:
        gradient = 'downhill'
        gradient_info = 'gradient:downhill'
    else:
        gradient_info = 'gradient:flat'

    # Determine activity type
    if 'walk' in task_lower:
        if gradient == 'uphill':
            return ('incline_walking', f'incline_{gradient}', gradient_info)
        elif gradient == 'downhill':
            return ('decline_walking', f'decline_{gradient}', gradient_info)
        return ('level_walking', 'level', gradient_info)

    # Default to running (primary activity in dataset)
    if gradient == 'uphill':
        return ('run', f'run_{gradient}', f'{gradient_info},treadmill:true')
    elif gradient == 'downhill':
        return ('run', f'run_{gradient}', f'{gradient_info},treadmill:true')

    return ('run', 'run', 'treadmill:true')


# Mapping from dataset name to task info function
_TASK_INFO_FUNCTIONS = {
    'Moore2015': get_task_info_moore2015,
    # 'Camargo2021': get_task_info_camargo2021,  # Skipped - use GT21 instead
    'Fregly2012': get_task_info_fregly2012,
    'Hamner2013': get_task_info_hamner2013,
    'Santos2017': get_task_info_santos2017,
    'Tan2021': get_task_info_tan2021,
    'Tan2022': get_task_info_tan2022,
    'vanderZee2022': get_task_info_vanderzee2022,
    'Wang2023': get_task_info_wang2023,
    # Previously missing datasets - now supported
    'Falisse2016': get_task_info_falisse2016,
    'Han2023': get_task_info_han2023,
    'Tiziana2019': get_task_info_tiziana2019,
    'Carter2023': get_task_info_carter2023,
}

# Tasks that should use phase normalization (cyclic gait tasks)
# From docs/reference/index.md - Phase-Friendly Families
CYCLIC_TASKS = {
    'level_walking', 'incline_walking', 'decline_walking',
    'stair_ascent', 'stair_descent', 'run',
    'sit_to_stand', 'stand_to_sit', 'squat', 'jump', 'hop', 'lunge',
    'step_up', 'step_down', 'walk_backward',
    'weighted_walk', 'dynamic_walk', 'transition',
}

# Tasks that should remain time-indexed only
# From docs/reference/index.md - Time-Indexed (Non-Cyclic) Families
NON_CYCLIC_TASKS = {
    'agility_drill', 'cutting', 'free_walk_episode',
    'load_handling', 'perturbation', 'balance_pose', 'functional_task',
}


def get_task_info(dataset: str, original_task: str) -> Tuple[str, str, str]:
    """
    Get standardized task info for a dataset and original task name.

    Args:
        dataset: Dataset name (e.g., 'Moore2015')
        original_task: Original task name from the B3D file

    Returns:
        Tuple of (standard_task, task_id, task_info)
    """
    if dataset not in _TASK_INFO_FUNCTIONS:
        raise ValueError(f"Unknown dataset: {dataset}. "
                        f"Valid datasets: {list(_TASK_INFO_FUNCTIONS.keys())}")

    return _TASK_INFO_FUNCTIONS[dataset](original_task)


def get_subject_name(dataset: str, original_name: str, subject_idx: int) -> str:
    """
    Generate standardized subject name.

    Args:
        dataset: Dataset name
        original_name: Original subject name from B3D file
        subject_idx: Subject index (0-based)

    Returns:
        Standardized subject name (e.g., 'MO15_AB01')
    """
    short_code = DATASET_SHORT_CODES.get(dataset, 'XX')
    # Assume able-bodied unless otherwise specified
    population = 'AB'
    subject_num = f'{subject_idx + 1:02d}'
    return f'{short_code}_{population}{subject_num}'


def is_cyclic_task(task: str) -> bool:
    """Check if a task should be phase-normalized."""
    return task in CYCLIC_TASKS


def get_supported_datasets() -> list:
    """Return list of supported dataset names."""
    return list(DATASET_SHORT_CODES.keys())
