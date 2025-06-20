# Dataset Overview

*Comprehensive reference for all standardized biomechanical datasets*

## Available Datasets

### Research-Grade Collections

| Dataset | Status | Tasks | Subjects | Cycles | Download |
|---------|--------|-------|----------|---------|----------|
| **Georgia Tech 2023** | :material-check-circle:{ .success } **Validated** | Walking, stairs, inclines, running | 13 | 500+ | [:material-download: Get Data](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| **University of Michigan 2021** | :material-check-circle:{ .success } **Validated** | Level, incline, decline walking | 12 | 600+ | [:material-download: Get Data](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| **AddBiomechanics** | :material-progress-clock:{ .warning } **In Progress** | Walking, running, jumping, stairs | 50+ | 2000+ | Coming Soon |

## Dataset Details

### Georgia Tech 2023 Collection

**Research Context**
- Multi-task locomotion study with healthy adults
- Focus on environmental adaptation and gait variability
- Published in *Journal of Biomechanics* (2023)

**Data Characteristics**
- **Subjects**: 13 healthy adults (7 male, 6 female)
- **Age Range**: 22-45 years
- **Tasks**: Level walking, incline walking (±10°), stair ascent/descent, running
- **Collection Protocol**: 5-10 trials per task per subject
- **Motion Capture**: 12-camera Vicon system at 100 Hz
- **Force Plates**: 3 AMTI force plates at 1000 Hz

**Available Variables**
```
Kinematics (rad):
├── hip_flexion_angle_ipsi_rad
├── hip_adduction_angle_ipsi_rad  
├── hip_rotation_angle_ipsi_rad
├── knee_flexion_angle_ipsi_rad
├── ankle_flexion_angle_ipsi_rad
└── [corresponding contralateral angles]

Kinetics (N⋅m, N):
├── hip_moment_ipsi_Nm
├── knee_moment_ipsi_Nm
├── ankle_moment_ipsi_Nm
├── ground_force_vertical_ipsi_N
├── ground_force_anterior_ipsi_N
└── ground_force_medial_ipsi_N
```

**Quality Validation**
- 100% of cycles pass physiological range checks
- Gait pattern consistency validated across subjects
- Cross-task biomechanical relationships verified
- No missing data or interpolated values

[**:material-information: Detailed Documentation**](dataset_gtech_2023/){ .md-button }

### University of Michigan 2021 Collection

**Research Context**
- Incline walking adaptation study
- Investigation of slope-dependent gait modifications
- Published in *Gait & Posture* (2021)

**Data Characteristics**
- **Subjects**: 12 healthy adults (6 male, 6 female)
- **Age Range**: 20-30 years  
- **Tasks**: Level walking, incline walking (+15°), decline walking (-15°)
- **Collection Protocol**: 8-12 trials per condition per subject
- **Motion Capture**: 8-camera OptiTrack system at 120 Hz
- **Force Plates**: 2 Bertec force plates at 1200 Hz

**Available Variables**
```
Kinematics (rad):
├── hip_flexion_angle_ipsi_rad
├── knee_flexion_angle_ipsi_rad
├── ankle_flexion_angle_ipsi_rad
└── [bilateral measurements]

Kinetics (N⋅m, N):
├── hip_moment_ipsi_Nm
├── knee_moment_ipsi_Nm  
├── ankle_moment_ipsi_Nm
├── ground_force_vertical_ipsi_N
└── [corresponding bilateral forces]

Spatiotemporal:
├── step_length_m
├── step_width_m
├── cadence_steps_per_min
└── walking_speed_m_per_s
```

**Quality Validation**
- All joint angles within established physiological ranges
- Slope-specific adaptations consistent with literature
- Force plate and marker data synchronized within 1ms
- Comprehensive outlier detection and removal

[**:material-information: Detailed Documentation**](dataset_umich_2021/){ .md-button }

### AddBiomechanics Collection (In Progress)

**Research Context**
- Large-scale open biomechanics database
- Multi-lab collaboration for movement diversity
- Ongoing data validation and standardization

**Planned Data Characteristics**
- **Subjects**: 50+ adults and children
- **Age Range**: 8-80 years
- **Tasks**: Walking, running, jumping, stairs, sports movements
- **Labs**: 10+ research institutions worldwide
- **Motion Capture**: Various systems (Vicon, OptiTrack, Qualisys)

**Expected Variables**
- Full-body kinematics (25+ degrees of freedom)
- Lower limb kinetics (hip, knee, ankle moments)
- Ground reaction forces (3D components)
- Electromyography (8+ muscles)
- Anthropometric measurements

[**:material-information: Detailed Documentation**](dataset_addbiomechanics/){ .md-button }

## Data Format Specifications

### Standardized Structure
All datasets follow identical structure for cross-study compatibility:

```python
# Loading any dataset
from locomotion_analysis import LocomotionData
data = LocomotionData.from_parquet('any_dataset_phase.parquet')

# Consistent interface across all datasets  
knee_angles = data.get_variable_3d('knee_flexion_angle_ipsi_rad')
walking_data = data.filter_task('level_walking')
average_knee = walking_data.get_average_trajectory('knee_flexion_angle_ipsi_rad')
```

### Phase vs Time Indexing

**Phase-Indexed Data** (Recommended)
- Exactly 150 points per gait cycle (0-100% gait cycle)
- Enables direct comparison across subjects and studies
- Optimal for statistical analysis and averaging
- File naming: `dataset_phase.parquet`

**Time-Indexed Data** (Original Resolution)
- Original sampling frequency preserved
- Variable cycle lengths and timing
- Maintains temporal dynamics and frequency content
- File naming: `dataset_time.parquet`

### Variable Naming Convention

**Standardized Names**
```
Joint Angles (rad):
  {joint}_flexion_angle_{side}_rad
  {joint}_adduction_angle_{side}_rad  
  {joint}_rotation_angle_{side}_rad

Joint Moments (N⋅m):
  {joint}_moment_{side}_Nm
  
Ground Forces (N):
  ground_force_{direction}_{side}_N
  
Where:
  {joint} = hip, knee, ankle
  {side} = ipsi, contra (ipsilateral, contralateral)
  {direction} = vertical, anterior, medial
```

**Variable Mapping**
Each dataset includes mapping from original to standardized names:
```python
# Access original variable names
data.get_original_variable_names()

# Access variable mapping
data.get_variable_mapping()
```

## Quality Assurance

### Validation Pipeline
Every dataset undergoes comprehensive validation:

1. **Range Validation**: Joint angles within physiological limits
2. **Pattern Validation**: Gait cycle shapes match expected patterns  
3. **Consistency Validation**: Cross-variable relationships verified
4. **Completeness Validation**: No missing data or gaps
5. **Statistical Validation**: Distributions compared to literature norms

### Validation Reports
Each dataset includes detailed quality reports:
- Visual validation plots for all variables
- Statistical summaries and outlier detection
- Cross-dataset comparison metrics
- Known limitations and usage notes

### Quality Metrics
```python
# Access quality information
data.get_quality_summary()
# Returns: validation status, outlier counts, data completeness

data.get_validation_report()
# Returns: detailed validation results by variable and task
```

## Usage Guidelines

### Choosing the Right Dataset

**For Cross-Study Comparisons**
Use multiple datasets with identical variable names:
```python
gtech_data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
umich_data = LocomotionData.from_parquet('umich_2021_phase.parquet')

# Direct comparison possible
gtech_walking = gtech_data.filter_task('level_walking')
umich_walking = umich_data.filter_task('level_walking')
```

**For Task-Specific Analysis**
- **Walking Studies**: All datasets include level walking
- **Incline Studies**: Georgia Tech 2023, University of Michigan 2021
- **Stair Studies**: Georgia Tech 2023
- **Running Studies**: Georgia Tech 2023, AddBiomechanics (coming)

**For Population Studies**
- **Healthy Adults**: All current datasets
- **Age Diversity**: AddBiomechanics (when available)
- **Pathological Populations**: Future dataset additions planned

### Citation Requirements

**Dataset Citations**
- Georgia Tech 2023: *Citation information provided with download*
- University of Michigan 2021: *Citation information provided with download*
- Platform Citation: *Locomotion Data Standardization Platform (2023)*

**Acknowledgments**
Include acknowledgment of data contributors and standardization effort in publications using these datasets.

## Contributing New Datasets

Interested in contributing your lab's data to the standardized collection?

[**:material-upload: Contribute Your Data**](../../lab_directors/contributing_data/){ .md-button .md-button--primary }

---

*All datasets undergo rigorous quality validation to ensure reliability for research applications.*