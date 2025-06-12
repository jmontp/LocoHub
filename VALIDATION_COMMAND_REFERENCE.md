# Validation Expectations Command Reference

**Created**: 2025-06-11  
**Purpose**: Command reference for modifying kinematic validation ranges in `docs/standard_spec/validation_expectations_kinematic.md`

## Command Formats

### Format 1: Move/Resize Ranges
```
<task>:<joint>:<%>,<raise|lower><degrees>,<widen|shorten><degrees>
```

**Actions:**
- `raise X degrees`: Move entire range up by X degrees (add X to both min and max)
- `lower X degrees`: Move entire range down by X degrees (subtract X from both min and max)  
- `widen X degrees`: Expand range by X degrees (subtract X/2 from min, add X/2 to max)
- `shorten X degrees`: Shrink range by X degrees (add X/2 to min, subtract X/2 from max)

**Examples:**
- `level_walking:ankle_flexion:0,raise10,widen5` - Move ankle range up 10° and expand by 5°
- `decline_walking:knee_flexion:50,lower3,shorten8` - Move knee range down 3° and shrink by 8°

### Format 2: Direct Set Ranges  
```
<task>:<joint>:<%>,<upper_degrees>,<lower_degrees>
```

**Actions:**
- Sets exact range bounds in degrees (automatically converted to radians)
- `<upper_degrees>`: Maximum value of the range
- `<lower_degrees>`: Minimum value of the range

**Examples:**
- `level_walking:knee_flexion:50,45,-5` - Set range to [-5°, 45°]
- `incline_walking:hip_flexion:25,60,10` - Set range to [10°, 60°]

## Valid Parameters

**Tasks:**
- `level_walking`
- `incline_walking` 
- `decline_walking`
- `up_stairs`
- `down_stairs`
- `run`
- `sit_to_stand`
- `jump`
- `squats`

**Joints:**
- `hip_flexion`
- `knee_flexion`
- `ankle_flexion`

**Phases:**
- `0` (Heel Strike / Initial Contact)
- `25` (Mid-Stance / Loading)
- `50` (Toe-Off / Push-off)
- `75` (Mid-Swing / Flight)

## Commands Executed (2025-06-11)

### Session: UMich 2021 Validation Improvements

**Initial Command:**
```
decline_walking:hip_flexion:0,raise10,widen10
```
- **Result**: Phase 0% range changed from [-0.1, 0.4] to [-0.01, 0.66] rad
- **Effect**: Raised range by 10° and widened by 10°

**Batch Commands (decline_walking improvements):**
```
decline_walking:hip_flexion:25,40,11        # Phase 25%: [11°, 40°] = [0.19, 0.70] rad
decline_walking:hip_flexion:50,40,11        # Phase 50%: [11°, 40°] = [0.19, 0.70] rad  
decline_walking:hip_flexion:75,40,11        # Phase 75%: [11°, 40°] = [0.19, 0.70] rad
decline_walking:knee_flexion:0,23,-10       # Phase 0%:  [-10°, 23°] = [-0.17, 0.40] rad
decline_walking:knee_flexion:25,50,-10      # Phase 25%: [-10°, 50°] = [-0.17, 0.87] rad
decline_walking:knee_flexion:50,60,-10      # Phase 50%: [-10°, 60°] = [-0.17, 1.05] rad
decline_walking:knee_flexion:75,90,20       # Phase 75%: [20°, 90°] = [0.35, 1.57] rad
decline_walking:ankle_flexion:0,23,-23      # Phase 0%:  [-23°, 23°] = [-0.40, 0.40] rad
decline_walking:ankle_flexion:25,8,-20      # Phase 25%: [-20°, 8°] = [-0.35, 0.14] rad
decline_walking:ankle_flexion:50,0,-40      # Phase 50%: [-40°, 0°] = [-0.70, 0.00] rad
decline_walking:ankle_flexion:75,15,-20     # Phase 75%: [-20°, 15°] = [-0.35, 0.26] rad
```

**Additional Hip Flexion Adjustments:**
```
decline_walking:hip_flexion:50,35,-23       # Phase 50%: [-23°, 35°] = [-0.40, 0.61] rad
decline_walking:hip_flexion:75,60,0         # Phase 75%: [0°, 60°] = [0.00, 1.05] rad
```

### Final decline_walking Validation Ranges

**Hip Flexion (hip_flexion_angle_ipsi_rad):**
- **Phase 0%**: [-0.01, 0.66] rad (≈ [-0.6°, 38°])
- **Phase 25%**: [0.19, 0.70] rad (≈ [11°, 40°])  
- **Phase 50%**: [-0.40, 0.61] rad (≈ [-23°, 35°])
- **Phase 75%**: [0.00, 1.05] rad (≈ [0°, 60°])

**Knee Flexion (knee_flexion_angle_ipsi_rad):**
- **Phase 0%**: [-0.17, 0.40] rad (≈ [-10°, 23°])
- **Phase 25%**: [-0.17, 0.87] rad (≈ [-10°, 50°])
- **Phase 50%**: [-0.17, 1.05] rad (≈ [-10°, 60°])
- **Phase 75%**: [0.35, 1.57] rad (≈ [20°, 90°])

**Ankle Flexion (ankle_flexion_angle_ipsi_rad):**
- **Phase 0%**: [-0.40, 0.40] rad (≈ [-23°, 23°])
- **Phase 25%**: [-0.35, 0.14] rad (≈ [-20°, 8°])
- **Phase 50%**: [-0.70, 0.00] rad (≈ [-40°, 0°])
- **Phase 75%**: [-0.35, 0.26] rad (≈ [-20°, 15°])

## Implementation Notes

### Automatic Actions After Each Command
1. **Range updates**: Values automatically converted from degrees to radians
2. **Plot generation**: `python3 source/validation/generate_validation_plots.py --tasks <task>` 
3. **File updates**: `docs/standard_spec/validation_expectations_kinematic.md` modified in-place

### Degree to Radian Conversion
- **Formula**: `radians = degrees × π / 180`
- **Common conversions**:
  - 10° = 0.1745 rad
  - 15° = 0.2618 rad  
  - 20° = 0.3491 rad
  - 30° = 0.5236 rad
  - 45° = 0.7854 rad
  - 60° = 1.0472 rad
  - 90° = 1.5708 rad

### Validation Impact Results

**UMich 2021 Dataset Validation Improvement:**
- **Before changes**: 0/8305 steps passed (0.0% success rate)
- **After decline_walking changes**: 1920/8305 steps passed (23.1% success rate)

**Task-specific improvements:**
- **decline_walking**: 0% → 54.6% success rate ✅
- **incline_walking**: 0% → 18.8% success rate ✅  
- **level_walking**: 0% → 0% (still needs adjustment)

### Usage Instructions

1. **Issue command** in format specified above
2. **Automatic processing**: 
   - Range values updated in validation file
   - Plots regenerated for affected task
   - Changes committed to file system
3. **Validation testing**: Re-run dataset validation to see improvements
4. **Iteration**: Adjust ranges based on validation results

### File Locations

- **Main validation file**: `docs/standard_spec/validation_expectations_kinematic.md`
- **Plot generator**: `source/validation/generate_validation_plots.py`
- **Dataset validator**: `source/validation/dataset_validator_phase.py`
- **Validation plots output**: `docs/standard_spec/validation/`
- **Validation reports**: `docs/datasets_documentation/validation_reports/`

## Command History Template

**Date**: YYYY-MM-DD  
**Session Purpose**: [Brief description]  
**Dataset Target**: [Dataset being optimized]

**Commands Executed:**
```
[List of commands with results]
```

**Validation Results:**
- **Before**: X/Y steps passed (Z% success rate)
- **After**: X/Y steps passed (Z% success rate)
- **Improvement**: +Z% success rate

**Notes**: [Any observations or follow-up needed]

---

*This reference enables reproducible validation range adjustments for biomechanical dataset optimization.*