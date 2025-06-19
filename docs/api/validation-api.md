# Validation API Reference

Comprehensive API documentation for dataset validation, quality assessment, and compliance checking.

## Overview

The validation API provides tools for:
- Dataset quality assessment against biomechanical expectations
- Variable naming convention validation
- Phase-indexed data structure verification  
- Automated validation report generation with visualizations

## Core Validation Classes

### DatasetValidator

Main class for validating phase-indexed locomotion datasets.

```python
from lib.validation.dataset_validator_phase import DatasetValidator

# Initialize validator
validator = DatasetValidator('dataset_phase.parquet')
```

#### Constructor

```python
DatasetValidator(dataset_path, output_dir=None, generate_plots=True)
```

**Parameters:**
- `dataset_path` (str): Path to phase-based dataset parquet file (must be *_phase.parquet)
- `output_dir` (str, optional): Directory to save validation reports
- `generate_plots` (bool): Whether to generate validation plots (default: True)

#### Core Methods

##### `run_validation() -> str`

Run complete dataset validation pipeline.

**Returns:**
- `str`: Path to generated validation report

**Example:**
```python
validator = DatasetValidator('gait_data_phase.parquet')
report_path = validator.run_validation()
print(f"Validation complete: {report_path}")
```

##### `load_dataset() -> LocomotionData`

Load and validate dataset structure using LocomotionData library.

**Returns:**
- `LocomotionData`: Loaded dataset object

**Raises:**
- `ValueError`: If dataset format is invalid or required columns missing

##### `validate_dataset(locomotion_data) -> Dict`

Validate entire dataset against kinematic and kinetic expectations.

**Parameters:**
- `locomotion_data` (LocomotionData): Loaded dataset object

**Returns:**
- `dict`: Validation results with structure:
  ```python
  {
      'total_steps': int,
      'valid_steps': int, 
      'failed_steps': int,
      'kinematic_failures': List[Dict],
      'kinetic_failures': List[Dict],
      'tasks_validated': List[str],
      'task_step_counts': Dict[str, Dict]
  }
  ```

**Example:**
```python
# Detailed validation workflow
validator = DatasetValidator('dataset_phase.parquet')
locomotion_data = validator.load_dataset()
results = validator.validate_dataset(locomotion_data)

print(f"Total steps: {results['total_steps']}")
print(f"Success rate: {results['valid_steps']/results['total_steps']:.1%}")
print(f"Kinematic failures: {len(results['kinematic_failures'])}")
print(f"Kinetic failures: {len(results['kinetic_failures'])}")
```

### StepClassifier

Low-level validation engine for individual step validation.

```python
from lib.validation.step_classifier import StepClassifier

classifier = StepClassifier()
```

#### Key Methods

##### `validate_data_against_specs(data_array, task, step_task_mapping, validation_type)`

Validate step data against specification ranges.

**Parameters:**
- `data_array` (np.ndarray): 3D array of shape (n_steps, 150, n_features)
- `task` (str): Task name for validation
- `step_task_mapping` (Dict): Mapping from step index to task name
- `validation_type` (str): 'kinematic' or 'kinetic'

**Returns:**
- `List[Dict]`: List of validation failure dictionaries

**Example:**
```python
classifier = StepClassifier()

# Validate kinematic data
failures = classifier.validate_data_against_specs(
    data_array=kinematic_data_3d,
    task='level_walking',
    step_task_mapping={0: 'level_walking', 1: 'level_walking'},
    validation_type='kinematic'
)

for failure in failures:
    print(f"Step {failure['step']}: {failure['variable']} at phase {failure['phase']}%")
    print(f"  Value: {failure['value']:.3f}, Expected: {failure['expected_min']:.3f}-{failure['expected_max']:.3f}")
```

##### `load_validation_ranges_from_specs(validation_type)`

Load validation ranges from specification files.

**Parameters:**
- `validation_type` (str): 'kinematic' or 'kinetic'

**Returns:**
- `Dict`: Validation ranges organized by task and variable

## Validation Utilities

### ValidationExpectationsParser

Parse validation ranges from markdown specification files.

```python
from lib.validation.validation_expectations_parser import ValidationExpectationsParser

parser = ValidationExpectationsParser()
```

##### `parse_validation_file(file_path) -> Dict`

Parse validation expectations from markdown file.

**Parameters:**
- `file_path` (str): Path to validation specification markdown file

**Returns:**
- `Dict`: Parsed validation ranges

**Example:**
```python
parser = ValidationExpectationsParser()
kinematic_ranges = parser.parse_validation_file(
    'docs/standard_spec/validation_expectations_kinematic.md'
)

# Access specific task and variable ranges
walking_ranges = kinematic_ranges['level_walking']
knee_range = walking_ranges['knee_flexion_angle_contra_rad']
print(f"Knee flexion range at phase 0: {knee_range['phase_0']}")
```

### AutomatedFineTuning

Automatically optimize validation ranges based on dataset statistics.

```python
from lib.validation.automated_fine_tuning import AutomatedFineTuning

tuner = AutomatedFineTuning()
```

##### `tune_validation_ranges(dataset_path, validation_type, percentile_range)`

Generate optimized validation ranges from dataset.

**Parameters:**
- `dataset_path` (str): Path to reference dataset
- `validation_type` (str): 'kinematic' or 'kinetic'  
- `percentile_range` (Tuple[float, float]): Percentile range for bounds (e.g., (5, 95))

**Returns:**
- `Dict`: Optimized validation ranges

**Example:**
```python
tuner = AutomatedFineTuning()

# Generate ranges from high-quality reference dataset
optimized_ranges = tuner.tune_validation_ranges(
    dataset_path='reference_dataset_phase.parquet',
    validation_type='kinematic',
    percentile_range=(2.5, 97.5)  # Conservative bounds
)

# Apply to existing specifications
tuner.apply_tuned_ranges(optimized_ranges, 'kinematic')
```

## Advanced Validation Patterns

### Custom Validation Pipeline

```python
def custom_validation_pipeline(dataset_path: str) -> Dict:
    """Custom validation with specific requirements."""
    
    # Initialize components
    validator = DatasetValidator(dataset_path, generate_plots=False)
    classifier = StepClassifier()
    
    # Load dataset
    locomotion_data = validator.load_dataset()
    
    # Custom validation logic
    results = {
        'dataset_info': {
            'subjects': len(locomotion_data.subjects),
            'tasks': len(locomotion_data.tasks),
            'features': len(locomotion_data.features)
        },
        'naming_compliance': locomotion_data.get_validation_report(),
        'quality_by_task': {}
    }
    
    # Task-specific validation
    for task in locomotion_data.tasks:
        task_results = {'subjects': {}}
        
        for subject in locomotion_data.subjects:
            # Get kinematic data
            data_3d, features = locomotion_data.get_cycles(subject, task, 
                                                         locomotion_data.ANGLE_FEATURES)
            if data_3d is None:
                continue
                
            # Validate each step
            step_failures = []
            for step_idx in range(data_3d.shape[0]):
                step_data = data_3d[step_idx:step_idx+1, :, :]  # Keep 3D shape
                failures = classifier.validate_data_against_specs(
                    step_data, task, {0: task}, 'kinematic'
                )
                step_failures.extend(failures)
            
            task_results['subjects'][subject] = {
                'total_steps': data_3d.shape[0],
                'failed_steps': len(step_failures),
                'quality_score': 1.0 - len(step_failures) / data_3d.shape[0]
            }
        
        results['quality_by_task'][task] = task_results
    
    return results

# Run custom validation
results = custom_validation_pipeline('my_dataset_phase.parquet')
```

### Batch Dataset Validation

```python
def validate_multiple_datasets(dataset_directory: str) -> Dict:
    """Validate all datasets in a directory."""
    
    dataset_paths = list(Path(dataset_directory).glob('*_phase.parquet'))
    validation_results = {}
    
    for dataset_path in dataset_paths:
        dataset_name = dataset_path.stem
        print(f"Validating {dataset_name}...")
        
        try:
            validator = DatasetValidator(str(dataset_path), generate_plots=False)
            locomotion_data = validator.load_dataset()
            results = validator.validate_dataset(locomotion_data)
            
            # Calculate overall quality metrics
            quality_score = results['valid_steps'] / results['total_steps'] if results['total_steps'] > 0 else 0
            
            validation_results[dataset_name] = {
                'status': 'SUCCESS',
                'quality_score': quality_score,
                'total_steps': results['total_steps'],
                'failure_count': len(results['kinematic_failures']) + len(results['kinetic_failures']),
                'tasks': results['tasks_validated']
            }
            
        except Exception as e:
            validation_results[dataset_name] = {
                'status': 'ERROR',
                'error': str(e),
                'quality_score': 0.0
            }
    
    return validation_results

# Validate all datasets
results = validate_multiple_datasets('./converted_datasets/')

# Generate summary
for dataset, result in results.items():
    status = result['status']
    quality = result.get('quality_score', 0)
    print(f"{dataset}: {status} (Quality: {quality:.1%})")
```

### Real-time Validation Monitoring

```python
class ValidationMonitor:
    """Real-time validation monitoring for data streams."""
    
    def __init__(self):
        self.classifier = StepClassifier()
        self.validation_history = []
        self.alert_threshold = 0.8  # Alert if quality drops below 80%
    
    def validate_incoming_step(self, step_data: np.ndarray, task: str) -> Dict:
        """Validate a single incoming step."""
        
        # Ensure step_data is 3D: (1, 150, n_features)
        if step_data.ndim == 2:
            step_data = step_data.reshape(1, 150, -1)
        
        # Validate step
        failures = self.classifier.validate_data_against_specs(
            step_data, task, {0: task}, 'kinematic'
        )
        
        quality_score = 1.0 - len(failures) / step_data.shape[2]  # Failures per feature
        
        result = {
            'timestamp': datetime.now(),
            'task': task,
            'quality_score': quality_score,
            'failure_count': len(failures),
            'failures': failures,
            'alert': quality_score < self.alert_threshold
        }
        
        self.validation_history.append(result)
        
        # Trigger alert if needed
        if result['alert']:
            self._trigger_quality_alert(result)
        
        return result
    
    def _trigger_quality_alert(self, result: Dict):
        """Handle quality alerts."""
        print(f"🚨 QUALITY ALERT: {result['task']} quality at {result['quality_score']:.1%}")
        print(f"   Failures: {result['failure_count']}")
    
    def get_quality_trends(self, window_size: int = 10) -> Dict:
        """Get recent quality trends."""
        if len(self.validation_history) < window_size:
            return {'insufficient_data': True}
        
        recent_results = self.validation_history[-window_size:]
        qualities = [r['quality_score'] for r in recent_results]
        
        return {
            'current_quality': qualities[-1],
            'mean_quality': np.mean(qualities),
            'quality_trend': 'improving' if qualities[-1] > qualities[0] else 'declining',
            'alert_rate': sum(1 for r in recent_results if r['alert']) / len(recent_results)
        }

# Usage
monitor = ValidationMonitor()

# Simulate incoming data stream
for i in range(20):
    # Generate sample step data (150 points, 6 features)
    step_data = np.random.randn(150, 6) * 0.1  # Small random values
    
    result = monitor.validate_incoming_step(step_data, 'level_walking')
    
    if i % 5 == 0:  # Check trends every 5 steps
        trends = monitor.get_quality_trends()
        if not trends.get('insufficient_data'):
            print(f"Quality trend: {trends['quality_trend']} (current: {trends['current_quality']:.1%})")
```

## Validation Configuration

### Custom Validation Ranges

```python
# Define custom validation ranges
custom_ranges = {
    'level_walking': {
        'knee_flexion_angle_contra_rad': {
            'phase_0': {'min': -0.1, 'max': 0.3},    # Heel strike
            'phase_25': {'min': 0.0, 'max': 0.8},    # Loading response  
            'phase_50': {'min': 0.5, 'max': 1.2},    # Mid-swing
            'phase_75': {'min': 0.2, 'max': 0.9}     # Terminal swing
        }
    }
}

# Apply custom ranges
classifier = StepClassifier()
classifier.kinematic_expectations = custom_ranges

# Use in validation
failures = classifier.validate_data_against_specs(
    data_array, 'level_walking', step_mapping, 'kinematic'
)
```

### Validation Report Customization

```python
def generate_custom_report(validation_results: Dict, output_path: str):
    """Generate custom validation report."""
    
    with open(output_path, 'w') as f:
        f.write("# Custom Validation Report\n\n")
        
        # Executive summary
        total_steps = validation_results['total_steps']
        valid_steps = validation_results['valid_steps']
        success_rate = valid_steps / total_steps if total_steps > 0 else 0
        
        f.write(f"**Dataset Quality**: {success_rate:.1%}\n")
        f.write(f"**Total Steps**: {total_steps}\n")
        f.write(f"**Valid Steps**: {valid_steps}\n\n")
        
        # Task breakdown
        f.write("## Task Analysis\n\n")
        for task in validation_results['tasks_validated']:
            task_counts = validation_results['task_step_counts'].get(task, {})
            task_total = task_counts.get('total', 0)
            task_valid = task_counts.get('valid', 0)
            task_rate = task_valid / task_total if task_total > 0 else 0
            
            f.write(f"### {task.replace('_', ' ').title()}\n")
            f.write(f"- Success Rate: {task_rate:.1%}\n")
            f.write(f"- Total Steps: {task_total}\n")
            f.write(f"- Valid Steps: {task_valid}\n\n")
        
        # Failure analysis
        kinematic_failures = validation_results.get('kinematic_failures', [])
        kinetic_failures = validation_results.get('kinetic_failures', [])
        
        if kinematic_failures or kinetic_failures:
            f.write("## Failure Summary\n\n")
            
            # Group failures by variable
            failure_counts = {}
            for failure in kinematic_failures + kinetic_failures:
                var = failure['variable']
                failure_counts[var] = failure_counts.get(var, 0) + 1
            
            f.write("| Variable | Failure Count |\n")
            f.write("|----------|---------------|\n")
            for var, count in sorted(failure_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {var} | {count} |\n")

# Usage
validator = DatasetValidator('dataset_phase.parquet')
locomotion_data = validator.load_dataset()
results = validator.validate_dataset(locomotion_data)

generate_custom_report(results, 'custom_validation_report.md')
```

## Error Handling and Debugging

```python
import logging

# Configure validation logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('validation')

def robust_validation(dataset_path: str) -> Dict:
    """Validation with comprehensive error handling."""
    
    try:
        validator = DatasetValidator(dataset_path)
        
        # Load with error handling
        try:
            locomotion_data = validator.load_dataset()
            logger.info(f"Successfully loaded dataset: {dataset_path}")
        except ValueError as e:
            logger.error(f"Dataset loading failed: {e}")
            return {'status': 'LOAD_ERROR', 'error': str(e)}
        
        # Validate with error handling  
        try:
            results = validator.validate_dataset(locomotion_data)
            logger.info(f"Validation completed: {results['valid_steps']}/{results['total_steps']} steps valid")
            return {'status': 'SUCCESS', 'results': results}
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {'status': 'VALIDATION_ERROR', 'error': str(e)}
            
    except Exception as e:
        logger.critical(f"Unexpected error: {e}")
        return {'status': 'CRITICAL_ERROR', 'error': str(e)}

# Usage with error handling
result = robust_validation('problematic_dataset.parquet')

if result['status'] == 'SUCCESS':
    validation_results = result['results']
    # Process successful validation
elif result['status'] == 'LOAD_ERROR':
    print(f"Cannot load dataset: {result['error']}")
elif result['status'] == 'VALIDATION_ERROR':
    print(f"Validation failed: {result['error']}")
else:
    print(f"Critical error: {result['error']}")
```

## Performance Optimization

```python
# Efficient validation for large datasets
def optimized_large_dataset_validation(dataset_path: str, sample_rate: float = 0.1):
    """Validate large datasets efficiently using sampling."""
    
    validator = DatasetValidator(dataset_path, generate_plots=False)
    locomotion_data = validator.load_dataset()
    
    # Sample subjects for faster validation
    total_subjects = len(locomotion_data.subjects)
    sample_size = max(1, int(total_subjects * sample_rate))
    sampled_subjects = np.random.choice(locomotion_data.subjects, sample_size, replace=False)
    
    print(f"Validating {sample_size}/{total_subjects} subjects ({sample_rate:.1%} sample)")
    
    # Create temporary dataset with sampled subjects
    df_sample = locomotion_data.df[locomotion_data.df['subject'].isin(sampled_subjects)]
    
    # Use efficient validation on sample
    sample_validation_results = {}
    for subject in sampled_subjects:
        for task in locomotion_data.tasks:
            data_3d, features = locomotion_data.get_cycles(subject, task)
            if data_3d is not None:
                valid_mask = locomotion_data.validate_cycles(subject, task)
                sample_validation_results[(subject, task)] = {
                    'quality_score': np.sum(valid_mask) / len(valid_mask)
                }
    
    # Estimate full dataset quality
    quality_scores = [r['quality_score'] for r in sample_validation_results.values()]
    estimated_quality = np.mean(quality_scores) if quality_scores else 0.0
    
    return {
        'estimated_quality': estimated_quality,
        'sample_size': sample_size,
        'total_subjects': total_subjects,
        'sample_results': sample_validation_results
    }

# Usage for large datasets
result = optimized_large_dataset_validation('large_dataset_phase.parquet', sample_rate=0.2)
print(f"Estimated dataset quality: {result['estimated_quality']:.1%}")
```

## Next Steps

- **Integration Examples**: See [Integration Guides](../integration/README.md)
- **LocomotionData API**: Check [LocomotionData API](locomotion-data-api.md)
- **Developer Tools**: Review [Developer Workflows](../developer/README.md)