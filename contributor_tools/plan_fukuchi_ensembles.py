"""Metadata-only complete participant-condition ensemble inventory; no downloads."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
MEMBER=re.compile(r'51subjs/(WBDS(\d{2})walk(O[SCF]|T0[1-8]))(ang|knt)\.txt')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(directory, metadata):
    pairs={};seen=set();by_name={}
    for row in metadata:
        name=row['FileName']
        if name in by_name:raise ValueError('Duplicate metadata filename')
        by_name[name]=row
    for member in directory:
        match=MEMBER.fullmatch(member['name'])
        if not match:
            if member['name'].endswith(('ang.txt','knt.txt')):raise ValueError('Unrecognized processed member')
            continue
        stem,subject,condition,kind=match.groups()
        if member['name'] in seen:raise ValueError('Duplicate archive member')
        seen.add(member['name'])
        name=Path(member['name']).name
        if name not in by_name or int(by_name[name]['Subject'])!=int(subject):raise ValueError('Metadata/filename identity mismatch')
        if member['method']!=8 or member['flags']&1 or member['uncompressed_size']>1024**2 or member['compressed_size']>1024**2:raise ValueError('Unsupported member admission')
        pair=pairs.setdefault(stem,{'stem':stem,'subject':'FU18_'+subject,'condition':condition,'environment':'overground' if condition[0]=='O' else 'treadmill','age_group':by_name[name]['AgeGroup'],'members':{}})
        if pair['age_group']!=by_name[name]['AgeGroup']:raise ValueError('Inconsistent cohort metadata')
        pair['members'][kind]=dict(member)
    expected={name for name in by_name if name.endswith(('ang.txt','knt.txt'))}
    if expected!={Path(name).name for name in seen}:raise ValueError('Archive/metadata processed coverage mismatch')
    if any(set(pair['members'])!={'ang','knt'} for pair in pairs.values()):raise ValueError('Unpaired ensemble source')
    records=sorted(pairs.values(),key=lambda pair:pair['stem'])
    subjects=sorted({pair['subject'] for pair in records})
    absent={subject:[condition for condition in ['OS','OC','OF']+[f'T0{i}' for i in range(1,9)] if not any(p['subject']==subject and p['condition']==condition for p in records)] for subject in subjects}
    members=[m for pair in records for m in pair['members'].values()]
    return {'pairs':records,'summary':{'subjects':len(subjects),'pairs':len(records),'members':len(members),'conditions':dict(sorted(collections.Counter(pair['condition'] for pair in records).items())),'environments':dict(collections.Counter(pair['environment'] for pair in records)),'cohort_subjects':{group:len({pair['subject'] for pair in records if pair['age_group']==group}) for group in sorted({pair['age_group'] for pair in records})},'compressed_payload_bytes':sum(m['compressed_size'] for m in members),'uncompressed_bytes':sum(m['uncompressed_size'] for m in members),'largest_uncompressed_member_bytes':max(m['uncompressed_size'] for m in members),'range_bytes_including_local_headers_and_names':sum(m['compressed_size']+30+len(m['name'].encode()) for m in members),'absent_condition_pairs':{s:c for s,c in absent.items() if c},'planned_side_observations_upper_bound':2*len(records),'planned_rows_upper_bound':300*len(records)}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    paths=[args.source_evidence/'ascii_zip_directory.json',args.source_evidence/'WBDSinfo.csv']
    with paths[1].open() as stream:metadata=list(csv.DictReader(stream))
    result=inventory(json.loads(paths[0].read_text()),metadata)
    archive_path=ROOT/'contributor_tools/conversion_scripts/Fukuchi_2018_Walking/source_evidence/figshare_v6_inventory.json'
    archive=next(f for f in json.loads(archive_path.read_text())['files'] if f['name']=='WBDSascii.zip')
    result.update(status='metadata_inventory_complete_no_full_conversion',scientific_approval=False,source_doi='10.6084/m9.figshare.5722711.v6',license='CC BY 4.0',archive=archive,input_sha256={str(p.resolve()):digest(p) for p in paths+[archive_path]},prior_acquisition_upper_bound_bytes=2341461,
                  acquisition='Two bounded Range requests per member: exact30-byte local header, then filename bytes plus compressed payload using header-derived offset; extra fields skipped by offset. Validate206 and Content-Range, local/central filename and method, decompressed size and CRC32. Record SHA256; do not claim whole archive MD5 verified.',
                  scientific_scope='Participant-condition ensemble means only. Missing old gait-event files do not block already processed means; they remain relevant to a separate raw-cycle reconstruction.',
                  speed_rule='Keep published condition codes. Processed metadata has no actual gait speed; do not copy a raw-trial speed or assign a population mean.')
    # Header and filename are separate requests if a ZIP extra field intervenes.
    result['acquisition']='Bounded Range requests:30-byte local header, exact filename bytes, exact compressed payload at header-derived offset. Skip extra fields by offset. Validate206/Content-Range, names/method, decompressed size and CRC32; record SHA256. Never claim whole-archive MD5 verification.'
    result['request_budget_reserved_bytes']=result['summary']['range_bytes_including_local_headers_and_names']+3*result['summary']['members']
    result['cumulative_acquisition_upper_bound_bytes']=2341461+result['request_budget_reserved_bytes']
    if result['cumulative_acquisition_upper_bound_bytes']>16*1024**2:raise ValueError('Original16 MiB acquisition budget exceeded')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
