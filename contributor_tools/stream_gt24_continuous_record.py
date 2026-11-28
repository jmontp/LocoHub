"""Prepared bounded adapter for one mapped GT24 Parsed continuous recording.

No CLI or automatic execution. Requires a serial coordinator, admitted source
manifest, reviewed isolated adapter, and runtime guard. Actual equivalence pilot
is still required. Gapped source recordings fail closed pending interval policy.
"""
from contextlib import contextmanager,ExitStack
import importlib.util
import json
import math
from pathlib import Path
import sys
from contributor_tools.match_gt24_complete_intervals import ProjectedCSV
from contributor_tools.gt24_continuous_stream_windows import aligned_rows,recording_facts,halo_windows
from contributor_tools.prepare_gt24_complete_membership import source_columns,fieldnames,stat_identity

VELOCITIES=tuple(f'{joint}_{leg}_velocity' for joint in ('hip_flexion','knee_angle','ankle_angle') for leg in ('l','r'))


def selected_sources(record):
    if record['disposition']!='canonical_parsed_candidate_requires_source_audit':raise ValueError('Unmapped source cannot be canonically labeled')
    if record['exo_state'] not in ('no_exo','powered','worn_unpowered'):raise ValueError('Explicit source actuator state required')
    kinds=['angle_filt','moment_filt','grf','velocity','insole_sim','power','power_bio','exo','exo_sim']
    if record['exo_state']!='no_exo':kinds.append('moment_filt_bio')
    selected={kind:record['files'][kind] for kind in kinds if kind in record['files']}
    if not {'angle_filt','moment_filt','grf','velocity','insole_sim'}<=set(selected):raise ValueError('Required source tables absent')
    return selected


@contextmanager
def source_rows(record,guard):
    selected=selected_sources(record);readers={}
    with ExitStack() as stack:
        for kind,evidence in selected.items():
            path=Path(evidence['path'])
            if stat_identity(path)!=evidence:raise ValueError('Inventoried source changed')
            stream=stack.enter_context(path.open('rb'));available=fieldnames(stream);stream.seek(0)
            columns=sorted(available & source_columns().get(kind,{'time'}))
            readers[kind]=ProjectedCSV(stream,columns,guard)
        yield aligned_rows(readers),readers
    for evidence in selected.values():
        if stat_identity(evidence['path'])!=evidence:raise ValueError('Source changed during bounded read')


def scan(record,guard):
    with source_rows(record,guard) as (rows,readers):
        facts=recording_facts(rows,VELOCITIES)
        evidence={name:reader.evidence() for name,reader in readers.items()}
    if facts['sampling_rate_hz'] is None:
        raise ValueError('Source clock gaps/nonuniform intervals require explicit contiguous-interval policy; no derivatives across omitted transitions')
    return facts,evidence


@contextmanager
def numerical_source_rows(record,guard):
    """Use the frozen adapter's pandas parser in bounded chunks.

    Python float parsing can differ by one bit from pandas' default CSV parser.
    Keeping its parser is necessary for exact preservation of existing values.
    """
    import pandas as pd
    selected=selected_sources(record);iterators={}
    with ExitStack() as stack:
        for kind,evidence in selected.items():
            path=Path(evidence['path'])
            if stat_identity(path)!=evidence:raise ValueError('Inventoried source changed')
            with path.open('rb') as stream:available=fieldnames(stream)
            columns=sorted(available & source_columns().get(kind,{'time'}))
            if 'time' not in columns:raise ValueError('Source clock absent')
            reader=stack.enter_context(pd.read_csv(path,usecols=columns,chunksize=512))
            def values(reader=reader):
                for frame in reader:
                    guard()
                    names=list(frame.columns)
                    for values in frame.itertuples(index=False,name=None):
                        yield {name:float(value) for name,value in zip(names,values)}
            iterators[kind]=values()
        yield aligned_rows(iterators)
    for evidence in selected.values():
        if stat_identity(evidence['path'])!=evidence:raise ValueError('Source changed during bounded parser read')


def numerical_facts(rows):
    """Record NumPy's exact uniform-spacing branch over the entire rebased clock."""
    first=None;previous=None;first_step=None;exact_uniform=True
    def observed():
        nonlocal first,previous,first_step,exact_uniform
        for row in rows:
            clock=row['angle_filt']['time']
            if first is None:first=clock
            rebased=clock-first
            if previous is not None:
                step=rebased-previous
                if first_step is None:first_step=step
                elif step!=first_step:exact_uniform=False
            previous=rebased
            yield row
    facts=recording_facts(observed(),VELOCITIES)
    facts['gradient_uniform_step_s']=first_step if exact_uniform else None
    return facts


def global_gradient(values,time_s,uniform_step):
    """Preserve NumPy's full-record branch even for locally uniform windows.

    This is NumPy gradient's 1-D, edge_order=1 nonuniform formula. The independent
    audit separately implements the source finite difference in scalar arithmetic.
    """
    import numpy as np
    if uniform_step is not None:return np.gradient(values,uniform_step)
    values=np.asarray(values,dtype=float);time_s=np.asarray(time_s,dtype=float)
    if len(values)<2 or len(values)!=len(time_s):raise ValueError('Derivative requires matching source neighbors')
    differences=np.diff(time_s);left=differences[:-1];right=differences[1:]
    a=-right/(left*(left+right));b=(right-left)/(left*right);c=left/(right*(left+right))
    result=np.empty_like(values)
    result[1:-1]=a*values[:-2]+b*values[1:-1]+c*values[2:]
    result[0]=(values[1]-values[0])/differences[0]
    result[-1]=(values[-1]-values[-2])/differences[-1]
    return result


def adapt_window(module,record,facts,rows,start,lo,core):
    """Reuse frozen field mapping; override only global facts and derivatives."""
    import numpy as np
    import pandas as pd
    data={kind:pd.DataFrame([row[kind] for row in rows]) for kind in rows[0]}
    task,_,_=module.map_task_name(record['recording'])
    if task!=record['task']:raise ValueError('Inventoried task mapping changed')
    phase=module.get_collection_phase(record['subject'],record['phase'])
    if module.get_exo_state(record['recording'],phase)!=record['exo_state']:raise ValueError('Explicit actuator state differs from adapter')
    gait=module.TASK_ARCHETYPE_MAP.get(task,module.SegmentationArchetype.GAIT)==module.SegmentationArchetype.GAIT
    reference=facts['gait_reference_leg'] if gait else 'l'
    old_loader,old_reference=module.load_trial_data,module._determine_reference_leg
    module.load_trial_data=lambda *args,**kwargs:data
    module._determine_reference_leg=lambda *args,**kwargs:reference
    try:frame=module.process_trial_time(Path(record['folder']),record['subject'],record['phase'],'all')
    finally:module.load_trial_data,module._determine_reference_leg=old_loader,old_reference
    if len(frame)!=len(rows):raise ValueError('Window adapter row count changed')
    clock=data['angle_filt'].time.to_numpy()
    # Match the full-record adapter's arithmetic, not a per-window origin.
    # Absolute and rebased clocks can differ in derivative rounding.
    derivative_time=clock-facts['source_start_time_s']
    for role,leg in [('ipsi',reference),('contra','r' if reference=='l' else 'l')]:
        for native,canonical,sign in [('hip_flexion','hip_flexion',1),('knee_angle','knee_flexion',-1),('ankle_angle','ankle_dorsiflexion',-1)]:
            column=native+'_'+leg+'_velocity'
            if facts['velocity_fallback_whole_column'][column]:
                velocity=global_gradient(frame[f'{canonical}_angle_{role}_rad'].to_numpy(),derivative_time,facts['gradient_uniform_step_s'])
            else:
                velocity=sign*module._series_or_nan(data.get('velocity'),column,len(rows))*(np.pi/180)
            frame[f'{canonical}_velocity_{role}_rad_s']=velocity
            frame[f'{canonical}_acceleration_{role}_rad_s2']=global_gradient(velocity,derivative_time,facts['gradient_uniform_step_s'])
    frame['time_s']=clock-facts['source_start_time_s']
    frame['source_start_time_s']=facts['source_start_time_s'];frame['source_end_time_s']=facts['source_end_time_s']
    frame['sampling_rate_hz']=facts['sampling_rate_hz']
    info=json.loads(frame.task_info.iloc[0]);info['sampling_rate_hz']=facts['sampling_rate_hz']
    info['ankle_velocity_fallback']={role:facts['velocity_fallback_whole_column'][f'ankle_angle_{leg}_velocity'] for role,leg in [('ipsi',reference),('contra','r' if reference=='l' else 'l')]}
    frame['task_info']=json.dumps(info,sort_keys=True)
    return frame.iloc[start-lo:start-lo+core].reset_index(drop=True)


def convert_record(record,adapter,output,guard):
    """One bounded multipass export. Caller must run independent audit afterward."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    output=Path(output)
    if output.exists():raise FileExistsError('Existing scientific artifact preserved')
    _,evidence=scan(record,guard)
    with numerical_source_rows(record,guard) as rows:facts=numerical_facts(rows)
    if facts['sampling_rate_hz'] is None:raise ValueError('Nonuniform parsed clock requires interval policy')
    adapter=Path(adapter);sys.path.insert(0,str(adapter.parent))
    spec=importlib.util.spec_from_file_location('gt24_bounded_isolated_adapter',adapter)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    written=0;writer=None
    try:
        with numerical_source_rows(record,guard) as rows:
            for start,lo,core,window in halo_windows(rows):
                guard();frame=adapt_window(module,record,facts,window,start,lo,core)
                table=pa.Table.from_pandas(frame,preserve_index=False)
                if writer is None:writer=pq.ParquetWriter(output,table.schema,compression='zstd')
                if not table.schema.equals(writer.schema,check_metadata=True):raise ValueError('Output schema changed across windows')
                writer.write_table(table,row_group_size=512);written+=len(frame)
        _,after_evidence=scan(record,guard)
        if after_evidence!=evidence:raise ValueError('Source bytes changed between passes')
    finally:
        if writer is not None:writer.close()
    if written!=facts['rows']:raise ValueError('Incomplete continuous source row coverage')
    return {'status':'bounded_parsed_continuous_export_unverified','rows':written,'facts':facts,'source_evidence':evidence,'scientific_approval':False,'audit_required':True}
