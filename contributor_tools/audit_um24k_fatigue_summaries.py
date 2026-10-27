"""Independent source-cell identity/value readback for UM24K fatigue summaries."""
import hashlib
import json
import math
from pathlib import Path
import struct

PROGRESSION=('LLrepDuration_progression','peakLean_progression','peakLean_deviation_progression','peakKneeFlexion_progression','peakKneeFlexion_deviation_progression')
SUMMARY=('fatiguedCompletionTime_deficit','fatiguedPeakLean','fatiguedPeakLean_deviation','fatiguedPeakKneeFlexion','fatiguedPeakKneeFlexion_deviation')
DEFINITIONS=('Squat repetition duration; post-fatigue pauses may occur','Peak sagittal thorax angle, trunk flexion positive','Deviation from minimum pre-fatigue bare peak lean','Peak knee angle, flexion positive','Deviation from maximum pre-fatigue peak knee angle of respective condition','Increase in duration of ten post-fatigue repetitions versus first ten pre-fatigue bare repetitions','Mean peak sagittal thorax angle of ten post-fatigue repetitions','Mean deviation in peak lean of ten post-fatigue repetitions','Mean peak knee angle of ten post-fatigue repetitions','Mean deviation in peak knee angle of ten post-fatigue repetitions')

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def child(obj,name):return obj[name] if isinstance(obj,dict) else getattr(obj,name)

def expected_rows(raw,kind):
    if kind=='questionnaire':
        q=child(raw,'modifiedquest');values=child(q,'data');headers=child(q,'headers')
        if values.shape!=(6,10) or headers.shape!=(6,):raise ValueError('Original questionnaire shape differs')
        for row in range(6):
            for column in range(10):yield {'subject':f'UM24_COLUMN_{column+1:02d}','source_subject_column':column+1,'source_file':'dataset_S2.mat','source_field':'modifiedquest.data','source_row':row+1,'source_task_label':str(headers[row]),'source_identity':f'um24k:dataset_S2.mat:modifiedquest.data:row:{row+1}:column:{column+1}','observation_type':'questionnaire_summary','value':float(values[row,column]),'unit':'rating_out_of_5','condition':'not_separately_labelled_in_source'}
        return
    fields=PROGRESSION if kind=='progression' else SUMMARY
    for position,name in enumerate(fields):
        for condition in ('bare','exo'):
            values=child(child(raw,name),condition)
            if values.shape!=((21,10) if kind=='progression' else (10,)):raise ValueError('Original summary shape differs')
            for column in range(10):
                for row in range(21 if kind=='progression' else 1):
                    result={'subject':f'UM24_COLUMN_{column+1:02d}','source_subject_column':column+1,'source_file':'dataset_S2.mat','source_field':name,'condition':condition,'observation_type':'fatigue_progression_summary' if kind=='progression' else 'post_fatigue_summary','source_row':row+1,'source_identity':f'um24k:dataset_S2.mat:{name}:{condition}:row:{row+1}:column:{column+1}','value':float(values[row,column] if kind=='progression' else values[column]),'unit':('s' if kind=='progression' else 'percent') if position==0 else 'deg','definition':DEFINITIONS[position+(0 if kind=='progression' else 5)]}
                    if kind=='progression':result['trial_progression_percent']=10*(row-10)
                    yield result

def verify_rows(actual,expected):
    if set(actual)!=set(expected):raise ValueError('Unexpected fields or invented timing/variability')
    for key,value in expected.items():
        if key=='value':
            current=actual[key]
            if current is None or math.isinf(value) or math.isinf(current) or math.isnan(value)!=math.isnan(current):raise ValueError('Invalid or changed missingness')
            if not math.isnan(value) and struct.pack('d',current)!=struct.pack('d',value):raise ValueError('Source value bits differ')
        elif actual[key]!=value:raise ValueError('Source identity/definition differs: '+key)
    return math.isfinite(expected['value'])

def verify_table(table,raw,kind):
    expected=list(expected_rows(raw,kind))
    if table.num_rows!=len(expected) or table.column_names!=list(expected[0]):raise ValueError('Exact source summary rows/columns required')
    metadata=table.schema.metadata or {}
    for key,value in {b'source_doi':b'10.5061/dryad.z34tmpgks',b'source_version':b'314890',b'scientific_approval':b'false',b'progression_reference':b'0 percent is self-declared fatigue; not gait phase or elapsed time'}.items():
        if metadata.get(key)!=value:raise ValueError('Source metadata differs')
    finite=0
    for actual,wanted in zip(table.to_pylist(),expected):finite+=verify_rows(actual,wanted)
    return {'rows':len(expected),'finite_checked':finite,'missing_unassessed':len(expected)-finite,'assessment':'source_values_checked_not_scientific_approval' if finite else 'unavailable_not_passed'}

def audit(plan_path):
    from scipy.io import loadmat
    import pyarrow.parquet as pq
    plan_path=Path(plan_path);plan_sha=digest(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['output_root'])
    for path,h in plan['bindings'].items():
        if digest(path)!=h:raise ValueError('Bound source/code changed')
    if Path(plan['source']).stat().st_size>1024**2:raise MemoryError('MAT admission exceeded')
    raw=loadmat(plan['source'],squeeze_me=True,struct_as_record=False)
    if {k for k in raw if not k.startswith('__')}!=set(PROGRESSION)|set(SUMMARY)|{'modifiedquest'}:raise ValueError('Source fields differ')
    results={};hashes={}
    for kind,count in [('progression',2100),('post_fatigue_summary',100),('questionnaire',60)]:
        path=root/(kind+'.parquet')
        if path.stat().st_size>4*1024**2:raise MemoryError('Summary file admission exceeded')
        before=digest(path);file=pq.ParquetFile(path)
        if file.metadata.num_rows!=count or sum(file.metadata.row_group(i).total_byte_size for i in range(file.metadata.num_row_groups))>4*1024**2:raise ValueError('Bounded source summary scope differs')
        results[kind]=verify_table(file.read(use_threads=False),raw,kind)
        if digest(path)!=before:raise ValueError('Output changed during readback')
        hashes[kind+'.parquet']=before
    for path,h in plan['bindings'].items():
        if digest(path)!=h:raise ValueError('Source/code changed during readback')
    if digest(plan_path)!=plan_sha:raise ValueError('Plan changed during readback')
    return {'status':'all_documented_S2_summary_cells_source_checked_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'bindings':plan['bindings'],'output_sha256':hashes,'tables':results,'limitations':plan['limitations'],'original_workspace':'Preserved in immutable source MAT, not interpreted as scientific measurement'}
