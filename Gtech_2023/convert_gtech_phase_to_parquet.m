% This file is meant to convert the data from the .mat file to a .parquet file
% for the Segmented dataset of the Georgia tech non-cylic dataset. 

% The file structure is as follows:
% "Segmentation"/{Subject}/{activity_name}.mat
% activity_name = {activity}_{activity_number}_{subactivity_name}_segmented

clear all;
close all;

% All the data will be interpolated to 150 datapoints per step
num_points_per_step = 150;

% The data will be saved in one large parquet file. To create it, we will 
% start with a table and build it up as we iterate through the data.
total_data = struct();
total_data.r = table();
total_data.l = table();

% The legs that we will iterate through
legs = {'r', 'l'};

% Iterate through all the data
data_dir = 'Segmentation';
output_dir = 'ParquetData';
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

% Get all the subjects
subjects = dir(data_dir);
subjects = subjects(3:end); % remove . and ..

% Iterate through all the subjects
for subject_idx = 1:length(subjects)
% for subject_idx = 1:2

    % Get the subject name
    subject = subjects(subject_idx).name
    subject_save_name = strcat("Gtech_2023_",subject);
    subject_dir = fullfile(data_dir, subject);
    activities = dir(subject_dir);
    activities = activities(3:end); % remove . and ..
    
    % Create a progress indicator
    num_activities = length(activities);
    fprintf('Processing activities for subject %s:\n', subject);

    % Iterate through all the activities
    for activity_idx = 1:length(activities)
        % Get the activity name
        activity = activities(activity_idx).name;
        fprintf('Processing %d/%d (%3d%%): %s\r', ...
                activity_idx, num_activities, ...
                round(activity_idx/num_activities * 100), activity);
        
        % Create a variable to store the data for the activity
        activity_data = struct();
        activity_data.r = [];
        activity_data.l = [];
        
        % If the activity has segmented in it's name, then we process it
        if ~contains(activity, 'segmented')
            continue;
        end
        
        % Get the file path and load the data
        activity_dir = fullfile(subject_dir, activity);
        data = load(activity_dir);
        
        % Get the activity name. This is found as the string that occurs 
        % before the first integer in the activity name
        activity_name = strsplit(activity, '.'); % remove the .mat
        activity_name = activity_name{1};
        activity_name_split = strsplit(activity_name, '_');
        % Find the first substring that is not a number. The activity name
        % is the combination of substrings before that point
        for substring_idx = 1:length(activity_name)
            % If the substring is not a number, then we have found the
            % activity name
            if ~isnan(str2double(activity_name_split{substring_idx}))
                activity_name = ...
                    strjoin(activity_name_split(1:substring_idx-1), '_');
                activity_number = ...
                    str2double(activity_name_split{substring_idx});
                sub_activity_name = ...
                    strjoin(activity_name_split(substring_idx+1:end), '_');
                break;
            end
        end

        % We need to obtain the foot angles from the data. We need to 
        % get these from a different csv file that is located in raw data
        % directory. Once we get the csv file, we need to match the time
        % axis of the csv file with the time axis of the data. Then we can
        % interpolate the data to 150 points per step.
        
        % For stairs, we need to get the first character of the subactivity
        % as a number to get the correct file
        if strcmp(activity_name, 'stairs')
           
            % Try to parse with two digits
            stair_num = str2double(sub_activity_name(1:2));
            % If this fails, try to parse with one digit
            if isnan(stair_num)
                stair_num = sub_activity_name(1);
            end
            %If both fail just skip this activity as a whole since 
            % I don't understand how to parse these activities.            
            if isnan(str2double(stair_num))
                continue;
            end
            global_file_name = fullfile('RawData', subject,...
                'Transforms_Euler',...
                [activity_name '_' int2str(activity_number) '_' stair_num '.csv']);
        
        % For step ups, we don't need the activity number if it is only 1
        elseif strcmp(activity_name, 'step_ups') && activity_number == 1
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler', 'step_ups.csv');
        
        % For jump, see if there is another number as the first character
        % of the subactivity name. If so, use that number to get the file
        elseif strcmp(activity_name, 'jump') && activity_number == 1 && ...
                ~isnan(str2double(sub_activity_name(1))) && ...
                str2double(sub_activity_name(1)) == 2
            jump_num = sub_activity_name(1);
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler', ...
                [activity_name '_' int2str(activity_number) '_' jump_num '.csv']);
        else
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler',...
                [activity_name '_' int2str(activity_number) '.csv']);
        end
        
        % Read the csv that contains the global angles
        global_raw_data = readtable(global_file_name);
        global_angles_time = global_raw_data.Header; % Get the time axis
        
        % Verify how many data points each leg has. Sometimes the data
        % for one leg is missing. In that case, we will nan-fill the data
        % for that leg. If both legs are missing, we will skip the file.
        num_steps = struct();
        num_steps.r = length(data.angle.data_r);  
        num_steps.l = length(data.angle.data_l);

        % The processing is split into three edge cases, depending on the 
        % number of steps for each leg. First case is if both legs are missing,
        % in which case we skip the file. Second case is if one leg is missing,
        % in which case we will nan-fill the data for that leg. Third case is
        % if one leg has more data than the other, in which case we will nan
        % fill the data for the leg with less data.

        % Case 1: If both legs are missing, we just exit the code
        if num_steps.r == 0 && num_steps.l == 0
            continue;
        end

        % Case 2: Attempt to process the data, skip a leg if it is missing
        for l_idx = 1:length(legs)
            
            leg = legs{l_idx};
            
            % Skip the leg if it has no data
            if num_steps.(leg) == 0
                continue;
            end

            % Get the data
            angle_data = data.angle.(['data_' leg]);
            moment_data = data.moment_filt.(['data_' leg]);
            velocity_data = data.velocity.(['data_' leg]);

            % Process each step for a given activity
            for step_idx = 1:num_steps.(leg)
                
                % Create the table for the step
                % Initialize with the subject, activity, and subactivity
                table_data = table();
                table_data.subject = ...
                    repmat(subject_save_name, num_points_per_step, 1);
                table_data.activity = ...
                    repmat({activity_name}, num_points_per_step, 1);
                table_data.task_info = ...
                    repmat({sub_activity_name}, num_points_per_step, 1);
                table_data.activity_number = ...
                    repmat(activity_number, num_points_per_step, 1);

                % Add time, interpolated to 150 data points
                step_time = angle_data(step_idx).time;
                time_interp = interp1(...
                    1:length(angle_data(step_idx).time), ...
                    step_time, ...
                    linspace(1, length(angle_data(step_idx).time), 150),"cubic")';
                table_data.(['time_' leg]) = time_interp;
                
                % Get all the fields that we want to process
                angle_fields = fieldnames(angle_data(step_idx).data);
                vel_fields = fieldnames(velocity_data(step_idx).data);
                moment_fields = fieldnames(moment_data(step_idx).data);
                global_fields = fieldnames(global_raw_data);
                
                % remove the 'properties', 'row', and 'Variables' fields
                angle_fields = angle_fields(~ismember(angle_fields, ...
                    {'Properties', 'Row', 'Variables'}));
                vel_fields = vel_fields(~ismember(vel_fields, ...
                    {'Properties', 'Row', 'Variables'}));
                moment_fields = moment_fields(~ismember(moment_fields, ...
                    {'Properties', 'Row', 'Variables'}));
                global_fields = global_fields(~ismember(global_fields, ...
                    {'Properties', 'Row', 'Variables'}));
                
                % Process Angles
                for field_idx = 1:length(angle_fields)
                    % Get the field and it's corresponding data
                    field = angle_fields{field_idx};
                    field_data = angle_data(step_idx).data.(field);
                    
                    % Interpolate to make each step 150 data points long
                    field_data_interp = interp1(1:length(field_data), ...
                        field_data, linspace(1, length(field_data), 150),"cubic")';
                    
                    % Add the data to the table
                    table_data.(field) = field_data_interp;
                end

                % Process Velocities
                for field_idx = 1:length(vel_fields)
                    % Get the field and it's corresponding data
                    field = vel_fields{field_idx};
                    field_data = velocity_data(step_idx).data.(field);
                    
                    % Interpolate to make each step 150 data points long
                    field_data_interp = interp1(1:length(field_data), ...
                        field_data, linspace(1, length(field_data), 150),"cubic")';
                    
                    % Add the data to the table
                    table_data.(field) = field_data_interp;
                end

                % Process Moments
                for field_idx = 1:length(moment_fields)
                    % Get the field and it's corresponding data
                    field = moment_fields{field_idx};
                    field_data = moment_data(step_idx).data.(field);
                    
                    % Interpolate to make each step 150 data points long
                    field_data_interp = interp1(1:length(field_data), ...
                        field_data, linspace(1, length(field_data), 150),"cubic")';
                    
                    % Add the data to the table
                    table_data.(field) = field_data_interp;
                end
                
                % Process the global angles
                s_idx = find(global_angles_time == step_time(1));
                e_idx = find(global_angles_time == step_time(end));
                global_data = global_raw_data(s_idx:e_idx, :);

                for field_idx = 1:length(global_fields)
                    % Get the field and it's corresponding data
                    field = global_fields{field_idx};
                    % Verify if the field is for the corresponding leg 
                    if ~contains(field, ['_' leg '_'])
                        continue;
                    end
                    field_data = global_data.(field);

                    % Interpolate to make each step 150 data points long
                    field_data_interp = interp1(1:length(field_data), ...
                        field_data, linspace(1, length(field_data), 150),"cubic")';

                    % Add the data to the table
                    table_data.(field) = field_data_interp;

                    % Calculate the derivative of the leg data with respect to
                    % the time axis and then interpolate it to 150 data points
                    field_data_diff = diff(field_data)./diff(step_time);
                    field_data_diff_interp = interp1(...
                        1:length(field_data_diff), ...
                        field_data_diff, ...
                        linspace(1, length(field_data_diff), 150),...
                        "cubic")';
                    table_data.([field '_velocity']) = field_data_diff_interp;

                end
                
                % Add the data to the total data
                activity_data.(leg) = [activity_data.(leg); table_data];
            end
        end

        % Case 2: Verify if both legs obtained data from the activity. 
        % If not, spoof the entire activity based on the data from the
        % other leg.
        for l_idx = 1:length(legs)
            leg = legs{l_idx};
            
            if num_steps.(leg) == 0

                % Get the other leg
                if strcmp(leg, 'r')
                    other_leg = 'l';
                else
                    other_leg = 'r';
                end

                % Multiply the number of steps by the steps per point 
                % to know how much we have to nan-fill
                nan_fill_points=num_steps.(other_leg)*num_points_per_step;

                % Create a local table for the spoofed data
                table_data = table();
                table_data.subject = ...
                    repmat(subject_save_name, nan_fill_points, 1);
                table_data.activity = ...
                    repmat({activity_name}, nan_fill_points, 1);
                table_data.subactivity = ...
                    repmat({sub_activity_name}, nan_fill_points, 1);
                table_data.activity_number = ...
                    repmat(activity_number, nan_fill_points, 1);

                
                % Copy all the fields from the other leg and fill them with nan
                other_leg_fields = total_data.(leg).Properties.VariableNames;
                % Remove the first four fields, since we already added them
                other_leg_fields = other_leg_fields(5:end);
                % remove the 'properties', 'row', and 'Variables' fields
                other_leg_fields = other_leg_fields(~ismember(other_leg_fields, ...
                    {'Properties', 'Row', 'Variables'}));
                for field_idx = 1:length(other_leg_fields)
                    field = other_leg_fields{field_idx};
                    table_data.(field) = nan(nan_fill_points, 1);
                end

                % Add the data to the total data
                activity_data.(leg) = table_data;
                % total_data.(leg) = [total_data.(leg); table_data];
            end
        end

        % Case 3: One leg has more data than the other. In this case, 
        % we will nan-fill the data for the leg with less data
        if num_steps.r ~= num_steps.l && num_steps.r ~= 0 && num_steps.l~=0
            % Find the leg with less data
            if num_steps.r > num_steps.l
                more_data_leg = 'r';
                less_data_leg = 'l';
            else
                more_data_leg = 'l';
                less_data_leg = 'r';
            end

            % Multiply the number of steps by the steps per point
            % to know how much we have to nan-fill
            nan_fill_points = (num_steps.(more_data_leg) - ...
                           num_steps.(less_data_leg))*num_points_per_step;

            % Create the table
            table_data = table();

            % Get the column names from the existing table
            existing_fields = activity_data.(less_data_leg).Properties.VariableNames;

            % Fill each field with appropriate data
            for field_idx = 1:length(existing_fields)
                field = existing_fields{field_idx};
                if ismember(field, {'subject'})
                    table_data.(field) = repmat(subject_save_name, nan_fill_points, 1);
                elseif ismember(field, {'activity'})
                    table_data.(field) = repmat({activity_name}, nan_fill_points, 1);
                elseif ismember(field, {'task_info', 'subactivity'})
                    table_data.(field) = repmat({sub_activity_name}, nan_fill_points, 1);
                elseif ismember(field, {'activity_number'})
                    table_data.(field) = repmat(activity_number, nan_fill_points, 1);
                else
                    table_data.(field) = nan(nan_fill_points, 1);
                end
            end

            % Add the data to the total data
            activity_data.(less_data_leg) = [activity_data.(less_data_leg); table_data];
        end

        
        % Case 3: If the sizes are different at any point, we have an error
        if size(total_data.r, 1) ~= size(total_data.l, 1)
            error(['The size of the growing tables for the right and ' ...
             'left legs are different']);
        end

        % Use the actual table height to determine the number of steps captured.
        num_steps_r_actual = height(activity_data.r) / num_points_per_step;
        activity_data.r.phase_r = repmat(linspace(0, 1, num_points_per_step)', num_steps_r_actual, 1);

        num_steps_l_actual = height(activity_data.l) / num_points_per_step;
        activity_data.l.phase_l = repmat(linspace(0, 1, num_points_per_step)', num_steps_l_actual, 1);

        % Introduce a phase shift of 50% to a leg so that it mimics
        % walking data. This is done by doing a circular shift of the data
        % by 50% of the number of steps. The leg that has the smallest first  
        % time step will be the one that is shifted.
        % if activity_data.r.time_r(1) == activity_data.l.time_l(1)
        %     % Do nothing
        % elseif activity_data.r.time_r(1) < activity_data.l.time_l(1)
        %     activity_data.r=circshift(activity_data.r,-num_points_per_step/2);
        % else
        activity_data.l=circshift(activity_data.l,-num_points_per_step/2);
        % end

        % Before adding activity_data to total_data, rename the column if it exists
        if ismember('subactivity', activity_data.r.Properties.VariableNames)
            activity_data.r = renamevars(activity_data.r, 'subactivity', 'task_info');
        end
        if ismember('subactivity', activity_data.l.Properties.VariableNames)
            activity_data.l = renamevars(activity_data.l, 'subactivity', 'task_info');
        end

        % Now you can safely add to total_data
        total_data.r = [total_data.r; activity_data.r];
        total_data.l = [total_data.l; activity_data.l];

    end

    % Complete the progress indicator
    fprintf('\n');

end

% Append the data horizontally for the right and left legs. Since the first
% three columns are the subject, activity, and sub-activity. We can ignore
% them on the second dataset.
combined_data = [total_data.r, total_data.l(:, 5:end)];

% Update the names of the columns so that they match the standardized notation
% for the data

% Get the names of the columns
old_col_names = ["knee_angle_r"  , "knee_angle_l"  , "knee_velocity_r", "knee_velocity_l", "knee_angle_r_moment", "knee_angle_l_moment", "ankle_angle_r"  , "ankle_angle_l"  , "ankle_velocity_r","ankle_velocity_l" , "ankle_angle_r_moment", "ankle_angle_l_moment", "calcn_r_Z"     , "calcn_l_Z"     , "calcn_r_Z_velocity", "calcn_l_Z_velocity", "hip_flexion_r"  , "hip_flexion_l"  , "hip_flexion_velocity_r", "hip_flexion_velocity_l", "hip_flexion_r_moment", "hip_flexion_l_moment", "activity", "RCOP_AP", "RCOP_ML", "LCOP_AP", "LCOP_ML", "RVerticalF", "RShearF_AP", "RShearF_ML", "LVerticalF", "LShearF_AP", "LShearF_ML"];
new_col_names = ["knee_angle_s_r", "knee_angle_s_l", "knee_vel_s_r"   , "knee_vel_s_l"   , "knee_torque_s_r"    , "knee_torque_s_l"    , "ankle_angle_s_r", "ankle_angle_s_l", "ankle_vel_s_r"   , "ankle_vel_s_l"   , "ankle_torque_s_r"    , "ankle_torque_s_l"    , "foot_angle_s_r", "foot_angle_s_l", "foot_vel_s_r"      , "foot_vel_s_l"      , "hip_angle_s_r",   "hip_angle_s_l",   "hip_vel_s_r"           , "hip_vel_s_l"           , "hip_torque_s_r"      , "hip_torque_s_l"      , "task",     "cop_z_r", "cop_x_r", "cop_z_l", "cop_x_l", "grf_y_r",    "grf_z_r",    "grf_x_r",    "grf_y_l",    "grf_z_l",    "grf_x_l"];

% Find which columns are missing from the table
missing_cols = ~ismember(old_col_names, combined_data.Properties.VariableNames);

% Print info about missing columns that will be created
missing_col_names = old_col_names(missing_cols);
if ~isempty(missing_col_names)
    fprintf('Creating NaN-filled columns for:\n%s\n', ...
        strjoin(missing_col_names, '\n'));
end

% Add missing columns with NaN values
for i = 1:length(old_col_names)
    if ~ismember(old_col_names(i), combined_data.Properties.VariableNames)
        % For 'activity' column, fill with empty strings instead of NaN
        if strcmp(old_col_names(i), 'activity')
            combined_data.(old_col_names(i)) = repmat("", height(combined_data), 1);
        else
            combined_data.(old_col_names(i)) = nan(height(combined_data), 1);
        end
    end
end

% Now rename all columns (since we know they all exist)
combined_data = renamevars(combined_data, old_col_names, new_col_names);

% Covert task data to string
combined_data.task = convertCharsToStrings(combined_data.task);

% Add a phase columns to the entire dataset
combined_data.phase = repmat(linspace(0, 1, num_points_per_step)', ...
    height(combined_data)/num_points_per_step, 1);

% Write the data to a parquet file
file_name =  'gtech_2023_phase.parquet';
% parquet_file = fullfile(output_dir,file_name);
parquetwrite(file_name,combined_data)