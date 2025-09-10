% Test conversion with single subject to check for completion
clear; clc;

% Set global flag for data fixes
global ENABLE_DATA_FIXES;
ENABLE_DATA_FIXES = true;

% Load data
fprintf('Loading Streaming.mat...\n');
streaming_data = load('Streaming.mat');

% Initialize output
total_data = table;

% Test with just AB01
subject_id = 'AB01';
fprintf('\n========================================\n');
fprintf('Processing %s (TEST)\n', subject_id);
fprintf('========================================\n');

subject_data = streaming_data.Streaming.(subject_id);

% Process STS only for quick test
if isfield(subject_data, 'Sts')
    fprintf('  Processing sit-to-stand trials...\n');
    
    % Load normalized data for cut points
    normalized_file = 'Normalized.mat';
    if exist(normalized_file, 'file')
        normalized_data = load(normalized_file);
        fprintf('    Found Normalized.mat data for %s\n', subject_id);
        
        % Process STS with normalized cut points
        stride_table = process_sts_cycles_with_normalized(...
            subject_data.Sts, normalized_data.Normalized.(subject_id), subject_id, 'test_metadata', 70);
        
        if ~isempty(stride_table)
            fprintf('      Added %d total STS cycles\n', height(stride_table)/150);
            total_data = stride_table;
        end
    else
        fprintf('    Warning: No Normalized.mat file found for %s\n', subject_id);
    end
else
    fprintf('  No STS data found for %s\n', subject_id);
end

% Save results
if ~isempty(total_data)
    output_path = sprintf('test_%s_phase.parquet', subject_id);
    parquetwrite(output_path, total_data);
    fprintf('Test conversion saved to %s\n', output_path);
    fprintf('Total rows: %d\n', height(total_data));
    fprintf('Variables: %d\n', width(total_data));
else
    fprintf('No data to save\n');
end