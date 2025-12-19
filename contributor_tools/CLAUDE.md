# Contributor Tools

Tools for converting raw biomechanical datasets to the LocoHub standardized parquet format, validating conversions, and generating documentation.

## Directory Structure

```
contributor_tools/
├── conversion_scripts/     # Dataset-specific conversion scripts (MATLAB/Python)
│   ├── Gtech_2021/        # Georgia Tech 2021 (Camargo et al.)
│   ├── Gtech_2023/        # Georgia Tech 2023
│   ├── GaTech_2024_TaskAgnostic/  # Georgia Tech 2024 exoskeleton
│   ├── Umich_2021/        # University of Michigan 2021
│   └── AddBiomechanics/   # AddBiomechanics dataset
├── common/                 # Shared utilities (phase_detection.py)
├── validation_ranges/      # YAML files defining valid data ranges per task
└── validation_plots/       # Generated validation plot outputs
```

## Conversion Workflow

### 1. Convert Raw Data to Parquet

Each dataset has its own conversion script in `conversion_scripts/<dataset>/`:

- **MATLAB datasets**: Run `convert_<dataset>_phase_to_parquet.m` in MATLAB
- **Python datasets**: Run `convert_<dataset>_phase_to_parquet.py`

Output: `converted_datasets/<dataset>_phase_dirty.parquet`

### 2. Validate the Conversion

**Quick validation check:**
```bash
python contributor_tools/quick_validation_check.py converted_datasets/<dataset>_phase_dirty.parquet
```

**With plots:**
```bash
python contributor_tools/quick_validation_check.py <dataset>.parquet --plot --task level_walking
```

**Diagnose failures:**
```bash
python contributor_tools/diagnose_validation_failures.py <dataset>.parquet --top 10
```

### 3. Tune Validation Ranges (if needed)

Interactive GUI for adjusting validation ranges:
```bash
python contributor_tools/interactive_validation_tuner.py
```

### 4. Create Clean Dataset

Remove failing strides:
```bash
python contributor_tools/create_clean_dataset.py converted_datasets/<dataset>_phase_dirty.parquet
```
Output: `<dataset>_phase_clean.parquet`

### 5. Generate Documentation

**Full documentation (plots + markdown):**
```bash
python contributor_tools/generate_validation_documentation.py
```

**Manage dataset pages:**
```bash
python contributor_tools/manage_dataset_documentation.py add-dataset \
    --dataset converted_datasets/<dataset>_phase.parquet \
    --short-code XX21
```

## Key Tools Reference

| Tool | Purpose |
|------|---------|
| `quick_validation_check.py` | Fast pass/fail validation with optional plotting |
| `diagnose_validation_failures.py` | Identify which features fail and why (under/over bounds) |
| `interactive_validation_tuner.py` | GUI for adjusting validation range boxes |
| `create_clean_dataset.py` | Remove failing strides from dirty parquet |
| `generate_validation_documentation.py` | Generate plots and markdown docs |
| `manage_dataset_documentation.py` | Add/update/remove dataset documentation pages |
| `manage_tasks.py` | CLI for managing canonical task definitions |

## Validation Ranges

Located in `validation_ranges/`:
- `default_ranges_v3.yaml` - Current default ranges for able-bodied data
- `impaired_ranges.yaml` - Ranges for impaired population data
- `example_custom_ranges.yaml` - Template for custom ranges

## Conversion Script Structure

Each conversion script directory typically contains:
- Main conversion script (`convert_*.m` or `convert_*.py`)
- `utilities/` - Helper functions for that dataset
- Validation scripts (`validate_*.m`) - Verify conversion correctness

### MATLAB Conversion Notes

The MATLAB executable is on the Windows partition at the default install location (WSL environment). Conversion scripts output parquet files to `converted_datasets/`.

## Adding a New Dataset

1. Create `conversion_scripts/<NewDataset>/` directory
2. Write conversion script following existing patterns
3. Run conversion to produce `_dirty.parquet`
4. Validate with `quick_validation_check.py`
5. Tune ranges if needed with `interactive_validation_tuner.py`
6. Create clean dataset with `create_clean_dataset.py`
7. Generate documentation with `manage_dataset_documentation.py`
