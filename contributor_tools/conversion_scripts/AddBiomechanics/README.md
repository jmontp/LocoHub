# AddBiomechanics Dataset Converter

Convert AddBiomechanics B3D files to LocoHub standardized parquet format.

## Quick Start

```bash
# Convert a specific sub-dataset
python convert_addbiomechanics_to_parquet.py \
    --dataset Moore2015 \
    --input /path/to/Moore2015/b3d/files \
    --output-dir ../../../converted_datasets
```

## Supported Datasets (12)

| Dataset | Task Types | Notes |
|---------|------------|-------|
| Moore2015 | Level walking | Treadmill at 0.8, 1.2, 1.6 m/s |
| Fregly2012 | Dynamic walking | Various gait modifications |
| Hamner2013 | Running | 2-5 m/s speeds |
| Santos2017 | Balance pose | Static standing poses |
| Tan2021 | Running | Modified running variants |
| Tan2022 | Dynamic walking | Modified walking variants |
| vanderZee2022 | Level walking | Treadmill trials |
| Wang2023 | Multiple | Walking, running, jumps, lunges, squats |
| Falisse2016 | Walking, running | Muscle redundancy study |
| Han2023 | Multiple | 19 motion types (yoga, dance, sports) |
| Tiziana2019 | Walking, stairs | Ages 6-72, toe/heel walking |
| Carter2023 | Running | Treadmill at various speeds/gradients |

**Excluded**: Camargo2021 (available separately as GT21/Gtech_2021 with original data)

## Output Files

The converter produces two output files per dataset:

- `{dataset}_time.parquet` - Time-indexed data (one row per frame)
- `{dataset}_phase.parquet` - Phase-normalized data (150 rows per stride)

## CLI Arguments

```
--dataset, -d    Dataset name (required)
--input, -i      Input directory containing B3D files (required)
--output-dir, -o Output directory (default: converted_datasets/)
```

## File Structure

```
AddBiomechanics/
├── convert_addbiomechanics_to_parquet.py  # Main conversion script
├── dataset_configs.py                      # Per-dataset configurations
├── metadata.yaml                           # Dataset metadata
├── README.md                               # This file
└── requirements.txt                        # Python dependencies
```

## Requirements

```bash
pip install nimblephysics numpy pandas scipy tqdm pyarrow
```

Key dependencies:
- `nimblephysics` - B3D file parsing
- `pandas` / `pyarrow` - Parquet I/O
- `scipy` - Interpolation

## Data Source

- Website: https://addbiomechanics.org/
- Format: B3D (Biomechanics 3D) files
- Institution: Stanford University

## Citation

```bibtex
@misc{addbiomechanics2024,
  title = {AddBiomechanics Dataset},
  year = {2024},
  url = {https://addbiomechanics.org/}
}
```

Individual sub-dataset citations are available in the metadata.yaml file.
