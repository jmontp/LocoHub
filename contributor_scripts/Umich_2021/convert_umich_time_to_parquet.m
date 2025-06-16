clearvars -except Streaming


%Load dataset
if exist('Streaming', 'var')==0
    load('Streaming.mat');
end

dataset = Streaming;


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
    % Process the Treadmill data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Get the treadmill data
    treadmill_data = subject_data.Tread;

    % List all the inclines
    tread_inclines_name = {'d10', 'd5', 'i0', 'i10', 'i5'};
    tread_inclines = {-10, -5, 0, 10, 5};

    % Iterate through all the inclines
    for incline_idx = 1:length(tread_inclines)

        % Get the current incline
        incline = tread_inclines{incline_idx};

        % Get the data for the current incline
        trial_struct = treadmill_data.(tread_inclines_name{incline_idx});
        
        % Process the trial data
        trial_table = process_trial(trial_struct);

        % Add the incline to the table: TODO: Not standardized yet
        % trial_table.incline = repmat(incline, size(trial_table, 1), 1);
        
        % Add the subject to the table
        trial_table.subject_id = repmat({subject_str}, size(trial_table, 1), 1);

        % Add the task to the table
        incline_value = tread_inclines{incline_idx};
        speed = tread_inclines_name{incline_idx};
        long_task_substring =  strcat(num2str(abs(incline_value)), '_deg_',speed,'_m_s');

        if incline < 0
            trial_table.task_name = repmat({'decline_walking'}, size(trial_table, 1), 1);
            trial_table.task_info = repmat({long_task_substring}, size(trial_table, 1), 1);
        elseif incline > 0
            trial_table.task_name = repmat({'incline_walking'}, size(trial_table, 1), 1);
            trial_table.task_info = repmat({long_task_substring}, size(trial_table, 1), 1);
        else
            trial_table.task_name = repmat({'level_walking'}, size(trial_table, 1), 1);
            trial_table.task_info = repmat({long_task_substring}, size(trial_table, 1), 1);
        end

        % Add the data to the total table
        total_data = [total_data; trial_table];
    end

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process the Walk to run data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Get the walk to run data
    try
        walk_to_run_data = subject_data.Wtr;
    
        % Process the walk to run data
        trial_table = process_trial(walk_to_run_data);
    
        % Add the subject to the table
        trial_table.subject_id = repmat({subject_str}, size(trial_table, 1), 1);
    
        % Add the task to the table
        trial_table.task_name = repmat({'transitions'}, size(trial_table, 1), 1);
        trial_table.task_info = repmat({'walk_to_run'}, size(trial_table, 1), 1);
    
        % Add the data to the total table
        total_data = [total_data; trial_table];
    catch
        % Don't do anything if we can't load the wtr data
    end

    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process the Run data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    % Get the run data
    run_data = subject_data.Run;

    % List all the speeds
    run_speeds_name = {'s1x8', 's2x0', 's2x2', 's2x4'};
    run_speeds = {1.8, 2.0, 2.2, 2.4};

    % Iterate through all the speeds
    for speed_idx = 1:length(run_speeds)

        % Get the current speed
        speed = run_speeds{speed_idx};
        
        try
            % Get the data for the current speed
            trial_struct = run_data.(run_speeds_name{speed_idx});
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
        trial_table.task_info = repmat({strcat(num2str(speed), '_m_s')}, size(trial_table, 1), 1);

        % Add the data to the total table
        total_data = [total_data; trial_table];

    end
end

% Save the data to a parquet file
% Write to converted_datasets folder in project root
output_path = fullfile('..', '..', '..', 'converted_datasets', 'umich_2021_time.parquet');
parquetwrite(output_path, total_data);
fprintf('Saved time-indexed data to: %s\n', output_path);



% This function will process the data for a single trial
function trial_table = process_trial(trial_struct)

    % Create a new table that will be returned
    trial_table = table;

    sagittal_plane = 1;
    frontal_plane = 2;
    transverse_plane = 3;

    % Linear forces directions
    x = 1;
    y = 3;
    z = 2;

    % Create a time axis for the trial based on the length and the fact that
    % all data (minus force plates, which is 1000 Hz) is sampled at 100 Hz
    Hz = 100;
    num_points = (length(trial_struct.jointAngles.RAnkleAngles)-1)/Hz;
    trial_table.time_s = (0:1/Hz:num_points)';


    % Joint angles - convert from degrees to radians and use new naming convention
    joint_angles = trial_struct.jointAngles;
    deg2rad_factor = pi/180;

    % Hip angles
    trial_table.hip_flexion_angle_r_rad = joint_angles.RHipAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.hip_adduction_angle_r_rad = joint_angles.RHipAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.hip_rotation_angle_r_rad = joint_angles.RHipAngles(:, transverse_plane) * deg2rad_factor;

    trial_table.hip_flexion_angle_l_rad = joint_angles.LHipAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.hip_adduction_angle_l_rad = joint_angles.LHipAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.hip_rotation_angle_l_rad = joint_angles.LHipAngles(:, transverse_plane) * deg2rad_factor;

    % Knee angles (note: negative sign for sagittal to match convention)
    trial_table.knee_flexion_angle_r_rad = -joint_angles.RKneeAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.knee_adduction_angle_r_rad = joint_angles.RKneeAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.knee_rotation_angle_r_rad = joint_angles.RKneeAngles(:, transverse_plane) * deg2rad_factor;

    trial_table.knee_flexion_angle_l_rad = -joint_angles.LKneeAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.knee_adduction_angle_l_rad = joint_angles.LKneeAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.knee_rotation_angle_l_rad = joint_angles.LKneeAngles(:, transverse_plane) * deg2rad_factor;

    % Ankle angles
    trial_table.ankle_flexion_angle_r_rad = joint_angles.RAnkleAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.ankle_inversion_angle_r_rad = joint_angles.RAnkleAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.ankle_rotation_angle_r_rad = joint_angles.RAnkleAngles(:, transverse_plane) * deg2rad_factor;

    trial_table.ankle_flexion_angle_l_rad = joint_angles.LAnkleAngles(:, sagittal_plane) * deg2rad_factor;
    trial_table.ankle_inversion_angle_l_rad = joint_angles.LAnkleAngles(:, frontal_plane) * deg2rad_factor;
    trial_table.ankle_rotation_angle_l_rad = joint_angles.LAnkleAngles(:, transverse_plane) * deg2rad_factor;

    % Keep foot and pelvis angles in old format for now (not in standard spec)
    trial_table.foot_angle_s_r = -joint_angles.RFootProgressAngles(:, sagittal_plane) - 90;
    trial_table.foot_angle_f_r = joint_angles.RFootProgressAngles(:, frontal_plane);
    trial_table.foot_angle_t_r = joint_angles.RFootProgressAngles(:, transverse_plane);

    trial_table.foot_angle_s_l = -joint_angles.LFootProgressAngles(:, sagittal_plane) - 90;
    trial_table.foot_angle_f_l = joint_angles.LFootProgressAngles(:, frontal_plane);
    trial_table.foot_angle_t_l = joint_angles.LFootProgressAngles(:, transverse_plane);

    trial_table.pelvis_angle_s_r = joint_angles.RPelvisAngles(:, sagittal_plane);
    trial_table.pelvis_angle_f_r = joint_angles.RPelvisAngles(:, frontal_plane);
    trial_table.pelvis_angle_t_r = joint_angles.RPelvisAngles(:, transverse_plane);

    trial_table.pelvis_angle_s_l = joint_angles.LPelvisAngles(:, sagittal_plane);
    trial_table.pelvis_angle_f_l = joint_angles.LPelvisAngles(:, frontal_plane);
    trial_table.pelvis_angle_t_l = joint_angles.LPelvisAngles(:, transverse_plane);
    
    % Joint velocity - calculate from angles (already in radians) using new naming convention
    % Hip velocities
    trial_table.hip_flexion_velocity_r_rad_s = gradient(trial_table.hip_flexion_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.hip_adduction_velocity_r_rad_s = gradient(trial_table.hip_adduction_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.hip_rotation_velocity_r_rad_s = gradient(trial_table.hip_rotation_angle_r_rad)./gradient(trial_table.time_s);

    trial_table.hip_flexion_velocity_l_rad_s = gradient(trial_table.hip_flexion_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.hip_adduction_velocity_l_rad_s = gradient(trial_table.hip_adduction_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.hip_rotation_velocity_l_rad_s = gradient(trial_table.hip_rotation_angle_l_rad)./gradient(trial_table.time_s);

    % Knee velocities
    trial_table.knee_flexion_velocity_r_rad_s = gradient(trial_table.knee_flexion_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.knee_adduction_velocity_r_rad_s = gradient(trial_table.knee_adduction_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.knee_rotation_velocity_r_rad_s = gradient(trial_table.knee_rotation_angle_r_rad)./gradient(trial_table.time_s);

    trial_table.knee_flexion_velocity_l_rad_s = gradient(trial_table.knee_flexion_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.knee_adduction_velocity_l_rad_s = gradient(trial_table.knee_adduction_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.knee_rotation_velocity_l_rad_s = gradient(trial_table.knee_rotation_angle_l_rad)./gradient(trial_table.time_s);

    % Ankle velocities
    trial_table.ankle_flexion_velocity_r_rad_s = gradient(trial_table.ankle_flexion_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.ankle_inversion_velocity_r_rad_s = gradient(trial_table.ankle_inversion_angle_r_rad)./gradient(trial_table.time_s);
    trial_table.ankle_rotation_velocity_r_rad_s = gradient(trial_table.ankle_rotation_angle_r_rad)./gradient(trial_table.time_s);

    trial_table.ankle_flexion_velocity_l_rad_s = gradient(trial_table.ankle_flexion_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.ankle_inversion_velocity_l_rad_s = gradient(trial_table.ankle_inversion_angle_l_rad)./gradient(trial_table.time_s);
    trial_table.ankle_rotation_velocity_l_rad_s = gradient(trial_table.ankle_rotation_angle_l_rad)./gradient(trial_table.time_s);

    % Keep foot and pelvis velocities in old format for now (not in standard spec)
    trial_table.foot_vel_s_r = gradient(trial_table.foot_angle_s_r)./gradient(trial_table.time_s);
    trial_table.foot_vel_f_r = gradient(trial_table.foot_angle_f_r)./gradient(trial_table.time_s);
    trial_table.foot_vel_t_r = gradient(trial_table.foot_angle_t_r)./gradient(trial_table.time_s);

    trial_table.foot_vel_s_l = gradient(trial_table.foot_angle_s_l)./gradient(trial_table.time_s);
    trial_table.foot_vel_f_l = gradient(trial_table.foot_angle_f_l)./gradient(trial_table.time_s);
    trial_table.foot_vel_t_l = gradient(trial_table.foot_angle_t_l)./gradient(trial_table.time_s);

    trial_table.pelvis_vel_s_r = gradient(trial_table.pelvis_angle_s_r)./gradient(trial_table.time_s);
    trial_table.pelvis_vel_f_r = gradient(trial_table.pelvis_angle_f_r)./gradient(trial_table.time_s);
    trial_table.pelvis_vel_t_r = gradient(trial_table.pelvis_angle_t_r)./gradient(trial_table.time_s);

    trial_table.pelvis_vel_s_l = gradient(trial_table.pelvis_angle_s_l)./gradient(trial_table.time_s);
    trial_table.pelvis_vel_f_l = gradient(trial_table.pelvis_angle_f_l)./gradient(trial_table.time_s);
    trial_table.pelvis_vel_t_l = gradient(trial_table.pelvis_angle_t_l)./gradient(trial_table.time_s);


    % Joint moments - use new naming convention (moments stay in Nm)
    joint_moments = trial_struct.jointMoments;

    % Hip moments
    trial_table.hip_flexion_moment_r_Nm = joint_moments.RHipMoment(:, sagittal_plane);
    trial_table.hip_adduction_moment_r_Nm = joint_moments.RHipMoment(:, frontal_plane);
    trial_table.hip_rotation_moment_r_Nm = joint_moments.RHipMoment(:, transverse_plane);

    trial_table.hip_flexion_moment_l_Nm = joint_moments.LHipMoment(:, sagittal_plane);
    trial_table.hip_adduction_moment_l_Nm = joint_moments.LHipMoment(:, frontal_plane);
    trial_table.hip_rotation_moment_l_Nm = joint_moments.LHipMoment(:, transverse_plane);

    % Knee moments (note: negative sign for sagittal to match convention)
    trial_table.knee_flexion_moment_r_Nm = -joint_moments.RKneeMoment(:, sagittal_plane);
    trial_table.knee_adduction_moment_r_Nm = joint_moments.RKneeMoment(:, frontal_plane);
    trial_table.knee_rotation_moment_r_Nm = joint_moments.RKneeMoment(:, transverse_plane);

    trial_table.knee_flexion_moment_l_Nm = -joint_moments.LKneeMoment(:, sagittal_plane);
    trial_table.knee_adduction_moment_l_Nm = joint_moments.LKneeMoment(:, frontal_plane);
    trial_table.knee_rotation_moment_l_Nm = joint_moments.LKneeMoment(:, transverse_plane);

    % Ankle moments
    trial_table.ankle_flexion_moment_r_Nm = joint_moments.RAnkleMoment(:, sagittal_plane);
    trial_table.ankle_inversion_moment_r_Nm = joint_moments.RAnkleMoment(:, frontal_plane);
    trial_table.ankle_rotation_moment_r_Nm = joint_moments.RAnkleMoment(:, transverse_plane);

    trial_table.ankle_flexion_moment_l_Nm = joint_moments.LAnkleMoment(:, sagittal_plane);
    trial_table.ankle_inversion_moment_l_Nm = joint_moments.LAnkleMoment(:, frontal_plane);
    trial_table.ankle_rotation_moment_l_Nm = joint_moments.LAnkleMoment(:, transverse_plane);

    % Ground reaction forces
    force_plates = trial_struct.forceplates;

    % Skip every 10th data point to match the 100 Hz sampling rate
    trial_table.grf_z_r = -force_plates.RForce(1:10:end, z);
    trial_table.grf_y_r = -force_plates.RForce(1:10:end, y);
    trial_table.grf_x_r = force_plates.RForce(1:10:end, x);

    trial_table.grf_z_l = -force_plates.LForce(1:10:end, z);
    trial_table.grf_y_l = -force_plates.LForce(1:10:end, y);
    trial_table.grf_x_l = force_plates.LForce(1:10:end, x);
    
    % Center of pressure
    trial_table.cop_z_r = -force_plates.RCoP(1:10:end, z);
    trial_table.cop_y_r = force_plates.RCoP(1:10:end, y);
    trial_table.cop_x_r = -force_plates.RCoP(1:10:end, x);

    trial_table.cop_z_l = -force_plates.LCoP(1:10:end, z);
    trial_table.cop_y_l = force_plates.LCoP(1:10:end, y);
    trial_table.cop_x_l = -force_plates.LCoP(1:10:end, x);

    % TODO: More data types will be added in here in the future

end