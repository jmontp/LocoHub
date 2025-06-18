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

# Read original kinetic data
original_data = parser.read_validation_data('source/tests/test_data/validation_parser/original_kinetic.md')
print('Original kinetic data:')
task = 'decline_walking'
if task in original_data:
    print(f'  Task {task} has {len(original_data[task])} phases')
    if 0 in original_data[task]:
        print(f'  Phase 0 has {len(original_data[task][0])} variables')
        print(f'  First 3 variables: {list(original_data[task][0].keys())[:3]}')

# Write it back and read again
with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
    temp_file = f.name
    f.write("""# Test Kinetic Validation

## Validation Tables

## Research Requirements
""")

try:
    print('\nWriting kinetic data...')
    parser.write_validation_data(temp_file, original_data, mode='kinetic')
    
    print('Reading back...')
    new_data = parser.read_validation_data(temp_file)
    
    print('New kinetic data:')
    if task in new_data:
        print(f'  Task {task} has {len(new_data[task])} phases')
        if 0 in new_data[task]:
            print(f'  Phase 0 has {len(new_data[task][0])} variables')
            print(f'  Variables: {list(new_data[task][0].keys())[:5]}')
    else:
        print(f'  Task {task} not found in new data')
        print(f'  Available tasks: {list(new_data.keys())}')
    
    # Show part of the written file
    with open(temp_file, 'r') as f:
        content = f.read()
    
    print('\nWritten file content:')
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '| Variable |' in line or 'ankle_flexion' in line or i < 25:
            print(f'  Line {i}: {line}')

finally:
    os.unlink(temp_file)