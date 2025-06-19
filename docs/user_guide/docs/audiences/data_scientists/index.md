# For Data Scientists

**Accelerate biomechanical machine learning with clean, validated datasets.**

<div class="data-scientist-hero" markdown>

## :material-brain: **ML-Ready Biomechanical Data**

Skip months of data preprocessing. Access standardized, feature-rich gait datasets optimized for machine learning workflows with built-in train/test splits and quality assurance.

[**:material-rocket-launch: Start ML Pipeline**](../../getting_started/quick_start/){ .md-button .md-button--primary }
[**:material-download: Download ML Datasets**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button }

</div>

## :material-lightning-bolt: Why Data Scientists Choose Our Platform

<div class="data-scientist-benefits" markdown>

### :material-database-check: **ML-Optimized Data Pipeline**
**Pre-processed, validated datasets ready for modeling.** Consistent feature engineering, standardized scaling, and quality-assured training data eliminate preprocessing bottlenecks.

### :material-chart-line: **Rich Feature Sets**  
**150+ biomechanical features per sample.** Joint angles, moments, forces, temporal parameters, and derived metrics provide comprehensive movement characterization.

### :material-shuffle-variant: **Built-in Cross-Validation**
**Stratified splits by subject and task.** Proper validation schemes prevent data leakage and ensure robust model evaluation in biomechanical contexts.

### :material-speedometer: **Scalable Processing**
**Efficient data structures for large-scale analysis.** Memory-optimized operations handle thousands of subjects and millions of gait cycles for population-level modeling.

</div>

## :material-code-braces: ML Pipeline Examples

<div class="ml-examples" markdown>

### **Gait Classification Pipeline**

=== "Scikit-learn Workflow"

    ```python
    import pandas as pd
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from locomotion_analysis import LocomotionData
    
    # Load and prepare ML dataset
    data = LocomotionData.from_parquet('ml_training_dataset.parquet')
    
    # Extract features for machine learning
    X, y = data.prepare_ml_features(
        target='task',  # Predict walking task
        features=['kinematic', 'kinetic', 'temporal'],  # Feature groups
        aggregations=['mean', 'std', 'max', 'min']  # Statistical summaries
    )
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Feature names: {X.columns.tolist()[:10]}...")  # First 10 features
    print(f"Target distribution: {y.value_counts()}")
    
    # Create ML pipeline with preprocessing
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])
    
    # Stratified cross-validation (important for biomechanical data)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring='accuracy')
    
    print(f"Cross-validation accuracy: {scores.mean():.3f} ± {scores.std():.3f}")
    
    # Train final model
    pipeline.fit(X, y)
    
    # Feature importance analysis
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': pipeline.named_steps['classifier'].feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("Top 10 most important features:")
    print(feature_importance.head(10))
    ```

=== "Deep Learning with PyTorch"

    ```python
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import LabelEncoder
    import numpy as np
    
    # Load time-series data for deep learning
    data = LocomotionData.from_parquet('timeseries_dataset.parquet')
    
    # Prepare sequential data (150 time points per gait cycle)
    X, y = data.prepare_sequential_features(
        target='pathology',  # Normal vs. pathological gait
        sequence_length=150,  # Full gait cycle
        features=['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
    )
    
    # Convert to PyTorch tensors
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    X_tensor = torch.FloatTensor(X)  # Shape: (n_samples, 150, n_features)
    y_tensor = torch.LongTensor(y_encoded)
    
    # Create data loaders
    dataset = TensorDataset(X_tensor, y_tensor)
    train_loader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # Define LSTM model for gait classification
    class GaitLSTM(nn.Module):
        def __init__(self, input_size, hidden_size, num_layers, num_classes):
            super(GaitLSTM, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
            self.fc = nn.Linear(hidden_size, num_classes)
            self.dropout = nn.Dropout(0.3)
            
        def forward(self, x):
            h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
            c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
            
            out, _ = self.lstm(x, (h0, c0))
            out = self.dropout(out[:, -1, :])  # Take last time step
            out = self.fc(out)
            return out
    
    # Initialize model and training components
    model = GaitLSTM(input_size=X.shape[2], hidden_size=64, num_layers=2, num_classes=len(le.classes_))
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training loop
    model.train()
    for epoch in range(100):
        total_loss = 0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        
        if (epoch + 1) % 10 == 0:
            print(f'Epoch [{epoch+1}/100], Loss: {total_loss/len(train_loader):.4f}')
    
    # Model evaluation
    model.eval()
    with torch.no_grad():
        outputs = model(X_tensor)
        _, predicted = torch.max(outputs.data, 1)
        accuracy = (predicted == y_tensor).sum().item() / len(y_tensor)
        print(f'Training Accuracy: {accuracy:.3f}')
    ```

=== "Feature Engineering Pipeline"

    ```python
    import pandas as pd
    import numpy as np
    from scipy import stats
    from sklearn.decomposition import PCA
    from sklearn.feature_selection import SelectKBest, f_classif
    
    # Advanced feature engineering for biomechanical data
    class BiomechanicalFeatureEngineer:
        def __init__(self):
            self.pca_kinematic = PCA(n_components=10)
            self.pca_kinetic = PCA(n_components=8)
            self.feature_selector = SelectKBest(f_classif, k=50)
            
        def extract_temporal_features(self, data):
            """Extract temporal-spatial parameters"""
            features = {}
            
            # Gait cycle timing
            features['cycle_duration'] = data.groupby(['subject', 'step'])['phase_percent'].count()
            features['stance_duration'] = data[data['phase_percent'] <= 60].groupby(['subject', 'step']).size()
            features['swing_duration'] = data[data['phase_percent'] > 60].groupby(['subject', 'step']).size()
            
            # Asymmetry indices
            ipsi_features = [col for col in data.columns if 'ipsi' in col]
            contra_features = [col for col in data.columns if 'contra' in col]
            
            for ipsi_col, contra_col in zip(ipsi_features, contra_features):
                if ipsi_col.replace('_ipsi_', '_contra_') == contra_col:
                    asym_name = ipsi_col.replace('_ipsi_', '_asymmetry_')
                    features[asym_name] = np.abs(data[ipsi_col] - data[contra_col]) / (data[ipsi_col] + data[contra_col] + 1e-8)
            
            return features
            
        def extract_kinematic_features(self, data):
            """Extract kinematic features with domain knowledge"""
            features = {}
            
            # Joint angle ranges and peaks
            angle_cols = [col for col in data.columns if 'angle' in col and 'rad' in col]
            for col in angle_cols:
                joint_data = data.groupby(['subject', 'step'])[col]
                features[f'{col}_rom'] = joint_data.max() - joint_data.min()
                features[f'{col}_peak'] = joint_data.max()
                features[f'{col}_min'] = joint_data.min()
                features[f'{col}_mean'] = joint_data.mean()
                features[f'{col}_std'] = joint_data.std()
                
                # Gait phase-specific features
                stance_data = data[data['phase_percent'] <= 60]
                swing_data = data[data['phase_percent'] > 60]
                
                if not stance_data.empty:
                    features[f'{col}_stance_peak'] = stance_data.groupby(['subject', 'step'])[col].max()
                if not swing_data.empty:
                    features[f'{col}_swing_peak'] = swing_data.groupby(['subject', 'step'])[col].max()
            
            return features
            
        def extract_kinetic_features(self, data):
            """Extract kinetic features"""
            features = {}
            
            # Joint moment features
            moment_cols = [col for col in data.columns if 'moment' in col and 'Nm' in col]
            for col in moment_cols:
                joint_data = data.groupby(['subject', 'step'])[col]
                features[f'{col}_peak_ext'] = joint_data.min()  # Extension moments (negative)
                features[f'{col}_peak_flex'] = joint_data.max()  # Flexion moments (positive)
                features[f'{col}_impulse'] = joint_data.apply(lambda x: np.trapz(np.abs(x)))
                features[f'{col}_power'] = joint_data.apply(lambda x: np.mean(x**2))
            
            # Ground reaction force features
            grf_cols = [col for col in data.columns if 'grf' in col and 'N' in col]
            for col in grf_cols:
                force_data = data.groupby(['subject', 'step'])[col]
                features[f'{col}_peak1'] = force_data.apply(lambda x: x.iloc[:30].max())  # Loading response
                features[f'{col}_peak2'] = force_data.apply(lambda x: x.iloc[40:60].max())  # Push-off
                features[f'{col}_impulse'] = force_data.apply(lambda x: np.trapz(x))
            
            return features
            
        def fit_transform(self, data, target):
            """Complete feature engineering pipeline"""
            # Extract all feature types
            temporal_features = self.extract_temporal_features(data)
            kinematic_features = self.extract_kinematic_features(data)
            kinetic_features = self.extract_kinetic_features(data)
            
            # Combine features
            all_features = {**temporal_features, **kinematic_features, **kinetic_features}
            feature_df = pd.DataFrame(all_features)
            
            # Handle missing values
            feature_df = feature_df.fillna(feature_df.mean())
            
            # Dimensionality reduction for kinematic/kinetic features
            kinematic_cols = [col for col in feature_df.columns if 'angle' in col]
            kinetic_cols = [col for col in feature_df.columns if 'moment' in col or 'grf' in col]
            
            if kinematic_cols:
                pca_kinematic = self.pca_kinematic.fit_transform(feature_df[kinematic_cols])
                pca_kinematic_df = pd.DataFrame(pca_kinematic, 
                                              columns=[f'pca_kinematic_{i}' for i in range(pca_kinematic.shape[1])])
                feature_df = pd.concat([feature_df.drop(columns=kinematic_cols), pca_kinematic_df], axis=1)
            
            if kinetic_cols:
                pca_kinetic = self.pca_kinetic.fit_transform(feature_df[kinetic_cols])
                pca_kinetic_df = pd.DataFrame(pca_kinetic, 
                                            columns=[f'pca_kinetic_{i}' for i in range(pca_kinetic.shape[1])])
                feature_df = pd.concat([feature_df.drop(columns=kinetic_cols), pca_kinetic_df], axis=1)
            
            # Feature selection
            X_selected = self.feature_selector.fit_transform(feature_df, target)
            selected_features = feature_df.columns[self.feature_selector.get_support()]
            
            return pd.DataFrame(X_selected, columns=selected_features)
    
    # Usage example
    data = LocomotionData.from_parquet('training_data.parquet')
    engineer = BiomechanicalFeatureEngineer()
    
    # Engineer features for pathology classification
    X_engineered = engineer.fit_transform(data.dataframe, data.dataframe['pathology'])
    print(f"Engineered feature matrix: {X_engineered.shape}")
    print(f"Selected features: {X_engineered.columns.tolist()}")
    ```

**Output:** Production-ready ML features with domain-specific engineering

</div>

## :material-database: ML-Ready Datasets

<div class="ml-datasets" markdown>

| Dataset | ML Applications | Samples | Features | Tasks |
|---------|-----------------|---------|----------|-------|
| **Classification Dataset** | Task/pathology prediction | 2,000+ cycles | 150+ features | Level walking, stairs, inclines |
| **Time Series Dataset** | Sequential modeling | 1,500+ cycles | 6 joints × 150 time points | LSTM/RNN training |
| **Regression Dataset** | Continuous outcome prediction | 1,200+ cycles | 200+ derived features | Age, BMI, performance metrics |
| **Clustering Dataset** | Gait pattern discovery | 3,000+ cycles | PCA-reduced features | Unsupervised analysis |

**ML-Optimized Features:**
- **Kinematic**: Joint angles, velocities, ranges of motion
- **Kinetic**: Joint moments, powers, ground reaction forces
- **Temporal**: Step timing, phase durations, cadence
- **Spatial**: Stride length, step width, foot progression
- **Derived**: Asymmetry indices, stability measures, efficiency metrics

</div>

## :material-brain: ML Methodologies

<div class="ml-methodologies" markdown>

<div class="method-card supervised" markdown>

### :material-target: **Supervised Learning**

**Perfect for:** Classification, regression, clinical prediction

**Common Applications:**
- **Pathology Detection**: Normal vs. abnormal gait patterns
- **Task Classification**: Walking, running, stair climbing
- **Fall Risk Assessment**: Mobility and stability prediction
- **Treatment Outcome**: Therapy effectiveness modeling

**Best Practices:**
- Subject-stratified cross-validation to prevent overfitting
- Feature engineering with biomechanical domain knowledge
- Class balancing for rare pathology conditions
- Temporal feature aggregation for robust predictions

[**Explore Supervised ML :material-arrow-right:**](supervised-learning/){ .md-button .ml-button }

</div>

<div class="method-card unsupervised" markdown>

### :material-cluster: **Unsupervised Learning**

**Perfect for:** Pattern discovery, phenotyping, data exploration

**Common Applications:**
- **Gait Phenotyping**: Discover movement subtypes
- **Anomaly Detection**: Identify unusual gait patterns
- **Dimensionality Reduction**: Visualize high-dimensional gait data
- **Clustering Analysis**: Group similar movement strategies

**Best Practices:**
- PCA for feature visualization and noise reduction
- t-SNE/UMAP for non-linear manifold exploration
- K-means clustering with biomechanical validation
- Hierarchical clustering for interpretable groupings

[**Explore Unsupervised ML :material-arrow-right:**](unsupervised-learning/){ .md-button .ml-button }

</div>

<div class="method-card deep-learning" markdown>

### :material-brain: **Deep Learning**

**Perfect for:** Sequential modeling, complex pattern recognition

**Common Applications:**
- **LSTM Networks**: Temporal gait sequence modeling
- **CNNs**: Gait image and spectrogram analysis
- **Autoencoders**: Gait feature representation learning
- **GANs**: Synthetic gait data generation

**Best Practices:**
- Sequence-to-sequence modeling for temporal patterns
- Attention mechanisms for important gait phases
- Transfer learning from larger movement datasets
- Regularization for limited biomechanical data

[**Explore Deep Learning :material-arrow-right:**](deep-learning/){ .md-button .ml-button }

</div>

</div>

## :material-chart-timeline: Model Evaluation

<div class="model-evaluation" markdown>

### **Biomechanics-Specific Validation**

```python
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
import matplotlib.pyplot as plt
import seaborn as sns

class BiomechanicalModelEvaluator:
    def __init__(self):
        self.results = {}
        
    def evaluate_classification(self, model, X, y, groups, task_names=None):
        """Evaluate classification with subject-based cross-validation"""
        
        # Use GroupKFold to ensure no subject appears in both train and test
        gkf = GroupKFold(n_splits=5)
        
        scores = []
        all_y_true = []
        all_y_pred = []
        
        for train_idx, test_idx in gkf.split(X, y, groups):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Fit and predict
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            # Store results
            scores.append(model.score(X_test, y_test))
            all_y_true.extend(y_test)
            all_y_pred.extend(y_pred)
        
        # Calculate overall metrics
        self.results['cv_scores'] = scores
        self.results['mean_accuracy'] = np.mean(scores)
        self.results['std_accuracy'] = np.std(scores)
        
        # Classification report
        if task_names:
            report = classification_report(all_y_true, all_y_pred, 
                                         target_names=task_names, output_dict=True)
        else:
            report = classification_report(all_y_true, all_y_pred, output_dict=True)
        
        self.results['classification_report'] = report
        
        # Confusion matrix
        cm = confusion_matrix(all_y_true, all_y_pred)
        self.results['confusion_matrix'] = cm
        
        return self.results
    
    def plot_results(self, task_names=None):
        """Create comprehensive evaluation plots"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Cross-validation scores
        axes[0, 0].bar(range(len(self.results['cv_scores'])), self.results['cv_scores'])
        axes[0, 0].axhline(y=self.results['mean_accuracy'], color='r', linestyle='--', 
                          label=f'Mean: {self.results["mean_accuracy"]:.3f}')
        axes[0, 0].set_xlabel('Fold')
        axes[0, 0].set_ylabel('Accuracy')
        axes[0, 0].set_title('Cross-Validation Scores')
        axes[0, 0].legend()
        
        # Confusion matrix
        sns.heatmap(self.results['confusion_matrix'], annot=True, fmt='d', 
                   xticklabels=task_names, yticklabels=task_names, ax=axes[0, 1])
        axes[0, 1].set_title('Confusion Matrix')
        axes[0, 1].set_xlabel('Predicted')
        axes[0, 1].set_ylabel('Actual')
        
        # Precision-recall by class
        report = self.results['classification_report']
        if task_names:
            classes = task_names
        else:
            classes = [k for k in report.keys() if k.isdigit() or k.replace('.', '').isdigit()]
        
        precision = [report[cls]['precision'] for cls in classes if cls in report]
        recall = [report[cls]['recall'] for cls in classes if cls in report]
        f1 = [report[cls]['f1-score'] for cls in classes if cls in report]
        
        x = np.arange(len(classes))
        width = 0.25
        
        axes[1, 0].bar(x - width, precision, width, label='Precision')
        axes[1, 0].bar(x, recall, width, label='Recall')  
        axes[1, 0].bar(x + width, f1, width, label='F1-Score')
        axes[1, 0].set_xlabel('Class')
        axes[1, 0].set_ylabel('Score')
        axes[1, 0].set_title('Per-Class Performance')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(classes, rotation=45)
        axes[1, 0].legend()
        
        # Performance summary
        summary_text = f"""
        Overall Accuracy: {self.results['mean_accuracy']:.3f} ± {self.results['std_accuracy']:.3f}
        Macro Avg Precision: {report['macro avg']['precision']:.3f}
        Macro Avg Recall: {report['macro avg']['recall']:.3f}
        Macro Avg F1-Score: {report['macro avg']['f1-score']:.3f}
        """
        axes[1, 1].text(0.1, 0.5, summary_text, fontsize=12, verticalalignment='center')
        axes[1, 1].axis('off')
        axes[1, 1].set_title('Performance Summary')
        
        plt.tight_layout()
        plt.savefig('model_evaluation_report.png', dpi=300, bbox_inches='tight')
        plt.show()

# Usage example
evaluator = BiomechanicalModelEvaluator()
results = evaluator.evaluate_classification(
    model=trained_model, 
    X=X_test, 
    y=y_test, 
    groups=subject_groups,
    task_names=['Level Walking', 'Incline Walking', 'Stair Climbing']
)
evaluator.plot_results(task_names=['Level Walking', 'Incline Walking', 'Stair Climbing'])
```

</div>

## :material-rocket-launch: Data Science Quick Start

<div class="getting-started-datascience" markdown>

### **Choose Your ML Approach**

=== ":material-timer: Rapid Prototyping (45 minutes)"

    **Perfect for:** Proof of concept, algorithm exploration
    
    1. Load pre-processed ML dataset (10 min)
    2. Perform basic feature selection (10 min)
    3. Train baseline classifier (15 min)
    4. Evaluate with proper cross-validation (10 min)
    
    **Outcome:** Working ML pipeline with evaluation metrics
    
    [:material-rocket-launch: Quick ML Pipeline](../../getting_started/quick_start/){ .md-button .md-button--primary }

=== ":material-brain: Deep Learning (3-5 hours)"

    **Perfect for:** Sequential modeling, complex patterns
    
    1. Prepare time-series data format (60 min)
    2. Design neural network architecture (90 min)
    3. Implement training with validation (120 min)
    4. Hyperparameter tuning and evaluation (60 min)
    
    **Outcome:** Production-ready deep learning model
    
    [:material-book-open: Deep Learning Guide](deep-learning/){ .md-button }

=== ":material-chart-line: Production Deployment (ongoing)"

    **Perfect for:** Scalable ML systems, real-time inference
    
    1. Model optimization and serialization
    2. API endpoint development and testing
    3. Monitoring and performance tracking
    4. Continuous learning and model updates
    
    **Outcome:** Deployed ML system with monitoring
    
    [:material-cloud: Production ML](production-ml/){ .md-button }

</div>

## :material-help-circle: Data Science Support

<div name="datascience-support" markdown>

**ML Development Resources:**

- :material-book-code: **[Feature Engineering Guide](feature-engineering/)** - Domain-specific feature extraction
- :material-chart-line: **[Model Selection Guide](model-selection/)** - Algorithm recommendations by task
- :material-test-tube: **[Validation Strategies](validation-strategies/)** - Proper evaluation for biomechanical data
- :material-brain: **[Deep Learning Examples](deep-learning/)** - Neural network architectures
- :material-github: **[ML Pipelines](https://github.com/your-org/biomechanical-ml-pipelines)** - Production-ready code examples

**Advanced Analysis Support:**
- Time-series analysis for sequential gait data
- Multi-level modeling for hierarchical data structures
- Bayesian approaches for uncertainty quantification
- Interpretable ML for clinical decision support

</div>

---

<div class="datascience-cta" markdown>

## Ready to Build ML Models with Biomechanical Data?

**Access clean, validated datasets optimized for machine learning with comprehensive feature engineering support.**

[**:material-rocket-launch: Start ML Pipeline**](../../getting_started/quick_start/){ .md-button .md-button--primary .cta-button }
[**:material-download: Download ML Data**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button .cta-button }

*Accelerate discovery with ML-ready biomechanical datasets.*

</div>