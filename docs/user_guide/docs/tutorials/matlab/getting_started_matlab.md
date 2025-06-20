# Getting Started with MATLAB for Locomotion Data Analysis

[Skip to main content](#main-content)

This tutorial provides a basic guide on how to work with standardized locomotion data using MATLAB.

<a name="main-content"></a> We'll cover common tasks such as joining different data sources (e.g., primary data and task data), filtering by specific criteria, and performing basic analyses like calculating averages for features.

MATLAB's built-in table data type and functions are well-suited for these operations.

**Running the Examples/Test Script:**

The code examples in this tutorial are designed to match the `test_matlab_tutorial.m` script located in the `docs/tutorials/test_files/` directory. To run these examples:
1.  Ensure you have `locomotion_data.csv` and `task_info.csv` in the same directory as your script (or the test script), or that your MATLAB Current Folder is set to this directory. You can copy the CSV files from `docs/tutorials/test_files/` if needed.
2.  Open MATLAB and navigate its Current Folder to the directory containing the script and CSV files.
3.  Run the script from the MATLAB command window: `test_matlab_tutorial` (or your script's name).

The test script wraps all operations in a `try...catch ME ... end` block to handle errors. For clarity, this tutorial presents code in separate blocks where logical, but aims to reflect the test script's flow.

## 1. Loading Your Data

Let's assume your standardized locomotion data is stored in CSV files. MATLAB can easily import this data into `table` objects.

**File 1: `locomotion_data.csv`**

Create a file named `locomotion_data.csv` with the following content (this is the same file used in the Python tutorial):

```csv
time_s,step_id,subject_id,task_id,knee_flexion_angle_rad,hip_flexion_angle_rad,ankle_flexion_angle_rad,cop_x_m,cop_y_m,vertical_grf_N
0.01,1,P001,P001_T01,0.178,0.089,0.052,0.10,0.05,650.2
0.02,1,P001,P001_T01,0.218,0.108,0.063,0.11,0.06,680.5
0.03,1,P001,P001_T01,0.264,0.122,0.075,0.12,0.07,700.3
0.04,2,P001,P001_T02,0.354,0.183,0.087,0.15,0.10,720.8
0.05,2,P001,P001_T02,0.384,0.197,0.093,0.16,0.11,750.2
0.06,2,P001,P001_T02,0.447,0.224,0.105,0.17,0.12,760.5
0.07,3,P001,P001_T01,0.155,0.075,0.045,0.09,0.04,620.1
0.08,3,P001,P001_T01,0.182,0.087,0.055,0.10,0.05,640.3
0.09,3,P001,P001_T01,0.230,0.107,0.068,0.11,0.06,660.7
0.10,3,P001,P001_T01,0.279,0.131,0.079,0.12,0.07,680.9
```

**File 2: `task_info.csv`**

Create a file named `task_info.csv` with the following content (also the same as in the Python tutorial):

```csv
step_id,task_id,task_name,subject_id,ground_inclination_deg,walking_speed_m_s
1,P001_T01,level_walking,P001,0,1.2
2,P001_T02,incline_walking,P001,5,1.5
3,P001_T01,level_walking,P001,0,1.2
```

Now, let's load this data using `readtable()`:

```matlab
% Define file paths (relative to the script's location or MATLAB Current Folder)
locomotionDataFile = 'locomotion_data.csv';
taskInfoFile = 'task_info.csv';

if exist(locomotionDataFile, 'file') && exist(taskInfoFile, 'file')
    tblLocomotion = readtable(locomotionDataFile);
    tblTasks = readtable(taskInfoFile);

    disp('Locomotion Data (first 3 rows):');
    disp(tblLocomotion(1:3,:)); % Display first 3 rows, matching test script
    disp('Task Information:');
    disp(tblTasks); % Display all task info (it's small), matching test script
else
    disp('Error: Ensure ''''locomotion_data.csv'''' and ''''task_info.csv'''' exist in the MATLAB Current Folder or provide correct paths.');
    % Create empty tables to allow the rest of the script to run without error
    tblLocomotion = table(); 
    tblTasks = table();
end

```

This setup provides `tblLocomotion` with time-series data and `tblTasks` with information about the tasks performed.

## 2. Combining Locomotion Data with Task Data (Outer Join)

To analyze locomotion features in the context of specific tasks, you'll combine these tables. An **outer join** keeps all rows from both tables, filling in missing values with appropriate fill values (e.g., `NaN` for numeric, `<missing>` for categorical/string) where a match isn't found. In MATLAB, `outerjoin` is used for this.

```matlab
% Convert relevant columns to categorical for join operation consistency and performance
% This should be done if these columns are not already categorical or if there are type mismatches.
% The test script applies this to both tables before joining.
tblLocomotion.step_id = categorical(tblLocomotion.step_id);
tblTasks.step_id = categorical(tblTasks.step_id);
tblLocomotion.task_id = categorical(tblLocomotion.task_id);
tblTasks.task_id = categorical(tblTasks.task_id);
tblLocomotion.subject_id = categorical(tblLocomotion.subject_id);
tblTasks.subject_id = categorical(tblTasks.subject_id);

% Perform an outer join on common keys
tblCombined = outerjoin(tblLocomotion, tblTasks, 'Keys', {'step_id', 'task_id', 'subject_id'});

disp('Combined Data (first 3 rows):');
disp(tblCombined(1:3,:)); % Display first 3 rows, matching test script
```

**Why an outer join?**
*   You might have locomotion data that wasn't assigned a task (it will still be included).
*   You might have task definitions for which no locomotion data was recorded (they will also be included).
In many cases, a `leftjoin` or `innerjoin` might be more appropriate depending on your specific data and analysis goals.

## 3. Filtering for a Particular Task

Once your data is combined, you can easily filter it to focus on a specific task. For example, let's filter the data for the 'incline_walking' task.

```matlab
% Filter for a specific task, e.g., 'incline_walking'
% Ensure task_name is a cell array of strings or a string array for strcmp
% The test script handles potential type differences for task_name before comparison.
if iscellstr(tblCombined.task_name) || isstring(tblCombined.task_name) % Check added from test script
    is_incline_walking = strcmp(tblCombined.task_name, 'incline_walking');
else
    % Fallback for other types, though direct comparison might work if it's categorical and matches
    is_incline_walking = tblCombined.task_name == 'incline_walking'; 
end
tblInclineWalking = tblCombined(is_incline_walking, :);

disp('Data for 'incline_walking' task:');
disp(tblInclineWalking);

% You can also filter by other criteria, e.g., subject_id
% is_subject_p001 = strcmp(tblCombined.subject_id, 'P001'); % Assuming subject_id is categorical or string
% tblSubjectP001 = tblCombined(is_subject_p001, :);
```

This allows you to isolate the data segments relevant to your particular research question or analysis.

## 4. Phase-Based Averaging for Gait Analysis

A common operation in biomechanics is to normalize gait cycles to 0-100% phase and then generate average curves. This allows for comparing gait patterns regardless of differences in cycle duration.

**Example: Averaging knee angle across steps by phase percentage**

```matlab
% For demonstration, add a phase column (0-100%) to tblLocomotion
% In a real dataset, this might come from a separate phase-normalized data file.
tblWithPhaseDemo = tblLocomotion; % Use a new variable to avoid confusion with later steps in test script
tblWithPhaseDemo.phase_ = zeros(height(tblLocomotion), 1);

uniqueStepIds = unique(tblLocomotion.step_id);
for i = 1:length(uniqueStepIds)
    stepId = uniqueStepIds(i);
    stepMask = tblLocomotion.step_id == stepId;
    numPoints = sum(stepMask);
    tblWithPhaseDemo.phase_(stepMask) = linspace(0, 100, numPoints)';
end

% Create phase bins (e.g., 1% width)
phaseBinWidth = 1; 
phaseBins = 0:phaseBinWidth:100; % Edges: 0, 1, ..., 100
phaseBinCenters = phaseBins(1:end-1) + phaseBinWidth/2; % Centers: 0.5, 1.5, ..., 99.5

% Assign each row to a phase bin based on its phase_ value
% The test script uses a direct find approach for binning
getBin = @(phaseVal) find(phaseBins <= phaseVal, 1, 'last');
if isempty(tblWithPhaseDemo) || ~ismember('phase_', tblWithPhaseDemo.Properties.VariableNames)
    disp('Skipping phase binning as tblWithPhaseDemo is empty or missing phase_ column');
    tblWithPhaseDemo.phase_bin = zeros(height(tblWithPhaseDemo),0); % empty column
else
    tblWithPhaseDemo.phase_bin = arrayfun(getBin, tblWithPhaseDemo.phase_);
end

% Calculate average knee angle for each phase bin across all steps in tblWithPhaseDemo
phaseAveragesAllSteps = NaN(length(phaseBinCenters), 1); % Initialize with NaN
if ismember('phase_bin', tblWithPhaseDemo.Properties.VariableNames)
    for bin_idx = 1:length(phaseBinCenters)
        % In the test script, the bin index in arrayfun corresponds to the label of the bin.
        % For example, phase_bin = 1 corresponds to the first bin [0-1%)
        binData = tblWithPhaseDemo(tblWithPhaseDemo.phase_bin == bin_idx, :);
        if ~isempty(binData)
            phaseAveragesAllSteps(bin_idx) = mean(binData.knee_flexion_angle_rad, 'omitnan');
        end
    end
end
disp('Average knee flexion angle by phase (first 5 phases - all steps):');
if length(phaseBinCenters) >=5 && length(phaseAveragesAllSteps) >=5
    phaseTableAllSteps = table(phaseBinCenters(1:5)', phaseAveragesAllSteps(1:5), 'VariableNames', {'Phase', 'AvgKneeFlexionAngle'});
    disp(phaseTableAllSteps);
else
    disp('Not enough data for first 5 phases table.');
end

% For by-task analysis, the test script re-initializes tblWithPhase from tblLocomotion,
% adds phase and phase_bin, and then joins with tblTasks.

tblWithPhaseForTask = tblLocomotion; % Start from original locomotion data
tblWithPhaseForTask.phase_ = zeros(height(tblLocomotion), 1);
for i = 1:length(uniqueStepIds) % uniqueStepIds from earlier
    stepId = uniqueStepIds(i);
    stepMask = tblLocomotion.step_id == stepId;
    numPoints = sum(stepMask);
    tblWithPhaseForTask.phase_(stepMask) = linspace(0, 100, numPoints)';
end
tblWithPhaseForTask.phase_bin = arrayfun(getBin, tblWithPhaseForTask.phase_); % Use same getBin

% Ensure key columns are categorical for the join
tblWithPhaseForTask.step_id = categorical(tblWithPhaseForTask.step_id);
tblWithPhaseForTask.task_id = categorical(tblWithPhaseForTask.task_id);
tblWithPhaseForTask.subject_id = categorical(tblWithPhaseForTask.subject_id);
% tblTasks should have its keys already categorical from Section 2

tblPhaseWithTask = innerjoin(tblWithPhaseForTask, tblTasks, 'Keys', {'step_id', 'task_id', 'subject_id'});

uniqueTaskNames = unique(tblPhaseWithTask.task_name);
uniqueTaskNames = uniqueTaskNames(~ismissing(uniqueTaskNames)); % Remove missing values

taskPhaseAverages = NaN(length(phaseBinCenters), length(uniqueTaskNames)); % Initialize with NaN

for t_idx = 1:length(uniqueTaskNames)
    currentTaskName = uniqueTaskNames(t_idx);
    taskData = tblPhaseWithTask(strcmp(tblPhaseWithTask.task_name, currentTaskName), :);
    
    if ismember('phase_bin', taskData.Properties.VariableNames)
        for bin_idx = 1:length(phaseBinCenters)
            % Again, bin_idx refers to the label assigned by getBin
            binDataForTask = taskData(taskData.phase_bin == bin_idx, :);
            if ~isempty(binDataForTask)
                taskPhaseAverages(bin_idx, t_idx) = mean(binDataForTask.knee_flexion_angle_rad, 'omitnan');
            end
        end
    end
end

disp('Phase-based knee flexion angle by task (first 3 phases):');
for t_idx = 1:length(uniqueTaskNames)
    disp(['Task: ', char(uniqueTaskNames(t_idx))]);
    if length(phaseBinCenters) >=3 && size(taskPhaseAverages,1) >=3
        taskPhaseTable = table(phaseBinCenters(1:3)', taskPhaseAverages(1:3,t_idx), 'VariableNames', {'Phase', 'AvgKneeFlexionAngle'});
        disp(taskPhaseTable);
    else
        disp('Not enough data for first 3 phases table for this task.');
    end
end
```

Note: The standardized data format may also provide data already indexed by phase (e.g., in Parquet files). MATLAB can read Parquet files using `parquetread()` (requires appropriate setup/addons if not built-in to your version).

## 5. Basic Plotting

Visualizing your data is essential. MATLAB has powerful built-in plotting capabilities. The test script saves plots to files.

**Example 5.1: Plotting a time-series feature for a specific task**

Let's plot the `knee_flexion_angle_rad` over time for the 'incline_walking' task and save it.

```matlab
% Using tblInclineWalking from section 3
if height(tblInclineWalking) > 0
    figure; % Create a new figure window
    plot(tblInclineWalking.time_s, tblInclineWalking.knee_flexion_angle_rad, 'o-'); % Marker 'o', line '-'
    xlabel('Time (s)');
    ylabel('Knee Flexion Angle (rad)');
    title('Knee Flexion Angle during Incline Walking');
    grid on;
    saveas(gcf, 'matlab_knee_angle_incline.png'); % Save the current figure
    disp('Plot saved as ''matlab_knee_angle_incline.png''');
else
    disp('No data available for 'incline_walking' task to plot.');
end

% Example 5.2: Comparing average feature values across tasks (Bar Plot)
% Using taskPhaseAverages calculated in section 4
if ~isempty(uniqueTaskNames) && ~isempty(taskPhaseAverages)
    figure;
    % Calculate the overall average across all phases for each task for the bar plot
    taskMeansForBarPlot = mean(taskPhaseAverages, 1, 'omitnan'); % Mean across 1st dim (phases)
    
    if ~isempty(taskMeansForBarPlot)
        bar(categorical(uniqueTaskNames), taskMeansForBarPlot);
        xlabel('Task Name');
        ylabel('Average Knee Flexion Angle (rad)');
        title('Average Knee Flexion Angle by Task (mean of phase averages)');
        xtickangle(45); % Rotate x-axis labels for readability
        saveas(gcf, 'matlab_knee_angle_by_task.png');
        disp('Plot saved as ''matlab_knee_angle_by_task.png''');
    else
        disp('No task means available for bar plot.');
    end
else
    disp('No task data available for bar plot (uniqueTaskNames or taskPhaseAverages is empty).');
end
```

## 6. Calculating Derived Metrics

Often, you'll need to compute new metrics from your existing data.

**Example 6.1: Calculate Knee Angle Range of Motion (RoM) per step**

Let's calculate the knee angle RoM for each step in the 'level_walking' task. RoM can be (max value - min value).
We use `tblPhaseWithTask` from Section 4 which contains `task_name`.

```matlab
% Using tblPhaseWithTask from section 4
% Filter for level_walking task
if iscellstr(tblPhaseWithTask.task_name) || isstring(tblPhaseWithTask.task_name)
    is_level_walking = strcmp(tblPhaseWithTask.task_name, 'level_walking');
else
    is_level_walking = tblPhaseWithTask.task_name == 'level_walking';
end
tblLevelWalking = tblPhaseWithTask(is_level_walking, :);

if height(tblLevelWalking) > 0
    % Define a helper function for range or use an anonymous function
    rangefun = @(x) max(x) - min(x);
    
    % Group by step_id and then calculate RoM for knee_flexion_angle_rad
    % Ensure step_id is categorical for groupsummary
    tblLevelWalking.step_id = categorical(tblLevelWalking.step_id);
    % The test script does not rename 'fun1_Variable' but directly uses it or finds it.
    kneeRomTable = groupsummary(tblLevelWalking, 'step_id', rangefun, 'knee_flexion_angle_rad');
    
    % Find the automatically named RoM column (e.g., 'fun1_knee_flexion_angle_rad')
    romColName = '';
    varNames = kneeRomTable.Properties.VariableNames;
    for k=1:length(varNames)
        if contains(varNames{k}, 'fun') && contains(varNames{k}, 'knee_flexion_angle_rad')
            romColName = varNames{k};
            break;
        end
    end

    disp('Knee Flexion Angle ROM per step during 'level_walking':');
    if ~isempty(romColName)
        % Optionally rename for clarity if desired, but test script selects by found name
        % kneeRomTable.Properties.VariableNames{romColName} = 'knee_flexion_angle_rom_rad';
        disp(kneeRomTable(:, {'step_id', romColName})); 
    else
        disp('Could not automatically find RoM column. Displaying with default name(s).');
        disp(kneeRomTable); % Display the whole table if renaming/finding failed
    end
else
    disp('No data available for 'level_walking' task to calculate RoM.');
end

% Final message
disp('MATLAB tutorial operations completed (mimicking test script structure).');
```

## Conclusion

This tutorial covered basic operations for handling standardized locomotion data in MATLAB:
*   Loading data into tables using `readtable`.
*   Joining different tables using `outerjoin` (and `innerjoin` for specific analyses).
*   Filtering tables based on task information or other criteria.
*   Working with phase-normalized data for gait analysis, including binning and averaging.
*   Creating basic plots using `plot` and `bar`, and saving them with `saveas`.
*   Calculating derived metrics like Range of Motion using `groupsummary`.

These examples provide a starting point. MATLAB offers extensive toolboxes for more advanced signal processing, statistics, and machine learning that can be applied to locomotion data.

Refer to the [MATLAB documentation](https://www.mathworks.com/help/matlab/) for more comprehensive information. Consult your dataset's specific metadata and the [Units & Conventions](../../standard_spec/units_and_conventions.md) documentation for details on column names, units, and conventions. 