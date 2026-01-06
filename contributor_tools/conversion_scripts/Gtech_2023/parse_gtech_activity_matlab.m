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
        
    elseif strcmp(activity_name, 'stand_to_sit')
        task_name = 'stand_to_sit';
        task_id = 'stand_to_sit';
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
        task_name = 'squat';  % Canonical name is singular
        task_id = 'squat';
        
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
        task_name = 'agility_drill';
        task_id = 'dynamic_walk';
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
        task_name = 'walk_backward';
        task_id = 'walk_backward';
        
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
        
    elseif strcmp(activity_name, 'ball_toss')
        task_name = 'load_handling';
        task_id = 'ball_toss';
        load_kg = 6.8; % 15 lbs
        info_parts = {sprintf('load_kg:%.1f', load_kg)};
        if ~isempty(sub_activity_name)
            info_parts{end+1} = sprintf('variant:%s', sub_activity_name);
        end
        task_info_str = strjoin(info_parts, ',');
        
    elseif strcmp(activity_name, 'lift_weight')
        task_name = 'load_handling';
        task_id = 'lift_weight';
        info_parts = {};
        if ~isempty(sub_activity_name)
            weight_match = regexp(sub_activity_name, '(\d+)lbs', 'tokens');
            if ~isempty(weight_match)
                weight_lbs = str2double(weight_match{1}{1});
                weight_kg = round(weight_lbs * 0.453592, 1);
                info_parts{end+1} = sprintf('load_kg:%.1f', weight_kg);
            end
            hand_match = regexp(sub_activity_name, '([lr])-([clr])', 'tokens');
            if ~isempty(hand_match)
                hand = hand_match{1}{1};
                position = hand_match{1}{2};
                info_parts{end+1} = sprintf('hand:%s', hand);
                info_parts{end+1} = sprintf('position:%s', position);
            end
            info_parts{end+1} = sprintf('variant:%s', sub_activity_name);
        end
        if isempty(info_parts)
            task_info_str = 'load_kg:0';
        else
            task_info_str = strjoin(info_parts, ',');
        end
        
    elseif strcmp(activity_name, 'cutting')
        task_name = 'cutting';
        task_id = 'cutting';
        info_parts = {};
        if ~isempty(sub_activity_name)
            if contains(sub_activity_name, 'left')
                info_parts{end+1} = 'direction:left';
            elseif contains(sub_activity_name, 'right')
                info_parts{end+1} = 'direction:right';
            end
            if contains(sub_activity_name, 'fast')
                info_parts{end+1} = 'speed:fast';
            elseif contains(sub_activity_name, 'slow')
                info_parts{end+1} = 'speed:slow';
            end
            info_parts{end+1} = sprintf('variant:%s', sub_activity_name);
        end
        if isempty(info_parts)
            task_info_str = '';
        else
            task_info_str = strjoin(info_parts, ',');
        end
        
    elseif strcmp(activity_name, 'lunges')
        task_name = 'agility_drill';
        task_id = 'lunges';
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
        
    elseif strcmp(activity_name, 'side_shuffle')
        task_name = 'agility_drill';
        task_id = 'side_shuffle';
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
        
    elseif strcmp(activity_name, 'tire_run')
        task_name = 'agility_drill';
        task_id = 'tire_run';
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
        
    elseif strcmp(activity_name, 'turn_and_step')
        task_name = 'agility_drill';
        task_id = 'turn_and_step';
        if ~isempty(sub_activity_name)
            info_parts = {sprintf('variant:%s', sub_activity_name)};
            if contains(sub_activity_name, 'left')
                info_parts{end+1} = 'direction:left';
            elseif contains(sub_activity_name, 'right')
                info_parts{end+1} = 'direction:right';
            end
            task_info_str = strjoin(info_parts, ',');
        end
        
    elseif strcmp(activity_name, 'meander') || strcmp(activity_name, 'obstacle_walk') || strcmp(activity_name, 'start_stop')
        task_name = 'free_walk_episode';
        task_id = activity_name;
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
        
    elseif strcmp(activity_name, 'push') || strcmp(activity_name, 'tug_of_war') || strcmp(activity_name, 'twister')
        task_name = 'perturbation';
        task_id = activity_name;
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end
        
    elseif strcmp(activity_name, 'poses')
        task_name = 'balance_pose';
        task_id = 'poses';
        if ~isempty(sub_activity_name)
            task_info_str = sprintf('variant:%s', sub_activity_name);
        end

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
