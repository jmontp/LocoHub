# LocoHub

<div align="center">
  <img src="docs/assets/locohub_logo.png" alt="LocoHub Logo" width="400">
  
  [![Documentation](https://github.com/jmontp/LocoHub/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/jmontp/LocoHub/actions/workflows/deploy-docs.yml)
  
  **The open standard for sharing biomechanical locomotion data through community-validated datasets, enabling reproducible research and faster development.**
</div>

## Available Datasets

<!-- DATASET_TABLE_START -->
| Dataset | Tasks | Documentation | Clean Dataset | Full Dataset |
|---------|-------|---------------|---------------|---------------|
| Gtech 2021 | Level Walking, Stair Ascent, Stair Descent, Transition | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/gt21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/h2aitlo77ujndhcqzhswo/gtech_2021_phase_clean.parquet?rlkey=zitswlvbc7g8bgt2f3jx3zyfx&st=26wq9hpi&raw=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/fvv83iipnhtapkaa1z70g/gtech_2021_phase_dirty.parquet?rlkey=fp7q7a3b0t8t6bivc9lynu5uj&st=idfk1sk4&raw=1">Download</a> |
| Umich 2021 | Decline Walking, Incline Walking, Level Walking, Run, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit, Transition | <a class="md-button md-button--primary" href="https://jmontp.github.io/LocoHub/datasets/um21/">Docs</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/typd1b24lfks6unjdiagf/umich_2021_phase_clean.parquet?rlkey=il6z7dnfs5i9n96tc90h1s244&st=vasjkbl2&raw=1">Download</a> | <a class="md-button" href="https://www.dropbox.com/scl/fi/21mbjl4g148idosnl5li1/umich_2021_phase_dirty.parquet?rlkey=jbcy3l53wgapuyc2e3k2pgbn6&st=tuctu1y2&raw=1">Download</a> |
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
from user_libs.python.locomotion_data import LocomotionData

data = LocomotionData('converted_datasets/umich_2021_phase_clean.parquet')
cycles, features = data.get_cycles('UM21_AB01', 'level_walking')
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

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
