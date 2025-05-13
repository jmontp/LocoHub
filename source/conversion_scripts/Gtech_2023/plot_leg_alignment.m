%% Plot Leg Alignment from Parquet File
%
% This script loads the generated parquet file (based on raw heel strikes)
% and plots the alignment between the left and right leg data for all tasks.
% This helps verify the phase offset applied during the data generation process.

clear all;
close all;
clc;

% --- Configuration ---
% Update this to the output file from the conversion script
parquet_file = './ParquetData/gtech_2023_phase.parquet'; 
output_plot_dir = 'Plots/AlignmentChecks_RawHS'; % Updated output dir name
% Options: 'lr', 'ipsicontra'. MUST match the convention used in the conversion script.
naming_convention = 'lr'; 
plot_variable_suffix = '_torque_s'; % Suffix for the variable to plot (e.g., '_angle_s' for knee/ankle/hip angle)
joint_to_plot = 'ankle'; % Joint variable prefix (e.g., 'knee', 'ankle', 'hip')

% --- Script Start ---

% Check if parquet file exists
if ~exist(parquet_file, 'file')
    error('Parquet file not found: %s\nPlease run convert_gtech_phase_to_parquet.m first.', parquet_file);
end

% Create output directory if it doesn't exist
if ~exist(output_plot_dir, 'dir')
    mkdir(output_plot_dir);
    fprintf('Created output directory: %s\n', output_plot_dir);
end

% Construct variable names based on naming convention
if strcmpi(naming_convention, 'ipsicontra')
    plot_variable_1 = [joint_to_plot, plot_variable_suffix, '_ipsi'];
    plot_variable_2 = [joint_to_plot, plot_variable_suffix, '_contra'];
    phase_col_1 = 'phase_ipsi';
    phase_col_2 = 'phase_contra';
    leg_label_1 = 'Ipsi';
    leg_label_2 = 'Contra';
else % Default to 'lr'
    plot_variable_1 = [joint_to_plot, plot_variable_suffix, '_l']; % Left leg variable
    plot_variable_2 = [joint_to_plot, plot_variable_suffix, '_r']; % Right leg variable
    phase_col_1 = 'phase_l'; % Use Left phase as reference
    phase_col_2 = 'phase_r';
    leg_label_1 = 'Left';
    leg_label_2 = 'Right';
end

% Construct GRF variable names
grf_variable_1 = ['grf_y_' lower(leg_label_1(1))]; % e.g., grf_y_l or grf_y_i
grf_variable_2 = ['grf_y_' lower(leg_label_2(1))]; % e.g., grf_y_r or grf_y_c

% Load the data
fprintf('Loading data from %s...\n', parquet_file);
try
    data = parquetread(parquet_file);
    fprintf('Data loaded successfully (%d rows).\n', height(data));
catch ME
    error('Failed to load parquet file: %s\nError: %s', parquet_file, ME.message);
end

% Define required columns based on naming convention
% 'task' column name comes from the final rename step in conversion script
required_base_cols = {'subject', 'task', 'task_info', 'activity_number', 'leading_leg_step'}; 
required_dynamic_cols = {phase_col_1, phase_col_2, plot_variable_1, plot_variable_2, grf_variable_1, grf_variable_2};
required_cols = [required_base_cols, required_dynamic_cols];

% Check if necessary columns exist
missing_cols = setdiff(required_cols, data.Properties.VariableNames);
if ~isempty(missing_cols)
    error('Missing required columns in the parquet file: %s\nPlease check configuration (naming_convention?) and parquet file contents.', strjoin(missing_cols, ', '));
end

% Get all unique task combinations in the dataset
[unique_all_combinations, ~] = unique(data(:, {'subject', 'task', 'task_info', 'activity_number'}), 'rows');
fprintf('Found %d unique subject/task combinations in the dataset to plot.\n', height(unique_all_combinations));

plot_count = 0;

% Iterate through each unique combination
for combo_idx = 1:height(unique_all_combinations)
    % Get the current combination
    current_combo = unique_all_combinations(combo_idx, :);
    % Handle potential cell array vs string differences for subject/task names
    if iscell(current_combo.subject)
        subject_name = current_combo.subject{1};
    else
        subject_name = current_combo.subject(1); % Assuming string array
    end
     if iscell(current_combo.task)
        task_name = current_combo.task{1};
    else
        task_name = current_combo.task(1); % Assuming string array
    end
     if iscell(current_combo.task_info)
        task_info = current_combo.task_info{1};
    else
        task_info = current_combo.task_info(1); % Assuming string array
    end
    activity_num = current_combo.activity_number(1);
    
    % Create a clean string representation for subject name if needed
    if isa(subject_name, 'string') && length(subject_name)>1 
        subject_name_str = subject_name(1); % Take first element if it's an array
    else
        subject_name_str = string(subject_name); % Convert to string
    end

    % Find all data rows matching this specific combination
    match_indices = strcmp(data.subject, subject_name) & ...
                    strcmp(data.task, task_name) & ...
                    strcmp(data.task_info, task_info) & ...
                    data.activity_number == activity_num;
                
    task_subset = data(match_indices, :);
    
    if isempty(task_subset) || height(task_subset) < 5 % Skip if no/very little data
        warning('Skipping combination %d due to insufficient data points.', combo_idx);
        continue; 
    end
    
    % Extract leading leg for this combination (should be consistent)
    leading_leg_plot = task_subset.leading_leg_step{1}; 

    fprintf('\nPlotting alignment for combination %d/%d: Subject=%s, Task=%s (%d), Task Info=%s, Leading Leg=%s\n', ...
            combo_idx, height(unique_all_combinations), subject_name_str, task_name, activity_num, task_info, leading_leg_plot);
    
    % --------------------------
    % PLOT BOTH LEGS DIRECTLY FROM TABLE DATA
    % --------------------------
    % Create a larger figure with more space for the title
    figure('Name', sprintf('Leg Alignment: %s - %s (%d) - %s', subject_name_str, task_name, activity_num, task_info), ...
           'Position', [50, 50, 1000, 900]); % Make figure taller for subplots
    
    % --- Top Subplot: Joint Angle ---
    subplot(2, 1, 1); % 2 rows, 1 column, first plot
    hold on;
    title(sprintf('%s Alignment vs %s Phase', strrep(joint_to_plot,'_',' '), leg_label_1), 'FontSize', 14, 'Interpreter', 'none');
    ylabel(sprintf('%s (%s)', strrep(joint_to_plot,'_',' '), plot_variable_suffix), 'FontSize', 12, 'Interpreter', 'none');
    grid on;
    set(gca, 'XTickLabel', []); % Remove x-axis labels for top plot
    
    % Plot directly from table using primary phase as x-axis for both legs
    x_phase_percent = task_subset.(phase_col_1) * 100; % Primary phase (e.g., phase_l)
    [sorted_x, sort_idx] = sort(task_subset.(phase_col_1)); % Sort by primary phase for potential future use, though not strictly needed for scatter

    % Plot Leg 2 (e.g., Right or Contra)
    y_leg2 = task_subset.(plot_variable_2);
    scatter(x_phase_percent, y_leg2, 10, 'b', 'filled', 'MarkerFaceAlpha', 0.3);
    
    % Plot Leg 1 (e.g., Left or Ipsi)
    y_leg1 = task_subset.(plot_variable_1);
    scatter(x_phase_percent, y_leg1, 10, 'r', 'filled', 'MarkerFaceAlpha', 0.3);
        
    % Add legend dynamically
    legend_labels = {sprintf('%s Leg Data', leg_label_2), ...
                     sprintf('%s Leg Data', leg_label_1)};
    legend(legend_labels, 'Location', 'best', 'FontSize', 10);
    hold off;

    % --- Bottom Subplot: Vertical GRF ---
    subplot(2, 1, 2); % 2 rows, 1 column, second plot
    hold on;
    title(sprintf('Vertical GRF vs %s Phase', leg_label_1), 'FontSize', 14);
    xlabel(sprintf('%s Leg Phase (%% Cycle)', leg_label_1), 'FontSize', 12);
    ylabel('Vertical GRF (N)', 'FontSize', 12);
    grid on;
    
    % Plot Leg 2 GRF (e.g., Right or Contra)
    y_grf2 = task_subset.(grf_variable_2);
    scatter(x_phase_percent, y_grf2, 10, 'b', 'filled', 'MarkerFaceAlpha', 0.3);
        
    % Plot Leg 1 GRF (e.g., Left or Ipsi)
    y_grf1 = task_subset.(grf_variable_1);
    scatter(x_phase_percent, y_grf1, 10, 'r', 'filled', 'MarkerFaceAlpha', 0.3);
        
    % Add legend dynamically for GRF
    legend_labels_grf = {sprintf('%s Leg GRF Data', leg_label_2), ...
                         sprintf('%s Leg GRF Data', leg_label_1)};
    legend(legend_labels_grf, 'Location', 'best', 'FontSize', 10);
    hold off;

    % Adjust overall title position slightly if needed
    sgtitle(sprintf('Leg Alignment: %s - %s (%d) - %s [Lead: %s]', ...
        subject_name_str, task_name, activity_num, task_info, upper(leading_leg_plot)), ...
        'Interpreter', 'none', 'FontSize', 16, 'FontWeight', 'bold');
    
    % Save plot
    % Use makeValidName for potentially problematic characters in task_info
    plot_filename_base = sprintf('LegAlignment_Subj_%s_Task_%s_%d_TaskInfo_%s.png', ...
        subject_name_str, task_name, activity_num, matlab.lang.makeValidName(task_info));
    plot_filename = fullfile(output_plot_dir, plot_filename_base);
    
    try
        saveas(gcf, plot_filename);
        fprintf('  Saved leg alignment plot: %s\n', plot_filename);
        plot_count = plot_count + 1;
    catch ME_save
         warning('Failed to save plot: %s\nError: %s', plot_filename, ME_save.message);
    end
    close(gcf); % Close figure after saving to prevent memory issues
end

fprintf('\nFinished plotting alignments.\n');
fprintf('Generated %d plots.\n', plot_count);

if plot_count == 0 && height(unique_all_combinations) > 0
     warning('No plots were generated, although combinations were found. Check data or script logic (e.g., required columns, naming convention).');
elseif height(unique_all_combinations) == 0
     fprintf('No unique combinations found in the data to plot.\n');
end 