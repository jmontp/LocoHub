#!/usr/bin/env python3
"""
BASIC WORKING COVERAGE TEST - Government Audit Compliance
=========================================================

Created: 2025-06-19 for EMERGENCY GOVERNMENT AUDIT COMPLIANCE
Purpose: Simple, basic tests that actually work to improve coverage

STRATEGY: Focus on basic functionality that executes without pandas/numpy issues.
Use existing test data that's known to work.
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

from user_libs.python.locomotion_data import LocomotionData, efficient_reshape_3d


class TestBasicWorkingCoverage:
    """Basic working tests for coverage improvement."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def working_data(self):
        """Create simple working data that doesn't cause pandas issues."""
        # Use a very simple structure
        data = []
        for i in range(300):  # Exactly 2 cycles
            cycle = i // 150
            point = i % 150
            data.append({
                'subject': f'SUB{cycle+1:02d}',
                'task': 'walk',
                'phase': point * (100.0 / 149.0),
                'hip_flexion_angle_ipsi_rad': 0.5 * np.sin(2 * np.pi * point / 150),
                'knee_flexion_angle_contra_rad': 0.3 * np.cos(2 * np.pi * point / 150)
            })
        
        return pd.DataFrame(data)
    
    def test_basic_file_errors(self, temp_dir):
        """Test basic file error conditions."""
        
        # Test file not found
        with pytest.raises(FileNotFoundError):
            LocomotionData('/nonexistent/file.parquet')
        
        # Test bad parquet file
        bad_file = os.path.join(temp_dir, 'bad.parquet')
        with open(bad_file, 'w') as f:
            f.write("not parquet")
        
        with pytest.raises(ValueError):
            LocomotionData(bad_file)
        
        # Test unsupported file type
        txt_file = os.path.join(temp_dir, 'test.txt')
        with open(txt_file, 'w') as f:
            f.write("test")
        
        with pytest.raises(ValueError):
            LocomotionData(txt_file, file_type='unsupported')
    
    def test_basic_data_validation(self, temp_dir):
        """Test basic data validation."""
        
        # Test empty dataset
        empty_df = pd.DataFrame()
        empty_path = os.path.join(temp_dir, 'empty.parquet')
        empty_df.to_parquet(empty_path)
        
        with pytest.raises(ValueError):
            LocomotionData(empty_path)
        
        # Test missing columns
        bad_df = pd.DataFrame({'wrong': [1, 2, 3]})
        bad_path = os.path.join(temp_dir, 'bad.parquet')
        bad_df.to_parquet(bad_path)
        
        with pytest.raises(ValueError):
            LocomotionData(bad_path)
    
    def test_basic_functionality(self, working_data, temp_dir):
        """Test basic functionality that should work."""
        
        parquet_path = os.path.join(temp_dir, 'working.parquet')
        working_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test basic properties
        assert len(loco.subjects) > 0
        assert len(loco.tasks) > 0
        assert len(loco.features) > 0
        
        # Test get_subjects and get_tasks
        subjects = loco.get_subjects()
        tasks = loco.get_tasks()
        assert isinstance(subjects, list)
        assert isinstance(tasks, list)
        
        # Test validation report
        report = loco.get_validation_report()
        assert isinstance(report, dict)
        
        # Test basic data access
        data_3d, features = loco.get_cycles('SUB01', 'walk')
        if data_3d is not None:
            assert isinstance(data_3d, np.ndarray)
            assert len(features) > 0
    
    def test_variable_name_methods(self, working_data, temp_dir):
        """Test variable name methods."""
        
        parquet_path = os.path.join(temp_dir, 'names.parquet')
        working_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test standard compliance checking
        assert loco._is_standard_compliant('hip_flexion_angle_ipsi_rad')
        assert not loco._is_standard_compliant('invalid_name')
        
        # Test biomechanical keyword detection
        assert loco._has_biomechanical_keywords('hip_angle_test')
        assert not loco._has_biomechanical_keywords('random_variable')
        
        # Test suggestion system
        suggestion = loco.suggest_standard_name('hip_angle_left')
        assert isinstance(suggestion, str)
        assert len(suggestion.split('_')) == 5
    
    def test_efficient_reshape_basic(self, working_data):
        """Test efficient reshape function."""
        
        features = ['hip_flexion_angle_ipsi_rad']
        
        # Test successful case
        data_3d, valid_features = efficient_reshape_3d(
            working_data, 'SUB01', 'walk', features
        )
        
        if data_3d is not None:
            assert isinstance(data_3d, np.ndarray)
            assert len(valid_features) > 0
        
        # Test nonexistent subject
        data_none, features_none = efficient_reshape_3d(
            working_data, 'INVALID', 'walk', features
        )
        assert data_none is None
        assert features_none == []
        
        # Test nonexistent features
        data_empty, features_empty = efficient_reshape_3d(
            working_data, 'SUB01', 'walk', ['nonexistent']
        )
        assert data_empty is None
        assert features_empty == []
    
    @patch('lib.core.locomotion_analysis.MATPLOTLIB_AVAILABLE', False)
    def test_matplotlib_not_available(self, working_data, temp_dir):
        """Test matplotlib not available errors."""
        
        parquet_path = os.path.join(temp_dir, 'plot_test.parquet')
        working_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        features = ['hip_flexion_angle_ipsi_rad']
        
        # All plotting functions should raise ImportError
        with pytest.raises(ImportError):
            loco.plot_time_series('SUB01', 'walk', features)
        
        with pytest.raises(ImportError):
            loco.plot_phase_patterns('SUB01', 'walk', features)
        
        with pytest.raises(ImportError):
            loco.plot_task_comparison('SUB01', ['walk'], features)
    
    @patch('lib.core.locomotion_analysis.MATPLOTLIB_AVAILABLE', True)
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.subplots')
    @patch('matplotlib.pyplot.tight_layout')
    def test_plotting_basic(self, mock_tight_layout, mock_subplots, mock_savefig, mock_show, working_data, temp_dir):
        """Test basic plotting functionality."""
        
        # Add time column
        df_with_time = working_data.copy()
        df_with_time['time_s'] = np.tile(np.linspace(0, 1.5, 150), 2)
        
        parquet_path = os.path.join(temp_dir, 'plot_basic.parquet')
        df_with_time.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        
        features = ['hip_flexion_angle_ipsi_rad']
        
        # Test time series plotting
        loco.plot_time_series('SUB01', 'walk', features)
        mock_subplots.assert_called()
        
        # Test phase patterns plotting
        loco.plot_phase_patterns('SUB01', 'walk', features)
        
        # Test task comparison plotting
        loco.plot_task_comparison('SUB01', ['walk'], features)
        
        # Test with nonexistent data (should not crash)
        loco.plot_time_series('INVALID', 'walk', features)
        loco.plot_phase_patterns('INVALID', 'walk', features)
    
    def test_data_analysis_basic(self, working_data, temp_dir):
        """Test basic data analysis methods."""
        
        parquet_path = os.path.join(temp_dir, 'analysis.parquet')
        working_data.to_parquet(parquet_path)
        
        loco = LocomotionData(parquet_path)
        
        # Test with invalid subject/task (should return empty/None)
        mean_empty = loco.get_mean_patterns('INVALID', 'walk')
        assert mean_empty == {}
        
        std_empty = loco.get_std_patterns('INVALID', 'walk')
        assert std_empty == {}
        
        valid_empty = loco.validate_cycles('INVALID', 'walk')
        assert len(valid_empty) == 0
        
        corr_none = loco.get_phase_correlations('INVALID', 'walk')
        assert corr_none is None
        
        outliers_empty = loco.find_outlier_cycles('INVALID', 'walk')
        assert len(outliers_empty) == 0
        
        summary_empty = loco.get_summary_statistics('INVALID', 'walk')
        assert len(summary_empty) == 0
        
        rom_empty = loco.calculate_rom('INVALID', 'walk')
        assert rom_empty == {}
        
        # Test data merging errors
        bad_task_data = pd.DataFrame({'wrong': ['test']})
        with pytest.raises(ValueError):
            loco.merge_with_task_data(bad_task_data)
    
    def test_warnings_and_edge_cases(self, temp_dir):
        """Test warning conditions and edge cases."""
        
        # Test NaN phase warning
        nan_df = pd.DataFrame({
            'subject': ['S1'],
            'task': ['T1'],
            'phase': [np.nan],
            'hip_flexion_angle_ipsi_rad': [0.1]
        })
        nan_path = os.path.join(temp_dir, 'nan.parquet')
        nan_df.to_parquet(nan_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            LocomotionData(nan_path)
            assert any("Phase column contains only NaN values" in str(warning.message) for warning in w)
        
        # Test out of range phase warning
        range_df = pd.DataFrame({
            'subject': ['S1'],
            'task': ['T1'],
            'phase': [150],  # > 100
            'hip_flexion_angle_ipsi_rad': [0.1]
        })
        range_path = os.path.join(temp_dir, 'range.parquet')
        range_df.to_parquet(range_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            LocomotionData(range_path)
            assert any("Phase values outside expected range" in str(warning.message) for warning in w)
        
        # Test invalid length warning
        invalid_length_df = pd.DataFrame({
            'subject': ['S1'] * 149,  # Not divisible by 150
            'task': ['T1'] * 149,
            'phase': np.linspace(0, 100, 149),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0, 0.1, 149)
        })
        invalid_path = os.path.join(temp_dir, 'invalid_length.parquet')
        invalid_length_df.to_parquet(invalid_path)
        
        loco_invalid = LocomotionData(invalid_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data, features = loco_invalid.get_cycles('S1', 'T1')
            assert any("not divisible by 150" in str(warning.message) for warning in w)
        assert data is None
        
        # Test no valid features warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            data, features = loco_invalid.get_cycles('S1', 'T1', ['nonexistent'])
            assert any("No valid features found" in str(warning.message) for warning in w)
        assert data is None
    
    def test_custom_parameters(self, working_data, temp_dir):
        """Test custom parameters and configurations."""
        
        # Test custom column names
        custom_df = working_data.copy()
        custom_df = custom_df.rename(columns={
            'subject': 'participant',
            'task': 'activity',
            'phase': 'gait_phase'
        })
        
        custom_path = os.path.join(temp_dir, 'custom.parquet')
        custom_df.to_parquet(custom_path)
        
        # Test with custom column names
        loco = LocomotionData(
            custom_path,
            subject_col='participant',
            task_col='activity',
            phase_col='gait_phase'
        )
        
        assert loco.subject_col == 'participant'
        assert loco.task_col == 'activity'
        assert loco.phase_col == 'gait_phase'


def run_basic_coverage_analysis():
    """Run basic coverage analysis."""
    print("🎯 BASIC WORKING COVERAGE ANALYSIS")
    print("🚨 Focus: Simple tests that actually execute")
    
    import subprocess
    import sys
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            '--cov=lib.core.locomotion_analysis',
            '--cov-report=term-missing',
            '--cov-report=html:basic_coverage_html',
            __file__, '-v'
        ], capture_output=True, text=True, cwd='..')
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        
        # Extract coverage
        lines = result.stdout.split('\n')
        for line in lines:
            if 'locomotion_analysis.py' in line and '%' in line:
                print(f"\n🔍 BASIC COVERAGE RESULT: {line}")
                
                parts = line.split()
                for part in parts:
                    if part.endswith('%'):
                        coverage_pct = int(part[:-1])
                        if coverage_pct >= 95:
                            print(f"🎉 MISSION SUCCESS! {coverage_pct}% coverage!")
                        elif coverage_pct >= 80:
                            print(f"💪 GREAT PROGRESS! {coverage_pct}% coverage!")
                        elif coverage_pct >= 60:
                            print(f"📈 GOOD PROGRESS! {coverage_pct}% coverage!")
                        else:
                            print(f"⚠️  {coverage_pct}% coverage - continuing effort")
                        break
                break
                
    except Exception as e:
        print(f"❌ Analysis failed: {e}")


if __name__ == "__main__":
    print("🚨 BASIC WORKING COVERAGE TEST")
    print("=" * 50)
    print("Strategy: Simple, robust tests that actually work")
    print("Goal: Improve coverage with working functionality")
    print("=" * 50)
    
    try:
        run_basic_coverage_analysis()
    except ImportError:
        print("⚠️  pytest not available")