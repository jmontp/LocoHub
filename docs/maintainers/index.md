---
title: Maintainers
---

# Maintainers

Essential commands and paths for day‑to‑day maintenance.

## Do This

- Convert: `contributor_tools/conversion_scripts/<dataset>/`
- Quick validate: `python contributor_tools/quick_validation_check.py <dataset_phase.parquet>`
- Filter valid strides: `python contributor_tools/create_filtered_dataset.py <dataset_phase_raw.parquet>`
- Full report (docs): `python contributor_tools/create_dataset_validation_report.py --dataset <dataset_phase.parquet>`
- Serve docs: `mkdocs serve`

## Where Things Are

- Converters: `contributor_tools/conversion_scripts/`
- Outputs: `converted_datasets/`
- Validation engine: `internal/validation_engine/validator.py`
- Validation ranges: `contributor_tools/validation_ranges/`
- Python API: `user_libs/python/locomotion_data.py`

## Workflows

- New dataset: add converter → export `<name>_phase.parquet` → quick validate → full report.
- Update ranges: edit YAML → regenerate reports → spot‑check datasets.
- Add variable: update `feature_constants.py` → update converters → update ranges.
- Website updates: run the maintainer CLI (see the [Website Management Flow](website_management_flow.md)) instead of editing registries by hand.

## Environment

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
