function test_all_matlab_tutorials()
    % Master test runner for all MATLAB tutorial tests
    %
    % Usage:
    %   test_all_matlab_tutorials()
    %
    % This will run all MATLAB tutorial test files and report results
    
    % Add MATLAB library to path
    addpath(fullfile('..', 'user_libs', 'matlab'));
    
    fprintf('\n');
    fprintf('======================================================================\n');
    fprintf('MATLAB TUTORIAL TEST REPORT\n');
    fprintf('======================================================================\n');
    fprintf('Date: %s\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
    
    % List of test files to run
    testFiles = {
        'test_matlab_tutorial_01_loading_data'
        'test_matlab_tutorial_02_data_filtering'
        'test_matlab_tutorial_03_visualization'
        'test_matlab_tutorial_04_cycle_analysis'
        'test_matlab_tutorial_05_group_analysis'
        'test_matlab_tutorial_06_publication_outputs'
        'test_matlab_dual_version_tutorial_03'
    };
    
    totalTests = length(testFiles);
    passedTests = 0;
    failedTests = 0;
    testResults = {};
    
    startTime = tic;
    
    % Run each test file
    for i = 1:length(testFiles)
        testName = testFiles{i};
        fprintf('\n----------------------------------------------------------------------\n');
        fprintf('Test: %s\n', strrep(testName, 'test_matlab_', ''));
        fprintf('File: %s.m\n', testName);
        
        testStart = tic;
        try
            % Run the test
            feval(testName);
            
            % Test passed
            passedTests = passedTests + 1;
            status = 'PASSED';
            errorMsg = '';
            fprintf('Status: PASSED\n');
            
        catch ME
            % Test failed
            failedTests = failedTests + 1;
            status = 'FAILED';
            errorMsg = ME.message;
            fprintf('Status: FAILED\n');
            fprintf('Error: %s\n', ME.message);
        end
        
        duration = toc(testStart);
        fprintf('Duration: %.2f seconds\n', duration);
        
        % Store result
        testResults{end+1} = struct( ...
            'name', testName, ...
            'status', status, ...
            'duration', duration, ...
            'error', errorMsg);
    end
    
    totalDuration = toc(startTime);
    
    % Print summary
    fprintf('\n----------------------------------------------------------------------\n');
    fprintf('Total tests: %d\n', totalTests);
    fprintf('Passed: %d\n', passedTests);
    fprintf('Failed: %d\n', failedTests);
    fprintf('Total duration: %.2f seconds\n', totalDuration);
    
    % Save report to file
    saveReport(testResults, totalTests, passedTests, failedTests, totalDuration);
    
    % Exit with appropriate code
    if failedTests > 0
        fprintf('\n');
        error('FAILURE: %d test(s) failed', failedTests);
    else
        fprintf('\nSUCCESS: All tests passed!\n');
    end
end

function saveReport(testResults, totalTests, passedTests, failedTests, totalDuration)
    % Save test report to file
    
    reportFile = 'matlab_tutorial_test_report.txt';
    
    fid = fopen(reportFile, 'w');
    if fid == -1
        warning('Could not create report file');
        return;
    end
    
    fprintf(fid, 'MATLAB TUTORIAL TEST REPORT\n');
    fprintf(fid, '======================================================================\n');
    fprintf(fid, 'Date: %s\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
    fprintf(fid, 'Total tests: %d\n', totalTests);
    fprintf(fid, 'Passed: %d\n', passedTests);
    fprintf(fid, 'Failed: %d\n', failedTests);
    fprintf(fid, 'Total duration: %.2f seconds\n\n', totalDuration);
    
    for i = 1:length(testResults)
        result = testResults{i};
        fprintf(fid, '----------------------------------------------------------------------\n');
        fprintf(fid, 'Test: %s\n', strrep(result.name, 'test_matlab_', ''));
        fprintf(fid, 'File: %s.m\n', result.name);
        fprintf(fid, 'Status: %s\n', result.status);
        fprintf(fid, 'Duration: %.2f seconds\n', result.duration);
        if ~isempty(result.error)
            fprintf(fid, 'Error: %s\n', result.error);
        end
        fprintf(fid, '\n');
    end
    
    fclose(fid);
    
    fprintf('\nReport saved to: %s\n', reportFile);
end