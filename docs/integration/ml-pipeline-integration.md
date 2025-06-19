# ML Pipeline Integration

Comprehensive guide for integrating the locomotion data standardization platform with machine learning workflows, including scikit-learn, PyTorch, and TensorFlow.

## Overview

The platform provides standardized biomechanical data that's ideal for machine learning applications. This guide covers:

- Feature extraction for ML models
- Integration with popular ML frameworks
- Cross-validation strategies for biomechanical data
- Model validation using domain knowledge

## Core ML Integration Patterns

### Feature Extraction Pipeline

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedKFold
from lib.core.locomotion_analysis import LocomotionData

class LocomotionFeatureExtractor:
    """Extract ML-ready features from locomotion data."""
    
    def __init__(self, feature_types=['kinematic', 'kinetic'], 
                 statistical_features=['mean', 'std', 'rom', 'peak_timing']):
        self.feature_types = feature_types
        self.statistical_features = statistical_features
        self.feature_names = []
        self.scaler = StandardScaler()
        
    def extract_features(self, locomotion_data: LocomotionData, 
                        subjects=None, tasks=None) -> tuple:
        """
        Extract ML features from locomotion data.
        
        Returns:
            features (np.ndarray): Feature matrix (n_samples, n_features)
            labels (np.ndarray): Labels for classification
            metadata (pd.DataFrame): Sample metadata
        """
        
        if subjects is None:
            subjects = locomotion_data.subjects
        if tasks is None:
            tasks = locomotion_data.tasks
            
        features_list = []
        labels_list = []
        metadata_list = []
        
        self.feature_names = []
        
        for subject in subjects:
            for task in tasks:
                # Get cycles for this subject-task
                if 'kinematic' in self.feature_types:
                    kin_data, kin_features = locomotion_data.get_cycles(
                        subject, task, locomotion_data.ANGLE_FEATURES
                    )
                else:
                    kin_data, kin_features = None, []
                    
                if 'kinetic' in self.feature_types:
                    kin_data_kinetic, kinetic_features = locomotion_data.get_cycles(
                        subject, task, locomotion_data.MOMENT_FEATURES
                    )
                else:
                    kin_data_kinetic, kinetic_features = None, []
                
                # Combine data
                if kin_data is not None and kin_data_kinetic is not None:
                    combined_data = np.concatenate([kin_data, kin_data_kinetic], axis=2)
                    combined_features = kin_features + kinetic_features
                elif kin_data is not None:
                    combined_data = kin_data
                    combined_features = kin_features
                elif kin_data_kinetic is not None:
                    combined_data = kin_data_kinetic
                    combined_features = kinetic_features
                else:
                    continue
                
                # Extract features for each cycle
                cycle_features = self._extract_cycle_features(
                    combined_data, combined_features
                )
                
                # Add to lists
                for i, cycle_feat in enumerate(cycle_features):
                    features_list.append(cycle_feat)
                    labels_list.append(task)
                    metadata_list.append({
                        'subject': subject,
                        'task': task,
                        'cycle': i
                    })
        
        # Convert to arrays
        features = np.array(features_list)
        labels = np.array(labels_list)
        metadata = pd.DataFrame(metadata_list)
        
        return features, labels, metadata
    
    def _extract_cycle_features(self, data_3d: np.ndarray, 
                               feature_names: list) -> list:
        """Extract statistical features from individual cycles."""
        
        n_cycles, n_points, n_features = data_3d.shape
        cycle_features = []
        
        for cycle_idx in range(n_cycles):
            cycle_data = data_3d[cycle_idx, :, :]  # (150, n_features)
            cycle_feat_vector = []
            
            for feat_idx, feat_name in enumerate(feature_names):
                feat_data = cycle_data[:, feat_idx]  # (150,)
                
                # Statistical features
                if 'mean' in self.statistical_features:
                    cycle_feat_vector.append(np.mean(feat_data))
                    if len(self.feature_names) <= len(feature_names) * len(self.statistical_features):
                        self.feature_names.append(f"{feat_name}_mean")
                
                if 'std' in self.statistical_features:
                    cycle_feat_vector.append(np.std(feat_data))
                    if len(self.feature_names) <= len(feature_names) * len(self.statistical_features):
                        self.feature_names.append(f"{feat_name}_std")
                
                if 'rom' in self.statistical_features:
                    rom = np.max(feat_data) - np.min(feat_data)
                    cycle_feat_vector.append(rom)
                    if len(self.feature_names) <= len(feature_names) * len(self.statistical_features):
                        self.feature_names.append(f"{feat_name}_rom")
                
                if 'peak_timing' in self.statistical_features:
                    peak_idx = np.argmax(np.abs(feat_data))
                    peak_timing = (peak_idx / len(feat_data)) * 100  # As percentage
                    cycle_feat_vector.append(peak_timing)
                    if len(self.feature_names) <= len(feature_names) * len(self.statistical_features):
                        self.feature_names.append(f"{feat_name}_peak_timing")
            
            cycle_features.append(cycle_feat_vector)
        
        return cycle_features
    
    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        """Fit scaler and transform features."""
        return self.scaler.fit_transform(features)
    
    def transform(self, features: np.ndarray) -> np.ndarray:
        """Transform features using fitted scaler."""
        return self.scaler.transform(features)

# Example usage
loco = LocomotionData('dataset_phase.parquet')
extractor = LocomotionFeatureExtractor()

# Extract features
features, labels, metadata = extractor.extract_features(loco)
print(f"Feature matrix shape: {features.shape}")
print(f"Feature names: {extractor.feature_names[:5]}...")
print(f"Unique tasks: {np.unique(labels)}")

# Scale features
features_scaled = extractor.fit_transform(features)
```

## Scikit-learn Integration

### Classification Pipeline

```python
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns

class LocomotionTaskClassifier:
    """Classify locomotion tasks using ML."""
    
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'svm': SVC(kernel='rbf', random_state=42),
        }
        self.best_model = None
        self.label_encoder = LabelEncoder()
        self.feature_extractor = LocomotionFeatureExtractor()
        
    def prepare_data(self, locomotion_data: LocomotionData):
        """Prepare data for classification."""
        
        # Extract features
        features, labels, metadata = self.feature_extractor.extract_features(locomotion_data)
        
        # Scale features
        features_scaled = self.feature_extractor.fit_transform(features)
        
        # Encode labels
        labels_encoded = self.label_encoder.fit_transform(labels)
        
        return features_scaled, labels_encoded, labels, metadata
    
    def evaluate_models(self, features: np.ndarray, labels: np.ndarray, 
                       cv_folds: int = 5) -> dict:
        """Evaluate different models using cross-validation."""
        
        # Use stratified k-fold to handle class imbalance
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        
        results = {}
        
        for name, model in self.models.items():
            print(f"Evaluating {name}...")
            
            # Cross-validation scores
            cv_scores = cross_val_score(model, features, labels, cv=cv, scoring='accuracy')
            
            results[name] = {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'cv_scores': cv_scores
            }
            
            print(f"  Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Select best model
        best_name = max(results.keys(), key=lambda x: results[x]['cv_mean'])
        self.best_model = self.models[best_name]
        
        print(f"\nBest model: {best_name}")
        return results
    
    def train_and_evaluate(self, features: np.ndarray, labels: np.ndarray, 
                          test_size: float = 0.2):
        """Train best model and evaluate on test set."""
        
        from sklearn.model_selection import train_test_split
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=test_size, stratify=labels, random_state=42
        )
        
        # Train best model
        self.best_model.fit(X_train, y_train)
        
        # Predictions
        y_pred = self.best_model.predict(X_test)
        
        # Evaluation
        accuracy = (y_pred == y_test).mean()
        
        # Classification report
        label_names = self.label_encoder.classes_
        report = classification_report(y_test, y_pred, 
                                     target_names=label_names, 
                                     output_dict=True)
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        return {
            'accuracy': accuracy,
            'classification_report': report,
            'confusion_matrix': cm,
            'label_names': label_names,
            'predictions': y_pred,
            'true_labels': y_test
        }
    
    def plot_confusion_matrix(self, cm: np.ndarray, label_names: list):
        """Plot confusion matrix."""
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=label_names, yticklabels=label_names)
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.show()
    
    def get_feature_importance(self) -> dict:
        """Get feature importance from trained model."""
        if hasattr(self.best_model, 'feature_importances_'):
            importances = self.best_model.feature_importances_
            feature_names = self.feature_extractor.feature_names
            
            # Sort by importance
            indices = np.argsort(importances)[::-1]
            
            return {
                'importances': importances[indices],
                'feature_names': [feature_names[i] for i in indices],
                'indices': indices
            }
        else:
            return None

# Example usage
loco = LocomotionData('dataset_phase.parquet')
classifier = LocomotionTaskClassifier()

# Prepare data
features, labels_encoded, labels_orig, metadata = classifier.prepare_data(loco)

# Evaluate models
results = classifier.evaluate_models(features, labels_encoded)

# Train and evaluate best model
eval_results = classifier.train_and_evaluate(features, labels_encoded)

print(f"\nTest Accuracy: {eval_results['accuracy']:.3f}")

# Plot confusion matrix
classifier.plot_confusion_matrix(
    eval_results['confusion_matrix'], 
    eval_results['label_names']
)

# Feature importance
importance = classifier.get_feature_importance()
if importance:
    print("\nTop 10 Important Features:")
    for i in range(10):
        feat_name = importance['feature_names'][i]
        feat_imp = importance['importances'][i]
        print(f"  {feat_name}: {feat_imp:.3f}")
```

### Regression Pipeline

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV

class LocomotionRegressor:
    """Predict continuous biomechanical parameters."""
    
    def __init__(self, target_feature: str = 'walking_speed'):
        self.target_feature = target_feature
        self.models = {
            'random_forest': RandomForestRegressor(random_state=42),
            'ridge': Ridge(),
            'lasso': Lasso()
        }
        self.best_model = None
        self.feature_extractor = LocomotionFeatureExtractor()
    
    def prepare_regression_data(self, locomotion_data: LocomotionData, 
                               target_data: dict) -> tuple:
        """Prepare data for regression."""
        
        # Extract features
        features, labels, metadata = self.feature_extractor.extract_features(locomotion_data)
        
        # Create target values from metadata
        targets = []
        valid_indices = []
        
        for i, (_, row) in enumerate(metadata.iterrows()):
            subject = row['subject']
            if subject in target_data:
                targets.append(target_data[subject])
                valid_indices.append(i)
        
        # Filter features and scale
        features_filtered = features[valid_indices]
        features_scaled = self.feature_extractor.fit_transform(features_filtered)
        targets = np.array(targets)
        
        return features_scaled, targets, metadata.iloc[valid_indices]
    
    def hyperparameter_tuning(self, features: np.ndarray, targets: np.ndarray):
        """Perform hyperparameter tuning."""
        
        param_grids = {
            'random_forest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20],
                'min_samples_split': [2, 5, 10]
            },
            'ridge': {
                'alpha': [0.1, 1.0, 10.0, 100.0]
            },
            'lasso': {
                'alpha': [0.01, 0.1, 1.0, 10.0]
            }
        }
        
        best_scores = {}
        best_models = {}
        
        for name, model in self.models.items():
            print(f"Tuning {name}...")
            
            grid_search = GridSearchCV(
                model, param_grids[name], 
                cv=5, scoring='r2', n_jobs=-1
            )
            
            grid_search.fit(features, targets)
            
            best_scores[name] = grid_search.best_score_
            best_models[name] = grid_search.best_estimator_
            
            print(f"  Best R²: {grid_search.best_score_:.3f}")
            print(f"  Best params: {grid_search.best_params_}")
        
        # Update models with best parameters
        self.models = best_models
        
        # Select best model
        best_name = max(best_scores.keys(), key=lambda x: best_scores[x])
        self.best_model = self.models[best_name]
        
        return best_scores, best_models
    
    def train_and_evaluate(self, features: np.ndarray, targets: np.ndarray):
        """Train and evaluate regression model."""
        
        from sklearn.model_selection import train_test_split
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, targets, test_size=0.2, random_state=42
        )
        
        # Train model
        self.best_model.fit(X_train, y_train)
        
        # Predictions
        y_pred_train = self.best_model.predict(X_train)
        y_pred_test = self.best_model.predict(X_test)
        
        # Metrics
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        train_rmse = np.sqrt(mean_squared_error(y_train, y_pred_train))
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        
        return {
            'train_r2': train_r2,
            'test_r2': test_r2,
            'train_rmse': train_rmse,
            'test_rmse': test_rmse,
            'predictions': y_pred_test,
            'true_values': y_test
        }
    
    def plot_predictions(self, y_true: np.ndarray, y_pred: np.ndarray):
        """Plot prediction vs actual."""
        plt.figure(figsize=(8, 6))
        plt.scatter(y_true, y_pred, alpha=0.6)
        
        # Perfect prediction line
        min_val, max_val = min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())
        plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2)
        
        plt.xlabel('True Values')
        plt.ylabel('Predictions')
        plt.title(f'Predictions vs True Values ({self.target_feature})')
        
        # Add R² score
        r2 = r2_score(y_true, y_pred)
        plt.text(0.05, 0.95, f'R² = {r2:.3f}', transform=plt.gca().transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        plt.show()

# Example usage with walking speed prediction
loco = LocomotionData('dataset_phase.parquet')

# Mock target data (walking speeds for each subject)
walking_speeds = {
    subject: np.random.normal(1.3, 0.2)  # m/s, typical walking speed
    for subject in loco.subjects
}

regressor = LocomotionRegressor(target_feature='walking_speed')

# Prepare data
features, targets, metadata = regressor.prepare_regression_data(loco, walking_speeds)

# Hyperparameter tuning
best_scores, best_models = regressor.hyperparameter_tuning(features, targets)

# Train and evaluate
results = regressor.train_and_evaluate(features, targets)

print(f"Test R²: {results['test_r2']:.3f}")
print(f"Test RMSE: {results['test_rmse']:.3f}")

# Plot results
regressor.plot_predictions(results['true_values'], results['predictions'])
```

## Deep Learning Integration

### PyTorch Integration

```python
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.model_selection import train_test_split

class GaitSequenceDataset(Dataset):
    """PyTorch dataset for gait sequence data."""
    
    def __init__(self, locomotion_data: LocomotionData, subjects=None, tasks=None):
        self.locomotion_data = locomotion_data
        self.subjects = subjects or locomotion_data.subjects
        self.tasks = tasks or locomotion_data.tasks
        self.sequences = []
        self.labels = []
        self.label_to_idx = {task: i for i, task in enumerate(self.tasks)}
        
        self._prepare_sequences()
    
    def _prepare_sequences(self):
        """Prepare sequences for training."""
        for subject in self.subjects:
            for task in self.tasks:
                # Get kinematic data
                data_3d, features = self.locomotion_data.get_cycles(
                    subject, task, self.locomotion_data.ANGLE_FEATURES
                )
                
                if data_3d is not None:
                    for cycle_idx in range(data_3d.shape[0]):
                        cycle_data = data_3d[cycle_idx, :, :]  # (150, n_features)
                        self.sequences.append(cycle_data)
                        self.labels.append(self.label_to_idx[task])
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = torch.FloatTensor(self.sequences[idx])  # (150, n_features)
        label = torch.LongTensor([self.labels[idx]])
        return sequence, label

class GaitLSTM(nn.Module):
    """LSTM network for gait sequence classification."""
    
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=5, dropout=0.3):
        super(GaitLSTM, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = nn.Linear(hidden_size, 1)
        
        # Classification layers
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, num_classes)
        )
    
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        
        # LSTM forward pass
        lstm_out, (h_n, c_n) = self.lstm(x)
        # lstm_out shape: (batch_size, sequence_length, hidden_size)
        
        # Attention mechanism
        attention_weights = torch.softmax(self.attention(lstm_out), dim=1)
        # attention_weights shape: (batch_size, sequence_length, 1)
        
        # Weighted sum
        attended_output = torch.sum(lstm_out * attention_weights, dim=1)
        # attended_output shape: (batch_size, hidden_size)
        
        # Classification
        output = self.classifier(attended_output)
        # output shape: (batch_size, num_classes)
        
        return output, attention_weights

class GaitLSTMTrainer:
    """Trainer for LSTM gait classification."""
    
    def __init__(self, model, device='cpu'):
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(model.parameters(), lr=0.001)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', patience=5, factor=0.5
        )
        
    def train_epoch(self, dataloader):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_idx, (data, targets) in enumerate(dataloader):
            data, targets = data.to(self.device), targets.to(self.device)
            targets = targets.squeeze()  # Remove extra dimension
            
            # Forward pass
            outputs, attention = self.model(data)
            loss = self.criterion(outputs, targets)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            # Statistics
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += targets.size(0)
            correct += (predicted == targets).sum().item()
        
        return total_loss / len(dataloader), 100. * correct / total
    
    def validate(self, dataloader):
        """Validate model."""
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for data, targets in dataloader:
                data, targets = data.to(self.device), targets.to(self.device)
                targets = targets.squeeze()
                
                outputs, attention = self.model(data)
                loss = self.criterion(outputs, targets)
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += targets.size(0)
                correct += (predicted == targets).sum().item()
        
        return total_loss / len(dataloader), 100. * correct / total
    
    def train(self, train_loader, val_loader, epochs=50):
        """Full training loop."""
        train_losses, train_accs = [], []
        val_losses, val_accs = [], []
        
        best_val_acc = 0
        
        for epoch in range(epochs):
            # Train
            train_loss, train_acc = self.train_epoch(train_loader)
            
            # Validate
            val_loss, val_acc = self.validate(val_loader)
            
            # Scheduler step
            self.scheduler.step(val_loss)
            
            # Store metrics
            train_losses.append(train_loss)
            train_accs.append(train_acc)
            val_losses.append(val_loss)
            val_accs.append(val_acc)
            
            # Save best model
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(self.model.state_dict(), 'best_gait_model.pth')
            
            if epoch % 10 == 0:
                print(f'Epoch {epoch}: Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%, '
                      f'Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%')
        
        return {
            'train_losses': train_losses,
            'train_accs': train_accs,
            'val_losses': val_losses,
            'val_accs': val_accs,
            'best_val_acc': best_val_acc
        }

# Example usage
loco = LocomotionData('dataset_phase.parquet')

# Create dataset
dataset = GaitSequenceDataset(loco)
print(f"Dataset size: {len(dataset)}")
print(f"Input shape: {dataset[0][0].shape}")  # (150, n_features)

# Split data
indices = list(range(len(dataset)))
train_indices, val_indices = train_test_split(indices, test_size=0.2, random_state=42)

train_dataset = torch.utils.data.Subset(dataset, train_indices)
val_dataset = torch.utils.data.Subset(dataset, val_indices)

# Create data loaders
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)

# Model
input_size = len(loco.ANGLE_FEATURES)  # Number of kinematic features
num_classes = len(loco.tasks)
model = GaitLSTM(input_size=input_size, num_classes=num_classes)

# Trainer
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
trainer = GaitLSTMTrainer(model, device=device)

# Train
results = trainer.train(train_loader, val_loader, epochs=100)
print(f"Best validation accuracy: {results['best_val_acc']:.2f}%")
```

### TensorFlow/Keras Integration

```python
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, Attention, GlobalAveragePooling1D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import LabelEncoder

class GaitCNN1D:
    """1D CNN for gait pattern classification."""
    
    def __init__(self, input_shape, num_classes):
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = self._build_model()
        self.label_encoder = LabelEncoder()
    
    def _build_model(self):
        """Build 1D CNN model."""
        model = Sequential([
            # First conv block
            tf.keras.layers.Conv1D(filters=64, kernel_size=10, activation='relu', 
                                  input_shape=self.input_shape),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Dropout(0.3),
            
            # Second conv block
            tf.keras.layers.Conv1D(filters=128, kernel_size=5, activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Dropout(0.3),
            
            # Third conv block
            tf.keras.layers.Conv1D(filters=256, kernel_size=3, activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dropout(0.5),
            
            # Classification layers
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(self.num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def prepare_data(self, locomotion_data: LocomotionData):
        """Prepare data for CNN training."""
        sequences = []
        labels = []
        
        for subject in locomotion_data.subjects:
            for task in locomotion_data.tasks:
                # Get kinematic data
                data_3d, features = locomotion_data.get_cycles(
                    subject, task, locomotion_data.ANGLE_FEATURES
                )
                
                if data_3d is not None:
                    for cycle_idx in range(data_3d.shape[0]):
                        cycle_data = data_3d[cycle_idx, :, :]  # (150, n_features)
                        sequences.append(cycle_data)
                        labels.append(task)
        
        # Convert to arrays
        X = np.array(sequences)  # (n_samples, 150, n_features)
        y = self.label_encoder.fit_transform(labels)  # (n_samples,)
        
        return X, y
    
    def train(self, X, y, validation_split=0.2, epochs=100, batch_size=32):
        """Train the CNN model."""
        
        # Callbacks
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
        ]
        
        # Train
        history = self.model.fit(
            X, y,
            validation_split=validation_split,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        return history
    
    def evaluate(self, X_test, y_test):
        """Evaluate model on test data."""
        test_loss, test_acc = self.model.evaluate(X_test, y_test, verbose=0)
        predictions = self.model.predict(X_test)
        
        return {
            'test_loss': test_loss,
            'test_accuracy': test_acc,
            'predictions': predictions,
            'predicted_classes': np.argmax(predictions, axis=1)
        }
    
    def plot_training_history(self, history):
        """Plot training history."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # Loss
        ax1.plot(history.history['loss'], label='Training Loss')
        ax1.plot(history.history['val_loss'], label='Validation Loss')
        ax1.set_title('Model Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.legend()
        
        # Accuracy
        ax2.plot(history.history['accuracy'], label='Training Accuracy')
        ax2.plot(history.history['val_accuracy'], label='Validation Accuracy')
        ax2.set_title('Model Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy')
        ax2.legend()
        
        plt.tight_layout()
        plt.show()

# Example usage
loco = LocomotionData('dataset_phase.parquet')

# Create and train CNN model
input_shape = (150, len(loco.ANGLE_FEATURES))  # (time_steps, features)
num_classes = len(loco.tasks)

cnn_model = GaitCNN1D(input_shape, num_classes)

# Prepare data
X, y = cnn_model.prepare_data(loco)
print(f"Data shape: {X.shape}")
print(f"Labels shape: {y.shape}")

# Train model
history = cnn_model.train(X, y, epochs=50)

# Plot training history
cnn_model.plot_training_history(history)

# Evaluate on test data (using last 20% for testing)
split_idx = int(0.8 * len(X))
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

results = cnn_model.evaluate(X_test, y_test)
print(f"Test accuracy: {results['test_accuracy']:.3f}")
```

## Cross-Validation for Biomechanical Data

### Subject-Wise Cross-Validation

```python
from sklearn.model_selection import GroupKFold
import numpy as np

class BiomechanicalCrossValidator:
    """Cross-validation strategies specific to biomechanical data."""
    
    @staticmethod
    def subject_wise_cv(features, labels, metadata, n_splits=5):
        """Perform subject-wise cross-validation."""
        
        # Get unique subjects
        subjects = metadata['subject'].unique()
        
        # Create groups for GroupKFold
        groups = metadata['subject'].values
        
        # Use GroupKFold to ensure subjects don't appear in both train and test
        gkf = GroupKFold(n_splits=n_splits)
        
        cv_results = []
        
        for fold, (train_idx, test_idx) in enumerate(gkf.split(features, labels, groups)):
            train_subjects = set(metadata.iloc[train_idx]['subject'])
            test_subjects = set(metadata.iloc[test_idx]['subject'])
            
            print(f"Fold {fold + 1}:")
            print(f"  Train subjects: {len(train_subjects)}")
            print(f"  Test subjects: {len(test_subjects)}")
            print(f"  Subject overlap: {len(train_subjects.intersection(test_subjects))}")
            
            cv_results.append({
                'fold': fold,
                'train_idx': train_idx,
                'test_idx': test_idx,
                'train_subjects': train_subjects,
                'test_subjects': test_subjects
            })
        
        return cv_results
    
    @staticmethod
    def task_wise_cv(features, labels, metadata, test_tasks=['incline_walking']):
        """Perform task-wise cross-validation."""
        
        # Split based on tasks
        test_mask = metadata['task'].isin(test_tasks)
        train_idx = np.where(~test_mask)[0]
        test_idx = np.where(test_mask)[0]
        
        train_tasks = set(metadata.iloc[train_idx]['task'])
        test_tasks_actual = set(metadata.iloc[test_idx]['task'])
        
        print(f"Task-wise split:")
        print(f"  Train tasks: {train_tasks}")
        print(f"  Test tasks: {test_tasks_actual}")
        
        return [{
            'fold': 0,
            'train_idx': train_idx,
            'test_idx': test_idx,
            'train_tasks': train_tasks,
            'test_tasks': test_tasks_actual
        }]
    
    @staticmethod
    def mixed_cv(features, labels, metadata, cv_type='subject', model=None):
        """Perform cross-validation with proper evaluation."""
        
        if cv_type == 'subject':
            cv_splits = BiomechanicalCrossValidator.subject_wise_cv(
                features, labels, metadata
            )
        elif cv_type == 'task':
            cv_splits = BiomechanicalCrossValidator.task_wise_cv(
                features, labels, metadata
            )
        else:
            raise ValueError("cv_type must be 'subject' or 'task'")
        
        cv_scores = []
        
        for split in cv_splits:
            train_idx, test_idx = split['train_idx'], split['test_idx']
            
            X_train, X_test = features[train_idx], features[test_idx]
            y_train, y_test = labels[train_idx], labels[test_idx]
            
            # Train model
            if model is not None:
                model_copy = clone(model)
                model_copy.fit(X_train, y_train)
                
                # Evaluate
                y_pred = model_copy.predict(X_test)
                accuracy = (y_pred == y_test).mean()
                
                cv_scores.append(accuracy)
        
        return cv_scores, cv_splits

# Example usage
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier

# Prepare data
loco = LocomotionData('dataset_phase.parquet')
extractor = LocomotionFeatureExtractor()
features, labels, metadata = extractor.extract_features(loco)

# Encode labels
le = LabelEncoder()
labels_encoded = le.fit_transform(labels)

# Scale features
features_scaled = extractor.fit_transform(features)

# Subject-wise cross-validation
model = RandomForestClassifier(n_estimators=100, random_state=42)
cv_scores, cv_splits = BiomechanicalCrossValidator.mixed_cv(
    features_scaled, labels_encoded, metadata, cv_type='subject', model=model
)

print(f"Subject-wise CV scores: {cv_scores}")
print(f"Mean accuracy: {np.mean(cv_scores):.3f} (+/- {np.std(cv_scores):.3f})")

# Task-wise cross-validation
cv_scores_task, cv_splits_task = BiomechanicalCrossValidator.mixed_cv(
    features_scaled, labels_encoded, metadata, cv_type='task', model=model
)

print(f"Task-wise CV scores: {cv_scores_task}")
```

## Model Validation with Domain Knowledge

### Biomechanical Consistency Checks

```python
class BiomechanicalValidator:
    """Validate ML model predictions using biomechanical domain knowledge."""
    
    def __init__(self, locomotion_data: LocomotionData):
        self.locomotion_data = locomotion_data
        self.domain_rules = self._define_domain_rules()
    
    def _define_domain_rules(self):
        """Define biomechanical domain rules."""
        return {
            'joint_angle_ranges': {
                'hip_flexion_angle_contra_rad': (-0.5, 1.5),
                'knee_flexion_angle_contra_rad': (-0.1, 2.0),
                'ankle_flexion_angle_contra_rad': (-1.0, 0.5)
            },
            'task_characteristics': {
                'level_walking': {
                    'typical_cadence': (90, 130),  # steps/min
                    'knee_rom_range': (0.8, 1.4)   # radians
                },
                'incline_walking': {
                    'increased_hip_flexion': True,
                    'increased_ankle_dorsiflexion': True
                }
            }
        }
    
    def validate_predictions(self, model, X_test, y_test, metadata_test):
        """Validate model predictions using domain knowledge."""
        
        # Get predictions
        y_pred = model.predict(X_test)
        
        validation_results = {
            'accuracy': (y_pred == y_test).mean(),
            'domain_violations': [],
            'consistency_scores': []
        }
        
        # Check each prediction
        for i, (pred, true, meta_row) in enumerate(zip(y_pred, y_test, metadata_test.itertuples())):
            subject = meta_row.subject
            task = meta_row.task
            
            # Get actual data for this sample
            data_3d, features = self.locomotion_data.get_cycles(subject, task)
            
            if data_3d is not None:
                # Calculate biomechanical metrics
                rom_values = np.max(data_3d, axis=1) - np.min(data_3d, axis=1)
                mean_rom = np.mean(rom_values, axis=0)
                
                # Check domain consistency
                violations = self._check_domain_consistency(
                    pred, task, mean_rom, features
                )
                
                if violations:
                    validation_results['domain_violations'].extend(violations)
                
                # Calculate consistency score
                consistency = self._calculate_consistency_score(
                    pred, true, task, mean_rom, features
                )
                validation_results['consistency_scores'].append(consistency)
        
        validation_results['mean_consistency'] = np.mean(
            validation_results['consistency_scores']
        )
        
        return validation_results
    
    def _check_domain_consistency(self, prediction, task, rom_values, features):
        """Check if prediction is consistent with domain knowledge."""
        violations = []
        
        # Task-specific checks
        if task == 'level_walking':
            # Check knee ROM for level walking
            knee_idx = features.index('knee_flexion_angle_contra_rad')
            knee_rom = rom_values[knee_idx]
            
            expected_range = self.domain_rules['task_characteristics']['level_walking']['knee_rom_range']
            if not (expected_range[0] <= knee_rom <= expected_range[1]):
                violations.append({
                    'type': 'knee_rom_violation',
                    'task': task,
                    'expected_range': expected_range,
                    'actual_value': knee_rom
                })
        
        elif task == 'incline_walking':
            # Check for increased hip flexion compared to level walking
            hip_idx = features.index('hip_flexion_angle_contra_rad')
            hip_rom = rom_values[hip_idx]
            
            # This would require comparison with level walking data for same subject
            # Simplified check: hip ROM should be reasonable for incline
            if hip_rom < 0.5:  # Too small for incline walking
                violations.append({
                    'type': 'hip_flexion_violation',
                    'task': task,
                    'actual_value': hip_rom
                })
        
        return violations
    
    def _calculate_consistency_score(self, prediction, true_label, task, rom_values, features):
        """Calculate consistency score between prediction and biomechanics."""
        
        # Base score from prediction accuracy
        base_score = 1.0 if prediction == true_label else 0.0
        
        # Biomechanical plausibility
        plausibility_score = self._calculate_plausibility(task, rom_values, features)
        
        # Combined score
        consistency_score = 0.7 * base_score + 0.3 * plausibility_score
        
        return consistency_score
    
    def _calculate_plausibility(self, task, rom_values, features):
        """Calculate biomechanical plausibility score."""
        
        plausibility = 1.0
        
        # Check joint angle ranges
        for feat_name, expected_range in self.domain_rules['joint_angle_ranges'].items():
            if feat_name in features:
                feat_idx = features.index(feat_name)
                rom_value = rom_values[feat_idx]
                
                # Penalty for values outside expected range
                if not (expected_range[0] <= rom_value <= expected_range[1]):
                    penalty = min(0.5, abs(rom_value - np.mean(expected_range)) / 
                                 (expected_range[1] - expected_range[0]))
                    plausibility -= penalty
        
        return max(0.0, plausibility)

# Example usage
loco = LocomotionData('dataset_phase.parquet')
validator = BiomechanicalValidator(loco)

# Train model
extractor = LocomotionFeatureExtractor()
features, labels, metadata = extractor.extract_features(loco)
features_scaled = extractor.fit_transform(features)
le = LabelEncoder()
labels_encoded = le.fit_transform(labels)

# Split data
X_train, X_test, y_train, y_test, meta_train, meta_test = train_test_split(
    features_scaled, labels_encoded, metadata, test_size=0.2, random_state=42
)

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Validate with domain knowledge
validation_results = validator.validate_predictions(model, X_test, y_test, meta_test)

print(f"Standard accuracy: {validation_results['accuracy']:.3f}")
print(f"Domain consistency score: {validation_results['mean_consistency']:.3f}")
print(f"Domain violations: {len(validation_results['domain_violations'])}")

for violation in validation_results['domain_violations'][:5]:  # Show first 5
    print(f"  {violation}")
```

## Production ML Pipeline

### Complete ML Pipeline

```python
import joblib
from pathlib import Path
import yaml

class LocomotionMLPipeline:
    """Complete ML pipeline for locomotion data analysis."""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path) if config_path else self._default_config()
        self.feature_extractor = None
        self.model = None
        self.label_encoder = None
        self.is_trained = False
        
    def _default_config(self):
        """Default configuration."""
        return {
            'feature_extraction': {
                'feature_types': ['kinematic'],
                'statistical_features': ['mean', 'std', 'rom']
            },
            'model': {
                'type': 'random_forest',
                'params': {'n_estimators': 100, 'random_state': 42}
            },
            'validation': {
                'cv_type': 'subject',
                'cv_folds': 5,
                'test_size': 0.2
            },
            'output': {
                'model_path': 'models/',
                'reports_path': 'reports/'
            }
        }
    
    def _load_config(self, config_path: str):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def train(self, dataset_path: str, target_column: str = 'task'):
        """Train the complete pipeline."""
        
        print("Loading dataset...")
        loco = LocomotionData(dataset_path)
        
        print("Extracting features...")
        self.feature_extractor = LocomotionFeatureExtractor(**self.config['feature_extraction'])
        features, labels, metadata = self.feature_extractor.extract_features(loco)
        
        print("Preprocessing...")
        features_scaled = self.feature_extractor.fit_transform(features)
        
        self.label_encoder = LabelEncoder()
        labels_encoded = self.label_encoder.fit_transform(labels)
        
        print("Training model...")
        # Initialize model based on config
        if self.config['model']['type'] == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(**self.config['model']['params'])
        # Add other model types as needed
        
        # Train model
        self.model.fit(features_scaled, labels_encoded)
        self.is_trained = True
        
        # Validation
        print("Validating model...")
        validation_results = self._validate_model(features_scaled, labels_encoded, metadata)
        
        # Save model
        self._save_pipeline()
        
        return {
            'training_samples': len(features),
            'features_count': len(self.feature_extractor.feature_names),
            'classes': list(self.label_encoder.classes_),
            'validation_results': validation_results
        }
    
    def _validate_model(self, features, labels, metadata):
        """Validate trained model."""
        
        cv_type = self.config['validation']['cv_type']
        cv_folds = self.config['validation']['cv_folds']
        
        if cv_type == 'subject':
            cv_scores, _ = BiomechanicalCrossValidator.mixed_cv(
                features, labels, metadata, cv_type='subject', model=self.model
            )
        else:
            # Standard k-fold
            from sklearn.model_selection import cross_val_score
            cv_scores = cross_val_score(self.model, features, labels, cv=cv_folds)
        
        return {
            'cv_scores': cv_scores,
            'mean_score': np.mean(cv_scores),
            'std_score': np.std(cv_scores)
        }
    
    def predict(self, dataset_path: str, subjects: list = None):
        """Make predictions on new data."""
        
        if not self.is_trained:
            raise ValueError("Pipeline must be trained before making predictions")
        
        # Load data
        loco = LocomotionData(dataset_path)
        
        # Extract features
        features, _, metadata = self.feature_extractor.extract_features(
            loco, subjects=subjects
        )
        
        # Transform features
        features_scaled = self.feature_extractor.transform(features)
        
        # Predict
        predictions_encoded = self.model.predict(features_scaled)
        predictions = self.label_encoder.inverse_transform(predictions_encoded)
        
        # Get prediction probabilities
        probabilities = self.model.predict_proba(features_scaled)
        
        return {
            'predictions': predictions,
            'probabilities': probabilities,
            'metadata': metadata,
            'class_names': self.label_encoder.classes_
        }
    
    def _save_pipeline(self):
        """Save trained pipeline."""
        
        output_dir = Path(self.config['output']['model_path'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save components
        joblib.dump(self.model, output_dir / 'model.pkl')
        joblib.dump(self.feature_extractor, output_dir / 'feature_extractor.pkl')
        joblib.dump(self.label_encoder, output_dir / 'label_encoder.pkl')
        
        # Save config
        with open(output_dir / 'config.yaml', 'w') as f:
            yaml.dump(self.config, f)
        
        print(f"Pipeline saved to {output_dir}")
    
    def load_pipeline(self, model_dir: str):
        """Load trained pipeline."""
        
        model_path = Path(model_dir)
        
        # Load components
        self.model = joblib.load(model_path / 'model.pkl')
        self.feature_extractor = joblib.load(model_path / 'feature_extractor.pkl')
        self.label_encoder = joblib.load(model_path / 'label_encoder.pkl')
        
        # Load config
        with open(model_path / 'config.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.is_trained = True
        print(f"Pipeline loaded from {model_path}")

# Example usage
pipeline = LocomotionMLPipeline()

# Train pipeline
results = pipeline.train('training_dataset_phase.parquet')
print(f"Training completed: {results['validation_results']['mean_score']:.3f} accuracy")

# Make predictions on new data
predictions = pipeline.predict('new_dataset_phase.parquet')
print(f"Predicted {len(predictions['predictions'])} samples")

# Save and load pipeline
pipeline.load_pipeline('models/')
```

This comprehensive ML integration guide provides:

1. **Feature extraction pipelines** optimized for biomechanical data
2. **Scikit-learn integration** with classification and regression examples
3. **Deep learning integration** with PyTorch and TensorFlow
4. **Cross-validation strategies** specific to biomechanical data
5. **Domain knowledge validation** for model predictions
6. **Production-ready pipeline** with configuration management

The examples show how to properly handle the unique challenges of biomechanical data, including subject-wise cross-validation to avoid data leakage and domain knowledge validation to ensure predictions are physiologically plausible.

## Next Steps

- **[Performance Optimization](performance-optimization.md)** - Advanced optimization techniques
- **[Research Platform Integration](research-platform-integration.md)** - Integration with research platforms
- **[Cloud Integration](cloud-integration.md)** - Cloud deployment patterns