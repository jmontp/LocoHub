"""Prepare one immutable publisher archive acquisition; --run opts into download.

No extraction, conversion, or writes to the active sixteen-participant source.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = Path('/mnt/s/locomotion_data/gt21_missing_participants_v1')
BUFFER = 1024**2
RESERVE = 15 * 1024**3


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(BUFFER), b''):
            h.update(block)
    return h.hexdigest()


def host_available():
    result = subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '-NoProfile', '-NonInteractive', '-Command',
        '[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress'],
        capture_output=True, text=True, check=True, timeout=15)
    return int(json.loads(result.stdout))


def copy_verified(response, stream, expected_size, expected_sha, guard, rate=BUFFER):
    """Bounded bytes, immutable SHA, and average transfer-rate ceiling."""
    start = time.monotonic(); count = 0; sha = hashlib.sha256()
    while True:
        guard(expected_size-count)
        if time.monotonic()-start > 2700:
            raise TimeoutError('Archive acquisition exceeded 45 minutes')
        block = response.read(min(BUFFER, expected_size-count+1))
        if not block:
            break
        count += len(block)
        if count > expected_size:
            raise ValueError('Archive exceeds publisher size')
        stream.write(block); sha.update(block)
        if rate:
            delay = count/rate - (time.monotonic()-start)
            if delay > 0:
                time.sleep(min(delay, 1))
    if count != expected_size or sha.hexdigest() != expected_sha:
        raise ValueError('Publisher size or SHA256 mismatch')
    return count


def prepare(ledger, subject):
    report = json.loads(Path(ledger).read_text())
    records = [x for x in report['missing_participant_ledger'] if x['subject'] == subject]
    if len(records) != 1 or subject not in report['missing_participants']:
        raise ValueError('Exactly one missing participant required')
    archive = records[0]['available_individual_archive']
    if archive['status'] != 'COMPLETED' or not archive['doi'].endswith('.1'):
        raise ValueError('Expected completed version1 archive')
    return {'status':'prepared_not_downloaded', 'scientific_approval':False, 'subject':subject,
        'archive':archive, 'destination':str(DESTINATION/subject),
        'bindings':{str(Path(ledger).resolve()):digest(ledger),str(Path(__file__).resolve()):digest(__file__)},
        'limits':{'buffer_bytes':BUFFER,'bandwidth_bytes_per_second':BUFFER,'timeout_seconds':2700,
                  'disk_reserve_after_download_bytes':RESERVE,'address_space_mib':256,
                  'windows_startup_mib':2816,'windows_runtime_mib':2048},
        'expanded_size_bytes':None,'expanded_size_status':'Unknown; no ZIP directory or payload fetched. Extraction is a separate admission gate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,default=ROOT/'docs/quality/audits/gt21-participant-source-coverage.json')
    parser.add_argument('--subject',required=True)
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    plan = prepare(args.ledger,args.subject)
    out = Path(plan['destination']); plan_path = out/'acquisition_plan.json'
    if out.exists():
        if not plan_path.is_file() or list(out.iterdir()) != [plan_path] or json.loads(plan_path.read_text()) != plan:
            raise FileExistsError('Existing attempt preserved; inspect separately')
    else:
        out.mkdir(parents=True,exist_ok=False)
        plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    if not args.run:
        print(json.dumps({'status':plan['status'],'plan':str(plan_path)})); return
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    os.nice(max(0,19-os.nice(0)))
    archive = plan['archive']; last=0.; plan_hash=digest(plan_path)
    def guard(remaining):
        nonlocal last
        if (out/'STOP').exists():raise RuntimeError('Acquisition stopped by request')
        if shutil.disk_usage(out).free < RESERVE+remaining:
            raise MemoryError('Insufficient disk reserve for remaining archive plus15GiB')
        if time.monotonic()-last >= 15:
            if host_available() < 2048:raise MemoryError('Windows runtime reserve below2GiB')
            last=time.monotonic()
    if host_available() < 2816:raise MemoryError('Windows startup reserve below2816MiB')
    guard(archive['size'])
    partial=out/(archive['sha256_hash']+'.zip.partial'); final=out/(archive['sha256_hash']+'.zip')
    receipt=out/'acquisition_result.json'
    result={'status':'downloading','scientific_approval':False,'plan_sha256':plan_hash}
    receipt.write_text(json.dumps(result)+'\n')
    try:
        request=urllib.request.Request(archive['download_url'],headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity'})
        with urllib.request.urlopen(request,timeout=30) as response,partial.open('xb') as stream:
            if response.status!=200 or int(response.headers.get('Content-Length','-1'))!=archive['size']:
                raise ValueError('Unexpected HTTP status or publisher size')
            count=copy_verified(response,stream,archive['size'],archive['sha256_hash'],guard)
            stream.flush();os.fsync(stream.fileno())
        if digest(plan_path)!=plan_hash or any(digest(p)!=h for p,h in plan['bindings'].items()):
            raise ValueError('Acquisition dependencies changed')
        # Atomic no-clobber publication on the same filesystem; failed attempts stay intact.
        os.link(partial,final);partial.unlink()
        result.update(status='publisher_archive_sha256_verified_not_extracted',bytes=count,archive_path=str(final),sha256=archive['sha256_hash'])
    except Exception as error:
        result.update(status='failed_partial_preserved',reason=str(error));raise
    finally:
        receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
