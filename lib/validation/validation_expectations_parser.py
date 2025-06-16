#!/usr/bin/env python3
"""
Validation Expectations Parser

Created: 2025-06-12 with user permission
Purpose: Unified markdown parser with dictionary API for validation expectations

Intent:
This module provides a clean API interface that completely separates markdown parsing
from data processing. External tools (like automated_fine_tuning.py) work with
dictionary APIs and have no knowledge of the underlying markdown format.

The parser handles all reading/writing and regenerates markdown files based on
new information provided through the dictionary interface.

**CORE ARCHITECTURE:**
1. **Dictionary API**: External tools work only with dictionaries
2. **Markdown Abstraction**: Parser handles all markdown formatting internally
3. **Unified Format**: Both kinematic and kinetic use the same table structure
4. **Feature Constants**: Uses feature_constants.py as single source of truth
5. **No Backward Compatibility**: Clean, modern implementation only

Usage:
    parser = ValidationExpectationsParser()
    
    # Read validation data as dictionary
    data = parser.read_validation_data('validation_expectations_kinematic.md')
    
    # Modify data programmatically
    data['level_walking'][25]['hip_flexion_angle_ipsi']['min'] = 0.1
    
    # Write back to markdown (automatically regenerated)
    parser.write_validation_data('validation_expectations_kinematic.md', data)
"""

import re
import math
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
import sys

# Add source directory to Python path for feature constants
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'source'))


class ValidationExpectationsParser:
    """
    Unified parser for validation expectations with dictionary API.
    
    This class provides a clean interface for reading and writing validation
    expectations while completely abstracting the markdown format from users.
    """
    
    def __init__(self):
        """Initialize the parser."""
        pass
    
    def read_validation_data(self, file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Read validation data from markdown file as dictionary.
        
        Args:
            file_path: Path to validation expectations markdown file
            
        Returns:
            Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
        """
        return self._parse_unified_format(file_path)
    
    def write_validation_data(self, file_path: str, 
                            validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                            dataset_name: Optional[str] = None,
                            method: Optional[str] = None,
                            mode: Optional[str] = None) -> None:
        """
        Write validation data to markdown file with automatic format generation.
        
        Args:
            file_path: Path to validation expectations markdown file
            validation_data: Validation data dictionary
            dataset_name: Name of dataset used (optional, for disclaimer)
            method: Statistical method used (optional, for disclaimer)
            mode: Mode override ('kinematic' or 'kinetic'). If None, auto-detect from file path.
        """
        # Determine mode from parameter or file path
        if mode is None:
            mode = 'kinematic' if 'kinematic' in str(file_path) else 'kinetic'
        
        # Read existing file to preserve non-table content
        with open(file_path, 'r') as f:
            original_content = f.read()
        
        # Generate new content with updated tables
        updated_content = self._generate_markdown_content(
            original_content, validation_data, mode, dataset_name, method
        )
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.write(updated_content)
    
    def _parse_unified_format(self, file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
        """
        Parse validation expectations using unified format for both kinematic and kinetic.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            Dictionary structured as: {task_name: {phase: {variable: {min, max}}}}
        """
        with open(file_path, 'r') as f:
            content = f.read()
        
        validation_data = {}
        
        # Find all task sections
        task_pattern = r'### Task: ([\w_]+)'
        tasks = re.findall(task_pattern, content)
        
        for task in tasks:
            validation_data[task] = {}
            
            # Find the task section content
            task_section_pattern = rf'### Task: {re.escape(task)}\n(.*?)(?=### Task:|## Research Requirements|## Parser Usage|## Maintenance Guidelines|## References|$)'
            task_match = re.search(task_section_pattern, content, re.DOTALL)
            
            if task_match:
                task_content = task_match.group(1)
                
                # Parse the unified hierarchical table
                table_data = self._parse_unified_table_format(task_content)
                validation_data[task] = table_data
        
        return validation_data
    
    def _parse_unified_table_format(self, task_content: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """
        Parse both unified hierarchical format and original individual phase format.
        
        Args:
            task_content: Content of the task section containing the table(s)
            
        Returns:
            Dictionary structured as: {phase: {variable: {min, max}}}
        """
        # Try unified hierarchical format first
        hierarchical_data = self._parse_hierarchical_format(task_content)
        if hierarchical_data:
            return hierarchical_data
        
        # Fall back to original individual phase format
        return self._parse_individual_phase_format(task_content)
    
    def _parse_hierarchical_format(self, task_content: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """Parse the unified hierarchical table format."""
        # Find the table by looking for the header pattern
        table_pattern = r'\| Variable \|.*?\n(\|:---|.*?)\n(\| \|.*?)\n((?:\|.*?\n)*?)(?=\n\*\*|$)'
        table_match = re.search(table_pattern, task_content, re.DOTALL)
        
        if not table_match:
            return {}
        
        header_line = table_match.group(0).split('\n')[0]  # First line with phases
        data_rows = table_match.group(3)
        
        # Extract phase information from the header line
        phase_pattern = r'(\d+)%'
        phases = [int(p) for p in re.findall(phase_pattern, header_line)]
        
        # Parse data rows
        phase_data = {phase: {} for phase in phases}
        
        for line in data_rows.strip().split('\n'):
            if '|' in line and not line.startswith('|:') and line.strip():
                parts = [p.strip() for p in line.split('|')]
                
                # Remove empty first and last parts from split
                if parts and not parts[0]:
                    parts = parts[1:]
                if parts and not parts[-1]:
                    parts = parts[:-1]
                
                if len(parts) >= 1 and parts[0]:  # Has variable name
                    variable = parts[0].strip()
                    
                    # Skip header rows
                    if variable in ['Variable', ''] or '**Min**' in variable or '---' in variable:
                        continue
                    
                    # Extract min/max values for each phase
                    value_index = 1  # Start after variable name
                    for phase in phases:
                        if value_index < len(parts) - 2:  # Ensure we have min/max pairs
                            min_str = parts[value_index].strip()
                            max_str = parts[value_index + 1].strip()
                            
                            # Parse numeric values
                            try:
                                min_val = self._parse_numeric_value(min_str)
                                max_val = self._parse_numeric_value(max_str)
                                
                                # Remove suffix for storage (e.g., '_rad' from variable names)
                                clean_variable = variable.replace('_rad', '').replace('_Nm', '')
                                
                                phase_data[phase][clean_variable] = {
                                    'min': min_val,
                                    'max': max_val
                                }
                            except (ValueError, IndexError):
                                pass  # Skip invalid data
                            
                            value_index += 3  # Move to next phase (min, max, separator)
                        else:
                            break
        
        return phase_data
    
    def _parse_individual_phase_format(self, task_content: str) -> Dict[int, Dict[str, Dict[str, float]]]:
        """Parse the original individual phase table format."""
        phase_data = {}
        
        # Find all phase sections: #### Phase X% (Description)
        phase_pattern = r'#### Phase (\d+)%.*?\n(.*?)(?=#### Phase|\*\*|$)'
        phase_matches = re.findall(phase_pattern, task_content, re.DOTALL)
        
        for phase_str, phase_content in phase_matches:
            phase = int(phase_str)
            phase_data[phase] = {}
            
            # Find the table in this phase section
            table_pattern = r'\| Variable \| Min_Value \| Max_Value \| Units \| Notes \|(.*?)(?=\n\n|\*\*|$)'
            table_match = re.search(table_pattern, phase_content, re.DOTALL)
            
            if table_match:
                table_rows = table_match.group(1)
                
                # Parse each table row
                for line in table_rows.strip().split('\n'):
                    if '|' in line and not line.startswith('|:') and not '---' in line:
                        parts = [p.strip() for p in line.split('|')]
                        
                        # Remove empty first and last parts
                        if parts and not parts[0]:
                            parts = parts[1:]
                        if parts and not parts[-1]:
                            parts = parts[:-1]
                        
                        if len(parts) >= 5:  # Variable, Min, Max, Units, Notes
                            variable = parts[0].strip()
                            min_str = parts[1].strip()
                            max_str = parts[2].strip()
                            
                            if variable and variable != 'Variable':
                                try:
                                    min_val = self._parse_numeric_value(min_str)
                                    max_val = self._parse_numeric_value(max_str)
                                    
                                    # Remove suffix for storage
                                    clean_variable = variable.replace('_rad', '').replace('_Nm', '')
                                    
                                    phase_data[phase][clean_variable] = {
                                        'min': min_val,
                                        'max': max_val
                                    }
                                except (ValueError, IndexError):
                                    pass  # Skip invalid data
        
        return phase_data
    
    def _parse_numeric_value(self, value_str: str) -> float:
        """
        Extract numeric value from a string, handling various formats.
        
        Args:
            value_str: String containing numeric value
            
        Returns:
            Extracted numeric value as float
            
        Raises:
            ValueError: If no numeric value can be extracted
        """
        value_str = value_str.strip()
        
        # Handle empty, dash, or NaN values
        if not value_str or value_str in ['-', 'nan', 'NaN']:
            return float('nan')
        
        # Extract the first number found (handles negative numbers)
        match = re.search(r'-?\d*\.?\d+', value_str)
        if match:
            return float(match.group())
        else:
            raise ValueError(f"Could not extract numeric value from '{value_str}'")
    
    def _generate_markdown_content(self, original_content: str, 
                                 validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                                 mode: str, dataset_name: Optional[str] = None, 
                                 method: Optional[str] = None) -> str:
        """
        Generate updated markdown content with new validation tables.
        
        Args:
            original_content: Original markdown file content
            validation_data: New validation data to write
            mode: 'kinematic' or 'kinetic'
            dataset_name: Name of dataset used for tuning (optional)
            method: Statistical method used (optional)
            
        Returns:
            Updated markdown content with new tables
        """
        # Find the start of the validation tables section
        validation_start_patterns = [
            r'## Validation Tables\s*\n',
            r'## Validation Tables - .*?\n'
        ]
        
        validation_start_match = None
        for pattern in validation_start_patterns:
            validation_start_match = re.search(pattern, original_content)
            if validation_start_match:
                break
        
        if not validation_start_match:
            raise ValueError("Could not find 'Validation Tables' section in markdown file")
        
        # Preserve content before validation tables
        prefix_content = original_content[:validation_start_match.end()]
        
        # Find content after all validation tables
        if mode == 'kinematic':
            end_patterns = [r'## Joint Validation Range Summary', r'## Pattern Definitions']
        else:
            end_patterns = [r'## Research Requirements', r'## Parser Usage']
        
        suffix_content = ""
        for pattern in end_patterns:
            end_match = re.search(pattern, original_content)
            if end_match:
                suffix_content = "\n" + original_content[end_match.start():]
                break
        
        # Generate new task sections
        task_sections = self._generate_task_sections(validation_data, mode, dataset_name, method)
        
        # Combine all parts
        return prefix_content + "\n" + task_sections + suffix_content
    
    def _generate_task_sections(self, validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]], 
                              mode: str, dataset_name: Optional[str] = None, 
                              method: Optional[str] = None) -> str:
        """
        Generate markdown task sections with validation tables.
        
        Args:
            validation_data: Validation data by task
            mode: 'kinematic' or 'kinetic'
            dataset_name: Name of dataset used for tuning (optional)
            method: Statistical method used (optional)
            
        Returns:
            Markdown content for all task sections
        """
        sections = []
        
        for task_name, task_data in validation_data.items():
            # Add per-task disclaimer if dataset/method provided
            if dataset_name or method:
                sections.append(self._generate_task_tuning_disclaimer(task_name, dataset_name, method))
                sections.append("")
            
            sections.append(f"### Task: {task_name}\n")
            sections.append("**Phase-Specific Range Validation (Ipsilateral Leg Only):**\n")
            
            # Generate unified hierarchical table
            table_content = self._generate_unified_hierarchical_table(task_data, mode)
            sections.append(table_content)
            sections.append("")  # Empty line after table
            
            # Add mode-specific content
            if mode == 'kinematic':
                self._add_kinematic_sections(sections, task_name)
            else:
                self._add_kinetic_sections(sections, task_name)
            
            # Add separator between tasks except for the last one
            if task_name != list(validation_data.keys())[-1]:
                sections.append("---")
                sections.append("")
        
        return "\n".join(sections)
    
    def _add_kinematic_sections(self, sections: List[str], task_name: str) -> None:
        """Add kinematic-specific sections (contralateral offset, visualization)."""
        sections.extend([
            "**Contralateral Offset Logic:**",
            "- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)",
            "- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)",
            "- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)",
            "- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)",
            "",
            "**Forward Kinematics Range Visualization:**",
            "",
            "| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |",
            "|---|---|---|---|",
            f"| ![{task_name.title().replace('_', ' ')} Forward Kinematics Heel Strike](validation/{task_name}_forward_kinematics_phase_00_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Mid-Stance](validation/{task_name}_forward_kinematics_phase_25_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Toe-Off](validation/{task_name}_forward_kinematics_phase_50_range.png) | ![{task_name.title().replace('_', ' ')} Forward Kinematics Mid-Swing](validation/{task_name}_forward_kinematics_phase_75_range.png) |",
            "",
            "**Filters by Phase Validation:**",
            "",
            f"![{task_name.title().replace('_', ' ')} Kinematic Filters by Phase](validation/{task_name}_kinematic_filters_by_phase.png)",
            ""
        ])
    
    def _add_kinetic_sections(self, sections: List[str], task_name: str) -> None:
        """Add kinetic-specific sections (filters by phase only)."""
        sections.extend([
            "**Filters by Phase Validation:**",
            "",
            f"![{task_name.title().replace('_', ' ')} Kinetic Filters by Phase](validation/{task_name}_kinetic_filters_by_phase.png)",
            ""
        ])
    
    def _generate_task_tuning_disclaimer(self, task_name: str, dataset_name: Optional[str] = None, 
                                       method: Optional[str] = None) -> str:
        """
        Generate a per-task disclaimer documenting the automated tuning process.
        
        Args:
            task_name: Name of the task being documented
            dataset_name: Name of dataset used for tuning
            method: Statistical method used for tuning
            
        Returns:
            Formatted per-task disclaimer markdown
        """
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
    
    def _generate_unified_hierarchical_table(self, task_data: Dict[int, Dict[str, Dict[str, float]]], mode: str) -> str:
        """Generate a hierarchical validation table with the user's preferred format."""
        
        # Import feature constants
        from lib.python.feature_constants import get_feature_list
        
        # Get standard features for the mode
        standard_features = get_feature_list(mode)
        
        # Get all variables across all phases
        all_variables = set()
        phases = sorted(task_data.keys())
        for phase_data in task_data.values():
            all_variables.update(phase_data.keys())
        
        # Filter to only variables that exist in the data, maintaining standard order
        sorted_variables = []
        for feature in standard_features:
            if mode == 'kinematic':
                base_name = feature.replace('_rad', '')  # Remove _rad suffix for matching
                if base_name in all_variables:
                    sorted_variables.append(base_name)
            elif mode == 'kinetic':
                base_name = feature.replace('_Nm', '')  # Remove _Nm suffix for matching
                if base_name in all_variables:
                    sorted_variables.append(base_name)
        
        # Determine unit and variable display format
        if mode == 'kinematic':
            var_suffix = "_rad"
        elif mode == 'kinetic':
            var_suffix = "_Nm"  # Default suffix for moments
        else:
            var_suffix = ""
        
        # Build table content
        content = []
        
        # Header row 1: Variable | | 0% | | | 25% | | | 50% | | | 75% | |Units|Notes|
        header1 = "| Variable |"
        for phase in phases:
            header1 += f" | {phase}% | |"
        header1 += " |Units|Notes|"
        content.append(header1)
        
        # Alignment row with proper left/center alignment
        align_row = "|:---|"
        for phase in phases:
            align_row += "---:|:---:|:---|"
        align_row += ":---:|:---|"
        content.append(align_row)
        
        # Header row 2: | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | | |
        header2 = "| |"
        for phase in phases:
            header2 += " **Min** | **Max** | |"
        header2 += " | |"
        content.append(header2)
        
        # Data rows
        for variable in sorted_variables:
            # Display name with appropriate suffix
            if mode == 'kinetic':
                # Determine specific suffix for kinetic variables
                if 'grf' in variable:
                    var_suffix = "_N"
                elif 'cop' in variable:
                    var_suffix = "_m"
                else:
                    var_suffix = "_Nm"  # Default for moments
            
            display_name = f"{variable}{var_suffix}"
            row = f"| {display_name} |"
            
            for phase in phases:
                if phase in task_data and variable in task_data[phase]:
                    min_val = task_data[phase][variable]['min']
                    max_val = task_data[phase][variable]['max']
                    
                    # Handle NaN values
                    if math.isnan(min_val) or math.isnan(max_val):
                        row += " nan | nan | |"
                    else:
                        row += f" {min_val:.3f} | {max_val:.3f} | |"
                else:
                    row += " - | - | |"
            
            # Determine unit for this specific variable
            if mode == 'kinetic':
                if 'grf' in variable:
                    var_unit = "N"
                elif 'cop' in variable:
                    var_unit = "m"
                else:
                    var_unit = "Nm"
            else:
                var_unit = "rad"
                
            row += f" |**{var_unit}** | |"
            content.append(row)
        
        return "\n".join(content)


# Legacy function wrappers for backward compatibility during transition
def parse_validation_expectations(file_path: str) -> Dict[str, Dict[int, Dict[str, Dict[str, float]]]]:
    """Legacy wrapper - use ValidationExpectationsParser.read_validation_data() instead."""
    parser = ValidationExpectationsParser()
    return parser.read_validation_data(file_path)


def write_validation_expectations(file_path: str, 
                                validation_data: Dict[str, Dict[int, Dict[str, Dict[str, float]]]],
                                dataset_name: str = None, method: str = None) -> None:
    """Legacy wrapper - use ValidationExpectationsParser.write_validation_data() instead."""
    parser = ValidationExpectationsParser()
    # Auto-detect mode from file path for legacy compatibility
    mode = 'kinematic' if 'kinematic' in str(file_path) else 'kinetic'
    parser.write_validation_data(file_path, validation_data, dataset_name, method, mode)


# Utility functions
def extract_numeric_value(value_str: str) -> float:
    """
    Extract numeric value from a string, handling various formats.
    
    Args:
        value_str: String containing numeric value
        
    Returns:
        Extracted numeric value as float
        
    Raises:
        ValueError: If no numeric value can be extracted
    """
    value_str = value_str.strip()
    
    # Handle empty, dash, or NaN values
    if not value_str or value_str in ['-', 'nan', 'NaN']:
        return float('nan')
    
    # Extract the first number found (handles negative numbers)
    match = re.search(r'-?\d*\.?\d+', value_str)
    if match:
        return float(match.group())
    else:
        raise ValueError(f"Could not extract numeric value from '{value_str}'")