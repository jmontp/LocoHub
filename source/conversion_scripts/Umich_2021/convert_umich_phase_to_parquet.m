clearvars -except Normalized


%Load dataset
if exist('Normalized', 'var')==0
    load('Normalized.mat');
end

dataset = Normalized;

% List all the entries in the dataset. These are the subjects
subjects = fieldnames(dataset);

% Create a table to store the data
total_data = table;

% Iterate through all the subjects
for subject_idx = 1:length(subjects)

    % Get the current subject
    subject = subjects{subject_idx};

    % Get the data for the current subject
    subject_data = dataset.(subject);

    % Create a string for the subject that will be used in the table
    subject_str = strcat('Umich_2021_', subject);


    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process the Walking data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Get the treadmill data
    walk_data = subject_data.Walk;

    % List all the inclines
    walk_speed_name = {'s0x8','s1', 's1x2', 'a0x2','a0x5','d0x2','d0x5'};
    tread_inclines_name = {'in10', 'in5', 'i0', 'i10', 'i5'};
    tread_inclines = {-10, -5, 0, 10, 5};

    % Iterate through all the speeds
    for speed_idx = 1:length(walk_speed_name)

        % Get the current speed
        speed = walk_speed_name{speed_idx};

        % Get the data for the current speed
        speed_data = walk_data.(walk_speed_name{speed_idx});

        % Iterate through all the inclines
        for incline_idx = 1:length(tread_inclines)

            % Get the current incline
            incline_name = tread_inclines_name{incline_idx};
            incline_value = tread_inclines{incline_idx};

            % Get the data for the current incline
            try
                trial_struct = speed_data.(incline_name);
            catch
                continue
            end
            
            % Process the trial data
            trial_table = process_trial(trial_struct);

            % Add the incline to the table: TODO: Not standardized yet
            % trial_table.incline = repmat(incline, size(trial_table, 1), 1);
            
            % Add the subject to the table
            trial_table.subject_id = repmat({subject_str}, size(trial_table, 1), 1);

            % Add the task to the table
            long_task_substring =  strcat(num2str(abs(incline_value)), '_deg_',speed,'_m_s');
            if incline_value < 0
                trial_table.task_name = repmat({'decline_walking'}, size(trial_table, 1), 1);
                long_task_name = strcat('decline_walking_',long_task_substring);
                trial_table.task_info = repmat({long_task_name}, size(trial_table, 1), 1);
            elseif incline_value > 0
                trial_table.task_name = repmat({'incline_walking'}, size(trial_table, 1), 1);
                long_task_name = strcat('incline_walking_',long_task_substring);
                trial_table.task_info = repmat({long_task_name}, size(trial_table, 1), 1);
            else
                trial_table.task_name = repmat({'level_walking'}, size(trial_table, 1), 1);
                long_task_name = strcat('level_walking_',speed);
                trial_table.task_info = repmat({long_task_name}, size(trial_table, 1), 1);
            end

            % Add the data to the total table
            total_data = [total_data; trial_table];
        end
    end

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process the Run data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Get the run data
    run_data = subject_data.Run;

    % List all the speeds
    run_speeds_name = {'s1x8', 's2x0', 's2x2', 's2x4', 'a0x2',...
                       'a0x5', 'd0x2', 'd0x5'};
    run_speeds = {1.8, 2.0, 2.2, 2.4};

    incline = {'i0'};

    % Iterate through all the speeds
    for speed_idx = 1:length(run_speeds)

        % Get the current speed
        speed = run_speeds{speed_idx};
        
        try
            % Get the data for the current speed
            trial_struct = run_data.(run_speeds_name{speed_idx}).(incline{1});
        catch
            % If the trial does not exist, we move on with our lives
            continue
        end

        % Process the trial data
        trial_table = process_trial(trial_struct);

        % Add the speed to the table: TODO: Not standardized yet
        % trial_table.speed = repmat(speed, size(trial_table, 1), 1);

        % Add the subject to the table
        trial_table.subject_id = repmat({subject_str}, size(trial_table, 1), 1);

        % Add the task to the table
        trial_table.task_name = repmat({'running'}, size(trial_table, 1), 1);

        % Add the long task name
        long_task = strcat('running_',num2str(speed));
        trial_table.task_info = repmat({long_task}, size(trial_table, 1), 1);
        

        % Add the data to the total table
        total_data = [total_data; trial_table];

    end
end

% Save the data to a parquet file
% Write to converted_datasets folder in project root
output_path = fullfile('..', '..', '..', 'converted_datasets', 'umich_2021_phase.parquet');
parquetwrite(output_path, total_data);
fprintf('Saved phase-indexed data to: %s\n', output_path);



% This function will process the data for a single trial
function trial_table = process_trial(trial_struct)

    % Create a new table that will be returned
    trial_table = table;
    
    % Plane conventions
    sagittal_plane = 1;
    frontal_plane = 2;
    transverse_plane = 3;

    % Linear forces directions
    x = 1;
    y = 3;
    z = 2;

    % Create a phase axis. This is determined by the amount of steps times
    % 150, which is the points per step. The phase axis will be a linear 
    % interpolation from 0 to 1 for each step
    pps = 150; % points per step
    num_strides = size(trial_struct.jointAngles.HipAngles,3);
    
    % Create phase_r (right leg) based on heel strike of the right leg
    trial_table.phase_r = repmat((0:1/pps:1-1/pps)'*100, num_strides, 1);
    
    % Create phase_l (left leg) as a 50% offset from phase_r
    % We add 50 to phase_r and make sure it wraps around at 100
    phase_l = trial_table.phase_r + 50;
    phase_l(phase_l >= 100) = phase_l(phase_l >= 100) - 100;
    trial_table.phase_l = phase_l;

    % Set how much of a circ shift we need to do to get the left side
    shift = pps/2;

    % Joint angles - convert from degrees to radians and use new naming convention
    joint_angles = trial_struct.jointAngles;
    deg2rad_factor = pi/180;

    % Hip angles - reshape and convert to radians
    trial_table.hip_flexion_angle_r_rad = reshape(joint_angles.HipAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    trial_table.hip_adduction_angle_r_rad = reshape(joint_angles.HipAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    trial_table.hip_rotation_angle_r_rad = reshape(joint_angles.HipAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    % We do not have left side joint angles, so we will just shift the right
    % side angles by half a step
    trial_table.hip_flexion_angle_l_rad = circshift(trial_table.hip_flexion_angle_r_rad, shift);
    trial_table.hip_adduction_angle_l_rad = circshift(trial_table.hip_adduction_angle_r_rad, shift);
    trial_table.hip_rotation_angle_l_rad = circshift(trial_table.hip_rotation_angle_r_rad, shift);

    % Knee angles - reshape, negate sagittal, and convert to radians
    trial_table.knee_flexion_angle_r_rad = reshape(-joint_angles.KneeAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    trial_table.knee_adduction_angle_r_rad = reshape(joint_angles.KneeAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    trial_table.knee_rotation_angle_r_rad = reshape(joint_angles.KneeAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    trial_table.knee_flexion_angle_l_rad = circshift(trial_table.knee_flexion_angle_r_rad, shift);
    trial_table.knee_adduction_angle_l_rad = circshift(trial_table.knee_adduction_angle_r_rad, shift);
    trial_table.knee_rotation_angle_l_rad = circshift(trial_table.knee_rotation_angle_r_rad, shift);

    % Ankle angles - reshape and convert to radians
    trial_table.ankle_flexion_angle_r_rad = reshape(joint_angles.AnkleAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    trial_table.ankle_inversion_angle_r_rad = reshape(joint_angles.AnkleAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    trial_table.ankle_rotation_angle_r_rad = reshape(joint_angles.AnkleAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    trial_table.ankle_flexion_angle_l_rad = circshift(trial_table.ankle_flexion_angle_r_rad, shift);
    trial_table.ankle_inversion_angle_l_rad = circshift(trial_table.ankle_inversion_angle_r_rad, shift);
    trial_table.ankle_rotation_angle_l_rad = circshift(trial_table.ankle_rotation_angle_r_rad, shift);

    % Keep foot and pelvis angles in old format for now (not in standard spec)
    trial_table.foot_angle_s_r = reshape(-joint_angles.FootProgressAngles(:, sagittal_plane, :) - 90, [], 1);
    trial_table.foot_angle_f_r = reshape(joint_angles.FootProgressAngles(:, frontal_plane, :), [], 1);
    trial_table.foot_angle_t_r = reshape(joint_angles.FootProgressAngles(:, transverse_plane, :), [], 1);

    trial_table.foot_angle_s_l = circshift(trial_table.foot_angle_s_r, shift);
    trial_table.foot_angle_f_l = circshift(trial_table.foot_angle_f_r, shift);
    trial_table.foot_angle_t_l = circshift(trial_table.foot_angle_t_r, shift);

    trial_table.pelvis_angle_s_r = reshape(joint_angles.PelvisAngles(:, sagittal_plane, :), [], 1);
    trial_table.pelvis_angle_f_r = reshape(joint_angles.PelvisAngles(:, frontal_plane, :), [], 1);
    trial_table.pelvis_angle_t_r = reshape(joint_angles.PelvisAngles(:, transverse_plane, :), [], 1);

    trial_table.pelvis_angle_s_l = circshift(trial_table.pelvis_angle_s_r, shift);
    trial_table.pelvis_angle_f_l = circshift(trial_table.pelvis_angle_f_r, shift);
    trial_table.pelvis_angle_t_l = circshift(trial_table.pelvis_angle_t_r, shift);

    % Joint velocity - calculate from angles (already in radians) using new naming convention
    % Note: These are phase derivatives, not time derivatives in rad/s
    d_phase_dt = 1;
    
    % Hip velocities
    trial_table.hip_flexion_velocity_r_rad_s = gradient(trial_table.hip_flexion_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.hip_adduction_velocity_r_rad_s = gradient(trial_table.hip_adduction_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.hip_rotation_velocity_r_rad_s = gradient(trial_table.hip_rotation_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;

    trial_table.hip_flexion_velocity_l_rad_s = circshift(trial_table.hip_flexion_velocity_r_rad_s, shift);
    trial_table.hip_adduction_velocity_l_rad_s = circshift(trial_table.hip_adduction_velocity_r_rad_s, shift);
    trial_table.hip_rotation_velocity_l_rad_s = circshift(trial_table.hip_rotation_velocity_r_rad_s, shift);

    % Knee velocities
    trial_table.knee_flexion_velocity_r_rad_s = gradient(trial_table.knee_flexion_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.knee_adduction_velocity_r_rad_s = gradient(trial_table.knee_adduction_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.knee_rotation_velocity_r_rad_s = gradient(trial_table.knee_rotation_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;

    trial_table.knee_flexion_velocity_l_rad_s = circshift(trial_table.knee_flexion_velocity_r_rad_s, shift);
    trial_table.knee_adduction_velocity_l_rad_s = circshift(trial_table.knee_adduction_velocity_r_rad_s, shift);
    trial_table.knee_rotation_velocity_l_rad_s = circshift(trial_table.knee_rotation_velocity_r_rad_s, shift);

    % Ankle velocities    
    trial_table.ankle_flexion_velocity_r_rad_s = gradient(trial_table.ankle_flexion_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;    
    trial_table.ankle_inversion_velocity_r_rad_s = gradient(trial_table.ankle_inversion_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.ankle_rotation_velocity_r_rad_s = gradient(trial_table.ankle_rotation_angle_r_rad)./gradient(trial_table.phase_r) * d_phase_dt;

    trial_table.ankle_flexion_velocity_l_rad_s = circshift(trial_table.ankle_flexion_velocity_r_rad_s, shift);
    trial_table.ankle_inversion_velocity_l_rad_s = circshift(trial_table.ankle_inversion_velocity_r_rad_s, shift);
    trial_table.ankle_rotation_velocity_l_rad_s = circshift(trial_table.ankle_rotation_velocity_r_rad_s, shift);

    % Keep foot velocities in old format for now (not in standard spec)
    trial_table.foot_vel_s_r = gradient(trial_table.foot_angle_s_r)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.foot_vel_f_r = gradient(trial_table.foot_angle_f_r)./gradient(trial_table.phase_r) * d_phase_dt;
    trial_table.foot_vel_t_r = gradient(trial_table.foot_angle_t_r)./gradient(trial_table.phase_r) * d_phase_dt;

    trial_table.foot_vel_s_l = circshift(trial_table.foot_vel_s_r, shift);
    trial_table.foot_vel_f_l = circshift(trial_table.foot_vel_f_r, shift);
    trial_table.foot_vel_t_l = circshift(trial_table.foot_vel_t_r, shift);

    % Joint moments - use new naming convention (moments stay in Nm)
    joint_moments = trial_struct.jointMoments;

    % Hip moments - reshape
    trial_table.hip_flexion_moment_r_Nm = reshape(joint_moments.HipMoment(:, sagittal_plane, :), [], 1);
    trial_table.hip_adduction_moment_r_Nm = reshape(joint_moments.HipMoment(:, frontal_plane, :), [], 1);
    trial_table.hip_rotation_moment_r_Nm = reshape(joint_moments.HipMoment(:, transverse_plane, :), [], 1);

    trial_table.hip_flexion_moment_l_Nm = circshift(trial_table.hip_flexion_moment_r_Nm, shift);
    trial_table.hip_adduction_moment_l_Nm = circshift(trial_table.hip_adduction_moment_r_Nm, shift);
    trial_table.hip_rotation_moment_l_Nm = circshift(trial_table.hip_rotation_moment_r_Nm, shift);

    % Knee moments - reshape, negate sagittal
    trial_table.knee_flexion_moment_r_Nm = reshape(-joint_moments.KneeMoment(:, sagittal_plane, :), [], 1);
    trial_table.knee_adduction_moment_r_Nm = reshape(joint_moments.KneeMoment(:, frontal_plane, :), [], 1);
    trial_table.knee_rotation_moment_r_Nm = reshape(joint_moments.KneeMoment(:, transverse_plane, :), [], 1);

    trial_table.knee_flexion_moment_l_Nm = circshift(trial_table.knee_flexion_moment_r_Nm, shift);
    trial_table.knee_adduction_moment_l_Nm = circshift(trial_table.knee_adduction_moment_r_Nm, shift);
    trial_table.knee_rotation_moment_l_Nm = circshift(trial_table.knee_rotation_moment_r_Nm, shift);

    % Ankle moments - reshape
    trial_table.ankle_flexion_moment_r_Nm = reshape(joint_moments.AnkleMoment(:, sagittal_plane, :), [], 1);
    trial_table.ankle_inversion_moment_r_Nm = reshape(joint_moments.AnkleMoment(:, frontal_plane, :), [], 1);
    trial_table.ankle_rotation_moment_r_Nm = reshape(joint_moments.AnkleMoment(:, transverse_plane, :), [], 1);

    trial_table.ankle_flexion_moment_l_Nm = circshift(trial_table.ankle_flexion_moment_r_Nm, shift);
    trial_table.ankle_inversion_moment_l_Nm = circshift(trial_table.ankle_inversion_moment_r_Nm, shift);
    trial_table.ankle_rotation_moment_l_Nm = circshift(trial_table.ankle_rotation_moment_r_Nm, shift);

    % Ground reaction forces
    force_plates = trial_struct.forceplates;

    trial_table.grf_z_r = -reshape(force_plates.Force(:, z, :), [], 1);
    trial_table.grf_y_r = -reshape(force_plates.Force(:, y, :), [], 1);
    trial_table.grf_x_r = -reshape(force_plates.Force(:, x, :), [], 1);

    trial_table.grf_z_l = circshift(trial_table.grf_z_r, shift);
    trial_table.grf_y_l = circshift(trial_table.grf_y_r, shift);
    trial_table.grf_x_l = circshift(trial_table.grf_x_r, shift);

    % Center of pressure, based on evaluating we have to switch 
    % the y and z axis. It's not a typo
    trial_table.cop_z_r = -reshape(force_plates.CoP(:, z, :), [], 1);
    trial_table.cop_y_r = reshape(force_plates.CoP(:, y, :), [], 1);
    trial_table.cop_x_r = -reshape(force_plates.CoP(:, x, :), [], 1);

    trial_table.cop_z_l = circshift(trial_table.cop_z_r, shift);
    trial_table.cop_y_l = circshift(trial_table.cop_y_r, shift);
    trial_table.cop_x_l = circshift(trial_table.cop_x_r, shift);


    % TODO: More data types will be added in here in the future

end