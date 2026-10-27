% LOCOMOTION_HELPERS - Standalone helper functions for locomotion data analysis
%
% This file contains utility functions for working with standardized
% locomotion data in MATLAB without requiring the LocomotionData class.
%
% Functions:
%   efficientReshape3D - Reshape phase data to 3D array
%   calculateMeanPatterns - Calculate mean gait patterns
%   validateCycles - Validate cycles based on constraints
%   plotMosaicData - Create mosaic plots
%   exportToCSV - Export processed data to CSV

function [data3D, featureNames] = efficientReshape3D(dataTable, subject, task, features, varargin)
    % EFFICIENTRESHAPE3D - Reshape phase-indexed data to 3D array
    %
    % This is the core reshaping function for efficient data access.
    %
    % Inputs:
    %   dataTable - Table with phase-indexed data
    %   subject - Subject ID
    %   task - Task name
    %   features - Cell array of feature names
    %   Optional name-value pairs:
    %     'SubjectCol' - Column name for subjects (default: 'subject')
    %     'TaskCol' - Column name for tasks (default: 'task')
    %     'PointsPerCycle' - Points per cycle (default: 150)
    %
    % Outputs:
    %   data3D - 3D array (nCycles, pointsPerCycle, nFeatures)
    %   featureNames - Cell array of valid feature names
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'SubjectCol', 'subject', @ischar);
    addParameter(p, 'TaskCol', 'task', @ischar);
    addParameter(p, 'PointsPerCycle', 150, @isnumeric);
    parse(p, varargin{:});
    
    subjectCol = p.Results.SubjectCol;
    taskCol = p.Results.TaskCol;
    pointsPerCycle = p.Results.PointsPerCycle;
    
    % Filter data
    mask = strcmp(dataTable.(subjectCol), subject) & ...
           strcmp(dataTable.(taskCol), task);
    subset = dataTable(mask, :);
    
    if height(subset) == 0
        data3D = [];
        featureNames = {};
        return;
    end
    
    % Check data length
    numPoints = height(subset);
    if mod(numPoints, pointsPerCycle) ~= 0
        warning('Data length %d not divisible by %d', numPoints, pointsPerCycle);
        data3D = [];
        featureNames = {};
        return;
    end
    
    numCycles = numPoints / pointsPerCycle;
    
    % Filter to valid features
    validFeatures = features(ismember(features, subset.Properties.VariableNames));
    if isempty(validFeatures)
        data3D = [];
        featureNames = {};
        return;
    end
    
    % Extract all features at once
    featureData = table2array(subset(:, validFeatures));
    
    % Reshape to 3D
    data3D = reshape(featureData, pointsPerCycle, numCycles, length(validFeatures));
    data3D = permute(data3D, [2, 1, 3]); % Reorder to (nCycles, pointsPerCycle, nFeatures)
    
    featureNames = validFeatures;
end

function [meanPatterns, stdPatterns] = calculateMeanPatterns(data3D, featureNames)
    % CALCULATEMEANPATTERNS - Calculate mean and std patterns from 3D data
    %
    % Inputs:
    %   data3D - 3D array (nCycles, 150, nFeatures)
    %   featureNames - Cell array of feature names
    %
    % Outputs:
    %   meanPatterns - Struct with mean patterns for each feature
    %   stdPatterns - Struct with std patterns for each feature
    
    if isempty(data3D)
        meanPatterns = struct();
        stdPatterns = struct();
        return;
    end
    
    % Calculate statistics
    meanData = squeeze(mean(data3D, 1)); % (150, nFeatures)
    stdData = squeeze(std(data3D, 0, 1)); % (150, nFeatures)
    
    % Handle single feature case
    if length(featureNames) == 1
        meanData = meanData(:);
        stdData = stdData(:);
    end
    
    % Create structs
    meanPatterns = struct();
    stdPatterns = struct();
    
    for i = 1:length(featureNames)
        fieldName = matlab.lang.makeValidName(featureNames{i});
        if length(featureNames) == 1
            meanPatterns.(fieldName) = meanData;
            stdPatterns.(fieldName) = stdData;
        else
            meanPatterns.(fieldName) = meanData(:, i);
            stdPatterns.(fieldName) = stdData(:, i);
        end
    end
end

function validMask = validateCycles(data3D, featureNames)
    % VALIDATECYCLES - Validate cycles based on biomechanical constraints
    %
    % Inputs:
    %   data3D - 3D array (nCycles, 150, nFeatures)
    %   featureNames - Cell array of feature names
    %
    % Outputs:
    %   validMask - Logical array (nCycles, 1) indicating valid cycles
    
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
        
        % Range checks
        if contains(feature, 'angle')
            % Angles: -pi to pi radians
            outOfRange = any(featData < -pi | featData > pi, 2);
            validMask = validMask & ~outOfRange;
            
            % Large discontinuities
            diffs = abs(diff(featData, 1, 2));
            largeJumps = any(diffs > 0.5236, 2); % 30 degrees = 0.5236 radians
            validMask = validMask & ~largeJumps;
            
        elseif contains(feature, 'velocity')
            % Velocities: reasonable range in rad/s
            outOfRange = any(abs(featData) > 17.45, 2); % 1000 deg/s = 17.45 rad/s
            validMask = validMask & ~outOfRange;
            
        elseif contains(feature, 'moment')
            % Moments: reasonable range
            outOfRange = any(abs(featData) > 300, 2);
            validMask = validMask & ~outOfRange;
        end
        
        % Check for NaN or Inf
        hasInvalid = any(~isfinite(featData), 2);
        validMask = validMask & ~hasInvalid;
    end
end

function fig = plotMosaicData(data3D, featureNames, varargin)
    % PLOTMOSAICDATA - Create mosaic plot of biomechanical data
    %
    % Inputs:
    %   data3D - 3D array (nCycles, 150, nFeatures)
    %   featureNames - Cell array of feature names
    %   Optional name-value pairs:
    %     'Title' - Plot title
    %     'ValidMask' - Logical array indicating valid cycles
    %     'PlotType' - 'mean', 'spaghetti', or 'both' (default: 'both')
    %
    % Outputs:
    %   fig - Figure handle
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Title', 'Biomechanical Data', @ischar);
    addParameter(p, 'ValidMask', [], @islogical);
    addParameter(p, 'PlotType', 'both', @ischar);
    parse(p, varargin{:});
    
    plotTitle = p.Results.Title;
    validMask = p.Results.ValidMask;
    plotType = p.Results.PlotType;
    
    if isempty(validMask)
        validMask = true(size(data3D, 1), 1);
    end
    
    % Create figure
    nFeatures = length(featureNames);
    nCols = min(3, nFeatures);
    nRows = ceil(nFeatures / nCols);
    
    fig = figure('Position', [100, 100, 400*nCols, 300*nRows]);
    phaseX = linspace(0, 100, 150);
    
    for i = 1:nFeatures
        subplot(nRows, nCols, i);
        
        featData = data3D(:, :, i);
        validData = featData(validMask, :);
        invalidData = featData(~validMask, :);
        
        % Plot based on type
        hold on;
        
        if ismember(plotType, {'spaghetti', 'both'})
            % Plot valid cycles
            for j = 1:size(validData, 1)
                plot(phaseX, validData(j, :), 'Color', [0.5 0.5 0.5], ...
                     'LineWidth', 0.5, 'Alpha', 0.3);
            end
            
            % Plot invalid cycles
            for j = 1:size(invalidData, 1)
                plot(phaseX, invalidData(j, :), 'r-', ...
                     'LineWidth', 0.8, 'Alpha', 0.5);
            end
        end
        
        if ismember(plotType, {'mean', 'both'}) && ~isempty(validData)
            meanCurve = mean(validData, 1);
            stdCurve = std(validData, 0, 1);
            
            if strcmp(plotType, 'mean')
                % Fill std region
                fill([phaseX, fliplr(phaseX)], ...
                     [meanCurve + stdCurve, fliplr(meanCurve - stdCurve)], ...
                     'b', 'FaceAlpha', 0.3, 'EdgeColor', 'none');
            end
            
            % Plot mean
            plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
        end
        
        % Format
        xlabel('Gait Cycle (%)');
        ylabel(strrep(featureNames{i}, '_', ' '));
        title(featureNames{i}, 'Interpreter', 'none');
        xlim([0 100]);
        grid on;
        hold off;
    end
    
    sgtitle(plotTitle);
end

function exportToCSV(data3D, featureNames, filename, varargin)
    % EXPORTTOCSV - Export 3D data to CSV format
    %
    % Inputs:
    %   data3D - 3D array (nCycles, 150, nFeatures)
    %   featureNames - Cell array of feature names
    %   filename - Output CSV filename
    %   Optional name-value pairs:
    %     'Format' - 'long' or 'wide' (default: 'long')
    %     'Subject' - Subject ID to include
    %     'Task' - Task name to include
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Format', 'long', @ischar);
    addParameter(p, 'Subject', '', @ischar);
    addParameter(p, 'Task', '', @ischar);
    parse(p, varargin{:});
    
    format = p.Results.Format;
    subject = p.Results.Subject;
    task = p.Results.Task;
    
    if strcmp(format, 'long')
        % Long format: cycle, phase, feature1, feature2, ...
        nCycles = size(data3D, 1);
        nPhases = size(data3D, 2);
        
        % Preallocate
        totalRows = nCycles * nPhases;
        cycleCol = repelem((1:nCycles)', nPhases);
        phaseCol = repmat((0:nPhases-1)' / (nPhases-1) * 100, nCycles, 1);
        
        % Create table
        T = table(cycleCol, phaseCol, 'VariableNames', {'Cycle', 'Phase'});
        
        % Add subject and task if provided
        if ~isempty(subject)
            T.Subject = repmat({subject}, totalRows, 1);
        end
        if ~isempty(task)
            T.Task = repmat({task}, totalRows, 1);
        end
        
        % Add feature data
        for i = 1:length(featureNames)
            featData = data3D(:, :, i);
            T.(featureNames{i}) = featData(:);
        end
        
    else
        % Wide format: cycle, feature1_0, feature1_1, ..., feature2_0, ...
        nCycles = size(data3D, 1);
        
        % Create table with cycle numbers
        T = table((1:nCycles)', 'VariableNames', {'Cycle'});
        
        % Add each feature's phases as columns
        for i = 1:length(featureNames)
            featData = data3D(:, :, i);
            for phase = 1:size(featData, 2)
                colName = sprintf('%s_%d', featureNames{i}, phase-1);
                T.(colName) = featData(:, phase);
            end
        end
    end
    
    % Write to CSV
    writetable(T, filename);
    fprintf('Exported data to %s\n', filename);
end

% Example usage function
function exampleUsage()
    % Example: Load and process data
    
    % Load parquet file
    dataTable = parquetread('locomotion_data.parquet');
    
    % Define features of interest
    features = {'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'};
    
    % Reshape to 3D
    [data3D, featureNames] = efficientReshape3D(dataTable, 'SUB01', 'normal_walk', features);
    
    % Calculate mean patterns
    [meanPatterns, stdPatterns] = calculateMeanPatterns(data3D, featureNames);
    
    % Validate cycles
    validMask = validateCycles(data3D, featureNames);
    fprintf('Valid cycles: %d/%d\n', sum(validMask), length(validMask));
    
    % Create plot
    fig = plotMosaicData(data3D, featureNames, 'ValidMask', validMask);
    
    % Export to CSV
    exportToCSV(data3D, featureNames, 'processed_data.csv', ...
                'Subject', 'SUB01', 'Task', 'normal_walk');
end