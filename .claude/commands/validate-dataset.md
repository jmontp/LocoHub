# Validate Dataset

Validate a converted biomechanical dataset and generate documentation.

## Usage

```
/validate-dataset <parquet_file> [--short-code CODE]
```

## Arguments

- `parquet_file`: Path to the phase-normalized parquet file (e.g., `converted_datasets/my_dataset_phase.parquet`)
- `--short-code`: Optional 2-5 character code for the dataset (e.g., GT21, UM24K)

## Workflow

When this skill is invoked, follow these steps:

### 1. Quick Validation Check

Run the validation check to see pass rates:

```bash
python3 contributor_tools/quick_validation_check.py <parquet_file>
```

Report the results to the user, including:
- Overall pass rate
- Per-task pass rates
- Any schema compliance issues

### 2. If Validation Fails (<90% pass rate)

Run diagnostics to identify issues:

```bash
python3 contributor_tools/diagnose_validation_failures.py <parquet_file> --top 10
```

Explain which features are failing and suggest fixes (sign conventions, unit conversions, etc.)

### 3. Generate Documentation

If validation passes or user wants to proceed:

```bash
python3 contributor_tools/manage_dataset_documentation.py add-dataset \
    --dataset <parquet_file> \
    --short-code <CODE> \
    --metadata-file <path_to_metadata.yaml>
```

If no metadata file exists, create one in the conversion script directory with:
- display_name
- short_code
- description
- year
- institution
- subjects
- citation
- protocol
- notes

### 4. Report Results

Summarize what was created:
- Documentation files in `docs/datasets/`
- Validation plots in `docs/datasets/validation_plots/<code>/`
- Metadata in `docs/datasets/_metadata/<code>.yaml`

## Key Tools

| Tool | Purpose |
|------|---------|
| `quick_validation_check.py` | Fast pass/fail validation |
| `diagnose_validation_failures.py` | Identify failing features |
| `manage_dataset_documentation.py` | Generate all documentation |
| `create_clean_dataset.py` | Remove failing strides |

## Example

```
/validate-dataset converted_datasets/umich_2024_knee_exo_phase.parquet --short-code UM24K
```
