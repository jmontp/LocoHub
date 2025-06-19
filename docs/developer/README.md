# Developer Workflows

Comprehensive guide for developers contributing to or extending the locomotion data standardization platform.

## Quick Navigation

- **[Contributing Code](contributing.md)** - Guidelines for contributing to the platform
- **[Creating Dataset Converters](dataset-converters.md)** - Adding support for new data sources
- **[Extending Validation Rules](validation-rules.md)** - Adding custom validation logic
- **[Architecture Overview](architecture.md)** - Platform architecture and design patterns

## Development Environment Setup

### Prerequisites

```bash
# Python 3.8+ required
python --version

# Install development dependencies
pip install -r requirements-dev.txt

# Install platform in development mode
pip install -e .

# Install pre-commit hooks
pre-commit install
```

### Required Tools

- **Python 3.8+**: Core runtime
- **Git**: Version control
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking

### Development Dependencies

```txt
# requirements-dev.txt
pytest>=6.0.0
pytest-cov>=2.10.0
black>=21.0.0
flake8>=3.9.0
mypy>=0.812
pre-commit>=2.10.0
jupyter>=1.0.0
matplotlib>=3.3.0
seaborn>=0.11.0
```

## Architecture Overview

### Core Components

```
locomotion-data-standardization/
├── lib/                          # Core library
│   ├── core/                     # Data analysis and features
│   │   ├── locomotion_analysis.py    # Main LocomotionData class
│   │   ├── feature_constants.py      # Standard feature definitions
│   │   └── examples.py               # Usage examples
│   └── validation/               # Validation and quality assessment
│       ├── dataset_validator_phase.py # Main validation engine
│       ├── step_classifier.py        # Step-level validation
│       ├── phase_validator.py         # Phase data validation
│       └── range_optimizer.py         # Validation range optimization
├── contributor_scripts/          # Dataset conversion utilities
│   ├── create_dataset_release.py     # Release management
│   ├── validate_phase_dataset.py     # CLI validation
│   └── [dataset]_converters/         # Dataset-specific converters
├── docs/                         # Documentation
│   ├── api/                      # API reference
│   ├── integration/              # Integration guides
│   ├── tutorials/                # User tutorials
│   └── developer/               # Developer documentation
└── tests/                       # Test suite
    ├── test_*.py                # Unit tests
    ├── demo_*.py               # Visual demos
    └── sample_plots/           # Expected test outputs
```

### Design Principles

1. **Single Responsibility**: Each module has a clear, focused purpose
2. **Standard Compliance**: Strict adherence to variable naming conventions
3. **Explicit Error Handling**: Clear error messages over silent failures
4. **Performance Optimized**: Efficient 3D array operations
5. **Extensible**: Easy to add new datasets, validation rules, and features

### Key Interfaces

#### LocomotionData Interface

```python
# Core data access pattern
loco = LocomotionData('dataset_phase.parquet')
data_3d, features = loco.get_cycles(subject, task)
# Returns: (n_cycles, 150, n_features) array
```

#### Validation Interface

```python
# Validation pattern
validator = DatasetValidator('dataset_phase.parquet')
report_path = validator.run_validation()
# Returns: path to validation report
```

#### Feature Constants Interface

```python
# Standard feature ordering
from lib.core.feature_constants import ANGLE_FEATURES, get_feature_list
kinematic_vars = get_feature_list('kinematic')
```

## Common Development Tasks

### Adding New Analysis Methods

```python
# 1. Add method to LocomotionData class
class LocomotionData:
    def new_analysis_method(self, subject: str, task: str, 
                           custom_param: float = 1.0) -> Dict:
        """
        New analysis method with clear documentation.
        
        Parameters
        ----------
        subject : str
            Subject ID
        task : str  
            Task name
        custom_param : float
            Custom parameter with default value
            
        Returns
        -------
        dict
            Analysis results with documented structure
            
        Examples
        --------
        >>> loco = LocomotionData('data.parquet')
        >>> result = loco.new_analysis_method('SUB01', 'level_walking')
        >>> print(result['metric_name'])
        """
        # Get data using standard interface
        data_3d, features = self.get_cycles(subject, task)
        
        if data_3d is None:
            return {}
            
        # Perform analysis
        results = self._compute_new_metric(data_3d, custom_param)
        
        return {
            'subject': subject,
            'task': task,
            'metric_name': results,
            'parameters': {'custom_param': custom_param}
        }
    
    def _compute_new_metric(self, data_3d: np.ndarray, param: float) -> float:
        """Private helper method for computation."""
        # Implementation details
        return np.mean(data_3d) * param

# 2. Add comprehensive tests
def test_new_analysis_method():
    """Test new analysis method."""
    loco = LocomotionData('test_data.parquet')
    
    # Test basic functionality
    result = loco.new_analysis_method('TEST_SUBJECT', 'level_walking')
    assert 'metric_name' in result
    assert result['subject'] == 'TEST_SUBJECT'
    
    # Test edge cases
    empty_result = loco.new_analysis_method('NONEXISTENT', 'level_walking')
    assert empty_result == {}
    
    # Test parameter variations
    result_custom = loco.new_analysis_method('TEST_SUBJECT', 'level_walking', 
                                           custom_param=2.0)
    assert result_custom['parameters']['custom_param'] == 2.0

# 3. Add to examples.py
def example_new_analysis():
    """Example demonstrating new analysis method."""
    loco = LocomotionData('example_data.parquet')
    
    # Analyze all subjects
    results = {}
    for subject in loco.subjects:
        subject_results = {}
        for task in loco.tasks:
            result = loco.new_analysis_method(subject, task)
            if result:  # Check for valid results
                subject_results[task] = result
        results[subject] = subject_results
    
    return results
```

### Adding New Validation Rules

```python
# 1. Extend StepClassifier with new validation
class StepClassifier:
    def validate_custom_constraint(self, data_array: np.ndarray, 
                                  task: str) -> List[Dict]:
        """Add custom biomechanical constraint validation."""
        failures = []
        
        # Example: Hip-knee coordination constraint
        if 'hip_flexion_angle' in self.current_features:
            hip_idx = self.current_features.index('hip_flexion_angle_contra_rad')
            knee_idx = self.current_features.index('knee_flexion_angle_contra_rad')
            
            for step_idx in range(data_array.shape[0]):
                hip_data = data_array[step_idx, :, hip_idx]
                knee_data = data_array[step_idx, :, knee_idx]
                
                # Check coordination at key phases
                for phase_idx in [0, 37, 75, 112]:  # 0%, 25%, 50%, 75%
                    if phase_idx < len(hip_data):
                        hip_val = hip_data[phase_idx]
                        knee_val = knee_data[phase_idx]
                        
                        # Custom constraint: knee should flex more than hip in swing
                        if phase_idx > 75 and task == 'level_walking':  # Swing phase
                            if knee_val < hip_val:  # Constraint violation
                                failures.append({
                                    'step': step_idx,
                                    'phase': phase_idx * 100 / 150,
                                    'constraint': 'hip_knee_coordination',
                                    'hip_value': hip_val,
                                    'knee_value': knee_val,
                                    'expected': 'knee > hip in swing phase'
                                })
        
        return failures

# 2. Integrate into main validation pipeline
def _validate_step_3d_data(self, step_data_3d: np.ndarray, features: List[str], 
                          task: str, validation_type: str, subject: str, 
                          step_idx: int, global_step_idx: int = None) -> List[Dict]:
    """Enhanced validation with custom constraints."""
    
    # Existing validation
    failures = self.step_classifier.validate_data_against_specs(
        step_data_array, task, step_task_mapping, validation_type
    )
    
    # Add custom validation
    custom_failures = self.step_classifier.validate_custom_constraint(
        step_data_array, task
    )
    
    # Combine failures
    all_failures = failures + custom_failures
    
    # Add metadata
    for failure in all_failures:
        failure['subject'] = subject
        failure['step_index'] = step_idx
        
    return all_failures

# 3. Add tests for new validation
def test_custom_constraint_validation():
    """Test custom constraint validation."""
    classifier = StepClassifier()
    
    # Create test data that violates constraint
    test_data = np.random.randn(1, 150, 6)  # 1 step, 150 points, 6 features
    
    # Set up violation: knee < hip in swing phase
    hip_idx = 0  # Assume hip is first feature
    knee_idx = 2  # Assume knee is third feature
    
    swing_phases = range(75, 150)  # Swing phase
    for phase in swing_phases:
        test_data[0, phase, hip_idx] = 1.0  # Hip flexion
        test_data[0, phase, knee_idx] = 0.5  # Knee flexion (violation)
    
    # Run validation
    failures = classifier.validate_custom_constraint(test_data, 'level_walking')
    
    # Should detect violations
    assert len(failures) > 0
    assert failures[0]['constraint'] == 'hip_knee_coordination'
```

### Creating Dataset Converters

```python
# 1. Create converter class following standard pattern
class NewDatasetConverter:
    """Converter for NewDataset to standard format."""
    
    def __init__(self, input_path: str, output_dir: str):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Standard variable mapping
        self.variable_mapping = {
            'RHipAngles_X': 'hip_flexion_angle_ipsi_rad',
            'LHipAngles_X': 'hip_flexion_angle_contra_rad',
            'RKneeAngles_X': 'knee_flexion_angle_ipsi_rad',
            'LKneeAngles_X': 'knee_flexion_angle_contra_rad',
            'RAnkleAngles_X': 'ankle_flexion_angle_ipsi_rad',
            'LAnkleAngles_X': 'ankle_flexion_angle_contra_rad'
        }
    
    def convert_to_phase_indexed(self) -> str:
        """Convert dataset to phase-indexed format."""
        
        print(f"Converting {self.input_path} to phase-indexed format...")
        
        # 1. Load original data
        raw_data = self._load_raw_data()
        
        # 2. Detect gait cycles
        cycles_data = self._detect_gait_cycles(raw_data)
        
        # 3. Phase normalize to 150 points
        phase_data = self._phase_normalize(cycles_data)
        
        # 4. Apply variable mapping
        standardized_data = self._standardize_variables(phase_data)
        
        # 5. Add metadata
        final_data = self._add_metadata(standardized_data)
        
        # 6. Save as parquet
        output_path = self.output_dir / f"{self.input_path.stem}_phase.parquet"
        final_data.to_parquet(output_path, index=False)
        
        print(f"Conversion completed: {output_path}")
        return str(output_path)
    
    def _load_raw_data(self) -> pd.DataFrame:
        """Load raw dataset (implement based on format)."""
        if self.input_path.suffix == '.csv':
            return pd.read_csv(self.input_path)
        elif self.input_path.suffix == '.mat':
            import scipy.io
            mat_data = scipy.io.loadmat(self.input_path)
            # Convert to DataFrame based on structure
            return self._mat_to_dataframe(mat_data)
        else:
            raise ValueError(f"Unsupported file format: {self.input_path.suffix}")
    
    def _detect_gait_cycles(self, data: pd.DataFrame) -> pd.DataFrame:
        """Detect individual gait cycles."""
        # Implementation depends on available signals
        # Common approaches:
        # 1. Heel strike detection from force plates
        # 2. Foot contact events from motion capture
        # 3. Algorithmic detection from kinematics
        
        cycles = []
        for subject in data['subject'].unique():
            subject_data = data[data['subject'] == subject]
            
            for task in data['task'].unique():
                task_data = subject_data[subject_data['task'] == task]
                
                if len(task_data) == 0:
                    continue
                
                # Detect cycles (simplified example)
                cycle_events = self._find_heel_strikes(task_data)
                
                for i in range(len(cycle_events) - 1):
                    start_idx = cycle_events[i]
                    end_idx = cycle_events[i + 1]
                    
                    cycle_data = task_data.iloc[start_idx:end_idx].copy()
                    cycle_data['cycle'] = i
                    cycles.append(cycle_data)
        
        return pd.concat(cycles, ignore_index=True)
    
    def _phase_normalize(self, cycles_data: pd.DataFrame) -> pd.DataFrame:
        """Normalize each cycle to 150 points."""
        normalized_cycles = []
        
        for (subject, task, cycle), group in cycles_data.groupby(['subject', 'task', 'cycle']):
            if len(group) < 50:  # Skip very short cycles
                continue
            
            # Interpolate to 150 points
            original_indices = np.arange(len(group))
            target_indices = np.linspace(0, len(group) - 1, 150)
            
            normalized_data = {
                'subject': subject,
                'task': task,
                'cycle': cycle,
                'phase_percent': np.linspace(0, 100, 150)
            }
            
            # Interpolate each variable
            for col in group.columns:
                if col not in ['subject', 'task', 'cycle'] and pd.api.types.is_numeric_dtype(group[col]):
                    interpolated = np.interp(target_indices, original_indices, group[col].values)
                    normalized_data[col] = interpolated
            
            normalized_df = pd.DataFrame(normalized_data)
            normalized_cycles.append(normalized_df)
        
        return pd.concat(normalized_cycles, ignore_index=True)
    
    def _standardize_variables(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply standard variable naming."""
        standardized = data.copy()
        
        # Rename variables according to mapping
        for old_name, new_name in self.variable_mapping.items():
            if old_name in standardized.columns:
                standardized[new_name] = standardized[old_name]
                standardized.drop(columns=[old_name], inplace=True)
        
        # Convert units if necessary (e.g., degrees to radians)
        angle_columns = [col for col in standardized.columns if 'angle' in col and 'rad' in col]
        for col in angle_columns:
            if col.replace('_rad', '_deg') in data.columns:
                # Assuming original was in degrees
                standardized[col] = np.deg2rad(standardized[col])
        
        return standardized
    
    def _add_metadata(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add required metadata columns."""
        final_data = data.copy()
        
        # Add step numbers (consecutive numbering within subject-task)
        final_data['step'] = 0
        for (subject, task), group in final_data.groupby(['subject', 'task']):
            step_numbers = np.arange(len(group))
            final_data.loc[group.index, 'step'] = step_numbers
        
        return final_data
    
    def _find_heel_strikes(self, data: pd.DataFrame) -> List[int]:
        """Find heel strike events (simplified implementation)."""
        # This would typically use ground reaction force or kinematic signals
        # Simplified example using periodic assumption
        estimated_cycle_length = len(data) // 5  # Assume ~5 cycles
        heel_strikes = list(range(0, len(data), estimated_cycle_length))
        return heel_strikes

# 2. Create CLI for the converter
def main():
    """CLI for NewDataset converter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert NewDataset to standard format")
    parser.add_argument('input_path', help='Path to input dataset')
    parser.add_argument('--output-dir', default='./converted_datasets', 
                       help='Output directory for converted data')
    
    args = parser.parse_args()
    
    # Convert dataset
    converter = NewDatasetConverter(args.input_path, args.output_dir)
    output_path = converter.convert_to_phase_indexed()
    
    # Validate converted dataset
    print("Validating converted dataset...")
    from lib.validation.dataset_validator_phase import DatasetValidator
    
    validator = DatasetValidator(output_path)
    report_path = validator.run_validation()
    
    print(f"Conversion completed successfully!")
    print(f"Dataset: {output_path}")
    print(f"Validation report: {report_path}")

if __name__ == '__main__':
    main()

# 3. Add tests for converter
def test_new_dataset_converter():
    """Test NewDataset converter."""
    # Create test data
    test_data = create_test_raw_data()
    test_file = 'test_input.csv'
    test_data.to_csv(test_file, index=False)
    
    try:
        # Run converter
        converter = NewDatasetConverter(test_file, 'test_output')
        output_path = converter.convert_to_phase_indexed()
        
        # Verify output
        assert Path(output_path).exists()
        
        # Load and validate structure
        converted_data = pd.read_parquet(output_path)
        
        # Check required columns
        required_cols = ['subject', 'task', 'phase_percent', 'step']
        for col in required_cols:
            assert col in converted_data.columns
        
        # Check phase normalization
        cycles = converted_data.groupby(['subject', 'task', 'step']).size()
        assert all(cycles == 150), "All cycles should have 150 points"
        
        # Check variable naming
        standard_vars = ['hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad']
        for var in standard_vars:
            if var in converter.variable_mapping.values():
                assert var in converted_data.columns
        
    finally:
        # Cleanup
        if Path(test_file).exists():
            Path(test_file).unlink()
        if Path('test_output').exists():
            import shutil
            shutil.rmtree('test_output')

def create_test_raw_data() -> pd.DataFrame:
    """Create test data for converter testing."""
    n_points = 1000
    n_subjects = 2
    
    data = []
    for subject_id in range(n_subjects):
        subject_name = f"SUB{subject_id:02d}"
        
        # Generate synthetic gait data
        time_points = np.linspace(0, 10, n_points)  # 10 seconds
        
        for task in ['level_walking', 'incline_walking']:
            # Synthetic joint angles (in degrees)
            hip_angle = 20 * np.sin(2 * np.pi * time_points) + np.random.normal(0, 2, n_points)
            knee_angle = 30 * np.sin(2 * np.pi * time_points + np.pi/4) + np.random.normal(0, 2, n_points)
            ankle_angle = 15 * np.sin(2 * np.pi * time_points + np.pi/2) + np.random.normal(0, 1, n_points)
            
            task_data = pd.DataFrame({
                'subject': subject_name,
                'task': task,
                'time': time_points,
                'RHipAngles_X': hip_angle,
                'LHipAngles_X': hip_angle + np.random.normal(0, 1, n_points),
                'RKneeAngles_X': knee_angle,
                'LKneeAngles_X': knee_angle + np.random.normal(0, 1, n_points),
                'RAnkleAngles_X': ankle_angle,
                'LAnkleAngles_X': ankle_angle + np.random.normal(0, 1, n_points)
            })
            
            data.append(task_data)
    
    return pd.concat(data, ignore_index=True)
```

## Testing Guidelines

### Test Structure

```python
# tests/test_new_feature.py
import pytest
import numpy as np
import pandas as pd
from lib.core.locomotion_analysis import LocomotionData

class TestNewFeature:
    """Test suite for new feature."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        # Create minimal valid dataset
        n_cycles = 3
        n_points = 150
        n_features = 6
        
        data = []
        for cycle in range(n_cycles):
            cycle_data = {
                'subject': 'TEST_SUB',
                'task': 'level_walking',
                'step': cycle,
                'phase_percent': np.linspace(0, 100, n_points)
            }
            
            # Add standard kinematic features
            features = ['hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 
                       'ankle_flexion_angle_contra_rad', 'hip_flexion_angle_ipsi_rad',
                       'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad']
            
            for i, feature in enumerate(features):
                # Generate realistic gait pattern
                phase_rad = np.linspace(0, 2*np.pi, n_points)
                cycle_data[feature] = np.sin(phase_rad + i*np.pi/6) * 0.5 + np.random.normal(0, 0.1, n_points)
            
            cycle_df = pd.DataFrame(cycle_data)
            data.append(cycle_df)
        
        return pd.concat(data, ignore_index=True)
    
    @pytest.fixture
    def locomotion_data(self, sample_data, tmp_path):
        """Create LocomotionData object with sample data."""
        # Save to temporary parquet file
        parquet_path = tmp_path / "test_data.parquet"
        sample_data.to_parquet(parquet_path, index=False)
        
        return LocomotionData(str(parquet_path))
    
    def test_basic_functionality(self, locomotion_data):
        """Test basic functionality of new feature."""
        result = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking')
        
        # Test structure
        assert isinstance(result, dict)
        assert 'metric_name' in result
        assert result['subject'] == 'TEST_SUB'
        assert result['task'] == 'level_walking'
    
    def test_edge_cases(self, locomotion_data):
        """Test edge cases and error handling."""
        # Test with nonexistent subject
        result = locomotion_data.new_analysis_method('NONEXISTENT', 'level_walking')
        assert result == {}
        
        # Test with nonexistent task
        result = locomotion_data.new_analysis_method('TEST_SUB', 'nonexistent_task')
        assert result == {}
    
    def test_parameter_variations(self, locomotion_data):
        """Test different parameter values."""
        # Test default parameter
        result_default = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking')
        
        # Test custom parameter
        result_custom = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking', 
                                                          custom_param=2.0)
        
        # Results should be different
        assert result_default['metric_name'] != result_custom['metric_name']
        assert result_custom['parameters']['custom_param'] == 2.0
    
    def test_data_types(self, locomotion_data):
        """Test return data types."""
        result = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking')
        
        assert isinstance(result['metric_name'], (int, float, np.number))
        assert isinstance(result['parameters'], dict)
    
    @pytest.mark.parametrize("param_value", [0.1, 1.0, 2.0, 10.0])
    def test_parameter_range(self, locomotion_data, param_value):
        """Test method with different parameter values."""
        result = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking', 
                                                    custom_param=param_value)
        
        # Should always return valid result for valid parameters
        assert 'metric_name' in result
        assert np.isfinite(result['metric_name'])

# Integration tests
class TestNewFeatureIntegration:
    """Integration tests for new feature with existing system."""
    
    def test_with_real_data(self):
        """Test with real dataset if available."""
        # Skip if no real data available
        pytest.importorskip("real_dataset", reason="Real dataset not available")
        
        loco = LocomotionData('path/to/real/dataset.parquet')
        
        # Test with multiple subjects and tasks
        for subject in loco.subjects[:3]:  # Test first 3 subjects
            for task in loco.tasks:
                result = loco.new_analysis_method(subject, task)
                
                # Should handle all real data gracefully
                assert isinstance(result, dict)
    
    def test_performance(self, locomotion_data):
        """Test performance of new method."""
        import time
        
        start_time = time.time()
        result = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking')
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 1.0  # Less than 1 second
        assert result is not None

# Visual tests (for demo purposes)
def test_new_feature_visualization(locomotion_data, tmp_path):
    """Generate visualization for manual inspection."""
    import matplotlib.pyplot as plt
    
    result = locomotion_data.new_analysis_method('TEST_SUB', 'level_walking')
    
    # Create simple plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(['Metric'], [result['metric_name']])
    ax.set_title('New Analysis Method Result')
    ax.set_ylabel('Metric Value')
    
    # Save plot
    plot_path = tmp_path / 'new_feature_test.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Verify plot was created
    assert plot_path.exists()
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_new_feature.py

# Run with coverage
pytest --cov=lib tests/

# Run visual tests (demos)
pytest tests/demo_*.py

# Run performance tests
pytest -m performance tests/
```

## Documentation Standards

### Code Documentation

```python
def new_analysis_function(data_3d: np.ndarray, 
                         parameter: float = 1.0,
                         method: str = 'default') -> Dict[str, Any]:
    """
    Perform new analysis on 3D locomotion data.
    
    This function implements [specific algorithm/method] for analyzing
    biomechanical data. It processes gait cycle data to extract [specific metrics].
    
    Parameters
    ----------
    data_3d : np.ndarray
        3D array of shape (n_cycles, 150, n_features) containing phase-normalized
        gait cycle data. Each cycle must have exactly 150 points.
    parameter : float, default=1.0
        Analysis parameter controlling [specific behavior]. Higher values
        increase [effect]. Must be positive.
    method : str, default='default'
        Analysis method to use. Options:
        - 'default': Standard algorithm
        - 'robust': Outlier-resistant variant
        - 'fast': Optimized for speed
        
    Returns
    -------
    dict
        Analysis results containing:
        - 'metric_value': float, computed metric value
        - 'confidence': float, confidence score [0-1]
        - 'method_used': str, actual method applied
        - 'n_cycles_processed': int, number of cycles analyzed
        
    Raises
    ------
    ValueError
        If data_3d is not 3D or has wrong shape
        If parameter is not positive
        If method is not recognized
    RuntimeError
        If analysis fails due to insufficient data
        
    Examples
    --------
    >>> import numpy as np
    >>> data = np.random.randn(5, 150, 6)  # 5 cycles, 6 features
    >>> result = new_analysis_function(data, parameter=1.5)
    >>> print(f"Metric value: {result['metric_value']:.3f}")
    Metric value: 0.237
    
    >>> # Using robust method
    >>> result_robust = new_analysis_function(data, method='robust')
    >>> result_robust['method_used']
    'robust'
    
    See Also
    --------
    LocomotionData.get_cycles : Get 3D cycle data
    validate_cycles : Validate cycle quality before analysis
    
    References
    ----------
    .. [1] Smith, J. et al. "New Analysis Method for Gait Data." 
           Journal of Biomechanics, 2023.
    """
    # Validate inputs
    if data_3d.ndim != 3:
        raise ValueError(f"data_3d must be 3D array, got {data_3d.ndim}D")
    
    if data_3d.shape[1] != 150:
        raise ValueError(f"Expected 150 points per cycle, got {data_3d.shape[1]}")
    
    if parameter <= 0:
        raise ValueError(f"parameter must be positive, got {parameter}")
    
    if method not in ['default', 'robust', 'fast']:
        raise ValueError(f"Unknown method '{method}'. Use 'default', 'robust', or 'fast'")
    
    # Implementation
    n_cycles, n_points, n_features = data_3d.shape
    
    if n_cycles == 0:
        raise RuntimeError("No cycles to analyze")
    
    # Perform analysis based on method
    if method == 'default':
        metric_value = np.mean(data_3d) * parameter
        confidence = 0.95
    elif method == 'robust':
        metric_value = np.median(data_3d) * parameter
        confidence = 0.90
    elif method == 'fast':
        metric_value = np.mean(data_3d[::2]) * parameter  # Skip every other cycle
        confidence = 0.85
    
    return {
        'metric_value': metric_value,
        'confidence': confidence,
        'method_used': method,
        'n_cycles_processed': n_cycles
    }
```

### API Documentation

```markdown
# New Feature API Documentation

## Overview

The new feature provides [functionality description] for locomotion data analysis.

## Quick Start

```python
from lib.core.locomotion_analysis import LocomotionData

# Load data
loco = LocomotionData('dataset_phase.parquet')

# Use new feature
result = loco.new_analysis_method('SUB01', 'level_walking')
print(f"Result: {result['metric_name']}")
```

## Core Functions

### `new_analysis_method(subject, task, **kwargs)`

[Function description and usage examples]

## Integration Examples

### With Existing Analysis Pipeline

```python
# Combine with existing analysis
def comprehensive_analysis(loco, subject, task):
    results = {}
    
    # Standard analysis
    data_3d, features = loco.get_cycles(subject, task)
    results['rom'] = loco.calculate_rom(subject, task)
    
    # New analysis
    results['new_metric'] = loco.new_analysis_method(subject, task)
    
    return results
```

### Performance Considerations

- Memory usage: O(n_cycles * n_features)
- Time complexity: O(n_cycles * n_points)
- Recommended for datasets with < 10,000 cycles

## Validation

The new feature includes built-in validation:

```python
# Check result validity
result = loco.new_analysis_method(subject, task)
if 'error' in result:
    print(f"Analysis failed: {result['error']}")
else:
    print(f"Success: {result['metric_name']}")
```
```

## Code Quality Standards

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.8
        
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
        args: [--profile=black]
```

### Linting Configuration

```ini
# setup.cfg
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    build,
    dist,
    .eggs,
    *.egg-info,
    .venv,
    venv

[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[tool:isort]
profile = black
multi_line_output = 3
include_trailing_comma = True
force_grid_wrap = 0
use_parentheses = True
ensure_newline_before_comments = True
line_length = 88
```

## Release Process

### Version Management

```python
# lib/__init__.py
__version__ = "1.2.3"

# Follow semantic versioning
# MAJOR.MINOR.PATCH
# - MAJOR: Breaking changes
# - MINOR: New features (backward compatible)
# - PATCH: Bug fixes
```

### Release Checklist

1. **Code Quality**
   - [ ] All tests pass
   - [ ] Code coverage > 90%
   - [ ] No linting errors
   - [ ] Type checking passes

2. **Documentation**
   - [ ] API documentation updated
   - [ ] Examples tested
   - [ ] Changelog updated
   - [ ] Version number incremented

3. **Validation**
   - [ ] Integration tests with real data
   - [ ] Performance benchmarks run
   - [ ] Breaking changes documented

4. **Release**
   - [ ] Create release branch
   - [ ] Tag version in git
   - [ ] Update package metadata
   - [ ] Deploy to package repository

## Next Steps

- **[Contributing Guidelines](contributing.md)** - Detailed contribution process
- **[Dataset Converter Guide](dataset-converters.md)** - Adding new data sources
- **[Validation Extension Guide](validation-rules.md)** - Custom validation rules
- **[Architecture Guide](architecture.md)** - Platform architecture details