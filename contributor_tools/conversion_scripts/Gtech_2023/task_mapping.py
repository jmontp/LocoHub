"""
Task mapping utility for Gtech_2023 dataset conversion.

Maps Gtech activity names to standardized task hierarchy following the 
three-level system: task, task_id, task_info.
"""

import re
from typing import Tuple, Dict, Any

def parse_gtech_activity_name(activity_name: str) -> Tuple[str, str, str]:
    """
    Parse Gtech activity name into standardized task hierarchy.
    
    Args:
        activity_name: Raw activity name from Gtech dataset (e.g., "normal_walk_1_1-2")
    
    Returns:
        Tuple of (task, task_id, task_info)
    """
    
    # Basic activity type mapping
    activity_mappings = {
        'normal_walk': 'level_walking',
        'incline_walk': 'incline_walking',  # Will be refined based on up/down
        'stairs': 'stair_ascent',  # Will be refined based on up/down
        'jump': 'jump',
        'squats': 'squats',
        'sit_to_stand': 'sit_to_stand',
        'stand_to_sit': 'stand_to_sit',
        'curb_up': 'step_up',
        'curb_down': 'step_down',
        'ball_toss': 'functional_task',
        'cutting': 'functional_task',
        'dynamic_walk': 'level_walking',  # Dynamic variations of walking
        'lift_weight': 'functional_task',
        'lunges': 'functional_task',
        'side_shuffle': 'functional_task',
        'step_ups': 'step_up',
        'tire_run': 'functional_task',
        'turn_and_step': 'functional_task',
        'walk_backward': 'backward_walking',
        'weighted_walk': 'level_walking'
    }
    
    # Parse activity name components
    parts = activity_name.split('_')
    
    # Extract base activity type
    base_activity = None
    activity_number = None
    sub_activity = None
    
    # Find the first numeric part to split activity type from parameters
    for i, part in enumerate(parts):
        if re.match(r'^\d+$', part):
            base_activity = '_'.join(parts[:i])
            activity_number = int(part)
            if i + 1 < len(parts):
                sub_activity = '_'.join(parts[i+1:])
            break
    
    if base_activity is None:
        # No numeric part found, treat entire string as activity
        base_activity = activity_name
        activity_number = 1
        sub_activity = ""
    
    # Get standardized task name
    task = activity_mappings.get(base_activity, 'functional_task')
    
    # Handle special cases and extract parameters
    task_info_dict = {}
    task_id = None
    
    if base_activity == 'normal_walk':
        # Extract speed from sub_activity (e.g., "1-2" -> 1.2 m/s, "0-6" -> 0.6 m/s)
        if sub_activity:
            speed_match = re.match(r'(\d+)-(\d+)', sub_activity)
            if speed_match:
                speed = float(f"{speed_match.group(1)}.{speed_match.group(2)}")
                task_info_dict['speed_m_s'] = speed
            elif sub_activity in ['shuffle', 'skip']:
                task_info_dict['variant'] = sub_activity
        
        task_id = 'level'
        task_info_dict['treadmill'] = True  # Assume treadmill for Gtech data
    
    elif base_activity == 'incline_walk':
        # Extract incline info (e.g., "up5", "down10")
        if sub_activity:
            if 'up' in sub_activity:
                incline_match = re.search(r'up(\d+)', sub_activity)
                if incline_match:
                    incline = int(incline_match.group(1))
                    task_info_dict['incline_deg'] = incline
                    task_id = f'incline_{incline}deg'
            elif 'down' in sub_activity:
                task = 'decline_walking'
                incline_match = re.search(r'down(\d+)', sub_activity)
                if incline_match:
                    incline = int(incline_match.group(1))
                    task_info_dict['incline_deg'] = -incline
                    task_id = f'decline_{incline}deg'
        
        if task_id is None:
            task_id = 'incline'
        
        task_info_dict['treadmill'] = True
    
    elif base_activity == 'stairs':
        # Determine ascent vs descent from sub_activity
        if sub_activity:
            if 'up' in sub_activity:
                task = 'stair_ascent'
                task_id = 'stair_ascent'
            elif 'down' in sub_activity:
                task = 'stair_descent'
                task_id = 'stair_descent'
            
            # Extract step number if present
            step_match = re.search(r'(\d+)', sub_activity)
            if step_match:
                task_info_dict['step_number'] = int(step_match.group(1))
        
        if task_id is None:
            task_id = 'stair_ascent'  # Default
        
        # Typical stair parameters for Gtech dataset
        task_info_dict['height_m'] = 0.15  # Typical step height
    
    elif base_activity == 'sit_to_stand':
        task_id = 'sit_to_stand'
        if sub_activity:
            if 'short' in sub_activity:
                task_info_dict['chair_height'] = 'low'
            elif 'tall' in sub_activity:
                task_info_dict['chair_height'] = 'standard'
            if 'arm' in sub_activity:
                task_info_dict['armrests'] = True
            elif 'noarm' in sub_activity:
                task_info_dict['armrests'] = False
    
    elif base_activity == 'squats':
        task_id = 'squats'
        if sub_activity:
            # Extract weight info (e.g., "25lbs", "0lbs")
            weight_match = re.search(r'(\d+)lbs', sub_activity)
            if weight_match:
                weight_lbs = int(weight_match.group(1))
                task_info_dict['weight_kg'] = round(weight_lbs * 0.453592, 1)
    
    elif base_activity == 'jump':
        task_id = 'jump'
        if sub_activity:
            if 'vertical' in sub_activity:
                task_info_dict['jump_type'] = 'vertical'
            elif 'fb' in sub_activity:
                task_info_dict['jump_type'] = 'forward_backward'
            elif 'lateral' in sub_activity:
                task_info_dict['jump_type'] = 'lateral'
            elif 'hop' in sub_activity:
                task_info_dict['jump_type'] = 'hop'
            elif '180' in sub_activity:
                task_info_dict['jump_type'] = 'turn_180'
    
    elif base_activity == 'dynamic_walk':
        # Special walking variants
        task = 'level_walking'
        task_id = 'level'
        if sub_activity:
            task_info_dict['variant'] = sub_activity
            task_info_dict['treadmill'] = True
    
    elif base_activity == 'weighted_walk':
        task = 'level_walking'
        task_id = 'level'
        if sub_activity:
            weight_match = re.search(r'(\d+)lbs', sub_activity)
            if weight_match:
                weight_lbs = int(weight_match.group(1))
                task_info_dict['weight_kg'] = round(weight_lbs * 0.453592, 1)
        task_info_dict['treadmill'] = True
    
    elif base_activity == 'walk_backward':
        task = 'backward_walking'
        task_id = 'backward'
        if sub_activity:
            speed_match = re.match(r'(\d+)-(\d+)', sub_activity)
            if speed_match:
                speed = float(f"{speed_match.group(1)}.{speed_match.group(2)}")
                task_info_dict['speed_m_s'] = speed
        task_info_dict['treadmill'] = True
    
    else:
        # Generic functional task
        task_id = base_activity
        if sub_activity:
            task_info_dict['variant'] = sub_activity
    
    # Set default task_id if not set
    if task_id is None:
        task_id = base_activity
    
    # Format task_info string
    task_info = ','.join([f"{k}:{v}" for k, v in task_info_dict.items() if v is not None])
    
    return task, task_id, task_info


def get_subject_metadata(subject_name: str) -> str:
    """
    Generate subject metadata string for Gtech dataset.
    
    Args:
        subject_name: Subject identifier (e.g., "GT23_AB01")
    
    Returns:
        Formatted subject metadata string
    """
    # For now, return empty string as subject-specific metadata 
    # would need to be loaded from external source
    # Could be enhanced to load from Subject_masses.csv or other metadata files
    return ""


def standardize_gtech_task_info(task: str, task_id: str, raw_activity: str) -> str:
    """
    Generate standardized task_info for common Gtech tasks.
    
    This function can be used to ensure consistent metadata formatting
    across the dataset.
    """
    _, _, task_info = parse_gtech_activity_name(raw_activity)
    return task_info


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_activities = [
        "normal_walk_1_1-2",
        "incline_walk_1_up5", 
        "incline_walk_2_down10",
        "stairs_1_1_up",
        "stairs_1_2_down",
        "sit_to_stand_1_short-arm",
        "squats_1_25lbs",
        "jump_1_vertical",
        "dynamic_walk_1_butt-kicks",
        "walk_backward_1_0-6"
    ]
    
    print("Testing Gtech activity name parsing:")
    print("-" * 60)
    for activity in test_activities:
        task, task_id, task_info = parse_gtech_activity_name(activity)
        print(f"'{activity}' -> task='{task}', task_id='{task_id}', task_info='{task_info}'")