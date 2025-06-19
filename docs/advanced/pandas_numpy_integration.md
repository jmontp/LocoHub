# Pandas/NumPy Integration Guide

**Advanced integration patterns for pandas and NumPy workflows**

## Overview

This guide demonstrates how to integrate the locomotion data platform with pandas and NumPy for advanced data analysis, statistical computing, and research workflows.

## Quick Start

```python
from lib.core.locomotion_analysis import LocomotionData
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load data
loco = LocomotionData('dataset_phase.parquet')

# Get 3D data for analysis
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
print(f"Data shape: {data_3d.shape}")  # (n_cycles, 150, n_features)
```

## Data Extraction Patterns

### Converting to Pandas DataFrames

```python
def locomotion_to_dataframe(loco_data, subject, task, features=None):
    """Convert LocomotionData to tidy pandas DataFrame."""
    
    data_3d, feature_names = loco_data.get_cycles(subject, task, features)
    if data_3d is None:
        return pd.DataFrame()
    
    # Reshape to long format
    n_cycles, n_phases, n_features = data_3d.shape
    
    # Create index arrays
    cycle_ids = np.repeat(range(n_cycles), n_phases)
    phases = np.tile(range(n_phases), n_cycles)
    
    # Create base DataFrame
    df_list = []
    for feat_idx, feature in enumerate(feature_names):
        values = data_3d[:, :, feat_idx].flatten()
        df_feat = pd.DataFrame({
            'subject': subject,
            'task': task,
            'cycle': cycle_ids,
            'phase': phases,
            'phase_percent': phases * (100/149),  # Convert to percentage
            'variable': feature,
            'value': values
        })
        df_list.append(df_feat)
    
    return pd.concat(df_list, ignore_index=True)

# Usage
df = locomotion_to_dataframe(loco, 'SUB01', 'normal_walk')
print(df.head())
```

### Multi-Subject Data Aggregation

```python
def create_population_dataframe(loco_data, task, features=None):
    """Create population-level DataFrame from all subjects."""
    
    subjects = loco_data.get_subjects()
    all_dfs = []
    
    for subject in subjects:
        df_subject = locomotion_to_dataframe(loco_data, subject, task, features)
        if not df_subject.empty:
            all_dfs.append(df_subject)
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame()

# Create population dataset
population_df = create_population_dataframe(loco, 'normal_walk')
print(f"Population data: {len(population_df)} rows, {population_df['subject'].nunique()} subjects")
```

## Statistical Analysis with Pandas

### Descriptive Statistics

```python
# Summary statistics by variable
stats_summary = population_df.groupby('variable')['value'].agg([
    'count', 'mean', 'std', 'min', 'max', 
    lambda x: x.quantile(0.25),  # Q1
    lambda x: x.quantile(0.75)   # Q3
]).round(4)

stats_summary.columns = ['count', 'mean', 'std', 'min', 'max', 'q25', 'q75']
print(stats_summary)
```

### Phase-Based Analysis

```python
# Analyze patterns at specific gait phases
key_phases = [0, 25, 50, 75]  # Heel strike, loading, mid-stance, push-off

phase_analysis = population_df[
    population_df['phase'].isin(key_phases)
].groupby(['variable', 'phase'])['value'].agg(['mean', 'std']).reset_index()

# Pivot for easier viewing
phase_pivot = phase_analysis.pivot(index='variable', columns='phase', values='mean')
print("Mean values at key gait phases:")
print(phase_pivot)
```

### Cross-Correlation Analysis

```python
def calculate_feature_correlations(loco_data, subject, task):
    """Calculate correlation matrix between features."""
    
    data_3d, features = loco_data.get_cycles(subject, task)
    if data_3d is None:
        return pd.DataFrame()
    
    # Reshape to (n_observations, n_features)
    n_cycles, n_phases, n_features = data_3d.shape
    data_2d = data_3d.reshape(n_cycles * n_phases, n_features)
    
    # Create correlation matrix
    corr_matrix = pd.DataFrame(
        np.corrcoef(data_2d.T),
        index=features,
        columns=features
    )
    
    return corr_matrix

# Calculate correlations
corr_matrix = calculate_feature_correlations(loco, 'SUB01', 'normal_walk')
print("Feature correlations:")
print(corr_matrix.round(3))

# Visualize correlation matrix
import seaborn as sns
plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
            square=True, fmt='.2f')
plt.title('Feature Correlation Matrix')
plt.tight_layout()
plt.show()
```

## Advanced NumPy Operations

### Gait Cycle Alignment

```python
def align_gait_cycles(data_3d, alignment_feature_idx=2):
    """Align gait cycles based on peak of specified feature."""
    
    n_cycles, n_phases, n_features = data_3d.shape
    aligned_data = np.zeros_like(data_3d)
    
    for cycle_idx in range(n_cycles):
        # Find peak in alignment feature
        cycle_data = data_3d[cycle_idx, :, alignment_feature_idx]
        peak_idx = np.argmax(cycle_data)
        
        # Calculate shift to align peak at 50% gait cycle
        target_peak = n_phases // 2
        shift = target_peak - peak_idx
        
        # Apply circular shift to all features
        for feat_idx in range(n_features):
            aligned_data[cycle_idx, :, feat_idx] = np.roll(
                data_3d[cycle_idx, :, feat_idx], shift
            )
    
    return aligned_data

# Usage
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
aligned_data = align_gait_cycles(data_3d, alignment_feature_idx=2)  # Align on knee angle

print(f"Original shape: {data_3d.shape}")
print(f"Aligned shape: {aligned_data.shape}")
```

### Principal Component Analysis

```python
def gait_pca_analysis(data_3d, n_components=5):
    """Perform PCA on gait cycle data."""
    
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    
    n_cycles, n_phases, n_features = data_3d.shape
    
    # Reshape to feature matrix
    X = data_3d.reshape(n_cycles, n_phases * n_features)
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Apply PCA
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)
    
    # Calculate explained variance
    explained_var = pca.explained_variance_ratio_
    cumulative_var = np.cumsum(explained_var)
    
    return {
        'transformed_data': X_pca,
        'explained_variance': explained_var,
        'cumulative_variance': cumulative_var,
        'components': pca.components_,
        'scaler': scaler,
        'pca_model': pca
    }

# Perform PCA
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
pca_results = gait_pca_analysis(data_3d)

print("Explained variance by component:")
for i, var in enumerate(pca_results['explained_variance']):
    print(f"PC{i+1}: {var:.3f} ({var*100:.1f}%)")

print(f"\nCumulative variance: {pca_results['cumulative_variance']}")
```

### Gait Variability Analysis

```python
def calculate_gait_variability(data_3d, method='coefficient_variation'):
    """Calculate gait variability metrics."""
    
    n_cycles, n_phases, n_features = data_3d.shape
    
    if method == 'coefficient_variation':
        # Calculate CV at each phase point
        means = np.mean(data_3d, axis=0)  # (n_phases, n_features)
        stds = np.std(data_3d, axis=0)    # (n_phases, n_features)
        
        # Avoid division by zero
        cv = np.divide(stds, means, out=np.zeros_like(stds), where=means!=0)
        variability = np.mean(cv, axis=0)  # Average CV across phases
        
    elif method == 'rmse':
        # Root mean square error from mean pattern
        mean_pattern = np.mean(data_3d, axis=0)
        squared_errors = (data_3d - mean_pattern[np.newaxis, :, :]) ** 2
        rmse = np.sqrt(np.mean(squared_errors, axis=(0, 1)))
        variability = rmse
        
    elif method == 'range':
        # Range (max - min) across cycles at each phase
        ranges = np.max(data_3d, axis=0) - np.min(data_3d, axis=0)
        variability = np.mean(ranges, axis=0)
    
    return variability

# Calculate variability for different methods
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')

cv_variability = calculate_gait_variability(data_3d, 'coefficient_variation')
rmse_variability = calculate_gait_variability(data_3d, 'rmse')
range_variability = calculate_gait_variability(data_3d, 'range')

# Create comparison DataFrame
variability_df = pd.DataFrame({
    'feature': features,
    'CV': cv_variability,
    'RMSE': rmse_variability,
    'Range': range_variability
})

print("Gait variability metrics:")
print(variability_df.round(4))
```

## Time-Frequency Analysis

### Gait Cycle Spectral Analysis

```python
def gait_spectral_analysis(data_3d, sampling_rate=150):
    """Perform spectral analysis on gait cycles."""
    
    from scipy import signal
    
    n_cycles, n_phases, n_features = data_3d.shape
    spectral_results = {}
    
    for feat_idx, feature in enumerate(features):
        # Concatenate all cycles for this feature
        time_series = data_3d[:, :, feat_idx].flatten()
        
        # Calculate power spectral density
        frequencies, psd = signal.welch(
            time_series, 
            fs=sampling_rate,
            nperseg=min(256, len(time_series)//4)
        )
        
        # Find dominant frequency
        dominant_freq_idx = np.argmax(psd[1:]) + 1  # Exclude DC component
        dominant_freq = frequencies[dominant_freq_idx]
        
        spectral_results[feature] = {
            'frequencies': frequencies,
            'psd': psd,
            'dominant_frequency': dominant_freq,
            'total_power': np.trapz(psd, frequencies)
        }
    
    return spectral_results

# Perform spectral analysis
spectral_results = gait_spectral_analysis(data_3d)

# Plot power spectral density
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

for idx, (feature, results) in enumerate(spectral_results.items()):
    if idx < len(axes):
        axes[idx].semilogy(results['frequencies'], results['psd'])
        axes[idx].set_title(f"{feature.replace('_', ' ')}")
        axes[idx].set_xlabel('Frequency (Hz)')
        axes[idx].set_ylabel('PSD')
        axes[idx].grid(True)
        
        # Mark dominant frequency
        axes[idx].axvline(results['dominant_frequency'], 
                         color='red', linestyle='--', 
                         label=f'Dominant: {results["dominant_frequency"]:.2f} Hz')
        axes[idx].legend()

plt.tight_layout()
plt.show()
```

## Data Export and Interchange

### Export to Standard Formats

```python
def export_to_csv(loco_data, output_path, subjects=None, tasks=None):
    """Export locomotion data to CSV format."""
    
    if subjects is None:
        subjects = loco_data.get_subjects()
    if tasks is None:
        tasks = loco_data.get_tasks()
    
    all_data = []
    
    for subject in subjects:
        for task in tasks:
            df = locomotion_to_dataframe(loco_data, subject, task)
            if not df.empty:
                all_data.append(df)
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df.to_csv(output_path, index=False)
        print(f"Exported {len(combined_df)} rows to {output_path}")
    else:
        print("No data to export")

# Export data
export_to_csv(loco, 'gait_data_export.csv', 
              subjects=['SUB01', 'SUB02'], 
              tasks=['normal_walk'])
```

### Create Analysis Pipelines

```python
class GaitAnalysisPipeline:
    """Reusable gait analysis pipeline using pandas/numpy."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        self.results = {}
    
    def run_subject_analysis(self, subject, task):
        """Run complete analysis for a subject-task combination."""
        
        # Extract data
        data_3d, features = self.loco_data.get_cycles(subject, task)
        if data_3d is None:
            return None
        
        # Basic statistics
        stats = self.loco_data.get_summary_statistics(subject, task)
        
        # ROM calculation
        rom_data = self.loco_data.calculate_rom(subject, task)
        
        # Variability analysis
        variability = calculate_gait_variability(data_3d, 'coefficient_variation')
        
        # Validation
        valid_mask = self.loco_data.validate_cycles(subject, task)
        
        # Compile results
        results = {
            'subject': subject,
            'task': task,
            'n_cycles': data_3d.shape[0],
            'valid_cycles': valid_mask.sum(),
            'data_quality': valid_mask.mean(),
            'stats': stats,
            'rom': rom_data,
            'variability': dict(zip(features, variability))
        }
        
        return results
    
    def run_population_analysis(self, task):
        """Run analysis across all subjects for a task."""
        
        subjects = self.loco_data.get_subjects()
        subject_results = []
        
        for subject in subjects:
            result = self.run_subject_analysis(subject, task)
            if result:
                subject_results.append(result)
        
        if not subject_results:
            return None
        
        # Aggregate population statistics
        population_stats = {
            'n_subjects': len(subject_results),
            'total_cycles': sum(r['n_cycles'] for r in subject_results),
            'average_quality': np.mean([r['data_quality'] for r in subject_results]),
            'subject_results': subject_results
        }
        
        return population_stats

# Usage
pipeline = GaitAnalysisPipeline(loco)

# Analyze single subject
subject_result = pipeline.run_subject_analysis('SUB01', 'normal_walk')
if subject_result:
    print(f"Subject {subject_result['subject']} - {subject_result['task']}:")
    print(f"  Cycles: {subject_result['n_cycles']} ({subject_result['valid_cycles']} valid)")
    print(f"  Quality: {subject_result['data_quality']:.2%}")

# Analyze population
population_result = pipeline.run_population_analysis('normal_walk')
if population_result:
    print(f"\nPopulation analysis for normal_walk:")
    print(f"  Subjects: {population_result['n_subjects']}")
    print(f"  Total cycles: {population_result['total_cycles']}")
    print(f"  Average quality: {population_result['average_quality']:.2%}")
```

## Performance Optimization

### Vectorized Operations

```python
def vectorized_rom_calculation(data_3d):
    """Efficiently calculate ROM using vectorized operations."""
    
    # Calculate ROM for all cycles and features at once
    cycle_max = np.max(data_3d, axis=1)  # (n_cycles, n_features)
    cycle_min = np.min(data_3d, axis=1)  # (n_cycles, n_features)
    rom_per_cycle = cycle_max - cycle_min
    
    return rom_per_cycle

# Compare performance
import time

data_3d, features = loco.get_cycles('SUB01', 'normal_walk')

# Vectorized approach
start_time = time.time()
rom_vectorized = vectorized_rom_calculation(data_3d)
vectorized_time = time.time() - start_time

# Loop-based approach
start_time = time.time()
rom_loop = np.zeros((data_3d.shape[0], data_3d.shape[2]))
for cycle in range(data_3d.shape[0]):
    for feature in range(data_3d.shape[2]):
        rom_loop[cycle, feature] = np.max(data_3d[cycle, :, feature]) - np.min(data_3d[cycle, :, feature])
loop_time = time.time() - start_time

print(f"Vectorized time: {vectorized_time:.4f}s")
print(f"Loop time: {loop_time:.4f}s")
print(f"Speedup: {loop_time/vectorized_time:.1f}x")
```

### Memory-Efficient Processing

```python
def process_large_dataset_chunked(loco_data, chunk_size=10):
    """Process large datasets in chunks to manage memory."""
    
    subjects = loco_data.get_subjects()
    tasks = loco_data.get_tasks()
    
    results = []
    
    for i in range(0, len(subjects), chunk_size):
        subject_chunk = subjects[i:i+chunk_size]
        
        for subject in subject_chunk:
            for task in tasks:
                # Process individual subject-task
                try:
                    stats = loco_data.get_summary_statistics(subject, task)
                    if not stats.empty:
                        result = {
                            'subject': subject,
                            'task': task,
                            'mean_knee_angle': stats.loc['knee_flexion_angle_ipsi_rad', 'mean'],
                            'std_knee_angle': stats.loc['knee_flexion_angle_ipsi_rad', 'std']
                        }
                        results.append(result)
                except Exception as e:
                    print(f"Error processing {subject}-{task}: {e}")
        
        # Optional: save intermediate results
        if i % (chunk_size * 5) == 0:
            print(f"Processed {i+len(subject_chunk)}/{len(subjects)} subjects")
    
    return pd.DataFrame(results)

# Process in chunks
chunk_results = process_large_dataset_chunked(loco, chunk_size=5)
print(f"Processed {len(chunk_results)} subject-task combinations")
```

This guide provides comprehensive patterns for integrating the locomotion data platform with pandas and NumPy for advanced data analysis and research workflows.