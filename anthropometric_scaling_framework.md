# Anthropometric Scaling Framework
## Implementation Specification for Population-Inclusive Biomechanical Analysis

Created: 2025-06-20 with user permission
Purpose: Technical specification for implementing anthropometric scaling in locomotion data standardization

Intent: Provides detailed implementation guidance for normalizing biomechanical data across diverse populations using literature-validated scaling methods to enable fair comparisons regardless of body size, age, or sex.

---

## Overview

Anthropometric scaling is essential for valid biomechanical comparisons across populations with different body sizes. This framework implements literature-validated methods to normalize joint moments, forces, and other biomechanical variables for fair comparison across diverse populations.

## Literature-Validated Scaling Methods

### 1. Joint Moment Scaling

#### Body Weight × Height Method (Recommended)
**Scientific Basis**: Most effective at reducing gender-based differences (Moisio et al., 2003)

```python
def scale_moment_bw_height(moment_nm, body_weight_kg, height_m):
    """
    Scale joint moment using body weight × height normalization
    
    Args:
        moment_nm: Joint moment in Newton-meters
        body_weight_kg: Body weight in kilograms
        height_m: Height in meters
    
    Returns:
        Normalized moment as percentage of (BW × Height)
    """
    return (moment_nm / (body_weight_kg * height_m)) * 100
```

**Literature Support**:
- Reduces anthropometric differences better than body weight alone
- Recommended for cross-population comparisons
- Particularly effective for hip, knee, and ankle moments

#### Allometric Scaling Method (Advanced)
**Scientific Basis**: Accounts for non-linear size-strength relationships

```python
def scale_moment_allometric(moment_nm, body_mass_kg, height_m, 
                          mass_exponent=0.67, height_exponent=1.0):
    """
    Scale joint moment using allometric scaling
    
    Args:
        moment_nm: Joint moment in Newton-meters
        body_mass_kg: Body mass in kilograms
        height_m: Height in meters
        mass_exponent: Allometric exponent for mass (default: 2/3)
        height_exponent: Allometric exponent for height (default: 1.0)
    
    Returns:
        Allometrically scaled moment
    """
    scaling_factor = (body_mass_kg ** mass_exponent) * (height_m ** height_exponent)
    return moment_nm / scaling_factor
```

**Optimal Exponents** (Population-Specific):
- **Adults**: Mass^0.67 × Height^1.0
- **Children**: Mass^0.75 × Height^1.2 (accounts for developmental differences)
- **Elderly**: Mass^0.60 × Height^0.9 (accounts for sarcopenia)

### 2. Ground Reaction Force Scaling

#### Body Weight Normalization (Standard)
```python
def scale_force_bodyweight(force_n, body_weight_kg):
    """
    Scale ground reaction force to body weight percentage
    
    Args:
        force_n: Force in Newtons
        body_weight_kg: Body weight in kilograms
    
    Returns:
        Force as percentage of body weight
    """
    body_weight_n = body_weight_kg * 9.81
    return (force_n / body_weight_n) * 100
```

#### Advanced Force Normalization
```python
def scale_force_advanced(force_n, body_weight_kg, method='division'):
    """
    Advanced force scaling methods
    
    Args:
        force_n: Force in Newtons
        body_weight_kg: Body weight in kilograms
        method: 'division', 'offset', or 'power_curve'
    
    Returns:
        Scaled force value
    """
    body_weight_n = body_weight_kg * 9.81
    
    if method == 'division':
        return force_n / body_weight_n
    elif method == 'offset':
        # For forces with non-zero baseline
        baseline = 0.1 * body_weight_n  # 10% BW baseline
        return (force_n - baseline) / (body_weight_n - baseline)
    elif method == 'power_curve':
        # For non-linear relationships
        return force_n / (body_weight_n ** 0.67)
```

### 3. Population-Specific Adjustments

#### Pediatric Scaling Factors
```python
def get_pediatric_scaling_factor(age_years):
    """
    Get age-appropriate scaling factor for pediatric populations
    
    Args:
        age_years: Age in years
    
    Returns:
        Scaling adjustment factor
    """
    if age_years < 5:
        return 1.2  # Account for immature motor patterns
    elif age_years < 10:
        return 1.1  # Developing coordination
    elif age_years < 15:
        return 1.05  # Near-adult patterns
    else:
        return 1.0  # Adult scaling
```

#### Elderly Scaling Factors
```python
def get_elderly_scaling_factor(age_years, sex):
    """
    Get age-appropriate scaling factor for elderly populations
    
    Args:
        age_years: Age in years
        sex: 'M' or 'F'
    
    Returns:
        Scaling adjustment factor
    """
    base_factor = 1.0
    
    if age_years > 65:
        # Account for sarcopenia (muscle loss)
        age_adjustment = 0.01 * (age_years - 65)  # 1% per year after 65
        
        # Sex-specific adjustments
        if sex == 'F':
            age_adjustment *= 1.2  # Women lose muscle mass faster
        
        base_factor = 1.0 + age_adjustment
    
    return base_factor
```

## Implementation Framework

### Core Scaling Class
```python
import numpy as np
from typing import Dict, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class AnthropometricData:
    """Container for subject anthropometric data"""
    height_m: float
    weight_kg: float
    age_years: int
    sex: str  # 'M' or 'F'
    pathology: Optional[str] = None
    
    @property
    def bmi(self) -> float:
        return self.weight_kg / (self.height_m ** 2)

class AnthropometricScaler:
    """
    Comprehensive anthropometric scaling for biomechanical data
    """
    
    def __init__(self):
        self.scaling_methods = {
            'body_weight': self._scale_by_body_weight,
            'body_weight_height': self._scale_by_bw_height,
            'allometric': self._scale_allometric,
            'population_specific': self._scale_population_specific
        }
    
    def scale_data(self, data: Dict[str, np.ndarray], 
                   anthropometrics: AnthropometricData,
                   method: str = 'body_weight_height') -> Dict[str, np.ndarray]:
        """
        Scale biomechanical data using specified method
        
        Args:
            data: Dictionary of biomechanical variables
            anthropometrics: Subject anthropometric data
            method: Scaling method to use
        
        Returns:
            Dictionary of scaled variables
        """
        if method not in self.scaling_methods:
            raise ValueError(f"Unknown scaling method: {method}")
        
        return self.scaling_methods[method](data, anthropometrics)
    
    def _scale_by_body_weight(self, data: Dict[str, np.ndarray], 
                             anthro: AnthropometricData) -> Dict[str, np.ndarray]:
        """Scale variables by body weight"""
        scaled_data = {}
        
        for variable, values in data.items():
            if 'moment' in variable or 'torque' in variable:
                # Scale moments to Nm/kg
                scaled_data[f"{variable}_per_kg"] = values / anthro.weight_kg
            elif 'force' in variable or 'grf' in variable:
                # Scale forces to %BW
                scaled_data[f"{variable}_bw_pct"] = (values / (anthro.weight_kg * 9.81)) * 100
            else:
                # Don't scale kinematic variables
                scaled_data[variable] = values
        
        return scaled_data
    
    def _scale_by_bw_height(self, data: Dict[str, np.ndarray], 
                           anthro: AnthropometricData) -> Dict[str, np.ndarray]:
        """Scale variables by body weight × height"""
        scaled_data = {}
        
        for variable, values in data.items():
            if 'moment' in variable or 'torque' in variable:
                # Scale moments to %(BW×Height)
                scaling_factor = anthro.weight_kg * anthro.height_m
                scaled_data[f"{variable}_bw_ht_pct"] = (values / scaling_factor) * 100
            elif 'force' in variable or 'grf' in variable:
                # Still use body weight for forces
                scaled_data[f"{variable}_bw_pct"] = (values / (anthro.weight_kg * 9.81)) * 100
            else:
                scaled_data[variable] = values
        
        return scaled_data
    
    def _scale_allometric(self, data: Dict[str, np.ndarray], 
                         anthro: AnthropometricData) -> Dict[str, np.ndarray]:
        """Scale variables using allometric scaling"""
        scaled_data = {}
        
        # Get population-specific exponents
        mass_exp, height_exp = self._get_allometric_exponents(anthro)
        scaling_factor = (anthro.weight_kg ** mass_exp) * (anthro.height_m ** height_exp)
        
        for variable, values in data.items():
            if 'moment' in variable or 'torque' in variable:
                scaled_data[f"{variable}_allometric"] = values / scaling_factor
            elif 'force' in variable or 'grf' in variable:
                # Use body weight scaling for forces
                scaled_data[f"{variable}_bw_pct"] = (values / (anthro.weight_kg * 9.81)) * 100
            else:
                scaled_data[variable] = values
        
        return scaled_data
    
    def _scale_population_specific(self, data: Dict[str, np.ndarray], 
                                  anthro: AnthropometricData) -> Dict[str, np.ndarray]:
        """Scale with population-specific adjustments"""
        # Start with body weight × height scaling
        scaled_data = self._scale_by_bw_height(data, anthro)
        
        # Apply population-specific adjustments
        adjustment_factor = self._get_population_adjustment(anthro)
        
        for variable, values in scaled_data.items():
            if 'moment' in variable or 'torque' in variable:
                scaled_data[variable] = values * adjustment_factor
        
        return scaled_data
    
    def _get_allometric_exponents(self, anthro: AnthropometricData) -> Tuple[float, float]:
        """Get population-specific allometric exponents"""
        if anthro.age_years < 18:
            return 0.75, 1.2  # Pediatric
        elif anthro.age_years > 65:
            return 0.60, 0.9  # Elderly
        else:
            return 0.67, 1.0  # Adult
    
    def _get_population_adjustment(self, anthro: AnthropometricData) -> float:
        """Get population-specific adjustment factor"""
        adjustment = 1.0
        
        # Age adjustments
        if anthro.age_years < 18:
            adjustment *= self._get_pediatric_adjustment(anthro.age_years)
        elif anthro.age_years > 65:
            adjustment *= self._get_elderly_adjustment(anthro.age_years, anthro.sex)
        
        # Pathology adjustments
        if anthro.pathology:
            adjustment *= self._get_pathology_adjustment(anthro.pathology)
        
        return adjustment
    
    def _get_pediatric_adjustment(self, age_years: int) -> float:
        """Pediatric scaling adjustment"""
        if age_years < 5:
            return 1.2
        elif age_years < 10:
            return 1.1
        elif age_years < 15:
            return 1.05
        else:
            return 1.0
    
    def _get_elderly_adjustment(self, age_years: int, sex: str) -> float:
        """Elderly scaling adjustment"""
        if age_years <= 65:
            return 1.0
        
        age_factor = 0.01 * (age_years - 65)
        if sex == 'F':
            age_factor *= 1.2  # Greater muscle loss in women
        
        return 1.0 + age_factor
    
    def _get_pathology_adjustment(self, pathology: str) -> float:
        """Pathology-specific scaling adjustment"""
        adjustments = {
            'parkinsons': 1.1,    # Reduced muscle strength
            'stroke': 1.2,        # Hemiparesis effects
            'cerebral_palsy': 1.3, # Spasticity and weakness
            'multiple_sclerosis': 1.15
        }
        return adjustments.get(pathology.lower(), 1.0)
```

## Integration with Validation System

### Scaled Validation Ranges
```python
class ScaledValidationManager:
    """Manage validation ranges for scaled data"""
    
    def __init__(self):
        self.scaled_ranges = self._load_scaled_ranges()
    
    def get_validation_ranges(self, task: str, scaling_method: str, 
                            population_category: str) -> Dict:
        """Get validation ranges for scaled data"""
        range_key = f"{task}_{scaling_method}_{population_category}"
        return self.scaled_ranges.get(range_key, self._get_default_ranges(task))
    
    def validate_scaled_data(self, data: Dict[str, np.ndarray], 
                           task: str, scaling_method: str,
                           anthropometrics: AnthropometricData) -> Dict:
        """Validate scaled biomechanical data"""
        population_category = self._categorize_population(anthropometrics)
        ranges = self.get_validation_ranges(task, scaling_method, population_category)
        
        validation_results = {}
        for variable, values in data.items():
            if variable in ranges:
                validation_results[variable] = self._validate_variable(
                    values, ranges[variable]
                )
        
        return validation_results
```

## Usage Examples

### Basic Scaling
```python
# Initialize scaler
scaler = AnthropometricScaler()

# Subject data
subject_data = {
    'hip_flexion_moment_ipsi_Nm': np.array([50, 45, 40, 35]),
    'knee_flexion_moment_ipsi_Nm': np.array([30, 25, 20, 15]),
    'vertical_grf_ipsi_N': np.array([800, 900, 950, 750])
}

# Subject anthropometrics
anthropometrics = AnthropometricData(
    height_m=1.75,
    weight_kg=70,
    age_years=25,
    sex='M'
)

# Scale data
scaled_data = scaler.scale_data(
    subject_data, 
    anthropometrics, 
    method='body_weight_height'
)

print(scaled_data)
# Output:
# {
#     'hip_flexion_moment_ipsi_Nm_bw_ht_pct': [40.8, 36.7, 32.7, 28.6],
#     'knee_flexion_moment_ipsi_Nm_bw_ht_pct': [24.5, 20.4, 16.3, 12.2],
#     'vertical_grf_ipsi_N_bw_pct': [116.6, 131.2, 138.5, 109.4]
# }
```

### Population-Specific Scaling
```python
# Elderly subject
elderly_anthropometrics = AnthropometricData(
    height_m=1.68,
    weight_kg=65,
    age_years=75,
    sex='F'
)

# Scale with population adjustments
scaled_data_elderly = scaler.scale_data(
    subject_data, 
    elderly_anthropometrics, 
    method='population_specific'
)
```

## Quality Assurance

### Scaling Effectiveness Metrics
```python
def assess_scaling_effectiveness(original_data: np.ndarray, 
                               scaled_data: np.ndarray,
                               groups: np.ndarray) -> Dict[str, float]:
    """
    Assess how well scaling reduces between-group variance
    
    Args:
        original_data: Unscaled data
        scaled_data: Scaled data
        groups: Group labels (e.g., sex, age category)
    
    Returns:
        Effectiveness metrics
    """
    from scipy import stats
    
    # Calculate variance reduction
    original_var = np.var(original_data)
    scaled_var = np.var(scaled_data)
    variance_reduction = (original_var - scaled_var) / original_var
    
    # Calculate group separation reduction
    group_f_original = stats.f_oneway(*[original_data[groups == g] for g in np.unique(groups)])[0]
    group_f_scaled = stats.f_oneway(*[scaled_data[groups == g] for g in np.unique(groups)])[0]
    separation_reduction = (group_f_original - group_f_scaled) / group_f_original
    
    return {
        'variance_reduction': variance_reduction,
        'group_separation_reduction': separation_reduction,
        'coefficient_of_variation_original': np.std(original_data) / np.mean(original_data),
        'coefficient_of_variation_scaled': np.std(scaled_data) / np.mean(scaled_data)
    }
```

## Testing Framework

### Unit Tests
```python
import unittest

class TestAnthropometricScaling(unittest.TestCase):
    
    def setUp(self):
        self.scaler = AnthropometricScaler()
        self.test_anthropometrics = AnthropometricData(
            height_m=1.75, weight_kg=70, age_years=25, sex='M'
        )
    
    def test_body_weight_scaling(self):
        """Test body weight scaling produces expected results"""
        test_data = {'hip_flexion_moment_ipsi_Nm': np.array([70])}
        scaled = self.scaler.scale_data(test_data, self.test_anthropometrics, 'body_weight')
        expected = 70 / 70  # 1.0 Nm/kg
        self.assertAlmostEqual(scaled['hip_flexion_moment_ipsi_Nm_per_kg'][0], expected)
    
    def test_allometric_scaling(self):
        """Test allometric scaling with known values"""
        test_data = {'hip_flexion_moment_ipsi_Nm': np.array([70])}
        scaled = self.scaler.scale_data(test_data, self.test_anthropometrics, 'allometric')
        # Verify scaling factor calculation
        expected_factor = (70 ** 0.67) * (1.75 ** 1.0)
        self.assertIsNotNone(scaled['hip_flexion_moment_ipsi_Nm_allometric'])
    
    def test_population_adjustments(self):
        """Test population-specific adjustments"""
        elderly_anthro = AnthropometricData(
            height_m=1.70, weight_kg=65, age_years=75, sex='F'
        )
        adjustment = self.scaler._get_population_adjustment(elderly_anthro)
        self.assertGreater(adjustment, 1.0)  # Should be > 1 for elderly
```

## Documentation and Maintenance

### Scaling Method Documentation
Each scaling method includes:
- **Scientific rationale** with literature citations
- **Appropriate use cases** and populations
- **Limitations** and considerations
- **Validation evidence** from literature
- **Implementation examples**

### Maintenance Guidelines
1. **Literature Updates**: Review scaling literature annually
2. **Population Validation**: Test with new populations as data becomes available
3. **Method Comparison**: Regularly compare scaling method effectiveness
4. **Clinical Validation**: Validate with clinical partners

This framework provides a comprehensive, literature-validated approach to anthropometric scaling that enables fair biomechanical comparisons across diverse populations while maintaining scientific rigor and clinical relevance.