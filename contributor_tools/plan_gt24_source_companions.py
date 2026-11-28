"""Header-only all869 GT24 source-only companions; no scientific data reads."""
import argparse,csv,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unit(kind,column,readme):
 if column=='time':return 's'
 if kind=='activity_flag':return 'boolean' if column in ('left','right') else None
 sections=re.split(r'(?m)^([a-z_]+)\.csv:',readme)
 body=None
 for index in range(1,len(sections),2):
  if sections[index]==kind:body=sections[index+1];break
 if body is None:raise ValueError('Publisher section missing: '+kind)
 for line in body.splitlines():
  match=re.match(r'^\s+([\w<>]+)\s+\(([^)]+)\)\s*$',line)
  if not match:continue
  pattern=re.escape(match[1]).replace('<side>','[lr]')
  if match[1].startswith('pelvis_imu_<side>_'):pattern=pattern.replace('pelvis_imu_[lr]_','pelvis_imu_(?:[lr]_)?')
  if re.fullmatch(pattern,column):return {'sec':'s','m/s^2':'m/s2'}.get(match[2],match[2])
 return None


def prepare(inventory,readme,output):
 inventory=Path(inventory).resolve();readme=Path(readme).resolve();data=json.loads(inventory.read_text());text=readme.read_text();records=[];profiles={};seen=set()
 for phase in data['phases']:
  for source in phase['parsed_recordings']:
   if source['disposition']!='source_only_unmapped_task':continue
   key=(phase['phase'],source['subject'],source['recording'])
   if key in seen:raise ValueError('Duplicate source identity')
   seen.add(key);files=[];folder=Path(source['folder'])
   if {p.resolve() for p in folder.iterdir() if p.is_file()}!={Path(f['path']).resolve() for f in source['files'].values()}:raise ValueError('Uninventoried source stream')
   for kind,f in sorted(source['files'].items()):
    path=Path(f['path']);st=path.stat()
    if path.name!=f"{key[1]}_{key[2]}_{kind}.csv" or path.parent!=folder or (st.st_size,st.st_mtime_ns)!=(f['bytes'],f['mtime_ns']):raise ValueError('Source identity/stat differs')
    with path.open('rb') as stream:header=stream.readline(65537)
    if len(header)>65536 or not header.endswith(b'\n'):raise ValueError('Header admission exceeded')
    columns=next(csv.reader([header.decode('utf-8-sig').rstrip('\r\n')]))
    if not columns or 'time' not in columns or len(columns)!=len(set(columns)):raise ValueError('Invalid source header')
    profile=hashlib.sha256(kind.encode()+b'\0'+header).hexdigest()
    profiles.setdefault(profile,{'source_kind':kind,'header_sha256':hashlib.sha256(header).hexdigest(),'columns':[{'source_name':c,'proposed_alias':f'source_{kind}__{c}','source_unit':unit(kind,c,text),'status':'documented_source_unit' if unit(kind,c,text) is not None else 'unit_unassessed'} for c in columns]})
    files.append({**f,'kind':kind,'header_profile':profile})
   records.append({'phase':key[0],'subject':key[1],'recording':key[2],'source_recording_id':'gt24:'+'/'.join(key),'source_metadata':{'phase':key[0],'canonical_task':None,'source_folder_label':key[2],'conditions_uninterpreted':True},'files':files,'all_csv_bytes':sum(f['bytes'] for f in files),'canonical_task':None,'scientific_approval':False})
 if len(records)!=869:raise ValueError('Exact869source-only identities required')
 result={'status':'all869_source_companions_header_inventory_unreviewed','scientific_approval':False,'bindings':{str(p):digest(p) for p in (inventory,readme,Path(__file__).resolve())},'readme':str(readme),'records':records,'header_profiles':profiles,'counts':{'records':869,'files':sum(len(r['files']) for r in records),'bytes':sum(r['all_csv_bytes'] for r in records)},'limits':'Only≤64KiBheaderperstream; no numericvalues. Parsed transitions absent; sourceonlyunmapped tasklabels uncanonicalized; original clocks distinct.'}
 with Path(output).open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
 return result['counts']

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inventory',type=Path,default=BASE/'gt24_full_continuous_scope_20261021/source_inventory.json');p.add_argument('--readme',type=Path,default=Path('/mnt/s/locomotion_data/GaTech_2024_TaskAgnostic/readme.txt'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.inventory,a.readme,a.output)))
