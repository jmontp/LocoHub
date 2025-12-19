function [segments, n_sit_to_stand, n_stand_to_sit] = segment_sit_stand_transitions(grf_file, varargin)
% SEGMENT_SIT_STAND_TRANSITIONS Segment sit-to-stand and stand-to-sit transitions.
%
% This function uses a kinematic-based approach to detect transitions between
% sitting and standing. It combines:
%   1. GRF thresholds to determine sitting vs standing states
%   2. Joint velocity thresholds to detect when motion starts and ends
%
% The kinematic approach ensures segment boundaries match actual motion
% onset/offset rather than using arbitrary time windows.
%
% Usage:
%   segments = segment_sit_stand_transitions(grf_file)
%   segments = segment_sit_stand_transitions(grf_file, 'VelocityFile', vel_file)
%   [segments, n_sts, n_s2s] = segment_sit_stand_transitions(grf_file)
%
% Args:
%   grf_file: Path to GroundFrame_GRFs.csv file
%
% Optional Parameters:
%   'VelocityFile': Path to Joint_Velocities.csv (default: derived from grf_file path)
%   'StandingThreshold': GRF (N) above which subject is standing (default: 600)
%   'SittingThreshold': GRF (N) below which subject is sitting (default: 400)
%   'VelocityThreshold': Joint velocity (deg/s) below which motion is stable (default: 15)
%   'MinStableDuration': Minimum stable duration (s) to confirm state (default: 0.3)
%   'SmoothWindow': Smoothing window in seconds for state detection (default: 0.3)
%   'MarginBefore': Extra time (s) before detected motion onset (default: 0.1)
%   'MarginAfter': Extra time (s) after detected motion offset (default: 0.1)
%
% Returns:
%   segments: Struct array with fields:
%       - type: 'sit_to_stand' or 'stand_to_sit'
%       - start_idx, end_idx: Sample indices
%       - start_time, end_time: Time values
%       - mid_time: Transition midpoint time
%       - duration: Window duration
%   n_sit_to_stand: Number of sit-to-stand transitions
%   n_stand_to_sit: Number of stand-to-sit transitions

    % Parse optional arguments
    p = inputParser;
    addRequired(p, 'grf_file', @ischar);
    addParameter(p, 'VelocityFile', '', @ischar);
    addParameter(p, 'StandingThreshold', 600, @isnumeric);
    addParameter(p, 'SittingThreshold', 400, @isnumeric);
    addParameter(p, 'VelocityThreshold', 15, @isnumeric);  % deg/s
    addParameter(p, 'MinStableDuration', 0.3, @isnumeric);
    addParameter(p, 'SmoothWindow', 0.3, @isnumeric);
    addParameter(p, 'MarginBefore', 0.1, @isnumeric);
    addParameter(p, 'MarginAfter', 0.1, @isnumeric);
    addParameter(p, 'MinDuration', 0.3, @isnumeric);   % Absolute minimum duration floor (s)
    addParameter(p, 'MaxDuration', 5.0, @isnumeric);   % Absolute maximum duration ceiling (s)
    addParameter(p, 'FilterByDuration', true, @islogical);  % Enable duration filtering
    addParameter(p, 'UseIQRFiltering', true, @islogical);   % Use IQR-based adaptive thresholds
    addParameter(p, 'TrimStartPercent', 0.0, @isnumeric);   % Trim this % from start of each segment
    parse(p, grf_file, varargin{:});

    standing_thresh = p.Results.StandingThreshold;
    sitting_thresh = p.Results.SittingThreshold;
    velocity_thresh = p.Results.VelocityThreshold;
    min_stable_duration = p.Results.MinStableDuration;
    smooth_window = p.Results.SmoothWindow;
    margin_before = p.Results.MarginBefore;
    margin_after = p.Results.MarginAfter;
    velocity_file = p.Results.VelocityFile;
    min_duration = p.Results.MinDuration;
    max_duration = p.Results.MaxDuration;
    filter_by_duration = p.Results.FilterByDuration;
    use_iqr_filtering = p.Results.UseIQRFiltering;
    trim_start_pct = p.Results.TrimStartPercent;

    % Initialize outputs
    segments = struct('type', {}, 'start_idx', {}, 'end_idx', {}, ...
                      'start_time', {}, 'end_time', {}, 'mid_time', {}, 'duration', {});
    n_sit_to_stand = 0;
    n_stand_to_sit = 0;

    % Check GRF file exists
    if ~exist(grf_file, 'file')
        warning('GRF file not found: %s', grf_file);
        return;
    end

    % Derive velocity file path if not provided
    if isempty(velocity_file)
        velocity_file = strrep(grf_file, 'GroundFrame_GRFs.csv', 'Joint_Velocities.csv');
    end

    % Load GRF data
    try
        grf_data = readtable(grf_file);
    catch ME
        warning('Failed to read GRF file: %s', ME.message);
        return;
    end

    % Extract time and vertical GRF columns
    time = grf_data.time;

    % Total vertical GRF (sum of both feet)
    if ismember('LForceY_Vertical', grf_data.Properties.VariableNames) && ...
       ismember('RForceY_Vertical', grf_data.Properties.VariableNames)
        total_vert = grf_data.LForceY_Vertical + grf_data.RForceY_Vertical;
    else
        warning('Expected GRF columns not found in file');
        return;
    end

    % Calculate sample rate
    dt = time(2) - time(1);
    sample_rate = 1 / dt;

    % Load joint velocity data for kinematic-based segmentation
    vel_data = [];
    max_joint_vel = [];
    use_kinematic_bounds = false;

    if exist(velocity_file, 'file')
        try
            vel_data = readtable(velocity_file);
            vel_time = vel_data.time;

            % Get relevant joint velocities (hip, knee, ankle for both legs)
            vel_cols = {};
            possible_cols = {'hip_flexion_velocity_l', 'hip_flexion_velocity_r', ...
                            'knee_velocity_l', 'knee_velocity_r', ...
                            'ankle_velocity_l', 'ankle_velocity_r'};
            for c = 1:length(possible_cols)
                if ismember(possible_cols{c}, vel_data.Properties.VariableNames)
                    vel_cols{end+1} = possible_cols{c};
                end
            end

            if ~isempty(vel_cols)
                % Compute max absolute velocity across all joints at each time point
                vel_matrix = zeros(height(vel_data), length(vel_cols));
                for c = 1:length(vel_cols)
                    vel_matrix(:, c) = abs(vel_data.(vel_cols{c}));
                end
                max_joint_vel = max(vel_matrix, [], 2);

                % Smooth the velocity signal
                smooth_samples = max(1, round(sample_rate * smooth_window));
                max_joint_vel = movmean(max_joint_vel, smooth_samples);

                use_kinematic_bounds = true;
                fprintf('    Using kinematic velocity bounds for segmentation\n');
            else
                warning('No joint velocity columns found in %s', velocity_file);
            end
        catch ME
            warning('Failed to read velocity file: %s', ME.message);
        end
    else
        warning('Velocity file not found: %s. Using GRF-only segmentation.', velocity_file);
    end

    % Smooth GRF for state detection
    smooth_samples = max(1, round(sample_rate * smooth_window));
    smooth_vert = movmean(total_vert, smooth_samples);

    % State machine for GRF-based sitting/standing detection
    n_samples = length(time);
    grf_states = cell(n_samples, 1);
    current_state = 'unknown';

    for i = 1:n_samples
        if smooth_vert(i) > standing_thresh
            new_state = 'standing';
        elseif smooth_vert(i) < sitting_thresh
            new_state = 'sitting';
        else
            if strcmp(current_state, 'unknown')
                new_state = 'transition';
            else
                new_state = current_state;
            end
        end
        grf_states{i} = new_state;
        current_state = new_state;
    end

    % Find GRF transition crossing points (sitting <-> standing)
    transitions = struct('type', {}, 'cross_idx', {}, 'cross_time', {});

    for i = 2:n_samples
        if strcmp(grf_states{i-1}, 'sitting') && strcmp(grf_states{i}, 'standing')
            trans.type = 'sit_to_stand';
            trans.cross_idx = i;
            trans.cross_time = time(i);
            transitions(end+1) = trans;
        elseif strcmp(grf_states{i-1}, 'standing') && strcmp(grf_states{i}, 'sitting')
            trans.type = 'stand_to_sit';
            trans.cross_idx = i;
            trans.cross_time = time(i);
            transitions(end+1) = trans;
        end
    end

    % Process each transition to create segments
    % Key insight: constrain search to not overlap with adjacent transitions
    min_stable_samples = round(min_stable_duration * sample_rate);

    for t = 1:length(transitions)
        trans = transitions(t);
        cross_idx = trans.cross_idx;
        cross_time = trans.cross_time;

        % Define search boundaries: don't go past adjacent transitions
        if t > 1
            search_start_limit = transitions(t-1).cross_idx;
        else
            search_start_limit = 1;
        end
        if t < length(transitions)
            search_end_limit = transitions(t+1).cross_idx;
        else
            search_end_limit = n_samples;
        end

        if use_kinematic_bounds
            % Use velocity-based motion detection
            % Find motion onset: search backward from crossing for where velocity RISES
            % (i.e., find the last stable point before motion started)
            motion_start_idx = cross_idx;

            for j = cross_idx:-1:max(1, search_start_limit)
                % Find corresponding velocity index
                [~, vel_idx] = min(abs(vel_time - time(j)));
                if vel_idx >= 1 && vel_idx <= length(max_joint_vel)
                    if max_joint_vel(vel_idx) < velocity_thresh
                        % Found a stable point, check if sustained
                        stable_count = 0;
                        for k = vel_idx:-1:max(1, vel_idx - min_stable_samples)
                            if max_joint_vel(k) < velocity_thresh
                                stable_count = stable_count + 1;
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples / 2  % Relaxed requirement
                            motion_start_idx = j;
                            break;
                        end
                    end
                end
            end

            % Find motion offset: search forward from crossing for where velocity DROPS
            motion_end_idx = cross_idx;

            for j = cross_idx:min(n_samples, search_end_limit)
                [~, vel_idx] = min(abs(vel_time - time(j)));
                if vel_idx >= 1 && vel_idx <= length(max_joint_vel)
                    if max_joint_vel(vel_idx) < velocity_thresh
                        % Found a stable point, check if sustained
                        stable_count = 0;
                        for k = vel_idx:min(length(max_joint_vel), vel_idx + min_stable_samples)
                            if max_joint_vel(k) < velocity_thresh
                                stable_count = stable_count + 1;
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples / 2  % Relaxed requirement
                            motion_end_idx = j;
                            break;
                        end
                    end
                end
            end

            % Add small margins
            margin_samples_before = round(margin_before * sample_rate);
            margin_samples_after = round(margin_after * sample_rate);

            window_start_idx = max(1, motion_start_idx - margin_samples_before);
            window_end_idx = min(n_samples, motion_end_idx + margin_samples_after);

            % Ensure we don't overlap with adjacent transitions
            window_start_idx = max(window_start_idx, search_start_limit);
            window_end_idx = min(window_end_idx, search_end_limit);

        else
            % Fallback: Use GRF-based heuristic (find stable regions)
            % Find start of transition (where GRF state was stable before)
            if strcmp(trans.type, 'sit_to_stand')
                start_idx = cross_idx;
                for j = cross_idx-1:-1:1
                    if strcmp(grf_states{j}, 'sitting')
                        start_idx = j;
                        break;
                    end
                end
            else  % stand_to_sit
                start_idx = cross_idx;
                for j = cross_idx-1:-1:1
                    if strcmp(grf_states{j}, 'standing')
                        start_idx = j;
                        break;
                    end
                end
            end

            % Find end of transition (where GRF state stabilizes after)
            if strcmp(trans.type, 'sit_to_stand')
                end_idx = cross_idx;
                for j = cross_idx+1:n_samples
                    if strcmp(grf_states{j}, 'standing')
                        end_idx = j;
                        % Continue until we have stable standing
                        stable_count = 0;
                        for k = j:min(n_samples, j + min_stable_samples)
                            if strcmp(grf_states{k}, 'standing')
                                stable_count = stable_count + 1;
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples
                            break;
                        end
                    end
                end
            else  % stand_to_sit
                end_idx = cross_idx;
                for j = cross_idx+1:n_samples
                    if strcmp(grf_states{j}, 'sitting')
                        end_idx = j;
                        stable_count = 0;
                        for k = j:min(n_samples, j + min_stable_samples)
                            if strcmp(grf_states{k}, 'sitting')
                                stable_count = stable_count + 1;
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples
                            break;
                        end
                    end
                end
            end

            window_start_idx = start_idx;
            window_end_idx = end_idx;
        end

        % Ensure valid indices
        window_start_idx = max(1, window_start_idx);
        window_end_idx = min(n_samples, window_end_idx);

        % Apply start trimming if specified
        if trim_start_pct > 0
            segment_length = window_end_idx - window_start_idx;
            trim_samples = round(segment_length * trim_start_pct / 100);
            window_start_idx = window_start_idx + trim_samples;
        end

        % Calculate midpoint
        mid_idx = floor((window_start_idx + window_end_idx) / 2);
        mid_time = time(mid_idx);

        % Only include if we have enough samples (at least ~100ms of data)
        if window_end_idx - window_start_idx > 10
            seg.type = trans.type;
            seg.start_idx = window_start_idx;
            seg.end_idx = window_end_idx;
            seg.start_time = time(window_start_idx);
            seg.end_time = time(window_end_idx);
            seg.mid_time = mid_time;
            seg.duration = time(window_end_idx) - time(window_start_idx);
            segments(end+1) = seg;

            if strcmp(trans.type, 'sit_to_stand')
                n_sit_to_stand = n_sit_to_stand + 1;
            else
                n_stand_to_sit = n_stand_to_sit + 1;
            end

            fprintf('    %s: %.2fs - %.2fs (duration: %.2fs)\n', ...
                trans.type, seg.start_time, seg.end_time, seg.duration);
        end
    end

    % Apply duration-based filtering to remove outliers
    if filter_by_duration && ~isempty(segments)
        n_before = length(segments);
        durations = [segments.duration];

        if use_iqr_filtering && length(durations) >= 4
            % IQR-based adaptive thresholds
            Q1 = prctile(durations, 25);
            Q3 = prctile(durations, 75);
            IQR = Q3 - Q1;

            % Calculate adaptive bounds with absolute floors/ceilings
            iqr_min = max(min_duration, Q1 - 1.5 * IQR);
            iqr_max = min(max_duration, Q3 + 1.5 * IQR);

            fprintf('    IQR filtering: Q1=%.2fs, Q3=%.2fs, IQR=%.2fs\n', Q1, Q3, IQR);
            fprintf('    Adaptive bounds: %.2fs < duration < %.2fs\n', iqr_min, iqr_max);

            % Filter by IQR-based bounds
            valid_idx = (durations >= iqr_min) & (durations <= iqr_max);
        else
            % Fixed threshold filtering (fallback or when not enough samples)
            valid_idx = (durations >= min_duration) & (durations <= max_duration);
            iqr_min = min_duration;
            iqr_max = max_duration;
        end

        segments = segments(valid_idx);
        n_after = length(segments);

        if n_before > n_after
            fprintf('    Duration filtering: removed %d of %d segments\n', ...
                n_before - n_after, n_before);
        end

        % Recount after filtering
        n_sit_to_stand = sum(strcmp({segments.type}, 'sit_to_stand'));
        n_stand_to_sit = sum(strcmp({segments.type}, 'stand_to_sit'));
    end
end
