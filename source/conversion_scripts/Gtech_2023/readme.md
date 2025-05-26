# Georgia Tech 2023 Dataset Converter

This directory contains conversion scripts for the Georgia Tech 2023 human lower-limb biomechanics dataset.

## Dataset Citation

Camargo, J., Flanagan, W., Csomay-Shanklin, N. et al. **A human lower-limb biomechanics and wearable sensors dataset during cyclic and non-cyclic activities**. Sci Data 10, 933 (2023). https://doi.org/10.1038/s41597-023-02840-6

[Link to publication](https://www.nature.com/articles/s41597-023-02840-6)

## Detailed Documentation

For comprehensive dataset information including structure, variables, and usage examples, see:
- 📖 [**Georgia Tech 2023 Dataset Documentation**](../../../docs/datasets_documentation/dataset_gtech_2023.md)

## Downloading the Data

1. Visit the Georgia Tech SmartTech repository: https://repository.gatech.edu/entities/publication/20860ffb-71fd-4049-a033-cd0ff308339e
2. Download the following files:
   - **RawDataset.zip** (for time-indexed conversion)
   - **ProcessedData_Standard_Gtech.zip** (for phase-indexed conversion)
3. Extract the downloaded files to the expected directory structure below

## Expected File Structure

Before running the conversion scripts, organize your data as follows:

```
Gtech_2023/
├── RawData/                         # Extract RawDataset.zip here
│   ├── AB01/
│   │   ├── incline_walk_1.csv
│   │   ├── normal_walk_1.csv
│   │   └── ...
│   ├── AB02/
│   │   └── ...
│   └── Subject_masses.csv
├── ProcessedData_Standard_Gtech/    # Extract ProcessedData_Standard_Gtech.zip here
│   ├── AB01_segmented.mat
│   ├── AB02_segmented.mat
│   └── ...
├── convert_gtech_all_to_parquet.py  # Time-indexed converter
├── convert_gtech_phase_to_parquet.m # Phase-indexed converter
└── combine_subjects_efficient.py     # Combines individual subject files
```

## Entry Points for Conversion

### 1. Time-Indexed Dataset Generation

```bash
# Main entry point - converts all subjects to time-indexed parquet
python convert_gtech_all_to_parquet.py

# Or convert a single subject
python convert_gtech_all_to_parquet.py AB01

# This will create:
# - converted_datasets/gtech_2023_time.parquet (all subjects)
# - converted_datasets/gtech_2023_time_AB01.parquet (single subject)
```

### 2. Phase-Indexed Dataset Generation

```matlab
% In MATLAB, navigate to this directory and run:
convert_gtech_phase_to_parquet

% This will create:
% - converted_datasets/gtech_2023_phase.parquet
```

### 3. Combining Individual Subject Files

If you've converted subjects individually:

```bash
python combine_subjects_efficient.py

# This will combine all individual subject files into:
# - converted_datasets/gtech_2023_time.parquet
```

## Processing Details

### Time-Indexed Data 

Usage Information
* Sampling rate = 100Hz

Usage notes:
* Currently this does not include detalied task segmentation such as different walking speeds. 

# Phase indexed data

The "convert_gtech_nc_segmented_to_parquet.m" script converts the data from the segmented portion of the dataset to the tabular format.

Usage Information
* Points per step = 150

Usage configuration
* Phase synchronization: When this flag is set to true, the phases for the right leg and the left leg will both be set to zero. When this flag is false, one leg will have a 50% phase offset so that the the time axis for the left and the right leg are approximately the same.

Usage notes
* Many of the right leg data is missing since there was a hardware error and force plate data could not be collected. Since segmentation of the right foot data could not be

# Task naming

normal_walking -> level_walking

incline_walking (+-) -> inline_walking(+) & decline_walking(-)

stairs (+-) -> stairs_up (+) & stairs_down (-)
