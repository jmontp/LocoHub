# LocoHub

Standardized locomotion datasets with explicit provenance, quality evidence, and native Parquet access for research.

**Start with the [dataset catalog](https://jmontp.github.io/LocoHub/datasets/), [data tutorial](https://jmontp.github.io/LocoHub/tutorials/), and [format reference](https://jmontp.github.io/LocoHub/reference/).**

Researchers read files directly with pandas, MATLAB, or another Parquet reader. No LocoHub analysis package is required. Python tooling in this repository supports conversion, quality checks, and release preparation.

## Dataset catalog

The existing downloads below are **legacy / unreviewed under the current release contract**. Their historical counts and reports are retained for inspection; they do not certify the linked files. Check each dataset's population, available signals, processing notes, and source license before use.

- **Full converted**: converted observations before profile-based filtering; it is not the original source recording.
- **Profile-filtered**: observations retained by a particular rule profile. Historical filenames may say `clean` or `dirty`; these names do not establish fitness for a research question.
- **—**: no download is registered for that variant.

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Strides | Documentation | Phase (profile-filtered) | Phase (full converted) | Time |
|---------|-------|---------|---------------|---------------|-------|------|
| Gait120 | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit | 6,882 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/ga26/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 19,849 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/rq9ljak2fmzxhqx68iw2u/gtech_2024_phase.parquet?rlkey=b08njvj2cga8iyo7u48s493uy&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| GaTech 2025 (Domain Adaptation) | Backward Walking, Level Walking, Sit To Stand, Stand To Sit | 5,470 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt25d/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/ni7qgftpoq2klndsrwkz1/gtech_2025_da_phase_clean.parquet?rlkey=j5ssc03k2sprw09vfzr370nh1&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/jye5hdd9z6ftjf6yogtm8/gtech_2025_da_phase_dirty.parquet?rlkey=edfildc8cwk4sipp4dkccy761&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2021 | Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition | 19,519 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | 2,940 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/xey8lljbjly0pl0o00vsb/gtech_2023_phase_clean.parquet?rlkey=ax2bk96imonvj3xb57nkho4x5&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vd24hcu6yo55qya0t0xmx/gtech_2023_phase_raw.parquet?rlkey=gdwjf6km2xc8mn92mvh495ubc&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| MBLUE Ankle Exoskeleton Study | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 15,825 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/mb24/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| StrokePiG OpenSim Pipeline Dataset | Level Walking Stroke | 144 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/sp50/">Docs</a> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> | <span class="md-button md-button--disabled">—</span> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | 14,240 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/q37ioia7zmpkxqtw5dtw6/umich_2021_phase_clean.parquet?rlkey=j9cgoam6nz7mwtadcacqff3rn&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dpk4wgtger1ktdoqrlxbr/umich_2021_phase_dirty.parquet?rlkey=rrjtx05woy1fd1du6oguai6x0&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
<!-- DATASET_TABLE_END -->

## Try the data format

Download the [synthetic CSV](docs/tutorials/assets/locohub_example_data.csv) or [equivalent Parquet](docs/tutorials/assets/locohub_example_data.parquet). Both contain four complete observations of 150 points each. The signals are artificial examples, not research data or reference ranges.

```bash
python -m pip install pandas pyarrow matplotlib
```

```python
import pandas as pd

# From the repository root; otherwise use the path where you saved the sample.
df = pd.read_parquet("docs/tutorials/assets/locohub_example_data.parquet")
identity = ["subject", "source_recording_id", "observation_id", "reference_side"]
print(df.groupby(identity).size())  # Four observations, 150 rows each
```

The [tutorial](https://jmontp.github.io/LocoHub/tutorials/) covers quality evidence, selecting observations, and plotting in Python and MATLAB. The former analysis libraries are retired from the supported researcher workflow; see the [migration notice](https://jmontp.github.io/LocoHub/api/api-index/).

## Contribute a dataset

Follow the [contributor guide](https://jmontp.github.io/LocoHub/contributing/). Preserve source identities and units, distinguish individual cycles from ensemble curves, and retain missing/unchecked results explicitly. Publish full data, filtered data, and quality evidence together using the release tooling; a high profile pass rate alone is not release approval.

## Develop the documentation

For project work, start with the [work backlog](docs/maintainers/backlog.html).
It records dependencies, evidence needed to finish each task, and the handoff
for the next agent or contributor. Read the next ready task with:

```bash
python3 contributor_tools/build_backlog_page.py --next
```

```bash
python -m pip install -r requirements-curation.txt
python -m pytest tests/test_data_documentation.py
python docs/build.py --check
python docs/build.py --output site
python -m http.server 8000 --directory site
```

The website is authored plain HTML, CSS, and JavaScript under `docs/` and is served by GitHub Pages. The standard-library builder checks links, copies referenced assets, and creates a search index; it does not render Markdown. Pull requests include a downloadable HTML preview artifact.

## License and citation

The repository code is licensed under the [MIT License](LICENSE). Dataset reuse is governed by each source dataset's terms; the code license does not grant data rights. Cite the original dataset and the exact LocoHub release used.
