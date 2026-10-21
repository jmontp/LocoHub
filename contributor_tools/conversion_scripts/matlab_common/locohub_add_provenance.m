function rows = locohub_add_provenance(rows, recording_id, source_key, reference_side, observation_type, start_time_s, end_time_s)
% Attach source-derived identity. source_key identifies source events or a
% named source-array element, never an export-order counter.
    assert(strlength(string(recording_id)) > 0 && strlength(string(source_key)) > 0, ...
        'LocoHub:Identity', 'Recording and source observation keys are required.');
    assert(any(strcmp(reference_side, {'left', 'right', 'unknown'})), ...
        'LocoHub:ReferenceSide', 'Invalid anatomical reference side.');
    assert((isnan(start_time_s) && isnan(end_time_s)) || ...
        (isfinite(start_time_s) && isfinite(end_time_s) && end_time_s > start_time_s), ...
        'LocoHub:SourceInterval', 'Source interval must be increasing or unavailable.');
    n = height(rows);
    identity = sprintf('%s:%s:%s', recording_id, source_key, reference_side);
    rows.source_recording_id = repmat({char(recording_id)}, n, 1);
    rows.observation_id = repmat({identity}, n, 1);
    rows.reference_side = repmat({char(reference_side)}, n, 1);
    rows.observation_type = repmat({char(observation_type)}, n, 1);
    rows.source_start_time_s = repmat(start_time_s, n, 1);
    rows.source_end_time_s = repmat(end_time_s, n, 1);
    for name = {'task_info', 'subject_metadata'}
        column = name{1};
        if ismember(column, rows.Properties.VariableNames)
            values = string(rows.(column));
            [unique_values, ~, groups] = unique(values);
            encoded = cell(numel(unique_values), 1);
            for k = 1:numel(unique_values)
                encoded{k} = locohub_metadata_json(unique_values(k));
            end
            rows.(column) = encoded(groups);
        end
    end
end
