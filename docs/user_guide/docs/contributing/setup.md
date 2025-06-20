# Development Setup

*Get your development environment ready for extending the platform*

## Quick Setup (5 minutes)

### Prerequisites
- Python 3.8+ or MATLAB R2020b+
- Git for version control
- 4GB RAM minimum (8GB recommended for large datasets)

### Python Development Setup

**1. Clone Repository**
```bash
git clone https://github.com/your-org/locomotion-data-standardization.git
cd locomotion-data-standardization
```

**2. Create Virtual Environment**
```bash
# Using conda (recommended)
conda create -n locomotion-dev python=3.9
conda activate locomotion-dev

# Or using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

**3. Install Development Dependencies**
```bash
# Install package in development mode
pip install -e .

# Install development tools
pip install -r requirements-dev.txt

# Verify installation
python -c "from locomotion_analysis import LocomotionData; print('Setup successful!')"
```

### MATLAB Development Setup

**1. Add to MATLAB Path**
```matlab
% Add core library to path
addpath('source/lib/matlab');

% Add utility functions
addpath('source/lib/matlab/utilities');

% Verify installation
data = LocomotionData('tests/test_data/demo_gtech_2023_phase.parquet');
disp('MATLAB setup successful!');
```

## Development Environment

### Recommended Tools

**Python IDE Setup**
- **VS Code**: With Python, Jupyter, and Git extensions
- **PyCharm**: Professional Python development
- **Jupyter Lab**: Interactive data analysis and visualization

**MATLAB Development**
- **MATLAB Editor**: Built-in development environment
- **VS Code**: With MATLAB extension for syntax highlighting
- **Git Integration**: For version control within MATLAB

### Project Structure
```
locomotion-data-standardization/
├── lib/                    # Core libraries
│   ├── core/              # Main LocomotionData class
│   └── validation/        # Dataset validation tools
├── source/                # Additional source code
│   ├── lib/matlab/       # MATLAB implementations
│   └── visualization/    # Plotting and analysis tools
├── tests/                 # Test suite
├── docs/                 # Documentation
├── contributor_scripts/   # Dataset conversion utilities
└── converted_datasets/   # Standardized data (gitignored)
```

## Core Development Tasks

### 1. Adding New Analysis Functions

**Python Example: Add Average Calculation**
```python
# In lib/core/locomotion_analysis.py
def get_average_trajectory_with_confidence(self, variable_name, confidence_level=0.95):
    """
    Calculate average trajectory with confidence intervals.
    
    Parameters:
    -----------
    variable_name : str
        Name of the variable to analyze
    confidence_level : float
        Confidence level for intervals (default 0.95)
        
    Returns:
    --------
    dict: Contains 'mean', 'lower_ci', 'upper_ci' arrays
    """
    data_3d = self.get_variable_3d(variable_name)
    # Reshape to (all_cycles, phase_points)  
    data_2d = data_3d.reshape(-1, data_3d.shape[-1])
    
    mean_traj = np.mean(data_2d, axis=0)
    std_traj = np.std(data_2d, axis=0)
    n_cycles = data_2d.shape[0]
    
    # Calculate confidence intervals
    from scipy import stats
    t_critical = stats.t.ppf((1 + confidence_level) / 2, n_cycles - 1)
    margin_error = t_critical * (std_traj / np.sqrt(n_cycles))
    
    return {
        'mean': mean_traj,
        'lower_ci': mean_traj - margin_error,
        'upper_ci': mean_traj + margin_error
    }
```

**MATLAB Example: Add Corresponding Function**
```matlab
% In source/lib/matlab/LocomotionData.m
function result = getAverageTrajectoryWithConfidence(obj, variableName, confidenceLevel)
    % Calculate average trajectory with confidence intervals
    
    if nargin < 3
        confidenceLevel = 0.95;
    end
    
    % Get 3D data array
    data3D = obj.getVariable(variableName);
    
    % Reshape to 2D (all_cycles x phase_points)
    [nSubjects, nCycles, nPhases] = size(data3D);
    data2D = reshape(data3D, [], nPhases);
    
    % Calculate statistics
    meanTraj = mean(data2D, 1);
    stdTraj = std(data2D, 0, 1);
    nCycles = size(data2D, 1);
    
    % Calculate confidence intervals
    tCritical = tinv((1 + confidenceLevel) / 2, nCycles - 1);
    marginError = tCritical .* (stdTraj ./ sqrt(nCycles));
    
    result.mean = meanTraj;
    result.lowerCI = meanTraj - marginError;
    result.upperCI = meanTraj + marginError;
end
```

### 2. Adding New Validation Rules

**Create Custom Validation**
```python
# In lib/validation/custom_validators.py
from .dataset_validator_phase import PhaseValidator

class CustomBiomechanicsValidator(PhaseValidator):
    """Custom validation rules for specific research needs"""
    
    def validate_step_width_symmetry(self, data):
        """Validate step width symmetry during walking"""
        walking_data = data.filter_task('level_walking')
        
        # Calculate step width asymmetry index
        left_step_width = walking_data.get_variable_3d('step_width_left')
        right_step_width = walking_data.get_variable_3d('step_width_right')
        
        asymmetry = np.abs(left_step_width - right_step_width) / (
            (left_step_width + right_step_width) / 2
        )
        
        # Check if asymmetry is within acceptable range (< 10%)
        max_asymmetry = np.max(asymmetry)
        if max_asymmetry > 0.10:
            return {
                'passed': False,
                'message': f'Step width asymmetry too high: {max_asymmetry:.2%}',
                'max_asymmetry': max_asymmetry
            }
        
        return {'passed': True, 'max_asymmetry': max_asymmetry}
```

### 3. Adding Dataset Conversion Support

**New Format Converter**
```python
# In contributor_scripts/new_format_converter.py
import pandas as pd
from locomotion_analysis import LocomotionData

class NewFormatConverter:
    """Convert custom lab format to standardized parquet"""
    
    def __init__(self, input_path):
        self.input_path = input_path
        self.raw_data = None
        self.standardized_data = None
    
    def load_raw_data(self):
        """Load data from custom format"""
        # Implement format-specific loading
        pass
    
    def extract_kinematics(self):
        """Extract joint angles and standardize names"""
        # Map custom variable names to standard names
        variable_mapping = {
            'hip_flex': 'hip_flexion_angle_ipsi_rad',
            'knee_flex': 'knee_flexion_angle_ipsi_rad',
            'ankle_flex': 'ankle_flexion_angle_ipsi_rad'
        }
        # Implementation details...
        pass
    
    def phase_index_data(self):
        """Convert to 150-point phase indexing"""
        # Interpolate to exactly 150 points per gait cycle
        pass
    
    def export_parquet(self, output_path):
        """Export to standardized parquet format"""
        self.standardized_data.to_parquet(output_path)
```

## Testing Your Contributions

### Running Tests

**Python Test Suite**
```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_locomotion_data_library.py  # Core functionality
pytest tests/test_validation_parser.py        # Validation system
pytest tests/demo_*.py                        # Visual validation

# Run with coverage
pytest --cov=lib tests/
```

**MATLAB Test Suite**
```matlab
% Run MATLAB tests
runtests tests/test_tutorial_library_matlab.m
runtests tests/test_tutorial_getting_started_matlab.m

% Run specific test function
test_result = test_tutorial_library_matlab();
```

### Adding Tests for New Features

**Python Test Example**
```python
# In tests/test_new_feature.py
import pytest
from locomotion_analysis import LocomotionData

def test_average_with_confidence():
    """Test new confidence interval function"""
    # Load test data
    data = LocomotionData.from_parquet('tests/test_data/demo_gtech_2023_phase.parquet')
    
    # Test function
    result = data.get_average_trajectory_with_confidence('knee_flexion_angle_ipsi_rad')
    
    # Verify output structure
    assert 'mean' in result
    assert 'lower_ci' in result  
    assert 'upper_ci' in result
    
    # Verify dimensions
    assert len(result['mean']) == 150  # Phase-indexed data
    
    # Verify confidence intervals make sense
    assert np.all(result['lower_ci'] <= result['mean'])
    assert np.all(result['upper_ci'] >= result['mean'])
```

**MATLAB Test Example**
```matlab
% In tests/test_new_matlab_feature.m
function test_average_with_confidence()
    % Test new MATLAB confidence interval function
    
    % Load test data
    data = LocomotionData('tests/test_data/demo_gtech_2023_phase.parquet');
    
    % Test function
    result = data.getAverageTrajectoryWithConfidence('knee_flexion_angle_ipsi_rad');
    
    % Verify output structure
    assert(isfield(result, 'mean'));
    assert(isfield(result, 'lowerCI'));
    assert(isfield(result, 'upperCI'));
    
    % Verify dimensions
    assert(length(result.mean) == 150);  % Phase-indexed data
    
    % Verify confidence intervals
    assert(all(result.lowerCI <= result.mean));
    assert(all(result.upperCI >= result.mean));
end
```

## Documentation Standards

### Code Documentation
- **Docstrings**: Complete parameter and return documentation
- **Type Hints**: Python 3.8+ type annotations  
- **Examples**: Working code examples in docstrings
- **MATLAB Comments**: Clear function headers with input/output descriptions

### User Documentation
- **Update Tutorials**: Add examples using new features
- **API Reference**: Auto-generated from docstrings
- **Changelog**: Document all user-facing changes
- **Migration Guides**: For breaking changes

## Contribution Workflow

### 1. Development Process
```bash
# Create feature branch
git checkout -b feature/new-analysis-function

# Make changes and test
# ... develop and test your feature ...

# Commit with clear messages
git add .
git commit -m "Add confidence interval calculation for trajectory analysis"

# Push and create pull request
git push origin feature/new-analysis-function
```

### 2. Code Review Process
- Automated tests must pass
- Code review by core maintainers
- Documentation updates included
- Performance impact assessed

### 3. Release Integration
- Features merged to main branch
- Version bumping follows semantic versioning
- Release notes generated automatically
- PyPI and MATLAB File Exchange updates

## Need Help?

### Development Support
- **[GitHub Issues](https://github.com/your-org/locomotion-data-standardization/issues)** - Bug reports and feature requests
- **[Development Forum](mailto:dev@locomotion-data-standardization.org)** - Technical discussions
- **[Code Review Guidelines](../contributor_guide/best_practices/)** - Best practices for contributions

### Community Resources
- **Weekly Developer Calls**: Join our virtual development meetings
- **Slack Workspace**: Real-time chat with other contributors
- **Documentation Sprints**: Contribute to documentation improvements

---

*Ready to extend the platform? Start with our [contributor guide](../contributor_guide/overview/) for detailed workflow information.*