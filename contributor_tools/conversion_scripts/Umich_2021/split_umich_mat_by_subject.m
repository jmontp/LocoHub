% One-time preparation for bounded-memory UMich conversions.
% This still loads one original MAT file at a time, but subsequent conversion
% runs load only one subject. Run from the Umich_2021 conversion directory.

streaming_output = fullfile(pwd, 'subject_mat', 'Streaming');
normalized_output = fullfile(pwd, 'subject_mat', 'Normalized');
if ~isfolder(streaming_output), mkdir(streaming_output); end
if ~isfolder(normalized_output), mkdir(normalized_output); end

fprintf('Loading Streaming.mat for one-time subject split...\n');
source = load('Streaming.mat', 'Streaming');
subjects = fieldnames(source.Streaming);
for subject_idx = 1:length(subjects)
    subject = subjects{subject_idx};
    subject_data = source.Streaming.(subject); %#ok<NASGU>
    save(fullfile(streaming_output, [subject '.mat']), 'subject_data', '-v7.3');
    clear subject_data
end
clear source

if exist('Normalized.mat', 'file')
    fprintf('Loading Normalized.mat for one-time subject split...\n');
    source = load('Normalized.mat', 'Normalized');
    subjects = fieldnames(source.Normalized);
    for subject_idx = 1:length(subjects)
        subject = subjects{subject_idx};
        normalized_subject = source.Normalized.(subject); %#ok<NASGU>
        save(fullfile(normalized_output, [subject '.mat']), 'normalized_subject', '-v7.3');
        clear normalized_subject
    end
    clear source
end

fprintf('Subject files written beneath %s\n', fullfile(pwd, 'subject_mat'));
