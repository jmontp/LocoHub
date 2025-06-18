#!/usr/bin/env python3
import sys
from pathlib import Path

# Add source to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'source'))

from validation.validation_expectations_parser import ValidationExpectationsParser

def debug_table_generation():
    """Debug table generation step by step."""
    
    parser = ValidationExpectationsParser()
    
    # Test data - same as the failing test
    sample_data = {
        0: {
            'hip_flexion_angle_ipsi': {'min': 0.349, 'max': 0.833},
            'knee_flexion_angle_ipsi': {'min': -0.047, 'max': 0.253},
            'ankle_flexion_angle_ipsi': {'min': -0.147, 'max': 0.145}
        },
        25: {
            'hip_flexion_angle_ipsi': {'min': -0.043, 'max': 0.526},
            'knee_flexion_angle_ipsi': {'min': 0.024, 'max': 0.358},
            'ankle_flexion_angle_ipsi': {'min': -0.224, 'max': -0.052}
        }
    }
    
    print("Debug: Starting table generation...")
    
    # Import feature constants
    from lib.python.feature_constants import get_feature_list
    
    # Get standard features for kinematic mode
    mode = 'kinematic'
    standard_features = get_feature_list(mode)
    print(f"Debug: Standard features count: {len(standard_features)}")
    print(f"Debug: First few standard features: {standard_features[:3]}")
    
    # Get all variables across all phases
    all_variables = set()
    phases = sorted(sample_data.keys())
    print(f"Debug: Phases: {phases}")
    
    for phase_data in sample_data.values():
        all_variables.update(phase_data.keys())
    print(f"Debug: All variables in data: {all_variables}")
    
    # Filter to only variables that exist in the data, maintaining standard order
    sorted_variables = []
    for feature in standard_features:
        base_name = feature.replace('_rad', '')  # Remove _rad suffix for matching
        print(f"Debug: Checking feature '{feature}' -> base_name '{base_name}' in {base_name in all_variables}")
        if base_name in all_variables:
            sorted_variables.append(base_name)
    
    print(f"Debug: Final sorted_variables: {sorted_variables}")
    
    if not sorted_variables:
        print("ERROR: No sorted variables found!")
        return
    
    # Now test table generation
    print("\nDebug: Testing table generation...")
    table = parser._generate_unified_hierarchical_table(sample_data, mode)
    
    print(f"Debug: Generated table length: {len(table)}")
    print("Debug: Generated table:")
    for i, line in enumerate(table.split('\n')):
        print(f"  {i}: {line}")
    
    print("\nDebug: Checking if data rows are present...")
    table_lines = table.split('\n')
    for i, line in enumerate(table_lines):
        if 'hip_flexion_angle_ipsi_rad' in line:
            print(f"Found data row at line {i}: {line}")
        elif '0.349' in line:
            print(f"Found value 0.349 at line {i}: {line}")

if __name__ == '__main__':
    debug_table_generation()