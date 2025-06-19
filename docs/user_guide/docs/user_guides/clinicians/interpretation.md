# Clinical Interpretation Guide

**Purpose**: Practical guide for clinicians to interpret standardized gait analysis data for patient assessment and treatment planning.

## Range of Motion Assessment

**Joint Angle Interpretation**

Normal walking patterns show predictable range of motion (ROM) values:

- **Hip Flexion**: 20-30° during swing phase, 10° extension during stance
- **Knee Flexion**: 60-70° peak during swing, 15° during loading response  
- **Ankle Flexion**: 20° dorsiflexion during swing, 15° plantarflexion at push-off

**Clinical Significance**:
- Reduced ROM indicates stiffness, contractures, or weakness
- Excessive ROM may suggest instability or compensation patterns
- Compare ipsilateral vs contralateral sides for asymmetry assessment

```python
# Example: Extract peak knee flexion for ROM assessment
data = LocomotionData('patient_data_phase.parquet')
knee_flexion = data.get_variable('knee_flexion_angle_ipsi_rad')
peak_knee_flexion = np.max(knee_flexion) * 180/np.pi  # Convert to degrees
```

## Symmetry Analysis

**Bilateral Comparison**

Healthy gait shows high symmetry between limbs (>90% similarity):

- **Step timing**: Stance and swing durations should be nearly equal
- **Joint angles**: Peak values should differ by <5° between sides
- **Movement patterns**: Phase relationships should be consistent

**Clinical Red Flags**:
- >10° difference in peak joint angles suggests pathology
- Asymmetric timing patterns indicate compensation or weakness
- Consistent phase shifts may indicate neurological involvement

```python
# Example: Calculate hip flexion symmetry
hip_ipsi = data.get_variable('hip_flexion_angle_ipsi_rad')
hip_contra = data.get_variable('hip_flexion_angle_contra_rad')
symmetry_index = np.corrcoef(hip_ipsi.mean(axis=0), hip_contra.mean(axis=0))[0,1]
```

## Timing and Phase Analysis

**Gait Cycle Timing**

Normal phase distribution:
- **Stance Phase**: 60% of gait cycle (loading response, mid-stance, push-off)
- **Swing Phase**: 40% of gait cycle (initial swing, mid-swing, terminal swing)
- **Double Support**: ~10% at heel strike and toe-off

**Clinical Interpretation**:
- Prolonged stance suggests weakness or pain avoidance
- Shortened swing indicates stiffness or fear of falling
- Altered double support timing shows balance concerns

**Phase-Specific Analysis**:
- **0% (Heel Strike)**: Assess initial contact patterns
- **25% (Loading Response)**: Evaluate shock absorption
- **50% (Mid-Stance)**: Check stability and weight acceptance
- **75% (Pre-Swing)**: Analyze push-off mechanics

## Abnormal Pattern Recognition

**Common Pathological Patterns**

1. **Crouch Gait**: Excessive knee and hip flexion throughout stance
   - Indicates quadriceps weakness or spasticity
   - Look for >20° knee flexion during mid-stance

2. **Stiff-Knee Gait**: Reduced knee flexion during swing
   - Suggests rectus femoris overactivity or knee stiffness
   - Peak swing knee flexion <45° is concerning

3. **Equinus Gait**: Excessive plantarflexion, limited dorsiflexion
   - Indicates gastrocnemius/soleus tightness or weakness
   - Look for persistent plantarflexion during swing

4. **Trendelenburg Pattern**: Hip drop during stance
   - Shows gluteus medius weakness
   - Compensatory trunk lean or contralateral pelvic drop

**Clinical Decision Support**:
- Compare patient data to normal ranges in validation specifications
- Use bilateral comparisons to identify compensation patterns
- Focus on functional phases (heel strike, push-off) for treatment targeting
- Consider temporal parameters alongside kinematic data for comprehensive assessment

> **Note**: Always correlate quantitative gait analysis with clinical examination and functional assessment. These metrics support but do not replace clinical judgment.