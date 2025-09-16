---
title: Datasets
---

# Datasets

Snapshot of available standardized datasets. Downloads point to externally
hosted parquet files so large data stays off of GitHub. Documentation is being
rebuilt with `prepare_dataset_submission.py`; the previous Markdown pages now
live under `_legacy/` for reference while the regenerated docs land here.

## At a Glance

| Dataset | Tasks | Docs | Validation | Download | Notes |
|---------|-------|------|------------|----------|-------|
| University of Michigan 2021 | Level, incline, decline walking | [UMich 2021](umich_2021_raw.md) | [Report](validation_reports/umich_2021_phase_validation_report.md) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Variant: [Filtered](umich_2021_filtered.md) |
| Georgia Tech 2023 | Walking, stairs, inclines | Legacy: [GTech 2023](_legacy/dataset_gtech_2023.md) | [Report](validation_reports/gtech_2023_phase_validation_report.md) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Validated |
| Georgia Tech 2021 | Walking, stairs, inclines | [GTech 2021](gtech_2021_raw.md) | — (refresh pending) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Variant: [Filtered](gtech_2021_filtered.md) |
| AddBiomechanics | Walking, running, jumping, stairs | Legacy: [Docs](_legacy/dataset_addbiomechanics.md) | — | — | Coming soon |

More: Legacy [Dataset Comparison](_legacy/dataset_comparison.md) • [Validation Reports](validation_reports/index.md)

## Format

- Phase-indexed (150 samples per cycle), with subject/task metadata columns.
- Naming pattern: `joint_motion_measurement_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`).
- Spec and ranges: [Reference](../reference/index.md) • [Validation Ranges](validation_ranges.md)
