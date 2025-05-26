% Test script for MATLAB library tutorial
% This script tests the LocomotionData library functionality

disp('Testing MATLAB LocomotionData library...');

% Add library to path
addpath('../../../source/lib/matlab');

try
    % 1. Test Basic Data Loading
    disp('1. Testing basic data loading...');
    
    % Create sample data structure
    data = struct();
    data.subject_id = repmat({'AB01'}, 450, 1);
    data.time_s = linspace(0, 3, 450)';
    data.phase = repmat((0:149)'/150 * 100, 3, 1);
    data.step_number = repelem((0:2)', 150, 1);
    data.hip_flexion_angle_right_rad = 0.5 * sin(2*pi*data.phase/100) + 0.1*randn(450, 1);
    data.knee_flexion_angle_right_rad = 0.8 * sin(2*pi*data.phase/100 + pi/4) + 0.1*randn(450, 1);
    data.ankle_flexion_angle_right_rad = 0.3 * sin(2*pi*data.phase/100 - pi/4) + 0.1*randn(450, 1);
    
    % Convert to table
    dataTable = struct2table(data);
    
    % Create LocomotionData object
    ld = LocomotionData(dataTable);
    disp('LocomotionData object created successfully');
    
    % 2. Test 3D Array Creation
    disp('2. Testing 3D array creation...');
    features = {'hip_flexion_angle_right_rad', 'knee_flexion_angle_right_rad', 'ankle_flexion_angle_right_rad'};
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
    
    % 7. Test Plotting Functions
    disp('7. Testing plotting functions...');
    
    % Time series plot
    figure('Visible', 'off');
    ld.plotTimeSeries({'knee_flexion_angle_right_rad'}, 'AB01');
    saveas(gcf, 'test_time_series.png');
    close(gcf);
    disp('Time series plot saved');
    
    % Phase pattern plot
    figure('Visible', 'off');
    ld.plotPhasePatterns(features, 'AB01');
    saveas(gcf, 'test_phase_patterns.png');
    close(gcf);
    disp('Phase patterns plot saved');
    
    % Task comparison plot
    figure('Visible', 'off');
    mergedLD.plotTaskComparison('knee_flexion_angle_right_rad', 'task_name');
    saveas(gcf, 'test_task_comparison.png');
    close(gcf);
    disp('Task comparison plot saved');
    
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
    data2.hip_flexion_angle_right_rad = 0.6 * sin(2*pi*data.phase/100) + 0.1*randn(450, 1);
    
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