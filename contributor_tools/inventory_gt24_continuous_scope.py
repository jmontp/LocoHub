"""Enumerate all GT24 Complete/Parsed continuous-source scope without data loads."""
import argparse
import ast
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile
ROOT=Path(__file__).resolve().parents[1]
NATIVE_TABLES={'Activity_Flag.csv','Bio_Joint_Moments.csv','Bio_Joint_Power.csv','Exo.csv','Exo_Sim.csv','GroundFrame_GRFs.csv','Joint_Angles.csv','Joint_Angles_Filt.csv','Joint_Moments.csv','Joint_Moments_Filt.csv','Joint_Velocities.csv','Net_Joint_Power.csv','Virtual_IMUs.csv','Virtual_Insoles.csv'}
REQUIRED_PARSED={'angle_filt','moment_filt','grf','velocity','insole_sim'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def task_patterns(path):
    tree=ast.parse(path.read_text())
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='TASK_MAPPING' for x in n.targets))
    return ast.literal_eval(assignment.value)


def parsed_disposition(name,files,patterns):
    match=next(((task,task_id) for pattern,(task,task_id,info) in patterns.items() if re.search(pattern,name)),None)
    states=[state for state,suffixes in [('no_exo',('_noexo','_bare')),('powered',('_on','_hilo')),('worn_unpowered',('_off',))] if any(s in name for s in suffixes)]
    missing=sorted(REQUIRED_PARSED-set(files))
    if missing:return 'blocked_missing_required_source_tables',{'missing':missing}
    if not match or match[0] is None:return 'source_only_unmapped_task',{'matched_task_id':match[1] if match else None}
    if len(states)!=1:return 'source_only_ambiguous_exoskeleton_state',{'states':states}
    return 'canonical_parsed_candidate_requires_source_audit',{'task':match[0],'task_id':match[1],'exo_state':states[0]}


def inventory(source):
    adapter=ROOT/'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/convert_gtech_2024_phase_to_parquet.py';patterns=task_patterns(adapter)
    phases=[]
    for phase in ('Phase1And2','Phase3'):
        archive=source/(phase+'_Complete.zip');stat=archive.stat();groups=defaultdict(list);excluded=[];central=[]
        with zipfile.ZipFile(archive) as z:
            names=[i.filename for i in z.infolist()]
            if len(names)!=len(set(names)):raise ValueError('Duplicate archive entry identity')
            for item in z.infolist():
                entry={'name':item.filename,'bytes':item.file_size,'compressed_bytes':item.compress_size,'crc32':item.CRC,'header_offset':item.header_offset};central.append(entry)
                if item.is_dir():reason='directory_entry'
                elif '__MACOSX/' in item.filename:reason='macos_resource_fork'
                elif not item.filename.endswith('.csv'):reason='non_csv_artifact'
                else:
                    groups[str(Path(item.filename).parent)].append(entry);continue
                excluded.append({'name':item.filename,'reason':reason})
        dynamic=[];static=[]
        for folder,entries in sorted(groups.items()):
            tables={Path(x['name']).name for x in entries}
            if tables=={'Statics.csv'}:
                static.append({'folder':folder,'members':entries,'disposition':'static_calibration_table_not_dynamic_continuous_recording'});continue
            parts=Path(folder).parts
            if len(parts)!=3 or not parts[-2].startswith('BT'):raise ValueError('Unrecognized native recording identity')
            dynamic.append({'subject':parts[-2],'recording':parts[-1],'member_folder':folder,'members':entries,'missing_expected_tables':sorted(NATIVE_TABLES-tables),'extra_tables':sorted(tables-NATIVE_TABLES),'disposition':'source_preservation_required_canonical_labels_not_yet_reconciled','native_transition_samples_retained':True})
        native_by_subject=defaultdict(list)
        for record in dynamic:native_by_subject[record['subject']].append(record['recording'])
        parsed=[];root=source/(phase+'_Parsed')/'Parsed'
        for subject in sorted(x for x in root.iterdir() if x.is_dir() and x.name.startswith('BT')):
            for folder in sorted(x for x in subject.iterdir() if x.is_dir()):
                prefix=subject.name+'_'+folder.name+'_';files={}
                for path in sorted(folder.iterdir()):
                    if path.is_file() and path.name.startswith(prefix) and path.suffix=='.csv':
                        s=path.stat();files[path.name[len(prefix):-4]]={'path':str(path.resolve()),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
                disposition,details=parsed_disposition(folder.name,files,patterns)
                candidates=[name for name in native_by_subject[subject.name] if folder.name==name or folder.name.startswith(name+'_')]
                parsed.append({'subject':subject.name,'recording':folder.name,'folder':str(folder.resolve()),'files':files,'disposition':disposition,**details,'native_name_candidates_only':candidates,'native_membership_verified':False})
        phases.append({'phase':phase,'archive':{'path':str(archive.resolve()),'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,'central_directory_sha256':hashlib.sha256(json.dumps(central,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'full_archive_sha256':None},'dynamic_complete_recordings':dynamic,'static_source_tables':static,'excluded_archive_entries':excluded,'parsed_recordings':parsed,'counts':{'dynamic_complete_recordings':len(dynamic),'native_csv_tables':sum(len(r['members']) for r in dynamic),'static_groups':len(static),'parsed_recordings':len(parsed),'parsed_dispositions':dict(Counter(r['disposition'] for r in parsed))}})
    return {'status':'full_continuous_source_scope_enumerated_unreviewed','scientific_approval':False,'phases':phases,'code_sha256':{str(adapter):digest(adapter),str(Path(__file__).resolve()):digest(__file__)},'readme':{'path':str(source/'readme.txt'),'sha256':digest(source/'readme.txt')},'limitations':['Archive central directories and local filesystem metadata only; no scientific CSV values loaded','Complete includes native transition samples absent from Parsed; these scopes must never be equated','Native name candidates are not established lineage; exact source-clock/value membership required','No unsupported canonical task or actuator state is invented for native intervals','Excluded directory/resource entries and static calibration tables are explicitly accounted for, not silently discarded']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=inventory(a.source_root.resolve());a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'status':report['status'],'phases':[{**x['counts'],'phase':x['phase']} for x in report['phases']]}))


if __name__=='__main__':main()
