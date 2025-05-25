% Test script for MATLAB tutorial
disp('Testing MATLAB tutorial...');

% 1. Loading the Data
try
    % Define file paths
    locomotionDataFile = 'locomotion_data.csv';
    taskInfoFile = 'task_info.csv';
    
    % Check if files exist
    if exist(locomotionDataFile, 'file') && exist(taskInfoFile, 'file')
        tblLocomotion = readtable(locomotionDataFile);
        tblTasks = readtable(taskInfoFile);
        
        disp('Locomotion Data (first 3 rows):');
        disp(tblLocomotion(1:3,:));
        disp('Task Information:');
        disp(tblTasks);
        
        % 2. Combining Data (Outer Join)
        % Convert to categorical for better performance in joins
        tblLocomotion.step_id = categorical(tblLocomotion.step_id);
        tblTasks.step_id = categorical(tblTasks.step_id);
        tblLocomotion.task_id = categorical(tblLocomotion.task_id);
        tblTasks.task_id = categorical(tblTasks.task_id);
        tblLocomotion.subject_id = categorical(tblLocomotion.subject_id);
        tblTasks.subject_id = categorical(tblTasks.subject_id);
        
        % Perform join on multiple keys
        tblCombined = outerjoin(tblLocomotion, tblTasks, 'Keys', {'step_id', 'task_id', 'subject_id'});
        
        disp('Combined Data (first 3 rows):');
        disp(tblCombined(1:3,:));
        
        % 3. Filtering for a Particular Task
        % Check if task_name is a string array or cell array
        if iscellstr(tblCombined.task_name) || isstring(tblCombined.task_name)
            is_incline_walking = strcmp(tblCombined.task_name, 'incline_walking');
        else
            is_incline_walking = tblCombined.task_name == 'incline_walking';
        end
        tblInclineWalking = tblCombined(is_incline_walking, :);
        
        disp('Data for ''incline_walking'' task:');
        disp(tblInclineWalking);
        
        % 4. Phase-Based Averaging
        % Add phase column for demonstration
        tblWithPhase = tblLocomotion;
        tblWithPhase.phase_ = zeros(height(tblLocomotion), 1);
        
        % Add phase column by step_id
        uniqueStepIds = unique(tblLocomotion.step_id);
        for i = 1:length(uniqueStepIds)
            stepId = uniqueStepIds(i);
            stepMask = tblLocomotion.step_id == stepId;
            numPoints = sum(stepMask);
            tblWithPhase.phase_(stepMask) = linspace(0, 100, numPoints)';
        end
        
        % Create phase bins
        phaseBinWidth = 1;  % 1% bin width
        phaseBins = 0:phaseBinWidth:100;
        phaseBinCenters = phaseBins(1:end-1) + phaseBinWidth/2;
        
        % Create a function to find the bin for each phase value
        getBin = @(phase) find(phaseBins <= phase, 1, 'last');
        
        % Assign each row to a phase bin
        tblWithPhase.phase_bin = arrayfun(getBin, tblWithPhase.phase_);
        
        % Calculate averages by phase bin
        phaseAverages = zeros(length(phaseBinCenters), 1);
        for bin = 1:length(phaseBinCenters)
            binData = tblWithPhase(tblWithPhase.phase_bin == bin, :);
            if ~isempty(binData)
                phaseAverages(bin) = mean(binData.knee_flexion_angle_rad, 'omitnan');
            else
                phaseAverages(bin) = NaN;
            end
        end
        
        disp('Average knee flexion angle by phase (first 5 phases):');
        phaseTable = table(phaseBinCenters(1:5)', phaseAverages(1:5), 'VariableNames', {'Phase', 'AvgKneeFlexionAngle'});
        disp(phaseTable);
        
        % Join with task info for by-task analysis
        tblWithPhase = tblLocomotion;
        tblWithPhase.phase_ = zeros(height(tblLocomotion), 1);
        
        % Add phase column by step_id
        for i = 1:length(uniqueStepIds)
            stepId = uniqueStepIds(i);
            stepMask = tblLocomotion.step_id == stepId;
            numPoints = sum(stepMask);
            tblWithPhase.phase_(stepMask) = linspace(0, 100, numPoints)';
        end
        
        % Add phase bin
        tblWithPhase.phase_bin = arrayfun(getBin, tblWithPhase.phase_);
        
        % Combine with task info
        tblWithPhase.step_id = categorical(tblWithPhase.step_id);
        tblWithPhase.task_id = categorical(tblWithPhase.task_id);
        tblWithPhase.subject_id = categorical(tblWithPhase.subject_id);
        tblPhaseWithTask = innerjoin(tblWithPhase, tblTasks, 'Keys', {'step_id', 'task_id', 'subject_id'});
        
        % Calculate by task
        uniqueTasks = unique(tblPhaseWithTask.task_name);
        uniqueTasks = uniqueTasks(~ismissing(uniqueTasks));  % Remove missing values
        
        % Create a matrix to hold averages for each task
        taskAverages = zeros(length(phaseBinCenters), length(uniqueTasks));
        for t = 1:length(uniqueTasks)
            taskName = uniqueTasks(t);
            taskData = tblPhaseWithTask(strcmp(tblPhaseWithTask.task_name, taskName), :);
            
            for bin = 1:length(phaseBinCenters)
                binData = taskData(taskData.phase_bin == bin, :);
                if ~isempty(binData)
                    taskAverages(bin, t) = mean(binData.knee_flexion_angle_rad, 'omitnan');
                else
                    taskAverages(bin, t) = NaN;
                end
            end
        end
        
        disp('Phase-based knee flexion angle by task (first 3 phases):');
        for t = 1:length(uniqueTasks)
            disp(['Task: ', char(uniqueTasks(t))]);
            taskPhaseTable = table(phaseBinCenters(1:3)', taskAverages(1:3,t), 'VariableNames', {'Phase', 'AvgKneeFlexionAngle'});
            disp(taskPhaseTable);
        end
        
        % 5. Basic Plotting
        % 5.1 Time-series plot
        figure;
        plot(tblInclineWalking.time_s, tblInclineWalking.knee_flexion_angle_rad, '-o');
        xlabel('Time (s)');
        ylabel('Knee Flexion Angle (rad)');
        title('Knee Flexion Angle during Incline Walking');
        grid on;
        saveas(gcf, 'matlab_knee_angle_incline.png');
        disp('Plot saved as ''matlab_knee_angle_incline.png''');
        
        % 5.2 Bar plot of averages by task
        figure;
        % Calculate average across all phases for each task
        taskMeans = mean(taskAverages, 1, 'omitnan');
        bar(categorical(uniqueTasks), taskMeans);
        xlabel('Task Name');
        ylabel('Average Knee Flexion Angle (rad)');
        title('Average Knee Flexion Angle by Task');
        saveas(gcf, 'matlab_knee_angle_by_task.png');
        disp('Plot saved as ''matlab_knee_angle_by_task.png''');
        
        % 6. Calculating Derived Metrics - Range of Motion (ROM)
        % Define a range function
        rangefun = @(x) max(x) - min(x);
        
        % Get level_walking data
        if iscellstr(tblPhaseWithTask.task_name) || isstring(tblPhaseWithTask.task_name)
            is_level_walking = strcmp(tblPhaseWithTask.task_name, 'level_walking');
        else
            is_level_walking = tblPhaseWithTask.task_name == 'level_walking';
        end
        tblLevelWalking = tblPhaseWithTask(is_level_walking, :);
        
        % Group by step_id to calculate ROM
        tblLevelWalking.step_id = categorical(tblLevelWalking.step_id);
        kneeRomTable = groupsummary(tblLevelWalking, 'step_id', rangefun, 'knee_flexion_angle_rad');
        
        % Find the ROM column
        romColIdx = find(contains(kneeRomTable.Properties.VariableNames, 'fun') & ...
                          contains(kneeRomTable.Properties.VariableNames, 'knee_flexion_angle_rad'));
        
        % Rename the column for clarity if found
        if ~isempty(romColIdx)
            kneeRomTable.Properties.VariableNames{romColIdx} = 'knee_flexion_angle_rom_rad';
            disp('Knee Flexion Angle ROM per step:');
            disp(kneeRomTable(:, {'step_id', 'knee_flexion_angle_rom_rad'}));
        else
            disp('Could not find ROM column');
            disp(kneeRomTable);
        end
        
        disp('MATLAB tutorial test completed successfully!');
    else
        disp('Error: Test files not found.');
    end
catch ME
    disp('Error during testing:');
    disp(ME.message);
end 