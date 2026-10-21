function prepare_gt23_transforms(options)
% Preserve native calcn tables in a source window, without CSV precision loss.
% This is input preparation only; no standardized data is produced.
    required = {'source_path', 'output_path', 'start_s', 'end_s'};
    assert(all(isfield(options, required)), 'Missing transform preparation options');
    assert(~isfile(options.output_path), 'Immutable output already exists');
    info = dir(options.source_path);
    assert(numel(info) == 1 && info.bytes <= 64*1024^2, 'Transform input exceeds 64 MiB admission');
    assert(isfinite(options.start_s) && isfinite(options.end_s) && options.end_s > options.start_s);
    original = load(options.source_path, 'Transforms');
    assert(isfield(original, 'Transforms') && istable(original.Transforms), 'Expected native transform table');
    columns = {'Header', 'calcn_l', 'calcn_r'};
    assert(all(ismember(columns, original.Transforms.Properties.VariableNames)), 'Missing calcn columns');
    clock = original.Transforms.Header(:);
    assert(isnumeric(clock) && all(isfinite(clock)) && all(diff(clock) > 0), 'Invalid transform clock');
    selection = find(clock >= options.start_s & clock <= options.end_s);
    before = find(clock < options.start_s, 1, 'last');
    after = find(clock > options.end_s, 1, 'first');
    selection = unique([before; selection; after]);
    assert(numel(selection) >= 2, 'Insufficient transform coverage');
    Transforms = original.Transforms(selection, columns);
    save(options.output_path, 'Transforms', '-v7');
    restored = load(options.output_path, 'Transforms');
    assert(isequaln(restored.Transforms, original.Transforms(selection, columns)), 'Native transform readback mismatch');
    report = struct('converted_data', false, 'exact_native_readback', true, ...
        'source_rows', height(original.Transforms), 'window_rows', height(Transforms), ...
        'first_source_row_1based', selection(1), 'last_source_row_1based', selection(end), ...
        'columns', {columns}, 'source_path', options.source_path);
    fid = fopen([options.output_path '.verification.json'], 'w');
    assert(fid >= 0, 'Cannot write verification');
    cleanup = onCleanup(@() fclose(fid));
    fprintf(fid, '%s\n', jsonencode(report));
end
