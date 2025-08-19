% Convert UMich 2021 data using heel strike events for proper stride segmentation
% This script uses the actual gait events from the Streaming data to properly
% align ipsilateral and contralateral data without using circshift assumptions.
%
% Key improvements over previous conversion:
% 1. Uses actual heel strike events (RHS/LHS) for stride segmentation
% 2. Calculates exact stride durations from event timing
% 3. Properly aligns ipsi/contra based on actual gait events
% 4. Includes phase_ipsi_dot for velocity validation
% 5. Preserves time axis for each stride
% 6. METHOD 2: Calculates velocities AFTER interpolation for exoskeleton control consistency

clearvars

% CONFIGURATION: Enable/disable data fixes
global ENABLE_DATA_FIXES;
ENABLE_DATA_FIXES = true;  % Set to false to disable all data corrections
% 
% Data fixes controlled by this flag:
% 1. Foot angle bias/sign corrections (including contralateral phase offset)
% 2. Direct pelvis from motion capture vs derived calculation
% 3. 90-degree offset correction for incline walking ankle angles  
% 4. Sign flip for decline walking knee moments

% Load Streaming data (contains both kinematics and events)
fprintf('Loading Streaming.mat...\n');
if exist('Streaming', 'var')==0
    load('Streaming.mat');
end

dataset = Streaming;

% List all subjects
subjects = fieldnames(dataset);

% Create table to store all data
total_data = table;

% Process each subject
for subject_idx = 1:length(subjects)
    
    % Get current subject
    subject = subjects{subject_idx};
    fprintf('\n========================================\n');
    fprintf('Processing %s (%d/%d)\n', subject, subject_idx, length(subjects));
    fprintf('========================================\n');
    
    % Get subject data
    subject_data = dataset.(subject);
    
    % Create standardized subject name
    subject_num = subject(end-1:end);  % Extract last 2 chars (e.g., '01' from 'AB01')
    subject_str = strcat('UM21_AB', subject_num);
    
    % Extract subject metadata from ParticipantDetails
    if isfield(subject_data, 'ParticipantDetails')
        details = subject_data.ParticipantDetails;
        
        % Find metadata fields
        age_idx = find(strcmp(details(:,1), 'Age'));
        mass_idx = find(strcmp(details(:,1), 'Bodymass'));
        height_idx = find(strcmp(details(:,1), 'Height'));
        
        % Extract values with defaults
        age = 0; body_mass = 70; height_m = 1.75; % defaults
        if ~isempty(age_idx), age = details{age_idx, 2}; end
        if ~isempty(mass_idx), body_mass = details{mass_idx, 2}; end
        if ~isempty(height_idx), height_m = details{height_idx, 2} / 1000; end % convert mm to m
        
        % Format subject metadata string
        subject_metadata = sprintf('age:%d,height_m:%.2f,weight_kg:%.1f', age, height_m, body_mass);
    else
        % Default values if no ParticipantDetails
        body_mass = 70; % kg (default for normalization)
        subject_metadata = 'age:0,height_m:1.75,weight_kg:70.0';
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process Walking data (Tread in Streaming.mat)
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    % Note: In Streaming.mat, walking data is under 'Tread' field
    if isfield(subject_data, 'Tread')
        fprintf('  Processing treadmill walking trials...\n');
        tread_data = subject_data.Tread;
        
        % Map incline codes to values
        incline_map = containers.Map(...
            {'d10', 'd5', 'i0', 'i10', 'i5'}, ...
            {-10, -5, 0, 10, 5});
        
        % Map speed codes to actual speeds
        speed_map = containers.Map(...
            {'s0x8', 's1', 's1x2', 'a0x2', 'a0x5', 'd0x2', 'd0x5'}, ...
            {0.8, 1.0, 1.2, 0.2, 0.5, 0.2, 0.5});
        
        % Process each incline condition
        incline_fields = fieldnames(tread_data);
        for incline_idx = 1:length(incline_fields)
            incline_name = incline_fields{incline_idx};
            
            % Skip if not a valid incline field
            if ~isKey(incline_map, incline_name)
                continue;
            end
            
            incline_value = incline_map(incline_name);
            incline_data = tread_data.(incline_name);
            
            % Check if events exist
            if ~isfield(incline_data, 'events')
                fprintf('    Warning: No events for incline %s, skipping\n', incline_name);
                continue;
            end
            
            events = incline_data.events;
            
            % Check for required event fields
            if ~isfield(events, 'tasks') || ~isfield(events, 'cutPoints')
                fprintf('    Warning: Missing tasks or cutPoints for %s, skipping\n', incline_name);
                continue;
            end
            
            % Process each speed segment using cutPoints
            tasks = events.tasks;
            cutPoints = events.cutPoints;
            
            for task_idx = 1:length(tasks)
                if task_idx > size(cutPoints, 1)
                    break;
                end
                
                speed_name = tasks{task_idx};
                
                % Skip if not a valid speed
                if ~isKey(speed_map, speed_name)
                    continue;
                end
                
                speed_value = speed_map(speed_name);
                
                % Get segment boundaries from cutPoints
                segment_start = cutPoints(task_idx, 1);
                segment_end = cutPoints(task_idx, 2);
                
                fprintf('    Processing %s at %s (%.1f m/s, %d deg)\n', ...
                    speed_name, incline_name, speed_value, incline_value);
                
                % Determine task type
                if incline_value < 0
                    task_type = 'decline_walking';
                    task_id = sprintf('decline_%ddeg', abs(incline_value));
                elseif incline_value > 0
                    task_type = 'incline_walking';
                    task_id = sprintf('incline_%ddeg', incline_value);
                else
                    task_type = 'level_walking';
                    task_id = 'level';
                end
                
                task_info = sprintf('incline_deg:%d,speed_m_s:%.1f,treadmill:true', ...
                    incline_value, speed_value);
                
                % Process strides using events for this segment
                stride_table = process_strides_with_segment_events(...
                    incline_data, events, segment_start, segment_end, ...
                    subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
                
                % Add to total data
                if ~isempty(stride_table)
                    total_data = [total_data; stride_table];
                    fprintf('      Added %d strides\n', height(stride_table)/150);
                end
            end
        end
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process Running data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    if isfield(subject_data, 'Run')
        fprintf('  Processing running trials...\n');
        run_data = subject_data.Run;
        
        % Map running speeds based on actual Streaming.mat structure
        % s1x8=1.8m/s, s2x0=2.0m/s, s2x2=2.2m/s, s2x4=2.4m/s  
        run_speed_map = containers.Map(...
            {'s1x8', 's2', 's2x0', 's2x2', 's2x4'}, ...
            {1.8, 2.0, 2.0, 2.2, 2.4});
        
        % Process each running speed that exists
        run_fields = fieldnames(run_data);
        for run_idx = 1:length(run_fields)
            speed_name = run_fields{run_idx};
            
            % Skip if not a valid running speed
            if ~isKey(run_speed_map, speed_name)
                continue;
            end
            
            trial_data = run_data.(speed_name);
            speed_value = run_speed_map(speed_name);
            
            % Check if events exist
            if ~isfield(trial_data, 'events')
                fprintf('    Warning: No events for %s, skipping\n', speed_name);
                continue;
            end
            
            fprintf('    Processing run at %.1f m/s\n', speed_value);
            
            events = trial_data.events;
            task_type = 'run';
            task_id = 'run';
            task_info = sprintf('speed_m_s:%.1f,treadmill:true', speed_value);
            
            % Process strides using events
            stride_table = process_strides_with_events(...
                trial_data, events, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
            
            % Add to total data
            if ~isempty(stride_table)
                total_data = [total_data; stride_table];
                fprintf('      Added %d strides\n', height(stride_table)/150);
            end
        end
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process Walk-to-Run transition data (Wrt)
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    if isfield(subject_data, 'Wtr')
        fprintf('  Processing walk-to-run transition trials...\n');
        wtr_data = subject_data.Wtr;
        
        % Process each walk-to-run trial
        wtr_fields = fieldnames(wtr_data);
        for wtr_idx = 1:length(wtr_fields)
            trial_name = wtr_fields{wtr_idx};
            trial_data = wtr_data.(trial_name);
            
            % Check if events exist
            if ~isfield(trial_data, 'events')
                fprintf('    Warning: No events for %s, skipping\n', trial_name);
                continue;
            end
            
            fprintf('    Processing walk-to-run transition: %s\n', trial_name);
            
            events = trial_data.events;
            task_type = 'level_walking';
            task_id = 'level';
            
            % Extract transition metadata if available from trial name or data
            % Default values for walk-to-run transition
            initial_speed = 1.2;  % Typical walking speed
            final_speed = 2.5;    % Typical running speed
            
            task_info = sprintf('gait_transition:true,transition_type:walk_to_run,initial_speed_m_s:%.1f,final_speed_m_s:%.1f,treadmill:true', ...
                initial_speed, final_speed);
            
            % Process strides using events
            stride_table = process_strides_with_events(...
                trial_data, events, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
            
            % Add to total data
            if ~isempty(stride_table)
                total_data = [total_data; stride_table];
                fprintf('      Added %d strides\n', height(stride_table)/150);
            end
        end
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process Sit-to-Stand transition data (Sts) using Normalized.mat CutPoints
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    if isfield(subject_data, 'Sts')
        fprintf('  Processing sit-to-stand trials...\n');
        sts_data = subject_data.Sts;
        
        % Try to load Normalized.mat for CutPoints
        normalized_data = [];
        if exist('Normalized.mat', 'file')
            temp_norm = load('Normalized.mat');
            if isfield(temp_norm, 'Normalized') && isfield(temp_norm.Normalized, subject)
                normalized_data = temp_norm.Normalized.(subject);
                fprintf('    Found Normalized.mat data for %s\n', subject);
            end
        end
        
        if isempty(normalized_data) || ~isfield(normalized_data, 'SitStand')
            fprintf('    Warning: No Normalized.mat SitStand data found, skipping Sts trials\n');
        else
            % Process using CutPoints from Normalized.mat
            stride_table = process_sts_cycles_with_normalized(...
                sts_data, normalized_data.SitStand, subject_str, subject_metadata, body_mass);
            
            % Add to total data
            if ~isempty(stride_table)
                total_data = [total_data; stride_table];
                fprintf('      Added %d sit-to-stand cycles and %d stand-to-sit cycles\n', ...
                    sum(strcmp(stride_table.task, 'sit_to_stand'))/150, ...
                    sum(strcmp(stride_table.task, 'stand_to_sit'))/150);
            end
        end
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process Stair data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    if isfield(subject_data, 'Stair')
        fprintf('  Processing stair trials...\n');
        stair_data = subject_data.Stair;
        
        % Map stair inclines to riser heights (mm)
        stair_height_map = containers.Map(...
            {'s20dg', 's25dg', 's30dg', 's35dg'}, ...
            {97, 120, 146, 162});
        
        % Map stair inclines to incline degrees
        stair_incline_map = containers.Map(...
            {'s20dg', 's25dg', 's30dg', 's35dg'}, ...
            {20, 25, 30, 35});
        
        % Process each stair trial
        stair_fields = fieldnames(stair_data);
        for stair_idx = 1:length(stair_fields)
            trial_name = stair_fields{stair_idx};
            trial_data = stair_data.(trial_name);
            
            % Check if events exist
            if ~isfield(trial_data, 'events')
                fprintf('    Warning: No events for %s, skipping\n', trial_name);
                continue;
            end
            
            % Extract incline and trial number from trial name (e.g., 's20dg_01')
            underscore_idx = strfind(trial_name, '_');
            if isempty(underscore_idx)
                fprintf('    Warning: Invalid trial name format %s, skipping\n', trial_name);
                continue;
            end
            
            incline_str = trial_name(1:underscore_idx-1);  % e.g., 's20dg'
            trial_num_str = trial_name(underscore_idx+1:end);  % e.g., '01'
            trial_num = str2double(trial_num_str);
            
            % Check if incline is supported
            if ~isKey(stair_height_map, incline_str)
                fprintf('    Warning: Unsupported incline %s for %s, skipping\n', incline_str, trial_name);
                continue;
            end
            
            % Determine task type based on trial number (odd = ascent, even = descent)
            if mod(trial_num, 2) == 1
                task_type = 'stair_ascent';
                task_id = 'stair_ascent';
            else
                task_type = 'stair_descent';
                task_id = 'stair_descent';
            end
            
            % Get metadata
            height_mm = stair_height_map(incline_str);
            incline_deg = stair_incline_map(incline_str);
            height_m = height_mm / 1000.0;  % Convert mm to meters
            
            task_info = sprintf('height_m:%.3f,incline_deg:%d,steps:1', height_m, incline_deg);
            
            fprintf('    Processing %s: %s (%.0fmm riser, %d°)\n', trial_name, task_type, height_mm, incline_deg);
            
            events = trial_data.events;
            
            % Process strides using events
            stride_table = process_strides_with_events(...
                trial_data, events, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
            
            % Add to total data
            if ~isempty(stride_table)
                total_data = [total_data; stride_table];
                fprintf('      Added %d strides\n', height(stride_table)/150);
            end
        end
    end
end

% Save the phase-indexed data
output_path = fullfile('..', '..', '..', 'converted_datasets', 'umich_2021_phase_raw.parquet');
fprintf('\n========================================\n');
fprintf('Saving to: %s\n', output_path);
fprintf('Total subjects: %d\n', length(unique(total_data.subject)));
fprintf('Total rows: %d\n', height(total_data));
fprintf('========================================\n');

parquetwrite(output_path, total_data);
fprintf('Conversion complete!\n');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Helper function to process strides within a specific segment
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function stride_table = process_strides_with_segment_events(trial_data, events, ...
    segment_start, segment_end, subject_str, subject_metadata, body_mass, task_type, task_id, task_info)
    
    % Initialize output table
    stride_table = table;
    
    % Check for required event fields
    if ~isfield(events, 'RHS') || ~isfield(events, 'LHS')
        fprintf('        Warning: Missing heel strike events\n');
        return;
    end
    
    % Get heel strike events (in frames at 100 Hz)
    RHS = events.RHS;  % Right heel strikes
    LHS = events.LHS;  % Left heel strikes
    
    % Filter heel strikes to only those within the segment
    RHS = RHS(RHS >= segment_start & RHS <= segment_end);
    LHS = LHS(LHS >= segment_start & LHS <= segment_end);
    
    if isempty(RHS) || length(RHS) < 2
        fprintf('        Warning: Not enough heel strikes in segment\n');
        return;
    end
    
    % Get stride times if available
    if isfield(events, 'RStrideTime')
        RStrideTime = events.RStrideTime;  % Stride durations in frames
        % Filter to match RHS indices
        rhs_indices = find(events.RHS >= segment_start & events.RHS <= segment_end);
        if ~isempty(rhs_indices) && rhs_indices(end) <= length(RStrideTime)
            RStrideTime = RStrideTime(rhs_indices);
        else
            % Calculate from heel strikes
            RStrideTime = diff(RHS);
        end
    else
        % Calculate from heel strikes
        RStrideTime = diff(RHS);
    end
    
    % Call the main processing function with filtered events
    stride_table = process_strides_with_events_internal(trial_data, ...
        RHS, LHS, RStrideTime, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Helper function to process strides using heel strike events
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function stride_table = process_strides_with_events(trial_data, events, ...
    subject_str, subject_metadata, body_mass, task_type, task_id, task_info)
    
    % Get heel strike events (in frames at 100 Hz)
    RHS = events.RHS;  % Right heel strikes
    LHS = events.LHS;  % Left heel strikes
    
    % Get stride times if available
    if isfield(events, 'RStrideTime')
        RStrideTime = events.RStrideTime;  % Stride durations in frames
    else
        % Calculate from heel strikes
        RStrideTime = diff(RHS);
    end
    
    % Call the main processing function
    stride_table = process_strides_with_events_internal(trial_data, ...
        RHS, LHS, RStrideTime, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Internal helper function to process strides
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function stride_table = process_strides_with_events_internal(trial_data, ...
    RHS, LHS, RStrideTime, subject_str, subject_metadata, body_mass, task_type, task_id, task_info)
    
    % Process both right-initiated and left-initiated strides
    right_strides = process_strides_single_leg(trial_data, RHS, LHS, RStrideTime, ...
        subject_str, subject_metadata, body_mass, task_type, task_id, task_info, 'right');
    
    % Calculate LStrideTime from LHS
    LStrideTime = diff(LHS);
    left_strides = process_strides_single_leg(trial_data, LHS, RHS, LStrideTime, ...
        subject_str, subject_metadata, body_mass, task_type, task_id, task_info, 'left');
    
    % Combine both tables
    stride_table = [right_strides; left_strides];
end

function stride_table = process_strides_single_leg(trial_data, ...
    ipsi_HS, contra_HS, ipsi_StrideTime, subject_str, subject_metadata, body_mass, task_type, task_id, task_info, leg_side)
    
    % Global flag for data fixes
    global ENABLE_DATA_FIXES;
    
    % Initialize output table
    stride_table = table;
    
    % Constants
    NUM_POINTS = 150;  % Points per gait cycle
    Hz = 100;  % Sampling frequency
    deg2rad = pi/180;
    
    % Plane conventions
    sagittal_plane = 1;
    frontal_plane = 2;
    transverse_plane = 3;
    
    % Process each ipsilateral stride
    num_strides = min(length(ipsi_HS)-1, length(ipsi_StrideTime));
    
    all_stride_data = [];
    
    for stride_idx = 1:num_strides
        % Get stride boundaries for ipsilateral leg
        ipsi_start_frame = ipsi_HS(stride_idx);
        ipsi_end_frame = ipsi_HS(stride_idx + 1);
        
        % Calculate stride duration and phase rate
        stride_duration_frames = ipsi_StrideTime(stride_idx);
        stride_duration_s = stride_duration_frames / Hz;
        phase_ipsi_dot = 100 / stride_duration_s;  % %/second
        
        % Use same time window for both legs to preserve natural phase offset
        % The left and right legs are naturally ~50% out of phase during walking
        % By using the same time indices, we capture this natural phase relationship
        
        % Map frame indices based on which leg is ipsilateral
        % Both legs use the SAME time window
        if strcmp(leg_side, 'right')
            % Right is ipsilateral
            r_start_frame = ipsi_start_frame;
            r_end_frame = ipsi_end_frame;
            l_start_frame = ipsi_start_frame;  % SAME time window
            l_end_frame = ipsi_end_frame;      % SAME time window
            
            % Create frame index structs for cleaner code
            ipsi_frames = r_start_frame:r_end_frame;
            contra_frames = l_start_frame:l_end_frame;
            ipsi_prefix = 'R';
            contra_prefix = 'L';
        else
            % Left is ipsilateral  
            l_start_frame = ipsi_start_frame;
            l_end_frame = ipsi_end_frame;
            r_start_frame = ipsi_start_frame;  % SAME time window
            r_end_frame = ipsi_end_frame;      % SAME time window
            
            % Create frame index structs for cleaner code
            ipsi_frames = l_start_frame:l_end_frame;
            contra_frames = r_start_frame:r_end_frame;
            ipsi_prefix = 'L';
            contra_prefix = 'R';
        end
        
        % Create time and phase arrays
        time_array = linspace(0, stride_duration_s, NUM_POINTS)';
        phase_array = linspace(0, 100, NUM_POINTS)';
        phase_dot_array = repmat(phase_ipsi_dot, NUM_POINTS, 1);
        
        % Initialize stride data structure
        stride_data = struct();
        stride_data.subject = repmat({subject_str}, NUM_POINTS, 1);
        stride_data.subject_metadata = repmat({subject_metadata}, NUM_POINTS, 1);
        stride_data.task = repmat({task_type}, NUM_POINTS, 1);
        stride_data.task_id = repmat({task_id}, NUM_POINTS, 1);
        stride_data.task_info = repmat({task_info}, NUM_POINTS, 1);
        stride_data.step = repmat(stride_idx, NUM_POINTS, 1);
        stride_data.time_s = time_array;
        stride_data.phase_ipsi = phase_array;
        stride_data.phase_ipsi_dot = phase_dot_array;
        
        % Process kinematics - interpolate to 150 points
        if isfield(trial_data, 'jointAngles')
            angles = trial_data.jointAngles;
            
            % Hip angles - use dynamic field names based on ipsi/contra
            if isfield(angles, 'RHipAngles') && isfield(angles, 'LHipAngles')
                % Get ipsi and contra data based on leg_side
                ipsi_hip_data = angles.([ipsi_prefix 'HipAngles']);
                contra_hip_data = angles.([contra_prefix 'HipAngles']);
                
                stride_data.hip_flexion_angle_ipsi_rad = interpolate_signal(...
                    ipsi_hip_data(ipsi_frames, sagittal_plane), NUM_POINTS) * deg2rad;
                stride_data.hip_flexion_angle_contra_rad = interpolate_signal(...
                    contra_hip_data(contra_frames, sagittal_plane), NUM_POINTS) * deg2rad;
                
                stride_data.hip_adduction_angle_ipsi_rad = interpolate_signal(...
                    ipsi_hip_data(ipsi_frames, frontal_plane), NUM_POINTS) * deg2rad;
                stride_data.hip_adduction_angle_contra_rad = interpolate_signal(...
                    contra_hip_data(contra_frames, frontal_plane), NUM_POINTS) * deg2rad;
                
                stride_data.hip_rotation_angle_ipsi_rad = interpolate_signal(...
                    ipsi_hip_data(ipsi_frames, transverse_plane), NUM_POINTS) * deg2rad;
                stride_data.hip_rotation_angle_contra_rad = interpolate_signal(...
                    contra_hip_data(contra_frames, transverse_plane), NUM_POINTS) * deg2rad;
            end
            
            % Knee angles
            if isfield(angles, 'RKneeAngles') && isfield(angles, 'LKneeAngles')
                % Process right knee
                r_knee_flex = interpolate_signal(...
                    angles.RKneeAngles(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
                r_knee_add = interpolate_signal(...
                    angles.RKneeAngles(r_start_frame:r_end_frame, frontal_plane), NUM_POINTS) * deg2rad;
                r_knee_rot = interpolate_signal(...
                    angles.RKneeAngles(r_start_frame:r_end_frame, transverse_plane), NUM_POINTS) * deg2rad;
                
                % Process left knee
                l_knee_flex = interpolate_signal(...
                    angles.LKneeAngles(l_start_frame:l_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
                l_knee_add = interpolate_signal(...
                    angles.LKneeAngles(l_start_frame:l_end_frame, frontal_plane), NUM_POINTS) * deg2rad;
                l_knee_rot = interpolate_signal(...
                    angles.LKneeAngles(l_start_frame:l_end_frame, transverse_plane), NUM_POINTS) * deg2rad;
                
                % Assign based on which leg is ipsilateral
                if strcmp(leg_side, 'right')
                    stride_data.knee_flexion_angle_ipsi_rad = r_knee_flex;
                    stride_data.knee_flexion_angle_contra_rad = l_knee_flex;
                    stride_data.knee_adduction_angle_ipsi_rad = r_knee_add;
                    stride_data.knee_adduction_angle_contra_rad = l_knee_add;
                    stride_data.knee_rotation_angle_ipsi_rad = r_knee_rot;
                    stride_data.knee_rotation_angle_contra_rad = l_knee_rot;
                else
                    stride_data.knee_flexion_angle_ipsi_rad = l_knee_flex;
                    stride_data.knee_flexion_angle_contra_rad = r_knee_flex;
                    stride_data.knee_adduction_angle_ipsi_rad = l_knee_add;
                    stride_data.knee_adduction_angle_contra_rad = r_knee_add;
                    stride_data.knee_rotation_angle_ipsi_rad = l_knee_rot;
                    stride_data.knee_rotation_angle_contra_rad = r_knee_rot;
                end
            end
            
            % Ankle angles
            if isfield(angles, 'RAnkleAngles') && isfield(angles, 'LAnkleAngles')
                % Process right ankle
                r_ankle_flex = interpolate_signal(...
                    angles.RAnkleAngles(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
                r_ankle_add = interpolate_signal(...
                    angles.RAnkleAngles(r_start_frame:r_end_frame, frontal_plane), NUM_POINTS) * deg2rad;
                r_ankle_rot = interpolate_signal(...
                    angles.RAnkleAngles(r_start_frame:r_end_frame, transverse_plane), NUM_POINTS) * deg2rad;
                
                % Process left ankle
                l_ankle_flex = interpolate_signal(...
                    angles.LAnkleAngles(l_start_frame:l_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
                l_ankle_add = interpolate_signal(...
                    angles.LAnkleAngles(l_start_frame:l_end_frame, frontal_plane), NUM_POINTS) * deg2rad;
                l_ankle_rot = interpolate_signal(...
                    angles.LAnkleAngles(l_start_frame:l_end_frame, transverse_plane), NUM_POINTS) * deg2rad;
                
                % Task-specific correction for incline walking ankle angles
                % DATA FIX: Apply 90-degree offset correction for incline walking ankle angles
                if ENABLE_DATA_FIXES && strcmp(task_type, 'incline_walking')
                    r_ankle_flex = apply_90_degree_correction(r_ankle_flex);
                    l_ankle_flex = apply_90_degree_correction(l_ankle_flex);
                end
                
                % Assign based on which leg is ipsilateral
                if strcmp(leg_side, 'right')
                    stride_data.ankle_dorsiflexion_angle_ipsi_rad = r_ankle_flex;
                    stride_data.ankle_dorsiflexion_angle_contra_rad = l_ankle_flex;
                    stride_data.ankle_adduction_angle_ipsi_rad = r_ankle_add;
                    stride_data.ankle_adduction_angle_contra_rad = l_ankle_add;
                    stride_data.ankle_rotation_angle_ipsi_rad = r_ankle_rot;
                    stride_data.ankle_rotation_angle_contra_rad = l_ankle_rot;
                else
                    stride_data.ankle_dorsiflexion_angle_ipsi_rad = l_ankle_flex;
                    stride_data.ankle_dorsiflexion_angle_contra_rad = r_ankle_flex;
                    stride_data.ankle_adduction_angle_ipsi_rad = l_ankle_add;
                    stride_data.ankle_adduction_angle_contra_rad = r_ankle_add;
                    stride_data.ankle_rotation_angle_ipsi_rad = l_ankle_rot;
                    stride_data.ankle_rotation_angle_contra_rad = r_ankle_rot;
                end
            end
            
            % Pelvis angles - will be calculated in segment section below
            
            % Foot angles - will be assigned in segment section below
            
            % Calculate joint angular velocities (rad/s) from interpolated angles 
            % METHOD 2: Calculate velocities AFTER interpolation for control consistency
            
            % Hip velocities - calculate from already interpolated angles
            if isfield(angles, 'RHipAngles') && isfield(angles, 'LHipAngles')
                % Calculate effective sampling rate for interpolated data
                effective_Hz = NUM_POINTS / stride_duration_s;
                
                % Calculate velocities from interpolated angles (already in stride_data)
                if strcmp(leg_side, 'right')
                    stride_data.hip_flexion_velocity_ipsi_rad_s = gradient(stride_data.hip_flexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.hip_flexion_velocity_contra_rad_s = gradient(stride_data.hip_flexion_angle_contra_rad) * effective_Hz;
                else
                    stride_data.hip_flexion_velocity_ipsi_rad_s = gradient(stride_data.hip_flexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.hip_flexion_velocity_contra_rad_s = gradient(stride_data.hip_flexion_angle_contra_rad) * effective_Hz;
                end
            end
            
            % Knee velocities - calculate from interpolated angles
            if isfield(angles, 'RKneeAngles') && isfield(angles, 'LKneeAngles')
                % Calculate velocities from already interpolated knee angles
                if strcmp(leg_side, 'right')
                    stride_data.knee_flexion_velocity_ipsi_rad_s = gradient(stride_data.knee_flexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.knee_flexion_velocity_contra_rad_s = gradient(stride_data.knee_flexion_angle_contra_rad) * effective_Hz;
                else
                    stride_data.knee_flexion_velocity_ipsi_rad_s = gradient(stride_data.knee_flexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.knee_flexion_velocity_contra_rad_s = gradient(stride_data.knee_flexion_angle_contra_rad) * effective_Hz;
                end
            end
            
            % Ankle velocities - calculate from interpolated angles  
            if isfield(angles, 'RAnkleAngles') && isfield(angles, 'LAnkleAngles')
                % Calculate velocities from already interpolated ankle angles
                if strcmp(leg_side, 'right')
                    stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.ankle_dorsiflexion_velocity_contra_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_contra_rad) * effective_Hz;
                else
                    stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_ipsi_rad) * effective_Hz;
                    stride_data.ankle_dorsiflexion_velocity_contra_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_contra_rad) * effective_Hz;
                end
            end
        end
        
        % Process kinetics
        if isfield(trial_data, 'jointMoments')
            moments = trial_data.jointMoments;
            
            % Hip moments
            if isfield(moments, 'RHipMoment') && isfield(moments, 'LHipMoment')
                ipsi_hip_moment = moments.([ipsi_prefix 'HipMoment']);
                contra_hip_moment = moments.([contra_prefix 'HipMoment']);
                
                stride_data.hip_flexion_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_hip_moment(ipsi_frames, sagittal_plane), NUM_POINTS);
                stride_data.hip_flexion_moment_contra_Nm_kg = interpolate_signal(...
                    contra_hip_moment(contra_frames, sagittal_plane), NUM_POINTS);
                
                stride_data.hip_adduction_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_hip_moment(ipsi_frames, frontal_plane), NUM_POINTS);
                stride_data.hip_adduction_moment_contra_Nm_kg = interpolate_signal(...
                    contra_hip_moment(contra_frames, frontal_plane), NUM_POINTS);
                
                stride_data.hip_rotation_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_hip_moment(ipsi_frames, transverse_plane), NUM_POINTS);
                stride_data.hip_rotation_moment_contra_Nm_kg = interpolate_signal(...
                    contra_hip_moment(contra_frames, transverse_plane), NUM_POINTS);
            end
            
            % Knee moments (note: ALWAYS negate both R and L sagittal for convention)
            if isfield(moments, 'RKneeMoment') && isfield(moments, 'LKneeMoment')
                % Process right knee moments
                r_knee_mom_flex = interpolate_signal(...
                    -moments.RKneeMoment(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS);
                r_knee_mom_add = interpolate_signal(...
                    moments.RKneeMoment(r_start_frame:r_end_frame, frontal_plane), NUM_POINTS);
                r_knee_mom_rot = interpolate_signal(...
                    moments.RKneeMoment(r_start_frame:r_end_frame, transverse_plane), NUM_POINTS);
                
                % Process left knee moments
                l_knee_mom_flex = interpolate_signal(...
                    -moments.LKneeMoment(l_start_frame:l_end_frame, sagittal_plane), NUM_POINTS);
                l_knee_mom_add = interpolate_signal(...
                    moments.LKneeMoment(l_start_frame:l_end_frame, frontal_plane), NUM_POINTS);
                l_knee_mom_rot = interpolate_signal(...
                    moments.LKneeMoment(l_start_frame:l_end_frame, transverse_plane), NUM_POINTS);
                
                % DATA FIX: Always flip sign of knee moments for consistent convention
                if ENABLE_DATA_FIXES
                    r_knee_mom_flex = -r_knee_mom_flex;  % Flip sign for consistency
                    l_knee_mom_flex = -l_knee_mom_flex;
                end
                
                % Assign based on which leg is ipsilateral
                if strcmp(leg_side, 'right')
                    stride_data.knee_flexion_moment_ipsi_Nm_kg = r_knee_mom_flex;
                    stride_data.knee_flexion_moment_contra_Nm_kg = l_knee_mom_flex;
                    stride_data.knee_adduction_moment_ipsi_Nm_kg = r_knee_mom_add;
                    stride_data.knee_adduction_moment_contra_Nm_kg = l_knee_mom_add;
                    stride_data.knee_rotation_moment_ipsi_Nm_kg = r_knee_mom_rot;
                    stride_data.knee_rotation_moment_contra_Nm_kg = l_knee_mom_rot;
                else
                    stride_data.knee_flexion_moment_ipsi_Nm_kg = l_knee_mom_flex;
                    stride_data.knee_flexion_moment_contra_Nm_kg = r_knee_mom_flex;
                    stride_data.knee_adduction_moment_ipsi_Nm_kg = l_knee_mom_add;
                    stride_data.knee_adduction_moment_contra_Nm_kg = r_knee_mom_add;
                    stride_data.knee_rotation_moment_ipsi_Nm_kg = l_knee_mom_rot;
                    stride_data.knee_rotation_moment_contra_Nm_kg = r_knee_mom_rot;
                end
            end
            
            % Ankle moments
            if isfield(moments, 'RAnkleMoment') && isfield(moments, 'LAnkleMoment')
                ipsi_ankle_moment = moments.([ipsi_prefix 'AnkleMoment']);
                contra_ankle_moment = moments.([contra_prefix 'AnkleMoment']);
                
                stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_ankle_moment(ipsi_frames, sagittal_plane), NUM_POINTS);
                stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = interpolate_signal(...
                    contra_ankle_moment(contra_frames, sagittal_plane), NUM_POINTS);
                
                stride_data.ankle_adduction_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_ankle_moment(ipsi_frames, frontal_plane), NUM_POINTS);
                stride_data.ankle_adduction_moment_contra_Nm_kg = interpolate_signal(...
                    contra_ankle_moment(contra_frames, frontal_plane), NUM_POINTS);
                
                stride_data.ankle_rotation_moment_ipsi_Nm_kg = interpolate_signal(...
                    ipsi_ankle_moment(ipsi_frames, transverse_plane), NUM_POINTS);
                stride_data.ankle_rotation_moment_contra_Nm_kg = interpolate_signal(...
                    contra_ankle_moment(contra_frames, transverse_plane), NUM_POINTS);
            end
        else
            % Fill kinetics with NaN when jointMoments field doesn't exist (e.g., Stair data)
            nan_vector = NaN(NUM_POINTS, 1);
            
            % Hip moments
            stride_data.hip_flexion_moment_ipsi_Nm_kg = nan_vector;
            stride_data.hip_flexion_moment_contra_Nm_kg = nan_vector;
            stride_data.hip_adduction_moment_ipsi_Nm_kg = nan_vector;
            stride_data.hip_adduction_moment_contra_Nm_kg = nan_vector;
            stride_data.hip_rotation_moment_ipsi_Nm_kg = nan_vector;
            stride_data.hip_rotation_moment_contra_Nm_kg = nan_vector;
            
            % Knee moments
            stride_data.knee_flexion_moment_ipsi_Nm_kg = nan_vector;
            stride_data.knee_flexion_moment_contra_Nm_kg = nan_vector;
            stride_data.knee_adduction_moment_ipsi_Nm_kg = nan_vector;
            stride_data.knee_adduction_moment_contra_Nm_kg = nan_vector;
            stride_data.knee_rotation_moment_ipsi_Nm_kg = nan_vector;
            stride_data.knee_rotation_moment_contra_Nm_kg = nan_vector;
            
            % Ankle moments
            stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = nan_vector;
            stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = nan_vector;
            stride_data.ankle_adduction_moment_ipsi_Nm_kg = nan_vector;
            stride_data.ankle_adduction_moment_contra_Nm_kg = nan_vector;
            stride_data.ankle_rotation_moment_ipsi_Nm_kg = nan_vector;
            stride_data.ankle_rotation_moment_contra_Nm_kg = nan_vector;
        end
        
        % Calculate segment angles using FOOT-UP approach with corrected foot angles
        if isfield(angles, 'RFootProgressAngles') && isfield(angles, 'RAnkleAngles') && isfield(angles, 'RKneeAngles')
            % Get foot angles in time domain and apply corrections FIRST
            r_foot_raw = interpolate_signal(...
                -angles.RFootProgressAngles(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
            l_foot_raw = interpolate_signal(...
                -angles.LFootProgressAngles(l_start_frame:l_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
            
            % Apply foot angle corrections before using for segment calculations
            % DATA FIX START: Fix foot angle bias/sign
            if ENABLE_DATA_FIXES
                offset_index =  strcmp(leg_side, 'left'); % Do we offset the leg to account for the 50% phase offset?
                r_foot_corrected = apply_foot_angle_correction(r_foot_raw, offset_index);
                l_foot_corrected = apply_foot_angle_correction(l_foot_raw, ~offset_index);
            else
                r_foot_corrected = r_foot_raw;
                l_foot_corrected = l_foot_raw;
            end
            % DATA FIX END: Fix foot angle bias/sign
            
            % Get ankle dorsiflexion angles
            r_ankle_angles_rad = angles.RAnkleAngles(r_start_frame:r_end_frame, sagittal_plane) * deg2rad;
            l_ankle_angles_rad = angles.LAnkleAngles(l_start_frame:l_end_frame, sagittal_plane) * deg2rad;
            
            % Interpolate ankle angles to 150 points
            r_ankle_interp = interpolate_signal(r_ankle_angles_rad, NUM_POINTS);
            l_ankle_interp = interpolate_signal(l_ankle_angles_rad, NUM_POINTS);
            
            % Calculate shank angle = corrected_foot_angle + ankle_dorsiflexion
            r_shank_angles_150pt = r_foot_corrected - r_ankle_interp;
            l_shank_angles_150pt = l_foot_corrected - l_ankle_interp;
            
            % Get knee angles for segment calculation (positive for segment chain)
            r_knee_for_segments = angles.RKneeAngles(r_start_frame:r_end_frame, sagittal_plane) * deg2rad;
            l_knee_for_segments = angles.LKneeAngles(l_start_frame:l_end_frame, sagittal_plane) * deg2rad;
            
            % Interpolate positive knee angles for segment calculations
            r_knee_segment_interp = interpolate_signal(r_knee_for_segments, NUM_POINTS);
            l_knee_segment_interp = interpolate_signal(l_knee_for_segments, NUM_POINTS);
            
            % Calculate thigh angle = shank_angle + knee_relative_angle (positive)
            r_thigh_angles_150pt = r_shank_angles_150pt + r_knee_segment_interp;
            l_thigh_angles_150pt = l_shank_angles_150pt + l_knee_segment_interp;
            
            % Get hip flexion angles and interpolate (for pelvis calculation)
            r_hip_angles_rad = angles.RHipAngles(r_start_frame:r_end_frame, sagittal_plane) * deg2rad;
            l_hip_angles_rad = angles.LHipAngles(l_start_frame:l_end_frame, sagittal_plane) * deg2rad;
            
            r_hip_interp = interpolate_signal(r_hip_angles_rad, NUM_POINTS);
            l_hip_interp = interpolate_signal(l_hip_angles_rad, NUM_POINTS);
            
            % Assign pelvis angles directly from motion capture data (like other planes)
            % DATA FIX: Use direct pelvis from motion capture instead of derived calculation
            if ENABLE_DATA_FIXES
                stride_data.pelvis_sagittal_angle_rad = interpolate_signal(...
                    angles.RPelvisAngles(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
            else
                % Alternative: derive from kinematic chain (original approach would go here)
                % For now, still use direct pelvis but this could be changed
                stride_data.pelvis_sagittal_angle_rad = interpolate_signal(...
                    angles.RPelvisAngles(r_start_frame:r_end_frame, sagittal_plane), NUM_POINTS) * deg2rad;
            end
            stride_data.pelvis_frontal_angle_rad = interpolate_signal(...
                angles.RPelvisAngles(r_start_frame:r_end_frame, frontal_plane), NUM_POINTS) * deg2rad;
            stride_data.pelvis_transverse_angle_rad = interpolate_signal(...
                angles.RPelvisAngles(r_start_frame:r_end_frame, transverse_plane), NUM_POINTS) * deg2rad;
            
            % Calculate velocities from interpolated angles using effective sampling rate
            effective_Hz = NUM_POINTS / stride_duration_s;  % Effective sampling rate for 150 points
            r_thigh_velocity = gradient(r_thigh_angles_150pt) * effective_Hz;
            r_shank_velocity = gradient(r_shank_angles_150pt) * effective_Hz;
            l_thigh_velocity = gradient(l_thigh_angles_150pt) * effective_Hz;
            l_shank_velocity = gradient(l_shank_angles_150pt) * effective_Hz;
            r_foot_velocity = gradient(r_foot_corrected) * effective_Hz;
            l_foot_velocity = gradient(l_foot_corrected) * effective_Hz;
            
            % No corrections needed with foot-up approach - angles should be biomechanically correct
            
            % Assign segment angles and velocities based on which leg is ipsilateral
            if strcmp(leg_side, 'right')
                stride_data.foot_sagittal_angle_ipsi_rad = r_foot_corrected;
                stride_data.foot_sagittal_angle_contra_rad = l_foot_corrected;
                stride_data.foot_sagittal_velocity_ipsi_rad_s = r_foot_velocity;
                stride_data.foot_sagittal_velocity_contra_rad_s = l_foot_velocity;
                stride_data.thigh_sagittal_angle_ipsi_rad = r_thigh_angles_150pt;
                stride_data.thigh_sagittal_angle_contra_rad = l_thigh_angles_150pt;
                stride_data.shank_sagittal_angle_ipsi_rad = r_shank_angles_150pt;
                stride_data.shank_sagittal_angle_contra_rad = l_shank_angles_150pt;
                stride_data.thigh_sagittal_velocity_ipsi_rad_s = r_thigh_velocity;
                stride_data.thigh_sagittal_velocity_contra_rad_s = l_thigh_velocity;
                stride_data.shank_sagittal_velocity_ipsi_rad_s = r_shank_velocity;
                stride_data.shank_sagittal_velocity_contra_rad_s = l_shank_velocity;
            else
                stride_data.foot_sagittal_angle_ipsi_rad = l_foot_corrected;
                stride_data.foot_sagittal_angle_contra_rad = r_foot_corrected;
                stride_data.foot_sagittal_velocity_ipsi_rad_s = l_foot_velocity;
                stride_data.foot_sagittal_velocity_contra_rad_s = r_foot_velocity;
                stride_data.thigh_sagittal_angle_ipsi_rad = l_thigh_angles_150pt;
                stride_data.thigh_sagittal_angle_contra_rad = r_thigh_angles_150pt;
                stride_data.shank_sagittal_angle_ipsi_rad = l_shank_angles_150pt;
                stride_data.shank_sagittal_angle_contra_rad = r_shank_angles_150pt;
                stride_data.thigh_sagittal_velocity_ipsi_rad_s = l_thigh_velocity;
                stride_data.thigh_sagittal_velocity_contra_rad_s = r_thigh_velocity;
                stride_data.shank_sagittal_velocity_ipsi_rad_s = l_shank_velocity;
                stride_data.shank_sagittal_velocity_contra_rad_s = r_shank_velocity;
            end
        end
        
        % Process ground reaction forces (if available)
        if isfield(trial_data, 'forceplates')
            forces = trial_data.forceplates;
            
            % Force directions (adjust for coordinate system)
            x = 2;  % AP (swapped from z)
            y = 3;  % Vertical (will negate)
            z = 1;  % ML (swapped from x)
            
            if isfield(forces, 'RForce') && isfield(forces, 'LForce')
                % Note: Forces sampled at 1000 Hz, so downsample
                % Calculate force indices (forces at 1000 Hz, kinematics at 100 Hz)
                r_force_start = (r_start_frame - 1) * 10 + 1;  % Convert to 1000 Hz index
                r_force_end = min(r_end_frame * 10, size(forces.RForce, 1));
                l_force_start = (l_start_frame - 1) * 10 + 1;
                l_force_end = min(l_end_frame * 10, size(forces.LForce, 1));
                
                % Extract and downsample forces (every 10th sample)
                r_force_indices = r_force_start:10:r_force_end;
                l_force_indices = l_force_start:10:l_force_end;
                
                % Ensure indices are valid
                r_force_indices = r_force_indices(r_force_indices <= size(forces.RForce, 1));
                l_force_indices = l_force_indices(l_force_indices <= size(forces.LForce, 1));
                
                if ~isempty(r_force_indices) && ~isempty(l_force_indices)
                    % Interpolate forces separately, then assign as ipsi/contra and normalize by weight
                    
                    % Anterior forces (previously AP) - flip sign for correct braking/propulsion convention
                    r_force_anterior = interpolate_signal(-forces.RForce(r_force_indices, x), NUM_POINTS);
                    l_force_anterior = interpolate_signal(-forces.LForce(l_force_indices, x), NUM_POINTS);
                    
                    % Vertical forces (negate for up positive)
                    r_force_vert = interpolate_signal(-forces.RForce(r_force_indices, y), NUM_POINTS);
                    l_force_vert = interpolate_signal(-forces.LForce(l_force_indices, y), NUM_POINTS);
                    
                    % Lateral forces (previously ML) - flip sign for left leg to maintain convention
                    r_force_lateral = interpolate_signal(forces.RForce(r_force_indices, z), NUM_POINTS);
                    l_force_lateral = interpolate_signal(-forces.LForce(l_force_indices, z), NUM_POINTS);
                    
                    % Assign forces based on which leg is ipsilateral and normalize by body weight to get BW
                    body_weight_N = body_mass * 9.81;  % Convert mass to weight for normalization
                    
                    if strcmp(leg_side, 'right')
                        % Right leg is ipsilateral
                        stride_data.anterior_grf_ipsi_BW = r_force_anterior / body_weight_N;
                        stride_data.anterior_grf_contra_BW = l_force_anterior / body_weight_N;
                        stride_data.vertical_grf_ipsi_BW = r_force_vert / body_weight_N;
                        stride_data.vertical_grf_contra_BW = l_force_vert / body_weight_N;
                        stride_data.lateral_grf_ipsi_BW = r_force_lateral / body_weight_N;
                        stride_data.lateral_grf_contra_BW = l_force_lateral / body_weight_N;
                    else
                        % Left leg is ipsilateral
                        stride_data.anterior_grf_ipsi_BW = l_force_anterior / body_weight_N;
                        stride_data.anterior_grf_contra_BW = r_force_anterior / body_weight_N;
                        stride_data.vertical_grf_ipsi_BW = l_force_vert / body_weight_N;
                        stride_data.vertical_grf_contra_BW = r_force_vert / body_weight_N;
                        stride_data.lateral_grf_ipsi_BW = l_force_lateral / body_weight_N;
                        stride_data.lateral_grf_contra_BW = r_force_lateral / body_weight_N;
                    end
                end
            end
            
            % Center of pressure - split into ipsi/contra
            if isfield(forces, 'RCoP') && isfield(forces, 'LCoP') && exist('r_force_indices', 'var') && exist('l_force_indices', 'var')
                if ~isempty(r_force_indices) && ~isempty(l_force_indices)
                    % Interpolate CoP for each foot
                    % Apply coordinate transformations to match standard convention
                    r_cop_anterior = interpolate_signal(-forces.RCoP(r_force_indices, x), NUM_POINTS);  % Negate X for anterior positive
                    l_cop_anterior = interpolate_signal(-forces.LCoP(l_force_indices, x), NUM_POINTS);
                    
                    r_cop_lateral = interpolate_signal(forces.RCoP(r_force_indices, z), NUM_POINTS);   % Z is lateral
                    l_cop_lateral = interpolate_signal(-forces.LCoP(l_force_indices, z), NUM_POINTS);  % Negate left for consistency
                    
                    r_cop_vertical = interpolate_signal(-forces.RCoP(r_force_indices, y), NUM_POINTS); % Y is vertical
                    l_cop_vertical = interpolate_signal(-forces.LCoP(l_force_indices, y), NUM_POINTS);
                    
                    % Assign based on which leg is ipsilateral
                    if strcmp(leg_side, 'right')
                        % Right leg is ipsilateral
                        stride_data.cop_anterior_ipsi_m = r_cop_anterior;
                        stride_data.cop_anterior_contra_m = l_cop_anterior;
                        stride_data.cop_lateral_ipsi_m = r_cop_lateral;
                        stride_data.cop_lateral_contra_m = l_cop_lateral;
                        stride_data.cop_vertical_ipsi_m = r_cop_vertical;
                        stride_data.cop_vertical_contra_m = l_cop_vertical;
                    else
                        % Left leg is ipsilateral
                        stride_data.cop_anterior_ipsi_m = l_cop_anterior;
                        stride_data.cop_anterior_contra_m = r_cop_anterior;
                        stride_data.cop_lateral_ipsi_m = l_cop_lateral;
                        stride_data.cop_lateral_contra_m = r_cop_lateral;
                        stride_data.cop_vertical_ipsi_m = l_cop_vertical;
                        stride_data.cop_vertical_contra_m = r_cop_vertical;
                    end
                end
            end
        else
            % Fill GRF and COP with NaN when forceplates field doesn't exist (e.g., Stair data)
            nan_vector = NaN(NUM_POINTS, 1);
            
            % Ground reaction forces
            stride_data.anterior_grf_ipsi_BW = nan_vector;
            stride_data.anterior_grf_contra_BW = nan_vector;
            stride_data.vertical_grf_ipsi_BW = nan_vector;
            stride_data.vertical_grf_contra_BW = nan_vector;
            stride_data.lateral_grf_ipsi_BW = nan_vector;
            stride_data.lateral_grf_contra_BW = nan_vector;
            
            % Center of pressure
            stride_data.cop_anterior_ipsi_m = nan_vector;
            stride_data.cop_anterior_contra_m = nan_vector;
            stride_data.cop_lateral_ipsi_m = nan_vector;
            stride_data.cop_lateral_contra_m = nan_vector;
            stride_data.cop_vertical_ipsi_m = nan_vector;
            stride_data.cop_vertical_contra_m = nan_vector;
        end
        
        % Convert struct to table and append
        stride_table_temp = struct2table(stride_data);
        
        if stride_idx == 1
            all_stride_data = stride_table_temp;
        else
            all_stride_data = [all_stride_data; stride_table_temp];
        end
    end
    
    stride_table = all_stride_data;
end

% Helper function to interpolate signal to fixed number of points
function interpolated = interpolate_signal(signal, num_points)
    if isempty(signal)
        interpolated = zeros(num_points, 1);
        return;
    end
    
    % Create original and target indices
    original_length = length(signal);
    original_indices = linspace(1, num_points, original_length);
    target_indices = 1:num_points;
    
    % Interpolate
    interpolated = interp1(original_indices, signal, target_indices, 'linear', 'extrap')';
end

% Helper function to apply foot angle corrections (matching phase script)
function corrected_angle = apply_foot_angle_correction(foot_angle_rad, contra)
    % Constants
    midstance_idx_1 = 95;  % 70% of 150-point cycle
    midstance_idx_2 = 100;  % 73% of 150-point cycle
    deg2rad_factor = pi/180;

    if contra
        midstance_idx_1 = mod(midstance_idx_1 + 150/2, 150);
        midstance_idx_2 = mod(midstance_idx_2 + 150/2, 150);
    end
    
    % Step 1: Apply iterative 90-degree offset correction to first point
    first_point = foot_angle_rad(1);
    
    % Keep applying ±90 degree offsets until within range [-50, 50] degrees
    while first_point > deg2rad_factor * 50  % Greater than 50 degrees
        foot_angle_rad = foot_angle_rad - pi/2;
        first_point = first_point - pi/2;
    end
    
    while first_point < -deg2rad_factor * 50  % Less than -50 degrees
        foot_angle_rad = foot_angle_rad + pi/2;
        first_point = first_point + pi/2;
    end
    
    % Step 2: Check 70% midstance point for sign flip
    midstance_angle_1 = foot_angle_rad(midstance_idx_1);
    midstance_angle_2 = foot_angle_rad(midstance_idx_2);
    if midstance_angle_1 > 0  && midstance_angle_2 > 0 % Should be negative (plantarflexion at 70% cycle)
        foot_angle_rad = -foot_angle_rad;
    end
    
    corrected_angle = foot_angle_rad;
end

% Helper function for 90-degree correction only (for ankle in incline)
function corrected = apply_90_degree_correction(angle_rad)
    % Apply iterative 90-degree offsets until within [-50, 50] degrees
    deg2rad_factor = pi/180;
    first_point = angle_rad(1);
    
    while first_point > deg2rad_factor * 50
        angle_rad = angle_rad - pi/2;
        first_point = first_point - pi/2;
    end
    
    while first_point < -deg2rad_factor * 50
        angle_rad = angle_rad + pi/2;
        first_point = first_point + pi/2;
    end
    
    corrected = angle_rad;
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Helper function to process Sts cycles using CutPoints from Normalized.mat
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function stride_table = process_sts_cycles_with_normalized(sts_data, sitstand_data, subject_str, subject_metadata, body_mass)
    
    % Initialize output table
    stride_table = table;
    
    % Check for required SitStand structure
    if ~isfield(sitstand_data, 'ss') || ~isfield(sitstand_data.ss, 'sit2stand')
        fprintf('        Warning: Missing sit2stand data in Normalized.mat\n');
        return;
    end
    
    % Get CutPoints from sit2stand data
    if ~isfield(sitstand_data.ss.sit2stand, 'CutPoints')
        fprintf('        Warning: Missing CutPoints in sit2stand data\n');
        return;
    end
    
    cutpoints = sitstand_data.ss.sit2stand.CutPoints;
    fprintf('        Found %d cycles with CutPoints\n', size(cutpoints, 1));
    
    % Process each cycle (2 cycles per Sts trial, 14 total cycles for 7 trials)
    sts_fields = fieldnames(sts_data);
    cycle_idx = 1;
    
    for trial_idx = 1:length(sts_fields)
        trial_name = sts_fields{trial_idx};
        trial_data = sts_data.(trial_name);
        
        % Each trial should have 2 cycles
        cycles_per_trial = 2;
        for cycle_in_trial = 1:cycles_per_trial
            if cycle_idx > size(cutpoints, 1)
                fprintf('        Warning: More expected cycles than CutPoints available\n');
                break;
            end
            
            cp = cutpoints(cycle_idx, :);
            fprintf('        Processing %s cycle %d: CutPoints [%d %d %d %d]\n', ...
                trial_name, cycle_in_trial, cp(1), cp(2), cp(3), cp(4));
            
            % Process sit_to_stand (indices 1 to 2)
            sit2stand_table = process_single_sts_cycle(trial_data, cp(1), cp(2), ...
                'sit_to_stand', subject_str, subject_metadata, body_mass, trial_name, cycle_in_trial);
            
            % Process stand_to_sit (indices 3 to 4)
            stand2sit_table = process_single_sts_cycle(trial_data, cp(3), cp(4), ...
                'stand_to_sit', subject_str, subject_metadata, body_mass, trial_name, cycle_in_trial);
            
            % Add both cycles to output
            if ~isempty(sit2stand_table)
                stride_table = [stride_table; sit2stand_table];
            end
            if ~isempty(stand2sit_table)
                stride_table = [stride_table; stand2sit_table];
            end
            
            cycle_idx = cycle_idx + 1;
        end
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Helper function to process a single sit-to-stand or stand-to-sit cycle
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function cycle_table = process_single_sts_cycle(trial_data, start_idx, end_idx, task_type, subject_str, subject_metadata, body_mass, trial_name, cycle_num)
    
    % Constants
    NUM_POINTS = 150;
    nan_vector = NaN(NUM_POINTS, 1);   % Define NaN vector for unmeasured kinetic variables
    zero_vector = zeros(NUM_POINTS, 1); % Define zero vector for unused kinematic variables
    
    % Initialize output
    cycle_table = table;
    
    % Check data availability
    if ~isfield(trial_data, 'jointAngles')
        fprintf('          Warning: No jointAngles data for %s\n', trial_name);
        return;
    end
    
    % Get cycle length
    cycle_length = end_idx - start_idx + 1;
    if cycle_length < 5
        fprintf('          Warning: Cycle too short (%d points) for %s\n', cycle_length, task_type);
        return;
    end
    
    % Create step identifier (use numeric cycle counter like walking data)
    step_id = cycle_num;  % Keep as numeric for consistency with walking data
    
    % Default metadata
    chair_height = 0.45;  % Standard chair height in meters
    task_info = sprintf('chair_height_m:%.2f,arms_used:false,speed:normal', chair_height);
    
    % Initialize stride data structure
    stride_data = struct();
    stride_data.subject = repmat({subject_str}, NUM_POINTS, 1);
    stride_data.task = repmat({task_type}, NUM_POINTS, 1);
    stride_data.task_id = repmat({task_type}, NUM_POINTS, 1);
    stride_data.task_info = repmat({task_info}, NUM_POINTS, 1);
    stride_data.step = repmat(step_id, NUM_POINTS, 1);  % Numeric array, not cell array
    stride_data.subject_metadata = repmat({subject_metadata}, NUM_POINTS, 1);
    
    % Time and phase information
    cycle_duration_s = (end_idx - start_idx) / 100;  % Assuming 100 Hz sampling
    stride_data.time_s = linspace(0, cycle_duration_s, NUM_POINTS)';
    stride_data.phase_ipsi = (0:(NUM_POINTS-1))' / (NUM_POINTS-1) * 100;
    stride_data.phase_ipsi_dot = repmat(100 / cycle_duration_s, NUM_POINTS, 1);  % %/second
    
    % Process joint angles
    angles = trial_data.jointAngles;
    
    % Hip angles (convert degrees to radians)
    if isfield(angles, 'LHipAngles') && isfield(angles, 'RHipAngles')
        % Sagittal plane (flexion)
        l_hip_flex = interpolate_signal(deg2rad(angles.LHipAngles(start_idx:end_idx, 1)), NUM_POINTS);
        r_hip_flex = interpolate_signal(deg2rad(angles.RHipAngles(start_idx:end_idx, 1)), NUM_POINTS);
        
        % Frontal plane (adduction) if available
        if size(angles.LHipAngles, 2) >= 2
            l_hip_add = interpolate_signal(deg2rad(angles.LHipAngles(start_idx:end_idx, 2)), NUM_POINTS);
            r_hip_add = interpolate_signal(deg2rad(angles.RHipAngles(start_idx:end_idx, 2)), NUM_POINTS);
        else
            l_hip_add = zeros(NUM_POINTS, 1);
            r_hip_add = zeros(NUM_POINTS, 1);
        end
        
        % Transverse plane (rotation) if available
        if size(angles.LHipAngles, 2) >= 3
            l_hip_rot = interpolate_signal(deg2rad(angles.LHipAngles(start_idx:end_idx, 3)), NUM_POINTS);
            r_hip_rot = interpolate_signal(deg2rad(angles.RHipAngles(start_idx:end_idx, 3)), NUM_POINTS);
        else
            l_hip_rot = zeros(NUM_POINTS, 1);
            r_hip_rot = zeros(NUM_POINTS, 1);
        end
        
        % For bilateral task, use left as ipsi, right as contra
        stride_data.hip_flexion_angle_ipsi_rad = l_hip_flex;
        stride_data.hip_flexion_angle_contra_rad = r_hip_flex;
        stride_data.hip_adduction_angle_ipsi_rad = l_hip_add;
        stride_data.hip_adduction_angle_contra_rad = r_hip_add;
        stride_data.hip_rotation_angle_ipsi_rad = l_hip_rot;
        stride_data.hip_rotation_angle_contra_rad = r_hip_rot;
    end
    
    % Knee angles
    if isfield(angles, 'LKneeAngles') && isfield(angles, 'RKneeAngles')
        % Sagittal plane (flexion)
        l_knee_flex = interpolate_signal(deg2rad(angles.LKneeAngles(start_idx:end_idx, 1)), NUM_POINTS);
        r_knee_flex = interpolate_signal(deg2rad(angles.RKneeAngles(start_idx:end_idx, 1)), NUM_POINTS);
        
        % Frontal and transverse planes (set to zero - not typically meaningful for STS)
        l_knee_add = zeros(NUM_POINTS, 1);
        r_knee_add = zeros(NUM_POINTS, 1);
        l_knee_rot = zeros(NUM_POINTS, 1);
        r_knee_rot = zeros(NUM_POINTS, 1);
        
        stride_data.knee_flexion_angle_ipsi_rad = l_knee_flex;
        stride_data.knee_flexion_angle_contra_rad = r_knee_flex;
        stride_data.knee_adduction_angle_ipsi_rad = l_knee_add;
        stride_data.knee_adduction_angle_contra_rad = r_knee_add;
        stride_data.knee_rotation_angle_ipsi_rad = l_knee_rot;
        stride_data.knee_rotation_angle_contra_rad = r_knee_rot;
    end
    
    % Ankle angles
    if isfield(angles, 'LAnkleAngles') && isfield(angles, 'RAnkleAngles')
        % Sagittal plane (dorsiflexion)
        l_ankle_flex = interpolate_signal(deg2rad(angles.LAnkleAngles(start_idx:end_idx, 1)), NUM_POINTS);
        r_ankle_flex = interpolate_signal(deg2rad(angles.RAnkleAngles(start_idx:end_idx, 1)), NUM_POINTS);
        
        % Frontal and transverse planes (set to zero)
        l_ankle_add = zeros(NUM_POINTS, 1);
        r_ankle_add = zeros(NUM_POINTS, 1);
        l_ankle_rot = zeros(NUM_POINTS, 1);
        r_ankle_rot = zeros(NUM_POINTS, 1);
        
        stride_data.ankle_dorsiflexion_angle_ipsi_rad = l_ankle_flex;
        stride_data.ankle_dorsiflexion_angle_contra_rad = r_ankle_flex;
        stride_data.ankle_adduction_angle_ipsi_rad = l_ankle_add;
        stride_data.ankle_adduction_angle_contra_rad = r_ankle_add;
        stride_data.ankle_rotation_angle_ipsi_rad = l_ankle_rot;
        stride_data.ankle_rotation_angle_contra_rad = r_ankle_rot;
    end
    
    % Pelvis angles (if available)
    if isfield(angles, 'LPelvisAngles')
        % Use left pelvis as representative
        pelvis_sag = interpolate_signal(deg2rad(angles.LPelvisAngles(start_idx:end_idx, 1)), NUM_POINTS);
        if size(angles.LPelvisAngles, 2) >= 2
            pelvis_front = interpolate_signal(deg2rad(angles.LPelvisAngles(start_idx:end_idx, 2)), NUM_POINTS);
        else
            pelvis_front = zeros(NUM_POINTS, 1);
        end
        if size(angles.LPelvisAngles, 2) >= 3
            pelvis_trans = interpolate_signal(deg2rad(angles.LPelvisAngles(start_idx:end_idx, 3)), NUM_POINTS);
        else
            pelvis_trans = zeros(NUM_POINTS, 1);
        end
        
        stride_data.pelvis_sagittal_angle_rad = pelvis_sag;
        stride_data.pelvis_frontal_angle_rad = pelvis_front;
        stride_data.pelvis_transverse_angle_rad = pelvis_trans;
    end
    
    % Calculate joint angular velocities from angles
    effective_Hz = NUM_POINTS / cycle_duration_s;
    
    % Hip velocities
    if isfield(angles, 'LHipAngles') && isfield(angles, 'RHipAngles')
        stride_data.hip_flexion_velocity_ipsi_rad_s = gradient(stride_data.hip_flexion_angle_ipsi_rad) * effective_Hz;
        stride_data.hip_flexion_velocity_contra_rad_s = gradient(stride_data.hip_flexion_angle_contra_rad) * effective_Hz;
    else
        stride_data.hip_flexion_velocity_ipsi_rad_s = zero_vector;
        stride_data.hip_flexion_velocity_contra_rad_s = zero_vector;
    end
    
    % Knee velocities
    if isfield(angles, 'LKneeAngles') && isfield(angles, 'RKneeAngles')
        stride_data.knee_flexion_velocity_ipsi_rad_s = gradient(stride_data.knee_flexion_angle_ipsi_rad) * effective_Hz;
        stride_data.knee_flexion_velocity_contra_rad_s = gradient(stride_data.knee_flexion_angle_contra_rad) * effective_Hz;
    else
        stride_data.knee_flexion_velocity_ipsi_rad_s = zero_vector;
        stride_data.knee_flexion_velocity_contra_rad_s = zero_vector;
    end
    
    % Ankle velocities
    if isfield(angles, 'LAnkleAngles') && isfield(angles, 'RAnkleAngles')
        stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_ipsi_rad) * effective_Hz;
        stride_data.ankle_dorsiflexion_velocity_contra_rad_s = gradient(stride_data.ankle_dorsiflexion_angle_contra_rad) * effective_Hz;
    else
        stride_data.ankle_dorsiflexion_velocity_ipsi_rad_s = zero_vector;
        stride_data.ankle_dorsiflexion_velocity_contra_rad_s = zero_vector;
    end
    
    % Segment angles (simplified for STS - no complex foot calculations)
    stride_data.foot_sagittal_angle_ipsi_rad = zero_vector;
    stride_data.foot_sagittal_angle_contra_rad = zero_vector;
    stride_data.foot_sagittal_velocity_ipsi_rad_s = zero_vector;
    stride_data.foot_sagittal_velocity_contra_rad_s = zero_vector;
    stride_data.shank_sagittal_angle_ipsi_rad = zero_vector;
    stride_data.shank_sagittal_angle_contra_rad = zero_vector;
    stride_data.shank_sagittal_velocity_ipsi_rad_s = zero_vector;
    stride_data.shank_sagittal_velocity_contra_rad_s = zero_vector;
    stride_data.thigh_sagittal_angle_ipsi_rad = zero_vector;
    stride_data.thigh_sagittal_angle_contra_rad = zero_vector;
    stride_data.thigh_sagittal_velocity_ipsi_rad_s = zero_vector;
    stride_data.thigh_sagittal_velocity_contra_rad_s = zero_vector;
    
    % Initialize other required columns with NaN for unmeasured kinetic data
    % Joint moments (not measured in sit-to-stand)
    stride_data.hip_flexion_moment_ipsi_Nm_kg = nan_vector;
    stride_data.hip_flexion_moment_contra_Nm_kg = nan_vector;
    stride_data.hip_adduction_moment_ipsi_Nm_kg = nan_vector;
    stride_data.hip_adduction_moment_contra_Nm_kg = nan_vector;
    stride_data.hip_rotation_moment_ipsi_Nm_kg = nan_vector;
    stride_data.hip_rotation_moment_contra_Nm_kg = nan_vector;
    stride_data.knee_flexion_moment_ipsi_Nm_kg = nan_vector;
    stride_data.knee_flexion_moment_contra_Nm_kg = nan_vector;
    stride_data.knee_adduction_moment_ipsi_Nm_kg = nan_vector;
    stride_data.knee_adduction_moment_contra_Nm_kg = nan_vector;
    stride_data.knee_rotation_moment_ipsi_Nm_kg = nan_vector;
    stride_data.knee_rotation_moment_contra_Nm_kg = nan_vector;
    stride_data.ankle_dorsiflexion_moment_ipsi_Nm_kg = nan_vector;
    stride_data.ankle_dorsiflexion_moment_contra_Nm_kg = nan_vector;
    stride_data.ankle_adduction_moment_ipsi_Nm_kg = nan_vector;
    stride_data.ankle_adduction_moment_contra_Nm_kg = nan_vector;
    stride_data.ankle_rotation_moment_ipsi_Nm_kg = nan_vector;
    stride_data.ankle_rotation_moment_contra_Nm_kg = nan_vector;
    
    % Ground reaction forces (not measured)
    stride_data.vertical_grf_ipsi_BW = nan_vector;
    stride_data.vertical_grf_contra_BW = nan_vector;
    stride_data.anterior_grf_ipsi_BW = nan_vector;
    stride_data.anterior_grf_contra_BW = nan_vector;
    stride_data.lateral_grf_ipsi_BW = nan_vector;
    stride_data.lateral_grf_contra_BW = nan_vector;
    
    % Center of pressure (not measured)
    stride_data.cop_anterior_ipsi_m = nan_vector;
    stride_data.cop_anterior_contra_m = nan_vector;
    stride_data.cop_lateral_ipsi_m = nan_vector;
    stride_data.cop_lateral_contra_m = nan_vector;
    stride_data.cop_vertical_ipsi_m = nan_vector;
    stride_data.cop_vertical_contra_m = nan_vector;
    
    % Convert struct to table
    cycle_table = struct2table(stride_data);
end

