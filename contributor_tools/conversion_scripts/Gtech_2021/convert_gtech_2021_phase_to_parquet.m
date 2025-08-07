% Convert Gtech 2021 (CAMARGO_ET_AL_J_BIOMECH_DATASET) to standardized parquet format
% Direct conversion from raw data to phase-indexed (150 points per cycle) parquet
%
% This script processes the CAMARGO dataset directly without intermediate files,
% leveraging knowledge from existing implementations but with a cleaner approach.

clear all;
close all;

% Add utilities to path
addpath('utilities');

%% Configuration
NUM_POINTS = 150;  % Points per gait cycle
DATA_ROOT = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
OUTPUT_DIR = fullfile('..', '..', '..', 'converted_datasets');
OUTPUT_FILE = 'gtech_2021_phase.parquet';

% Create output directory if needed
if ~exist(OUTPUT_DIR, 'dir')
    mkdir(OUTPUT_DIR);
end

%% Load subject information
fprintf('Loading subject information...\n');
subjectInfo = load(fullfile(DATA_ROOT, 'SubjectInfo.mat'));
subjectInfo = subjectInfo.data;

%% Define subjects to process
% Exclude problematic subjects based on prior knowledge
subjects_to_process = {};
for i = 6:30
    if i == 22 || i == 26 || i == 27 || i == 29 || i == 100
        continue;  % Skip problematic subjects
    end
    subjects_to_process{end+1} = sprintf('AB%02d', i);
end

fprintf('Will process %d subjects\n', length(subjects_to_process));

%% Initialize output table
output_table = table();

%% Process each subject
for subj_idx = 1:length(subjects_to_process)
    subject_code = subjects_to_process{subj_idx};
    subject_str = sprintf('Gtech_2021_%s', subject_code);
    
    fprintf('\n========================================\n');
    fprintf('Processing %s (%d/%d)\n', subject_code, subj_idx, length(subjects_to_process));
    fprintf('========================================\n');
    
    % Get subject mass for moment normalization
    subject_mass = subjectInfo.Weight(strcmp(subjectInfo.Subject, subject_code));
    if isempty(subject_mass)
        fprintf('  WARNING: No mass data for %s, skipping\n', subject_code);
        continue;
    end
    fprintf('  Subject mass: %.2f kg\n', subject_mass);
    
    % Find subject's date folder
    subject_dir = fullfile(DATA_ROOT, subject_code);
    if ~exist(subject_dir, 'dir')
        fprintf('  WARNING: Subject directory not found\n');
        continue;
    end
    
    date_folders = dir(subject_dir);
    date_folders = date_folders([date_folders.isdir]);
    date_folders = date_folders(contains({date_folders.name}, '_'));
    
    if isempty(date_folders)
        fprintf('  WARNING: No date folder found\n');
        continue;
    end
    
    % Process the date folder (typically one per subject)
    date_path = fullfile(subject_dir, date_folders(1).name);
    fprintf('  Processing folder: %s\n', date_folders(1).name);
    
    % Process each locomotion mode
    subject_rows = [];
    
    % 1. Process treadmill data
    treadmill_rows = process_treadmill(date_path, subject_str, subject_mass);
    if ~isempty(treadmill_rows)
        subject_rows = [subject_rows; treadmill_rows];
        fprintf('  Added %d treadmill strides\n', height(treadmill_rows));
    end
    
    % 2. Process level ground data
    levelground_rows = process_levelground(date_path, subject_str, subject_mass);
    if ~isempty(levelground_rows)
        subject_rows = [subject_rows; levelground_rows];
        fprintf('  Added %d level ground strides\n', height(levelground_rows));
    end
    
    % 3. Process ramp data
    ramp_rows = process_ramp(date_path, subject_str, subject_mass);
    if ~isempty(ramp_rows)
        subject_rows = [subject_rows; ramp_rows];
        fprintf('  Added %d ramp strides\n', height(ramp_rows));
    end
    
    % 4. Process stair data
    stair_rows = process_stair(date_path, subject_str, subject_mass);
    if ~isempty(stair_rows)
        subject_rows = [subject_rows; stair_rows];
        fprintf('  Added %d stair strides\n', height(stair_rows));
    end
    
    % Add subject data to main table
    if ~isempty(subject_rows)
        output_table = [output_table; subject_rows];
        fprintf('  Total strides for %s: %d\n', subject_code, height(subject_rows));
    else
        fprintf('  WARNING: No valid strides found for %s\n', subject_code);
    end
end

%% Save to parquet
if height(output_table) > 0
    output_path = fullfile(OUTPUT_DIR, OUTPUT_FILE);
    fprintf('\n========================================\n');
    fprintf('Saving to: %s\n', output_path);
    fprintf('Total subjects: %d\n', length(unique(output_table.subject)));
    fprintf('Total strides: %d\n', height(output_table));
    
    % Expand arrays for parquet format (150 rows per stride)
    fprintf('Expanding arrays for parquet format...\n');
    expanded_table = expand_table_for_parquet(output_table);
    fprintf('Expanded to %d rows (150 points x %d strides)\n', height(expanded_table), height(output_table));
    fprintf('========================================\n');
    
    parquetwrite(output_path, expanded_table);
    fprintf('Conversion complete!\n');
else
    error('No data was processed successfully');
end

%% Helper Functions

function rows = process_treadmill(date_path, subject_str, subject_mass)
    % Process treadmill walking data
    rows = table();
    mode_path = fullfile(date_path, 'treadmill');
    
    if ~exist(mode_path, 'dir')
        return;
    end
    
    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        
        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end
        
        % Extract speed segments (find unique steady-state speeds)
        if ~isfield(trial_data, 'conditions') || ~istable(trial_data.conditions)
            continue;
        end
        
        speed_vec = trial_data.conditions.Speed;
        time_vec = trial_data.conditions.Header;
        
        % Find steady-state speeds using threshold-based detection
        steady_speeds = check_steady_speeds(speed_vec);
        
        % Process each steady-state speed
        for speed_val = steady_speeds'
            % Find regions at this exact speed
            speed_mask = (speed_vec == speed_val);
            
            % Find continuous regions
            diff_mask = [false; diff(speed_mask) ~= 0; false];
            region_starts = find(diff_mask(1:end-1) & speed_mask);
            region_ends = find(diff_mask(2:end) & ~speed_mask) - 1;
            
            % Process each continuous region
            for r = 1:length(region_starts)
                region_length = region_ends(r) - region_starts(r) + 1;
                
                % Need sufficient data for steady state (at least 0.5 seconds at 1000Hz)
                if region_length < 500
                    continue;
                end
                
                % Get time window for this region
                time_start = time_vec(region_starts(r));
                time_end = time_vec(region_ends(r));
                
                % Determine condition (steady, accelerating, or decelerating)
                condition = 'steady';
                if r > 1 && region_starts(r) > 1
                    prev_speed = speed_vec(region_starts(r) - 1);
                    if prev_speed ~= speed_val
                        if prev_speed < speed_val
                            condition = 'accelerating';
                        else
                            condition = 'decelerating';
                        end
                    end
                end
                
                % Extract strides for this segment
                task_info = sprintf('speed_m_s:%.2f,treadmill:true,condition:%s', speed_val, condition);
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'level_walking', 'level', task_info, subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end

function rows = process_levelground(date_path, subject_str, subject_mass)
    % Process level ground walking data
    rows = table();
    mode_path = fullfile(date_path, 'levelground');
    
    if ~exist(mode_path, 'dir')
        return;
    end
    
    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        
        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end
        
        % Determine speed from filename
        if contains(trial_name, 'slow')
            speed_val = 0.8;
        elseif contains(trial_name, 'fast')
            speed_val = 1.2;
        else
            speed_val = 1.0;  % normal or unspecified
        end
        
        % Check for labels to segment walking portions
        time_start = [];
        time_end = [];
        
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))
            % Has labels - use walk segments only
            labels = trial_data.conditions.Label;
            if iscell(labels)
                walk_mask = strcmp(labels, 'walk');
            else
                walk_mask = false(size(labels));
            end
            
            if sum(walk_mask) > 50
                walk_indices = find(walk_mask);
                time_start = trial_data.conditions.Header(walk_indices(1));
                time_end = trial_data.conditions.Header(walk_indices(end));
            end
        end
        
        % If no valid label segment, use entire trial
        if isempty(time_start) && isfield(trial_data, 'ik') && istable(trial_data.ik)
            time_start = trial_data.ik.Header(1);
            time_end = trial_data.ik.Header(end);
        end
        
        if ~isempty(time_start)
            % Extract strides
            stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                subject_str, 'level_walking', 'level', ...
                sprintf('speed_m_s:%.1f,overground:true', speed_val), ...
                subject_mass);
            
            if ~isempty(stride_rows)
                rows = [rows; stride_rows];
            end
        end
    end
end

function rows = process_ramp(date_path, subject_str, subject_mass)
    % Process ramp ascent/descent data
    rows = table();
    mode_path = fullfile(date_path, 'ramp');
    
    if ~exist(mode_path, 'dir')
        return;
    end
    
    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        
        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end
        
        % Default ramp angle
        ramp_angle = 5;  % degrees
        
        % Check for ramp incline in conditions
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions)
            if any(strcmp(trial_data.conditions.Properties.VariableNames, 'rampIncline'))
                ramp_angle = trial_data.conditions.rampIncline(1);
            end
        end
        
        % Process ascent and descent separately using labels
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))
            
            labels = trial_data.conditions.Label;
            
            % Process ascent
            if iscell(labels)
                ascent_mask = strcmp(labels, 'rampascent');
            else
                ascent_mask = false(size(labels));
            end
            
            if sum(ascent_mask) > 50
                ascent_indices = find(ascent_mask);
                time_start = trial_data.conditions.Header(ascent_indices(1));
                time_end = trial_data.conditions.Header(ascent_indices(end));
                
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'incline_walking', sprintf('incline_%ddeg', abs(ramp_angle)), ...
                    sprintf('incline_deg:%d,speed_m_s:1.0,overground:true', abs(ramp_angle)), ...
                    subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
            
            % Process descent
            if iscell(labels)
                descent_mask = strcmp(labels, 'rampdescent');
            else
                descent_mask = false(size(labels));
            end
            
            if sum(descent_mask) > 50
                descent_indices = find(descent_mask);
                time_start = trial_data.conditions.Header(descent_indices(1));
                time_end = trial_data.conditions.Header(descent_indices(end));
                
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'decline_walking', sprintf('decline_%ddeg', abs(ramp_angle)), ...
                    sprintf('incline_deg:-%d,speed_m_s:1.0,overground:true', abs(ramp_angle)), ...
                    subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end

function rows = process_stair(date_path, subject_str, subject_mass)
    % Process stair ascent/descent data
    rows = table();
    mode_path = fullfile(date_path, 'stair');
    
    if ~exist(mode_path, 'dir')
        return;
    end
    
    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        
        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end
        
        % Process ascent and descent separately using labels
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))
            
            labels = trial_data.conditions.Label;
            
            % Process ascent
            if iscell(labels)
                ascent_mask = strcmp(labels, 'stairascent');
            else
                ascent_mask = false(size(labels));
            end
            
            if sum(ascent_mask) > 50
                ascent_indices = find(ascent_mask);
                time_start = trial_data.conditions.Header(ascent_indices(1));
                time_end = trial_data.conditions.Header(ascent_indices(end));
                
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'stair_ascent', 'stair_ascent', ...
                    'speed_m_s:0.5,overground:true', subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
            
            % Process descent
            if iscell(labels)
                descent_mask = strcmp(labels, 'stairdescent');
            else
                descent_mask = false(size(labels));
            end
            
            if sum(descent_mask) > 50
                descent_indices = find(descent_mask);
                time_start = trial_data.conditions.Header(descent_indices(1));
                time_end = trial_data.conditions.Header(descent_indices(end));
                
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'stair_descent', 'stair_descent', ...
                    'speed_m_s:0.5,overground:true', subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end

function trial_data = load_trial_data(mode_path, trial_name)
    % Load all relevant data files for a trial
    trial_data = struct();
    
    try
        % Load conditions
        cond_file = fullfile(mode_path, 'conditions', trial_name);
        if exist(cond_file, 'file')
            temp = load(cond_file);
            % Handle different condition structures
            if isfield(temp, 'speed') && istable(temp.speed)
                % Treadmill format with speed table
                trial_data.conditions = temp.speed;
            elseif isfield(temp, 'data') && istable(temp.data)
                trial_data.conditions = temp.data;
            elseif isfield(temp, 'labels') && istable(temp.labels)
                % Level ground/ramp/stair format with labels
                trial_data.conditions = temp.labels;
            else
                % Keep as struct if not a standard format
                trial_data.conditions = temp;
            end
        end
        
        % Load IK (inverse kinematics)
        ik_file = fullfile(mode_path, 'ik', trial_name);
        if exist(ik_file, 'file')
            temp = load(ik_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.ik = temp.data;
            else
                trial_data.ik = temp;
            end
        end
        
        % Load ID (inverse dynamics)
        id_file = fullfile(mode_path, 'id', trial_name);
        if exist(id_file, 'file')
            temp = load(id_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.id = temp.data;
            else
                trial_data.id = temp;
            end
        end
        
        % Load right gait cycle events
        gc_file = fullfile(mode_path, 'gcRight', trial_name);
        if exist(gc_file, 'file')
            temp = load(gc_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.gcRight = temp.data;
            else
                trial_data.gcRight = temp;
            end
        end
        
    catch ME
        warning('Failed to load trial %s: %s', trial_name, ME.message);
        trial_data = [];
    end
end

function rows = extract_and_process_strides(trial_data, time_start, time_end, ...
    subject_str, task, task_id, task_info, subject_mass)
    % Extract strides from time window and process to standard format
    
    rows = [];  % Will collect complete stride rows
    NUM_POINTS = 150;  % Points per gait cycle
    
    % Check we have minimum required data
    if ~isfield(trial_data, 'gcRight') || ~istable(trial_data.gcRight) || ...
       ~isfield(trial_data, 'ik') || ~istable(trial_data.ik) || ...
       ~isfield(trial_data, 'id') || ~istable(trial_data.id)
        rows = table();
        return;
    end
    
    % Get time indices for the window of interest
    gc_time = trial_data.gcRight.Header;
    window_indices = find(gc_time >= time_start & gc_time <= time_end);
    
    if isempty(window_indices)
        rows = table();
        return;
    end
    
    % HeelStrike contains gait cycle percentages (0-100%)
    % Find heel strikes as falling edges where percentage drops to 0
    heel_strike_pct = trial_data.gcRight.HeelStrike;
    
    % Find falling edges (where HeelStrike == 0) within our window
    % Using the utility function from old code
    hs_indices = findFallingEdges_onlyInSection(heel_strike_pct == 0, window_indices);
    
    if length(hs_indices) < 2
        rows = table();
        return;  % Need at least 2 heel strikes for one stride
    end
    
    % Process each stride (heel strike to heel strike)
    for s = 1:(length(hs_indices)-1)
        stride_start_idx = hs_indices(s);
        stride_end_idx = hs_indices(s+1) - 1;  % End just before next heel strike
        
        % Get the gait cycle percentages for this stride
        stride_pct = heel_strike_pct(stride_start_idx:stride_end_idx);
        stride_time = gc_time(stride_start_idx:stride_end_idx);
        
        % Skip if we don't have good percentage data
        valid_pct_idx = find(stride_pct > 0, 1, 'first');
        if isempty(valid_pct_idx) || length(stride_pct) < 10
            continue;
        end
        
        % Get time bounds for this stride
        stride_start_time = stride_time(1);
        stride_end_time = stride_time(end);
        
        % Get indices for this stride in IK and ID data
        ik_mask = (trial_data.ik.Header >= stride_start_time) & (trial_data.ik.Header <= stride_end_time);
        id_mask = (trial_data.id.Header >= stride_start_time) & (trial_data.id.Header <= stride_end_time);
        
        if sum(ik_mask) < 10 || sum(id_mask) < 10
            continue;  % Not enough data points
        end
        
        % Phase (0-100% of gait cycle)
        target_pct = linspace(0, 100, NUM_POINTS)';
        
        % Initialize data arrays for this stride
        stride_data = struct();
        stride_data.phase_ipsi = target_pct;
        
        % Process kinematics (angles in degrees, convert to radians)
        deg2rad = pi/180;
        
        % For interpolation, we need to map from gait cycle percentage to data
        % Use the valid portion of the stride percentage data
        valid_stride_pct = stride_pct(valid_pct_idx:end);
        valid_stride_time = stride_time(valid_pct_idx:end);
        
        % Ankle dorsiflexion angle (note: may need sign flip depending on convention)
        if any(strcmp(trial_data.ik.Properties.VariableNames, 'ankle_angle_r'))
            angle_data = trial_data.ik.ankle_angle_r(ik_mask);
            ik_time = trial_data.ik.Header(ik_mask);
            % First interpolate angle data to stride time points
            angle_at_stride_time = interp1(ik_time, angle_data, valid_stride_time, 'linear', 'extrap');
            % Then interpolate from percentage to normalized 150 points
            % Note: negating to match dorsiflexion convention (positive = toe up)
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = -interp1(valid_stride_pct, angle_at_stride_time, target_pct, 'linear', 'extrap') * deg2rad;
        else
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
        end
        
        % Knee angle
        if any(strcmp(trial_data.ik.Properties.VariableNames, 'knee_angle_r'))
            angle_data = trial_data.ik.knee_angle_r(ik_mask);
            angle_at_stride_time = interp1(ik_time, angle_data, valid_stride_time, 'linear', 'extrap');
            stride_data.knee_flexion_angle_ipsi_rad = interp1(valid_stride_pct, angle_at_stride_time, target_pct, 'linear', 'extrap') * deg2rad;
        else
            stride_data.knee_flexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
        end
        
        % Hip angle
        if any(strcmp(trial_data.ik.Properties.VariableNames, 'hip_flexion_r'))
            angle_data = trial_data.ik.hip_flexion_r(ik_mask);
            angle_at_stride_time = interp1(ik_time, angle_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_angle_ipsi_rad = interp1(valid_stride_pct, angle_at_stride_time, target_pct, 'linear', 'extrap') * deg2rad;
        else
            stride_data.hip_flexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
        end
        
        % Process kinetics (moments, normalize by body mass)
        id_time = trial_data.id.Header(id_mask);
        
        % Ankle dorsiflexion moment
        if any(strcmp(trial_data.id.Properties.VariableNames, 'ankle_angle_r_moment'))
            moment_data = trial_data.id.ankle_angle_r_moment(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm = zeros(NUM_POINTS, 1);
        end
        
        % Knee flexion moment
        if any(strcmp(trial_data.id.Properties.VariableNames, 'knee_angle_r_moment'))
            moment_data = trial_data.id.knee_angle_r_moment(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.knee_flexion_moment_ipsi_Nm = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.knee_flexion_moment_ipsi_Nm = zeros(NUM_POINTS, 1);
        end
        
        % Hip flexion moment
        if any(strcmp(trial_data.id.Properties.VariableNames, 'hip_flexion_r_moment'))
            moment_data = trial_data.id.hip_flexion_r_moment(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_moment_ipsi_Nm = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.hip_flexion_moment_ipsi_Nm = zeros(NUM_POINTS, 1);
        end
        
        % Create single row with arrays for this stride
        row = table();
        row.subject = {subject_str};
        row.task = {task};
        row.task_id = {task_id};
        row.task_info = {task_info};
        row.step = s;
        row.phase_ipsi = {stride_data.phase_ipsi};  % Store as cell array
        row.ankle_dorsiflexion_angle_ipsi_rad = {stride_data.ankle_dorsiflexion_angle_ipsi_rad};
        row.knee_flexion_angle_ipsi_rad = {stride_data.knee_flexion_angle_ipsi_rad};
        row.hip_flexion_angle_ipsi_rad = {stride_data.hip_flexion_angle_ipsi_rad};
        row.ankle_dorsiflexion_moment_ipsi_Nm = {stride_data.ankle_dorsiflexion_moment_ipsi_Nm};
        row.knee_flexion_moment_ipsi_Nm = {stride_data.knee_flexion_moment_ipsi_Nm};
        row.hip_flexion_moment_ipsi_Nm = {stride_data.hip_flexion_moment_ipsi_Nm};
        
        % Append this single row
        if isempty(rows)
            rows = row;
        else
            rows = [rows; row];
        end
    end
    
    % Convert to table if we have data
    if ~isempty(rows) && ~istable(rows)
        rows = table();  % Return empty table if something went wrong
    end
end

function speeds = check_steady_speeds(speed_vector)
    % Find steady-state belt speeds
    % For Gtech data, speeds are exact values (0.5, 0.9, 1.3, 1.7, etc.)
    min_duration = 500;  % Minimum 500 samples (0.5 seconds at 1000Hz) for steady state
    
    % Get unique speeds
    unique_speeds = unique(speed_vector);
    
    speeds = [];
    for test_speed = unique_speeds'
        % Count samples at this speed
        count = sum(speed_vector == test_speed);
        
        % Only include if sufficient duration and meaningful walking speed
        if count >= min_duration && test_speed >= 0.3 && test_speed <= 2.5
            speeds = [speeds; test_speed];
        end
    end
    
    % Sort speeds
    speeds = sort(speeds);
end

function expanded = expand_table_for_parquet(compact_table)
    % Expand table with array cells into individual rows
    % This converts from 1 row per stride (with 150-point arrays)
    % to 150 rows per stride (with scalar values)
    
    num_strides = height(compact_table);
    num_points = 150;
    total_rows = num_strides * num_points;
    
    fprintf('  Expanding %d strides to %d total rows...\n', num_strides, total_rows);
    
    % Pre-allocate arrays for efficiency
    subject = cell(total_rows, 1);
    task = cell(total_rows, 1);
    task_id = cell(total_rows, 1);
    task_info = cell(total_rows, 1);
    step = zeros(total_rows, 1);
    phase_ipsi = zeros(total_rows, 1);
    ankle_dorsiflexion_angle_ipsi_rad = zeros(total_rows, 1);
    knee_flexion_angle_ipsi_rad = zeros(total_rows, 1);
    hip_flexion_angle_ipsi_rad = zeros(total_rows, 1);
    ankle_dorsiflexion_moment_ipsi_Nm = zeros(total_rows, 1);
    knee_flexion_moment_ipsi_Nm = zeros(total_rows, 1);
    hip_flexion_moment_ipsi_Nm = zeros(total_rows, 1);
    
    % Process each stride
    row_idx = 1;
    for stride_idx = 1:num_strides
        if mod(stride_idx, 1000) == 0
            fprintf('    Processing stride %d/%d\n', stride_idx, num_strides);
        end
        
        stride = compact_table(stride_idx, :);
        
        % Expand each point in the stride
        for p = 1:num_points
            % Copy metadata (same for all points in stride)
            subject{row_idx} = stride.subject{1};
            task{row_idx} = stride.task{1};
            task_id{row_idx} = stride.task_id{1};
            task_info{row_idx} = stride.task_info{1};
            step(row_idx) = stride.step;
            
            % Extract point data from arrays
            phase_ipsi(row_idx) = stride.phase_ipsi{1}(p);
            ankle_dorsiflexion_angle_ipsi_rad(row_idx) = stride.ankle_dorsiflexion_angle_ipsi_rad{1}(p);
            knee_flexion_angle_ipsi_rad(row_idx) = stride.knee_flexion_angle_ipsi_rad{1}(p);
            hip_flexion_angle_ipsi_rad(row_idx) = stride.hip_flexion_angle_ipsi_rad{1}(p);
            ankle_dorsiflexion_moment_ipsi_Nm(row_idx) = stride.ankle_dorsiflexion_moment_ipsi_Nm{1}(p);
            knee_flexion_moment_ipsi_Nm(row_idx) = stride.knee_flexion_moment_ipsi_Nm{1}(p);
            hip_flexion_moment_ipsi_Nm(row_idx) = stride.hip_flexion_moment_ipsi_Nm{1}(p);
            
            row_idx = row_idx + 1;
        end
    end
    
    % Create output table from arrays
    fprintf('  Creating expanded table...\n');
    expanded = table(subject, task, task_id, task_info, step, phase_ipsi, ...
        ankle_dorsiflexion_angle_ipsi_rad, knee_flexion_angle_ipsi_rad, ...
        hip_flexion_angle_ipsi_rad, ankle_dorsiflexion_moment_ipsi_Nm, ...
        knee_flexion_moment_ipsi_Nm, hip_flexion_moment_ipsi_Nm);
end