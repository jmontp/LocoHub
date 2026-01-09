# LocoHub

<div align="center">
  <img src="docs/assets/locohub_logo.png" alt="LocoHub Logo" width="400">
  
  [![Documentation](https://github.com/jmontp/LocoHub/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/jmontp/LocoHub/actions/workflows/deploy-docs.yml)
  
  **The open standard for sharing biomechanical locomotion data through community-validated datasets, enabling reproducible research and faster development.**
</div>

## Available Datasets

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Strides | Documentation | Phase (Clean) | Phase | Time |
|---------|-------|---------|---------------|---------------|-------|------|
| GaTech 2024 (TaskAgnostic) | Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 19,849 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/rq9ljak2fmzxhqx68iw2u/gtech_2024_phase.parquet?rlkey=b08njvj2cga8iyo7u48s493uy&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2021 | Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition | 19,519 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Gtech 2023 | Agility Drill, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit, Step Down, Step Up, Walk Backward | 2,940 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt23/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/xey8lljbjly0pl0o00vsb/gtech_2023_phase_clean.parquet?rlkey=ax2bk96imonvj3xb57nkho4x5&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/vd24hcu6yo55qya0t0xmx/gtech_2023_phase_raw.parquet?rlkey=gdwjf6km2xc8mn92mvh495ubc&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| MBLUE Ankle Exoskeleton Study | Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit | 15,825 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/mb24/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/i1q5vcoq85ot958993fv5/mblue_ankle_phase_clean.parquet?rlkey=olktfihwldiu87fuamcko788q&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/6xr64078wfvsxee4xfz7v/mblue_ankle_phase.parquet?rlkey=owrklzpaonrkgdhly74u2thr6&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | 14,240 | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/q37ioia7zmpkxqtw5dtw6/umich_2021_phase_clean.parquet?rlkey=j9cgoam6nz7mwtadcacqff3rn&dl=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/dpk4wgtger1ktdoqrlxbr/umich_2021_phase_dirty.parquet?rlkey=rrjtx05woy1fd1du6oguai6x0&dl=1">Download</a> | <span class="md-button md-button--disabled">—</span> |
<!-- DATASET_TABLE_END -->

---

**📚 Full Documentation: [https://jmontp.github.io/LocoHub/](https://jmontp.github.io/LocoHub/)**

## Quickstart

### Install dependencies

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-container.txt
```

### Load a standardized dataset

```python
from locohub import LocomotionData

data = LocomotionData('converted_datasets/umich_2021_phase_clean.parquet')
cycles, features = data.get_cycles('UM21_AB01', 'level_walking')
```

### Install from source

```bash
pip install .
# or for development
pip install -e .
```

### Explore the docs locally

```bash
mkdocs serve
```

## Contributor Toolkit

- Conversion templates and utilities live in `contributor_tools/`
- `python contributor_tools/manage_dataset_documentation.py add-dataset` creates docs + validation summaries
- `python contributor_tools/quick_validation_check.py <dataset.parquet>` runs the fast validator pass
- Validation ranges are stored under `contributor_tools/validation_ranges/`

## GRF/COP Naming Migration

Ground reaction force and center-of-pressure columns now follow the schema
`<signal_type>_<axis>_<side>_<unit>` (for example `grf_vertical_ipsi_BW`,
`cop_anterior_contra_m`). Older datasets that used `vertical_grf_*`,
`anterior_grf_*`, and `lateral_grf_*` still load through `LocomotionData`
and the validation engine via internal aliases, but code that accesses
columns directly should migrate. To rewrite Parquet files on disk, use:

```bash
python contributor_tools/migrate_grf_cop_naming.py converted_datasets/*.parquet
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
