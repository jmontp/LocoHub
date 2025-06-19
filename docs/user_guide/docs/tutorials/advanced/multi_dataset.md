# Advanced Multi-Dataset Analysis

Master sophisticated analysis patterns combining multiple locomotion datasets for comprehensive biomechanical research.

## Overview

Multi-dataset analysis enables powerful research capabilities:

- **Cross-study comparisons**: Compare findings across different research groups
- **Population-level insights**: Establish normative values from large cohorts
- **Methodological validation**: Verify findings across different measurement systems
- **Longitudinal tracking**: Monitor changes over time or interventions

This tutorial demonstrates memory-safe patterns for analyzing multiple datasets using existing small test files.

## Prerequisites

Complete [Basic Analysis](../basic/load_explore.md) and [Metrics](../basic/metrics.md) tutorials first.

## Memory-Safe Multi-Dataset Patterns

### Pattern 1: Sequential Analysis

Process datasets one at a time to minimize memory usage:

```python
import pandas as pd
import numpy as np
from pathlib import Path
from locomotion_analysis import LocomotionData

def analyze_datasets_sequentially(dataset_paths, analysis_func):
    """
    Analyze multiple datasets sequentially to minimize memory usage.
    
    Parameters:
    -----------
    dataset_paths : list
        List of paths to locomotion datasets
    analysis_func : callable
        Function that takes LocomotionData object and returns results
    
    Returns:
    --------
    dict : Combined results from all datasets
    """
    combined_results = {}
    
    for i, path in enumerate(dataset_paths):
        print(f"Processing dataset {i+1}/{len(dataset_paths)}: {path}")
        
        # Load dataset
        loco = LocomotionData(path)
        
        # Perform analysis
        results = analysis_func(loco)
        
        # Store results with dataset identifier
        dataset_name = Path(path).stem
        combined_results[dataset_name] = results
        
        # Clear from memory
        del loco
        
    return combined_results

# Example usage
def compute_rom_statistics(loco_data):
    """Compute ROM statistics for a dataset."""
    subjects = loco_data.get_subjects()
    tasks = loco_data.get_tasks()
    
    rom_stats = {}
    
    for subject in subjects:
        for task in tasks:
            try:
                rom_data = loco_data.calculate_rom(subject, task)
                
                # Focus on key variables
                key_vars = ['knee_flexion_angle_contra_rad', 
                           'hip_flexion_angle_contra_rad']
                
                for var in key_vars:
                    if var in rom_data:
                        key = f"{subject}_{task}_{var}"
                        rom_stats[key] = {
                            'mean': np.mean(rom_data[var]),
                            'std': np.std(rom_data[var]),
                            'n_cycles': len(rom_data[var])
                        }
            except Exception as e:
                print(f"Warning: Failed to process {subject}/{task}: {e}")
                
    return rom_stats

# Process multiple datasets
dataset_paths = [
    'docs/tutorials/test_files/locomotion_data.csv',
    # Add more dataset paths here
]

# combined_results = analyze_datasets_sequentially(dataset_paths, compute_rom_statistics)
```

### Pattern 2: Metadata-First Approach

Extract metadata before loading full datasets:

```python
def extract_dataset_metadata(csv_path):
    """
    Extract key metadata without loading full dataset.
    
    Returns basic information about subjects, tasks, and data volume.
    """
    # Read just the first few rows to understand structure
    sample_df = pd.read_csv(csv_path, nrows=100)
    
    # Get unique values
    subjects = sample_df['subject_id'].unique() if 'subject_id' in sample_df.columns else []
    tasks = sample_df['task_id'].unique() if 'task_id' in sample_df.columns else []
    
    # Estimate total rows
    with open(csv_path, 'r') as f:
        total_lines = sum(1 for _ in f) - 1  # Subtract header
    
    metadata = {
        'n_subjects': len(subjects),
        'n_tasks': len(tasks),
        'n_rows': total_lines,
        'subjects': list(subjects),
        'tasks': list(tasks),
        'columns': list(sample_df.columns)
    }
    
    return metadata

# Example: Plan analysis based on metadata
def plan_multi_dataset_analysis(dataset_paths):
    """Plan analysis strategy based on dataset characteristics."""
    
    print("Dataset Inventory:")
    print("=" * 50)
    
    total_subjects = set()
    total_tasks = set()
    
    for path in dataset_paths:
        meta = extract_dataset_metadata(path)
        dataset_name = Path(path).stem
        
        print(f"{dataset_name}:")
        print(f"  Subjects: {meta['n_subjects']} ({', '.join(meta['subjects'])})")
        print(f"  Tasks: {meta['n_tasks']} ({', '.join(meta['tasks'])})")
        print(f"  Data points: {meta['n_rows']:,}")
        print()
        
        total_subjects.update(meta['subjects'])
        total_tasks.update(meta['tasks'])
    
    print(f"Combined Analysis Scope:")
    print(f"  Total unique subjects: {len(total_subjects)}")
    print(f"  Total unique tasks: {len(total_tasks)}")
    print(f"  Common subjects: {identify_common_subjects(dataset_paths)}")
    print(f"  Common tasks: {identify_common_tasks(dataset_paths)}")

def identify_common_subjects(dataset_paths):
    """Find subjects present in multiple datasets."""
    all_subjects = []
    
    for path in dataset_paths:
        meta = extract_dataset_metadata(path)
        all_subjects.append(set(meta['subjects']))
    
    if len(all_subjects) > 1:
        common = all_subjects[0]
        for subjects in all_subjects[1:]:
            common = common.intersection(subjects)
        return list(common)
    else:
        return list(all_subjects[0]) if all_subjects else []

def identify_common_tasks(dataset_paths):
    """Find tasks present in multiple datasets."""
    all_tasks = []
    
    for path in dataset_paths:
        meta = extract_dataset_metadata(path)
        all_tasks.append(set(meta['tasks']))
    
    if len(all_tasks) > 1:
        common = all_tasks[0]
        for tasks in all_tasks[1:]:
            common = common.intersection(tasks)
        return list(common)
    else:
        return list(all_tasks[0]) if all_tasks else []
```

## Advanced Analysis Patterns

### Cross-Dataset Comparison

Compare the same metrics across different datasets:

```python
def compare_across_datasets(dataset_paths, target_subjects=None, target_tasks=None):
    """
    Compare specific metrics across multiple datasets.
    
    Parameters:
    -----------
    dataset_paths : list
        Paths to datasets to compare
    target_subjects : list, optional
        Specific subjects to analyze (None = all)
    target_tasks : list, optional
        Specific tasks to analyze (None = all)
    """
    
    comparison_results = {}
    
    for path in dataset_paths:
        dataset_name = Path(path).stem
        print(f"Analyzing {dataset_name}...")
        
        loco = LocomotionData(path)
        
        # Get available subjects and tasks
        available_subjects = loco.get_subjects()
        available_tasks = loco.get_tasks()
        
        # Filter to targets if specified
        subjects = target_subjects if target_subjects else available_subjects
        tasks = target_tasks if target_tasks else available_tasks
        
        # Compute metrics for each subject/task combination
        dataset_metrics = {}
        
        for subject in subjects:
            if subject not in available_subjects:
                continue
                
            for task in tasks:
                if task not in available_tasks:
                    continue
                
                try:
                    # Calculate key metrics
                    rom_data = loco.calculate_rom(subject, task)
                    mean_patterns = loco.get_mean_patterns(subject, task)
                    
                    # Store key metrics
                    key = f"{subject}_{task}"
                    dataset_metrics[key] = {
                        'knee_rom': np.mean(rom_data.get('knee_flexion_angle_contra_rad', [0])),
                        'hip_rom': np.mean(rom_data.get('hip_flexion_angle_contra_rad', [0])),
                        'knee_peak': np.max(mean_patterns.get('knee_flexion_angle_contra_rad', [0])),
                        'n_cycles': len(rom_data.get('knee_flexion_angle_contra_rad', []))
                    }
                    
                except Exception as e:
                    print(f"  Warning: Failed {subject}/{task}: {e}")
        
        comparison_results[dataset_name] = dataset_metrics
        del loco  # Free memory
    
    return comparison_results

def summarize_cross_dataset_comparison(comparison_results):
    """Create summary of cross-dataset comparison."""
    
    print("\\nCross-Dataset Comparison Summary:")
    print("=" * 50)
    
    # Find common subject/task combinations
    all_keys = set()
    for dataset_metrics in comparison_results.values():
        all_keys.update(dataset_metrics.keys())
    
    common_keys = all_keys
    for dataset_metrics in comparison_results.values():
        common_keys = common_keys.intersection(set(dataset_metrics.keys()))
    
    print(f"Common analyses: {len(common_keys)}")
    
    if common_keys:
        print("\\nMetric Comparison (mean ± std across datasets):")
        
        metrics = ['knee_rom', 'hip_rom', 'knee_peak']
        
        for metric in metrics:
            print(f"\\n{metric.replace('_', ' ').title()}:")
            
            for key in sorted(common_keys):
                values = []
                for dataset_name, dataset_metrics in comparison_results.items():
                    if key in dataset_metrics and metric in dataset_metrics[key]:
                        values.append(dataset_metrics[key][metric])
                
                if values:
                    mean_val = np.mean(values)
                    std_val = np.std(values)
                    print(f"  {key}: {mean_val:.3f} ± {std_val:.3f} rad ({len(values)} datasets)")
```

### Population Normative Analysis

Establish normative values across multiple datasets:

```python
def create_population_norms(dataset_paths, age_groups=None):
    """
    Create population normative values from multiple datasets.
    
    Parameters:
    -----------
    dataset_paths : list
        Paths to datasets containing population data
    age_groups : dict, optional
        Dictionary mapping age group names to subject lists
    """
    
    print("Creating Population Normative Database...")
    print("=" * 50)
    
    # Collect all data
    population_data = {
        'knee_rom': [],
        'hip_rom': [],
        'ankle_rom': [],
        'subjects': [],
        'datasets': []
    }
    
    for path in dataset_paths:
        dataset_name = Path(path).stem
        print(f"Processing {dataset_name}...")
        
        loco = LocomotionData(path)
        subjects = loco.get_subjects()
        
        for subject in subjects:
            try:
                # Use standard walking task
                rom_data = loco.calculate_rom(subject, 'level_walking')
                
                # Extract ROM values
                knee_rom = np.mean(rom_data.get('knee_flexion_angle_contra_rad', []))
                hip_rom = np.mean(rom_data.get('hip_flexion_angle_contra_rad', []))
                ankle_rom = np.mean(rom_data.get('ankle_flexion_angle_contra_rad', []))
                
                # Store data
                population_data['knee_rom'].append(knee_rom)
                population_data['hip_rom'].append(hip_rom)
                population_data['ankle_rom'].append(ankle_rom)
                population_data['subjects'].append(subject)
                population_data['datasets'].append(dataset_name)
                
            except Exception as e:
                print(f"  Warning: Failed {subject}: {e}")
        
        del loco  # Free memory
    
    # Compute normative statistics
    normative_stats = {}
    
    for metric in ['knee_rom', 'hip_rom', 'ankle_rom']:
        values = np.array(population_data[metric])
        values = values[~np.isnan(values)]  # Remove NaN values
        
        if len(values) > 0:
            normative_stats[metric] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'median': np.median(values),
                'p25': np.percentile(values, 25),
                'p75': np.percentile(values, 75),
                'p95_lower': np.percentile(values, 2.5),
                'p95_upper': np.percentile(values, 97.5),
                'n': len(values)
            }
    
    return normative_stats, population_data

def report_population_norms(normative_stats):
    """Generate normative values report."""
    
    print("\\nPopulation Normative Values:")
    print("=" * 50)
    
    for metric, stats in normative_stats.items():
        metric_name = metric.replace('_', ' ').title()
        
        print(f"\\n{metric_name}:")
        print(f"  Mean: {np.degrees(stats['mean']):.1f}° ± {np.degrees(stats['std']):.1f}°")
        print(f"  Median: {np.degrees(stats['median']):.1f}°")
        print(f"  IQR: {np.degrees(stats['p25']):.1f}° - {np.degrees(stats['p75']):.1f}°")
        print(f"  95% CI: {np.degrees(stats['p95_lower']):.1f}° - {np.degrees(stats['p95_upper']):.1f}°")
        print(f"  Sample size: {stats['n']}")
```

## Performance and Memory Optimization

### Chunked Processing

Process large datasets in manageable chunks:

```python
def process_large_dataset_chunked(csv_path, chunk_size=10000, analysis_func=None):
    """
    Process large CSV datasets in chunks to manage memory usage.
    
    Parameters:
    -----------
    csv_path : str
        Path to large CSV file
    chunk_size : int
        Number of rows to process at once
    analysis_func : callable
        Function to apply to each chunk
    """
    
    results = []
    
    # Process file in chunks
    for chunk_df in pd.read_csv(csv_path, chunksize=chunk_size):
        
        # Apply analysis to chunk
        if analysis_func:
            chunk_result = analysis_func(chunk_df)
            results.append(chunk_result)
        
        # Print progress
        print(f"Processed chunk with {len(chunk_df)} rows")
    
    return results

def analyze_chunk_for_metrics(chunk_df):
    """Extract key metrics from a data chunk."""
    
    # Group by subject and task
    grouped = chunk_df.groupby(['subject_id', 'task_id'])
    
    chunk_metrics = {}
    
    for (subject, task), group in grouped:
        # Calculate basic statistics
        knee_data = group.get('knee_flexion_angle_rad', [])
        
        if len(knee_data) > 0:
            chunk_metrics[f"{subject}_{task}"] = {
                'knee_mean': np.mean(knee_data),
                'knee_std': np.std(knee_data),
                'n_points': len(knee_data)
            }
    
    return chunk_metrics
```

### Smart Caching

Cache intermediate results to avoid recomputation:

```python
import pickle
from pathlib import Path

class MultiDatasetAnalyzer:
    """
    Smart analyzer with caching for multi-dataset workflows.
    """
    
    def __init__(self, cache_dir='analysis_cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_cache_path(self, dataset_path, analysis_type):
        """Generate cache file path."""
        dataset_name = Path(dataset_path).stem
        return self.cache_dir / f"{dataset_name}_{analysis_type}.pkl"
    
    def load_or_compute_rom(self, dataset_path, force_recompute=False):
        """Load ROM data from cache or compute if needed."""
        
        cache_path = self.get_cache_path(dataset_path, 'rom_analysis')
        
        # Check if cached result exists and is newer than dataset
        if not force_recompute and cache_path.exists():
            dataset_mtime = Path(dataset_path).stat().st_mtime
            cache_mtime = cache_path.stat().st_mtime
            
            if cache_mtime > dataset_mtime:
                print(f"Loading cached ROM analysis for {Path(dataset_path).stem}")
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        
        # Compute ROM analysis
        print(f"Computing ROM analysis for {Path(dataset_path).stem}")
        loco = LocomotionData(dataset_path)
        
        rom_results = {}
        subjects = loco.get_subjects()
        tasks = loco.get_tasks()
        
        for subject in subjects:
            for task in tasks:
                try:
                    rom_data = loco.calculate_rom(subject, task)
                    rom_results[f"{subject}_{task}"] = rom_data
                except Exception as e:
                    print(f"Warning: ROM calculation failed for {subject}/{task}: {e}")
        
        # Cache results
        with open(cache_path, 'wb') as f:
            pickle.dump(rom_results, f)
        
        del loco  # Free memory
        return rom_results
    
    def clear_cache(self):
        """Clear all cached results."""
        for cache_file in self.cache_dir.glob('*.pkl'):
            cache_file.unlink()
        print("Cache cleared")
```

## Practical Examples

### Example 1: Cross-Laboratory Validation

```python
def validate_across_labs():
    """
    Example: Validate gait measurements across different laboratories.
    Uses small test files to demonstrate the pattern.
    """
    
    print("Cross-Laboratory Validation Study")
    print("=" * 40)
    
    # Simulate multiple lab datasets (using same test file for demonstration)
    lab_datasets = {
        'Lab_A': 'docs/tutorials/test_files/locomotion_data.csv',
        # In real use: 'Lab_B': 'path/to/lab_b_data.csv',
        # In real use: 'Lab_C': 'path/to/lab_c_data.csv',
    }
    
    lab_results = {}
    
    for lab_name, dataset_path in lab_datasets.items():
        print(f"\\nProcessing {lab_name}...")
        
        try:
            loco = LocomotionData(dataset_path)
            
            # Compute standard metrics
            subjects = loco.get_subjects()
            tasks = loco.get_tasks()
            
            lab_metrics = []
            
            for subject in subjects[:2]:  # Process first 2 subjects
                for task in tasks[:1]:    # Process first task
                    try:
                        rom_data = loco.calculate_rom(subject, task)
                        knee_rom = np.mean(rom_data.get('knee_flexion_angle_rad', [0]))
                        lab_metrics.append(knee_rom)
                    except:
                        pass
            
            if lab_metrics:
                lab_results[lab_name] = {
                    'mean_knee_rom': np.mean(lab_metrics),
                    'std_knee_rom': np.std(lab_metrics),
                    'n_measurements': len(lab_metrics)
                }
            
            del loco
            
        except Exception as e:
            print(f"Error processing {lab_name}: {e}")
    
    # Report cross-lab comparison
    print("\\nCross-Laboratory Comparison:")
    for lab, metrics in lab_results.items():
        print(f"{lab}: {np.degrees(metrics['mean_knee_rom']):.1f}° ± {np.degrees(metrics['std_knee_rom']):.1f}° (n={metrics['n_measurements']})")

# Run example (uncomment to execute)
# validate_across_labs()
```

### Example 2: Temporal Trend Analysis

```python
def analyze_temporal_trends():
    """
    Example: Analyze trends over time or interventions.
    Demonstrates pattern for longitudinal multi-dataset analysis.
    """
    
    print("Temporal Trend Analysis")
    print("=" * 30)
    
    # Simulate time-series datasets
    time_points = {
        'Baseline': 'docs/tutorials/test_files/locomotion_data.csv',
        # In real use: 'Week_4': 'path/to/week4_data.csv',
        # In real use: 'Week_8': 'path/to/week8_data.csv',
    }
    
    trend_data = {}
    
    for time_point, dataset_path in time_points.items():
        print(f"Processing {time_point}...")
        
        try:
            loco = LocomotionData(dataset_path)
            
            # Calculate group statistics
            all_knee_rom = []
            subjects = loco.get_subjects()
            
            for subject in subjects:
                try:
                    rom_data = loco.calculate_rom(subject, 'level_walking')
                    knee_rom = np.mean(rom_data.get('knee_flexion_angle_rad', []))
                    if not np.isnan(knee_rom):
                        all_knee_rom.append(knee_rom)
                except:
                    pass
            
            if all_knee_rom:
                trend_data[time_point] = {
                    'mean': np.mean(all_knee_rom),
                    'sem': np.std(all_knee_rom) / np.sqrt(len(all_knee_rom)),
                    'n': len(all_knee_rom)
                }
            
            del loco
            
        except Exception as e:
            print(f"Error processing {time_point}: {e}")
    
    # Report trends
    print("\\nTemporal Trends:")
    for time_point, stats in trend_data.items():
        print(f"{time_point}: {np.degrees(stats['mean']):.1f}° ± {np.degrees(stats['sem']):.1f}° SEM (n={stats['n']})")

# Run example (uncomment to execute)
# analyze_temporal_trends()
```

## Best Practices

### Memory Management

1. **Process sequentially**: Load one dataset at a time
2. **Delete objects**: Use `del` to free memory immediately
3. **Cache wisely**: Cache expensive computations, not raw data
4. **Chunk large files**: Process CSV files in chunks

### Quality Control

1. **Validate compatibility**: Check column names and data formats
2. **Handle missing data**: Implement robust error handling
3. **Document assumptions**: Record processing decisions
4. **Verify results**: Cross-check with single-dataset analyses

### Reproducibility

1. **Version control**: Track dataset versions and analysis code
2. **Seed random processes**: Use `np.random.seed()` for consistency
3. **Log parameters**: Record all analysis parameters
4. **Save intermediate results**: Enable restarting from checkpoints

## Troubleshooting

### Common Issues

**Memory errors with large datasets:**
- Use chunked processing
- Process datasets sequentially
- Clear objects with `del`

**Inconsistent column names:**
- Implement name mapping dictionaries
- Validate columns before analysis
- Use `feature_constants.py` for standardization

**Mixed data formats:**
- Detect formats automatically
- Handle both parquet and CSV
- Validate data structure

**Performance bottlenecks:**
- Profile code with memory monitoring
- Cache expensive computations
- Optimize data access patterns

## Next Steps

- Explore [Statistical Analysis](../basic/metrics.md) for advanced statistical methods
- Review [Visualization](../basic/visualizations.md) for multi-dataset plotting
- Check [API Reference](../../reference/api.md) for complete function documentation

## Summary

Multi-dataset analysis enables powerful research applications while requiring careful attention to memory management and data compatibility. The patterns demonstrated here provide a foundation for sophisticated biomechanical research workflows using the locomotion data standardization framework.