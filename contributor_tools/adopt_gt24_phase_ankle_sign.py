"""Stream a pilot-validated GT24 ankle sign correction into new phase outputs.

Requires both complete original phase batches with known converter provenance.
Old quality reports are retained under baseline_evidence, never presented as
assessments of corrected values. No source reconversion or IMU recalculation.
"""
import argparse
import itertools
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.run_gt24_ankle_converter_pilot import FIELDS,digest,verify
from contributor_tools.prepare_gt24_ankle_fix import ADAPTER,README_SHA256
from contributor_tools.preserve_um21_planar_estimates import exact_value
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
META={'ankle_source_positive_direction':'plantarflexion','ankle_canonical_transform':'negation for dorsiflexion positive','ankle_convention_evidence':'source README lines 90-94 and 483-563','ankle_convention_readme_sha256':README_SHA256,'ankle_source_alias_method':'source sign retained after phase interpolation; velocity and acceleration derived'}


def task_metadata(text):
    info=json.loads(text)
    if not isinstance(info,dict) or set(META)&set(info):raise ValueError('Already corrected or ambiguous ankle convention metadata')
    if info.get('moment_semantics')!='source_filtered_total_joint_moment_Nm_per_source_model_kg' or info.get('biological_moment_semantics')!='source_total_minus_exo_interaction_when_available':raise ValueError('Unknown kinetic units/conventions')
    if info.get('exo_state') not in ('powered','worn_unpowered','no_exo'):raise ValueError('Unknown exoskeleton state')
    expected='known_absent_no_exo' if info['exo_state']=='no_exo' else 'source_interaction_torque_when_available'
    if info.get('assistance_semantics')!=expected:raise ValueError('Unknown assistance semantics')
    return json.dumps({**info,**META},sort_keys=True)


def validate_manifest(manifest,phase,subject,recording,converter_sha):
    if (manifest.get('dataset'),manifest.get('source'),manifest.get('subject'),manifest.get('recording'))!=('gt24',phase,subject,recording):raise ValueError('Source identity differs from inventory')
    if manifest.get('status') not in ('converted_unreviewed','no_accepted_observations'):raise ValueError('Unfinished/quarantined source recording')
    matches=[x for x in manifest['converter_code'] if Path(x['path']).name==ADAPTER.name]
    if len(matches)!=1 or matches[0]['sha256']!=converter_sha:raise ValueError('Unknown baseline ankle convention code')
    readmes=[x for x in manifest['sources'] if Path(x['path']).name=='readme.txt']
    if len(readmes)!=1 or readmes[0]['sha256']!=README_SHA256:raise ValueError('Source README provenance absent')
    rows=manifest['rows']
    if type(rows) is not int or rows<0 or rows%150:raise ValueError('Invalid phase count')
    if (manifest['status']=='no_accepted_observations')!=(rows==0):raise ValueError('Empty recording disposition inconsistent')
    if rows and not manifest.get('schema_passed'):raise ValueError('Baseline structurally invalid')
    outputs=manifest['outputs'];names=[x['name'] for x in outputs]
    if len(names)!=len(set(names)) or any(Path(n).name!=n for n in names):raise ValueError('Unsafe/duplicate output artifact')
    if ('phase.parquet' in names)!=(rows>0):raise ValueError('Phase output disposition differs')
    if sum(manifest.get('decision_counts',{}).values())!=rows//150:raise ValueError('Original observation assessment count differs')
    return rows


def transform(table):
    import pyarrow as pa
    import pyarrow.compute as pc
    names=table.column_names
    if len(set(names))!=len(names) or not set(FIELDS)<=set(names) or set(FIELDS.values())&set(names):raise ValueError('Missing/ambiguous original ankle fields')
    for name,alias in FIELDS.items():
        field=table.schema.field(name)
        if not pa.types.is_floating(field.type):raise ValueError('Ankle coordinate must be floating')
        original=table[name]
        table=table.append_column(field.with_name(alias),original)
        table=table.set_column(table.schema.get_field_index(name),field,pc.negate(original))
    index=table.schema.get_field_index('task_info');field=table.schema.field('task_info')
    table=table.set_column(index,field,pa.array([task_metadata(x) for x in table['task_info'].to_pylist()],type=field.type))
    return table


def verify_shard(before,after,record,guard):
    import pyarrow.parquet as pq
    from contributor_tools.common.data_contract import inspect_contract
    left,right=pq.ParquetFile(before),pq.ParquetFile(after);seen=set()
    if left.metadata.num_rows!=right.metadata.num_rows or left.schema_arrow.metadata!=right.schema_arrow.metadata:raise ValueError('Row/schema metadata changed')
    for a,b in itertools.zip_longest(left.iter_batches(batch_size=150,use_threads=False),right.iter_batches(batch_size=150,use_threads=False)):
        guard()
        if a is None or b is None or a.num_rows!=150 or b.num_rows!=150:raise ValueError('Partial observation')
        if b.schema.names!=a.schema.names+list(FIELDS.values()):raise ValueError('Unexpected columns/order')
        values={name:a.column(a.schema.get_field_index(name)).to_pylist() for name in a.schema.names}
        identities=values['observation_id'];identity=identities[0];prefix=f"gt24:{record['phase']}/{record['subject']}/{record['recording']}"
        if len(set(identities))!=1 or identity in seen or not identity.startswith(prefix+':samples:') or values['source_recording_id']!=[prefix]*150:raise ValueError('Source observation identity differs/duplicates')
        seen.add(identity)
        for name in a.schema.names:
            av=a.column(a.schema.get_field_index(name));bv=b.column(b.schema.get_field_index(name))
            if not a.schema.field(name).equals(b.schema.field(name),check_metadata=True) or not av.is_null().equals(bv.is_null()):raise ValueError('Original field metadata/mask changed')
            if name in FIELDS:
                alias=FIELDS[name];restored=b.column(b.schema.get_field_index(alias))
                if not a.schema.field(name).with_name(alias).equals(b.schema.field(alias),check_metadata=True) or not av.is_null().equals(restored.is_null()) or not exact_value(values[name],restored.to_pylist()):raise ValueError('Source alias changed')
                expected=[None if x is None else -x for x in values[name]]
            elif name=='task_info':expected=[task_metadata(x) for x in values[name]]
            else:expected=values[name]
            if not exact_value(expected,bv.to_pylist()):raise ValueError('Persisted value differs: '+name)
        for i,text in enumerate(values['task_info']):
            info=json.loads(text)
            for side in ('ipsi','contra'):
                value=values[f'ankle_dorsiflexion_assistance_moment_{side}_Nm_kg'][i]
                if info['exo_state']=='no_exo':
                    if value!=0:raise ValueError('No-exo structural assistance not zero')
                elif value is not None and not math.isnan(value):raise ValueError('Unavailable ankle actuator represented as measurement')
        if not inspect_contract(b.to_pandas(use_threads=False),mode='phase').schema_passed:raise ValueError('Corrected structural validation failed')
    if len(seen)*150!=record['rows']:raise ValueError('Observation count differs')
    return len(seen)


def collect(baselines,proposal):
    converter_sha=proposal['original_code'][str(ROOT/ADAPTER)];records=[];bindings={};expected_phases={'Phase1And2','Phase3'};phases=set()
    for baseline in baselines:
        summary_path=baseline/'batch_summary.json';inventory_path=baseline/'source_inventory.json'
        summary=json.loads(summary_path.read_text());inventory=json.loads(inventory_path.read_text());phase=inventory['source']
        if inventory['dataset']!='gt24' or phase not in expected_phases or phase in phases:raise ValueError('Need distinct complete GT24 phase batches')
        phases.add(phase);items=inventory['recordings'];keys=[(r['subject'],r['recording']) for r in items]
        if len(set(keys))!=len(keys) or len(keys)!=inventory['recording_count'] or summary['batch_status']!='completed' or summary['remaining_recordings']!=0 or summary['planned_recordings']!=len(keys) or summary['completed_recordings']!=len(keys):raise ValueError('Incomplete batch inventory')
        source_root=Path(inventory['source_root']);actual={(s.name,t.name) for s in source_root.iterdir() if s.is_dir() and s.name.startswith('BT') for t in s.iterdir() if t.is_dir()}
        if actual!=set(keys):raise ValueError('Declared inventory does not cover current source recording folders')
        for p in [summary_path,inventory_path]:bindings[str(p.resolve())]=digest(p)
        declared=set();total=0
        for subject,recording in keys:
            if any('/' in x or x in ('.','..') for x in (subject,recording)):raise ValueError('Unsafe recording identity')
            folder=baseline/'gt24'/phase/subject/recording;manifest_path=folder/'conversion_manifest.json';manifest=json.loads(manifest_path.read_text())
            rows=validate_manifest(manifest,phase,subject,recording,converter_sha);total+=rows;declared.add(str(manifest_path.resolve()))
            expected={'conversion_manifest.json',*[x['name'] for x in manifest['outputs']]}
            if {p.name for p in folder.iterdir()}!=expected:raise ValueError('Unbound baseline record artifacts')
            records.append({'phase':phase,'subject':subject,'recording':recording,'folder':str(folder.resolve()),'rows':rows,'manifest_sha256':digest(manifest_path),'outputs':manifest['outputs'],'disposition':manifest['status']})
        if total!=summary['rows'] or total//150!=summary['observations']:raise ValueError('Batch aggregate mismatch')
        if {str(p.resolve()) for p in baseline.rglob('conversion_manifest.json')}!=declared:raise ValueError('Undeclared converted recordings')
    if phases!=expected_phases:raise ValueError('Both phase scopes required')
    return records,bindings


def main():
    p=argparse.ArgumentParser(description=__doc__);base=ROOT/'converted_datasets/reconversion_v2'
    p.add_argument('--baseline',type=Path,action='append',required=True);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true')
    p.add_argument('--proposal',type=Path,default=base/'swarm_backlog_20261021/gt24_ankle_negation_proposal');a=p.parse_args();out=a.output_root.resolve()
    if not out.is_relative_to(base) or out in [x.resolve() for x in a.baseline]:raise ValueError('New isolated destination required')
    pp=a.proposal/'preparation_manifest.json';proposal=json.loads(pp.read_text());pilot=base/'gt24_ankle_converter_pilot_v2_20261021/pilot_summary.json';completed=json.loads(pilot.read_text());pilotplan=pilot.parent/'plan.json'
    if completed['status']!='two_phase_ankle_converter_pilot_checked_unreviewed' or completed['plan_sha256']!=digest(pilotplan) or len(completed['records'])!=2:raise ValueError('Successful bound two-phase numerical pilot required')
    records,bindings=collect([x.resolve() for x in a.baseline],proposal)
    for path in [pp,pilot,pilotplan,Path(__file__),ROOT/'contributor_tools/run_gt24_ankle_converter_pilot.py',ROOT/'contributor_tools/prepare_gt24_ankle_fix.py',ROOT/'contributor_tools/preserve_um21_planar_estimates.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py',*sorted((ROOT/'contributor_tools/common').rglob('*.py'))]:bindings[str(path.resolve())]=digest(path)
    for i,record in enumerate(completed['records']):
        for name,key in [('reference.parquet','reference_sha256'),('corrected.parquet','corrected_sha256')]:bindings[str(pilot.parent/f'record_{i}'/name)]=record[key]
    verify(bindings)
    plan={'status':'prepared_not_executed','scientific_approval':False,'records':records,'bindings':bindings,'expected_observations':sum(r['rows']//150 for r in records),'mapping':FIELDS,'metadata':META}
    planpath=out/'plan.json'
    if out.exists():
        if not planpath.is_file() or list(out.iterdir())!=[planpath] or json.loads(planpath.read_text())!=plan:raise FileExistsError('Existing attempt preserved')
    else:out.mkdir(parents=True);planpath.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'status':'prepared_not_executed','records':len(records)}));return
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[name]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)));headroom(out)
    if windows_available_mib()<2816:raise MemoryError('Host startup reserve insufficient')
    import pyarrow as pa
    import pyarrow.parquet as pq
    pa.set_cpu_count(1);pa.set_io_thread_count(1);last=0.
    def guard():
        nonlocal last
        if time.monotonic()-last>=15:
            headroom(out)
            if windows_available_mib()<2048:raise MemoryError('Host runtime reserve insufficient')
            last=time.monotonic()
    result={'status':'running','scientific_approval':False,'plan_sha256':digest(planpath),'records':[],'observations':0,'limitations':['Source-documented coordinate correction, not independent anatomical posture measurement','Existing phase segmentation and IMU estimates unchanged','Original range/quality reports retained as baseline evidence only; corrected values require fresh scientific assessment']}
    def save():
        tmp=out/'adoption_summary.tmp';tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out/'adoption_summary.json')
    save()
    try:
        for record in records:
            guard();folder=Path(record['folder']);manifest=folder/'conversion_manifest.json'
            if digest(manifest)!=record['manifest_sha256']:raise ValueError('Baseline manifest changed')
            target=out/'gt24'/record['phase']/record['subject']/record['recording'];target.mkdir(parents=True)
            evidence=target/'baseline_evidence';evidence.mkdir()
            for entry in record['outputs']:
                if digest(folder/entry['name'])!=entry['sha256']:raise ValueError('Baseline artifact changed')
                if entry['name']!='phase.parquet':shutil.copyfile(folder/entry['name'],evidence/entry['name'])
            shutil.copyfile(manifest,evidence/manifest.name)
            observed=0;outputsha=None
            if record['rows']:
                source=folder/'phase.parquet';partial=target/'phase.parquet.partial';writer=None;headroom(out,source.stat().st_size)
                try:
                    for batch in pq.ParquetFile(source).iter_batches(batch_size=150,use_threads=False):
                        guard();table=transform(pa.Table.from_batches([batch]))
                        if writer is None:writer=pq.ParquetWriter(partial,table.schema,compression='zstd')
                        writer.write_table(table)
                finally:
                    if writer is not None:writer.close()
                observed=verify_shard(source,partial,record,guard);partial.replace(target/'phase.parquet');outputsha=digest(target/'phase.parquet')
            for entry in record['outputs']:
                if digest(folder/entry['name'])!=entry['sha256']:raise ValueError('Baseline changed during correction')
                if entry['name']!='phase.parquet' and digest(evidence/entry['name'])!=entry['sha256']:raise ValueError('Baseline sidecar copy differs')
            if digest(manifest)!=record['manifest_sha256'] or digest(evidence/manifest.name)!=record['manifest_sha256']:raise ValueError('Baseline manifest copy differs')
            rr={'phase':record['phase'],'subject':record['subject'],'recording':record['recording'],'disposition':record['disposition'],'observations':observed,'rows':150*observed,'phase_sha256':outputsha,'baseline_manifest_sha256':record['manifest_sha256'],'exact_unrelated_values_metadata_and_masks':True,'quality_status':'corrected_values_unassessed'}
            (target/'adoption_manifest.json').write_text(json.dumps(rr,indent=2)+'\n');result['records'].append(rr);result['observations']+=observed;save()
        if result['observations']!=plan['expected_observations'] or len(result['records'])!=len(records):raise ValueError('Final coverage differs')
        verify(bindings);result['status']='both_gt24_phase_batches_ankle_corrected_unreviewed'
    except Exception as error:result.update(status='failed_incomplete',reason=str(error));raise
    finally:save()


if __name__=='__main__':main()
