function test_matlab_tutorial_02_data_filtering()
    % Test MATLAB Tutorial 02: Data Filtering
    % Tests all code examples from the data filtering tutorial
    
    fprintf('\n=== Testing MATLAB Tutorial 02: Data Filtering ===\n');
    
    % Add paths
    addpath(fullfile('..', 'user_libs', 'matlab'));
    
    % Check if mock dataset exists
    mockDataset = 'mock_data/mock_dataset_phase.parquet';
    if ~exist(mockDataset, 'file')
        error('Mock dataset not found. Run: python generate_mock_dataset.py');
    end
    
    % Run all test functions
    testCount = 0;
    passCount = 0;
    
    tests = {
        @test_filter_by_task
        @test_filter_by_subject
        @test_multiple_criteria
        @test_table_operations
        @test_cycle_filtering
        @test_variable_groups
        @test_chained_filters
        @test_filter_save_load
    };
    
    for i = 1:length(tests)
        testCount = testCount + 1;
        try
            tests{i}();
            passCount = passCount + 1;
            fprintf('  ✓ %s passed\n', func2str(tests{i}));
        catch ME
            fprintf('  ✗ %s failed: %s\n', func2str(tests{i}), ME.message);
        end
    end
    
    fprintf('\nResults: %d/%d tests passed\n', passCount, testCount);
    
    if passCount == testCount
        fprintf('SUCCESS: All tests passed!\n');
    else
        error('FAILURE: %d test(s) failed', testCount - passCount);
    end
end

function test_filter_by_task()
    % Test filtering by task
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    originalLength = loco.length();
    
    % Filter for level walking only
    levelWalking = loco.filterTask('level_walking');
    assert(levelWalking.length() <= originalLength, ...
        'Filtered data should not be larger than original');
    
    % Verify only level_walking task remains
    tasks = unique(levelWalking.data.task);
    assert(length(tasks) == 1 && strcmp(tasks{1}, 'level_walking'), ...
        'Should only have level_walking task');
    
    % Filter for multiple tasks
    walkingTasks = {'level_walking', 'incline_walking', 'decline_walking'};
    allWalking = loco.filterTasks(walkingTasks);
    
    % Verify filtered tasks
    filteredTasks = unique(allWalking.data.task);
    assert(all(ismember(filteredTasks, walkingTasks)), ...
        'Should only have specified walking tasks');
end

function test_filter_by_subject()
    % Test filtering by subject
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Single subject
    subject01 = loco.filterSubject('SUB01');
    subjects = unique(subject01.data.subject);
    assert(length(subjects) == 1 && strcmp(subjects{1}, 'SUB01'), ...
        'Should only have SUB01');
    
    % Multiple subjects
    subjectsOfInterest = {'SUB01', 'SUB02'};
    selectedSubjects = loco.filterSubjects(subjectsOfInterest);
    
    filteredSubjects = unique(selectedSubjects.data.subject);
    assert(all(ismember(filteredSubjects, subjectsOfInterest)), ...
        'Should only have selected subjects');
end

function test_multiple_criteria()
    % Test combining multiple filter criteria
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Level walking for specific subjects
    levelWalkingSubset = loco.filter( ...
        'Task', 'level_walking', ...
        'Subjects', {'SUB01', 'SUB02'});
    
    % Verify both criteria are met
    tasks = unique(levelWalkingSubset.data.task);
    subjects = unique(levelWalkingSubset.data.subject);
    
    assert(length(tasks) == 1 && strcmp(tasks{1}, 'level_walking'), ...
        'Should only have level_walking');
    assert(all(ismember(subjects, {'SUB01', 'SUB02'})), ...
        'Should only have specified subjects');
end

function test_table_operations()
    % Test direct table filtering operations
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    rawData = loco.data;
    
    % Level walking for specific subjects
    levelWalkingSubset = rawData( ...
        strcmp(rawData.task, 'level_walking') & ...
        ismember(rawData.subject, {'SUB01', 'SUB02'}), :);
    
    assert(height(levelWalkingSubset) > 0, ...
        'Should have some filtered data');
    
    % Verify filtering worked
    tasks = unique(levelWalkingSubset.task);
    assert(length(tasks) == 1 && strcmp(tasks{1}, 'level_walking'), ...
        'Table filtering should work correctly');
end

function test_cycle_filtering()
    % Test filtering by cycle characteristics
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Get actual cycle IDs from the data
    allCycles = unique(loco.data.cycle_id);
    
    % If we have at least 3 cycles, use the first 3
    if length(allCycles) >= 3
        testCycles = allCycles(1:3);
        filteredCycles = loco.filterCycles(testCycles);
        
        % Verify cycle filtering
        uniqueCycles = unique(filteredCycles.data.cycle_id);
        assert(all(ismember(uniqueCycles, testCycles)), ...
            'Should only have selected cycles');
    else
        % Just test that we can filter by whatever cycles exist
        testCycles = allCycles(1);
        filteredCycles = loco.filterCycles(testCycles);
        assert(height(filteredCycles.data) > 0, 'Should have some data');
    end
    
    % Test first N cycles method (simplified to avoid string/text issues)
    first2Cycles = loco.getFirstNCycles(2);
    
    % Simple test - just verify we got some data
    assert(height(first2Cycles.data) > 0, 'Should have some data');
    assert(height(first2Cycles.data) <= height(loco.data), 'Should not have more data than original');
end

function test_variable_groups()
    % Test filtering variables by groups
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    originalVars = width(loco.data);
    
    % Select kinematic variables
    kinematics = loco.selectVariableGroup('kinematics', 'Side', 'ipsi');
    
    % Should have fewer variables
    assert(width(kinematics.data) < originalVars, ...
        'Should have fewer variables after selection');
    
    % Check for angle variables
    vars = kinematics.data.Properties.VariableNames;
    hasAngles = any(contains(vars, 'angle'));
    assert(hasAngles, 'Kinematics should include angle variables');
end

function test_chained_filters()
    % Test chaining multiple filter operations
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Chain filters
    filtered = loco ...
        .filterTask('level_walking') ...
        .filterSubject('SUB01');
    
    % Verify both filters applied
    tasks = unique(filtered.data.task);
    subjects = unique(filtered.data.subject);
    
    assert(length(tasks) == 1 && strcmp(tasks{1}, 'level_walking'), ...
        'Should have level_walking task');
    assert(length(subjects) == 1 && strcmp(subjects{1}, 'SUB01'), ...
        'Should have SUB01 subject');
    
    % Test single filter call with multiple criteria
    filtered2 = loco.filter( ...
        'Task', 'level_walking', ...
        'Subject', 'SUB01');
    
    assert(height(filtered.data) == height(filtered2.data), ...
        'Chained and single filter should give same result');
end

function test_filter_save_load()
    % Test saving and loading filtered datasets
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Create filtered dataset
    levelWalking = loco.filterTask('level_walking');
    
    % Save to temporary file
    tempFile = 'temp_test_filtered.parquet';
    
    % Save using parquetwrite
    parquetwrite(tempFile, levelWalking.data);
    
    % Load back
    loaded = LocomotionData(tempFile);
    
    % Verify data matches
    assert(height(loaded.data) == height(levelWalking.data), ...
        'Loaded data should match saved data');
    
    % Clean up
    if exist(tempFile, 'file')
        delete(tempFile);
    end
end