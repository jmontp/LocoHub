# Tutorial 4: Cycle Analysis

## Overview

Learn to analyze individual gait cycles, calculate biomechanical metrics, and identify patterns and outliers in your data.

## Learning Objectives

- Extract and analyze individual gait cycles
- Calculate range of motion and peak values  
- Perform bilateral comparisons
- Detect outlier cycles
- Extract cycle-by-cycle features for statistical analysis

## Setup

=== "Using Library"
    ```matlab
    % Add library to path
    addpath('user_libs/matlab');
    
    % Load data
    loco = LocomotionData('converted_datasets/umich_2021_phase.parquet');
    
    % Filter for analysis
    subjectData = loco.filterTask('level_walking').filterSubject('SUB01');
    ```

=== "Using Raw Data"
    ```matlab
    % Load data directly
    data = parquetread('converted_datasets/umich_2021_phase.parquet');
    
    % Filter for analysis  
    subjectData = data(strcmp(data.subject, 'SUB01') & ...
                      strcmp(data.task, 'level_walking'), :);
    ```

## Extracting Individual Cycles

### Getting 3D Cycle Arrays

=== "Using Library"
    ```matlab
    % Extract cycles as 3D array [cycles × points × features]
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    [data3D, featureNames] = subjectData.getCycles('SUB01', 'level_walking', features);
    
    fprintf('Data shape: %d cycles × %d points × %d features\n', size(data3D));
    fprintf('Features: %s\n', strjoin(featureNames, ', '));
    ```

=== "Using Raw Data"
    ```matlab
    function [data3D, featureNames] = extractCycles(data, features)
        % Extract cycles into 3D array
        
        uniqueCycles = unique(data.cycle_id);
        nCycles = length(uniqueCycles);
        nPoints = 150;  % Phase data has 150 points per cycle
        nFeatures = length(features);
        
        data3D = NaN(nCycles, nPoints, nFeatures);
        
        for c = 1:nCycles
            cycleData = data(data.cycle_id == uniqueCycles(c), :);
            
            if height(cycleData) == nPoints
                for f = 1:nFeatures
                    if any(strcmp(cycleData.Properties.VariableNames, features{f}))
                        data3D(c, :, f) = cycleData.(features{f});
                    end
                end
            end
        end
        
        featureNames = features;
    end
    
    % Extract cycles
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    [data3D, featureNames] = extractCycles(subjectData, features);
    
    fprintf('Data shape: %d cycles × %d points × %d features\n', size(data3D));
    ```

### Analyzing Individual Cycles

=== "Using Library"
    ```matlab
    % Get knee flexion data for first feature
    kneeData = squeeze(data3D(:, :, 1));  % [cycles × points]
    
    % Plot first few cycles
    phase = 0:100/149:100;
    
    figure();
    hold on;
    for i = 1:min(5, size(kneeData, 1))
        plot(phase, rad2deg(kneeData(i, :)), 'LineWidth', 1.5, ...
             'DisplayName', sprintf('Cycle %d', i));
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Individual Gait Cycles');
    legend('show');
    grid on;
    ```

=== "Using Raw Data"
    ```matlab
    % Manual cycle extraction and plotting
    uniqueCycles = unique(subjectData.cycle_id);
    phase = 0:100/149:100;
    
    figure();
    hold on;
    for i = 1:min(5, length(uniqueCycles))
        cycleData = subjectData(subjectData.cycle_id == uniqueCycles(i), :);
        
        if height(cycleData) == 150
            kneeAngle = cycleData.knee_flexion_angle_ipsi_rad;
            plot(phase, rad2deg(kneeAngle), 'LineWidth', 1.5, ...
                 'DisplayName', sprintf('Cycle %d', i));
        end
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion Angle (deg)');
    title('Individual Gait Cycles');
    legend('show');
    grid on;
    ```

## Calculating Biomechanical Metrics

### Range of Motion (ROM)

=== "Using Library"
    ```matlab
    % Calculate ROM using built-in method
    romData = subjectData.calculateROM('SUB01', 'level_walking', features, true);
    
    % Display results
    fprintf('Range of Motion Analysis:\n');
    fprintf('========================\n');
    for i = 1:length(featureNames)
        feature = featureNames{i};
        if isfield(romData, feature)
            meanROM = mean(romData.(feature), 'omitnan');
            stdROM = std(romData.(feature), 'omitnan');
            
            if contains(feature, 'angle')
                fprintf('%s: %.1f ± %.1f deg\n', feature, ...
                       rad2deg(meanROM), rad2deg(stdROM));
            else
                fprintf('%s: %.3f ± %.3f\n', feature, meanROM, stdROM);
            end
        end
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual ROM calculation
    function romValues = calculateROM(data3D)
        % Calculate range of motion for each cycle
        romValues = max(data3D, [], 2) - min(data3D, [], 2);
    end
    
    % Calculate ROM for knee flexion
    kneeROM = calculateROM(kneeData);
    
    fprintf('Knee Flexion ROM:\n');
    fprintf('Mean: %.1f deg\n', rad2deg(mean(kneeROM, 'omitnan')));
    fprintf('Std:  %.1f deg\n', rad2deg(std(kneeROM, 'omitnan')));
    fprintf('Range: %.1f - %.1f deg\n', ...
            rad2deg(min(kneeROM)), rad2deg(max(kneeROM)));
    
    % Plot ROM distribution
    figure();
    histogram(rad2deg(kneeROM), 10, 'FaceAlpha', 0.7);
    xlabel('Range of Motion (deg)');
    ylabel('Number of Cycles');
    title('Knee Flexion ROM Distribution');
    grid on;
    ```

### Peak Values and Timing

=== "Using Library"
    ```matlab
    % Detect peaks using library method
    [peakValues, peakTimes] = subjectData.detectPeakTiming('SUB01', 'level_walking', features);
    
    % Analyze knee flexion peaks
    kneeFeature = featureNames{1};  % knee_flexion_angle_ipsi_rad
    
    maxValues = peakValues.(kneeFeature).max_values;
    maxTimes = peakTimes.(kneeFeature).max_times;
    minValues = peakValues.(kneeFeature).min_values;
    minTimes = peakTimes.(kneeFeature).min_times;
    
    fprintf('Knee Flexion Peak Analysis:\n');
    fprintf('==========================\n');
    fprintf('Peak Flexion: %.1f ± %.1f deg at %.1f ± %.1f%% GC\n', ...
            rad2deg(mean(maxValues, 'omitnan')), rad2deg(std(maxValues, 'omitnan')), ...
            mean(maxTimes, 'omitnan'), std(maxTimes, 'omitnan'));
    fprintf('Min Flexion:  %.1f ± %.1f deg at %.1f ± %.1f%% GC\n', ...
            rad2deg(mean(minValues, 'omitnan')), rad2deg(std(minValues, 'omitnan')), ...
            mean(minTimes, 'omitnan'), std(minTimes, 'omitnan'));
    ```

=== "Using Raw Data"
    ```matlab
    % Manual peak detection
    function [peakVals, peakTimes, minVals, minTimes] = findPeaks(data3D)
        [nCycles, nPoints, ~] = size(data3D);
        
        peakVals = zeros(nCycles, 1);
        peakTimes = zeros(nCycles, 1);
        minVals = zeros(nCycles, 1);
        minTimes = zeros(nCycles, 1);
        
        for c = 1:nCycles
            cycleData = data3D(c, :, 1);
            if ~any(isnan(cycleData))
                [maxVal, maxIdx] = max(cycleData);
                [minVal, minIdx] = min(cycleData);
                
                peakVals(c) = maxVal;
                peakTimes(c) = (maxIdx - 1) / (nPoints - 1) * 100;
                minVals(c) = minVal;
                minTimes(c) = (minIdx - 1) / (nPoints - 1) * 100;
            else
                peakVals(c) = NaN;
                peakTimes(c) = NaN;
                minVals(c) = NaN;
                minTimes(c) = NaN;
            end
        end
    end
    
    [peakVals, peakTimes, minVals, minTimes] = findPeaks(data3D);
    
    % Plot peak timing distribution
    figure();
    subplot(1, 2, 1);
    histogram(peakTimes, 10, 'FaceAlpha', 0.7);
    xlabel('Peak Time (% Gait Cycle)');
    ylabel('Number of Cycles');
    title('Peak Flexion Timing');
    grid on;
    
    subplot(1, 2, 2);
    histogram(rad2deg(peakVals), 10, 'FaceAlpha', 0.7);
    xlabel('Peak Flexion (deg)');
    ylabel('Number of Cycles');
    title('Peak Flexion Values');
    grid on;
    ```

## Cycle Feature Extraction

### Extracting Multiple Metrics

=== "Using Library"
    ```matlab
    % Extract comprehensive cycle features
    cycleFeatures = subjectData.extractCycleFeatures('SUB01', 'level_walking', ...
        'Features', features, ...
        'Metrics', {'rom', 'peak', 'mean', 'std', 'peak_time'});
    
    % Display first few rows
    fprintf('Cycle Features Table:\n');
    disp(head(cycleFeatures));
    
    % Summary statistics
    fprintf('\nSummary Statistics:\n');
    fprintf('==================\n');
    varNames = cycleFeatures.Properties.VariableNames;
    for i = 2:width(cycleFeatures)  % Skip cycle_id
        varName = varNames{i};
        values = cycleFeatures.(varName);
        
        fprintf('%s:\n', varName);
        fprintf('  Mean: %.3f\n', mean(values, 'omitnan'));
        fprintf('  Std:  %.3f\n', std(values, 'omitnan'));
        fprintf('  Range: %.3f - %.3f\n', min(values), max(values));
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual feature extraction
    function featureTable = extractFeatures(data3D, featureNames)
        [nCycles, ~, nFeatures] = size(data3D);
        
        % Initialize results
        cycleId = (1:nCycles)';
        featureTable = table(cycleId, 'VariableNames', {'cycle_id'});
        
        for f = 1:nFeatures
            featureName = featureNames{f};
            featureData = squeeze(data3D(:, :, f));
            
            % Calculate metrics
            rom = max(featureData, [], 2) - min(featureData, [], 2);
            peak = max(abs(featureData), [], 2);
            meanVal = mean(featureData, 2, 'omitnan');
            stdVal = std(featureData, 0, 2, 'omitnan');
            
            % Add to table
            featureTable.([featureName '_rom']) = rom;
            featureTable.([featureName '_peak']) = peak;
            featureTable.([featureName '_mean']) = meanVal;
            featureTable.([featureName '_std']) = stdVal;
        end
    end
    
    cycleFeatures = extractFeatures(data3D, featureNames);
    disp(head(cycleFeatures));
    ```

## Bilateral Comparisons

### Comparing Left and Right Sides

=== "Using Library"
    ```matlab
    % Get bilateral features
    bilateralFeatures = {'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', ...
                        'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad'};
    
    % Perform bilateral comparison
    comparison = subjectData.bilateralComparison('SUB01', 'level_walking', bilateralFeatures);
    
    % Display symmetry results
    fprintf('Bilateral Symmetry Analysis:\n');
    fprintf('===========================\n');
    
    joints = fieldnames(comparison);
    for i = 1:length(joints)
        joint = joints{i};
        symmetryIndex = comparison.(joint).symmetry_index;
        correlation = comparison.(joint).correlation;
        
        fprintf('%s:\n', strrep(joint, '_', ' '));
        fprintf('  Symmetry Index: %.1f ± %.1f%%\n', ...
               mean(symmetryIndex, 'omitnan'), std(symmetryIndex, 'omitnan'));
        fprintf('  Correlation: %.3f ± %.3f\n', ...
               mean(correlation, 'omitnan'), std(correlation, 'omitnan'));
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual bilateral analysis
    function symmetryIndex = calculateSymmetryIndex(ipsiData, contraData)
        % Symmetry index: (ipsi - contra) / (ipsi + contra) * 100
        ipsiMean = mean(ipsiData, 2, 'omitnan');
        contraMean = mean(contraData, 2, 'omitnan');
        
        symmetryIndex = (ipsiMean - contraMean) ./ (ipsiMean + contraMean) * 100;
    end
    
    % Get ipsi and contra knee data
    ipsiFeatures = features(contains(features, 'ipsi'));
    contraFeatures = strrep(ipsiFeatures, 'ipsi', 'contra');
    
    [ipsiData3D, ~] = extractCycles(subjectData, ipsiFeatures);
    [contraData3D, ~] = extractCycles(subjectData, contraFeatures);
    
    % Calculate symmetry for knee flexion
    kneeIpsi = squeeze(ipsiData3D(:, :, 1));
    kneeContra = squeeze(contraData3D(:, :, 1));
    
    symmetryIndex = calculateSymmetryIndex(kneeIpsi, kneeContra);
    
    fprintf('Knee Flexion Symmetry:\n');
    fprintf('Mean Symmetry Index: %.1f ± %.1f%%\n', ...
            mean(symmetryIndex, 'omitnan'), std(symmetryIndex, 'omitnan'));
    
    % Plot symmetry distribution
    figure();
    histogram(symmetryIndex, 10, 'FaceAlpha', 0.7);
    xlabel('Symmetry Index (%)');
    ylabel('Number of Cycles');
    title('Bilateral Symmetry Distribution');
    xline(0, 'r--', 'Perfect Symmetry');
    grid on;
    ```

## Outlier Detection

### Statistical Outlier Detection

=== "Using Library"
    ```matlab
    % Use built-in outlier detection
    validMask = subjectData.validateCycles('SUB01', 'level_walking');
    
    fprintf('Cycle Quality Assessment:\n');
    fprintf('========================\n');
    fprintf('Valid cycles: %d/%d (%.1f%%)\n', ...
            sum(validMask), length(validMask), 100 * mean(validMask));
    
    % Find outlier cycles using built-in method
    outlierCycles = subjectData.findOutlierCycles('SUB01', 'level_walking', features);
    
    fprintf('Outlier cycles detected: %d\n', length(outlierCycles));
    if ~isempty(outlierCycles)
        fprintf('Outlier cycle IDs: %s\n', num2str(outlierCycles'));
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual outlier detection using statistical methods
    function outlierIdx = detectOutliers(data, method)
        switch lower(method)
            case 'iqr'
                % Interquartile range method
                Q1 = prctile(data, 25);
                Q3 = prctile(data, 75);
                IQR = Q3 - Q1;
                outlierIdx = data < (Q1 - 1.5*IQR) | data > (Q3 + 1.5*IQR);
                
            case 'zscore'
                % Z-score method
                zScores = abs(zscore(data));
                outlierIdx = zScores > 3;
                
            case 'modified_zscore'
                % Modified Z-score (more robust)
                median_val = median(data);
                mad_val = mad(data, 1);
                modifiedZ = 0.6745 * (data - median_val) / mad_val;
                outlierIdx = abs(modifiedZ) > 3.5;
        end
    end
    
    % Detect outliers in knee ROM
    kneeROM = max(kneeData, [], 2) - min(kneeData, [], 2);
    
    outlierMethods = {'iqr', 'zscore', 'modified_zscore'};
    
    figure();
    for i = 1:length(outlierMethods)
        method = outlierMethods{i};
        outliers = detectOutliers(kneeROM, method);
        
        subplot(1, 3, i);
        boxplot(rad2deg(kneeROM), 'Outliers', rad2deg(kneeROM(outliers)));
        title(sprintf('%s Method', upper(method)));
        ylabel('ROM (deg)');
        
        fprintf('%s outliers: %d/%d cycles\n', method, sum(outliers), length(outliers));
    end
    
    sgtitle('Outlier Detection Methods');
    ```

### Visualizing Outliers

=== "Using Library"
    ```matlab
    % Plot normal vs outlier cycles
    if ~isempty(outlierCycles)
        figure();
        
        % Plot all cycles in light gray
        hold on;
        for c = 1:size(kneeData, 1)
            if ~any(isnan(kneeData(c, :)))
                plot(phase, rad2deg(kneeData(c, :)), 'Color', [0.8 0.8 0.8 0.3]);
            end
        end
        
        % Highlight outlier cycles in red
        for i = 1:length(outlierCycles)
            cycleIdx = outlierCycles(i);
            if cycleIdx <= size(kneeData, 1)
                plot(phase, rad2deg(kneeData(cycleIdx, :)), 'r-', 'LineWidth', 2);
            end
        end
        
        % Plot mean pattern
        meanPattern = mean(kneeData, 1, 'omitnan');
        plot(phase, rad2deg(meanPattern), 'b-', 'LineWidth', 3, 'DisplayName', 'Mean');
        
        xlabel('Gait Cycle (%)');
        ylabel('Knee Flexion Angle (deg)');
        title('Outlier Cycles Highlighted');
        legend('show');
        grid on;
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual outlier visualization
    outliers = detectOutliers(kneeROM, 'iqr');
    
    figure();
    subplot(2, 1, 1);
    hold on;
    
    % Plot normal cycles
    normalCycles = find(~outliers);
    for i = 1:length(normalCycles)
        c = normalCycles(i);
        plot(phase, rad2deg(kneeData(c, :)), 'Color', [0.2 0.4 0.8 0.3]);
    end
    
    % Plot outlier cycles
    outlierCycles = find(outliers);
    for i = 1:length(outlierCycles)
        c = outlierCycles(i);
        plot(phase, rad2deg(kneeData(c, :)), 'r-', 'LineWidth', 2);
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (deg)');
    title(sprintf('Normal vs Outlier Cycles (%d outliers)', sum(outliers)));
    grid on;
    
    % ROM comparison
    subplot(2, 1, 2);
    boxplot([rad2deg(kneeROM(~outliers)); rad2deg(kneeROM(outliers))], ...
            [zeros(sum(~outliers), 1); ones(sum(outliers), 1)]);
    set(gca, 'XTickLabel', {'Normal', 'Outliers'});
    ylabel('ROM (deg)');
    title('ROM Distribution');
    grid on;
    ```

## Advanced Cycle Analysis

### Cycle-to-Cycle Variability

=== "Using Library"
    ```matlab
    % Analyze cycle-to-cycle variability
    summary = subjectData.getSummaryStatistics('SUB01', 'level_walking', features);
    
    % Calculate coefficient of variation for each phase point
    meanPatterns = subjectData.getMeanPatterns('SUB01', 'level_walking');
    stdPatterns = subjectData.getStdPatterns('SUB01', 'level_walking');
    
    kneeFeature = featureNames{1};
    kneeMean = meanPatterns.(kneeFeature);
    kneeStd = stdPatterns.(kneeFeature);
    
    % Coefficient of variation
    cv = (kneeStd ./ abs(kneeMean)) * 100;
    cv(isinf(cv)) = NaN;  % Handle division by zero
    
    % Plot variability across gait cycle
    figure();
    subplot(2, 1, 1);
    plot(phase, cv, 'b-', 'LineWidth', 2);
    xlabel('Gait Cycle (%)');
    ylabel('Coefficient of Variation (%)');
    title('Cycle-to-Cycle Variability');
    grid on;
    
    subplot(2, 1, 2);
    fill([phase, fliplr(phase)], ...
         [rad2deg(kneeMean + kneeStd)', fliplr(rad2deg(kneeMean - kneeStd)')], ...
         [0.7 0.7 1], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
    hold on;
    plot(phase, rad2deg(kneeMean), 'b-', 'LineWidth', 2);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (deg)');
    title('Mean ± SD Pattern');
    grid on;
    ```

=== "Using Raw Data"
    ```matlab
    % Manual variability analysis
    meanPattern = mean(kneeData, 1, 'omitnan');
    stdPattern = std(kneeData, 0, 1, 'omitnan');
    
    % Coefficient of variation at each phase point
    cv = (stdPattern ./ abs(meanPattern)) * 100;
    cv(isinf(cv)) = NaN;
    
    fprintf('Variability Analysis:\n');
    fprintf('====================\n');
    fprintf('Mean CV: %.1f%%\n', mean(cv, 'omitnan'));
    fprintf('Max CV: %.1f%% at %.0f%% GC\n', max(cv), phase(cv == max(cv)));
    fprintf('Min CV: %.1f%% at %.0f%% GC\n', min(cv), phase(cv == min(cv)));
    
    % Find phases of high/low variability
    highVar = cv > prctile(cv, 75);
    lowVar = cv < prctile(cv, 25);
    
    fprintf('High variability phases: %s\n', ...
            num2str(phase(highVar), '%.0f '));
    fprintf('Low variability phases: %s\n', ...
            num2str(phase(lowVar), '%.0f '));
    ```

## Statistical Analysis

### Cycle Feature Correlations

=== "Using Library"
    ```matlab
    % Get correlations between features at each phase
    correlations = subjectData.getPhaseCorrelations('SUB01', 'level_walking', features);
    
    % Display correlation matrix
    fprintf('Feature Correlations:\n');
    fprintf('====================\n');
    corrMatrix = correlations.correlation_matrix;
    featureLabels = correlations.features;
    
    % Display correlation matrix
    for i = 1:length(featureLabels)
        fprintf('%20s: ', featureLabels{i});
        for j = 1:length(featureLabels)
            fprintf('%6.3f ', corrMatrix(i, j));
        end
        fprintf('\n');
    end
    ```

=== "Using Raw Data"
    ```matlab
    % Manual correlation analysis between cycle features
    numericData = cycleFeatures(:, 2:end);  % Exclude cycle_id
    corrMatrix = corr(table2array(numericData), 'Rows', 'complete');
    
    % Visualize correlation matrix
    figure();
    imagesc(corrMatrix);
    colorbar;
    colormap(jet);
    caxis([-1 1]);
    
    % Add labels
    varNames = cycleFeatures.Properties.VariableNames(2:end);
    shortNames = cellfun(@(x) strrep(x, 'knee_flexion_angle_ipsi_rad_', ''), ...
                        varNames, 'UniformOutput', false);
    
    set(gca, 'XTick', 1:length(shortNames), 'XTickLabel', shortNames);
    set(gca, 'YTick', 1:length(shortNames), 'YTickLabel', shortNames);
    xtickangle(45);
    title('Cycle Feature Correlations');
    ```

## Best Practices

### Data Quality Checks
```matlab
% Always check data completeness before analysis
[data3D, featureNames] = subjectData.getCycles('SUB01', 'level_walking', features);

% Check for missing cycles
validCycles = ~any(any(isnan(data3D), 2), 3);
fprintf('Data Quality Report:\n');
fprintf('===================\n');
fprintf('Total cycles: %d\n', size(data3D, 1));
fprintf('Valid cycles: %d (%.1f%%)\n', sum(validCycles), 100*mean(validCycles));
fprintf('Missing data cycles: %d\n', sum(~validCycles));

% Check cycle length consistency
cycleLengths = sum(~isnan(data3D(:, :, 1)), 2);
fprintf('Cycle length consistency: %s\n', ...
        all(cycleLengths == 150) ? 'PASS' : 'FAIL');
```

### Robust Statistical Measures
```matlab
% Use robust statistics for outlier-prone data
function stats = robustStats(data)
    stats.median = median(data, 'omitnan');
    stats.mad = mad(data, 1);  % Median absolute deviation
    stats.iqr = iqr(data);
    stats.q25 = prctile(data, 25);
    stats.q75 = prctile(data, 75);
end

% Example for knee ROM
kneeROM = max(kneeData, [], 2) - min(kneeData, [], 2);
robustKneeStats = robustStats(rad2deg(kneeROM));

fprintf('Robust ROM Statistics:\n');
fprintf('Median: %.1f deg\n', robustKneeStats.median);
fprintf('MAD: %.1f deg\n', robustKneeStats.mad);
fprintf('IQR: %.1f deg (%.1f - %.1f)\n', ...
        robustKneeStats.iqr, robustKneeStats.q25, robustKneeStats.q75);
```

## Summary

You've learned to perform comprehensive cycle analysis in MATLAB:

- **Individual cycle extraction** and 3D array manipulation
- **Biomechanical metrics** including ROM, peaks, and timing
- **Bilateral comparisons** and symmetry analysis  
- **Outlier detection** using multiple statistical methods
- **Cycle feature extraction** for statistical modeling
- **Variability analysis** and quality assessment

## Next Steps

[Continue to Tutorial 5: Group Analysis →](05_group_analysis.md)

Learn to aggregate data across multiple subjects and perform population-level statistical analyses.