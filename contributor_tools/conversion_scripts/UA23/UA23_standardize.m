clear;close;clc;

T = table('Size', [0 48], ...
          'VariableTypes', {'string','string','string','string','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double','double','double', ...
                            'double','double','double'}, ...
          'VariableNames', {'subject','task','task_id','task_info','step', ...
                            'phase_ipsi','hip_flexion_angle_ipsi_rad', ...
                            'hip_adduction_angle_ipsi_rad','knee_flexion_angle_ipsi_rad', ...
                            'ankle_dorsiflexion_angle_ipsi_rad','hip_flexion_moment_ipsi_Nm_kg', ...
                            'knee_flexion_moment_ipsi_Nm_kg','ankle_dorsiflexion_moment_ipsi_Nm_kg', ...
                            'vertical_grf_ipsi_BW','hip_flexion_angle_contra_rad', ...
                            'knee_flexion_angle_contra_rad','ankle_dorsiflexion_angle_contra_rad', ...
                            'hip_flexion_moment_contra_Nm_kg','knee_flexion_moment_contra_Nm_kg', ...
                            'ankle_dorsiflexion_moment_contra_Nm_kg','pelvis_sagittal_angle_rad', ...
                            'pelvis_frontal_angle_rad','pelvis_transverse_angle_rad', ...
                            'trunk_sagittal_angle_rad','trunk_frontal_angle_rad', ...
                            'trunk_transverse_angle_rad','thigh_sagittal_angle_ipsi_rad', ...
                            'thigh_sagittal_angle_contra_rad','shank_sagittal_angle_ipsi_rad', ...
                            'shank_sagittal_angle_contra_rad','foot_sagittal_angle_ipsi_rad', ...
                            'foot_sagittal_angle_contra_rad','hip_flexion_velocity_ipsi_rad_s', ...
                            'hip_flexion_velocity_contra_rad_s', ...
                            'knee_flexion_velocity_ipsi_rad_s', ...
                            'knee_flexion_velocity_contra_rad_s', ...
                            'ankle_dorsiflexion_velocity_ipsi_rad_s', ...
                            'ankle_dorsiflexion_velocity_contra_rad_s', ...
                            'vertical_grf_contra_BW','anterior_grf_ipsi_BW', ...
                            'anterior_grf_contra_BW','lateral_grf_ipsi_BW', ...
                            'lateral_grf_contra_BW','cop_anterior_ipsi_m', ...
                            'cop_anterior_contra_m','cop_lateral_ipsi_m', ...
                            'cop_lateral_contra_m','hip_adduction_angle_contra_rad'});

Original = load('.\MAT_normalizedData_PostStrokeAdults_v27-02-23');
subj_info = readtable('.\subj_info.xlsx');

Npoints = 150;

prefix = 'UA23_';
subjs = subj_info.Subj_name;
subjects = cellfun(@(x) [prefix x], subjs, 'UniformOutput', false);
subjects = replace(subjects,'TVC','CVA');

task = 'level_walking_stroke';
task_id = 'level';

D2R = pi/180;
for i_subj = 1:1:length(subjs)
    subj = subjs{i_subj};
    subject = subjects{i_subj};
    subj_weight = subj_info.Weight_kg(i_subj);
    % All kinematics and kinetics data use the same conventions.
    %% Paretic Side
    strides_flag_P = Original.Sub(i_subj).events.P_GoodForcePlateLanding;
    
    for i_stride = 1:1:length(strides_flag_P)
    
        phase_ipsi = linspace(0,100,Npoints);
        hip_flexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.HipAngles.x(:,i_stride);
        hip_adduction_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.HipAngles.z(:,i_stride); % lateral positive
        knee_flexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.KneeAngles.x(:,i_stride);
        ankle_dorsiflexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.AnkleAngles.x(:,i_stride);
        if strides_flag_P(i_stride) == 1
            hip_flexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_PsideData.HipMoment.x(:,i_stride); 
            knee_flexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_PsideData.KneeMoment.x(:,i_stride);
            ankle_dorsiflexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_PsideData.AnkleMoment.x(:,i_stride);            
        end
        
        hip_flexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).PsideSegm_NsideData.HipAngles.x(:,i_stride);
        hip_adduction_angle_contra_rad_ = D2R * Original.Sub(i_subj).PsideSegm_NsideData.HipAngles.z(:,i_stride);
        knee_flexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).PsideSegm_NsideData.KneeAngles.x(:,i_stride);
        ankle_dorsiflexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).PsideSegm_NsideData.AnkleAngles.x(:,i_stride);
        if strides_flag_P(i_stride) == 1
            hip_flexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_NsideData.HipMoment.x(:,i_stride);
            knee_flexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_NsideData.KneeMoment.x(:,i_stride);
            ankle_dorsiflexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).PsideSegm_NsideData.AnkleMoment.x(:,i_stride);
        end
        
        pelvis_sagittal_angle_rad_ = - D2R * Original.Sub(i_subj).PsideSegm_PsideData.PelvisAngles.x(:,i_stride);
        pelvis_frontal_angle_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.PelvisAngles.z(:,i_stride);
        pelvis_transverse_angle_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.PelvisAngles.y(:,i_stride);
        trunk_sagittal_angle_rad_ = - D2R * Original.Sub(i_subj).PsideSegm_PsideData.ThoraxAngles.x(:,i_stride);
        trunk_frontal_angle_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.ThoraxAngles.z(:,i_stride);
        trunk_transverse_angle_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.ThoraxAngles.y(:,i_stride);
        thigh_sagittal_angle_ipsi_rad_ = hip_flexion_angle_ipsi_rad_ + pelvis_sagittal_angle_rad_;
        thigh_sagittal_angle_contra_rad_ = hip_flexion_angle_contra_rad_ + pelvis_sagittal_angle_rad_;
        foot_sagittal_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).PsideSegm_PsideData.FootProgressAngles.x(:,i_stride) + pi/2;
        foot_sagittal_angle_contra_rad_ = D2R * Original.Sub(i_subj).PsideSegm_NsideData.FootProgressAngles.x(:,i_stride) + pi/2;    
        shank_sagittal_angle_ipsi_rad_ =  - foot_sagittal_angle_ipsi_rad_ - ankle_dorsiflexion_angle_ipsi_rad_;
        shank_sagittal_angle_contra_rad_ =  - foot_sagittal_angle_contra_rad_ - ankle_dorsiflexion_angle_contra_rad_;

        if strides_flag_P(i_stride) == 1
            vertical_grf_ipsi_BW_ = Original.Sub(i_subj).PsideSegm_PsideData.GroundReactionForce.z(:,i_stride);
            vertical_grf_contra_BW_ = Original.Sub(i_subj).PsideSegm_NsideData.GroundReactionForce.z(:,i_stride);
            anterior_grf_ipsi_BW_ = Original.Sub(i_subj).PsideSegm_PsideData.GroundReactionForce.x(:,i_stride);
            anterior_grf_contra_BW_ = Original.Sub(i_subj).PsideSegm_NsideData.GroundReactionForce.x(:,i_stride);
            lateral_grf_ipsi_BW_ = - Original.Sub(i_subj).PsideSegm_PsideData.GroundReactionForce.y(:,i_stride);
            lateral_grf_contra_BW_ = - Original.Sub(i_subj).PsideSegm_NsideData.GroundReactionForce.y(:,i_stride);
        end
        ICstart = Original.Sub(i_subj).events.P_ICstart(i_stride);
        ICstop = Original.Sub(i_subj).events.P_ICstop(i_stride);
        if strides_flag_P(i_stride) == 1
            vertical_ANK_ipsi_m_ = Original.Sub(i_subj).PsideSegm_PsideData.ANK.z(:,i_stride) / 1000;
            vertical_ANK_contra_m_ = Original.Sub(i_subj).PsideSegm_NsideData.ANK.z(:,i_stride) / 1000;       
            ankle_adduction_moment_ipsi_Nm_kg_ = Original.Sub(i_subj).PsideSegm_PsideData.AnkleMoment.z(:,i_stride); % hit the ground with the lateral side of foot -> positive
            ankle_adduction_moment_contra_Nm_kg_ = Original.Sub(i_subj).PsideSegm_NsideData.AnkleMoment.z(:,i_stride);
        end
        TO_ipsi = Original.Sub(i_subj).events.P_TOnorm(i_stride);

        % velocity
        time_stride = (ICstop - ICstart)/100;
        if time_stride > 0
            timestamps = linspace(0,time_stride,1001);
            hip_flexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(hip_flexion_angle_ipsi_rad_)');
            knee_flexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(knee_flexion_angle_ipsi_rad_)');
            ankle_dorsiflexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(ankle_dorsiflexion_angle_ipsi_rad_)');
            hip_flexion_velocity_contra_rad_s_ = num_deriv(timestamps,(hip_flexion_angle_contra_rad_)');
            knee_flexion_velocity_contra_rad_s_ = num_deriv(timestamps,(knee_flexion_angle_contra_rad_)');
            ankle_dorsiflexion_velocity_contra_rad_s_ = num_deriv(timestamps,(ankle_dorsiflexion_angle_contra_rad_)');
        else
            hip_flexion_velocity_ipsi_rad_s_ = nan(1001,1);
            knee_flexion_velocity_ipsi_rad_s_ = nan(1001,1);
            ankle_dorsiflexion_velocity_ipsi_rad_s_ = nan(1001,1);
            hip_flexion_velocity_contra_rad_s_ = nan(1001,1);
            knee_flexion_velocity_contra_rad_s_ = nan(1001,1);
            ankle_dorsiflexion_velocity_contra_rad_s_ = nan(1001,1);
        end

        % COP
        if strides_flag_P(i_stride) == 1
            cop_anterior_ipsi_m_ = -(-ankle_dorsiflexion_moment_ipsi_Nm_kg_ + anterior_grf_ipsi_BW_ .* vertical_ANK_ipsi_m_) ./ vertical_grf_ipsi_BW_;
            cop_anterior_ipsi_m_(vertical_grf_ipsi_BW_*subj_weight < 40) = 0;
            if TO_ipsi < 1000 && TO_ipsi > 100
                cop_anterior_ipsi_m_(round(TO_ipsi) + 1:end) = 0;
            end
            cop_anterior_contra_m_ = -(-ankle_dorsiflexion_moment_contra_Nm_kg_ + anterior_grf_contra_BW_ .* vertical_ANK_contra_m_) ./ vertical_grf_contra_BW_;
            cop_anterior_contra_m_(vertical_grf_contra_BW_*subj_weight < 40) = 0;
            if time_stride > 0
                IC_contra = (Original.Sub(i_subj).events.P_IC_cnt(i_stride) - ICstart)/(ICstop - ICstart);
                TO_contra = (Original.Sub(i_subj).events.P_TO_cnt(i_stride) - ICstart)/(ICstop - ICstart);
                cop_anterior_contra_m_(round(TO_contra*1000 + 1):round(IC_contra*1000 + 1)) = 0;
            end
    
            cop_lateral_ipsi_m_ = (ankle_adduction_moment_ipsi_Nm_kg_ - lateral_grf_ipsi_BW_ .* vertical_ANK_ipsi_m_) ./ vertical_grf_ipsi_BW_; % lateral -> positive
            cop_lateral_ipsi_m_(vertical_grf_ipsi_BW_*subj_weight < 40) = 0;
            if TO_ipsi < 1000 && TO_ipsi > 100
                cop_lateral_ipsi_m_(round(TO_ipsi) + 1:end) = 0;
            end
            cop_lateral_contra_m_ = (ankle_adduction_moment_contra_Nm_kg_ - lateral_grf_contra_BW_ .* vertical_ANK_contra_m_) ./ vertical_grf_contra_BW_;
            cop_lateral_contra_m_(vertical_grf_contra_BW_*subj_weight < 40) = 0;
            if time_stride > 0
                cop_lateral_contra_m_(round(TO_contra*1000 + 1):round(IC_contra*1000 + 1)) = 0;
            end
        end

        % speed
        speed = subj_info.P_side_speed(strcmp(subj_info.Subj_name,subj));
        task_info = strcat('speed_m_s:',num2str(speed),',overground:true',',side:paretic');
        
        T_i = table('Size', [Npoints 48], ...
                    'VariableTypes', {'string','string','string','string','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double'}, ...
                    'VariableNames', {'subject','task','task_id','task_info','step', ...
                                      'phase_ipsi','hip_flexion_angle_ipsi_rad', ...
                                      'hip_adduction_angle_ipsi_rad','knee_flexion_angle_ipsi_rad', ...
                                      'ankle_dorsiflexion_angle_ipsi_rad','hip_flexion_moment_ipsi_Nm_kg', ...
                                      'knee_flexion_moment_ipsi_Nm_kg','ankle_dorsiflexion_moment_ipsi_Nm_kg', ...
                                      'vertical_grf_ipsi_BW','hip_flexion_angle_contra_rad', ...
                                      'knee_flexion_angle_contra_rad','ankle_dorsiflexion_angle_contra_rad', ...
                                      'hip_flexion_moment_contra_Nm_kg','knee_flexion_moment_contra_Nm_kg', ...
                                      'ankle_dorsiflexion_moment_contra_Nm_kg','pelvis_sagittal_angle_rad', ...
                                      'pelvis_frontal_angle_rad','pelvis_transverse_angle_rad', ...
                                      'trunk_sagittal_angle_rad','trunk_frontal_angle_rad', ...
                                      'trunk_transverse_angle_rad','thigh_sagittal_angle_ipsi_rad', ...
                                      'thigh_sagittal_angle_contra_rad','shank_sagittal_angle_ipsi_rad', ...
                                      'shank_sagittal_angle_contra_rad','foot_sagittal_angle_ipsi_rad', ...
                                      'foot_sagittal_angle_contra_rad','hip_flexion_velocity_ipsi_rad_s', ...
                                      'hip_flexion_velocity_contra_rad_s', ...
                                      'knee_flexion_velocity_ipsi_rad_s', ...
                                      'knee_flexion_velocity_contra_rad_s', ...
                                      'ankle_dorsiflexion_velocity_ipsi_rad_s', ...
                                      'ankle_dorsiflexion_velocity_contra_rad_s', ...
                                      'vertical_grf_contra_BW','anterior_grf_ipsi_BW', ...
                                      'anterior_grf_contra_BW','lateral_grf_ipsi_BW', ...
                                      'lateral_grf_contra_BW','cop_anterior_ipsi_m', ...
                                      'cop_anterior_contra_m','cop_lateral_ipsi_m', ...
                                      'cop_lateral_contra_m','hip_adduction_angle_contra_rad'});         
        T_i.subject(:) = subject;
        T_i.task(:) = task;
        T_i.task_id(:) = task_id;
        T_i.task_info(:) = task_info;
        T_i.step(:) = i_stride;
        T_i.phase_ipsi = phase_ipsi';
        T_i.hip_flexion_angle_ipsi_rad = my_resample(hip_flexion_angle_ipsi_rad_,Npoints);
        T_i.hip_adduction_angle_ipsi_rad = my_resample(hip_adduction_angle_ipsi_rad_,Npoints);
        T_i.knee_flexion_angle_ipsi_rad = my_resample(knee_flexion_angle_ipsi_rad_,Npoints);
        T_i.ankle_dorsiflexion_angle_ipsi_rad = my_resample(ankle_dorsiflexion_angle_ipsi_rad_,Npoints);
        if strides_flag_P(i_stride) == 1
            T_i.hip_flexion_moment_ipsi_Nm_kg = my_resample(hip_flexion_moment_ipsi_Nm_kg_,Npoints);
            T_i.knee_flexion_moment_ipsi_Nm_kg = my_resample(knee_flexion_moment_ipsi_Nm_kg_,Npoints);
            T_i.ankle_dorsiflexion_moment_ipsi_Nm_kg = my_resample(ankle_dorsiflexion_moment_ipsi_Nm_kg_,Npoints);
        else
            T_i.hip_flexion_moment_ipsi_Nm_kg = nan(Npoints,1);
            T_i.knee_flexion_moment_ipsi_Nm_kg = nan(Npoints,1);
            T_i.ankle_dorsiflexion_moment_ipsi_Nm_kg = nan(Npoints,1);
        end
        T_i.hip_flexion_angle_contra_rad = my_resample(hip_flexion_angle_contra_rad_,Npoints);
        T_i.hip_adduction_angle_contra_rad = my_resample(hip_adduction_angle_contra_rad_,Npoints);
        T_i.knee_flexion_angle_contra_rad = my_resample(knee_flexion_angle_contra_rad_,Npoints);
        T_i.ankle_dorsiflexion_angle_contra_rad = my_resample(ankle_dorsiflexion_angle_contra_rad_,Npoints);
        if strides_flag_P(i_stride) == 1
            T_i.hip_flexion_moment_contra_Nm_kg = my_resample(hip_flexion_moment_contra_Nm_kg_,Npoints);
            T_i.knee_flexion_moment_contra_Nm_kg = my_resample(knee_flexion_moment_contra_Nm_kg_,Npoints);
            T_i.ankle_dorsiflexion_moment_contra_Nm_kg = my_resample(ankle_dorsiflexion_moment_contra_Nm_kg_,Npoints);
        else
            T_i.hip_flexion_moment_contra_Nm_kg = nan(Npoints,1);
            T_i.knee_flexion_moment_contra_Nm_kg = nan(Npoints,1);
            T_i.ankle_dorsiflexion_moment_contra_Nm_kg = nan(Npoints,1);
        end
        T_i.pelvis_sagittal_angle_rad = my_resample(pelvis_sagittal_angle_rad_,Npoints);
        T_i.pelvis_frontal_angle_rad = my_resample(pelvis_frontal_angle_rad_,Npoints);
        T_i.pelvis_transverse_angle_rad = my_resample(pelvis_transverse_angle_rad_,Npoints);
        T_i.trunk_sagittal_angle_rad = my_resample(trunk_sagittal_angle_rad_,Npoints);
        T_i.trunk_frontal_angle_rad = my_resample(trunk_frontal_angle_rad_,Npoints);
        T_i.trunk_transverse_angle_rad = my_resample(trunk_transverse_angle_rad_,Npoints);
        T_i.thigh_sagittal_angle_ipsi_rad = my_resample(thigh_sagittal_angle_ipsi_rad_,Npoints);
        T_i.thigh_sagittal_angle_contra_rad = my_resample(thigh_sagittal_angle_contra_rad_,Npoints);
        T_i.shank_sagittal_angle_ipsi_rad = my_resample(shank_sagittal_angle_ipsi_rad_,Npoints);
        T_i.shank_sagittal_angle_contra_rad = my_resample(shank_sagittal_angle_contra_rad_,Npoints);
        T_i.foot_sagittal_angle_ipsi_rad = my_resample(foot_sagittal_angle_ipsi_rad_,Npoints);
        T_i.foot_sagittal_angle_contra_rad = my_resample(foot_sagittal_angle_contra_rad_,Npoints);
        T_i.hip_flexion_velocity_ipsi_rad_s = my_resample(hip_flexion_velocity_ipsi_rad_s_,Npoints);
        T_i.hip_flexion_velocity_contra_rad_s = my_resample(hip_flexion_velocity_contra_rad_s_,Npoints);
        T_i.knee_flexion_velocity_ipsi_rad_s = my_resample(knee_flexion_velocity_ipsi_rad_s_,Npoints);
        T_i.knee_flexion_velocity_contra_rad_s = my_resample(knee_flexion_velocity_contra_rad_s_,Npoints);
        T_i.ankle_dorsiflexion_velocity_ipsi_rad_s = my_resample(ankle_dorsiflexion_velocity_ipsi_rad_s_,Npoints);
        T_i.ankle_dorsiflexion_velocity_contra_rad_s = my_resample(ankle_dorsiflexion_velocity_contra_rad_s_,Npoints);
        if strides_flag_P(i_stride) == 1
            T_i.vertical_grf_ipsi_BW = my_resample(vertical_grf_ipsi_BW_,Npoints);
            T_i.vertical_grf_contra_BW = my_resample(vertical_grf_contra_BW_,Npoints);
            T_i.anterior_grf_ipsi_BW = my_resample(anterior_grf_ipsi_BW_,Npoints);
            T_i.anterior_grf_contra_BW = my_resample(anterior_grf_contra_BW_,Npoints);
            T_i.lateral_grf_ipsi_BW = my_resample(lateral_grf_ipsi_BW_,Npoints);
            T_i.lateral_grf_contra_BW = my_resample(lateral_grf_contra_BW_,Npoints);
            T_i.cop_anterior_ipsi_m = my_resample(cop_anterior_ipsi_m_,Npoints);
            T_i.cop_anterior_contra_m = my_resample(cop_anterior_contra_m_,Npoints);
            T_i.cop_lateral_ipsi_m = my_resample(cop_lateral_ipsi_m_,Npoints);
            T_i.cop_lateral_contra_m = my_resample(cop_lateral_contra_m_,Npoints);
        else
            T_i.vertical_grf_ipsi_BW = nan(Npoints,1);
            T_i.vertical_grf_contra_BW = nan(Npoints,1);
            T_i.anterior_grf_ipsi_BW = nan(Npoints,1);
            T_i.anterior_grf_contra_BW = nan(Npoints,1);
            T_i.lateral_grf_ipsi_BW = nan(Npoints,1);
            T_i.lateral_grf_contra_BW = nan(Npoints,1);
            T_i.cop_anterior_ipsi_m = nan(Npoints,1);
            T_i.cop_anterior_contra_m = nan(Npoints,1);
            T_i.cop_lateral_ipsi_m = nan(Npoints,1);
            T_i.cop_lateral_contra_m = nan(Npoints,1);
        end

        T = [T; T_i];
    end

    %% Normative Side
    strides_flag_N = Original.Sub(i_subj).events.N_GoodForcePlateLanding;
    
    for i_stride = 1:1:length(strides_flag_N)
    
        phase_ipsi = linspace(0,100,Npoints);
        hip_flexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.HipAngles.x(:,i_stride);
        hip_adduction_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.HipAngles.z(:,i_stride); % lateral positive
        knee_flexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.KneeAngles.x(:,i_stride);
        ankle_dorsiflexion_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.AnkleAngles.x(:,i_stride);
        if strides_flag_N(i_stride) == 1
            hip_flexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_NsideData.HipMoment.x(:,i_stride); 
            knee_flexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_NsideData.KneeMoment.x(:,i_stride);
            ankle_dorsiflexion_moment_ipsi_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_NsideData.AnkleMoment.x(:,i_stride);            
        end
        
        hip_flexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).NsideSegm_PsideData.HipAngles.x(:,i_stride);
        hip_adduction_angle_contra_rad_ = D2R * Original.Sub(i_subj).NsideSegm_PsideData.HipAngles.z(:,i_stride);
        knee_flexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).NsideSegm_PsideData.KneeAngles.x(:,i_stride);
        ankle_dorsiflexion_angle_contra_rad_ = D2R * Original.Sub(i_subj).NsideSegm_PsideData.AnkleAngles.x(:,i_stride);
        if strides_flag_N(i_stride) == 1
            hip_flexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_PsideData.HipMoment.x(:,i_stride);
            knee_flexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_PsideData.KneeMoment.x(:,i_stride);
            ankle_dorsiflexion_moment_contra_Nm_kg_ = - Original.Sub(i_subj).NsideSegm_PsideData.AnkleMoment.x(:,i_stride);
        end
        
        pelvis_sagittal_angle_rad_ = - D2R * Original.Sub(i_subj).NsideSegm_NsideData.PelvisAngles.x(:,i_stride);
        pelvis_frontal_angle_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.PelvisAngles.z(:,i_stride);
        pelvis_transverse_angle_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.PelvisAngles.y(:,i_stride);
        trunk_sagittal_angle_rad_ = - D2R * Original.Sub(i_subj).NsideSegm_NsideData.ThoraxAngles.x(:,i_stride);
        trunk_frontal_angle_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.ThoraxAngles.z(:,i_stride);
        trunk_transverse_angle_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.ThoraxAngles.y(:,i_stride);
        thigh_sagittal_angle_ipsi_rad_ = hip_flexion_angle_ipsi_rad_ + pelvis_sagittal_angle_rad_;
        thigh_sagittal_angle_contra_rad_ = hip_flexion_angle_contra_rad_ + pelvis_sagittal_angle_rad_;
        foot_sagittal_angle_ipsi_rad_ = D2R * Original.Sub(i_subj).NsideSegm_NsideData.FootProgressAngles.x(:,i_stride) + pi/2;
        foot_sagittal_angle_contra_rad_ = D2R * Original.Sub(i_subj).NsideSegm_PsideData.FootProgressAngles.x(:,i_stride) + pi/2;    
        shank_sagittal_angle_ipsi_rad_ =  - foot_sagittal_angle_ipsi_rad_ - ankle_dorsiflexion_angle_ipsi_rad_;
        shank_sagittal_angle_contra_rad_ =  - foot_sagittal_angle_contra_rad_ - ankle_dorsiflexion_angle_contra_rad_;

        if strides_flag_N(i_stride) == 1
            vertical_grf_ipsi_BW_ = Original.Sub(i_subj).NsideSegm_NsideData.GroundReactionForce.z(:,i_stride);
            vertical_grf_contra_BW_ = Original.Sub(i_subj).NsideSegm_PsideData.GroundReactionForce.z(:,i_stride);
            anterior_grf_ipsi_BW_ = Original.Sub(i_subj).NsideSegm_NsideData.GroundReactionForce.x(:,i_stride);
            anterior_grf_contra_BW_ = Original.Sub(i_subj).NsideSegm_PsideData.GroundReactionForce.x(:,i_stride);
            lateral_grf_ipsi_BW_ = - Original.Sub(i_subj).NsideSegm_NsideData.GroundReactionForce.y(:,i_stride);
            lateral_grf_contra_BW_ = - Original.Sub(i_subj).NsideSegm_PsideData.GroundReactionForce.y(:,i_stride);
        end

        ICstart = Original.Sub(i_subj).events.N_ICstart(i_stride);
        ICstop = Original.Sub(i_subj).events.N_ICstop(i_stride);
        if strides_flag_N(i_stride) == 1
            vertical_ANK_ipsi_m_ = Original.Sub(i_subj).NsideSegm_NsideData.ANK.z(:,i_stride) / 1000;
            vertical_ANK_contra_m_ = Original.Sub(i_subj).NsideSegm_PsideData.ANK.z(:,i_stride) / 1000;
            ankle_adduction_moment_ipsi_Nm_kg_ = Original.Sub(i_subj).NsideSegm_NsideData.AnkleMoment.z(:,i_stride); % hit the ground with the lateral side of foot -> positive
            ankle_adduction_moment_contra_Nm_kg_ = Original.Sub(i_subj).NsideSegm_PsideData.AnkleMoment.z(:,i_stride);
        end
        TO_ipsi = Original.Sub(i_subj).events.N_TOnorm(i_stride);

        % velocity
        time_stride = (ICstop - ICstart)/100;
        if  time_stride > 0
            timestamps = linspace(0,time_stride,1001);
            hip_flexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(hip_flexion_angle_ipsi_rad_)');
            knee_flexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(knee_flexion_angle_ipsi_rad_)');
            ankle_dorsiflexion_velocity_ipsi_rad_s_ = num_deriv(timestamps,(ankle_dorsiflexion_angle_ipsi_rad_)');
            hip_flexion_velocity_contra_rad_s_ = num_deriv(timestamps,(hip_flexion_angle_contra_rad_)');
            knee_flexion_velocity_contra_rad_s_ = num_deriv(timestamps,(knee_flexion_angle_contra_rad_)');
            ankle_dorsiflexion_velocity_contra_rad_s_ = num_deriv(timestamps,(ankle_dorsiflexion_angle_contra_rad_)');
        else
            hip_flexion_velocity_ipsi_rad_s_ = nan(1001,1);
            knee_flexion_velocity_ipsi_rad_s_ = nan(1001,1);
            ankle_dorsiflexion_velocity_ipsi_rad_s_ = nan(1001,1);
            hip_flexion_velocity_contra_rad_s_ = nan(1001,1);
            knee_flexion_velocity_contra_rad_s_ = nan(1001,1);
            ankle_dorsiflexion_velocity_contra_rad_s_ = nan(1001,1);
        end
        % COP
        if strides_flag_N(i_stride) == 1
            cop_anterior_ipsi_m_ = -(-ankle_dorsiflexion_moment_ipsi_Nm_kg_ + anterior_grf_ipsi_BW_ .* vertical_ANK_ipsi_m_) ./ vertical_grf_ipsi_BW_;
            cop_anterior_ipsi_m_(vertical_grf_ipsi_BW_*subj_weight < 40) = 0;
            if TO_ipsi < 1000 && TO_ipsi > 100
                cop_anterior_ipsi_m_(round(TO_ipsi) + 1:end) = 0;
            end
            cop_anterior_contra_m_ = -(-ankle_dorsiflexion_moment_contra_Nm_kg_ + anterior_grf_contra_BW_ .* vertical_ANK_contra_m_) ./ vertical_grf_contra_BW_;
            cop_anterior_contra_m_(vertical_grf_contra_BW_*subj_weight < 40) = 0;
            if time_stride > 0
                IC_contra = (Original.Sub(i_subj).events.N_IC_cnt(i_stride) - ICstart)/(ICstop - ICstart);
                TO_contra = (Original.Sub(i_subj).events.N_TO_cnt(i_stride) - ICstart)/(ICstop - ICstart);
                cop_anterior_contra_m_(round(TO_contra*1000 + 1):round(IC_contra*1000 + 1)) = 0;
            end
    
            cop_lateral_ipsi_m_ = (ankle_adduction_moment_ipsi_Nm_kg_ - lateral_grf_ipsi_BW_ .* vertical_ANK_ipsi_m_) ./ vertical_grf_ipsi_BW_; % lateral -> positive
            cop_lateral_ipsi_m_(vertical_grf_ipsi_BW_*subj_weight < 40) = 0;
            if TO_ipsi < 1000 && TO_ipsi > 100
                cop_lateral_ipsi_m_(round(TO_ipsi) + 1:end) = 0;
            end
            cop_lateral_contra_m_ = (ankle_adduction_moment_contra_Nm_kg_ - lateral_grf_contra_BW_ .* vertical_ANK_contra_m_) ./ vertical_grf_contra_BW_;
            cop_lateral_contra_m_(vertical_grf_contra_BW_*subj_weight < 40) = 0;
            if time_stride > 0
                cop_lateral_contra_m_(round(TO_contra*1000 + 1):round(IC_contra*1000 + 1)) = 0;
            end
        end

        % speed
        speed = subj_info.N_side_speed(strcmp(subj_info.Subj_name,subj));
        task_info = strcat('speed_m_s:',num2str(speed),',overground:true',',side:non-paretic');

        T_i = table('Size', [Npoints 48], ...
                    'VariableTypes', {'string','string','string','string','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double','double','double', ...
                                      'double','double','double'}, ...
                    'VariableNames', {'subject','task','task_id','task_info','step', ...
                                      'phase_ipsi','hip_flexion_angle_ipsi_rad', ...
                                      'hip_adduction_angle_ipsi_rad','knee_flexion_angle_ipsi_rad', ...
                                      'ankle_dorsiflexion_angle_ipsi_rad','hip_flexion_moment_ipsi_Nm_kg', ...
                                      'knee_flexion_moment_ipsi_Nm_kg','ankle_dorsiflexion_moment_ipsi_Nm_kg', ...
                                      'vertical_grf_ipsi_BW','hip_flexion_angle_contra_rad', ...
                                      'knee_flexion_angle_contra_rad','ankle_dorsiflexion_angle_contra_rad', ...
                                      'hip_flexion_moment_contra_Nm_kg','knee_flexion_moment_contra_Nm_kg', ...
                                      'ankle_dorsiflexion_moment_contra_Nm_kg','pelvis_sagittal_angle_rad', ...
                                      'pelvis_frontal_angle_rad','pelvis_transverse_angle_rad', ...
                                      'trunk_sagittal_angle_rad','trunk_frontal_angle_rad', ...
                                      'trunk_transverse_angle_rad','thigh_sagittal_angle_ipsi_rad', ...
                                      'thigh_sagittal_angle_contra_rad','shank_sagittal_angle_ipsi_rad', ...
                                      'shank_sagittal_angle_contra_rad','foot_sagittal_angle_ipsi_rad', ...
                                      'foot_sagittal_angle_contra_rad','hip_flexion_velocity_ipsi_rad_s', ...
                                      'hip_flexion_velocity_contra_rad_s', ...
                                      'knee_flexion_velocity_ipsi_rad_s', ...
                                      'knee_flexion_velocity_contra_rad_s', ...
                                      'ankle_dorsiflexion_velocity_ipsi_rad_s', ...
                                      'ankle_dorsiflexion_velocity_contra_rad_s', ...
                                      'vertical_grf_contra_BW','anterior_grf_ipsi_BW', ...
                                      'anterior_grf_contra_BW','lateral_grf_ipsi_BW', ...
                                      'lateral_grf_contra_BW','cop_anterior_ipsi_m', ...
                                      'cop_anterior_contra_m','cop_lateral_ipsi_m', ...
                                      'cop_lateral_contra_m','hip_adduction_angle_contra_rad'});         
        T_i.subject(:) = subject;
        T_i.task(:) = task;
        T_i.task_id(:) = task_id;
        T_i.task_info(:) = task_info;
        T_i.step(:) = i_stride;
        T_i.phase_ipsi = phase_ipsi';
        T_i.hip_flexion_angle_ipsi_rad = my_resample(hip_flexion_angle_ipsi_rad_,Npoints);
        T_i.hip_adduction_angle_ipsi_rad = my_resample(hip_adduction_angle_ipsi_rad_,Npoints);
        T_i.knee_flexion_angle_ipsi_rad = my_resample(knee_flexion_angle_ipsi_rad_,Npoints);
        T_i.ankle_dorsiflexion_angle_ipsi_rad = my_resample(ankle_dorsiflexion_angle_ipsi_rad_,Npoints);
        if strides_flag_N(i_stride) == 1
            T_i.hip_flexion_moment_ipsi_Nm_kg = my_resample(hip_flexion_moment_ipsi_Nm_kg_,Npoints);
            T_i.knee_flexion_moment_ipsi_Nm_kg = my_resample(knee_flexion_moment_ipsi_Nm_kg_,Npoints);
            T_i.ankle_dorsiflexion_moment_ipsi_Nm_kg = my_resample(ankle_dorsiflexion_moment_ipsi_Nm_kg_,Npoints);
        else
            T_i.hip_flexion_moment_ipsi_Nm_kg = nan(Npoints,1);
            T_i.knee_flexion_moment_ipsi_Nm_kg = nan(Npoints,1);
            T_i.ankle_dorsiflexion_moment_ipsi_Nm_kg = nan(Npoints,1);
        end
        T_i.hip_flexion_angle_contra_rad = my_resample(hip_flexion_angle_contra_rad_,Npoints);
        T_i.hip_adduction_angle_contra_rad = my_resample(hip_adduction_angle_contra_rad_,Npoints);
        T_i.knee_flexion_angle_contra_rad = my_resample(knee_flexion_angle_contra_rad_,Npoints);
        T_i.ankle_dorsiflexion_angle_contra_rad = my_resample(ankle_dorsiflexion_angle_contra_rad_,Npoints);
        if strides_flag_N(i_stride) == 1
            T_i.hip_flexion_moment_contra_Nm_kg = my_resample(hip_flexion_moment_contra_Nm_kg_,Npoints);
            T_i.knee_flexion_moment_contra_Nm_kg = my_resample(knee_flexion_moment_contra_Nm_kg_,Npoints);
            T_i.ankle_dorsiflexion_moment_contra_Nm_kg = my_resample(ankle_dorsiflexion_moment_contra_Nm_kg_,Npoints);
        else
            T_i.hip_flexion_moment_contra_Nm_kg = nan(Npoints,1);
            T_i.knee_flexion_moment_contra_Nm_kg = nan(Npoints,1);
            T_i.ankle_dorsiflexion_moment_contra_Nm_kg = nan(Npoints,1);
        end
        T_i.pelvis_sagittal_angle_rad = my_resample(pelvis_sagittal_angle_rad_,Npoints);
        T_i.pelvis_frontal_angle_rad = my_resample(pelvis_frontal_angle_rad_,Npoints);
        T_i.pelvis_transverse_angle_rad = my_resample(pelvis_transverse_angle_rad_,Npoints);
        T_i.trunk_sagittal_angle_rad = my_resample(trunk_sagittal_angle_rad_,Npoints);
        T_i.trunk_frontal_angle_rad = my_resample(trunk_frontal_angle_rad_,Npoints);
        T_i.trunk_transverse_angle_rad = my_resample(trunk_transverse_angle_rad_,Npoints);
        T_i.thigh_sagittal_angle_ipsi_rad = my_resample(thigh_sagittal_angle_ipsi_rad_,Npoints);
        T_i.thigh_sagittal_angle_contra_rad = my_resample(thigh_sagittal_angle_contra_rad_,Npoints);
        T_i.shank_sagittal_angle_ipsi_rad = my_resample(shank_sagittal_angle_ipsi_rad_,Npoints);
        T_i.shank_sagittal_angle_contra_rad = my_resample(shank_sagittal_angle_contra_rad_,Npoints);
        T_i.foot_sagittal_angle_ipsi_rad = my_resample(foot_sagittal_angle_ipsi_rad_,Npoints);
        T_i.foot_sagittal_angle_contra_rad = my_resample(foot_sagittal_angle_contra_rad_,Npoints);
        T_i.hip_flexion_velocity_ipsi_rad_s = my_resample(hip_flexion_velocity_ipsi_rad_s_,Npoints);
        T_i.hip_flexion_velocity_contra_rad_s = my_resample(hip_flexion_velocity_contra_rad_s_,Npoints);
        T_i.knee_flexion_velocity_ipsi_rad_s = my_resample(knee_flexion_velocity_ipsi_rad_s_,Npoints);
        T_i.knee_flexion_velocity_contra_rad_s = my_resample(knee_flexion_velocity_contra_rad_s_,Npoints);
        T_i.ankle_dorsiflexion_velocity_ipsi_rad_s = my_resample(ankle_dorsiflexion_velocity_ipsi_rad_s_,Npoints);
        T_i.ankle_dorsiflexion_velocity_contra_rad_s = my_resample(ankle_dorsiflexion_velocity_contra_rad_s_,Npoints);
        if strides_flag_N(i_stride) == 1
            T_i.vertical_grf_ipsi_BW = my_resample(vertical_grf_ipsi_BW_,Npoints);
            T_i.vertical_grf_contra_BW = my_resample(vertical_grf_contra_BW_,Npoints);
            T_i.anterior_grf_ipsi_BW = my_resample(anterior_grf_ipsi_BW_,Npoints);
            T_i.anterior_grf_contra_BW = my_resample(anterior_grf_contra_BW_,Npoints);
            T_i.lateral_grf_ipsi_BW = my_resample(lateral_grf_ipsi_BW_,Npoints);
            T_i.lateral_grf_contra_BW = my_resample(lateral_grf_contra_BW_,Npoints);
            T_i.cop_anterior_ipsi_m = my_resample(cop_anterior_ipsi_m_,Npoints);
            T_i.cop_anterior_contra_m = my_resample(cop_anterior_contra_m_,Npoints);
            T_i.cop_lateral_ipsi_m = my_resample(cop_lateral_ipsi_m_,Npoints);
            T_i.cop_lateral_contra_m = my_resample(cop_lateral_contra_m_,Npoints);
        else
            T_i.vertical_grf_ipsi_BW = nan(Npoints,1);
            T_i.vertical_grf_contra_BW = nan(Npoints,1);
            T_i.anterior_grf_ipsi_BW = nan(Npoints,1);
            T_i.anterior_grf_contra_BW = nan(Npoints,1);
            T_i.lateral_grf_ipsi_BW = nan(Npoints,1);
            T_i.lateral_grf_contra_BW = nan(Npoints,1);
            T_i.cop_anterior_ipsi_m = nan(Npoints,1);
            T_i.cop_anterior_contra_m = nan(Npoints,1);
            T_i.cop_lateral_ipsi_m = nan(Npoints,1);
            T_i.cop_lateral_contra_m = nan(Npoints,1);
        end

        T = [T; T_i];
    end
end

parquet_name = strcat('.\',prefix,'stroke_dataset.parquet');
parquetwrite(parquet_name, T);

disp('All done!:)')