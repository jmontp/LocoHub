%% Walking Biomechanics Data Set (WBDS) analysis.
% Claudiane A Fukuchi claufukuchi@gmail.com

% This supplemental material presents a script that exemplifies the basic data analysis
% steps taken to calculate the discrete variables presented in the companion manuscript.

% In addition, it demonstrates plots of angles, moments, and ground
% reaction force curves.

% Some of the steps have been reduced to minimize clutter, but the user
% should be able to adapt this code to any given file structure.
clc, clear all, close all

% Select the directory where the unzipped files downloaded from Figshare are located
fileDir = uigetdir;

%% Exploratory data analysis
% Determine what metadata file type to be imported as a table
T = readtable([fileDir filesep 'WBDSinfo.xlsx'],'FileType','spreadsheet',...
    'ReadVariableNames',true,'ReadRowNames',false,'Sheet','Planilha1');

% Remove duplicate rows based on Subject column
[~,ind] = unique(T(:,1),'rows');
Tnew = T(ind,:);
Tnew = Tnew(1:43-1,:);

%% Summary demographics data
% Anthropometric information of mean (Age, Mass, and Height), by AgeGroup and Gender
varfun(@mean,Tnew,'InputVariables',{'Age','Mass','Height'},'GroupingVariables',{'AgeGroup','Gender'})

%% Plotting the distribution of demographics
figure
[H,AX,BigAx] =gplotmatrix([Tnew.Age,Tnew.Mass,Tnew.Height],[],Tnew.AgeGroup,[]);

title(BigAx,'Distribution of Anthropometrics')

% Axes lables
AX(1,1).YLabel.String = 'Age';
AX(2,1).YLabel.String = 'Mass';
AX(3,1).YLabel.String = 'Height';

AX(3,1).XLabel.String = 'Age';
AX(3,2).XLabel.String = 'Mass';
AX(3,3).XLabel.String = 'Height';

%% Example of batching processing the data. This can be used to open the processed files and generate plots of angles, moments, and GRFs.
nsubjsY = 24; % number of subjects in the Young Adult group
nsubjsO = 18; % number of subjects in the Old Adult group

speedlabel    = {'Slow','Comf','Fast'}; % Overground walking speeds

% Parameters to perform exploration of walking biomechanics data
if 1
    % Overground condition
    Condition = 'O';
    speed     = {'S','C','F'}; % walking speeds
    
    corR =[0.6196 0.7922 0.8824   0.4196 0.6824 0.8392   0.2588 0.5725 0.7765];
else
    % Treadmill condition
    Condition = 'T';
    speed     = [1:8]; % walking speeds
    
    corR =[0.9686 0.9843 1.0000   0.8706 0.9216 0.9686   0.7765 0.8588 0.9373,...
        0.6196 0.7922 0.8824   0.4196 0.6824 0.8392   0.2588 0.5725 0.7765,...
        0.1294 0.4431 0.7098   0.0314 0.2706 0.5804];
end

axesXYZ   = {'Z','X','Y'}; % Reference system
varType   = {'Angle','Moment','GRF'}; % Biomechanical variable types
units     = {'[º]','[Nm/kg]','[N/kg]'};

varType2 = {'ang','knt'}; % type of biomechanical variables

% Parameters for plotting data
corR = reshape(corR,3,length(speed))';

jointsA    = {'Pelvis','Hip','Knee','Ankle','Foot'}; % lower extremity joints/segments - Angles
jointsT    = {'Hip','Knee','Ankle'}; % lower extremity joints/segments - Moments

% Re-arrange order of direction to reflect sagittal, frontal, and
% transverse planes
orderXYZ = [3 1 2];

%% Angular kinematics for pelvis, hip, knee, ankle and foot
% Labels of graph axes
planesA = {'sagittal';'frontal';'transverse'};

ylabelA = {'POST(-)/ANT(+)','ER(-)/IR(+)','DOWN(-)/UP(+)',...
    'ABD(-)/ADD(+)','ER(-)/IR(+)','EXT(-)/FLX(+)',...
    'ABD(-)/ADD(+)','ER(-)/IR(+)','EXT(-)/FLX(+)',...
    'EVE(-)/INV(+)','ABD(-)/ADD(+)','PF(-)/DF(+)',...
    'EV(-)/INV(+)','ER(-)/IR(+)','PF(-)/DF(+)'};

dirA    = {'Pelvic Obliquity','Pelvic Rotation','Pelvic Tilt',...
    'Hip Add/Abduction','Hip Int/External Rotation','Hip Flexion/Extension',...
    'Knee Add/Abduction','Knee Int/External Rotation','Knee Flx/Extension',...
    'Ankle Inv/Eversion','Ankle Add/Abduction','Ankle Dorsi/Plantarflexion',...
    'Foot Inv/Eversion','Foot Int/External Rotation','Foot DF/Plantarflexion'};

yaxisLim = [0 16 -10 10 -10 10 -20 40 -10 10 -20 5 -20 100 -10 10 -30 0 -20 20 -10 20 0 30 -100 50 -10 20 0 22];

hcurve = []; %preallocating

hwb = waitbar(0,'Please wait...');

figure(1)
figsize = get(0,'screensize');
set(gcf,'position',figsize);

for ij = 1:length(jointsA)
    for xyz = 1:length(axesXYZ)
        varName = strcat('R',jointsA{ij},'Angle',...
            axesXYZ{xyz});
        for igs = 1:length(speed)
            xXx = []; %create empty array
            for isubj = 1:nsubjsY
                
                % Import files
                subLabel = ['WBDS' num2str(isubj,'%02i')]; % Subject label
                
                switch Condition
                    case 'O'
                        xVn = importdata([fileDir filesep subLabel 'walkO' speed{igs} 'ang.txt']);
                    case 'T'
                        xVn = importdata([fileDir filesep subLabel 'walkT0' num2str(igs) 'ang.txt']);
                end
                
                % Find the column corresponding to the variable based on the header
                iVar = find(strcmp(varName,xVn.colheaders));
                xX = xVn.data(:,iVar);
                xXx = [xXx xX]; % Concatenate data of different subjects
            end
            
            angA = nanmean(xXx,2); % average curves across subjects
            
            % Generate the average curves across subjects
            time = xVn.data(:,1); % time normalized vector
            subplot(5,3,(3*ij-3)+xyz)
            
            % Ploting average curve across subjects
            
            hcurve = plot(time,angA,'Color',corR(igs,:),'linewidth',2); grid on; hold on;
            
            if (strcmp(Condition,'T') && igs==5) || (strcmp(Condition,'O') && igs==2)
                set(hcurve,'linestyle',':')
            end
            
            % Set y-axis limit
            ylim([yaxisLim((6*ij-6)+2*xyz-1) yaxisLim((6*ij-6)+2*xyz)])
            xlim([0 100]) % set x-axis limit
            xlabel('Gait cycle [%]'), ylabel([ylabelA{(3*ij-3)+orderXYZ(xyz)} ' [º]'])
            title([dirA{(3*ij-3)+orderXYZ(xyz)}],'FontSize',15)
            hleg(igs) = hcurve;
            
            % Creating legend for the curves
            switch Condition
                case 'O'
                    legText{igs} = strcat(speedlabel{igs});
                case 'T'
                    legText{igs} = strcat(['T0' num2str(igs)]);
            end
            
            wbD = length(jointsA)*length(axesXYZ)*length(speed)*nsubjsY;
            wbN = (nsubjsY*length(speed)*length(axesXYZ))*ij-(nsubjsY*length(speed)*length(axesXYZ)) + (nsubjsY*length(speed))*xyz-(nsubjsY*length(speed)) + (nsubjsY*igs-nsubjsY)+isubj;
            waitbar(wbN / wbD)
            
        end
    end
end
% Legend of the graphs
legend(hleg,legText)
close(hwb)
clear hleg

%% Joint moments for hip, knee and ankle
% Labels of graph axes
ylabelM = {'ADD(-)/ABD(+)','INT(-)/EXT(+)','EXT(-)/FLX(+)',...
    'ADD(-)/ABD(+)','INT(-)/EXT(+)','FLX(-)/EXT(+)',...
    'INV(-)/EVE(+)','ADD(-)/ABD(+)','DF(-)/PF(+)'};

dirM    = {'Hip Abd/Adduction','Hip Ext/Internal Rotation','Hip Flexion/Extension',...
    'Knee Abd/Adduction','Knee Ext/Internal Rotation','Knee Ext/Flexion',...
    'Ankle Ev/Inversion','Ankle Abd/Adduction','Ankle PF/Dorsiflexion'};

yaxisLim = [-1.5 1 -.5 1.5 -.4 .5 -1 1.5 -.5 1 -.2 .5 -.5 2 -.2 .4 -.2 1];

hcurve = []; %preallocating

hwb = waitbar(0,'Please wait...');
figure(2)
figsize = get(0,'screensize');
set(gcf,'position',figsize);

for ij = 1:length(jointsT)
    for xyz = 1:length(axesXYZ)
        varName = strcat('R',jointsT{ij},'Moment',...
            axesXYZ{xyz});
        for igs = 1:length(speed)
            xXx = []; %create empty array
            for isubj = 1:nsubjsY
                
                % Import files
                subLabel = ['WBDS' num2str(isubj,'%02i')]; % Subject label
                
                switch Condition
                    case 'O'
                        xVn = importdata([fileDir filesep subLabel 'walkO' speed{igs} 'knt.txt']);
                    case 'T'
                        xVn = importdata([fileDir filesep subLabel 'walkT0' num2str(igs) 'knt.txt']);
                end
                
                % Find the column corresponding to the variable based on the header
                iVar = find(strcmp(varName,xVn.colheaders));
                xX = xVn.data(:,iVar);
                xXx = [xXx xX]; % Concatenate data of different subjects
            end
            
            momM = nanmean(xXx,2); % average curves across subjects
            
            % Generate the average curves across subjects
            time = xVn.data(:,1); % time normalized vector
            subplot(3,3,(3*ij-3)+xyz)
            
            % Plotting average curve across subjects
            hcurve = plot(time,momM,'Color',corR(igs,:),'linewidth',2); grid on; hold on;
            
            if (strcmp(Condition,'T') && igs==5) || (strcmp(Condition,'O') && igs==2)
                set(hcurve,'linestyle',':')
            end
            
            % Set y-axis limit
            ylim([yaxisLim((6*ij-6)+2*xyz-1) yaxisLim((6*ij-6)+2*xyz)])
            xlim([0 100]) % set x-axis limit
            xlabel('Gait cycle [%]'), ylabel([ylabelM{(3*ij-3)+orderXYZ(xyz)} ' Nm/kg'])
            title([dirM{(3*ij-3)+orderXYZ(xyz)}],'FontSize',15)
            hleg(igs) = hcurve;
            
            % Creating legend for the curves
            switch Condition
                case 'O'
                    legText{igs} = strcat(speedlabel{igs});
                case 'T'
                    legText{igs} = strcat(['T0' num2str(igs)]);
            end
            
            wbD = length(jointsT)*length(axesXYZ)*length(speed)*nsubjsY;
            wbN = (nsubjsY*length(speed)*length(axesXYZ))*ij-(nsubjsY*length(speed)*length(axesXYZ)) + (nsubjsY*length(speed))*xyz-(nsubjsY*length(speed)) + (nsubjsY*igs-nsubjsY)+isubj;
            waitbar(wbN / wbD)
            
        end
    end
end
% Legend of the graphs
legend(hleg,legText)
close(hwb)
clear hleg

%% Making figure displaying Ground reaction forces data
planesA = {'sagittal';'frontal';'transverse'};
ylabelGRF = {'BREAK(-)/PROP(+)','INF(-)/SUP(+)','LAT(-)/MED(+)'};
dirGRF    = {'ANTERIOR-POSTERIOR','VERTICAL','MEDIAL-LATERAL'};

yaxisLim = [-.6 1.4 -3 3 0 14];

hcurve = []; %preallocating

hwb = waitbar(0,'Please wait...');

figure(3)
figsize = get(0,'screensize');
set(gcf,'position',figsize);

for icond = 1:2
    if icond==1;
        speed  = [1:8]; % walking speeds treadmill
        corR =[0.9686 0.9843 1.0000   0.8706 0.9216 0.9686   0.7765 0.8588 0.9373,...
            0.6196 0.7922 0.8824   0.4196 0.6824 0.8392   0.2588 0.5725 0.7765,...
            0.1294 0.4431 0.7098   0.0314 0.2706 0.5804];
    else
        speed  = {'S','C','F'}; % walking speeds overground
        corR =[0.6196 0.7922 0.8824   0.4196 0.6824 0.8392   0.2588 0.5725 0.7765];
    end
    
    corR = reshape(corR,3,length(speed))';
    
    for xyz = 1:length(axesXYZ)
        varName = strcat('RGRF',axesXYZ{xyz});
        
        hleg=[];legText=[];
        for igs = 1:length(speed)
            xXx = []; %create empty array
            for isubj = 1:nsubjsY
                
                % Import files
                subLabel = ['WBDS' num2str(isubj,'%02i')]; % Subject label
                
                if icond==2
                    xVn = importdata([fileDir filesep subLabel 'walkO' speed{igs} 'knt.txt']);
                else
                    xVn = importdata([fileDir filesep subLabel 'walkT0' num2str(igs) 'knt.txt']);
                end
                
                % Find the column corresponding to the variable based on the header
                iVar = find(strcmp(varName,xVn.colheaders));
                xX = xVn.data(:,iVar);
                xXx = [xXx xX]; % Concatenate data of different subjects
            end
            
            grfM = nanmean(xXx,2); % average curves across subjects
            
            % Generate the average curves across subjects
            time = xVn.data(:,1); % time normalized vector
            subplot(2,3,(3*icond-3)+xyz)
            
            % Plotting average curve across subjects
            hcurve = plot(time,grfM,'Color',corR(igs,:),'linewidth',2); grid on; hold on;
            
            if (icond==1 && igs==5) || (icond==2 && igs==2)
                set(hcurve,'linestyle',':')
            end
            
            % Set ylim
            ylim([yaxisLim(2*xyz-1) yaxisLim(2*xyz)])
            xlim([0 100])
            xlabel('Gait cycle [%]'), ylabel([ylabelGRF{orderXYZ(xyz)} ' [N/kg]'])
            title(['GRF ' dirGRF{orderXYZ(xyz)}],'FontSize',15)
            hleg(igs) = hcurve;
            
            % Creating legend for the curves
            if icond==2
                legText{igs} = strcat(speedlabel{igs});
            else
                legText{igs} = strcat(['T0' num2str(igs)]);
            end
            
            % Waitbar
            wbD = 2*length(axesXYZ)*length(speed)*nsubjsY;
            wbN = (nsubjsY*length(speed)*length(axesXYZ))*icond-(nsubjsY*length(speed)*length(axesXYZ)) + (nsubjsY*length(speed))*xyz-(nsubjsY*length(speed)) + (nsubjsY*igs-nsubjsY)+isubj;
            waitbar(wbN / wbD)
            
        end
    end
    % Legend of the graphs
    legend(hleg,legText)
end
close(hwb) %close waitbar
clear hleg

%% Plotting mean and 1 std for Young and Old Adult right Angles at the Sagittal Plane
x = linspace(0,100,101)';
ylabelA = {'Pelvic Tilt [º]','Hip Flexion [º]','Knee Flexion [º]','Ankle Dorsiflexion [º]'};
velO    = {'Slow','Comfortable','Fast'};
velT    = {'T01','T02','T03','T04','T05','T06','T07','T08'};

hcurve = [];

switch Condition
    case 'O'
        speed = {'S','C','F'};
    case 'T'
        speed = [1:8];
end

figure(4)
figsize = get(0,'screensize');
set(gcf,'position',figsize);

for igrp = 1:2
    % Number indices of subjects
    if igrp==1
        iisubjs = 1:24; %Young
        cor = [0.6 0.6 0.6]; % Grey
        corAVG = [0 0 0]; % Black
    else
        iisubjs = 25:42; %Older
        cor = [0 0 1]; % Blue
        corAVG = cor;
    end
    
    for ij = 1:length(jointsA)-1 % without foot segment
        varName = strcat('R',jointsA{ij},'AngleZ');
        
        for igs = 1:length(speed)
            xXx = [];
            
            for isj = iisubjs
                
                % Import files (Young group)
                subLabel = ['WBDS' num2str(isj,'%02i')]; % Subject label
                
                switch Condition
                    case 'O'
                        xVn = importdata([fileDir filesep subLabel 'walkO' speed{igs} 'ang.txt']);
                        nGS = 3;
                    case 'T'
                        if (isj == 32 || isj == 39) && igs > 6
                            continue
                            
                        elseif (isj == 28 || isj == 29 || isj == 36 || isj == 37) && igs > 7;
                            continue
                        end
                        
                        xVn = importdata([fileDir filesep subLabel 'walkT0' num2str(igs) 'ang.txt']);
                        nGS = 8;
                end
                
                % Find the column corresponding to the variable based on the header
                iVar = find(strcmp(varName,xVn.colheaders));
                xX = xVn.data(:,iVar);
                xXx = [xXx xX]; % Concatenate data of different subjects
                
            end
            
            angAA = nanmean(xXx,2); % average curves across subjects
            sdAA = nanstd(xXx,0,2); % std curves across subjects
            meanPlusSTD = angAA + sdAA; meanMinusSTD = angAA - sdAA;
            
            subplot(4,nGS,(nGS*ij-nGS)+igs)
            hFill = fill([x',fliplr(x')], [meanPlusSTD', fliplr(meanMinusSTD')],cor,'EdgeAlpha',.5,'FaceAlpha',.5); hold on;
            
            havg = plot(x, angAA,'Color',corAVG,'linewidth',2); grid on;
            
            switch Condition
                case 'O'
                    if ij==1 && igs==1 || ij==1 && igs==2 || ij==1 && igs==3
                        title(velO(igs),'FontSize',15)
                    end
                    if ij==1 && igs==1 || ij==2 && igs==1 || ij==3 && igs==1 || ij==4 && igs==1
                        ylabel(ylabelA(ij))
                    end
                    if ij==4 && igs==1 || ij==4 && igs==2 || ij==4 && igs==3
                        xlabel('Gait cycle [%]')
                    end
                    
                    % Set ylim
                    if ij==1 && igs==1 || ij==1 && igs==2 || ij==1 && igs==3
                        ylim([-10 30]);
                    end
                    if ij==2 && igs==1 || ij==2 && igs==2 || ij==2 && igs==3
                        ylim([-22 50]);
                    end
                    if ij==3 && igs==1 || ij==3 && igs==2 || ij==3 && igs==3
                        ylim([-10 80]);
                    end
                    if ij==4 && igs==1 || ij==4 && igs==2 || ij==4 && igs==3
                        ylim([-25 20]);
                    end
                    
                case 'T'
                    if ij==1 && igs==1 || ij==1 && igs==2 || ij==1 && igs==3 || ij==1 && igs==4 || ij==1 && igs==5 || ij==1 && igs==6 || ij==1 && igs==7 || ij==1 && igs==8
                        title(velT(igs),'FontSize',15)
                    end
                    if ij==1 && igs==1 || ij==2 && igs==1 || ij==3 && igs==1 || ij==4 && igs==1
                        ylabel(ylabelA(ij))
                    end
                    if ij==4 && igs==1 || ij==4 && igs==2 || ij==4 && igs==3 || ij==4 && igs==4 || ij==4 && igs==5 || ij==4 && igs==6 || ij==4 && igs==7 || ij==4 && igs==8
                        xlabel('Gait cycle [%]')
                    end
                    
                    % Set ylim
                    if ij==1 && igs==1 || ij==1 && igs==2 || ij==1 && igs==3 || ij==1 && igs==4 || ij==1 && igs==5 || ij==1 && igs==6 || ij==1 && igs==7 || ij==1 && igs==8
                        ylim([-10 30]);
                    end
                    if ij==2 && igs==1 || ij==2 && igs==2 || ij==2 && igs==3 || ij==2 && igs==4 || ij==2 && igs==5 || ij==2 && igs==6 || ij==2 && igs==7 || ij==2 && igs==8
                        ylim([-20 50]);
                    end
                    if ij==3 && igs==1 || ij==3 && igs==2 || ij==3 && igs==3 || ij==3 && igs==4 || ij==3 && igs==5 || ij==3 && igs==6 || ij==3 && igs==7 || ij==3 && igs==8
                        ylim([-10 80]);
                    end
                    if ij==4 && igs==1 || ij==4 && igs==2 || ij==4 && igs==3 || ij==4 && igs==4 || ij==4 && igs==5 || ij==4 && igs==6 || ij==4 && igs==7 || ij==4 && igs==8
                        ylim([-25 20]);
                    end
            end
        end
    end
    hleg(igrp) = havg;
    
end
legend(hleg,{'Young Adult','Older Adult'});
set(legend, 'position',[.925 0.878 0.05 0.05]);
legend('boxoff')

%% Load and visualize the marker position during standing calibration trial for subject 1
% Import static trial data
xS = importdata([fileDir filesep 'WBDS01static1.txt']);

timeS = xS.data(:,1);

markerLabelS = xS.colheaders(2:end);
markerLabelS2 = markerLabelS(1:3:end-2);

dataS = mean(xS.data(:,2:end),1);

% 3D plot of static markers
figure ('units','normalized','outerposition',[0 0 1 1])
subplot(1,2,1)

for i = 1:size(dataS,2)/3
    % Showing standing calibration markers
    h1(i) = plot3(dataS(:,3*i),dataS(:,3*i-2),dataS(:,3*i-1),'ro'); hold on
    
    % Assigning label to markers
    text(dataS(:,3*i),dataS(:,3*i-2),dataS(:,3*i-1),[' ' num2str(i)])
    
    mLabel = markerLabelS2{i};
    leg{i} = [num2str(i) '-' mLabel(1:end-1)];
end

% Plotting Lab coordinate system
h2 = plot3([500 500+250],[500 500],[0 0],'b-');
h3 = plot3([500 500],[500 500+250],[0 0],'r-');
h4 = plot3([500 500],[500 500],[0 250],'g-');

% Lines connecting markers
% Pelvis
h5 = plot3([dataS(3) dataS(6)],[dataS(1) dataS(4)],[dataS(2) dataS(5)],'k-');
h6 = plot3([dataS(3) dataS(9)],[dataS(1) dataS(7)],[dataS(2) dataS(8)],'k-');
h7 = plot3([dataS(6) dataS(12)],[dataS(4) dataS(10)],[dataS(5) dataS(11)],'k-');
h8 = plot3([dataS(9) dataS(12)],[dataS(7) dataS(10)],[dataS(8) dataS(11)],'k-');
h9 = plot3([dataS(6) dataS(15)],[dataS(4) dataS(13)],[dataS(5) dataS(14)],'k-');
h10 = plot3([dataS(3) dataS(18)],[dataS(1) dataS(16)],[dataS(2) dataS(17)],'k-');
h11 = plot3([dataS(3) dataS(21)],[dataS(1) dataS(19)],[dataS(2) dataS(20)],'k-');
h12 = plot3([dataS(21) dataS(18)],[dataS(19) dataS(16)],[dataS(20) dataS(17)],'k-');
h13 = plot3([dataS(18) dataS(9)],[dataS(16) dataS(7)],[dataS(17) dataS(8)],'k-');
h14 = plot3([dataS(12) dataS(15)],[dataS(10) dataS(13)],[dataS(11) dataS(14)],'k-');
h15 = plot3([dataS(15) dataS(45)],[dataS(13) dataS(43)],[dataS(14) dataS(44)],'k-');
h16 = plot3([dataS(45) dataS(6)],[dataS(43) dataS(4)],[dataS(44) dataS(5)],'k-');

% Right Thigh
h17 = plot3([dataS(21) dataS(24)],[dataS(19) dataS(22)],[dataS(20) dataS(23)],'k-');
h18 = plot3([dataS(24) dataS(27)],[dataS(22) dataS(25)],[dataS(23) dataS(26)],'k-');
h19 = plot3([dataS(27) dataS(30)],[dataS(25) dataS(28)],[dataS(26) dataS(29)],'k-');
h20 = plot3([dataS(30) dataS(69)],[dataS(28) dataS(67)],[dataS(29) dataS(68)],'k-');
h21 = plot3([dataS(69) dataS(21)],[dataS(67) dataS(19)],[dataS(68) dataS(20)],'k-');
h22 = plot3([dataS(24) dataS(69)],[dataS(22) dataS(67)],[dataS(23) dataS(68)],'k-');

% Left Thigh
h23 = plot3([dataS(45) dataS(48)],[dataS(43) dataS(46)],[dataS(44) dataS(47)],'k-');
h24 = plot3([dataS(48) dataS(51)],[dataS(46) dataS(49)],[dataS(47) dataS(50)],'k-');
h25 = plot3([dataS(51) dataS(54)],[dataS(49) dataS(52)],[dataS(50) dataS(53)],'k-');
h26 = plot3([dataS(54) dataS(78)],[dataS(52) dataS(76)],[dataS(53) dataS(77)],'k-');
h27 = plot3([dataS(78) dataS(45)],[dataS(76) dataS(43)],[dataS(77) dataS(44)],'k-');
h28 = plot3([dataS(78) dataS(48)],[dataS(76) dataS(46)],[dataS(77) dataS(47)],'k-');

% Right shank and foot
h29 = plot3([dataS(27) dataS(33)],[dataS(25) dataS(31)],[dataS(26) dataS(32)],'k-');
h30 = plot3([dataS(69) dataS(72)],[dataS(67) dataS(70)],[dataS(68) dataS(71)],'k-');
h31 = plot3([dataS(72) dataS(33)],[dataS(70) dataS(31)],[dataS(71) dataS(32)],'k-');
h32 = plot3([dataS(33) dataS(36)],[dataS(31) dataS(34)],[dataS(32) dataS(35)],'k-');
h33 = plot3([dataS(72) dataS(36)],[dataS(70) dataS(34)],[dataS(71) dataS(35)],'k-');
h34 = plot3([dataS(33) dataS(42)],[dataS(31) dataS(40)],[dataS(32) dataS(41)],'k-');
h35 = plot3([dataS(42) dataS(75)],[dataS(40) dataS(73)],[dataS(41) dataS(74)],'k-');
h36 = plot3([dataS(75) dataS(39)],[dataS(73) dataS(37)],[dataS(74) dataS(38)],'k-');
h37 = plot3([dataS(39) dataS(72)],[dataS(37) dataS(70)],[dataS(38) dataS(71)],'k-');
h38 = plot3([dataS(36) dataS(42)],[dataS(34) dataS(40)],[dataS(35) dataS(41)],'k-');
h39 = plot3([dataS(39) dataS(36)],[dataS(37) dataS(34)],[dataS(38) dataS(35)],'k-');
h40 = plot3([dataS(75) dataS(36)],[dataS(73) dataS(34)],[dataS(74) dataS(35)],'k-');

% Left shank and foot
h41 = plot3([dataS(51) dataS(57)],[dataS(49) dataS(55)],[dataS(50) dataS(56)],'k-');
h42 = plot3([dataS(78) dataS(81)],[dataS(76) dataS(79)],[dataS(77) dataS(80)],'k-');
h43 = plot3([dataS(57) dataS(81)],[dataS(55) dataS(79)],[dataS(56) dataS(80)],'k-');
h44 = plot3([dataS(57) dataS(60)],[dataS(55) dataS(58)],[dataS(56) dataS(59)],'k-');
h45 = plot3([dataS(81) dataS(60)],[dataS(79) dataS(58)],[dataS(80) dataS(59)],'k-');
h46 = plot3([dataS(57) dataS(66)],[dataS(55) dataS(64)],[dataS(56) dataS(65)],'k-');
h47 = plot3([dataS(66) dataS(84)],[dataS(64) dataS(82)],[dataS(65) dataS(83)],'k-');
h48 = plot3([dataS(84) dataS(63)],[dataS(82) dataS(61)],[dataS(83) dataS(62)],'k-');
h49 = plot3([dataS(63) dataS(81)],[dataS(61) dataS(79)],[dataS(62) dataS(80)],'k-');
h50 = plot3([dataS(66) dataS(60)],[dataS(64) dataS(58)],[dataS(65) dataS(59)],'k-');
h51 = plot3([dataS(63) dataS(60)],[dataS(61) dataS(58)],[dataS(62) dataS(59)],'k-');
h52 = plot3([dataS(84) dataS(60)],[dataS(82) dataS(58)],[dataS(83) dataS(59)],'k-');

set([h2 h3 h4],'Linewidth',2)
set(h1,'MarkerFaceColor',[1 0 0])

xlabel('Z-axis [mm]'), ylabel('X-axis [mm]'), zlabel('Y-axis [mm]')

axis equal
axis([450 1600 400 1250 0 1200])
grid

% Showing legend of markers
lg = legend(h1,leg);

set(lg,'Position',[0.6629 0.0906 0.1010 0.8261])
set(gca,'CameraPosition',[320.9143 9.7713e+03 5.9311e+03])

%% Import markers during walking for subject 1
if 0
    % Overground condition
    Condition = 'O';
    xD = importdata([fileDir filesep 'WBDS01walkO06Smkr.txt']);
    xF = importdata([fileDir filesep 'WBDS01walkO06Sgrf.txt']);
else
    % Treadmill condition
    Condition = 'T';
    xD = importdata([fileDir filesep 'WBDS01walkT05mkr.txt']);
    xF = importdata([fileDir filesep 'WBDS01walkT05grf.txt']);
end

timeD = xD.data(:,1); % time vector

markerLabelD = xD.colheaders(2:end);
markerLabelD2 = markerLabelD(1:3:end-2);

dataD = xD.data(:,2:end);

% Import forces during walking for subject 1
timeF = xF.data(:,1);

dataF = xF.data(:,2:end);


% Making animation
direction = {'x','y','z'};
FPids     = 1:5;
FPTids    = 1:2;

% Downsampling force data
dataFp = resample(dataF,1,2);

switch Condition
    case 'O'
        for ifp = 1:length(FPids)
            for xyz = 1:length(direction)
                fp.(['CoP' direction{xyz} num2str(FPids(ifp))]) = dataFp(:,(7*ifp-7)+xyz+3); %CoP
                fp.(['F' direction{xyz} num2str(FPids(ifp))])   = dataFp(:,(7*ifp-7)+xyz); % Forces
            end
        end
        
        % Position of the corners of the FP in the LAB
        fp.corner1_1 = [1806 0 -403];
        fp.corner2_1 = [1806 0 -3];
        fp.corner3_1 = [1206 0 -3];
        fp.corner4_1 = [1206 0 -403];
        
        fp.corner1_2 = [2409 0 -403];
        fp.corner2_2 = [2409 0 -3];
        fp.corner3_2 = [1809 0 -3];
        fp.corner4_2 = [1809 0 -403];
        
        fp.corner1_3 = [603 0 -203];
        fp.corner2_3 = [603 0 -603];
        fp.corner3_3 = [1203 0 -603];
        fp.corner4_3 = [1203 0 -203];
        
        fp.corner1_4 = [0 0 -3];
        fp.corner2_4 = [0 0 -403];
        fp.corner3_4 = [600 0 -403];
        fp.corner4_4 = [600 0 -3];
        
        fp.corner1_5 = [0 0 400];
        fp.corner2_5 = [0 0 0];
        fp.corner3_5 = [600 0 0];
        fp.corner4_5 = [600 0 400];
        
    case 'T'
        for ifpT = 1:length(FPTids)
            for xyz = 1:length(direction)
                fpT.(['CoP' direction{xyz} num2str(FPTids(ifpT))]) = dataFp(:,(7*ifpT-7)+xyz+3); %CoP
                fpT.(['F' direction{xyz} num2str(FPTids(ifpT))])   = dataFp(:,(7*ifpT-7)+xyz); % Forces
            end
        end
        
        % Treadmill dimensions
        widthT = 486;
        lengthT = 1800;
        
        % Position of the geometric center of the treadmill in the LAB
        centerTposition = [2149 9 976.7];
        
        fpT.corner1_1 = [centerTposition(1)-lengthT/2 0 centerTposition(3)-widthT/2];
        fpT.corner2_1 = [fpT.corner1_1(1) fpT.corner1_1(2) fpT.corner1_1(3)+widthT];
        fpT.corner3_1 = [fpT.corner1_1(1)+lengthT fpT.corner1_1(2) fpT.corner2_1(3)];
        fpT.corner4_1 = [fpT.corner3_1(1) fpT.corner3_1(2) fpT.corner1_1(3)];
        
        fpT.corner1_2 = [centerTposition(1)-lengthT/2 0 centerTposition(3)-widthT/2+widthT];
        fpT.corner2_2 = [fpT.corner1_2(1) fpT.corner1_2(2) fpT.corner1_2(3)+widthT];
        fpT.corner3_2 = [fpT.corner1_2(1)+lengthT fpT.corner1_2(2) fpT.corner2_2(3)];
        fpT.corner4_2 = [fpT.corner3_2(1) fpT.corner3_2(2) fpT.corner1_2(3)];
end

n2cm = .75; % Newtons to cm
figure
for i = 1:10:size(dataD,1)
    
    % Plotting markers
    plot3(dataD(i,3:3:end),dataD(i,1:3:end-2),dataD(i,2:3:end-1),'ro','MarkerFaceColor',[1 0 0]); hold on
    
    % Lines connecting markers
    % Pelvis
    h5 = plot3([dataD(i,3) dataD(i,6)],[dataD(i,1) dataD(i,4)],[dataD(i,2) dataD(i,5)],'k-');
    h6 = plot3([dataD(i,3) dataD(i,9)],[dataD(i,1) dataD(i,7)],[dataD(i,2) dataD(i,8)],'k-');
    h7 = plot3([dataD(i,6) dataD(i,12)],[dataD(i,4) dataD(i,10)],[dataD(i,5) dataD(i,11)],'k-');
    h8 = plot3([dataD(i,9) dataD(i,12)],[dataD(i,7) dataD(i,10)],[dataD(i,8) dataD(i,11)],'k-');
    h9 = plot3([dataD(i,6) dataD(i,15)],[dataD(i,4) dataD(i,13)],[dataD(i,5) dataD(i,14)],'k-');
    h10 = plot3([dataD(i,3) dataD(i,18)],[dataD(i,1) dataD(i,16)],[dataD(i,2) dataD(i,17)],'k-');
    h11 = plot3([dataD(i,3) dataD(i,21)],[dataD(i,1) dataD(i,19)],[dataD(i,2) dataD(i,20)],'k-');
    h12 = plot3([dataD(i,21) dataD(i,18)],[dataD(i,19) dataD(i,16)],[dataD(i,20) dataD(i,17)],'k-');
    h13 = plot3([dataD(i,18) dataD(i,9)],[dataD(i,16) dataD(i,7)],[dataD(i,17) dataD(i,8)],'k-');
    h14 = plot3([dataD(i,12) dataD(i,15)],[dataD(i,10) dataD(i,13)],[dataD(i,11) dataD(i,14)],'k-');
    h15 = plot3([dataD(i,15) dataD(i,45)],[dataD(i,13) dataD(i,43)],[dataD(i,14) dataD(i,44)],'k-');
    h16 = plot3([dataD(i,45) dataD(i,6)],[dataD(i,43) dataD(i,4)],[dataD(i,44) dataD(i,5)],'k-');
    
    % Right Thigh
    h17 = plot3([dataD(i,21) dataD(i,24)],[dataD(i,19) dataD(i,22)],[dataD(i,20) dataD(i,23)],'k-');
    h18 = plot3([dataD(i,24) dataD(i,27)],[dataD(i,22) dataD(i,25)],[dataD(i,23) dataD(i,26)],'k-');
    h19 = plot3([dataD(i,27) dataD(i,30)],[dataD(i,25) dataD(i,28)],[dataD(i,26) dataD(i,29)],'k-');
    
    % Left Thigh
    h20 = plot3([dataD(i,45) dataD(i,48)],[dataD(i,43) dataD(i,46)],[dataD(i,44) dataD(i,47)],'k-');
    h21 = plot3([dataD(i,48) dataD(i,51)],[dataD(i,46) dataD(i,49)],[dataD(i,47) dataD(i,50)],'k-');
    h22 = plot3([dataD(i,51) dataD(i,54)],[dataD(i,49) dataD(i,52)],[dataD(i,50) dataD(i,53)],'k-');
    
    % Right shank and foot
    h23 = plot3([dataD(i,27) dataD(i,33)],[dataD(i,25) dataD(i,31)],[dataD(i,26) dataD(i,32)],'k-');
    h24 = plot3([dataD(i,33) dataD(i,36)],[dataD(i,31) dataD(i,34)],[dataD(i,32) dataD(i,35)],'k-');
    h25 = plot3([dataD(i,33) dataD(i,42)],[dataD(i,31) dataD(i,40)],[dataD(i,32) dataD(i,41)],'k-');
    h26 = plot3([dataD(i,36) dataD(i,42)],[dataD(i,34) dataD(i,40)],[dataD(i,35) dataD(i,41)],'k-');
    h27 = plot3([dataD(i,39) dataD(i,36)],[dataD(i,37) dataD(i,34)],[dataD(i,38) dataD(i,35)],'k-');
    
    % Left shank and foot
    h28 = plot3([dataD(i,51) dataD(i,57)],[dataD(i,49) dataD(i,55)],[dataD(i,50) dataD(i,56)],'k-');
    h29 = plot3([dataD(i,57) dataD(i,60)],[dataD(i,55) dataD(i,58)],[dataD(i,56) dataD(i,59)],'k-');
    h30 = plot3([dataD(i,57) dataD(i,66)],[dataD(i,55) dataD(i,64)],[dataD(i,56) dataD(i,65)],'k-');
    h31 = plot3([dataD(i,66) dataD(i,60)],[dataD(i,64) dataD(i,58)],[dataD(i,65) dataD(i,59)],'k-');
    h32 = plot3([dataD(i,63) dataD(i,60)],[dataD(i,61) dataD(i,58)],[dataD(i,62) dataD(i,59)],'k-');
    
    % Plotting force platform corners
    switch Condition
        case 'O'
            for ifp = 1:length(FPids)
                
                % Drawing FPs
                hFPa(ifp) = plot3([fp.(['corner1_' num2str(ifp)])(3) fp.(['corner2_' num2str(ifp)])(3) fp.(['corner3_' num2str(ifp)])(3) fp.(['corner4_' num2str(ifp)])(3) fp.(['corner1_' num2str(ifp)])(3)],...
                    [fp.(['corner1_' num2str(ifp)])(1) fp.(['corner2_' num2str(ifp)])(1) fp.(['corner3_' num2str(ifp)])(1) fp.(['corner4_' num2str(ifp)])(1) fp.(['corner1_' num2str(ifp)])(1)],...
                    [fp.(['corner1_' num2str(ifp)])(2) fp.(['corner2_' num2str(ifp)])(2) fp.(['corner3_' num2str(ifp)])(2) fp.(['corner4_' num2str(ifp)])(2) fp.(['corner1_' num2str(ifp)])(2)],...
                    'k-'); hold on
                
                % Filling FP areas
                hFPb(ifp) = fill3([fp.(['corner1_' num2str(ifp)])(3) fp.(['corner2_' num2str(ifp)])(3) fp.(['corner3_' num2str(ifp)])(3) fp.(['corner4_' num2str(ifp)])(3)],...
                    [fp.(['corner1_' num2str(ifp)])(1) fp.(['corner2_' num2str(ifp)])(1) fp.(['corner3_' num2str(ifp)])(1) fp.(['corner4_' num2str(ifp)])(1)],...
                    [fp.(['corner1_' num2str(ifp)])(2) fp.(['corner2_' num2str(ifp)])(2) fp.(['corner3_' num2str(ifp)])(2) fp.(['corner4_' num2str(ifp)])(2)],...
                    [0 0 0],'FaceAlpha',.5);
            end
            
            % Plotting GRF vector
            hArrow = plot3([fp.CoPz1(i) fp.CoPz1(i)+fp.Fz1(i)/n2cm],[fp.CoPx1(i) fp.CoPx1(i)+fp.Fx1(i)/n2cm],[fp.CoPy1(i) fp.Fy1(i)/n2cm],'b-',...
                [fp.CoPz2(i) fp.CoPz2(i)+fp.Fz2(i)/n2cm],[fp.CoPx2(i) fp.CoPx2(i)+fp.Fx2(i)/n2cm],[fp.CoPy2(i) fp.Fy2(i)/n2cm],'b-',...
                [fp.CoPz3(i) fp.CoPz3(i)+fp.Fz3(i)/n2cm],[fp.CoPx3(i) fp.CoPx3(i)+fp.Fx3(i)/n2cm],[fp.CoPy3(i) fp.Fy3(i)/n2cm],'b-',...
                [fp.CoPz4(i) fp.CoPz4(i)+fp.Fz4(i)/n2cm],[fp.CoPx4(i) fp.CoPx4(i)+fp.Fx4(i)/n2cm],[fp.CoPy4(i) fp.Fy4(i)/n2cm],'b-',...
                [fp.CoPz5(i) fp.CoPz5(i)+fp.Fz5(i)/n2cm],[fp.CoPx5(i) fp.CoPx5(i)+fp.Fx5(i)/n2cm],[fp.CoPy5(i) fp.Fy5(i)/n2cm],'b-','linewidth',3);
            
            set(hFPa,'LineWidth',2)
            
            grid on
            axis equal, axis([-700 500 -100 3000 0 1000])
            
        case 'T'
            for ifpT = 1:length(FPTids)
                
                % Drawing FPs
                hFPTa(ifpT) = plot3([fpT.(['corner1_' num2str(ifpT)])(3) fpT.(['corner2_' num2str(ifpT)])(3) fpT.(['corner3_' num2str(ifpT)])(3) fpT.(['corner4_' num2str(ifpT)])(3) fpT.(['corner1_' num2str(ifpT)])(3)],...
                    [fpT.(['corner1_' num2str(ifpT)])(1) fpT.(['corner2_' num2str(ifpT)])(1) fpT.(['corner3_' num2str(ifpT)])(1) fpT.(['corner4_' num2str(ifpT)])(1) fpT.(['corner1_' num2str(ifpT)])(1)],...
                    [fpT.(['corner1_' num2str(ifpT)])(2) fpT.(['corner2_' num2str(ifpT)])(2) fpT.(['corner3_' num2str(ifpT)])(2) fpT.(['corner4_' num2str(ifpT)])(2) fpT.(['corner1_' num2str(ifpT)])(2)],...
                    'k-'); hold on
                
                % Filling FP areas
                hFPTb(ifpT) = fill3([fpT.(['corner1_' num2str(ifpT)])(3) fpT.(['corner2_' num2str(ifpT)])(3) fpT.(['corner3_' num2str(ifpT)])(3) fpT.(['corner4_' num2str(ifpT)])(3)],...
                    [fpT.(['corner1_' num2str(ifpT)])(1) fpT.(['corner2_' num2str(ifpT)])(1) fpT.(['corner3_' num2str(ifpT)])(1) fpT.(['corner4_' num2str(ifpT)])(1)],...
                    [fpT.(['corner1_' num2str(ifpT)])(2) fpT.(['corner2_' num2str(ifpT)])(2) fpT.(['corner3_' num2str(ifpT)])(2) fpT.(['corner4_' num2str(ifpT)])(2)],...
                    [0 0 0],'FaceAlpha',.5);
            end
            
            % Plotting GRF vector
            hArrow = plot3([fpT.CoPz1(i) fpT.CoPz1(i)+fpT.Fz1(i)/n2cm],[fpT.CoPx1(i) fpT.CoPx1(i)+fpT.Fx1(i)/n2cm],[fpT.CoPy1(i) fpT.Fy1(i)/n2cm],'b-',...
                [fpT.CoPz2(i) fpT.CoPz2(i)+fpT.Fz2(i)/n2cm],[fpT.CoPx2(i) fpT.CoPx2(i)+fpT.Fx2(i)/n2cm],[fpT.CoPy2(i) fpT.Fy2(i)/n2cm],'b-','linewidth',3);
            
            set(hFPTa,'LineWidth',2)
            
            grid on
            axis equal, axis([400 2000 1000 3200 0 1500])
    end
    hold off
    pause(0.1)
end