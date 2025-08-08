function events = findEvents(eventVector)
    % Find continuous events in a boolean vector
    % Returns start and end indices of continuous true regions
    %
    % Input:
    %   eventVector - logical vector indicating events
    %
    % Output:
    %   events - table with Start and End columns
    
    events = table();
    
    if isempty(eventVector)
        return;
    end
    
    % Ensure it's a logical vector
    eventVector = logical(eventVector);
    
    % Find transitions
    % Add padding to handle edge cases
    padded = [false; eventVector(:); false];
    
    % Rising edges (start of events)
    starts = find(diff(padded) == 1);
    
    % Falling edges (end of events)
    ends = find(diff(padded) == -1) - 1;
    
    % Create events table
    if ~isempty(starts) && ~isempty(ends)
        events.Start = starts;
        events.End = ends;
    end
end