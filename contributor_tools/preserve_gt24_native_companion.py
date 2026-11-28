"""Preserve whole GT24 native CSV recordings, including ambiguous/residual intervals.

Only an external exclusive scientific slot may execute a record. No extraction,
array libraries, inferred task labels, resampling or automatic bulk launch.
"""
import argparse,gzip,hashlib,json,os,resource,shutil,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'converted_datasets/reconversion_v2'


def digest(path,guard=lambda:None):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024**2),b''):guard();h.update(block)
 return h.hexdigest()


def verify(bindings,guard=lambda:None):
 for path,sha in bindings.items():
  if digest(path,guard)!=sha:raise ValueError('Frozen native prerequisite changed: '+path)


def reserve_bytes(records):
 # Deflate worst case plus gzip/member overhead, not an assumed compression ratio.
 return sum(m['bytes']+(m['bytes']//16384+1)*64+1024 for r in records for m in r['members'])


def prepare(membership_path,summary_path,output):
 from contributor_tools.prepare_gt24_complete_membership import summarize,TABLES
 membership_path=Path(membership_path).resolve();summary_path=Path(summary_path).resolve();output=Path(output).resolve()
 if output.exists() or not output.is_relative_to(BASE):raise ValueError('Fresh isolated native companion output required')
 membership=json.loads(membership_path.read_text());summary=json.loads(summary_path.read_text())
 if len(membership['jobs'])!=2447 or summary.get('status')!='all_planned_candidate_checks_aggregated_unreviewed' or summary.get('scientific_approval') is not False:raise ValueError('Actual full2447membership completion required')
 if summarize(membership_path)!=summary:raise ValueError('Summary does not reproduce every bound candidate report')
 inventory_path=Path(membership['inventory']);inventory=json.loads(inventory_path.read_text())
 lookup={(r['phase'],r['subject'],r['recording']):r for r in summary['native_recordings']}
 if len(lookup)!=1358 or len(summary['native_recordings'])!=1358:raise ValueError('Exact1358unique native scope required')
 records=[];seen=set()
 for phase in inventory['phases']:
  for source in phase['dynamic_complete_recordings']:
   key=(phase['phase'],source['subject'],source['recording'])
   if key in seen or key not in lookup:raise ValueError('Duplicate or unmatched native recording')
   seen.add(key);members=source['members']
   if not members or len({m['name'] for m in members})!=len(members):raise ValueError('Every unique native CSV member required')
   records.append({'phase':key[0],'subject':key[1],'recording':key[2],'source_recording_id':'gt24-native:'+'/'.join(key),'archive':phase['archive'],'members':members,'coverage':lookup[key]})
 if seen!=set(lookup):raise ValueError('Missing original native identities')
 bindings=dict(membership['bindings']);bindings.update(summary['candidate_report_hashes'])
 for path in [membership_path,summary_path,inventory_path,Path(__file__).resolve(),ROOT/'contributor_tools/audit_gt24_native_companion.py',ROOT/'contributor_tools/preserve_mblue_planar_estimates.py']:
  sha=digest(path)
  if str(path) in bindings and bindings[str(path)]!=sha:raise ValueError('Conflicting native evidence')
  bindings[str(path)]=sha
 verify(bindings)
 plan={'status':'prepared_not_run','scientific_approval':False,'canonical_dataset_approval':False,'bindings':bindings,'output':str(output),'records':records,'kind_to_native_filename':TABLES,'required_output_bytes_upper_bound':reserve_bytes(records),'reserve_bytes':5*1024**3,'memory_limit_mib':256,'per_record_timeout_seconds':3600,'scope':'All1358dynamic native recordings; whole CSV members duplicated to retain boundary context. Static calibration and nonCSV entries remain referenced original archive exclusions, not claimed exported.','excluded_archive_scope':[{'phase':p['phase'],'static_source_tables':p['static_source_tables'],'excluded_archive_entries':p['excluded_archive_entries']} for p in inventory['phases']],'unresolved_parsed_membership':summary['unresolved_parsed_membership']}
 free=shutil.disk_usage(output.parent).free
 required=plan['required_output_bytes_upper_bound']+plan['reserve_bytes']
 plan['disk_admission']={'free_bytes_at_preparation':free,'full_required_bytes_including_reserve':required,'full_scope_fits_worst_case_at_preparation':free>=required,'status':'full_worst_case_space_available_not_execution_approval' if free>=required else 'full_worst_case_space_unavailable_staged_execution_only','policy':'Plan only: no scientific outputs written. Each record must independently pass current worst-case bytes plus5GiB reserve; all1358verified records still required for completion. No assumed compression ratio.'}
 output.mkdir();path=output/'plan.json';path.write_text(json.dumps(plan,indent=2)+'\n');return {'plan':str(path),'sha256':digest(path),'native_recordings':1358,'disk_upper_bound_bytes':plan['required_output_bytes_upper_bound']}


def guard_for(folder,timeout=3600):
 from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
 start=time.monotonic();last=[0.]
 def guard():
  now=time.monotonic()
  if now-start>timeout:raise TimeoutError('Native source worker finite timeout')
  if (folder/'STOP').exists() or (folder.parent.parent/'STOP').exists():raise RuntimeError('Native source worker stopped')
  if now-last[0]>=15:
   headroom(folder)
   available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))//1024
   if available<(3584 if last[0]==0 else 2048) or windows_available_mib()<(2816 if last[0]==0 else 2048):raise MemoryError('Native source worker reserve')
   if shutil.disk_usage(folder).free<5*1024**3:raise MemoryError('Native source disk reserve')
   last[0]=now
 guard();return guard


def archive_identity(record):
 path=Path(record['archive']['path']);stat=path.stat()
 if (str(path.resolve()),stat.st_size,stat.st_mtime_ns)!=(record['archive']['path'],record['archive']['bytes'],record['archive']['mtime_ns']):raise ValueError('Native archive changed')
 return stat.st_size,stat.st_mtime_ns


def preserve_record(record,folder,guard=lambda:None):
 """Streaming ZIP member→gzip; no raw temporary files or row modifications."""
 folder=Path(folder)
 if folder.exists():raise FileExistsError('Preserve existing native outputs')
 folder.mkdir(parents=True);before=archive_identity(record);reports=[]
 with zipfile.ZipFile(record['archive']['path']) as archive:
  if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('Duplicate native archive members')
  for index,member in enumerate(record['members']):
   guard();info=archive.getinfo(member['name'])
   if (info.file_size,info.compress_size,info.CRC,info.header_offset)!=(member['bytes'],member['compressed_bytes'],member['crc32'],member['header_offset']):raise ValueError('Native member changed')
   path=folder/f'{index:04d}.csv.gz';partial=path.with_suffix('.partial');h=hashlib.sha256();count=0
   with archive.open(info) as source,partial.open('xb') as target:
    with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0,compresslevel=1) as compressed:
     for block in iter(lambda:source.read(1024**2),b''):guard();compressed.write(block);h.update(block);count+=len(block)
   if count!=member['bytes']:raise ValueError('Incomplete native member')
   partial.replace(path);reports.append({'member':member['name'],'source_bytes':count,'source_sha256':h.hexdigest(),'compressed':path.name,'compressed_sha256':digest(path,guard)})
 if archive_identity(record)!=before:raise ValueError('Native archive changed during preservation')
 return reports


def admit_record_disk(record,folder,reserve=5*1024**3):
 if reserve<5*1024**3:raise ValueError('Native disk reserve cannot be lowered')
 if shutil.disk_usage(folder).free<reserve_bytes([record])+reserve:raise MemoryError('Per-record duplication disk admission refused')


def run(planpath,expected,index):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));os.nice(max(0,19-os.nice(0)))
 planpath=Path(planpath).resolve();plan=json.loads(planpath.read_text())
 if digest(planpath)!=expected or plan['output']!=str(planpath.parent):raise ValueError('Native plan differs')
 verify(plan['bindings'])
 if not 0<=index<len(plan['records']):raise ValueError('Native record index outside plan')
 record=plan['records'][index];folder=planpath.parent/'records'/f'{index:06d}'
 guard=guard_for(planpath.parent,plan['per_record_timeout_seconds'])
 admit_record_disk(record,planpath.parent,plan['reserve_bytes'])
 streams=preserve_record(record,folder,guard);verify(plan['bindings'],guard)
 if digest(planpath)!=expected:raise ValueError('Native plan changed during export')
 receipt={'status':'whole_native_csv_members_preserved_pending_independent_audit','scientific_approval':False,'plan_sha256':expected,'record_index':index,'identity':{k:record[k] for k in ('phase','subject','recording','source_recording_id')},'streams':streams}
 with (folder/'preservation.json').open('x') as out:json.dump(receipt,out,indent=2)


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
 q=sub.add_parser('prepare');q.add_argument('--membership-plan',type=Path,required=True);q.add_argument('--coverage-summary',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
 q=sub.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--plan-sha256',required=True);q.add_argument('--record-index',type=int,required=True);a=p.parse_args()
 if a.mode=='prepare':print(json.dumps(prepare(a.membership_plan,a.coverage_summary,a.output)))
 else:run(a.plan,a.plan_sha256,a.record_index)
if __name__=='__main__':main()
