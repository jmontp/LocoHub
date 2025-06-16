%{
Demonstration Script for LocomotionData MATLAB Plotting Utilities

Created: 2025-06-11 with user permission
Purpose: Comprehensive demonstration of the LocomotionData MATLAB plotting capabilities showing
         how to use the plotting methods for phase-normalized locomotion data visualization.

Intent:
This script demonstrates the key plotting features of the LocomotionData MATLAB library:

1. Phase Pattern Plotting: Spaghetti plots, mean±std, and combined visualizations
2. Task Comparison Plotting: Cross-task mean pattern comparison
3. Time Series Plotting: Time-indexed data visualization  
4. Custom Plotting: Advanced customization using raw 3D data access
5. Validation Integration: Automatic validation overlay with color coding

Output:
Generates demonstration plots in source/tests/sample_plots/demo_locomotion_plotting_matlab/:
- Phase pattern plots (spaghetti, mean, combined modes)
- Task comparison plots with multiple tasks
- Time series plots for time-indexed data
- Custom plotting examples with percentiles and styling
- Validation overlay demonstrations

Usage:
    cd source/tests
    matlab -batch "demo_locomotion_plotting_matlab"

This demo helps developers understand:
- How to visualize phase-normalized locomotion data in MATLAB
- Different plotting modes and their appropriate use cases
- Integration with biomechanical validation systems
- Custom plotting techniques for advanced analysis
%}

function demo_locomotion_plotting_matlab()
    % Main demonstration function
    fprintf('🎨 LocomotionData MATLAB Plotting Utilities Demonstration\n');
    fprintf('%s\n', repmat('=', 1, 60));
    
    try
        % Add library to path
        addpath('../lib/matlab');
        
        % Verify library is available
        if exist('LocomotionData', 'class') ~= 8
            error('LocomotionData class not found. Check library path.');
        end
        fprintf('✓ Successfully loaded LocomotionData library\n');
        
        % Create demonstration data
        demoData = setupDemoData();
        
        % Initialize LocomotionData
        loco = LocomotionData(demoData);
        
        % Run demonstrations
        demoPhasePatternPlotting(loco);
        demoTaskComparisonPlotting(loco);
        demoTimeSeriesPlotting(loco);
        demoCustomPlotting(loco);
        
        printBanner('Demo Complete');
        fprintf('🎉 All plotting demonstrations completed successfully!\n');
        fprintf('📁 Generated plots saved in: sample_plots/demo_locomotion_plotting_matlab/\n');
        
        % Count generated plots
        plotDir = 'sample_plots/demo_locomotion_plotting_matlab';
        if exist(plotDir, 'dir')
            plotFiles = dir(fullfile(plotDir, '*.png'));
            fprintf('📊 Generated %d demonstration plots\n', length(plotFiles));
        end
        
    catch ME
        fprintf('❌ Demo error: %s\n', ME.message);
        fprintf('   Location: %s (line %d)\n', ME.stack(1).name, ME.stack(1).line);
    end
end

function data = setupDemoData()
    % Create demonstration dataset with realistic biomechanical patterns
    printBanner('Setting Up Demonstration Data');
    
    % Parameters
    subjects = {'SUB01', 'SUB02', 'SUB03'};
    tasks = {'level_walking', 'incline_walking', 'decline_walking'};
    nCycles = 5;
    pointsPerCycle = 150;
    
    % Initialize data structure
    allData = table();
    
    for s = 1:length(subjects)
        subject = subjects{s};
        
        for t = 1:length(tasks)
            task = tasks{t};
            
            for cycle = 1:nCycles
                % Create realistic phase progression
                phase = linspace(0, 100, pointsPerCycle)';
                
                % Generate realistic biomechanical patterns
                % Hip flexion: ~20-30 degrees peak
                if contains(task, 'incline')
                    hipBase = 0.4;
                elseif contains(task, 'decline')
                    hipBase = 0.3;
                else
                    hipBase = 0.35;
                end
                hipFlexion = hipBase * sin(2 * pi * phase / 100) + 0.05 * randn(pointsPerCycle, 1);
                
                % Knee flexion: ~60-70 degrees peak, offset from hip
                if contains(task, 'incline')
                    kneeBase = 1.1;
                elseif contains(task, 'decline')
                    kneeBase = 0.9;
                else
                    kneeBase = 1.0;
                end
                kneeFlexion = kneeBase * sin(2 * pi * phase / 100 + pi/6) + 0.1 * randn(pointsPerCycle, 1);
                
                % Ankle dorsiflexion: ~15-20 degrees, different phase
                if contains(task, 'incline')
                    ankleBase = 0.25;
                elseif contains(task, 'decline')
                    ankleBase = 0.15;
                else
                    ankleBase = 0.2;
                end
                ankleFlexion = ankleBase * sin(2 * pi * phase / 100 - pi/3) + 0.05 * randn(pointsPerCycle, 1);
                
                % Add subject-specific variation
                subjectFactor = 1.0 + 0.1 * str2double(subject(end)) - 0.15;
                hipFlexion = hipFlexion * subjectFactor;
                kneeFlexion = kneeFlexion * subjectFactor * 1.05;
                ankleFlexion = ankleFlexion * subjectFactor * 0.95;
                
                % Create time series
                timeS = linspace((cycle-1) * 1.2, cycle * 1.2, pointsPerCycle)';
                
                % Create data for this cycle
                cycleData = table();
                cycleData.subject = repmat({subject}, pointsPerCycle, 1);
                cycleData.task = repmat({task}, pointsPerCycle, 1);
                cycleData.step = repmat(cycle-1, pointsPerCycle, 1);
                cycleData.phase_percent = phase;
                cycleData.time_s = timeS;
                cycleData.hip_flexion_angle_contra_rad = hipFlexion;
                cycleData.knee_flexion_angle_contra_rad = kneeFlexion;
                cycleData.ankle_flexion_angle_contra_rad = ankleFlexion;
                cycleData.hip_flexion_angle_ipsi_rad = hipFlexion * 0.95 + 0.02 * randn(pointsPerCycle, 1);
                cycleData.knee_flexion_angle_ipsi_rad = kneeFlexion * 1.02 + 0.05 * randn(pointsPerCycle, 1);
                cycleData.ankle_flexion_angle_ipsi_rad = ankleFlexion * 0.98 + 0.03 * randn(pointsPerCycle, 1);
                
                allData = [allData; cycleData];
            end
        end
    end
    
    fprintf('✓ Created demonstration dataset:\n');
    fprintf('  - Subjects: %d (%s)\n', length(subjects), strjoin(subjects, ', '));
    fprintf('  - Tasks: %d (%s)\n', length(tasks), strjoin(tasks, ', '));
    fprintf('  - Cycles per subject-task: %d\n', nCycles);
    fprintf('  - Total data points: %s\n', addCommas(height(allData)));
    
    data = allData;
end

function demoPhasePatternPlotting(loco)
    % Demonstrate phase pattern plotting with different modes
    printBanner('Phase Pattern Plotting Demonstration');
    
    subject = loco.subjects{1};
    task = loco.tasks{1};
    features = {'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad'};
    
    outputDir = 'sample_plots/demo_locomotion_plotting_matlab';
    if ~exist(outputDir, 'dir')
        mkdir(outputDir);
    end
    
    fprintf('Plotting for %s - %s\n', subject, task);
    
    % 1. Spaghetti plot - show all individual cycles
    fprintf('1. Creating spaghetti plot (individual cycles)...\n');
    try
        loco.plotPhasePatterns(subject, task, features, ...
                              'PlotType', 'spaghetti', ...
                              'SavePath', fullfile(outputDir, '1_spaghetti_plot.png'));
        fprintf('   ✓ Saved: 1_spaghetti_plot.png\n');
    catch ME
        fprintf('   ✗ Error: %s\n', ME.message);
    end
    
    % 2. Mean ± standard deviation plot
    fprintf('2. Creating mean±std plot with confidence bands...\n');
    try
        loco.plotPhasePatterns(subject, task, features, ...
                              'PlotType', 'mean', ...
                              'SavePath', fullfile(outputDir, '2_mean_std_plot.png'));
        fprintf('   ✓ Saved: 2_mean_std_plot.png\n');
    catch ME
        fprintf('   ✗ Error: %s\n', ME.message);
    end
    
    % 3. Combined plot - both individual cycles and mean
    fprintf('3. Creating combined plot (both modes)...\n');
    try
        loco.plotPhasePatterns(subject, task, features, ...
                              'PlotType', 'both', ...
                              'SavePath', fullfile(outputDir, '3_combined_plot.png'));
        fprintf('   ✓ Saved: 3_combined_plot.png\n');
    catch ME
        fprintf('   ✗ Error: %s\n', ME.message);
    end
    
    fprintf('\n📊 Phase pattern plots demonstrate:\n');
    fprintf('   - Gray lines: Valid cycles passing biomechanical validation\n');
    fprintf('   - Red lines: Invalid cycles failing validation criteria\n');
    fprintf('   - Blue line: Mean pattern across valid cycles only\n');
    fprintf('   - Blue shaded area: ±1 standard deviation (in mean mode)\n');
end

function demoTaskComparisonPlotting(loco)
    % Demonstrate task comparison plotting
    printBanner('Task Comparison Plotting Demonstration');
    
    subject = loco.subjects{1};
    tasks = loco.tasks;
    features = {'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad'};
    
    outputDir = 'sample_plots/demo_locomotion_plotting_matlab';
    
    if length(tasks) > 1
        fprintf('Comparing tasks for %s: %s\n', subject, strjoin(tasks, ', '));
        
        % Compare all available tasks
        try
            loco.plotTaskComparison(subject, tasks, features, ...
                                   'SavePath', fullfile(outputDir, '4_task_comparison.png'));
            fprintf('   ✓ Saved: 4_task_comparison.png\n');
        catch ME
            fprintf('   ✗ Error: %s\n', ME.message);
        end
        
        % Compare specific tasks
        if length(tasks) >= 2
            try
                loco.plotTaskComparison(subject, tasks(1:2), features, ...
                                       'SavePath', fullfile(outputDir, '5_two_task_comparison.png'));
                fprintf('   ✓ Saved: 5_two_task_comparison.png\n');
            catch ME
                fprintf('   ✗ Error: %s\n', ME.message);
            end
        end
        
        fprintf('\n📊 Task comparison plots show:\n');
        fprintf('   - Mean patterns for each task overlaid\n');
        fprintf('   - Different colors for each task\n');
        fprintf('   - Clear visualization of task-specific differences\n');
    else
        fprintf('⚠️  Only one task available - skipping task comparison\n');
    end
end

function demoTimeSeriesPlotting(loco)
    % Demonstrate time series plotting
    printBanner('Time Series Plotting Demonstration');
    
    subject = loco.subjects{1};
    task = loco.tasks{1};
    features = {'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad'};
    
    outputDir = 'sample_plots/demo_locomotion_plotting_matlab';
    
    if any(strcmp('time_s', loco.data.Properties.VariableNames))
        fprintf('Creating time series plot for %s - %s\n', subject, task);
        
        try
            loco.plotTimeSeries(subject, task, features, ...
                               'TimeCol', 'time_s', ...
                               'SavePath', fullfile(outputDir, '6_time_series.png'));
            fprintf('   ✓ Saved: 6_time_series.png\n');
        catch ME
            fprintf('   ✗ Error: %s\n', ME.message);
        end
        
        fprintf('\n📊 Time series plots show:\n');
        fprintf('   - Raw time-indexed data progression\n');
        fprintf('   - Multiple gait cycles in sequence\n');
        fprintf('   - Useful for identifying temporal patterns\n');
    else
        fprintf('⚠️  No time_s column available - skipping time series plotting\n');
    end
end

function demoCustomPlotting(loco)
    % Demonstrate custom plotting with raw 3D data access
    printBanner('Custom Plotting Demonstration');
    
    subject = loco.subjects{1};
    task = loco.tasks{1};
    features = {'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad'};
    
    outputDir = 'sample_plots/demo_locomotion_plotting_matlab';
    
    fprintf('Creating custom plots for %s - %s\n', subject, task);
    
    % Get 3D data and validation
    try
        [data3D, featureNames] = loco.getCycles(subject, task, features);
        validMask = loco.validateCycles(subject, task, features);
        
        if ~isempty(data3D)
            % Custom percentile plot
            figure('Position', [100, 100, 1200, 300], 'Visible', 'off');
            phaseX = linspace(0, 100, 150);
            
            for i = 1:length(featureNames)
                subplot(1, length(featureNames), i);
                
                featData = data3D(:, :, i);
                validData = featData(validMask, :);
                
                if ~isempty(validData)
                    % Calculate percentiles
                    p10 = prctile(validData, 10, 1);
                    p25 = prctile(validData, 25, 1);
                    p50 = prctile(validData, 50, 1);  % Median
                    p75 = prctile(validData, 75, 1);
                    p90 = prctile(validData, 90, 1);
                    
                    % Plot with custom styling
                    hold on;
                    fill([phaseX, fliplr(phaseX)], [p10, fliplr(p90)], ...
                         [0.8, 0.9, 1.0], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
                    fill([phaseX, fliplr(phaseX)], [p25, fliplr(p75)], ...
                         [0.6, 0.8, 1.0], 'FaceAlpha', 0.5, 'EdgeColor', 'none');
                    plot(phaseX, p50, 'Color', [0, 0.2, 0.6], 'LineWidth', 2);
                    
                    xlabel('Gait Cycle (%)');
                    ylabel(strrep(featureNames{i}, '_', ' '));
                    title(strrep(featureNames{i}, '_', ' '), 'Interpreter', 'none');
                    xlim([0, 100]);
                    grid on;
                    
                    if i == 1
                        legend({'10-90th percentile', '25-75th percentile', 'Median'}, ...
                               'Location', 'northeast', 'FontSize', 8);
                    end
                end
            end
            
            sgtitle(sprintf('%s - %s: Custom Percentile Analysis', subject, task));
            print(fullfile(outputDir, '7_custom_percentile_plot.png'), '-dpng', '-r300');
            close(gcf);
            
            fprintf('   ✓ Saved: 7_custom_percentile_plot.png\n');
            
            % Validation overlay demonstration
            figure('Position', [100, 100, 1200, 300], 'Visible', 'off');
            
            for i = 1:length(featureNames)
                subplot(1, length(featureNames), i);
                
                featData = data3D(:, :, i);
                validData = featData(validMask, :);
                invalidData = featData(~validMask, :);
                
                hold on;
                
                % Plot individual cycles with validation coloring
                for j = 1:size(validData, 1)
                    plot(phaseX, validData(j, :), 'Color', [0.7, 0.7, 0.7], 'LineWidth', 0.8);
                end
                for j = 1:size(invalidData, 1)
                    plot(phaseX, invalidData(j, :), 'r-', 'LineWidth', 0.8);
                end
                
                % Plot mean
                if ~isempty(validData)
                    meanCurve = mean(validData, 1);
                    plot(phaseX, meanCurve, 'b-', 'LineWidth', 3);
                end
                
                xlabel('Gait Cycle (%)');
                ylabel(strrep(featureNames{i}, '_', ' '));
                title(strrep(featureNames{i}, '_', ' '), 'Interpreter', 'none');
                xlim([0, 100]);
                grid on;
                
                if i == 1
                    legend({'Valid cycles', 'Invalid cycles', 'Mean'}, ...
                           'Location', 'northeast', 'FontSize', 8);
                end
            end
            
            sgtitle(sprintf('%s - %s: Validation Overlay Demo (Valid: %d/%d)', ...
                           subject, task, sum(validMask), length(validMask)));
            print(fullfile(outputDir, '8_validation_overlay_demo.png'), '-dpng', '-r300');
            close(gcf);
            
            fprintf('   ✓ Saved: 8_validation_overlay_demo.png\n');
            
            fprintf('\n📊 Custom plotting demonstrates:\n');
            fprintf('   - Access to raw 3D data arrays for advanced analysis\n');
            fprintf('   - Percentile-based visualization (10th, 25th, 50th, 75th, 90th)\n');
            fprintf('   - Custom validation overlay with color coding\n');
            fprintf('   - High-resolution export capabilities\n');
        else
            fprintf('⚠️  No valid data found for custom plotting\n');
        end
        
    catch ME
        fprintf('⚠️  Custom plotting error: %s\n', ME.message);
    end
end

function printBanner(title)
    % Print a formatted banner for demo sections
    fprintf('\n%s\n', repmat('=', 1, 60));
    fprintf('  %s\n', title);
    fprintf('%s\n', repmat('=', 1, 60));
end

function str = addCommas(num)
    % Add commas to large numbers for readability
    str = num2str(num);
    if length(str) > 3
        % Simple comma insertion for demo purposes
        str = sprintf('%,d', num);
    end
end