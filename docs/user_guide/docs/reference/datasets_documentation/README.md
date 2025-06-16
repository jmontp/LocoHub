# Locomotion Datasets Documentation

Comprehensive reference for all standardized locomotion datasets in this repository.

**Quick Reference:** [AddBiomechanics](dataset_addbiomechanics.md) • [GTech 2023](dataset_gtech_2023.md) • [UMich 2021](dataset_umich_2021.md)

## Available Datasets

### 1. University of Michigan 2021 (UMich 2021)
- **Focus**: Treadmill-based locomotion with speed and incline variations
- **Subjects**: 10 healthy adults (5M/5F, age 20-60)
- **Key Activities**: Walking (multiple speeds/inclines), running, sit-to-stand, stairs
- **Unique Features**: Systematic incline variations (-10° to +10°), walk-to-run transitions
- **Format**: Time series (100 Hz) and phase-normalized (150 points/cycle)
- **PI**: Robert D. Gregg IV, Ph.D. (Locomotor Control Systems Laboratory)
- **Publication**: [IEEE DataPort 2018](https://ieee-dataport.org/open-access/effect-walking-incline-and-speed-human-leg-kinematics-kinetics-and-emg)
- **Documentation**: [`dataset_umich_2021.md`](dataset_umich_2021.md)

### 2. Georgia Tech 2023 (GTech 2023)
- **Focus**: Diverse daily activities and sports movements
- **Subjects**: 12 healthy adults (AB01-AB13, excluding AB04)
- **Key Activities**: 20+ tasks including walking, running, jumping, sports movements, functional tasks
- **Unique Features**: EMG data, IMU sensors, extensive activity variety, non-cyclic tasks
- **Format**: Time series (200 Hz) and phase-normalized (150 points/cycle)
- **PI**: Aaron Young, Ph.D. (EPIC Lab - Exoskeleton and Prosthetic Intelligent Controls)
- **Publication**: [Scientific Data 2023](https://doi.org/10.1038/s41597-023-02341-6)
- **Documentation**: [`dataset_gtech_2023.md`](dataset_gtech_2023.md)

### 3. AddBiomechanics 
- **Focus**: OpenSim-processed biomechanics data with full-body kinematics and kinetics
- **Subjects**: Multiple subjects from various sources
- **Key Activities**: Walking, running, and various locomotion tasks
- **Unique Features**: B3D file format, nimblephysics processing, pre-scaled OpenSim models
- **Format**: Time series and phase-normalized (150 points/cycle)
- **PI**: Stanford Neuromuscular Biomechanics Lab
- **Publication**: [bioRxiv 2023](https://doi.org/10.1101/2023.06.15.545116)
- **Documentation**: [`dataset_addbiomechanics.md`](dataset_addbiomechanics.md)

## Quick Comparison

| Feature | UMich 2021 | GTech 2023 | AddBiomechanics |
|---------|------------|------------|-----------------|
| **Year** | 2021 | 2023 | Ongoing |
| **Subjects** | 10 | 12 | Multiple |
| **Primary Focus** | Treadmill locomotion | Multi-activity | Full-body biomechanics |
| **Sampling Rate** | 100 Hz | 200 Hz | Variable |
| **Incline Walking** | ✓ (-10° to +10°) | ✓ (5°, 10°) | ✓ |
| **Running** | ✓ (1.8-2.4 m/s) | ✓ | ✓ |
| **Stairs** | ✓ (limited) | ✓ (extensive) | ✓ |
| **Sports Movements** | ✗ | ✓ | ✓ |
| **EMG Data** | ✗ | ✓ (raw) | ✗ |
| **IMU Data** | ✗ | ✓ | ✗ |
| **Force Plates** | ✓ (treadmill) | ✓ (ground+treadmill) | ✓ |

## Common Variables Across Datasets

All datasets are standardized to include these core biomechanical variables:

### Kinematics (per leg: _contra/ipsi)
- Joint angles: hip, knee, ankle (3 planes each)
- Joint velocities: hip, knee, ankle (sagittal plane minimum)

### Kinetics (per leg: _contra/ipsi)
- Joint moments: hip, knee, ankle (3 planes each, mass-normalized)
- Ground reaction forces: AP, vertical, ML
- Center of pressure: AP, vertical, ML

### Metadata
- `subject`: Unique subject identifier
- `task`: Task/activity identifier
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

## Usage Tips

- **For gait analysis**: Use phase-normalized data for cross-subject comparisons
- **For time-series ML**: Use time series data with original sampling rates
- **For multi-task analysis**: GTech 2023 offers the most activity variety
- **For treadmill studies**: UMich 2021 provides systematic speed/incline conditions

## Adding New Datasets

When adding a new dataset to this repository:

1. Create detailed documentation using existing files as templates
2. Update this README with a summary entry
3. Add the dataset to the quick comparison table
4. Ensure conversion scripts output to `converted_datasets/` folder
5. Update CLAUDE.md with any dataset-specific commands

---

*These datasets provide cleaned, tested biomechanical data ready for reproducible research.*