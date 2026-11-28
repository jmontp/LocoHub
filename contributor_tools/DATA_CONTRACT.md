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
unreviewed. For side-`none` observations, `_ipsi_`/`_contra_` columns name roles,
not anatomical sides; the converter provenance must state how the ipsi role was
chosen. An ensemble with an unknown source side retains that uncertainty as a
contract warning. Source clocks are optional: supply both `source_start_time_s` and
`source_end_time_s` when known. Both may be unavailable; never calculate source
timing from an assumed stride duration. An ensemble has no single source event,
so both of its source clocks must be unavailable; any recorded clock value fails the contract.

Legacy exports missing the source recording or observation IDs are **unreviewed
and not publishable through this pipeline**. A `step` counter alone does not
establish source provenance. Revisit the original converter and source data to
recover real identities. Text that a missing value becomes after string
conversion (`nan`, `-nan`, `None`, `null`, `<NA>`, `NaT`, `<missing>`,
`<undefined>`, `N/A`, `#N/A`, `#NA`, `1.#QNAN`, in any case, including
full-width and zero-width variants) is not a source identity or `task_id`. `NA`
alone remains a valid identity.

Composite identities are split only on `/ \ : | ; ,`. A part fails when it is
one of `nan`, `-nan`, `<NA>`, `<missing>`, `<undefined>`, `N/A`, `#N/A`, `#NA`,
`1.#QNAN` (same folding), or when it is blank (whitespace only), e.g.
`gt21:AB01/NaN/1` or `AB01/ /t1`. These are deliberately accepted:
`None`, `null` and `NaT` parts, which can be real labels (`AB01/none/t1`);
empty parts, which URLs, drive letters and absolute paths produce
(`https://…`, `C:\data`, `AB01//t1`); and anything joined by `_`, `-`, `.` or
spaces, which is not split (`nan_trial`, `NaT-7`, `AB01_NaN`).

The contract names each affected observation, and no observation in that file is
eligible. Categorical identity columns are assessed like plain strings.

## Signs and frames

The authoritative sign table and diagram are in
[`docs/reference/index.html#signs-and-frames`](../docs/reference/index.html#signs-and-frames)
(Markdown source: `docs/reference/index.md`).

Decided: D-UM21-C03-1 = B (2026-10-31; changed from C, answered 2026-10-30,
under which knee flexion and the knee flexor moment were negative) and
D-GT21-C01-1 = B (2026-10-30):

- Frame: +x walking direction, +y up, +z the person's right side (out of the
  page when the person faces right). Both legs use this frame for sagittal signals.
- Segment angles (pelvis, trunk, thigh, shank, foot) are counterclockwise
  positive about +z: pelvis anterior tilt **−**, trunk leaning back +,
  thigh/shank distal end forward +, foot toes up +.
- Joint angles and their derivatives are positive in their named direction:
  hip flexion +, knee flexion +, ankle dorsiflexion +. OpenSim gait2392
  `knee_angle` is flexion-negative, so LocoHub knee = −`knee_angle`.
- Moments are internal, on the distal segment, and positive in their named
  direction: hip flexor +, knee flexor +, ankle dorsiflexor + (plantarflexor −).
  Power is moment × joint angular velocity; generation is positive.
- Sideways force and COP are positive outward for each leg (left leg mirrored).

LocoHub definitions that follow from the rule and existing usage (not separate
decisions):

- Ground reaction force is the force applied by the ground to the person:
  vertical up +, anterior forward +.
- Segment zero references: thigh and shank from straight down; foot and pelvis
  from forward horizontal; trunk zero undefined. Composition (thigh = pelvis +
  hip, shank = thigh − knee, foot = shank + ankle) holds only up to each
  dataset's zero offsets, which dataset notes state.
- Foot-flat zero (D-REF-6, 27 November 2026; GT23 v12, GT21 v2, UM21 v6): foot and ankle
  angles carry a per-person shift so a flat foot on level ground reads 0, and the
  foot-frame centre of pressure (forward, up) is turned by the same angle; see
  docs/reference/index.md and the package's limitations.json.
- Frontal and transverse signs are not yet adopted; converters keep and
  document the source sign.

Converters apply these signs only from independent source evidence (publisher
documentation, model files, measured events), never from curve appearance or
range pass rates, and record each mapping in provenance. Evidence:
`docs/quality/audits/um21-c03-conventions.json`,
`docs/quality/audits/gt21-c01-conventions.json`,
`docs/quality/audits/sign-conventions-source-survey.json`.

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

Each assessed observation reports its identity and `time_lineage`: the index
column, its earliest and latest values after sorting, and `source_start_time_s`/`source_end_time_s`.
Unavailable, nonconstant, or nonfinite values are reported as null, never computed.

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
blocks release creation. Explicit statuses `reviewed` or `approved` are accepted
only with a top-level `review` record naming `reviewer` and a quoted,
timezone-stamped `reviewed_at`. `scope` is optional; when it is absent, the
release records a limitation.
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
A profile marked `reviewed` or `approved` must declare a nonempty applicability
block for every task; `profile_applicability_gaps()` lists the tasks that do not.

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
    "reviewed_at": "2026-01-01T00:00:00Z",
    "scope": "what the reviewer actually checked"
  }
}
```

Replace the illustrative values with recorded facts. Local source `path` is
optional and resolves relative to the provenance JSON; when present, its
checksum is verified. Remote source URI/checksum pairs remain explicitly
contributor-declared unless the local source is supplied. A remote URI verified
through a local copy is recorded as `verified_local` with a limitation that the
URI itself was not downloaded. This command performs no network downloads.
License, citation, and additional provenance fields may be included and are
preserved.

The `converter` and `review` fields are contributor declarations. The manifest
copies them verbatim and lists them in `declared_by_contributor`, and the data
card labels them as declared. `review.scope` is optional, but when given it must
be a nonempty string. When it is absent, the release records a limitation that
the scope of the review is not stated.

```bash
python3 contributor_tools/build_dataset_release.py identified.parquet \
  --output-dir releases/my-dataset-v1 \
  --provenance provenance.json \
  --ranges contributor_tools/validation_ranges/my-profile.yaml \
  --memory-budget-mb 256
```

The destination must not exist. The command stages all outputs in a sibling
directory and publishes that directory only after successful writes and
checksums. Existing releases are never overwritten. It refuses a profile marked
`reviewed` or `approved` if it lacks that review record, or if any task lacks an
applicability block naming more than the task or observation structure
(`task`, `task_id`, `observation_type` and the identity columns alone are not
enough).
Any profile whose `review` holds a non-JSON value, such as an unquoted YAML date,
is refused. The data card labels the profile's review status as the profile's own
claim.

Publication is an atomic no-replace rename of the staging directory. On
filesystems that reject that rename, such as WSL drvfs mounts like `/mnt/s`, the
builder falls back under the same lock: it creates the destination with an
exclusive `mkdir`, writes `RELEASE_INCOMPLETE.txt` first, hard-links or
exclusively copies each file without replacing any file (manifest files last),
checks every published file's hash against the manifest, and then removes the
marker. Errors remove the files placed. After a hard interruption the marker and
the sibling `.<name>.release.lock` file remain. Treat any release directory containing
`RELEASE_INCOMPLETE.txt` as unusable, and delete it and the lock by hand before
rebuilding.

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
The read goes through the open file whose footer matched the admission (via
/proc on Linux), so an input replaced after admission is rejected unread.
The estimate is not an operating-system memory limit. Keep the default on
shared WSL hosts; move larger releases to a suitable host instead of bypassing
the guard. CLI execution lowers process priority, reads without Arrow
parallelism, and writes 16,384-row groups.

Tiny synthetic fixtures test the complete pipeline without production datasets:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 -m pytest -q tests/test_data_contract.py tests/test_dataset_release.py
```

## Release package

One layout for every dataset's local review package. `contributor_tools/common/release_package.py` writes it by streaming
(row-group by row-group); a small per-dataset adapter supplies the inputs. `run_gt23_r01_bundle.py` is the first adapter
(Georgia Tech 2023); the UMich 2021 package v5 (phase and time tables) and the Georgia Tech 2021 package v1 use the same layout. A package is written to a new
directory and never replaces an existing one. `scientific_approval` is always false; a package is a review copy, not a
publication.

```text
<release>/
  full_phase.parquet        full_time.parquet          every exported observation
  filtered_phase.parquet    filtered_time.parquet      full minus the observations the assessment failed, nothing else
  exclusions.csv            every exclusion, with observation id, stage and reason
  assessment.jsonl          the structured assessment, one line per observation
  limitations.json          each known limitation with counts
  dataset_index.json        files, counts, recordings, signal states, held columns
  phase_preview.json        mean and SD per phase sample of the filtered phase file
  test_summary.json         the builder's checks, with expected and observed values
  README.md                 plain-words description
  evidence/                 dataset-specific CSV evidence (optional, listed in the manifest)
  manifest.json             sha256 and bytes of every other file, counts, inputs, resources
  manifest.sha256           sha256 of manifest.json
```

A dataset without a time table omits `*_time.parquet`; `manifest.json` lists the tables that exist (`tables`).

**Tables.** Every table file holds the source columns of the observation contract unchanged plus six string columns:
`source_export` (which source part supplied the row), `quality_status` (`no_failure_found` or `failed`; filtered files hold
only `no_failure_found`), `failed_limits` (JSON list), `limitations` (JSON list), `lineage_id` and `assessment_id` (the same
value on every row of every file). Phase observations keep exactly 150 samples on the inclusive 0-100 grid; time
observations keep their source clock. Nothing is resampled, filled or re-labelled. Full and filtered write identical
column lists. Row groups are 12,000 rows.

**Replacement.** An adapter may name source recordings that a later part replaces (for example a corrected re-export). The
replaced rows are dropped from the earlier part, the replacing part may contain only those recordings, and every replaced
observation is accounted for in the checks.

**assessment.jsonl.** One JSON object per observation with `observation_id`, `reference_side`, `table`, `observation_type`,
`subject`, `source_recording_id`, `task`, `task_id`, `rows`, `status` (`failed` removes the observation from filtered;
anything else keeps it), `failed_limits`, `failed_channels`, `failed_samples`, `limitations`, `flight`, `attributes`,
`held_signals` (column to reason), `channel_states` (state to columns, using the states of the table above), plus
`in_full_variant` and `in_filtered_variant`. A missing or unchecked signal appears here as such; it is never evidence of
passing.

**exclusions.csv.** Columns: `exclusion_id, observation_id, subject, source_recording_id, reference_side, stage, kind,
reason_code, reason, decision, in_full_variant, in_filtered_variant, task, task_id, start_s, end_s, detail`. `stage` is one of
`upstream_not_released` (left out before the export table: source or export exclusions, source windows not exported),
`release_membership` (left out of both variants at packaging) and `filtered_variant_only` (in full, left out of filtered:
the assessment failures, which the builder adds itself). `kind` is the dataset's own name for the class. Every observation,
segment or window that is not in a variant is listed once.

**limitations.json.** `limitations` (each with `id`, `title`, a plain statement and counts: observations by type,
recordings, participants, how many remain in filtered, how many failed), `unchecked_signal_families` and
`unchecked_columns_by_assessment`.

**manifest.json.** `schema` (`locohub.release_package/1`), `dataset_id`, `release_id`, `stage`, `tables`, `binding`, `counts`,
`inputs_sha256` (every source file read, each checked against its producing receipt before the build), `bound_files_sha256`
(code, receipts and handoffs the launcher spec binds), `files` (sha256 and bytes of every file except the manifest) and
`resources` (peak RSS, address-space limit, niceness, wall time, row-group sizes). `binding` holds the sha256 of each table
file, `exclusions.csv` and `assessment.jsonl`, the counts, `lineage_id` and `assessment_id`. The same `binding` object is
copied into `dataset_index.json`, `phase_preview.json`, `test_summary.json` and `limitations.json`; a reader checks that all
five agree. `lineage_id` hashes the source files and bound files (not the builder), so the full and filtered variants and
any later rebuild from the same inputs share it; `assessment_id` hashes the assessment files.

**Checks.** `test_summary.json` always records: grid and order of every observation, identical columns, the written
observations equal the assessed ones with their row counts, full = filtered + failed with no gap or overlap, filtered rows =
full rows minus the failed rows, every failed observation listed in `exclusions.csv`, no finite value in held columns, one
lineage and assessment id on every row, and one assessment line per observation. Adapters add their own (for example
expected totals from the verified source chain).

**Memory rules.** One numerical worker through the guarded launcher; one table at a time, so two writers are open at once
(an open writer keeps about 80 KB of metadata per row group); source files are read in batches of at most 3,000 rows with
Arrow threads off; only compact assessment entries stay resident. The 256 MiB / 500,000-row admission of
`build_dataset_release.py` is unchanged and is not raised; the streaming builder is for exports above it.

**Adapter.** A subclass of `ReleaseAdapter` provides the table parts and the replacements, the assessment entries, the
source exclusions, optional evidence tables, the limitation entries, README sections, extra checks and the input hashes.
Nothing else is per dataset.

**Relation to the other two builders.**

| `build_dataset_release.py` (in-memory) | UMich 2021 bundle `um21_r01_review_v2` (legacy layout) | Release package |
| --- | --- | --- |
| `full.parquet` (source export, byte for byte) | `full.parquet` | `full_phase.parquet`, `full_time.parquet` |
| `filtered.parquet` | `filtered.parquet` | `filtered_phase.parquet`, `filtered_time.parquet` |
| `exclusions.parquet` | `exclusions.csv` (`recording`, `stage`, `reason_code`) | `exclusions.csv` (`source_recording_id`, `stage`, `kind`, `reason_code`) |
| `quality.json` | `assessment_amendments.jsonl`, `held_signals.csv` | `assessment.jsonl` (held columns and states per observation) |
| limitations inside `manifest.json` and `quality.json` | in the handoff | `limitations.json` |
| `manifest.json`, `manifest.sha256` | same | same, with `binding` and per-file bytes |
| `README.md` data card | short README | plain-words README |
| none | `dataset_index.json`, `phase_preview.json`, `test_summary.json` | same names, same `binding` |

The in-memory builder, its tests and the older UMich 2021 bundle (`um21_r01_review_v2`) keep their layouts. The UM21 review
page (`build_dataset_review_page.py`) now reads the package layout (`um21_r01_package_v5`, which has a phase table and a
time table with ground force); the legacy-bundle reading of `held_signals.csv` stays only for older bundles.
