function convert_gtech_2021_phase_to_parquet(options)
% Optional struct selects exactly one recording for bounded staging.
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

if nargin < 1, options = struct(); end


% Add utilities to path
addpath('utilities');
addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'matlab_common'));

%% Configuration
NUM_POINTS = 150;  % Points per gait cycle
DATA_ROOT = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
OUTPUT_DIR = fullfile('..', '..', '..', 'converted_datasets');

% A recording request never enters the all-subject accumulation path.
if ~isempty(fieldnames(options))
    required = {'data_root','subject','date','mode','recording','output_path'};
    assert(all(isfield(options, required)), 'LocoHub:RecordingOptions', 'Incomplete recording options');
    assert(any(strcmp(options.mode, {'treadmill','levelground','ramp','stair'})), 'LocoHub:Mode', 'Unsupported mode');
    assert(~isfile(options.output_path), 'LocoHub:ImmutableOutput', 'Output already exists');
    subject_info = load(fullfile(options.data_root, 'SubjectInfo.mat'));
    mass = subject_info.data.Weight(strcmp(subject_info.data.Subject, options.subject));
    assert(isscalar(mass) && isfinite(mass) && mass > 0, 'LocoHub:Mass', 'Measured subject mass required');
    date_path = fullfile(options.data_root, options.subject, options.date);
    subject_str = ['GT21_' options.subject];
    metadata = jsonencode(struct('weight_kg', mass));
    switch options.mode
        case 'treadmill'
            rows = process_treadmill(date_path, subject_str, mass, metadata, options.recording);
        case 'levelground'
            rows = process_levelground(date_path, subject_str, mass, metadata, options.recording);
        case 'ramp'
            rows = process_ramp(date_path, subject_str, mass, metadata, options.recording);
        case 'stair'
            rows = process_stair(date_path, subject_str, mass, metadata, options.recording);
    end
    assert(~isempty(rows), 'LocoHub:NoObservations', 'Recording produced no observations; investigate exclusions');
    expanded = expand_table_for_parquet(rows);
    parquetwrite(options.output_path, expanded);
    % Export original source tables for independent bounded Python comparisons.
    evidence_dir = fileparts(options.output_path);
    for channel = {'conditions','ik_offset','id','gcLeft','gcRight'}
        source_file = fullfile(date_path, options.mode, channel{1}, options.recording);
        if ~isfile(source_file), continue; end
        original = load(source_file);
        names = fieldnames(original);
        for k = 1:numel(names)
            if istable(original.(names{k}))
                writetable(original.(names{k}), fullfile(evidence_dir, ...
                    ['source_' channel{1} '_' names{k} '.csv']));
            end
        end
    end
    fprintf('Recording export: %d observations, %d rows\n', height(rows), height(expanded));
    return;
end


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

    % Estimate segment lengths from static markers (per subject)
    seg_lengths = gtech_estimate_segment_lengths(DATA_ROOT, subject_code);
    subject_metadata = sprintf( ...
        'weight_kg:%.1f,thigh_length_m:%.3f,shank_length_m:%.3f,foot_length_m:%.3f', ...
        subject_mass, ...
        seg_lengths.thigh_length_m, ...
        seg_lengths.shank_length_m, ...
        seg_lengths.foot_length_m);
    
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
    [treadmill_rows, treadmill_speeds] = process_treadmill(date_path, subject_str, subject_mass, subject_metadata);
    if ~isempty(treadmill_rows)
        subject_rows = [subject_rows; treadmill_rows];
        fprintf('  Added %d treadmill strides\n', height(treadmill_rows));
        trial_counts.treadmill_speeds = treadmill_speeds;
    end
    
    % 2. Process level ground data
    [levelground_rows, lg_trials] = process_levelground(date_path, subject_str, subject_mass, subject_metadata);
    if ~isempty(levelground_rows)
        subject_rows = [subject_rows; levelground_rows];
        fprintf('  Added %d level ground strides\n', height(levelground_rows));
        trial_counts.levelground = lg_trials;
    end
    
    % 3. Process ramp data
    [ramp_rows, ramp_trials] = process_ramp(date_path, subject_str, subject_mass, subject_metadata);
    if ~isempty(ramp_rows)
        subject_rows = [subject_rows; ramp_rows];
        fprintf('  Added %d ramp strides\n', height(ramp_rows));
        trial_counts.ramp = ramp_trials;
    end
    
    % 4. Process stair data
    [stair_rows, stair_trials] = process_stair(date_path, subject_str, subject_mass, subject_metadata);
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

end % Main conversion entry point

%% Helper Functions

function [rows, unique_speeds] = process_treadmill(date_path, subject_str, subject_mass, subject_metadata, recording_filter)
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
    if nargin >= 5
        trial_files = trial_files(strcmp({trial_files.name}, recording_filter));
        assert(numel(trial_files) == 1, 'LocoHub:Recording', 'Requested recording not found');
    end
    
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
                    subject_str, subject_metadata, 'level_walking', 'level', task_info, subject_mass, 'treadmill');
                
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

function [rows, trial_count] = process_levelground(date_path, subject_str, subject_mass, subject_metadata, recording_filter)
    % Process level ground walking data and labeled transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'levelground');

    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    if nargin >= 5
        trial_files = trial_files(strcmp({trial_files.name}, recording_filter));
        assert(numel(trial_files) == 1, 'LocoHub:Recording', 'Requested recording not found');
    end
    trial_count = length(trial_files);  % Count all trial files

    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;

        % Load all data for this trial
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        % Filename supplies a speed category, not a measured trial speed.
        if contains(trial_name, 'slow')
            speed_category = 'slow';
        elseif contains(trial_name, 'fast')
            speed_category = 'fast';
        elseif contains(trial_name, 'normal')
            speed_category = 'normal';
        else
            speed_category = 'unknown';
        end

        has_labels = isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
            any(strcmp(trial_data.conditions.Properties.VariableNames, 'Label'));
        if has_labels
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
                    [task, task_id, task_info] = map_levelground_label(label_name, speed_category);
                    if isempty(task)
                        continue;
                    end

                    stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                        subject_str, subject_metadata, task, task_id, task_info, subject_mass, 'levelground');

                    if ~isempty(stride_rows)
                        rows = [rows; stride_rows];
                    end
                end
            end
        end

        % Only missing label tables permit an explicitly unverified fallback.
        if ~has_labels && isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
            time_start = trial_data.ik_offset.Header(1);
            time_end = trial_data.ik_offset.Header(end);
            task_info = sprintf('speed_category:%s,speed_source:filename,surface:overground,labels_missing:true', speed_category);
            stride_rows = extract_and_process_strides(trial_data, time_start, time_end, ...
                subject_str, subject_metadata, 'level_walking', 'level', task_info, subject_mass, 'levelground');

            if ~isempty(stride_rows)
                rows = [rows; stride_rows];
            end
        end
    end
end

function [rows, trial_count] = process_ramp(date_path, subject_str, subject_mass, subject_metadata, recording_filter)
    % Process ramp ascent/descent data, including transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'ramp');

    if ~exist(mode_path, 'dir')
        return;
    end

    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    if nargin >= 5
        trial_files = trial_files(strcmp({trial_files.name}, recording_filter));
        assert(numel(trial_files) == 1, 'LocoHub:Recording', 'Requested recording not found');
    end
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
        % Fallback: use scalar rampIncline copied from conditions struct
        if isnan(ramp_angle) && isfield(trial_data, 'rampIncline')
            ramp_angle = trial_data.rampIncline;
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
                        subject_str, subject_metadata, task, task_id, task_info, subject_mass, 'ramp');

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
                subject_str, subject_metadata, task, task_id, task_info, subject_mass, 'ramp');

                if ~isempty(stride_rows)
                    rows = [rows; stride_rows];
                end
            end
        end
    end
end

function [rows, trial_count] = process_stair(date_path, subject_str, subject_mass, subject_metadata, recording_filter)
    % Process stair ascent/descent data and transitions
    rows = table();
    trial_count = 0;
    mode_path = fullfile(date_path, 'stair');

    if ~exist(mode_path, 'dir')
        return;
    end

    % Get all trial files
    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    if nargin >= 5
        trial_files = trial_files(strcmp({trial_files.name}, recording_filter));
        assert(numel(trial_files) == 1, 'LocoHub:Recording', 'Requested recording not found');
    end
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
                        subject_str, subject_metadata, task, task_id, task_info, subject_mass, 'stair');

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
                subject_str, subject_metadata, task, task_id, task_info, subject_mass, 'stair');

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

function [task, task_id, task_info] = map_levelground_label(label_name, speed_category)
    % Map level ground labels to standardized task metadata
    task = '';
    task_id = '';
    task_info = '';

    base_info = sprintf('speed_category:%s,speed_source:filename,surface:overground', speed_category);

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
    [date_path, source_mode] = fileparts(mode_path);
    [subject_path, source_date] = fileparts(date_path);
    [~, source_subject] = fileparts(subject_path);
    trial_data.source_recording_id = sprintf('gt21:%s/%s/%s/%s', source_subject, source_date, source_mode, trial_name);
    
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
            % Also copy rampIncline field if it exists (for ramp trials)
            if isfield(temp, 'rampIncline')
                trial_data.rampIncline = temp.rampIncline;
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
        
        % Load marker data if available
        markers_file = fullfile(mode_path, 'markers', trial_name);
        if exist(markers_file, 'file')
            temp = load(markers_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.markers = temp.data;
            else
                trial_data.markers = temp;
            end
        end
        
    catch ME
        warning('Failed to load trial %s: %s', trial_name, ME.message);
        trial_data = [];
    end
end

function rows = extract_and_process_strides(trial_data, time_start, time_end, ...
    subject_str, subject_metadata, task, task_id, task_info, subject_mass, mode)
    % NEW APPROACH: Single-leg processing based on first heel strike
    % The leg that heel strikes first becomes ipsilateral for entire trial
    
    % Determine which leg heel strikes first in this trial segment
    [first_leg, first_hs_time] = gtech_determine_first_heel_strike(trial_data, time_start, time_end);
    
    if isempty(first_leg)
        fprintf('  No heel strikes found in time window %.3f-%.3f sec\n', time_start, time_end);
        rows = table();
        return;
    end
    
    fprintf('  First heel strike: %s leg at %.3f sec\n', first_leg, first_hs_time);
    
    % Process ONLY with the first heel-striking leg as ipsilateral
    % This eliminates duplicate strides and provides consistent force plate assignment
    rows = extract_and_process_strides_single_leg(trial_data, time_start, time_end, ...
        subject_str, subject_metadata, task, task_id, task_info, subject_mass, first_leg, mode);
end

function rows = extract_and_process_strides_single_leg(trial_data, time_start, time_end, ...
    subject_str, subject_metadata, task, task_id, task_info, subject_mass, leg_side, mode)
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
    
    % Source zero-percent resets identify heel strikes. Keep the actual
    % next heel-strike sample as the inclusive endpoint, not its predecessor.
    source_resets = find(heel_strike_pct == 0 & [false; heel_strike_pct(1:end-1) > 0]);
    hs_indices = source_resets(ismember(source_resets, window_indices));

    if length(hs_indices) < 2
        rows = table();
        return;  % Need at least 2 heel strikes for one stride
    end
    
    % Process each stride (heel strike to heel strike)
    for s = 1:(length(hs_indices)-1)
        stride_start_idx = hs_indices(s);
        stride_end_idx = hs_indices(s+1);
        source_pct = heel_strike_pct(stride_start_idx:stride_end_idx);
        stride_time = gc_time(stride_start_idx:stride_end_idx);
        assert(all(isfinite(stride_time)) && all(diff(stride_time) > 0), ...
            'LocoHub:SourceClock', 'Gait-event timestamps must increase');
        stride_pct = 100 * (stride_time - stride_time(1)) / (stride_time(end) - stride_time(1));

        % Skip if stride is too short or doesn't progress properly
        if length(stride_pct) < 10 || max(source_pct) < 50
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
        stride_data.subject = repmat({subject_str}, NUM_POINTS, 1);
        stride_data.subject_metadata = repmat({subject_metadata}, NUM_POINTS, 1);
        stride_data.phase_ipsi = target_pct;
        stride_data.phase_ipsi_dot = repmat(phase_ipsi_dot_value, NUM_POINTS, 1);  % Constant for all 150 points
        
        nan_vector = NaN(NUM_POINTS, 1);
        stride_data.cop_anterior_ipsi_m = nan_vector;
        stride_data.cop_anterior_contra_m = nan_vector;
        stride_data.cop_lateral_ipsi_m = nan_vector;
        stride_data.cop_lateral_contra_m = nan_vector;
        stride_data.cop_vertical_ipsi_m = nan_vector;
        stride_data.cop_vertical_contra_m = nan_vector;
        
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
        
        ik_time = trial_data.ik_offset.Header(ik_mask);
        target_times = linspace(stride_start_time, stride_end_time, NUM_POINTS);

        % Ankle dorsiflexion angle - IPSILATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, ipsi_ankle_var))
            angle_data = trial_data.ik_offset.(ipsi_ankle_var)(ik_mask);
            ik_time = trial_data.ik_offset.Header(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            target_times = linspace(stride_start_time, stride_end_time, NUM_POINTS);
            ankle_data = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            ankle_velocity = gradient(ankle_data) * (NUM_POINTS - 1) / stride_duration_s;
            ankle_acceleration = gradient(ankle_velocity) * (NUM_POINTS - 1) / stride_duration_s;
            
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = ankle_data;
            stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = ankle_velocity;
            stride_data.ankle_dorsiflexion_acceleration_ipsi_rad_s2 = ankle_acceleration;
        else
            stride_data.ankle_dorsiflexion_angle_ipsi_rad = NaN(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = NaN(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_acceleration_ipsi_rad_s2 = NaN(NUM_POINTS, 1);
        end
        
        % Ankle dorsiflexion angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_ankle_var))
            angle_data = trial_data.ik_offset.(contra_ankle_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            ankle_data_contra = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            ankle_velocity_contra = gradient(ankle_data_contra) * (NUM_POINTS - 1) / stride_duration_s;
            ankle_acceleration_contra = gradient(ankle_velocity_contra) * (NUM_POINTS - 1) / stride_duration_s;
            
            stride_data.ankle_dorsiflexion_angle_contra_rad = ankle_data_contra;
            stride_data.ankle_dorsiflexion_velocity_contra_rad_s = ankle_velocity_contra;
            stride_data.ankle_dorsiflexion_acceleration_contra_rad_s2 = ankle_acceleration_contra;
        else
            stride_data.ankle_dorsiflexion_angle_contra_rad = NaN(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_velocity_contra_rad_s = NaN(NUM_POINTS, 1);
            stride_data.ankle_dorsiflexion_acceleration_contra_rad_s2 = NaN(NUM_POINTS, 1);
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
            
            knee_velocity = gradient(knee_data) * (NUM_POINTS - 1) / stride_duration_s;
            knee_acceleration = gradient(knee_velocity) * (NUM_POINTS - 1) / stride_duration_s;
            
            stride_data.knee_flexion_angle_ipsi_rad = knee_data;
            stride_data.knee_flexion_velocity_ipsi_rad_s = knee_velocity;
            stride_data.knee_flexion_acceleration_ipsi_rad_s2 = knee_acceleration;
        else
            stride_data.knee_flexion_angle_ipsi_rad = NaN(NUM_POINTS, 1);
            stride_data.knee_flexion_velocity_ipsi_rad_s = NaN(NUM_POINTS, 1);
            stride_data.knee_flexion_acceleration_ipsi_rad_s2 = NaN(NUM_POINTS, 1);
        end
        
        % Knee angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_knee_var))
            angle_data = trial_data.ik_offset.(contra_knee_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            knee_data_contra = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            
            % FIX: Flip knee angle if needed (Gtech dataset has inverted knee flexion)
            knee_data_contra = -knee_data_contra;
            
            knee_velocity_contra = gradient(knee_data_contra) * (NUM_POINTS - 1) / stride_duration_s;
            knee_acceleration_contra = gradient(knee_velocity_contra) * (NUM_POINTS - 1) / stride_duration_s;
            
            stride_data.knee_flexion_angle_contra_rad = knee_data_contra;
            stride_data.knee_flexion_velocity_contra_rad_s = knee_velocity_contra;
            stride_data.knee_flexion_acceleration_contra_rad_s2 = knee_acceleration_contra;
        else
            stride_data.knee_flexion_angle_contra_rad = NaN(NUM_POINTS, 1);
            stride_data.knee_flexion_velocity_contra_rad_s = NaN(NUM_POINTS, 1);
            stride_data.knee_flexion_acceleration_contra_rad_s2 = NaN(NUM_POINTS, 1);
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
            stride_data.hip_flexion_velocity_ipsi_rad_s = gradient(stride_data.hip_flexion_angle_ipsi_rad) * (NUM_POINTS - 1) / stride_duration_s;
            stride_data.hip_flexion_acceleration_ipsi_rad_s2 = gradient(stride_data.hip_flexion_velocity_ipsi_rad_s) * (NUM_POINTS - 1) / stride_duration_s;
        else
            stride_data.hip_flexion_angle_ipsi_rad = NaN(NUM_POINTS, 1);
            stride_data.hip_flexion_velocity_ipsi_rad_s = NaN(NUM_POINTS, 1);
            stride_data.hip_flexion_acceleration_ipsi_rad_s2 = NaN(NUM_POINTS, 1);
        end
        
        % Hip angle - CONTRALATERAL
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, contra_hip_var))
            angle_data = trial_data.ik_offset.(contra_hip_var)(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            stride_data.hip_flexion_angle_contra_rad = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            stride_data.hip_flexion_velocity_contra_rad_s = gradient(stride_data.hip_flexion_angle_contra_rad) * (NUM_POINTS - 1) / stride_duration_s;
            stride_data.hip_flexion_acceleration_contra_rad_s2 = gradient(stride_data.hip_flexion_velocity_contra_rad_s) * (NUM_POINTS - 1) / stride_duration_s;
        else
            stride_data.hip_flexion_angle_contra_rad = NaN(NUM_POINTS, 1);
            stride_data.hip_flexion_velocity_contra_rad_s = NaN(NUM_POINTS, 1);
            stride_data.hip_flexion_acceleration_contra_rad_s2 = NaN(NUM_POINTS, 1);
        end
        
        % Calculate segment angles from kinematic chain
        % Pelvis sagittal angle (from pelvis tilt)
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, 'pelvis_tilt'))
            angle_data = trial_data.ik_offset.pelvis_tilt(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            stride_data.pelvis_sagittal_angle_rad = interp1(ik_time, angle_data, target_times, 'linear') * deg2rad;
            stride_data.pelvis_sagittal_velocity_rad_s = gradient(stride_data.pelvis_sagittal_angle_rad) * (NUM_POINTS - 1) / stride_duration_s;
        else
            stride_data.pelvis_sagittal_angle_rad = NaN(NUM_POINTS, 1);
            stride_data.pelvis_sagittal_velocity_rad_s = NaN(NUM_POINTS, 1);
        end
        
        % Trunk sagittal angle (pelvis + lumbar extension)
        if any(strcmp(trial_data.ik_offset.Properties.VariableNames, 'lumbar_extension'))
            lumbar_data = trial_data.ik_offset.lumbar_extension(ik_mask);
            
            % NAIVE APPROACH: Direct time interpolation + simple gradient
            lumbar_interp = interp1(ik_time, lumbar_data, target_times, 'linear') * deg2rad;
            stride_data.trunk_sagittal_angle_rad = stride_data.pelvis_sagittal_angle_rad + lumbar_interp;
            stride_data.trunk_sagittal_velocity_rad_s = gradient(stride_data.trunk_sagittal_angle_rad) * (NUM_POINTS - 1) / stride_duration_s;
        else
            stride_data.trunk_sagittal_angle_rad = NaN(NUM_POINTS, 1);  % Lumbar measurement unavailable
            stride_data.trunk_sagittal_velocity_rad_s = NaN(NUM_POINTS, 1);
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
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = NaN(NUM_POINTS, 1);
        end
        
        % Ankle dorsiflexion moment - CONTRALATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, contra_ankle_moment_var))
            moment_data = trial_data.id.(contra_ankle_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = NaN(NUM_POINTS, 1);
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
            stride_data.knee_flexion_moment_ipsi_Nm_kg = NaN(NUM_POINTS, 1);
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
            stride_data.knee_flexion_moment_contra_Nm_kg = NaN(NUM_POINTS, 1);
        end
        
        % Hip flexion moment - IPSILATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, ipsi_hip_moment_var))
            moment_data = trial_data.id.(ipsi_hip_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_moment_ipsi_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.hip_flexion_moment_ipsi_Nm_kg = NaN(NUM_POINTS, 1);
        end
        
        % Hip flexion moment - CONTRALATERAL
        if any(strcmp(trial_data.id.Properties.VariableNames, contra_hip_moment_var))
            moment_data = trial_data.id.(contra_hip_moment_var)(id_mask) / subject_mass;
            moment_at_stride_time = interp1(id_time, moment_data, valid_stride_time, 'linear', 'extrap');
            stride_data.hip_flexion_moment_contra_Nm_kg = interp1(valid_stride_pct, moment_at_stride_time, target_pct, 'linear', 'extrap');
        else
            stride_data.hip_flexion_moment_contra_Nm_kg = NaN(NUM_POINTS, 1);
        end
        
        % Apply measured plate identity to both legs; never swap using waveforms.
        for output_side = {'ipsi','contra'}
            suffix=output_side{1};
            for component={'vertical','anterior','lateral'}
                stride_data.([component{1} '_grf_' suffix '_BW'])=nan_vector;
            end
        end
        if isfield(trial_data,'fp') && isfield(trial_data,'markers')
            for output_side = {'ipsi','contra'}
                physical_side = leg_side;
                if strcmp(output_side{1},'contra')
                    if strcmpi(leg_side,'right'), physical_side='left'; else, physical_side='right'; end
                end
                force_sd = gtech_compute_grf_cop_stride(trial_data, stride_time, ...
                    stride_pct, physical_side, subject_mass, NUM_POINTS, mode);
                if ~isempty(force_sd)
                    suffix=output_side{1};
                    stride_data.(['vertical_grf_' suffix '_BW'])=force_sd.vertical_grf_BW;
                    stride_data.(['anterior_grf_' suffix '_BW'])=force_sd.anterior_grf_BW;
                    stride_data.(['lateral_grf_' suffix '_BW'])=force_sd.lateral_grf_BW;
                    stride_data.(['cop_anterior_' suffix '_m'])=force_sd.cop_ant_m;
                    stride_data.(['cop_vertical_' suffix '_m'])=force_sd.cop_vert_m;
                    stride_data.(['cop_lateral_' suffix '_m'])=force_sd.cop_lat_m;
                    % Preserve the existing ipsilateral moment path only.
                    if strcmp(suffix,'ipsi') && any(strcmpi(mode,{'treadmill','ramp','stair'}))
                        stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg=force_sd.ankle_moment_Nm_kg;
                    end
                end
            end
        end

        % Create single row with arrays for this stride
        row = table();
        row.subject = {subject_str};
        row.subject_metadata = {subject_metadata};
        row.task = {task};
        row.task_id = {task_id};
        row.task_info = {task_info};
        % Simple step numbering (no leg suffix since we're not duplicating)
        row.step = sprintf('%03d', s);
        row = locohub_add_provenance(row, trial_data.source_recording_id, ...
            sprintf('samples:%d:%d', stride_start_idx, stride_end_idx), leg_side, ...
            'individual_cycle', stride_start_time, stride_end_time);
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
        row.ankle_dorsiflexion_acceleration_ipsi_rad_s2 = {stride_data.ankle_dorsiflexion_acceleration_ipsi_rad_s2};
        row.knee_flexion_acceleration_ipsi_rad_s2 = {stride_data.knee_flexion_acceleration_ipsi_rad_s2};
        row.hip_flexion_acceleration_ipsi_rad_s2 = {stride_data.hip_flexion_acceleration_ipsi_rad_s2};
        
        % Contralateral kinematics
        row.ankle_dorsiflexion_angle_contra_rad = {stride_data.ankle_dorsiflexion_angle_contra_rad};
        row.knee_flexion_angle_contra_rad = {stride_data.knee_flexion_angle_contra_rad};
        row.hip_flexion_angle_contra_rad = {stride_data.hip_flexion_angle_contra_rad};
        
        % Contralateral velocities
        row.ankle_dorsiflexion_velocity_contra_rad_s = {stride_data.ankle_dorsiflexion_velocity_contra_rad_s};
        row.knee_flexion_velocity_contra_rad_s = {stride_data.knee_flexion_velocity_contra_rad_s};
        row.hip_flexion_velocity_contra_rad_s = {stride_data.hip_flexion_velocity_contra_rad_s};
        row.ankle_dorsiflexion_acceleration_contra_rad_s2 = {stride_data.ankle_dorsiflexion_acceleration_contra_rad_s2};
        row.knee_flexion_acceleration_contra_rad_s2 = {stride_data.knee_flexion_acceleration_contra_rad_s2};
        row.hip_flexion_acceleration_contra_rad_s2 = {stride_data.hip_flexion_acceleration_contra_rad_s2};
        
        % Ipsilateral kinetics
        row.ankle_dorsiflexion_moment_ipsi_Nm_kg = {stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg};
        row.knee_flexion_moment_ipsi_Nm_kg = {stride_data.knee_flexion_moment_ipsi_Nm_kg};
        row.hip_flexion_moment_ipsi_Nm_kg = {stride_data.hip_flexion_moment_ipsi_Nm_kg};
        
        % Contralateral kinetics
        row.ankle_dorsiflexion_moment_contra_Nm_kg = {stride_data.ankle_dorsiflexion_moment_contra_Nm_kg};
        row.knee_flexion_moment_contra_Nm_kg = {stride_data.knee_flexion_moment_contra_Nm_kg};
        row.hip_flexion_moment_contra_Nm_kg = {stride_data.hip_flexion_moment_contra_Nm_kg};
        
        % Ipsilateral Ground Reaction Forces
        row.grf_vertical_ipsi_BW = {stride_data.vertical_grf_ipsi_BW};
        row.grf_anterior_ipsi_BW = {stride_data.anterior_grf_ipsi_BW};
        row.grf_lateral_ipsi_BW = {stride_data.lateral_grf_ipsi_BW};
        
        % Contralateral Ground Reaction Forces
        row.grf_vertical_contra_BW = {stride_data.vertical_grf_contra_BW};
        row.grf_anterior_contra_BW = {stride_data.anterior_grf_contra_BW};
        row.grf_lateral_contra_BW = {stride_data.lateral_grf_contra_BW};
        
        % Center of pressure (ankle frame, meters)
        row.cop_anterior_ipsi_m = {stride_data.cop_anterior_ipsi_m};
        row.cop_anterior_contra_m = {stride_data.cop_anterior_contra_m};
        row.cop_lateral_ipsi_m = {stride_data.cop_lateral_ipsi_m};
        row.cop_lateral_contra_m = {stride_data.cop_lateral_contra_m};
        row.cop_vertical_ipsi_m = {stride_data.cop_vertical_ipsi_m};
        row.cop_vertical_contra_m = {stride_data.cop_vertical_contra_m};
        
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
    subject_metadata = cell(total_rows, 1);
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
    
    % Ipsilateral accelerations
    ankle_dorsiflexion_acceleration_ipsi_rad_s2 = zeros(total_rows, 1);
    knee_flexion_acceleration_ipsi_rad_s2 = zeros(total_rows, 1);
    hip_flexion_acceleration_ipsi_rad_s2 = zeros(total_rows, 1);
    
    % Contralateral kinematics
    ankle_dorsiflexion_angle_contra_rad = zeros(total_rows, 1);
    knee_flexion_angle_contra_rad = zeros(total_rows, 1);
    hip_flexion_angle_contra_rad = zeros(total_rows, 1);
    
    % Contralateral velocities
    ankle_dorsiflexion_velocity_contra_rad_s = zeros(total_rows, 1);
    knee_flexion_velocity_contra_rad_s = zeros(total_rows, 1);
    hip_flexion_velocity_contra_rad_s = zeros(total_rows, 1);
    
    % Contralateral accelerations
    ankle_dorsiflexion_acceleration_contra_rad_s2 = zeros(total_rows, 1);
    knee_flexion_acceleration_contra_rad_s2 = zeros(total_rows, 1);
    hip_flexion_acceleration_contra_rad_s2 = zeros(total_rows, 1);
    
    % Ipsilateral kinetics
    ankle_dorsiflexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    knee_flexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    hip_flexion_moment_ipsi_Nm_kg = zeros(total_rows, 1);
    
    % Contralateral kinetics
    ankle_dorsiflexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    knee_flexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    hip_flexion_moment_contra_Nm_kg = zeros(total_rows, 1);
    
    % Ipsilateral Ground Reaction Forces
    grf_vertical_ipsi_BW = zeros(total_rows, 1);
    grf_anterior_ipsi_BW = zeros(total_rows, 1);
    grf_lateral_ipsi_BW = zeros(total_rows, 1);
    
    % Contralateral Ground Reaction Forces
    grf_vertical_contra_BW = zeros(total_rows, 1);
    grf_anterior_contra_BW = zeros(total_rows, 1);
    grf_lateral_contra_BW = zeros(total_rows, 1);
    
    % Center of pressure (ankle frame, meters)
    cop_anterior_ipsi_m = zeros(total_rows, 1);
    cop_lateral_ipsi_m = zeros(total_rows, 1);
    cop_vertical_ipsi_m = zeros(total_rows, 1);
    cop_anterior_contra_m = zeros(total_rows, 1);
    cop_lateral_contra_m = zeros(total_rows, 1);
    cop_vertical_contra_m = zeros(total_rows, 1);
    
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
        if mod(stride_idx, 500) == 0
            fprintf('    Processing stride %d/%d\n', stride_idx, num_strides);
        end
        
        stride = compact_table(stride_idx, :);
        
        % Expand each point in the stride
        for p = 1:num_points
            % Copy metadata (same for all points in stride)
            subject{row_idx} = stride.subject{1};
            subject_metadata{row_idx} = stride.subject_metadata{1};
            task{row_idx} = stride.task{1};
            task_id{row_idx} = stride.task_id{1};
            task_info{row_idx} = stride.task_info{1};
            step{row_idx} = stride.observation_id{1};
            
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
            
            % Ipsilateral accelerations
            ankle_dorsiflexion_acceleration_ipsi_rad_s2(row_idx) = stride.ankle_dorsiflexion_acceleration_ipsi_rad_s2{1}(p);
            knee_flexion_acceleration_ipsi_rad_s2(row_idx) = stride.knee_flexion_acceleration_ipsi_rad_s2{1}(p);
            hip_flexion_acceleration_ipsi_rad_s2(row_idx) = stride.hip_flexion_acceleration_ipsi_rad_s2{1}(p);
            
            % Contralateral kinematics
            ankle_dorsiflexion_angle_contra_rad(row_idx) = stride.ankle_dorsiflexion_angle_contra_rad{1}(p);
            knee_flexion_angle_contra_rad(row_idx) = stride.knee_flexion_angle_contra_rad{1}(p);
            hip_flexion_angle_contra_rad(row_idx) = stride.hip_flexion_angle_contra_rad{1}(p);
            
            % Contralateral velocities
            ankle_dorsiflexion_velocity_contra_rad_s(row_idx) = stride.ankle_dorsiflexion_velocity_contra_rad_s{1}(p);
            knee_flexion_velocity_contra_rad_s(row_idx) = stride.knee_flexion_velocity_contra_rad_s{1}(p);
            hip_flexion_velocity_contra_rad_s(row_idx) = stride.hip_flexion_velocity_contra_rad_s{1}(p);
            
            % Contralateral accelerations
            ankle_dorsiflexion_acceleration_contra_rad_s2(row_idx) = stride.ankle_dorsiflexion_acceleration_contra_rad_s2{1}(p);
            knee_flexion_acceleration_contra_rad_s2(row_idx) = stride.knee_flexion_acceleration_contra_rad_s2{1}(p);
            hip_flexion_acceleration_contra_rad_s2(row_idx) = stride.hip_flexion_acceleration_contra_rad_s2{1}(p);
            
            % Ipsilateral kinetics
            ankle_dorsiflexion_moment_ipsi_Nm_kg(row_idx) = stride.ankle_dorsiflexion_moment_ipsi_Nm_kg{1}(p);
            knee_flexion_moment_ipsi_Nm_kg(row_idx) = stride.knee_flexion_moment_ipsi_Nm_kg{1}(p);
            hip_flexion_moment_ipsi_Nm_kg(row_idx) = stride.hip_flexion_moment_ipsi_Nm_kg{1}(p);
            
            % Contralateral kinetics
            ankle_dorsiflexion_moment_contra_Nm_kg(row_idx) = stride.ankle_dorsiflexion_moment_contra_Nm_kg{1}(p);
            knee_flexion_moment_contra_Nm_kg(row_idx) = stride.knee_flexion_moment_contra_Nm_kg{1}(p);
            hip_flexion_moment_contra_Nm_kg(row_idx) = stride.hip_flexion_moment_contra_Nm_kg{1}(p);
            
            % Ipsilateral Ground Reaction Forces
            grf_vertical_ipsi_BW(row_idx) = stride.grf_vertical_ipsi_BW{1}(p);
            grf_anterior_ipsi_BW(row_idx) = stride.grf_anterior_ipsi_BW{1}(p);
            grf_lateral_ipsi_BW(row_idx) = stride.grf_lateral_ipsi_BW{1}(p);
            
            % Contralateral Ground Reaction Forces
            grf_vertical_contra_BW(row_idx) = stride.grf_vertical_contra_BW{1}(p);
            grf_anterior_contra_BW(row_idx) = stride.grf_anterior_contra_BW{1}(p);
            grf_lateral_contra_BW(row_idx) = stride.grf_lateral_contra_BW{1}(p);
            
            % Center of pressure (ankle frame, meters)
            cop_anterior_ipsi_m(row_idx) = stride.cop_anterior_ipsi_m{1}(p);
            cop_lateral_ipsi_m(row_idx) = stride.cop_lateral_ipsi_m{1}(p);
            cop_vertical_ipsi_m(row_idx) = stride.cop_vertical_ipsi_m{1}(p);
            cop_anterior_contra_m(row_idx) = stride.cop_anterior_contra_m{1}(p);
            cop_lateral_contra_m(row_idx) = stride.cop_lateral_contra_m{1}(p);
            cop_vertical_contra_m(row_idx) = stride.cop_vertical_contra_m{1}(p);
            
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
    expanded = table(subject, subject_metadata, task, task_id, task_info, step, phase_ipsi, phase_ipsi_dot, ...
        ankle_dorsiflexion_angle_ipsi_rad, knee_flexion_angle_ipsi_rad, hip_flexion_angle_ipsi_rad, ...
        ankle_dorsiflexion_velocity_ipsi_rad_s, knee_flexion_velocity_ipsi_rad_s, hip_flexion_velocity_ipsi_rad_s, ...
        ankle_dorsiflexion_acceleration_ipsi_rad_s2, knee_flexion_acceleration_ipsi_rad_s2, hip_flexion_acceleration_ipsi_rad_s2, ...
        ankle_dorsiflexion_angle_contra_rad, knee_flexion_angle_contra_rad, hip_flexion_angle_contra_rad, ...
        ankle_dorsiflexion_velocity_contra_rad_s, knee_flexion_velocity_contra_rad_s, hip_flexion_velocity_contra_rad_s, ...
        ankle_dorsiflexion_acceleration_contra_rad_s2, knee_flexion_acceleration_contra_rad_s2, hip_flexion_acceleration_contra_rad_s2, ...
        ankle_dorsiflexion_moment_ipsi_Nm_kg, knee_flexion_moment_ipsi_Nm_kg, hip_flexion_moment_ipsi_Nm_kg, ...
        ankle_dorsiflexion_moment_contra_Nm_kg, knee_flexion_moment_contra_Nm_kg, hip_flexion_moment_contra_Nm_kg, ...
        grf_vertical_ipsi_BW, grf_anterior_ipsi_BW, grf_lateral_ipsi_BW, ...
        grf_vertical_contra_BW, grf_anterior_contra_BW, grf_lateral_contra_BW, ...
        cop_anterior_ipsi_m, cop_lateral_ipsi_m, cop_vertical_ipsi_m, ...
        cop_anterior_contra_m, cop_lateral_contra_m, cop_vertical_contra_m, ...
        pelvis_sagittal_angle_rad, trunk_sagittal_angle_rad, ...
        pelvis_sagittal_velocity_rad_s, trunk_sagittal_velocity_rad_s, ...
        thigh_sagittal_angle_ipsi_rad, shank_sagittal_angle_ipsi_rad, foot_sagittal_angle_ipsi_rad, ...
        thigh_sagittal_velocity_ipsi_rad_s, shank_sagittal_velocity_ipsi_rad_s, foot_sagittal_velocity_ipsi_rad_s, ...
        thigh_sagittal_angle_contra_rad, shank_sagittal_angle_contra_rad, foot_sagittal_angle_contra_rad, ...
        thigh_sagittal_velocity_contra_rad_s, shank_sagittal_velocity_contra_rad_s, foot_sagittal_velocity_contra_rad_s);
    provenance_columns = {'source_recording_id', 'observation_id', 'reference_side', ...
        'observation_type', 'source_start_time_s', 'source_end_time_s'};
    for k = 1:numel(provenance_columns)
        name = provenance_columns{k};
        expanded.(name) = repelem(compact_table.(name), num_points, 1);
    end
end

%% Helper Functions

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
