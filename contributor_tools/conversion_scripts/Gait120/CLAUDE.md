# Gait120 Conversion

## Dataset Overview

**Comprehensive Human Locomotion and Electromyography Dataset: Gait120**

- **Paper:** [Scientific Data (Nature)](https://www.nature.com/articles/s41597-025-05391-0)
- **DOI:** [10.6084/m9.figshare.27677016](https://doi.org/10.6084/m9.figshare.27677016)
- **Authors:** Junyo Boo, Dongwook Seo, Minseung Kim, Seungbum Koo

## Dataset Details

| Property | Value |
|----------|-------|
| Subjects | 120 healthy males (ages 20-59) |
| Tasks | 7 (level walking, stair ascent/descent, slope ascent/descent, sit-to-stand, stand-to-sit) |
| Total Cycles | ~6,882 movement cycles |
| Format | OpenSim .mot files (joint angles in degrees) |
| Total Size | ~15 GB (12 zip files, ~1.3 GB each) |
| OpenSim Model | Modified Rajagopal model with single DoF knee |

## Data Location

Source data downloaded to:
```
/mnt/s/locomotion_data/Gait120/
```

Output:
```
converted_datasets/gait120_phase.parquet
```

## Folder Structure

```
/mnt/s/locomotion_data/Gait120/
├── S001/
│   ├── JointAngle/
│   │   ├── LevelWalking/
│   │   │   ├── Trial01/
│   │   │   │   ├── Step01.mot
│   │   │   │   ├── Step02.mot
│   │   │   │   └── ...
│   │   ├── StairAscent/
│   │   ├── StairDescent/
│   │   ├── SlopeAscent/
│   │   ├── SlopeDescent/
│   │   ├── SitToStand/
│   │   └── StandToSit/
│   ├── MotionCapture/
│   │   ├── TRC/  # Marker trajectory data
│   │   └── MOT/  # Force plate data (limited availability)
│   └── EMG/      # Not used in conversion
├── S002/
└── ... (S001-S120)
```

## Running the Download

```bash
bash contributor_tools/conversion_scripts/Gait120/download_gait120.sh
```

Or specify a custom output directory:
```bash
bash contributor_tools/conversion_scripts/Gait120/download_gait120.sh /path/to/output
```

## Running the Conversion

```bash
python contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py \
    --input /mnt/s/locomotion_data/Gait120
```

Options:
- `--subjects S001 S002` - Process specific subjects only
- `--test` - Test mode: process only first subject and first task
- `--explore` - Explore data structure without converting
- `--output-dir PATH` - Change output directory

## Data Notes

### Sign Conventions

**Source data (OpenSim modified Rajagopal model):**
- Hip: flexion +, adduction +, internal rotation +
- Knee: **EXTENSION +** (different from our standard!)
- Ankle: dorsiflexion +

**Conversion applies:**
- Knee angle is **NEGATED** to convert to flexion-positive standard
- All other angles preserved as-is
- Degrees converted to radians

### Bilateral Data

Full-body motion capture provides **bilateral kinematic data**:
- Both left and right leg joint angles are available
- EMG is right leg only (not used in conversion)
- Contralateral data is 50% phase-shifted for gait tasks

### Data Availability Limitations

1. **Force plate data:** Only available for level walking, sit-to-stand, and stand-to-sit tasks
2. **First 10 subjects (S001-S010):** No force plate data due to coordinate system alignment issue
3. **GRF/moments:** Not included in this conversion (kinematic-only dataset)

### Task Mapping

| Source Folder | Standard Task | Task ID |
|---------------|---------------|---------|
| LevelWalking | level_walking | level_walking |
| StairAscent | stair_ascent | stair_ascent |
| StairDescent | stair_descent | stair_descent |
| SlopeAscent | incline_walking | slope_ascent |
| SlopeDescent | decline_walking | slope_descent |
| SitToStand | sit_to_stand | sit_to_stand |
| StandToSit | stand_to_sit | stand_to_sit |

### Subject Naming

Subject IDs in output: `G120_S001`, `G120_S002`, ... `G120_S120`

### Output Columns

**Metadata:**
- subject, subject_metadata, task, task_id, task_info, step, phase_ipsi, phase_ipsi_dot

**Joint Angles (radians):**
- hip_flexion_angle_{ipsi,contra}_rad
- knee_flexion_angle_{ipsi,contra}_rad (note: converted to flexion+)
- ankle_dorsiflexion_angle_{ipsi,contra}_rad

**Joint Velocities (rad/s):**
- Computed via gradient from angles

**Joint Accelerations (rad/s^2):**
- Computed via gradient from velocities

**Segment Angles (radians):**
- pelvis_sagittal_angle_rad
- thigh_sagittal_angle_{ipsi,contra}_rad
- shank_sagittal_angle_{ipsi,contra}_rad
- foot_sagittal_angle_{ipsi,contra}_rad

**Segment Velocities (rad/s):**
- Computed via gradient from segment angles

### Not Included

- GRF data (not available for most tasks/subjects)
- Joint moments (not computed without GRF)
- COP data (not available)
- EMG data (separate .mat files, not part of standard format)

## Validation

After conversion:

```bash
# Quick validation
python contributor_tools/quick_validation_check.py converted_datasets/gait120_phase.parquet

# With plots
python contributor_tools/quick_validation_check.py converted_datasets/gait120_phase.parquet \
    --plot --task level_walking

# Diagnose failures
python contributor_tools/diagnose_validation_failures.py converted_datasets/gait120_phase.parquet --top 10
```

## Expected Output

- **Subjects:** 120
- **Strides:** ~13,000-14,000 (both legs processed for each step file)
- **Tasks:** 7
- **Rows:** ~2M+ (strides × 150 points)

## References

- Boo, J., Seo, D., Kim, M. & Koo, S. Comprehensive human locomotion and electromyography dataset: Gait120. Sci Data (2025). https://doi.org/10.1038/s41597-025-05391-0
