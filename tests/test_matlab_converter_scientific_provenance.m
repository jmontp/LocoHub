function tests = test_matlab_converter_scientific_provenance
% Tiny analytic fixtures. No source datasets or complete conversion scripts run.
    tests = functiontests(localfunctions);
end

function setupOnce(testCase)
    root = fileparts(fileparts(mfilename('fullpath')));
    converters = fullfile(root, 'contributor_tools', 'conversion_scripts');
    helper_path = fullfile(converters, 'matlab_common');
    utility_path = fullfile(converters, 'Gtech_2021', 'utilities');
    addpath(helper_path, utility_path);
    temporary = tempname;
    mkdir(temporary);
    addpath(temporary);
    testCase.TestData.paths = {temporary, helper_path, utility_path};
    testCase.TestData.temporary = temporary;

    % Execute the actual local converter helpers without its full-dataset main.
    source = fileread(fullfile(converters, 'Gtech_2021', 'convert_gtech_2021_phase_to_parquet.m'));
    beginning = strfind(source, 'function [rows, unique_speeds] = process_treadmill');
    wrapper = sprintf(['function rows = fixture_gt21(trial)\n' ...
        'rows = extract_and_process_strides_single_leg(trial, 0, 2.1, ' ...
        '''GT21_AB06'', ''weight_kg:70'', ''level_walking'', ''level'', ' ...
        '''surface:overground'', 70, ''right'', ''levelground'');\n' ...
        'rows = expand_table_for_parquet(rows);\nend\n']);
    write_fixture(fullfile(temporary, 'fixture_gt21.m'), [wrapper source(beginning(1):end)]);

    source = fileread(fullfile(converters, 'Umich_2021', 'convert_umich_time_to_parquet.m'));
    beginning = strfind(source, 'function [subject_str, subject_metadata, body_mass] = get_subject_metadata');
    ending = strfind(source(beginning(1)+1:end), newline + "function ");
    local = source(beginning(1):beginning(1)+ending(1)-1);
    wrapper = sprintf(['function [metadata, mass] = fixture_um21(data)\n' ...
        '[~, metadata, mass] = get_subject_metadata(''AB01'', data);\nend\n']);
    write_fixture(fullfile(temporary, 'fixture_um21.m'), [wrapper local]);
end

function teardownOnce(testCase)
    clear fixture_gt21 fixture_um21
    rmpath(testCase.TestData.paths{:});
    rmdir(testCase.TestData.temporary, 's');
end

function write_fixture(path, source)
    handle = fopen(path, 'w');
    cleanup = onCleanup(@() fclose(handle));
    fprintf(handle, '%s', source);
end

function trial = synthetic_trial(recording)
    Header = (0:0.01:2.1)';
    HeelStrike = mod(round(Header * 100), 100);
    trial.gcLeft = table(Header, HeelStrike);
    trial.gcRight = table(Header, HeelStrike);
    hip_flexion_r = 2 * Header;
    hip_flexion_l = 3 * Header;
    trial.ik_offset = table(Header, hip_flexion_r, hip_flexion_l);
    trial.id = table(Header); % No joint moment measurements.
    trial.source_recording_id = recording;
end

function testMissingChannelsAndPhysicalDerivative(testCase)
    rows = fixture_gt21(synthetic_trial('gt21:AB06/session/levelground/trial_A.mat'));
    verifyGreaterThan(testCase, height(rows), 0);
    verifyTrue(testCase, all(isnan(rows.knee_flexion_moment_ipsi_Nm_kg)));
    verifyTrue(testCase, all(isnan(rows.ankle_dorsiflexion_angle_ipsi_rad)));
    verifyTrue(testCase, all(isnan(rows.trunk_sagittal_angle_rad)));
    verifyEqual(testCase, rows.hip_flexion_velocity_ipsi_rad_s, ...
        repmat(deg2rad(2), height(rows), 1), 'AbsTol', 1e-10);
    verifyEqual(testCase, rows.source_start_time_s(1), 0, 'AbsTol', 1e-12);
end

function testSourceIdentityDoesNotDependOnExportCounter(testCase)
    first = fixture_gt21(synthetic_trial('gt21:AB06/session/levelground/trial_A.mat'));
    again = fixture_gt21(synthetic_trial('gt21:AB06/session/levelground/trial_A.mat'));
    second = fixture_gt21(synthetic_trial('gt21:AB06/session/levelground/trial_B.mat'));
    verifyEqual(testCase, first.observation_id, again.observation_id);
    verifyNotEqual(testCase, first.observation_id{1}, second.observation_id{1});
    verifyEqual(testCase, first.step, first.observation_id);
    verifyEqual(testCase, jsondecode(first.task_info{1}).surface, 'overground');
end

function testUnknownAnthropometryIsNotInvented(testCase)
    [metadata, mass] = fixture_um21(struct());
    verifyTrue(testCase, isnan(mass));
    decoded = jsondecode(locohub_metadata_json(metadata));
    verifyTrue(testCase, isempty(decoded.weight_kg) || isnan(decoded.weight_kg));
    verifyTrue(testCase, isempty(decoded.height_m) || isnan(decoded.height_m));
end

function testMetadataTypesAndInvalidIdentity(testCase)
    decoded = jsondecode(locohub_metadata_json('treadmill:true,speed_m_s:1.2,weight_kg:unknown'));
    verifyTrue(testCase, decoded.treadmill);
    verifyEqual(testCase, decoded.speed_m_s, 1.2);
    verifyError(testCase, @() locohub_add_provenance(table(1), '', 'sample:1:2', ...
        'left', 'individual_cycle', 0, 1), 'LocoHub:Identity');
end
