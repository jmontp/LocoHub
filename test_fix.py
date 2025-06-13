#!/usr/bin/env python3
import tempfile
import os
import sys
from pathlib import Path

# Add source to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'source'))

from validation.validation_expectations_parser import ValidationExpectationsParser

parser = ValidationExpectationsParser()

# Create temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    temp_file = f.name
    f.write("""# Test Kinematic Validation

## Validation Tables

## Joint Validation Range Summary
""")

try:
    # Sample data
    sample_data = {
        'level_walking': {
            0: {
                'hip_flexion_angle_ipsi': {'min': 0.349, 'max': 0.833},
                'knee_flexion_angle_ipsi': {'min': -0.047, 'max': 0.253}
            },
            25: {
                'hip_flexion_angle_ipsi': {'min': -0.043, 'max': 0.526},
                'knee_flexion_angle_ipsi': {'min': 0.024, 'max': 0.358}
            }
        }
    }
    
    print('Testing with explicit mode=kinematic...')
    parser.write_validation_data(
        temp_file,
        sample_data,
        dataset_name='test_dataset.parquet',
        method='percentile_95',
        mode='kinematic'  # EXPLICIT MODE
    )
    
    with open(temp_file, 'r') as f:
        content = f.read()
    
    print('Content checks:')
    print(f'  hip_flexion_angle_ipsi_rad: {"hip_flexion_angle_ipsi_rad" in content}')
    print(f'  0.349: {"0.349" in content}')
    print(f'  0.833: {"0.833" in content}')
    
    # Show table section
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'hip_flexion' in line or 'knee_flexion' in line:
            print(f'  Line {i}: {line}')

finally:
    os.unlink(temp_file)