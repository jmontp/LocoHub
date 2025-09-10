% Test actual stair processing with single trial
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
fprintf('Processing %s (STAIR PROCESSING TEST)\n', subject_id);
fprintf('========================================\n');

subject_data = streaming_data.Streaming.(subject_id);
subject_str = 'AB01';
subject_metadata = 'test_metadata';
body_mass = 70; % Test value

% Test processing one stair trial
if isfield(subject_data, 'Stair')
    fprintf('  Processing one stair trial...\n');
    stair_data = subject_data.Stair;
    
    % Test with s20dg_01 (20 degree ascent trial)
    trial_name = 's20dg_01';
    if isfield(stair_data, trial_name)
        trial_data = stair_data.(trial_name);
        
        % Extract metadata
        incline_str = 's20dg';
        trial_num = 1;
        
        % Determine task type (odd = ascent)
        task_type = 'stair_ascent';
        task_id = 'stair_ascent';
        height_m = 0.097; % 97mm riser
        incline_deg = 20;
        task_info = sprintf('height_m:%.3f,incline_deg:%d,steps:1', height_m, incline_deg);
        
        fprintf('    Processing %s: %s (%.0fmm riser, %d°)\n', trial_name, task_type, height_m*1000, incline_deg);
        fprintf('    Task info: %s\n', task_info);
        
        if isfield(trial_data, 'events')
            events = trial_data.events;
            
            try
                % Process using the existing function
                stride_table = process_strides_with_events(...
                    trial_data, events, subject_str, subject_metadata, body_mass, task_type, task_id, task_info);
                
                if ~isempty(stride_table)
                    fprintf('      SUCCESS: Generated stride table with %d rows (%d strides)\n', height(stride_table), height(stride_table)/150);
                    fprintf('      Stride table variables: %d\n', width(stride_table));
                    
                    % Check a few key variables
                    if any(strcmp(stride_table.Properties.VariableNames, 'knee_flexion_angle_ipsi_rad'))
                        fprintf('      Has kinematics: knee_flexion_angle_ipsi_rad\n');
                    end
                    if any(strcmp(stride_table.Properties.VariableNames, 'knee_flexion_moment_ipsi_Nm_kg'))
                        fprintf('      Has kinetics: knee_flexion_moment_ipsi_Nm_kg (should be NaN for stair)\n');
                        % Check if it's NaN as expected
                        moment_val = stride_table.knee_flexion_moment_ipsi_Nm_kg(1);
                        fprintf('      Sample moment value: %s\n', mat2str(moment_val));
                    end
                    
                    total_data = stride_table;
                else
                    fprintf('      ERROR: Empty stride table returned\n');
                end
                
            catch ME
                fprintf('      ERROR: %s\n', ME.message);
            end
        else
            fprintf('    ERROR: No events found\n');
        end
    else
        fprintf('  Trial %s not found\n', trial_name);
    end
else
    fprintf('  No Stair data found\n');
end

% Save results if successful
if ~isempty(total_data)
    output_path = 'test_stair_AB01.parquet';
    parquetwrite(output_path, total_data);
    fprintf('\nTEST SUCCESS: Saved to %s\n', output_path);
    fprintf('Total rows: %d\n', height(total_data));
    fprintf('Variables: %d\n', width(total_data));
else
    fprintf('\nTEST FAILED: No data to save\n');
end