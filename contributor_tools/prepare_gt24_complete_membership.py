"""Prepare full-scope GT24 native/Parsed membership jobs; explicit --record-index runs one.

No ZIP extraction. Each job streams a single candidate's projected tables to EOF,
under an externally serialized worker guard. Prefix candidates stay unverified
until all supplied table clocks and projected values match. This is not conversion.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from contributor_tools.match_gt24_complete_intervals import ProjectedCSV, compare_membership, require_shared_membership
from contributor_tools.preserve_mblue_planar_estimates import digest,headroom,windows_available_mib
TABLES={'angle_filt':'Joint_Angles_Filt.csv','moment_filt':'Joint_Moments_Filt.csv','moment_filt_bio':'Bio_Joint_Moments.csv','velocity':'Joint_Velocities.csv','grf':'GroundFrame_GRFs.csv','insole_sim':'Virtual_Insoles.csv','exo':'Exo.csv'}


def stat_identity(path):
    path=Path(path);s=path.stat()
    return {'path':str(path.resolve()),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}


def source_columns():
    fields={kind:{'time'} for kind in TABLES}
    for leg in ('l','r'):
        for joint in ('hip_flexion','knee_angle','ankle_angle'):
            fields['angle_filt'].add(joint+'_'+leg)
            fields['velocity'].add(joint+'_'+leg+'_velocity')
            for kind in ('moment_filt','moment_filt_bio'):fields[kind].add(joint+'_'+leg+'_moment')
        for axis in ('x','y','z'):fields['grf'].add(f'fp_{leg}_force_{axis}')
        for axis in ('x','z'):fields['insole_sim'].add(f'insole_{leg}_cop_{axis}')
        for joint in ('hip','knee'):fields['exo'].add(f'{joint}_angle_{leg}_torque_interaction')
    return fields


def verify(bindings):
    for name,expected in bindings.items():
        if digest(name)!=expected:raise ValueError('Bound evidence changed: '+name)


def build_plan(inventory_path):
    inventory=json.loads(inventory_path.read_text())
    if inventory['status']!='full_continuous_source_scope_enumerated_unreviewed':raise ValueError('Full scope inventory required')
    if {phase['phase'] for phase in inventory['phases']}!={'Phase1And2','Phase3'} or len(inventory['phases'])!=2:raise ValueError('Both source phases required')
    verify(inventory['code_sha256']);verify({inventory['readme']['path']:inventory['readme']['sha256']})
    jobs=[];unresolved=[]
    for phase in inventory['phases']:
        native={(r['subject'],r['recording']):r for r in phase['dynamic_complete_recordings']}
        for parsed in phase['parsed_recordings']:
            if not parsed['native_name_candidates_only']:
                unresolved.append({'phase':phase['phase'],'subject':parsed['subject'],'recording':parsed['recording'],'reason':'no_native_name_candidate; requires independent identity reconciliation'})
            for candidate in parsed['native_name_candidates_only']:
                record=native[(parsed['subject'],candidate)]
                members={Path(x['name']).name:x for x in record['members']}
                missing=[key for key in ('angle_filt','moment_filt','velocity','grf','insole_sim') if key not in parsed['files']]
                if missing:
                    unresolved.append({'phase':phase['phase'],'subject':parsed['subject'],'recording':parsed['recording'],'reason':'missing_required_parsed_tables','tables':missing});continue
                tables=[]
                for kind,name in TABLES.items():
                    if kind not in parsed['files']:continue
                    if name not in members:raise ValueError('Native source table absent: '+name)
                    tables.append({'kind':kind,'member':members[name],'parsed':parsed['files'][kind],'requested_columns':sorted(source_columns()[kind])})
                jobs.append({'phase':phase['phase'],'subject':parsed['subject'],'native_recording':candidate,'parsed_recording':parsed['recording'],'archive':phase['archive'],'tables':tables,'parsed_disposition':parsed['disposition'],'omitted_parsed_tables':sorted(set(parsed['files'])-set(TABLES)),'absent_optional_tables':sorted(set(TABLES)-set(parsed['files']))})
    code=[Path(__file__),ROOT/'contributor_tools/match_gt24_complete_intervals.py']
    # Bind all imported local code; source numerical libraries are never imported.
    code.append(ROOT/'contributor_tools/preserve_mblue_planar_estimates.py')
    bindings={str(p.resolve()):digest(p) for p in code}
    bindings.update(inventory['code_sha256'])
    bindings[str(inventory_path)]=digest(inventory_path)
    bindings[inventory['readme']['path']]=inventory['readme']['sha256']
    return {'status':'prepared_not_executed','inventory':str(inventory_path),'bindings':bindings,'jobs':jobs,'unresolved_source_membership':unresolved,'worker_limit_mib':256,'source_scope':'Every inventoried Parsed candidate in both phases; Complete coverage requires union after unique membership resolution','limits':['No wholesale extraction or raw source duplication','No claim for omitted table fields or anatomical convention','Unmatched Complete intervals remain source-only; no invented task or actuator labels','Full native transition coverage is distinct from canonical Parsed exports']}


def fieldnames(stream):
    line=stream.readline(65537)
    if len(line)>65536:raise ValueError('CSV header admission exceeded')
    fields=next(csv.reader([line.decode('utf-8-sig')]))
    if not fields or len(fields)!=len(set(fields)):raise ValueError('Duplicate or empty CSV header')
    return set(fields)


def checked_projection(native_fields, parsed_fields, requested, kind):
    requested=set(requested)
    if (native_fields & requested)!=(parsed_fields & requested) or 'time' not in native_fields:
        raise ValueError('Source projected field availability differs')
    selected=native_fields & requested
    if selected=={'time'}:raise ValueError('Timestamp-only membership evidence is insufficient')
    if kind=='angle_filt':
        required={f'{joint}_{leg}' for joint in ('hip_flexion','knee_angle','ankle_angle') for leg in ('l','r')}
        if not required<=selected:raise ValueError('Required bilateral joint angle source fields absent')
    return sorted(selected)


def checked_report_intervals(report):
    intervals=require_shared_membership(report['tables'])
    if intervals!=report['matched_intervals']:raise ValueError('Top-level intervals differ from table evidence')
    return intervals


def run_one(planpath,index):
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    plan_sha=digest(planpath);plan=json.loads(planpath.read_text());verify(plan['bindings'])
    if not 0<=index<len(plan['jobs']):raise ValueError('Candidate job index outside plan')
    job=plan['jobs'][index]
    archive=Path(job['archive']['path']);before=stat_identity(archive)
    if any(before[k]!=job['archive'][k] for k in ('path','bytes','mtime_ns')):raise ValueError('Archive identity changed')
    target=planpath.parent/'records'/f'{index:06d}.json'
    if target.exists():raise FileExistsError('Preserve existing membership evidence')
    target.parent.mkdir(exist_ok=True)
    last=0.;started=time.monotonic()
    def guard():
        nonlocal last
        now=time.monotonic()
        if now-started>1800:raise RuntimeError('Finite worker time admission exceeded')
        if now-last>=15:
            headroom(planpath.parent)
            if windows_available_mib()<2048:raise RuntimeError('Windows reserve below 2048 MiB')
            last=now
    headroom(planpath.parent)
    available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    if available<3584*1024:raise MemoryError('WSL startup reserve below 3584 MiB')
    if windows_available_mib()<2816:raise RuntimeError('Windows startup reserve below 2816 MiB')
    results={};parsed_identities=[]
    with zipfile.ZipFile(archive) as z:
        for table in job['tables']:
            guard();member=table['member'];info=z.getinfo(member['name'])
            if (info.file_size,info.compress_size,info.CRC,info.header_offset)!=(member['bytes'],member['compressed_bytes'],member['crc32'],member['header_offset']):raise ValueError('Archive member identity changed')
            parsed=Path(table['parsed']['path']);identity=stat_identity(parsed)
            if identity!=table['parsed']:raise ValueError('Parsed source identity changed')
            parsed_identities.append(identity)
            with z.open(info) as a,parsed.open('rb') as b:
                af,bf=fieldnames(a),fieldnames(b)
            requested=set(table['requested_columns'])
            columns=checked_projection(af,bf,requested,table['kind'])
            with z.open(info) as a,parsed.open('rb') as b:
                result=compare_membership(ProjectedCSV(a,columns,guard),ProjectedCSV(b,columns,guard))
            result['unavailable_requested_fields']=sorted(requested-af)
            results[table['kind']]=result
    passed=all(r['membership_verified'] for r in results.values())
    intervals=require_shared_membership(results) if passed else None
    verify(plan['bindings'])
    if stat_identity(archive)!=before or any(stat_identity(x['path'])!=x for x in parsed_identities):raise ValueError('Source changed during check')
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed during source check')
    report={'status':'native_parsed_candidate_checked_unreviewed' if passed else 'native_parsed_candidate_rejected','scientific_approval':False,'membership_verified':passed,'plan_sha256':digest(planpath),'job_index':index,'phase':job['phase'],'subject':job['subject'],'native_recording':job['native_recording'],'parsed_recording':job['parsed_recording'],'matched_intervals':intervals,'tables':results,'native_scope_complete':False,'limitations':plan['limits']}
    with target.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({'status':report['status'],'report':str(target)}))


def union_ranges(intervals):
    result=[]
    for low,high in sorted(intervals):
        if low<0 or high<low:raise ValueError('Invalid source interval')
        if result and low<=result[-1][1]+1:result[-1][1]=max(result[-1][1],high)
        else:result.append([low,high])
    return result


def summarize(planpath):
    plan=json.loads(planpath.read_text());verify(plan['bindings']);plan_sha=digest(planpath)
    inventory=json.loads(Path(plan['inventory']).read_text())
    candidates={};native={};report_hashes={}
    for index,job in enumerate(plan['jobs']):
        path=planpath.parent/'records'/f'{index:06d}.json'
        report=json.loads(path.read_text());report_hashes[str(path)]=digest(path)
        key=(job['phase'],job['subject'],job['parsed_recording'])
        if report['plan_sha256']!=plan_sha or report['job_index']!=index or any(report[k]!=job[k] for k in ('phase','subject','native_recording','parsed_recording')):raise ValueError('Candidate result identity differs')
        if report['status'] not in ('native_parsed_candidate_checked_unreviewed','native_parsed_candidate_rejected'):raise ValueError('Candidate result not terminal')
        if report['membership_verified']!=(report['status']=='native_parsed_candidate_checked_unreviewed'):raise ValueError('Contradictory result')
        candidates.setdefault(key,[])
        nkey=(job['phase'],job['subject'],job['native_recording'])
        entry=native.setdefault(nkey,{'tables':{},'intervals':[]})
        for kind,result in report['tables'].items():
            if kind in entry['tables'] and entry['tables'][kind]!=result['native']:raise ValueError('Native source identity changed between candidate checks')
            entry['tables'][kind]=result['native']
        if report['membership_verified']:
            intervals=checked_report_intervals(report)
            candidates[key].append((nkey,intervals))
    unresolved=list(plan['unresolved_source_membership'])
    for key,positive in candidates.items():
        if len(positive)!=1:
            unresolved.append({'phase':key[0],'subject':key[1],'recording':key[2],'reason':'no_unique_verified_native_membership','positive_candidates':len(positive)})
        else:
            nkey,intervals=positive[0]
            native[nkey]['intervals'].extend((x['first_row'],x['last_row']) for x in intervals)
    ledger=[]
    for phase in inventory['phases']:
        for record in phase['dynamic_complete_recordings']:
            key=(phase['phase'],record['subject'],record['recording']);entry=native.get(key)
            item={'phase':key[0],'subject':key[1],'recording':key[2]}
            if entry is None:
                item.update(status='native_not_read_no_candidate',native_rows=None,unmatched_native_rows=None)
            else:
                tables=entry['tables'];n=tables['angle_filt']['rows'];ranges=union_ranges(entry['intervals']);cursor=0;gaps=[]
                for low,high in ranges:
                    if high>=n:raise ValueError('Membership interval exceeds native source')
                    if low>cursor:gaps.append([cursor,low-1])
                    cursor=high+1
                if cursor<n:gaps.append([cursor,n-1])
                item.update(status='native_projected_source_scanned',native_rows=n,verified_unique_parsed_intervals=ranges,unmatched_native_intervals=gaps,unmatched_native_rows=sum(b-a+1 for a,b in gaps),source_tables=tables)
            ledger.append(item)
    verify(plan['bindings']);verify(report_hashes)
    if digest(planpath)!=plan_sha:raise ValueError('Plan changed during aggregation')
    return {'status':'all_planned_candidate_checks_aggregated_unreviewed','scientific_approval':False,'plan_sha256':plan_sha,'candidate_report_hashes':report_hashes,'native_recordings':ledger,'unresolved_parsed_membership':unresolved,'complete_native_canonical_coverage':False,'limitation':'Only uniquely verified Parsed intervals are covered. Native transitions/unmatched intervals and unread recordings remain explicit; no inferred task or exo state.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory',type=Path)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--record-index',type=int)
    parser.add_argument('--summarize',action='store_true')
    args=parser.parse_args();root=args.output_root.resolve();planpath=root/'plan.json'
    if not root.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Isolated local scientific output required')
    if args.summarize:
        report=summarize(planpath)
        with (root/'coverage_summary.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
        print(json.dumps({'status':report['status']}));return
    if args.record_index is not None:
        run_one(planpath,args.record_index);return
    if args.inventory is None:raise ValueError('Inventory required for preparation')
    plan=build_plan(args.inventory.resolve());root.mkdir(parents=True,exist_ok=False)
    planpath.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'status':plan['status'],'candidate_jobs':len(plan['jobs']),'unresolved':len(plan['unresolved_source_membership']),'plan':str(planpath)}))

if __name__=='__main__':main()
