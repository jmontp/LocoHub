# Troubleshooting Guide

Common issues and solutions when working with standardized locomotion data.

## Installation Issues

### Python Package Installation

!!! error "ImportError: No module named 'pandas'"
    **Problem**: Missing required Python packages
    
    **Solution**:
    ```bash
    pip install pandas matplotlib numpy pyarrow
    ```
    
    **Alternative**: Use conda
    ```bash
    conda install pandas matplotlib numpy pyarrow
    ```

!!! error "Memory Error when loading large datasets"
    **Problem**: Insufficient memory for large datasets
    
    **Solutions**:
    
    1. **Load specific columns only**:
    ```python
    columns = ['subject', 'task', 'step', 'phase_percent', 'knee_flexion_angle_ipsi_rad']
    data = pd.read_parquet('dataset.parquet', columns=columns)
    ```
    
    2. **Use chunked loading**:
    ```python
    def load_in_chunks(filepath, chunk_size=10000):
        chunks = []
        for chunk in pd.read_parquet(filepath, chunksize=chunk_size):
            processed_chunk = chunk.groupby('phase_percent').mean()
            chunks.append(processed_chunk)
        return pd.concat(chunks)
    ```

### MATLAB Issues

!!! error "Error using readtable: Unable to interpret file"
    **Problem**: MATLAB version doesn't support parquet files
    
    **Solutions**:
    
    1. **Use newer MATLAB** (R2019a or later):
    ```matlab
    data = readtable('dataset.parquet');
    ```
    
    2. **Convert to CSV first**:
    ```python
    # In Python
    import pandas as pd
    data = pd.read_parquet('dataset.parquet')
    data.to_csv('dataset.csv', index=False)
    ```
    
    ```matlab
    % In MATLAB
    data = readtable('dataset.csv');
    ```

!!! error "Out of memory error in MATLAB"
    **Problem**: Large dataset exceeds available memory
    
    **Solutions**:
    
    1. **Process in chunks**:
    ```matlab
    % Read subset of data
    opts = detectImportOptions('dataset.parquet');
    opts = setvaropts(opts, 'subject', 'Type', 'categorical');
    
    % Read specific subjects only
    data = readtable('dataset.parquet', opts);
    subject_data = data(data.subject == 'SUB01', :);
    ```
    
    2. **Use tall arrays** (if available):
    ```matlab
    tall_data = tall(readtable('dataset.parquet'));
    result = gather(groupsummary(tall_data, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad'));
    ```

## Data Loading Issues

### File Format Problems

!!! error "FileNotFoundError: No such file or directory"
    **Problem**: Incorrect file path or missing file
    
    **Solutions**:
    
    1. **Check current directory**:
    ```python
    import os
    print("Current directory:", os.getcwd())
    print("Files in directory:", os.listdir('.'))
    ```
    
    2. **Use absolute paths**:
    ```python
    data_path = '/full/path/to/dataset.parquet'
    data = pd.read_parquet(data_path)
    ```

!!! error "ValueError: Unknown file format"
    **Problem**: Unsupported file format
    
    **Solution**: Convert to supported format
    ```python
    # For CSV files
    data = pd.read_csv('dataset.csv')
    
    # For Excel files
    data = pd.read_excel('dataset.xlsx')
    
    # Save as parquet
    data.to_parquet('dataset.parquet')
    ```

### Data Structure Issues

!!! error "KeyError: 'phase_percent'"
    **Problem**: Missing required columns
    
    **Solution**: Check column names and structure
    ```python
    print("Available columns:", data.columns.tolist())
    print("Expected columns:", ['subject', 'task', 'step', 'phase_percent'])
    
    # Check if dataset is time-indexed instead of phase-indexed
    if 'time_s' in data.columns and 'phase_percent' not in data.columns:
        print("This appears to be a time-indexed dataset")
        print("Use phase-indexed version or convert to phase data")
    ```

!!! error "ValueError: Phase data does not have 150 points per cycle"
    **Problem**: Incorrect phase indexing
    
    **Solution**: Check phase indexing
    ```python
    # Check points per cycle
    points_per_cycle = data.groupby(['subject', 'task', 'step']).size()
    print("Points per cycle distribution:")
    print(points_per_cycle.value_counts())
    
    # Filter for complete cycles only
    complete_cycles = points_per_cycle[points_per_cycle == 150].index
    complete_data = data.set_index(['subject', 'task', 'step']).loc[complete_cycles].reset_index()
    ```

## Analysis Issues

### Statistical Analysis Problems

!!! error "ValueError: All values are NaN"
    **Problem**: Missing or invalid data
    
    **Solutions**:
    
    1. **Check for missing data**:
    ```python
    print("Missing data summary:")
    print(data.isnull().sum())
    
    # Remove rows with missing critical data
    clean_data = data.dropna(subset=['knee_flexion_angle_ipsi_rad'])
    ```
    
    2. **Check data ranges**:
    ```python
    import numpy as np
    
    # Check for unrealistic values
    knee_deg = np.degrees(data['knee_flexion_angle_ipsi_rad'])
    print(f"Knee angle range: {knee_deg.min():.1f}° to {knee_deg.max():.1f}°")
    
    # Flag potential outliers
    outliers = (knee_deg < -30) | (knee_deg > 150)
    print(f"Potential outliers: {outliers.sum()} points")
    ```

!!! error "RuntimeWarning: invalid value encountered in mean"
    **Problem**: Mathematical operations on invalid data
    
    **Solution**: Clean data before analysis
    ```python
    # Remove infinite and NaN values
    clean_data = data.replace([np.inf, -np.inf], np.nan).dropna()
    
    # Or use numpy functions that handle NaN
    mean_knee = np.nanmean(data['knee_flexion_angle_ipsi_rad'])
    ```

### Visualization Problems

!!! error "No such file or directory: 'plot.png'"
    **Problem**: Plot saving issues
    
    **Solution**: Check directory permissions and path
    ```python
    import os
    import matplotlib.pyplot as plt
    
    # Ensure output directory exists
    output_dir = 'plots'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save with full path
    plt.savefig(os.path.join(output_dir, 'plot.png'))
    ```

!!! error "RuntimeError: Cannot generate plot in non-GUI environment"
    **Problem**: Plotting in headless environment
    
    **Solution**: Use non-interactive backend
    ```python
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    
    # Create plot
    plt.figure()
    plt.plot(data['phase_percent'], data['knee_flexion_angle_ipsi_rad'])
    plt.savefig('plot.png')  # Must save, cannot show()
    ```

## Validation Issues

### Dataset Validation Failures

!!! error "ValidationError: Phase indexing invalid"
    **Problem**: Incorrect gait cycle structure
    
    **Solution**: Check and fix phase indexing
    ```python
    # Check phase values
    phase_summary = data.groupby(['subject', 'task', 'step'])['phase_percent'].agg(['min', 'max', 'count'])
    print(phase_summary)
    
    # Expected: min=0, max=100, count=150 for each cycle
    
    # Fix if needed (example for linear interpolation)
    fixed_data = []
    for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
        if len(group) != 150:
            print(f"Fixing cycle {subject}-{task}-{step}: {len(group)} points")
            # Re-interpolate to 150 points
            new_phase = np.linspace(0, 100, 150)
            interp_data = group.copy()
            # Interpolate other variables here...
            
    ```

!!! error "BiomechanicalError: Values outside expected range"
    **Problem**: Unrealistic biomechanical values
    
    **Solution**: Check data units and coordinate systems
    ```python
    # Check if angles are in degrees vs radians
    knee_angle = data['knee_flexion_angle_ipsi_rad']
    
    if knee_angle.max() > 10:  # Likely in degrees, not radians
        print("Converting degrees to radians")
        data['knee_flexion_angle_ipsi_rad'] = np.radians(knee_angle)
    
    # Check coordinate system convention
    print("Sample values:")
    print(f"Hip flexion: {np.degrees(data['hip_flexion_angle_ipsi_rad']).describe()}")
    print(f"Knee flexion: {np.degrees(data['knee_flexion_angle_ipsi_rad']).describe()}")
    ```

### Quality Score Issues

!!! error "QualityError: Low quality score"
    **Problem**: Dataset fails quality thresholds
    
    **Solution**: Identify and address quality issues
    ```python
    # Run detailed validation
    from validation import generate_quality_report
    
    report = generate_quality_report(data, detailed=True)
    
    print("Quality issues:")
    for issue in report['issues']:
        print(f"- {issue['type']}: {issue['description']}")
        print(f"  Affected cycles: {issue['affected_cycles']}")
        print(f"  Suggested fix: {issue['suggested_fix']}")
    ```

## Performance Issues

### Slow Data Loading

!!! warning "Data loading takes too long"
    **Problem**: Large datasets slow to load
    
    **Solutions**:
    
    1. **Use more efficient formats**:
    ```python
    # Parquet is faster than CSV
    data = pd.read_parquet('dataset.parquet')  # Fast
    
    # Avoid CSV for large datasets
    data = pd.read_csv('dataset.csv')  # Slow
    ```
    
    2. **Load only needed data**:
    ```python
    # Load specific columns
    needed_cols = ['subject', 'task', 'phase_percent', 'knee_flexion_angle_ipsi_rad']
    data = pd.read_parquet('dataset.parquet', columns=needed_cols)
    
    # Load specific subjects
    all_data = pd.read_parquet('dataset.parquet')
    subject_data = all_data[all_data['subject'].isin(['SUB01', 'SUB02'])]
    ```

### Memory Usage Issues

!!! warning "High memory usage"
    **Problem**: Dataset uses too much memory
    
    **Solutions**:
    
    1. **Optimize data types**:
    ```python
    # Check memory usage
    print(f"Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    
    # Optimize dtypes
    data['subject'] = data['subject'].astype('category')
    data['task'] = data['task'].astype('category')
    
    # Use float32 instead of float64 if precision allows
    for col in ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']:
        data[col] = data[col].astype('float32')
    
    print(f"Optimized memory: {data.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    ```
    
    2. **Process in chunks**:
    ```python
    def process_large_dataset(filepath, chunk_size=10000):
        results = []
        
        # Process in chunks
        for chunk in pd.read_parquet(filepath, chunksize=chunk_size):
            # Process each chunk
            chunk_result = chunk.groupby('phase_percent').mean()
            results.append(chunk_result)
        
        # Combine results
        return pd.concat(results).groupby(level=0).mean()
    ```

## Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide** for your specific issue
2. **Verify your data format** matches requirements
3. **Test with sample data** to isolate the problem
4. **Check software versions** (Python, MATLAB, packages)

### How to Report Issues

When reporting issues, include:

1. **Complete error message** (copy-paste the full traceback)
2. **Minimal example** that reproduces the problem
3. **Environment details** (OS, Python/MATLAB version, package versions)
4. **Data description** (size, format, source)

**Example Issue Report**:
```
**Problem**: Getting KeyError when loading dataset

**Error Message**:
KeyError: 'phase_percent'

**Code**:
```python
data = pd.read_parquet('my_dataset.parquet')
avg_pattern = data.groupby('phase_percent').mean()
```

**Environment**:
- OS: Windows 10
- Python: 3.9.7
- pandas: 1.3.3
- Dataset: 10MB parquet file from lab motion capture

**Additional Info**:
Dataset columns: ['time_s', 'subject', 'task', 'knee_angle', ...]
```

### Community Resources

- **GitHub Issues**: [Report bugs and request features](https://github.com/your-org/locomotion-data-standardization/issues)
- **Discussions**: [Ask questions and share tips](https://github.com/your-org/locomotion-data-standardization/discussions)
- **Documentation**: [Complete user guide](../user_guide/)
- **Tutorials**: [Step-by-step examples](../tutorials/)

### Getting Support

1. **Search existing issues** on GitHub first
2. **Check the FAQ** below for common questions
3. **Post in discussions** for usage questions
4. **Create an issue** for bugs or feature requests
5. **Email support**: [support@locomotion-standardization.org](mailto:support@locomotion-standardization.org)

## Frequently Asked Questions

### Data Format Questions

!!! question "Can I use time-indexed data instead of phase-indexed?"
    Yes! Use time-indexed datasets (`*_time.parquet`) for temporal analysis. Phase-indexed data (`*_phase.parquet`) is better for cross-subject comparison and averaging.

!!! question "What if my dataset doesn't have exactly 150 points per cycle?"
    This is expected for time-indexed data. For phase-indexed data, all cycles must have exactly 150 points. Use our conversion tools to create phase-indexed versions.

!!! question "Can I add custom variables to standardized datasets?"
    Yes, but follow the naming convention: `{joint}_{motion}_{measurement}_{side}_{unit}`. Document any custom variables clearly.

### Analysis Questions

!!! question "How do I handle missing data?"
    Remove cycles with >5% missing data. For smaller gaps, document the missing data and consider interpolation only if biomechanically appropriate.

!!! question "What statistical tests should I use?"
    For comparing tasks: ANOVA for multiple groups, t-tests for pairs. For repeated measures: use mixed-effects models. Always check assumptions first.

!!! question "How do I cite the datasets?"
    Each dataset has a specific citation format. Check the dataset documentation for the correct citation and DOI.

### Technical Questions

!!! question "Why is my analysis slow?"
    Common causes: loading unnecessary columns, inefficient groupby operations, large datasets in memory. See [Performance Issues](#performance-issues) above.

!!! question "Can I use other programming languages?"
    The datasets are in standard formats (parquet, CSV) that work with R, Julia, etc. Core validation tools are currently Python/MATLAB only.

!!! question "How do I convert my lab's data format?"
    See the [Contributor Guide](../contributor_guide/) for conversion tools and examples for common formats (C3D, MAT files, etc.).

---

*Still having issues? Don't hesitate to [contact us](mailto:support@locomotion-standardization.org) or [open an issue](https://github.com/your-org/locomotion-data-standardization/issues).*