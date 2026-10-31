# Converted Datasets

Local working copies of converted locomotion data. **Nothing in this folder is an approved release.** No dataset has completed scientific review, and no file here has been matched byte-for-byte to an online download.

Current evidence for each study: [Status by dataset](../docs/quality/index.html#dataset-status). Remaining work: [reconstruction backlog](../docs/maintainers/backlog.html).

## Three kinds of file

| Kind | Where | What it means |
|------|-------|---------------|
| **Legacy, unreviewed** | `*.parquet` at the top of this folder | Earlier conversions. No source check is bound to these bytes; several have known defects (see the file audit). |
| **Reconstruction job records** | `reconversion_v2/<job>/` | Working directories of many kinds: rebuilt outputs, source-check receipts, plans, censuses, and stopped or superseded runs. An output counts as source-checked only if its job has a completed source-readback receipt, and only for that receipt's scope. None is reviewed or a release. Which outputs qualify: [Status by dataset](../docs/quality/index.html#dataset-status); every job's disposition: [job records](../docs/quality/audits/pm02-job-dispositions.json). |
| **Release bundle** | none yet | Built by `contributor_tools/build_dataset_release.py` with a manifest, hashes, quality results and exclusions. No release bundle exists in this folder yet. |

Filename suffixes describe earlier processing, not quality: `clean` means filtered by a historical, unreviewed range profile; `dirty`, `raw`, or no suffix means the full legacy conversion. A `clean` file is not verified data, and some `clean`/full pairs do not share a parent file.

## Legacy files present here

Status for every file below: **legacy, unreviewed**. Findings for each file are in the [file audit](../docs/quality/index.html#file-status).

| Study | Files | Known issues (examples) |
|-------|-------|-------------------------|
| UMich 2021 | `umich_2021_phase_clean`, `umich_2021_phase_raw`, `umich_2021_time` | Observation keys collide; the `clean` file has 3 of 9 tasks |
| Georgia Tech 2021 | `gtech_2021_phase_clean`, `gtech_2021_time` (+ `oldcmp`, `oldcmp2` comparisons) | Different curves share one identity; velocity scale error |
| Georgia Tech 2023 | `gtech_2023_time` | Participant AB03 mass needs correction; no local phase file |
| Georgia Tech 2024 | `gtech_2024_phase`, `gtech_2024_phase_clean`, `gtech_2024_time`, `gtech_2024_time_bt24` | No source lineage or observation identity; converter mass lookup under review |
| Georgia Tech 2025 | `gtech_2025_da_phase_clean`, `gtech_2025_da_phase_dirty` | No source lineage; converter ankle sign under correction |
| Gait120 | `gait120_opensim_phase`, `gait120_phase`, `gait120_phase_clean` | Stored masses disagree with the source; files are not a filtered pair |
| MBLUE Ankle | `mblue_ankle_phase`, `mblue_ankle_phase_clean` | Keys collide across conditions; stair cycles counted from both leg views |
| StrokePiG | `strokepig_phase`, `strokepig_test_ik` | Clinical affected side not verified |

## Data format

Variable names follow `<joint>_<motion>_<measurement>_<side>_<unit>`, for example `knee_flexion_angle_ipsi_rad`. Legacy files predate the current observation identity columns (`source_recording_id`, `observation_id`, `reference_side`), so never group them by subject, task and step alone. The current contract is in [File format](../docs/reference/index.html).

To learn the format with honest example data, use the synthetic files in [`docs/tutorials/assets/`](../docs/tutorials/assets/) and the [tutorial](../docs/tutorials/index.html):

```python
import pandas as pd
data = pd.read_parquet('docs/tutorials/assets/locohub_example_data.parquet')
```

```matlab
data = parquetread('docs/tutorials/assets/locohub_example_data.parquet');
```
