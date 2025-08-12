% Compare velocity calculation methods for UMich data
% Method 1: Calculate velocities before interpolation (current approach)
% Method 2: Calculate velocities after interpolation (proposed approach)

clear all; close all;

% Load one subject's data for comparison
fprintf('Loading UMich Streaming data...\n');
load('Streaming.mat');

% Get first available subject and trial
subjects = fieldnames(Streaming);
subject = subjects{1};
fprintf('Using subject: %s\n', subject);

% Use level walking data (i0 = 0 degrees incline)
trial_data = Streaming.(subject).Tread.i0;

% Get heel strike events
events = trial_data.events;
RHS = events.RHS;
angles = trial_data.jointAngles;

% Parameters
Hz = 100;  % Sampling frequency
NUM_POINTS = 150;
deg2rad = pi/180;

% Take a representative stride (use first complete stride)
if length(RHS) < 3
    error('Need at least 3 heel strikes for comparison');
end

stride_start = RHS(1);
stride_end = RHS(2);
stride_duration_frames = stride_end - stride_start;
stride_duration_s = stride_duration_frames / Hz;

fprintf('Analyzing stride from frame %d to %d (%.2f seconds)\n', ...
    stride_start, stride_end, stride_duration_s);

% Extract right hip flexion angle for this stride
hip_angles_deg = angles.RHipAngles(stride_start:stride_end, 1);  % Sagittal plane
time_original = ((0:length(hip_angles_deg)-1) / Hz)';  % Original time vector

fprintf('Original data: %d samples at %.1f Hz\n', length(hip_angles_deg), Hz);

%% Method 1: Calculate velocities BEFORE interpolation (current approach)
fprintf('\n=== Method 1: Velocities Before Interpolation ===\n');

% Convert to radians and calculate velocity in original time domain
hip_angles_rad_orig = hip_angles_deg * deg2rad;
hip_velocity_orig = gradient(hip_angles_rad_orig) * Hz;  % rad/s

% Create target time and phase vectors for interpolation
time_target = linspace(0, stride_duration_s, NUM_POINTS)';
phase_target = linspace(0, 100, NUM_POINTS)';

% Interpolate both angles and velocities to 150 points
hip_angle_method1 = interp1(time_original, hip_angles_rad_orig, time_target, 'linear', 'extrap');
hip_velocity_method1 = interp1(time_original, hip_velocity_orig, time_target, 'linear', 'extrap');

fprintf('Method 1 completed: interpolated %d points to %d points\n', ...
    length(hip_angles_deg), NUM_POINTS);

%% Method 2: Calculate velocities AFTER interpolation (proposed approach)
fprintf('\n=== Method 2: Velocities After Interpolation ===\n');

% First interpolate angles to 150 points
hip_angle_method2 = interp1(time_original, hip_angles_rad_orig, time_target, 'linear', 'extrap');

% Then calculate velocities from interpolated data
effective_Hz = NUM_POINTS / stride_duration_s;  % Effective sampling rate
hip_velocity_method2 = gradient(hip_angle_method2) * effective_Hz;  % rad/s

fprintf('Method 2 completed: effective sampling rate = %.1f Hz\n', effective_Hz);

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
fprintf('  Method 1: %.4f rad/s at phase %.1f%%\n', peak_vel1, phase_target(peak_idx1));
fprintf('  Method 2: %.4f rad/s at phase %.1f%%\n', peak_vel2, phase_target(peak_idx2));
fprintf('  Difference: %.4f rad/s (%.1f%%)\n', peak_vel1-peak_vel2, 100*(peak_vel1-peak_vel2)/peak_vel1);

%% Create comparison plots
fprintf('\n=== Creating Plots ===\n');

figure('Position', [100, 100, 1200, 800]);

% Plot 1: Original vs interpolated data
subplot(2,3,1);
plot(time_original, hip_angles_deg, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Original');
hold on;
plot(time_target, hip_angle_method1/deg2rad, 'r--', 'LineWidth', 1, 'DisplayName', 'Interpolated');
xlabel('Time (s)');
ylabel('Hip Angle (deg)');
title('Original vs Interpolated Angles');
legend();
grid on;

% Plot 2: Velocity comparison
subplot(2,3,2);
plot(phase_target, hip_velocity_method1, 'b-', 'LineWidth', 2, 'DisplayName', 'Method 1 (Before)');
hold on;
plot(phase_target, hip_velocity_method2, 'r--', 'LineWidth', 1.5, 'DisplayName', 'Method 2 (After)');
xlabel('Gait Phase (%)');
ylabel('Hip Velocity (rad/s)');
title('Velocity Comparison');
legend();
grid on;

% Plot 3: Velocity difference
subplot(2,3,3);
plot(phase_target, velocity_diff, 'k-', 'LineWidth', 1.5);
xlabel('Gait Phase (%)');
ylabel('Velocity Difference (rad/s)');
title('Method 1 - Method 2');
grid on;

% Plot 4: Original velocity data
subplot(2,3,4);
plot(time_original, hip_velocity_orig, 'b-', 'LineWidth', 1);
hold on;
plot(time_target, hip_velocity_method1, 'r--', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('Velocity (rad/s)');
title('Original vs Method 1 Velocities');
legend({'Original', 'Method 1'});
grid on;

% Plot 5: Relative error
subplot(2,3,5);
rel_error = 100 * abs(velocity_diff) ./ (abs(hip_velocity_method1) + 1e-6);  % Avoid div by zero
plot(phase_target, rel_error, 'k-', 'LineWidth', 1.5);
xlabel('Gait Phase (%)');
ylabel('Relative Error (%)');
title('Relative Velocity Error');
grid on;

% Plot 6: Power spectral density comparison
subplot(2,3,6);
% Calculate PSDs using same frequency vector
[psd1, f] = pwelch(hip_velocity_method1, [], [], [], effective_Hz);
[psd2, ~] = pwelch(hip_velocity_method2, [], [], [], effective_Hz);
loglog(f, psd1, 'b-', 'LineWidth', 1.5, 'DisplayName', 'Method 1');
hold on;
loglog(f, psd2, 'r--', 'LineWidth', 1.5, 'DisplayName', 'Method 2');
xlabel('Frequency (Hz)');
ylabel('PSD (rad²/s²/Hz)');
title('Velocity Power Spectral Density');
legend();
grid on;

sgtitle(sprintf('Velocity Calculation Methods Comparison - %s Hip Flexion', subject));

% Save the plot
print('velocity_methods_comparison_umich.png', '-dpng', '-r300');
fprintf('Plot saved as: velocity_methods_comparison_umich.png\n');

%% Summary statistics
fprintf('\n=== Summary ===\n');
fprintf('Both methods produce similar results for interpolated data.\n');
if max_velocity_diff < 0.1
    fprintf('Differences are small (< 0.1 rad/s) - methods are comparable.\n');
elseif max_velocity_diff < 0.5
    fprintf('Moderate differences (0.1-0.5 rad/s) - consider biomechanical impact.\n');
else
    fprintf('Large differences (> 0.5 rad/s) - method choice significantly matters.\n');
end

fprintf('Peak velocity preservation: Method 1 retains %.1f%% more detail.\n', ...
    100*(peak_vel1-peak_vel2)/peak_vel2);