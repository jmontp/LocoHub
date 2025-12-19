% Batch check: compute ankle torque from raw GRF + COP and compare to ID
% across all subjects/tasks/trials. Writes one PNG per subject/mode/trial/leg.
% Parquet mode: can also read processed signals from a parquet file and
% compute torque RMSE for direct comparison against the raw recompute.

clear; clc; close all;

SCRIPT_DIR = fileparts(mfilename('fullpath'));
addpath(fullfile(SCRIPT_DIR, 'utilities'));

%% Configuration
DATA_ROOT = fullfile(SCRIPT_DIR, 'CAMARGO_ET_AL_J_BIOMECH_DATASET');
RUN_RAW = false;       % run full raw recompute from .mat files
RUN_PARQUET = true;    % also load parquet and compute RMSE reference
PARQUET_PATH = fullfile(SCRIPT_DIR, '..', '..', '..', 'converted_datasets', 'gtech_2021_phase_dirty.parquet');
SUBJECTS = {};              % empty = all subjects under DATA_ROOT
MODES = {'treadmill', 'ramp', 'stair', 'levelground'};  % folders to search
LEGS = {'right', 'left'};
NUM_POINTS = 150;           % samples per stride
MAX_STRIDES_PLOT = 50;      % max strides to plot per mode/trial (worst RMSE)
OUTPUT_DIR = fullfile(SCRIPT_DIR, 'debug_ankle_torque_plots');

% Force plate selection for non-treadmill modes:
% choose plate with largest |vy| at heel strike + 200 ms (fallback: max |vy| over stride)

%% Subject list
if isempty(SUBJECTS)
    d = dir(fullfile(DATA_ROOT, 'AB*'));
    SUBJECTS = {d([d.isdir]).name};
end
subject_info = load(fullfile(DATA_ROOT, 'SubjectInfo.mat'));
subject_info = subject_info.data;

all_raw_rmse = [];

if RUN_PARQUET
    fprintf('Running parquet torque check on %s\n', PARQUET_PATH);
    all_parquet_rmse = plot_from_parquet(PARQUET_PATH, MAX_STRIDES_PLOT);
else
    all_parquet_rmse = [];
end

if ~RUN_RAW
    summarize_rmse(all_raw_rmse, all_parquet_rmse);
    return;
end

%% Iterate subjects/modes/trials
for s = 1:numel(SUBJECTS)
    subj = SUBJECTS{s};
    subj_mass = subject_info.Weight(strcmp(subject_info.Subject, subj));
    if isempty(subj_mass)
        fprintf('Skipping %s (no mass info)\n', subj);
        continue;
    end
    
    % Locate date folder (use first if multiple)
    date_dirs = dir(fullfile(DATA_ROOT, subj, '*_*'));
    if isempty(date_dirs)
        fprintf('Skipping %s (no date folder)\n', subj);
        continue;
    end
    date_folder = date_dirs(1).name;
    
    for m = 1:numel(MODES)
        mode = MODES{m};
        mode_path = fullfile(DATA_ROOT, subj, date_folder, mode);
        cond_folder = fullfile(mode_path, 'conditions');
        if ~exist(cond_folder, 'dir')
            continue;
        end
        trials = dir(fullfile(cond_folder, '*.mat'));
        for t = 1:numel(trials)
            trial_name = trials(t).name;
            trial_data = load_trial_tables(mode_path, trial_name);
            if isempty(trial_data.gcRight) || isempty(trial_data.gcLeft) || isempty(trial_data.ik_offset) || isempty(trial_data.id)
                fprintf('Skipping %s/%s/%s (missing required tables)\n', subj, mode, trial_name);
                continue;
            end
            for lg = 1:numel(LEGS)
                leg = LEGS{lg};
                stride_data = collect_strides(trial_data, leg, subj_mass, NUM_POINTS, mode);
                if isempty(stride_data)
                    continue;
                end
                rmse_raw = plot_stride_set(stride_data, min(numel(stride_data), MAX_STRIDES_PLOT), ...
                    sprintf('%s %s %s (%s)', subj, mode, trial_name, leg), ...
                    fullfile(OUTPUT_DIR, subj, mode), ...
                    sprintf('%s_%s_%s_%s.png', subj, mode, erase(trial_name, '.mat'), leg));
                all_raw_rmse = [all_raw_rmse; rmse_raw(:)]; %#ok<AGROW>
            end
        end
    end
end
fprintf('Done. Plots in %s\n', OUTPUT_DIR);
summarize_rmse(all_raw_rmse, all_parquet_rmse);

%% Helpers
function label = label_once(ax, label_text)
label = '';
kids = findobj(ax, '-property', 'DisplayName');
names = get(kids, 'DisplayName');
if ischar(names)
    names = {names};
end
if ~iscell(names) || ~any(strcmp(names, label_text))
    label = label_text;
end
end

function trial_data = load_trial_tables(mode_path, trial_name)
trial_data = struct();
read_tbl = @(folder) load_table(fullfile(mode_path, folder), trial_name);
trial_data.conditions = read_tbl('conditions');
trial_data.ik_offset = read_tbl('ik_offset');
trial_data.id = read_tbl('id');
trial_data.gcRight = read_tbl('gcRight');
trial_data.gcLeft = read_tbl('gcLeft');
trial_data.fp = read_tbl('fp');
trial_data.markers = read_tbl('markers');
end

function tbl = load_table(folder, trial_name)
tbl = [];
f = fullfile(folder, trial_name);
if ~exist(f, 'file')
    return;
end
tmp = load(f);
if isfield(tmp, 'data') && istable(tmp.data)
    tbl = tmp.data;
elseif istable(tmp)
    tbl = tmp;
end
end

function stride_data = collect_strides(trial_data, leg_side, subject_mass, NUM_POINTS, mode)
stride_data = [];
gc = select_gc(trial_data, leg_side);
if isempty(gc) || ~isfield(trial_data, 'ik_offset') || ~istable(trial_data.ik_offset)
    return;
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
    sd = gtech_compute_grf_cop_stride(trial_data, stride_time, stride_pct, leg_side, subject_mass, NUM_POINTS, mode);
    if isempty(sd)
        continue;
    end
    stride_data = [stride_data; sd]; %#ok<AGROW>
end
end

function gc = select_gc(trial_data, leg_side)
if strcmpi(leg_side, 'right')
    gc = trial_data.gcRight;
else
    gc = trial_data.gcLeft;
end
end

function val = interp_named(tbl, varname, mask, target_times, default_val, method)
if nargin < 5
    default_val = 0;
end
if nargin < 6
    method = 'linear';
end
if isempty(tbl) || ~istable(tbl) || ~any(strcmp(tbl.Properties.VariableNames, varname))
    if isnumeric(default_val)
        val = default_val * ones(numel(target_times), 1);
    else
        val = nan(numel(target_times), 1);
    end
    return;
end
if isempty(mask)
    src_time = tbl.Header;
    src_val = tbl.(varname);
else
    src_time = tbl.Header(mask);
    src_val = tbl.(varname)(mask);
end
val = interp1(src_time, src_val, target_times, method, default_val)';
end

function M = reshape_parquet_stride(vec, stride_len)
vec = vec(:);
n = numel(vec);
remk = mod(n, stride_len);
if remk ~= 0
    error('Length %d not divisible by stride length %d', n, stride_len);
end
q = n / stride_len;
M = reshape(vec, stride_len, q);
end


function summarize_rmse(raw_rmse, parquet_rmse)
if ~isempty(raw_rmse)
    raw_rmse = raw_rmse(~isnan(raw_rmse));
end
if ~isempty(parquet_rmse)
    parquet_rmse = parquet_rmse(~isnan(parquet_rmse));
end

if isempty(raw_rmse) && isempty(parquet_rmse)
    fprintf('No RMSE data available.\n');
    return;
end

if ~isempty(raw_rmse)
    fprintf('Raw recompute RMSE (Nm/kg): n=%d, mean=%.3f, median=%.3f, p90=%.3f\n', ...
        numel(raw_rmse), mean(raw_rmse), median(raw_rmse), prctile(raw_rmse, 90));
end
if ~isempty(parquet_rmse)
    fprintf('Parquet RMSE (Nm/kg): n=%d, mean=%.3f, median=%.3f, p90=%.3f\n', ...
        numel(parquet_rmse), mean(parquet_rmse), median(parquet_rmse), prctile(parquet_rmse, 90));
end
if ~isempty(raw_rmse) && ~isempty(parquet_rmse)
    fprintf('RMSE delta (parquet - raw): mean=%.3f\n', mean(parquet_rmse) - mean(raw_rmse));
end
end

function rmse_parquet = plot_from_parquet(parquet_path, max_strides)
cols = {...
    'phase_ipsi', ...
    'ankle_dorsiflexion_moment_ipsi_Nm_kg', ...
    'grf_vertical_ipsi_BW', ...
    'grf_anterior_ipsi_BW', ...
    'grf_lateral_ipsi_BW', ...
    'cop_anterior_ipsi_m', ...
    'cop_vertical_ipsi_m', ...
    'cop_lateral_ipsi_m', ...
    'foot_sagittal_angle_ipsi_rad', ...
    'subject', 'task', 'task_info'};
fprintf('  Loading parquet columns from %s\n', parquet_path);
parquet_data = parquetread(parquet_path, 'SelectedVariableNames', cols);
STRIDE_LENGTH = 150;

phase = reshape_parquet_stride(parquet_data.phase_ipsi, STRIDE_LENGTH);
ankle_id = reshape_parquet_stride(parquet_data.ankle_dorsiflexion_moment_ipsi_Nm_kg, STRIDE_LENGTH);
vgrf = reshape_parquet_stride(parquet_data.grf_vertical_ipsi_BW, STRIDE_LENGTH);
sgrf = reshape_parquet_stride(parquet_data.grf_anterior_ipsi_BW, STRIDE_LENGTH);
lgrf = reshape_parquet_stride(parquet_data.grf_lateral_ipsi_BW, STRIDE_LENGTH);
cop_ant = reshape_parquet_stride(parquet_data.cop_anterior_ipsi_m, STRIDE_LENGTH);
cop_vert = reshape_parquet_stride(parquet_data.cop_vertical_ipsi_m, STRIDE_LENGTH);
cop_lat = reshape_parquet_stride(parquet_data.cop_lateral_ipsi_m, STRIDE_LENGTH);
foot_angle = reshape_parquet_stride(parquet_data.foot_sagittal_angle_ipsi_rad, STRIDE_LENGTH);

n_strides = size(phase, 2);
fprintf('  Parquet contains %d strides (ipsilateral)\n', n_strides);

ankle_torque_est_no_shear = (-cop_ant .* vgrf) * 9.81;
ankle_torque_est = (-cop_ant .* vgrf + cop_vert .* sgrf) * 9.81;
rmse_parquet = sqrt(mean((ankle_torque_est - ankle_id).^2, 1, 'omitnan'))';

% Select strides to plot: focus on outliers with largest RMSE
if ~isfinite(max_strides) || max_strides <= 0
    max_strides = n_strides;
end
RMSE_THRESH = 0.25;  % Nm/kg, consider anything above as an outlier
outlier_idx = find(rmse_parquet > RMSE_THRESH);
if ~isempty(outlier_idx)
    [~, order] = sort(rmse_parquet(outlier_idx), 'descend');
    stride_idx = outlier_idx(order(1:min(max_strides, numel(order))));
    fprintf('  Plotting %d outlier strides (RMSE > %.3f Nm/kg, max=%.3f)\n', ...
        numel(stride_idx), RMSE_THRESH, max(rmse_parquet));
else
    [~, order] = sort(rmse_parquet, 'descend');
    stride_idx = order(1:min(max_strides, n_strides));
    fprintf('  No RMSE outliers above %.3f; plotting %d worst strides (max=%.3f Nm/kg)\n', ...
        RMSE_THRESH, numel(stride_idx), max(rmse_parquet));
end

fig = figure('Visible', 'off', 'Position', [100, 100, 900, 1100]);
ax1 = subplot(4,1,1); hold on;
ax2 = subplot(4,1,2); hold on;
ax3 = subplot(4,1,3); hold on;
ax4 = subplot(4,1,4); hold on;

for k = 1:numel(stride_idx)
    idx = stride_idx(k);
    if mod(k, 500) == 0
        fprintf('    Plotting/parquet torque for stride %d/%d\n', k, numel(stride_idx));
    end
    p = phase(:, idx);
    plot(ax1, p, ankle_id(:, idx), 'Color', [0 0 1 0.35], 'DisplayName', label_once(ax1, 'Measured Ankle Torque'));
    plot(ax1, p, ankle_torque_est_no_shear(:, idx), ':', 'Color', [0 0.6 0 0.35], 'DisplayName', label_once(ax1, 'Estimated Ankle Torque (No Shear)'));
    plot(ax1, p, ankle_torque_est(:, idx), '--', 'Color', [1 0.6 0 0.35], 'DisplayName', label_once(ax1, 'Estimated Ankle Torque'));
    
    plot(ax2, p, vgrf(:, idx), 'Color', [0 0.6 0 0.35], 'DisplayName', label_once(ax2, 'Vertical GRF (BW)'));
    plot(ax2, p, sgrf(:, idx), 'Color', [0.8 0 0 0.35], 'DisplayName', label_once(ax2, 'Shear GRF (BW)'));
    plot(ax2, p, lgrf(:, idx), 'Color', [0 0 0.8 0.35], 'DisplayName', label_once(ax2, 'Lateral GRF (BW)'));
    
    plot(ax3, p, cop_ant(:, idx), 'Color', [0.5 0 0.5 0.35], 'DisplayName', label_once(ax3, 'CoP Anterior (m)'));
    plot(ax3, p, cop_vert(:, idx), 'Color', [0.6 0.3 0.1 0.35], 'DisplayName', label_once(ax3, 'CoP Vertical (m)'));
    plot(ax3, p, cop_lat(:, idx), 'Color', [0.8 0.4 0.8 0.35], 'DisplayName', label_once(ax3, 'CoP Lateral (m)'));
    
    plot(ax4, p, foot_angle(:, idx) * 180/pi, 'Color', [0 0.8 0.8 0.35], 'DisplayName', label_once(ax4, 'Foot Angle (deg)'));
end

ax1.Title.String = sprintf('Parquet Torque Check: %s', parquet_path);
ax1.YLabel.String = 'Ankle Torque (Nm/kg)';
legend(ax1, 'Location', 'eastoutside');

ax2.YLabel.String = 'Ground Reaction Force (BW)';
ax2.Title.String = 'Ground Reaction Forces';
plot(ax2, [0 100], [0 0], '--k', 'LineWidth', 0.7);
legend(ax2, 'Location', 'eastoutside');

ax3.YLabel.String = 'Center of Pressure (m)';
ax3.Title.String = 'Center of Pressure Trajectory';
plot(ax3, [0 100], [0 0], '--k', 'LineWidth', 0.7);
legend(ax3, 'Location', 'eastoutside');

ax4.XLabel.String = 'Gait Phase (%)';
ax4.YLabel.String = 'Foot Angle (degrees)';
ax4.Title.String = 'Foot Angle Trajectory';
legend(ax4, 'Location', 'eastoutside');

out_dir = fullfile(fileparts(parquet_path), 'parquet_plots');
if ~exist(out_dir, 'dir'); mkdir(out_dir); end
out_file = fullfile(out_dir, 'ankle_torque_parquet_reference.png');
saveas(fig, out_file);
close(fig);
fprintf('Saved parquet reference plot to %s\\n', out_file);
end

function [vx_var, vy_var, vz_var, px_var, py_var, pz_var] = treadmill_map(leg_side)
if strcmpi(leg_side, 'right')
    vx_var = 'Treadmill_R_vx';
    vy_var = 'Treadmill_R_vy';
    vz_var = 'Treadmill_R_vz';
    px_var = 'Treadmill_R_px';
    py_var = 'Treadmill_R_py';
    pz_var = 'Treadmill_R_pz';
else
    vx_var = 'Treadmill_L_vx';
    vy_var = 'Treadmill_L_vy';
    vz_var = 'Treadmill_L_vz';
    px_var = 'Treadmill_L_px';
    py_var = 'Treadmill_L_py';
    pz_var = 'Treadmill_L_pz';
end
end

function [vx_var, vy_var, vz_var, px_var, py_var, pz_var] = select_fp_vars(fp_tbl, stride_time, leg_side, mode)
vx_var = '';
vy_var = '';
vz_var = '';
px_var = '';
py_var = '';
pz_var = '';
if isempty(fp_tbl) || ~istable(fp_tbl) || ~any(strcmp(fp_tbl.Properties.VariableNames, 'Header'))
    return;
end

if strcmpi(mode, 'treadmill')
    [vx_var, vy_var, vz_var, px_var, py_var, pz_var] = treadmill_map(leg_side);
    return;
end

% Non-treadmill: choose force plate with largest |vy| near HS+200 ms (fallback: max |vy|)
available = {};
for fp = fp_tbl.Properties.VariableNames
    name = fp{1};
    if endsWith(name, '_vy')
        available{end+1} = erase(name, '_vy'); %#ok<AGROW>
    end
end
if isempty(available)
    return;
end

fp_time = fp_tbl.Header;
hs_time = stride_time(1);
check_time = hs_time + 0.2;
check_idx = find(fp_time >= check_time, 1, 'first');

best_fp = '';
best_force = 0;
for i = 1:numel(available)
    vy_name = [available{i} '_vy'];
    if ~any(strcmp(fp_tbl.Properties.VariableNames, vy_name))
        continue;
    end
    vy_data = fp_tbl.(vy_name);
    if ~isempty(check_idx)
        force_val = abs(vy_data(check_idx));
    else
        force_val = max(abs(vy_data));
    end
    if force_val > best_force
        best_force = force_val;
        best_fp = available{i};
    end
end

if isempty(best_fp) || best_force < 50  % low force -> likely no contact
    return;
end
vx_var = [best_fp '_vx'];
vy_var = [best_fp '_vy'];
vz_var = [best_fp '_vz'];
px_var = [best_fp '_px'];
py_var = [best_fp '_py'];
pz_var = [best_fp '_pz'];
end

function [lat, vert, ant] = ankle_marker(markers, stride_time, target_times, leg_side)
lat = zeros(numel(target_times), 1);
vert = zeros(numel(target_times), 1);
ant = zeros(numel(target_times), 1);
if isempty(markers) || ~istable(markers) || ~any(strcmp(markers.Properties.VariableNames, 'Header'))
    return;
end
mask = (markers.Header >= stride_time(1)) & (markers.Header <= stride_time(end));
if sum(mask) < 2
    return;
end
if strcmpi(leg_side, 'right')
    x_col = 'R_Ankle_Lat_x';
    y_col = 'R_Ankle_Lat_y';
    z_col = 'R_Ankle_Lat_z';
else
    x_col = 'L_Ankle_Lat_x';
    y_col = 'L_Ankle_Lat_y';
    z_col = 'L_Ankle_Lat_z';
end
vars = markers.Properties.VariableNames;
if ~all(ismember({x_col, y_col, z_col}, vars))
    return;
end
t_src = markers.Header(mask);
lat = interp1(t_src, markers.(x_col)(mask), target_times, 'linear', 'extrap')'/1000;
vert = interp1(t_src, markers.(y_col)(mask), target_times, 'linear', 'extrap')'/1000;
ant = interp1(t_src, markers.(z_col)(mask), target_times, 'linear', 'extrap')'/1000;
end

function rmse_best = plot_stride_set(stride_data, max_strides, title_suffix, out_dir, out_name)
num_strides = numel(stride_data);
take = min(num_strides, max_strides);
phase = cat(2, stride_data.phase);
ankle_id = cat(2, stride_data.ankle_moment_Nm_kg);
grf_v = cat(2, stride_data.vertical_grf_BW);
grf_a = cat(2, stride_data.anterior_grf_BW);
grf_l = cat(2, stride_data.lateral_grf_BW);
cop_ant = cat(2, stride_data.cop_ant_m);
cop_vert = cat(2, stride_data.cop_vert_m);
cop_lat = cat(2, stride_data.cop_lat_m);
foot_angle = cat(2, stride_data.foot_angle_rad);

ankle_torque_est_no_shear = (-cop_ant .* grf_v) * 9.81;
ankle_torque_est = (-cop_ant .* grf_v + cop_vert .* grf_a) * 9.81;

% Search over sign flips for anterior COP and shear GRF to minimize RMSE vs. ID
best_est = zeros(size(ankle_torque_est));
best_mult = ones(2, take);  % [cop_ant_sign; shear_grf_sign]
best_cop_ant = cop_ant;
best_shear = grf_a;
flip_opts = [1, -1];
for idx = 1:take
    best_rmse = inf;
    for sa = flip_opts
        for sg = flip_opts
            est_candidate = (-(sa * cop_ant(:, idx)) .* grf_v(:, idx) + cop_vert(:, idx) .* (sg * grf_a(:, idx))) * 9.81;
            diff = est_candidate - ankle_id(:, idx);
            rmse = sqrt(mean(diff.^2, 'omitnan'));
            if rmse < best_rmse
                best_rmse = rmse;
                best_est(:, idx) = est_candidate;
                best_mult(:, idx) = [sa; sg];
                best_cop_ant(:, idx) = sa * cop_ant(:, idx);
                best_shear(:, idx) = sg * grf_a(:, idx);
            end
        end
    end
end

flipped = find(any(best_mult ~= 1, 1));
if ~isempty(flipped)
    fprintf('  Detected sign improvements (cop_ant or shear_grf) on %d/%d strides (showing first 5):\n', numel(flipped), take);
    for k = 1:min(5, numel(flipped))
        idx = flipped(k);
        fprintf('    stride %d: cop_ant x%.0f, shear_grf x%.0f\n', idx, best_mult(1, idx), best_mult(2, idx));
    end
end

fig = figure('Visible', 'off', 'Position', [100, 100, 900, 1100]);
ax1 = subplot(4, 1, 1); hold on;
ax2 = subplot(4, 1, 2); hold on;
ax3 = subplot(4, 1, 3); hold on;
ax4 = subplot(4, 1, 4); hold on;

for idx = 1:take
    p = phase(:, idx);
    plot(ax1, p, ankle_id(:, idx), 'Color', [0 0 1 0.4], 'DisplayName', label_once(ax1, 'Measured Ankle Torque'));
    plot(ax1, p, ankle_torque_est_no_shear(:, idx), ':', 'Color', [0 0.6 0 0.4], 'DisplayName', label_once(ax1, 'Estimated Ankle Torque (No Shear)'));
    plot(ax1, p, ankle_torque_est(:, idx), '--', 'Color', [1 0.6 0 0.4], 'DisplayName', label_once(ax1, 'Estimated Ankle Torque'));
    plot(ax1, p, best_est(:, idx), '-', 'Color', [0.6 0 0.9 0.35], 'LineWidth', 1.1, 'DisplayName', label_once(ax1, 'Best (COP sign search)'));
    
    plot(ax2, p, grf_v(:, idx), 'Color', [0 0.6 0 0.4], 'DisplayName', label_once(ax2, 'Vertical GRF (BW)'));
    plot(ax2, p, grf_a(:, idx), 'Color', [0.8 0 0 0.4], 'DisplayName', label_once(ax2, 'Shear GRF (BW)'));
    plot(ax2, p, grf_l(:, idx), 'Color', [0 0 0.8 0.4], 'DisplayName', label_once(ax2, 'Lateral GRF (BW)'));
    plot(ax2, p, best_shear(:, idx), '--', 'Color', [0.6 0 0.6 0.5], 'DisplayName', label_once(ax2, 'Shear GRF (best sign)'));
    
    plot(ax3, p, cop_ant(:, idx), 'Color', [0.5 0 0.5 0.4], 'DisplayName', label_once(ax3, 'CoP Anterior (m)'));
    plot(ax3, p, cop_vert(:, idx), 'Color', [0.6 0.3 0.1 0.4], 'DisplayName', label_once(ax3, 'CoP Vertical (m)'));
    plot(ax3, p, cop_lat(:, idx), 'Color', [0.8 0.4 0.8 0.4], 'DisplayName', label_once(ax3, 'CoP Lateral (m)'));
    plot(ax3, p, best_cop_ant(:, idx), '--', 'Color', [0.4 0 0.7 0.6], 'DisplayName', label_once(ax3, 'CoP Anterior (best sign)'));
    
    plot(ax4, p, foot_angle(:, idx) * 180/pi, 'Color', [0 0.8 0.8 0.4], 'DisplayName', label_once(ax4, 'Foot Angle (deg)'));
end

ax1.XLabel.String = 'Gait Phase (%)';
ax1.YLabel.String = 'Ankle Torque (Nm/kg)';
ax1.Title.String = sprintf('Measured vs Estimated Ankle Torque - %s', title_suffix);
legend(ax1, 'Location', 'eastoutside');

ax2.XLabel.String = 'Gait Phase (%)';
ax2.YLabel.String = 'Ground Reaction Force (BW)';
ax2.Title.String = 'Ground Reaction Forces';
plot(ax2, [0 100], [0 0], '--k', 'LineWidth', 0.7);
legend(ax2, 'Location', 'eastoutside');

ax3.XLabel.String = 'Gait Phase (%)';
ax3.YLabel.String = 'Center of Pressure (m)';
ax3.Title.String = 'Center of Pressure Trajectory';
plot(ax3, [0 100], [0 0], '--k', 'LineWidth', 0.7);
legend(ax3, 'Location', 'eastoutside');

ax4.XLabel.String = 'Gait Phase (%)';
ax4.YLabel.String = 'Foot Angle (degrees)';
ax4.Title.String = 'Foot Angle Trajectory';
legend(ax4, 'Location', 'eastoutside');

rmse_best = sqrt(mean((best_est - ankle_id).^2, 1, 'omitnan'))';

if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end
saveas(fig, fullfile(out_dir, out_name));
close(fig);
end
