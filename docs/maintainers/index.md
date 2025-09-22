---
title: Maintainers
---

# Maintainers

Essential commands and paths for day‑to‑day maintenance.

## Do This

### Review Dataset Submissions
Contributors now submit complete packages with documentation. Your role:

1. **Review PR contents**:
   - ✅ Dataset parquet file in `converted_datasets/`
   - ✅ Documentation in `docs/datasets/`
   - ✅ Conversion script in `contributor_tools/conversion_scripts/`

2. **Check validation results**:
   - Review validation pass rates in documentation
   - Ensure ≥80% pass rate or justified exceptions
   - Check for appropriate task coverage

3. **Verify metadata**:
   - Short code is unique
   - Institution and citation provided
   - Subject count and tasks documented

4. **Merge if complete**:
   - All files present
   - Validation acceptable
   - Documentation complete

### Quick Validation Tools
- Test dataset: `python contributor_tools/quick_validation_check.py <dataset_phase.parquet>`
- Filter strides: `python contributor_tools/create_filtered_dataset.py <dataset_phase.parquet>`
- Serve docs locally: `mkdocs serve`

## Where Things Are

- Converters: `contributor_tools/conversion_scripts/`
- Outputs: `converted_datasets/`
- Validation engine: `internal/validation_engine/validator.py`
- Validation ranges: `contributor_tools/validation_ranges/`
- Python API: `user_libs/python/locomotion_data.py`

## Workflows

### Standard PR Review Flow
1. **Contributor submits PR** with dataset + documentation
2. **Review submission** - Check files, validation, metadata
3. **Request changes** if needed (missing info, low validation)  
4. **Merge when ready** - Documentation is already complete!

### Maintenance Tasks
- **Update validation ranges**: Edit YAML → have contributors re-run validation
- **Add new variables**: Update `feature_constants.py` → update converters
- **Fix documentation**: Direct edits to `docs/datasets/*.md` files
- **Archive datasets**: Move old docs to `archived/` subdirectory


## Contributor Tools at a Glance

Quick references for the contributor-facing scripts maintainers should recognize, including the unified submission workflow.

<details>
<summary>`create_filtered_dataset.py` — Filters stride data using the validation engine and writes a cleaned parquet copy.</summary>

```mermaid
flowchart TD
    A[Start CLI] --> B[Parse dataset/ranges/exclusions]
    B --> C{Dataset file exists?}
    C -- No --> Z[Exit with error]
    C -- Yes --> D[Derive output name]
    D --> E[Load dataset with LocomotionData]
    E --> F[Validate requested exclude columns]
    F --> G{Output exists?}
    G -- No --> H[Init Validator with ranges]
    G -- Yes --> I{Overwrite confirmed?}
    I -- No --> Z
    I -- Yes --> H
    H --> J[Filter each task: remove failing strides]
    J --> K[Drop excluded columns and save parquet]
    K --> L[Report pass rate + output]
    L --> M[Return exit code]
```

</details>

<details>
<summary>`prepare_dataset_submission.py` — Unified contributor workflow for validation, plots, and documentation.</summary>

Generates or refreshes everything a contributor needs for a dataset page. The script derives a dataset slug from the parquet file name, stores metadata in `docs/datasets/_metadata/`, writes the Markdown page, and rebuilds the dataset tables that live between the `<!-- DATASET_TABLE_START -->` / `<!-- DATASET_TABLE_END -->` markers in `README.md`, `docs/index.md`, and `docs/datasets/index.md`. Those tables are regenerated from the metadata directory so the public landing pages always list the newest datasets with consistent links.

<details>
<summary>`add-dataset` subcommand</summary>

Primary entry point today. Collects metadata (prompts or file), runs validation, writes dataset docs, persists metadata YAML, regenerates tables, and outputs the submission checklist.

```mermaid
flowchart TD
    A[Start CLI] --> B[Parse dataset and options]
    B --> C{Metadata file supplied?}
    C -- Yes --> D[Load YAML or JSON metadata]
    C -- No --> E[Prompt contributor for fields]
    D --> F
    E --> F[Assemble metadata payload]
    F --> G[Run validator on parquet]
    G --> H{Validation passed?}
    H -- No --> I[Capture issues but continue]
    H -- Yes --> J[Store pass statistics]
    I --> K
    J --> K[Embed validation summary]
    K --> L[Render dataset Markdown + plots]
    L --> M[Write metadata YAML and checklist]
    M --> N[Regenerate dataset tables via markers]
    N --> O[Exit with status]
```

</details>

<details>
<summary>`refresh-validation` subcommand</summary>

Planned follow-up flow for when contributors need to rerun validation after adjusting converters or ranges. Would skip metadata prompts, rebuild plots, update summaries, and refresh tables using the existing metadata.

```mermaid
flowchart TD
    A[Start CLI] --> B[Parse dataset and ranges options]
    B --> C[Run validator and regenerate plots]
    C --> D[Update dataset Markdown with new summary]
    D --> E[Persist metadata stats]
    E --> F[Refresh dataset tables between markers]
    F --> G[Exit with status]
```

</details>

<details>
<summary>`edit-metadata` subcommand</summary>

Intended fast path for metadata-only tweaks. Loads the existing YAML, lets contributors edit fields, saves updates, and offers to chain directly into a validation refresh if data quality changed.

```mermaid
flowchart TD
    A[Start CLI] --> B[Load existing metadata YAML]
    B --> C[Prompt contributor to edit fields]
    C --> D[Write updated metadata and Markdown]
    D --> E[Refresh dataset tables between markers]
    E --> F{Run validation refresh now?}
    F -- Yes --> G[Chain to refresh-validation]
    F -- No --> H[Exit with status]
```

</details>

</details>

<details>
<summary>`interactive_validation_tuner.py` — GUI tool for hands-on validation range tuning.</summary>

Helps contributors diagnose failing variables and author custom range YAMLs. Requires tkinter/display support; useful when datasets target special populations and need bespoke envelopes before re-running `add-dataset`.

```mermaid
flowchart TD
    A[Start CLI] --> B[Check tkinter and display availability]
    B -- Missing --> C[Print setup instructions and exit]
    B -- Available --> D[Launch tuner window]
    D --> E[Load validation YAML and dataset]
    E --> F[Render draggable range boxes]
    F --> G[Contributor adjusts ranges / toggles options]
    G --> H[Preview pass/fail changes]
    H --> I{Save ranges?}
    I -- Yes --> J[Export updated YAML]
    I -- No --> K[Keep editing]
    J --> L[Continue editing or close]
    K --> L
    L --> M[Exit application]
```

</details>

<details>
<summary>`quick_validation_check.py` — Fast validator that prints stride pass rates with optional plot rendering.</summary>

```mermaid
flowchart TD
    A[Start CLI] --> B[Parse CLI options]
    B --> C{Dataset file and ranges file exist?}
    C -- No --> Z[Exit with error]
    C -- Yes --> D[Initialize Validator]
    D --> E[Run validation]
    E --> F[Print pass summary]
    F --> G{Plot flag enabled?}
    G -- No --> H[Exit with status code]
    G -- Yes --> I[Render interactive or saved plots]
    I --> H
```

</details>


## Documentation Website Architecture

Everything on the public site is generated from a small collection of source folders:

```
docs/
├── datasets/
│   ├── _metadata/             # YAML snapshots driving tables & cards
│   ├── validation_plots/      # Exported plot directories (images + index.md)
│   ├── validation_archives/   # Historical copies of ranges/plots (timestamped)
│   └── <dataset>.md           # Dataset landing pages (generated)
├── maintainers/               # Maintainer handbook (this page)
├── reference/                 # Data standard spec and units
├── contributing/              # Contributor step-by-step guide
└── index.md                   # Homepage (contains dataset table markers)
```

Key mechanics to remember:
- MkDocs reads `mkdocs.yml`, which pulls in `docs/` and enables the `mermaid2` plugin for diagrams.
- `prepare_dataset_submission.py add-dataset` is the authoritative writer. It:
  1. Loads or prompts for metadata and writes `docs/datasets/_metadata/<slug>.yaml`.
  2. Runs validation, storing summary text and stats in the metadata dict.
  3. Renders `docs/datasets/<slug>.md`, referencing any generated plots.
  4. Regenerates the dataset tables inside the marker pairs (`<!-- DATASET_TABLE_START -->` / `<!-- DATASET_TABLE_END -->`) in `README.md`, `docs/index.md`, and `docs/datasets/index.md`.
  5. Writes `docs/datasets/validation_plots/<slug>/` (images plus `index.md`) and archives validation YAML when requested.
- Running `mkdocs serve` or `mkdocs build` does not invoke regeneration—it only renders the already-generated Markdown.
- If you hand-edit generated Markdown, mirror the change in the metadata or template; the next `add-dataset` run will otherwise overwrite it.

## Planned `reset_dataset_docs.py`

Purpose: provide a controlled “nuke” for derived documentation so maintainers can test regeneration end-to-end.

Algorithm sketch:
1. **Safety checks**
   - Confirm the current directory is the repo root.
   - Abort if `git status --porcelain` shows staged changes unless `--force` is supplied.

2. **Backup (optional)**
   - For each target Markdown file (`README.md`, `docs/index.md`, `docs/datasets/index.md`), capture the block between the table markers and write it to `docs/datasets/_backups/<filename>.<timestamp>.md` when `--backup` is passed.

3. **Clear derived content**
   - Replace the text between each marker pair with `_Dataset table will be regenerated on next add-dataset run._`.
   - Optional flags: `--wipe-plots` to delete `docs/datasets/validation_plots/*` and `--wipe-archives` for `docs/datasets/validation_archives/*`.

4. **Next steps prompt**
   - Echo the exact `prepare_dataset_submission.py add-dataset --metadata-file ... --overwrite` command needed to rebuild.
   - Remind maintainers to inspect or delete the backup files.

5. **Exit codes**
   - Return `0` on success.
   - Non-zero when markers are missing, backups fail, or safety checks trip.

Until the script exists, perform the same steps manually: remove the table blocks, run `add-dataset` with an existing metadata file, and confirm the tables repopulate from YAML.

## Environment

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
