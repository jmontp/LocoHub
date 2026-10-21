"""Resume the frozen GT21 batch after a proven pre-launch memory refusal.

Keeps all completed outputs and every refused-launch artifact. Native execution
failures, scientific audit failures, and explicit stop requests never auto-retry.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from contributor_tools.reconvert_recording import digest


def prelaunch_memory_refusal(folder):
    required={'options.json','input_manifest.json','launcher.log'}
    if not folder.is_dir() or {p.name for p in folder.iterdir()}!=required:return False
    if not all((folder/name).is_file() and not (folder/name).is_symlink() for name in required):return False
    return 'Windows needs the hard limit plus 2 GiB available before launch' in (folder/'launcher.log').read_text()


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--batch-root',type=Path,required=True)
    p.add_argument('--control-root',type=Path,required=True);a=p.parse_args()
    batch=a.batch_root.resolve();control=a.control_root.resolve();control.mkdir(parents=True,exist_ok=True)
    lock=(control/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    os.nice(max(0,19-os.nice(0)))
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
    # The conversion remains bound to its original code evidence.
    evidence=json.loads((batch/'batch_code.json').read_text())
    state={'pid':os.getpid(),'status':'starting','scientific_approval':False,'attempts':[]}
    state_path=control/'status.json'
    def stopped():return (batch/'STOP_AFTER_CURRENT').exists() or (control/'STOP_AFTER_CURRENT').exists()
    def launch(command,log):
        with log.open('x') as stream:
            return subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
    try:
        while True:
            if stopped():raise RuntimeError('Explicit stop request; no automatic resume')
            assert all(digest(Path(x['path']))==x['sha256'] for x in evidence),'Frozen conversion code changed'
            previous=json.loads((batch/'batch_status.json').read_text())
            if previous['status']=='stopped_incomplete':
                record=previous['active_recording'];folder=batch/record['subject']/record['date']/record['mode']/Path(record['recording']).stem
                if not prelaunch_memory_refusal(folder):raise RuntimeError('Failure is not a proven pre-launch memory refusal')
                archive=control/f'prelaunch_refusal_{time.time_ns()}';folder.rename(archive)
                save(archive/'batch_status.json',previous)
                state.setdefault('preserved_refusals',[]).append({'path':str(archive),'recording':record,
                    'files':{x.name:digest(x) for x in archive.iterdir()}})
                # Do not archive the same refusal again if interrupted while waiting.
                previous['status']='waiting_for_host_memory';save(batch/'batch_status.json',previous)
            elif previous['status'] not in ('waiting_for_host_memory','complete_unreviewed'):
                raise RuntimeError('Unexpected batch state; refuse duplicate producer: '+previous['status'])
            while True:
                if stopped():raise RuntimeError('Explicit stop request during memory wait')
                result=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command','[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress'],capture_output=True,text=True,timeout=30,check=True)
                free=int(json.loads(result.stdout))
                state.update(status='waiting_for_host_memory',windows_available_mib=free,c_free_bytes=shutil.disk_usage('/mnt/c').free,s_free_bytes=shutil.disk_usage('/mnt/s').free,checked_at_unix=time.time());save(state_path,state)
                if free>=4352 and state['c_free_bytes']>=1024**3 and state['s_free_bytes']>=5*1024**3:break
                time.sleep(30)
            attempt=control/f'attempt_{time.time_ns()}';attempt.mkdir()
            producer=launch(['python3','contributor_tools/run_gt21_native_batch.py','--output-root',str(batch),'--run'],attempt/'conversion.log')
            auditor=launch(['python3','contributor_tools/audit_gt21_native_batch.py','--batch-root',str(batch),'--output-root',str(attempt/'source_audit'),'--watch-pid',str(producer.pid)],attempt/'audit.log')
            state.update(status='running',producer_pid=producer.pid,auditor_pid=auditor.pid);save(state_path,state)
            while producer.poll() is None:
                if stopped() or (auditor.poll() is not None and auditor.returncode):
                    (batch/'STOP_AFTER_CURRENT').touch()
                time.sleep(2)
            # Audit drains completed records after the producer exits.
            while auditor.poll() is None:time.sleep(2)
            item={'path':str(attempt),'producer_exit':producer.returncode,'auditor_exit':auditor.returncode}
            state['attempts'].append(item);save(state_path,state)
            if auditor.returncode:raise RuntimeError('Source checker failed; no automatic resume')
            if producer.returncode==0:
                end=json.loads((batch/'batch_status.json').read_text())
                audit=json.loads((attempt/'source_audit/audit_status.json').read_text())
                if end['status']!='complete_unreviewed' or audit['status']!='all_recordings_source_checked_unreviewed':
                    raise RuntimeError('Batch or source audit is incomplete')
                state['status']='complete_source_checked_unreviewed';break
            # Only the narrow refusal classifier above permits another attempt.
    except Exception as error:state.update(status='stopped_incomplete',reason=str(error));raise
    finally:save(state_path,state)


if __name__=='__main__':main()
