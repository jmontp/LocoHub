function gt21_static_export(source_root, out_dir, subject, nonce)
% GT21 standing-trial export for ONE participant (A3 check: does a standing-pose offset explain the knee gap?). DRAFT: not run.
% Reads only: <source_root>/<subject>/<session>/static/{markers,ik,ik_offset}/*.mat (MATLAB tables).
% Writes only (refusing an existing file, never overwriting) into out_dir:
%   <subject>__<session>__<channel>__<recording>.csv   one per static table; numeric columns, %.17g, header row = column names
%   static_meta_<subject>.json                         what was found, column names, units, row counts, any read error
% Nothing is converted, filtered, relabelled or inferred. A missing static folder or unreadable table is recorded in the
% meta file and is not an error. nonce is only echoed so the launcher can find this MATLAB process.
    if nargin ~= 4
        error('gt21_static_export:args', 'source_root, out_dir, subject, nonce required');
    end
    if isempty(regexp(subject, '^AB\d\d$', 'once'))
        error('gt21_static_export:subject', 'subject must look like AB06');
    end
    fprintf('gt21_static_export nonce=%s subject=%s\n', nonce, subject);
    if ~isfolder(out_dir)
        error('gt21_static_export:out', 'out_dir must already exist (created by the runner)');
    end
    channels = {'markers', 'ik', 'ik_offset'};
    sessions = dir(fullfile(source_root, subject));
    sessions = sessions([sessions.isdir] & ~startsWith({sessions.name}, '.') & ~strcmp({sessions.name}, 'osimxml'));
    meta = struct('subject', subject, 'sessions_checked', {{sessions.name}}, 'tables', struct([]));
    n = 0;
    for s = 1:numel(sessions)
        for c = 1:numel(channels)
            folder = fullfile(source_root, subject, sessions(s).name, 'static', channels{c});
            files = dir(fullfile(folder, '*.mat'));
            [~, order] = sort({files.name});
            files = files(order);
            for k = 1:numel(files)
                n = n + 1;
                rec = erase(files(k).name, '.mat');
                entry = struct('session', sessions(s).name, 'channel', channels{c}, 'recording', rec, ...
                    'read_ok', false, 'variable', '', 'csv', '', 'n_rows', [], 'columns', {{}}, 'units', {{}}, 'skipped_columns', {{}}, 'error', '');
                try
                    data = load(fullfile(folder, files(k).name));
                    names = fieldnames(data);
                    tbl = [];
                    for v = 1:numel(names)
                        if istable(data.(names{v})), tbl = data.(names{v}); entry.variable = names{v}; break; end
                    end
                    if isempty(tbl)
                        error('no table variable in file (variables: %s)', strjoin(names', ','));
                    end
                    vn = tbl.Properties.VariableNames;
                    keep = false(1, numel(vn));
                    for v = 1:numel(vn)
                        col = tbl.(vn{v});
                        keep(v) = isnumeric(col) && iscolumn(col);
                    end
                    entry.columns = vn(keep);
                    entry.skipped_columns = vn(~keep);
                    if isempty(tbl.Properties.VariableUnits)
                        entry.units = repmat({''}, 1, nnz(keep));
                    else
                        u = tbl.Properties.VariableUnits;
                        entry.units = u(keep);
                    end
                    entry.n_rows = height(tbl);
                    csv_name = sprintf('%s__%s__%s__%s.csv', subject, sessions(s).name, channels{c}, rec);
                    write_table_csv(fullfile(out_dir, csv_name), tbl, vn(keep));
                    entry.csv = csv_name;
                    entry.read_ok = true;
                catch err
                    entry.error = err.message;
                end
                if n == 1, meta.tables = entry; else, meta.tables(n) = entry; end %#ok<AGROW>
            end
        end
    end
    meta.n_tables = n;
    write_text(fullfile(out_dir, ['static_meta_' subject '.json']), jsonencode(meta));
end

function write_table_csv(path, tbl, names)
    if isfile(path)  % MATLAB fopen has no exclusive mode: refuse an existing file explicitly
        error('gt21_static_export:out', 'file already exists: %s', path);
    end
    fid = fopen(path, 'w');
    if fid < 0
        error('gt21_static_export:out', 'cannot create: %s', path);
    end
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, '%s\n', strjoin(names, ','));
    m = zeros(height(tbl), numel(names));
    for v = 1:numel(names)
        m(:, v) = double(tbl.(names{v}));
    end
    fmt = [repmat('%.17g,', 1, numel(names) - 1) '%.17g\n'];
    fprintf(fid, fmt, m');
end

function write_text(path, text)
    if isfile(path)
        error('gt21_static_export:out', 'file already exists: %s', path);
    end
    fid = fopen(path, 'w');
    if fid < 0
        error('gt21_static_export:out', 'cannot create: %s', path);
    end
    fprintf(fid, '%s\n', text);
    fclose(fid);
end
