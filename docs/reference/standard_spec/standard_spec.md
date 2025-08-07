# Locomotion Data Standard - Technical Specification

Core technical specification for parquet file structure and data organization.

**For comprehensive reference including biomechanics, see:** [Biomechanical Standard](../biomechanical_standard.md) | [Quick Reference](../quick_reference.md)

## Data Formats

---

### Time-Indexed Data
*Original sampling frequency preserved*

- **Format**: `dataset_time.parquet`
- **Structure**: Continuous time series data
- **Use case**: Temporal analysis, event detection

---

### Phase-Indexed Data  
*Normalized to 150 points per gait cycle*

- **Format**: `dataset_phase.parquet` 
- **Structure**: 150 points per cycle (0-100%)
- **Use case**: Cross-subject comparison, averaging

---

## Variable Naming

See [Biomechanical Standard - Variable Naming System](../biomechanical_standard.md#variable-naming-system) for complete variable reference.

## Subject Naming Convention

All subjects must follow a strict naming convention to ensure global uniqueness and clear population identification.

### Format
`<DATASET_CODE>_<POPULATION_CODE><SUBJECT_NUMBER>`

- **DATASET_CODE**: 2-4 character dataset identifier (e.g., UM21, GT23, PROS)
- **POPULATION_CODE**: Standardized population identifier (see table below)
- **SUBJECT_NUMBER**: 2-3 digit number (01, 02, ..., 999)

### Population Codes

| Code | Population | Description |
|------|------------|-------------|
| AB | Able-bodied | Healthy controls with no impairments |
| TFA | Transfemoral Amputee | Above-knee amputation |
| TTA | Transtibial Amputee | Below-knee amputation |
| SCI | Spinal Cord Injury | Complete or incomplete SCI |
| CVA | Stroke | Cerebrovascular accident survivors |
| PD | Parkinson's Disease | Diagnosed Parkinson's patients |
| CP | Cerebral Palsy | Individuals with cerebral palsy |
| MS | Multiple Sclerosis | Diagnosed MS patients |
| OA | Osteoarthritis | Significant joint osteoarthritis |
| ELD | Elderly | Age > 65, otherwise healthy |
| PED | Pediatric | Age < 18 |
| IMP | Impaired (Other) | Other impairments not listed above |

### Examples
- `UM21_AB01` - University of Michigan 2021, able-bodied subject 01
- `GT23_AB05` - Georgia Tech 2023, able-bodied subject 05
- `PROS_TFA03` - Prosthetics study, transfemoral amputee 03
- `GAIT_CVA12` - Gait study, stroke patient 12
- `AGING_ELD07` - Aging study, elderly subject 07

### Why This Matters

1. **Dataset Concatenation**: Prevents ID collisions when combining datasets
2. **Population Analysis**: Enables filtering by population type across studies
3. **Clinical Context**: Preserves important population information
4. **Research Integrity**: Maintains clear data provenance

## Required Columns

**Metadata** (required for all datasets):
- `subject` - Subject identifier following naming convention above
- `subject_metadata` - (Optional) Demographics in key:value format (e.g., "age:45,sex:F,height_m:1.68")
- `task` - Biomechanical category (e.g., level_walking, incline_walking)
- `task_id` - Task variant with primary parameter (e.g., incline_10deg, stair_ascent)
- `task_info` - Metadata in key:value format (e.g., "incline_deg:10,speed_m_s:1.2")
- `step` - Step/cycle number

**Phase Data** (required for phase-indexed):
- `phase_ipsi` - Gait cycle phase (0-100%) aligned to ipsilateral heel strike

**Time Data** (required for time-indexed):
- `time_s` - Time in seconds

## Standard Variables

See [Biomechanical Standard - Comprehensive Variable Reference](../biomechanical_standard.md#variable-naming-system) for complete list of standardized variables.

## Task Definitions

See [Biomechanical Standard - Task Classification System](../biomechanical_standard.md#task-classification-system) for complete task hierarchy and metadata specifications.

## Sign Conventions

See [Biomechanical Standard - Coordinate System & Conventions](../biomechanical_standard.md#coordinate-system--conventions) for detailed sign conventions and coordinate system definitions.

## Phase Calculation

**Phase-indexed data normalization**:
1. Detect gait events (heel strike to heel strike)
2. Normalize each cycle to exactly 150 points
3. Calculate phase percentage: `phase_percent = (point_index / 149) * 100`

**Phase Interpretation**:
- `0%` - Heel strike (start of gait cycle)
- `~60%` - Opposite heel strike (typical)
- `100%` - Next heel strike (end of cycle)

## Missing Data

**Handling**:
- Missing values: `NaN` (Not a Number)
- Invalid measurements: `NaN`
- No synthetic data generation

**Quality Flags** (optional):
- `is_reconstructed_<side>` - Boolean flag for filled data
- Use `true` for interpolated/reconstructed values

## File Examples

**Time-indexed**:
```
subject,subject_metadata,task,task_id,task_info,step,time_s,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
UM21_AB01,"age:25,sex:M,height_m:1.75,weight_kg:70",level_walking,level,"speed_m_s:1.2,treadmill:true",0,0.00,0.123,-0.456
UM21_AB01,"age:25,sex:M,height_m:1.75,weight_kg:70",level_walking,level,"speed_m_s:1.2,treadmill:true",0,0.01,0.126,-0.445
UM21_AB01,"age:25,sex:M,height_m:1.75,weight_kg:70",level_walking,level,"speed_m_s:1.2,treadmill:true",1,1.20,0.120,-0.460
```

**Phase-indexed**:
```
subject,subject_metadata,task,task_id,task_info,step,phase_ipsi,knee_flexion_angle_ipsi_rad,hip_moment_contra_Nm
GT23_AB03,"age:28,sex:F,height_m:1.68,weight_kg:65",incline_walking,incline_10deg,"incline_deg:10,speed_m_s:1.0,treadmill:true",0,0.0,0.123,-0.456
GT23_AB03,"age:28,sex:F,height_m:1.68,weight_kg:65",incline_walking,incline_10deg,"incline_deg:10,speed_m_s:1.0,treadmill:true",0,0.7,0.126,-0.445
GT23_AB03,"age:28,sex:F,height_m:1.68,weight_kg:65",incline_walking,incline_10deg,"incline_deg:10,speed_m_s:1.0,treadmill:true",0,100.0,0.120,-0.460
GT23_AB03,"age:28,sex:F,height_m:1.68,weight_kg:65",incline_walking,incline_10deg,"incline_deg:10,speed_m_s:1.0,treadmill:true",1,0.0,0.125,-0.458
```

## Validation Requirements

**Phase Data Validation**:
- Exactly 150 points per cycle
- Phase values: 0.0 to 100.0
- No gaps in phase progression

**Variable Validation**:
- Joint angles: -π to π radians  
- Realistic biomechanical ranges
- Consistent units across datasets

---

*For detailed implementation examples, see the [Python Tutorial](../tutorials/python/getting_started_python.md) and [MATLAB Tutorial](../tutorials/matlab/getting_started_matlab.md).*