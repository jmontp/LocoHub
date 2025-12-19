% Validate that converted parquet torque matches raw recomputation from .mat.
% Compares per-stride RMSE (estimated vs ID ankle dorsiflexion moment) from
% a raw recompute against the parquet signals produced by the converter.
%
% Usage: adjust the configuration block below, then run this script in MATLAB.
% It will error if the parquet RMSE deviates from the raw RMSE beyond tolerance.

%% Configuration
SCRIPT_DIR = fileparts(mfilename('fullpath'));
addpath(fullfile(SCRIPT_DIR, 'utilities'));

DATA_ROOT = fullfile(SCRIPT_DIR, 'CAMARGO_ET_AL_J_BIOMECH_DATASET');
if ~exist('PARQUET_PATH','var')
    PARQUET_PATH = fullfile(SCRIPT_DIR, '..', '..', '..', 'converted_datasets', 'gtech_2021_phase_test.parquet');
end

if ~exist('SUBJECT_CODE','var')
    SUBJECT_CODE = 'AB06';
end
if ~exist('DATE_FOLDER','var')
    DATE_FOLDER = '10_09_18';
end
if ~exist('MODE','var')
    MODE = 'treadmill';              % treadmill | ramp | stair | levelground
end
if ~exist('TRIAL_NAME','var')
    TRIAL_NAME = 'treadmill_01_01.mat';
end
if ~exist('LEG_OVERRIDE','var')
    LEG_OVERRIDE = '';          % set '' to auto-detect first HS leg; otherwise 'right'/'left'
end
if ~exist('TASK_FILTER','var')
    TASK_FILTER = 'level_walking';   % parquet task filter
end
if ~exist('TASK_INFO_FILTER','var')
    TASK_INFO_FILTER = 'speed_m_s:0.50'; % substring to match in task_info (set '' to skip)
end
NUM_POINTS = 150;
MAX_STRIDES = 200;               % limit plotted/checked strides
if ~exist('TORQUE_TOLERANCE','var')
    TORQUE_TOLERANCE = 0.05;     % allowable difference in mean RMSE (Nm/kg)
end

%% Load subject mass
subject_info = load(fullfile(DATA_ROOT, 'SubjectInfo.mat'));
subject_info = subject_info.data;
subject_mass = subject_info.Weight(strcmp(subject_info.Subject, SUBJECT_CODE));
if isempty(subject_mass)
    error('No mass entry for subject %s', SUBJECT_CODE);
end

%% Raw recompute from .mat
mode_path = fullfile(DATA_ROOT, SUBJECT_CODE, DATE_FOLDER, MODE);
trial_data = load_trial_tables(mode_path, TRIAL_NAME);
if isempty(trial_data.gcRight) || isempty(trial_data.gcLeft) || isempty(trial_data.ik_offset) || isempty(trial_data.id)
    error('Missing required tables for raw recompute (gcRight/gcLeft/ik_offset/id).');
end
if isempty(LEG_OVERRIDE)
    leg_side = detect_first_leg(trial_data);
    fprintf('Detected first heel-strike leg: %s\n', leg_side);
else
    leg_side = LEG_OVERRIDE;
end

% For treadmill: segment by target speed using same logic as converter
stride_data = [];
speed_target = parse_speed_target(TASK_INFO_FILTER);
if strcmpi(MODE, 'treadmill') && ~isempty(speed_target)
    stride_data = [];
    cond = trial_data.conditions;
    if ~isempty(cond) && istable(cond) && ...
       any(strcmp(cond.Properties.VariableNames, 'Speed')) && ...
       any(strcmp(cond.Properties.VariableNames, 'Header'))
        speed_vec = cond.Speed;
        time_vec = cond.Header;
        tolerance = 0.025;  % same as converter
        speed_mask = abs(speed_vec - speed_target) <= tolerance;
        transitions = diff([false; speed_mask; false]);
        region_starts = find(transitions == 1);
        region_ends = find(transitions == -1) - 1;
        min_len = 5000; % samples at 1000 Hz
        for r = 1:numel(region_starts)
            region_length = region_ends(r) - region_starts(r) + 1;
            if region_length < min_len
                continue;
            end
            time_start_region = time_vec(region_starts(r));
            time_end_region = time_vec(region_ends(r));
            % Use same ipsilateral leg selection as converter for this window
            [region_leg, ~] = gtech_determine_first_heel_strike(trial_data, time_start_region, time_end_region);
            if isempty(region_leg)
                continue;
            end
            sd_region = collect_strides(trial_data, region_leg, subject_mass, ...
                NUM_POINTS, MODE, time_start_region, time_end_region);
            stride_data = [stride_data; sd_region]; %#ok<AGROW>
        end
    end
    % Fallback: if no strides were found in the speed window, fall back to
    % stride-level speed filtering across the full trial.
    if isempty(stride_data)
        stride_data = collect_strides(trial_data, leg_side, subject_mass, NUM_POINTS, MODE);
        if ~isempty(stride_data)
            stride_data = filter_by_speed(stride_data, trial_data.conditions, speed_target);
        end
    end
else
    stride_data = collect_strides(trial_data, leg_side, subject_mass, NUM_POINTS, MODE);
end
if isempty(stride_data)
    error('No strides found in raw recompute.');
end
raw_rmse = compute_stride_rmse(stride_data);
if isfinite(MAX_STRIDES)
    raw_rmse = raw_rmse(1:min(MAX_STRIDES, numel(raw_rmse)));
end

%% Parquet recompute
parquet_data = parquetread(PARQUET_PATH);
keep_cols = { ...
    'phase_ipsi', ...
    'ankle_dorsiflexion_moment_ipsi_Nm_kg', ...
    'grf_vertical_ipsi_BW', ...
    'grf_anterior_ipsi_BW', ...
    'cop_anterior_ipsi_m', ...
    'cop_vertical_ipsi_m', ...
    'subject', 'task', 'task_info'};
missing_cols = setdiff(keep_cols, parquet_data.Properties.VariableNames);
if ~isempty(missing_cols)
    error('Parquet missing required columns: %s', strjoin(missing_cols, ', '));
end
parquet_data = parquet_data(:, keep_cols);

subject_id = sprintf('GT21_%s', SUBJECT_CODE);
parquet_mask = strcmp(parquet_data.subject, subject_id);
if ~isempty(TASK_FILTER)
    parquet_mask = parquet_mask & strcmp(parquet_data.task, TASK_FILTER);
end
if ~isempty(TASK_INFO_FILTER)
    parquet_mask = parquet_mask & contains(parquet_data.task_info, TASK_INFO_FILTER);
end
if ~any(parquet_mask)
    error('Filtered parquet has no rows for subject %s (task=%s, info~%s)', subject_id, TASK_FILTER, TASK_INFO_FILTER);
end
phase_p = reshape_stride(parquet_data.phase_ipsi(parquet_mask), NUM_POINTS);
id_p = reshape_stride(parquet_data.ankle_dorsiflexion_moment_ipsi_Nm_kg(parquet_mask), NUM_POINTS);
vgrf_p = reshape_stride(parquet_data.grf_vertical_ipsi_BW(parquet_mask), NUM_POINTS);
sgrf_p = reshape_stride(parquet_data.grf_anterior_ipsi_BW(parquet_mask), NUM_POINTS);
cop_ant_p = reshape_stride(parquet_data.cop_anterior_ipsi_m(parquet_mask), NUM_POINTS);
cop_vert_p = reshape_stride(parquet_data.cop_vertical_ipsi_m(parquet_mask), NUM_POINTS);

est_p = (-cop_ant_p .* vgrf_p + cop_vert_p .* sgrf_p) * 9.81;
% Optional sign search on stored COP/shear (should already be tuned in parquet, but re-check)
flip_opts = [1, -1];
best_est_p = zeros(size(est_p));
for i = 1:size(est_p,2)
    best = inf; chosen = est_p(:, i);
    for sa = flip_opts
        for sg = flip_opts
            cand = (-(sa * cop_ant_p(:, i)) .* vgrf_p(:, i) + cop_vert_p(:, i) .* (sg * sgrf_p(:, i))) * 9.81;
            rmse = sqrt(mean((cand - id_p(:, i)).^2, 'omitnan'));
            if rmse < best
                best = rmse;
                chosen = cand;
            end
        end
    end
    best_est_p(:, i) = chosen;
end
parquet_rmse = sqrt(mean((best_est_p - id_p).^2, 1, 'omitnan'))';
if isfinite(MAX_STRIDES)
    parquet_rmse = parquet_rmse(1:min(MAX_STRIDES, numel(parquet_rmse)));
end

%% Compare
mean_raw = mean(raw_rmse, 'omitnan');
mean_parquet = mean(parquet_rmse, 'omitnan');
delta = mean_parquet - mean_raw;

fprintf('Raw RMSE: mean=%.3f (n=%d)\n', mean_raw, numel(raw_rmse));
fprintf('Parquet RMSE: mean=%.3f (n=%d)\n', mean_parquet, numel(parquet_rmse));
fprintf('Delta (parquet - raw): %.3f Nm/kg\n', delta);

if abs(delta) > TORQUE_TOLERANCE
    error('RMSE difference (%.3f) exceeds tolerance %.3f', delta, TORQUE_TOLERANCE);
else
    fprintf('PASS: RMSE difference within tolerance.\n');
end

%% Helpers
function stride_data = collect_strides(trial_data, leg_side, subject_mass, NUM_POINTS, mode, time_start_override, time_end_override)
stride_data = [];
gc = select_gc(trial_data, leg_side);
if isempty(gc) || ~isfield(trial_data, 'ik_offset') || ~istable(trial_data.ik_offset)
    return;
end

if nargin >= 6
    window_override = true;
else
    window_override = false;
end

stride_indices = findFallingEdges_onlyInSection(gc.HeelStrike == 0, 1:height(gc));
if numel(stride_indices) < 2
    return;
end

gc_time = gc.Header;
heel_strike_pct = gc.HeelStrike;

for s = 1:(numel(stride_indices)-1)
    start_idx = max(1, stride_indices(s) - 1);
    end_idx = max(1, stride_indices(s+1) - 2);
    stride_pct = heel_strike_pct(start_idx:end_idx);
    stride_time = gc_time(start_idx:end_idx);

    if window_override
        if stride_time(1) < time_start_override || stride_time(end) > time_end_override
            continue;
        end
    end

    sd = gtech_compute_grf_cop_stride(trial_data, stride_time, stride_pct, ...
        leg_side, subject_mass, NUM_POINTS, mode);
    if isempty(sd)
        continue;
    end
    stride_data = [stride_data; sd]; %#ok<AGROW>
end
end

function rmse = compute_stride_rmse(stride_data)
n = numel(stride_data);
rmse = zeros(n, 1);
for i = 1:n
    rmse(i) = stride_data(i).best_rmse;
end
end

function gc = select_gc(trial_data, leg_side)
if strcmpi(leg_side, 'right')
    gc = trial_data.gcRight;
else
    gc = trial_data.gcLeft;
end
end

function val = reshape_stride(vec, stride_len)
vec = vec(:);
n = numel(vec);
r = mod(n, stride_len);
if r ~= 0
    error('Length %d not divisible by %d', n, stride_len);
end
q = n / stride_len;
val = reshape(vec, stride_len, q);
end

function speed = parse_speed_target(task_info_filter)
speed = [];
if isempty(task_info_filter), return; end
expr = 'speed_m_s:([0-9.]+)';
tokens = regexp(task_info_filter, expr, 'tokens');
if ~isempty(tokens)
    speed = str2double(tokens{1}{1});
end
end

function stride_data = filter_by_speed(stride_data, conditions_tbl, target_speed)
if isempty(conditions_tbl) || ~istable(conditions_tbl) || ...
   ~any(strcmp(conditions_tbl.Properties.VariableNames, 'Speed')) || ...
   ~any(strcmp(conditions_tbl.Properties.VariableNames, 'Header'))
    return;
end
speed_vec = conditions_tbl.Speed;
time_vec = conditions_tbl.Header;
tolerance = 0.025;
keep = true(numel(stride_data),1);
for i = 1:numel(stride_data)
    t0 = stride_data(i).start_time;
    t1 = stride_data(i).end_time;
    mask = (time_vec >= t0) & (time_vec <= t1);
    if ~any(mask)
        mask = (time_vec >= t0) & (time_vec <= t0 + 2); % fallback 2s window
    end
    stride_speed = mean(speed_vec(mask), 'omitnan');
    keep(i) = abs(stride_speed - target_speed) <= tolerance;
end
stride_data = stride_data(keep);
end

function leg_side = detect_first_leg(trial_data)
leg_side = 'right';
if ~isfield(trial_data, 'gcRight') || ~isfield(trial_data, 'gcLeft') || ...
   isempty(trial_data.gcRight) || isempty(trial_data.gcLeft)
    return;
end
gcR = trial_data.gcRight;
gcL = trial_data.gcLeft;

hs_r = findFallingEdges_onlyInSection(gcR.HeelStrike == 0, 1:height(gcR));
hs_l = findFallingEdges_onlyInSection(gcL.HeelStrike == 0, 1:height(gcL));

t_r = inf; t_l = inf;
if ~isempty(hs_r)
    idx = max(1, hs_r(1)-1);
    t_r = gcR.Header(idx);
end
if ~isempty(hs_l)
    idx = max(1, hs_l(1)-1);
    t_l = gcL.Header(idx);
end
if t_l < t_r
    leg_side = 'left';
else
    leg_side = 'right';
end
end

function trial_data = load_trial_tables(mode_path, trial_name)
trial_data = struct();
trial_data.conditions = load_table(fullfile(mode_path, 'conditions'), trial_name);
trial_data.ik_offset = load_table(fullfile(mode_path, 'ik_offset'), trial_name);
trial_data.id = load_table(fullfile(mode_path, 'id'), trial_name);
trial_data.gcRight = load_table(fullfile(mode_path, 'gcRight'), trial_name);
trial_data.gcLeft = load_table(fullfile(mode_path, 'gcLeft'), trial_name);
trial_data.fp = load_table(fullfile(mode_path, 'fp'), trial_name);
trial_data.markers = load_table(fullfile(mode_path, 'markers'), trial_name);
end

function tbl = load_table(folder, trial_name)
tbl = [];
f = fullfile(folder, trial_name);
if ~exist(f, 'file'), return; end
tmp = load(f);
if isfield(tmp, 'data') && istable(tmp.data)
    tbl = tmp.data;
elseif istable(tmp)
    tbl = tmp;
end
end
