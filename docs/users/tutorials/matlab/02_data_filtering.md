# Tutorial 2: Data Filtering (MATLAB)

## Overview

After loading data, filtering is the most critical skill. Learn to extract specific subsets of data for focused analysis, reducing computation time and improving clarity.

## Learning Objectives

- Filter data by task, subject, and variables
- Combine multiple filter conditions  
- Create reusable filtered datasets
- Understand filtering performance implications

## Basic Filtering Operations

### Filter by Task

```matlab
% Load the dataset
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');

% Filter for level walking only
levelWalking = loco.filterTask('level_walking');
fprintf('Original data: %d rows\n', loco.length());
fprintf('Level walking only: %d rows\n', levelWalking.length());

% Filter for multiple tasks
walkingTasks = {'level_walking', 'incline_walking', 'decline_walking'};
allWalking = loco.filterTasks(walkingTasks);
fprintf('All walking tasks: %d rows\n', allWalking.length());
```

### Filter by Subject

```matlab
% Single subject
subject01 = loco.filterSubject('SUB01');
fprintf('SUB01 data: %d rows\n', subject01.length());

% Multiple subjects
subjectsOfInterest = {'SUB01', 'SUB02', 'SUB03'};
selectedSubjects = loco.filterSubjects(subjectsOfInterest);
fprintf('Selected subjects: %d rows\n', selectedSubjects.length());

% Exclude specific subjects
excluded = {'SUB10', 'SUB11'};  % e.g., outliers or incomplete data
allSubjects = loco.getSubjects();
keepSubjects = setdiff(allSubjects, excluded);
filteredData = loco.filterSubjects(keepSubjects);
fprintf('After exclusion: %d rows\n', filteredData.length());
```

## Combining Filter Conditions

### Multiple Criteria

```matlab
% Level walking for specific subjects
levelWalkingSubset = loco.filter( ...
    'Task', 'level_walking', ...
    'Subjects', {'SUB01', 'SUB02', 'SUB03'});

% All walking tasks except decline for healthy subjects
healthySubjects = {'SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05'};
walkingHealthy = loco.filter( ...
    'Subjects', healthySubjects, ...
    'ExcludeTasks', {'decline_walking'}, ...
    'TaskContains', 'walking');
```

### Using Table Operations

```matlab
% Direct table filtering
rawData = loco.data;

% Level walking for specific subjects
levelWalkingSubset = rawData( ...
    strcmp(rawData.task, 'level_walking') & ...
    ismember(rawData.subject, {'SUB01', 'SUB02', 'SUB03'}), :);

% All walking tasks except decline for healthy subjects
healthySubjects = {'SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05'};
walkingHealthy = rawData( ...
    ~strcmp(rawData.task, 'decline_walking') & ...
    ismember(rawData.subject, healthySubjects) & ...
    contains(rawData.task, 'walking'), :);
```

## Filtering by Cycle Characteristics

### Select Specific Cycles

```matlab
% First 5 cycles per subject-task combination
first5Cycles = loco.getFirstNCycles(5);

% Or specific cycle numbers
cycles1to3 = loco.filterCycles([1, 2, 3]);

% Using table operations
function firstNCycles = getFirstNCycles(data, n)
    % Get first n cycles for each subject-task combination
    uniqueCombos = unique(data(:, {'subject', 'task'}));
    firstNCycles = table();
    
    for i = 1:height(uniqueCombos)
        subj = uniqueCombos.subject{i};
        task = uniqueCombos.task{i};
        
        subset = data(strcmp(data.subject, subj) & ...
                     strcmp(data.task, task), :);
        uniqueCycles = unique(subset.cycle_id);
        keepCycles = uniqueCycles(1:min(n, length(uniqueCycles)));
        
        cycleData = subset(ismember(subset.cycle_id, keepCycles), :);
        firstNCycles = [firstNCycles; cycleData]; %#ok<AGROW>
    end
end

first5Cycles = getFirstNCycles(loco.data, 5);
```

### Filter by Cycle Quality

```matlab
% Remove cycles with missing data
cleanData = loco.removeIncompleteCycles( ...
    'CheckColumns', {'knee_flexion_angle_ipsi_rad'});

% Get quality metrics
qualityStats = loco.getCycleQualityStats();
fprintf('Cycles with complete knee data: %d\n', qualityStats.completeCycles);

% Manual quality check
function cleanData = removeIncompleteCycles(data, checkColumns)
    % Remove cycles with missing data in specified columns
    completeCycles = table();
    
    groups = findgroups(data.subject, data.task, data.cycle_id);
    uniqueGroups = unique(groups);
    
    for g = uniqueGroups'
        groupData = data(groups == g, :);
        
        hasComplete = true;
        for col = checkColumns
            if any(ismissing(groupData.(col{1})))
                hasComplete = false;
                break;
            end
        end
        
        if hasComplete
            completeCycles = [completeCycles; groupData]; %#ok<AGROW>
        end
    end
    
    cleanData = completeCycles;
end
```

## Filtering Variables

### Select Variable Groups

```matlab
% Keep only essential columns for analysis
analysisData = loco.selectVariableGroup('kinematics', 'Side', 'ipsi');

% Or select multiple groups
analysisData = loco.selectVariables( ...
    'Groups', {'kinematics', 'kinetics'}, ...
    'Side', 'ipsi');

fprintf('Reduced from %d to %d columns\n', ...
    width(loco.data), width(analysisData.data));
```

### Create Variable Subsets

```matlab
% Separate ipsilateral and contralateral
ipsiData = loco.getSideData('ipsi');
contraData = loco.getSideData('contra');

% Lower body only
lowerBodyData = loco.getBodyRegion('lower');
% Or specific joints
lowerBodyData = loco.selectJoints({'hip', 'knee', 'ankle'});

% Manual variable selection
essentialCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
kinematicVars = {};
allVars = loco.data.Properties.VariableNames;

for i = 1:length(allVars)
    if contains(allVars{i}, 'angle') && contains(allVars{i}, 'ipsi')
        kinematicVars{end+1} = allVars{i}; %#ok<AGROW>
    end
end

analysisData = loco.data(:, [essentialCols, kinematicVars]);
```

## Efficient Filtering Patterns

### Create Reusable Filters

```matlab
classdef DataFilter
    % Reusable filtering operations for locomotion data
    
    methods (Static)
        function filtered = getTask(data, taskName)
            % Filter by single task
            filtered = data(strcmp(data.task, taskName), :);
        end
        
        function filtered = getSubjectTask(data, subject, task)
            % Filter by subject and task
            filtered = data( ...
                strcmp(data.subject, subject) & ...
                strcmp(data.task, task), :);
        end
        
        function filtered = getWalkingTasks(data)
            % Get all walking-related tasks
            allTasks = unique(data.task);
            walkingTasks = allTasks(contains(allTasks, 'walking'));
            filtered = data(ismember(data.task, walkingTasks), :);
        end
        
        function filtered = removeIncompleteCycles(data, checkColumns)
            % Remove cycles with missing data in specified columns
            completeMask = true(height(data), 1);
            for col = checkColumns
                completeMask = completeMask & ~ismissing(data.(col{1}));
            end
            filtered = data(completeMask, :);
        end
    end
end

% Usage
filter = DataFilter;
levelWalking = filter.getTask(loco.data, 'level_walking');
sub01Level = filter.getSubjectTask(loco.data, 'SUB01', 'level_walking');
walkingOnly = filter.getWalkingTasks(loco.data);
```

### Chain Filters Efficiently

```matlab
% Chain filter methods using fluent interface
filtered = loco ...
    .filterTask('level_walking') ...
    .filterSubject('SUB01') ...
    .filterCycles(1:10);

% Or use single filter call
filtered = loco.filter( ...
    'Task', 'level_walking', ...
    'Subject', 'SUB01', ...
    'MaxCycle', 9);

% Manual chaining
data = loco.data;

% Inefficient: Multiple copies
filtered1 = data(strcmp(data.task, 'level_walking'), :);
filtered2 = filtered1(strcmp(filtered1.subject, 'SUB01'), :);
filtered3 = filtered2(filtered2.cycle_id < 10, :);

% Efficient: Single operation
filtered = data( ...
    strcmp(data.task, 'level_walking') & ...
    strcmp(data.subject, 'SUB01') & ...
    data.cycle_id < 10, :);
```

## Saving Filtered Datasets

```matlab
% Save filtered subset for reuse
levelWalkingClean = loco.filterTask('level_walking').removeIncompleteCycles();

% Save using library methods
levelWalkingClean.save('processed/level_walking_clean.parquet');

% Or export to different formats
levelWalkingClean.exportCSV('processed/level_walking_clean.csv');

% Manual save
filteredData = loco.data( ...
    strcmp(loco.data.task, 'level_walking') & ...
    ~ismissing(loco.data.knee_flexion_angle_ipsi_rad), :);

% Save as parquet (maintains data types)
parquetwrite('processed/level_walking_clean.parquet', filteredData);

% Save as CSV (human-readable)
writetable(filteredData, 'processed/level_walking_clean.csv');

% Load filtered data later
savedData = LocomotionData('processed/level_walking_clean.parquet');
% Or for manual loading
savedTable = parquetread('processed/level_walking_clean.parquet');
```

## Practice Exercises

### Exercise 1: Complex Filter
Create a filter that selects:
- Only incline and decline walking
- First 3 subjects
- Cycles 5-10
- Only knee and hip variables

```matlab
% Solution
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');

% Filter tasks and subjects
filtered = loco.filter( ...
    'Tasks', {'incline_walking', 'decline_walking'}, ...
    'Subjects', loco.getSubjects()(1:3), ...
    'MinCycle', 5, ...
    'MaxCycle', 10);

% Select variables
varsToKeep = {'subject', 'task', 'cycle_id', 'phase_percent'};
allVars = filtered.getVariables();
for i = 1:length(allVars)
    if contains(allVars{i}, 'knee') || contains(allVars{i}, 'hip')
        varsToKeep{end+1} = allVars{i}; %#ok<AGROW>
    end
end

finalData = filtered.data(:, varsToKeep);
```

### Exercise 2: Filter Function
Write a function that filters data based on a configuration structure:

```matlab
function filtered = filterByConfig(loco, config)
    % Filter data based on configuration structure
    %
    % Inputs:
    %   loco - LocomotionData object
    %   config - Structure with filter settings
    %
    % Output:
    %   filtered - Filtered LocomotionData object
    
    filtered = loco;
    
    % Filter by tasks
    if isfield(config, 'tasks')
        filtered = filtered.filterTasks(config.tasks);
    end
    
    % Filter by subjects
    if isfield(config, 'subjects')
        filtered = filtered.filterSubjects(config.subjects);
    end
    
    % Filter by cycle range
    if isfield(config, 'minCycle') && isfield(config, 'maxCycle')
        cycles = config.minCycle:config.maxCycle;
        filtered = filtered.filterCycles(cycles);
    end
    
    % Filter variables by keywords
    if isfield(config, 'variables')
        varsToKeep = {'subject', 'task', 'cycle_id', 'phase_percent'};
        allVars = filtered.getVariables();
        
        for i = 1:length(allVars)
            for j = 1:length(config.variables)
                if contains(allVars{i}, config.variables{j})
                    varsToKeep{end+1} = allVars{i}; %#ok<AGROW>
                    break;
                end
            end
        end
        
        filtered.data = filtered.data(:, unique(varsToKeep, 'stable'));
    end
end

% Usage
config.tasks = {'level_walking', 'incline_walking'};
config.subjects = {'SUB01', 'SUB02'};
config.minCycle = 5;
config.maxCycle = 15;
config.variables = {'knee', 'hip'};

filtered = filterByConfig(loco, config);
```

### Exercise 3: Quality Control
Create a function that returns only "good" cycles:

```matlab
function goodCycles = getGoodCycles(loco)
    % Return only high-quality cycles
    %
    % Criteria:
    % - Complete data (no NaN values)
    % - Within 2 standard deviations of mean cycle duration
    % - Has all 150 phase points
    
    data = loco.data;
    goodCycles = table();
    
    % Group by subject, task, cycle
    [groups, subjects, tasks, cycles] = findgroups( ...
        data.subject, data.task, data.cycle_id);
    
    for g = 1:max(groups)
        cycleData = data(groups == g, :);
        
        % Check 1: Has all 150 phase points
        if height(cycleData) ~= 150
            continue;
        end
        
        % Check 2: No missing data
        biomechVars = setdiff(cycleData.Properties.VariableNames, ...
            {'subject', 'task', 'cycle_id', 'phase_percent', 'phase_ipsi', 'phase_contra'});
        
        hasMissing = false;
        for var = biomechVars
            if any(ismissing(cycleData.(var{1})))
                hasMissing = true;
                break;
            end
        end
        
        if hasMissing
            continue;
        end
        
        % Check 3: Within 2 SD of mean (would need cycle duration info)
        % For phase data, all cycles are normalized to 150 points
        % So this check is implicit
        
        goodCycles = [goodCycles; cycleData]; %#ok<AGROW>
    end
    
    fprintf('Kept %d of %d cycles (%.1f%%)\n', ...
        height(goodCycles)/150, ...
        height(data)/150, ...
        100 * height(goodCycles) / height(data));
end

% Usage
goodData = getGoodCycles(loco);
```

## Key Takeaways

1. **Filter early and often** - Work with focused subsets
2. **Use logical operators** - & (and), | (or), ~ (not) for complex conditions
3. **Save filtered datasets** - Avoid repeating complex filters
4. **Think about memory** - Filter before heavy computations
5. **Create reusable filters** - Build a library of common operations
6. **MATLAB-specific features**:
   - Use `strcmp` for string comparison
   - Use `ismember` for multiple value matching
   - Use `contains` for partial string matching
   - Leverage table operations for efficient filtering

## Next Steps

[Continue to Tutorial 3: Basic Visualization →](03_visualization.md)

Learn to create phase averages, spaghetti plots, and publication-ready figures with your filtered data.