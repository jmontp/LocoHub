% Compare velocity calculation methods for Gtech data  
% Method 1: Calculate velocities before interpolation (current approach)
% Method 2: Calculate velocities after interpolation (proposed approach)

clear all; close all;

% Add utilities to path
addpath('utilities');

% Configuration
DATA_ROOT = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
NUM_POINTS = 150;
deg2rad = pi/180;

% Load a test subject and trial
subject = 'AB06';
date_folder = '10_09_18';
trial_name = 'levelground_ccw_fast_01_01.mat';

fprintf('Loading Gtech data for %s...\n', subject);

% Load trial data
trial_path = fullfile(DATA_ROOT, subject, date_folder, 'levelground');
ik_file = fullfile(trial_path, 'ik_offset', trial_name);
gc_file = fullfile(trial_path, 'gcRight', trial_name);

if ~exist(ik_file, 'file') || ~exist(gc_file, 'file')
    error('Required data files not found');
end

% Load IK and gait cycle data
ik_data = load(ik_file);
gc_data = load(gc_file);

fprintf('Loaded IK data with %d samples\n', height(ik_data.data));
fprintf('Loaded GC data with %d samples\n', height(gc_data.data));

% Extract a single stride using heel strike detection
heel_strike_pct = gc_data.data.HeelStrike;
gc_time = gc_data.data.Header;

% Find heel strikes (where percentage drops to 0)
hs_indices = find(diff([1; heel_strike_pct == 0]) == 1);

if length(hs_indices) < 2
    error('Need at least 2 heel strikes for comparison');
end

% Take first complete stride
stride_start_idx = hs_indices(1);
stride_end_idx = hs_indices(2) - 1;

% Get time bounds
stride_start_time = gc_time(stride_start_idx);
stride_end_time = gc_time(stride_end_idx);
stride_duration_s = stride_end_time - stride_start_time;

fprintf('Analyzing stride from %.3f to %.3f seconds (%.3f s duration)\n', ...
    stride_start_time, stride_end_time, stride_duration_s);

% Extract IK data for this time window
ik_time = ik_data.data.Header;
ik_mask = (ik_time >= stride_start_time) & (ik_time <= stride_end_time);
ik_indices = find(ik_mask);

if sum(ik_mask) < 10
    error('Insufficient IK data points in stride');
end

% Extract hip flexion angle data
hip_angles_deg = ik_data.data.hip_flexion_r(ik_mask);
ik_time_stride = ik_time(ik_mask);

% Create relative time vector
time_original = ik_time_stride - ik_time_stride(1);  % Start from 0

fprintf('Original IK data: %d samples over %.3f seconds\n', ...
    length(hip_angles_deg), stride_duration_s);

% Get gait cycle percentages for this stride
stride_pct = heel_strike_pct(stride_start_idx:stride_end_idx);
stride_gc_time = gc_time(stride_start_idx:stride_end_idx);

% Find valid percentage data (> 0)
valid_pct_idx = find(stride_pct > 0, 1, 'first');
if isempty(valid_pct_idx)
    error('No valid gait cycle percentages found');
end

valid_stride_pct = stride_pct(valid_pct_idx:end);
valid_stride_time = stride_gc_time(valid_pct_idx:end) - stride_start_time;

%% Method 1: Calculate velocities BEFORE interpolation (current approach)
fprintf('\n=== Method 1: Velocities Before Interpolation ===\n');

% Convert to radians and calculate velocity in original time domain
hip_angles_rad_orig = hip_angles_deg * deg2rad;
hip_velocity_orig = gradient(hip_angles_rad_orig) ./ gradient(time_original);  % rad/s

% Create target percentage and time vectors
target_pct = linspace(0, 100, NUM_POINTS)';

% Interpolate angle data to stride time points first
angle_at_stride_time = interp1(time_original, hip_angles_deg, valid_stride_time, 'linear', 'extrap');
% Then interpolate from percentage to normalized 150 points  
hip_angle_method1 = interp1(valid_stride_pct, angle_at_stride_time, target_pct, 'linear', 'extrap') * deg2rad;

% Interpolate velocity data similarly
velocity_at_stride_time = interp1(time_original, hip_velocity_orig, valid_stride_time, 'linear', 'extrap');
hip_velocity_method1 = interp1(valid_stride_pct, velocity_at_stride_time, target_pct, 'linear', 'extrap');

fprintf('Method 1 completed: %d samples -> %d points via gait cycle percentages\n', ...
    length(hip_angles_deg), NUM_POINTS);

%% Method 2: Calculate velocities AFTER interpolation (proposed approach)
fprintf('\n=== Method 2: Velocities After Interpolation ===\n');

% First interpolate angles using same method as Method 1
hip_angle_method2 = interp1(valid_stride_pct, angle_at_stride_time, target_pct, 'linear', 'extrap') * deg2rad;

% Then calculate velocities from interpolated data
% Use phase derivative: dθ/dt = (dθ/dφ) * (dφ/dt)
% where φ is gait phase and dφ/dt = 100/stride_duration
phase_rate = 100 / stride_duration_s;  % %/s
hip_velocity_method2 = gradient(hip_angle_method2) ./ gradient(target_pct) * phase_rate;  % rad/s

fprintf('Method 2 completed: phase rate = %.2f %%/s\n', phase_rate);

%% Compare the results
fprintf('\n=== Comparison Results ===\n');

% Angles should be identical
angle_diff = hip_angle_method1 - hip_angle_method2;
max_angle_diff = max(abs(angle_diff));
fprintf('Maximum angle difference: %.8f rad (%.6f deg)\n', ...
    max_angle_diff, max_angle_diff/deg2rad);

% Velocity differences
velocity_diff = hip_velocity_method1 - hip_velocity_method2;
max_velocity_diff = max(abs(velocity_diff));
mean_velocity_diff = mean(abs(velocity_diff));
rms_velocity_diff = sqrt(mean(velocity_diff.^2));

fprintf('Velocity differences:\n');
fprintf('  Maximum: %.4f rad/s\n', max_velocity_diff);
fprintf('  Mean absolute: %.4f rad/s\n', mean_velocity_diff);
fprintf('  RMS: %.4f rad/s\n', rms_velocity_diff);

% Peak velocity comparison
[peak_vel1, peak_idx1] = max(abs(hip_velocity_method1));
[peak_vel2, peak_idx2] = max(abs(hip_velocity_method2));
fprintf('Peak velocities:\n');
fprintf('  Method 1: %.4f rad/s at phase %.1f%%\n', peak_vel1, target_pct(peak_idx1));
fprintf('  Method 2: %.4f rad/s at phase %.1f%%\n', peak_vel2, target_pct(peak_idx2));
fprintf('  Difference: %.4f rad/s (%.1f%%)\n', peak_vel1-peak_vel2, 100*(peak_vel1-peak_vel2)/peak_vel1);

% Correlation analysis
corr_coef = corrcoef(hip_velocity_method1, hip_velocity_method2);
fprintf('Correlation coefficient: %.4f\n', corr_coef(1,2));

%% Create comparison plots
fprintf('\n=== Creating Plots ===\n');

figure('Position', [100, 100, 1200, 800]);

% Plot 1: Original vs interpolated angles
subplot(2,3,1);
plot(time_original, hip_angles_deg, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Original IK');
hold on;
plot(valid_stride_time, angle_at_stride_time, 'g--', 'LineWidth', 1, 'DisplayName', 'At GC time');
xlabel('Time (s)');
ylabel('Hip Angle (deg)');
title('Original vs Stride-Aligned Angles');
legend();
grid on;

% Plot 2: Velocity comparison
subplot(2,3,2);
plot(target_pct, hip_velocity_method1, 'b-', 'LineWidth', 2, 'DisplayName', 'Method 1 (Before)');
hold on;
plot(target_pct, hip_velocity_method2, 'r--', 'LineWidth', 1.5, 'DisplayName', 'Method 2 (After)');
xlabel('Gait Phase (%)');
ylabel('Hip Velocity (rad/s)');
title('Velocity Comparison');
legend();
grid on;

% Plot 3: Velocity difference
subplot(2,3,3);
plot(target_pct, velocity_diff, 'k-', 'LineWidth', 1.5);
xlabel('Gait Phase (%)');
ylabel('Velocity Difference (rad/s)');
title('Method 1 - Method 2');
grid on;

% Plot 4: Original velocity data
subplot(2,3,4);
plot(time_original, hip_velocity_orig, 'b-', 'LineWidth', 1);
hold on;
plot(valid_stride_time, velocity_at_stride_time, 'g--', 'LineWidth', 1);
xlabel('Time (s)');
ylabel('Velocity (rad/s)');
title('Original Velocity Data');
legend({'From IK time', 'At GC time'});
grid on;

% Plot 5: Relative error
subplot(2,3,5);
rel_error = 100 * abs(velocity_diff) ./ (abs(hip_velocity_method1) + 1e-6);
plot(target_pct, rel_error, 'k-', 'LineWidth', 1.5);
xlabel('Gait Phase (%)');
ylabel('Relative Error (%)');
title('Relative Velocity Error');
grid on;

% Plot 6: Scatter plot correlation
subplot(2,3,6);
scatter(hip_velocity_method1, hip_velocity_method2, 30, target_pct, 'filled');
hold on;
plot([-2 2], [-2 2], 'k--', 'LineWidth', 1);  % Unity line
xlabel('Method 1 Velocity (rad/s)');
ylabel('Method 2 Velocity (rad/s)');
title(sprintf('Correlation (r=%.3f)', corr_coef(1,2)));
colorbar;
colormap(parula);
grid on;
axis equal;

sgtitle(sprintf('Velocity Methods Comparison - Gtech %s Hip Flexion', subject));

% Save the plot
print('velocity_methods_comparison_gtech.png', '-dpng', '-r300');
fprintf('Plot saved as: velocity_methods_comparison_gtech.png\n');

%% Additional analysis: Frequency content
fprintf('\n=== Frequency Analysis ===\n');

% Estimate effective sampling rates
dt_method1 = stride_duration_s / NUM_POINTS;
fs_effective = 1 / dt_method1;

fprintf('Effective sampling rate: %.2f Hz\n', fs_effective);
fprintf('Nyquist frequency: %.2f Hz\n', fs_effective/2);

% Check for aliasing concerns
original_dt = mean(diff(time_original));
original_fs = 1 / original_dt;
fprintf('Original sampling rate: %.2f Hz\n', original_fs);

if fs_effective < original_fs/2
    fprintf('WARNING: Effective sampling rate may cause aliasing!\n');
end

%% Summary statistics
fprintf('\n=== Summary ===\n');
fprintf('Gait cycle approach introduces additional complexity due to phase mapping.\n');
if max_velocity_diff < 0.1
    fprintf('Differences are small (< 0.1 rad/s) - methods are comparable.\n');
elseif max_velocity_diff < 0.5  
    fprintf('Moderate differences (0.1-0.5 rad/s) - consider biomechanical impact.\n');
else
    fprintf('Large differences (> 0.5 rad/s) - method choice significantly matters.\n');
end

fprintf('Correlation: %.3f (1.0 = perfect correlation)\n', corr_coef(1,2));
fprintf('Peak velocity difference: %.1f%% \n', 100*abs(peak_vel1-peak_vel2)/max(peak_vel1,peak_vel2));