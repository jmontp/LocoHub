# Demographic Stratification System
## Age/Sex/Population-Specific Validation Framework

Created: 2025-06-20 with user permission
Purpose: Implementation specification for demographic stratification in locomotion data validation

Intent: Provides a comprehensive framework for creating age, sex, and population-specific validation ranges to enable accurate biomechanical assessment across diverse demographics, replacing one-size-fits-all validation with personalized, literature-based normative ranges.

---

## Overview

Current validation ranges are based solely on healthy young adults (18-60 years). This system enables demographic-specific validation by stratifying populations based on age, sex, and pathological conditions, providing appropriate normative ranges for each group.

## Literature-Based Demographic Categories

### Age Stratification

#### Pediatric Categories
```python
PEDIATRIC_CATEGORIES = {
    'early_childhood': {'age_range': (2, 5), 'characteristics': [
        'Developing basic motor patterns',
        'High step width relative to height',
        'Variable cadence',
        'Immature balance control'
    ]},
    'middle_childhood': {'age_range': (6, 9), 'characteristics': [
        'Refining motor skills',
        'Decreasing step width',
        'More consistent temporal patterns',
        'Improving balance'
    ]},
    'late_childhood': {'age_range': (10, 12), 'characteristics': [
        'Near-adult kinematic patterns',
        'Kinematic covariation maturity',
        'Approaching adult stride mechanics',
        'Stable gait patterns'
    ]},
    'adolescence': {'age_range': (13, 17), 'characteristics': [
        'Adult-like patterns but still developing',
        'Growth-related temporary inconsistencies',
        'Increasing strength and power',
        'Finalizing motor control'
    ]}
}
```

#### Adult Categories
```python
ADULT_CATEGORIES = {
    'young_adult': {'age_range': (18, 30), 'characteristics': [
        'Peak performance capabilities',
        'Optimal joint ranges of motion',
        'Minimal age-related changes',
        'Reference population for normative data'
    ]},
    'middle_aged': {'age_range': (31, 50), 'characteristics': [
        'Stable performance with minimal decline',
        'Slight decrease in flexibility',
        'Maintained strength and power',
        'Early adaptations to lifestyle changes'
    ]},
    'pre_elderly': {'age_range': (51, 65), 'characteristics': [
        'Early age-related changes',
        'Slight increase in double support time',
        'Beginning of muscle mass decline',
        'Increased variability in gait patterns'
    ]},
    'young_old': {'age_range': (66, 75), 'characteristics': [
        'Noticeable gait changes',
        'Reduced stride length',
        'Increased step width for stability',
        'Slower walking speeds'
    ]},
    'old_old': {'age_range': (76, 100), 'characteristics': [
        'Significant adaptations',
        'Markedly reduced joint ROM',
        'Increased metabolic cost',
        'Greater fall risk'
    ]}
}
```

### Sex-Specific Differences

#### Consistent Across Age Groups
```python
SEX_DIFFERENCES = {
    'female': {
        'gait_characteristics': [
            'Higher cadence (steps/min)',
            'Shorter stride length',
            'Greater ankle dorsiflexion ROM',
            'Greater hip adduction ROM',
            'Increased pelvic motion',
            'Different hip-knee coordination'
        ],
        'biomechanical_patterns': [
            'Higher ankle moments in stance',
            'Different knee valgus patterns',
            'Altered hip moment strategies',
            'Greater reliance on ankle strategy'
        ]
    },
    'male': {
        'gait_characteristics': [
            'Lower cadence',
            'Longer stride length',
            'Greater hip flexion ROM',
            'Reduced ankle ROM',
            'Less pelvic motion',
            'Hip-dominant movement patterns'
        ],
        'biomechanical_patterns': [
            'Higher hip moments in stance',
            'Greater knee extension moments',
            'Different ankle push-off patterns',
            'Hip-dominant propulsion strategy'
        ]
    }
}
```

## Implementation Framework

### Core Stratification Class
```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from enum import Enum

class AgeCategory(Enum):
    EARLY_CHILDHOOD = "early_childhood"
    MIDDLE_CHILDHOOD = "middle_childhood"
    LATE_CHILDHOOD = "late_childhood"
    ADOLESCENCE = "adolescence"
    YOUNG_ADULT = "young_adult"
    MIDDLE_AGED = "middle_aged"
    PRE_ELDERLY = "pre_elderly"
    YOUNG_OLD = "young_old"
    OLD_OLD = "old_old"

class PathologyCategory(Enum):
    HEALTHY = "healthy"
    PARKINSONS = "parkinsons"
    STROKE = "stroke"
    CEREBRAL_PALSY = "cerebral_palsy"
    MULTIPLE_SCLEROSIS = "multiple_sclerosis"

@dataclass
class DemographicProfile:
    """Complete demographic profile for validation stratification"""
    age_years: int
    sex: str  # 'M' or 'F'
    height_m: float
    weight_kg: float
    pathology: Optional[str] = None
    severity: Optional[str] = None  # 'mild', 'moderate', 'severe'
    
    @property
    def age_category(self) -> AgeCategory:
        """Determine age category"""
        if 2 <= self.age_years <= 5:
            return AgeCategory.EARLY_CHILDHOOD
        elif 6 <= self.age_years <= 9:
            return AgeCategory.MIDDLE_CHILDHOOD
        elif 10 <= self.age_years <= 12:
            return AgeCategory.LATE_CHILDHOOD
        elif 13 <= self.age_years <= 17:
            return AgeCategory.ADOLESCENCE
        elif 18 <= self.age_years <= 30:
            return AgeCategory.YOUNG_ADULT
        elif 31 <= self.age_years <= 50:
            return AgeCategory.MIDDLE_AGED
        elif 51 <= self.age_years <= 65:
            return AgeCategory.PRE_ELDERLY
        elif 66 <= self.age_years <= 75:
            return AgeCategory.YOUNG_OLD
        else:
            return AgeCategory.OLD_OLD
    
    @property
    def pathology_category(self) -> PathologyCategory:
        """Determine pathology category"""
        if not self.pathology:
            return PathologyCategory.HEALTHY
        return PathologyCategory(self.pathology.lower())
    
    @property
    def stratification_key(self) -> str:
        """Generate unique stratification key"""
        base_key = f"{self.age_category.value}_{self.sex.lower()}"
        if self.pathology:
            base_key += f"_{self.pathology_category.value}"
            if self.severity:
                base_key += f"_{self.severity}"
        return base_key

class DemographicStratifier:
    """
    Main class for demographic stratification and validation
    """
    
    def __init__(self):
        self.validation_ranges = self._load_demographic_ranges()
        self.population_stats = self._load_population_statistics()
    
    def stratify_subject(self, profile: DemographicProfile) -> Dict[str, str]:
        """
        Stratify subject into demographic categories
        
        Args:
            profile: Subject demographic profile
        
        Returns:
            Dictionary of stratification categories
        """
        return {
            'age_category': profile.age_category.value,
            'sex': profile.sex.lower(),
            'pathology': profile.pathology_category.value,
            'stratification_key': profile.stratification_key,
            'primary_category': self._get_primary_category(profile),
            'fallback_categories': self._get_fallback_categories(profile)
        }
    
    def get_validation_ranges(self, task: str, profile: DemographicProfile) -> Dict:
        """
        Get demographic-specific validation ranges
        
        Args:
            task: Locomotion task (e.g., 'level_walking')
            profile: Subject demographic profile
        
        Returns:
            Validation ranges for the demographic group
        """
        stratification = self.stratify_subject(profile)
        
        # Try primary category first
        primary_key = f"{task}_{stratification['primary_category']}"
        if primary_key in self.validation_ranges:
            return self.validation_ranges[primary_key]
        
        # Try fallback categories
        for fallback in stratification['fallback_categories']:
            fallback_key = f"{task}_{fallback}"
            if fallback_key in self.validation_ranges:
                return self.validation_ranges[fallback_key]
        
        # Final fallback to healthy young adult
        return self.validation_ranges.get(f"{task}_young_adult_healthy", {})
    
    def validate_with_demographics(self, data: Dict[str, np.ndarray], 
                                 task: str, profile: DemographicProfile) -> Dict:
        """
        Perform demographic-aware validation
        
        Args:
            data: Biomechanical data to validate
            task: Locomotion task
            profile: Subject demographic profile
        
        Returns:
            Validation results with demographic context
        """
        ranges = self.get_validation_ranges(task, profile)
        stratification = self.stratify_subject(profile)
        
        validation_results = {
            'demographic_profile': stratification,
            'validation_ranges_used': ranges.get('source', 'default'),
            'variable_results': {}
        }
        
        for variable, values in data.items():
            if variable in ranges:
                validation_results['variable_results'][variable] = \
                    self._validate_variable_with_demographics(
                        values, ranges[variable], profile
                    )
        
        return validation_results
    
    def _get_primary_category(self, profile: DemographicProfile) -> str:
        """Get the most specific demographic category"""
        return profile.stratification_key
    
    def _get_fallback_categories(self, profile: DemographicProfile) -> List[str]:
        """Get fallback categories in order of preference"""
        fallbacks = []
        
        # Remove severity if present
        if profile.severity:
            fallbacks.append(f"{profile.age_category.value}_{profile.sex.lower()}_{profile.pathology_category.value}")
        
        # Remove pathology
        if profile.pathology:
            fallbacks.append(f"{profile.age_category.value}_{profile.sex.lower()}_healthy")
        
        # Remove sex
        fallbacks.append(f"{profile.age_category.value}_healthy")
        
        # Age group fallbacks
        age_fallbacks = self._get_age_fallbacks(profile.age_category)
        for age_category in age_fallbacks:
            fallbacks.append(f"{age_category}_{profile.sex.lower()}_healthy")
            fallbacks.append(f"{age_category}_healthy")
        
        return fallbacks
    
    def _get_age_fallbacks(self, age_category: AgeCategory) -> List[str]:
        """Get age-based fallback categories"""
        fallback_map = {
            AgeCategory.EARLY_CHILDHOOD: ['middle_childhood', 'late_childhood'],
            AgeCategory.MIDDLE_CHILDHOOD: ['late_childhood', 'early_childhood'],
            AgeCategory.LATE_CHILDHOOD: ['adolescence', 'middle_childhood'],
            AgeCategory.ADOLESCENCE: ['young_adult', 'late_childhood'],
            AgeCategory.YOUNG_ADULT: ['middle_aged', 'adolescence'],
            AgeCategory.MIDDLE_AGED: ['young_adult', 'pre_elderly'],
            AgeCategory.PRE_ELDERLY: ['middle_aged', 'young_old'],
            AgeCategory.YOUNG_OLD: ['pre_elderly', 'old_old'],
            AgeCategory.OLD_OLD: ['young_old', 'pre_elderly']
        }
        return fallback_map.get(age_category, ['young_adult'])
```

## Validation Range Generation

### Age-Specific Range Adjustments
```python
class ValidationRangeGenerator:
    """Generate demographic-specific validation ranges"""
    
    def __init__(self):
        self.base_ranges = self._load_base_ranges()  # Young adult healthy ranges
        self.demographic_factors = self._load_demographic_factors()
    
    def generate_demographic_ranges(self, base_task: str, 
                                  demographic_key: str) -> Dict:
        """
        Generate validation ranges for specific demographic
        
        Args:
            base_task: Base task (e.g., 'level_walking')
            demographic_key: Demographic identifier
        
        Returns:
            Adjusted validation ranges
        """
        base_ranges = self.base_ranges[base_task]
        factors = self.demographic_factors.get(demographic_key, {})
        
        adjusted_ranges = {}
        for variable, ranges in base_ranges.items():
            adjusted_ranges[variable] = self._apply_demographic_factors(
                ranges, factors.get(variable, {})
            )
        
        return adjusted_ranges
    
    def _apply_demographic_factors(self, base_ranges: Dict, 
                                 factors: Dict) -> Dict:
        """Apply demographic adjustment factors to ranges"""
        adjusted = {}
        
        for phase, range_dict in base_ranges.items():
            adjusted[phase] = {}
            for bound, value in range_dict.items():
                # Apply multiplicative factor
                multiplier = factors.get(f"{bound}_multiplier", 1.0)
                # Apply additive offset
                offset = factors.get(f"{bound}_offset", 0.0)
                
                adjusted[phase][bound] = (value * multiplier) + offset
        
        return adjusted
```

### Literature-Based Demographic Factors
```python
DEMOGRAPHIC_FACTORS = {
    # Elderly adjustments based on literature
    'young_old_m_healthy': {
        'hip_flexion_angle_ipsi_rad': {
            'max_multiplier': 0.9,    # Reduced ROM
            'min_multiplier': 1.0,
        },
        'knee_flexion_angle_ipsi_rad': {
            'max_multiplier': 0.85,   # Reduced knee flexion
            'min_multiplier': 1.0,
        },
        'ankle_dorsiflexion_angle_ipsi_rad': {
            'max_multiplier': 0.8,    # Significant ankle ROM reduction
            'min_multiplier': 1.0,
        }
    },
    
    # Female-specific adjustments
    'young_adult_f_healthy': {
        'hip_flexion_angle_ipsi_rad': {
            'max_multiplier': 0.95,   # Slightly reduced hip flexion
            'min_multiplier': 1.0,
        },
        'ankle_dorsiflexion_angle_ipsi_rad': {
            'max_multiplier': 1.1,    # Greater ankle ROM
            'min_multiplier': 1.0,
        }
    },
    
    # Pediatric adjustments
    'late_childhood_healthy': {
        'hip_flexion_angle_ipsi_rad': {
            'max_multiplier': 1.1,    # Greater ROM in children
            'min_multiplier': 0.9,
        },
        'knee_flexion_angle_ipsi_rad': {
            'max_multiplier': 1.2,    # Higher knee flexion
            'min_multiplier': 0.9,
        }
    },
    
    # Pathological adjustments
    'young_adult_parkinsons': {
        'hip_flexion_angle_ipsi_rad': {
            'max_multiplier': 0.7,    # Reduced ROM in PD
            'min_multiplier': 1.1,    # Forward trunk posture
        },
        'knee_flexion_angle_ipsi_rad': {
            'max_multiplier': 0.8,    # Reduced knee flexion
            'min_multiplier': 1.0,
        },
        'ankle_dorsiflexion_angle_ipsi_rad': {
            'max_multiplier': 0.6,    # Severely reduced ankle ROM
            'min_multiplier': 1.0,
        }
    }
}
```

## Validation Range Tables

### Example: Level Walking - Elderly Male
```markdown
### Task: level_walking_young_old_m_healthy

**Phase-Specific Range Validation (Male, 66-75 years):**

| Variable | | 0% | | | 25% | | | 50% | | | 75% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | |
| hip_flexion_angle_ipsi_rad | -0.10 | 0.18 | | -0.05 | 0.22 | | -0.15 | 0.27 | | 0.15 | 0.54 | |rad|Reduced ROM vs young adult|
| knee_flexion_angle_ipsi_rad | -0.05 | 0.08 | | 0.05 | 0.20 | | -0.02 | 0.10 | | 0.20 | 0.51 | |rad|Reduced knee flexion|
| ankle_dorsiflexion_angle_ipsi_rad | -0.12 | 0.12 | | 0.05 | 0.16 | | -0.16 | 0.04 | | -0.08 | 0.08 | |rad|Significantly reduced ROM|
```

### Example: Level Walking - Female
```markdown
### Task: level_walking_young_adult_f_healthy

**Phase-Specific Range Validation (Female, 18-30 years):**

| Variable | | 0% | | | 25% | | | 50% | | | 75% | | |Units|Notes|
|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|---:|:---:|:---|:---:|:---|
| | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | **Min** | **Max** | | |
| hip_flexion_angle_ipsi_rad | -0.12 | 0.19 | | -0.06 | 0.24 | | -0.17 | 0.29 | | 0.16 | 0.58 | |rad|Slightly reduced hip flexion|
| ankle_dorsiflexion_angle_ipsi_rad | -0.14 | 0.17 | | 0.06 | 0.22 | | -0.18 | 0.05 | | -0.09 | 0.11 | |rad|Greater ankle ROM|
```

## Integration with Existing System

### Modified Validation Parser
```python
class DemographicValidationParser:
    """Enhanced validation parser with demographic support"""
    
    def __init__(self):
        self.base_parser = ValidationParser()
        self.stratifier = DemographicStratifier()
    
    def validate_dataset(self, data: Dict, metadata: Dict) -> Dict:
        """
        Validate dataset with demographic stratification
        
        Args:
            data: Biomechanical data
            metadata: Subject metadata including demographics
        
        Returns:
            Validation results with demographic breakdown
        """
        results = {'subjects': {}, 'population_summary': {}}
        
        for subject_id, subject_data in data.items():
            # Create demographic profile
            profile = DemographicProfile(
                age_years=metadata[subject_id]['age'],
                sex=metadata[subject_id]['sex'],
                height_m=metadata[subject_id]['height'],
                weight_kg=metadata[subject_id]['weight'],
                pathology=metadata[subject_id].get('pathology')
            )
            
            # Validate with demographic stratification
            subject_results = self.stratifier.validate_with_demographics(
                subject_data, metadata[subject_id]['task'], profile
            )
            
            results['subjects'][subject_id] = subject_results
        
        # Generate population summary
        results['population_summary'] = self._generate_population_summary(results)
        
        return results
```

### CLI Integration
```python
# Enhanced CLI commands
def validate_with_demographics(dataset_path: str, metadata_path: str):
    """Validate dataset with demographic stratification"""
    
    # Load data and metadata
    data = load_dataset(dataset_path)
    metadata = load_metadata(metadata_path)
    
    # Initialize demographic validator
    validator = DemographicValidationParser()
    
    # Perform validation
    results = validator.validate_dataset(data, metadata)
    
    # Generate demographic report
    report = generate_demographic_report(results)
    
    print(f"Validation completed for {len(results['subjects'])} subjects")
    print(f"Population breakdown:")
    for category, count in results['population_summary']['categories'].items():
        print(f"  {category}: {count} subjects")
    
    return results
```

## Population Statistics and Monitoring

### Demographic Coverage Tracking
```python
class PopulationCoverageTracker:
    """Track demographic coverage across datasets"""
    
    def __init__(self):
        self.coverage_stats = {}
    
    def update_coverage(self, dataset_name: str, subjects: List[DemographicProfile]):
        """Update coverage statistics for dataset"""
        stats = {
            'total_subjects': len(subjects),
            'age_distribution': self._analyze_age_distribution(subjects),
            'sex_distribution': self._analyze_sex_distribution(subjects),
            'pathology_distribution': self._analyze_pathology_distribution(subjects),
            'coverage_gaps': self._identify_coverage_gaps(subjects)
        }
        
        self.coverage_stats[dataset_name] = stats
    
    def generate_coverage_report(self) -> Dict:
        """Generate comprehensive coverage report"""
        total_subjects = sum(stats['total_subjects'] 
                           for stats in self.coverage_stats.values())
        
        combined_stats = {
            'total_subjects_all_datasets': total_subjects,
            'datasets': self.coverage_stats,
            'population_priorities': self._identify_population_priorities(),
            'recommended_additions': self._recommend_population_additions()
        }
        
        return combined_stats
```

## Quality Assurance

### Demographic Validation Quality Metrics
```python
def assess_demographic_validation_quality(validation_results: Dict) -> Dict:
    """Assess quality of demographic-specific validation"""
    
    quality_metrics = {
        'coverage_completeness': 0.0,
        'range_appropriateness': 0.0,
        'clinical_validity': 0.0,
        'statistical_soundness': 0.0
    }
    
    # Assess coverage completeness
    represented_demographics = set()
    for subject_results in validation_results['subjects'].values():
        represented_demographics.add(
            subject_results['demographic_profile']['primary_category']
        )
    
    quality_metrics['coverage_completeness'] = len(represented_demographics) / 20  # Assume 20 target categories
    
    # Assess range appropriateness (compare to literature)
    quality_metrics['range_appropriateness'] = assess_literature_alignment(validation_results)
    
    # Assess clinical validity (if clinical data available)
    quality_metrics['clinical_validity'] = assess_clinical_alignment(validation_results)
    
    return quality_metrics
```

## Usage Examples

### Basic Demographic Validation
```python
# Create demographic profile
profile = DemographicProfile(
    age_years=70,
    sex='F',
    height_m=1.62,
    weight_kg=58,
    pathology='parkinsons',
    severity='mild'
)

# Initialize stratifier
stratifier = DemographicStratifier()

# Get validation ranges
ranges = stratifier.get_validation_ranges('level_walking', profile)

# Validate data
results = stratifier.validate_with_demographics(
    subject_data, 'level_walking', profile
)

print(f"Validation used ranges for: {results['validation_ranges_used']}")
print(f"Primary demographic: {results['demographic_profile']['primary_category']}")
```

This demographic stratification system provides a comprehensive framework for population-specific validation while maintaining backward compatibility with existing validation approaches. The system gracefully handles missing demographic categories through intelligent fallback mechanisms and provides clear documentation of which validation ranges were applied to each subject.