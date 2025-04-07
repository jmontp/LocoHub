% This file is meant to convert the data from the .mat file to a .parquet file
% for the Segmented dataset of the Georgia tech non-cylic dataset. 

% The file structure is as follows:
% "Segmentation"/{Subject}/{activity_name}.mat
% activity_name = {activity}_{activity_number}_{subactivity_name}_segmented

clear all;
close all;

% All the data will be interpolated to 150 datapoints per step
num_points_per_step = 150;
% Choose the naming convention for output columns:
% 'lr': Use standard left/right suffixes (_l, _r)
% 'ipsicontra': Use ipsilateral/contralateral suffixes (_ipsi, _contra), where ipsi = left.
naming_convention = 'lr'; % Options: 'lr', 'ipsicontra'

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
% for subject_idx = 1:length(subjects)
for subject_idx = 1:2

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
        % Initialize first step times for this activity
        first_step_time_r = NaN;
        first_step_time_l = NaN;
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
        
        % Get parsing file path (replace "_segmented" with "_parsing")
        [~,name] = fileparts(activity);
        parsing_name = strrep(name, '_segmented', '_parsing');
        parsing_file = fullfile(subject_dir, parsing_name);
    
        try
            % Load heel strike indices if parsing file exists
            parsing_data = load(parsing_file);
            heel_strike_time.r = parsing_data.right; 
            heel_strike_time.l = parsing_data.left;
            parsing_file_exists = true;
        catch
            warning('Parsing file not found: %s', parsing_file);
        end

        % Get total activity name
        total_activity_name = strrep(activity, '_segmented', '');
        
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
            raw_activity_name = [activity_name '_' int2str(activity_number) '_' stair_num];
        
        % For step ups, we don't need the activity number if it is only 1
        elseif strcmp(activity_name, 'step_ups') && activity_number == 1
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler', 'step_ups.csv');
            raw_activity_name = 'step_ups';

        % For jump, see if there is another number as the first character
        % of the subactivity name. If so, use that number to get the file
        elseif strcmp(activity_name, 'jump') && activity_number == 1 && ...
                ~isnan(str2double(sub_activity_name(1))) && ...
                str2double(sub_activity_name(1)) == 2
            jump_num = sub_activity_name(1);
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler', ...
                [activity_name '_' int2str(activity_number) '_' jump_num '.csv']);
            raw_activity_name = [activity_name '_' int2str(activity_number) '_' jump_num];
        else
            global_file_name = fullfile('RawData', subject, ...
                'Transforms_Euler',...
                [activity_name '_' int2str(activity_number) '.csv']);
            raw_activity_name = [activity_name '_' int2str(activity_number)];
        end
        
        % Read the csv that contains the global angles
        global_raw_data = readtable(global_file_name);
        global_angles_time = global_raw_data.Header; % Get the time axis

        % Load GRF data
        grf_file = fullfile('RawData', subject, 'CSV_data', raw_activity_name, 'GroundFrame_GRFs.csv');
        grf_data = readtable(grf_file);
        grf_time = grf_data.time; % Assuming first column is time
        
        % --- Load Raw Kinematic/Kinetic Data ---
        % Load raw data needed for reconstruction in Case 3
        raw_data_loaded = false;
        raw_angle_data = table();
        raw_velocity_data = table();
        raw_moment_data = table();
        raw_link_angle_data = table();
        raw_link_velocity_data = table();
        raw_time = [];
        
        try
            csv_base_path = fullfile('RawData', subject, 'CSV_data', raw_activity_name);
            
            % Try to load joint angle data
            angle_file = fullfile(csv_base_path, 'Joint_Angle.csv');
            if exist(angle_file, 'file')
                raw_angle_data = readtable(angle_file);
                if ismember('time', raw_angle_data.Properties.VariableNames)
                    raw_time = raw_angle_data.time;
                    raw_data_loaded = true;
                end
            else
                warning('Raw angle file not found: %s', angle_file);
            end
            
            % Try to load joint velocity data
            velocity_file = fullfile(csv_base_path, 'Joint_Velocities.csv');
            if exist(velocity_file, 'file')
                raw_velocity_data = readtable(velocity_file);
                if ~raw_data_loaded && ismember('time', raw_velocity_data.Properties.VariableNames)
                    raw_time = raw_velocity_data.time;
                    raw_data_loaded = true;
                end
            else
                warning('Raw velocity file not found: %s', velocity_file);
            end
            
            % Try to load joint moment data
            moment_file = fullfile(csv_base_path, 'Joint_Moments.csv');
            if exist(moment_file, 'file')
                raw_moment_data = readtable(moment_file);
                if ~raw_data_loaded && ismember('time', raw_moment_data.Properties.VariableNames)
                    raw_time = raw_moment_data.time;
                    raw_data_loaded = true;
                end
            else
                warning('Raw moment file not found: %s', moment_file);
            end
            
            % Try to load link angle data
            link_angle_file = fullfile(csv_base_path, 'Link_Angle.csv');
            if exist(link_angle_file, 'file')
                raw_link_angle_data = readtable(link_angle_file);
                if ~raw_data_loaded && ismember('time', raw_link_angle_data.Properties.VariableNames)
                    raw_time = raw_link_angle_data.time;
                    raw_data_loaded = true;
                end
            else
                warning('Raw link angle file not found: %s', link_angle_file);
            end
            
            % Try to load link velocity data
            link_velocity_file = fullfile(csv_base_path, 'Link_Velocities.csv');
            if exist(link_velocity_file, 'file')
                raw_link_velocity_data = readtable(link_velocity_file);
                if ~raw_data_loaded && ismember('time', raw_link_velocity_data.Properties.VariableNames)
                    raw_time = raw_link_velocity_data.time;
                    raw_data_loaded = true;
                end
            else
                warning('Raw link velocity file not found: %s', link_velocity_file);
            end
            
            if ~raw_data_loaded
                warning('No raw kinematic/kinetic data loaded successfully for %s.', raw_activity_name);
            end
        catch ME
            warning('%s', ['Error loading raw kinematic/kinetic CSV files: ' ME.message '. Case 3 reconstruction will use NaN fill.']);
        end
        % --- End Raw Data Loading ---
        
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

        % Case 1: If both legs are missing, we just go to the next one
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
                table_data.is_reconstructed = ...
                    repmat(false, num_points_per_step, 1); % Add flag, default false

                % Add time, interpolated to 150 data points
                step_time = angle_data(step_idx).time;

                % Store the start time of the very first step for this leg/activity
                if step_idx == 1
                    if strcmp(leg, 'r')
                        first_step_time_r = step_time(1);
                    else % leg == 'l'
                        first_step_time_l = step_time(1);
                    end
                end
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
                
                % Process GRF data
                if strcmp(leg, 'r')
                    grf_fields = {'RForceX', 'RForceY_Vertical', 'RForceZ', ...
                        'RCOPX', 'RCOPY_Vertical', 'RCOPZ'};
                else
                    grf_fields = {'LForceX', 'LForceY_Vertical', 'LForceZ', ...
                        'LCOPX', 'LCOPY_Vertical', 'LCOPZ'};
                end

                if parsing_file_exists && size(heel_strike_time.(leg), 1) >= step_idx
                
                    % Load transformation data
                    transform_file = fullfile('RawData', subject, 'Transforms', [raw_activity_name '.mat']);
                    try
                        transform_data = load(transform_file);
                        transform_struct = struct();
                        transform_struct.r = transform_data.Transforms.calcn_r;
                        transform_struct.l = transform_data.Transforms.calcn_l;
                        transform_struct.time = transform_data.Transforms.Header;
                    catch
                        warning('Transform file not found: %s', transform_file);
                        transform_struct = [];
                    end

                    % Get step boundaries from heel strikes
                    step_start = heel_strike_time.(leg)(step_idx,1);
                    step_end = heel_strike_time.(leg)(step_idx,2);

                    % Find indices where GRF time matches step boundaries
                    start_idx = find(grf_time == step_start);
                    end_idx = find(grf_time == step_end);
                    
                    % Check if indices were found
                    if isempty(start_idx) || isempty(end_idx) || isempty(transform_struct)
                        % Indices not found or transforms missing, nan-fill all fields
                        for field_idx = 1:length(grf_fields)
                            field = grf_fields{field_idx};
                            table_data.(field) = nan(num_points_per_step, 1);
                        end
                    else
                        % Process GRF data normally
                        grf_slice = grf_data(start_idx:end_idx,:);
                        
                        % Find corresponding transform indices
                        transform_start_idx = find(transform_struct.time >= step_start, 1);
                        transform_end_idx = find(transform_struct.time <= step_end, 1, 'last');
                        
                        if ~isempty(transform_start_idx) && ~isempty(transform_end_idx)
                            transforms_slice = transform_struct.(leg)(transform_start_idx:transform_end_idx);
                            
                            % Get COP data
                            if strcmp(leg, 'r')
                                cop_x = grf_slice.RCOPX;
                                cop_z = grf_slice.RCOPZ;
                            else
                                cop_x = grf_slice.LCOPX;
                                cop_z = grf_slice.LCOPZ;
                            end
                            
                            % Transform COP to local frame
                            cop_local_x = zeros(size(cop_x));
                            cop_local_z = zeros(size(cop_z));
                            
                            for t = 1:length(cop_x)
                                % Find closest transform
                                [~, closest_idx] = min(abs(transform_struct.time - grf_slice.time(t)));
                                T = transforms_slice{closest_idx - transform_start_idx + 1};
                                
                                % Extract translation from transform
                                translation = T(1:3,4);
                                
                                % Transform COP point
                                cop_global = [cop_x(t); 0; cop_z(t)];  % y is assumed 0
                                cop_local = cop_global - translation;
                                
                                cop_local_x(t) = cop_local(1);
                                cop_local_z(t) = cop_local(3);
                            end
                            
                            % Interpolate transformed COP to 150 points
                            cop_x_interp = interp1(1:length(cop_local_x), cop_local_x, ...
                                linspace(1, length(cop_local_x), 150), "cubic")';
                            cop_z_interp = interp1(1:length(cop_local_z), cop_local_z, ...
                                linspace(1, length(cop_local_z), 150), "cubic")';
                            
                            % Store transformed COP
                            if strcmp(leg, 'r')
                                table_data.RCOPX = cop_x_interp;
                                table_data.RCOPZ = cop_z_interp;
                                table_data.RCOPY_Vertical = zeros(num_points_per_step, 1);
                            else
                                table_data.LCOPX = cop_x_interp;
                                table_data.LCOPZ = cop_z_interp;
                                table_data.LCOPY_Vertical = zeros(num_points_per_step, 1);
                            end
                            
                            % Process other GRF fields normally
                            for field_idx = 1:length(grf_fields)
                                field = grf_fields{field_idx};
                                if ~contains(field, 'COP')  % Skip COP fields as we handled them above
                                    field_data = grf_slice.(field);
                                    field_data_interp = interp1(1:length(field_data),...
                                        field_data, linspace(1, length(field_data), 150), "cubic")';
                                    table_data.(field) = field_data_interp;
                                end
                            end
                        else
                            % No matching transforms found, nan-fill all fields
                            for field_idx = 1:length(grf_fields)
                                field = grf_fields{field_idx};
                                table_data.(field) = nan(num_points_per_step, 1);
                            end
                        end
                    end
                
                else % GRF data is missing, therefore nan-fill all fields
                    for field_idx = 1:length(grf_fields)
                        field = grf_fields{field_idx};
                        table_data.(field) = nan(num_points_per_step, 1);
                    end
                end
                
                % Add the data to the total data
                activity_data.(leg) = [activity_data.(leg); table_data];
            end
        end

        % Case 3: Verify if both legs obtained data from the activity. 
        % If not, reconstruct the leg data from raw files, or spoof with NaNs if raw data unavailable.
        for l_idx = 1:length(legs)
            leg = legs{l_idx};
            
            if num_steps.(leg) == 0
                % Get the other leg
                if strcmp(leg, 'r')
                    other_leg = 'l';
                else
                    other_leg = 'r';
                end

                % Check if other leg has steps
                if num_steps.(other_leg) == 0
                    warning('Both legs have zero steps for %s. Skipping leg reconstruction.', activity);
                    continue;
                end

                % Create a table to hold the reconstructed leg data
                reconstructed_data = table();
                steps_processed = 0;

                % Attempt data reconstruction if raw data is available
                if raw_data_loaded && ~isempty(raw_time)
                    fprintf('Reconstructing %s leg data from raw files for %s...\n', leg, activity);
                    
                    % Get step timings from heel strike data or from segmented leg data
                    step_timings = [];
                    
                    % First try to get timings from parsing file (heel strikes)
                    if parsing_file_exists && isfield(heel_strike_time, other_leg) && ~isempty(heel_strike_time.(other_leg))
                        step_timings = heel_strike_time.(other_leg);
                        fprintf('  Using heel strike timings (%d steps).\n', size(step_timings, 1));
                    % Otherwise try to get timings from segmented data
                    elseif isfield(data, 'angle') && isfield(data.angle, ['data_' other_leg]) && ~isempty(data.angle.(['data_' other_leg]))
                        other_steps = length(data.angle.(['data_' other_leg]));
                        step_timings = zeros(other_steps, 2);
                        valid_steps = 0;
                        
                        for step_i = 1:other_steps
                            if isfield(data.angle.(['data_' other_leg])(step_i), 'time')
                                time_vec = data.angle.(['data_' other_leg])(step_i).time;
                                if ~isempty(time_vec) && length(time_vec) >= 2
                                    valid_steps = valid_steps + 1;
                                    step_timings(valid_steps, 1) = time_vec(1);
                                    step_timings(valid_steps, 2) = time_vec(end);
                                end
                            end
                        end
                        
                        if valid_steps > 0
                            step_timings = step_timings(1:valid_steps, :);
                            fprintf('  Using segmented data timings (%d valid steps).\n', valid_steps);
                        else
                            step_timings = [];
                        end
                    end
                    
                    % If we have valid step timings, process each step
                    if ~isempty(step_timings)
                        % Load transform file (once) - needed for GRF data
                        transform_struct = [];
                        transform_file = fullfile('RawData', subject, 'Transforms', [raw_activity_name '.mat']);
                        try
                            transform_data = load(transform_file);
                            transform_struct = struct();
                            transform_struct.r = transform_data.Transforms.calcn_r;
                            transform_struct.l = transform_data.Transforms.calcn_l;
                            transform_struct.time = transform_data.Transforms.Header;
                        catch
                            warning('Transform file not found: %s', transform_file);
                        end
                        
                        % Process each step based on timings
                        for step_idx = 1:size(step_timings, 1)
                            step_start = step_timings(step_idx, 1);
                            step_end = step_timings(step_idx, 2);
                            
                            % Skip invalid steps
                            if step_end <= step_start
                                warning('  Invalid step timing [%f, %f] for step %d. Skipping.', step_start, step_end, step_idx);
                                continue;
                            end
                            
                            % Setup metadata for the step
                            step_data = table();
                            step_data.subject = repmat(subject_save_name, num_points_per_step, 1);
                            step_data.activity = repmat({activity_name}, num_points_per_step, 1);
                            step_data.task_info = repmat({sub_activity_name}, num_points_per_step, 1);
                            step_data.activity_number = repmat(activity_number, num_points_per_step, 1);
                            step_data.is_reconstructed = repmat(true, num_points_per_step, 1); % Flag as reconstructed
                            
                            % Create interpolated time array
                            time_interp = linspace(step_start, step_end, num_points_per_step)';
                            step_data.(['time_' leg]) = time_interp;
                            
                            % Extract and process raw angle data
                            angle_fields = {['knee_angle_' leg], ['ankle_angle_' leg], ['hip_flexion_' leg]};
                            for field_idx = 1:length(angle_fields)
                                field = angle_fields{field_idx};
                                if ~isempty(raw_angle_data) && ismember(field, raw_angle_data.Properties.VariableNames)
                                    % Find indices in raw time that match our step
                                    start_idx = find(raw_time >= step_start, 1, 'first');
                                    end_idx = find(raw_time <= step_end, 1, 'last');
                                    
                                    if ~isempty(start_idx) && ~isempty(end_idx) && end_idx > start_idx
                                        % Extract data and interpolate
                                        raw_times = raw_time(start_idx:end_idx);
                                        raw_values = raw_angle_data.(field)(start_idx:end_idx);
                                        step_data.(field) = interp1(raw_times, raw_values, time_interp, 'cubic', NaN);
                                    else
                                        % No data found in range
                                        step_data.(field) = nan(num_points_per_step, 1);
                                    end
                                else
                                    step_data.(field) = nan(num_points_per_step, 1);
                                end
                            end
                            
                            % Extract and process raw velocity data
                            velocity_fields = {['knee_velocity_' leg], ['ankle_velocity_' leg], ['hip_flexion_velocity_' leg]};
                            for field_idx = 1:length(velocity_fields)
                                field = velocity_fields{field_idx};
                                if ~isempty(raw_velocity_data) && ismember(field, raw_velocity_data.Properties.VariableNames)
                                    start_idx = find(raw_time >= step_start, 1, 'first');
                                    end_idx = find(raw_time <= step_end, 1, 'last');
                                    
                                    if ~isempty(start_idx) && ~isempty(end_idx) && end_idx > start_idx
                                        raw_times = raw_time(start_idx:end_idx);
                                        raw_values = raw_velocity_data.(field)(start_idx:end_idx);
                                        step_data.(field) = interp1(raw_times, raw_values, time_interp, 'cubic', NaN);
                                    else
                                        step_data.(field) = nan(num_points_per_step, 1);
                                    end
                                else
                                    step_data.(field) = nan(num_points_per_step, 1);
                                end
                            end
                            
                            % Extract and process raw moment data
                            moment_fields = {['knee_angle_' leg '_moment'], ['ankle_angle_' leg '_moment'], ['hip_flexion_' leg '_moment']};
                            for field_idx = 1:length(moment_fields)
                                field = moment_fields{field_idx};
                                if ~isempty(raw_moment_data) && ismember(field, raw_moment_data.Properties.VariableNames)
                                    start_idx = find(raw_time >= step_start, 1, 'first');
                                    end_idx = find(raw_time <= step_end, 1, 'last');
                                    
                                    if ~isempty(start_idx) && ~isempty(end_idx) && end_idx > start_idx
                                        raw_times = raw_time(start_idx:end_idx);
                                        raw_values = raw_moment_data.(field)(start_idx:end_idx);
                                        step_data.(field) = interp1(raw_times, raw_values, time_interp, 'cubic', NaN);
                                    else
                                        step_data.(field) = nan(num_points_per_step, 1);
                                    end
                                else
                                    step_data.(field) = nan(num_points_per_step, 1);
                                end
                            end
                            
                            % Extract and process link angle data
                            % Expected field names like 'foot_link_r', 'shank_link_r', 'thigh_link_r', etc.
                            if ~isempty(raw_link_angle_data)
                                % Find all link angle fields for this leg in the data
                                all_link_fields = raw_link_angle_data.Properties.VariableNames;
                                link_angle_fields = {};
                                for f = 1:length(all_link_fields)
                                    if contains(all_link_fields{f}, ['_link_' leg]) || ...
                                       contains(all_link_fields{f}, ['link_' leg '_'])
                                        link_angle_fields{end+1} = all_link_fields{f};
                                    end
                                end
                                
                                % Process each link angle field
                                for field_idx = 1:length(link_angle_fields)
                                    field = link_angle_fields{field_idx};
                                    start_idx = find(raw_time >= step_start, 1, 'first');
                                    end_idx = find(raw_time <= step_end, 1, 'last');
                                    
                                    if ~isempty(start_idx) && ~isempty(end_idx) && end_idx > start_idx
                                        raw_times = raw_time(start_idx:end_idx);
                                        raw_values = raw_link_angle_data.(field)(start_idx:end_idx);
                                        step_data.(field) = interp1(raw_times, raw_values, time_interp, 'cubic', NaN);
                                    else
                                        step_data.(field) = nan(num_points_per_step, 1);
                                    end
                                end
                            end
                            
                            % Extract and process link velocity data
                            if ~isempty(raw_link_velocity_data)
                                % Find all link velocity fields for this leg in the data
                                all_link_vel_fields = raw_link_velocity_data.Properties.VariableNames;
                                link_vel_fields = {};
                                for f = 1:length(all_link_vel_fields)
                                    if contains(all_link_vel_fields{f}, ['_link_' leg]) || ...
                                       contains(all_link_vel_fields{f}, ['link_' leg '_']) || ...
                                       contains(all_link_vel_fields{f}, ['_link_vel_' leg])
                                        link_vel_fields{end+1} = all_link_vel_fields{f};
                                    end
                                end
                                
                                % Process each link velocity field
                                for field_idx = 1:length(link_vel_fields)
                                    field = link_vel_fields{field_idx};
                                    start_idx = find(raw_time >= step_start, 1, 'first');
                                    end_idx = find(raw_time <= step_end, 1, 'last');
                                    
                                    if ~isempty(start_idx) && ~isempty(end_idx) && end_idx > start_idx
                                        raw_times = raw_time(start_idx:end_idx);
                                        raw_values = raw_link_velocity_data.(field)(start_idx:end_idx);
                                        step_data.(field) = interp1(raw_times, raw_values, time_interp, 'cubic', NaN);
                                    else
                                        step_data.(field) = nan(num_points_per_step, 1);
                                    end
                                end
                            end
                            
                            % Process global angle data
                            s_idx_global = find(global_angles_time >= step_start, 1, 'first');
                            e_idx_global = find(global_angles_time <= step_end, 1, 'last');
                            
                            if ~isempty(s_idx_global) && ~isempty(e_idx_global) && e_idx_global > s_idx_global
                                global_time_slice = global_angles_time(s_idx_global:e_idx_global);
                                global_data_slice = global_raw_data(s_idx_global:e_idx_global, :);
                                
                                % Process global angles that match this leg
                                for field_idx = 1:length(global_fields)
                                    field = global_fields{field_idx};
                                    if contains(field, ['_' leg '_']) && ismember(field, global_data_slice.Properties.VariableNames)
                                        % Interpolate the global angle data
                                        field_data = global_data_slice.(field);
                                        field_data_interp = interp1(global_time_slice, field_data, time_interp, 'cubic', NaN);
                                        step_data.(field) = field_data_interp;
                                        
                                        % Calculate velocity by differentiating
                                        if length(global_time_slice) > 1
                                            field_data_diff = diff(field_data) ./ diff(global_time_slice);
                                            time_diff_midpoints = global_time_slice(1:end-1) + diff(global_time_slice)/2;
                                            
                                            if length(time_diff_midpoints) >= 2
                                                field_diff_interp = interp1(time_diff_midpoints, field_data_diff, time_interp, 'cubic', NaN);
                                                step_data.([field '_velocity']) = field_diff_interp;
                                            else
                                                step_data.([field '_velocity']) = nan(num_points_per_step, 1);
                                            end
                                        else
                                            step_data.([field '_velocity']) = nan(num_points_per_step, 1);
                                        end
                                    end
                                end
                            end
                            
                            % Process GRF and COP data
                            if strcmp(leg, 'r')
                                grf_fields = {'RForceX', 'RForceY_Vertical', 'RForceZ', 'RCOPX', 'RCOPY_Vertical', 'RCOPZ'};
                            else
                                grf_fields = {'LForceX', 'LForceY_Vertical', 'LForceZ', 'LCOPX', 'LCOPY_Vertical', 'LCOPZ'};
                            end
                            
                            % Find GRF data for this step
                            s_idx_grf = find(grf_time >= step_start, 1, 'first');
                            e_idx_grf = find(grf_time <= step_end, 1, 'last');
                            
                            if ~isempty(s_idx_grf) && ~isempty(e_idx_grf) && e_idx_grf > s_idx_grf && ~isempty(transform_struct)
                                grf_slice = grf_data(s_idx_grf:e_idx_grf, :);
                                grf_time_slice = grf_time(s_idx_grf:e_idx_grf);
                                
                                % Find transform data for this step
                                transform_start_idx = find(transform_struct.time >= step_start, 1, 'first');
                                transform_end_idx = find(transform_struct.time <= step_end, 1, 'last');
                                
                                if ~isempty(transform_start_idx) && ~isempty(transform_end_idx) && ...
                                   transform_start_idx <= length(transform_struct.(leg)) && transform_end_idx <= length(transform_struct.(leg))
                                    transforms_slice = transform_struct.(leg)(transform_start_idx:transform_end_idx);
                                    transform_time_slice = transform_struct.time(transform_start_idx:transform_end_idx);
                                    
                                    % Get COP data for this leg
                                    if strcmp(leg, 'r')
                                        cop_x_raw = grf_slice.RCOPX;
                                        cop_z_raw = grf_slice.RCOPZ;
                                    else
                                        cop_x_raw = grf_slice.LCOPX;
                                        cop_z_raw = grf_slice.LCOPZ;
                                    end
                                    
                                    % Transform COP to local frame
                                    cop_local_x = nan(size(cop_x_raw));
                                    cop_local_z = nan(size(cop_z_raw));
                                    
                                    for t = 1:length(grf_time_slice)
                                        % Find closest transform
                                        [~, closest_idx] = min(abs(transform_time_slice - grf_time_slice(t)));
                                        if closest_idx <= length(transforms_slice)
                                            T = transforms_slice{closest_idx};
                                            
                                            % Make sure transform is valid
                                            if isnumeric(T) && all(size(T) == [4, 4])
                                                % Extract translation from transform
                                                translation = T(1:3, 4);
                                                rotation = T(1:3, 1:3);
                                                
                                                % Transform COP point
                                                cop_global = [cop_x_raw(t); 0; cop_z_raw(t)];  % y is assumed 0
                                                if ~any(isnan(cop_global))
                                                    cop_relative = cop_global - translation;
                                                    cop_local = rotation' * cop_relative;
                                                    
                                                    cop_local_x(t) = cop_local(1);
                                                    cop_local_z(t) = cop_local(3);
                                                end
                                            end
                                        end
                                    end
                                    
                                    % Interpolate transformed COP
                                    valid_cop_indices = ~isnan(cop_local_x) & ~isnan(cop_local_z);
                                    if sum(valid_cop_indices) >= 2
                                        cop_x_interp = interp1(grf_time_slice(valid_cop_indices), cop_local_x(valid_cop_indices), time_interp, 'cubic', NaN);
                                        cop_z_interp = interp1(grf_time_slice(valid_cop_indices), cop_local_z(valid_cop_indices), time_interp, 'cubic', NaN);
                                        
                                        if strcmp(leg, 'r')
                                            step_data.RCOPX = cop_x_interp;
                                            step_data.RCOPZ = cop_z_interp;
                                            step_data.RCOPY_Vertical = zeros(num_points_per_step, 1);
                                        else
                                            step_data.LCOPX = cop_x_interp;
                                            step_data.LCOPZ = cop_z_interp;
                                            step_data.LCOPY_Vertical = zeros(num_points_per_step, 1);
                                        end
                                    else
                                        for f_idx = 1:length(grf_fields)
                                            if contains(grf_fields{f_idx}, 'COP')
                                                step_data.(grf_fields{f_idx}) = nan(num_points_per_step, 1);
                                            end
                                        end
                                    end
                                    
                                    % Process force data
                                    for f_idx = 1:length(grf_fields)
                                        field = grf_fields{f_idx};
                                        if ~contains(field, 'COP') && ismember(field, grf_slice.Properties.VariableNames)
                                            field_data = grf_slice.(field);
                                            if ~all(isnan(field_data))
                                                step_data.(field) = interp1(grf_time_slice, field_data, time_interp, 'cubic', NaN);
                                            else
                                                step_data.(field) = nan(num_points_per_step, 1);
                                            end
                                        elseif ~contains(field, 'COP')
                                            step_data.(field) = nan(num_points_per_step, 1);
                                        end
                                    end
                                else
                                    % No transforms found - NaN fill GRF fields
                                    for f_idx = 1:length(grf_fields)
                                        step_data.(grf_fields{f_idx}) = nan(num_points_per_step, 1);
                                    end
                                end
                            else
                                % No GRF data found - NaN fill GRF fields
                                for f_idx = 1:length(grf_fields)
                                    step_data.(grf_fields{f_idx}) = nan(num_points_per_step, 1);
                                end
                            end
                            
                            % Add the processed step to the reconstructed data
                            reconstructed_data = [reconstructed_data; step_data];
                            steps_processed = steps_processed + 1;
                        end
                    end
                    
                    if steps_processed > 0
                        fprintf('  Successfully reconstructed %d steps for %s leg.\n', steps_processed, leg);
                        activity_data.(leg) = reconstructed_data;
                    else
                        warning('  Failed to reconstruct any steps from raw data. Falling back to NaN fill.');
                        raw_data_loaded = false; % Force fallback to NaN fill
                    end
                end
                
                % If raw data reconstruction failed or wasn't attempted, use NaN fill
                if ~raw_data_loaded || steps_processed == 0
                    fprintf('NaN-filling %s leg data (using other leg as template)...\n', leg);
                    
                    % Determine how many points to fill based on other leg
                    nan_fill_points = num_steps.(other_leg) * num_points_per_step;
                    
                    % Create NaN-filled table based on metadata
                table_data = table();
                    table_data.subject = repmat(subject_save_name, nan_fill_points, 1);
                    table_data.activity = repmat({activity_name}, nan_fill_points, 1);
                    table_data.task_info = repmat({sub_activity_name}, nan_fill_points, 1);
                    table_data.activity_number = repmat(activity_number, nan_fill_points, 1);
                    table_data.is_reconstructed = repmat(false, nan_fill_points, 1); % Flag as NOT reconstructed (NaN fill)
                    
                    % Determine fields to fill from total_data structure
                    fields_to_fill = {};
                    if ~isempty(total_data.(leg))
                        fields_to_fill = total_data.(leg).Properties.VariableNames;
                        if ~isempty(fields_to_fill) && length(fields_to_fill) >= 5
                            fields_to_fill = fields_to_fill(5:end); % Skip metadata fields
                        end
                    end
                    
                    % If no fields in total_data yet, try to infer from the other leg's activity_data
                    if isempty(fields_to_fill) && ~isempty(activity_data.(other_leg))
                        other_fields = activity_data.(other_leg).Properties.VariableNames;
                        for f_idx = 1:length(other_fields)
                            field = other_fields{f_idx};
                            % Convert fields specific to other leg to this leg
                            if contains(field, ['_' other_leg]) || contains(field, [other_leg '_'])
                                new_field = strrep(field, ['_' other_leg], ['_' leg]);
                                new_field = strrep(new_field, [other_leg '_'], [leg '_']);
                                fields_to_fill{end+1} = new_field;
                            elseif ~ismember(field, {'subject', 'activity', 'task_info', 'activity_number'})
                                fields_to_fill{end+1} = field;
                            end
                        end
                    end
                    
                    % Fill each field with NaN
                    for field_idx = 1:length(fields_to_fill)
                        field = fields_to_fill{field_idx};
                        if ~ismember(field, {'subject', 'activity', 'task_info', 'activity_number'})
                    table_data.(field) = nan(nan_fill_points, 1);
                        end
                    end
                    
                    % Add time column if not already added
                    if ~ismember(['time_' leg], table_data.Properties.VariableNames)
                        table_data.(['time_' leg]) = nan(nan_fill_points, 1);
                    end
                    
                activity_data.(leg) = table_data;
                end
            end
        end

        % Case 4: One leg has more data than the other. In this case, 
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

        
        % Case 5: If the sizes are different at any point, we have an error
        if size(total_data.r, 1) ~= size(total_data.l, 1)
            error(['The size of the growing tables for the right and ' ...
             'left legs are different']);
        end

        % Use the actual table height to determine the number of steps captured.
        num_steps_r_actual = height(activity_data.r) / num_points_per_step;
        activity_data.r.phase_r = repmat(linspace(0, 1, num_points_per_step)', num_steps_r_actual, 1);

        num_steps_l_actual = height(activity_data.l) / num_points_per_step;
        activity_data.l.phase_l = repmat(linspace(0, 1, num_points_per_step)', num_steps_l_actual, 1);

        % --- START: Final Conditional Phase Shift Logic (Shift ONLY if both legs original) ---
        fprintf('Applying conditional phase shift for: %s\n', activity);

        % Define the circshift logic as an anonymous function for reuse
        apply_shift = @(target_table, target_phase_col) ...
            apply_step_circshift(target_table, num_points_per_step, target_phase_col);

        if num_steps.r > 0 && num_steps.l > 0 % Normal Case: Shift ONLY if Both legs have original data
            if ~isnan(first_step_time_r) && ~isnan(first_step_time_l)
                if first_step_time_l > first_step_time_r
                    fprintf('  Shifting LEFT leg (started later).\n');
                    activity_data.l = apply_shift(activity_data.l, 'phase_l');
                else % Right started later or simultaneously
                    fprintf('  Shifting RIGHT leg (started later or simultaneously).\n');
                    activity_data.r = apply_shift(activity_data.r, 'phase_r');
                end
            else
                 warning('Could not determine first step times for %s. Skipping conditional shift.', activity);
            end
        else % Reconstruction Case (Right or Left leg missing/reconstructed)
            fprintf('  Reconstruction occurred. NO phase shift applied.\n');
            % DO NOTHING - leave reconstructed data time-aligned with its source timing
        end
        % --- END: Final Conditional Phase Shift Logic ---
        % Before adding activity_data to total_data, rename the column if it exists
        if ismember('subactivity', activity_data.r.Properties.VariableNames)
            activity_data.r = renamevars(activity_data.r, 'subactivity', 'task_info');
        end
        if ismember('subactivity', activity_data.l.Properties.VariableNames)
            activity_data.l = renamevars(activity_data.l, 'subactivity', 'task_info');
        end

        % Ensure column compatibility between total_data and activity_data
        for l_idx = 1:length(legs)
            leg = legs{l_idx};
            
            % Only proceed if we have data for this leg 
            if isempty(activity_data.(leg))
                continue;
            end
            
            % Check for missing columns that should be added to activity_data
            if ~isempty(total_data.(leg))
                % Get columns that are in total_data but not in activity_data
                missing_cols = setdiff(total_data.(leg).Properties.VariableNames, activity_data.(leg).Properties.VariableNames);
                
                % If there are missing columns, add them with NaN values
                if ~isempty(missing_cols)
                    fprintf('Adding %d missing columns to activity_data.%s: %s\n', ...
                        length(missing_cols), leg, strjoin(missing_cols, ', '));
                    
                    % Add each missing column with NaN values
                    for col_idx = 1:length(missing_cols)
                        col_name = missing_cols{col_idx};
                        activity_data.(leg).(col_name) = nan(height(activity_data.(leg)), 1);
                    end
                end
                
                % Ensure column order matches between the tables
                activity_data.(leg) = activity_data.(leg)(:, total_data.(leg).Properties.VariableNames);
            end
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

% Ensure both tables have the flag column before combining
if ~ismember('is_reconstructed', total_data.r.Properties.VariableNames)
    if height(total_data.r) > 0
        total_data.r.is_reconstructed = false(height(total_data.r), 1);
    elseif ~isempty(properties(total_data.r))
        total_data.r = addvars(total_data.r, logical.empty(0,1), 'NewVariableNames', 'is_reconstructed');
    end
end
if ~ismember('is_reconstructed', total_data.l.Properties.VariableNames)
     if height(total_data.l) > 0
        total_data.l.is_reconstructed = false(height(total_data.l), 1);
    elseif ~isempty(properties(total_data.l))
         total_data.l = addvars(total_data.l, logical.empty(0,1), 'NewVariableNames', 'is_reconstructed');
    end
end

% Rename flag columns before combining if they exist
if ismember('is_reconstructed', total_data.r.Properties.VariableNames)
    total_data.r = renamevars(total_data.r, 'is_reconstructed', 'is_reconstructed_r');
end
if ismember('is_reconstructed', total_data.l.Properties.VariableNames)
    total_data.l = renamevars(total_data.l, 'is_reconstructed', 'is_reconstructed_l');
end

% Define columns to keep from each table (ensure metadata + data + flag)
common_cols = {'subject', 'activity', 'task_info', 'activity_number'};
r_cols = setdiff(total_data.r.Properties.VariableNames, common_cols, 'stable');
l_cols = setdiff(total_data.l.Properties.VariableNames, common_cols, 'stable');

% Combine data, keeping common columns only once
if ~isempty(total_data.r) && ~isempty(total_data.l)
    combined_data = [total_data.r(:, [common_cols, r_cols]), total_data.l(:, l_cols)];
elseif ~isempty(total_data.r) % Handle case where one leg might be empty
    combined_data = total_data.r(:, [common_cols, r_cols]);
    % Add empty columns for left leg data + flag
    l_cols_to_add = setdiff(total_data.l.Properties.VariableNames, common_cols, 'stable'); % Get expected L cols
    for i = 1:length(l_cols_to_add)
        combined_data.(l_cols_to_add{i}) = nan(height(combined_data), 1); 
    end
elseif ~isempty(total_data.l)
    combined_data = total_data.l(:, [common_cols, l_cols]);
    % Add empty columns for right leg data + flag
    r_cols_to_add = setdiff(total_data.r.Properties.VariableNames, common_cols, 'stable'); % Get expected R cols
     for i = 1:length(r_cols_to_add)
        combined_data.(r_cols_to_add{i}) = nan(height(combined_data), 1);
    end
else
    combined_data = table(); % Both empty
end

% Ensure final combined_data has the reconstructed flags even if one side was empty
if ~ismember('is_reconstructed_r', combined_data.Properties.VariableNames)
    combined_data.is_reconstructed_r = false(height(combined_data), 1);
end
if ~ismember('is_reconstructed_l', combined_data.Properties.VariableNames)
    combined_data.is_reconstructed_l = false(height(combined_data), 1);
end


% Update the names of the columns so that they match the standardized notation
% for the data

% Get the names of the columns
old_col_names = ["knee_angle_r"  , "knee_angle_l"  , "knee_velocity_r", "knee_velocity_l", "knee_angle_r_moment", "knee_angle_l_moment", "ankle_angle_r"  , "ankle_angle_l"  , "ankle_velocity_r","ankle_velocity_l" , "ankle_angle_r_moment", "ankle_angle_l_moment", "calcn_r_Z"     , "calcn_l_Z"     , "calcn_r_Z_velocity", "calcn_l_Z_velocity", "hip_flexion_r"  , "hip_flexion_l"  , "hip_flexion_velocity_r", "hip_flexion_velocity_l", "hip_flexion_r_moment", "hip_flexion_l_moment", "activity", "RCOPZ",   "RCOPX",   "LCOPZ",   "LCOPX",  "RForceY_Vertical", "RForceZ", "RForceX", "LForceY_Vertical", "RForceZ", "RForceX"];
new_col_names = ["knee_angle_s_r", "knee_angle_s_l", "knee_vel_s_r"   , "knee_vel_s_l"   , "knee_torque_s_r"    , "knee_torque_s_l"    , "ankle_angle_s_r", "ankle_angle_s_l", "ankle_vel_s_r"   , "ankle_vel_s_l"   , "ankle_torque_s_r"    , "ankle_torque_s_l"    , "foot_angle_s_r", "foot_angle_s_l", "foot_vel_s_r"      , "foot_vel_s_l"      , "hip_angle_s_r",   "hip_angle_s_l",   "hip_vel_s_r"           , "hip_vel_s_l"           , "hip_torque_s_r"      , "hip_torque_s_l"      , "task",     "cop_z_r", "cop_x_r", "cop_z_l", "cop_x_l", "grf_y_r",         "grf_z_r", "grf_x_r",  "grf_y_l",         "grf_z_l", "grf_x_l"];
ipsi_contra_new_col_names = ["knee_angle_s_contra", "knee_angle_s_ipsi", "knee_vel_s_contra", "knee_vel_s_ipsi", "knee_torque_s_contra", "knee_torque_s_ipsi", "ankle_angle_s_contra", "ankle_angle_s_ipsi", "ankle_vel_s_contra", "ankle_vel_s_ipsi", "ankle_torque_s_contra", "ankle_torque_s_ipsi", "foot_angle_s_contra", "foot_angle_s_ipsi", "foot_vel_s_contra", "foot_vel_s_ipsi", "hip_angle_s_contra", "hip_angle_s_ipsi", "hip_vel_s_contra", "hip_vel_s_ipsi", "hip_torque_s_contra", "hip_torque_s_ipsi", "task", "cop_z_contra", "cop_x_contra", "cop_z_ipsi", "cop_x_ipsi", "grf_y_contra", "grf_z_contra", "grf_x_contra", "grf_y_ipsi", "grf_z_ipsi", "grf_x_ipsi"];

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
% Conditionally rename reconstruction flags BEFORE main renamevars
% Default config value added earlier if not provided

if strcmpi(naming_convention, 'ipsicontra') % Use top-level variable
    fprintf('Using ipsi/contra naming convention for MATLAB output.\n');
    if ismember('is_reconstructed_r', combined_data.Properties.VariableNames)
        combined_data = renamevars(combined_data, 'is_reconstructed_r', 'is_reconstructed_contra');
    end
    if ismember('is_reconstructed_l', combined_data.Properties.VariableNames)
        combined_data = renamevars(combined_data, 'is_reconstructed_l', 'is_reconstructed_ipsi');
    end
    final_new_names = ipsi_contra_new_col_names;
    % Note: Sign flips for contralateral data might be needed here if conventions differ
else % Default 'lr'
    fprintf('Using left/right naming convention for MATLAB output.\n');
    final_new_names = new_col_names;
end

% Now rename all columns listed in old_col_names using the selected convention
combined_data = renamevars(combined_data, old_col_names, final_new_names);

% Covert task data to string
combined_data.task = convertCharsToStrings(combined_data.task);

% Add a phase columns to the entire dataset
combined_data.phase = repmat(linspace(0, 1, num_points_per_step)', ...
    height(combined_data)/num_points_per_step, 1);

% Write the data to a parquet file
file_name =  'gtech_2023_phase.parquet';
% parquet_file = fullfile(output_dir,file_name);
parquetwrite(file_name,combined_data)


% --- Helper Function for Step-wise Circular Shift ---
function shifted_table = apply_step_circshift(input_table, num_points, phase_col_name)
    if isempty(input_table)
        shifted_table = input_table;
        return;
    end

    shifted_table = input_table; % Create a copy
    num_steps_actual = height(input_table) / num_points;

    if mod(height(input_table), num_points) ~= 0
         warning('Table height is not a multiple of num_points. Skipping circshift.');
         return;
    end

    % Apply the phase shift step by step
    for step = 1:num_steps_actual
        start_orig = (step-1) * num_points + 1;
        end_orig = step * num_points;

        % Calculate midpoint for shifting
        mid_point_offset = floor(num_points / 2); % Use floor for integer index
        mid_point_idx = start_orig + mid_point_offset - 1;

        % Indices for the two halves
        first_half_indices_orig = start_orig:mid_point_idx;
        second_half_indices_orig = (mid_point_idx + 1):end_orig;

        % Target indices
        target_first_half_indices = start_orig:(start_orig + length(second_half_indices_orig) - 1);
        target_second_half_indices = (target_first_half_indices(end) + 1):end_orig;

        % Perform the shift within the step boundaries
        shifted_table(target_first_half_indices, :) = input_table(second_half_indices_orig, :);
        shifted_table(target_second_half_indices, :) = input_table(first_half_indices_orig, :);
    end

    % Update the phase values after shifting
    new_phase_first_half = linspace(0.5, 1 - 1/num_points, mid_point_offset)'; % Ends just before 1
    new_phase_second_half = linspace(0, 0.5 - 1/num_points, num_points - mid_point_offset)'; % Ends just before 0.5
    
    % Check if phase column exists before trying to assign
    if ismember(phase_col_name, shifted_table.Properties.VariableNames)
        shifted_table.(phase_col_name) = repmat([new_phase_first_half; new_phase_second_half], num_steps_actual, 1);
    else
        warning('Phase column "%s" not found in table. Cannot update phase values.', phase_col_name);
    end
end