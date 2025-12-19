# GaTech 2024 TaskAgnostic Dataset Conversion

Converts the "Task-agnostic exoskeleton control via biological joint moment estimation" dataset
to the LocoHub standardized phase-normalized parquet format.

## Source Dataset

- **Paper**: [Nature 2024](https://www.nature.com/articles/s41586-024-08157-7)
- **Repository**: [Georgia Tech Digital Repository](https://repository.gatech.edu/handle/1853/75759)
- **Lab**: [EPIC Lab at Georgia Tech](https://www.epic.gatech.edu/)

## Dataset Description

- **Subjects**: 25 total (Phase1And2: BT01-BT17 training, Phase3: 10 validation)
- **Activities**: 28 different tasks per subject
- **Sampling Rate**: 200 Hz
- **Data Types**: Joint angles, moments, velocities, power, GRF, IMU, exoskeleton sensors

## Activities Included

| Category | Activities |
|----------|------------|
| Level Walking | 0.6-2.5 m/s, shuffle, skip |
| Incline/Decline | 5°, 10° slopes |
| Stairs | Ascent, descent |
| Backward Walking | 0.6-1.0 m/s |
| Sit-to-Stand | Short/tall chair, with/without armrests |
| Squats | Bodyweight, weighted (25 lbs) |
| Jumping | Vertical, lateral, rotational |
| Lunges | Forward/backward, lateral |
| Cutting | Left/right, slow/fast |
| Other | Meander, obstacle walk, curb, step-ups |

## Usage

```bash
# Convert all subjects
python convert_gtech_2024_phase_to_parquet.py -i Parsed -o gtech_2024_phase.parquet

# Convert specific subjects
python convert_gtech_2024_phase_to_parquet.py -i Parsed -s BT24 BT01

# Test mode (first subject only)
python convert_gtech_2024_phase_to_parquet.py -i Parsed --test
```

## Output Format

Phase-normalized to 150 points per gait cycle with columns:

### Metadata
- `subject`: GT24_BT## format
- `subject_metadata`: weight_kg
- `task`: Standard task name (level_walking, stair_ascent, etc.)
- `task_id`: Specific task identifier
- `task_info`: Additional metadata (speed, exo_powered, etc.)
- `step`: Stride number

### Phase
- `phase_ipsi`: 0-100% gait cycle
- `phase_ipsi_dot`: Phase rate (%/s)

### Kinematics (radians)
- `hip_flexion_angle_{ipsi,contra}_rad`
- `knee_flexion_angle_{ipsi,contra}_rad`
- `ankle_dorsiflexion_angle_{ipsi,contra}_rad`
- Corresponding velocities (_rad_s) and accelerations (_rad_s2)

### Kinetics
- `hip_flexion_moment_{ipsi,contra}_Nm_kg`
- `knee_flexion_moment_{ipsi,contra}_Nm_kg`
- `ankle_dorsiflexion_moment_{ipsi,contra}_Nm_kg`

### Ground Reaction Forces
- `grf_vertical_{ipsi,contra}_BW`
- `grf_anterior_{ipsi,contra}_BW`
- `grf_lateral_{ipsi,contra}_BW`

### Center of Pressure
- `cop_anterior_{ipsi,contra}_m`
- `cop_lateral_{ipsi,contra}_m`
- `cop_vertical_{ipsi,contra}_m`

## Sign Conventions

Following LocoHub standards:
- **Hip**: Flexion positive
- **Knee**: Flexion positive (source data negated)
- **Ankle**: Dorsiflexion positive
- **Moments**: Internal moments, flexion positive
- **GRF**: Upward positive (vertical), forward positive (anterior)

## Notes

- Gait cycles detected from vertical GRF threshold crossings
- Uses biological moments (exo torque subtracted) when available
- Exo powered/unpowered status recorded in task_info
- Phase3 subjects used for validation (not in training data)
