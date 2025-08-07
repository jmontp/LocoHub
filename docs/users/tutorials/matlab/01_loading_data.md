# Tutorial 1: Loading Data Efficiently (MATLAB)

## Overview

Learn how to load biomechanical datasets efficiently in MATLAB, understanding memory implications and column selection strategies.

## Learning Objectives

- Load phase-indexed and time-indexed datasets
- Select specific columns to reduce memory usage
- Understand the data structure and available variables
- List subjects, tasks, and measurement variables

## Full Dataset Loading

### Basic Loading

```matlab
% Add library to path
addpath('user_libs/matlab');

% Load a complete phase-indexed dataset
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');

% Check dataset size
[rows, cols] = loco.getShape();
fprintf('Dataset shape: %d rows x %d columns\n', rows, cols);
fprintf('Memory usage: %.2f MB\n', loco.getMemoryUsage() / 1024^2);
```

### Understanding the Structure

```matlab
% View column names
fprintf('Available columns:\n');
variables = loco.getVariables();
disp(variables);

% Check data types
fprintf('\nData types:\n');
dataTypes = loco.getDataTypes();
disp(dataTypes);

% Preview first few rows
fprintf('\nFirst 5 rows:\n');
headData = loco.head(5);
disp(headData);
```

## Memory-Efficient Loading

### Column Selection

```matlab
% Load only specific biomechanical variables
selectedColumns = {
    'subject', 
    'task', 
    'cycle_id',
    'phase_percent',
    'knee_flexion_angle_ipsi_rad',
    'hip_flexion_angle_ipsi_rad'
};

% Load with column selection
locoEfficient = LocomotionData( ...
    'converted_datasets/umich_2021_phase.parquet', ...
    'Columns', selectedColumns);

% Compare memory usage
fprintf('Full dataset: %.2f MB\n', loco.getMemoryUsage() / 1024^2);
fprintf('Selected columns: %.2f MB\n', locoEfficient.getMemoryUsage() / 1024^2);
```

### Loading Variable Groups

```matlab
% Load only kinematic variables
locoKinematics = LocomotionData( ...
    'converted_datasets/umich_2021_phase.parquet', ...
    'VariableGroup', 'kinematics');

% Load only kinetic variables
locoKinetics = LocomotionData( ...
    'converted_datasets/umich_2021_phase.parquet', ...
    'VariableGroup', 'kinetics');

% Load multiple joints
locoLower = LocomotionData( ...
    'converted_datasets/umich_2021_phase.parquet', ...
    'Joints', {'hip', 'knee', 'ankle'});
```

## Exploring Available Data

### List Subjects and Tasks

```matlab
% Get unique subjects
subjects = loco.getSubjects();
fprintf('Number of subjects: %d\n', length(subjects));
fprintf('Subject IDs: ');
disp(subjects(1:min(5, length(subjects))));  % Show first 5

% Get unique tasks
tasks = loco.getTasks();
fprintf('Available tasks: ');
disp(tasks);

% Count cycles per task
for i = 1:length(tasks)
    nCycles = loco.countCycles('Task', tasks{i});
    fprintf('%s: %d cycles\n', tasks{i}, nCycles);
end
```

### Understanding Variable Naming

```matlab
% Identify variable types
variableInfo = loco.getVariableInfo();

fprintf('Joint angles: %d variables\n', variableInfo.kinematics.count);
fprintf('Joint moments: %d variables\n', variableInfo.kinetics.moments.count);
fprintf('Ground reaction forces: %d variables\n', variableInfo.kinetics.forces.count);

% Get detailed variable descriptions
loco.describeVariables();

% Understanding naming convention
fprintf('\nNaming convention examples:\n');
variables = loco.getVariables();
for i = 1:min(3, length(variables))
    description = loco.getVariableDescription(variables{i});
    fprintf('- %s: %s\n', variables{i}, description);
end
```

## Time-Indexed vs Phase-Indexed Data

### Loading Different Data Types

```matlab
% Phase-indexed: 150 points per gait cycle
locoPhase = LocomotionData('converted_datasets/umich_2021_phase.parquet');
fprintf('Phase data points per cycle: %d\n', locoPhase.pointsPerCycle);
fprintf('Data type: %s\n', locoPhase.dataType);  % 'phase' or 'time'

% Time-indexed: original sampling frequency
locoTime = LocomotionData('converted_datasets/umich_2021_time.parquet');
fprintf('Sampling frequency: %d Hz\n', locoTime.samplingFrequency);
fprintf('Time column available: %d\n', locoTime.hasTimeColumn);
```

## Accessing Raw Data

### Direct Table Access

```matlab
% Access the underlying table data
rawData = loco.data;

% MATLAB table operations
subjects = unique(rawData.subject);
tasks = unique(rawData.task);

% Filter using table operations
levelWalking = rawData(strcmp(rawData.task, 'level_walking'), :);
fprintf('Level walking data: %d rows\n', height(levelWalking));

% Get specific columns
kneeData = rawData.knee_flexion_angle_ipsi_rad;
fprintf('Knee flexion data points: %d\n', length(kneeData));
```

## Practice Exercises

### Exercise 1: Memory Optimization
Load the Georgia Tech 2023 dataset with only the variables needed to analyze knee and ankle kinematics during stair climbing.

```matlab
% Solution outline
gtechData = LocomotionData( ...
    'converted_datasets/gtech_2023_phase.parquet', ...
    'Columns', { ...
        'subject', 'task', 'cycle_id', 'phase_percent', ...
        'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', ...
        'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'});

% Filter for stair tasks
stairData = gtechData.filterTask({'stair_ascent', 'stair_descent'});
```

### Exercise 2: Data Exploration
Write a function that prints a summary of a dataset including:
- Number of subjects
- Available tasks  
- Number of cycles per task
- List of bilateral variables (both ipsi and contra versions)

```matlab
function summarizeDataset(loco)
    % Print dataset summary
    fprintf('=== Dataset Summary ===\n');
    
    % Number of subjects
    subjects = loco.getSubjects();
    fprintf('Number of subjects: %d\n', length(subjects));
    
    % Available tasks
    tasks = loco.getTasks();
    fprintf('Available tasks: ');
    disp(tasks);
    
    % Cycles per task
    fprintf('\nCycles per task:\n');
    for i = 1:length(tasks)
        nCycles = loco.countCycles('Task', tasks{i});
        fprintf('  %s: %d cycles\n', tasks{i}, nCycles);
    end
    
    % Bilateral variables
    variables = loco.getVariables();
    bilateralVars = {};
    for i = 1:length(variables)
        if contains(variables{i}, '_ipsi_')
            contraVar = strrep(variables{i}, '_ipsi_', '_contra_');
            if any(strcmp(variables, contraVar))
                bilateralVars{end+1} = strrep(variables{i}, '_ipsi_', '_'); %#ok<AGROW>
            end
        end
    end
    
    fprintf('\nBilateral variables (%d pairs):\n', length(bilateralVars));
    for i = 1:min(5, length(bilateralVars))
        fprintf('  %s\n', bilateralVars{i});
    end
end
```

### Exercise 3: Smart Loading
Create a function that automatically selects columns based on keywords:

```matlab
function loco = loadByKeywords(filepath, keywords, includeMetadata)
    % Load dataset with variables matching keywords
    %
    % Inputs:
    %   filepath - Path to parquet file
    %   keywords - Cell array of keywords (default: {'knee', 'hip'})
    %   includeMetadata - Include subject/task/cycle columns (default: true)
    %
    % Output:
    %   loco - LocomotionData object with selected columns
    
    % Default arguments
    if nargin < 2
        keywords = {'knee', 'hip'};
    end
    if nargin < 3
        includeMetadata = true;
    end
    
    % First load to get column names
    temp = LocomotionData(filepath);
    allColumns = temp.getVariables();
    
    % Select matching columns
    selectedColumns = {};
    
    % Add metadata columns if requested
    if includeMetadata
        metaCols = {'subject', 'task', 'cycle_id', 'phase_percent', ...
                   'phase_ipsi', 'phase_contra'};
        for i = 1:length(metaCols)
            if any(strcmp(allColumns, metaCols{i}))
                selectedColumns{end+1} = metaCols{i}; %#ok<AGROW>
            end
        end
    end
    
    % Add columns matching keywords
    for i = 1:length(allColumns)
        for j = 1:length(keywords)
            if contains(allColumns{i}, keywords{j})
                selectedColumns{end+1} = allColumns{i}; %#ok<AGROW>
                break;
            end
        end
    end
    
    % Remove duplicates
    selectedColumns = unique(selectedColumns, 'stable');
    
    % Load with selected columns
    loco = LocomotionData(filepath, 'Columns', selectedColumns);
    
    fprintf('Loaded %d columns matching keywords\n', length(selectedColumns));
end
```

## Key Takeaways

1. **Always consider memory** when loading large datasets
2. **Use column selection** to load only what you need
3. **Understand the structure** before analysis:
   - Phase-indexed: 150 points per cycle
   - Time-indexed: original sampling rate
4. **Variable naming convention**:
   - Joint_motion_side_unit
   - ipsi = ipsilateral, contra = contralateral
   - rad = radians, Nm = Newton-meters, N = Newtons
5. **MATLAB-specific features**:
   - Direct table access via `loco.data`
   - Name-value pair arguments for options
   - Cell arrays for multiple selections

## Next Steps

[Continue to Tutorial 2: Data Filtering →](02_data_filtering.md)

Learn how to filter your loaded data by task, subject, and other criteria for focused analysis.