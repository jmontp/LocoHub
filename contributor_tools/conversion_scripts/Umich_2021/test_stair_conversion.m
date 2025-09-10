% Test stair conversion with single subject to check for completion
clear; clc;

% Set global flag for data fixes
global ENABLE_DATA_FIXES;
ENABLE_DATA_FIXES = true;

% Load data
fprintf('Loading Streaming.mat...\n');
streaming_data = load('Streaming.mat');

% Initialize output
total_data = table();

% Test with just AB01
subject_id = 'AB01';
fprintf('\n========================================\n');
fprintf('Processing %s (STAIR TEST)\n', subject_id);
fprintf('========================================\n');

subject_data = streaming_data.Streaming.(subject_id);

% Process Stair only for quick test
if isfield(subject_data, 'Stair')
    fprintf('  Processing stair trials...\n');
    stair_data = subject_data.Stair;
    
    % Test with a few stair trials to check structure
    trial_names = {'s20dg_01', 's20dg_02', 's25dg_01', 's25dg_02'};
    
    for i = 1:length(trial_names)
        trial_name = trial_names{i};
        
        if isfield(stair_data, trial_name)
            trial_data = stair_data.(trial_name);
            
            fprintf('    Testing %s structure:\n', trial_name);
            fprintf('      Has events: %s\n', mat2str(isfield(trial_data, 'events')));
            fprintf('      Has jointAngles: %s\n', mat2str(isfield(trial_data, 'jointAngles')));
            fprintf('      Has jointMoments: %s\n', mat2str(isfield(trial_data, 'jointMoments')));
            fprintf('      Has forceplates: %s\n', mat2str(isfield(trial_data, 'forceplates')));
            
            if isfield(trial_data, 'events')
                events = trial_data.events;
                if isfield(events, 'RHeelStrike') && isfield(events, 'LHeelStrike')
                    fprintf('      R heel strikes: %d\n', length(events.RHeelStrike));
                    fprintf('      L heel strikes: %d\n', length(events.LHeelStrike));
                end
            end
        else
            fprintf('    Warning: Trial %s not found\n', trial_name);
        end
    end
else
    fprintf('  No Stair data found for %s\n', subject_id);
end

% Also test Wtr data
if isfield(subject_data, 'Wtr')
    fprintf('  Found Wtr data\n');
    wtr_data = subject_data.Wtr;
    fprintf('    Has events: %s\n', mat2str(isfield(wtr_data, 'events')));
    fprintf('    Has jointMoments: %s\n', mat2str(isfield(wtr_data, 'jointMoments')));
    fprintf('    Has forceplates: %s\n', mat2str(isfield(wtr_data, 'forceplates')));
else
    fprintf('  No Wtr data found for %s\n', subject_id);
end

fprintf('\nTest complete!\n');