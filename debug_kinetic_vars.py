#!/usr/bin/env python3
import sys
from pathlib import Path

# Add source to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'source'))

from validation.validation_expectations_parser import ValidationExpectationsParser
from lib.python.feature_constants import get_feature_list

# Test kinetic table generation with original data
parser = ValidationExpectationsParser()
original_data = parser.read_validation_data('source/tests/test_data/validation_parser/original_kinetic.md')

task_data = original_data['decline_walking']
print('Debugging kinetic table generation...')
print(f'Task data phases: {list(task_data.keys())}')
print(f'Phase 0 variables: {list(task_data[0].keys())[:5]}...')

print('\nKinetic feature constants:')
standard_features = get_feature_list('kinetic')
print(f'Standard kinetic features count: {len(standard_features)}')
print(f'First 5 standard features: {standard_features[:5]}')

print('\nChecking variable matching:')
all_variables = set()
for phase_data in task_data.values():
    all_variables.update(phase_data.keys())
print(f'All variables in data: {list(all_variables)[:5]}...')

# Check which variables match
sorted_variables = []
for feature in standard_features:
    if feature in all_variables:
        sorted_variables.append(feature)
        print(f'  MATCH: {feature}')
    else:
        if 'flexion_moment' in feature:  # Only show flexion moments for brevity
            print(f'  NO MATCH: {feature}')

print(f'\nFinal sorted_variables: {sorted_variables}')

# Test table generation directly
print(f'\nTesting table generation...')
table = parser._generate_unified_hierarchical_table(task_data, 'kinetic')
print(f'Generated table length: {len(table)}')
lines = table.split('\n')
for i, line in enumerate(lines):
    if i < 8 or 'moment' in line:
        print(f'  Line {i}: {line}')