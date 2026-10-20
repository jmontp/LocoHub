function convert_gtech_2023_time_to_parquet()
% CONVERT_GTECH_2023_TIME_TO_PARQUET  Time-indexed export for the Georgia Tech
% 2023 dataset (s41597-023-02840-6), aligned to the LocoHub standard.
%
% This is the time-indexed sibling of convert_gtech_phase_to_parquet.m. It
% deliberately reuses that script's dataset-specific conventions so the phase
% and time exports agree signal-for-signal:
%   * Joint angles/velocities/moments are read straight from the OpenSim IK/ID
%     CSVs (NOT reconstructed from a kinematic chain).
%   * deg -> rad for joint and segment angles; deg/s -> rad/s for velocities.
%   * Knee angle/velocity/moment negated. Ankle is NOT negated: the raw OpenSim
%     ankle_angle already follows the standard (ankle_dorsiflexion = foot - shank,
%     dorsiflexion positive), and the ankle moment is likewise already correct.
%     Hip untouched; pelvis transverse +pi/2 frame offset.
%   * Segment angles from Link_Angle.csv with Z=sagittal, X=frontal,
%     Y=transverse (rotm2eul(...,'YZX') convention).
%   * GRF axis map ForceX->anterior, ForceY_Vertical->vertical, ForceZ->lateral;
%     normalized by body weight (mass*9.81) -> _BW.
%   * Moments already Nm/kg from OpenSim -> rename only.
%   * CoP transformed into the local calcn (ankle) frame per sample; anterior =
%     local x, lateral = local z, vertical forced to 0.
%
% Unlike the phase export it does NOT normalize each cycle to 150 points. Each
% labeled sub-activity (a *_parsing.mat file) becomes one continuous, native-
% resolution time window with time_s reset to 0 and a single coarse `step` id.
% The reference (ipsi) leg is the leg whose heel strike leads the window; ipsi
% columns are sourced from that anatomical side.
%
% Configuration via environment variables:
%   GTECH2023_DATA_ROOT   Folder containing RawData/ and Segmentation/
%                         (default: current directory)
%   GTECH2023_SUBJECT     Process a single subject only, e.g. 'AB01' (optional)
%   LOCOHUB_PYTHON        Python interpreter with pyarrow for the shard merge
%
% Output: converted_datasets/gtech_2023_time.parquet (bounded-memory: one
% parquet shard per subject, streamed into the final file with 65,536-row
% groups by contributor_tools/common/merge_parquet_shards.py).

    script_dir = fileparts(mfilename('fullpath'));
    addpath(script_dir);  % for parse_gtech_activity_matlab
    addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'matlab_common'));

    data_root = getenv('GTECH2023_DATA_ROOT');
    if isempty(data_root)
        data_root = '.';
    end

    raw_root = fullfile(data_root, 'RawData');
    segmentation_root = fullfile(data_root, 'Segmentation');
    if ~isfolder(segmentation_root)
        error('Segmentation directory not found: %s', segmentation_root);
    end

    % Resolve output path relative to the repo (three levels up from this file:
    % conversion_scripts/Gtech_2023 -> conversion_scripts -> contributor_tools).
    repo_root = fileparts(fileparts(fileparts(script_dir)));
    output_dir = fullfile(repo_root, 'converted_datasets');
    if ~isfolder(output_dir)
        mkdir(output_dir);
    end
    output_path = fullfile(output_dir, 'gtech_2023_time.parquet');
    merger_script = fullfile(repo_root, 'contributor_tools', 'common', 'merge_parquet_shards.py');

    % Subject mass table (unknown mass leaves normalized GRF unavailable).
    default_mass_kg = NaN;
    mass_table = load_subject_masses(fullfile(raw_root, 'Subject_masses.csv'));

    % Subject list.
    single_subject = getenv('GTECH2023_SUBJECT');
    if ~isempty(single_subject)
        subjects = {single_subject};
    else
        entries = dir(segmentation_root);
        subjects = {};
        for k = 1:numel(entries)
            name = entries(k).name;
            if entries(k).isdir && ~isempty(regexp(name, '^AB\d+$', 'once'))
                subjects{end+1} = name; %#ok<AGROW>
            end
        end
        subjects = sort(subjects);
    end
    if isempty(subjects)
        error('No AB## subjects found in %s', segmentation_root);
    end

    % Sharded output setup.
    shard_dir = tempname(output_dir);
    mkdir(shard_dir);
    shard_counter = 0;
    total_rows = 0;
    step_counter = 1;

    fprintf('Converting GTech 2023 time-indexed data (%d subjects)\n', numel(subjects));

    for s = 1:numel(subjects)
        subject = subjects{s};
        fprintf('\n=== Subject %s (%d/%d) ===\n', subject, s, numel(subjects));

        subject_mass_kg = default_mass_kg;
        if ~isempty(mass_table) && isKey(mass_table, subject)
            subject_mass_kg = mass_table(subject);
        else
            warning('Mass not found for %s; normalized GRF will be unavailable.', subject);
        end
        if ~isscalar(subject_mass_kg) || ~isfinite(subject_mass_kg) || subject_mass_kg <= 0
            subject_mass_kg = NaN;
        end
        weight_N = subject_mass_kg * 9.81;
        subject_id = ['GT23_' subject];
        subject_metadata = sprintf('weight_kg:%.2f', subject_mass_kg);

        seg_dir = fullfile(segmentation_root, subject);
        raw_dir = fullfile(raw_root, subject);
        parsing_files = dir(fullfile(seg_dir, '*_parsing.mat'));
        if isempty(parsing_files)
            warning('No *_parsing.mat for %s; skipping.', subject);
            continue;
        end

        subject_rows = table();
        cached_folder = '';
        cached = struct();

        for a = 1:numel(parsing_files)
            parsing_name = parsing_files(a).name;
            [activity_name, sub_activity_name, raw_folder] = ...
                derive_activity(parsing_name);
            if isempty(raw_folder)
                continue;
            end

            % Window + reference leg from the parsing intervals.
            parsing_path = fullfile(seg_dir, parsing_name);
            [t0, t1, reference_leg] = window_from_parsing(parsing_path);
            if isnan(t0)
                fprintf('  %-42s no usable intervals; skip\n', parsing_name);
                continue;
            end

            % Load (and cache) the raw CSV folder for this window.
            activity_dir = fullfile(raw_dir, 'CSV_Data', raw_folder);
            if ~isfolder(activity_dir)
                warning('Raw folder not found: %s; skip %s', activity_dir, parsing_name);
                continue;
            end
            if ~strcmp(cached_folder, raw_folder)
                cached = load_activity_csvs(activity_dir, ...
                    fullfile(raw_dir, 'Transforms', [raw_folder '.mat']));
                cached_folder = raw_folder;
            end
            if isempty(cached.time)
                warning('No master time for %s; skip %s', raw_folder, parsing_name);
                continue;
            end

            [task_name, task_id, task_info] = ...
                parse_gtech_activity_matlab(activity_name, sub_activity_name);

            rows = build_time_window( ...
                cached, t0, t1, reference_leg, weight_N);
            if isempty(rows) || height(rows) < 2
                fprintf('  %-42s window empty; skip\n', parsing_name);
                continue;
            end

            n = height(rows);
            rows.subject          = repmat(string(subject_id), n, 1);
            rows.subject_metadata = repmat(string(subject_metadata), n, 1);
            rows.task             = repmat(string(task_name), n, 1);
            rows.task_id          = repmat(string(task_id), n, 1);
            rows.task_info        = repmat(string(task_info), n, 1);
            rows.step             = repmat(step_counter, n, 1);
            rows.assistance_active = false(n, 1);
            rows.reference_leg    = repmat(string(reference_leg), n, 1);
            rows.time_scope       = repmat("continuous_trial", n, 1);
            rows.time_reset_per   = repmat("segment", n, 1);
            source_id = sprintf('gt23:%s/%s', subject, raw_folder);
            rows = locohub_add_provenance(rows, source_id, ...
                sprintf('window:%.17g:%.17g', t0, t1), reference_leg, ...
                'continuous_recording', t0, t1);
            rows.step = rows.observation_id;


            subject_rows = append_rows(subject_rows, rows);
            step_counter = step_counter + 1;
            fprintf('  %-42s %-16s step=%d rows=%d\n', ...
                parsing_name, task_name, step_counter - 1, n);
        end

        if ~isempty(subject_rows)
            [shard_counter, total_rows] = write_table_shard( ...
                subject_rows, shard_dir, shard_counter, total_rows);
        end
        clear subject_rows cached
        cached_folder = '';
    end

    fprintf('\nMerging %d shards (%d rows) -> %s\n', shard_counter, total_rows, output_path);
    if shard_counter == 0
        error('No data produced; nothing to merge.');
    end
    merge_parquet_shards(merger_script, shard_dir, output_path);
    rmdir(shard_dir, 's');
    fprintf('Done: %s (%d rows)\n', output_path, total_rows);
end


% =====================================================================
function [activity_name, sub_activity_name, raw_folder] = derive_activity(parsing_name)
% Port of the phase converter's raw_activity_name derivation.
    activity_name = '';
    sub_activity_name = '';
    raw_folder = '';

    [~, base] = fileparts(parsing_name);
    base = strrep(base, '_parsing', '');
    parts = strsplit(base, '_');
    is_num = ~isnan(str2double(parts));
    first_num_idx = find(is_num, 1);

    if isempty(first_num_idx) || first_num_idx == 1
        if isempty(parts)
            return;
        end
        activity_name = parts{1};
        activity_number = 1;
        sub_activity_name = strjoin(parts(2:end), '_');
        if strcmp(activity_name, 'step_ups')
            raw_folder = 'step_ups';
        else
            raw_folder = activity_name;
        end
    else
        activity_name = strjoin(parts(1:first_num_idx-1), '_');
        activity_number = str2double(parts{first_num_idx});
        sub_activity_name = strjoin(parts(first_num_idx+1:end), '_');
        raw_folder = [activity_name '_' int2str(activity_number)];
    end

    % Special cases: the raw CSV folder embeds an extra index for stairs/jump.
    if strcmp(activity_name, 'stairs') && ~isempty(sub_activity_name)
        stair_num = str2double(sub_activity_name(1:min(2, numel(sub_activity_name))));
        if isnan(stair_num)
            stair_num = str2double(sub_activity_name(1));
        end
        if ~isnan(stair_num)
            raw_folder = [activity_name '_' int2str(activity_number) '_' num2str(stair_num)];
        end
    elseif strcmp(activity_name, 'jump') && activity_number == 1 && ...
            ~isempty(sub_activity_name) && ~isnan(str2double(sub_activity_name(1)))
        raw_folder = [activity_name '_' int2str(activity_number) '_' sub_activity_name(1)];
    end
end


% =====================================================================
function [t0, t1, reference_leg] = window_from_parsing(parsing_path)
% Envelope [min start, max end] over every Nx2 interval field in the parsing
% file. reference_leg = anatomical side whose first heel strike leads (falls
% back to 'right').
    t0 = NaN; t1 = NaN; reference_leg = 'right';
    try
        pdata = load(parsing_path);
    catch
        return;
    end
    fields = fieldnames(pdata);
    starts = []; ends = [];
    left_first = Inf; right_first = Inf;
    for i = 1:numel(fields)
        v = pdata.(fields{i});
        if isnumeric(v) && ~isempty(v) && size(v, 2) == 2
            fs = v(:, 1); fe = v(:, 2);
            starts = [starts; fs]; %#ok<AGROW>
            ends = [ends; fe]; %#ok<AGROW>
            fname = lower(fields{i});
            if startsWith(fname, 'left')
                left_first = min(left_first, min(fs));
            elseif startsWith(fname, 'right')
                right_first = min(right_first, min(fs));
            end
        end
    end
    if isempty(starts)
        return;
    end
    t0 = min(starts);
    t1 = max(ends);
    if isfinite(left_first) && left_first < right_first
        reference_leg = 'left';
    else
        reference_leg = 'right';  % right leads, ties, or only sit/stand fields
    end
end


% =====================================================================
function cached = load_activity_csvs(activity_dir, transform_path)
% Load the raw CSV tables and the CoP transforms once per activity folder.
    cached = struct('time', [], 'angle', [], 'velocity', [], 'moment', [], ...
        'link', [], 'grf', [], 'grf_time', [], ...
        'trans_time', [], 'R_l', [], 'Tr_l', [], 'R_r', [], 'Tr_r', [], ...
        'has_transforms', false);

    angle = read_csv(fullfile(activity_dir, 'Joint_Angle.csv'));
    if isempty(angle)
        return;  % joint angles are the master grid; without them, skip folder
    end
    cached.angle = angle;
    cached.time = angle.time;
    cached.velocity = read_csv(fullfile(activity_dir, 'Joint_Velocities.csv'));
    cached.moment = read_csv(fullfile(activity_dir, 'Joint_Moments.csv'));
    cached.link = read_csv(fullfile(activity_dir, 'Link_Angle.csv'));
    grf = read_csv(fullfile(activity_dir, 'GroundFrame_GRFs.csv'));
    cached.grf = grf;
    if ~isempty(grf)
        cached.grf_time = grf.time;
    end

    % CoP transforms (calcn_l / calcn_r 4x4 per Header timestamp).
    if isfile(transform_path)
        try
            tdat = load(transform_path);
            if isfield(tdat, 'Transforms') && istable(tdat.Transforms)
                T = tdat.Transforms;
                vn = T.Properties.VariableNames;
                if all(ismember({'Header', 'calcn_l', 'calcn_r'}, vn))
                    cached.trans_time = T.Header(:);
                    [cached.R_l, cached.Tr_l] = stack_transforms(T.calcn_l);
                    [cached.R_r, cached.Tr_r] = stack_transforms(T.calcn_r);
                    cached.has_transforms = true;
                end
            end
        catch ME
            warning('Failed to load transforms %s: %s', transform_path, ME.message);
        end
    end
end


function [R, Tr] = stack_transforms(col)
% Convert a column of 4x4 homogeneous transforms into 3x3xN rotations and
% 3xN translations. Invalid cells become NaN.
    n = numel(col);
    R = nan(3, 3, n);
    Tr = nan(3, n);
    for i = 1:n
        M = col{i};
        if isnumeric(M) && isequal(size(M), [4, 4])
            R(:, :, i) = M(1:3, 1:3);
            Tr(:, i) = M(1:3, 4);
        end
    end
end


function tbl = read_csv(path)
    tbl = [];
    if isfile(path)
        try
            tbl = readtable(path, 'VariableNamingRule', 'preserve');
        catch
            tbl = [];
        end
    end
end


% =====================================================================
function rows = build_time_window(cached, t0, t1, reference_leg, weight_N)
% Build a native-resolution, continuous time table for [t0, t1] with all
% standardized columns. ipsi = reference_leg.
    rows = table();
    master = cached.time;
    mask = master >= t0 & master <= t1;
    tw = master(mask);
    if numel(tw) < 2
        return;
    end
    time_s = tw - tw(1);
    n = numel(time_s);
    deg2rad = pi / 180;

    if strcmp(reference_leg, 'left')
        ipsi = 'l'; contra = 'r';
    else
        ipsi = 'r'; contra = 'l';
    end

    rows.time_s = time_s;
    dt_med = median(diff(tw));
    rows.sampling_rate_hz = repmat(round(1 / dt_med), n, 1);

    % ---- Joint angles (deg -> rad, with sign conventions) ----
    % hip_flexion: as-is; knee (knee_angle): negate; ankle (ankle_angle): as-is
    % (raw ankle already follows ankle_dorsiflexion = foot - shank, dorsiflexion +)
    rows.hip_flexion_angle_ipsi_rad   = sig(cached.angle, ['hip_flexion_' ipsi], tw) * deg2rad;
    rows.hip_flexion_angle_contra_rad = sig(cached.angle, ['hip_flexion_' contra], tw) * deg2rad;
    rows.knee_flexion_angle_ipsi_rad   = -sig(cached.angle, ['knee_angle_' ipsi], tw) * deg2rad;
    rows.knee_flexion_angle_contra_rad = -sig(cached.angle, ['knee_angle_' contra], tw) * deg2rad;
    rows.ankle_dorsiflexion_angle_ipsi_rad   = sig(cached.angle, ['ankle_angle_' ipsi], tw) * deg2rad;
    rows.ankle_dorsiflexion_angle_contra_rad = sig(cached.angle, ['ankle_angle_' contra], tw) * deg2rad;

    % ---- Joint velocities (deg/s -> rad/s, knee negated; ankle as-is) ----
    rows.hip_flexion_velocity_ipsi_rad_s   = sig(cached.velocity, ['hip_flexion_velocity_' ipsi], tw) * deg2rad;
    rows.hip_flexion_velocity_contra_rad_s = sig(cached.velocity, ['hip_flexion_velocity_' contra], tw) * deg2rad;
    rows.knee_flexion_velocity_ipsi_rad_s   = -sig(cached.velocity, ['knee_velocity_' ipsi], tw) * deg2rad;
    rows.knee_flexion_velocity_contra_rad_s = -sig(cached.velocity, ['knee_velocity_' contra], tw) * deg2rad;
    rows.ankle_dorsiflexion_velocity_ipsi_rad_s   = sig(cached.velocity, ['ankle_velocity_' ipsi], tw) * deg2rad;
    rows.ankle_dorsiflexion_velocity_contra_rad_s = sig(cached.velocity, ['ankle_velocity_' contra], tw) * deg2rad;

    % ---- Joint moments (already Nm/kg; knee negated, ankle NOT) ----
    rows.hip_flexion_moment_ipsi_Nm_kg   = sig(cached.moment, ['hip_flexion_' ipsi '_moment'], tw);
    rows.hip_flexion_moment_contra_Nm_kg = sig(cached.moment, ['hip_flexion_' contra '_moment'], tw);
    rows.knee_flexion_moment_ipsi_Nm_kg   = -sig(cached.moment, ['knee_angle_' ipsi '_moment'], tw);
    rows.knee_flexion_moment_contra_Nm_kg = -sig(cached.moment, ['knee_angle_' contra '_moment'], tw);
    rows.ankle_dorsiflexion_moment_ipsi_Nm_kg   = sig(cached.moment, ['ankle_angle_' ipsi '_moment'], tw);
    rows.ankle_dorsiflexion_moment_contra_Nm_kg = sig(cached.moment, ['ankle_angle_' contra '_moment'], tw);

    % ---- Segment angles from Link_Angle (Z=sag, X=front, Y=trans), deg->rad ----
    rows.pelvis_sagittal_angle_rad   = sig(cached.link, 'pelvis_Z', tw) * deg2rad;
    rows.pelvis_frontal_angle_rad    = sig(cached.link, 'pelvis_X', tw) * deg2rad;
    rows.pelvis_transverse_angle_rad = sig(cached.link, 'pelvis_Y', tw) * deg2rad + pi/2;

    rows = add_segment(rows, cached.link, 'thigh', 'femur', ipsi, contra, tw, deg2rad);
    rows = add_segment(rows, cached.link, 'shank', 'tibia', ipsi, contra, tw, deg2rad);
    rows = add_segment(rows, cached.link, 'foot',  'calcn', ipsi, contra, tw, deg2rad);

    % ---- GRF (axis remap + body-weight normalization) ----
    grf = cached.grf;
    if ~isempty(grf)
        gmask = cached.grf_time >= t0 & cached.grf_time <= t1;
        gt = cached.grf_time(gmask);
    else
        gt = [];
    end
    IU = upper(ipsi); CU = upper(contra);
    rows.grf_anterior_ipsi_BW   = grf_norm(grf, [IU 'ForceX'], gt, tw, weight_N);
    rows.grf_vertical_ipsi_BW   = grf_norm(grf, [IU 'ForceY_Vertical'], gt, tw, weight_N);
    rows.grf_lateral_ipsi_BW    = grf_norm(grf, [IU 'ForceZ'], gt, tw, weight_N);
    rows.grf_anterior_contra_BW = grf_norm(grf, [CU 'ForceX'], gt, tw, weight_N);
    rows.grf_vertical_contra_BW = grf_norm(grf, [CU 'ForceY_Vertical'], gt, tw, weight_N);
    rows.grf_lateral_contra_BW  = grf_norm(grf, [CU 'ForceZ'], gt, tw, weight_N);

    % ---- CoP in local calcn (ankle) frame ----
    [cop_a_i, cop_l_i] = cop_local(cached, grf, gt, tw, ipsi, t0, t1);
    [cop_a_c, cop_l_c] = cop_local(cached, grf, gt, tw, contra, t0, t1);
    cop_v_i = zeros(n, 1);
    cop_v_c = zeros(n, 1);

    % Mask CoP as missing whenever the limb is unloaded (vertical GRF below
    % 0.2 BW) OR the transformed CoP is non-physical for the ankle frame
    % (> 0.5 m from the ankle). Off-contact force-plate CoP is meaningless, and
    % contact-onset/force-plate-boundary transients otherwise leave CoP samples
    % half a metre or more from the ankle. Mirrors the levelground masking added
    % for the GTech 2021 time export.
    cop_phys_max = 0.5;
    mask_ipsi = ~(rows.grf_vertical_ipsi_BW >= 0.2) | ...
        abs(cop_a_i) > cop_phys_max | abs(cop_l_i) > cop_phys_max;
    mask_contra = ~(rows.grf_vertical_contra_BW >= 0.2) | ...
        abs(cop_a_c) > cop_phys_max | abs(cop_l_c) > cop_phys_max;
    cop_a_i(mask_ipsi) = NaN;  cop_l_i(mask_ipsi) = NaN;  cop_v_i(mask_ipsi) = NaN;
    cop_a_c(mask_contra) = NaN; cop_l_c(mask_contra) = NaN; cop_v_c(mask_contra) = NaN;

    rows.cop_anterior_ipsi_m   = cop_a_i;
    rows.cop_lateral_ipsi_m    = cop_l_i;
    rows.cop_vertical_ipsi_m   = cop_v_i;
    rows.cop_anterior_contra_m = cop_a_c;
    rows.cop_lateral_contra_m  = cop_l_c;
    rows.cop_vertical_contra_m = cop_v_c;
end


function rows = add_segment(rows, link, seg, raw, ipsi, contra, tw, deg2rad)
    rows.([seg '_sagittal_angle_ipsi_rad'])    = sig(link, [raw '_' ipsi '_Z'], tw) * deg2rad;
    rows.([seg '_sagittal_angle_contra_rad'])  = sig(link, [raw '_' contra '_Z'], tw) * deg2rad;
    rows.([seg '_frontal_angle_ipsi_rad'])     = sig(link, [raw '_' ipsi '_X'], tw) * deg2rad;
    rows.([seg '_frontal_angle_contra_rad'])   = sig(link, [raw '_' contra '_X'], tw) * deg2rad;
    rows.([seg '_transverse_angle_ipsi_rad'])  = sig(link, [raw '_' ipsi '_Y'], tw) * deg2rad;
    rows.([seg '_transverse_angle_contra_rad']) = sig(link, [raw '_' contra '_Y'], tw) * deg2rad;
end


function out = sig(tbl, colname, target_time)
% Linear interpolation of a named column onto target_time; NaN if missing.
    n = numel(target_time);
    if isempty(tbl) || ~ismember(colname, tbl.Properties.VariableNames)
        out = nan(n, 1);
        return;
    end
    src_t = tbl.time;
    src_v = tbl.(colname);
    out = interp1(src_t, src_v, target_time, 'linear', NaN);
    out = out(:);
end


function out = grf_norm(grf, colname, grf_time, target_time, weight_N)
    n = numel(target_time);
    if isempty(grf) || isempty(grf_time) || ~ismember(colname, grf.Properties.VariableNames)
        out = nan(n, 1);
        return;
    end
    gmask = grf.time >= grf_time(1) & grf.time <= grf_time(end);
    src_t = grf.time(gmask);
    src_v = grf.(colname)(gmask);
    out = interp1(src_t, src_v, target_time, 'linear', NaN) / weight_N;
    out = out(:);
end


function [cop_ant, cop_lat] = cop_local(cached, grf, grf_time, target_time, leg, t0, t1)
% Transform CoP into the local calcn frame for one leg, then interpolate onto
% target_time. Returns NaN columns when transforms or raw CoP are unavailable.
    n = numel(target_time);
    cop_ant = nan(n, 1);
    cop_lat = nan(n, 1);
    LU = upper(leg);
    copx_name = [LU 'COPX'];
    copz_name = [LU 'COPZ'];
    if isempty(grf) || isempty(grf_time) || ~cached.has_transforms
        return;
    end
    if ~all(ismember({copx_name, copz_name}, grf.Properties.VariableNames))
        return;
    end

    gmask = grf.time >= t0 & grf.time <= t1;
    gt = grf.time(gmask);
    copx = grf.(copx_name)(gmask);
    copz = grf.(copz_name)(gmask);
    if numel(gt) < 2
        return;
    end

    if strcmp(leg, 'l')
        R = cached.R_l; Tr = cached.Tr_l;
    else
        R = cached.R_r; Tr = cached.Tr_r;
    end
    trans_time = cached.trans_time;
    Nt = numel(trans_time);
    if Nt < 1
        return;
    end

    % Nearest transform per GRF sample.
    nn = interp1(trans_time, 1:Nt, gt, 'nearest', 'extrap');
    nn = max(1, min(Nt, round(nn)));

    cop_global = [copx.'; zeros(1, numel(copx)); copz.'];  % 3 x Ng
    Rn = R(:, :, nn);           % 3 x 3 x Ng
    Trn = Tr(:, nn);            % 3 x Ng
    rel = cop_global - Trn;     % 3 x Ng
    % local = R' * rel, per page.
    local = pagemtimes(permute(Rn, [2 1 3]), reshape(rel, 3, 1, []));
    local = reshape(local, 3, []);  % 3 x Ng

    local_x = local(1, :).';
    local_z = local(3, :).';
    % Interpolate onto the kinematic target grid.
    cop_ant = interp1(gt, local_x, target_time, 'linear', NaN);
    cop_lat = interp1(gt, local_z, target_time, 'linear', NaN);
    cop_ant = cop_ant(:);
    cop_lat = cop_lat(:);
end


% =====================================================================
function combined = append_rows(combined, rows)
% Vertically concatenate, NaN/<missing>-padding any column set differences.
    if isempty(combined)
        combined = rows;
        return;
    end
    missing_in_combined = setdiff(rows.Properties.VariableNames, combined.Properties.VariableNames);
    for i = 1:numel(missing_in_combined)
        combined.(missing_in_combined{i}) = default_column(combined.(rows.Properties.VariableNames{1}), height(combined), rows.(missing_in_combined{i}));
    end
    missing_in_rows = setdiff(combined.Properties.VariableNames, rows.Properties.VariableNames);
    for i = 1:numel(missing_in_rows)
        rows.(missing_in_rows{i}) = default_column([], height(rows), combined.(missing_in_rows{i}));
    end
    rows = rows(:, combined.Properties.VariableNames);
    combined = [combined; rows];
end


function col = default_column(~, n, template)
    if isstring(template) || iscellstr(template)
        col = repmat("", n, 1);
    elseif islogical(template)
        col = false(n, 1);
    else
        col = nan(n, 1);
    end
end


function mass_table = load_subject_masses(path)
    mass_table = containers.Map('KeyType', 'char', 'ValueType', 'double');
    if ~isfile(path)
        return;
    end
    try
        T = readtable(path, 'CommentStyle', '#', 'VariableNamingRule', 'preserve');
    catch
        return;
    end
    vn = T.Properties.VariableNames;
    if ~all(ismember({'subject_id', 'mass_kg'}, vn))
        return;
    end
    for i = 1:height(T)
        sid = T.subject_id{i};
        if ~ischar(sid) && ~isstring(sid)
            continue;
        end
        mass_table(char(sid)) = T.mass_kg(i);
    end
end


% =====================================================================
function [shard_counter, total_rows] = write_table_shard(rows, shard_dir, shard_counter, total_rows)
    if isempty(rows)
        return;
    end
    shard_counter = shard_counter + 1;
    shard_path = fullfile(shard_dir, sprintf('%05d.parquet', shard_counter));
    parquetwrite(shard_path, rows);
    total_rows = total_rows + height(rows);
end


function merge_parquet_shards(merger_script, shard_dir, output_path)
    python_executable = getenv('LOCOHUB_PYTHON');
    if isempty(python_executable)
        if ispc
            python_executable = 'wsl.exe python3';
        else
            python_executable = 'python3';
        end
    end
    if startsWith(python_executable, 'wsl.exe')
        % wsl.exe python3 runs inside WSL and needs POSIX paths, so translate
        % Windows drive paths (S:\a\b or S:/a/b) to /mnt/s/a/b.
        merger_script = win2wsl(merger_script);
        shard_dir = win2wsl(shard_dir);
        output_path = win2wsl(output_path);
    end
    command = sprintf('%s "%s" "%s" "%s" --row-group-size 65536', ...
        python_executable, merger_script, shard_dir, output_path);
    status = system(command);
    if status ~= 0
        error('Shard merge failed. Recoverable shards remain in %s.', shard_dir);
    end
end


function p = win2wsl(p)
    p = strrep(p, '\', '/');
    if numel(p) >= 2 && p(2) == ':'
        drive = lower(p(1));
        p = ['/mnt/' drive p(3:end)];
    end
end
