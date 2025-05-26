# AddBiomechanics Dataset

## Overview

The AddBiomechanics dataset provides comprehensive 3D biomechanical data processed through the AddBiomechanics pipeline, which uses OpenSim-based musculoskeletal modeling and inverse dynamics.

## Dataset Information

- **Source Institution**: Stanford Neuromuscular Biomechanics Lab
- **Year**: Ongoing collection
- **Format**: B3D (Biomechanics 3D) files
- **Website**: https://addbiomechanics.org/
- **Paper**: [AddBiomechanics: Automating model scaling, inverse kinematics, and inverse dynamics from human motion data through sequential optimization](https://doi.org/10.1101/2023.06.15.545116)

## Citation

```bibtex
@article{addbiomechanics2023,
  title={AddBiomechanics: Automating model scaling, inverse kinematics, and inverse dynamics from human motion data through sequential optimization},
  author={Werling, Keenon and Bianco, Nicholas A. and Raitor, Michael and Stingel, Jon and Hicks, Jennifer L. and Collins, Steven H. and Delp, Scott L. and Liu, C. Karen},
  journal={bioRxiv},
  year={2023},
  doi={10.1101/2023.06.15.545116}
}
```

## Data Structure

### Available Variables
- **Kinematics**: Full-body joint angles, velocities, and accelerations
- **Kinetics**: Joint moments and powers
- **Ground Reaction Forces**: 3D forces and center of pressure
- **Segment Kinematics**: Global positions and orientations

### File Format
- **Input**: B3D binary files containing trial data
- **Output**: Standardized parquet files (time-indexed and phase-indexed)

### Coordinate System
- OpenSim standard: X-forward, Y-up, Z-right
- Joint angles follow OpenSim conventions

## Processing Pipeline

1. **B3D Parsing**: Extract biomechanical data using nimblephysics
2. **Variable Mapping**: Convert to standardized naming convention
3. **Unit Conversion**: Ensure SI units (rad, N, m)
4. **Phase Detection**: Identify gait cycles from kinematics
5. **Validation**: Apply biomechanical constraints

## Usage Example

```python
# Convert B3D files to standardized format
python source/conversion_scripts/AddBiomechanics/convert_addbiomechanics_to_parquet.py

# Add phase information
python source/conversion_scripts/AddBiomechanics/add_phase_info.py

# Load converted data
import pandas as pd
df = pd.read_parquet('converted_datasets/addbiomechanics_time.parquet')
```

## Notes

- Data includes full 3D kinematics and kinetics
- Suitable for machine learning applications
- Pre-processed through OpenSim pipeline
- Includes marker data and model scaling information