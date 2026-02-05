"""
Task mapping for GaTech 2025 Domain Adaptation dataset.

Maps the 6 activity categories from the source dataset to standardized task names.

Source: Scherpereel et al., "Deep Domain Adaptation Eliminates Costly Data Required
for Task-Agnostic Wearable Robotic Control" (Science Robotics, 2025)

Source activity naming convention:
  <base_task>_<vicon_trial>_<descriptor>_<model_abbreviation>
  Model abbreviations: baseline, 4t4s, 0task

Task descriptions (from readme):
  ball_toss: Tossing 15 lbs medicine ball (center/left/right)
  cutting: Jog/Run into sharp turn (left/right, fast/slow)
  normal_walk: Level treadmill walking (0.6/1.2/1.8 m/s + shuffle at 0.4 m/s)
  stairs: Walking up and down stairs (up/down)
  start_stop: Starting and stopping walking on overground force plates
  walk_backward: Walking backward on treadmill (0.6/0.8/1.0 m/s)
  sit_to_stand: Sit-to-stand transfers (short-arm/short-noarm/tall-noarm)
"""

from typing import Dict, Tuple, Optional
import re

# Full task mapping with metadata
# Key: regex pattern matching task folder names
# Value: (standard_task, task_id_template, additional_info)
FULL_TASK_MAPPING: Dict[str, Tuple[str, str, Dict]] = {
    # Level walking at different speeds
    r'normal_walk.*_0-6': ('level_walking', 'level_0.6ms', {'speed_m_s': 0.6, 'incline_deg': 0.0, 'surface': 'treadmill'}),
    r'normal_walk.*_1-2': ('level_walking', 'level_1.2ms', {'speed_m_s': 1.2, 'incline_deg': 0.0, 'surface': 'treadmill'}),
    r'normal_walk.*_1-8': ('level_walking', 'level_1.8ms', {'speed_m_s': 1.8, 'incline_deg': 0.0, 'surface': 'treadmill'}),
    # Shuffle is lateral, exclude from standard tasks
    r'normal_walk.*_shuffle': (None, 'shuffle', {'speed_m_s': 0.4, 'incline_deg': 0.0, 'surface': 'treadmill'}),

    # Stairs
    r'stairs.*_up': ('stair_ascent', 'stair_ascent', {'incline_deg': 0.0, 'surface': 'stairs'}),
    r'stairs.*_down': ('stair_descent', 'stair_descent', {'incline_deg': 0.0, 'surface': 'stairs'}),

    # Backward walking
    r'walk_backward.*_0-6': ('backward_walking', 'backward_0.6ms', {'speed_m_s': 0.6, 'incline_deg': 0.0, 'surface': 'treadmill'}),
    r'walk_backward.*_0-8': ('backward_walking', 'backward_0.8ms', {'speed_m_s': 0.8, 'incline_deg': 0.0, 'surface': 'treadmill'}),
    r'walk_backward.*_1-0': ('backward_walking', 'backward_1.0ms', {'speed_m_s': 1.0, 'incline_deg': 0.0, 'surface': 'treadmill'}),

    # Sit-to-stand variations
    r'sit_to_stand.*_short-arm': ('sit_to_stand', 'sit_stand_short_arm', {'incline_deg': 0.0, 'chair': 'short', 'arm_rest': True}),
    r'sit_to_stand.*_short-noarm': ('sit_to_stand', 'sit_stand_short_noarm', {'incline_deg': 0.0, 'chair': 'short', 'arm_rest': False}),
    r'sit_to_stand.*_tall-noarm': ('sit_to_stand', 'sit_stand_tall_noarm', {'incline_deg': 0.0, 'chair': 'tall', 'arm_rest': False}),

    # Cutting (direction changes) - non-cyclic, exclude from standard tasks
    r'cutting.*_left-fast': (None, 'cut_left_fast', {'incline_deg': 0.0, 'direction': 'left', 'speed': 'fast'}),
    r'cutting.*_left-slow': (None, 'cut_left_slow', {'incline_deg': 0.0, 'direction': 'left', 'speed': 'slow'}),
    r'cutting.*_right-fast': (None, 'cut_right_fast', {'incline_deg': 0.0, 'direction': 'right', 'speed': 'fast'}),
    r'cutting.*_right-slow': (None, 'cut_right_slow', {'incline_deg': 0.0, 'direction': 'right', 'speed': 'slow'}),

    # Ball toss - non-cyclic, exclude
    r'ball_toss.*_center': (None, 'ball_toss_center', {'incline_deg': 0.0}),
    r'ball_toss.*_left': (None, 'ball_toss_left', {'incline_deg': 0.0}),
    r'ball_toss.*_right': (None, 'ball_toss_right', {'incline_deg': 0.0}),

    # Start/stop - transitions, exclude
    r'start_stop': (None, 'start_stop', {'incline_deg': 0.0, 'surface': 'overground'}),
}


def map_task(task_folder: str) -> Tuple[Optional[str], Optional[str], Dict]:
    """
    Map a task folder name to standardized task name, ID, and metadata.

    Args:
        task_folder: Source folder name (e.g., 'normal_walk_1_1_1-2_baseline')

    Returns:
        Tuple of (task_name, task_id, task_info_dict) or (None, None, {}) if not mapped
    """
    for pattern, (task_name, task_id, base_info) in FULL_TASK_MAPPING.items():
        if re.search(pattern, task_folder):
            info = base_info.copy()
            return task_name, task_id, info

    return None, None, {}


def get_supported_tasks() -> list:
    """Return list of standard task names supported by this dataset."""
    tasks = set()
    for _, (task_name, _, _) in FULL_TASK_MAPPING.items():
        if task_name is not None:
            tasks.add(task_name)
    return sorted(list(tasks))
