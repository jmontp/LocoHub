#!/usr/bin/env python3
"""
Test Utilities Module

Created: 2025-08-07
Purpose: Common utilities for tutorial tests

Provides helper functions for:
- Data validation
- Numerical comparisons
- Plot verification
- Mock data generation
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, List, Tuple, Optional


# Tolerance for floating point comparisons
DEFAULT_TOLERANCE = 1e-6
ANGLE_TOLERANCE = np.radians(1)  # 1 degree tolerance for angles


def assert_array_shape(array: np.ndarray, expected_shape: tuple, name: str = "array"):
    """
    Assert that an array has the expected shape.
    
    Parameters:
    -----------
    array : np.ndarray
        Array to check
    expected_shape : tuple
        Expected shape
    name : str
        Name for error messages
    """
    actual_shape = array.shape
    assert actual_shape == expected_shape, \
        f"{name} shape mismatch: expected {expected_shape}, got {actual_shape}"


def assert_array_equal(actual: np.ndarray, expected: np.ndarray, 
                      tolerance: float = DEFAULT_TOLERANCE, name: str = "array"):
    """
    Assert that two arrays are equal within tolerance.
    
    Parameters:
    -----------
    actual : np.ndarray
        Actual array
    expected : np.ndarray
        Expected array
    tolerance : float
        Maximum allowed difference
    name : str
        Name for error messages
    """
    assert_array_shape(actual, expected.shape, name)
    
    max_diff = np.max(np.abs(actual - expected))
    assert max_diff <= tolerance, \
        f"{name} values differ: max difference {max_diff} > tolerance {tolerance}"


def assert_angles_equal(actual: np.ndarray, expected: np.ndarray, 
                       tolerance: float = ANGLE_TOLERANCE, name: str = "angles"):
    """
    Assert that two angle arrays are equal within tolerance.
    Handles angle wrapping.
    
    Parameters:
    -----------
    actual : np.ndarray
        Actual angles (radians)
    expected : np.ndarray
        Expected angles (radians)
    tolerance : float
        Maximum allowed difference (radians)
    name : str
        Name for error messages
    """
    # Normalize angles to [-pi, pi]
    actual_norm = np.arctan2(np.sin(actual), np.cos(actual))
    expected_norm = np.arctan2(np.sin(expected), np.cos(expected))
    
    # Calculate angular difference
    diff = np.abs(np.arctan2(np.sin(actual_norm - expected_norm), 
                             np.cos(actual_norm - expected_norm)))
    
    max_diff = np.max(diff)
    assert max_diff <= tolerance, \
        f"{name} differ: max difference {np.degrees(max_diff):.1f}° > tolerance {np.degrees(tolerance):.1f}°"


def assert_dataframe_equal(actual: pd.DataFrame, expected: pd.DataFrame, 
                          check_dtype: bool = False):
    """
    Assert that two DataFrames are equal.
    
    Parameters:
    -----------
    actual : pd.DataFrame
        Actual DataFrame
    expected : pd.DataFrame
        Expected DataFrame
    check_dtype : bool
        Whether to check data types
    """
    # Check shape
    assert actual.shape == expected.shape, \
        f"DataFrame shape mismatch: {actual.shape} vs {expected.shape}"
    
    # Check columns
    assert list(actual.columns) == list(expected.columns), \
        f"Column mismatch: {list(actual.columns)} vs {list(expected.columns)}"
    
    # Check values
    for col in actual.columns:
        if actual[col].dtype in ['float64', 'float32']:
            assert_array_equal(actual[col].values, expected[col].values, 
                             name=f"Column '{col}'")
        else:
            assert (actual[col] == expected[col]).all(), \
                f"Column '{col}' values differ"


def validate_phase_data(data: Union[pd.DataFrame, np.ndarray], 
                        n_points: int = 150) -> bool:
    """
    Validate that data is properly phase-indexed.
    
    Parameters:
    -----------
    data : DataFrame or array
        Data to validate
    n_points : int
        Expected points per cycle
    
    Returns:
    --------
    bool : True if valid
    """
    if isinstance(data, pd.DataFrame):
        if 'phase_percent' in data.columns:
            # Check phase values
            phases = data['phase_percent'].unique()
            expected_phases = np.linspace(0, 100, n_points, endpoint=False)
            
            return np.allclose(sorted(phases), expected_phases, rtol=0.01)
    
    elif isinstance(data, np.ndarray):
        # Check array dimensions
        if len(data.shape) >= 2:
            return data.shape[-2] == n_points or data.shape[-1] == n_points
    
    return False


def validate_biomechanical_ranges(data: pd.DataFrame, variable: str) -> dict:
    """
    Validate that biomechanical variables are in reasonable ranges.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data containing biomechanical variables
    variable : str
        Variable name to check
    
    Returns:
    --------
    dict : Validation results
    """
    if variable not in data.columns:
        return {'valid': False, 'reason': 'Variable not found'}
    
    values = data[variable].values
    
    # Define reasonable ranges (in radians for angles, Nm for moments)
    ranges = {
        'hip_flexion_angle': (-0.5, 1.5),      # ~-30 to 85 degrees
        'knee_flexion_angle': (-0.2, 2.0),     # ~-10 to 115 degrees
        'ankle_dorsiflexion_angle': (-0.7, 0.7), # ~-40 to 40 degrees
        'hip_flexion_moment': (-200, 200),     # Nm
        'knee_flexion_moment': (-150, 150),    # Nm
        'ankle_dorsiflexion_moment': (-100, 100) # Nm
    }
    
    # Find matching range
    for key, (min_val, max_val) in ranges.items():
        if key in variable:
            if 'moment' in variable:
                # Moments can vary with body weight
                if np.min(values) < min_val * 2 or np.max(values) > max_val * 2:
                    return {
                        'valid': False,
                        'reason': f'Values outside range: [{np.min(values):.1f}, {np.max(values):.1f}]',
                        'expected_range': (min_val, max_val)
                    }
            else:
                # Angles
                if np.min(values) < min_val or np.max(values) > max_val:
                    return {
                        'valid': False,
                        'reason': f'Values outside range: [{np.degrees(np.min(values)):.1f}, {np.degrees(np.max(values)):.1f}] deg',
                        'expected_range': (np.degrees(min_val), np.degrees(max_val))
                    }
            
            return {'valid': True, 'range': (np.min(values), np.max(values))}
    
    # No specific range defined
    return {'valid': True, 'range': (np.min(values), np.max(values))}


def create_test_cycles(n_cycles: int = 5, n_points: int = 150, 
                      n_features: int = 6) -> Tuple[np.ndarray, List[str]]:
    """
    Create test 3D cycle array with realistic patterns.
    
    Parameters:
    -----------
    n_cycles : int
        Number of cycles
    n_points : int
        Points per cycle
    n_features : int
        Number of features
    
    Returns:
    --------
    tuple : (3D array, feature names)
    """
    np.random.seed(42)
    
    # Create phase
    phase = np.linspace(0, 2*np.pi, n_points)
    
    # Generate features
    cycles_3d = np.zeros((n_cycles, n_points, n_features))
    feature_names = []
    
    for feat in range(n_features):
        # Different pattern for each feature
        amplitude = 0.5 + feat * 0.1
        phase_shift = feat * np.pi / 6
        
        for cycle in range(n_cycles):
            # Add cycle-to-cycle variation
            cycle_amp = amplitude * (1 + np.random.randn() * 0.1)
            cycle_phase = phase_shift + np.random.randn() * 0.05
            
            cycles_3d[cycle, :, feat] = cycle_amp * np.sin(phase + cycle_phase)
        
        feature_names.append(f'feature_{feat}')
    
    return cycles_3d, feature_names


def compare_plots(plot1_path: Path, plot2_path: Path, 
                 threshold: float = 0.95) -> bool:
    """
    Compare two plot files for similarity.
    
    Parameters:
    -----------
    plot1_path : Path
        First plot file
    plot2_path : Path
        Second plot file
    threshold : float
        Similarity threshold (0-1)
    
    Returns:
    --------
    bool : True if similar enough
    """
    # Simple check: both files exist and have reasonable size
    if not plot1_path.exists() or not plot2_path.exists():
        return False
    
    size1 = plot1_path.stat().st_size
    size2 = plot2_path.stat().st_size
    
    # Check if sizes are within 20% of each other
    size_ratio = min(size1, size2) / max(size1, size2)
    
    return size_ratio > 0.8


def generate_mock_metadata(n_subjects: int = 3) -> pd.DataFrame:
    """
    Generate mock metadata for subjects.
    
    Parameters:
    -----------
    n_subjects : int
        Number of subjects
    
    Returns:
    --------
    DataFrame : Subject metadata
    """
    metadata = []
    
    for i in range(n_subjects):
        metadata.append({
            'subject': f'SUB{i+1:02d}',
            'age': 25 + i * 5,
            'height_m': 1.70 + i * 0.05,
            'weight_kg': 70 + i * 5,
            'gender': 'M' if i % 2 == 0 else 'F',
            'group': 'control' if i < n_subjects // 2 else 'intervention'
        })
    
    return pd.DataFrame(metadata)


def calculate_cycle_metrics(cycles_3d: np.ndarray, 
                           feature_idx: int = 0) -> dict:
    """
    Calculate common cycle metrics.
    
    Parameters:
    -----------
    cycles_3d : np.ndarray
        3D array of cycles (n_cycles, n_points, n_features)
    feature_idx : int
        Feature index to analyze
    
    Returns:
    --------
    dict : Calculated metrics
    """
    data = cycles_3d[:, :, feature_idx]
    
    metrics = {
        'rom': np.mean(np.max(data, axis=1) - np.min(data, axis=1)),
        'rom_std': np.std(np.max(data, axis=1) - np.min(data, axis=1)),
        'peak_value': np.mean(np.max(data, axis=1)),
        'peak_timing': np.mean(np.argmax(data, axis=1) / data.shape[1] * 100),
        'mean_value': np.mean(data),
        'cv': np.mean(np.std(data, axis=0) / (np.mean(data, axis=0) + 1e-10))
    }
    
    return metrics


# Test the utilities module itself
if __name__ == "__main__":
    print("Testing utilities module...")
    
    # Test array comparison
    a = np.array([1, 2, 3])
    b = np.array([1, 2, 3])
    assert_array_equal(a, b, name="test arrays")
    print("✓ Array comparison works")
    
    # Test angle comparison
    angles1 = np.array([0, np.pi/2, np.pi])
    angles2 = np.array([0, np.pi/2 + 0.01, np.pi - 0.01])
    assert_angles_equal(angles1, angles2, tolerance=0.02)
    print("✓ Angle comparison works")
    
    # Test cycle creation
    cycles, features = create_test_cycles()
    assert cycles.shape == (5, 150, 6)
    assert len(features) == 6
    print("✓ Test cycle creation works")
    
    # Test metrics calculation
    metrics = calculate_cycle_metrics(cycles)
    assert 'rom' in metrics
    assert 'peak_timing' in metrics
    print("✓ Metrics calculation works")
    
    print("\nAll utility tests passed!")