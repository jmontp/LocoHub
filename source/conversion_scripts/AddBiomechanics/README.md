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

## Quick Start

### Convert B3D to Parquet
```bash
python convert_addbiomechanics_to_parquet.py
```

### Add Phase Information
```bash
python add_phase_info.py
```

### Add Task Information
```bash
python add_task_info.py
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