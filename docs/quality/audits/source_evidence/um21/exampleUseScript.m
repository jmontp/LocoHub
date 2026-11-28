% exampleUseScript

%% Load Data
% load('Z:\Datasets\R01\Normalized.mat')
% load('Z:\Datasets\R01\Streaming.mat')
% This file takes some time to load, it is recommend to load it once and
% avoid removing it from memory by using "clearvars -except" when clearing
% the matlab workspace
clearvars -except Streaming Normalized;
close all;
clc;

%% Select Subjects and Tasks to Plots

% find the identifier of all anonymous subjects using fieldnames function
% sub=fieldnames(R01);

% -or-

% manually define a cell array of fields you wish to access
sub={'AB04','AB05'};
speed={'s1'};
incline={'in10'};
percentGait=linspace(0,1,150);

%% loop through each subject, plotting kinematics

for s=1:numel(sub)
    % this line uses a dynamic field reference to access the data of each
    % subject in a for loop. Dynamic field references: https://blogs.mathworks.com/loren/2005/12/13/use-dynamic-field-references/
    temp_task = Normalized.(sub{s}).Walk.(speed{1}).(incline{1}); 
    
    %% load pelvis and hip data, calculate thigh angle 
    temp_pelvis = temp_task.jointAngles.PelvisAngles;
    temp_hip = temp_task.jointAngles.HipAngles;
    temp_thigh = temp_hip - temp_pelvis;
    
    % 1.the first dimension of data is 150 points, uniformly spread
    % throughout the gait cycl
    % 2. the second dimension indicates 3 axes of rotation
    % 3. the third dimension indicates repeated strides 
    
    %this command cuts the data down to only the saggital plane of every
    %stride
    temp_saggital_thigh = squeeze( temp_thigh(:,1,:));
    
    %% load forceplate data
    temp_forceplate=temp_task.forceplates.Force;
    
    % 1.the first dimension of data is 150 points, uniformly spread
    % throughout the gait cycl
    % 2. the second dimension indicates 3 components of force vector
    % 3. the third dimension indicates repeated strides 
    
    %this command cuts the data down to only the Z (vertical) component of
    %the forceplate data
    temp_forceplateZ=squeeze( temp_forceplate(:,3,:) );
        
    figure(s);
    subplot(211); 
    plot(percentGait,temp_saggital_thigh) % thigh angle vs. percent gait
    title([sub{s},': Thigh Kinematics'])
    xlabel('Percent Gait')
    ylabel('deg')
    
    subplot(212);
    plot(percentGait,temp_forceplateZ); % forceplate vertical load vs. percent gait
    title([sub{s},': Forceplate Z'])
    xlabel('Percent Gait')
    ylabel('N / kg')

    clear temp*
end