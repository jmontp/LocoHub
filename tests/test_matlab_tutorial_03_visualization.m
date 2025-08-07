function test_matlab_tutorial_03_visualization()
    % Test MATLAB Tutorial 03: Visualization
    % Tests all code examples from the visualization tutorial
    
    fprintf('\n=== Testing MATLAB Tutorial 03: Visualization ===\n');
    
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
        @test_phase_averages
        @test_std_patterns
        @test_spaghetti_plot
        @test_publication_style
        @test_multi_feature_plots
        @test_task_comparisons
        @test_unit_conversions
        @test_figure_customization
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

function test_phase_averages()
    % Test computing phase averages
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    levelWalking = loco.filterTask('level_walking');
    
    if levelWalking.length() == 0
        error('No level walking data found');
    end
    
    subject = levelWalking.getSubjects();
    subject = subject{1};
    
    % Test getMeanPatterns
    meanPatterns = levelWalking.getMeanPatterns(subject, 'level_walking');
    assert(isstruct(meanPatterns), 'Mean patterns should be a struct');
    
    % Test that patterns have correct length (150 points)
    features = fieldnames(meanPatterns);
    if ~isempty(features)
        firstFeature = features{1};
        assert(length(meanPatterns.(firstFeature)) == 150, ...
            'Mean patterns should have 150 points per cycle');
    end
    
    % Test getStdPatterns
    stdPatterns = levelWalking.getStdPatterns(subject, 'level_walking');
    assert(isstruct(stdPatterns), 'Std patterns should be a struct');
    
    % Verify same features in both structs
    meanFeatures = sort(fieldnames(meanPatterns));
    stdFeatures = sort(fieldnames(stdPatterns));
    assert(isequal(meanFeatures, stdFeatures), ...
        'Mean and std patterns should have same features');
end

function test_std_patterns()
    % Test standard deviation pattern computation
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    levelWalking = loco.filterTask('level_walking');
    
    if levelWalking.length() == 0
        error('No level walking data found');
    end
    
    subject = levelWalking.getSubjects();
    subject = subject{1};
    
    stdPatterns = levelWalking.getStdPatterns(subject, 'level_walking');
    
    % Test that std values are non-negative
    features = fieldnames(stdPatterns);
    for i = 1:length(features)
        stdValues = stdPatterns.(features{i});
        assert(all(stdValues >= 0), ...
            sprintf('Standard deviation values should be non-negative for %s', features{i}));
        assert(length(stdValues) == 150, ...
            sprintf('Std pattern should have 150 points for %s', features{i}));
    end
end

function test_spaghetti_plot()
    % Test spaghetti plot functionality
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    levelWalking = loco.filterTask('level_walking');
    
    if levelWalking.length() == 0
        error('No level walking data found');
    end
    
    subject = levelWalking.getSubjects();
    subject = subject{1};
    
    % Test that plotSpaghettiPlot method exists and runs
    features = loco.getVariables();
    if ~isempty(features)
        testFeature = features(1);  % Use first available feature
        
        try
            fig = levelWalking.plotSpaghettiPlot(subject, 'level_walking', testFeature);
            assert(ishandle(fig), 'plotSpaghettiPlot should return a valid figure handle');
            
            % Test with different options
            fig2 = levelWalking.plotSpaghettiPlot(subject, 'level_walking', testFeature, ...
                'ShowMean', true, 'ShowStd', false, 'Alpha', 0.5);
            assert(ishandle(fig2), 'plotSpaghettiPlot with options should return a valid figure handle');
            
            % Clean up
            close(fig);
            close(fig2);
        catch ME
            rethrow(ME);
        end
    end
end

function test_publication_style()
    % Test publication style setting
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Test different styles
    styles = {'biomechanics', 'nature', 'ieee', 'default'};
    
    for i = 1:length(styles)
        try
            loco.setPublicationStyle(styles{i});
            % If no error, style was applied successfully
        catch ME
            error('Failed to set publication style "%s": %s', styles{i}, ME.message);
        end
    end
    
    % Test invalid style (should give warning, not error)
    try
        loco.setPublicationStyle('invalid_style');
        % Should complete without error but may give warning
    catch ME
        error('Setting invalid style should not throw error: %s', ME.message);
    end
    
    % Reset to default
    loco.setPublicationStyle('default');
end

function test_multi_feature_plots()
    % Test plotting multiple features
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    levelWalking = loco.filterTask('level_walking');
    
    if levelWalking.length() == 0
        error('No level walking data found');
    end
    
    subject = levelWalking.getSubjects();
    subject = subject{1};
    
    % Get available features
    features = loco.getVariables();
    
    if length(features) >= 2
        testFeatures = features(1:min(3, length(features)));  % Use up to 3 features
        
        try
            fig = levelWalking.plotPhasePatterns(subject, 'level_walking', testFeatures);
            assert(ishandle(fig), 'plotPhasePatterns should return a valid figure handle');
            close(fig);
        catch ME
            error('Multi-feature plotting failed: %s', ME.message);
        end
    end
end

function test_task_comparisons()
    % Test task comparison plots
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Get available tasks
    tasks = loco.getTasks();
    subjects = loco.getSubjects();
    
    if length(tasks) >= 2 && ~isempty(subjects)
        subject = subjects{1};
        testTasks = tasks(1:min(3, length(tasks)));  % Use up to 3 tasks
        features = loco.getVariables();
        
        if ~isempty(features)
            testFeature = features(1);
            
            try
                fig = loco.plotTaskComparison(subject, testTasks, testFeature);
                assert(ishandle(fig), 'plotTaskComparison should return a valid figure handle');
                close(fig);
            catch ME
                error('Task comparison plotting failed: %s', ME.message);
            end
        end
    end
end

function test_unit_conversions()
    % Test unit label and display name functions
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Test getUnitLabel
    testCases = struct(...
        'knee_flexion_angle_ipsi_rad', '(rad)', ...
        'knee_flexion_velocity_ipsi_rad_s', '(rad/s)', ...
        'knee_moment_ipsi_Nm', '(Nm)', ...
        'grf_vertical_ipsi_N', '(N)', ...
        'unknown_variable', '');
    
    featureNames = fieldnames(testCases);
    for i = 1:length(featureNames)
        feature = featureNames{i};
        expected = testCases.(feature);
        actual = loco.getUnitLabel(feature);
        assert(strcmp(actual, expected), ...
            sprintf('Unit label for %s should be "%s", got "%s"', feature, expected, actual));
    end
    
    % Test getFeatureDisplayName
    testName = 'knee_flexion_angle_ipsi_rad';
    displayName = loco.getFeatureDisplayName(testName);
    assert(ischar(displayName), 'Display name should be a character array');
    assert(~contains(displayName, '_'), 'Display name should not contain underscores');
end

function test_figure_customization()
    % Test figure customization options
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    levelWalking = loco.filterTask('level_walking');
    
    if levelWalking.length() == 0
        error('No level walking data found');
    end
    
    subject = levelWalking.getSubjects();
    subject = subject{1};
    
    features = loco.getVariables();
    if ~isempty(features)
        testFeature = features(1);
        
        % Test different Units options
        try
            fig1 = levelWalking.plotPhasePatterns(subject, 'level_walking', testFeature, ...
                'Units', 'degrees');
            assert(ishandle(fig1), 'Plot with degrees units should work');
            close(fig1);
            
            fig2 = levelWalking.plotPhasePatterns(subject, 'level_walking', testFeature, ...
                'Units', 'radians');
            assert(ishandle(fig2), 'Plot with radians units should work');
            close(fig2);
        catch ME
            error('Figure customization failed: %s', ME.message);
        end
    end
end