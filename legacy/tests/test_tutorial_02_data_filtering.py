#!/usr/bin/env python3
"""
Test Tutorial 02: Data Filtering

Created: 2025-08-07
Purpose: Test all code examples from Tutorial 02 - Data Filtering

This test validates that all code snippets from the data filtering tutorial
work correctly with our mock dataset.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from locohub import LocomotionData

# Path to mock dataset
MOCK_DATASET = Path(__file__).parent / 'mock_data' / 'mock_dataset_phase.parquet'


def test_basic_filtering():
    """Test basic subject and task filtering."""
    print("Testing basic filtering...")
    
    # Using Library
    data = LocomotionData(str(MOCK_DATASET))
    
    # Single subject filtering
    sub1_data = data.filter(subject='SUB01')
    assert len(sub1_data.df['subject'].unique()) == 1
    assert sub1_data.df['subject'].unique()[0] == 'SUB01'
    print(f"  Single subject: {len(sub1_data.df)} rows")
    
    # Single task filtering
    level_data = data.filter(task='level_walking')
    assert len(level_data.df['task'].unique()) == 1
    assert level_data.df['task'].unique()[0] == 'level_walking'
    print(f"  Single task: {len(level_data.df)} rows")
    
    # Combined filtering
    combined = data.filter(subject='SUB01', task='level_walking')
    assert len(combined.df['subject'].unique()) == 1
    assert len(combined.df['task'].unique()) == 1
    print(f"  Combined: {len(combined.df)} rows")
    
    print("✓ Basic filtering successful")


def test_raw_filtering():
    """Test filtering with raw pandas."""
    print("\nTesting raw pandas filtering...")
    
    data = pd.read_parquet(MOCK_DATASET)
    
    # Single subject
    sub1_data = data[data['subject'] == 'SUB01']
    assert len(sub1_data['subject'].unique()) == 1
    print(f"  Single subject: {len(sub1_data)} rows")
    
    # Single task
    level_data = data[data['task'] == 'level_walking']
    assert len(level_data['task'].unique()) == 1
    print(f"  Single task: {len(level_data)} rows")
    
    # Combined filtering
    combined = data[(data['subject'] == 'SUB01') & (data['task'] == 'level_walking')]
    assert len(combined) == 750  # 5 cycles * 150 points
    print(f"  Combined: {len(combined)} rows")
    
    print("✓ Raw filtering successful")


def test_multiple_subjects():
    """Test filtering multiple subjects."""
    print("\nTesting multiple subject filtering...")
    
    # Using Library
    data = LocomotionData(str(MOCK_DATASET))
    
    # Filter multiple subjects
    multi_sub = data.filter(subject=['SUB01', 'SUB02'])
    unique_subjects = sorted(multi_sub.df['subject'].unique())
    assert unique_subjects == ['SUB01', 'SUB02']
    print(f"  Multiple subjects: {unique_subjects}")
    
    # Using Raw Data
    raw_data = pd.read_parquet(MOCK_DATASET)
    multi_sub_raw = raw_data[raw_data['subject'].isin(['SUB01', 'SUB02'])]
    assert len(multi_sub_raw['subject'].unique()) == 2
    
    print("✓ Multiple subject filtering successful")


def test_multiple_tasks():
    """Test filtering multiple tasks."""
    print("\nTesting multiple task filtering...")
    
    # Using Library
    data = LocomotionData(str(MOCK_DATASET))
    
    # Filter multiple tasks
    multi_task = data.filter(task=['level_walking', 'incline_walking'])
    unique_tasks = sorted(multi_task.df['task'].unique())
    assert unique_tasks == ['incline_walking', 'level_walking']
    print(f"  Multiple tasks: {unique_tasks}")
    
    # Using Raw Data
    raw_data = pd.read_parquet(MOCK_DATASET)
    multi_task_raw = raw_data[raw_data['task'].isin(['level_walking', 'incline_walking'])]
    assert len(multi_task_raw['task'].unique()) == 2
    
    print("✓ Multiple task filtering successful")


def test_cycle_filtering():
    """Test filtering specific cycles."""
    print("\nTesting cycle filtering...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Get specific subject/task combination
    filtered = data.filter(subject='SUB01', task='level_walking')
    
    # Get unique cycles
    unique_cycles = filtered.df['cycle_id'].unique()
    print(f"  Available cycles: {len(unique_cycles)}")
    assert len(unique_cycles) == 5, f"Expected 5 cycles, got {len(unique_cycles)}"
    
    # Filter to first 3 cycles
    first_cycles = unique_cycles[:3]
    cycle_filtered = filtered.df[filtered.df['cycle_id'].isin(first_cycles)]
    assert len(cycle_filtered['cycle_id'].unique()) == 3
    print(f"  Filtered to {len(cycle_filtered['cycle_id'].unique())} cycles")
    
    print("✓ Cycle filtering successful")


def test_phase_range_filtering():
    """Test filtering specific phase ranges."""
    print("\nTesting phase range filtering...")
    
    data = LocomotionData(str(MOCK_DATASET))
    sub1_level = data.filter(subject='SUB01', task='level_walking')
    
    # Filter stance phase (0-60% of gait cycle)
    stance_phase = sub1_level.df[sub1_level.df['phase_percent'] <= 60]
    
    # Should have 60% of points per cycle
    expected_points = int(150 * 0.6) * 5  # 90 points * 5 cycles
    # Allow for slight variation due to linspace endpoint handling
    assert abs(len(stance_phase) - expected_points) <= 5
    print(f"  Stance phase: {len(stance_phase)} points")
    
    # Filter swing phase (60-100% of gait cycle)
    swing_phase = sub1_level.df[sub1_level.df['phase_percent'] > 60]
    print(f"  Swing phase: {len(swing_phase)} points")
    
    # Total should equal original
    total = len(stance_phase) + len(swing_phase)
    assert total == len(sub1_level.df), f"Phase split mismatch: {total} vs {len(sub1_level.df)}"
    
    print("✓ Phase range filtering successful")


def test_value_based_filtering():
    """Test filtering based on biomechanical values."""
    print("\nTesting value-based filtering...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Get all data for a specific subject
    sub1_data = data.filter(subject='SUB01')
    
    # Filter based on knee flexion angle
    if 'knee_flexion_angle_ipsi_rad' in sub1_data.df.columns:
        # Find high knee flexion points (> 1.0 rad ~ 57 degrees)
        high_flexion = sub1_data.df[sub1_data.df['knee_flexion_angle_ipsi_rad'] > 1.0]
        print(f"  High knee flexion points: {len(high_flexion)}")
        
        # Find low knee flexion points (< 0.2 rad ~ 11 degrees)
        low_flexion = sub1_data.df[sub1_data.df['knee_flexion_angle_ipsi_rad'] < 0.2]
        print(f"  Low knee flexion points: {len(low_flexion)}")
        
        # Verify some points exist in each category
        assert len(high_flexion) > 0, "Should have some high flexion points"
        assert len(low_flexion) > 0, "Should have some low flexion points"
    
    print("✓ Value-based filtering successful")


def test_chained_filtering():
    """Test chaining multiple filter operations."""
    print("\nTesting chained filtering...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Chain multiple filters
    filtered = (data
                .filter(subject=['SUB01', 'SUB02'])
                .filter(task='level_walking'))
    
    # Verify results
    unique_subjects = sorted(filtered.df['subject'].unique())
    unique_tasks = filtered.df['task'].unique()
    
    assert unique_subjects == ['SUB01', 'SUB02']
    assert len(unique_tasks) == 1
    assert unique_tasks[0] == 'level_walking'
    
    # Expected: 2 subjects * 5 cycles * 150 points = 1500 rows
    expected_rows = 2 * 5 * 150
    assert len(filtered.df) == expected_rows
    
    print(f"  Chained filter result: {len(filtered.df)} rows")
    print("✓ Chained filtering successful")


def test_query_method():
    """Test pandas query method for complex filtering."""
    print("\nTesting query method...")
    
    data = pd.read_parquet(MOCK_DATASET)
    
    # Complex query
    query_result = data.query("subject == 'SUB01' and task in ['level_walking', 'incline_walking']")
    
    # Verify results
    assert len(query_result['subject'].unique()) == 1
    assert len(query_result['task'].unique()) == 2
    
    print(f"  Query result: {len(query_result)} rows")
    
    # Query with numeric condition
    if 'knee_flexion_angle_ipsi_rad' in data.columns:
        complex_query = data.query(
            "subject == 'SUB01' and task == 'level_walking' and knee_flexion_angle_ipsi_rad > 0.5"
        )
        print(f"  Complex query result: {len(complex_query)} rows")
        assert len(complex_query) > 0
    
    print("✓ Query method successful")


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TUTORIAL 02: DATA FILTERING")
    print("="*60)
    
    # Check mock dataset exists
    if not MOCK_DATASET.exists():
        print(f"ERROR: Mock dataset not found at {MOCK_DATASET}")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    try:
        test_basic_filtering()
        test_raw_filtering()
        test_multiple_subjects()
        test_multiple_tasks()
        test_cycle_filtering()
        test_phase_range_filtering()
        test_value_based_filtering()
        test_chained_filtering()
        test_query_method()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())