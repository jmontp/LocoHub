"""One bounded full-cohort ensemble pair; frozen pilot interpolation/readback reused.

No stride reconstruction and no averaging across subjects, conditions or legs.
Run only through the reviewed serial full-ensemble runner.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
FAMILY=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,FAMILY/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def protocol(stem):
    match=re.fullmatch(r'WBDS(\d{2})walk(O[SCF]|T0[1-8])',stem)
    if not match:raise ValueError('Unreviewed participant-condition stem')
    subject,condition=match.groups()
    if not 1<=int(subject)<=51:raise ValueError('Outside pinned51-participant cohort')
    return subject,condition,('overground' if condition.startswith('O') else 'treadmill')


def expanded_rows(angles,kinetics,stem,base):
    subject,condition,environment=protocol(stem)
    rows=base.build_rows(angles,kinetics,f'WBDS{subject}walkOC')
    source_id='fu18:v6:participant_condition_ensemble:'+stem
    for row in rows:
        row['source_recording_id']=source_id
        row['observation_id']=source_id+':'+row['reference_side']
        row['task_id']=environment+'_'+condition
        info=json.loads(row['task_info'])
        info.update(environment=environment,source_condition=condition)
        if environment=='overground':info['speed_category']={'OS':'slow','OC':'comfortable','OF':'fast'}[condition]
        else:info.pop('speed_category')
        row['task_info']=json.dumps(info,sort_keys=True)
    return rows


def independent_readback(frame,sources,stem,checker):
    # Validate actual identity before adapting metadata to the frozen numerical checker.
    match=re.fullmatch(r'WBDS(\d{2})walk(O[SCF]|T0[1-8])',stem)
    assert match
    subject,condition=match.groups()
    environment='overground' if condition[0]=='O' else 'treadmill'
    source_id='fu18:v6:participant_condition_ensemble:'+stem
    assert frame.subject.eq('FU18_'+subject).all()
    assert frame.task.eq('level_walking').all()
    assert frame.task_id.eq(environment+'_'+condition).all()
    assert frame.source_recording_id.eq(source_id).all()
    assert all(oid==source_id+':'+side for oid,side in zip(frame.observation_id,frame.reference_side))
    normalized=frame.copy()
    normalized_info=[]
    for raw in frame.task_info:
        info=json.loads(raw)
        assert info['environment']==environment and info['source_condition']==condition
        if environment=='overground':assert info['speed_category']=={'OS':'slow','OC':'comfortable','OF':'fast'}[condition]
        else:assert 'speed_category' not in info
        assert 'speed_m_s' not in info
        info.update(environment='overground',source_condition='C',speed_category='comfortable')
        normalized_info.append(json.dumps(info,sort_keys=True))
    surrogate=f'WBDS{subject}walkOC'
    normalized['task_info']=normalized_info
    normalized['task_id']='overground_C'
    normalized['source_recording_id']='fu18:v6:participant_condition_ensemble:'+surrogate
    normalized['observation_id']=[sid+':'+side for sid,side in zip(normalized.source_recording_id,normalized.reference_side)]
    return checker.validate_frame(normalized,sources,[surrogate+'ang.txt',surrogate+'knt.txt'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--stem',required=True)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    if digest(args.plan)!=args.plan_sha256:raise ValueError('Frozen plan changed')
    plan=json.loads(args.plan.read_text())
    if not any(pair['stem']==args.stem for pair in plan['pairs']):raise ValueError('Pair absent from reviewed inventory')
    if args.output_root.resolve()!=Path(plan['output_root']).resolve():raise ValueError('Output outside exact authorized root')
    if args.source_dir.resolve()!=Path(plan['source_dir']).resolve():raise ValueError('Source outside exact planned root')
    bindings={str(args.plan):args.plan_sha256,**plan['code_sha256']}
    acquisition_path=args.source_dir/(args.stem+'.acquisition.json')
    acquisition=json.loads(acquisition_path.read_text())
    assert acquisition['stem']==args.stem and acquisition['plan_sha256']==args.plan_sha256
    bindings[str(acquisition_path)]=digest(acquisition_path)
    paths=[args.source_dir/(args.stem+suffix+'.txt') for suffix in ('ang','knt')]
    for p in paths:
        if p.stat().st_size>1024**2:raise ValueError('Source member exceeds1 MiB')
        bindings[str(p)]=acquisition['files'][p.name]['sha256']
    def verify():
        for name,expected in bindings.items():
            if digest(name)!=expected:raise ValueError('Bound input changed: '+name)
    verify()
    base=load('frozen_fu18_conversion','convert_ensemble_pilot.py')
    checker=load('frozen_fu18_readback','check_ensemble_pilot.py')
    rows=expanded_rows(*(base.read_curve(path) for path in paths),args.stem,base)
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    frame=pd.DataFrame(rows)
    out=args.output_root/args.stem
    out.mkdir(parents=True,exist_ok=False)
    parquet=out/'ensemble.parquet';frame.to_parquet(parquet,index=False,row_group_size=150)
    source_values={}
    for path in paths:
        raw=pd.read_csv(path,sep='\t')
        assert len(raw)==101
        np.testing.assert_allclose(raw.Time,np.arange(101),rtol=0,atol=1e-8)
        for column in raw:
            if column!='Time':
                assert column not in source_values
                source_values[column]=raw[column].to_numpy()
    # Read the written artifact; never validate only the pre-write frame.
    checked,error=independent_readback(pd.read_parquet(parquet),source_values,args.stem,checker)
    verify()
    manifest={'status':'converted_ensemble_unreviewed','scientific_approval':False,'source_files':{str(p):bindings[str(p)] for p in paths},'output_sha256':digest(parquet),'rows':len(frame),'ensembles':2,'individual_cycles':0,'source_stem':args.stem,'plan_sha256':args.plan_sha256,'converter_sha256':digest(__file__),'verified_input_sha256':bindings}
    mp=out/'conversion_manifest.json';mp.write_text(json.dumps(manifest,indent=2)+'\n')
    report={'status':'ensemble_source_values_checked_unreviewed','scientific_approval':False,'manifest_sha256':digest(mp),'reviewer_sha256':digest(FAMILY/'check_ensemble_pilot.py'),'ensembles':2,'individual_cycles':0,'finite_source_values_checked':checked,'max_abs_source_error':error,'verified_input_sha256':{**bindings,str(mp):digest(mp),str(parquet):digest(parquet)},'scope':'Source participant-condition means; no raw events, stride counts, within-subject SD or invented timing. Left canonical fields remain unavailable.'}
    (out/'source_readback.json').write_text(json.dumps(report,indent=2)+'\n')
    verify()
    print(json.dumps({'stem':args.stem,'status':report['status'],'rows':len(frame),'observations':2}))


if __name__=='__main__':main()
