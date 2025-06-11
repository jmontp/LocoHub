# MATLAB Library Tutorial for Locomotion Data Analysis

This tutorial demonstrates how to use the **LocomotionData** class and helper functions for efficient analysis of standardized locomotion data in MATLAB. The library provides both object-oriented and functional approaches for common operations.

## Prerequisites

Ensure you have MATLAB with the following capabilities:
- Statistics and Machine Learning Toolbox (for statistical functions)
- Support for parquet files (`parquetread` function)

## 0. Setup and Path Configuration

```matlab
% Add library path to MATLAB path
addpath('../../../source/lib/matlab');

% Verify the library is available
if exist('LocomotionData', 'class') == 8
    fprintf('LocomotionData library loaded successfully\n');
else
    error('LocomotionData library not found. Check path.');
end
```

## 1. Loading Data

### Using the LocomotionData Class

```matlab
% Load phase-indexed parquet data
dataPath = 'path/to/gtech_2023_phase.parquet';
loco = LocomotionData(dataPath);

% Or specify column names if different
% loco = LocomotionData(dataPath, 'SubjectCol', 'subject_id', 'TaskCol', 'task_name');

% View basic information
fprintf('Loaded %d rows\n', height(loco.data));
fprintf('Subjects: %s\n', strjoin(loco.subjects(1:min(5, length(loco.subjects))), ', '));
fprintf('Tasks: %s\n', strjoin(loco.tasks, ', '));
fprintf('Features: %d biomechanical features\n', length(loco.features));
```

### Using Helper Functions (Alternative Approach)

```matlab
% Load data directly without class
dataTable = parquetread(dataPath);

% Define features of interest
features = {'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'};

% Use standalone functions
[data3D, featureNames] = efficientReshape3D(dataTable, 'AB01', 'normal_walk', features);
fprintf('Extracted data shape: %d cycles x %d points x %d features\n', ...
        size(data3D, 1), size(data3D, 2), size(data3D, 3));
```

## 2. Basic Data Exploration

```matlab
% Display available data
fprintf('\nAvailable subjects:\n');
for i = 1:length(loco.subjects)
    fprintf('  %s\n', loco.subjects{i});
end

fprintf('\nAvailable tasks:\n');
for i = 1:length(loco.tasks)
    fprintf('  %s\n', loco.tasks{i});
end

fprintf('\nBiomechanical features (first 10):\n');
for i = 1:min(10, length(loco.features))
    fprintf('  %s\n', loco.features{i});
end
```

## 3. Efficient 3D Data Access

The core functionality converts phase-indexed data into 3D arrays:

```matlab
% Select subject and task
subject = loco.subjects{1};
task = 'normal_walk';

% Get 3D array for all features
[data3D, featureNames] = loco.getCycles(subject, task);

if ~isempty(data3D)
    fprintf('Data shape: %d cycles x %d points x %d features\n', ...
            size(data3D, 1), size(data3D, 2), size(data3D, 3));
    fprintf('Found %d gait cycles\n', size(data3D, 1));
    fprintf('Features extracted: %d\n', length(featureNames));
else
    fprintf('No data found for %s - %s\n', subject, task);
end

% Extract specific features only
angleFeatures = {'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'};
[angleData, angleNames] = loco.getCycles(subject, task, angleFeatures);
fprintf('Angle data shape: %d x %d x %d\n', size(angleData));
```

## 4. Data Validation

Automatically validate cycles based on biomechanical constraints:

```matlab
% Validate all cycles
validMask = loco.validateCycles(subject, task);
nValid = sum(validMask);
nTotal = length(validMask);

fprintf('Valid cycles: %d/%d (%.1f%%)\n', nValid, nTotal, nValid/nTotal*100);

% Get details on invalid cycles
invalidIndices = find(~validMask);
if ~isempty(invalidIndices)
    fprintf('Invalid cycle indices: %s\n', mat2str(invalidIndices));
end

% Using helper function approach
validMaskHelper = validateCycles(angleData, angleNames);
fprintf('Helper function validation: %d/%d valid\n', ...
        sum(validMaskHelper), length(validMaskHelper));
```

## 5. Statistical Analysis

### Mean and Standard Deviation Patterns

```matlab
% Get mean patterns for each feature
meanPatterns = loco.getMeanPatterns(subject, task, angleFeatures);
stdPatterns = loco.getStdPatterns(subject, task, angleFeatures);

% Display results for knee angle
if isfield(meanPatterns, 'knee_flexion_angle_right_rad')
    kneeMean = meanPatterns.knee_flexion_angle_right_rad;
    fprintf('Knee angle: mean = %.3f rad, peak = %.3f rad\n', ...
            mean(kneeMean), max(kneeMean));
end

% Using helper functions
[meanPatternsHelper, stdPatternsHelper] = calculateMeanPatterns(angleData, angleNames);
fprintf('Mean patterns calculated using helper functions\n');
```

### Range of Motion (ROM) Analysis

```matlab
% Calculate ROM per cycle
romPerCycle = loco.calculateROM(subject, task, angleFeatures, true);

% Calculate overall ROM
romOverall = loco.calculateROM(subject, task, angleFeatures, false);

% Display results
fprintf('\nRange of Motion Analysis:\n');
for i = 1:length(angleFeatures)
    feature = angleFeatures{i};
    fieldName = matlab.lang.makeValidName(feature);
    
    if isfield(romPerCycle, fieldName)
        romCycles = romPerCycle.(fieldName);
        romTotal = romOverall.(fieldName);
        
        fprintf('%s:\n', feature);
        fprintf('  ROM per cycle: %.3f ± %.3f rad\n', mean(romCycles), std(romCycles));
        fprintf('  Overall ROM: %.3f rad\n', romTotal);
    end
end
```

### Summary Statistics

```matlab
% Get comprehensive summary statistics
summary = loco.getSummaryStatistics(subject, task, angleFeatures);
fprintf('\nSummary Statistics:\n');
disp(summary);
```

## 6. Outlier Detection

```matlab
% Find outlier cycles with default threshold (2.0)
outlierIndices = loco.findOutlierCycles(subject, task, angleFeatures);
fprintf('Outlier cycles (>2 std): %s\n', mat2str(outlierIndices));

% Find outliers with stricter threshold
strictOutliers = loco.findOutlierCycles(subject, task, angleFeatures, 1.5);
fprintf('Outlier cycles (>1.5 std): %s\n', mat2str(strictOutliers));
```

## 7. Data Merging

Merge locomotion data with additional task information:

```matlab
% Create example task data
taskData = table();
taskData.subject = {subject; subject};
taskData.task = {'normal_walk'; 'incline_walk'};
taskData.speed_m_s = [1.2; 1.0];
taskData.incline_deg = [0; 5];

% Merge with locomotion data
mergedData = loco.mergeWithTaskData(taskData, 'Type', 'inner');
fprintf('Merged data shape: %d x %d\n', height(mergedData), width(mergedData));

% Show new columns
originalCols = loco.data.Properties.VariableNames;
newCols = setdiff(mergedData.Properties.VariableNames, originalCols);
fprintf('New columns: %s\n', strjoin(newCols, ', '));
```

## 8. Visualization

The MATLAB library provides comprehensive plotting utilities for phase-normalized locomotion data with multiple visualization styles.

### Phase Pattern Plotting

The library offers three main plotting styles for phase-normalized data:

```matlab
% 1. Spaghetti plots - show all individual cycles
loco.plotPhasePatterns(subject, task, angleFeatures, ...
                      'PlotType', 'spaghetti', ...
                      'SavePath', 'spaghetti_plot.png');

% 2. Mean ± standard deviation plots with shaded confidence bands
loco.plotPhasePatterns(subject, task, angleFeatures, ...
                      'PlotType', 'mean', ...
                      'SavePath', 'mean_patterns.png');

% 3. Combined plots - both individual cycles and mean pattern overlay  
loco.plotPhasePatterns(subject, task, angleFeatures, ...
                      'PlotType', 'both', ...
                      'SavePath', 'phase_patterns.png');
```

**Plot Features:**
- **Gray lines**: Valid cycles passing biomechanical validation
- **Red lines**: Invalid cycles failing validation criteria
- **Blue line**: Mean pattern across valid cycles only
- **Blue shaded area**: ±1 standard deviation (in 'mean' mode)
- **Automatic layout**: Intelligent subplot arrangement (up to 3 columns)

### Task Comparison Plots

Compare mean patterns across different tasks for the same subject:

```matlab
% Compare multiple tasks for the same subject
availableTasks = intersect(loco.tasks, {'normal_walk', 'incline_walk', 'decline_walk'});
if length(availableTasks) > 1
    loco.plotTaskComparison(subject, availableTasks, angleFeatures, ...
                           'SavePath', 'task_comparison.png');
end
```

### Time Series Plotting

For time-indexed data analysis:

```matlab
% Plot time series data (if time column exists)
if any(strcmp('time_s', loco.data.Properties.VariableNames))
    loco.plotTimeSeries(subject, task, angleFeatures, ...
                       'TimeCol', 'time_s', ...
                       'SavePath', 'time_series.png');
end
```

### Custom Plotting with Raw Data

Access underlying 3D arrays for advanced custom visualizations:

```matlab
% Get 3D data arrays
[data3D, featureNames] = loco.getCycles(subject, task, angleFeatures);
validMask = loco.validateCycles(subject, task, angleFeatures);

% Create custom percentile plot
figure('Position', [100, 100, 1200, 300]);
phaseX = linspace(0, 100, 150);

for i = 1:length(featureNames)
    subplot(1, length(featureNames), i);
    
    featData = data3D(:, :, i);
    validData = featData(validMask, :);
    
    % Calculate percentiles
    p25 = prctile(validData, 25, 1);
    p50 = prctile(validData, 50, 1);  % Median
    p75 = prctile(validData, 75, 1);
    
    % Plot with custom styling
    fill([phaseX, fliplr(phaseX)], [p25, fliplr(p75)], ...
         [0.7, 0.9, 1.0], 'FaceAlpha', 0.5, 'EdgeColor', 'none');
    hold on;
    plot(phaseX, p50, 'Color', [0, 0.2, 0.6], 'LineWidth', 2);
    
    xlabel('Gait Cycle (%)');
    ylabel(strrep(featureNames{i}, '_', ' '));
    title(featureNames{i}, 'Interpreter', 'none');
    xlim([0, 100]);
    grid on;
    legend({'IQR (25-75%)', 'Median'}, 'Location', 'best');
end

sgtitle(sprintf('%s - %s: Custom Percentile Analysis', subject, task));
print('custom_percentile_plot.png', '-dpng', '-r300');
```

### Alternative Helper Function Plotting

For more control over plotting, use the helper functions directly:

```matlab
% Using helper function for custom plotting
validMask = loco.validateCycles(subject, task, angleFeatures);
[data3D, featureNames] = loco.getCycles(subject, task, angleFeatures);

% Create mosaic plot with custom options
fig = figure('Position', [100, 100, 1000, 600]);
plotMosaicData(data3D, featureNames, ...
              'Title', sprintf('%s - %s', subject, task), ...
              'ValidMask', validMask, ...
              'PlotType', 'both', ...
              'ColorScheme', 'custom', ...
              'ShowLegend', true);

% Save with high resolution
print(fig, 'custom_mosaic_plot.png', '-dpng', '-r300');
```

## 9. Advanced Analysis Example

Complete workflow for analyzing gait variability:

```matlab
function results = analyzeGaitVariability(loco, subject, task, features)
    % Comprehensive gait variability analysis
    
    fprintf('\n=== Gait Variability Analysis: %s - %s ===\n', subject, task);
    
    % 1. Get data and validate
    [data3D, featureNames] = loco.getCycles(subject, task, features);
    if isempty(data3D)
        fprintf('No data found\n');
        results = struct();
        return;
    end
    
    validMask = loco.validateCycles(subject, task, features);
    nValid = sum(validMask);
    nTotal = length(validMask);
    
    fprintf('Valid cycles: %d/%d (%.1f%%)\n', nValid, nTotal, nValid/nTotal*100);
    
    % 2. Calculate metrics for valid cycles only
    validData = data3D(validMask, :, :);
    
    % 3. Initialize results structure
    results = struct();
    
    % 4. Analyze each feature
    for i = 1:length(featureNames)
        feature = featureNames{i};
        featData = validData(:, :, i);
        
        % Mean pattern
        meanPattern = mean(featData, 1);
        
        % Cycle-to-cycle variability (CV)
        cycleMeans = mean(featData, 2);
        cv = std(cycleMeans) / mean(cycleMeans) * 100;
        
        % Step-to-step variability at each phase
        phaseCV = std(featData, 0, 1) ./ mean(featData, 1) * 100;
        meanPhaseCV = mean(phaseCV);
        
        % Range of motion
        romValues = max(featData, [], 2) - min(featData, [], 2);
        romCV = std(romValues) / mean(romValues) * 100;
        
        % Store results
        fieldName = matlab.lang.makeValidName(feature);
        results.(fieldName) = struct(...
            'cycleCV', cv, ...
            'phaseCV', meanPhaseCV, ...
            'romCV', romCV, ...
            'meanROM', mean(romValues));
        
        fprintf('\n%s:\n', feature);
        fprintf('  Cycle-to-cycle CV: %.1f%%\n', cv);
        fprintf('  Phase-to-phase CV: %.1f%%\n', meanPhaseCV);
        fprintf('  ROM CV: %.1f%%\n', romCV);
        fprintf('  Mean ROM: %.3f rad\n', mean(romValues));
    end
    
    % 5. Find most variable feature
    cvs = zeros(1, length(featureNames));
    for i = 1:length(featureNames)
        fieldName = matlab.lang.makeValidName(featureNames{i});
        cvs(i) = results.(fieldName).cycleCV;
    end
    
    [maxCV, maxIdx] = max(cvs);
    mostVariable = featureNames{maxIdx};
    fprintf('\nMost variable feature: %s (CV = %.1f%%)\n', mostVariable, maxCV);
end

% Run the analysis
featuresToAnalyze = {'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'};
variabilityResults = analyzeGaitVariability(loco, subject, task, featuresToAnalyze);
```

## 10. Batch Processing Multiple Subjects

```matlab
function results = batchProcessSubjects(loco, task, features, maxSubjects)
    % Process multiple subjects and compare results
    
    if nargin < 4
        maxSubjects = 5;
    end
    
    subjects = loco.subjects(1:min(maxSubjects, length(loco.subjects)));
    results = struct();
    
    fprintf('\n=== Batch Processing %d subjects for %s ===\n', ...
            length(subjects), task);
    
    for i = 1:length(subjects)
        subject = subjects{i};
        fprintf('\nProcessing %s...\n', subject);
        
        % Get data
        [data3D, ~] = loco.getCycles(subject, task, features);
        if isempty(data3D)
            fprintf('  No data for %s\n', subject);
            continue;
        end
        
        % Validate and get statistics
        validMask = loco.validateCycles(subject, task, features);
        meanPatterns = loco.getMeanPatterns(subject, task, features);
        romData = loco.calculateROM(subject, task, features, false);
        
        % Store results
        results.(matlab.lang.makeValidName(subject)) = struct(...
            'nCycles', size(data3D, 1), ...
            'nValid', sum(validMask), ...
            'meanPatterns', meanPatterns, ...
            'romData', romData);
        
        fprintf('  Cycles: %d (valid: %d)\n', size(data3D, 1), sum(validMask));
    end
    
    % Compare ROM across subjects
    fprintf('\n=== ROM Comparison ===\n');
    subjectFields = fieldnames(results);
    
    for i = 1:length(features)
        feature = features{i};
        fprintf('\n%s:\n', feature);
        
        for j = 1:length(subjectFields)
            subjectField = subjectFields{j};
            romField = matlab.lang.makeValidName(feature);
            
            if isfield(results.(subjectField).romData, romField)
                rom = results.(subjectField).romData.(romField);
                fprintf('  %s: %.3f rad\n', subjectField, rom);
            end
        end
    end
end

% Run batch processing
batchResults = batchProcessSubjects(loco, 'normal_walk', angleFeatures, 3);
```

## 11. Export Results

```matlab
% Export summary statistics to CSV
summaryStats = loco.getSummaryStatistics(subject, task);
writetable(summaryStats, 'summary_statistics.csv', 'WriteRowNames', true);
fprintf('Summary statistics saved to summary_statistics.csv\n');

% Export ROM data
romData = loco.calculateROM(subject, task, angleFeatures, true);
romTable = table();

% Convert ROM struct to table
for i = 1:length(angleFeatures)
    feature = angleFeatures{i};
    fieldName = matlab.lang.makeValidName(feature);
    if isfield(romData, fieldName)
        romTable.(fieldName) = romData.(fieldName);
    end
end

writetable(romTable, 'rom_per_cycle.csv');
fprintf('ROM data saved to rom_per_cycle.csv\n');

% Export using helper function
exportToCSV(angleData, angleNames, 'exported_cycles.csv', ...
           'Format', 'long', 'Subject', subject, 'Task', task);
```

## 12. Working with Multiple Datasets

```matlab
% Compare data from different datasets
datasets = {'gtech_2023_phase.parquet', 'umich_2021_phase.parquet'};
datasetNames = {'GTech2023', 'UMich2021'};

for i = 1:length(datasets)
    if exist(datasets{i}, 'file')
        fprintf('\n=== Loading %s ===\n', datasetNames{i});
        
        % Load dataset
        loco_temp = LocomotionData(datasets{i});
        
        % Find common subjects and tasks
        commonSubjects = intersect(loco.subjects, loco_temp.subjects);
        commonTasks = intersect(loco.tasks, loco_temp.tasks);
        
        fprintf('Common subjects: %d\n', length(commonSubjects));
        fprintf('Common tasks: %d\n', length(commonTasks));
        
        % Compare for first common subject/task
        if ~isempty(commonSubjects) && ~isempty(commonTasks)
            subj = commonSubjects{1};
            tsk = commonTasks{1};
            
            [data1, ~] = loco.getCycles(subj, tsk, angleFeatures);
            [data2, ~] = loco_temp.getCycles(subj, tsk, angleFeatures);
            
            if ~isempty(data1) && ~isempty(data2)
                fprintf('Dataset 1 cycles: %d\n', size(data1, 1));
                fprintf('Dataset 2 cycles: %d\n', size(data2, 1));
            end
        end
    end
end
```

## 13. Performance Comparison

```matlab
% Compare efficiency of different approaches
fprintf('\n=== Performance Comparison ===\n');

% Method 1: Using LocomotionData class
tic;
[data3D_class, ~] = loco.getCycles(subject, task, angleFeatures);
time_class = toc;

% Method 2: Using helper functions
tic;
[data3D_helper, ~] = efficientReshape3D(loco.data, subject, task, angleFeatures);
time_helper = toc;

fprintf('Class method: %.4f seconds\n', time_class);
fprintf('Helper function: %.4f seconds\n', time_helper);
fprintf('Speedup: %.1fx\n', time_class / time_helper);

% Verify results are identical
if isequal(data3D_class, data3D_helper)
    fprintf('✓ Results are identical\n');
else
    fprintf('⚠ Results differ\n');
end
```

## Conclusion

This tutorial covered the main features of the MATLAB LocomotionData library:

- **Efficient data loading** from parquet files
- **Object-oriented and functional interfaces** for different programming styles
- **3D array operations** for fast cycle-based analysis
- **Automatic validation** based on biomechanical constraints
- **Statistical analysis** including mean patterns, ROM, and variability
- **Comprehensive visualization** with customizable plots
- **Data merging** capabilities
- **Batch processing** for multiple subjects
- **Export functionality** for results

### Key Functions Summary

**LocomotionData Class Methods:**
- `getCycles()` - Extract 3D arrays
- `validateCycles()` - Validate biomechanical constraints
- `getMeanPatterns()` / `getStdPatterns()` - Statistical patterns
- `calculateROM()` - Range of motion analysis
- `plotPhasePatterns()` - Visualization
- `mergeWithTaskData()` - Data joining

**Helper Functions:**
- `efficientReshape3D()` - Core 3D reshaping
- `calculateMeanPatterns()` - Statistical calculations
- `validateCycles()` - Standalone validation
- `plotMosaicData()` - Flexible plotting
- `exportToCSV()` - Data export

The library provides efficient, validated methods for analyzing standardized locomotion data while maintaining MATLAB's familiar syntax and functionality.

For more advanced usage, see the source code in `source/lib/matlab/` which includes additional customization options and implementation details.