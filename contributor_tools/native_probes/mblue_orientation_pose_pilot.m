function mblue_orientation_pose_pilot(options)
% One source-window derivation using native OpenSim body transforms.
% These explicitly defined projected body axes are not measured orientations.
assert(~isfile(options.output_path), 'Immutable output already exists');
javaaddpath(fullfile(options.opensim_home, 'sdk', 'Java', 'org-opensim-modeling.jar'));
setenv('PATH', [fullfile(options.opensim_home, 'bin') ';' getenv('PATH')]);
import org.opensim.modeling.*
model = Model(options.model_path);
state = model.initSystem();
storage = Storage(options.ik_path);
assert(storage.getSize() <= 200000, 'Source row admission exceeded');
model.getSimbodyEngine().convertDegreesToRadians(storage);
labels = storage.getColumnLabels();
coordinates = model.getCoordinateSet();
column = zeros(coordinates.getSize(), 1);
for j = 0:coordinates.getSize()-1
    name = char(coordinates.get(j).getName());
    matches = [];
    for k = 1:labels.getSize()-1
        if strcmp(char(labels.get(k)), name), matches(end+1) = k-1; end %#ok<AGROW>
    end
    assert(numel(matches) == 1, 'Every model coordinate needs one source column');
    column(j+1) = matches;
end
% Femur/tibia local -Y longitudinal axis; calcaneus local +X forward axis.
body_names = {'femur_r','tibia_r','calcn_r','femur_l','tibia_l','calcn_l'};
body_axes = [0 -1 0;0 -1 0;1 0 0;0 -1 0;0 -1 0;1 0 0];
rows = zeros(options.max_rows, 1+3+6*4); count = 0;
for i = 0:storage.getSize()-1
    vector = storage.getStateVector(i); t = vector.getTime();
    if t < options.start_s || t > options.end_s, continue; end
    count = count+1; assert(count <= options.max_rows, 'Pilot window row admission exceeded');
    values = vector.getData(); state.setTime(t);
    for j = 0:coordinates.getSize()-1
        value = values.get(column(j+1)); assert(isfinite(value), 'Nonfinite coordinate');
        coordinate = coordinates.get(j);
        if coordinate.getLocked(state)
            assert(abs(coordinate.getValue(state)-value) < 1e-8, 'Source disagrees with locked coordinate');
        else
            coordinate.setValue(state, value, false);
        end
    end
    model.assemble(state);
    for j = 0:coordinates.getSize()-1
        assert(abs(coordinates.get(j).getValue(state)-values.get(column(j+1))) < 1e-7, ...
            'Assembly changed source coordinate; inspect constraints');
    end
    model.realizePosition(state);
    heading3 = model.getBodySet().get('pelvis').expressVectorInGround(state, Vec3(1,0,0));
    heading = [heading3.get(0),0,heading3.get(2)];
    assert(norm(heading)>1e-8, 'Undefined pelvis-forward horizontal projection');
    heading = heading/norm(heading);
    rows(count,1:4) = [t heading];
    for b = 1:numel(body_names)
        axis = body_axes(b,:);
        ground = model.getBodySet().get(body_names{b}).expressVectorInGround(state, Vec3(axis(1),axis(2),axis(3)));
        direction = [ground.get(0),ground.get(1),ground.get(2)];
        assert(all(isfinite(direction)) && abs(norm(direction)-1)<1e-7, 'Invalid native body-axis rotation');
        anterior = dot(direction,heading); vertical = direction(2);
        if hypot(anterior,vertical)<1e-8
            angle = NaN;
        elseif b==3 || b==6
            angle = atan2(vertical,anterior); % foot: forward-horizontal zero, toes-up positive
        else
            angle = atan2(anterior,-vertical); % limb: vertical-down zero, forward tilt positive
        end
        rows(count,4+(b-1)*4+(1:4)) = [direction angle];
    end
end
assert(count>=2, 'Insufficient source samples in pilot window');
rows = rows(1:count,:); assert(all(diff(rows(:,1))>0), 'Source time must strictly increase');
names = {'source_time_s','heading_ground_x','heading_ground_y','heading_ground_z'};
for b = 1:numel(body_names)
    names = [names, strcat(body_names{b},{'_axis_ground_x','_axis_ground_y','_axis_ground_z','_projected_angle_rad'})]; %#ok<AGROW>
end
writetable(array2table(rows, 'VariableNames',names), options.output_path);
fprintf('Native OpenSim pose pilot: %d source samples, six body axes\n', count);
end
