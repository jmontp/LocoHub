% BIOMECHANICS_VISUALIZATION - Comprehensive ggplot2-style visualization system for biomechanical data
%
% Created: 2025-06-19 with user permission
% Purpose: Publication-ready visualization system for LocomotionData with ggplot2-inspired design
%
% Intent: This module provides a complete visualization framework for biomechanical data,
% implementing ggplot2-style aesthetics and functionality specifically tailored for
% locomotion research. It includes themes, color palettes, plotting functions, and
% publication-ready templates that follow biomechanical visualization best practices.
%
% MAIN FUNCTIONS:
%   plotPhasePatterns     - Phase-normalized gait cycle visualization
%   plotTaskComparison    - Cross-task comparison plots  
%   plotSubjectComparison - Population/group comparison plots
%   createPublicationFigure - Multi-panel publication templates
%
% THEME FUNCTIONS:
%   getBiomechTheme       - Core biomechanics theme settings
%   getBiomechColors      - Colorblind-friendly color palettes
%   applyBiomechTheme     - Apply theme to existing figure
%
% UTILITY FUNCTIONS:
%   exportFigure          - Export with proper DPI and formats
%   addPhaseAnnotations   - Add stance/swing phase markers
%   calculateConfidenceBands - Statistical confidence intervals

%% =================================================================
%% CORE THEME AND COLOR PALETTE FUNCTIONS
%% =================================================================

function theme = getBiomechTheme(varargin)
    % GETBIOMECHTHEME - Get biomechanics-specific theme settings
    %
    % Inputs:
    %   Optional name-value pairs:
    %     'Style' - 'publication', 'presentation', or 'manuscript' (default: 'publication')
    %     'FontSize' - Base font size (default: 12)
    %     'LineWidth' - Base line width (default: 1.5)
    %
    % Returns:
    %   theme - Struct with theme settings
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Style', 'publication', @ischar);
    addParameter(p, 'FontSize', 12, @isnumeric);
    addParameter(p, 'LineWidth', 1.5, @isnumeric);
    parse(p, varargin{:});
    
    style = p.Results.Style;
    baseFontSize = p.Results.FontSize;
    baseLineWidth = p.Results.LineWidth;
    
    % Base theme settings
    theme = struct();
    theme.style = style;
    
    % Typography
    switch lower(style)
        case 'publication'
            theme.font.family = 'Arial';
            theme.font.size.title = baseFontSize + 2;
            theme.font.size.axis = baseFontSize;
            theme.font.size.label = baseFontSize;
            theme.font.size.legend = baseFontSize - 1;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'normal';
            
        case 'presentation'
            theme.font.family = 'Arial';
            theme.font.size.title = baseFontSize + 4;
            theme.font.size.axis = baseFontSize + 2;
            theme.font.size.label = baseFontSize + 2;
            theme.font.size.legend = baseFontSize;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'bold';
            
        case 'manuscript'
            theme.font.family = 'Times New Roman';
            theme.font.size.title = baseFontSize + 1;
            theme.font.size.axis = baseFontSize - 1;
            theme.font.size.label = baseFontSize - 1;
            theme.font.size.legend = baseFontSize - 2;
            theme.font.weight.title = 'bold';
            theme.font.weight.axis = 'normal';
    end
    
    % Lines and markers
    theme.line.width.main = baseLineWidth;
    theme.line.width.thin = baseLineWidth * 0.7;
    theme.line.width.thick = baseLineWidth * 1.5;
    theme.line.width.grid = 0.5;
    
    % Colors (defined using hex codes for consistency)
    theme.colors = getBiomechColors();
    
    % Layout
    theme.layout.margin = [0.08, 0.08, 0.08, 0.08]; % [left, bottom, right, top]
    theme.layout.spacing = 0.05;
    theme.layout.panel_background = [1, 1, 1]; % White
    theme.layout.grid_color = [0.9, 0.9, 0.9]; % Light gray
    theme.layout.grid_alpha = 0.7;
    
    % Axis formatting
    theme.axis.color = [0.2, 0.2, 0.2]; % Dark gray
    theme.axis.tick_length = 0.01;
    theme.axis.show_box = true;
    theme.axis.show_grid = true;
    
    % Legend
    theme.legend.location = 'northeast';
    theme.legend.frame = true;
    theme.legend.background = [1, 1, 1, 0.9]; % Semi-transparent white
end

function colors = getBiomechColors(varargin)
    % GETBIOMECHCOLORS - Get colorblind-friendly color palettes for biomechanical data
    %
    % Inputs:
    %   Optional name-value pairs:
    %     'Palette' - 'default', 'joints', 'tasks', 'subjects', or 'sequential' (default: 'default')
    %     'ColorblindSafe' - true/false (default: true)
    %
    % Returns:
    %   colors - Struct with color definitions
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Palette', 'default', @ischar);
    addParameter(p, 'ColorblindSafe', true, @islogical);
    parse(p, varargin{:});
    
    palette = p.Results.Palette;
    colorblindSafe = p.Results.ColorblindSafe;
    
    colors = struct();
    
    if colorblindSafe
        % Colorblind-friendly palettes based on ColorBrewer and Viridis
        switch lower(palette)
            case 'default'
                colors.primary = [0.12, 0.47, 0.71];    % Blue
                colors.secondary = [0.89, 0.47, 0.00];  % Orange
                colors.tertiary = [0.17, 0.63, 0.17];   % Green
                colors.quaternary = [0.84, 0.19, 0.15]; % Red
                colors.quinary = [0.58, 0.40, 0.74];    % Purple
                colors.senary = [0.55, 0.34, 0.29];     % Brown
                
            case 'joints'
                % Optimized for hip-knee-ankle visualization
                colors.hip = [0.89, 0.47, 0.00];        % Orange
                colors.knee = [0.12, 0.47, 0.71];       % Blue  
                colors.ankle = [0.17, 0.63, 0.17];      % Green
                colors.hip_light = [0.99, 0.75, 0.44];  % Light orange
                colors.knee_light = [0.68, 0.85, 0.90]; % Light blue
                colors.ankle_light = [0.78, 0.91, 0.78]; % Light green
                
            case 'tasks'
                % Optimized for different locomotor tasks
                colors.normal_walk = [0.12, 0.47, 0.71]; % Blue
                colors.fast_walk = [0.20, 0.63, 0.17];   % Green
                colors.slow_walk = [0.65, 0.81, 0.89];   % Light blue
                colors.incline_walk = [0.89, 0.47, 0.00]; % Orange
                colors.decline_walk = [0.99, 0.75, 0.44]; % Light orange
                colors.stair_ascent = [0.84, 0.19, 0.15]; % Red
                colors.stair_descent = [0.99, 0.68, 0.68]; % Light red
                colors.run = [0.58, 0.40, 0.74];         % Purple
                
            case 'subjects'
                % For population studies - using qualitative palette
                colors.subject_palette = [
                    0.12, 0.47, 0.71;  % Blue
                    0.89, 0.47, 0.00;  % Orange
                    0.17, 0.63, 0.17;  % Green
                    0.84, 0.19, 0.15;  % Red
                    0.58, 0.40, 0.74;  % Purple
                    0.55, 0.34, 0.29;  % Brown
                    0.89, 0.47, 0.76;  % Pink
                    0.50, 0.50, 0.50   % Gray
                ];
                
            case 'sequential'
                % For continuous data or phases
                colors.sequential_blue = [
                    0.97, 0.98, 1.00;
                    0.87, 0.92, 0.97;
                    0.68, 0.85, 0.90;
                    0.45, 0.68, 0.82;
                    0.21, 0.51, 0.74;
                    0.08, 0.35, 0.55;
                    0.03, 0.19, 0.38
                ];
        end
    else
        % Standard palette (not colorblind optimized)
        colors.primary = [0, 0.45, 0.74];
        colors.secondary = [0.85, 0.33, 0.10];
        colors.tertiary = [0.93, 0.69, 0.13];
        % ... additional standard colors
    end
    
    % Special biomechanical colors
    colors.valid_cycle = [0.3, 0.3, 0.3];        % Dark gray for valid data
    colors.invalid_cycle = [0.84, 0.19, 0.15];   % Red for invalid/outlier data
    colors.mean_line = [0.12, 0.47, 0.71];       % Blue for mean patterns
    colors.confidence_band = [0.68, 0.85, 0.90]; % Light blue for confidence
    colors.phase_annotation = [0.5, 0.5, 0.5];   % Gray for phase markers
    
    % Transparency values
    colors.alpha.cycle = 0.3;
    colors.alpha.confidence = 0.4;
    colors.alpha.background = 0.1;
end

function applyBiomechTheme(fig, theme)
    % APPLYBIOMECHTHEME - Apply biomechanics theme to existing figure
    %
    % Inputs:
    %   fig - Figure handle
    %   theme - Theme struct from getBiomechTheme()
    
    if nargin < 2
        theme = getBiomechTheme();
    end
    
    % Set current figure
    figure(fig);
    
    % Get all axes in figure
    axes_handles = findall(fig, 'Type', 'axes');
    
    for ax = axes_handles'
        % Font settings
        set(ax, 'FontName', theme.font.family);
        set(ax, 'FontSize', theme.font.size.axis);
        
        % Axis colors and styling
        set(ax, 'XColor', theme.axis.color);
        set(ax, 'YColor', theme.axis.color);
        set(ax, 'LineWidth', theme.line.width.thin);
        
        % Grid settings
        if theme.axis.show_grid
            grid(ax, 'on');
            set(ax, 'GridColor', theme.layout.grid_color);
            set(ax, 'GridAlpha', theme.layout.grid_alpha);
            set(ax, 'GridLineStyle', '-');
        end
        
        % Background
        set(ax, 'Color', theme.layout.panel_background);
        
        % Box
        if theme.axis.show_box
            box(ax, 'on');
        end
        
        % Title formatting
        title_handle = get(ax, 'Title');
        if ~isempty(title_handle.String)
            set(title_handle, 'FontSize', theme.font.size.title);
            set(title_handle, 'FontWeight', theme.font.weight.title);
        end
        
        % Label formatting
        xlabel_handle = get(ax, 'XLabel');
        ylabel_handle = get(ax, 'YLabel');
        set(xlabel_handle, 'FontSize', theme.font.size.label);
        set(ylabel_handle, 'FontSize', theme.font.size.label);
    end
    
    % Set figure background
    set(fig, 'Color', 'white');
    
    % Apply to legend if present
    legend_handles = findall(fig, 'Type', 'legend');
    for leg = legend_handles'
        set(leg, 'FontSize', theme.font.size.legend);
        set(leg, 'Location', theme.legend.location);
        if theme.legend.frame
            set(leg, 'Box', 'on');
        end
    end
end

%% =================================================================
%% MAIN PLOTTING FUNCTIONS
%% =================================================================

function fig = plotPhasePatterns(locoData, subject, task, features, varargin)
    % PLOTPHASEPATTERNS - Create ggplot2-style phase pattern visualization
    %
    % Inputs:
    %   locoData - LocomotionData object
    %   subject - Subject ID
    %   task - Task name
    %   features - Cell array of feature names
    %   Optional name-value pairs:
    %     'PlotType' - 'mean', 'spaghetti', 'both', or 'ribbon' (default: 'both')
    %     'Theme' - Theme struct or style name (default: 'publication')
    %     'Colors' - Color palette name (default: 'joints')
    %     'ShowInvalid' - Show invalid cycles (default: true)
    %     'ConfidenceLevel' - Confidence level for bands (default: 0.95)
    %     'SavePath' - Path to save figure
    %     'ExportFormat' - Export format(s) (default: {'png', 'pdf'})
    %     'AddPhaseLines' - Add stance/swing phase markers (default: true)
    %
    % Returns:
    %   fig - Figure handle
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'PlotType', 'both', @ischar);
    addParameter(p, 'Theme', 'publication', @(x) isstruct(x) || ischar(x));
    addParameter(p, 'Colors', 'joints', @ischar);
    addParameter(p, 'ShowInvalid', true, @islogical);
    addParameter(p, 'ConfidenceLevel', 0.95, @isnumeric);
    addParameter(p, 'SavePath', '', @ischar);
    addParameter(p, 'ExportFormat', {{'png', 'pdf'}}, @iscell);
    addParameter(p, 'AddPhaseLines', true, @islogical);
    parse(p, varargin{:});
    
    plotType = p.Results.PlotType;
    themeInput = p.Results.Theme;
    colorPalette = p.Results.Colors;
    showInvalid = p.Results.ShowInvalid;
    confidenceLevel = p.Results.ConfidenceLevel;
    savePath = p.Results.SavePath;
    exportFormat = p.Results.ExportFormat;
    addPhaseLines = p.Results.AddPhaseLines;
    
    % Get theme
    if isstruct(themeInput)
        theme = themeInput;
    else
        theme = getBiomechTheme('Style', themeInput);
    end
    
    % Get colors
    colors = getBiomechColors('Palette', colorPalette);
    
    % Get data
    [data3D, featureNames] = locoData.getCycles(subject, task, features);
    
    if isempty(data3D)
        error('No data found for subject ''%s'', task ''%s''', subject, task);
    end
    
    % Validate cycles
    validMask = locoData.validateCycles(subject, task, features);
    
    % Create figure
    nFeatures = length(featureNames);
    nCols = min(3, nFeatures);
    nRows = ceil(nFeatures / nCols);
    
    fig = figure('Position', [100, 100, 400*nCols, 300*nRows]);
    phaseX = linspace(0, 100, 150);
    
    for i = 1:nFeatures
        subplot(nRows, nCols, i);
        hold on;
        
        featData = data3D(:, :, i);
        validData = featData(validMask, :);
        invalidData = featData(~validMask, :);
        
        % Determine colors for this feature
        feature = featureNames{i};
        if contains(feature, 'hip')
            lineColor = colors.hip;
            lightColor = colors.hip_light;
        elseif contains(feature, 'knee')
            lineColor = colors.knee;
            lightColor = colors.knee_light;
        elseif contains(feature, 'ankle')
            lineColor = colors.ankle;
            lightColor = colors.ankle_light;
        else
            lineColor = colors.primary;
            lightColor = [0.8, 0.8, 0.8];
        end
        
        % Plot based on type
        if ismember(plotType, {'spaghetti', 'both'})
            % Plot individual cycles
            for j = 1:size(validData, 1)
                plot(phaseX, validData(j, :), 'Color', [colors.valid_cycle, colors.alpha.cycle], ...
                     'LineWidth', theme.line.width.thin);
            end
            
            % Plot invalid cycles if requested
            if showInvalid
                for j = 1:size(invalidData, 1)
                    plot(phaseX, invalidData(j, :), 'Color', colors.invalid_cycle, ...
                         'LineWidth', theme.line.width.thin, 'LineStyle', '--');
                end
            end
        end
        
        % Plot mean pattern and confidence bands
        if ismember(plotType, {'mean', 'both', 'ribbon'}) && ~isempty(validData)
            meanCurve = mean(validData, 1);
            
            if strcmp(plotType, 'ribbon') || strcmp(plotType, 'mean')
                % Calculate confidence bands
                [lowerBand, upperBand] = calculateConfidenceBands(validData, confidenceLevel);
                
                % Plot confidence band
                fill([phaseX, fliplr(phaseX)], [upperBand, fliplr(lowerBand)], ...
                     lightColor, 'FaceAlpha', colors.alpha.confidence, ...
                     'EdgeColor', 'none');
            else
                % Plot standard deviation band for 'both' type
                stdCurve = std(validData, 0, 1);
                fill([phaseX, fliplr(phaseX)], ...
                     [meanCurve + stdCurve, fliplr(meanCurve - stdCurve)], ...
                     lightColor, 'FaceAlpha', colors.alpha.confidence, ...
                     'EdgeColor', 'none');
            end
            
            % Plot mean line
            plot(phaseX, meanCurve, 'Color', lineColor, ...
                 'LineWidth', theme.line.width.thick);
        end
        
        % Add phase annotations
        if addPhaseLines
            addPhaseAnnotations(gca, colors.phase_annotation);
        end
        
        % Formatting
        xlabel('Gait Cycle (%)', 'FontSize', theme.font.size.label);
        ylabel(formatFeatureName(feature), 'FontSize', theme.font.size.label);
        title(formatFeatureName(feature), 'Interpreter', 'none', ...
              'FontSize', theme.font.size.title, 'FontWeight', theme.font.weight.title);
        xlim([0 100]);
        
        hold off;
    end
    
    % Add main title
    sgtitle(sprintf('%s - %s (Valid: %d/%d cycles)', ...
            subject, formatTaskName(task), sum(validMask), length(validMask)), ...
            'FontSize', theme.font.size.title + 2, 'FontWeight', 'bold');
    
    % Apply theme
    applyBiomechTheme(fig, theme);
    
    % Export if requested
    if ~isempty(savePath)
        exportFigure(fig, savePath, 'Format', exportFormat, 'Theme', theme);
    end
end

function fig = plotTaskComparison(locoData, subject, tasks, features, varargin)
    % PLOTTASKCOMPARISON - Create ggplot2-style task comparison plots
    %
    % Inputs:
    %   locoData - LocomotionData object
    %   subject - Subject ID
    %   tasks - Cell array of task names
    %   features - Cell array of feature names
    %   Optional name-value pairs:
    %     'Theme' - Theme struct or style name (default: 'publication')
    %     'Colors' - Color palette name (default: 'tasks')
    %     'ShowConfidence' - Show confidence bands (default: true)
    %     'ConfidenceLevel' - Confidence level (default: 0.95)
    %     'SavePath' - Path to save figure
    %     'AddPhaseLines' - Add stance/swing markers (default: true)
    %
    % Returns:
    %   fig - Figure handle
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Theme', 'publication', @(x) isstruct(x) || ischar(x));
    addParameter(p, 'Colors', 'tasks', @ischar);
    addParameter(p, 'ShowConfidence', true, @islogical);
    addParameter(p, 'ConfidenceLevel', 0.95, @isnumeric);
    addParameter(p, 'SavePath', '', @ischar);
    addParameter(p, 'AddPhaseLines', true, @islogical);
    parse(p, varargin{:});
    
    themeInput = p.Results.Theme;
    colorPalette = p.Results.Colors;
    showConfidence = p.Results.ShowConfidence;
    confidenceLevel = p.Results.ConfidenceLevel;
    savePath = p.Results.SavePath;
    addPhaseLines = p.Results.AddPhaseLines;
    
    % Get theme and colors
    if isstruct(themeInput)
        theme = themeInput;
    else
        theme = getBiomechTheme('Style', themeInput);
    end
    colors = getBiomechColors('Palette', colorPalette);
    
    % Create figure
    nFeatures = length(features);
    nCols = min(3, nFeatures);
    nRows = ceil(nFeatures / nCols);
    
    fig = figure('Position', [100, 100, 400*nCols, 300*nRows]);
    phaseX = linspace(0, 100, 150);
    
    % Get task colors
    taskColors = getTaskColors(tasks, colors);
    
    for i = 1:nFeatures
        subplot(nRows, nCols, i);
        hold on;
        
        legendEntries = {};
        
        for j = 1:length(tasks)
            % Get data for this task
            [data3D, ~] = locoData.getCycles(subject, tasks{j}, features(i));
            
            if ~isempty(data3D)
                % Validate cycles
                validMask = locoData.validateCycles(subject, tasks{j}, features(i));
                validData = data3D(validMask, :, 1);
                
                if ~isempty(validData)
                    meanCurve = mean(validData, 1);
                    
                    % Plot confidence band if requested
                    if showConfidence && size(validData, 1) > 1
                        [lowerBand, upperBand] = calculateConfidenceBands(validData, confidenceLevel);
                        fill([phaseX, fliplr(phaseX)], [upperBand, fliplr(lowerBand)], ...
                             taskColors{j}, 'FaceAlpha', colors.alpha.confidence, ...
                             'EdgeColor', 'none');
                    end
                    
                    % Plot mean line
                    plot(phaseX, meanCurve, 'Color', taskColors{j}, ...
                         'LineWidth', theme.line.width.thick, ...
                         'DisplayName', formatTaskName(tasks{j}));
                    
                    legendEntries{end+1} = formatTaskName(tasks{j});
                end
            end
        end
        
        % Add phase annotations
        if addPhaseLines
            addPhaseAnnotations(gca, colors.phase_annotation);
        end
        
        % Formatting
        xlabel('Gait Cycle (%)', 'FontSize', theme.font.size.label);
        ylabel(formatFeatureName(features{i}), 'FontSize', theme.font.size.label);
        title(formatFeatureName(features{i}), 'Interpreter', 'none', ...
              'FontSize', theme.font.size.title, 'FontWeight', theme.font.weight.title);
        xlim([0 100]);
        
        % Add legend
        if ~isempty(legendEntries)
            legend(legendEntries, 'Location', theme.legend.location, ...
                   'FontSize', theme.font.size.legend);
        end
        
        hold off;
    end
    
    % Add main title
    sgtitle(sprintf('%s - Task Comparison', subject), ...
            'FontSize', theme.font.size.title + 2, 'FontWeight', 'bold');
    
    % Apply theme
    applyBiomechTheme(fig, theme);
    
    % Export if requested
    if ~isempty(savePath)
        exportFigure(fig, savePath, 'Theme', theme);
    end
end

function fig = plotSubjectComparison(locoData, subjects, task, features, varargin)
    % PLOTSUBJECTCOMPARISON - Create population/group comparison plots
    %
    % Inputs:
    %   locoData - LocomotionData object
    %   subjects - Cell array of subject IDs
    %   task - Task name
    %   features - Cell array of feature names
    %   Optional name-value pairs:
    %     'GroupBy' - Grouping variable name (optional)
    %     'GroupData' - Table with grouping information (optional)
    %     'ShowIndividuals' - Show individual subject lines (default: false)
    %     'Theme' - Theme struct or style name (default: 'publication')
    %     'Colors' - Color palette name (default: 'subjects')
    %     'SavePath' - Path to save figure
    %
    % Returns:
    %   fig - Figure handle
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'GroupBy', '', @ischar);
    addParameter(p, 'GroupData', table(), @istable);
    addParameter(p, 'ShowIndividuals', false, @islogical);
    addParameter(p, 'Theme', 'publication', @(x) isstruct(x) || ischar(x));
    addParameter(p, 'Colors', 'subjects', @ischar);
    addParameter(p, 'SavePath', '', @ischar);
    parse(p, varargin{:});
    
    groupBy = p.Results.GroupBy;
    groupData = p.Results.GroupData;
    showIndividuals = p.Results.ShowIndividuals;
    themeInput = p.Results.Theme;
    colorPalette = p.Results.Colors;
    savePath = p.Results.SavePath;
    
    % Get theme and colors
    if isstruct(themeInput)
        theme = themeInput;
    else
        theme = getBiomechTheme('Style', themeInput);
    end
    colors = getBiomechColors('Palette', colorPalette);
    
    % Create figure
    nFeatures = length(features);
    nCols = min(3, nFeatures);
    nRows = ceil(nFeatures / nCols);
    
    fig = figure('Position', [100, 100, 400*nCols, 300*nRows]);
    phaseX = linspace(0, 100, 150);
    
    % Organize subjects by groups if specified
    if ~isempty(groupBy) && ~isempty(groupData)
        [groupedSubjects, groupNames] = organizeSubjectsByGroup(subjects, groupBy, groupData);
    else
        groupedSubjects = {subjects};
        groupNames = {'All Subjects'};
    end
    
    for i = 1:nFeatures
        subplot(nRows, nCols, i);
        hold on;
        
        legendEntries = {};
        
        for g = 1:length(groupedSubjects)
            groupSubjects = groupedSubjects{g};
            allGroupData = [];
            
            % Collect data from all subjects in group
            for s = 1:length(groupSubjects)
                [data3D, ~] = locoData.getCycles(groupSubjects{s}, task, features(i));
                
                if ~isempty(data3D)
                    validMask = locoData.validateCycles(groupSubjects{s}, task, features(i));
                    validData = data3D(validMask, :, 1);
                    
                    if ~isempty(validData)
                        if showIndividuals
                            % Plot individual subject mean
                            subjectMean = mean(validData, 1);
                            plot(phaseX, subjectMean, 'Color', [colors.subject_palette(mod(s-1, size(colors.subject_palette, 1))+1, :), 0.5], ...
                                 'LineWidth', theme.line.width.thin);
                        end
                        
                        % Add to group data
                        allGroupData = [allGroupData; validData];
                    end
                end
            end
            
            % Plot group statistics
            if ~isempty(allGroupData)
                groupMean = mean(allGroupData, 1);
                groupColor = colors.subject_palette(mod(g-1, size(colors.subject_palette, 1))+1, :);
                
                % Plot confidence band
                [lowerBand, upperBand] = calculateConfidenceBands(allGroupData, 0.95);
                fill([phaseX, fliplr(phaseX)], [upperBand, fliplr(lowerBand)], ...
                     groupColor, 'FaceAlpha', colors.alpha.confidence, ...
                     'EdgeColor', 'none');
                
                % Plot group mean
                plot(phaseX, groupMean, 'Color', groupColor, ...
                     'LineWidth', theme.line.width.thick, ...
                     'DisplayName', groupNames{g});
                
                legendEntries{end+1} = groupNames{g};
            end
        end
        
        % Formatting
        xlabel('Gait Cycle (%)', 'FontSize', theme.font.size.label);
        ylabel(formatFeatureName(features{i}), 'FontSize', theme.font.size.label);
        title(formatFeatureName(features{i}), 'Interpreter', 'none', ...
              'FontSize', theme.font.size.title, 'FontWeight', theme.font.weight.title);
        xlim([0 100]);
        
        % Add legend
        if ~isempty(legendEntries)
            legend(legendEntries, 'Location', theme.legend.location, ...
                   'FontSize', theme.font.size.legend);
        end
        
        hold off;
    end
    
    % Add main title
    if length(groupNames) == 1
        titleStr = sprintf('Population Analysis - %s (n=%d)', formatTaskName(task), length(subjects));
    else
        titleStr = sprintf('Group Comparison - %s', formatTaskName(task));
    end
    sgtitle(titleStr, 'FontSize', theme.font.size.title + 2, 'FontWeight', 'bold');
    
    % Apply theme
    applyBiomechTheme(fig, theme);
    
    % Export if requested
    if ~isempty(savePath)
        exportFigure(fig, savePath, 'Theme', theme);
    end
end

%% =================================================================
%% PUBLICATION TEMPLATES
%% =================================================================

function fig = createPublicationFigure(locoData, figureSpec, varargin)
    % CREATEPUBLICATIONFIGURE - Create multi-panel publication-ready figures
    %
    % Inputs:
    %   locoData - LocomotionData object
    %   figureSpec - Struct defining figure layout and content
    %   Optional name-value pairs:
    %     'Theme' - Theme struct or style name (default: 'publication')
    %     'Size' - Figure size preset: 'single', 'double', 'full' (default: 'double')
    %     'SavePath' - Path to save figure
    %     'ExportFormat' - Export formats (default: {'png', 'pdf', 'eps'})
    %
    % figureSpec format:
    %   .layout - [nRows, nCols] or 'custom'
    %   .panels - Cell array of panel specifications
    %   .title - Main figure title
    %   .caption - Figure caption
    %
    % Returns:
    %   fig - Figure handle
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Theme', 'publication', @(x) isstruct(x) || ischar(x));
    addParameter(p, 'Size', 'double', @ischar);
    addParameter(p, 'SavePath', '', @ischar);
    addParameter(p, 'ExportFormat', {{'png', 'pdf', 'eps'}}, @iscell);
    parse(p, varargin{:});
    
    themeInput = p.Results.Theme;
    figSize = p.Results.Size;
    savePath = p.Results.SavePath;
    exportFormat = p.Results.ExportFormat;
    
    % Get theme
    if isstruct(themeInput)
        theme = themeInput;
    else
        theme = getBiomechTheme('Style', themeInput);
    end
    
    % Determine figure size
    switch lower(figSize)
        case 'single'
            figWidth = 400;
            figHeight = 300;
        case 'double'
            figWidth = 800;
            figHeight = 600;
        case 'full'
            figWidth = 1200;
            figHeight = 900;
        otherwise
            figWidth = 800;
            figHeight = 600;
    end
    
    % Create figure
    fig = figure('Position', [100, 100, figWidth, figHeight]);
    
    % Set up layout
    if isnumeric(figureSpec.layout)
        nRows = figureSpec.layout(1);
        nCols = figureSpec.layout(2);
    else
        % Custom layout handling would go here
        nRows = 2;
        nCols = 2;
    end
    
    % Create panels
    for p = 1:length(figureSpec.panels)
        panel = figureSpec.panels{p};
        
        if isfield(panel, 'position')
            subplot(nRows, nCols, panel.position);
        else
            subplot(nRows, nCols, p);
        end
        
        % Create panel content based on type
        switch lower(panel.type)
            case 'phase_patterns'
                createPhasePanel(locoData, panel, theme);
            case 'task_comparison'
                createTaskComparisonPanel(locoData, panel, theme);
            case 'correlation_matrix'
                createCorrelationPanel(locoData, panel, theme);
            case 'rom_comparison'
                createROMPanel(locoData, panel, theme);
            otherwise
                text(0.5, 0.5, 'Panel type not implemented', ...
                     'HorizontalAlignment', 'center');
        end
        
        % Add panel label
        if isfield(panel, 'label')
            addPanelLabel(gca, panel.label, theme);
        end
    end
    
    % Add main title
    if isfield(figureSpec, 'title')
        sgtitle(figureSpec.title, 'FontSize', theme.font.size.title + 4, ...
                'FontWeight', 'bold');
    end
    
    % Apply theme
    applyBiomechTheme(fig, theme);
    
    % Export if requested
    if ~isempty(savePath)
        exportFigure(fig, savePath, 'Format', exportFormat, 'Theme', theme);
    end
end

%% =================================================================
%% UTILITY FUNCTIONS
%% =================================================================

function exportFigure(fig, savePath, varargin)
    % EXPORTFIGURE - Export figure with proper DPI and formats
    %
    % Inputs:
    %   fig - Figure handle
    %   savePath - Base path for saving (without extension)
    %   Optional name-value pairs:
    %     'Format' - Cell array of formats (default: {'png', 'pdf'})
    %     'DPI' - Resolution for raster formats (default: 300)
    %     'Theme' - Theme struct for sizing
    
    % Parse inputs
    p = inputParser;
    addParameter(p, 'Format', {{'png', 'pdf'}}, @iscell);
    addParameter(p, 'DPI', 300, @isnumeric);
    addParameter(p, 'Theme', struct(), @isstruct);
    parse(p, varargin{:});
    
    formats = p.Results.Format;
    dpi = p.Results.DPI;
    theme = p.Results.Theme;
    
    % Ensure formats is a cell array
    if ischar(formats)
        formats = {formats};
    elseif iscell(formats) && iscell(formats{1})
        formats = formats{1};
    end
    
    % Set paper properties for consistent sizing
    set(fig, 'PaperPositionMode', 'auto');
    set(fig, 'PaperUnits', 'inches');
    
    for i = 1:length(formats)
        format = formats{i};
        filename = sprintf('%s.%s', savePath, format);
        
        switch lower(format)
            case 'png'
                print(fig, filename, '-dpng', sprintf('-r%d', dpi));
                
            case 'pdf'
                print(fig, filename, '-dpdf', '-bestfit');
                
            case 'eps'
                print(fig, filename, '-depsc2', '-tiff');
                
            case 'svg'
                print(fig, filename, '-dsvg');
                
            case 'tiff' 
                print(fig, filename, '-dtiff', sprintf('-r%d', dpi));
                
            otherwise
                warning('Unknown format: %s', format);
        end
        
        fprintf('Figure saved: %s\n', filename);
    end
end

function addPhaseAnnotations(ax, color)
    % ADDPHASEANNOTATIONS - Add stance/swing phase markers
    %
    % Inputs:
    %   ax - Axes handle
    %   color - Color for phase lines
    
    % Typical stance phase end (~60% of gait cycle)
    stanceEnd = 60;
    
    % Get current y-limits
    ylims = ylim(ax);
    
    % Add vertical line at stance/swing transition
    line([stanceEnd, stanceEnd], ylims, 'Color', color, ...
         'LineStyle', '--', 'LineWidth', 1, 'Alpha', 0.7);
    
    % Add phase labels
    text(30, ylims(2) * 0.95, 'Stance', 'HorizontalAlignment', 'center', ...
         'Color', color, 'FontSize', 10, 'FontWeight', 'bold');
    text(80, ylims(2) * 0.95, 'Swing', 'HorizontalAlignment', 'center', ...
         'Color', color, 'FontSize', 10, 'FontWeight', 'bold');
end

function [lowerBand, upperBand] = calculateConfidenceBands(data, confidenceLevel)
    % CALCULATECONFIDENCEBANDS - Calculate statistical confidence intervals
    %
    % Inputs:
    %   data - Matrix of data (nCycles x nPhases)
    %   confidenceLevel - Confidence level (e.g., 0.95 for 95%)
    %
    % Returns:
    %   lowerBand - Lower confidence bound
    %   upperBand - Upper confidence bound
    
    if size(data, 1) < 2
        % Not enough data for confidence intervals
        meanData = mean(data, 1);
        lowerBand = meanData;
        upperBand = meanData;
        return;
    end
    
    % Calculate standard error
    meanData = mean(data, 1);
    stdData = std(data, 0, 1);
    n = size(data, 1);
    sem = stdData / sqrt(n);
    
    % Calculate t-statistic for confidence level
    alpha = 1 - confidenceLevel;
    tStat = tinv(1 - alpha/2, n - 1);
    
    % Calculate confidence bands
    margin = tStat * sem;
    lowerBand = meanData - margin;
    upperBand = meanData + margin;
end

function formattedName = formatFeatureName(featureName)
    % FORMATFEATURENAME - Format feature names for display
    %
    % Inputs:
    %   featureName - Raw feature name
    %
    % Returns:
    %   formattedName - Formatted name for display
    
    % Replace underscores with spaces
    formattedName = strrep(featureName, '_', ' ');
    
    % Capitalize first letter of each word
    words = split(formattedName, ' ');
    for i = 1:length(words)
        if ~isempty(words{i})
            words{i}(1) = upper(words{i}(1));
        end
    end
    formattedName = strjoin(words, ' ');
    
    % Add units
    if contains(featureName, 'angle') && contains(featureName, 'rad')
        formattedName = [formattedName, ' (rad)'];
    elseif contains(featureName, 'moment') && contains(featureName, 'Nm')
        formattedName = [formattedName, ' (Nm)'];
    elseif contains(featureName, 'velocity') && contains(featureName, 'rad_s')
        formattedName = [formattedName, ' (rad/s)'];
    end
end

function formattedName = formatTaskName(taskName)
    % FORMATTASKNAME - Format task names for display
    %
    % Inputs:
    %   taskName - Raw task name
    %
    % Returns:
    %   formattedName - Formatted name for display
    
    % Replace underscores with spaces
    formattedName = strrep(taskName, '_', ' ');
    
    % Capitalize first letter of each word
    words = split(formattedName, ' ');
    for i = 1:length(words)
        if ~isempty(words{i})
            words{i}(1) = upper(words{i}(1));
        end
    end
    formattedName = strjoin(words, ' ');
end

function taskColors = getTaskColors(tasks, colors)
    % GETTASKCOLORS - Get colors for specific tasks
    %
    % Inputs:
    %   tasks - Cell array of task names
    %   colors - Colors struct
    %
    % Returns:
    %   taskColors - Cell array of RGB colors
    
    taskColors = cell(length(tasks), 1);
    
    for i = 1:length(tasks)
        task = tasks{i};
        
        % Try to match specific task colors
        if isfield(colors, strrep(task, ' ', '_'))
            taskColors{i} = colors.(strrep(task, ' ', '_'));
        elseif contains(task, 'normal') || contains(task, 'level')
            taskColors{i} = colors.normal_walk;
        elseif contains(task, 'fast')
            taskColors{i} = colors.fast_walk;
        elseif contains(task, 'slow')
            taskColors{i} = colors.slow_walk;
        elseif contains(task, 'incline') || contains(task, 'up')
            taskColors{i} = colors.incline_walk;
        elseif contains(task, 'decline') || contains(task, 'down')
            taskColors{i} = colors.decline_walk;
        elseif contains(task, 'stair') && contains(task, 'up')
            taskColors{i} = colors.stair_ascent;
        elseif contains(task, 'stair') && contains(task, 'down')
            taskColors{i} = colors.stair_descent;
        elseif contains(task, 'run')
            taskColors{i} = colors.run;
        else
            % Use default palette
            colorIdx = mod(i-1, size(colors.subject_palette, 1)) + 1;
            taskColors{i} = colors.subject_palette(colorIdx, :);
        end
    end
end

function [groupedSubjects, groupNames] = organizeSubjectsByGroup(subjects, groupBy, groupData)
    % ORGANIZESUBJECTSBYGROUP - Organize subjects into groups
    %
    % Inputs:
    %   subjects - Cell array of subject IDs
    %   groupBy - Column name for grouping
    %   groupData - Table with grouping information
    %
    % Returns:
    %   groupedSubjects - Cell array of subject groups
    %   groupNames - Group names
    
    groupedSubjects = {};
    groupNames = {};
    
    % Find unique groups
    uniqueGroups = unique(groupData.(groupBy));
    
    for i = 1:length(uniqueGroups)
        group = uniqueGroups{i};
        
        % Find subjects in this group
        groupMask = strcmp(groupData.(groupBy), group);
        groupSubjectList = groupData.subject(groupMask);
        
        % Filter to requested subjects
        groupSubjects = intersect(subjects, groupSubjectList);
        
        if ~isempty(groupSubjects)
            groupedSubjects{end+1} = groupSubjects;
            groupNames{end+1} = group;
        end
    end
end

function createPhasePanel(locoData, panel, theme)
    % Helper function to create phase pattern panel content
    % Implementation would go here based on panel specifications
end

function createTaskComparisonPanel(locoData, panel, theme)
    % Helper function to create task comparison panel content
    % Implementation would go here based on panel specifications
end

function createCorrelationPanel(locoData, panel, theme)
    % Helper function to create correlation matrix panel content
    % Implementation would go here based on panel specifications
end

function createROMPanel(locoData, panel, theme)
    % Helper function to create ROM comparison panel content
    % Implementation would go here based on panel specifications
end

function addPanelLabel(ax, label, theme)
    % ADDPANELLABEL - Add panel label (A, B, C, etc.)
    %
    % Inputs:
    %   ax - Axes handle
    %   label - Label text
    %   theme - Theme struct
    
    % Get axes position
    pos = get(ax, 'Position');
    axPos = get(ax, 'OuterPosition');
    
    % Add label outside the plot area
    annotation('textbox', [axPos(1) - 0.05, axPos(2) + axPos(4) - 0.05, 0.05, 0.05], ...
               'String', label, 'FontSize', theme.font.size.title + 2, ...
               'FontWeight', 'bold', 'LineStyle', 'none', ...
               'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
end