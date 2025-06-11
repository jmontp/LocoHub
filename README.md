# Locomotion Data Standardization

Easy-to-use, cleaned up and tested biomechanical datasets that enable reproducible results across studies.

**Quick Links:** [Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) • [Standard Spec](docs/standard_spec/standard_spec.md) • [Python Tutorial](docs/tutorials/python/getting_started_python.md)

## Use Cases

---

### 1. Standard Specification Reference
*Download the tables and manage them yourself*

Use the standardized variable names and data format in your own work:
- **Variable naming**: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`  
- **Time indexing**: Original sampling rate preserved
- **Phase indexing**: 150 points per normalized gait cycle
- **Reference**: [Data Format Spec](docs/standard_spec/standard_spec.md)

---

### 2. Data Analysis Library
*Use library code to help manage the tables*

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

---

### 3. Dataset Development
*Contribute new datasets to the standard*

Convert new datasets or contribute to the project:

1. **Create conversion scripts** following existing patterns
2. **Fill out dataset documentation** using [Dataset Template](docs/standard_spec/dataset_template.md)
3. **Submit validation report** with `python source/validation/dataset_validator_phase.py --dataset your_dataset_phase.parquet`
4. **Follow pull request guidelines** in [Contributing Guide](CONTRIBUTING.md)

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

## Contribution Process

To contribute a new dataset:

1. **Create conversion scripts** following existing patterns in `source/conversion_scripts/`
2. **Fill out dataset documentation** using [Dataset Template](docs/standard_spec/dataset_template.md)  
3. **Submit validation report** with `python source/validation/dataset_validator_phase.py --dataset your_dataset_phase.parquet`
4. **Follow pull request guidelines** in [Contributing Guide](CONTRIBUTING.md)

## Future

Release standardized datasets with train/test benchmarks to accelerate biomechanics research and enable reproducible ML-based control algorithms for prosthetics and exoskeletons.

---

<div align="center">
Made with ❤️ for the biomechanics community
</div>