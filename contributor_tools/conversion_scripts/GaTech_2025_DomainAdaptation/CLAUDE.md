# GaTech 2025 Domain Adaptation Conversion

## Dataset Info

- **Paper:** Scherpereel et al., "Deep Domain Adaptation Eliminates Costly Data Required for Task-Agnostic Wearable Robotic Control" (Science Robotics, 2025)
- **Repository:** https://repository.gatech.edu/entities/publication/d6798aa7-541e-4f6e-980e-4855cdd3f629
- **Lab:** EPIC Lab (Georgia Tech)
- **Short code:** GT25D
- **Subject prefix:** GT25D_

## Important: Different Subjects from GaTech_2024_TaskAgnostic

Despite overlapping subject ID labels (BT01-BT08), these are **different participants** from the Molinaro et al. (Nature 2024) dataset. The mass values and subject count confirm this.

## Data Location

Source data is stored on the S: drive:
```
S:\locomotion_data\GaTech_2025_DomainAdaptation\Parsed
```

In WSL:
```
/mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed
```

## Running the Conversion

```bash
python3 contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py
```

With explicit input path:
```bash
python3 contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/convert_gtech_2025_da_to_parquet.py \
    --input /mnt/s/locomotion_data/GaTech_2025_DomainAdaptation/Parsed
```

Output: `converted_datasets/gtech_2025_da_phase_dirty.parquet`

## Model Variants

The dataset tests 3 domain adaptation models. The model variant is stored in `task_info` as `model:<variant>`:
- **baseline**: Semisupervised baseline model (device-specific data, limited tasks/participants)
- **4t4s**: Semisupervised model with domain adaptation (same device data budget + unlabeled data)
- **0task**: Unsupervised model (no device-specific data, only unactuated/unlabeled data)

## CSV Format

Identical to GaTech_2024_TaskAgnostic Parsed format:
- 200 Hz sampling rate
- Parsed naming: `{subject}_{task_name}_{data_type}.csv`
- Same column names, sign conventions, and units
- Exo sign convention: extension positive, flexion negative
- OpenSim convention: hip flexion+, knee extension+, ankle plantarflexion+

## Sign Conventions Applied in Conversion

- Knee angles: negated (OpenSim extension+ -> our flexion+)
- Knee moments: negated (same reason)
- Exo torques: negated (exo extension+ -> our flexion+)
- GRF anterior: negated then auto-corrected for walking direction
- GRF lateral: auto-corrected so ipsi is negative (medial)
