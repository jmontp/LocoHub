#!/usr/bin/env python3
"""
Validation Range Optimizer

Created: 2025-06-18 with user permission
Purpose: Memory-conscious statistical validation range optimization

Intent:
This module provides streaming statistical analysis to optimize validation ranges
across multiple datasets without loading full datasets into memory. Uses incremental
statistics and efficient percentile approximation for memory-conscious processing.

**Core Components:**
1. **StreamingStatsCalculator**: Incremental mean, variance, and percentile calculation
2. **RangeOptimizationMethods**: Different statistical approaches (percentile, std dev, IQR)
3. **MultiDatasetAggregator**: Memory-efficient multi-dataset statistics
4. **RangeOptimizer**: Main interface for validation range optimization
5. **False Positive Rate Analysis**: Optimization targeting specific error rates

**Memory Efficiency Features:**
- Welford's algorithm for incremental variance calculation
- P² algorithm for streaming percentile approximation
- Chunked data processing to avoid memory exhaustion
- Efficient multi-dataset aggregation without full data storage

Usage:
    optimizer = RangeOptimizer()
    optimizer.add_dataset('dataset_name', data_dict)
    ranges = optimizer.optimize_ranges(method='percentile', features=['hip_flexion_angle_ipsi_rad'])
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Generator, Union
from abc import ABC, abstractmethod
import math
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamingStatsCalculator:
    """
    Memory-efficient streaming statistical calculator.
    
    Uses Welford's algorithm for variance and simple quantile tracking
    to calculate statistics incrementally without storing all data points.
    """
    
    def __init__(self, reservoir_size: int = 1000):
        """Initialize streaming calculator.
        
        Args:
            reservoir_size: Size of sample reservoir for percentile estimation
        """
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0  # Sum of squares of differences from mean
        
        # Reservoir sampling for percentile estimation
        self.reservoir_size = reservoir_size
        self.reservoir = []
        self.reservoir_full = False
        
    def add_value(self, value: float):
        """
        Add a value to the streaming calculation.
        
        Args:
            value: New data point to include in calculations
        """
        if not isinstance(value, (int, float)) or np.isnan(value):
            return  # Skip invalid values
        
        # Welford's algorithm for mean and variance
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2
        
        # Reservoir sampling for percentiles
        if len(self.reservoir) < self.reservoir_size:
            self.reservoir.append(value)
        else:
            if not self.reservoir_full:
                self.reservoir_full = True
            # Replace random element in reservoir
            import random
            j = random.randint(0, self.count - 1)
            if j < self.reservoir_size:
                self.reservoir[j] = value
    
    def get_mean(self) -> float:
        """Get current mean."""
        return self.mean
    
    def get_variance(self) -> float:
        """Get current variance (sample variance with Bessel's correction)."""
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)
    
    def get_std(self) -> float:
        """Get current standard deviation."""
        return math.sqrt(self.get_variance())
    
    def get_count(self) -> int:
        """Get number of observations."""
        return self.count
    
    def get_percentile(self, percentile: float) -> float:
        """
        Get approximated percentile using reservoir sampling.
        
        Args:
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Approximated percentile value
        """
        if len(self.reservoir) == 0:
            return 0.0
        
        # Use reservoir sample to estimate percentile
        sorted_reservoir = sorted(self.reservoir)
        index = (percentile / 100.0) * (len(sorted_reservoir) - 1)
        
        if index == int(index):
            return sorted_reservoir[int(index)]
        else:
            # Linear interpolation
            lower_idx = int(index)
            upper_idx = min(lower_idx + 1, len(sorted_reservoir) - 1)
            weight = index - lower_idx
            
            return (1 - weight) * sorted_reservoir[lower_idx] + weight * sorted_reservoir[upper_idx]




class RangeOptimizationMethod(ABC):
    """Abstract base class for range optimization methods."""
    
    @abstractmethod
    def calculate_range(self, data: Union[np.ndarray, StreamingStatsCalculator]) -> Tuple[float, float]:
        """
        Calculate optimal range for given data.
        
        Args:
            data: Either numpy array or streaming calculator
            
        Returns:
            Tuple of (min_value, max_value)
        """
        pass
    
    @abstractmethod
    def get_method_name(self) -> str:
        """Get method name for reporting."""
        pass


class PercentileMethod(RangeOptimizationMethod):
    """Percentile-based range optimization."""
    
    def __init__(self, lower_percentile: float = 5, upper_percentile: float = 95):
        """
        Initialize percentile method.
        
        Args:
            lower_percentile: Lower percentile boundary (0-100)
            upper_percentile: Upper percentile boundary (0-100)
        """
        self.lower_percentile = lower_percentile
        self.upper_percentile = upper_percentile
    
    def calculate_range(self, data: Union[np.ndarray, StreamingStatsCalculator]) -> Tuple[float, float]:
        """Calculate percentile-based range."""
        if isinstance(data, StreamingStatsCalculator):
            range_min = data.get_percentile(self.lower_percentile)
            range_max = data.get_percentile(self.upper_percentile)
        else:
            range_min = np.percentile(data, self.lower_percentile)
            range_max = np.percentile(data, self.upper_percentile)
        
        return range_min, range_max
    
    def get_method_name(self) -> str:
        """Get method name."""
        return f"percentile_{self.lower_percentile}_{self.upper_percentile}"


class StdDevMethod(RangeOptimizationMethod):
    """Standard deviation-based range optimization."""
    
    def __init__(self, num_std_dev: float = 2.5):
        """
        Initialize standard deviation method.
        
        Args:
            num_std_dev: Number of standard deviations for range
        """
        self.num_std_dev = num_std_dev
    
    def calculate_range(self, data: Union[np.ndarray, StreamingStatsCalculator]) -> Tuple[float, float]:
        """Calculate standard deviation-based range."""
        if isinstance(data, StreamingStatsCalculator):
            mean = data.get_mean()
            std = data.get_std()
        else:
            mean = np.mean(data)
            std = np.std(data)
        
        range_min = mean - self.num_std_dev * std
        range_max = mean + self.num_std_dev * std
        
        return range_min, range_max
    
    def get_method_name(self) -> str:
        """Get method name."""
        return f"std_dev_{self.num_std_dev}"


class IQRMethod(RangeOptimizationMethod):
    """Interquartile range-based optimization."""
    
    def __init__(self, iqr_multiplier: float = 1.5):
        """
        Initialize IQR method.
        
        Args:
            iqr_multiplier: Multiplier for IQR-based range
        """
        self.iqr_multiplier = iqr_multiplier
    
    def calculate_range(self, data: Union[np.ndarray, StreamingStatsCalculator]) -> Tuple[float, float]:
        """Calculate IQR-based range."""
        if isinstance(data, StreamingStatsCalculator):
            q25 = data.get_percentile(25)
            q75 = data.get_percentile(75)
        else:
            q25 = np.percentile(data, 25)
            q75 = np.percentile(data, 75)
        
        iqr = q75 - q25
        range_min = q25 - self.iqr_multiplier * iqr
        range_max = q75 + self.iqr_multiplier * iqr
        
        return range_min, range_max
    
    def get_method_name(self) -> str:
        """Get method name."""
        return f"iqr_{self.iqr_multiplier}"


class MultiDatasetAggregator:
    """
    Memory-efficient aggregator for multiple datasets.
    
    Combines data from multiple datasets without storing all values,
    using streaming statistics for efficient processing.
    """
    
    def __init__(self):
        """Initialize aggregator."""
        self.datasets = {}
        self.dataset_weights = {}
        self.feature_calculators = defaultdict(StreamingStatsCalculator)
    
    def add_dataset(self, name: str, data: Dict[str, np.ndarray], weight: float = 1.0):
        """
        Add dataset to aggregator.
        
        Args:
            name: Dataset identifier
            data: Dictionary mapping feature names to data arrays
            weight: Weight for this dataset in aggregation
        """
        self.datasets[name] = list(data.keys())  # Store feature names only
        self.dataset_weights[name] = weight
        
        # Add data to streaming calculators
        for feature, values in data.items():
            calculator = self.feature_calculators[feature]
            for value in values:
                if isinstance(value, (int, float)) and not np.isnan(value):
                    calculator.add_value(value)
        
        logger.info(f"Added dataset '{name}' with {len(data)} features and weight {weight}")
    
    def add_data_chunk(self, dataset_name: str, chunk: Dict[str, np.ndarray]):
        """
        Add data chunk for streaming processing.
        
        Args:
            dataset_name: Dataset identifier
            chunk: Data chunk to process
        """
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = list(chunk.keys())
            self.dataset_weights[dataset_name] = 1.0
        
        # Process chunk
        for feature, values in chunk.items():
            calculator = self.feature_calculators[feature]
            for value in values:
                if isinstance(value, (int, float)) and not np.isnan(value):
                    calculator.add_value(value)
    
    def get_dataset_names(self) -> List[str]:
        """Get list of dataset names."""
        return list(self.datasets.keys())
    
    def get_dataset_weights(self) -> Dict[str, float]:
        """Get dataset weights."""
        return self.dataset_weights.copy()
    
    def get_feature_names(self) -> List[str]:
        """Get all feature names across datasets."""
        return list(self.feature_calculators.keys())
    
    def aggregate_feature(self, feature_name: str) -> np.ndarray:
        """
        Get aggregated feature data from reservoir samples.
        
        Args:
            feature_name: Feature to aggregate
            
        Returns:
            Array of reservoir samples for the feature
        """
        if feature_name not in self.feature_calculators:
            return np.array([])
        
        calculator = self.feature_calculators[feature_name]
        return np.array(calculator.reservoir) if calculator.reservoir else np.array([])
    
    def get_feature_calculator(self, feature_name: str) -> Optional[StreamingStatsCalculator]:
        """
        Get streaming calculator for feature.
        
        Args:
            feature_name: Feature name
            
        Returns:
            StreamingStatsCalculator or None if feature not found
        """
        return self.feature_calculators.get(feature_name)


class RangeOptimizer:
    """
    Main range optimizer that combines all components.
    
    Provides high-level interface for validation range optimization
    using streaming statistical analysis across multiple datasets.
    """
    
    def __init__(self):
        """Initialize range optimizer."""
        self.aggregator = MultiDatasetAggregator()
        self.optimization_methods = {
            'percentile': PercentileMethod,
            'std_dev': StdDevMethod,
            'iqr': IQRMethod
        }
    
    def add_dataset(self, name: str, data: Dict[str, np.ndarray], weight: float = 1.0):
        """
        Add dataset for optimization.
        
        Args:
            name: Dataset identifier
            data: Feature data dictionary
            weight: Dataset weight
        """
        self.aggregator.add_dataset(name, data, weight)
    
    def add_data_chunk(self, dataset_name: str, chunk: Dict[str, np.ndarray]):
        """
        Add data chunk for streaming processing.
        
        Args:
            dataset_name: Dataset identifier
            chunk: Data chunk
        """
        self.aggregator.add_data_chunk(dataset_name, chunk)
    
    def optimize_ranges(self, 
                       method: str,
                       features: List[str],
                       **method_kwargs) -> Dict[str, Dict[str, float]]:
        """
        Optimize validation ranges for specified features.
        
        Args:
            method: Optimization method ('percentile', 'std_dev', 'iqr')
            features: List of feature names to optimize
            **method_kwargs: Method-specific parameters
            
        Returns:
            Dictionary mapping feature names to {'min': value, 'max': value}
        """
        if method not in self.optimization_methods:
            raise ValueError(f"Unknown method: {method}. Available: {list(self.optimization_methods.keys())}")
        
        # Create optimization method instance
        method_class = self.optimization_methods[method]
        
        if method == 'percentile':
            lower = method_kwargs.get('percentiles', (5, 95))[0]
            upper = method_kwargs.get('percentiles', (5, 95))[1]
            optimizer = method_class(lower, upper)
        elif method == 'std_dev':
            num_std = method_kwargs.get('num_std_dev', 2.5)
            optimizer = method_class(num_std)
        elif method == 'iqr':
            multiplier = method_kwargs.get('iqr_multiplier', 1.5)
            optimizer = method_class(multiplier)
        else:
            optimizer = method_class()
        
        # Optimize ranges
        optimized_ranges = {}
        for feature in features:
            calculator = self.aggregator.get_feature_calculator(feature)
            if calculator is None or calculator.get_count() == 0:
                logger.warning(f"No data available for feature: {feature}")
                continue
            
            range_min, range_max = optimizer.calculate_range(calculator)
            optimized_ranges[feature] = {
                'min': range_min,
                'max': range_max
            }
            
            logger.info(f"Optimized {feature}: [{range_min:.3f}, {range_max:.3f}] "
                       f"using {optimizer.get_method_name()} (n={calculator.get_count()})")
        
        return optimized_ranges
    
    def calculate_false_positive_rates(self, 
                                     current_ranges: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """
        Calculate false positive rates for current validation ranges.
        
        Args:
            current_ranges: Current validation ranges
            
        Returns:
            Dictionary mapping feature names to false positive rates
        """
        fp_rates = {}
        
        for feature, range_dict in current_ranges.items():
            calculator = self.aggregator.get_feature_calculator(feature)
            if calculator is None or calculator.get_count() == 0:
                fp_rates[feature] = 0.0
                continue
            
            range_min = range_dict['min']
            range_max = range_dict['max']
            
            # Estimate false positive rate using percentiles
            # This is an approximation since we're using streaming stats
            try:
                # Get percentiles corresponding to range boundaries
                if range_min != float('-inf'):
                    # Estimate what percentile the min range corresponds to
                    p_min = self._estimate_percentile_for_value(calculator, range_min)
                else:
                    p_min = 0.0
                
                if range_max != float('inf'):
                    # Estimate what percentile the max range corresponds to
                    p_max = self._estimate_percentile_for_value(calculator, range_max)
                else:
                    p_max = 100.0
                
                # False positive rate is data outside the range
                fp_rate = (p_min + (100 - p_max)) / 100.0
                fp_rates[feature] = max(0.0, min(1.0, fp_rate))
                
            except Exception as e:
                logger.warning(f"Could not calculate FP rate for {feature}: {e}")
                fp_rates[feature] = 0.0
        
        return fp_rates
    
    def _estimate_percentile_for_value(self, calculator: StreamingStatsCalculator, value: float) -> float:
        """
        Estimate what percentile a value corresponds to.
        
        This is a rough approximation using available percentile estimates.
        """
        # Test some standard percentiles to bracket the value
        test_percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        
        for p in test_percentiles:
            p_value = calculator.get_percentile(p)
            if value <= p_value:
                return p
        
        return 99.0  # Value is above 99th percentile
    
    def optimize_for_fp_rate(self, 
                            features: List[str], 
                            target_fp_rate: float,
                            tolerance: float = 0.01,
                            max_iterations: int = 10) -> Dict[str, Dict[str, float]]:
        """
        Optimize ranges to achieve target false positive rate.
        
        Args:
            features: Features to optimize
            target_fp_rate: Target false positive rate (0.0 to 1.0)
            tolerance: Acceptable tolerance for target rate
            max_iterations: Maximum optimization iterations
            
        Returns:
            Optimized ranges achieving target false positive rate
        """
        optimized_ranges = {}
        
        for feature in features:
            calculator = self.aggregator.get_feature_calculator(feature)
            if calculator is None or calculator.get_count() == 0:
                continue
            
            # Binary search for appropriate percentiles
            lower_bound = 0.1
            upper_bound = 49.9  # Leave symmetric room
            
            best_range = None
            best_error = float('inf')
            
            for iteration in range(max_iterations):
                # Current percentiles
                lower_p = lower_bound
                upper_p = 100 - lower_bound
                
                # Calculate range
                range_min = calculator.get_percentile(lower_p)
                range_max = calculator.get_percentile(upper_p)
                
                # Calculate achieved FP rate
                current_fp_rate = (lower_p + (100 - upper_p)) / 100.0
                error = abs(current_fp_rate - target_fp_rate)
                
                if error < best_error:
                    best_error = error
                    best_range = {'min': range_min, 'max': range_max}
                
                if error <= tolerance:
                    break
                
                # Adjust bounds
                if current_fp_rate > target_fp_rate:
                    # Need wider range (smaller percentiles)
                    upper_bound = lower_bound
                    lower_bound = lower_bound / 2
                else:
                    # Need narrower range (larger percentiles)
                    lower_bound = (lower_bound + upper_bound) / 2
            
            if best_range is not None:
                optimized_ranges[feature] = best_range
                logger.info(f"Optimized {feature} for FP rate {target_fp_rate:.3f}: "
                           f"[{best_range['min']:.3f}, {best_range['max']:.3f}] "
                           f"(error: {best_error:.4f})")
        
        return optimized_ranges
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        Get summary of available data for optimization.
        
        Returns:
            Summary dictionary with dataset and feature information
        """
        summary = {
            'datasets': self.aggregator.get_dataset_names(),
            'dataset_weights': self.aggregator.get_dataset_weights(),
            'features': {},
            'total_observations': 0
        }
        
        for feature in self.aggregator.get_feature_names():
            calculator = self.aggregator.get_feature_calculator(feature)
            if calculator:
                feature_info = {
                    'count': calculator.get_count(),
                    'mean': calculator.get_mean(),
                    'std': calculator.get_std(),
                    'p5': calculator.get_percentile(5),
                    'p95': calculator.get_percentile(95)
                }
                summary['features'][feature] = feature_info
                summary['total_observations'] += calculator.get_count()
        
        return summary