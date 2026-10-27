"""Guarded serial Fukuchi ensemble pilot; plan-only unless --run is explicit.

The coordinator must schedule this job after the current numerical worker exits.
This wrapper neither launches the surrounding queue nor stops unrelated workers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT/'converted_datasets/reconversion_v2/swarm_backlog_20261021/fukuchi_source_pilot/ensemble_pilot_plan_v2.json'
PLAN_SHA256 = '266066557789e58a02bd33fca88dd70b6a7be0017623924f68fd879657ba1794'
OUTPUT = ROOT/'converted_datasets/reconversion_v2/fukuchi_ensemble_pilot_20261021'
ATTEMPT = OUTPUT.with_name(OUTPUT.name+'_guarded_attempt')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def expected_commands():
    directory = Path(__file__).parent
    return [
        ['ionice', '-c', '3', 'python3', str(directory/'convert_ensemble_pilot.py'),
         '--source-pilot', str(PLAN.parent), '--output-root', str(OUTPUT)],
        ['ionice', '-c', '3', 'python3', str(directory/'check_ensemble_pilot.py'),
         '--output-root', str(OUTPUT)],
    ]


def verified_plan():
    if digest(PLAN) != PLAN_SHA256:
        raise ValueError('Pinned v2 plan hash mismatch')
    plan = json.loads(PLAN.read_text())
    if plan['revision'] != 2 or plan['status'] != 'prepared_not_run':
        raise ValueError('Unexpected plan revision or state')
    if plan['output_root'] != str(OUTPUT) or plan['commands'] != expected_commands():
        raise ValueError('Plan commands or output paths changed')
    bindings = {str(PLAN): PLAN_SHA256}
    for key in ('code_sha256', 'source_hashes', 'fixture_sha256'):
        bindings.update(plan[key])
    for name, expected in bindings.items():
        if digest(name) != expected:
            raise ValueError('Bound input changed: '+name)
    return plan, bindings


def windows_available_mib(timeout=10):
    result = subprocess.run([
        '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '-NoProfile', '-NonInteractive', '-Command',
        '[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) | ConvertTo-Json -Compress'],
        capture_output=True, text=True, timeout=timeout, check=True)
    value = json.loads(result.stdout)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('Invalid Windows memory measurement')
    return value


def linux_available_mib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1])//1024
    raise RuntimeError('Cannot measure Linux memory')


def check_resources(prelaunch=False, probe_timeout=10):
    measurements = {'windows_available_mib': windows_available_mib(timeout=probe_timeout),
                    'linux_available_mib': linux_available_mib(),
                    'c_free_bytes': shutil.disk_usage('/mnt/c').free,
                    's_free_bytes': shutil.disk_usage('/mnt/s').free}
    if measurements['windows_available_mib'] < (2816 if prelaunch else 2048):
        raise MemoryError('Windows available memory below pilot reserve')
    if measurements['linux_available_mib'] < 2048:
        raise MemoryError('Linux available memory below 2 GiB reserve')
    if measurements['c_free_bytes'] < 1024**3 or measurements['s_free_bytes'] < 5*1024**3:
        raise OSError('Disk reserve below C: 1 GiB or S: 5 GiB')
    return measurements


def stop_owned_group(process):
    # start_new_session gives this child its own process group. Never use pkill.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def guarded_stage(command, log_path, stage):
    stage['prelaunch_resources'] = check_resources(prelaunch=True)
    environment = dict(os.environ)
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS'):
        environment[name] = '1'
    environment.pop('PYTHONOPTIMIZE', None)  # Readback assertions must be enabled.
    with log_path.open('x') as log:
        started = time.monotonic()
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        stage['pid'] = process.pid
        next_probe = started + 15
        try:
            while process.poll() is None:
                if time.monotonic()-started >= 120:
                    raise subprocess.TimeoutExpired(command, 120)
                if time.monotonic() >= next_probe:
                    stage['last_resources'] = check_resources(probe_timeout=min(10, 120-(time.monotonic()-started)))
                    next_probe = time.monotonic()+15
                time.sleep(.25)
            stage['returncode'] = process.returncode
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, command)
        finally:
            stop_owned_group(process)
            stage['elapsed_seconds'] = round(time.monotonic()-started, 3)
            stage['returncode'] = process.returncode
    stage['log_sha256'] = digest(log_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Execute only in the coordinator serial slot')
    args = parser.parse_args()
    plan, bindings = verified_plan()
    summary = {'status': 'plan_only', 'scientific_approval': False,
               'plan_sha256': PLAN_SHA256, 'runner_sha256': digest(__file__),
               'input_sha256': bindings, 'output_root': str(OUTPUT),
               'attempt_root': str(ATTEMPT), 'commands': plan['commands'], 'stages': [],
               'limits': {'step_timeout_seconds': 120, 'probe_timeout_seconds': 10,
                          'poll_seconds': 15, 'child_address_space_mib': 768,
                          'windows_prelaunch_mib': 2816, 'windows_runtime_mib': 2048,
                          'linux_available_mib': 2048, 'c_free_gib': 1, 's_free_gib': 5}}
    if not args.run:
        print(json.dumps(summary, indent=2))
        return
    if OUTPUT.exists() or ATTEMPT.exists():
        raise FileExistsError('Pilot output or attempt exists; no overwrite or implicit resume')
    ATTEMPT.mkdir(parents=False, exist_ok=False)
    os.nice(max(0, 19-os.nice(0)))
    def terminate(signum, frame):
        raise InterruptedError('Runner received signal '+str(signum))
    signal.signal(signal.SIGTERM, terminate)
    summary['status'] = 'running'
    try:
        for index, command in enumerate(plan['commands']):
            verified_plan()
            stage = {'name': ('convert', 'source_readback')[index], 'status': 'running'}
            summary['stages'].append(stage)
            guarded_stage(command, ATTEMPT/(stage['name']+'.log'), stage)
            verified_plan()
            stage['status'] = 'completed'
        report_path = OUTPUT/'source_readback.json'
        manifest_path = OUTPUT/'conversion_manifest.json'
        report = json.loads(report_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if (report['status'] != 'ensemble_source_values_checked_unreviewed'
                or report['ensembles'] != 2 or report['individual_cycles'] != 0
                or report['scientific_approval'] is not False
                or report['manifest_sha256'] != digest(manifest_path)
                or manifest['output_sha256'] != digest(OUTPUT/'ensemble.parquet')):
            raise ValueError('Pilot acceptance summary failed')
        for name, expected in report['verified_input_sha256'].items():
            if digest(name) != expected:
                raise ValueError('Readback input changed before acceptance: '+name)
        summary['output_sha256'] = {str(p): digest(p) for p in
                                   [report_path, manifest_path, OUTPUT/'ensemble.parquet']}
        summary['status'] = 'ensemble_pilot_source_readback_passed_unreviewed'
    except BaseException as error:
        summary['status'] = 'failed'
        summary['error'] = type(error).__name__+': '+str(error)
        if summary['stages'] and summary['stages'][-1]['status'] == 'running':
            summary['stages'][-1]['status'] = 'failed'
        raise
    finally:
        with (ATTEMPT/'summary.json').open('x') as stream:
            json.dump(summary, stream, indent=2)
            stream.write('\n')
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
