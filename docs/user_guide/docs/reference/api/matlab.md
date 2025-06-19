# MATLAB API Reference

The MATLAB library provides efficient tools for loading, processing, and analyzing standardized locomotion datasets. The library implements 3D array operations optimized for phase-indexed biomechanical data.

## Installation

Add the MATLAB library to your path:

```matlab
addpath('path/to/locomotion-data-standardization/source/lib/matlab');
```

## LocomotionData Class

Main class for working with standardized locomotion datasets.

### Constructor

```matlab
loco = LocomotionData(dataPath, varargin)
```

**Parameters:**
- `dataPath` (char) - Path to parquet file
- `'SubjectCol'` (char, optional) - Column name for subjects (default: 'subject')  
- `'TaskCol'` (char, optional) - Column name for tasks (default: 'task')
- `'PhaseCol'` (char, optional) - Column name for phase (default: 'phase')

**Example:**
```matlab
loco = LocomotionData('gtech_2023_phase.parquet');
% Custom column names
loco = LocomotionData('data.parquet', 'SubjectCol', 'participant_id');
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `data` | table | Loaded locomotion data |
| `subjects` | cell array | Unique subject IDs |
| `tasks` | cell array | Unique task names |
| `features` | cell array | Available biomechanical features |
| `POINTS_PER_CYCLE` | double | Constant = 150 |

### Core Methods

#### getCycles
Extract 3D array of cycles for analysis.

```matlab
[data3D, featureNames] = getCycles(subject, task, features)
```

**Parameters:**
- `subject` (char) - Subject ID
- `task` (char) - Task name  
- `features` (cell array, optional) - Feature names to extract

**Returns:**
- `data3D` (double) - 3D array (nCycles, 150, nFeatures)
- `featureNames` (cell array) - Valid feature names

**Example:**
```matlab
% Get all features for a subject-task
[data3D, features] = loco.getCycles('SUB01', 'normal_walk');

% Get specific features
features = {'knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm'};
[data3D, validFeatures] = loco.getCycles('SUB01', 'normal_walk', features);
```

#### getMeanPatterns
Calculate mean patterns across cycles.

```matlab
meanPatterns = getMeanPatterns(subject, task, features)
```

**Returns:**
- `meanPatterns` (struct) - Struct with fields for each feature containing mean pattern (150×1)

**Example:**
```matlab
meanPatterns = loco.getMeanPatterns('SUB01', 'normal_walk');
plot(1:150, meanPatterns.knee_flexion_angle_ipsi_rad);
```

#### getStdPatterns
Calculate standard deviation patterns across cycles.

```matlab
stdPatterns = getStdPatterns(subject, task, features)
```

**Returns:**
- `stdPatterns` (struct) - Struct with fields for each feature containing std pattern (150×1)

#### validateCycles
Validate cycles based on biomechanical constraints.

```matlab
validMask = validateCycles(subject, task, features)
```

**Returns:**
- `validMask` (logical) - Logical array indicating valid cycles

**Validation Rules:**
- **Angles:** Within -π to π radians, no discontinuities > 30°
- **Velocities:** Within ±1000 deg/s (17.45 rad/s)  
- **Moments:** Within ±300 Nm
- **General:** No NaN or Inf values

### Analysis Methods

#### findOutlierCycles
Identify outlier cycles using RMSE from mean pattern.

```matlab
outlierIndices = findOutlierCycles(subject, task, features, threshold)
```

**Parameters:**
- `threshold` (double, optional) - Standard deviations for outlier detection (default: 2.0)

**Returns:**
- `outlierIndices` (double array) - Indices of outlier cycles

#### getPhaseCorrelations
Calculate feature correlations at each phase point.

```matlab
correlations = getPhaseCorrelations(subject, task, features)
```

**Returns:**
- `correlations` (double) - 3D array (150, nFeatures, nFeatures)

#### getSummaryStatistics
Compute comprehensive statistics for all features.

```matlab
summary = getSummaryStatistics(subject, task, features)
```

**Returns:**
- `summary` (table) - Statistics table with columns: Mean, Std, Min, Max, Median, Q25, Q75

#### calculateROM
Calculate Range of Motion for features.

```matlab
romData = calculateROM(subject, task, features, byCycle)
```

**Parameters:**
- `byCycle` (logical, optional) - Calculate ROM per cycle (default: true)

**Returns:**
- `romData` (struct) - ROM values for each feature

### Data Management

#### mergeWithTaskData
Merge locomotion data with task metadata.

```matlab
mergedData = mergeWithTaskData(taskData, varargin)
```

**Parameters:**
- `taskData` (table) - Task information table
- `'JoinKeys'` (cell array, optional) - Keys for joining (default: {'subject', 'task'})
- `'Type'` (char, optional) - Join type: 'inner', 'outer', 'left', 'right' (default: 'outer')

### Visualization Methods

#### plotTimeSeries
Plot time series data for features.

```matlab
plotTimeSeries(subject, task, features, varargin)
```

**Parameters:**
- `'TimeCol'` (char, optional) - Time column name (default: 'time_s')
- `'SavePath'` (char, optional) - Path to save plot

#### plotPhasePatterns
Plot phase-normalized gait patterns.

```matlab
plotPhasePatterns(subject, task, features, varargin)
```

**Parameters:**
- `'PlotType'` (char, optional) - 'mean', 'spaghetti', or 'both' (default: 'both')
- `'SavePath'` (char, optional) - Path to save plot

**Example:**
```matlab
features = {'knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm'};
loco.plotPhasePatterns('SUB01', 'normal_walk', features, 'PlotType', 'both');
```

#### plotTaskComparison
Compare mean patterns across multiple tasks.

```matlab
plotTaskComparison(subject, tasks, features, varargin)
```

**Parameters:**
- `tasks` (cell array) - Task names to compare
- `'SavePath'` (char, optional) - Path to save plot

**Example:**
```matlab
tasks = {'normal_walk', 'fast_walk', 'slow_walk'};
features = {'knee_flexion_angle_ipsi_rad'};
loco.plotTaskComparison('SUB01', tasks, features);
```

## Helper Functions

Standalone functions for data processing without the class interface.

### efficientReshape3D
Core function for reshaping phase data to 3D arrays.

```matlab
[data3D, featureNames] = efficientReshape3D(dataTable, subject, task, features, varargin)
```

**Parameters:**
- `dataTable` (table) - Table with phase-indexed data
- `subject` (char) - Subject ID
- `task` (char) - Task name
- `features` (cell array) - Feature names
- `'SubjectCol'` (char, optional) - Subject column name (default: 'subject')
- `'TaskCol'` (char, optional) - Task column name (default: 'task')  
- `'PointsPerCycle'` (double, optional) - Points per cycle (default: 150)

**Returns:**
- `data3D` (double) - 3D array (nCycles, pointsPerCycle, nFeatures)
- `featureNames` (cell array) - Valid feature names

### calculateMeanPatterns
Calculate mean and standard deviation patterns from 3D data.

```matlab
[meanPatterns, stdPatterns] = calculateMeanPatterns(data3D, featureNames)
```

**Parameters:**
- `data3D` (double) - 3D array (nCycles, 150, nFeatures)
- `featureNames` (cell array) - Feature names

**Returns:**
- `meanPatterns` (struct) - Mean patterns for each feature
- `stdPatterns` (struct) - Standard deviation patterns for each feature

### validateCycles
Validate cycles using biomechanical constraints.

```matlab
validMask = validateCycles(data3D, featureNames)
```

**Parameters:**
- `data3D` (double) - 3D array (nCycles, 150, nFeatures)
- `featureNames` (cell array) - Feature names

**Returns:**
- `validMask` (logical) - Valid cycle indicators

### plotMosaicData
Create mosaic plots of biomechanical data.

```matlab
fig = plotMosaicData(data3D, featureNames, varargin)
```

**Parameters:**
- `'Title'` (char, optional) - Plot title (default: 'Biomechanical Data')
- `'ValidMask'` (logical, optional) - Valid cycle indicators
- `'PlotType'` (char, optional) - 'mean', 'spaghetti', or 'both' (default: 'both')

**Returns:**
- `fig` (figure) - Figure handle

### exportToCSV
Export 3D data to CSV format.

```matlab
exportToCSV(data3D, featureNames, filename, varargin)
```

**Parameters:**
- `filename` (char) - Output CSV filename
- `'Format'` (char, optional) - 'long' or 'wide' (default: 'long')
- `'Subject'` (char, optional) - Subject ID to include
- `'Task'` (char, optional) - Task name to include

## Complete Example

```matlab
% Load data
loco = LocomotionData('gtech_2023_phase.parquet');

% Display dataset info
fprintf('Subjects: %d, Tasks: %d, Features: %d\n', ...
        length(loco.subjects), length(loco.tasks), length(loco.features));

% Get data for specific subject-task
subject = loco.subjects{1};
task = 'normal_walk';
features = {'knee_flexion_angle_ipsi_rad', 'hip_moment_contra_Nm'};

[data3D, validFeatures] = loco.getCycles(subject, task, features);
fprintf('Extracted %d cycles, %d points per cycle, %d features\n', ...
        size(data3D, 1), size(data3D, 2), size(data3D, 3));

% Validate cycles
validMask = loco.validateCycles(subject, task, features);
fprintf('Valid cycles: %d/%d\n', sum(validMask), length(validMask));

% Calculate mean patterns
meanPatterns = loco.getMeanPatterns(subject, task, features);

% Plot results
loco.plotPhasePatterns(subject, task, features, 'PlotType', 'both');

% Compare tasks (if multiple available)
if length(loco.tasks) > 1
    tasks = loco.tasks(1:min(3, length(loco.tasks)));
    loco.plotTaskComparison(subject, tasks, features(1));
end

% Export processed data
validData3D = data3D(validMask, :, :);
exportToCSV(validData3D, validFeatures, 'processed_locomotion_data.csv', ...
           'Subject', subject, 'Task', task);
```

## Data Format Requirements

The MATLAB library expects phase-indexed parquet files with:

- **Structure:** Exactly 150 points per gait cycle
- **Columns:** `subject`, `task`, `phase`, plus biomechanical features
- **Features:** Variables ending in `_rad` (angles), `_rad_per_s` (velocities), `_Nm` (moments)
- **Naming:** Features with `_ipsi_` (ipsilateral) or `_contra_` (contralateral) indicators

## Error Handling

The library includes comprehensive error handling:

- **Invalid data length:** Warning if data not divisible by 150 points
- **Missing features:** Returns empty arrays with warnings
- **No data found:** Graceful handling of missing subject-task combinations
- **Validation failures:** Detailed reporting of constraint violations

## Memory Efficiency

The implementation includes several memory optimizations:

- **Caching:** Results cached for repeated access
- **Vectorized operations:** Efficient 3D array manipulations
- **Selective loading:** Load only required features
- **Batch processing:** Process multiple cycles simultaneously

## Current Implementation Status

**Implemented:**
- LocomotionData class with full API
- All helper functions for standalone use
- Comprehensive validation system
- Multiple visualization options
- Data export capabilities

**Testing Status:**
- Core functionality tested in tutorial examples
- Validation system verified with sample datasets
- Plotting functions operational

**Known Limitations:**
- Requires MATLAB R2019b+ for parquet file support
- Memory usage scales with dataset size
- Limited to phase-indexed data (150 points per cycle)

For Python users, see the [Python API Reference](python.md) for equivalent functionality.