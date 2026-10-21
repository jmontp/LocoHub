"""Metadata-only GT23 scope ledger: never silently equate parsed windows to raw scope."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
CHANNELS=('Activity_Flag.csv','GroundFrame_GRFs.csv','Joint_Angle.csv','Joint_Moments.csv','Joint_Powers.csv','Joint_Velocities.csv','Raw_EMGs.csv','Real_IMUs.csv','Virtual_IMUs.csv','Virtual_Insoles.csv')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()


def read(path):
    with Path(path).open('rb') as f:data=f.read(4*1024**2+1)
    if len(data)>4*1024**2:raise MemoryError('Metadata admission exceeded')
    return json.loads(data)


def scope(records,publisher,local_folders):
    keys=[(r['subject'],r['parsing']) for r in records]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate parsing inventory')
    by_record={}
    for r in records:by_record.setdefault((r['subject'],r['recording']),[]).append(r)
    members={}
    for row in publisher:
        p=PurePosixPath(row['name'])
        if len(p.parts)!=4 or p.parts[1]!='CSV_Data' or row['name'].endswith('/'):continue
        if '..' in p.parts or p.is_absolute():raise ValueError('Unsafe publisher source path')
        key=(p.parts[0],p.parts[2]);channels=members.setdefault(key,{})
        if p.name in channels:raise ValueError('Duplicate publisher source member')
        channels[p.name]=row
    if set(local_folders)!=set(members):raise ValueError('Local and publisher recording folder scope differs')
    if set(by_record)-set(members):raise ValueError('Parsing references absent source recording')
    result=[]
    for key,channels in sorted(members.items()):
        if set(channels)!=set(CHANNELS):raise ValueError('Published channel scope differs')
        parsed=by_record.get(key,[])
        result.append({'subject':key[0],'recording':key[1],'parsing_files':[r['parsing'] for r in parsed],
             'nonempty_parsing_files':[r['parsing'] for r in parsed if r['has_intervals']],
             'disposition':'parsed_windows_and_complete_source_channels' if parsed else 'unsegmented_source_channels_no_invented_cycles',
             'semantic_assessment':'Recording name retained; activity/calibration category not inferred from absence of parsing.',
             'publisher_files':[{k:r[k] for k in ('name','crc32','uncompressed_size')} for r in channels.values()]})
    return {'status':'metadata_scope_prepared_not_converted','scientific_approval':False,'subjects':len({key[0] for key in members}),
            'parsing_inventory_entries':len(records),'empty_parsing_entries':sum(not r['has_intervals'] for r in records),
            'raw_recordings':len(result),'mapped_raw_recordings':len(by_record),'unmapped_raw_recordings':len(set(members)-set(by_record)),
            'published_csv_files':sum(len(r['publisher_files']) for r in result),
            'published_csv_bytes':sum(f['uncompressed_size'] for r in result for f in r['publisher_files']),
            'records':result,'parsing_entries':records,
            'limitations':['Publisher CRC/size metadata identifies expected bytes; actual full local bytes have not been compared in this metadata-only step.',
                           'Existing six-input conversion does not retain all ten original CSV channels; preserve source companions before claiming full recording coverage.',
                           'Markers, external loads, model/Statics metadata, transforms and C3D remain original source artifacts; this ledger scopes CSV channels and parsing windows, not every published archive.']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--publisher-directory',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    folders={(x.parent.parent.name,x.name) for x in (a.source_root/'RawData').glob('AB*/CSV_Data/*') if x.is_dir()}
    result=scope(read(a.inventory)['records'],read(a.publisher_directory),folders)
    result['bindings']={str(x.resolve()):digest(x) for x in (a.inventory,a.publisher_directory,Path(__file__))};result['source_root']=str(a.source_root.resolve())
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','parsing_entries','bindings','limitations')}))

if __name__=='__main__':main()
