function test_matlab_tutorial_01_loading_data()
    % Test MATLAB Tutorial 01: Loading Data
    % Tests all code examples from the loading data tutorial
    
    fprintf('\n=== Testing MATLAB Tutorial 01: Loading Data ===\n');
    
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
        @test_basic_loading
        @test_structure_understanding
        @test_column_selection
        @test_variable_groups
        @test_subject_task_listing
        @test_variable_naming
        @test_raw_data_access
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

function test_basic_loading()
    % Test basic dataset loading
    
    % Load a complete phase-indexed dataset
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Check dataset size
    [rows, cols] = loco.getShape();
    assert(rows > 0, 'Dataset should have rows');
    assert(cols > 0, 'Dataset should have columns');
    
    % Check memory usage
    memUsage = loco.getMemoryUsage();
    assert(memUsage > 0, 'Memory usage should be positive');
end

function test_structure_understanding()
    % Test understanding data structure
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % View column names
    variables = loco.getVariables();
    assert(iscell(variables), 'Variables should be a cell array');
    assert(~isempty(variables), 'Should have variables');
    
    % Check data types
    dataTypes = loco.getDataTypes();
    assert(~isempty(dataTypes), 'Should have data types');
    
    % Preview first few rows
    headData = loco.head(5);
    assert(height(headData) <= 5, 'Head should return at most 5 rows');
end

function test_column_selection()
    % Test memory-efficient column selection
    
    % Load full dataset
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    fullMemory = loco.getMemoryUsage();
    
    % Load with column selection
    selectedColumns = {'subject', 'task', 'cycle_id', 'phase_percent', 'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    locoEfficient = LocomotionData( ...
        'mock_data/mock_dataset_phase.parquet', ...
        'Columns', selectedColumns);
    
    efficientMemory = locoEfficient.getMemoryUsage();
    
    % Verify reduced memory usage
    assert(efficientMemory <= fullMemory, ...
        'Selected columns should use less or equal memory');
    
    % Verify columns were selected
    vars = locoEfficient.getVariables();
    assert(length(vars) <= length(selectedColumns) + 2, ...  % +2 for phase columns
        'Should have limited columns');
end

function test_variable_groups()
    % Test loading variable groups
    
    % Load kinematic variables
    locoKinematics = LocomotionData( ...
        'mock_data/mock_dataset_phase.parquet', ...
        'VariableGroup', 'kinematics');
    
    % Check that we have angle variables
    vars = locoKinematics.getVariables();
    hasAngles = false;
    for i = 1:length(vars)
        if contains(vars{i}, 'angle')
            hasAngles = true;
            break;
        end
    end
    assert(hasAngles, 'Kinematics should include angle variables');
end

function test_subject_task_listing()
    % Test listing subjects and tasks
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Get unique subjects
    subjects = loco.getSubjects();
    assert(iscell(subjects), 'Subjects should be a cell array');
    assert(length(subjects) >= 3, 'Should have at least 3 subjects');
    
    % Get unique tasks
    tasks = loco.getTasks();
    assert(iscell(tasks), 'Tasks should be a cell array');
    assert(length(tasks) >= 3, 'Should have at least 3 tasks');
    
    % Count cycles per task
    for i = 1:length(tasks)
        nCycles = loco.countCycles('Task', tasks{i});
        assert(nCycles > 0, sprintf('Task %s should have cycles', tasks{i}));
    end
end

function test_variable_naming()
    % Test variable naming and info
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Get variable info
    variableInfo = loco.getVariableInfo();
    assert(isstruct(variableInfo), 'Variable info should be a struct');
    assert(isfield(variableInfo, 'kinematics'), 'Should have kinematics info');
    
    % Get variable descriptions
    variables = loco.getVariables();
    if ~isempty(variables)
        description = loco.getVariableDescription(variables{1});
        assert(ischar(description) || isstring(description), ...
            'Description should be a string');
    end
end

function test_raw_data_access()
    % Test accessing raw table data
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Access the underlying table data
    rawData = loco.data;
    assert(istable(rawData), 'Raw data should be a table');
    
    % MATLAB table operations
    subjects = unique(rawData.subject);
    assert(~isempty(subjects), 'Should have subjects in raw data');
    
    tasks = unique(rawData.task);
    assert(~isempty(tasks), 'Should have tasks in raw data');
    
    % Filter using table operations
    if any(strcmp(tasks, 'level_walking'))
        levelWalking = rawData(strcmp(rawData.task, 'level_walking'), :);
        assert(height(levelWalking) > 0, 'Should have level walking data');
    end
end