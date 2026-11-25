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
