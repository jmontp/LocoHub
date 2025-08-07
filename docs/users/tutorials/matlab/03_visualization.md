# Tutorial 3: Basic Visualization

## Overview

Learn to create essential biomechanical visualizations: phase averages with standard deviation bands, spaghetti plots showing all cycles, and publication-ready figures.

## Learning Objectives

- Compute and plot phase averages
- Add standard deviation shading  
- Create spaghetti plots
- Customize plots for publication
- Compare multiple conditions

## Setup

=== "Using Library"
    ```matlab
    % Add library to path
    addpath('user_libs/matlab');
    
    % Load and filter data
    loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');
    levelWalking = loco.filterTask('level_walking').filterSubject('SUB01');
    
    % Set publication style
    loco.setPublicationStyle('biomechanics');
    ```

=== "Using Raw Data"
    ```matlab
    % Load data directly
    data = parquetread('converted_datasets/umich_2021_phase.parquet');
    
    % Filter for level walking, SUB01
    levelWalking = data(strcmp(data.task, 'level_walking') & ...
                       strcmp(data.subject, 'SUB01'), :);
    
    % Set plotting defaults
    set(groot, 'DefaultAxesFontSize', 12);
    set(groot, 'DefaultLineLineWidth', 1.5);
    ```

## Computing Phase Averages

### Basic Phase Average

=== "Using Library"
    ```matlab
    % Compute mean patterns using library method
    meanPatterns = levelWalking.getMeanPatterns('SUB01', 'level_walking');
    stdPatterns = levelWalking.getStdPatterns('SUB01', 'level_walking');
    
    % Get knee flexion data
    kneeMean = meanPatterns.knee_flexion_angle_ipsi_rad;
    kneeStd = stdPatterns.knee_flexion_angle_ipsi_rad;
    
    % Convert to degrees for plotting
    kneeMeanDeg = rad2deg(kneeMean);
    kneeStdDeg = rad2deg(kneeStd);
    ```

=== "Using Raw Data"
    ```matlab
    function [meanCurve, stdCurve] = computePhaseAverage(data, variable)
        % Compute mean and std across cycles for each phase point
        
        % Get unique phase percentages
        phases = unique(data.phase_percent);
        meanCurve = zeros(length(phases), 1);
        stdCurve = zeros(length(phases), 1);
        
        for i = 1:length(phases)
            phaseData = data.(variable)(data.phase_percent == phases(i));
            meanCurve(i) = mean(phaseData, 'omitnan');
            stdCurve(i) = std(phaseData, 'omitnan');
        end
    end
    
    % Compute average knee flexion
    [kneeMean, kneeStd] = computePhaseAverage(levelWalking, 'knee_flexion_angle_ipsi_rad');
    
    % Convert to degrees for plotting
    kneeMeanDeg = rad2deg(kneeMean);
    kneeStdDeg = rad2deg(kneeStd);
    ```

### Using Built-in Methods

=== "Using Library"
    ```matlab
    % Using LocomotionData methods
    meanPatterns = levelWalking.getMeanPatterns('SUB01', 'level_walking');
    
    % Get specific variables
    kneeMean = meanPatterns.knee_flexion_angle_ipsi_rad;
    hipMean = meanPatterns.hip_flexion_angle_ipsi_rad;
    ankleMean = meanPatterns.ankle_flexion_angle_ipsi_rad;
    
    % Get summary statistics
    summary = levelWalking.getSummaryStatistics('SUB01', 'level_walking', ...
                                               {'knee_flexion_angle_ipsi_rad'});
    ```

=== "Using Raw Data"
    ```matlab
    % Manual computation with groupsummary
    meanPatterns = struct();
    variables = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', ...
                'ankle_flexion_angle_ipsi_rad'};
    
    for i = 1:length(variables)
        var = variables{i};
        if any(strcmp(levelWalking.Properties.VariableNames, var))
            meanData = groupsummary(levelWalking, 'phase_percent', 'mean', var);
            meanPatterns.(var) = meanData.(['mean_' var]);
        end
    end
    ```

## Basic Plotting

### Simple Line Plot

=== "Using Library"
    ```matlab
    % Plot using built-in method
    figure();
    loco.plotPhasePatterns('SUB01', 'level_walking', ...
                          {'knee_flexion_angle_ipsi_rad'}, ...
                          'Units', 'degrees');
    ```

=== "Using Raw Data"
    ```matlab
    % Manual plotting
    phase = 0:100/149:100;  % 150 points per cycle
    
    figure();
    plot(phase, kneeMeanDeg, 'b-', 'LineWidth', 2);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Mean Knee Flexion - Level Walking');
    grid on;
    xlim([0 100]);
    ```

### Adding Standard Deviation Bands

=== "Using Library"
    ```matlab
    % Plot with standard deviation bands
    figure();
    loco.plotPhasePatterns('SUB01', 'level_walking', ...
                          {'knee_flexion_angle_ipsi_rad'}, ...
                          'Units', 'degrees', 'ShowStd', true);
    ```

=== "Using Raw Data"
    ```matlab
    % Manual plotting with std bands
    phase = 0:100/149:100;
    
    figure();
    hold on;
    
    % Plot standard deviation band
    upper = kneeMeanDeg + kneeStdDeg;
    lower = kneeMeanDeg - kneeStdDeg;
    fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
         [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
    
    % Plot mean line
    plot(phase, kneeMeanDeg, 'b-', 'LineWidth', 2);
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Mean ± SD Knee Flexion - Level Walking');
    grid on;
    xlim([0 100]);
    legend('±1 SD', 'Mean', 'Location', 'best');
    ```

## Spaghetti Plots

### All Individual Cycles

=== "Using Library"
    ```matlab
    % Create spaghetti plot using library method
    figure();
    loco.plotSpaghettiPlot('SUB01', 'level_walking', ...
                          {'knee_flexion_angle_ipsi_rad'}, ...
                          'Units', 'degrees', 'ShowMean', true);
    ```

=== "Using Raw Data"
    ```matlab
    % Manual spaghetti plot
    [data3D, featureNames] = levelWalking.getCycles('SUB01', 'level_walking', ...
                                                   {'knee_flexion_angle_ipsi_rad'});
    
    kneeData = squeeze(data3D(:, :, 1));  % Get knee data
    kneeDataDeg = rad2deg(kneeData);      % Convert to degrees
    
    phase = 0:100/149:100;
    
    figure();
    hold on;
    
    % Plot all cycles with transparency
    for cycle = 1:size(kneeDataDeg, 1)
        if ~any(isnan(kneeDataDeg(cycle, :)))
            plot(phase, kneeDataDeg(cycle, :), 'Color', [0.7 0.7 0.7 0.3]);
        end
    end
    
    % Overlay mean
    meanPattern = mean(kneeDataDeg, 1, 'omitnan');
    plot(phase, meanPattern, 'b-', 'LineWidth', 3);
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Individual Cycles - Knee Flexion');
    grid on;
    xlim([0 100]);
    ```

### Customizing Spaghetti Plots

=== "Using Library"
    ```matlab
    % Customized spaghetti plot
    figure();
    loco.plotSpaghettiPlot('SUB01', 'level_walking', ...
                          {'knee_flexion_angle_ipsi_rad'}, ...
                          'Units', 'degrees', ...
                          'Alpha', 0.2, ...
                          'Color', [0.8 0.2 0.2], ...
                          'ShowMean', true, ...
                          'ShowStd', true);
    ```

=== "Using Raw Data"
    ```matlab
    % Manual customized plotting
    figure();
    hold on;
    
    % Plot cycles with custom color and transparency
    for cycle = 1:size(kneeDataDeg, 1)
        if ~any(isnan(kneeDataDeg(cycle, :)))
            plot(phase, kneeDataDeg(cycle, :), 'Color', [0.8 0.2 0.2 0.2], ...
                 'LineWidth', 0.5);
        end
    end
    
    % Add mean and std
    meanPattern = mean(kneeDataDeg, 1, 'omitnan');
    stdPattern = std(kneeDataDeg, 1, 'omitnan');
    
    % Std band
    upper = meanPattern + stdPattern;
    lower = meanPattern - stdPattern;
    fill([phase, fliplr(phase)], [upper, fliplr(lower)], ...
         [0.8 0.2 0.2], 'FaceAlpha', 0.2, 'EdgeColor', 'none');
    
    % Mean line
    plot(phase, meanPattern, 'Color', [0.8 0.2 0.2], 'LineWidth', 3);
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Individual Cycles with Mean ± SD');
    grid on;
    xlim([0 100]);
    ```

## Multi-Variable Plots

### Multiple Features in Subplots

=== "Using Library"
    ```matlab
    % Plot multiple features
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', ...
               'ankle_flexion_angle_ipsi_rad'};
    
    figure();
    loco.plotPhasePatterns('SUB01', 'level_walking', features, ...
                          'Units', 'degrees', 'ShowStd', true);
    ```

=== "Using Raw Data"
    ```matlab
    % Manual multi-feature plotting
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', ...
               'ankle_flexion_angle_ipsi_rad'};
    titles = {'Knee Flexion', 'Hip Flexion', 'Ankle Flexion'};
    
    figure('Position', [100 100 1200 400]);
    
    for i = 1:length(features)
        [meanCurve, stdCurve] = computePhaseAverage(levelWalking, features{i});
        meanDeg = rad2deg(meanCurve);
        stdDeg = rad2deg(stdCurve);
        
        subplot(1, 3, i);
        hold on;
        
        % Std band
        upper = meanDeg + stdDeg;
        lower = meanDeg - stdDeg;
        fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
             [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
        
        % Mean line
        plot(phase, meanDeg, 'b-', 'LineWidth', 2);
        
        xlabel('Gait Cycle (%)');
        ylabel('Angle (deg)');
        title(titles{i});
        grid on;
        xlim([0 100]);
    end
    
    sgtitle('Joint Angles - Level Walking');
    ```

## Task Comparisons

### Multiple Tasks

=== "Using Library"
    ```matlab
    % Compare different tasks
    tasks = {'level_walking', 'incline_walking', 'decline_walking'};
    
    figure();
    loco.plotTaskComparison('SUB01', tasks, {'knee_flexion_angle_ipsi_rad'}, ...
                           'Units', 'degrees');
    ```

=== "Using Raw Data"
    ```matlab
    % Manual task comparison
    tasks = {'level_walking', 'incline_walking', 'decline_walking'};
    colors = {[0 0.4 0.8], [0.8 0.4 0], [0.8 0 0.4]};
    
    figure();
    hold on;
    
    for i = 1:length(tasks)
        taskData = data(strcmp(data.task, tasks{i}) & ...
                       strcmp(data.subject, 'SUB01'), :);
        
        if ~isempty(taskData)
            [meanCurve, ~] = computePhaseAverage(taskData, 'knee_flexion_angle_ipsi_rad');
            meanDeg = rad2deg(meanCurve);
            
            plot(phase, meanDeg, 'Color', colors{i}, 'LineWidth', 2, ...
                 'DisplayName', strrep(tasks{i}, '_', ' '));
        end
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Task Comparison - Knee Flexion');
    legend('show');
    grid on;
    xlim([0 100]);
    ```

## Publication-Ready Figures

### Setting Publication Style

=== "Using Library"
    ```matlab
    % Set journal-specific style
    loco.setPublicationStyle('biomechanics');  % or 'nature', 'ieee'
    
    % Create publication figure
    figure('Position', [100 100 800 600]);
    loco.plotPhasePatterns('SUB01', 'level_walking', ...
                          {'knee_flexion_angle_ipsi_rad'}, ...
                          'Units', 'degrees', 'ShowStd', true);
    
    % Save high-resolution figure
    print('knee_flexion_publication', '-dpng', '-r300');
    ```

=== "Using Raw Data"
    ```matlab
    % Manual publication styling
    set(groot, 'DefaultAxesFontSize', 12);
    set(groot, 'DefaultAxesFontName', 'Arial');
    set(groot, 'DefaultTextFontSize', 12);
    set(groot, 'DefaultLineLineWidth', 1.5);
    set(groot, 'DefaultAxesBox', 'off');
    
    % Create figure with specific size
    figure('Position', [100 100 800 600], 'Color', 'white');
    
    % Plot with publication formatting
    hold on;
    fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
         [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
    plot(phase, kneeMeanDeg, 'b-', 'LineWidth', 2);
    
    xlabel('Gait Cycle (%)', 'FontSize', 14, 'FontName', 'Arial');
    ylabel('Knee Flexion Angle (deg)', 'FontSize', 14, 'FontName', 'Arial');
    title('Mean Knee Flexion - Level Walking', 'FontSize', 16, 'FontName', 'Arial');
    
    grid on;
    xlim([0 100]);
    
    % Save high-resolution
    print('knee_flexion_publication', '-dpng', '-r300');
    print('knee_flexion_publication', '-depsc', '-r300');  % Vector format
    ```

## Advanced Visualization

### Multi-Panel Figures

=== "Using Library"
    ```matlab
    % Create multi-panel comparison
    subjects = {'SUB01', 'SUB02', 'SUB03'};
    
    figure('Position', [100 100 1200 800]);
    
    for i = 1:length(subjects)
        subplot(2, 2, i);
        subjectData = loco.filterSubject(subjects{i});
        subjectData.plotPhasePatterns(subjects{i}, 'level_walking', ...
                                    {'knee_flexion_angle_ipsi_rad'}, ...
                                    'Units', 'degrees', 'ShowStd', true);
        title(subjects{i});
    end
    
    % Add overall title
    subplot(2, 2, 4);
    % Summary plot or text
    text(0.5, 0.5, 'Summary Statistics', 'HorizontalAlignment', 'center');
    
    sgtitle('Multi-Subject Comparison');
    ```

=== "Using Raw Data"
    ```matlab
    % Manual multi-panel figure
    subjects = {'SUB01', 'SUB02', 'SUB03'};
    
    figure('Position', [100 100 1200 800]);
    
    for i = 1:length(subjects)
        subjectData = data(strcmp(data.subject, subjects{i}) & ...
                          strcmp(data.task, 'level_walking'), :);
        
        if ~isempty(subjectData)
            [meanCurve, stdCurve] = computePhaseAverage(subjectData, ...
                                                      'knee_flexion_angle_ipsi_rad');
            meanDeg = rad2deg(meanCurve);
            stdDeg = rad2deg(stdCurve);
            
            subplot(2, 2, i);
            hold on;
            
            upper = meanDeg + stdDeg;
            lower = meanDeg - stdDeg;
            fill([phase, fliplr(phase)], [upper', fliplr(lower')], ...
                 [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
            plot(phase, meanDeg, 'b-', 'LineWidth', 2);
            
            xlabel('Gait Cycle (%)');
            ylabel('Knee Flexion (deg)');
            title(subjects{i});
            grid on;
            xlim([0 100]);
        end
    end
    
    sgtitle('Multi-Subject Comparison - Knee Flexion');
    ```

## Best Practices

### Data Quality Checks
```matlab
% Check data completeness
[data3D, ~] = levelWalking.getCycles('SUB01', 'level_walking', ...
                                    {'knee_flexion_angle_ipsi_rad'});

% Count valid cycles
validCycles = sum(~any(isnan(data3D(:, :, 1)), 2));
totalCycles = size(data3D, 1);

fprintf('Valid cycles: %d/%d (%.1f%%)\n', validCycles, totalCycles, ...
        100 * validCycles / totalCycles);
```

### Unit Conversions
```matlab
% Always check and convert units for display
features = {'knee_flexion_angle_ipsi_rad', 'knee_flexion_velocity_ipsi_rad_s'};

for i = 1:length(features)
    if contains(features{i}, 'angle')
        fprintf('%s: radians → degrees\n', features{i});
    elseif contains(features{i}, 'velocity')
        fprintf('%s: rad/s → deg/s\n', features{i});
    end
end
```

### Saving Figures
```matlab
% Save in multiple formats for different uses
figName = 'knee_flexion_analysis';

% High-resolution PNG for presentations
print(figName, '-dpng', '-r300');

% Vector format for publications
print(figName, '-depsc', '-r300');

% MATLAB figure for further editing
savefig([figName '.fig']);
```

## Summary

You've learned to create essential biomechanical visualizations in MATLAB:

- **Phase averages** with mean and standard deviation patterns
- **Spaghetti plots** showing individual cycle variability
- **Multi-variable comparisons** across features and conditions
- **Publication-ready formatting** with appropriate styles
- **Quality checks** and unit conversions for reliable results

## Next Steps

[Continue to Tutorial 4: Cycle Analysis →](04_cycle_analysis.md)

Learn to analyze individual gait cycles, calculate ROM and peaks, and identify patterns in your data.