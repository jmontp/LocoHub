function export_gt21_force_sources(options)
% Preserve native force and marker tables without assigning axes, signs or feet.
    assert(~isfile(options.output_path), 'LocoHub:ImmutableOutput', 'Output exists');
    folder = fileparts(options.output_path);
    report = struct('status', 'native_source_tables_readback', ...
        'scientific_approval', false, 'tables', {{}});
    for channel = {'fp', 'markers'}
        source_path = fullfile(options.data_root, options.subject, options.date, ...
            options.mode, channel{1}, options.recording);
        assert(isfile(source_path), 'LocoHub:MissingSource', 'Missing %s', source_path);
        source = load(source_path);
        fields = fieldnames(source);
        found = false;
        for k = 1:numel(fields)
            original = source.(fields{k});
            if ~istable(original), continue; end
            found = true;
            assert(any(strcmp(original.Properties.VariableNames, 'Header')), ...
                'LocoHub:SourceClock', 'Source table has no clock');
            clock = original.Header;
            assert(all(isfinite(clock)) && all(diff(clock) > 0), ...
                'LocoHub:SourceClock', 'Source clock does not increase');
            name = ['source_' channel{1} '_' fields{k} '.parquet'];
            target = fullfile(folder, name);
            assert(~isfile(target), 'LocoHub:ImmutableOutput', 'Source export exists');
            parquetwrite(target, original);
            restored = parquetread(target);
            assert(isequal(original.Properties.VariableNames, restored.Properties.VariableNames));
            for column = original.Properties.VariableNames
                assert(isequaln(original.(column{1}), restored.(column{1})), ...
                    'LocoHub:Readback', 'Source values changed in %s', column{1});
            end
            item = struct('channel', channel{1}, 'source_field', fields{k}, ...
                'file', name, 'rows', height(original), ...
                'variable_names', {original.Properties.VariableNames}, ...
                'variable_units', {original.Properties.VariableUnits}, ...
                'variable_descriptions', {original.Properties.VariableDescriptions});
            report.tables{end+1} = item;
        end
        assert(found, 'LocoHub:MissingTable', 'No native table in %s', source_path);
    end
    stream = fopen(options.output_path, 'w');
    assert(stream >= 0, 'Cannot write source manifest');
    cleanup = onCleanup(@() fclose(stream));
    fprintf(stream, '%s\n', jsonencode(report));
end
