---
title: Data contract and quality evidence
---

# Data contract and quality evidence

LocoHub releases standardize files and preserve evidence about their origin and processing. Researchers consume these files directly. The current contract is **version 2.0**; historical files in the catalog may follow older conventions and remain **legacy / unreviewed** until their identities and provenance have been established.

## Observation identity

An observation is the unit whose samples must remain together during validation and filtering. Its identity is the combination of:

| Column | Meaning |
|--------|---------|
| `subject` | Participant identifier scoped consistently across the dataset. |
| `source_recording_id` | Original recording or trial identity, preserved across derived observations. |
| `observation_id` | Stable identifier for a cycle, transfer, ensemble curve, or continuous recording. |
| `reference_side` | `left`, `right`, or `none`; identifies the limb defining ipsilateral signals when applicable. Source ensembles may retain `unknown`, with a recorded warning. |

These fields must be explicit, nonempty, and traceable to the source. A legacy `step` label alone does not establish observation identity. Row order and blocks of 150 are not substitutes for source identities. Do not invent a recording identity merely to pass validation.

`observation_type` declares what the observation represents:

| Value | Meaning and analysis implication |
|-------|----------------------------------|
| `individual_cycle` | One segmented cycle. Repeated cycles from a participant are not independent participants. |
| `transfer` | One segmented transfer or action with documented boundaries. |
| `ensemble_curve` | An aggregate curve. Do not count it as an individual stride or treat its samples as independent measurements. |
| `continuous_recording` | A continuous time observation with increasing timestamps. |

Bilateral views may share a source recording. Keep related observations together when defining training/test splits or assessing participant-level uncertainty.

## Metadata

Every observation requires `task`, `task_id`, and `task_info` alongside its identity and observation type. Metadata must remain constant within the observation.

- `task` identifies the activity family, for example `level_walking` or `stair_ascent`.
- `task_id` identifies a specific protocol variant within the dataset.
- `task_info` is a JSON object, serialized as a JSON string in CSV/Parquet when needed: `{"speed_m_s":1.2,"incline_deg":0,"treadmill":true}`.
- Optional `subject_metadata` uses the same JSON representation. Preserve unknown demographic values as unknown; do not infer them.
- Optional `source_start_time_s` and `source_end_time_s` are supplied together and remain constant within the observation. Known boundaries must be finite, with end greater than start. Transfers and ensembles may preserve both boundaries as unknown; one unknown boundary alone is invalid. Never invent durations for normalized source curves.

Older releases may contain comma-separated `key:value` strings. That legacy representation requires explicit conversion and review before a version 2.0 release. Missing values are not zero and are not evidence of a negative finding.

Task definitions live in `contributor_tools/common/task_registry.py`; variable definitions live in `contributor_tools/common/feature_constants.py`. These are internal contributor tools, not a public analysis SDK. Document population and assistance conditions alongside task metadata; a matching task name alone does not make studies comparable.

## Sample indices

| Mode | Index | Required structure |
|------|-------|--------------------|
| Phase | `phase_ipsi` | Exactly 150 distinct samples matching the inclusive grid `linspace(0, 100, 150)` when ordered within each observation. |
| Ensemble | `phase_ipsi` | The same grid, with `observation_type="ensemble_curve"`. |
| Time | `time_s` | At least two distinct finite timestamps, sorted within each observation for analysis. |

The phase grid includes both 0% and 100%; these endpoints describe consecutive boundaries. Event definitions, interpolation, and original durations belong in provenance. For non-gait actions, document what the start and end events mean. Phase normalization changes the sampling representation and does not retain all original time samples.

Time mode supports recordings without defensible cycle boundaries. A continuous recording must not be relabeled as an individual cycle merely to use phase tooling. File rows may be interleaved; checks sort by index within each identity. Phase indices must be unique within an observation; time observations must not repeat timestamps.

## Signals, units, and missing values

Use explicit column names with unit and side tokens. Examples:

| Signal | Example column | Stored unit |
|--------|----------------|-------------|
| Joint angle | `knee_flexion_angle_ipsi_rad` | radians |
| Angular velocity | `knee_flexion_velocity_ipsi_rad_s` | radians/second |
| Mass-normalized moment | `hip_flexion_moment_ipsi_Nm_kg` | Nm/kg |
| Ground reaction force | `grf_vertical_ipsi_BW` | body weights |
| Center of pressure | `cop_anterior_ipsi_m` | meters |
| Segment orientation | `pelvis_sagittal_angle_rad` | radians |

`ipsi` is the reference limb and `contra` is the opposite limb. Contralateral event timing must come from the recorded protocol or a documented derivation; it is not universally a 50% shift. Preserve whether moments represent total, biological, or assistance moments. Record the coordinate frame, signs, normalization mass, force-plate assignment, filtering, and derivative method in conversion provenance.

Unavailable signals stay missing. Zero-filled missing features can create false evidence that a signal was measured. A column existing in a file does not establish coverage across every task or observation. Inspect finite-value coverage and required/optional signal declarations before analysis.

## Quality states

| State | Interpretation |
|-------|----------------|
| `passed` | Applicable checks ran and their conditions were satisfied. |
| `failed` | Applicable checks ran and at least one condition was not satisfied. |
| `missing` | Signal data were unavailable; required and optional signals are identified separately. |
| `unchecked` | No applicable profile/check ran, or no mandatory checks were configured. |
| `invalid` | Structural or nonfinite data prevented a trustworthy result. |

Structural integrity, signal coverage, and biomechanical profile conformance are separate evidence. A profile only checks its configured features and phases or time ranges. It does not establish correct source measurements, coordinate transforms, event detection, or clinical applicability.

A profile declares its intended tasks, observation types, required/optional features, thresholds, and supporting rationale. Empirical or manually tuned ranges must be described as such. Call them literature-derived only when traceable sources support the rules. Ensemble curves need a profile that explicitly includes `ensemble_curve`.

Profiles can restrict applicability using recorded metadata such as population or assistance condition. Missing or mismatched applicability metadata leaves an observation unchecked. Profiles without those restrictions disclose that limitation. Whole-waveform diagnostics record missing and infinite values, constant signals, and the largest adjacent-sample change. Optional `waveform_ranges` check bounds across every sample; a configured `max_abs_step` produces a review warning, not an automatic exclusion. See the contributor contract guide in the repository for profile syntax.

No applicable profile means **unchecked**, not passed. A dataset with unchecked observations may retain full converted data and evidence, but those observations are not eligible for the profile-filtered artifact. A low pass rate warrants investigation of both conversion and applicability; increasing thresholds is not itself a correction.

## Release evidence

A prepared release directory contains these artifacts:

| Artifact | Purpose |
|----------|---------|
| `full.parquet` | Byte-identical copy of the admitted converted input file. |
| `filtered.parquet` | Whole observations eligible under the specified profile; may be empty. |
| `quality.json` | Structural checks, signal coverage, observation states, and reasons. |
| `exclusions.parquet` | Identities and reasons for observations excluded from the filtered artifact. |
| `manifest.json` | Release identity, contract version, artifact hashes, counts, and provenance references. |
| `manifest.sha256` | Checksum of the manifest itself. |
| `provenance.json` | Source identifiers/hashes, converter revision, contributor review, and processing notes. |
| `profile.yaml` | Snapshot of the rule profile, when one was supplied. |
| `README.md` | Generated data card describing counts, artifacts, and limitations. |

**Full converted** does not mean original raw data. **Profile-filtered** does not mean universally clean. Report both the selected variant and the profile used. Historical `clean`/`dirty` filenames do not substitute for this evidence.

Building a bundle records checks and contributor review; it does not automatically grant independent maintainer approval. Source URIs and hashes without accessible local source files remain contributor declarations. Reconcile release artifacts with the original study and inspect limitations before publication.

The interactive tuner saves draft profiles with a rationale and an audit sidecar recording hashes, changes, and decision counts. Draft profiles cannot be used to publish a release bundle; review the rules and their evidence before recording an approved profile.

New release directories are immutable: changes to data, profiles, or provenance produce a new directory and identifier. Existing catalog downloads remain legacy / unreviewed unless the corresponding files are explicitly reprocessed and reviewed. This documentation update does not revalidate them.

## Related workflows

- [Load and inspect the complete example](../tutorials/index.md)
- [Find datasets](../datasets/index.md)
- [Prepare a release](../contributing/index.md)
- [Review a release](../maintainers/index.md)
