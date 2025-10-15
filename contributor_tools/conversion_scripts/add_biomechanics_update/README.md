# AddBiomechanics Update Pipeline

This module provides a clean conversion path from raw AddBiomechanics B3D files to
the canonical locomotion parquet formats. It supersedes the legacy scripts under
`AddBiomechanics/` by adopting shared utilities, configuration-driven workflows,
and repository-wide conventions outlined in `docs/reference/index.md`.

## Layout

```
add_biomechanics_update/
├── convert.py              # CLI entrypoint for time + phase conversion
├── config.py               # Dataset selection, path configuration, logging
├── schemas.py              # Canonical column ordering & validation hooks
├── task_mappings.py        # Dataset-specific task metadata helpers
├── io/
│   ├── b3d_reader.py       # Streaming reader that yields normalized frames
│   └── writers.py          # Parquet writers using pyarrow, shared schema
├── utils/
│   ├── stride_events.py    # GRF-based heel-strike detection & phase helpers
│   └── metadata.py         # Subject/task metadata normalization utilities
├── tests/
│   ├── test_stride_events.py
│   ├── test_end_to_end.py
│   └── data/               # Lightweight golden fixtures
├── docs/
│   └── design_notes.md     # Rationale, assumptions, open questions
└── notebooks/              # Optional exploratory work
```

## Key Principles

- **Configuration first**: All filesystem locations and dataset lists are passed
  through CLI flags or YAML config. No hard-coded `/datasets/...` paths.
- **Single-pass streaming**: B3D parsing yields pandas/pyarrow tables in
  manageable chunks without temporary `_partial` files.
- **Canonical schema**: Writers enforce required columns (`subject`, `task`,
  `task_id`, `task_info`, `step`, `phase_ipsi`, `time_s`, etc.) and verify task
  names against `task_registry`.
- **Shared utilities**: Heel-strike detection lives in `contributor_tools/common`
  so other datasets can reuse it. This module only provides thin wrappers.
- **Testable pipeline**: Unit tests cover stride-event detection, schema
  validation, and a smoke end-to-end conversion using sample B3D fixtures.

## Roadmap

1. Implement the shared GRF-based heel-strike detector and expose it through
   `utils/stride_events.py`.
2. Port dataset-specific task mappings into `task_mappings.py`, aligning output
   with canonical task families and metadata keys.
3. Replace legacy scripts by wiring `convert.py` into the contributor CLI docs.

