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
            
            expected_columns = ["knee_flexion_angle_r_rad","knee_flexion_angle_l_rad",...
                "knee_flexion_velocity_r_rad_s","knee_flexion_velocity_l_rad_s","knee_flexion_moment_r_Nm","knee_flexion_moment_l_Nm",...
                "ankle_dorsiflexion_angle_r_rad","ankle_dorsiflexion_angle_l_rad","ankle_dorsiflexion_velocity_r_rad_s","ankle_dorsiflexion_velocity_l_rad_s",...
                "ankle_dorsiflexion_moment_r_Nm","ankle_dorsiflexion_moment_l_Nm","foot_angle_s_r","foot_angle_s_l",...
                "foot_vel_s_r","foot_vel_s_l","hip_flexion_angle_r_rad","hip_flexion_angle_l_rad",...
                "hip_flexion_velocity_r_rad_s","hip_flexion_velocity_l_rad_s","hip_flexion_moment_r_Nm","hip_flexion_moment_l_Nm",...
                "task","cop_z_r","cop_x_r","cop_z_l","cop_x_l",...
                "grf_y_r","grf_z_r","grf_x_r","grf_y_l","grf_z_l","grf_x_l","phase_l","phase_r"];
            
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