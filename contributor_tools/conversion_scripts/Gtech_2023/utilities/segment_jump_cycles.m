function [segments, n_jumps] = segment_jump_cycles(grf_file, varargin)
% SEGMENT_JUMP_CYCLES Segment jump activities using standing-to-standing detection.
%
% This function detects jump cycles by identifying stable standing phases and
% flight phases, then segmenting from stable standing through jump back to
% stable standing. This captures the full jump including countermovement
% preparation and landing recovery.
%
% Cycle definition: stable standing -> countermovement -> takeoff -> flight -> landing -> stable standing
%
% Usage:
%   segments = segment_jump_cycles(grf_file)
%   [segments, n_jumps] = segment_jump_cycles(grf_file, 'FlightThreshold', 50)
%
% Args:
%   grf_file: Path to GroundFrame_GRFs.csv file
%
% Optional Parameters:
%   'VelocityFile': Path to Joint_Velocities.csv (default: derived from grf_file path)
%   'FlightThreshold': GRF (N) below which subject is in flight (default: 50)
%   'StandingThreshold': GRF (N) above which subject is standing (default: 600)
%   'VelocityThreshold': Joint velocity (deg/s) below which motion is stable (default: 25)
%   'MinFlightDuration': Minimum flight duration (s) to be a real jump (default: 0.05)
%   'MinStableDuration': Minimum stable standing duration (s) (default: 0.2)
%   'SmoothWindow': Smoothing window in seconds (default: 0.05)
%   'MinDuration': Minimum cycle duration (s) (default: 0.5)
%   'MaxDuration': Maximum cycle duration (s) (default: 4.0)
%   'UseIQRFiltering': Use IQR-based outlier removal (default: true)
%   'MarginBefore': Extra time (s) before detected motion onset (default: 0.05)
%   'MarginAfter': Extra time (s) after detected motion offset (default: 0.05)
%
% Returns:
%   segments: Struct array with fields:
%       - type: 'jump'
%       - start_idx, end_idx: Sample indices
%       - start_time, end_time: Time values
%       - duration: Cycle duration
%       - flight_duration: Duration of flight phase within cycle
%   n_jumps: Number of jump cycles detected

    % Parse optional arguments
    p = inputParser;
    addRequired(p, 'grf_file', @ischar);
    addParameter(p, 'VelocityFile', '', @ischar);
    addParameter(p, 'FlightThreshold', 50, @isnumeric);      % N - below this = flight
    addParameter(p, 'StandingThreshold', 600, @isnumeric);   % N - above this = standing
    addParameter(p, 'VelocityThreshold', 25, @isnumeric);    % deg/s - below this = stable
    addParameter(p, 'MinFlightDuration', 0.05, @isnumeric);  % seconds
    addParameter(p, 'MinStableDuration', 0.2, @isnumeric);   % seconds
    addParameter(p, 'SmoothWindow', 0.05, @isnumeric);       % seconds
    addParameter(p, 'MinDuration', 0.5, @isnumeric);         % seconds
    addParameter(p, 'MaxDuration', 4.0, @isnumeric);         % seconds
    addParameter(p, 'UseIQRFiltering', true, @islogical);
    addParameter(p, 'MarginBefore', 0.05, @isnumeric);       % seconds
    addParameter(p, 'MarginAfter', 0.05, @isnumeric);        % seconds
    parse(p, grf_file, varargin{:});

    flight_thresh = p.Results.FlightThreshold;
    standing_thresh = p.Results.StandingThreshold;
    velocity_thresh = p.Results.VelocityThreshold;
    min_flight_dur = p.Results.MinFlightDuration;
    min_stable_dur = p.Results.MinStableDuration;
    smooth_window = p.Results.SmoothWindow;
    min_duration = p.Results.MinDuration;
    max_duration = p.Results.MaxDuration;
    use_iqr_filtering = p.Results.UseIQRFiltering;
    velocity_file = p.Results.VelocityFile;
    margin_before = p.Results.MarginBefore;
    margin_after = p.Results.MarginAfter;

    % Initialize outputs
    segments = struct('type', {}, 'start_idx', {}, 'end_idx', {}, ...
                      'start_time', {}, 'end_time', {}, 'duration', {}, ...
                      'flight_duration', {});
    n_jumps = 0;

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

    % Extract time and vertical GRF
    time = grf_data.time;

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
    n_samples = length(time);

    % Smooth GRF
    smooth_samples = max(1, round(sample_rate * smooth_window));
    smooth_vert = movmean(total_vert, smooth_samples);

    % Load joint velocity data for kinematic-based segmentation
    max_joint_vel = [];
    vel_time = [];
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
                max_joint_vel = movmean(max_joint_vel, smooth_samples);

                use_kinematic_bounds = true;
                fprintf('    Using kinematic velocity bounds for jump segmentation\n');
            else
                warning('No joint velocity columns found in %s', velocity_file);
            end
        catch ME
            warning('Failed to read velocity file: %s', ME.message);
        end
    else
        fprintf('    Velocity file not found, using GRF-only segmentation\n');
    end

    % Detect flight phases (GRF below threshold)
    in_flight = smooth_vert < flight_thresh;

    % Find flight phase transitions
    flight_changes = diff([0; in_flight; 0]);
    takeoff_idx = find(flight_changes == 1);   % Start of flight
    landing_idx = find(flight_changes == -1);  % End of flight (landing)

    % Ensure we have matching pairs
    if isempty(takeoff_idx) || isempty(landing_idx)
        warning('No flight phases detected in %s', grf_file);
        return;
    end

    % Filter flight phases by minimum duration
    min_flight_samples = round(min_flight_dur * sample_rate);
    valid_flights = [];

    for i = 1:min(length(takeoff_idx), length(landing_idx))
        if landing_idx(i) > takeoff_idx(i)
            flight_samples = landing_idx(i) - takeoff_idx(i);
            if flight_samples >= min_flight_samples
                valid_flights(end+1, :) = [takeoff_idx(i), landing_idx(i)];
            end
        end
    end

    if isempty(valid_flights)
        warning('No valid flight phases (>%.2fs) detected', min_flight_dur);
        return;
    end

    fprintf('    Detected %d valid flight phases\n', size(valid_flights, 1));

    % For each flight phase, find stable standing before and after
    min_stable_samples = round(min_stable_dur * sample_rate);
    margin_samples_before = round(margin_before * sample_rate);
    margin_samples_after = round(margin_after * sample_rate);

    for i = 1:size(valid_flights, 1)
        flight_start = valid_flights(i, 1);
        flight_end = valid_flights(i, 2);
        flight_dur = time(flight_end) - time(flight_start);

        % Define search boundaries: don't go past adjacent flights
        if i > 1
            search_start_limit = valid_flights(i-1, 2);  % After previous landing
        else
            search_start_limit = 1;
        end
        if i < size(valid_flights, 1)
            search_end_limit = valid_flights(i+1, 1);    % Before next takeoff
        else
            search_end_limit = n_samples;
        end

        % Find stable standing BEFORE this jump
        % Search backward from takeoff for stable standing (high GRF, low velocity)
        seg_start_idx = flight_start;

        if use_kinematic_bounds
            % Use velocity-based detection
            for j = flight_start:-1:max(1, search_start_limit)
                % Check if standing (high GRF)
                if smooth_vert(j) < standing_thresh
                    continue;  % Not standing yet
                end

                % Find corresponding velocity index
                [~, vel_idx] = min(abs(vel_time - time(j)));
                if vel_idx >= 1 && vel_idx <= length(max_joint_vel)
                    if max_joint_vel(vel_idx) < velocity_thresh
                        % Found a stable point, check if sustained
                        stable_count = 0;
                        for k = vel_idx:-1:max(1, vel_idx - min_stable_samples)
                            if k <= length(max_joint_vel) && max_joint_vel(k) < velocity_thresh
                                % Also check GRF is high
                                [~, grf_idx] = min(abs(time - vel_time(k)));
                                if grf_idx >= 1 && grf_idx <= n_samples && smooth_vert(grf_idx) > standing_thresh
                                    stable_count = stable_count + 1;
                                end
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples / 2
                            seg_start_idx = j;
                            break;
                        end
                    end
                end
            end
        else
            % GRF-only: find where GRF first crosses standing threshold before takeoff
            for j = flight_start:-1:max(1, search_start_limit)
                if smooth_vert(j) > standing_thresh
                    % Check if stable
                    stable_count = 0;
                    for k = j:-1:max(1, j - min_stable_samples)
                        if smooth_vert(k) > standing_thresh
                            stable_count = stable_count + 1;
                        else
                            break;
                        end
                    end
                    if stable_count >= min_stable_samples / 2
                        seg_start_idx = j;
                        break;
                    end
                end
            end
        end

        % Find stable standing AFTER this jump
        % Search forward from landing for stable standing (high GRF, low velocity)
        seg_end_idx = flight_end;

        if use_kinematic_bounds
            % Use velocity-based detection
            for j = flight_end:min(n_samples, search_end_limit)
                % Check if standing (high GRF)
                if smooth_vert(j) < standing_thresh
                    continue;  % Not standing yet
                end

                % Find corresponding velocity index
                [~, vel_idx] = min(abs(vel_time - time(j)));
                if vel_idx >= 1 && vel_idx <= length(max_joint_vel)
                    if max_joint_vel(vel_idx) < velocity_thresh
                        % Found a stable point, check if sustained
                        stable_count = 0;
                        for k = vel_idx:min(length(max_joint_vel), vel_idx + min_stable_samples)
                            if max_joint_vel(k) < velocity_thresh
                                % Also check GRF is high
                                [~, grf_idx] = min(abs(time - vel_time(k)));
                                if grf_idx >= 1 && grf_idx <= n_samples && smooth_vert(grf_idx) > standing_thresh
                                    stable_count = stable_count + 1;
                                end
                            else
                                break;
                            end
                        end
                        if stable_count >= min_stable_samples / 2
                            seg_end_idx = j;
                            break;
                        end
                    end
                end
            end
        else
            % GRF-only: find where GRF stabilizes above standing threshold after landing
            for j = flight_end:min(n_samples, search_end_limit)
                if smooth_vert(j) > standing_thresh
                    % Check if stable
                    stable_count = 0;
                    for k = j:min(n_samples, j + min_stable_samples)
                        if smooth_vert(k) > standing_thresh
                            stable_count = stable_count + 1;
                        else
                            break;
                        end
                    end
                    if stable_count >= min_stable_samples / 2
                        seg_end_idx = j;
                        break;
                    end
                end
            end
        end

        % Add small margins
        seg_start_idx = max(1, seg_start_idx - margin_samples_before);
        seg_end_idx = min(n_samples, seg_end_idx + margin_samples_after);

        % Ensure we don't overlap with adjacent jumps
        seg_start_idx = max(seg_start_idx, search_start_limit);
        seg_end_idx = min(seg_end_idx, search_end_limit);

        seg_start_time = time(seg_start_idx);
        seg_end_time = time(seg_end_idx);
        seg_duration = seg_end_time - seg_start_time;

        % Basic duration check
        if seg_duration >= min_duration && seg_duration <= max_duration
            seg.type = 'jump';
            seg.start_idx = seg_start_idx;
            seg.end_idx = seg_end_idx;
            seg.start_time = seg_start_time;
            seg.end_time = seg_end_time;
            seg.duration = seg_duration;
            seg.flight_duration = flight_dur;
            segments(end+1) = seg;

            fprintf('    jump: %.2fs - %.2fs (duration: %.2fs, flight: %.2fs)\n', ...
                seg_start_time, seg_end_time, seg_duration, flight_dur);
        end
    end

    n_jumps = length(segments);

    % Apply IQR-based filtering if enabled and enough samples
    if use_iqr_filtering && n_jumps >= 4
        durations = [segments.duration];
        Q1 = prctile(durations, 25);
        Q3 = prctile(durations, 75);
        IQR = Q3 - Q1;

        iqr_min = max(min_duration, Q1 - 1.5 * IQR);
        iqr_max = min(max_duration, Q3 + 1.5 * IQR);

        fprintf('    IQR filtering: Q1=%.2fs, Q3=%.2fs, IQR=%.2fs\n', Q1, Q3, IQR);
        fprintf('    Adaptive bounds: %.2fs < duration < %.2fs\n', iqr_min, iqr_max);

        valid_idx = (durations >= iqr_min) & (durations <= iqr_max);
        n_before = n_jumps;
        segments = segments(valid_idx);
        n_jumps = length(segments);

        if n_before > n_jumps
            fprintf('    Duration filtering: removed %d of %d segments\n', ...
                n_before - n_jumps, n_before);
        end
    end

    fprintf('    Total: %d jump cycles detected (standing -> jump -> standing)\n', n_jumps);
end
