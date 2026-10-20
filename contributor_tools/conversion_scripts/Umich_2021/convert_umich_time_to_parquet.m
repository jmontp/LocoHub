clearvars -except Streaming
addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'matlab_common'));

INPUT_SAMPLING_RATE_HZ = 100;
OUTPUT_SAMPLING_RATE_HZ = 200;

subject_source_dir = getenv('UMICH_STREAMING_SUBJECT_DIR');
use_subject_files = ~isempty(subject_source_dir) && isfolder(subject_source_dir);
if use_subject_files
    subject_files = dir(fullfile(subject_source_dir, 'AB*.mat'));
    subjects = erase({subject_files.name}, '.mat')';
else
    if exist('Streaming', 'var') == 0
        load('Streaming.mat');
    end
    dataset = Streaming;
    subjects = fieldnames(dataset);
end

output_path = fullfile('..', '..', '..', 'converted_datasets', 'umich_2021_time.parquet');
shard_dir = tempname(fileparts(output_path));
mkdir(shard_dir);
shard_counter = 0;
total_rows = 0;
step_counter = 1;

for subject_idx = 1:length(subjects)
    subject = subjects{subject_idx};
    if use_subject_files
        loaded_subject = load(fullfile(subject_source_dir, [subject '.mat']));
        if isfield(loaded_subject, subject)
            subject_data = loaded_subject.(subject);
        elseif isfield(loaded_subject, 'subject_data')
            subject_data = loaded_subject.subject_data;
        elseif isfield(loaded_subject, 'Streaming') && isfield(loaded_subject.Streaming, subject)
            subject_data = loaded_subject.Streaming.(subject);
        else
            error('Subject file %s does not contain %s.', subject, subject);
        end
    else
        subject_data = dataset.(subject);
    end

    [subject_str, subject_metadata, body_mass] = get_subject_metadata(subject, subject_data);

    fprintf('\n========================================\n');
    fprintf('Processing %s (%d/%d)\n', subject_str, subject_idx, length(subjects));
    fprintf('========================================\n');

    if isfield(subject_data, 'Tread')
        fprintf('  Processing treadmill segments...\n');
        [subject_rows, step_counter] = process_treadmill_trials( ...
            subject_data.Tread, subject_str, subject_metadata, body_mass, step_counter, OUTPUT_SAMPLING_RATE_HZ);
        [shard_counter, total_rows] = write_table_shard(subject_rows, shard_dir, shard_counter, total_rows);
        clear subject_rows
    end

    if isfield(subject_data, 'Run')
        fprintf('  Processing running trials...\n');
        [subject_rows, step_counter] = process_run_trials( ...
            subject_data.Run, subject_str, subject_metadata, body_mass, step_counter, OUTPUT_SAMPLING_RATE_HZ);
        [shard_counter, total_rows] = write_table_shard(subject_rows, shard_dir, shard_counter, total_rows);
        clear subject_rows
    end

    if isfield(subject_data, 'Wtr')
        fprintf('  Processing walk-to-run transition trials...\n');
        [subject_rows, step_counter] = process_wtr_trials( ...
            subject_data.Wtr, subject_str, subject_metadata, body_mass, step_counter, OUTPUT_SAMPLING_RATE_HZ);
        [shard_counter, total_rows] = write_table_shard(subject_rows, shard_dir, shard_counter, total_rows);
        clear subject_rows
    end

    if isfield(subject_data, 'Stair')
        fprintf('  Processing stair trials...\n');
        [subject_rows, step_counter] = process_stair_trials( ...
            subject_data.Stair, subject_str, subject_metadata, body_mass, step_counter, OUTPUT_SAMPLING_RATE_HZ);
        [shard_counter, total_rows] = write_table_shard(subject_rows, shard_dir, shard_counter, total_rows);
        clear subject_rows
    end
    clear subject_data loaded_subject
end

merge_parquet_shards(shard_dir, output_path);
rmdir(shard_dir, 's');
fprintf('\nSaved time-indexed data to: %s\n', output_path);
fprintf('Subjects: %d\n', length(subjects));
fprintf('Rows: %d\n', total_rows);


function [shard_counter, total_rows] = write_table_shard(rows, shard_dir, shard_counter, total_rows)
    if isempty(rows)
        return;
    end
    shard_counter = shard_counter + 1;
    shard_path = fullfile(shard_dir, sprintf('%05d.parquet', shard_counter));
    parquetwrite(shard_path, rows);
    total_rows = total_rows + height(rows);
end


function merge_parquet_shards(shard_dir, output_path)
    python_executable = getenv('LOCOHUB_PYTHON');
    if isempty(python_executable)
        if ispc
            python_executable = 'wsl.exe python3';
        else
            python_executable = 'python3';
        end
    end
    merger = fullfile('..', '..', 'common', 'merge_parquet_shards.py');
    if startsWith(python_executable, 'wsl.exe')
        % wsl.exe python3 runs inside WSL and needs POSIX paths, so translate
        % Windows drive paths (S:\a\b or S:/a/b) to /mnt/s/a/b.
        merger = win2wsl(merger);
        shard_dir = win2wsl(shard_dir);
        output_path = win2wsl(output_path);
    end
    command = sprintf('%s "%s" "%s" "%s" --row-group-size 65536', ...
        python_executable, merger, shard_dir, output_path);
    status = system(command);
    if status ~= 0
        error('Shard merge failed. Recoverable shards remain in %s.', shard_dir);
    end
end


function p = win2wsl(p)
    p = strrep(p, '\', '/');
    if numel(p) >= 2 && p(2) == ':'
        drive = lower(p(1));
        p = ['/mnt/' drive p(3:end)];
    end
end


function [subject_str, subject_metadata, body_mass] = get_subject_metadata(subject, subject_data)
    subject_num = subject(end-1:end);
    subject_str = strcat('UM21_AB', subject_num);

    if isfield(subject_data, 'ParticipantDetails')
        details = subject_data.ParticipantDetails;

        sex_idx = find(strcmp(details(:,1), 'Sex'));
        age_idx = find(strcmp(details(:,1), 'Age'));
        mass_idx = find(strcmp(details(:,1), 'Bodymass'));
        height_idx = find(strcmp(details(:,1), 'Height'));

        age = NaN;
        body_mass = NaN;
        height_m = NaN;
        sex_char = 'unknown';

        if ~isempty(sex_idx)
            sex_code = details{sex_idx, 2};
            if isequal(sex_code, 1)
                sex_char = 'F';
            elseif isequal(sex_code, 2)
                sex_char = 'M';
            end
        end
        if ~isempty(age_idx), age = details{age_idx, 2}; end
        if ~isempty(mass_idx), body_mass = details{mass_idx, 2}; end
        if ~isempty(height_idx), height_m = details{height_idx, 2} / 1000; end
        if ~isscalar(body_mass) || ~isfinite(body_mass) || body_mass <= 0, body_mass = NaN; end

        subject_metadata = sprintf('age:%d,sex:%s,height_m:%.2f,weight_kg:%.1f', ...
            age, sex_char, height_m, body_mass);
    else
        body_mass = NaN;
        subject_metadata = 'age:unknown,sex:unknown,height_m:unknown,weight_kg:unknown';
    end
end


function [rows, step_counter] = process_treadmill_trials(tread_data, subject_str, subject_metadata, body_mass, step_counter, sampling_rate_hz)
    rows = table;

    incline_map = containers.Map( ...
        {'d10', 'd5', 'i0', 'i10', 'i5'}, ...
        {-10, -5, 0, 10, 5});
    speed_map = containers.Map( ...
        {'s0x8', 's1', 's1x2', 'a0x2', 'a0x5', 'd0x2', 'd0x5'}, ...
        {0.8, 1.0, 1.2, 0.2, 0.5, 0.2, 0.5});

    incline_fields = fieldnames(tread_data);
    for incline_idx = 1:length(incline_fields)
        incline_name = incline_fields{incline_idx};
        if ~isKey(incline_map, incline_name)
            continue;
        end

        incline_value = incline_map(incline_name);
        incline_data = tread_data.(incline_name);
        incline_data.source_recording_id = sprintf('um21:Streaming/%s/Tread/%s', erase(subject_str, 'UM21_'), incline_name);

        if isfield(incline_data, 'events') && isfield(incline_data.events, 'tasks') && isfield(incline_data.events, 'cutPoints')
            tasks = incline_data.events.tasks;
            cut_points = incline_data.events.cutPoints;

            for task_idx = 1:length(tasks)
                if task_idx > size(cut_points, 1)
                    break;
                end

                speed_name = tasks{task_idx};
                if ~isKey(speed_map, speed_name)
                    continue;
                end

                speed_value = speed_map(speed_name);
                segment_start = cut_points(task_idx, 1);
                segment_end = cut_points(task_idx, 2);
                collection_id = sprintf('Tread_%s_%s_seg%02d', incline_name, speed_name, task_idx);

                [task, task_id, task_info] = map_treadmill_task(incline_value, speed_name, speed_value, collection_id, sampling_rate_hz);
                trial_rows = process_trial_time( ...
                    incline_data, subject_str, subject_metadata, body_mass, task, task_id, task_info, ...
                    collection_id, step_counter, sampling_rate_hz, 'segment', segment_start, segment_end);

                if ~isempty(trial_rows)
                    rows = [rows; trial_rows];
                    step_counter = step_counter + 1;
                end
            end
        else
            collection_id = sprintf('Tread_%s_full', incline_name);
            [task, task_id, task_info] = map_treadmill_task(incline_value, 'unknown', NaN, collection_id, sampling_rate_hz);
            trial_rows = process_trial_time( ...
                incline_data, subject_str, subject_metadata, body_mass, task, task_id, task_info, ...
                collection_id, step_counter, sampling_rate_hz, 'trial');
            if ~isempty(trial_rows)
                rows = [rows; trial_rows];
                step_counter = step_counter + 1;
            end
        end
    end
end


function [task, task_id, task_info] = map_treadmill_task(incline_value, speed_name, speed_value, collection_id, sampling_rate_hz)
    if startsWith(speed_name, 'a') || startsWith(speed_name, 'd')
        task = 'transition';
        if startsWith(speed_name, 'a')
            task_id = 'walk_transition_accel';
            transition_phase = 'acceleration';
        else
            task_id = 'walk_transition_decel';
            transition_phase = 'deceleration';
        end

        if isnan(speed_value)
            speed_fragment = 'acceleration_m_s2:unknown';
        else
            speed_fragment = sprintf('acceleration_m_s2:%.1f', speed_value);
        end

        task_info = sprintf(['gait_transition:true,transition_from:level_walking,' ...
            'transition_to:level_walking,transition_phase:%s,%s,' ...
            'incline_deg:%d,treadmill:true,surface:treadmill,' ...
            'time_scope:continuous_trial,time_reset_per:segment,' ...
            'collection_source:Streaming,collection_id:%s,' ...
            'sampling_rate_hz:%.0f,reference_leg:right'], ...
            transition_phase, speed_fragment, incline_value, collection_id, sampling_rate_hz);
        return;
    end

    if incline_value < 0
        task = 'decline_walking';
        task_id = sprintf('decline_%ddeg', abs(incline_value));
    elseif incline_value > 0
        task = 'incline_walking';
        task_id = sprintf('incline_%ddeg', incline_value);
    else
        task = 'level_walking';
        task_id = 'level';
    end

    if isnan(speed_value)
        speed_fragment = 'speed_m_s:unknown';
    else
        speed_fragment = sprintf('speed_m_s:%.1f', speed_value);
    end

    task_info = sprintf(['incline_deg:%d,%s,treadmill:true,surface:treadmill,' ...
        'time_scope:continuous_trial,time_reset_per:segment,' ...
        'collection_source:Streaming,collection_id:%s,' ...
        'sampling_rate_hz:%.0f,reference_leg:right'], ...
        incline_value, speed_fragment, collection_id, sampling_rate_hz);
end


function [rows, step_counter] = process_run_trials(run_data, subject_str, subject_metadata, body_mass, step_counter, sampling_rate_hz)
    rows = table;

    run_speed_map = containers.Map( ...
        {'s1x8', 's2', 's2x0', 's2x2', 's2x4'}, ...
        {1.8, 2.0, 2.0, 2.2, 2.4});

    run_fields = fieldnames(run_data);
    for run_idx = 1:length(run_fields)
        speed_name = run_fields{run_idx};
        if ~isKey(run_speed_map, speed_name)
            continue;
        end

        speed_value = run_speed_map(speed_name);
        trial_struct = run_data.(speed_name);
        trial_struct.source_recording_id = sprintf('um21:Streaming/%s/Run/%s', erase(subject_str, 'UM21_'), speed_name);
        collection_id = sprintf('Run_%s', speed_name);
        speed_label = strrep(sprintf('%.1f', speed_value), '.', '_');

        task_info = sprintf(['speed_m_s:%.1f,treadmill:false,surface:overground,' ...
            'time_scope:continuous_trial,time_reset_per:trial,' ...
            'collection_source:Streaming,collection_id:%s,' ...
            'sampling_rate_hz:%.0f,reference_leg:right'], ...
            speed_value, collection_id, sampling_rate_hz);

        trial_rows = process_trial_time( ...
            trial_struct, subject_str, subject_metadata, body_mass, 'run', ...
            sprintf('run_%sms', speed_label), task_info, collection_id, step_counter, sampling_rate_hz, 'trial');

        if ~isempty(trial_rows)
            rows = [rows; trial_rows];
            step_counter = step_counter + 1;
        end
    end
end


function [rows, step_counter] = process_wtr_trials(wtr_data, subject_str, subject_metadata, body_mass, step_counter, sampling_rate_hz)
    rows = table;

    if isfield(wtr_data, 'jointAngles')
        trial_names = {'trial'};
        trial_structs = {wtr_data};
    else
        trial_names = fieldnames(wtr_data);
        trial_structs = cell(size(trial_names));
        for idx = 1:length(trial_names)
            trial_structs{idx} = wtr_data.(trial_names{idx});
        end
    end

    for idx = 1:length(trial_names)
        trial_name = trial_names{idx};
        trial_struct = trial_structs{idx};
        if isfield(wtr_data, 'jointAngles')
            trial_struct.source_recording_id = sprintf('um21:Streaming/%s/Wtr', erase(subject_str, 'UM21_'));
        else
            trial_struct.source_recording_id = sprintf('um21:Streaming/%s/Wtr/%s', erase(subject_str, 'UM21_'), trial_name);
        end

        collection_id = sprintf('Wtr_%s', trial_name);
        task_info = sprintf(['gait_transition:true,transition_from:level_walking,' ...
            'transition_to:run,initial_speed_m_s:1.2,final_speed_m_s:2.5,' ...
            'treadmill:true,surface:treadmill,time_scope:continuous_trial,' ...
            'time_reset_per:trial,collection_source:Streaming,collection_id:%s,' ...
            'sampling_rate_hz:%.0f,reference_leg:right'], collection_id, sampling_rate_hz);

        trial_rows = process_trial_time( ...
            trial_struct, subject_str, subject_metadata, body_mass, 'transition', ...
            'walk_to_run', task_info, collection_id, step_counter, sampling_rate_hz, 'trial');

        if ~isempty(trial_rows)
            rows = [rows; trial_rows];
            step_counter = step_counter + 1;
        end
    end
end


function [rows, step_counter] = process_stair_trials(stair_data, subject_str, subject_metadata, body_mass, step_counter, sampling_rate_hz)
    rows = table;

    stair_height_map = containers.Map( ...
        {'s20dg', 's25dg', 's30dg', 's35dg'}, ...
        {97, 120, 146, 162});
    stair_depth_map = containers.Map( ...
        {'s20dg', 's25dg', 's30dg', 's35dg'}, ...
        {315, 305, 295, 285});
    stair_incline_map = containers.Map( ...
        {'s20dg', 's25dg', 's30dg', 's35dg'}, ...
        {20, 25, 30, 35});

    stair_fields = fieldnames(stair_data);
    for stair_idx = 1:length(stair_fields)
        trial_name = stair_fields{stair_idx};
        trial_struct = stair_data.(trial_name);
        trial_struct.source_recording_id = sprintf('um21:Streaming/%s/Stair/%s', erase(subject_str, 'UM21_'), trial_name);

        underscore_idx = strfind(trial_name, '_');
        if isempty(underscore_idx)
            continue;
        end

        incline_str = trial_name(1:underscore_idx(1)-1);
        trial_num = str2double(trial_name(underscore_idx(1)+1:end));
        if ~isKey(stair_height_map, incline_str) || isnan(trial_num)
            continue;
        end

        if mod(trial_num, 2) == 1
            task = 'stair_ascent';
            task_id = 'stair_ascent';
        else
            task = 'stair_descent';
            task_id = 'stair_descent';
        end

        collection_id = sprintf('Stair_%s', trial_name);
        task_info = sprintf(['step_height_m:%.3f,step_width_m:%.3f,incline_deg:%d,' ...
            'time_scope:continuous_trial,time_reset_per:trial,' ...
            'collection_source:Streaming,collection_id:%s,' ...
            'sampling_rate_hz:%.0f,reference_leg:right'], ...
            stair_height_map(incline_str) / 1000, stair_depth_map(incline_str) / 1000, ...
            stair_incline_map(incline_str), collection_id, sampling_rate_hz);

        trial_rows = process_trial_time( ...
            trial_struct, subject_str, subject_metadata, body_mass, task, task_id, ...
            task_info, collection_id, step_counter, sampling_rate_hz, 'trial');

        if ~isempty(trial_rows)
            rows = [rows; trial_rows];
            step_counter = step_counter + 1;
        end
    end
end


function trial_table = process_trial_time( ...
    trial_struct, subject_str, subject_metadata, body_mass, task, task_id, task_info, ...
    collection_id, step_id, sampling_rate_hz, time_reset_per_label, segment_start, segment_end)

    if nargin < 11 || isempty(time_reset_per_label)
        time_reset_per_label = 'trial';
    end
    if nargin < 12 || isempty(segment_start)
        segment_start = 1;
    end
    if nargin < 13 || isempty(segment_end)
        segment_end = size(trial_struct.jointAngles.RHipAngles, 1);
    end

    trial_table = table;

    if ~isfield(trial_struct, 'jointAngles')
        return;
    end

    angles = trial_struct.jointAngles;

    if ~isfield(angles, 'RHipAngles') || ~isfield(angles, 'LHipAngles') || ...
            ~isfield(angles, 'RKneeAngles') || ~isfield(angles, 'LKneeAngles') || ...
            ~isfield(angles, 'RAnkleAngles') || ~isfield(angles, 'LAnkleAngles')
        return;
    end

    segment_start = max(1, round(segment_start));
    segment_end = min(round(segment_end), size(angles.RHipAngles, 1));
    if segment_end <= segment_start
        return;
    end
    [segment_end, angles_are_valid, rejection_reason] = sanitize_angle_segment( ...
        angles, segment_start, segment_end);
    if ~angles_are_valid
        fprintf('      Warning: skipping corrupt angle segment (%s)\n', rejection_reason);
        return;
    end
    if segment_end <= segment_start
        return;
    end

    input_sampling_rate_hz = 100;
    idx = segment_start:segment_end;
    source_time_s = ((0:length(idx)-1)' ./ input_sampling_rate_hz);
    time_s = ((0:round(source_time_s(end) * sampling_rate_hz))' ./ sampling_rate_hz);
    n_samples = length(time_s);
    dt = 1 / sampling_rate_hz;
    body_weight_N = body_mass * 9.81;
    deg2rad_factor = pi / 180;

    sagittal_plane = 1;
    frontal_plane = 2;
    transverse_plane = 3;

    right_hip_flex = resample_signal(angles.RHipAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    left_hip_flex = resample_signal(angles.LHipAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    right_hip_add = resample_signal(angles.RHipAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    left_hip_add = resample_signal(angles.LHipAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    right_hip_rot = resample_signal(angles.RHipAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);
    left_hip_rot = resample_signal(angles.LHipAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);

    % The UMich raw knee channel is already flexion-positive.
    right_knee_flex = resample_signal(angles.RKneeAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    left_knee_flex = resample_signal(angles.LKneeAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    right_knee_add = resample_signal(angles.RKneeAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    left_knee_add = resample_signal(angles.LKneeAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    right_knee_rot = resample_signal(angles.RKneeAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);
    left_knee_rot = resample_signal(angles.LKneeAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);

    right_ankle_flex = resample_signal(angles.RAnkleAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    left_ankle_flex = resample_signal(angles.LAnkleAngles(idx, sagittal_plane) * deg2rad_factor, source_time_s, time_s);
    if strcmp(task, 'incline_walking')
        right_ankle_flex = apply_90_degree_correction(right_ankle_flex);
        left_ankle_flex = apply_90_degree_correction(left_ankle_flex);
    end
    right_ankle_add = resample_signal(angles.RAnkleAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    left_ankle_add = resample_signal(angles.LAnkleAngles(idx, frontal_plane) * deg2rad_factor, source_time_s, time_s);
    right_ankle_rot = resample_signal(angles.RAnkleAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);
    left_ankle_rot = resample_signal(angles.LAnkleAngles(idx, transverse_plane) * deg2rad_factor, source_time_s, time_s);
    nan_signal = NaN(n_samples, 1);

    right_hip_flex_vel = gradient(right_hip_flex, dt);
    left_hip_flex_vel = gradient(left_hip_flex, dt);
    right_hip_add_vel = gradient(right_hip_add, dt);
    left_hip_add_vel = gradient(left_hip_add, dt);
    right_hip_rot_vel = gradient(right_hip_rot, dt);
    left_hip_rot_vel = gradient(left_hip_rot, dt);

    right_knee_flex_vel = gradient(right_knee_flex, dt);
    left_knee_flex_vel = gradient(left_knee_flex, dt);
    right_knee_add_vel = gradient(right_knee_add, dt);
    left_knee_add_vel = gradient(left_knee_add, dt);
    right_knee_rot_vel = gradient(right_knee_rot, dt);
    left_knee_rot_vel = gradient(left_knee_rot, dt);

    right_ankle_flex_vel = gradient(right_ankle_flex, dt);
    left_ankle_flex_vel = gradient(left_ankle_flex, dt);
    right_ankle_add_vel = gradient(right_ankle_add, dt);
    left_ankle_add_vel = gradient(left_ankle_add, dt);
    right_ankle_rot_vel = gradient(right_ankle_rot, dt);
    left_ankle_rot_vel = gradient(left_ankle_rot, dt);

    right_pelvis_sag = get_optional_angle(angles, 'RPelvisAngles', idx, sagittal_plane, source_time_s, time_s, deg2rad_factor, nan_signal);
    left_pelvis_sag = get_optional_angle(angles, 'LPelvisAngles', idx, sagittal_plane, source_time_s, time_s, deg2rad_factor, nan_signal);
    right_pelvis_front = get_optional_angle(angles, 'RPelvisAngles', idx, frontal_plane, source_time_s, time_s, deg2rad_factor, nan_signal);
    left_pelvis_front = get_optional_angle(angles, 'LPelvisAngles', idx, frontal_plane, source_time_s, time_s, deg2rad_factor, nan_signal);
    right_pelvis_trans = get_optional_angle(angles, 'RPelvisAngles', idx, transverse_plane, source_time_s, time_s, deg2rad_factor, nan_signal);
    left_pelvis_trans = get_optional_angle(angles, 'LPelvisAngles', idx, transverse_plane, source_time_s, time_s, deg2rad_factor, nan_signal);

    right_foot_sag = get_optional_foot_angle(angles, 'RFootProgressAngles', idx, source_time_s, time_s, deg2rad_factor, nan_signal);
    left_foot_sag = get_optional_foot_angle(angles, 'LFootProgressAngles', idx, source_time_s, time_s, deg2rad_factor, nan_signal);

    if ~all(isnan(right_foot_sag))
        right_shank_sag = right_foot_sag - right_ankle_flex;
        right_thigh_sag = right_shank_sag + right_knee_flex;
        right_pelvis_from_chain = right_thigh_sag - right_hip_flex;
    else
        right_pelvis_from_chain = nan_signal;
        right_thigh_sag = nan_signal;
        right_shank_sag = nan_signal;
    end

    if ~all(isnan(left_foot_sag))
        left_shank_sag = left_foot_sag - left_ankle_flex;
        left_thigh_sag = left_shank_sag + left_knee_flex;
        left_pelvis_from_chain = left_thigh_sag - left_hip_flex;
    else
        left_pelvis_from_chain = nan_signal;
        left_thigh_sag = nan_signal;
        left_shank_sag = nan_signal;
    end

    % A dataset has one pelvis orientation. Use the measured pelvis when it
    % is available, then derive both limb segment chains from that shared
    % origin so the hip, knee, and ankle identities hold simultaneously.
    pelvis_sag = choose_pelvis_signal(right_pelvis_sag, left_pelvis_sag, nan_signal);
    if all(isnan(pelvis_sag))
        pelvis_sag = choose_pelvis_signal(right_pelvis_from_chain, left_pelvis_from_chain, nan_signal);
    end
    pelvis_front = choose_pelvis_signal(right_pelvis_front, left_pelvis_front, nan_signal);
    pelvis_trans = choose_pelvis_signal(right_pelvis_trans, left_pelvis_trans, nan_signal);

    right_thigh_sag = pelvis_sag + right_hip_flex;
    right_shank_sag = right_thigh_sag - right_knee_flex;
    right_foot_sag = right_shank_sag + right_ankle_flex;
    left_thigh_sag = pelvis_sag + left_hip_flex;
    left_shank_sag = left_thigh_sag - left_knee_flex;
    left_foot_sag = left_shank_sag + left_ankle_flex;

    pelvis_sag_vel = gradient(pelvis_sag, dt);
    right_thigh_sag_vel = gradient(right_thigh_sag, dt);
    left_thigh_sag_vel = gradient(left_thigh_sag, dt);
    right_shank_sag_vel = gradient(right_shank_sag, dt);
    left_shank_sag_vel = gradient(left_shank_sag, dt);
    right_foot_sag_vel = gradient(right_foot_sag, dt);
    left_foot_sag_vel = gradient(left_foot_sag, dt);

    right_hip_flex_acc = gradient(right_hip_flex_vel, dt);
    left_hip_flex_acc = gradient(left_hip_flex_vel, dt);
    right_knee_flex_acc = gradient(right_knee_flex_vel, dt);
    left_knee_flex_acc = gradient(left_knee_flex_vel, dt);
    right_ankle_flex_acc = gradient(right_ankle_flex_vel, dt);
    left_ankle_flex_acc = gradient(left_ankle_flex_vel, dt);

    if isfield(trial_struct, 'jointMoments') && ...
            isfield(trial_struct.jointMoments, 'RHipMoment') && isfield(trial_struct.jointMoments, 'LHipMoment') && ...
            isfield(trial_struct.jointMoments, 'RKneeMoment') && isfield(trial_struct.jointMoments, 'LKneeMoment') && ...
            isfield(trial_struct.jointMoments, 'RAnkleMoment') && isfield(trial_struct.jointMoments, 'LAnkleMoment')
        moments = trial_struct.jointMoments;

        % Streaming.mat moments are already normalized by body mass (Nm/kg).
        right_hip_flex_mom = resample_signal(moments.RHipMoment(idx, sagittal_plane), source_time_s, time_s);
        left_hip_flex_mom = resample_signal(moments.LHipMoment(idx, sagittal_plane), source_time_s, time_s);
        right_hip_add_mom = resample_signal(moments.RHipMoment(idx, frontal_plane), source_time_s, time_s);
        left_hip_add_mom = resample_signal(moments.LHipMoment(idx, frontal_plane), source_time_s, time_s);
        right_hip_rot_mom = resample_signal(moments.RHipMoment(idx, transverse_plane), source_time_s, time_s);
        left_hip_rot_mom = resample_signal(moments.LHipMoment(idx, transverse_plane), source_time_s, time_s);

        % Match current phase converter default behavior: keep native knee-moment sign.
        right_knee_flex_mom = resample_signal(moments.RKneeMoment(idx, sagittal_plane), source_time_s, time_s);
        left_knee_flex_mom = resample_signal(moments.LKneeMoment(idx, sagittal_plane), source_time_s, time_s);
        right_knee_add_mom = resample_signal(moments.RKneeMoment(idx, frontal_plane), source_time_s, time_s);
        left_knee_add_mom = resample_signal(moments.LKneeMoment(idx, frontal_plane), source_time_s, time_s);
        right_knee_rot_mom = resample_signal(moments.RKneeMoment(idx, transverse_plane), source_time_s, time_s);
        left_knee_rot_mom = resample_signal(moments.LKneeMoment(idx, transverse_plane), source_time_s, time_s);

        right_ankle_flex_mom = resample_signal(moments.RAnkleMoment(idx, sagittal_plane), source_time_s, time_s);
        left_ankle_flex_mom = resample_signal(moments.LAnkleMoment(idx, sagittal_plane), source_time_s, time_s);
        right_ankle_add_mom = resample_signal(moments.RAnkleMoment(idx, frontal_plane), source_time_s, time_s);
        left_ankle_add_mom = resample_signal(moments.LAnkleMoment(idx, frontal_plane), source_time_s, time_s);
        right_ankle_rot_mom = resample_signal(moments.RAnkleMoment(idx, transverse_plane), source_time_s, time_s);
        left_ankle_rot_mom = resample_signal(moments.LAnkleMoment(idx, transverse_plane), source_time_s, time_s);
    else
        right_hip_flex_mom = nan_signal;
        left_hip_flex_mom = nan_signal;
        right_hip_add_mom = nan_signal;
        left_hip_add_mom = nan_signal;
        right_hip_rot_mom = nan_signal;
        left_hip_rot_mom = nan_signal;
        right_knee_flex_mom = nan_signal;
        left_knee_flex_mom = nan_signal;
        right_knee_add_mom = nan_signal;
        left_knee_add_mom = nan_signal;
        right_knee_rot_mom = nan_signal;
        left_knee_rot_mom = nan_signal;
        right_ankle_flex_mom = nan_signal;
        left_ankle_flex_mom = nan_signal;
        right_ankle_add_mom = nan_signal;
        left_ankle_add_mom = nan_signal;
        right_ankle_rot_mom = nan_signal;
        left_ankle_rot_mom = nan_signal;
    end

    if isfield(trial_struct, 'forceplates') && isfield(trial_struct.forceplates, 'RForce') && isfield(trial_struct.forceplates, 'LForce')
        force_idx_start = (segment_start - 1) * 10 + 1;
        force_idx_end_r = min(segment_end * 10, size(trial_struct.forceplates.RForce, 1));
        force_idx_end_l = min(segment_end * 10, size(trial_struct.forceplates.LForce, 1));
        force_idx_r = force_idx_start:10:force_idx_end_r;
        force_idx_l = force_idx_start:10:force_idx_end_l;

        % Raw force-plate axes: column 2 AP, column 3 vertical/down, column 1 ML/left.
        x = 2;
        y = 3;
        z = 1;

        force_time_ipsi = ((0:length(force_idx_r)-1)' ./ input_sampling_rate_hz);
        force_time_contra = ((0:length(force_idx_l)-1)' ./ input_sampling_rate_hz);

        grf_vertical_ipsi = resample_signal(-trial_struct.forceplates.RForce(force_idx_r, y) ./ body_weight_N, force_time_ipsi, time_s);
        grf_vertical_contra = resample_signal(-trial_struct.forceplates.LForce(force_idx_l, y) ./ body_weight_N, force_time_contra, time_s);
        grf_anterior_ipsi = resample_signal(trial_struct.forceplates.RForce(force_idx_r, x) ./ body_weight_N, force_time_ipsi, time_s);
        grf_anterior_contra = resample_signal(trial_struct.forceplates.LForce(force_idx_l, x) ./ body_weight_N, force_time_contra, time_s);
        grf_lateral_ipsi = resample_signal(-trial_struct.forceplates.RForce(force_idx_r, z) ./ body_weight_N, force_time_ipsi, time_s);
        grf_lateral_contra = resample_signal(-trial_struct.forceplates.LForce(force_idx_l, z) ./ body_weight_N, force_time_contra, time_s);

        % CoP columns are contact-relative metres. Raw CoP is in a global
        % treadmill frame and millimetres, so zero every stance episode at
        % its initial contact rather than subtracting a moving ankle marker.
        cop_vertical_ipsi = nan_signal;
        cop_vertical_contra = nan_signal;
        cop_lateral_ipsi = nan_signal;
        cop_lateral_contra = nan_signal;
        cop_anterior_ipsi = nan_signal;
        cop_anterior_contra = nan_signal;
        if isfield(trial_struct.forceplates, 'RCoP') && isfield(trial_struct.forceplates, 'LCoP')
            % The force-plate AP position axis decreases heel-to-toe, so
            % negate it for standardized Anterior+ output.
            r_cop_anterior = resample_signal(-trial_struct.forceplates.RCoP(force_idx_r, x) ./ 1000, force_time_ipsi, time_s);
            l_cop_anterior = resample_signal(-trial_struct.forceplates.LCoP(force_idx_l, x) ./ 1000, force_time_contra, time_s);
            r_cop_lateral = resample_signal(-trial_struct.forceplates.RCoP(force_idx_r, z) ./ 1000, force_time_ipsi, time_s);
            l_cop_lateral = resample_signal(-trial_struct.forceplates.LCoP(force_idx_l, z) ./ 1000, force_time_contra, time_s);
            r_cop_vertical = resample_signal(trial_struct.forceplates.RCoP(force_idx_r, y) ./ 1000, force_time_ipsi, time_s);
            l_cop_vertical = resample_signal(trial_struct.forceplates.LCoP(force_idx_l, y) ./ 1000, force_time_contra, time_s);

            % Gate stance episodes at 0.2 BW (matching the GTech 2023 CoP template) so
            % the per-episode zero origin is a real heel-strike CoP, not a near-zero-force
            % onset transient whose moment/Fz CoP sits far off the plate and offsets the
            % whole stance.
            contact_threshold_BW = 0.2;
            [cop_anterior_ipsi, cop_lateral_ipsi, cop_vertical_ipsi] = ...
                zero_cop_by_contact(r_cop_anterior, r_cop_lateral, r_cop_vertical, ...
                grf_vertical_ipsi, contact_threshold_BW, false);
            [cop_anterior_contra, cop_lateral_contra, cop_vertical_contra] = ...
                zero_cop_by_contact(l_cop_anterior, l_cop_lateral, l_cop_vertical, ...
                grf_vertical_contra, contact_threshold_BW, false);

            % Physical-bound safety mask: contact-onset / off-plate transients can still
            % leave a stance-relative CoP well beyond foot scale. Anything > 0.5 m from the
            % contact origin is non-physical for an ankle-frame CoP -> mask to NaN
            % (mirrors GTech 2023 convert_gtech_2023_time_to_parquet.m).
            cop_phys_max = 0.5;
            bad_ipsi = abs(cop_anterior_ipsi) > cop_phys_max | abs(cop_lateral_ipsi) > cop_phys_max;
            cop_anterior_ipsi(bad_ipsi) = NaN;
            cop_lateral_ipsi(bad_ipsi)  = NaN;
            cop_vertical_ipsi(bad_ipsi) = NaN;
            bad_contra = abs(cop_anterior_contra) > cop_phys_max | abs(cop_lateral_contra) > cop_phys_max;
            cop_anterior_contra(bad_contra) = NaN;
            cop_lateral_contra(bad_contra)  = NaN;
            cop_vertical_contra(bad_contra) = NaN;
        end
    else
        grf_vertical_ipsi = nan_signal;
        grf_vertical_contra = nan_signal;
        grf_anterior_ipsi = nan_signal;
        grf_anterior_contra = nan_signal;
        grf_lateral_ipsi = nan_signal;
        grf_lateral_contra = nan_signal;
        cop_vertical_ipsi = nan_signal;
        cop_vertical_contra = nan_signal;
        cop_lateral_ipsi = nan_signal;
        cop_lateral_contra = nan_signal;
        cop_anterior_ipsi = nan_signal;
        cop_anterior_contra = nan_signal;
    end

    trial_table = table;
    trial_table.subject = repmat({subject_str}, n_samples, 1);
    trial_table.subject_metadata = repmat({subject_metadata}, n_samples, 1);
    trial_table.task = repmat({task}, n_samples, 1);
    trial_table.task_id = repmat({task_id}, n_samples, 1);
    trial_table.task_info = repmat({task_info}, n_samples, 1);
    trial_table.collection_id = repmat({collection_id}, n_samples, 1);
    trial_table.time_scope = repmat({'continuous_trial'}, n_samples, 1);
    trial_table.time_reset_per = repmat({time_reset_per_label}, n_samples, 1);
    trial_table.reference_leg = repmat({'right'}, n_samples, 1);
    trial_table.sampling_rate_hz = repmat(sampling_rate_hz, n_samples, 1);
    trial_table.step = repmat(step_id, n_samples, 1);
    trial_table.time_s = time_s;
    trial_table.assistance_active = false(n_samples, 1);
    trial_table = locohub_add_provenance(trial_table, trial_struct.source_recording_id, ...
        sprintf('frames:%d:%d', segment_start, segment_end), 'right', ...
        'continuous_recording', (segment_start - 1) / input_sampling_rate_hz, ...
        (segment_end - 1) / input_sampling_rate_hz);
    trial_table.step = trial_table.observation_id;


    trial_table.hip_flexion_angle_ipsi_rad = right_hip_flex;
    trial_table.hip_flexion_angle_contra_rad = left_hip_flex;
    trial_table.hip_adduction_angle_ipsi_rad = right_hip_add;
    trial_table.hip_adduction_angle_contra_rad = left_hip_add;
    trial_table.hip_rotation_angle_ipsi_rad = right_hip_rot;
    trial_table.hip_rotation_angle_contra_rad = left_hip_rot;

    trial_table.knee_flexion_angle_ipsi_rad = right_knee_flex;
    trial_table.knee_flexion_angle_contra_rad = left_knee_flex;
    trial_table.knee_adduction_angle_ipsi_rad = right_knee_add;
    trial_table.knee_adduction_angle_contra_rad = left_knee_add;
    trial_table.knee_rotation_angle_ipsi_rad = right_knee_rot;
    trial_table.knee_rotation_angle_contra_rad = left_knee_rot;

    trial_table.ankle_dorsiflexion_angle_ipsi_rad = right_ankle_flex;
    trial_table.ankle_dorsiflexion_angle_contra_rad = left_ankle_flex;
    trial_table.ankle_adduction_angle_ipsi_rad = right_ankle_add;
    trial_table.ankle_adduction_angle_contra_rad = left_ankle_add;
    trial_table.ankle_rotation_angle_ipsi_rad = right_ankle_rot;
    trial_table.ankle_rotation_angle_contra_rad = left_ankle_rot;

    trial_table.hip_flexion_velocity_ipsi_rad_s = right_hip_flex_vel;
    trial_table.hip_flexion_velocity_contra_rad_s = left_hip_flex_vel;
    trial_table.hip_adduction_velocity_ipsi_rad_s = right_hip_add_vel;
    trial_table.hip_adduction_velocity_contra_rad_s = left_hip_add_vel;
    trial_table.hip_rotation_velocity_ipsi_rad_s = right_hip_rot_vel;
    trial_table.hip_rotation_velocity_contra_rad_s = left_hip_rot_vel;

    trial_table.knee_flexion_velocity_ipsi_rad_s = right_knee_flex_vel;
    trial_table.knee_flexion_velocity_contra_rad_s = left_knee_flex_vel;
    trial_table.knee_adduction_velocity_ipsi_rad_s = right_knee_add_vel;
    trial_table.knee_adduction_velocity_contra_rad_s = left_knee_add_vel;
    trial_table.knee_rotation_velocity_ipsi_rad_s = right_knee_rot_vel;
    trial_table.knee_rotation_velocity_contra_rad_s = left_knee_rot_vel;

    trial_table.ankle_dorsiflexion_velocity_ipsi_rad_s = right_ankle_flex_vel;
    trial_table.ankle_dorsiflexion_velocity_contra_rad_s = left_ankle_flex_vel;
    trial_table.ankle_adduction_velocity_ipsi_rad_s = right_ankle_add_vel;
    trial_table.ankle_adduction_velocity_contra_rad_s = left_ankle_add_vel;
    trial_table.ankle_rotation_velocity_ipsi_rad_s = right_ankle_rot_vel;
    trial_table.ankle_rotation_velocity_contra_rad_s = left_ankle_rot_vel;

    trial_table.hip_flexion_acceleration_ipsi_rad_s2 = right_hip_flex_acc;
    trial_table.hip_flexion_acceleration_contra_rad_s2 = left_hip_flex_acc;
    trial_table.knee_flexion_acceleration_ipsi_rad_s2 = right_knee_flex_acc;
    trial_table.knee_flexion_acceleration_contra_rad_s2 = left_knee_flex_acc;
    trial_table.ankle_dorsiflexion_acceleration_ipsi_rad_s2 = right_ankle_flex_acc;
    trial_table.ankle_dorsiflexion_acceleration_contra_rad_s2 = left_ankle_flex_acc;

    trial_table.hip_flexion_moment_ipsi_Nm_kg = right_hip_flex_mom;
    trial_table.hip_flexion_moment_contra_Nm_kg = left_hip_flex_mom;
    trial_table.hip_adduction_moment_ipsi_Nm_kg = right_hip_add_mom;
    trial_table.hip_adduction_moment_contra_Nm_kg = left_hip_add_mom;
    trial_table.hip_rotation_moment_ipsi_Nm_kg = right_hip_rot_mom;
    trial_table.hip_rotation_moment_contra_Nm_kg = left_hip_rot_mom;

    trial_table.knee_flexion_moment_ipsi_Nm_kg = right_knee_flex_mom;
    trial_table.knee_flexion_moment_contra_Nm_kg = left_knee_flex_mom;
    trial_table.knee_adduction_moment_ipsi_Nm_kg = right_knee_add_mom;
    trial_table.knee_adduction_moment_contra_Nm_kg = left_knee_add_mom;
    trial_table.knee_rotation_moment_ipsi_Nm_kg = right_knee_rot_mom;
    trial_table.knee_rotation_moment_contra_Nm_kg = left_knee_rot_mom;

    trial_table.ankle_dorsiflexion_moment_ipsi_Nm_kg = right_ankle_flex_mom;
    trial_table.ankle_dorsiflexion_moment_contra_Nm_kg = left_ankle_flex_mom;
    trial_table.ankle_adduction_moment_ipsi_Nm_kg = right_ankle_add_mom;
    trial_table.ankle_adduction_moment_contra_Nm_kg = left_ankle_add_mom;
    trial_table.ankle_rotation_moment_ipsi_Nm_kg = right_ankle_rot_mom;
    trial_table.ankle_rotation_moment_contra_Nm_kg = left_ankle_rot_mom;

    trial_table.grf_vertical_ipsi_BW = grf_vertical_ipsi;
    trial_table.grf_vertical_contra_BW = grf_vertical_contra;
    trial_table.grf_anterior_ipsi_BW = grf_anterior_ipsi;
    trial_table.grf_anterior_contra_BW = grf_anterior_contra;
    trial_table.grf_lateral_ipsi_BW = grf_lateral_ipsi;
    trial_table.grf_lateral_contra_BW = grf_lateral_contra;

    trial_table.cop_anterior_ipsi_m = cop_anterior_ipsi;
    trial_table.cop_anterior_contra_m = cop_anterior_contra;
    trial_table.cop_lateral_ipsi_m = cop_lateral_ipsi;
    trial_table.cop_lateral_contra_m = cop_lateral_contra;
    trial_table.cop_vertical_ipsi_m = cop_vertical_ipsi;
    trial_table.cop_vertical_contra_m = cop_vertical_contra;

    trial_table.pelvis_sagittal_angle_rad = pelvis_sag;
    trial_table.pelvis_frontal_angle_rad = pelvis_front;
    trial_table.pelvis_transverse_angle_rad = pelvis_trans;
    trial_table.thigh_sagittal_angle_ipsi_rad = right_thigh_sag;
    trial_table.thigh_sagittal_angle_contra_rad = left_thigh_sag;
    trial_table.shank_sagittal_angle_ipsi_rad = right_shank_sag;
    trial_table.shank_sagittal_angle_contra_rad = left_shank_sag;
    trial_table.foot_sagittal_angle_ipsi_rad = right_foot_sag;
    trial_table.foot_sagittal_angle_contra_rad = left_foot_sag;
    trial_table.thigh_sagittal_velocity_ipsi_rad_s = right_thigh_sag_vel;
    trial_table.thigh_sagittal_velocity_contra_rad_s = left_thigh_sag_vel;
    trial_table.shank_sagittal_velocity_ipsi_rad_s = right_shank_sag_vel;
    trial_table.shank_sagittal_velocity_contra_rad_s = left_shank_sag_vel;
    trial_table.foot_sagittal_velocity_ipsi_rad_s = right_foot_sag_vel;
    trial_table.foot_sagittal_velocity_contra_rad_s = left_foot_sag_vel;
    trial_table = mask_structural_outliers(trial_table);
end


function data = mask_structural_outliers(data)
    % Acquisition glitches beyond the standard's absolute physical guards
    % are unavailable measurements, not valid extreme biomechanics.
    names = data.Properties.VariableNames;
    for name_idx = 1:length(names)
        name = names{name_idx};
        limit = [];
        if startsWith(name, 'cop_') && endsWith(name, '_m')
            limit = 5;
        elseif contains(name, '_acceleration_') && endsWith(name, '_rad_s2')
            limit = 10000;
        elseif contains(name, '_velocity_') && endsWith(name, '_rad_s')
            limit = 100;
        end
        if ~isempty(limit) && isnumeric(data.(name))
            invalid = ~isfinite(data.(name)) | abs(data.(name)) > limit;
            data.(name)(invalid) = NaN;
        end
    end
end


function signal = get_optional_angle(angles, field_name, idx, plane_idx, source_time_s, target_time_s, deg2rad_factor, default_signal)
    signal = default_signal;
    if isfield(angles, field_name) && size(angles.(field_name), 2) >= plane_idx
        signal = resample_signal(angles.(field_name)(idx, plane_idx) * deg2rad_factor, source_time_s, target_time_s);
    end
end


function [segment_end, is_valid, reason] = sanitize_angle_segment(angles, segment_start, segment_end)
    % Remove only unambiguous acquisition padding, then reject gross corruption.
    % A valid pose can contain an individual zero-valued joint, so padding is
    % recognized only when all six sagittal channels are exactly zero for at
    % least 10 consecutive frames at the end of the requested segment.
    fields = {'RHipAngles', 'LHipAngles', 'RKneeAngles', 'LKneeAngles', ...
        'RAnkleAngles', 'LAnkleAngles'};
    sagittal = zeros(segment_end - segment_start + 1, length(fields));
    all_angles = [];
    for field_idx = 1:length(fields)
        values = angles.(fields{field_idx})(segment_start:segment_end, :);
        sagittal(:, field_idx) = values(:, 1);
        all_angles = [all_angles, values]; %#ok<AGROW>
    end

    trailing_padding = all(sagittal == 0, 2);
    last_nonpadding = find(~trailing_padding, 1, 'last');
    if isempty(last_nonpadding)
        is_valid = false;
        reason = 'all requested joint-angle frames are zero';
        return;
    end
    padding_length = size(sagittal, 1) - last_nonpadding;
    if padding_length >= 10
        segment_end = segment_start + last_nonpadding - 1;
        all_angles = all_angles(1:last_nonpadding, :);
    end

    % Pelvis and foot-progress channels also feed the reconstructed segment
    % angles and their gradients, so subject them to the same corruption guard.
    optional_fields = {'RPelvisAngles', 'LPelvisAngles', ...
        'RFootProgressAngles', 'LFootProgressAngles'};
    retained_rows = size(all_angles, 1);
    for field_idx = 1:length(optional_fields)
        field_name = optional_fields{field_idx};
        if isfield(angles, field_name)
            values = angles.(field_name)(segment_start:segment_end, :);
            if size(values, 1) ~= retained_rows
                is_valid = false;
                reason = sprintf('%s does not cover the retained segment', field_name);
                return;
            end
            all_angles = [all_angles, values]; %#ok<AGROW>
        end
    end

    if any(~isfinite(all_angles), 'all')
        is_valid = false;
        reason = 'joint angles contain NaN or Inf';
        return;
    end
    if any(abs(all_angles) > 180, 'all')
        is_valid = false;
        reason = 'joint angle exceeds +/-180 degrees';
        return;
    end
    if size(all_angles, 1) > 1 && any(abs(diff(all_angles, 1, 1)) > 120, 'all')
        is_valid = false;
        reason = 'joint angle jumps more than 120 degrees in one frame';
        return;
    end

    is_valid = true;
    reason = '';
end


function signal = get_optional_foot_angle(angles, field_name, idx, source_time_s, target_time_s, deg2rad_factor, default_signal)
    signal = default_signal;
    if isfield(angles, field_name) && size(angles.(field_name), 2) >= 1
        signal = resample_signal(-angles.(field_name)(idx, 1) * deg2rad_factor, source_time_s, target_time_s);
        signal = apply_90_degree_correction(signal);
    end
end


function pelvis_signal = choose_pelvis_signal(primary_signal, secondary_signal, default_signal)
    if ~all(isnan(primary_signal))
        pelvis_signal = primary_signal;
    elseif ~all(isnan(secondary_signal))
        pelvis_signal = secondary_signal;
    else
        pelvis_signal = default_signal;
    end
end


function signal_out = resample_signal(signal_in, source_time_s, target_time_s)
    signal_in = signal_in(:);
    source_time_s = source_time_s(:);
    target_time_s = target_time_s(:);

    if isempty(signal_in) || isempty(source_time_s)
        signal_out = NaN(length(target_time_s), 1);
        return;
    end

    if length(signal_in) == 1 || length(unique(source_time_s)) < 2
        signal_out = repmat(signal_in(1), length(target_time_s), 1);
        return;
    end

    signal_out = interp1(source_time_s, signal_in, target_time_s, 'linear', 'extrap');
    signal_out = signal_out(:);
end


function corrected = apply_90_degree_correction(angle_rad)
    deg2rad_factor = pi / 180;
    first_point = angle_rad(1);

    while first_point > deg2rad_factor * 50
        angle_rad = angle_rad - pi / 2;
        first_point = first_point - pi / 2;
    end

    while first_point < -deg2rad_factor * 50
        angle_rad = angle_rad + pi / 2;
        first_point = first_point + pi / 2;
    end

    corrected = angle_rad;
end


function [anterior, lateral, vertical] = zero_cop_by_contact( ...
        anterior, lateral, vertical, vertical_force_BW, contact_threshold_BW, allow_initial_contact)
    % Express each contiguous stance episode relative to its initial CoP.
    anterior = anterior(:);
    lateral = lateral(:);
    vertical = vertical(:);
    vertical_force_BW = vertical_force_BW(:);

    contact = isfinite(vertical_force_BW) & ...
        vertical_force_BW > contact_threshold_BW & ...
        isfinite(anterior) & isfinite(lateral) & isfinite(vertical);
    % A segment may start in mid-stance. Without the preceding heel strike,
    % that partial episode has no valid stride-relative origin.
    if ~allow_initial_contact && ~isempty(contact) && contact(1)
        first_end = find(~contact, 1, 'first');
        if isempty(first_end)
            contact(:) = false;
        else
            contact(1:first_end - 1) = false;
        end
    end
    contact_starts = find(contact & [true; ~contact(1:end-1)]);
    contact_ends = find(contact & [~contact(2:end); true]);

    for episode_idx = 1:min(numel(contact_starts), numel(contact_ends))
        episode = contact_starts(episode_idx):contact_ends(episode_idx);
        anterior(episode) = anterior(episode) - anterior(episode(1));
        lateral(episode) = lateral(episode) - lateral(episode(1));
        vertical(episode) = vertical(episode) - vertical(episode(1));
        edge_count = max(1, floor(numel(episode) * 0.2));
        early_progression = median(anterior(episode(1:edge_count)), 'omitnan');
        late_progression = median(anterior(episode(end-edge_count+1:end)), 'omitnan');
        if late_progression < early_progression
            anterior(episode) = -anterior(episode);
        end
    end

    anterior(~contact) = NaN;
    lateral(~contact) = NaN;
    vertical(~contact) = NaN;
end
