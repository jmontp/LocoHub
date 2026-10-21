---
title: Contribute a dataset
---

# Contribute a dataset

A contribution includes converted observations and enough evidence to review their identities, units, processing, and exclusions. A high range-check pass rate alone is not an acceptance criterion.

## 1. Establish source provenance and sharing terms

Record the original study citation, source location, data license, participant/task coverage, and source-file hashes. Confirm that the source terms permit the proposed redistribution. Distinguish measured signals, reconstructed signals, and ensemble averages.

Preserve original recording identifiers and mapping decisions. Declare missing metadata instead of inferring it. Existing files that lack trustworthy identities remain legacy / unreviewed until their source lineage can be established.

## 2. Convert a small, representative pilot

Set up contributor tooling from the repository root:

```bash
python -m pip install -r requirements-curation.txt
```

Follow the [version 2.0 data contract](../reference/index.md). Supply explicit observation identities, observation types, and JSON task metadata. Keep missing signals missing, and preserve reference side and source boundaries. Group phase observations using their complete identity before interpolating to the inclusive 150-point grid; never infer cycles by dividing a row count by 150.

Start with a small source subset that covers the intended task and signal types. Review representative source-to-output traces and document:

- source signal → output column, units, signs, and coordinate transformations;
- event detection, cycle boundaries, interpolation, and bilateral mappings;
- filtering and derivative methods, including their order;
- normalization masses, assistance/biological moment definitions, and force-plate assignments;
- unavailable signals, excluded source trials, and protocol limitations.

Use the [synthetic tutorial fixture](../tutorials/index.md) to understand file shape, not to validate biomechanical assumptions. Dataset-specific converters remain under `contributor_tools/conversion_scripts/`; shared implementation belongs under `contributor_tools/common/`.

## 3. Diagnose quality issues and define the profile

Investigate structural failures, missing signals, invalid values, and implausible traces before selecting observations. Fix conversion errors at their source, then regenerate the pilot.

A biomechanical profile is a declared selection rule. Record its intended population and protocol, required and optional features, observation types, thresholds, and evidence. An empirical or manually tuned rule is not automatically a literature norm. A profile intended for individual cycles must explicitly opt in before being used for ensemble curves.

The interactive tuner can help inspect candidate ranges:

```bash
python contributor_tools/interactive_validation_tuner.py
```

Treat ranges initialized from the same dataset as provisional. Keep a change rationale and compare before/after effects by task, subject, and signal. Do not alter a rule solely to make an unexplained failure disappear. The release builder preserves the selected profile; it does not establish the scientific correctness of that profile.

## 4. Prepare reviewed provenance

Create a JSON provenance file. Replace every illustrative value below with reviewed source information; do not claim a reviewer or revision that has not been verified.

```json
{
  "dataset_id": "example-study",
  "release_id": "v1",
  "sources": [
    {
      "uri": "https://data.example.org/study/source.mat",
      "path": "source.mat",
      "sha256": "REPLACE_WITH_THE_64_CHARACTER_SOURCE_SHA256"
    }
  ],
  "converter": {
    "name": "dataset-specific converter",
    "revision": "REPLACE_WITH_THE_REVIEWED_SOURCE_REVISION"
  },
  "review": {
    "reviewer": "REPLACE_WITH_ACTUAL_REVIEWER",
    "reviewed_at": "REPLACE_WITH_ISO8601_TIMESTAMP"
  },
  "license": "REPLACE_WITH_SOURCE_DATA_TERMS",
  "citation": "REPLACE_WITH_ORIGINAL_DATASET_CITATION"
}
```

Local `path` values resolve relative to the provenance file and their hashes are verified. A URI and hash without a local path remain contributor declarations; the builder does not download remote sources. Include processing notes and known limitations in the provenance record. Use a distinct release identifier for any subsequent change.

## 5. Build a release bundle

Use a new output directory:

```bash
python contributor_tools/build_dataset_release.py pilot.parquet \
    --output-dir releases/example-study/v1 \
    --provenance reviewed_source.json \
    --ranges reviewed_profile.yaml \
    --mode phase
```

Choose `--mode time` for continuous time observations or `--mode ensemble` for ensemble curves. Use repeatable `--required-feature COLUMN_NAME` only when explicitly defining the intended required feature set. Record that choice with the review rationale.

If no profile is appropriate, omit `--ranges`. Unmatched observations remain **unchecked** and the profile-filtered artifact is empty; absence of checks never produces passing observations.

The builder writes `full.parquet`, `filtered.parquet`, `quality.json`, `exclusions.parquet`, `manifest.json`, `manifest.sha256`, `provenance.json`, and a profile snapshot when supplied. It rejects an existing output directory and structural/identity violations. See [release evidence](../reference/index.md#release-evidence) for each artifact's meaning. Maintainer implementation details are recorded in `contributor_tools/DATA_CONTRACT.md` in the repository.

The builder admits bounded inputs before loading them in memory. Defaults are `--memory-budget-mb 256` and `--max-input-rows 500000`; this is not a streaming pipeline or a hard process-memory cap. If input exceeds these limits, prepare a smaller reviewable shard or use a separately planned resource budget. Do not casually increase limits or run simultaneous full-dataset jobs on a shared machine.

## 6. Review and submit

- Reconcile full/filtered observation counts with `quality.json` and exclusions. Check which required signals were missing or unchecked.
- Inspect exclusions across subjects and tasks; filtering may change the represented population or conditions.
- Verify the profile snapshot, source hashes, converter revision, source citation/license, and known limitations.
- Include source-to-output evidence for a representative pilot and any known exceptions.
- Submit converter changes, provenance, profile, and release evidence for maintainer review. Preparing a bundle does not grant independent approval.

Keep historical catalog statistics separate from new release results. Updating a web page does not revalidate an artifact. Do not paste console summaries into a report as a substitute for the machine-readable evidence.

## Publishing documentation

The existing documentation manager maintains legacy catalog pages and historical reports. Existing `clean`/`dirty` filenames and download links are retained for traceability. A new release must be labeled with its real review status, artifact identifiers, and limitations before it is linked publicly.

Preview documentation locally and run the small documentation tests:

```bash
python -m pytest tests/test_data_documentation.py
python docs/build.py --output site
python -m http.server 8000 --directory site
```

See the [maintainer review checklist](../maintainers/index.md) for the release decision and the [catalog](../datasets/index.md) for currently available artifacts.

The published website is authored HTML under `docs/`. This Markdown remains an internal reference. The legacy documentation generator does not publish or update the HTML site.
