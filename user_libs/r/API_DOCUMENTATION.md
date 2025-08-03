# LocomotionData R Library - Complete API Documentation

**Version**: 1.0.0  
**Created**: 2025-06-19  
**Purpose**: Complete API reference for the R LocomotionData library

## Overview

The LocomotionData R library provides a comprehensive S4 class system for loading, analyzing, and visualizing phase-indexed biomechanical data. It mirrors the Python LocomotionData API while leveraging R's strengths in statistical analysis and data.table for performance.

## Quick Start

```r
library(LocomotionData)

# Load phase-indexed data
loco <- loadLocomotionData("gait_data.parquet")

# Basic analysis
data_3d <- getCycles(loco, "SUB01", "normal_walk")
mean_patterns <- getMeanPatterns(loco, "SUB01", "normal_walk")
rom_data <- calculateROM(loco, "SUB01", "normal_walk")

# Quality assessment
valid_mask <- validateCycles(loco, "SUB01", "normal_walk")
outliers <- findOutlierCycles(loco, "SUB01", "normal_walk")

# Visualization
plotPhasePatterns(loco, "SUB01", "normal_walk", 
                 c("knee_flexion_angle_contra_rad"))
```

## Core S4 Class

### LocomotionData Class

The main S4 class for locomotion data analysis with efficient 3D array operations.

**Slots:**
- `data`: data.table containing raw locomotion data
- `subjects`: character vector of unique subject IDs
- `tasks`: character vector of unique task names
- `features`: character vector of biomechanical feature names
- `data_path`: character path to original data file
- `subject_col`: character name of subject column
- `task_col`: character name of task column
- `phase_col`: character name of phase column
- `feature_mappings`: named list mapping feature names to column names
- `validation_report`: list containing variable name validation results
- `cache`: list for caching 3D array results
- `points_per_cycle`: integer number of points per gait cycle (150)

## Core Analysis Methods

### Data Access Methods

#### `getSubjects(object)`
Get list of unique subjects.

**Returns:** character vector of subject IDs

#### `getTasks(object)`
Get list of unique tasks.

**Returns:** character vector of task names

#### `getFeatures(object)`
Get list of available biomechanical features.

**Returns:** character vector of feature names

#### `getCycles(object, subject, task, features = NULL)`
Get 3D array of cycles for a subject-task combination.

**Parameters:**
- `subject`: character subject ID
- `task`: character task name
- `features`: character vector of features (optional, uses all if NULL)

**Returns:** list with `data_3d` (array of shape n_cycles × 150 × n_features) and `feature_names`

### Statistical Analysis Methods

#### `getMeanPatterns(object, subject, task, features = NULL)`
Get mean patterns for each feature.

**Returns:** named list mapping feature names to mean patterns (150 points)

#### `getStdPatterns(object, subject, task, features = NULL)`
Get standard deviation patterns for each feature.

**Returns:** named list mapping feature names to std patterns (150 points)

#### `getSummaryStatistics(object, subject, task, features = NULL)`
Get comprehensive summary statistics for all features.

**Returns:** data.frame with mean, std, min, max, median, q25, q75

#### `calculateROM(object, subject, task, features = NULL, by_cycle = TRUE)`
Calculate Range of Motion (ROM) for features.

**Parameters:**
- `by_cycle`: logical, if TRUE calculate ROM per cycle, if FALSE overall ROM

**Returns:** named list with ROM values for each feature

#### `getPhaseCorrelations(object, subject, task, features = NULL)`
Calculate correlation between features at each phase point.

**Returns:** array of shape (150, n_features, n_features) with correlation matrices

### Quality Assessment Methods

#### `validateCycles(object, subject, task, features = NULL)`
Validate cycles based on biomechanical constraints.

**Returns:** logical vector indicating valid cycles

#### `findOutlierCycles(object, subject, task, features = NULL, threshold = 2.0)`
Find outlier cycles based on deviation from mean pattern.

**Parameters:**
- `threshold`: numeric, number of standard deviations for outlier threshold

**Returns:** integer vector of outlier cycle indices

#### `getValidationReport(object)`
Get variable name validation report.

**Returns:** list with validation components (standard_compliant, non_standard, warnings, errors)

### Multi-Subject/Multi-Task Analysis

#### `getMultiSubjectStatistics(object, subjects = NULL, task, features = NULL)`
Get summary statistics across multiple subjects for a single task.

**Parameters:**
- `subjects`: character vector of subject IDs (NULL for all subjects)

**Returns:** data.frame with group statistics including between-subject variability

#### `getMultiTaskStatistics(object, subject, tasks = NULL, features = NULL)`
Get summary statistics across multiple tasks for a single subject.

**Parameters:**
- `tasks`: character vector of task names (NULL for all tasks)

**Returns:** data.frame with across-task statistics

#### `getGroupMeanPatterns(object, subjects = NULL, task, features = NULL)`
Get mean patterns across multiple subjects for a single task.

**Returns:** list with group_means, group_stds, subject_count, subjects_included

### Data Manipulation Methods

#### `filterSubjects(object, subjects)`
Create subset of LocomotionData with specified subjects.

**Parameters:**
- `subjects`: character vector of subject IDs to keep

**Returns:** LocomotionData object with filtered data

#### `filterTasks(object, tasks)`
Create subset of LocomotionData with specified tasks.

**Parameters:**
- `tasks`: character vector of task names to keep

**Returns:** LocomotionData object with filtered data

#### `mergeWithTaskData(object, task_data, join_keys = NULL, how = "outer")`
Merge locomotion data with task information.

**Parameters:**
- `task_data`: data.frame with task information
- `join_keys`: character vector of keys to join on (defaults to subject and task columns)
- `how`: character type of join ('inner', 'outer', 'left', 'right')

**Returns:** data.table with merged data

#### `clearCache(object)`
Clear cached 3D array results.

**Returns:** LocomotionData object with cleared cache

## Visualization Methods

### Plotting Functions

#### `plotPhasePatterns(object, subject, task, features, plot_type = "both", save_path = NULL)`
Plot phase-normalized patterns with ggplot2.

**Parameters:**
- `plot_type`: character 'mean', 'spaghetti', or 'both'
- `save_path`: character path to save plot (optional)

**Returns:** ggplot object

#### `plotTaskComparison(object, subject, tasks, features, save_path = NULL)`
Plot comparison of mean patterns across tasks.

**Returns:** ggplot object

#### `plotTimeSeries(object, subject, task, features, time_col = "time_s", save_path = NULL)`
Plot time series data for specific features.

**Parameters:**
- `time_col`: character column name for time data

**Returns:** ggplot object

## Data Loading and Validation

### Enhanced Parquet Loading

#### `loadParquetData(file_path, chunk_size = 100000L, memory_limit = 2.0, show_progress = TRUE, validate_structure = TRUE)`
Memory-efficient parquet file loading with streaming support.

**Parameters:**
- `chunk_size`: integer rows per chunk for large files
- `memory_limit`: numeric maximum memory usage in GB
- `show_progress`: logical whether to show progress
- `validate_structure`: logical whether to validate parquet structure

**Returns:** data.table with loaded data

#### `validateParquetStructure(file_path, required_columns = NULL, subject_col = "subject", task_col = "task", phase_col = "phase", parquet_file = NULL)`
Validate parquet file structure and required columns.

**Returns:** list with validation results

#### `detectDataFormat(file_path, sample_size = 5000L, subject_col = "subject", task_col = "task", phase_col = "phase")`
Automatically detect if data is phase-indexed or time-indexed.

**Returns:** list with format detection results

### Data Conversion

#### `convertTimeToPhase(file_path, output_path = NULL, time_col = "time", subject_col = "subject", task_col = "task", gait_events_col = NULL, points_per_cycle = 150L, show_progress = TRUE)`
Convert time-indexed locomotion data to phase-indexed format.

**Returns:** data.table with phase-indexed data

## Utility Functions

### Variable Name Validation

#### `isStandardCompliant(variable_name)`
Check if variable name follows standard convention: `<joint>_<motion>_<measurement>_<side>_<unit>`

**Returns:** logical TRUE if compliant

#### `suggestStandardName(variable_name)`
Suggest standard compliant name for a variable.

**Returns:** character suggested standard name

### Feature Constants

#### `getFeatureConstants()`
Get all feature constants as a named list.

**Returns:** list containing all feature constant vectors

#### `getKinematicFeatureMap()`
Get feature index mapping for kinematic variables.

**Returns:** named integer vector mapping variable names to array indices

#### `getKineticFeatureMap()`
Get feature index mapping for kinetic variables.

**Returns:** named integer vector mapping variable names to array indices

### Biomechanical Utilities

#### `deg2rad(degrees)` / `rad2deg(radians)`
Convert between degrees and radians.

#### `calculatePhase(time, events)`
Calculate gait cycle phase from time data.

#### `interpolateToPhase(phase, data, n_points = 150L)`
Interpolate data to standard phase grid.

#### `detectGaitEvents(time, vgrf, threshold = 50, min_cycle_time = 0.5)`
Simple heel strike detection from vertical ground reaction force.

### Performance and Memory

#### `efficientReshape3D(data, subject, task, features, subject_col = "subject", task_col = "task", points_per_cycle = 150L)`
Standalone function for efficient 3D reshaping.

#### `getMemoryUsage()`
Get current R session memory usage information.

#### `validateDataDimensions(n_points, points_per_cycle = 150L)`
Validate that data dimensions are consistent for 3D reshaping.

## Standard Feature Lists

The library provides standardized feature lists matching the Python API:

- `ANGLE_FEATURES`: Standard joint angle features
- `VELOCITY_FEATURES`: Standard joint velocity features  
- `MOMENT_FEATURES`: Standard joint moment features
- `GRF_FEATURES`: Ground reaction force features
- `COP_FEATURES`: Center of pressure features

## Examples and Demonstrations

### Run Complete Example Suite

#### `run_all_examples(data_path)`
Execute all example workflows demonstrating:
1. Basic gait analysis
2. Data quality assessment
3. Comparative biomechanics study
4. Population-level analysis

## Error Handling

The library provides comprehensive error handling:
- File existence validation
- Required column checking
- Data format validation
- Feature availability verification
- Biomechanical constraint validation

## Performance Considerations

### Memory Management
- Chunked loading for large parquet files
- Memory limit controls
- Automatic garbage collection
- Cache management

### Computational Efficiency
- data.table for fast operations
- Vectorized statistical calculations
- Efficient 3D array operations
- Optional progress reporting

## Integration with Python API

The R library maintains full API compatibility with the Python version:
- Identical method names and signatures
- Consistent return value structures
- Same validation logic
- Equivalent statistical calculations

This ensures seamless transition between R and Python workflows while leveraging each language's strengths.

## Installation and Dependencies

**Required packages:**
- `data.table`: Fast data manipulation
- `ggplot2`: Advanced plotting
- `arrow`: Parquet file support
- `methods`: S4 class system

**Optional packages:**
- `pryr`: Enhanced memory profiling

```r
# Install dependencies
install.packages(c("data.table", "ggplot2", "arrow", "methods"))

# Load the package
library(LocomotionData)
```