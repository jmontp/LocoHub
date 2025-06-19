# Performance Optimization Guide

Advanced techniques for optimizing performance when working with large locomotion datasets, including memory management, parallel processing, and algorithmic optimizations.

## Overview

This guide covers performance optimization strategies for:
- Large dataset processing (>1GB parquet files)
- Memory-efficient data loading and analysis
- Parallel processing techniques
- Streaming data operations
- Caching strategies

## Memory Optimization

### Efficient Data Loading

```python
import numpy as np
import pandas as pd
from pathlib import Path
import psutil
import gc
from typing import Iterator, Generator
from lib.core.locomotion_analysis import LocomotionData

class MemoryEfficientLoader:
    """Memory-efficient data loading for large datasets."""
    
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        self.memory_threshold = 0.8  # 80% memory usage threshold
        
    def load_in_chunks(self, file_path: str) -> Generator[pd.DataFrame, None, None]:
        """Load parquet file in chunks to manage memory."""
        
        # Read parquet file metadata to estimate size
        pf = pd.read_parquet(file_path, engine='pyarrow')
        total_rows = len(pf)
        
        # Calculate optimal chunk size based on available memory
        available_memory = psutil.virtual_memory().available
        estimated_row_size = pf.memory_usage(deep=True).sum() / total_rows
        optimal_chunk_size = min(
            self.chunk_size,
            int(available_memory * 0.5 / estimated_row_size)  # Use 50% of available memory
        )
        
        print(f"Loading {total_rows} rows in chunks of {optimal_chunk_size}")
        
        # Load in chunks
        for start in range(0, total_rows, optimal_chunk_size):
            end = min(start + optimal_chunk_size, total_rows)
            chunk = pf.iloc[start:end].copy()
            yield chunk
            
            # Force garbage collection after each chunk
            gc.collect()
    
    def process_dataset_streaming(self, file_path: str, processing_func) -> dict:
        """Process dataset in streaming fashion."""
        
        results = []
        total_processed = 0
        
        for chunk in self.load_in_chunks(file_path):
            # Process chunk
            chunk_result = processing_func(chunk)
            results.append(chunk_result)
            
            total_processed += len(chunk)
            
            # Monitor memory usage
            memory_percent = psutil.virtual_memory().percent / 100
            if memory_percent > self.memory_threshold:
                print(f"⚠️  High memory usage: {memory_percent:.1%}")
                gc.collect()  # Force garbage collection
        
        print(f"Processed {total_processed} total rows")
        return {'results': results, 'total_processed': total_processed}

class StreamingLocomotionAnalysis:
    """Memory-efficient analysis for large locomotion datasets."""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        
    def streaming_feature_extraction(self, file_path: str, 
                                   subjects: list = None, 
                                   tasks: list = None) -> Iterator[dict]:
        """Extract features in streaming fashion."""
        
        loader = MemoryEfficientLoader(chunk_size=self.batch_size)
        
        for chunk in loader.load_in_chunks(file_path):
            # Filter chunk if subjects/tasks specified
            if subjects:
                chunk = chunk[chunk['subject'].isin(subjects)]
            if tasks:
                chunk = chunk[chunk['task'].isin(tasks)]
            
            if len(chunk) == 0:
                continue
            
            # Process this chunk
            chunk_features = self._extract_chunk_features(chunk)
            yield chunk_features
    
    def _extract_chunk_features(self, chunk: pd.DataFrame) -> dict:
        """Extract features from a data chunk."""
        
        features = {
            'chunk_size': len(chunk),
            'subjects': chunk['subject'].nunique(),
            'tasks': chunk['task'].nunique(),
            'subject_task_combinations': []
        }
        
        # Group by subject-task and extract features
        for (subject, task), group in chunk.groupby(['subject', 'task']):
            if len(group) % 150 == 0:  # Valid phase data
                n_cycles = len(group) // 150
                
                # Extract features for each cycle
                for cycle in range(n_cycles):
                    start_idx = cycle * 150
                    end_idx = (cycle + 1) * 150
                    cycle_data = group.iloc[start_idx:end_idx]
                    
                    # Calculate basic statistics
                    feature_cols = [col for col in cycle_data.columns 
                                  if 'angle' in col or 'moment' in col]
                    
                    if feature_cols:
                        cycle_features = {
                            'subject': subject,
                            'task': task,
                            'cycle': cycle,
                            'features': {}
                        }
                        
                        for col in feature_cols:
                            data = cycle_data[col].values
                            cycle_features['features'][col] = {
                                'mean': np.mean(data),
                                'std': np.std(data),
                                'rom': np.max(data) - np.min(data),
                                'peak_phase': np.argmax(np.abs(data))
                            }
                        
                        features['subject_task_combinations'].append(cycle_features)
        
        return features

# Example usage
file_path = 'large_dataset_phase.parquet'
analyzer = StreamingLocomotionAnalysis(batch_size=5000)

# Process in streaming fashion
all_features = []
for chunk_features in analyzer.streaming_feature_extraction(file_path):
    all_features.extend(chunk_features['subject_task_combinations'])
    print(f"Processed chunk: {chunk_features['chunk_size']} rows, "
          f"{chunk_features['subjects']} subjects, {chunk_features['tasks']} tasks")

print(f"Total features extracted: {len(all_features)}")
```

### Memory-Mapped Arrays

```python
import numpy as np
from pathlib import Path
import tempfile

class MemoryMappedDataset:
    """Memory-mapped dataset for efficient large data access."""
    
    def __init__(self, data_shape: tuple, dtype=np.float32, mode='w+'):
        self.shape = data_shape
        self.dtype = dtype
        
        # Create temporary file for memory mapping
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        
        # Create memory-mapped array
        self.data = np.memmap(
            self.temp_path, 
            dtype=dtype, 
            mode=mode, 
            shape=data_shape
        )
        
    def __del__(self):
        """Clean up temporary file."""
        try:
            Path(self.temp_path).unlink(missing_ok=True)
        except:
            pass
    
    def save_chunk(self, chunk_data: np.ndarray, start_idx: int):
        """Save data chunk to memory-mapped array."""
        end_idx = start_idx + chunk_data.shape[0]
        self.data[start_idx:end_idx] = chunk_data
        
    def get_chunk(self, start_idx: int, chunk_size: int) -> np.ndarray:
        """Get data chunk from memory-mapped array."""
        end_idx = min(start_idx + chunk_size, self.shape[0])
        return self.data[start_idx:end_idx]
    
    def flush(self):
        """Flush changes to disk."""
        self.data.flush()

class EfficientFeatureMatrix:
    """Efficient feature matrix using memory mapping."""
    
    def __init__(self, max_samples: int, n_features: int):
        self.max_samples = max_samples
        self.n_features = n_features
        self.current_size = 0
        
        # Create memory-mapped arrays
        self.features = MemoryMappedDataset((max_samples, n_features), dtype=np.float32)
        self.labels = MemoryMappedDataset((max_samples,), dtype=np.int32)
        self.metadata = []  # Keep metadata in memory as it's smaller
        
    def add_batch(self, batch_features: np.ndarray, batch_labels: np.ndarray, 
                  batch_metadata: list):
        """Add batch of features to matrix."""
        
        batch_size = len(batch_features)
        
        if self.current_size + batch_size > self.max_samples:
            raise ValueError("Exceeding maximum samples capacity")
        
        # Add to memory-mapped arrays
        start_idx = self.current_size
        self.features.save_chunk(batch_features.astype(np.float32), start_idx)
        self.labels.save_chunk(batch_labels.astype(np.int32), start_idx)
        
        # Add metadata
        self.metadata.extend(batch_metadata)
        
        self.current_size += batch_size
        
        # Flush to disk
        self.features.flush()
        self.labels.flush()
    
    def get_batch(self, start_idx: int, batch_size: int) -> tuple:
        """Get batch of features."""
        
        end_idx = min(start_idx + batch_size, self.current_size)
        actual_batch_size = end_idx - start_idx
        
        batch_features = self.features.get_chunk(start_idx, actual_batch_size)
        batch_labels = self.labels.get_chunk(start_idx, actual_batch_size)
        batch_metadata = self.metadata[start_idx:end_idx]
        
        return batch_features, batch_labels, batch_metadata
    
    def get_all_data(self) -> tuple:
        """Get all data (use with caution for large datasets)."""
        features = self.features.data[:self.current_size]
        labels = self.labels.data[:self.current_size]
        return features, labels, self.metadata

# Example usage for large dataset
def process_large_dataset_efficiently(file_path: str, max_samples: int = 1000000):
    """Process large dataset efficiently using memory mapping."""
    
    # Estimate feature count (assuming 6 kinematic features)
    n_features = 6 * 4  # 6 variables * 4 statistical features
    
    # Create efficient feature matrix
    feature_matrix = EfficientFeatureMatrix(max_samples, n_features)
    
    # Process in streaming fashion
    analyzer = StreamingLocomotionAnalysis(batch_size=1000)
    
    for chunk_features in analyzer.streaming_feature_extraction(file_path):
        if len(chunk_features['subject_task_combinations']) == 0:
            continue
            
        # Convert to arrays
        batch_features = []
        batch_labels = []
        batch_metadata = []
        
        for item in chunk_features['subject_task_combinations']:
            # Flatten features
            feature_vector = []
            for var_name, stats in item['features'].items():
                feature_vector.extend([
                    stats['mean'], stats['std'], 
                    stats['rom'], stats['peak_phase']
                ])
            
            if len(feature_vector) == n_features:  # Ensure consistent size
                batch_features.append(feature_vector)
                batch_labels.append(hash(item['task']) % 10)  # Simple label encoding
                batch_metadata.append({
                    'subject': item['subject'],
                    'task': item['task'],
                    'cycle': item['cycle']
                })
        
        if batch_features:
            batch_features = np.array(batch_features)
            batch_labels = np.array(batch_labels)
            
            feature_matrix.add_batch(batch_features, batch_labels, batch_metadata)
            
            print(f"Added batch: {len(batch_features)} samples, "
                  f"Total: {feature_matrix.current_size}")
    
    return feature_matrix
```

## Parallel Processing

### Multiprocessing for Data Analysis

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import time

class ParallelLocomotionProcessor:
    """Parallel processing for locomotion data analysis."""
    
    def __init__(self, n_workers: int = None):
        self.n_workers = n_workers or mp.cpu_count()
        
    def parallel_subject_analysis(self, file_path: str, analysis_func, 
                                 subjects: list = None) -> dict:
        """Analyze subjects in parallel."""
        
        # Load dataset once
        loco = LocomotionData(file_path)
        target_subjects = subjects or loco.subjects
        
        print(f"Processing {len(target_subjects)} subjects using {self.n_workers} workers")
        
        # Create partial function with fixed parameters
        worker_func = partial(self._analyze_single_subject, file_path, analysis_func)
        
        results = {}
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all tasks
            future_to_subject = {
                executor.submit(worker_func, subject): subject 
                for subject in target_subjects
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_subject):
                subject = future_to_subject[future]
                try:
                    result = future.result()
                    results[subject] = result
                    print(f"Completed: {subject}")
                except Exception as e:
                    print(f"Error processing {subject}: {e}")
                    results[subject] = {'error': str(e)}
        
        return results
    
    def _analyze_single_subject(self, file_path: str, analysis_func, subject: str):
        """Analyze single subject (worker function)."""
        
        # Load dataset in worker process
        loco = LocomotionData(file_path)
        
        # Run analysis
        return analysis_func(loco, subject)
    
    def parallel_task_analysis(self, file_path: str, analysis_func,
                              tasks: list = None) -> dict:
        """Analyze tasks in parallel."""
        
        loco = LocomotionData(file_path)
        target_tasks = tasks or loco.tasks
        
        print(f"Processing {len(target_tasks)} tasks using {self.n_workers} workers")
        
        worker_func = partial(self._analyze_single_task, file_path, analysis_func)
        
        results = {}
        
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            future_to_task = {
                executor.submit(worker_func, task): task 
                for task in target_tasks
            }
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task] = result
                    print(f"Completed: {task}")
                except Exception as e:
                    print(f"Error processing {task}: {e}")
                    results[task] = {'error': str(e)}
        
        return results
    
    def _analyze_single_task(self, file_path: str, analysis_func, task: str):
        """Analyze single task (worker function)."""
        
        loco = LocomotionData(file_path)
        return analysis_func(loco, task)

# Example analysis functions
def comprehensive_subject_analysis(loco: LocomotionData, subject: str) -> dict:
    """Comprehensive analysis for a single subject."""
    
    results = {
        'subject': subject,
        'tasks_completed': [],
        'total_cycles': 0,
        'quality_scores': {},
        'rom_data': {},
        'outlier_counts': {}
    }
    
    for task in loco.tasks:
        try:
            # Get cycles
            data_3d, features = loco.get_cycles(subject, task)
            
            if data_3d is not None:
                results['tasks_completed'].append(task)
                results['total_cycles'] += data_3d.shape[0]
                
                # Quality assessment
                valid_mask = loco.validate_cycles(subject, task)
                quality_score = np.sum(valid_mask) / len(valid_mask)
                results['quality_scores'][task] = quality_score
                
                # ROM analysis
                rom_data = loco.calculate_rom(subject, task, by_cycle=False)
                results['rom_data'][task] = rom_data
                
                # Outlier detection
                outliers = loco.find_outlier_cycles(subject, task)
                results['outlier_counts'][task] = len(outliers)
                
        except Exception as e:
            print(f"Error analyzing {subject}-{task}: {e}")
    
    return results

def task_population_analysis(loco: LocomotionData, task: str) -> dict:
    """Population-level analysis for a single task."""
    
    results = {
        'task': task,
        'subjects_with_data': [],
        'population_stats': {},
        'mean_patterns': {},
        'variability_analysis': {}
    }
    
    all_subjects_data = []
    
    for subject in loco.subjects:
        try:
            data_3d, features = loco.get_cycles(subject, task)
            
            if data_3d is not None:
                results['subjects_with_data'].append(subject)
                
                # Calculate mean pattern for this subject
                mean_pattern = np.mean(data_3d, axis=0)  # (150, n_features)
                all_subjects_data.append(mean_pattern)
                
        except Exception as e:
            continue
    
    if all_subjects_data:
        all_subjects_array = np.array(all_subjects_data)  # (n_subjects, 150, n_features)
        
        # Population statistics
        population_mean = np.mean(all_subjects_array, axis=0)  # (150, n_features)
        population_std = np.std(all_subjects_array, axis=0)
        
        results['population_stats'] = {
            'n_subjects': len(all_subjects_data),
            'mean_pattern_shape': population_mean.shape,
            'mean_variability': np.mean(population_std)
        }
        
        # Store patterns (convert to lists for JSON serialization)
        if len(features) > 0:
            for i, feature in enumerate(features):
                results['mean_patterns'][feature] = population_mean[:, i].tolist()
                results['variability_analysis'][feature] = {
                    'mean_std': np.mean(population_std[:, i]),
                    'max_std': np.max(population_std[:, i]),
                    'coefficient_of_variation': np.mean(population_std[:, i]) / np.mean(population_mean[:, i])
                }
    
    return results

# Example usage
processor = ParallelLocomotionProcessor(n_workers=4)

# Parallel subject analysis
start_time = time.time()
subject_results = processor.parallel_subject_analysis(
    'large_dataset_phase.parquet', 
    comprehensive_subject_analysis
)
subject_time = time.time() - start_time

print(f"Subject analysis completed in {subject_time:.2f} seconds")
print(f"Processed {len(subject_results)} subjects")

# Parallel task analysis
start_time = time.time()
task_results = processor.parallel_task_analysis(
    'large_dataset_phase.parquet',
    task_population_analysis
)
task_time = time.time() - start_time

print(f"Task analysis completed in {task_time:.2f} seconds")
print(f"Processed {len(task_results)} tasks")

# Summary statistics
total_cycles = sum(r['total_cycles'] for r in subject_results.values() if 'total_cycles' in r)
print(f"Total cycles processed: {total_cycles}")
```

### GPU Acceleration with CuPy

```python
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("CuPy not available, falling back to CPU")

class GPUAcceleratedAnalysis:
    """GPU-accelerated locomotion data analysis using CuPy."""
    
    def __init__(self, use_gpu: bool = None):
        self.use_gpu = use_gpu if use_gpu is not None else GPU_AVAILABLE
        
        if self.use_gpu and not GPU_AVAILABLE:
            print("GPU requested but CuPy not available, using CPU")
            self.use_gpu = False
            
        self.xp = cp if self.use_gpu else np
        
    def gpu_statistical_analysis(self, data_3d: np.ndarray) -> dict:
        """Perform statistical analysis on GPU."""
        
        # Transfer data to GPU
        if self.use_gpu:
            gpu_data = cp.asarray(data_3d)
        else:
            gpu_data = data_3d
        
        # Calculate statistics on GPU
        mean_patterns = self.xp.mean(gpu_data, axis=0)  # (150, n_features)
        std_patterns = self.xp.std(gpu_data, axis=0)
        
        # Range of motion calculation
        rom_per_cycle = self.xp.max(gpu_data, axis=1) - self.xp.min(gpu_data, axis=1)
        mean_rom = self.xp.mean(rom_per_cycle, axis=0)
        
        # Peak detection
        peak_indices = self.xp.argmax(self.xp.abs(gpu_data), axis=1)
        
        # Cross-correlations between features
        n_cycles, n_points, n_features = gpu_data.shape
        correlations = self.xp.zeros((n_features, n_features))
        
        for i in range(n_features):
            for j in range(i, n_features):
                # Flatten cycles for correlation calculation
                feat_i = gpu_data[:, :, i].flatten()
                feat_j = gpu_data[:, :, j].flatten()
                
                # Calculate correlation coefficient
                corr = self.xp.corrcoef(feat_i, feat_j)[0, 1]
                correlations[i, j] = corr
                correlations[j, i] = corr
        
        # Transfer results back to CPU
        if self.use_gpu:
            results = {
                'mean_patterns': cp.asnumpy(mean_patterns),
                'std_patterns': cp.asnumpy(std_patterns),
                'mean_rom': cp.asnumpy(mean_rom),
                'peak_indices': cp.asnumpy(peak_indices),
                'feature_correlations': cp.asnumpy(correlations)
            }
        else:
            results = {
                'mean_patterns': mean_patterns,
                'std_patterns': std_patterns,
                'mean_rom': mean_rom,
                'peak_indices': peak_indices,
                'feature_correlations': correlations
            }
        
        return results
    
    def gpu_outlier_detection(self, data_3d: np.ndarray, threshold: float = 2.0) -> np.ndarray:
        """GPU-accelerated outlier detection."""
        
        if self.use_gpu:
            gpu_data = cp.asarray(data_3d)
        else:
            gpu_data = data_3d
        
        # Calculate mean pattern
        mean_pattern = self.xp.mean(gpu_data, axis=0)
        
        # Calculate deviations
        deviations = gpu_data - mean_pattern[self.xp.newaxis, :, :]
        
        # Calculate RMSE for each cycle
        rmse_per_cycle = self.xp.sqrt(self.xp.mean(deviations**2, axis=(1, 2)))
        
        # Outlier threshold
        outlier_threshold = self.xp.mean(rmse_per_cycle) + threshold * self.xp.std(rmse_per_cycle)
        
        # Find outliers
        outlier_mask = rmse_per_cycle > outlier_threshold
        
        if self.use_gpu:
            return cp.asnumpy(outlier_mask)
        else:
            return outlier_mask
    
    def batch_gpu_analysis(self, file_path: str, batch_size: int = 1000) -> dict:
        """Batch GPU analysis for large datasets."""
        
        loco = LocomotionData(file_path)
        
        all_results = {
            'subjects_processed': 0,
            'total_cycles': 0,
            'gpu_time': 0,
            'subject_results': {}
        }
        
        for subject in loco.subjects:
            subject_gpu_time = 0
            
            for task in loco.tasks:
                try:
                    data_3d, features = loco.get_cycles(subject, task)
                    
                    if data_3d is not None and data_3d.shape[0] > 0:
                        # Process in batches if data is large
                        n_cycles = data_3d.shape[0]
                        
                        for batch_start in range(0, n_cycles, batch_size):
                            batch_end = min(batch_start + batch_size, n_cycles)
                            batch_data = data_3d[batch_start:batch_end]
                            
                            # GPU analysis
                            start_time = time.time()
                            
                            stats = self.gpu_statistical_analysis(batch_data)
                            outliers = self.gpu_outlier_detection(batch_data)
                            
                            batch_gpu_time = time.time() - start_time
                            subject_gpu_time += batch_gpu_time
                            
                            # Store results
                            if subject not in all_results['subject_results']:
                                all_results['subject_results'][subject] = {}
                            
                            all_results['subject_results'][subject][task] = {
                                'cycles_processed': batch_data.shape[0],
                                'outlier_count': int(np.sum(outliers)),
                                'mean_rom': stats['mean_rom'].tolist(),
                                'processing_time': batch_gpu_time
                            }
                            
                            all_results['total_cycles'] += batch_data.shape[0]
                
                except Exception as e:
                    print(f"Error processing {subject}-{task}: {e}")
            
            all_results['subjects_processed'] += 1
            all_results['gpu_time'] += subject_gpu_time
            
            if all_results['subjects_processed'] % 10 == 0:
                print(f"Processed {all_results['subjects_processed']} subjects, "
                      f"GPU time: {all_results['gpu_time']:.2f}s")
        
        return all_results

# Example usage
if GPU_AVAILABLE:
    # GPU analysis
    gpu_analyzer = GPUAcceleratedAnalysis(use_gpu=True)
    
    # Load sample data
    loco = LocomotionData('dataset_phase.parquet')
    data_3d, features = loco.get_cycles(loco.subjects[0], loco.tasks[0])
    
    if data_3d is not None:
        # Compare CPU vs GPU performance
        start_time = time.time()
        cpu_results = GPUAcceleratedAnalysis(use_gpu=False).gpu_statistical_analysis(data_3d)
        cpu_time = time.time() - start_time
        
        start_time = time.time()
        gpu_results = gpu_analyzer.gpu_statistical_analysis(data_3d)
        gpu_time = time.time() - start_time
        
        print(f"CPU analysis time: {cpu_time:.4f}s")
        print(f"GPU analysis time: {gpu_time:.4f}s")
        print(f"Speedup: {cpu_time/gpu_time:.2f}x")
        
        # Batch analysis
        batch_results = gpu_analyzer.batch_gpu_analysis('dataset_phase.parquet')
        print(f"Processed {batch_results['total_cycles']} cycles in {batch_results['gpu_time']:.2f}s")
```

## Caching Strategies

### Intelligent Caching System

```python
import pickle
import hashlib
from pathlib import Path
import time
from functools import wraps
from typing import Any, Callable

class LocomotionDataCache:
    """Intelligent caching system for locomotion data analysis."""
    
    def __init__(self, cache_dir: str = '.cache', max_cache_size: int = 1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size  # MB
        self.cache_index = self._load_cache_index()
        
    def _load_cache_index(self) -> dict:
        """Load cache index from disk."""
        index_file = self.cache_dir / 'cache_index.pkl'
        if index_file.exists():
            with open(index_file, 'rb') as f:
                return pickle.load(f)
        return {}
    
    def _save_cache_index(self):
        """Save cache index to disk."""
        index_file = self.cache_dir / 'cache_index.pkl'
        with open(index_file, 'wb') as f:
            pickle.dump(self.cache_index, f)
    
    def _get_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function arguments."""
        # Create hashable representation
        cache_data = (func_name, args, tuple(sorted(kwargs.items())))
        cache_str = str(cache_data)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _cleanup_cache(self):
        """Remove old cache entries if cache is too large."""
        total_size = sum(
            (self.cache_dir / entry['filename']).stat().st_size 
            for entry in self.cache_index.values()
            if (self.cache_dir / entry['filename']).exists()
        ) / (1024 * 1024)  # Convert to MB
        
        if total_size > self.max_cache_size:
            # Sort by last access time and remove oldest
            sorted_entries = sorted(
                self.cache_index.items(),
                key=lambda x: x[1]['last_access']
            )
            
            removed_size = 0
            for cache_key, entry in sorted_entries:
                cache_file = self.cache_dir / entry['filename']
                if cache_file.exists():
                    file_size = cache_file.stat().st_size / (1024 * 1024)
                    cache_file.unlink()
                    removed_size += file_size
                
                del self.cache_index[cache_key]
                
                if total_size - removed_size < self.max_cache_size * 0.8:
                    break
            
            self._save_cache_index()
            print(f"Cache cleanup: removed {removed_size:.1f}MB")
    
    def get(self, func_name: str, args: tuple, kwargs: dict) -> Any:
        """Get cached result."""
        cache_key = self._get_cache_key(func_name, args, kwargs)
        
        if cache_key in self.cache_index:
            cache_file = self.cache_dir / self.cache_index[cache_key]['filename']
            
            if cache_file.exists():
                # Update last access time
                self.cache_index[cache_key]['last_access'] = time.time()
                
                # Load cached result
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        return None
    
    def set(self, func_name: str, args: tuple, kwargs: dict, result: Any):
        """Cache result."""
        cache_key = self._get_cache_key(func_name, args, kwargs)
        filename = f"{cache_key}.pkl"
        cache_file = self.cache_dir / filename
        
        # Save result
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
        
        # Update index
        self.cache_index[cache_key] = {
            'filename': filename,
            'created': time.time(),
            'last_access': time.time(),
            'function': func_name
        }
        
        self._save_cache_index()
        
        # Cleanup if necessary
        self._cleanup_cache()

def cached_analysis(cache_instance: LocomotionDataCache = None):
    """Decorator for caching analysis results."""
    
    if cache_instance is None:
        cache_instance = LocomotionDataCache()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get from cache
            cached_result = cache_instance.get(func.__name__, args, kwargs)
            
            if cached_result is not None:
                print(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function
            print(f"Computing {func.__name__}...")
            start_time = time.time()
            result = func(*args, **kwargs)
            computation_time = time.time() - start_time
            
            print(f"Computed in {computation_time:.2f}s, caching result")
            
            # Cache result
            cache_instance.set(func.__name__, args, kwargs, result)
            
            return result
        
        return wrapper
    return decorator

# Create global cache instance
global_cache = LocomotionDataCache(max_cache_size=2000)  # 2GB cache

@cached_analysis(global_cache)
def expensive_population_analysis(file_path: str, task: str) -> dict:
    """Expensive analysis that benefits from caching."""
    
    loco = LocomotionData(file_path)
    
    all_data = []
    for subject in loco.subjects:
        data_3d, features = loco.get_cycles(subject, task)
        if data_3d is not None:
            # Calculate comprehensive statistics
            for cycle_idx in range(data_3d.shape[0]):
                cycle_data = data_3d[cycle_idx, :, :]
                
                # Complex feature extraction
                cycle_features = {
                    'subject': subject,
                    'cycle': cycle_idx,
                    'features': {}
                }
                
                for feat_idx, feat_name in enumerate(features):
                    feat_data = cycle_data[:, feat_idx]
                    
                    # Statistical moments
                    cycle_features['features'][feat_name] = {
                        'mean': np.mean(feat_data),
                        'std': np.std(feat_data),
                        'skewness': scipy.stats.skew(feat_data),
                        'kurtosis': scipy.stats.kurtosis(feat_data),
                        'rom': np.max(feat_data) - np.min(feat_data),
                        'peak_timing': np.argmax(np.abs(feat_data)) / len(feat_data)
                    }
                    
                    # Fourier analysis
                    fft = np.fft.fft(feat_data)
                    freqs = np.fft.fftfreq(len(feat_data))
                    
                    cycle_features['features'][feat_name]['dominant_frequency'] = \
                        freqs[np.argmax(np.abs(fft[1:len(fft)//2])) + 1]
                
                all_data.append(cycle_features)
    
    # Population-level analysis
    population_stats = {}
    
    if features:
        for feat_name in features:
            feat_values = {
                'mean': [item['features'][feat_name]['mean'] for item in all_data],
                'std': [item['features'][feat_name]['std'] for item in all_data],
                'rom': [item['features'][feat_name]['rom'] for item in all_data]
            }
            
            population_stats[feat_name] = {
                'mean_of_means': np.mean(feat_values['mean']),
                'std_of_means': np.std(feat_values['mean']),
                'mean_variability': np.mean(feat_values['std']),
                'rom_distribution': {
                    'mean': np.mean(feat_values['rom']),
                    'std': np.std(feat_values['rom']),
                    'percentiles': np.percentile(feat_values['rom'], [5, 25, 50, 75, 95]).tolist()
                }
            }
    
    return {
        'task': task,
        'n_subjects': len(set(item['subject'] for item in all_data)),
        'n_cycles': len(all_data),
        'population_stats': population_stats,
        'raw_data': all_data
    }

# Example usage
import scipy.stats

# First call - will compute and cache
result1 = expensive_population_analysis('dataset_phase.parquet', 'level_walking')

# Second call - will use cache
result2 = expensive_population_analysis('dataset_phase.parquet', 'level_walking')

# Verify results are identical
assert result1['n_cycles'] == result2['n_cycles']
print(f"Processed {result1['n_cycles']} cycles from {result1['n_subjects']} subjects")
```

## Algorithmic Optimizations

### Optimized 3D Array Operations

```python
import numba
from numba import jit, prange
import numpy as np

class OptimizedAnalytics:
    """Optimized analytics using Numba JIT compilation."""
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def fast_statistical_features(data_3d: np.ndarray) -> np.ndarray:
        """Fast computation of statistical features using Numba."""
        
        n_cycles, n_points, n_features = data_3d.shape
        n_stats = 6  # mean, std, min, max, rom, peak_timing
        
        # Output array: (n_cycles, n_features * n_stats)
        features = np.zeros((n_cycles, n_features * n_stats))
        
        for cycle in prange(n_cycles):
            for feat in prange(n_features):
                feat_data = data_3d[cycle, :, feat]
                
                # Calculate statistics
                mean_val = np.mean(feat_data)
                std_val = np.std(feat_data)
                min_val = np.min(feat_data)
                max_val = np.max(feat_data)
                rom_val = max_val - min_val
                peak_idx = np.argmax(np.abs(feat_data))
                peak_timing = peak_idx / n_points
                
                # Store in output array
                base_idx = feat * n_stats
                features[cycle, base_idx] = mean_val
                features[cycle, base_idx + 1] = std_val
                features[cycle, base_idx + 2] = min_val
                features[cycle, base_idx + 3] = max_val
                features[cycle, base_idx + 4] = rom_val
                features[cycle, base_idx + 5] = peak_timing
        
        return features
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def fast_outlier_detection(data_3d: np.ndarray, threshold: float = 2.0) -> np.ndarray:
        """Fast outlier detection using Numba."""
        
        n_cycles, n_points, n_features = data_3d.shape
        
        # Calculate mean pattern
        mean_pattern = np.mean(data_3d, axis=0)
        
        # Calculate RMSE for each cycle
        rmse_values = np.zeros(n_cycles)
        
        for cycle in prange(n_cycles):
            total_error = 0.0
            count = 0
            
            for point in range(n_points):
                for feat in range(n_features):
                    diff = data_3d[cycle, point, feat] - mean_pattern[point, feat]
                    total_error += diff * diff
                    count += 1
            
            rmse_values[cycle] = np.sqrt(total_error / count)
        
        # Calculate threshold
        mean_rmse = np.mean(rmse_values)
        std_rmse = np.std(rmse_values)
        outlier_threshold = mean_rmse + threshold * std_rmse
        
        # Find outliers
        outlier_mask = rmse_values > outlier_threshold
        
        return outlier_mask
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def fast_correlation_matrix(data_3d: np.ndarray) -> np.ndarray:
        """Fast correlation matrix computation using Numba."""
        
        n_cycles, n_points, n_features = data_3d.shape
        
        # Flatten data for correlation calculation
        flattened_data = np.zeros((n_features, n_cycles * n_points))
        
        for feat in prange(n_features):
            for cycle in range(n_cycles):
                for point in range(n_points):
                    idx = cycle * n_points + point
                    flattened_data[feat, idx] = data_3d[cycle, point, feat]
        
        # Calculate correlation matrix
        corr_matrix = np.zeros((n_features, n_features))
        
        for i in prange(n_features):
            for j in range(i, n_features):
                # Calculate correlation coefficient
                data_i = flattened_data[i, :]
                data_j = flattened_data[j, :]
                
                mean_i = np.mean(data_i)
                mean_j = np.mean(data_j)
                
                numerator = 0.0
                denom_i = 0.0
                denom_j = 0.0
                
                for k in range(len(data_i)):
                    diff_i = data_i[k] - mean_i
                    diff_j = data_j[k] - mean_j
                    
                    numerator += diff_i * diff_j
                    denom_i += diff_i * diff_i
                    denom_j += diff_j * diff_j
                
                if denom_i > 0 and denom_j > 0:
                    corr = numerator / np.sqrt(denom_i * denom_j)
                else:
                    corr = 0.0
                
                corr_matrix[i, j] = corr
                corr_matrix[j, i] = corr
        
        return corr_matrix

class BenchmarkOptimizations:
    """Benchmark different optimization techniques."""
    
    def __init__(self):
        self.optimizer = OptimizedAnalytics()
    
    def benchmark_feature_extraction(self, data_3d: np.ndarray) -> dict:
        """Benchmark feature extraction methods."""
        
        results = {}
        
        # NumPy implementation
        start_time = time.time()
        numpy_features = self._numpy_feature_extraction(data_3d)
        numpy_time = time.time() - start_time
        
        # Numba implementation
        start_time = time.time()
        numba_features = self.optimizer.fast_statistical_features(data_3d)
        numba_time = time.time() - start_time
        
        results = {
            'numpy_time': numpy_time,
            'numba_time': numba_time,
            'speedup': numpy_time / numba_time,
            'results_match': np.allclose(numpy_features, numba_features, rtol=1e-5)
        }
        
        return results
    
    def _numpy_feature_extraction(self, data_3d: np.ndarray) -> np.ndarray:
        """NumPy-based feature extraction for comparison."""
        
        n_cycles, n_points, n_features = data_3d.shape
        features = []
        
        for cycle in range(n_cycles):
            cycle_features = []
            
            for feat in range(n_features):
                feat_data = data_3d[cycle, :, feat]
                
                # Calculate statistics
                mean_val = np.mean(feat_data)
                std_val = np.std(feat_data)
                min_val = np.min(feat_data)
                max_val = np.max(feat_data)
                rom_val = max_val - min_val
                peak_timing = np.argmax(np.abs(feat_data)) / n_points
                
                cycle_features.extend([mean_val, std_val, min_val, max_val, rom_val, peak_timing])
            
            features.append(cycle_features)
        
        return np.array(features)
    
    def run_comprehensive_benchmark(self, file_path: str) -> dict:
        """Run comprehensive performance benchmark."""
        
        loco = LocomotionData(file_path)
        
        # Get sample data
        subject = loco.subjects[0]
        task = loco.tasks[0]
        data_3d, features = loco.get_cycles(subject, task)
        
        if data_3d is None:
            return {'error': 'No data available for benchmarking'}
        
        print(f"Benchmarking with data shape: {data_3d.shape}")
        
        # Feature extraction benchmark
        feature_benchmark = self.benchmark_feature_extraction(data_3d)
        
        # Outlier detection benchmark
        start_time = time.time()
        numpy_outliers = self._numpy_outlier_detection(data_3d)
        numpy_outlier_time = time.time() - start_time
        
        start_time = time.time()
        numba_outliers = self.optimizer.fast_outlier_detection(data_3d)
        numba_outlier_time = time.time() - start_time
        
        # Correlation benchmark
        start_time = time.time()
        numpy_corr = self._numpy_correlation(data_3d)
        numpy_corr_time = time.time() - start_time
        
        start_time = time.time()
        numba_corr = self.optimizer.fast_correlation_matrix(data_3d)
        numba_corr_time = time.time() - start_time
        
        return {
            'data_shape': data_3d.shape,
            'feature_extraction': feature_benchmark,
            'outlier_detection': {
                'numpy_time': numpy_outlier_time,
                'numba_time': numba_outlier_time,
                'speedup': numpy_outlier_time / numba_outlier_time,
                'results_match': np.allclose(numpy_outliers, numba_outliers)
            },
            'correlation': {
                'numpy_time': numpy_corr_time,
                'numba_time': numba_corr_time,
                'speedup': numpy_corr_time / numba_corr_time,
                'results_match': np.allclose(numpy_corr, numba_corr, rtol=1e-5)
            }
        }
    
    def _numpy_outlier_detection(self, data_3d: np.ndarray, threshold: float = 2.0) -> np.ndarray:
        """NumPy outlier detection for comparison."""
        mean_pattern = np.mean(data_3d, axis=0)
        deviations = data_3d - mean_pattern[np.newaxis, :, :]
        rmse_per_cycle = np.sqrt(np.mean(deviations**2, axis=(1, 2)))
        outlier_threshold = np.mean(rmse_per_cycle) + threshold * np.std(rmse_per_cycle)
        return rmse_per_cycle > outlier_threshold
    
    def _numpy_correlation(self, data_3d: np.ndarray) -> np.ndarray:
        """NumPy correlation calculation for comparison."""
        n_cycles, n_points, n_features = data_3d.shape
        flattened = data_3d.reshape(-1, n_features)
        return np.corrcoef(flattened.T)

# Example usage
benchmark = BenchmarkOptimizations()
results = benchmark.run_comprehensive_benchmark('dataset_phase.parquet')

print("Performance Benchmark Results:")
print(f"Data shape: {results['data_shape']}")
print(f"Feature extraction speedup: {results['feature_extraction']['speedup']:.2f}x")
print(f"Outlier detection speedup: {results['outlier_detection']['speedup']:.2f}x")
print(f"Correlation speedup: {results['correlation']['speedup']:.2f}x")

# Verify correctness
all_correct = (
    results['feature_extraction']['results_match'] and
    results['outlier_detection']['results_match'] and
    results['correlation']['results_match']
)

print(f"All optimizations produce correct results: {all_correct}")
```

## Performance Monitoring and Profiling

### Real-time Performance Monitor

```python
import psutil
import time
import threading
from collections import deque
import matplotlib.pyplot as plt

class PerformanceMonitor:
    """Real-time performance monitoring for locomotion data processing."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.monitoring = False
        self.monitor_thread = None
        
        # Performance metrics
        self.timestamps = deque(maxlen=max_history)
        self.cpu_usage = deque(maxlen=max_history)
        self.memory_usage = deque(maxlen=max_history)
        self.memory_available = deque(maxlen=max_history)
        
        # Processing metrics
        self.processing_times = deque(maxlen=max_history)
        self.throughput = deque(maxlen=max_history)
        
    def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        print("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Performance monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Monitoring loop running in separate thread."""
        while self.monitoring:
            timestamp = time.time()
            
            # System metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Store metrics
            self.timestamps.append(timestamp)
            self.cpu_usage.append(cpu_percent)
            self.memory_usage.append(memory_percent)
            self.memory_available.append(memory_available_mb)
            
            time.sleep(interval)
    
    def record_processing_time(self, processing_time: float, items_processed: int):
        """Record processing performance."""
        self.processing_times.append(processing_time)
        
        if processing_time > 0:
            throughput_value = items_processed / processing_time
            self.throughput.append(throughput_value)
    
    def get_current_stats(self) -> dict:
        """Get current performance statistics."""
        if not self.timestamps:
            return {}
        
        return {
            'cpu_usage': self.cpu_usage[-1] if self.cpu_usage else 0,
            'memory_usage': self.memory_usage[-1] if self.memory_usage else 0,
            'memory_available_mb': self.memory_available[-1] if self.memory_available else 0,
            'avg_processing_time': np.mean(list(self.processing_times)) if self.processing_times else 0,
            'avg_throughput': np.mean(list(self.throughput)) if self.throughput else 0
        }
    
    def plot_performance(self, save_path: str = None):
        """Plot performance metrics."""
        if not self.timestamps:
            print("No monitoring data available")
            return
        
        # Convert timestamps to relative time
        start_time = self.timestamps[0]
        relative_times = [(t - start_time) / 60 for t in self.timestamps]  # Minutes
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # CPU usage
        ax1.plot(relative_times, list(self.cpu_usage), 'b-', linewidth=1)
        ax1.set_title('CPU Usage')
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('CPU %')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 100)
        
        # Memory usage
        ax2.plot(relative_times, list(self.memory_usage), 'r-', linewidth=1)
        ax2.set_title('Memory Usage')
        ax2.set_xlabel('Time (minutes)')
        ax2.set_ylabel('Memory %')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)
        
        # Processing times
        if self.processing_times:
            ax3.plot(list(self.processing_times), 'g-', linewidth=1)
            ax3.set_title('Processing Times')
            ax3.set_xlabel('Processing Batch')
            ax3.set_ylabel('Time (seconds)')
            ax3.grid(True, alpha=0.3)
        
        # Throughput
        if self.throughput:
            ax4.plot(list(self.throughput), 'm-', linewidth=1)
            ax4.set_title('Processing Throughput')
            ax4.set_xlabel('Processing Batch')
            ax4.set_ylabel('Items/second')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Performance plot saved to {save_path}")
        else:
            plt.show()

# Example usage with performance monitoring
def monitored_analysis_example(file_path: str):
    """Example of analysis with performance monitoring."""
    
    # Start monitoring
    monitor = PerformanceMonitor()
    monitor.start_monitoring(interval=0.5)  # Monitor every 0.5 seconds
    
    try:
        # Load data
        print("Loading dataset...")
        start_time = time.time()
        loco = LocomotionData(file_path)
        load_time = time.time() - start_time
        monitor.record_processing_time(load_time, 1)
        
        # Process subjects
        results = {}
        for i, subject in enumerate(loco.subjects[:10]):  # Process first 10 subjects
            print(f"Processing subject {i+1}/10: {subject}")
            
            subject_start = time.time()
            subject_results = {}
            
            for task in loco.tasks:
                # Get data
                data_3d, features = loco.get_cycles(subject, task)
                
                if data_3d is not None:
                    # Use optimized analysis
                    optimizer = OptimizedAnalytics()
                    features_extracted = optimizer.fast_statistical_features(data_3d)
                    outliers = optimizer.fast_outlier_detection(data_3d)
                    
                    subject_results[task] = {
                        'cycles': data_3d.shape[0],
                        'outliers': int(np.sum(outliers)),
                        'features_shape': features_extracted.shape
                    }
            
            subject_time = time.time() - subject_start
            monitor.record_processing_time(subject_time, len(subject_results))
            
            results[subject] = subject_results
            
            # Print current stats every 5 subjects
            if (i + 1) % 5 == 0:
                stats = monitor.get_current_stats()
                print(f"  Current stats: CPU {stats['cpu_usage']:.1f}%, "
                      f"Memory {stats['memory_usage']:.1f}%, "
                      f"Throughput {stats['avg_throughput']:.1f} tasks/sec")
        
        print("Analysis completed!")
        
        # Final statistics
        final_stats = monitor.get_current_stats()
        print(f"Final Performance Summary:")
        print(f"  Average CPU Usage: {final_stats['cpu_usage']:.1f}%")
        print(f"  Average Memory Usage: {final_stats['memory_usage']:.1f}%")
        print(f"  Average Processing Time: {final_stats['avg_processing_time']:.2f}s")
        print(f"  Average Throughput: {final_stats['avg_throughput']:.1f} items/sec")
        
        # Plot performance
        monitor.plot_performance('performance_analysis.png')
        
        return results
        
    finally:
        # Stop monitoring
        monitor.stop_monitoring()

# Run monitored analysis
# results = monitored_analysis_example('dataset_phase.parquet')
```

This comprehensive performance optimization guide provides:

1. **Memory optimization** with efficient data loading and memory-mapped arrays
2. **Parallel processing** using multiprocessing and GPU acceleration
3. **Intelligent caching** to avoid redundant computations
4. **Algorithmic optimizations** using Numba JIT compilation
5. **Performance monitoring** for real-time analysis

These techniques can significantly improve performance when working with large locomotion datasets, reducing processing times from hours to minutes for typical analysis workflows.

## Next Steps

- **[Cloud Integration](cloud-integration.md)** - Cloud deployment and scaling patterns
- **[Research Platform Integration](research-platform-integration.md)** - Integration with research platforms
- **[Developer Workflows](../developer/README.md)** - Contributing and extending the platform