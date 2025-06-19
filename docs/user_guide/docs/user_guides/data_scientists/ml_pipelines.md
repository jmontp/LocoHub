# ML Pipelines for Locomotion Data

Machine learning workflows for biomechanical analysis using standardized locomotion datasets. This guide focuses on memory-safe operations, feature extraction patterns, and scikit-learn integration.

## Quick Start

```python
import numpy as np
import pandas as pd
from locomotion_analysis import LocomotionData
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# Load standardized locomotion data
loco = LocomotionData('gait_data.parquet')

# Basic feature extraction
features = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
data_3d, feature_names = loco.get_cycles('SUB01', 'level_walking', features)
```

## Core Concepts

### 3D Data Structure
Locomotion data is structured as 3D arrays: `(n_cycles, 150_phases, n_features)`

```python
# Understanding the data structure
print(f"Data shape: {data_3d.shape}")
# Output: Data shape: (10, 150, 2)  # 10 cycles, 150 phase points, 2 features

# Access individual cycles
cycle_1 = data_3d[0, :, :]  # Shape: (150, 2)

# Access specific features across all cycles
knee_angles = data_3d[:, :, 0]  # Shape: (10, 150)
```

### Memory-Safe Operations
Always use generators and chunking for large datasets:

```python
def process_subjects_batch(loco, subjects, batch_size=10):
    """Process subjects in memory-safe batches."""
    for i in range(0, len(subjects), batch_size):
        batch = subjects[i:i + batch_size]
        yield [(subj, loco.get_cycles(subj, 'level_walking')) for subj in batch]

# Usage
subjects = loco.get_subjects()
for batch in process_subjects_batch(loco, subjects[:50]):  # First 50 subjects
    # Process batch
    pass
```

## Feature Extraction Patterns

### 1. Statistical Features

Extract statistical summaries from phase-normalized cycles:

```python
def extract_statistical_features(data_3d, feature_names):
    """Extract comprehensive statistical features from 3D gait data."""
    n_cycles, n_phases, n_features = data_3d.shape
    
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        feat_data = data_3d[:, :, i]  # (n_cycles, 150)
        
        # Cycle-level statistics
        features[f'{feature_name}_mean'] = np.mean(feat_data, axis=1)
        features[f'{feature_name}_std'] = np.std(feat_data, axis=1)
        features[f'{feature_name}_range'] = np.ptp(feat_data, axis=1)
        features[f'{feature_name}_max'] = np.max(feat_data, axis=1)
        features[f'{feature_name}_min'] = np.min(feat_data, axis=1)
        
        # Phase-specific values (key gait events)
        features[f'{feature_name}_heel_strike'] = feat_data[:, 0]    # 0% phase
        features[f'{feature_name}_toe_off'] = feat_data[:, 75]       # ~50% phase
        features[f'{feature_name}_mid_swing'] = feat_data[:, 112]    # ~75% phase
        
        # Symmetry measures (if contra/ipsi pairs available)
        if 'ipsi' in feature_name:
            contra_name = feature_name.replace('ipsi', 'contra')
            if contra_name in feature_names:
                j = feature_names.index(contra_name)
                contra_data = data_3d[:, :, j]
                features[f'{feature_name}_symmetry'] = np.corrcoef(
                    feat_data.mean(axis=0), contra_data.mean(axis=0)
                )[0, 1]
    
    return pd.DataFrame(features)

# Usage
statistical_features = extract_statistical_features(data_3d, feature_names)
print(f"Extracted {statistical_features.shape[1]} statistical features")
```

### 2. Principal Component Features

Extract PCA features from phase-normalized patterns:

```python
def extract_pca_features(data_3d, n_components=5):
    """Extract PCA features from gait cycles."""
    n_cycles, n_phases, n_features = data_3d.shape
    
    # Reshape to 2D: (n_cycles, n_phases * n_features)
    data_2d = data_3d.reshape(n_cycles, -1)
    
    # Apply PCA
    pca = PCA(n_components=n_components)
    pca_features = pca.fit_transform(data_2d)
    
    # Create feature DataFrame
    feature_names = [f'PC{i+1}' for i in range(n_components)]
    pca_df = pd.DataFrame(pca_features, columns=feature_names)
    
    print(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")
    
    return pca_df, pca

# Usage
pca_features, pca_model = extract_pca_features(data_3d, n_components=3)
```

### 3. Time-Series Features

Extract time-series specific features:

```python
def extract_temporal_features(data_3d, feature_names):
    """Extract temporal features from gait cycles."""
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        feat_data = data_3d[:, :, i]  # (n_cycles, 150)
        
        # Peak detection
        for cycle_idx in range(feat_data.shape[0]):
            cycle = feat_data[cycle_idx, :]
            
            # Find peaks and valleys
            peaks = []
            valleys = []
            for j in range(1, len(cycle) - 1):
                if cycle[j] > cycle[j-1] and cycle[j] > cycle[j+1]:
                    peaks.append((j, cycle[j]))
                elif cycle[j] < cycle[j-1] and cycle[j] < cycle[j+1]:
                    valleys.append((j, cycle[j]))
            
            features.setdefault(f'{feature_name}_n_peaks', []).append(len(peaks))
            features.setdefault(f'{feature_name}_n_valleys', []).append(len(valleys))
            
            # Peak timing and magnitude
            if peaks:
                max_peak_phase, max_peak_val = max(peaks, key=lambda x: x[1])
                features.setdefault(f'{feature_name}_max_peak_phase', []).append(max_peak_phase)
                features.setdefault(f'{feature_name}_max_peak_value', []).append(max_peak_val)
            else:
                features.setdefault(f'{feature_name}_max_peak_phase', []).append(np.nan)
                features.setdefault(f'{feature_name}_max_peak_value', []).append(np.nan)
    
    return pd.DataFrame(features)

# Usage
temporal_features = extract_temporal_features(data_3d, feature_names)
```

## Classification Workflows

### 1. Task Classification

Classify locomotion tasks based on gait patterns:

```python
def build_task_classifier(loco, subjects, target_tasks=['level_walking', 'incline_walking']):
    """Build a classifier to distinguish between locomotion tasks."""
    
    X_list = []
    y_list = []
    
    # Extract features for each subject and task
    for subject in subjects[:20]:  # Memory-safe: limit subjects
        for task in target_tasks:
            try:
                # Get cycles data
                data_3d, features = loco.get_cycles(subject, task)
                if data_3d is None or data_3d.shape[0] < 3:
                    continue
                
                # Extract statistical features for each cycle
                stat_features = extract_statistical_features(data_3d, features)
                
                # Add to dataset
                X_list.append(stat_features)
                y_list.extend([task] * len(stat_features))
                
            except Exception as e:
                print(f"Skipping {subject}-{task}: {e}")
                continue
    
    # Combine all features
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Build pipeline
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    
    # Train model
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    train_score = pipeline.score(X_train, y_train)
    test_score = pipeline.score(X_test, y_test)
    
    print(f"Task Classification Results:")
    print(f"Training accuracy: {train_score:.3f}")
    print(f"Test accuracy: {test_score:.3f}")
    
    return pipeline, X_test, y_test

# Usage
subjects = loco.get_subjects()
classifier, X_test, y_test = build_task_classifier(loco, subjects)
```

### 2. Outlier Detection

Identify anomalous gait cycles:

```python
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report

def detect_gait_outliers(loco, subject, task):
    """Detect outlier gait cycles using Isolation Forest."""
    
    # Get data
    data_3d, features = loco.get_cycles(subject, task)
    if data_3d is None:
        return None
    
    # Extract features
    stat_features = extract_statistical_features(data_3d, features)
    
    # Apply outlier detection
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    outlier_labels = iso_forest.fit_predict(stat_features)
    
    # Compare with LocomotionData's validation
    valid_mask = loco.validate_cycles(subject, task)
    
    # Results
    results = {
        'n_cycles': len(outlier_labels),
        'ml_outliers': np.sum(outlier_labels == -1),
        'validation_outliers': np.sum(~valid_mask),
        'outlier_labels': outlier_labels,
        'validation_mask': valid_mask
    }
    
    print(f"Outlier Detection for {subject}-{task}:")
    print(f"  ML detected: {results['ml_outliers']}/{results['n_cycles']} outliers")
    print(f"  Validation detected: {results['validation_outliers']}/{results['n_cycles']} outliers")
    
    return results

# Usage
outlier_results = detect_gait_outliers(loco, 'SUB01', 'level_walking')
```

## Regression Workflows

### 1. Biomechanical Parameter Prediction

Predict biomechanical parameters from gait patterns:

```python
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

def predict_knee_moments_from_kinematics(loco, subjects):
    """Predict knee moments from kinematic patterns."""
    
    X_list = []
    y_list = []
    
    kinematic_features = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
    kinetic_target = 'knee_flexion_moment_ipsi_Nm'
    
    for subject in subjects[:15]:  # Memory-safe subset
        try:
            # Get kinematic data
            kin_data, kin_names = loco.get_cycles(subject, 'level_walking', kinematic_features)
            # Get kinetic target
            kin_target, _ = loco.get_cycles(subject, 'level_walking', [kinetic_target])
            
            if kin_data is None or kin_target is None:
                continue
            
            # Extract features from kinematics
            kin_features = extract_statistical_features(kin_data, kin_names)
            
            # Target: max knee moment per cycle
            target_values = np.max(kin_target[:, :, 0], axis=1)
            
            X_list.append(kin_features)
            y_list.extend(target_values)
            
        except Exception as e:
            print(f"Skipping {subject}: {e}")
            continue
    
    # Combine data
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    
    # Split and train
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Ridge regression pipeline
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('regressor', Ridge(alpha=1.0))
    ])
    
    pipeline.fit(X_train, y_train)
    
    # Predictions
    y_pred = pipeline.predict(X_test)
    
    # Evaluate
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Knee Moment Prediction Results:")
    print(f"MSE: {mse:.3f}")
    print(f"R²: {r2:.3f}")
    
    return pipeline, X_test, y_test, y_pred

# Usage
subjects = loco.get_subjects()
moment_predictor, X_test, y_test, y_pred = predict_knee_moments_from_kinematics(loco, subjects)
```

### 2. Cross-Subject Validation

Evaluate model generalization across subjects:

```python
from sklearn.model_selection import LeaveOneGroupOut

def cross_subject_validation(loco, subjects, task='level_walking'):
    """Perform leave-one-subject-out cross-validation."""
    
    X_list = []
    y_list = []
    groups = []
    
    # Collect data from all subjects
    for subject in subjects[:10]:  # Memory-safe subset
        try:
            data_3d, features = loco.get_cycles(subject, task)
            if data_3d is None:
                continue
            
            # Extract features
            stat_features = extract_statistical_features(data_3d, features)
            
            # Create binary classification: normal vs outlier cycles
            valid_mask = loco.validate_cycles(subject, task)
            
            X_list.append(stat_features)
            y_list.extend(valid_mask.astype(int))
            groups.extend([subject] * len(stat_features))
            
        except Exception as e:
            print(f"Skipping {subject}: {e}")
            continue
    
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    groups = np.array(groups)
    
    # Leave-one-subject-out cross-validation
    logo = LeaveOneGroupOut()
    scores = []
    
    for train_idx, test_idx in logo.split(X, y, groups):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        # Train model
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(n_estimators=50, random_state=42))
        ])
        
        pipeline.fit(X_train, y_train)
        score = pipeline.score(X_test, y_test)
        scores.append(score)
    
    print(f"Cross-Subject Validation Results:")
    print(f"Mean accuracy: {np.mean(scores):.3f} ± {np.std(scores):.3f}")
    print(f"Subject-wise scores: {[f'{s:.3f}' for s in scores]}")
    
    return scores

# Usage
subjects = loco.get_subjects()
cv_scores = cross_subject_validation(loco, subjects)
```

## Clustering and Dimensionality Reduction

### 1. Gait Pattern Clustering

Identify distinct gait patterns:

```python
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

def cluster_gait_patterns(loco, subjects, task='level_walking', n_clusters=3):
    """Cluster gait patterns using K-means."""
    
    X_list = []
    subject_labels = []
    
    # Collect data
    for subject in subjects[:20]:  # Memory-safe subset
        try:
            data_3d, features = loco.get_cycles(subject, task)
            if data_3d is None or data_3d.shape[0] < 5:
                continue
            
            # Use PCA features for clustering
            pca_features, _ = extract_pca_features(data_3d, n_components=10)
            
            X_list.append(pca_features)
            subject_labels.extend([subject] * len(pca_features))
            
        except Exception as e:
            print(f"Skipping {subject}: {e}")
            continue
    
    X = pd.concat(X_list, ignore_index=True)
    
    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(X)
    
    # t-SNE for visualization
    tsne = TSNE(n_components=2, random_state=42, perplexity=30)
    X_embedded = tsne.fit_transform(X)
    
    # Plot results
    plt.figure(figsize=(12, 5))
    
    # Clustering results
    plt.subplot(1, 2, 1)
    scatter = plt.scatter(X_embedded[:, 0], X_embedded[:, 1], c=cluster_labels, cmap='tab10')
    plt.title(f'Gait Pattern Clusters (n={n_clusters})')
    plt.xlabel('t-SNE 1')
    plt.ylabel('t-SNE 2')
    plt.colorbar(scatter)
    
    # Subject distribution
    plt.subplot(1, 2, 2)
    unique_subjects = list(set(subject_labels))
    subject_colors = {subj: i for i, subj in enumerate(unique_subjects)}
    colors = [subject_colors[subj] for subj in subject_labels]
    scatter2 = plt.scatter(X_embedded[:, 0], X_embedded[:, 1], c=colors, cmap='tab20')
    plt.title('Subject Distribution')
    plt.xlabel('t-SNE 1')
    plt.ylabel('t-SNE 2')
    
    plt.tight_layout()
    plt.show()
    
    # Cluster statistics
    print(f"Clustering Results:")
    print(f"Silhouette score: {silhouette_score(X, cluster_labels):.3f}")
    for i in range(n_clusters):
        cluster_size = np.sum(cluster_labels == i)
        print(f"Cluster {i}: {cluster_size} cycles ({cluster_size/len(cluster_labels)*100:.1f}%)")
    
    return cluster_labels, X_embedded

# Usage (if matplotlib available)
if MATPLOTLIB_AVAILABLE:
    subjects = loco.get_subjects()
    clusters, embedding = cluster_gait_patterns(loco, subjects)
```

## Memory Optimization Tips

### 1. Batch Processing

```python
def process_large_dataset_batches(data_path, batch_size=1000):
    """Process large datasets in memory-safe batches."""
    
    # Read dataset info without loading full data
    df_info = pd.read_parquet(data_path, columns=['subject', 'task'])
    subjects = df_info['subject'].unique()
    
    for i in range(0, len(subjects), batch_size):
        batch_subjects = subjects[i:i + batch_size]
        
        # Load only needed subjects
        batch_mask = df_info['subject'].isin(batch_subjects)
        batch_data = pd.read_parquet(data_path)[batch_mask]
        
        # Process batch
        loco_batch = LocomotionData(batch_data)
        
        # Your ML pipeline here
        yield loco_batch
        
        # Clear memory
        del loco_batch, batch_data
```

### 2. Feature Caching

```python
def cache_extracted_features(loco, subjects, cache_file='features_cache.parquet'):
    """Cache extracted features to avoid recomputation."""
    
    try:
        # Try to load cached features
        cached_features = pd.read_parquet(cache_file)
        print(f"Loaded {len(cached_features)} cached features")
        return cached_features
    except FileNotFoundError:
        pass
    
    # Extract features fresh
    feature_list = []
    
    for subject in subjects:
        for task in loco.get_tasks():
            try:
                data_3d, features = loco.get_cycles(subject, task)
                if data_3d is None:
                    continue
                
                stat_features = extract_statistical_features(data_3d, features)
                stat_features['subject'] = subject
                stat_features['task'] = task
                
                feature_list.append(stat_features)
                
            except Exception as e:
                continue
    
    # Combine and cache
    all_features = pd.concat(feature_list, ignore_index=True)
    all_features.to_parquet(cache_file)
    
    print(f"Cached {len(all_features)} features to {cache_file}")
    return all_features
```

## Integration with Common ML Libraries

### Scikit-learn Integration

The examples above demonstrate extensive scikit-learn integration. Key patterns:

- **Pipelines**: Always use `Pipeline` for preprocessing + model
- **Cross-validation**: Use `LeaveOneGroupOut` for subject-wise CV
- **Feature Selection**: Use `SelectKBest` or `RFE` for high-dimensional features

### PyTorch Integration

```python
import torch
from torch.utils.data import Dataset, DataLoader

class GaitDataset(Dataset):
    """PyTorch dataset for gait cycle data."""
    
    def __init__(self, data_3d, labels):
        self.data = torch.FloatTensor(data_3d)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx], self.labels[idx]

# Usage
data_3d, _ = loco.get_cycles('SUB01', 'level_walking')
labels = np.random.randint(0, 2, size=data_3d.shape[0])  # Example labels

dataset = GaitDataset(data_3d, labels)
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
```

## Best Practices

1. **Memory Management**: Always use small test datasets first, then scale up
2. **Feature Engineering**: Focus on biomechanically meaningful features
3. **Cross-Validation**: Use subject-wise splits to avoid data leakage
4. **Validation**: Compare ML results with domain-specific validation
5. **Reproducibility**: Set random seeds and version control feature extraction code

## Next Steps

- **Advanced Features**: Time-frequency analysis, biomechanical constraints
- **Deep Learning**: LSTM/CNN models for sequential gait data  
- **Multi-modal**: Combine kinematics, kinetics, and EMG data
- **Population Studies**: Large-scale analysis across demographics

For more advanced workflows, see the [research workflows guide](../researchers/analysis_workflows.md) and [publication plots guide](../researchers/publication_plots.md).