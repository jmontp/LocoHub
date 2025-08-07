function test_matlab_tutorial_05_group_analysis()
    % Test MATLAB Tutorial 05: Group Analysis
    % Tests all code examples from the group analysis tutorial
    
    fprintf('\n=== Testing MATLAB Tutorial 05: Group Analysis ===\n');
    
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
        @test_multi_subject_aggregation
        @test_ensemble_averages
        @test_group_comparisons
        @test_normative_data
        @test_missing_data_handling
        @test_statistical_analysis
        @test_group_helper_function
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

function test_multi_subject_aggregation()
    % Test aggregating data across multiple subjects
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    
    % Get all subjects
    allSubjects = loco.getSubjects();
    assert(~isempty(allSubjects), 'No subjects found');
    
    task = 'level_walking';
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    % Initialize storage
    subjectCount = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        
        % Filter data
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            % Get mean patterns
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            
            % Verify patterns exist
            assert(isstruct(meanPatterns), 'Mean patterns should be a struct');
            subjectCount = subjectCount + 1;
        end
    end
    
    assert(subjectCount > 0, 'No valid subjects found for aggregation');
    fprintf('    Successfully aggregated %d subjects\n', subjectCount);
end

function test_ensemble_averages()
    % Test computing ensemble averages across subjects
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    allSubjects = loco.getSubjects();
    task = 'level_walking';
    feature = 'knee_flexion_angle_ipsi_rad';
    
    % Collect data from all subjects
    allSubjectMeans = [];
    validCount = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            
            if isfield(meanPatterns, feature)
                validCount = validCount + 1;
                if validCount == 1
                    allSubjectMeans = zeros(length(allSubjects), 150);
                end
                allSubjectMeans(validCount, :) = meanPatterns.(feature);
            end
        end
    end
    
    % Compute ensemble statistics
    if validCount > 0
        ensembleMean = mean(allSubjectMeans(1:validCount, :), 1, 'omitnan');
        ensembleStd = std(allSubjectMeans(1:validCount, :), 0, 1, 'omitnan');
        ensembleSEM = ensembleStd / sqrt(validCount);
        
        assert(length(ensembleMean) == 150, 'Ensemble mean should have 150 points');
        assert(all(~isnan(ensembleMean)), 'Ensemble mean should not contain NaN');
        assert(all(ensembleSEM >= 0), 'SEM should be non-negative');
        
        fprintf('    Ensemble computed for %d subjects\n', validCount);
    end
end

function test_group_comparisons()
    % Test comparing two groups of subjects
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    allSubjects = loco.getSubjects();
    
    if length(allSubjects) >= 2
        % Split into two groups
        group1Subjects = allSubjects(1:floor(length(allSubjects)/2));
        group2Subjects = allSubjects(floor(length(allSubjects)/2)+1:end);
        
        task = 'level_walking';
        feature = 'knee_flexion_angle_ipsi_rad';
        
        % Get group data using helper function
        group1Data = getGroupData(loco, group1Subjects, task, {feature});
        group2Data = getGroupData(loco, group2Subjects, task, {feature});
        
        % Verify both groups have data
        assert(~isempty(group1Data), 'Group 1 should have data');
        assert(~isempty(group2Data), 'Group 2 should have data');
        
        % Check dimensions
        assert(size(group1Data, 2) == 150, 'Group 1 data should have 150 phase points');
        assert(size(group2Data, 2) == 150, 'Group 2 data should have 150 phase points');
        
        fprintf('    Compared %d vs %d subjects\n', size(group1Data, 1), size(group2Data, 1));
    end
end

function test_normative_data()
    % Test creation of normative reference ranges
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    allSubjects = loco.getSubjects();
    task = 'level_walking';
    feature = 'knee_flexion_angle_ipsi_rad';
    
    % Collect normative data
    normativeData = [];
    validCount = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            if isfield(meanPatterns, feature)
                validCount = validCount + 1;
                if validCount == 1
                    normativeData = zeros(length(allSubjects), 150);
                end
                normativeData(validCount, :) = meanPatterns.(feature);
            end
        end
    end
    
    if validCount > 0
        % Compute reference ranges
        normMean = mean(normativeData(1:validCount, :), 1, 'omitnan');
        normStd = std(normativeData(1:validCount, :), 0, 1, 'omitnan');
        
        % Reference ranges (mean ± 2SD)
        upperBound = normMean + 2 * normStd;
        lowerBound = normMean - 2 * normStd;
        
        % Verify bounds
        assert(all(upperBound > lowerBound), 'Upper bound should be greater than lower bound');
        assert(length(upperBound) == 150, 'Bounds should have 150 points');
        
        % Calculate summary metrics
        peakFlexion = max(normMean);
        rom = max(normMean) - min(normMean);
        
        assert(peakFlexion > 0, 'Peak flexion should be positive');
        assert(rom > 0, 'ROM should be positive');
        
        fprintf('    Normative data created from %d subjects\n', validCount);
        fprintf('    Peak flexion: %.2f rad, ROM: %.2f rad\n', peakFlexion, rom);
    end
end

function test_missing_data_handling()
    % Test handling of missing data across subjects
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    allSubjects = loco.getSubjects();
    task = 'level_walking';
    features = {'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    
    dataCompleteness = struct();
    dataCompleteness.complete = 0;
    dataCompleteness.partial = 0;
    dataCompleteness.missing = 0;
    
    for i = 1:length(allSubjects)
        subject = allSubjects{i};
        subjectData = loco.filterSubject(subject).filterTask(task);
        
        if subjectData.length() > 0
            meanPatterns = subjectData.getMeanPatterns(subject, task);
            availableFeatures = fieldnames(meanPatterns);
            
            missingFeatures = setdiff(features, availableFeatures);
            if isempty(missingFeatures)
                dataCompleteness.complete = dataCompleteness.complete + 1;
            else
                dataCompleteness.partial = dataCompleteness.partial + 1;
            end
        else
            dataCompleteness.missing = dataCompleteness.missing + 1;
        end
    end
    
    % Verify completeness tracking
    totalChecked = dataCompleteness.complete + dataCompleteness.partial + dataCompleteness.missing;
    assert(totalChecked == length(allSubjects), 'All subjects should be categorized');
    
    fprintf('    Data completeness - Complete: %d, Partial: %d, Missing: %d\n', ...
        dataCompleteness.complete, dataCompleteness.partial, dataCompleteness.missing);
end

function test_statistical_analysis()
    % Test statistical comparison functions
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    allSubjects = loco.getSubjects();
    
    if length(allSubjects) >= 2
        % Create two groups
        group1 = allSubjects(1);
        group2 = allSubjects(min(2, length(allSubjects)));
        
        task = 'level_walking';
        feature = 'knee_flexion_angle_ipsi_rad';
        
        % Get data for statistical testing
        g1Data = loco.filterSubject(group1{1}).filterTask(task);
        g2Data = loco.filterSubject(group2{1}).filterTask(task);
        
        if g1Data.length() > 0 && g2Data.length() > 0
            % Get mean patterns
            g1Mean = g1Data.getMeanPatterns(group1{1}, task);
            g2Mean = g2Data.getMeanPatterns(group2{1}, task);
            
            if isfield(g1Mean, feature) && isfield(g2Mean, feature)
                % Perform simple comparison
                diff = abs(g1Mean.(feature) - g2Mean.(feature));
                meanDiff = mean(diff, 'omitnan');
                
                assert(meanDiff >= 0, 'Mean difference should be non-negative');
                assert(~isnan(meanDiff), 'Mean difference should not be NaN');
                
                fprintf('    Statistical comparison completed\n');
            end
        end
    end
end

function test_group_helper_function()
    % Test the getGroupData helper function
    
    loco = LocomotionData('mock_data/mock_dataset_phase.parquet');
    subjects = loco.getSubjects();
    
    if ~isempty(subjects)
        task = 'level_walking';
        features = {'knee_flexion_angle_ipsi_rad'};
        
        % Test helper function
        groupData = getGroupData(loco, subjects(1:min(2, length(subjects))), task, features);
        
        % Verify output structure
        assert(ndims(groupData) == 3 || ndims(groupData) == 2, ...
            'Group data should be 2D or 3D array');
        
        if ~isempty(groupData)
            assert(size(groupData, 2) == 150, 'Should have 150 phase points');
            fprintf('    Helper function returned data for %d subjects\n', size(groupData, 1));
        end
    end
end

% Helper function for group data extraction
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
    if validCount > 0
        groupData = groupData(1:validCount, :, :);
        if size(groupData, 3) == 1
            groupData = squeeze(groupData);
        end
    end
end