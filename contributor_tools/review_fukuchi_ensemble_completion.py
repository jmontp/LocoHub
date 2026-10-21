"""Bounded receipt/coverage review; no scientific array loading or conversion.

This verifies completed source-readback evidence, not anatomical correctness.
Run after the coordinator releases the numerical slot. Outputs are immutable.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zlib

MAX_JSON = 4 * 1024**2
EXPECTED_CONDITIONS = {'OC':42,'OF':42,'OS':42, **{f'T0{i}':51 for i in range(1,7)},'T07':40,'T08':36}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def read_json(path):
    with Path(path).open('rb') as stream:raw=stream.read(MAX_JSON+1)
    if len(raw)>MAX_JSON:raise ValueError('Receipt JSON admission exceeded')
    return json.loads(raw)


def add_binding(bindings,path,value):
    key=str(Path(path).resolve())
    if key in bindings and bindings[key]!=value:raise ValueError('Conflicting evidence hash')
    bindings[key]=value


def contained(root,path):
    path=Path(path).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Artifact outside run root')
    return path


def review(plan_path,expected_sha,summary_path,allow_subset=False):
    plan_path=Path(plan_path).resolve();summary_path=Path(summary_path).resolve()
    if digest(plan_path)!=expected_sha:raise ValueError('Plan changed')
    plan=read_json(plan_path);summary=read_json(summary_path)
    root=Path(plan['run_root']).resolve()
    if summary_path!=root/'summary.json':raise ValueError('Wrong run summary')
    if Path(plan['source_dir']).resolve()!=root/'sources' or Path(plan['output_root']).resolve()!=root/'pairs':raise ValueError('Invalid plan roots')
    bindings={str(plan_path):expected_sha,str(summary_path):digest(summary_path)}
    for group in ('input_sha256','code_sha256'):
        for path,sha in plan[group].items():add_binding(bindings,path,sha)
    expected={p['stem']:p for p in plan['pairs']}
    if len(expected)!=len(plan['pairs']):raise ValueError('Duplicate planned pair')
    full=summary['status']=='all_published_ensemble_pairs_source_checked_unreviewed'
    if not full and (not allow_subset or summary['status']!='explicit_subset_source_checked_unreviewed'):raise ValueError('No accepted completed scope')
    if summary.get('scientific_approval') is not False or summary['plan_sha256']!=expected_sha:raise ValueError('Summary approval/plan differs')
    receipts=summary['pairs'];seen=set();selected=[]
    for receipt in receipts:
        stem=receipt['stem']
        if stem in seen or stem not in expected or Path(stem).name!=stem:raise ValueError('Duplicate/unknown pair identity')
        seen.add(stem);pair=expected[stem];selected.append(pair)
        if receipt['rows']!=300 or receipt['observations']!=2 or receipt['status']!='ensemble_source_values_checked_unreviewed':raise ValueError('Pair receipt count/status differs')
        directory=contained(root,root/'pairs'/stem)
        mp=directory/'conversion_manifest.json';rp=directory/'source_readback.json';parquet=directory/'ensemble.parquet'
        acquisition_path=contained(root,root/'sources'/(stem+'.acquisition.json'))
        acquisition=read_json(acquisition_path);manifest=read_json(mp);report=read_json(rp)
        if acquisition['stem']!=stem or acquisition['plan_sha256']!=expected_sha or acquisition['source_doi']!=plan['source_doi']:raise ValueError('Acquisition identity differs')
        if acquisition['whole_archive_md5_verified'] is not False or acquisition['archive_url']!=plan['archive']['download_url']:raise ValueError('Acquisition provenance differs')
        members={Path(m['name']).name:m for m in pair['members'].values()}
        if set(pair['members'])!={'ang','knt'} or len(members)!=2 or set(acquisition['files'])!=set(members):raise ValueError('Exact acquired pair coverage differs')
        sources={}
        for name,member in members.items():
            record=acquisition['files'][name];source=contained(root,root/'sources'/name)
            if not 0<member['uncompressed_size']<=1024**2:raise ValueError('Source member admission exceeded')
            for field,expected_value in [('archive_member',member['name']),('bytes',member['uncompressed_size']),('compressed_size',member['compressed_size']),('crc32',member['crc32'])]:
                if record[field]!=expected_value:raise ValueError('Source archive ledger differs')
            crc=0;size=0
            with source.open('rb') as stream:
                for block in iter(lambda:stream.read(65536),b''):
                    size+=len(block)
                    if size>member['uncompressed_size']:raise ValueError('Source size exceeded')
                    crc=zlib.crc32(block,crc)
            if size!=member['uncompressed_size'] or crc&0xffffffff!=member['crc32']:raise ValueError('Source size/CRC differs')
            sources[str(source)]=record['sha256'];add_binding(bindings,source,record['sha256'])
        if manifest['source_stem']!=stem or manifest['plan_sha256']!=expected_sha or manifest['source_files']!=sources:raise ValueError('Converter source identity differs')
        if manifest['status']!='converted_ensemble_unreviewed' or manifest['rows']!=300 or manifest['ensembles']!=2 or manifest['individual_cycles']!=0 or manifest['scientific_approval'] is not False:raise ValueError('Conversion scope differs')
        if report['status']!='ensemble_source_values_checked_unreviewed' or report['ensembles']!=2 or report['individual_cycles']!=0 or report['scientific_approval'] is not False:raise ValueError('Readback scope differs')
        for document,field,filename in [(manifest,'converter_sha256','convert_fukuchi_ensemble_pair.py'),(report,'reviewer_sha256','check_ensemble_pilot.py')]:
            identities=[sha for path,sha in plan['code_sha256'].items() if Path(path).name==filename]
            if len(identities)!=1 or document.get(field)!=identities[0]:raise ValueError('Actual converter/reviewer identity differs')
        required={**sources,str(acquisition_path):digest(acquisition_path),str(plan_path):expected_sha,**plan['code_sha256']}
        for path,sha in required.items():
            if manifest['verified_input_sha256'].get(path)!=sha or report['verified_input_sha256'].get(path)!=sha:raise ValueError('Readback source/code binding missing')
        add_binding(bindings,mp,report['manifest_sha256']);add_binding(bindings,rp,receipt['readback_sha256'])
        add_binding(bindings,parquet,manifest['output_sha256']);add_binding(bindings,parquet,receipt['output_sha256'])
        if report['verified_input_sha256'].get(str(mp))!=report['manifest_sha256'] or report['verified_input_sha256'].get(str(parquet))!=manifest['output_sha256']:raise ValueError('Persisted readback output binding differs')
        for document in (manifest,report):
            for path,sha in document['verified_input_sha256'].items():add_binding(bindings,path,sha)
    count=len(seen)
    if not count or summary['full_inventory_pairs']!=len(expected) or summary['completed_pairs']!=count or summary['completed_rows']!=300*count or summary['completed_observations']!=2*count:raise ValueError('Summary totals differ')
    if full and seen!=set(expected):raise ValueError('Full status omits published pairs')
    conditions=dict(Counter(p['condition'] for p in selected));environments=dict(Counter(p['environment'] for p in selected));subjects=len({p['subject'] for p in selected})
    if full and (count!=508 or subjects!=51 or conditions!=EXPECTED_CONDITIONS or environments!={'overground':126,'treadmill':382}):raise ValueError('Published full cohort differs')
    for path,sha in bindings.items():
        if digest(path)!=sha:raise ValueError('Changed bound artifact: '+path)
    return {'status':'full_receipts_reconciled_unreviewed' if full else 'subset_receipts_reconciled_unreviewed',
            'scientific_approval':False,'catalog_activation':False,'plan_sha256':expected_sha,
            'pairs':count,'subjects':subjects,'observations':2*count,'rows':300*count,
            'conditions':conditions,'environments':environments,'bindings':bindings,
            'limitations':['Receipt verification does not rerun scientific values or establish anatomical conventions.',
                           'Left canonical signals remain unavailable; bilateral timing, raw strides, durations and within-participant SD are not reconstructed.',
                           'Whole-archive MD5 is not verified under bounded range acquisition.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-subset',action='store_true');a=p.parse_args()
    if a.output.exists():raise FileExistsError('Preserve existing review')
    result=review(a.plan,a.plan_sha256,a.summary,a.allow_subset)
    with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='bindings'}))


if __name__=='__main__':main()
