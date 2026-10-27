#!/usr/bin/env python3
"""
Test Tutorial 01: Loading Data Efficiently

Created: 2025-08-07
Purpose: Test all code examples from Tutorial 01 - Loading Data

This test validates that all code snippets from the loading data tutorial
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


def test_basic_loading():
    """Test basic dataset loading using library."""
    print("Testing basic loading...")
    
    # Load a complete phase-indexed dataset
    data = LocomotionData(str(MOCK_DATASET))
    
    # Check dataset shape
    print(f"Dataset shape: {data.df.shape}")
    print(f"Memory usage: {data.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    assert data.df.shape[0] == 6750, f"Expected 6750 rows, got {data.df.shape[0]}"
    assert data.df.shape[1] >= 25, f"Expected at least 25 columns, got {data.df.shape[1]}"
    print("✓ Basic loading successful")


def test_raw_data_loading():
    """Test loading using raw pandas."""
    print("\nTesting raw data loading...")
    
    # Load a complete phase-indexed dataset
    data = pd.read_parquet(MOCK_DATASET)
    
    # Check dataset size
    print(f"Dataset shape: {data.shape}")
    print(f"Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    assert data.shape[0] == 6750, f"Expected 6750 rows, got {data.shape[0]}"
    print("✓ Raw data loading successful")


def test_understanding_structure():
    """Test understanding the data structure."""
    print("\nTesting data structure understanding...")
    
    # Using library
    data = LocomotionData(str(MOCK_DATASET))
    
    # View column names
    print("Available columns (sample):")
    variables = data.features  # Use features attribute
    print(f"  {variables[:3]}...")
    
    # Check data types
    print("\nData types (sample):")
    dtypes = data.df.dtypes
    print(f"  {list(dtypes.items())[:3]}...")
    
    # Preview first few rows
    print("\nFirst 5 rows preview")
    preview = data.df.head()
    assert len(preview) == 5, "Head should return 5 rows"
    
    print("✓ Structure understanding successful")


def test_column_selection():
    """Test memory-efficient column selection."""
    print("\nTesting column selection...")
    
    # Note: LocomotionData doesn't support column selection during init
    # We'll demonstrate the concept using pandas directly after loading
    
    # Load full dataset
    data_full = LocomotionData(str(MOCK_DATASET))
    
    # Simulate column selection by subsetting the DataFrame
    selected_columns = [
        'subject', 
        'task', 
        'cycle_id',
        'phase_ipsi',
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad'
    ]
    
    # Filter to selected columns
    data_efficient_df = data_full.df[selected_columns].copy()
    
    # Compare memory usage
    full_memory = data_full.df.memory_usage(deep=True).sum() / 1024**2
    efficient_memory = data_efficient_df.memory_usage(deep=True).sum() / 1024**2
    
    print(f"Full dataset: {full_memory:.2f} MB")
    print(f"Selected columns: {efficient_memory:.2f} MB")
    print(f"Memory saved: {(1 - efficient_memory/full_memory)*100:.1f}%")
    
    assert efficient_memory < full_memory, "Selected columns should use less memory"
    assert len(data_efficient_df.columns) == 6, f"Expected 6 columns, got {len(data_efficient_df.columns)}"
    
    print("✓ Column selection successful")


def test_raw_column_selection():
    """Test column selection with raw pandas."""
    print("\nTesting raw pandas column selection...")
    
    # Define columns to load
    selected_columns = [
        'subject', 
        'task', 
        'cycle_id',
        'phase_percent',
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad'
    ]
    
    # Load with column selection
    data = pd.read_parquet(MOCK_DATASET, columns=selected_columns)
    
    assert len(data.columns) == 6, f"Expected 6 columns, got {len(data.columns)}"
    assert set(data.columns) == set(selected_columns), "Column mismatch"
    
    print(f"Loaded {len(data.columns)} columns successfully")
    print("✓ Raw column selection successful")


def test_subject_task_listing():
    """Test listing subjects and tasks."""
    print("\nTesting subject and task listing...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Get subjects
    subjects = data.get_subjects()
    print(f"Subjects: {subjects}")
    assert subjects == ['SUB01', 'SUB02', 'SUB03'], f"Unexpected subjects: {subjects}"
    
    # Get tasks
    tasks = data.get_tasks()
    print(f"Tasks: {tasks}")
    expected_tasks = ['level_walking', 'incline_walking', 'decline_walking']
    assert set(tasks) == set(expected_tasks), f"Unexpected tasks: {tasks}"
    
    print("✓ Subject and task listing successful")


def test_data_filtering():
    """Test basic data filtering."""
    print("\nTesting data filtering...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Filter for specific subject and task using pandas operations
    filtered_df = data.df[(data.df['subject'] == 'SUB01') & (data.df['task'] == 'level_walking')]
    
    # Check filtered data
    unique_subjects = filtered_df['subject'].unique()
    unique_tasks = filtered_df['task'].unique()
    
    assert len(unique_subjects) == 1, "Should have only one subject"
    assert unique_subjects[0] == 'SUB01', "Should be SUB01"
    assert len(unique_tasks) == 1, "Should have only one task"
    assert unique_tasks[0] == 'level_walking', "Should be level_walking"
    
    # Expected: 5 cycles * 150 points = 750 rows
    expected_rows = 5 * 150
    assert len(filtered_df) == expected_rows, f"Expected {expected_rows} rows, got {len(filtered_df)}"
    
    print(f"Filtered to {len(filtered_df)} rows")
    print("✓ Data filtering successful")


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TUTORIAL 01: LOADING DATA")
    print("="*60)
    
    # Check mock dataset exists
    if not MOCK_DATASET.exists():
        print(f"ERROR: Mock dataset not found at {MOCK_DATASET}")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    try:
        test_basic_loading()
        test_raw_data_loading()
        test_understanding_structure()
        test_column_selection()
        test_raw_column_selection()
        test_subject_task_listing()
        test_data_filtering()
        
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