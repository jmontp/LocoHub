function [task_name, task_id, task_info_str] = parse_gtech_activity_matlab(activity_name, sub_activity_name)
% Parse Gtech activity name into standardized task hierarchy for MATLAB.
%
% This function provides the same mapping logic as the Python task_mapping.py
% to ensure consistency between time-indexed and phase-indexed conversions.
%
% Args:
%   activity_name: Base activity name (e.g., 'normal_walk', 'stairs')
%   sub_activity_name: Sub-activity parameters (e.g., 'up5', '1-2')
%
% Returns:
%   task_name: Standardized task category
%   task_id: Primary variant identifier
%   task_info_str: Metadata in key:value format

    % Default values
    task_name = 'functional_task';
    task_id = activity_name;
    task_info_str = '';
    
    % Parse based on activity type
    if strcmp(activity_name, 'normal_walk')
        task_name = 'level_walking';
        task_id = 'level';
        
        % Extract speed from sub_activity (e.g., "1-2" -> 1.2 m/s)
        if ~isempty(sub_activity_name)
            speed_match = regexp(sub_activity_name, '(\d+)-(\d+)', 'tokens');
            if ~isempty(speed_match)
                speed = str2double([speed_match{1}{1} '.' speed_match{1}{2}]);
                task_info_str = sprintf('speed_m_s:%.1f,treadmill:true', speed);
            elseif contains(sub_activity_name, 'shuffle') || contains(sub_activity_name, 'skip')
                task_info_str = sprintf('variant:%s,treadmill:true', sub_activity_name);
            else
                task_info_str = 'treadmill:true';
            end
        else
            task_info_str = 'treadmill:true';
        end
        
    elseif strcmp(activity_name, 'incline_walk')
        % Default to incline, will be changed to decline if needed
        task_name = 'incline_walking';
        
        if ~isempty(sub_activity_name)
            if contains(sub_activity_name, 'up', 'IgnoreCase', true)
                % Extract incline angle (e.g., "up5" -> 5 degrees)
                incline_match = regexp(sub_activity_name, 'up(\d+)', 'tokens', 'ignorecase');
                if ~isempty(incline_match)
                    incline = str2double(incline_match{1}{1});
                    task_id = sprintf('incline_%ddeg', incline);
                    task_info_str = sprintf('incline_deg:%d,treadmill:true', incline);
                else
                    task_id = 'incline';
                    task_info_str = 'treadmill:true';
                end
            elseif contains(sub_activity_name, 'down', 'IgnoreCase', true)
                task_name = 'decline_walking';
                % Extract decline angle (e.g., "down10" -> -10 degrees)
                decline_match = regexp(sub_activity_name, 'down(\d+)', 'tokens', 'ignorecase');
                if ~isempty(decline_match)
                    incline = str2double(decline_match{1}{1});
                    task_id = sprintf('decline_%ddeg', incline);
                    task_info_str = sprintf('incline_deg:%d,treadmill:true', -incline);
                else
                    task_id = 'decline';
                    task_info_str = 'treadmill:true';
                end
            else
                % Default to incline if direction unclear
                task_id = 'incline';
                task_info_str = 'treadmill:true';
            end
        else
            task_id = 'incline';
            task_info_str = 'treadmill:true';
        end
        
    elseif strcmp(activity_name, 'stairs')
        if ~isempty(sub_activity_name)
            if contains(sub_activity_name, 'up', 'IgnoreCase', true)
                task_name = 'stair_ascent';
                task_id = 'stair_ascent';
            elseif contains(sub_activity_name, 'down', 'IgnoreCase', true)
                task_name = 'stair_descent';
                task_id = 'stair_descent';
            else
                % Default to ascent
                task_name = 'stair_ascent';
                task_id = 'stair_ascent';
            end
            
            % Extract step number if present
            step_match = regexp(sub_activity_name, '(\d+)', 'tokens');
            if ~isempty(step_match)
                step_num = str2double(step_match{1}{1});
                task_info_str = sprintf('step_number:%d,height_m:0.15', step_num);
            else
                task_info_str = 'height_m:0.15';
            end
        else
            % Default to ascent
            task_name = 'stair_ascent';
            task_id = 'stair_ascent';
            task_info_str = 'height_m:0.15';
        end
        
    elseif strcmp(activity_name, 'sit_to_stand')
        task_name = 'sit_to_stand';
        task_id = 'sit_to_stand';
        
        if ~isempty(sub_activity_name)
            if contains(sub_activity_name, 'short', 'IgnoreCase', true)
                task_info_str = 'chair_height:low';
            elseif contains(sub_activity_name, 'tall', 'IgnoreCase', true)
                task_info_str = 'chair_height:standard';
            else
                task_info_str = '';
            end
            
            if contains(sub_activity_name, 'arm', 'IgnoreCase', true) && ~contains(sub_activity_name, 'noarm', 'IgnoreCase', true)
                if ~isempty(task_info_str)
                    task_info_str = [task_info_str ',armrests:true'];
                else
                    task_info_str = 'armrests:true';
                end
            elseif contains(sub_activity_name, 'noarm', 'IgnoreCase', true)
                if ~isempty(task_info_str)
                    task_info_str = [task_info_str ',armrests:false'];
                else
                    task_info_str = 'armrests:false';
                end
            end
        end
        
    elseif strcmp(activity_name, 'squats')
        task_name = 'squats';
        task_id = 'squats';
        
        if ~isempty(sub_activity_name)
            % Extract weight (e.g., "25lbs" -> 11.3 kg)
            weight_match = regexp(sub_activity_name, '(\d+)lbs', 'tokens');
            if ~isempty(weight_match)
                weight_lbs = str2double(weight_match{1}{1});
                weight_kg = round(weight_lbs * 0.453592, 1);
                task_info_str = sprintf('weight_kg:%.1f', weight_kg);
            end
        end
        
    elseif strcmp(activity_name, 'jump')
        task_name = 'jump';
        task_id = 'jump';
        
        if ~isempty(sub_activity_name)
            if contains(sub_activity_name, 'vertical', 'IgnoreCase', true)
                task_info_str = 'jump_type:vertical';
            elseif contains(sub_activity_name, 'fb', 'IgnoreCase', true)
                task_info_str = 'jump_type:forward_backward';
            elseif contains(sub_activity_name, 'lateral', 'IgnoreCase', true)
                task_info_str = 'jump_type:lateral';
            elseif contains(sub_activity_name, 'hop', 'IgnoreCase', true)
                task_info_str = 'jump_type:hop';
            elseif contains(sub_activity_name, '180', 'IgnoreCase', true)
                task_info_str = 'jump_type:turn_180';
            end
        end
        
    elseif strcmp(activity_name, 'dynamic_walk')
        task_name = 'level_walking';
        task_id = 'level';
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s,treadmill:true', sub_activity_name);
        else
            task_info_str = 'treadmill:true';
        end
        
    elseif strcmp(activity_name, 'weighted_walk')
        task_name = 'level_walking';
        task_id = 'level';
        
        if ~isempty(sub_activity_name)
            weight_match = regexp(sub_activity_name, '(\d+)lbs', 'tokens');
            if ~isempty(weight_match)
                weight_lbs = str2double(weight_match{1}{1});
                weight_kg = round(weight_lbs * 0.453592, 1);
                task_info_str = sprintf('weight_kg:%.1f,treadmill:true', weight_kg);
            else
                task_info_str = 'treadmill:true';
            end
        else
            task_info_str = 'treadmill:true';
        end
        
    elseif strcmp(activity_name, 'walk_backward')
        task_name = 'backward_walking';
        task_id = 'backward';
        
        if ~isempty(sub_activity_name)
            speed_match = regexp(sub_activity_name, '(\d+)-(\d+)', 'tokens');
            if ~isempty(speed_match)
                speed = str2double([speed_match{1}{1} '.' speed_match{1}{2}]);
                task_info_str = sprintf('speed_m_s:%.1f,treadmill:true', speed);
            else
                task_info_str = 'treadmill:true';
            end
        else
            task_info_str = 'treadmill:true';
        end
        
    elseif strcmp(activity_name, 'curb_up')
        task_name = 'step_up';
        task_id = 'step_up';
        task_info_str = 'height_m:0.15';
        
    elseif strcmp(activity_name, 'curb_down')
        task_name = 'step_down';
        task_id = 'step_down';
        task_info_str = 'height_m:0.15';
        
    elseif strcmp(activity_name, 'step_ups')
        task_name = 'step_up';
        task_id = 'step_up';
        task_info_str = 'height_m:0.20';
        
    else
        % Generic functional task for unrecognized activities
        task_name = 'functional_task';
        task_id = activity_name;
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
    end
    
    % Ensure task_info_str is never empty (set default if needed)
    if isempty(task_info_str)
        task_info_str = 'experiment:gtech_2023';
    end
end