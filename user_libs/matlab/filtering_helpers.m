function filteredData = filterByTask(data, tasks)
    % Filter data by task(s)
    %
    % Inputs:
    %   data - Table with 'task' column
    %   tasks - String or cell array of task names
    %
    % Outputs:
    %   filteredData - Filtered table
    
    if ischar(tasks)
        tasks = {tasks};
    end
    
    % Create logical index for matching tasks
    matchIdx = false(height(data), 1);
    for i = 1:length(tasks)
        matchIdx = matchIdx | strcmp(data.task, tasks{i});
    end
    
    filteredData = data(matchIdx, :);
end

function filteredData = filterBySubject(data, subjects)
    % Filter data by subject(s)
    %
    % Inputs:
    %   data - Table with 'subject' column
    %   subjects - String or cell array of subject IDs
    %
    % Outputs:
    %   filteredData - Filtered table
    
    if ischar(subjects)
        subjects = {subjects};
    end
    
    % Create logical index for matching subjects
    matchIdx = false(height(data), 1);
    for i = 1:length(subjects)
        matchIdx = matchIdx | strcmp(data.subject, subjects{i});
    end
    
    filteredData = data(matchIdx, :);
end

function filteredData = filterByCycles(data, cycleIds)
    % Filter data by cycle IDs
    %
    % Inputs:
    %   data - Table with 'cycle_id' column
    %   cycleIds - Array of cycle IDs
    %
    % Outputs:
    %   filteredData - Filtered table
    
    filteredData = data(ismember(data.cycle_id, cycleIds), :);
end

function filteredData = filterByPhaseRange(data, minPhase, maxPhase)
    % Filter data by phase range
    %
    % Inputs:
    %   data - Table with 'phase_percent' column
    %   minPhase - Minimum phase (0-149)
    %   maxPhase - Maximum phase (0-149)
    %
    % Outputs:
    %   filteredData - Filtered table
    
    filteredData = data(data.phase_percent >= minPhase & ...
                       data.phase_percent <= maxPhase, :);
end

function filteredData = filterMultipleCriteria(data, varargin)
    % Filter data by multiple criteria
    %
    % Inputs:
    %   data - Table
    %   varargin - Name-value pairs:
    %     'Task' - Task name(s)
    %     'Subject' - Subject ID(s)
    %     'Cycles' - Cycle IDs
    %     'PhaseRange' - [min max] phase values
    %
    % Outputs:
    %   filteredData - Filtered table
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Task', {}, @(x) ischar(x) || iscell(x));
    addParameter(p, 'Subject', {}, @(x) ischar(x) || iscell(x));
    addParameter(p, 'Cycles', [], @isnumeric);
    addParameter(p, 'PhaseRange', [], @(x) isnumeric(x) && length(x) == 2);
    parse(p, varargin{:});
    
    filteredData = data;
    
    % Apply task filter
    if ~isempty(p.Results.Task)
        filteredData = filterByTask(filteredData, p.Results.Task);
    end
    
    % Apply subject filter
    if ~isempty(p.Results.Subject)
        filteredData = filterBySubject(filteredData, p.Results.Subject);
    end
    
    % Apply cycle filter
    if ~isempty(p.Results.Cycles)
        filteredData = filterByCycles(filteredData, p.Results.Cycles);
    end
    
    % Apply phase range filter
    if ~isempty(p.Results.PhaseRange)
        filteredData = filterByPhaseRange(filteredData, ...
            p.Results.PhaseRange(1), p.Results.PhaseRange(2));
    end
end

function filteredData = selectVariables(data, variables)
    % Select specific variables from data
    %
    % Inputs:
    %   data - Table
    %   variables - Cell array of variable names
    %
    % Outputs:
    %   filteredData - Table with selected variables
    
    % Always include metadata columns
    metaCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
    
    % Find which metadata columns exist
    existingMeta = intersect(metaCols, data.Properties.VariableNames);
    
    % Find which requested variables exist
    existingVars = intersect(variables, data.Properties.VariableNames);
    
    % Combine and select
    allCols = [existingMeta, existingVars];
    filteredData = data(:, allCols);
end

function filteredData = selectVariableGroup(data, varType, varargin)
    % Select variables by type
    %
    % Inputs:
    %   data - Table
    %   varType - String: 'kinematics', 'kinetics', or 'segment'
    %   varargin - Optional parameters:
    %     'Side' - 'ipsi', 'contra', or 'both' (default: 'both')
    %
    % Outputs:
    %   filteredData - Table with selected variables
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'Side', 'both', @ischar);
    parse(p, varargin{:});
    
    % Get all variables
    allVars = data.Properties.VariableNames;
    metaCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
    bioVars = setdiff(allVars, metaCols, 'stable');
    
    % Filter by type
    switch lower(varType)
        case 'kinematics'
            typeVars = bioVars(contains(bioVars, '_angle_') | ...
                               contains(bioVars, '_velocity_'));
        case 'kinetics'
            typeVars = bioVars(contains(bioVars, '_moment_') | ...
                               contains(bioVars, '_power_') | ...
                               contains(bioVars, '_force_') | ...
                               contains(bioVars, '_grf_'));
        case 'segment'
            typeVars = bioVars(contains(bioVars, 'segment_angle'));
        otherwise
            error('Unknown variable type: %s', varType);
    end
    
    % Filter by side
    switch lower(p.Results.Side)
        case 'ipsi'
            selectedVars = typeVars(contains(typeVars, '_ipsi_'));
        case 'contra'
            selectedVars = typeVars(contains(typeVars, '_contra_'));
        case 'both'
            selectedVars = typeVars;
        otherwise
            error('Unknown side: %s', p.Results.Side);
    end
    
    % Include metadata and selected variables
    existingMeta = intersect(metaCols, allVars);
    filteredData = data(:, [existingMeta, selectedVars]);
end

function filteredData = getFirstNCycles(data, n, varargin)
    % Get first N cycles for each subject-task combination
    %
    % Inputs:
    %   data - Table with cycle data
    %   n - Number of cycles to keep
    %   varargin - Optional parameters:
    %     'PerTask' - true/false to get N cycles per task (default: true)
    %
    % Outputs:
    %   filteredData - Table with first N cycles
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'PerTask', true, @islogical);
    parse(p, varargin{:});
    
    filteredData = [];
    
    subjects = unique(data.subject);
    tasks = unique(data.task);
    
    for s = 1:length(subjects)
        if p.Results.PerTask
            % Get N cycles per task
            for t = 1:length(tasks)
                subTaskData = data(strcmp(data.subject, subjects{s}) & ...
                                  strcmp(data.task, tasks{t}), :);
                
                if height(subTaskData) > 0
                    cycles = unique(subTaskData.cycle_id);
                    selectedCycles = cycles(1:min(n, length(cycles)));
                    
                    cycleData = subTaskData(ismember(subTaskData.cycle_id, ...
                                                     selectedCycles), :);
                    
                    if isempty(filteredData)
                        filteredData = cycleData;
                    else
                        filteredData = [filteredData; cycleData];
                    end
                end
            end
        else
            % Get N cycles total per subject
            subData = data(strcmp(data.subject, subjects{s}), :);
            
            if height(subData) > 0
                cycles = unique(subData.cycle_id);
                selectedCycles = cycles(1:min(n, length(cycles)));
                
                cycleData = subData(ismember(subData.cycle_id, selectedCycles), :);
                
                if isempty(filteredData)
                    filteredData = cycleData;
                else
                    filteredData = [filteredData; cycleData];
                end
            end
        end
    end
end

function saveFilteredData(data, filepath)
    % Save filtered data to parquet file
    %
    % Inputs:
    %   data - Table to save
    %   filepath - Output file path
    
    parquetwrite(filepath, data);
    fprintf('Saved %d rows to %s\n', height(data), filepath);
end