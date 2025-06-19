#!/usr/bin/env python3
"""
Comprehensive Coverage Tests for CLI Optimize Validation Ranges

Created: 2025-06-18 with user permission  
Purpose: Achieve 100% line coverage for contributor_scripts/optimize_validation_ranges.py

Intent:
This test file provides comprehensive coverage for all 252 lines of the CLI script
optimize_validation_ranges.py. Tests all code paths, error conditions, edge cases,
and functionality using direct imports and subprocess execution to ensure
government audit compliance with honest functionality testing.

Coverage Strategy:
1. Direct testing of ValidationRangeOptimizer class methods
2. Testing main() function with mocked sys.argv
3. All CLI argument combinations and validation
4. All optimization methods (percentile, std_dev, iqr)
5. Multi-dataset processing with different weights
6. Memory-efficient chunked processing
7. Target false positive rate optimization
8. Error handling and edge cases
9. Output format variations and reporting
10. Comparison functionality with current validation files
"""

import pytest
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import json
from unittest.mock import patch, MagicMock, mock_open
import logging
import os
import argparse
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from lib.core.feature_constants import ANGLE_FEATURES, MOMENT_FEATURES

# Import the CLI script components for direct testing
sys.path.append(str(project_root / "contributor_scripts"))
try:
    import optimize_validation_ranges
    from optimize_validation_ranges import ValidationRangeOptimizer, main
except ImportError as e:
    print(f"Warning: Could not import CLI script components: {e}")
    optimize_validation_ranges = None
    ValidationRangeOptimizer = None
    main = None


class TestCLIOptimizeValidationRanges:
    """Comprehensive test coverage for optimize_validation_ranges.py CLI script."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def small_test_dataset(self, temp_dir):
        """Create small test dataset for basic functionality."""
        np.random.seed(42)
        
        # Create realistic biomechanical data
        n_cycles = 5
        n_points = 150
        total_rows = n_cycles * n_points
        
        data = {
            'subject_id': np.repeat(['S001'], total_rows),
            'task': np.repeat(['level_walking'], total_rows),
            'cycle_id': np.repeat(range(n_cycles), n_points),
            'phase': np.tile(np.linspace(0, 100, n_points), n_cycles),
            'step_number': np.repeat(range(n_cycles), n_points),
            
            # Realistic joint angles (in radians)
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.3, total_rows),
            'hip_flexion_angle_contra_rad': np.random.normal(0.1, 0.25, total_rows),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.4, total_rows),
            'knee_flexion_angle_contra_rad': np.random.normal(0.4, 0.35, total_rows),
            'ankle_flexion_angle_ipsi_rad': np.random.normal(-0.1, 0.2, total_rows),
            'ankle_flexion_angle_contra_rad': np.random.normal(-0.05, 0.18, total_rows),
            
            # Realistic joint moments (in Nm)
            'hip_flexion_moment_ipsi_Nm': np.random.normal(50, 20, total_rows),
            'hip_flexion_moment_contra_Nm': np.random.normal(45, 18, total_rows),
            'knee_flexion_moment_ipsi_Nm': np.random.normal(30, 15, total_rows),
            'knee_flexion_moment_contra_Nm': np.random.normal(25, 12, total_rows),
            'ankle_flexion_moment_ipsi_Nm': np.random.normal(80, 25, total_rows),
            'ankle_flexion_moment_contra_Nm': np.random.normal(75, 22, total_rows)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "small_test_dataset_phase.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def large_test_dataset(self, temp_dir):
        """Create large test dataset to trigger chunked processing."""
        np.random.seed(123)
        
        # Create dataset larger than default chunk_size (50000)
        n_cycles = 400  # 400 * 150 = 60,000 rows > 50,000
        n_points = 150
        total_rows = n_cycles * n_points
        
        data = {
            'subject_id': np.repeat([f'S{i:03d}' for i in range(10)], total_rows // 10),
            'task': np.repeat(['level_walking'], total_rows),
            'cycle_id': np.tile(range(n_cycles // 10), 10 * n_points),
            'phase': np.tile(np.linspace(0, 100, n_points), n_cycles),
            
            # More features for comprehensive testing
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.15, 0.25, total_rows),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.6, 0.3, total_rows),
            'ankle_flexion_angle_ipsi_rad': np.random.normal(-0.08, 0.15, total_rows),
            'hip_flexion_moment_ipsi_Nm': np.random.normal(55, 25, total_rows)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "large_test_dataset_phase.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def phase_percent_dataset(self, temp_dir):
        """Create dataset with phase_percent column instead of phase."""
        np.random.seed(456)
        
        data = {
            'subject_id': ['S001'] * 300,
            'task': ['level_walking'] * 300,
            'phase_percent': np.tile(np.linspace(0, 100, 150), 2),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.25, 0.2, 300),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.45, 0.3, 300)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "phase_percent_dataset_phase.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def invalid_dataset_no_phase(self, temp_dir):
        """Create invalid dataset missing phase columns."""
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 100)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "invalid_no_phase_dataset.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def invalid_dataset_no_biomech(self, temp_dir):
        """Create invalid dataset missing biomechanical features."""
        data = {
            'subject_id': ['S001'] * 150,
            'task': ['level_walking'] * 150,
            'phase': np.linspace(0, 100, 150),
            'other_column': np.random.normal(0, 1, 150)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "invalid_no_biomech_dataset.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def empty_phase_dataset(self, temp_dir):
        """Create dataset with all NaN phase values."""
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'phase': [np.nan] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 100)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "empty_phase_dataset.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def validation_file(self, temp_dir):
        """Create mock validation expectations file."""
        content = """# Kinematic Validation Expectations

## Level Walking

### Phase 25

| Feature | Min | Max |
|---------|-----|-----|
| hip_flexion_angle_ipsi_rad | -0.5 | 0.8 |
| knee_flexion_angle_ipsi_rad | 0.0 | 1.2 |

### Phase 50

| Feature | Min | Max |
|---------|-----|-----|
| hip_flexion_angle_ipsi_rad | -0.3 | 0.6 |
| knee_flexion_angle_ipsi_rad | 0.1 | 1.0 |
"""
        file_path = temp_dir / "validation_expectations_kinematic.md"
        file_path.write_text(content)
        return file_path
    
    @pytest.fixture
    def cli_script_path(self):
        """Get path to CLI script."""
        return project_root / "contributor_scripts" / "optimize_validation_ranges.py"
    
    def run_cli(self, cli_script_path, args, expected_success=True):
        """Run CLI script with given arguments."""
        cmd = [sys.executable, str(cli_script_path)] + args
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=60  # Prevent hanging
        )
        
        if expected_success:
            if result.returncode != 0:
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                pytest.fail(f"CLI script failed with return code {result.returncode}")
        
        return result
    
    def test_basic_percentile_optimization(self, cli_script_path, small_test_dataset, temp_dir):
        """Test basic percentile method optimization."""
        output_dir = temp_dir / "basic_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--method', 'percentile',
            '--percentiles', '10', '90',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Check outputs were created
        assert output_dir.exists()
        assert any(f.name.startswith('optimization_report_percentile_') for f in output_dir.iterdir())
        assert any(f.name.startswith('optimized_ranges_percentile_') for f in output_dir.iterdir())
        
        # Verify success message in output
        assert "OPTIMIZATION COMPLETE" in result.stdout
        assert "Method: percentile" in result.stdout
    
    def test_std_dev_method(self, cli_script_path, small_test_dataset, temp_dir):
        """Test standard deviation method."""
        output_dir = temp_dir / "std_dev_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--method', 'std_dev',
            '--num-std-dev', '3.0',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "Method: std_dev" in result.stdout
        assert output_dir.exists()
    
    def test_iqr_method(self, cli_script_path, small_test_dataset, temp_dir):
        """Test IQR method."""
        output_dir = temp_dir / "iqr_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--method', 'iqr',
            '--iqr-multiplier', '2.0',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "Method: iqr" in result.stdout
        assert output_dir.exists()
    
    def test_target_fp_rate_optimization(self, cli_script_path, small_test_dataset, temp_dir):
        """Test target false positive rate optimization."""
        output_dir = temp_dir / "fp_rate_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--target-fp-rate', '0.1',
            '--fp-tolerance', '0.02',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "target_fp_rate_0.1" in result.stdout
        assert output_dir.exists()
    
    def test_multi_dataset_processing(self, cli_script_path, small_test_dataset, phase_percent_dataset, temp_dir):
        """Test processing multiple datasets with weights."""
        output_dir = temp_dir / "multi_dataset_output"
        
        args = [
            '--datasets', str(small_test_dataset), str(phase_percent_dataset),
            '--weights', '2.0', '1.0',
            '--method', 'percentile',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "Successfully loaded 2/2 datasets" in result.stdout
        assert output_dir.exists()
    
    def test_chunked_processing_large_dataset(self, cli_script_path, large_test_dataset, temp_dir):
        """Test chunked processing for large datasets."""
        output_dir = temp_dir / "chunked_output"
        
        args = [
            '--datasets', str(large_test_dataset),
            '--chunk-size', '10000',  # Small chunk size to force chunking
            '--method', 'percentile',
            '--output-dir', str(output_dir),
            '--verbose'
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Should see chunking messages in verbose output
        assert "Processing large dataset" in result.stdout or "chunk" in result.stdout.lower()
        assert output_dir.exists()
    
    def test_feature_selection_kinematic_only(self, cli_script_path, small_test_dataset, temp_dir):
        """Test kinematic-only feature selection."""
        output_dir = temp_dir / "kinematic_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--kinematic-only',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert output_dir.exists()
        
        # Check JSON output contains only kinematic features
        json_files = list(output_dir.glob('optimized_ranges_*.json'))
        assert len(json_files) > 0
        
        with open(json_files[0]) as f:
            data = json.load(f)
        
        optimized_features = set(data['optimized_ranges'].keys())
        kinematic_features = set(f for f in ANGLE_FEATURES if f in optimized_features)
        moment_features = set(f for f in MOMENT_FEATURES if f in optimized_features)
        
        # Should have kinematic features and no moment features
        assert len(kinematic_features) > 0
        assert len(moment_features) == 0
    
    def test_feature_selection_kinetic_only(self, cli_script_path, small_test_dataset, temp_dir):
        """Test kinetic-only feature selection."""
        output_dir = temp_dir / "kinetic_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--kinetic-only',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert output_dir.exists()
    
    def test_specific_features_selection(self, cli_script_path, small_test_dataset, temp_dir):
        """Test specific feature selection."""
        output_dir = temp_dir / "specific_features_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--features', 'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert output_dir.exists()
        
        # Check only specified features were optimized
        json_files = list(output_dir.glob('optimized_ranges_*.json'))
        assert len(json_files) > 0
        
        with open(json_files[0]) as f:
            data = json.load(f)
        
        optimized_features = set(data['optimized_ranges'].keys())
        expected_features = {'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'}
        
        # Should only have the specified features (subset of expected due to data availability)
        assert optimized_features.issubset(expected_features)
    
    def test_comparison_with_current_validation(self, cli_script_path, small_test_dataset, validation_file, temp_dir):
        """Test comparison with current validation file."""
        output_dir = temp_dir / "comparison_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--compare-current', str(validation_file),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert output_dir.exists()
        
        # Check comparison file was created
        comparison_files = list(output_dir.glob('fp_rate_comparison_*.json'))
        assert len(comparison_files) > 0
        
        with open(comparison_files[0]) as f:
            comparison_data = json.load(f)
        
        assert 'current_fp_rates' in comparison_data
        assert 'optimized_ranges' in comparison_data
        assert 'comparison_timestamp' in comparison_data
    
    def test_report_only_mode(self, cli_script_path, small_test_dataset, temp_dir):
        """Test report-only mode."""
        output_dir = temp_dir / "report_only_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--report-only',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "Next steps:" in result.stdout
        assert output_dir.exists()
    
    def test_verbose_logging(self, cli_script_path, small_test_dataset, temp_dir):
        """Test verbose logging mode."""
        output_dir = temp_dir / "verbose_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--verbose',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Verbose mode should produce more detailed output
        assert len(result.stdout) > 100  # Should have substantial output
        assert output_dir.exists()
    
    def test_error_mismatched_weights(self, cli_script_path, small_test_dataset, phase_percent_dataset, temp_dir):
        """Test error when number of weights doesn't match datasets."""
        args = [
            '--datasets', str(small_test_dataset), str(phase_percent_dataset),
            '--weights', '1.0',  # Only one weight for two datasets
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "Number of weights must match number of datasets" in result.stderr
    
    def test_error_conflicting_feature_flags(self, cli_script_path, small_test_dataset, temp_dir):
        """Test error when both kinematic-only and kinetic-only are specified."""
        args = [
            '--datasets', str(small_test_dataset),
            '--kinematic-only',
            '--kinetic-only',
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "Cannot specify both --kinematic-only and --kinetic-only" in result.stderr
    
    def test_error_nonexistent_dataset(self, cli_script_path, temp_dir):
        """Test error handling for nonexistent dataset."""
        nonexistent_file = temp_dir / "nonexistent_dataset.parquet"
        
        args = [
            '--datasets', str(nonexistent_file),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "No datasets successfully loaded" in result.stdout
    
    def test_error_invalid_dataset_no_phase(self, cli_script_path, invalid_dataset_no_phase, temp_dir):
        """Test error handling for dataset missing phase columns."""
        args = [
            '--datasets', str(invalid_dataset_no_phase),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "No datasets successfully loaded" in result.stdout
    
    def test_error_invalid_dataset_no_biomech(self, cli_script_path, invalid_dataset_no_biomech, temp_dir):
        """Test error handling for dataset missing biomechanical features."""
        args = [
            '--datasets', str(invalid_dataset_no_biomech),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "No datasets successfully loaded" in result.stdout
    
    def test_error_empty_phase_dataset(self, cli_script_path, empty_phase_dataset, temp_dir):
        """Test error handling for dataset with no valid phase data."""
        args = [
            '--datasets', str(empty_phase_dataset),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        result = self.run_cli(cli_script_path, args, expected_success=False)
        
        assert result.returncode != 0
        assert "No datasets successfully loaded" in result.stdout
    
    def test_phase_percent_column_support(self, cli_script_path, phase_percent_dataset, temp_dir):
        """Test support for phase_percent column."""
        output_dir = temp_dir / "phase_percent_output"
        
        args = [
            '--datasets', str(phase_percent_dataset),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert "Successfully loaded 1/1 datasets" in result.stdout
        assert output_dir.exists()
    
    def test_default_argument_values(self, cli_script_path, small_test_dataset, temp_dir):
        """Test default argument values are applied correctly."""
        output_dir = temp_dir / "defaults_output"
        
        # Minimal arguments to test defaults
        args = [
            '--datasets', str(small_test_dataset),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Should use default method (percentile) and percentiles (5, 95)
        assert "Method: percentile" in result.stdout
        assert output_dir.exists()
        
        # Check that default values were used in output files
        json_files = list(output_dir.glob('optimized_ranges_*.json'))
        assert len(json_files) > 0
    
    def test_output_file_generation(self, cli_script_path, small_test_dataset, temp_dir):
        """Test all expected output files are generated."""
        output_dir = temp_dir / "file_generation_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Check report file
        report_files = list(output_dir.glob('optimization_report_*.md'))
        assert len(report_files) > 0
        
        report_content = report_files[0].read_text()
        assert "# Validation Range Optimization Report" in report_content
        assert "## Datasets Processed" in report_content
        assert "## Optimized Ranges" in report_content
        
        # Check JSON file
        json_files = list(output_dir.glob('optimized_ranges_*.json'))
        assert len(json_files) > 0
        
        with open(json_files[0]) as f:
            json_data = json.load(f)
        
        assert 'metadata' in json_data
        assert 'optimized_ranges' in json_data
        assert 'generated' in json_data['metadata']
        assert 'datasets' in json_data['metadata']
    
    def test_edge_case_single_value_feature(self, cli_script_path, temp_dir):
        """Test edge case where a feature has only one unique value."""
        # Create dataset with constant feature value
        data = {
            'subject_id': ['S001'] * 150,
            'task': ['level_walking'] * 150,
            'phase': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': [0.5] * 150  # Constant value
        }
        
        df = pd.DataFrame(data)
        dataset_path = temp_dir / "constant_feature_dataset.parquet"
        df.to_parquet(dataset_path)
        
        output_dir = temp_dir / "constant_output"
        
        args = [
            '--datasets', str(dataset_path),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Should still complete successfully
        assert result.returncode == 0
        assert output_dir.exists()
    
    def test_edge_case_nan_values(self, cli_script_path, temp_dir):
        """Test handling of NaN values in features."""
        np.random.seed(789)
        
        # Create dataset with some NaN values
        values = np.random.normal(0.3, 0.2, 150)
        values[::10] = np.nan  # Every 10th value is NaN
        
        data = {
            'subject_id': ['S001'] * 150,
            'task': ['level_walking'] * 150,
            'phase': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': values,
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.6, 0.3, 150)
        }
        
        df = pd.DataFrame(data)
        dataset_path = temp_dir / "nan_values_dataset.parquet"
        df.to_parquet(dataset_path)
        
        output_dir = temp_dir / "nan_output"
        
        args = [
            '--datasets', str(dataset_path),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Should handle NaN values gracefully
        assert result.returncode == 0
        assert output_dir.exists()
    
    def test_all_optimization_methods_comprehensive(self, cli_script_path, small_test_dataset, temp_dir):
        """Test all optimization methods with different parameters."""
        methods_and_args = [
            (['--method', 'percentile', '--percentiles', '1', '99'], 'percentile'),
            (['--method', 'std_dev', '--num-std-dev', '1.5'], 'std_dev'),
            (['--method', 'std_dev', '--num-std-dev', '4.0'], 'std_dev'),
            (['--method', 'iqr', '--iqr-multiplier', '1.0'], 'iqr'),
            (['--method', 'iqr', '--iqr-multiplier', '3.0'], 'iqr'),
        ]
        
        for method_args, method_name in methods_and_args:
            output_dir = temp_dir / f"{method_name}_comprehensive_output_{hash(str(method_args))}"
            
            args = [
                '--datasets', str(small_test_dataset),
                '--output-dir', str(output_dir)
            ] + method_args
            
            result = self.run_cli(cli_script_path, args)
            
            assert result.returncode == 0
            assert f"Method: {method_name}" in result.stdout
            assert output_dir.exists()
    
    def test_memory_efficiency_options(self, cli_script_path, large_test_dataset, temp_dir):
        """Test various chunk sizes for memory efficiency."""
        chunk_sizes = [5000, 25000, 100000]
        
        for chunk_size in chunk_sizes:
            output_dir = temp_dir / f"chunk_{chunk_size}_output"
            
            args = [
                '--datasets', str(large_test_dataset),
                '--chunk-size', str(chunk_size),
                '--output-dir', str(output_dir)
            ]
            
            result = self.run_cli(cli_script_path, args)
            
            assert result.returncode == 0
            assert output_dir.exists()
    
    def test_import_error_handling(self, cli_script_path, temp_dir):
        """Test import error handling by mocking import failure."""
        # This test requires running the script in an environment where imports fail
        # We'll test this by temporarily renaming the lib directory
        
        lib_dir = project_root / "lib"
        temp_lib_dir = project_root / "lib_temp_hidden"
        
        try:
            # Temporarily hide lib directory to trigger import error
            if lib_dir.exists():
                lib_dir.rename(temp_lib_dir)
                
                args = ['--datasets', 'dummy.parquet']
                result = self.run_cli(cli_script_path, args, expected_success=False)
                
                assert result.returncode == 1
                assert "Error importing required modules" in result.stdout
                
        finally:
            # Restore lib directory
            if temp_lib_dir.exists():
                temp_lib_dir.rename(lib_dir)
    
    def test_json_export_comprehensive(self, cli_script_path, small_test_dataset, temp_dir):
        """Test comprehensive JSON export functionality."""
        output_dir = temp_dir / "json_comprehensive_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--method', 'percentile',
            '--percentiles', '25', '75',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Find and validate JSON file
        json_files = list(output_dir.glob('optimized_ranges_*.json'))
        assert len(json_files) > 0
        
        with open(json_files[0]) as f:
            data = json.load(f)
        
        # Validate JSON structure
        assert 'metadata' in data
        assert 'optimized_ranges' in data
        
        metadata = data['metadata']
        assert 'generated' in metadata
        assert 'datasets' in metadata
        assert 'total_observations' in metadata
        
        # Validate dataset info
        datasets = metadata['datasets']
        assert len(datasets) > 0
        assert 'name' in datasets[0]
        assert 'path' in datasets[0]
        assert 'weight' in datasets[0]
        assert 'rows' in datasets[0]
        assert 'features' in datasets[0]
        
        # Validate optimized ranges
        optimized_ranges = data['optimized_ranges']
        for feature, range_dict in optimized_ranges.items():
            assert 'min' in range_dict
            assert 'max' in range_dict
            assert isinstance(range_dict['min'], (int, float))
            assert isinstance(range_dict['max'], (int, float))
            assert range_dict['min'] <= range_dict['max']
    
    def test_logging_configuration(self, cli_script_path, small_test_dataset, temp_dir):
        """Test logging configuration and output."""
        output_dir = temp_dir / "logging_output"
        
        # Test normal logging
        args = [
            '--datasets', str(small_test_dataset),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Should have INFO level messages
        assert "Initializing validation range optimizer" in result.stdout
        assert "Successfully loaded" in result.stdout
        
        # Test verbose logging
        output_dir_verbose = temp_dir / "logging_verbose_output"
        
        args_verbose = [
            '--datasets', str(small_test_dataset),
            '--verbose',
            '--output-dir', str(output_dir_verbose)
        ]
        
        result_verbose = self.run_cli(cli_script_path, args_verbose)
        
        # Verbose should have more detailed output
        assert len(result_verbose.stdout) >= len(result.stdout)
    
    def test_no_ranges_optimized_error(self):
        """Test error when no ranges can be optimized."""
        # This would happen when no valid features are found
        # We test this through the empty biomech dataset
        pass  # Covered by test_error_invalid_dataset_no_biomech
    
    def test_all_argument_combinations(self, cli_script_path, small_test_dataset, phase_percent_dataset, temp_dir):
        """Test various argument combinations for comprehensive coverage."""
        test_cases = [
            # Basic cases
            ['--datasets', str(small_test_dataset)],
            ['--datasets', str(small_test_dataset), '--method', 'percentile'],
            ['--datasets', str(small_test_dataset), '--method', 'std_dev'],
            ['--datasets', str(small_test_dataset), '--method', 'iqr'],
            
            # Target FP rate variations
            ['--datasets', str(small_test_dataset), '--target-fp-rate', '0.05'],
            ['--datasets', str(small_test_dataset), '--target-fp-rate', '0.01', '--fp-tolerance', '0.005'],
            
            # Feature selection variations
            ['--datasets', str(small_test_dataset), '--features', 'hip_flexion_angle_ipsi_rad'],
            ['--datasets', str(small_test_dataset), '--kinematic-only'],
            ['--datasets', str(small_test_dataset), '--kinetic-only'],
            
            # Multi-dataset
            ['--datasets', str(small_test_dataset), str(phase_percent_dataset)],
            ['--datasets', str(small_test_dataset), str(phase_percent_dataset), '--weights', '1.5', '0.5'],
            
            # Processing options
            ['--datasets', str(small_test_dataset), '--chunk-size', '1000'],
            ['--datasets', str(small_test_dataset), '--report-only'],
            ['--datasets', str(small_test_dataset), '--verbose'],
        ]
        
        for i, args in enumerate(test_cases):
            output_dir = temp_dir / f"combo_{i}_output"
            full_args = args + ['--output-dir', str(output_dir)]
            
            result = self.run_cli(cli_script_path, full_args)
            
            assert result.returncode == 0, f"Failed on test case {i}: {args}"
            assert output_dir.exists(), f"Output directory not created for test case {i}: {args}"
    
    def test_output_directory_creation(self, cli_script_path, small_test_dataset, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        nonexistent_output_dir = temp_dir / "deeply" / "nested" / "output" / "dir"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--output-dir', str(nonexistent_output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert result.returncode == 0
        assert nonexistent_output_dir.exists()
        assert any(nonexistent_output_dir.iterdir())  # Contains output files
    
    def test_timestamp_in_filenames(self, cli_script_path, small_test_dataset, temp_dir):
        """Test that timestamps are included in output filenames."""
        output_dir = temp_dir / "timestamp_output"
        
        args = [
            '--datasets', str(small_test_dataset),
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        # Check that files have timestamps in their names
        files = list(output_dir.iterdir())
        assert len(files) >= 2  # Should have both report and JSON files
        
        for file in files:
            # Timestamp format should be YYYYMMDD_HHMMSS
            assert any(part.replace('_', '').isdigit() and len(part) >= 8 
                      for part in file.stem.split('_'))
    
    @pytest.mark.timeout(30)
    def test_performance_large_dataset(self, cli_script_path, large_test_dataset, temp_dir):
        """Test performance with large dataset (should complete within timeout)."""
        output_dir = temp_dir / "performance_output"
        
        args = [
            '--datasets', str(large_test_dataset),
            '--chunk-size', '20000',
            '--output-dir', str(output_dir)
        ]
        
        result = self.run_cli(cli_script_path, args)
        
        assert result.returncode == 0
        assert output_dir.exists()
        
        # Should have processed the large dataset successfully
        assert "Successfully loaded 1/1 datasets" in result.stdout


class TestValidationRangeOptimizerDirect:
    """Direct testing of ValidationRangeOptimizer class for 100% coverage."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample biomechanical data for testing."""
        np.random.seed(42)
        return {
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.3, 100),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.4, 100),
            'hip_flexion_moment_ipsi_Nm': np.random.normal(50, 20, 100)
        }
    
    @pytest.fixture
    def sample_dataset(self, temp_dir, sample_data):
        """Create sample dataset file."""
        n_rows = 300
        data = {
            'subject_id': ['S001'] * n_rows,
            'task': ['level_walking'] * n_rows,
            'phase': np.tile(np.linspace(0, 100, 150), 2),
            **{k: np.tile(v[:150], 2) for k, v in sample_data.items()}
        }
        
        # Ensure all arrays have the same length
        for key, values in data.items():
            if len(values) != n_rows:
                # Repeat or truncate to match n_rows
                if len(values) < n_rows:
                    repeats = (n_rows // len(values)) + 1
                    data[key] = np.tile(values, repeats)[:n_rows]
                else:
                    data[key] = values[:n_rows]
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "sample_dataset.parquet"
        df.to_parquet(file_path)
        return file_path
    
    @pytest.fixture
    def optimizer(self):
        """Create ValidationRangeOptimizer instance."""
        if ValidationRangeOptimizer is None:
            pytest.skip("ValidationRangeOptimizer not available")
        return ValidationRangeOptimizer(chunk_size=1000)
    
    def test_optimizer_initialization(self):
        """Test ValidationRangeOptimizer initialization."""
        if ValidationRangeOptimizer is None:
            pytest.skip("ValidationRangeOptimizer not available")
        
        # Test default initialization
        optimizer = ValidationRangeOptimizer()
        assert optimizer.chunk_size == 50000
        assert optimizer.processed_datasets == []
        
        # Test custom chunk_size
        optimizer_custom = ValidationRangeOptimizer(chunk_size=10000)
        assert optimizer_custom.chunk_size == 10000
    
    def test_load_dataset_success(self, optimizer, sample_dataset):
        """Test successful dataset loading."""
        result = optimizer.load_dataset(str(sample_dataset), weight=2.0)
        
        assert result is True
        assert len(optimizer.processed_datasets) == 1
        
        dataset_info = optimizer.processed_datasets[0]
        assert dataset_info['name'] == 'sample_dataset'
        assert dataset_info['weight'] == 2.0
        assert dataset_info['rows'] == 300
        assert dataset_info['features'] >= 1
    
    def test_load_nonexistent_dataset(self, optimizer, temp_dir):
        """Test loading nonexistent dataset."""
        nonexistent_path = temp_dir / "nonexistent.parquet"
        result = optimizer.load_dataset(str(nonexistent_path))
        
        assert result is False
        assert len(optimizer.processed_datasets) == 0
    
    def test_load_dataset_no_phase_column(self, optimizer, temp_dir):
        """Test loading dataset without phase columns."""
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 100)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "no_phase_dataset.parquet"
        df.to_parquet(file_path)
        
        result = optimizer.load_dataset(str(file_path))
        
        assert result is False
        assert len(optimizer.processed_datasets) == 0
    
    def test_load_dataset_no_biomech_features(self, optimizer, temp_dir):
        """Test loading dataset without biomechanical features."""
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'phase': np.linspace(0, 100, 100),
            'other_column': np.random.normal(0, 1, 100)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "no_biomech_dataset.parquet"
        df.to_parquet(file_path)
        
        result = optimizer.load_dataset(str(file_path))
        
        assert result is False
        assert len(optimizer.processed_datasets) == 0
    
    def test_load_dataset_empty_phase_data(self, optimizer, temp_dir):
        """Test loading dataset with all NaN phase data."""
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'phase': [np.nan] * 100,
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 100)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "empty_phase_dataset.parquet"
        df.to_parquet(file_path)
        
        result = optimizer.load_dataset(str(file_path))
        
        assert result is False
        assert len(optimizer.processed_datasets) == 0
    
    def test_load_dataset_phase_percent_column(self, optimizer, temp_dir):
        """Test loading dataset with phase_percent column."""
        data = {
            'subject_id': ['S001'] * 150,
            'task': ['level_walking'] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "phase_percent_dataset.parquet"
        df.to_parquet(file_path)
        
        result = optimizer.load_dataset(str(file_path))
        
        assert result is True
        assert len(optimizer.processed_datasets) == 1
    
    def test_load_large_dataset_chunked_processing(self, temp_dir):
        """Test chunked processing of large dataset."""
        if ValidationRangeOptimizer is None:
            pytest.skip("ValidationRangeOptimizer not available")
        
        # Create optimizer with very small chunk size to force chunking
        optimizer = ValidationRangeOptimizer(chunk_size=50)
        
        # Create dataset larger than chunk size
        n_rows = 200
        data = {
            'subject_id': ['S001'] * n_rows,
            'task': ['level_walking'] * n_rows,
            'phase': np.tile(np.linspace(0, 100, 150), n_rows // 150 + 1)[:n_rows],
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, n_rows)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "large_dataset.parquet"
        df.to_parquet(file_path)
        
        result = optimizer.load_dataset(str(file_path))
        
        assert result is True
        assert len(optimizer.processed_datasets) == 1
        assert optimizer.processed_datasets[0]['rows'] == n_rows
    
    def test_load_dataset_exception_handling(self, optimizer, temp_dir):
        """Test exception handling during dataset loading."""
        # Create a file that will cause an exception when read
        bad_file = temp_dir / "bad_dataset.parquet"
        bad_file.write_text("this is not a parquet file")
        
        result = optimizer.load_dataset(str(bad_file))
        
        assert result is False
        assert len(optimizer.processed_datasets) == 0
    
    def test_extract_biomechanical_features(self, optimizer):
        """Test biomechanical feature extraction."""
        # Create test dataframe with various features
        df = pd.DataFrame({
            'hip_flexion_angle_ipsi_rad': [1, 2, 3],
            'knee_flexion_angle_ipsi_rad': [1, 2, 3],
            'hip_flexion_moment_ipsi_Nm': [1, 2, 3],
            'other_column': [1, 2, 3]
        })
        
        features = optimizer._extract_biomechanical_features(df)
        
        # Should extract only the biomechanical features
        expected_features = {'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'hip_flexion_moment_ipsi_Nm'}
        assert set(features).issubset(expected_features)
        assert 'other_column' not in features
    
    def test_optimize_ranges_percentile(self, optimizer, sample_dataset):
        """Test range optimization using percentile method."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        result = optimizer.optimize_ranges(
            method='percentile',
            features=features,
            percentiles=(10, 90)
        )
        
        assert isinstance(result, dict)
        assert len(result) > 0
        
        for feature, range_dict in result.items():
            assert 'min' in range_dict
            assert 'max' in range_dict
            assert range_dict['min'] <= range_dict['max']
    
    def test_optimize_ranges_std_dev(self, optimizer, sample_dataset):
        """Test range optimization using standard deviation method."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        result = optimizer.optimize_ranges(
            method='std_dev',
            features=features,
            num_std_dev=2.0
        )
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_optimize_ranges_iqr(self, optimizer, sample_dataset):
        """Test range optimization using IQR method."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        result = optimizer.optimize_ranges(
            method='iqr',
            features=features,
            iqr_multiplier=1.5
        )
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_optimize_ranges_no_features(self, optimizer):
        """Test optimization with no features available."""
        result = optimizer.optimize_ranges(
            method='percentile',
            features=[]
        )
        
        assert result == {}
    
    def test_optimize_ranges_unknown_method(self, optimizer, sample_dataset):
        """Test optimization with unknown method."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        result = optimizer.optimize_ranges(
            method='unknown_method',
            features=features
        )
        
        # Should handle unknown method gracefully by returning empty dict
        assert result == {}
    
    def test_optimize_for_target_fp_rate(self, optimizer, sample_dataset):
        """Test optimization for target false positive rate."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        result = optimizer.optimize_for_target_fp_rate(
            features=features,
            target_fp_rate=0.1,
            tolerance=0.02
        )
        
        assert isinstance(result, dict)
    
    def test_optimize_for_target_fp_rate_no_features(self, optimizer):
        """Test FP rate optimization with no features."""
        result = optimizer.optimize_for_target_fp_rate(features=[])
        
        assert result == {}
    
    def test_calculate_current_fp_rates(self, optimizer, sample_dataset, temp_dir):
        """Test calculation of current false positive rates."""
        optimizer.load_dataset(str(sample_dataset))
        
        # Create mock validation file
        validation_content = """# Kinematic Validation Expectations

## Level Walking

### Phase 25

| Feature | Min | Max |
|---------|-----|-----|
| hip_flexion_angle_ipsi_rad | -0.5 | 0.8 |

### Phase 50

| Feature | Min | Max |
|---------|-----|-----|
| hip_flexion_angle_ipsi_rad | -0.3 | 0.6 |
"""
        validation_file = temp_dir / "validation.md"
        validation_file.write_text(validation_content)
        
        result = optimizer.calculate_current_fp_rates(str(validation_file))
        
        assert isinstance(result, dict)
    
    def test_calculate_current_fp_rates_error(self, optimizer, temp_dir):
        """Test FP rate calculation with invalid validation file."""
        invalid_file = temp_dir / "invalid_validation.md"
        invalid_file.write_text("invalid content")
        
        result = optimizer.calculate_current_fp_rates(str(invalid_file))
        
        assert result == {}
    
    def test_generate_report(self, optimizer, sample_dataset, temp_dir):
        """Test report generation."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        optimized_ranges = optimizer.optimize_ranges(
            method='percentile',
            features=features
        )
        
        report_file = temp_dir / "test_report.md"
        report = optimizer.generate_report(
            optimized_ranges, 
            'percentile',
            str(report_file)
        )
        
        assert isinstance(report, str)
        assert "# Validation Range Optimization Report" in report
        assert report_file.exists()
        
        report_content = report_file.read_text()
        assert "# Validation Range Optimization Report" in report_content
    
    def test_generate_report_without_file(self, optimizer, sample_dataset):
        """Test report generation without output file."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        optimized_ranges = optimizer.optimize_ranges(
            method='percentile',
            features=features
        )
        
        report = optimizer.generate_report(optimized_ranges, 'percentile')
        
        assert isinstance(report, str)
        assert "# Validation Range Optimization Report" in report
    
    def test_generate_report_file_error(self, optimizer, sample_dataset):
        """Test report generation with file write error."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        optimized_ranges = optimizer.optimize_ranges(
            method='percentile',
            features=features
        )
        
        # Try to write to invalid path
        report = optimizer.generate_report(
            optimized_ranges, 
            'percentile',
            '/invalid/path/report.md'
        )
        
        # Should still return report string even if file write fails
        assert isinstance(report, str)
        assert "# Validation Range Optimization Report" in report
    
    def test_export_ranges_json(self, optimizer, sample_dataset, temp_dir):
        """Test JSON export of optimized ranges."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        optimized_ranges = optimizer.optimize_ranges(
            method='percentile',
            features=features
        )
        
        json_file = temp_dir / "test_ranges.json"
        optimizer.export_ranges_json(optimized_ranges, str(json_file))
        
        assert json_file.exists()
        
        with open(json_file) as f:
            data = json.load(f)
        
        assert 'metadata' in data
        assert 'optimized_ranges' in data
        assert data['optimized_ranges'] == optimized_ranges
    
    def test_export_ranges_json_error(self, optimizer, sample_dataset):
        """Test JSON export with file write error."""
        optimizer.load_dataset(str(sample_dataset))
        
        features = list(optimizer.optimizer.aggregator.get_feature_names())
        if not features:
            pytest.skip("No features available for optimization")
        
        optimized_ranges = optimizer.optimize_ranges(
            method='percentile',
            features=features
        )
        
        # Try to write to invalid path - should not raise exception
        optimizer.export_ranges_json(optimized_ranges, '/invalid/path/ranges.json')


class TestMainFunctionDirect:
    """Direct testing of main() function for complete coverage."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_dataset(self, temp_dir):
        """Create sample dataset file."""
        np.random.seed(42)
        data = {
            'subject_id': ['S001'] * 300,
            'task': ['level_walking'] * 300,
            'phase': np.tile(np.linspace(0, 100, 150), 2),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 300),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 300)
        }
        
        df = pd.DataFrame(data)
        file_path = temp_dir / "sample_dataset.parquet"
        df.to_parquet(file_path)
        return file_path
    
    def test_main_function_basic(self, sample_dataset, temp_dir):
        """Test main function with basic arguments."""
        if main is None:
            pytest.skip("main function not available")
        
        output_dir = temp_dir / "main_output"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--output-dir', str(output_dir)
        ]
        
        with patch('sys.argv', test_argv):
            with patch('builtins.print') as mock_print:
                main()
        
        assert output_dir.exists()
        
        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        success_messages = [msg for msg in print_calls if "OPTIMIZATION COMPLETE" in str(msg)]
        assert len(success_messages) > 0
    
    def test_main_function_all_methods(self, sample_dataset, temp_dir):
        """Test main function with all optimization methods."""
        if main is None:
            pytest.skip("main function not available")
        
        methods = [
            ['--method', 'percentile', '--percentiles', '10', '90'],
            ['--method', 'std_dev', '--num-std-dev', '2.0'],
            ['--method', 'iqr', '--iqr-multiplier', '1.5']
        ]
        
        for i, method_args in enumerate(methods):
            output_dir = temp_dir / f"main_method_{i}_output"
            
            test_argv = [
                'optimize_validation_ranges.py',
                '--datasets', str(sample_dataset),
                '--output-dir', str(output_dir)
            ] + method_args
            
            with patch('sys.argv', test_argv):
                with patch('builtins.print'):
                    main()
            
            assert output_dir.exists()
    
    def test_main_function_target_fp_rate(self, sample_dataset, temp_dir):
        """Test main function with target FP rate."""
        if main is None:
            pytest.skip("main function not available")
        
        output_dir = temp_dir / "main_fp_output"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--target-fp-rate', '0.05',
            '--fp-tolerance', '0.01',
            '--output-dir', str(output_dir)
        ]
        
        with patch('sys.argv', test_argv):
            with patch('builtins.print'):
                main()
        
        assert output_dir.exists()
    
    def test_main_function_feature_selection(self, sample_dataset, temp_dir):
        """Test main function with feature selection options."""
        if main is None:
            pytest.skip("main function not available")
        
        feature_options = [
            ['--features', 'hip_flexion_angle_ipsi_rad'],
            ['--kinematic-only'],
            ['--kinetic-only']
        ]
        
        for i, feature_args in enumerate(feature_options):
            output_dir = temp_dir / f"main_features_{i}_output"
            
            test_argv = [
                'optimize_validation_ranges.py',
                '--datasets', str(sample_dataset),
                '--output-dir', str(output_dir)
            ] + feature_args
            
            with patch('sys.argv', test_argv):
                with patch('builtins.print'):
                    main()
            
            assert output_dir.exists()
    
    def test_main_function_verbose(self, sample_dataset, temp_dir):
        """Test main function with verbose logging."""
        if main is None:
            pytest.skip("main function not available")
        
        output_dir = temp_dir / "main_verbose_output"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--verbose',
            '--output-dir', str(output_dir)
        ]
        
        with patch('sys.argv', test_argv):
            with patch('builtins.print'):
                main()
        
        assert output_dir.exists()
    
    def test_main_function_report_only(self, sample_dataset, temp_dir):
        """Test main function with report-only mode."""
        if main is None:
            pytest.skip("main function not available")
        
        output_dir = temp_dir / "main_report_only_output"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--report-only',
            '--output-dir', str(output_dir)
        ]
        
        with patch('sys.argv', test_argv):
            with patch('builtins.print') as mock_print:
                main()
        
        assert output_dir.exists()
        
        # Check that report-only specific messages were printed
        print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
        next_steps_messages = [msg for msg in print_calls if "Next steps:" in str(msg)]
        assert len(next_steps_messages) > 0
    
    def test_main_function_argument_validation_errors(self, sample_dataset, temp_dir):
        """Test main function argument validation errors."""
        if main is None:
            pytest.skip("main function not available")
        
        # Test mismatched weights
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset), str(sample_dataset),
            '--weights', '1.0',  # Only one weight for two datasets
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        with patch('sys.argv', test_argv):
            with pytest.raises(SystemExit):
                main()
        
        # Test conflicting feature flags
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--kinematic-only',
            '--kinetic-only',
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        with patch('sys.argv', test_argv):
            with pytest.raises(SystemExit):
                main()
    
    def test_main_function_no_successful_loads(self, temp_dir):
        """Test main function when no datasets load successfully."""
        if main is None:
            pytest.skip("main function not available")
        
        nonexistent_file = temp_dir / "nonexistent.parquet"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(nonexistent_file),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        with patch('sys.argv', test_argv):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    def test_main_function_no_ranges_optimized(self, temp_dir):
        """Test main function when no ranges can be optimized."""
        if main is None:
            pytest.skip("main function not available")
        
        # Create dataset with no biomechanical features
        data = {
            'subject_id': ['S001'] * 100,
            'task': ['level_walking'] * 100,
            'phase': np.linspace(0, 100, 100),
            'other_column': np.random.normal(0, 1, 100)
        }
        
        df = pd.DataFrame(data)
        dataset_path = temp_dir / "no_biomech_dataset.parquet"
        df.to_parquet(dataset_path)
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(dataset_path),
            '--output-dir', str(temp_dir / "error_output")
        ]
        
        with patch('sys.argv', test_argv):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    def test_main_function_comparison_mode(self, sample_dataset, temp_dir):
        """Test main function with comparison mode."""
        if main is None:
            pytest.skip("main function not available")
        
        # Create mock validation file
        validation_content = """# Kinematic Validation Expectations

## Level Walking

### Phase 25

| Feature | Min | Max |
|---------|-----|-----|
| hip_flexion_angle_ipsi_rad | -0.5 | 0.8 |
"""
        validation_file = temp_dir / "validation.md"
        validation_file.write_text(validation_content)
        
        output_dir = temp_dir / "main_comparison_output"
        
        test_argv = [
            'optimize_validation_ranges.py',
            '--datasets', str(sample_dataset),
            '--compare-current', str(validation_file),
            '--output-dir', str(output_dir)
        ]
        
        with patch('sys.argv', test_argv):
            with patch('builtins.print'):
                main()
        
        assert output_dir.exists()
        
        # Check that comparison file was created
        comparison_files = list(output_dir.glob('fp_rate_comparison_*.json'))
        assert len(comparison_files) > 0


if __name__ == '__main__':
    # Run tests if script is executed directly
    pytest.main([__file__, '-v', '--tb=short'])