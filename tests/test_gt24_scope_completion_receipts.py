"""Persisted synthetic receipts through the actual delegated receipt checkers."""
import json,zipfile
from pathlib import Path
import pytest
from contributor_tools import run_gt24_scope_completion as m
from contributor_tools.run_gt24_full_reconstruction import checked_record
from contributor_tools.run_gt24_source_companion_batch import receipt_closure
from contributor_tools.prepare_gt24_complete_membership import stat_identity
from contributor_tools.audit_gt24_native_companion import coverage


def write(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(value));return p

def data(p,text='time,x\n0,1\n'):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p

@pytest.fixture
def persisted(tmp_path,monkeypatch):
 mr=tmp_path/'mapped';cr=tmp_path/'companions';nr=tmp_path/'native';ident=dict(phase='P',subject='S',recording='r');other=dict(phase='P',subject='S',recording='u');source=data(tmp_path/'raw.csv')
 original={**ident,'disposition':'canonical_parsed_candidate_requires_source_audit','files':{'angle_filt':{'path':str(source)}}};unmapped={**other,'disposition':'source_only_unmapped_task','files':{}}
 folder=mr/'mapped/P/S/r';baseline=data(folder/'record_0/baseline_unreviewed.parquet','baseline');output=data(folder/'record_0/continuous.parquet','corrected');record={**ident,'files':original['files'],'reference_output':str(baseline)};rp=write(folder/'plan.json',{'records':[record]});write(folder/'admission.json',{})
 for name,status in [('baseline','bounded_parsed_continuous_export_unverified'),('export','participant_normalization_export_unverified'),('audit','participant_normalization_independent_readback_checked_unreviewed')]:
  write(folder/'record_0'/(name+'.json'),dict(status=status,scientific_approval=False,plan_sha256=m.digest(rp),output_sha256=m.digest(baseline if name=='baseline' else output),rows=1,all_unrelated_values_field_metadata_null_masks_exact=True,reference_sha256=m.digest(baseline)))
 raw={**ident,'status':'corrected_raw_source_fields_checked_unreviewed','scientific_approval':False,'plan_sha256':m.digest(rp),'output_sha256':m.digest(output),'bound_producer_policy':'gt24_participant_mass_missingness_v2','rows':1,'source_sha256':{'angle_filt':m.digest(source)}};write(folder/'raw_source.json',raw);_,hashes=checked_record(folder,record)
 mappedrow={**ident,'status':raw['status'],'report':str(folder/'raw_source.json'),'report_sha256':m.digest(folder/'raw_source.json'),'receipt_hashes':hashes}
 archive=tmp_path/'original.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('r/angle.csv',source.read_bytes())
 with zipfile.ZipFile(archive) as z:
  info=z.getinfo('r/angle.csv');member=dict(name=info.filename,bytes=info.file_size,compressed_bytes=info.compress_size,crc32=info.CRC,header_offset=info.header_offset)
 job=dict(phase='P',subject='S',parsed_recording='r',native_recording='n',archive=stat_identity(archive),tables=[dict(kind='angle',member=member,parsed=stat_identity(source))]);mp=write(mr/'membership/plan.json',{'jobs':[job],'bindings':{}})
 report=dict(job_index=0,phase='P',subject='S',parsed_recording='r',native_recording='n',status='native_parsed_candidate_rejected',membership_verified=False,scientific_approval=False,plan_sha256=m.digest(mp),tables={'angle':{'parsed':{'full_csv_sha256':m.digest(source)},'native':{'full_csv_sha256':m.digest(source)}}});cp=write(mr/'membership/records/000000.json',report)
 candidate=dict(index=0,path=str(cp),sha256=m.digest(cp),status=report['status']);residual=write(mr/'membership/coverage_summary.json',{'synthetic':True})
 row={**other,'source_recording_id':'source-u','files':[{'kind':'angle','path':str(source)}]};cf=cr/'records/P/S/u';cpp=write(cf/'plan.json',{});producer=write(cf/'preservation.json',{});gz=data(cf/'source.gz','gzip-fixture');parquet=data(cf/'source.parquet','parquet-fixture')
 stream=dict(kind='angle',rows=1,literal_csv_bytes_equal=True,every_numeric_value_and_missing_mask_checked=True,source_header_and_units_checked=True,source_sha256=m.digest(source),compressed=gz.name,compressed_sha256=m.digest(gz),parquet=parquet.name,parquet_sha256=m.digest(parquet))
 write(cf/'source_readback.json',{**other,'source_recording_id':'source-u','status':'all_inventoried_source_streams_lossless_readback_checked_unreviewed','scientific_approval':False,'canonical_dataset_approval':False,'plan_sha256':m.digest(cpp),'preservation_sha256':m.digest(producer),'streams':[stream]});ch=receipt_closure(cf,row)
 native={**ident,'recording':'n','members':[member]};nrecord={**native,'source_recording_id':'native-n','coverage':{}};np=write(nr/'plan.json',{'records':[nrecord],'bindings':{},'kind_to_native_filename':{'angle':'angle.csv'},'excluded_archive_scope':[]});nf=nr/'records/000000';ngz=data(nf/'native.gz','native-gzip-fixture');nprod=write(nf/'preservation.json',{})
 ns=dict(member=member['name'],rows=1,source_sha256=m.digest(source),compressed=ngz.name,compressed_sha256=m.digest(ngz),literal_native_bytes_equal=True);ns['coverage']=coverage(nrecord,member['name'],1,m.digest(source),{'angle':'angle.csv'});ni={k:nrecord[k] for k in ('phase','subject','recording','source_recording_id')}
 nreport=write(nf/'source_readback.json',dict(status='whole_native_csv_members_independently_byte_checked_unreviewed',scientific_approval=False,canonical_dataset_approval=False,plan_sha256=m.digest(np),record_index=0,identity=ni,preservation_sha256=m.digest(nprod),streams=[ns],artifact_hashes={str(ngz):m.digest(ngz)}))
 nativehash={str(ngz):m.digest(ngz),str(nreport):m.digest(nreport),str(nprod):m.digest(nprod)}
 write(nr/'native_summary.json',dict(status='all1358_native_recordings_lossless_source_preserved_unreviewed',scientific_approval=False,plan_sha256=m.digest(np),records=[dict(identity=ni,report=str(nreport),sha256=m.digest(nreport),streams=1)],excluded_archive_scope=[],artifact_hashes=nativehash,unresolved_parsed_membership=['synthetic-negative']))
 mappedplan=write(mr/'plan.json',{});companionplan=write(cr/'plan.json',{'records':[row]});inventory=write(tmp_path/'inventory.json',{})
 write(mr/'status.json',dict(status='all2421_scope_accounted_source_review_incomplete',scientific_approval=False,plan_sha256=m.digest(mappedplan),records=[mappedrow,{**other,'status':'source_only_preservation_pending'}],candidate_reports=[candidate],native_residual_summary=str(residual),native_residual_summary_sha256=m.digest(residual)))
 write(cr/'batch_status.json',dict(status='all869_gt24_source_companions_lossless_readback_checked_unreviewed',scientific_approval=False,plan_sha256=m.digest(companionplan),records=[{**other,'report':str(cf/'source_readback.json'),'artifact_hashes':ch}]))
 monkeypatch.setattr(m,'scope_gate',lambda *args:([original,unmapped],[native]))
 plan=dict(mapped_plan=str(mappedplan),companion_plan=str(companionplan),inventory=str(inventory),native_output=str(nr),excluded_archive_scope=[],bindings={})
 return plan,dict(source=source,mapped=folder,native=ngz,candidate=cp,archive=archive,mr=mr,nr=nr)


def test_persisted_end_to_end_and_negative_membership(persisted):
 plan,_=persisted;result=m._closure(plan,1);assert result['scientific_approval'] is False;assert result['unresolved_parsed_membership']==['synthetic-negative']

@pytest.mark.parametrize('fault',['missing_mapped','swapped_identity','source','native','candidate','negative_source'])
def test_persisted_tampering_rejected(persisted,fault):
 plan,p=persisted
 if fault=='missing_mapped':(p['mapped']/'raw_source.json').unlink()
 elif fault=='swapped_identity':
  path=p['mapped']/'plan.json';d=m.load(path);d['records'][0]['subject']='other';write(path,d)
 elif fault=='source':p['source'].write_text('changed')
 elif fault=='native':p['native'].write_text('changed')
 elif fault=='candidate':write(p['candidate'],{})
 else:
  with zipfile.ZipFile(p['archive'],'w') as z:z.writestr('r/angle.csv','changed')
 with pytest.raises((ValueError,FileNotFoundError)):m._closure(plan,1)

@pytest.mark.parametrize('sig',[m.signal.SIGINT,m.signal.SIGTERM])
def test_interruption_cleans_owned_sessions_without_resume(tmp_path,monkeypatch,sig):
 mp=write(tmp_path/'mapped/plan.json',{});cp=write(tmp_path/'companion/plan.json',{})
 path=write(tmp_path/'plan.json',dict(output=str(tmp_path),bindings={},mapped_plan=str(mp),companion_plan=str(cp)))
 monkeypatch.setattr(m,'headroom',lambda *a:None)
 live={101:{'start':'a','ppid':1,'pgid':101,'state':'S'},102:{'start':'b','ppid':101,'pgid':102,'state':'S'}};signals=[]
 monkeypatch.setattr(m,'processes',lambda:{p:dict(v) for p,v in live.items()})
 def kill(pid,signal):
  signals.append((pid,signal))
  if signal==m.signal.SIGKILL:live.pop(pid,None)
 monkeypatch.setattr(m.os,'kill',kill);monkeypatch.setattr(m.os,'killpg',kill)
 class Child:
  pid=101
  def poll(self):m.signal.getsignal(sig)(sig,None)
  def wait(self,timeout):return -9
 monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:Child())
 original=m.signal.getsignal(sig)
 with pytest.raises(RuntimeError,match='interrupted'):m.run(path,m.digest(path))
 assert not live and all(s!=m.signal.SIGCONT for _,s in signals)
 assert m.signal.getsignal(sig)==original
 assert m.load(tmp_path/'status.json')['status']=='stopped_incomplete'


def test_reused_leader_and_descendant_pids_not_signalled(monkeypatch):
 owned={101:{'start':'old','pgid':101},102:{'start':'oldchild','pgid':102}}
 live={101:{'start':'new','ppid':1,'pgid':101,'state':'S'},102:{'start':'newchild','ppid':101,'pgid':102,'state':'S'},103:{'start':'stranger','ppid':101,'pgid':103,'state':'S'}}
 monkeypatch.setattr(m,'processes',lambda:live)
 monkeypatch.setattr(m.os,'kill',lambda *a:pytest.fail('reused PID signalled'))
 monkeypatch.setattr(m.os,'killpg',lambda *a:pytest.fail('reused group signalled'))
 class Child:
  pid=101
  def wait(self,timeout):return 0
 m.cleanup(Child(),owned);assert set(owned)=={101,102}

@pytest.mark.parametrize('module_name,argv,target,expected_count',[
 ('run_gt24_full_reconstruction',['run','--plan','/tmp/plan.json','--plan-sha256','a'],'run',2),
 ('run_gt24_source_companion_batch',['run','--plan','/tmp/plan.json','--plan-sha256','a'],'run',2),
 ('preserve_gt24_native_companion',['prepare','--membership-plan','/tmp/m.json','--coverage-summary','/tmp/s.json','--output','/tmp/new'],'prepare',3),
 ('preserve_gt24_native_companion',['run','--plan','/tmp/plan.json','--plan-sha256','a','--record-index','0'],'run',3),
 ('audit_gt24_native_companion',['--plan','/tmp/plan.json','--plan-sha256','a','--record-index','0'],'run',3),
 ('audit_gt24_native_companion',['--plan','/tmp/plan.json','--plan-sha256','a','--summarize'],'summarize',2),
])
def test_actual_delegated_cli_parsers(monkeypatch,module_name,argv,target,expected_count):
 import importlib
 module=importlib.import_module('contributor_tools.'+module_name);calls=[]
 monkeypatch.setattr(module,target,lambda *a:(calls.append(a),{'synthetic':True})[1]);monkeypatch.setattr(m.sys,'argv',[module_name,*argv]);
 if hasattr(module,'main'):module.main()
 else:
  import ast
  tree=ast.parse(Path(module.__file__).read_text());block=tree.body[-1]
  namespace=dict(vars(module));namespace['__name__']='__main__'
  exec(compile(ast.Module(body=[block],type_ignores=[]),module.__file__,'exec'),namespace)
 assert len(calls)==1 and len(calls[0])==expected_count
