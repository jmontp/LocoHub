function mblue_fileinfo_metadata(options)
% Only small FileInfo subject_info metadata; never load normalized arrays.
assert(~isfile(options.output_path), 'Immutable output already exists');
assert(numel(options.sources)>=1 && numel(options.sources)<=10, 'Subject admission exceeded');
result=struct('subjects',struct());
for i=1:numel(options.sources)
    source=options.sources(i);
    entry=dir(source.path);
    assert(numel(entry)==1 && entry.bytes<=1024^2, 'FileInfo exceeds1MiB');
    vars=whos('-file',source.path);
    assert(any(strcmp({vars.name},'subject_info')), 'Missing subject_info');
    loaded=load(source.path,'subject_info'); info=loaded.subject_info;
    assert(isstruct(info) && isscalar(info), 'Expected scalar metadata struct');
    selected=struct('subject',text_scalar(info.subject),'date',text_scalar(info.date));
    assert(strcmp(selected.subject,source.subject),'Source subject identity differs');
    for j=1:numel(source.fields)
        request=source.fields(j);
        assert(any(strcmp(request.condition,{'bare','exo'})), 'Unknown condition');
        selected.(request.condition).(request.task).(request.key)=text_scalar(info.(request.condition).(request.task).(request.key));
    end
    result.subjects.(source.subject)=selected;
end
encoded=jsonencode(result);
assert(numel(encoded)<=1024^2,'Metadata JSON admission exceeded');
fid=fopen(options.output_path,'w');assert(fid~=-1,'Cannot create metadata output');
cleanup=onCleanup(@()fclose(fid));fwrite(fid,encoded,'char');
end

function value=text_scalar(input)
assert((isstring(input)&&isscalar(input)) || (ischar(input)&&isrow(input)), 'Expected scalar source text');
value=char(input);assert(~isempty(value)&&strcmp(value,strtrim(value)),'Empty or padded source text');
assert(isempty(regexp(value,'[/\\\r\n]','once')) && ~any(strcmp(value,{'.','..'})), 'Unsafe source text');
end
