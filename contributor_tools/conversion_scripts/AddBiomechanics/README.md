# AddBiomechanics Dataset Converter

This directory contains conversion scripts for the AddBiomechanics dataset format.

## Dataset Citation

**AddBiomechanics Dataset**
- Source: Stanford Neuromuscular Biomechanics Lab
- Format: B3D (Biomechanics 3D) files
- Website: https://addbiomechanics.org/

## Detailed Documentation

For comprehensive dataset information including structure, variables, and usage examples, see:
- 📖 [**AddBiomechanics Dataset Documentation**](../../../docs/datasets_documentation/dataset_addbiomechanics.md)

## Downloading the Data

1. Visit the AddBiomechanics website: https://addbiomechanics.org/
2. Create an account and browse available datasets
3. Download B3D files for the subjects/trials you need
4. Extract the downloaded files to the expected directory structure below

## Expected File Structure

Before running the conversion scripts, organize your data as follows:

```
AddBiomechanics/
├── raw_data/               # Place downloaded B3D files here
│   ├── subject_01/
│   │   ├── trial_01.b3d
│   │   ├── trial_02.b3d
│   │   └── ...
│   ├── subject_02/
│   │   └── ...
│   └── ...
├── convert_addbiomechanics_to_parquet.py
├── add_phase_info.py
├── add_task_info.py
├── b3d_to_parquet.py
└── requirements.txt
```

## Entry Points for Conversion

### 1. Time-Indexed Dataset Generation

```bash
# Main entry point - converts B3D files to time-indexed parquet
python convert_addbiomechanics_to_parquet.py --input_dir raw_data --output_dir ../../../converted_datasets

# This will create:
# - converted_datasets/addbiomechanics_time.parquet
```

### 2. Phase-Indexed Dataset Generation

```bash
# After generating time-indexed data, create phase-normalized version
python add_phase_info.py --input ../../../converted_datasets/addbiomechanics_time.parquet

# This will create:
# - converted_datasets/addbiomechanics_phase.parquet
```

### 3. Optional: Add Task Metadata

```bash
# Add detailed task information if available
python add_task_info.py --input ../../../converted_datasets/addbiomechanics_time.parquet

# Updates the existing parquet files with task metadata
```

## Scripts Overview

- `b3d_to_parquet.py` - Core B3D file parser and converter
- `convert_addbiomechanics_to_parquet.py` - Main conversion pipeline
- `add_phase_info.py` - Adds gait cycle phase normalization
- `add_task_info.py` - Adds task metadata and labels

## Requirements

See `requirements.txt` for dependencies. Key packages:
- nimblephysics
- torch
- pandas
- pyarrow