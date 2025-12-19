% Test script for sit-to-stand segmentation using kinematic velocity bounds
% Run this to verify the segmentation function works correctly before full conversion

clear all; close all;

% Add utilities to path
addpath(pwd);

% Find a sit-to-stand activity file to test
data_root = fullfile('..', 'RawData');
subjects = dir(data_root);
subjects = subjects([subjects.isdir] & ~ismember({subjects.name}, {'.', '..'}));

fprintf('=== Testing Sit-to-Stand Segmentation ===\n\n');

% Find first subject with sit_to_stand data
test_grf_file = '';
test_subject = '';
for s = 1:length(subjects)
    subject = subjects(s).name;
    csv_dir = fullfile(data_root, subject, 'CSV_data');
    if ~exist(csv_dir, 'dir'), continue; end

    activities = dir(csv_dir);
    activities = activities([activities.isdir] & ~ismember({activities.name}, {'.', '..'}));

    for a = 1:length(activities)
        if contains(activities(a).name, 'sit_to_stand', 'IgnoreCase', true)
            grf_file = fullfile(csv_dir, activities(a).name, 'GroundFrame_GRFs.csv');
            vel_file = fullfile(csv_dir, activities(a).name, 'Joint_Velocities.csv');
            if exist(grf_file, 'file') && exist(vel_file, 'file')
                test_grf_file = grf_file;
                test_vel_file = vel_file;
                test_subject = subject;
                test_activity = activities(a).name;
                break;
            end
        end
    end
    if ~isempty(test_grf_file), break; end
end

if isempty(test_grf_file)
    error('No sit_to_stand activity with GRF and velocity data found');
end

fprintf('Testing with:\n');
fprintf('  Subject: %s\n', test_subject);
fprintf('  Activity: %s\n', test_activity);
fprintf('  GRF file: %s\n', test_grf_file);
fprintf('  Velocity file: %s\n\n', test_vel_file);

% Run segmentation
[segments, n_sts, n_s2s] = segment_sit_stand_transitions(test_grf_file);

fprintf('\n=== Results ===\n');
fprintf('Found %d sit-to-stand transitions\n', n_sts);
fprintf('Found %d stand-to-sit transitions\n', n_s2s);

if isempty(segments)
    fprintf('\nNo segments found. Check thresholds.\n');
    return;
end

% Display segment details
fprintf('\nSegment details:\n');
for i = 1:length(segments)
    seg = segments(i);
    fprintf('  %d. %s: %.2fs - %.2fs (duration: %.2fs)\n', ...
        i, seg.type, seg.start_time, seg.end_time, seg.duration);
end

% Plot for visualization
figure('Position', [100, 100, 1200, 800]);

% Load data for plotting
grf_data = readtable(test_grf_file);
vel_data = readtable(test_vel_file);

time_grf = grf_data.time;
total_vert = grf_data.LForceY_Vertical + grf_data.RForceY_Vertical;

time_vel = vel_data.time;

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

% Compute max joint velocity
vel_matrix = zeros(height(vel_data), length(present_cols));
for c = 1:length(present_cols)
    vel_matrix(:, c) = abs(vel_data.(present_cols{c}));
end
max_joint_vel = max(vel_matrix, [], 2);

% Subplot 1: Vertical GRF
subplot(3, 1, 1);
plot(time_grf, total_vert, 'b', 'LineWidth', 1);
hold on;
yline(600, 'g--', 'Standing threshold', 'LineWidth', 1.5);
yline(400, 'r--', 'Sitting threshold', 'LineWidth', 1.5);
for i = 1:length(segments)
    xline(segments(i).start_time, 'k-', 'LineWidth', 2);
    xline(segments(i).end_time, 'k-', 'LineWidth', 2);
    % Shade the segment region
    x_fill = [segments(i).start_time, segments(i).end_time, segments(i).end_time, segments(i).start_time];
    y_fill = [min(ylim), min(ylim), max(ylim), max(ylim)];
    if strcmp(segments(i).type, 'sit_to_stand')
        fill(x_fill, y_fill, 'g', 'FaceAlpha', 0.2, 'EdgeColor', 'none');
    else
        fill(x_fill, y_fill, 'r', 'FaceAlpha', 0.2, 'EdgeColor', 'none');
    end
end
xlabel('Time (s)');
ylabel('Total Vertical GRF (N)');
title('Vertical GRF with Detected Segments');
legend('GRF', 'Standing', 'Sitting', 'Location', 'best');
grid on;

% Subplot 2: Max joint velocity
subplot(3, 1, 2);
plot(time_vel, max_joint_vel, 'b', 'LineWidth', 1);
hold on;
yline(15, 'r--', 'Velocity threshold (15 deg/s)', 'LineWidth', 1.5);
for i = 1:length(segments)
    xline(segments(i).start_time, 'k-', 'LineWidth', 2);
    xline(segments(i).end_time, 'k-', 'LineWidth', 2);
end
xlabel('Time (s)');
ylabel('Max Joint Velocity (deg/s)');
title('Maximum Joint Velocity Across All Joints');
grid on;

% Subplot 3: Individual joint velocities
subplot(3, 1, 3);
colors = lines(length(present_cols));
hold on;
for c = 1:length(present_cols)
    plot(time_vel, abs(vel_data.(present_cols{c})), 'Color', colors(c,:), 'LineWidth', 0.8);
end
yline(15, 'r--', 'LineWidth', 1.5);
for i = 1:length(segments)
    xline(segments(i).start_time, 'k-', 'LineWidth', 2);
    xline(segments(i).end_time, 'k-', 'LineWidth', 2);
end
xlabel('Time (s)');
ylabel('Joint Velocity (deg/s)');
title('Individual Joint Velocities');
legend(strrep(present_cols, '_', ' '), 'Location', 'best');
grid on;

sgtitle(sprintf('Sit-to-Stand Segmentation Test: %s / %s', test_subject, test_activity));

% Save figure
saveas(gcf, 'sit_stand_segmentation_test.png');
fprintf('\nFigure saved to: sit_stand_segmentation_test.png\n');

fprintf('\n=== Test Complete ===\n');
