"""Isolated full GT23 source restoration after actual reviewed correction pilots.

Prepare requires completed AB01 time/phase and AB03 raw-source checks and an
explicit hash-bound coordinator review. Run requires an exclusively held native
slot. Original files and historical converters are never edited. Fresh output
only: failures retain evidence and a complete pending/finished scope ledger.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'converted_datasets/reconversion_v2'
sys.path.insert(0,str(ROOT))
from contributor_tools.plan_gt23_full_source_restoration import digest,read
from contributor_tools.prepare_mblue_orientation_pose_pilot import windows
CODE=ROOT/'contributor_tools/conversion_scripts/Gtech_2023'
SUPPORT=BASE/'gt23_ab03_native_mass_pilot_preparation_20261021'
OWNERSHIP=BASE/'gt21_strict_after_gt24companion_20261021/run_watcher.py'


def merge_bindings(*groups):
    result={}
    for group in groups:
        for path,sha in group.items():
            canonical=str(Path(path).resolve())
            if canonical in result and result[canonical]!=sha:raise ValueError('Conflicting bound identity: '+canonical)
            result[canonical]=sha
    return result


def write(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2)


def save(path,value):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def verify(bindings):
    for path,sha in bindings.items():
        if digest(path)!=sha:raise ValueError('Changed bound input: '+path)


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def reviewed_pilots(review,digest_fn=digest,verify_fn=verify):
    if review.get('decision')!='approved_for_full_source_reconstruction' or review.get('scientific_approval') is not False:raise ValueError('Explicit coordinator pilot review required')
    expected={'AB01':'two_producer_AB01_normalization_raw_source_checked_unreviewed','AB03':'real_AB03_native_publisher_normalization_source_checked_unreviewed'}
    if set(review.get('pilots',{}))!=set(expected):raise ValueError('Both real pilot participants required')
    bindings={}
    for subject,status in expected.items():
        item=review['pilots'][subject];path=Path(item['path'])
        if digest_fn(path)!=item['sha256']:raise ValueError('Pilot receipt changed since review')
        r=read(path)
        if r.get('status')!=status or r.get('scientific_approval') is not False:raise ValueError('Pilot not successfully source checked')
        verify_fn(r['bindings']);bindings=merge_bindings(bindings,r['bindings'],{str(path):item['sha256']})
        if subject=='AB01':
            if {c['mode'] for c in r['cases']}!={'time','phase'} or len(r['cases'])!=2:raise ValueError('Both native producer modes required')
            audits=[(Path(c['raw_audit_report']),c['raw_audit_sha256']) for c in r['cases']]
        else:
            if r.get('mass_kg')!=113.5:raise ValueError('Actual AB03 publisher mass not established')
            # Pilot output is bound by its original plan; do not accept an arbitrary report location.
            pilot_plan=read(SUPPORT/'plan.json');verify_fn(pilot_plan['bindings'])
            audits=[(Path(pilot_plan['output'])/'raw_audit/raw_source_readback.json',r['raw_audit_sha256'])]
            bindings=merge_bindings(bindings,{str(SUPPORT/'plan.json'):digest_fn(SUPPORT/'plan.json')})
            if r.get('plan_sha256')!=digest_fn(SUPPORT/'plan.json'):raise ValueError('AB03 pilot plan lineage differs')
        for ap,sha in audits:
            if digest_fn(ap)!=sha:raise ValueError('Raw pilot readback changed')
            a=read(ap)
            if a.get('status')!='publisher_normalization_raw_source_checked_unreviewed' or a.get('participant')!=subject or a.get('entirely_unassessed_features')!=[] or a.get('rows_checked',0)<2:raise ValueError('Actual complete independent source audit required')
            coverage=a.get('feature_coverage',{})
            if a.get('scientific_approval') is not False or len(coverage)!=18 or any(c.get('finite',0)<=0 or c.get('finite',0)+c.get('missing',0)!=a['rows_checked'] for c in coverage.values()):raise ValueError('Pilot per-feature source coverage incomplete')
            if digest_fn(ap.parent/'plan.json')!=a.get('plan_sha256'):raise ValueError('Raw audit plan lineage differs')
            verify_fn(a['bindings']);bindings=merge_bindings(bindings,a['bindings'],{str(ap):sha})
    return bindings


def prepare(scope_path,review_path,output):
    scope=read(scope_path);review=read(review_path);bindings=reviewed_pilots(review)
    verify(scope['bindings'])
    if (scope['raw_recordings'],scope['parsing_inventory_entries'],scope['published_csv_files'])!=(488,787,4880):raise ValueError('Full reviewed GT23 scope required')
    out=Path(output).resolve()
    if out.exists() or not out.is_relative_to(BASE):raise ValueError('Fresh authorized full reconstruction root required')
    out.mkdir();support=out/'support';support.mkdir();guards=support/'guard';guards.mkdir()
    for name in ('run_matlab_recording_guarded.ps1','run_gt23_recording_guarded.ps1'):
        shutil.copyfile(SUPPORT/'native_guard'/name,guards/name)
    shutil.copyfile(SUPPORT/'native_cleanup.py',support/'native_cleanup.py')
    for mode in ('time','phase'):
        text=(SUPPORT/'native_time_driver.py').read_text()
        if text.count("'-Mode','time'")!=1:raise ValueError('Native driver dispatch differs')
        (support/f'native_{mode}_driver.py').write_text(text.replace("'-Mode','time'",f"'-Mode','{mode}'"))
    tools=['rebuild_gt23_full_source.py','plan_gt23_full_source_restoration.py','preserve_gt23_full_source_channels.py','withhold_gt23_unverified_anatomy.py',
           'prepare_gt23_recording.py','correct_gt23_global_force_frame.py','annotate_gt23_cop_frame.py','chain_gt23_cop_metadata.py',
           'correct_gt23_publisher_normalization.py','audit_gt23_publisher_raw_source.py','audit_gt23_raw_kinematics.py','audit_mblue_orientation_pose_pilot.py','prepare_mblue_orientation_pose_pilot.py','preserve_mblue_planar_estimates.py','reconvert_recording.py']
    files=[scope_path,review_path,OWNERSHIP,*[ROOT/'tests'/n for n in ('test_gt23_full_runner_gates.py','test_gt23_full_runner_cli.py','test_gt23_raw_kinematics.py','test_gt23_full_source_scope.py','test_gt23_source_channel_preservation.py','test_gt23_anatomy_disposition.py')],*[ROOT/'contributor_tools'/n for n in tools],*CODE.rglob('*.m'),*(CODE.parent/'matlab_common').glob('*.m'),*(ROOT/'contributor_tools/common').rglob('*.py'),*support.rglob('*.py'),*guards.glob('*.ps1')]
    bindings=merge_bindings(bindings,scope['bindings'],{str(Path(p).resolve()):digest(p) for p in files})
    verify(bindings)
    p={'status':'prepared_not_executed','scientific_approval':False,'bindings':bindings,'scope_path':str(Path(scope_path).resolve()),'review_path':str(Path(review_path).resolve()),
       'source_root':scope['source_root'],'support':str(support),'output':str(out),'source_channels':4880,'source_recordings':488,'parsing_entries':787,
       'limits':{'total_deadline_h':336,'source_record_disk_reserve_bytes':5*1024**3},'ownership_helper':str(OWNERSHIP),
       'scope_notes':['Parsing files can contain multiple events: 787 is not an observation count.','All 85 unparsed recordings retain all source CSV channels; no invented event segmentation.','Canonical unverified joint/segment anatomy is withheld with exact prior-value aliases.','No source files deleted; partial attempts require explicit new output root.']}
    write(out/'plan.json',p);return p


def capture_owned(child,owned,helper):
    parent=owned.get(child.pid);current=helper.process(child.pid)
    if not parent or not current or current['start']!=parent['start']:return
    descendants=helper.descendants(child.pid);current=helper.process(child.pid)
    if not current or current['start']!=parent['start']:return
    for pid,row in descendants.items():
        if pid not in owned or owned[pid]['start']==row['start']:owned[pid]=row


def cleanup_linux(child,owned,helper):
    parent=owned.get(child.pid);current=helper.process(child.pid)
    if parent and current and current['start']==parent['start'] and current.get('state')!='Z':
        try:os.kill(child.pid,signal.SIGSTOP)
        except ProcessLookupError:pass
        capture_owned(child,owned,helper)
    for pid,identity in sorted(owned.items(),key=lambda pair:pair[0]==child.pid):
        current=helper.process(pid)
        if not current or current['start']!=identity['start'] or current.get('state')=='Z':continue
        try:
            if current['pgid']==pid:os.killpg(pid,signal.SIGKILL)
            else:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
    child.wait(timeout=15);deadline=time.monotonic()+15
    while True:
        alive=[]
        for pid,identity in owned.items():
            current=helper.process(pid)
            if current and current['start']==identity['start'] and current.get('state')!='Z':alive.append(pid)
        if not alive:return
        if time.monotonic()>deadline:raise RuntimeError('Owned Linux identities remain alive')
        time.sleep(.1)


class Runtime:
    def __init__(self,plan):
        self.plan=plan;self.out=Path(plan['output']);self.last=0;self.started=time.monotonic()
        self.plan_path=self.out/'plan.json';self.plan_sha=digest(self.plan_path)
        for helper in (Path(plan['ownership_helper']),Path(plan['support'])/'native_cleanup.py'):
            if plan['bindings'].get(str(helper))!=digest(helper):raise ValueError('Process ownership helper changed')
        self.owned=load(plan['ownership_helper'],'gt23_full_process_ownership')
        self.cleanup=load(Path(plan['support'])/'native_cleanup.py','gt23_full_native_cleanup')
    def stop_and_ownership(self):
        if any((self.out/n).exists() for n in ('STOP','STOP_AFTER_CURRENT')):raise RuntimeError('Coordinator STOP')
        if time.monotonic()-self.started>self.plan['limits']['total_deadline_h']*3600:raise TimeoutError('Full source reconstruction deadline exceeded')
        if digest(self.plan_path)!=self.plan_sha:raise ValueError('Plan changed during full reconstruction')
        for pid,start,cmd in ((402226,'24607869','contributor_tools/run_gt21_with_memory_wait.py'),(402224,'24607849','metadata_serial_queue_20261021/run_queue.py')):
            current=self.owned.process(pid)
            if not current or current['start']!=start or current['state']!='T' or cmd not in current['cmd']:raise RuntimeError('Exact held controller/unsafe parent identity differs')
        if self.owned.descendants(402226):raise RuntimeError('Held native controller has descendants')
    def resources(self,force=False,native=False):
        self.stop_and_ownership()
        if not force and time.monotonic()-self.last<15:return
        from contributor_tools.preserve_mblue_planar_estimates import headroom,windows_available_mib
        headroom(self.out)
        available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))//1024
        if available<(3584 if force else 2048) or windows_available_mib()<(4352 if native else 2816 if force else 2048):raise MemoryError('Shared-host headroom insufficient')
        self.last=time.monotonic()
    def stage(self,name,command,folder,timeout=1800,intent=None):
        self.resources(True,native=intent is not None);self.verify_inputs()
        if intent is not None:
            idir=self.out/'native_intents';idir.mkdir(exist_ok=True);ip=idir/(name+'_native_intent.json');write(ip,intent)
        env=dict(os.environ);env.pop('PYTHONOPTIMIZE',None)
        for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):env[key]='1'
        with (folder/(name+'.log')).open('x') as log:
            child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            started=time.monotonic();owned={}
            identity=self.owned.process(child.pid)
            if identity:owned[child.pid]=identity
            try:
                while child.poll() is None:
                    capture_owned(child,owned,self.owned)
                    if time.monotonic()-started>timeout:raise TimeoutError('Bounded stage timeout')
                    self.resources();time.sleep(.2)
                if child.returncode:raise RuntimeError('Stage failed: '+name)
            finally:
                # Stop owned descendants even when the leader already exited.
                handlers={sig:signal.signal(sig,signal.SIG_IGN) for sig in (signal.SIGTERM,signal.SIGINT)}
                try:
                    failures=[]
                    try:cleanup_linux(child,owned,self.owned)
                    except Exception as error:failures.append('Linux: '+str(error))
                    if intent is not None:
                        try:
                            proof=self.cleanup.await_cleanup(ip,timeout=370)
                            if proof.get('safe_to_release') is not True:raise RuntimeError('Windows ownership cleanup unresolved')
                        except Exception as error:failures.append('Windows: '+str(error))
                    if failures:raise RuntimeError('Cleanup unresolved; retain native slot: '+'; '.join(failures))
                finally:
                    for sig,handler in handlers.items():signal.signal(sig,handler)
        self.verify_inputs()
    def guarded_digest(self,path):
        import hashlib
        h=hashlib.sha256()
        with Path(path).open('rb') as f:
            for chunk in iter(lambda:f.read(1024**2),b''):
                self.resources();h.update(chunk)
        return h.hexdigest()
    def verify_inputs(self,bindings=None):
        for path,sha in (self.plan['bindings'] if bindings is None else bindings).items():
            if self.guarded_digest(path)!=sha:raise ValueError('Bound execution input changed: '+path)

    def native(self,name,options,folder,mode):
        folder.mkdir(parents=True,exist_ok=False);op=folder/'options.json';write(op,options)
        support=Path(self.plan['support']);guard=support/'guard/run_gt23_recording_guarded.ps1';core=guard.with_name('run_matlab_recording_guarded.ps1')
        from contributor_tools.audit_mblue_orientation_pose_pilot import linux
        status=linux(options['output_path']).parent/'native_status.json'
        intent={'guard_path':str(core),'guard_sha256':digest(core),'options_path':str(op),'options_sha256':digest(op),'options_windows':windows(op),'status_path':str(status)}
        if mode in ('time','phase'):
            command=[sys.executable,str(support/f'native_{mode}_driver.py'),windows(op),windows(CODE),windows(guard)]
        else:
            command=['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',windows(guard),'-OptionsPath',windows(op),'-CodeDirectory',windows(CODE),'-MemoryMiB','2048','-TimeoutSeconds','300','-Mode','prepare-transforms']
        self.stage(name,command,folder,timeout=390,intent=intent)
        s=read(status)
        if s.get('status')!='completed' or s.get('exit_code')!=0 or s.get('native_job_closed') is not True:raise ValueError('Native conversion incomplete')
        return op,status
    def tool(self,name,args,folder):
        self.stage(name,[sys.executable,*args],folder)


def admit_record_disk(record,free,reserve):
    needed=sum(f['uncompressed_size'] for f in record['publisher_files'])*1.02+reserve
    if free<needed:raise MemoryError('Next source recording disk admission failed; prior receipts retained')
    return needed


def verify_original_membership(evidence,companion):
    originals={f['source_path']:f['source_sha256'] for f in companion['files']}
    required={'Joint_Angle.csv','Joint_Velocities.csv','Joint_Moments.csv','GroundFrame_GRFs.csv'}
    if not required<=set(evidence['csv_files']):raise ValueError('Missing required original CSV source')
    for name in required:
        item=evidence['csv_files'][name]
        if item['source'] not in originals or item['source_sha256']!=originals[item['source']]:raise ValueError('Conversion source differs from exact lossless original companion')


def corrected_record(runtime,record,index):
    """Existing producer plus verified correction chain, without inferred events."""
    p=runtime.plan;root=Path(p['source_root']);folder=runtime.out/'parsed'/record['subject']/Path(record['parsing']).stem
    folder.mkdir(parents=True,exist_ok=False);source=folder/'source'
    parsing=root/'Segmentation'/record['subject']/record['parsing']
    if runtime.guarded_digest(parsing)!=record['parsing_sha256']:raise ValueError('Original parsing bytes changed')
    if not record['has_intervals']:return {'status':'no_source_intervals_source_channels_preserved','scientific_approval':False}
    transform=root/'RawData'/record['subject']/'Transforms'/(record['recording']+'.mat')
    if transform.stat().st_size>64*1024**2:return {'status':'deferred_transform_admission_source_channels_preserved','scientific_approval':False}
    runtime.tool('source_prepare',[str(ROOT/'contributor_tools/prepare_gt23_recording.py'),'--source-root',str(root),'--subject',record['subject'],'--parsing',record['parsing'],'--output-root',str(source)],folder)
    evidence=read(source/'source_window_manifest.json')
    if evidence['subject']!=record['subject'] or evidence['parsing']!=record['parsing'] or evidence['recording']!=record['recording']:raise ValueError('Source preparation identity differs')
    companion=read(runtime.out/'source_companions'/record['subject']/record['recording']/'source_readback.json')
    verify_original_membership(evidence,companion)
    target=source/'RawData'/record['subject']/'Transforms'/(record['recording']+'.mat');target.parent.mkdir(parents=True)
    runtime.native(f'{index}_transform',{'source_path':windows(transform),'output_path':windows(target),'start_s':evidence['start_s'],'end_s':evidence['end_s']},folder/'transform','prepare-transforms')
    if read(str(target)+'.verification.json').get('exact_native_readback') is not True:raise ValueError('Native transform extraction differs')
    native_inputs=[target,source/'RawData/Subject_masses.csv',source/'Segmentation'/record['subject']/record['parsing'],*[source/'RawData'/record['subject']/'CSV_Data'/record['recording']/name for name in evidence['csv_files']]]
    if sum(x.stat().st_size for x in native_inputs)>64*1024**2:return {'status':'deferred_prepared_window_admission_source_channels_preserved','scientific_approval':False}
    native_code={str(x.relative_to(ROOT)):runtime.guarded_digest(x) for x in CODE.rglob('*.m')};reports={}
    for mode in ('time','phase'):
        base=folder/mode;base.mkdir();native=base/'native';parquet=native/(mode+'.parquet')
        options,status=runtime.native(f'{index}_{mode}',{'data_root':windows(source),'output_path':windows(parquet),'subject':record['subject'],'recording':record['parsing']},native,mode)
        manifest=native/'conversion_manifest.json'
        metadata={'output_sha256':runtime.guarded_digest(parquet),'code_sha256':native_code,'scientific_approval':False}
        if mode=='time':metadata.update(prepared_input_manifest=runtime.guarded_digest(source/'source_window_manifest.json'),prepared_input_sha256={str(x.relative_to(source)):runtime.guarded_digest(x) for x in source.rglob('*') if x.is_file()})
        write(manifest,metadata)
        producer='contributor_tools/conversion_scripts/Gtech_2023/'+('convert_gtech_2023_time_to_parquet.m' if mode=='time' else 'convert_gtech_phase_to_parquet.m')
        driver=Path(p['support'])/f'native_{mode}_driver.py';lineage=native/'lineage.json'
        write(lineage,{'input_sha256':runtime.guarded_digest(parquet),'producing_mode':mode,'converter_path':producer,'converter_sha256':native_code[producer],'run_manifest':str(manifest),'run_driver':str(driver),
            'evidence_sha256':{str(x):runtime.guarded_digest(x) for x in (manifest,driver,options,status,source/'source_window_manifest.json')}})
        def tool(name,args):runtime.tool(f'{index}_{mode}_{name}',args,base)
        tool('force',[str(ROOT/'contributor_tools/correct_gt23_global_force_frame.py'),'--input',str(parquet),'--input-sha256',runtime.guarded_digest(parquet),'--lineage',str(lineage),'--lineage-sha256',runtime.guarded_digest(lineage),'--output',str(base/'force')])
        tool('cop_prepare',[str(ROOT/'contributor_tools/chain_gt23_cop_metadata.py'),'prepare','--force-report',str(base/'force/correction_readback.json'),'--native-lineage',str(lineage),'--plan',str(base/'cop_plan.json'),'--output',str(base/'cop')])
        tool('cop_run',[str(ROOT/'contributor_tools/chain_gt23_cop_metadata.py'),'run','--plan',str(base/'cop_plan.json'),'--plan-sha256',runtime.guarded_digest(base/'cop_plan.json')])
        tool('normalization_prepare',[str(ROOT/'contributor_tools/correct_gt23_publisher_normalization.py'),'prepare','--combined-report',str(base/'cop/combined_correction_readback.json'),'--plan',str(base/'normalization_plan.json'),'--output',str(base/'normalized')])
        tool('normalization_run',[str(ROOT/'contributor_tools/correct_gt23_publisher_normalization.py'),'run','--plan',str(base/'normalization_plan.json'),'--plan-sha256',runtime.guarded_digest(base/'normalization_plan.json')])
        raw_evidence=source/'source_window_manifest.json'
        if mode=='phase':
            raw_evidence=base/'phase_source_evidence.json'
            sha={v['source']:v['source_sha256'] for v in evidence['csv_files'].values()};sha.update(evidence['other_source_sha256']);sha[str(source/'Segmentation'/record['subject']/record['parsing'])]=runtime.guarded_digest(parsing)
            write(raw_evidence,{'output_sha256':runtime.guarded_digest(parquet),'scientific_approval':False,'source_sha256':sha,'scope':'Hash-bound source identity only; independent numerical audit follows.'})
        tool('raw_prepare',[str(ROOT/'contributor_tools/audit_gt23_publisher_raw_source.py'),'prepare','--report',str(base/'normalized/normalization_readback.json'),'--native-source-manifest',str(manifest),'--source-evidence',str(raw_evidence),'--source-evidence-sha256',runtime.guarded_digest(raw_evidence),'--output',str(base/'raw_audit')])
        tool('raw_audit',[str(ROOT/'contributor_tools/audit_gt23_publisher_raw_source.py'),'run','--plan',str(base/'raw_audit/plan.json'),'--plan-sha256',runtime.guarded_digest(base/'raw_audit/plan.json')])
        audit=read(base/'raw_audit/raw_source_readback.json')
        if audit.get('status') not in ('publisher_normalization_raw_source_checked_unreviewed','publisher_normalization_raw_source_partial_unassessed') or audit.get('participant')!=record['subject'] or audit.get('scientific_approval') is not False:raise ValueError('Independent full-record source audit failed')
        kinematic_evidence=raw_evidence
        if mode=='phase':
            kinematic_evidence=base/'phase_kinematics_source_evidence.json'
            proof=read(raw_evidence);proof['source_sha256']=dict(proof['source_sha256'])
            for name,item in evidence['csv_files'].items():
                prepared=source/'RawData'/record['subject']/'CSV_Data'/record['recording']/name
                if runtime.guarded_digest(prepared)!=item['window_sha256']:raise ValueError('Prepared source window changed')
                proof['source_sha256'][str(prepared)]=item['window_sha256']
            proof['source_sha256'][str(source/'source_window_manifest.json')]=runtime.guarded_digest(source/'source_window_manifest.json')
            write(kinematic_evidence,proof)
        tool('kinematics_prepare',[str(ROOT/'contributor_tools/audit_gt23_raw_kinematics.py'),'prepare','--report',str(base/'normalized/normalization_readback.json'),'--native-source-manifest',str(manifest),'--source-evidence',str(kinematic_evidence),'--source-evidence-sha256',runtime.guarded_digest(kinematic_evidence),'--output',str(base/'kinematics_audit')])
        tool('kinematics_run',[str(ROOT/'contributor_tools/audit_gt23_raw_kinematics.py'),'run','--plan',str(base/'kinematics_audit/plan.json'),'--plan-sha256',runtime.guarded_digest(base/'kinematics_audit/plan.json'),'--supervised-exclusive-slot'])
        kinematic_report=base/'kinematics_audit/raw_kinematics_readback.json'
        from contributor_tools.withhold_gt23_unverified_anatomy import run as withhold
        disposition=withhold(base/'normalized/corrected.parquet',base/'source_checked.parquet',check_resources=runtime.resources)
        reports[mode]={'kinematics_readback_path':str(kinematic_report),'kinematics_readback_sha256':runtime.guarded_digest(kinematic_report),'kinematics_plan':str(base/'kinematics_audit/plan.json'),'source_readback':audit,'source_readback_path':str(base/'raw_audit/raw_source_readback.json'),'source_readback_sha256':runtime.guarded_digest(base/'raw_audit/raw_source_readback.json'),'audit_plan':str(base/'raw_audit/plan.json'),'anatomy_disposition':disposition,'output':str(base/'source_checked.parquet'),'sha256':runtime.guarded_digest(base/'source_checked.parquet')}
    return {'status':'both_modes_source_checked_canonical_anatomy_unavailable','scientific_approval':False,'modes':reports}


def verify_final_ledger(runtime,scope,ledger):
    source_keys={r['subject']+'/'+r['recording'] for r in scope['records']}
    parsing_keys={r['subject']+'/'+r['parsing'] for r in scope['parsing_entries']}
    if set(ledger['source_recordings'])!=source_keys or set(ledger['parsing_entries'])!=parsing_keys:raise ValueError('Final full scope ledger differs')
    expected_sources={r['subject']+'/'+r['recording']:r for r in scope['records']}
    expected_records={r['subject']+'/'+r['parsing']:r for r in scope['parsing_entries']}
    deferred=[];partial=[]
    for key,item in ledger['source_recordings'].items():
        if item.get('status')!='all_ten_source_channels_losslessly_preserved_unreviewed':raise ValueError('Incomplete source-channel preservation')
        if runtime.guarded_digest(item['receipt'])!=item['sha256']:raise ValueError('Source preservation receipt changed')
        receipt=read(item['receipt'])
        if receipt.get('subject')+'/'+receipt.get('recording')!=key or len(receipt.get('files',[]))!=10:raise ValueError('Source receipt identity/scope differs')
        if receipt.get('status')!=item['status'] or receipt.get('scientific_approval') is not False:raise ValueError('Source preservation receipt status differs')
        if len({f['source_path'] for f in receipt['files']})!=10 or len({f['output_path'] for f in receipt['files']})!=10:raise ValueError('Duplicate source companion identity')
        expected={str((Path(runtime.plan['source_root'])/'RawData'/member['name']).resolve()):member for member in expected_sources[key]['publisher_files']}
        if {str(Path(f['source_path']).resolve()) for f in receipt['files']}!=set(expected):raise ValueError('Exact publisher source channel membership differs')
        for file in receipt['files']:
            member=expected[str(Path(file['source_path']).resolve())]
            if file['source_bytes']!=member['uncompressed_size'] or file['publisher_crc32']!=member['crc32']:raise ValueError('Publisher source size/CRC differs')
            if Path(file['source_path']).stat().st_size!=file['source_bytes'] or runtime.guarded_digest(file['source_path'])!=file['source_sha256'] or file['lossless_readback_sha256']!=file['source_sha256']:raise ValueError('Original source changed or preservation hash differs')
            if runtime.guarded_digest(file['output_path'])!=file['output_sha256']:raise ValueError('Persisted source companion changed')
    allowed={'no_source_intervals_source_channels_preserved','deferred_transform_admission_source_channels_preserved','deferred_prepared_window_admission_source_channels_preserved'}
    for key,item in ledger['parsing_entries'].items():
        if runtime.guarded_digest(item['receipt'])!=item['sha256']:raise ValueError('Parsing disposition receipt changed')
        receipt=read(item['receipt'])
        if receipt.get('record',{}).get('subject','')+'/'+receipt.get('record',{}).get('parsing','')!=key:raise ValueError('Parsing receipt source identity differs')
        if receipt.get('record')!=expected_records[key]:raise ValueError('Parsing receipt original record differs')
        if receipt.get('status')!=item['status'] or receipt.get('scientific_approval') is not False:raise ValueError('Parsing disposition status differs')
        if item['status'] in allowed:deferred.append({'entry':key,'reason':item['status']});continue
        if item['status']!='both_modes_source_checked_canonical_anatomy_unavailable' or set(receipt.get('modes',{}))!={'time','phase'}:raise ValueError('Incomplete native mode accounting')
        for mode,row in receipt['modes'].items():
            if runtime.guarded_digest(row['output'])!=row['sha256']:raise ValueError('Corrected output changed')
            audit=row['source_readback']
            if audit.get('status') not in ('publisher_normalization_raw_source_checked_unreviewed','publisher_normalization_raw_source_partial_unassessed') or audit.get('scientific_approval') is not False or audit.get('participant')!=expected_records[key]['subject']:raise ValueError('Nested source audit disposition differs')
            if runtime.guarded_digest(row['source_readback_path'])!=row['source_readback_sha256'] or read(row['source_readback_path'])!=audit:raise ValueError('Persisted source audit differs')
            if runtime.guarded_digest(row['audit_plan'])!=audit.get('plan_sha256'):raise ValueError('Source audit plan changed')
            audit_plan=read(row['audit_plan'])
            if audit_plan['mode']!=mode or audit_plan['bindings']!=audit.get('bindings') or audit_plan['expected_rows']!=audit.get('rows_checked'):raise ValueError('Source audit scope differs')
            if not audit.get('bindings') or audit_plan['parquet'] not in audit['bindings']:raise ValueError('Audited original output not bound')
            for path,sha in audit['bindings'].items():
                if runtime.guarded_digest(path)!=sha:raise ValueError('Source audit input/output changed')
            disposition=row['anatomy_disposition']
            if disposition.get('status')!='source_interpretations_preserved_canonical_anatomy_unavailable' or disposition.get('scientific_approval') is not False or disposition.get('rows')!=audit['rows_checked'] or audit['rows_checked']<=0:raise ValueError('Anatomy disposition differs')
            if runtime.guarded_digest(row['kinematics_readback_path'])!=row['kinematics_readback_sha256']:raise ValueError('Kinematics receipt changed')
            kin=read(row['kinematics_readback_path']);kp=read(row['kinematics_plan'])
            if kin.get('status') not in ('supplied_raw_kinematics_producer_recipe_checked_unreviewed','supplied_raw_kinematics_partial_unassessed') or kin.get('scientific_approval') is not False or kin.get('anatomical_approval') is not False or kin.get('physical_source_participant')!=expected_records[key]['subject'] or kin.get('source_recording')!=expected_records[key]['recording']:raise ValueError('Kinematics source disposition differs')
            if runtime.guarded_digest(row['kinematics_plan'])!=kin.get('plan_sha256') or kp['mode']!=mode or kp['parquet']!=audit_plan['parquet'] or kin['rows_checked']!=audit['rows_checked'] or kp['bindings']!=kin['bindings']:raise ValueError('Kinematics audit scope differs')
            if runtime.guarded_digest(kp['parquet'])!=kin['output_sha256']:raise ValueError('Kinematics audited output changed')
            for path,sha in kin['bindings'].items():
                if runtime.guarded_digest(path)!=sha:raise ValueError('Kinematics source binding changed')
            if kin['status']=='supplied_raw_kinematics_partial_unassessed':partial.append({'entry':key,'mode':mode,'audit':'supplied_kinematics','features':kin['entirely_unassessed_features']})
            if audit['status']=='publisher_normalization_raw_source_partial_unassessed':partial.append({'entry':key,'mode':mode,'features':audit['entirely_unassessed_features']})
    return {'source_recordings_preserved':len(source_keys),'parsing_entries_accounted':len(parsing_keys),
            'deferred_or_empty_entries':deferred,'partially_unassessed_sources':partial,
            'scientific_gaps':['Canonical joint/segment anatomical directions remain unavailable; resolve exact publisher raw-to-segmented/model convention before restoration.',
                               'Actual parsing event completeness, overlapping-window duplicate observations and task semantics remain independent validation gates.',
                               'Oversized transform/prepared windows need bounded streaming successors; recording presence is not converted-data completion.']}


def run(plan_path,expected):
    plan_path=Path(plan_path).resolve()
    if digest(plan_path)!=expected:raise ValueError('Execution plan differs')
    p=read(plan_path)
    # Refuse standalone competing work; coordinator must own the stopped controller.
    stat=Path('/proc/402226/stat').read_text().rsplit(')',1)[1].split()
    if stat[0]!='T' or stat[19]!='24607869':raise RuntimeError('Exclusive native controller hold not established')
    if Path('/proc/402226/task/402226/children').read_text().strip():raise RuntimeError('Native controller has an active child')
    parent=Path('/proc/402224/stat').read_text().rsplit(')',1)[1].split()
    if parent[0]!='T' or parent[19]!='24607849':raise RuntimeError('Unsafe old metadata parent must remain held')
    out=Path(p['output'])
    if (out/'attempt.json').exists():raise FileExistsError('Existing attempt retained; no implicit retry/overwrite')
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','ARROW_NUM_THREADS'):os.environ[key]='1'
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2));os.nice(max(0,19-os.nice(0)))
    runtime=Runtime(p);runtime.resources(True,native=True);runtime.verify_inputs();reviewed_pilots(read(p['review_path']),runtime.guarded_digest,runtime.verify_inputs);scope=read(p['scope_path'])
    def terminate(signum,frame):raise RuntimeError('Full reconstruction termination requested')
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    write(out/'attempt.json',{'plan_sha256':expected,'scientific_approval':False})
    ledger={'status':'running_unreviewed','scientific_approval':False,'source_recordings':{r['subject']+'/'+r['recording']:{'status':'pending'} for r in scope['records']},
       'parsing_entries':{r['subject']+'/'+r['parsing']:{'status':'pending'} for r in scope['parsing_entries']}}
    save(out/'progress.json',ledger)
    try:
        from contributor_tools.preserve_gt23_full_source_channels import preserve_record
        for r in scope['records']:
            if (out/'STOP').exists():raise RuntimeError('Coordinator STOP')
            key=r['subject']+'/'+r['recording'];folder=out/'source_companions'/key
            admit_record_disk(r,shutil.disk_usage(out).free,p['limits']['source_record_disk_reserve_bytes'])
            result=preserve_record(Path(p['source_root']),r,folder,runtime.resources)
            ledger['source_recordings'][key]={'status':result['status'],'receipt':str(folder/'source_readback.json'),'sha256':digest(folder/'source_readback.json')};save(out/'progress.json',ledger)
        for index,r in enumerate(scope['parsing_entries']):
            if (out/'STOP').exists():raise RuntimeError('Coordinator STOP')
            runtime.resources(True,native=True);runtime.verify_inputs();key=r['subject']+'/'+r['parsing']
            result=corrected_record(runtime,r,index);receipt=out/'parsed'/r['subject']/Path(r['parsing']).stem/'record_readback.json';result['record']=r;write(receipt,result)
            ledger['parsing_entries'][key]={'status':result['status'],'receipt':str(receipt),'sha256':digest(receipt)};save(out/'progress.json',ledger)
        runtime.verify_inputs();ledger['coverage_assessment']=verify_final_ledger(runtime,scope,ledger)
        ledger['status']='full_source_scope_accounted_anatomy_and_event_validation_unresolved'
    except BaseException as error:ledger.update(status='stopped_incomplete',reason=str(error));raise
    finally:save(out/'progress.json',ledger)
    write(out/'completion.json',{**ledger,'plan_sha256':expected,'full_scientific_approval':False})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);subs=parser.add_subparsers(dest='mode',required=True)
    a=subs.add_parser('prepare');a.add_argument('--scope',type=Path,required=True);a.add_argument('--pilot-review',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a=subs.add_parser('run');a.add_argument('--plan',type=Path,required=True);a.add_argument('--plan-sha256',required=True)
    a=parser.parse_args()
    if a.mode=='prepare':prepare(a.scope,a.pilot_review,a.output)
    else:run(a.plan,a.plan_sha256)
