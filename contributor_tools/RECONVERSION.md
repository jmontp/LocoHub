# Bounded source reconversion

The workers write **unreviewed staging artifacts** under the ignored
`converted_datasets/reconversion_v2/` directory. They never overwrite existing
datasets, publish a release, or claim scientific approval from a schema check.
Each recording runs in its own process; the batch driver never concatenates the
whole dataset.

## Run one recording

From the repository root:

```bash
python3 contributor_tools/reconvert_recording.py \
  --dataset strokepig \
  --source-root /mnt/s/locomotion_data/50_StrokePiG \
  --subject TVC03 --recording BWA6_ik.mot \
  --memory-mib 1536
```

For GT24, supply the actual collection source explicitly. The source root is the
`Parsed` folder that directly contains subject directories:

```bash
python3 contributor_tools/reconvert_recording.py \
  --dataset gt24 \
  --source-root /mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Phase3_Parsed/Parsed \
  --source Phase3 --subject BT24 --recording normal_walk_1_1_1-2_on \
  --output-root converted_datasets/reconversion_v2/gt24_pilot \
  --memory-mib 1536
```

The GT24 recording name must exist in the selected source directory. Inspect
directory names first; the example does not create or infer a trial.

## Serial batch and resource controls

```bash
python3 contributor_tools/run_reconversion_batch.py \
  --dataset strokepig \
  --source-root /mnt/s/locomotion_data/50_StrokePiG \
  --output-root converted_datasets/reconversion_v2/strokepig_serial_20261020 \
  --memory-mib 1536 --delay-seconds 2 --run
```

Omit `--run` to write only the source inventory. Optional `--subjects` and
`--max-recordings` restrict the plan. Reusing a batch directory requires the same
source plan.

- Exactly one conversion subprocess runs at a time, at Linux nice level 19.
- Numeric libraries and Arrow use one thread.
- Each worker has a hard 1536 MiB virtual-address-space limit by default.
  An explicitly requested larger budget may be at most 10 GiB and 80% of total WSL RAM. Defaults remain 1536 MiB.
- Before each worker, the batch waits until `/proc/meminfo` reports enough available
  memory for its entire address-space cap plus a 2 GiB reserve. During conversion,
  a monitor stops only its own worker process group if available memory drops
  below 1.5 GiB, the disk floor is crossed, or the worker times out. A two-second inter-recording delay is the default.
- A fixed, non-bypassable 5 GiB free-space guard checks the mounted output volume
  before scientific imports or output creation. Low disk capacity stops the batch;
  it does not trigger deletion or automatic retries. Under WSL, native filesystem
  free space is insufficient evidence because the virtual disk can exceed its
  Windows backing volume. The currently authorized output remains the repository's
  `converted_datasets/reconversion_v2` directory on the mounted S drive.
- A worker defaults to rejecting source inputs above 64 MiB (explicitly configurable up to 512 MiB) or a conservative
  `256 MiB + 16 × source bytes` working-memory estimate above its cap.
- Workers time out after 180 seconds by default. Failures are logged individually;
  three consecutive worker/schema failures stop the queue with
  `batch_status: stopped_incomplete`. Isolated failures are retained while subsequent
  recordings continue. These controls can reject an input and do not
  guarantee that every converter fits the limit.

No MATLAB, OpenSim scaling, IK optimization, or inverse-dynamics pipeline is
launched. StrokePiG uses the existing source `.mot` kinematics and optional C3D
forces. Unsupported/missing signals remain missing.

## Artifacts and resumption

Each recording directory contains:

- `phase.parquet`, when the converter emitted observations.
- `quality_unreviewed.json`, with identity/schema results, diagnostic decisions,
  and missing signal columns. Without `--ranges`, observations stay unchecked.
- `conversion_manifest.json`, with exact source paths/sizes/SHA-256 hashes, source
  converter/dependency hashes, library versions and capabilities, profile evidence,
  resource use, and output checksums.
- `failed.json` if conversion failed after the output directory was created.

The batch additionally writes `source_inventory.json`, per-recording logs,
`recording_results.jsonl`, and `batch_summary.json`. Schema failures are explicitly
quarantined in the summary; `schema_valid_rows` excludes them.

Inspect `batch_summary.json` and the current log to monitor progress. To stop
cleanly after the active recording, create a file named `STOP_AFTER_CURRENT` in the
batch output root. The batch will also honor it while waiting for memory. Remove
that file before deliberately resuming. A queue exits successfully only after
processing the whole plan without worker/schema failures, so a second dataset can
be chained with shell `&&` without running after an incomplete first batch.

Standalone `--resume` and batch resumption accept an existing recording only when
all source hashes, converter/dependency hashes, profile presence/hash, critical
library versions/capabilities, and output hashes match. Changed scientific inputs,
an interrupted directory, or modified artifacts require a **new output root**.
Existing outputs are not silently regenerated or reused. Updating converter code
during a running batch can produce different dependency hashes across recordings;
finish or stop at a recording boundary before changing it.

The completed StrokePiG batch and GT24 pilot are immutable outputs from the worker
code recorded in their manifests. Subsequent disk-guard changes altered the worker
hash, so current `--resume` intentionally rejects those earlier run directories.
Do not rerun completed StrokePiG merely because a safety guard changed. Use a new
output root for any later conversion under the updated code.

## Local source coverage and review limits

As inspected on 2026-10-20, `/mnt/s/locomotion_data/50_StrokePiG` contains 50
subject folders. Forty-six original precomputed IK recordings are available
across 16 subjects. Thirty-four subject folders have no original IK `.mot` file
and therefore require separately coordinated IK processing before this workflow
can cover them. Original `BWA6`, `BWA_6`, `BWA-6`, and lowercase names are retained;
the two `TVC03/BWA6_test*` reconstructions are excluded as alternate processing of
an existing acquisition.

GT24 parsed CSV sources, GT23 raw data and segmentation sources, and 120 Gait120
subject folders are also present locally. GT23's current converters require
coordinated native MATLAB execution. Gait120's OpenSim workflow requires a separate
resource and provenance review. UM21, GT21, and UM24 source data were not found in
the inspected local source root; existing standardized outputs cannot substitute
for their missing sources.

A later read-only storage audit found possible original sources inside this
repository: `contributor_tools/conversion_scripts/Gtech_2021/CAMARGO_ET_AL_J_BIOMECH_DATASET/`
and `contributor_tools/conversion_scripts/Umich_2021/{Normalized,Streaming}.mat`.
Their contents and completeness have not been checked. Preserve these files and
inspect them before treating GT21 or UM21 reconversion as blocked on missing data.

The metadata-only inventory counted the following supported source files; archives
and unrelated files were excluded. File presence does not establish release
completeness.

| Source tree | Local subjects | Coverage counted | Bytes |
| --- | ---: | --- | ---: |
| GT24 Phase1And2 Parsed | 15 | 1,669 trial folders; 25,035 CSV files | 44,929,907,441 |
| GT24 Phase3 Parsed | 10 | 752 trial folders; 11,280 CSV files | 21,279,062,878 |
| GT23 RawData | 12 | 6,357 CSV; 549 MOT; 537 TRC; 489 MAT | 75,560,466,277 |
| GT23 Segmentation | 12 | 1,776 MAT | 1,170,385,468 |
| Gait120 | 120 | 8,880 MOT; 7,001 TRC; 240 MAT | 18,175,204,515 |
| StrokePiG | 50 | 200 C3D; 48 MOT; 67 TRC; 51 MP | 578,486,829 |

GT24 has 22 unique local subject identifiers across the two source trees; source
phase is part of every recording identity. One StrokePiG folder (TVC24) contains
both its own and another subject's `.mp` file. The metadata parser selects only a
file whose embedded subject identifier matches the source subject folder.

The first real pilot, StrokePiG TVC03/BWA6, emitted three identified observations
(450 rows), passed the structural contract, and remained unchecked. Peak resident
memory was 559,300 KiB, with a 1536 MiB address-space cap; elapsed worker time was
2.39 seconds. This establishes small-recording feasibility only.

The completed serial StrokePiG run is at
`converted_datasets/reconversion_v2/strokepig_serial_20261020/`: **46/46 recordings,
136 observations, 20,400 rows**, with all output observations satisfying the
structural contract and no worker failures. Peak worker RSS was 288,348 KiB
(about 282 MiB). All 136 observations remain **unchecked and unreviewed**, because
no diagnostic profile was selected. Coverage is the 16 subjects with available
original IK files, not the entire 50-folder raw collection.

The GT24 walking pilot is at
`converted_datasets/reconversion_v2/gt24_pilot_20261020/gt24/Phase3/BT24/normal_walk_1_1_1-2_on/`:
17 observations, 2,550 rows, and a valid structural contract. The default diagnostic
profile reported zero passed, one failed, and 16 missing. The failing observation
exceeded a contralateral anterior COP range; these are diagnostic decisions, not
release approval. Eight unavailable signal columns include unresolved horizontal
GRF, absent vertical COP, and unsupplied ankle assistance. Input evidence covered
17,197,878 bytes; elapsed conversion time was 2.73 seconds, peak RSS 559,300 KiB.
The three pilot artifacts occupy about 2.4 MB.

**GT24 bulk conversion is blocked by storage and has not been started.** The S
drive had approximately 2.7 GiB free and C approximately 3.3 GiB when checked;
Ubuntu's WSL disk is backed by C. Its much larger reported virtual capacity is not
usable backing capacity. No alternate drive has been authorized. Existing data was
not removed. The two GT24 source trees contain 2,421 trial folders, and even the
two-second scheduling gaps alone would take about 81 minutes.

## GT24 source conventions

The local source documentation is
`/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/readme.txt`, included by SHA-256 in
GT24 conversion manifests. Its line 37 states “y-axis is vertical”; lines 41–42
describe filtered total moments and total-minus-exoskeleton biological moments in
Nm/kg. Lines 57–85 distinguish masses with and without the worn exoskeleton.
Lines 667–675 describe insole COP in “OpenSim left and right foot frames”.

The converter retains the source moment normalization and records
`weight_basis` and moment semantics in JSON metadata. A source model including the
exoskeleton is not interchangeable with participant-only mass for cross-dataset
normalization. Exact per-trial model-mass reconciliation remains a review item.
Derived velocities are computed on the inclusive normalized time grid, and
segment angles remain estimates from virtual-IMU integration with converter
initialization.

The readme does not establish an anatomical forward/lateral transform for every
trial. The converter therefore preserves signed source horizontal forces as
`source_grf_global_{x,z}_{ipsi,contra}_N` and leaves canonical horizontal GRF
missing. It never chooses a sign from an expected push-off or medial-force shape.
Vertical COP is missing because the insole source supplies only two COP
coordinates. Missing exoskeleton channels remain missing; explicit source-labeled
`no_exo` conditions alone establish known zero assistance.

Clinical affected side remains unknown unless supplied explicitly. Missing
anthropometry is not replaced with cohort defaults. Source `.mot` files are
derived kinematics, and their exact bytes are retained in the provenance manifest.
Existing converters can reject candidate windows before output; a complete
candidate-level segmentation exclusion ledger remains outstanding. A complete
source inventory therefore does not mean that every possible gait event was
retained. Scientific review of event definitions, coordinate conventions, and
profile applicability remains necessary before creating a reviewed release.

## Corrected reconstruction started after the adversarial audit (20 October 2026)

Current storage check: S has about 15 GiB free; C has less than 1 GiB. Outputs stay
on S; WSL's large apparent free capacity is not additional Windows backing space.
The 5 GiB output-volume floor still applies.

`reconvert_umich_streaming.py` reads individual source windows from UM21's HDF5 MAT
file with a 768 MiB address-space cap. It writes one Parquet per treadmill
recording, unique source/frame/side identities, an accounted candidate ledger,
source/output hashes, and an unreviewed summary. It uses simultaneous bilateral
samples and the measured heel-strike interval, including both endpoints, rather
than a supplied duration that might disagree with those endpoints. Derivatives
span 149 intervals. Segment-chain angles are explicitly derived.

This is **partial kinematics staging**, not a complete corrected replacement:
only treadmill sagittal hip/knee signals and derived thigh/shank angles are
standardized. Original ankle values remain in `source_ankle_sagittal_angle_*`;
canonical ankle values are missing pending offset review. Kinetics, other tasks,
and normalized transfers are not included. Transfer timing and anatomical pairing
are not inferred from normalized array order. Historical MATLAB transfer handling
and the GT21 native conversion still require follow-up before production use.

Pilot: `converted_datasets/reconversion_v2/um21_tread_pilot_20261020/` contains
183 observations / 27,450 rows from AB01/d10. All output IDs and phase endpoints
were checked; three cycles independently match both source hip/knee channels to
within 5.1e-14 radians, with correctly scaled central-difference velocities.
77 consecutive source event pairs fall outside or ambiguously across labeled task
intervals and are retained in the exclusion ledger. This is not release approval.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 19 ionice -c 3 \
  python3 contributor_tools/reconvert_umich_streaming.py \
  --output-root converted_datasets/reconversion_v2/um21_tread_corrected_20261020
```

The 50-recording UM21 treadmill run is followed serially by the existing bounded
GT24 Phase3 and Phase1And2 conversion workers. Queue status and log are under
`converted_datasets/reconversion_v2/fixed_data_queue_20261020/`. Each dataset has
a separate output directory. A queue-level `STOP_AFTER_CURRENT` prevents the next
dataset from starting; to stop the active dataset at its next recording boundary,
create the same file in that dataset's output root. Failure or storage hold stops
the queue. Existing historical files are never overwritten.


### Expanded-budget GT24 restart

After explicit approval for a larger memory budget, the restart uses one worker
with a 9216 MiB address-space cap and a 512 MiB source-input cap, with the guards
above. The previously rejected BT01/sit_to_stand_1_1_short-arm_on pilot completed:
16 observations / 2,400 rows, structural checks passed, all observations unchecked;
peak worker RSS was about 200 MiB. The 9 GiB limit is a ceiling, not preallocated RAM.

UM21's 50-recording partial treadmill run is complete (1,293,900 rows) and is not
repeated. GT24 Phase3, followed by Phase1And2, runs in new directories ending in
`_9g_20261020`; existing outputs are preserved because the guard changes alter
worker provenance. Current queue status/logs are at
`converted_datasets/reconversion_v2/fixed_data_queue_9g_20261020/`.
The same STOP_AFTER_CURRENT controls apply. Large or unsupported inputs can still
stop the queue; raising the ceiling is not permission to bypass the remaining guards.

### Canonical-task correction after the expanded-memory run

The expanded-memory GT24 run processed 75 recordings, then correctly stopped on
three backward-walking schema failures. The converter used `backward_walking`,
but the canonical registry uses `walk_backward`. Both GT24 mapping tables now
use the registry spelling; ancillary functional mappings also use existing
canonical families. This does not reclassify backward walking as forward walking.

All three rejected BT01 backward recordings were regenerated in
`gt24_backward_fix_pilot_20261020`: 58 observations / 8,700 rows. An independent
check compared every hip/knee sample on both sides to original angle CSVs and
checked source frame endpoints; maximum error was below 1e-13 radians. Other
signals and event-detection validity remain separate review items. The check is
archived in `contributor_tools/audit_probes/2026_10_20/check_gt24_backward_source.py`.

The replacement GT24 queue uses `fixed_data_queue_canonical_20261020` with output
roots `gt24_phase3_canonical_20261020` and `gt24_phase1and2_canonical_20261020`.
It retains the approved 9 GiB / 512 MiB limits and all runtime guards. Earlier
outputs are preserved because changing task mapping changes conversion provenance.

GT25 code now retains inclusive endpoints, resamples against actual timestamps,
preserves gaps, avoids fallback body mass and unmeasured assistance/COP zeros,
and does not flip force signals based on expected waveform shapes. Known-value
fixtures exercise these changes. GT25 regeneration, identities, full task coverage,
and source convention reconciliation are still pending. The full remaining scope
is tracked in `contributor_tools/dataset_remediation.json`; code tests or partial
kinematics reconstruction alone do not close dataset-level findings.
