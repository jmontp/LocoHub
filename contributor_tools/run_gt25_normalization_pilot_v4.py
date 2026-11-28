"""Execute a hash-bound, serial GT25 ankle and normalization v4 pilot handoff; plan-only by default.

Each child retains its existing memory/headroom guards. This wrapper owns only
its child process group and adds a timeout and exact pilot acceptance gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(bindings):
    for path, expected in bindings.items():
        if digest(path) != expected:
            raise ValueError('Changed binding: ' + path)


def acceptance(report, stage):
    expected = ('streaming_transfer_converted_unreviewed' if stage == 'conversion'
                else 'independent_raw_transfer_events_and_values_checked_unreviewed')
    count = 'observations' if stage == 'conversion' else 'observations_checked'
    rows = 'rows' if stage == 'conversion' else 'rows_checked'
    if report.get('status') != expected or report.get(count) != 28 or report.get(rows) != 4200:
        raise ValueError('BT07 pilot coverage/status differs')
    if stage == 'audit' and report.get('numeric_features_checked') != 92:
        raise ValueError('Expected all 92 canonical/source numerical features')
    if report.get('scientific_approval') is not False:
        raise ValueError('Unexpected scientific approval')


def child(command, cwd, log):
    env = dict(os.environ)
    for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'ARROW_NUM_THREADS'):
        env[key] = '1'
    with Path(log).open('x') as stream:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            result = process.wait(timeout=3660)
        except BaseException:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        if result:
            raise RuntimeError('Pilot child failed; see ' + str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if digest(args.plan) != args.plan_sha256:
        raise ValueError('Handoff plan hash differs')
    plan = json.loads(args.plan.read_text())
    verify(plan['bindings'])
    if not args.run:
        print(json.dumps({'status': 'prepared_not_executed', 'bindings_verified': len(plan['bindings'])}))
        return
    attempt = Path(plan['attempt_root'])
    attempt.mkdir(exist_ok=False)
    result = {'status': 'running', 'scientific_approval': False, 'stages': [],
              'handoff_sha256': args.plan_sha256}
    try:
        for stage in plan['stages']:
            verify(plan['bindings'])
            child(stage['command'], plan['cwd'], attempt / (stage['name'] + '.log'))
            report = json.loads(Path(stage['report']).read_text())
            acceptance(report, stage['name'])
            verify(report.get('bindings', {}))
            if stage['name'] == 'conversion':
                phase = Path(stage['report']).parent / 'phase.parquet'
                if digest(phase) != report['phase_sha256']:
                    raise ValueError('Converted output hash differs')
                actual = {s['source_path']: s['source_sha256'] for s in report['sources']}
                if actual != plan['expected_source_hashes']:
                    raise ValueError('Exact source coverage/hash differs')
            result['stages'].append({'name': stage['name'], 'report': stage['report'],
                                     'report_sha256': digest(stage['report'])})
        verify(plan['bindings'])
        result['status'] = 'corrected_transfer_source_readback_complete_unreviewed'
    except BaseException as error:
        result.update(status='failed_incomplete', reason=str(error))
        raise
    finally:
        (attempt / 'handoff_summary.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
