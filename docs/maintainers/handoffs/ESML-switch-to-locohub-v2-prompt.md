Switch the ES training data from the July 2026 LocoHub files to the new LocoHub local review packages. Do it on a new branch/config flag so the old pipeline still runs; do not delete the old `es_prepared` files.

**New data (read only)** — `/mnt/s/workspace/locomotion-data-standardization/converted_datasets/reconversion_v2/`
- GT2021: `gt21_r01_package_v2/` (22 participants; you used 15)
- UMich 2021: `um21_r01_package_v6/` (treadmill only: 44 recordings, 10 participants)
- GT2023: `gt23_r01_review_v12/`

Each folder has the same layout: `full_time.parquet`, `filtered_time.parquet`, `full_phase.parquet`, `filtered_phase.parquet`, `exclusions.csv`, `assessment.jsonl`, `limitations.json`, `manifest.json`, `README.md`. Read each README and `limitations.json` first, and take column names from the parquet schema. Do not assume the old names. Use the `filtered_*` files (quality failures already removed). If you need the excluded data, use `full_*` with the per-row `quality_status` column. Every exclusion is listed in `exclusions.csv`.

**Conventions that changed** (the standard is in `docs/reference/index.md` in that repo):
- Joint angles = differences of gravity-referenced segment angles (hip = thigh − pelvis, knee = thigh − shank, ankle = foot − shank). Thigh and shank are measured from down, foot and pelvis from horizontal. Side-view angles are measured in each leg's own plane, not the lab's. A standing hip reads about +10° by design.
- The foot angle is zeroed so the foot reads 0° when flat in level-walking mid-stance (per person), so the ankle angle shifts with it. GT2023 AB07 and UMich AB10 are uncorrected (flagged in `limitations.json`).
- Centre of pressure is in the ankle frame within the leg plane, with its origin 100 mm forward of the ankle centre. Your old CoP used the ankle centre, so add 0.100 m to compare.
- Power = published moment × LocoHub joint speed.
- Units are in the column suffix (`_rad`, `_Nm_kg`, `_BW`, `_m`).

**Expected differences from your current files** (measured, training minus new; mean / typical difference):
- GT2021: ankle −9.5° / 16°, shank +2.8°, foot −6.7°, CoP +1.1 cm. Ankle moment and vertical force are identical. About 0.1–0.2% of your old GT2021 angle samples were wrapped by ±180/360° (44 recordings, mostly AB24/AB07). Those are gone in the new data.
- UMich 2021: ankle +1.8° / 2.6°, shank −2.6°, foot −0.8°, CoP +1.5 cm. Moment and force are identical.
- GT2023: small (ankle −0.5° / 6°), but your current GT2023 file holds only sit-to-stand. Check whether that is intended before changing anything.

**Loader changes to expect**
1. **Task labels:** time-table rows of continuous recordings carry `task = continuous_recording`, not a per-row task. Rebuild per-row task labels from the phase-table stride windows of the same recording, or train from the phase table if that fits the objective.
2. **Force:** GT2021 has force on both legs for every activity, and missing force is NaN, so your dropout rule and your GT2021 force sidecar should no longer be needed. Under 20 N, UMich writes 0. GT2021 writes NaN when the foot should be in stance but the plate reads under 20 N.
3. **UMich CoP:** use the package's CoP instead of your CoP sidecar. CoP and force are held back (NaN) for AB01/AB02/AB03 i10, AB04 d10 and AB10 d5, and force also for AB04 i5. Note that UMich CoP comes from a plate position fitted per recording. Check whether that breaks your rule that no held-out moment enters an input.
4. **Missing stretches:** held frames are NaN (GT2021 about 4% of leg-frames, AB27 about 13%). Expect fewer complete 60-sample windows.
5. **Velocity:** your `dtheta_raw` / `dpsi_raw` are your own backward differences. The packages carry joint speeds (central difference), not segment speeds. Keep computing your own if the objective needs them, from the new angles.

**Memory** (shared WSL host): stream parquet with pyarrow `iter_batches` and column selection, one participant at a time, one numerical worker, low priority. Never load a whole package (GT2021 is about 16 GB).

**Before training**
1. Rebuild your prepared files from the new packages into a NEW folder, for example `es_prepared_v2/`.
2. Print per dataset: participants, recordings, samples, windows kept versus the old prepared files, and the share of NaN per input column.
3. Spot-check one GT2021 and one UMich recording: overlay old and new ankle/shank/foot angles, and confirm the differences above (constant-ish offsets, no wraps).
4. Report back, and do not start a long training run until I've looked.

These packages are local review versions and are not scientifically approved or published. Do not upload or share them.
