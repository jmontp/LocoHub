#!/usr/bin/env python3
"""
Test Tutorial 04: Cycle Analysis

Created: 2025-08-07
Purpose: Test all code examples from Tutorial 04 - Cycle Analysis

This test validates cycle extraction, 3D array operations, and cycle-based
analysis from the tutorial.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from user_libs.python.locomotion_data import LocomotionData

# Path to mock dataset
MOCK_DATASET = Path(__file__).parent / 'mock_data' / 'mock_dataset_phase.parquet'


def test_cycle_extraction():
    """Test extracting individual cycles."""
    print("Testing cycle extraction...")
    
    # Using Library
    data = LocomotionData(str(MOCK_DATASET))
    
    # Extract cycles for specific subject/task
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Check shape: (n_cycles, n_points, n_features)
    assert cycles_3d is not None, "Failed to extract cycles"
    assert len(cycles_3d.shape) == 3, f"Expected 3D array, got shape {cycles_3d.shape}"
    
    n_cycles, n_points, n_features = cycles_3d.shape
    assert n_cycles == 5, f"Expected 5 cycles, got {n_cycles}"
    assert n_points == 150, f"Expected 150 points per cycle, got {n_points}"
    
    print(f"  Extracted shape: {cycles_3d.shape}")
    print(f"  Features: {features[:3]}...")
    
    print("✓ Cycle extraction successful")


def test_3d_array_indexing():
    """Test 3D array indexing and slicing."""
    print("\nTesting 3D array indexing...")
    
    data = LocomotionData(str(MOCK_DATASET))
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Get first cycle
    first_cycle = cycles_3d[0, :, :]
    assert first_cycle.shape == (150, len(features))
    print(f"  First cycle shape: {first_cycle.shape}")
    
    # Get all cycles at 50% gait (index 75)
    midstance = cycles_3d[:, 75, :]
    assert midstance.shape == (5, len(features))
    print(f"  Midstance values shape: {midstance.shape}")
    
    # Get knee flexion for all cycles (assuming it's in features)
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        knee_all_cycles = cycles_3d[:, :, knee_idx]
        assert knee_all_cycles.shape == (5, 150)
        print(f"  Knee flexion shape: {knee_all_cycles.shape}")
    
    print("✓ 3D array indexing successful")


def test_cycle_statistics():
    """Test computing statistics across cycles."""
    print("\nTesting cycle statistics...")
    
    data = LocomotionData(str(MOCK_DATASET))
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Compute mean across cycles (axis=0)
    mean_pattern = np.mean(cycles_3d, axis=0)
    assert mean_pattern.shape == (150, len(features))
    print(f"  Mean pattern shape: {mean_pattern.shape}")
    
    # Compute std across cycles
    std_pattern = np.std(cycles_3d, axis=0)
    assert std_pattern.shape == (150, len(features))
    print(f"  Std pattern shape: {std_pattern.shape}")
    
    # Compute cycle-to-cycle variability
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        knee_cycles = cycles_3d[:, :, knee_idx]
        
        # Coefficient of variation at each point
        cv = np.std(knee_cycles, axis=0) / (np.mean(knee_cycles, axis=0) + 1e-10)
        assert len(cv) == 150
        print(f"  CV range: {cv.min():.3f} to {cv.max():.3f}")
    
    print("✓ Cycle statistics successful")


def test_range_of_motion():
    """Test ROM calculation for each cycle."""
    print("\nTesting range of motion calculation...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Using library method
    rom_data = data.calculate_rom('SUB01', 'level_walking')
    
    assert rom_data is not None, "ROM calculation failed"
    assert len(rom_data) > 0, "No ROM data returned"
    
    # Check specific joint if available
    if 'knee_flexion_angle_ipsi_rad' in rom_data:
        knee_rom = rom_data['knee_flexion_angle_ipsi_rad']
        assert len(knee_rom) == 5, f"Expected 5 ROM values, got {len(knee_rom)}"
        
        # Convert to degrees for display
        knee_rom_deg = np.degrees(knee_rom)
        print(f"  Knee ROM (degrees): {knee_rom_deg.mean():.1f} ± {knee_rom_deg.std():.1f}")
    
    # Manual calculation
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        knee_cycles = cycles_3d[:, :, knee_idx]
        
        # Calculate ROM for each cycle
        rom_manual = np.max(knee_cycles, axis=1) - np.min(knee_cycles, axis=1)
        assert len(rom_manual) == 5
        print(f"  Manual ROM calculation: {len(rom_manual)} cycles")
    
    print("✓ ROM calculation successful")


def test_peak_detection():
    """Test finding peaks in gait cycles."""
    print("\nTesting peak detection...")
    
    data = LocomotionData(str(MOCK_DATASET))
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        knee_cycles = cycles_3d[:, :, knee_idx]
        
        # Find peaks for each cycle
        peaks_per_cycle = []
        for cycle in knee_cycles:
            # Simple peak: maximum value
            peak_value = np.max(cycle)
            peak_index = np.argmax(cycle)
            peak_phase = (peak_index / 150) * 100
            peaks_per_cycle.append({
                'value': peak_value,
                'index': peak_index,
                'phase': peak_phase
            })
        
        assert len(peaks_per_cycle) == 5
        
        # Average peak timing
        avg_peak_phase = np.mean([p['phase'] for p in peaks_per_cycle])
        print(f"  Average peak phase: {avg_peak_phase:.1f}%")
        
        # Peak value variability
        peak_values = [p['value'] for p in peaks_per_cycle]
        print(f"  Peak values (rad): {np.mean(peak_values):.3f} ± {np.std(peak_values):.3f}")
    
    print("✓ Peak detection successful")


def test_cycle_validation():
    """Test cycle validation and outlier detection."""
    print("\nTesting cycle validation...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Validate cycles
    valid_mask = data.validate_cycles('SUB01', 'level_walking')
    
    assert valid_mask is not None, "Validation failed"
    assert len(valid_mask) == 5, f"Expected 5 validation results, got {len(valid_mask)}"
    
    n_valid = np.sum(valid_mask)
    print(f"  Valid cycles: {n_valid}/{len(valid_mask)}")
    
    # Find outlier cycles
    outliers = data.find_outlier_cycles('SUB01', 'level_walking')
    
    if outliers is not None:
        n_outliers = np.sum(outliers)
        print(f"  Outlier cycles: {n_outliers}/{len(outliers)}")
    
    print("✓ Cycle validation successful")


def test_phase_specific_analysis():
    """Test analysis at specific gait phases."""
    print("\nTesting phase-specific analysis...")
    
    data = LocomotionData(str(MOCK_DATASET))
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Define key phases
    phases = {
        'heel_strike': 0,      # 0% gait cycle
        'midstance': 37,       # ~25% gait cycle (37/150)
        'toe_off': 90,         # ~60% gait cycle
        'midswing': 127        # ~85% gait cycle
    }
    
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        
        for phase_name, phase_idx in phases.items():
            # Get values at this phase for all cycles
            phase_values = cycles_3d[:, phase_idx, knee_idx]
            assert len(phase_values) == 5
            
            phase_deg = np.degrees(phase_values)
            print(f"  {phase_name}: {phase_deg.mean():.1f} ± {phase_deg.std():.1f} deg")
    
    print("✓ Phase-specific analysis successful")


def test_cycle_alignment():
    """Test cycle alignment and comparison."""
    print("\nTesting cycle alignment...")
    
    data = LocomotionData(str(MOCK_DATASET))
    
    # Get cycles for two different tasks
    level_cycles, level_features = data.get_cycles('SUB01', 'level_walking')
    incline_cycles, incline_features = data.get_cycles('SUB01', 'incline_walking')
    
    assert level_cycles is not None and incline_cycles is not None
    
    # Both should have same structure
    assert level_cycles.shape[1:] == incline_cycles.shape[1:], "Shape mismatch between tasks"
    
    # Compare mean patterns
    level_mean = np.mean(level_cycles, axis=0)
    incline_mean = np.mean(incline_cycles, axis=0)
    
    # Calculate difference
    pattern_diff = incline_mean - level_mean
    
    if 'knee_flexion_angle_ipsi_rad' in level_features:
        knee_idx = level_features.index('knee_flexion_angle_ipsi_rad')
        knee_diff = pattern_diff[:, knee_idx]
        
        max_diff = np.max(np.abs(knee_diff))
        print(f"  Max difference between tasks: {np.degrees(max_diff):.1f} degrees")
    
    print("✓ Cycle alignment successful")


def test_temporal_parameters():
    """Test extracting temporal parameters from cycles."""
    print("\nTesting temporal parameters...")
    
    data = LocomotionData(str(MOCK_DATASET))
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Since we have phase-indexed data, we can analyze phase durations
    # In real data, you'd calculate stride time, stance%, etc.
    
    # Simulate finding stance/swing transition
    if 'knee_flexion_angle_ipsi_rad' in features:
        knee_idx = features.index('knee_flexion_angle_ipsi_rad')
        
        for cycle_idx in range(cycles_3d.shape[0]):
            cycle = cycles_3d[cycle_idx, :, knee_idx]
            
            # Find minimum in early cycle (typical toe-off region)
            toe_off_region = cycle[85:95]  # Around 60% gait
            toe_off_idx = 85 + np.argmin(toe_off_region)
            toe_off_phase = (toe_off_idx / 150) * 100
            
            # Store would-be temporal parameters
            stance_percent = toe_off_phase
            swing_percent = 100 - toe_off_phase
        
        print(f"  Example stance%: {stance_percent:.1f}%")
        print(f"  Example swing%: {swing_percent:.1f}%")
    
    print("✓ Temporal parameters successful")


def main():
    """Run all tests."""
    print("="*60)
    print("TESTING TUTORIAL 04: CYCLE ANALYSIS")
    print("="*60)
    
    # Check mock dataset exists
    if not MOCK_DATASET.exists():
        print(f"ERROR: Mock dataset not found at {MOCK_DATASET}")
        print("Please run: python tests/generate_mock_dataset.py")
        return 1
    
    try:
        test_cycle_extraction()
        test_3d_array_indexing()
        test_cycle_statistics()
        test_range_of_motion()
        test_peak_detection()
        test_cycle_validation()
        test_phase_specific_analysis()
        test_cycle_alignment()
        test_temporal_parameters()
        
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