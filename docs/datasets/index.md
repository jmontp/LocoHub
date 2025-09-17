---
title: Datasets
---

# Datasets

Snapshot of available standardized datasets. Downloads point to externally
hosted parquet files so large data stays off of GitHub. Documentation is being
rebuilt with `prepare_dataset_submission.py`; the previous Markdown pages now
live under `_legacy/` for reference while the regenerated docs land here.

## At a Glance

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Quality | Documentation | Download |
|---------|-------|---------|---------------|----------|
| [Georgia Tech 2021](https://jmontp.github.io/LocoHub/datasets/gtech_2021_raw/) | Level Walking, Incline Walking, Decline Walking, Stair Ascent, Stair Descent | ⚠️ Partial (89.2%) | [Docs](https://jmontp.github.io/LocoHub/datasets/gtech_2021_raw/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [Georgia Tech 2021 (Filtered)](https://jmontp.github.io/LocoHub/datasets/gtech_2021_filtered/) | Level Walking, Incline Walking, Decline Walking, Stair Ascent, Stair Descent | ✅ Validated | [Docs](https://jmontp.github.io/LocoHub/datasets/gtech_2021_filtered/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [University of Michigan 2021](https://jmontp.github.io/LocoHub/datasets/umich_2021_raw/) | Level Walking, Incline Walking, Decline Walking, Run, Sit To Stand, Stand To Sit | ⚠️ Partial (92.7%) | [Docs](https://jmontp.github.io/LocoHub/datasets/umich_2021_raw/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| [University of Michigan 2021 (Filtered)](https://jmontp.github.io/LocoHub/datasets/umich_2021_filtered/) | Level Walking, Incline Walking, Decline Walking, Run, Sit To Stand, Stand To Sit | ✅ Validated | [Docs](https://jmontp.github.io/LocoHub/datasets/umich_2021_filtered/) | [Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
<!-- DATASET_TABLE_END -->

More: Legacy [Dataset Comparison](_legacy/dataset_comparison.md) • [Validation Reports](validation_reports/index.md)

## Format

- Phase-indexed (150 samples per cycle), with subject/task metadata columns.
- Naming pattern: `joint_motion_measurement_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`).
- Spec and ranges: [Reference](../reference/index.md) • [Validation Ranges](validation_ranges.md)
