# Machine Learning Pipeline Integration Guide

**Complete guide for integrating locomotion data with ML frameworks and research pipelines**

## Overview

This guide demonstrates how to integrate the locomotion data platform with popular machine learning frameworks including scikit-learn, TensorFlow, and PyTorch for gait analysis, prediction, and classification tasks.

## Quick Start

```python
from lib.core.locomotion_analysis import LocomotionData
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

# Load and prepare data
loco = LocomotionData('dataset_phase.parquet')
X, y, subjects = prepare_ml_features(loco, target='task')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
```

## Feature Engineering

### Gait Cycle Feature Extraction

```python
def extract_gait_features(loco_data, subjects=None, tasks=None):
    """Extract comprehensive gait features for ML."""
    
    if subjects is None:
        subjects = loco_data.get_subjects()
    if tasks is None:
        tasks = loco_data.get_tasks()
    
    feature_vectors = []
    labels = []
    metadata = []
    
    for subject in subjects:
        for task in tasks:
            # Get 3D gait data
            data_3d, feature_names = loco_data.get_cycles(subject, task)
            if data_3d is None:
                continue
            
            # Extract features for each gait cycle
            for cycle_idx in range(data_3d.shape[0]):
                cycle_data = data_3d[cycle_idx, :, :]  # (150, n_features)
                
                # Extract multiple feature types
                features = {}
                
                # 1. Statistical features
                features.update(extract_statistical_features(cycle_data, feature_names))
                
                # 2. Temporal features
                features.update(extract_temporal_features(cycle_data, feature_names))
                
                # 3. Frequency features
                features.update(extract_frequency_features(cycle_data, feature_names))
                
                # 4. Shape features
                features.update(extract_shape_features(cycle_data, feature_names))
                
                # Store results
                feature_vectors.append(list(features.values()))
                labels.append(task)
                metadata.append({
                    'subject': subject,
                    'task': task,
                    'cycle': cycle_idx,
                    'feature_names': list(features.keys())
                })
    
    return np.array(feature_vectors), np.array(labels), metadata

def extract_statistical_features(cycle_data, feature_names):
    """Extract statistical features from gait cycle."""
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        signal = cycle_data[:, i]
        prefix = feature_name.split('_')[0] + '_' + feature_name.split('_')[1]  # e.g., 'knee_flexion'
        
        features[f'{prefix}_mean'] = np.mean(signal)
        features[f'{prefix}_std'] = np.std(signal)
        features[f'{prefix}_min'] = np.min(signal)
        features[f'{prefix}_max'] = np.max(signal)
        features[f'{prefix}_range'] = np.max(signal) - np.min(signal)
        features[f'{prefix}_skew'] = compute_skewness(signal)
        features[f'{prefix}_kurtosis'] = compute_kurtosis(signal)
    
    return features

def extract_temporal_features(cycle_data, feature_names):
    """Extract temporal features from gait cycle."""
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        signal = cycle_data[:, i]
        prefix = feature_name.split('_')[0] + '_' + feature_name.split('_')[1]
        
        # Peak timing
        peak_idx = np.argmax(signal)
        features[f'{prefix}_peak_time'] = peak_idx / len(signal)  # Normalized time
        
        # Valley timing
        valley_idx = np.argmin(signal)
        features[f'{prefix}_valley_time'] = valley_idx / len(signal)
        
        # Zero crossings
        features[f'{prefix}_zero_crossings'] = count_zero_crossings(signal)
        
        # Time to peak slope
        slopes = np.diff(signal)
        max_slope_idx = np.argmax(np.abs(slopes))
        features[f'{prefix}_max_slope_time'] = max_slope_idx / len(slopes)
    
    return features

def extract_frequency_features(cycle_data, feature_names):
    """Extract frequency domain features."""
    from scipy import signal as sp_signal
    
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        time_signal = cycle_data[:, i]
        prefix = feature_name.split('_')[0] + '_' + feature_name.split('_')[1]
        
        # Power spectral density
        frequencies, psd = sp_signal.welch(time_signal, nperseg=len(time_signal)//4)
        
        # Spectral features
        features[f'{prefix}_spectral_centroid'] = np.sum(frequencies * psd) / np.sum(psd)
        features[f'{prefix}_spectral_bandwidth'] = np.sqrt(np.sum(((frequencies - features[f'{prefix}_spectral_centroid']) ** 2) * psd) / np.sum(psd))
        features[f'{prefix}_spectral_rolloff'] = compute_spectral_rolloff(frequencies, psd, 0.85)
        features[f'{prefix}_spectral_flux'] = np.sum(np.diff(psd) ** 2)
    
    return features

def extract_shape_features(cycle_data, feature_names):
    """Extract shape-based features."""
    features = {}
    
    for i, feature_name in enumerate(feature_names):
        signal = cycle_data[:, i]
        prefix = feature_name.split('_')[0] + '_' + feature_name.split('_')[1]
        
        # Symmetry features
        mid_point = len(signal) // 2
        first_half = signal[:mid_point]
        second_half = signal[mid_point:]
        
        # Reverse second half for comparison
        second_half_reversed = second_half[::-1]
        
        # Calculate symmetry as correlation
        if len(first_half) == len(second_half_reversed):
            symmetry = np.corrcoef(first_half, second_half_reversed)[0, 1]
            features[f'{prefix}_symmetry'] = symmetry if not np.isnan(symmetry) else 0
        
        # Shape complexity (approximate entropy)
        features[f'{prefix}_complexity'] = approximate_entropy(signal, 2, 0.2 * np.std(signal))
        
        # Regularity (sample entropy)
        features[f'{prefix}_regularity'] = sample_entropy(signal, 2, 0.2 * np.std(signal))
    
    return features

# Helper functions
def compute_skewness(x):
    """Compute skewness of signal."""
    mean_x = np.mean(x)
    std_x = np.std(x)
    if std_x == 0:
        return 0
    return np.mean(((x - mean_x) / std_x) ** 3)

def compute_kurtosis(x):
    """Compute kurtosis of signal."""
    mean_x = np.mean(x)
    std_x = np.std(x)
    if std_x == 0:
        return 0
    return np.mean(((x - mean_x) / std_x) ** 4) - 3

def count_zero_crossings(x):
    """Count zero crossings in signal."""
    return len(np.where(np.diff(np.sign(x)))[0])

def compute_spectral_rolloff(frequencies, psd, rolloff_threshold=0.85):
    """Compute spectral rolloff frequency."""
    cumulative_energy = np.cumsum(psd)
    total_energy = cumulative_energy[-1]
    rolloff_energy = rolloff_threshold * total_energy
    
    rolloff_idx = np.where(cumulative_energy >= rolloff_energy)[0]
    if len(rolloff_idx) > 0:
        return frequencies[rolloff_idx[0]]
    else:
        return frequencies[-1]

def approximate_entropy(U, m, r):
    """Calculate approximate entropy."""
    def _maxdist(xi, xj, N):
        return max([abs(ua - va) for ua, va in zip(xi, xj)])
    
    def _phi(m):
        patterns = np.array([U[i:i + m] for i in range(N - m + 1)])
        C = np.zeros(N - m + 1)
        for i in range(N - m + 1):
            template_i = patterns[i]
            for j in range(N - m + 1):
                if _maxdist(template_i, patterns[j], m) <= r:
                    C[i] += 1.0
        C = C / float(N - m + 1.0)
        phi = np.mean(np.log(C))
        return phi
    
    N = len(U)
    return _phi(m) - _phi(m + 1)

def sample_entropy(U, m, r):
    """Calculate sample entropy."""
    def _maxdist(xi, xj):
        return max([abs(ua - va) for ua, va in zip(xi, xj)])
    
    N = len(U)
    B = 0.0
    A = 0.0
    
    # Template matching
    for i in range(N - m):
        template = U[i:i + m]
        for j in range(i + 1, N - m):
            if _maxdist(template, U[j:j + m]) <= r:
                B += 1
            if _maxdist(U[i:i + m + 1], U[j:j + m + 1]) <= r:
                A += 1
    
    if B == 0:
        return float('inf')
    return -np.log(A / B)
```

## Scikit-learn Integration

### Classification Pipeline

```python
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix

class GaitClassificationPipeline:
    """Complete ML pipeline for gait pattern classification."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.models = {}
        
    def prepare_data(self, target='task', subjects=None, tasks=None):
        """Prepare features and labels for ML."""
        
        # Extract features
        X, y, metadata = extract_gait_features(self.loco_data, subjects, tasks)
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Store feature names
        self.feature_names = metadata[0]['feature_names'] if metadata else []
        
        return X, y_encoded, metadata
    
    def train_models(self, X_train, y_train):
        """Train multiple models for comparison."""
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Define models
        models = {
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'SVM': SVC(kernel='rbf', random_state=42),
            'Neural Network': MLPClassifier(hidden_layer_sizes=(100, 50), random_state=42)
        }
        
        # Train and evaluate each model
        for name, model in models.items():
            print(f"Training {name}...")
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)
            
            # Fit on full training set
            model.fit(X_train_scaled, y_train)
            
            # Store model and results
            self.models[name] = {
                'model': model,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            print(f"  CV Score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    
    def evaluate_models(self, X_test, y_test):
        """Evaluate trained models on test set."""
        
        X_test_scaled = self.scaler.transform(X_test)
        results = {}
        
        for name, model_info in self.models.items():
            model = model_info['model']
            
            # Predictions
            y_pred = model.predict(X_test_scaled)
            
            # Classification report
            report = classification_report(y_test, y_pred, 
                                         target_names=self.label_encoder.classes_,
                                         output_dict=True)
            
            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            
            results[name] = {
                'accuracy': report['accuracy'],
                'classification_report': report,
                'confusion_matrix': cm
            }
            
            print(f"\n{name} Results:")
            print(f"  Accuracy: {report['accuracy']:.3f}")
            print(f"  Macro Avg F1: {report['macro avg']['f1-score']:.3f}")
        
        return results
    
    def get_feature_importance(self, model_name='Random Forest'):
        """Get feature importance from tree-based model."""
        
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]['model']
        
        if hasattr(model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return importance_df
        else:
            print(f"Model {model_name} does not support feature importance")
            return None

# Usage example
pipeline = GaitClassificationPipeline(loco)

# Prepare data
X, y, metadata = pipeline.prepare_data(target='task')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, 
                                                    stratify=y, random_state=42)

# Train models
pipeline.train_models(X_train, y_train)

# Evaluate models
results = pipeline.evaluate_models(X_test, y_test)

# Feature importance
importance = pipeline.get_feature_importance()
print("\nTop 10 Most Important Features:")
print(importance.head(10))
```

### Regression Analysis

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_squared_error, r2_score

class GaitRegressionPipeline:
    """Pipeline for predicting continuous variables from gait data."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        self.scaler = StandardScaler()
        
    def prepare_regression_data(self, target_variable='walking_speed'):
        """Prepare data for regression analysis."""
        
        # Extract gait features
        X, _, metadata = extract_gait_features(self.loco_data)
        
        # Create target variable (example: synthetic walking speed)
        # In practice, this would come from external measurements
        y = self.create_synthetic_target(metadata, target_variable)
        
        return X, y, metadata
    
    def create_synthetic_target(self, metadata, target_variable):
        """Create synthetic target for demonstration."""
        
        if target_variable == 'walking_speed':
            # Simulate walking speed based on task type
            speeds = []
            for meta in metadata:
                if 'fast' in meta['task']:
                    speed = np.random.normal(1.8, 0.2)
                elif 'slow' in meta['task']:
                    speed = np.random.normal(0.8, 0.1)
                else:
                    speed = np.random.normal(1.3, 0.15)
                speeds.append(max(0.5, speed))  # Ensure positive speed
            return np.array(speeds)
        
        elif target_variable == 'age':
            # Simulate age based on gait variability
            ages = []
            for meta in metadata:
                # Assume higher variability correlates with age
                base_age = np.random.normal(45, 15)
                ages.append(max(18, min(80, base_age)))
            return np.array(ages)
        
        else:
            raise ValueError(f"Unknown target variable: {target_variable}")
    
    def train_regression_models(self, X_train, y_train):
        """Train regression models."""
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        models = {
            'Random Forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'Ridge': Ridge(alpha=1.0),
            'Lasso': Lasso(alpha=1.0),
        }
        
        self.regression_models = {}
        
        for name, model in models.items():
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, 
                                      cv=5, scoring='r2')
            
            # Fit model
            model.fit(X_train_scaled, y_train)
            
            self.regression_models[name] = {
                'model': model,
                'cv_r2_mean': cv_scores.mean(),
                'cv_r2_std': cv_scores.std()
            }
            
            print(f"{name} - CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    
    def evaluate_regression_models(self, X_test, y_test):
        """Evaluate regression models."""
        
        X_test_scaled = self.scaler.transform(X_test)
        results = {}
        
        for name, model_info in self.regression_models.items():
            model = model_info['model']
            
            # Predictions
            y_pred = model.predict(X_test_scaled)
            
            # Metrics
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            results[name] = {
                'mse': mse,
                'rmse': np.sqrt(mse),
                'r2': r2,
                'predictions': y_pred
            }
            
            print(f"{name} - R²: {r2:.3f}, RMSE: {np.sqrt(mse):.3f}")
        
        return results

# Usage
reg_pipeline = GaitRegressionPipeline(loco)
X, y, metadata = reg_pipeline.prepare_regression_data('walking_speed')
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

reg_pipeline.train_regression_models(X_train, y_train)
reg_results = reg_pipeline.evaluate_regression_models(X_test, y_test)
```

## TensorFlow/Keras Integration

### Deep Learning for Gait Classification

```python
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

class GaitDeepLearningPipeline:
    """Deep learning pipeline for gait analysis."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        self.model = None
        
    def prepare_sequence_data(self, subjects=None, tasks=None):
        """Prepare sequence data for RNN/LSTM models."""
        
        if subjects is None:
            subjects = self.loco_data.get_subjects()
        if tasks is None:
            tasks = self.loco_data.get_tasks()
        
        sequences = []
        labels = []
        
        for subject in subjects:
            for task in tasks:
                data_3d, features = self.loco_data.get_cycles(subject, task)
                if data_3d is None:
                    continue
                
                # Each gait cycle is a sequence
                for cycle_idx in range(data_3d.shape[0]):
                    sequence = data_3d[cycle_idx, :, :]  # (150, n_features)
                    sequences.append(sequence)
                    labels.append(task)
        
        return np.array(sequences), np.array(labels)
    
    def build_lstm_model(self, input_shape, num_classes):
        """Build LSTM model for gait classification."""
        
        model = keras.Sequential([
            layers.LSTM(64, return_sequences=True, input_shape=input_shape),
            layers.Dropout(0.2),
            layers.LSTM(32, return_sequences=False),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def build_cnn_model(self, input_shape, num_classes):
        """Build CNN model for gait pattern recognition."""
        
        model = keras.Sequential([
            layers.Conv1D(32, 3, activation='relu', input_shape=input_shape),
            layers.MaxPooling1D(2),
            layers.Conv1D(64, 3, activation='relu'),
            layers.MaxPooling1D(2),
            layers.Conv1D(128, 3, activation='relu'),
            layers.GlobalMaxPooling1D(),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def train_deep_model(self, X, y, model_type='lstm', validation_split=0.2):
        """Train deep learning model."""
        
        # Encode labels
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        
        # Normalize features
        X_norm = (X - np.mean(X, axis=(0, 1))) / np.std(X, axis=(0, 1))
        
        # Build model
        input_shape = (X.shape[1], X.shape[2])  # (sequence_length, features)
        num_classes = len(np.unique(y_encoded))
        
        if model_type == 'lstm':
            self.model = self.build_lstm_model(input_shape, num_classes)
        elif model_type == 'cnn':
            self.model = self.build_cnn_model(input_shape, num_classes)
        else:
            raise ValueError("model_type must be 'lstm' or 'cnn'")
        
        # Callbacks
        callbacks = [
            keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=5)
        ]
        
        # Train model
        history = self.model.fit(
            X_norm, y_encoded,
            epochs=100,
            batch_size=32,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=1
        )
        
        self.label_encoder = label_encoder
        return history
    
    def evaluate_deep_model(self, X_test, y_test):
        """Evaluate deep learning model."""
        
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        # Normalize test data
        X_test_norm = (X_test - np.mean(X_test, axis=(0, 1))) / np.std(X_test, axis=(0, 1))
        
        # Encode test labels
        y_test_encoded = self.label_encoder.transform(y_test)
        
        # Evaluate
        test_loss, test_accuracy = self.model.evaluate(X_test_norm, y_test_encoded, verbose=0)
        
        # Predictions
        y_pred_proba = self.model.predict(X_test_norm)
        y_pred = np.argmax(y_pred_proba, axis=1)
        
        return {
            'test_loss': test_loss,
            'test_accuracy': test_accuracy,
            'predictions': y_pred,
            'prediction_probabilities': y_pred_proba
        }

# Usage
dl_pipeline = GaitDeepLearningPipeline(loco)

# Prepare sequence data
X_seq, y_seq = dl_pipeline.prepare_sequence_data()
X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, 
                                                    test_size=0.2, 
                                                    stratify=y_seq, 
                                                    random_state=42)

print(f"Training data shape: {X_train.shape}")
print(f"Test data shape: {X_test.shape}")

# Train LSTM model
print("Training LSTM model...")
history_lstm = dl_pipeline.train_deep_model(X_train, y_train, model_type='lstm')

# Evaluate model
results_lstm = dl_pipeline.evaluate_deep_model(X_test, y_test)
print(f"LSTM Test Accuracy: {results_lstm['test_accuracy']:.3f}")
```

### Autoencoder for Anomaly Detection

```python
class GaitAnomalyDetector:
    """Autoencoder-based anomaly detection for gait patterns."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        self.autoencoder = None
        self.encoder = None
        self.decoder = None
        
    def build_autoencoder(self, input_shape, encoding_dim=10):
        """Build autoencoder for gait pattern reconstruction."""
        
        # Input layer
        input_layer = layers.Input(shape=input_shape)
        
        # Encoder
        encoded = layers.LSTM(64, return_sequences=True)(input_layer)
        encoded = layers.LSTM(32, return_sequences=True)(encoded)
        encoded = layers.LSTM(encoding_dim, return_sequences=False)(encoded)
        
        # Decoder
        decoded = layers.RepeatVector(input_shape[0])(encoded)
        decoded = layers.LSTM(encoding_dim, return_sequences=True)(decoded)
        decoded = layers.LSTM(32, return_sequences=True)(decoded)
        decoded = layers.LSTM(64, return_sequences=True)(decoded)
        decoded = layers.TimeDistributed(layers.Dense(input_shape[1]))(decoded)
        
        # Models
        self.autoencoder = keras.Model(input_layer, decoded)
        self.encoder = keras.Model(input_layer, encoded)
        
        self.autoencoder.compile(optimizer='adam', loss='mse')
        
        return self.autoencoder
    
    def train_autoencoder(self, X_normal, validation_split=0.2):
        """Train autoencoder on normal gait patterns."""
        
        # Normalize data
        self.X_mean = np.mean(X_normal, axis=(0, 1))
        self.X_std = np.std(X_normal, axis=(0, 1))
        X_norm = (X_normal - self.X_mean) / self.X_std
        
        # Build model
        input_shape = (X_normal.shape[1], X_normal.shape[2])
        self.build_autoencoder(input_shape)
        
        # Train
        history = self.autoencoder.fit(
            X_norm, X_norm,
            epochs=100,
            batch_size=32,
            validation_split=validation_split,
            callbacks=[
                keras.callbacks.EarlyStopping(patience=15, restore_best_weights=True)
            ],
            verbose=1
        )
        
        return history
    
    def detect_anomalies(self, X_test, threshold_percentile=95):
        """Detect anomalous gait patterns."""
        
        # Normalize test data
        X_test_norm = (X_test - self.X_mean) / self.X_std
        
        # Reconstruct
        X_reconstructed = self.autoencoder.predict(X_test_norm)
        
        # Calculate reconstruction error
        reconstruction_errors = np.mean(np.square(X_test_norm - X_reconstructed), axis=(1, 2))
        
        # Set threshold based on percentile
        threshold = np.percentile(reconstruction_errors, threshold_percentile)
        
        # Identify anomalies
        anomalies = reconstruction_errors > threshold
        
        return {
            'reconstruction_errors': reconstruction_errors,
            'threshold': threshold,
            'anomalies': anomalies,
            'anomaly_indices': np.where(anomalies)[0]
        }

# Usage
anomaly_detector = GaitAnomalyDetector(loco)

# Prepare normal gait data (example: only normal walking)
X_normal = []
subjects = loco.get_subjects()
for subject in subjects:
    data_3d, _ = loco.get_cycles(subject, 'normal_walk')
    if data_3d is not None:
        for cycle in range(data_3d.shape[0]):
            X_normal.append(data_3d[cycle, :, :])

X_normal = np.array(X_normal)
print(f"Normal gait data shape: {X_normal.shape}")

# Train autoencoder
history = anomaly_detector.train_autoencoder(X_normal)

# Test on mixed data (normal + pathological)
X_test = X_normal  # In practice, include pathological data
anomaly_results = anomaly_detector.detect_anomalies(X_test)

print(f"Detected {np.sum(anomaly_results['anomalies'])} anomalies out of {len(X_test)} samples")
```

## PyTorch Integration

### Gait Pattern Recognition with PyTorch

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F

class GaitDataset(Dataset):
    """PyTorch dataset for gait data."""
    
    def __init__(self, sequences, labels, transform=None):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.LongTensor(labels)
        self.transform = transform
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = self.sequences[idx]
        label = self.labels[idx]
        
        if self.transform:
            sequence = self.transform(sequence)
        
        return sequence, label

class GaitLSTM(nn.Module):
    """LSTM network for gait classification."""
    
    def __init__(self, input_size, hidden_size, num_layers, num_classes, dropout=0.2):
        super(GaitLSTM, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, 
                           batch_first=True, dropout=dropout)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, num_classes)
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Take the last output
        output = lstm_out[:, -1, :]
        output = self.dropout(output)
        output = self.fc(output)
        
        return output

class GaitCNN(nn.Module):
    """1D CNN for gait pattern classification."""
    
    def __init__(self, input_channels, num_classes):
        super(GaitCNN, self).__init__()
        
        self.conv1 = nn.Conv1d(input_channels, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        
        self.pool = nn.MaxPool1d(2)
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, num_classes)
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, x):
        # Transpose for Conv1d (batch, channels, sequence)
        x = x.transpose(1, 2)
        
        x = F.relu(self.conv1(x))
        x = self.pool(x)
        
        x = F.relu(self.conv2(x))
        x = self.pool(x)
        
        x = F.relu(self.conv3(x))
        x = self.global_pool(x)
        
        x = x.squeeze(-1)  # Remove last dimension
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x

class PyTorchGaitClassifier:
    """PyTorch-based gait classification pipeline."""
    
    def __init__(self, model_type='lstm'):
        self.model_type = model_type
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
    def prepare_data_loaders(self, X_train, y_train, X_test, y_test, batch_size=32):
        """Prepare PyTorch data loaders."""
        
        # Normalize data
        X_mean = np.mean(X_train, axis=(0, 1))
        X_std = np.std(X_train, axis=(0, 1))
        
        X_train_norm = (X_train - X_mean) / X_std
        X_test_norm = (X_test - X_mean) / X_std
        
        # Create datasets
        train_dataset = GaitDataset(X_train_norm, y_train)
        test_dataset = GaitDataset(X_test_norm, y_test)
        
        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        return train_loader, test_loader
    
    def build_model(self, input_size, num_classes):
        """Build PyTorch model."""
        
        if self.model_type == 'lstm':
            self.model = GaitLSTM(
                input_size=input_size,
                hidden_size=64,
                num_layers=2,
                num_classes=num_classes,
                dropout=0.2
            )
        elif self.model_type == 'cnn':
            self.model = GaitCNN(
                input_channels=input_size,
                num_classes=num_classes
            )
        else:
            raise ValueError("model_type must be 'lstm' or 'cnn'")
        
        self.model.to(self.device)
        return self.model
    
    def train_model(self, train_loader, test_loader, num_epochs=100, learning_rate=0.001):
        """Train PyTorch model."""
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=5)
        
        train_losses = []
        test_accuracies = []
        
        for epoch in range(num_epochs):
            # Training phase
            self.model.train()
            train_loss = 0.0
            
            for sequences, labels in train_loader:
                sequences, labels = sequences.to(self.device), labels.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(sequences)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation phase
            self.model.eval()
            correct = 0
            total = 0
            test_loss = 0.0
            
            with torch.no_grad():
                for sequences, labels in test_loader:
                    sequences, labels = sequences.to(self.device), labels.to(self.device)
                    outputs = self.model(sequences)
                    loss = criterion(outputs, labels)
                    test_loss += loss.item()
                    
                    _, predicted = torch.max(outputs.data, 1)
                    total += labels.size(0)
                    correct += (predicted == labels).sum().item()
            
            avg_train_loss = train_loss / len(train_loader)
            test_accuracy = 100 * correct / total
            avg_test_loss = test_loss / len(test_loader)
            
            train_losses.append(avg_train_loss)
            test_accuracies.append(test_accuracy)
            
            scheduler.step(avg_test_loss)
            
            if epoch % 10 == 0:
                print(f'Epoch [{epoch}/{num_epochs}], Train Loss: {avg_train_loss:.4f}, '
                      f'Test Accuracy: {test_accuracy:.2f}%')
        
        return train_losses, test_accuracies
    
    def evaluate_model(self, test_loader):
        """Evaluate trained model."""
        
        self.model.eval()
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for sequences, labels in test_loader:
                sequences = sequences.to(self.device)
                outputs = self.model(sequences)
                _, predicted = torch.max(outputs, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_labels.extend(labels.numpy())
        
        return np.array(all_predictions), np.array(all_labels)

# Usage
# Prepare data (assuming X_seq and y_seq from previous example)
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y_seq)

X_train, X_test, y_train, y_test = train_test_split(X_seq, y_encoded, 
                                                    test_size=0.2, 
                                                    stratify=y_encoded, 
                                                    random_state=42)

# Initialize classifier
pytorch_classifier = PyTorchGaitClassifier(model_type='lstm')

# Prepare data loaders
train_loader, test_loader = pytorch_classifier.prepare_data_loaders(
    X_train, y_train, X_test, y_test, batch_size=32
)

# Build and train model
input_size = X_train.shape[2]  # Number of features
num_classes = len(np.unique(y_encoded))

pytorch_classifier.build_model(input_size, num_classes)
train_losses, test_accuracies = pytorch_classifier.train_model(train_loader, test_loader)

# Evaluate
predictions, true_labels = pytorch_classifier.evaluate_model(test_loader)
final_accuracy = np.mean(predictions == true_labels)
print(f"Final Test Accuracy: {final_accuracy:.3f}")
```

## Model Deployment and Production

### Model Serialization and Loading

```python
import joblib
import pickle

def save_ml_pipeline(pipeline, scaler, label_encoder, filepath):
    """Save complete ML pipeline for deployment."""
    
    pipeline_data = {
        'model': pipeline,
        'scaler': scaler,
        'label_encoder': label_encoder,
        'feature_names': getattr(pipeline, 'feature_names_', None)
    }
    
    joblib.dump(pipeline_data, filepath)
    print(f"Pipeline saved to {filepath}")

def load_ml_pipeline(filepath):
    """Load ML pipeline for inference."""
    
    pipeline_data = joblib.load(filepath)
    return pipeline_data

# Save model
save_ml_pipeline(pipeline.models['Random Forest']['model'], 
                 pipeline.scaler, 
                 pipeline.label_encoder,
                 'gait_classification_pipeline.pkl')

# Load and use model
loaded_pipeline = load_ml_pipeline('gait_classification_pipeline.pkl')
model = loaded_pipeline['model']
scaler = loaded_pipeline['scaler']
```

### Real-time Inference Pipeline

```python
class GaitInferencePipeline:
    """Real-time gait classification inference."""
    
    def __init__(self, model_path):
        self.pipeline_data = load_ml_pipeline(model_path)
        self.model = self.pipeline_data['model']
        self.scaler = self.pipeline_data['scaler']
        self.label_encoder = self.pipeline_data['label_encoder']
    
    def predict_gait_cycle(self, cycle_data, feature_names):
        """Predict single gait cycle classification."""
        
        # Extract features from single cycle
        features = {}
        features.update(extract_statistical_features(cycle_data, feature_names))
        features.update(extract_temporal_features(cycle_data, feature_names))
        features.update(extract_frequency_features(cycle_data, feature_names))
        features.update(extract_shape_features(cycle_data, feature_names))
        
        # Convert to array
        feature_vector = np.array(list(features.values())).reshape(1, -1)
        
        # Scale features
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict
        prediction_proba = self.model.predict_proba(feature_vector_scaled)[0]
        prediction_class = self.model.predict(feature_vector_scaled)[0]
        
        # Decode label
        predicted_task = self.label_encoder.inverse_transform([prediction_class])[0]
        
        return {
            'predicted_task': predicted_task,
            'confidence': prediction_proba.max(),
            'class_probabilities': dict(zip(self.label_encoder.classes_, prediction_proba))
        }

# Usage for real-time inference
inference_pipeline = GaitInferencePipeline('gait_classification_pipeline.pkl')

# Simulate real-time data
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
single_cycle = data_3d[0, :, :]  # First cycle

# Make prediction
result = inference_pipeline.predict_gait_cycle(single_cycle, features)
print(f"Predicted task: {result['predicted_task']}")
print(f"Confidence: {result['confidence']:.3f}")
```

This comprehensive guide provides complete integration patterns for machine learning workflows with the locomotion data platform, covering feature engineering, model training, evaluation, and deployment scenarios.