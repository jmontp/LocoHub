% Debug script to show table column differences
clear; clc;

% Load a sample of walking data
fprintf('Loading Streaming.mat...\n');
streaming_data = load('Streaming.mat');
subject_data = streaming_data.Streaming.AB01;

% Get a sample walking trial
trial = subject_data.Tread.s1_i0.trial;
events = subject_data.Tread.s1_i0.events;

% Process a single walking stride
stride_table_walk = process_strides_with_segment_events(trial, events, ...
    1, 1000, 'SUB01', 'test_metadata', 70, 'level_walking', 'level', 'speed_m_s:1.0');

if ~isempty(stride_table_walk)
    fprintf('\nWalking table has %d variables:\n', width(stride_table_walk));
    walk_vars = stride_table_walk.Properties.VariableNames;
    for i = 1:length(walk_vars)
        fprintf('  %d: %s\n', i, walk_vars{i});
    end
else
    fprintf('Walking table is empty!\n');
end

% Process a sample STS cycle
if isfield(subject_data, 'Sts')
    sts_trial = subject_data.Sts.Sts_1.trial;
    
    % Test the STS processing function
    sts_table = process_single_sts_cycle(sts_trial, 25, 47, 'sit_to_stand', ...
        'SUB01', 'test_metadata', 70, 'Sts_1', 1);
    
    if ~isempty(sts_table)
        fprintf('\nSTS table has %d variables:\n', width(sts_table));
        sts_vars = sts_table.Properties.VariableNames;
        for i = 1:length(sts_vars)
            fprintf('  %d: %s\n', i, sts_vars{i});
        end
        
        % Show missing variables
        fprintf('\nVariables in walking but not in STS:\n');
        missing_in_sts = setdiff(walk_vars, sts_vars);
        for i = 1:length(missing_in_sts)
            fprintf('  %s\n', missing_in_sts{i});
        end
        
        fprintf('\nVariables in STS but not in walking:\n');
        missing_in_walk = setdiff(sts_vars, walk_vars);
        for i = 1:length(missing_in_walk)
            fprintf('  %s\n', missing_in_walk{i});
        end
    else
        fprintf('STS table is empty!\n');
    end
else
    fprintf('No STS data found!\n');
end