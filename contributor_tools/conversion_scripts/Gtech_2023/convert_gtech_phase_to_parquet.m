% This file is meant to convert raw Gtech 2023 data based on heel strikes
% from _parsing.mat files into a standardized phase-aligned parquet file.
%
% IMPORTANT: Before running this script, you must generate Link_Angle.csv files:
%   1. Navigate to utilities/ folder
%   2. Run convert_gtech_rotm_to_eul_csv.m to generate Link_Angle.csv and Link_Velocities.csv
%   3. These files contain segment angles in DEGREES (not radians)

% --- Step 1: Initialization & Setup ---
clear all;
close all;

num_points_per_step = 150;
naming_convention = 'ipsicontra'; % Options: 'lr', 'ipsicontra'
data_dir_root = '.'; % Assumes RawData and Segmentation are subdirs of CWD
output_dir = fullfile('..', '..', '..', 'converted_datasets'); % Output to project root
critical_activities = {'stairs', 'incline_walk', 'normal_walk', 'sit_to_stand', ...
    'stand_to_sit', 'squats', 'jump', 'step_ups', 'curb_up', 'curb_down', ...
    'walk_backward', 'weighted_walk'}; % Define tasks to convert into phase dataset

% Initialize a single table to hold all processed data
total_data = table();

% Initialize per-activity counters
critical_activity_counts = struct();
for i = 1:length(critical_activities)
    activity_fieldname = matlab.lang.makeValidName(critical_activities{i}); % Ensure valid fieldname
    critical_activity_counts.(activity_fieldname) = 0;
end
one_step_activity_count = 0; % Initialize counter for single-step activities

% Expected raw file types and their time column name
% Used for iterating through required raw files
% NOTE: Link_Angle files must be generated first using utilities/convert_gtech_rotm_to_eul_csv.m
raw_file_info = struct(...
    'Joint_Angle', 'time', ...
    'Joint_Velocities', 'time', ...
    'Joint_Moments', 'time', ...
    'Link_Angle', 'time', ...  % Segment angles from convert_gtech_rotm_to_eul_csv.m
    'Link_Velocities', 'time', ...
    'GroundFrame_GRFs', 'time' ...
);
% Note: Not using Transforms_Euler folder - contains radians, not degrees
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
    % Following naming convention: DATASET_POPULATION+NUMBER
    % GT23 = Georgia Tech 2023, AB = Able-bodied
    % Extract subject number (e.g., '01' from 'AB01')
    if startsWith(subject, 'AB')
        subject_num = subject(3:end);
    else
        subject_num = subject;
    end
    subject_save_name = strcat("GT23_AB", sprintf('%02s', subject_num));
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
                 if is_potentially_critical
                    warning('Parsing file %s found, but missing/empty heel strike data for BOTH legs. Skipping.', activity_file_name);
                 end
                raw_data_load_successful = false;
            end
        catch ME
             if is_potentially_critical
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
                         % Link_Angle and Link_Velocities are not marked as essential because we check them separately
                         if ~ismember(fname, {'Link_Angle', 'Link_Velocities'})
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
                    if ~ismember(fname, {'Link_Angle', 'Link_Velocities'})
                        essential_raw_missing = true;
                    end
                end
            catch ME
                if ismember(activity_name, critical_activities)
                    warning(ME.identifier, 'Error loading raw data file %s: %s. Will use NaNs.', file_path, ME.message);
                end
                raw_data.(fname) = [];
                 if ~ismember(fname, {'Link_Angle', 'Link_Velocities'})
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
            % Both left and right data are valid.
            % Determine leading leg by comparing amount of data (number of heel strikes).
            num_hs_l = size(parsing_data.left, 1);
            num_hs_r = size(parsing_data.right, 1);

            if num_hs_l > num_hs_r
                leading_leg = 'l';
                leading_hs_times = parsing_data.left;
                fprintf('    Leading Leg: %s (Based on HS count: L=%d > R=%d)\n', leading_leg, num_hs_l, num_hs_r);
            elseif num_hs_r > num_hs_l
                leading_leg = 'r';
                leading_hs_times = parsing_data.right;
                 fprintf('    Leading Leg: %s (Based on HS count: R=%d > L=%d)\n', leading_leg, num_hs_r, num_hs_l);
            else % Tie in number of heel strikes, use first timestamp as tie-breaker
                first_hs_l = parsing_data.left(1,1);
                first_hs_r = parsing_data.right(1,1);
                if first_hs_l <= first_hs_r
                    leading_leg = 'l';
                    leading_hs_times = parsing_data.left;
                else
                    leading_leg = 'r';
                    leading_hs_times = parsing_data.right;
                end
                fprintf('    Leading Leg: %s (Based on first HS time tie-breaker: L=%d, R=%d)\n', leading_leg, num_hs_l, num_hs_r);
            end
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
            
            % Use standardized task mapping function
            [task_name, task_id, task_info_str] = parse_gtech_activity_matlab(activity_name, sub_activity_name);
            
            step_data_single.task = repmat({task_name}, num_points_per_step, 1);
            step_data_single.task_id = repmat({task_id}, num_points_per_step, 1);
            step_data_single.task_info = repmat({task_info_str}, num_points_per_step, 1);
            
            % Add subject_metadata column (empty for now)
            step_data_single.subject_metadata = repmat({''}, num_points_per_step, 1);
            step_data_single.leading_leg_step = repmat({leading_leg}, num_points_per_step, 1); % Add leading leg marker
            step_data_single.step = repmat(step_idx, num_points_per_step, 1);

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

            % --- Interpolate Link Angles (Segment Angles) ---
            % Process all segment angles: pelvis, femur (thigh), tibia (shank), calcn (foot)
            link_angle_cols_to_process = {
                'pelvis_X', 'pelvis_Y', 'pelvis_Z', ...  % Pelvis angles
                'femur_l_X', 'femur_l_Y', 'femur_l_Z', ... % Left thigh
                'femur_r_X', 'femur_r_Y', 'femur_r_Z', ... % Right thigh
                'tibia_l_X', 'tibia_l_Y', 'tibia_l_Z', ... % Left shank
                'tibia_r_X', 'tibia_r_Y', 'tibia_r_Z', ... % Right shank
                'calcn_l_X', 'calcn_l_Y', 'calcn_l_Z', ... % Left foot
                'calcn_r_X', 'calcn_r_Y', 'calcn_r_Z'  % Right foot
            };
            
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
            
            % --- Foot angle already interpolated, no velocity calculation needed ---
            
            % --- Not using Transforms_Euler - segment angles come from Link_Angle.csv ---
            % Transforms_Euler folder contains angles in radians, while Link_Angle.csv
            % (generated by convert_gtech_rotm_to_eul_csv.m) contains angles in degrees
            % which matches what the rest of the script expects

            % --- Interpolate GRF & Transform COP ---
            % Using standardized directional naming with ipsi/contra mapping
            grf_cols_base = {'ForceX', 'ForceY_Vertical', 'ForceZ', 'COPX', 'COPY_Vertical', 'COPZ'};
            % Map to standardized names: anterior (X), vertical (Y), lateral (Z)
            grf_cols_standardized = {'anterior_grf', 'vertical_grf', 'lateral_grf', 'cop_anterior', 'cop_vertical', 'cop_lateral'};
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
                    % Determine ipsi/contra suffix based on leading leg
                    if strcmp(leading_leg, leg_char)
                        ipsi_contra_suffix = '_ipsi';
                    else
                        ipsi_contra_suffix = '_contra';
                    end
                    
                    for v = 1:length(grf_cols_base)
                        var_base_raw = grf_cols_base{v};
                        col_raw = [upper(leg_char) var_base_raw]; % e.g., LForceX, RCOPZ
                        
                        % Create standardized column name with ipsi/contra and units
                        standardized_base = grf_cols_standardized{v};
                        if contains(standardized_base, 'grf')
                            col_final = [standardized_base ipsi_contra_suffix '_N']; % e.g., grf_anterior_ipsi_N
                        else % COP variables
                            col_final = [standardized_base ipsi_contra_suffix '_m']; % e.g., cop_anterior_ipsi_m
                        end

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
                                         % Use standardized column names with ipsi/contra
                                         step_data_single.(['cop_anterior' ipsi_contra_suffix '_m']) = interpolate_signal(raw_grf_time_slice, cop_local_x, time_interp, interp_method);
                                         step_data_single.(['cop_lateral' ipsi_contra_suffix '_m']) = interpolate_signal(raw_grf_time_slice, cop_local_z, time_interp, interp_method);
                                         step_data_single.(['cop_vertical' ipsi_contra_suffix '_m']) = zeros(num_points_per_step, 1); % Assume zero vertical COP in local frame
                                     else % Not enough transform data or length mismatch
                                         if ismember(activity_name, critical_activities)
                                             warning('Transform data issue for step %d. Cannot transform COP.', step_idx);
                                         end
                                         % Use standardized column names with ipsi/contra for NaN case
                                         step_data_single.(['cop_anterior' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                         step_data_single.(['cop_lateral' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                         step_data_single.(['cop_vertical' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                     end

                                elseif strcmp(var_base_raw, 'COPY_Vertical') || strcmp(var_base_raw, 'COPZ')
                                     % Do nothing - handled by COPX logic
                                else % Interpolate non-COP GRF directly
                                    step_data_single.(col_final) = interpolate_signal(raw_grf_time_slice, raw_vals, time_interp, interp_method);
                                end

                            elseif contains(var_base_raw, 'COP') % No transforms available or loaded
                                  % Use standardized column names for COP when no transforms available
                                  step_data_single.(['cop_anterior' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                  step_data_single.(['cop_lateral' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                  step_data_single.(['cop_vertical' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                            else % Interpolate non-COP GRF directly
                                step_data_single.(col_final) = interpolate_signal(raw_grf_time_slice, raw_vals, time_interp, interp_method);
                            end
                        else
                            % Add NaN column if raw GRF column missing
                            step_data_single.(col_final) = nan(num_points_per_step, 1);
                             if contains(var_base_raw, 'COP') % Ensure all related COP NaNs are added if one raw col is missing
                                 % Use standardized column names for missing COP data
                                 step_data_single.(['cop_anterior' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                 step_data_single.(['cop_vertical' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                                 step_data_single.(['cop_lateral' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                    end
                end
                        end
                    end
            else % Add NaN columns if raw GRF data file missing
                 for leg_char = ['l', 'r']
                    % Determine ipsi/contra suffix for this leg
                    if strcmp(leading_leg, leg_char)
                        ipsi_contra_suffix = '_ipsi';
                    else
                        ipsi_contra_suffix = '_contra';
                    end
                    
                    % Use standardized column names for missing GRF/COP data
                    step_data_single.(['anterior_grf' ipsi_contra_suffix '_N']) = nan(num_points_per_step, 1);
                    step_data_single.(['vertical_grf' ipsi_contra_suffix '_N']) = nan(num_points_per_step, 1);
                    step_data_single.(['lateral_grf' ipsi_contra_suffix '_N']) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_anterior' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_vertical' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                    step_data_single.(['cop_lateral' ipsi_contra_suffix '_m']) = nan(num_points_per_step, 1);
                        end
                    end
                    
            % --- Assign Phase based on Leading Leg and Naming Convention --- 
            if strcmpi(naming_convention, 'ipsicontra')
                % For ipsi/contra, ipsi is always the leading leg at phase 0
                step_data_single.phase_ipsi = base_phase_step;
                % Store which anatomical leg is ipsi for this step
                step_data_single.ipsi_is_left = repmat(strcmp(leading_leg, 'l'), num_points_per_step, 1);
            else
                % For left/right naming
                if strcmp(leading_leg, 'r')
                    step_data_single.phase_r = base_phase_step;
                    step_data_single.phase_l = offset_phase_step;
                else % leading_leg == 'l'
                    step_data_single.phase_l = base_phase_step;
                    step_data_single.phase_r = offset_phase_step;
                end
            end

            % --- Perform Data Swap if LR convention and Ipsilateral Leg Led ---
            % This is to ensure that the right leg data is aligned to phase 0
            % and the left leg data is aligned to phase 0.5 at the start of 
            % each activity and therefore step.
            if strcmpi(naming_convention, 'lr') && strcmp(leading_leg, 'l')
                % fprintf('    Swapping L/R data for step %d to align R leg to phase 0.\n', step_idx);
                colnames = step_data_single.Properties.VariableNames;
                for i = 1:length(colnames)
                    col_l = colnames{i};
                    % Identify columns ending in '_l' that should be swapped
                    if contains(col_l, '_l')
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

        % --- Check if only one step was processed for this activity ---
        if num_steps == 1 && ~isempty(activity_step_data)
            one_step_activity_count = one_step_activity_count + 1;
        end

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
fprintf('Total number of subjects processed: %d\n', length(subjects));
fprintf('Total number of activity instances resulting in exactly one processed step: %d\n', one_step_activity_count);

combined_data = total_data;

% --- Column Renaming Strategy for Ipsi/Contra ---
if strcmpi(naming_convention, 'ipsicontra')
    fprintf('Using ipsi/contra naming convention with dynamic mapping based on leading leg.\n');
    
    % For ipsi/contra naming, we need to dynamically map L/R to ipsi/contra
    % based on which leg was leading for each step
    
    % First, do standard renaming for non-lateralized variables
    standard_renames = {...
        'activity', 'task'; ...
        'phase_ipsi', 'phase_ipsi'; ...  % Already created as phase_ipsi
        'step', 'step'; ...
        'pelvis_Z', 'pelvis_sagittal_angle_rad'; ...  % Pelvis sagittal
        'pelvis_X', 'pelvis_frontal_angle_rad'; ...   % Pelvis frontal
        'pelvis_Y', 'pelvis_transverse_angle_rad'     % Pelvis transverse
    };
    
    for i = 1:size(standard_renames, 1)
        old_name = standard_renames{i, 1};
        new_name = standard_renames{i, 2};
        if ismember(old_name, combined_data.Properties.VariableNames)
            combined_data = renamevars(combined_data, old_name, new_name);
        end
    end
    
    % Now handle lateralized variables with dynamic ipsi/contra mapping
    % We need to swap data based on the ipsi_is_left flag
    
    % Define variable patterns to process
    lateralized_patterns = {
        'knee_angle', 'knee_flexion_angle', '_rad';
        'knee_velocity', 'knee_flexion_velocity', '_rad_s';
        'knee_angle_l_moment', 'knee_flexion_moment', '_Nm';
        'knee_angle_r_moment', 'knee_flexion_moment', '_Nm';
        'ankle_angle', 'ankle_dorsiflexion_angle', '_rad';
        'ankle_velocity', 'ankle_dorsiflexion_velocity', '_rad_s';
        'ankle_angle_l_moment', 'ankle_dorsiflexion_moment', '_Nm';
        'ankle_angle_r_moment', 'ankle_dorsiflexion_moment', '_Nm';
        'hip_flexion', 'hip_flexion_angle', '_rad';
        'hip_flexion_velocity', 'hip_flexion_velocity', '_rad_s';
        'hip_flexion_l_moment', 'hip_flexion_moment', '_Nm';
        'hip_flexion_r_moment', 'hip_flexion_moment', '_Nm';
        % Segment angles - sagittal plane (Z is sagittal in Gtech convention)
        'femur_l_Z', 'thigh_sagittal_angle_ipsi', '_rad';
        'femur_r_Z', 'thigh_sagittal_angle_contra', '_rad';
        'tibia_l_Z', 'shank_sagittal_angle_ipsi', '_rad';
        'tibia_r_Z', 'shank_sagittal_angle_contra', '_rad';
        'calcn_l_Z', 'foot_sagittal_angle_ipsi', '_rad';
        'calcn_r_Z', 'foot_sagittal_angle_contra', '_rad';
        % Segment angles - frontal plane (X is frontal)
        'femur_l_X', 'thigh_frontal_angle_ipsi', '_rad';
        'femur_r_X', 'thigh_frontal_angle_contra', '_rad';
        'tibia_l_X', 'shank_frontal_angle_ipsi', '_rad';
        'tibia_r_X', 'shank_frontal_angle_contra', '_rad';
        'calcn_l_X', 'foot_frontal_angle_ipsi', '_rad';
        'calcn_r_X', 'foot_frontal_angle_contra', '_rad';
        % Segment angles - transverse plane (Y is transverse)
        'femur_l_Y', 'thigh_transverse_angle_ipsi', '_rad';
        'femur_r_Y', 'thigh_transverse_angle_contra', '_rad';
        'tibia_l_Y', 'shank_transverse_angle_ipsi', '_rad';
        'tibia_r_Y', 'shank_transverse_angle_contra', '_rad';
        'calcn_l_Y', 'foot_transverse_angle_ipsi', '_rad';
        'calcn_r_Y', 'foot_transverse_angle_contra', '_rad';
        % GRF and COP (rename to standardized anterior/lateral/vertical)
        'cop_x', 'cop_anterior', '_m';
        'cop_y', 'cop_vertical', '_m';
        'cop_z', 'cop_lateral', '_m';
        'grf_x', 'anterior_grf', '_N';
        'grf_y', 'vertical_grf', '_N';
        'grf_z', 'lateral_grf', '_N'
    };
    
    % Process each lateralized variable
    for i = 1:size(lateralized_patterns, 1)
        old_base = lateralized_patterns{i, 1};
        new_base = lateralized_patterns{i, 2};
        suffix = lateralized_patterns{i, 3};
        
        % Handle special cases for segment angles where L/R is embedded in the name
        if contains(old_base, 'femur_') || contains(old_base, 'tibia_') || contains(old_base, 'calcn_')
            % For segment angles, L/R is already in the base name
            col_l = old_base;  % e.g., 'femur_l_Z'
            col_r = strrep(old_base, '_l_', '_r_');  % e.g., 'femur_r_Z'
            
            % For segment angles, the new names already include ipsi/contra
            col_ipsi = new_base;  % e.g., 'thigh_sagittal_angle_ipsi'
            col_contra = strrep(new_base, '_ipsi', '_contra');  % e.g., 'thigh_sagittal_angle_contra'
            % Add the suffix (e.g., '_rad')
            col_ipsi = [col_ipsi suffix];
            col_contra = [col_contra suffix];
        elseif contains(old_base, '_moment')
            % Handle moments
            col_l = old_base;
            col_r = strrep(old_base, '_l_', '_r_');
            col_ipsi = [new_base '_ipsi' suffix];
            col_contra = [new_base '_contra' suffix];
        else
            % Standard pattern: append _l and _r
            col_l = [old_base '_l'];
            col_r = [old_base '_r'];
            col_ipsi = [new_base '_ipsi' suffix];
            col_contra = [new_base '_contra' suffix];
        end
        
        % Check if both L and R columns exist
        if ismember(col_l, combined_data.Properties.VariableNames) && ...
           ismember(col_r, combined_data.Properties.VariableNames)
            
            % Create ipsi and contra columns based on leading leg
            combined_data.(col_ipsi) = zeros(height(combined_data), 1);
            combined_data.(col_contra) = zeros(height(combined_data), 1);
            
            % When ipsi_is_left is true (left leg leading): L->ipsi, R->contra
            % When ipsi_is_left is false (right leg leading): R->ipsi, L->contra
            if ismember('ipsi_is_left', combined_data.Properties.VariableNames)
                left_leading_idx = combined_data.ipsi_is_left == 1;
                right_leading_idx = combined_data.ipsi_is_left == 0;
                
                combined_data.(col_ipsi)(left_leading_idx) = combined_data.(col_l)(left_leading_idx);
                combined_data.(col_contra)(left_leading_idx) = combined_data.(col_r)(left_leading_idx);
                
                combined_data.(col_ipsi)(right_leading_idx) = combined_data.(col_r)(right_leading_idx);
                combined_data.(col_contra)(right_leading_idx) = combined_data.(col_l)(right_leading_idx);
            else
                % Fallback: simple L->ipsi, R->contra if ipsi_is_left not found
                warning('ipsi_is_left column not found, using simple L->ipsi mapping');
                combined_data.(col_ipsi) = combined_data.(col_l);
                combined_data.(col_contra) = combined_data.(col_r);
            end
            
            % Remove the original L/R columns
            combined_data = removevars(combined_data, {col_l, col_r});
            
            fprintf('  Mapped %s/%s -> %s/%s\n', col_l, col_r, col_ipsi, col_contra);
        end
    end
    
    % Remove the helper column
    if ismember('ipsi_is_left', combined_data.Properties.VariableNames)
        combined_data = removevars(combined_data, 'ipsi_is_left');
    end
    
else
    % Standard L/R renaming (existing code)
    fprintf('Using left/right naming convention.\n');
    
    % Define column renaming map
    old_col_names_map = {...
        'knee_angle_l', 'knee_angle_r', 'knee_velocity_l', 'knee_velocity_r', 'knee_angle_l_moment', 'knee_angle_r_moment', ...
        'ankle_angle_l', 'ankle_angle_r', 'ankle_velocity_l', 'ankle_velocity_r', 'ankle_angle_l_moment', 'ankle_angle_r_moment', ...
        'calcn_l_Z', 'calcn_r_Z', ...
        'hip_flexion_l', 'hip_flexion_r', 'hip_flexion_velocity_l', 'hip_flexion_velocity_r', 'hip_flexion_l_moment', 'hip_flexion_r_moment', ...
        'activity', ...
        'cop_x_l', 'cop_y_l', 'cop_z_l', 'cop_x_r', 'cop_y_r', 'cop_z_r', ...
        'grf_x_l', 'grf_y_l', 'grf_z_l', 'grf_x_r', 'grf_y_r', 'grf_z_r', ...
        'phase_l', 'phase_r', 'step'
    };
    
    new_col_names_lr = {...
        'knee_flexion_angle_l_rad', 'knee_flexion_angle_r_rad', 'knee_flexion_velocity_l_rad_s', 'knee_flexion_velocity_r_rad_s', 'knee_flexion_moment_l_Nm', 'knee_flexion_moment_r_Nm', ...
        'ankle_dorsiflexion_angle_l_rad', 'ankle_dorsiflexion_angle_r_rad', 'ankle_dorsiflexion_velocity_l_rad_s', 'ankle_dorsiflexion_velocity_r_rad_s', 'ankle_dorsiflexion_moment_l_Nm', 'ankle_dorsiflexion_moment_r_Nm', ...
        'foot_sagittal_angle_l_rad', 'foot_sagittal_angle_r_rad', ...
        'hip_flexion_angle_l_rad', 'hip_flexion_angle_r_rad', 'hip_flexion_velocity_l_rad_s', 'hip_flexion_velocity_r_rad_s', 'hip_flexion_moment_l_Nm', 'hip_flexion_moment_r_Nm', ...
        'task', ...
        'cop_anterior_l_m', 'cop_vertical_l_m', 'cop_lateral_l_m', ...
        'cop_anterior_r_m', 'cop_vertical_r_m', 'cop_lateral_r_m', ...
        'grf_anterior_l_N', 'grf_vertical_l_N', 'grf_lateral_l_N', ...
        'grf_anterior_r_N', 'grf_vertical_r_N', 'grf_lateral_r_N', ...
        'phase_l', 'phase_r', 'step'
    };
    
    % Rename columns
    present_old_cols = old_col_names_map(ismember(old_col_names_map, combined_data.Properties.VariableNames));
    if ~isempty(present_old_cols)
        [~, idx_map] = ismember(present_old_cols, old_col_names_map);
        present_new_names = new_col_names_lr(idx_map);
        fprintf('Renaming %d columns...\n', length(present_old_cols));
        combined_data = renamevars(combined_data, present_old_cols, present_new_names);
    end
end

% --- Convert joint and segment angles from degrees to radians ---
fprintf('Converting joint and segment angles from degrees to radians...\n');

% Define the joint angle and velocity columns to convert based on naming convention
if strcmpi(naming_convention, 'ipsicontra')
    % Joint angle columns
    joint_angle_cols = {
        'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad', ...
        'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', ...
        'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
    };
    
    % Joint velocity columns  
    joint_velocity_cols = {
        'hip_flexion_velocity_ipsi_rad_s', 'hip_flexion_velocity_contra_rad_s', ...
        'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s', ...
        'ankle_dorsiflexion_velocity_ipsi_rad_s', 'ankle_dorsiflexion_velocity_contra_rad_s'
    };
    
    % Segment angle columns (all planes)
    segment_angle_cols = {
        'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad', ...
        'thigh_sagittal_angle_ipsi_rad', 'thigh_sagittal_angle_contra_rad', ...
        'thigh_frontal_angle_ipsi_rad', 'thigh_frontal_angle_contra_rad', ...
        'thigh_transverse_angle_ipsi_rad', 'thigh_transverse_angle_contra_rad', ...
        'shank_sagittal_angle_ipsi_rad', 'shank_sagittal_angle_contra_rad', ...
        'shank_frontal_angle_ipsi_rad', 'shank_frontal_angle_contra_rad', ...
        'shank_transverse_angle_ipsi_rad', 'shank_transverse_angle_contra_rad', ...
        'foot_sagittal_angle_ipsi_rad', 'foot_sagittal_angle_contra_rad', ...
        'foot_frontal_angle_ipsi_rad', 'foot_frontal_angle_contra_rad', ...
        'foot_transverse_angle_ipsi_rad', 'foot_transverse_angle_contra_rad'
    };
else % 'lr' naming convention
    % Joint angle columns
    joint_angle_cols = {
        'hip_flexion_angle_l_rad', 'hip_flexion_angle_r_rad', ...
        'knee_flexion_angle_l_rad', 'knee_flexion_angle_r_rad', ...
        'ankle_dorsiflexion_angle_l_rad', 'ankle_dorsiflexion_angle_r_rad'
    };
    
    % Joint velocity columns
    joint_velocity_cols = {
        'hip_flexion_velocity_l_rad_s', 'hip_flexion_velocity_r_rad_s', ...
        'knee_flexion_velocity_l_rad_s', 'knee_flexion_velocity_r_rad_s', ...
        'ankle_dorsiflexion_velocity_l_rad_s', 'ankle_dorsiflexion_velocity_r_rad_s'
    };
    
    % Segment angle columns (all planes)
    segment_angle_cols = {
        'pelvis_sagittal_angle_rad', 'pelvis_frontal_angle_rad', 'pelvis_transverse_angle_rad', ...
        'thigh_sagittal_angle_l_rad', 'thigh_sagittal_angle_r_rad', ...
        'thigh_frontal_angle_l_rad', 'thigh_frontal_angle_r_rad', ...
        'thigh_transverse_angle_l_rad', 'thigh_transverse_angle_r_rad', ...
        'shank_sagittal_angle_l_rad', 'shank_sagittal_angle_r_rad', ...
        'shank_frontal_angle_l_rad', 'shank_frontal_angle_r_rad', ...
        'shank_transverse_angle_l_rad', 'shank_transverse_angle_r_rad', ...
        'foot_sagittal_angle_l_rad', 'foot_sagittal_angle_r_rad', ...
        'foot_frontal_angle_l_rad', 'foot_frontal_angle_r_rad', ...
        'foot_transverse_angle_l_rad', 'foot_transverse_angle_r_rad'
    };
end

% Convert joint angles from degrees to radians
for i = 1:length(joint_angle_cols)
    col_name = joint_angle_cols{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = combined_data.(col_name) * (pi/180);
        fprintf('  Converted %s from degrees to radians\n', col_name);
    end
end

% Convert joint velocities from deg/s to rad/s
for i = 1:length(joint_velocity_cols)
    col_name = joint_velocity_cols{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = combined_data.(col_name) * (pi/180);
        fprintf('  Converted %s from deg/s to rad/s\n', col_name);
    end
end

% Convert segment angles from degrees to radians
for i = 1:length(segment_angle_cols)
    col_name = segment_angle_cols{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = combined_data.(col_name) * (pi/180);
        fprintf('  Converted %s from degrees to radians\n', col_name);
    end
end

% --- Post-Processing: Apply Standard Corrections ---
fprintf('\n--- Applying post-processing corrections ---\n');

% 1. Fix knee angle sign convention (positive = flexion)
% In the Gtech data, knee angles appear to be negative for flexion
% We need to flip the sign to match the standard convention
if strcmpi(naming_convention, 'ipsicontra')
    knee_angle_cols_to_flip = {
        'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad'
    };
    knee_velocity_cols_to_flip = {
        'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s'
    };
    knee_moment_cols_to_flip = {
        'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm'
    };
    % Ankle angles also need flipping (positive = dorsiflexion)
    ankle_angle_cols_to_flip = {
        'ankle_dorsiflexion_angle_ipsi_rad', 'ankle_dorsiflexion_angle_contra_rad'
    };
    ankle_velocity_cols_to_flip = {
        'ankle_dorsiflexion_velocity_ipsi_rad_s', 'ankle_dorsiflexion_velocity_contra_rad_s'
    };
    % Note: Ankle moments should NOT be flipped
else
    knee_angle_cols_to_flip = {
        'knee_flexion_angle_l_rad', 'knee_flexion_angle_r_rad'
    };
    knee_velocity_cols_to_flip = {
        'knee_flexion_velocity_l_rad_s', 'knee_flexion_velocity_r_rad_s'
    };
    knee_moment_cols_to_flip = {
        'knee_flexion_moment_l_Nm', 'knee_flexion_moment_r_Nm'
    };
    ankle_angle_cols_to_flip = {
        'ankle_dorsiflexion_angle_l_rad', 'ankle_dorsiflexion_angle_r_rad'
    };
    ankle_velocity_cols_to_flip = {
        'ankle_dorsiflexion_velocity_l_rad_s', 'ankle_dorsiflexion_velocity_r_rad_s'
    };
    % Note: Ankle moments should NOT be flipped
end

% Flip knee angle signs
for i = 1:length(knee_angle_cols_to_flip)
    col_name = knee_angle_cols_to_flip{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = -1 * combined_data.(col_name);
        fprintf('  Flipped sign for %s (positive = flexion)\n', col_name);
    end
end

% Flip knee velocity signs to match angle convention
for i = 1:length(knee_velocity_cols_to_flip)
    col_name = knee_velocity_cols_to_flip{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = -1 * combined_data.(col_name);
        fprintf('  Flipped sign for %s to match angle convention\n', col_name);
    end
end

% Flip knee moment signs to match angle convention
for i = 1:length(knee_moment_cols_to_flip)
    col_name = knee_moment_cols_to_flip{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = -1 * combined_data.(col_name);
        fprintf('  Flipped sign for %s to match angle convention\n', col_name);
    end
end

% Flip ankle angle signs (positive = dorsiflexion)
for i = 1:length(ankle_angle_cols_to_flip)
    col_name = ankle_angle_cols_to_flip{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = -1 * combined_data.(col_name);
        fprintf('  Flipped sign for %s (positive = dorsiflexion)\n', col_name);
    end
end

% Flip ankle velocity signs to match angle convention
for i = 1:length(ankle_velocity_cols_to_flip)
    col_name = ankle_velocity_cols_to_flip{i};
    if ismember(col_name, combined_data.Properties.VariableNames)
        combined_data.(col_name) = -1 * combined_data.(col_name);
        fprintf('  Flipped sign for %s to match angle convention\n', col_name);
    end
end

% Note: Ankle moments should NOT be flipped - only angles and velocities

% 2. Check for and remove duplicate rows
initial_rows = height(combined_data);
[~, unique_idx] = unique(combined_data(:, {'subject', 'task', 'step', 'phase_ipsi'}), 'rows', 'stable');
if length(unique_idx) < initial_rows
    combined_data = combined_data(unique_idx, :);
    fprintf('  Removed %d duplicate rows\n', initial_rows - length(unique_idx));
else
    fprintf('  No duplicate rows found\n');
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
     final_phase_col_1 = 'phase_ipsi'; % Only need ipsi phase (contra is redundant)
     if ~ismember(final_phase_col_1, combined_data.Properties.VariableNames)
         warning('Final table missing expected phase column (%s)! Check interpolation and renaming.', final_phase_col_1);
     end
else % 'lr'
     final_phase_col_1 = 'phase_l'; 
     final_phase_col_2 = 'phase_r';
     if ~ismember(final_phase_col_1, combined_data.Properties.VariableNames) || ~ismember(final_phase_col_2, combined_data.Properties.VariableNames)
         warning('Final table missing expected phase columns (%s or %s)! Check interpolation and renaming.', final_phase_col_1, final_phase_col_2);
     end
end

% Write the data to a parquet file
file_name = fullfile(output_dir, 'gtech_2023_phase_raw.parquet'); % New filename indicating source
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
