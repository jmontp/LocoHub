# Step-Level Debugging Guide for Biomechanical Validation

## Overview

This guide demonstrates how to use the intuitive biomechanical validation system to identify and fix specific data issues at the individual step level, enabling efficient debugging and data correction.

## Key Features for Debugging

### 1. **Independent Task Expectations**
- Each task has completely standalone descriptions (no inheritance)
- Clear, specific angle ranges for each activity
- Clinically meaningful descriptions for easy interpretation

### 2. **Step-Level Error Identification**
- Pinpoints exact failing data points with `step_id` format: `Subject_Task_Phase`
- Shows actual vs. expected values for each measurement
- Provides specific fix suggestions for each error type

### 3. **Actionable Bug Reports**
- Prioritizes most critical issues by severity and error count
- Groups related errors for systematic fixing
- Provides specific technical recommendations

## Example Debugging Workflow

### Step 1: Run Validation
```python
from validation_intuitive_biomechanics import IntuitiveValidator

validator = IntuitiveValidator(df)
validated_df = validator.validate()

# Get comprehensive debugging information
step_errors = validator.get_step_level_errors()
bug_fix_report = validator.get_bug_fix_report()
```

### Step 2: Identify Critical Issues

From the bug fix report, the most critical issue is:
```
📍 S01 / squats / knee_flexion_angle_rad / heel_strike:
   💢 15 severe errors (avg deviation: 159.7°)
   🔧 Fix: Reduce knee flexion from 169.7° to 10.0°- during heel_strike. 
       Verify knee joint center or check for crouch pattern.
```

**What this tells us:**
- Subject S01 has severe knee angle issues during squats
- Knee is flexed 169.7° when it should be near neutral (-5° to 10°)
- This occurs consistently during the heel strike phase (0-10%)
- Likely a measurement calibration or joint definition problem

### Step 3: Examine Specific Failing Steps

The step-level errors show exact problematic data points:
```
Step ID: S01_squats_0.0
- Subject: S01
- Task: squats
- Phase: 0.0% (heel strike)
- Joint: knee_flexion_angle_rad
- Actual: 169.7°
- Expected: -5.0° to 10.0°
- Deviation: 159.7°
- Severity: Severe
```

**Debugging Actions:**
1. **Check joint definition**: Knee joint axis may be incorrectly defined
2. **Verify calibration**: Neutral position may need recalibration
3. **Review data collection**: Check for sensor placement issues
4. **Examine similar cases**: Other subjects with same pattern

### Step 4: Systematic Data Fixing

#### Option A: Fix in Source Data
```python
# Example fix for knee joint calibration offset
offset_correction = -160 * np.pi/180  # Convert 160° to radians

# Apply to specific subject/task combinations identified in bug report
mask = (df['subject_id'] == 'S01') & (df['task_name'] == 'squats')
df.loc[mask, 'knee_flexion_angle_rad'] += offset_correction
```

#### Option B: Fix in Conversion Script
```python
# In conversion script, add calibration correction
if subject_id == 'S01' and 'knee_flexion' in joint_name:
    # Apply known calibration correction for this subject
    joint_angles += knee_offset_correction
```

## Real-World Debugging Examples

### Example 1: Hip Flexion During Running
**Error Report:**
```
Subject: S02, Task: run, Joint: hip_flexion_angle_rad, Phase: mid_stance
Expected: 10-25°, Actual: 45°, Deviation: 20°, Severity: Moderate
Fix: Reduce hip flexion from 45° to 25°- during mid_stance. 
     Check for excessive forward lean or measurement offset.
```

**Possible Causes:**
- Forward trunk lean during running
- Hip joint center estimation error
- Pelvic tilt measurement issues

**Debugging Steps:**
1. Check pelvis/trunk segment definitions
2. Verify hip joint center calculation
3. Compare with other running subjects
4. Review video for actual movement pattern

### Example 2: Ankle Angles During Stair Climbing
**Error Report:**
```
Subject: S03, Task: up_stairs, Joint: ankle_flexion_angle_rad, Phase: heel_strike
Expected: 5-15°, Actual: -10°, Deviation: 15°, Severity: Moderate
Fix: Increase ankle dorsiflexion from -10° to 5°+ during heel_strike.
     Check ankle joint calibration or foot contact definition.
```

**Possible Causes:**
- Ankle joint axis misalignment
- Foot segment definition issues
- Different foot strike pattern on stairs

**Debugging Steps:**
1. Verify ankle joint axis definition
2. Check foot segment orientation
3. Review step contact patterns
4. Compare with level walking data

## Automated Debugging Reports

### Bug Fix Guide (`debug_report_bug_fix_guide.csv`)
Prioritized list of issues with specific fix suggestions:
- Groups errors by subject/task/joint combination
- Shows error counts and severity levels
- Provides actionable fix recommendations
- Sorts by severity and impact

### Step-Level Errors (`debug_report_step_errors.csv`)
Detailed information for every failing data point:
- Exact step identification (`step_id`)
- Actual vs. expected values
- Clinical context for each measurement
- Specific phase information

### Subject Summary (`debug_report_subject_summary.csv`)
High-level overview of subject-specific issues:
- Total errors per subject
- Number of tasks/joints affected
- Average deviation magnitude
- Count of severe errors

## Integration with Data Processing Pipelines

### For Conversion Scripts
```python
# Add validation check during conversion
validator = IntuitiveValidator(converted_df)
validated_df = validator.validate()

# Check if validation passes
if not validated_df['validation_intuitive'].all():
    print("⚠️  Validation issues found!")
    
    # Get debugging information
    bug_report = validator.get_bug_fix_report()
    critical_issues = bug_report[bug_report['typical_severity'] == 'Severe']
    
    if len(critical_issues) > 0:
        print("🚨 CRITICAL ISSUES - Review before proceeding:")
        for _, issue in critical_issues.iterrows():
            print(f"- {issue['subject_id']}/{issue['task_name']}: {issue['fix_suggestion']}")
```

### For Data Analysis Scripts
```python
# Check data quality before analysis
validator = IntuitiveValidator(analysis_df)
validated_df = validator.validate()

# Get quality metrics
total_errors = len(validator.get_step_level_errors())
severe_errors = len(validator.get_step_level_errors().query('severity == "Severe"'))

print(f"Data Quality: {total_errors} total errors, {severe_errors} severe")

# Exclude problematic data if needed
clean_df = validated_df[validated_df['validation_intuitive']]
print(f"Usable data: {len(clean_df)}/{len(validated_df)} rows ({len(clean_df)/len(validated_df)*100:.1f}%)")
```

## Language Model Integration

The debugging reports are designed to be easily consumed by language models for automated data fixing:

### Prompt Template for LM-Assisted Debugging
```
Dataset Validation Issues:

{bug_fix_report}

Step-Level Details:
{step_errors}

Please analyze these biomechanical validation errors and suggest:
1. Most likely root causes for each type of error
2. Specific code changes to fix measurement issues
3. Quality checks to prevent similar issues

Focus on the most severe and frequent errors first.
```

### Automated Fix Generation
```python
def generate_fix_code(bug_report):
    """Generate code suggestions based on validation errors"""
    
    fixes = []
    for _, error in bug_report.iterrows():
        if 'calibration' in error['fix_suggestion']:
            fix_code = f"""
# Fix for {error['subject_id']} {error['joint']} calibration
mask = (df['subject_id'] == '{error['subject_id']}') & (df['task_name'] == '{error['task_name']}')
df.loc[mask, '{error['joint']}'] += {calculate_offset(error)}
"""
            fixes.append(fix_code)
    
    return fixes
```

## Summary

This step-level debugging system provides:

1. **Precise Error Identification**: Exact data points with issues
2. **Independent Task Descriptions**: Clear expectations for each activity
3. **Actionable Fix Suggestions**: Specific recommendations for each error type
4. **Systematic Debugging**: Prioritized reports for efficient issue resolution
5. **Automation-Ready**: Structured output for language model integration

The system enables both human debuggers and automated tools to quickly identify, understand, and fix biomechanical data validation issues at the individual step level, ensuring high-quality datasets for analysis and machine learning applications.