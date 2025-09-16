---
title: Maintainers
---

# Maintainers

Essential commands and paths for day‑to‑day maintenance.

## Do This

### Review Dataset Submissions
Contributors now submit complete packages with documentation. Your role:

1. **Review PR contents**:
   - ✅ Dataset parquet file in `converted_datasets/`
   - ✅ Documentation in `docs/datasets/`
   - ✅ Conversion script in `contributor_tools/conversion_scripts/`

2. **Check validation results**:
   - Review validation pass rates in documentation
   - Ensure ≥80% pass rate or justified exceptions
   - Check for appropriate task coverage

3. **Verify metadata**:
   - Short code is unique
   - Institution and citation provided
   - Subject count and tasks documented

4. **Merge if complete**:
   - All files present
   - Validation acceptable
   - Documentation complete

### Quick Validation Tools
- Test dataset: `python contributor_tools/quick_validation_check.py <dataset_phase.parquet>`
- Filter strides: `python contributor_tools/create_filtered_dataset.py <dataset_phase.parquet>`
- Serve docs locally: `mkdocs serve`

## Where Things Are

- Converters: `contributor_tools/conversion_scripts/`
- Outputs: `converted_datasets/`
- Validation engine: `internal/validation_engine/validator.py`
- Validation ranges: `contributor_tools/validation_ranges/`
- Python API: `user_libs/python/locomotion_data.py`

## Workflows

### Standard PR Review Flow
1. **Contributor submits PR** with dataset + documentation
2. **Review submission** - Check files, validation, metadata
3. **Request changes** if needed (missing info, low validation)  
4. **Merge when ready** - Documentation is already complete!

### Maintenance Tasks
- **Update validation ranges**: Edit YAML → have contributors re-run validation
- **Add new variables**: Update `feature_constants.py` → update converters
- **Fix documentation**: Direct edits to `docs/datasets/*.md` files
- **Archive datasets**: Move old docs to `archived/` subdirectory


## Environment

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
