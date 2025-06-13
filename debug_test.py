#!/usr/bin/env python3
import tempfile
import os
import sys
from pathlib import Path

# Add source to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'source'))

from validation.validation_expectations_parser import ValidationExpectationsParser

def test_write_minimal():
    """Minimal test to debug the write issue."""
    
    parser = ValidationExpectationsParser()
    
    # Create temp file with minimal markdown structure
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        temp_file = f.name
        f.write("""# Test Kinematic Validation

## Validation Tables

""")
    
    try:
        # Sample data - exactly what the test uses
        sample_data = {
            'level_walking': {
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
        }
        
        print("Sample data structure:")
        for task, task_data in sample_data.items():
            print(f"  {task}:")
            for phase, phase_data in task_data.items():
                print(f"    Phase {phase}: {list(phase_data.keys())}")
        
        print("\nCalling write_validation_data...")
        parser.write_validation_data(
            temp_file,
            sample_data,
            dataset_name='test_dataset.parquet',
            method='percentile_95'
        )
        
        print("Reading back content...")
        with open(temp_file, 'r') as f:
            content = f.read()
        
        print(f"Content length: {len(content)}")
        
        # Check for expected elements
        checks = [
            ('level_walking', 'level_walking' in content),
            ('hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad' in content),
            ('0.349', '0.349' in content),
            ('0.833', '0.833' in content),
            ('**rad**', '**rad**' in content),
        ]
        
        print("\nContent checks:")
        for item, result in checks:
            print(f"  {item}: {result}")
        
        # Show the table section
        lines = content.split('\n')
        table_start = None
        for i, line in enumerate(lines):
            if '| Variable |' in line:
                table_start = i
                break
        
        if table_start:
            print(f"\nTable section (starting at line {table_start}):")
            for i in range(table_start, min(table_start + 15, len(lines))):
                print(f"  {i:2d}: {lines[i]}")
        else:
            print("\nNo table found!")
            print("\nFull content:")
            for i, line in enumerate(lines):
                print(f"  {i:2d}: {line}")
        
    finally:
        os.unlink(temp_file)

if __name__ == '__main__':
    test_write_minimal()