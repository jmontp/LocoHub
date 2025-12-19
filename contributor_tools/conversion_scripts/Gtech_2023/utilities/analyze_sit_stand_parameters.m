% Analyze sit-to-stand data to determine appropriate thresholds
% This script examines velocity distributions and transition durations
% to inform parameter selection for segmentation

clear all; close all;

addpath(pwd);

data_root = fullfile('..', 'RawData');
subjects = dir(data_root);
subjects = subjects([subjects.isdir] & ~ismember({subjects.name}, {'.', '..'}));

fprintf('=== Analyzing Sit-to-Stand Parameters ===\n\n');

% Collect all velocities during stable periods and during motion
all_stable_velocities = [];
all_motion_velocities = [];
all_durations_sts = [];  % sit-to-stand durations
all_durations_s2s = [];  % stand-to-sit durations

for s = 1:length(subjects)
    subject = subjects(s).name;
    csv_dir = fullfile(data_root, subject, 'CSV_data');
    if ~exist(csv_dir, 'dir'), continue; end

    activities = dir(csv_dir);
    activities = activities([activities.isdir] & ~ismember({activities.name}, {'.', '..'}));

    for a = 1:length(activities)
        if ~contains(activities(a).name, 'sit_to_stand', 'IgnoreCase', true)
            continue;
        end

        grf_file = fullfile(csv_dir, activities(a).name, 'GroundFrame_GRFs.csv');
        vel_file = fullfile(csv_dir, activities(a).name, 'Joint_Velocities.csv');

        if ~exist(grf_file, 'file') || ~exist(vel_file, 'file')
            continue;
        end

        fprintf('Processing %s / %s\n', subject, activities(a).name);

        % Load data
        grf_data = readtable(grf_file);
        vel_data = readtable(vel_file);

        time_grf = grf_data.time;
        total_vert = grf_data.LForceY_Vertical + grf_data.RForceY_Vertical;

        % Get joint velocities
        vel_cols = {'hip_flexion_velocity_l', 'hip_flexion_velocity_r', ...
                    'knee_velocity_l', 'knee_velocity_r', ...
                    'ankle_velocity_l', 'ankle_velocity_r'};
        present_cols = {};
        for c = 1:length(vel_cols)
            if ismember(vel_cols{c}, vel_data.Properties.VariableNames)
                present_cols{end+1} = vel_cols{c};
            end
        end

        if isempty(present_cols)
            continue;
        end

        % Compute max joint velocity
        vel_matrix = zeros(height(vel_data), length(present_cols));
        for c = 1:length(present_cols)
            vel_matrix(:, c) = abs(vel_data.(present_cols{c}));
        end
        max_joint_vel = max(vel_matrix, [], 2);

        % Classify samples as stable (sitting/standing) or in motion based on GRF
        % Sitting: GRF < 400 N, Standing: GRF > 600 N
        dt = time_grf(2) - time_grf(1);
        sample_rate = 1/dt;

        % Smooth GRF
        smooth_vert = movmean(total_vert, round(0.3 * sample_rate));

        sitting_idx = smooth_vert < 400;
        standing_idx = smooth_vert > 600;
        motion_idx = ~sitting_idx & ~standing_idx;

        % Interpolate velocity to GRF time
        vel_time = vel_data.time;
        max_vel_interp = interp1(vel_time, max_joint_vel, time_grf, 'linear', 'extrap');

        % Collect velocities
        stable_vel = max_vel_interp(sitting_idx | standing_idx);
        motion_vel = max_vel_interp(motion_idx);

        all_stable_velocities = [all_stable_velocities; stable_vel(:)];
        all_motion_velocities = [all_motion_velocities; motion_vel(:)];

        % Run segmentation to get durations (using current parameters)
        [segments, ~, ~] = segment_sit_stand_transitions(grf_file);

        for seg_idx = 1:length(segments)
            if strcmp(segments(seg_idx).type, 'sit_to_stand')
                all_durations_sts = [all_durations_sts; segments(seg_idx).duration];
            else
                all_durations_s2s = [all_durations_s2s; segments(seg_idx).duration];
            end
        end
    end
end

%% Analysis Results
fprintf('\n=== VELOCITY ANALYSIS ===\n');
fprintf('Stable state velocities (sitting/standing):\n');
fprintf('  N samples: %d\n', length(all_stable_velocities));
fprintf('  Mean: %.2f deg/s\n', mean(all_stable_velocities, 'omitnan'));
fprintf('  Median: %.2f deg/s\n', median(all_stable_velocities, 'omitnan'));
fprintf('  Std: %.2f deg/s\n', std(all_stable_velocities, 'omitnan'));
fprintf('  75th percentile: %.2f deg/s\n', prctile(all_stable_velocities, 75));
fprintf('  90th percentile: %.2f deg/s\n', prctile(all_stable_velocities, 90));
fprintf('  95th percentile: %.2f deg/s\n', prctile(all_stable_velocities, 95));

fprintf('\nMotion velocities (during transitions):\n');
fprintf('  N samples: %d\n', length(all_motion_velocities));
fprintf('  Mean: %.2f deg/s\n', mean(all_motion_velocities, 'omitnan'));
fprintf('  Median: %.2f deg/s\n', median(all_motion_velocities, 'omitnan'));
fprintf('  5th percentile: %.2f deg/s\n', prctile(all_motion_velocities, 5));
fprintf('  10th percentile: %.2f deg/s\n', prctile(all_motion_velocities, 10));

fprintf('\n=== DURATION ANALYSIS ===\n');
fprintf('Sit-to-stand durations (N=%d):\n', length(all_durations_sts));
fprintf('  Mean: %.2f s\n', mean(all_durations_sts));
fprintf('  Median: %.2f s\n', median(all_durations_sts));
fprintf('  Std: %.2f s\n', std(all_durations_sts));
fprintf('  Min: %.2f s\n', min(all_durations_sts));
fprintf('  Max: %.2f s\n', max(all_durations_sts));
fprintf('  25th percentile: %.2f s\n', prctile(all_durations_sts, 25));
fprintf('  75th percentile: %.2f s\n', prctile(all_durations_sts, 75));
fprintf('  90th percentile: %.2f s\n', prctile(all_durations_sts, 90));
fprintf('  95th percentile: %.2f s\n', prctile(all_durations_sts, 95));

fprintf('\nStand-to-sit durations (N=%d):\n', length(all_durations_s2s));
fprintf('  Mean: %.2f s\n', mean(all_durations_s2s));
fprintf('  Median: %.2f s\n', median(all_durations_s2s));
fprintf('  Std: %.2f s\n', std(all_durations_s2s));
fprintf('  Min: %.2f s\n', min(all_durations_s2s));
fprintf('  Max: %.2f s\n', max(all_durations_s2s));
fprintf('  25th percentile: %.2f s\n', prctile(all_durations_s2s, 25));
fprintf('  75th percentile: %.2f s\n', prctile(all_durations_s2s, 75));
fprintf('  90th percentile: %.2f s\n', prctile(all_durations_s2s, 90));
fprintf('  95th percentile: %.2f s\n', prctile(all_durations_s2s, 95));

%% Recommended thresholds
fprintf('\n=== RECOMMENDED THRESHOLDS ===\n');

% Velocity threshold: should be above 95th percentile of stable velocities
% but below 10th percentile of motion velocities
vel_thresh_low = prctile(all_stable_velocities, 95);
vel_thresh_high = prctile(all_motion_velocities, 10);
vel_thresh_recommended = (vel_thresh_low + vel_thresh_high) / 2;
fprintf('Velocity threshold:\n');
fprintf('  95th pctl of stable: %.2f deg/s\n', vel_thresh_low);
fprintf('  10th pctl of motion: %.2f deg/s\n', vel_thresh_high);
fprintf('  RECOMMENDED: %.1f deg/s\n', vel_thresh_recommended);

% Duration thresholds using IQR method
all_durations = [all_durations_sts; all_durations_s2s];
Q1 = prctile(all_durations, 25);
Q3 = prctile(all_durations, 75);
IQR = Q3 - Q1;
duration_min = max(0.3, Q1 - 1.5 * IQR);  % At least 0.3s
duration_max = Q3 + 1.5 * IQR;
fprintf('\nDuration thresholds (IQR method):\n');
fprintf('  Q1: %.2f s, Q3: %.2f s, IQR: %.2f s\n', Q1, Q3, IQR);
fprintf('  RECOMMENDED min: %.2f s\n', duration_min);
fprintf('  RECOMMENDED max: %.2f s\n', duration_max);

%% Plots
figure('Position', [100, 100, 1200, 400]);

% Velocity distribution
subplot(1, 3, 1);
histogram(all_stable_velocities, 50, 'Normalization', 'probability', 'FaceColor', 'b', 'FaceAlpha', 0.5);
hold on;
histogram(all_motion_velocities, 50, 'Normalization', 'probability', 'FaceColor', 'r', 'FaceAlpha', 0.5);
xline(15, 'k--', 'Current (15)', 'LineWidth', 2);
xline(vel_thresh_recommended, 'g--', sprintf('Recommended (%.1f)', vel_thresh_recommended), 'LineWidth', 2);
xlabel('Max Joint Velocity (deg/s)');
ylabel('Probability');
title('Velocity Distribution');
legend('Stable (sitting/standing)', 'Motion (transition)', 'Location', 'best');
xlim([0 100]);
grid on;

% Duration distribution - sit-to-stand
subplot(1, 3, 2);
histogram(all_durations_sts, 30, 'FaceColor', 'g', 'FaceAlpha', 0.7);
hold on;
xline(duration_min, 'r--', sprintf('Min (%.2fs)', duration_min), 'LineWidth', 2);
xline(duration_max, 'r--', sprintf('Max (%.2fs)', duration_max), 'LineWidth', 2);
xlabel('Duration (s)');
ylabel('Count');
title(sprintf('Sit-to-Stand Durations (N=%d)', length(all_durations_sts)));
grid on;

% Duration distribution - stand-to-sit
subplot(1, 3, 3);
histogram(all_durations_s2s, 30, 'FaceColor', 'm', 'FaceAlpha', 0.7);
hold on;
xline(duration_min, 'r--', sprintf('Min (%.2fs)', duration_min), 'LineWidth', 2);
xline(duration_max, 'r--', sprintf('Max (%.2fs)', duration_max), 'LineWidth', 2);
xlabel('Duration (s)');
ylabel('Count');
title(sprintf('Stand-to-Sit Durations (N=%d)', length(all_durations_s2s)));
grid on;

sgtitle('Sit-to-Stand Parameter Analysis');
saveas(gcf, 'sit_stand_parameter_analysis.png');
fprintf('\nFigure saved to: sit_stand_parameter_analysis.png\n');
