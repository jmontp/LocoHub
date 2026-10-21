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


### GT25 source-linked pilot

The recording adapter is
`contributor_tools/conversion_scripts/GaTech_2025_DomainAdaptation/reconvert_recording.py`.
It accepts source-root, subject, recording, output-root, memory-mib, max-source-mib
and resume arguments, and uses the same guarded staging worker as GT24. Its source
manifest includes the original README containing measured masses and conventions.

`gt25_source_pilot_20261020` contains seven BT01 recordings covering three walking
controller models, backward walking, chair transfers, and stair ascent/descent:
152 observations / 22,800 rows. The independent `check_gt25_source.py` probe in
`contributor_tools/audit_probes/2026_10_20/` checks every observation against source
CSVs, binding its results to manifests and output hashes. Maximum checked signal
error was 4.44e-16. This verifies the stated transforms, not the unresolved
anatomical interpretation of every source channel.

Already-parsed short stair trials were previously erased by first/last-stride
trimming; each of the two pilot stair recordings now retains three observations.
The gait duration ceiling no longer rejects longer chair transfers. IDs encode
actual recording, source endpoints and reference side; missing horizontal-frame
interpretations remain missing while raw global force channels are retained.

This is a partial pilot, not a finished GT25 release. Remaining work includes all
subjects/tasks, candidate exclusion accounting, event validation, segment-angle
interpretation, COP coordinates, and the source README/converter disagreement on
ankle-angle sign. GT24 resumed from verified outputs after this serial pilot;
its own boundary-stride trimming still needs source-specific review.


### GT24 timing and short-recording corrections

GT24's source README also states that Parsed transitions were already removed.
Unconditional first/last-stride trimming is now disabled, and gait duration limits
no longer discard chair transfers. Resampling now uses source timestamps, preserves
missing measurements, and rejects misaligned channel clocks instead of pairing by
row number. Nonuniform-clock and missing-sample fixtures cover these changes.

The current `gt24_timing_trim_pilot_20261020` has 24 observations / 3,600 rows:
three ascent, three descent and 18 chair transfers. The previous chair pilot had
16 transfers. Every retained hip/knee sample on both sides matches source CSV
interpolation to within 4.44e-16 radians. The archived `check_gt24_trim_source.py`
probe binds its findings to source, output and manifest hashes. Event semantics,
other signal conventions and complete exclusion accounting remain open.

The old canonical queue was stopped at a recording boundary. Its outputs are
preserved. The corrected queue is `fixed_data_queue_timing_20261020`, with output
roots `gt24_phase3_timing_20261020` and `gt24_phase1and2_timing_20261020`. It retains
one worker, the 9 GiB ceiling, 512 MiB source admission, and memory/disk guards.
These outputs remain unreviewed staging files, not approved dataset releases.


### UM21 normalized transfers: preserve source, avoid invented pairing

`reconvert_umich_transfers.py` reads one normalized curve at a time and retains
original joint-angle/forceplate names, plane indices and values without converting
source axes or units. The full source-preservation run is
`um21_normalized_transfers_20261020`: 20 subject/task arrays, 252 curves / 37,800
rows. Every exported source channel was read back and compared exactly, including
NaNs. The manifest records source, converter and output SHA-256 values.

Anatomical reference side, source time and duration remain unknown. There are no
invented opposite-leg channels or time derivatives. Marker arrays have different
curve counts and are not paired by ordinal position. This staging output is not a
canonical bilateral release; matching source anatomy and original recording times
remains required. A sampled approximate waveform match was insufficient evidence.

The MATLAB normalized-transfer path no longer copies each curve into both sides,
assigns streaming durations by sequence, or invents chair height/arm-support
metadata. Unpaired curves are explicitly marked unknown-side and contralateral
measurements remain missing. The obsolete duration/event-matching helpers were
removed. These native edits have not been executed in MATLAB; the Python export
provides verified source preservation, not evidence of native execution.

GT24 was stopped at a recording boundary for this bounded export, then resumed
from the same immutable timing-corrected outputs.


### MBLUE observed-time alignment pilot

MBLUE walking no longer pairs opposite-leg curves by index, clamps to the last
available curve or applies a fixed half-cycle shift. Angles, moments and force
use original timestamp overlap. COP samples use the same ipsilateral time window
for both plates. Gaps and conflicting overlapping samples remain missing.
Missing source duration and pelvis measurements no longer become 1/2 seconds or
zero degrees; unknown subject mass no longer defaults to 70 kg.

`mblue_overlap_pilot_20261020` contains 102 AB01 bare level-walking observations
at 1 m/s. The independent `check_mblue_time_overlap.py` probe checked 45,228
opposite-leg hip/knee/ankle values against uniquely overlapping source intervals;
maximum error was 4.44e-16 radians. Source, converter and output hashes are saved.
This is a provisional legacy-schema pilot, not a publishable release. Stable
identities, all subjects/conditions, bilateral-task alignment, full force/COP
semantics and exclusion accounting remain open. GT24 resumed after this pilot.


### GT21 bounded native MATLAB path

`convert_gtech_2021_phase_to_parquet(options)` accepts an explicit source root,
subject, date, mode, recording and output path. This branch processes one
recording and bypasses all-subject accumulation. Existing outputs are rejected.
`run_matlab_recording_guarded.ps1` launches MATLAB suspended, assigns it to a
Windows job with a hard aggregate memory limit and idle priority, then resumes
it. Descendants remain in the job. The guard requires a 2 GiB pre-launch reserve,
monitors a 1.5 GiB available-memory floor and 5 GiB S-space floor, and enforces a
timeout. Temp/preferences and outputs are directed to S. WSL conversion is stopped
at a recording boundary while a native numerical worker runs.

The first native pilot revealed an additional endpoint bug: the exported cycle
ended one sample before the next source heel-strike reset. The corrected code
uses consecutive reset samples inclusively and elapsed-time phase for every
channel. `gt21_inclusive_pilot_20261020` contains four AB06 levelground observations
(600 rows). MATLAB R2023b completed with a 2 GiB hard limit. An independent Python
probe checked every bilateral hip/knee/ankle angle, velocity and moment against
original tables exported directly from the MAT files; maximum angle/moment error
was 4.60e-14. Both endpoints of every cycle match consecutive source heel strikes,
and structural checks pass. Exact source/code/output hashes and code snapshots
are retained. The earlier pilot is preserved separately.

This is not whole-GT21 approval. Other subjects/modes, force/COP transformations,
source conventions and complete exclusion accounting remain open. No full native
batch has started yet. GT24 resumed after the native pilot.


### Gait120 missing metadata and source anthropometry

Gait120 no longer substitutes 70/75 kg, 1.70 m, a one-second cycle or zero pelvis
orientation for absent measurements. Unknown metadata remains missing; derived
segment angles remain missing when pelvis orientation is absent. Optional OpenSim
reconstruction rejects missing mass/height before loading or scaling a model.
The converter imports its own named helpers explicitly, avoiding a collision
with StrokePiG's `marker_mapping` module in a shared process.

The metadata reader was checked against all 120 rows of the supplied spreadsheet;
masses and heights match, with measured masses ranging from 48.2 to 118.0 kg.
`gait120_anthropometry_review_20261020/source_comparison.json` records the source
and reader hashes plus each compared record. This verifies metadata reading only.
Affected Parquet files have not been regenerated, and phase/laterality assumptions
and historical inverse-dynamics anomalies remain open.


### GT21 full local inventory and serial batch

`run_gt21_native_batch.py` inventories every available subject/date/mode instead
of using the historical hard-coded subject exclusions. The current local source
has 2,301 recordings across 16 subjects, including AB27. This does not establish
complete coverage of the original published dataset; missing-source reconciliation
remains open. Default invocation inventories only; `--run` enables reconstruction.

Each recording has a separate immutable directory, source/code hashes, native
status, losslessly compressed original source-table CSVs and streaming structural
checks. Decompressed CSV hashes are verified before removing the temporary CSVs. Resume checks
all source, code and output hashes. Missing required channels, admission failures,
changed code, native failures or invalid output stop the batch. Native admission
is capped at 64 MiB of source files in addition to the Windows hard 2 GiB job limit.
Code snapshots are retained; a batch cannot silently mix converter versions.

`gt21_native_batch_20261020/start_after_gt24.py` is waiting for the live GT24 queue
to complete both phases. It will start GT21 only after confirmed successful queue
completion and unchanged reviewed code. Its status is `dispatch_status.json`;
GT21 progress will be in `batch_status.json` and `batch.log`. A GT21-root
`STOP_AFTER_CURRENT` cancels the pending dispatch or stops the batch at a recording
boundary. This preserves the one-numerical-worker rule. The native batch itself
has not run yet; the prior single-recording native pilot remains the execution
evidence. Batch software fixtures cover inventory, required channels, path safety
and immutable resume behavior.


### StrokePiG source events and clock pilot

The converter now uses anatomical C3D Foot Strike annotations when available,
keeps both annotated cycle endpoints, and interpolates using actual IK times.
Kinematic fallback boundaries are explicitly marked unverified. Candidate events
and rejection reasons accompany each exported observation. Missing samples remain
missing through interpolation. The C3D clock now restores the original acquisition
frame number from ezc3d's zero-based header index; force windows match IK timestamps
rather than assuming identical row indices.

`strokepig_events_pilot_20261020` regenerated TVC03/BWA6 under a 1.5 GiB address-space
cap (peak RSS about 193 MiB). Its three original left-foot cycles produce 450 rows.
The independent `check_strokepig_events.py` probe reads C3D events and raw MOT data
without the converter: every bilateral hip/knee/ankle angle matches to at most
4.45e-16 rad. The raw C3D binary header independently confirms the 9.34-second IK
start. Source, output and probe hashes are saved in `source_comparison.json`.

This is one recording, not a completed StrokePiG rebuild. Clinical affected side
remains unknown; anatomical left is explicitly a default reference. Force/COP,
model sign conventions, complete source coverage and a ledger for recordings with
no accepted cycles remain to be verified. The GT24 queue resumed after this pilot;
the GT21 dispatcher was rebound to the resumed queue and still waits for successful
completion of both GT24 phases.


### Gait120 original anatomical reference and sample order

The source paper (Scientific Data 12:1023, DOI 10.1038/s41597-025-05391-0,
Methods page 5) states that supplied gait cycles span right heel strike to the
next right heel strike. Transfers use pelvis/shoulder boundaries. This contradicts
the converter's unsupported left/right swap and half-cycle circular rotation.
Both transformations were removed, including optional pipeline/ID output rotation.
The default precomputed-angle path uses actual source time and preserves missing
gaps. Exports now record source identities, anatomical reference, observation type,
endpoint samples/times and the source protocol supporting the phase boundaries.

`gait120_source_pilot_20261020` reconstructed 14 recordings: one per task for S001
(no source forces) and S011 (source forces for eligible tasks), totaling 2,100 rows.
All bilateral hip/knee/ankle angles match direct interpolation from the original
MOT tables to at most 4.45e-16 rad. Every saved output passes the structural check
and exact Parquet readback. Source/code/output hashes and converter snapshots are
retained. `anthropometry_comparison.json` independently checks all 14 outputs
against the actual fallback spreadsheet, including its hash. The pilot runner now
also includes that spreadsheet directly in future source manifests.

These checks establish preservation of the stated source frame and transformed
samples; they do not independently validate the original event detection or model
signs. Full Gait120 reconstruction, force/COP frames and historical inverse-dynamics
anomalies remain open. The paper also states that force data for S001–S010 are
unavailable because acquisition coordinate frames were not correctly aligned;
missing force values for these participants must remain missing.


### Gait120 force plate preservation pending anatomical mapping

The old force helper assigned early/late loading to legs using an assumed gait
pattern, including for bilateral transfers. It also mapped force X/Z and COP X/Z
to conflicting anatomical axes, and could publish lab-frame COP as ankle-relative
when markers were missing. The Gait120 adapter no longer uses those guesses.

Available original plate force, COP and torque channels are retained under
`source_plate*_force_*_N`, `source_plate*_cop_*_m` and `source_plate*_torque_*_Nm`.
They retain original MOT axes and are interpolated onto actual IK timestamps;
missing samples and timestamps outside force coverage remain missing. Canonical
anatomical GRF/COP fields remain missing with an explicit reason in task metadata
until plate-to-side and coordinate transforms are verified. This is an unresolved
mapping, not a claim that the source measurements are unavailable or invalid.

`gait120_force_pilot_20261020` regenerated the same 14-recording/2,100-row pilot.
All bilateral sagittal angles still match. Walking supplies two plates while the
two transfer trials supply only one: all 36 available force/COP/torque channels
match independent source interpolation exactly. Source, code, output and actual
anthropometric spreadsheet hashes are retained. The initial probe incorrectly
assumed both plates existed in transfers; its partial outputs and failure record
are preserved in `gait120_force_pilot_20261020_incomplete_probe`. The corrected
probe explicitly checks that absent channels remain absent.

Full reconstruction and anatomical force/COP validation remain open. Experimental
OpenSim/ID paths are not verified by this default precomputed-angle pilot.


### Gait120 full local inventory and pending reconstruction

`run_gait120_batch.py` inventories all local JointAngle recordings, including
unsupported paths as explicit exclusions. The local source matches the paper:
6,882 recordings from 120 participants, comprising 1,060 walking, 1,187 stair
ascent, 1,186 stair descent, 1,172 slope ascent, 1,150 slope descent, 558 sit-to-stand
and 569 stand-to-sit recordings. No unsupported paths were found in this inventory.

`gait120_full_batch_20261020` holds the frozen inventory/code snapshots. Each worker
has a 1 GiB address-space cap, 64 MiB source admission, numerical threads set to
one, and a 120-second timeout. The parent requires 2 GiB memory reserve and 5 GiB
disk headroom; the existing live monitor stops only its own worker if available
memory falls below 1.5 GiB. Each source file gets an immutable output directory,
source/code/output hashes, structural validation and exact readback. Changed or
partial evidence stops resume rather than overwriting an artifact. A root
`STOP_AFTER_CURRENT` cancels the pending dispatcher or stops between recordings.

The worker executed S011/LevelWalking/Trial01/step01 successfully. All 78 numeric
columns exactly match the prior independent source-checked force pilot, and its
resume fingerprint was checked. A small post-run comparison initially hit a
512 MiB inspection cap; rerunning that inspection with one Arrow I/O thread under
768 MiB succeeded. The conversion itself succeeded under its 1 GiB cap.

`start_after_gt21.py` waits for the live GT21 dispatcher and requires its full batch
to report `complete_unreviewed` before starting Gait120. It refuses to start after
incomplete GT21 work. Progress will be recorded in `batch_status.json`; the
current dispatcher status is `waiting_for_gt21`. The full batch has not run yet.

Reconstruction uses precomputed source angles, not experimental OpenSim/ID. It
preserves raw force-plate channels while anatomical force/COP remains unresolved.
Non-sagittal signal standardization, event/model checks, release reconciliation
and scientific approval remain open even after this batch finishes.


### GT23 measured three-dimensional COP correction (native execution pending)

Both GT23 MATLAB paths replaced the source `RCOPY_Vertical`/`LCOPY_Vertical`
measurements with zero before applying calcn transforms, then separately forced
local vertical COP to zero. The corrected paths retain the source Y coordinate
and transform/export all three components. Missing measured coordinates remain
missing. Transform timestamps outside their observed coverage no longer use an
extrapolated endpoint pose. The phase converter also initializes anatomical
routing columns with missing values instead of zeros for unassigned rows.

`check_gt23_cop_source.py` examined 4,096 rows each from AB01 ball toss, walking
and sit-to-stand. Ball toss and sit-to-stand contain measured global Y values up
to about 0.0106 m; the sampled right walking channel is missing, which must not
be converted into a measured zero. Source hashes and finite/missing/nonzero counts
are in `gt23_cop_source_review_20261020/source_comparison.json`.

Existing static tests previously required the zero-filled behavior. They now
check measured-Y wiring and lack of transform extrapolation; a separate geometric
fixture demonstrates that measured global Y changes local anterior COP in a
rotated frame. Neither test executes MATLAB. Native converter execution, original
transform/frame checks and affected artifact reconstruction remain pending; this
finding is not closed by the source audit or Python tests.
