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
    % Following naming convention: DATASET_POPULATION+NUMBER
    % UM21 = UMich 2021 dataset, AB = Able-bodied
    subject_num = subject(end-1:end);  % Extract last 2 chars (e.g., '01' from 'AB01')
    subject_str = strcat('UM21_AB', subject_num);


    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Process the Walking data
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%f%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

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
            
            % Process the trial data (pass task info for data fixes)
            task_type = '';
            if incline_value < 0
                task_type = 'decline_walking';
            elseif incline_value > 0
                task_type = 'incline_walking';
            else
                task_type = 'level_walking';
            end
            trial_table = process_trial(trial_struct, task_type, subject_str, incline_value);

            % Add the subject to the table (using standard naming)
            trial_table.subject = repmat({subject_str}, size(trial_table, 1), 1);

            % Add the task to the table following standard spec
            % Map speed codes to actual speeds in m/s
            speed_map = containers.Map(...
                {'s0x8', 's1', 's1x2', 'a0x2', 'a0x5', 'd0x2', 'd0x5'}, ...
                {0.8, 1.0, 1.2, 0.2, 0.5, 0.2, 0.5});
            speed_value = speed_map(speed);
            
            if incline_value < 0
                trial_table.task = repmat({'decline_walking'}, size(trial_table, 1), 1);
                trial_table.task_id = repmat({sprintf('decline_%ddeg', abs(incline_value))}, size(trial_table, 1), 1);
                trial_table.task_info = repmat({sprintf('incline_deg:%d,speed_m_s:%.1f,treadmill:true', incline_value, speed_value)}, size(trial_table, 1), 1);
            elseif incline_value > 0
                trial_table.task = repmat({'incline_walking'}, size(trial_table, 1), 1);
                trial_table.task_id = repmat({sprintf('incline_%ddeg', incline_value)}, size(trial_table, 1), 1);
                trial_table.task_info = repmat({sprintf('incline_deg:%d,speed_m_s:%.1f,treadmill:true', incline_value, speed_value)}, size(trial_table, 1), 1);
            else
                trial_table.task = repmat({'level_walking'}, size(trial_table, 1), 1);
                trial_table.task_id = repmat({'level'}, size(trial_table, 1), 1);
                trial_table.task_info = repmat({sprintf('incline_deg:0,speed_m_s:%.1f,treadmill:true', speed_value)}, size(trial_table, 1), 1);
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

    % Iterate through all running conditions
    run_speed_name = {'s2','s2x5','s3','s3x5','s4'};

    for speed_idx = 1:length(run_speed_name)

        % Get the current speed
        speed = run_speed_name{speed_idx};

        % Get the data for the current speed, if it exists
        try
            trial_struct = run_data.(speed);
        catch
            continue
        end

        % Process the trial data (pass task info for data fixes)
        trial_table = process_trial(trial_struct, 'run', subject_str, 0);  % 0 incline for running

        % Add the subject to the table (using standard naming)
        trial_table.subject = repmat({subject_str}, size(trial_table, 1), 1);

        % Add the task to the table following standard spec
        % Map run speed codes to actual speeds in m/s
        run_speed_map = containers.Map(...
            {'s2', 's2x5', 's3', 's3x5', 's4'}, ...
            {2.0, 2.5, 3.0, 3.5, 4.0});
        run_speed_value = run_speed_map(run_speed_name{speed_idx});
        
        trial_table.task = repmat({'run'}, size(trial_table, 1), 1);
        trial_table.task_id = repmat({'run'}, size(trial_table, 1), 1);
        trial_table.task_info = repmat({sprintf('speed_m_s:%.1f,treadmill:true', run_speed_value)}, size(trial_table, 1), 1);

        % Add the data to the total table
        total_data = [total_data; trial_table];
    end

end


 








% Save the phase-indexed data
output_path = fullfile('..', '..', '..', 'converted_datasets', 'umich_2021_phase.parquet');
parquetwrite(output_path, total_data);

fprintf('Saved phase-indexed data to: %s\n', output_path);



% This function will process the data for a single trial
function trial_table = process_trial(trial_struct, task_type, subject_str, incline_value)

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
    % interpolation from 0 to 100 for each step (following standard spec)
    pps = 150; % points per step
    num_strides = size(trial_struct.jointAngles.HipAngles,3);
    
    % Create phase_ipsi based on standard specification (0-100% aligned to ipsilateral heel strike)
    trial_table.phase_ipsi = repmat((0:1/pps:1-1/pps)'*100, num_strides, 1);
    
    % Add step numbers for proper step identification
    step_numbers = [];
    for step = 1:num_strides
        step_numbers = [step_numbers; repmat(step, pps, 1)];
    end
    trial_table.step = step_numbers;

    % Set how much of a circ shift we need to do to get the contralateral leg
    shift = pps/2;

    % Joint angles - convert from degrees to radians and use left/right naming convention
    joint_angles = trial_struct.jointAngles;
    deg2rad_factor = pi/180;

    % Hip angles - reshape and convert to radians (use standard ipsi/contra naming)
    hip_flexion_ipsi = reshape(joint_angles.HipAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    hip_adduction_ipsi = reshape(joint_angles.HipAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    hip_rotation_ipsi = reshape(joint_angles.HipAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.hip_flexion_angle_ipsi_rad = hip_flexion_ipsi;
    trial_table.hip_adduction_angle_ipsi_rad = hip_adduction_ipsi;
    trial_table.hip_rotation_angle_ipsi_rad = hip_rotation_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.hip_flexion_angle_contra_rad = circshift(hip_flexion_ipsi, shift);
    trial_table.hip_adduction_angle_contra_rad = circshift(hip_adduction_ipsi, shift);
    trial_table.hip_rotation_angle_contra_rad = circshift(hip_rotation_ipsi, shift);

    % Knee angles - reshape, negate sagittal (OpenSim convention), and convert to radians
    knee_flexion_ipsi = reshape(joint_angles.KneeAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    knee_adduction_ipsi = reshape(joint_angles.KneeAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    knee_rotation_ipsi = reshape(joint_angles.KneeAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.knee_flexion_angle_ipsi_rad = knee_flexion_ipsi;
    trial_table.knee_adduction_angle_ipsi_rad = knee_adduction_ipsi;
    trial_table.knee_rotation_angle_ipsi_rad = knee_rotation_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.knee_flexion_angle_contra_rad = circshift(knee_flexion_ipsi, shift);
    trial_table.knee_adduction_angle_contra_rad = circshift(knee_adduction_ipsi, shift);
    trial_table.knee_rotation_angle_contra_rad = circshift(knee_rotation_ipsi, shift);

    % Ankle angles - reshape and convert to radians (use standard ipsi/contra naming)
    ankle_dorsiflexion_ipsi = reshape(-joint_angles.AnkleAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    ankle_adduction_ipsi = reshape(joint_angles.AnkleAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    ankle_rotation_ipsi = reshape(joint_angles.AnkleAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.ankle_dorsiflexion_angle_ipsi_rad = ankle_dorsiflexion_ipsi;
    trial_table.ankle_adduction_angle_ipsi_rad = ankle_adduction_ipsi;
    trial_table.ankle_rotation_angle_ipsi_rad = ankle_rotation_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.ankle_dorsiflexion_angle_contra_rad = circshift(ankle_dorsiflexion_ipsi, shift);
    trial_table.ankle_adduction_angle_contra_rad = circshift(ankle_adduction_ipsi, shift);
    trial_table.ankle_rotation_angle_contra_rad = circshift(ankle_rotation_ipsi, shift);

    % Joint moments - convert from Nm to Nm (already correct) and use standard ipsi/contra naming
    joint_moments = trial_struct.jointMoments;

    % Hip moments
    hip_flexion_moment_ipsi = reshape(joint_moments.HipMoment(:, sagittal_plane, :), [], 1);
    hip_adduction_moment_ipsi = reshape(joint_moments.HipMoment(:, frontal_plane, :), [], 1);
    hip_rotation_moment_ipsi = reshape(joint_moments.HipMoment(:, transverse_plane, :), [], 1);

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.hip_flexion_moment_ipsi_Nm = hip_flexion_moment_ipsi;
    trial_table.hip_adduction_moment_ipsi_Nm = hip_adduction_moment_ipsi;
    trial_table.hip_rotation_moment_ipsi_Nm = hip_rotation_moment_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.hip_flexion_moment_contra_Nm = circshift(hip_flexion_moment_ipsi, shift);
    trial_table.hip_adduction_moment_contra_Nm = circshift(hip_adduction_moment_ipsi, shift);
    trial_table.hip_rotation_moment_contra_Nm = circshift(hip_rotation_moment_ipsi, shift);

    % Knee moments
    knee_flexion_moment_ipsi = reshape(joint_moments.KneeMoment(:, sagittal_plane, :), [], 1);
    knee_adduction_moment_ipsi = reshape(joint_moments.KneeMoment(:, frontal_plane, :), [], 1);
    knee_rotation_moment_ipsi = reshape(joint_moments.KneeMoment(:, transverse_plane, :), [], 1);

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.knee_flexion_moment_ipsi_Nm = knee_flexion_moment_ipsi;
    trial_table.knee_adduction_moment_ipsi_Nm = knee_adduction_moment_ipsi;
    trial_table.knee_rotation_moment_ipsi_Nm = knee_rotation_moment_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.knee_flexion_moment_contra_Nm = circshift(knee_flexion_moment_ipsi, shift);
    trial_table.knee_adduction_moment_contra_Nm = circshift(knee_adduction_moment_ipsi, shift);
    trial_table.knee_rotation_moment_contra_Nm = circshift(knee_rotation_moment_ipsi, shift);

    % Ankle moments
    ankle_dorsiflexion_moment_ipsi = reshape(joint_moments.AnkleMoment(:, sagittal_plane, :), [], 1);
    ankle_adduction_moment_ipsi = reshape(joint_moments.AnkleMoment(:, frontal_plane, :), [], 1);
    ankle_rotation_moment_ipsi = reshape(joint_moments.AnkleMoment(:, transverse_plane, :), [], 1);

    % Apply standard naming convention (right leg = ipsi, left leg = contra)
    trial_table.ankle_dorsiflexion_moment_ipsi_Nm = ankle_dorsiflexion_moment_ipsi;
    trial_table.ankle_adduction_moment_ipsi_Nm = ankle_adduction_moment_ipsi;
    trial_table.ankle_rotation_moment_ipsi_Nm = ankle_rotation_moment_ipsi;
    
    % Original data becomes contra (left leg)
    trial_table.ankle_dorsiflexion_moment_contra_Nm = circshift(ankle_dorsiflexion_moment_ipsi, shift);
    trial_table.ankle_adduction_moment_contra_Nm = circshift(ankle_adduction_moment_ipsi, shift);
    trial_table.ankle_rotation_moment_contra_Nm = circshift(ankle_rotation_moment_ipsi, shift);

    % Ground reaction forces - use standard naming convention
    grf_data = trial_struct.forceplates;

    % Ground reaction forces - use standard naming convention (combined legs)
    trial_table.vertical_grf_N = reshape(grf_data.Force(:, y, :), [], 1);
    trial_table.ap_grf_N = reshape(grf_data.Force(:, x, :), [], 1);
    trial_table.ml_grf_N = reshape(grf_data.Force(:, z, :), [], 1);

    % Center of pressure - use standard naming convention (combined legs)
    trial_table.cop_x_m = reshape(grf_data.CoP(:, x, :), [], 1);
    trial_table.cop_y_m = reshape(grf_data.CoP(:, y, :), [], 1);
    trial_table.cop_z_m = reshape(grf_data.CoP(:, z, :), [], 1);

    % Segment angles - extract from motion capture data and calculate derived angles
    segment_angles = trial_struct.jointAngles;
    
    % Pelvis angles - extract directly from PelvisAngles data
    pelvis_tilt = reshape(segment_angles.PelvisAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    pelvis_obliquity = reshape(segment_angles.PelvisAngles(:, frontal_plane, :), [], 1) * deg2rad_factor;
    pelvis_rotation = reshape(segment_angles.PelvisAngles(:, transverse_plane, :), [], 1) * deg2rad_factor;
    
    % Apply anatomical plane naming convention (pelvis angles are global, no ipsi/contra distinction)
    trial_table.pelvis_sagittal_angle_rad = pelvis_tilt;
    trial_table.pelvis_frontal_angle_rad = pelvis_obliquity;
    trial_table.pelvis_transverse_angle_rad = pelvis_rotation;
    
    % Foot angles - extract from FootProgressAngles data (sagittal plane for foot progression)
    foot_progression_ipsi = -reshape(segment_angles.FootProgressAngles(:, sagittal_plane, :), [], 1) * deg2rad_factor;
    
    % =========================================================================
    % FOOT ANGLE FIX: Apply corrections to foot sagittal angles BEFORE circshift
    % =========================================================================
    % Process each stride independently to:
    % 1. Apply iterative 90-degree offsets to bring first point within [-90, 90] range
    % 2. Check 70% midstance - if positive, sign flip entire stride
    
    midstance_idx = 105;  % 70% of 150-point cycle
    
    for stride = 1:num_strides
        stride_start = (stride-1)*pps + 1;
        stride_end = stride*pps;
        
        % Step 1: Apply iterative 90-degree offset correction to first point
        first_point = foot_progression_ipsi(stride_start);
        
        % Keep applying ±90 degree offsets until within range
        while first_point > deg2rad_factor * 50  % Greater than 90 degrees
            foot_progression_ipsi(stride_start:stride_end) = foot_progression_ipsi(stride_start:stride_end) - pi/2;
            first_point = first_point - pi/2;
        end
        
        while first_point < - deg2rad_factor * 50  % Less than -90 degrees
            foot_progression_ipsi(stride_start:stride_end) = foot_progression_ipsi(stride_start:stride_end) + pi/2;
            first_point = first_point + pi/2;
        end
        
        % Step 2: Check 70% midstance point for sign flip
        midstance_angle = foot_progression_ipsi(stride_start + midstance_idx - 1);
        if midstance_angle > 0  % Should be negative (plantarflexion at 70% cycle)
            foot_progression_ipsi(stride_start:stride_end) = -foot_progression_ipsi(stride_start:stride_end);
        end
    end
    
    % Apply anatomical plane naming convention (right leg = ipsi, left leg = contra)
    % Now the contra gets the corrected ipsi data through circshift
    trial_table.foot_sagittal_angle_ipsi_rad = foot_progression_ipsi;
    trial_table.foot_sagittal_angle_contra_rad = circshift(foot_progression_ipsi, shift);
    
    % Calculate derived segment angles using biomechanical relationships
    % thigh_angle = pelvis_tilt + hip_flexion
    thigh_angle_ipsi = (pelvis_tilt + hip_flexion_ipsi);
    trial_table.thigh_sagittal_angle_ipsi_rad = thigh_angle_ipsi;
    trial_table.thigh_sagittal_angle_contra_rad = circshift(thigh_angle_ipsi, shift);
    
    % shank_angle = thigh_angle - knee_flexion (note: using original thigh_angle calculation for consistency)
    shank_angle_ipsi = ((pelvis_tilt + hip_flexion_ipsi) - knee_flexion_ipsi);
    trial_table.shank_sagittal_angle_ipsi_rad = shank_angle_ipsi;
    trial_table.shank_sagittal_angle_contra_rad = circshift(shank_angle_ipsi, shift);

end