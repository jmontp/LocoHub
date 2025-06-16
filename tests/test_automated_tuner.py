#!/usr/bin/env python3
"""
Unit Tests for Automated Fine-Tuner

Created: 2025-06-12 with user permission
Purpose: Comprehensive unit tests for automated tuner functionality

Intent:
This test suite validates the AutomatedFineTuner's ability to:
1. Load and analyze locomotion data from parquet files
2. Calculate statistical ranges using different methods
3. Generate comprehensive reports
4. Integrate with the markdown parser correctly
5. Handle edge cases and error conditions

The tests use synthetic test data to avoid dependency on large datasets.
"""

import unittest
import tempfile
import os
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Add source directory to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from lib.validation.automated_fine_tuning import AutomatedFineTuner


class TestAutomatedFineTuner(unittest.TestCase):
    """Test suite for AutomatedFineTuner class."""
    
    def setUp(self):
        """Set up test fixtures including synthetic test data."""
        # Create synthetic test data
        self.test_data_file = None
        self.create_synthetic_test_data()
        
        # Initialize tuner
        self.tuner = AutomatedFineTuner(self.test_data_file, mode='kinematic')
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.test_data_file and os.path.exists(self.test_data_file):
            os.unlink(self.test_data_file)
    
    def create_synthetic_test_data(self):
        """Create synthetic parquet data for testing."""
        # Generate realistic biomechanical data
        np.random.seed(42)  # For reproducible tests
        
        # Create test data for 2 subjects, 2 tasks, 3 cycles each
        data_rows = []
        
        subjects = ['TEST_S001', 'TEST_S002']
        tasks = ['level_walking', 'decline_walking']
        
        for subject in subjects:
            for task in tasks:
                for cycle in range(3):  # 3 cycles per subject-task
                    cycle_id = f"{subject}_{task}_cycle_{cycle+1}"
                    
                    # Generate 150 phase points per cycle
                    for phase_idx in range(150):
                        phase_percent = (phase_idx / 149) * 100  # 0-100%
                        
                        # Generate realistic joint angles (in radians)
                        hip_angle = 0.3 + 0.2 * np.sin(2 * np.pi * phase_idx / 150) + np.random.normal(0, 0.05)
                        knee_angle = 0.1 + 0.3 * np.sin(2 * np.pi * phase_idx / 150 + np.pi/4) + np.random.normal(0, 0.03)
                        ankle_angle = -0.1 + 0.15 * np.sin(2 * np.pi * phase_idx / 150 + np.pi/2) + np.random.normal(0, 0.02)
                        
                        # Add task-specific variations
                        if task == 'decline_walking':
                            hip_angle += 0.1
                            knee_angle += 0.05
                            ankle_angle -= 0.05
                        
                        data_rows.append({
                            'subject': subject,
                            'task': task,
                            'cycle_id': cycle_id,
                            'phase_percent': phase_percent,
                            'hip_flexion_angle_ipsi_rad': hip_angle,
                            'knee_flexion_angle_ipsi_rad': knee_angle,
                            'ankle_flexion_angle_ipsi_rad': ankle_angle,
                            'hip_flexion_angle_contra_rad': hip_angle + np.random.normal(0, 0.02),
                            'knee_flexion_angle_contra_rad': knee_angle + np.random.normal(0, 0.02),
                            'ankle_flexion_angle_contra_rad': ankle_angle + np.random.normal(0, 0.02)
                        })
        
        # Create DataFrame and save as parquet
        df = pd.DataFrame(data_rows)
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
            self.test_data_file = f.name
        
        df.to_parquet(self.test_data_file)
    
    def test_tuner_initialization(self):
        """Test tuner initializes correctly with valid parameters."""
        tuner = AutomatedFineTuner('dummy_path.parquet', mode='kinematic')
        self.assertEqual(tuner.mode, 'kinematic')
        self.assertIn('percentile_95', tuner.methods)
        self.assertIn('mean_3std', tuner.methods)
        
        # Test kinetic mode
        tuner_kinetic = AutomatedFineTuner('dummy_path.parquet', mode='kinetic')
        self.assertEqual(tuner_kinetic.mode, 'kinetic')
    
    def test_statistical_methods(self):
        """Test all statistical methods with known data."""
        # Create test data with known properties
        test_values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        
        # Test mean_3std method
        min_val, max_val = self.tuner._method_mean_3std(test_values)
        expected_mean = 5.5
        expected_std = np.std(test_values)
        self.assertAlmostEqual(min_val, expected_mean - 3 * expected_std, places=3)
        self.assertAlmostEqual(max_val, expected_mean + 3 * expected_std, places=3)
        
        # Test percentile_95 method
        min_val, max_val = self.tuner._method_percentile_95(test_values)
        self.assertAlmostEqual(min_val, np.percentile(test_values, 2.5), places=3)
        self.assertAlmostEqual(max_val, np.percentile(test_values, 97.5), places=3)
        
        # Test percentile_90 method
        min_val, max_val = self.tuner._method_percentile_90(test_values)
        self.assertAlmostEqual(min_val, np.percentile(test_values, 5), places=3)
        self.assertAlmostEqual(max_val, np.percentile(test_values, 95), places=3)
        
        # Test iqr_expansion method
        min_val, max_val = self.tuner._method_iqr_expansion(test_values)
        q1 = np.percentile(test_values, 25)
        q3 = np.percentile(test_values, 75)
        iqr = q3 - q1
        self.assertAlmostEqual(min_val, q1 - 1.5 * iqr, places=3)
        self.assertAlmostEqual(max_val, q3 + 1.5 * iqr, places=3)
        
        # Test robust_percentile method
        min_val, max_val = self.tuner._method_robust_percentile(test_values)
        self.assertAlmostEqual(min_val, np.percentile(test_values, 10), places=3)
        self.assertAlmostEqual(max_val, np.percentile(test_values, 90), places=3)
        
        # Test conservative method
        min_val, max_val = self.tuner._method_conservative(test_values)
        data_min = np.min(test_values)
        data_max = np.max(test_values)
        range_width = data_max - data_min
        buffer = range_width * 0.05
        self.assertAlmostEqual(min_val, data_min - buffer, places=3)
        self.assertAlmostEqual(max_val, data_max + buffer, places=3)
    
    def test_statistical_methods_edge_cases(self):
        """Test statistical methods with edge cases."""
        # Test empty array
        empty_values = np.array([])
        
        for method_name in self.tuner.methods:
            method = self.tuner.methods[method_name]
            min_val, max_val = method(empty_values)
            self.assertEqual(min_val, 0.0)
            self.assertEqual(max_val, 0.0)
        
        # Test single value
        single_value = np.array([5.0])
        
        # Most methods should handle single values gracefully
        min_val, max_val = self.tuner._method_percentile_95(single_value)
        self.assertEqual(min_val, 5.0)
        self.assertEqual(max_val, 5.0)
    
    def test_data_loading_and_analysis(self):
        """Test data loading and organization functionality."""
        # This test requires the synthetic data file
        task_phase_data = self.tuner.load_and_analyze_data()
        
        # Verify structure
        self.assertIsInstance(task_phase_data, dict)
        self.assertIn('level_walking', task_phase_data)
        self.assertIn('decline_walking', task_phase_data)
        
        # Verify phases
        for task in task_phase_data:
            task_data = task_phase_data[task]
            self.assertIn(0, task_data)  # 0% phase
            self.assertIn(25, task_data)  # 25% phase
            self.assertIn(50, task_data)  # 50% phase
            self.assertIn(75, task_data)  # 75% phase
            
            # Verify variables
            for phase in task_data:
                phase_data = task_data[phase]
                self.assertIn('hip_flexion_angle_ipsi', phase_data)
                self.assertIn('knee_flexion_angle_ipsi', phase_data)
                self.assertIn('ankle_flexion_angle_ipsi', phase_data)
                
                # Verify data arrays
                for var_name, values in phase_data.items():
                    self.assertIsInstance(values, np.ndarray)
                    if len(values) > 0:
                        self.assertTrue(all(np.isfinite(values)))  # No NaN or inf values
    
    def test_statistical_range_calculation(self):
        """Test statistical range calculation with synthetic data."""
        # Load test data
        task_phase_data = self.tuner.load_and_analyze_data()
        
        # Calculate ranges using percentile_95 method
        validation_ranges = self.tuner.calculate_statistical_ranges(
            task_phase_data, method='percentile_95'
        )
        
        # Verify structure
        self.assertIsInstance(validation_ranges, dict)
        self.assertIn('level_walking', validation_ranges)
        self.assertIn('decline_walking', validation_ranges)
        
        # Verify range data
        for task, task_ranges in validation_ranges.items():
            for phase, phase_ranges in task_ranges.items():
                for var_name, range_data in phase_ranges.items():
                    self.assertIn('min', range_data)
                    self.assertIn('max', range_data)
                    
                    min_val = range_data['min']
                    max_val = range_data['max']
                    
                    # Basic sanity checks
                    if not np.isnan(min_val) and not np.isnan(max_val):
                        self.assertLessEqual(min_val, max_val, 
                                           f"Min should be <= max for {task}/{phase}/{var_name}")
    
    def test_different_statistical_methods(self):
        """Test that different statistical methods produce different results."""
        task_phase_data = self.tuner.load_and_analyze_data()
        
        # Calculate ranges with different methods
        ranges_95 = self.tuner.calculate_statistical_ranges(task_phase_data, 'percentile_95')
        ranges_90 = self.tuner.calculate_statistical_ranges(task_phase_data, 'percentile_90')
        ranges_conservative = self.tuner.calculate_statistical_ranges(task_phase_data, 'conservative')
        
        # Compare ranges for a specific variable
        task = 'level_walking'
        phase = 0
        var = 'hip_flexion_angle_ipsi'
        
        if (task in ranges_95 and phase in ranges_95[task] and 
            var in ranges_95[task][phase]):
            
            range_95 = ranges_95[task][phase][var]
            range_90 = ranges_90[task][phase][var]
            range_cons = ranges_conservative[task][phase][var]
            
            # 90% range should be narrower than 95% range
            width_95 = range_95['max'] - range_95['min']
            width_90 = range_90['max'] - range_90['min']
            
            if not (np.isnan(width_95) or np.isnan(width_90)):
                self.assertLessEqual(width_90, width_95, 
                                   "90% range should be narrower than 95% range")
            
            # Conservative should be widest
            width_cons = range_cons['max'] - range_cons['min']
            if not np.isnan(width_cons):
                self.assertGreaterEqual(width_cons, width_95, 
                                      "Conservative should be wider than 95% range")
    
    def test_report_generation(self):
        """Test statistics report generation."""
        task_phase_data = self.tuner.load_and_analyze_data()
        validation_ranges = self.tuner.calculate_statistical_ranges(task_phase_data, 'percentile_95')
        
        report = self.tuner.generate_statistics_report(
            task_phase_data, validation_ranges, 'percentile_95'
        )
        
        # Verify report content
        self.assertIsInstance(report, str)
        self.assertIn('Automated Fine-Tuning Report', report)
        self.assertIn('percentile_95', report)
        self.assertIn('level_walking', report)
        self.assertIn('decline_walking', report)
        self.assertIn('Task Summary', report)
        self.assertIn('Coverage Analysis', report)
    
    def test_integration_with_parser(self):
        """Test integration with ValidationExpectationsParser."""
        # Run statistical tuning without saving to avoid modifying production files
        results = self.tuner.run_statistical_tuning(
            method='percentile_95',
            save_ranges=False,  # Don't save to avoid modifying files
            save_report=False
        )
        
        # Verify results structure
        self.assertIsInstance(results, dict)
        self.assertTrue(results['success'])
        self.assertEqual(results['method'], 'percentile_95')
        self.assertIn('validation_ranges', results)
        self.assertIn('task_phase_data', results)
        self.assertIn('duration', results)
        self.assertIn('total_ranges', results)
        
        # Verify validation ranges structure
        validation_ranges = results['validation_ranges']
        self.assertIsInstance(validation_ranges, dict)
        
        # Test that validation ranges can be used with parser
        try:
            from lib.validation.validation_expectations_parser import ValidationExpectationsParser
            parser = ValidationExpectationsParser()
            
            # Create temporary file for testing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                temp_file = f.name
                f.write("""# Test Validation
                
## Validation Tables

## Joint Validation Range Summary
""")
            
            # Test writing with parser (should not crash)
            parser.write_validation_data(
                temp_file, 
                validation_ranges,
                dataset_name='test_data.parquet',
                method='percentile_95',
                mode='kinematic'
            )
            
            # Verify file was written
            with open(temp_file, 'r') as f:
                content = f.read()
            
            self.assertIn('level_walking', content)
            self.assertIn('95% Percentile', content)
            
            # Clean up
            os.unlink(temp_file)
            
        except ImportError:
            self.skipTest("ValidationExpectationsParser not available")
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test invalid statistical method
        task_phase_data = self.tuner.load_and_analyze_data()
        
        with self.assertRaises(ValueError):
            self.tuner.calculate_statistical_ranges(task_phase_data, 'invalid_method')
    
    def test_memory_efficiency(self):
        """Test that tuner handles data efficiently."""
        # This is a basic test - in practice would need larger datasets
        task_phase_data = self.tuner.load_and_analyze_data()
        
        # Verify data is stored as numpy arrays (memory efficient)
        for task_data in task_phase_data.values():
            for phase_data in task_data.values():
                for values in phase_data.values():
                    self.assertIsInstance(values, np.ndarray)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)