#!/usr/bin/env python3
"""
Validation Expectations Parser

Parses validation expectations from markdown files to extract validation ranges.
Supports both kinematic (joint angles) and kinetic (forces/moments) validation data.
"""

import re
from typing import Dict
from pathlib import Path


def extract_numeric_value(value_str: str) -> float:
    """
    Extract numeric value from a string that may contain degree annotations.
    
    Args:
        value_str: String containing numeric value (e.g., "0.1", "-0.5")
        
    Returns:
        Extracted numeric value as float
        
    Raises:
        ValueError: If no numeric value can be extracted
    """
    # Remove any whitespace
    value_str = value_str.strip()
    
    # Extract the first number found (handles negative numbers)
    match = re.search(r'-?\d*\.?\d+', value_str)
    if match:
        return float(match.group())
    else:
        # Fail explicitly instead of returning 0
        raise ValueError(f"Could not extract numeric value from '{value_str}'")


def validate_task_completeness(task_data: Dict, task_name: str, mode: str) -> None:
    """
    Validate that task data contains all required phases and variables.
    
    Args:
        task_data: Task validation data 
        task_name: Name of the task
        mode: 'kinematic' or 'kinetic'
        
    Raises:
        ValueError: If required validation data is missing
    """
    required_phases = [0, 25, 50, 75]  # Don't require 100% as it's computed
    
    if mode == 'kinematic':
        required_variables = [
            'hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
            'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra', 
            'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra'
        ]
    else:  # kinetic
        required_variables = [
            'hip_moment_ipsi_Nm_kg', 'hip_moment_contra_Nm_kg',
            'knee_moment_ipsi_Nm_kg', 'knee_moment_contra_Nm_kg',
            'ankle_moment_ipsi_Nm_kg', 'ankle_moment_contra_Nm_kg'
        ]
    
    # Check that all required phases exist
    missing_phases = [phase for phase in required_phases if phase not in task_data]
    if missing_phases:
        raise ValueError(f"Task '{task_name}' missing required phases: {missing_phases}")
    
    # Check that all required variables exist in each phase
    for phase in required_phases:
        if phase in task_data:
            missing_vars = [var for var in required_variables if var not in task_data[phase]]
            if missing_vars:
                raise ValueError(f"Task '{task_name}' phase {phase}% missing required variables: {missing_vars}")
            
            # Check that each variable has both min and max values
            for var in required_variables:
                if var in task_data[phase]:
                    var_data = task_data[phase][var]
                    if not isinstance(var_data, dict) or 'min' not in var_data or 'max' not in var_data:
                        raise ValueError(f"Task '{task_name}' phase {phase}% variable '{var}' missing 'min' or 'max' values")


def parse_kinematic_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations_kinematic.md file to extract joint angle ranges.
    
    Args:
        file_path: Path to the validation_expectations_kinematic.md file
        
    Returns:
        Dictionary structured as: {task_name: {phase: {joint: {min, max}}}}
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Dictionary to store parsed data
    validation_data = {}
    
    # Find all task sections
    task_pattern = r'### Task: ([\w_]+)\n'
    tasks = re.findall(task_pattern, content)
    
    for task in tasks:
        validation_data[task] = {}
        
        # Find the task section
        task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## ✅ \*\*MAJOR UPDATE COMPLETED\*\*|## Joint Validation Range Summary|## Pattern Definitions|$)'
        task_match = re.search(task_section_pattern, content, re.DOTALL)
        
        if task_match:
            task_content = task_match.group(1)
            
            # Find all phase sections within this task
            phase_pattern = r'#### Phase (\d+)%.*?\n\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=####|\*\*Contralateral|\*\*Note:|\*\*Forward|$)'
            phase_matches = re.findall(phase_pattern, task_content, re.DOTALL)
            
            for phase_str, table_content in phase_matches:
                phase = int(phase_str)
                validation_data[task][phase] = {}
                
                # Parse table rows for joint angles - Updated to handle degree format
                row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \([^)]+\) \| ([-\d.]+) \([^)]+\) \| (\w+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for variable, min_val, max_val, unit in rows:
                    # Extract bilateral joint angles (both left and right legs)
                    if ('_ipsi_rad' in variable or '_contra_rad' in variable) and unit == 'rad':
                        # Determine joint type and side
                        if 'hip_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'hip_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'hip_flexion_angle_contra'
                        elif 'knee_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'knee_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'knee_flexion_angle_contra'
                        elif 'ankle_flexion_angle' in variable:
                            if '_ipsi_rad' in variable:
                                joint_name = 'ankle_flexion_angle_ipsi'
                            elif '_contra_rad' in variable:
                                joint_name = 'ankle_flexion_angle_contra'
                        else:
                            continue
                        
                        validation_data[task][phase][joint_name] = {
                            'min': float(min_val),
                            'max': float(max_val)
                        }
    
    return validation_data


def parse_kinetic_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """
    Parse the validation_expectations_kinetic.md file to extract force/moment ranges.
    
    Args:
        file_path: Path to the validation_expectations_kinetic.md file
        
    Returns:
        Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Dictionary to store parsed data
    validation_data = {}
    
    # Find all task sections
    task_pattern = r'### Task: ([\w_]+)\n'
    tasks = re.findall(task_pattern, content)
    
    for task in tasks:
        validation_data[task] = {}
        
        # Find the task section
        task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## Research Requirements|$)'
        task_match = re.search(task_section_pattern, content, re.DOTALL)
        
        if task_match:
            task_content = task_match.group(1)
            
            # Find all phase tables within this task
            phase_pattern = r'#### Phase (\d+)% \([^)]+\)\n\| Variable.*?\n((?:\|.*?\n)*)'
            phase_matches = re.findall(phase_pattern, task_content, re.MULTILINE)
            
            for phase_str, table_content in phase_matches:
                phase = int(phase_str)
                validation_data[task][phase] = {}
                
                # Parse each row in the table
                row_pattern = r'\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|'
                rows = re.findall(row_pattern, table_content)
                
                for row in rows:
                    if len(row) == 5:
                        variable, min_val_str, max_val_str, units, notes = [col.strip() for col in row]
                        
                        # Skip header rows
                        if variable == 'Variable' or '---' in variable:
                            continue
                        
                        # Extract numeric values, handling both simple numbers and degree annotations
                        min_val = extract_numeric_value(min_val_str)
                        max_val = extract_numeric_value(max_val_str)
                        
                        # Store the variable data
                        validation_data[task][phase][variable] = {
                            'min': min_val,
                            'max': max_val
                        }
    
    return validation_data


def apply_contralateral_offset_kinematic(task_data: Dict, task_name: str) -> Dict:
    """
    Apply contralateral offset logic for gait-based tasks (kinematic variables).
    For bilateral tasks, return data as-is.
    
    Args:
        task_data: Phase data for the task
        task_name: Name of the task
        
    Returns:
        Updated task data with contralateral ranges computed
    """
    gait_tasks = {
        'level_walking', 'incline_walking', 'decline_walking', 
        'up_stairs', 'down_stairs', 'run'
    }
    
    if task_name not in gait_tasks:
        # Bilateral tasks already have both legs specified
        return task_data
    
    # For gait tasks, compute contralateral leg ranges with 50% offset
    phases = [0, 25, 50, 75, 100]
    joint_types = ['hip_flexion_angle', 'knee_flexion_angle', 'ankle_flexion_angle']
    
    # Create a new task_data copy to avoid modifying original
    updated_task_data = {}
    for phase in phases:
        if phase in task_data:
            updated_task_data[phase] = task_data[phase].copy()
        else:
            updated_task_data[phase] = {}
    
    # Apply contralateral offset logic
    for phase in phases:
        if phase == 100:
            # 100% phase should be the same as 0% to show cyclical nature
            if 0 in task_data:
                updated_task_data[100] = task_data[0].copy()
                
                # Apply contralateral offset for 100% phase: 100% contra = 50% ipsi
                if 50 in task_data:
                    for joint_type in joint_types:
                        ipsi_joint = f'{joint_type}_ipsi'
                        contra_joint = f'{joint_type}_contra'
                        if ipsi_joint in task_data[50]:
                            updated_task_data[100][contra_joint] = task_data[50][ipsi_joint].copy()
            continue
            
        if phase in task_data:
            # Calculate contralateral phase with 50% offset
            contralateral_phase = (phase + 50) % 100
            if contralateral_phase == 100:
                contralateral_phase = 0
            
            # Map contralateral phase to available phases
            if contralateral_phase == 0:
                source_phase = 0
            elif contralateral_phase == 25:
                source_phase = 25
            elif contralateral_phase == 50:
                source_phase = 50
            elif contralateral_phase == 75:
                source_phase = 75
            else:
                continue
            
            # Copy left leg data to right leg for contralateral phase
            for joint_type in joint_types:
                left_joint = f'{joint_type}_ipsi'
                right_joint = f'{joint_type}_contra'
                
                if left_joint in task_data[source_phase]:
                    if phase not in updated_task_data:
                        updated_task_data[phase] = {}
                    updated_task_data[phase][right_joint] = task_data[source_phase][left_joint].copy()
    
    return updated_task_data


def apply_contralateral_offset_kinetic(task_data: Dict, task_name: str) -> Dict:
    """
    Apply contralateral offset logic for gait-based tasks (kinetic variables).
    For bilateral tasks, return data as-is.
    
    Args:
        task_data: Phase data for the task
        task_name: Name of the task
        
    Returns:
        Updated task data with contralateral ranges computed
    """
    gait_tasks = {
        'level_walking', 'incline_walking', 'decline_walking', 
        'up_stairs', 'down_stairs', 'run'
    }
    
    if task_name not in gait_tasks:
        # Bilateral tasks already have both legs specified
        return task_data
    
    # For gait tasks, compute contralateral leg ranges with 50% offset
    phases = [0, 25, 50, 75, 100]
    kinetic_types = ['hip_moment', 'knee_moment', 'ankle_moment', 'vertical_grf', 'ap_grf', 'ml_grf']
    
    updated_task_data = task_data.copy()
    
    for phase in phases:
        if phase not in updated_task_data:
            updated_task_data[phase] = {}
        
        # Apply 50% offset logic for contralateral variables
        # Phase 0% ipsi = Phase 50% contra, Phase 25% ipsi = Phase 75% contra, etc.
        contralateral_phase = (phase + 50) % 100
        
        if contralateral_phase in task_data:
            source_phase = contralateral_phase
        else:
            # Fallback to same phase if offset phase not available
            source_phase = phase
            
        for kinetic_type in kinetic_types:
            # For moments, apply offset logic to ipsi/contra
            if 'moment' in kinetic_type:
                ipsi_var = f'{kinetic_type}_ipsi_Nm_kg'
                contra_var = f'{kinetic_type}_contra_Nm_kg'
                
                if ipsi_var in task_data[source_phase]:
                    updated_task_data[phase][contra_var] = task_data[source_phase][ipsi_var].copy()
            
            # For GRF, forces are shared between legs (no ipsi/contra distinction needed)
            # GRF represents the combined ground reaction, but we can model bilateral patterns
    
    return updated_task_data