# Locomotion Datasets Glossary

This glossary provides a quick reference for all standardized locomotion datasets in this repository. For detailed information about each dataset, see the individual dataset documentation files.

## Available Datasets

### 1. University of Michigan 2021 (UMich 2021)
- **Focus**: Treadmill-based locomotion with speed and incline variations
- **Subjects**: 10 healthy adults (5M/5F, age 20-60)
- **Key Activities**: Walking (multiple speeds/inclines), running, sit-to-stand, stairs
- **Unique Features**: Systematic incline variations (-10° to +10°), walk-to-run transitions
- **Format**: Time series (100 Hz) and phase-normalized (150 points/cycle)
- **Documentation**: [`dataset_umich_2021.md`](dataset_umich_2021.md)

### 2. Georgia Tech 2023 (GTech 2023)
- **Focus**: Diverse daily activities and sports movements
- **Subjects**: 12 healthy adults (AB01-AB13, excluding AB04)
- **Key Activities**: 20+ tasks including walking, running, jumping, sports movements, functional tasks
- **Unique Features**: EMG data, IMU sensors, extensive activity variety
- **Format**: Time series (200 Hz) and phase-normalized (150 points/cycle)
- **Documentation**: [`dataset_gtech_2023.md`](dataset_gtech_2023.md)

### 3. AddBiomechanics (Various Years)
- **Focus**: Large-scale aggregated dataset from multiple sources
- **Subjects**: [To be documented]
- **Key Activities**: [To be documented]
- **Unique Features**: B3D file format, nimblephysics processing
- **Format**: Time series and phase-normalized
- **Documentation**: [`dataset_addbiomechanics.md`](dataset_addbiomechanics.md) (to be created)

## Quick Comparison

| Feature | UMich 2021 | GTech 2023 | AddBiomechanics |
|---------|------------|------------|-----------------|
| **Year** | 2021 | 2023 | Various |
| **Subjects** | 10 | 12 | TBD |
| **Primary Focus** | Treadmill locomotion | Multi-activity | Aggregated |
| **Sampling Rate** | 100 Hz | 200 Hz | Variable |
| **Incline Walking** | ✓ (-10° to +10°) | ✓ (5°, 10°) | TBD |
| **Running** | ✓ (1.8-2.4 m/s) | ✓ | TBD |
| **Stairs** | ✓ (limited) | ✓ (extensive) | TBD |
| **Sports Movements** | ✗ | ✓ | TBD |
| **EMG Data** | ✗ | ✓ (raw) | TBD |
| **IMU Data** | ✗ | ✓ | TBD |
| **Force Plates** | ✓ (treadmill) | ✓ (ground+treadmill) | TBD |

## Common Variables Across Datasets

All datasets are standardized to include these core biomechanical variables:

### Kinematics (per leg: _r/right, _l/left)
- Joint angles: hip, knee, ankle (3 planes each)
- Joint velocities: hip, knee, ankle (sagittal plane minimum)

### Kinetics (per leg: _r/right, _l/left)
- Joint moments: hip, knee, ankle (3 planes each, mass-normalized)
- Ground reaction forces: AP, vertical, ML
- Center of pressure: AP, vertical, ML

### Metadata
- `subject_id`: Unique subject identifier
- `task_id`: Task/activity identifier
- `time_s`: Time in seconds (time series format)
- `phase`: Gait cycle percentage 0-100% (phase-normalized format)

## File Naming Convention

All standardized datasets follow this structure:
```
converted_datasets/
├── [dataset_name]_[year]_time.parquet      # Time series data
├── [dataset_name]_[year]_phase.parquet     # Phase-normalized data
└── [dataset_name]_[year]_metadata.json     # Additional metadata
```

## Adding New Datasets

When adding a new dataset to this repository:

1. Create a detailed documentation file using [`dataset_template.md`](dataset_template.md)
2. Update this glossary with a summary entry
3. Add the dataset to the quick comparison table
4. Ensure conversion scripts output to `converted_datasets/` folder
5. Update CLAUDE.md with any dataset-specific commands

## Usage Tips

- **For gait analysis**: Use phase-normalized data for cross-subject comparisons
- **For time-series ML**: Use time series data with original sampling rates
- **For multi-task analysis**: GTech 2023 offers the most activity variety
- **For treadmill studies**: UMich 2021 provides systematic speed/incline conditions

---
*Last Updated: January 2025*
*Glossary Version: 1.0*

**Note**: This glossary should be updated whenever new datasets are added to maintain a centralized reference for all available data.