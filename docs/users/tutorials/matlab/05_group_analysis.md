# Tutorial 5: Group Analysis

## Overview

Learn to aggregate biomechanical data across multiple subjects, compute group statistics, and perform population-level analyses.

## Learning Objectives

- Aggregate data across subjects
- Compute ensemble averages with confidence intervals
- Handle missing data appropriately  
- Perform statistical comparisons between groups
- Create normative reference data

## Setup

=== "Using Library"
    ```matlab
    % Add library to path
    addpath('user_libs/matlab');
    
    % Load data
    loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');
    
    % Get all subjects
    allSubjects = loco.getSubjects();
    fprintf('Total subjects: %d\n', length(allSubjects));
    ```

=== "Using Raw Data"
    ```matlab
    % Add helper functions to path
    addpath('user_libs/matlab');
    
    % Load data
    data = parquetread('converted_datasets/umich_2021_phase.parquet');
    
    % Get all subjects
    allSubjects = unique(data.subject);
    fprintf('Total subjects: %d\n', length(allSubjects));
    ```

## Multi-Subject Aggregation

### Computing Group Means

=== "Using Library"
    ```matlab
    % Aggregate data across all subjects for level walking
    task = 'level_walking';
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    % Initialize storage for all subjects
    allSubjectMeans = [];
    allSubjectStds = [];
    subjectCount = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        
        % Filter data for this subject and task
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            % Get mean patterns for this subject
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            stdPatterns = subjectData.getStdPatterns(subject, task);
            
            % Store subject data
            if subjectCount == 0
                % Initialize arrays
                nFeatures = length(features);
                nPoints = 150;
                allSubjectMeans = NaN(length(allSubjects), nPoints, nFeatures);
                allSubjectStds = NaN(length(allSubjects), nPoints, nFeatures);
            end
            
            subjectCount = subjectCount + 1;
            
            for f = 1:length(features)
                feature = features{f};
                if isfield(meanPatterns, feature)
                    allSubjectMeans(subjectCount, :, f) = meanPatterns.(feature);
                    allSubjectStds(subjectCount, :, f) = stdPatterns.(feature);
                end
            end
        end
    end
    
    fprintf('Successfully processed %d subjects\n', subjectCount);
    ```

=== "Using Raw Data"
    ```matlab
    % Using aggregateSubjects helper function
    task = 'level_walking';
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    % Aggregate knee flexion data
    kneeAgg = aggregateSubjects(data, allSubjects, task, features{1});
    
    % Or manually aggregate
    allSubjectMeans = [];
    allSubjectStds = [];
    subjectCount = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        
        % Filter data for this subject and task
        subjectData = data(strcmp(data.subject, subject) & ...
                          strcmp(data.task, task), :);
        
        if height(subjectData) > 0
            % Store subject data
            if subjectCount == 0
                % Initialize arrays
                nFeatures = length(features);
                nPoints = 150;
                allSubjectMeans = NaN(length(allSubjects), nPoints, nFeatures);
                allSubjectStds = NaN(length(allSubjects), nPoints, nFeatures);
            end
            
            subjectCount = subjectCount + 1;
            
            for f = 1:length(features)
                feature = features{f};
                if ismember(feature, subjectData.Properties.VariableNames)
                    [meanCurve, stdCurve] = computePhaseAverage(subjectData, feature);
                    allSubjectMeans(subjectCount, :, f) = meanCurve;
                    allSubjectStds(subjectCount, :, f) = stdCurve;
                end
            end
        end
    end
    
    fprintf('Successfully processed %d subjects\n', subjectCount);
    ```

### Ensemble Averages

```matlab
% Compute ensemble averages across subjects
phase = 0:100/149:100;

figure('Position', [100 100 1200 600]);

for f = 1:length(features)
    subplot(1, length(features), f);
    
    % Get data for this feature
    featureData = squeeze(allSubjectMeans(1:subjectCount, :, f));
    
    % Compute ensemble statistics
    ensembleMean = mean(featureData, 1, 'omitnan');
    ensembleStd = std(featureData, 0, 1, 'omitnan');
    ensembleSEM = ensembleStd / sqrt(subjectCount);
    
    % Convert to degrees if angle
    if contains(features{f}, 'angle')
        ensembleMean = rad2deg(ensembleMean);
        ensembleStd = rad2deg(ensembleStd);
        ensembleSEM = rad2deg(ensembleSEM);
        unitLabel = '(deg)';
    else
        unitLabel = '';
    end
    
    % Plot ensemble mean ± SEM
    hold on;
    fill([phase, fliplr(phase)], ...
         [ensembleMean + ensembleSEM, fliplr(ensembleMean - ensembleSEM)], ...
         [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
    
    plot(phase, ensembleMean, 'b-', 'LineWidth', 2);
    
    xlabel('Gait Cycle (%)');
    ylabel(sprintf('%s %s', strrep(features{f}, '_', ' '), unitLabel));
    title(sprintf('Group Mean (n=%d)', subjectCount));
    grid on;
    xlim([0 100]);
end

sgtitle(sprintf('Ensemble Averages - %s', strrep(task, '_', ' ')));
```

## Statistical Analysis

### Group Comparisons

```matlab
% Compare two groups (example: young vs old, or healthy vs pathological)
% For demonstration, split subjects into two groups randomly

group1Subjects = allSubjects(1:floor(length(allSubjects)/2));
group2Subjects = allSubjects(floor(length(allSubjects)/2)+1:end);

fprintf('Group 1: %d subjects\n', length(group1Subjects));
fprintf('Group 2: %d subjects\n', length(group2Subjects));

% Function to get group data
function groupData = getGroupData(loco, subjects, task, features)
    groupData = [];
    validCount = 0;
    
    for i = 1:length(subjects)
        subject = subjects{i};
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            validCount = validCount + 1;
            
            if validCount == 1
                nFeatures = length(features);
                nPoints = 150;
                groupData = NaN(length(subjects), nPoints, nFeatures);
            end
            
            for f = 1:length(features)
                feature = features{f};
                if isfield(meanPatterns, feature)
                    groupData(validCount, :, f) = meanPatterns.(feature);
                end
            end
        end
    end
    
    % Trim to valid data
    groupData = groupData(1:validCount, :, :);
end

% Get data for both groups
group1Data = getGroupData(loco, group1Subjects, task, features);
group2Data = getGroupData(loco, group2Subjects, task, features);

% Statistical comparison at each phase point
feature = features{1};  % Knee flexion
f = 1;

group1Feature = squeeze(group1Data(:, :, f));
group2Feature = squeeze(group2Data(:, :, f));

% Perform t-tests at each phase point
pValues = zeros(1, 150);
for p = 1:150
    g1_vals = group1Feature(:, p);
    g2_vals = group2Feature(:, p);
    
    % Remove NaN values
    g1_clean = g1_vals(~isnan(g1_vals));
    g2_clean = g2_vals(~isnan(g2_vals));
    
    if length(g1_clean) > 1 && length(g2_clean) > 1
        [~, pValues(p)] = ttest2(g1_clean, g2_clean);
    else
        pValues(p) = NaN;
    end
end

% Plot comparison
figure();
subplot(2, 1, 1);
hold on;

% Group 1
g1Mean = mean(group1Feature, 1, 'omitnan');
g1SEM = std(group1Feature, 0, 1, 'omitnan') / sqrt(size(group1Feature, 1));
fill([phase, fliplr(phase)], ...
     rad2deg([g1Mean + g1SEM, fliplr(g1Mean - g1SEM)]), ...
     [1 0.7 0.7], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
plot(phase, rad2deg(g1Mean), 'r-', 'LineWidth', 2, 'DisplayName', 'Group 1');

% Group 2  
g2Mean = mean(group2Feature, 1, 'omitnan');
g2SEM = std(group2Feature, 0, 1, 'omitnan') / sqrt(size(group2Feature, 1));
fill([phase, fliplr(phase)], ...
     rad2deg([g2Mean + g2SEM, fliplr(g2Mean - g2SEM)]), ...
     [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
plot(phase, rad2deg(g2Mean), 'b-', 'LineWidth', 2, 'DisplayName', 'Group 2');

xlabel('Gait Cycle (%)');
ylabel('Knee Flexion (deg)');
title('Group Comparison');
legend('show');
grid on;

% P-values plot
subplot(2, 1, 2);
plot(phase, pValues, 'k-', 'LineWidth', 1.5);
yline(0.05, 'r--', 'α = 0.05');
xlabel('Gait Cycle (%)');
ylabel('p-value');
title('Statistical Significance');
ylim([0 1]);
grid on;
```

## Normative Data Creation

### Reference Ranges

```matlab
% Create normative reference ranges (mean ± 2SD)
feature = features{1};
f = 1;

% Use all subjects as normative population
normativeData = squeeze(allSubjectMeans(1:subjectCount, :, f));

% Compute reference ranges
normMean = mean(normativeData, 1, 'omitnan');
normStd = std(normativeData, 0, 1, 'omitnan');

% Reference ranges (mean ± 2SD)
upperBound = normMean + 2 * normStd;
lowerBound = normMean - 2 * normStd;

% Convert to degrees
normMeanDeg = rad2deg(normMean);
upperBoundDeg = rad2deg(upperBound);
lowerBoundDeg = rad2deg(lowerBound);

% Plot normative ranges
figure();
hold on;

% Reference band
fill([phase, fliplr(phase)], [upperBoundDeg, fliplr(lowerBoundDeg)], ...
     [0.9 0.9 0.9], 'EdgeColor', 'none', 'DisplayName', 'Normal Range (±2SD)');

% Mean line
plot(phase, normMeanDeg, 'k-', 'LineWidth', 2, 'DisplayName', 'Normal Mean');

% Boundary lines
plot(phase, upperBoundDeg, 'k--', 'LineWidth', 1, 'DisplayName', 'Upper/Lower Bounds');
plot(phase, lowerBoundDeg, 'k--', 'LineWidth', 1);

xlabel('Gait Cycle (%)');
ylabel('Knee Flexion (deg)');
title(sprintf('Normative Reference Data (n=%d)', subjectCount));
legend('show');
grid on;
xlim([0 100]);

% Save normative data
normativeTable = table(phase', normMeanDeg', upperBoundDeg', lowerBoundDeg', ...
    'VariableNames', {'phase_percent', 'mean', 'upper_bound', 'lower_bound'});

% Display summary
fprintf('\nNormative Data Summary:\n');
fprintf('======================\n');
fprintf('Feature: %s\n', feature);
fprintf('Population size: %d subjects\n', subjectCount);
fprintf('Peak flexion: %.1f ± %.1f deg\n', max(normMeanDeg), std(max(normativeData, [], 2), 'omitnan') * 180/pi);
fprintf('Range of motion: %.1f ± %.1f deg\n', ...
        mean(max(normativeData, [], 2) - min(normativeData, [], 2)) * 180/pi, ...
        std(max(normativeData, [], 2) - min(normativeData, [], 2)) * 180/pi);
```

## Best Practices

### Handling Missing Data
```matlab
% Check data completeness across subjects
fprintf('Data Completeness Report:\n');
fprintf('========================\n');

for i = 1:length(allSubjects)
    subject = allSubjects{i};
    subjectData = loco.filterSubject(subject).filterTask(task);
    
    if subjectData.length() > 0
        % Check for missing features
        meanPatterns = subjectData.getMeanPatterns(subject, task);
        availableFeatures = fieldnames(meanPatterns);
        
        missingFeatures = setdiff(features, availableFeatures);
        if ~isempty(missingFeatures)
            fprintf('%s: Missing %s\n', subject, strjoin(missingFeatures, ', '));
        end
    else
        fprintf('%s: No %s data\n', subject, task);
    end
end
```

### Statistical Power Analysis
```matlab
% Estimate required sample size for group comparisons
effect_size = 0.5;  % Cohen's d
alpha = 0.05;
power = 0.8;

% Approximate sample size calculation (per group)
% This is a simplified calculation - use proper power analysis tools for research
z_alpha = norminv(1 - alpha/2);
z_beta = norminv(power);
n_approx = 2 * ((z_alpha + z_beta) / effect_size)^2;

fprintf('\nPower Analysis (Approximate):\n');
fprintf('============================\n');
fprintf('Effect size (Cohen''s d): %.1f\n', effect_size);
fprintf('Alpha level: %.2f\n', alpha);
fprintf('Power: %.1f%%\n', power * 100);
fprintf('Estimated sample size per group: %.0f\n', ceil(n_approx));
fprintf('Current group sizes: %d, %d\n', size(group1Data, 1), size(group2Data, 1));
```

## Summary

You've learned to perform group-level biomechanical analysis in MATLAB:

- **Multi-subject aggregation** with proper data handling
- **Ensemble averaging** with confidence intervals
- **Statistical comparisons** between groups
- **Normative reference data** creation
- **Quality assessment** and missing data handling

## Next Steps

[Continue to Tutorial 6: Publication Outputs →](06_publication_outputs.md)

Learn to create publication-ready figures, tables, and ensure reproducibility of your analyses.