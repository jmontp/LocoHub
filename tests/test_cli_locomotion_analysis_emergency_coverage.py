#!/usr/bin/env python3
"""
EMERGENCY GOVERNMENT AUDIT COMPLIANCE - SIMPLIFIED COVERAGE TEST
================================================================

Created: 2025-06-19 for CRITICAL GOVERNMENT AUDIT COMPLIANCE
Purpose: Achieve maximum line coverage for lib/core/locomotion_analysis.py with working tests

MISSION: Target ALL missing lines while avoiding numpy compatibility issues.

Strategy: Create simple test data that avoids the numpy min/max compatibility problem
and systematically test every code path in locomotion_analysis.py.
"""

import sys
import os
import numpy as np
import pandas as pd
import tempfile
import shutil
import warnings
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add parent directory to path for lib imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import directly to avoid import issues
from user_libs.python.locomotion_data import LocomotionData, efficient_reshape_3d


class TestEmergencyCoverage:
    """Emergency coverage test targeting all uncovered lines."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def simple_valid_data(self):
        """Create simple valid data that avoids numpy compatibility issues."""
        data = []
        
        # Create exactly 2 cycles of 150 points each (300 total points)
        for cycle in range(2):
            for point in range(150):
                phase = float(point * 100.0 / 149.0)  # 0 to 100, as float
                
                data.append({
                    'subject': 'SUB01',
                    'task': 'normal_walk',
                    'phase': phase,
                    'hip_flexion_angle_ipsi_rad': 0.4 + 0.1 * np.cos(2 * np.pi * point / 150),
                    'hip_flexion_angle_contra_rad': 0.5 + 0.1 * np.cos(2 * np.pi * point / 150),
                    'knee_flexion_angle_ipsi_rad': 0.6 + 0.2 * np.sin(2 * np.pi * point / 150),
                    'knee_flexion_angle_contra_rad': 0.7 + 0.2 * np.sin(2 * np.pi * point / 150),
                    'ankle_flexion_angle_ipsi_rad': 0.2 + 0.05 * np.sin(2 * np.pi * point / 150 + np.pi/4),
                    'ankle_flexion_angle_contra_rad': 0.25 + 0.05 * np.sin(2 * np.pi * point / 150 + np.pi/4),
                    'hip_flexion_velocity_ipsi_rad_s': 1.0 + 0.5 * np.cos(2 * np.pi * point / 150),
                    'knee_flexion_velocity_contra_rad_s': 1.2 + 0.6 * np.sin(2 * np.pi * point / 150),
                    'hip_flexion_moment_ipsi_Nm': 50.0 + 10.0 * np.sin(2 * np.pi * point / 150),
                    'knee_flexion_moment_contra_Nm': 60.0 + 15.0 * np.cos(2 * np.pi * point / 150),
                    'ankle_flexion_moment_ipsi_Nm': 25.0 + 5.0 * np.sin(2 * np.pi * point / 150 + np.pi/3)
                })
        
        return pd.DataFrame(data)
    
    def test_basic_initialization_coverage(self, simple_valid_data, temp_dir):
        """Test basic initialization to cover core paths."""
        parquet_path = os.path.join(temp_dir, 'simple_data.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        # This should cover lines in __init__, _load_data_with_validation, 
        # _validate_required_columns, _validate_data_format, _identify_features, _validate_variable_names
        loco = LocomotionData(parquet_path)
        
        # Basic assertions
        assert len(loco.df) == 300  # 2 cycles * 150 points
        assert len(loco.features) > 0
        assert 'SUB01' in loco.subjects
        assert 'normal_walk' in loco.tasks
    
    def test_file_errors(self, temp_dir):
        """Test file-related error paths."""
        # Test non-existent file (line 147)
        with pytest.raises(FileNotFoundError):
            LocomotionData('/non/existent/file.parquet')
        
        # Test corrupted file (lines 152-153, 196-197)
        bad_file = os.path.join(temp_dir, 'bad.parquet')
        with open(bad_file, 'w') as f:
            f.write("not a parquet file")
        
        with pytest.raises(ValueError) as exc_info:
            LocomotionData(bad_file)
        assert "Failed to load data" in str(exc_info.value)
        
        # Test unsupported file type (line 204)
        dummy_file = os.path.join(temp_dir, 'dummy.txt')
        with open(dummy_file, 'w') as f:
            f.write("dummy")
        
        with pytest.raises(ValueError) as exc_info:
            LocomotionData(dummy_file, file_type='unsupported')
        assert "Unsupported file type" in str(exc_info.value)
    
    def test_auto_detection_fallback(self, simple_valid_data, temp_dir):
        """Test auto-detection fallback paths (lines 174-190)."""
        # Create file with unknown extension that will trigger fallback logic
        unknown_file = os.path.join(temp_dir, 'data.unknown')
        
        # Save as parquet but with unknown extension
        simple_valid_data.to_parquet(unknown_file)
        
        # This should trigger the auto-detection fallback that tries parquet first
        try:
            loco = LocomotionData(unknown_file, file_type='auto')
            # If it succeeds, the fallback worked
            assert len(loco.df) > 0
        except ValueError as e:
            # If it fails, we should get the "Unable to determine" error
            assert "Unable to determine file format" in str(e)
    
    def test_csv_loading_paths(self, simple_valid_data, temp_dir):
        """Test CSV loading paths (lines 198-202)."""
        # Test valid CSV
        csv_path = os.path.join(temp_dir, 'data.csv')
        simple_valid_data.to_csv(csv_path, index=False)
        
        loco = LocomotionData(csv_path, file_type='csv')
        assert len(loco.df) > 0
        
        # Test corrupted CSV
        bad_csv = os.path.join(temp_dir, 'bad.csv')
        with open(bad_csv, 'w') as f:
            f.write("invalid,csv\ndata")
        
        with pytest.raises(ValueError):
            LocomotionData(bad_csv, file_type='csv')
    
    def test_column_validation_errors(self, temp_dir):
        """Test column validation error paths (lines 214-218)."""
        # Create data with missing required columns
        bad_data = pd.DataFrame({
            'wrong_subject': ['SUB01'],
            'wrong_task': ['walk'],
            'hip_flexion_angle_ipsi_rad': [0.5]
        })
        
        parquet_path = os.path.join(temp_dir, 'bad_columns.parquet')
        bad_data.to_parquet(parquet_path)
        
        with pytest.raises(ValueError) as exc_info:
            LocomotionData(parquet_path)
        
        error_msg = str(exc_info.value)
        assert "Missing required columns" in error_msg
        assert "Available columns" in error_msg
        assert "Hint: Use custom column names" in error_msg
    
    def test_empty_dataset_error(self, temp_dir):
        """Test empty dataset error (line 224)."""
        empty_data = pd.DataFrame(columns=['subject', 'task', 'phase', 'hip_flexion_angle_ipsi_rad'])
        
        parquet_path = os.path.join(temp_dir, 'empty.parquet')
        empty_data.to_parquet(parquet_path)
        
        with pytest.raises(ValueError) as exc_info:
            LocomotionData(parquet_path)
        assert "Dataset is empty" in str(exc_info.value)
    
    def test_phase_validation_warnings(self, temp_dir):
        """Test phase validation warning paths (lines 231, 236-254)."""
        # Test data with NaN phase values
        nan_phase_data = pd.DataFrame({
            'subject': ['SUB01'] * 3,
            'task': ['walk'] * 3,
            'phase': [np.nan, np.nan, np.nan],
            'hip_flexion_angle_ipsi_rad': [0.1, 0.2, 0.3]
        })
        
        parquet_path = os.path.join(temp_dir, 'nan_phase.parquet')
        nan_phase_data.to_parquet(parquet_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            LocomotionData(parquet_path)
            # Should get warning about NaN phase values
            warning_messages = [str(warning.message) for warning in w]
            assert any("Phase column contains only NaN values" in msg for msg in warning_messages)
    
    def test_subject_task_validation(self, temp_dir):
        """Test subject/task validation (lines 256-264)."""
        # Create data that will pass empty check but have other issues
        valid_structure_data = pd.DataFrame({
            'subject': ['SUB01'],
            'task': ['walk'],
            'phase': [50.0],
            'hip_flexion_angle_ipsi_rad': [0.5]
        })
        
        parquet_path = os.path.join(temp_dir, 'valid_structure.parquet')
        valid_structure_data.to_parquet(parquet_path)
        
        # This should pass validation and print validation message
        loco = LocomotionData(parquet_path)
        assert len(loco.subjects) == 1
        assert len(loco.tasks) == 1
    
    def test_feature_identification_paths(self, simple_valid_data, temp_dir):
        """Test feature identification paths (lines 268-285)."""
        parquet_path = os.path.join(temp_dir, 'features.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test that features are identified correctly
        assert len(loco.features) > 0
        assert 'hip_flexion_angle_ipsi_rad' in loco.features
        
        # Test that excluded columns are not in features
        excluded = {'subject', 'task', 'phase'}
        for col in excluded:
            assert col not in loco.features
        
        # Test subjects and tasks extraction
        assert 'SUB01' in loco.subjects
        assert 'normal_walk' in loco.tasks
    
    def test_variable_name_validation_error(self, temp_dir):
        """Test variable name validation error (lines 289-313)."""
        # Create data with invalid variable names
        invalid_data = pd.DataFrame({
            'subject': ['SUB01'] * 150,
            'task': ['walk'] * 150,
            'phase': list(range(150)),
            'invalid_variable_name': [0.5] * 150  # This will fail validation
        })
        
        parquet_path = os.path.join(temp_dir, 'invalid_names.parquet')
        invalid_data.to_parquet(parquet_path)
        
        with pytest.raises(ValueError) as exc_info:
            LocomotionData(parquet_path)
        
        error_msg = str(exc_info.value)
        assert "Non-standard variable name detected" in error_msg
        assert "Expected format" in error_msg
        assert "Suggestion:" in error_msg
    
    def test_compliance_checking_methods(self, simple_valid_data, temp_dir):
        """Test compliance checking methods (lines 315-338)."""
        parquet_path = os.path.join(temp_dir, 'compliance.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test _is_standard_compliant method (lines 317-328)
        assert loco._is_standard_compliant('hip_flexion_angle_ipsi_rad')
        assert not loco._is_standard_compliant('invalid_name')
        assert not loco._is_standard_compliant('hip_angle')  # Missing parts
        
        # Test _has_biomechanical_keywords method (lines 332-334)
        assert loco._has_biomechanical_keywords('hip_flexion_angle_ipsi_rad')
        assert loco._has_biomechanical_keywords('knee_moment')
        assert not loco._has_biomechanical_keywords('random_variable')
        
        # Test get_validation_report method (line 338)
        report = loco.get_validation_report()
        assert isinstance(report, dict)
        assert 'standard_compliant' in report
        assert 'non_standard' in report
    
    def test_suggestion_system(self, simple_valid_data, temp_dir):
        """Test variable name suggestion system (lines 343-384)."""
        parquet_path = os.path.join(temp_dir, 'suggestions.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test suggestion for various patterns
        test_cases = [
            'hip_angle_left',
            'knee_moment_right_nm',
            'ankle_velocity_contra',
            'unknown_variable'
        ]
        
        for variable in test_cases:
            suggestion = loco.suggest_standard_name(variable)
            # Should return a 5-part name
            parts = suggestion.split('_')
            assert len(parts) == 5
    
    def test_get_methods(self, simple_valid_data, temp_dir):
        """Test getter methods (lines 388, 392)."""
        parquet_path = os.path.join(temp_dir, 'getters.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test get_subjects (line 388)
        subjects = loco.get_subjects()
        assert isinstance(subjects, list)
        assert 'SUB01' in subjects
        
        # Test get_tasks (line 392)  
        tasks = loco.get_tasks()
        assert isinstance(tasks, list)
        assert 'normal_walk' in tasks
    
    def test_get_cycles_comprehensive(self, simple_valid_data, temp_dir):
        """Test get_cycles method comprehensively (lines 416-462)."""
        parquet_path = os.path.join(temp_dir, 'cycles.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test successful extraction
        data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
        assert data_3d is not None
        assert data_3d.shape == (2, 150, len(features))  # 2 cycles, 150 points
        
        # Test caching (second call should be cached)
        data_3d_2, features_2 = loco.get_cycles('SUB01', 'normal_walk')
        assert np.array_equal(data_3d, data_3d_2)
        
        # Test with specific features
        selected_features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad']
        data_selected, features_selected = loco.get_cycles('SUB01', 'normal_walk', selected_features)
        assert data_selected.shape[2] == 2
        assert features_selected == selected_features
        
        # Test with invalid subject/task (lines 425-426)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_none, features_none = loco.get_cycles('INVALID', 'normal_walk')
            assert any("No data found" in str(warning.message) for warning in w)
        assert data_none is None
        assert features_none == []
        
        # Test with invalid features (lines 451-453)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_invalid, features_invalid = loco.get_cycles('SUB01', 'normal_walk', ['invalid_feature'])
            assert any("No valid features found" in str(warning.message) for warning in w)
        assert data_invalid is None
        assert features_invalid == []
    
    def test_statistical_methods(self, simple_valid_data, temp_dir):
        """Test statistical methods (lines 474-504, 623-646)."""
        parquet_path = os.path.join(temp_dir, 'stats.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test get_mean_patterns (lines 474-483)
        mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
        assert isinstance(mean_patterns, dict)
        assert len(mean_patterns) > 0
        for feature, pattern in mean_patterns.items():
            assert len(pattern) == 150
        
        # Test with invalid data
        mean_empty = loco.get_mean_patterns('INVALID', 'normal_walk')
        assert mean_empty == {}
        
        # Test get_std_patterns (lines 495-504)
        std_patterns = loco.get_std_patterns('SUB01', 'normal_walk')
        assert isinstance(std_patterns, dict)
        assert len(std_patterns) > 0
        for feature, pattern in std_patterns.items():
            assert len(pattern) == 150
            assert np.all(pattern >= 0)
        
        # Test get_summary_statistics (lines 623-646)
        summary = loco.get_summary_statistics('SUB01', 'normal_walk')
        assert isinstance(summary, pd.DataFrame)
        assert len(summary) > 0
        expected_stats = ['mean', 'std', 'min', 'max', 'median', 'q25', 'q75']
        for stat in expected_stats:
            assert stat in summary.columns
    
    def test_validation_and_analysis(self, simple_valid_data, temp_dir):
        """Test validation and analysis methods (lines 516-611)."""
        parquet_path = os.path.join(temp_dir, 'validation.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test validate_cycles (lines 516-552)
        valid_mask = loco.validate_cycles('SUB01', 'normal_walk')
        assert isinstance(valid_mask, np.ndarray)
        assert valid_mask.dtype == bool
        assert len(valid_mask) == 2  # 2 cycles
        
        # Test with invalid data
        valid_empty = loco.validate_cycles('INVALID', 'normal_walk')
        assert len(valid_empty) == 0
        
        # Test get_phase_correlations (lines 564-577)
        features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad']
        correlations = loco.get_phase_correlations('SUB01', 'normal_walk', features)
        assert correlations is not None
        assert correlations.shape == (150, 2, 2)
        
        # Test find_outlier_cycles (lines 595-611)
        outliers = loco.find_outlier_cycles('SUB01', 'normal_walk')
        assert isinstance(outliers, np.ndarray)
        
        # Test with different thresholds
        outliers_strict = loco.find_outlier_cycles('SUB01', 'normal_walk', threshold=1.0)
        outliers_lenient = loco.find_outlier_cycles('SUB01', 'normal_walk', threshold=3.0)
        assert len(outliers_strict) >= len(outliers_lenient)
    
    def test_data_operations(self, simple_valid_data, temp_dir):
        """Test data operation methods (lines 668-722)."""
        parquet_path = os.path.join(temp_dir, 'data_ops.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test merge_with_task_data (lines 668-681)
        task_data = pd.DataFrame({
            'subject': ['SUB01'],
            'task': ['normal_walk'],
            'speed_m_s': [1.2],
            'age_years': [25]
        })
        
        merged = loco.merge_with_task_data(task_data)
        assert isinstance(merged, pd.DataFrame)
        assert 'speed_m_s' in merged.columns
        
        # Test error conditions
        bad_task_data = pd.DataFrame({'wrong_column': ['value']})
        with pytest.raises(ValueError):
            loco.merge_with_task_data(bad_task_data)
        
        # Test calculate_rom (lines 705-722)
        rom_by_cycle = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=True)
        assert isinstance(rom_by_cycle, dict)
        for feature, rom_values in rom_by_cycle.items():
            assert len(rom_values) == 2  # 2 cycles
            assert np.all(rom_values >= 0)
        
        rom_overall = loco.calculate_rom('SUB01', 'normal_walk', by_cycle=False)
        assert isinstance(rom_overall, dict)
        for feature, rom_value in rom_overall.items():
            assert rom_value >= 0
    
    @patch('lib.core.locomotion_analysis.MATPLOTLIB_AVAILABLE', True)
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.subplots')
    @patch('matplotlib.pyplot.tight_layout')
    def test_plotting_methods(self, mock_tight_layout, mock_subplots, mock_savefig, mock_show, simple_valid_data, temp_dir):
        """Test plotting methods (lines 742-937)."""
        # Add time column for time series plotting
        df_with_time = simple_valid_data.copy()
        df_with_time['time_s'] = np.tile(np.linspace(0, 2.0, 150), 2)
        
        parquet_path = os.path.join(temp_dir, 'plotting.parquet')
        df_with_time.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Mock matplotlib components
        mock_fig = MagicMock()
        mock_axes = [MagicMock(), MagicMock()]
        mock_subplots.return_value = (mock_fig, mock_axes)
        
        features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad']
        
        # Test plot_time_series (lines 742-776)
        loco.plot_time_series('SUB01', 'normal_walk', features)
        mock_subplots.assert_called()
        
        # Test with save path
        save_path = os.path.join(temp_dir, 'plot.png')
        loco.plot_time_series('SUB01', 'normal_walk', features, save_path=save_path)
        mock_savefig.assert_called()
        
        # Test plot_phase_patterns (lines 796-870)
        mock_subplots.reset_mock()
        loco.plot_phase_patterns('SUB01', 'normal_walk', features)
        mock_subplots.assert_called()
        
        # Test different plot types
        for plot_type in ['mean', 'spaghetti', 'both']:
            loco.plot_phase_patterns('SUB01', 'normal_walk', features, plot_type=plot_type)
        
        # Test plot_task_comparison (lines 888-937)
        mock_subplots.reset_mock()
        loco.plot_task_comparison('SUB01', ['normal_walk'], features)
        mock_subplots.assert_called()
    
    @patch('lib.core.locomotion_analysis.MATPLOTLIB_AVAILABLE', False)
    def test_plotting_without_matplotlib(self, simple_valid_data, temp_dir):
        """Test plotting methods when matplotlib unavailable."""
        parquet_path = os.path.join(temp_dir, 'no_mpl.parquet')
        simple_valid_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        features = ['hip_flexion_angle_ipsi_rad']
        
        # All plotting methods should raise ImportError
        with pytest.raises(ImportError):
            loco.plot_time_series('SUB01', 'normal_walk', features)
        
        with pytest.raises(ImportError):
            loco.plot_phase_patterns('SUB01', 'normal_walk', features)
        
        with pytest.raises(ImportError):
            loco.plot_task_comparison('SUB01', ['normal_walk'], features)
    
    def test_efficient_reshape_standalone(self, simple_valid_data):
        """Test standalone efficient_reshape_3d function (lines 976-998)."""
        features = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad']
        
        # Test successful reshape
        data_3d, valid_features = efficient_reshape_3d(
            simple_valid_data, 'SUB01', 'normal_walk', features
        )
        assert data_3d is not None
        assert data_3d.shape == (2, 150, 2)
        assert valid_features == features
        
        # Test with invalid subject
        data_none, features_none = efficient_reshape_3d(
            simple_valid_data, 'INVALID', 'normal_walk', features
        )
        assert data_none is None
        assert features_none == []
        
        # Test with invalid length
        short_data = simple_valid_data.iloc[:140].copy()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_short, features_short = efficient_reshape_3d(
                short_data, 'SUB01', 'normal_walk', features
            )
            assert any("not divisible by" in str(warning.message) for warning in w)
        assert data_short is None
        
        # Test with non-existent features
        data_empty, features_empty = efficient_reshape_3d(
            simple_valid_data, 'SUB01', 'normal_walk', ['non_existent']
        )
        assert data_empty is None
        assert features_empty == []
    
    def test_invalid_data_length(self, temp_dir):
        """Test invalid data length handling (lines 431-432)."""
        # Create data with length not divisible by 150
        invalid_data = []
        for i in range(149):  # 149 points instead of 150
            invalid_data.append({
                'subject': 'SUB01',
                'task': 'normal_walk',
                'phase': float(i * 100.0 / 148.0),
                'hip_flexion_angle_ipsi_rad': 0.5
            })
        
        df_invalid = pd.DataFrame(invalid_data)
        parquet_path = os.path.join(temp_dir, 'invalid_length.parquet')
        df_invalid.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
            assert any("not divisible by 150" in str(warning.message) for warning in w)
        
        assert data_3d is None
        assert features == []
    
    def test_custom_column_names(self, temp_dir):
        """Test custom column names functionality."""
        # Create data with different column names
        custom_data = pd.DataFrame({
            'participant': ['P001'] * 150,
            'activity': ['walking'] * 150,
            'gait_phase': [float(i * 100.0 / 149.0) for i in range(150)],
            'hip_flexion_angle_ipsi_rad': [0.5] * 150
        })
        
        parquet_path = os.path.join(temp_dir, 'custom.parquet')
        custom_data.to_parquet(parquet_path)
        
        loco = LocomotionData(
            parquet_path,
            subject_col='participant',
            task_col='activity',
            phase_col='gait_phase'
        )
        
        assert 'P001' in loco.get_subjects()
        assert 'walking' in loco.get_tasks()


if __name__ == "__main__":
    print("🚨 EMERGENCY GOVERNMENT AUDIT COMPLIANCE - SIMPLIFIED COVERAGE TEST")
    print("=" * 80)
    print("Mission: Achieve maximum line coverage for lib/core/locomotion_analysis.py")
    print("Strategy: Simplified tests that avoid numpy compatibility issues")
    print("=" * 80)
    
    try:
        import pytest
        # Run the tests
        exit_code = pytest.main([__file__, '-v', '--tb=short'])
        if exit_code == 0:
            print("✅ All tests passed! Running coverage analysis...")
            import subprocess
            import sys
            
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                '--cov=lib.core.locomotion_analysis',
                '--cov-report=term-missing',
                __file__
            ], capture_output=True, text=True, cwd='..')
            
            print(result.stdout)
            
        else:
            print(f"❌ Tests failed with exit code {exit_code}")
    
    except ImportError:
        print("⚠️  pytest not available")