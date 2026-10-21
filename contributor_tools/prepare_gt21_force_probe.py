"""Prepare/run one guarded native force-source export for coordinate review."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contributor_tools.reconvert_recording import digest, ensure_storage_headroom
from contributor_tools.run_gt21_native_batch import windows_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--subject', required=True)
    p.add_argument('--date', required=True)
    p.add_argument('--mode', choices=['treadmill', 'ramp', 'stair', 'levelground'], required=True)
    p.add_argument('--recording', required=True)
    p.add_argument('--output-root', type=Path, required=True)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    os.nice(max(0, 19 - os.nice(0)))
    out = args.output_root.resolve()
    ensure_storage_headroom(out)
    if shutil.disk_usage('/mnt/c').free < 1024**3:
        raise OSError('C drive below 1 GiB free')
    source_root = args.source_root.resolve()
    sources = [source_root / args.subject / args.date / args.mode / channel / args.recording
               for channel in ('fp', 'markers')]
    if any(not x.resolve().is_relative_to(source_root) for x in sources):
        raise ValueError('Source outside root')
    if sum(x.stat().st_size for x in sources) > 64 * 1024**2:
        raise MemoryError('Source exceeds 64 MiB admission')
    guard = ROOT / 'contributor_tools/run_matlab_recording_guarded.ps1'
    helper = ROOT / 'contributor_tools/audit_probes/2026_10_20/export_gt21_force_sources.m'
    code = [Path(__file__), guard, helper, ROOT / 'contributor_tools/reconvert_recording.py',
            ROOT / 'contributor_tools/run_gt21_native_batch.py']
    plan = {'sources': {str(x): digest(x) for x in sources},
            'code': {str(x): digest(x) for x in code}, 'scientific_approval': False}
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / 'probe_plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError('Probe inputs changed; use a new output root')
    plan_path.write_text(json.dumps(plan, indent=2) + '\n')
    code_dir = out / 'code'
    code_dir.mkdir(exist_ok=True)
    shutil.copyfile(helper, code_dir / helper.name)
    # Reuse the unchanged guarded launcher through a narrowly scoped entry point.
    (code_dir / 'convert_gtech_2021_phase_to_parquet.m').write_text(
        'function convert_gtech_2021_phase_to_parquet(options)\n'
        'export_gt21_force_sources(options);\nend\n')
    options = {'data_root': windows_path(source_root), 'subject': args.subject,
               'date': args.date, 'mode': args.mode, 'recording': args.recording,
               'output_path': windows_path(out / 'native_source_manifest.json')}
    (out / 'options.json').write_text(json.dumps(options, indent=2) + '\n')
    if not args.run:
        print(json.dumps({'status': 'prepared_only', 'source_bytes': sum(x.stat().st_size for x in sources)}))
        return
    if (out / 'native_source_manifest.json').exists():
        raise FileExistsError('Probe already produced output; use its readback evidence')
    command = ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
        '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', windows_path(guard),
        '-OptionsPath', windows_path(out / 'options.json'), '-CodeDirectory', windows_path(code_dir),
        '-MemoryMiB', '2048', '-TimeoutSeconds', '300']
    with (out / 'launcher.log').open('x') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError('Native source probe failed; see launcher.log')
    native = json.loads((out / 'native_status.json').read_text(encoding='utf-8-sig'))
    if native['status'] != 'completed' or native['exit_code'] != 0:
        raise RuntimeError('Native worker did not complete')
    for group in ('sources', 'code'):
        if any(digest(Path(x)) != sha for x, sha in plan[group].items()):
            raise RuntimeError('Source or code changed during probe')
    report = json.loads((out / 'native_source_manifest.json').read_text())
    assert report['status'] == 'native_source_tables_readback'
    for item in report['tables']:
        item['sha256'] = digest(out / item['file'])
    report['inputs'] = plan
    (out / 'source_comparison.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'tables': len(report['tables'])}))


if __name__ == '__main__':
    main()
