# Add New Dataset

Download data from a published paper and create a conversion script for the LocoHub standardized format.

## Usage

```
/add-dataset <paper_url_or_doi>
```

## Arguments

- `paper_url_or_doi`: URL to the paper (Google Scholar, DOI, PubMed) or a description of the dataset

## Workflow

When this skill is invoked, follow these steps:

### 1. Find the Data Repository

Search for the paper's data availability statement to find where the data is hosted:
- Dryad
- Zenodo
- Figshare
- OSF
- GitHub
- University repository

### 2. Download the Data

Create a new directory in `contributor_tools/conversion_scripts/<DatasetName>/` and download:
- All data files (MAT, CSV, etc.)
- README or data documentation

### 3. Explore Data Structure

Use MATLAB or Python to examine the data structure:
- What variables are available?
- What is the sampling rate?
- How are subjects/tasks organized?
- What units are used?

### 4. Create Conversion Script

Write a conversion script following the pattern in existing scripts:
- `convert_<dataset>_phase_to_parquet.py` for Python datasets
- `convert_<dataset>_phase_to_parquet.m` for MATLAB datasets

Key conversions:
- Angles: degrees → radians
- Moments: Nm → Nm/kg (mass-normalized)
- GRF: N → BW (body-weight normalized)
- Phase: resample to 150 points per cycle
- Sign conventions per `docs/reference/index.md`

### 5. Create README

Create a `README.md` with:
- Paper information (title, authors, journal, DOI)
- Data repository link
- Data structure description
- Task mapping to standard names
- Available features
- Citation in BibTeX format

### 6. Create Metadata File

Create a `metadata.yaml` with dataset information for documentation generation.

### 7. Run Conversion and Validate

```bash
python3 <conversion_script>
python3 contributor_tools/quick_validation_check.py converted_datasets/<output>.parquet
```

### 8. Generate Documentation

```bash
python3 contributor_tools/manage_dataset_documentation.py add-dataset \
    --dataset converted_datasets/<output>.parquet \
    --metadata-file contributor_tools/conversion_scripts/<DatasetName>/metadata.yaml
```

## Standard Task Mappings

| Common Names | Standard Name |
|--------------|---------------|
| Walking, overground, treadmill | `level_walking` |
| Ramp up, incline | `incline_walking` |
| Ramp down, decline | `decline_walking` |
| Stairs up | `stair_ascent` |
| Stairs down | `stair_descent` |
| Sit-to-stand, STS | `sit_to_stand` |
| Stand-to-sit | `stand_to_sit` |
| Squat, lifting | `squat` |
| Running, jogging | `run` |
| Jumping | `jump` |

## Example

```
/add-dataset https://doi.org/10.1126/scirobotics.adr8282
```
