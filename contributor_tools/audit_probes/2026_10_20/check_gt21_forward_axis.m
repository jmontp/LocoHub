function check_gt21_forward_axis(options)
% Synthetic regression checks, separate from scientific source validation.
t = (0:4)';
markers = table(t, 'VariableNames', {'Header'});
for side = {'L','R'}
    markers.([side{1} '_ASIS_x']) = zeros(5,1);
    markers.([side{1} '_PSIS_x']) = zeros(5,1);
    markers.([side{1} '_ASIS_z']) = ones(5,1);
    markers.([side{1} '_PSIS_z']) = zeros(5,1);
end
assert(gtech_forward_source_z_sign(markers,[0,4]) == 1);
markers.L_ASIS_z(:) = -1; markers.R_ASIS_z(:) = -1;
assert(gtech_forward_source_z_sign(markers,[0,4]) == -1);
turning = markers; turning.L_ASIS_z(3:5) = 1; turning.R_ASIS_z(3:5) = 1;
assert(isnan(gtech_forward_source_z_sign(turning,[0,4])));
sideways = markers; sideways.L_ASIS_x(:) = 2; sideways.R_ASIS_x(:) = 2;
assert(isnan(gtech_forward_source_z_sign(sideways,[0,4])));
missing = markers; missing.L_ASIS_z(2) = NaN;
assert(isnan(gtech_forward_source_z_sign(missing,[0,4])));
missing = removevars(markers,'L_ASIS_z');
assert(isnan(gtech_forward_source_z_sign(missing,[0,4])));
assert(isnan(gtech_forward_source_z_sign(markers,[-1,4])));
assert(isnan(gtech_forward_source_z_sign(markers,[0,5])));
assert(isnan(gtech_forward_source_z_sign(markers,[1,1])));
invalid = markers; invalid.Header(3) = invalid.Header(2);
assert(isnan(gtech_forward_source_z_sign(invalid,[0,4])));
report = struct('status','synthetic_forward_axis_checks_passed','checks',10, ...
    'scientific_approval',false);
stream = fopen(options.output_path,'w'); assert(stream >= 0);
cleanup = onCleanup(@() fclose(stream));
fprintf(stream,'%s\n',jsonencode(report));
end
