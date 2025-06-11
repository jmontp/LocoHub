# Expected Validation Failures Report

## Purpose
This report documents the intentional violations introduced in the demo datasets
for testing the accuracy of the dataset_validator_phase.py system.

## Validation Scenarios

### Subject: SUB01

#### Task: level_walking

**Step 0:**
- `hip_flexion_angle_contra_rad`: Set to 0.8 rad at phases [0, 37, 75, 112]

**Step 1:**
- `hip_flexion_angle_contra_rad`: Set to 0.9 rad at phases [0, 37, 75, 112]

#### Task: incline_walking

**Step 2:**
- `knee_flexion_angle_contra_rad`: Set to 1.5 rad at phases [0, 37, 75, 112]

### Subject: SUB02

#### Task: decline_walking

**Step 0:**
- `ankle_flexion_angle_contra_rad`: Set to -0.5 rad at phases [0, 37, 75, 112]

**Step 3:**
- `hip_flexion_angle_contra_rad`: Set to 0.8 rad at phases [0, 37]
- `knee_flexion_angle_ipsi_rad`: Set to 1.2 rad at phases [75, 112]


## Expected Validation Results

### Efficient Validation Approach
The validation system uses representative phase validation, checking only key phases
(0%, 25%, 50%, 75%) rather than all 150 points per gait cycle.

### Total Expected Failures
Based on the scenarios above, the validation system should detect approximately
**20** validation failures when using the efficient approach.

### Accuracy Testing
When running dataset_validator_phase.py on the demo_violations_phase.parquet dataset,
the number of detected failures should match this expected count for 100% accuracy.

---
*Generated on 2025-06-11 16:48:38 by demo_dataset_validator_phase.py*
