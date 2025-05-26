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
    end
    
    properties (Access = private)
        cache           % Cache for 3D arrays
    end
    
    methods
        function obj = LocomotionData(dataPath, varargin)
            % Constructor - Load locomotion data from parquet file
            %
            % Inputs:
            %   dataPath - Path to parquet file
            %   Optional name-value pairs:
            %     'SubjectCol' - Column name for subjects (default: 'subject')
            %     'TaskCol' - Column name for tasks (default: 'task')
            %     'PhaseCol' - Column name for phase (default: 'phase')
            
            % Parse inputs
            p = inputParser;
            addRequired(p, 'dataPath', @ischar);
            addParameter(p, 'SubjectCol', 'subject', @ischar);
            addParameter(p, 'TaskCol', 'task', @ischar);
            addParameter(p, 'PhaseCol', 'phase', @ischar);
            parse(p, dataPath, varargin{:});
            
            obj.dataPath = p.Results.dataPath;
            obj.subjectCol = p.Results.SubjectCol;
            obj.taskCol = p.Results.TaskCol;
            obj.phaseCol = p.Results.PhaseCol;
            
            % Load data
            fprintf('Loading data from %s...\n', obj.dataPath);
            obj.data = parquetread(obj.dataPath);
            
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
    end
    
    methods (Access = private)
        function identifyMetadata(obj)
            % Identify subjects, tasks, and features
            
            obj.subjects = unique(obj.data.(obj.subjectCol));
            obj.tasks = unique(obj.data.(obj.taskCol));
            
            % Identify biomechanical features
            excludeCols = {obj.subjectCol, obj.taskCol, obj.phaseCol, ...
                          'time', 'time_s', 'step_number', 'is_reconstructed_r', ...
                          'is_reconstructed_l', 'task_info', 'activity_number'};
            
            allCols = obj.data.Properties.VariableNames;
            obj.features = {};
            
            for i = 1:length(allCols)
                col = allCols{i};
                if ~any(strcmp(col, excludeCols)) && ...
                   (contains(col, 'angle') || contains(col, 'velocity') || ...
                    contains(col, 'moment'))
                    obj.features{end+1} = col;
                end
            end
        end
    end
end