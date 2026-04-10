% Convert Gtech 2021 dataset to standardized time-indexed parquet format.
%
% Pragmatic export policy:
% - Preserve native trial timing (`time_s`)
% - Reuse phase-script task mappings and sign conventions
% - Use coarse trial/segment windows instead of exact stride filtering
% - Keep treadmill/levelground GRF/CoP where left/right channels are available
% - Use force-plate assignment for stair/ramp windows

clear all;
close all;

addpath('utilities');

DATA_ROOT = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
OUTPUT_DIR = fullfile('..', '..', '..', 'converted_datasets');
OUTPUT_FILE = 'gtech_2021_time.parquet';
TARGET_SAMPLING_RATE_HZ = 200;

if ~exist(OUTPUT_DIR, 'dir')
    mkdir(OUTPUT_DIR);
end

fprintf('Loading subject information...\n');
subjectInfo = load(fullfile(DATA_ROOT, 'SubjectInfo.mat'));
subjectInfo = subjectInfo.data;

subjects_to_process = {};
for i = 6:30
    if i == 22 || i == 26 || i == 27 || i == 29 || i == 100
        continue;
    end
    subjects_to_process{end+1} = sprintf('AB%02d', i);
end

output_table = table();
step_counter = 1;

for subj_idx = 1:length(subjects_to_process)
    subject_code = subjects_to_process{subj_idx};
    subject_str = sprintf('GT21_%s', subject_code);

    fprintf('\n========================================\n');
    fprintf('Processing %s (%d/%d)\n', subject_code, subj_idx, length(subjects_to_process));
    fprintf('========================================\n');

    subject_mass = subjectInfo.Weight(strcmp(subjectInfo.Subject, subject_code));
    if isempty(subject_mass)
        fprintf('  WARNING: No mass data for %s, skipping\n', subject_code);
        continue;
    end

    seg_lengths = gtech_estimate_segment_lengths(DATA_ROOT, subject_code);
    subject_metadata = sprintf( ...
        'weight_kg:%.1f,thigh_length_m:%.3f,shank_length_m:%.3f,foot_length_m:%.3f', ...
        subject_mass, seg_lengths.thigh_length_m, seg_lengths.shank_length_m, seg_lengths.foot_length_m);

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

    date_path = fullfile(subject_dir, date_folders(1).name);
    fprintf('  Processing folder: %s\n', date_folders(1).name);

    [rows, step_counter] = process_treadmill_time(date_path, subject_str, subject_mass, subject_metadata, step_counter);
    output_table = [output_table; rows];
    [rows, step_counter] = process_levelground_time(date_path, subject_str, subject_mass, subject_metadata, step_counter);
    output_table = [output_table; rows];
    [rows, step_counter] = process_ramp_time(date_path, subject_str, subject_mass, subject_metadata, step_counter);
    output_table = [output_table; rows];
    [rows, step_counter] = process_stair_time(date_path, subject_str, subject_mass, subject_metadata, step_counter);
    output_table = [output_table; rows];
end

output_path = fullfile(OUTPUT_DIR, OUTPUT_FILE);
parquetwrite(output_path, output_table);
fprintf('\nSaved time-indexed data to: %s\n', output_path);
fprintf('Subjects: %d\n', length(unique(output_table.subject)));
fprintf('Rows: %d\n', height(output_table));


function [rows, step_counter] = process_treadmill_time(date_path, subject_str, subject_mass, subject_metadata, step_counter)
    rows = table();
    mode_path = fullfile(date_path, 'treadmill');
    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    target_speeds = 0.50:0.05:2.00;
    tolerance = 0.025;

    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data) || ~isfield(trial_data, 'conditions') || ~istable(trial_data.conditions)
            continue;
        end

        speed_vec = trial_data.conditions.Speed;
        time_vec = trial_data.conditions.Header;

        for speed_val = target_speeds
            speed_mask = abs(speed_vec - speed_val) <= tolerance;
            transitions = diff([false; speed_mask; false]);
            region_starts = find(transitions == 1);
            region_ends = find(transitions == -1) - 1;

            for r = 1:length(region_starts)
                region_length = region_ends(r) - region_starts(r) + 1;
                if region_length < 5000
                    continue;
                end

                time_start = time_vec(region_starts(r));
                time_end = time_vec(region_ends(r));
                actual_speed = mean(speed_vec(region_starts(r):region_ends(r)));
                collection_id = sprintf('treadmill_%s_speed_%0.2f_seg%02d', erase(trial_name, '.mat'), actual_speed, r);
                task_info = sprintf('speed_m_s:%.2f,treadmill:true,surface:treadmill', actual_speed);

                segment_rows = extract_and_process_time_window( ...
                    trial_data, time_start, time_end, subject_str, subject_metadata, ...
                    'level_walking', 'level', task_info, subject_mass, 'treadmill', ...
                    'segment', collection_id, step_counter);

                if ~isempty(segment_rows)
                    rows = [rows; segment_rows];
                    step_counter = step_counter + 1;
                end
            end
        end
    end
end


function [rows, step_counter] = process_levelground_time(date_path, subject_str, subject_mass, subject_metadata, step_counter)
    rows = table();
    mode_path = fullfile(date_path, 'levelground');
    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        if contains(trial_name, 'slow')
            speed_val = 0.88;
        elseif contains(trial_name, 'fast')
            speed_val = 1.45;
        else
            speed_val = 1.17;
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
                for seg_idx = 1:size(segments, 1)
                    [task, task_id, task_info] = map_levelground_label(label_name, speed_val);
                    if isempty(task)
                        continue;
                    end
                    collection_id = sprintf('levelground_%s_%s_seg%02d', erase(trial_name, '.mat'), label_name, seg_idx);
                    segment_rows = extract_and_process_time_window( ...
                        trial_data, segments(seg_idx, 1), segments(seg_idx, 2), subject_str, subject_metadata, ...
                        task, task_id, task_info, subject_mass, 'levelground', 'segment', collection_id, step_counter);
                    if ~isempty(segment_rows)
                        rows = [rows; segment_rows];
                        step_counter = step_counter + 1;
                        processed = true;
                    end
                end
            end
        end

        if ~processed && isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
            collection_id = sprintf('levelground_%s_full', erase(trial_name, '.mat'));
            task_info = sprintf('speed_m_s:%.2f,surface:overground,labels_missing:true', speed_val);
            segment_rows = extract_and_process_time_window( ...
                trial_data, trial_data.ik_offset.Header(1), trial_data.ik_offset.Header(end), ...
                subject_str, subject_metadata, 'level_walking', 'level', task_info, ...
                subject_mass, 'levelground', 'trial', collection_id, step_counter);
            if ~isempty(segment_rows)
                rows = [rows; segment_rows];
                step_counter = step_counter + 1;
            end
        end
    end
end


function [rows, step_counter] = process_ramp_time(date_path, subject_str, subject_mass, subject_metadata, step_counter)
    rows = table();
    mode_path = fullfile(date_path, 'ramp');
    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        ramp_angle = NaN;
        if isfield(trial_data, 'conditions') && istable(trial_data.conditions) && ...
                any(strcmp(trial_data.conditions.Properties.VariableNames, 'rampIncline'))
            ramp_angle = trial_data.conditions.rampIncline(1);
        end
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
                for seg_idx = 1:size(segments, 1)
                    [task, task_id, task_info] = map_ramp_label(label_name, ramp_angle);
                    if isempty(task)
                        continue;
                    end
                    collection_id = sprintf('ramp_%s_%s_seg%02d', erase(trial_name, '.mat'), label_name, seg_idx);
                    segment_rows = extract_and_process_time_window( ...
                        trial_data, segments(seg_idx, 1), segments(seg_idx, 2), subject_str, subject_metadata, ...
                        task, task_id, task_info, subject_mass, 'ramp', 'segment', collection_id, step_counter);
                    if ~isempty(segment_rows)
                        rows = [rows; segment_rows];
                        step_counter = step_counter + 1;
                        processed = true;
                    end
                end
            end
        end

        if ~processed && isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset) && ~isnan(ramp_angle)
            angle_label = round(ramp_angle, 1);
            if contains(lower(trial_name), 'descent') || contains(lower(trial_name), 'walk-rampdescent')
                task = 'decline_walking';
                task_id = sprintf('decline_%.1fdeg', -angle_label);
                task_info = sprintf('incline_deg:%.1f,surface:overground,fallback:true', -angle_label);
            else
                task = 'incline_walking';
                task_id = sprintf('incline_%.1fdeg', angle_label);
                task_info = sprintf('incline_deg:%.1f,surface:overground,fallback:true', angle_label);
            end
            collection_id = sprintf('ramp_%s_full', erase(trial_name, '.mat'));
            segment_rows = extract_and_process_time_window( ...
                trial_data, trial_data.ik_offset.Header(1), trial_data.ik_offset.Header(end), ...
                subject_str, subject_metadata, task, task_id, task_info, ...
                subject_mass, 'ramp', 'trial', collection_id, step_counter);
            if ~isempty(segment_rows)
                rows = [rows; segment_rows];
                step_counter = step_counter + 1;
            end
        end
    end
end


function [rows, step_counter] = process_stair_time(date_path, subject_str, subject_mass, subject_metadata, step_counter)
    rows = table();
    mode_path = fullfile(date_path, 'stair');
    if ~exist(mode_path, 'dir')
        return;
    end

    trial_files = dir(fullfile(mode_path, 'conditions', '*.mat'));
    for t = 1:length(trial_files)
        trial_name = trial_files(t).name;
        trial_data = load_trial_data(mode_path, trial_name);
        if isempty(trial_data)
            continue;
        end

        if isfield(trial_data, 'stairHeight')
            stair_height_m = round(trial_data.stairHeight * 0.0254, 3);
        else
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
                for seg_idx = 1:size(segments, 1)
                    [task, task_id, task_info] = map_stair_label(label_name, stair_height_m);
                    if isempty(task)
                        continue;
                    end
                    collection_id = sprintf('stair_%s_%s_seg%02d', erase(trial_name, '.mat'), label_name, seg_idx);
                    segment_rows = extract_and_process_time_window( ...
                        trial_data, segments(seg_idx, 1), segments(seg_idx, 2), subject_str, subject_metadata, ...
                        task, task_id, task_info, subject_mass, 'stair', 'segment', collection_id, step_counter);
                    if ~isempty(segment_rows)
                        rows = [rows; segment_rows];
                        step_counter = step_counter + 1;
                        processed = true;
                    end
                end
            end
        end

        if ~processed && isfield(trial_data, 'ik_offset') && istable(trial_data.ik_offset)
            if contains(lower(trial_name), 'descent')
                task = 'stair_descent';
                task_id = 'stair_descent';
            else
                task = 'stair_ascent';
                task_id = 'stair_ascent';
            end
            task_info = sprintf('step_height_m:%.3f,surface:stairs,fallback:true', stair_height_m);
            collection_id = sprintf('stair_%s_full', erase(trial_name, '.mat'));
            segment_rows = extract_and_process_time_window( ...
                trial_data, trial_data.ik_offset.Header(1), trial_data.ik_offset.Header(end), ...
                subject_str, subject_metadata, task, task_id, task_info, ...
                subject_mass, 'stair', 'trial', collection_id, step_counter);
            if ~isempty(segment_rows)
                rows = [rows; segment_rows];
                step_counter = step_counter + 1;
            end
        end
    end
end


function rows = extract_and_process_time_window(trial_data, time_start, time_end, ...
    subject_str, subject_metadata, task, task_id, task_info, subject_mass, mode, time_reset_per_label, collection_id, step_id)

    rows = table();
    if ~isfield(trial_data, 'ik_offset') || ~istable(trial_data.ik_offset)
        return;
    end

    ik_mask = (trial_data.ik_offset.Header >= time_start) & (trial_data.ik_offset.Header <= time_end);
    if sum(ik_mask) < 10
        return;
    end

    ik_time = trial_data.ik_offset.Header(ik_mask);
    ik_time = ik_time(:);
    if numel(ik_time) < 2
        return;
    end

    sampling_rate_hz = 200;
    duration_s = ik_time(end) - ik_time(1);
    n_samples = max(2, floor(duration_s * sampling_rate_hz) + 1);
    time_s = ((0:n_samples-1)' ./ sampling_rate_hz);
    target_time = ik_time(1) + time_s;
    dt = 1 / sampling_rate_hz;
    nan_signal = NaN(n_samples, 1);

    [first_leg, first_hs_time] = gtech_determine_first_heel_strike(trial_data, time_start, time_end);
    if isempty(first_leg)
        first_leg = 'right';
    end
    if strcmp(first_leg, 'right')
        ipsi_suffix = 'r';
        contra_suffix = 'l';
        ipsi_tread = 'R';
        contra_tread = 'L';
    else
        ipsi_suffix = 'l';
        contra_suffix = 'r';
        ipsi_tread = 'L';
        contra_tread = 'R';
    end

    deg2rad = pi / 180;

    full_ik_time = trial_data.ik_offset.Header(:);
    ankle_ipsi = interp_optional(trial_data.ik_offset, sprintf('ankle_angle_%s', ipsi_suffix), full_ik_time, target_time) * deg2rad;
    ankle_contra = interp_optional(trial_data.ik_offset, sprintf('ankle_angle_%s', contra_suffix), full_ik_time, target_time) * deg2rad;
    knee_ipsi = -interp_optional(trial_data.ik_offset, sprintf('knee_angle_%s', ipsi_suffix), full_ik_time, target_time) * deg2rad;
    knee_contra = -interp_optional(trial_data.ik_offset, sprintf('knee_angle_%s', contra_suffix), full_ik_time, target_time) * deg2rad;
    hip_ipsi = interp_optional(trial_data.ik_offset, sprintf('hip_flexion_%s', ipsi_suffix), full_ik_time, target_time) * deg2rad;
    hip_contra = interp_optional(trial_data.ik_offset, sprintf('hip_flexion_%s', contra_suffix), full_ik_time, target_time) * deg2rad;

    ankle_vel_ipsi = gradient(ankle_ipsi, dt);
    ankle_vel_contra = gradient(ankle_contra, dt);
    knee_vel_ipsi = gradient(knee_ipsi, dt);
    knee_vel_contra = gradient(knee_contra, dt);
    hip_vel_ipsi = gradient(hip_ipsi, dt);
    hip_vel_contra = gradient(hip_contra, dt);

    ankle_acc_ipsi = gradient(ankle_vel_ipsi, dt);
    ankle_acc_contra = gradient(ankle_vel_contra, dt);
    knee_acc_ipsi = gradient(knee_vel_ipsi, dt);
    knee_acc_contra = gradient(knee_vel_contra, dt);
    hip_acc_ipsi = gradient(hip_vel_ipsi, dt);
    hip_acc_contra = gradient(hip_vel_contra, dt);

    pelvis_sag = interp_optional(trial_data.ik_offset, 'pelvis_tilt', full_ik_time, target_time) * deg2rad;
    lumbar_ext = interp_optional(trial_data.ik_offset, 'lumbar_extension', full_ik_time, target_time) * deg2rad;
    trunk_sag = pelvis_sag + lumbar_ext;
    pelvis_vel = gradient(pelvis_sag, dt);
    trunk_vel = gradient(trunk_sag, dt);

    thigh_ipsi = pelvis_sag + hip_ipsi;
    thigh_contra = pelvis_sag + hip_contra;
    shank_ipsi = thigh_ipsi - knee_ipsi;
    shank_contra = thigh_contra - knee_contra;
    foot_ipsi = shank_ipsi + ankle_ipsi;
    foot_contra = shank_contra + ankle_contra;

    thigh_vel_ipsi = pelvis_vel + hip_vel_ipsi;
    thigh_vel_contra = pelvis_vel + hip_vel_contra;
    shank_vel_ipsi = thigh_vel_ipsi - knee_vel_ipsi;
    shank_vel_contra = thigh_vel_contra - knee_vel_contra;
    foot_vel_ipsi = shank_vel_ipsi + ankle_vel_ipsi;
    foot_vel_contra = shank_vel_contra + ankle_vel_contra;

    if isfield(trial_data, 'id') && istable(trial_data.id)
        id_time = trial_data.id.Header(:);
        ankle_mom_ipsi = interp_optional(trial_data.id, sprintf('ankle_angle_%s_moment', ipsi_suffix), id_time, target_time) / subject_mass;
        ankle_mom_contra = interp_optional(trial_data.id, sprintf('ankle_angle_%s_moment', contra_suffix), id_time, target_time) / subject_mass;
        knee_mom_ipsi = -interp_optional(trial_data.id, sprintf('knee_angle_%s_moment', ipsi_suffix), id_time, target_time) / subject_mass;
        knee_mom_contra = -interp_optional(trial_data.id, sprintf('knee_angle_%s_moment', contra_suffix), id_time, target_time) / subject_mass;
        hip_mom_ipsi = interp_optional(trial_data.id, sprintf('hip_flexion_%s_moment', ipsi_suffix), id_time, target_time) / subject_mass;
        hip_mom_contra = interp_optional(trial_data.id, sprintf('hip_flexion_%s_moment', contra_suffix), id_time, target_time) / subject_mass;
    else
        ankle_mom_ipsi = nan_signal;
        ankle_mom_contra = nan_signal;
        knee_mom_ipsi = nan_signal;
        knee_mom_contra = nan_signal;
        hip_mom_ipsi = nan_signal;
        hip_mom_contra = nan_signal;
    end

    grf_vertical_ipsi = nan_signal;
    grf_vertical_contra = nan_signal;
    grf_anterior_ipsi = nan_signal;
    grf_anterior_contra = nan_signal;
    grf_lateral_ipsi = nan_signal;
    grf_lateral_contra = nan_signal;
    cop_anterior_ipsi = nan_signal;
    cop_anterior_contra = nan_signal;
    cop_lateral_ipsi = nan_signal;
    cop_lateral_contra = nan_signal;
    cop_vertical_ipsi = nan_signal;
    cop_vertical_contra = nan_signal;

    if ismember(lower(mode), {'treadmill', 'levelground'}) && isfield(trial_data, 'fp') && istable(trial_data.fp)
        fp_time = trial_data.fp.Header(:);
        grf_vertical_ipsi = interp_optional(trial_data.fp, sprintf('Treadmill_%s_vy', ipsi_tread), fp_time, target_time) / (subject_mass * 9.81);
        grf_vertical_contra = interp_optional(trial_data.fp, sprintf('Treadmill_%s_vy', contra_tread), fp_time, target_time) / (subject_mass * 9.81);
        grf_anterior_ipsi = -interp_optional(trial_data.fp, sprintf('Treadmill_%s_vz', ipsi_tread), fp_time, target_time) / (subject_mass * 9.81);
        grf_anterior_contra = -interp_optional(trial_data.fp, sprintf('Treadmill_%s_vz', contra_tread), fp_time, target_time) / (subject_mass * 9.81);
        grf_lateral_ipsi = interp_optional(trial_data.fp, sprintf('Treadmill_%s_vx', ipsi_tread), fp_time, target_time) / (subject_mass * 9.81);
        grf_lateral_contra = interp_optional(trial_data.fp, sprintf('Treadmill_%s_vx', contra_tread), fp_time, target_time) / (subject_mass * 9.81);

        if isfield(trial_data, 'markers') && istable(trial_data.markers)
            marker_time = trial_data.markers.Header(:);
            ankle_lat_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_x', upper(ipsi_suffix)), marker_time, target_time) / 1000;
            ankle_vert_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_y', upper(ipsi_suffix)), marker_time, target_time) / 1000;
            ankle_ant_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_z', upper(ipsi_suffix)), marker_time, target_time) / 1000;
            ankle_lat_contra = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_x', upper(contra_suffix)), marker_time, target_time) / 1000;
            ankle_vert_contra = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_y', upper(contra_suffix)), marker_time, target_time) / 1000;
            ankle_ant_contra = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_z', upper(contra_suffix)), marker_time, target_time) / 1000;

            cop_lateral_ipsi = interp_optional(trial_data.fp, sprintf('Treadmill_%s_px', ipsi_tread), fp_time, target_time) - ankle_lat_ipsi;
            cop_vertical_ipsi = interp_optional(trial_data.fp, sprintf('Treadmill_%s_py', ipsi_tread), fp_time, target_time) - ankle_vert_ipsi;
            cop_anterior_ipsi = -(interp_optional(trial_data.fp, sprintf('Treadmill_%s_pz', ipsi_tread), fp_time, target_time) - ankle_ant_ipsi);
            cop_lateral_contra = interp_optional(trial_data.fp, sprintf('Treadmill_%s_px', contra_tread), fp_time, target_time) - ankle_lat_contra;
            cop_vertical_contra = interp_optional(trial_data.fp, sprintf('Treadmill_%s_py', contra_tread), fp_time, target_time) - ankle_vert_contra;
            cop_anterior_contra = interp_optional(trial_data.fp, sprintf('Treadmill_%s_pz', contra_tread), fp_time, target_time) - ankle_ant_contra;
        end
    elseif ismember(lower(mode), {'stair', 'ramp'}) && isfield(trial_data, 'fp') && istable(trial_data.fp)
        fp_time = trial_data.fp.Header(:);
        best_fp_ipsi = select_best_force_plate(trial_data.fp, time_start, time_end, first_hs_time);

        if ~isempty(best_fp_ipsi)
            grf_vertical_ipsi = interp_optional(trial_data.fp, [best_fp_ipsi '_vy'], fp_time, target_time) / (subject_mass * 9.81);
            grf_anterior_ipsi = interp_optional(trial_data.fp, [best_fp_ipsi '_vz'], fp_time, target_time) / (subject_mass * 9.81);
            grf_lateral_ipsi = interp_optional(trial_data.fp, [best_fp_ipsi '_vx'], fp_time, target_time) / (subject_mass * 9.81);

            if isfield(trial_data, 'markers') && istable(trial_data.markers)
                marker_time = trial_data.markers.Header(:);
                ankle_lat_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_x', upper(ipsi_suffix)), marker_time, target_time) / 1000;
                ankle_vert_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_y', upper(ipsi_suffix)), marker_time, target_time) / 1000;
                ankle_ant_ipsi = interp_optional(trial_data.markers, sprintf('%s_Ankle_Lat_z', upper(ipsi_suffix)), marker_time, target_time) / 1000;

                cop_lateral_ipsi = interp_optional(trial_data.fp, [best_fp_ipsi '_px'], fp_time, target_time) - ankle_lat_ipsi;
                cop_vertical_ipsi = interp_optional(trial_data.fp, [best_fp_ipsi '_py'], fp_time, target_time) - ankle_vert_ipsi;
                cop_anterior_ipsi = -(interp_optional(trial_data.fp, [best_fp_ipsi '_pz'], fp_time, target_time) - ankle_ant_ipsi);
            end

            contact_mask = grf_vertical_ipsi < 0.2;
            cop_anterior_ipsi(contact_mask) = 0;
            cop_lateral_ipsi(contact_mask) = 0;
            cop_vertical_ipsi(contact_mask) = 0;
        end
    end

    task_info = append_time_metadata(task_info, collection_id, time_reset_per_label, sampling_rate_hz, first_leg, mode);

    rows = table();
    rows.subject = repmat({subject_str}, n_samples, 1);
    rows.subject_metadata = repmat({subject_metadata}, n_samples, 1);
    rows.task = repmat({task}, n_samples, 1);
    rows.task_id = repmat({task_id}, n_samples, 1);
    rows.task_info = repmat({task_info}, n_samples, 1);
    rows.collection_id = repmat({collection_id}, n_samples, 1);
    rows.time_scope = repmat({'continuous_trial'}, n_samples, 1);
    rows.time_reset_per = repmat({time_reset_per_label}, n_samples, 1);
    rows.reference_leg = repmat({first_leg}, n_samples, 1);
    rows.sampling_rate_hz = repmat(sampling_rate_hz, n_samples, 1);
    rows.step = repmat(step_id, n_samples, 1);
    rows.time_s = time_s;
    rows.assistance_active = false(n_samples, 1);

    rows.hip_flexion_angle_ipsi_rad = hip_ipsi;
    rows.hip_flexion_angle_contra_rad = hip_contra;
    rows.knee_flexion_angle_ipsi_rad = knee_ipsi;
    rows.knee_flexion_angle_contra_rad = knee_contra;
    rows.ankle_dorsiflexion_angle_ipsi_rad = ankle_ipsi;
    rows.ankle_dorsiflexion_angle_contra_rad = ankle_contra;

    rows.hip_flexion_velocity_ipsi_rad_s = hip_vel_ipsi;
    rows.hip_flexion_velocity_contra_rad_s = hip_vel_contra;
    rows.knee_flexion_velocity_ipsi_rad_s = knee_vel_ipsi;
    rows.knee_flexion_velocity_contra_rad_s = knee_vel_contra;
    rows.ankle_dorsiflexion_velocity_ipsi_rad_s = ankle_vel_ipsi;
    rows.ankle_dorsiflexion_velocity_contra_rad_s = ankle_vel_contra;

    rows.hip_flexion_acceleration_ipsi_rad_s2 = hip_acc_ipsi;
    rows.hip_flexion_acceleration_contra_rad_s2 = hip_acc_contra;
    rows.knee_flexion_acceleration_ipsi_rad_s2 = knee_acc_ipsi;
    rows.knee_flexion_acceleration_contra_rad_s2 = knee_acc_contra;
    rows.ankle_dorsiflexion_acceleration_ipsi_rad_s2 = ankle_acc_ipsi;
    rows.ankle_dorsiflexion_acceleration_contra_rad_s2 = ankle_acc_contra;

    rows.hip_flexion_moment_ipsi_Nm_kg = hip_mom_ipsi;
    rows.hip_flexion_moment_contra_Nm_kg = hip_mom_contra;
    rows.knee_flexion_moment_ipsi_Nm_kg = knee_mom_ipsi;
    rows.knee_flexion_moment_contra_Nm_kg = knee_mom_contra;
    rows.ankle_dorsiflexion_moment_ipsi_Nm_kg = ankle_mom_ipsi;
    rows.ankle_dorsiflexion_moment_contra_Nm_kg = ankle_mom_contra;

    rows.grf_vertical_ipsi_BW = grf_vertical_ipsi;
    rows.grf_vertical_contra_BW = grf_vertical_contra;
    rows.grf_anterior_ipsi_BW = grf_anterior_ipsi;
    rows.grf_anterior_contra_BW = grf_anterior_contra;
    rows.grf_lateral_ipsi_BW = grf_lateral_ipsi;
    rows.grf_lateral_contra_BW = grf_lateral_contra;

    rows.cop_anterior_ipsi_m = cop_anterior_ipsi;
    rows.cop_anterior_contra_m = cop_anterior_contra;
    rows.cop_lateral_ipsi_m = cop_lateral_ipsi;
    rows.cop_lateral_contra_m = cop_lateral_contra;
    rows.cop_vertical_ipsi_m = cop_vertical_ipsi;
    rows.cop_vertical_contra_m = cop_vertical_contra;

    rows.pelvis_sagittal_angle_rad = pelvis_sag;
    rows.trunk_sagittal_angle_rad = trunk_sag;
    rows.pelvis_sagittal_velocity_rad_s = pelvis_vel;
    rows.trunk_sagittal_velocity_rad_s = trunk_vel;
    rows.thigh_sagittal_angle_ipsi_rad = thigh_ipsi;
    rows.thigh_sagittal_angle_contra_rad = thigh_contra;
    rows.shank_sagittal_angle_ipsi_rad = shank_ipsi;
    rows.shank_sagittal_angle_contra_rad = shank_contra;
    rows.foot_sagittal_angle_ipsi_rad = foot_ipsi;
    rows.foot_sagittal_angle_contra_rad = foot_contra;
    rows.thigh_sagittal_velocity_ipsi_rad_s = thigh_vel_ipsi;
    rows.thigh_sagittal_velocity_contra_rad_s = thigh_vel_contra;
    rows.shank_sagittal_velocity_ipsi_rad_s = shank_vel_ipsi;
    rows.shank_sagittal_velocity_contra_rad_s = shank_vel_contra;
    rows.foot_sagittal_velocity_ipsi_rad_s = foot_vel_ipsi;
    rows.foot_sagittal_velocity_contra_rad_s = foot_vel_contra;
end


function out = interp_optional(tbl, var_name, source_time, target_time)
    out = NaN(numel(target_time), 1);
    if any(strcmp(tbl.Properties.VariableNames, var_name))
        values = tbl.(var_name)(:);
        out = interp1(source_time, values, target_time, 'linear', NaN);
        out = out(:);
    end
end


function best_fp = select_best_force_plate(fp_tbl, time_start, time_end, first_hs_time)
    best_fp = '';
    if isempty(fp_tbl) || ~istable(fp_tbl) || ~any(strcmp(fp_tbl.Properties.VariableNames, 'Header'))
        return;
    end

    fp_names = {};
    for idx = 1:numel(fp_tbl.Properties.VariableNames)
        var_name = fp_tbl.Properties.VariableNames{idx};
        if startsWith(var_name, 'FP') && endsWith(var_name, '_vy')
            fp_names{end+1} = erase(var_name, '_vy'); %#ok<AGROW>
        end
    end
    if isempty(fp_names)
        return;
    end

    fp_time = fp_tbl.Header(:);
    if ~isempty(first_hs_time)
        check_time = min(time_end, first_hs_time + 0.2);
        check_idx = find(fp_time >= check_time, 1, 'first');
    else
        check_idx = [];
    end

    best_force = 0;
    if ~isempty(check_idx)
        for idx = 1:numel(fp_names)
            vy_name = [fp_names{idx} '_vy'];
            force_at_check = abs(fp_tbl.(vy_name)(check_idx));
            if force_at_check > best_force
                best_force = force_at_check;
                best_fp = fp_names{idx};
            end
        end
        if best_force > 200
            return;
        end
    end

    window_mask = fp_time >= time_start & fp_time <= time_end;
    if ~any(window_mask)
        return;
    end

    best_force = 0;
    best_fp = '';
    for idx = 1:numel(fp_names)
        vy_name = [fp_names{idx} '_vy'];
        force_peak = max(abs(fp_tbl.(vy_name)(window_mask)), [], 'omitnan');
        if force_peak > best_force
            best_force = force_peak;
            best_fp = fp_names{idx};
        end
    end

    if best_force <= 200
        best_fp = '';
    end
end


function task_info = append_time_metadata(task_info, collection_id, time_reset_per_label, sampling_rate_hz, first_leg, mode)
    task_info = sprintf('%s,time_scope:continuous_trial,time_reset_per:%s,collection_source:%s,collection_id:%s,sampling_rate_hz:%.3f,reference_leg:%s', ...
        task_info, time_reset_per_label, mode, collection_id, sampling_rate_hz, first_leg);
end


function [task, task_id, task_info] = map_levelground_label(label_name, speed_val)
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
    task = '';
    task_id = '';
    task_info = '';
    angle_up = abs(ramp_angle);
    angle_down = -abs(ramp_angle);
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
            task_id = sprintf('decline_%.1fdeg', abs(angle_down));
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
    task = '';
    task_id = '';
    task_info = '';
    base_info = sprintf('step_height_m:%.3f,surface:stairs', stair_height_m);

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


function segments = get_label_segments(labels, header, target_label, min_samples)
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
    segments = segments(durations > 0.05, :);
end


function trial_data = load_trial_data(mode_path, trial_name)
    trial_data = struct();

    try
        cond_file = fullfile(mode_path, 'conditions', trial_name);
        if exist(cond_file, 'file')
            temp = load(cond_file);
            if isfield(temp, 'speed') && istable(temp.speed)
                trial_data.conditions = temp.speed;
            elseif isfield(temp, 'data') && istable(temp.data)
                trial_data.conditions = temp.data;
            elseif isfield(temp, 'labels') && istable(temp.labels)
                trial_data.conditions = temp.labels;
            else
                trial_data.conditions = temp;
            end
            if isfield(temp, 'stairHeight')
                trial_data.stairHeight = temp.stairHeight;
            end
            if isfield(temp, 'rampIncline')
                trial_data.rampIncline = temp.rampIncline;
            end
        end

        ik_file = fullfile(mode_path, 'ik_offset', trial_name);
        if exist(ik_file, 'file')
            temp = load(ik_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.ik_offset = temp.data;
            else
                trial_data.ik_offset = temp;
            end
        end

        id_file = fullfile(mode_path, 'id', trial_name);
        if exist(id_file, 'file')
            temp = load(id_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.id = temp.data;
            else
                trial_data.id = temp;
            end
        end

        gc_file = fullfile(mode_path, 'gcRight', trial_name);
        if exist(gc_file, 'file')
            temp = load(gc_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.gcRight = temp.data;
            else
                trial_data.gcRight = temp;
            end
        end

        gc_file_left = fullfile(mode_path, 'gcLeft', trial_name);
        if exist(gc_file_left, 'file')
            temp = load(gc_file_left);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.gcLeft = temp.data;
            else
                trial_data.gcLeft = temp;
            end
        end

        fp_file = fullfile(mode_path, 'fp', trial_name);
        if exist(fp_file, 'file')
            temp = load(fp_file);
            if isfield(temp, 'data') && istable(temp.data)
                trial_data.fp = temp.data;
            else
                trial_data.fp = temp;
            end
        end

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
