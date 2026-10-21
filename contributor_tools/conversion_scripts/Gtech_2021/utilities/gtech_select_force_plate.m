function [plate, reason] = gtech_select_force_plate(fp, markers, stride_time, side, mode)
% Follow source Osim.correlateForcePlates geometry (heel/toe mean, 100 N).
% A clear majority must support this foot. No unused-plate right-leg default,
% peak-force guess, or waveform-based leg swap. Multiple candidates stay unknown.
plate = ''; reason = 'no_supported_plate';
if isempty(fp) || ~istable(fp) || isempty(stride_time), return; end
if strcmpi(mode, 'treadmill')
    if strcmpi(side,'right'), candidate='Treadmill_R'; else, candidate='Treadmill_L'; end
    names = strcat(candidate, {'_vx','_vy','_vz','_px','_py','_pz'});
    if all(ismember(names,fp.Properties.VariableNames)), plate=candidate; reason='named_treadmill_plate'; end
    return;
end
if isempty(markers) || ~istable(markers), reason='missing_markers'; return; end
required = {'Header'};
for leg={'L','R'}
    for marker={'Heel','Toe_Tip'}
        for axis={'x','y','z'}
            required{end+1}=[leg{1} '_' marker{1} '_' axis{1}]; %#ok<AGROW>
        end
    end
end
if ~all(ismember(required,markers.Properties.VariableNames)) || ...
        ~ismember('Header',fp.Properties.VariableNames), reason='missing_channels'; return; end
ft=fp.Header; mt=markers.Header;
if any(~isfinite(ft)) || any(diff(ft)<=0) || any(~isfinite(mt)) || any(diff(mt)<=0)
    reason='invalid_clock'; return;
end
mask=mt>=stride_time(1) & mt<=stride_time(end) & mt>=ft(1) & mt<=ft(end);
if sum(mask)<2, reason='insufficient_clock_overlap'; return; end
clock=mt(mask);
left=(markers{mask,{'L_Heel_x','L_Heel_y','L_Heel_z'}}+ ...
      markers{mask,{'L_Toe_Tip_x','L_Toe_Tip_y','L_Toe_Tip_z'}})/2000;
right=(markers{mask,{'R_Heel_x','R_Heel_y','R_Heel_z'}}+ ...
       markers{mask,{'R_Toe_Tip_x','R_Toe_Tip_y','R_Toe_Tip_z'}})/2000;
candidates={};
for name=fp.Properties.VariableNames
    if ~endsWith(name{1},'_vy'), continue; end
    prefix=extractBefore(name{1},strlength(name{1})-2);
    channels=strcat(prefix,{'_vx','_vy','_vz','_px','_py','_pz'});
    if ~all(ismember(channels,fp.Properties.VariableNames)), continue; end
    force=interp1(ft,fp.(name{1}),clock,'linear',NaN);
    contact=force>100;
    if ~any(contact), continue; end
    cop=interp1(ft,fp{:,strcat(prefix,{'_px','_py','_pz'})},clock,'linear',NaN);
    valid=all(isfinite(cop),2)&all(isfinite(left),2)&all(isfinite(right),2);
    if any(contact & ~valid), continue; end
    dl=sqrt(sum((cop(contact,:)-left(contact,:)).^2,2));
    dr=sqrt(sum((cop(contact,:)-right(contact,:)).^2,2));
    if strcmpi(side,'left'), fraction=mean(dl<dr); else, fraction=mean(dr<dl); end
    if fraction>2/3, candidates{end+1}=prefix; end %#ok<AGROW>
end
if numel(candidates)==1
    plate=candidates{1}; reason='source_marker_majority';
elseif numel(candidates)>1
    reason='multiple_supported_plates';
end
end
