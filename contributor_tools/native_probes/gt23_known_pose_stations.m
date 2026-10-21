function gt23_known_pose_stations(options)
% Thirteen synthetic model poses only. Does not read scientific time series.
assert(~isfile(options.output_path),'Fresh output required');
javaaddpath(fullfile(options.opensim_home,'sdk','Java','org-opensim-modeling.jar'));
setenv('PATH',[fullfile(options.opensim_home,'bin') ';' getenv('PATH')]);
import org.opensim.modeling.*
model=Model(options.model_path); state=model.initSystem(); coords=model.getCoordinateSet();
target={'hip_flexion_r','knee_angle_r','ankle_angle_r','hip_flexion_l','knee_angle_l','ankle_angle_l'};
markers={'RASI','LASI','RPSI','LPSI','RKNE','RMKNE','LKNE','LMKNE','RANK','RMANK','LANK','LMANK','RCAL','LCAL','RMT1','RMT5','LMT1','LMT5'};
rows=cell(13,1); epsilon=pi/180;
for pose=1:13
    % Explicit coordinate zero pose, not an assertion of anatomical neutral.
    for j=0:coords.getSize()-1
        c=coords.get(j); assert(~c.getLocked(state),'Locked coordinate needs explicit review');
        c.setValue(state,0,false);
    end
    name='neutral';
    if pose>1
        index=floor((pose-2)/2)+1; direction=2*mod(pose-2,2)-1;
        c=coords.get(target{index}); c.setValue(state,direction*epsilon,false);
        if direction<0, suffix='minus';else,suffix='plus';end
        name=[target{index} ':' suffix];
    end
    model.assemble(state); model.realizePosition(state);
    q=struct();
    for j=1:numel(target),q.(target{j})=coords.get(target{j}).getValue(state);end
    % Reject any assembly-induced motion in untargeted coordinates too.
    for j=0:coords.getSize()-1
        c=coords.get(j); expected=0; idx=find(strcmp(target,char(c.getName())));
        if pose>1 && ~isempty(idx) && idx==index,expected=direction*epsilon;end
        assert(abs(c.getValue(state)-expected)<1e-9,'Assembly changed requested coordinate');
    end
    stations=struct();
    for j=1:numel(markers)
        m=model.getMarkerSet().get(markers{j}); v=m.getLocationInGround(state);
        stations.(markers{j})=[v.get(0),v.get(1),v.get(2)];
    end
    bodies={'femur_r','tibia_r','femur_l','tibia_l'}; names={'hip_r','knee_r','hip_l','knee_l'};
    for j=1:4
        v=model.getBodySet().get(bodies{j}).findStationLocationInGround(state,Vec3(0,0,0));
        stations.(names{j})=[v.get(0),v.get(1),v.get(2)];
    end
    rows{pose}=struct('pose',name,'coordinates',q,'stations',stations);
end
fid=fopen(options.output_path,'w');assert(fid>=0);cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'%s',jsonencode(rows));
end
