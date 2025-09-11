---
title: Maintainers
---

# Maintainers

Short, task-first guide for keeping LocoHub healthy. Links go straight to the source you need.

## Quick Actions

- Convert dataset: `contributor_tools/conversion_scripts/<dataset>/`
- Validate quickly: `python contributor_tools/quick_validation_check.py <path.parquet>`
- Filter to valid strides: `python contributor_tools/create_filtered_dataset.py <raw.parquet>`
- Generate docs report: `python contributor_tools/create_dataset_validation_report.py --dataset <path.parquet>`
- Serve docs: `mkdocs serve`

## Key Paths

- Converters: `contributor_tools/conversion_scripts/`
- Outputs: `converted_datasets/`
- Validation engine: `internal/validation_engine/validator.py`
- Validation ranges (YAML): `contributor_tools/validation_ranges/`
- Python API: `user_libs/python/locomotion_data.py`

## Core Workflows

- New dataset: add converter → export `<name>_phase.parquet` → quick-validate → full report.
- Update ranges: edit YAML → regenerate reports → spot-check affected datasets.
- Add variable: update `feature_constants.py` → adjust converters → update ranges.

## Must-Know Links

- Scripts Cheat Sheet: [maintainers/scripts_cheatsheet.md](scripts_cheatsheet.md)
- Developer Guide: [maintainers/developer_guide.md](developer_guide.md)
- Testing: [maintainers/testing.md](testing.md)
- Architecture (high level): [maintainers/architecture.md](architecture.md)
- Setup: [maintainers/setup.md](setup.md)

## Minimal Setup

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdocs serve  # http://localhost:8000
```

That’s it. For deeper details, jump to the guides above when needed.
