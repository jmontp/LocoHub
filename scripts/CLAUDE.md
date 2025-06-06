# CLAUDE.md - Scripts Directory

This file provides Claude Code guidance for working with the utility and validation scripts in this directory.

## Directory Overview

The `scripts/` directory contains utility scripts for validation, analysis, plotting, and dataset management. These are standalone tools that operate on the standardized Parquet files produced by the conversion scripts.

## Script Categories

### 🔍 Validation Scripts

#### `validate_all_datasets.sh`
**Purpose**: Automated validation pipeline for all datasets
**Usage**: `./validate_all_datasets.sh`
**Output**: Timestamped reports in `../validation_reports/`

**What it does**:
1. Checks Python dependencies (pandas, numpy, plotly, pyarrow)
2. Runs validation on all found datasets (GTech 2023, UMich 2021, AddBiomechanics)
3. Generates validation reports, mosaic plots, and diagnostic GIFs
4. Creates summary report with findings and next steps

**When to use**:
- After converting new datasets
- Before releasing dataset versions
- During development to check data quality
- For comprehensive validation reporting

#### `memory_safe_validator.py`
**Purpose**: Validate large Parquet files without memory issues
**Usage**: `python memory_safe_validator.py <parquet_file>`
**Features**:
- Chunk-based processing for files >1GB
- Phase vs time-indexed data detection
- Memory usage monitoring
- Safe validation for very large datasets

**When to use**:
- Validating large AddBiomechanics datasets
- When encountering memory errors with standard validation
- For production validation of large datasets

### 📊 Analysis and Plotting Scripts

#### `comprehensive_mosaic_plot.py`
**Purpose**: Generate comprehensive multi-task comparison plots
**Usage**: `python comprehensive_mosaic_plot.py --input <parquet_file>`
**Features**:
- Multi-task visualization
- Statistical overlays
- Export to PNG/HTML
- Task-specific analysis

#### `mosaic_plot_3d_efficient.py`
**Purpose**: High-performance 3D visualization of biomechanical data
**Usage**: `python mosaic_plot_3d_efficient.py --input <parquet_file>`
**Features**:
- Optimized 3D array operations
- Interactive 3D plots
- Performance benchmarking
- Memory-efficient processing

#### `generate_validation_gifs.py`
**Purpose**: Create animated validation visualizations
**Usage**: `python generate_validation_gifs.py --input <parquet_file>`
**Features**:
- Animated stick figure walking
- Validation overlay animations
- GIF export for documentation
- Sample subject/task selection

### 🔧 Utility Scripts

#### `check_file_structure.py`
**Purpose**: Verify Parquet file structure and schema compliance
**Usage**: `python check_file_structure.py <parquet_file>`
**Checks**:
- Required columns present
- Data types correct
- Schema compliance with standard
- File integrity

#### `check_parquet_structure.py`
**Purpose**: Detailed Parquet metadata analysis
**Usage**: `python check_parquet_structure.py <parquet_file>`
**Features**:
- Schema inspection
- Compression analysis
- Row group information
- Storage optimization suggestions

#### `quick_phase_check.py`
**Purpose**: Fast validation of phase-indexed data
**Usage**: `python quick_phase_check.py <phase_parquet_file>`
**Checks**:
- 150 points per cycle compliance
- Phase percentage validation
- Cycle completeness
- Quick error detection

#### `compare_plotting_performance.py`
**Purpose**: Benchmark plotting performance across different methods
**Usage**: `python compare_plotting_performance.py`
**Features**:
- Performance comparison of visualization methods
- Memory usage analysis
- Speed benchmarks
- Optimization recommendations

#### `add_step_numbers.py`
**Purpose**: Add step numbering to gait cycle data
**Usage**: `python add_step_numbers.py --input <parquet_file>`
**Features**:
- Automatic step detection
- Step numbering for analysis
- Gait event identification

## Common Usage Patterns

### Running Full Validation Pipeline
```bash
# Comprehensive validation (creates reports)
./validate_all_datasets.sh

# Check specific dataset with memory safety
python memory_safe_validator.py converted_datasets/gtech_2023_phase.parquet

# Quick phase validation
python quick_phase_check.py converted_datasets/gtech_2023_phase.parquet
```

### Generating Visualizations
```bash
# Comprehensive plots for all tasks
python comprehensive_mosaic_plot.py --input converted_datasets/gtech_2023_phase.parquet

# 3D visualization with performance optimization
python mosaic_plot_3d_efficient.py --input converted_datasets/gtech_2023_phase.parquet

# Create validation animations
python generate_validation_gifs.py --input converted_datasets/gtech_2023_phase.parquet
```

### File Structure Verification
```bash
# Check file structure compliance
python check_file_structure.py converted_datasets/gtech_2023_phase.parquet

# Detailed Parquet analysis
python check_parquet_structure.py converted_datasets/gtech_2023_phase.parquet
```

## Script Dependencies

### Common Python Requirements
Most scripts require:
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `pyarrow` - Parquet file handling
- `matplotlib` - Basic plotting
- `plotly` - Interactive visualizations

### Additional Dependencies by Script
- **Validation scripts**: `scipy` for statistical analysis
- **3D plotting**: `plotly`, `kaleido` for exports
- **Animation scripts**: `matplotlib.animation`, `pillow` for GIF creation
- **Performance scripts**: `memory_profiler`, `time` for benchmarking

### Installation
```bash
# Basic requirements
pip install pandas numpy pyarrow matplotlib plotly

# Additional for animations and exports
pip install pillow kaleido memory_profiler

# For development and benchmarking
pip install scipy scikit-learn
```

## Output Locations

### Validation Reports
- **Location**: `../validation_reports/<timestamp>/`
- **Contents**: 
  - `*_validation.csv` - Detailed error reports
  - `*_validation.log` - Processing logs
  - `VALIDATION_SUMMARY.md` - Summary report

### Generated Plots
- **Location**: `../source/visualization/plots/`
- **Subdirectories**:
  - `comprehensive_<dataset>/` - Task comparison plots
  - `validated_<dataset>/` - Validation-filtered plots
  - `png/` - Static PNG exports

### Animations and GIFs
- **Location**: Varies by script, typically in working directory or `plots/`
- **Naming**: `<subject>_<task>_animation.gif`

## Integration with Other Components

### With Conversion Scripts
- Scripts operate on outputs from `../source/conversion_scripts/`
- Validation feeds back to conversion process for improvements
- File structure checks ensure conversion compliance

### With Source Libraries
- Plotting scripts use `../source/lib/python/locomotion_analysis.py`
- Validation scripts import from `../source/tests/validation_blueprint.py`
- Performance scripts benchmark library operations

### With Documentation
- Validation reports reference `../docs/standard_spec/` for compliance rules
- Error codes link to validation documentation
- Plot outputs support tutorial documentation

## Best Practices for Script Usage

### Before Running Scripts
1. **Check dependencies**: Ensure required packages are installed
2. **Verify input files**: Confirm Parquet files exist and are accessible
3. **Check disk space**: Some operations generate large outputs
4. **Review documentation**: Check script-specific help with `--help` flag

### Performance Considerations
- **Large files**: Use memory-safe variants for files >1GB
- **Batch processing**: Consider parallelization for multiple datasets
- **Output management**: Clean up old validation reports and plots regularly
- **Resource monitoring**: Monitor CPU and memory usage during processing

### Error Handling
- **Validation failures**: Check error codes against validation documentation
- **Memory errors**: Use chunk-based or memory-safe alternatives
- **File errors**: Verify file permissions and disk space
- **Dependency errors**: Check package versions and installation

## Script Development Guidelines

### Adding New Scripts
1. Follow naming convention: `<function>_<detail>.py`
2. Include detailed docstring with usage examples
3. Add command-line argument parsing with `--help`
4. Handle common errors gracefully
5. Output progress information for long-running operations
6. Update this CLAUDE.md file with new script information

### Modifying Existing Scripts
1. Test with multiple dataset types (time vs phase-indexed)
2. Ensure backward compatibility with existing outputs
3. Update documentation and help text
4. Test memory usage with large files
5. Validate outputs against expected results

## Troubleshooting Common Issues

### Validation Script Issues
- **"Missing required packages"**: Install with pip as shown above
- **"File not found"**: Check file paths and ensure datasets are converted
- **"Memory error"**: Use `memory_safe_validator.py` instead
- **"Permission denied"**: Check file permissions and disk space

### Plotting Script Issues
- **"No display available"**: Use headless matplotlib backend
- **"Plotly export fails"**: Install `kaleido` for static exports
- **"GIF creation fails"**: Install `pillow` for animation support
- **"Interactive plots don't show"**: Use appropriate backend for environment

### Performance Issues
- **Slow processing**: Use optimized 3D array operations where available
- **High memory usage**: Process in chunks or use streaming approaches
- **Large output files**: Compress or reduce resolution as appropriate

This scripts directory provides the operational tools for working with standardized locomotion data, supporting validation, analysis, and visualization workflows across the entire project.