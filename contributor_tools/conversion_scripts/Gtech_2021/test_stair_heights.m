% Test script to verify stair height processing
% This script checks that all 4 stair heights are properly extracted and processed

fprintf('Testing stair height extraction for Gtech 2021 dataset\n');
fprintf('========================================\n\n');

% Test subject
subject = 'AB06';
base_path = 'CAMARGO_ET_AL_J_BIOMECH_DATASET';
subject_path = fullfile(base_path, subject, '10_09_18', 'stair', 'conditions');

% Check for all stair files
stair_files = dir(fullfile(subject_path, 'stair_*.mat'));
fprintf('Found %d stair files for subject %s\n\n', length(stair_files), subject);

% Track unique heights
unique_heights = [];

% Process each file to extract height
for i = 1:length(stair_files)
    file_path = fullfile(subject_path, stair_files(i).name);
    
    % Extract stair number from filename
    tokens = regexp(stair_files(i).name, 'stair_(\d+)_', 'tokens');
    if ~isempty(tokens)
        stair_num = str2double(tokens{1}{1});
    else
        stair_num = 0;
    end
    
    % Load file and check for stairHeight field
    data = load(file_path);
    
    if isfield(data, 'stairHeight')
        height_in = data.stairHeight;
        height_mm = round(height_in * 25.4);
        
        fprintf('File: %s\n', stair_files(i).name);
        fprintf('  Stair number: %d\n', stair_num);
        fprintf('  Height: %d inches (%d mm)\n', height_in, height_mm);
        
        % Determine task based on trial pattern
        if contains(stair_files(i).name, '_l_01_') || contains(stair_files(i).name, '_r_01_')
            task = 'ascent';
        elseif contains(stair_files(i).name, '_l_02_') || contains(stair_files(i).name, '_r_02_')
            task = 'descent';
        else
            task = 'unknown';
        end
        
        % Generate task_id as would be done in main script
        if strcmp(task, 'ascent')
            task_id = sprintf('stair_ascent_%dmm', height_mm);
        elseif strcmp(task, 'descent')
            task_id = sprintf('stair_descent_%dmm', height_mm);
        else
            task_id = 'unknown';
        end
        
        fprintf('  Task: %s\n', task);
        fprintf('  Task ID: %s\n\n', task_id);
        
        % Track unique heights
        if ~ismember(height_mm, unique_heights)
            unique_heights = [unique_heights, height_mm];
        end
    else
        fprintf('File: %s - NO HEIGHT FIELD FOUND\n\n', stair_files(i).name);
    end
end

% Summary
fprintf('\n========================================\n');
fprintf('SUMMARY\n');
fprintf('========================================\n');
fprintf('Unique stair heights found: ');
unique_heights = sort(unique_heights);
for i = 1:length(unique_heights)
    fprintf('%dmm ', unique_heights(i));
end
fprintf('\n\nExpected heights: 102mm (4in), 127mm (5in), 152mm (6in), 178mm (7in)\n');

if length(unique_heights) == 4
    fprintf('\n✓ All 4 expected stair heights found!\n');
else
    fprintf('\n✗ Only %d of 4 expected heights found\n', length(unique_heights));
end

% Generate expected task_ids
fprintf('\nExpected task_id values after conversion:\n');
for h = unique_heights
    fprintf('  - stair_ascent_%dmm\n', h);
    fprintf('  - stair_descent_%dmm\n', h);
end