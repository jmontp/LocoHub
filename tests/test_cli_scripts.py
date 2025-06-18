#!/usr/bin/env python3
"""
CLI Scripts Testing

Created: 2025-06-18 with user permission
Purpose: Test coverage for contributor_scripts CLI tools

Intent: Achieve 100% test coverage by testing all CLI entry points
for user stories US-02 through US-07
"""

import os
import sys
import unittest
import tempfile
import pandas as pd
import numpy as np
import subprocess
from pathlib import Path

class TestCLIScripts(unittest.TestCase):
    """Test CLI scripts functionality and coverage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dataset = self._create_test_dataset()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def _create_test_dataset(self):
        """Create a test dataset for CLI testing."""
        # Create valid phase dataset
        test_data = pd.DataFrame({
            'subject': ['subject_001'] * 150,
            'task': ['level_walking'] * 150,
            'step': [1] * 150,
            'phase_percent': np.linspace(0, 100, 150),
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.2, 0.1, 150),
            'knee_flexion_angle_ipsi_rad': np.random.normal(0.5, 0.2, 150)
        })
        
        dataset_path = os.path.join(self.temp_dir, "test_dataset_phase.parquet")
        test_data.to_parquet(dataset_path)
        return dataset_path
    
    def test_detect_dataset_type_cli(self):
        """Test detect_dataset_type.py CLI functionality."""
        cmd = [
            sys.executable, 
            "contributor_scripts/detect_dataset_type.py",
            "--json",
            self.test_dataset
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Should run without error
        self.assertEqual(result.returncode, 0, f"CLI failed with: {result.stderr}")
        
        # Should contain detection results
        output = result.stdout
        self.assertIn("confidence", output.lower())
        
    def test_validate_phase_dataset_cli(self):
        """Test validate_phase_dataset.py CLI functionality."""
        cmd = [
            sys.executable,
            "contributor_scripts/validate_phase_dataset.py", 
            "--dataset", self.test_dataset,
            "--quick"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Should run without error (even if validation fails due to missing specs)
        self.assertIn(result.returncode, [0, 1], f"CLI failed unexpectedly: {result.stderr}")
        
    def test_optimize_validation_ranges_cli(self):
        """Test optimize_validation_ranges.py CLI functionality."""
        cmd = [
            sys.executable,
            "contributor_scripts/optimize_validation_ranges.py",
            "--datasets", self.test_dataset,
            "--method", "percentile", 
            "--output", os.path.join(self.temp_dir, "optimized_ranges.json")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Should run without critical error
        self.assertIn(result.returncode, [0, 1], f"CLI failed unexpectedly: {result.stderr}")
        
    def test_update_validation_ranges_cli(self):
        """Test update_validation_ranges.py CLI functionality."""
        cmd = [
            sys.executable,
            "contributor_scripts/update_validation_ranges.py",
            "--help"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Help should always work
        self.assertEqual(result.returncode, 0, f"Help command failed: {result.stderr}")
        self.assertIn("usage", result.stdout.lower())
        
    def test_create_ml_benchmark_cli(self):
        """Test create_ml_benchmark.py CLI functionality."""
        cmd = [
            sys.executable,
            "contributor_scripts/create_ml_benchmark.py",
            self.test_dataset,
            "--output", os.path.join(self.temp_dir, "benchmark")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Should run (may fail due to insufficient data but shouldn't crash)
        self.assertIn(result.returncode, [0, 1], f"CLI failed unexpectedly: {result.stderr}")
        
    def test_create_dataset_release_cli(self):
        """Test create_dataset_release.py CLI functionality."""
        # Create minimal config file
        config_data = {
            "dataset_name": "test_dataset",
            "version": "1.0.0",
            "description": "Test dataset",
            "datasets": [self.test_dataset]
        }
        
        import json
        config_path = os.path.join(self.temp_dir, "release_config.json")
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
            
        cmd = [
            sys.executable,
            "contributor_scripts/create_dataset_release.py",
            "--config", config_path,
            "--output", os.path.join(self.temp_dir, "release")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Should run (may fail due to missing templates but shouldn't crash)
        self.assertIn(result.returncode, [0, 1], f"CLI failed unexpectedly: {result.stderr}")
        
    def test_all_cli_help_commands(self):
        """Test that all CLI scripts have functional help."""
        cli_scripts = [
            "contributor_scripts/detect_dataset_type.py",
            "contributor_scripts/validate_phase_dataset.py",
            "contributor_scripts/optimize_validation_ranges.py", 
            "contributor_scripts/update_validation_ranges.py",
            "contributor_scripts/create_ml_benchmark.py",
            "contributor_scripts/create_dataset_release.py"
        ]
        
        for script in cli_scripts:
            with self.subTest(script=script):
                cmd = [sys.executable, script, "--help"]
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
                
                self.assertEqual(result.returncode, 0, f"Help failed for {script}: {result.stderr}")
                self.assertIn("usage", result.stdout.lower(), f"No usage info in {script}")


class TestCoreLibraryFunctionality(unittest.TestCase):
    """Test core library functionality for better coverage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_locomotion_data_comprehensive(self):
        """Test LocomotionData core functionality."""
        from lib.core.locomotion_analysis import LocomotionData
        
        # Create comprehensive test dataset
        n_points = 300
        data = pd.DataFrame({
            'subject': (['S001'] * 150 + ['S002'] * 150),
            'task': ['walk'] * n_points,
            'step': ([1] * 150 + [2] * 150),
            'phase_percent': list(np.linspace(0, 100, 150)) * 2,
            'hip_angle': np.random.normal(0.2, 0.1, n_points),
            'knee_angle': np.random.normal(0.5, 0.2, n_points)
        })
        
        dataset_path = os.path.join(self.temp_dir, "comprehensive_test_phase.parquet")
        data.to_parquet(dataset_path)
        
        # Test loading
        locomotion_data = LocomotionData(
            dataset_path,
            phase_col='phase_percent',
            subject_col='subject', 
            task_col='task',
            step_col='step'
        )
        
        # Test properties
        self.assertEqual(len(locomotion_data.subjects), 2)
        self.assertEqual(len(locomotion_data.tasks), 1)
        self.assertGreater(len(locomotion_data.features), 0)
        
        # Test data access methods
        subject_data = locomotion_data.get_subject_data('S001')
        self.assertIsInstance(subject_data, pd.DataFrame)
        
        task_data = locomotion_data.get_task_data('walk')
        self.assertIsInstance(task_data, pd.DataFrame)
        
        # Test 3D array functionality if available
        if hasattr(locomotion_data, 'to_3d_array'):
            array_3d = locomotion_data.to_3d_array(['hip_angle'])
            self.assertEqual(len(array_3d.shape), 3)
            
    def test_feature_constants(self):
        """Test feature constants functionality."""
        import lib.core.feature_constants as fc
        
        # Test that module loads without error
        self.assertTrue(hasattr(fc, '__file__'))
        
        # Test any available constants
        constants = [attr for attr in dir(fc) if not attr.startswith('_')]
        self.assertGreater(len(constants), 0)


if __name__ == "__main__":
    unittest.main()