"""Receipt-bound GT23 participant normalization after completed force/COP fixes.

Preparation reads only bounded receipts and streamed hashes. Run only through
an external single-worker resource guard. Source aliases retain interpolated
source-coordinate Nm; they are not additional raw recordings.
"""
import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CHAIN_PATH=ROOT/'contributor_tools/chain_gt23_cop_metadata.py'
EVIDENCE=ROOT/'docs/quality/audits/source_evidence/gt23'
MASS=EVIDENCE/'publisher-subject-masses.csv'
README=EVIDENCE/'publisher-readme.txt'
LOCAL_MASS=Path('/mnt/s/locomotion_data/Gtech_2023/RawData/Subject_masses.csv')
PINNED_SOURCE={str(MASS):'ff7f268497c0f2945374894005f68d647e869130e46e90194346752ea6508ab0',str(README):'4a5c8ef0a8d96ed3b81253e7fed2d8516b884fa2aa63e4340c0ab54cf2ac4752',str(LOCAL_MASS):'46e8465d7e027f676b9cdc4a26814ca1e28ab1a218f96cf6b910e2512dcb3e6b'}
MOMENTS={f'{canonical}_moment_{side}_Nm_kg':(f'source_{source}_moment_{side}_Nm',sign) for side in ('ipsi','contra') for canonical,source,sign in [('hip_flexion','hip_flexion',1),('knee_flexion','knee_angle',-1),('ankle_dorsiflexion','ankle_angle',1)]}
FORCES=[f'grf_vertical_{s}_BW' for s in ('ipsi','contra')]+[f'source_grf_global_{a}_{s}_BW' for s in ('ipsi','contra') for a in ('x','z')]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

PINNED_CHAIN='900ad16134c5924fc2dfedf73b6db07bcd4454701b5ae2021e3c46e4a0d92f41'

def chain_module():
    import hashlib
    if hashlib.sha256(CHAIN_PATH.read_bytes()).hexdigest()!=PINNED_CHAIN:raise ValueError('Frozen chain helper changed')
    return load(CHAIN_PATH,'gt23_normalization_chain')

def masses():
    c=chain_module();c.verify(PINNED_SOURCE)
    published={r['Subject']:float(r['Mass']) for r in csv.DictReader(MASS.read_text().splitlines())}
    old={r['subject_id']:float(r['mass_kg']) for r in csv.DictReader(x for x in LOCAL_MASS.read_text().splitlines() if not x.startswith('#'))}
    if set(published)!=set(old) or any(not math.isfinite(v) or v<=0 for v in [*published.values(),*old.values()]):raise ValueError('Invalid mass inventory')
    return published,old

def subject_mass_metadata(raw,old,new):
    try:info=json.loads(raw)
    except json.JSONDecodeError:
        parts=raw.split(':')
        if len(parts)!=2 or parts[0]!='weight_kg':raise ValueError('Unknown original mass metadata')
        info={'weight_kg':float(parts[1])}
    if not isinstance(info,dict) or info.get('weight_kg')!=old:raise ValueError('Original mass denominator not established')
    if 'source_previous_normalization_mass_kg' in info:raise ValueError('Already corrected mass metadata')
    return json.dumps({**info,'weight_kg':new,'source_previous_normalization_mass_kg':old},sort_keys=True,allow_nan=False)

def transform_table(table,published,old):
    import pyarrow as pa
    c=chain_module();force=c.load('gt23_norm_force',c.FORCE_PATH);cop=c.load('gt23_norm_cop',c.COP_PATH)
    c.validate_force_table(table,force)
    if len(set(table.column_names))!=len(table.column_names) or set(a for a,s in MOMENTS.values())&set(table.column_names):raise ValueError('Duplicate/source alias conflict')
    subjects=table['subject'].to_pylist();new=[];previous=[]
    for subject in subjects:
        if not isinstance(subject,str) or not subject.startswith('GT23_'):raise ValueError('Invalid subject')
        key=subject[5:]
        if key not in published or key not in old:raise ValueError('Unknown participant mass')
        if any(not math.isfinite(v) or v<=0 for v in (published[key],old[key])):raise ValueError('Invalid participant mass')
        new.append(published[key]);previous.append(old[key])
    result=table
    def replace(name,values):
        nonlocal result
        f=table.schema.field(name);result=result.set_column(result.schema.get_field_index(name),f,pa.array(values,type=f.type))
    for name,(alias,sign) in MOMENTS.items():
        f=table.schema.field(name)
        if not pa.types.is_floating(f.type):raise ValueError('Moment not floating point')
        values=table[name].to_pylist()
        result=result.append_column(pa.field(alias,f.type,metadata={b'unit':b'Nm',b'coordinate_convention':b'publisher raw CSV; existing interpolation retained'}),pa.array([None if v is None else v*sign for v in values],type=f.type))
        replace(name,[None if v is None else v/m for v,m in zip(values,new)])
    for name in FORCES:
        if not pa.types.is_floating(table.schema.field(name).type):raise ValueError('Force not floating point')
        replace(name,[None if v is None else v*a/b for v,a,b in zip(table[name].to_pylist(),previous,new)])
    replace('subject_metadata',[subject_mass_metadata(v,a,b) for v,a,b in zip(table['subject_metadata'].to_pylist(),previous,new)])
    metadata=[]
    for raw,a,b in zip(table['task_info'].to_pylist(),previous,new):
        info=json.loads(raw)
        if info.get('gt23_cop_frame')!=cop.COP_INFO or 'gt23_publisher_normalization' in info:raise ValueError('Missing COP provenance or already corrected')
        info['gt23_publisher_normalization']={'participant_mass_kg':b,'previous_normalization_mass_kg':a,'moment_source_units':'Nm','moment_target_units':'Nm/kg','source_moment_aliases':'Publisher coordinate signs restored; existing interpolation retained','force_scaling':'previous mass / publisher participant mass','source_readme_sha256':PINNED_SOURCE[str(README)],'source_mass_sha256':PINNED_SOURCE[str(MASS)],'anatomical_joint_signs':'Unchanged; independent anatomical approval remains pending','earlier_force_metadata':'Retained as history; its existing-normalization caveat is superseded only by this normalization record'}
        metadata.append(json.dumps(info,sort_keys=True,allow_nan=False))
    replace('task_info',metadata)
    return result

def exact_equal(a,b):
    import pyarrow as pa
    a=a.combine_chunks();b=b.combine_chunks()
    if not a.is_null().equals(b.is_null()):return False
    if pa.types.is_floating(a.type):
        integer={32:pa.uint32(),64:pa.uint64()}.get(a.type.bit_width)
        return integer is not None and a.view(integer).equals(b.view(integer))
    return a.equals(b)

def verify_tables(before,after,published,old):
    expected=transform_table(before,published,old)
    if not expected.schema.equals(after.schema,check_metadata=True) or len(before)!=len(after):raise ValueError('Schema/row mismatch')
    for name in expected.column_names:
        if not exact_equal(expected[name],after[name]):raise ValueError('Readback mismatch: '+name)

def receipt_chain(report_path,c):
    report_path=Path(report_path).resolve()
    if report_path.stat().st_size>4*1024**2:raise ValueError('Oversized receipt')
    report=json.loads(report_path.read_text())
    if report.get('status')!='force_and_cop_metadata_corrections_source_preserved_unreviewed' or report.get('scientific_approval') is not False:raise ValueError('Completed combined correction required')
    bindings=report['verified_input_sha256'];c.verify(bindings);c.verify(c.PINNED)
    if bindings.get(str(CHAIN_PATH))!=c.digest(CHAIN_PATH):raise ValueError('Unbound combined producer')
    force=c.load('gt23_norm_lineage',c.FORCE_PATH)
    force_report=json.loads(Path(report['force_report']).read_text())
    native=[p for p in force_report['input_sha256'] if p.endswith('.json') and Path(p).stat().st_size<4*1024**2 and json.loads(Path(p).read_text()).get('input_sha256') and json.loads(Path(p).read_text()).get('producing_mode')]
    if len(native)!=1:raise ValueError('Ambiguous native lineage')
    chain=c.completed_chain(report['force_report'],native[0],force,{str(c.FORCE_PATH):c.PINNED[str(c.FORCE_PATH)]})
    if report['original_native_input']!=chain['original_input'] or report['actual_producing_converter']!=chain['producer'] or report['intermediate_force_output']!=chain['input']:raise ValueError('Combined producer lineage mismatch')
    for p,h in chain['bindings'].items():
        if bindings.get(p)!=h:raise ValueError('Incomplete combined lineage')
    target=report_path.parent/'corrected.parquet'
    if c.digest(target)!=report['output_sha256']:raise ValueError('Combined output changed')
    return {'input':str(target),'producer':chain['producer'],'bindings':{**bindings,str(report_path):c.digest(report_path),str(target):c.digest(target)}}

def prepare(report,plan,output):
    c=chain_module();lineage=receipt_chain(report,c);masses()
    plan=Path(plan).resolve();output=Path(output).resolve();local=ROOT/'converted_datasets/reconversion_v2'
    if not plan.is_relative_to(local) or not output.is_relative_to(local) or plan.exists() or output.exists():raise ValueError('Fresh authorized plan/output required')
    bindings={**lineage['bindings'],**PINNED_SOURCE,str(Path(__file__).resolve()):c.digest(__file__),str(CHAIN_PATH):c.digest(CHAIN_PATH)}
    guard=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/run_ensemble_pilot.py';bindings[str(guard)]=c.digest(guard)
    review=ROOT/'docs/quality/audits/gt23-publisher-units-and-mass-review.json';bindings[str(review)]=c.digest(review)
    p={**lineage,'bindings':bindings,'combined_report':str(Path(report).resolve()),'output':str(output),'scientific_approval':False,'status':'prepared_not_run','guard':{'module':str(guard),'function':'guarded_stage','timeout_seconds':120,'worker_address_space_mib':768,'resource_poll_seconds':15},'scope':'Participant normalization only; prior force/COP retained; no sign approval.'}
    c.verify(bindings);plan.parent.mkdir(parents=True,exist_ok=True)
    with plan.open('x') as f:json.dump(p,f,indent=2)
    return {'plan':str(plan),'plan_sha256':c.digest(plan),'guarded_worker_command':['ionice','-c','3','python3',str(Path(__file__).resolve()),'run','--plan',str(plan),'--plan-sha256',c.digest(plan)]}

def run(plan_path,expected):
    import os,resource
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    c=chain_module()
    if c.digest(plan_path)!=expected:raise ValueError('Plan hash mismatch')
    plan=json.loads(Path(plan_path).read_text());c.verify(plan['bindings']);lineage=receipt_chain(plan['combined_report'],c)
    if lineage['input']!=plan['input'] or lineage['producer']!=plan['producer']:raise ValueError('Lineage changed')
    for p,h in lineage['bindings'].items():
        if plan['bindings'].get(p)!=h:raise ValueError('Incomplete plan bindings')
    published,old=masses()
    import pyarrow as pa
    import pyarrow.parquet as pq
    from itertools import zip_longest
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    output=Path(plan['output']).resolve()
    if not output.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Unauthorized output')
    output.mkdir(parents=True,exist_ok=False);target=output/'corrected.parquet';writer=None;rows=0
    try:
        for batch in pq.ParquetFile(plan['input']).iter_batches(batch_size=512,use_threads=False):
            if batch.nbytes>8*1024**2:raise MemoryError('Batch admission exceeded')
            t=transform_table(pa.Table.from_batches([batch]),published,old)
            if writer is None:writer=pq.ParquetWriter(target,t.schema,compression='zstd')
            writer.write_table(t,row_group_size=512);rows+=len(t)
    finally:
        if writer:writer.close()
    if not rows:raise ValueError('Empty source')
    for a,b in zip_longest(pq.ParquetFile(plan['input']).iter_batches(batch_size=512,use_threads=False),pq.ParquetFile(target).iter_batches(batch_size=512,use_threads=False)):
        if a is None or b is None:raise ValueError('Readback length changed')
        verify_tables(pa.Table.from_batches([a]),pa.Table.from_batches([b]),published,old)
    c.verify(plan['bindings'])
    if c.digest(plan_path)!=expected:raise ValueError('Plan changed')
    report={'status':'force_cop_and_publisher_normalization_corrected_unreviewed','scientific_approval':False,'rows_checked':rows,'actual_producing_converter':plan['producer'],'verified_input_sha256':plan['bindings'],'plan_sha256':expected,'output_sha256':c.digest(target),'scope':'Participant mass and Nm normalization; earlier source frames preserved; joint signs still unapproved.'}
    (output/'normalization_readback.json').write_text(json.dumps(report,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    q=s.add_parser('prepare')
    for n in ('combined-report','plan','output'):q.add_argument('--'+n,type=Path,required=True)
    q=s.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True)
    a=p.parse_args()
    if a.mode=='prepare':print(json.dumps(prepare(a.combined_report,a.plan,a.output),indent=2))
    else:run(a.plan,a.plan_sha256)
if __name__=='__main__':main()
