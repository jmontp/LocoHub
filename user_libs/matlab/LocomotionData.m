classdef LocomotionData < handle
    % LOCOMOTIONDATA - Class for loading and processing standardized locomotion data
    %
    % This class implements efficient 3D array operations for phase-indexed
    % biomechanical data following the locomotion data standard.
    %
    % Example Usage:
    % --------------
    %   % Load data
    %   loco = LocomotionData('path/to/data.parquet');
    %   
    %   % Get data for specific subject/task
    %   [data3D, features] = loco.getCycles('SUB01', 'normal_walk');
    %   
    %   % Calculate mean patterns
    %   meanPatterns = loco.getMeanPatterns('SUB01', 'normal_walk');
    %   
    %   % Validate cycles
    %   validMask = loco.validateCycles('SUB01', 'normal_walk');
    %
    % Properties:
    %   data        - Table containing the locomotion data
    %   subjects    - List of unique subjects
    %   tasks       - List of unique tasks
    %   features    - List of biomechanical features
    %
    % Methods:
    %   getCycles           - Get 3D array of cycles
    %   getMeanPatterns     - Get mean patterns for features
    %   getStdPatterns      - Get standard deviation patterns
    %   validateCycles      - Validate cycles based on constraints
    %   findOutlierCycles   - Find outlier cycles
    %   getPhaseCorrelations - Calculate feature correlations at each phase
    %   getSummaryStatistics - Get summary statistics
    
    properties (Constant)
        POINTS_PER_CYCLE = 150;
    end
    
    properties
        data            % Table with locomotion data
        dataPath        % Path to data file
        subjectCol      % Column name for subjects
        taskCol         % Column name for tasks
        phaseCol        % Column name for phase
        subjects        % Unique subjects
        tasks           % Unique tasks
        features        % Available biomechanical features
        pointsPerCycle  % Points per cycle (150 for phase data)
        dataType        % 'phase' or 'time' indexed data
        samplingFrequency % Sampling frequency for time data
        hasTimeColumn   % Whether time column exists
    end
    
    properties (Access = private)
        cache           % Cache for 3D arrays
    end
    
    methods
        function obj = LocomotionData(dataPath, varargin)
            % Constructor - Load locomotion data from parquet file
            %
            % Inputs:
            %   dataPath - Path to parquet file (optional if empty constructor)
            %   Optional name-value pairs:
            %     'SubjectCol' - Column name for subjects (default: 'subject')
            %     'TaskCol' - Column name for tasks (default: 'task')
            %     'PhaseCol' - Column name for phase (default: 'phase')
            %     'Columns' - Cell array of column names to load
            %     'VariableGroup' - Load specific variable group ('kinematics', 'kinetics')
            %     'Joints' - Cell array of joints to load
            
            % Handle empty constructor for filter methods
            if nargin == 0
                obj.data = table();
                obj.cache = containers.Map();
                obj.subjects = {};
                obj.tasks = {};
                obj.features = {};
                obj.subjectCol = 'subject';
                obj.taskCol = 'task';
                obj.phaseCol = 'phase_percent';
                obj.dataType = 'phase';
                obj.pointsPerCycle = 150;
                obj.samplingFrequency = [];
                obj.hasTimeColumn = false;
                return;
            end
            
            % Parse inputs
            p = inputParser;
            addRequired(p, 'dataPath', @(x) ischar(x) || isstring(x));
            addParameter(p, 'SubjectCol', 'subject', @ischar);
            addParameter(p, 'TaskCol', 'task', @ischar);
            addParameter(p, 'PhaseCol', 'phase', @ischar);
            addParameter(p, 'Columns', {}, @iscell);
            addParameter(p, 'VariableGroup', '', @ischar);
            addParameter(p, 'Joints', {}, @iscell);
            parse(p, dataPath, varargin{:});
            
            obj.dataPath = p.Results.dataPath;
            obj.subjectCol = p.Results.SubjectCol;
            obj.taskCol = p.Results.TaskCol;
            obj.phaseCol = p.Results.PhaseCol;
            
            % Load data
            fprintf('Loading data from %s...\n', obj.dataPath);
            
            if ~isempty(p.Results.Columns)
                % Load specific columns
                obj.data = parquetread(obj.dataPath);
                allCols = obj.data.Properties.VariableNames;
                
                % Ensure columns is a cell array
                if ~iscell(p.Results.Columns)
                    requestedCols = {p.Results.Columns};
                else
                    requestedCols = p.Results.Columns;
                end
                
                % Find valid columns
                keepCols = {};
                for i = 1:length(requestedCols)
                    if any(strcmp(allCols, requestedCols{i}))
                        keepCols{end+1} = requestedCols{i};
                    end
                end
                
                % Always include phase columns if they exist
                if any(strcmp(allCols, 'phase_ipsi')) && ~any(strcmp(keepCols, 'phase_ipsi'))
                    keepCols{end+1} = 'phase_ipsi';
                end
                if any(strcmp(allCols, 'phase_contra')) && ~any(strcmp(keepCols, 'phase_contra'))
                    keepCols{end+1} = 'phase_contra';
                end
                
                % Ensure we have columns to keep
                if isempty(keepCols)
                    error('No valid columns found to load');
                end
                
                obj.data = obj.data(:, keepCols);
                
            elseif ~isempty(p.Results.VariableGroup)
                % Load by variable group
                obj.data = parquetread(obj.dataPath);
                allCols = obj.data.Properties.VariableNames;
                keepCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
                
                if strcmp(p.Results.VariableGroup, 'kinematics')
                    for i = 1:length(allCols)
                        if contains(allCols{i}, 'angle')
                            keepCols{end+1} = allCols{i};
                        end
                    end
                elseif strcmp(p.Results.VariableGroup, 'kinetics')
                    for i = 1:length(allCols)
                        if contains(allCols{i}, 'moment') || contains(allCols{i}, 'force')
                            keepCols{end+1} = allCols{i};
                        end
                    end
                end
                
                % Always include phase columns if they exist
                if any(strcmp(allCols, 'phase_ipsi'))
                    keepCols{end+1} = 'phase_ipsi';
                end
                if any(strcmp(allCols, 'phase_contra'))
                    keepCols{end+1} = 'phase_contra';
                end
                
                obj.data = obj.data(:, unique(keepCols, 'stable'));
                
            elseif ~isempty(p.Results.Joints)
                % Load by joints
                obj.data = parquetread(obj.dataPath);
                allCols = obj.data.Properties.VariableNames;
                keepCols = {'subject', 'task', 'cycle_id', 'phase_percent'};
                
                for i = 1:length(allCols)
                    for j = 1:length(p.Results.Joints)
                        if contains(allCols{i}, p.Results.Joints{j})
                            keepCols{end+1} = allCols{i};
                            break;
                        end
                    end
                end
                
                % Always include phase columns if they exist
                if any(strcmp(allCols, 'phase_ipsi'))
                    keepCols{end+1} = 'phase_ipsi';
                end
                if any(strcmp(allCols, 'phase_contra'))
                    keepCols{end+1} = 'phase_contra';
                end
                
                obj.data = obj.data(:, unique(keepCols, 'stable'));
                
            else
                % Load all data
                obj.data = parquetread(obj.dataPath);
            end
            
            % Initialize cache
            obj.cache = containers.Map();
            
            % Identify subjects, tasks, and features
            obj.identifyMetadata();
            
            fprintf('Loaded data with %d rows, %d subjects, %d tasks, %d features\n', ...
                height(obj.data), length(obj.subjects), length(obj.tasks), ...
                length(obj.features));
        end
        
        function [data3D, featureNames] = getCycles(obj, subject, task, features)
            % Get 3D array of cycles for a subject-task combination
            %
            % Inputs:
            %   subject - Subject ID
            %   task - Task name
            %   features - Cell array of feature names (optional)
            %
            % Outputs:
            %   data3D - 3D array of shape (nCycles, 150, nFeatures)
            %   featureNames - Cell array of feature names
            
            if nargin < 4
                features = obj.features;
            end
            
            % Check cache
            cacheKey = sprintf('%s_%s_%s', subject, task, strjoin(features, ','));
            if isKey(obj.cache, cacheKey)
                cached = obj.cache(cacheKey);
                data3D = cached.data3D;
                featureNames = cached.featureNames;
                return;
            end
            
            % Filter data
            mask = strcmp(obj.data.(obj.subjectCol), subject) & ...
                   strcmp(obj.data.(obj.taskCol), task);
            subset = obj.data(mask, :);
            
            if height(subset) == 0
                warning('No data found for subject ''%s'', task ''%s''', subject, task);
                data3D = [];
                featureNames = {};
                return;
            end
            
            % Check data length
            nPoints = height(subset);
            if mod(nPoints, obj.POINTS_PER_CYCLE) ~= 0
                warning('Data length %d not divisible by %d', nPoints, obj.POINTS_PER_CYCLE);
                data3D = [];
                featureNames = {};
                return;
            end
            
            nCycles = nPoints / obj.POINTS_PER_CYCLE;
            
            % Select valid features
            validFeatures = features(ismember(features, subset.Properties.VariableNames));
            if isempty(validFeatures)
                warning('No valid features found');
                data3D = [];
                featureNames = {};
                return;
            end
            
            % Extract and reshape to 3D
            featureData = table2array(subset(:, validFeatures));
            data3D = reshape(featureData, obj.POINTS_PER_CYCLE, nCycles, length(validFeatures));
            data3D = permute(data3D, [2, 1, 3]); % Reorder to (nCycles, 150, nFeatures)
            
            featureNames = validFeatures;
            
            % Cache result
            cached.data3D = data3D;
            cached.featureNames = featureNames;
            obj.cache(cacheKey) = cached;
        end
        
        function meanPatterns = getMeanPatterns(obj, subject, task, features)
            % Get mean patterns for each feature
            %
            % Returns:
            %   meanPatterns - Struct with fields for each feature
            
            if nargin < 4
                features = obj.features;
            end
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                meanPatterns = struct();
                return;
            end
            
            % Calculate means
            meanData = mean(data3D, 1); % Average across cycles
            meanData = squeeze(meanData); % Remove singleton dimension
            
            % Create struct
            meanPatterns = struct();
            for i = 1:length(featureNames)
                fieldName = matlab.lang.makeValidName(featureNames{i});
                meanPatterns.(fieldName) = meanData(:, i);
            end
        end
        
        function stdPatterns = getStdPatterns(obj, subject, task, features)
            % Get standard deviation patterns for each feature
            %
            % Returns:
            %   stdPatterns - Struct with fields for each feature
            
            if nargin < 4
                features = obj.features;
            end
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                stdPatterns = struct();
                return;
            end
            
            % Calculate stds
            stdData = std(data3D, 0, 1); % Std across cycles
            stdData = squeeze(stdData); % Remove singleton dimension
            
            % Create struct
            stdPatterns = struct();
            for i = 1:length(featureNames)
                fieldName = matlab.lang.makeValidName(featureNames{i});
                stdPatterns.(fieldName) = stdData(:, i);
            end
        end
        
        function validMask = validateCycles(obj, subject, task, features)
            % Validate cycles based on biomechanical constraints
            %
            % Returns:
            %   validMask - Logical array indicating valid cycles
            
            if nargin < 4
                features = obj.features;
            end
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                validMask = logical([]);
                return;
            end
            
            nCycles = size(data3D, 1);
            validMask = true(nCycles, 1);
            
            % Check each feature
            for i = 1:length(featureNames)
                feature = featureNames{i};
                featData = data3D(:, :, i);
                
                % Range checks based on feature type
                if contains(feature, 'angle')
                    % Angles should be between -pi and pi radians
                    outOfRange = any(featData < -pi | featData > pi, 2);
                    validMask = validMask & ~outOfRange;
                    
                    % Check for large discontinuities
                    diffs = abs(diff(featData, 1, 2));
                    largeJumps = any(diffs > 0.5236, 2); % 30 degrees = 0.5236 radians
                    validMask = validMask & ~largeJumps;
                    
                elseif contains(feature, 'velocity')
                    % Velocities reasonable range in rad/s
                    outOfRange = any(abs(featData) > 17.45, 2); % 1000 deg/s = 17.45 rad/s
                    validMask = validMask & ~outOfRange;
                    
                elseif contains(feature, 'moment')
                    % Moments reasonable range
                    outOfRange = any(abs(featData) > 300, 2);
                    validMask = validMask & ~outOfRange;
                end
                
                % Check for NaN or Inf
                hasInvalid = any(~isfinite(featData), 2);
                validMask = validMask & ~hasInvalid;
            end
        end
        
        function outlierIndices = findOutlierCycles(obj, subject, task, features, threshold)
            % Find outlier cycles based on deviation from mean pattern
            %
            % Inputs:
            %   threshold - Number of standard deviations (default: 2)
            %
            % Returns:
            %   outlierIndices - Indices of outlier cycles
            
            if nargin < 4
                features = obj.features;
            end
            if nargin < 5
                threshold = 2.0;
            end
            
            [data3D, ~] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                outlierIndices = [];
                return;
            end
            
            % Calculate mean pattern
            meanPattern = mean(data3D, 1);
            
            % Calculate deviation for each cycle
            deviations = data3D - repmat(meanPattern, size(data3D, 1), 1, 1);
            rmsePerCycle = sqrt(mean(mean(deviations.^2, 2), 3));
            
            % Find outliers
            outlierThreshold = mean(rmsePerCycle) + threshold * std(rmsePerCycle);
            outlierIndices = find(rmsePerCycle > outlierThreshold);
        end
        
        function correlations = getPhaseCorrelations(obj, subject, task, features)
            % Calculate correlation between features at each phase point
            %
            % Returns:
            %   correlations - 3D array (150, nFeatures, nFeatures)
            
            if nargin < 4
                features = obj.features;
            end
            
            [data3D, ~] = obj.getCycles(subject, task, features);
            
            if isempty(data3D) || size(data3D, 1) < 2
                correlations = [];
                return;
            end
            
            nPhases = obj.POINTS_PER_CYCLE;
            nFeatures = size(data3D, 3);
            correlations = zeros(nPhases, nFeatures, nFeatures);
            
            for phase = 1:nPhases
                phaseData = squeeze(data3D(:, phase, :)); % (nCycles, nFeatures)
                correlations(phase, :, :) = corrcoef(phaseData);
            end
        end
        
        function summary = getSummaryStatistics(obj, subject, task, features)
            % Get summary statistics for all features
            %
            % Returns:
            %   summary - Table with statistics
            
            if nargin < 4
                features = obj.features;
            end
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                summary = table();
                return;
            end
            
            % Reshape to 2D for easier statistics
            data2D = reshape(data3D, [], size(data3D, 3));
            
            % Calculate statistics
            meanVals = mean(data2D, 1)';
            stdVals = std(data2D, 0, 1)';
            minVals = min(data2D, [], 1)';
            maxVals = max(data2D, [], 1)';
            medianVals = median(data2D, 1)';
            q25Vals = prctile(data2D, 25, 1)';
            q75Vals = prctile(data2D, 75, 1)';
            
            % Create table
            summary = table(meanVals, stdVals, minVals, maxVals, ...
                           medianVals, q25Vals, q75Vals, ...
                           'RowNames', featureNames, ...
                           'VariableNames', {'Mean', 'Std', 'Min', 'Max', ...
                                           'Median', 'Q25', 'Q75'});
        end
        
        function mergedData = mergeWithTaskData(obj, taskData, varargin)
            % Merge locomotion data with task information
            %
            % Inputs:
            %   taskData - Table with task information
            %   Optional name-value pairs:
            %     'JoinKeys' - Cell array of keys to join on
            %     'Type' - 'inner', 'outer', 'left', 'right'
            %
            % Returns:
            %   mergedData - Merged table
            
            p = inputParser;
            addParameter(p, 'JoinKeys', {obj.subjectCol, obj.taskCol}, @iscell);
            addParameter(p, 'Type', 'outer', @ischar);
            parse(p, varargin{:});
            
            joinKeys = p.Results.JoinKeys;
            joinType = p.Results.Type;
            
            % Check if join keys exist
            for i = 1:length(joinKeys)
                if ~any(strcmp(joinKeys{i}, obj.data.Properties.VariableNames))
                    error('Join key %s not found in locomotion data', joinKeys{i});
                end
                if ~any(strcmp(joinKeys{i}, taskData.Properties.VariableNames))
                    error('Join key %s not found in task data', joinKeys{i});
                end
            end
            
            % Perform join based on type
            switch lower(joinType)
                case 'inner'
                    mergedData = innerjoin(obj.data, taskData, 'Keys', joinKeys);
                case 'outer'
                    mergedData = outerjoin(obj.data, taskData, 'Keys', joinKeys);
                case 'left'
                    mergedData = leftjoin(obj.data, taskData, 'Keys', joinKeys);
                case 'right'
                    mergedData = leftjoin(taskData, obj.data, 'Keys', joinKeys);
                otherwise
                    error('Invalid join type: %s', joinType);
            end
        end
        
        function romData = calculateROM(obj, subject, task, features, byCycle)
            % Calculate Range of Motion (ROM) for features
            %
            % Inputs:
            %   subject - Subject ID
            %   task - Task name
            %   features - Cell array of feature names (optional)
            %   byCycle - Logical, if true calculate ROM per cycle (default: true)
            %
            % Returns:
            %   romData - Struct with ROM data for each feature
            
            if nargin < 4
                features = obj.features;
            end
            if nargin < 5
                byCycle = true;
            end
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                romData = struct();
                return;
            end
            
            romData = struct();
            
            for i = 1:length(featureNames)
                featData = data3D(:, :, i); % (nCycles, 150)
                fieldName = matlab.lang.makeValidName(featureNames{i});
                
                if byCycle
                    % ROM per cycle
                    romData.(fieldName) = max(featData, [], 2) - min(featData, [], 2);
                else
                    % Overall ROM
                    romData.(fieldName) = max(featData(:)) - min(featData(:));
                end
            end
        end
        
        function plotTimeSeries(obj, subject, task, features, varargin)
            % Plot time series data for specific features
            %
            % Inputs:
            %   subject - Subject ID
            %   task - Task name
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'TimeCol' - Column name for time data (default: 'time_s')
            %     'SavePath' - Path to save plot
            
            p = inputParser;
            addParameter(p, 'TimeCol', 'time_s', @ischar);
            addParameter(p, 'SavePath', '', @ischar);
            parse(p, varargin{:});
            
            timeCol = p.Results.TimeCol;
            savePath = p.Results.SavePath;
            
            % Filter data
            mask = strcmp(obj.data.(obj.subjectCol), subject) & ...
                   strcmp(obj.data.(obj.taskCol), task);
            subset = obj.data(mask, :);
            
            if height(subset) == 0
                fprintf('No data found for %s - %s\n', subject, task);
                return;
            end
            
            % Create subplots
            nFeatures = length(features);
            figure;
            
            for i = 1:nFeatures
                subplot(nFeatures, 1, i);
                
                if any(strcmp(features{i}, subset.Properties.VariableNames)) && ...
                   any(strcmp(timeCol, subset.Properties.VariableNames))
                    plot(subset.(timeCol), subset.(features{i}), 'b-', 'LineWidth', 1);
                    ylabel(strrep(features{i}, '_', ' '));
                    grid on;
                else
                    text(0.5, 0.5, sprintf('Feature %s not found', features{i}), ...
                         'HorizontalAlignment', 'center', ...
                         'VerticalAlignment', 'middle');
                end
                
                if i == nFeatures
                    xlabel('Time (s)');
                end
            end
            
            sgtitle(sprintf('%s - %s', subject, task));
            
            if ~isempty(savePath)
                saveas(gcf, savePath);
                fprintf('Plot saved to %s\n', savePath);
            end
        end
        
        function plotPhasePatterns(obj, subject, task, features, varargin)
            % Plot phase-normalized patterns
            %
            % Inputs:
            %   subject - Subject ID
            %   task - Task name
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'PlotType' - 'mean', 'spaghetti', or 'both' (default: 'both')
            %     'SavePath' - Path to save plot
            
            p = inputParser;
            addParameter(p, 'PlotType', 'both', @ischar);
            addParameter(p, 'SavePath', '', @ischar);
            parse(p, varargin{:});
            
            plotType = p.Results.PlotType;
            savePath = p.Results.SavePath;
            
            [data3D, featureNames] = obj.getCycles(subject, task, features);
            
            if isempty(data3D)
                fprintf('No data found for %s - %s\n', subject, task);
                return;
            end
            
            % Get valid cycles
            validMask = obj.validateCycles(subject, task, features);
            
            % Create subplots
            nFeatures = length(featureNames);
            nCols = min(3, nFeatures);
            nRows = ceil(nFeatures / nCols);
            
            figure('Position', [100, 100, 400*nCols, 300*nRows]);
            phaseX = linspace(0, 100, obj.POINTS_PER_CYCLE);
            
            for i = 1:nFeatures
                subplot(nRows, nCols, i);
                
                featData = data3D(:, :, i);
                validData = featData(validMask, :);
                invalidData = featData(~validMask, :);
                
                hold on;
                
                % Plot individual cycles
                if strcmp(plotType, 'spaghetti') || strcmp(plotType, 'both')
                    % Valid cycles in gray
                    for j = 1:size(validData, 1)
                        plot(phaseX, validData(j, :), 'Color', [0.7 0.7 0.7], ...
                             'LineWidth', 0.8);
                    end
                    % Invalid cycles in red
                    for j = 1:size(invalidData, 1)
                        plot(phaseX, invalidData(j, :), 'r-', 'LineWidth', 0.8);
                    end
                end
                
                % Plot mean pattern
                if (strcmp(plotType, 'mean') || strcmp(plotType, 'both')) && ...
                   ~isempty(validData)
                    meanCurve = mean(validData, 1);
                    stdCurve = std(validData, 0, 1);
                    
                    if strcmp(plotType, 'mean')
                        % Fill std region
                        fill([phaseX, fliplr(phaseX)], ...
                             [meanCurve + stdCurve, fliplr(meanCurve - stdCurve)], ...
                             'b', 'FaceAlpha', 0.3, 'EdgeColor', 'none');
                    end
                    
                    plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
                end
                
                xlabel('Gait Cycle (%)');
                ylabel(strrep(featureNames{i}, '_', ' '));
                title(featureNames{i}, 'Interpreter', 'none');
                xlim([0 100]);
                grid on;
                hold off;
            end
            
            sgtitle(sprintf('%s - %s (Valid: %d/%d cycles)', ...
                           subject, task, sum(validMask), length(validMask)));
            
            if ~isempty(savePath)
                saveas(gcf, savePath);
                fprintf('Plot saved to %s\n', savePath);
            end
        end
        
        function plotTaskComparison(obj, subject, tasks, features, varargin)
            % Plot comparison of mean patterns across tasks
            %
            % Inputs:
            %   subject - Subject ID
            %   tasks - Cell array of task names
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'SavePath' - Path to save plot
            
            p = inputParser;
            addParameter(p, 'SavePath', '', @ischar);
            parse(p, varargin{:});
            
            savePath = p.Results.SavePath;
            
            % Create subplots
            nFeatures = length(features);
            nCols = min(3, nFeatures);
            nRows = ceil(nFeatures / nCols);
            
            figure('Position', [100, 100, 400*nCols, 300*nRows]);
            phaseX = linspace(0, 100, obj.POINTS_PER_CYCLE);
            colors = lines(length(tasks));
            
            for i = 1:nFeatures
                subplot(nRows, nCols, i);
                hold on;
                
                for j = 1:length(tasks)
                    meanPatterns = obj.getMeanPatterns(subject, tasks{j}, features(i));
                    fieldName = matlab.lang.makeValidName(features{i});
                    
                    if isfield(meanPatterns, fieldName)
                        plot(phaseX, meanPatterns.(fieldName), ...
                             'Color', colors(j, :), 'LineWidth', 2, ...
                             'DisplayName', tasks{j});
                    end
                end
                
                xlabel('Gait Cycle (%)');
                ylabel(strrep(features{i}, '_', ' '));
                title(features{i}, 'Interpreter', 'none');
                xlim([0 100]);
                grid on;
                legend('show');
                hold off;
            end
            
            sgtitle(sprintf('%s - Task Comparison', subject));
            
            if ~isempty(savePath)
                saveas(gcf, savePath);
                fprintf('Plot saved to %s\n', savePath);
            end
        end
        
        function fig = plotPhasePatterns_v2(obj, subject, task, features, varargin)
            % PLOTPHASEPATTERNS_V2 - Enhanced ggplot2-style phase pattern visualization
            %
            % This method provides publication-ready visualization with biomechanics-specific
            % themes, colorblind-friendly palettes, and advanced statistical annotations.
            %
            % Inputs:
            %   subject - Subject ID
            %   task - Task name  
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'PlotType' - 'mean', 'spaghetti', 'both', or 'ribbon' (default: 'both')
            %     'Theme' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
            %     'Colors' - 'joints', 'tasks', or 'subjects' (default: 'joints')
            %     'ShowInvalid' - Show invalid cycles (default: true)
            %     'ConfidenceLevel' - Confidence level for bands (default: 0.95)
            %     'SavePath' - Path to save figure
            %     'ExportFormat' - Export format(s) (default: {'png', 'pdf'})
            %     'AddPhaseLines' - Add stance/swing phase markers (default: true)
            %
            % Returns:
            %   fig - Figure handle
            %
            % Example:
            %   fig = loco.plotPhasePatterns_v2('SUB01', 'normal_walk', {'knee_flexion_angle_ipsi_rad'}, ...
            %                                   'PlotType', 'ribbon', 'Theme', 'publication', ...
            %                                   'SavePath', 'knee_analysis');
            
            % Use the enhanced visualization system
            fig = plotPhasePatterns(obj, subject, task, features, varargin{:});
        end
        
        function fig = plotTaskComparison_v2(obj, subject, tasks, features, varargin)
            % PLOTTASKCOMPARISON_V2 - Enhanced ggplot2-style task comparison
            %
            % Creates publication-ready task comparison plots with confidence bands,
            % biomechanics-specific color schemes, and advanced statistical visualization.
            %
            % Inputs:
            %   subject - Subject ID
            %   tasks - Cell array of task names
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'Theme' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
            %     'Colors' - Color palette name (default: 'tasks')
            %     'ShowConfidence' - Show confidence bands (default: true)
            %     'ConfidenceLevel' - Confidence level (default: 0.95)
            %     'SavePath' - Path to save figure
            %     'AddPhaseLines' - Add stance/swing markers (default: true)
            %
            % Returns:
            %   fig - Figure handle
            %
            % Example:
            %   fig = loco.plotTaskComparison_v2('SUB01', {'normal_walk', 'fast_walk'}, ...
            %                                    {'knee_flexion_angle_ipsi_rad'}, ...
            %                                    'ShowConfidence', true, 'SavePath', 'task_comparison');
            
            % Use the enhanced visualization system
            fig = plotTaskComparison(obj, subject, tasks, features, varargin{:});
        end
        
        function fig = plotSubjectComparison_v2(obj, subjects, task, features, varargin)
            % PLOTSUBJECTCOMPARISON_V2 - Enhanced population/group comparison plots
            %
            % Creates publication-ready population analysis plots with group statistics,
            % confidence intervals, and optional individual subject overlays.
            %
            % Inputs:
            %   subjects - Cell array of subject IDs
            %   task - Task name
            %   features - Cell array of feature names
            %   Optional name-value pairs:
            %     'GroupBy' - Grouping variable name (optional)
            %     'GroupData' - Table with grouping information (optional)
            %     'ShowIndividuals' - Show individual subject lines (default: false)
            %     'Theme' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
            %     'Colors' - Color palette name (default: 'subjects')
            %     'SavePath' - Path to save figure
            %
            % Returns:
            %   fig - Figure handle
            %
            % Example:
            %   % Simple population analysis
            %   fig = loco.plotSubjectComparison_v2({'SUB01', 'SUB02', 'SUB03'}, 'normal_walk', ...
            %                                       {'knee_flexion_angle_ipsi_rad'});
            %
            %   % Group comparison with metadata
            %   groupData = table({'SUB01'; 'SUB02'; 'SUB03'}, {'Control'; 'Control'; 'Patient'}, ...
            %                    'VariableNames', {'subject', 'group'});
            %   fig = loco.plotSubjectComparison_v2({'SUB01', 'SUB02', 'SUB03'}, 'normal_walk', ...
            %                                       {'knee_flexion_angle_ipsi_rad'}, ...
            %                                       'GroupBy', 'group', 'GroupData', groupData);
            
            % Use the enhanced visualization system
            fig = plotSubjectComparison(obj, subjects, task, features, varargin{:});
        end
        
        function fig = createPublicationFigure_v2(obj, figureSpec, varargin)
            % CREATEPUBLICATIONFIGURE_V2 - Create multi-panel publication figures
            %
            % Creates complex, multi-panel figures suitable for scientific publication
            % with consistent formatting, proper spacing, and publication-quality output.
            %
            % Inputs:
            %   figureSpec - Struct defining figure layout and content
            %   Optional name-value pairs:
            %     'Theme' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
            %     'Size' - Figure size preset: 'single', 'double', 'full' (default: 'double')
            %     'SavePath' - Path to save figure
            %     'ExportFormat' - Export formats (default: {'png', 'pdf', 'eps'})
            %
            % figureSpec format:
            %   .layout - [nRows, nCols] or 'custom'
            %   .panels - Cell array of panel specifications
            %   .title - Main figure title
            %   .caption - Figure caption (optional)
            %
            % Panel specification format:
            %   .type - 'phase_patterns', 'task_comparison', 'correlation_matrix', 'rom_comparison'
            %   .position - Panel position in subplot grid
            %   .subject - Subject ID (if applicable)
            %   .task - Task name (if applicable)
            %   .tasks - Task array (for comparisons)
            %   .features - Feature array
            %   .label - Panel label (A, B, C, etc.)
            %   .options - Additional plotting options
            %
            % Returns:
            %   fig - Figure handle
            %
            % Example:
            %   figSpec.layout = [2, 2];
            %   figSpec.title = 'Knee Kinematics Analysis';
            %   figSpec.panels{1} = struct('type', 'phase_patterns', 'position', 1, ...
            %                              'subject', 'SUB01', 'task', 'normal_walk', ...
            %                              'features', {{'knee_flexion_angle_ipsi_rad'}}, ...
            %                              'label', 'A');
            %   figSpec.panels{2} = struct('type', 'task_comparison', 'position', 2, ...
            %                              'subject', 'SUB01', 'tasks', {{'normal_walk', 'fast_walk'}}, ...
            %                              'features', {{'knee_flexion_angle_ipsi_rad'}}, ...
            %                              'label', 'B');
            %   fig = loco.createPublicationFigure_v2(figSpec, 'SavePath', 'publication_figure');
            
            % Use the enhanced visualization system
            fig = createPublicationFigure(obj, figureSpec, varargin{:});
        end
        
        function exportFigure_v2(obj, fig, savePath, varargin)
            % EXPORTFIGURE_V2 - Export figures with publication-quality settings
            %
            % Exports figures in multiple formats with proper DPI settings for
            % different publication requirements.
            %
            % Inputs:
            %   fig - Figure handle
            %   savePath - Base path for saving (without extension)
            %   Optional name-value pairs:
            %     'Format' - Cell array of formats (default: {'png', 'pdf'})
            %     'DPI' - Resolution for raster formats (default: 300)
            %     'Theme' - Theme struct for sizing adjustments
            %
            % Supported formats:
            %   'png' - High-resolution raster (300 DPI default)
            %   'pdf' - Vector format for publications
            %   'eps' - Vector format with TIFF preview
            %   'svg' - Scalable vector graphics
            %   'tiff' - High-quality raster format
            %
            % Example:
            %   loco.exportFigure_v2(fig, 'my_figure', 'Format', {'png', 'pdf', 'eps'}, 'DPI', 600);
            
            % Use the enhanced export system
            exportFigure(fig, savePath, varargin{:});
        end
        
        % =================== FILTERING METHODS ===================
        
        function filteredObj = filter(obj, varargin)
            % Filter data by subject and/or task
            %
            % Usage:
            %   filtered = loco.filter('Subject', 'SUB01');
            %   filtered = loco.filter('Task', 'level_walking');
            %   filtered = loco.filter('Subject', 'SUB01', 'Task', 'level_walking');
            %   filtered = loco.filter('Subjects', {'SUB01', 'SUB02'});
            %   filtered = loco.filter('Tasks', {'level_walking', 'incline_walking'});
            
            p = inputParser;
            addParameter(p, 'Subject', [], @(x) ischar(x) || iscell(x));
            addParameter(p, 'Subjects', [], @iscell);
            addParameter(p, 'Task', [], @(x) ischar(x) || iscell(x));
            addParameter(p, 'Tasks', [], @iscell);
            parse(p, varargin{:});
            
            % Start with all data
            filteredData = obj.data;
            
            % Filter by subject(s)
            subjectFilter = p.Results.Subjects;
            if isempty(subjectFilter)
                subjectFilter = p.Results.Subject;
            end
            
            if ~isempty(subjectFilter)
                if ischar(subjectFilter)
                    mask = strcmp(filteredData.(obj.subjectCol), subjectFilter);
                else % cell array
                    mask = ismember(filteredData.(obj.subjectCol), subjectFilter);
                end
                filteredData = filteredData(mask, :);
            end
            
            % Filter by task(s)
            taskFilter = p.Results.Tasks;
            if isempty(taskFilter)
                taskFilter = p.Results.Task;
            end
            
            if ~isempty(taskFilter)
                if ischar(taskFilter)
                    mask = strcmp(filteredData.(obj.taskCol), taskFilter);
                else % cell array
                    mask = ismember(filteredData.(obj.taskCol), taskFilter);
                end
                filteredData = filteredData(mask, :);
            end
            
            % Create new LocomotionData object with filtered data
            filteredObj = LocomotionData.empty();
            filteredObj(1).data = filteredData;
            filteredObj.dataPath = obj.dataPath;
            filteredObj.subjectCol = obj.subjectCol;
            filteredObj.taskCol = obj.taskCol;
            filteredObj.phaseCol = obj.phaseCol;
            filteredObj.cache = containers.Map();
            
            % Re-identify metadata for filtered data
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = filterTask(obj, task)
            % Convenience method for filtering by task
            filteredObj = obj.filter('Task', task);
        end
        
        function filteredObj = filterTasks(obj, tasks)
            % Convenience method for filtering by multiple tasks
            filteredObj = obj.filter('Tasks', tasks);
        end
        
        function filteredObj = filterSubject(obj, subject)
            % Convenience method for filtering by subject
            filteredObj = obj.filter('Subject', subject);
        end
        
        function filteredObj = filterSubjects(obj, subjects)
            % Convenience method for filtering by multiple subjects
            filteredObj = obj.filter('Subjects', subjects);
        end
        
        % =================== UTILITY METHODS ===================
        
        function [rows, cols] = getShape(obj)
            % Return shape of data table
            if nargout == 1
                rows = size(obj.data);
            else
                [rows, cols] = size(obj.data);
            end
        end
        
        function bytes = getMemoryUsage(obj)
            % Estimate memory usage of data table
            info = whos('obj');
            bytes = info.bytes;
        end
        
        function vars = getVariables(obj)
            % Return list of biomechanical variables (features)
            vars = obj.features;
        end
        
        function h = head(obj, n)
            % Return first n rows of data
            if nargin < 2
                n = 5;
            end
            h = obj.data(1:min(n, height(obj.data)), :);
        end
        
        function t = getDataTypes(obj)
            % Return data types of all columns
            varNames = obj.data.Properties.VariableNames;
            t = table();
            for i = 1:length(varNames)
                t.(varNames{i}) = class(obj.data.(varNames{i}));
            end
        end
        
        function n = length(obj)
            % Return number of rows in dataset
            n = height(obj.data);
        end
        
        % =================== DATA EXPLORATION METHODS ===================
        
        function subjects = getSubjects(obj)
            % Return list of unique subjects
            subjects = obj.subjects;
        end
        
        function tasks = getTasks(obj)
            % Return list of unique tasks
            tasks = obj.tasks;
        end
        
        function n = countCycles(obj, varargin)
            % Count cycles, optionally filtered by task
            p = inputParser;
            addParameter(p, 'Task', [], @(x) ischar(x) || isstring(x));
            parse(p, varargin{:});
            
            if isempty(p.Results.Task)
                % Count all unique cycles
                n = length(unique(obj.data.cycle_id));
            else
                % Count cycles for specific task
                taskData = obj.data(strcmp(obj.data.task, p.Results.Task), :);
                n = length(unique(taskData.cycle_id));
            end
        end
        
        function info = getVariableInfo(obj)
            % Return structure with variable type information
            info = struct();
            
            % Count kinematic variables (angles)
            angleVars = cellfun(@(x) contains(x, 'angle'), obj.features);
            info.kinematics.count = sum(angleVars);
            info.kinematics.variables = obj.features(angleVars);
            
            % Count kinetic variables (moments and forces)
            momentVars = cellfun(@(x) contains(x, 'moment'), obj.features);
            forceVars = cellfun(@(x) contains(x, 'force'), obj.features);
            
            info.kinetics.moments.count = sum(momentVars);
            info.kinetics.moments.variables = obj.features(momentVars);
            info.kinetics.forces.count = sum(forceVars);
            info.kinetics.forces.variables = obj.features(forceVars);
        end
        
        function desc = getVariableDescription(obj, varName)
            % Return human-readable description of a variable
            if ~any(strcmp(obj.features, varName))
                desc = 'Variable not found';
                return;
            end
            
            % Parse variable name
            parts = strsplit(varName, '_');
            
            % Build description
            if contains(varName, 'angle')
                joint = parts{1};
                motion = parts{2};
                side = parts{contains(parts, {'ipsi', 'contra'})};
                unit = parts{end};
                
                if strcmp(side, 'ipsi')
                    sideStr = 'Ipsilateral';
                else
                    sideStr = 'Contralateral';
                end
                
                desc = sprintf('%s %s %s angle in %s', ...
                    sideStr, joint, motion, unit);
                    
            elseif contains(varName, 'moment')
                joint = parts{1};
                side = parts{contains(parts, {'ipsi', 'contra'})};
                unit = parts{end};
                
                if strcmp(side, 'ipsi')
                    sideStr = 'Ipsilateral';
                else
                    sideStr = 'Contralateral';
                end
                
                desc = sprintf('%s %s moment in %s', ...
                    sideStr, joint, unit);
                    
            elseif contains(varName, 'force')
                desc = sprintf('Ground reaction force: %s', varName);
            else
                desc = varName;
            end
        end
        
        function describeVariables(obj)
            % Print descriptions of all variables
            fprintf('\nVariable Descriptions:\n');
            fprintf('======================\n');
            
            for i = 1:length(obj.features)
                desc = obj.getVariableDescription(obj.features{i});
                fprintf('%s:\n  %s\n', obj.features{i}, desc);
            end
        end
        
        function filteredObj = filterCycles(obj, cycles)
            % Filter data to specific cycle numbers
            mask = ismember(obj.data.cycle_id, cycles);
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(mask, :);
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = getFirstNCycles(obj, n)
            % Get first n cycles for each subject-task combination
            filteredData = table();
            
            uniqueCombos = unique(obj.data(:, {'subject', 'task'}));
            for i = 1:height(uniqueCombos)
                % Get subject and task for this combination
                if iscell(uniqueCombos.subject)
                    subj = uniqueCombos.subject{i};
                else
                    subj = uniqueCombos.subject(i);
                    if ~ischar(subj) && ~isstring(subj)
                        subj = char(subj);
                    end
                end
                
                if iscell(uniqueCombos.task)
                    task = uniqueCombos.task{i};
                else
                    task = uniqueCombos.task(i);
                    if ~ischar(task) && ~isstring(task)
                        task = char(task);
                    end
                end
                
                subset = obj.data(strcmp(obj.data.subject, subj) & ...
                                 strcmp(obj.data.task, task), :);
                uniqueCycles = unique(subset.cycle_id);
                keepCycles = uniqueCycles(1:min(n, length(uniqueCycles)));
                
                cycleData = subset(ismember(subset.cycle_id, keepCycles), :);
                filteredData = [filteredData; cycleData];
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = filteredData;
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = removeIncompleteCycles(obj, varargin)
            % Remove cycles with missing data
            p = inputParser;
            addParameter(p, 'CheckColumns', {}, @(x) iscell(x));
            parse(p, varargin{:});
            
            checkCols = p.Results.CheckColumns;
            if isempty(checkCols)
                checkCols = obj.features;
            end
            
            completeCycles = table();
            groups = findgroups(obj.data.subject, obj.data.task, obj.data.cycle_id);
            uniqueGroups = unique(groups);
            
            for g = uniqueGroups'
                groupData = obj.data(groups == g, :);
                
                hasComplete = true;
                for col = checkCols
                    if any(ismissing(groupData.(col{1})))
                        hasComplete = false;
                        break;
                    end
                end
                
                if hasComplete
                    completeCycles = [completeCycles; groupData];
                end
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = completeCycles;
            filteredObj.identifyMetadata();
        end
        
        function stats = getCycleQualityStats(obj)
            % Return statistics about cycle quality
            stats = struct();
            
            totalCycles = length(unique(obj.data.cycle_id));
            completeCycles = 0;
            
            groups = findgroups(obj.data.subject, obj.data.task, obj.data.cycle_id);
            uniqueGroups = unique(groups);
            
            for g = uniqueGroups'
                groupData = obj.data(groups == g, :);
                
                hasComplete = true;
                for i = 1:length(obj.features)
                    if any(ismissing(groupData.(obj.features{i})))
                        hasComplete = false;
                        break;
                    end
                end
                
                if hasComplete
                    completeCycles = completeCycles + 1;
                end
            end
            
            stats.totalCycles = totalCycles;
            stats.completeCycles = completeCycles;
            stats.percentComplete = 100 * completeCycles / totalCycles;
        end
        
        function filteredObj = selectVariableGroup(obj, group, varargin)
            % Select variables by group (e.g., 'kinematics', 'kinetics')
            p = inputParser;
            addParameter(p, 'Side', [], @(x) ischar(x) || isstring(x));
            parse(p, varargin{:});
            
            keepVars = {'subject', 'task', 'cycle_id', 'phase_percent'};
            
            if strcmp(group, 'kinematics')
                for i = 1:length(obj.features)
                    if contains(obj.features{i}, 'angle')
                        if isempty(p.Results.Side) || contains(obj.features{i}, p.Results.Side)
                            keepVars{end+1} = obj.features{i};
                        end
                    end
                end
            elseif strcmp(group, 'kinetics')
                for i = 1:length(obj.features)
                    if contains(obj.features{i}, 'moment') || contains(obj.features{i}, 'force')
                        if isempty(p.Results.Side) || contains(obj.features{i}, p.Results.Side)
                            keepVars{end+1} = obj.features{i};
                        end
                    end
                end
            end
            
            % Add phase columns if they exist
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_ipsi'))
                keepVars{end+1} = 'phase_ipsi';
            end
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_contra'))
                keepVars{end+1} = 'phase_contra';
            end
            
            % Ensure keepVars is a cell array and has valid columns
            keepVars = unique(keepVars, 'stable');
            validCols = intersect(keepVars, obj.data.Properties.VariableNames, 'stable');
            
            % Ensure validCols is not empty
            if isempty(validCols)
                error('No valid columns found for selection');
            end
            
            % Ensure validCols is a cell array
            if ~iscell(validCols)
                validCols = {validCols};
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(:, validCols);
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = selectVariables(obj, varargin)
            % Select multiple variable groups
            p = inputParser;
            addParameter(p, 'Groups', {}, @(x) iscell(x));
            addParameter(p, 'Side', [], @(x) ischar(x) || isstring(x));
            parse(p, varargin{:});
            
            keepVars = {'subject', 'task', 'cycle_id', 'phase_percent'};
            
            for g = 1:length(p.Results.Groups)
                group = p.Results.Groups{g};
                
                if strcmp(group, 'kinematics')
                    for i = 1:length(obj.features)
                        if contains(obj.features{i}, 'angle')
                            if isempty(p.Results.Side) || contains(obj.features{i}, p.Results.Side)
                                keepVars{end+1} = obj.features{i};
                            end
                        end
                    end
                elseif strcmp(group, 'kinetics')
                    for i = 1:length(obj.features)
                        if contains(obj.features{i}, 'moment') || contains(obj.features{i}, 'force')
                            if isempty(p.Results.Side) || contains(obj.features{i}, p.Results.Side)
                                keepVars{end+1} = obj.features{i};
                            end
                        end
                    end
                end
            end
            
            % Add phase columns if they exist
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_ipsi'))
                keepVars{end+1} = 'phase_ipsi';
            end
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_contra'))
                keepVars{end+1} = 'phase_contra';
            end
            
            % Ensure keepVars is a cell array and has valid columns
            keepVars = unique(keepVars, 'stable');
            validCols = intersect(keepVars, obj.data.Properties.VariableNames, 'stable');
            
            % Ensure validCols is not empty
            if isempty(validCols)
                error('No valid columns found for selection');
            end
            
            % Ensure validCols is a cell array
            if ~iscell(validCols)
                validCols = {validCols};
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(:, validCols);
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = getSideData(obj, side)
            % Get data for specific side (ipsi or contra)
            keepVars = {'subject', 'task', 'cycle_id', 'phase_percent'};
            
            for i = 1:length(obj.features)
                if contains(obj.features{i}, side)
                    keepVars{end+1} = obj.features{i};
                end
            end
            
            % Add phase columns if they exist
            if strcmp(side, 'ipsi') && any(strcmp(obj.data.Properties.VariableNames, 'phase_ipsi'))
                keepVars{end+1} = 'phase_ipsi';
            end
            if strcmp(side, 'contra') && any(strcmp(obj.data.Properties.VariableNames, 'phase_contra'))
                keepVars{end+1} = 'phase_contra';
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(:, unique(keepVars, 'stable'));
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = getBodyRegion(obj, region)
            % Get data for specific body region
            keepVars = {'subject', 'task', 'cycle_id', 'phase_percent'};
            
            if strcmp(region, 'lower')
                keywords = {'hip', 'knee', 'ankle', 'grf'};
            elseif strcmp(region, 'upper')
                keywords = {'shoulder', 'elbow', 'wrist'};
            else
                keywords = {};
            end
            
            for i = 1:length(obj.features)
                for j = 1:length(keywords)
                    if contains(obj.features{i}, keywords{j})
                        keepVars{end+1} = obj.features{i};
                        break;
                    end
                end
            end
            
            % Add phase columns if they exist
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_ipsi'))
                keepVars{end+1} = 'phase_ipsi';
            end
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_contra'))
                keepVars{end+1} = 'phase_contra';
            end
            
            % Ensure keepVars is a cell array and has valid columns
            keepVars = unique(keepVars, 'stable');
            validCols = intersect(keepVars, obj.data.Properties.VariableNames, 'stable');
            
            % Ensure validCols is not empty
            if isempty(validCols)
                error('No valid columns found for selection');
            end
            
            % Ensure validCols is a cell array
            if ~iscell(validCols)
                validCols = {validCols};
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(:, validCols);
            filteredObj.identifyMetadata();
        end
        
        function filteredObj = selectJoints(obj, joints)
            % Select data for specific joints
            keepVars = {'subject', 'task', 'cycle_id', 'phase_percent'};
            
            for i = 1:length(obj.features)
                for j = 1:length(joints)
                    if contains(obj.features{i}, joints{j})
                        keepVars{end+1} = obj.features{i};
                        break;
                    end
                end
            end
            
            % Add phase columns if they exist
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_ipsi'))
                keepVars{end+1} = 'phase_ipsi';
            end
            if any(strcmp(obj.data.Properties.VariableNames, 'phase_contra'))
                keepVars{end+1} = 'phase_contra';
            end
            
            % Ensure keepVars is a cell array and has valid columns
            keepVars = unique(keepVars, 'stable');
            validCols = intersect(keepVars, obj.data.Properties.VariableNames, 'stable');
            
            % Ensure validCols is not empty
            if isempty(validCols)
                error('No valid columns found for selection');
            end
            
            % Ensure validCols is a cell array
            if ~iscell(validCols)
                validCols = {validCols};
            end
            
            filteredObj = LocomotionData();
            filteredObj.data = obj.data(:, validCols);
            filteredObj.identifyMetadata();
        end
        
        function save(obj, filepath)
            % Save data to parquet file
            parquetwrite(filepath, obj.data);
        end
        
        function exportCSV(obj, filepath)
            % Export data to CSV file
            writetable(obj.data, filepath);
        end
    end
    
    methods (Access = private)
        function identifyMetadata(obj)
            % Identify subjects, tasks, and features
            
            % Handle empty data
            if isempty(obj.data) || height(obj.data) == 0
                obj.subjects = {};
                obj.tasks = {};
                obj.features = {};
                return;
            end
            
            % Check if required columns exist
            colNames = obj.data.Properties.VariableNames;
            if ~any(strcmp(colNames, obj.subjectCol)) || ~any(strcmp(colNames, obj.taskCol))
                obj.subjects = {};
                obj.tasks = {};
                obj.features = {};
                return;
            end
            
            % Ensure subjects and tasks are cell arrays
            subjs = unique(obj.data.(obj.subjectCol));
            if ~iscell(subjs)
                if isstring(subjs)
                    obj.subjects = cellstr(subjs);
                else
                    obj.subjects = {subjs};
                end
            else
                obj.subjects = subjs;
            end
            
            tsks = unique(obj.data.(obj.taskCol));
            if ~iscell(tsks)
                if isstring(tsks)
                    obj.tasks = cellstr(tsks);
                else
                    obj.tasks = {tsks};
                end
            else
                obj.tasks = tsks;
            end
            
            % Identify biomechanical features
            excludeCols = {obj.subjectCol, obj.taskCol, obj.phaseCol, ...
                          'time', 'time_s', 'step_number', 'is_reconstructed_contra', ...
                          'is_reconstructed_ipsi', 'task_info', 'activity_number'};
            
            allCols = obj.data.Properties.VariableNames;
            obj.features = {};
            
            for i = 1:length(allCols)
                col = allCols{i};
                if ~any(strcmp(col, excludeCols)) && ...
                   (contains(col, 'angle') || contains(col, 'velocity') || ...
                    contains(col, 'moment') || contains(col, 'force'))
                    obj.features{end+1} = col;
                end
            end
            
            % Determine data type and properties
            if any(strcmp(allCols, 'phase_percent'))
                obj.dataType = 'phase';
                obj.pointsPerCycle = 150;
                obj.samplingFrequency = [];
                obj.hasTimeColumn = false;
            elseif any(strcmp(allCols, 'time'))
                obj.dataType = 'time';
                obj.pointsPerCycle = [];
                obj.samplingFrequency = 100; % Default, should be determined from data
                obj.hasTimeColumn = true;
            else
                obj.dataType = 'unknown';
                obj.pointsPerCycle = [];
                obj.samplingFrequency = [];
                obj.hasTimeColumn = false;
            end
        end
    end
end