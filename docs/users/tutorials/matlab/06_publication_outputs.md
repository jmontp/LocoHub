# Tutorial 6: Publication Outputs

## Overview

Learn to create publication-ready figures, tables, and reproducible analysis reports from your biomechanical data.

## Learning Objectives

- Create multi-panel figures with consistent formatting
- Generate publication-ready tables with statistics
- Apply journal-specific formatting requirements
- Ensure reproducibility of analyses
- Prepare data for sharing and archiving

## Setup

```matlab
% Add library to path
addpath('user_libs/matlab');

% Load data
loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');

% Set publication style
loco.setPublicationStyle('biomechanics');
```

## Multi-Panel Figures

### Creating Figure Layouts

```matlab
% Create a comprehensive multi-panel figure
subjects = {'SUB01', 'SUB02', 'SUB03'};
tasks = {'level_walking', 'incline_walking', 'decline_walking'};
features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};

% Create figure with specific dimensions for journal
fig = figure('Position', [100 100 1200 900], 'Color', 'white');
fig.PaperUnits = 'inches';
fig.PaperPosition = [0 0 12 9];

% Set up subplot grid (3 subjects × 2 features)
nRows = length(subjects);
nCols = length(features);
phase = 0:100/149:100;

for s = 1:length(subjects)
    subject = subjects{s};
    
    for f = 1:length(features)
        feature = features{f};
        
        subplot(nRows, nCols, (s-1)*nCols + f);
        hold on;
        
        % Plot each task with different colors
        colors = {[0 0.4 0.8], [0.8 0.4 0], [0.8 0 0.4]};
        
        for t = 1:length(tasks)
            task = tasks{t};
            taskData = loco.filterSubject(subject).filterTask(task);
            
            if taskData.length() > 0
                % Get mean pattern
                meanPatterns = taskData.getMeanPatterns(subject, task);
                stdPatterns = taskData.getStdPatterns(subject, task);
                
                if isfield(meanPatterns, feature)
                    meanCurve = meanPatterns.(feature);
                    stdCurve = stdPatterns.(feature);
                    
                    % Convert to degrees if angle
                    if contains(feature, 'angle')
                        meanCurve = rad2deg(meanCurve);
                        stdCurve = rad2deg(stdCurve);
                        yLabel = 'Angle (deg)';
                    else
                        yLabel = strrep(feature, '_', ' ');
                    end
                    
                    % Plot with confidence band
                    fill([phase, fliplr(phase)], ...
                         [meanCurve + stdCurve, fliplr(meanCurve - stdCurve)]', ...
                         colors{t}, 'FaceAlpha', 0.2, 'EdgeColor', 'none');
                    
                    plot(phase, meanCurve, 'Color', colors{t}, 'LineWidth', 2, ...
                         'DisplayName', strrep(task, '_', ' '));
                end
            end
        end
        
        % Format subplot
        xlabel('Gait Cycle (%)');
        ylabel(yLabel);
        
        if s == 1 && f == 1
            legend('Location', 'best', 'FontSize', 8);
        end
        
        % Add subject label and feature title
        if f == 1
            title(sprintf('%s - %s', subject, strrep(feature, '_', ' ')), ...
                  'FontSize', 10, 'FontWeight', 'bold');
        else
            title(strrep(feature, '_', ' '), 'FontSize', 10, 'FontWeight', 'bold');
        end
        
        grid on;
        xlim([0 100]);
        
        % Set consistent y-axis limits for comparison
        if contains(feature, 'knee')
            ylim([-10 70]);
        elseif contains(feature, 'hip')
            ylim([-20 40]);
        end
    end
end

% Add overall title
sgtitle('Joint Kinematics Across Walking Conditions', ...
        'FontSize', 14, 'FontWeight', 'bold');

% Save in multiple formats
print(fig, 'joint_kinematics_comparison', '-dpng', '-r300');
print(fig, 'joint_kinematics_comparison', '-depsc', '-r300');
savefig(fig, 'joint_kinematics_comparison.fig');
```

### Statistical Summary Figures

```matlab
% Create a figure showing group statistics
allSubjects = loco.getSubjects();
task = 'level_walking';
feature = 'knee_flexion_angle_ipsi_rad';

% Collect ROM data across subjects
romData = [];
subjectLabels = {};

for i = 1:min(10, length(allSubjects))  % Limit to first 10 subjects
    subject = allSubjects{i};
    subjectData = loco.filterSubject(subject).filterTask(task);
    
    if subjectData.length() > 0
        romResult = subjectData.calculateROM(subject, task, {feature}, true);
        
        if isfield(romResult, feature)
            romData(end+1) = rad2deg(mean(romResult.(feature), 'omitnan'));
            subjectLabels{end+1} = subject;
        end
    end
end

% Create publication-quality bar plot
fig = figure('Position', [100 100 800 600], 'Color', 'white');

% Bar plot with error bars
meanROM = mean(romData);
stdROM = std(romData);
semROM = stdROM / sqrt(length(romData));

bar(1, meanROM, 'FaceColor', [0.6 0.6 0.8], 'EdgeColor', 'black');
hold on;
errorbar(1, meanROM, semROM, 'k-', 'LineWidth', 2, 'CapSize', 10);

% Add individual data points
scatter(ones(size(romData)) + 0.1*randn(size(romData)), romData, ...
        50, 'filled', 'MarkerFaceColor', [0.2 0.2 0.8], ...
        'MarkerFaceAlpha', 0.6, 'MarkerEdgeColor', 'black');

% Format
xlim([0.5 1.5]);
set(gca, 'XTick', 1, 'XTickLabel', {'Knee Flexion ROM'});
ylabel('Range of Motion (deg)', 'FontSize', 12);
title(sprintf('Knee Flexion ROM - %s (n=%d)', strrep(task, '_', ' '), length(romData)), ...
      'FontSize', 14, 'FontWeight', 'bold');

% Add statistics text
text(1, max(romData)*0.9, sprintf('Mean ± SEM\n%.1f ± %.1f°', meanROM, semROM), ...
     'HorizontalAlignment', 'center', 'FontSize', 10, ...
     'BackgroundColor', 'white', 'EdgeColor', 'black');

grid on;

% Save figure
print(fig, 'knee_rom_statistics', '-dpng', '-r300');
print(fig, 'knee_rom_statistics', '-depsc', '-r300');
```

## Publication Tables

### Demographic and Clinical Characteristics

```matlab
% Create demographic table (example with mock data)
fprintf('Creating demographic table...\n');

% Mock demographic data structure
demographics = struct();
demographics.subjects = allSubjects(1:min(20, length(allSubjects)));
demographics.age = 25 + 30*rand(length(demographics.subjects), 1);  % Age 25-55
demographics.height = 1.6 + 0.3*rand(length(demographics.subjects), 1);  % Height 1.6-1.9m
demographics.mass = 60 + 30*rand(length(demographics.subjects), 1);  % Mass 60-90kg
demographics.sex = repmat({'M'; 'F'}, ceil(length(demographics.subjects)/2), 1);
demographics.sex = demographics.sex(1:length(demographics.subjects));

% Create and save demographic table
demoTable = table(demographics.subjects, demographics.age, demographics.height, ...
                  demographics.mass, demographics.sex, ...
                  'VariableNames', {'Subject', 'Age_years', 'Height_m', 'Mass_kg', 'Sex'});

% Calculate summary statistics
fprintf('\nDemographic Characteristics (n=%d):\n', height(demoTable));
fprintf('=========================================\n');
fprintf('Age: %.1f ± %.1f years (range: %.1f - %.1f)\n', ...
        mean(demoTable.Age_years), std(demoTable.Age_years), ...
        min(demoTable.Age_years), max(demoTable.Age_years));
fprintf('Height: %.2f ± %.2f m (range: %.2f - %.2f)\n', ...
        mean(demoTable.Height_m), std(demoTable.Height_m), ...
        min(demoTable.Height_m), max(demoTable.Height_m));
fprintf('Mass: %.1f ± %.1f kg (range: %.1f - %.1f)\n', ...
        mean(demoTable.Mass_kg), std(demoTable.Mass_kg), ...
        min(demoTable.Mass_kg), max(demoTable.Mass_kg));
fprintf('Sex: %d Male, %d Female\n', ...
        sum(strcmp(demoTable.Sex, 'M')), sum(strcmp(demoTable.Sex, 'F')));

% Export to CSV for manuscript
writetable(demoTable, 'demographic_table.csv');
```

### Biomechanical Results Table

```matlab
% Create comprehensive results table
tasks = {'level_walking', 'incline_walking', 'decline_walking'};
features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad'};

% Initialize results structure
results = struct();
results.Task = {};
results.Variable = {};
results.Mean = [];
results.StdDev = [];
results.Min = [];
results.Max = [];
results.SampleSize = [];

rowCount = 0;

for t = 1:length(tasks)
    task = tasks{t};
    
    for f = 1:length(features)
        feature = features{f};
        
        % Collect data across subjects
        subjectValues = [];
        
        for s = 1:min(10, length(allSubjects))  % Limit subjects for demo
            subject = allSubjects{s};
            subjectData = loco.filterSubject(subject).filterTask(task);
            
            if subjectData.length() > 0
                romResult = subjectData.calculateROM(subject, task, {feature}, true);
                
                if isfield(romResult, feature)
                    subjectValues(end+1) = mean(romResult.(feature), 'omitnan');
                end
            end
        end
        
        if ~isempty(subjectValues)
            rowCount = rowCount + 1;
            
            % Convert to degrees if angle
            if contains(feature, 'angle')
                subjectValues = rad2deg(subjectValues);
                units = '(deg)';
            else
                units = '';
            end
            
            results.Task{rowCount} = strrep(task, '_', ' ');
            results.Variable{rowCount} = [strrep(feature, '_', ' '), ' ROM ', units];
            results.Mean(rowCount) = mean(subjectValues);
            results.StdDev(rowCount) = std(subjectValues);
            results.Min(rowCount) = min(subjectValues);
            results.Max(rowCount) = max(subjectValues);
            results.SampleSize(rowCount) = length(subjectValues);
        end
    end
end

% Create table
resultsTable = struct2table(results);

% Display formatted table
fprintf('\nBiomechanical Results Summary:\n');
fprintf('==============================\n');
for i = 1:height(resultsTable)
    fprintf('%-15s %-30s %6.1f ± %4.1f (%4.1f - %4.1f) [n=%d]\n', ...
            resultsTable.Task{i}, resultsTable.Variable{i}, ...
            resultsTable.Mean(i), resultsTable.StdDev(i), ...
            resultsTable.Min(i), resultsTable.Max(i), ...
            resultsTable.SampleSize(i));
end

% Export to CSV
writetable(resultsTable, 'biomechanical_results_table.csv');

% Create formatted table for LaTeX
fid = fopen('results_table_latex.txt', 'w');
fprintf(fid, '\\begin{table}[ht]\n');
fprintf(fid, '\\centering\n');
fprintf(fid, '\\caption{Biomechanical Results Summary}\n');
fprintf(fid, '\\begin{tabular}{lllc}\n');
fprintf(fid, '\\hline\n');
fprintf(fid, 'Task & Variable & Mean ± SD & n \\\\\n');
fprintf(fid, '\\hline\n');

for i = 1:height(resultsTable)
    fprintf(fid, '%s & %s & %.1f ± %.1f & %d \\\\\n', ...
            resultsTable.Task{i}, resultsTable.Variable{i}, ...
            resultsTable.Mean(i), resultsTable.StdDev(i), ...
            resultsTable.SampleSize(i));
end

fprintf(fid, '\\hline\n');
fprintf(fid, '\\end{tabular}\n');
fprintf(fid, '\\end{table}\n');
fclose(fid);

fprintf('\nLaTeX table saved to: results_table_latex.txt\n');
```

## Data Archiving and Sharing

### Preparing Supplementary Data

```matlab
% Create supplementary data package for publication
fprintf('Creating supplementary data package...\n');

% Create directory structure
if ~exist('supplementary_data', 'dir')
    mkdir('supplementary_data');
end

% 1. Subject-level mean patterns
mkdir('supplementary_data/subject_mean_patterns');

task = 'level_walking';
features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};

for s = 1:min(5, length(allSubjects))  % Limit for demo
    subject = allSubjects{s};
    subjectData = loco.filterSubject(subject).filterTask(task);
    
    if subjectData.length() > 0
        meanPatterns = subjectData.getMeanPatterns(subject, task);
        
        % Create table with phase and mean patterns
        phase = (0:100/149:100)';
        subjectTable = table(phase, 'VariableNames', {'phase_percent'});
        
        for f = 1:length(features)
            feature = features{f};
            if isfield(meanPatterns, feature)
                % Convert angles to degrees
                if contains(feature, 'angle')
                    values = rad2deg(meanPatterns.(feature));
                    colName = strrep(feature, 'rad', 'deg');
                else
                    values = meanPatterns.(feature);
                    colName = feature;
                end
                
                subjectTable.(colName) = values;
            end
        end
        
        % Save subject data
        filename = sprintf('supplementary_data/subject_mean_patterns/%s_%s.csv', ...
                          subject, task);
        writetable(subjectTable, filename);
    end
end

% 2. Group summary statistics
groupSummary = struct();
groupSummary.task = task;
groupSummary.n_subjects = subjectCount;
groupSummary.features = features;

% Save group summary
save('supplementary_data/group_summary.mat', 'groupSummary');

% 3. Analysis parameters
analysisParams = struct();
analysisParams.data_file = 'converted_datasets/umich_2021_phase.parquet';
analysisParams.analysis_date = datestr(now);
analysisParams.matlab_version = version;
analysisParams.points_per_cycle = 150;
analysisParams.tasks_analyzed = tasks;
analysisParams.features_analyzed = features;

% Save parameters
save('supplementary_data/analysis_parameters.mat', 'analysisParams');

% Create README file
fid = fopen('supplementary_data/README.txt', 'w');
fprintf(fid, 'Supplementary Data Package\n');
fprintf(fid, '==========================\n\n');
fprintf(fid, 'Analysis Date: %s\n', datestr(now));
fprintf(fid, 'MATLAB Version: %s\n\n', version);
fprintf(fid, 'Contents:\n');
fprintf(fid, '---------\n');
fprintf(fid, 'subject_mean_patterns/ : Individual subject mean patterns (CSV format)\n');
fprintf(fid, 'group_summary.mat      : Group-level summary statistics\n');
fprintf(fid, 'analysis_parameters.mat: Analysis parameters and settings\n');
fprintf(fid, 'README.txt            : This file\n\n');
fprintf(fid, 'Data Format:\n');
fprintf(fid, '------------\n');
fprintf(fid, 'Phase data normalized to 150 points per gait cycle (0-100%%)\n');
fprintf(fid, 'Angular data converted from radians to degrees\n');
fprintf(fid, 'Missing values represented as NaN\n\n');
fprintf(fid, 'Contact: [Author email]\n');
fclose(fid);

fprintf('Supplementary data package created in: supplementary_data/\n');
```

## Journal-Specific Formatting

### Apply Journal Styles

```matlab
% Function to apply different journal styles
function applyJournalStyle(journalName)
    switch lower(journalName)
        case 'jbiomech'
            % Journal of Biomechanics style
            set(groot, 'DefaultAxesFontSize', 12);
            set(groot, 'DefaultAxesFontName', 'Arial');
            set(groot, 'DefaultTextFontSize', 12);
            set(groot, 'DefaultLineLineWidth', 1.5);
            set(groot, 'DefaultFigureColor', 'white');
            
        case 'gaitposture'
            % Gait & Posture style
            set(groot, 'DefaultAxesFontSize', 10);
            set(groot, 'DefaultAxesFontName', 'Times');
            set(groot, 'DefaultTextFontSize', 10);
            set(groot, 'DefaultLineLineWidth', 1.2);
            
        case 'ieee'
            % IEEE Transactions style
            set(groot, 'DefaultAxesFontSize', 9);
            set(groot, 'DefaultAxesFontName', 'Times');
            set(groot, 'DefaultTextFontSize', 9);
            set(groot, 'DefaultLineLineWidth', 1);
    end
end

% Example: Create figure in Journal of Biomechanics style
applyJournalStyle('jbiomech');

fig = figure('Position', [100 100 800 600]);
% ... create your figure ...

% Save with journal specifications
print(fig, 'figure_jbiomech_style', '-dpng', '-r600');  % High resolution for submission
```

## Reproducibility Checklist

```matlab
% Create reproducibility report
function generateReproducibilityReport()
    fid = fopen('reproducibility_report.txt', 'w');
    
    fprintf(fid, 'Reproducibility Report\n');
    fprintf(fid, '======================\n\n');
    
    % System information
    fprintf(fid, 'System Information:\n');
    fprintf(fid, '-------------------\n');
    fprintf(fid, 'MATLAB Version: %s\n', version);
    fprintf(fid, 'Operating System: %s\n', computer);
    fprintf(fid, 'Analysis Date: %s\n\n', datestr(now));
    
    % Data information
    fprintf(fid, 'Data Information:\n');
    fprintf(fid, '-----------------\n');
    fprintf(fid, 'Dataset: converted_datasets/umich_2021_phase.parquet\n');
    fprintf(fid, 'Data Structure: Phase-indexed (150 points per cycle)\n');
    fprintf(fid, 'Units: Angles in radians, converted to degrees for display\n\n');
    
    % Analysis parameters
    fprintf(fid, 'Analysis Parameters:\n');
    fprintf(fid, '--------------------\n');
    fprintf(fid, 'Statistical tests: Two-sample t-tests\n');
    fprintf(fid, 'Significance level: α = 0.05\n');
    fprintf(fid, 'Missing data handling: Excluded from calculations\n');
    fprintf(fid, 'Outlier detection: Not applied\n\n');
    
    % Code availability
    fprintf(fid, 'Code Availability:\n');
    fprintf(fid, '------------------\n');
    fprintf(fid, 'Analysis scripts: Available upon request\n');
    fprintf(fid, 'LocomotionData library: Open source\n');
    fprintf(fid, 'Tutorial code: docs/users/tutorials/matlab/\n\n');
    
    fclose(fid);
    
    fprintf('Reproducibility report saved to: reproducibility_report.txt\n');
end

generateReproducibilityReport();
```

## Best Practices Summary

### Figure Quality Guidelines
```matlab
% Guidelines for publication-quality figures
fprintf('Publication Figure Guidelines:\n');
fprintf('==============================\n');
fprintf('✓ Use vector formats (EPS, SVG) for line plots\n');
fprintf('✓ Use high resolution (≥300 DPI) for raster images\n');
fprintf('✓ Ensure readable font sizes (≥8pt for small text)\n');
fprintf('✓ Use colorblind-friendly color schemes\n');
fprintf('✓ Include proper axis labels with units\n');
fprintf('✓ Add statistical annotations where appropriate\n');
fprintf('✓ Use consistent styling across all figures\n');
fprintf('✓ Test figures at final print size\n');
```

### Data Sharing Standards
```matlab
% Data sharing best practices
fprintf('\nData Sharing Guidelines:\n');
fprintf('========================\n');
fprintf('✓ Provide processed data in standard formats (CSV, MAT)\n');
fprintf('✓ Include detailed metadata and variable descriptions\n');
fprintf('✓ Document all preprocessing and analysis steps\n');
fprintf('✓ Use persistent identifiers (DOI) for datasets\n');
fprintf('✓ Follow FAIR data principles (Findable, Accessible, Interoperable, Reusable)\n');
fprintf('✓ Include analysis code with sufficient documentation\n');
fprintf('✓ Specify software versions and dependencies\n');
```

## Summary

You've learned to create professional publication outputs in MATLAB:

- **Multi-panel figures** with journal-quality formatting
- **Statistical summary tables** with comprehensive metrics
- **Data archiving packages** for reproducible research
- **Journal-specific styling** for different publication venues
- **Reproducibility documentation** following best practices

## Additional Resources

### Further Learning
- [API Reference](../../api/locomotion-data-api.md) - Detailed function documentation
- [Dataset Documentation](../../../reference/datasets_documentation/) - Available datasets
- [Contributing Guide](../../../contributing/) - Add your own datasets
- [GitHub Repository](https://github.com/your-repo) - Source code and examples

### MATLAB Community
- [MATLAB Central](https://www.mathworks.com/matlabcentral/) - File Exchange and community
- [Biomechanics Analysis Toolkit](https://www.biomechanist.net/) - Specialized tools
- [OpenSim Community](https://opensim.stanford.edu/community) - Related biomechanics software

This completes the MATLAB tutorial series. You now have comprehensive tools for biomechanical data analysis from loading through publication!

Happy analyzing! 🎉