"""Bounded Complete/Parsed ankle correspondence pilot; no automatic execution.

Uses only stdlib. Preparation reads archive directories/file metadata, not CSV
values. --run reads at most 5000 rows per table and 8 MiB decompressed per
member. Failure to align timestamps within that prefix is deferred, not guessed.
This does not run the patched converter or validate physical anatomical poses.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.prepare_gt24_ankle_fix import README_SHA256
from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
TABLES={'angle_filt':('Joint_Angles_Filt.csv',''),'moment_filt':('Joint_Moments_Filt.csv','_moment'),'moment_filt_bio':('Bio_Joint_Moments.csv','_moment'),'velocity':('Joint_Velocities.csv','_velocity'),'power':('Net_Joint_Power.csv','_power'),'power_bio':('Bio_Joint_Power.csv','_power')}


def stat_identity(path):
    s=Path(path).stat();return {'path':str(Path(path).resolve()),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024**2),b''):value.update(chunk)
    return value.hexdigest()


def read_prefix(stream,columns,limit,guard):
    """Hash exactly the consumed CSV bytes, with bounded line/member size."""
    h=hashlib.sha256();size=0
    def lines():
        nonlocal size
        while True:
            guard();line=stream.readline(65537)
            if not line:break
            size+=len(line)
            if len(line)>65536 or size>8*1024**2:raise ValueError('CSV byte admission exceeded')
            h.update(line);yield line.decode('utf-8-sig')
    reader=csv.DictReader(lines())
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not set(columns)<=set(reader.fieldnames):raise ValueError('Missing/duplicate exact source fields')
    rows=[];previous=-math.inf
    for _ in range(limit):
        row=next(reader,None)
        if row is None:break
        values={k:float(row[k]) for k in columns}
        clock=values['time']
        if not math.isfinite(clock) or clock<=previous:raise ValueError('Source timestamps not finite/increasing')
        if any(math.isinf(x) for x in values.values()):raise ValueError('Infinite source value')
        previous=clock;rows.append(values)
    if len(rows)<3:raise ValueError('Insufficient bounded source samples')
    return rows,{'consumed_prefix_sha256':h.hexdigest(),'consumed_bytes':size,'rows_read':len(rows),'row_limit':limit,'scope':'consumed CSV prefix only; not full-file hash'}


def compare_rows(native,parsed,columns):
    by_time={r['time']:r for r in native};finite={c:0 for c in columns if c!='time'}
    for row in parsed:
        if row['time'] not in by_time:raise ValueError('alignment_deferred: exact Parsed clock absent from bounded Complete prefix')
        source=by_time[row['time']]
        for name in finite:
            a,b=source[name],row[name]
            if math.isnan(a)!=math.isnan(b):raise ValueError('Source missingness differs: '+name)
            if math.isnan(a):continue
            if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9):raise ValueError('Complete/Parsed values differ: '+name)
            finite[name]+=1
    return finite


def check_relations(tables):
    """Documented source operations, fixed rounding allowance; no fitted signs."""
    angle=tables['angle_filt'];times=[r['time'] for r in angle]
    if any([r['time'] for r in rows]!=times for rows in tables.values()):raise ValueError('Parsed counterpart clocks differ')
    report={}
    for side in ('l','r'):
        ac=f'ankle_angle_{side}';vc=ac+'_velocity';mc=ac+'_moment';pc=ac+'_power'
        derivative=0;powers={'net':0,'biological':0};max_error=0.
        for i in range(1,len(angle)-1):
            dt0=times[i]-times[i-1];dt1=times[i+1]-times[i]
            # README specifies uniform 200 Hz central differences. Never silently
            # use neighboring samples across a removed transition or time gap.
            if not math.isclose(dt0,.005,abs_tol=1e-9,rel_tol=0) or not math.isclose(dt1,.005,abs_tol=1e-9,rel_tol=0):continue
            a,b=angle[i-1][ac],angle[i+1][ac];v=tables['velocity'][i][vc]
            if all(math.isfinite(x) for x in (a,b,v)):
                expected=(b-a)/.01;error=abs(v-expected);max_error=max(max_error,error)
                if not math.isclose(v,expected,rel_tol=1e-6,abs_tol=1e-5):raise ValueError('Documented central derivative differs')
                derivative+=1
        for moment,power,label in [('moment_filt','power','net'),('moment_filt_bio','power_bio','biological')]:
            for m,v,p in zip(tables[moment],tables['velocity'],tables[power]):
                mv,vv,pv=m[mc],v[vc],p[pc]
                if math.isnan(mv) or math.isnan(vv):
                    if not math.isnan(pv):raise ValueError('Power missingness contradicts source operands')
                elif not math.isfinite(pv) or not math.isclose(pv,mv*vv*math.pi/180,rel_tol=1e-6,abs_tol=1e-6):raise ValueError('Documented power product differs')
                else:powers[label]+=1
        if not derivative:raise ValueError('No interior uniform-clock derivative evidence')
        report[side]={'interior_derivatives_checked':derivative,'maximum_derivative_error_deg_s':max_error,'finite_power_products':powers,'missing_power_channels_unassessed':[k for k,v in powers.items() if not v]}
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic'))
    p.add_argument('--output-root',type=Path,required=True);p.add_argument('--run',action='store_true');p.add_argument('--rows',type=int,default=5000);a=p.parse_args()
    if not 3<=a.rows<=5000:p.error('Row admission is 3..5000')
    out=a.output_root.resolve()
    if not out.is_relative_to(ROOT/'converted_datasets/reconversion_v2'):raise ValueError('Local isolated output required')
    readme=a.source_root/'readme.txt'
    if digest(readme)!=README_SHA256:raise ValueError('Released convention evidence changed')
    selections=[('Phase1And2','BT01','normal_walk_1_0-6_on','Complete/BT01/normal_walk_1'),('Phase3','BT20','normal_walk_1_1_0-6_on','Phase3_Complete/BT20/normal_walk_1_1')]
    records=[]
    for phase,subject,condition,member_folder in selections:
        archive=a.source_root/(phase+'_Complete.zip');folder=a.source_root/(phase+'_Parsed')/'Parsed'/subject/condition
        tables={}
        with zipfile.ZipFile(archive) as z:
            for kind,(native,suffix) in TABLES.items():
                name=member_folder+'/'+native
                matches=[x for x in z.infolist() if x.filename==name]
                if len(matches)!=1:raise ValueError('Ambiguous/missing exact archive member')
                info=matches[0];parsed=folder/f'{subject}_{condition}_{kind}.csv'
                tables[kind]={'member':name,'member_bytes':info.file_size,'member_crc32':info.CRC,'compressed_bytes':info.compress_size,'header_offset':info.header_offset,'parsed':stat_identity(parsed),'columns':['time',f'ankle_angle_l{suffix}',f'ankle_angle_r{suffix}']}
        records.append({'phase':phase,'subject':subject,'parsed_condition':condition,'archive':stat_identity(archive),'mapping_basis':'README task-name construction and exact subject/base trial; values and absolute clocks must independently match before acceptance','tables':tables})
    code={str(Path(__file__).resolve()):digest(__file__),str(ROOT/'contributor_tools/prepare_gt24_ankle_fix.py'):digest(ROOT/'contributor_tools/prepare_gt24_ankle_fix.py'),str(ROOT/'contributor_tools/preserve_mblue_planar_estimates.py'):digest(ROOT/'contributor_tools/preserve_mblue_planar_estimates.py')}
    plan={'status':'prepared_not_executed','scientific_approval':False,'records':records,'native_rows_per_table':a.rows,'parsed_rows_per_table':min(a.rows,256),'readme_sha256':README_SHA256,'code_sha256':code,'memory_admission_mib':256,'archive_identity_scope':'stat plus exact member CRC/size/offset; source evidence additionally hashes consumed member bytes at execution, not entire multi-GB archive'}
    path=out/'plan.json'
    if out.exists():
        if not path.is_file() or list(out.iterdir())!=[path] or json.loads(path.read_text())!=plan:raise FileExistsError('Preserve existing attempt')
    else:out.mkdir(parents=True);path.write_text(json.dumps(plan,indent=2)+'\n')
    if not a.run:print(json.dumps({'plan':str(path),'status':plan['status']}));return
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)));headroom(out)
    if windows_available_mib()<2304:raise MemoryError('Host startup reserve insufficient')
    started=time.monotonic();last=0.
    def guard():
        nonlocal last
        now=time.monotonic()
        if now-started>180:raise TimeoutError('Bounded pilot exceeded 180 seconds')
        if now-last>=15:
            headroom(out)
            if windows_available_mib()<2048:raise MemoryError('Host runtime reserve insufficient')
            last=now
    result={'status':'running','scientific_approval':False,'plan_sha256':digest(path),'records':[]}
    try:
        for record in records:
            guard();tables={};checks={}
            with zipfile.ZipFile(record['archive']['path']) as z:
                for kind,entry in record['tables'].items():
                    guard()
                    with z.open(entry['member']) as f:native,ns=read_prefix(f,entry['columns'],a.rows,guard)
                    with Path(entry['parsed']['path']).open('rb') as f:parsed,ps=read_prefix(f,entry['columns'],min(a.rows,256),guard)
                    checks[kind]={'native_prefix':ns,'parsed_prefix':ps,'finite_correspondence':compare_rows(native,parsed,entry['columns'])};tables[kind]=parsed
            result['records'].append({'phase':record['phase'],'subject':record['subject'],'condition':record['parsed_condition'],'tables':checks,'source_relations':check_relations(tables)})
        for record in records:
            if stat_identity(record['archive']['path'])!=record['archive']:raise ValueError('Archive changed')
            for entry in record['tables'].values():
                if stat_identity(entry['parsed']['path'])!=entry['parsed']:raise ValueError('Parsed source changed')
        if digest(readme)!=README_SHA256 or any(digest(k)!=v for k,v in code.items()):raise ValueError('Bound code/evidence changed')
        result['status']='bounded_native_parsed_ankle_correspondence_checked_unreviewed'
    except Exception as error:
        result.update(status='alignment_deferred' if 'alignment_deferred:' in str(error) else 'failed_unreviewed',reason=str(error));raise
    finally:(out/'source_comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'records':len(result['records'])}))


if __name__=='__main__':main()
