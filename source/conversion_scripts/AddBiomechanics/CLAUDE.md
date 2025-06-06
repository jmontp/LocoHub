# CLAUDE.md - AddBiomechanics Conversion Scripts

This file provides Claude Code guidance for working with the AddBiomechanics dataset conversion scripts.

## Overview

The AddBiomechanics conversion scripts transform 3D biomechanics data from OpenSim/AddBiomechanics B3D format into the standardized Parquet format. This is the most complex conversion in the project due to heavy dependencies and 3D biomechanics processing.

## Directory Structure

```
AddBiomechanics/
├── README.md                            # Main conversion documentation
├── requirements.txt                     # Heavy dependencies (nimblephysics, torch)
├── convert_addbiomechanics_to_parquet.py # Main B3D→Parquet converter
├── add_phase_info.py                    # Phase normalization (150 pts/cycle)  
├── add_task_info.py                     # Task metadata standardization
├── b3d_to_parquet.py                    # Core B3D file parser
├── extract_biomechanics_dataset.sh      # Data extraction utility
├── processing_Gtech_2021_timeparquet_to_phase.py # GTech subset processing
├── verify_addbiomechanics.ipynb         # Verification notebook
├── add_phase_info.ipynb                 # Phase analysis notebook
├── addbpqcarter2023tasknaming.ipynb     # Task naming analysis
├── zjytestfield.ipynb                   # Development notebook
└── Gtech_2021/                          # GTech 2021 subset processing
    ├── add_task_info.py                 # GTech-specific task standardization
    └── validate_dataset.py              # GTech-specific validation
```

## Key Scripts and Their Purposes

### 1. `convert_addbiomechanics_to_parquet.py` - Main Converter
**Purpose**: Primary conversion script from B3D files to standardized Parquet

**Input**: 
- B3D files from OpenSim/AddBiomechanics pipeline
- Raw 3D biomechanics data with full-body kinematics and kinetics

**Output**:
- Time-indexed Parquet files with standardized variable names
- Comprehensive biomechanical data (joint angles, moments, GRFs, segment kinematics)

**Key Features**:
- B3D format parsing using nimblephysics
- 3D coordinate transformations
- Standardized variable naming implementation
- Error handling for malformed B3D files

**Dependencies**: Requires `nimblephysics`, `torch` (heavy physics simulation libraries)

### 2. `add_phase_info.py` - Phase Normalization
**Purpose**: Convert time-indexed data to phase-normalized (150 points per gait cycle)

**Input**: Time-indexed Parquet files from main converter
**Output**: Phase-indexed Parquet files with `phase_%` column

**Processing Steps**:
1. **Gait event detection**: Identify heel strikes and toe-offs
2. **Cycle segmentation**: Extract individual gait cycles
3. **Phase normalization**: Interpolate to 150 points per cycle
4. **Quality validation**: Ensure phase data meets standards

**Key Algorithms**:
- Heel strike detection using vertical GRF and kinematic patterns
- Cubic spline interpolation for phase normalization
- Cycle quality assessment and filtering

### 3. `add_task_info.py` - Task Standardization
**Purpose**: Add standardized task metadata and naming to converted datasets

**Input**: Converted Parquet files (time or phase-indexed)
**Output**: Enhanced Parquet files with standardized task information

**Standardization Process**:
- Map original task names to standard vocabulary
- Add task-specific metadata (speed, incline, etc.)
- Ensure task naming compliance with controlled vocabulary
- Add task IDs for consistent referencing

**Task Mapping**: References `../../../docs/standard_spec/task_definitions.md`

### 4. `b3d_to_parquet.py` - Core Parser
**Purpose**: Low-level B3D file parsing and data extraction

**Features**:
- **Binary format handling**: Parse OpenSim B3D binary format
- **Data structure extraction**: Extract time series, metadata, and annotations
- **Error handling**: Robust parsing with graceful failure modes
- **Memory management**: Efficient handling of large B3D files

**Technical Details**:
- Uses nimblephysics for B3D format interpretation
- Handles multiple subjects and trials per B3D file
- Extracts full 3D biomechanics including:
  - Joint angles (all DOF)
  - Joint moments and powers
  - Ground reaction forces
  - Segment orientations and positions
  - Marker trajectories (if available)

## Processing Pipeline

### Standard Conversion Workflow
```
B3D Files → convert_addbiomechanics_to_parquet.py → Time-indexed Parquet
                                                          ↓
Phase-indexed Parquet ← add_phase_info.py ← add_task_info.py ← Metadata Enhancement
```

### Detailed Steps
1. **B3D Parsing**: Extract raw biomechanics data using `b3d_to_parquet.py`
2. **Variable Standardization**: Apply naming conventions and unit conversions
3. **Time-indexed Export**: Generate time-based Parquet files
4. **Task Standardization**: Add standardized task metadata
5. **Phase Processing**: Generate phase-normalized datasets (150 points/cycle)
6. **Validation**: Run through validation pipeline to ensure compliance

## Special Considerations

### Heavy Dependencies
**nimblephysics**: Physics simulation engine required for B3D parsing
- Large installation (>2GB)
- Requires specific Python versions
- May need compilation from source
- GPU acceleration optional but recommended

**torch**: Deep learning framework (dependency of nimblephysics)
- Another large installation
- CUDA support for GPU acceleration
- Version compatibility important

### Installation Process
```bash
# Navigate to AddBiomechanics directory
cd source/conversion_scripts/AddBiomechanics

# Install requirements (this will take time and space)
pip install -r requirements.txt

# Verify installation
python -c "import nimblephysics; print('Success')"
```

### Memory and Performance
- **Large datasets**: B3D files can be >1GB each
- **Memory usage**: Conversion process memory-intensive
- **Processing time**: Significant time for large datasets
- **Storage requirements**: Intermediate files need substantial disk space

## Data Quality and Validation

### Input Data Validation
- **B3D format verification**: Ensure files are valid B3D format
- **Completeness check**: Verify all required biomechanical variables present
- **Coordinate system validation**: Ensure proper OpenSim coordinate conventions

### Output Data Validation
- **Standard compliance**: All outputs validated against format specification
- **Phase calculation accuracy**: Verify 150-point normalization is correct
- **Variable naming**: Ensure all variables follow naming convention
- **Data integrity**: Verify no data loss during conversion

### Known Issues and Limitations
- **Right-leg data**: Some subjects may have incomplete right-leg data
- **Task identification**: Complex mapping from original to standard task names
- **Coordinate transformations**: Multiple coordinate frame conversions required
- **File size**: Output files can be very large (>1GB)

## Integration with Other Components

### With Validation System
- Outputs automatically validated using `../../tests/validation_blueprint.py`
- Enhanced validation available for detailed error analysis
- Custom validation rules for AddBiomechanics-specific issues

### With Analysis Libraries
- Converted data compatible with `../../lib/python/locomotion_analysis.py`
- Full 3D biomechanics data available for advanced analysis
- Integration with visualization tools for 3D plotting

### With Documentation
- **Main README**: `README.md` - detailed usage instructions
- **Dataset documentation**: `../../../docs/datasets_documentation/dataset_addbiomechanics.md`
- **Format specification**: `../../../docs/standard_spec/standard_spec.md`

## Development and Debugging

### Common Issues
**Installation Problems**:
- nimblephysics installation failures
- CUDA/GPU compatibility issues
- Python version conflicts

**Conversion Errors**:
- Malformed B3D files
- Missing biomechanical variables
- Coordinate system inconsistencies
- Memory exhaustion during processing

**Output Issues**:
- Phase detection failures
- Task mapping errors
- Validation failures
- File size concerns

### Debugging Tools
- **Jupyter notebooks**: Available for interactive development and debugging
- **Verification notebook**: `verify_addbiomechanics.ipynb` for output validation
- **Phase analysis**: `add_phase_info.ipynb` for phase calculation debugging
- **Task naming**: `addbpqcarter2023tasknaming.ipynb` for task mapping analysis

### Testing and Verification
```bash
# Test B3D parsing
python b3d_to_parquet.py --input sample.b3d --output test.parquet

# Test full conversion pipeline
python convert_addbiomechanics_to_parquet.py --input_dir ./b3d_files/ --output_dir ./converted/

# Test phase normalization
python add_phase_info.py --input converted/dataset_time.parquet --output converted/dataset_phase.parquet

# Validate outputs
python ../../tests/validation_blueprint_enhanced.py --input converted/dataset_phase.parquet
```

## Best Practices for Claude Code

### When Working with AddBiomechanics Conversion
1. **Check dependencies first**: Verify nimblephysics and torch are properly installed
2. **Monitor memory usage**: AddBiomechanics processing is memory-intensive
3. **Validate intermediate outputs**: Check data quality at each processing step
4. **Use notebooks for debugging**: Leverage existing Jupyter notebooks for development
5. **Test with small datasets**: Verify pipeline with subset before full processing

### Performance Optimization
- **Chunk processing**: Process large B3D files in chunks if memory limited
- **Parallel processing**: Use multiprocessing for multiple B3D files
- **Disk management**: Monitor disk space during conversion
- **Memory monitoring**: Track memory usage and clean up intermediate variables

### Error Handling
- **Graceful degradation**: Handle missing data as NaN rather than failing
- **Informative logging**: Provide detailed error messages with context
- **Partial results**: Save intermediate results to avoid complete loss on failure
- **Recovery mechanisms**: Implement checkpointing for long-running conversions

This AddBiomechanics conversion represents the most technically complex part of the standardization pipeline, requiring careful attention to dependencies, memory management, and data quality validation.