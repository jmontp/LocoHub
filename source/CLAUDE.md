# CLAUDE.md - Source Directory

This file provides Claude Code guidance for working with the core source code in this directory.

## Directory Overview

The `source/` directory contains the core implementation of the Locomotion Data Standardization framework, including conversion scripts, libraries, validation systems, and visualization tools.

## Directory Structure

```
source/
├── conversion_scripts/           # Dataset-specific conversion implementations
│   ├── AddBiomechanics/         # OpenSim/AddBiomechanics dataset conversion
│   ├── Gtech_2023/              # Georgia Tech 2023 dataset conversion  
│   ├── Umich_2021/              # University of Michigan 2021 dataset conversion
│   └── CONSOLIDATION_PLAN.md    # Future conversion consolidation strategy
├── lib/                         # Core analysis libraries
│   ├── python/                  # Python implementation
│   └── matlab/                  # MATLAB implementation
├── tests/                       # Validation and testing framework
├── visualization/               # Plotting and animation tools
└── naming_convention_mapping.py # Variable name standardization utilities
```

## Core Components

### 1. Conversion Scripts (`conversion_scripts/`)
**Purpose**: Transform raw research datasets into standardized Parquet format

**Architecture**:
- Each dataset has its own subdirectory with specific conversion logic
- Common patterns: load raw data → standardize variables → validate → export Parquet
- Both time-indexed and phase-indexed outputs supported

**Key Features**:
- Dataset-specific format handling (B3D, MATLAB .mat, CSV)
- Standardized variable naming following `<joint>_<motion>_<measurement>_<side>_<unit>`
- Phase normalization to 150 points per gait cycle
- Metadata extraction and standardization

### 2. Core Libraries (`lib/`)
**Purpose**: Provide unified analysis interface for standardized data

#### Python Library (`lib/python/`)
**Main Class**: `LocomotionData` in `locomotion_analysis.py`

**Key Features**:
- **Efficient 3D array operations** (100x faster than pandas groupby)
- **Dual indexing support** (time and phase-based data)
- **Integrated validation** using validation blueprint
- **Statistical analysis** and phase pattern extraction
- **Visualization integration** with plotting tools

**Core Methods**:
- `from_parquet()` - Load standardized datasets
- `to_3d_array()` - Convert to efficient 3D arrays for analysis
- `validate_data()` - Run 5-layer validation system
- `calculate_statistics()` - Compute descriptive statistics
- `plot_phase_patterns()` - Generate phase-normalized plots

#### MATLAB Library (`lib/matlab/`)
**Main Class**: `LocomotionData` in `LocomotionData.m`

**Features**:
- **Feature parity** with Python implementation
- **Native MATLAB integration** with existing workflows
- **Optimized for MATLAB** data structures and operations
- **Cross-platform compatibility** with Python-generated datasets

### 3. Validation System (`tests/`)
**Purpose**: Ensure data quality and standard compliance

#### `validation_blueprint.py` - Core Validator
**5-Layer Validation System**:
1. **Pre-checks** (Codes 1-9): Column existence, naming, vocabulary
2. **Layer 0** (Codes 10-29): Global sanity checks (ranges, units)
3. **Layer 1-2** (Codes 30-49): Biomechanical envelopes (baseline + task-specific)
4. **Layer 3** (Codes 50-59): Physics consistency (power analysis)
5. **Layer 4** (Codes 60-69): Subject heuristics (neutral pose)

#### `validation_blueprint_enhanced.py` - Advanced Validator
**Enhanced Features**:
- **Comprehensive mode**: Collects all validation errors
- **Detailed reporting**: Human-readable error descriptions
- **Export capabilities**: CSV reports with failure analysis
- **Error tracking**: Multiple error codes per data point

### 4. Visualization Tools (`visualization/`)
**Purpose**: Generate plots, animations, and visual validation

**Key Scripts**:
- `mozaic_plot.py` - Multi-task comparison plots
- `mosaic_plot_validated.py` - Validation-integrated plotting
- `walking_animator.py` - Animated stick figure visualizations
- `mosaic_plot_with_failure_analysis.py` - Error analysis plots

**Features**:
- **Task comparison visualizations** across multiple activities
- **Validation overlay plots** showing data quality
- **Interactive plotting** with Plotly integration
- **Animation generation** for documentation and validation
- **Performance optimization** for large datasets

## Development Patterns and Standards

### Code Organization Principles
1. **Dataset-specific conversion** in isolated subdirectories
2. **Common functionality** in shared libraries
3. **Validation as a service** used by all components
4. **Visualization as post-processing** operating on standardized data

### Variable Naming Standards
**Pattern**: `<joint>_<motion>_<measurement>_<side>_<unit>`

**Examples**:
- `knee_flexion_angle_right_rad`
- `hip_moment_left_Nm`
- `ankle_flexion_velocity_left_rad_s`

**Implementation**: `naming_convention_mapping.py` provides utilities for:
- Variable name standardization
- Legacy name mapping
- Unit conversion helpers
- Validation of naming compliance

### Data Format Standards
**Time-indexed Data**:
- Preserves original sampling frequency
- Includes `time_s` column with monotonic progression
- Suitable for temporal analysis and event detection

**Phase-indexed Data**:
- Normalized to 150 points per gait cycle
- Includes `phase_%` column (0-100%)
- Suitable for cross-subject comparison and averaging

### Error Handling Patterns
1. **Graceful degradation**: Missing data handled as NaN
2. **Informative errors**: Clear error messages with context
3. **Validation integration**: All outputs validated before export
4. **Logging**: Comprehensive logging for debugging

## Integration Between Components

### Conversion → Validation → Library → Visualization Flow
```
Raw Data → Conversion Scripts → Standardized Parquet → Validation → Library Classes → Visualization
```

### Cross-Component Dependencies
- **Conversion scripts** use validation system for output verification
- **Libraries** integrate validation for data quality assurance
- **Visualization** tools use library classes for data access
- **All components** follow specifications in `../../docs/standard_spec/`

### Data Flow Patterns
1. **Load**: Raw data loaded by dataset-specific conversion scripts
2. **Transform**: Data standardized using naming conventions and format rules
3. **Validate**: Output validated using 5-layer validation system
4. **Export**: Standardized Parquet files created for both time and phase indexing
5. **Analyze**: Library classes provide efficient access and analysis
6. **Visualize**: Plotting tools generate insights and validation plots

## Common Development Tasks

### Adding Support for a New Dataset
1. **Create conversion directory**: `conversion_scripts/<DatasetName>/`
2. **Implement conversion script**: Following existing patterns
3. **Add validation rules**: Dataset-specific rules if needed
4. **Test integration**: Ensure library compatibility
5. **Update documentation**: Create dataset documentation
6. **Add visualizations**: Dataset-specific plotting if needed

### Adding New Biomechanical Variables
1. **Define variable name**: Following naming convention
2. **Update validation rules**: Add to appropriate validation layers
3. **Extend library support**: Add to LocomotionData classes
4. **Update conversion scripts**: Include in relevant datasets
5. **Add visualization**: Support in plotting tools
6. **Document specification**: Update standard documentation

### Modifying Validation Rules
1. **Update validation blueprint**: Modify validation layers
2. **Test on existing datasets**: Ensure no false positives
3. **Update error documentation**: Add new error codes
4. **Regenerate validation reports**: Check impact on datasets
5. **Update library integration**: Ensure compatibility

### Performance Optimization
1. **Profile code**: Identify bottlenecks in conversion/analysis
2. **Optimize 3D operations**: Use vectorized operations where possible
3. **Memory management**: Implement chunked processing for large datasets
4. **Caching strategies**: Cache frequently accessed data
5. **Parallel processing**: Use multiprocessing where appropriate

## Testing and Quality Assurance

### Validation Testing
- **Unit tests**: Individual validation rules tested
- **Integration tests**: Full validation pipeline tested
- **Regression tests**: Ensure changes don't break existing functionality
- **Performance tests**: Monitor validation speed and memory usage

### Library Testing
- **API tests**: Public methods tested with various inputs
- **Data integrity tests**: Ensure operations preserve data quality
- **Cross-platform tests**: Python and MATLAB compatibility
- **Performance benchmarks**: Monitor operation speed and efficiency

### Conversion Testing
- **Format compliance**: Outputs tested against standard specification
- **Data preservation**: Ensure no data loss during conversion
- **Edge case handling**: Test with problematic or incomplete data
- **Round-trip testing**: Verify data integrity through full pipeline

## Dependencies and Requirements

### Core Python Dependencies
```python
pandas>=1.5.0       # Data manipulation and analysis
numpy>=1.20.0       # Numerical computing
pyarrow>=10.0.0     # Parquet file handling
matplotlib>=3.5.0   # Basic plotting
plotly>=5.0.0       # Interactive visualizations
scipy>=1.8.0        # Scientific computing
```

### Conversion-Specific Dependencies
- **AddBiomechanics**: `nimblephysics`, `torch` (heavy physics simulation dependencies)
- **GTech/UMich**: Standard scientific Python stack
- **MATLAB**: R2019b+ with Signal Processing Toolbox

### Development Dependencies
```python
pytest>=7.0.0       # Testing framework
memory_profiler     # Memory usage monitoring  
black>=22.0.0       # Code formatting
flake8>=4.0.0       # Linting
jupyter>=1.0.0      # Notebook development
```

## Performance Considerations

### Memory Management
- **Chunked processing**: For datasets >1GB
- **Lazy loading**: Load data only when needed
- **Memory monitoring**: Track usage during operations
- **Garbage collection**: Explicit cleanup for large operations

### Computational Efficiency
- **Vectorized operations**: Use NumPy/pandas vectorization
- **3D array optimization**: Reshape for efficient mathematical operations
- **Caching**: Cache computed results for repeated access
- **Parallel processing**: Use multiprocessing for independent operations

### Storage Optimization
- **Parquet compression**: Use efficient compression algorithms
- **Data types**: Use appropriate dtypes to minimize storage
- **Column selection**: Load only required columns when possible
- **Indexing**: Use appropriate indexing for common access patterns

## Best Practices for Claude Code

### When Working with Source Code
1. **Follow established patterns**: Use existing conversion scripts as templates
2. **Validate early and often**: Run validation on all generated data
3. **Test with multiple datasets**: Ensure cross-dataset compatibility
4. **Document changes**: Update relevant documentation files
5. **Performance test**: Monitor memory and speed for large datasets

### Code Style and Standards
- **PEP 8 compliance**: Follow Python style guidelines
- **Descriptive naming**: Use clear, descriptive variable and function names
- **Comprehensive docstrings**: Document all public methods and classes
- **Error handling**: Implement robust error handling with informative messages
- **Testing**: Write tests for new functionality

### Integration Guidelines
- **Library first**: Use existing library functionality where possible
- **Validation integration**: Always validate outputs before export
- **Documentation updates**: Update relevant docs when changing functionality
- **Backward compatibility**: Maintain compatibility with existing datasets
- **Cross-platform testing**: Test Python and MATLAB implementations

This source directory represents the core implementation of the locomotion data standardization framework, providing the foundation for converting, validating, analyzing, and visualizing biomechanical datasets in a standardized format.