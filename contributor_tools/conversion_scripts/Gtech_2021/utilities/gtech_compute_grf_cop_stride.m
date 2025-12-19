function sd = gtech_compute_grf_cop_stride(trial_data, stride_time, stride_pct, leg_side, subject_mass, NUM_POINTS, mode)
%GTECH_COMPUTE_GRF_COP_STRIDE Canonical GRF/COP + ankle moment pipeline for one stride.
%
% sd = gtech_compute_grf_cop_stride(trial_data, stride_time, stride_pct, ...
%       leg_side, subject_mass, NUM_POINTS, mode)
%
% Inputs
%   trial_data    Struct with fields: ik_offset, id, fp, markers (tables)
%   stride_time   Vector of times (s) for this stride from gc table
%   stride_pct    Vector of gait percentages (0–100) for this stride
%   leg_side      'right' or 'left'
%   subject_mass  Subject mass in kg
%   NUM_POINTS    Number of samples per stride (e.g., 150)
%   mode          String: 'treadmill', 'ramp', 'stair', 'levelground'
%
% Output
%   sd struct with fields:
%     phase                 (NUM_POINTS x 1) gait phase (%)
%     ankle_moment_Nm_kg    (NUM_POINTS x 1) ID ankle moment (Nm/kg)
%     vertical_grf_BW       (NUM_POINTS x 1)
%     anterior_grf_BW       (NUM_POINTS x 1)
%     lateral_grf_BW        (NUM_POINTS x 1)
%     cop_ant_m             (NUM_POINTS x 1) COP anterior (ankle frame, m)
%     cop_vert_m            (NUM_POINTS x 1)
%     cop_lat_m             (NUM_POINTS x 1)
%     foot_angle_rad        (NUM_POINTS x 1) sagittal foot angle
%     best_est              (NUM_POINTS x 1) best-estimated torque (Nm/kg)
%     best_rmse             scalar RMSE vs ID (Nm/kg)
%     phase_rate            scalar d(phase)/dt in %/s
%     start_time            stride start time (s)
%     end_time              stride end time (s)

sd = [];

if isempty(stride_time) || numel(stride_time) ~= numel(stride_pct)
    return;
end

% Basic stride quality checks (match validator script)
if numel(stride_pct) < 10 || max(stride_pct) < 50
    return;
end

deg2rad = pi/180;

target_pct = linspace(0, 100, NUM_POINTS)';
target_times = linspace(stride_time(1), stride_time(end), NUM_POINTS);
stride_duration = stride_time(end) - stride_time(1);
if stride_duration <= 0
    return;
end

ik = trial_data.ik_offset;
idt = trial_data.id;
fp = trial_data.fp;
markers = trial_data.markers;

ik_mask = (ik.Header >= stride_time(1)) & (ik.Header <= stride_time(end));
id_mask = (idt.Header >= stride_time(1)) & (idt.Header <= stride_time(end));

% Kinematics for simple foot angle estimate
if strcmpi(leg_side, 'right')
    hip_var = 'hip_flexion_r';
    knee_var = 'knee_angle_r';
    ankle_var = 'ankle_angle_r';
    ankle_id_var = 'ankle_angle_r_moment';
else
    hip_var = 'hip_flexion_l';
    knee_var = 'knee_angle_l';
    ankle_var = 'ankle_angle_l';
    ankle_id_var = 'ankle_angle_l_moment';
end

pelvis = interp_named(ik, 'pelvis_tilt', ik_mask, target_times) * deg2rad;
hip = interp_named(ik, hip_var, ik_mask, target_times) * deg2rad;
knee = -interp_named(ik, knee_var, ik_mask, target_times) * deg2rad;
ankle = interp_named(ik, ankle_var, ik_mask, target_times) * deg2rad;
thigh = pelvis + hip;
shank = thigh - knee;
foot_angle = shank + ankle;

% ID ankle moment (Nm/kg)
moment_raw = interp_named(idt, ankle_id_var, id_mask, stride_time, 'extrap') / subject_mass;
ankle_moment = interp1(stride_pct, moment_raw, target_pct, 'linear', 'extrap');

% GRF / COP in ankle frame
[vx_var, vy_var, vz_var, px_var, py_var, pz_var] = select_fp_vars(fp, stride_time, leg_side, mode);
vx = interp_named(fp, vx_var, [], target_times, NaN);
vy = interp_named(fp, vy_var, [], target_times, NaN);
vz = interp_named(fp, vz_var, [], target_times, NaN);

vertical_grf = vy / (subject_mass * 9.81);
anterior_grf = vz / (subject_mass * 9.81);
lateral_grf = vx / (subject_mass * 9.81);

[ankle_lat, ankle_vert, ankle_ant] = ankle_marker(markers, stride_time, target_times, leg_side);
cop_lat = interp_named(fp, px_var, [], target_times, NaN) - ankle_lat;
cop_vert = interp_named(fp, py_var, [], target_times, NaN) - ankle_vert;
cop_ant = interp_named(fp, pz_var, [], target_times, NaN);
if ~all(isnan(cop_ant))
    cop_ant = -(cop_ant - ankle_ant);
end

% Zero COP where vertical GRF is below contact threshold
contact_threshold_BW = 0.2;
mask_low = vertical_grf < contact_threshold_BW;
cop_ant(mask_low) = 0;
cop_lat(mask_low) = 0;
cop_vert(mask_low) = 0;

% Sign search over anterior COP / shear GRF to best match ID ankle moment
flip_opts = [1, -1];
best_est = zeros(NUM_POINTS, 1);
best_rmse = inf;
best_sa = 1;
best_sg = 1;
for sa = flip_opts
    for sg = flip_opts
        est_candidate = (-(sa * cop_ant) .* vertical_grf + cop_vert .* (sg * anterior_grf)) * 9.81;
        rmse = sqrt(mean((est_candidate - ankle_moment).^2, 'omitnan'));
        if rmse < best_rmse
            best_rmse = rmse;
            best_est = est_candidate;
            best_sa = sa;
            best_sg = sg;
        end
    end
end

% Apply best sign combination to COP anterior and shear GRF so that any
% downstream torque computation using (-cop_ant .* vgrf + cop_vert .* sgrf)
% is already sign-consistent with the ID ankle moment.
cop_ant = best_sa * cop_ant;
anterior_grf = best_sg * anterior_grf;

sd.phase = target_pct;
sd.ankle_moment_Nm_kg = ankle_moment;
sd.vertical_grf_BW = vertical_grf;
sd.anterior_grf_BW = anterior_grf;
sd.lateral_grf_BW = lateral_grf;
sd.cop_ant_m = cop_ant;
sd.cop_vert_m = cop_vert;
sd.cop_lat_m = cop_lat;
sd.foot_angle_rad = foot_angle;
sd.best_est = best_est;
sd.best_rmse = best_rmse;
sd.phase_rate = 100 / stride_duration;
sd.start_time = stride_time(1);
sd.end_time = stride_time(end);

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

function [vx_var, vy_var, vz_var, px_var, py_var, pz_var] = select_fp_vars(fp_tbl, stride_time, leg_side, mode)
vx_var = ''; vy_var = ''; vz_var = '';
px_var = ''; py_var = ''; pz_var = '';
if isempty(fp_tbl) || ~istable(fp_tbl) || ~any(strcmp(fp_tbl.Properties.VariableNames, 'Header'))
    return;
end
if strcmpi(mode, 'treadmill')
    if strcmpi(leg_side, 'right')
        vx_var = 'Treadmill_R_vx'; vy_var = 'Treadmill_R_vy'; vz_var = 'Treadmill_R_vz';
        px_var = 'Treadmill_R_px'; py_var = 'Treadmill_R_py'; pz_var = 'Treadmill_R_pz';
    else
        vx_var = 'Treadmill_L_vx'; vy_var = 'Treadmill_L_vy'; vz_var = 'Treadmill_L_vz';
        px_var = 'Treadmill_L_px'; py_var = 'Treadmill_L_py'; pz_var = 'Treadmill_L_pz';
    end
    return;
end
fp_time = fp_tbl.Header;
hs_time = stride_time(1);
check_time = hs_time + 0.2;
check_idx = find(fp_time >= check_time, 1, 'first');
available = {};
for fp = fp_tbl.Properties.VariableNames
    if endsWith(fp{1}, '_vy')
        available{end+1} = erase(fp{1}, '_vy'); %#ok<AGROW>
    end
end
best_fp = '';
best_force = 0;
for i = 1:numel(available)
    vy_name = [available{i} '_vy'];
    if ~any(strcmp(fp_tbl.Properties.VariableNames, vy_name)), continue; end
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
if isempty(best_fp) || best_force < 50, return; end
vx_var = [best_fp '_vx']; vy_var = [best_fp '_vy']; vz_var = [best_fp '_vz'];
px_var = [best_fp '_px']; py_var = [best_fp '_py']; pz_var = [best_fp '_pz'];
end

function [lat, vert, ant] = ankle_marker(markers, stride_time, target_times, leg_side)
lat = zeros(numel(target_times), 1);
vert = zeros(numel(target_times), 1);
ant = zeros(numel(target_times), 1);
if isempty(markers) || ~istable(markers) || ~any(strcmp(markers.Properties.VariableNames, 'Header'))
    return;
end
mask = (markers.Header >= stride_time(1)) & (markers.Header <= stride_time(end));
if sum(mask) < 2, return; end
if strcmpi(leg_side, 'right')
    x_col = 'R_Ankle_Lat_x'; y_col = 'R_Ankle_Lat_y'; z_col = 'R_Ankle_Lat_z';
else
    x_col = 'L_Ankle_Lat_x'; y_col = 'L_Ankle_Lat_y'; z_col = 'L_Ankle_Lat_z';
end
vars = markers.Properties.VariableNames;
if ~all(ismember({x_col, y_col, z_col}, vars)), return; end
t_src = markers.Header(mask);
lat = interp1(t_src, markers.(x_col)(mask), target_times, 'linear', 'extrap')'/1000;
vert = interp1(t_src, markers.(y_col)(mask), target_times, 'linear', 'extrap')'/1000;
ant = interp1(t_src, markers.(z_col)(mask), target_times, 'linear', 'extrap')'/1000;
end
