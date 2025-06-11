# CLAUDE.md - GTech 2023 Conversion

Process Georgia Tech 2023 biomechanical data (13 subjects, 19 activities).

## Key Scripts

**Main Conversion**:
- `convert_gtech_all_to_parquet.py` - MATLAB .mat → Parquet converter
- `combine_subjects_efficient.py` - Efficient subject data merger
- `process_all_subjects.sh` - Batch processing utility

**Legacy MATLAB**:
- `convert_gtech_phase_to_parquet.m` - Phase conversion (legacy)

## Data Structure

**Input**:
- `RawData/AB01/` through `RawData/AB13/` - Subject directories with .mat files
- `RawData/Subject_masses.csv` - Body mass metadata
- Kinematic, kinetic, EMG, and IMU data

**Output**:
- `gtech_2023_time.parquet` - Time-indexed dataset
- `gtech_2023_phase.parquet` - Phase-indexed (150 points/cycle)

## Processing Pipeline

```
MATLAB .mat files → convert_gtech_all_to_parquet.py → Time-indexed Parquet
                                                            ↓
Subject metadata ← combine_subjects_efficient.py ← Phase-indexed Parquet
```

## Key Features

**Data Processing**:
- 19 different activity types (walking, stairs, jumping, etc.)
- Full kinematic and kinetic data extraction
- EMG and IMU data integration
- Standardized variable naming implementation

**Quality Assurance**:
- Gait cycle segmentation with heel strike detection
- Alignment validation plots in `Plots/AlignmentChecks_RawHS/`
- Missing data documentation in `_datamissing.txt`
- Cross-validation with MATLAB verification tools

## Utilities

**Helper Scripts** (`utilities/`):
- `convert_gtech_rotm_to_eul_csv.m` - Rotation matrix conversions
- `plot_leg_alignment.m` - Leg alignment visualization
- `verify_gtech_data.ipynb` - Data verification notebook
- `benchmark_processing.m` - Performance testing

## Performance

**Processing Characteristics**:
- Moderate memory requirements compared to AddBiomechanics
- Batch processing supported for all 13 subjects
- Efficient subject file merging algorithms

## Testing

```bash
# Process all subjects
python convert_gtech_all_to_parquet.py --input_dir RawData/ --output_dir ./converted/
./process_all_subjects.sh

# Verify conversion
python utilities/verify_gtech_data.ipynb
```

---

*Efficient conversion of comprehensive biomechanical dataset with multiple activity types.*