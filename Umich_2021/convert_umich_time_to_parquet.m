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
        trial_table.subject = repmat({subject_str}, size(trial_table, 1), 1);

        % Add the task to the table
        incline_value = tread_inclines{incline_idx};
        speed = tread_inclines_name{incline_idx};
        long_task_substring =  strcat(num2str(abs(incline_value)), '_deg_',speed,'_m_s');

        if incline < 0
            trial_table.task = repmat({'decline_walking'}, size(trial_table, 1), 1);
            trial_table.task_info = repmat({long_task_substring}, size(trial_table, 1), 1);
        elseif incline > 0
            trial_table.task = repmat({'incline_walking'}, size(trial_table, 1), 1);
            trial_table.task_info = repmat({long_task_substring}, size(trial_table, 1), 1);
        else
            trial_table.task = repmat({'level_walking'}, size(trial_table, 1), 1);
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
        trial_table.subject = repmat({subject_str}, size(trial_table, 1), 1);
    
        % Add the task to the table
        trial_table.task = repmat({'transitions'}, size(trial_table, 1), 1);
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
        trial_table.subject = repmat({subject_str}, size(trial_table, 1), 1);

        % Add the task to the table
        trial_table.task = repmat({'running'}, size(trial_table, 1), 1);
        trial_table.task_info = repmat({strcat(num2str(speed), '_m_s')}, size(trial_table, 1), 1);

        % Add the data to the total table
        total_data = [total_data; trial_table];

    end
end

% Save the data to a parquet file
parquetwrite('umich_2021_time.parquet', total_data);



% This function will process the data for a single trial
function trial_table = process_trial(trial_struct)

    % Create a new table that will be returned
    trial_table = table;

    sagittal_plane = 1;
    frontal_plane = 2;
    transverse_plane = 3;

    % Create a time axis for the trial based on the length and the fact that
    % all data (minus force plates, which is 1000 Hz) is sampled at 100 Hz
    Hz = 100;
    num_points = (length(trial_struct.jointAngles.RAnkleAngles)-1)/Hz;
    trial_table.time = (0:1/Hz:num_points)';


    % Joint angles
    joint_angles = trial_struct.jointAngles;

    trial_table.hip_angle_s_r = joint_angles.RHipAngles(:, sagittal_plane);
    trial_table.hip_angle_f_r = joint_angles.RHipAngles(:, frontal_plane);
    trial_table.hip_angle_t_r = joint_angles.RHipAngles(:, transverse_plane);

    trial_table.hip_angle_s_l = joint_angles.LHipAngles(:, sagittal_plane);
    trial_table.hip_angle_f_l = joint_angles.LHipAngles(:, frontal_plane);
    trial_table.hip_angle_t_l = joint_angles.LHipAngles(:, transverse_plane);

    trial_table.knee_angle_s_r = -joint_angles.RKneeAngles(:, sagittal_plane);
    trial_table.knee_angle_f_r = joint_angles.RKneeAngles(:, frontal_plane);
    trial_table.knee_angle_t_r = joint_angles.RKneeAngles(:, transverse_plane);

    trial_table.knee_angle_s_l = -joint_angles.LKneeAngles(:, sagittal_plane);
    trial_table.knee_angle_f_l = joint_angles.LKneeAngles(:, frontal_plane);
    trial_table.knee_angle_t_l = joint_angles.LKneeAngles(:, transverse_plane);

    trial_table.ankle_angle_s_r = joint_angles.RAnkleAngles(:, sagittal_plane);
    trial_table.ankle_angle_f_r = joint_angles.RAnkleAngles(:, frontal_plane);
    trial_table.ankle_angle_t_r = joint_angles.RAnkleAngles(:, transverse_plane);

    trial_table.ankle_angle_s_l = joint_angles.LAnkleAngles(:, sagittal_plane);
    trial_table.ankle_angle_f_l = joint_angles.LAnkleAngles(:, frontal_plane);
    trial_table.ankle_angle_t_l = joint_angles.LAnkleAngles(:, transverse_plane);

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
    
    % Joint velocity, there are no joint velocities in the dataset, so we
    % will calculate them using the joint angles and time axis
    trial_table.hip_vel_s_r = gradient(trial_table.hip_angle_s_r)./gradient(trial_table.time);
    trial_table.hip_vel_f_r = gradient(trial_table.hip_angle_f_r)./gradient(trial_table.time);
    trial_table.hip_vel_t_r = gradient(trial_table.hip_angle_t_r)./gradient(trial_table.time);

    trial_table.hip_vel_s_l = gradient(trial_table.hip_angle_s_l)./gradient(trial_table.time);
    trial_table.hip_vel_f_l = gradient(trial_table.hip_angle_f_l)./gradient(trial_table.time);
    trial_table.hip_vel_t_l = gradient(trial_table.hip_angle_t_l)./gradient(trial_table.time);

    trial_table.knee_vel_s_r = gradient(trial_table.knee_angle_s_r)./gradient(trial_table.time);
    trial_table.knee_vel_f_r = gradient(trial_table.knee_angle_f_r)./gradient(trial_table.time);
    trial_table.knee_vel_t_r = gradient(trial_table.knee_angle_t_r)./gradient(trial_table.time);

    trial_table.knee_vel_s_l = gradient(trial_table.knee_angle_s_l)./gradient(trial_table.time);
    trial_table.knee_vel_f_l = gradient(trial_table.knee_angle_f_l)./gradient(trial_table.time);
    trial_table.knee_vel_t_l = gradient(trial_table.knee_angle_t_l)./gradient(trial_table.time);

    trial_table.ankle_vel_s_r = gradient(trial_table.ankle_angle_s_r)./gradient(trial_table.time);
    trial_table.ankle_vel_f_r = gradient(trial_table.ankle_angle_f_r)./gradient(trial_table.time);
    trial_table.ankle_vel_t_r = gradient(trial_table.ankle_angle_t_r)./gradient(trial_table.time);

    trial_table.ankle_vel_s_l = gradient(trial_table.ankle_angle_s_l)./gradient(trial_table.time);
    trial_table.ankle_vel_f_l = gradient(trial_table.ankle_angle_f_l)./gradient(trial_table.time);
    trial_table.ankle_vel_t_l = gradient(trial_table.ankle_angle_t_l)./gradient(trial_table.time);

    trial_table.foot_vel_s_r = gradient(trial_table.foot_angle_s_r)./gradient(trial_table.time);
    trial_table.foot_vel_f_r = gradient(trial_table.foot_angle_f_r)./gradient(trial_table.time);
    trial_table.foot_vel_t_r = gradient(trial_table.foot_angle_t_r)./gradient(trial_table.time);

    trial_table.foot_vel_s_l = gradient(trial_table.foot_angle_s_l)./gradient(trial_table.time);
    trial_table.foot_vel_f_l = gradient(trial_table.foot_angle_f_l)./gradient(trial_table.time);
    trial_table.foot_vel_t_l = gradient(trial_table.foot_angle_t_l)./gradient(trial_table.time);

    trial_table.pelvis_vel_s_r = gradient(trial_table.pelvis_angle_s_r)./gradient(trial_table.time);
    trial_table.pelvis_vel_f_r = gradient(trial_table.pelvis_angle_f_r)./gradient(trial_table.time);
    trial_table.pelvis_vel_t_r = gradient(trial_table.pelvis_angle_t_r)./gradient(trial_table.time);

    trial_table.pelvis_vel_s_l = gradient(trial_table.pelvis_angle_s_l)./gradient(trial_table.time);
    trial_table.pelvis_vel_f_l = gradient(trial_table.pelvis_angle_f_l)./gradient(trial_table.time);
    trial_table.pelvis_vel_t_l = gradient(trial_table.pelvis_angle_t_l)./gradient(trial_table.time);


    % Joint moments
    joint_moments = trial_struct.jointMoments;

    trial_table.hip_torque_s_r = joint_moments.RHipMoment(:, sagittal_plane);
    trial_table.hip_torque_f_r = joint_moments.RHipMoment(:, frontal_plane);
    trial_table.hip_torque_t_r = joint_moments.RHipMoment(:, transverse_plane);

    trial_table.hip_torque_s_l = joint_moments.LHipMoment(:, sagittal_plane);
    trial_table.hip_torque_f_l = joint_moments.LHipMoment(:, frontal_plane);
    trial_table.hip_torque_t_l = joint_moments.LHipMoment(:, transverse_plane);

    trial_table.knee_torque_s_r = -joint_moments.RKneeMoment(:, sagittal_plane);
    trial_table.knee_torque_f_r = joint_moments.RKneeMoment(:, frontal_plane);
    trial_table.knee_torque_t_r = joint_moments.RKneeMoment(:, transverse_plane);

    trial_table.knee_torque_s_l = -joint_moments.LKneeMoment(:, sagittal_plane);
    trial_table.knee_torque_f_l = joint_moments.LKneeMoment(:, frontal_plane);
    trial_table.knee_torque_t_l = joint_moments.LKneeMoment(:, transverse_plane);

    trial_table.ankle_torque_s_r = joint_moments.RAnkleMoment(:, sagittal_plane);
    trial_table.ankle_torque_f_r = joint_moments.RAnkleMoment(:, frontal_plane);
    trial_table.ankle_torque_t_r = joint_moments.RAnkleMoment(:, transverse_plane);

    trial_table.ankle_torque_s_l = joint_moments.LAnkleMoment(:, sagittal_plane);
    trial_table.ankle_torque_f_l = joint_moments.LAnkleMoment(:, frontal_plane);
    trial_table.ankle_torque_t_l = joint_moments.LAnkleMoment(:, transverse_plane);

    % TODO: More data types will be added in here in the future

end