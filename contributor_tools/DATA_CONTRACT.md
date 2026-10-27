# Identified observations and local dataset releases

The release pipeline preserves a complete source export and produces a separate,
profile-filtered download. It never repairs signals, generates missing source
identities, or changes the input file. The implementation is internal contributor
tooling; researchers can read the resulting Parquet tables with native tools.

## Observation contract

Every row supplies these columns:

| Column | Meaning |
| --- | --- |
| `subject` | Nonempty source subject identifier, stored as a string |
| `source_recording_id` | Nonempty identifier of the actual source recording or source summary |
| `observation_id` | Nonempty source event/segment/summary identifier within that recording |
| `reference_side` | `left`, `right`, or explicitly `none`; source ensembles alone may declare `unknown` with a warning |
| `observation_type` | `individual_cycle`, `transfer`, `ensemble_curve`, or `continuous_recording` |
| `task` | Task family |
| `task_id` | Specific task variant |
| `task_info` | JSON object containing source task metadata |
| `phase_ipsi` or `time_s` | The observation's primary index |

The composite identity is `(subject, source_recording_id, observation_id,
reference_side)`. Both reference legs may be represented when the converter
records their identities explicitly. Metadata must remain constant within each
identity; conflicting metadata is rejected instead of splitting one observation
silently. If `subject_metadata` is supplied it must contain JSON objects.

Phase observations have **150 distinct samples on the inclusive 0–100 grid**.
Sample order in the file is arbitrary: checks sort within each identity.
Duplicate, incomplete, and endpoint-excluded grids fail the contract. Time
observations have at least two distinct finite timestamps, sorted within the
identified observation. No resampling is performed.

`ensemble_curve` explicitly denotes a source aggregate, not an independent
stride. An ensemble may have `reference_side: none`. A limb-indexed individual
cycle must declare its left or right reference. Unknown cycle/transfer sides remain
unreviewed. An ensemble with an unknown source side retains that uncertainty as a
contract warning. Source clocks are optional: supply both `source_start_time_s` and
`source_end_time_s` when known. Both may be unavailable; never calculate source
timing from an assumed stride duration.

Legacy exports missing the source recording or observation IDs are **unreviewed
and not publishable through this pipeline**. A `step` counter alone does not
establish source provenance. Revisit the original converter and source data to
recover real identities.

## Quality profiles and missing signals

`common/data_contract.py` exposes `inspect_contract()` and
`assess_observations()` for contributor tools. The same assessment drives
release filtering. It reports signal and observation states as:

| State | Meaning |
| --- | --- |
| `passed` | All applicable checks passed |
| `failed` | A supplied finite signal exceeded an explicit profile bound |
| `missing` | A required signal is absent or partially unavailable |
| `unchecked` | No applicable profile, no required checks, or no range for the signal |
| `invalid` | An invalid structure, nonnumeric signal, or infinite signal |

At signal level, `missing` also identifies optional unavailable signals.
Missing optional signals are visible in coverage and do not automatically
exclude an observation. Present failed or invalid signals do exclude it.
Every required signal must be finite across the whole observation, including
samples between configured phase checks.

Existing YAML profiles remain supported. When they lack required/optional
metadata, **all configured features are required**. Declare narrower requirements
explicitly when the source does not measure every signal:

```yaml
version: '2.0'
tasks:
  level_walking:
    metadata:
      required_features: [knee_flexion_angle_ipsi_rad]
      optional_features: [grf_vertical_ipsi_BW]
      observation_types: [individual_cycle]
    phases:
      0:
        knee_flexion_angle_ipsi_rad: {min: 0.0, max: 1.0}
        grf_vertical_ipsi_BW: {min: 0.0, max: 2.0}
      100:
        knee_flexion_angle_ipsi_rad: {min: 0.0, max: 1.0}
```

The CLI can override the required set using repeated `--required-feature`.
An explicit empty required set never produces passing observations.
Configured phase percentages select the nearest sample on the inclusive grid;
the report records requested phase, actual phase, and sample index.

Ensembles require an explicit `observation_types: [ensemble_curve]` opt-in.
Time data requires task metadata `time_ranges`, mapping signal names to finite
`min`/`max` bounds checked at every sample. Phase ranges are never applied to
time data. No profile or an unmatched task/type yields an empty filtered
artifact and explicit `unchecked` results.

Every supplied signal also records whole-waveform finite/missing/infinite counts,
an exact constant-signal flag, and the largest adjacent-sample change. Constant
signals are informational; some measurements are legitimately constant. Optional
task metadata `waveform_ranges` adds bounds checked at every sample, including
between sparse phase checks:

```yaml
metadata:
  waveform_ranges:
    knee_flexion_angle_ipsi_rad: {min: -0.5, max: 2.5, max_abs_step: 0.3}
```

These illustrative limits require source-specific justification. `min` and `max`
must be supplied together. `max_abs_step` is an optional positive threshold in
signal units per adjacent sample; exceeding it produces an informational review
warning. No spike threshold is invented, and a warning-only rule cannot make an
otherwise unchecked observation pass.

Profiles saved by the tuner are drafts. A top-level `review_status: draft`
blocks release creation. Explicit statuses `reviewed` or `approved` are accepted.
Older profiles with no status remain usable but are labeled `legacy_unspecified`
with a limitation; approval is never inferred.

When ranges depend on population or acquisition conditions, declare task
metadata applicability explicitly:

```yaml
metadata:
  applicability:
    population: [stroke]
    exo_state: [no_exo]
```

These constraints match typed values in `task_info`, `subject_metadata`, or
constant columns with the same names. Every constraint must match. Missing or
mismatched values leave the observation unchecked; another population's ranges
are never substituted. Conflicting metadata sources and duplicate JSON keys are
rejected. Older profiles without applicability metadata retain a prominent
limitation; no healthy-population or exoskeleton-condition match is inferred.

Passing these checks does not establish correct event detection, coordinate
frames, inverse dynamics, force-plate assignments, or source measurements.
Those require converter-specific evidence. There is no universal pass-rate
threshold.

## Release creation

Install the curation dependencies from the repository root:

```bash
python3 -m pip install -r requirements-curation.txt
```

Prepare a provenance JSON file using the actual source, converter, and review
records:

```json
{
  "dataset_id": "my-dataset",
  "release_id": "v1",
  "sources": [
    {
      "uri": "source-recording.mat",
      "path": "source-recording.mat",
      "sha256": "REPLACE_WITH_THE_ACTUAL_64_CHARACTER_SHA256"
    }
  ],
  "converter": {"name": "my-converter", "revision": "actual-source-revision"},
  "review": {
    "reviewer": "actual-reviewer",
    "reviewed_at": "2026-01-01T00:00:00Z"
  }
}
```

Replace the illustrative values with recorded facts. Local source `path` is
optional and resolves relative to the provenance JSON; when present, its
checksum is verified. Remote source URI/checksum pairs remain explicitly
contributor-declared unless the local source is supplied. This command performs
no network downloads. License, citation, and additional provenance fields may
be included and are preserved.

```bash
python3 contributor_tools/build_dataset_release.py identified.parquet \
  --output-dir releases/my-dataset-v1 \
  --provenance provenance.json \
  --ranges contributor_tools/validation_ranges/my-profile.yaml \
  --memory-budget-mb 256
```

The destination must not exist. The command stages all outputs in a sibling
directory and publishes that directory only after successful writes and
checksums. Existing releases are never overwritten.

| Artifact | Contents |
| --- | --- |
| `full.parquet` | Byte-for-byte original source export |
| `filtered.parquet` | Whole eligible observations, sorted by identity and primary index |
| `quality.json` | Contract result, per-signal checks, coverage, failure reasons, and limitations |
| `exclusions.parquet` | Source identities, statuses, and reasons for every excluded observation |
| `manifest.json` | Counts, artifact hashes, source verification state, profile identity, software and processing-code hashes |
| `manifest.sha256` | Checksum of the manifest |
| `provenance.json` | Original provenance declaration |
| `profile.yaml` | Exact profile used, when supplied |
| `README.md` | Human-readable data card rendered from the same results and provenance |

The builder is **admitted in-memory processing, not streaming**. Before loading,
it checks Parquet metadata against a conservative estimated memory budget
(default 256 MiB) and a row cap (default 500,000). Oversized inputs are rejected.
The estimate is not an operating-system memory limit. Keep the default on
shared WSL hosts; move larger releases to a suitable host instead of bypassing
the guard. CLI execution lowers process priority, reads without Arrow
parallelism, and writes 16,384-row groups.

Tiny synthetic fixtures test the complete pipeline without production datasets:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 -m pytest -q tests/test_data_contract.py tests/test_dataset_release.py
```
