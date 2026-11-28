"""Independent native ZIP/gzip byte readback and residual row accounting.

No writer import, source array load, canonical label or repaired clock. All native
CSV columns remain available verbatim, including tables outside Parsed matching.
"""
import argparse,csv,decimal,gzip,hashlib,json,os,resource,shutil,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def digest(path,guard=lambda:None):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):guard();h.update(block)
 return h.hexdigest()


def verify(bindings,guard=lambda:None):
 for path,sha in bindings.items():
  if digest(path,guard)!=sha:raise ValueError('Native audit bound artifact changed')


def coverage(record,member_name,rows,source_sha,table_names):
 """Only hash-bound, same-table membership can remove rows from residual scope."""
 evidence=record['coverage'];kind=next((k for k,name in table_names.items() if name==Path(member_name).name),None)
 table=evidence.get('source_tables',{}).get(kind)
 if table is None:
  return {'matched_rows':0,'residual_rows':rows,'verified_unique_parsed_intervals':[],'residual_intervals':[[0,rows-1]] if rows else [],'basis':'entire_stream_source_only_no_verified_table_membership'}
 if table['rows']!=rows or table['full_csv_sha256']!=source_sha:raise ValueError('Membership native table hash/count differs')
 intervals=evidence.get('verified_unique_parsed_intervals',[]);cursor=0;gaps=[];covered=0
 for pair in intervals:
  if len(pair)!=2 or any(type(n) is not int for n in pair):raise ValueError('Invalid native row interval')
  low,high=pair
  if low<cursor or high<low or high>=rows:raise ValueError('Overlapping/out-of-range native interval')
  if low>cursor:gaps.append([cursor,low-1])
  covered+=high-low+1;cursor=high+1
 if cursor<rows:gaps.append([cursor,rows-1])
 if rows!=evidence['native_rows'] or gaps!=evidence['unmatched_native_intervals'] or rows-covered!=evidence['unmatched_native_rows']:raise ValueError('Residual summary contradicts native row evidence')
 return {'matched_rows':covered,'residual_rows':rows-covered,'verified_unique_parsed_intervals':intervals,'residual_intervals':gaps,'basis':'unique_membership_only_bound_native_table_hash; no_task_or_anatomy_approval'}


def clock_rows(path,guard=lambda:None):
 csv.field_size_limit(1024**2);rows=0;previous=None;diagnostics={'missing_or_nonfinite':0,'duplicates':0,'decreases':0,'non_numeric':0}
 with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as stream:
  reader=csv.reader(stream,strict=True);header=next(reader,None)
  if not header or len(header)!=len(set(header)):raise ValueError('Unassessed malformed native header')
  index=header.index('time') if 'time' in header else None
  for row in reader:
   if len(row)!=len(header):raise ValueError('Unassessed malformed native row width')
   if rows%512==0:guard()
   if index is not None:
    try:value=decimal.Decimal(row[index])
    except decimal.InvalidOperation:diagnostics['non_numeric']+=1;value=None
    if value is None or not value.is_finite():diagnostics['missing_or_nonfinite']+=1
    else:
     if previous is not None:diagnostics['duplicates']+=int(value==previous);diagnostics['decreases']+=int(value<previous)
     previous=value
   rows+=1
 return rows,{'original_columns':header,'time_column_present':index is not None,'clock_units':'unassessed_original_source_units','clock_diagnostics':diagnostics,'clock_policy':'preserved_without_repair; row index is per original CSV stream'}


def audit_record(record,folder,producer,table_names,guard=lambda:None):
 folder=Path(folder);archive=Path(record['archive']['path']);stat=archive.stat();before=(stat.st_size,stat.st_mtime_ns)
 if before!=(record['archive']['bytes'],record['archive']['mtime_ns']):raise ValueError('Native archive stat differs')
 expected={m['name']:m for m in record['members']};streams=producer['streams']
 if len(expected)!=len(record['members']) or len(streams)!=len(expected) or {s['member'] for s in streams}!=set(expected):raise ValueError('Full native member scope required')
 artifacts={};results=[]
 with zipfile.ZipFile(archive) as source:
  if len(source.namelist())!=len(set(source.namelist())):raise ValueError('Duplicate native ZIP members')
  for stream in streams:
   member=expected[stream['member']];info=source.getinfo(member['name'])
   if (info.file_size,info.compress_size,info.CRC,info.header_offset)!=(member['bytes'],member['compressed_bytes'],member['crc32'],member['header_offset']):raise ValueError('Native member identity differs')
   name=stream['compressed']
   if Path(name).name!=name:raise ValueError('Output basename required')
   path=folder/name;sha=digest(path,guard)
   if sha!=stream['compressed_sha256']:raise ValueError('Native output changed before audit')
   h=hashlib.sha256();count=0
   with source.open(info) as native,gzip.open(path,'rb') as restored:
    while True:
     a=native.read(1024**2);b=restored.read(1024**2);guard()
     if a!=b:raise ValueError('Native literal bytes differ')
     if not a:break
     h.update(a);count+=len(a)
   if count!=member['bytes'] or count!=stream['source_bytes'] or h.hexdigest()!=stream['source_sha256']:raise ValueError('Native source bytes/hash receipt differs')
   rows,clocks=clock_rows(path,guard);mapping=coverage(record,member['name'],rows,h.hexdigest(),table_names)
   if digest(path,guard)!=sha:raise ValueError('Native output changed during audit')
   artifacts[str(path)]=sha;results.append({'member':member['name'],'source_sha256':h.hexdigest(),'source_bytes':count,'rows':rows,'literal_native_bytes_equal':True,'compressed':name,'compressed_sha256':sha,'coverage':mapping,**clocks})
 if (archive.stat().st_size,archive.stat().st_mtime_ns)!=before:raise ValueError('Native archive changed during audit')
 verify(artifacts,guard);return results,artifacts


def runtime_guard(folder,timeout=3600):
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 started=time.monotonic();last=[0.]
 def guard():
  now=time.monotonic()
  if now-started>timeout or (folder/'STOP').exists():raise RuntimeError('Native audit stop/finite timeout')
  if now-last[0]>=15:
   headroom(folder);available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))//1024
   if available<(3584 if last[0]==0 else 2048) or windows_available_mib()<(2816 if last[0]==0 else 2048):raise MemoryError('Native audit reserve')
   if shutil.disk_usage(folder).free<5*1024**3:raise MemoryError('Native audit disk reserve')
   last[0]=now
 guard();return guard


def run(planpath,expected,index):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)))
 planpath=Path(planpath).resolve();plan=json.loads(planpath.read_text());guard=runtime_guard(planpath.parent)
 if digest(planpath)!=expected:raise ValueError('Native audit plan changed')
 verify(plan['bindings'],guard)
 if not 0<=index<len(plan['records']):raise ValueError('Native record index outside plan')
 record=plan['records'][index];folder=planpath.parent/'records'/f'{index:06d}';path=folder/'preservation.json';sha=digest(path);producer=json.loads(path.read_text())
 identity={k:record[k] for k in ('phase','subject','recording','source_recording_id')}
 if producer.get('status')!='whole_native_csv_members_preserved_pending_independent_audit' or producer.get('scientific_approval') is not False or producer.get('plan_sha256')!=expected or producer.get('record_index')!=index or producer.get('identity')!=identity:raise ValueError('Native producer prerequisite differs')
 attempt=folder/'audit_attempt.json'
 with attempt.open('x') as stream:json.dump({'plan_sha256':expected,'scientific_approval':False},stream)
 streams,artifacts=audit_record(record,folder,producer,plan['kind_to_native_filename'],guard)
 verify(plan['bindings'],guard)
 if digest(path)!=sha or digest(planpath)!=expected:raise ValueError('Native audit evidence changed')
 report={'status':'whole_native_csv_members_independently_byte_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':expected,'record_index':index,'identity':identity,'preservation_sha256':sha,'artifact_hashes':artifacts,'streams':streams,'interpretation':'All original native rows/columns/clocks retained. Verified membership is coverage bookkeeping, not canonical task or anatomical approval.'}
 with (folder/'source_readback.json').open('x') as stream:json.dump(report,stream,indent=2)


def summarize(planpath,expected):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)))
 planpath=Path(planpath).resolve();plan=json.loads(planpath.read_text());guard=runtime_guard(planpath.parent,24*3600)
 if digest(planpath)!=expected or len(plan['records'])!=1358:raise ValueError('Full1358native plan required')
 verify(plan['bindings'],guard);records=[];bindings={};seen=set()
 for index,record in enumerate(plan['records']):
  folder=planpath.parent/'records'/f'{index:06d}';path=folder/'source_readback.json';report=json.loads(path.read_text());identity={k:record[k] for k in ('phase','subject','recording','source_recording_id')}
  key=(record['phase'],record['subject'],record['recording'])
  if key in seen:raise ValueError('Duplicate original native record')
  seen.add(key)
  if report.get('status')!='whole_native_csv_members_independently_byte_checked_unreviewed' or report.get('scientific_approval') is not False or report.get('canonical_dataset_approval') is not False or report.get('plan_sha256')!=expected or report.get('record_index')!=index or report.get('identity')!=identity:raise ValueError('Native readback identity/status differs')
  streams=report['streams']
  if len(streams)!=len(record['members']) or {s['member'] for s in streams}!={m['name'] for m in record['members']}:raise ValueError('Incomplete native stream ledger')
  required_artifacts={}
  for stream in streams:
   if stream['literal_native_bytes_equal'] is not True or coverage(record,stream['member'],stream['rows'],stream['source_sha256'],plan['kind_to_native_filename'])!=stream['coverage']:raise ValueError('Native coverage receipt differs')
   if Path(stream['compressed']).name!=stream['compressed']:raise ValueError('Native output basename required')
   required_artifacts[str(folder/stream['compressed'])]=stream['compressed_sha256']
  if required_artifacts!=report['artifact_hashes']:raise ValueError('Native output binding closure differs')
  bindings.update(required_artifacts);bindings[str(path)]=digest(path);bindings[str(folder/'preservation.json')]=report['preservation_sha256']
  records.append({'identity':identity,'report':str(path),'sha256':digest(path),'streams':len(streams)})
 verify(bindings,guard);verify(plan['bindings'],guard)
 if digest(planpath)!=expected:raise ValueError('Native plan changed during final closure')
 report={'status':'all1358_native_recordings_lossless_source_preserved_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':expected,'records':records,'artifact_hashes':bindings,'original_scope':plan['scope'],'excluded_archive_scope':plan['excluded_archive_scope'],'unresolved_parsed_membership':plan['unresolved_parsed_membership']}
 with (planpath.parent/'native_summary.json').open('x') as stream:json.dump(report,stream,indent=2)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--record-index',type=int);g.add_argument('--summarize',action='store_true');a=p.parse_args()
 if a.summarize:summarize(a.plan,a.plan_sha256)
 else:run(a.plan,a.plan_sha256,a.record_index)
if __name__=='__main__':main()
