% Simple debug to check what columns we have
clear; clc;

% Create a temporary test STS table
test_data.jointAngles.LHipAngles = [10, 5, 2; 15, 8, 3; 20, 10, 5]; % 3 frames, 3 planes
test_data.jointAngles.RHipAngles = [12, 4, 1; 18, 7, 2; 22, 9, 4];
test_data.jointAngles.LKneeAngles = [0, 0, 0; 10, 0, 0; 20, 0, 0];
test_data.jointAngles.RKneeAngles = [0, 0, 0; 12, 0, 0; 24, 0, 0];
test_data.jointAngles.LAnkleAngles = [0, 0, 0; -5, 0, 0; -10, 0, 0];
test_data.jointAngles.RAnkleAngles = [0, 0, 0; -6, 0, 0; -12, 0, 0];
test_data.jointAngles.LPelvisAngles = [5, 2, 1; 7, 3, 2; 9, 4, 3];

sts_table = process_single_sts_cycle(test_data, 1, 3, 'sit_to_stand', ...
    'SUB01', 'test_metadata', 70, 'Sts_1', 1);

if ~isempty(sts_table)
    fprintf('STS table created with %d variables:\n', width(sts_table));
    sts_vars = sts_table.Properties.VariableNames;
    for i = 1:length(sts_vars)
        fprintf('  %d: %s\n', i, sts_vars{i});
    end
else
    fprintf('STS table is empty!\n');
end

% Let's also check what a basic walking table looks like from the existing code
% by examining what variables are in the main process_strides_single_leg function
fprintf('\nTo find missing variables, check convert_umich_phase_to_parquet.m around line 500-950\n');
fprintf('Look for all stride_data.VARNAME assignments in process_strides_single_leg function\n');