function romData = calculateROM(data, variable)
    % Calculate range of motion for each cycle
    %
    % Inputs:
    %   data - Table with cycle_id and variable columns
    %   variable - String name of the variable
    %
    % Outputs:
    %   romData - Array of ROM values per cycle
    
    cycles = unique(data.cycle_id);
    romData = zeros(length(cycles), 1);
    
    for i = 1:length(cycles)
        cycleData = data.(variable)(data.cycle_id == cycles(i));
        romData(i) = max(cycleData) - min(cycleData);
    end
end

function [peakValues, peakPhases] = detectPeaks(data, variable)
    % Detect peak values and their timing for each cycle
    %
    % Inputs:
    %   data - Table with cycle_id, phase_percent, and variable columns
    %   variable - String name of the variable
    %
    % Outputs:
    %   peakValues - Array of peak values per cycle
    %   peakPhases - Array of phase percentages where peaks occur
    
    cycles = unique(data.cycle_id);
    peakValues = zeros(length(cycles), 1);
    peakPhases = zeros(length(cycles), 1);
    
    for i = 1:length(cycles)
        cycleData = data(data.cycle_id == cycles(i), :);
        cycleData = sortrows(cycleData, 'phase_percent');
        
        values = cycleData.(variable);
        phases = cycleData.phase_percent;
        
        [peakVal, peakIdx] = max(values);
        peakValues(i) = peakVal;
        peakPhases(i) = phases(peakIdx) * (100/149);  % Convert to percentage
    end
end

function comparison = compareBilateral(data, ipsiVariable, contraVariable)
    % Compare ipsilateral and contralateral variables
    %
    % Inputs:
    %   data - Table with bilateral data
    %   ipsiVariable - String name of ipsilateral variable
    %   contraVariable - String name of contralateral variable
    %
    % Outputs:
    %   comparison - Struct with comparison results
    
    % Compute statistics for both sides
    [ipsiMean, ipsiStd] = computePhaseAverage(data, ipsiVariable);
    [contraMean, contraStd] = computePhaseAverage(data, contraVariable);
    
    % Calculate asymmetry
    asymmetry = abs(ipsiMean - contraMean);
    
    % Calculate correlation
    validIdx = ~isnan(ipsiMean) & ~isnan(contraMean);
    if sum(validIdx) > 1
        r = corrcoef(ipsiMean(validIdx), contraMean(validIdx));
        correlation = r(1,2);
    else
        correlation = NaN;
    end
    
    % Package results
    comparison = struct();
    comparison.ipsiMean = ipsiMean;
    comparison.ipsiStd = ipsiStd;
    comparison.contraMean = contraMean;
    comparison.contraStd = contraStd;
    comparison.asymmetry = asymmetry;
    comparison.meanAsymmetry = mean(asymmetry, 'omitnan');
    comparison.correlation = correlation;
end

function features = extractCycleFeatures(data, variables)
    % Extract key features from gait cycles
    %
    % Inputs:
    %   data - Table with cycle data
    %   variables - Cell array of variable names
    %
    % Outputs:
    %   features - Struct with extracted features per variable
    
    features = struct();
    
    for v = 1:length(variables)
        var = variables{v};
        
        if any(strcmp(data.Properties.VariableNames, var))
            % Calculate ROM
            romValues = calculateROM(data, var);
            
            % Detect peaks
            [peakValues, peakPhases] = detectPeaks(data, var);
            
            % Calculate mean and std across cycles
            cycles = unique(data.cycle_id);
            cycleAvgs = zeros(length(cycles), 1);
            
            for c = 1:length(cycles)
                cycleData = data.(var)(data.cycle_id == cycles(c));
                cycleAvgs(c) = mean(cycleData, 'omitnan');
            end
            
            % Store features
            features.(var) = struct();
            features.(var).rom_mean = mean(romValues, 'omitnan');
            features.(var).rom_std = std(romValues, 'omitnan');
            features.(var).peak_mean = mean(peakValues, 'omitnan');
            features.(var).peak_std = std(peakValues, 'omitnan');
            features.(var).peak_phase_mean = mean(peakPhases, 'omitnan');
            features.(var).peak_phase_std = std(peakPhases, 'omitnan');
            features.(var).cycle_avg_mean = mean(cycleAvgs, 'omitnan');
            features.(var).cycle_avg_std = std(cycleAvgs, 'omitnan');
        end
    end
end

function aggregated = aggregateSubjects(data, subjects, task, variable)
    % Aggregate data across multiple subjects
    %
    % Inputs:
    %   data - Full dataset table
    %   subjects - Cell array of subject IDs
    %   task - String task name
    %   variable - String variable name
    %
    % Outputs:
    %   aggregated - Struct with aggregated statistics
    
    nSubjects = length(subjects);
    allMeans = zeros(150, nSubjects);
    allStds = zeros(150, nSubjects);
    validCount = 0;
    
    for s = 1:nSubjects
        % Filter for subject and task
        subjectData = data(strcmp(data.subject, subjects{s}) & ...
                          strcmp(data.task, task), :);
        
        if height(subjectData) > 0
            validCount = validCount + 1;
            [meanCurve, stdCurve] = computePhaseAverage(subjectData, variable);
            allMeans(:, validCount) = meanCurve;
            allStds(:, validCount) = stdCurve;
        end
    end
    
    % Trim to valid subjects
    allMeans = allMeans(:, 1:validCount);
    allStds = allStds(:, 1:validCount);
    
    % Calculate ensemble statistics
    aggregated = struct();
    aggregated.ensembleMean = mean(allMeans, 2, 'omitnan');
    aggregated.ensembleStd = std(allMeans, 0, 2, 'omitnan');
    aggregated.ensembleSEM = aggregated.ensembleStd / sqrt(validCount);
    aggregated.subjectMeans = allMeans;
    aggregated.subjectStds = allStds;
    aggregated.nSubjects = validCount;
    aggregated.subjects = subjects(1:validCount);
end

% Helper function needed by other functions
function [meanCurve, stdCurve] = computePhaseAverage(data, variable)
    % Compute mean and std across cycles for each phase point
    % (Duplicate of visualization_helpers version for standalone use)
    
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