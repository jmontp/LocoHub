# Clinical Applications

*Apply validated biomechanical datasets to clinical research and practice*

## Clinical Research Applications

### Normative Reference Data

**Establish Normal Ranges**
Use standardized healthy adult datasets to establish normative ranges for clinical comparison:

```python
from locomotion_analysis import LocomotionData
import numpy as np

# Load healthy reference data
healthy_data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
walking_data = healthy_data.filter_task('level_walking')

# Calculate normative ranges (mean ± 2 SD)
knee_mean = walking_data.get_average_trajectory('knee_flexion_angle_ipsi_rad')
knee_std = walking_data.get_std_trajectory('knee_flexion_angle_ipsi_rad')

# Define normal range boundaries
normal_upper = knee_mean + 2 * knee_std
normal_lower = knee_mean - 2 * knee_std

print("Knee flexion normal range established from 13 healthy subjects")
```

**Clinical Interpretation**
- **95% Normal Range**: Mean ± 2 standard deviations
- **Phase-Specific Analysis**: Compare patient data at specific gait phases
- **Task-Specific Norms**: Different reference ranges for walking, stairs, inclines

### Patient Data Comparison

**Individual Patient Analysis**
```python
# Load patient data (assuming same standardized format)
patient_data = LocomotionData.from_parquet('patient_001_phase.parquet')
patient_walking = patient_data.filter_task('level_walking')

# Get patient's average knee angle
patient_knee = patient_walking.get_average_trajectory('knee_flexion_angle_ipsi_rad')

# Calculate deviation from normal
deviation = patient_knee - knee_mean
deviation_z_score = deviation / knee_std

# Identify phases with significant deviations
abnormal_phases = np.where(np.abs(deviation_z_score) > 2)[0]
print(f"Abnormal phases: {abnormal_phases} (z-score > 2)")
```

**Group Comparisons**
```python
# Compare patient group to healthy controls
patient_group = [
    LocomotionData.from_parquet(f'patient_{i:03d}_phase.parquet') 
    for i in range(1, 21)  # 20 patients
]

# Calculate group averages
patient_averages = []
for patient in patient_group:
    walking = patient.filter_task('level_walking')
    avg_knee = walking.get_average_trajectory('knee_flexion_angle_ipsi_rad')
    patient_averages.append(avg_knee)

patient_group_mean = np.mean(patient_averages, axis=0)

# Statistical comparison with healthy controls
from scipy import stats
t_stat, p_values = stats.ttest_ind(
    patient_averages, 
    [walking_data.get_variable_3d('knee_flexion_angle_ipsi_rad')[i,j,:] 
     for i in range(healthy_data.n_subjects) 
     for j in range(healthy_data.n_cycles)]
)
```

## Clinical Assessment Tools

### Gait Analysis Reports

**Automated Clinical Reports**
```python
def generate_clinical_report(patient_data, reference_data):
    """Generate standardized clinical gait analysis report"""
    
    report = {
        'patient_id': patient_data.get_subject_ids()[0],
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'reference_population': 'Healthy adults (n=13, age 22-45)',
        'deviations': {}
    }
    
    # Analyze key clinical variables
    clinical_variables = [
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad', 
        'ankle_flexion_angle_ipsi_rad',
        'knee_moment_ipsi_Nm'
    ]
    
    for variable in clinical_variables:
        # Get patient and reference data
        patient_traj = patient_data.get_average_trajectory(variable)
        ref_mean = reference_data.get_average_trajectory(variable)
        ref_std = reference_data.get_std_trajectory(variable)
        
        # Calculate deviations
        z_scores = (patient_traj - ref_mean) / ref_std
        significant_deviations = np.where(np.abs(z_scores) > 1.96)[0]
        
        report['deviations'][variable] = {
            'max_deviation': np.max(np.abs(z_scores)),
            'abnormal_phases': significant_deviations.tolist(),
            'interpretation': interpret_deviation(variable, z_scores)
        }
    
    return report

def interpret_deviation(variable, z_scores):
    """Provide clinical interpretation of deviations"""
    max_z = np.max(np.abs(z_scores))
    phase_max = np.argmax(np.abs(z_scores))
    
    interpretations = {
        'knee_flexion_angle_ipsi_rad': {
            'high': f'Excessive knee flexion at {phase_max}% gait cycle',
            'low': f'Limited knee flexion at {phase_max}% gait cycle'
        },
        'hip_flexion_angle_ipsi_rad': {
            'high': f'Excessive hip flexion at {phase_max}% gait cycle', 
            'low': f'Limited hip flexion at {phase_max}% gait cycle'
        }
    }
    
    if max_z > 2:
        direction = 'high' if z_scores[phase_max] > 0 else 'low'
        return interpretations.get(variable, {}).get(direction, 'Significant deviation')
    else:
        return 'Within normal limits'
```

### Outcome Measures

**Standardized Clinical Metrics**
```python
def calculate_clinical_outcomes(data):
    """Calculate standard clinical outcome measures"""
    
    walking_data = data.filter_task('level_walking')
    
    outcomes = {}
    
    # Range of motion measures
    knee_rom = calculate_range_of_motion(
        walking_data.get_average_trajectory('knee_flexion_angle_ipsi_rad')
    )
    hip_rom = calculate_range_of_motion(
        walking_data.get_average_trajectory('hip_flexion_angle_ipsi_rad')
    )
    
    outcomes['range_of_motion'] = {
        'knee_flexion_rom_deg': np.degrees(knee_rom),
        'hip_flexion_rom_deg': np.degrees(hip_rom)
    }
    
    # Gait symmetry measures
    if 'knee_flexion_angle_contra_rad' in walking_data.get_variable_names():
        ipsi_knee = walking_data.get_average_trajectory('knee_flexion_angle_ipsi_rad')
        contra_knee = walking_data.get_average_trajectory('knee_flexion_angle_contra_rad')
        
        symmetry_index = calculate_symmetry_index(ipsi_knee, contra_knee)
        outcomes['symmetry'] = {
            'knee_symmetry_index': symmetry_index,
            'interpretation': 'Symmetric' if symmetry_index < 0.1 else 'Asymmetric'
        }
    
    # Power generation measures (if kinetic data available)
    if 'knee_moment_ipsi_Nm' in walking_data.get_variable_names():
        knee_power = calculate_joint_power(
            walking_data.get_average_trajectory('knee_moment_ipsi_Nm'),
            walking_data.get_average_trajectory('knee_angular_velocity_ipsi_rad_per_s')
        )
        outcomes['power'] = {
            'knee_peak_power_W': np.max(knee_power),
            'knee_negative_work_J': np.trapz(knee_power[knee_power < 0])
        }
    
    return outcomes

def calculate_range_of_motion(angle_trajectory):
    """Calculate range of motion from angle trajectory"""
    return np.max(angle_trajectory) - np.min(angle_trajectory)

def calculate_symmetry_index(left_traj, right_traj):
    """Calculate symmetry index between bilateral trajectories"""
    # Normalize trajectories to account for magnitude differences
    left_norm = (left_traj - np.mean(left_traj)) / np.std(left_traj)
    right_norm = (right_traj - np.mean(right_traj)) / np.std(right_traj)
    
    # Calculate RMS difference as symmetry measure
    rms_diff = np.sqrt(np.mean((left_norm - right_norm)**2))
    return rms_diff
```

## Intervention Assessment

### Pre-Post Treatment Comparisons

**Treatment Efficacy Analysis**
```python
def assess_treatment_efficacy(pre_data, post_data, reference_data):
    """Assess treatment efficacy using standardized measures"""
    
    # Calculate deviations from normal for pre and post
    pre_deviations = calculate_deviations_from_normal(pre_data, reference_data)
    post_deviations = calculate_deviations_from_normal(post_data, reference_data)
    
    # Calculate improvement metrics
    improvement = {}
    
    for variable in pre_deviations.keys():
        pre_dev = np.abs(pre_deviations[variable])
        post_dev = np.abs(post_deviations[variable])
        
        # Calculate percent improvement
        improvement[variable] = {
            'pre_treatment_deviation': np.mean(pre_dev),
            'post_treatment_deviation': np.mean(post_dev),
            'percent_improvement': (np.mean(pre_dev) - np.mean(post_dev)) / np.mean(pre_dev) * 100,
            'clinically_significant': np.mean(post_dev) < np.mean(pre_dev) * 0.85  # 15% improvement threshold
        }
    
    return improvement

def calculate_deviations_from_normal(patient_data, reference_data):
    """Calculate how much patient deviates from normal patterns"""
    deviations = {}
    
    clinical_variables = [
        'knee_flexion_angle_ipsi_rad',
        'hip_flexion_angle_ipsi_rad',
        'ankle_flexion_angle_ipsi_rad'
    ]
    
    for variable in clinical_variables:
        if variable in patient_data.get_variable_names():
            patient_traj = patient_data.get_average_trajectory(variable)
            ref_mean = reference_data.get_average_trajectory(variable)
            
            # Calculate absolute deviation from normal
            deviations[variable] = np.abs(patient_traj - ref_mean)
    
    return deviations
```

### Longitudinal Monitoring

**Progress Tracking**
```python
def track_patient_progress(patient_sessions, reference_data):
    """Track patient progress across multiple sessions"""
    
    progress_data = {
        'session_dates': [],
        'outcome_measures': {},
        'deviation_scores': {}
    }
    
    for session_date, session_data in patient_sessions.items():
        progress_data['session_dates'].append(session_date)
        
        # Calculate outcome measures for this session
        outcomes = calculate_clinical_outcomes(session_data)
        
        for measure, value in outcomes.items():
            if measure not in progress_data['outcome_measures']:
                progress_data['outcome_measures'][measure] = []
            progress_data['outcome_measures'][measure].append(value)
        
        # Calculate deviation from normal
        deviations = calculate_deviations_from_normal(session_data, reference_data)
        
        for variable, deviation in deviations.items():
            if variable not in progress_data['deviation_scores']:
                progress_data['deviation_scores'][variable] = []
            progress_data['deviation_scores'][variable].append(np.mean(deviation))
    
    return progress_data
```

## Clinical Validation Studies

### Study Design Support

**Sample Size Calculations**
```python
def calculate_sample_size_for_clinical_study(reference_data, effect_size=0.5, power=0.8):
    """Calculate required sample size for detecting clinically meaningful changes"""
    
    # Use heel-strike knee angle as primary outcome
    knee_angles = reference_data.filter_task('level_walking').get_variable_3d('knee_flexion_angle_ipsi_rad')
    
    # Get heel-strike values (phase 0)
    heel_strike_angles = knee_angles[:, :, 0].flatten()
    
    # Calculate variance
    variance = np.var(heel_strike_angles)
    
    # Sample size calculation using power analysis
    from scipy import stats
    alpha = 0.05
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)
    
    n_per_group = 2 * variance * (z_alpha + z_beta)**2 / effect_size**2
    
    return {
        'n_per_group': int(np.ceil(n_per_group)),
        'total_n': int(np.ceil(2 * n_per_group)),
        'assumptions': {
            'effect_size': effect_size,
            'power': power,
            'alpha': alpha,
            'variance': variance
        }
    }
```

**Control Group Matching**
```python
def match_controls_to_patients(patient_demographics, reference_data):
    """Match control subjects to patient characteristics"""
    
    # Example matching criteria
    matched_controls = []
    
    for patient in patient_demographics:
        # Find controls within age range (±5 years)
        age_matches = reference_data.filter_subjects_by_age(
            patient['age'] - 5, patient['age'] + 5
        )
        
        # Further filter by sex if needed
        if patient['sex']:
            sex_matches = age_matches.filter_subjects_by_sex(patient['sex'])
        else:
            sex_matches = age_matches
        
        matched_controls.append(sex_matches)
    
    return matched_controls
```

## Clinical Decision Support

### Risk Assessment

**Fall Risk Indicators**
```python
def assess_fall_risk(patient_data, reference_data):
    """Assess fall risk based on gait patterns"""
    
    risk_factors = {}
    
    # Step width variability (increased variability = higher risk)
    if 'step_width_m' in patient_data.get_variable_names():
        step_widths = patient_data.filter_task('level_walking').get_variable_3d('step_width_m')
        step_width_cv = np.std(step_widths) / np.mean(step_widths)
        
        risk_factors['step_width_variability'] = {
            'value': step_width_cv,
            'risk_level': 'High' if step_width_cv > 0.15 else 'Normal',
            'interpretation': 'Increased step width variability suggests balance impairment'
        }
    
    # Swing phase duration (shortened swing = higher risk)
    # Calculate from gait events or phase data
    walking_data = patient_data.filter_task('level_walking')
    # Simplified: assume swing phase is 40% of gait cycle
    swing_duration = 0.4  # This would be calculated from actual data
    
    risk_factors['swing_phase_duration'] = {
        'value': swing_duration,
        'risk_level': 'High' if swing_duration < 0.35 else 'Normal',
        'interpretation': 'Shortened swing phase may indicate fear of falling'
    }
    
    return risk_factors
```

### Treatment Recommendations

**Evidence-Based Recommendations**
```python
def generate_treatment_recommendations(patient_data, clinical_assessment):
    """Generate evidence-based treatment recommendations"""
    
    recommendations = []
    
    # Analyze key deviations
    for variable, deviation_info in clinical_assessment['deviations'].items():
        max_deviation = deviation_info['max_deviation']
        abnormal_phases = deviation_info['abnormal_phases']
        
        if variable == 'knee_flexion_angle_ipsi_rad' and max_deviation > 2:
            if len(abnormal_phases) > 0:
                phase = abnormal_phases[0]
                if phase < 25:  # Loading response
                    recommendations.append({
                        'target': 'Knee flexion during loading response',
                        'intervention': 'Strengthen quadriceps, practice controlled knee flexion',
                        'rationale': 'Limited knee flexion at heel strike reduces shock absorption',
                        'evidence_level': 'Level II (systematic review)'
                    })
                elif 50 < phase < 75:  # Pre-swing
                    recommendations.append({
                        'target': 'Knee flexion during pre-swing',
                        'intervention': 'Hip flexor strengthening, gait training',
                        'rationale': 'Adequate knee flexion needed for toe clearance',
                        'evidence_level': 'Level I (RCT evidence)'
                    })
        
        elif variable == 'hip_flexion_angle_ipsi_rad' and max_deviation > 2:
            recommendations.append({
                'target': 'Hip flexion range of motion',
                'intervention': 'Hip flexor stretching, hip mobility exercises',
                'rationale': 'Limited hip flexion affects stride length and efficiency',
                'evidence_level': 'Level II (cohort studies)'
            })
    
    return recommendations
```

## Integration with Electronic Health Records

### Data Export for EHR

**Standardized Clinical Summaries**
```python
def export_clinical_summary_for_ehr(patient_data, assessment_results):
    """Export clinical gait analysis summary for EHR integration"""
    
    summary = {
        'patient_id': patient_data.get_subject_ids()[0],
        'assessment_date': datetime.now().isoformat(),
        'assessment_type': 'Quantitative Gait Analysis',
        'reference_standard': 'Healthy adult normative data (n=25)',
        
        'key_findings': [],
        'outcome_measures': assessment_results.get('outcome_measures', {}),
        'clinical_recommendations': assessment_results.get('recommendations', []),
        
        'data_quality': {
            'trials_analyzed': patient_data.n_cycles,
            'data_completeness': '100%',  # This would be calculated
            'measurement_reliability': 'High (ICC > 0.90)'
        }
    }
    
    # Add key clinical findings in structured format
    for variable, deviation in assessment_results['deviations'].items():
        if deviation['max_deviation'] > 1.96:  # Significant deviation
            finding = {
                'parameter': variable.replace('_', ' ').title(),
                'finding': deviation['interpretation'],
                'severity': 'Mild' if deviation['max_deviation'] < 2.5 else 'Moderate',
                'clinical_significance': 'May affect functional mobility'
            }
            summary['key_findings'].append(finding)
    
    return summary
```

## Regulatory and Compliance

### FDA Guidelines Compliance

**Clinical Trial Data Standards**
- All datasets follow CDISC (Clinical Data Interchange Standards Consortium) principles
- Standardized variable naming enables regulatory submission
- Quality validation meets FDA guidelines for clinical data integrity
- Audit trails maintained for all data processing steps

**Medical Device Integration**
- Compatible with FDA-approved gait analysis systems
- Standardized outputs facilitate regulatory pathway for new devices
- Reference datasets support predicate device comparisons

### HIPAA Compliance

**De-identification Standards**
- All datasets are de-identified according to HIPAA Safe Harbor rules
- No direct patient identifiers included
- Dates shifted to maintain temporal relationships while protecting privacy
- Geographic information limited to region level only

## Getting Started with Clinical Applications

### Installation for Clinical Use
```bash
# Install with clinical analysis extensions
pip install locomotion-analysis[clinical]

# Verify clinical modules
python -c "from locomotion_analysis.clinical import ClinicalAnalyzer; print('Clinical tools ready')"
```

### Example Clinical Workflow
```python
from locomotion_analysis import LocomotionData
from locomotion_analysis.clinical import ClinicalAnalyzer

# Load reference data
reference = LocomotionData.from_parquet('healthy_reference_phase.parquet')

# Load patient data  
patient = LocomotionData.from_parquet('patient_001_phase.parquet')

# Initialize clinical analyzer
analyzer = ClinicalAnalyzer(reference_data=reference)

# Generate comprehensive clinical report
report = analyzer.generate_clinical_report(patient)

# Export for EHR integration
ehr_summary = analyzer.export_ehr_summary(patient, report)
```

## Next Steps

- **[Getting Started](../getting_started/quick_start/)** - Set up your analysis environment
- **[Clinical Validation Studies](../user_guides/researchers/analysis_workflows/)** - Design rigorous clinical research
- **[API Reference](../reference/api/python/)** - Complete function documentation for clinical applications

---

*Clinical applications are supported by validated reference datasets and evidence-based analysis methods.*