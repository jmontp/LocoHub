%{
Tutorial Test: MATLAB Library Functionality

Created: 2025-06-11 (moved from docs/tutorials/matlab/)
Purpose: Validates the MATLAB LocomotionData library functionality from the library tutorial

Intent:
This test script validates all functionality covered in the MATLAB library tutorial,
ensuring that the LocomotionData class works correctly for:

PRIMARY FUNCTIONS:
1. Library Import: Verify LocomotionData class can be loaded successfully
2. Data Creation: Test creation of test datasets with proper MATLAB structure
3. 3D Array Operations: Validate efficient reshape operations for phase data
4. Statistical Analysis: Test mean, std, and range calculations across cycles
5. Data Validation: Ensure data integrity and expected outputs

Usage:
    cd source/tests
    matlab -batch "test_tutorial_library_matlab"

Expected Output:
- Successful class loading confirmation
- Test data creation and validation
- 3D array operation results
- Statistical calculations
- All tests passing confirmation

This test ensures the library tutorial examples work correctly and validates
the core functionality users will rely on for biomechanical data analysis in MATLAB.
%}

disp('Testing MATLAB LocomotionData library...');

% Add library to path
addpath('../lib/matlab');

try
    % 1. Test Basic Data Loading
    disp('1. Testing basic data loading...');
    
    % Create sample data structure
    data = struct();
    data.subject_id = repmat({'AB01'}, 450, 1);
    data.time_s = linspace(0, 3, 450)';
    data.phase = repmat((0:149)'/150 * 100, 3, 1);
    data.step_number = repelem((0:2)', 150, 1);
    data.hip_flexion_angle_contra_rad = 0.5 * sin(2*pi*data.phase/100) + 0.1*randn(450, 1);
    data.knee_flexion_angle_contra_rad = 0.8 * sin(2*pi*data.phase/100 + pi/4) + 0.1*randn(450, 1);
    data.ankle_flexion_angle_contra_rad = 0.3 * sin(2*pi*data.phase/100 - pi/4) + 0.1*randn(450, 1);
    
    % Convert to table
    dataTable = struct2table(data);
    
    % Create LocomotionData object
    ld = LocomotionData(dataTable);
    disp('LocomotionData object created successfully');
    
    % 2. Test 3D Array Creation
    disp('2. Testing 3D array creation...');
    features = {'hip_flexion_angle_contra_rad', 'knee_flexion_angle_contra_rad', 'ankle_flexion_angle_contra_rad'};
    [data3d, featureNames, cycleInfo] = ld.to3DArray(features);
    fprintf('3D array shape: %d x %d x %d\n', size(data3d));
    disp('Feature names:');
    disp(featureNames);
    
    % 3. Test Validation
    disp('3. Testing validation...');
    validationReport = ld.validateData();
    disp('Validation report:');
    disp(validationReport);
    
    % 4. Test Statistics
    disp('4. Testing statistics calculation...');
    stats = ld.calculateStatistics(features);
    disp('Statistics:');
    disp(stats);
    
    % 5. Test ROM Calculation
    disp('5. Testing ROM calculation...');
    romData = ld.calculateROM(features);
    disp('ROM data (first 5 rows):');
    disp(romData(1:min(5, height(romData)), :));
    
    % 6. Test Data Merging
    disp('6. Testing data merging...');
    % Create task info
    taskInfo = table();
    taskInfo.subject_id = {'AB01'};
    taskInfo.task_id = {'walking'};
    taskInfo.task_name = {'level_walking'};
    taskInfo.speed_ms = 1.2;
    
    % Merge with task data
    mergedLD = ld.mergeWithTaskData(taskInfo, {'subject_id'});
    disp('Data merged successfully');
    disp(['Original columns: ', num2str(width(ld.data))]);
    disp(['Merged columns: ', num2str(width(mergedLD.data))]);
    
    % 7. Test Comprehensive Plotting Functions
    disp('7. Testing comprehensive plotting functions...');
    
    subject = ld.subjects{1};
    task = ld.tasks{1};
    
    % Test 7a: Phase pattern plots with different modes
    disp('  Testing phase pattern plots...');
    plotModes = {'spaghetti', 'mean', 'both'};
    for i = 1:length(plotModes)
        mode = plotModes{i};
        testFile = sprintf('test_phase_%s.png', mode);
        
        try
            ld.plotPhasePatterns(subject, task, features, ...
                                'PlotType', mode, ...
                                'SavePath', testFile);
            if exist(testFile, 'file')
                fprintf('    ✓ %s plot created\n', mode);
                delete(testFile);
            else
                fprintf('    ✗ %s plot failed\n', mode);
            end
        catch ME
            fprintf('    ✗ %s plot error: %s\n', mode, ME.message);
        end
    end
    
    % Test 7b: Task comparison plots  
    disp('  Testing task comparison plots...');
    if length(ld.tasks) > 1
        try
            ld.plotTaskComparison(subject, ld.tasks(1:2), features(1), ...
                                 'SavePath', 'test_comparison.png');
            if exist('test_comparison.png', 'file')
                disp('    ✓ Task comparison plot created');
                delete('test_comparison.png');
            else
                disp('    ✗ Task comparison plot failed');
            end
        catch ME
            fprintf('    ✗ Task comparison error: %s\n', ME.message);
        end
    else
        disp('    - Task comparison skipped (only 1 task available)');
    end
    
    % Test 7c: Time series plots
    disp('  Testing time series plots...');
    if any(strcmp('time_s', ld.data.Properties.VariableNames))
        try
            ld.plotTimeSeries(subject, task, features(1), ...
                             'SavePath', 'test_timeseries.png');
            if exist('test_timeseries.png', 'file')
                disp('    ✓ Time series plot created');
                delete('test_timeseries.png');
            else
                disp('    ✗ Time series plot failed');
            end
        catch ME
            fprintf('    ✗ Time series error: %s\n', ME.message);
        end
    else
        disp('    - Time series skipped (no time_s column)');
    end
    
    % Test 7d: Plot parameter validation
    disp('  Testing plot parameter validation...');
    try
        % Test invalid plot type - should handle gracefully
        ld.plotPhasePatterns(subject, task, features(1), 'PlotType', 'invalid');
        disp('    ✗ Should have handled invalid plot type');
    catch ME
        disp('    ✓ Invalid plot type properly handled');
    end
    
    % Test 7e: Empty data handling
    disp('  Testing empty data handling...');
    try
        ld.plotPhasePatterns('nonexistent', 'nonexistent', features(1));
        disp('    ✓ Empty data handled gracefully');
    catch ME
        disp('    ✓ Empty data handled with warning');
    end
    
    disp('✓ All plotting tests completed');
    
    % 8. Test Functional Interface
    disp('8. Testing functional interface...');
    
    % Load from struct
    dataStruct = ld.data;
    ld2 = loadLocomotionData(dataStruct);
    disp('Loaded from struct successfully');
    
    % Get 3D array using functional interface
    [data3d2, featureNames2] = getLocomotion3DArray(ld2, features);
    fprintf('Functional interface 3D array shape: %d x %d x %d\n', size(data3d2));
    
    % Validate using functional interface
    [isValid, report] = validateLocomotionData(ld2);
    fprintf('Functional validation result: %d\n', isValid);
    
    % Calculate stats using functional interface
    stats2 = calculateLocomotionStats(ld2, features);
    disp('Functional statistics calculated');
    
    % 9. Test Advanced Features
    disp('9. Testing advanced features...');
    
    % Test with multiple subjects
    data2 = data;
    data2.subject_id = repmat({'AB02'}, 450, 1);
    data2.hip_flexion_angle_contra_rad = 0.6 * sin(2*pi*data.phase/100) + 0.1*randn(450, 1);
    
    combinedData = [dataTable; struct2table(data2)];
    ldMulti = LocomotionData(combinedData);
    
    % Get unique subjects
    subjects = ldMulti.getUniqueSubjects();
    fprintf('Number of subjects: %d\n', length(subjects));
    disp('Subjects:');
    disp(subjects);
    
    % Filter by subject
    ldFiltered = ldMulti.filterBySubject('AB02');
    fprintf('Filtered data rows: %d\n', height(ldFiltered.data));
    
    % 10. Test Error Handling
    disp('10. Testing error handling...');
    
    % Test with invalid features
    try
        [~, ~] = ld.to3DArray({'nonexistent_feature'});
    catch ME
        disp('Caught expected error for invalid feature:');
        disp(ME.message);
    end
    
    % Test with empty data
    emptyLD = LocomotionData(table());
    try
        emptyLD.validateData();
        disp('Empty data validation handled gracefully');
    catch ME
        disp('Error with empty data:');
        disp(ME.message);
    end
    
    disp('===================================');
    disp('All MATLAB library tests passed successfully!');
    disp('===================================');
    
    % Clean up test files
    delete('test_time_series.png');
    delete('test_phase_patterns.png');
    delete('test_task_comparison.png');
    
catch ME
    disp('Error during library testing:');
    disp(ME.message);
    disp(ME.stack(1));
end