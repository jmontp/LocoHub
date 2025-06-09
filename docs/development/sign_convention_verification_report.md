# Sign Convention Verification Report

**Date**: 2025-01-06  
**Purpose**: Verify that validation expectations match the OpenSim sign conventions

## Executive Summary

✅ **VERIFIED**: The validation expectations in `validation_expectations.md` are **fully consistent** with the OpenSim sign conventions defined in `sign_conventions.md`.

## Sign Convention Reference

According to `sign_conventions.md`, the project follows OpenSim coordinate system:

### Joint Angles
- **Positive flexion**: sagittal plane rotation that decreases joint angle
  - Hip: positive = thigh forward
  - Knee: positive = knee bends
  - Ankle: positive = dorsiflexion (foot up)

### Ground Reaction Forces
- `vertical_grf_N`: positive **upward**
- `ap_grf_N`: positive **anterior/forward**
- `ml_grf_N`: positive **rightward/lateral**

## Verification Results

### 1. Level Walking - Heel Strike (Phase 0%)

| Joint | Range (rad) | Expected Pattern | Verification |
|-------|------------|------------------|--------------|
| Hip Flexion Left | [0.1, 0.6] | Positive (thigh forward) | ✅ Correct - hip flexed at heel strike |
| Knee Flexion Left | [0.0, 0.3] | Small positive (slight bend) | ✅ Correct - slight knee flexion for shock absorption |
| Ankle Flexion Left | [-0.1, 0.1] | Near neutral | ✅ Correct - neutral ankle at contact |

**Visual Confirmation**: Stick figure shows hip at 11.5° flexion (thigh forward) ✅

### 2. Sit to Stand - Seated (Phase 0%)

| Joint | Range (rad) | Expected Pattern | Verification |
|-------|------------|------------------|--------------|
| Hip Flexion | [1.2, 2.0] | Large positive (deep flexion) | ✅ Correct - seated position requires ~90° hip flexion |
| Knee Flexion | [1.0, 1.8] | Large positive (deep flexion) | ✅ Correct - seated position requires ~90° knee flexion |
| Ankle Flexion | [0.0, 0.4] | Slight positive | ✅ Correct - slight dorsiflexion when seated |

**Visual Confirmation**: Stick figure shows hip at 68.8°-114.6° flexion (deep seated position) ✅

### 3. Squats - Bottom Position (Phase 50%)

| Joint | Range (rad) | Expected Pattern | Verification |
|-------|------------|------------------|--------------|
| Hip Flexion | [1.2, 2.2] | Maximum positive | ✅ Correct - deep hip flexion at squat bottom |
| Knee Flexion | [1.6, 2.4] | Maximum positive | ✅ Correct - deep knee flexion at squat bottom |
| Ankle Flexion | [0.2, 0.6] | Positive (dorsiflexion) | ✅ Correct - ankle dorsiflexes for balance |

**Visual Confirmation**: Stick figure shows maximum flexion at all joints ✅

### 4. Level Walking - Push-Off (Phase 50%)

| Joint | Range (rad) | Expected Pattern | Verification |
|-------|------------|------------------|--------------|
| Hip Flexion Left | [-0.3, 0.2] | Negative to small positive | ✅ Correct - hip extends (thigh back) during push-off |
| Ankle Flexion Left | [-0.3, 0.0] | Negative (plantarflexion) | ✅ Correct - ankle plantarflexes for propulsion |

### 5. Decline Walking - Heel Strike (Phase 0%)

| Joint | Range (rad) | Expected Pattern | Verification |
|-------|------------|------------------|--------------|
| Hip Flexion Left | [-0.2, 0.4] | Reduced flexion | ✅ Correct - less hip flexion needed on decline |
| Ankle Flexion Left | [-0.2, 0.0] | Slight plantarflexion | ✅ Correct - plantarflexion for controlled descent |

## Key Biomechanical Validations

### Hip Joint
- ✅ Positive values during forward thigh movements (walking heel strike, stair ascent)
- ✅ Negative values during hip extension (push-off phases)
- ✅ Large positive values during deep flexion activities (sitting, squatting)

### Knee Joint
- ✅ Always positive or zero (knee cannot hyperextend in normal activities)
- ✅ Small values (~0-0.3 rad) during near-full extension
- ✅ Large values (~1.5-2.4 rad) during deep flexion (squats, sitting)

### Ankle Joint
- ✅ Positive values for dorsiflexion (foot up)
- ✅ Negative values for plantarflexion (foot down)
- ✅ Appropriate ranges for each activity phase

## Ground Reaction Forces

The GRF conventions are also correctly applied:
- Vertical GRF ranges from 0 (swing phase) to >2000N (impact/push-off)
- AP GRF shows negative values during braking (heel strike) and positive during propulsion (push-off)
- ML GRF shows appropriate mediolateral balance forces

## Conclusion

The validation expectations demonstrate:

1. **Correct sign interpretation**: All joint angles follow OpenSim conventions
2. **Biomechanically plausible ranges**: Values match expected human movement patterns
3. **Phase-appropriate patterns**: Each task phase shows appropriate joint configurations
4. **Visual confirmation**: Stick figure representations match the numerical ranges

The validation system is properly configured to detect biomechanical anomalies while respecting the OpenSim coordinate system conventions.

## Recommendations

1. Continue using these validation ranges as they correctly implement OpenSim conventions
2. The visual validation figures provide excellent confirmation of the numerical ranges
3. Any future additions should maintain this sign convention consistency