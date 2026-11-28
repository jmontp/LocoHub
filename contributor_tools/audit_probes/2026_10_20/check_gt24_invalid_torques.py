"""Check every README-listed failed-load-cell trial using bounded CSV reads."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
ROOT=Path(__file__).resolve().parents[3]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def invalid_trials(text):
    start=text.index('Due to a failure in one of the loadcells')
    section=text[start:].split('/////',1)[0]
    subject=side=None;records=[]
    for line in section.splitlines():
        stripped=line.strip()
        match=re.match(r'- (BT\d+)\b',stripped)
        if match:subject=match[1];side=None;continue
        match=re.match(r'- Invalid (left|right) leg joint torques',stripped)
        if match:side=match[1] if '(none)' not in stripped else None;continue
        if stripped.startswith('- ') and subject and side:
            name=stripped[2:]
            if not re.fullmatch(r'[a-z0-9_-]+',name):raise ValueError('Unrecognized trial name')
            records.append({'subject':subject,'side':side,'recording':name})
    keys=[(r['subject'],r['side'],r['recording']) for r in records]
    if not records or len(keys)!=len(set(keys)):raise ValueError('Empty or duplicate source exclusions')
    return records


def inspect_csv(path,side):
    before=path.stat();rows=0;counts={};other_finite=0
    with path.open(newline='') as stream:
        reader=csv.DictReader(stream)
        columns=[c for c in reader.fieldnames if c.endswith('_'+side[0]+'_moment')]
        if not columns:raise ValueError('Missing documented invalid-side torque columns')
        counts={c:{'finite':0,'nan':0,'infinite':0} for c in columns}
        others=[c for c in reader.fieldnames if c.endswith('_moment') and c not in columns]
        for row in reader:
            rows+=1
            for col in columns:
                value=float(row[col]);kind='finite' if math.isfinite(value) else 'nan' if math.isnan(value) else 'infinite'
                counts[col][kind]+=1
            other_finite+=sum(math.isfinite(float(row[c])) for c in others)
    after=path.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    return {'path':str(path),'sha256':digest(path),'rows':rows,'invalid_side_columns':counts,
        'opposite_side_finite_values':other_finite,
        'documented_invalid_values_are_all_nan':rows>0 and all(c['nan']==rows for c in counts.values())}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--readme',type=Path,default=ROOT/'contributor_tools/conversion_scripts/GaTech_2024_TaskAgnostic/dataset_readme.txt')
    p.add_argument('--source-root',type=Path,default=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/Phase1And2_Parsed/Parsed'))
    p.add_argument('--output-root',type=Path,required=True);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)))
    a.output_root.mkdir(parents=True,exist_ok=False)
    results=[]
    for record in invalid_trials(a.readme.read_text()):
        parent=a.source_root/record['subject'];exact=parent/record['recording']
        folders=[exact] if exact.is_dir() else sorted(x for x in parent.glob(record['recording']+'_*') if x.is_dir())
        result={**record,'files':[],'missing_variants':[],'matched_recordings':[x.name for x in folders]}
        if not folders:result['missing_variants'].append('recording')
        for folder in folders:
            for suffix in ['moment','moment_filt','moment_filt_bio']:
                path=folder/(record['subject']+'_'+folder.name+'_'+suffix+'.csv')
                if path.is_file():result['files'].append(inspect_csv(path,record['side']))
                else:result['missing_variants'].append(str(path))
        results.append(result)
    files=[f for r in results for f in r['files']]
    report={'status':'source_invalid_torque_review','scientific_approval':False,'readme_sha256':digest(a.readme),
        'probe_sha256':digest(Path(__file__)),'listed_trial_sides':len(results),'files_checked':len(files),
        'rows_checked':sum(f['rows'] for f in files),'files_with_finite_or_infinite_invalid_torques':sum(not f['documented_invalid_values_are_all_nan'] for f in files),
        'missing_variants':sum(len(r['missing_variants']) for r in results),'records':results,
        'limitations':['Source CSVs only; corrected-output preservation requires a separate readback','Missing torque channels do not invalidate the available joint angles','This check does not establish ankle signs, physical frames or event correctness']}
    (a.output_root/'source_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__':main()
