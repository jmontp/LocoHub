function [meanCurve, stdCurve] = computePhaseAverage(data, variable)
    % Compute mean and std across cycles for each phase point
    % 
    % Inputs:
    %   data - Table with phase_percent and variable columns
    %   variable - String name of the variable to average
    %
    % Outputs:
    %   meanCurve - 150x1 array of mean values
    %   stdCurve - 150x1 array of standard deviation values
    
    % Get unique phase percentages (should be 0-149)
    phases = unique(data.phase_percent);
    nPhases = length(phases);
    
    meanCurve = zeros(nPhases, 1);
    stdCurve = zeros(nPhases, 1);
    
    % Compute statistics for each phase point
    for i = 1:nPhases
        phaseData = data.(variable)(data.phase_percent == phases(i));
        meanCurve(i) = mean(phaseData, 'omitnan');
        stdCurve(i) = std(phaseData, 'omitnan');
    end
end

function fig = createSpaghettiPlot(data, variable, varargin)
    % Create spaghetti plot showing all individual cycles
    %
    % Inputs:
    %   data - Table with cycle_id, phase_percent, and variable columns
    %   variable - String name of the variable to plot
    %   varargin - Optional parameters:
    %     'ShowMean' - true/false to show mean line (default: true)
    %     'ShowStd' - true/false to show std band (default: false)
    %     'Units' - 'radians' or 'degrees' (default: 'radians')
    %     'Alpha' - Transparency for individual lines (default: 0.3)
    %     'Color' - Color for individual lines (default: [0.7 0.7 0.7])
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'ShowMean', true, @islogical);
    addParameter(p, 'ShowStd', false, @islogical);
    addParameter(p, 'Units', 'radians', @ischar);
    addParameter(p, 'Alpha', 0.3, @isnumeric);
    addParameter(p, 'Color', [0.7 0.7 0.7], @isnumeric);
    parse(p, varargin{:});
    
    % Create figure
    fig = figure();
    hold on;
    
    % Get phase array
    phase = 0:100/149:100;
    
    % Get unique cycles
    cycles = unique(data.cycle_id);
    
    % Plot each cycle
    for i = 1:length(cycles)
        cycleData = data(data.cycle_id == cycles(i), :);
        cycleData = sortrows(cycleData, 'phase_percent');
        
        values = cycleData.(variable);
        
        % Convert units if needed
        if strcmpi(p.Results.Units, 'degrees') && contains(variable, '_rad')
            values = rad2deg(values);
        end
        
        % Plot with transparency
        plot(phase, values, 'Color', [p.Results.Color p.Results.Alpha], ...
             'LineWidth', 0.5);
    end
    
    % Add mean and std if requested
    if p.Results.ShowMean || p.Results.ShowStd
        [meanCurve, stdCurve] = computePhaseAverage(data, variable);
        
        % Convert units
        if strcmpi(p.Results.Units, 'degrees') && contains(variable, '_rad')
            meanCurve = rad2deg(meanCurve);
            stdCurve = rad2deg(stdCurve);
        end
        
        % Plot std band
        if p.Results.ShowStd
            upper = meanCurve + stdCurve;
            lower = meanCurve - stdCurve;
            fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
                 'b', 'FaceAlpha', 0.2, 'EdgeColor', 'none');
        end
        
        % Plot mean line
        if p.Results.ShowMean
            plot(phase, meanCurve, 'b-', 'LineWidth', 2);
        end
    end
    
    % Formatting
    xlabel('Gait Cycle (%)');
    if strcmpi(p.Results.Units, 'degrees') && contains(variable, '_rad')
        ylabel([strrep(variable, '_', ' ') ' (deg)']);
    else
        ylabel(strrep(variable, '_', ' '));
    end
    title(['Spaghetti Plot - ' strrep(variable, '_', ' ')]);
    grid on;
    xlim([0 100]);
    
    fig = gcf;
end

function applyPublicationStyle(style)
    % Apply publication-specific formatting to current axes
    %
    % Inputs:
    %   style - String: 'biomechanics', 'nature', 'ieee', or 'default'
    
    switch lower(style)
        case 'biomechanics'
            set(gca, 'FontSize', 12, 'FontName', 'Arial');
            set(gca, 'LineWidth', 1.5);
            set(gca, 'Box', 'off');
            set(gca, 'TickDir', 'out');
            
        case 'nature'
            set(gca, 'FontSize', 10, 'FontName', 'Helvetica');
            set(gca, 'LineWidth', 1);
            set(gca, 'Box', 'off');
            
        case 'ieee'
            set(gca, 'FontSize', 11, 'FontName', 'Times New Roman');
            set(gca, 'LineWidth', 1);
            set(gca, 'Box', 'on');
            
        otherwise
            % Reset to defaults
            set(gca, 'FontSize', 10);
            set(gca, 'LineWidth', 0.5);
    end
end

function fig = plotPhaseComparison(data, variable, groupingVar, varargin)
    % Plot comparison of a variable across different groups
    %
    % Inputs:
    %   data - Table with data
    %   variable - String name of variable to plot
    %   groupingVar - String name of grouping variable (e.g., 'task')
    %   varargin - Optional parameters
    
    % Parse optional inputs
    p = inputParser;
    addParameter(p, 'Units', 'radians', @ischar);
    addParameter(p, 'ShowStd', true, @islogical);
    parse(p, varargin{:});
    
    % Get unique groups
    groups = unique(data.(groupingVar));
    nGroups = length(groups);
    
    % Set up colors
    colors = lines(nGroups);
    
    % Create figure
    fig = figure();
    hold on;
    
    phase = 0:100/149:100;
    
    % Plot each group
    for i = 1:nGroups
        groupData = data(strcmp(data.(groupingVar), groups{i}), :);
        
        if height(groupData) > 0
            [meanCurve, stdCurve] = computePhaseAverage(groupData, variable);
            
            % Convert units
            if strcmpi(p.Results.Units, 'degrees') && contains(variable, '_rad')
                meanCurve = rad2deg(meanCurve);
                stdCurve = rad2deg(stdCurve);
            end
            
            % Plot std band if requested
            if p.Results.ShowStd
                upper = meanCurve + stdCurve;
                lower = meanCurve - stdCurve;
                fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
                     colors(i,:), 'FaceAlpha', 0.2, 'EdgeColor', 'none');
            end
            
            % Plot mean line
            plot(phase, meanCurve, 'Color', colors(i,:), 'LineWidth', 2, ...
                 'DisplayName', strrep(groups{i}, '_', ' '));
        end
    end
    
    % Formatting
    xlabel('Gait Cycle (%)');
    if strcmpi(p.Results.Units, 'degrees') && contains(variable, '_rad')
        ylabel([strrep(variable, '_', ' ') ' (deg)']);
    else
        ylabel(strrep(variable, '_', ' '));
    end
    title(['Comparison by ' strrep(groupingVar, '_', ' ')]);
    legend('show', 'Location', 'best');
    grid on;
    xlim([0 100]);
    
    fig = gcf;
end