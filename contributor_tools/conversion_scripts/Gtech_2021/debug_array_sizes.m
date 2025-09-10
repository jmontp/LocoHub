% Debug script to identify where the array size duplication bug occurs
% This isolates the stride processing logic to identify the root cause

NUM_POINTS = 150;
fprintf('Debug: NUM_POINTS = %d\n', NUM_POINTS);

% Simulate loading one stride worth of data
% Load real data from existing test trial
try
    trial_data = load('CAMARGO_ET_AL_J_BIOMECH_DATASET/AB06/10_09_18/stair/gcRight/stair_2_l_01_01.mat');
    fprintf('Loaded heel strike data: %d points\n', length(trial_data.data.HeelStrike));
    
    % Show raw data characteristics
    heel_strike_pct = trial_data.data.HeelStrike;
    gc_time = trial_data.data.Header;
    
    % Find heel strikes (falling edges where percentage drops to 0)
    hs_indices = find(diff([100; heel_strike_pct]) < -50);  % Simple falling edge detection
    fprintf('Found %d heel strikes\n', length(hs_indices));
    
    if length(hs_indices) >= 2
        % Process first stride
        stride_start_idx = hs_indices(1);
        stride_end_idx = hs_indices(2) - 1;
        
        stride_pct = heel_strike_pct(stride_start_idx:stride_end_idx);
        stride_time = gc_time(stride_start_idx:stride_end_idx);
        
        fprintf('RAW stride data:\n');
        fprintf('  stride_pct length: %d points\n', length(stride_pct));
        fprintf('  stride_pct range: %.1f to %.1f\n', min(stride_pct), max(stride_pct));
        
        % Now create target arrays
        stride_start_time = stride_time(1);
        stride_end_time = stride_time(end);
        stride_duration_s = stride_end_time - stride_start_time;
        
        target_times = linspace(stride_start_time, stride_end_time, NUM_POINTS);
        target_pct = linspace(0, 100, NUM_POINTS)';
        
        fprintf('\nTarget arrays:\n');
        fprintf('  target_times length: %d points\n', length(target_times));
        fprintf('  target_pct length: %d points\n', length(target_pct));
        
        % Test interpolation - this should create 150-point output
        test_interp = interp1(stride_time, stride_pct, target_times, 'linear');
        fprintf('  Interpolated result length: %d points\n', length(test_interp));
        
        % Check if the issue is in the expand_table_for_parquet function
        % Simulate what happens when we store in table
        stride_data.phase_ipsi = target_pct;
        stride_data.test_var = test_interp';
        
        fprintf('\nStride struct arrays:\n');
        fprintf('  stride_data.phase_ipsi length: %d\n', length(stride_data.phase_ipsi));
        fprintf('  stride_data.test_var length: %d\n', length(stride_data.test_var));
        
        % Simulate table row creation (like in main script)
        row.phase_ipsi = {stride_data.phase_ipsi};
        row.test_var = {stride_data.test_var};
        compact_table = struct2table(row);
        
        fprintf('\nTable cell contents:\n');
        fprintf('  row.phase_ipsi{1} length: %d\n', length(row.phase_ipsi{1}));
        fprintf('  row.test_var{1} length: %d\n', length(row.test_var{1}));
        
        % Show what expand_table_for_parquet would see
        fprintf('\nWhat expand_table_for_parquet would see:\n');
        fprintf('  compact_table.phase_ipsi{1} length: %d\n', length(compact_table.phase_ipsi{1}));
        
        % If this is 150, the bug is somewhere else
        % If this is >150, we found the source
        
    else
        fprintf('Error: Not enough heel strikes found\n');
    end
    
catch ME
    fprintf('Error loading test data: %s\n', ME.message);
    fprintf('Make sure CAMARGO_ET_AL_J_BIOMECH_DATASET is in current directory\n');
end