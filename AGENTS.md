# LocoHub contributor guidance

## Purpose

LocoHub delivers curated standardized locomotion data and clear documentation.
It does not maintain a public analysis SDK. Researchers use ordinary Parquet/CSV
readers. Historical Python/MATLAB/R libraries are retained under `legacy/` only.

## Active structure

- `contributor_tools/conversion_scripts/`: dataset-specific source adapters.
- `contributor_tools/common/`: internal schema, table, validation, transformation and plotting helpers.
- `contributor_tools/build_dataset_release.py`: immutable local release bundles.
- `contributor_tools/DATA_CONTRACT.md`: versioned observation contract and release workflow.
- `docs/`: researcher catalog, data reference, native Python/MATLAB examples.
- `tests/`: small independent data/conversion/release fixtures.
- `converted_datasets/`: local scientific artifacts; never overwrite implicitly.

## Scientific correctness

Preserve source recording, observation and anatomical reference identities.
Never invent timing, mass, clinical laterality, unavailable measurements, or source
provenance. Keep individual cycles, transfers, ensembles and continuous recordings
distinct. Inclusive phase exports have exactly 150 samples from 0 to 100 percent.

Use one structured observation assessment for filtering, reports and release
facts. Missing/unassessed signals are not evidence of passing. Reference ranges
need population/protocol context and evidence; do not tune to reach a desired
aggregate pass rate. Draft tuner profiles are not approved release profiles.

Full converted and profile-filtered variants retain their shared source lineage.
Every exclusion must be accounted for. Historical artifacts remain explicitly
legacy/unreviewed until reconverted or independently reconciled.

## Resource constraints

This is low-priority work on a shared WSL host. Use one numerical worker, low
process/I/O priority, small fixtures and bounded reads. Do not load full research
datasets or launch bulk conversions/MATLAB automatically. Default release/review
loads have a 256 MiB admission estimate. Do not raise it to bypass a rejection.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg nice -n 19 ionice -c 3 python3 -m pytest -q
```

Full-data integration tests are opt-in with `--run-integration`. MATLAB R2023b
is installed in the Windows default location, accessed from WSL. Coordinate any
native MATLAB run because it has a larger startup memory footprint.

## Working conventions

Human-managed, focused development. Preserve pre-existing edits. Keep source
adapters and reviewer tools simple; add tests against independently known values
rather than mirroring implementation. Use synthetic fixtures honestly labeled as
synthetic. Do not claim scientific dataset regeneration from fixture tests.

Do not publish or push releases without the requested destination/workflow.
If committing, stage specific files (never `git add -A`) and include:

Co-authored-by: José A. Montes Pérez <jmontp@umich.edu>
