% DEMO_BIOMECHANICS_VISUALIZATION - Comprehensive demonstration of ggplot2-style visualization system
%
% Created: 2025-06-19 with user permission
% Purpose: Demonstrate the biomechanics visualization system capabilities
%
% Intent: This script showcases all features of the enhanced visualization system,
% including themes, color palettes, phase patterns, task comparisons, population
% analysis, and publication-ready figures. It serves as both a demo and a
% comprehensive tutorial for users.
%
% DEMONSTRATION SECTIONS:
% 1. Basic Setup and Data Loading
% 2. Theme and Color Palette Showcase
% 3. Phase Pattern Visualization Variants
% 4. Task Comparison Analysis
% 5. Population/Group Comparison
% 6. Publication Figure Templates
% 7. Export Functionality Demo

%% =================================================================
%% SECTION 1: BASIC SETUP AND DATA LOADING
%% =================================================================

fprintf('=== Biomechanics Visualization System Demo ===\n\n');

% Check if sample data exists
dataPath = 'converted_datasets/gtech_2023_phase_AB01.parquet';
if ~exist(dataPath, 'file')
    fprintf('Sample data not found at: %s\n', dataPath);
    fprintf('Please ensure sample dataset is available or modify the path.\n');
    fprintf('This demo will create synthetic data for illustration.\n\n');
    
    % Create synthetic data for demo
    createSyntheticDemo();
    return;
end

% Load data
fprintf('1. Loading locomotion data...\n');
try
    loco = LocomotionData(dataPath);
    fprintf('   Successfully loaded data with %d subjects, %d tasks\n', ...
            length(loco.subjects), length(loco.tasks));
    
    % Display available features
    fprintf('   Available biomechanical features:\n');
    for i = 1:min(5, length(loco.features))
        fprintf('     - %s\n', loco.features{i});
    end
    if length(loco.features) > 5
        fprintf('     ... and %d more features\n', length(loco.features) - 5);
    end
    fprintf('\n');
    
catch ME
    fprintf('Error loading data: %s\n', ME.message);
    fprintf('Creating synthetic demo instead...\n\n');
    createSyntheticDemo();
    return;
end

%% =================================================================
%% SECTION 2: THEME AND COLOR PALETTE SHOWCASE
%% =================================================================

fprintf('2. Demonstrating themes and color palettes...\n');

% Get different themes
themes = {'publication', 'presentation', 'manuscript'};
colors = {'joints', 'tasks', 'subjects'};

% Create theme comparison figure
fig_themes = figure('Position', [100, 100, 1200, 400]);

for i = 1:length(themes)
    subplot(1, 3, i);
    
    % Get theme
    theme = getBiomechTheme('Style', themes{i});
    biomechColors = getBiomechColors('Palette', 'joints');
    
    % Create sample plot
    x = linspace(0, 100, 150);
    y1 = sin(2*pi*x/100) + 0.5;
    y2 = cos(2*pi*x/100) + 0.2;
    y3 = sin(4*pi*x/100) * 0.3 + 0.1;
    
    hold on;
    plot(x, y1, 'Color', biomechColors.hip, 'LineWidth', theme.line.width.thick, 'DisplayName', 'Hip');
    plot(x, y2, 'Color', biomechColors.knee, 'LineWidth', theme.line.width.thick, 'DisplayName', 'Knee');
    plot(x, y3, 'Color', biomechColors.ankle, 'LineWidth', theme.line.width.thick, 'DisplayName', 'Ankle');
    
    xlabel('Gait Cycle (%)', 'FontSize', theme.font.size.label);
    ylabel('Joint Angle (rad)', 'FontSize', theme.font.size.label);
    title(sprintf('%s Theme', themes{i}), 'FontSize', theme.font.size.title, ...
          'FontWeight', theme.font.weight.title);
    legend('show', 'Location', 'northeast', 'FontSize', theme.font.size.legend);
    xlim([0 100]);
    grid on;
    hold off;
    
    % Apply theme
    applyBiomechTheme(gcf, theme);
end

sgtitle('Theme Comparison', 'FontSize', 16, 'FontWeight', 'bold');

% Save theme comparison
exportFigure(fig_themes, 'demo_themes_comparison', 'Format', {'png'});
fprintf('   Theme comparison saved as: demo_themes_comparison.png\n');

% Demonstrate color palettes
fig_colors = figure('Position', [100, 150, 1200, 300]);

for i = 1:length(colors)
    subplot(1, 3, i);
    
    paletteColors = getBiomechColors('Palette', colors{i});
    
    % Create color demonstration
    if strcmp(colors{i}, 'joints')
        colorData = [paletteColors.hip; paletteColors.knee; paletteColors.ankle];
        labels = {'Hip', 'Knee', 'Ankle'};
    elseif strcmp(colors{i}, 'tasks')
        colorData = [paletteColors.normal_walk; paletteColors.fast_walk; paletteColors.incline_walk];
        labels = {'Normal Walk', 'Fast Walk', 'Incline Walk'};
    else
        colorData = paletteColors.subject_palette(1:3, :);
        labels = {'Subject 1', 'Subject 2', 'Subject 3'};
    end
    
    bar(1:size(colorData, 1), ones(size(colorData, 1), 1), 'FaceColor', 'flat', 'CData', colorData);
    set(gca, 'XTickLabel', labels);
    title(sprintf('%s Palette', colors{i}));
    ylabel('Color Sample');
end

sgtitle('Color Palette Showcase', 'FontSize', 16, 'FontWeight', 'bold');
exportFigure(fig_colors, 'demo_color_palettes', 'Format', {'png'});
fprintf('   Color palettes saved as: demo_color_palettes.png\n\n');

%% =================================================================
%% SECTION 3: PHASE PATTERN VISUALIZATION VARIANTS
%% =================================================================

fprintf('3. Demonstrating phase pattern visualizations...\n');

% Select subject and task for demo
subject = loco.subjects{1};
task = loco.tasks{1};
features = {'knee_flexion_angle_ipsi_rad'};

if ~ismember('knee_flexion_angle_ipsi_rad', loco.features)
    % Use first available angle feature
    angleFeatures = loco.features(contains(loco.features, 'angle'));
    if ~isempty(angleFeatures)
        features = angleFeatures(1);
    else
        features = loco.features(1);
    end
end

fprintf('   Using subject: %s, task: %s, feature: %s\n', subject, task, features{1});

% Demonstrate different plot types
plotTypes = {'mean', 'spaghetti', 'both', 'ribbon'};

fig_patterns = figure('Position', [100, 200, 1600, 400]);

for i = 1:length(plotTypes)
    subplot(1, 4, i);
    
    % Note: Since we may not have the full visualization system loaded,
    % we'll create a simplified version using the existing LocomotionData methods
    [data3D, featureNames] = loco.getCycles(subject, task, features);
    
    if ~isempty(data3D)
        validMask = loco.validateCycles(subject, task, features);
        featData = data3D(:, :, 1);
        validData = featData(validMask, :);
        
        phaseX = linspace(0, 100, 150);
        hold on;
        
        switch plotTypes{i}
            case 'mean'
                if ~isempty(validData)
                    meanCurve = mean(validData, 1);
                    stdCurve = std(validData, 0, 1);
                    fill([phaseX, fliplr(phaseX)], ...
                         [meanCurve + stdCurve, fliplr(meanCurve - stdCurve)], ...
                         [0.7 0.7 0.9], 'FaceAlpha', 0.4, 'EdgeColor', 'none');
                    plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
                end
                
            case 'spaghetti'
                for j = 1:size(validData, 1)
                    plot(phaseX, validData(j, :), 'Color', [0.5 0.5 0.5 0.3], 'LineWidth', 0.8);
                end
                
            case 'both'
                % Plot individual cycles
                for j = 1:size(validData, 1)
                    plot(phaseX, validData(j, :), 'Color', [0.7 0.7 0.7 0.3], 'LineWidth', 0.8);
                end
                % Plot mean
                if ~isempty(validData)
                    meanCurve = mean(validData, 1);
                    plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
                end
                
            case 'ribbon'
                if ~isempty(validData) && size(validData, 1) > 1
                    meanCurve = mean(validData, 1);
                    sem = std(validData, 0, 1) / sqrt(size(validData, 1));
                    tVal = tinv(0.975, size(validData, 1) - 1);
                    ci = tVal * sem;
                    
                    fill([phaseX, fliplr(phaseX)], ...
                         [meanCurve + ci, fliplr(meanCurve - ci)], ...
                         [0.7 0.7 0.9], 'FaceAlpha', 0.4, 'EdgeColor', 'none');
                    plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
                end
        end
        
        xlabel('Gait Cycle (%)');
        ylabel('Angle (rad)');
        title(sprintf('%s Plot', plotTypes{i}));
        xlim([0 100]);
        grid on;
        hold off;
    else
        text(0.5, 0.5, 'No data available', 'HorizontalAlignment', 'center');
    end
end

sgtitle(sprintf('Phase Pattern Plot Types - %s', features{1}), 'FontSize', 14, 'FontWeight', 'bold');
exportFigure(fig_patterns, 'demo_pattern_types', 'Format', {'png'});
fprintf('   Pattern types demo saved as: demo_pattern_types.png\n');

%% =================================================================
%% SECTION 4: TASK COMPARISON ANALYSIS
%% =================================================================

fprintf('4. Demonstrating task comparison analysis...\n');

% Get available tasks (use first 3 for demo)
availableTasks = loco.tasks(1:min(3, length(loco.tasks)));
fprintf('   Comparing tasks: %s\n', strjoin(availableTasks, ', '));

fig_tasks = figure('Position', [100, 250, 800, 600]);

% Create task comparison using existing method
loco.plotTaskComparison(subject, availableTasks, features, 'SavePath', '');

% Enhance with custom formatting
title(sprintf('Task Comparison - %s', features{1}), 'FontSize', 14, 'FontWeight', 'bold');

exportFigure(gcf, 'demo_task_comparison', 'Format', {'png'});
fprintf('   Task comparison saved as: demo_task_comparison.png\n');

%% =================================================================
%% SECTION 5: POPULATION/GROUP COMPARISON
%% =================================================================

fprintf('5. Demonstrating population analysis...\n');

% Use available subjects (limit to first 3 for demo)
subjects = loco.subjects(1:min(3, length(loco.subjects)));
fprintf('   Analyzing subjects: %s\n', strjoin(subjects, ', '));

fig_population = figure('Position', [100, 300, 800, 600]);

% Create population comparison plot
phaseX = linspace(0, 100, 150);
allData = [];
subjectMeans = [];

hold on;
colors_pop = lines(length(subjects));

for s = 1:length(subjects)
    [data3D, ~] = loco.getCycles(subjects{s}, task, features);
    
    if ~isempty(data3D)
        validMask = loco.validateCycles(subjects{s}, task, features);
        validData = data3D(validMask, :, 1);
        
        if ~isempty(validData)
            subjectMean = mean(validData, 1);
            subjectMeans = [subjectMeans; subjectMean];
            allData = [allData; validData];
            
            plot(phaseX, subjectMean, 'Color', colors_pop(s, :), ...
                 'LineWidth', 2, 'DisplayName', subjects{s});
        end
    end
end

% Add population mean
if ~isempty(allData)
    popMean = mean(allData, 1);
    popStd = std(allData, 0, 1);
    
    % Plot confidence band
    fill([phaseX, fliplr(phaseX)], ...
         [popMean + popStd, fliplr(popMean - popStd)], ...
         [0.8 0.8 0.8], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
    
    plot(phaseX, popMean, 'k-', 'LineWidth', 3, 'DisplayName', 'Population Mean');
end

xlabel('Gait Cycle (%)');
ylabel('Angle (rad)');
title(sprintf('Population Analysis - %s', features{1}));
legend('show', 'Location', 'best');
xlim([0 100]);
grid on;
hold off;

exportFigure(gcf, 'demo_population_analysis', 'Format', {'png'});
fprintf('   Population analysis saved as: demo_population_analysis.png\n');

%% =================================================================
%% SECTION 6: PUBLICATION FIGURE TEMPLATE
%% =================================================================

fprintf('6. Creating publication figure template...\n');

% Create a multi-panel publication figure
fig_pub = figure('Position', [100, 50, 1200, 900]);

% Panel A: Phase patterns
subplot(2, 2, 1);
[data3D, ~] = loco.getCycles(subject, task, features);
if ~isempty(data3D)
    validMask = loco.validateCycles(subject, task, features);
    featData = data3D(:, :, 1);
    validData = featData(validMask, :);
    
    hold on;
    for j = 1:size(validData, 1)
        plot(phaseX, validData(j, :), 'Color', [0.7 0.7 0.7 0.3], 'LineWidth', 0.8);
    end
    if ~isempty(validData)
        meanCurve = mean(validData, 1);
        plot(phaseX, meanCurve, 'b-', 'LineWidth', 2);
    end
    xlabel('Gait Cycle (%)');
    ylabel('Angle (rad)');
    title('A. Individual Cycles');
    xlim([0 100]);
    grid on;
    hold off;
end

% Panel B: Task comparison
subplot(2, 2, 2);
hold on;
for t = 1:min(2, length(availableTasks))
    [data3D, ~] = loco.getCycles(subject, availableTasks{t}, features);
    if ~isempty(data3D)
        validMask = loco.validateCycles(subject, availableTasks{t}, features);
        validData = data3D(validMask, :, 1);
        if ~isempty(validData)
            meanCurve = mean(validData, 1);
            plot(phaseX, meanCurve, 'LineWidth', 2, 'DisplayName', availableTasks{t});
        end
    end
end
xlabel('Gait Cycle (%)');
ylabel('Angle (rad)');
title('B. Task Comparison');
legend('show', 'Location', 'best');
xlim([0 100]);
grid on;
hold off;

% Panel C: Population comparison
subplot(2, 2, 3);
hold on;
for s = 1:length(subjects)
    [data3D, ~] = loco.getCycles(subjects{s}, task, features);
    if ~isempty(data3D)
        validMask = loco.validateCycles(subjects{s}, task, features);
        validData = data3D(validMask, :, 1);
        if ~isempty(validData)
            subjectMean = mean(validData, 1);
            plot(phaseX, subjectMean, 'LineWidth', 2, 'DisplayName', subjects{s});
        end
    end
end
xlabel('Gait Cycle (%)');
ylabel('Angle (rad)');
title('C. Subject Comparison');
legend('show', 'Location', 'best');
xlim([0 100]);
grid on;
hold off;

% Panel D: Statistical summary
subplot(2, 2, 4);
summary = loco.getSummaryStatistics(subject, task, features);
if ~isempty(summary)
    stats = [summary.Mean(1), summary.Std(1), summary.Min(1), summary.Max(1)];
    statLabels = {'Mean', 'Std', 'Min', 'Max'};
    bar(stats);
    set(gca, 'XTickLabel', statLabels);
    ylabel('Value (rad)');
    title('D. Statistical Summary');
    grid on;
else
    text(0.5, 0.5, 'No statistics available', 'HorizontalAlignment', 'center');
end

% Main title
sgtitle(sprintf('Comprehensive Analysis - %s (%s)', features{1}, subject), ...
        'FontSize', 16, 'FontWeight', 'bold');

% Apply consistent formatting
set(findall(fig_pub, 'Type', 'axes'), 'FontSize', 10);

exportFigure(fig_pub, 'demo_publication_figure', 'Format', {'png', 'pdf'});
fprintf('   Publication figure saved as: demo_publication_figure.png/.pdf\n');

%% =================================================================
%% SECTION 7: EXPORT FUNCTIONALITY DEMO
%% =================================================================

fprintf('7. Demonstrating export capabilities...\n');

% Create simple figure for export testing
fig_export = figure('Position', [100, 100, 600, 400]);
plot(phaseX, sin(2*pi*phaseX/100), 'b-', 'LineWidth', 2);
xlabel('Gait Cycle (%)');
ylabel('Normalized Signal');
title('Export Quality Test');
grid on;

% Export in multiple formats
formats = {'png', 'pdf', 'eps'};
for i = 1:length(formats)
    try
        exportFigure(fig_export, sprintf('demo_export_test_%s', formats{i}), ...
                    'Format', {formats{i}}, 'DPI', 300);
        fprintf('   Successfully exported: demo_export_test_%s.%s\n', formats{i}, formats{i});
    catch ME
        fprintf('   Failed to export %s: %s\n', formats{i}, ME.message);
    end
end

%% =================================================================
%% DEMO SUMMARY
%% =================================================================

fprintf('\n=== Demo Complete ===\n');
fprintf('Generated demonstration files:\n');
fprintf('  - demo_themes_comparison.png\n');
fprintf('  - demo_color_palettes.png\n');
fprintf('  - demo_pattern_types.png\n');
fprintf('  - demo_task_comparison.png\n');
fprintf('  - demo_population_analysis.png\n');
fprintf('  - demo_publication_figure.png/.pdf\n');
fprintf('  - demo_export_test_*.png/.pdf/.eps\n\n');

fprintf('Key Features Demonstrated:\n');
fprintf('  ✓ Publication-ready themes (publication, presentation, manuscript)\n');
fprintf('  ✓ Colorblind-friendly palettes (joints, tasks, subjects)\n');
fprintf('  ✓ Multiple plot types (mean, spaghetti, both, ribbon)\n');
fprintf('  ✓ Task comparison visualization\n');
fprintf('  ✓ Population/group analysis\n');
fprintf('  ✓ Multi-panel publication figures\n');
fprintf('  ✓ High-quality export (PNG, PDF, EPS)\n\n');

fprintf('Usage Tips:\n');
fprintf('  - Use plotPhasePatterns_v2() for enhanced phase visualizations\n');
fprintf('  - Use plotTaskComparison_v2() for advanced task comparisons\n');
fprintf('  - Use plotSubjectComparison_v2() for population studies\n');
fprintf('  - Use createPublicationFigure_v2() for complex multi-panel figures\n');
fprintf('  - Use exportFigure_v2() for publication-quality output\n\n');

close all; % Clean up figures

function createSyntheticDemo()
    % Create synthetic data demonstration when real data is not available
    
    fprintf('Creating synthetic data demonstration...\n');
    
    % Generate synthetic gait data
    nCycles = 20;
    nPhases = 150;
    phaseX = linspace(0, 100, nPhases);
    
    % Synthetic knee angle pattern (typical walking)
    basePattern = -0.5 * cos(2*pi*phaseX/100) + 0.3 * cos(4*pi*phaseX/100) + 0.2;
    
    % Add noise and variability
    syntheticData = zeros(nCycles, nPhases);
    for i = 1:nCycles
        noise = 0.1 * randn(1, nPhases);
        amplitude = 0.8 + 0.4 * rand(); % Vary amplitude
        syntheticData(i, :) = amplitude * basePattern + noise;
    end
    
    % Create demonstration plots
    fig_synthetic = figure('Position', [100, 100, 1200, 800]);
    
    % Plot 1: Individual cycles
    subplot(2, 2, 1);
    hold on;
    for i = 1:nCycles
        plot(phaseX, syntheticData(i, :), 'Color', [0.7 0.7 0.7 0.5], 'LineWidth', 0.8);
    end
    meanPattern = mean(syntheticData, 1);
    plot(phaseX, meanPattern, 'b-', 'LineWidth', 3);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Angle (rad)');
    title('Individual Gait Cycles');
    xlim([0 100]);
    grid on;
    hold off;
    
    % Plot 2: Mean with confidence bands
    subplot(2, 2, 2);
    stdPattern = std(syntheticData, 0, 1);
    hold on;
    fill([phaseX, fliplr(phaseX)], ...
         [meanPattern + stdPattern, fliplr(meanPattern - stdPattern)], ...
         [0.7 0.7 0.9], 'FaceAlpha', 0.4, 'EdgeColor', 'none');
    plot(phaseX, meanPattern, 'b-', 'LineWidth', 2);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Angle (rad)');
    title('Mean ± SD Pattern');
    xlim([0 100]);
    grid on;
    hold off;
    
    % Plot 3: Task comparison (simulate different speeds)
    subplot(2, 2, 3);
    tasks = {'Normal', 'Fast', 'Slow'};
    taskData = {syntheticData, ...
                syntheticData * 1.2 + 0.1, ...
                syntheticData * 0.8 - 0.1};
    colors_task = [0.2 0.4 0.8; 0.8 0.2 0.2; 0.2 0.8 0.2];
    
    hold on;
    for t = 1:length(tasks)
        taskMean = mean(taskData{t}, 1);
        plot(phaseX, taskMean, 'Color', colors_task(t, :), ...
             'LineWidth', 2, 'DisplayName', tasks{t});
    end
    xlabel('Gait Cycle (%)');
    ylabel('Knee Angle (rad)');
    title('Task Comparison');
    legend('show', 'Location', 'best');
    xlim([0 100]);
    grid on;
    hold off;
    
    % Plot 4: Color palette demonstration
    subplot(2, 2, 4);
    joints = {'Hip', 'Knee', 'Ankle'};
    joint_colors = [0.89, 0.47, 0.00; 0.12, 0.47, 0.71; 0.17, 0.63, 0.17];
    
    bar(1:3, [0.8, 1.2, 0.6], 'FaceColor', 'flat', 'CData', joint_colors);
    set(gca, 'XTickLabel', joints);
    ylabel('ROM (rad)');
    title('Joint Color Palette');
    grid on;
    
    sgtitle('Biomechanics Visualization System - Synthetic Demo', ...
            'FontSize', 16, 'FontWeight', 'bold');
    
    % Apply theme-like formatting
    set(findall(fig_synthetic, 'Type', 'axes'), 'FontSize', 10);
    
    % Export synthetic demo
    print(fig_synthetic, 'demo_synthetic_visualization.png', '-dpng', '-r300');
    
    fprintf('Synthetic demo saved as: demo_synthetic_visualization.png\n');
    fprintf('\nSynthetic Demo Features:\n');
    fprintf('  ✓ Individual cycle visualization\n');
    fprintf('  ✓ Statistical confidence bands\n');
    fprintf('  ✓ Multi-task comparison\n');
    fprintf('  ✓ Colorblind-friendly palettes\n');
    fprintf('  ✓ Publication-ready formatting\n\n');
    
    fprintf('To use with real data:\n');
    fprintf('  1. Load your parquet file: loco = LocomotionData(''your_data.parquet'');\n');
    fprintf('  2. Use enhanced plotting: loco.plotPhasePatterns_v2(subject, task, features);\n');
    fprintf('  3. Export with: loco.exportFigure_v2(fig, ''filename'', ''Format'', {{''png'', ''pdf''}});\n\n');
end