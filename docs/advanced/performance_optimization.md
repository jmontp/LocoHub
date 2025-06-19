# Performance Optimization Guide

**Complete guide for optimizing locomotion data processing performance**

## Overview

This guide provides comprehensive strategies for optimizing performance when working with large locomotion datasets, including memory management, parallel processing, caching strategies, and algorithm optimization.

## Memory Management

### Efficient Data Loading

```python
from lib.core.locomotion_analysis import LocomotionData
import numpy as np
import pandas as pd
from pathlib import Path
import psutil
import gc
import warnings

class MemoryEfficientLoader:
    """Memory-efficient data loading for large locomotion datasets."""
    
    def __init__(self, chunk_size=1000, memory_limit_gb=4):
        self.chunk_size = chunk_size
        self.memory_limit_bytes = memory_limit_gb * 1024**3
        
    def check_memory_usage(self):
        """Check current memory usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024**2,
            'vms_mb': memory_info.vms / 1024**2,
            'percent': process.memory_percent()
        }
    
    def load_dataset_chunked(self, dataset_path, subjects=None):
        """Load dataset in chunks to manage memory."""
        
        # Read file info first
        file_path = Path(dataset_path)
        if file_path.suffix == '.parquet':
            # Get parquet metadata
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(dataset_path)
            total_rows = parquet_file.metadata.num_rows
            
            print(f"Dataset info: {total_rows} rows, {parquet_file.metadata.num_columns} columns")
            
            # Calculate optimal chunk size based on memory
            if total_rows > self.chunk_size:
                n_chunks = int(np.ceil(total_rows / self.chunk_size))
                print(f"Processing in {n_chunks} chunks of {self.chunk_size} rows")
                
                for chunk_idx in range(n_chunks):
                    start_row = chunk_idx * self.chunk_size
                    end_row = min(start_row + self.chunk_size, total_rows)
                    
                    # Read chunk
                    chunk_df = pd.read_parquet(
                        dataset_path,
                        engine='pyarrow',
                        use_pandas_metadata=True
                    ).iloc[start_row:end_row]
                    
                    # Filter subjects if specified
                    if subjects is not None:
                        chunk_df = chunk_df[chunk_df['subject'].isin(subjects)]
                    
                    # Yield chunk for processing
                    yield chunk_df
                    
                    # Memory cleanup
                    del chunk_df
                    gc.collect()
                    
                    # Check memory usage
                    memory_info = self.check_memory_usage()
                    if memory_info['rss_mb'] > (self.memory_limit_bytes / 1024**2):
                        warnings.warn(f"Memory usage high: {memory_info['rss_mb']:.1f} MB")
            else:
                # Load entire dataset if small enough
                df = pd.read_parquet(dataset_path)
                if subjects is not None:
                    df = df[df['subject'].isin(subjects)]
                yield df
    
    def process_dataset_streaming(self, dataset_path, processing_func, subjects=None, **kwargs):
        """Process large dataset in streaming fashion."""
        
        results = []
        total_processed = 0
        
        for chunk_idx, chunk_df in enumerate(self.load_dataset_chunked(dataset_path, subjects)):
            print(f"Processing chunk {chunk_idx + 1}...")
            
            # Process chunk
            try:
                chunk_result = processing_func(chunk_df, **kwargs)
                results.append(chunk_result)
                total_processed += len(chunk_df)
                
                print(f"  Processed {len(chunk_df)} rows (total: {total_processed})")
                
            except Exception as e:
                print(f"  Error processing chunk {chunk_idx + 1}: {e}")
                continue
            
            # Memory monitoring
            memory_info = self.check_memory_usage()
            print(f"  Memory usage: {memory_info['rss_mb']:.1f} MB ({memory_info['percent']:.1f}%)")
        
        return results

# Example processing function
def calculate_summary_stats_chunk(chunk_df):
    """Calculate summary statistics for a data chunk."""
    
    # Identify biomechanical features
    feature_cols = [col for col in chunk_df.columns 
                   if any(keyword in col for keyword in ['angle', 'moment', 'velocity'])]
    
    if not feature_cols:
        return pd.DataFrame()
    
    # Calculate statistics
    stats = chunk_df.groupby(['subject', 'task'])[feature_cols].agg([
        'mean', 'std', 'min', 'max', 'count'
    ]).reset_index()
    
    return stats

# Usage
loader = MemoryEfficientLoader(chunk_size=5000, memory_limit_gb=8)

# Process large dataset in chunks
results = loader.process_dataset_streaming(
    'very_large_dataset_phase.parquet',
    calculate_summary_stats_chunk,
    subjects=['SUB001', 'SUB002', 'SUB003']
)

# Combine results
if results:
    combined_stats = pd.concat(results, ignore_index=True)
    print(f"Final results: {len(combined_stats)} rows")
```

### Memory-Mapped Arrays

```python
import numpy as np
from pathlib import Path

class MemoryMappedGaitData:
    """Use memory mapping for very large gait datasets."""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def convert_to_memmap(self, loco_data, subjects, tasks, dtype=np.float32):
        """Convert LocomotionData to memory-mapped arrays."""
        
        memmap_files = {}
        
        for subject in subjects:
            for task in tasks:
                # Get 3D data
                data_3d, features = loco_data.get_cycles(subject, task)
                if data_3d is None:
                    continue
                
                # Convert to specified dtype to save memory
                data_3d = data_3d.astype(dtype)
                
                # Create memory-mapped file
                memmap_path = self.data_dir / f"{subject}_{task}_data.npy"
                
                # Save as memory-mapped array
                memmap_array = np.memmap(
                    memmap_path, 
                    dtype=dtype, 
                    mode='w+', 
                    shape=data_3d.shape
                )
                memmap_array[:] = data_3d[:]
                del memmap_array  # Close file
                
                # Store metadata
                metadata = {
                    'shape': data_3d.shape,
                    'dtype': str(dtype),
                    'features': features
                }
                
                metadata_path = self.data_dir / f"{subject}_{task}_metadata.json"
                with open(metadata_path, 'w') as f:
                    import json
                    json.dump(metadata, f)
                
                memmap_files[f"{subject}_{task}"] = {
                    'data_path': memmap_path,
                    'metadata_path': metadata_path,
                    'shape': data_3d.shape,
                    'features': features
                }
        
        return memmap_files
    
    def load_memmap_data(self, subject, task, dtype=np.float32):
        """Load memory-mapped data for analysis."""
        
        data_path = self.data_dir / f"{subject}_{task}_data.npy"
        metadata_path = self.data_dir / f"{subject}_{task}_metadata.json"
        
        if not data_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(f"Memory-mapped data not found for {subject}_{task}")
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            import json
            metadata = json.load(f)
        
        # Load memory-mapped array
        data_array = np.memmap(
            data_path,
            dtype=dtype,
            mode='r',
            shape=tuple(metadata['shape'])
        )
        
        return data_array, metadata['features']
    
    def analyze_memmap_data(self, subject, task, analysis_func):
        """Analyze memory-mapped data without loading into RAM."""
        
        data_array, features = self.load_memmap_data(subject, task)
        
        # Process data in chunks to avoid loading everything
        n_cycles = data_array.shape[0]
        chunk_size = min(100, n_cycles)  # Process 100 cycles at a time
        
        results = []
        
        for start_idx in range(0, n_cycles, chunk_size):
            end_idx = min(start_idx + chunk_size, n_cycles)
            
            # Load chunk into memory
            chunk_data = np.array(data_array[start_idx:end_idx, :, :])
            
            # Analyze chunk
            chunk_result = analysis_func(chunk_data, features)
            results.append(chunk_result)
            
            # Clean up
            del chunk_data
        
        return results

# Usage
loco = LocomotionData('large_dataset_phase.parquet')
memmap_handler = MemoryMappedGaitData('memmap_data/')

# Convert to memory-mapped format
subjects = loco.get_subjects()[:10]  # First 10 subjects
tasks = ['normal_walk', 'fast_walk']

memmap_files = memmap_handler.convert_to_memmap(loco, subjects, tasks, dtype=np.float32)
print(f"Created {len(memmap_files)} memory-mapped files")

# Analyze without loading into RAM
def calculate_mean_pattern(chunk_data, features):
    """Calculate mean gait pattern for a chunk."""
    return np.mean(chunk_data, axis=0)  # Mean across cycles

results = memmap_handler.analyze_memmap_data('SUB01', 'normal_walk', calculate_mean_pattern)
overall_mean = np.mean(results, axis=0)  # Combine chunk results
```

## Parallel Processing

### Multiprocessing for Gait Analysis

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import time
from functools import partial

class ParallelGaitAnalyzer:
    """Parallel processing for large-scale gait analysis."""
    
    def __init__(self, n_processes=None):
        self.n_processes = n_processes or mp.cpu_count()
        
    def analyze_subject_task_parallel(self, dataset_path, analysis_func, 
                                    subjects=None, tasks=None, use_threads=False):
        """Analyze subject-task combinations in parallel."""
        
        # Load data once
        loco = LocomotionData(dataset_path)
        
        if subjects is None:
            subjects = loco.get_subjects()
        if tasks is None:
            tasks = loco.get_tasks()
        
        # Create work items
        work_items = []
        for subject in subjects:
            for task in tasks:
                work_items.append((subject, task, dataset_path))
        
        print(f"Processing {len(work_items)} subject-task combinations using {self.n_processes} processes")
        
        # Choose executor type
        executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
        
        # Process in parallel
        results = []
        start_time = time.time()
        
        with executor_class(max_workers=self.n_processes) as executor:
            # Submit all jobs
            future_to_item = {
                executor.submit(analysis_func, item[0], item[1], item[2]): item 
                for item in work_items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    result['subject'] = item[0]
                    result['task'] = item[1]
                    results.append(result)
                    
                    if len(results) % 10 == 0:
                        elapsed = time.time() - start_time
                        remaining = len(work_items) - len(results)
                        eta = (elapsed / len(results)) * remaining
                        print(f"Completed {len(results)}/{len(work_items)} ({elapsed:.1f}s elapsed, {eta:.1f}s remaining)")
                        
                except Exception as e:
                    print(f"Error processing {item[0]}-{item[1]}: {e}")
        
        total_time = time.time() - start_time
        print(f"Parallel processing completed in {total_time:.1f}s")
        
        return results
    
    def batch_validate_cycles(self, dataset_path, subjects=None, batch_size=50):
        """Validate gait cycles in parallel batches."""
        
        def validate_batch(subject_batch, dataset_path):
            """Validate a batch of subjects."""
            loco = LocomotionData(dataset_path)
            results = []
            
            for subject in subject_batch:
                tasks = loco.get_tasks()
                for task in tasks:
                    try:
                        valid_mask = loco.validate_cycles(subject, task)
                        if len(valid_mask) > 0:
                            results.append({
                                'subject': subject,
                                'task': task,
                                'total_cycles': len(valid_mask),
                                'valid_cycles': valid_mask.sum(),
                                'validity_rate': valid_mask.mean()
                            })
                    except Exception as e:
                        print(f"Validation error for {subject}-{task}: {e}")
            
            return results
        
        # Load data to get subjects
        loco = LocomotionData(dataset_path)
        if subjects is None:
            subjects = loco.get_subjects()
        
        # Create batches
        subject_batches = [subjects[i:i+batch_size] for i in range(0, len(subjects), batch_size)]
        
        print(f"Validating {len(subjects)} subjects in {len(subject_batches)} batches")
        
        # Process batches in parallel
        all_results = []
        with ProcessPoolExecutor(max_workers=self.n_processes) as executor:
            futures = [
                executor.submit(validate_batch, batch, dataset_path) 
                for batch in subject_batches
            ]
            
            for future in as_completed(futures):
                batch_results = future.result()
                all_results.extend(batch_results)
        
        return pd.DataFrame(all_results)

# Analysis functions for parallel processing
def analyze_gait_summary(subject, task, dataset_path):
    """Analyze gait summary statistics for a subject-task."""
    try:
        loco = LocomotionData(dataset_path)
        
        # Get summary statistics
        stats = loco.get_summary_statistics(subject, task)
        rom_data = loco.calculate_rom(subject, task, by_cycle=False)
        valid_mask = loco.validate_cycles(subject, task)
        
        result = {
            'n_cycles': len(valid_mask) if len(valid_mask) > 0 else 0,
            'valid_cycles': valid_mask.sum() if len(valid_mask) > 0 else 0,
            'validity_rate': valid_mask.mean() if len(valid_mask) > 0 else 0,
            'rom_knee': np.degrees(rom_data.get('knee_flexion_angle_ipsi_rad', 0)),
            'rom_hip': np.degrees(rom_data.get('hip_flexion_angle_ipsi_rad', 0)),
            'rom_ankle': np.degrees(rom_data.get('ankle_flexion_angle_ipsi_rad', 0))
        }
        
        return result
        
    except Exception as e:
        return {'error': str(e)}

def extract_gait_features_parallel(subject, task, dataset_path):
    """Extract comprehensive gait features in parallel."""
    try:
        loco = LocomotionData(dataset_path)
        data_3d, features = loco.get_cycles(subject, task)
        
        if data_3d is None:
            return {'error': 'No data available'}
        
        # Extract multiple feature types
        feature_dict = {}
        
        # Statistical features
        for i, feature in enumerate(features):
            signal_data = data_3d[:, :, i]
            
            # Per-cycle statistics
            cycle_means = np.mean(signal_data, axis=1)
            cycle_stds = np.std(signal_data, axis=1)
            cycle_ranges = np.max(signal_data, axis=1) - np.min(signal_data, axis=1)
            
            feature_dict[f'{feature}_mean'] = np.mean(cycle_means)
            feature_dict[f'{feature}_std'] = np.mean(cycle_stds)
            feature_dict[f'{feature}_cv'] = np.std(cycle_means) / np.mean(cycle_means) if np.mean(cycle_means) != 0 else 0
            feature_dict[f'{feature}_range'] = np.mean(cycle_ranges)
        
        return feature_dict
        
    except Exception as e:
        return {'error': str(e)}

# Usage
analyzer = ParallelGaitAnalyzer(n_processes=8)

# Parallel gait summary analysis
summary_results = analyzer.analyze_subject_task_parallel(
    'large_dataset_phase.parquet',
    analyze_gait_summary,
    subjects=None,  # All subjects
    tasks=['normal_walk', 'fast_walk']
)

summary_df = pd.DataFrame(summary_results)
print(f"Processed {len(summary_df)} subject-task combinations")
print(f"Average validity rate: {summary_df['validity_rate'].mean():.2f}")

# Parallel validation
validation_results = analyzer.batch_validate_cycles(
    'large_dataset_phase.parquet',
    batch_size=25
)

print(f"Validation completed for {len(validation_results)} combinations")
```

### GPU Acceleration with CuPy

```python
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("CuPy not available - GPU acceleration disabled")

class GPUGaitAnalyzer:
    """GPU-accelerated gait analysis using CuPy."""
    
    def __init__(self):
        if not GPU_AVAILABLE:
            raise ImportError("CuPy required for GPU acceleration")
        
        # Check GPU availability
        try:
            cp.cuda.Device(0).use()
            self.device_info = cp.cuda.runtime.getDeviceProperties(0)
            print(f"GPU: {self.device_info['name'].decode()}")
            print(f"Memory: {self.device_info['totalGlobalMem'] / 1024**3:.1f} GB")
        except Exception as e:
            raise RuntimeError(f"GPU initialization failed: {e}")
    
    def transfer_to_gpu(self, data_3d):
        """Transfer data to GPU memory."""
        return cp.asarray(data_3d)
    
    def calculate_mean_patterns_gpu(self, data_3d_gpu):
        """Calculate mean gait patterns on GPU."""
        # Mean across cycles (axis 0)
        mean_patterns = cp.mean(data_3d_gpu, axis=0)
        return mean_patterns
    
    def calculate_variability_gpu(self, data_3d_gpu):
        """Calculate gait variability metrics on GPU."""
        
        # Standard deviation across cycles
        std_patterns = cp.std(data_3d_gpu, axis=0)
        
        # Coefficient of variation
        mean_patterns = cp.mean(data_3d_gpu, axis=0)
        cv_patterns = cp.divide(std_patterns, mean_patterns, 
                               out=cp.zeros_like(std_patterns), 
                               where=mean_patterns!=0)
        
        # Range of motion per cycle
        cycle_max = cp.max(data_3d_gpu, axis=1)  # (n_cycles, n_features)
        cycle_min = cp.min(data_3d_gpu, axis=1)
        rom_per_cycle = cycle_max - cycle_min
        
        return {
            'std_patterns': std_patterns,
            'cv_patterns': cv_patterns,
            'rom_per_cycle': rom_per_cycle,
            'mean_rom': cp.mean(rom_per_cycle, axis=0)
        }
    
    def cross_correlation_gpu(self, data_3d_gpu):
        """Calculate cross-correlations between features on GPU."""
        
        n_cycles, n_phases, n_features = data_3d_gpu.shape
        
        # Reshape to (n_observations, n_features)
        data_2d = data_3d_gpu.reshape(n_cycles * n_phases, n_features)
        
        # Calculate correlation matrix
        correlation_matrix = cp.corrcoef(data_2d.T)
        
        return correlation_matrix
    
    def principal_components_gpu(self, data_3d_gpu, n_components=5):
        """Calculate principal components on GPU."""
        
        n_cycles, n_phases, n_features = data_3d_gpu.shape
        
        # Reshape and center data
        data_2d = data_3d_gpu.reshape(n_cycles, n_phases * n_features)
        data_centered = data_2d - cp.mean(data_2d, axis=0)
        
        # SVD for PCA
        U, s, Vt = cp.linalg.svd(data_centered, full_matrices=False)
        
        # Calculate explained variance
        explained_variance = (s ** 2) / (n_cycles - 1)
        explained_variance_ratio = explained_variance / cp.sum(explained_variance)
        
        # Principal components
        components = Vt[:n_components]
        transformed = cp.dot(data_centered, components.T)
        
        return {
            'components': components,
            'transformed': transformed,
            'explained_variance_ratio': explained_variance_ratio[:n_components]
        }
    
    def batch_analyze_gpu(self, loco_data, subjects, tasks, analysis_type='all'):
        """Perform batch analysis on GPU."""
        
        results = {}
        
        for subject in subjects:
            subject_results = {}
            
            for task in tasks:
                # Get data and transfer to GPU
                data_3d, features = loco_data.get_cycles(subject, task)
                if data_3d is None:
                    continue
                
                print(f"Processing {subject}-{task} on GPU...")
                
                # Transfer to GPU
                data_3d_gpu = self.transfer_to_gpu(data_3d)
                
                task_results = {}
                
                if analysis_type in ['all', 'mean']:
                    mean_patterns = self.calculate_mean_patterns_gpu(data_3d_gpu)
                    task_results['mean_patterns'] = cp.asnumpy(mean_patterns)
                
                if analysis_type in ['all', 'variability']:
                    variability = self.calculate_variability_gpu(data_3d_gpu)
                    task_results['variability'] = {
                        k: cp.asnumpy(v) for k, v in variability.items()
                    }
                
                if analysis_type in ['all', 'correlation']:
                    correlation = self.cross_correlation_gpu(data_3d_gpu)
                    task_results['correlation'] = cp.asnumpy(correlation)
                
                if analysis_type in ['all', 'pca']:
                    pca_results = self.principal_components_gpu(data_3d_gpu)
                    task_results['pca'] = {
                        k: cp.asnumpy(v) for k, v in pca_results.items()
                    }
                
                # Clean up GPU memory
                del data_3d_gpu
                cp.get_default_memory_pool().free_all_blocks()
                
                task_results['features'] = features
                subject_results[task] = task_results
            
            results[subject] = subject_results
        
        return results

# Usage (if GPU available)
if GPU_AVAILABLE:
    gpu_analyzer = GPUGaitAnalyzer()
    loco = LocomotionData('dataset_phase.parquet')
    
    # GPU-accelerated analysis
    gpu_results = gpu_analyzer.batch_analyze_gpu(
        loco, 
        subjects=['SUB01', 'SUB02'], 
        tasks=['normal_walk'],
        analysis_type='all'
    )
    
    print("GPU analysis completed")
    
    # Example: Access PCA results
    pca_results = gpu_results['SUB01']['normal_walk']['pca']
    print(f"Explained variance ratios: {pca_results['explained_variance_ratio']}")
```

## Caching Strategies

### Intelligent Caching System

```python
import pickle
import hashlib
from pathlib import Path
import time
import json

class GaitAnalysisCache:
    """Intelligent caching system for gait analysis results."""
    
    def __init__(self, cache_dir='gait_cache', max_cache_size_gb=5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size_gb * 1024**3
        
        # Cache metadata
        self.metadata_file = self.cache_dir / 'cache_metadata.json'
        self.load_metadata()
    
    def load_metadata(self):
        """Load cache metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'entries': {},
                'total_size': 0,
                'last_cleanup': time.time()
            }
    
    def save_metadata(self):
        """Save cache metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def generate_cache_key(self, func_name, *args, **kwargs):
        """Generate unique cache key for function call."""
        
        # Create string representation of arguments
        key_data = {
            'function': func_name,
            'args': args,
            'kwargs': {k: v for k, v in kwargs.items() if k != 'force_recalculate'}
        }
        
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        
        # Generate hash
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return cache_key
    
    def get_cache_path(self, cache_key):
        """Get cache file path for key."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def is_cached(self, cache_key):
        """Check if result is cached."""
        cache_path = self.get_cache_path(cache_key)
        return cache_path.exists() and cache_key in self.metadata['entries']
    
    def get_cached_result(self, cache_key):
        """Retrieve cached result."""
        if not self.is_cached(cache_key):
            return None
        
        cache_path = self.get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'rb') as f:
                result = pickle.load(f)
            
            # Update access time
            self.metadata['entries'][cache_key]['last_accessed'] = time.time()
            self.save_metadata()
            
            return result
            
        except Exception as e:
            print(f"Error loading cached result: {e}")
            # Remove corrupted cache entry
            self.remove_cache_entry(cache_key)
            return None
    
    def cache_result(self, cache_key, result, func_name):
        """Cache analysis result."""
        
        cache_path = self.get_cache_path(cache_key)
        
        try:
            # Save result
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            
            # Update metadata
            file_size = cache_path.stat().st_size
            self.metadata['entries'][cache_key] = {
                'function': func_name,
                'size': file_size,
                'created': time.time(),
                'last_accessed': time.time(),
                'file_path': str(cache_path)
            }
            self.metadata['total_size'] += file_size
            
            # Check cache size limit
            if self.metadata['total_size'] > self.max_cache_size:
                self.cleanup_cache()
            
            self.save_metadata()
            
        except Exception as e:
            print(f"Error caching result: {e}")
    
    def remove_cache_entry(self, cache_key):
        """Remove cache entry."""
        if cache_key in self.metadata['entries']:
            cache_path = Path(self.metadata['entries'][cache_key]['file_path'])
            if cache_path.exists():
                file_size = cache_path.stat().st_size
                cache_path.unlink()
                self.metadata['total_size'] -= file_size
            
            del self.metadata['entries'][cache_key]
            self.save_metadata()
    
    def cleanup_cache(self):
        """Clean up cache based on LRU policy."""
        
        # Sort entries by last access time
        entries_by_access = sorted(
            self.metadata['entries'].items(),
            key=lambda x: x[1]['last_accessed']
        )
        
        # Remove oldest entries until under size limit
        target_size = self.max_cache_size * 0.8  # Keep 20% buffer
        
        while self.metadata['total_size'] > target_size and entries_by_access:
            cache_key, entry = entries_by_access.pop(0)
            print(f"Removing cached entry: {entry['function']}")
            self.remove_cache_entry(cache_key)
        
        self.metadata['last_cleanup'] = time.time()
        print(f"Cache cleanup completed. Size: {self.metadata['total_size'] / 1024**2:.1f} MB")

class CachedGaitAnalyzer:
    """Gait analyzer with intelligent caching."""
    
    def __init__(self, loco_data, cache_dir='gait_cache'):
        self.loco_data = loco_data
        self.cache = GaitAnalysisCache(cache_dir)
    
    def cached_analysis(self, func, *args, force_recalculate=False, **kwargs):
        """Decorator-like function for caching analysis results."""
        
        func_name = func.__name__
        cache_key = self.cache.generate_cache_key(func_name, *args, **kwargs)
        
        # Check cache first
        if not force_recalculate and self.cache.is_cached(cache_key):
            print(f"Loading cached result for {func_name}")
            return self.cache.get_cached_result(cache_key)
        
        # Calculate result
        print(f"Calculating {func_name}...")
        start_time = time.time()
        result = func(*args, **kwargs)
        calculation_time = time.time() - start_time
        
        # Cache result
        self.cache.cache_result(cache_key, result, func_name)
        print(f"Calculation completed in {calculation_time:.2f}s and cached")
        
        return result
    
    def get_summary_statistics_cached(self, subject, task, force_recalculate=False):
        """Cached version of summary statistics calculation."""
        
        def calculate_stats(subject, task):
            return self.loco_data.get_summary_statistics(subject, task)
        
        return self.cached_analysis(
            calculate_stats, subject, task, 
            force_recalculate=force_recalculate
        )
    
    def get_cycles_cached(self, subject, task, features=None, force_recalculate=False):
        """Cached version of get_cycles."""
        
        def get_cycles_data(subject, task, features):
            return self.loco_data.get_cycles(subject, task, features)
        
        return self.cached_analysis(
            get_cycles_data, subject, task, features,
            force_recalculate=force_recalculate
        )
    
    def calculate_advanced_metrics_cached(self, subject, task, force_recalculate=False):
        """Calculate and cache advanced gait metrics."""
        
        def calculate_advanced_metrics(subject, task):
            # Get data
            data_3d, features = self.loco_data.get_cycles(subject, task)
            if data_3d is None:
                return None
            
            metrics = {}
            
            # ROM calculation
            rom_data = self.loco_data.calculate_rom(subject, task, by_cycle=False)
            metrics['rom'] = {k: float(v) for k, v in rom_data.items()}
            
            # Variability metrics
            for i, feature in enumerate(features):
                signal_data = data_3d[:, :, i]
                
                # Coefficient of variation
                cycle_means = np.mean(signal_data, axis=1)
                cv = np.std(cycle_means) / np.mean(cycle_means) if np.mean(cycle_means) != 0 else 0
                metrics[f'{feature}_cv'] = float(cv)
                
                # Step-to-step variability
                step_variability = np.std(cycle_means) / np.mean(cycle_means) if np.mean(cycle_means) != 0 else 0
                metrics[f'{feature}_step_variability'] = float(step_variability)
            
            # Symmetry analysis
            ipsi_features = [f for f in features if 'ipsi' in f]
            for ipsi_feature in ipsi_features:
                contra_feature = ipsi_feature.replace('ipsi', 'contra')
                if contra_feature in features:
                    ipsi_idx = features.index(ipsi_feature)
                    contra_idx = features.index(contra_feature)
                    
                    ipsi_mean = np.mean(data_3d[:, :, ipsi_idx])
                    contra_mean = np.mean(data_3d[:, :, contra_idx])
                    
                    symmetry_index = abs(ipsi_mean - contra_mean) / (0.5 * (abs(ipsi_mean) + abs(contra_mean)))
                    metrics[f'{ipsi_feature}_symmetry'] = float(symmetry_index)
            
            return metrics
        
        return self.cached_analysis(
            calculate_advanced_metrics, subject, task,
            force_recalculate=force_recalculate
        )

# Usage
loco = LocomotionData('dataset_phase.parquet')
cached_analyzer = CachedGaitAnalyzer(loco, cache_dir='gait_analysis_cache')

# First call - calculates and caches
stats1 = cached_analyzer.get_summary_statistics_cached('SUB01', 'normal_walk')
print("First call completed")

# Second call - loads from cache
stats2 = cached_analyzer.get_summary_statistics_cached('SUB01', 'normal_walk')
print("Second call completed (cached)")

# Advanced metrics with caching
advanced_metrics = cached_analyzer.calculate_advanced_metrics_cached('SUB01', 'normal_walk')
print(f"Advanced metrics: {len(advanced_metrics)} calculated")

# Force recalculation
stats3 = cached_analyzer.get_summary_statistics_cached('SUB01', 'normal_walk', force_recalculate=True)
print("Forced recalculation completed")
```

## Algorithm Optimization

### Vectorized Operations

```python
import numpy as np
from numba import jit, prange
import time

class OptimizedGaitCalculations:
    """Optimized algorithms for common gait calculations."""
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def calculate_rom_vectorized(data_3d):
        """Vectorized ROM calculation using Numba."""
        
        n_cycles, n_phases, n_features = data_3d.shape
        rom_results = np.zeros((n_cycles, n_features))
        
        for cycle in prange(n_cycles):
            for feature in prange(n_features):
                cycle_data = data_3d[cycle, :, feature]
                rom_results[cycle, feature] = np.max(cycle_data) - np.min(cycle_data)
        
        return rom_results
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def calculate_phase_correlations_optimized(data_3d):
        """Optimized phase correlation calculation."""
        
        n_cycles, n_phases, n_features = data_3d.shape
        correlations = np.zeros((n_phases, n_features, n_features))
        
        for phase in prange(n_phases):
            phase_data = data_3d[:, phase, :]  # (n_cycles, n_features)
            
            # Calculate correlation matrix for this phase
            for i in range(n_features):
                for j in range(n_features):
                    if i <= j:  # Only calculate upper triangle
                        x = phase_data[:, i]
                        y = phase_data[:, j]
                        
                        # Pearson correlation
                        mean_x = np.mean(x)
                        mean_y = np.mean(y)
                        
                        num = np.sum((x - mean_x) * (y - mean_y))
                        den = np.sqrt(np.sum((x - mean_x)**2) * np.sum((y - mean_y)**2))
                        
                        if den > 0:
                            corr = num / den
                        else:
                            corr = 0.0
                        
                        correlations[phase, i, j] = corr
                        correlations[phase, j, i] = corr  # Symmetric
        
        return correlations
    
    @staticmethod
    @jit(nopython=True)
    def detect_outliers_iqr(data, k=1.5):
        """Fast outlier detection using IQR method."""
        
        q25 = np.percentile(data, 25)
        q75 = np.percentile(data, 75)
        iqr = q75 - q25
        
        lower_bound = q25 - k * iqr
        upper_bound = q75 + k * iqr
        
        outliers = (data < lower_bound) | (data > upper_bound)
        return outliers
    
    @staticmethod
    def benchmark_calculations(data_3d, n_iterations=10):
        """Benchmark different calculation approaches."""
        
        print(f"Benchmarking with data shape: {data_3d.shape}")
        
        # Standard numpy approach
        start_time = time.time()
        for _ in range(n_iterations):
            rom_numpy = np.max(data_3d, axis=1) - np.min(data_3d, axis=1)
        numpy_time = (time.time() - start_time) / n_iterations
        
        # Optimized numba approach
        start_time = time.time()
        for _ in range(n_iterations):
            rom_numba = OptimizedGaitCalculations.calculate_rom_vectorized(data_3d)
        numba_time = (time.time() - start_time) / n_iterations
        
        print(f"NumPy ROM calculation: {numpy_time:.4f}s")
        print(f"Numba ROM calculation: {numba_time:.4f}s")
        print(f"Speedup: {numpy_time / numba_time:.2f}x")
        
        # Verify results are equivalent
        np.testing.assert_allclose(rom_numpy, rom_numba, rtol=1e-10)
        print("Results verified - calculations are equivalent")

# Performance comparison example
loco = LocomotionData('dataset_phase.parquet')
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')

if data_3d is not None:
    optimizer = OptimizedGaitCalculations()
    optimizer.benchmark_calculations(data_3d, n_iterations=100)
```

### Streaming Data Processing

```python
class StreamingGaitProcessor:
    """Process gait data in streaming fashion for real-time applications."""
    
    def __init__(self, buffer_size=150):
        self.buffer_size = buffer_size
        self.reset_buffer()
    
    def reset_buffer(self):
        """Reset processing buffer."""
        self.buffer = []
        self.processed_cycles = 0
    
    def add_data_point(self, data_point):
        """Add new data point to buffer."""
        self.buffer.append(data_point)
        
        # Process when buffer is full
        if len(self.buffer) >= self.buffer_size:
            cycle_data = np.array(self.buffer[:self.buffer_size])
            self.process_cycle(cycle_data)
            
            # Slide buffer
            self.buffer = self.buffer[self.buffer_size:]
            self.processed_cycles += 1
    
    def process_cycle(self, cycle_data):
        """Process a complete gait cycle."""
        
        # Calculate real-time metrics
        metrics = {
            'cycle_number': self.processed_cycles,
            'rom': np.max(cycle_data, axis=0) - np.min(cycle_data, axis=0),
            'mean_values': np.mean(cycle_data, axis=0),
            'peak_indices': np.argmax(cycle_data, axis=0),
            'valley_indices': np.argmin(cycle_data, axis=0)
        }
        
        # Trigger alerts if needed
        self.check_alerts(metrics)
        
        return metrics
    
    def check_alerts(self, metrics):
        """Check for real-time alerts based on gait metrics."""
        
        # Example alert conditions
        if np.any(metrics['rom'] < 0.1):  # Very low ROM
            print(f"Alert: Low ROM detected in cycle {metrics['cycle_number']}")
        
        if np.any(metrics['mean_values'] < -2.0) or np.any(metrics['mean_values'] > 2.0):
            print(f"Alert: Extreme values detected in cycle {metrics['cycle_number']}")

# Real-time processing simulation
processor = StreamingGaitProcessor()

# Simulate streaming data
loco = LocomotionData('dataset_phase.parquet')
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')

if data_3d is not None:
    print("Simulating streaming gait analysis...")
    
    # Process each cycle point by point
    for cycle_idx in range(min(5, data_3d.shape[0])):  # Process first 5 cycles
        for phase_idx in range(data_3d.shape[1]):
            data_point = data_3d[cycle_idx, phase_idx, :]
            processor.add_data_point(data_point)
        
        print(f"Processed cycle {cycle_idx + 1}")
```

This comprehensive performance optimization guide provides strategies for memory management, parallel processing, caching, and algorithm optimization to handle large-scale locomotion data analysis efficiently.