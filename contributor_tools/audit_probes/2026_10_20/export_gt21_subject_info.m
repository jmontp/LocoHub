function export_gt21_subject_info(options)
% Read the original native table independently of the dataset converter.
    assert(~isfile(options.output_path), 'Immutable output exists');
    source = load(fullfile(options.data_root, 'SubjectInfo.mat'));
    assert(isfield(source, 'data') && istable(source.data));
    assert(all(ismember({'Subject','Weight'}, source.data.Properties.VariableNames)));
    measurements = source.data(:, {'Subject','Weight'});
    assert(all(isfinite(measurements.Weight)) && all(measurements.Weight > 0));
    assert(numel(unique(string(measurements.Subject))) == height(measurements));
    writetable(measurements, options.output_path);
    restored = readtable(options.output_path);
    assert(isequal(string(restored.Subject), string(measurements.Subject)));
    assert(isequaln(restored.Weight, measurements.Weight), 'Mass values changed on CSV readback');
    fprintf('Verified exact native mass readback for %d subjects\n', height(measurements));
end
