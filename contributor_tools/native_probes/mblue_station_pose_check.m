function mblue_station_pose_check(options)
% Independent source reader and station API; never exports canonical anatomy.
assert(~isfile(options.output_path), 'Fresh station output required');
javaaddpath(fullfile(options.opensim_home,'sdk','Java','org-opensim-modeling.jar'));
setenv('PATH',[fullfile(options.opensim_home,'bin') ';' getenv('PATH')]);
import org.opensim.modeling.*
model=Model(options.model_path); state=model.initSystem(); coords=model.getCoordinateSet();
expected=cellstr(options.coordinate_names); assert(coords.getSize()==numel(expected),'Coordinate scope differs');
for j=1:numel(expected), assert(strcmp(char(coords.get(j-1).getName()),expected{j}),'Coordinate identity differs'); end
fid=fopen(options.ik_path,'r'); assert(fid>=0); cleaner=onCleanup(@() fclose(fid));
info=dir(options.ik_path); assert(info.bytes<=64*1024^2,'Source byte cap');
degreeFlag=''; found=false;
for n=1:101
    line=fgetl(fid); assert(ischar(line)&&numel(line)<=65536,'Invalid source header');
    token=regexp(strtrim(line),'^inDegrees\s*=\s*(yes|no)$','tokens','once');
    if ~isempty(token), assert(isempty(degreeFlag),'Duplicate degree flag'); degreeFlag=token{1}; end
    if strcmpi(strtrim(line),'endheader'), found=true; break; end
end
assert(found && ~isempty(degreeFlag),'Explicit source units required');
labels=strsplit(strtrim(fgetl(fid))); assert(strcmp(labels{1},'time') && numel(unique(labels))==numel(labels),'Invalid source columns');
columns=zeros(1,numel(expected));
for j=1:numel(expected)
    hit=find(strcmp(labels,expected{j})); assert(numel(hit)==1,'Missing source coordinate'); columns(j)=hit;
end
bodies={'pelvis','femur_r','tibia_r','calcn_r','femur_l','tibia_l','calcn_l'};
points=[0 0 0;1 0 0;0 1 0;0 0 1];
% Force row shape independently of jsondecode cell orientation.
names=[{'source_time_s'},reshape(strcat('coordinate_',expected),1,[])];
for b=1:7
    for p=1:4
        names=[names,strcat(bodies{b},'_station',num2str(p-1),{'_x','_y','_z'})]; %#ok<AGROW>
    end
end
rows=zeros(options.max_rows,numel(names)); count=0; sourceCount=0; previous=-Inf;
while true
    line=fgetl(fid); if ~ischar(line),break;end
    assert(numel(line)<=65536,'Source line cap');
    sourceCount=sourceCount+1; assert(sourceCount<=200000,'Source row cap');
    tokens=strsplit(strtrim(line)); assert(numel(tokens)==numel(labels),'Source row width');
    values=str2double(tokens); t=values(1); assert(isfinite(t)&&t>previous,'Invalid clock'); previous=t;
    if t<options.start_s || t>options.end_s,continue;end
    count=count+1; assert(count<=options.max_rows,'Selected row cap');
    q=values(columns); assert(all(isfinite(q)),'Nonfinite coordinates');
    if strcmp(degreeFlag,'yes'), q(logical(options.rotational))=q(logical(options.rotational))*pi/180;end
    state.setTime(t);
    for j=1:numel(expected)
        c=coords.get(j-1);
        if c.getLocked(state),assert(abs(c.getValue(state)-q(j))<1e-8,'Locked state mismatch');
        else,c.setValue(state,q(j),false);end
    end
    model.assemble(state);model.realizePosition(state);
    for j=1:numel(expected),assert(abs(coords.get(j-1).getValue(state)-q(j))<1e-7,'Assembly changed source');end
    rows(count,1:1+numel(q))=[t,q]; offset=1+numel(q);
    for b=1:7
        body=model.getBodySet().get(bodies{b});
        for p=1:4
            v=body.findStationLocationInGround(state,Vec3(points(p,1),points(p,2),points(p,3)));
            xyz=[v.get(0),v.get(1),v.get(2)];assert(all(isfinite(xyz)),'Nonfinite station');
            rows(count,offset+(1:3))=xyz;offset=offset+3;
        end
    end
end
assert(count>=2,'Insufficient selected samples');
writetable(array2table(rows(1:count,:),'VariableNames',names),options.output_path);
end
