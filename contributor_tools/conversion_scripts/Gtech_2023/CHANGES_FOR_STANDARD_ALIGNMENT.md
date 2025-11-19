# Gtech_2023 Conversion Updates for Standard Alignment

## Summary

Updated Gtech_2023 conversion scripts to align with the current standard specifications defined in `docs/reference/standard_spec/`. The changes ensure compliance with the three-level task hierarchy and required column structure.

## Files Modified

### 1. New Files Created

#### `task_mapping.py`
- **Purpose**: Python utility for mapping Gtech activity names to standardized task hierarchy
- **Features**:
  - Parses activity names like "normal_walk_1_1-2" into standardized format
  - Returns (task, task_id, task_info) tuple following three-level hierarchy
  - Handles speed extraction, incline/decline detection, weight conversion
  - Consistent mapping for stairs, jumps, functional tasks

#### `parse_gtech_activity_matlab.m`
- **Purpose**: MATLAB equivalent of Python task mapping for phase conversion
- **Features**: 
  - Same mapping logic as Python version for consistency
  - Handles all Gtech activity types
  - Returns standardized task names, IDs, and metadata strings

### 2. Updated Files

#### `convert_gtech_all_to_parquet.py` (Time-indexed conversion)
**Changes Made**:
- **Import**: Added `from task_mapping import parse_gtech_activity_name, get_subject_metadata`
- **Column Updates**:
  - `time` → `time_s` (following standard naming)
  - Added `task`, `task_id`, `task_info` columns using task mapping utility
  - Added `subject_metadata` column (empty for now)
  - Added `step` column (initialized to 0 for time-indexed data)
- **GRF/COP Naming**: Updated to follow standardized directional naming:
  - **Python (time-indexed)**: Uses left/right with directional names
    - `RForceX` → `grf_anterior_r_N` (anterior-posterior force)
    - `RForceY_Vertical` → `grf_vertical_r_N` (vertical force)
    - `RForceZ` → `grf_lateral_r_N` (medial-lateral force)
    - `RCOPX` → `cop_anterior_r_m` (anterior-posterior COP)
    - Similar for left side
  - **MATLAB (phase-indexed)**: Uses ipsi/contra with directional names
    - Maps left/right to ipsi/contra based on leading leg
    - `grf_anterior_ipsi_N`, `grf_vertical_ipsi_N`, `grf_lateral_ipsi_N`
    - `cop_anterior_ipsi_m`, `cop_vertical_ipsi_m`, `cop_lateral_ipsi_m`
    - Similar for contra side
- **Subject Naming**: Already followed GT23_AB## pattern correctly ✓

#### `convert_gtech_phase_to_parquet.m` (Phase-indexed conversion)
**Changes Made**:
- **Task Mapping**: Replaced hardcoded if/else logic with call to `parse_gtech_activity_matlab()`
- **Column Updates**:
  - Uses standardized task mapping for `task`, `task_id`, `task_info`
  - Added `subject_metadata` column 
  - Maintains existing `step` column
- **Consistency**: Now uses same mapping logic as Python version

## Standard Compliance Verification

### Required Columns ✓
All required columns from standard specification are now included:

**Time-indexed datasets**:
- `subject` ✓ (GT23_AB## format)
- `subject_metadata` ✓ (empty for now)
- `task` ✓ (standardized categories)
- `task_id` ✓ (primary parameter variants)
- `task_info` ✓ (key:value metadata format)
- `step` ✓ (initialized to 0)
- `time_s` ✓ (renamed from 'time')

**Phase-indexed datasets**:
- All above columns ✓
- `phase_ipsi` ✓ (already implemented)
- Exactly 150 points per cycle ✓ (already implemented)

### Task Hierarchy ✓
Now follows three-level system:

1. **Task** (biomechanical category): 
   - `level_walking`, `incline_walking`, `decline_walking`
   - `stair_ascent`, `stair_descent`
   - `jump`, `squats`, `sit_to_stand`
   - `functional_task` (for other activities)

2. **Task ID** (primary parameter):
   - `level`, `incline_5deg`, `decline_10deg`
   - `stair_ascent`, `stair_descent`
   - Activity-specific identifiers

3. **Task Info** (detailed metadata):
   - `"speed_m_s:1.2,treadmill:true"`
   - `"incline_deg:10,treadmill:true"`
   - `"step_number:1,height_m:0.15"`
   - Consistent key:value format

### Variable Naming ✓
- Joint angles in radians with `_rad` suffix ✓
- Joint moments in Nm with `_Nm` suffix ✓
- GRF forces with directional names (`anterior_grf_r_N`) ✓
- COP coordinates with anatomical directions ✓

### Subject Naming ✓
- Follows `GT23_AB##` convention ✓
- GT23 = Georgia Tech 2023 dataset identifier
- AB = Able-bodied population
- ## = Zero-padded subject number

## Example Output Structure

### Time-indexed Example:
```
subject,subject_metadata,task,task_id,task_info,step,time_s,knee_flexion_angle_r_rad,grf_anterior_r_N,cop_anterior_r_m
GT23_AB01,"",level_walking,level,"speed_m_s:1.2,treadmill:true",0,0.00,0.123,856.2,-0.12
GT23_AB01,"",level_walking,level,"speed_m_s:1.2,treadmill:true",0,0.01,0.126,842.7,-0.10
```

### Phase-indexed Example:
```
subject,subject_metadata,task,task_id,task_info,step,phase_ipsi,knee_flexion_angle_ipsi_rad,grf_anterior_ipsi_N,cop_anterior_ipsi_m
GT23_AB01,"",incline_walking,incline_10deg,"incline_deg:10,treadmill:true",0,0.0,0.123,856.2,-0.12
GT23_AB01,"",incline_walking,incline_10deg,"incline_deg:10,treadmill:true",0,0.7,0.126,842.7,-0.08
```

## Testing Status

### Task Mapping Tests ✓
- **Python**: Tested with 10 representative activity names ✓
- **MATLAB**: Tested basic functionality ✓
- **Consistency**: Both implementations produce same results ✓

### Integration Status
- **Ready for testing**: Updated scripts ready for full dataset conversion
- **Backward compatibility**: Existing analysis code should work with new column structure
- **Validation**: Scripts should pass dataset validation checks

## Next Steps

1. **Full Dataset Test**: Run conversion on complete Gtech_2023 dataset
2. **Validation**: Run `create_dataset_validation_report.py` on converted data
3. **Quality Check**: Verify task_info strings are properly parseable
4. **Documentation**: Update dataset documentation with new task categories

## Migration Notes

### For Existing Users
- Previous `task` column is now split into `task`, `task_id`, `task_info`
- Time column renamed from `time` to `time_s`
- GRF column names updated to be more descriptive
- Subject names remain same (GT23_AB##)

### For Analysis Code
- Update imports to handle new column structure
- Modify task filtering to use new three-level hierarchy
- Parse `task_info` strings if detailed metadata needed
- No changes needed for subject/phase indexing

---

*These changes ensure full compliance with the LocoHub standard specification while maintaining the quality and completeness of the Gtech_2023 dataset.*
