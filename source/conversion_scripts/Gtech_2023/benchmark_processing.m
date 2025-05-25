%% Benchmark Processing Script
% This script compares the performance of the legacy conversion with the
% optimized conversion.

clc;
clear;

% Configuration for both runs
config.num_points   = 150;
config.data_dir     = 'Segmentation';
config.raw_data_dir = 'RawData';
config.output_dir   = 'ParquetData';
config.parfor_flag  = true;
config.profile_flag = false;

disp('Benchmarking legacy conversion...');
tic;
% Assumes the legacy conversion function exists.
convert_gtech_phase_to_parquet();  % Legacy call (without config)
legacy_time = toc;
fprintf('Legacy conversion time: %.2f seconds\n', legacy_time);

disp('Benchmarking optimized conversion...');
tic;
convert_gtech_phase_to_parquet_v2(config);
optimized_time = toc;
fprintf('Optimized conversion time: %.2f seconds\n', optimized_time);

fprintf('Speedup factor: %.2f×\n', legacy_time / optimized_time); 