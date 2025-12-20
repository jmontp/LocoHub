function [segments, n_jumps] = segment_jump_cycles(grf_file, varargin)
% SEGMENT_JUMP_CYCLES Segment cyclic jump activities (hops) using GRF-based flight detection.
%
% This function detects jump cycles by identifying flight phases (both feet off ground)
% and segmenting from landing to landing.
%
% Usage:
%   segments = segment_jump_cycles(grf_file)
%   [segments, n_jumps] = segment_jump_cycles(grf_file, 'FlightThreshold', 50)
%
% Args:
%   grf_file: Path to GroundFrame_GRFs.csv file
%
% Optional Parameters:
%   'FlightThreshold': GRF (N) below which subject is in flight (default: 50)
%   'MinFlightDuration': Minimum flight duration (s) to be a real jump (default: 0.1)
%   'MinGroundDuration': Minimum ground contact duration (s) (default: 0.1)
%   'SmoothWindow': Smoothing window in seconds (default: 0.02)
%   'MinDuration': Minimum cycle duration (s) (default: 0.3)
%   'MaxDuration': Maximum cycle duration (s) (default: 3.0)
%   'UseIQRFiltering': Use IQR-based outlier removal (default: true)
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
    addParameter(p, 'FlightThreshold', 50, @isnumeric);      % N - below this = flight
    addParameter(p, 'MinFlightDuration', 0.1, @isnumeric);   % seconds
    addParameter(p, 'MinGroundDuration', 0.1, @isnumeric);   % seconds
    addParameter(p, 'SmoothWindow', 0.02, @isnumeric);       % seconds
    addParameter(p, 'MinDuration', 0.3, @isnumeric);         % seconds
    addParameter(p, 'MaxDuration', 3.0, @isnumeric);         % seconds
    addParameter(p, 'UseIQRFiltering', true, @islogical);
    parse(p, grf_file, varargin{:});

    flight_thresh = p.Results.FlightThreshold;
    min_flight_dur = p.Results.MinFlightDuration;
    min_ground_dur = p.Results.MinGroundDuration;
    smooth_window = p.Results.SmoothWindow;
    min_duration = p.Results.MinDuration;
    max_duration = p.Results.MaxDuration;
    use_iqr_filtering = p.Results.UseIQRFiltering;

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

    % Create segments from landing to landing
    % Each jump cycle: landing_i -> ground contact -> takeoff -> flight -> landing_(i+1)
    landing_times = time(valid_flights(:, 2));

    min_ground_samples = round(min_ground_dur * sample_rate);

    for i = 1:(size(valid_flights, 1) - 1)
        % Segment from this landing to next landing
        seg_start_idx = valid_flights(i, 2);      % This landing
        seg_end_idx = valid_flights(i+1, 2);      % Next landing

        % Check for minimum ground contact between flights
        ground_samples = valid_flights(i+1, 1) - valid_flights(i, 2);
        if ground_samples < min_ground_samples
            continue;  % Skip if ground contact too short
        end

        seg_start_time = time(seg_start_idx);
        seg_end_time = time(seg_end_idx);
        seg_duration = seg_end_time - seg_start_time;

        % Calculate flight duration within this cycle
        flight_start = valid_flights(i+1, 1);
        flight_end = valid_flights(i+1, 2);
        flight_dur = time(flight_end) - time(flight_start);

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

    fprintf('    Total: %d jump cycles detected\n', n_jumps);
end
