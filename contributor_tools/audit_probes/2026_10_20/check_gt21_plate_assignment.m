function check_gt21_plate_assignment(options)
% Synthetic labelled geometry: identities must override force magnitude.
t=(0:4)'; markers=table(t,'VariableNames',{'Header'}); fp=markers;
for side={'L','R'}
    x=-100; if strcmp(side{1},'R'), x=100; end
    for marker={'Heel','Toe_Tip'}
        markers.([side{1} '_' marker{1} '_x'])=repmat(x,5,1);
        markers.([side{1} '_' marker{1} '_y'])=zeros(5,1);
        markers.([side{1} '_' marker{1} '_z'])=zeros(5,1);
    end
end
for k=1:2
    prefix=sprintf('FP%d',k); x=-.1; if k==2, x=.1; end
    for component={'vx','vz','py','pz'}, fp.([prefix '_' component{1}])=zeros(5,1); end
    fp.([prefix '_vy'])=repmat(200*k,5,1); fp.([prefix '_px'])=repmat(x,5,1);
end
assert(strcmp(gtech_select_force_plate(fp,markers,[0,4],'left','stair'),'FP1'));
assert(strcmp(gtech_select_force_plate(fp,markers,[0,4],'right','stair'),'FP2'));
% Increasing opposite-foot force cannot change the left assignment.
strong=fp; strong.FP2_vy(:)=10000;
assert(strcmp(gtech_select_force_plate(strong,markers,[0,4],'left','ramp'),'FP1'));
missing=markers; missing.L_Heel_x(2)=NaN;
assert(isempty(gtech_select_force_plate(fp,missing,[0,4],'left','stair')));
unused=fp; unused.FP1_vy(:)=0;
assert(isempty(gtech_select_force_plate(unused,markers,[0,4],'left','stair')));
ambiguous=fp; ambiguous.FP1_px(:)=0;
assert(isempty(gtech_select_force_plate(ambiguous,markers,[0,4],'left','stair')));
multiple=fp;
for component={'vx','vy','vz','px','py','pz'}
    multiple.(['FP3_' component{1}])=fp.(['FP1_' component{1}]);
end
[plate,reason]=gtech_select_force_plate(multiple,markers,[0,4],'left','stair');
assert(isempty(plate) && strcmp(reason,'multiple_supported_plates'));
missing=removevars(markers,'R_Toe_Tip_z');
assert(isempty(gtech_select_force_plate(fp,missing,[0,4],'right','stair')));
report=struct('status','synthetic_plate_assignment_checks_passed','checks',8,'scientific_approval',false);
stream=fopen(options.output_path,'w');assert(stream>=0);cleanup=onCleanup(@() fclose(stream));
fprintf(stream,'%s\n',jsonencode(report));
end
