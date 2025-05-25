#!/usr/bin/env python3
"""
Generate validation GIFs for representative subject-task combinations
"""
import subprocess
import os
import sys

# Representative subject-task combinations to validate
validation_cases = [
    # Gtech 2023 dataset
    {
        'file': 'source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet',
        'subject': 'Gtech_2023_AB01',
        'task': 'normal_walk',
        'output': 'validation_gtech_normal_walk.gif'
    },
    {
        'file': 'source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet',
        'subject': 'Gtech_2023_AB01',
        'task': 'incline_walk',
        'output': 'validation_gtech_incline_walk.gif'
    },
    {
        'file': 'source/conversion_scripts/Gtech_2023/gtech_2023_phase.parquet',
        'subject': 'Gtech_2023_AB01',
        'task': 'stairs',
        'output': 'validation_gtech_stairs.gif'
    },
    # UMich 2021 dataset
    {
        'file': 'source/conversion_scripts/Umich_2021/umich_2021_phase.parquet',
        'subject': 'UMich_2021_RA03',
        'task': 'treadmill_levelwalk_1.2',
        'output': 'validation_umich_levelwalk.gif'
    },
    {
        'file': 'source/conversion_scripts/Umich_2021/umich_2021_phase.parquet',
        'subject': 'UMich_2021_RA03',
        'task': 'treadmill_incline10_1.2',
        'output': 'validation_umich_incline.gif'
    }
]

# Create output directory
output_dir = 'validation_gifs'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

# Generate GIFs
for case in validation_cases:
    print(f"\nGenerating GIF for {case['subject']} - {case['task']}...")
    
    cmd = [
        'python3', 'source/visualization/walking_animator.py',
        '-f', case['file'],
        '-s', case['subject'],
        '-t', case['task'],
        '--save-gif'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Move the generated GIF to our output directory
            # The walking_animator saves GIFs with a specific naming pattern
            expected_gif = f"{case['subject']}_{case['task']}.gif"
            if os.path.exists(expected_gif):
                os.rename(expected_gif, os.path.join(output_dir, case['output']))
                print(f"✓ Successfully created {case['output']}")
            else:
                print(f"⚠ GIF generation completed but file not found: {expected_gif}")
        else:
            print(f"✗ Failed to generate GIF")
            print(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout after 60 seconds")
    except Exception as e:
        print(f"✗ Error: {str(e)}")

print(f"\n{'='*50}")
print(f"GIF generation complete. Check the '{output_dir}' directory.")