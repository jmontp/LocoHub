---
title: Datasets
---

# Datasets

Snapshot of available standardized datasets. Links go to docs, validation, and downloads.

## At a Glance

| Dataset | Tasks | Docs | Validation | Download | Notes |
|---------|-------|------|------------|----------|-------|
| University of Michigan 2021 | Level, incline, decline walking | [UMich 2021](dataset_umich_2021.md) | [Report](validation_reports/umich_2021_phase_validation_report.md) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Variants: [Filtered](dataset_umich_2021_filtered.md), [Events](dataset_umich_2021_events.md) |
| Georgia Tech 2023 | Walking, stairs, inclines | [GTech 2023](dataset_gtech_2023.md) | [Report](validation_reports/gtech_2023_phase_validation_report.md) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Validated |
| Georgia Tech 2021 | Walking, stairs, inclines | [GTech 2021](dataset_gtech_2021.md) | [Report](validation_reports/gtech_2021_phase_validation_report.md) | [Link](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) | Variant: [Filtered](dataset_gtech_2021_filtered.md) |
| AddBiomechanics | Walking, running, jumping, stairs | [Docs](dataset_addbiomechanics.md) | — | — | Coming soon |

More: [Comparison Plots](comparison_plots/) • [Validation Reports](validation_reports/index.md)

## Format

- Phase-indexed (150 samples per cycle), with subject/task metadata columns.
- Naming pattern: `joint_motion_measurement_side_unit` (e.g., `knee_flexion_angle_ipsi_rad`).
- Spec and ranges: [Standard Spec](../standard_spec/standard_spec.md) • [Validation Ranges](validation_ranges.md)
