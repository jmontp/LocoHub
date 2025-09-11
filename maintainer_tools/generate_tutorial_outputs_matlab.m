function generate_tutorial_outputs_matlab(csvPath, outDir)
% generate_tutorial_outputs_matlab Generate expected tutorial plots (MATLAB)
%
% Usage (non-interactive):
%   matlab -batch "generate_tutorial_outputs_matlab('docs/contributing/locohub_example_data.csv','docs/users/tutorials/assets')"
%
% Inputs:
%   csvPath - path to example CSV (string/char)
%   outDir  - output directory to save figures (string/char)

if nargin < 1 || isempty(csvPath)
    csvPath = '../docs/contributing/locohub_example_data.csv';
end
if nargin < 2 || isempty(outDir)
    outDir  = '../docs/users/tutorials/assets';
end

if ~exist(outDir, 'dir')
    mkdir(outDir);
end

T = readtable(csvPath);

% Basic checks
req = {'subject','task','phase_ipsi','knee_flexion_angle_ipsi_rad','vertical_grf_ipsi_N'};
missing = req(~ismember(req, T.Properties.VariableNames));
if ~isempty(missing)
    % Try to sanitize CSV where task_info contains unquoted commas
    warnMsg = sprintf('Missing required columns: %s. Attempting CSV sanitization...', strjoin(missing, ', '));
    warning(warnMsg);
    sanitizedPath = fullfile(outDir, '_sanitized_example.csv');
    try
        sanitizeCsv(csvPath, sanitizedPath);
        T = readtable(sanitizedPath);
        missing = req(~ismember(req, T.Properties.VariableNames));
        if ~isempty(missing)
            error('Missing required columns after sanitization: %s', strjoin(missing, ', '));
        end
    catch me
        rethrow(me);
    end
end

% Helper for mean±std by phase
    function G = meanStdByPhase(colName)
        [g,~,idx] = unique(T.phase_ipsi);
        mu  = splitapply(@mean, T.(colName), idx);
        sig = splitapply(@std,  T.(colName), idx);
        G = table(g, mu, sig, 'VariableNames', {'phase_ipsi','mean','std'});
    end

% 1) Knee Flexion Mean±SD
Gknee = meanStdByPhase('knee_flexion_angle_ipsi_rad');
f1 = figure('Visible','off','Position',[100 100 600 360]); hold on
fill([Gknee.phase_ipsi; flipud(Gknee.phase_ipsi)], ...
     [Gknee.mean - Gknee.std; flipud(Gknee.mean + Gknee.std)], ...
     [0 0.45 0.9], 'FaceAlpha',0.2, 'EdgeColor','none');
plot(Gknee.phase_ipsi, Gknee.mean, 'Color',[0 0.45 0.9], 'LineWidth',1.8)
xlabel('Gait Cycle (%)'); ylabel('Knee Flexion (rad)'); grid on; box on
title('Knee Flexion: Mean \.\pm SD')
set(gca,'Layer','top');
exportgraphics(f1, fullfile(outDir,'expected_knee_flexion_mean_sd_matlab.png'), 'Resolution',150);
close(f1)

% 2) Vertical GRF Mean±SD
Ggrf = meanStdByPhase('vertical_grf_ipsi_N');
f2 = figure('Visible','off','Position',[100 100 600 360]); hold on
fill([Ggrf.phase_ipsi; flipud(Ggrf.phase_ipsi)], ...
     [Ggrf.mean - Ggrf.std; flipud(Ggrf.mean + Ggrf.std)], ...
     [0.85 0.33 0.10], 'FaceAlpha',0.2, 'EdgeColor','none');
plot(Ggrf.phase_ipsi, Ggrf.mean, 'Color',[0.85 0.33 0.10], 'LineWidth',1.8)
xlabel('Gait Cycle (%)'); ylabel('Vertical GRF (N)'); grid on; box on
title('Vertical GRF: Mean \.\pm SD')
set(gca,'Layer','top');
exportgraphics(f2, fullfile(outDir,'expected_vertical_grf_mean_sd_matlab.png'), 'Resolution',150);
close(f2)

fprintf('Wrote: %s\n', fullfile(outDir,'expected_knee_flexion_mean_sd_matlab.png'));
fprintf('Wrote: %s\n', fullfile(outDir,'expected_vertical_grf_mean_sd_matlab.png'));

end

function sanitizeCsv(inPath, outPath)
% sanitizeCsv Fix unquoted commas in task_info by quoting the 4th field
% Assumes CSV order: subject,task,task_id,task_info,step,phase_ipsi,...
% Ensure parent directory exists for the output path
parentDir = fileparts(outPath);
if ~isempty(parentDir) && ~exist(parentDir, 'dir')
    mkdir(parentDir);
end

txt = fileread(inPath);
lines = splitlines(txt);
if isempty(lines)
    error('Empty CSV: %s', inPath);
end
header = lines{1};
data = lines(2:end);
out = cell(size(data));
for i = 1:numel(data)
    row = data{i};
    if strlength(row) == 0
        out{i} = row; %#ok<AGROW>
        continue
    end
    parts = split(row, ',');
    % If parts are as expected (>= 14) and task_info likely split across two fields,
    % merge fields 4 and 5 into a single quoted field.
    if numel(parts) >= 15
        parts(4) = strcat('"', parts(4), ',', parts(5), '"');
        parts(5) = [];
    end
    out{i} = strjoin(parts, ','); %#ok<AGROW>
end
fid = fopen(outPath, 'w');
if fid == -1
    error('Failed to open sanitized output path for writing: %s', outPath);
end
cleaner = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, '%s\n', header);
for i = 1:numel(out)
    fprintf(fid, '%s\n', out{i});
end
end
