# Locomotion Data Standardization

Standardized biomechanical datasets for cross-study analysis.

**Quick Links:** [Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) • [Standard Spec](docs/standard_spec/standard_spec.md) • [Python Tutorial](docs/tutorials/python/getting_started_python.md)

## Use Cases

### Standard Specification Reference
Use the standardized variable names and data format in your own work:
- **Variable naming**: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`  
- **Time indexing**: Original sampling rate preserved
- **Phase indexing**: 150 points per normalized gait cycle
- **Reference**: [Data Format Spec](docs/standard_spec/standard_spec.md)

### Data Analysis Library  
Load and analyze standardized datasets with optimized 3D array operations:

**Python:**
```python
sys.path.append('source/lib/python')
from locomotion_analysis import LocomotionData
data = LocomotionData.from_parquet('dataset.parquet')
data_3d = data.to_3d_array(['knee_flexion_angle_ipsi_rad'])
```

**MATLAB:**
```matlab
addpath('source/lib/matlab')
data = LocomotionData('dataset.parquet');
knee_angles = data.get_variable('knee_flexion_angle_ipsi_rad');
```

**Tutorials**: [Python](docs/tutorials/python/getting_started_python.md) • [MATLAB](docs/tutorials/matlab/getting_started_matlab.md)

### Dataset Development
Convert new datasets or contribute to the project:

```bash
# Convert new datasets
python source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py
python source/conversion_scripts/Gtech_2023/convert_gtech_all_to_parquet.py
matlab -batch "convert_umich_phase_to_parquet"

# Validate outputs
python source/validation/dataset_validator_phase.py --dataset your_dataset.parquet
```

**Reference**: [Contributing Guide](CONTRIBUTING.md)

## Available Datasets

- **AddBiomechanics**: Multiple subjects, full 3D biomechanics
- **GTech 2023**: 13 subjects, 19 activities + EMG/IMU  
- **UMich 2021**: 10 subjects, incline walking

[Download Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0)

## Documentation

- [Data Format Spec](docs/standard_spec/standard_spec.md)
- [Python Tutorial](docs/tutorials/python/getting_started_python.md)
- [MATLAB Tutorial](docs/tutorials/matlab/getting_started_matlab.md)

---

<div align="center">
Made with ❤️ for the biomechanics community
</div>