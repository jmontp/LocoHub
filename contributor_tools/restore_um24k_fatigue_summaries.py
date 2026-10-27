"""UM24K S2 source summaries: no gait cycles, resampling, timing invention or pooling."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'contributor_tools/conversion_scripts/UMich_2024_KneeExo'
S2_SHA='3f347db39ee86441140695aa94de5ec440fc2f61f61fc0925bf74f5e669b3c8f'
PROGRESSION={'LLrepDuration_progression':('s','Squat repetition duration; post-fatigue pauses may occur'), 'peakLean_progression':('deg','Peak sagittal thorax angle, trunk flexion positive'), 'peakLean_deviation_progression':('deg','Deviation from minimum pre-fatigue bare peak lean'), 'peakKneeFlexion_progression':('deg','Peak knee angle, flexion positive'), 'peakKneeFlexion_deviation_progression':('deg','Deviation from maximum pre-fatigue peak knee angle of respective condition')}
SUMMARY={'fatiguedCompletionTime_deficit':('percent','Increase in duration of ten post-fatigue repetitions versus first ten pre-fatigue bare repetitions'), 'fatiguedPeakLean':('deg','Mean peak sagittal thorax angle of ten post-fatigue repetitions'), 'fatiguedPeakLean_deviation':('deg','Mean deviation in peak lean of ten post-fatigue repetitions'), 'fatiguedPeakKneeFlexion':('deg','Mean peak knee angle of ten post-fatigue repetitions'), 'fatiguedPeakKneeFlexion_deviation':('deg','Mean deviation in peak knee angle of ten post-fatigue repetitions')}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(data):
    import numpy as np
    names={k for k in data if not k.startswith('__')}
    if names!=set(PROGRESSION)|set(SUMMARY)|{'modifiedquest'}:raise ValueError('Unknown or missing S2 structures')
    for name in (*PROGRESSION,*SUMMARY):
        group=data[name]
        if not isinstance(group,dict) or set(group)!={'bare','exo'}:raise ValueError('Source condition structure differs')
        for value in group.values():
            a=np.asarray(value);shape=(21,10) if name in PROGRESSION else (10,)
            if a.shape!=shape or a.dtype.kind!='f' or np.isinf(a).any():raise ValueError('Source summary shape/type/infinity differs')
    q=data['modifiedquest']
    if not isinstance(q,dict) or set(q)!={'headers','data'}:raise ValueError('Questionnaire fields differ')
    a=np.asarray(q['data']);headers=np.asarray(q['headers'])
    if a.shape!=(6,10) or a.dtype.kind!='f' or np.isinf(a).any():raise ValueError('Questionnaire shape/type/infinity differs')
    if headers.shape!=(6,) or any(not isinstance(x,str) or not x for x in headers):raise ValueError('Six original task labels required')
    if len(set(headers.tolist()))!=6:raise ValueError('Duplicate questionnaire task labels')
    return data

def tables(data):
    import pyarrow as pa
    from itertools import product
    outputs={}
    for kind,mapping in [('progression',PROGRESSION),('post_fatigue_summary',SUMMARY)]:
        rows=[]
        for name,(unit,definition) in mapping.items():
            for condition,column in product(('bare','exo'),range(10)):
                for index in range(21 if kind=='progression' else 1):
                    row={'subject':f'UM24_COLUMN_{column+1:02d}','source_subject_column':column+1,'source_file':'dataset_S2.mat','source_field':name,'condition':condition,'observation_type':'fatigue_progression_summary' if kind=='progression' else 'post_fatigue_summary','source_row':index+1,'source_identity':f'um24k:dataset_S2.mat:{name}:{condition}:row:{index+1}:column:{column+1}','value':float(data[name][condition][index,column] if kind=='progression' else data[name][condition][column]),'unit':unit,'definition':definition}
                    if kind=='progression':row['trial_progression_percent']=-100+10*index
                    rows.append(row)
        outputs[kind]=pa.Table.from_pylist(rows)
    rows=[]
    for index,label in enumerate(data['modifiedquest']['headers']):
        for column in range(10):rows.append({'subject':f'UM24_COLUMN_{column+1:02d}','source_subject_column':column+1,'source_file':'dataset_S2.mat','source_field':'modifiedquest.data','source_row':index+1,'source_task_label':str(label),'source_identity':f'um24k:dataset_S2.mat:modifiedquest.data:row:{index+1}:column:{column+1}','observation_type':'questionnaire_summary','value':float(data['modifiedquest']['data'][index,column]),'unit':'rating_out_of_5','condition':'not_separately_labelled_in_source'})
    outputs['questionnaire']=pa.Table.from_pylist(rows)
    metadata={b'source_doi':b'10.5061/dryad.z34tmpgks',b'source_version':b'314890',b'scientific_approval':b'false',b'progression_reference':b'0 percent is self-declared fatigue; not gait phase or elapsed time',b'participant_identity':b'Source column ordinal; no named participant identifiers',b'variability':b'Source summaries only; no SD, individual cycle count or measurements invented',b'workspace':b'Original MATLAB __function_workspace__ preserved in source MAT; not a scientific table'}
    return {k:t.replace_schema_metadata(metadata) for k,t in outputs.items()}

def prepare(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2') or output.exists():raise ValueError('Fresh authorized output required')
    if digest(SOURCE/'dataset_S2.mat')!=S2_SHA:raise ValueError('Publisher source differs')
    evidence=ROOT/'docs/quality/audits/source_evidence/um24k'
    paths=[SOURCE/'dataset_S2.mat',evidence/'publisher-readme.txt',evidence/'publisher-files.json',evidence/'publisher-version.json',Path(__file__),ROOT/'contributor_tools/audit_um24k_fatigue_summaries.py']
    plan={'status':'prepared_not_run','scientific_approval':False,'output_root':str(output),'source':str(SOURCE/'dataset_S2.mat'),'bindings':{str(p):digest(p) for p in paths},'scope':{'participants':10,'progression_fields':5,'progression_rows':2100,'summary_fields':5,'summary_rows':100,'questionnaire_rows':60},'limitations':['Trial progression percentage is anchored to fatigue, not gait phase or elapsed time.','No raw repetitions, within-participant SD or individual timestamps reconstructed.','Questionnaire headers preserved exactly; no inferred task naming or bare/exo condition.','Named participant IDs and clinical laterality unavailable.','MATLAB function workspace bytes remain in original source, not converted into scientific observations.'],'resource_policy':'Single externally guarded 768 MiB worker; explicit coordinator launch only.'}
    output.mkdir();(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan

def run(plan_path):
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    import pyarrow as pa
    import pyarrow.parquet as pq
    from scipy.io import loadmat
    from contributor_tools.audit_um24k_fatigue_summaries import audit
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text());root=Path(plan['output_root'])
    if root.resolve()!=plan_path.resolve().parent or not root.resolve().is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Output scope differs')
    for p,h in plan['bindings'].items():
        if digest(p)!=h:raise ValueError('Source or code changed')
    if any((root/n).exists() for n in ('progression.parquet','post_fatigue_summary.parquet','questionnaire.parquet','source_readback.json')):raise FileExistsError('Preserve previous attempt')
    source=Path(plan['source'])
    if source.stat().st_size>1024**2:raise MemoryError('Bounded MAT admission exceeded')
    data=validate(loadmat(source,simplify_cells=True))
    for name,table in tables(data).items():pq.write_table(table,root/(name+'.parquet'),compression='zstd',row_group_size=210)
    del data
    report=audit(plan_path)
    with (root/'source_readback.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run(a.output_root/'plan.json')
    else:print(json.dumps(prepare(a.output_root)['scope']))

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT));main()
