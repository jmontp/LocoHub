# Locomotion Data Standardization

Standardized biomechanical datasets for cross-study analysis.

**Quick Links:** [Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) • [Python Tutorial](docs/tutorials/python/getting_started_python.md) • [MATLAB Tutorial](docs/tutorials/matlab/getting_started_matlab.md)

## What It Does

Converts research datasets to standardized format:
- **Naming**: `knee_flexion_angle_ipsi_rad`
- **Time indexing**: Original sampling rate
- **Phase indexing**: 150 points per gait cycle  
- **Validation**: Biomechanical constraints + data quality
- **Analysis**: Optimized 3D array operations

## Install

```bash
git clone https://github.com/your-username/locomotion-data-standardization.git
cd locomotion-data-standardization
pip install -r requirements.txt
```

## Quick Start

**Python:**
```python
from locomotion_analysis import LocomotionData
data = LocomotionData.from_parquet('dataset.parquet')
data_3d = data.to_3d_array(['knee_flexion_angle_ipsi_rad'])
```

**MATLAB:**
```matlab
data = LocomotionData('dataset.parquet');
knee_angles = data.get_variable('knee_flexion_angle_ipsi_rad');
```

## Data Format

**Variables:** `<joint>_<motion>_<measurement>_<side>_<unit>`  
**Example:** `knee_flexion_angle_ipsi_rad`

**Includes:** Joint angles, moments, ground reaction forces, metadata

## Datasets

- **AddBiomechanics**: Multiple subjects, full 3D biomechanics
- **GTech 2023**: 13 subjects, 19 activities + EMG/IMU  
- **UMich 2021**: 10 subjects, incline walking

[Download Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0)

## Convert Data

```bash
# AddBiomechanics
python source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py

# GTech 2023
python source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py

# UMich 2021 (MATLAB)
matlab -batch "convert_umich_phase_to_parquet"
```

## Documentation

- [Python Tutorial](docs/tutorials/python/getting_started_python.md)
- [MATLAB Tutorial](docs/tutorials/matlab/getting_started_matlab.md)  
- [Data Format Spec](docs/standard_spec/standard_spec.md)

---

<div align="center">
Made with ❤️ for the biomechanics community
</div>