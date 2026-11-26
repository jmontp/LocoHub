# Decisions made for José (from 25 November 2026)

José: "do your picks. keep going until all three datasets have their phase and time datasets. Make decisions along the way for me and make a table at the end in case I want to change anything."

Each row: what was decided, what else was possible, and how to undo it.

| # | Date | Dataset | Decision | Other option | Undo cost |
|---|---|---|---|---|---|
| 1 | 2026-11-25 | UM21 | Add continuous time-series files with real plate force (D-UM21-TIME-1 A) | Per-stride only | Drop the time files from the package |
| 2 | 2026-11-25 | all | GT21 quality check before the training-data wrap re-run | Wrap re-run first | None; order only |
| 3 | 2026-11-25 | UM21 | Keep source sample rates in the time files (no resampling), as GT21 did | Resample to a common rate | Re-export time files |
| 4 | 2026-11-25 | UM21 | Time files use one 100 Hz clock; plate force sampled at those frames (no averaging) | Keep plates at 1 kHz in a separate table | Re-export time files |
| 5 | 2026-11-25 | UM21 | Per-stride (phase) files stay exactly as v4, no force columns added (T05-A) | Add force to phase files | Rebuild phase files |
| 6 | 2026-11-25 | UM21 | Force held back for the 5 recordings whose CoP is held back (T05-B) | Publish their force | Re-export 5 recordings |
| 7 | 2026-11-25 | UM21 | Plate value under 20 N stored as 0 body weight (T05-G), as in GT21 | Store as missing | Re-export time files |
| 8 | 2026-11-25 | UM21 | A time recording with a 30° jump is failed whole and left out of the filtered files (T05-D); revisit after pilot if it drops many | Mark only the jump | Rebuild package |
| 9 | 2026-11-25 | UM21 | Source plate values treated as newtons, not N/kg as the README says (UM21-SLOPE evidence) | Follow README | Re-export force |
| 10 | 2026-11-25 | UM21 | AB03 and AB10 plate force published as recorded although it reads 3-9% under body weight; noted in limitations | Rescale or hold | Re-export 2 participants |
| 11 | 2026-11-25 | GT21 | Same quality limits and status rules as UM21/GT23, no tuning | GT21-specific limits | Re-run assessment (~10 min) |
| 12 | 2026-11-25 | GT21 | Plate dropout (force 0 while ankle moment > 0.3 Nm/kg; 689 observations) flagged only, not failed or removed | Fail or remove them | Re-run assessment |
| 13 | 2026-11-25 | GT21 | ~20 strides with early source heel strikes and 2 with no toe-off kept and flagged, not dropped | Drop them | Re-run assessment |
| 14 | 2026-11-25 | GT21 | Leg-plane glitch check (P1) left unchecked: the export has no per-frame leg plane | Recompute from markers | New code + re-run |
| 15 | 2026-11-25 | all | Freed 44 GB: GT21 r2 export, 2 failed GT21 test packages, GT23 in-between step data (José approved) | Free space elsewhere | Rebuild from code if needed |
| 16 | 2026-11-25 | GT21 | Package uses the GT23 layout (one phase and one time file per variant, not split by participant) | Split by participant | Rebuild package (~25 min) |
| 17 | 2026-11-25 | GT21 | Flagged items (plate dropout, held frames, short stances, no-toe-off strides) stay in both full and filtered files; only quality failures leave filtered | Remove flagged items from filtered | Rebuild package |
| 18 | 2026-11-25 | all | Shared package builder writes larger file chunks to fit the memory cap, instead of raising the cap; UM21/GT23 output unchanged | Raise the cap | Revert two lines |
| 19 | 2026-11-26 | UM21 | Kept the whole-recording 30° jump rule for time files: 1 of 44 recordings fails (AB05 d10) | Mark only the jump samples | Rebuild package v5 |
| 20 | 2026-11-26 | UM21 | AB04 i10 right-leg CoP kept, flagged as plate-noise-limited (time vs stride values differ by median 2.8 mm) | Hold that leg's CoP (60 -> 59 legs) | Rebuild package v5 |
| 21 | 2026-11-26 | UM21 | Time files use task = continuous_recording, as GT21 does (a recording spans several tasks) | One task per recording | Rebuild package v5 |
| 22 | 2026-11-26 | UM21 | Velocity agreement gated pooled over all strides; pelvis velocity and power reported, not gated | Per-recording gate | Re-run readback |
| 23 | 2026-11-26 | UM21 | Force also held for AB04 i5 (fails the 95% plate-loaded gate), in addition to the 5 held recordings | Publish it | Rebuild package v5 |
| 24 | 2026-11-26 | UM21 vs GT21 | Small difference kept and to be documented: GT21 marks force missing when the foot should be in stance but the plate reads under 20 N; UM21 has no independent stance timing, so under 20 N is always 0 | Use source gait events to mask UM21 the same way | New code + rebuild v5 |
