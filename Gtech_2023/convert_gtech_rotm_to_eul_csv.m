% MIT License
% 
% Copyright (c) 2024 José A. Montes Pérez
% 
% Permission is hereby granted, free of charge, to any person obtaining a copy
% of this software and associated documentation files (the "Software"), to deal
% in the Software without restriction, including without limitation the rights
% to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
% copies of the Software, and to permit persons to whom the Software is
% furnished to do so, subject to the following conditions:
% 
% The above copyright notice and this permission notice shall be included in
% all copies or substantial portions of the Software.
% 
% THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
% IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
% FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
% AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
% LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
% OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
% THE SOFTWARE.

% close all figures
close all;
clear all;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% User configuration area

% Euler angle sequence. This defines the ordering of the euler angle
% convention. Reference the second argument in: 
% https://www.mathworks.com/help/robotics/ref/rotm2eul.html
rotm_sequence = 'YZX'; % Z should correspond to saggital plane angles

% Define the base folder and the destination sub folder
% Structure of the files in the RawData folder is as follows:
% base_folder/SubjectName/Transforms/TaskName.mat
base_folder = 'RawData';

% Setting to true will make the script not save any of the euler angle 
% csv files and just plot the x, y, and z angles. This is good way to 
% verify that you're rotm sequence is correct.
just_plot = false;
plot_title = [rotm_sequence ' '];


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Don't touch anything under here

% List every folder in the base folder
subject_list = dir(fullfile(base_folder, '*'));

% Remove the '.' and '..' folders
subject_list = subject_list(~ismember({subject_list.name}, {'.', '..'}));

% Preallocate memory for large arrays
subject_count = length(subject_list);

% Create one big subplot that will have 12 total subplots
% It will have 9 (3 subjects time three euler angles) rows and 4 columns, 
% with the columns have different subjects
if just_plot
    figure;
    sgtitle(append("Testing rotation ordering: ", rotm_sequence, plot_title))
end

% Iterate through all the subjects
for subject_num = 1:subject_count

    % Get the subject_name
    subject_name = subject_list(subject_num).name

    % Get all the folders for the Transformation subfolder
    task_list = dir(fullfile(base_folder, subject_name,'Transforms', '*'));

    % Remove the '.' and '..' folders
    task_list = task_list(~ismember({task_list.name}, {'.', '..'}));

    % Preallocate memory for large arrays
    task_count = length(task_list);

    % Iterate through all the tasks
    for task_num = 1:task_count

        % Get the task name
        task_name = task_list(task_num).name;
        % Remove the ".mat" file type from the task name
        task_name = task_name(1:end-4);

        % If we just want to plot, skip all the tasks that are not 
        % normal_walk_1
        if just_plot && ~strcmp(task_name, 'normal_walk_1')
            continue
        end

        % Load the file
        data_file = fullfile(base_folder,subject_name,'Transforms',...
                             task_name);
        data = load(data_file);
        Transforms = data.Transforms;

        % Get the number of data points
        data_points = size(Transforms.Header, 1);

        % Get the fields in the struct
        field_list = fieldnames(Transforms);

        % Create an empty table that will store the data to be ultimately 
        % saved
        euler_angle_table = table;
        euler_velocity_table = table;
          
        % Print the subject, task, and field name
        disp([subject_name, " ", task_name]);
        
        % Iterate through all the field members and populate the table
        for field_num = 1:length(field_list)

            % Get the field name
            field_name = field_list{field_num};

            % We don't care about the Properties, Row, or Variables fields
            if strcmp(field_name, 'Properties') || ...
               strcmp(field_name, 'Row') || ...
               strcmp(field_name, 'Variables')
                continue
            end

            % Get the field data
            field_data = Transforms.(field_name);

            % The header column is just the time axis. Add it to the table
            % and move on to the next field.
            if strcmp(field_name, 'Header')
                euler_angle_table.time = field_data;
                euler_velocity_table.time = field_data;
                continue
            end

            % Get the rotation matrices and convert them into the euler 
            % angles. They are read is as homogenous matrices
            h_mat = cell2mat(field_data);
            
            % Reshape the matrix to be 4x4xN. The normal indexing of 
            % reshape does not work, so I have to transpose, reshape, 
            % and the transpose back to get the right indexing.
            % The 3d transpose is done using the permute method since 
            % Transpose does not work on 3d matrices.
            h_mat_r = permute(reshape(h_mat', 4, 4, []),[2,1,3]);
            
            % Assert that the indexing works. This is done by comparing
            % the first homogeneous matrix are equal to each other
            assert(sum(h_mat_r(1:4,1:4,1)-h_mat(1:4,1:4),"all")==0);

            % Get the rotation matrices as the first 3x3 matrix of the 
            % homogenous transform
            rotation_matrices = h_mat_r(1:3, 1:3, :);
           
            % Convert the rotation matrices to euler angles
            % euler_angles = rotm2eul(rotation_matrices, "YZX"); %My order
            % euler_angles = rotm2eul(rotation_matrices, "ZYX"); %Default
            euler_angles = rad2deg(rotm2eul(rotation_matrices, rotm_sequence));

       
 
            % Add the field to the table
            for euler_idx = 1:3
                angle_name = append(field_name,"_",rotm_sequence(euler_idx));
                euler_angle_table.(angle_name) = euler_angles(:, euler_idx);
                   
                % Calculate the euler velocities
                Hz = 200; % For the motion capture data
                dt = 1/Hz;

                vel_name = append(field_name,"_vel_",rotm_sequence(euler_idx));
                euler_velocity = gradient(euler_angles(:, euler_idx))/dt;
                euler_velocity_table.(vel_name) = euler_velocity;
            end
           
        end

        % Save the table for the given task
        if ~just_plot
            angle_dest_file_name = fullfile(base_folder, subject_name,...
                'CSV_data', task_name, 'Link_Angle.csv');
            velocity_dest_file_name = fullfile(base_folder, subject_name,...
                'CSV_data', task_name, 'Link_Velocities.csv');
            try
                writetable(euler_angle_table, angle_dest_file_name)
                writetable(euler_velocity_table, velocity_dest_file_name)
            catch 
                %If the folder for the task does not exist, then we just 
                % don't do anything
            end
        end
       

        % Plot the data for the normal walking task
        if strcmp(task_name, 'normal_walk_1') && just_plot
            
            % Define the plot matrix
            subrows_per_subject = 3;
            subjects_per_row = 3;
            num_rows = subrows_per_subject*subjects_per_row;
            num_cols = 4;

            % Define the legend order. These two variables have to 
            % match in order
            legend_order = {"Z", "Y", "X"};
            task_order = {append("calcn_r_", legend_order{1}),...
                          append("calcn_r_", legend_order{2}),...
                          append("calcn_r_", legend_order{3})};

            % Create plot with three vertical subplots
            ns = 2000;
            ne = 6000;
            for euler_idx = 1:3

                % Get the column number of the subplot
                subplot_num = ...
                mod(subject_num-1,subjects_per_row)*num_cols*subrows_per_subject + ...
                (euler_idx-1)*num_cols + ...
                ceil(subject_num/subjects_per_row)
                
                % Create a subplot
                ax = subplot(9, 4, subplot_num);

                % Get the data to plot
                d = euler_angle_table.(task_order{euler_idx});
                % plot_data = rad2deg(d(ns:ne) - d(1));  %Shift data
                plot_data = rad2deg(d(ns:ne));       % Unshifted data
                
                % Plot the data
                plot(euler_angle_table.Header(ns:ne), plot_data);

                % Set the title for every subject
                if euler_idx == 1
                    title(append(subject_name, " ", task_name), ...
                        'Interpreter','none',...
                        'FontSize', 14, 'FontWeight', 'bold');
                end
                
                % Make z axis bold
                y_text = append("Euler ", legend_order{euler_idx}, ' (deg)');
                if strcmp(legend_order{euler_idx},"Z")==true
                    ylabel(y_text ,'FontSize', 14, 'FontWeight', 'bold');
                    ax.XGrid = 'off';
                    ax.YGrid = 'on';
                else
                    ylabel(y_text);
                end

                % Set the x label for every subject
                if mod(subplot_num,12) >= 9
                    xlabel("Time (s)");
                end
                
                legend(legend_order{euler_idx})
            end
            disp("Plotted")
        end
    end
end