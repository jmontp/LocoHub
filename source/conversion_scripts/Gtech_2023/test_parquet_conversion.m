classdef TestParquetConversion < matlab.unittest.TestCase
    % TestParquetConversion
    % This suite confirms that the optimized conversion produces the same
    % schema and near-numerical equivalence as the legacy conversion.
    
    methods(Test)
        function testSchemaConsistency(testCase)
            % Configure a test instance (directories to test data)
            config.num_points   = 150;
            config.data_dir     = 'TestSegmentation';
            config.raw_data_dir = 'TestRawData';
            config.output_dir   = 'TestParquetData';
            config.parfor_flag  = false;
            config.profile_flag = false;
            
            % Run conversion
            convert_gtech_phase_to_parquet_v2(config);
            
            % Load the output and verify expected columns exist
            output_file = fullfile(config.output_dir, 'gtech_2023_phase.parquet');
            data = parquetread(output_file);
            
            expected_columns = ["knee_angle_s_r","knee_angle_s_l",...
                "knee_vel_s_r","knee_vel_s_l","knee_torque_s_r","knee_torque_s_l",...
                "ankle_angle_s_r","ankle_angle_s_l","ankle_vel_s_r","ankle_vel_s_l",...
                "ankle_torque_s_r","ankle_torque_s_l","foot_angle_s_r","foot_angle_s_l",...
                "foot_vel_s_r","foot_vel_s_l","hip_angle_s_r","hip_angle_s_l",...
                "hip_vel_s_r","hip_vel_s_l","hip_torque_s_r","hip_torque_s_l",...
                "task","cop_z_r","cop_x_r","cop_z_l","cop_x_l",...
                "grf_y_r","grf_z_r","grf_x_r","grf_y_l","grf_z_l","grf_x_l","phase"];
            
            actual_columns = string(data.Properties.VariableNames);
            for col = expected_columns
                testCase.assertTrue(ismember(col, actual_columns), ['Missing column: ' col]);
            end
        end
        
        function testNumericalEquivalence(testCase)
            % This test compares legacy and optimized conversion outputs.
            legacy_file = 'legacy_parquet.parquet';
            optimized_file = fullfile('ParquetData', 'gtech_2023_phase.parquet');
            legacy_data = parquetread(legacy_file);
            optimized_data = parquetread(optimized_file);
            
            testCase.verifyEqual(height(legacy_data), height(optimized_data));
            numeric_vars = varfun(@isnumeric, legacy_data, 'OutputFormat','uniform');
            numeric_columns = legacy_data.Properties.VariableNames(numeric_vars);
            tol = 1e-6;
            for i = 1:length(numeric_columns)
                col = numeric_columns{i};
                diff_val = abs(legacy_data.(col) - optimized_data.(col));
                testCase.verifyLessThanOrEqual(max(diff_val), tol, ...
                    ['Column ', col, ' differs more than tolerance.']);
            end
        end
    end
end 