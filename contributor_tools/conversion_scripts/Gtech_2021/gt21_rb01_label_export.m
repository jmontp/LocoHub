function gt21_rb01_label_export(source_root, out_dir, subject, nonce)
% GT21-RB01 label and subject export for ONE participant. DRAFT: not run; waits for the native-launcher review.
% Reads only: <source_root>/SubjectInfo.mat and <source_root>/<subject>/<session>/<mode>/conditions/*.mat.
% Writes only (exclusively, never overwriting) into out_dir: labels_<subject>.jsonl and subject_info_<subject>.json.
% Nothing is converted, filtered, relabelled or inferred. Missing items are written as null, never filled.
% nonce is only echoed so the launcher can find this MATLAB process in the Windows process list.
    if nargin ~= 4
        error('gt21_rb01_label_export:args', 'source_root, out_dir, subject, nonce required');
    end
    if isempty(regexp(subject, '^AB\d\d$', 'once'))
        error('gt21_rb01_label_export:subject', 'subject must look like AB06');
    end
    fprintf('gt21_rb01 nonce=%s subject=%s\n', nonce, subject);
    modes = {'levelground', 'ramp', 'stair', 'treadmill'};
    if ~isfolder(out_dir)
        error('gt21_rb01_label_export:out', 'out_dir must already exist (created by the runner)');
    end

    % ---- subject row (all columns, units as stored; no unit is inferred) ----
    info = load(fullfile(source_root, 'SubjectInfo.mat'));
    names = fieldnames(info);
    tbl = info.(names{1});
    if ~istable(tbl)
        error('gt21_rb01_label_export:info', 'SubjectInfo.mat does not hold a table');
    end
    row = find(strcmp(string(tbl.Subject), subject));
    result = struct('subject', subject, 'rows_matching', numel(row), ...
        'variable_names', {tbl.Properties.VariableNames}, ...
        'variable_units', {tbl.Properties.VariableUnits}, 'values', struct());
    if numel(row) == 1
        for v = 1:numel(tbl.Properties.VariableNames)
            name = tbl.Properties.VariableNames{v};
            cell_value = tbl.(name)(row);
            if iscell(cell_value), cell_value = cell_value{1}; end
            result.values.(name) = cell_value;
        end
        % literal text of Weight as MATLAB prints it, to compare with the 22 literals already read
        result.weight_literal_g17 = sprintf('%.17g', double(tbl.Weight(row)));
        result.weight_literal_short = num2str(tbl.Weight(row));
    end
    write_text(fullfile(out_dir, ['subject_info_' subject '.json']), jsonencode(result));

    % ---- one JSON line per recording (conditions file) ----
    sessions = dir(fullfile(source_root, subject));
    sessions = sessions([sessions.isdir] & ~startsWith({sessions.name}, '.') & ~strcmp({sessions.name}, 'osimxml'));
    fid = fopen(fullfile(out_dir, ['labels_' subject '.jsonl']), 'wx');
    if fid < 0
        error('gt21_rb01_label_export:out', 'labels file already exists or cannot be created');
    end
    cleaner = onCleanup(@() fclose(fid));
    for s = 1:numel(sessions)
        for m = 1:numel(modes)
            folder = fullfile(source_root, subject, sessions(s).name, modes{m}, 'conditions');
            files = dir(fullfile(folder, '*.mat'));
            [~, order] = sort({files.name});
            files = files(order);
            for k = 1:numel(files)
                rec = describe_recording(fullfile(folder, files(k).name));
                rec.subject = subject; rec.session = sessions(s).name; rec.mode = modes{m};
                rec.recording = erase(files(k).name, '.mat');
                fprintf(fid, '%s\n', jsonencode(rec));
            end
        end
    end
end

function rec = describe_recording(path)
    rec = struct('read_ok', false, 'top_level_fields', {{}}, 'condition_columns', {{}}, 'n_rows', [], ...
        'header_first', [], 'header_last', [], 'label_windows', [], 'label_present', false, ...
        'ramp_incline_column_unique', [], 'ramp_incline_top_level', [], 'stair_height_top_level', [], ...
        'speed_min', [], 'speed_max', [], 'error', '');
    try
        data = load(path);
        rec.top_level_fields = fieldnames(data)';
        if isfield(data, 'stairHeight'), rec.stair_height_top_level = double(data.stairHeight); end
        if isfield(data, 'rampIncline'), rec.ramp_incline_top_level = double(data.rampIncline); end
        if isfield(data, 'conditions') && istable(data.conditions)
            c = data.conditions;
            rec.condition_columns = c.Properties.VariableNames;
            rec.n_rows = height(c);
            if ismember('Header', c.Properties.VariableNames) && height(c) > 0
                rec.header_first = c.Header(1); rec.header_last = c.Header(end);
            end
            if ismember('Speed', c.Properties.VariableNames) && height(c) > 0
                rec.speed_min = min(c.Speed); rec.speed_max = max(c.Speed);
            end
            if ismember('rampIncline', c.Properties.VariableNames)
                rec.ramp_incline_column_unique = unique(double(c.rampIncline(~isnan(c.rampIncline))))';
            end
            if ismember('Label', c.Properties.VariableNames)
                rec.label_present = true;
                rec.label_windows = run_windows(string(c.Label), c.Header);
            end
        end
        rec.read_ok = true;
    catch err
        rec.error = err.message;
    end
end

function windows = run_windows(labels, header)
% Consecutive runs of equal label: label, first and last Header value, row count (header values as stored).
    windows = struct('label', {}, 'start_header', {}, 'end_header', {}, 'rows', {});
    n = numel(labels);
    if n == 0, return; end
    first = 1;
    for i = 2:n + 1
        if i == n + 1 || labels(i) ~= labels(first)
            windows(end + 1) = struct('label', char(labels(first)), 'start_header', header(first), ...
                'end_header', header(i - 1), 'rows', i - first); %#ok<AGROW>
            first = i;
        end
    end
end

function write_text(path, text)
    fid = fopen(path, 'wx');
    if fid < 0
        error('gt21_rb01_label_export:out', 'file already exists or cannot be created: %s', path);
    end
    fprintf(fid, '%s\n', text);
    fclose(fid);
end
