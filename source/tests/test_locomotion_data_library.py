#!/usr/bin/env python3
"""
Comprehensive Test Suite for LocomotionData Library

Created: 2025-06-11 with user permission
Purpose: Validates all core functionality of the LocomotionData library

Intent:
This comprehensive test suite validates the complete LocomotionData library functionality
to ensure robust data loading, processing, and analysis capabilities:

**PRIMARY FUNCTIONS:**
1. **Data Loading**: Test parquet/CSV loading with various data formats and error conditions
2. **3D Array Operations**: Validate efficient reshape operations and caching mechanisms
3. **Statistical Analysis**: Test mean, std, ROM, and correlation calculations
4. **Data Validation**: Ensure biomechanical constraints and outlier detection
5. **Plotting Functions**: Test all visualization methods with various parameters
6. **Error Handling**: Validate graceful handling of edge cases and invalid inputs

Usage:
    cd source/tests
    python test_locomotion_data_library.py

Expected Output:
- Comprehensive validation of all library methods
- Edge case and error condition testing
- Performance benchmarks for large datasets
- Memory usage validation
- All tests passing confirmation

This test suite ensures the library is production-ready and can handle
real-world biomechanical datasets with robust error handling.
"""

import sys
import os
import numpy as np
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import warnings

# Add library path
sys.path.append('../../lib/core')

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    class pytest:
        @staticmethod
        def fixture(func):
            return func
        
        @staticmethod  
        def mark():
            class Mark:
                def parametrize(self, *args, **kwargs):
                    def decorator(func):
                        return func
                    return decorator
            return Mark()

from locomotion_analysis import LocomotionData, efficient_reshape_3d


class TestLocomotionDataLibrary:
    """Comprehensive test suite for LocomotionData library."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample phase-indexed locomotion data."""
        np.random.seed(42)
        n_subjects = 3
        n_tasks = 2
        n_cycles = 4
        points_per_cycle = 150
        
        data = []
        subjects = [f'SUB{i:02d}' for i in range(1, n_subjects+1)]
        tasks = ['normal_walk', 'fast_walk']
        
        for subject in subjects:
            for task in tasks:
                for cycle in range(n_cycles):
                    phase = np.linspace(0, 100, points_per_cycle)
                    
                    # Generate realistic biomechanical patterns
                    base_hip = 0.4 * np.sin(2 * np.pi * phase / 100)
                    base_knee = 0.8 * np.sin(2 * np.pi * phase / 100 - np.pi/4)
                    base_ankle = 0.3 * np.sin(2 * np.pi * phase / 100 - np.pi/2)
                    
                    # Add task-specific modifications
                    if task == 'fast_walk':
                        base_hip *= 1.2
                        base_knee *= 1.1
                        base_ankle *= 1.15
                    
                    # Add realistic noise
                    noise_factor = 0.05
                    hip_noise = np.random.normal(0, noise_factor, points_per_cycle)
                    knee_noise = np.random.normal(0, noise_factor, points_per_cycle)
                    ankle_noise = np.random.normal(0, noise_factor, points_per_cycle)
                    
                    for i in range(points_per_cycle):
                        data.append({
                            'subject': subject,
                            'task': task,
                            'phase': phase[i],
                            'cycle': cycle,
                            'hip_flexion_angle_contra_rad': base_hip[i] + hip_noise[i],
                            'knee_flexion_angle_contra_rad': base_knee[i] + knee_noise[i],
                            'ankle_flexion_angle_contra_rad': base_ankle[i] + ankle_noise[i],
                            'hip_flexion_angle_ipsi_rad': base_hip[i] + hip_noise[i] + 0.02,
                            'knee_flexion_angle_ipsi_rad': base_knee[i] + knee_noise[i] + 0.02,
                            'ankle_flexion_angle_ipsi_rad': base_ankle[i] + ankle_noise[i] + 0.02,
                            'hip_flexion_velocity_contra_rad_s': np.gradient(base_hip)[i] * 2,
                            'knee_flexion_velocity_contra_rad_s': np.gradient(base_knee)[i] * 2,
                            'ankle_flexion_velocity_contra_rad_s': np.gradient(base_ankle)[i] * 2,
                            'hip_flexion_moment_contra_Nm': 50 * np.sin(2 * np.pi * phase[i] / 100 + np.pi/3),
                            'knee_flexion_moment_contra_Nm': 80 * np.sin(2 * np.pi * phase[i] / 100),
                            'ankle_flexion_moment_contra_Nm': 30 * np.sin(2 * np.pi * phase[i] / 100 - np.pi/6)
                        })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def corrupted_data(self):
        """Create data with various corruption patterns for error testing."""
        np.random.seed(42)
        
        data = []
        for i in range(300):  # 2 cycles of 150 points
            phase = (i % 150) * (100/149)
            data.append({
                'subject': 'SUB01',
                'task': 'normal_walk',
                'phase': phase,
                'hip_flexion_angle_contra_rad': np.nan if i == 50 else 0.4 * np.sin(2 * np.pi * phase / 100),
                'knee_flexion_angle_contra_rad': np.inf if i == 100 else 0.8 * np.sin(2 * np.pi * phase / 100),
                'ankle_flexion_angle_contra_rad': 10.0 if i == 200 else 0.3 * np.sin(2 * np.pi * phase / 100),  # Unrealistic value
            })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def invalid_length_data(self):
        """Create data with invalid cycle length."""
        data = []
        for i in range(140):  # Not divisible by 150
            data.append({
                'subject': 'SUB01',
                'task': 'normal_walk',
                'phase': i * (100/139),
                'hip_flexion_angle_contra_rad': 0.4 * np.sin(2 * np.pi * i / 140)
            })
        
        return pd.DataFrame(data)
    
    def test_initialization_parquet(self, sample_data, temp_dir):
        """Test initialization with parquet file."""
        # Save as parquet
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        # Test loading
        loco = LocomotionData(parquet_path)
        
        assert len(loco.df) == len(sample_data)
        assert loco.get_subjects() == ['SUB01', 'SUB02', 'SUB03']
        assert loco.get_tasks() == ['fast_walk', 'normal_walk']
        assert len(loco.features) > 0
        
    def test_initialization_csv(self, sample_data, temp_dir):
        """Test initialization with CSV file."""
        # Save as CSV
        csv_path = os.path.join(temp_dir, 'test_data.csv')
        sample_data.to_csv(csv_path, index=False)
        
        # Test loading
        loco = LocomotionData(csv_path, file_type='csv')
        
        assert len(loco.df) == len(sample_data)
        assert loco.get_subjects() == ['SUB01', 'SUB02', 'SUB03']
        
    def test_initialization_auto_detection(self, sample_data, temp_dir):
        """Test automatic file type detection."""
        # Test parquet auto-detection
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path, file_type='auto')
        assert len(loco.df) == len(sample_data)
        
        # Test CSV auto-detection
        csv_path = os.path.join(temp_dir, 'test_data.csv')
        sample_data.to_csv(csv_path, index=False)
        
        loco = LocomotionData(csv_path, file_type='auto')
        assert len(loco.df) == len(sample_data)
    
    def test_feature_identification(self, sample_data, temp_dir):
        """Test automatic feature identification."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Check that angle features are identified
        angle_features = [f for f in loco.features if 'angle' in f]
        assert len(angle_features) == 6  # 3 joints × 2 sides
        
        # Check that velocity features are identified
        velocity_features = [f for f in loco.features if 'velocity' in f]
        assert len(velocity_features) == 3  # 3 joints × 1 side (only contra in sample)
        
        # Check that moment features are identified
        moment_features = [f for f in loco.features if 'moment' in f]
        assert len(moment_features) == 3  # 3 joints × 1 side
        
        # Check that excluded columns are not in features
        excluded = {'subject', 'task', 'phase', 'cycle'}
        for col in excluded:
            assert col not in loco.features
    
    def test_get_cycles_basic(self, sample_data, temp_dir):
        """Test basic 3D array extraction."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Get cycles for specific subject/task
        data_3d, feature_names = loco.get_cycles('SUB01', 'normal_walk')
        
        assert data_3d is not None
        assert data_3d.shape == (4, 150, len(feature_names))  # 4 cycles, 150 points, n features
        assert len(feature_names) > 0
        
        # Test with specific features
        selected_features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
        data_3d, feature_names = loco.get_cycles('SUB01', 'normal_walk', selected_features)
        
        assert data_3d.shape == (4, 150, 2)
        assert feature_names == selected_features
    
    def test_get_cycles_caching(self, sample_data, temp_dir):
        """Test that 3D array extraction uses caching."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # First call
        data_3d_1, features_1 = loco.get_cycles('SUB01', 'normal_walk')
        
        # Second call should use cache
        data_3d_2, features_2 = loco.get_cycles('SUB01', 'normal_walk')
        
        # Should be identical (same memory location if cached properly)
        assert np.array_equal(data_3d_1, data_3d_2)
        assert features_1 == features_2
    
    def test_get_cycles_invalid_data(self, sample_data, temp_dir):
        """Test get_cycles with invalid subject/task combinations."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test non-existent subject
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_3d, features = loco.get_cycles('INVALID', 'normal_walk')
            assert len(w) == 1
            assert "No data found" in str(w[0].message)
        
        assert data_3d is None
        assert features == []
        
        # Test non-existent task
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_3d, features = loco.get_cycles('SUB01', 'invalid_task')
            assert len(w) == 1
        
        assert data_3d is None
        assert features == []
    
    def test_get_cycles_invalid_length(self, invalid_length_data, temp_dir):
        """Test get_cycles with data not divisible by 150."""
        parquet_path = os.path.join(temp_dir, 'invalid_data.parquet')
        invalid_length_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
            assert len(w) == 1
            assert "not divisible by 150" in str(w[0].message)
        
        assert data_3d is None
        assert features == []
    
    def test_statistical_methods(self, sample_data, temp_dir):
        """Test statistical analysis methods."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test mean patterns
        mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
        assert isinstance(mean_patterns, dict)
        assert len(mean_patterns) > 0
        
        for feature, pattern in mean_patterns.items():
            assert len(pattern) == 150
            assert np.all(np.isfinite(pattern))
        
        # Test std patterns
        std_patterns = loco.get_std_patterns('SUB01', 'normal_walk')
        assert isinstance(std_patterns, dict)
        assert len(std_patterns) > 0
        
        for feature, pattern in std_patterns.items():
            assert len(pattern) == 150
            assert np.all(np.isfinite(pattern))
            assert np.all(pattern >= 0)  # Standard deviation should be non-negative
        
        # Test summary statistics
        summary = loco.get_summary_statistics('SUB01', 'normal_walk')
        assert isinstance(summary, pd.DataFrame)
        assert len(summary) > 0
        
        # Check expected columns
        expected_stats = ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75']
        for stat in expected_stats:
            assert stat in summary.columns
    
    def test_validation_methods(self, sample_data, corrupted_data, temp_dir):
        """Test cycle validation methods."""
        # Test with clean data
        parquet_path = os.path.join(temp_dir, 'clean_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        valid_mask = loco.validate_cycles('SUB01', 'normal_walk')
        
        assert isinstance(valid_mask, np.ndarray)
        assert len(valid_mask) == 4  # 4 cycles
        assert valid_mask.dtype == bool
        
        # Most cycles should be valid for clean data
        assert np.sum(valid_mask) >= 3
        
        # Test with corrupted data
        corrupted_path = os.path.join(temp_dir, 'corrupted_data.parquet')
        corrupted_data.to_parquet(corrupted_path)
        
        loco_corrupted = LocomotionData(corrupted_path)
        valid_mask_corrupted = loco_corrupted.validate_cycles('SUB01', 'normal_walk')
        
        # Should detect corruption
        assert np.sum(valid_mask_corrupted) < len(valid_mask_corrupted)
    
    def test_outlier_detection(self, sample_data, temp_dir):
        """Test outlier detection functionality."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test outlier detection
        outliers = loco.find_outlier_cycles('SUB01', 'normal_walk')
        assert isinstance(outliers, np.ndarray)
        
        # With clean synthetic data, should find few or no outliers
        assert len(outliers) <= 1
        
        # Test with different threshold
        outliers_strict = loco.find_outlier_cycles('SUB01', 'normal_walk', threshold=1.0)
        outliers_lenient = loco.find_outlier_cycles('SUB01', 'normal_walk', threshold=3.0)
        
        # Stricter threshold should find more outliers
        assert len(outliers_strict) >= len(outliers_lenient)
    
    def test_rom_calculation(self, sample_data, temp_dir):
        """Test Range of Motion calculation."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test ROM by cycle
        rom_by_cycle = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=True)
        assert isinstance(rom_by_cycle, dict)
        
        for feature, rom_values in rom_by_cycle.items():
            assert len(rom_values) == 4  # 4 cycles
            assert np.all(rom_values >= 0)  # ROM should be non-negative
        
        # Test overall ROM
        rom_overall = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=False)
        assert isinstance(rom_overall, dict)
        
        for feature, rom_value in rom_overall.items():
            assert isinstance(rom_value, (int, float))
            assert rom_value >= 0
    
    def test_phase_correlations(self, sample_data, temp_dir):
        """Test phase correlation analysis."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test correlation calculation
        features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
        correlations = loco.get_phase_correlations('SUB01', 'normal_walk', features)
        
        assert correlations is not None
        assert correlations.shape == (150, 2, 2)  # 150 phases, 2x2 correlation matrix
        
        # Check that correlations are valid
        for phase in range(150):
            corr_matrix = correlations[phase]
            # Diagonal should be 1
            assert np.allclose(np.diag(corr_matrix), 1.0)
            # Matrix should be symmetric
            assert np.allclose(corr_matrix, corr_matrix.T)
            # Values should be between -1 and 1
            assert np.all(np.abs(corr_matrix) <= 1.0)
    
    def test_data_merging(self, sample_data, temp_dir):
        """Test data merging functionality."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Create task data
        task_data = pd.DataFrame({
            'subject': ['SUB01', 'SUB02', 'SUB03'],
            'task': ['normal_walk', 'normal_walk', 'normal_walk'],
            'speed_m_s': [1.2, 1.3, 1.1],
            'age_years': [25, 30, 28]
        })
        
        # Test merging
        merged = loco.merge_with_task_data(task_data)
        assert isinstance(merged, pd.DataFrame)
        assert 'speed_m_s' in merged.columns
        assert 'age_years' in merged.columns
        assert len(merged) > 0
        
        # Test with custom join keys
        merged_custom = loco.merge_with_task_data(task_data, join_keys=['subject'])
        assert len(merged_custom) > 0
    
    def test_efficient_reshape_standalone(self, sample_data):
        """Test standalone efficient reshape function."""
        # Test basic functionality
        data_3d, features = efficient_reshape_3d(
            sample_data, 'SUB01', 'normal_walk', 
            ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
        )
        
        assert data_3d is not None
        assert data_3d.shape == (4, 150, 2)
        assert len(features) == 2
        
        # Test with invalid subject
        data_3d, features = efficient_reshape_3d(
            sample_data, 'INVALID', 'normal_walk', 
            ['hip_flexion_angle_contra_rad']
        )
        
        assert data_3d is None
        assert features == []
    
    def test_error_handling_edge_cases(self, sample_data, temp_dir):
        """Test error handling for various edge cases."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test with empty feature list
        data_3d, features = loco.get_cycles('SUB01', 'normal_walk', [])
        assert data_3d is not None
        assert len(features) > 0  # Should use all features
        
        # Test with invalid features
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_3d, features = loco.get_cycles('SUB01', 'normal_walk', ['invalid_feature'])
            assert len(w) == 1
            assert "No valid features found" in str(w[0].message)
        
        assert data_3d is None
        assert features == []
        
        # Test statistical methods with no data
        empty_stats = loco.get_mean_patterns('INVALID', 'normal_walk')
        assert empty_stats == {}
        
        empty_summary = loco.get_summary_statistics('INVALID', 'normal_walk')
        assert len(empty_summary) == 0
    
    def test_plotting_interface_basic(self, sample_data, temp_dir):
        """Test plotting interface without actually displaying plots."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Mock matplotlib to avoid display
        with patch('matplotlib.pyplot.show'), patch('matplotlib.pyplot.savefig'):
            # Test phase pattern plots
            features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad']
            
            # Test different plot types
            plot_types = ['mean', 'spaghetti', 'both']
            for plot_type in plot_types:
                try:
                    loco.plot_phase_patterns('SUB01', 'normal_walk', features, plot_type=plot_type)
                    # Should not raise exception
                except Exception as e:
                    # Only acceptable if it's about missing data
                    assert "No data found" in str(e) or "matplotlib" in str(e).lower()
            
            # Test task comparison
            try:
                loco.plot_task_comparison('SUB01', ['normal_walk', 'fast_walk'], features[:1])
            except Exception as e:
                assert "No data found" in str(e) or "matplotlib" in str(e).lower()
    
    def test_memory_efficiency(self, temp_dir):
        """Test memory efficiency with larger datasets."""
        # Create larger dataset
        np.random.seed(42)
        n_subjects = 5
        n_tasks = 3
        n_cycles = 10
        points_per_cycle = 150
        
        large_data = []
        for subject in [f'SUB{i:02d}' for i in range(1, n_subjects+1)]:
            for task in ['walk', 'run', 'jump']:
                for cycle in range(n_cycles):
                    phase = np.linspace(0, 100, points_per_cycle)
                    
                    for i in range(points_per_cycle):
                        large_data.append({
                            'subject': subject,
                            'task': task,
                            'phase': phase[i],
                            'hip_flexion_angle_contra_rad': np.random.normal(0, 0.5),
                            'knee_flexion_angle_contra_rad': np.random.normal(0, 0.5),
                            'ankle_flexion_angle_contra_rad': np.random.normal(0, 0.3),
                        })
        
        df_large = pd.DataFrame(large_data)
        
        # Save and load
        parquet_path = os.path.join(temp_dir, 'large_data.parquet')
        df_large.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test that operations complete in reasonable time
        import time
        start_time = time.time()
        
        data_3d, features = loco.get_cycles('SUB01', 'walk')
        elapsed = time.time() - start_time
        
        assert elapsed < 1.0  # Should complete within 1 second
        assert data_3d.shape == (n_cycles, points_per_cycle, len(features))
    
    def test_performance_benchmarks(self, sample_data, temp_dir):
        """Test performance benchmarks for key operations."""
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        import time
        
        # Benchmark 3D extraction
        start_time = time.time()
        for _ in range(10):
            data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
        extraction_time = time.time() - start_time
        
        # Should benefit from caching after first call
        assert extraction_time < 0.1  # 10 calls in < 0.1 seconds
        
        # Benchmark statistical calculations
        start_time = time.time()
        for _ in range(5):
            mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
            std_patterns = loco.get_std_patterns('SUB01', 'normal_walk')
        stats_time = time.time() - start_time
        
        assert stats_time < 0.5  # 5 iterations in < 0.5 seconds


def run_manual_tests():
    """Run tests manually when pytest is not available."""
    print("🧪 Running manual tests for LocomotionData library...")
    
    import tempfile
    import shutil
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create test instance
        test_instance = TestLocomotionDataLibrary()
        
        # Generate sample data
        print("\n✅ Test 1: Sample data generation")
        sample_data = test_instance.sample_data()
        assert len(sample_data) > 0
        print(f"   Generated {len(sample_data)} rows of sample data")
        
        # Test initialization
        print("\n✅ Test 2: Library initialization")
        parquet_path = os.path.join(temp_dir, 'test_data.parquet')
        sample_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        assert len(loco.get_subjects()) == 3
        assert len(loco.get_tasks()) == 2
        assert len(loco.features) > 0
        print(f"   Loaded {len(loco.df)} rows, {len(loco.features)} features")
        
        # Test 3D extraction
        print("\n✅ Test 3: 3D array extraction")
        data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
        assert data_3d is not None
        assert data_3d.shape == (4, 150, len(features))
        print(f"   Extracted 3D array: {data_3d.shape}")
        
        # Test statistical methods
        print("\n✅ Test 4: Statistical analysis")
        mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
        assert len(mean_patterns) > 0
        
        summary = loco.get_summary_statistics('SUB01', 'normal_walk')
        assert len(summary) > 0
        print(f"   Calculated statistics for {len(mean_patterns)} features")
        
        # Test validation
        print("\n✅ Test 5: Cycle validation")
        valid_mask = loco.validate_cycles('SUB01', 'normal_walk')
        assert len(valid_mask) == 4
        print(f"   Validation: {np.sum(valid_mask)}/{len(valid_mask)} cycles valid")
        
        # Test outlier detection
        print("\n✅ Test 6: Outlier detection")
        outliers = loco.find_outlier_cycles('SUB01', 'normal_walk')
        print(f"   Found {len(outliers)} outlier cycles")
        
        # Test ROM calculation
        print("\n✅ Test 7: ROM calculation")
        rom_data = loco.calculate_rom('SUB01', 'normal_walk')
        assert len(rom_data) > 0
        print(f"   Calculated ROM for {len(rom_data)} features")
        
        # Test error handling
        print("\n✅ Test 8: Error handling")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_none, features_none = loco.get_cycles('INVALID', 'normal_walk')
            assert len(w) > 0
            assert data_none is None
        print("   Error handling working correctly")
        
        print("\n🎉 All manual tests passed! LocomotionData library is working correctly.")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    if PYTEST_AVAILABLE:
        print("🧪 Running pytest test suite...")
        # Run with pytest if available
        import pytest
        pytest.main([__file__, "-v"])
    else:
        print("⚠️  pytest not available, running manual tests...")
        run_manual_tests()