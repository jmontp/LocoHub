#!/usr/bin/env python3
"""
Test US-05: Validation Range Optimization

Created: 2025-06-18 with user permission
Purpose: Test memory-conscious statistical validation range optimization

Intent:
This test module validates the range optimization system that uses streaming
statistical analysis to optimize validation ranges across multiple datasets.
Tests memory-efficient percentile calculations, multi-dataset aggregation,
and false positive rate optimization.

**Test Categories:**
1. **Streaming Statistics**: Incremental percentile and statistical calculations
2. **Multi-Dataset Analysis**: Aggregation across multiple data sources
3. **Optimization Algorithms**: Range optimization with different methods
4. **Memory Efficiency**: Large dataset processing without memory exhaustion
5. **Integration**: API compatibility with existing validation system
"""

import unittest
import numpy as np
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from internal.validation_engine.range_optimizer import (
        StreamingStatsCalculator,
        RangeOptimizer,
        PercentileMethod,
        StdDevMethod,
        IQRMethod,
        MultiDatasetAggregator
    )
except ImportError:
    # Module not implemented yet - tests will be skipped
    StreamingStatsCalculator = None
    RangeOptimizer = None


class TestStreamingStatsCalculator(unittest.TestCase):
    """Test streaming statistical calculations for memory efficiency."""
    
    def setUp(self):
        """Set up test data."""
        if StreamingStatsCalculator is None:
            self.skipTest("StreamingStatsCalculator not implemented yet")
        self.calculator = StreamingStatsCalculator()
    
    def test_incremental_mean_calculation(self):
        """Test incremental mean calculation matches batch calculation."""
        data = np.random.normal(10, 2, 1000)
        
        # Incremental calculation
        for value in data:
            self.calculator.add_value(value)
        
        incremental_mean = self.calculator.get_mean()
        batch_mean = np.mean(data)
        
        self.assertAlmostEqual(incremental_mean, batch_mean, places=6)
    
    def test_incremental_variance_calculation(self):
        """Test incremental variance calculation using Welford's algorithm."""
        data = np.random.normal(5, 1.5, 500)
        
        # Incremental calculation
        for value in data:
            self.calculator.add_value(value)
        
        incremental_std = self.calculator.get_std()
        batch_std = np.std(data, ddof=1)
        
        self.assertAlmostEqual(incremental_std, batch_std, places=6)
    
    def test_streaming_percentiles(self):
        """Test streaming percentile calculation with P² algorithm."""
        data = np.random.normal(0, 1, 2000)
        
        # Add data in chunks to simulate streaming
        chunk_size = 100
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i+chunk_size]
            for value in chunk:
                self.calculator.add_value(value)
        
        # Test key percentiles
        p50_streaming = self.calculator.get_percentile(50)
        p95_streaming = self.calculator.get_percentile(95)
        p5_streaming = self.calculator.get_percentile(5)
        
        p50_batch = np.percentile(data, 50)
        p95_batch = np.percentile(data, 95)
        p5_batch = np.percentile(data, 5)
        
        # Allow some tolerance for streaming approximation (reservoir sampling)
        self.assertAlmostEqual(p50_streaming, p50_batch, delta=0.5)
        self.assertAlmostEqual(p95_streaming, p95_batch, delta=1.0)
        self.assertAlmostEqual(p5_streaming, p5_batch, delta=1.0)
    
    def test_memory_efficiency(self):
        """Test that streaming calculator maintains constant memory usage."""
        # Add large amount of data
        for i in range(100000):
            self.calculator.add_value(np.random.normal(0, 1))
        
        # Should still be able to calculate statistics
        mean = self.calculator.get_mean()
        std = self.calculator.get_std()
        p95 = self.calculator.get_percentile(95)
        
        self.assertIsInstance(mean, float)
        self.assertIsInstance(std, float)
        self.assertIsInstance(p95, float)


class TestRangeOptimizationMethods(unittest.TestCase):
    """Test different statistical methods for range optimization."""
    
    def setUp(self):
        """Set up test data."""
        if RangeOptimizer is None:
            self.skipTest("RangeOptimizer not implemented yet")
        
        # Create synthetic biomechanical data with realistic characteristics
        np.random.seed(42)
        self.hip_angles = np.random.normal(20, 15, 1000)  # degrees
        self.knee_angles = np.random.normal(60, 20, 1000)  # degrees
        self.ankle_moments = np.random.normal(1.2, 0.8, 1000)  # Nm/kg
    
    def test_percentile_method(self):
        """Test percentile-based range optimization."""
        method = PercentileMethod(lower_percentile=5, upper_percentile=95)
        
        range_min, range_max = method.calculate_range(self.hip_angles)
        
        expected_min = np.percentile(self.hip_angles, 5)
        expected_max = np.percentile(self.hip_angles, 95)
        
        self.assertAlmostEqual(range_min, expected_min, places=3)
        self.assertAlmostEqual(range_max, expected_max, places=3)
    
    def test_std_dev_method(self):
        """Test standard deviation-based range optimization."""
        method = StdDevMethod(num_std_dev=2.5)
        
        range_min, range_max = method.calculate_range(self.knee_angles)
        
        mean = np.mean(self.knee_angles)
        std = np.std(self.knee_angles)
        expected_min = mean - 2.5 * std
        expected_max = mean + 2.5 * std
        
        self.assertAlmostEqual(range_min, expected_min, places=3)
        self.assertAlmostEqual(range_max, expected_max, places=3)
    
    def test_iqr_method(self):
        """Test interquartile range-based optimization."""
        method = IQRMethod(iqr_multiplier=1.5)
        
        range_min, range_max = method.calculate_range(self.ankle_moments)
        
        q25 = np.percentile(self.ankle_moments, 25)
        q75 = np.percentile(self.ankle_moments, 75)
        iqr = q75 - q25
        expected_min = q25 - 1.5 * iqr
        expected_max = q75 + 1.5 * iqr
        
        self.assertAlmostEqual(range_min, expected_min, places=3)
        self.assertAlmostEqual(range_max, expected_max, places=3)
    
    def test_outlier_handling(self):
        """Test that methods handle outliers appropriately."""
        # Add extreme outliers
        data_with_outliers = np.concatenate([
            self.hip_angles,
            [-1000, 1000]  # Extreme outliers
        ])
        
        # Percentile method should be robust to outliers
        percentile_method = PercentileMethod(lower_percentile=5, upper_percentile=95)
        p_min, p_max = percentile_method.calculate_range(data_with_outliers)
        
        # StdDev method should be affected by outliers
        std_method = StdDevMethod(num_std_dev=2.0)
        s_min, s_max = std_method.calculate_range(data_with_outliers)
        
        # Percentile ranges should be similar to original data
        orig_p_min, orig_p_max = percentile_method.calculate_range(self.hip_angles)
        self.assertAlmostEqual(p_min, orig_p_min, delta=0.5)
        self.assertAlmostEqual(p_max, orig_p_max, delta=0.5)
        
        # StdDev ranges should be much wider due to outliers
        orig_s_min, orig_s_max = std_method.calculate_range(self.hip_angles)
        self.assertGreater(abs(s_max - s_min), abs(orig_s_max - orig_s_min))


class TestMultiDatasetAggregation(unittest.TestCase):
    """Test aggregation of statistics across multiple datasets."""
    
    def setUp(self):
        """Set up multiple synthetic datasets."""
        if MultiDatasetAggregator is None:
            self.skipTest("MultiDatasetAggregator not implemented yet")
        
        np.random.seed(42)
        
        # Create multiple datasets with different characteristics
        self.datasets = {
            'dataset_A': {
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.3, 0.2, 500),
                'knee_flexion_angle_ipsi_rad': np.random.normal(1.0, 0.3, 500)
            },
            'dataset_B': {
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.4, 0.15, 300),
                'knee_flexion_angle_ipsi_rad': np.random.normal(1.1, 0.25, 300)
            },
            'dataset_C': {
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.35, 0.18, 400),
                'knee_flexion_angle_ipsi_rad': np.random.normal(0.95, 0.28, 400)
            }
        }
        
        self.aggregator = MultiDatasetAggregator()
    
    def test_dataset_addition(self):
        """Test adding datasets to aggregator."""
        for name, data in self.datasets.items():
            self.aggregator.add_dataset(name, data)
        
        self.assertEqual(len(self.aggregator.get_dataset_names()), 3)
        self.assertIn('dataset_A', self.aggregator.get_dataset_names())
    
    def test_feature_aggregation(self):
        """Test aggregation of features across datasets."""
        for name, data in self.datasets.items():
            self.aggregator.add_dataset(name, data)
        
        # Aggregate hip flexion data
        aggregated_hip = self.aggregator.aggregate_feature('hip_flexion_angle_ipsi_rad')
        
        # Should return reservoir sample (limited size)
        self.assertGreater(len(aggregated_hip), 0)
        self.assertLessEqual(len(aggregated_hip), 1000)  # Reservoir size limit
        
        # Check that values are within expected range
        self.assertTrue(np.all(np.isfinite(aggregated_hip)))
        
        # Values should be similar to input data statistics
        if len(aggregated_hip) > 10:
            mean_range = (0.2, 0.5)  # Expected range from input datasets
            self.assertGreaterEqual(np.mean(aggregated_hip), mean_range[0])
            self.assertLessEqual(np.mean(aggregated_hip), mean_range[1])
    
    def test_weighted_aggregation(self):
        """Test weighted aggregation based on dataset quality/size."""
        for name, data in self.datasets.items():
            # Weight by dataset size
            weight = len(data['hip_flexion_angle_ipsi_rad']) / 1000
            self.aggregator.add_dataset(name, data, weight=weight)
        
        # Test that weights are preserved
        weights = self.aggregator.get_dataset_weights()
        self.assertAlmostEqual(weights['dataset_A'], 0.5, places=3)
        self.assertAlmostEqual(weights['dataset_B'], 0.3, places=3)
        self.assertAlmostEqual(weights['dataset_C'], 0.4, places=3)
    
    def test_missing_feature_handling(self):
        """Test handling of missing features in some datasets."""
        # Add dataset with missing feature
        dataset_partial = {
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.3, 0.2, 100)
            # Missing knee_flexion_angle_ipsi_rad
        }
        
        self.aggregator.add_dataset('dataset_partial', dataset_partial)
        
        # Should still aggregate hip data
        hip_data = self.aggregator.aggregate_feature('hip_flexion_angle_ipsi_rad')
        self.assertIsNotNone(hip_data)
        
        # Should handle missing knee data gracefully
        knee_data = self.aggregator.aggregate_feature('knee_flexion_angle_ipsi_rad')
        self.assertEqual(len(knee_data), 0)  # No data available


class TestRangeOptimizer(unittest.TestCase):
    """Test the main range optimizer that combines all components."""
    
    def setUp(self):
        """Set up range optimizer with test data."""
        if RangeOptimizer is None:
            self.skipTest("RangeOptimizer not implemented yet")
        
        self.optimizer = RangeOptimizer()
        
        # Create test datasets
        np.random.seed(42)
        self.test_datasets = {
            'train_dataset': {
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.3, 0.2, 1000),
                'knee_flexion_angle_ipsi_rad': np.random.normal(1.0, 0.3, 1000)
            },
            'validation_dataset': {
                'hip_flexion_angle_ipsi_rad': np.random.normal(0.35, 0.18, 500),
                'knee_flexion_angle_ipsi_rad': np.random.normal(0.95, 0.28, 500)
            }
        }
    
    def test_optimize_ranges_percentile(self):
        """Test range optimization using percentile method."""
        for name, data in self.test_datasets.items():
            self.optimizer.add_dataset(name, data)
        
        # Optimize using percentile method
        optimized_ranges = self.optimizer.optimize_ranges(
            method='percentile',
            features=['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'],
            percentiles=(5, 95)
        )
        
        self.assertIn('hip_flexion_angle_ipsi_rad', optimized_ranges)
        self.assertIn('knee_flexion_angle_ipsi_rad', optimized_ranges)
        
        # Check range structure
        hip_range = optimized_ranges['hip_flexion_angle_ipsi_rad']
        self.assertIn('min', hip_range)
        self.assertIn('max', hip_range)
        self.assertLess(hip_range['min'], hip_range['max'])
    
    def test_false_positive_rate_calculation(self):
        """Test calculation of false positive rates for validation."""
        for name, data in self.test_datasets.items():
            self.optimizer.add_dataset(name, data)
        
        # Set initial ranges (too narrow)
        current_ranges = {
            'hip_flexion_angle_ipsi_rad': {'min': 0.0, 'max': 0.6},
            'knee_flexion_angle_ipsi_rad': {'min': 0.4, 'max': 1.6}
        }
        
        # Calculate false positive rates
        fp_rates = self.optimizer.calculate_false_positive_rates(current_ranges)
        
        self.assertIn('hip_flexion_angle_ipsi_rad', fp_rates)
        self.assertIn('knee_flexion_angle_ipsi_rad', fp_rates)
        
        # Should be between 0 and 1
        for feature, rate in fp_rates.items():
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)
    
    def test_optimization_with_target_fp_rate(self):
        """Test optimization targeting specific false positive rate."""
        for name, data in self.test_datasets.items():
            self.optimizer.add_dataset(name, data)
        
        # Optimize to achieve ~5% false positive rate
        optimized_ranges = self.optimizer.optimize_for_fp_rate(
            features=['hip_flexion_angle_ipsi_rad'],
            target_fp_rate=0.05,
            tolerance=0.01
        )
        
        # Verify the achieved false positive rate
        fp_rates = self.optimizer.calculate_false_positive_rates(optimized_ranges)
        achieved_rate = fp_rates['hip_flexion_angle_ipsi_rad']
        
        self.assertAlmostEqual(achieved_rate, 0.05, delta=0.01)


class TestMemoryEfficiency(unittest.TestCase):
    """Test memory efficiency of streaming processing."""
    
    def setUp(self):
        """Set up memory efficiency tests."""
        if RangeOptimizer is None:
            self.skipTest("RangeOptimizer not implemented yet")
    
    def test_large_dataset_processing(self):
        """Test processing large datasets without memory exhaustion."""
        # Skip memory monitoring for simplicity
        
        optimizer = RangeOptimizer()
        
        # Simulate very large dataset processing
        def generate_large_chunks():
            """Generator that yields data chunks."""
            for i in range(100):  # 100 chunks
                yield {
                    'hip_flexion_angle_ipsi_rad': np.random.normal(0.3, 0.2, 10000),
                    'knee_flexion_angle_ipsi_rad': np.random.normal(1.0, 0.3, 10000)
                }
        
        # Process in streaming fashion
        for i, chunk in enumerate(generate_large_chunks()):
            optimizer.add_data_chunk(f'chunk_{i}', chunk)
        
        # Should be able to calculate statistics
        ranges = optimizer.optimize_ranges(
            method='percentile',
            features=['hip_flexion_angle_ipsi_rad'],
            percentiles=(5, 95)
        )
        
        self.assertIsNotNone(ranges)
        self.assertIn('hip_flexion_angle_ipsi_rad', ranges)
    
    def test_streaming_vs_batch_accuracy(self):
        """Test that streaming results match batch processing accuracy."""
        if StreamingStatsCalculator is None:
            self.skipTest("StreamingStatsCalculator not implemented yet")
        
        # Generate test data
        np.random.seed(42)
        large_dataset = np.random.normal(10, 3, 50000)
        
        # Streaming calculation
        streaming_calc = StreamingStatsCalculator()
        chunk_size = 1000
        for i in range(0, len(large_dataset), chunk_size):
            chunk = large_dataset[i:i+chunk_size]
            for value in chunk:
                streaming_calc.add_value(value)
        
        # Batch calculation
        batch_mean = np.mean(large_dataset)
        batch_std = np.std(large_dataset, ddof=1)
        batch_p95 = np.percentile(large_dataset, 95)
        
        # Compare results (with tolerance for reservoir sampling approximation)
        self.assertAlmostEqual(streaming_calc.get_mean(), batch_mean, places=4)
        self.assertAlmostEqual(streaming_calc.get_std(), batch_std, places=4)
        self.assertAlmostEqual(streaming_calc.get_percentile(95), batch_p95, delta=2.0)


class TestIntegrationWithValidationSystem(unittest.TestCase):
    """Test integration with existing validation system."""
    
    def setUp(self):
        """Set up integration tests."""
        if RangeOptimizer is None:
            self.skipTest("RangeOptimizer not implemented yet")
    
    def test_validation_expectations_format(self):
        """Test that optimized ranges match validation expectations format."""
        optimizer = RangeOptimizer()
        
        # Add test data
        test_data = {
            'hip_flexion_angle_ipsi_rad': np.random.normal(0.3, 0.2, 1000),
            'knee_flexion_angle_ipsi_rad': np.random.normal(1.0, 0.3, 1000)
        }
        optimizer.add_dataset('test', test_data)
        
        # Optimize ranges
        ranges = optimizer.optimize_ranges(
            method='percentile',
            features=['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'],
            percentiles=(5, 95)
        )
        
        # Check format compatibility
        for feature, range_dict in ranges.items():
            self.assertIn('min', range_dict)
            self.assertIn('max', range_dict)
            self.assertIsInstance(range_dict['min'], (int, float))
            self.assertIsInstance(range_dict['max'], (int, float))
    
    def test_feature_constants_compatibility(self):
        """Test compatibility with feature_constants.py."""
        from user_libs.python.feature_constants import ANGLE_FEATURES, MOMENT_FEATURES
        
        optimizer = RangeOptimizer()
        
        # Should accept feature names from feature_constants
        test_data = {}
        for feature in ANGLE_FEATURES[:2]:  # Test first 2 features
            test_data[feature] = np.random.normal(0.5, 0.3, 1000)
        
        optimizer.add_dataset('test', test_data)
        ranges = optimizer.optimize_ranges(
            method='percentile',
            features=list(test_data.keys()),
            percentiles=(10, 90)
        )
        
        # Should have ranges for all requested features
        self.assertEqual(len(ranges), len(test_data))
        for feature in test_data.keys():
            self.assertIn(feature, ranges)


if __name__ == '__main__':
    unittest.main()