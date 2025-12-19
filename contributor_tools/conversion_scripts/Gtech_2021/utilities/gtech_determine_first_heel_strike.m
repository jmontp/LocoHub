function [first_leg, first_hs_time] = gtech_determine_first_heel_strike(trial_data, time_start, time_end)
%GTECH_DETERMINE_FIRST_HEEL_STRIKE Determine which leg heel-strikes first in a window.
%   [first_leg, first_hs_time] = gtech_determine_first_heel_strike(trial_data, ...
%       time_start, time_end)
%
% Uses gcRight/gcLeft tables and findFallingEdges_onlyInSection to find the
% first heel-strike event within the provided [time_start, time_end] window.
%
% Returns:
%   first_leg     'right', 'left', or '' if no heel strikes are found
%   first_hs_time Time (s) of the first heel strike (or [] if none)

first_leg = '';
first_hs_time = [];

% Check gait cycle tables exist
if ~isfield(trial_data, 'gcRight') || ~istable(trial_data.gcRight) || ...
   ~isfield(trial_data, 'gcLeft')  || ~istable(trial_data.gcLeft)
    return;
end

% Right leg heel strikes in window
gcR = trial_data.gcRight;
right_gc_time = gcR.Header;
right_window_indices = find(right_gc_time >= time_start & right_gc_time <= time_end);

if ~isempty(right_window_indices)
    right_hs_pct = gcR.HeelStrike;
    right_hs_indices = findFallingEdges_onlyInSection(right_hs_pct == 0, right_window_indices);
    if ~isempty(right_hs_indices)
        % Include the actual HS sample (index where HeelStrike is still 1)
        idx = max(1, right_hs_indices(1) - 1);
        right_first_hs_time = right_gc_time(idx);
    else
        right_first_hs_time = inf;
    end
else
    right_first_hs_time = inf;
end

% Left leg heel strikes in window
gcL = trial_data.gcLeft;
left_gc_time = gcL.Header;
left_window_indices = find(left_gc_time >= time_start & left_gc_time <= time_end);

if ~isempty(left_window_indices)
    left_hs_pct = gcL.HeelStrike;
    left_hs_indices = findFallingEdges_onlyInSection(left_hs_pct == 0, left_window_indices);
    if ~isempty(left_hs_indices)
        idx = max(1, left_hs_indices(1) - 1);
        left_first_hs_time = left_gc_time(idx);
    else
        left_first_hs_time = inf;
    end
else
    left_first_hs_time = inf;
end

% Decide which leg heel-strikes first
if right_first_hs_time < left_first_hs_time
    first_leg = 'right';
    first_hs_time = right_first_hs_time;
elseif left_first_hs_time < right_first_hs_time
    first_leg = 'left';
    first_hs_time = left_first_hs_time;
else
    % Either both inf or exactly equal; treat as no clear first leg
    first_leg = '';
    first_hs_time = [];
end

end

