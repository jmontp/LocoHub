# PM ONGOING - Data Conversion Scripts

## High Level Tasks

### 1. AddBiomechanics Dataset Conversion
- **Description**: Convert AddBiomechanics B3D files to standardized parquet format with proper phase calculation
- **Status**: ✅ PRODUCTION READY

### 2. GTech 2023 Dataset Processing  
- **Description**: Process GTech 2023 motion capture data with efficient subject combination and validation
- **Status**: ✅ PRODUCTION READY

### 3. UMich 2021 Dataset Integration
- **Description**: Convert UMich 2021 MATLAB data structures to standardized format with proper metadata
- **Status**: ✅ PRODUCTION READY

## Recent Work (Last 15 Items)

### Historical Context
1. **AddBiomechanics Processing Pipeline** - Established conversion from B3D to parquet format
   - Implemented b3d_to_parquet.py for efficient data extraction
   - Added phase calculation and task naming standardization
   - Created validation scripts for converted AddBiomechanics data
   - Established processing workflow for large-scale biomechanics datasets

2. **GTech 2023 Efficient Processing** - Optimized subject combination and data processing
   - Implemented combine_subjects_efficient.py for memory-efficient processing
   - Created convert_gtech_all_to_parquet.py for batch conversion
   - Added segmentation processing for individual subjects (AB01-AB13)
   - Established benchmark processing for performance optimization

3. **UMich 2021 MATLAB Integration** - Converted MATLAB data structures to standardized format
   - Implemented convert_umich_phase_to_parquet.m for phase-based data
   - Created convert_umich_time_to_parquet.m for time-series data
   - Documented MATLAB structure format in umich_2021_mat_structure.md
   - Added validation scripts for UMich data verification

## Context Scratchpad

### Dataset Conversion Status
- **AddBiomechanics**: ✅ B3D to parquet pipeline established
- **GTech 2023**: ✅ Motion capture processing with efficient subject combination  
- **UMich 2021**: ✅ MATLAB to parquet conversion implemented

### Key Conversion Scripts
- **AddBiomechanics**: `b3d_to_parquet.py`, `convert_addbiomechanics_to_parquet.py`
- **GTech 2023**: `combine_subjects_efficient.py`, `convert_gtech_all_to_parquet.py`
- **UMich 2021**: `convert_umich_phase_to_parquet.m`, `convert_umich_time_to_parquet.m`

### Data Processing Commands
- `python convert_addbiomechanics_to_parquet.py` - Convert AddBiomechanics datasets
- `python combine_subjects_efficient.py` - Process GTech 2023 subjects efficiently
- `matlab -batch "convert_umich_phase_to_parquet"` - Convert UMich phase data

### Output Standards
- **Format**: Parquet files with standardized column naming
- **Phase Calculation**: 0-100% normalized phase with 150 points per cycle
- **Validation**: All converted datasets validated against specification requirements
- **Metadata**: Proper subject, task, and experimental condition documentation