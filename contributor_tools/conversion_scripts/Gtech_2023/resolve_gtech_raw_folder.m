function folder = resolve_gtech_raw_folder(csv_root, parsing_name)
% Resolve the longest complete recording prefix present in the original source.
% For example, sit_to_stand_1_2_short-arm belongs to sit_to_stand_1_2, not _1.
    [~, base] = fileparts(parsing_name);
    base = regexprep(base, '_parsing$', '');
    entries = dir(csv_root);
    candidates = {};
    for index = 1:numel(entries)
        name = entries(index).name;
        if entries(index).isdir && ~any(strcmp(name, {'.', '..'})) && ...
                (strcmp(base, name) || startsWith(base, [name '_']))
            candidates{end+1} = name; %#ok<AGROW>
        end
    end
    assert(~isempty(candidates), 'No original recording folder matches %s', parsing_name);
    lengths = cellfun(@numel, candidates);
    candidates = candidates(lengths == max(lengths));
    assert(numel(candidates) == 1, 'Ambiguous original recording for %s', parsing_name);
    folder = candidates{1};
end
