function test_matlab_dual_version_tutorial_03()
    % Test MATLAB Tutorial 03: Both Library and Raw Data versions
    % Tests that both approaches produce equivalent results
    
    fprintf('\n=== Testing Tutorial 03: Dual Version Validation ===\n');
    
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
        @test_phase_average_equivalence
        @test_spaghetti_plot_equivalence
        @test_multi_variable_equivalence
        @test_task_comparison_equivalence
        @test_publication_style_equivalence
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
        fprintf('SUCCESS: All dual version tests passed!\n');
    else
        error('FAILURE: %d dual version test(s) failed', testCount - passCount);
    end
end

function test_phase_average_equivalence()
    % Test that library and raw methods produce same phase averages
    
    % Load data both ways
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    rawData = parquetread('mock_data/mock_dataset_phase.parquet');
    
    % Filter for level walking, SUB01
    levelWalkingLib = loco.filterTask('level_walking').filterSubject('SUB01');
    levelWalkingRaw = rawData(strcmp(rawData.task, 'level_walking') & ...
                              strcmp(rawData.subject, 'SUB01'), :);
    
    % LIBRARY METHOD
    meanPatternsLib = levelWalkingLib.getMeanPatterns('SUB01', 'level_walking');
    stdPatternsLib = levelWalkingLib.getStdPatterns('SUB01', 'level_walking');
    kneeMeanLib = meanPatternsLib.knee_flexion_angle_ipsi_rad;
    kneeStdLib = stdPatternsLib.knee_flexion_angle_ipsi_rad;
    
    % RAW DATA METHOD
    phases = unique(levelWalkingRaw.phase_percent);
    kneeMeanRaw = zeros(length(phases), 1);
    kneeStdRaw = zeros(length(phases), 1);
    
    for i = 1:length(phases)
        phaseData = levelWalkingRaw.knee_flexion_angle_ipsi_rad(...
            levelWalkingRaw.phase_percent == phases(i));
        kneeMeanRaw(i) = mean(phaseData, 'omitnan');
        kneeStdRaw(i) = std(phaseData, 'omitnan');
    end
    
    % Compare results (allowing small numerical differences)
    tolerance = 1e-6;
    assert(max(abs(kneeMeanLib - kneeMeanRaw)) < tolerance, ...
        'Mean patterns differ between library and raw methods');
    assert(max(abs(kneeStdLib - kneeStdRaw)) < tolerance, ...
        'Std patterns differ between library and raw methods');
end

function test_spaghetti_plot_equivalence()
    % Test that spaghetti plots use same underlying data
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    rawData = parquetread('mock_data/mock_dataset_phase.parquet');
    
    levelWalkingLib = loco.filterTask('level_walking').filterSubject('SUB01');
    levelWalkingRaw = rawData(strcmp(rawData.task, 'level_walking') & ...
                              strcmp(rawData.subject, 'SUB01'), :);
    
    % Get cycles from library
    [data3DLib, ~] = levelWalkingLib.getCycles('SUB01', 'level_walking', ...
                                               {'knee_flexion_angle_ipsi_rad'});
    
    % Get cycles from raw data
    cycles = unique(levelWalkingRaw.cycle_id);
    nCycles = length(cycles);
    data3DRaw = zeros(nCycles, 150);
    
    for i = 1:nCycles
        cycleData = levelWalkingRaw(levelWalkingRaw.cycle_id == cycles(i), :);
        cycleData = sortrows(cycleData, 'phase_percent');
        
        % Ensure we have 150 points
        if height(cycleData) == 150
            data3DRaw(i, :) = cycleData.knee_flexion_angle_ipsi_rad;
        else
            data3DRaw(i, :) = NaN;
        end
    end
    
    % Compare dimensions
    assert(size(data3DLib, 1) == size(data3DRaw, 1), ...
        'Number of cycles differs between methods');
    assert(size(data3DLib, 2) == 150 && size(data3DRaw, 2) == 150, ...
        'Phase points should be 150 for both methods');
    
    % Compare actual data (squeeze library data to 2D)
    data3DLib2D = squeeze(data3DLib(:, :, 1));
    tolerance = 1e-6;
    
    % Compare non-NaN values
    validIdx = ~isnan(data3DLib2D(:)) & ~isnan(data3DRaw(:));
    if any(validIdx)
        maxDiff = max(abs(data3DLib2D(validIdx) - data3DRaw(validIdx)));
        assert(maxDiff < tolerance, ...
            sprintf('Cycle data differs by %f between methods', maxDiff));
    end
end

function test_multi_variable_equivalence()
    % Test multi-variable plotting data consistency
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    rawData = parquetread('mock_data/mock_dataset_phase.parquet');
    
    levelWalkingRaw = rawData(strcmp(rawData.task, 'level_walking') & ...
                              strcmp(rawData.subject, 'SUB01'), :);
    
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    for f = 1:length(features)
        feature = features{f};
        
        % Library method
        meanPatternsLib = loco.filterTask('level_walking').filterSubject('SUB01')...
                              .getMeanPatterns('SUB01', 'level_walking');
        if isfield(meanPatternsLib, feature)
            meanLib = meanPatternsLib.(feature);
        else
            continue;
        end
        
        % Raw method using helper function
        addpath(fullfile('..', 'user_libs', 'matlab'));
        [meanRaw, ~] = computePhaseAverage(levelWalkingRaw, feature);
        
        % Compare
        tolerance = 1e-6;
        assert(max(abs(meanLib - meanRaw)) < tolerance, ...
            sprintf('Feature %s differs between methods', feature));
    end
end

function test_task_comparison_equivalence()
    % Test task comparison data consistency
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    rawData = parquetread('mock_data/mock_dataset_phase.parquet');
    
    tasks = {'level_walking', 'incline_walking'};
    
    for t = 1:length(tasks)
        task = tasks{t};
        
        % Library method
        taskDataLib = loco.filterTask(task).filterSubject('SUB01');
        if taskDataLib.length() > 0
            meanPatternsLib = taskDataLib.getMeanPatterns('SUB01', task);
            if isfield(meanPatternsLib, 'knee_flexion_angle_ipsi_rad')
                meanLib = meanPatternsLib.knee_flexion_angle_ipsi_rad;
            else
                continue;
            end
        else
            continue;
        end
        
        % Raw method
        taskDataRaw = rawData(strcmp(rawData.task, task) & ...
                             strcmp(rawData.subject, 'SUB01'), :);
        if height(taskDataRaw) > 0
            [meanRaw, ~] = computePhaseAverage(taskDataRaw, 'knee_flexion_angle_ipsi_rad');
        else
            continue;
        end
        
        % Compare
        tolerance = 1e-6;
        assert(max(abs(meanLib - meanRaw)) < tolerance, ...
            sprintf('Task %s data differs between methods', task));
    end
end

function test_publication_style_equivalence()
    % Test that publication styling can be applied to both versions
    
    % Test library version
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    try
        loco.setPublicationStyle('biomechanics');
        % Should not error
    catch ME
        error('Library publication style failed: %s', ME.message);
    end
    
    % Test raw version with helper
    try
        applyPublicationStyle('biomechanics');
        % Should not error
    catch ME
        error('Raw publication style failed: %s', ME.message);
    end
    
    % Both methods should work without errors
    assert(true, 'Publication styles work for both methods');
end

% Helper function for raw data (local copy for testing)
function [meanCurve, stdCurve] = computePhaseAverage(data, variable)
    phases = unique(data.phase_percent);
    nPhases = length(phases);
    
    meanCurve = zeros(nPhases, 1);
    stdCurve = zeros(nPhases, 1);
    
    for i = 1:nPhases
        phaseData = data.(variable)(data.phase_percent == phases(i));
        meanCurve(i) = mean(phaseData, 'omitnan');
        stdCurve(i) = std(phaseData, 'omitnan');
    end
end

function applyPublicationStyle(style)
    % Apply publication style to current axes
    switch lower(style)
        case 'biomechanics'
            set(gca, 'FontSize', 12, 'FontName', 'Arial');
        case 'nature'
            set(gca, 'FontSize', 10, 'FontName', 'Helvetica');
        case 'ieee'
            set(gca, 'FontSize', 11, 'FontName', 'Times New Roman');
        otherwise
            set(gca, 'FontSize', 10);
    end
end