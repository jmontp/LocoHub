---
title: Dataset catalog
---

# Dataset catalog

Find datasets by task and download availability, then inspect the study population, signals, processing, and limitations on its documentation page.

!!! warning "Legacy / unreviewed catalog"
    These existing listings have not been approved under the current release contract. Counts and historical reports are retained without revalidation. A prior “clean” label or pass-rate badge does not certify the linked artifact. Read the [quality and release definitions](../reference/index.md#release-evidence) before choosing data.

**Full converted** includes observations before profile filtering; it is not original source data. **Profile-filtered** retains observations selected by a specific rule profile. Historical filenames may contain `clean`, `dirty`, or `raw`. A **—** means no download is registered for that variant. The displayed stride count is historical and may describe the full input rather than the filtered download; it does not count independent participants.

[Compare task coverage and historical plots](comparison.md){ .md-button }

<div id="catalog-controls" class="catalog-controls" hidden>
  <label for="catalog-search">Dataset or task <input id="catalog-search" type="search" placeholder="Search the catalog" /></label>
  <label for="catalog-task">Task <select id="catalog-task"><option value="">All tasks</option></select></label>
  <label for="catalog-download">Download <select id="catalog-download"><option value="">Any availability</option><option value="full">Full converted phase</option><option value="filtered">Profile-filtered phase</option><option value="time">Time data</option><option value="none">No registered download</option></select></label>
  <button id="catalog-reset" type="button">Reset filters</button>
</div>
<p id="catalog-status" role="status" aria-live="polite"></p>

<div data-dataset-catalog markdown="1">

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Strides | Documentation | Phase (profile-filtered) | Phase (full converted) | Time |
|---------|-------|---------|---------------|---------------|-------|------|
| Gait120 | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit | 6,882 | <a class="md-button md-button--primary" href="ga26/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 19,849 | <a class="md-button md-button--primary" href="gt24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/rq9ljak2fmzxhqx68iw2u/gtech_2024_phase.parquet?rlkey=b08njvj2cga8iyo7u48s493uy&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| GaTech 2025 (Domain Adaptation) | Backward Walking, Level Walking, Sit To Stand, Stand To Sit | 5,470 | <a class="md-button md-button--primary" href="gt25d/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/ni7qgftpoq2klndsrwkz1/gtech_2025_da_phase_clean.parquet?rlkey=j5ssc03k2sprw09vfzr370nh1&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/jye5hdd9z6ftjf6yogtm8/gtech_2025_da_phase_dirty.parquet?rlkey=edfildc8cwk4sipp4dkccy761&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2021 | Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition | 19,519 | <a class="md-button md-button--primary" href="gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | 2,940 | <a class="md-button md-button--primary" href="gt23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/xey8lljbjly0pl0o00vsb/gtech_2023_phase_clean.parquet?rlkey=ax2bk96imonvj3xb57nkho4x5&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vd24hcu6yo55qya0t0xmx/gtech_2023_phase_raw.parquet?rlkey=gdwjf6km2xc8mn92mvh495ubc&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| MBLUE Ankle Exoskeleton Study | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 15,825 | <a class="md-button md-button--primary" href="mb24/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| StrokePiG OpenSim Pipeline Dataset | Level Walking Stroke | 144 | <a class="md-button md-button--primary" href="sp50/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | 14,240 | <a class="md-button md-button--primary" href="um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/q37ioia7zmpkxqtw5dtw6/umich_2021_phase_clean.parquet?rlkey=j9cgoam6nz7mwtadcacqff3rn&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dpk4wgtger1ktdoqrlxbr/umich_2021_phase_dirty.parquet?rlkey=rrjtx05woy1fd1du6oguai6x0&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
<!-- DATASET_TABLE_END -->

</div>

## Choose a variant

- Start with **full converted data** when investigating quality, applying your own inclusion criteria, or comparing the effects of filtering.
- Use **profile-filtered data** only after checking the profile's intended population and tasks, required features, and exclusion reasons.
- Prefer **time data** for timing, event detection, or activities without defensible cycle boundaries. Phase exports resample each observation to 150 points; they do not preserve every original sample.

For new releases, download the manifest, provenance, quality results, profile, and exclusions with the data. Distinguish individual cycles from ensemble curves before counting observations or creating analysis splits. See the [native data tutorial](../tutorials/index.md).
