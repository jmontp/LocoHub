function data = loadPhaseData(filepath, varargin)
    % Load phase-indexed biomechanical data from parquet file
    %
    % Inputs:
    %   filepath - Path to parquet file
    %   varargin - Optional name-value pairs:
    %     'Columns' - Cell array of column names to load
    %     'Variables' - Cell array of biomechanical variables to load
    %
    % Outputs:
    %   data - Table with loaded data
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'Columns', {}, @iscell);
    addParameter(p, 'Variables', {}, @iscell);
    parse(p, varargin{:});
    
    % Load data
    if ~isempty(p.Results.Columns)
        % Load specific columns
        data = parquetread(filepath, 'SelectedVariableNames', p.Results.Columns);
    elseif ~isempty(p.Results.Variables)
        % Load metadata columns plus specified variables
        metaCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
        allCols = [metaCols, p.Results.Variables];
        data = parquetread(filepath, 'SelectedVariableNames', allCols);
    else
        % Load all data
        data = parquetread(filepath);
    end
end

function [nRows, nCols] = getDataShape(data)
    % Get shape of data table
    %
    % Inputs:
    %   data - Table
    %
    % Outputs:
    %   nRows - Number of rows
    %   nCols - Number of columns
    
    nRows = height(data);
    nCols = width(data);
end

function memoryMB = getMemoryUsage(data)
    % Estimate memory usage of data table
    %
    % Inputs:
    %   data - Table
    %
    % Outputs:
    %   memoryMB - Memory usage in megabytes
    
    % Get variable information
    s = whos('data');
    memoryMB = s.bytes / (1024^2);
end

function subjects = getUniqueSubjects(data)
    % Get list of unique subjects in dataset
    %
    % Inputs:
    %   data - Table with 'subject' column
    %
    % Outputs:
    %   subjects - Cell array of subject IDs
    
    if ismember('subject', data.Properties.VariableNames)
        subjects = unique(data.subject);
    else
        error('Data must have a "subject" column');
    end
end

function tasks = getUniqueTasks(data)
    % Get list of unique tasks in dataset
    %
    % Inputs:
    %   data - Table with 'task' column
    %
    % Outputs:
    %   tasks - Cell array of task names
    
    if ismember('task', data.Properties.VariableNames)
        tasks = unique(data.task);
    else
        error('Data must have a "task" column');
    end
end

function variables = getBiomechanicalVariables(data)
    % Get list of biomechanical variables (excluding metadata)
    %
    % Inputs:
    %   data - Table
    %
    % Outputs:
    %   variables - Cell array of variable names
    
    allVars = data.Properties.VariableNames;
    metaCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
    variables = setdiff(allVars, metaCols, 'stable');
end

function variables = getVariablesByType(data, varType, varargin)
    % Get variables by biomechanical type
    %
    % Inputs:
    %   data - Table
    %   varType - String: 'kinematics', 'kinetics', or 'segment'
    %   varargin - Optional parameters:
    %     'Side' - 'ipsi', 'contra', or 'both' (default: 'both')
    %
    % Outputs:
    %   variables - Cell array of matching variable names
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'Side', 'both', @ischar);
    parse(p, varargin{:});
    
    allVars = getBiomechanicalVariables(data);
    
    % Filter by type
    switch lower(varType)
        case 'kinematics'
            typeVars = allVars(contains(allVars, '_angle_') | ...
                               contains(allVars, '_velocity_'));
        case 'kinetics'
            typeVars = allVars(contains(allVars, '_moment_') | ...
                               contains(allVars, '_power_') | ...
                               contains(allVars, '_force_') | ...
                               contains(allVars, '_grf_'));
        case 'segment'
            typeVars = allVars(contains(allVars, 'segment_angle'));
        otherwise
            error('Unknown variable type: %s', varType);
    end
    
    % Filter by side
    switch lower(p.Results.Side)
        case 'ipsi'
            variables = typeVars(contains(typeVars, '_ipsi_'));
        case 'contra'
            variables = typeVars(contains(typeVars, '_contra_'));
        case 'both'
            variables = typeVars;
        otherwise
            error('Unknown side: %s', p.Results.Side);
    end
end

function displayDataSummary(data)
    % Display summary of loaded data
    %
    % Inputs:
    %   data - Table
    
    fprintf('\nData Summary:\n');
    fprintf('=============\n');
    
    [nRows, nCols] = getDataShape(data);
    fprintf('Shape: %d rows x %d columns\n', nRows, nCols);
    
    memMB = getMemoryUsage(data);
    fprintf('Memory: %.2f MB\n', memMB);
    
    subjects = getUniqueSubjects(data);
    fprintf('Subjects: %d (%s)\n', length(subjects), strjoin(subjects, ', '));
    
    tasks = getUniqueTasks(data);
    fprintf('Tasks: %d\n', length(tasks));
    for i = 1:length(tasks)
        fprintf('  - %s\n', tasks{i});
    end
    
    variables = getBiomechanicalVariables(data);
    fprintf('Biomechanical variables: %d\n', length(variables));
    
    % Show variable categories
    kinVars = getVariablesByType(data, 'kinematics');
    kinetics = getVariablesByType(data, 'kinetics');
    segments = getVariablesByType(data, 'segment');
    
    fprintf('  - Kinematics: %d\n', length(kinVars));
    fprintf('  - Kinetics: %d\n', length(kinetics));
    fprintf('  - Segments: %d\n', length(segments));
end

function checkDataQuality(data)
    % Check for common data quality issues
    %
    % Inputs:
    %   data - Table
    
    fprintf('\nData Quality Check:\n');
    fprintf('==================\n');
    
    % Check for NaN values
    variables = getBiomechanicalVariables(data);
    nanCounts = zeros(length(variables), 1);
    
    for i = 1:length(variables)
        var = variables{i};
        nanCounts(i) = sum(isnan(data.(var)));
    end
    
    totalNaN = sum(nanCounts);
    if totalNaN > 0
        fprintf('⚠ Found %d NaN values across %d variables\n', ...
            totalNaN, sum(nanCounts > 0));
    else
        fprintf('✓ No NaN values found\n');
    end
    
    % Check phase indexing
    phases = unique(data.phase_percent);
    if length(phases) == 150
        fprintf('✓ Correct phase indexing (150 points)\n');
    else
        fprintf('⚠ Unexpected phase points: %d (expected 150)\n', length(phases));
    end
    
    % Check for complete cycles
    subjects = getUniqueSubjects(data);
    tasks = getUniqueTasks(data);
    
    incompleteCycles = 0;
    for s = 1:length(subjects)
        for t = 1:length(tasks)
            subTaskData = data(strcmp(data.subject, subjects{s}) & ...
                              strcmp(data.task, tasks{t}), :);
            
            if height(subTaskData) > 0
                cycles = unique(subTaskData.cycle_id);
                for c = 1:length(cycles)
                    cycleData = subTaskData(subTaskData.cycle_id == cycles(c), :);
                    if height(cycleData) ~= 150
                        incompleteCycles = incompleteCycles + 1;
                    end
                end
            end
        end
    end
    
    if incompleteCycles == 0
        fprintf('✓ All cycles complete (150 points each)\n');
    else
        fprintf('⚠ Found %d incomplete cycles\n', incompleteCycles);
    end
end