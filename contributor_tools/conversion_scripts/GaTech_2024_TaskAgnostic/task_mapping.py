"""
Task mapping for GaTech 2024 TaskAgnostic dataset.

Maps the 28 activities from the source dataset to standardized task names.

Source activity naming convention:
  <base_task>_<vicon_trial>_<descriptor>_<exo_on_off>

Examples:
  normal_walk_1_1_1-2_on  -> level_walking at 1.2 m/s, exo powered
  stairs_1_1_3_up_on      -> stair_ascent, exo powered
  incline_walk_2_1_up10_off -> incline_walking at 10deg, exo unpowered
"""

from typing import Dict, Tuple, Optional
import re

# Full task mapping with metadata
# Key: regex pattern
# Value: (standard_task, task_id_template, additional_info)
FULL_TASK_MAPPING: Dict[str, Tuple[str, str, Dict]] = {
    # Level walking at different speeds
    r'normal_walk.*_0-6': ('level_walking', 'level_0.6ms', {'speed_m_s': 0.6, 'surface': 'treadmill'}),
    r'normal_walk.*_1-2': ('level_walking', 'level_1.2ms', {'speed_m_s': 1.2, 'surface': 'treadmill'}),
    r'normal_walk.*_1-8': ('level_walking', 'level_1.8ms', {'speed_m_s': 1.8, 'surface': 'treadmill'}),
    r'normal_walk.*_2-0': ('level_walking', 'level_2.0ms', {'speed_m_s': 2.0, 'surface': 'treadmill'}),
    r'normal_walk.*_2-5': ('level_walking', 'level_2.5ms', {'speed_m_s': 2.5, 'surface': 'treadmill'}),
    r'normal_walk.*_shuffle': ('level_walking', 'shuffle', {'speed_m_s': 0.4, 'surface': 'treadmill', 'gait_type': 'shuffle'}),
    r'normal_walk.*_skip': ('level_walking', 'skip', {'speed_m_s': 1.2, 'surface': 'treadmill', 'gait_type': 'skip'}),

    # Incline/decline walking
    r'incline_walk.*_up5': ('incline_walking', 'incline_5deg', {'incline_deg': 5.0, 'speed_m_s': 1.2, 'surface': 'treadmill'}),
    r'incline_walk.*_up10': ('incline_walking', 'incline_10deg', {'incline_deg': 10.0, 'speed_m_s': 1.2, 'surface': 'treadmill'}),
    r'incline_walk.*_down5': ('decline_walking', 'decline_5deg', {'incline_deg': -5.0, 'speed_m_s': 1.2, 'surface': 'treadmill'}),
    r'incline_walk.*_down10': ('decline_walking', 'decline_10deg', {'incline_deg': -10.0, 'speed_m_s': 1.2, 'surface': 'treadmill'}),

    # Stairs
    r'stairs.*_up': ('stair_ascent', 'stair_ascent', {'surface': 'stairs'}),
    r'stairs.*_down': ('stair_descent', 'stair_descent', {'surface': 'stairs'}),

    # Curb (small step)
    r'curb_up': ('stair_ascent', 'curb_up', {'surface': 'curb', 'step_type': 'curb'}),
    r'curb_down': ('stair_descent', 'curb_down', {'surface': 'curb', 'step_type': 'curb'}),

    # Step ups (onto platform)
    r'step_ups.*_left': ('stair_ascent', 'step_up_left', {'surface': 'platform', 'leading_leg': 'left'}),
    r'step_ups.*_right': ('stair_ascent', 'step_up_right', {'surface': 'platform', 'leading_leg': 'right'}),

    # Backward walking
    r'walk_backward.*_0-6': ('backward_walking', 'backward_0.6ms', {'speed_m_s': 0.6, 'surface': 'treadmill'}),
    r'walk_backward.*_0-8': ('backward_walking', 'backward_0.8ms', {'speed_m_s': 0.8, 'surface': 'treadmill'}),
    r'walk_backward.*_1-0': ('backward_walking', 'backward_1.0ms', {'speed_m_s': 1.0, 'surface': 'treadmill'}),

    # Weighted walking
    r'weighted_walk.*_25lbs': ('level_walking', 'weighted_25lbs', {'speed_m_s': 1.0, 'surface': 'treadmill', 'weight_lbs': 25}),

    # Dynamic walking (calisthenics)
    r'dynamic_walk.*_butt-kicks': ('level_walking', 'butt_kicks', {'speed_m_s': 0.8, 'surface': 'treadmill', 'gait_type': 'butt_kicks'}),
    r'dynamic_walk.*_high-knees': ('level_walking', 'high_knees', {'speed_m_s': 0.8, 'surface': 'treadmill', 'gait_type': 'high_knees'}),
    r'dynamic_walk.*_heel-walk': ('level_walking', 'heel_walk', {'speed_m_s': 0.4, 'surface': 'treadmill', 'gait_type': 'heel_walk'}),
    r'dynamic_walk.*_toe-walk': ('level_walking', 'toe_walk', {'speed_m_s': 0.4, 'surface': 'treadmill', 'gait_type': 'toe_walk'}),

    # Sit-to-stand variations
    r'sit_to_stand.*_short-arm': ('sit_to_stand', 'sit_stand_short_arm', {'chair': 'short', 'arm_rest': True}),
    r'sit_to_stand.*_short-noarm': ('sit_to_stand', 'sit_stand_short_noarm', {'chair': 'short', 'arm_rest': False}),
    r'sit_to_stand.*_tall-noarm': ('sit_to_stand', 'sit_stand_tall_noarm', {'chair': 'tall', 'arm_rest': False}),

    # Squats
    r'squats.*_0lbs': ('squat', 'squat_bodyweight', {'weight_lbs': 0}),
    r'squats.*_25lbs': ('squat', 'squat_25lbs', {'weight_lbs': 25}),

    # Jumping
    r'jump.*_fb': ('jump', 'jump_forward_backward', {'jump_type': 'forward_backward'}),
    r'jump.*_hop': ('jump', 'jump_hop', {'jump_type': 'hop'}),
    r'jump.*_vertical': ('jump', 'jump_vertical', {'jump_type': 'vertical'}),
    r'jump.*_lateral': ('jump', 'jump_lateral', {'jump_type': 'lateral'}),
    r'jump.*_90': ('jump', 'jump_90deg', {'jump_type': 'rotational_90'}),
    r'jump.*_180': ('jump', 'jump_180deg', {'jump_type': 'rotational_180'}),

    # Lunges
    r'lunges.*_set': ('lunge', 'lunge', {'lunge_type': 'forward_backward'}),
    r'lunges.*_left': ('lunge', 'lunge_lateral_left', {'lunge_type': 'lateral', 'direction': 'left'}),
    r'lunges.*_right': ('lunge', 'lunge_lateral_right', {'lunge_type': 'lateral', 'direction': 'right'}),

    # Cutting (direction changes)
    r'cutting.*_left-fast': ('cutting', 'cut_left_fast', {'direction': 'left', 'speed': 'fast'}),
    r'cutting.*_left-slow': ('cutting', 'cut_left_slow', {'direction': 'left', 'speed': 'slow'}),
    r'cutting.*_right-fast': ('cutting', 'cut_right_fast', {'direction': 'right', 'speed': 'fast'}),
    r'cutting.*_right-slow': ('cutting', 'cut_right_slow', {'direction': 'right', 'speed': 'slow'}),

    # Overground activities
    r'meander': ('level_walking', 'meander', {'surface': 'overground', 'gait_type': 'freeform'}),
    r'obstacle_walk': ('level_walking', 'obstacle_walk', {'surface': 'treadmill', 'obstacle': True}),
    r'start_stop': ('transition', 'start_stop', {'surface': 'overground'}),
    r'turn_and_step.*_left': ('transition', 'turn_left', {'surface': 'overground', 'direction': 'left'}),
    r'turn_and_step.*_right': ('transition', 'turn_right', {'surface': 'overground', 'direction': 'right'}),

    # Other activities
    r'side_shuffle': ('level_walking', 'side_shuffle', {'gait_type': 'side_shuffle'}),
    r'tire_run': ('level_walking', 'tire_run', {'gait_type': 'tire_run'}),
    r'ball_toss': ('functional', 'ball_toss', {'activity': 'ball_toss'}),
    r'lift_weight': ('functional', 'lift_weight', {'activity': 'lifting'}),
    r'poses': ('standing', 'poses', {'activity': 'static_poses'}),
    r'push': ('functional', 'push', {'activity': 'push_pull'}),
    r'tug_of_war': ('functional', 'tug_of_war', {'activity': 'push_pull'}),
    r'twister': ('functional', 'twister', {'activity': 'twister'}),
}

# Activities that should be skipped (non-cyclic or special)
SKIP_TASKS = [
    'poses',  # Static postures, no gait cycles
    'push',   # External perturbations
    'tug_of_war',
    'twister',
    'ball_toss',
    'lift_weight',
]

# Activities with clear gait cycles
CYCLIC_TASKS = [
    'normal_walk',
    'incline_walk',
    'walk_backward',
    'weighted_walk',
    'dynamic_walk',
    'stairs',
    'meander',
    'side_shuffle',
]


def map_task(task_folder: str) -> Tuple[Optional[str], Optional[str], Dict]:
    """
    Map a task folder name to standardized task name, ID, and metadata.

    Args:
        task_folder: Source folder name (e.g., 'normal_walk_1_1_1-2_on')

    Returns:
        Tuple of (task_name, task_id, task_info_dict) or (None, None, {}) if not mapped
    """
    # Check for skip tasks
    for skip in SKIP_TASKS:
        if skip in task_folder:
            return None, None, {}

    # Check exo status
    exo_powered = None
    if '_on' in task_folder:
        exo_powered = True
    elif '_off' in task_folder:
        exo_powered = False

    # Find matching pattern
    for pattern, (task_name, task_id, base_info) in FULL_TASK_MAPPING.items():
        if re.search(pattern, task_folder):
            info = base_info.copy()
            info['exo_powered'] = exo_powered
            return task_name, task_id, info

    return None, None, {'exo_powered': exo_powered}


def get_supported_tasks() -> list:
    """Return list of standard task names supported by this dataset."""
    tasks = set()
    for _, (task_name, _, _) in FULL_TASK_MAPPING.items():
        tasks.add(task_name)
    return sorted(list(tasks))


def is_cyclic_task(task_folder: str) -> bool:
    """Check if a task folder represents a cyclic gait activity."""
    for cyclic in CYCLIC_TASKS:
        if cyclic in task_folder:
            return True
    return False
