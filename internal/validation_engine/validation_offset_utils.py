#!/usr/bin/env python3
"""
Validation Offset Utilities

Utility functions for applying contralateral offset logic and validation completeness checks.
These functions are used by various validation components.

Extracted from the original validation_expectations_parser.py to maintain essential
functionality after migration to YAML config system.
"""

from typing import Dict, List, Optional
from pathlib import Path
import sys

# Add source directory to Python path for feature constants
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source'))


def apply_contralateral_offset_kinematic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]], 
    task_name: str = None
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Apply contralateral offset logic for kinematic variables.
    
    For gait-based tasks, the contralateral leg is 50% out of phase:
    - Phase 0% ipsilateral = Phase 50% contralateral
    - Phase 25% ipsilateral = Phase 75% contralateral
    - Phase 50% ipsilateral = Phase 0% contralateral
    - Phase 75% ipsilateral = Phase 25% contralateral
    
    Args:
        phase_data: Dictionary with phase percentages as keys
        task_name: Name of the task (for determining if offset should apply)
        
    Returns:
        Dictionary with contralateral variables added based on offset logic
    """
    # Gait-based tasks where contralateral offset applies
    gait_tasks = [
        'level_walking', 'incline_walking', 'decline_walking',
        'stair_ascent', 'stair_descent', 'running', 'sprinting'
    ]
    
    # Check if this is a gait task
    is_gait_task = task_name and any(task in task_name.lower() for task in gait_tasks)
    
    if not is_gait_task:
        return phase_data
    
    # Create a copy to avoid modifying the original
    result = {}
    
    # Phase offset mapping for contralateral leg
    phase_offset_map = {
        0: 50,
        25: 75,
        50: 0,
        75: 25,
        95: 45  # Special case for 95% phase if present
    }
    
    for phase_pct, variables in phase_data.items():
        result[phase_pct] = {}
        
        # Copy all ipsilateral variables
        for var_name, var_range in variables.items():
            if '_ipsi' in var_name:
                result[phase_pct][var_name] = var_range.copy()
        
        # Add contralateral variables from offset phase
        if phase_pct in phase_offset_map:
            offset_phase = phase_offset_map[phase_pct]
            if offset_phase in phase_data:
                for var_name, var_range in phase_data[offset_phase].items():
                    if '_ipsi' in var_name:
                        # Create contralateral version
                        contra_name = var_name.replace('_ipsi', '_contra')
                        result[phase_pct][contra_name] = var_range.copy()
    
    return result


def apply_contralateral_offset_kinetic(
    phase_data: Dict[int, Dict[str, Dict[str, float]]],
    task_name: str = None
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Apply contralateral offset logic for kinetic variables.
    
    For gait-based tasks, the contralateral leg is 50% out of phase.
    Same logic as kinematic but for force/moment variables.
    
    Args:
        phase_data: Dictionary with phase percentages as keys
        task_name: Name of the task
        
    Returns:
        Dictionary with contralateral variables added
    """
    # Gait-based tasks where contralateral offset applies
    gait_tasks = [
        'level_walking', 'incline_walking', 'decline_walking',
        'stair_ascent', 'stair_descent', 'running', 'sprinting'
    ]
    
    # Check if this is a gait task
    is_gait_task = task_name and any(task in task_name.lower() for task in gait_tasks)
    
    if not is_gait_task:
        return phase_data
    
    # Create a copy to avoid modifying the original
    result = {}
    
    # Phase offset mapping for contralateral leg
    phase_offset_map = {
        0: 50,
        25: 75,
        50: 0,
        75: 25,
        95: 45  # Special case for 95% phase if present
    }
    
    for phase_pct, variables in phase_data.items():
        result[phase_pct] = {}
        
        # Copy all ipsilateral variables
        for var_name, var_range in variables.items():
            if '_ipsi' in var_name:
                result[phase_pct][var_name] = var_range.copy()
        
        # Add contralateral variables from offset phase
        if phase_pct in phase_offset_map:
            offset_phase = phase_offset_map[phase_pct]
            if offset_phase in phase_data:
                for var_name, var_range in phase_data[offset_phase].items():
                    if '_ipsi' in var_name:
                        # Create contralateral version
                        contra_name = var_name.replace('_ipsi', '_contra')
                        result[phase_pct][contra_name] = var_range.copy()
    
    return result


def validate_task_completeness(
    phase_data: Dict[int, Dict[str, Dict[str, float]]],
    task_name: str,
    mode: str
) -> bool:
    """
    Validate that a task has complete phase and variable coverage.
    
    Args:
        phase_data: Dictionary with phase data
        task_name: Name of the task
        mode: 'kinematic' or 'kinetic'
        
    Returns:
        True if validation passes
    """
    required_phases = [0, 25, 50, 75]
    
    # Check required phases exist
    for phase in required_phases:
        if phase not in phase_data:
            print(f"⚠️  Warning: Task '{task_name}' missing phase {phase}% in {mode} validation")
            return False
    
    # Check each phase has variables
    for phase in required_phases:
        if not phase_data[phase]:
            print(f"⚠️  Warning: Task '{task_name}' has no variables at phase {phase}% in {mode} validation")
            return False
    
    return True