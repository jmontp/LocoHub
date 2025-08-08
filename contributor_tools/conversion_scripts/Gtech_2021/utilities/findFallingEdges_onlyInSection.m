function edges = findFallingEdges_onlyInSection(booleanVector, searchRange)
    % Find falling edges (1 to 0 transitions) within a specific search range
    % Used for detecting heel strikes in gait cycle data
    %
    % Inputs:
    %   booleanVector - logical vector to search for falling edges
    %   searchRange - indices to search within
    %
    % Output:
    %   edges - indices where falling edges occur
    
    edges = [];
    
    if isempty(booleanVector) || isempty(searchRange)
        return;
    end
    
    % Ensure search range is within bounds
    searchRange = searchRange(searchRange >= 1 & searchRange <= length(booleanVector));
    
    if length(searchRange) < 2
        return;
    end
    
    % Get the section to search
    section = booleanVector(searchRange);
    
    % Find falling edges (1 to 0 transitions)
    % A falling edge occurs when current value is 0 and previous is 1
    falling = [false; (section(1:end-1) == 1) & (section(2:end) == 0)];
    
    % Get indices in original vector
    edge_indices = find(falling);
    
    if ~isempty(edge_indices)
        % Convert back to original indices
        edges = searchRange(edge_indices);
    end
end