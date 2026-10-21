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
| OpenSim Model | Modified Rajagopal model with single DoF knee (**NOT publicly available**) |

## Online Resources

### Figshare Repository

**URL:** https://springernature.figshare.com/articles/dataset/27677016

| File | Size | Description |
|------|------|-------------|
| `Gait120_001_to_010.zip` ... `Gait120_111_to_120.zip` | ~1.3 GB each | Subject data (12 files) |
| `Subject_Demographics.xlsx` | 14 KB | Basic demographics |
| `Anthropometric_Data_Participants.xlsx` | 19 KB | Height, mass, leg length, joint widths |
| `Matlab_Codes_for_Processing.zip` | 11 KB | EMG processing scripts only |

### Anthropometric Data

Direct download URL: https://ndownloader.figshare.com/files/54257534

Contains per-subject measurements:
- Height (mm), Body mass (kg), Leg length (mm)
- Knee width, Ankle width, Shoulder offset
- Elbow width, Wrist width, Hand thickness

The `scale_model.py` script uses this data automatically.

### Data NOT Provided

The dataset does **NOT** include:
- OpenSim model files (.osim)
- Scaling setup files
- The original modified Rajagopal model used for IK

This is why inverse dynamics cannot be accurately computed using the pre-computed IK files.

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
│   │   ├── Static/TRC/    # Static trial for scaling
│   │   ├── LevelWalking/
│   │   │   ├── TRC/       # Marker trajectory data
│   │   │   └── MOT/       # Force plate data
│   │   └── ...
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

### Default Mode (Pre-computed IK)

Uses the pre-computed .mot files from JointAngle/:

```bash
python contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py \
    --input /mnt/s/locomotion_data/Gait120
```

### Full Pipeline Mode (Recommended for ID)

Runs the complete OpenSim pipeline from TRC files: Scale → IK → ID

```bash
python contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py \
    --input /mnt/s/locomotion_data/Gait120 \
    --run-ik
```

This mode:
- Scales the Rajagopal model for each subject using static trial + anthropometric data
- Runs inverse kinematics from TRC marker files
- Runs inverse dynamics using the same scaled model
- Produces internally consistent kinematics and kinetics

### Command Line Options

| Option | Description |
|--------|-------------|
| `--subjects S001 S002` | Process specific subjects only |
| `--test` | Test mode: process only first subject and first task |
| `--explore` | Explore data structure without converting |
| `--output-dir PATH` | Change output directory |
| `--run-ik` | Run full pipeline (Scale → IK → ID) instead of pre-computed IK |
| `--enable-id` | Enable ID with pre-computed IK (experimental, results inaccurate) |
| `--pipeline-cache PATH` | Directory for cached scaled models and IK results |

## Processing Modes

### Mode 1: Pre-computed IK (Default)

**Usage:** `python convert_gait120_to_parquet.py`

- Uses .mot files from `JointAngle/` folder
- Fast (no OpenSim computation needed)
- **Cannot run accurate ID** because the original model is not available
- Kinematics are from the Gait120 authors' unpublished model

### Mode 2: Full Pipeline (`--run-ik`)

**Usage:** `python convert_gait120_to_parquet.py --run-ik`

- Uses TRC marker files from `MotionCapture/` folder
- Runs OpenSim ScaleTool with static trial + anthropometric data
- Runs OpenSim IKTool with our Rajagopal model
- Runs OpenSim IDTool with the same scaled model
- **Produces accurate ID results** (same model for IK and ID)
- Slower but recommended when moments are needed

**Data flow:**
```
Static TRC → ScaleTool → Scaled Model
                              ↓
Stride TRC → IKTool → Joint Angles (IK output)
                              ↓
GRF MOT → IDTool → Joint Moments (ID output)
                              ↓
                    Phase-Normalized Parquet
```

## OpenSim Pipeline Architecture

The full pipeline is implemented in `contributor_tools/common/`:

| Module | Purpose |
|--------|---------|
| `opensim_scaling.py` | ScaleTool wrapper for model scaling |
| `opensim_ik.py` | IKTool wrapper for inverse kinematics |
| `opensim_inverse_dynamics.py` | IDTool wrapper for inverse dynamics |
| `opensim_pipeline.py` | Orchestrates Scale → IK → ID with caching |

### Marker Mapping

Gait120 uses Plug-in Gait markers; Rajagopal uses anatomical landmarks.
Mapping is defined in `marker_mapping.py`:

| Gait120 | Rajagopal | Description |
|---------|-----------|-------------|
| LASI, RASI | LASI, RASI | Pelvis (exact match) |
| LPSI, RPSI | LPSI, RPSI | Pelvis (exact match) |
| RKNE, LKNE | RLFC, LLFC | Lateral knee |
| RANK, LANK | RLMAL, LLMAL | Lateral ankle |
| RHEE, LHEE | RCAL, LCAL | Heel/calcaneus |
| RTOE, LTOE | RTOE, LTOE | Toe (exact match) |
| RTHI, LTHI | RTH2, LTH2 | Thigh cluster |
| RTIB, LTIB | RTB2, LTB2 | Shank cluster |

### GRF Data Availability

| Task | TRC | GRF | Can Run IK | Can Run ID |
|------|-----|-----|------------|------------|
| Level walking | All | S011-S120 | Yes | Yes (S011+) |
| Stair ascent | All | None | Yes | No |
| Stair descent | All | None | Yes | No |
| Slope ascent | All | None | Yes | No |
| Slope descent | All | None | Yes | No |
| Sit-to-stand | All | All | Yes | Yes |
| Stand-to-sit | All | All | Yes | Yes |

## Setup

### 1. Install OpenSim Python API

```bash
conda install -c opensim-org opensim
```

### 2. Download and Prepare the Model

```bash
python contributor_tools/conversion_scripts/Gait120/setup_opensim_model.py
```

This downloads the Rajagopal 2015 model and modifies it to match Gait120's single-DOF knee configuration.

### Files Created

| File | Description |
|------|-------------|
| `rajagopal_gait120.osim` | Modified Rajagopal model with locked secondary knee DOFs |
| `marker_mapping.py` | Gait120 ↔ Rajagopal marker correspondence |
| `scale_model.py` | Script to scale model using official anthropometric data |
| `scaled_models/` | Directory for subject-specific scaled models (when using `--run-ik`) |

## Sign Conventions

### Kinematics

**Source data (OpenSim modified Rajagopal model):**
- Hip: flexion +, adduction +, internal rotation +
- Knee: **EXTENSION +** (different from our standard!)
- Ankle: dorsiflexion +

**Conversion applies:**
- Knee angle is **NEGATED** to convert to flexion-positive standard
- All other angles preserved as-is
- Degrees converted to radians

### Moments

| Joint | OpenSim Output | LocoHub Standard | Action |
|-------|----------------|------------------|--------|
| Hip flexion | Flexion + | Flexion + | None |
| Knee | Extension + | Flexion + | **Negate** |
| Ankle | Dorsiflexion + | Dorsiflexion + | None |

## Data Notes

### Bilateral Data

Full-body motion capture provides **bilateral kinematic data**:
- Both left and right leg joint angles are available
- EMG is right leg only (not used in conversion)
- Contralateral data is 50% phase-shifted for gait tasks

### Data Availability Limitations

1. **Force plate data:** Only available for level walking (S011+), sit-to-stand, and stand-to-sit tasks
2. **First 10 subjects (S001-S010):** No force plate data due to coordinate system alignment issue
3. **Static trials:** Available for all subjects in `MotionCapture/Static/TRC/`

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

**Ground Reaction Forces (when available):**
- grf_vertical_{ipsi,contra}_N, grf_vertical_{ipsi,contra}_BW
- grf_anterior_{ipsi,contra}_N, grf_anterior_{ipsi,contra}_BW
- grf_lateral_{ipsi,contra}_N, grf_lateral_{ipsi,contra}_BW
- cop_anterior_{ipsi,contra}_m, cop_lateral_{ipsi,contra}_m

**Joint Moments (Nm/kg, when using `--run-ik` with GRF available):**
- hip_flexion_moment_{ipsi,contra}_Nm_kg
- knee_flexion_moment_{ipsi,contra}_Nm_kg
- ankle_dorsiflexion_moment_{ipsi,contra}_Nm_kg

### Not Included

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

### Moment Validation (Compare to Literature)

When using `--run-ik`, compare ID output to Winter (2009) normative data:
- Hip extension moment peak: ~0.5-1.0 Nm/kg at early stance
- Knee extension moment peak: ~0.3-0.6 Nm/kg at loading response
- Ankle plantarflexion moment peak: ~1.2-1.6 Nm/kg at push-off

Joint moments during swing should be near zero (no ground contact).

## Expected Output

- **Subjects:** 120
- **Strides:** ~13,000-14,000 (both legs processed for each step file)
- **Tasks:** 7
- **Rows:** ~2M+ (strides × 150 points)

## Performance Notes

When using `--run-ik`:
- **Model scaling:** ~120 subjects × 1 model = 120 cached models
- **IK:** ~13,000 strides (can be cached for subsequent runs)
- **ID:** ~8,000 strides with GRF

The pipeline caches scaled models and IK results to avoid redundant computation.

## References

- Boo, J., Seo, D., Kim, M. & Koo, S. Comprehensive human locomotion and electromyography dataset: Gait120. Sci Data (2025). https://doi.org/10.1038/s41597-025-05391-0
