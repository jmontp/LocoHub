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
                
                # Parse table rows for joint angles - Updated for radians-only format
                row_pattern = r'\| ([\w_]+) \| ([-\d.]+) \| ([-\d.]+) \| (\w+) \|'
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


def write_kinematic_validation_expectations(file_path: str, 
                                          validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                                          dataset_name: str = None,
                                          method: str = None) -> None:
    """
    Write kinematic validation expectations to a markdown file.
    
    This function provides programmatic writing capabilities for the validation
    expectations parser, enabling automated updates to validation specification files.
    
    Args:
        file_path: Path to the validation_expectations_kinematic.md file to write
        validation_data: Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
        dataset_name: Name of dataset used for tuning (optional, for disclaimer)
        method: Statistical method used for tuning (optional, for disclaimer)
        
    Raises:
        RuntimeError: If file writing fails
    """
    try:
        # Read the existing file to preserve non-table content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Generate new content with updated tables and disclaimer
        updated_content = _generate_kinematic_markdown_content(
            content, validation_data, dataset_name, method
        )
        
        # Write the updated content back to file
        with open(file_path, 'w') as f:
            f.write(updated_content)
            
    except Exception as e:
        raise RuntimeError(f"Failed to write kinematic validation expectations to {file_path}: {e}")


def _generate_kinematic_markdown_content(original_content: str, 
                                       validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                                       dataset_name: str = None,
                                       method: str = None) -> str:
    """
    Generate updated markdown content with new validation tables.
    
    Args:
        original_content: Original markdown file content
        validation_data: New validation data to write
        dataset_name: Name of dataset used for tuning (optional)
        method: Statistical method used (optional)
        
    Returns:
        Updated markdown content with new tables
    """
    # Find the start of the validation tables section
    validation_start_pattern = r'(## Validation Tables - VERIFIED\s*\n)'
    validation_start_match = re.search(validation_start_pattern, original_content)
    
    if not validation_start_match:
        raise ValueError("Could not find 'Validation Tables - VERIFIED' section in markdown file")
    
    # Preserve content before validation tables
    prefix_content = original_content[:validation_start_match.end()]
    
    # Find content after all validation tables (before Joint Validation Range Summary)
    end_pattern = r'(## Joint Validation Range Summary|## Pattern Definitions|$)'
    end_match = re.search(end_pattern, original_content)
    
    suffix_content = ""
    if end_match:
        suffix_content = "\n" + original_content[end_match.start():]
    
    # Generate new task sections with per-task disclaimers
    task_sections = _generate_task_sections(validation_data, dataset_name, method)
    
    # Combine all parts
    return prefix_content + "\n" + task_sections + suffix_content


def _generate_tuning_disclaimer(dataset_name: str = None, method: str = None) -> str:
    """
    Generate a disclaimer section documenting the automated tuning process.
    
    Args:
        dataset_name: Name of dataset used for tuning
        method: Statistical method used for tuning
        
    Returns:
        Formatted disclaimer markdown
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    disclaimer = ["**🤖 AUTOMATED TUNING DISCLAIMER**"]
    disclaimer.append("")
    disclaimer.append("⚠️  **Important**: These validation ranges were automatically generated using statistical analysis of biomechanical data.")
    disclaimer.append("")
    
    if dataset_name:
        disclaimer.append(f"📊 **Source Dataset**: `{dataset_name}`")
    if method:
        method_descriptions = {
            'mean_3std': 'Mean ± 3 Standard Deviations (~99.7% coverage)',
            'percentile_95': '95% Percentile Range (2.5th to 97.5th percentiles)',
            'percentile_90': '90% Percentile Range (5th to 95th percentiles)', 
            'iqr_expansion': 'IQR Expansion (Q1-1.5×IQR to Q3+1.5×IQR)',
            'robust_percentile': 'Robust Percentiles (10th to 90th)',
            'conservative': 'Conservative Min/Max with 5% buffer'
        }
        method_desc = method_descriptions.get(method, method)
        disclaimer.append(f"📈 **Statistical Method**: `{method}` ({method_desc})")
    
    disclaimer.append(f"🕒 **Generated**: {timestamp}")
    disclaimer.append("")
    disclaimer.append("**Key Points**:")
    disclaimer.append("- Ranges derived from real biomechanical data, not literature estimates")
    disclaimer.append("- Statistical coverage optimized for data-driven validation")
    disclaimer.append("- May need adjustment for different populations or experimental conditions")
    disclaimer.append("- Regenerate ranges when adding new datasets for optimal coverage")
    disclaimer.append("")
    disclaimer.append("---")
    
    return "\n".join(disclaimer)


def _generate_task_tuning_disclaimer(task_name: str, dataset_name: str = None, method: str = None) -> str:
    """
    Generate a per-task disclaimer documenting the automated tuning process.
    
    Args:
        task_name: Name of the task being documented
        dataset_name: Name of dataset used for tuning
        method: Statistical method used for tuning
        
    Returns:
        Formatted per-task disclaimer markdown
    """
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    disclaimer = [f"**🤖 AUTOMATED TUNING - {task_name.upper()}**"]
    disclaimer.append("")
    disclaimer.append("⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.")
    disclaimer.append("")
    
    # Build info line with dataset and method
    info_parts = []
    if dataset_name:
        info_parts.append(f"📊 **Source**: `{dataset_name}`")
    if method:
        method_descriptions = {
            'mean_3std': 'Mean ± 3σ',
            'percentile_95': '95% Percentile',
            'percentile_90': '90% Percentile', 
            'iqr_expansion': 'IQR Expansion',
            'robust_percentile': 'Robust Percentiles',
            'conservative': 'Conservative Min/Max'
        }
        method_desc = method_descriptions.get(method, method)
        info_parts.append(f"📈 **Method**: {method_desc}")
    
    if info_parts:
        info_parts.append(f"🕒 **Generated**: {timestamp}")
        disclaimer.append(" | ".join(info_parts))
        disclaimer.append("")
    
    return "\n".join(disclaimer)


def _generate_task_sections(validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]], 
                          dataset_name: str = None, method: str = None) -> str:
    """
    Generate markdown task sections with validation tables.
    
    Args:
        validation_data: Validation data by task
        dataset_name: Name of dataset used for tuning (optional)
        method: Statistical method used (optional)
        
    Returns:
        Markdown content for all task sections
    """
    sections = []
    
    for task_name, task_data in validation_data.items():
        sections.append(f"### Task: {task_name}\n")
        
        # Add per-task disclaimer if dataset/method provided
        if dataset_name or method:
            sections.append(_generate_task_tuning_disclaimer(task_name, dataset_name, method))
            sections.append("")
        
        sections.append("**Phase-Specific Range Validation (Ipsilateral Leg Only):**\n")
        
        # Sort phases for consistent output (0, 25, 50, 75)
        phases = sorted([p for p in task_data.keys() if p in [0, 25, 50, 75]])
        
        for phase in phases:
            phase_data = task_data[phase]
            
            # Generate phase section
            phase_section = _generate_phase_section(phase, phase_data)
            sections.append(phase_section)
        
        # Add standard contralateral offset explanation and forward kinematics references
        sections.append("**Contralateral Offset Logic:**")
        sections.append("- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)")
        sections.append("- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)")  
        sections.append("- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)")
        sections.append("- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)")
        sections.append("")
        
        sections.append("**Forward Kinematics Range Visualization:**")
        sections.append("")
        sections.append("| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |")
        sections.append("|---|---|---|---|")
        sections.append(f"| ![{task_name.title().replace('_', ' ')} Forward Kinematics Heel Strike](validation/{task_name}_forward_kinematics_phase_00_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Mid-Stance](validation/{task_name}_forward_kinematics_phase_25_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Toe-Off](validation/{task_name}_forward_kinematics_phase_50_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Mid-Swing](validation/{task_name}_forward_kinematics_phase_75_range.png) |")
        sections.append("")
        
        sections.append("**Filters by Phase Validation:**")
        sections.append("")
        sections.append(f"![{task_name.title().replace('_', ' ')} Kinematic Filters by Phase](validation/{task_name}_kinematic_filters_by_phase.png)")
        sections.append("")
        
        # Add separator between tasks except for the last one
        if task_name != list(validation_data.keys())[-1]:
            sections.append("---")
            sections.append("")
    
    return "\n".join(sections)


def _generate_phase_section(phase: int, phase_data: Dict[str, Dict[str, float]]) -> str:
    """
    Generate markdown for a single phase section with validation table.
    
    Args:
        phase: Phase percentage (0, 25, 50, 75)
        phase_data: Phase validation data
        
    Returns:
        Markdown content for the phase section
    """
    # Add phase description based on percentage
    if phase == 0:
        phase_content = [f"#### Phase {phase}% (Heel Strike)"]
    elif phase == 25:
        phase_content = [f"#### Phase {phase}% (Mid-Stance)"]
    elif phase == 50:
        phase_content = [f"#### Phase {phase}% (Toe-Off)"]
    elif phase == 75:
        phase_content = [f"#### Phase {phase}% (Mid-Swing)"]
    else:
        phase_content = [f"#### Phase {phase}%"]
    
    # Generate validation table
    phase_content.append("| Variable | Min_Value | Max_Value | Units | Notes |")
    phase_content.append("|----------|-----------|-----------|-------|-------|")
    
    # Standard variable order for consistency (match the automated fine tuning output)
    variable_order = [
        'hip_flexion_angle_ipsi',
        'knee_flexion_angle_ipsi', 
        'ankle_flexion_angle_ipsi'
    ]
    
    # Add rows for variables that exist in the data
    for variable in variable_order:
        if variable in phase_data:
            var_data = phase_data[variable]
            min_val = var_data['min']
            max_val = var_data['max']
            
            # Format values to 2 decimal places with appropriate descriptive notes
            notes = {
                'hip_flexion_angle_ipsi': 'Data-driven statistical range',
                'knee_flexion_angle_ipsi': 'Data-driven statistical range', 
                'ankle_flexion_angle_ipsi': 'Data-driven statistical range'
            }
            
            note = notes.get(variable, 'Optimized range')
            phase_content.append(f"| {variable}_rad | {min_val:.2f} | {max_val:.2f} | rad | {note} |")
    
    phase_content.append("")  # Empty line after table
    
    return "\n".join(phase_content)


def write_kinetic_validation_expectations(file_path: str,
                                        validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]]) -> None:
    """
    Write kinetic validation expectations to a markdown file.
    
    Args:
        file_path: Path to the validation_expectations_kinetic.md file to write  
        validation_data: Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
        
    Raises:
        RuntimeError: If file writing fails
    """
    try:
        # Similar implementation to kinematic version but for kinetic variables
        with open(file_path, 'r') as f:
            content = f.read()
        
        updated_content = _generate_kinetic_markdown_content(content, validation_data)
        
        with open(file_path, 'w') as f:
            f.write(updated_content)
            
    except Exception as e:
        raise RuntimeError(f"Failed to write kinetic validation expectations to {file_path}: {e}")


def _generate_kinetic_markdown_content(original_content: str,
                                     validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]]) -> str:
    """
    Generate updated kinetic markdown content with new validation tables.
    
    Args:
        original_content: Original markdown file content
        validation_data: New validation data to write
        
    Returns:
        Updated markdown content with new tables
    """
    # Implementation similar to kinematic version but adapted for kinetic file structure
    # This would need to be customized based on the actual kinetic file format
    # For now, return the original content as a placeholder
    return original_content