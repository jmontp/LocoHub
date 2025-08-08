function [heel_strikes_right, heel_strikes_left] = detect_heel_strikes_from_markers(trial_data)
    % Detect heel strikes from marker data when gait cycle data is not available
    % Uses the existing getHeelStrikes function from the lib folder
    %
    % Inputs:
    %   trial_data - structure containing marker data
    %
    % Outputs:
    %   heel_strikes_right - indices of right heel strikes
    %   heel_strikes_left - indices of left heel strikes
    
    heel_strikes_right = [];
    heel_strikes_left = [];
    
    % Check if we have marker data
    if ~isfield(trial_data, 'markers')
        warning('No marker data available for heel strike detection');
        return;
    end
    
    markers = trial_data.markers;
    
    % Try to find heel markers
    % Common marker names for heel: RHEE, RHE, RightHeel, R_Heel, etc.
    right_heel_marker = [];
    left_heel_marker = [];
    
    marker_fields = fieldnames(markers);
    
    % Search for right heel marker
    right_patterns = {'RHEE', 'RHE', 'RightHeel', 'R_Heel', 'R_HEE', 'right_heel'};
    for i = 1:length(right_patterns)
        idx = find(contains(marker_fields, right_patterns{i}, 'IgnoreCase', true));
        if ~isempty(idx)
            right_heel_marker = markers.(marker_fields{idx(1)});
            break;
        end
    end
    
    % Search for left heel marker
    left_patterns = {'LHEE', 'LHE', 'LeftHeel', 'L_Heel', 'L_HEE', 'left_heel'};
    for i = 1:length(left_patterns)
        idx = find(contains(marker_fields, left_patterns{i}, 'IgnoreCase', true));
        if ~isempty(idx)
            left_heel_marker = markers.(marker_fields{idx(1)});
            break;
        end
    end
    
    % If heel markers not found, try ankle markers as fallback
    if isempty(right_heel_marker)
        right_patterns = {'RANK', 'RAnkle', 'R_Ankle', 'right_ankle'};
        for i = 1:length(right_patterns)
            idx = find(contains(marker_fields, right_patterns{i}, 'IgnoreCase', true));
            if ~isempty(idx)
                right_heel_marker = markers.(marker_fields{idx(1)});
                warning('Using ankle marker for right heel strike detection');
                break;
            end
        end
    end
    
    if isempty(left_heel_marker)
        left_patterns = {'LANK', 'LAnkle', 'L_Ankle', 'left_ankle'};
        for i = 1:length(left_patterns)
            idx = find(contains(marker_fields, left_patterns{i}, 'IgnoreCase', true));
            if ~isempty(idx)
                left_heel_marker = markers.(marker_fields{idx(1)});
                warning('Using ankle marker for left heel strike detection');
                break;
            end
        end
    end
    
    % Detect heel strikes using the velocity-based method
    if ~isempty(right_heel_marker)
        % Prepare data array [x, y, z]
        if size(right_heel_marker, 2) >= 3
            dataArr = right_heel_marker(:, 1:3);
        else
            warning('Right heel marker does not have 3D coordinates');
            dataArr = [];
        end
        
        if ~isempty(dataArr)
            try
                % Use the existing getStrikes function (from lib folder)
                addpath('../CAMARGO_ET_AL_J_BIOMECH_DATASET/scripts/lib/');
                [heel_strikes_right, ~] = getStrikes(dataArr, 'v_thresh_stance', 0.1, 'v_thresh_swing', 0.1);
            catch ME
                warning('Failed to detect right heel strikes: %s', ME.message);
                heel_strikes_right = [];
            end
        end
    end
    
    if ~isempty(left_heel_marker)
        % Prepare data array [x, y, z]
        if size(left_heel_marker, 2) >= 3
            dataArr = left_heel_marker(:, 1:3);
        else
            warning('Left heel marker does not have 3D coordinates');
            dataArr = [];
        end
        
        if ~isempty(dataArr)
            try
                % Use the existing getStrikes function
                [heel_strikes_left, ~] = getStrikes(dataArr, 'v_thresh_stance', 0.1, 'v_thresh_swing', 0.1);
            catch ME
                warning('Failed to detect left heel strikes: %s', ME.message);
                heel_strikes_left = [];
            end
        end
    end
    
    % Validate heel strikes
    heel_strikes_right = validate_heel_strikes(heel_strikes_right);
    heel_strikes_left = validate_heel_strikes(heel_strikes_left);
end

function strikes = validate_heel_strikes(strikes)
    % Validate and clean heel strike indices
    
    if isempty(strikes)
        return;
    end
    
    % Remove duplicates
    strikes = unique(strikes);
    
    % Sort in ascending order
    strikes = sort(strikes);
    
    % Remove strikes that are too close together (< 0.5 seconds at 100 Hz)
    min_samples = 50; % Minimum samples between strikes
    
    valid_strikes = strikes(1);
    for i = 2:length(strikes)
        if strikes(i) - valid_strikes(end) >= min_samples
            valid_strikes = [valid_strikes, strikes(i)];
        end
    end
    
    strikes = valid_strikes;
end