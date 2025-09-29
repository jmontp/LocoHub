---
title: Datasets
---

# Datasets

Snapshot of available standardized datasets. Downloads point to externally
hosted parquet files so large data stays off of GitHub. Documentation is being
rebuilt with `manage_dataset_documentation.py`; the previous Markdown pages now
live under `_legacy/` for reference while the regenerated docs land here.

## At a Glance

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Quality | Validation | Download |
|---------|-------|---------|------------|----------|
| [Umich 2021 Raw](um21.md) | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | ⚠️ Partial (85.3%) | [Report](um21_validation.md) | Coming Soon |
<!-- DATASET_TABLE_END -->

<div style="border: 1px solid #1f78d1; background: #e7f2ff; padding: 1rem 1.25rem; border-radius: 0.75rem; margin: 1.5rem 0;">
  <strong>🧭 Coming Soon:</strong> Interactive Dataset Comparison. Select a task and line up validation plots, pass rates, and download links across datasets in one place.
</div>

## Format

- Phase-indexed (150 samples per cycle), with subject/task metadata columns.
- Naming pattern: `joint_motion_measurement_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`).
- Spec and ranges: [Reference](../reference/index.md) • [Validation Ranges](validation_ranges.md)
