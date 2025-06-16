# Phase-Level Failure Analysis for Optimization

## Task Performance Overview

- **decline_walking**: 0.0% success rate (0/3 steps)
- **level_walking**: 0.0% success rate (0/1 steps)

## Most Problematic Phases

- **Heel Strike (0.0%)**: 2 failures
- **Mid-Stance (25.0%)**: 1 failures
- **Toe-Off (50.0%)**: 1 failures

## Most Problematic Variables

- **hip_flexion_angle_ipsi**: 2 failures
- **knee_flexion_angle_ipsi**: 1 failures
- **ankle_flexion_angle_ipsi**: 1 failures

## Top Optimization Targets

1. **decline_walking - hip_flexion_angle_ipsi - Phase 0.0%**
   - Failures: 2
   - Current range: [-0.100, 0.400]
   - Suggested range: [-0.100, 1.074]
   - Needs to expand max by 0.500

2. **decline_walking - knee_flexion_angle_ipsi - Phase 25.0%**
   - Failures: 1
   - Current range: [0.000, 1.200]
   - Suggested range: [0.000, 1.800]
   - Needs to expand max by 0.300

3. **level_walking - ankle_flexion_angle_ipsi - Phase 50.0%**
   - Failures: 1
   - Current range: [-0.300, 0.200]
   - Suggested range: [-0.720, 0.200]
   - Needs to expand min by 0.300
