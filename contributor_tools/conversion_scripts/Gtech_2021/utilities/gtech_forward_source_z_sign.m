function direction = gtech_forward_source_z_sign(markers, stride_time)
% Orient the laboratory Z axis using measured anterior/posterior pelvis markers.
% This is a signed laboratory axis, not a rotated anatomical frame. It is only
% defined for a complete straight cycle whose horizontal anterior vector is
% consistently Z-dominant. Missing markers, turns and non-Z paths stay unknown.
direction = NaN;
if isempty(markers) || ~istable(markers) || isempty(stride_time), return; end
required = {'Header','L_ASIS_x','R_ASIS_x','L_PSIS_x','R_PSIS_x', ...
    'L_ASIS_z','R_ASIS_z','L_PSIS_z','R_PSIS_z'};
if ~all(ismember(required, markers.Properties.VariableNames)), return; end
clock = markers.Header;
if any(~isfinite(clock)) || any(diff(clock) <= 0), return; end
if stride_time(1) < clock(1) || stride_time(end) > clock(end), return; end
mask = clock >= stride_time(1) & clock <= stride_time(end);
if sum(mask) < 2, return; end
x = (markers.L_ASIS_x(mask) + markers.R_ASIS_x(mask) ...
    - markers.L_PSIS_x(mask) - markers.R_PSIS_x(mask)) / 2;
z = (markers.L_ASIS_z(mask) + markers.R_ASIS_z(mask) ...
    - markers.L_PSIS_z(mask) - markers.R_PSIS_z(mask)) / 2;
if any(~isfinite(x)) || any(~isfinite(z)) || any(abs(z) <= abs(x)), return; end
if all(z > 0), direction = 1; elseif all(z < 0), direction = -1; end
end
