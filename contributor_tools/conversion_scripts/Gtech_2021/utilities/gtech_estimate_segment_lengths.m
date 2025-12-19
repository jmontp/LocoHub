function seg = gtech_estimate_segment_lengths(root_dir, subject_code)
%GTECH_ESTIMATE_SEGMENT_LENGTHS Estimate thigh, shank, and foot lengths in meters.
%
% seg = gtech_estimate_segment_lengths(root_dir, subject_code)
%
% Uses markers from the CAMARGO_ET_AL_J_BIOMECH_DATASET to estimate
% per-subject segment lengths. Prefers static markers; falls back to
% level-ground markers, then treadmill, ramp, and stair markers. Returns
% NaN for any segment that cannot be computed from available markers.
%
% Output fields (all in meters):
%   seg.thigh_length_m
%   seg.shank_length_m
%   seg.foot_length_m

seg = struct( ...
    'thigh_length_m', NaN, ...
    'shank_length_m', NaN, ...
    'foot_length_m', NaN);

if nargin < 2 || isempty(root_dir) || isempty(subject_code)
    return;
end

markers = load_markers_table(root_dir, subject_code);
if isempty(markers) || ~istable(markers)
    return;
end

% Compute median distances (more robust to motion than mean)
seg_R = struct( ...
    'thigh', pair_mean_dist(markers, 'R_Thigh_Upper', 'R_Knee_Lat'), ...
    'shank', pair_mean_dist(markers, 'R_Knee_Lat', 'R_Ankle_Lat'), ...
    'foot',  pair_mean_dist(markers, 'R_Heel', 'R_Toe_Tip'));

seg_L = struct( ...
    'thigh', pair_mean_dist(markers, 'L_Thigh_Upper', 'L_Knee_Lat'), ...
    'shank', pair_mean_dist(markers, 'L_Knee_Lat', 'L_Ankle_Lat'), ...
    'foot',  pair_mean_dist(markers, 'L_Heel', 'L_Toe_Tip'));

seg.thigh_length_m = mean([seg_R.thigh, seg_L.thigh], 'omitnan');
seg.shank_length_m = mean([seg_R.shank, seg_L.shank], 'omitnan');
seg.foot_length_m  = mean([seg_R.foot,  seg_L.foot],  'omitnan');

if isnan(seg.thigh_length_m)
    seg.thigh_length_m = NaN;
end
if isnan(seg.shank_length_m)
    seg.shank_length_m = NaN;
end
if isnan(seg.foot_length_m)
    seg.foot_length_m = NaN;
end

end

function markers = load_markers_table(root_dir, subject_code)
markers = [];
subject_dir = fullfile(root_dir, subject_code);
if ~exist(subject_dir, 'dir')
    return;
end

date_dirs = dir(subject_dir);
date_dirs = date_dirs([date_dirs.isdir]);
date_dirs = date_dirs(contains({date_dirs.name}, '_'));
if isempty(date_dirs)
    return;
end
% Use first date folder (same behavior as converter)
date_dirs = sort({date_dirs.name});
date_folder = date_dirs{1};

% Prefer static, then levelground, treadmill, ramp, stair
mode_order = { ...
    fullfile(subject_dir, date_folder, 'static', 'markers'), ...
    fullfile(subject_dir, date_folder, 'levelground', 'markers'), ...
    fullfile(subject_dir, date_folder, 'treadmill', 'markers'), ...
    fullfile(subject_dir, date_folder, 'ramp', 'markers'), ...
    fullfile(subject_dir, date_folder, 'stair', 'markers')};

for m = 1:numel(mode_order)
    marker_dir = mode_order{m};
    if ~exist(marker_dir, 'dir')
        continue;
    end
    files = dir(fullfile(marker_dir, '*.mat'));
    if isempty(files)
        continue;
    end
    % Sort for reproducibility
    [~, idx] = sort({files.name});
    files = files(idx);
    for i = 1:numel(files)
        file_path = fullfile(marker_dir, files(i).name);
        try
            temp = load(file_path);
        catch
            continue;
        end
        if isfield(temp, 'data') && istable(temp.data)
            markers = temp.data;
        elseif istable(temp)
            markers = temp;
        else
            fns = fieldnames(temp);
            for k = 1:numel(fns)
                val = temp.(fns{k});
                if istable(val)
                    markers = val;
                    break;
                end
            end
        end
        if ~isempty(markers)
            return;
        end
    end
end
end

function d = pair_mean_dist(markers, nameA, nameB)
colsA = strcat(nameA, {'_x','_y','_z'});
colsB = strcat(nameB, {'_x','_y','_z'});
if ~all(ismember([colsA colsB], markers.Properties.VariableNames))
    d = NaN;
    return;
end
coordA = markers{:, colsA};
coordB = markers{:, colsB};
if isempty(coordA) || isempty(coordB)
    d = NaN;
    return;
end
if size(coordA, 1) ~= size(coordB, 1)
    n = min(size(coordA, 1), size(coordB, 1));
    coordA = coordA(1:n, :);
    coordB = coordB(1:n, :);
end
diff_mm = coordA - coordB;
dist_mm = sqrt(sum(diff_mm.^2, 2));
d = median(dist_mm, 'omitnan') / 1000.0;
end
