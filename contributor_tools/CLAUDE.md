# Contributor Tools

Tools for converting raw biomechanical datasets to the LocoHub standardized parquet format, validating conversions, and generating documentation.

## Directory Structure

```
contributor_tools/
├── conversion_scripts/     # Dataset-specific conversion scripts (MATLAB/Python)
│   ├── Gtech_2021/        # Georgia Tech 2021 (Camargo et al.)
│   ├── Gtech_2023/        # Georgia Tech 2023
│   ├── GaTech_2024_TaskAgnostic/  # Georgia Tech 2024 exoskeleton
│   ├── Umich_2021/        # University of Michigan 2021
│   └── AddBiomechanics/   # AddBiomechanics dataset
├── common/                 # Shared Python libraries (see common/CLAUDE.md)
│   ├── stride_segmentation.py  # Unified stride/cycle segmentation
│   ├── phase_detection.py      # GRF-based gait event detection
│   ├── near_miss_analysis.py   # Marginal failure analysis
│   ├── config_manager.py       # Validation YAML config loading/saving
│   ├── validation/             # Validation engine
│   │   ├── validator.py        # Core validation logic
│   │   └── report_generator.py # Markdown report generation
│   └── plotting/               # Validation plot generation
│       ├── filters_by_phase_plots.py  # Main validation plots
│       ├── step_classifier.py         # Pass/fail color coding
│       └── forward_kinematics_plots.py # FK visualizations
├── validation_ranges/      # YAML files defining valid data ranges per task
└── validation_plots/       # Generated validation plot outputs (gitignored)
```

Note: `internal/` has been consolidated into `contributor_tools/common/`.
Task registry is now in `src/locohub/task_registry.py` (shared source of truth).

## Common Libraries (`common/`)

Shared Python utilities for conversion scripts. See `common/CLAUDE.md` for detailed API documentation.

### Stride Segmentation (`stride_segmentation.py`)

Unified library for segmenting biomechanical data into cycles/strides. Supports three archetypes:

| Archetype | Tasks | Detection Method |
|-----------|-------|------------------|
| **Gait** | level_walking, incline_walking, decline_walking, stair_ascent, stair_descent, run, backward_walking, hop | Heel strike to heel strike (GRF threshold crossing) |
| **Standing Action** | jump, squat, lunge | Stable standing → action → stable standing (GRF + velocity) |
| **Sit-Stand Transfer** | sit_to_stand, stand_to_sit | GRF state machine + velocity-based motion onset/offset |

**Usage in conversion scripts:**
```python
from common.stride_segmentation import segment_by_task, GaitSegmentationConfig

# Auto-route to correct archetype
segments = segment_by_task(df, task="level_walking")

# Or use specific functions with custom config
from common.stride_segmentation import segment_gait_cycles, segment_sit_stand_transfers
segments = segment_gait_cycles(df, GaitSegmentationConfig(grf_threshold_N=30.0))
```

### Phase Detection (`phase_detection.py`)

Lower-level GRF event detection (heel strikes, toe-offs).

### Near-Miss Analysis (`near_miss_analysis.py`)

Identifies marginal validation failures using z-scores and phase violation counts.

## Conversion Workflow

### 1. Convert Raw Data to Parquet

Each dataset has its own conversion script in `conversion_scripts/<dataset>/`:

- **MATLAB datasets**: Run `convert_<dataset>_phase_to_parquet.m` in MATLAB
- **Python datasets**: Run `convert_<dataset>_phase_to_parquet.py`

Output: `converted_datasets/<dataset>_phase_dirty.parquet`

### 2. Validate the Conversion

**Quick validation check:**
```bash
python contributor_tools/quick_validation_check.py converted_datasets/<dataset>_phase_dirty.parquet
```

**With plots:**
```bash
python contributor_tools/quick_validation_check.py <dataset>.parquet --plot --task level_walking
```

**Diagnose failures:**
```bash
python contributor_tools/diagnose_validation_failures.py <dataset>.parquet --top 10
```

### 3. Tune Validation Ranges (if needed)

**Generate ranges from data (CLI):**
```bash
python contributor_tools/manage_ranges.py generate <dataset>.parquet --tasks sit_to_stand --update
```

**Interactive GUI for adjusting validation ranges:**
```bash
python contributor_tools/interactive_validation_tuner.py
```

### 4. Create Clean Dataset

Remove failing strides:
```bash
python contributor_tools/create_clean_dataset.py converted_datasets/<dataset>_phase_dirty.parquet
```
Output: `<dataset>_phase_clean.parquet`

### 5. Generate Documentation

**Full documentation (plots + markdown):**
```bash
python contributor_tools/generate_validation_documentation.py
```

**Manage dataset pages:**
```bash
python contributor_tools/manage_dataset_documentation.py add-dataset \
    --dataset converted_datasets/<dataset>_phase.parquet \
    --short-code XX21
```

## Key Tools Reference

| Tool | Purpose |
|------|---------|
| `quick_validation_check.py` | Fast pass/fail validation with optional plotting |
| `diagnose_validation_failures.py` | Identify which features fail and why (under/over bounds) |
| `interactive_validation_tuner.py` | GUI for adjusting validation range boxes |
| `manage_ranges.py` | CLI for generating validation ranges from data |
| `create_clean_dataset.py` | Remove failing strides from dirty parquet |
| `generate_validation_documentation.py` | Generate plots and markdown docs |
| `manage_dataset_documentation.py` | Add/update/remove dataset documentation pages |
| `manage_tasks.py` | CLI for managing canonical task definitions |

## Validation Ranges

Located in `validation_ranges/`:
- `default_ranges.yaml` - Current default ranges for able-bodied data
- `impaired_ranges.yaml` - Ranges for impaired population data
- `example_custom_ranges.yaml` - Template for custom ranges

### Interpreting Pass Rates

**The goal of validation is NOT to achieve 100% pass rates.** The validation ranges represent established biomechanical norms derived from literature and reference datasets. Pass rates indicate how well a dataset conforms to these norms:

- **High pass rates (>80%)**: Data closely matches expected biomechanical patterns
- **Moderate pass rates (40-80%)**: Data has characteristics worth investigating - could be valid variations or quality issues
- **Low pass rates (<40%)**: Data significantly deviates from norms - requires documentation or investigation

**What failing strides indicate:**

1. **Data quality issues** - Sensor noise, processing artifacts, or conversion errors that should be fixed
2. **Special populations** - Pathological gait, elderly subjects, or other populations with different movement patterns
3. **Non-standard protocols** - Unusual speeds, surfaces, or task variations
4. **Task-specific differences** - Non-gait tasks (sit-to-stand, cutting) that require task-specific validation criteria

**Do NOT automatically widen ranges to increase pass rates.** Instead:

- Investigate failures to understand their cause
- Document known deviations in the dataset metadata
- Create population-specific or task-specific range files if needed
- Use the "clean" dataset (failing strides removed) for applications requiring high data quality

### Near-Miss Analysis (Planned Feature)

For cases where strides fail by a small margin, a near-miss analysis workflow helps identify candidates for range review:

**Concept:** Distinguish "barely outside bounds" from "way outside bounds" using:
- **Z-score from clean data**: How many standard deviations from the mean of passing strides?
- **Number of phases failed**: Strides failing at 1-2 phases are more likely minor outliers than strides failing everywhere

**Criteria for "marginal failure":**
- Few phases violated (e.g., ≤2 of 4 checkpoints)
- Small z-score at each violation (e.g., z < 2.5σ from clean mean)

**Workflow:**

1. **Flag marginal failures and export candidate ranges:**
   ```bash
   python contributor_tools/diagnose_validation_failures.py <dataset>.parquet \
       --flag-marginal --export-review
   ```
   Outputs: `review_<dataset>_candidate_ranges.yaml` with suggested bounds already applied.

2. **Test the candidate ranges:**
   ```bash
   python contributor_tools/quick_validation_check.py <dataset>.parquet \
       --ranges review_<dataset>_candidate_ranges.yaml
   ```
   Compare pass rates to see the impact of accepting the suggestions.

3. **Accept or reject:**
   - If satisfied, copy to `validation_ranges/default_ranges.yaml`
   - If not, adjust thresholds (`--max-zscore`, `--max-phases`) and regenerate

**Tuning thresholds:**
- `--max-zscore 2.5` (default): Only strides within 2.5σ of clean mean qualify as marginal
- `--max-phases 2` (default): Only strides failing at ≤2 phase checkpoints qualify
- Lower values = more conservative suggestions; higher values = more aggressive

**Key principle:** Human review required - no automatic range expansion. The exported file lets you see the impact before committing.

**Shared library:** The near-miss detection logic lives in `contributor_tools/common/near_miss_analysis.py` for use by both `diagnose_validation_failures.py` and other tools.

## Conversion Script Structure

Each conversion script directory typically contains:
- Main conversion script (`convert_*.m` or `convert_*.py`)
- `utilities/` - Helper functions for that dataset
- Validation scripts (`validate_*.m`) - Verify conversion correctness

### MATLAB Conversion Notes

The MATLAB executable is on the Windows partition at the default install location (WSL environment). Conversion scripts output parquet files to `converted_datasets/`.

## Adding a New Dataset

1. Create `conversion_scripts/<NewDataset>/` directory
2. Write conversion script following existing patterns
3. Run conversion to produce `_dirty.parquet`
4. Validate with `quick_validation_check.py`
5. Tune ranges if needed with `interactive_validation_tuner.py`
6. Create clean dataset with `create_clean_dataset.py`
7. Generate documentation with `manage_dataset_documentation.py`
