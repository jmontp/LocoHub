function encoded = locohub_metadata_json(value)
% Encode converter-owned metadata as a JSON object. Unknown numbers become null.
% Existing converters construct flat comma-separated key:value strings; decode
% those here before writing. This is not a loader for arbitrary legacy datasets.
    if isstruct(value)
        encoded = jsonencode(value);
        return;
    end
    value = char(value);
    if startsWith(strtrim(value), '{')
        decoded = jsondecode(value);
        assert(isstruct(decoded), 'LocoHub:Metadata', 'Metadata must be an object.');
        encoded = jsonencode(decoded);
        return;
    end
    metadata = struct();
    if ~isempty(value)
        parts = strsplit(value, ',');
        for k = 1:numel(parts)
            split_at = strfind(parts{k}, ':');
            assert(~isempty(split_at), 'LocoHub:Metadata', 'Invalid metadata field.');
            key = strtrim(parts{k}(1:split_at(1)-1));
            item = strtrim(parts{k}(split_at(1)+1:end));
            assert(isvarname(key), 'LocoHub:Metadata', 'Invalid metadata key.');
            assert(~isfield(metadata, key), 'LocoHub:Metadata', 'Duplicate metadata key.');
            numeric = str2double(item);
            if strcmpi(item, 'true') || strcmpi(item, 'false')
                metadata.(key) = strcmpi(item, 'true');
            elseif isfinite(numeric)
                metadata.(key) = numeric;
            elseif any(strcmpi(item, {'nan', 'unknown', 'null', 'inf', '-inf'}))
                metadata.(key) = NaN;
            else
                metadata.(key) = item;
            end
        end
    end
    encoded = jsonencode(metadata);
end
