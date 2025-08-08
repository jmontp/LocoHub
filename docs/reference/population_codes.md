# Population Codes Reference

Standardized codes for identifying subject populations across all datasets.

## Quick Reference Table

| Code | Population | Description | Example |
|------|------------|-------------|---------|
| **AB** | Able-bodied | Healthy controls with no impairments | `UM21_AB01` |
| **TFA** | Transfemoral Amputee | Above-knee amputation | `PROS_TFA03` |
| **TTA** | Transtibial Amputee | Below-knee amputation | `PROS_TTA02` |
| **SCI** | Spinal Cord Injury | Complete or incomplete SCI | `REHA_SCI05` |
| **CVA** | Stroke | Cerebrovascular accident survivors | `GAIT_CVA12` |
| **PD** | Parkinson's Disease | Diagnosed Parkinson's patients | `NEURO_PD08` |
| **CP** | Cerebral Palsy | Individuals with cerebral palsy | `PEDS_CP04` |
| **MS** | Multiple Sclerosis | Diagnosed MS patients | `NEURO_MS11` |
| **OA** | Osteoarthritis | Significant joint osteoarthritis | `KNEE_OA09` |
| **ELD** | Elderly | Age > 65, otherwise healthy | `AGING_ELD07` |
| **PED** | Pediatric | Age < 18 | `CHILD_PED15` |
| **IMP** | Impaired (Other) | Other impairments not listed above | `STUDY_IMP06` |

## Detailed Descriptions

### AB - Able-bodied
- **Criteria**: No musculoskeletal or neurological impairments
- **Age Range**: Typically 18-65 (use ELD for >65, PED for <18)
- **Common Studies**: Control groups, normative data collection
- **Metadata Fields**: age, sex, height_m, weight_kg, dominant_side

### TFA - Transfemoral Amputee
- **Criteria**: Amputation above the knee joint
- **Subtypes**: Unilateral, bilateral
- **Common Studies**: Prosthetic control, gait adaptation
- **Metadata Fields**: amputation_side, years_since, prosthetic_type, K_level

### TTA - Transtibial Amputee
- **Criteria**: Amputation below the knee joint
- **Subtypes**: Unilateral, bilateral
- **Common Studies**: Prosthetic design, energy efficiency
- **Metadata Fields**: amputation_side, years_since, prosthetic_type, K_level

### SCI - Spinal Cord Injury
- **Criteria**: Complete or incomplete spinal cord injury
- **Classification**: ASIA scale (A-E), injury level (C1-S5)
- **Common Studies**: Exoskeleton control, rehabilitation progress
- **Metadata Fields**: injury_level, ASIA_grade, years_since, assistive_device

### CVA - Stroke
- **Criteria**: History of cerebrovascular accident
- **Subtypes**: Hemorrhagic, ischemic
- **Common Studies**: Gait rehabilitation, asymmetry analysis
- **Metadata Fields**: affected_side, months_since, FAC_score, assistive_device

### PD - Parkinson's Disease
- **Criteria**: Clinical diagnosis of Parkinson's disease
- **Staging**: Hoehn and Yahr scale (1-5)
- **Common Studies**: Freezing of gait, medication effects
- **Metadata Fields**: H_Y_stage, years_since, medication_state, UPDRS_score

### CP - Cerebral Palsy
- **Criteria**: Diagnosis of cerebral palsy
- **Classification**: GMFCS levels (I-V)
- **Common Studies**: Pediatric gait, intervention outcomes
- **Metadata Fields**: GMFCS_level, CP_type, affected_limbs, age

### MS - Multiple Sclerosis
- **Criteria**: Clinical diagnosis of multiple sclerosis
- **Types**: Relapsing-remitting, progressive
- **Common Studies**: Fatigue effects, disease progression
- **Metadata Fields**: MS_type, EDSS_score, years_since, mobility_aid

### OA - Osteoarthritis
- **Criteria**: Radiographic or clinical osteoarthritis
- **Common Joints**: Knee, hip, ankle
- **Common Studies**: Joint loading, pain adaptation
- **Metadata Fields**: affected_joints, KL_grade, pain_VAS, years_since

### ELD - Elderly
- **Criteria**: Age > 65 years, otherwise healthy
- **Exclusions**: Major impairments (use specific codes if present)
- **Common Studies**: Aging effects, fall risk assessment
- **Metadata Fields**: age, fall_history, activity_level, medications

### PED - Pediatric
- **Criteria**: Age < 18 years
- **Subgroups**: Toddler (1-3), Child (4-12), Adolescent (13-17)
- **Common Studies**: Development, growth effects
- **Metadata Fields**: age, height_m, weight_kg, tanner_stage

### IMP - Impaired (Other)
- **Use Cases**: Rare conditions, multiple impairments, unspecified
- **Documentation**: Requires detailed subject_metadata
- **Examples**: Muscular dystrophy, traumatic brain injury, rare syndromes
- **Metadata Fields**: diagnosis, functional_level, assistive_device

## Implementation Guidelines

### Choosing the Right Code

1. **Primary Impairment**: Use the most specific code for the primary condition
2. **Multiple Conditions**: Use the most functionally limiting condition
3. **Age Considerations**:
   - Healthy child → PED
   - Healthy elderly → ELD
   - Child with CP → CP (not PED)
   - Elderly with stroke → CVA (not ELD)

### Creating Subject IDs

```python
# Format: DATASET_POPULATION+NUMBER
subject_id = f"{dataset_code}_{population_code}{subject_num:02d}"

# Examples:
"UM21_AB01"     # UMich 2021, able-bodied subject 1
"PROS_TFA03"    # Prosthetics study, transfemoral amputee 3
"AGING_ELD15"   # Aging study, elderly subject 15
```

### Subject Metadata Format

Store additional demographic and clinical information in the `subject_metadata` column:

```python
# Basic demographics (all populations)
metadata = "age:45,sex:F,height_m:1.68,weight_kg:65"

# Population-specific additions
# Amputee
metadata += ",amputation_side:right,years_since:3,K_level:3"

# Stroke
metadata += ",affected_side:left,months_since:18,FAC_score:5"

# Parkinson's
metadata += ",H_Y_stage:2,medication_state:ON,UPDRS_motor:24"
```

## Standard Metadata Fields

### Universal Fields
- `age`: Age in years
- `sex`: M/F/O (Male/Female/Other)
- `height_m`: Height in meters
- `weight_kg`: Weight in kilograms
- `dominant_side`: left/right

### Clinical Assessment Scores
- `K_level`: Amputee functional level (0-4)
- `ASIA_grade`: SCI completeness (A-E)
- `FAC_score`: Functional Ambulation Category (0-5)
- `H_Y_stage`: Hoehn and Yahr stage (1-5)
- `GMFCS_level`: Gross Motor Function Classification (I-V)
- `EDSS_score`: Expanded Disability Status Scale (0-10)
- `KL_grade`: Kellgren-Lawrence OA grade (0-4)

### Temporal Information
- `years_since`: Years since diagnosis/injury
- `months_since`: Months since event (for recent)
- `session_date`: Date of data collection

## Best Practices

1. **Consistency**: Use the same code across all sessions for a subject
2. **Documentation**: Always include basic demographics in metadata
3. **Privacy**: Use coded IDs, never include names or identifiers
4. **Validation**: Verify population code matches clinical documentation
5. **Updates**: If diagnosis changes, create new subject ID with appropriate code

## Examples from Existing Datasets

### University of Michigan 2021
- Original: `AB01`, `AB02`, ..., `AB10`
- Converted: `UM21_AB01`, `UM21_AB02`, ..., `UM21_AB10`
- All able-bodied subjects aged 20-60

### Georgia Tech 2023
- Original: `AB01`, `AB03`, ..., `AB13`
- Converted: `GT23_AB01`, `GT23_AB03`, ..., `GT23_AB13`
- All able-bodied subjects aged 18-35

### Future Prosthetics Study
- Expected: `PROS_TFA01`, `PROS_TTA01`, `PROS_AB01` (control)
- Mixed population with controls

## Task Naming for Impaired Populations

### Overview

When working with impaired populations, task naming can follow two approaches:

1. **Standard task names** - When the population code in the subject ID provides sufficient context
2. **Population-specific task names** - When explicit population identification in the task name is beneficial

### Task Naming Guidelines

#### Standard Approach (Recommended for most cases)
```python
# Population is identified through subject ID
{"subject": "STUDY_CVA01", "task": "level_walking", ...}  # CVA = stroke
{"subject": "STUDY_TFA02", "task": "incline_walking", ...}  # TFA = transfemoral amputee
```

#### Population-Specific Approach (When needed)
```python
# Population is explicit in both subject ID and task name
{"subject": "STUDY_CVA01", "task": "level_walking_stroke", ...}
{"subject": "STUDY_TFA02", "task": "incline_walking_amputee", ...}
```

### When to Use Population-Specific Task Names

**Use population-specific names when:**
- Different validation ranges are needed per population
- Research focuses on within-population variations
- Clinical protocols require explicit task differentiation
- Datasets combine multiple impaired populations

**Use standard names when:**
- Subject ID provides sufficient population context
- Analysis compares with able-bodied controls
- Population follows typical biomechanical patterns
- Simplicity and consistency are priorities

### Population Suffix Mapping

| Population Code | Task Suffix Options | Example |
|----------------|-------------------|---------|
| CVA | `_stroke` or `_cva` | `level_walking_stroke` |
| TFA | `_amputee` or `_tfa` | `level_walking_tfa` |
| TTA | `_amputee` or `_tta` | `level_walking_tta` |
| SCI | `_sci` | `level_walking_sci` |
| PD | `_pd` or `_parkinsons` | `level_walking_pd` |
| CP | `_cp` | `level_walking_cp` |
| MS | `_ms` | `level_walking_ms` |
| OA | `_oa` | `level_walking_oa` |

### Filtering Strategies

```python
from user_libs.python.locomotion_data import LocomotionData

data = LocomotionData('dataset.parquet')

# Strategy 1: Filter by subject population code
stroke_data = data.df[data.df['subject'].str.contains('_CVA')]

# Strategy 2: Filter by task name (if using population-specific naming)
stroke_tasks = data.df[data.df['task'].str.contains('_stroke')]

# Strategy 3: Combined filtering
stroke_walking = data.df[
    (data.df['subject'].str.contains('_CVA')) & 
    (data.df['task'].str.contains('walking'))
]
```

### Best Practices

1. **Be consistent** within a dataset - choose one approach and stick to it
2. **Document your choice** in dataset documentation
3. **Consider your audience** - clinical researchers may prefer explicit task names
4. **Think about scalability** - will you add more populations later?
5. **Preserve information** - ensure population context is never lost

---

*This reference ensures consistent population identification across all datasets in the locomotion data standard.*