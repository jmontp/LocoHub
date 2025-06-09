#!/usr/bin/env python3
"""
Update Validation Table Format

Updates the validation_expectations.md file to include degrees in parentheses 
for all joint angle values in the Min_Value and Max_Value columns.

Format: 0.15 (9°) for radian values with degree equivalents in parentheses.
"""

import re
import numpy as np
import argparse
from pathlib import Path


def convert_rad_to_deg_format(value_str):
    """Convert a radian value to 'rad (deg°)' format."""
    try:
        rad_value = float(value_str)
        deg_value = np.degrees(rad_value)
        return f"{value_str} ({deg_value:.0f}°)"
    except ValueError:
        return value_str


def update_validation_table(file_path: str) -> str:
    """
    Update the validation_expectations.md file to include degrees in parentheses.
    
    Args:
        file_path: Path to the validation_expectations.md file
        
    Returns:
        Updated content
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match joint angle table rows
    # Looks for: | variable_name_rad | min_value | max_value | rad | notes |
    pattern = r'\| ([a-z_]+_rad) \| ([-\d.]+) \| ([-\d.]+) \| rad \| ([^|]+) \|'
    
    def replace_row(match):
        variable = match.group(1)
        min_val = match.group(2)
        max_val = match.group(3)
        notes = match.group(4)
        
        # Convert to format with degrees in parentheses
        min_formatted = convert_rad_to_deg_format(min_val)
        max_formatted = convert_rad_to_deg_format(max_val)
        
        return f"| {variable} | {min_formatted} | {max_formatted} | rad | {notes} |"
    
    # Apply the replacement
    updated_content = re.sub(pattern, replace_row, content)
    
    return updated_content


def main():
    """Main function to update validation table format."""
    
    parser = argparse.ArgumentParser(
        description='Update validation table format to include degrees'
    )
    parser.add_argument(
        '--validation-file',
        type=str,
        default='docs/standard_spec/validation_expectations.md',
        help='Path to validation_expectations.md file'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        help='Output file path (default: overwrite input file)'
    )
    
    args = parser.parse_args()
    
    # Find the validation expectations file
    if Path(args.validation_file).exists():
        validation_file = args.validation_file
    else:
        # Try from project root
        project_root = Path(__file__).parent.parent
        validation_file = project_root / args.validation_file
        if not validation_file.exists():
            print(f"Error: Could not find validation file at {args.validation_file}")
            return 1
    
    print(f"Updating validation table format in: {validation_file}")
    
    # Update the table format
    try:
        updated_content = update_validation_table(str(validation_file))
        
        # Write to output file
        output_file = args.output_file if args.output_file else validation_file
        with open(output_file, 'w') as f:
            f.write(updated_content)
        
        print(f"✅ Successfully updated validation table format!")
        print(f"Output written to: {output_file}")
        
    except Exception as e:
        print(f"Error updating validation file: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())