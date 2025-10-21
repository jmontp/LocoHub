% Convert Gtech 2021 (CAMARGO_ET_AL_J_BIOMECH_DATASET) to standardized parquet format
% Direct conversion from raw data to phase-indexed (150 points per cycle) parquet
%
% Conventions (reflecting current implementation):
% 1) Knee flexion angle: Unconditionally negated (ipsi and contra) so flexion is positive.
% 2) Ankle dorsiflexion angle: No phase-0 offset removal; direct time interpolation, then velocity via gradient.
% 3) Knee flexion moment: Unconditionally negated (ipsi and contra) across all tasks; normalized by body mass.
% 4) Segment angles (sagittal plane):
%    - pelvis_sagittal_angle = pelvis_tilt (from data)
%    - trunk_sagittal_angle  = pelvis_sagittal_angle + lumbar_extension
%    - thigh_sagittal_angle_[ipsi|contra] = pelvis_sagittal_angle + hip_flexion
%    - shank_sagittal_angle_[ipsi|contra] = thigh_sagittal_angle_[ipsi|contra] - knee_flexion
%    - foot_sagittal_angle_[ipsi|contra]  = shank_sagittal_angle_[ipsi|contra] + ankle_angle
% 5) Velocities: Computed after interpolation (150 samples) using finite differences.
%
% Notes:
% - Ipsilateral leg is the first heel-striking leg within the segment; only that leg's strides are output (no duplicates).
% - GRF: Treadmill channels treat *_vy as vertical and *_vz as anterior–posterior; overground GRF is skipped; for stairs/ramps, per‑stride force-plate assignment uses early/late peak windows.
%
% KNOWN ISSUES:
% 1. Step Numbering: Step IDs are reused across different tasks (e.g., '001' appears in 
%    level_walking, stair_descent, etc.). This causes multiple strides to share the same ID.
%    Proper fix requires considering multiple subjects and inter-task relationships.
%
% 2. Stair Descent GRF Discontinuity: Vertical GRF for stair descent shows ~0.46 BW at 
%    stride start instead of near-zero. Likely due to force plate assignment or phase 
%    alignment issues. Requires deeper investigation of force plate timing and step-through
%    gait mechanics.
%
% TEST MODE: Set TEST_MODE=true to process only subjects in TEST_SUBJECTS.

clear all;
close all;


% Add utilities to path
addpath('utilities');

%% Configuration
NUM_POINTS = 150;  % Points per gait cycle
DATA_ROOT = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
OUTPUT_DIR = fullfile('..', '..', '..', 'converted_datasets');

% TEST MODE Configuration
TEST_MODE = false;  % Set to true for testing with limited subjects
TEST_SUBJECTS = {'AB06'};  % Subjects to use in test mode

% Set output filename based on mode
if TEST_MODE
    OUTPUT_FILE = 'gtech_2021_phase_test.parquet';
else
    OUTPUT_FILE = 'gtech_2021_phase_dirty.parquet';
end

% Create output directory if needed
if ~exist(OUTPUT_DIR, 'dir')
    mkdir(OUTPUT_DIR);
end

%% Load subject information
fprintf('Loading subject information...\n');
subjectInfo = load(fullfile(DATA_ROOT, 'SubjectInfo.mat'));
subjectInfo = subjectInfo.data;

%% Define subjects to process
% TEST_MODE and TEST_SUBJECTS are defined in Configuration section above

if TEST_MODE
    % Use test subjects only
    subjects_to_process = TEST_SUBJECTS;
    fprintf('TEST MODE: Processing only specified subjects\n');
else
    % Process all valid subjects
    % Exclude problematic subjects based on prior knowledge
    subjects_to_process = {};
    for i = 6:30
        if i == 22 || i == 26 || i == 27 || i == 29 || i == 100
            continue;  % Skip problematic subjects
        end
        subjects_to_process{end+1} = sprintf('AB%02d', i);
    end
    fprintf('FULL MODE: Processing all valid subjects\n');
end

fprintf('Will process %d subjects: %s\n', length(subjects_to_process), strjoin(subjects_to_process, ', '));

%% Initialize output table
output_table = table();

%% Process each subject
for subj_idx = 1:length(subjects_to_process)
    subject_code = subjects_to_process{subj_idx};
    subject_str = sprintf('GT21_%s', subject_code);
    
    fprintf('\n========================================\n');
    fprintf('Processing %s (%d/%d)\n', subject_code, subj_idx, length(subjects_to_process));
    fprintf('========================================\n');
    
    % Get subject mass for moment normalization
    subject_mass = subjectInfo.Weight(strcmp(subjectInfo.Subject, subject_code));
    if isempty(subject_mass)
        fprintf('  WARNING: No mass data for %s, skipping\n', subject_code);
        continue;
    end
    
    % Initialize trial counters for validation
    trial_counts = struct('treadmill_speeds', 0, 'levelground', 0, 'stair', 0, 'ramp', 0);
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
    [treadmill_rows, treadmill_speeds] = process_treadmill(date_path, subject_str, subject_mass);
    if ~isempty(treadmill_rows)
        subject_rows = [subject_rows; treadmill_rows];
        fprintf('  Added %d treadmill strides\n', height(treadmill_rows));
        trial_counts.treadmill_speeds = treadmill_speeds;
    end
    
    % 2. Process level ground data
    [levelground_rows, lg_trials] = process_levelground(date_path, subject_str, subject_mass);
    if ~isempty(levelground_rows)
        subject_rows = [subject_rows; levelground_rows];
        fprintf('  Added %d level ground strides\n', height(levelground_rows));
        trial_counts.levelground = lg_trials;
    end
    
    % 3. Process ramp data
    [ramp_rows, ramp_trials] = process_ramp(date_path, subject_str, subject_mass);
    if ~isempty(ramp_rows)
        subject_rows = [subject_rows; ramp_rows];
        fprintf('  Added %d ramp strides\n', height(ramp_rows));
        trial_counts.ramp = ramp_trials;
    end
    
    % 4. Process stair data
    [stair_rows, stair_trials] = process_stair(date_path, subject_str, subject_mass);
    if ~isempty(stair_rows)
        subject_rows = [subject_rows; stair_rows];
        fprintf('  Added %d stair strides\n', height(stair_rows));
        trial_counts.stair = stair_trials;
    end
    
    % Add subject data to main table
    if ~isempty(subject_rows)
        output_table = [output_table; subject_rows];
        fprintf('  Total strides for %s: %d\n', subject_code, height(subject_rows));
    else
        fprintf('  WARNING: No valid strides found for %s\n', subject_code);
    end
    
    % Report trial count validation
    fprintf('\n  === Trial Count Validation for %s ===\n', subject_code);
    fprintf('  Treadmill: %d unique speeds detected (expected: 28)\n', trial_counts.treadmill_speeds);
    fprintf('  Level-ground: %d trials (expected: 30)\n', trial_counts.levelground);
    fprintf('  Stair: %d trials (expected: 40)\n', trial_counts.stair);
    fprintf('  Ramp: %d trials (expected: 60)\n', trial_counts.ramp);
    
    % Warnings for missing trials
    if trial_counts.treadmill_speeds < 28
        fprintf('  ⚠ Missing %d treadmill speeds\n', 28 - trial_counts.treadmill_speeds);
    end
    if trial_counts.levelground < 30
        fprintf('  ⚠ Missing %d level-ground trials\n', 30 - trial_counts.levelground);
    end
    if trial_counts.stair < 40
        fprintf('  ⚠ Missing %d stair trials\n', 40 - trial_counts.stair);
    end
    if trial_counts.ramp < 60
        fprintf('  ⚠ Missing %d ramp trials\n', 60 - trial_counts.ramp);
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

function [rows, unique_speeds] = process_treadmill(date_path, subject_str, subject_mass)
    % Process treadmill walking data
    rows = table();
    unique_speeds = 0;
    detected_speeds = [];
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
        
        % Find steady-state speeds using improved threshold-based detection
        % Paper reports 28 speeds from 0.5 to 1.85 m/s in 0.05 m/s increments
        % Data actually contains up to 2.0 m/s, so we'll process all available
        target_speeds = 0.50:0.05:2.00;  % All speeds from 0.5 to 2.0 m/s
        tolerance = 0.025;  % Allow ±0.025 m/s (half increment) variation
        
        % Process each target speed
        for speed_val = target_speeds
            % Find regions within tolerance of target speed
            speed_mask = abs(speed_vec - speed_val) <= tolerance;
            
            % Find continuous regions
            transitions = diff([false; speed_mask; false]);
            region_starts = find(transitions == 1);
            region_ends = find(transitions == -1) - 1;
            
            % Process each continuous region
            for r = 1:length(region_starts)
                region_length = region_ends(r) - region_starts(r) + 1;
                
                % Need sufficient data for steady state (at least 5 seconds at 1000Hz for treadmill)
                if region_length < 5000
                    continue;
                end
                
                % Get time window for this region
                time_start = time_vec(region_starts(r));
                time_end = time_vec(region_ends(r));
                
                % Calculate actual mean speed in this region
                actual_speed = mean(speed_vec(region_starts(r):region_ends(r)));
                
                % Track unique speeds
                detected_speeds = [detected_speeds, actual_speed];
                
                % Extract strides for this segment
                task_info = sprintf('speed_m_s:%.2f,treadmill:true,surface:treadmill', actual_speed);
                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, 'level_walking', 'level', task_info, subject_mass);
                
                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                    fprintf('    Found %d strides at %.2f m/s (%.1f-%.1f sec)\n', ...
                        height(stride_rows), actual_speed, time_start, time_end);
                end
            end
        end
    end
    
    % Count unique speeds
    unique_speeds = length(unique(round(detected_speeds, 2)));
end

function [rows, trial_count] = process_levelground(date_path, subject_str, subject_mass)
    % Process level ground walking data and labeled transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'levelground');

    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    trial_count = length(trial_files);  % Count all trial files

    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;

        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        % Determine speed from filename (using paper-reported values)
        if contains(trial_name, 'slow')
            speed_val = 0.88;  % Paper: 0.88 ± 0.19 m/s
        elseif contains(trial_name, 'fast')
            speed_val = 1.45;  % Paper: 1.45 ± 0.27 m/s
        else
            speed_val = 1.17;  % normal - Paper: 1.17 ± 0.21 m/s
        end

        processed = false;
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))
            labels = trial_data.conditions.Label;
            header = trial_data.conditions.Header;
            target_labels = {'walk', 'turnccw', 'turncw', 'stand-walk', 'walk-stand'};

            for lbl_idx = 1:length(target_labels)
                label_name = target_labels{lbl_idx};
                segments = get_label_segments(labels, header, label_name, 50);
                if isempty(segments)
                    continue;
                end

                for seg_idx = 1:size(segments, 1)
                    time_start = segments(seg_idx, 1);
                    time_end = segments(seg_idx, 2);
                    [task, task_id, task_info] = map_levelground_label(label_name, speed_val);
                    if isempty(task)
                        continue;
                    end

                    stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                        subject_str, task, task_id, task_info, subject_mass);

                    if ~isempty(stride_rows)
                        rows = [rows; stride_rows];
                        processed = true;
                    end
                end
            end
        end

        % Fallback: treat entire trial as level walking if no labeled segments were processed
        if ~processed && isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
            time_start = trial_data.ik_offset.Header(1);
            time_end = trial_data.ik_offset.Header(end);
            task_info = sprintf('speed_m_s:%.2f,surface:overground,labels_missing:true', speed_val);
            stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                subject_str, 'level_walking', 'level', task_info, subject_mass);

            if ~isempty(stride_rows)
                rows = [rows; stride_rows];
            end
        end
    end
end
function [rows, trial_count] = process_ramp(date_path, subject_str, subject_mass)
    % Process ramp ascent/descent data, including transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'ramp');

    if ~exist(mode_path, 'dir')
        return;
    end

    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    trial_count = length(trial_files);  % Count all trial files

    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;

        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        % Default ramp angle (degrees)
        ramp_angle = NaN;
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'rampIncline'))
            ramp_angle = trial_data.conditions.rampIncline(1);
        end

        processed = false;
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))

            labels = trial_data.conditions.Label;
            header = trial_data.conditions.Header;
            target_labels = {'rampascent', 'walk-rampascent', 'rampascent-walk', ...
                             'rampdescent', 'walk-rampdescent', 'rampdescent-walk'};

            for lbl_idx = 1:length(target_labels)
                label_name = target_labels{lbl_idx};
                segments = get_label_segments(labels, header, label_name, 50);
                if isempty(segments)
                    continue;
                end

                for seg_idx = 1:size(segments, 1)
                    time_start = segments(seg_idx, 1);
                    time_end = segments(seg_idx, 2);
                    [task, task_id, task_info] = map_ramp_label(label_name, ramp_angle);
                    if isempty(task)
                        continue;
                    end

                    stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                        subject_str, task, task_id, task_info, subject_mass);

                    if ~isempty(stride_rows)
                        rows = [rows; stride_rows];
                        processed = true;
                    end
                end
            end
        end

        if ~processed
            % FALLBACK PROCESSING: No labels found or insufficient labeled segments
            if isnan(ramp_angle)
                fprintf('  WARNING: No ramp incline available for %s, skipping fallback\n', trial_name);
                continue;
            end

            if isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
                time_start = trial_data.ik_offset.Header(1);
                time_end = trial_data.ik_offset.Header(end);
                angle_label = round(ramp_angle, 1);

                if contains(lower(trial_name), 'ascent') || contains(lower(trial_name), 'walk-rampascent')
                    task = 'incline_walking';
                    task_id = sprintf('incline_%.1fdeg', angle_label);
                    task_info = sprintf('incline_deg:%.1f,surface:overground,fallback:true', angle_label);
                elseif contains(lower(trial_name), 'descent') || contains(lower(trial_name), 'walk-rampdescent')
                    task = 'decline_walking';
                    task_id = sprintf('decline_%.1fdeg', -angle_label);
                    task_info = sprintf('incline_deg:%.1f,surface:overground,fallback:true', -angle_label);
                else
                    % Unknown direction, assume ascent by default
                    task = 'incline_walking';
                    task_id = sprintf('incline_%.1fdeg', angle_label);
                    task_info = sprintf('incline_deg:%.1f,surface:overground,fallback:true', angle_label);
                end

                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, task, task_id, task_info, subject_mass);

                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end
function [rows, trial_count] = process_stair(date_path, subject_str, subject_mass)
    % Process stair ascent/descent data and transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'stair');

    if ~exist(mode_path, 'dir')
        return;
    end

    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    trial_count = length(trial_files);  % Count all trial files

    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;

        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        % Extract stair height (stored in inches, convert to meters)
        stair_height_m = NaN;
        if isfield(trial_data, 'stairHeight')
            stair_height_in = trial_data.stairHeight;
            stair_height_m = round((stair_height_in * 0.0254), 3);
            fprintf('  Processing stair trial: height=%.3fm (%.0f inches)\n', stair_height_m, stair_height_in);
        else
            fprintf('  WARNING: No stair height found, using default 0.102 m (4 inches)\n');
            stair_height_m = 0.102;
        end

        processed = false;
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
           any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'))

            labels = trial_data.conditions.Label;
            header = trial_data.conditions.Header;
            target_labels = {'stairascent', 'walk-stairascent', 'stairascent-walk', ...
                             'stairdescent', 'walk-stairdescent', 'stairdescent-walk'};

            for lbl_idx = 1:length(target_labels)
                label_name = target_labels{lbl_idx};
                segments = get_label_segments(labels, header, label_name, 50);
                if isempty(segments)
                    continue;
                end

                for seg_idx = 1:size(segments, 1)
                    time_start = segments(seg_idx, 1);
                    time_end = segments(seg_idx, 2);
                    [task, task_id, task_info] = map_stair_label(label_name, stair_height_m);
                    if isempty(task)
                        continue;
                    end

                    stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                        subject_str, task, task_id, task_info, subject_mass);

                    if ~isempty(stride_rows)
                        rows = [rows; stride_rows];
                        processed = true;
                    end
                end
            end
        end

        if ~processed
            % FALLBACK PROCESSING: No labels found or insufficient segments
            if isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
                time_start = trial_data.ik_offset.Header(1);
                time_end = trial_data.ik_offset.Header(end);

                if contains(lower(trial_name), 'ascent')
                    task = 'stair_ascent';
                    task_id = 'stair_ascent';
                    task_info = sprintf('step_height_m:%.3f,surface:stairs,fallback:true', stair_height_m);
                elseif contains(lower(trial_name), 'descent')
                    task = 'stair_descent';
                    task_id = 'stair_descent';
                    task_info = sprintf('step_height_m:%.3f,surface:stairs,fallback:true', stair_height_m);
                else
                    fprintf('  WARNING: Stair file with unknown pattern, skipping fallback: %s\n', trial_name);
                    continue;
                end

                stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                    subject_str, task, task_id, task_info, subject_mass);

                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end
function segments = get_label_segments(labels, header, target_label, min_samples)
    % Utility to find contiguous label regions
    if nargin < 4
        min_samples = 1;
    end

    segments = [];
    if isempty(labels) || isempty(header)
        return;
    end

    if ~iscell(labels)
        labels = cellstr(string(labels));
    end

    mask = strcmp(labels, target_label);
    if sum(mask) < min_samples
        return;
    end

    mask = mask(:);
    header = header(:);

    transitions = diff([false; mask; false]);
    starts = find(transitions == 1);
    ends = find(transitions == -1) - 1;

    if isempty(starts)
        return;
    end

    segments = [header(starts), header(ends)];
    durations = segments(:, 2) - segments(:, 1);
    segments = segments(durations > 0.05, :);  % minimum meaningful duration
end

function [task, task_id, task_info] = map_levelground_label(label_name, speed_val)
    % Map level ground labels to standardized task metadata
    task = '';
    task_id = '';
    task_info = '';

    base_info = sprintf('speed_m_s:%.2f,surface:overground', speed_val);

    switch label_name
        case 'walk'
            task = 'level_walking';
            task_id = 'level';
            task_info = base_info;
        case 'turnccw'
            task = 'transition';
            task_id = 'turn_left';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:level_walking,turn_direction:left', base_info);
        case 'turncw'
            task = 'transition';
            task_id = 'turn_right';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:level_walking,turn_direction:right', base_info);
        case 'stand-walk'
            task = 'transition';
            task_id = 'stand_to_walk';
            task_info = sprintf('%s,gait_transition:true,transition_from:stand,transition_to:level_walking', base_info);
        case 'walk-stand'
            task = 'transition';
            task_id = 'walk_to_stand';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:stand', base_info);
    end
end

function [task, task_id, task_info] = map_ramp_label(label_name, ramp_angle)
    % Map ramp labels to standardized task metadata
    task = '';
    task_id = '';
    task_info = '';

    if isnan(ramp_angle)
        return;
    end

    angle_up = round(ramp_angle, 1);
    angle_down = -angle_up;
    ascent_info = sprintf('incline_deg:%.1f,surface:overground', angle_up);
    descent_info = sprintf('incline_deg:%.1f,surface:overground', angle_down);

    switch label_name
        case 'rampascent'
            task = 'incline_walking';
            task_id = sprintf('incline_%.1fdeg', angle_up);
            task_info = ascent_info;
        case 'walk-rampascent'
            task = 'transition';
            task_id = 'walk_to_ramp_ascent';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:incline_walking', ascent_info);
        case 'rampascent-walk'
            task = 'transition';
            task_id = 'ramp_ascent_to_walk';
            task_info = sprintf('%s,gait_transition:true,transition_from:incline_walking,transition_to:level_walking', ascent_info);
        case 'rampdescent'
            task = 'decline_walking';
            task_id = sprintf('decline_%.1fdeg', angle_down);
            task_info = descent_info;
        case 'walk-rampdescent'
            task = 'transition';
            task_id = 'walk_to_ramp_descent';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:decline_walking', descent_info);
        case 'rampdescent-walk'
            task = 'transition';
            task_id = 'ramp_descent_to_walk';
            task_info = sprintf('%s,gait_transition:true,transition_from:decline_walking,transition_to:level_walking', descent_info);
    end
end

function [task, task_id, task_info] = map_stair_label(label_name, stair_height_m)
    % Map stair labels to standardized task metadata
    task = '';
    task_id = '';
    task_info = '';

    if isnan(stair_height_m)
        stair_height_m = 0.102;  % default four-inch step
    end

    height_val = round(stair_height_m, 3);
    base_info = sprintf('step_height_m:%.3f,surface:stairs', height_val);

    switch label_name
        case 'stairascent'
            task = 'stair_ascent';
            task_id = 'stair_ascent';
            task_info = base_info;
        case 'walk-stairascent'
            task = 'transition';
            task_id = 'walk_to_stair_ascent';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent', base_info);
        case 'stairascent-walk'
            task = 'transition';
            task_id = 'stair_ascent_to_walk';
            task_info = sprintf('%s,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking', base_info);
        case 'stairdescent'
            task = 'stair_descent';
            task_id = 'stair_descent';
            task_info = base_info;
        case 'walk-stairdescent'
            task = 'transition';
            task_id = 'walk_to_stair_descent';
            task_info = sprintf('%s,gait_transition:true,transition_from:level_walking,transition_to:stair_descent', base_info);
        case 'stairdescent-walk'
            task = 'transition';
            task_id = 'stair_descent_to_walk';
            task_info = sprintf('%s,gait_transition:true,transition_from:stair_descent,transition_to:level_walking', base_info);
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
            
            % Also copy stairHeight field if it exists (for stair trials)
            if isfield(temp, 'stairHeight')
                trial_data.stairHeight = temp.stairHeight;
            end
        end
        
        % Load IK (inverse kinematics)
        ik_file = fullfile(mode_path, 'ik_offset', trial_name);
        if exist(ik_file, 'file')
            temp = load(ik_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.ik_offset = temp.data;
            else
                trial_data.ik_offset = temp;
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
        else
            error('Missing right gait cycle file: %s', gc_file);
        end
        
        % Load left gait cycle events (mandatory for bilateral processing)
        gc_file_left = fullfile(mode_path, 'gcLeft', trial_name);
        if exist(gc_file_left, 'file')
            temp = load(gc_file_left);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.gcLeft = temp.data;
            else
                trial_data.gcLeft = temp;
            end
        else
            error('Missing left gait cycle file: %s', gc_file_left);
        end
        
        % Load FP (force plate) data for GRF
        fp_file = fullfile(mode_path, 'fp', trial_name);
        if exist(fp_file, 'file')
            temp = load(fp_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.fp = temp.data;
            else
                trial_data.fp = temp;
            end
        end
        
    catch ME
        warning('Failed to load trial %s: %s', trial_name, ME.message);
        trial_data = [];
    end
end

function rows = extract_and_process_strides(trial_data, time_start, time_end, ...
    subject_str, task, task_id, task_info, subject_mass)
    % NEW APPROACH: Single-leg processing based on first heel strike
    % The leg that heel strikes first becomes ipsilateral for entire trial
    
    % Determine which leg heel strikes first in this trial segment
    [first_leg, first_hs_time] = determine_first_heel_strike(trial_data, time_start, time_end);
    
    if isempty(first_leg)
        fprintf('  No heel strikes found in time window %.3f-%.3f sec\n', time_start, time_end);
        rows = table();
        return;
    end
    
    fprintf('  First heel strike: %s leg at %.3f sec\n', first_leg, first_hs_time);
    
    % Process ONLY with the first heel-striking leg as ipsilateral
    % This eliminates duplicate strides and provides consistent force plate assignment
    rows = extract_and_process_strides_single_leg(trial_data, time_start, time_end, ...
        subject_str, task, task_id, task_info, subject_mass, first_leg);
end

function rows = extract_and_process_strides_single_leg(trial_data, time_start, time_end, ...
    subject_str, task, task_id, task_info, subject_mass, leg_side)
    % Extract strides from time window and process to standard format for single leg
    
    rows = [];  % Will collect complete stride rows
    NUM_POINTS = 150;  % Points per gait cycle
    
    % Check we have minimum required data (both legs mandatory for bilateral processing)
    if ~isfield(trial_data, 'gcRight') || ~istable(trial_data.gcRight) || ...
       ~isfield(trial_data, 'gcLeft') || ~istable(trial_data.gcLeft) || ...
       ~isfield(trial_data, 'ik_offset') || ~istable(trial_data.ik_offset) || ...
       ~isfield(trial_data, 'id') || ~istable(trial_data.id)
        error('Missing required data fields for bilateral processing');
    end
    
    % Select appropriate gait cycle data based on leg_side
    if strcmp(leg_side, 'right')
        gc_data = trial_data.gcRight;
    else
        gc_data = trial_data.gcLeft;
    end
    
    % Get time indices for the window of interest
    gc_time = gc_data.Header;
    window_indices = find(gc_time >= time_start & gc_time <= time_end);
    
    if isempty(window_indices)
        rows = table();
        return;
    end
    
    % HeelStrike contains gait cycle percentages (0-100%)
    % Find heel strikes as falling edges where percentage drops to 0
    heel_strike_pct = gc_data.HeelStrike;
    
    % Find falling edges (where HeelStrike == 0) within our window
    % Using the utility function from old code
    hs_indices = findFallingEdges_onlyInSection(heel_strike_pct == 0, window_indices);
    
    if length(hs_indices) < 2
        rows = table();
        return;  % Need at least 2 heel strikes for one stride
    end
    
    % Process each stride (heel strike to heel strike)
    for s = 1:(length(hs_indices)-1)
        % Fix off-by-one error: include the actual heel strike sample
        % hs_indices contains the index where HeelStrike becomes 0, 
        % but we want the index where HeelStrike is still 1 (actual heel strike)
        stride_start_idx = max(1, hs_indices(s) - 1);  % Include HS sample, clamp to bounds
        stride_end_idx = max(1, hs_indices(s+1) - 2);  % End just before next HS sample
        
        % Get the gait cycle percentages for this stride
        stride_pct = heel_strike_pct(stride_start_idx:stride_end_idx);
        stride_time = gc_time(stride_start_idx:stride_end_idx);
        
        % Skip if stride is too short or doesn't progress properly
        if length(stride_pct) < 10 || max(stride_pct) < 50
            continue;
        end
        
        % Use the full stride including 0% heel strike point
        valid_pct_idx = 1;  % Start from beginning (includes 0%)
        
        % Get time bounds for this stride
        stride_start_time = stride_time(1);
        stride_end_time = stride_time(end);
        
        % Calculate stride duration and phase rate (phase time derivative)
        stride_duration_s = stride_end_time - stride_start_time;
        phase_ipsi_dot_value = 100 / stride_duration_s;  % %/second
        
        % Get indices for this stride in IK and ID data
        ik_mask = (trial_data.ik_offset.Header >= stride_start_time) & (trial_data.ik_offset.Header <= stride_end_time);
        id_mask = (trial_data.id.Header >= stride_start_time) & (trial_data.id.Header <= stride_end_time);
        
        if sum(ik_mask) < 10 || sum(id_mask) < 10
            continue;  % Not enough data points
        end
        
        % Phase (0-100% of gait cycle)
        target_pct = linspace(0, 100, NUM_POINTS)';
        
        % Initialize data arrays for this stride
        stride_data = struct();
        stride_data.phase_ipsi = target_pct;
        stride_data.phase_ipsi_dot = repmat(phase_ipsi_dot_value, NUM_POINTS, 1);  % Constant for all 150 points
        
        % Process kinematics (angles in degrees, convert to radians)
        deg2rad = pi/180;
        
        % For interpolation, we need to map from gait cycle percentage to data
        % Use the valid portion of the stride percentage data
        valid_stride_pct = stride_pct(valid_pct_idx:end);
        valid_stride_time = stride_time(valid_pct_idx:end);
        
        % Determine variable names based on leg_side
        if strcmp(leg_side, 'right')
            ipsi_ankle_var = 'ankle_angle_r';
            contra_ankle_var = 'ankle_angle_l';
        else
            ipsi_ankle_var = 'ankle_angle_l';
            contra_ankle_var = 'ankle_angle_r';
        end
        
        % Ankle dorsiflexion angle - IPSILATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, ipsi_ankle_var))
            angle_data = trial_data.ik_offset.(ipsi_ankle_var)(ik_mask);
            ik_time = trial_data.ik_offset.Header(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            target_times = linspace(stride_start_time, stride_end_time, NUM_POINTS);
            ankle_data = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            ankle_velocity = gradient(ankle_data) * 150 / stride_duration_s;
            
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = ankle_data;
            stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = ankle_velocity;
        else
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Ankle dorsiflexion angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_ankle_var))
            angle_data = trial_data.ik_offset.(contra_ankle_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            ankle_data_contra = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            ankle_velocity_contra = gradient(ankle_data_contra) * 150 / stride_duration_s;
            
            stride_data.ankle_dorsiflexion_angle_contra_rad = ankle_data_contra;
            stride_data.ankle_dorsiflexion_velocity_contra_rad_s = ankle_velocity_contra;
        else
            stride_data.ankle_dorsiflexion_angle_contra_rad = zeros(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_velocity_contra_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Determine knee variable names based on leg_side
        if strcmp(leg_side, 'right')
            ipsi_knee_var = 'knee_angle_r';
            contra_knee_var = 'knee_angle_l';
        else
            ipsi_knee_var = 'knee_angle_l';
            contra_knee_var = 'knee_angle_r';
        end
        
        % Knee angle with per-stride sign detection - IPSILATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, ipsi_knee_var))
            angle_data = trial_data.ik_offset.(ipsi_knee_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            knee_data = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            
            % FIX: Flip knee angle if needed (Gtech dataset has inverted knee flexion)
            knee_data = -knee_data;
            
            knee_velocity = gradient(knee_data) * 150 / stride_duration_s;
            
            stride_data.knee_flexion_angle_ipsi_rad = knee_data;
            stride_data.knee_flexion_velocity_ipsi_rad_s = knee_velocity;
        else
            stride_data.knee_flexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
            stride_data.knee_flexion_velocity_ipsi_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Knee angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_knee_var))
            angle_data = trial_data.ik_offset.(contra_knee_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            knee_data_contra = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            
            % FIX: Flip knee angle if needed (Gtech dataset has inverted knee flexion)
            knee_data_contra = -knee_data_contra;
            
            knee_velocity_contra = gradient(knee_data_contra) * 150 / stride_duration_s;
            
            stride_data.knee_flexion_angle_contra_rad = knee_data_contra;
            stride_data.knee_flexion_velocity_contra_rad_s = knee_velocity_contra;
        else
            stride_data.knee_flexion_angle_contra_rad = zeros(NUM_POINTS, 1);
            stride_data.knee_flexion_velocity_contra_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Determine hip variable names based on leg_side
        if strcmp(leg_side, 'right')
            ipsi_hip_var = 'hip_flexion_r';
            contra_hip_var = 'hip_flexion_l';
        else
            ipsi_hip_var = 'hip_flexion_l';
            contra_hip_var = 'hip_flexion_r';
        end
        
        % Hip angle - IPSILATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, ipsi_hip_var))
            angle_data = trial_data.ik_offset.(ipsi_hip_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            stride_data.hip_flexion_angle_ipsi_rad = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            stride_data.hip_flexion_velocity_ipsi_rad_s = gradient(stride_data.hip_flexion_angle_ipsi_rad) * 150 / stride_duration_s;
        else
            stride_data.hip_flexion_angle_ipsi_rad = zeros(NUM_POINTS, 1);
            stride_data.hip_flexion_velocity_ipsi_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Hip angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_hip_var))
            angle_data = trial_data.ik_offset.(contra_hip_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            stride_data.hip_flexion_angle_contra_rad = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            stride_data.hip_flexion_velocity_contra_rad_s = gradient(stride_data.hip_flexion_angle_contra_rad) * 150 / stride_duration_s;
        else
            stride_data.hip_flexion_angle_contra_rad = zeros(NUM_POINTS, 1);
            stride_data.hip_flexion_velocity_contra_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Calculate segment angles from kinematic chain
        % Pelvis sagittal angle (from pelvis tilt)
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, 'pelvis_tilt'))
            angle_data = trial_data.ik_offset.pelvis_tilt(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            stride_data.pelvis_sagittal_angle_rad = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            stride_data.pelvis_sagittal_velocity_rad_s = gradient(stride_data.pelvis_sagittal_angle_rad) * 150 / stride_duration_s;
        else
            stride_data.pelvis_sagittal_angle_rad = zeros(NUM_POINTS, 1);
            stride_data.pelvis_sagittal_velocity_rad_s = zeros(NUM_POINTS, 1);
        end
        
        % Trunk sagittal angle (pelvis + lumbar extension)
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, 'lumbar_extension'))
            lumbar_data = trial_data.ik_offset.lumbar_extension(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            lumbar_interp = interp1(ik_time, lumbar_data, target_times, 'linear') * deg2rad;
            stride_data.trunk_sagittal_angle_rad = stride_data.pelvis_sagittal_angle_rad + lumbar_interp;
            stride_data.trunk_sagittal_velocity_rad_s = gradient(stride_data.trunk_sagittal_angle_rad) * 150 / stride_duration_s;
        else
            stride_data.trunk_sagittal_angle_rad = stride_data.pelvis_sagittal_angle_rad;  % Same as pelvis if no lumbar
            stride_data.trunk_sagittal_velocity_rad_s = stride_data.pelvis_sagittal_velocity_rad_s;
        end
        
        % Thigh sagittal angle - IPSILATERAL (pelvis + hip flexion)
        stride_data.thigh_sagittal_angle_ipsi_rad = stride_data.pelvis_sagittal_angle_rad + stride_data.hip_flexion_angle_ipsi_rad;
        stride_data.thigh_sagittal_velocity_ipsi_rad_s = stride_data.pelvis_sagittal_velocity_rad_s + stride_data.hip_flexion_velocity_ipsi_rad_s;
        
        % Thigh sagittal angle - CONTRALATERAL
        stride_data.thigh_sagittal_angle_contra_rad = stride_data.pelvis_sagittal_angle_rad + stride_data.hip_flexion_angle_contra_rad;
        stride_data.thigh_sagittal_velocity_contra_rad_s = stride_data.pelvis_sagittal_velocity_rad_s + stride_data.hip_flexion_velocity_contra_rad_s;
        
        % Shank sagittal angle - IPSILATERAL (thigh - knee flexion)
        stride_data.shank_sagittal_angle_ipsi_rad = stride_data.thigh_sagittal_angle_ipsi_rad - stride_data.knee_flexion_angle_ipsi_rad;
        stride_data.shank_sagittal_velocity_ipsi_rad_s = stride_data.thigh_sagittal_velocity_ipsi_rad_s - stride_data.knee_flexion_velocity_ipsi_rad_s;
        
        % Shank sagittal angle - CONTRALATERAL
        stride_data.shank_sagittal_angle_contra_rad = stride_data.thigh_sagittal_angle_contra_rad - stride_data.knee_flexion_angle_contra_rad;
        stride_data.shank_sagittal_velocity_contra_rad_s = stride_data.thigh_sagittal_velocity_contra_rad_s - stride_data.knee_flexion_velocity_contra_rad_s;
        
        % Foot sagittal angle - IPSILATERAL (shank + ankle angle)
        stride_data.foot_sagittal_angle_ipsi_rad = stride_data.shank_sagittal_angle_ipsi_rad + stride_data.ankle_dorsiflexion_angle_ipsi_rad;
        stride_data.foot_sagittal_velocity_ipsi_rad_s = stride_data.shank_sagittal_velocity_ipsi_rad_s + stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s;
        
        % Foot sagittal angle - CONTRALATERAL
        stride_data.foot_sagittal_angle_contra_rad = stride_data.shank_sagittal_angle_contra_rad + stride_data.ankle_dorsiflexion_angle_contra_rad;
        stride_data.foot_sagittal_velocity_contra_rad_s = stride_data.shank_sagittal_velocity_contra_rad_s + stride_data.ankle_dorsiflexion_velocity_contra_rad_s;
        
        % Process kinetics (moments, normalize by body mass)
        id_time = trial_data.id.Header(id_mask);
        
        % Determine moment variable names based on leg_side
        if strcmp(leg_side, 'right')
            ipsi_ankle_moment_var = 'ankle_angle_r_moment';
            contra_ankle_moment_var = 'ankle_angle_l_moment';
        else
            ipsi_ankle_moment_var = 'ankle_angle_l_moment';
            contra_ankle_moment_var = 'ankle_angle_r_moment';
        end
        
        % Ankle dorsiflexion moment - IPSILATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, ipsi_ankle_moment_var))
            moment_data = trial_data.id.(ipsi_ankle_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Ankle dorsiflexion moment - CONTRALATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, contra_ankle_moment_var))
            moment_data = trial_data.id.(contra_ankle_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Determine knee and hip moment variable names based on leg_side
        if strcmp(leg_side, 'right')
            ipsi_knee_moment_var = 'knee_angle_r_moment';
            contra_knee_moment_var = 'knee_angle_l_moment';
            ipsi_hip_moment_var = 'hip_flexion_r_moment';
            contra_hip_moment_var = 'hip_flexion_l_moment';
        else
            ipsi_knee_moment_var = 'knee_angle_l_moment';
            contra_knee_moment_var = 'knee_angle_r_moment';
            ipsi_hip_moment_var = 'hip_flexion_l_moment';
            contra_hip_moment_var = 'hip_flexion_r_moment';
        end
        
        % Knee flexion moment with stair ascent and decline walking fixes - IPSILATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, ipsi_knee_moment_var))
            moment_data = trial_data.id.(ipsi_knee_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            knee_moment = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
            
            % Always flip knee moment for consistent convention across all tasks
            knee_moment = -knee_moment;
            
            stride_data.knee_flexion_moment_ipsi_Nm_kg = knee_moment;
        else
            stride_data.knee_flexion_moment_ipsi_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Knee flexion moment - CONTRALATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, contra_knee_moment_var))
            moment_data = trial_data.id.(contra_knee_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            knee_moment_contra = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
            
            % Always flip knee moment for consistent convention across all tasks
            knee_moment_contra = -knee_moment_contra;
            
            stride_data.knee_flexion_moment_contra_Nm_kg = knee_moment_contra;
        else
            stride_data.knee_flexion_moment_contra_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Hip flexion moment - IPSILATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, ipsi_hip_moment_var))
            moment_data = trial_data.id.(ipsi_hip_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_moment_ipsi_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.hip_flexion_moment_ipsi_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Hip flexion moment - CONTRALATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, contra_hip_moment_var))
            moment_data = trial_data.id.(contra_hip_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_moment_contra_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.hip_flexion_moment_contra_Nm_kg = zeros(NUM_POINTS, 1);
        end
        
        % Process Ground Reaction Forces (GRF) - weight normalized
        if isfield(trial_data, 'fp') && istable(trial_data.fp)
            fp_time = trial_data.fp.Header;
            
            % Determine which force plate variables to use based on task and leg
            treadmill_task = contains(task_info, 'treadmill:true');
            stair_ramp_task = contains(task, 'stair') || contains(task, 'incline') || contains(task, 'decline');
            
            if treadmill_task
                % For treadmill: use dedicated left/right channels
                % CORRECTED coordinate mapping based on data analysis
                % Data analysis showed: anterior_grf has vertical-like values, vertical_grf has anterior-like values
                if strcmp(leg_side, 'right')
                    % Right leg ipsilateral - SWAPPED vy and vz based on data analysis
                    ipsi_vx_var = 'Treadmill_R_vx';  % Medial-lateral (unchanged)
                    ipsi_vy_var = 'Treadmill_R_vy';  % Vertical GRF (data shows this has vertical-like range)
                    ipsi_vz_var = 'Treadmill_R_vz';  % Anterior-posterior GRF (data shows this has anterior-like range)
                    contra_vx_var = 'Treadmill_L_vx';
                    contra_vy_var = 'Treadmill_L_vy';  % Vertical GRF
                    contra_vz_var = 'Treadmill_L_vz';  % Anterior-posterior GRF
                else
                    % Left leg ipsilateral - SWAPPED vy and vz based on data analysis
                    ipsi_vx_var = 'Treadmill_L_vx';  % Medial-lateral (unchanged)
                    ipsi_vy_var = 'Treadmill_L_vy';  % Vertical GRF (data shows this has vertical-like range)
                    ipsi_vz_var = 'Treadmill_L_vz';  % Anterior-posterior GRF (data shows this has anterior-like range)
                    contra_vx_var = 'Treadmill_R_vx';
                    contra_vy_var = 'Treadmill_R_vy';  % Vertical GRF
                    contra_vz_var = 'Treadmill_R_vz';  % Anterior-posterior GRF
                end
            elseif stair_ramp_task
                % NEW ALGORITHM: Heel strike + 200ms for force plate assignment
                % Works for stairs, ramps, and could be extended to all tasks
                stride_start_time = valid_stride_time(1);  % Heel strike time
                
                % Find available force plates
                available_fps = {};
                for test_fp = {'FP1', 'FP2', 'FP3', 'FP4', 'FP5', 'FP6'}
                    vy_var = [test_fp{1} '_vy'];
                    if any(strcmp(trial_data.fp.Properties.VariableNames, vy_var))
                        available_fps{end+1} = test_fp{1};
                    end
                end
                fp_names = available_fps;
                
                % HEEL STRIKE + 200ms/800ms ALGORITHM
                % Check force plates 200ms after ipsilateral heel strike for ipsi
                % Contralateral GRF will be left as NaN for now
                hs_check_time = stride_start_time + 0.2;  % 200ms after heel strike
                
                % Find indices in force plate data for check time
                check_idx = find(fp_time >= hs_check_time, 1, 'first');
                
                % Variables for force plate assignment
                best_fp_ipsi = '';
                max_force_at_check = 0;
                
                if ~isempty(check_idx)
                    % Find force plate with maximum force at heel strike + 200ms
                    fprintf('  DEBUG [HS+200ms]: Checking at time %.3f (HS at %.3f)\n', hs_check_time, stride_start_time);
                    
                    % Check each force plate at the check time
                    for fp = fp_names
                        vy_var = [fp{1} '_vy'];
                        
                        % Get force at check time (heel strike + 200ms)
                        force_at_check = abs(trial_data.fp.(vy_var)(check_idx));
                        
                        fprintf('  DEBUG [HS+200ms]: %s - Force at check: %.1f N\n', fp{1}, force_at_check);
                        
                        % Find plate with maximum force
                        if force_at_check > max_force_at_check
                            max_force_at_check = force_at_check;
                            best_fp_ipsi = fp{1};
                        end
                    end
                    
                    % Assign ipsilateral force plate if significant force found
                    if max_force_at_check > 200  % 200N threshold
                        fprintf('  DEBUG [HS+200ms]: Assigned %s to IPSI (force: %.1f N)\n', best_fp_ipsi, max_force_at_check);
                        
                        % Set ipsilateral force plate variables
                        ipsi_vx_var = [best_fp_ipsi '_vx'];
                        ipsi_vy_var = [best_fp_ipsi '_vy'];
                        ipsi_vz_var = [best_fp_ipsi '_vz'];
                        
                        % Leave contralateral GRF as NaN for now
                        contra_vx_var = '';
                        contra_vy_var = '';
                        contra_vz_var = '';
                        
                    else
                        fprintf('  DEBUG [HS+200ms]: No significant force at check time (max: %.1f N)\n', max_force_at_check);
                        % Set all GRF to NaN for this stride
                        ipsi_vx_var = '';
                        ipsi_vy_var = '';
                        ipsi_vz_var = '';
                        contra_vx_var = '';
                        contra_vy_var = '';
                        contra_vz_var = '';
                    end
                else
                    fprintf('  DEBUG [HS+200ms]: No force plate data at check time\n');
                    % Set all GRF to NaN for this stride
                    ipsi_vx_var = '';
                    ipsi_vy_var = '';
                    ipsi_vz_var = '';
                    contra_vx_var = '';
                    contra_vy_var = '';
                    contra_vz_var = '';
                end
            else
                % For overground level walking: skip GRF due to 50% phase offset issue
                % Combined force plates can't distinguish which foot is on the plate
                ipsi_vx_var = '';  % Skip GRF processing
                ipsi_vy_var = '';
                ipsi_vz_var = '';
                contra_vx_var = '';
                contra_vy_var = '';
                contra_vz_var = '';
            end
            
            % Process ipsilateral GRF - FIXED: Direct time interpolation like kinematics
            if ~isempty(ipsi_vy_var) && any(strcmp(trial_data.fp.Properties.VariableNames, ipsi_vy_var))
                % Vertical GRF (ipsilateral) - FIXED: use vy_var which has vertical-like data
                vy_data = trial_data.fp.(ipsi_vy_var);
                
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Replace double interpolation with single direct interpolation
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vy_data, target_times, 'linear', NaN);
                
                % DEBUG: Print GRF statistics for stair tasks
                if stair_ramp_task
                    raw_max = max(abs(vy_data));
                    interp_max = max(abs(grf_interpolated));
                    normalized_max = interp_max / (subject_mass * 9.81);
                    fprintf('  DEBUG [Stair GRF]: Vertical GRF - Raw max: %.1f N, Interp max: %.1f N, Normalized max: %.2f BW\n', ...
                        raw_max, interp_max, normalized_max);
                end
                
                % Normalize by weight (divide by mass * 9.81)
                stride_data.vertical_grf_ipsi_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.vertical_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            end
            
            if ~isempty(ipsi_vz_var) && any(strcmp(trial_data.fp.Properties.VariableNames, ipsi_vz_var))
                % Anterior-posterior GRF (ipsilateral) - FIXED: use vz_var which has anterior-like data
                vz_data = trial_data.fp.(ipsi_vz_var);
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vz_data, target_times, 'linear', NaN);
                stride_data.anterior_grf_ipsi_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.anterior_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            end
            
            if ~isempty(ipsi_vx_var) && any(strcmp(trial_data.fp.Properties.VariableNames, ipsi_vx_var))
                % Medial-lateral GRF (ipsilateral)
                vx_data = trial_data.fp.(ipsi_vx_var);
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vx_data, target_times, 'linear', NaN);
                
                % Lateral GRF sign: keep global Right+ convention across all tasks.
                % Do not flip sign based on task or leg.
                
                stride_data.lateral_grf_ipsi_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.lateral_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            end
            
            % Process contralateral GRF - FIXED: Direct time interpolation like kinematics
            if ~isempty(contra_vy_var) && any(strcmp(trial_data.fp.Properties.VariableNames, contra_vy_var))
                % Vertical GRF (contralateral) - FIXED: use vy_var which has vertical-like data
                vy_data = trial_data.fp.(contra_vy_var);
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vy_data, target_times, 'linear', NaN);
                stride_data.vertical_grf_contra_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.vertical_grf_contra_BW = NaN(NUM_POINTS, 1);
            end
            
            if ~isempty(contra_vz_var) && any(strcmp(trial_data.fp.Properties.VariableNames, contra_vz_var))
                % Anterior-posterior GRF (contralateral) - FIXED: use vz_var which has anterior-like data
                vz_data = trial_data.fp.(contra_vz_var);
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vz_data, target_times, 'linear', NaN);
                stride_data.anterior_grf_contra_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.anterior_grf_contra_BW = NaN(NUM_POINTS, 1);
            end
            
            if ~isempty(contra_vx_var) && any(strcmp(trial_data.fp.Properties.VariableNames, contra_vx_var))
                % Medial-lateral GRF (contralateral)
                vx_data = trial_data.fp.(contra_vx_var);
                % CRITICAL FIX: Use direct time interpolation (same as kinematics)
                % Use NaN instead of extrapolation to avoid false GRF in swing phase
                grf_interpolated = interp1(fp_time, vx_data, target_times, 'linear', NaN);
                
                % Lateral GRF sign: keep global Right+ convention across all tasks.
                % Do not flip sign based on task or leg.
                
                stride_data.lateral_grf_contra_BW = grf_interpolated / (subject_mass * 9.81);
            else
                stride_data.lateral_grf_contra_BW = NaN(NUM_POINTS, 1);
            end
        else
            % No force plate data available - fill with NaN
            stride_data.vertical_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            stride_data.anterior_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            stride_data.lateral_grf_ipsi_BW = NaN(NUM_POINTS, 1);
            stride_data.vertical_grf_contra_BW = NaN(NUM_POINTS, 1);
            stride_data.anterior_grf_contra_BW = NaN(NUM_POINTS, 1);
            stride_data.lateral_grf_contra_BW = NaN(NUM_POINTS, 1);
        end
        
        % CHECK FOR SWAPPED GRF ASSIGNMENT
        % Detect if ipsi/contra GRF are swapped based on physiological impossibility
        % Ipsilateral foot should have near-zero GRF during swing phase (60-100%)
        if ~all(isnan(stride_data.vertical_grf_ipsi_BW)) && ~all(isnan(stride_data.vertical_grf_contra_BW))
            % Define phase windows for checking
            early_stance_idx = (stride_data.phase_ipsi >= 10) & (stride_data.phase_ipsi <= 40);
            late_swing_idx = (stride_data.phase_ipsi >= 70) & (stride_data.phase_ipsi <= 95);
            
            % Calculate mean GRF in each window for ipsilateral
            early_ipsi_grf = mean(stride_data.vertical_grf_ipsi_BW(early_stance_idx), 'omitnan');
            late_ipsi_grf = mean(stride_data.vertical_grf_ipsi_BW(late_swing_idx), 'omitnan');
            
            % Calculate mean GRF in each window for contralateral
            early_contra_grf = mean(stride_data.vertical_grf_contra_BW(early_stance_idx), 'omitnan');
            late_contra_grf = mean(stride_data.vertical_grf_contra_BW(late_swing_idx), 'omitnan');
            
            % Check if pattern suggests swapped assignment
            % Ipsi should be HIGH in early stance, ZERO in late swing
            % Contra should be LOW in early stance, HIGH in late swing
            swap_detected = false;
            
            % Detection criteria:
            % 1. Late ipsi GRF > 0.3 BW (should be near zero)  
            % 2. Late ipsi GRF > 0.5 * early ipsi GRF (should be much lower)
            % Simplified: just check if ipsi has significant force during swing
            if late_ipsi_grf > 0.3 && ...
               late_ipsi_grf > 0.5 * early_ipsi_grf
                swap_detected = true;
                fprintf('  WARNING: Swapped GRF detected for %s stride %d (task: %s)\n', ...
                    subject_str, s, task);
                fprintf('    Early ipsi: %.2f BW, Late ipsi: %.2f BW (should be ~0)\n', ...
                    early_ipsi_grf, late_ipsi_grf);
                fprintf('    Early contra: %.2f BW, Late contra: %.2f BW\n', ...
                    early_contra_grf, late_contra_grf);
                fprintf('    -> Swapping ipsi/contra GRF assignments\n');
                
                % Swap all GRF components
                temp_vert = stride_data.vertical_grf_ipsi_BW;
                stride_data.vertical_grf_ipsi_BW = stride_data.vertical_grf_contra_BW;
                stride_data.vertical_grf_contra_BW = temp_vert;
                
                temp_ant = stride_data.anterior_grf_ipsi_BW;
                stride_data.anterior_grf_ipsi_BW = stride_data.anterior_grf_contra_BW;
                stride_data.anterior_grf_contra_BW = temp_ant;
                
                temp_lat = stride_data.lateral_grf_ipsi_BW;
                stride_data.lateral_grf_ipsi_BW = stride_data.lateral_grf_contra_BW;
                stride_data.lateral_grf_contra_BW = temp_lat;
            end
        end
        
        % Create single row with arrays for this stride
        row = table();
        row.subject = {subject_str};
        row.task = {task};
        row.task_id = {task_id};
        row.task_info = {task_info};
        % Simple step numbering (no leg suffix since we're not duplicating)
        row.step = sprintf('%03d', s);
        row.phase_ipsi = {stride_data.phase_ipsi};  % Store as cell array
        row.phase_ipsi_dot = {stride_data.phase_ipsi_dot};  % Store phase rate as cell array
        
        % Ipsilateral kinematics
        row.ankle_dorsiflexion_angle_ipsi_rad = {stride_data.ankle_dorsiflexion_angle_ipsi_rad};
        row.knee_flexion_angle_ipsi_rad = {stride_data.knee_flexion_angle_ipsi_rad};
        row.hip_flexion_angle_ipsi_rad = {stride_data.hip_flexion_angle_ipsi_rad};
        
        % Ipsilateral velocities
        row.ankle_dorsiflexion_velocity_ipsi_rad_s = {stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s};
        row.knee_flexion_velocity_ipsi_rad_s = {stride_data.knee_flexion_velocity_ipsi_rad_s};
        row.hip_flexion_velocity_ipsi_rad_s = {stride_data.hip_flexion_velocity_ipsi_rad_s};
        
        % Contralateral kinematics
        row.ankle_dorsiflexion_angle_contra_rad = {stride_data.ankle_dorsiflexion_angle_contra_rad};
        row.knee_flexion_angle_contra_rad = {stride_data.knee_flexion_angle_contra_rad};
        row.hip_flexion_angle_contra_rad = {stride_data.hip_flexion_angle_contra_rad};
        
        % Contralateral velocities
        row.ankle_dorsiflexion_velocity_contra_rad_s = {stride_data.ankle_dorsiflexion_velocity_contra_rad_s};
        row.knee_flexion_velocity_contra_rad_s = {stride_data.knee_flexion_velocity_contra_rad_s};
        row.hip_flexion_velocity_contra_rad_s = {stride_data.hip_flexion_velocity_contra_rad_s};
        
        % Ipsilateral kinetics
        row.ankle_dorsiflexion_moment_ipsi_Nm_kg = {stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg};
        row.knee_flexion_moment_ipsi_Nm_kg = {stride_data.knee_flexion_moment_ipsi_Nm_kg};
        row.hip_flexion_moment_ipsi_Nm_kg = {stride_data.hip_flexion_moment_ipsi_Nm_kg};
        
        % Contralateral kinetics
        row.ankle_dorsiflexion_moment_contra_Nm_kg = {stride_data.ankle_dorsiflexion_moment_contra_Nm_kg};
        row.knee_flexion_moment_contra_Nm_kg = {stride_data.knee_flexion_moment_contra_Nm_kg};
        row.hip_flexion_moment_contra_Nm_kg = {stride_data.hip_flexion_moment_contra_Nm_kg};
        
        % Ipsilateral Ground Reaction Forces
        row.vertical_grf_ipsi_BW = {stride_data.vertical_grf_ipsi_BW};
        row.anterior_grf_ipsi_BW = {stride_data.anterior_grf_ipsi_BW};
        row.lateral_grf_ipsi_BW = {stride_data.lateral_grf_ipsi_BW};
        
        % Contralateral Ground Reaction Forces
        row.vertical_grf_contra_BW = {stride_data.vertical_grf_contra_BW};
        row.anterior_grf_contra_BW = {stride_data.anterior_grf_contra_BW};
        row.lateral_grf_contra_BW = {stride_data.lateral_grf_contra_BW};
        
        % Segment angles (pelvis and trunk are shared)
        row.pelvis_sagittal_angle_rad = {stride_data.pelvis_sagittal_angle_rad};
        row.trunk_sagittal_angle_rad = {stride_data.trunk_sagittal_angle_rad};
        
        % Segment velocities (pelvis and trunk are shared)
        row.pelvis_sagittal_velocity_rad_s = {stride_data.pelvis_sagittal_velocity_rad_s};
        row.trunk_sagittal_velocity_rad_s = {stride_data.trunk_sagittal_velocity_rad_s};
        
        % Ipsilateral segment angles
        row.thigh_sagittal_angle_ipsi_rad = {stride_data.thigh_sagittal_angle_ipsi_rad};
        row.shank_sagittal_angle_ipsi_rad = {stride_data.shank_sagittal_angle_ipsi_rad};
        row.foot_sagittal_angle_ipsi_rad = {stride_data.foot_sagittal_angle_ipsi_rad};
        
        % Ipsilateral segment velocities
        row.thigh_sagittal_velocity_ipsi_rad_s = {stride_data.thigh_sagittal_velocity_ipsi_rad_s};
        row.shank_sagittal_velocity_ipsi_rad_s = {stride_data.shank_sagittal_velocity_ipsi_rad_s};
        row.foot_sagittal_velocity_ipsi_rad_s = {stride_data.foot_sagittal_velocity_ipsi_rad_s};
        
        % Contralateral segment angles
        row.thigh_sagittal_angle_contra_rad = {stride_data.thigh_sagittal_angle_contra_rad};
        row.shank_sagittal_angle_contra_rad = {stride_data.shank_sagittal_angle_contra_rad};
        row.foot_sagittal_angle_contra_rad = {stride_data.foot_sagittal_angle_contra_rad};
        
        % Contralateral segment velocities
        row.thigh_sagittal_velocity_contra_rad_s = {stride_data.thigh_sagittal_velocity_contra_rad_s};
        row.shank_sagittal_velocity_contra_rad_s = {stride_data.shank_sagittal_velocity_contra_rad_s};
        row.foot_sagittal_velocity_contra_rad_s = {stride_data.foot_sagittal_velocity_contra_rad_s};
        
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
    step = cell(total_rows, 1);
    phase_ipsi = zeros(total_rows, 1);
    phase_ipsi_dot = zeros(total_rows, 1);  % Add phase rate array
    
    % Ipsilateral kinematics
    ankle_dorsiflexion_angle_ipsi_rad = zeros(total_rows, 1);
    knee_flexion_angle_ipsi_rad = zeros(total_rows, 1);
    hip_flexion_angle_ipsi_rad = zeros(total_rows, 1);
    
    % Ipsilateral velocities
    ankle_dorsiflexion_velocity_ipsi_rad_s = zeros(total_rows, 1);
    knee_flexion_velocity_ipsi_rad_s = zeros(total_rows, 1);
    hip_flexion_velocity_ipsi_rad_s = zeros(total_rows, 1);
    
    % Contralateral kinematics
    ankle_dorsiflexion_angle_contra_rad = zeros(total_rows, 1);
    knee_flexion_angle_contra_rad = zeros(total_rows, 1);
    hip_flexion_angle_contra_rad = zeros(total_rows, 1);
    
    % Contralateral velocities
    ankle_dorsiflexion_velocity_contra_rad_s = zeros(total_rows, 1);
    knee_flexion_velocity_contra_rad_s = zeros(total_rows, 1);
    hip_flexion_velocity_contra_rad_s = zeros(total_rows, 1);
    
    % Ipsilateral kinetics
    ankle_dorsiflexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    knee_flexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    hip_flexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    
    % Contralateral kinetics
    ankle_dorsiflexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    knee_flexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    hip_flexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    
    % Ipsilateral Ground Reaction Forces
    vertical_grf_ipsi_BW = zeros(total_rows, 1);
    anterior_grf_ipsi_BW = zeros(total_rows, 1);
    lateral_grf_ipsi_BW = zeros(total_rows, 1);
    
    % Contralateral Ground Reaction Forces
    vertical_grf_contra_BW = zeros(total_rows, 1);
    anterior_grf_contra_BW = zeros(total_rows, 1);
    lateral_grf_contra_BW = zeros(total_rows, 1);
    
    % Segment angles (shared)
    pelvis_sagittal_angle_rad = zeros(total_rows, 1);
    trunk_sagittal_angle_rad = zeros(total_rows, 1);
    
    % Segment velocities (shared)
    pelvis_sagittal_velocity_rad_s = zeros(total_rows, 1);
    trunk_sagittal_velocity_rad_s = zeros(total_rows, 1);
    
    % Ipsilateral segment angles
    thigh_sagittal_angle_ipsi_rad = zeros(total_rows, 1);
    shank_sagittal_angle_ipsi_rad = zeros(total_rows, 1);
    foot_sagittal_angle_ipsi_rad = zeros(total_rows, 1);
    
    % Ipsilateral segment velocities
    thigh_sagittal_velocity_ipsi_rad_s = zeros(total_rows, 1);
    shank_sagittal_velocity_ipsi_rad_s = zeros(total_rows, 1);
    foot_sagittal_velocity_ipsi_rad_s = zeros(total_rows, 1);
    
    % Contralateral segment angles
    thigh_sagittal_angle_contra_rad = zeros(total_rows, 1);
    shank_sagittal_angle_contra_rad = zeros(total_rows, 1);
    foot_sagittal_angle_contra_rad = zeros(total_rows, 1);
    
    % Contralateral segment velocities
    thigh_sagittal_velocity_contra_rad_s = zeros(total_rows, 1);
    shank_sagittal_velocity_contra_rad_s = zeros(total_rows, 1);
    foot_sagittal_velocity_contra_rad_s = zeros(total_rows, 1);
    
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
            step{row_idx} = stride.step;
            
            % Extract point data from arrays
            phase_ipsi(row_idx) = stride.phase_ipsi{1}(p);
            phase_ipsi_dot(row_idx) = stride.phase_ipsi_dot{1}(p);  % Extract phase rate
            
            % Ipsilateral kinematics
            ankle_dorsiflexion_angle_ipsi_rad(row_idx) = stride.ankle_dorsiflexion_angle_ipsi_rad{1}(p);
            knee_flexion_angle_ipsi_rad(row_idx) = stride.knee_flexion_angle_ipsi_rad{1}(p);
            hip_flexion_angle_ipsi_rad(row_idx) = stride.hip_flexion_angle_ipsi_rad{1}(p);
            
            % Ipsilateral velocities
            ankle_dorsiflexion_velocity_ipsi_rad_s(row_idx) = stride.ankle_dorsiflexion_velocity_ipsi_rad_s{1}(p);
            knee_flexion_velocity_ipsi_rad_s(row_idx) = stride.knee_flexion_velocity_ipsi_rad_s{1}(p);
            hip_flexion_velocity_ipsi_rad_s(row_idx) = stride.hip_flexion_velocity_ipsi_rad_s{1}(p);
            
            % Contralateral kinematics
            ankle_dorsiflexion_angle_contra_rad(row_idx) = stride.ankle_dorsiflexion_angle_contra_rad{1}(p);
            knee_flexion_angle_contra_rad(row_idx) = stride.knee_flexion_angle_contra_rad{1}(p);
            hip_flexion_angle_contra_rad(row_idx) = stride.hip_flexion_angle_contra_rad{1}(p);
            
            % Contralateral velocities
            ankle_dorsiflexion_velocity_contra_rad_s(row_idx) = stride.ankle_dorsiflexion_velocity_contra_rad_s{1}(p);
            knee_flexion_velocity_contra_rad_s(row_idx) = stride.knee_flexion_velocity_contra_rad_s{1}(p);
            hip_flexion_velocity_contra_rad_s(row_idx) = stride.hip_flexion_velocity_contra_rad_s{1}(p);
            
            % Ipsilateral kinetics
            ankle_dorsiflexion_moment_ipsi_Nm_kg(row_idx) = stride.ankle_dorsiflexion_moment_ipsi_Nm_kg{1}(p);
            knee_flexion_moment_ipsi_Nm_kg(row_idx) = stride.knee_flexion_moment_ipsi_Nm_kg{1}(p);
            hip_flexion_moment_ipsi_Nm_kg(row_idx) = stride.hip_flexion_moment_ipsi_Nm_kg{1}(p);
            
            % Contralateral kinetics
            ankle_dorsiflexion_moment_contra_Nm_kg(row_idx) = stride.ankle_dorsiflexion_moment_contra_Nm_kg{1}(p);
            knee_flexion_moment_contra_Nm_kg(row_idx) = stride.knee_flexion_moment_contra_Nm_kg{1}(p);
            hip_flexion_moment_contra_Nm_kg(row_idx) = stride.hip_flexion_moment_contra_Nm_kg{1}(p);
            
            % Ipsilateral Ground Reaction Forces
            vertical_grf_ipsi_BW(row_idx) = stride.vertical_grf_ipsi_BW{1}(p);
            anterior_grf_ipsi_BW(row_idx) = stride.anterior_grf_ipsi_BW{1}(p);
            lateral_grf_ipsi_BW(row_idx) = stride.lateral_grf_ipsi_BW{1}(p);
            
            % Contralateral Ground Reaction Forces
            vertical_grf_contra_BW(row_idx) = stride.vertical_grf_contra_BW{1}(p);
            anterior_grf_contra_BW(row_idx) = stride.anterior_grf_contra_BW{1}(p);
            lateral_grf_contra_BW(row_idx) = stride.lateral_grf_contra_BW{1}(p);
            
            % Shared segment angles
            pelvis_sagittal_angle_rad(row_idx) = stride.pelvis_sagittal_angle_rad{1}(p);
            trunk_sagittal_angle_rad(row_idx) = stride.trunk_sagittal_angle_rad{1}(p);
            
            % Shared segment velocities
            pelvis_sagittal_velocity_rad_s(row_idx) = stride.pelvis_sagittal_velocity_rad_s{1}(p);
            trunk_sagittal_velocity_rad_s(row_idx) = stride.trunk_sagittal_velocity_rad_s{1}(p);
            
            % Ipsilateral segment angles
            thigh_sagittal_angle_ipsi_rad(row_idx) = stride.thigh_sagittal_angle_ipsi_rad{1}(p);
            shank_sagittal_angle_ipsi_rad(row_idx) = stride.shank_sagittal_angle_ipsi_rad{1}(p);
            foot_sagittal_angle_ipsi_rad(row_idx) = stride.foot_sagittal_angle_ipsi_rad{1}(p);
            
            % Ipsilateral segment velocities
            thigh_sagittal_velocity_ipsi_rad_s(row_idx) = stride.thigh_sagittal_velocity_ipsi_rad_s{1}(p);
            shank_sagittal_velocity_ipsi_rad_s(row_idx) = stride.shank_sagittal_velocity_ipsi_rad_s{1}(p);
            foot_sagittal_velocity_ipsi_rad_s(row_idx) = stride.foot_sagittal_velocity_ipsi_rad_s{1}(p);
            
            % Contralateral segment angles
            thigh_sagittal_angle_contra_rad(row_idx) = stride.thigh_sagittal_angle_contra_rad{1}(p);
            shank_sagittal_angle_contra_rad(row_idx) = stride.shank_sagittal_angle_contra_rad{1}(p);
            foot_sagittal_angle_contra_rad(row_idx) = stride.foot_sagittal_angle_contra_rad{1}(p);
            
            % Contralateral segment velocities
            thigh_sagittal_velocity_contra_rad_s(row_idx) = stride.thigh_sagittal_velocity_contra_rad_s{1}(p);
            shank_sagittal_velocity_contra_rad_s(row_idx) = stride.shank_sagittal_velocity_contra_rad_s{1}(p);
            foot_sagittal_velocity_contra_rad_s(row_idx) = stride.foot_sagittal_velocity_contra_rad_s{1}(p);
            
            row_idx = row_idx + 1;
        end
    end
    
    % Create output table from arrays
    fprintf('  Creating expanded table...\n');
    expanded = table(subject, task, task_id, task_info, step, phase_ipsi, phase_ipsi_dot, ...
        ankle_dorsiflexion_angle_ipsi_rad, knee_flexion_angle_ipsi_rad, hip_flexion_angle_ipsi_rad, ...
        ankle_dorsiflexion_velocity_ipsi_rad_s, knee_flexion_velocity_ipsi_rad_s, hip_flexion_velocity_ipsi_rad_s, ...
        ankle_dorsiflexion_angle_contra_rad, knee_flexion_angle_contra_rad, hip_flexion_angle_contra_rad, ...
        ankle_dorsiflexion_velocity_contra_rad_s, knee_flexion_velocity_contra_rad_s, hip_flexion_velocity_contra_rad_s, ...
        ankle_dorsiflexion_moment_ipsi_Nm_kg, knee_flexion_moment_ipsi_Nm_kg, hip_flexion_moment_ipsi_Nm_kg, ...
        ankle_dorsiflexion_moment_contra_Nm_kg, knee_flexion_moment_contra_Nm_kg, hip_flexion_moment_contra_Nm_kg, ...
        vertical_grf_ipsi_BW, anterior_grf_ipsi_BW, lateral_grf_ipsi_BW, ...
        vertical_grf_contra_BW, anterior_grf_contra_BW, lateral_grf_contra_BW, ...
        pelvis_sagittal_angle_rad, trunk_sagittal_angle_rad, ...
        pelvis_sagittal_velocity_rad_s, trunk_sagittal_velocity_rad_s, ...
        thigh_sagittal_angle_ipsi_rad, shank_sagittal_angle_ipsi_rad, foot_sagittal_angle_ipsi_rad, ...
        thigh_sagittal_velocity_ipsi_rad_s, shank_sagittal_velocity_ipsi_rad_s, foot_sagittal_velocity_ipsi_rad_s, ...
        thigh_sagittal_angle_contra_rad, shank_sagittal_angle_contra_rad, foot_sagittal_angle_contra_rad, ...
        thigh_sagittal_velocity_contra_rad_s, shank_sagittal_velocity_contra_rad_s, foot_sagittal_velocity_contra_rad_s);
end

%% Helper Functions

function [first_leg, first_hs_time] = determine_first_heel_strike(trial_data, time_start, time_end)
    % Determine which leg heel strikes first in a trial segment
    % Returns 'right', 'left', or empty string if no heel strikes found
    
    first_leg = '';
    first_hs_time = [];
    
    % Check we have both gait cycle data
    if ~isfield(trial_data, 'gcRight') || ~istable(trial_data.gcRight) || ...
       ~isfield(trial_data, 'gcLeft') || ~istable(trial_data.gcLeft)
        return;
    end
    
    % Get heel strike indices for right leg
    right_gc_time = trial_data.gcRight.Header;
    right_window_indices = find(right_gc_time >= time_start & right_gc_time <= time_end);
    
    if ~isempty(right_window_indices)
        right_heel_strike_pct = trial_data.gcRight.HeelStrike;
        right_hs_indices = findFallingEdges_onlyInSection(right_heel_strike_pct == 0, right_window_indices);
        if ~isempty(right_hs_indices)
            right_first_hs_time = right_gc_time(right_hs_indices(1));
        else
            right_first_hs_time = inf;  % No heel strikes found
        end
    else
        right_first_hs_time = inf;
    end
    
    % Get heel strike indices for left leg
    left_gc_time = trial_data.gcLeft.Header;
    left_window_indices = find(left_gc_time >= time_start & left_gc_time <= time_end);
    
    if ~isempty(left_window_indices)
        left_heel_strike_pct = trial_data.gcLeft.HeelStrike;
        left_hs_indices = findFallingEdges_onlyInSection(left_heel_strike_pct == 0, left_window_indices);
        if ~isempty(left_hs_indices)
            left_first_hs_time = left_gc_time(left_hs_indices(1));
        else
            left_first_hs_time = inf;  % No heel strikes found
        end
    else
        left_first_hs_time = inf;
    end
    
    % Determine which leg strikes first
    if right_first_hs_time < left_first_hs_time
        first_leg = 'right';
        first_hs_time = right_first_hs_time;
    elseif left_first_hs_time < right_first_hs_time
        first_leg = 'left';
        first_hs_time = left_first_hs_time;
    end
    % If both are inf (no heel strikes), first_leg remains empty
end

% Helper function for improved gradient calculation with proper boundary conditions
function velocity = improved_gradient(angle_data)
    % Calculate gradient with forward/backward differences at boundaries
    n = length(angle_data);
    velocity = zeros(n, 1);
    
    % First point: forward difference (no periodic assumption)
    velocity(1) = angle_data(2) - angle_data(1);
    
    % Last point: backward difference (no periodic assumption)
    velocity(n) = angle_data(n) - angle_data(n-1);
    
    % Middle points: standard central difference
    for i = 2:n-1
        velocity(i) = (angle_data(i+1) - angle_data(i-1)) / 2;
    end
end
