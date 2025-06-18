#!/usr/bin/env python3
import tempfile
import os
import sys
from pathlib import Path

# Add source to path
project_root = Path(__file__).parent
sys.path.append(str(project_root / 'source'))

from validation.validation_expectations_parser import ValidationExpectationsParser

def debug_write_pipeline():
    """Debug the full write pipeline step by step."""
    
    # Create a custom parser class with debug prints
    class DebugParser(ValidationExpectationsParser):
        def _generate_unified_hierarchical_table(self, task_data, mode):
            print(f"DEBUG: _generate_unified_hierarchical_table called with mode={mode}")
            print(f"DEBUG: task_data keys: {list(task_data.keys())}")
            print(f"DEBUG: task_data[0] keys: {list(task_data[0].keys()) if 0 in task_data else 'No phase 0'}")
            
            result = super()._generate_unified_hierarchical_table(task_data, mode)
            print(f"DEBUG: Table generation result length: {len(result)}")
            lines = result.split('\n')
            print(f"DEBUG: Table has {len(lines)} lines")
            for i, line in enumerate(lines):
                if 'hip_flexion' in line or i < 4:
                    print(f"DEBUG: Line {i}: {line}")
            
            return result
        
        def _generate_task_sections(self, validation_data, mode, dataset_name=None, method=None):
            print(f"DEBUG: _generate_task_sections called with mode={mode}")
            print(f"DEBUG: validation_data keys: {list(validation_data.keys())}")
            
            result = super()._generate_task_sections(validation_data, mode, dataset_name, method)
            print(f"DEBUG: Task sections result length: {len(result)}")
            lines = result.split('\n')
            for i, line in enumerate(lines):
                if 'hip_flexion' in line or '| Variable |' in line:
                    print(f"DEBUG: Task sections line {i}: {line}")
            
            return result
        
        def _generate_markdown_content(self, original_content, validation_data, mode, dataset_name=None, method=None):
            print(f"DEBUG: _generate_markdown_content called with mode={mode}")
            
            result = super()._generate_markdown_content(original_content, validation_data, mode, dataset_name, method)
            print(f"DEBUG: Final markdown length: {len(result)}")
            lines = result.split('\n')
            for i, line in enumerate(lines):
                if 'hip_flexion' in line or '| Variable |' in line:
                    print(f"DEBUG: Final markdown line {i}: {line}")
            
            return result
    
    parser = DebugParser()
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        temp_file = f.name
        f.write("""# Test Kinematic Validation

## Validation Tables

## Joint Validation Range Summary
""")
    
    try:
        # Sample data - exactly what the failing test uses
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
        
        print("Starting debug write...")
        parser.write_validation_data(
            temp_file,
            sample_data,
            dataset_name='test_dataset.parquet',
            method='percentile_95'
        )
        
        print("\nReading back result...")
        with open(temp_file, 'r') as f:
            content = f.read()
        
        print(f"Final file length: {len(content)}")
        print("Checking for expected values:")
        print(f"  hip_flexion_angle_ipsi_rad: {'hip_flexion_angle_ipsi_rad' in content}")
        print(f"  0.349: {'0.349' in content}")
        
    finally:
        os.unlink(temp_file)

if __name__ == '__main__':
    debug_write_pipeline()