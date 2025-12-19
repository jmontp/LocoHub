% Run a small battery of raw vs parquet torque checks for Gtech 2021.
% Uses validate_raw_vs_parquet.m as the core engine and overrides its
% configuration via base workspace variables.
%
% Cases (all for AB06):
%   1) Treadmill level walking, 0.50 m/s
%   2) Ramp incline_walking (all inclines)
%   3) Stair ascent, 7-inch steps (step_height_m:0.178)

function validate_gtech_torque_suite()
SCRIPT_DIR = fileparts(mfilename('fullpath'));
cd(SCRIPT_DIR);

PARQUET_PATH = fullfile(SCRIPT_DIR, '..', '..', '..', ...
    'converted_datasets', 'gtech_2021_phase_test.parquet');

cases = {};

% Case 1: Treadmill level walking, 0.50 m/s
c1 = struct();
c1.name            = 'AB06 treadmill 0.50 m/s';
c1.SUBJECT_CODE    = 'AB06';
c1.DATE_FOLDER     = '10_09_18';
c1.MODE            = 'treadmill';
c1.TRIAL_NAME      = 'treadmill_01_01.mat';
c1.LEG_OVERRIDE    = '';
c1.TASK_FILTER     = 'level_walking';
c1.TASK_INFO_FILTER = 'speed_m_s:0.50';
c1.TORQUE_TOLERANCE = 0.05;
cases{end+1} = c1;

% Case 2: Ramp incline walking (all inclines)
c2 = struct();
c2.name            = 'AB06 ramp incline_walking (all inclines)';
c2.SUBJECT_CODE    = 'AB06';
c2.DATE_FOLDER     = '10_09_18';
c2.MODE            = 'ramp';
c2.TRIAL_NAME      = 'ramp_3_l_01_01.mat';
c2.LEG_OVERRIDE    = '';
c2.TASK_FILTER     = 'incline_walking';
c2.TASK_INFO_FILTER = '';
c2.TORQUE_TOLERANCE = 0.10;
cases{end+1} = c2;

% Case 3: Stair ascent, 7-inch steps (step_height_m:0.178)
c3 = struct();
c3.name            = 'AB06 stair_ascent (7-inch)';
c3.SUBJECT_CODE    = 'AB06';
c3.DATE_FOLDER     = '10_09_18';
c3.MODE            = 'stair';
c3.TRIAL_NAME      = 'stair_2_l_01_01.mat';
c3.LEG_OVERRIDE    = '';
c3.TASK_FILTER     = 'stair_ascent';
c3.TASK_INFO_FILTER = 'step_height_m:0.178';
c3.TORQUE_TOLERANCE = 0.10;
cases{end+1} = c3;

all_ok = true;
for k = 1:numel(cases)
    cfg = cases{k};
    fprintf('\n=== Case %d/%d: %s ===\n', k, numel(cases), cfg.name);

    % Push configuration into base workspace for validate_raw_vs_parquet.m
    assignin('base', 'PARQUET_PATH', PARQUET_PATH);
    assignin('base', 'SUBJECT_CODE', cfg.SUBJECT_CODE);
    assignin('base', 'DATE_FOLDER',  cfg.DATE_FOLDER);
    assignin('base', 'MODE',         cfg.MODE);
    assignin('base', 'TRIAL_NAME',   cfg.TRIAL_NAME);
    assignin('base', 'LEG_OVERRIDE', cfg.LEG_OVERRIDE);
    assignin('base', 'TASK_FILTER',  cfg.TASK_FILTER);
    assignin('base', 'TASK_INFO_FILTER', cfg.TASK_INFO_FILTER);
    assignin('base', 'TORQUE_TOLERANCE', cfg.TORQUE_TOLERANCE);

    try
        evalin('base', 'validate_raw_vs_parquet');
    catch ME
        all_ok = false;
        fprintf('  ERROR in case \"%s\": %s\n', cfg.name, ME.message);
    end
end

if ~all_ok
    error('One or more torque validation cases failed.');
else
    fprintf('\nAll torque validation cases passed.\n');
end
end
