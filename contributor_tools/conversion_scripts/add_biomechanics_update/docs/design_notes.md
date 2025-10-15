# AddBiomechanics Update — Design Notes

## Legacy Audit Summary

- Conversion scripts rely on hard-coded `/datasets/...` paths and mutable module
  state, preventing reuse and automated testing.
- `b3d_to_parquet.py` writes via `fastparquet` in append mode, creating temporary
  `_partial_` files and risking schema drift across chunks.
- Task metadata helpers mix canonical labels with dataset-specific strings and
  leave several datasets unimplemented (`Falisse2017`, `Tiziana2019`,
  `Carter2023`, etc.).
- Phase generation uses duplicated GRF logic, saves NaN-filled records, and
  stores per-leg `phase_l`/`phase_r` columns instead of the required
  `phase_ipsi`/`phase_contra` schema.
- Merge markers remain in `convert_addbiomechanics_to_parquet.py`, signalling
  unfinished integration.

## Goals

1. Provide a deterministic CLI that converts selected datasets end-to-end.
2. Normalize subject/task metadata to match `task_registry` and reference docs.
3. Ship a reusable vertical-GRF heel-strike detector for all contributor tools.
4. Produce both time- and phase-indexed parquet files with canonical columns.
5. Cover the pipeline with unit tests and documentation.

## Open Questions / TODO

- Confirm which AddBiomechanics datasets should ship in the first release of the
  update (prioritize Santos2017, Tiziana2019?).
- Determine naming convention for generated parquet files (e.g.,
  `addbiomechanics_<dataset>_{time|phase}.parquet`).
- Evaluate whether subject metadata should include demographics from accompanying
  CSVs or rely solely on B3D contents.
- Define minimal sample data for tests without distributing large B3D files.


## Documentation & Testing Plan

- Update `contributor_tools/README.md` (or create a dedicated section) once the
  new CLI is production-ready, including example commands and dependency notes.
- Expand `docs/reference/index.md` with a pointer to the shared GRF detector and
  the expectation that time-indexed datasets expose `grf_vertical_*` columns for
  automated phase conversion.
- Author a usage guide in `docs/contributing/` that walks contributors through
  running `add_biomechanics_update/convert.py`, highlighting configuration files,
  validation steps, and troubleshooting tips.
- Integrate the new detector into the validation workflow by adding tests that
  feed converted parquet files into `DatasetValidator`, ensuring heel-strike
  detection produces 150-point phase exports without gaps.
- Extend unit tests to cover:
  - conversion of synthetic B3D fixtures end-to-end (time + phase outputs)
  - task metadata mapping for each supported dataset
  - schema enforcement (required column presence/order)
  - regression checks for GRF noise handling and edge cases (e.g., missing legs)
