# Population Expansion Roadmap
## Wave 2 User Experience - Lane C: Population Expansion

Created: 2025-06-20 with user permission
Purpose: Comprehensive plan for expanding locomotion data standardization beyond healthy young adults

Intent: This document establishes a framework for inclusive biomechanical analysis across diverse populations, enabling clinical and research applications across demographics by integrating pathological datasets, anthropometric scaling, and age/sex stratification systems.

---

## Executive Summary

The current locomotion data standardization project focuses primarily on healthy young adults (ages 18-60, N=34 across 3 datasets). To enable broader clinical and research applications, we need systematic expansion to include pathological populations, proper anthropometric scaling, and demographic stratification. This roadmap provides research-backed strategies for achieving population-inclusive biomechanical analysis.

### Current Population Limitations
- **Age Range**: 18-60 years (no pediatric or elderly populations)
- **Health Status**: Healthy individuals only (no pathological conditions)
- **Demographics**: Limited diversity across race, ethnicity, and socioeconomic factors
- **Validation Ranges**: Based solely on healthy young adult norms

## Task 1: Pathological Population Datasets

### Available Datasets Identified

#### 1. Parkinson's Disease Datasets
**PhysioNet Gait Database**
- **Subjects**: 93 PD patients + 73 controls
- **Demographics**: Mean age 66.3 years, 63% men (PD), 55% men (controls)  
- **Data Type**: Ground Reaction Force (GRF) from 16 sensors (8 per foot)
- **Format**: Two-minute walking trials
- **Access**: Open access via PhysioNet
- **URL**: https://physionet.org/content/gaitpdb/1.0.0/

**FDA WearGait-PD Dataset**
- **Subjects**: PD patients + age-matched controls
- **Data Type**: Raw IMU data (13 sensors) + sensorized insoles (16 pressure sensors per foot)
- **Measurements**: 3-DOF acceleration, rotational velocity, magnetic field, orientation
- **Access**: Open access via FDA Center for Devices and Radiological Health
- **Integration**: Requires conversion from IMU/pressure to joint kinematics/kinetics

#### 2. Cerebral Palsy Datasets
**Research Dataset (LSTM Study)**
- **Subjects**: 363 cerebral palsy patients
- **Demographics**: Age 11.8 ± 3.2 years
- **Data Type**: Foot-marker kinematics
- **Application**: Gait event detection using deep learning
- **Access**: Contact researchers for potential collaboration

#### 3. Multi-Pathology Datasets
**Gait Disorder Classification Dataset**
- **Conditions**: Multiple sclerosis, stroke, cerebral palsy
- **Data Type**: Gait force data
- **Performance**: 89.8% classification accuracy achieved
- **Access**: Through research collaboration

### Integration Requirements

#### Data Format Standardization
1. **Coordinate System Alignment**: Convert from various coordinate systems to standard OpenSim conventions
2. **Sampling Rate Harmonization**: Resample to common frequencies (100/200 Hz)
3. **Variable Mapping**: Map pathological dataset variables to standard locomotion features
4. **Missing Data Handling**: Develop strategies for incomplete kinematic/kinetic data

#### Validation Adaptations
1. **Pathology-Specific Ranges**: Develop separate validation ranges for each condition
2. **Severity Scaling**: Account for disease severity levels (mild, moderate, severe)
3. **Asymmetry Handling**: Adapt bilateral validation for asymmetric pathologies
4. **Non-Cyclic Patterns**: Validate irregular gait patterns common in pathologies

### Implementation Plan

#### Phase 1: Proof of Concept (Months 1-3)
- Integrate PhysioNet Parkinson's dataset as pilot
- Develop conversion pipeline from GRF to joint moments
- Create pathology-specific validation ranges
- Test with existing validation framework

#### Phase 2: Multi-Pathology Integration (Months 4-6)
- Add cerebral palsy and stroke datasets
- Develop automated pathology detection/classification
- Create condition-specific analysis workflows
- Validate against clinical gold standards

#### Phase 3: Clinical Validation (Months 7-9)
- Collaborate with clinical partners for validation
- Develop clinical interpretation guidelines
- Create pathology-specific visualization tools
- Establish quality control metrics

## Task 2: Anthropometric Scaling System

### Literature-Based Scaling Methods

#### 1. Joint Moment Normalization
**Body Weight × Height Method**
- **Rationale**: Most effective at reducing gender-based differences
- **Application**: Normalize moments to %BW×Height
- **Literature Support**: Reduces anthropometric effects better than body weight alone
- **Implementation**: `moment_normalized = moment / (body_weight_kg × height_m)`

**Allometric Scaling**
- **Rationale**: Addresses non-linear relationships between size and strength
- **Application**: Power law scaling: `moment_scaled = moment / (body_mass^a × height^b)`
- **Literature Support**: Superior to ratio scaling for removing anthropometric effects
- **Implementation**: Determine optimal exponents (a, b) through regression analysis

#### 2. Ground Reaction Force Normalization
**Body Weight Normalization**
- **Standard Method**: Normalize forces to body weight percentage
- **Implementation**: `force_normalized = force_N / (body_weight_kg × 9.81)`
- **Application**: Universal across all populations and conditions

**Advanced Normalization Techniques**
- **Offset Normalization**: For variables with non-zero baselines
- **Power Curve Normalization**: For non-linear relationships
- **Literature Support**: More appropriate than division normalization for some variables

#### 3. Population-Specific Scaling Factors

**Pediatric Populations**
- **Height-Based Scaling**: Account for growth-related changes
- **Maturation Scaling**: Consider developmental stage beyond chronological age
- **Bone Density Factors**: Account for developing skeletal system

**Elderly Populations**  
- **Sarcopenia Adjustments**: Account for age-related muscle loss
- **Bone Density Corrections**: Adjust for osteoporotic changes
- **Metabolic Scaling**: Consider reduced metabolic capacity

### Implementation Framework

#### Core Scaling Module
```python
class AnthropometricScaler:
    def __init__(self, method='body_weight_height'):
        self.method = method
        self.population_factors = self._load_population_factors()
    
    def scale_moments(self, moments, body_weight, height, age=None, sex=None):
        """Apply anthropometric scaling to joint moments"""
        
    def scale_forces(self, forces, body_weight):
        """Apply body weight normalization to forces"""
        
    def get_population_factor(self, age, sex, pathology=None):
        """Get population-specific scaling factors"""
```

#### Validation Integration
- **Scaled Validation Ranges**: Develop ranges for scaled vs. raw data
- **Population-Specific Ranges**: Separate ranges for different scaling methods
- **Quality Metrics**: Assess scaling effectiveness through variance reduction

## Task 3: Age/Sex Stratification System

### Literature-Based Age Categories

#### 1. Pediatric Stratification
**Age Groups**:
- **Early Childhood**: 2-5 years (developing basic motor patterns)
- **Middle Childhood**: 6-9 years (refining motor skills)
- **Late Childhood**: 10-12 years (approaching adult patterns)
- **Adolescence**: 13-18 years (adult-like but still developing)

**Key Differences**:
- Kinematic covariation matures by age 10
- Stride length increases with age and height
- Step width decreases with age
- Cadence decreases with age (approaches adult values)

#### 2. Adult Stratification
**Age Groups**:
- **Young Adults**: 18-30 years (peak performance)
- **Middle-Aged**: 31-50 years (stable performance)
- **Pre-Elderly**: 51-65 years (early decline)
- **Young-Old**: 66-75 years (noticeable changes)
- **Old-Old**: 76+ years (significant adaptations)

**Key Differences**:
- Stride length decreases with age
- Double support time increases
- Joint range of motion decreases (especially ankle)
- Metabolic cost increases

#### 3. Sex-Specific Differences

**Across All Ages**:
- **Women**: Higher cadence, shorter stride length, greater ankle ROM
- **Men**: Longer stride length, greater hip ROM, different joint coordination
- **Clinical Implications**: Sex differences persist into older adulthood

### Validation Range Stratification

#### Age-Stratified Ranges
```markdown
### Task: level_walking_elderly

**Phase-Specific Range Validation (Age 65+):**

| Variable | 0% Min | 0% Max | 25% Min | 25% Max | ... |
|----------|--------|--------|---------|---------|-----|
| hip_flexion_angle_ipsi_rad | -0.15 | 0.25 | -0.10 | 0.30 | ... |
```

#### Sex-Stratified Ranges
```markdown
### Task: level_walking_female

**Phase-Specific Range Validation (Female-Specific):**

| Variable | 0% Min | 0% Max | 25% Min | 25% Max | ... |
|----------|--------|--------|---------|---------|-----|
| ankle_dorsiflexion_angle_ipsi_rad | -0.20 | 0.30 | -0.15 | 0.35 | ... |
```

#### Combined Stratification
```markdown
### Task: level_walking_elderly_female

**Phase-Specific Range Validation (Elderly Female):**
```

### Implementation Framework

#### Stratification Module
```python
class DemographicStratifier:
    def __init__(self):
        self.age_categories = self._define_age_categories()
        self.sex_factors = self._define_sex_factors()
    
    def categorize_subject(self, age, sex, pathology=None):
        """Determine appropriate validation category"""
        
    def get_validation_ranges(self, task, age_category, sex, pathology=None):
        """Get demographic-specific validation ranges"""
        
    def validate_with_demographics(self, data, metadata):
        """Perform demographic-aware validation"""
```

#### Validation Integration
- **Dynamic Range Selection**: Automatically select appropriate ranges based on demographics
- **Multi-Category Validation**: Support subjects spanning multiple categories
- **Uncertainty Quantification**: Provide confidence intervals for boundary cases

## Implementation Strategy

### Phase 1: Foundation (Months 1-3)
**Deliverables**:
- Anthropometric scaling module implementation
- Basic age/sex stratification system
- Integration with existing validation framework
- Documentation and testing

**Success Metrics**:
- Scaling reduces variance by >20% in mixed populations
- Age/sex stratification improves validation accuracy by >15%
- All current datasets remain compatible

### Phase 2: Pathological Integration (Months 4-6)
**Deliverables**:
- Parkinson's dataset integration (PhysioNet)
- Pathology-specific validation ranges
- Clinical interpretation guidelines
- Automated pathology detection system

**Success Metrics**:
- Successful integration of ≥100 pathological subjects
- Validation accuracy >90% for pathological data
- Clinical validation from partner institutions

### Phase 3: Comprehensive Population Coverage (Months 7-12)
**Deliverables**:
- Pediatric and elderly population datasets
- Complete demographic stratification system
- Multi-pathology support (stroke, cerebral palsy, etc.)
- Population-specific analysis workflows

**Success Metrics**:
- Coverage of age range 5-85 years
- ≥3 pathological conditions supported
- Validation ranges for ≥10 demographic strata

## Resource Requirements

### Technical Infrastructure
- **Storage**: Additional 50-100 GB for pathological datasets
- **Computing**: Increased processing power for population-specific analyses
- **Validation**: Extended validation suite covering all populations

### Partnerships
- **Clinical Collaborations**: Partner with rehabilitation hospitals
- **Research Institutions**: Collaborate with movement disorder labs
- **Data Providers**: Establish agreements with dataset owners

### Quality Assurance
- **Clinical Review**: Expert review of pathological validation ranges
- **Population Validation**: Test with diverse populations
- **Longitudinal Tracking**: Monitor population-specific performance

## Expected Impact

### Clinical Applications
- **Diagnostic Support**: Population-specific normative databases
- **Treatment Monitoring**: Personalized outcome tracking
- **Risk Assessment**: Demographic-aware fall risk prediction

### Research Enablement
- **Population Studies**: Enable large-scale demographic comparisons
- **Intervention Research**: Support population-specific interventions
- **Longitudinal Studies**: Track changes across lifespan

### User Experience
- **Inclusive Design**: Ensure all populations can use the system
- **Personalized Feedback**: Provide population-appropriate interpretations
- **Clinical Translation**: Bridge research and clinical practice

## Conclusion

This population expansion roadmap provides a comprehensive framework for transforming the locomotion data standardization project from a healthy young adult focus to an inclusive system supporting diverse populations. The three-phase implementation strategy balances immediate impact with long-term sustainability, ensuring that biomechanical analysis becomes accessible and relevant across all demographics.

The integration of pathological datasets, anthropometric scaling, and demographic stratification will enable clinical applications while maintaining scientific rigor. This expansion represents a critical step toward making biomechanical analysis truly inclusive and clinically relevant.

---

**Next Steps**: 
1. Review and approve this roadmap with project stakeholders
2. Prioritize implementation phases based on available resources
3. Establish clinical partnerships for validation
4. Begin Phase 1 implementation with existing datasets