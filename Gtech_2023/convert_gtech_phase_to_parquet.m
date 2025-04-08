% This file is meant to convert raw Gtech 2023 data based on heel strikes
% from _parsing.mat files into a standardized phase-aligned parquet file.

% --- Step 1: Initialization & Setup ---
clear all;
close all;

num_points_per_step = 150;
naming_convention = 'lr'; % Options: 'lr', 'ipsicontra'
data_dir_root = '.'; % Assumes RawData and Segmentation are subdirs of CWD
output_dir = 'ParquetData';
critical_activities = {'stairs', 'incline_walk', 'normal_walk', 'sit_to_stand'}; % Define critical tasks

% Initialize a single table to hold all processed data
total_data = table();

% Initialize per-activity counters
critical_activity_counts = struct();
for i = 1:length(critical_activities)
    activity_fieldname = matlab.lang.makeValidName(critical_activities{i}); % Ensure valid fieldname
    critical_activity_counts.(activity_fieldname) = 0;
end

% Expected raw file types and their time column name
% Used for iterating through required raw files
raw_file_info = struct(...
    'Joint_Angle', 'time', ...
    'Joint_Velocities', 'time', ...
    'Joint_Moments', 'time', ...
    'Link_Angle', 'time', ...
    'Link_Velocities', 'time', ...
    'GroundFrame_GRFs', 'time', ...
    'Transforms_Euler', 'Header' ... % Special case for global angles file
);
raw_filenames = fieldnames(raw_file_info);

% --- Start Main Processing ---
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

segmentation_dir = fullfile(data_dir_root, 'Segmentation');
if ~exist(segmentation_dir, 'dir')
    error('Segmentation directory not found: %s', segmentation_dir);
end

subjects = dir(segmentation_dir);
subjects = subjects(~ismember({subjects.name},{'.','..'}) & [subjects.isdir]); % Filter . and .. and files

if isempty(subjects)
    error('No subject directories found in %s', segmentation_dir);
end

% --- Step 2: Subject Loop ---
for subject_idx = 1:length(subjects)
% for subject_idx = 1:2
    subject = subjects(subject_idx).name;
    subject_save_name = strcat("Gtech_2023_", subject);
    subject_segmentation_dir = fullfile(segmentation_dir, subject);
    subject_raw_data_dir = fullfile(data_dir_root, 'RawData', subject);

    % Check if corresponding RawData directory exists
    if ~exist(subject_raw_data_dir, 'dir')
        warning('RawData directory not found for subject %s: %s. Skipping subject.', subject, subject_raw_data_dir);
        continue;
    end

    activities = dir(fullfile(subject_segmentation_dir, '*_parsing.mat')); % Look for parsing files

    if isempty(activities)
        warning('No *_parsing.mat files found for subject %s in %s. Skipping subject.', subject, subject_segmentation_dir);
                continue;
            end

    % fprintf('Processing Subject: %s (%d activities)\n', subject, length(activities));
    printed_subject_header = false; % Flag to print subject header only once

    subject_activity_data = table(); % Accumulate data per subject

    % --- Activity Loop ---
    for activity_idx = 1:length(activities)
        activity_file_name = activities(activity_idx).name; % e.g., walk_1_normal_parsing.mat

        % --- Corrected Preliminary check for critical activity based on filename ---
        is_potentially_critical = false;
        for c_idx = 1:length(critical_activities)
            % Check if filename starts with any critical activity name
            if startsWith(activity_file_name, critical_activities{c_idx}, 'IgnoreCase', true)
                is_potentially_critical = true;
                break; % Found a match, no need to check further
            end
        end
        
        if ~is_potentially_critical
             % fprintf('  Skipping non-critical activity (preliminary check): %s\n', activity_file_name);
             continue; % Skip before attempting to load anything
        end
        % --- End Preliminary Check ---

        % --- Step 1 (Cont.): Load Essential Data ---
        raw_data = struct(); % Store all loaded raw data tables for this activity
        raw_time_vectors = struct(); % Store time vectors separately
        parsing_data = struct();
        transform_data = struct();
        raw_data_load_successful = true; % Flag to track data loading

        % Load Parsing Data (Heel Strikes)
        parsing_file_path = fullfile(subject_segmentation_dir, activity_file_name);

        % Check if parsing file exists first
        if ~exist(parsing_file_path, 'file')
            warning('Parsing file not found: %s. Skipping.', parsing_file_path);
            continue; % Skip this activity if parsing file doesn't exist
        end

        % Try loading the existing parsing file
        try
            parsing_data = load(parsing_file_path);
            % Check required fields after successful load
            % Skip ONLY if BOTH left and right data are missing/empty
            left_invalid = ~isfield(parsing_data, 'left') || isempty(parsing_data.left);
            right_invalid = ~isfield(parsing_data, 'right') || isempty(parsing_data.right);
            if left_invalid && right_invalid
                 % Only warn if critical, using the preliminary name check
                 if ismember(activity_name, critical_activities) 
                    warning('Parsing file %s found, but missing/empty heel strike data for BOTH legs. Skipping.', activity_file_name);
                 end
                raw_data_load_successful = false;
            end
        catch ME
             % Warn if loading the *existing* file failed (corruption, permissions, etc.)
             % Use preliminary name for check as activity_name is not defined yet
             if ismember(activity_name, critical_activities)
                 warning(ME.identifier, 'Error loading existing parsing file %s: %s. Skipping.', activity_file_name, ME.message);
             end
            raw_data_load_successful = false;
            left_invalid = true; % Assume invalid if load fails
            right_invalid = true;
        end
        if ~raw_data_load_successful, continue; end % Skip if parsing failed

        % Determine activity base name for raw files
        [~, activity_base_name] = fileparts(activity_file_name);
        activity_base_name = strrep(activity_base_name, '_parsing', ''); % Remove suffix

        % --- Determine raw_activity_name (Adapted from previous logic) ---
        activity_name_parts = strsplit(activity_base_name, '_');
        part_is_num = ~isnan(str2double(activity_name_parts));
        first_num_idx = find(part_is_num, 1);

        if isempty(first_num_idx) || first_num_idx == 1
            % Handle cases like 'step_ups' which might not have a number
             if length(activity_name_parts) >= 1
                 activity_name = activity_name_parts{1};
                 activity_number = 1; % Default
                 sub_activity_name = strjoin(activity_name_parts(2:end), '_');
                 if strcmp(activity_name, 'step_ups') % Specific override
                     raw_activity_name = 'step_ups';
                 else
                     raw_activity_name = activity_name; % Fallback
                end
            else
                warning('Cannot parse activity name structure for %s. Skipping.', activity_base_name);
            continue;
        end
        else
            activity_name = strjoin(activity_name_parts(1:first_num_idx-1), '_');
            activity_number = str2double(activity_name_parts{first_num_idx});
            sub_activity_name = strjoin(activity_name_parts(first_num_idx+1:end), '_');
            % Construct default raw name without sub-activity part
            raw_activity_name = [activity_name '_' int2str(activity_number)]; 
        end

        % Override raw_activity_name for special cases (Stairs, Jump, etc.)
        if strcmp(activity_name, 'stairs')
            stair_num_str = '';
            if ~isempty(sub_activity_name)
                stair_num = str2double(sub_activity_name(1:min(2,length(sub_activity_name))));
                 if isnan(stair_num) && ~isempty(sub_activity_name)
                     stair_num = str2double(sub_activity_name(1));
                 end
                 if ~isnan(stair_num)
                    stair_num_str = num2str(stair_num); % Convert back to string for filename
                    raw_activity_name = [activity_name '_' int2str(activity_number) '_' stair_num_str];
                 else
                     if ismember(activity_name, critical_activities)
                         warning('Could not parse stair number for %s', activity_base_name);
                     end
                 end
            end
        elseif strcmp(activity_name, 'jump') && activity_number == 1 && ~isempty(sub_activity_name) && ~isnan(str2double(sub_activity_name(1)))
             jump_num_str = sub_activity_name(1);
             raw_activity_name = [activity_name '_' int2str(activity_number) '_' jump_num_str];
        % Add other special case overrides here if needed
        end

        % --- Check if activity is critical ---
        if ~ismember(activity_name, critical_activities)
            % fprintf('  Skipping non-critical activity: %s\n', activity_file_name);
            continue; % Skip to the next activity
        end

        % --- Print Headers only if critical activity is found ---
        if ~printed_subject_header
            fprintf('Processing Subject: %s (%d activities found, processing critical only)\n', subject, length(activities));
            printed_subject_header = true;
        end
        fprintf('  Processing Activity: %s (%d/%d)\n', activity_file_name, activity_idx, length(activities));

        % --- End raw_activity_name determination ---

        % Load Raw Data Files (CSVs and Transforms)
        raw_kin_time = []; % Master time for kinematic/kinetic CSVs from their 'time' column
        essential_raw_missing = false;

        for k = 1:length(raw_filenames)
            fname = raw_filenames{k};
            time_col = raw_file_info.(fname); % Expected time column name

            % Construct file path based on type
            if strcmp(fname, 'Transforms_Euler')
                file_path = fullfile(subject_raw_data_dir, 'Transforms_Euler', [raw_activity_name '.csv']);
            elseif strcmp(fname, 'GroundFrame_GRFs')
                 file_path = fullfile(subject_raw_data_dir, 'CSV_data', raw_activity_name, [fname '.csv']);
            else % Other Kin/Kin CSVs
                 % Assuming filenames like 'Joint_Angle.csv', 'Joint_Velocities.csv' etc.
                 % Keep the underscore from raw_file_info definition
                 csv_filename_base = fname; 
                 file_path = fullfile(subject_raw_data_dir, 'CSV_data', raw_activity_name, [csv_filename_base '.csv']);
            end

            % Load the table and time vector
            try
                if exist(file_path, 'file')
                    current_table = readtable(file_path);
                    if ~ismember(time_col, current_table.Properties.VariableNames)
                         if ismember(activity_name, critical_activities)
                             warning('Time column "%s" not found in %s. Skipping file.', time_col, file_path);
                         end
                         raw_data.(fname) = []; % Mark as missing
                         if ~ismember(fname, {'Transforms_Euler', 'Link_Angle', 'Link_Velocities'}) % Mark if essential is missing
                            essential_raw_missing = true;
                        end
                    else
                        raw_data.(fname) = current_table;
                        raw_time_vectors.(fname) = current_table.(time_col);

                        % Assign master kin time from first valid kin/kin file loaded
                        if isempty(raw_kin_time) && ismember(fname, {'Joint_Angle', 'Joint_Velocities', 'Joint_Moments'})
                            raw_kin_time = raw_time_vectors.(fname);
                            fprintf('    Using master kinematic time from: %s\n', fname);
                        end
                    end
                else
                    if ismember(activity_name, critical_activities)
                        warning('Raw data file not found: %s. Will use NaNs.', file_path);
                    end
                    raw_data.(fname) = []; % Mark as missing
                    if ~ismember(fname, {'Transforms_Euler', 'Link_Angle', 'Link_Velocities'}) % Mark if essential is missing
                        essential_raw_missing = true;
                    end
                end
            catch ME
                if ismember(activity_name, critical_activities)
                    warning(ME.identifier, 'Error loading raw data file %s: %s. Will use NaNs.', file_path, ME.message);
                end
                raw_data.(fname) = [];
                 if ~ismember(fname, {'Transforms_Euler', 'Link_Angle', 'Link_Velocities'})
                    essential_raw_missing = true;
                            end
                        end
                    end
                
        % Load Transforms .mat
        transform_file_path = fullfile(subject_raw_data_dir, 'Transforms', [raw_activity_name '.mat']);
        transform_data_loaded = false;
        try
            if exist(transform_file_path, 'file')
                t_data = load(transform_file_path);
                 
                % Check structure more granularly
                required_columns_present = true; % Renaming to required_columns_present for clarity
                if ~isfield(t_data, 'Transforms')
                    if ismember(activity_name, critical_activities)
                         warning('Transforms file %s loaded, but missing top-level \'\'Transforms\'\' struct.', transform_file_path);
                    end
                    required_columns_present = false;
                elseif ~istable(t_data.Transforms) % Verify it's a table before checking columns
                     if ismember(activity_name, critical_activities)
                         warning('Transforms file %s loaded, but \'\'Transforms\'\' is not a table.', transform_file_path);
                     end
                    required_columns_present = false;
                elseif ~any(strcmp('Header', t_data.Transforms.Properties.VariableNames))
                    if ismember(activity_name, critical_activities)
                         warning('Transforms table in %s loaded, but missing \'\'Header\'\' column.', transform_file_path);
                    end
                    required_columns_present = false;
                 elseif ~any(strcmp('calcn_l', t_data.Transforms.Properties.VariableNames))
                     if ismember(activity_name, critical_activities)
                         warning('Transforms table in %s loaded, but missing \'\'calcn_l\'\' column.', transform_file_path);
                     end
                     required_columns_present = false;
                 elseif ~any(strcmp('calcn_r', t_data.Transforms.Properties.VariableNames))
                      if ismember(activity_name, critical_activities)
                         warning('Transforms table in %s loaded, but missing \'\'calcn_r\'\' column.', transform_file_path);
                      end
                     required_columns_present = false;
                end

                % Assign data only if all required columns were found
                if required_columns_present
                    transform_data.time = t_data.Transforms.Header;
                    transform_data.l = t_data.Transforms.calcn_l;
                    transform_data.r = t_data.Transforms.calcn_r;
                    transform_data_loaded = true; % Mark transforms as loaded and valid
                 end % else: required_columns_present is false, transform_data_loaded remains false

            else % File doesn't exist
                 if ismember(activity_name, critical_activities)
                     warning('Transforms file not found: %s. COP cannot be transformed.', transform_file_path);
                 end
                 % transform_data_loaded remains false
            end
        catch ME
             % Use preliminary name for check as activity_name is not defined yet
             if ismember(activity_name, critical_activities)
                 warning(ME.identifier, 'Error loading existing transforms file %s: %s.', transform_file_path, ME.message);
             end
             % transform_data_loaded remains false
        end

        % Check essential data availability
        if essential_raw_missing || isempty(raw_kin_time)
            fprintf('  Skipping activity %s due to missing essential raw data or time vector.\n', activity_file_name);
                    continue;
                end

        % --- Step 2 (Cont.): Determine Leading Leg ---
        % Use flags set during parsing data check (left_invalid, right_invalid)

        if ~left_invalid && right_invalid
            % Only left data is valid
            leading_leg = 'l';
            leading_hs_times = parsing_data.left;
            fprintf('    Leading Leg: %s (Only left HS data available)\n', leading_leg);
        elseif left_invalid && ~right_invalid
            % Only right data is valid
            leading_leg = 'r';
            leading_hs_times = parsing_data.right;
            fprintf('    Leading Leg: %s (Only right HS data available)\n', leading_leg);
        elseif ~left_invalid && ~right_invalid
            % Both left and right data are valid, compare first heel strike
            first_hs_l = parsing_data.left(1,1);
            first_hs_r = parsing_data.right(1,1);
            if first_hs_l <= first_hs_r
                leading_leg = 'l';
                leading_hs_times = parsing_data.left;
            else
                leading_leg = 'r';
                leading_hs_times = parsing_data.right;
            end
            fprintf('    Leading Leg: %s (Based on first HS comparison)\n', leading_leg);
        else
            % This case should theoretically not be reached because the script 
            % continues only if raw_data_load_successful is true (meaning at least one leg was valid).
            % Adding a safeguard in case logic flow changes.
            warning('Error determining leading leg for %s. Both left and right HS data appear invalid despite passing initial checks. Skipping activity.', activity_file_name);
            continue; % Skip activity
        end

        % --- Step 3: Define Step Intervals ---
        % Check if any step intervals exist (each row is [start, end])
        if isempty(leading_hs_times) 
            % It becomes TRUE if N=0 (i.e., no steps found)
            if ismember(activity_name, critical_activities)
                warning('No step intervals found for leading leg in %s. Skipping activity.', activity_file_name);
            end
            continue;
        end
        % If code reaches here, N must be >= 1
        % Each row is assumed to be [start_time, end_time]
        step_intervals = leading_hs_times;
        num_steps = size(step_intervals, 1);
        fprintf('    Found %d step intervals directly from parsing data.\n', num_steps);

        activity_step_data = table(); % Accumulate steps for this activity

        % --- Step 4: Reconstruct & Assign Phase (Per Step) ---
        for step_idx = 1:num_steps
            step_start = step_intervals(step_idx, 1); % Start time from Col 1
            step_end = step_intervals(step_idx, 2);   % End time from Col 2

                            if step_end <= step_start
                warning('  Invalid step interval [%f, %f] for step %d. Skipping.', step_start, step_end, step_idx);
                                continue;
                            end
                            
            step_data_single = table(); % Data for this single step

            % Add Metadata
            step_data_single.subject = repmat(subject_save_name, num_points_per_step, 1);
            step_data_single.activity = repmat({activity_name}, num_points_per_step, 1);
            step_data_single.task_info = repmat({sub_activity_name}, num_points_per_step, 1);
            step_data_single.activity_number = repmat(activity_number, num_points_per_step, 1);
            step_data_single.leading_leg_step = repmat({leading_leg}, num_points_per_step, 1); % Add leading leg marker

            % Generate Time & Phase Vectors for this step
                            time_interp = linspace(step_start, step_end, num_points_per_step)';
            base_phase_step = linspace(0, 1 - 1/num_points_per_step, num_points_per_step)';
            offset_phase_step = mod(base_phase_step + 0.5, 1);
            step_data_single.time = time_interp; % Common time column for the step

            % --- Interpolate signals ---
            interp_method = 'linear'; % Use linear for robustness, 'cubic' can overshoot

            % --- Interpolate Joint Angles ---
            angle_vars = {'knee_angle', 'ankle_angle', 'hip_flexion'};
            if isfield(raw_data, 'Joint_Angle') && ~isempty(raw_data.Joint_Angle)
                raw_angle_table = raw_data.Joint_Angle;
                idx_angle = (raw_kin_time >= step_start & raw_kin_time <= step_end);
                raw_angle_time_slice = raw_kin_time(idx_angle);

                for v = 1:length(angle_vars)
                    var_base = angle_vars{v};
                    col_l = [var_base '_l']; col_r = [var_base '_r'];
                    if ismember(col_l, raw_angle_table.Properties.VariableNames)
                        raw_vals_l = raw_angle_table.(col_l)(idx_angle);
                        step_data_single.(col_l) = interpolate_signal(raw_angle_time_slice, raw_vals_l, time_interp, interp_method);
                    else; step_data_single.(col_l) = nan(num_points_per_step, 1); end
                    if ismember(col_r, raw_angle_table.Properties.VariableNames)
                        raw_vals_r = raw_angle_table.(col_r)(idx_angle);
                         step_data_single.(col_r) = interpolate_signal(raw_angle_time_slice, raw_vals_r, time_interp, interp_method);
                    else; step_data_single.(col_r) = nan(num_points_per_step, 1); end
                end
            else % Add NaN columns if raw angle data missing
                 for v = 1:length(angle_vars); var_base = angle_vars{v}; step_data_single.([var_base '_l']) = nan(num_points_per_step, 1); step_data_single.([var_base '_r']) = nan(num_points_per_step, 1); end
            end

            % --- Interpolate Joint Velocities ---
            vel_vars = {'knee_velocity', 'ankle_velocity', 'hip_flexion_velocity'};
             if isfield(raw_data, 'Joint_Velocities') && ~isempty(raw_data.Joint_Velocities)
                raw_vel_table = raw_data.Joint_Velocities;
                idx_vel = (raw_kin_time >= step_start & raw_kin_time <= step_end);
                raw_vel_time_slice = raw_kin_time(idx_vel);

                for v = 1:length(vel_vars)
                    var_base = vel_vars{v};
                    col_l = [var_base '_l']; col_r = [var_base '_r'];
                     if ismember(col_l, raw_vel_table.Properties.VariableNames)
                        raw_vals_l = raw_vel_table.(col_l)(idx_vel);
                        step_data_single.(col_l) = interpolate_signal(raw_vel_time_slice, raw_vals_l, time_interp, interp_method);
                    else; step_data_single.(col_l) = nan(num_points_per_step, 1); end
                     if ismember(col_r, raw_vel_table.Properties.VariableNames)
                        raw_vals_r = raw_vel_table.(col_r)(idx_vel);
                        step_data_single.(col_r) = interpolate_signal(raw_vel_time_slice, raw_vals_r, time_interp, interp_method);
                    else; step_data_single.(col_r) = nan(num_points_per_step, 1); end
                                    end
                                else
                 for v = 1:length(vel_vars); var_base = vel_vars{v}; step_data_single.([var_base '_l']) = nan(num_points_per_step, 1); step_data_single.([var_base '_r']) = nan(num_points_per_step, 1); end
            end

            % --- Interpolate Joint Moments ---
            mom_vars = {'knee_angle_moment', 'ankle_angle_moment', 'hip_flexion_moment'};
             if isfield(raw_data, 'Joint_Moments') && ~isempty(raw_data.Joint_Moments)
                raw_mom_table = raw_data.Joint_Moments;
                idx_mom = (raw_kin_time >= step_start & raw_kin_time <= step_end);
                raw_mom_time_slice = raw_kin_time(idx_mom);

                for v = 1:length(mom_vars)
                    var_base = mom_vars{v};
                    % Construct L/R column names (e.g., knee_angle_l_moment)
                    prefix = strrep(var_base, '_moment', '');
                    col_l = [prefix '_l_moment']; col_r = [prefix '_r_moment'];
                     if ismember(col_l, raw_mom_table.Properties.VariableNames)
                        raw_vals_l = raw_mom_table.(col_l)(idx_mom);
                        step_data_single.(col_l) = interpolate_signal(raw_mom_time_slice, raw_vals_l, time_interp, interp_method);
                    else; step_data_single.(col_l) = nan(num_points_per_step, 1); end
                     if ismember(col_r, raw_mom_table.Properties.VariableNames)
                        raw_vals_r = raw_mom_table.(col_r)(idx_mom);
                        step_data_single.(col_r) = interpolate_signal(raw_mom_time_slice, raw_vals_r, time_interp, interp_method);
                    else; step_data_single.(col_r) = nan(num_points_per_step, 1); end
                                    end
                                else
                 for v = 1:length(mom_vars); var_base = mom_vars{v}; prefix = strrep(var_base, '_moment', ''); step_data_single.([prefix '_l_moment']) = nan(num_points_per_step, 1); step_data_single.([prefix '_r_moment']) = nan(num_points_per_step, 1); end
            end

            % --- Interpolate Link Angles (Example for Foot Angle Z - Add others) ---
            link_angle_cols_to_process = {'calcn_l_Z', 'calcn_r_Z'}; % Define expected input cols
            if isfield(raw_data, 'Link_Angle') && ~isempty(raw_data.Link_Angle)
                 raw_link_ang_table = raw_data.Link_Angle;
                 idx_link_ang = (raw_kin_time >= step_start & raw_kin_time <= step_end);
                 raw_link_ang_time_slice = raw_kin_time(idx_link_ang);
                 for v = 1:length(link_angle_cols_to_process)
                     col_name = link_angle_cols_to_process{v};
                     if ismember(col_name, raw_link_ang_table.Properties.VariableNames)
                           raw_vals = raw_link_ang_table.(col_name)(idx_link_ang);
                           step_data_single.(col_name) = interpolate_signal(raw_link_ang_time_slice, raw_vals, time_interp, interp_method);
                     else; step_data_single.(col_name) = nan(num_points_per_step, 1); end
                 end
            else % Add NaNs if Link_Angle file missing
                for v = 1:length(link_angle_cols_to_process); step_data_single.(link_angle_cols_to_process{v}) = nan(num_points_per_step, 1); end
            end
             % Add similar block for Link_Velocities if needed, using raw_data.Link_Velocities

            % --- Interpolate Global Angles ---
             if isfield(raw_data, 'Transforms_Euler') && ~isempty(raw_data.Transforms_Euler)
                raw_global_table = raw_data.Transforms_Euler;
                raw_global_time = raw_time_vectors.Transforms_Euler;
                idx_global = (raw_global_time >= step_start & raw_global_time <= step_end);
                raw_global_time_slice = raw_global_time(idx_global);
                global_cols = raw_global_table.Properties.VariableNames;

                for c = 1:length(global_cols)
                    col_name = global_cols{c};
                    if ~strcmp(col_name, raw_file_info.Transforms_Euler) % Skip time column
                         raw_vals = raw_global_table.(col_name)(idx_global);
                         step_data_single.(col_name) = interpolate_signal(raw_global_time_slice, raw_vals, time_interp, interp_method);
                                    end
                                end
             else
                 % Add NaNs for expected global columns if file was missing
                 expected_global_cols = {'foot_l_X', 'foot_l_Y', 'foot_l_Z', 'foot_r_X', 'foot_r_Y', 'foot_r_Z'}; % Example
                 for c = 1:length(expected_global_cols); step_data_single.(expected_global_cols{c}) = nan(num_points_per_step, 1); end
             end

            % --- Interpolate GRF & Transform COP ---
            grf_cols_base = {'ForceX', 'ForceY_Vertical', 'ForceZ', 'COPX', 'COPY_Vertical', 'COPZ'};
            grf_cols_final_base = {'grf_x', 'grf_y', 'grf_z', 'cop_x', 'cop_y', 'cop_z'};
            if isfield(raw_data, 'GroundFrame_GRFs') && ~isempty(raw_data.GroundFrame_GRFs)
                raw_grf_table = raw_data.GroundFrame_GRFs;
                raw_grf_time = raw_time_vectors.GroundFrame_GRFs;
                idx_grf = (raw_grf_time >= step_start & raw_grf_time <= step_end);
                raw_grf_time_slice = raw_grf_time(idx_grf);
                raw_grf_table_slice = raw_grf_table(idx_grf,:);

                % Find corresponding transforms for COP transformation
                idx_trans = []; transforms_slice_l = {}; transforms_slice_r = {}; trans_time_slice = [];
                if transform_data_loaded && isfield(transform_data, 'time') % Check if transform_data is valid
                    idx_trans = (transform_data.time >= step_start & transform_data.time <= step_end);
                    if any(idx_trans) % Only proceed if there are transforms in the interval
                        trans_time_slice = transform_data.time(idx_trans);
                        transforms_slice_l = transform_data.l(idx_trans);
                        transforms_slice_r = transform_data.r(idx_trans);
                    else
                        transform_data_loaded = false; % No transforms for this interval
                        if ismember(activity_name, critical_activities)
                            warning('No transforms found within step interval [%f, %f]. COP will not be transformed.', step_start, step_end);
                        end
                                end
                            end
                            
                for leg_char = ['l', 'r']
                    for v = 1:length(grf_cols_base)
                        var_base_raw = grf_cols_base{v};
                        col_raw = [upper(leg_char) var_base_raw]; % e.g., LForceX, RCOPZ
                        col_final = [grf_cols_final_base{v} '_' leg_char]; % e.g., grf_x_l, cop_z_r

                        if ismember(col_raw, raw_grf_table.Properties.VariableNames)
                            raw_vals = raw_grf_table_slice.(col_raw);

                            % Special handling for COP transformation
                            if contains(var_base_raw, 'COP') && transform_data_loaded && ~isempty(trans_time_slice)
                                if strcmp(var_base_raw, 'COPX') % Process X and Z together
                                     cop_x_raw_slice = raw_vals;
                                     if ismember([upper(leg_char) 'COPZ'], raw_grf_table_slice.Properties.VariableNames)
                                         cop_z_raw_slice = raw_grf_table_slice.([upper(leg_char) 'COPZ']);
                                     else
                                          if ismember(activity_name, critical_activities)
                                              warning('Missing raw Z COP column for %s leg in step %d. Cannot transform COP.', leg_char, step_idx);
                                          end
                                          cop_z_raw_slice = nan(size(cop_x_raw_slice)); % Use NaNs
                                     end

                                     cop_local_x = nan(length(raw_grf_time_slice), 1);
                                     cop_local_z = nan(length(raw_grf_time_slice), 1);

                                     transforms_to_use = transforms_slice_r; % Default R
                                     if leg_char == 'l'; transforms_to_use = transforms_slice_l; end

                                     % Ensure transforms_to_use matches length of trans_time_slice
                                     if length(trans_time_slice) >= 1 && length(transforms_to_use) == length(trans_time_slice)
                                          for t_idx = 1:length(raw_grf_time_slice)
                                             current_grf_time = raw_grf_time_slice(t_idx);
                                             [~, closest_trans_idx] = min(abs(trans_time_slice - current_grf_time));
                                             if closest_trans_idx <= length(transforms_to_use)
                                                 T = transforms_to_use{closest_trans_idx};
                                            if isnumeric(T) && all(size(T) == [4, 4])
                                                     translation = T(1:3, 4); rotation = T(1:3, 1:3);
                                                     cop_global = [cop_x_raw_slice(t_idx); 0; cop_z_raw_slice(t_idx)];
                                                if ~any(isnan(cop_global))
                                                    cop_relative = cop_global - translation;
                                                    cop_local = rotation' * cop_relative;
                                                          cop_local_x(t_idx) = cop_local(1);
                                                          cop_local_z(t_idx) = cop_local(3);
                                                end
                                            end
                                        end
                                    end
                                         step_data_single.(['cop_x_' leg_char]) = interpolate_signal(raw_grf_time_slice, cop_local_x, time_interp, interp_method);
                                         step_data_single.(['cop_z_' leg_char]) = interpolate_signal(raw_grf_time_slice, cop_local_z, time_interp, interp_method);
                                         step_data_single.(['cop_y_' leg_char]) = zeros(num_points_per_step, 1); % Assume zero vertical COP in local frame
                                     else % Not enough transform data or length mismatch
                                         if ismember(activity_name, critical_activities)
                                             warning('Transform data issue for step %d. Cannot transform COP.', step_idx);
                                         end
                                         step_data_single.(['cop_x_' leg_char]) = nan(num_points_per_step, 1);
                                         step_data_single.(['cop_z_' leg_char]) = nan(num_points_per_step, 1);
                                         step_data_single.(['cop_y_' leg_char]) = nan(num_points_per_step, 1);
                                     end

                                elseif strcmp(var_base_raw, 'COPY_Vertical') || strcmp(var_base_raw, 'COPZ')
                                     % Do nothing - handled by COPX logic
                                else % Interpolate non-COP GRF directly
                                    step_data_single.(col_final) = interpolate_signal(raw_grf_time_slice, raw_vals, time_interp, interp_method);
                                end

                            elseif contains(var_base_raw, 'COP') % No transforms available or loaded
                                  step_data_single.(['cop_x_' leg_char]) = nan(num_points_per_step, 1);
                                  step_data_single.(['cop_z_' leg_char]) = nan(num_points_per_step, 1);
                                  step_data_single.(['cop_y_' leg_char]) = nan(num_points_per_step, 1);
                            else % Interpolate non-COP GRF directly
                                step_data_single.(col_final) = interpolate_signal(raw_grf_time_slice, raw_vals, time_interp, interp_method);
                            end
                        else
                            % Add NaN column if raw GRF column missing
                            step_data_single.(col_final) = nan(num_points_per_step, 1);
                             if contains(var_base_raw, 'COP') % Ensure all related COP NaNs are added if one raw col is missing
                                 step_data_single.(['cop_x_' leg_char]) = nan(num_points_per_step, 1);
                                 step_data_single.(['cop_y_' leg_char]) = nan(num_points_per_step, 1);
                                 step_data_single.(['cop_z_' leg_char]) = nan(num_points_per_step, 1);
                    end
                end
                        end
                    end
            else % Add NaN columns if raw GRF data file missing
                 for leg_char = ['l', 'r']
                    step_data_single.(['grf_x_' leg_char]) = nan(num_points_per_step, 1);
                    step_data_single.(['grf_y_' leg_char]) = nan(num_points_per_step, 1);
                    step_data_single.(['grf_z_' leg_char]) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_x_' leg_char]) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_y_' leg_char]) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_z_' leg_char]) = nan(num_points_per_step, 1);
                        end
                    end
                    
            % --- Assign Phase based on Leading Leg --- 
             if strcmp(leading_leg, 'r')
                step_data_single.phase_r = base_phase_step;
                step_data_single.phase_l = offset_phase_step;
            else % leading_leg == 'l'
                step_data_single.phase_l = base_phase_step;
                step_data_single.phase_r = offset_phase_step;
            end

            % --- Perform Data Swap if LR convention and Left Leg Led ---
            % This is to ensure that the right leg data is aligned to phase 0
            % and the left leg data is aligned to phase 0.5 at the start of 
            % each activity and therefore step.
            if strcmpi(naming_convention, 'lr') && strcmp(leading_leg, 'l')
                % fprintf('    Swapping L/R data for step %d to align R leg to phase 0.\n', step_idx);
                colnames = step_data_single.Properties.VariableNames;
                for i = 1:length(colnames)
                    col_l = colnames{i};
                    % Identify columns ending in '_l' that should be swapped
                    if endsWith(col_l, '_l')
                        col_r = strrep(col_l, '_l', '_r');
                        % Check if the corresponding _r column exists
                        if ismember(col_r, colnames)
                            % Swap the data content of the columns
                            temp_data = step_data_single.(col_l);
                            step_data_single.(col_l) = step_data_single.(col_r);
                            step_data_single.(col_r) = temp_data;
                            % fprintf('      Swapped %s <-> %s\n', col_l, col_r);
                        end
                    end
                end
            end

            % --- Append Step Data to Activity Table --- 
            activity_step_data = [activity_step_data; step_data_single];
        end % --- End of step loop ---

        % --- Step 5: Combine Activity Data ---
        % Increment counter if this was a critical activity and data was generated
        activity_fieldname = matlab.lang.makeValidName(activity_name);
        if isfield(critical_activity_counts, activity_fieldname) && ~isempty(activity_step_data)
            critical_activity_counts.(activity_fieldname) = critical_activity_counts.(activity_fieldname) + 1;
        end

        if ~isempty(activity_step_data)
            if isempty(subject_activity_data)
                 subject_activity_data = activity_step_data;
            else
                 % Add missing columns with NaNs before vertical concatenation
                 missing_in_subject = setdiff(activity_step_data.Properties.VariableNames, subject_activity_data.Properties.VariableNames);
                 missing_in_activity = setdiff(subject_activity_data.Properties.VariableNames, activity_step_data.Properties.VariableNames);
                 for m = 1:length(missing_in_subject)
                     col_name = missing_in_subject{m};
                     subject_activity_data.(col_name) = nan(height(subject_activity_data), 1);
                 end
                 for m = 1:length(missing_in_activity)
                      col_name = missing_in_activity{m};
                      activity_step_data.(col_name) = nan(height(activity_step_data), 1);
                 end
                 % Ensure same column order before vcat
                 try
                    activity_step_data = activity_step_data(:, subject_activity_data.Properties.VariableNames);
                    subject_activity_data = [subject_activity_data; activity_step_data];
                 catch ME_vcat
                     warning(ME_vcat.identifier, 'VCAT Error for %s (Step Data): %s. Columns might mismatch.', activity_file_name, ME_vcat.message);
                 end
            end
        end

    end % --- End of activity loop ---

    % --- Combine Subject Data into Total Data ---
    if ~isempty(subject_activity_data)
         if isempty(total_data)
             total_data = subject_activity_data;
         else
             % Add missing columns with NaNs before vertical concatenation
             missing_in_total = setdiff(subject_activity_data.Properties.VariableNames, total_data.Properties.VariableNames);
             missing_in_subject = setdiff(total_data.Properties.VariableNames, subject_activity_data.Properties.VariableNames);
              for m = 1:length(missing_in_total)
                  col_name = missing_in_total{m};
                  total_data.(col_name) = nan(height(total_data), 1);
              end
              for m = 1:length(missing_in_subject)
                   col_name = missing_in_subject{m};
                   subject_activity_data.(col_name) = nan(height(subject_activity_data), 1);
              end
              % Ensure same column order before vcat
              try
                 subject_activity_data = subject_activity_data(:, total_data.Properties.VariableNames);
                 total_data = [total_data; subject_activity_data];
              catch ME_vcat_subj
                    warning(ME_vcat_subj.identifier, 'VCAT Error for Subject %s: %s. Columns might mismatch.', subject, ME_vcat_subj.message);
              end
         end
    end

end % --- End of subject loop ---

% --- Step 6: Finalize and Save ---
if isempty(total_data)
    error('No data processed successfully. Check input files, paths, and warnings.');
end

% Report count of processed critical activities
fprintf('\n--- Processed Critical Activity Counts ---\n');
count_fields = fieldnames(critical_activity_counts);
if isempty(count_fields)
    fprintf('No critical activities were defined or processed.\n');
else
    for i = 1:length(count_fields)
        field_name = count_fields{i};
        % Attempt to map field_name back to original critical_activity name for display
        original_name = field_name; % Default
        for j = 1:length(critical_activities)
            if strcmp(matlab.lang.makeValidName(critical_activities{j}), field_name)
                original_name = critical_activities{j};
                break;
            end
        end
        fprintf('  %s: %d instances\n', original_name, critical_activity_counts.(field_name));
    end
end
fprintf('----------------------------------------\n');

combined_data = total_data;

% --- Define column renaming map (Intermediate names from interpolation -> Final names) ---
% Verify these intermediate names match the ones created in the step loop!
old_col_names_map = {...
    'knee_angle_l', 'knee_angle_r', 'knee_velocity_l', 'knee_velocity_r', 'knee_angle_l_moment', 'knee_angle_r_moment', ...
    'ankle_angle_l', 'ankle_angle_r', 'ankle_velocity_l', 'ankle_velocity_r', 'ankle_angle_l_moment', 'ankle_angle_r_moment', ...
    'calcn_l_Z', 'calcn_r_Z', ... % Example Link Angle - VERIFY ACTUAL NAME USED
    'hip_flexion_l', 'hip_flexion_r', 'hip_flexion_velocity_l', 'hip_flexion_velocity_r', 'hip_flexion_l_moment', 'hip_flexion_r_moment', ...
    'activity', ... % Source activity name used for intermediate table
    'cop_x_l', 'cop_y_l', 'cop_z_l', 'cop_x_r', 'cop_y_r', 'cop_z_r', ... % Names created during interpolation
    'grf_x_l', 'grf_y_l', 'grf_z_l', 'grf_x_r', 'grf_y_r', 'grf_z_r', ... % Names created during interpolation
    'phase_l', 'phase_r', ... % Names created during interpolation
    % Add Global angle intermediate names if they need renaming (e.g., 'foot_l_X')
    };

new_col_names_lr = {...
    'knee_angle_s_l', 'knee_angle_s_r', 'knee_vel_s_l', 'knee_vel_s_r', 'knee_torque_s_l', 'knee_torque_s_r', ...
    'ankle_angle_s_l', 'ankle_angle_s_r', 'ankle_vel_s_l', 'ankle_vel_s_r', 'ankle_torque_s_l', 'ankle_torque_s_r', ...
    'foot_angle_s_l', 'foot_angle_s_r', ... % Example Target Link Angle - VERIFY
    'hip_angle_s_l', 'hip_angle_s_r', 'hip_vel_s_l', 'hip_vel_s_r', 'hip_torque_s_l', 'hip_torque_s_r', ...
    'task', ... % Standard name for activity
    'cop_x_l', 'cop_y_l', 'cop_z_l', 'cop_x_r', 'cop_y_r', 'cop_z_r', ... % Keep simple?
    'grf_x_l', 'grf_y_l', 'grf_z_l', 'grf_x_r', 'grf_y_r', 'grf_z_r', ... % Keep simple?
    'phase_l', 'phase_r', ... % Keep final phase names standard
    % Add final global angle names
    };

new_col_names_ipsi = {...
    'knee_angle_s_ipsi', 'knee_angle_s_contra', 'knee_vel_s_ipsi', 'knee_vel_s_contra', 'knee_torque_s_ipsi', 'knee_torque_s_contra', ...
    'ankle_angle_s_ipsi', 'ankle_angle_s_contra', 'ankle_vel_s_ipsi', 'ankle_vel_s_contra', 'ankle_torque_s_ipsi', 'ankle_torque_s_contra', ...
    'foot_angle_s_ipsi', 'foot_angle_s_contra', ... % Example Target Link Angle
    'hip_angle_s_ipsi', 'hip_angle_s_contra', 'hip_vel_s_ipsi', 'hip_vel_s_contra', 'hip_torque_s_ipsi', 'hip_torque_s_contra', ...
    'task', ...
    'cop_x_ipsi', 'cop_y_ipsi', 'cop_z_ipsi', 'cop_x_contra', 'cop_y_contra', 'cop_z_contra', ...
    'grf_x_ipsi', 'grf_y_ipsi', 'grf_z_ipsi', 'grf_x_contra', 'grf_y_contra', 'grf_z_contra', ...
    'phase_ipsi', 'phase_contra', ... % Final phase column names
     % Add final global angle names
    };

% Select the final naming convention map
if strcmpi(naming_convention, 'ipsicontra')
    fprintf('Using ipsi/contra naming convention.\n');
    final_new_names_map = new_col_names_ipsi;
else
    fprintf('Using left/right naming convention.\n');
    final_new_names_map = new_col_names_lr;
end

% Ensure map lengths match
if length(old_col_names_map) ~= length(final_new_names_map)
    error('Column renaming map lengths do not match (%d vs %d). Check definitions.', length(old_col_names_map), length(final_new_names_map));
end

% Identify columns present in the data AND in the old_col_names map
present_old_cols = old_col_names_map(ismember(old_col_names_map, combined_data.Properties.VariableNames));
if ~isempty(present_old_cols)
    [~, idx_map] = ismember(present_old_cols, old_col_names_map); % Get indices in original map
    present_new_names = final_new_names_map(idx_map); % Select corresponding new names

    % Rename only the present columns
    fprintf('Renaming %d columns...\n', length(present_old_cols));
    combined_data = renamevars(combined_data, present_old_cols, present_new_names);
else
     warning('No columns found to rename based on the defined map.');
end

% Convert task data to string (if column exists after rename)
final_task_col = 'task'; % Standard name
if ismember(final_task_col, combined_data.Properties.VariableNames)
    combined_data.(final_task_col) = convertCharsToStrings(combined_data.(final_task_col));
else
    warning('Column "%s" not found after renaming. Cannot convert to string.', final_task_col);
end

% Final Check for phase columns based on naming convention
if strcmpi(naming_convention, 'ipsicontra')
     final_phase_col_1 = 'phase_ipsi'; final_phase_col_2 = 'phase_contra';
else % 'lr'
     final_phase_col_1 = 'phase_l'; final_phase_col_2 = 'phase_r';
end
if ~ismember(final_phase_col_1, combined_data.Properties.VariableNames) || ~ismember(final_phase_col_2, combined_data.Properties.VariableNames)
     warning('Final table missing expected phase columns (%s or %s)! Check interpolation and renaming.', final_phase_col_1, final_phase_col_2);
end

% Write the data to a parquet file
file_name = fullfile(output_dir, 'gtech_2023_phase_rawHS_based.parquet'); % New filename indicating source
try
    parquetwrite(file_name, combined_data);
    fprintf('Processing complete. Output saved to: %s\n', file_name);
catch ME_write
    error('Failed to write Parquet file: %s\nCheck dependencies (requires MATLAB R2021a+ or specific setup).', ME_write.message);
end

% --- END MAIN PROCESSING ---

% --- Define Helper Function for Interpolation (Moved to End) ---
function interp_data = interpolate_signal(raw_times, raw_values, target_times, method, nan_fill_val)
    % Helper to interpolate a single signal, handling missing/invalid data.
    if nargin < 5
        nan_fill_val = NaN; % Default fill value
    end
    if isempty(raw_times) || isempty(raw_values) || length(raw_times) < 2 || ~isnumeric(raw_values) || all(isnan(raw_values))
        interp_data = repmat(nan_fill_val, length(target_times), 1);
        return;
    end
    % Ensure time vectors are column vectors for interp1
    raw_times = raw_times(:);
    target_times = target_times(:);

    % Ensure unique, monotonically increasing time points for interpolation
    [unique_raw_times, ia, ~] = unique(raw_times);
    unique_raw_values = raw_values(ia,:); % Handle multi-column inputs if needed

    if length(unique_raw_times) < 2
         interp_data = repmat(nan_fill_val, length(target_times), size(unique_raw_values, 2));
         return;
    end

    % Use try-catch for interpolation robustness
    try
        interp_data = interp1(unique_raw_times, unique_raw_values, target_times, method, nan_fill_val);
    catch ME
        warning(ME.identifier, 'Interpolation failed: %s. Filling with NaNs.', ME.message);
        interp_data = repmat(nan_fill_val, length(target_times), size(unique_raw_values, 2));
    end
end
% --- End Helper Function ---